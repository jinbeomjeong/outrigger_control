"""Path 2 recount of the K-2 touch creep latch judgement (rules ``k2_touch_creep_rules.md`` 8).

Written by control-expert BEFORE any V-2 .. V-7 result; its blob sha is fixed in the pre-launch
record (rules I-3). It does not import or read path 1 (``k2_judge.py``) or ``d8x_judge.py``.
It reads the raw run outputs (harness json / jsonl, series npz, Chrono row json and pads npz)
and recounts the row items J1 .. J11 (rules 5.1), the shadow FLAGs SH-1 .. SH-6 (5.2), the V-5
regression criteria (3.4), the V-6 extra items (3.5), the gates G-A .. G-E (7), the grade (10)
and the B branches (10.1, 5.4).

Field names of the K-2 outputs are not frozen in code: every raw key is read through a field
map (built-in default below, or ``--fields <map.json>``, whose sha256 goes into the output and
the pre-launch record). A missing key is "not judgeable" (exit 2), never a pass.

Sub-commands
  recount         --manifest <inputs.json> --expect <expect.json> [--fields <map.json>]
                  [--rules-dir <k2 folder>] --out <file> [--format json|md]
  expect-template --out <file>                     (the rule counts and tags, to review / edit)
  selftest-d8x    --ra-off <ra_off.json> --ra-on <ra_on.json> [--points <d8x_points.json>]
                  --out <file>  (J items on the stored D8x R-a rows: must give 68 / 6 J3 fails,
                  J3 only; with --points also E-7 on every row)
  points-check    --points <k2_points_5p5_3p5.json> --out <file>   (rev1 2 condition; exit 2 on fail)
  selftest-v5-stored --acc <touch_phase/acceptance> --ps7 <touch_phase/ps7_E.json> --out <file>
                  (rev4 2 format check of the V-5 raw readers on the stored acceptance outputs)

Manifest V-5 for this path is ``v5_raw``: ``{"off": <arm folder>, "tcl": <arm folder>, "sidecars": {"off": [...],
"tcl": [...]}, "c2_sha256": <optional>}`` (rev2 1 / rev4); the flat ``v5`` entries are path 1 input only.

Rev1 (``k2_touch_creep_rules_rev1.md``): d45 execution value = 4-decimal rounding, the point-file
condition (rev1 2), E-7 on every row (rev1 3), the D-hat record items (a)(b) (rev1 4; keys
``k2.dhat_window_open_legs``, ``k2.dhat_window_stroke_mm``, ``k2.dhat_N``, record only).
  selftest-screen --screen-dir <k2/screen> --out <file>   (format check on the 44 screen rows)

Exit codes: 0 pass, 1 fail (a gate failed / selftest mismatch), 2 not judgeable or input error,
3 internal error. The last stdout line is JSON. Units: N, s, deg, bar, m.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
import traceback
from pathlib import Path

import numpy as np

TOOL = "k2_recount"
VERSION = "1.4"
"""1.4 (rev5, before any result): provenance per V-5 step (d8 from its meta), G8 c2.py via sidecar HEAD / clean and
the k2-run c2.py sha, G8 K-2 evidence from the row fields, flatten sidecar not read, rev5 seal."""
"""1.3 (rev2 / rev3, before any result): V-5 from the raw outputs (``manifest["v5_raw"]``: off / tcl arm folders,
sidecars) with the criteria.md absolute items and pass->fail vs the off arm; V-6 SH-1 .. SH-6; E-5 / I-9 checks
(V-2 / V-4 options off, V-3 option values, V-6 moving damping / open shares); rev2 / rev3 seals."""

# ------------------------------------------------------------------ rule constants (rules 0, 5)
F_MIN_N = 9414.589
F_D8_N = F_MIN_N + 5000.0
SH6_MARGIN_N = 2000.0
SH3_READY_S = 3.0
SH4_EROSION_N = -3000.0
ATTITUDE_LIMIT_DEG = 0.2
READY_LIMIT_S = 120.0
MOVING_LIMIT_BAR = 210.0
LOCKED_LIMIT_BAR = 350.0
LIFT_WINDOW_MIN_S = 1.0
SH2_WINDOW_S = 0.3
LATCH_WINDOW_SAMPLES = 5
CONTROL_PERIOD_S = 0.1
CP_LEVEL = 0.95
CP_LIMIT = 0.03
STROKE_EVENTS = ("FAULT_STROKE_END", "WARN_LIFT_STROKE_LIMITED", "FAULT_LIFT_STROKE_LIMIT")
WARN_ALLOWED = ("WARN_PROBE_STIFFNESS_OUT_OF_RANGE",)
LATCH_EVENT = "INFO_TOUCH_CREEP_LATCH"
CAP_EVENT = "INFO_TOUCH_CREEP_CAP"
DIP_EVENT = "INFO_TOUCH_DIP_HELD"
LEGS = ("FL", "FR", "RL", "RR")
TCL_SUFFIX = "_TCL"
RULES_FILE = "k2_touch_creep_rules.md"
RULES_SEAL = "k2_touch_creep_rules.sha256"
RULES_SHA256 = "a3658197bdab02870a0b362144606f404021ebac90662a35efacfa8dbe477263"
REV1_FILE = "k2_touch_creep_rules_rev1.md"
REV1_SEAL = "k2_touch_creep_rules_rev1.sha256"
REV1_SHA256 = "5ba081c62f8aef0edc5bb99119d7586b0d2914761582f2323c289f472f244776"
REV2_FILE = "k2_touch_creep_rules_rev2.md"
REV2_SEAL = "k2_touch_creep_rules_rev2.sha256"
REV2_SHA256 = "b3f1b41f27030c75aec726d2a3feb5abc36697864e0d83766a8fe0c4460394ea"
REV3_FILE = "k2_touch_creep_rules_rev3.md"
REV3_SEAL = "k2_touch_creep_rules_rev3.sha256"
REV3_SHA256 = "8bcdb0ed1fdf6d730ac781929e93b233972d1e80566e1ae14ffb7ddf049d6e61"
REV4_FILE = "k2_touch_creep_rules_rev4.md"
REV4_SEAL = "k2_touch_creep_rules_rev4.sha256"
REV4_SHA256 = "82160ff54874e3d43bf7c5a1ae96d6e8612b1e7635aaccea39a4299352ce00c5"
REV5_FILE = "k2_touch_creep_rules_rev5.md"
REV5_SEAL = "k2_touch_creep_rules_rev5.sha256"
REV5_SHA256 = "73b877580ec5dc94a46a38d2ed620372cddd17dd38eef06126d84843b485eccc"
C2_SHA256_RUN = "f58ee42b0f10ea42ceac5768e6ed373a38ee5e14440d9fc831536700b45ba6b1"
"""rev2 1 common: sha256 of the k2-run working copy of 03_src/outrigger_sim/control/c2.py (provenance c2_sha256)."""
REG_JUDGED_SHA256 = "2900db889efc73070c3a8fbe557b1a4ad9ee3392afc099ba00be1d0549174ec9"
REG_RECORD_SHA256 = "d4f58334c6ca7c393c35072a798c09f4995d7fde274e0af6b21b99f977d503eb"
V5_COUNTS = {"soil": 60, "d8": 576, "noise_L2": 855, "regression": 93, "ps7": 20, "g8_safe_stop": 83}
D8_GUARD_KN = 14.41
D8_ATT_DEG = 0.2
D8_READY_S = 100.0
S1_FRONT = ("S1@FL", "S1@FR")
GOOD_VERDICTS = (True, "pass", "stroke_limited_pass")
# rev3 1: V-3 E-5 references (run YAML computed values) and the option key set per arm
KT_REL_YAML = 0.23309250561413625
EPS_AUG_M_S = 0.00209243016
LOCK_EPS_M_S = 1e-6
FS_FRONT_N = 4000.0
FS_REAR_SCALE = 0.8333
PAD_ZETA_MOVING = 0.10
CRAWLER_C_SCALE = 2.0
ARM_PRESET = {"H0": "none", "L1eq": "l1eq", "L1eq_fs": "l1eq_fs", "L1eq_zm": "l1eq_zm", "AUG": "aug",
              "AUG_crc2": "aug_crc2", "AUG_eps": "aug_eps"}
_KT, _FS, _ZM = "crawler_kt_rel", "seal_fs_front_N", "pad_zeta_moving"
ARM_OPTION_KEYS = {"H0": set(), "L1eq": {_KT}, "L1eq_fs": {_KT, _FS}, "L1eq_zm": {_KT, _ZM},
                   "AUG": {_KT, _FS, _ZM}, "AUG_crc2": {_KT, _FS, _ZM, "crawler_c_scale"},
                   "AUG_eps": {_KT, _FS, _ZM, "valve_open_eps_m_s"}}
E7_TOL_DEG = 1e-9
E7_CHRONO_TOL_DEG = 1e-4
POINT_DIAMOND_TOL_DEG = 1e-12
POINT_TABLE_D45_TOL_DEG = 2e-5
DHAT_FLAG_N = 5000.0
V6_FLOORS_DEG = {"fdown3.5": (0.0, 3.5), "k2pp025": (1.375, 2.625)}
DYN_SPEC_FILE = "k2_dyn_spec.md"
DYN_SPEC_SHA256 = "502b0bb78558d40586cbcddb718b6c5d53529de4e78369f454762c9fe73727ff"
V3_KEYS_SHA256 = "d4a030d71e4a365e328fbbf7caa212c378a8671fed8ba206d25b50666255cf95"
V3_ARMS = ("H0", "L1eq", "L1eq_fs", "L1eq_zm", "AUG", "AUG_crc2", "AUG_eps")
V3_JUDGED = ("H0", "L1eq", "L1eq_fs", "L1eq_zm", "AUG", "AUG_eps")
V3_B3_ARMS = ("L1eq", "L1eq_fs", "L1eq_zm", "AUG")
V3_PER_CELL = 273

# ------------------------------------------------------------------ default field map
DEFAULT_FIELDS = {
    "harness_row": {
        "id": "id", "tag": "controller_tag", "k1": "k1_order_gate",
        "tcl": "touch_creep_latch", "commands": "commands_sha256", "fails": "fails",
        "aug_arm": "aug_arm", "is_kplant": "is_kplant", "angles": "angles_deg",
        "point": "point", "series": "series_file",
        "dhat_open": "k2.dhat_window_open_legs", "dhat_stroke": "k2.dhat_window_stroke_mm",
        "dhat": "k2.dhat_N",
        "t_touch": "d8x.t_touch_s", "t_lift": "d8x.t_lift_s", "t_ready": "d8x.t_ready_s",
        "J1": "d8x.J1_min_cyl_after_lift_N", "J1_window": "d8x.J1_window_s",
        "reanchor": "d8x.reanchor_intervals_s", "J2": "d8x.J2_min_cyl_reanchor_N",
        "J3": "d8x.J3_pad_lift_samples", "J4": "d8x.J4_att_max_after_ready_deg",
        "J6": "d8x.J6_max_moving_bar", "events": "d8x.events",
    },
    "series": {"t": "t_s", "pad_normal": "pad_normal_min_N", "body_rate": "body_rate_rad_s"},
    "chrono_row": {
        "id": "case_id", "tag": "controller_tag", "k1": "k1_order_gate",
        "tcl": "touch_creep_latch", "engine": "engine", "floor_true_deg": "floor_true_deg",
        "t_touch": "t_touch_s", "t_lift": "t_lift_s", "t_ready": "t_ready_s",
        "J1": "J1_min_cyl_after_lift_N", "J1_window": "J1_window_s",
        "reanchor": "reanchor_intervals_s", "J2": "J2_min_cyl_reanchor_N",
        "J4": "J4_att_max_after_ready_deg", "J6": "J6_max_moving_bar",
        "J6_locked": "J6_max_locked_bar", "J10": "crawler_recontact_after_loc",
        "events": "events",
        "dhat_open": "k2.dhat_window_open_legs", "dhat_stroke": "k2.dhat_window_stroke_mm",
        "dhat": "k2.dhat_N",
    },
    "chrono_pads": {"t": "t", "pad_normal": "N"},
    "chrono_rate": {"t": "t", "body_rate": "body_omega"},
}


class NotJudgeable(Exception):
    """A required input is missing or inconsistent (exit 2)."""


# ------------------------------------------------------------------ small helpers
def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def get_path(obj, dotted: str, required: bool = True):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            if required:
                raise NotJudgeable(f"key '{dotted}' missing")
            return None
    return cur


def load_rows(path: Path) -> list[dict]:
    """A json file ({"runs": [...]} / {"results": [...]} / [...]) or a jsonl file."""
    text = Path(path).read_text(encoding="utf-8")
    if str(path).endswith(".jsonl"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    if isinstance(data, list):
        return data
    for key in ("runs", "results", "rows"):
        if key in data and isinstance(data[key], list):
            return data[key]
    raise NotJudgeable(f"{path}: no row list (runs / results / rows)")


def event_pairs(events) -> list[tuple[float | None, str]]:
    out = []
    for item in events or []:
        if isinstance(item, str):
            out.append((None, item))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            out.append((float(item[0]), str(item[1])))
        elif isinstance(item, dict):
            out.append((item.get("t_s", item.get("t")), str(item.get("name"))))
        else:
            raise NotJudgeable(f"event entry not understood: {item!r}")
    return out


def prefix(name: str) -> str:
    return name.split(":")[0]


def event_families(names: list[str]) -> dict:
    stroke = [n for n in names if n.startswith(STROKE_EVENTS)]
    return {
        "J7": stroke,
        "J8": [n for n in names if n.startswith("FAULT_") and n not in stroke],
        "J9": [n for n in names if n.startswith("WARN_") and n not in stroke
               and prefix(n) not in WARN_ALLOWED],
        "E3": [n for n in names if n.startswith("REJ_")],
        "latch": [n for n in names if prefix(n) == LATCH_EVENT],
        "cap": [n for n in names if prefix(n) == CAP_EVENT],
        "dip": [n for n in names if prefix(n) == DIP_EVENT],
        "creep_any": [n for n in names if n.startswith("INFO_TOUCH_CREEP_")],
    }


def latch_times(pairs) -> dict[int, float]:
    """First INFO_TOUCH_CREEP_LATCH time per leg index."""
    out: dict[int, float] = {}
    for t, name in pairs:
        if prefix(name) == LATCH_EVENT and ":" in name:
            leg = name.split(":", 1)[1]
            if leg in LEGS and LEGS.index(leg) not in out and t is not None:
                out[LEGS.index(leg)] = float(t)
    return out


# ------------------------------------------------------------------ series metrics
def series_metrics(t, pad, rate, t_touch: float, latches: dict[int, float]) -> dict:
    """J3 recount, SH-1 post-latch lift, SH-2 rocking amplitude, J3 from first four-pad contact."""
    t = np.asarray(t, float)
    pad = np.asarray(pad, float)
    if pad.ndim != 2 or pad.shape[1] != 4 or pad.shape[0] != t.shape[0]:
        raise NotJudgeable(f"pad series shape {pad.shape} vs t {t.shape}")
    lifted = pad <= 0.0
    after = t >= t_touch - 1e-9
    j3 = int(np.sum(np.any(lifted, axis=1) & after))
    j3_min = float(np.min(pad[after])) if after.any() else None
    contact_all = np.all(pad > 0.0, axis=1)
    if contact_all.any():
        i4 = int(np.argmax(contact_all))
        j3_all4 = int(np.sum(np.any(lifted[i4:], axis=1)))
    else:
        j3_all4 = None
    sh1 = {}
    for leg, t_l in latches.items():
        win = (t > t_l + 1e-9) & (t < t_touch - 1e-9)
        sh1[LEGS[leg]] = int(np.sum(lifted[win, leg]))
    rate_amp = None
    if rate is not None:
        tr, q = rate
        tr = np.asarray(tr, float)
        q = np.asarray(q, float)
        seg = (tr >= t_touch - SH2_WINDOW_S - 1e-9) & (tr < t_touch - 1e-9)
        if seg.sum() >= 2:
            w = q[seg, :2]
            rate_amp = float(np.degrees(np.max(np.abs(w - w.mean(axis=0)))))
    return {"J3_series": j3, "J3_min_N_series": j3_min, "J3_from_first_all4": j3_all4,
            "SH1_post_latch_lift": sh1, "SH2_rate_amp_deg_s": rate_amp}


def false_latch(t, pad, latches: dict[int, float]) -> list[str]:
    """V-6 L2b: true pad normal <= 0 at the latch time or at any of the 5 window sample times."""
    t = np.asarray(t, float)
    pad = np.asarray(pad, float)
    bad = []
    for leg, t_l in latches.items():
        for k in range(LATCH_WINDOW_SAMPLES):
            ts = t_l - k * CONTROL_PERIOD_S
            idx = int(np.searchsorted(t, ts + 1e-9)) - 1
            if idx < 0 or pad[idx, leg] <= 0.0:
                bad.append(f"{LEGS[leg]}@{ts:.3f}")
                break
    return bad


# ------------------------------------------------------------------ points (rules 3.2, rev1 1-3)
V4_TAGS = ("pitch+", "pitch-", "roll+", "roll-", "r+p+0.25", "r+p+0.5", "r+p+0.75", "r+p-0.25",
           "r+p-0.5", "r+p-0.75", "r-p+0.5", "r-p-0.5", "d45++", "d45+-", "d45-+", "d45--")


def v4_table_points(roll_half: float = 5.5, pitch_half: float = 3.5) -> dict:
    """Rules 3.2 table (exact values; d45 = roll_half * pitch_half / (roll_half + pitch_half))."""
    pts = {"pitch+": (0.0, pitch_half), "pitch-": (0.0, -pitch_half),
           "roll+": (roll_half, 0.0), "roll-": (-roll_half, 0.0)}
    for tag in V4_TAGS:
        if tag.startswith("r") and "p" in tag and not tag.startswith("roll"):
            sr = 1.0 if tag[1] == "+" else -1.0
            sp = 1.0 if tag[3] == "+" else -1.0
            frac = float(tag[4:])
            pts[tag] = (sr * frac * roll_half, sp * (1.0 - frac) * pitch_half)
    d = roll_half * pitch_half / (roll_half + pitch_half)
    for tag in ("d45++", "d45+-", "d45-+", "d45--"):
        pts[tag] = ((1.0 if tag[3] == "+" else -1.0) * d, (1.0 if tag[4] == "+" else -1.0) * d)
    return pts


def v4_diamond_points(roll_half: float = 5.5, pitch_half: float = 3.5) -> dict:
    """Rev1 1: the execution values = the table with the edge and d45 points rounded to 4 decimals
    (the same construction as ``d8x_diag.diamond_points``, re-implemented here)."""
    exact = v4_table_points(roll_half, pitch_half)
    out = {}
    for tag, (r, p) in exact.items():
        if tag in ("pitch+", "pitch-", "roll+", "roll-"):
            out[tag] = (r, p)
        elif tag.startswith("d45"):
            d = round(roll_half * pitch_half / (roll_half + pitch_half), 4)
            out[tag] = (math.copysign(d, r), math.copysign(d, p))
        else:
            out[tag] = (round(r, 4), round(p, 4))
    return out


def load_point_file(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    pts = data.get("ra_points")
    if not isinstance(pts, list):
        raise NotJudgeable(f"{path}: no ra_points list")
    return {p["tag"]: (float(p["roll_deg"]), float(p["pitch_deg"])) for p in pts}


def points_check(path: Path) -> dict:
    """Rev1 2: (i) = diamond construction (<= 1e-12 deg), (ii) table within 2e-5 deg (d45) /
    1e-12 deg (the other 12 points)."""
    got = load_point_file(path)
    dia, tab = v4_diamond_points(), v4_table_points()
    problems = []
    if sorted(got) != sorted(V4_TAGS):
        problems.append(f"tags {sorted(got)}")
    worst = {"diamond": 0.0, "table_d45": 0.0, "table_other": 0.0}
    for tag in V4_TAGS:
        if tag not in got:
            continue
        dd = max(abs(a - b) for a, b in zip(got[tag], dia[tag]))
        dt = max(abs(a - b) for a, b in zip(got[tag], tab[tag]))
        worst["diamond"] = max(worst["diamond"], dd)
        key = "table_d45" if tag.startswith("d45") else "table_other"
        worst[key] = max(worst[key], dt)
        tol = POINT_TABLE_D45_TOL_DEG if tag.startswith("d45") else POINT_DIAMOND_TOL_DEG
        if dd > POINT_DIAMOND_TOL_DEG:
            problems.append(f"{tag}: diamond diff {dd:.3g} deg")
        if dt > tol:
            problems.append(f"{tag}: table diff {dt:.3g} deg > {tol:g}")
    return {"path": str(path), "sha256": sha256_file(path), "worst_diff_deg": worst,
            "problems": problems, "ok": not problems}


def e7_check(row: dict, f: dict, kind: str, points: dict | None, floor_deg) -> str | None:
    """E-7: harness angles = point file (<= 1e-9 deg); Chrono floor_true_deg = 3.5 table (1e-4)."""
    if kind == "harness":
        if points is None:
            return None
        tag = get_path(row, f["point"])
        ang = get_path(row, f["angles"])
        if tag not in points:
            return f"point {tag} not in the point file"
        d = max(abs(float(a) - b) for a, b in zip(ang, points[tag]))
        return None if d <= E7_TOL_DEG else f"{tag} angles {ang} vs {points[tag]} ({d:.3g} deg)"
    if floor_deg is None:
        return None
    ang = get_path(row, f["floor_true_deg"])
    d = max(abs(float(a) - b) for a, b in zip(ang, floor_deg))
    return None if d <= E7_CHRONO_TOL_DEG else f"floor {ang} vs {floor_deg} ({d:.3g} deg)"


def dhat_summary(off: list[dict], tcl: list[dict]) -> dict:
    """Rev1 4 (a)(b), record only: D-hat window open legs / stroke and the K-2 minus off D-hat."""
    om = {pair_key(r): r for r in off}
    missing = 0
    open_rows, stroke_max, deltas = 0, None, []
    for r in tcl:
        d = r.get("dhat") or {}
        if d.get("open_legs") is None or d.get("stroke_mm") is None or d.get("dhat_N") is None:
            missing += 1
            continue
        if d["open_legs"]:
            open_rows += 1
        s = [float(x) for x in d["stroke_mm"] if x is not None]  # None = leg not open (k2_record)
        if s:
            stroke_max = max(s) if stroke_max is None else max(stroke_max, max(s))
        o = (om.get(pair_key(r)) or {}).get("dhat") or {}
        if is_num(o.get("dhat_N")) and is_num(d["dhat_N"]):
            deltas.append((d["dhat_N"] - o["dhat_N"], r["id"]))
    vals = [v for v, _ in deltas]
    return {"tcl_rows": len(tcl), "missing": missing, "open_leg_rows": open_rows,
            "stroke_max_mm": stroke_max, "pairs": len(deltas),
            "delta_quantiles_N": (np.quantile(vals, [0, .05, .5, .95, 1]).tolist() if vals else None),
            "abs_delta_ge_5kN": sorted(((round(v, 1), i) for v, i in deltas if abs(v) >= DHAT_FLAG_N),
                                       key=lambda x: -abs(x[0]))}


# ------------------------------------------------------------------ row judgement (rules 5.1)
def _close(value, ref) -> bool:
    if not is_num(value):
        return False
    if ref == 0:
        return abs(value) <= 1e-12
    return abs(value - ref) <= 1e-9 * abs(ref)


def check_options_off(row: dict) -> list[str]:
    """rev2 4 V-2 / V-4: no dissipation arm (aug_arm None, k2.aug None)."""
    out = []
    if row.get("aug_arm") is not None:
        out.append(f"E-5 aug_arm {row.get('aug_arm')!r} on a V-2 / V-4 row")
    if (row.get("k2") or {}).get("aug") is not None:
        out.append("E-5 k2.aug present on a V-2 / V-4 row")
    return out


def _fractions_ok(values) -> bool:
    if isinstance(values, dict):
        values = [values.get(leg) for leg in LEGS]
    return (isinstance(values, (list, tuple)) and len(values) == 4
            and all(is_num(v) and 0.0 <= v <= 1.0 for v in values))


def check_v3_arm(row: dict, arm: str) -> list[str]:
    """rev2 4 / rev3 1: E-5 options and values of a V-3 row, I-9 open shares."""
    out = []
    aug = (row.get("k2") or {}).get("aug")
    if not isinstance(aug, dict):
        return ["E-5 k2.aug missing"]
    if aug.get("arm") != arm or row.get("aug_arm") != arm:
        out.append(f"E-5 arm {aug.get('arm')!r} / {row.get('aug_arm')!r} != {arm}")
    if aug.get("is_kplant") is not True:
        out.append("I-9 is_kplant not true")
    plant = aug.get("plant_aug") or {}
    if plant.get("preset") != ARM_PRESET[arm]:
        out.append(f"E-5 preset {plant.get('preset')!r} != {ARM_PRESET[arm]}")
    options = plant.get("options")
    if not isinstance(options, dict) or set(options) != ARM_OPTION_KEYS[arm]:
        out.append(f"E-5 option keys {sorted(options) if isinstance(options, dict) else options} "
                   f"!= {sorted(ARM_OPTION_KEYS[arm])}")
    res = plant.get("resolved") or {}
    want = {}
    if _KT in ARM_OPTION_KEYS[arm]:
        want[_KT] = KT_REL_YAML
    if _FS in ARM_OPTION_KEYS[arm]:
        want.update({_FS: FS_FRONT_N, "seal_fs_rear_scale": FS_REAR_SCALE})
    if _ZM in ARM_OPTION_KEYS[arm]:
        want[_ZM] = PAD_ZETA_MOVING
    if arm == "AUG_crc2":
        want["crawler_c_scale"] = CRAWLER_C_SCALE
    want["valve_open_eps_m_s"] = EPS_AUG_M_S if arm == "AUG_eps" else LOCK_EPS_M_S
    for key, ref in want.items():
        if not _close(res.get(key), ref):
            out.append(f"E-5 resolved {key} {res.get(key)!r} != {ref!r}")
    if _ZM in ARM_OPTION_KEYS[arm]:
        lock, mov = res.get("cn_lock_N_s_m"), res.get("cn_moving_N_s_m")
        if not (isinstance(lock, list) and isinstance(mov, list) and len(lock) == len(mov) == 4
                and all(_close(m, c * PAD_ZETA_MOVING / 0.03) for c, m in zip(lock, mov))):
            out.append("E-5 cn_moving != cn_lock x 0.10 / 0.03")
    if not _fractions_ok(aug.get("valve_open_fraction_touch_to_lift")):
        out.append("I-9 valve_open_fraction_touch_to_lift missing / out of [0, 1]")
    return out


def check_v6_row(row: dict, engine: str) -> list[str]:
    """rev2 4 / rev3 2: V-6 moving damping (L1 on, L2b off) and the L1 I-9 open shares."""
    out = []
    if engine == "L1":
        if row.get("moving_damping") is not True or not _close(row.get("pad_zeta_moving"), PAD_ZETA_MOVING):
            out.append("E-5 L1 moving damping not on at 0.10")
        if not _fractions_ok(row.get("valve_open_fraction_touch_to_lift")):
            out.append("I-9 L1 valve_open_fraction_touch_to_lift missing / out of [0, 1]")
    elif row.get("moving_damping") is not False or row.get("pad_zeta_moving") is not None:
        out.append("E-5 L2b moving damping not off")
    return out


def judge_row(row: dict, fmap: dict, kind: str, series_root: Path | None, k2_profile: bool,
              chrono_files: dict | None = None, points: dict | None = None,
              floor_deg: tuple | None = None, check=None) -> dict:
    """One row: J items, E items, K-2 evidence and series metrics. kind: harness | chrono.

    ``points``: tag -> (roll, pitch) [deg] of the point file (E-7, harness rows).
    ``floor_deg``: expected (roll, pitch) [deg] of a Chrono row (E-7, ``floor_true_deg``)."""
    f = fmap["harness_row"] if kind == "harness" else fmap["chrono_row"]
    rid = get_path(row, f["id"])
    out = {"id": rid, "not_judgeable": [], "fail_items": []}
    try:
        e7 = e7_check(row, f, kind, points, floor_deg)
    except NotJudgeable as exc:
        e7 = str(exc)
    if e7:
        out["not_judgeable"].append(f"E-7 {e7}")
    if check is not None:
        out["not_judgeable"].extend(check(row))
    out["dhat"] = {"open_legs": get_path(row, f["dhat_open"], required=False),
                   "stroke_mm": get_path(row, f["dhat_stroke"], required=False),
                   "dhat_N": get_path(row, f["dhat"], required=False)}
    try:
        tag = get_path(row, f["tag"])
        k1 = get_path(row, f["k1"])
        tcl = bool(get_path(row, f["tcl"])) if k2_profile else False
        pairs = event_pairs(get_path(row, f["events"]))
        names = [n for _, n in pairs]
        fam = event_families(names)
        t_touch = get_path(row, f["t_touch"])
        t_lift = get_path(row, f["t_lift"])
        t_ready = get_path(row, f["t_ready"])
        j1 = get_path(row, f["J1"])
        j1_win = get_path(row, f["J1_window"])
        reanchor = get_path(row, f["reanchor"])
        j2 = get_path(row, f["J2"], required=bool(reanchor))
        j4 = get_path(row, f["J4"])
        j6 = get_path(row, f["J6"])
    except NotJudgeable as exc:
        out["not_judgeable"].append(str(exc))
        return out
    items = {
        "J1": is_num(j1) and j1 >= F_D8_N,
        "J4": is_num(j4) and j4 <= ATTITUDE_LIMIT_DEG,
        "J5": is_num(t_ready) and t_ready <= READY_LIMIT_S,
        "J6": is_num(j6) and j6 <= MOVING_LIMIT_BAR,
        "J7": not fam["J7"], "J8": not fam["J8"], "J9": not fam["J9"],
        "E-2": all(v is not None for v in (t_touch, t_lift, t_ready)),
        "E-3": not fam["E3"],
    }
    if reanchor:
        items["J2"] = is_num(j2) and j2 >= F_D8_N
    if kind == "harness":
        fails = get_path(row, f["fails"], required=False)
        items["J11"] = fails is not None and not fails
        j3 = get_path(row, f["J3"], required=False)
    else:
        locked = get_path(row, f["J6_locked"], required=False)
        if locked is not None:
            items["J6_locked"] = is_num(locked) and locked <= LOCKED_LIMIT_BAR
        recon = get_path(row, f["J10"], required=False)
        if recon is None:
            out["not_judgeable"].append("J10 crawler recontact field missing")
        else:
            items["J10"] = recon == 0 or recon is False
        j3 = None
    if is_num(j1_win) and j1_win < LIFT_WINDOW_MIN_S:
        out["not_judgeable"].append(f"E-10 lift-off window {j1_win:.3f} s < 1 s")
    latches = latch_times(pairs)
    # series (J3 recount, SH-1, SH-2)
    metrics = None
    try:
        if kind == "harness":
            sname = get_path(row, f["series"], required=k2_profile)
            if sname is not None and series_root is not None and is_num(t_touch):
                s = np.load(Path(series_root) / sname, allow_pickle=False)
                sf = fmap["series"]
                metrics = series_metrics(s[sf["t"]], s[sf["pad_normal"]],
                                         (s[sf["t"]], s[sf["body_rate"]]), t_touch, latches)
        elif chrono_files and is_num(t_touch):
            pf = fmap["chrono_pads"]
            pads = np.load(chrono_files["pads"], allow_pickle=False)
            rate = None
            if chrono_files.get("rate"):
                rf = fmap["chrono_rate"]
                r = np.load(chrono_files["rate"], allow_pickle=False)
                rate = (r[rf["t"]], r[rf["body_rate"]])
            metrics = series_metrics(pads[pf["t"]], pads[pf["pad_normal"]], rate, t_touch, latches)
            out["false_latch"] = false_latch(pads[pf["t"]], pads[pf["pad_normal"]], latches)
    except (OSError, KeyError, ValueError, NotJudgeable) as exc:
        out["not_judgeable"].append(f"E-8 series: {exc}")
    if metrics is not None:
        if j3 is not None and j3 != metrics["J3_series"]:
            out["not_judgeable"].append(f"J3 row {j3} != series recount {metrics['J3_series']}")
        j3 = metrics["J3_series"] if j3 is None else j3
    elif k2_profile:
        out["not_judgeable"].append("E-8 1 ms pad normal series missing")
    if j3 is None:
        out["not_judgeable"].append("J3 not available")
    else:
        items["J3"] = j3 == 0
    # E-4 K-2 evidence, E-6 tag
    if k2_profile:
        if tcl:
            legs = {n.split(":", 1)[1] for n in fam["latch"] if ":" in n}
            if legs != set(LEGS):
                out["not_judgeable"].append(f"E-4 latch legs {sorted(legs)}")
            if fam["dip"]:
                out["not_judgeable"].append(f"E-4 {DIP_EVENT} in a K-2 row")
            if not str(tag).endswith(TCL_SUFFIX):
                out["not_judgeable"].append(f"E-6 K-2 row tag {tag}")
        else:
            if fam["creep_any"]:
                out["not_judgeable"].append("E-4 INFO_TOUCH_CREEP_* in an off row")
            if str(tag).endswith(TCL_SUFFIX):
                out["not_judgeable"].append(f"E-6 off row tag {tag}")
    out.update({
        "tag": tag, "k1": bool(k1), "tcl": tcl, "items": items,
        "fail_items": sorted(k for k, ok in items.items() if not ok),
        "values": {"J1_N": j1, "J2_N": j2 if reanchor else None, "J3": j3, "t_ready_s": t_ready,
                   "t_touch_s": t_touch, "J4_deg": j4, "J6_bar": j6},
        "cap_events": len(fam["cap"]), "latch_legs": sorted(LEGS[i] for i in latches),
        "metrics": metrics,
    })
    if kind == "harness":
        out["commands_sha256"] = get_path(row, fmap["harness_row"]["commands"], required=False)
    return out


def row_status(r: dict) -> str:
    if r["not_judgeable"]:
        return "not_judgeable"
    return "fail" if r["fail_items"] else "pass"


# ------------------------------------------------------------------ bundle helpers
def tag_histogram(rows: list[dict]) -> dict:
    hist: dict = {}
    for r in rows:
        hist[str(r.get("tag"))] = hist.get(str(r.get("tag")), 0) + 1
    return hist


def summarize(rows: list[dict]) -> dict:
    st = [row_status(r) for r in rows]
    return {"n": len(rows), "pass": st.count("pass"), "fail": st.count("fail"),
            "not_judgeable": st.count("not_judgeable"),
            "fail_ids": [r["id"] for r, s in zip(rows, st) if s == "fail"],
            "not_judgeable_ids": [r["id"] for r, s in zip(rows, st) if s == "not_judgeable"]}


def pair_key(r: dict) -> tuple:
    return (r["id"], r.get("k1"))


def shadow(off: list[dict], tcl: list[dict], flag_enabled: bool = True) -> dict:
    """SH-1 .. SH-6 on one bundle (paired by id and K1 arm, rules 5.2, E-11)."""
    om = {pair_key(r): r for r in off}
    tm = {pair_key(r): r for r in tcl}
    unpaired = sorted(set(om) ^ set(tm))
    keys = sorted(set(om) & set(tm))
    res = {"pairs": len(keys), "unpaired": len(unpaired), "flags": []}
    if unpaired:
        res["not_judgeable"] = f"E-11 unpaired keys {len(unpaired)}"
        return res
    sh1 = [k for k in keys if (tm[k].get("metrics") or {}).get("SH1_post_latch_lift")
           and any(v > 0 for v in tm[k]["metrics"]["SH1_post_latch_lift"].values())]
    amp_off = [om[k]["metrics"]["SH2_rate_amp_deg_s"] for k in keys
               if om[k].get("metrics") and om[k]["metrics"]["SH2_rate_amp_deg_s"] is not None]
    amp_tcl = [tm[k]["metrics"]["SH2_rate_amp_deg_s"] for k in keys
               if tm[k].get("metrics") and tm[k]["metrics"]["SH2_rate_amp_deg_s"] is not None]
    d_ready = {k: tm[k]["values"]["t_ready_s"] - om[k]["values"]["t_ready_s"] for k in keys
               if is_num(tm[k]["values"].get("t_ready_s")) and is_num(om[k]["values"].get("t_ready_s"))}
    j1_off = [om[k]["values"]["J1_N"] for k in keys if is_num(om[k]["values"].get("J1_N"))]
    j1_tcl = [tm[k]["values"]["J1_N"] for k in keys if is_num(tm[k]["values"].get("J1_N"))]
    d_j1 = sorted((tm[k]["values"]["J1_N"] - om[k]["values"]["J1_N"], k[0]) for k in keys
                  if is_num(tm[k]["values"].get("J1_N")) and is_num(om[k]["values"].get("J1_N")))
    caps = sum(tm[k].get("cap_events", 0) for k in keys)
    near = []
    for k in keys:
        v = tm[k]["values"]
        for name in ("J1_N", "J2_N"):
            if is_num(v.get(name)) and v[name] < F_D8_N + SH6_MARGIN_N:
                near.append((k[0], name, v[name]))
    res.update({
        "SH1_rows": [k[0] for k in sh1],
        "SH2_median_off": float(np.median(amp_off)) if amp_off else None,
        "SH2_median_tcl": float(np.median(amp_tcl)) if amp_tcl else None,
        "SH3_max_delta_s": max(d_ready.values()) if d_ready else None,
        "SH3_rows": sorted(k[0] for k, d in d_ready.items() if d > SH3_READY_S),
        "SH4_min_off_N": min(j1_off) if j1_off else None,
        "SH4_min_tcl_N": min(j1_tcl) if j1_tcl else None,
        "SH5_cap_events": caps, "SH6_rows": near,
        "record_row_dJ1_worst5": d_j1[:5],
        "record_row_dJ1_quantiles_N": (np.quantile([d for d, _ in d_j1], [0, .25, .5, .75, 1]).tolist()
                                       if d_j1 else None),
    })
    if res["SH4_min_off_N"] is not None and res["SH4_min_tcl_N"] is not None:
        res["SH4_delta_N"] = res["SH4_min_tcl_N"] - res["SH4_min_off_N"]
    else:
        res["SH4_delta_N"] = None
    if not flag_enabled:
        return res
    if sh1:
        res["flags"].append("SH-1")
    if res["SH2_median_off"] is not None and res["SH2_median_tcl"] is not None \
            and res["SH2_median_tcl"] > res["SH2_median_off"]:
        res["flags"].append("SH-2")
    if res["SH3_rows"]:
        res["flags"].append("SH-3")
    if res["SH4_delta_N"] is not None and res["SH4_delta_N"] < SH4_EROSION_N:
        res["flags"].append("SH-4")
    if caps > 0:
        res["flags"].append("SH-5")
    if near:
        res["flags"].append("SH-6")
    return res


def cp_upper(k: int, n: int) -> dict:
    """One-sided Clopper-Pearson upper bound, two paths (beta quantile, binomial cdf root)."""
    from scipy.optimize import brentq
    from scipy.stats import beta, binom
    a = 1.0 if k >= n else float(beta.ppf(CP_LEVEL, k + 1, n - k))
    if k >= n:
        b = 1.0
    else:
        b = float(brentq(lambda p: binom.cdf(k, n, p) - (1.0 - CP_LEVEL), 1e-12, 1.0 - 1e-12,
                         xtol=1e-14))
    return {"k": k, "n": n, "beta_ppf": a, "binom_root": b, "agree": abs(a - b) <= 1e-9,
            "pass": max(a, b) <= CP_LIMIT}


# ------------------------------------------------------------------ V-5 regression
def v5_bundle(spec: dict) -> dict:
    """One V-5 bundle. spec: kind (pass_to_fail | noise_cp | g8), off, tcl (file lists),
    key, status (dotted path to a pass flag / 'pass'|'fail' string), and for g8 ready / faults."""
    kind = spec["kind"]

    def rows(files):
        out = []
        for p in files:
            out.extend(load_rows(Path(p)))
        return out

    off, tcl = rows(spec["off"]), rows(spec["tcl"])

    def status(r):
        v = get_path(r, spec["status"])
        if isinstance(v, bool):
            return v
        if isinstance(v, str) and v.lower() in ("pass", "fail", "ok"):
            return v.lower() in ("pass", "ok")
        raise NotJudgeable(f"status value {v!r}")

    om = {get_path(r, spec["key"]): r for r in off}
    tm = {get_path(r, spec["key"]): r for r in tcl}
    res = {"kind": kind, "n_off": len(off), "n_tcl": len(tcl),
           "unpaired": sorted(str(k) for k in set(om) ^ set(tm))}
    if len(om) != len(off) or len(tm) != len(tcl):
        res["not_judgeable"] = "duplicate keys"
        return res
    if kind == "noise_cp":
        k = sum(not status(r) for r in tcl)
        res["cp"] = cp_upper(k, len(tcl))
        res["pass_to_fail"] = sorted(str(x) for x in set(om) & set(tm)
                                     if status(om[x]) and not status(tm[x]))
        res["pass"] = res["cp"]["pass"] and res["cp"]["agree"]
    elif kind == "pass_to_fail":
        res["pass_to_fail"] = sorted(str(x) for x in set(om) & set(tm)
                                     if status(om[x]) and not status(tm[x]))
        res["pass"] = not res["pass_to_fail"] and not res["unpaired"]
    elif kind == "g8":
        bad = []
        for x in set(om) & set(tm):
            ready_off = bool(get_path(om[x], spec["ready"]))
            ready_tcl = bool(get_path(tm[x], spec["ready"]))
            f_off = {prefix(n) for n in get_path(om[x], spec["faults"]) or [] if n.startswith("FAULT_")}
            f_tcl = {prefix(n) for n in get_path(tm[x], spec["faults"]) or [] if n.startswith("FAULT_")}
            if ready_off and not ready_tcl:
                bad.append((str(x), "ready lost"))
            if f_tcl - f_off:
                bad.append((str(x), f"new FAULT {sorted(f_tcl - f_off)}"))
            if spec.get("status") and status(om[x]) and not status(tm[x]):
                bad.append((str(x), "status pass->fail"))
        res["failures"] = sorted(bad)
        res["pass"] = not bad and not res["unpaired"]
    else:
        raise NotJudgeable(f"V-5 kind {kind}")
    if res["unpaired"]:
        res["pass"] = False
        res["not_judgeable"] = f"unpaired keys {len(res['unpaired'])}"
    return res


# ------------------------------------------------------------------ recount
def judge_files(files: list[str], fmap: dict, series_root, k2: bool,
                points: dict | None = None, check=None) -> list[dict]:
    """``series_root`` None: each file's series folder is ``<file stem>_series`` next to it (the
    ``acc_d8.py --k2 / --aug`` default), so the off and K-2 files of one bundle keep their own series.
    ``check(row)``: extra row identity problems (rev2 4 E-5 / I-9), not judgeable when any."""
    rows = []
    for p in files:
        root = series_root if series_root is not None else Path(p).with_name(Path(p).stem + "_series")
        for row in load_rows(Path(p)):
            rows.append(judge_row(row, fmap, "harness", root, k2, points=points, check=check))
    return rows


def bundle_points(m: dict, name: str, problems: list[str], out: dict) -> dict | None:
    """Point file of a harness bundle (E-7); V-4 also runs the rev1 2 point-file check."""
    path = m.get("points_file")
    if not path:
        problems.append(f"E-7 {name}: points_file missing in the manifest")
        return None
    if name == "v4":
        chk = points_check(Path(path))
        out["points_check"] = chk
        if not chk["ok"]:
            problems.append(f"rev1 2 point file check failed: {chk['problems']}")
    else:
        out["points_file_sha256"] = sha256_file(Path(path))
    return load_point_file(Path(path))


def check_count(name: str, rows: list[dict], expect: dict, problems: list[str]) -> None:
    n = expect.get("count")
    if n is not None and len(rows) != n:
        problems.append(f"E-1 {name}: {len(rows)} rows, expected {n}")
    tags = expect.get("tags")
    if tags is not None:
        hist = tag_histogram(rows)
        if hist != tags:
            problems.append(f"E-6 {name}: tags {hist} != expected {tags}")


def recount(manifest: dict, expect: dict, fmap: dict, rules_dir: Path | None) -> dict:
    problems: list[str] = []
    out: dict = {"bundles": {}}
    if rules_dir is not None:
        out["rules_check"] = rules_check(rules_dir)
        if not out["rules_check"]["ok"]:
            problems.append("I-7 rules seal check failed")
    gates: dict = {}
    flags: list = []
    # V-2, V-4
    for b in ("v2", "v4"):
        if b not in manifest:
            problems.append(f"E-1 bundle {b} missing")
            continue
        m = manifest[b]
        info: dict = {}
        pts = bundle_points(m, b, problems, info)
        off = judge_files(m["off"], fmap, m.get("series_root"), True, pts, check=check_options_off)
        tcl = judge_files(m["tcl"], fmap, m.get("series_root"), True, pts, check=check_options_off)
        check_count(f"{b}.off", off, expect.get(b, {}).get("off", {}), problems)
        check_count(f"{b}.tcl", tcl, expect.get(b, {}).get("tcl", {}), problems)
        s_tcl = summarize(tcl)
        sh = shadow(off, tcl)
        out["bundles"][b] = {"off": summarize(off), "tcl": s_tcl, "shadow": sh,
                             "dhat_record": dhat_summary(off, tcl), **info}
        if b == "v2" and m.get("stored_off"):
            out["bundles"][b]["I4"] = off_invariance(off, m["stored_off"], fmap)
            if not out["bundles"][b]["I4"]["ok"]:
                problems.append("I-4 off-arm commands differ from the stored D8x rows")
        if s_tcl["not_judgeable"] or sh.get("not_judgeable"):
            problems.append(f"{b}: not judgeable rows / pairs")
        gates["G-A" if b == "v2" else "G-C"] = "pass" if s_tcl["fail"] == 0 else "fail"
        flags += [(b, f) for f in sh["flags"]]
    # V-3
    if "v3" in manifest:
        m = manifest["v3"]
        v3: dict = {}
        pts = bundle_points(m, "v3", problems, v3)
        g_b = "pass"
        for arm in V3_ARMS:
            if arm not in m["arms"]:
                problems.append(f"E-1 V-3 arm {arm} missing")
                continue
            a = m["arms"][arm]
            chk = (lambda row, arm=arm: check_v3_arm(row, arm))
            off = judge_files(a["off"], fmap, m.get("series_root"), True, pts, check=chk)
            tcl = judge_files(a["tcl"], fmap, m.get("series_root"), True, pts, check=chk)
            for side, rows in (("off", off), ("tcl", tcl)):
                if len(rows) != V3_PER_CELL:
                    problems.append(f"E-1 V-3 {arm}.{side}: {len(rows)} != {V3_PER_CELL}")
                ids = sorted({r["id"] for r in rows})
                if hashlib.sha256("\n".join(ids).encode()).hexdigest() != V3_KEYS_SHA256:
                    problems.append(f"E-5 V-3 {arm}.{side}: key list sha differs")
            v3_arm_check(a, fmap, arm, problems)
            sh = shadow(off, tcl, flag_enabled=arm in V3_JUDGED)
            s_tcl = summarize(tcl)
            v3[arm] = {"off": summarize(off), "tcl": s_tcl, "shadow": sh,
                       "off_J3_rows": sum(1 for r in off if r.get("values", {}).get("J3")),
                       "dhat_record": dhat_summary(off, tcl)}
            if arm in V3_JUDGED:
                if s_tcl["fail"]:
                    g_b = "fail"
                if s_tcl["not_judgeable"] or sh.get("not_judgeable"):
                    problems.append(f"V-3 {arm}: not judgeable rows / pairs")
                flags += [(f"v3.{arm}", f) for f in sh["flags"]]
        out["bundles"]["v3"] = v3
        gates["G-B"] = g_b
    else:
        problems.append("E-1 bundle v3 missing")
    # V-5 (rev2 1: raw outputs, absolute items on the K-2 arm, pass->fail vs the off arm)
    if "v5_raw" in manifest:
        out["bundles"]["v5"], gates["G-D"] = recount_v5_raw(manifest["v5_raw"], problems)
    else:
        problems.append("E-1 bundle v5_raw missing (path 2 reads the V-5 raw outputs, rev2 1)")
    # V-6
    if "v6" in manifest:
        out["bundles"]["v6"], g_e, f6 = recount_v6(manifest["v6"], expect.get("v6", {}), fmap, problems)
        gates["G-E"] = g_e
        flags += f6
    else:
        problems.append("E-1 bundle v6 missing")
    out["gates"] = gates
    out["flags"] = [{"bundle": b, "flag": f} for b, f in flags]
    out["branches"] = branches(out)
    out["problems"] = problems
    out["grade"] = grade(gates, flags, problems)
    return out


# ------------------------------------------------------------------ V-5 raw outputs (rev2 1 / 2)
def _doc(folder: Path, name: str):
    p = Path(folder) / name
    if not p.exists():
        raise NotJudgeable(f"V-5 output missing: {p}")
    if name.endswith(".jsonl"):
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    return json.loads(p.read_text(encoding="utf-8"))


def _err(r) -> bool:
    """rev4 1 (a): an error row has an ``error`` key with a non-empty value (``None`` = no error)."""
    return isinstance(r, dict) and r.get("error") not in (None, "", [], {}, False)


SGS_PREFIX = "lift_stroke_guard."
"""rev4 1 (b): the SGS settings compared on every noise row (other keys, e.g. the gyro noise of the level, differ
by design)."""


def _count(x) -> int | None:
    if isinstance(x, list):
        return len(x)
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return int(x)
    return None


class _Tally:
    """Absolute items of one bundle: failures and missing values (E-9: missing = fail)."""

    def __init__(self):
        self.fail: dict[str, list] = {}
        self.missing: dict[str, int] = {}

    def bad(self, item: str, what) -> None:
        self.fail.setdefault(item, []).append(what)

    def miss(self, item: str) -> None:
        self.missing[item] = self.missing.get(item, 0) + 1
        self.bad(item, "missing")

    def result(self) -> dict:
        return {"failures": {k: v[:40] for k, v in self.fail.items()},
                "failure_counts": {k: len(v) for k, v in self.fail.items()}, "missing": dict(self.missing),
                "absolute_pass": not self.fail}


def _event_rows(doc: dict) -> tuple[dict, list]:
    """``results[].runs[]`` rows keyed key|timing|event|offset|index (acc_judge.event_runs); errored results."""
    rows, errors = {}, []
    for res in doc.get("results", []):
        if _err(res):
            errors.append(str(res.get("key")))
            continue
        for i, run in enumerate(res.get("runs", [])):
            timing = res.get("timing", run.get("timing"))
            rows[f"{res['key']}|{timing}|{run.get('event')}|{run.get('offset_s')}|{i}"] = run
    return rows, errors


def _p2f(off: dict, tcl: dict, good=lambda v: v is True) -> tuple[list, list]:
    keys = set(off) & set(tcl)
    p2f = sorted(k for k in keys if good(off[k]) and not good(tcl[k]))
    return p2f, sorted(set(off) ^ set(tcl))


def _v5_grid(off_dir, tcl_dir) -> dict:
    t = _Tally()
    parts = {}
    for name in ("grid_r67_main.json", "grid_r67_top.json", "grid_r69_top.json", "grid_r69_bottom.json"):
        a, ea = _event_rows(_doc(tcl_dir, name))
        b, eb = _event_rows(_doc(off_dir, name))
        for e in ea:
            t.bad("error", f"{name}:{e}")
        for k, run in a.items():
            if "fault_periods" not in run:
                t.miss("fault_periods")
            elif run["fault_periods"]:
                t.bad("fault", f"{name}:{k}")
            if "pass" not in run:
                t.miss("pass")
        p2f, unm = _p2f({k: r.get("pass") for k, r in b.items()}, {k: r.get("pass") for k, r in a.items()})
        for k in p2f:
            t.bad("pass_to_fail", f"{name}:{k}")
        for k in unm:
            t.bad("unmatched", f"{name}:{k}")
        parts[name] = {"n_tcl": len(a), "n_off": len(b), "errors_off": len(eb)}
    return {"parts": parts, "n": sum(p["n_tcl"] for p in parts.values()), **t.result()}


def _v5_soil(off_dir, tcl_dir) -> dict:
    t = _Tally()
    a, ea = _event_rows(_doc(tcl_dir, "soil_A.json"))
    b, _ = _event_rows(_doc(off_dir, "soil_A.json"))
    a = {k: v for k, v in a.items() if k.split("|")[4] == "two" or "|two|" in k}
    b = {k: v for k, v in b.items() if k.split("|")[4] == "two" or "|two|" in k}
    for e in ea:
        if e.endswith("|two"):
            t.bad("error", e)
    if len(a) != V5_COUNTS["soil"]:
        t.bad("count", f"{len(a)} != {V5_COUNTS['soil']}")
    soft = {k for k in a if "|G1|" in k or "|J2|" in k}
    for k, run in a.items():
        if "pass" not in run:
            t.miss("pass")
        elif k in soft and not run["pass"]:
            t.bad("soft_failed", k)
        if "fault_periods" not in run:
            t.miss("fault_periods")
        elif run["fault_periods"]:
            t.bad("fault", k)
    rigid_a = {k: a[k].get("pass") for k in a if k not in soft}
    rigid_b = {k: b[k].get("pass") for k in b if not ("|G1|" in k or "|J2|" in k)}
    p2f, unm = _p2f(rigid_b, rigid_a)
    for k in p2f:
        t.bad("pass_to_fail", k)
    for k in sorted(set(a) ^ set(b)):
        t.bad("unmatched", k)
    return {"n": len(a), "soft_rows": len(soft), **t.result()}


def _v5_d8(off_dir, tcl_dir) -> dict:
    t = _Tally()
    runs = _doc(tcl_dir, "d8_both.json")["runs"]
    if len(runs) != V5_COUNTS["d8"]:
        t.bad("count", f"{len(runs)} != {V5_COUNTS['d8']}")
    for r in runs:
        rid = r.get("id")
        if _err(r):
            t.bad("error", rid)
            continue
        if "fails" not in r:
            t.miss("fails")
        elif r["fails"]:
            t.bad("fails", rid)
        if r.get("fault") is None:
            t.miss("fault")
        elif r["fault"]:
            t.bad("fault", rid)
        for key, ok in (("min_true_cyl_force_kN", lambda v: v >= D8_GUARD_KN),
                        ("ss_true_att_deg_maxabs", lambda v: v <= D8_ATT_DEG),
                        ("t_ready_s", lambda v: v <= D8_READY_S)):
            v = r.get(key)
            if not is_num(v):
                t.miss(key)
            elif not ok(v):
                t.bad(key, rid)
    off = {r["id"]: r for r in _doc(off_dir, "d8_both.json")["runs"] if not _err(r)}
    pairs = [(r, off[r["id"]]) for r in runs if not _err(r) and r.get("id") in off]
    rec = {}
    if pairs:
        d_ready = [a["t_ready_s"] - b["t_ready_s"] for a, b in pairs
                   if is_num(a.get("t_ready_s")) and is_num(b.get("t_ready_s"))]
        d_min = [a["min_true_cyl_force_kN"] - b["min_true_cyl_force_kN"] for a, b in pairs
                 if is_num(a.get("min_true_cyl_force_kN")) and is_num(b.get("min_true_cyl_force_kN"))]
        rec = {"ready_mean_delta_s": float(np.mean(d_ready)) if d_ready else None,
               "min_true_delta_kN_worst": min(d_min) if d_min else None}
    return {"n": len(runs), "record_vs_off": rec, **t.result()}


def _v5_noise(off_dir, tcl_dir) -> dict:
    t = _Tally()
    j = _doc(tcl_dir, "r79_L1L2_judgement.json")
    raw = _doc(tcl_dir, "r79_L1L2.json")
    rows = [r for r in j.get("runs", []) if r.get("level") == "L2"
            and not any(m in str(r.get("inner", "")) for m in S1_FRONT)]
    if len(rows) != V5_COUNTS["noise_L2"]:
        t.bad("count", f"{len(rows)} != {V5_COUNTS['noise_L2']}")
    k = 0
    for r in rows:
        if "pass" not in r:
            t.miss("pass")
            k += 1
        elif not r["pass"]:
            k += 1
    cp = cp_upper(k, len(rows)) if rows else None
    if cp is None or not (cp["pass"] and cp["agree"]):
        t.bad("cp_upper", cp)
    for key in ("unmatched", "errors"):
        c = _count(j.get(key))
        if c is None:
            t.miss(key)
        elif c:
            t.bad(key, c)
    ref = [x for x in j.get("reference", []) if x.get("group") == "all"]
    if len(ref) != 1 or not is_num(ref[0].get("false_loc")):
        t.miss("L1_false_loc")
    elif ref[0]["false_loc"]:
        t.bad("L1_false_loc", ref[0]["false_loc"])
    preset = (raw.get("meta") or {}).get("preset_settings")
    for res in raw.get("results", []):
        if _err(res):
            t.bad("error", res.get("key"))
            continue
        if preset is None or "controller_settings" not in res:
            t.miss("controller_settings")
        else:
            cs = res["controller_settings"]
            keys = {k for k in set(cs) | set(preset) if k.startswith(SGS_PREFIX)}
            if not keys:
                t.miss("sgs_settings")
            elif any(cs.get(k) != preset.get(k) for k in keys):
                t.bad("sgs_settings", f"{res.get('key')}|{res.get('level')}")
    old = {r["key"]: r.get("pass") for r in _doc(off_dir, "r79_L1L2_judgement.json").get("runs", [])}
    p2f = sorted(r["key"] for r in rows if old.get(r["key"]) is True and r.get("pass") is not True)
    return {"n": len(rows), "failures": k, "cp": cp, "record_pass_to_fail": p2f, **t.result()}


def _reg_verdicts(folder) -> tuple[dict, list, dict]:
    """Judged regression rows (key -> verdict) with the regression_keys.py key format, record keys, errors."""
    judged, errors = {}, []
    for name in ("clip_harness.json", "clip_p0.json"):
        for r in _doc(folder, name).get("records", []):
            if _err(r):
                errors.append(f"{name}:{r.get('id')}")
            judged[f"{name}:{r['id']}"] = r.get("verdict", r.get("pass"))
    for name in ("clip_x426_C.json", "clip_x426_D.json"):
        for r in _doc(folder, name).get("results", []):
            key = r.get("key", r.get("id", r.get("case_id")))
            if _err(r):
                errors.append(f"{name}:{key}")
            if isinstance(r.get("base"), dict) and "pass" in r["base"]:
                v = r["base"]["pass"]
            else:
                v = r.get("verdict", r.get("pass"))
            judged[f"{name}:{key}"] = v
    for res in _doc(folder, "clip_A.json").get("results", []):
        if _err(res):
            errors.append(f"clip_A.json:{res.get('key')}")
            continue
        for i, run in enumerate(res.get("runs", [])):
            judged[f"clip_A.json:{res['key']}#{i}"] = run.get("pass")
    jdoc = _doc(folder, "clip_r79_L1L2_judgement.json")
    jk = set()
    for r in jdoc.get("runs", []):
        judged[f"clip_r79_L1L2_judgement.json:{r['key']}"] = r.get("pass")
        jk.add(r["key"])
    record = [f"clip_r79_L1L2.json:{r['key']}|{r.get('level')}" for r in _doc(folder, "clip_r79_L1L2.json")["results"]
              if r["key"] not in jk]
    record += [f"clip_r79_L3L4.json:{r['key']}|{r.get('level')}" for r in _doc(folder, "clip_r79_L3L4.json")["results"]]
    return judged, errors, {"record": sorted(set(record)), "unmatched": _count(jdoc.get("unmatched")),
                            "errors": _count(jdoc.get("errors"))}


def _sha_list(xs) -> str:
    return hashlib.sha256("\n".join(sorted(xs)).encode("utf-8")).hexdigest()


def _v5_regression(off_dir, tcl_dir) -> dict:
    t = _Tally()
    a, ea, xa = _reg_verdicts(tcl_dir)
    b, _, xb = _reg_verdicts(off_dir)
    for side, verd, extra in (("tcl", a, xa), ("off", b, xb)):
        if _sha_list(verd) != REG_JUDGED_SHA256:
            t.bad("judged_keys_sha", side)
        if _sha_list(extra["record"]) != REG_RECORD_SHA256:
            t.bad("record_keys_sha", side)
    for e in ea:
        t.bad("error", e)
    if xa["errors"] is None:
        t.miss("r79_errors")
    elif xa["errors"]:
        t.bad("r79_errors", xa["errors"])
    # rev4 1 (c): the r79 judgement 'unmatched' is a record here (criteria.md regression row: pass->fail only)
    for k, v in a.items():
        if v is None:
            t.miss("verdict")
    p2f, unm = _p2f(b, a, good=lambda v: v in GOOD_VERDICTS)
    for k in p2f:
        t.bad("pass_to_fail", k)
    for k in unm:
        t.bad("unmatched", k)
    return {"n": len(a), "record_n": len(xa["record"]), "record_r79_unmatched": xa["unmatched"], **t.result()}


def _v5_ps7(off_dir, tcl_dir) -> dict:
    t = _Tally()
    a, b = _doc(tcl_dir, "ps7.json"), _doc(off_dir, "ps7.json")
    if len(a) != V5_COUNTS["ps7"]:
        t.bad("count", f"{len(a)} != {V5_COUNTS['ps7']}")
    for r in a:
        if _err(r):
            t.bad("error", r.get("key"))
        if "pass" not in r:
            t.miss("pass")
    p2f, unm = _p2f({r["key"]: r.get("pass") for r in b}, {r["key"]: r.get("pass") for r in a})
    for k in p2f:
        t.bad("pass_to_fail", k)
    for k in unm:
        t.bad("unmatched", k)
    return {"n": len(a), **t.result()}


def _g8_rows(folder) -> dict:
    rows = {}
    for name in ("g8_jobs1.jsonl", "g8_jobs3.jsonl", "g8_jobs5.jsonl"):
        for r in _doc(folder, name):
            rows[f"{r.get('tag')}|{r.get('key')}"] = r
    return rows


def _g8_faults(r) -> set:
    names = r.get("warn_fault") or []
    return {prefix(str(n)) for n in names if str(n).startswith("FAULT_")}


def _v5_g8(off_dir, tcl_dir) -> dict:
    t = _Tally()
    a, b = _g8_rows(tcl_dir), _g8_rows(off_dir)
    if len(a) != V5_COUNTS["g8_safe_stop"]:
        t.bad("count", f"{len(a)} != {V5_COUNTS['g8_safe_stop']}")
    for k, r in a.items():
        if _err(r):
            t.bad("error", k)
            continue
        if k not in b:
            t.bad("unmatched", k)
            continue
        o = b[k]
        if "final" not in r or "final" not in o:
            t.miss("final")
        elif o["final"] == "ready" and r["final"] != "ready":
            t.bad("ready_lost", k)
        new = _g8_faults(r) - _g8_faults(o)
        if new:
            t.bad("new_fault", f"{k}:{sorted(new)}")
        if "pass" in r and "pass" in o and o["pass"] is True and r["pass"] is not True:
            t.bad("pass_to_fail", k)
    for k in sorted(set(b) - set(a)):
        t.bad("unmatched", k)
    return {"n": len(a), **t.result()}


V5_BUNDLE_FUNCS = {"grid": _v5_grid, "soil": _v5_soil, "d8": _v5_d8, "noise_L2": _v5_noise,
                   "regression": _v5_regression, "ps7": _v5_ps7, "g8_safe_stop": _v5_g8}
V5_EVENT_FILES = (("r79_L1L2.json", "results"), ("clip_r79_L1L2.json", "results"), ("clip_r79_L3L4.json", "results"),
                  ("ps7.json", None))


V5_PROVENANCE_STEPS = ("reg1", "reg2", "reg3", "reg4", "reg5", "reg6", "reg7", "grid_r67_main", "grid_r67_top",
                       "grid_r69_top", "grid_r69_bottom", "soil_A", "noise_L1L2", "ps7")
"""rev5 1: one ``provenance/<step>.json`` per step; d8 takes ``d8_both.json`` meta, G8 the rev5 2 check."""
RUN_HEAD_FULL = "6a44ff81d25aea1fa162daf9b14c23b99beb9db0"
G8_SIDECARS = ("g8_jobs1.launch.json", "g8_jobs3.launch.json", "g8_jobs5.launch.json")


def _v5_common(m: dict, arms: dict) -> dict:
    """rev2 1 / rev5 common items and the K-2 evidence: sidecar rc (run + r79 judge steps, not flatten),
    provenance per step (d8 from its meta), the G8 c2.py check (rev5 2), event rows, G8 row fields."""
    t = _Tally()
    c2 = m.get("c2_sha256", C2_SHA256_RUN)
    run_head = m.get("run_head", RUN_HEAD_FULL)
    run_wt = m.get("run_wt")
    if not run_wt or not (Path(run_wt) / "03_src/outrigger_sim/control/c2.py").exists():
        t.miss("run_wt_c2")
    elif sha256_file(Path(run_wt) / "03_src/outrigger_sim/control/c2.py") != c2:
        t.bad("run_wt_c2_sha256", "k2-run c2.py differs")
    for arm, folder in arms.items():
        sidecars = {}
        for sc in m.get("sidecars", {}).get(arm, []):
            p = Path(sc)
            if p.name.startswith("flatten"):  # rev5 3: not a path 2 input
                continue
            if not p.exists():
                t.miss("sidecar")
                continue
            doc = json.loads(p.read_text(encoding="utf-8"))
            sidecars[p.name] = doc
            if doc.get("rc") != 0:
                t.bad("sidecar_rc", f"{arm}:{p.name}={doc.get('rc')}")
        for name in G8_SIDECARS:  # rev5 2: G8 c2.py = the RUN_HEAD file
            doc = sidecars.get(name)
            if doc is None:
                t.miss("g8_sidecar")
                continue
            for side in ("git_start", "git_end"):
                g = doc.get(side) or {}
                if g.get("head") != run_head or g.get("is_clean") is not True:
                    t.bad("g8_git", f"{arm}:{name}:{side}")
        provs = {}
        for step in V5_PROVENANCE_STEPS:
            p = Path(folder) / "provenance" / f"{step}.json"
            if not p.exists():
                t.miss("provenance")
                continue
            provs[p.name] = json.loads(p.read_text(encoding="utf-8"))
        d8 = Path(folder) / "d8_both.json"
        if d8.exists():
            provs["d8_both.json:meta"] = json.loads(d8.read_text(encoding="utf-8")).get("meta") or {}
        else:
            t.miss("provenance")
        for pname, d in provs.items():
            p = Path(pname)
            if d.get("c2_sha256") != c2:
                t.bad("c2_sha256", f"{arm}:{p.name}")
            if d.get("combo") != "preset":
                t.bad("combo", f"{arm}:{p.name}={d.get('combo')}")
            if d.get("k2") != ("on" if arm == "tcl" else "off"):
                t.bad("k2", f"{arm}:{p.name}={d.get('k2')}")
            if d.get("touch_creep_latch") is not (arm == "tcl"):
                t.bad("touch_creep_latch", f"{arm}:{p.name}")
            if str(d.get("controller_tag", "")).endswith(TCL_SUFFIX) is not (arm == "tcl"):
                t.bad("controller_tag", f"{arm}:{p.name}={d.get('controller_tag')}")
        for name, key in V5_EVENT_FILES:
            p = Path(folder) / name
            if not p.exists():
                t.miss(f"events:{name}")
                continue
            doc = json.loads(p.read_text(encoding="utf-8"))
            rows = doc if key is None else doc.get(key, [])
            latch = creep = 0
            for r in rows:
                names = [n for _, n in event_pairs(r.get("events") or [])]
                latch += any(prefix(n) == LATCH_EVENT for n in names)
                creep += any(n.startswith("INFO_TOUCH_CREEP_") for n in names)
            if arm == "tcl" and latch == 0:
                t.bad("k2_evidence", f"tcl:{name} no INFO_TOUCH_CREEP_LATCH row")
            if arm == "off" and creep:
                t.bad("k2_evidence", f"off:{name} {creep} INFO_TOUCH_CREEP_* rows")
        try:
            g8 = _g8_rows(folder)
        except NotJudgeable:
            t.miss("events:g8")
            g8 = {}
        for r in g8.values():  # rev5 2: G8 K-2 evidence from the row fields, not events
            if r.get("touch_creep_latch") is not (arm == "tcl"):
                t.bad("g8_touch_creep_latch", f"{arm}:{r.get('tag')}|{r.get('key')}")
            if str(r.get("controller_tag", "")).endswith(TCL_SUFFIX) is not (arm == "tcl"):
                t.bad("g8_controller_tag", f"{arm}:{r.get('tag')}|{r.get('key')}")
    return t.result()


def recount_v5_raw(m: dict, problems: list[str]) -> tuple[dict, str]:
    """V-5 from the raw step outputs of the two arm folders (rev2 1): absolute items on the K-2 arm, pass->fail
    vs the off arm; G-D fails when any bundle fails; missing inputs make the bundle not judgeable."""
    arms = {"off": Path(m["off"]), "tcl": Path(m["tcl"])}
    out = {}
    g_d = "pass"
    try:
        out["common"] = _v5_common(m, arms)
        if not out["common"]["absolute_pass"]:
            g_d = "fail"
    except (OSError, ValueError, KeyError, NotJudgeable) as exc:
        problems.append(f"V-5 common: {exc}")
    for name, func in V5_BUNDLE_FUNCS.items():
        try:
            res = func(arms["off"], arms["tcl"])
        except (OSError, ValueError, KeyError, NotJudgeable) as exc:
            problems.append(f"V-5 {name} not judgeable: {exc}")
            out[name] = {"not_judgeable": str(exc)}
            continue
        if not res["absolute_pass"]:
            g_d = "fail"
        out[name] = res
    out["missing_total"] = sum(sum((v.get("missing") or {}).values()) for v in out.values() if isinstance(v, dict))
    return out, g_d


def v3_arm_check(a: dict, fmap: dict, arm: str, problems: list[str]) -> None:
    """E-5 / I-9: aug arm label and KPlant flag on every V-3 row."""
    f = fmap["harness_row"]
    for side in ("off", "tcl"):
        for p in a[side]:
            for row in load_rows(Path(p)):
                if get_path(row, f["aug_arm"], required=False) != arm:
                    problems.append(f"E-5 V-3 {arm}.{side}: aug_arm differs in {p}")
                    return
                if get_path(row, f["is_kplant"], required=False) is not True:
                    problems.append(f"I-9 V-3 {arm}.{side}: KPlant flag not true in {p}")
                    return


def off_invariance(off: list[dict], stored_files: list[str], fmap: dict) -> dict:
    stored = {}
    f = fmap["harness_row"]
    for p in stored_files:
        for row in load_rows(Path(p)):
            stored[(row[f["id"].split(".")[0]], bool(row.get("k1_order_gate")))] = row.get("commands_sha256")
    diff = [r["id"] for r in off if stored.get((r["id"], r["k1"])) != r.get("commands_sha256")]
    return {"n": len(off), "stored": len(stored), "differ": diff[:20], "n_differ": len(diff),
            "ok": not diff and len(stored) == len(off)}


def recount_v6(m: dict, expect: dict, fmap: dict, problems: list[str]):
    """V-6 Chrono 8 rows: K-2 rows judged, off rows recorded, 5.4 predictions and branch."""
    rows = {}
    for name, spec in m["rows"].items():
        row = json.loads(Path(spec["row_json"]).read_text(encoding="utf-8"))
        if "path" in spec:
            row = get_path(row, spec["path"])
        files = {"pads": spec["pads_npz"], "rate": spec.get("rate_npz")}
        floors = [v for k, v in V6_FLOORS_DEG.items() if f"_{k}_" in name]
        if len(floors) != 1:
            problems.append(f"E-7 V-6 {name}: floor not identified from the row name")
        r = judge_row(row, fmap, "chrono", None, True, files,
                      floor_deg=floors[0] if len(floors) == 1 else None,
                      check=lambda rw, eng=spec["engine"]: check_v6_row(rw, eng))
        r["engine"], r["arm"] = spec["engine"], spec["arm"]
        r["base"] = name.rsplit("_", 1)[0]
        exp = expect.get("rows", {}).get(name)
        if exp is None:
            problems.append(f"E-1 V-6 row {name} not expected")
        else:
            if r.get("tag") != exp.get("tag"):
                problems.append(f"I-10 V-6 {name}: tag {r.get('tag')} != {exp.get('tag')}")
            if r.get("k1") is not False:
                problems.append(f"I-10 V-6 {name}: K1 not off")
        if spec["arm"] == "tcl" and spec["engine"] == "L2b":
            r["items"]["V6_false_latch"] = not r.get("false_latch")
            r["items"]["V6_cap"] = r.get("cap_events", 0) == 0
            r["fail_items"] = sorted(k for k, ok in r["items"].items() if not ok)
        rows[name] = r
    missing = sorted(set(expect.get("rows", {})) - set(rows))
    if missing:
        problems.append(f"E-1 V-6 rows missing {missing}")
    judged = [r for r in rows.values() if r["arm"] == "tcl"]
    if any(row_status(r) == "not_judgeable" for r in judged):
        problems.append("V-6 K-2 row not judgeable")
    g_e = "pass" if all(row_status(r) == "pass" for r in judged) and len(judged) == 4 else "fail"
    sh6 = v6_shadow(rows)
    flags = [("v6", f) for f in sh6["flags"]]
    l1_off = [r for r in rows.values() if r["engine"] == "L1" and r["arm"] == "off"]
    j3_off = [r["values"].get("J3") for r in l1_off]
    branch = ("no_gain_shown" if l1_off and all(v == 0 for v in j3_off)
              else "paired_evidence" if any(is_num(v) and v > 0 for v in j3_off) else "unknown")
    off6 = [{**r, "id": r["base"], "k1": None} for r in rows.values() if r["arm"] == "off"]
    tcl6 = [{**r, "id": r["base"], "k1": None} for r in rows.values() if r["arm"] == "tcl"]
    return {"rows": rows, "chrono_branch": branch, "predictions": predictions(rows), "shadow": sh6,
            "dhat_record": dhat_summary(off6, tcl6)}, g_e, flags


def v6_shadow(rows: dict) -> dict:
    """rev2 3: SH-1 .. SH-6 of the V-6 bundle (4 pairs by base name); a missing value is a FLAG and counted."""
    tcl = [r for r in rows.values() if r["arm"] == "tcl"]
    off = [r for r in rows.values() if r["arm"] == "off"]
    pairs = {r["base"]: [None, None] for r in rows.values()}
    for r in rows.values():
        pairs[r["base"]][0 if r["arm"] == "off" else 1] = r
    flags, missing = set(), {}

    def miss(item):
        missing[item] = missing.get(item, 0) + 1
        flags.add(item)

    sh1_rows = []
    for r in tcl:
        sh1 = (r.get("metrics") or {}).get("SH1_post_latch_lift")
        if sh1 is None:
            miss("SH-1")
        elif any(v > 0 for v in sh1.values()):
            sh1_rows.append(r["id"])
            flags.add("SH-1")

    def amps(side):
        vals = [(r.get("metrics") or {}).get("SH2_rate_amp_deg_s") for r in side]
        return [v for v in vals if is_num(v)]
    a_off, a_tcl = amps(off), amps(tcl)
    med_off = float(np.median(a_off)) if len(a_off) == 4 else None
    med_tcl = float(np.median(a_tcl)) if len(a_tcl) == 4 else None
    if med_off is None or med_tcl is None:
        miss("SH-2")
    elif med_tcl > med_off:
        flags.add("SH-2")
    d_ready = {}
    for base, (o, k) in pairs.items():
        a = None if k is None else k["values"].get("t_ready_s")
        b = None if o is None else o["values"].get("t_ready_s")
        if not (is_num(a) and is_num(b)):
            miss("SH-3")
            continue
        d_ready[base] = a - b
        if a - b > SH3_READY_S:
            flags.add("SH-3")
    j_off = [r["values"].get("J1_N") for r in off]
    j_tcl = [r["values"].get("J1_N") for r in tcl]
    sh4 = None
    if len(j_off) != 4 or len(j_tcl) != 4 or not all(is_num(v) for v in j_off + j_tcl):
        miss("SH-4")
    else:
        sh4 = min(j_tcl) - min(j_off)
        if sh4 < SH4_EROSION_N:
            flags.add("SH-4")
    caps = sum(int(r.get("cap_events") or 0) for r in tcl)
    l1_false = sum(len(r.get("false_latch") or []) for r in tcl if r["engine"] == "L1")
    if any(r["engine"] == "L1" and r.get("false_latch") is None for r in tcl):
        miss("SH-5")
    if caps + l1_false > 0:
        flags.add("SH-5")
    near = []
    for r in tcl:
        v = r["values"]
        if not is_num(v.get("J1_N")):
            miss("SH-6")
        for name in ("J1_N", "J2_N"):
            if is_num(v.get(name)) and v[name] < F_D8_N + SH6_MARGIN_N:
                near.append((r["id"], name, v[name]))
                flags.add("SH-6")
    return {"flags": sorted(flags), "missing": missing, "SH1_rows": sh1_rows, "SH2_median_off": med_off,
            "SH2_median_tcl": med_tcl, "SH3_delta_s": d_ready, "SH4_delta_N": sh4, "SH5_caps": caps,
            "SH5_l1_false_latch": l1_false, "SH6_rows": near}


def predictions(rows: dict) -> list[dict]:
    """Rules 5.4 sealed predictions: inside / outside, recorded only."""
    out = []

    def add(name, what, value, lo, hi):
        ok = None if value is None else (lo <= value <= hi)
        out.append({"row": name, "item": what, "value": value, "range": [lo, hi], "inside": ok})

    pair = {}
    for name, r in rows.items():
        pair.setdefault((r["engine"], name.replace("_tcl", "").replace("_off", "")), {})[r["arm"]] = r
    for name, r in rows.items():
        v = r["values"]
        mn = (r.get("metrics") or {}).get("J3_min_N_series")
        if r["engine"] == "L1" and r["arm"] == "off":
            add(name, "J3", v.get("J3"), 0, 150)
            add(name, "min pad N", mn, 0.0, 50e3)
        elif r["engine"] == "L1":
            add(name, "J3", v.get("J3"), 0, 0)
            add(name, "min pad N", mn, 0.0, 25e3)
            add(name, "cap", r.get("cap_events"), 0, 0)
        else:
            add(name, "J3", v.get("J3"), 0, 0)
            add(name, "min pad N", mn, 40e3, math.inf)
            if r["arm"] == "tcl":
                add(name, "false latch", len(r.get("false_latch") or []), 0, 0)
                add(name, "cap", r.get("cap_events"), 0, 0)
    for (engine, base), p in pair.items():
        if engine == "L1" and "off" in p and "tcl" in p:
            def d(key, p=p):
                a, b = p["tcl"]["values"].get(key), p["off"]["values"].get(key)
                return a - b if is_num(a) and is_num(b) else None
            add(base, "TOUCH end shift s", d("t_touch_s"), -0.5, 2.0)
            add(base, "READY shift s", d("t_ready_s"), -1.5, 1.5)
            add(base, "J1 shift N", d("J1_N"), -5e3, 5e3)
    return out


def branches(out: dict) -> list[str]:
    g = out["gates"]
    b = []
    if g.get("G-C") == "fail":
        b.append("B-1")
    if g.get("G-A") == "fail":
        b.append("B-2")
    v3 = out["bundles"].get("v3", {})
    if v3 and all(v3.get(a, {}).get("off_J3_rows", 1) == 0 for a in V3_B3_ARMS):
        b.append("B-3")
    if g.get("G-B") == "fail":
        b.append("B-4")
    if g.get("G-E") == "fail":
        b.append("B-5")
    if g.get("G-D") == "fail":
        b.append("B-6")
    crc2 = v3.get("AUG_crc2", {}).get("tcl", {})
    if crc2.get("fail"):
        b.append("B-7")
    return b


def grade(gates: dict, flags: list, problems: list[str]) -> str:
    """Rules 10 (G-F, two paths and the post audit, is outside this tool: grade is provisional)."""
    if problems:
        return "not_judgeable"
    if any(gates.get(g) == "fail" for g in ("G-B", "G-C", "G-D", "G-E")):
        return "fail"
    if gates.get("G-A") == "fail":
        return "conditional_range_limited"
    if flags:
        return "conditional"
    return "pass"


def rules_check(rules_dir: Path) -> dict:
    rules = Path(rules_dir) / RULES_FILE
    seal = Path(rules_dir) / RULES_SEAL
    dyn = Path(rules_dir) / DYN_SPEC_FILE
    res = {"rules_sha256": sha256_file(rules) if rules.exists() else None,
           "seal_first_token": seal.read_text(encoding="utf-8").split()[0] if seal.exists() else None,
           "dyn_spec_sha256": sha256_file(dyn) if dyn.exists() else None}
    ok = res["rules_sha256"] == RULES_SHA256 == res["seal_first_token"] and res["dyn_spec_sha256"] == DYN_SPEC_SHA256
    for tag, fname, sname, want in (("rev1", REV1_FILE, REV1_SEAL, REV1_SHA256), ("rev2", REV2_FILE, REV2_SEAL, REV2_SHA256),
                                    ("rev3", REV3_FILE, REV3_SEAL, REV3_SHA256),
                                    ("rev4", REV4_FILE, REV4_SEAL, REV4_SHA256),
                                    ("rev5", REV5_FILE, REV5_SEAL, REV5_SHA256)):
        f, s = Path(rules_dir) / fname, Path(rules_dir) / sname
        res[f"{tag}_sha256"] = sha256_file(f) if f.exists() else None
        res[f"{tag}_seal_first_token"] = s.read_text(encoding="utf-8").split()[0] if s.exists() else None
        ok = ok and res[f"{tag}_sha256"] == want == res[f"{tag}_seal_first_token"]
    res["ok"] = ok
    return res


# ------------------------------------------------------------------ expect template
def expect_template() -> dict:
    """Counts and tags from the rules (3, 1.2). Review and freeze in the pre-launch record."""
    v2_off = {"final_C4G2_LAS": 910, "final_C4G2_LAS_K1": 192}
    v2_tcl = {"final_C4G2_LAS_TCL": 910, "final_C4G2_LAS_K1_TCL": 192}
    v6 = {}
    for floor in ("fdown3.5", "k2pp025"):
        for arm, tag in (("off", "final_C4G2_LAS"), ("tcl", "final_C4G2_LAS_TCL")):
            v6[f"K2_L1_top_{floor}_Fs0_{arm}"] = {"engine": "L1", "arm": arm, "tag": tag}
            v6[f"K2_L2b_top_{floor}_Fs4_{arm}"] = {"engine": "L2b", "arm": arm, "tag": tag}
    return {
        "v2": {"off": {"count": 1102, "tags": v2_off}, "tcl": {"count": 1102, "tags": v2_tcl}},
        "v3": {"keys_sha256": V3_KEYS_SHA256, "arms": list(V3_ARMS), "per_cell": V3_PER_CELL},
        "v4": {"off": {"count": 596, "tags": {"final_C4G2_LAS": 596}},
               "tcl": {"count": 596, "tags": {"final_C4G2_LAS_TCL": 596}}},
        "v5": {"noise_L2": {"count": 855}, "grid": {"count": 768}, "d8": {"count": 576},
               "soil": {"count": 60}, "regression": {"count": 118}, "ps7": {"count": 20},
               "g8_safe_stop": {"count": None}},
        "v6": {"rows": v6},
        "note": "v5 counts are the rule table values; g8_safe_stop count is fixed in the pre-launch record",
    }


# ------------------------------------------------------------------ selftests
def selftest_d8x(ra_off: Path, ra_on: Path, points_file: Path | None = None) -> dict:
    """Stored D8x R-a rows (no K-2 fields): J items must give 68 (K1 off) + 6 (K1 on), J3 only.
    With ``points_file`` (``d8x_points.json``) E-7 is checked on every row as well."""
    fmap = copy.deepcopy(DEFAULT_FIELDS)
    pts = load_point_file(points_file) if points_file else None
    res = {"E7_checked": pts is not None}
    total = 0
    for name, path, expected in (("off", ra_off, 68), ("on", ra_on, 6)):
        rows = [judge_row(r, fmap, "harness", None, False, points=pts) for r in load_rows(path)]
        s = summarize(rows)
        only_j3 = all(r["fail_items"] == ["J3"] for r in rows if row_status(r) == "fail")
        res[name] = {"n": s["n"], "fail": s["fail"], "not_judgeable": s["not_judgeable"],
                     "expected_fail": expected, "fail_items_only_J3": only_j3,
                     "ok": s["fail"] == expected and only_j3 and s["not_judgeable"] == 0}
        total += s["fail"]
    res["total_fail"] = total
    res["ok"] = res["off"]["ok"] and res["on"]["ok"] and total == 74
    return res


STORED_V5 = {
    "grid_r67_main.json": "grid/grid_r67_main.json", "grid_r67_top.json": "grid/grid_r67_top.json",
    "grid_r69_top.json": "grid/grid_r69_top.json", "grid_r69_bottom.json": "grid/grid_r69_bottom.json",
    "soil_A.json": "soil/soil_A.json", "d8_both.json": "d8/d8_both.json", "r79_L1L2.json": "noise/r79_L1L2.json",
    "r79_L1L2_judgement.json": "noise/r79_L1L2_judgement.json", "g8_jobs1.jsonl": "g8_safe_stop/out1.jsonl",
    "g8_jobs3.jsonl": "g8_safe_stop/out3.jsonl", "g8_jobs5.jsonl": "g8_safe_stop/out5.jsonl",
    **{n: f"regression/{n}" for n in ("clip_harness.json", "clip_p0.json", "clip_x426_C.json", "clip_x426_D.json",
                                     "clip_A.json", "clip_r79_L1L2.json", "clip_r79_L1L2_judgement.json",
                                     "clip_r79_L3L4.json")}}


def selftest_v5_stored(acc: Path, ps7: Path) -> dict:
    """rev4 2: the V-5 bundle functions on the stored final-controller acceptance outputs, the same files as both
    arms (format check; every bundle must pass its absolute items, as in the accepted judgement)."""
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        arm = Path(tmp)
        for name, rel in STORED_V5.items():
            shutil.copyfile(Path(acc) / rel, arm / name)
        shutil.copyfile(ps7, arm / "ps7.json")
        res = {}
        for name, func in V5_BUNDLE_FUNCS.items():
            r = func(arm, arm)
            res[name] = {"n": r.get("n"), "absolute_pass": r["absolute_pass"], "failure_counts": r["failure_counts"],
                         "missing": r["missing"]}
    want_n = {"grid": 768, **V5_COUNTS}
    ok = all(v["absolute_pass"] and v["n"] == want_n[k] for k, v in res.items())
    return {"bundles": res, "ok": ok}


def selftest_screen(screen_dir: Path) -> dict:
    """The 44 design-screen rows: counts, VC J3 / cap, SH-3 and SH-4 on the V0 / VC pairs."""
    rows = []
    for run in ("smoke", "run1", "run2a", "run2b"):
        p = Path(screen_dir) / f"j3ctrl_{run}_variants.json"
        rows += json.loads(p.read_text(encoding="utf-8"))
    by = {}
    for r in rows:
        by.setdefault(r["variant"], {})[r["id"]] = r
    vc = by.get("VC", {})
    v0 = by.get("V0", {})
    keys = sorted(set(vc) & set(v0))
    d_ready = {k: vc[k]["t_ready_s"] - v0[k]["t_ready_s"] for k in keys}
    min_off = min(v0[k]["min_true_cyl_force_kN"] for k in keys) if keys else None
    min_tcl = min(vc[k]["min_true_cyl_force_kN"] for k in keys) if keys else None
    res = {"rows": len(rows), "variants": {v: len(m) for v, m in sorted(by.items())},
           "VC_J3_zero": sum(1 for r in vc.values() if r["J3_stored_def"] == 0),
           "VC_cap_latch": sum(1 for r in vc.values() if any(r.get("creep_cap_latch") or [])),
           "pairs_V0_VC": keys, "SH3_delta_s": d_ready,
           "SH4_min_off_kN": min_off, "SH4_min_tcl_kN": min_tcl,
           "SH4_delta_kN": None if min_off is None else min_tcl - min_off}
    res["ok"] = (res["rows"] == 44 and len(vc) == 8 and res["VC_J3_zero"] == 8
                 and res["VC_cap_latch"] == 0 and len(keys) == 4
                 and abs(res["SH4_delta_kN"] - 3.83) < 1e-9)
    return res


# ------------------------------------------------------------------ CLI
def to_md(obj: dict) -> str:
    lines = [f"# {TOOL} {VERSION}", ""]
    for key in ("grade", "gates", "branches", "problems", "flags", "ok"):
        if key in obj:
            lines.append(f"- {key}: `{json.dumps(obj[key], default=str)}`")
    lines += ["", "```json", json.dumps(obj, indent=1, default=str)[:200000], "```"]
    return "\n".join(lines) + "\n"


def write_out(obj: dict, out: Path, fmt: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    text = to_md(obj) if fmt == "md" else json.dumps(obj, indent=1, default=str)
    out.write_bytes(text.encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog=TOOL)
    sub = ap.add_subparsers(dest="cmd", required=True)
    rc = sub.add_parser("recount")
    rc.add_argument("--manifest", required=True)
    rc.add_argument("--expect", required=True)
    rc.add_argument("--fields")
    rc.add_argument("--rules-dir")
    et = sub.add_parser("expect-template")
    sd = sub.add_parser("selftest-d8x")
    sd.add_argument("--ra-off", required=True)
    sd.add_argument("--ra-on", required=True)
    sd.add_argument("--points")
    ss = sub.add_parser("selftest-screen")
    ss.add_argument("--screen-dir", required=True)
    pc = sub.add_parser("points-check")
    pc.add_argument("--points", required=True)
    sv = sub.add_parser("selftest-v5-stored")
    sv.add_argument("--acc", required=True, help="touch_phase/acceptance folder")
    sv.add_argument("--ps7", required=True, help="stored touch_phase/ps7_E.json")
    for p in (rc, et, sd, ss, pc, sv):
        p.add_argument("--out", required=True)
        p.add_argument("--format", choices=("json", "md"), default="json")
    args = ap.parse_args(argv)
    head = {"tool": TOOL, "version": VERSION, "tool_sha256": sha256_file(Path(__file__)),
            "cmd": args.cmd}
    try:
        if args.cmd == "expect-template":
            obj, code = {**head, "expect": expect_template()}, 0
        elif args.cmd == "selftest-d8x":
            r = selftest_d8x(Path(args.ra_off), Path(args.ra_on),
                             Path(args.points) if args.points else None)
            obj = {**head, "inputs": {"ra_off": sha256_file(Path(args.ra_off)),
                                      "ra_on": sha256_file(Path(args.ra_on))}, **r}
            code = 0 if r["ok"] else 1
        elif args.cmd == "selftest-v5-stored":
            r = selftest_v5_stored(Path(args.acc), Path(args.ps7))
            obj, code = {**head, **r}, 0 if r["ok"] else 1
        elif args.cmd == "points-check":
            r = points_check(Path(args.points))
            obj, code = {**head, **r}, 0 if r["ok"] else 2
        elif args.cmd == "selftest-screen":
            r = selftest_screen(Path(args.screen_dir))
            obj, code = {**head, **r}, 0 if r["ok"] else 1
        else:
            fmap = copy.deepcopy(DEFAULT_FIELDS)
            head["fields_sha256"] = None
            if args.fields:
                head["fields_sha256"] = sha256_file(Path(args.fields))
                for section, vals in json.loads(Path(args.fields).read_text(encoding="utf-8")).items():
                    fmap.setdefault(section, {}).update(vals)
            manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
            expect = json.loads(Path(args.expect).read_text(encoding="utf-8"))
            head["manifest_sha256"] = sha256_file(Path(args.manifest))
            head["expect_sha256"] = sha256_file(Path(args.expect))
            r = recount(manifest, expect, fmap, Path(args.rules_dir) if args.rules_dir else None)
            obj = {**head, **r}
            code = 2 if r["grade"] == "not_judgeable" else (1 if r["grade"] == "fail" else 0)
    except NotJudgeable as exc:
        obj, code = {**head, "error": f"not judgeable: {exc}"}, 2
    except (OSError, ValueError, KeyError) as exc:
        obj, code = {**head, "error": f"input error: {exc!r}"}, 2
    except Exception as exc:  # noqa: BLE001 - exit 3 contract
        obj, code = {**head, "error": f"internal: {exc!r}", "traceback": traceback.format_exc()}, 3
    write_out(obj, Path(args.out), args.format)
    summary = {k: obj.get(k) for k in ("cmd", "ok", "grade", "gates", "error") if k in obj}
    summary["exit"] = code
    summary["out"] = str(args.out)
    print(json.dumps(summary, default=str))
    return code


if __name__ == "__main__":
    sys.exit(main())
