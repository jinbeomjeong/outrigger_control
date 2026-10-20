"""Export the outrigger jack cylinders and tabulate their faces.

The user identified ``FRONT JACK CYL`` as the hydraulic outrigger cylinder;
``REAR JACK CYL`` is its rear counterpart. This script reads the STEP file
(about 2 min), keeps only occurrences whose path matches ``--pattern``, and
writes:

* ``01_cad/02_legs/legs/<occurrence>.brep``: each solid already placed in world
  coordinates (small files, reusable without re-reading the STEP file).
* ``01_cad/02_legs/leg_faces.csv``: one row per face with surface type, cylinder radius
  and axis, area and world bounding box, used to tell barrel, rod and pad apart
  and to estimate the stroke.

``--from-brep`` rebuilds only ``01_cad/02_legs/leg_faces.csv`` from the cached BREP files
(seconds, no STEP read); it reuses the occurrence paths of the existing table.

Usage:
    python -I 04_scripts/00_cad/inspect_legs.py [--force] [--pattern REGEX]
    python -I 04_scripts/00_cad/inspect_legs.py --from-brep
"""

import argparse
import csv
import math
import re
import sys
import time
from pathlib import Path

from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepTools import breptools
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
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Shape, topods
from OCC.Core.XCAFDoc import XCAFDoc_ShapeTool

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad_common import LEGS_DIR, STEP_PATH
from extract_parts import collect_occurrences, load_document

DEFAULT_PATTERN = r"JACK CYL"
LEG_BREP_DIR = LEGS_DIR / "legs"
LEG_FACES_CSV = LEGS_DIR / "leg_faces.csv"
# Every GeomAbs_SurfaceType value; unknown values still fall back to str().
SURFACE_TYPE_NAMES = {
    GeomAbs_Plane: "plane",
    GeomAbs_Cylinder: "cylinder",
    GeomAbs_Cone: "cone",
    GeomAbs_Sphere: "sphere",
    GeomAbs_Torus: "torus",
    GeomAbs_BezierSurface: "bezier_surface",
    GeomAbs_BSplineSurface: "bspline_surface",
    GeomAbs_SurfaceOfRevolution: "surface_of_revolution",
    GeomAbs_SurfaceOfExtrusion: "surface_of_extrusion",
    GeomAbs_OffsetSurface: "offset_surface",
    GeomAbs_OtherSurface: "other_surface",
}


def _safe_file_stem(path_names: list[str]) -> str:
    joined = "__".join(path_names[1:])
    return re.sub(r"[^0-9A-Za-z_.-]+", "_", joined).strip("_")


def _face_rows(occurrence_path: str, shape: TopoDS_Shape) -> list[dict]:
    rows = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        surface = BRepAdaptor_Surface(face, True)
        surface_type = surface.GetType()
        radius_mm, axis = math.nan, (math.nan,) * 3
        if surface_type == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            radius_mm = cylinder.Radius()
            direction = cylinder.Axis().Direction()
            axis = (direction.X(), direction.Y(), direction.Z())
        elif surface_type == GeomAbs_Plane:
            direction = surface.Plane().Axis().Direction()
            axis = (direction.X(), direction.Y(), direction.Z())
        properties = GProp_GProps()
        brepgprop.SurfaceProperties(face, properties)
        box = Bnd_Box()
        brepbndlib.AddOptimal(face, box, False, False)
        x_min, y_min, z_min, x_max, y_max, z_max = box.Get()
        rows.append(
            {
                "instance_path": occurrence_path,
                "surface_type": SURFACE_TYPE_NAMES.get(surface_type, str(surface_type)),
                "radius_mm": radius_mm,
                "axis_or_normal_x": axis[0],
                "axis_or_normal_y": axis[1],
                "axis_or_normal_z": axis[2],
                "area_mm2": properties.Mass(),
                "bbox_min_x_mm": x_min,
                "bbox_min_y_mm": y_min,
                "bbox_min_z_mm": z_min,
                "bbox_max_x_mm": x_max,
                "bbox_max_y_mm": y_max,
                "bbox_max_z_mm": z_max,
            }
        )
    return rows


def export_legs(pattern: str) -> None:
    """Write world-placed BREP files and the face table for matching parts."""
    document = load_document(STEP_PATH)
    matcher = re.compile(pattern)
    LEG_BREP_DIR.mkdir(parents=True, exist_ok=True)
    face_rows: list[dict] = []
    for occurrence in collect_occurrences(document):
        occurrence_path = " / ".join(occurrence.names)
        if not matcher.search(occurrence_path):
            continue
        shape = XCAFDoc_ShapeTool.GetShape(occurrence.prototype).Moved(
            occurrence.location
        )
        brep_path = LEG_BREP_DIR / f"{_safe_file_stem(occurrence.names)}.brep"
        breptools.Write(shape, str(brep_path))
        face_rows.extend(_face_rows(occurrence_path, shape))
        print(f"exported {brep_path.name}", flush=True)
    if not face_rows:
        raise SystemExit(f"no occurrence matched {pattern!r}")
    _write_face_table(face_rows)


def _write_face_table(face_rows: list[dict]) -> None:
    with LEG_FACES_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(face_rows[0]))
        writer.writeheader()
        writer.writerows(face_rows)


def rebuild_faces_from_brep() -> None:
    """Rewrite the face table from the cached BREP files, without the STEP file.

    The occurrence paths (and their order) are taken from the existing face
    table, because the BREP file names drop the root name and non-ASCII text.
    The BREP shapes are already placed in world coordinates.
    """
    if not LEG_FACES_CSV.exists():
        raise SystemExit(f"{LEG_FACES_CSV} is needed for the occurrence paths")
    with LEG_FACES_CSV.open(encoding="utf-8-sig", newline="") as handle:
        occurrence_paths = list(
            dict.fromkeys(row["instance_path"] for row in csv.DictReader(handle))
        )
    face_rows: list[dict] = []
    for occurrence_path in occurrence_paths:
        names = occurrence_path.split(" / ")
        brep_path = LEG_BREP_DIR / f"{_safe_file_stem(names)}.brep"
        shape = TopoDS_Shape()
        if not breptools.Read(shape, str(brep_path), BRep_Builder()):
            raise SystemExit(f"cannot read {brep_path}")
        face_rows.extend(_face_rows(occurrence_path, shape))
        print(f"read {brep_path.name}", flush=True)
    _write_face_table(face_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-export if cached")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help="path regex")
    parser.add_argument(
        "--from-brep",
        action="store_true",
        help="rebuild only the face table from 01_cad/02_legs/legs/*.brep (no STEP read)",
    )
    arguments = parser.parse_args()
    started_s = time.perf_counter()
    if arguments.from_brep:
        rebuild_faces_from_brep()
        print(f"done in {time.perf_counter() - started_s:.1f} s")
        return
    if LEG_FACES_CSV.exists() and not arguments.force:
        print(f"cached: {LEG_FACES_CSV} (use --force to rebuild)")
        return
    export_legs(arguments.pattern)
    print(f"done in {time.perf_counter() - started_s:.0f} s")


if __name__ == "__main__":
    main()
