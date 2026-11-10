"""D8x path-2 independent recount (rules 06_analysis/02_control/d8x/d8x_rules.md 8, + rev1 + rev2).

Written by control-expert before any R-a / R-c / Chrono result existed. It reads only the raw
result files (R-a json, R-c jsonl, Chrono result.json / verify json / r8_series.npz, G0 json,
the point file) and the rules. It does not import any project module and does not read the
output of the path-1 judge (``d8x_judge.py``).

Rules applied (the original, with the sections replaced by rev1 and rev2):
    1.1 / 1.2 (rev1)  asymmetric diamond 5.7 / 3.7 (nose down) / 3.6 (nose up), point table
    3                 expected counts G0 60, R-a 1,102 (910 + K1 192), R-c 288 (192 + K1 96), C 19
    4.1               J1..J11 (F_D8 = F_min + 5 kN)
    4.3 (rev1, rev2)  G0-1..G0-3 on all 60, G0-4 gate only on the L1-R top floors (rev2 3)
    5.0               gates G0, G1, G2a, G2b (G-S and G3 are outside this tool)
    5.1 (rev2 3)      W = argmin m(p) over 11 candidates, eligibility = true R_v <= 1.01
    5.2               V = floor of the smallest J1 among Chrono rows #1..#6
    6                 E-1..E-8, E-4b (rev2 2), E-2 exception (rev2 5), tags / LAS-b (rev2 4)
    7                 V-1 / V-1b (K1), V-2 / V-2b (LAS-b), V-3 (VB - V0)
    10                grade (provisional: G-S, G3 and the audits are outside)

Usage:
    python -I -B d8x_recount.py recount [--points P] [--g0 G0_REV1] [--g0-base G0_BASE]
        [--ra RA_OFF] [--ra-k1 RA_ON] [--rc RC_OFF] [--rc-k1 RC_ON] [--chrono DIR ...]
        [--expect EXPECT.json] [--rules-dir DIR] [--skip-identity] [--out FILE]
        [--format json|md]
    python -I -B d8x_recount.py hash-compare --bundle ra|rc A B [--out FILE] [--format json|md]
    python -I -B d8x_recount.py table

Inputs: --ra / --ra-k1 = acc_d8.py --points outputs (K1 off: stages main,robust,kt = 910 runs;
K1 on: stage main = 192 runs), --rc / --rc-k1 = run_v5.py d1 --group H-R-X jsonl (192 / 96 lines,
identity sidecar <stem>.identity.json next to it), --chrono = folders searched recursively for
result.json with a ``d8x`` block (row name ``D8X_...``) and verify*.json whose ``metrics[].case``
equals the result.json ``case``; r8_series.npz next to result.json. Pass only the judged run
of each Chrono row (a rerun under rev2 5 replaces the earlier folder in the input).

--expect JSON (E-6, the pre-launch values; keys not given keep the defaults below):
    {"ra": {"off": TAG, "on": TAG},
     "rc": {"VB": {"off": TAG, "on": TAG}, "V0": {"off": TAG, "on": TAG}},
     "chrono": TAG}
Defaults: R-a / R-c V0 / Chrono final_C4G2_LAS, R-c VB final_C4G2_P3_LAS (rules 2.1, rev2 4).

Exit codes: 0 pass / conditional pass / provisional without a failure, 1 fail (rules "미달"),
2 not judgeable or input error, 3 internal error. The last stdout line is a JSON summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import traceback
from pathlib import Path

import numpy as np

TOOL = "d8x_recount"
TOOL_VERSION = "1.0"

# ------------------------------------------------------------------------------------ rules
RULES_SHA256 = {
    "d8x_rules.md": "a377b9bb028385bb7d7d97312a71816ba0ca758e2cb193e25b2d092fff064da8",
    "d8x_rules_rev1.md": "ad16f452fb4dce7395a059c73d7caf213f1a9a69f18af8d230bf03f4518e80d4",
    "d8x_rules_rev2.md": "5f3fa620fe704834a9b6c0a65824b29b75e2a527ea8e97a17abb5e07987a8c27",
}

F_MIN_N = 9414.58911            # YAML control.F_min_cylinder_N (rules: 9,414.589 N)
F_D8_N = F_MIN_N + 5000.0       # rules header: D8 line
FLAG_FORCE_MARGIN_N = 2000.0    # 10 FLAG (i)
J4_LIMIT_DEG = 0.2
J5_LIMIT_S = 120.0
J6_MOVING_BAR = 210.0
J6_LOCKED_BAR = 350.0
E8_MIN_WINDOW_S = 1.0
STROKE_GUARD_M = 0.6828         # 4.2 / 10 FLAG (ii): reading stroke margin to the guard
FLAG_STROKE_MARGIN_MM = 5.0
EPS_U = 0.01                    # 1.1 usage tolerance
W_ELIGIBLE_RV = 1.0 + EPS_U     # rev2 3
G0_PROBE_M = 0.002
G0_H4_M = 0.0029
G0_SWIVEL_DEG = 10.0
G0_RV_HAT = 1.005
G0_ERR_DEG = 0.037
FLAG_G04_ERR_DEG = 0.02         # 10 FLAG (iv)
ANGLE_TOL_HARNESS_DEG = 1e-9    # E-5
ANGLE_TOL_CHRONO_DEG = 1e-4     # I-4 / E-4

HALF_ROLL = 5.7
HALF_PITCH_DOWN = 3.7
HALF_PITCH_UP = 3.6

LEVELS = ("top", "middle", "bottom")
MASTS = ("rigid", "stiff", "upper", "lower")

# rev1 1.2 (A), table order
RA_POINTS = {
    "pitch+": (0.0, 3.7), "pitch-": (0.0, -3.6), "roll+": (5.7, 0.0), "roll-": (-5.7, 0.0),
    "r+p+0.25": (1.425, 2.775), "r+p+0.5": (2.85, 1.85), "r+p+0.75": (4.275, 0.925),
    "r+p-0.25": (1.425, -2.7), "r+p-0.5": (2.85, -1.8), "r+p-0.75": (4.275, -0.9),
    "r-p+0.5": (-2.85, 1.85), "r-p-0.5": (-2.85, -1.8),
    "d45++": (2.2627, 2.2627), "d45-+": (-2.2627, 2.2627),
    "d45+-": (2.2064, -2.2064), "d45--": (-2.2064, -2.2064),
}
# rev1 1.2 (B)
RPX_POINTS = {"rpX": (2.8632, 1.8413), "rpX-+": (-2.8632, 1.8413),
              "rpX+-": (2.8242, -1.8162), "rpX--": (-2.8242, -1.8162)}
# rev1 1.2 (C)
AXIS_VERTICES = {"fdown3.7": (0.0, 3.7), "fup3.6": (0.0, -3.6), "roll5.7": (5.7, 0.0),
                 "rollm5.7": (-5.7, 0.0)}
# original 3 R-c (rev1 rename fup3.7 -> fup3.6)
RC_FLOORS = ("fdown3.7", "fup3.6", "roll5.7", "rollm5.7", "rpX", "rpX+-", "rpX-+", "rpX--")
# original 5.1 order (tie-break order) and floor names; coordinates rev1
W_CANDIDATES = (("r+p+0.25", "dxpp025"), ("r+p+0.75", "dxpp075"), ("r+p-0.25", "dxpm025"),
                ("r+p-0.5", "dxpm050"), ("r+p-0.75", "dxpm075"), ("r-p+0.5", "dxmp050"),
                ("r-p-0.5", "dxmm050"), ("d45++", "d45pp"), ("d45+-", "d45pm"),
                ("d45-+", "d45mp"), ("d45--", "d45mm"))
W_MIRRORS = {"r+p-0.5": "rpX+-", "r-p+0.5": "rpX-+", "r-p-0.5": "rpX--"}
W_FLOORS = {floor: RA_POINTS[point] for point, floor in W_CANDIDATES}
CHRONO_FLOORS = {**AXIS_VERTICES, "rpX": RPX_POINTS["rpX"], **W_FLOORS}
G0_POINTS = {**RA_POINTS, **RPX_POINTS}
# rev2 3: G0-4 gate = floors of the L1-R rows #7..#11 (top), as G0 point tags
G0_4_GATE = (("top", "pitch+"), ("top", "pitch-"), ("top", "roll+"), ("top", "rpX"))

# R-a point subsets (original 3)
RA_ROBUST_LOWER = ("pitch+", "pitch-", "roll+", "roll-", "r+p+0.5", "d45++")
RA_KT = ("pitch+", "pitch-", "roll+", "roll-", "r+p+0.5", "r+p+0.25", "d45++")
KT_SCALES = ("x0.3", "x1", "x3")
RC_SCALES = (1.0, 3.0)
RC_SETTINGS = ("VB", "V0")
RC_EPS = {"off": (0.0, 0.002), "on": (0.0,)}

# Chrono 19 rows (original 4.4 with rev1 renames, rev2 1 settle map, rev2 6 groups)
# (no, family, engine, beta_GPa, fs_kN, level, floor, order, settle_kind, group)
CHRONO_TABLE = (
    (1, "K24", "L2b", 1.0, 4.0, "top", "fdown3.7", 1, "identity", "G2-R"),
    (2, "K24", "L2b", 1.0, 4.0, "top", "fup3.6", 1, "identity", None),
    (3, "K24", "L2b", 1.0, 4.0, "top", "roll5.7", 1, "identity", None),
    (4, "K24", "L2b", 1.0, 4.0, "top", "rollm5.7", 1, "identity", None),
    (5, "K24", "L2b", 1.0, 4.0, "top", "rpX", 1, "identity", None),
    (6, "K24", "L2b", 1.0, 4.0, "top", "<W>", 1, "identity", None),
    (7, "C1_D8", "L1R", 1.6, None, "top", "fdown3.7", 1, "level", "D8"),
    (8, "C1_D8", "L1R", 1.6, None, "top", "fup3.6", 1, "level", None),
    (9, "C1_D8", "L1R", 1.6, None, "top", "roll5.7", 1, "level", None),
    (10, "C1_D8", "L1R", 1.6, None, "top", "rpX", 1, "level", None),
    (11, "C1_H4V", "L1R", 1.0, None, "top", "fdown3.7", 1, "level", "G2-R"),
    (12, "A", "L2b", 1.0, 0.0, "middle", "rpX", 1, "identity", None),
    (13, "A", "L2b", 1.0, 0.0, "bottom", "rpX", 1, "identity", None),
    (14, "K0V", "L2b", 1.0, 0.0, "top", "fdown3.7", 1, "identity", "G2-R"),
    (15, "K0V", "L2b", 1.0, 0.0, "top", "fup3.6", 1, "identity", None),
    (16, "K0V", "L2b", 1.0, 0.0, "top", "roll5.7", 1, "identity", None),
    (17, "K0V", "L2b", 1.0, 0.0, "top", "rollm5.7", 1, "identity", None),
    (18, "K0V", "L2b", 1.0, 0.0, "top", "rpX", 1, "identity", None),
    (19, "K8", "L2b", 1.0, 8.0, "top", "<V>", 2, "identity", None),
)
# Chrono floor -> harness point names at the same place (V-1 / V-2 mapping, 5.1 rpX ~ r+p+0.5)
FLOOR_TO_HARNESS = {
    "fdown3.7": ("pitch+", "fdown3.7"), "fup3.6": ("pitch-", "fup3.6"),
    "roll5.7": ("roll+", "roll5.7"), "rollm5.7": ("roll-", "rollm5.7"),
    "rpX": ("r+p+0.5", "rpX"),
    **{floor: (point,) + ((W_MIRRORS[point],) if point in W_MIRRORS else ())
       for point, floor in W_CANDIDATES},
}

DEFAULT_EXPECT = {
    "source": "default (rules 2.1 / rev2 4 sealed tags; pass --expect with the pre-launch values)",
    "ra": {"off": "final_C4G2_LAS", "on": "final_C4G2_LAS"},
    "rc": {"VB": {"off": "final_C4G2_P3_LAS", "on": "final_C4G2_P3_LAS"},
           "V0": {"off": "final_C4G2_LAS", "on": "final_C4G2_LAS"}},
    "chrono": "final_C4G2_LAS",
}
FORBIDDEN_TAGS = ("final_C4G2", "final_C4G2_P3")  # rev2 4: LAS-b off tags

J7_EXACT = ("FAULT_STROKE_END", "WARN_LIFT_STROKE_LIMITED")
J7_PREFIX = "FAULT_LIFT_STROKE_LIMIT"
J9_ALLOWED = ("WARN_PROBE_STIFFNESS_OUT_OF_RANGE",)
LAS_EVENT_PREFIX = "INFO_LIFTOFF_SLOW"
V1_BLOCKING_EVENTS = ("INFO_LOC_FLAT_SOIL_MARGIN", "INFO_LOC_CLEARANCE_MARGIN", "INFO_LOC_REVOKED")


class InputError(Exception):
    """An input file is missing or not of the expected form (exit 2)."""


# ---------------------------------------------------------------------------------- helpers
def r_v(roll_deg: float, pitch_deg: float) -> float:
    """rev1 1.1 asymmetric usage."""
    half_pitch = HALF_PITCH_DOWN if pitch_deg >= 0.0 else HALF_PITCH_UP
    return abs(roll_deg) / HALF_ROLL + abs(pitch_deg) / half_pitch


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_sha256_lf(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputError(f"missing file {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"{path}: not JSON ({exc})") from exc


def load_jsonl(path: Path) -> list:
    rows = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InputError(f"missing file {path}") from exc
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise InputError(f"{path}:{number}: not JSON ({exc})") from exc
    return rows


def is_number(value) -> bool:
    """A finite real number (E-7: None / NaN / inf / bool are not numbers)."""
    if isinstance(value, bool) or value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def get_path(doc, *keys):
    for key in keys:
        if not isinstance(doc, dict) or key not in doc:
            return None
        doc = doc[key]
    return doc


def event_base(name: str) -> str:
    return str(name).split(":", 1)[0]


_EVENT_RE = re.compile(r"t_s=([-+0-9.eEinfa]+).*?name=(['\"])(.*?)\2")


def parse_events(raw) -> list | None:
    """Events as [[t_s, name], ...] from lists, dicts or ``C2Event(...)`` strings."""
    if raw is None:
        return None
    out = []
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            out.append([float(item[0]), str(item[1])])
        elif isinstance(item, dict) and "name" in item:
            out.append([float(item.get("t_s", item.get("t", float("nan")))), str(item["name"])])
        elif isinstance(item, str):
            match = _EVENT_RE.search(item)
            if match:
                out.append([float(match.group(1)), match.group(3)])
            else:
                out.append([float("nan"), item])
        else:
            raise InputError(f"event of unknown form: {item!r}")
    return out


def classify_events(names) -> dict:
    """J7 / J8 / J9 / E-3 / LAS-b counts from event names."""
    j7, j8, j9, rej, las, v1_block, soil = [], [], [], [], [], [], []
    for name in names:
        base = event_base(name)
        if base in J7_EXACT or base.startswith(J7_PREFIX):
            j7.append(name)
        elif base.startswith("FAULT_"):
            j8.append(name)
        elif base.startswith("WARN_") and base not in J9_ALLOWED:
            j9.append(name)
        if base.startswith("REJ_"):
            rej.append(name)
        if base.startswith(LAS_EVENT_PREFIX):
            las.append(name)
        if base in V1_BLOCKING_EVENTS:
            v1_block.append(name)
        if "soil_mode" in base.lower():
            soil.append(name)
    return {"J7": j7, "J8": j8, "J9": j9, "REJ": rej, "LAS": las, "V1_block": v1_block,
            "soil_mode": soil}


def item(value, ok, applied=True, note=None) -> dict:
    out = {"value": value, "result": ("n/a" if not applied else ("pass" if ok else "fail"))}
    if note:
        out["note"] = note
    return out


def num_item(value, compare, applied=True, note=None) -> dict:
    """A numeric item; E-7: None / NaN fails when applied."""
    if not applied:
        return item(value, True, applied=False, note=note)
    if not is_number(value):
        return item(value, False, note=(note or "") + " E-7 missing/NaN".strip())
    return item(float(value), bool(compare(float(value))), note=note)


def list_item(values, applied=True, note=None) -> dict:
    if not applied:
        return item(values, True, applied=False)
    if values is None:
        return item(None, False, note="E-7 missing list")
    return item(list(values), len(values) == 0, note=note)


def finish_row(row: dict) -> dict:
    """Row verdict: unjudgeable dominates, then fail (any applied item fails, E-2, E-3)."""
    failed_items = [k for k, v in row["items"].items() if v["result"] == "fail"]
    row["failed_items"] = failed_items
    if row["unjudgeable"]:
        row["verdict"] = "unjudgeable"
    elif row["fail"] or failed_items:
        row["verdict"] = "fail"
    else:
        row["verdict"] = "pass"
    return row


def harness_items(block: dict, fails, events_names) -> tuple[dict, list]:
    """J1..J9, J11 of a harness run from its ``d8x`` block (R-a and R-c share the block)."""
    ev = classify_events(events_names)
    reanchor = block.get("reanchor_intervals_s")
    h4_ran = bool(reanchor) or any(event_base(n) == "reanchor_started" for n in events_names)
    items = {
        "J1": num_item(block.get("J1_min_cyl_after_lift_N"), lambda v: v >= F_D8_N),
        "J2": num_item(block.get("J2_min_cyl_reanchor_N"), lambda v: v >= F_D8_N, applied=h4_ran),
        "J3": num_item(block.get("J3_pad_lift_samples"), lambda v: v == 0),
        "J4": num_item(block.get("J4_att_max_after_ready_deg"), lambda v: v <= J4_LIMIT_DEG),
        "J5": num_item(block.get("t_ready_s"), lambda v: v <= J5_LIMIT_S),
        "J6_moving": num_item(block.get("J6_max_moving_bar"), lambda v: v <= J6_MOVING_BAR),
        "J7": list_item(ev["J7"]),
        "J8": list_item(ev["J8"]),
        "J9": list_item(ev["J9"]),
        "J11": list_item(fails),
    }
    fail = []
    for name, key in (("TOUCH", "t_touch_s"), ("crawler liftoff", "t_lift_s"), ("READY", "t_ready_s")):
        if not is_number(block.get(key)):
            fail.append(f"E-2 no {name} time ({key})")
    if ev["REJ"]:
        fail.append(f"E-3 REJ events {ev['REJ']}")
    return items, fail, ev


def e8_check(block_window, row: dict) -> None:
    if is_number(block_window) and float(block_window) < E8_MIN_WINDOW_S:
        row["unjudgeable"].append(f"E-8 window after liftoff {float(block_window):.6g} s < 1 s")


def angle_check(row: dict, angles, table_angles, tol: float, label: str) -> None:
    if angles is None or len(angles) != 2 or not all(is_number(a) for a in angles):
        row["unjudgeable"].append(f"E-5 {label}: angles missing ({angles!r})")
        return
    diff = max(abs(float(angles[0]) - table_angles[0]), abs(float(angles[1]) - table_angles[1]))
    if diff > tol:
        row["unjudgeable"].append(f"E-5 {label}: angles {angles} vs table {list(table_angles)} "
                                  f"(diff {diff:.3g} deg)")


# ---------------------------------------------------------------------------------- points
def check_points(path: Path) -> dict:
    """I-3: point file values equal the rev1 table (difference 0) and rules_rev rev1."""
    doc = load_json(path)
    problems = []
    if doc.get("rules_rev") != "rev1":
        problems.append(f"rules_rev {doc.get('rules_rev')!r} != 'rev1'")

    def compare(entries, key, table, label):
        if not isinstance(entries, list):
            problems.append(f"{label}: missing")
            return
        seen = {}
        for entry in entries:
            name = entry.get(key)
            if name in seen:
                problems.append(f"{label}: duplicate {name}")
            seen[name] = (entry.get("roll_deg"), entry.get("pitch_deg"))
        if set(seen) != set(table):
            problems.append(f"{label}: names {sorted(seen)} != {sorted(table)}")
        for name, angles in table.items():
            if name in seen:
                got = seen[name]
                if not all(is_number(a) for a in got) or (float(got[0]), float(got[1])) != angles:
                    problems.append(f"{label} {name}: {got} != {angles}")

    compare(doc.get("ra_points"), "tag", RA_POINTS, "(A)")
    compare(doc.get("rpx_points"), "name", RPX_POINTS, "(B)")
    compare(doc.get("axis_vertices"), "name", AXIS_VERTICES, "(C)")
    if doc.get("rc_floors") is not None and sorted(doc["rc_floors"]) != sorted(RC_FLOORS):
        problems.append(f"rc_floors {doc['rc_floors']} != {list(RC_FLOORS)}")
    rules = doc.get("rules") or {}
    for key, name in (("original", "d8x_rules.md"), ("rev1", "d8x_rules_rev1.md"),
                      ("rev2", "d8x_rules_rev2.md")):
        sha = get_path(rules, key, "sha256")
        if sha is not None and sha != RULES_SHA256[name]:
            problems.append(f"rules {key} sha {sha} != sealed {RULES_SHA256[name]}")
    return {"rule": "I-3", "file": str(path), "sha256": file_sha256(path),
            "sha256_lf": text_sha256_lf(path), "result": "pass" if not problems else "unjudgeable",
            "problems": problems}


def check_rules_dir(folder: Path) -> dict:
    out = {}
    for name, sealed in RULES_SHA256.items():
        path = Path(folder) / name
        if not path.is_file():
            out[name] = {"result": "missing"}
            continue
        raw, lf = file_sha256(path), text_sha256_lf(path)
        out[name] = {"sha256": raw, "sha256_lf": lf, "sealed": sealed,
                     "result": "pass" if sealed in (raw, lf) else "mismatch"}
    return out


# --------------------------------------------------------------------------------------- G0
G0_COMPARE_KEYS = (("G0-1", "s_max_m"), ("G0-2", "F_static_min_N"), ("G0-3", "swivel_deg"),
                   ("G0-4", "floor_hat_deg"))


def judge_g0(path: Path, base_path: Path | None) -> dict:
    """G0 (rev1 3 / 4.3, rev2 3): G0-1..3 on every evaluation, G0-4 gate on the rev2 scope."""
    doc = load_json(path)
    rows_in = doc.get("rows")
    if not isinstance(rows_in, list):
        raise InputError(f"{path}: no 'rows' list")
    unjudgeable, rows, seen = [], [], {}
    expected = {(level, tag) for level in LEVELS for tag in G0_POINTS}
    for entry in rows_in:
        key = (entry.get("level"), entry.get("tag"))
        if key in seen:
            unjudgeable.append(f"E-1/E-5 duplicate G0 key {key}")
            continue
        seen[key] = entry
        if key not in expected:
            unjudgeable.append(f"E-5 G0 key outside the set {key}")
    missing = sorted(expected - set(seen))
    if missing:
        unjudgeable.append(f"E-1 G0 missing {len(missing)} keys: {missing[:6]}")
    for key in sorted(set(seen) & expected, key=lambda k: (LEVELS.index(k[0]), list(G0_POINTS).index(k[1]))):
        entry = seen[key]
        level, tag = key
        roll, pitch = G0_POINTS[tag]
        g0 = entry.get("G0") or {}
        row = {"bundle": "G0", "key": f"{level}|{tag}", "level": level, "point": tag,
               "items": {}, "unjudgeable": [], "fail": [], "record": {}}
        floor = entry.get("floor_deg")
        if floor is not None:
            angle_check(row, floor, (roll, pitch), ANGLE_TOL_HARNESS_DEG, "G0 floor_deg")
        allowance = G0_PROBE_M + (G0_H4_M if pitch > 0.0 else 0.0)
        s_max = get_path(g0, "G0-1", "s_max_m")
        row["items"]["G0-1"] = num_item(s_max, lambda v: v + allowance < STROKE_GUARD_M)
        if is_number(s_max):
            row["record"]["G0-1_margin_mm"] = (STROKE_GUARD_M - (float(s_max) + allowance)) * 1e3
        recorded_allowance = get_path(g0, "G0-1", "allowance_m")
        row["record"]["G0-1_allowance_m"] = allowance
        if is_number(recorded_allowance) and abs(float(recorded_allowance) - allowance) > 1e-12:
            row["record"]["G0-1_allowance_note"] = f"file allowance {recorded_allowance} != {allowance}"
        f_static = get_path(g0, "G0-2", "F_static_min_N")
        row["items"]["G0-2"] = num_item(f_static, lambda v: v >= F_D8_N)
        swivel = get_path(g0, "G0-3", "swivel_deg")
        row["items"]["G0-3"] = num_item(swivel, lambda v: v <= G0_SWIVEL_DEG)
        hat = get_path(g0, "G0-4", "floor_hat_deg")
        in_gate = key in G0_4_GATE
        if hat is not None and len(hat) == 2 and all(is_number(h) for h in hat):
            hat = (float(hat[0]), float(hat[1]))
            rv_hat = r_v(*hat)
            err = (hat[0] - roll, hat[1] - pitch)
            row["record"].update({"G0-4_Rv_hat": rv_hat, "G0-4_err_deg": list(err),
                                  "G0-4_err_max_deg": max(abs(err[0]), abs(err[1]))})
            ok = rv_hat <= G0_RV_HAT and abs(err[0]) <= G0_ERR_DEG and abs(err[1]) <= G0_ERR_DEG
            row["items"]["G0-4"] = item(rv_hat, ok, applied=in_gate,
                                        note="gate (rev2 3)" if in_gate else "record only (rev2 3)")
        else:
            row["items"]["G0-4"] = item(hat, False, applied=in_gate,
                                        note="E-7 floor_hat_deg missing" if in_gate else "record only")
        row["record"]["true_Rv"] = r_v(roll, pitch)
        row["record"]["source"] = entry.get("source")
        rows.append(finish_row(row))
    reuse = None
    if base_path is not None:
        reuse = _g0_reuse_check(doc, load_json(base_path), base_path)
        if reuse["problems"]:
            unjudgeable.extend(f"rev1 3 reuse: {p}" for p in reuse["problems"])
    counts = count_rows(rows, 60, unjudgeable)
    gate = "unjudgeable" if counts["status"] == "unjudgeable" else (
        "pass" if all(r["verdict"] == "pass" for r in rows) else "fail")
    return {"file": str(path), "sha256": file_sha256(path), "rows": rows, "counts": counts,
            "bundle_problems": unjudgeable, "reuse_check": reuse, "gate_G0": gate,
            "gate_scope_G0_4": [f"{l}|{t}" for l, t in G0_4_GATE]}


UNCHANGED_G0 = ("pitch+", "roll+", "roll-", "r+p+0.25", "r+p+0.5", "r+p+0.75", "r-p+0.5",
                "d45++", "d45-+", "rpX", "rpX-+")


def _g0_reuse_check(doc: dict, base: dict, base_path: Path) -> dict:
    """rev1 3: the 33 reused evaluations carry the 3da8daa values unchanged."""
    base_rows = {(r.get("level"), r.get("tag")): r for r in base.get("rows", [])}
    rows = {(r.get("level"), r.get("tag")): r for r in doc.get("rows", [])}
    problems, compared = [], 0
    for level in LEVELS:
        for tag in UNCHANGED_G0:
            a, b = rows.get((level, tag)), base_rows.get((level, tag))
            if a is None or b is None:
                problems.append(f"{level}|{tag} missing in {'rev1' if a is None else 'base'}")
                continue
            for item_name, key in G0_COMPARE_KEYS:
                va, vb = get_path(a, "G0", item_name, key), get_path(b, "G0", item_name, key)
                compared += 1
                if json.dumps(va) != json.dumps(vb):
                    problems.append(f"{level}|{tag} {item_name}.{key}: {va} != base {vb}")
    return {"base": str(base_path), "base_sha256": file_sha256(base_path), "compared": compared,
            "problems": problems}


# ------------------------------------------------------------------------------------- R-a
_ID_KINDS = {"main", "seed", "d0", "beta", "kt", "ktd0"}


def parse_ra_id(run_id: str) -> dict | None:
    parts = str(run_id).split("|")
    if not parts or parts[0] not in _ID_KINDS:
        return None
    kind, rest = parts[0], parts[1:]
    if rest and rest[0] not in LEVELS:
        rest = rest[1:]  # the config segment (``r8.apply`` puts the config name in the id)
    if len(rest) < 3:
        return None
    level, mast, tag = rest[0], rest[1], rest[2]
    param = rest[3] if len(rest) > 3 else None
    stage = {"main": "main", "seed": "robust", "d0": "robust", "beta": "robust", "kt": "kt",
             "ktd0": "kt"}[kind]
    variant = {"main": "main", "seed": f"seed{param}", "d0": f"d0s{param}",
               "beta": f"beta{param}", "kt": f"kt{param}", "ktd0": f"ktd0{param}"}[kind]
    return {"stage": stage, "level": level, "mast": mast, "point": tag, "variant": variant}


def _variant_parts(variant: str):
    """('main'|'seed'|'d0s'|'beta'|'kt'|'ktd0', value) of a producer variant string."""
    variant = str(variant)
    if variant == "main":
        return "main", None
    for prefix in ("ktd0", "kt", "seed", "d0s", "beta"):
        if variant.startswith(prefix):
            try:
                return prefix, float(variant[len(prefix):])
            except ValueError:
                return prefix, None
    return variant, None


def kt_scale_map(variants) -> tuple[dict, list]:
    """The three kt crawler scales -> x0.3 / x1 / x3 (rules 3 td_kt), from the variant values."""
    values = sorted({round(v, 4) for kind, v in (_variant_parts(x) for x in variants)
                     if kind in ("kt", "ktd0") and v is not None})
    problems = []
    if len(values) != 3:
        problems.append(f"kt scales {values}: expected 3 distinct values")
        return {}, problems
    low, mid, high = values
    if not (abs(low / mid - 0.3) <= 5e-3 and abs(high / mid - 3.0) <= 5e-3):
        problems.append(f"kt scales {values}: ratios {low / mid:.5f}, {high / mid:.5f} != 0.3, 3")
        return {}, problems
    return {low: "x0.3", mid: "x1", high: "x3"}, problems


def normalize_variant(stage: str, variant: str, kt_map: dict) -> str:
    kind, value = _variant_parts(variant)
    if kind == "main":
        return "main"
    if kind == "seed" and value in (1.0, 2.0):
        return f"seed{int(value)}"
    if kind == "d0s" and value in (0.0, 1.0, 2.0):
        return f"d0s{int(value)}"
    if kind == "beta" and value is not None:
        for beta, label in ((0.69e9, "beta0.69"), (1.6e9, "beta1.6")):
            if abs(value - beta) <= 1e-9 * beta:
                return label
    if kind in ("kt", "ktd0") and value is not None and round(value, 4) in kt_map:
        return f"{kind}:{kt_map[round(value, 4)]}"
    return f"?{variant}"


def ra_expected(k1: str) -> set:
    out = set()
    for level in LEVELS:
        for point in RA_POINTS:
            for mast in MASTS:
                out.add(("main", level, mast, point, "main"))
    if k1 == "on":
        return out
    for point in RA_POINTS:
        for mast in MASTS:
            for v in ("seed1", "seed2", "d0s0", "d0s1", "d0s2", "beta0.69", "beta1.6"):
                out.add(("robust", "top", mast, point, v))
    for level in ("middle", "bottom"):
        for point in RA_ROBUST_LOWER:
            for mast in MASTS:
                for v in ("beta0.69", "beta1.6", "d0s0"):
                    out.add(("robust", level, mast, point, v))
    for point in RA_KT:
        for mast in ("rigid", "stiff"):
            for scale in KT_SCALES:
                for kind in ("kt", "ktd0"):
                    out.add(("kt", "top", mast, point, f"{kind}:{scale}"))
        for level in ("middle", "bottom"):
            for scale in KT_SCALES:
                out.add(("kt", level, "rigid", point, f"kt:{scale}"))
    return out


def judge_ra(path: Path, k1: str, expect: dict, skip_identity: bool, kt_map: dict) -> dict:
    doc = load_json(path)
    runs = doc.get("runs")
    if not isinstance(runs, list):
        raise InputError(f"{path}: no 'runs' list")
    meta = doc.get("meta") or {}
    bundle_problems = []
    d8x_meta = meta.get("d8x") or {}
    if d8x_meta.get("k1") not in (None, k1):
        bundle_problems.append(f"meta.d8x.k1 {d8x_meta.get('k1')!r} != file role {k1!r}")
    identity = identity_check_ra(meta) if not skip_identity else {"skipped": True, "problems": []}
    bundle_problems.extend(f"I-1 {p}" for p in identity["problems"])
    expected = ra_expected(k1)
    expected_tag = expect["ra"][k1]
    rows, seen = [], {}
    for run in runs:
        row = _judge_ra_run(run, k1, expected_tag, kt_map)
        key = row["key_tuple"]
        if key in seen:
            row["unjudgeable"].append("E-5 duplicate key")
            seen[key]["unjudgeable"].append("E-5 duplicate key")
        elif key is not None:
            seen[key] = row
        if key is not None and key not in expected:
            row["unjudgeable"].append(f"E-5 key outside the rules 3 set {key}")
        rows.append(row)
    for row in rows:
        finish_row(row)
    missing = sorted(expected - set(seen))
    if missing:
        bundle_problems.append(f"E-1 missing {len(missing)} keys, e.g. {missing[:4]}")
    tags = {}
    for run in runs:
        tags[str(run.get("controller_tag"))] = tags.get(str(run.get("controller_tag")), 0) + 1
    return {"file": str(path), "sha256": file_sha256(path), "k1": k1, "rows": rows,
            "expected_n": len(expected), "bundle_problems": bundle_problems,
            "identity": identity, "tag_histogram": tags}


def _judge_ra_run(run: dict, k1: str, expected_tag: str, kt_map: dict) -> dict:
    row = {"bundle": "R-a", "k1": k1, "id": run.get("id"), "items": {}, "unjudgeable": [],
           "fail": [], "record": {}}
    from_id = parse_ra_id(run.get("id", ""))
    fields = {k: run.get(k) for k in ("stage", "level", "mast", "point", "variant")}
    if "error" in run:
        source = from_id
        row["fail"].append(f"E-2 driver error: {str(run.get('error'))[:200]}")
    else:
        source = fields if all(fields.values()) else None
        if source is None:
            row["unjudgeable"].append(f"E-5 identity fields missing {fields}")
            source = from_id
        elif from_id is not None:
            for k in ("stage", "level", "mast", "point"):
                if from_id[k] != fields[k]:
                    row["unjudgeable"].append(f"E-5 id {k} {from_id[k]!r} != field {fields[k]!r}")
            kind_id, val_id = _variant_parts(from_id["variant"])
            kind_f, val_f = _variant_parts(fields["variant"])
            if kind_id != kind_f or (val_id is not None and val_f is not None
                                     and abs(val_id - val_f) > 1e-9 * max(1.0, abs(val_f))):
                row["unjudgeable"].append(f"E-5 id variant {from_id['variant']!r} != "
                                          f"field {fields['variant']!r}")
    if source is None:
        row["unjudgeable"].append(f"E-5 no identity for run id {run.get('id')!r}")
        row["key_tuple"] = None
        row["key"] = None
        return row
    vnorm = normalize_variant(source["stage"], source["variant"], kt_map)
    key = (source["stage"], source["level"], source["mast"], source["point"], vnorm)
    row.update(key_tuple=key, key="|".join(key), stage=key[0], level=key[1], mast=key[2],
               point=key[3], variant=key[4])
    row["commands_sha256"] = run.get("commands_sha256")
    if "error" in run:
        return row
    if key[3] in RA_POINTS:
        angle_check(row, run.get("angles_deg"), RA_POINTS[key[3]], ANGLE_TOL_HARNESS_DEG, "R-a")
    # E-6 tag / K1 / LAS-b (rev2 4)
    tag = run.get("controller_tag")
    if tag != expected_tag or tag in FORBIDDEN_TAGS:
        row["unjudgeable"].append(f"E-6 tag {tag!r} != expected {expected_tag!r}")
    if run.get("k1_order_gate") is not (k1 == "on"):
        row["unjudgeable"].append(f"E-6 k1_order_gate {run.get('k1_order_gate')!r} != {k1 == 'on'}")
    if run.get("liftoff_slow_enabled") is not True:
        row["unjudgeable"].append(f"E-6 LAS-b {run.get('liftoff_slow_enabled')!r} (rev2 4: must be on)")
    block = run.get("d8x")
    if not isinstance(block, dict):
        row["unjudgeable"].append("d8x block missing")
        return row
    events = parse_events(block.get("events"))
    if events is None:
        row["unjudgeable"].append("d8x.events missing")
        events = []
    names = [n for _, n in events]
    items, fail, ev = harness_items(block, run.get("fails"), names)
    row["items"] = items
    row["fail"].extend(fail)
    e8_check(block.get("J1_window_s"), row)
    row["record"] = {"las_events": len(ev["LAS"]), "J1_N": block.get("J1_min_cyl_after_lift_N"),
                     "J2_N": block.get("J2_min_cyl_reanchor_N"),
                     "stroke_max_m": block.get("stroke_max_m"),
                     "stroke_margin_mm": (STROKE_GUARD_M - float(block["stroke_max_m"])) * 1e3
                     if is_number(block.get("stroke_max_m")) else None,
                     "J1_window_s": block.get("J1_window_s"),
                     "info_events": sorted({event_base(n) for n in names if n.startswith("INFO_")})}
    return row


def identity_check_ra(meta: dict) -> dict:
    d8x = meta.get("d8x") or {}
    return _identity_pair(d8x.get("identity_start"), d8x.get("identity_end"))


def _identity_pair(start, end) -> dict:
    """I-1: clean tree (tracked) at the start and the end, the same HEAD."""
    problems, record = [], {}
    for label, ident in (("start", start), ("end", end)):
        if not isinstance(ident, dict):
            problems.append(f"identity {label} missing")
            continue
        git = ident.get("git") or {}
        record[label] = {"head": git.get("head"), "is_clean": git.get("is_clean"),
                         "affinity_mask": ident.get("affinity_mask"),
                         "threads": ident.get("threads"), "python": ident.get("python")}
        if git.get("is_clean") is not True or (git.get("status_porcelain") not in (None, "")):
            problems.append(f"identity {label}: tree not clean")
        threads = ident.get("threads") or {}
        bad = {k: v for k, v in threads.items() if k.endswith("_NUM_THREADS") and v != "1"}
        if bad:
            record[label]["thread_note"] = f"thread variables not 1: {bad}"
    if isinstance(start, dict) and isinstance(end, dict):
        if get_path(start, "git", "head") != get_path(end, "git", "head"):
            problems.append("identity: HEAD differs between start and end")
    return {"problems": problems, "record": record}


# ------------------------------------------------------------------------------------- R-c
def rc_expected(k1: str) -> set:
    return {(floor, level, scale, setting, eps) for setting in RC_SETTINGS for level in LEVELS
            for floor in RC_FLOORS for scale in RC_SCALES for eps in RC_EPS[k1]}


def judge_rc(path: Path, k1: str, expect: dict, skip_identity: bool) -> dict:
    lines = load_jsonl(path)
    bundle_problems = []
    identity = {"skipped": True, "problems": []}
    if not skip_identity:
        sidecar = path.with_name(path.stem + ".identity.json")
        if sidecar.is_file():
            stored = load_json(sidecar)
            starts, ends = stored.get("start") or [], stored.get("end") or []
            identity = _identity_pair(starts[0] if starts else None, ends[-1] if ends else None)
            identity["sidecar"] = str(sidecar)
            identity["starts"] = len(starts)
            identity["ends"] = len(ends)
        else:
            identity = {"problems": [f"identity sidecar {sidecar.name} missing"]}
        bundle_problems.extend(f"I-1 {p}" for p in identity["problems"])
    expected = rc_expected(k1)
    rows, seen = [], {}
    for line in lines:
        row = _judge_rc_line(line, k1, expect)
        key = row.get("key_tuple")
        if key in seen:
            row["unjudgeable"].append("E-5 duplicate key")
            seen[key]["unjudgeable"].append("E-5 duplicate key")
        elif key is not None:
            seen[key] = row
        if key is not None and key not in expected:
            row["unjudgeable"].append(f"E-5 key outside the rules 3 set {key}")
        rows.append(row)
    for row in rows:
        finish_row(row)
    missing = sorted(expected - set(seen), key=str)
    if missing:
        bundle_problems.append(f"E-1 missing {len(missing)} keys, e.g. {missing[:4]}")
    tags = {}
    for line in lines:
        tags[str(line.get("controller_tag"))] = tags.get(str(line.get("controller_tag")), 0) + 1
    return {"file": str(path), "sha256": file_sha256(path), "k1": k1, "rows": rows,
            "expected_n": len(expected), "bundle_problems": bundle_problems,
            "identity": identity, "tag_histogram": tags}


def _judge_rc_line(line: dict, k1: str, expect: dict) -> dict:
    row = {"bundle": "R-c", "k1": k1, "items": {}, "unjudgeable": [], "fail": [], "record": {}}
    job = line.get("job") or {}
    d1job = job.get("d1") or {}
    try:
        key = (str(d1job["slope_name"]), str(d1job["level"]), float(d1job["crawler_k_scale"]),
               str(job["setting"]), float(job.get("eps", 0.0)))
    except (KeyError, TypeError, ValueError):
        row["unjudgeable"].append(f"E-5 job identity missing {job!r:.200}")
        row.update(key_tuple=None, key=None)
        return row
    row.update(key_tuple=key, key=f"{key[0]}|{key[1]}|x{key[2]:g}|{key[3]}|e{key[4]:g}",
               floor=key[0], level=key[1], crawler_k_scale=key[2], setting=key[3], eps=key[4],
               point=key[0])
    row["commands_sha256"] = line.get("commands_sha256")
    if d1job.get("group") != "H-R-X":
        row["unjudgeable"].append(f"E-5 group {d1job.get('group')!r} != 'H-R-X'")
    if job.get("k1") != k1:
        row["unjudgeable"].append(f"E-6 job.k1 {job.get('k1')!r} != file role {k1!r}")
    if "error" in line or not isinstance(line.get("d1"), dict):
        row["fail"].append(f"E-2 driver error / no d1 record: {str(line.get('error'))[:200]}")
        return row
    if key[0] in CHRONO_FLOORS and key[0] in RC_FLOORS:
        table = {**AXIS_VERTICES, **RPX_POINTS}[key[0]]
        angle_check(row, [d1job.get("roll_deg"), d1job.get("pitch_deg")], table,
                    ANGLE_TOL_HARNESS_DEG, "R-c job")
    expected_tag = get_path(expect, "rc", key[3], k1)
    tag = line.get("controller_tag")
    if tag != expected_tag or tag in FORBIDDEN_TAGS:
        row["unjudgeable"].append(f"E-6 tag {tag!r} != expected {expected_tag!r}")
    d1 = line["d1"]
    block = d1.get("d8x")
    if not isinstance(block, dict):
        row["unjudgeable"].append("d1.d8x block missing")
        return row
    if block.get("k1_order_gate") is not (k1 == "on"):
        row["unjudgeable"].append(f"E-6 k1_order_gate {block.get('k1_order_gate')!r} != {k1 == 'on'}")
    if block.get("liftoff_slow_enabled") is not True:
        row["unjudgeable"].append(f"E-6 LAS-b {block.get('liftoff_slow_enabled')!r} (rev2 4: must be on)")
    for field, want in (("level", key[1]), ("floor", key[0])):
        if block.get(field) is not None and block.get(field) != want:
            row["unjudgeable"].append(f"E-5 d8x.{field} {block.get(field)!r} != job {want!r}")
    if block.get("crawler_k_scale") is not None and float(block["crawler_k_scale"]) != key[2]:
        row["unjudgeable"].append("E-5 d8x.crawler_k_scale != job")
    if key[0] in RC_FLOORS:
        angle_check(row, block.get("angles_deg"), {**AXIS_VERTICES, **RPX_POINTS}[key[0]],
                    ANGLE_TOL_HARNESS_DEG, "R-c d8x")
    events = parse_events(block.get("events"))
    if events is None:
        row["unjudgeable"].append("d1.d8x.events missing")
        events = []
    names = [n for _, n in events]
    items, fail, ev = harness_items(block, d1.get("fail_items"), names)
    row["items"] = items
    row["fail"].extend(fail)
    e8_check(block.get("J1_window_s"), row)
    row["record"] = {"las_events": len(ev["LAS"]), "J1_N": block.get("J1_min_cyl_after_lift_N"),
                     "J2_N": block.get("J2_min_cyl_reanchor_N"),
                     "stroke_max_m": block.get("stroke_max_m"),
                     "stroke_margin_mm": (STROKE_GUARD_M - float(block["stroke_max_m"])) * 1e3
                     if is_number(block.get("stroke_max_m")) else None,
                     "J1_window_s": block.get("J1_window_s"), "d1_verdict": d1.get("verdict"),
                     "soil_mode_events": len(ev["soil_mode"])}
    return row


# ---------------------------------------------------------------------------------- Chrono
def chrono_expected_rows(w_floor: str | None, v_floor: str | None) -> dict:
    """Row name -> spec dict (original 4.4, rev1 4.4 names). #6 / #19 need W / V."""
    out = {}
    for no, family, engine, beta, fs, level, floor, order, settle, group in CHRONO_TABLE:
        if floor == "<W>":
            floor = w_floor
        elif floor == "<V>":
            floor = v_floor
        if floor is None:
            name = f"#{no}"
        elif family in ("C1_D8",):
            name = f"D8X_{family}_{level}_{floor}_b1.6"
        elif family == "C1_H4V":
            name = f"D8X_{family}_{level}_{floor}"
        else:
            name = f"D8X_{family}_{level}_{floor}_Fs{fs:g}"
        out[name] = {"no": no, "family": family, "engine": engine, "beta_GPa": beta,
                     "fs_kN": fs, "level": level, "floor": floor, "order": order,
                     "settle_kind": settle, "group": group}
    return out


