"""Build the face index of the whole assembly (C5) from the B-rep cache.

Every prototype of ``01_cad/06_brep`` is analysed once (faces in
``TopExp_Explorer`` order), then the rows are moved to every occurrence with
the placement matrices of ``instances.csv``. The STEP file is not read.

Outputs (``01_cad/07_faces/``):

* ``prototype_faces.csv.gz``: one row per face of each prototype, prototype
  frame (mm).
* ``instance_faces.csv.gz``: one row per face of each occurrence, CAD world
  frame (mm, Y up) and body frame (m; x = +Z_cad, y = +X_cad, z = +Y_cad,
  origin = CAD origin).
* ``face_index_summary.json``: counts, crawler selection, timing, memory,
  provenance, column description.
* ``face_index_verification.json``: area sums, normal self-check, comparison
  with ``02_legs/leg_faces.csv``, ``04_mast/mast_faces.csv`` and the crawler
  grouser tips, IMU C1 query, query timings.

Conventions:

* ``face_index``: position of the face in ``TopExp_Explorer(prototype,
  TopAbs_FACE)``; reproducible for the same cache file.
* ``solid_index``: position of the first solid containing the face in
  ``TopExp_Explorer(prototype, TopAbs_SOLID)`` (unique solids), -1 if the
  face belongs to no solid.
* Plane normal: outward normal of the face (surface normal XDir x YDir of the
  plane, reversed for a REVERSED face). Faces outside solids (open shells,
  ``solid_index = -1``), faces of solids that fail ``BRepCheck_Analyzer``
  (``solid_valid = False``) and faces of parts with zero volume carry
  ``normal_uncertain = True``: an open shell has no inside, so "outward" is
  only the stored orientation. (The 49 zero-volume occurrences of
  ``parts.csv`` are empty shapes without faces; they give no rows.)
* Cylinder, cone, sphere, torus: ``axis_*`` (direction sign arbitrary),
  ``axis_point_*`` = face centroid projected on the axis (sphere: centre),
  ``radius_mm`` (cylinder radius, cone reference radius, sphere radius, torus
  major radius), ``radius2_mm`` (torus minor radius), ``cone_half_angle_rad``.
  ``convex`` = the outward normal points away from the axis or centre (shaft,
  boss); False = bore, hole.
* Crawler (``0:1:1:746``, another model's undercarriage, 156,614 faces): by
  default only faces whose lowest point is within ``CRAWLER_BAND_MM`` of the
  ground plus downward grouser tip planes (plane, normal y_cad < -0.99,
  within ``TIP_SEARCH_MM``) are kept; ``--crawler-all`` keeps every face.
  ``face_index`` keeps the full explorer numbering either way.

Usage (project root, about 3 min)::

    python -I 04_scripts/00_cad/build_face_index.py [--crawler-all] [--verify-only]
    python -I 04_scripts/00_cad/check_cache.py --write --cache 07_faces
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepClass3d import BRepClass3d_SolidClassifier
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepLProp import BRepLProp_SLProps
from OCC.Core.BRepTools import breptools
from OCC.Core.BRepTopAdaptor import BRepTopAdaptor_FClass2d
from OCC.Core.GeomAbs import (
    GeomAbs_BezierSurface,
    GeomAbs_BSplineSurface,
    GeomAbs_Cone,
    GeomAbs_Cylinder,
    GeomAbs_OffsetSurface,
    GeomAbs_OtherSurface,
    GeomAbs_Plane,
    GeomAbs_Sphere,
    GeomAbs_SurfaceOfExtrusion,
    GeomAbs_SurfaceOfRevolution,
    GeomAbs_Torus,
)
from OCC.Core.gp import gp_Pnt, gp_Pnt2d
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_IN, TopAbs_OUT, TopAbs_REVERSED, TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer, topexp
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.TopoDS import TopoDS_Face, TopoDS_Shape, topods
from OCC.Core.TopTools import TopTools_IndexedMapOfShape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brep_cache
from cad_common import FACES_DIR, LEGS_DIR, MAST_DIR, MM_PER_M, PARTS_CSV, PROJECT_ROOT
from check_cache import sha256_file

PROTOTYPE_FACES = FACES_DIR / "prototype_faces.csv.gz"
INSTANCE_FACES = FACES_DIR / "instance_faces.csv.gz"
SUMMARY_JSON = FACES_DIR / "face_index_summary.json"
VERIFICATION_JSON = FACES_DIR / "face_index_verification.json"
LOG_PATH = FACES_DIR / "build.log"
CRAWLER_DIR = brep_cache.DERIVED_DIR / "crawler"

CRAWLER_ENTRY = "0:1:1:746"
CRAWLER_BAND_MM = 50.0  # keep crawler faces whose lowest point is this close to the ground
TIP_SEARCH_MM = 120.0  # grouser tip planes (same as derive_crawler_cache.py)
DOWN_NORMAL_Y = -0.99  # downward plane: outward normal y_cad below this
ZERO_VOLUME_MM3 = 1e-3  # parts.csv volume at or below this: zero-volume part
ALIGNED_TOLERANCE = 1e-9  # rotation entries within this of 0 or +-1: axis-aligned
FLOAT_FORMAT = "%.10g"
OUTWARD_SAMPLE = 3000  # faces in the point-in-solid orientation check
OUTWARD_STEP_MM = 0.05
OUTWARD_SEED = 20261020

# CAD -> body axes (x = +Z_cad, y = +X_cad, z = +Y_cad), CAD origin.
CAD_TO_BODY = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

KIND_NAMES = {
    GeomAbs_Plane: "plane",
    GeomAbs_Cylinder: "cylinder",
    GeomAbs_Cone: "cone",
    GeomAbs_Sphere: "sphere",
    GeomAbs_Torus: "torus",
    GeomAbs_BezierSurface: "bezier",
    GeomAbs_BSplineSurface: "bspline",
    GeomAbs_SurfaceOfRevolution: "revolution",
    GeomAbs_SurfaceOfExtrusion: "extrusion",
    GeomAbs_OffsetSurface: "offset",
    GeomAbs_OtherSurface: "other",
}

XYZ = ("x", "y", "z")
# Vector quantities of a face row: name -> (is a point, unit suffix).
POINT_FIELDS = ("centroid", "axis_point")
DIRECTION_FIELDS = ("normal", "axis")


def log(message: str) -> None:
    rss_gb = psutil.Process().memory_info().rss / 1e9
    line = f"[{time.strftime('%H:%M:%S')} | rss {rss_gb:5.2f} GB] {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def peak_memory_gb() -> float:
    return psutil.Process().memory_info().peak_wset / 1e9


# --------------------------------------------------------------------------
# One face (prototype frame)
# --------------------------------------------------------------------------
def _bbox(shape: TopoDS_Shape, optimal: bool = True) -> tuple[float, ...]:
    box = Bnd_Box()
    if optimal:
        brepbndlib.AddOptimal(shape, box, False, False)
    else:
        brepbndlib.Add(shape, box, False)
    return box.Get()


def _xyz(vector) -> tuple[float, float, float]:
    return (vector.X(), vector.Y(), vector.Z())


def _axis_fields(position, centroid: np.ndarray, centre_only: bool = False) -> dict:
    """Axis direction and the centroid projected on the axis (or the centre)."""
    direction = np.array(_xyz(position.Direction()))
    origin = np.array(_xyz(position.Location()))
    point = origin if centre_only else origin + direction * float((centroid - origin) @ direction)
    return {"axis": direction, "axis_point": point}


def analyze_face(face: TopoDS_Face, bbox: tuple[float, ...] | None = None) -> dict:
    """Kind, area, centroid, normal or axis, radius and bbox of one face (shape frame, mm)."""
    surface = BRepAdaptor_Surface(face, True)
    surface_type = surface.GetType()
    reversed_face = face.Orientation() == TopAbs_REVERSED
    properties = GProp_GProps()
    brepgprop.SurfaceProperties(face, properties)
    area = properties.Mass()
    box = bbox if bbox is not None else _bbox(face)
    if area > 0.0:
        centroid = np.array(_xyz(properties.CentreOfMass()))
    else:  # degenerate face: bbox centre
        centroid = (np.array(box[:3]) + np.array(box[3:])) / 2
    row = {
        "kind": KIND_NAMES.get(surface_type, str(surface_type)),
        "reversed": reversed_face,
        "area_mm2": area,
        "centroid": centroid,
        "normal": np.full(3, np.nan),
        "axis": np.full(3, np.nan),
        "axis_point": np.full(3, np.nan),
        "radius_mm": np.nan,
        "radius2_mm": np.nan,
        "cone_half_angle_rad": np.nan,
        "convex": None,
        "bbox": box,
    }
    position = None
    if surface_type == GeomAbs_Plane:
        position = surface.Plane().Position()
        normal = np.array(_xyz(position.XDirection().Crossed(position.YDirection())))
        row["normal"] = -normal if reversed_face else normal
    elif surface_type == GeomAbs_Cylinder:
        cylinder = surface.Cylinder()
        position = cylinder.Position()
        row.update(_axis_fields(position, centroid), radius_mm=cylinder.Radius())
    elif surface_type == GeomAbs_Cone:
        cone = surface.Cone()
        position = cone.Position()
        row.update(
            _axis_fields(position, centroid),
            radius_mm=cone.RefRadius(),
            cone_half_angle_rad=cone.SemiAngle(),
        )
    elif surface_type == GeomAbs_Sphere:
        sphere = surface.Sphere()
        position = sphere.Position()
        row.update(_axis_fields(position, centroid, centre_only=True), radius_mm=sphere.Radius())
    elif surface_type == GeomAbs_Torus:
        torus = surface.Torus()
        position = torus.Position()
        row.update(
            _axis_fields(position, centroid),
            radius_mm=torus.MajorRadius(),
            radius2_mm=torus.MinorRadius(),
        )
    if position is not None and surface_type != GeomAbs_Plane:
        # The parametric normal of a direct frame points away from the axis.
        row["convex"] = bool(position.Direct()) != reversed_face
    return row


def check_normal(face: TopoDS_Face, row: dict) -> bool | None:
    """Independent check: oriented surface normal at the UV centre vs the row.

    Planes: the normal must equal ``row["normal"]``. Cylinders: the radial
    component must point away from the axis exactly when ``convex``.
    Returns None for other kinds or an undefined normal.
    """
    if row["kind"] not in ("plane", "cylinder"):
        return None
    surface = BRepAdaptor_Surface(face, True)
    u_min, u_max, v_min, v_max = breptools.UVBounds(face)
    u, v = (u_min + u_max) / 2, (v_min + v_max) / 2
    props = BRepLProp_SLProps(surface, u, v, 1, 1e-9)
    if not props.IsNormalDefined():
        return None
    normal = np.array(_xyz(props.Normal()))
    if row["reversed"]:
        normal = -normal
    if row["kind"] == "plane":
        return bool(normal @ row["normal"] > 1 - 1e-9)
    point = np.array(_xyz(props.Value()))
    radial = point - row["axis_point"]
    radial -= row["axis"] * float(radial @ row["axis"])
    return bool(normal @ radial > 0) == row["convex"]


# --------------------------------------------------------------------------
# Prototype pass
# --------------------------------------------------------------------------
def _face_solid_map(
    shape: TopoDS_Shape,
) -> tuple[TopTools_IndexedMapOfShape, dict[int, int], set[int]]:
    """Unique-face map, face map index -> first solid index, indices of invalid solids."""
    face_map = TopTools_IndexedMapOfShape()
    topexp.MapShapes(shape, TopAbs_FACE, face_map)
    solid_map = TopTools_IndexedMapOfShape()
    topexp.MapShapes(shape, TopAbs_SOLID, solid_map)
    solid_of: dict[int, int] = {}
    invalid: set[int] = set()
    for solid_index in range(solid_map.Size()):
        solid = solid_map.FindKey(solid_index + 1)
        if not BRepCheck_Analyzer(solid).IsValid():
            invalid.add(solid_index)
        explorer = TopExp_Explorer(solid, TopAbs_FACE)
        while explorer.More():
            solid_of.setdefault(face_map.FindIndex(explorer.Current()), solid_index)
            explorer.Next()
    return face_map, solid_of, invalid


def _iter_faces(shape: TopoDS_Shape):
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        yield topods.Face(explorer.Current())
        explorer.Next()


def _shape_area(shape: TopoDS_Shape) -> float:
    properties = GProp_GProps()
    brepgprop.SurfaceProperties(shape, properties)
    return properties.Mass()


class CrawlerSelector:
    """Decides which crawler faces enter the index (CAD world ground level)."""

    def __init__(self, instance: brep_cache.Instance, ground_y_mm: float, keep_all: bool):
        self.rotation = np.reshape(instance.matrix, (3, 4))[:, :3]
        self.translation = np.reshape(instance.matrix, (3, 4))[:, 3]
        self.ground_y_mm = ground_y_mm
        self.keep_all = keep_all

    def world_min_y(self, bbox: tuple[float, ...]) -> float:
        corners = np.array(np.meshgrid(*zip(bbox[:3], bbox[3:], strict=True))).reshape(3, -1)
        return float((self.rotation @ corners)[1].min() + self.translation[1])

    def selection(self, row: dict) -> str | None:
        """``ground_band``, ``grouser_tip``, ``all`` (keep-all mode) or None (excluded)."""
        height = self.world_min_y(row["bbox"]) - self.ground_y_mm
        if height <= CRAWLER_BAND_MM:
            return "ground_band"
        normal_y = (self.rotation @ row["normal"])[1] if row["kind"] == "plane" else np.nan
        if normal_y < DOWN_NORMAL_Y and height <= TIP_SEARCH_MM:
            return "grouser_tip"
        return "all" if self.keep_all else None


def analyze_prototype(entry: str, selector: CrawlerSelector | None, stats: dict) -> tuple:
    """Face rows and face shapes of one prototype (prototype frame)."""
    shape = brep_cache.load_prototype(entry)
    face_map, solid_of, invalid_solids = _face_solid_map(shape)
    rows, faces = [], []
    area_sum = 0.0
    explorer_faces = 0
    excluded: dict[str, int] = {}
    excluded_area = 0.0
    normal_checks = {"checked": 0, "failed": 0}
    for face_index, face in enumerate(_iter_faces(shape)):
        explorer_faces += 1
        if selector is None:
            row = analyze_face(face)
            selection = "all"
        else:
            # Cheap conservative bbox first; exact bbox only for kept faces.
            row = analyze_face(face, bbox=_bbox(face, optimal=False))
            selection = selector.selection(row)
            if selection is not None:
                row = analyze_face(face)
                selection = selector.selection(row)  # re-test with the exact bbox
        area_sum += row["area_mm2"]
        if selection is None:
            excluded[row["kind"]] = excluded.get(row["kind"], 0) + 1
            excluded_area += row["area_mm2"]
            continue
        result = check_normal(face, row)
        if result is not None:
            normal_checks["checked"] += 1
            normal_checks["failed"] += int(not result)
        row.update(
            prototype_entry=entry,
            face_index=face_index,
            solid_index=solid_of.get(face_map.FindIndex(face), -1),
            solid_valid=solid_of.get(face_map.FindIndex(face), -1) not in invalid_solids,
            selection=selection,
        )
        rows.append(row)
        faces.append(face)
    shape_area = _shape_area(shape)
    stats[entry] = {
        "explorer_faces": explorer_faces,
        "unique_faces": face_map.Size(),
        "kept_faces": len(rows),
        "excluded_faces_by_kind": excluded,
        "excluded_area_mm2": excluded_area,
        "face_area_sum_mm2": area_sum,
        "shape_area_mm2": shape_area,
        "area_relative_difference": abs(area_sum - shape_area) / shape_area if shape_area else 0.0,
        "normal_checks": normal_checks,
    }
    return rows, faces


def _flatten(rows: list[dict], frame_suffix: str = "_mm") -> pd.DataFrame:
    """Rows with vector fields -> DataFrame with x/y/z columns (prototype frame)."""
    table: dict[str, object] = {
        "prototype_entry": [row["prototype_entry"] for row in rows],
        "face_index": [row["face_index"] for row in rows],
        "solid_index": [row["solid_index"] for row in rows],
        "solid_valid": [row["solid_valid"] for row in rows],
        "selection": [row["selection"] for row in rows],
        "kind": [row["kind"] for row in rows],
        "reversed": [row["reversed"] for row in rows],
        "area_mm2": [row["area_mm2"] for row in rows],
    }
    for field in POINT_FIELDS + DIRECTION_FIELDS:
        values = np.array([row[field] for row in rows]).reshape(-1, 3)
        suffix = frame_suffix if field in POINT_FIELDS else ""
        for axis, column in zip(XYZ, values.T, strict=True):
            table[f"{field}_{axis}{suffix}"] = column
    for name in ("radius_mm", "radius2_mm", "cone_half_angle_rad", "convex"):
        table[name] = [row[name] for row in rows]
    boxes = np.array([row["bbox"] for row in rows]).reshape(-1, 6)
    for i, bound in enumerate(("min", "max")):
        for j, axis in enumerate(XYZ):
            table[f"bbox_{bound}_{axis}_mm"] = boxes[:, 3 * i + j]
    return pd.DataFrame(table)


# --------------------------------------------------------------------------
# Instance pass
# --------------------------------------------------------------------------
def _is_axis_aligned(rotation: np.ndarray) -> bool:
    magnitude = np.abs(rotation)
    return bool(
        np.all((magnitude < ALIGNED_TOLERANCE) | (np.abs(magnitude - 1) < ALIGNED_TOLERANCE))
    )


def _world_bbox(proto: pd.DataFrame, rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    """AABB of the transformed prototype boxes (exact for axis-aligned rotations)."""
    low = proto[[f"bbox_min_{a}_mm" for a in XYZ]].to_numpy()
    high = proto[[f"bbox_max_{a}_mm" for a in XYZ]].to_numpy()
    centre, half = (low + high) / 2, (high - low) / 2
    centre_world = centre @ rotation.T + translation
    half_world = half @ np.abs(rotation).T
    return np.hstack([centre_world - half_world, centre_world + half_world])


def _instance_rows(
    proto: pd.DataFrame,
    faces: list[TopoDS_Face],
    instance: brep_cache.Instance,
    flags: dict,
) -> pd.DataFrame:
    matrix = np.reshape(instance.matrix, (3, 4))
    rotation, translation = matrix[:, :3], matrix[:, 3]
    path_parts = instance.instance_path.split(" / ")
    out = pd.DataFrame(
        {
            "instance_path": instance.instance_path,
            "prototype_entry": instance.prototype_entry,
            "product_name": instance.product_name,
            "top_assembly": instance.top_assembly,
            "parent_assembly": path_parts[-2] if len(path_parts) > 1 else "",
        },
        index=range(len(proto)),
    )
    for name in (
        "face_index",
        "solid_index",
        "solid_valid",
        "selection",
        "kind",
        "reversed",
        "area_mm2",
    ):
        out[name] = proto[name].to_numpy()
    for field in POINT_FIELDS + DIRECTION_FIELDS:
        suffix = "_mm" if field in POINT_FIELDS else ""
        local = proto[[f"{field}_{a}{suffix}" for a in XYZ]].to_numpy()
        world = local @ rotation.T + (translation if field in POINT_FIELDS else 0.0)
        body = world @ CAD_TO_BODY.T / (MM_PER_M if field in POINT_FIELDS else 1.0)
        for i, axis in enumerate(XYZ):
            out[f"{field}_{axis}_cad{suffix}"] = world[:, i]
        for i, axis in enumerate(XYZ):
            out[f"{field}_{axis}_body{'_m' if field in POINT_FIELDS else ''}"] = body[:, i]
    for name in ("radius_mm", "radius2_mm", "cone_half_angle_rad", "convex"):
        out[name] = proto[name].to_numpy()
    aligned = _is_axis_aligned(rotation)
    if aligned:
        boxes = _world_bbox(proto, rotation, translation)
    else:
        location = TopLoc_Location(instance.trsf())
        boxes = np.array([_bbox(face.Moved(location)) for face in faces]).reshape(-1, 6)
    for i, bound in enumerate(("min", "max")):
        for j, axis in enumerate(XYZ):
            out[f"bbox_{bound}_{axis}_cad_mm"] = boxes[:, 3 * i + j]
    low_body = boxes[:, :3] @ CAD_TO_BODY.T / MM_PER_M
    high_body = boxes[:, 3:] @ CAD_TO_BODY.T / MM_PER_M
    for j, axis in enumerate(XYZ):
        out[f"bbox_min_{axis}_body_m"] = low_body[:, j]
    for j, axis in enumerate(XYZ):
        out[f"bbox_max_{axis}_body_m"] = high_body[:, j]
    out["bbox_recomputed"] = not aligned
    out["normal_uncertain"] = (
        flags["zero_volume"] | (out["solid_index"] < 0) | ~out["solid_valid"].astype(bool)
    )
    return out


def _zero_volume_entries() -> set[str]:
    parts = pd.read_csv(PARTS_CSV, encoding="utf-8-sig", usecols=["prototype_entry", "volume_mm3"])
    return set(parts.loc[parts["volume_mm3"].abs() <= ZERO_VOLUME_MM3, "prototype_entry"])


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def build(crawler_all: bool) -> dict:
    started = time.perf_counter()
    instances = brep_cache.instances()
    if any(item.is_mirrored for item in instances):
        raise ValueError("mirrored placements change face orientation; not supported")
    crawler_summary = json.loads((CRAWLER_DIR / "crawler_summary.json").read_text("utf-8"))
    ground_y_mm = float(crawler_summary["ground_y_mm"])
    crawler_instance = brep_cache.instances_of(CRAWLER_ENTRY)[0]
    selector = CrawlerSelector(crawler_instance, ground_y_mm, keep_all=crawler_all)
    zero_volume = _zero_volume_entries()

    entries = [row["prototype_entry"] for row in brep_cache.prototypes()]
    proto_rows: list[dict] = []
    proto_faces: dict[str, list[TopoDS_Face]] = {}
    stats: dict[str, dict] = {}
    for count, entry in enumerate(entries, start=1):
        is_crawler = entry == CRAWLER_ENTRY
        if is_crawler:
            log(f"crawler {entry}: selecting faces (ground Y {ground_y_mm:.4f} mm)")
        rows, faces = analyze_prototype(entry, selector if is_crawler else None, stats)
        proto_rows.extend(rows)
        proto_faces[entry] = faces
        if count % 100 == 0 or is_crawler:
            log(f"  {count}/{len(entries)} prototypes, {len(proto_rows)} face rows")
    prototype_seconds = time.perf_counter() - started

    proto = _flatten(proto_rows)
    proto["normal_uncertain"] = (
        proto["prototype_entry"].isin(zero_volume)
        | (proto["solid_index"] < 0)
        | ~proto["solid_valid"].astype(bool)
    )
    names = {row["prototype_entry"]: row["product_name"] for row in brep_cache.prototypes()}
    proto.insert(1, "product_name", proto["prototype_entry"].map(names))
    log(f"prototype pass {prototype_seconds:.1f} s, {len(proto)} rows")

    started_instances = time.perf_counter()
    groups = {entry: frame for entry, frame in proto.groupby("prototype_entry", sort=False)}
    pieces = []
    for instance in instances:
        # Prototypes without faces (empty bodies) give no rows.
        frame = groups.get(instance.prototype_entry, proto.iloc[0:0]).reset_index(drop=True)
        flags = {"zero_volume": instance.prototype_entry in zero_volume}
        pieces.append(_instance_rows(frame, proto_faces[instance.prototype_entry], instance, flags))
    index = pd.concat(pieces, ignore_index=True)
    instance_seconds = time.perf_counter() - started_instances
    log(f"instance pass {instance_seconds:.1f} s, {len(index)} rows")

    started_write = time.perf_counter()
    proto.to_csv(PROTOTYPE_FACES, index=False, float_format=FLOAT_FORMAT, encoding="utf-8")
    index.to_csv(INSTANCE_FACES, index=False, float_format=FLOAT_FORMAT, encoding="utf-8")
    write_seconds = time.perf_counter() - started_write
    log(f"wrote tables in {write_seconds:.1f} s")

    crawler_stats = stats[CRAWLER_ENTRY]
    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": "crawler_all" if crawler_all else "crawler_ground_band",
        "frames": {
            "prototype_faces": "prototype frame, mm",
            "instance_faces": "*_cad*: CAD world (mm, Y up); *_body*: body axes "
            "(x = +Z_cad, y = +X_cad, z = +Y_cad), CAD origin, m",
        },
        "counts": {
            "prototypes": len(entries),
            "instances": len(instances),
            "prototype_face_rows": len(proto),
            "instance_face_rows": len(index),
            "instance_face_rows_by_kind": index["kind"].value_counts().to_dict(),
            "instance_face_rows_by_selection": index["selection"].value_counts().to_dict(),
            "instance_rows_normal_uncertain": int(index["normal_uncertain"].sum()),
            "instance_rows_in_invalid_solids": int((~index["solid_valid"].astype(bool)).sum()),
            "prototypes_with_invalid_solids": proto.loc[
                ~proto["solid_valid"].astype(bool), "prototype_entry"
            ]
            .value_counts()
            .to_dict(),
            "instance_rows_outside_solids": int((index["solid_index"] < 0).sum()),
            "instance_rows_bbox_recomputed": int(index["bbox_recomputed"].sum()),
            "instances_not_axis_aligned": int(
                sum(not _is_axis_aligned(np.reshape(i.matrix, (3, 4))[:, :3]) for i in instances)
            ),
            "zero_volume_prototypes": sorted(zero_volume),
            "prototypes_without_faces": sorted(set(entries) - set(groups)),
            "instances_without_faces": sum(i.prototype_entry not in groups for i in instances),
            "prototypes_with_faces_outside_solids": proto.loc[
                proto["solid_index"] < 0, "prototype_entry"
            ]
            .value_counts()
            .to_dict(),
            "all_faces_if_crawler_complete": int(
                len(index) + sum(crawler_stats["excluded_faces_by_kind"].values())
            ),
        },
        "crawler": {
            "prototype_entry": CRAWLER_ENTRY,
            "instance_path": crawler_instance.instance_path,
            "note": "undercarriage of another model (REXOME25) per the STEP description",
            "ground_y_cad_mm": ground_y_mm,
            "ground_z_body_m": ground_y_mm / MM_PER_M,
            "band_mm": CRAWLER_BAND_MM,
            "grouser_tip_rule": f"plane, normal y_cad < {DOWN_NORMAL_Y}, "
            f"lowest point <= {TIP_SEARCH_MM} mm above ground",
            "explorer_faces": crawler_stats["explorer_faces"],
            "kept_faces": crawler_stats["kept_faces"],
            "kept_by_selection": index.loc[index["prototype_entry"] == CRAWLER_ENTRY, "selection"]
            .value_counts()
            .to_dict(),
            "excluded_faces": sum(crawler_stats["excluded_faces_by_kind"].values()),
            "excluded_faces_by_kind": crawler_stats["excluded_faces_by_kind"],
            "excluded_area_mm2": crawler_stats["excluded_area_mm2"],
            "include_all": "run build_face_index.py --crawler-all",
        },
        "timing_s": {
            "prototype_pass": round(prototype_seconds, 1),
            "instance_pass": round(instance_seconds, 1),
            "write": round(write_seconds, 1),
            "total": round(time.perf_counter() - started, 1),
        },
        "peak_memory_gb": round(peak_memory_gb(), 2),
        "files": {
            path.name: {"bytes": path.stat().st_size} for path in (PROTOTYPE_FACES, INSTANCE_FACES)
        },
        "provenance": {
            "cache": "01_cad/06_brep (prototypes.csv, instances.csv, prototypes/*.bbrep)",
            "prototypes_csv_sha256": sha256_file(brep_cache.PROTOTYPES_CSV),
            "instances_csv_sha256": sha256_file(brep_cache.INSTANCES_CSV),
            "crawler_summary_sha256": sha256_file(CRAWLER_DIR / "crawler_summary.json"),
            "script": Path(__file__).resolve().relative_to(PROJECT_ROOT).as_posix(),
            "script_sha256": sha256_file(Path(__file__)),
        },
        "prototype_stats": stats,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------
def _area_check(summary: dict) -> dict:
    stats = summary["prototype_stats"]
    worst = max(stats.items(), key=lambda item: item[1]["area_relative_difference"])
    normal_checked = sum(s["normal_checks"]["checked"] for s in stats.values())
    normal_failed = sum(s["normal_checks"]["failed"] for s in stats.values())
    return {
        "criterion": "sum of face areas vs BRepGProp SurfaceProperties(prototype), rel <= 1e-9",
        "prototypes": len(stats),
        "max_relative_difference": worst[1]["area_relative_difference"],
        "worst_prototype": worst[0],
        "passed": worst[1]["area_relative_difference"] <= 1e-9,
        "explorer_vs_unique_faces_differ": sorted(
            entry for entry, s in stats.items() if s["explorer_faces"] != s["unique_faces"]
        ),
        "normal_self_check": {
            "method": "BRepLProp_SLProps normal at UV centre, orientation applied "
            "(planes: equal normal; cylinders: radial sign vs convex)",
            "checked": normal_checked,
            "failed": normal_failed,
        },
    }


def _outward_check(sample_size: int = OUTWARD_SAMPLE, step_mm: float = OUTWARD_STEP_MM) -> dict:
    """Point-in-solid test: a point just outside along the normal is OUT, just inside is IN.

    Random planes and cylinders of valid solids (fixed seed, crawler excluded).
    The test point is the UV centre of the face if it lies on the face.
    """
    proto = pd.read_csv(PROTOTYPE_FACES, low_memory=False)
    candidates = proto[
        proto["kind"].isin(["plane", "cylinder"])
        & (proto["solid_index"] >= 0)
        & proto["solid_valid"].astype(bool)
        & (proto["prototype_entry"] != CRAWLER_ENTRY)
    ]
    sample = candidates.sample(min(sample_size, len(candidates)), random_state=OUTWARD_SEED)
    counts = {
        "sampled": len(sample),
        "tested": 0,
        "passed": 0,
        "reversed": 0,  # IN outside, OUT inside: normal points into the material
        "ambiguous": 0,  # both OUT (sheet, gap) or both IN (overlapping solids) at the step
        "skipped_off_face": 0,
    }
    failures = []
    for entry, rows in sample.groupby("prototype_entry"):
        shape = brep_cache.load_prototype(entry)
        faces = list(_iter_faces(shape))
        solid_map = TopTools_IndexedMapOfShape()
        topexp.MapShapes(shape, TopAbs_SOLID, solid_map)
        for row in rows.itertuples():
            face = faces[row.face_index]
            u_min, u_max, v_min, v_max = breptools.UVBounds(face)
            u, v = (u_min + u_max) / 2, (v_min + v_max) / 2
            if BRepTopAdaptor_FClass2d(face, 1e-7).Perform(gp_Pnt2d(u, v)) != TopAbs_IN:
                counts["skipped_off_face"] += 1
                continue
            surface = BRepAdaptor_Surface(face, True)
            props = BRepLProp_SLProps(surface, u, v, 1, 1e-9)
            point = np.array(_xyz(props.Value()))
            if row.kind == "plane":
                outward = np.array([row.normal_x, row.normal_y, row.normal_z])
            else:
                axis = np.array([row.axis_x, row.axis_y, row.axis_z])
                origin = (row.axis_point_x_mm, row.axis_point_y_mm, row.axis_point_z_mm)
                radial = point - np.array(origin)
                radial -= axis * float(radial @ axis)
                radial /= np.linalg.norm(radial)
                outward = radial if row.convex else -radial
            solid = solid_map.FindKey(row.solid_index + 1)
            states = []
            for sign in (1.0, -1.0):
                probe = gp_Pnt(*(point + sign * step_mm * outward))
                states.append(BRepClass3d_SolidClassifier(solid, probe, 1e-7).State())
            counts["tested"] += 1
            if states == [TopAbs_OUT, TopAbs_IN]:
                counts["passed"] += 1
                continue
            outcome = "reversed" if states == [TopAbs_IN, TopAbs_OUT] else "ambiguous"
            counts[outcome] += 1
            if len(failures) < 20:
                failures.append(
                    {
                        "prototype_entry": entry,
                        "face_index": int(row.face_index),
                        "outcome": outcome,
                    }
                )
    counts["failed_examples"] = failures
    counts["method"] = (
        f"BRepClass3d_SolidClassifier at the face UV centre +- {step_mm} mm along the "
        "outward direction (plane normal; cylinder radial by 'convex'); expect OUT / IN"
    )
    return counts


def _compare_table(index: pd.DataFrame, path: Path, by_solid: bool) -> dict:
    """Row-by-row comparison with an older per-instance face table (world mm)."""
    old = pd.read_csv(path, encoding="utf-8-sig")
    old["kind"] = old["surface_type"].replace({"bspline_surface": "bspline"})
    new = index[index["instance_path"].isin(set(old["instance_path"]))]
    sort_keys = ["instance_path", "solid_index", "face_index"] if by_solid else None
    if sort_keys:
        new = new.sort_values(sort_keys, kind="stable")
    result = {
        "file": path.relative_to(PROJECT_ROOT).as_posix(),
        "old_rows": len(old),
        "new_rows": len(new),
        "instances": int(old["instance_path"].nunique()),
    }
    old_counts = old.groupby("instance_path", sort=False).size()
    new_counts = new.groupby("instance_path", sort=False).size()
    mismatched = (old_counts - new_counts.reindex(old_counts.index)).abs() > 0
    result["instances_with_count_mismatch"] = int(mismatched.sum())
    if mismatched.any():
        return result
    # Same instance order as the old file, faces in the old table order.
    order = {path_name: i for i, path_name in enumerate(old["instance_path"].unique())}
    new = new.assign(_o=new["instance_path"].map(order)).sort_values("_o", kind="stable")
    new = new.reset_index(drop=True)
    old = old.reset_index(drop=True)
    result["kind_mismatch"] = int((old["kind"] != new["kind"]).sum())
    result["max_area_relative_difference"] = float(
        ((old["area_mm2"] - new["area_mm2"]).abs() / old["area_mm2"].abs().clip(lower=1e-12)).max()
    )
    old_box = old[[f"bbox_{b}_{a}_mm" for b in ("min", "max") for a in XYZ]].to_numpy()
    new_box = new[[f"bbox_{b}_{a}_cad_mm" for b in ("min", "max") for a in XYZ]].to_numpy()
    result["max_bbox_abs_difference_mm"] = float(np.abs(old_box - new_box).max())
    old_centre = (old_box[:, :3] + old_box[:, 3:]) / 2
    new_centre = (new_box[:, :3] + new_box[:, 3:]) / 2
    result["max_bbox_centre_difference_mm"] = float(
        np.linalg.norm(old_centre - new_centre, axis=1).max()
    )
    centroid = new[[f"centroid_{a}_cad_mm" for a in XYZ]].to_numpy()
    inside = np.all(
        (centroid >= old_box[:, :3] - 1e-6) & (centroid <= old_box[:, 3:] + 1e-6), axis=1
    )
    curved = ~new["kind"].isin(["plane"]).to_numpy()
    result["centroid_outside_old_bbox_planes"] = int((~inside & ~curved).sum())
    old_vec = old[[f"axis_or_normal_{a}" for a in XYZ]].to_numpy()
    planes = (new["kind"] == "plane").to_numpy()
    new_normal = new[[f"normal_{a}_cad" for a in XYZ]].to_numpy()
    dot = np.einsum("ij,ij->i", old_vec[planes], new_normal[planes])
    result["planes"] = int(planes.sum())
    result["plane_normal_max_angle_deg_ignoring_sign"] = float(
        np.degrees(np.arccos(np.clip(np.abs(dot), -1, 1))).max()
    )
    result["plane_normal_opposite_to_old"] = int((dot < 0).sum())
    cylinders = (new["kind"] == "cylinder").to_numpy()
    new_axis = new[[f"axis_{a}_cad" for a in XYZ]].to_numpy()
    axis_dot = np.abs(np.einsum("ij,ij->i", old_vec[cylinders], new_axis[cylinders]))
    result["cylinders"] = int(cylinders.sum())
    if cylinders.any():
        angle = np.degrees(np.arccos(np.clip(axis_dot, -1, 1)))
        radius_old = old.loc[cylinders, "radius_mm"].to_numpy()
        radius_new = new.loc[cylinders, "radius_mm"].to_numpy()
        result["cylinder_axis_max_angle_deg"] = float(angle.max())
        result["cylinder_radius_max_difference_mm"] = float(np.abs(radius_old - radius_new).max())
    if "axis_point_x_mm" in old.columns and cylinders.any():
        old_point = old.loc[cylinders, [f"axis_point_{a}_mm" for a in XYZ]].to_numpy()
        new_point = new.loc[cylinders, [f"axis_point_{a}_cad_mm" for a in XYZ]].to_numpy()
        offset = old_point - new_point
        offset -= new_axis[cylinders] * np.einsum("ij,ij->i", offset, new_axis[cylinders])[:, None]
        result["cylinder_axis_line_max_distance_mm"] = float(np.linalg.norm(offset, axis=1).max())
    if "solid_index" in old.columns:
        result["solid_index_mismatch"] = int(
            (old["solid_index"].to_numpy() != new["solid_index"].to_numpy()).sum()
        )
    return result


def _grouser_check(index: pd.DataFrame, ground_y_mm: float) -> dict:
    from scipy.spatial import cKDTree

    old = pd.read_csv(CRAWLER_DIR / "crawler_grouser_tips.csv", encoding="utf-8-sig")
    new = index[(index["prototype_entry"] == CRAWLER_ENTRY) & (index["kind"] == "plane")]
    new = new[new["normal_y_cad"] < DOWN_NORMAL_Y]
    new = new[new["bbox_min_y_cad_mm"] - ground_y_mm <= TIP_SEARCH_MM]
    old_centroid = old[[f"centroid_{a}_mm" for a in XYZ]].to_numpy()
    new_centroid = new[[f"centroid_{a}_cad_mm" for a in XYZ]].to_numpy()
    distance, nearest = cKDTree(new_centroid).query(old_centroid)
    matched = new.iloc[nearest]
    plane_height_new = matched["centroid_y_cad_mm"].to_numpy() - ground_y_mm
    ground_level = new[new["centroid_y_cad_mm"] - ground_y_mm <= 1.0]
    return {
        "old_rows": len(old),
        "new_downward_planes_within_120mm": len(new),
        "max_centroid_distance_mm": float(distance.max()),
        "max_area_relative_difference": float(
            (
                np.abs(old["area_mm2"].to_numpy() - matched["area_mm2"].to_numpy())
                / old["area_mm2"]
            ).max()
        ),
        "max_plane_height_difference_mm": float(
            np.abs(old["plane_height_mm"].to_numpy() - plane_height_new).max()
        ),
        "ground_level_tips_new": len(ground_level),
        "ground_level_tips_old": int((old["plane_height_mm"] <= 1.0).sum()),
        "ground_level_tip_z_body_m": [
            float(ground_level["centroid_z_body_m"].min()),
            float(ground_level["centroid_z_body_m"].max()),
        ],
        "ground_z_body_m": ground_y_mm / MM_PER_M,
        "ground_level_tip_x_body_m": [
            float(ground_level["bbox_min_x_body_m"].min()),
            float(ground_level["bbox_max_x_body_m"].max()),
        ],
    }


def _imu_and_timing() -> dict:
    import face_index

    started = time.perf_counter()
    face_index.load.cache_clear()
    table = face_index.load()
    load_seconds = time.perf_counter() - started
    c1_window = ((0.24, 0.475, 0.035), (0.44, 1.215, 0.045))
    timings = {}
    started = time.perf_counter()
    c1 = face_index.query(
        kind="plane", normal_body=(0, 0, 1), tol_deg=1.0, bbox=c1_window, bbox_mode="overlap"
    )
    timings["imu_c1_plane_up_in_window"] = time.perf_counter() - started
    started = time.perf_counter()
    upward = face_index.query(kind="plane", normal_body=(0, 0, 1), tol_deg=5, area_min_mm2=1e4)
    timings["all_upward_planes_area_ge_1e4"] = time.perf_counter() - started
    started = time.perf_counter()
    pins = face_index.query(kind="cylinder", axis_body=(0, 1, 0), tol_deg=1, convex=False)
    timings["holes_with_axis_along_body_y"] = time.perf_counter() - started
    columns = [
        "instance_path",
        "face_index",
        "area_mm2",
        "centroid_x_body_m",
        "centroid_y_body_m",
        "centroid_z_body_m",
        "bbox_min_x_body_m",
        "bbox_max_x_body_m",
        "bbox_min_y_body_m",
        "bbox_max_y_body_m",
        "bbox_min_z_body_m",
        "bbox_max_z_body_m",
    ]
    return {
        "rows_loaded": len(table),
        "load_seconds": round(load_seconds, 3),
        "imu_c1": {
            "query": "kind=plane, normal_body=(0,0,1), tol 1 deg, bbox overlap "
            "x 0.24..0.44, y 0.475..1.215, z 0.035..0.045 m",
            "hits": len(c1),
            "faces": c1[columns].to_dict(orient="records"),
            "passed": bool(
                len(c1) > 0 and np.allclose(c1["centroid_z_body_m"].to_numpy(), 0.040, atol=1e-6)
            ),
        },
        "query_seconds": {name: round(value, 4) for name, value in timings.items()},
        "query_hits": {
            "all_upward_planes_area_ge_1e4": len(upward),
            "holes_with_axis_along_body_y": len(pins),
        },
    }


def verify(summary: dict) -> dict:
    log("verification")
    index = pd.read_csv(INSTANCE_FACES, low_memory=False)
    ground_y_mm = summary["crawler"]["ground_y_cad_mm"]
    report = {
        "area": _area_check(summary),
        "outward": _outward_check(),
        "legs": _compare_table(index, LEGS_DIR / "leg_faces.csv", by_solid=False),
        "mast": _compare_table(index, MAST_DIR / "mast_faces.csv", by_solid=True),
        "crawler_grouser_tips": _grouser_check(index, ground_y_mm),
        "query": _imu_and_timing(),
    }
    report["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    VERIFICATION_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"wrote {VERIFICATION_JSON.name}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--crawler-all", action="store_true", help="index every crawler face")
    parser.add_argument("--verify-only", action="store_true", help="re-run the verification")
    arguments = parser.parse_args()
    FACES_DIR.mkdir(parents=True, exist_ok=True)
    if arguments.verify_only:
        summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    else:
        LOG_PATH.write_text("", encoding="utf-8")
        summary = build(arguments.crawler_all)
    verify(summary)
    log(f"done, peak memory {peak_memory_gb():.2f} GB")
    print("next: python -I 04_scripts/00_cad/check_cache.py --write --cache 07_faces")


if __name__ == "__main__":
    main()
