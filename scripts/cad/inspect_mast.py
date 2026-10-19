"""Export the mast-mechanism parts and tabulate their faces with axis locations.

Reads the STEP file once (a few minutes), keeps the occurrences whose path
matches ``--pattern`` (mast, boom, backstay/boom cylinders, mast bracket,
winch, hose guide, base deck, and the parts the folded mast comes close to:
drive auger, roof cover, counterweight, centre deck cover by default) and writes:

* ``cad/mast/<occurrence>.brep``: each part placed in world (CAD) coordinates.
* ``cad/mast/index.json``: occurrence path -> BREP file, plus the STEP path,
  its modification time and the extraction pattern.
* ``cad/mast_faces.csv``: one row per face with surface type, radius, axis
  direction, a point on the axis (for cylinders), area and world bbox. The
  axis point is the projection of the face bbox centre onto the axis, so
  coaxial faces share the same coordinates across the axis direction.

``--from-brep`` rebuilds only the face table from the cached BREP files.

Frames: CAD root frame, mm, Y up (see docs/cad_review.md).

Usage:
    python -I scripts/cad/inspect_mast.py [--force] [--pattern REGEX]
    python -I scripts/cad/inspect_mast.py --from-brep
"""

import argparse
import csv
import json
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
from OCC.Core.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Shape, topods
from OCC.Core.XCAFDoc import XCAFDoc_ShapeTool

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cad_common import CAD_DIR, STEP_PATH
from extract_parts import collect_occurrences, load_document
from inspect_legs import SURFACE_TYPE_NAMES, _safe_file_stem

DEFAULT_PATTERN = (
    r"/ (MAST ASSY|BOOM|BACKSTAY CYL|BOOM CYL|MAST BK|윈치|Hose guide arm"
    r"|Hose guide CYL|BASE DECK|LOWER GUIDE_ASSY|0\. DRIVE AUGER ASSY|SIDE HOUSING_ROOF COVER"
    r"|COUNTER WEIGHT|CENTER DECK COVER_1):"
)
MAST_BREP_DIR = CAD_DIR / "mast"
MAST_INDEX_JSON = MAST_BREP_DIR / "index.json"
MAST_FACES_CSV = CAD_DIR / "mast_faces.csv"


def _face_rows(occurrence_path: str, shape: TopoDS_Shape) -> list[dict]:
    rows = []
    solid_explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    solids = []
    while solid_explorer.More():
        solids.append(solid_explorer.Current())
        solid_explorer.Next()
    if not solids:
        solids = [shape]
    for solid_index, solid in enumerate(solids):
        explorer = TopExp_Explorer(solid, TopAbs_FACE)
        while explorer.More():
            face = topods.Face(explorer.Current())
            explorer.Next()
            rows.append(_face_row(occurrence_path, solid_index, face))
    return rows


def _face_row(occurrence_path: str, solid_index: int, face) -> dict:
    surface = BRepAdaptor_Surface(face, True)
    surface_type = surface.GetType()
    box = Bnd_Box()
    brepbndlib.AddOptimal(face, box, False, False)
    x_min, y_min, z_min, x_max, y_max, z_max = box.Get()
    centre = ((x_min + x_max) / 2, (y_min + y_max) / 2, (z_min + z_max) / 2)
    radius_mm = math.nan
    axis = (math.nan,) * 3
    point = (math.nan,) * 3
    if surface_type == GeomAbs_Cylinder:
        cylinder = surface.Cylinder()
        radius_mm = cylinder.Radius()
        direction = cylinder.Axis().Direction()
        location = cylinder.Axis().Location()
        axis = (direction.X(), direction.Y(), direction.Z())
        origin = (location.X(), location.Y(), location.Z())
        along = sum((centre[i] - origin[i]) * axis[i] for i in range(3))
        point = tuple(origin[i] + along * axis[i] for i in range(3))
    elif surface_type == GeomAbs_Plane:
        direction = surface.Plane().Axis().Direction()
        axis = (direction.X(), direction.Y(), direction.Z())
    properties = GProp_GProps()
    brepgprop.SurfaceProperties(face, properties)
    return {
        "instance_path": occurrence_path,
        "solid_index": solid_index,
        "surface_type": SURFACE_TYPE_NAMES.get(surface_type, str(surface_type)),
        "radius_mm": radius_mm,
        "axis_or_normal_x": axis[0],
        "axis_or_normal_y": axis[1],
        "axis_or_normal_z": axis[2],
        "axis_point_x_mm": point[0],
        "axis_point_y_mm": point[1],
        "axis_point_z_mm": point[2],
        "area_mm2": properties.Mass(),
        "bbox_min_x_mm": x_min,
        "bbox_min_y_mm": y_min,
        "bbox_min_z_mm": z_min,
        "bbox_max_x_mm": x_max,
        "bbox_max_y_mm": y_max,
        "bbox_max_z_mm": z_max,
    }