def _parse_row_name(name: str) -> dict | None:
    """Family / level / floor of a ``D8X_`` row name (to place #6 / #19 before W / V exist)."""
    m = re.match(r"^D8X_(K24|K0V|K8|A|C1_D8|C1_H4V)_(top|middle|bottom)_(.+?)(?:_(Fs\d+|b1\.6))?$",
                 str(name))
    if not m:
        return None
    return {"family": m.group(1), "level": m.group(2), "floor": m.group(3), "suffix": m.group(4)}


def discover_chrono(roots) -> tuple[list, dict]:
    """result.json files with a D8X ``d8x`` block, and verify metrics indexed by case."""
    results, verify = [], {}
    for root in roots:
        root = Path(root)
        if not root.exists():
            raise InputError(f"Chrono root {root} does not exist")
        for path in sorted(root.rglob("result.json")):
            doc = load_json(path)
            block = doc.get("d8x") if isinstance(doc, dict) else None
            if isinstance(block, dict) and str(block.get("row", "")).startswith("D8X_"):
                results.append((path, doc))
        for path in sorted(root.rglob("verify*.json")):
            doc = load_json(path)
            metrics = doc.get("metrics") if isinstance(doc, dict) else None
            if isinstance(metrics, list):
                for entry in metrics:
                    if isinstance(entry, dict) and "case" in entry:
                        verify.setdefault(str(entry["case"]), []).append((path, entry))
    return results, verify


