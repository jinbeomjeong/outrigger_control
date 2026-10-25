"""Write the pad-type table ``02_params/pad_variants.json`` and the C8 hulls of pad type A.

Pad area is an experiment variable with two types (user decisions U-PAD-1..6 2026-10-25,
``00_docs/01_dynamics/dynamics_model.md`` rev. 44 5.30, implementation (1) of 5.30.5):

* ``cad330``      type A: all four pads are the REXOME33 CAD pad (330 x 330, chamfer 30,
                  0.1071 m^2), B-rep ``01_cad/02_legs/legs/*_10_1.brep`` (= YAML today);
* ``dwg_rear250`` type B (**default**): front pads as CAD, rear pads REXOME35 drawing SECTION
                  A-A' 250 x 250 with the corner chamfer 30 mm **ASSUMPTION** (0.0607 m^2), from
                  the drawing-chain synthesis B-rep ``01_cad/02_legs/rexome35/moving_R{L,R}.brep``
                  (orientation of the CAD pad kept, ASSUMPTION).

The masses are not part of the table: type A uses the same moving-part / pad-body masses as
type B (U-PAD-3, only area and polygon change). The YAML ``02_params/rexome33.yaml`` is only
read (pad bottom centre, retracted offsets); it is never written here, so ``Params.sha256``
and ``file_sha256`` stay as they are. The table is a generated file (do not edit by hand);
it moves into a YAML block ``pad_shapes`` (excluded from the L1 / L2b fingerprint) at the next
YAML regeneration bundle (5.30.5 (3)).

Per leg and type: ``polygon_xy_m`` (bottom face outer wire relative to
``legs.<leg>.pad_bottom_center_retracted_m``, counter-clockwise from +z, body frame, 9
significant digits like the YAML), ``bottom_area_m2`` (B-rep face area), perimeter, Chrono SCM
Bekker width ``b = 2 A / perimeter`` (``vehicle_terrain.md`` 82-97), equivalent radius, side
angle, source B-rep (path, sha256), assumptions, and the C8 pad hull / simple visual OBJ
(existing ``01_cad/09_sim_shapes`` entries, or for the type A rear pads new OBJs under
``01_cad/09_sim_shapes/pad_variants/`` built here with the same recipe as
``build_sim_shapes.stage_legs``: convex hull of the bottom octagon, the side height and the
45 deg top chamfer, retracted state).

Frame: machine body axes (x forward = +Z_cad, y left = +X_cad, z up = +Y_cad), origin = CAD
origin, metres. CAD length unit mm (B-rep caches, mm -> m x 1e-3).

Usage (project root, Chrono-dev python):
    python -I 04_scripts/00_cad/export_pad_variants.py [--check]

``--check`` recomputes everything in memory and compares it with the written table (exit 1 on
difference); nothing is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_sim_shapes as bss  # noqa: E402
from build_sim_shapes import (  # noqa: E402
    CAD_TO_BODY,
    LEG_ORDER,
    MM,
    PROJECT_ROOT,
    ROD_PAD_BREP,
    bbox_cad_to_body_m,
    brep_props_body,
    cad_to_body_m,
    compare_props,
    inset_polygon,
    pad_bottom,
    polygon_area,
    read_ascii_brep,
    side_angle_deg,
    source_record,
    split_rod_pad,
    trimesh_props,
    volume_properties,
    write_obj,
)
from cad_common import LEGS_DIR  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "03_src"))
from outrigger_sim.params import DEFAULT_PARAMS_PATH, load_params  # noqa: E402

TABLE_JSON = PROJECT_ROOT / "02_params" / "pad_variants.json"
SIM_SHAPES_DIR = PROJECT_ROOT / "01_cad" / "09_sim_shapes"
SIM_SHAPES_INDEX = SIM_SHAPES_DIR / "sim_shapes.json"
VARIANT_SHAPES_DIR = SIM_SHAPES_DIR / "pad_variants"
CAD_BREP = {leg: LEGS_DIR / "legs" / ROD_PAD_BREP[leg] for leg in LEG_ORDER}
DRAWING_BREP = {leg: LEGS_DIR / "rexome35" / f"moving_{leg}.brep" for leg in ("RL", "RR")}
SCHEMA = 1
DEFAULT_VARIANT = "dwg_rear250"
SIGNIFICANT_DIGITS = 9
DRAWING_SIDE_MM = 250.0
DRAWING_CHAMFER_MM = 30.0  # ASSUMPTION: no chamfer dimension on the drawing (figure read 25 ... 30)
TOL = {
    "area_vs_polygon_rel": 1e-6,     # B-rep face area vs shoelace area of the outer wire
    "area_vs_drawing_rel": 1e-6,     # synthesis B-rep vs 250^2 - 2 x 30^2 mm^2
    "polygon_vs_yaml_m": 1e-9,       # type A polygon vs YAML legs.<leg>.pad.polygon_xy_m
    "area_vs_yaml_rel": 1e-9,        # type A area vs YAML legs.<leg>.pad.bottom_area_m2
    "centroid_vs_yaml_m": 1e-4,      # face centroid vs YAML pad_bottom_center (0.1 mm rounding)
    "bottom_z_vs_yaml_m": 1e-4,
    "hull_volume_rel": 1e-5,         # OBJ (6 decimals) vs B-rep plate, as verify_sim_shapes
    "hull_down_area_rel": 1e-6,
}
VARIANTS = {
    "cad330": {
        "label": "A",
        "description": "REXOME33 CAD pads on all four legs: 330 x 330, chamfer 30, 0.1071 m^2 (B-rep)",
        "sources": {leg: "cad" for leg in LEG_ORDER},
        "mass_note": "moving-part / pad-body masses as in the YAML (= type B rear 250 synthesis); "
                     "U-PAD-3: only area and polygon change",
    },
    "dwg_rear250": {
        "label": "B",
        "description": "front CAD 330 (drawing = CAD), rear REXOME35 drawing 250 x 250, chamfer 30 mm ASSUMPTION, "
                       "0.0607 m^2 (drawing-chain synthesis B-rep)",
        "sources": {"FL": "cad", "FR": "cad", "RL": "drawing", "RR": "drawing"},
        "mass_note": "moving-part / pad-body masses as in the YAML (rear: 250 pad synthesis)",
    },
}
SOURCE_TEXT = {
    "cad": "REXOME33 CAD B-rep 01_cad/02_legs/legs/<leg>_10_1.brep, lowest -Y_cad plane (outer wire)",
    "drawing": "REXOME35 drawing REXOME35-9206 Rev.0 rear SECTION A-A' 250 x 250 "
               "(08_test_data/datasheets/cylinder_rear_extract.md); synthesis B-rep "
               "01_cad/02_legs/rexome35/moving_<leg>.brep (cyl35_synth.py), lowest -Y_cad plane",
}
ASSUMPTIONS = {
    "cad": [],
    "drawing": ["ASSUMPTION: corner chamfer 30 x 30 mm (no dimension on the drawing; figure read 25 ... 30, "
                "25 mm gives +0.9 % area, -0.4 % b)",
                "ASSUMPTION: pad orientation of the CAD pad kept (3.376 deg from body x; swivel pad)",
                "ASSUMPTION: plate thickness 25 mm / side height 20 mm as the CAD pad"],
}


def sig(value: float, digits: int = SIGNIFICANT_DIGITS) -> float:
    """Round to ``digits`` significant digits (same rule as export_params.sig)."""
    value = float(value)
    if value == 0.0 or not math.isfinite(value):
        return value
    return float(f"{value:.{digits - 1}e}")


def perimeter(xy: np.ndarray) -> float:
    return float(np.linalg.norm(np.roll(xy, -1, axis=0) - xy, axis=1).sum())


def side_height_mm(shape, bottom_y_mm: float) -> float:
    """Height of the vertical planar side faces that start at the bottom face (B-rep), mm;
    same rule as ``build_sim_shapes.measure_side_height``."""
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.GeomAbs import GeomAbs_Plane
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopoDS import topods

    sides = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        surface = BRepAdaptor_Surface(face, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        if abs(surface.Plane().Axis().Direction().Y()) > 1e-3:
            continue
        box = Bnd_Box()
        brepbndlib.AddOptimal(face, box, False, False)
        _, lo, _, _, hi, _ = box.Get()
        if abs(lo - bottom_y_mm) < 1e-3:
            sides.append(hi - bottom_y_mm)
    if not sides:
        raise SystemExit("no vertical pad side face found")
    return float(max(sides))


def measure_pad(path: Path, leg_index: int, params, build_hull: bool) -> dict:
    """Bottom face of one pad B-rep in the retracted body frame (+ optional simple plate)."""
    leg = params.legs[leg_index]
    offset = float(leg.retracted_offset_from_cad_m)
    centre_yaml = np.asarray(leg.pad_bottom_center_retracted_m, float)
    shape = read_ascii_brep(path)
    bottom = pad_bottom(shape)
    poly_body = cad_to_body_m(np.array(bottom["polygon_cad_mm"])) + [0.0, 0.0, offset]
    xy = poly_body[:, :2]
    if polygon_area(xy) < 0:
        xy = xy[::-1]
    rel_xy = xy - centre_yaml[:2]
    centroid = (CAD_TO_BODY @ np.array(bottom["centroid_cad_mm"])) * MM + [0.0, 0.0, offset]
    area = bottom["area_mm2"] * MM**2
    peri = perimeter(xy)
    out = {
        "brep": source_record(path),
        "bottom_area_m2": area,
        "polygon_area_m2": polygon_area(xy),
        "perimeter_m": peri,
        "polygon_rel_xy_m": rel_xy,
        "polygon_abs_xy_m": xy,
        "side_angle_deg": side_angle_deg(xy),
        "centroid_body_m": centroid,
        "centroid_minus_yaml_m": centroid - centre_yaml,
        "bottom_z_m": float(poly_body[:, 2].mean()),
        "normal_body": (CAD_TO_BODY @ np.array(bottom["normal_cad"])).tolist(),
        "edges_m": np.linalg.norm(np.roll(xy, -1, axis=0) - xy, axis=1),
    }
    plate, _, _ = split_rod_pad(shape, bottom["y_cad_mm"])
    plate_p = volume_properties(plate)
    thickness_m = (plate_p["bbox_mm"][1][1] - plate_p["bbox_mm"][0][1]) * MM
    side_m = side_height_mm(shape, bottom["y_cad_mm"]) * MM
    out.update(thickness_m=thickness_m, side_height_m=side_m, chamfer_m=thickness_m - side_m,
               plate_valid=plate_p["valid"])
    if build_hull:
        import trimesh

        top_xy = inset_polygon(xy, thickness_m - side_m)
        z_b = out["bottom_z_m"]
        points = np.vstack([np.column_stack([xy, np.full(len(xy), z_b)]),
                            np.column_stack([xy, np.full(len(xy), z_b + side_m)]),
                            np.column_stack([top_xy, np.full(len(xy), z_b + thickness_m)])])
        simple = trimesh.convex.convex_hull(points)
        sv, sf = np.asarray(simple.vertices), np.asarray(simple.faces, np.int64)
        brep_plate = brep_props_body(plate_p, offset)
        out["simple_mesh"] = (sv, sf)
        out["simple_vs_brep_plate"] = compare_props(trimesh_props(sv, sf), brep_plate)
        out["brep_plate"] = brep_plate
        out["plate_bbox_body_m"] = (bbox_cad_to_body_m(np.array(plate_p["bbox_mm"])) + [0, 0, offset]).tolist()
    return out


def polygon_sha256(polygon: list) -> str:
    """SHA-256 of the canonical JSON of a polygon (list of [x, y]); same rule as
    ``outrigger_sim.pad_variants.polygon_sha256``."""
    text = json.dumps([[float(x), float(y)] for x, y in polygon], separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def down_area(vertices: np.ndarray, faces: np.ndarray) -> float:
    a, b, c = (vertices[faces[:, k]] for k in range(3))
    n = np.cross(b - a, c - a)
    return 0.5 * float(np.linalg.norm(n[n[:, 2] < 0], axis=1).sum())


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def build(write_shapes: bool) -> tuple[dict, list[str]]:
    started = time.perf_counter()
    params = load_params()
    index = json.loads(SIM_SHAPES_INDEX.read_text(encoding="utf-8"))
    failures: list[str] = []
    checks: dict = {}
    measured = {}
    for i, leg in enumerate(LEG_ORDER):
        measured[(leg, "cad")] = measure_pad(CAD_BREP[leg], i, params, build_hull=leg in DRAWING_BREP)
        if leg in DRAWING_BREP:
            measured[(leg, "drawing")] = measure_pad(DRAWING_BREP[leg], i, params, build_hull=False)

    # --- C8 shapes: existing index entries, or the type A rear pads built here
    c8: dict = {}
    for (leg, kind), m in measured.items():
        index_hull = index["collision"][f"pad_{leg}_hull"]
        index_simple = index["visual"][f"pad_{leg}_simple"]
        index_brep = index["legs"][leg]["brep"]["path"]
        if index_brep == m["brep"]["path"]:  # the C8 index was built from this B-rep
            c8[(leg, kind)] = {
                "in_c8_index": True,
                "hull": {"name": f"pad_{leg}_hull", "file": index_hull["file"],
                         "sha256": bss.sha256_file(PROJECT_ROOT / index_hull["file"]), "faces": index_hull["faces"]},
                "visual_simple": {"name": f"pad_{leg}_simple", "file": index_simple["file"],
                                  "sha256": bss.sha256_file(PROJECT_ROOT / index_simple["file"]),
                                  "faces": index_simple["faces"]},
            }
            continue
        sv, sf = m["simple_mesh"]
        header = ["frame: machine body axes, origin CAD origin, metres, leg retracted state",
                  f"pad type A (cad330) of {leg}: generated by 04_scripts/00_cad/export_pad_variants.py"]
        files = {"hull": VARIANT_SHAPES_DIR / "collision" / f"pad_{leg}_hull_cad330.obj",
                 "visual_simple": VARIANT_SHAPES_DIR / "visual" / f"pad_{leg}_simple_cad330.obj"}
        entry = {"in_c8_index": False}
        for role, path in files.items():
            if write_shapes:
                path.parent.mkdir(parents=True, exist_ok=True)
                write_obj(path, [(sv, sf)], [f"C8 {'collision candidate' if role == 'hull' else 'visual'}: "
                                             f"chamfered octagon pad plate (convex)", *header])
            v, f = bss.read_obj(path)[0]
            entry[role] = {"name": path.stem, "file": rel(path), "sha256": bss.sha256_file(path), "faces": int(len(f))}
            # checks of the written OBJ (6 decimals) against the B-rep
            import trimesh

            mesh = trimesh.Trimesh(v, f, process=False)
            item = {
                "down_area_rel_to_brep": down_area(v, f) / m["bottom_area_m2"] - 1.0,
                "volume_rel_to_brep_plate": float(mesh.volume) / m["brep_plate"]["volume_m3"] - 1.0,
                "com_abs_m": float(np.linalg.norm(mesh.center_mass - np.asarray(m["brep_plate"]["com_m"]))),
                "obj_convex": bool(abs(mesh.convex_hull.volume / mesh.volume - 1.0) <= 1e-4),
                "obj_bottom_z_m": float(v[:, 2].min()),
                "obj_bottom_minus_yaml_z_m": float(v[:, 2].min() - params.legs[LEG_ORDER.index(leg)]
                                                   .pad_bottom_center_retracted_m[2]),
            }
            checks.setdefault("type_a_rear_shapes", {})[f"{leg}.{role}"] = item
            if abs(item["down_area_rel_to_brep"]) > TOL["hull_down_area_rel"]:
                failures.append(f"{leg} {role}: down-facing area {item['down_area_rel_to_brep']:+.2e}")
            if abs(item["volume_rel_to_brep_plate"]) > TOL["hull_volume_rel"]:
                failures.append(f"{leg} {role}: volume vs B-rep plate {item['volume_rel_to_brep_plate']:+.2e}")
            if not item["obj_convex"]:
                failures.append(f"{leg} {role}: not convex")
            if abs(item["obj_bottom_minus_yaml_z_m"]) > TOL["bottom_z_vs_yaml_m"]:
                failures.append(f"{leg} {role}: bottom z {item['obj_bottom_minus_yaml_z_m']:+.2e} m off the YAML")
        c8[(leg, kind)] = entry

    # --- per-leg records and checks
    records = {}
    for (leg, kind), m in measured.items():
        i = LEG_ORDER.index(leg)
        yaml_pad = params.legs[i].pad
        polygon = [[sig(x), sig(y)] for x, y in m["polygon_rel_xy_m"]]
        area = sig(m["bottom_area_m2"])
        peri = sig(m["perimeter_m"])
        rec = {
            "source_kind": "cad_brep" if kind == "cad" else "drawing_synthesis_brep",
            "source": SOURCE_TEXT[kind].replace("<leg>", ROD_PAD_BREP[leg][:-5] if kind == "cad" else leg),
            "brep": {"path": m["brep"]["path"], "bytes": m["brep"]["bytes"], "sha256": m["brep"]["sha256"]},
            "assumptions": ASSUMPTIONS[kind],
            "polygon_xy_m": polygon,
            "polygon_sha256": polygon_sha256(polygon),
            "polygon_reference": f"relative to legs.{leg}.pad_bottom_center_retracted_m (x, y), counter-clockwise from +z",
            "bottom_area_m2": area,
            "perimeter_m": peri,
            "bekker_b_m": sig(2.0 * m["bottom_area_m2"] / m["perimeter_m"]),
            "equivalent_radius_m": sig(math.sqrt(m["bottom_area_m2"] / math.pi)),
            "equivalent_square_side_m": sig(math.sqrt(m["bottom_area_m2"])),
            "side_angle_deg": sig(m["side_angle_deg"]),
            "thickness_m": sig(m["thickness_m"]),
            "side_height_m": sig(m["side_height_m"]),
            "c8": c8[(leg, kind)],
        }
        records[(leg, kind)] = rec
        item = {
            "area_vs_polygon_rel": m["bottom_area_m2"] / m["polygon_area_m2"] - 1.0,
            "centroid_minus_yaml_m": m["centroid_minus_yaml_m"].tolist(),
            "bottom_z_minus_yaml_m": m["bottom_z_m"] - params.legs[i].pad_bottom_center_retracted_m[2],
            "normal_body": m["normal_body"],
            "edges_m": sorted(set(round(float(e), 6) for e in m["edges_m"])),
            "plate_valid": m["plate_valid"],
        }
        if kind == "cad":
            diff = np.abs(np.array(polygon) - np.array(yaml_pad.polygon_xy_m)) if len(polygon) == len(yaml_pad.polygon_xy_m) else None
            item["polygon_vs_yaml_max_abs_m"] = None if diff is None else float(diff.max())
            item["area_vs_yaml_rel"] = area / yaml_pad.bottom_area_m2 - 1.0
            if diff is None or diff.max() > TOL["polygon_vs_yaml_m"]:
                failures.append(f"{leg} cad: polygon differs from the YAML ({item['polygon_vs_yaml_max_abs_m']})")
            if abs(item["area_vs_yaml_rel"]) > TOL["area_vs_yaml_rel"]:
                failures.append(f"{leg} cad: area differs from the YAML ({item['area_vs_yaml_rel']:+.2e})")
        else:
            expected = (DRAWING_SIDE_MM**2 - 2.0 * DRAWING_CHAMFER_MM**2) * MM**2
            item["area_vs_drawing_rel"] = m["bottom_area_m2"] / expected - 1.0
            item["drawing_area_m2"] = expected
            if abs(item["area_vs_drawing_rel"]) > TOL["area_vs_drawing_rel"]:
                failures.append(f"{leg} drawing: area {m['bottom_area_m2']} vs drawing {expected}")
            index_area = index["legs"][leg]["pad_face"]["brep_area_m2"]
            item["area_vs_c8_index_rel"] = m["bottom_area_m2"] / index_area - 1.0
            if abs(item["area_vs_c8_index_rel"]) > TOL["area_vs_polygon_rel"]:
                failures.append(f"{leg} drawing: area differs from the C8 index pad face")
        if abs(item["area_vs_polygon_rel"]) > TOL["area_vs_polygon_rel"]:
            failures.append(f"{leg} {kind}: B-rep face area vs outer-wire polygon {item['area_vs_polygon_rel']:+.2e}")
        if np.abs(m["centroid_minus_yaml_m"][:2]).max() > TOL["centroid_vs_yaml_m"]:
            failures.append(f"{leg} {kind}: face centroid off the YAML pad centre")
        if abs(item["bottom_z_minus_yaml_m"]) > TOL["bottom_z_vs_yaml_m"]:
            failures.append(f"{leg} {kind}: bottom z off the YAML")
        if not m["plate_valid"]:
            failures.append(f"{leg} {kind}: pad plate B-rep not valid")
        checks.setdefault("legs", {})[f"{leg}.{kind}"] = item

    variants = {}
    for name, spec in VARIANTS.items():
        legs = {leg: records[(leg, spec["sources"][leg])] for leg in LEG_ORDER}
        variants[name] = {
            "label": spec["label"],
            "description": spec["description"],
            "mass_note": spec["mass_note"],
            "legs": legs,
            "override_keys": [f"legs.{leg}.pad.{key}" for leg in LEG_ORDER for key in ("polygon_xy_m", "bottom_area_m2")],
        }
    params_file = DEFAULT_PARAMS_PATH
    table = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "generator": {"path": rel(Path(__file__)), "sha256": bss.sha256_file(Path(__file__))},
        "decision": "user decisions U-PAD-1..6 2026-10-25 (00_docs/decision_log.md sec. 2; "
                    "00_docs/01_dynamics/dynamics_model.md rev. 44 5.30.5 / 5.30.8)",
        "default": DEFAULT_VARIANT,
        "names": list(VARIANTS),
        "use": "S9 (SCM) and shape consumers only: outrigger_sim.pad_variants.apply_pad_variant(params, name) "
               "overrides legs.<leg>.pad.polygon_xy_m / bottom_area_m2 in memory (the run fingerprint then holds the "
               "type); rigid-floor L1 / L2b (S1 ... S8) do not use the pad area (5.30.3) and keep the YAML as is",
        "frame": "machine body axes (x forward, y left, z up), metres; polygons relative to "
                 "legs.<leg>.pad_bottom_center_retracted_m",
        "units": "SI (m, m^2); angles in deg (side_angle_deg: long pad sides from body x, folded to [0, 90))",
        "bekker_b_definition": "b = 2 A / perimeter (Chrono SCM patch width, vehicle_terrain.md 82-97)",
        "params_yaml": {"path": rel(params_file), "file_sha256": params.file_sha256,
                        "note": "read only (pad bottom centres, retracted offsets, type A comparison)"},
        "c8_index": source_record(SIM_SHAPES_INDEX),
        "variants": variants,
        "tolerances": TOL,
        "checks": checks,
        "failures": failures,
        "time_s": time.perf_counter() - started,
    }
    return table, failures


def _plain(obj):
    if isinstance(obj, (np.bool_, np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return obj.as_posix()
    raise TypeError(type(obj))


def _comparable(table: dict) -> dict:
    out = json.loads(json.dumps(table, default=_plain))
    for key in ("generated", "time_s"):
        out.pop(key, None)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="recompute and compare, write nothing")
    args = parser.parse_args()
    yaml_before = bss.sha256_file(DEFAULT_PARAMS_PATH)
    table, failures = build(write_shapes=not args.check)
    if bss.sha256_file(DEFAULT_PARAMS_PATH) != yaml_before:
        raise SystemExit("the YAML changed while running (it must stay untouched)")
    if args.check:
        old = json.loads(TABLE_JSON.read_text(encoding="utf-8"))
        same = _comparable(old) == _comparable(table)
        print(f"{rel(TABLE_JSON)}: {'unchanged' if same else 'DIFFERS'}; {len(failures)} failure(s) {failures}")
        return 0 if same and not failures else 1
    TABLE_JSON.write_text(json.dumps(table, ensure_ascii=False, indent=1, default=_plain) + "\n", encoding="utf-8")
    for name, variant in table["variants"].items():
        areas = {leg: rec["bottom_area_m2"] for leg, rec in variant["legs"].items()}
        bs = {leg: rec["bekker_b_m"] for leg, rec in variant["legs"].items()}
        print(f"{name}: A {areas} m2, b {bs} m")
    print(f"wrote {rel(TABLE_JSON)}: {len(failures)} failure(s) {failures}; YAML sha256 {yaml_before[:12]} unchanged; "
          f"{table['time_s']:.1f} s")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
