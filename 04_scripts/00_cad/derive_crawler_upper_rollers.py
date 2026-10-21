"""Per-part B-rep files, index and face table of the crawler upper (carrier) rollers.

The crawler shrinkwrap (prototype ``0:1:1:746``) has one carrier roller per
track at Z_cad 0 (``check_upper_run.py``, ``upper_run_check.json``). The
roller wheel, its shaft boss and the bracket are ONE solid (left 234, right
1900). This script groups, per side,

* the roller solid (``roller_body``: wheel + shaft boss + bracket, merged in the
  CAD), and
* the fasteners that hold the bracket: every solid smaller than
  ``FASTENER_MAX_VOLUME_MM3`` whose exact distance to the roller solid is at
  most ``FASTENER_TOUCH_MM`` (two long and two short bolts, four washers),

writes each group as one compound in a binary B-rep file (same convention as
``derive_crawler_parts.py``: CAD world frame, mm, Y up, crawler placement
applied, identity placement) and writes

* ``01_cad/06_brep/derived/crawler/crawler_upper_rollers.csv`` / ``.json``:
  one row per part (mass properties, bbox, axis, tread / flange sizes,
  estimated rotating mass),
* ``01_cad/06_brep/derived/crawler/crawler_upper_roller_solids.csv``: member
  solids with role and mass properties,
* ``01_cad/07_faces/crawler_upper_roller_faces.csv.gz``: face table of the
  parts in the column layout of ``instance_faces.csv.gz`` (C5) plus
  ``part_id`` and ``role``; query it with
  ``face_index.query(..., table=face_index.load_crawler_upper_roller_faces())``.

The seat block under the bracket (left solid 22, right mirror) is NOT part of
the roller: it touches the track frame solid along its side below the frame
top (welded into the frame), and its holes are the bolt diameter (tapped)
while the bracket holes are clearance holes. The script records this check.

Rotating mass (estimate): the roller solid cut by a cylinder of radius
``ROTATING_CUT_RADIUS_MM`` about the roller axis over the X span of the
Ø120 / Ø140 / Ø120 / Ø100 faces (tread start to the outer end). The shaft
inside the wheel is not separate in the shrinkwrap, so the value includes it;
the Ø80 boss on the bracket side is excluded (fixed). Marked as estimate.

Only cache files are read (no STEP). Frames: ``*_cad_mm`` = CAD world (mm, Y
up); ``*_body_m`` = body axes (x = +Z_cad, y = +X_cad, z = +Y_cad, CAD origin,
m). Inertia about the part centroid, body axes, kg m^2. Density = crawler
prototype material from ``parts_classified.csv`` (steel 7.85 g/cm^3).

Usage:
    python -I -X utf8 04_scripts/00_cad/derive_crawler_upper_rollers.py
"""

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
import pandas as pd
import psutil
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import topods

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brep_cache
import build_face_index as bfi
from build_style_index import place_one_pcore
from cad_common import FACES_DIR, MM_PER_M, PROJECT_ROOT
from check_cache import sha256_file
from check_upper_run import distance, face_summary
from derive_crawler_parts import (
    CAD_TO_BODY,
    bbox,
    crawler_density,
    face_ranges,
    load_solids,
    make_compound,
    mass_properties,
    to_body,
)

CRAWLER_ENTRY = "0:1:1:746"
CRAWLER_DIR = brep_cache.DERIVED_DIR / "crawler"
PARTS_OUT_DIR = CRAWLER_DIR / "parts"
INDEX_CSV = CRAWLER_DIR / "crawler_upper_rollers.csv"
INDEX_JSON = CRAWLER_DIR / "crawler_upper_rollers.json"
SOLIDS_OUT_CSV = CRAWLER_DIR / "crawler_upper_roller_solids.csv"
FACES_OUT = FACES_DIR / "crawler_upper_roller_faces.csv.gz"
UPPER_RUN_JSON = CRAWLER_DIR / "upper_run_check.json"
LOG_PATH = CRAWLER_DIR / "derive_upper_rollers.log"