def _pick_verify(case: str, verify: dict) -> tuple[dict | None, list, str | None]:
    entries = verify.get(case) or []
    if not entries:
        return None, [], f"no verify metrics for case {case!r}"
    texts = {json.dumps(e, sort_keys=True, default=str) for _, e in entries}
    if len(texts) > 1:
        return None, [str(p) for p, _ in entries], (f"{len(texts)} different verify metrics "
                                                    f"for case {case!r}")
    return entries[0][1], [str(p) for p, _ in entries], None


def _settle_kind(raw) -> tuple[str | None, str | None]:
    """(kind, level) of a recorded settle map: 'identity' | 'level' (+ level name)."""
    if raw is None:
        return None, None
    if isinstance(raw, dict):
        kind = str(raw.get("kind") or raw.get("type") or raw.get("name") or "")
        level = raw.get("level") or raw.get("stage")
        text = kind.lower()
    else:
        text = str(raw).lower()
        level = None
    if "identity" in text:
        return "identity", None
    if "level" in text:
        if level is None:
            for name in LEVELS:
                if re.search(rf"\b{name}\b", text):
                    level = name
        return "level", (str(level) if level is not None else None)
    return text or None, level


def _r8_cross_check(folder: Path) -> dict:
    path = folder / "r8_series.npz"
    if not path.is_file():
        return {"file": None, "note": "r8_series.npz missing"}
    with np.load(path, allow_pickle=False) as z:
        t = np.asarray(z["t"], float) if "t" in z.files else None
        phase = np.asarray(z["phase"]).astype(str) if "phase" in z.files else None
    out = {"file": str(path), "sha256": file_sha256(path),
           "t_last_s": float(t[-1]) if t is not None and t.size else None}
    if t is not None and phase is not None:
        ready = np.flatnonzero(phase == "ready")
        out["first_ready_s"] = float(t[ready[0]]) if ready.size else None
        touch_end = np.flatnonzero((phase[:-1] == "touch") & (phase[1:] != "touch"))
        out["touch_end_s"] = float(t[touch_end[0] + 1]) if touch_end.size else None
        out["phase_fault"] = bool(np.any(np.char.startswith(phase, "fault")))
    return out


