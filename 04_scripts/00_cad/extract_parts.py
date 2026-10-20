"""Extract a per-instance part table from the STEP assembly with OpenCascade XCAF.

A full run takes about 11 minutes and 3.7 GB peak memory (2026-10-19: STEP
read and XCAF transfer about 2 min, measuring 681 prototypes about 8.5 min),
so the result is cached as ``01_cad/01_parts/parts.csv``; later analysis reads only that
table.

Each row is one leaf occurrence (a part placed in the assembly). Geometry
values are in the STEP length unit (mm) and the world frame of the STEP root.
Mass properties are computed per prototype shape with unit density and then
transformed to the world frame:

* ``volume_mm3``: solid volume.
* ``centroid_*_mm``: volume centroid.
* ``inertia_*_mm5``: inertia tensor about the centroid for density 1, world
  axes, tensor convention (off-diagonal terms are -integral(x*y dV)).
  Multiply by density (kg/mm^3) to get kg*mm^2.

Usage:
    python -I 04_scripts/00_cad/extract_parts.py [--force]
"""

import argparse
import csv
import math
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GeomAbs import GeomAbs_Cylinder
from OCC.Core.GProp import GProp_GProps
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPCAFControl import STEPCAFControl_Reader
from OCC.Core.TCollection import TCollection_AsciiString, TCollection_ExtendedString
from OCC.Core.TDataStd import TDataStd_TreeNode
from OCC.Core.TDF import (
    TDF_Attribute,
    TDF_AttributeIterator,
    TDF_Label,
    TDF_LabelSequence,
    TDF_Tool,
)
from OCC.Core.TDocStd import TDocStd_Document
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.TopoDS import TopoDS_Shape, topods
from OCC.Core.XCAFApp import XCAFApp_Application
from OCC.Core.XCAFDoc import (
    XCAFDoc_DocumentTool,
    XCAFDoc_Material,
    XCAFDoc_ShapeTool,
    xcafdoc,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad_common import PARTS_CSV, STEP_PATH, decode_step_string

DOCUMENT_FORMAT = "XmlXCAF"
PATH_SEPARATOR = " / "
PROGRESS_EVERY_PROTOTYPES = 50


@dataclass
class PrototypeGeometry:
    """Geometry of one part definition in its own coordinate frame."""

    solid_count: int
    shell_count: int
    volume_mm3: float
    centroid_mm: np.ndarray
    inertia_mm5: np.ndarray
    main_cylinder_radius_mm: float
    main_cylinder_area_mm2: float
    main_cylinder_axis: np.ndarray


@dataclass
class PartRow:
    """One leaf occurrence of the assembly, ready to be written as CSV."""

    instance_path: str
    top_assembly: str
    depth: int
    product_name: str
    instance_name: str
    prototype_entry: str
    instance_count: int
    material: str
    density_g_cm3: float
    is_mirrored: bool
    solid_count: int
    shell_count: int
    bbox_min_x_mm: float
    bbox_min_y_mm: float
    bbox_min_z_mm: float
    bbox_max_x_mm: float
    bbox_max_y_mm: float
    bbox_max_z_mm: float
    volume_mm3: float
    centroid_x_mm: float
    centroid_y_mm: float
    centroid_z_mm: float
    inertia_xx_mm5: float
    inertia_yy_mm5: float
    inertia_zz_mm5: float
    inertia_xy_mm5: float
    inertia_xz_mm5: float
    inertia_yz_mm5: float
    main_cylinder_radius_mm: float
    main_cylinder_area_mm2: float
    main_cylinder_axis_x: float
    main_cylinder_axis_y: float
    main_cylinder_axis_z: float


# --------------------------------------------------------------------------
# Document loading
# --------------------------------------------------------------------------
def load_document(step_path: Path) -> TDocStd_Document:
    """Read the STEP assembly into an XCAF document with names and materials.

    Raises:
        RuntimeError: If OpenCascade cannot read or translate the file.
    """
    application = XCAFApp_Application.GetApplication()
    document = TDocStd_Document(TCollection_ExtendedString(DOCUMENT_FORMAT))
    application.NewDocument(TCollection_ExtendedString(DOCUMENT_FORMAT), document)
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetMatMode(True)
    reader.SetColorMode(False)
    reader.SetLayerMode(False)
    if reader.ReadFile(str(step_path)) != IFSelect_RetDone:
        raise RuntimeError(f"STEP read failed: {step_path}")
    print("STEP parsed; transferring to XCAF ...", flush=True)
    if not reader.Transfer(document):
        raise RuntimeError(f"STEP transfer failed: {step_path}")
    return document


# --------------------------------------------------------------------------
# Label helpers
# --------------------------------------------------------------------------
def _label_name(label: TDF_Label) -> str:
    return decode_step_string(label.GetLabelName())


def _find_attribute(label: TDF_Label, guid) -> TDF_Attribute | None:
    """Return the attribute with ``guid`` on ``label``, or None.

    pythonocc's ``TDF_Label.FindAttribute`` returns True but does not fill a
    derived attribute object passed as the out-parameter, so iterate instead.
    """
    iterator = TDF_AttributeIterator(label)
    while iterator.More():
        attribute = iterator.Value()
        if attribute.ID().IsSame(guid):
            return attribute
        iterator.Next()
    return None


def _read_material(label: TDF_Label) -> tuple[str, float]:
    """Return (material name, density in g/cm^3) attached to a shape label."""
    reference = _find_attribute(label, xcafdoc.MaterialRefGUID())
    if reference is None:
        return "", math.nan
    tree_node = TDataStd_TreeNode.DownCast(reference)
    # The shape and material nodes are linked parent/child; which side is the
    # parent has differed between OCC versions (Father() in 7.9/8.0).
    material_node = tree_node.First() if tree_node.HasFirst() else tree_node.Father()
    if material_node is None:
        return "", math.nan
    found = _find_attribute(material_node.Label(), XCAFDoc_Material.GetID())
    if found is None:
        return "", math.nan
    material = XCAFDoc_Material.DownCast(found)
    name = decode_step_string(material.GetName().ToCString())
    # XCAFDoc_Material keeps the STEP value as written (g/cm^3 here).
    return name, material.GetDensity()


def _label_entry(label: TDF_Label) -> str:
    """Return the OCAF entry (e.g. ``0:1:1:5``), unique per prototype label."""
    entry = TCollection_AsciiString()
    TDF_Tool.Entry(label, entry)
    return entry.ToCString()


def _sub_labels(label: TDF_Label) -> list[TDF_Label]:
    components = TDF_LabelSequence()
    XCAFDoc_ShapeTool.GetComponents(label, components, False)
    return [components.Value(index) for index in range(1, components.Length() + 1)]


def _referred_label(component: TDF_Label) -> TDF_Label:
    referred = TDF_Label()
    XCAFDoc_ShapeTool.GetReferredShape(component, referred)
    return referred


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def _count_subshapes(shape: TopoDS_Shape, shape_type) -> int:
    explorer = TopExp_Explorer(shape, shape_type)
    count = 0
    while explorer.More():
        count += 1
        explorer.Next()
    return count


def _inertia_matrix(properties: GProp_GProps) -> np.ndarray:
    matrix = properties.MatrixOfInertia()
    return np.array(
        [[matrix.Value(row, column) for column in (1, 2, 3)] for row in (1, 2, 3)]
    )


def _main_cylinder(shape: TopoDS_Shape) -> tuple[float, float, np.ndarray]:
    """Return radius, total area and axis of the largest-area cylinder radius."""
    area_by_radius: dict[float, float] = {}
    axis_by_radius: dict[float, np.ndarray] = {}
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        surface = BRepAdaptor_Surface(face, True)
        if surface.GetType() != GeomAbs_Cylinder:
            continue
        cylinder = surface.Cylinder()
        radius = round(cylinder.Radius(), 1)
        face_properties = GProp_GProps()
        brepgprop.SurfaceProperties(face, face_properties)
        area_by_radius[radius] = (
            area_by_radius.get(radius, 0.0) + face_properties.Mass()
        )
        direction = cylinder.Axis().Direction()
        axis_by_radius[radius] = np.array([direction.X(), direction.Y(), direction.Z()])
    if not area_by_radius:
        return math.nan, 0.0, np.full(3, math.nan)
    radius = max(area_by_radius, key=area_by_radius.get)
    return radius, area_by_radius[radius], axis_by_radius[radius]


def measure_prototype(shape: TopoDS_Shape) -> PrototypeGeometry:
    """Compute unit-density mass properties of a part in its own frame."""
    properties = GProp_GProps()
    brepgprop.VolumeProperties(shape, properties)
    center = properties.CentreOfMass()
    radius, area, axis = _main_cylinder(shape)
    return PrototypeGeometry(
        solid_count=_count_subshapes(shape, TopAbs_SOLID),
        shell_count=_count_subshapes(shape, TopAbs_SHELL),
        volume_mm3=properties.Mass(),
        centroid_mm=np.array([center.X(), center.Y(), center.Z()]),
        inertia_mm5=_inertia_matrix(properties),
        main_cylinder_radius_mm=radius,
        main_cylinder_area_mm2=area,
        main_cylinder_axis=axis,
    )


def _rotation_and_translation(
    location: TopLoc_Location,
) -> tuple[np.ndarray, np.ndarray]:
    transform = location.Transformation()
    rotation = np.array(
        [[transform.Value(row, column) for column in (1, 2, 3)] for row in (1, 2, 3)]
    )
    translation = np.array([transform.Value(row, 4) for row in (1, 2, 3)])
    return rotation, translation


def _world_bbox(shape: TopoDS_Shape, location: TopLoc_Location) -> tuple[float, ...]:
    box = Bnd_Box()
    brepbndlib.AddOptimal(shape.Moved(location), box, False, False)
    if box.IsVoid():
        return (math.nan,) * 6
    return box.Get()


# --------------------------------------------------------------------------
# Assembly traversal
# --------------------------------------------------------------------------
@dataclass
class _Occurrence:
    prototype: TDF_Label
    location: TopLoc_Location
    names: list[str]


def collect_occurrences(document: TDocStd_Document) -> list[_Occurrence]:
    """Walk the assembly tree and return every leaf occurrence."""
    shape_tool = XCAFDoc_DocumentTool.ShapeTool(document.Main())
    roots = TDF_LabelSequence()
    shape_tool.GetFreeShapes(roots)

    occurrences: list[_Occurrence] = []
    pending = [
        (roots.Value(index), TopLoc_Location(), [_label_name(roots.Value(index))])
        for index in range(1, roots.Length() + 1)
    ]
    while pending:
        label, location, names = pending.pop()
        if not XCAFDoc_ShapeTool.IsAssembly(label):
            occurrences.append(_Occurrence(label, location, names))
            continue
        for component in _sub_labels(label):
            component_location = location.Multiplied(
                XCAFDoc_ShapeTool.GetLocation(component)
            )
            child_names = [*names, _label_name(component)]
            pending.append(
                (_referred_label(component), component_location, child_names)
            )
    return occurrences


def _build_row(
    occurrence: _Occurrence,
    geometry: PrototypeGeometry,
    instance_count: int,
    material: tuple[str, float],
) -> PartRow:
    prototype_shape = XCAFDoc_ShapeTool.GetShape(occurrence.prototype)
    rotation, translation = _rotation_and_translation(occurrence.location)
    centroid = rotation @ geometry.centroid_mm + translation
    inertia = rotation @ geometry.inertia_mm5 @ rotation.T
    axis = rotation @ geometry.main_cylinder_axis
    bbox = _world_bbox(prototype_shape, occurrence.location)
    return PartRow(
        instance_path=PATH_SEPARATOR.join(occurrence.names),
        top_assembly=occurrence.names[1] if len(occurrence.names) > 1 else "",
        depth=len(occurrence.names) - 1,
        product_name=_label_name(occurrence.prototype),
        instance_name=occurrence.names[-1],
        prototype_entry=_label_entry(occurrence.prototype),
        instance_count=instance_count,
        material=material[0],
        density_g_cm3=material[1],
        is_mirrored=bool(np.linalg.det(rotation) < 0),
        solid_count=geometry.solid_count,
        shell_count=geometry.shell_count,
        bbox_min_x_mm=bbox[0],
        bbox_min_y_mm=bbox[1],
        bbox_min_z_mm=bbox[2],
        bbox_max_x_mm=bbox[3],
        bbox_max_y_mm=bbox[4],
        bbox_max_z_mm=bbox[5],
        volume_mm3=geometry.volume_mm3,
        centroid_x_mm=centroid[0],
        centroid_y_mm=centroid[1],
        centroid_z_mm=centroid[2],
        inertia_xx_mm5=inertia[0, 0],
        inertia_yy_mm5=inertia[1, 1],
        inertia_zz_mm5=inertia[2, 2],
        inertia_xy_mm5=inertia[0, 1],
        inertia_xz_mm5=inertia[0, 2],
        inertia_yz_mm5=inertia[1, 2],
        main_cylinder_radius_mm=geometry.main_cylinder_radius_mm,
        main_cylinder_area_mm2=geometry.main_cylinder_area_mm2,
        main_cylinder_axis_x=axis[0],
        main_cylinder_axis_y=axis[1],
        main_cylinder_axis_z=axis[2],
    )


def build_part_rows(document: TDocStd_Document) -> list[PartRow]:
    """Measure each prototype once and emit one row per occurrence."""
    occurrences = collect_occurrences(document)
    occurrences_by_prototype: dict[str, list[_Occurrence]] = {}
    for occurrence in occurrences:
        entry = _label_entry(occurrence.prototype)
        occurrences_by_prototype.setdefault(entry, []).append(occurrence)
    print(
        f"{len(occurrences)} leaf occurrences, "
        f"{len(occurrences_by_prototype)} prototypes",
        flush=True,
    )

    rows: list[PartRow] = []
    started_s = time.perf_counter()
    for done, group in enumerate(occurrences_by_prototype.values(), start=1):
        prototype = group[0].prototype
        geometry = measure_prototype(XCAFDoc_ShapeTool.GetShape(prototype))
        material = _read_material(prototype)
        rows.extend(_build_row(item, geometry, len(group), material) for item in group)
        if done % PROGRESS_EVERY_PROTOTYPES == 0:
            elapsed_s = time.perf_counter() - started_s
            print(
                f"  measured {done}/{len(occurrences_by_prototype)} ({elapsed_s:.0f} s)",
                flush=True,
            )
    rows.sort(key=lambda row: row.instance_path)
    return rows


def write_rows(rows: list[PartRow], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    records = [asdict(row) for row in rows]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--force", action="store_true", help="re-extract even if cached"
    )
    parser.add_argument("--step", type=Path, default=STEP_PATH, help="STEP input")
    parser.add_argument("--output", type=Path, default=PARTS_CSV, help="CSV output")
    arguments = parser.parse_args()

    if arguments.output.exists() and not arguments.force:
        print(f"cached: {arguments.output} (use --force to rebuild)")
        return
    started_s = time.perf_counter()
    document = load_document(arguments.step)
    print(f"document ready in {time.perf_counter() - started_s:.0f} s", flush=True)
    rows = build_part_rows(document)
    write_rows(rows, arguments.output)
    print(
        f"wrote {len(rows)} rows to {arguments.output} "
        f"in {time.perf_counter() - started_s:.0f} s total"
    )


if __name__ == "__main__":
    main()