def _write_face_table(face_rows: list[dict]) -> None:
    with MAST_FACES_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(face_rows[0]))
        writer.writeheader()
        writer.writerows(face_rows)


def export_parts(pattern: str) -> None:
    """Write world-placed BREP files, the index and the face table."""
    document = load_document(STEP_PATH)
    matcher = re.compile(pattern)
    MAST_BREP_DIR.mkdir(parents=True, exist_ok=True)
    index: dict[str, str] = {}
    face_rows: list[dict] = []
    for occurrence in collect_occurrences(document):
        occurrence_path = " / ".join(occurrence.names)
        if not matcher.search(occurrence_path):
            continue
        shape = XCAFDoc_ShapeTool.GetShape(occurrence.prototype).Moved(
            occurrence.location
        )
        stem = _safe_file_stem(occurrence.names) or "part"
        file_name = f"{stem}.brep"
        suffix = 1
        while file_name in index.values():
            suffix += 1
            file_name = f"{stem}__{suffix}.brep"
        breptools.Write(shape, str(MAST_BREP_DIR / file_name))
        index[occurrence_path] = file_name
        face_rows.extend(_face_rows(occurrence_path, shape))
    if not face_rows:
        raise SystemExit(f"no occurrence matched {pattern!r}")
    print(f"exported {len(index)} parts", flush=True)
    stat = STEP_PATH.stat()
    MAST_INDEX_JSON.write_text(
        json.dumps(
            {
                "step_path": str(STEP_PATH),
                "step_size_bytes": stat.st_size,
                "step_mtime": time.strftime(
                    "%Y-%m-%dT%H:%M:%S", time.localtime(stat.st_mtime)
                ),
                "pattern": pattern,
                "frame": "CAD root frame, mm, Y up; shapes already placed",
                "parts": index,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    _write_face_table(face_rows)


def rebuild_faces_from_brep() -> None:
    """Rewrite the face table from the cached BREP files (no STEP read)."""
    index = json.loads(MAST_INDEX_JSON.read_text(encoding="utf-8"))["parts"]
    face_rows: list[dict] = []
    for occurrence_path, file_name in index.items():
        shape = TopoDS_Shape()
        if not breptools.Read(shape, str(MAST_BREP_DIR / file_name), BRep_Builder()):
            raise SystemExit(f"cannot read {file_name}")
        face_rows.extend(_face_rows(occurrence_path, shape))
    _write_face_table(face_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-export if cached")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help="path regex")
    parser.add_argument(
        "--from-brep",
        action="store_true",
        help="rebuild only the face table from cad/mast/*.brep (no STEP read)",
    )
    arguments = parser.parse_args()
    started_s = time.perf_counter()
    if arguments.from_brep:
        rebuild_faces_from_brep()
    elif MAST_INDEX_JSON.exists() and not arguments.force:
        print(f"cached: {MAST_INDEX_JSON} (use --force to rebuild)")
        return
    else:
        export_parts(arguments.pattern)
    print(f"done in {time.perf_counter() - started_s:.0f} s")


if __name__ == "__main__":
    main()