def judge_chrono(roots, expect: dict, w_floor: str | None) -> dict:
    """Chrono rows: identity (I-4, E-4, E-4b, E-6, rev2 6) and J1..J10; V selection."""
    results, verify = discover_chrono(roots)
    bundle_problems, rows, seen = [], [], {}
    expected_tag = expect["chrono"]
    for path, doc in results:
        block = doc["d8x"]
        name = str(block["row"])
        row = {"bundle": "C", "row": name, "key": name, "result_json": str(path),
               "result_sha256": file_sha256(path), "items": {}, "unjudgeable": [], "fail": [],
               "record": {}}
        if name in seen:
            row["unjudgeable"].append("E-5 duplicate Chrono row (pass only the judged run)")
            seen[name]["unjudgeable"].append("E-5 duplicate Chrono row")
        else:
            seen[name] = row
        rows.append(row)
        parsed = _parse_row_name(name)
        if parsed is None:
            row["unjudgeable"].append("E-5 row name outside the 4.4 pattern")
            continue
        row.update(level=parsed["level"], floor=parsed["floor"], family=parsed["family"])
        case = str(doc.get("case") or get_path(doc, "settings", "case_id") or name)
        metrics, verify_files, problem = _pick_verify(case, verify)
        row["verify_files"] = verify_files
        if problem:
            row["unjudgeable"].append(problem)
            continue
        _judge_chrono_row(row, block, doc, metrics, path.parent, expected_tag)
    return {"rows": rows, "bundle_problems": bundle_problems, "roots": [str(r) for r in roots],
            "n_result_json": len(results)}