SIDES = {"L": "left", "R": "right"}
FASTENER_MAX_VOLUME_MM3 = 1e5
FASTENER_TOUCH_MM = 1.0
NEIGHBOUR_BOX_GAP_MM = 2.0
SEAT_MAX_VOLUME_MM3 = 1e6  # seat block candidates (excluded, recorded)
FRAME_MIN_VOLUME_MM3 = 1e7  # track frame solid
AXIS_TOL = 1e-9
ROTATING_CUT_RADIUS_MM = 75.0  # > the largest roller radius 70 mm
SYMMETRY_REL_TOL = 1e-9
POSITION_MIRROR_TOL_M = 1e-5  # 0.01 mm; the crawler is placed 0.0005 mm off X_cad 0
FLOAT_FORMAT = "%.10g"
BOX_KEYS = ("min_x", "min_y", "min_z", "max_x", "max_y", "max_z")


def log(message: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def volume(shape) -> float:
    props = GProp_GProps()
    brepgprop.VolumeProperties(shape, props)
    return props.Mass()


def box_gap(a: np.ndarray, b: np.ndarray) -> float:
    gap = np.clip(np.maximum(a[:3], b[:3]) - np.minimum(a[3:], b[3:]), 0, None)
    return float(np.linalg.norm(gap))


# --------------------------------------------------------------------------
# Grouping
# --------------------------------------------------------------------------
def find_rollers(upper_run: dict) -> dict[str, int]:
    found = {}
    for candidate in upper_run["upper_zone_non_chain_solids"]:
        if candidate["solid"] in upper_run["supports_touching_upper_chain"]:
            found[{"left": "L", "right": "R"}[candidate["side"]]] = candidate["solid"]
    if sorted(found) != ["L", "R"]:
        raise RuntimeError(f"expected one carrier roller per side, got {found}")
    return found


def group_part(roller: int, solids: pd.DataFrame, shapes: list) -> dict:
    """Roller solid + touching fasteners; neighbours that are not taken, with reasons."""
    boxes = solids[[f"bbox_{k}_mm" for k in BOX_KEYS]].to_numpy()
    roller_box = boxes[roller]
    members = [{"solid": roller, "role": "roller_body"}]
    neighbours = []
    for index in range(len(shapes)):
        if index == roller or box_gap(roller_box, boxes[index]) > NEIGHBOUR_BOX_GAP_MM:
            continue
        vol = float(solids.at[index, "volume_mm3"])
        gap = distance(shapes[roller], shapes[index])[0]
        if vol < FASTENER_MAX_VOLUME_MM3 and gap <= FASTENER_TOUCH_MM:
            members.append({"solid": index, "role": None, "distance_to_roller_mm": gap})
        else:
            neighbours.append({"solid": index, "volume_mm3": vol, "distance_to_roller_mm": gap})
    for member in members[1:]:
        member["role"] = fastener_role(shapes[member["solid"]], solids.loc[member["solid"]])
    return {"members": members, "neighbours": neighbours}


def fastener_role(shape, row: pd.Series) -> str:
    """bolt_long / bolt_short / washer from the Y length (bolt axis = Y_cad)."""
    length = row["bbox_max_y_mm"] - row["bbox_min_y_mm"]
    if length <= 5.0:
        return "washer"
    return "bolt_long" if length >= 70.0 else "bolt_short"


def seat_block_check(part: dict, roller: int, solids: pd.DataFrame, shapes: list) -> dict:
    """Why the block under the bracket stays with the frame."""
    axis_y = float(solids.at[roller, "bbox_min_y_mm"] + solids.at[roller, "bbox_max_y_mm"]) / 2
    # Seat candidates: touching neighbours below the roller (chain links touch from above).
    seats = [n for n in part["neighbours"]
             if n["volume_mm3"] < SEAT_MAX_VOLUME_MM3 and n["distance_to_roller_mm"] <= 1e-6
             and solids.at[n["solid"], "bbox_max_y_mm"] <= axis_y]
    frames = solids.index[(solids["volume_mm3"] > FRAME_MIN_VOLUME_MM3)
                          & (solids["side"] == solids.at[roller, "side"])]
    out = []
    for seat in seats:
        index = seat["solid"]
        seat_box = solids.loc[index, [f"bbox_{k}_mm" for k in BOX_KEYS]].to_numpy(float)
        touching_frames = []
        for frame in frames:
            frame_box = solids.loc[frame, [f"bbox_{k}_mm" for k in BOX_KEYS]].to_numpy(float)
            if box_gap(seat_box, frame_box) > 1.0:
                continue
            value, _, point = distance(shapes[index], shapes[frame])
            if value <= 1e-6:
                touching_frames.append({"frame_solid": int(frame), "distance_mm": value,
                                        "contact_point_cad_mm": point,
                                        "frame_top_y_cad_mm": float(frame_box[4])})
        holes_seat = sorted({r["radius_mm"] for r in face_summary(shapes[index])["rounds"]
                             if abs(r["axis"][1]) > 0.99})
        holes_bracket = sorted({r["radius_mm"] for r in face_summary(shapes[roller])["rounds"]
                                if abs(r["axis"][1]) > 0.99})
        out.append({
            "seat_solid": int(index), "volume_mm3": seat["volume_mm3"],
            "bbox_cad_mm": seat_box.round(3).tolist(),
            "touches_frame": touching_frames,
            "seat_hole_radii_mm": holes_seat, "bracket_hole_radii_mm": holes_bracket,
            "decision": "excluded (frame)" if touching_frames else "check manually",
            "reason": "touches the track frame solid below the frame top (welded seat); "
                      "hole radius = bolt shank radius (tapped), bracket holes are clearance",
        })
    return {"seat_blocks": out}


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------
def roller_geometry(shape, face_offset: int) -> dict:
    """Revolved faces about X_cad: diameters with X spans, axis, tread faces (global index)."""
    rows, index = [], 0
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        record = bfi.analyze_face(face)
        if record["kind"] == "cylinder" and abs(abs(record["axis"][0]) - 1) < AXIS_TOL \
                and record["radius_mm"] >= 20.0:
            rows.append({"face": face_offset + index, "radius_mm": record["radius_mm"],
                         "x0": record["bbox"][0], "x1": record["bbox"][3],
                         "axis_point": record["axis_point"], "convex": record["convex"]})
        index += 1
    by_radius: dict[float, dict] = {}
    for row in rows:
        key = round(row["radius_mm"], 6)
        entry = by_radius.setdefault(key, {"faces": [], "spans": []})
        entry["faces"].append(row["face"])
        entry["spans"].append((row["x0"], row["x1"]))
    axis_y = float(np.median([r["axis_point"][1] for r in rows]))
    axis_z = float(np.median([r["axis_point"][2] for r in rows]))
    bands = []
    for radius, entry in sorted(by_radius.items()):
        spans = sorted({(round(a, 6), round(b, 6)) for a, b in entry["spans"]})
        bands.append({"diameter_mm": 2 * radius, "spans_x_cad_mm": spans,
                      "faces": sorted(entry["faces"])})
    tread = next(b for b in bands if abs(b["diameter_mm"] - 120.0) < 1e-6)
    flange = max(bands, key=lambda b: b["diameter_mm"])
    spans = tread["spans_x_cad_mm"]
    if len(spans) != 2:
        raise RuntimeError(f"expected two tread spans, got {spans}")
    # Spans as |X| intervals (inner = closer to the machine centre) for both sides.
    inner, outer = sorted((min(abs(s[0]), abs(s[1])), max(abs(s[0]), abs(s[1]))) for s in spans)
    return {
        "axis_y_cad_mm": axis_y, "axis_z_cad_mm": axis_z, "bands": bands,
        "tread_diameter_mm": tread["diameter_mm"],
        "tread_width_mm": float(np.mean([s[1] - s[0] for s in spans])),
        "tread_spans": spans, "tread_faces": tread["faces"],
        "tread_gap_mm": float(outer[0] - inner[1]),
        "flange_diameter_mm": flange["diameter_mm"],
        "flange_span": flange["spans_x_cad_mm"][0],
        "flange_faces": flange["faces"],
        "x_centre_cad_mm": float(np.mean(flange["spans_x_cad_mm"][0])),
    }


def rotating_estimate(shape, geometry: dict, density: float) -> dict:
    """Roller solid inside a cylinder about the roller axis, tread start to outer end."""
    xs = [x for band in geometry["bands"] if band["diameter_mm"] >= 100.0 - 1e-6
          for span in band["spans_x_cad_mm"] for x in span]
    x0, x1 = min(xs), max(xs)
    start = gp_Pnt(x0, geometry["axis_y_cad_mm"], geometry["axis_z_cad_mm"])
    cylinder = BRepPrimAPI_MakeCylinder(gp_Ax2(start, gp_Dir(1, 0, 0)),
                                        ROTATING_CUT_RADIUS_MM, x1 - x0).Shape()
    common = BRepAlgoAPI_Common(shape, cylinder)
    common.Build()
    if not common.IsDone():
        raise RuntimeError("rotating-part cut failed")
    cut = common.Shape()
    props = GProp_GProps()
    brepgprop.VolumeProperties(cut, props)
    vol = props.Mass()
    centre = props.CentreOfMass()
    axis = gp_Ax2(gp_Pnt(centre.X(), centre.Y(), centre.Z()), gp_Dir(1, 0, 0)).Axis()
    spin = props.MomentOfInertia(axis) * density * 1e-6 * 1e-6  # kg m^2
    ideal = sum(np.pi * (b["diameter_mm"] / 2) ** 2 * (s[1] - s[0])
                for b in geometry["bands"] if b["diameter_mm"] >= 100.0 - 1e-6
                for s in b["spans_x_cad_mm"])
    return {"x_span_cad_mm": [x0, x1], "volume_mm3": vol, "mass_kg": vol * density * 1e-6,
            "spin_inertia_kg_m2": spin, "ideal_cylinders_volume_mm3": ideal,
            "valid": bool(BRepCheck_Analyzer(cut).IsValid())}


# --------------------------------------------------------------------------
# Rows
# --------------------------------------------------------------------------
def mass_columns(props: dict, prefix: str = "") -> dict:
    row = {f"{prefix}volume_mm3": props["volume_mm3"], f"{prefix}mass_kg": props["mass_kg"]}
    for axis, value in zip("xyz", props["com_cad_mm"], strict=True):
        row[f"{prefix}com_{axis}_cad_mm"] = value
    for axis, value in zip("xyz", props["com_body_m"], strict=True):
        row[f"{prefix}com_{axis}_body_m"] = value
    inertia = props["inertia_body_kg_m2"]
    for name, (i, j) in {"xx": (0, 0), "yy": (1, 1), "zz": (2, 2),
                         "xy": (0, 1), "xz": (0, 2), "yz": (1, 2)}.items():
        row[f"{prefix}I{name}_body_kg_m2"] = inertia[i, j]
    for k, value in enumerate(props["principal_kg_m2"], start=1):
        row[f"{prefix}I{k}_principal_kg_m2"] = value
    return row


def box_columns(box: np.ndarray) -> dict:
    row = {f"bbox_{k}_cad_mm": v for k, v in zip(BOX_KEYS, box, strict=True)}
    body = np.sort(np.stack([to_body(box[:3]), to_body(box[3:])]), axis=0).ravel()
    row.update({f"bbox_{k}_body_m": v for k, v in zip(BOX_KEYS, body, strict=True)})
    return row


def face_rows(part_id: str, members: list[dict], solid_shapes, face_start, invalid) -> pd.DataFrame:
    """C5 face rows (instance_faces.csv.gz layout) of the part's solids + part_id, role."""
    instance = brep_cache.instances_of(CRAWLER_ENTRY)[0]
    prototype = brep_cache.load_prototype(CRAWLER_ENTRY)
    _, proto_face_start = load_solids(prototype)
    proto_solids = []
    explorer = TopExp_Explorer(prototype, bfi.TopAbs_SOLID)
    while explorer.More():
        proto_solids.append(topods.Solid(explorer.Current()))
        explorer.Next()
    rows, faces, roles, checks = [], [], [], {"checked": 0, "failed": 0}
    for member in members:
        solid = member["solid"]
        if int(proto_face_start[solid]) != int(face_start[solid]):
            raise RuntimeError("prototype and placed face numbering differ")
        face_explorer = TopExp_Explorer(proto_solids[solid], TopAbs_FACE)
        local = 0
        while face_explorer.More():
            face = topods.Face(face_explorer.Current())
            face_explorer.Next()
            row = bfi.analyze_face(face)
            result = bfi.check_normal(face, row)
            if result is not None:
                checks["checked"] += 1
                checks["failed"] += int(not result)
            row.update(prototype_entry=CRAWLER_ENTRY, face_index=int(face_start[solid]) + local,
                       solid_index=solid, solid_valid=solid not in invalid,
                       selection="upper_roller")
            rows.append(row)
            faces.append(face)
            roles.append(member["role"])
            local += 1
    proto = bfi._flatten(rows)
    table = bfi._instance_rows(proto, faces, instance, {"zero_volume": False})
    table.insert(0, "part_id", part_id)
    table.insert(1, "role", roles)
    return table, checks


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------
MIRROR_SIGNS = {"xx": 1, "yy": 1, "zz": 1, "xy": -1, "xz": 1, "yz": -1}  # X_cad -> -X_cad = body y


def verify(rows: pd.DataFrame, solid_rows: pd.DataFrame, upper_run: dict, shapes: dict,
           face_table: pd.DataFrame, face_checks: dict) -> dict:
    left, right = rows.set_index("side").loc["L"], rows.set_index("side").loc["R"]
    scale = float(max(left[[f"I{k}_principal_kg_m2" for k in (1, 2, 3)]]))
    sym = {"volume_rel": abs(right["volume_mm3"] / left["volume_mm3"] - 1)}
    for name, sign in MIRROR_SIGNS.items():
        column = f"I{name}_body_kg_m2"
        sym[f"I{name}_rel_to_I_max"] = abs(right[column] - sign * left[column]) / scale
    sym["rotating_volume_est_rel"] = abs(right["rotating_volume_est_mm3"]
                                         / left["rotating_volume_est_mm3"] - 1)
    for column in ("roller_axis_z_body_m", "roller_axis_x_body_m"):
        sym[f"{column}_abs_diff"] = abs(right[column] - left[column])
    # The crawler placement is 0.0005 mm off the CAD X origin (crawler_wheels.csv:
    # +1044.9995 / -1045.0005), so the y mirror sum is about 1e-6 m.
    sym["roller_axis_y_body_m_sum"] = abs(right["roller_axis_y_body_m"] + left["roller_axis_y_body_m"])
    sym["member_volumes_match"] = bool(np.allclose(
        np.sort(solid_rows[solid_rows.side == "L"]["volume_mm3"].to_numpy()),
        np.sort(solid_rows[solid_rows.side == "R"]["volume_mm3"].to_numpy()), rtol=SYMMETRY_REL_TOL))
    sym_pass = (all(v <= SYMMETRY_REL_TOL for k, v in sym.items() if k.endswith("_rel")
                    or k.endswith("_I_max"))
                and all(v <= 1e-9 for k, v in sym.items() if k.endswith("_abs_diff"))
                and sym["roller_axis_y_body_m_sum"] <= POSITION_MIRROR_TOL_M
                and sym["member_volumes_match"])

    reload = {}
    for _, row in rows.iterrows():
        shape = brep_cache.read_brep(PROJECT_ROOT / row["file"])
        props = GProp_GProps()
        explorer = TopExp_Explorer(shape, bfi.TopAbs_SOLID)
        count = 0
        while explorer.More():
            item = GProp_GProps()
            brepgprop.VolumeProperties(explorer.Current(), item)
            props.Add(item, 1.0)
            count += 1
            explorer.Next()
        cached = solid_rows.loc[solid_rows.part_id == row["part_id"], "cache_volume_mm3"].sum()
        reload[row["part_id"]] = {"solids": count, "expected_solids": int(row["solid_count"]),
                                  "volume_rel_diff_vs_cache": abs(props.Mass() / cached - 1)}
    reload_pass = all(v["solids"] == v["expected_solids"] and v["volume_rel_diff_vs_cache"] <= 1e-9
                      for v in reload.values())

    reference = {}
    for candidate in upper_run["upper_zone_non_chain_solids"]:
        if candidate["solid"] not in upper_run["supports_touching_upper_chain"]:
            continue
        side = {"left": "L", "right": "R"}[candidate["side"]]
        row = rows.set_index("side").loc[side]
        roller = candidate["roller"]
        spans = {b["diameter_mm"]: (b["x_from_mm"], b["x_to_mm"]) for b in roller["x_spans_by_diameter"]}
        diffs = {
            "axis_y_mm": abs(row["roller_axis_y_cad_mm"] - roller["axis_mm"]["y"]),
            "axis_z_mm": abs(row["roller_axis_z_cad_mm"] - roller["axis_mm"]["z"]),
            "flange_diameter_mm": abs(row["flange_diameter_mm"] - max(spans)),
            "flange_width_mm": abs(row["flange_width_mm"] - (spans[max(spans)][1] - spans[max(spans)][0])),
            "tread_diameter_mm": abs(row["tread_diameter_mm"] - 120.0),
            "tread_width_mm": abs(row["tread_width_mm"] - (spans[120.0][1] - spans[120.0][0])),
            "roller_volume_mm3_rel": abs(row["roller_body_volume_mm3"] / candidate["volume_mm3"] - 1),
        }
        reference[row["part_id"]] = {k: round(float(v), 6) for k, v in diffs.items()}
    # upper_run_check.json rounds to 2-3 decimals (mm) and 1 decimal (volume)
    reference_pass = all(v["roller_volume_mm3_rel"] <= 1e-7 and all(
        d <= 0.01 for k, d in v.items() if k != "roller_volume_mm3_rel") for v in reference.values())

    faces = {}
    for part_id, group in face_table.groupby("part_id"):
        row = rows.set_index("part_id").loc[part_id]
        shape = shapes[part_id]
        props = GProp_GProps()
        brepgprop.SurfaceProperties(shape, props)
        faces[part_id] = {"rows": len(group), "face_count": int(row["face_count"]),
                          "area_rel_diff": abs(group["area_mm2"].sum() / props.Mass() - 1)}
    import face_index

    table = face_index.load_crawler_upper_roller_faces()
    treads = face_index.query(kind="cylinder", axis_body=(0, 1, 0), radius_mm=(59.999, 60.001),
                              convex=True, table=table)
    flange = face_index.query(kind="cylinder", axis_body=(0, 1, 0), radius_mm=(69.999, 70.001),
                              convex=True, table=table)
    query = {"tread_faces_per_part": treads.groupby("part_id").size().to_dict(),
             "tread_faces_expected": {r.part_id: len(str(r.tread_face_indices).split(";"))
                                      for r in rows.itertuples()},
             "flange_faces_per_part": flange.groupby("part_id").size().to_dict(),
             "tread_axis_z_body_m": sorted(treads["axis_point_z_body_m"].round(6).unique().tolist())}
    query_pass = (query["tread_faces_per_part"] == query["tread_faces_expected"]
                  and len(query["tread_axis_z_body_m"]) == 1)
    faces_pass = (all(v["rows"] == v["face_count"] and v["area_rel_diff"] <= 1e-9
                      for v in faces.values()) and face_checks["failed"] == 0)
    return {
        "symmetry": {"values": sym, "tolerance_rel": SYMMETRY_REL_TOL,
                     "tolerance_axis_y_mirror_m": POSITION_MIRROR_TOL_M, "pass": bool(sym_pass)},
        "reload": {"parts": reload, "pass": reload_pass},
        "upper_run_check_match": {"abs_diff": reference, "tolerance": "0.01 mm (json rounding), "
                                  "volume 1e-7 rel", "pass": reference_pass},
        "face_table": {"parts": faces, "normal_checks": face_checks, "pass": faces_pass},
        "face_index_query": {**query, "pass": bool(query_pass)},
        "pass": bool(sym_pass and reload_pass and reference_pass and faces_pass and query_pass),
    }


# --------------------------------------------------------------------------
def main() -> None:
    started = time.perf_counter()
    LOG_PATH.write_text("", encoding="utf-8")
    cpu = place_one_pcore()
    log(f"cpu {cpu}")
    instance = brep_cache.instances_of(CRAWLER_ENTRY)[0]
    crawler = brep_cache.load_part(instance.instance_path)
    solid_shapes, face_start = load_solids(crawler)
    solids = pd.read_csv(CRAWLER_DIR / "crawler_solids.csv", encoding="utf-8-sig").set_index("solid", drop=False)
    summary = json.loads((CRAWLER_DIR / "crawler_summary.json").read_text(encoding="utf-8"))
    upper_run = json.loads(UPPER_RUN_JSON.read_text(encoding="utf-8"))
    ground_y = float(summary["ground_y_mm"])
    density, density_source = crawler_density()
    log(f"{len(solid_shapes)} solids, density {density} g/cm3 ({density_source})")
    rollers = find_rollers(upper_run)

    rows, solid_rows, shapes, tables, groupings = [], [], {}, [], {}
    face_checks = {"checked": 0, "failed": 0}
    for side, roller in sorted(rollers.items()):
        part_id = f"upper_roller_{side}1"
        part = group_part(roller, solids, solid_shapes)
        part.update(seat_block_check(part, roller, solids, solid_shapes))
        members = sorted(part["members"], key=lambda m: m["solid"])
        ids = [m["solid"] for m in members]
        invalid = {s for s in ids if not BRepCheck_Analyzer(solid_shapes[s]).IsValid()}
        compound = make_compound(solid_shapes[s] for s in ids)
        path = PARTS_OUT_DIR / f"{part_id}{brep_cache.BINARY_SUFFIX}"
        brep_cache.write_brep(compound, path)
        shapes[part_id] = compound
        props = mass_properties([solid_shapes[s] for s in ids], density)
        body = mass_properties([solid_shapes[roller]], density)
        fasteners = [s for s in ids if s != roller]
        fast = mass_properties([solid_shapes[s] for s in fasteners], density)
        geometry = roller_geometry(solid_shapes[roller], int(face_start[roller]))
        rotating = rotating_estimate(solid_shapes[roller], geometry, density)
        axis_body = to_body([geometry["x_centre_cad_mm"], geometry["axis_y_cad_mm"],
                             geometry["axis_z_cad_mm"]])
        ranges = face_ranges(ids, face_start)
        box = bbox(compound)
        hub = [b for b in geometry["bands"] if b["diameter_mm"] < 100.0 - 1e-6]
        cap = [b for b in geometry["bands"] if abs(b["diameter_mm"] - 100.0) < 1e-6]
        row = {
            "part_id": part_id, "kind": "upper_roller", "side": side, "order_index": 0,
            "solid_count": len(ids), "solids": ";".join(map(str, ids)),
            "roller_solid": roller, "fastener_solids": ";".join(map(str, fasteners)),
            "file": path.relative_to(PROJECT_ROOT).as_posix(), "file_bytes": path.stat().st_size,
            "sha256": sha256_file(path), "density_g_cm3": density,
            **mass_columns(props),
            "compound_volume_rel_diff": volume(compound) / props["volume_mm3"] - 1,
            "roller_body_volume_mm3": body["volume_mm3"], "roller_body_mass_kg": body["mass_kg"],
            "fastener_mass_kg": fast["mass_kg"],
            **box_columns(box),
            "face_count": sum(b - a for a, b in ranges),
            "face_ranges": ";".join(f"{a}-{b - 1}" for a, b in ranges),
            "roller_axis_x_cad_mm": geometry["x_centre_cad_mm"],
            "roller_axis_y_cad_mm": geometry["axis_y_cad_mm"],
            "roller_axis_z_cad_mm": geometry["axis_z_cad_mm"],
            "roller_axis_x_body_m": axis_body[0], "roller_axis_y_body_m": axis_body[1],
            "roller_axis_z_body_m": axis_body[2], "roller_axis_dir_body": "0 1 0",
            "axis_above_ground_mm": geometry["axis_y_cad_mm"] - ground_y,
            "tread_diameter_mm": geometry["tread_diameter_mm"],
            "tread_width_mm": geometry["tread_width_mm"],
            "tread_spans_x_cad_mm": ";".join(f"{a:.3f}..{b:.3f}" for a, b in geometry["tread_spans"]),
            "tread_gap_mm": geometry["tread_gap_mm"],
            "tread_top_above_ground_mm": geometry["axis_y_cad_mm"] + 60.0 - ground_y,
            "tread_face_indices": ";".join(map(str, geometry["tread_faces"])),
            "flange_diameter_mm": geometry["flange_diameter_mm"],
            "flange_width_mm": geometry["flange_span"][1] - geometry["flange_span"][0],
            "flange_face_indices": ";".join(map(str, geometry["flange_faces"])),
            "hub_diameter_mm": hub[0]["diameter_mm"] if hub else np.nan,
            "end_cap_diameter_mm": cap[0]["diameter_mm"] if cap else np.nan,
            "rotating_volume_est_mm3": rotating["volume_mm3"],
            "rotating_mass_est_kg": rotating["mass_kg"],
            "rotating_spin_inertia_est_kg_m2": rotating["spin_inertia_kg_m2"],
            "rotating_estimate": "ESTIMATE: roller solid inside R75 cylinder about the axis over "
                                 f"X_cad {rotating['x_span_cad_mm'][0]:.1f}..{rotating['x_span_cad_mm'][1]:.1f}"
                                 " (D120/D140/D120/D100; inner shaft included, D80 boss excluded)",
        }
        rows.append(row)
        for member in members:
            mp = mass_properties([solid_shapes[member["solid"]]], density)
            solid_rows.append({
                "part_id": part_id, "side": side, "solid": member["solid"], "role": member["role"],
                "distance_to_roller_mm": member.get("distance_to_roller_mm", 0.0),
                "cache_volume_mm3": float(solids.at[member["solid"], "volume_mm3"]),
                **mass_columns(mp),
                **box_columns(np.array([solids.at[member["solid"], f"bbox_{k}_mm"] for k in BOX_KEYS])),
                "face_start": int(face_start[member["solid"]]),
                "face_count": int(face_start[member["solid"] + 1] - face_start[member["solid"]]),
                "brep_valid": member["solid"] not in invalid,
            })
        table, checks = face_rows(part_id, members, solid_shapes, face_start, invalid)
        tables.append(table)
        for key in face_checks:
            face_checks[key] += checks[key]
        groupings[part_id] = {"members": members, "neighbours_not_taken": part["neighbours"],
                              "seat_blocks": part["seat_blocks"], "rotating": rotating,
                              "bands": geometry["bands"]}
        log(f"{part_id}: solids {ids}, mass {props['mass_kg']:.3f} kg, "
            f"rotating est {rotating['mass_kg']:.3f} kg")

    rows_df = pd.DataFrame(rows)
    solids_df = pd.DataFrame(solid_rows)
    face_table = pd.concat(tables, ignore_index=True)
    rows_df.to_csv(INDEX_CSV, index=False, encoding="utf-8-sig", float_format=FLOAT_FORMAT)
    solids_df.to_csv(SOLIDS_OUT_CSV, index=False, encoding="utf-8-sig", float_format=FLOAT_FORMAT)
    face_table.to_csv(FACES_OUT, index=False, float_format=FLOAT_FORMAT)
    log(f"wrote {INDEX_CSV.name}, {SOLIDS_OUT_CSV.name}, {FACES_OUT.name} ({len(face_table)} faces)")

    import face_index

    face_index.load_crawler_upper_roller_faces.cache_clear()
    checks = verify(rows_df, solids_df, upper_run, shapes, face_table, face_checks)
    log(f"verification pass = {checks['pass']}")
    script = Path(__file__).resolve()
    payload = {
        "provenance": {
            "source_prototype_entry": CRAWLER_ENTRY,
            "source_instance_path": instance.instance_path,
            "source_file": summary["provenance"]["source_file"],
            "source_sha256": summary["provenance"]["source_sha256"],
            "inputs_sha256": {p.name: sha256_file(p) for p in (
                CRAWLER_DIR / "crawler_solids.csv", CRAWLER_DIR / "crawler_summary.json",
                UPPER_RUN_JSON)},
            "generator": script.relative_to(PROJECT_ROOT).as_posix(),
            "generator_sha256": sha256_file(script),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "run_time_s": round(time.perf_counter() - started, 1),
            "peak_memory_gb": round(psutil.Process().memory_info().peak_wset / 1e9, 2),
            "cpu": cpu,
            "note": summary["provenance"]["note"],
        },
        "frames": {
            "brep_files": "CAD world frame, mm, Y up, crawler placement applied; identity placement",
            "body_from_cad_rotation": CAD_TO_BODY.tolist(),
            "inertia": "about the part (or solid) centroid, body axes, kg m^2",
            "ground_y_cad_mm": ground_y,
        },
        "density": {"g_cm3": density, "source": density_source},
        "definitions": {
            "part": "roller solid (wheel + shaft boss + bracket merged in the shrinkwrap) + "
                    f"solids < {FASTENER_MAX_VOLUME_MM3:g} mm3 within {FASTENER_TOUCH_MM} mm "
                    "(BRepExtrema) of it",
            "roles": "roller_body, bolt_long (Y length >= 70 mm), bolt_short, washer (<= 5 mm)",
            "rotating_estimate": "see rotating_estimate column; the shrinkwrap does not separate "
                                 "the wheel from the shaft, so this is an estimate",
            "face_table": "01_cad/07_faces/crawler_upper_roller_faces.csv.gz, columns of "
                          "instance_faces.csv.gz + part_id, role; selection = upper_roller; "
                          "face_index = TopExp face order of the crawler prototype",
        },
        "parts": rows_df.to_dict("records"),
        "grouping": groupings,
        "verification": checks,
    }
    INDEX_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=float),
                          encoding="utf-8")
    log(f"done in {time.perf_counter() - started:.1f} s")


if __name__ == "__main__":
    main()
