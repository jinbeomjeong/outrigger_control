"""Crawler ground contact sheet (CAD track C7 close-out, input for S9 SCM).

Reads only cache and result files (no STEP, no B-rep):

* ``01_cad/06_brep/derived/crawler/``: ``crawler_summary.json``,
  ``crawler_wheels.csv``, ``crawler_grouser_tips.csv``, ``crawler_solids.csv``,
  ``crawler_contact_parts.csv`` (all written by ``derive_crawler_cache.py`` /
  ``derive_crawler_parts.py``; not modified here),
* ``02_params/rexome33.yaml`` (crawler block, read only),
* ``06_analysis/00_dynamics/reference.json`` and ``leg_extension_loads.json``
  (crawler values used by the reference solutions),
* ``07_results/S2b/crawler_{top,middle,bottom}/result.json`` (static crawler
  sphere forces, mass case C, exact geometry).

Writes ``crawler_ground_sheet.json`` and ``crawler_ground_sheet.png`` next to
the crawler derived cache:

1. cross-check table CAD <-> YAML <-> reference/S2b,
2. contact rectangles per track (body frame, m) and the face-based contact
   length / area per height band (three band definitions, see ``BAND_DEFS``),
3. static crawler load per track and auger level, mean contact pressures for
   several area definitions, roller-to-shoe mapping (load concentration),
4. SCM active-domain proposal for a 2 cm grid.

Frames: CAD world mm, Y up; body frame x = +Z_cad, y = +X_cad, z = +Y_cad,
CAD origin, m (``02_params/rexome33.yaml`` ``frames``). Heights are above the
crawler floor (lowest crawler point, Y_cad = ``ground_y_mm``).

Run from the project root::

    & C:\\ProgramData\\miniforge3\\envs\\Chrono-dev\\python.exe -I 04_scripts\\00_cad\\build_crawler_ground_sheet.py
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CRAWLER_DIR = PROJECT_ROOT / "01_cad" / "06_brep" / "derived" / "crawler"
YAML_PATH = PROJECT_ROOT / "02_params" / "rexome33.yaml"
REFERENCE_PATH = PROJECT_ROOT / "06_analysis" / "00_dynamics" / "reference.json"
LEG_LOADS_PATH = PROJECT_ROOT / "06_analysis" / "00_dynamics" / "leg_extension_loads.json"
S2B_DIR = PROJECT_ROOT / "07_results" / "S2b"
OUT_JSON = CRAWLER_DIR / "crawler_ground_sheet.json"
OUT_PNG = CRAWLER_DIR / "crawler_ground_sheet.png"

MM_PER_M = 1000.0
AUGER_LEVELS = ("top", "middle", "bottom")
PAD_AREA_MM2 = 2108.5          # grouser pad plane (4 per shoe), same rule as export_params.py
BLOCK_PLANE_AREA_MM2 = 32501.3  # shoe block bottom plane 4 mm above the pads
AREA_TOL_MM2 = 1.0
BANDS_MM = (1.0, 3.0, 5.0, 10.0, 15.0, 22.0)
SINKAGE_MM = (0.0, 2.5, 5.0, 10.0, 15.0, 22.0)
SCM_GRID_M = 0.02              # S9 grid (roadmap: SCM 2 cm grid)
SCM_MARGIN_M = 0.10            # ASSUMPTION: soil bulldozing / ray margin around the shoe blocks (5 cells)
SCM_Z_SIZE_M = 0.40            # ASSUMPTION: active-domain height (covers ground -0.2 ... +0.2 m)
JOINT_SHARE_MM = 15.0         # ASSUMPTION: a roller within this distance of a track joint loads both shoes
BAND_DEFS = {
    "centroid": "face counted if its centroid height <= band (crawler_summary.json definition)",
    "lowest_point": "face counted (whole face) if its lowest point <= band",
    "surface_part": "only the part of each (tilted) face lower than the band; area pro rata to the length along x",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def r(value: float, nd: int = 4) -> float:
    return float(round(float(value), nd))


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------
def load_inputs() -> dict:
    files = {
        "summary": CRAWLER_DIR / "crawler_summary.json",
        "wheels": CRAWLER_DIR / "crawler_wheels.csv",
        "tips": CRAWLER_DIR / "crawler_grouser_tips.csv",
        "solids": CRAWLER_DIR / "crawler_solids.csv",
        "parts": CRAWLER_DIR / "crawler_contact_parts.csv",
        "yaml": YAML_PATH,
        "reference": REFERENCE_PATH,
        "leg_loads": LEG_LOADS_PATH,
    }
    for level in AUGER_LEVELS:
        files[f"s2b_{level}"] = S2B_DIR / f"crawler_{level}" / "result.json"
    data = {"files": files}
    data["summary"] = json.loads(files["summary"].read_text(encoding="utf-8"))
    data["wheels"] = pd.read_csv(files["wheels"], encoding="utf-8-sig")
    data["tips"] = pd.read_csv(files["tips"], encoding="utf-8-sig")
    data["solids"] = pd.read_csv(files["solids"], encoding="utf-8-sig")
    data["parts"] = pd.read_csv(files["parts"], encoding="utf-8-sig")
    data["yaml"] = yaml.safe_load(files["yaml"].read_text(encoding="utf-8"))
    data["reference"] = json.loads(files["reference"].read_text(encoding="utf-8"))
    data["leg_loads"] = json.loads(files["leg_loads"].read_text(encoding="utf-8"))
    data["s2b"] = {lv: json.loads(files[f"s2b_{lv}"].read_text(encoding="utf-8")) for lv in AUGER_LEVELS}
    return data


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------
def ground_faces(tips: pd.DataFrame, ground_y_mm: float) -> pd.DataFrame:
    """Downward pad and block-bottom planes with lowest/highest point and slope along Z_cad."""
    faces = tips[(tips["normal_y"] < -0.99)].copy()
    is_pad = (faces["area_mm2"] - PAD_AREA_MM2).abs() < AREA_TOL_MM2
    is_block = (faces["area_mm2"] - BLOCK_PLANE_AREA_MM2).abs() < AREA_TOL_MM2
    faces = faces[is_pad | is_block].copy()
    faces["kind"] = np.where((faces["area_mm2"] - PAD_AREA_MM2).abs() < AREA_TOL_MM2, "pad", "block_bottom")
    faces["lo_mm"] = faces["bbox_min_y_mm"] - ground_y_mm
    faces["hi_mm"] = faces["bbox_max_y_mm"] - ground_y_mm
    faces["hc_mm"] = faces["centroid_y_mm"] - ground_y_mm
    # plane n . dp = 0  ->  dY/dZ = -n_z / n_y (n_x = 0 for these faces)
    faces["dy_dz"] = -faces["normal_z"] / faces["normal_y"]
    faces = faces[faces["lo_mm"] < 30.0]
    return faces


def band_extent(faces: pd.DataFrame, side: str, band: float, how: str) -> dict:
    """Contact extent and area of one side within a height band."""
    f = faces[faces["side"] == side]
    zs, xs, area = [], [], 0.0
    for row in f.itertuples(index=False):
        z0, z1 = row.bbox_min_z_mm, row.bbox_max_z_mm
        if how == "centroid":
            if row.hc_mm > band:
                continue
            frac = 1.0
        elif how == "lowest_point":
            if row.lo_mm > band:
                continue
            frac = 1.0
        else:  # surface_part
            if row.lo_mm > band:
                continue
            if abs(row.dy_dz) < 1e-9 or row.hi_mm <= band:
                frac = 1.0
            else:
                # height h(z) = hc + dy_dz (z - zc); keep the z part with h <= band
                z_cut = row.centroid_z_mm + (band - row.hc_mm) / row.dy_dz
                if row.dy_dz > 0:
                    z1 = min(z1, z_cut)
                else:
                    z0 = max(z0, z_cut)
                frac = max(0.0, (z1 - z0) / (row.bbox_max_z_mm - row.bbox_min_z_mm))
        zs += [z0, z1]
        xs += [row.bbox_min_x_mm, row.bbox_max_x_mm]
        area += row.area_mm2 * frac
    if not zs:
        return {"length_mm": 0.0, "area_mm2": 0.0}
    return {
        "x_body_m": [r(min(zs) / MM_PER_M, 5), r(max(zs) / MM_PER_M, 5)],
        "y_body_m": [r(min(xs) / MM_PER_M, 5), r(max(xs) / MM_PER_M, 5)],
        "length_mm": r(max(zs) - min(zs), 4),
        "width_mm": r(max(xs) - min(xs), 2),
        "area_mm2": r(area, 3),
        "face_count": int(len(zs) // 2),
    }


def shoe_table(parts: pd.DataFrame, solids: pd.DataFrame, faces: pd.DataFrame, side: str) -> pd.DataFrame:
    """Ground shoes (flat + end) of one side: station x, gap, block bbox (body m)."""
    sid = solids.set_index("solid")
    shoes = parts[(parts["side"] == side) & parts["kind"].isin(["flat_shoe", "end_shoe"])].copy()
    rows = []
    for row in shoes.itertuples(index=False):
        s = sid.loc[int(row.ground_shoe_solid)]
        f = faces[faces["solid"] == int(row.ground_shoe_solid)]
        pads = f[f["kind"] == "pad"]
        block = f[f["kind"] == "block_bottom"]
        rows.append({
            "part_id": row.part_id,
            "kind": row.kind,
            "station_x_body_m": float(row.station_x_body_m),
            "gap_mm": float(row.grouser_lowest_above_ground_mm),
            "tilt_deg": float(row.ground_tilt_deg),
            "block_x_body_m": [s.bbox_min_z_mm / MM_PER_M, s.bbox_max_z_mm / MM_PER_M],
            "block_y_body_m": [s.bbox_min_x_mm / MM_PER_M, s.bbox_max_x_mm / MM_PER_M],
            "pad_count": int(len(pads)),
            "pad_area_mm2": float(pads["area_mm2"].sum()),
            "block_bottom_lowest_mm": float(block["lo_mm"].min()) if len(block) else math.nan,
            "block_bottom_area_mm2": float(block["area_mm2"].sum()),
            "block_bottom_x_body_m": ([block["bbox_min_z_mm"].min() / MM_PER_M, block["bbox_max_z_mm"].max() / MM_PER_M]
                                      if len(block) else None),
            "block_bottom_y_body_m": ([block["bbox_min_x_mm"].min() / MM_PER_M, block["bbox_max_x_mm"].max() / MM_PER_M]
                                      if len(block) else None),
            "pads": [[p.bbox_min_z_mm / MM_PER_M, p.bbox_max_z_mm / MM_PER_M, p.bbox_min_x_mm / MM_PER_M,
                      p.bbox_max_x_mm / MM_PER_M] for p in pads.itertuples(index=False)],
        })
    return pd.DataFrame(rows).sort_values("station_x_body_m").reset_index(drop=True)


def shoe_plate_gap_height_mm(tips: pd.DataFrame, ground_y_mm: float, side: str) -> float:
    """Most frequent height of the 600 mm wide downward planes between 20 and 60 mm (shoe plate underside)."""
    t = tips[(tips["side"] == side) & (tips["normal_y"] < -0.99)]
    t = t[(t["bbox_max_x_mm"] - t["bbox_min_x_mm"]) > 590.0]
    h = (t["centroid_y_mm"] - ground_y_mm).round(1)
    h = h[(h > 20.0) & (h < 60.0)]
    return float(h.mode().iloc[0])


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    t_start = time.perf_counter()
    d = load_inputs()
    summ, tips, solids, parts, wheels = d["summary"], d["tips"], d["solids"], d["parts"], d["wheels"]
    y_cfg = d["yaml"]
    cr_yaml = y_cfg["contact"]["crawler"]
    lay = cr_yaml["sphere_layout"]
    g0 = float(summ["ground_y_mm"])
    faces = ground_faces(tips, g0)

    # ---------------- shoe tables, pitch, heights ----------------
    shoes = {s: shoe_table(parts, solids, faces, s) for s in ("L", "R")}
    side_name = {"L": "left", "R": "right"}
    shL = shoes["L"]
    flat = shL[shL["kind"] == "flat_shoe"]
    pitch_mm = float(summ["shoe_pitch"]["pitch_mm_median"])
    block_len_mm = float(np.median([(b[1] - b[0]) * MM_PER_M for b in flat["block_x_body_m"]]))
    block_w_mm = float(np.median([(b[1] - b[0]) * MM_PER_M for b in flat["block_y_body_m"]]))
    bb_len_mm = float(np.median([(b[1] - b[0]) * MM_PER_M for b in flat["block_bottom_x_body_m"]]))
    bb_w_mm = float(np.median([(b[1] - b[0]) * MM_PER_M for b in flat["block_bottom_y_body_m"]]))
    pad_lo = faces[(faces["kind"] == "pad")]
    flat_pad_h = float(pad_lo[pad_lo["solid"].isin(
        parts[parts["kind"] == "flat_shoe"]["ground_shoe_solid"].astype(int))]["lo_mm"].max())
    block_bottom_h = float(flat["block_bottom_lowest_mm"].median())
    plate_gap_h = shoe_plate_gap_height_mm(tips, g0, "left")
    gap_between_blocks_mm = pitch_mm - block_len_mm
    per_shoe_pad_area = float(flat["pad_area_mm2"].median())
    per_shoe_block_area = per_shoe_pad_area + float(flat["block_bottom_area_mm2"].median())

    # ---------------- band table ----------------
    bands = {}
    for how in BAND_DEFS:
        bands[how] = {f"{b:g}mm": {side_name[s]: band_extent(faces, side_name[s], b, how) for s in ("L", "R")}
                      for b in BANDS_MM}
    # reproduction of crawler_summary.json (centroid definition) as a self-check
    repro = []
    for key in ("1mm", "3mm", "5mm", "10mm"):
        for side in ("left", "right"):
            s_ref = summ["ground_patches_by_band"][key][side]
            mine = bands["centroid"][key][side]
            repro.append(max(abs(mine["length_mm"] - s_ref["length_mm"]), abs(mine["area_mm2"] - s_ref["tip_area_mm2"])))
    repro_max = float(max(repro))

    # ---------------- rectangles (body m) ----------------
    rects = {}
    for s in ("L", "R"):
        sh = shoes[s]
        fl = sh[sh["kind"] == "flat_shoe"]
        p1 = bands["centroid"]["1mm"][side_name[s]]
        rects[side_name[s]] = {
            "pad_tips_flat_1mm": {"x_m": p1["x_body_m"], "y_m": p1["y_body_m"],
                                  "length_mm": p1["length_mm"], "width_mm": p1["width_mm"],
                                  "note": "outer envelope of the 4 x 10 grouser pads at height 0 (rigid floor contact)"},
            "block_bottom_flat": {
                "x_m": [r(min(b[0] for b in fl["block_bottom_x_body_m"]), 5), r(max(b[1] for b in fl["block_bottom_x_body_m"]), 5)],
                "y_m": [r(min(b[0] for b in fl["block_bottom_y_body_m"]), 5), r(max(b[1] for b in fl["block_bottom_y_body_m"]), 5)],
                "height_mm": r(block_bottom_h, 2),
                "note": "envelope of the flat shoe block bottom planes (+4 mm), 10 shoes"},
            "block_outline_flat": {
                "x_m": [r(min(b[0] for b in fl["block_x_body_m"]), 5), r(max(b[1] for b in fl["block_x_body_m"]), 5)],
                "y_m": [r(min(b[0] for b in fl["block_y_body_m"]), 5), r(max(b[1] for b in fl["block_y_body_m"]), 5)],
                "note": "bbox of the 10 flat ground-shoe solids (600 mm wide blocks)"},
            "block_outline_all_contact_shoes": {
                "x_m": [r(min(b[0] for b in sh["block_x_body_m"]), 5), r(max(b[1] for b in sh["block_x_body_m"]), 5)],
                "y_m": [r(min(b[0] for b in sh["block_y_body_m"]), 5), r(max(b[1] for b in sh["block_y_body_m"]), 5)],
                "note": "bbox of 10 flat + 6 end shoe blocks (end shoes are raised 2.2 ... 21.5 mm)"},
        }
    for v in rects.values():
        for rr in v.values():
            rr["length_m"] = r(rr["x_m"][1] - rr["x_m"][0], 5)
            rr["width_m"] = r(rr["y_m"][1] - rr["y_m"][0], 5)
            rr["centre_m"] = [r(0.5 * (rr["x_m"][0] + rr["x_m"][1]), 5), r(0.5 * (rr["y_m"][0] + rr["y_m"][1]), 5)]

    # ---------------- sinkage engagement ----------------
    sink = []
    for s_mm in SINKAGE_MM:
        eng = shL[shL["gap_mm"] <= s_mm + 1e-3]
        ext = band_extent(faces, "left", s_mm + 1e-6, "surface_part")
        sink.append({
            "sinkage_mm": s_mm,
            "engaged_shoes_per_track": int(len(eng)),
            "engaged_end_shoes": eng[eng["kind"] == "end_shoe"]["part_id"].tolist(),
            "contact_length_surface_part_mm": ext["length_mm"],
            "contact_area_surface_part_mm2_per_track": ext["area_mm2"],
            "note": "rigid track pressed vertically into a soil surface (no tilt); faces = pads + block bottoms only",
        })
    sink.append({"sinkage_mm": r(plate_gap_h, 1), "note": "shoe plate underside in the 43 mm gaps between blocks starts to bear; "
                 "above this the whole 600 mm x length outline bears (estimate)"})

    # ---------------- roller stations and roller-to-shoe mapping ----------------
    rl = wheels[(wheels["side"] == "left") & (wheels["role"].str.contains("track roller"))].sort_values("axis_x_body_m")
    roller_x = rl["axis_x_body_m"].to_numpy()
    roller_d = float(rl["max_round_diameter_mm"].median())
    roller_spacing = np.diff(roller_x) * MM_PER_M
    st = shL["station_x_body_m"].to_numpy()
    bounds = np.concatenate([[st[0] - pitch_mm / 2 / MM_PER_M], 0.5 * (st[1:] + st[:-1]), [st[-1] + pitch_mm / 2 / MM_PER_M]])
    mapping = []
    for i, x in enumerate(roller_x):
        k = int(np.searchsorted(bounds, x) - 1)
        shoe = shL.iloc[k]
        dist_joint = min(x - bounds[k], bounds[k + 1] - x) * MM_PER_M
        mapping.append({
            "roller": f"roller_L{i + 1}", "roller_x_m": r(x, 4),
            "shoe_under_roller": shoe["part_id"], "shoe_kind": shoe["kind"], "shoe_gap_mm": r(shoe["gap_mm"], 2),
            "shoe_station_x_m": r(shoe["station_x_body_m"], 4),
            "offset_from_shoe_centre_mm": r((x - shoe["station_x_body_m"]) * MM_PER_M, 1),
            "distance_to_nearest_joint_mm": r(dist_joint, 1),
            "nearest_joint_x_m": r(bounds[k] if x - bounds[k] < bounds[k + 1] - x else bounds[k + 1], 4),
        })
        near_k = k - 1 if x - bounds[k] < bounds[k + 1] - x else k + 1
        shared = dist_joint <= JOINT_SHARE_MM and 0 <= near_k < len(shL)
        mapping[-1]["shoes_loaded"] = [shoe["part_id"]] + ([shL.iloc[near_k]["part_id"]] if shared else [])
    loaded = {p for m in mapping for p in m["shoes_loaded"]}
    shoes_without_roller = [p for p in flat["part_id"] if p not in loaded]
    # end-roller load point sensitivity: sum x^2 of the roller stations about x = 0
    x_alt = roller_x.copy()
    x_alt[0], x_alt[-1] = mapping[0]["nearest_joint_x_m"], mapping[-1]["nearest_joint_x_m"]
    lever = {
        "sum_x2_rollers_m2 (about x = 0)": r(float(np.sum(roller_x ** 2)), 5),
        "sum_x2_end_rollers_at_nearest_joint_m2": r(float(np.sum(x_alt ** 2)), 5),
        "ratio": r(float(np.sum(x_alt ** 2) / np.sum(roller_x ** 2)), 4),
        "note": "end rollers sit over the first raised shoes in this CAD track phase; if their load reaches the floor at the "
                "nearest joint instead of the roller axis, the roller-row pitch stiffness changes by this ratio "
                "(equal sphere stiffness, end shoes ignored; changes with the track phase by up to half a pitch)",
    }

    # ---------------- loads (S2b exact, reference linear) ----------------
    ref_lay = d["reference"]["lift_V4_compliant_crawler"]["layouts"]["D rollers + gapped end shoes (YAML contact.crawler.sphere_layout)"]
    ref_f = np.array(ref_lay["settled_on_crawler (legs at 0)"]["crawler_sphere_forces_N"], float)
    nr, ne = len(lay["roller_x_m"]), len(lay["end_shoe_x_m"])
    x_st = np.array(list(lay["roller_x_m"]) + list(lay["end_shoe_x_m"]), float)
    area_defs = {
        "A1_pad_tips_flat (rigid floor, 40 pads)": per_shoe_pad_area * 10 / MM_PER_M ** 2,
        "A2_block_bottoms_flat (soil, sinkage > 4 mm, 10 shoes)": per_shoe_block_area * 10 / MM_PER_M ** 2,
        "A3_rect_pad_width_x_flat_length (0.422 x 1.637)": rects["left"]["pad_tips_flat_1mm"]["width_m"] * rects["left"]["pad_tips_flat_1mm"]["length_m"],
        "A4_rect_block_bottom (0.489 x flat block-bottom length)": rects["left"]["block_bottom_flat"]["width_m"] * rects["left"]["block_bottom_flat"]["length_m"],
        "A5_rect_block_outline (0.600 x flat block length)": rects["left"]["block_outline_flat"]["width_m"] * rects["left"]["block_outline_flat"]["length_m"],
        "A6_reference_only (0.600 x (roller span + roller diameter))": 0.600 * ((roller_x[-1] - roller_x[0]) + roller_d / MM_PER_M),
    }
    x_c = rects["left"]["pad_tips_flat_1mm"]["centre_m"][0]
    L_flat = rects["left"]["pad_tips_flat_1mm"]["length_m"]
    b_block = rects["left"]["block_bottom_flat"]["width_m"]
    loads = {}
    for lv in AUGER_LEVELS:
        res = d["s2b"][lv]
        f = np.array(res["analytic_exact"]["sphere_force_N"], float)
        labels = res["sphere_labels"]
        W = float(res["analytic_exact"]["weight_N"])
        per = {}
        for side, sgn in (("L", "left"), ("R", "right")):
            idx = [i for i, lab in enumerate(labels) if lab.startswith(side + "-")]
            fs = f[idx]
            labs = [labels[i] for i in idx]
            xs = np.array([x_st[int(l.split("-")[-1]) + (nr if "end_shoe" in l else 0)] for l in labs])
            F = float(fs.sum())
            x_cop = float((fs * xs).sum() / F)
            e = x_cop - x_c
            roller_f = fs[:nr]
            per[sgn] = {
                "station_forces_N": {l: r(v, 1) for l, v in zip(labs, fs) if v != 0.0 or "roller" in l},
                "total_N": r(F, 1),
                "share_of_weight": r(F / W, 5),
                "x_centre_of_pressure_m": r(x_cop, 4),
                "eccentricity_vs_flat_centre_m": r(e, 4),
                "kern_limit_L_over_6_m": r(L_flat / 6, 4),
                "mean_pressure_kPa": {k: r(F / a / 1e3, 1) for k, a in area_defs.items()},
                "winkler_rigid_track_estimate (ASSUMPTION)": (
                    {"p_max_kPa": r(2 * F / (3 * b_block * (L_flat / 2 - e)) / 1e3, 1),
                     "contact_length_m": r(3 * (L_flat / 2 - e), 3),
                     "note": "e > L/6: triangular pressure on a linear Winkler soil, block-bottom width, flat length only; "
                             "end shoes ignored (they shorten the lever when the soil yields)"}
                    if e > L_flat / 6 else
                    {"p_max_kPa": r(F / (b_block * L_flat) * (1 + 6 * e / L_flat) / 1e3, 1),
                     "p_min_kPa": r(F / (b_block * L_flat) * (1 - 6 * e / L_flat) / 1e3, 1)}),
                "roller_station_pressure_kPa": {
                    "front_roller_on_one_shoe_pads (rigid floor)": r(roller_f[-1] / (per_shoe_pad_area / MM_PER_M ** 2) / 1e3, 0),
                    "front_roller_on_one_shoe_block (soil)": r(roller_f[-1] / (per_shoe_block_area / MM_PER_M ** 2) / 1e3, 1),
                    "front_roller_tributary_357mm_x_block_width (soil)": r(roller_f[-1] / (0.357 * b_block) / 1e3, 1),
                    "rear_roller_tributary_357mm_x_block_width (soil)": r(roller_f[0] / (0.357 * b_block) / 1e3, 1),
                },
            }
        loads[lv] = {
            "source": f"07_results/S2b/crawler_{lv}/result.json analytic_exact (exact geometry, mass case C)",
            "weight_N": r(W, 2),
            "sum_sphere_forces_N": r(f.sum(), 2),
            "equilibrium_rel_diff": float(abs(f.sum() - W) / W),
            "chrono_window_crawler_fz_mean_N": r(res["window"]["crawler_fz_mean_N"], 2),
            "chrono_vs_weight_rel_diff": float(abs(res["window"]["crawler_fz_mean_N"] - W) / W),
            "pose_uz_mm_roll_deg_pitch_deg": [r(res["analytic_exact"]["u_z_mm"], 4), r(res["analytic_exact"]["roll_deg"], 6),
                                              r(res["analytic_exact"]["pitch_deg"], 5)],
            "active_spheres": int(res["analytic_exact"]["active"]),
            "tracks": per,
        }
    ref_left = np.concatenate([ref_f[:nr], ref_f[2 * nr:2 * nr + ne]])
    s2b_top = np.array(d["s2b"]["top"]["analytic_exact"]["sphere_force_N"], float)
    lab_top = d["s2b"]["top"]["sphere_labels"]
    s2b_left = np.array([s2b_top[i] for i, l in enumerate(lab_top) if l.startswith("L-")])
    loads["reference_json_top_linear"] = {
        "source": "reference.json lift_V4_compliant_crawler / layouts / D ... / settled_on_crawler (legs at 0) (linear, no P-delta)",
        "left_track_total_N": r(ref_left.sum(), 1),
        "max_abs_diff_vs_S2b_exact_left_N": r(np.max(np.abs(ref_left - s2b_left)), 1),
        "note": "difference is the small-angle linearisation (P-delta), not a dimension difference",
    }

    # ---------------- cross-check ----------------
    cp = parts.set_index("part_id")
    roll_cad = cp[(cp["kind"] == "roller") & (cp["side"] == "L")].sort_values("order_index")["station_x_body_m"].to_numpy()
    es = cp[(cp["kind"] == "end_shoe") & (cp["side"] == "L")].sort_values("order_index")
    es_x_cad, es_gap_cad = es["station_x_body_m"].to_numpy(), es["gap_m"].to_numpy()
    ref_note = d["reference"]["kinematics"].get("note_slope", "")
    solL = solids[solids["side"] == "left"]
    lm = d["leg_loads"]["meta"]
    cross = [
        {"item": "track centre half spacing", "cad": f"+{summ['track_centre_half_spacing_mm']:.4f} mm (left), "
                 f"{rects['right']['pad_tips_flat_1mm']['centre_m'][1] * MM_PER_M:.4f} mm (right pad centre)",
         "yaml": f"sphere_layout.track_centre_y_m = {lay['track_centre_y_m']}",
         "reference": f"reference.json layouts D track_centre_y_m = {ref_lay['track_centre_y_m']}; leg_extension_loads via dyn_model.crawler_points (YAML)",
         "diff_mm": r(abs(summ["track_centre_half_spacing_mm"] - lay["track_centre_y_m"] * MM_PER_M), 4), "verdict": "match"},
        {"item": "ground width of the grouser pads", "cad": f"{summ['shoe_ground_width_mm']:.2f} mm (block bottom {bb_w_mm:.1f}, block {block_w_mm:.1f})",
         "yaml": "not used (no key)", "reference": "not used",
         "diff_mm": None, "verdict": "not used by the models (SCM input only)"},
        {"item": "flat ground length (+1 mm)", "cad": f"{bands['centroid']['1mm']['left']['length_mm']:.1f} mm, x {bands['centroid']['1mm']['left']['x_body_m']} m",
         "yaml": "not used (roller_x_m / end_shoe_x_m instead)",
         "reference": "reference.json kinematics: crawler as rigid box " + ref_note.split("crawler treated as a rigid box ")[-1][:60],
         "diff_mm": None, "verdict": "not used for contact; the box is the crawler bbox for clearance only "
                                     f"(CAD bbox x {solL.bbox_min_z_mm.min():.1f} ... {solL.bbox_max_z_mm.max():.1f} mm, |y| max {solids.bbox_max_x_mm.max():.1f} mm)"},
        {"item": "track rollers", "cad": f"{len(roll_cad)}/side, D {roller_d:.1f} mm, x {np.round(roll_cad, 4).tolist()} m, spacing {np.round(roller_spacing, 3).tolist()} mm",
         "yaml": f"roller_x_m = {lay['roller_x_m']}", "reference": "S2b/reference use the YAML list (24 spheres, labels L/R-roller-0..5)",
         "diff_mm": r(np.max(np.abs(roll_cad - np.array(lay["roller_x_m"]))) * MM_PER_M, 4), "verdict": "match (0.1 mm rounding)"},
        {"item": "end shoe stations", "cad": f"x {np.round(es_x_cad, 5).tolist()} m",
         "yaml": f"end_shoe_x_m = {lay['end_shoe_x_m']}", "reference": "via YAML",
         "diff_mm": r(np.max(np.abs(es_x_cad - np.array(lay["end_shoe_x_m"]))) * MM_PER_M, 4), "verdict": "match (0.1 mm rounding)"},
        {"item": "end shoe gaps", "cad": f"{np.round(es_gap_cad * MM_PER_M, 3).tolist()} mm",
         "yaml": f"end_shoe_gap_m = {lay['end_shoe_gap_m']}", "reference": "via YAML",
         "diff_mm": r(np.max(np.abs(es_gap_cad - np.array(lay["end_shoe_gap_m"]))) * MM_PER_M, 4), "verdict": "match (0.01 mm rounding)"},
        {"item": "crawler floor height", "cad": f"Y_cad {g0:.4f} mm = z {g0 / MM_PER_M:.7f} m",
         "yaml": f"ground.crawler_bottom_z_m = {y_cfg['ground']['crawler_bottom_z_m']}",
         "reference": "reference / S2b / leg_extension_loads floor at ground.crawler_bottom_z_m",
         "diff_mm": r(abs(g0 / MM_PER_M - y_cfg["ground"]["crawler_bottom_z_m"]) * MM_PER_M, 4),
         "verdict": "match (0.1 mm rounding; shifts every contact height equally, no static effect)"},
        {"item": "mass case / level of the loads", "cad": "case C (auger_levels.json), three levels",
         "yaml": "superstructure.auger_levels.*", "reference": f"leg_extension_loads: level {lm['auger_level']}, case {lm['mass_case']}; S2b: top/middle/bottom",
         "diff_mm": None, "verdict": "consistent"},
    ]

    # ---------------- SCM active domain ----------------
    scm = {}
    allx = [b for sh in shoes.values() for b in sh["block_x_body_m"]]
    x0 = min(b[0] for b in allx) - SCM_MARGIN_M
    x1 = max(b[1] for b in allx) + SCM_MARGIN_M
    first_end = shL[(shL["kind"] == "end_shoe") & (shL["gap_mm"] < 3.0)]
    fl_all = pd.concat([flat, first_end])
    xr0 = min(b[0] for b in fl_all["block_x_body_m"]) - SCM_MARGIN_M
    xr1 = max(b[1] for b in fl_all["block_x_body_m"]) + SCM_MARGIN_M
    for name, (xa, xb) in {"full (10 flat + 6 end shoes per track)": (x0, x1),
                           "reduced (10 flat + first end shoe at each end)": (xr0, xr1)}.items():
        boxes = {}
        nodes = 0
        for s in ("L", "R"):
            yy = rects[side_name[s]]["block_outline_flat"]["y_m"]
            ya, yb = yy[0] - SCM_MARGIN_M, yy[1] + SCM_MARGIN_M
            nx = int(math.ceil((xb - xa) / SCM_GRID_M)) + 1
            ny = int(math.ceil((yb - ya) / SCM_GRID_M)) + 1
            nodes += nx * ny
            boxes[side_name[s]] = {"centre_body_m": [r(0.5 * (xa + xb), 4), r(0.5 * (ya + yb), 4), r(g0 / MM_PER_M, 4)],
                                   "size_m": [r(xb - xa, 4), r(yb - ya, 4), SCM_Z_SIZE_M],
                                   "x_m": [r(xa, 4), r(xb, 4)], "y_m": [r(ya, 4), r(yb, 4)], "grid_nodes": nx * ny}
        scm[name] = {"boxes": boxes, "grid_nodes_both_tracks": nodes}
    scm_meta = {
        "grid_m": SCM_GRID_M,
        "margin_m (ASSUMPTION)": SCM_MARGIN_M,
        "z_size_m (ASSUMPTION)": SCM_Z_SIZE_M,
        "api": "pychrono.vehicle.SCMTerrain.AddActiveDomain(body, centre, size): OOBB in the frame of the body that carries the "
               "crawler contact shapes (superstructure body); centre z at the floor",
        "cells_across_features": {"pad_width_64mm": r(64.16 / (SCM_GRID_M * MM_PER_M), 1),
                                   "block_bottom_flat_length_88mm": r(bb_len_mm / (SCM_GRID_M * MM_PER_M), 1),
                                   "gap_between_blocks_mm": r(gap_between_blocks_mm / (SCM_GRID_M * MM_PER_M), 1),
                                   "block_width_600mm": r(block_w_mm / (SCM_GRID_M * MM_PER_M), 1)},
        "note": "the 4 mm pad step and 64 mm pads are near/below the 2 cm grid: on SCM model each shoe as a flat block "
                "bottom (489 x 88 mm, or the 600 x 130 mm outline); the r = 0.05 m spheres of layout D are a rigid-floor "
                "model and would act as point punches on SCM (proposal for dynamics-expert)",
    }

    elapsed = time.perf_counter() - t_start
    out = {
        "provenance": {
            "generator": rel(Path(__file__)),
            "generator_sha256": sha256_file(Path(__file__)),
            "created_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "inputs": {k: {"path": rel(p), "sha256": sha256_file(p)} for k, p in d["files"].items()},
            "runtime_s": r(elapsed, 2),
            "note": "cache-only (no STEP, no B-rep); the drawn undercarriage is the REXOME25 model per the STEP description",
        },
        "frames": "body axes x = +Z_cad (forward), y = +X_cad (left), z = +Y_cad (up), CAD origin, m; heights in mm above "
                  f"the crawler floor Y_cad = {g0:.4f} mm (z = {g0 / MM_PER_M:.6f} m)",
        "cross_check": cross,
        "shoe_geometry": {
            "pitch_mm": pitch_mm,
            "ground_shoe_block_mm (x length, y width, height)": [r(block_len_mm, 1), r(block_w_mm, 1), 72.0],
            "block_bottom_plane_mm (x, y)": [r(bb_len_mm, 1), r(bb_w_mm, 1)],
            "block_bottom_height_above_pads_mm": r(block_bottom_h, 2),
            "pad_per_shoe": {"count": 4, "area_each_mm2": PAD_AREA_MM2, "width_y_mm": 64.16,
                             "flat_shoe_pad_lowest_max_mm": r(flat_pad_h, 6)},
            "gap_between_blocks_x_mm": r(gap_between_blocks_mm, 1),
            "shoe_plate_underside_in_gap_height_mm": r(plate_gap_h, 1),
            "grouser_height_mm": {"block_bottom_to_plate_underside": r(plate_gap_h - block_bottom_h, 1),
                                  "pad_tip_to_plate_underside": r(plate_gap_h, 1),
                                  "pad_protrusion_below_block": r(block_bottom_h, 1),
                                  "note": "no bar grousers: each ground shoe is a 600 x 130 x 72 mm block with 4 pads; "
                                          "the block below the plate acts as the grouser (shape-based reading, ASSUMPTION)"},
            "area_per_shoe_mm2": {"pads": r(per_shoe_pad_area, 1), "pads_plus_block_bottom": r(per_shoe_block_area, 1)},
        },
        "rectangles_body_m": rects,
        "bands": {"definitions": BAND_DEFS, "per_band": bands,
                  "summary_reproduction_max_abs_diff (mm or mm^2)": r(repro_max, 6)},
        "sinkage_engagement_left_track": sink,
        "end_shoes_left": shL[shL["kind"] == "end_shoe"][["part_id", "station_x_body_m", "gap_mm", "tilt_deg"]]
            .round(5).to_dict(orient="records"),
        "rollers": {"count_per_track": int(len(roller_x)), "diameter_mm": roller_d,
                    "x_m": np.round(roller_x, 4).tolist(), "spacing_mm": np.round(roller_spacing, 3).tolist(),
                    "spacing_over_pitch": r(float(np.median(roller_spacing)) / pitch_mm, 3),
                    "roller_bottom_above_floor_mm": float(rl["bottom_height_mm"].median()),
                    "roller_to_shoe_left": mapping,
                    "flat_shoes_without_roller_above": shoes_without_roller,
                    "joint_share_threshold_mm (ASSUMPTION)": JOINT_SHARE_MM,
                    "end_roller_lever_sensitivity": lever},
        "loads_case_C": loads,
        "area_definitions_m2_per_track": {k: r(v, 5) for k, v in area_defs.items()},
        "scm_active_domain": {"meta": scm_meta, "variants": scm},
        "uncertainties": {
            "U_len_1mm_vs_3mm": "1,636.7 mm (+1 mm, all definitions) vs 1.84 m (earlier render-mesh vertex selection at +3 mm): "
                                "the earlier value includes the inner edge of the first raised end shoe pads (lowest point 2.23 / 2.37 mm). "
                                "See bands.per_band.*.3mm: centroid / lowest_point / surface_part.",
            "U_block_bottom_plus4mm": "+4.0 mm plane 489 x 88 mm per shoe = ground-shoe block bottom; pads protrude 4 mm.",
            "U7_upper_roller": "one carrier roller per track in the drawn model (body x 0.000 m, z -0.3327 m, tread dia "
                               "120 mm; see derived/crawler/upper_run_check.json and crawler_upper_rollers.csv). It "
                               "supports the upper run only and carries no ground load, so it is not part of this sheet.",
            "U8_REXOME25_undercarriage": "all values are the drawn REXOME25 undercarriage; manufacturer confirmation pending.",
        },
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    plot(out, shoes, wheels, solids, d)
    print(f"wrote {rel(OUT_JSON)} and {rel(OUT_PNG)} in {time.perf_counter() - t_start:.1f} s; "
          f"summary reproduction max diff {repro_max:.2e}")


# --------------------------------------------------------------------------
# Figure
# --------------------------------------------------------------------------
def plot(out: dict, shoes: dict, wheels: pd.DataFrame, solids: pd.DataFrame, d: dict) -> None:
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(13.5, 8.6), dpi=130)
    c_track, c_flat, c_end, c_pad = "#d9d9d9", "#9ecae1", "#fdd0a2", "#08306b"
    c_roll, c_scm, c_rect = "#6a51a3", "#d62728", "#2ca02c"
    for side, sgn in (("L", "left"), ("R", "right")):
        so = solids[solids["side"] == sgn]
        ax.add_patch(mpatches.Rectangle((so.bbox_min_z_mm.min() / MM_PER_M, so.bbox_min_x_mm.min() / MM_PER_M),
                                        (so.bbox_max_z_mm.max() - so.bbox_min_z_mm.min()) / MM_PER_M,
                                        (so.bbox_max_x_mm.max() - so.bbox_min_x_mm.min()) / MM_PER_M,
                                        fc=c_track, ec="#969696", lw=0.6, zorder=0))
        for row in shoes[side].itertuples(index=False):
            bx, by = row.block_x_body_m, row.block_y_body_m
            ax.add_patch(mpatches.Rectangle((bx[0], by[0]), bx[1] - bx[0], by[1] - by[0],
                                            fc=c_flat if row.kind == "flat_shoe" else c_end, ec="#525252", lw=0.5, zorder=1,
                                            hatch=None if row.kind == "flat_shoe" else "///"))
            for p in row.pads:
                ax.add_patch(mpatches.Rectangle((p[0], p[2]), p[1] - p[0], p[3] - p[2], fc=c_pad, ec="none", zorder=2,
                                                alpha=1.0 if row.kind == "flat_shoe" else 0.45))
            if row.kind == "end_shoe":
                ax.text(row.station_x_body_m, (by[1] + 0.03) if side == "L" else (by[0] - 0.03), f"{row.gap_mm:.1f}",
                        ha="center", va="bottom" if side == "L" else "top", fontsize=7.5, color="#a63603")
        wl = wheels[(wheels["side"] == sgn) & wheels["role"].str.contains("track roller")]
        for w in wl.itertuples(index=False):
            ax.add_patch(mpatches.Rectangle((w.axis_x_body_m - w.max_round_diameter_mm / 2 / MM_PER_M,
                                             w.axis_y_body_m - w.width_x_mm / 2 / MM_PER_M),
                                            w.max_round_diameter_mm / MM_PER_M, w.width_x_mm / MM_PER_M,
                                            fc="none", ec=c_roll, lw=1.4, ls="--", zorder=4))
            ax.plot(w.axis_x_body_m, w.axis_y_body_m, "+", color=c_roll, ms=7, zorder=5)
        for w in wheels[(wheels["side"] == sgn) & wheels["role"].str.contains("end wheel")].itertuples(index=False):
            ax.add_patch(mpatches.Rectangle((w.axis_x_body_m - w.max_round_diameter_mm / 2 / MM_PER_M,
                                             w.axis_y_body_m - w.width_x_mm / 2 / MM_PER_M),
                                            w.max_round_diameter_mm / MM_PER_M, w.width_x_mm / MM_PER_M,
                                            fc="none", ec="#636363", lw=0.9, ls=":", zorder=3))
        rr = out["rectangles_body_m"][sgn]["pad_tips_flat_1mm"]
        ax.add_patch(mpatches.Rectangle((rr["x_m"][0], rr["y_m"][0]), rr["length_m"], rr["width_m"],
                                        fc="none", ec=c_rect, lw=2.0, zorder=6))
        bx = out["scm_active_domain"]["variants"]["full (10 flat + 6 end shoes per track)"]["boxes"][sgn]
        ax.add_patch(mpatches.Rectangle((bx["x_m"][0], bx["y_m"][0]), bx["size_m"][0], bx["size_m"][1],
                                        fc="none", ec=c_scm, lw=1.6, ls=(0, (6, 3)), zorder=7))
        for lv, mk in zip(AUGER_LEVELS, ("v", "s", "^")):
            t = out["loads_case_C"][lv]["tracks"][sgn]
            ax.plot(t["x_centre_of_pressure_m"], rr["centre_m"][1], mk, color="#000000", mfc="#ffffff", ms=6, zorder=8)
        tt = [out["loads_case_C"][lv]["tracks"][sgn]["x_centre_of_pressure_m"] for lv in AUGER_LEVELS]
        ax.text(max(tt) + 0.03, rr["centre_m"][1] - 0.02, f"압력 중심 x {min(tt):.3f}~{max(tt):.3f}", fontsize=7.5, va="top", zorder=9,
                bbox=dict(fc="#ffffff", ec="none", alpha=0.8, pad=1))
    cg = d["leg_loads"]["meta"]["inputs_from_yaml"]["combined_cg_xy_m"]
    ax.plot(cg[0], cg[1], "o", color="#000000", ms=7, zorder=8)
    ax.annotate("무게중심 투영(상단, 로드 포함)\n" f"({cg[0]:.3f}, {cg[1]:.3f}) m", (cg[0], cg[1]), xytext=(cg[0] + 0.35, 0.12),
                fontsize=8.5, arrowprops=dict(arrowstyle="-", lw=0.6))
    rl = out["rectangles_body_m"]["left"]["pad_tips_flat_1mm"]
    ax.annotate("", xy=(rl["x_m"][0], 0.60), xytext=(rl["x_m"][1], 0.60),
                arrowprops=dict(arrowstyle="<->", lw=0.8, color=c_rect))
    ax.text(rl["centre_m"][0], 0.585, f"평탄 접지(+1 mm) {rl['length_mm']:.1f} mm, x {rl['x_m'][0]:.4f} … {rl['x_m'][1]:.4f} m",
            ha="center", va="top", fontsize=8.5, color="#1b7837")
    ax.text(1.95, 1.50, f"그라우저 패드 폭 {rl['width_mm']:.1f} mm, 블록 600 mm, 피치 {out['shoe_geometry']['pitch_mm']:.1f} mm",
            ha="right", va="bottom", fontsize=8.5)
    sc = out["scm_active_domain"]["variants"]["full (10 flat + 6 end shoes per track)"]
    b = sc["boxes"]["left"]
    ax.text(b["x_m"][0], 1.50, f"SCM 활성 영역(제안) {b['size_m'][0]:.2f} × {b['size_m'][1]:.2f} m, "
            f"2 cm 격자 {b['grid_nodes']:,}점/트랙", fontsize=8.5, color=c_scm, va="bottom")
    ax.axhline(0, color="#bdbdbd", lw=0.5, zorder=0)
    ax.axvline(0, color="#bdbdbd", lw=0.5, zorder=0)
    handles = [
        mpatches.Patch(fc=c_flat, ec="#525252", label="평탄 접지 슈 블록(10/트랙)"),
        mpatches.Patch(fc=c_end, ec="#525252", hatch="///", label="끝 슈 블록(3/끝), 숫자 = 틈 mm"),
        mpatches.Patch(fc=c_pad, label="그라우저 패드(4/슈, 높이 0)"),
        mpatches.Patch(fc="none", ec=c_rect, lw=2, label="+1 mm 접지 사각형"),
        mpatches.Patch(fc="none", ec=c_roll, ls="--", lw=1.4, label="하부 롤러 Ø194(위쪽 163 mm, 투영)"),
        mpatches.Patch(fc="none", ec="#636363", ls=":", label="끝 바퀴(투영)"),
        mpatches.Patch(fc="none", ec=c_scm, ls="--", lw=1.6, label="SCM 활성 영역 제안(여유 0.10 m, 가정)"),
        plt.Line2D([], [], marker="v", ls="none", color="#000", mfc="#fff", label="트랙 압력 중심 상단/중단/하단(▼■▲)"),
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(0.01, 0.5), fontsize=8, ncol=2, framealpha=0.95)
    ax.set_xlim(-2.0, 2.0)
    ax.set_ylim(-1.65, 1.62)
    ax.set_aspect("equal")
    ax.set_xlabel("기체 x [m] (앞 +)")
    ax.set_ylabel("기체 y [m] (왼쪽 +)")
    ax.set_title("크롤러 접지면 평면도 (CAD 하부체 = REXOME25 모델, 기체 좌표, 바닥 z = −1.0509 m)", fontsize=11)
    ax.grid(True, lw=0.3, color="#e0e0e0")
    fig.tight_layout()
    fig.savefig(OUT_PNG)
    plt.close(fig)


if __name__ == "__main__":
    main()