def _judge_chrono_row(row, block, doc, metrics, folder: Path, expected_tag) -> None:
    family, level, floor = row["family"], row["level"], row["floor"]
    engine = "L1R" if family.startswith("C1_") else "L2b"
    spec = next((s for s in CHRONO_TABLE if s[1] == family), None)
    row["engine"] = engine
    # I-4 / E-4: mode, floor, level, beta, F_s
    if block.get("slope_limit_mode") != "verification_ext":
        row["unjudgeable"].append(f"E-4 slope_limit_mode {block.get('slope_limit_mode')!r}")
    table = CHRONO_FLOORS.get(floor)
    if table is None:
        row["unjudgeable"].append(f"E-4 floor {floor!r} not in rules 1.2 / 5.1")
    else:
        angle_check(row, block.get("floor_true_deg"), table, ANGLE_TOL_CHRONO_DEG, "I-4 floor_true_deg")
        vmetric = metrics.get("floor_true_deg")
        if vmetric is not None:
            angle_check(row, vmetric, table, ANGLE_TOL_CHRONO_DEG, "verify floor_true_deg")
    if block.get("level") != level:
        row["unjudgeable"].append(f"I-4 level {block.get('level')!r} != {level!r}")
    beta_want = 1.6 if family == "C1_D8" else 1.0
    if not is_number(block.get("beta_GPa")) or abs(float(block["beta_GPa"]) - beta_want) > 1e-12:
        row["unjudgeable"].append(f"I-4 beta_GPa {block.get('beta_GPa')!r} != {beta_want}")
    fs_want = {"K24": 4.0, "A": 0.0, "K0V": 0.0, "K8": 8.0}.get(family)
    fs = block.get("fs_kN")
    if fs_want is None:  # L1-R: no seal friction
        if fs not in (None, 0, 0.0):
            row["unjudgeable"].append(f"I-4 fs_kN {fs!r} on an L1-R row")
    elif not is_number(fs) or abs(float(fs) - fs_want) > 1e-12:
        row["unjudgeable"].append(f"I-4 fs_kN {fs!r} != {fs_want}")
    spans = block.get("half_spans_deg")
    if spans is not None:
        values = list(spans.values()) if isinstance(spans, dict) else list(spans)
        if sorted(float(v) for v in values) != sorted((HALF_ROLL, HALF_PITCH_DOWN, HALF_PITCH_UP)):
            row["unjudgeable"].append(f"rev1 9.3 half_spans_deg {spans!r}")
    # E-4b settle map (rev2 1)
    kind, s_level = _settle_kind(block.get("settle_map"))
    want_kind = "level" if engine == "L1R" else "identity"
    if kind != want_kind:
        row["unjudgeable"].append(f"E-4b settle map {block.get('settle_map')!r}, expected {want_kind}")
    elif kind == "level" and s_level != level:
        row["unjudgeable"].append(f"E-4b settle map level {s_level!r} != {level!r}")
    # E-6 tag and LAS-b (rev2 4)
    tag = block.get("controller_tag")
    if tag != expected_tag or tag in FORBIDDEN_TAGS:
        row["unjudgeable"].append(f"E-6 tag {tag!r} != expected_tag {expected_tag!r}")
    if block.get("liftoff_slow_enabled") is not True:
        row["unjudgeable"].append(f"E-6 LAS-b {block.get('liftoff_slow_enabled')!r}")
    # rev2 6 scenario group
    group = block.get("scenario_group")
    if not group or not block.get("scenario_id"):
        row["unjudgeable"].append("rev2 6 scenario_group / scenario_id missing")
    else:
        group_want = None
        if floor == "fdown3.7" and family in ("K24", "K0V", "C1_H4V"):
            group_want = "G2-R"
        elif floor == "fdown3.7" and family == "C1_D8":
            group_want = "D8"
        if group_want is not None and group != group_want:
            row["unjudgeable"].append(f"rev2 6 scenario_group {group!r} != {group_want!r}")
    row["record"]["scenario_group"] = group
    row["record"]["scenario_id"] = block.get("scenario_id")
    # events
    events = parse_events(metrics.get("events"))
    if events is None:
        ce = folder / "controller_events.json"
        events = parse_events(load_json(ce)) if ce.is_file() else None
    if events is None:
        row["unjudgeable"].append("events missing (verify metrics.events / controller_events.json)")
        events = []
    names = [n for _, n in events]
    ev = classify_events(names)
    times = metrics.get("times_s") or {}
    t_touch, t_lift, t_ready, t_end = (times.get("touch"), times.get("liftoff"),
                                       times.get("ready"), times.get("end"))
    t_loc = min((t for t, n in events if n == "crawler_liftoff_confirmed"), default=None)
    if not is_number(t_lift) and is_number(t_loc):
        t_lift = t_loc
    elif is_number(t_lift) and is_number(t_loc):
        t_lift = min(float(t_lift), float(t_loc))
    r8 = _r8_cross_check(folder)
    row["record"]["r8_series"] = r8
    if is_number(r8.get("t_last_s")):
        t_end = max(float(t_end), r8["t_last_s"]) if is_number(t_end) else r8["t_last_s"]
    # E-2 with the rev2 5 exception
    if not is_number(t_touch):
        row["fail"].append("E-2 no TOUCH time")
    if not is_number(t_lift):
        row["fail"].append("E-2 no crawler liftoff time")
    if not is_number(t_ready):
        if is_number(t_end) and float(t_end) < J5_LIMIT_S:
            row["unjudgeable"].append(f"rev2 5 no READY and run end {float(t_end):.3f} s < 120 s "
                                      "(rerun with T_run >= 130 s)")
        else:
            row["fail"].append("E-2 no READY (run end >= 120 s or unknown)")
    if is_number(r8.get("first_ready_s")) and is_number(t_ready) and \
            abs(r8["first_ready_s"] - float(t_ready)) > 0.1 + 1e-6:
        row["record"]["note_ready"] = f"r8 first ready {r8['first_ready_s']} vs verify {t_ready}"
    # E-3
    target_code = metrics.get("target_code") or get_path(doc, "acceptance", "target_code")
    if target_code is None:
        row["fail"].append("E-3 target_code missing")
    elif str(target_code).startswith("REJ_") or str(target_code) != "ACCEPTED":
        row["fail"].append(f"E-3 target_code {target_code!r}")
    if ev["REJ"]:
        row["fail"].append(f"E-3 REJ events {ev['REJ']}")
    # E-8
    if is_number(t_lift) and is_number(t_end) and float(t_end) - float(t_lift) < E8_MIN_WINDOW_S:
        row["unjudgeable"].append(f"E-8 window after liftoff {float(t_end) - float(t_lift):.6g} s < 1 s")
    # J items
    h4_ran = any(event_base(n) == "reanchor_started" for n in names)
    j1 = metrics.get("min_cyl_after_liftoff_kN")
    j2 = metrics.get("min_cyl_reanchor_kN")
    items = {
        "J1": num_item(None if not is_number(j1) else float(j1) * 1e3, lambda v: v >= F_D8_N),
        "J2": num_item(None if not is_number(j2) else float(j2) * 1e3, lambda v: v >= F_D8_N,
                       applied=h4_ran),
        "J3": _chrono_j3(metrics),
        "J4": num_item(metrics.get("att_err_after_ready_maxabs_deg"), lambda v: v <= J4_LIMIT_DEG),
        "J5": num_item(t_ready, lambda v: v <= J5_LIMIT_S),
        "J6_moving": num_item(metrics.get("max_moving_pressure_bar"), lambda v: v <= J6_MOVING_BAR),
        "J6_locked": _chrono_j6_locked(metrics),
        "J7": list_item(ev["J7"]),
        "J8": list_item(ev["J8"]),
        "J9": list_item(ev["J9"]),
        "J10": num_item(metrics.get("crawler_recontact_after_loc_count"), lambda v: v == 0),
    }
    row["items"] = items
    stroke = metrics.get("stroke_reading_max_m")
    if not is_number(stroke):
        legs = get_path(metrics, "stroke", "max_m")
        stroke = max(float(v) for v in legs) if isinstance(legs, list) and legs and \
            all(is_number(v) for v in legs) else None
    row["record"].update({
        "J1_N": items["J1"]["value"], "J2_N": items["J2"]["value"] if h4_ran else None,
        "t_touch_s": t_touch, "t_lift_s": t_lift, "t_ready_s": t_ready, "t_end_s": t_end,
        "las_events": len(ev["LAS"]), "v1_blocking_events": ev["V1_block"],
        "soil_mode_events": ev["soil_mode"], "stroke_max_m": stroke,
        "stroke_margin_mm": (STROKE_GUARD_M - stroke) * 1e3 if is_number(stroke) else None,
        "F_min_N_file": metrics.get("F_min_N"),
    })
    if is_number(metrics.get("F_min_N")) and abs(float(metrics["F_min_N"]) - F_MIN_N) > 1e-6:
        row["record"]["note_fmin"] = f"verify F_min_N {metrics['F_min_N']} != {F_MIN_N}"


_J3_KEYS = ("pad_lift_after_touch_count", "pad_lift_count", "J3_pad_lift_samples")


def _chrono_j3(metrics: dict) -> dict:
    for key in _J3_KEYS:
        if key in metrics:
            return num_item(metrics[key], lambda v: v == 0, note=f"source {key}")
    value = metrics.get("pad_N_min_after_liftoff_kN")
    return num_item(value, lambda v: v > 0.0, note="source pad_N_min_after_liftoff_kN > 0 (proxy)")


_J6_LOCKED_KEYS = ("max_locked_pressure_bar", "max_pressure_locked_bar", "max_pressure_any_step_bar")


def _chrono_j6_locked(metrics: dict) -> dict:
    for key in _J6_LOCKED_KEYS:
        if key in metrics:
            return num_item(metrics[key], lambda v: v <= J6_LOCKED_BAR, note=f"source {key}")
    return item(None, True, applied=False, note="no locked-pressure field (rules: when present)")


# --------------------------------------------------------------------------- counts / gates
def count_rows(rows, expected_n: int, problems) -> dict:
    out = {"expected": expected_n, "actual": len(rows),
           "pass": sum(r["verdict"] == "pass" for r in rows),
           "fail": sum(r["verdict"] == "fail" for r in rows),
           "unjudgeable": sum(r["verdict"] == "unjudgeable" for r in rows)}
    if out["actual"] != expected_n:
        problems = list(problems) + [f"E-1 count {out['actual']} != {expected_n}"]
    out["problems"] = list(problems)
    if out["problems"] or out["unjudgeable"]:
        out["status"] = "unjudgeable"
    elif out["fail"]:
        out["status"] = "fail"
    else:
        out["status"] = "pass"
    return out


def select_w(ra_off: dict | None, rc_off: dict | None) -> dict:
    """5.1 with rev2 3 eligibility: W = argmin m(p), ties by the 5.1 order."""
    if ra_off is None:
        return {"status": "pending", "reason": "R-a K1-off result missing"}
    table = []
    for point, floor in W_CANDIDATES:
        ra_values = [float(r["record"]["J1_N"]) for r in ra_off["rows"]
                     if r.get("level") == "top" and r.get("mast") == "rigid"
                     and r.get("point") == point and r.get("record")
                     and is_number(r["record"].get("J1_N"))]
        rc_values = []
        mirror = W_MIRRORS.get(point)
        if mirror is not None and rc_off is not None:
            rc_values = [float(r["record"]["J1_N"]) for r in rc_off["rows"]
                         if r.get("level") == "top" and r.get("floor") == mirror and r.get("record")
                         and is_number(r["record"].get("J1_N"))]
        values = ra_values + rc_values
        true_rv = r_v(*RA_POINTS[point])
        table.append({"point": point, "floor": floor, "m_N": min(values) if values else None,
                      "m_ra_N": min(ra_values) if ra_values else None,
                      "m_rc_mirror_N": min(rc_values) if rc_values else None, "mirror": mirror,
                      "n_ra": len(ra_values), "n_rc": len(rc_values), "true_Rv": true_rv,
                      "eligible": true_rv <= W_ELIGIBLE_RV})
    if any(e["mirror"] for e in table) and rc_off is None:
        return {"status": "pending", "reason": "R-c K1-off result missing (mirror pairs)",
                "table": table}
    ranked = [e for e in table if e["m_N"] is not None]
    ranked.sort(key=lambda e: (e["m_N"], [p for p, _ in W_CANDIDATES].index(e["point"])))
    for rank, entry in enumerate(ranked, 1):
        entry["rank"] = rank
    chosen = next((e for e in ranked if e["eligible"]), None)
    skipped = [e["point"] for e in ranked if not e["eligible"]
               and (chosen is None or e["rank"] < chosen["rank"])]
    if chosen is None:
        return {"status": "no_eligible", "table": table, "skipped": skipped}
    return {"status": "selected", "point": chosen["point"], "floor": chosen["floor"],
            "m_N": chosen["m_N"], "angles_deg": list(RA_POINTS[chosen["point"]]),
            "skipped_ineligible": skipped, "table": table,
            "risk_d45_down": chosen["point"] in ("d45++", "d45-+")}


def select_v(chrono_rows, w_floor: str | None) -> dict:
    """5.2: V = floor of the smallest J1 among rows #1..#6 (table order on ties)."""
    order = []
    for name, spec in chrono_expected_rows(w_floor, None).items():
        if spec["no"] <= 6:
            order.append((spec["no"], name, spec["floor"]))
    by_name = {r["row"]: r for r in chrono_rows}
    entries, missing = [], []
    for no, name, floor in order:
        row = by_name.get(name)
        j1 = get_path(row or {}, "record", "J1_N")
        if row is None or not is_number(j1) or row.get("verdict") == "unjudgeable":
            missing.append(name)
            continue
        entries.append({"no": no, "row": name, "floor": floor, "J1_N": float(j1)})
    if missing:
        return {"status": "pending", "missing_or_unjudgeable": missing, "table": entries}
    best = min(entries, key=lambda e: (e["J1_N"], e["no"]))
    return {"status": "selected", "floor": best["floor"], "row": best["row"], "J1_N": best["J1_N"],
            "table": entries}


def invariance(ra_off, ra_on, rc_off, rc_on, chrono_rows) -> dict:
    """V-1 (K1), V-2 (LAS-b), V-3 (VB - V0)."""
    out = {}
    # V-1
    pairs, dependent, problems = 0, set(), []
    if ra_off is not None and ra_on is not None:
        off = {(r["level"], r["mast"], r["point"]): r for r in ra_off["rows"]
               if r.get("stage") == "main" and r.get("key")}
        for r in ra_on["rows"]:
            if not r.get("key"):
                continue
            k = (r["level"], r["mast"], r["point"])
            other = off.get(k)
            pairs += 1
            a, b = r.get("commands_sha256"), (other or {}).get("commands_sha256")
            if other is None or a is None or b is None:
                problems.append(f"R-a pair {k} missing hash")
                dependent.add(("R-a", r["point"], r["level"]))
            elif a != b:
                dependent.add(("R-a", r["point"], r["level"]))
    if rc_off is not None and rc_on is not None:
        off = {(r["floor"], r["level"], r["crawler_k_scale"], r["setting"]): r for r in rc_off["rows"]
               if r.get("key") and r.get("eps") == 0.0}
        for r in rc_on["rows"]:
            if not r.get("key"):
                continue
            k = (r["floor"], r["level"], r["crawler_k_scale"], r["setting"])
            other = off.get(k)
            pairs += 1
            a, b = r.get("commands_sha256"), (other or {}).get("commands_sha256")
            if other is None or a is None or b is None:
                problems.append(f"R-c pair {k} missing hash")
                dependent.add(("R-c", r["floor"], r["level"]))
            elif a != b:
                dependent.add(("R-c", r["floor"], r["level"]))
    complete = all(x is not None for x in (ra_off, ra_on, rc_off, rc_on))
    v1 = {"pairs": pairs, "expected_pairs": 192 + 96,
          "K1_DEPENDENT": sorted([list(d) for d in dependent]), "problems": problems}
    if not complete:
        v1["class"] = "pending"
    else:
        v1["class"] = "K1_INVARIANT" if not dependent and pairs == 288 else "K1_DEPENDENT"
    succession = []
    for r in chrono_rows or []:
        rec = r.get("record") or {}
        blocking = list(rec.get("v1_blocking_events") or []) + list(rec.get("soil_mode_events") or [])
        succession.append({"row": r["row"], "blocking_events": blocking,
                           "succession_ok": not blocking})
    v1["chrono_succession"] = succession
    out["V-1"] = v1
    # V-2: judged rows only (K1 pairs excluded)
    counts = {}
    for bundle, doc in (("R-a", ra_off), ("R-c", rc_off)):
        if doc is None:
            continue
        for r in doc["rows"]:
            if not r.get("key"):
                continue
            k = (bundle, r["point"], r["level"])
            counts[k] = counts.get(k, 0) + int((r.get("record") or {}).get("las_events") or 0)
    las_dep = sorted([[b, p, l, n] for (b, p, l), n in counts.items() if n > 0])
    out["V-2"] = {"class": "pending" if ra_off is None or rc_off is None else
                  ("LAS_INACTIVE" if not las_dep else "LAS_DEPENDENT"),
                  "LAS_DEPENDENT": las_dep, "points_counted": len(counts),
                  "chrono_rows_on_dependent_points": _chrono_dependent(chrono_rows, las_dep)}
    out["V-1"]["chrono_rows_on_dependent_points"] = _chrono_dependent(
        chrono_rows, [[b, p, l, 1] for b, p, l in v1["K1_DEPENDENT"]])
    # V-3
    v3 = []
    if rc_off is not None:
        idx = {(r["floor"], r["level"], r["crawler_k_scale"], r["eps"], r["setting"]): r
               for r in rc_off["rows"] if r.get("key")}
        for (floor, level, scale, eps, setting), r in sorted(idx.items(), key=lambda x: str(x[0])):
            if setting != "VB":
                continue
            v0 = idx.get((floor, level, scale, eps, "V0"))
            a = get_path(r, "record", "J1_N")
            b = get_path(v0 or {}, "record", "J1_N")
            v3.append({"floor": floor, "level": level, "crawler_k_scale": scale, "eps": eps,
                       "J1_VB_N": a, "J1_V0_N": b,
                       "VB_minus_V0_N": float(a) - float(b) if is_number(a) and is_number(b) else None})
    out["V-3"] = v3
    return out


def _chrono_dependent(chrono_rows, dependent) -> list:
    points = {(p, l) for _, p, l, _ in dependent}
    out = []
    for r in chrono_rows or []:
        floor, level = r.get("floor"), r.get("level")
        names = FLOOR_TO_HARNESS.get(floor, (floor,))
        if any((n, level) in points for n in names):
            out.append(r["row"])
    return out


def flags(ra_off, rc_off, chrono_rows, g0) -> list:
    """10 FLAG (i), (ii), (iv); (iii) is added from V-1 / V-2."""
    out = []
    line = F_D8_N + FLAG_FORCE_MARGIN_N
    sources = []
    for doc in (ra_off, rc_off):
        if doc is not None:
            sources.extend(doc["rows"])
    sources.extend(chrono_rows or [])
    for r in sources:
        rec = r.get("record") or {}
        for label in ("J1_N", "J2_N"):
            v = rec.get(label)
            if label == "J2_N" and get_path(r, "items", "J2", "result") == "n/a":
                continue
            if is_number(v) and float(v) < line:
                out.append({"flag": "i", "bundle": r["bundle"], "row": r.get("key"),
                            "item": label[:2], "value_N": float(v), "line_N": line})
        margin = rec.get("stroke_margin_mm")
        if is_number(margin) and float(margin) < FLAG_STROKE_MARGIN_MM:
            out.append({"flag": "ii", "bundle": r["bundle"], "row": r.get("key"),
                        "stroke_margin_mm": float(margin)})
    if g0 is not None:
        for r in g0["rows"]:
            if (r["level"], r["point"]) in G0_4_GATE:
                err = r["record"].get("G0-4_err_max_deg")
                if is_number(err) and float(err) > FLAG_G04_ERR_DEG:
                    out.append({"flag": "iv", "bundle": "G0", "row": r["key"], "err_deg": float(err)})
    return out


# -------------------------------------------------------------------------------- recount
def recount(args) -> dict:
    expect = DEFAULT_EXPECT if args.expect is None else _load_expect(args.expect)
    report = {"tool": TOOL, "version": TOOL_VERSION, "tool_sha256": file_sha256(Path(__file__)),
              "rules_sealed_sha256": RULES_SHA256, "F_D8_N": F_D8_N, "expect": expect,
              "inputs": {}}
    if args.rules_dir:
        report["rules_check"] = check_rules_dir(Path(args.rules_dir))
    if args.points:
        report["point_file"] = check_points(Path(args.points))
    g0 = judge_g0(Path(args.g0), Path(args.g0_base) if args.g0_base else None) if args.g0 else None
    kt_variants = []
    ra_paths = [(p, k) for p, k in ((args.ra, "off"), (args.ra_k1, "on")) if p]
    for path, _ in ra_paths:
        kt_variants.extend(str(r.get("variant")) for r in load_json(Path(path)).get("runs", [])
                           if r.get("variant"))
    kt_map, kt_problems = kt_scale_map(kt_variants) if kt_variants else ({}, [])
    ra = {k: judge_ra(Path(p), k, expect, args.skip_identity, kt_map) for p, k in ra_paths}
    rc = {k: judge_rc(Path(p), k, expect, args.skip_identity)
          for p, k in ((args.rc, "off"), (args.rc_k1, "on")) if p}
    w = select_w(ra.get("off"), rc.get("off"))
    w_floor = w.get("floor") if w.get("status") == "selected" else None
    chrono = judge_chrono(args.chrono, expect, w_floor) if args.chrono else None
    report["g0"] = g0
    report["kt_scales"] = {"map": {str(k): v for k, v in kt_map.items()}, "problems": kt_problems}
    report["ra"] = ra
    report["rc"] = rc
    report["selection"] = {"W": w}
    bundles = {}
    # G0
    bundles["G0"] = g0["counts"] if g0 else {"status": "pending"}
    # R-a: 1,102 = judged 910 + K1 192
    bundles["R-a"] = _bundle(ra, 1102, {"off": 910, "on": 192}, kt_problems)
    bundles["R-c"] = _bundle(rc, 288, {"off": 192, "on": 96}, [])
    # Chrono
    if chrono is not None:
        for r in chrono["rows"]:
            finish_row(r)
        v = select_v(chrono["rows"], w_floor)
        report["selection"]["V"] = v
        v_floor = v.get("floor") if v.get("status") == "selected" else None
        _chrono_set_check(chrono, w, w_floor, v_floor)
        report["chrono"] = chrono
        bundles["C"] = chrono["counts"]
    else:
        report["selection"]["V"] = {"status": "pending", "reason": "no Chrono input"}
        bundles["C"] = {"status": "pending"}
    report["bundles"] = bundles
    report["invariance"] = invariance(ra.get("off"), ra.get("on"), rc.get("off"), rc.get("on"),
                                      chrono["rows"] if chrono else None)
    fl = flags(ra.get("off"), rc.get("off"), chrono["rows"] if chrono else None, g0)
    for cls, key in (("K1_DEPENDENT", "V-1"), ("LAS_DEPENDENT", "V-2")):
        entries = report["invariance"][key].get(cls) or []
        for e in entries:
            fl.append({"flag": "iii", "class": cls, "bundle": e[0], "point": e[1], "level": e[2]})
    report["flags"] = fl
    report["gates"] = gates(report)
    report["grade"] = grade(report)
    return report


def _load_expect(path: str) -> dict:
    doc = load_json(Path(path))
    out = json.loads(json.dumps(DEFAULT_EXPECT))
    out["source"] = str(path)
    for key in ("ra", "rc", "chrono"):
        if key in doc:
            out[key] = doc[key]
    return out


def _bundle(parts: dict, expected_total: int, expected_parts: dict, extra_problems) -> dict:
    if not parts:
        return {"status": "pending"}
    out = {"expected": expected_total, "parts": {}, "problems": list(extra_problems)}
    actual = 0
    for k, doc in parts.items():
        c = count_rows(doc["rows"], expected_parts[k], doc["bundle_problems"])
        out["parts"][k] = c
        actual += c["actual"]
    out["actual"] = actual
    out["missing_parts"] = [f"K1 {k}" for k in expected_parts if k not in parts]
    for name in ("pass", "fail", "unjudgeable"):
        out[name] = sum(c[name] for c in out["parts"].values())
    judged = out["parts"].get("off")
    out["judged"] = {name: (judged or {}).get(name) for name in ("pass", "fail", "unjudgeable")}
    if not out["missing_parts"] and actual != expected_total:
        out["problems"].append(f"E-1 count {actual} != {expected_total}")
    if out["problems"] or any(c["status"] == "unjudgeable" for c in out["parts"].values()):
        out["status"] = "unjudgeable"
    elif judged is not None and judged["fail"]:
        out["status"] = "fail"
    elif out["missing_parts"]:
        out["status"] = "pending"
    else:
        out["status"] = "pass"
    out["k1_rows_fail"] = (out["parts"].get("on") or {}).get("fail")
    return out


def _chrono_set_check(chrono: dict, w: dict, w_floor, v_floor) -> None:
    """E-1 for C (18 + 1) and the #6 / #19 floors against W / V."""
    rows = chrono["rows"]
    problems = list(chrono["bundle_problems"])
    expected = chrono_expected_rows(w_floor, v_floor)
    names = [r["row"] for r in rows]
    first = [r for r in rows if not r["row"].startswith("D8X_K8_")]
    second = [r for r in rows if r["row"].startswith("D8X_K8_")]
    for r in rows:
        if r["row"] in expected:
            r["spec_no"] = expected[r["row"]]["no"]
            continue
        parsed = _parse_row_name(r["row"])
        fam = parsed["family"] if parsed else None
        if fam == "K24" and w_floor is None and parsed["floor"] in W_FLOORS:
            r["spec_no"] = 6
            r["record"]["note_w"] = "W not selected by this recount yet; #6 floor not checked"
            continue
        if fam == "K8" and v_floor is None and parsed["floor"] in CHRONO_FLOORS:
            r["spec_no"] = 19
            r["record"]["note_v"] = "V not selected yet; #19 floor not checked"
            continue
        r["unjudgeable"].append("E-5 row not in the 4.4 table (with W / V of this recount)")
        r["verdict"] = "unjudgeable"
    for name, spec in expected.items():
        if name.startswith("#"):
            continue
        if name not in names:
            if spec["order"] == 2 and not second:
                continue  # 2nd-order row not run yet
            problems.append(f"E-1 missing row {name}")
    if w.get("status") not in ("selected", "pending") and any(r.get("spec_no") == 6 for r in rows):
        problems.append(f"W selection status {w.get('status')} but #6 present")
    chrono["counts_first"] = count_rows(first, 18, [p for p in problems if "K8" not in p])
    chrono["counts_second"] = count_rows(second, 1, []) if second else {"status": "pending"}
    chrono["counts"] = count_rows(rows, 19, problems) if second else dict(
        count_rows(rows, 18, problems), status_note="second-order row not present",
        expected_total=19)
    if not second:
        chrono["counts"]["status"] = (chrono["counts"]["status"] if chrono["counts"]["status"] != "pass"
                                      else "pending")


def gates(report: dict) -> dict:
    g0 = report["bundles"]["G0"]["status"] if report.get("g0") else "pending"
    if report.get("g0") is not None:
        g0 = report["g0"]["gate_G0"]
    ra, rc = report["bundles"]["R-a"]["status"], report["bundles"]["R-c"]["status"]
    if "unjudgeable" in (ra, rc):
        g1 = "unjudgeable"
    elif "fail" in (ra, rc):
        g1 = "fail"
    elif "pending" in (ra, rc):
        g1 = "pending"
    else:
        g1 = "pass"
    ch = report.get("chrono")
    if ch is None:
        g2a = g2b = "pending"
    else:
        g2a = ch["counts_first"]["status"]
        g2b = ch["counts_second"]["status"]
    pf = report.get("point_file")
    return {"G-S": {"I-3": pf["result"] if pf else "pending",
                    "other": "outside this tool (seal, pre-run audit, implementation tests)"},
            "G0": g0, "G1": g1, "G2a": g2a, "G2b": g2b,
            "G3": "outside this tool (two-path agreement, post-judgement audit, I-2/I-2b)"}


def grade(report: dict) -> dict:
    """10 (provisional): unjudgeable > fail > pending > flags > pass."""
    g = report["gates"]
    statuses = [g["G0"], g["G1"], g["G2a"], g["G2b"], g["G-S"]["I-3"]]
    reasons = []
    if "unjudgeable" in statuses:
        label = "판정 불가"
        reasons = [k for k in ("G0", "G1", "G2a", "G2b") if g[k] == "unjudgeable"]
        if g["G-S"]["I-3"] == "unjudgeable":
            reasons.append("I-3")
    elif "fail" in statuses:
        label = "미달"
        reasons = [k for k in ("G0", "G1", "G2a", "G2b") if g[k] == "fail"]
    elif "pending" in statuses:
        label = "보류(입력 미완)"
        reasons = [k for k in ("G0", "G1", "G2a", "G2b") if g[k] == "pending"]
        if g["G-S"]["I-3"] == "pending":
            reasons.append("I-3")
    elif report["flags"]:
        label = "조건부 통과"
    else:
        label = "통과"
    return {"label": label, "provisional": True, "reasons": reasons,
            "n_flags": len(report["flags"]),
            "note": "G-S (seal/audit/tests) and G3 (two-path, audit, I-2) are outside this tool"}


# ----------------------------------------------------------------------------- hash compare
def hash_compare(bundle: str, a: Path, b: Path) -> dict:
    """I-2b / V-2 replay: commands_sha256 per key between two runs of the same bundle."""
    def index(path):
        if bundle == "ra":
            doc = load_json(path)
            variants = [str(r.get("variant")) for r in doc.get("runs", []) if r.get("variant")]
            kmap, _ = kt_scale_map(variants) if variants else ({}, [])
            out = {}
            for run in doc.get("runs", []):
                src = {k: run.get(k) for k in ("stage", "level", "mast", "point", "variant")}
                if not all(src.values()):
                    src = parse_ra_id(run.get("id", "")) or {}
                if not src:
                    continue
                key = "|".join((src["stage"], src["level"], src["mast"], src["point"],
                                normalize_variant(src["stage"], src["variant"], kmap)))
                out.setdefault(key, []).append(run.get("commands_sha256"))
            return out
        out = {}
        for line in load_jsonl(path):
            job = line.get("job") or {}
            d1 = job.get("d1") or {}
            key = f"{d1.get('slope_name')}|{d1.get('level')}|x{d1.get('crawler_k_scale')}|" \
                  f"{job.get('setting')}|e{job.get('eps')}|k1{job.get('k1')}"
            out.setdefault(key, []).append(line.get("commands_sha256"))
        return out

    ia, ib = index(a), index(b)
    diff = sorted(k for k in set(ia) & set(ib) if ia[k] != ib[k])
    dup = sorted(k for k in set(ia) | set(ib) if len(ia.get(k, [])) > 1 or len(ib.get(k, [])) > 1)
    only_a, only_b = sorted(set(ia) - set(ib)), sorted(set(ib) - set(ia))
    none = sorted(k for k in set(ia) | set(ib) if None in ia.get(k, []) + ib.get(k, []))
    same = not (diff or dup or only_a or only_b or none)
    return {"bundle": bundle, "a": str(a), "b": str(b), "a_sha256": file_sha256(a),
            "b_sha256": file_sha256(b), "n_a": len(ia), "n_b": len(ib), "differ": diff,
            "duplicates": dup, "only_a": only_a, "only_b": only_b, "missing_hash": none,
            "result": "same" if same else "different"}


# ---------------------------------------------------------------------------------- output
def strip_for_json(obj):
    if isinstance(obj, dict):
        return {k: strip_for_json(v) for k, v in obj.items() if k != "key_tuple"}
    if isinstance(obj, list):
        return [strip_for_json(v) for v in obj]
    if isinstance(obj, tuple):
        return [strip_for_json(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return str(obj)
    return obj


def to_markdown(report: dict) -> str:
    lines = [f"# D8x 경로 2 재집계 ({TOOL} {TOOL_VERSION})", "",
             f"- 도구 sha256: `{report['tool_sha256']}`",
             f"- $F_{{D8}}$ = {report['F_D8_N']:.5f} N",
             f"- 기대 태그 출처: {report['expect']['source']}", ""]
    g = report["grade"]
    lines += [f"## 등급(잠정): **{g['label']}**", "", f"- 사유: {g['reasons']}",
              f"- FLAG 수: {g['n_flags']}", f"- {g['note']}", "", "## 관문", "",
              "| 관문 | 결과 |", "|---|---|"]
    for k, v in report["gates"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## 묶음별 수 (E-1)", "", "| 묶음 | 기대 | 실제 | 통과 | 실패 | 불가 | 상태 |",
              "|---|---|---|---|---|---|---|"]
    for name, b in report["bundles"].items():
        lines.append(f"| {name} | {b.get('expected', '')} | {b.get('actual', '')} | "
                     f"{b.get('pass', '')} | {b.get('fail', '')} | {b.get('unjudgeable', '')} | "
                     f"{b.get('status')} |")
        for part, c in (b.get("parts") or {}).items():
            lines.append(f"| {name} K1 {part} | {c['expected']} | {c['actual']} | {c['pass']} | "
                         f"{c['fail']} | {c['unjudgeable']} | {c['status']} |")
    for name, b in report["bundles"].items():
        probs = list(b.get("problems") or [])
        for c in (b.get("parts") or {}).values():
            probs.extend(c.get("problems") or [])
        for p in probs[:20]:
            lines.append(f"- {name}: {p}")
    sel = report["selection"]
    lines += ["", "## 선정", "", f"- W: {sel['W'].get('status')} "
              f"{sel['W'].get('point', '')} {sel['W'].get('floor', '')} m = {sel['W'].get('m_N', '')} N",
              f"- V: {sel['V'].get('status')} {sel['V'].get('floor', '')} "
              f"{sel['V'].get('row', '')} J1 = {sel['V'].get('J1_N', '')} N"]
    inv = report["invariance"]
    lines += ["", "## 불변·승계", "", f"- V-1: {inv['V-1']['class']} (짝 {inv['V-1']['pairs']}, "
              f"다름 {len(inv['V-1']['K1_DEPENDENT'])})",
              f"- V-2: {inv['V-2']['class']} (작동 점 {len(inv['V-2']['LAS_DEPENDENT'])})",
              f"- V-3: {len(inv['V-3'])} 짝 기록"]
    lines += ["", "## FLAG", ""]
    for f in report["flags"][:60]:
        lines.append(f"- {json.dumps(f, ensure_ascii=False)}")
    lines += ["", "## 실패·불가 행", ""]
    all_rows = []
    for part in list((report.get("ra") or {}).values()) + list((report.get("rc") or {}).values()):
        all_rows.extend(part["rows"])
    if report.get("chrono"):
        all_rows.extend(report["chrono"]["rows"])
    if report.get("g0"):
        all_rows.extend(report["g0"]["rows"])
    for r in all_rows:
        if r["verdict"] != "pass":
            lines.append(f"- {r['bundle']} {r.get('key')} k1={r.get('k1', '')}: {r['verdict']} "
                         f"items {r.get('failed_items')} fail {r['fail'][:3]} "
                         f"unjudgeable {r['unjudgeable'][:3]}")
    return "\n".join(lines) + "\n"


def summary_line(report: dict) -> dict:
    b = report["bundles"]
    return {"tool": TOOL, "grade": report["grade"]["label"], "gates": {
        k: (v if isinstance(v, str) else v.get("I-3")) for k, v in report["gates"].items()},
        "counts": {k: [v.get("expected"), v.get("actual"), v.get("pass"), v.get("fail"),
                       v.get("unjudgeable"), v.get("status")] for k, v in b.items()},
        "W": report["selection"]["W"].get("floor"), "V": report["selection"]["V"].get("floor"),
        "V1": report["invariance"]["V-1"]["class"], "V2": report["invariance"]["V-2"]["class"],
        "flags": len(report["flags"])}


def exit_code(report: dict) -> int:
    label = report["grade"]["label"]
    if label == "판정 불가":
        return 2
    if label == "미달":
        return 1
    return 0


def emit(doc: dict, args, md: str | None, summary: dict) -> None:
    text = md if (args.format == "md" and md is not None) else json.dumps(
        strip_for_json(doc), indent=1, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
    sys.stdout.write(json.dumps(summary, ensure_ascii=True) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    rc = sub.add_parser("recount")
    rc.add_argument("--points")
    rc.add_argument("--g0")
    rc.add_argument("--g0-base")
    rc.add_argument("--ra")
    rc.add_argument("--ra-k1")
    rc.add_argument("--rc")
    rc.add_argument("--rc-k1")
    rc.add_argument("--chrono", nargs="*", default=None)
    rc.add_argument("--expect")
    rc.add_argument("--rules-dir")
    rc.add_argument("--skip-identity", action="store_true")
    rc.add_argument("--out")
    rc.add_argument("--format", choices=("json", "md"), default="json")
    hc = sub.add_parser("hash-compare")
    hc.add_argument("--bundle", choices=("ra", "rc"), required=True)
    hc.add_argument("a")
    hc.add_argument("b")
    hc.add_argument("--out")
    hc.add_argument("--format", choices=("json", "md"), default="json")
    sub.add_parser("table")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "table":
            doc = {"A": RA_POINTS, "B": RPX_POINTS, "C": AXIS_VERTICES, "W_floors": W_FLOORS,
                   "R_v": {k: r_v(*v) for k, v in {**RA_POINTS, **RPX_POINTS}.items()},
                   "chrono_rows": list(chrono_expected_rows("<W>", "<V>"))}
            sys.stdout.write(json.dumps(doc, indent=1) + "\n")
            sys.stdout.write(json.dumps({"tool": TOOL, "status": "ok"}) + "\n")
            return 0
        if args.cmd == "hash-compare":
            doc = hash_compare(args.bundle, Path(args.a), Path(args.b))
            md = f"# hash-compare {args.bundle}: {doc['result']}\n" + "\n".join(
                f"- {k}: {doc[k][:20]}" for k in ("differ", "duplicates", "only_a", "only_b",
                                                  "missing_hash")) + "\n"
            emit(doc, args, md, {"tool": TOOL, "result": doc["result"], "differ": len(doc["differ"])})
            return 0 if doc["result"] == "same" else 1
        report = recount(args)
        emit(report, args, to_markdown(report), summary_line(report))
        return exit_code(report)
    except InputError as exc:
        sys.stdout.write(json.dumps({"tool": TOOL, "status": "input_error", "error": str(exc)}) + "\n")
        return 2
    except Exception as exc:  # internal error: exit 3 with the trace on stderr
        traceback.print_exc()
        sys.stdout.write(json.dumps({"tool": TOOL, "status": "internal_error",
                                     "error": repr(exc)}) + "\n")
        return 3


if __name__ == "__main__":
    sys.exit(main())
