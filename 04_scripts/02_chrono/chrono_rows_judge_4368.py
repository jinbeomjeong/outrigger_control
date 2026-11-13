"""436.8 Chrono path 1 aggregation, new version (rules rev5 R5-A1; cad-expert 2026-11-13).

Reads the judgement blocks and series a 436.8 Chrono row wrote (``run_S9.py level`` SCM rows, ``run_S8C.py`` L2b rows,
``run_S6C.py`` L1-R rows) and re-decides the items of rules rev3 R3-G3 / G4 / G5 (D8) / G6 / G8 / G10 with the rev3 /
rev4 definitions. The runners and the earlier judge functions (``r76_g6_chrono_judge.py``, ``verify/s8_control.py`` C1
row, ``verify/s6_control.py`` ``_times``) are not changed; their differences are listed in
``chrono_rows_judge_4368_README.md`` and in the output ``disclosure`` block (``git diff --no-index --numstat``).

Items (alignment table ``06_analysis/02_control/verif_matrix/v5_resume_4368/chrono_path1_rev3_alignment.md`` 3 =
rules rev6 R6-A D-26 .. D-39):

* D-26 (N-1) :func:`sgs_class` - spec 427.9 soil-guard safe stop -> ``stroke_limited_stop`` (allowed stop), S-01..04.
* D-27 / D-28 (N-2 / N-3) :func:`ready_items` - P3-6 FLAG (record), READY <= 120 s + 1e-9 (G6 gate).
* D-29 (N-4) :func:`d8_lift_time` - D8 t_lift = first 1 ms sample, phase not idle / check / touch, crawler normal <= 0.
* D-30 (N-5) SCM t_lift (same function on ``step_series.npz``); L1-R 10 Hz bracket t_b / t_a (R6-B1).
* D-31 / D-39 (N-6 / N-14) :func:`c1_block` - R40-1 / R40-2 on the D-29 t_lift with the S8-A2 judged force; hold =
  ``not_judgeable`` (resolution with the L1 pair is a person's step: values only, ``stop``).
* D-32 (N-7) :func:`moving_pressure` - moving = |u_applied| > 1e-9 m/s on the 10 Hz control rows, p = F_cyl / A_p.
* D-33 (N-8) :func:`lift_samples` - pad normal <= 0 (Q-14).
* D-34 / D-35 (N-9 / N-10) :func:`p38_block` - P3-8 window end min(first LOC, first soil mode); 377 (first LOC + 1 s)
  -> ``P3-8_demoted``, else U-S9-G6c ``P3-8_preloc_loss`` (G6-3 true, no FAULT), both in ``demoted_items``.
* D-36 (N-11) :func:`recontact_events` - duration = samples x 1 ms.
* D-37 / D-38 (N-12 / N-13) :func:`p32_block` - strict LOC < first DONE, loaded = > 0.01 W, revoked-LOC normal.
* R5-B1 / R6-B6 / R6-B7 / R6-1 :func:`origin_check` - time base, integer-period rounding, fallback legs.
* t_D (R6-B4, 100 samples) :func:`departure`, with the runner difference recorded; P3-3 on the new t_D.
* rules seals :func:`seal_check` (original, rev1 .. rev6).

C-1 .. C-9 follow rev6 R6-B1 .. R6-B9 (:data:`ASSUMPTIONS`); ``--assume C-n=value`` is for sensitivity looks only and
marks the output ``deviates_from_rev6``.

Scope: Chrono C-1 .. C-5 and the O-C5 record rows (``run_S9.py level``, run_S8C, run_S6C). Open-loop rows (C-6 / C-7,
``run_S9.py machine``) are not judged here (:data:`OPENLOOP_CRITERIA`): they are listed in ``skipped_rows`` and do not
change the exit code. ``--batch``: a run_S8C / run_S6C row folder is taken from the case log's ``batch wall ... ->
<dir>`` line, else from the one runner folder of its ``--tag`` stamped inside the case window (:func:`_rigid_row_dir`);
every row records how it was found (``row_dir``).

CLI (Chrono-dev, no simulation)::

    python -I -X utf8 04_scripts/02_chrono/chrono_rows_judge_4368.py judge --out out.json \
        [--batch <07_results/S9/batch_...>] [--row <row dir>] [--results-root <07_results>] \
        [--rules-dir <verif_matrix>] [--params <rexome33.yaml>] [--assume C-n=value ...]
    python -I -X utf8 04_scripts/02_chrono/chrono_rows_judge_4368.py disclose [--out f.json]
    python -I -X utf8 04_scripts/02_chrono/chrono_rows_judge_4368.py seals [--rules-dir <dir>]

Exit codes: 0 done; 1 a check failed (seal mismatch, time-origin mismatch) or a row needs a stop (unresolved R40-2
hold); 2 an input is missing or invalid; 3 internal error. The last stdout line is JSON; the line before it is
``errors N``. Units: SI (s, N, m), pressure in bar where the key says so.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOL_VERSION = "chrono_rows_judge_4368 v2 (cad-expert 2026-11-13: row folder from the case log, open-loop rows skipped)"

# --- rules and seals (rev5 R5-A1 requirement 4) -----------------------------------------------------------------
RULES_DIR_DEFAULT = ROOT / "06_analysis" / "02_control" / "verif_matrix"
RULES_SEALS = {
    "v5_resume_4368_rules.md": "9019b405b7a196f28a756e7ca91f443f6241a58bd8e1eee0361483066cb19524",
    "v5_resume_4368_rules_rev1.md": "d9094fda104e25ac7eb7aea44d7c34d8215a839fc3771aa50b224d43082f02c7",
    "v5_resume_4368_rules_rev2.md": "497e4614d6780c3201027b3946e3c21da05e2fefe9a3609436bc35ea664c3199",
    "v5_resume_4368_rules_rev3.md": "dad8dfa68da7a988971f4d687706465289ec7dd95d09079c92215c64e5eae557",
    "v5_resume_4368_rules_rev4.md": "7ea87a30b08a00263c597d42d3450dc56f68952e8d3205604cb2c5bab5dce14b",
    "v5_resume_4368_rules_rev5.md": "452a8436c547e4da8d78205556cbb37633842d42cb98c18849cb883d827b3aca",
    "v5_resume_4368_rules_rev6.md": "809e563971ea451aba7c9d0787c660bdcab1c495af39c513c8f158e09b4fe6c9",
}
"""Sealed sha256 of each rules file (the ``.sha256`` files of 2026-11-13); both the file and its ``.sha256`` must
match (original 8.2 S-1)."""

# --- disclosure (requirement 3) ---------------------------------------------------------------------------------
DISCLOSE_PAIRS = (
    ("04_scripts/03_control/s8/r76_g6_chrono_judge.py", "G6 gates: D-26 / D-27 / D-28 / D-34 / D-35"),
    ("03_src/outrigger_sim/verify/s8_control.py", "C1 row (R40-1 / R40-2): D-31 / D-39"),
    ("03_src/outrigger_sim/verify/s6_control.py", "_times lift-off and moving pressure: D-29 / D-30 / D-32"),
)

# --- constants (rules rev3 / rev4, spec) ------------------------------------------------------------------------
CMP_EPS = 1e-9
"""Original 7.6: a comparison is true within 1e-9."""
F_MIN_N_RULES = 9414.589
"""Rules original 2 / rev3 R3-C4 (YAML ``control.F_min_cylinder_N`` 9414.58911 N); the YAML value is used, this
constant is only checked against it (|diff| <= 0.001 N)."""
R40_MARGIN_N = 5000.0
"""Rev3 R3-G6: R40-2 threshold F_min + 5 kN."""
LIFTOFF_WINDOW_S = 8.0
SLOW_WINDOW_S = 1.0
READY_GATE_S = 120.0
"""Rev3 R3-G4: G6 gate READY <= 120 s after the closed-loop start."""
DEPARTURE_FRACTION = 0.01
DEPARTURE_HOLD_S = 0.1
"""Rev2 R2-5: t_D = crawler normal < 0.01 W held 0.1 s."""
TRANSIENT_MAX_S, TRANSIENT_MAX_W = 0.5, 0.15
CHATTER_AFTER_LOC_S, CHATTER_MAX_S, CHATTER_MAX_OVER = 1.0, 0.1, 1.2
"""P3-1 recontact classes (U-S9-G6d, spec 423.3/423.4); same values as run_S9 / ``late_loc_rule``."""
READY_CRAWLER_WINDOW_S = 10.0
RUT_CLEARANCE_MIN_M = 0.025
MOVING_PRESSURE_MAX_BAR, RELIEF_BAR = 180.0, 210.0
MOVING_EPS_M_S = 1e-9
"""Rev3 Q-13: moving = applied command != 0 with the 7.6 allowance."""
CONTROL_PERIOD_S = 0.1
LOC_EVENT, SOIL_MODE_EVENT = "crawler_liftoff_confirmed", "soil_mode_start"
LOC_REVOKE_EVENTS = ("FIX_LOC_REVOKE", "INFO_LOC_REVOKED")
P38_KINDS = ("leg_reapproach_start", "relevel_predicted", "probe_aborted_low_load")
REAPPROACH_KIND = "leg_reapproach_start"
PRE_LIFT_PHASES = ("idle", "check", "touch")
FAULT_PHASES = ("fault", "fault_reground")
SGS_EVENT = "FAULT_LIFT_STROKE_LIMIT:soil"
STROKE_END_FAULT = "FAULT_STROKE_END"
FALLBACK_EVENT = "WARN_ROD_PRESSURE_FALLBACK"
G6_ROW_NAMES = {"S-03": "D1S_G1_B_middle_Fs4_spJ1FL", "S-04": "D1S_G1_B_bottom_Fs4_spJ1FL"}
"""Row id -> case name of the C-3 rows (G6 gates) when the batch entry has no ``d1_id``; every other row id comes
from the batch entry ``d1_id`` (``d1_chrono_rows``)."""
G6_IDS = ("S-03", "S-04")
OPENLOOP_CRITERIA = ("C-6", "C-7", "C-7a", "C-7b")
"""Open-loop rows (rules original 5.2 / 5.3, rev4 R4-A3 names C-7a / C-7b): not judged by this tool. Original 9.1
gives C-6 / C-7 path 1 = ``result.json`` ``p3a`` and path 2 = ``openloop_compare.py`` ``analyse`` (``series.npz``),
original 7.5 / 8.1 make them record rows (no grade), rev5 R5-A1 (last bullet) scopes the Chrono path 1 aggregation
new version to C-1 .. C-5. Such rows are listed in ``skipped_rows`` (exit code unaffected)."""
OPENLOOP_FILES = ("series.npz", "flow_series.npz")
OPENLOOP_SKIP_RULE = ("rules original 9.1 (C-6 / C-7 path 1 = result.json p3a, path 2 = openloop_compare.py analyse), "
                      "7.5 / 8.1 (record rows, no grade), rev5 R5-A1 (Chrono path 1 new version = C-1 .. C-5)")
LEGS = ("FL", "FR", "RL", "RR")
G = 9.80665
_EVENT_RE = re.compile(r"t_s=([-0-9.eE+]+), name='([^']*)'")

# --- C-1 .. C-9 = rules rev6 R6-B1 .. R6-B9 (sealed 809e5639) ---------------------------------------------------
ASSUMPTIONS: dict[str, str] = {
    "C-1": "bracket_10hz",   # R6-B1: L1-R t_lift = first 10 Hz record row (phase not idle/check/touch, F_crawler normal
                             # <= 0) = t_b; t_a (last row > 0 before it) recorded
    "C-2": "s8a2",           # R6-B2: R40-2 raw = S8-A2 judged force (airborne samples: F_cyl_mean_20ms), count recorded
    "C-3": "first",          # R6-B3: 377 window end = first confirmed LOC (revoked included) + 1 s; final-LOC result recorded
    "C-4": "count",          # R6-B4: t_D hold = 100 samples (samples x 1 ms); runner t_D difference recorded
    "C-5": "10hz",           # R6-B5: moving pressure on the 10 Hz control rows of record.npz
    "C-6": "round",          # R6-B6: integer-period check by n = round(t / T) (no 1e-9 allowance), residual recorded
    "C-7": "union",          # R6-B7: fallback legs = log legs U WARN_ROD_PRESSURE_FALLBACK legs; log leg without event = S-11
    "C-8": "S-01,S-02,S-03,S-04",  # R6-B8: rows of the 427.9 stroke_limited_stop class
    "C-9": "q14",            # R6-B9: SGS condition 3 lift = pad normal <= 0 (Chrono)
}
"""Rules rev6 definitions (the alignment table's open questions C-1 .. C-9). ``--assume C-n=value`` replaces one for a
sensitivity look; the output then carries ``deviates_from_rev6`` and must not be used as the path 1 result."""
ASSUMPTION_CHOICES = {"C-1": ("bracket_10hz", "not_judgeable"), "C-2": ("s8a2", "raw"), "C-3": ("first", "final"),
                      "C-4": ("count", "span"), "C-5": ("10hz",), "C-6": ("round",), "C-7": ("union",),
                      "C-9": ("q14", "harness")}
D_NUMBERS = {"N-1": "D-26", "N-2": "D-27", "N-3": "D-28", "N-4": "D-29", "N-5": "D-30", "N-6": "D-31", "N-7": "D-32",
             "N-8": "D-33", "N-9": "D-34", "N-10": "D-35", "N-11": "D-36", "N-12": "D-37", "N-13": "D-38",
             "N-14": "D-39"}
"""Rev6 R6-A: alignment-table N items -> disclosure numbers D-26 .. D-39."""


class InputError(Exception):
    """A required input is missing or invalid (exit 2)."""


# =============================================================================================== helpers
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ge(v: float, c: float) -> bool:
    return bool(v >= c - CMP_EPS)


def le(v: float, c: float) -> bool:
    return bool(v <= c + CMP_EPS)


def centred_mean(x: np.ndarray, n: int) -> np.ndarray:
    """Centred moving mean over ``n`` (made odd) samples along axis 0, truncated at the ends (same definition as
    ``verify/s7_control.centred_mean``, re-written here so the new version has no import of the judge modules)."""
    x = np.asarray(x, dtype=float)
    n = max(1, int(n) | 1)
    h = n // 2
    c = np.concatenate([np.zeros((1, *x.shape[1:])), np.cumsum(x, axis=0)], axis=0)
    k = np.arange(x.shape[0])
    lo = np.clip(k - h, 0, x.shape[0])
    hi = np.clip(k + h + 1, 0, x.shape[0])
    cnt = (hi - lo).reshape((-1,) + (1,) * (x.ndim - 1))
    return (c[hi] - c[lo]) / cnt


def median_dt(t: np.ndarray) -> float:
    return float(np.median(np.diff(t))) if t.size > 1 else float("nan")


def phase_at(t: np.ndarray, phases_abs: list[tuple[float, str]]) -> np.ndarray:
    """Phase name of each sample (last phase starting at or before it; ``idle`` before the first)."""
    names = np.array(["idle"] + [p for _, p in phases_abs], dtype=object)
    starts = np.array([tp for tp, _ in phases_abs], dtype=float)
    k = np.searchsorted(starts, np.asarray(t, float) + CMP_EPS, side="right")
    return names[k]


def phase_windows(phases_abs: list[tuple[float, str]], name: str, t_end: float) -> list[tuple[float, float]]:
    out = []
    for i, (tp, ph) in enumerate(phases_abs):
        if ph == name:
            out.append((tp, phases_abs[i + 1][0] if i + 1 < len(phases_abs) else t_end))
    return out


def event_kind_leg(name: str) -> tuple[str, str | None]:
    head, _, rest = name.partition(":")
    return head, (rest.split(":")[0] if rest else None)


def has_fault(events: list[tuple[float, str]], phases_abs: list[tuple[float, str]]) -> bool:
    return any(p in FAULT_PHASES for _, p in phases_abs) or any(n.startswith("FAULT") for _, n in events)


def first_phase(phases_abs: list[tuple[float, str]], name: str) -> float | None:
    return next((tp for tp, p in phases_abs if p == name), None)


def first_event(events: list[tuple[float, str]], name: str) -> float | None:
    return next((te for te, n in events if n == name), None)


def first_run(flag: np.ndarray, t: np.ndarray, hold_s: float, rule: str) -> tuple[int | None, int | None]:
    """First run of ``flag`` lasting ``hold_s``: C-4 ``count`` = samples x dt >= hold, ``span`` = last - first >=
    hold. Returns (start index, index where the hold is reached)."""
    dt = median_dt(t)
    need = max(1, int(round(hold_s / dt))) if rule == "count" else None
    start = None
    for k in range(len(t)):
        if flag[k]:
            if start is None:
                start = k
            if (need is not None and k - start + 1 >= need) or (need is None and t[k] - t[start] >= hold_s - CMP_EPS):
                return start, k
        else:
            start = None
    return None, None


def runs(flag: np.ndarray) -> list[tuple[int, int]]:
    """(first, last) index of each run of True."""
    f = np.asarray(flag, bool).astype(np.int8)
    d = np.diff(np.concatenate([[0], f, [0]]))
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1, strict=True))


# =============================================================================================== params / inputs
def load_params(path: Path) -> dict[str, Any]:
    import yaml  # noqa: PLC0415 - Chrono-dev has PyYAML

    if not path.exists():
        raise InputError(f"params YAML missing: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        head = [float(raw["legs"][lg]["cylinder"]["head_area_m2"]) for lg in LEGS]
        rod_kg = [float(raw["legs"][lg]["moving_part"]["mass_kg"]) for lg in LEGS]
        f_min = float(raw["control"]["F_min_cylinder_N"])
    except (KeyError, TypeError, ValueError) as e:
        raise InputError(f"params YAML lacks a key: {e}") from e
    return {"path": str(path), "sha256": sha256_file(path), "head_area_m2": head, "rod_weight_N": [m * G for m in rod_kg],
            "F_min_N": f_min, "F_min_matches_rules": abs(f_min - F_MIN_N_RULES) <= 1e-3}


def parse_events_json(path: Path) -> list[tuple[float, str]]:
    out = []
    for s in json.loads(path.read_text(encoding="utf-8")):
        m = _EVENT_RE.search(str(s))
        if m:
            out.append((float(m.group(1)), m.group(2)))
    return out


def npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def load_row(d: Path) -> dict[str, Any]:
    """Result, engine kind and series of one row folder."""
    rj = d / "result.json"
    if not rj.exists():
        raise InputError(f"result.json missing: {d}")
    res = json.loads(rj.read_text(encoding="utf-8"))
    row: dict[str, Any] = {"dir": str(d), "name": d.name, "result": res, "files": {}}
    for name in ("step_series.npz", "pads.npz", "r8_series.npz", "record/record.npz"):
        p = d / name
        if p.exists():
            row["files"][name] = {"sha256": sha256_file(p)}
    if "step_series.npz" in row["files"]:
        row["engine"] = "SCM"
        row["series"] = npz(d / "step_series.npz")
        phases = [(float(p["t_s"]), str(p["phase"])) for p in res.get("phases") or []]
        events = [(float(e["t_s"]), str(e["name"])) for e in res.get("events") or []]
        t0 = float((res.get("p3b") or {}).get("t_loop_start_s", phases[0][0] if phases else 0.0))
    elif "pads.npz" in row["files"]:
        pads = npz(d / "pads.npz")
        row["engine"] = "L2b" if "crawler_normal_N" in pads else "L1R"
        row["pads"] = pads
        t0 = float(res["settings"]["start_t_s"])
        # rev6 R6-1: run_S8C / run_S6C result.json phases are relative to settings.start_t_s (run_S8C 1876); a
        # phase time beyond the run length means an absolute list (mixed bases = S-11)
        raw = [(float(tp), str(p)) for tp, p in res.get("phases") or []]
        span = float(np.asarray(pads["t"], float)[-1]) - t0
        if raw and max(tp for tp, _ in raw) > span + 1e-6:
            row["time_base_problems"] = [f"S-11: phases up to {max(tp for tp, _ in raw):g} s exceed the run length "
                                         f"{span:g} s after start_t_s (not relative times)"]
        phases = [(tp + t0, p) for tp, p in raw]
        ev = d / "controller_events.json"
        events = parse_events_json(ev) if ev.exists() else []
    elif "p3a" in res and (d / "series.npz").exists():
        # run_S9 ``machine`` open-loop row (C-6 / C-7): outside this tool (see :func:`openloop_skip`); recorded only
        for name in OPENLOOP_FILES:
            if (d / name).exists():
                row["files"][name] = {"sha256": sha256_file(d / name)}
        row["engine"] = "openloop"
        return row
    else:
        raise InputError(f"no step_series.npz / pads.npz in {d}")
    rec = d / "record" / "record.npz"
    row["record"] = npz(rec) if rec.exists() else None
    r8 = d / "r8_series.npz"
    row["r8"] = npz(r8) if r8.exists() else None
    row.update(t0=t0, phases=sorted(phases), events=sorted(events))
    return row


def row_id_of(row: dict[str, Any], meta: dict[str, Any] | None) -> str | None:
    if meta and meta.get("d1_id"):
        return str(meta["d1_id"])
    for rid, stem in G6_ROW_NAMES.items():
        if row["name"].startswith(stem) or (meta and str(meta.get("case", "")).startswith(stem)):
            return rid
    return None


# =============================================================================================== N items
def departure(t: np.ndarray, cn: np.ndarray, weight_N: float, rule: str) -> dict[str, Any]:
    lim = DEPARTURE_FRACTION * weight_N
    k0, k1 = first_run(cn < lim, t, DEPARTURE_HOLD_S, rule)
    out: dict[str, Any] = {"limit_N": lim, "rule": f"crawler normal < 0.01 W held 0.1 s (C-4 {rule})",
                           "departed": k0 is not None}
    if k0 is not None:
        out.update(t_departure_s=float(t[k0]), t_confirmed_s=float(t[k1]), k_confirmed=int(k1))
    return out


def recontact_events(t: np.ndarray, cn: np.ndarray, weight_N: float, dep: dict[str, Any], t_loc_fin: float | None,
                     t_ready: float | None) -> dict[str, Any]:
    """N-11: recontacts after the departure confirmation (>= 0.01 W), duration = samples x dt (rev3 Q-11)."""
    out: dict[str, Any] = {"events": [], "pass": True, "flags": []}
    if not dep.get("departed"):
        return out
    dt = median_dt(t)
    lim = DEPARTURE_FRACTION * weight_N
    on = (np.arange(t.size) >= dep["k_confirmed"]) & (cn >= lim)
    for a, b in runs(on):
        dur = (b - a + 1) * dt
        ended = b + 1 < t.size
        t_end = float(t[b + 1]) if ended else None
        peak = float(cn[a:b + 1].max())
        before = bool(t_loc_fin is not None and ended and t_end <= t_loc_fin + CMP_EPS)
        transient = bool(ended and dur <= TRANSIENT_MAX_S + CMP_EPS and before and peak <= TRANSIENT_MAX_W * weight_N)
        ts = float(t[a])
        chatter = bool(not transient and t_loc_fin is not None and ended
                       and t_loc_fin + CMP_EPS < ts <= t_loc_fin + CHATTER_AFTER_LOC_S + CMP_EPS
                       and dur <= CHATTER_MAX_S + CMP_EPS and peak <= CHATTER_MAX_OVER * lim
                       and (t_ready is None or ts < t_ready))
        out["events"].append({"t_start_s": ts, "t_end_s": t_end, "samples": int(b - a + 1), "duration_s": dur,
                              "max_normal_N": peak, "class": "transient_flag" if transient else
                              ("threshold_chatter" if chatter else "strict_fail")})
    cls = [e["class"] for e in out["events"]]
    out["pass"] = "strict_fail" not in cls
    out["flags"] = (["P3-1_transient_recontact"] if "transient_flag" in cls else []) + (
        ["P3-1_threshold_chatter"] if "threshold_chatter" in cls else [])
    return out


def loc_timeline(events: list[tuple[float, str]]) -> dict[str, Any]:
    """First / final confirmed LOC (spec 424.8.1: a revocation cancels the latest LOC at or before it)."""
    locs = [te for te, n in events if n == LOC_EVENT]
    revokes = [te for te, n in events if event_kind_leg(n)[0] in LOC_REVOKE_EVENTS]
    revoked: list[float] = []
    for tr in revokes:
        live = [x for x in locs if x <= tr + CMP_EPS and x not in revoked]
        if live:
            revoked.append(live[-1])
    if revokes:
        after = [x for x in locs if x > revokes[-1] + CMP_EPS]
        final = after[0] if after else None
    else:
        final = locs[0] if locs else None
    return {"t_loc_first_s": locs[0] if locs else None, "t_loc_final_s": final, "revoked_loc_s": revoked,
            "revokes_s": revokes}


def p32_block(t: np.ndarray, cn: np.ndarray, weight_N: float, tl: dict[str, Any], t_dep: float | None,
              t_done: float | None, limit_s: float | None) -> dict[str, Any]:
    """N-12 / N-13: order clause strict (final LOC < first DONE), loaded = > 0.01 W at the final LOC, time clause
    0 <= t_LOC - t_D <= T_lim; revoked LOCs: crawler normal recorded."""
    lim = DEPARTURE_FRACTION * weight_N

    def cn_at(tq: float) -> float:
        return float(cn[min(int(np.searchsorted(t, tq - CMP_EPS)), t.size - 1)])

    t_loc = tl["t_loc_final_s"]
    out: dict[str, Any] = {"t_loc_final_s": t_loc, "t_first_done_s": t_done, "limit_s": limit_s,
                           "revoked": [{"t_s": x, "crawler_normal_N": cn_at(x), "loaded": cn_at(x) > lim}
                                       for x in tl["revoked_loc_s"]]}
    if t_loc is None:
        out.update(order=False, within=False, reason="no LOC")
        return out
    order = bool(t_done is None or t_loc < t_done)
    c = cn_at(t_loc)
    d = None if t_dep is None else t_loc - t_dep
    out.update(order=order, crawler_normal_at_loc_N=c, loaded=bool(c > lim), loc_minus_departure_s=d)
    if limit_s is None or d is None:
        out.update(within=None, reason="T_lim or t_D unknown")
    else:
        out["within"] = bool(order and not out["loaded"] and d >= -CMP_EPS and le(d, limit_s))
    return out


def _preloc_flag_ok(t: np.ndarray, f: np.ndarray, hits: list[dict[str, Any]], t_ref: float | None, f_min_N: float,
                    fault: bool) -> tuple[bool | None, list[dict[str, Any]]]:
    """377 condition over the P3-8 hits: every hit is a re-approach start whose started leg's 1 ms true F_cyl minimum
    over [start, t_ref + 1 s] is >= F_min, and no FAULT. None = not computable (no samples in a window)."""
    rows, ok = [], True
    for h in hits:
        r = {"t_s": h["t_s"], "event": h["event"]}
        if h["kind"] != REAPPROACH_KIND or h["leg"] not in LEGS:
            r["reason"] = "not a re-approach start (377 covers re-approach only)"
            ok = False
        else:
            hi = (t_ref + 1.0) if t_ref is not None else float(t[-1])
            sel = (t >= h["t_s"] - CMP_EPS) & (t <= hi + CMP_EPS)
            if not sel.any():
                return None, rows
            m = float(f[sel, LEGS.index(h["leg"])].min())
            r.update(window_s=[h["t_s"], hi], min_F_cyl_N=m, ge_F_min=ge(m, f_min_N))
            ok &= r["ge_F_min"]
        rows.append(r)
    return bool(ok and not fault), rows


def p38_block(t: np.ndarray, f: np.ndarray, events: list[tuple[float, str]], tl: dict[str, Any],
              f_min_N: float, fault: bool, loc_rule: str, g63_pass: bool | None) -> dict[str, Any]:
    """D-35 (N-10): window = start .. min(first LOC (revoked ones too), first soil mode start). D-34 (N-9, rev6 R6-B3 /
    R6-C3): ``preloc_flag_ok`` (377: start .. first LOC + 1 s) true -> FLAG ``P3-8_demoted``; false with G6-3 true and
    no FAULT -> FLAG ``P3-8_preloc_loss`` (U-S9-G6c); otherwise fail; not computable -> not_judgeable. Both FLAG
    branches go to ``demoted_items``. The 377 result with the final LOC is recorded (R6-B3)."""
    ends = [x for x in (tl["t_loc_first_s"], first_event(events, SOIL_MODE_EVENT)) if x is not None]
    w_end = min(ends) if ends else None
    hits = []
    for te, n in events:
        kind, leg = event_kind_leg(n)
        if kind in P38_KINDS and (w_end is None or te < w_end):
            hits.append({"t_s": te, "event": n, "kind": kind, "leg": leg})
    first_ref, final_ref = tl["t_loc_first_s"], tl["t_loc_final_s"]
    t_ref = final_ref if loc_rule == "final" else first_ref
    other_ref = first_ref if loc_rule == "final" else final_ref
    out: dict[str, Any] = {"window_end_s": w_end, "events": hits, "loc_for_377": loc_rule, "fault": fault,
                           "F_min_N": f_min_N, "G6-3_pass": g63_pass, "demoted_items": [], "flags": []}
    if not hits:
        out.update(verdict="pass", preloc_flag_ok=None)
        return out
    ok, rows = _preloc_flag_ok(t, f, hits, t_ref, f_min_N, fault)
    ok_other, _ = _preloc_flag_ok(t, f, hits, other_ref, f_min_N, fault)
    out.update(preloc_flag_ok=ok, preloc_rows=rows,
               record_377_other_loc={"loc": "final" if loc_rule != "final" else "first", "preloc_flag_ok": ok_other,
                                     "differs": ok_other != ok, "loc_revoked_run": bool(tl["revoked_loc_s"])})
    if ok is None:
        out.update(verdict="not_judgeable", reason="preloc_flag_ok not computable (rev6 R6-C3 branch 3)")
    elif ok:
        out.update(verdict="flag", flags=["P3-8_demoted"],
                   demoted_items=[{"item": "G6-7_preloc", "rule": "377", "flag": "P3-8_demoted"}])
    elif g63_pass and not fault:
        out.update(verdict="flag", flags=["P3-8_preloc_loss"],
                   demoted_items=[{"item": "G6-7_preloc", "rule": "U-S9-G6c", "flag": "P3-8_preloc_loss"}])
    else:
        out["verdict"] = "fail"
    return out


def lift_samples(t: np.ndarray, pad_n: np.ndarray, t_from: float | None, *, f_cyl: np.ndarray | None = None,
                 rod_weight_N: list[float] | None = None, rule: str = "q14") -> dict[str, Any]:
    """N-8 / Q-14: lifted sample = pad normal <= 0 (C-9 ``harness``: F_cyl + rod weight <= 0) from ``t_from``."""
    if t_from is None:
        return {"t_from_s": None, "status": "not_judgeable", "reason": "no start time"}
    if rule == "harness":
        x = np.asarray(f_cyl, float) + np.asarray(rod_weight_N, float)[None, :]
    else:
        x = np.asarray(pad_n, float)
    sel = t >= t_from - CMP_EPS
    lifted = (x <= 0.0) & sel[:, None]
    per = {}
    for i, lg in enumerate(LEGS):
        k = np.flatnonzero(lifted[:, i])
        per[lg] = {"samples": int(k.size), "t_first_s": float(t[k[0]]) if k.size else None}
    return {"t_from_s": t_from, "rule": rule, "per_leg": per, "lifted": bool(lifted.any())}


def moving_pressure(rec: dict[str, np.ndarray] | None, head_area_m2: list[float], *, event_row: bool) -> dict[str, Any]:
    """N-7 (rev3 Q-13, C-5 10 Hz): moving = |u_applied| > 1e-9 m/s, p = F_cyl / A_p, saturation = extending >= 210
    bar. Event rows need the J-5 / U58 window, not in this version -> not_judgeable."""
    if rec is None or "u_applied" not in rec or "F_cyl" not in rec:
        return {"status": "not_judgeable", "reason": "record.npz u_applied / F_cyl missing"}
    u = np.asarray(rec["u_applied"], float)
    p = np.asarray(rec["F_cyl"], float) / np.asarray(head_area_m2, float)[None, :] / 1e5
    moving = np.abs(u) > MOVING_EPS_M_S
    sat = (u > MOVING_EPS_M_S) & (p >= RELIEF_BAR - CMP_EPS)
    out: dict[str, Any] = {"basis": "record.npz 10 Hz rows (C-5)", "moving_samples": int(moving.sum()),
                           "max_moving_bar": float(p[moving].max()) if moving.any() else None,
                           "saturated_samples": int(sat.sum())}
    if event_row:
        out.update(status="not_judgeable", reason="event row: J-5 / U58 window not in this version")
    else:
        out["within"] = bool((out["max_moving_bar"] is None or le(out["max_moving_bar"], MOVING_PRESSURE_MAX_BAR))
                             and out["saturated_samples"] == 0)
        out["status"] = "judged"
    return out


def d8_lift_time(t: np.ndarray, cn: np.ndarray, phases_abs: list[tuple[float, str]]) -> float | None:
    """N-4 / N-5 (rev3 R3-G5, rev6 5 t_lift): first sample whose phase is not idle / check / touch with the crawler
    normal <= 0."""
    ph = phase_at(t, phases_abs)
    ok = ~np.isin(ph, PRE_LIFT_PHASES) & (np.asarray(cn, float) <= 0.0)
    k = np.flatnonzero(ok)
    return float(t[k[0]]) if k.size else None


def c1_block(row: dict[str, Any], t_lift: float | None, f_min_N: float, raw_rule: str) -> dict[str, Any]:
    """N-6 / N-14: R40-1 raw minimum after t_lift (outside REANCHOR, before a floor event) >= F_min + 5 kN; R40-2
    hold (rigid crawler, minimum within 8 s of t_lift, slow minimum over the same 8 s >= the limit) =
    ``not_judgeable`` and a stop (the L1-pair resolution is a person's step)."""
    pads, res = row["pads"], row["result"]
    limit = f_min_N + R40_MARGIN_N
    out: dict[str, Any] = {"limit_N": limit, "t_lift_s": t_lift, "raw_rule": raw_rule}
    if t_lift is None:
        out.update(status="not_judgeable", reason="no t_lift")
        return out
    t = np.asarray(pads["t"], float)
    f = np.asarray(pads["F_cyl_min_interval"], float)
    air = None
    if raw_rule == "s8a2" and "airborne" in pads and "F_cyl_mean_20ms" in pads:
        air = np.asarray(pads["airborne"], bool)
        f = np.where(air, np.asarray(pads["F_cyl_mean_20ms"], float), f)
    elif raw_rule == "s8a2":
        out["s8a2_note"] = "pads.npz has no airborne / F_cyl_mean_20ms: plain 1 ms minimum"
    mask = t >= t_lift - CMP_EPS
    for a, b in phase_windows(row["phases"], "reanchor", float(t[-1])):
        mask &= ~((t >= a - CMP_EPS) & (t <= b + CMP_EPS))
    ev = res.get("event_t_s")
    if ev is not None:
        mask &= t < float(ev) + row["t0"]
    if not mask.any():
        out.update(status="not_judgeable", reason="no samples after t_lift")
        return out
    slow = centred_mean(f, int(round(SLOW_WINDOW_S / median_dt(t))))
    fa = np.where(mask[:, None], f, np.inf)
    k = np.unravel_index(int(np.argmin(fa)), fa.shape)
    raw = float(fa[k])
    early = mask & (t <= t_lift + LIFTOFF_WINDOW_S + CMP_EPS)
    slow8 = float(np.where(early[:, None], slow, np.inf).min()) if early.any() else None
    s8 = (res.get("settings") or {}).get("s8") or {}
    rigid = str(s8.get("crawler_contact") or "nsc_rigid") == "nsc_rigid" or s8.get("crawler_check_passed") is not True
    after = float(t[k[0]]) - t_lift
    passed = ge(raw, limit)
    hold = bool(not passed and rigid and le(after, LIFTOFF_WINDOW_S) and slow8 is not None and ge(slow8, limit))
    out["s8a2_airborne_samples_in_window"] = None if air is None else int((air & mask[:, None]).sum())
    out.update(raw_min_N=raw, raw_leg=LEGS[k[1]], raw_t_s=float(t[k[0]]), raw_after_lift_s=after,
               slow_min_first8_N=slow8, rigid=rigid,
               status="not_judgeable" if hold else "judged", verdict=None if hold else ("pass" if passed else "fail"),
               hold=hold, stop=hold,
               note="R40-2 hold: not judgeable; resolve with the L1 pair (F_s 0, d1_selection_rules 8) or ask"
               if hold else "")
    return out


def sgs_class(row: dict[str, Any], s: dict[str, np.ndarray], dep: dict[str, Any], f_min_N: float, mp: dict[str, Any],
              params: dict[str, Any], c9: str) -> dict[str, Any]:
    """N-1 (spec 427.9, rev3 R3-G3): soil-guard safe stop = stroke_limited_stop when conditions 1 .. 5 hold."""
    events, phases = row["events"], row["phases"]
    faults = [n for _, n in events if n.startswith("FAULT")]
    c1 = bool(faults and faults[0].startswith(SGS_EVENT))
    if not c1:
        return {"applies": False, "class": None, "first_fault": faults[0] if faults else None}
    t = np.asarray(s["t_s"], float)
    c2 = not any(n.startswith(STROKE_END_FAULT) for _, n in events)
    lift = lift_samples(t, s["scm_pad_normal_N"], first_phase(phases, "level"), f_cyl=s["F_cyl_N"],
                        rod_weight_N=params["rod_weight_N"], rule=c9)
    c3 = lift.get("lifted") is False
    t_dep = dep.get("t_departure_s")
    m = None
    if t_dep is not None:
        sel = t >= t_dep - CMP_EPS
        m = float(np.asarray(s["F_cyl_N"], float)[sel].min())
    c4 = bool(m is not None and ge(m, f_min_N))
    c5 = mp.get("within") is True
    conds = {"1_soil_stop_first": c1, "2_no_stroke_end": c2, "3_no_lift": c3, "4_F_after_departure": c4,
             "5_moving_pressure": c5}
    return {"applies": True, "conditions": conds, "min_F_after_departure_N": m, "lift": lift,
            "class": "stroke_limited_stop" if all(conds.values()) else "fail"}


def ready_items(phases: list[tuple[float, str]], t0: float, p3b: dict[str, Any]) -> dict[str, Any]:
    """N-2 / N-3: P3-6 (record; FLAG when outside the row limit), G6 gate READY <= 120 s + 1e-9."""
    t_ready = first_phase(phases, "ready")
    rel = None if t_ready is None else t_ready - t0
    p36 = p3b.get("P3-6_ready") or {}
    lim = p36.get("limit_s")
    return {"t_ready_rel_s": rel, "P3-6_limit_s": lim,
            "P3-6": None if rel is None or lim is None else ("pass" if le(rel, float(lim)) else "flag"),
            "READY_le_120s": bool(rel is not None and le(rel, READY_GATE_S))}


FINE_DT_S = 1e-3


def origin_check(row: dict[str, Any]) -> dict[str, Any]:
    """R5-B1 with rev6 R6-B6 (original 2 integer-period comparison n = round(t / T), no 1e-9 allowance):
    every r8 row gives consecutive control-period numbers round((t - t0) / 0.1) and the same 1 ms number
    round(t / 1e-3) as a 1 ms series sample; every ``fallback_lock_log`` ``t_start_s`` has the 1 ms number of an r8
    row. Residuals are recorded. R6-B7 (C-7): fallback legs = log legs U ``WARN_ROD_PRESSURE_FALLBACK`` legs; a log leg
    without the event = S-11; event-only legs (open stretch) are listed for the J11 recount. R6-1: phase time-base
    problems of the row are S-11 too."""
    out: dict[str, Any] = {"rule": "rev6 R6-B6 round(t / T)", "ok": True,
                           "problems": list(row.get("time_base_problems") or [])}
    fine = np.asarray(row["series"]["t_s"] if row["engine"] == "SCM" else row["pads"]["t"], float)
    r8 = None if row["r8"] is None else np.asarray(row["r8"]["t"], float)
    if r8 is None or r8.size == 0:
        out.update(ok=None, problems=out["problems"] + ["no r8_series t"])
        return out
    n_period = np.round((r8 - row["t0"]) / CONTROL_PERIOD_S)
    fine_ms = set(np.round(fine / FINE_DT_S).astype(np.int64).tolist())
    r8_ms = np.round(r8 / FINE_DT_S).astype(np.int64)
    missing = [float(r8[i]) for i, v in enumerate(r8_ms.tolist()) if v not in fine_ms]
    consecutive = bool(np.all(np.diff(n_period) == 1.0))
    out.update(r8_first_t_s=float(r8[0]), t0_s=row["t0"], first_period_number=int(n_period[0]),
               periods_consecutive=consecutive, r8_rows_without_1ms_sample=len(missing),
               residual_period_max=float(np.abs((r8 - row["t0"]) / CONTROL_PERIOD_S - n_period).max()),
               residual_1ms_max_s=float(np.abs(r8 - r8_ms * FINE_DT_S).max()))
    if not consecutive:
        out["problems"].append("r8 control-period numbers are not consecutive")
    if missing:
        out["problems"].append(f"{len(missing)} r8 rows without a 1 ms sample of the same number (first {missing[0]})")
    tp = ((row["result"].get("controller_meta") or {}).get("two_pressure") or {})
    log = tp.get("fallback_lock_log")
    warn_legs = sorted({event_kind_leg(n)[1] for _, n in row["events"] if event_kind_leg(n)[0] == FALLBACK_EVENT})
    if log is None:
        out["fallback"] = {"log": "key missing", "event_legs": warn_legs}
        if warn_legs:
            out["problems"].append("S-11: fallback events but no fallback_lock_log key")
    else:
        log_legs = sorted({str(e["leg"]) for e in log})
        r8_set = set(r8_ms.tolist())
        off = [float(e["t_start_s"]) for e in log if int(round(float(e["t_start_s"]) / FINE_DT_S)) not in r8_set]
        out["fallback"] = {"log_entries": len(log), "log_legs": log_legs, "event_legs": warn_legs,
                           "fallback_legs_R6_B7": sorted(set(log_legs) | set(warn_legs)),
                           "open_stretch_legs": [lg for lg in warn_legs if lg not in log_legs],
                           "open_stretch_note": "J11 window end / n_late of open stretches = the C-5 J11 recount "
                                                "(revision 6 6), not computed here",
                           "t_start_not_on_r8_rows": off}
        bad = [lg for lg in log_legs if lg not in warn_legs]
        if bad:
            out["problems"].append(f"S-11: fallback_lock_log legs without WARN_ROD_PRESSURE_FALLBACK: {bad}")
        if off:
            out["problems"].append(f"fallback_lock_log t_start_s not on an r8 row: {off[:3]}")
    out["ok"] = not out["problems"]
    return out


# =============================================================================================== rows
def judge_scm(row: dict[str, Any], rid: str | None, params: dict[str, Any], asm: dict[str, str]) -> dict[str, Any]:
    res, s = row["result"], row["series"]
    p3b = res.get("p3b") or {}
    if "weight_N" not in p3b:
        raise InputError(f"p3b.weight_N missing: {row['dir']}")
    w = float(p3b["weight_N"])
    f_min = params["F_min_N"]
    t = np.asarray(s["t_s"], float)
    cn = np.asarray(s["scm_crawler_normal_N"], float)
    f = np.asarray(s["F_cyl_N"], float)
    phases, events = row["phases"], row["events"]
    fault = has_fault(events, phases)
    dep = departure(t, cn, w, asm["C-4"])
    runner_td = (p3b.get("departure") or {}).get("t_departure_s")
    dep["runner_t_departure_s"] = runner_td
    dep["differs_from_runner"] = bool((runner_td is None) != (dep.get("t_departure_s") is None) or (
        runner_td is not None and abs(float(runner_td) - dep["t_departure_s"]) > CMP_EPS))
    dep["diff_from_runner_s"] = None if runner_td is None or dep.get("t_departure_s") is None else \
        dep["t_departure_s"] - float(runner_td)
    t_dep = dep.get("t_departure_s")
    f_after = None if t_dep is None else float(f[t >= t_dep - CMP_EPS].min())
    p33 = {"t_D_s": t_dep, "F_min_after_departure_N": f_after,
           "within": None if f_after is None else ge(f_after, f_min)}
    tl = loc_timeline(events)
    t_ready, t_done = first_phase(phases, "ready"), first_phase(phases, "done")
    rc = recontact_events(t, cn, w, dep, tl["t_loc_final_s"], t_ready)
    p32 = p32_block(t, cn, w, tl, t_dep, t_done, (p3b.get("P3-2_loc") or {}).get("limit_s"))
    p38 = p38_block(t, f, events, tl, f_min, fault, asm["C-3"], p33["within"])
    ready = ready_items(phases, row["t0"], p3b)
    mp = moving_pressure(row["record"], params["head_area_m2"], event_row=res.get("soil_event") is not None)
    t_lift = d8_lift_time(t, cn, phases)
    lift_level = lift_samples(t, s["scm_pad_normal_N"], first_phase(phases, "level"), f_cyl=f,
                              rod_weight_N=params["rod_weight_N"], rule=asm["C-9"])
    sgs_rows = [x.strip() for x in asm["C-8"].split(",") if x.strip()]
    sgs = sgs_class(row, s, dep, f_min, mp, params, asm["C-9"]) if rid in sgs_rows else {"applies": None,
                                                                                        "reason": "C-8: not a SGS row"}
    items = {"departure_t_D": dep, "P3-3_after_t_D": p33, "P3-1_recontact_D-36": rc, "loc_timeline": tl,
             "P3-2_D-37_D-38": p32, "P3-8_D-34_D-35": p38, "ready_D-27_D-28": ready, "moving_pressure_D-32": mp,
             "D8_t_lift_s_D-30": t_lift, "lift_after_level_D-33": lift_level, "SGS_427_9_D-26": sgs}
    out = {"items": items, "grade": None, "grade_note": "D items re-computed; row grade only for G6 rows (S-03 / S-04)",
           "demoted_items": p38["demoted_items"]}
    if rid in G6_IDS:
        out.update(g6_grade(p3b, t, cn, f_after, rc, p32, p38, ready, sgs, fault, f_min))
    return out


def g6_grade(p3b, t, cn, f_after, rc, p32, p38, ready, sgs, fault, f_min) -> dict[str, Any]:
    """G6 gates of C-3 (rev3 R3-G3 / G4, d1_selection_rules 11: P3 + G6, stroke_limited_stop allowed)."""
    t_r = ready["t_ready_rel_s"]
    t_ready_abs = None if t_r is None else t_r + float(p3b.get("t_loop_start_s", 0.0))
    zero = None
    if t_ready_abs is not None:
        w = (t >= t_ready_abs - CMP_EPS) & (t <= t_ready_abs + READY_CRAWLER_WINDOW_S + CMP_EPS)
        zero = bool(w.any() and cn[w].max() <= 0.0)
    p32b = p3b.get("P3-2_loc") or {}
    p32_flag = bool((p32b.get("late_loc_reapproach") or {}).get("flag") or (p32b.get("late_loc_revoked") or {}).get("flag"))
    p35 = p3b.get("P3-5_clearance_stroke") or {}
    rut = p35.get("rut_clearance_min_after_first_ready_m")
    p34v = (p3b.get("checks") or {}).get("P3-4_verdict")
    gates = {
        "G6-1_crawler": "pass" if (zero and rc["pass"] and not rc["flags"]) else (
            "flag" if (zero and rc["pass"]) else "fail"),
        "G6-2_loc": "pass" if p32.get("within") else ("flag" if p32_flag else "fail"),
        "G6-3_Fmin": "pass" if (f_after is not None and ge(f_after, f_min)) else "fail",
        "G6-4_att": p34v if (t_r is not None and p34v in ("pass", "flag", "fail")) else "fail",
        "G6-5_rut_stroke": "pass" if (rut is not None and ge(float(rut), RUT_CLEARANCE_MIN_M)
                                      and p35.get("stroke_within")) else "fail",
        "G6-6_fault_ready": "pass" if (not fault and t_r is not None) else "fail",
        "G6-7_preloc": p38["verdict"],
        "READY_le_120s": "pass" if ready["READY_le_120s"] else "fail",
    }
    if sgs.get("class") == "stroke_limited_stop":
        grade = "stroke_limited_stop"
        note = "427.9 safe stop: allowed stop (original allowed_stop), READY-dependent gates not used"
    elif sgs.get("class") == "fail":
        grade, note = "fail", "soil-guard stop without the 427.9 conditions"
    else:
        vals = list(gates.values())
        # original 274: not judgeable > fail > pass (FLAG is not a fail, rev3 R3-G7)
        grade = ("not_judgeable" if "not_judgeable" in vals else "fail" if "fail" in vals
                 else "flag" if "flag" in vals else "pass")
        note = ""
    return {"gates": gates, "F_min_after_departure_N": f_after, "grade": grade, "grade_note": note,
            "P3-6_record": ready["P3-6"]}


def judge_rigid(row: dict[str, Any], params: dict[str, Any], asm: dict[str, str]) -> dict[str, Any]:
    pads = row["pads"]
    t = np.asarray(pads["t"], float)
    f_min = params["F_min_N"]
    event_row = row["result"].get("event_t_s") is not None
    mp = moving_pressure(row["record"], params["head_area_m2"], event_row=event_row)
    if row["engine"] == "L2b":
        t_lift = d8_lift_time(t, np.asarray(pads["crawler_normal_N"], float), row["phases"])
        lift_basis = "pads.npz crawler_normal_N 1 ms"
    elif asm["C-1"] == "bracket_10hz" and row["record"] is not None and "F_crawler" in row["record"]:
        # rev6 R6-B1: revision 6 5 "10 Hz bracket": t_b = first 10 Hz row (phase not idle / check / touch) with the
        # crawler normal <= 0, t_a = last row with the normal > 0 before it; normal = floor normal projection
        rec = row["record"]
        tr = np.asarray(rec["t"], float)
        nrm = (row["result"].get("floor_plane") or {}).get("normal_world")
        n_src = "result.json floor_plane.normal_world" if nrm is not None else "world z (no floor_plane record)"
        nrm = np.asarray(nrm if nrm is not None else [0.0, 0.0, 1.0], float)
        fcn = np.asarray(rec["F_crawler"], float) @ (nrm / np.linalg.norm(nrm))
        t_lift = d8_lift_time(tr, fcn, row["phases"])
        t_a = None
        if t_lift is not None:
            k = np.flatnonzero((tr < t_lift - CMP_EPS) & (fcn > 0.0))
            t_a = float(tr[k[-1]]) if k.size else None
        lift_basis = {"basis": "bracket_10Hz", "t_a_s": t_a, "t_b_s": t_lift, "normal": n_src}
    else:
        t_lift, lift_basis = None, "C-1 override not_judgeable: L1-R has no 1 ms crawler normal"
    c1 = c1_block(row, t_lift, f_min, asm["C-2"])
    lift = lift_samples(t, pads["N"], t_lift)
    items = {"D8_t_lift_s_D-29_D-30": t_lift, "D8_t_lift_basis": lift_basis, "C1_R40": c1,
             "D8_no_pad_lift_Q-14": lift if t_lift is not None else {"status": "not_judgeable",
                                                                       "reason": str(lift_basis)},
             "moving_pressure_D-32": mp}
    return {"items": items, "grade": None, "grade_note": "N items re-computed; D8 row grade is the bundle judge's"}


# =============================================================================================== batch / CLI
def batch_rows(batch: Path, results_root: Path | None) -> list[tuple[Path, dict[str, Any]]]:
    bj = batch / "batch.json"
    if not bj.exists():
        raise InputError(f"batch.json missing: {batch}")
    doc = json.loads(bj.read_text(encoding="utf-8"))
    root = results_root or batch.parents[1]
    progress = batch / "progress.log"
    progress_text = progress.read_text("utf-8", errors="replace") if progress.is_file() else ""
    out = []
    for c in doc.get("cases") or []:
        name = str(c["case"])
        argv = [str(a) for a in c.get("argv") or []]
        d = batch / name
        located: dict[str, Any] = {"source": "batch_folder"}
        if not (d / "result.json").exists():
            d, located = _rigid_row_dir(name, argv, batch, root, progress_text, c)
        if d is None or not (d / "result.json").exists():
            raise InputError(f"row folder of {name} not found (batch {batch}, results root {root})")
        out.append((d, {**c, "_row_dir": located}))
    return out


def _arg(argv: list[str], opt: str) -> str | None:
    return argv[argv.index(opt) + 1] if opt in argv and argv.index(opt) + 1 < len(argv) else None


ROW_DIR_SLACK_S = 2.0
"""Fallback search (no ``-> <folder>`` line in the case log): a runner folder stamp is accepted within the case's
progress.log START .. END (else batch stamp .. batch stamp + ``wall_s``) widened by this many seconds (the stamp has
1 s resolution and the runner takes it after its own start-up)."""
_STAMP_RE = re.compile(r"_(\d{8}_\d{6})$")


def runner_log_dir(log_text: str) -> str | None:
    """Folder of the last ``batch wall ... -> <dir>`` line of a run_S8C / run_S6C case log (same rule as
    ``s9_batch.s8c_case_check``, which gs-check uses; re-written here so this tool imports no runner module)."""
    return next((ln.split("->", 1)[1].strip() for ln in reversed(log_text.splitlines())
                 if ln.startswith("batch wall") and "->" in ln), None)


def _stamp_time(stamp: str) -> float:
    import datetime as _dt  # noqa: PLC0415

    return _dt.datetime.strptime(stamp, "%Y%m%d_%H%M%S").timestamp()


def _case_window(name: str, progress_text: str, batch: Path, entry: dict[str, Any]) -> tuple[float, float, str]:
    """(start, end, basis) epoch seconds of one case: progress.log ``START`` / ``END`` lines, else the batch stamp
    .. stamp + ``wall_s`` (+ ``est_s`` when no wall)."""
    import datetime as _dt  # noqa: PLC0415

    def last(kind: str) -> float | None:
        m = [x for x in re.finditer(rf"^{kind} {re.escape(name)} (\S+)", progress_text, re.M)]
        return _dt.datetime.fromisoformat(m[-1].group(1)).timestamp() if m else None

    a, b = last("START"), last("END")
    if a is not None and b is not None:
        return a, b, "progress.log START / END"
    m = _STAMP_RE.search(batch.name)
    if m is None:
        raise InputError(f"{name}: no progress.log START / END and no stamp in batch folder name {batch.name}")
    t0 = _stamp_time(m.group(1))
    span = float(entry.get("wall_s") or entry.get("est_s") or 0.0)
    return t0, t0 + span, "batch stamp + wall_s"


def _rigid_row_dir(name: str, argv: list[str], batch: Path, root: Path, progress_text: str,
                   entry: dict[str, Any]) -> tuple[Path | None, dict[str, Any]]:
    """Row folder of a run_S8C / run_S6C row (the runner writes its own batch folder).

    1. The case log ``<batch>/<case>.log``: last ``batch wall ... -> <dir>`` line (:func:`runner_log_dir`), row =
       ``<dir>/<--only>``; a logged folder without ``result.json`` is an InputError (no fallback).
    2. No such line: runner folders matching the ``--tag`` (any stamp) whose stamp lies in the case window
       (:func:`_case_window` +- :data:`ROW_DIR_SLACK_S`); exactly one is used, none or several = InputError.

    Returns (row folder or None when the argv has no ``--tag`` / ``--only``, record of how it was found)."""
    tag, only = _arg(argv, "--tag"), _arg(argv, "--only")
    if tag is None or only is None:
        return None, {"source": None, "reason": "argv has no --tag / --only"}
    log = batch / f"{name}.log"
    logged = runner_log_dir(log.read_text("utf-8", errors="replace")) if log.is_file() else None
    if logged is not None:
        p = Path(logged)
        d = (p if p.is_absolute() else root.parent / p) / only
        if (d / "result.json").exists():
            return d, {"source": "case_log", "log": str(log), "logged_dir": logged}
        # the run wrote into another checkout (a removed worktree) and its results were moved: the same path below
        # the results root (``.../07_results/<rest>`` -> ``<results root>/<rest>``)
        parts = [x.lower() for x in p.parts]
        if root.name.lower() in parts:
            moved = root.joinpath(*p.parts[len(parts) - parts[::-1].index(root.name.lower()):]) / only
            if (moved / "result.json").exists():
                return moved, {"source": "case_log_relocated", "log": str(log), "logged_dir": logged,
                               "results_root": str(root)}
        raise InputError(f"{name}: case log names {logged} but {d / 'result.json'} is missing (also below the "
                         f"results root {root})")
    script = next((Path(a).name for a in argv if a.endswith(".py")), "")
    pats = [f"S8/{tag}_*/{only}"] if script == "run_S8C.py" else [f"S6/*_{tag}_*/{only}", f"S6/*{tag}*/{only}"]
    t_a, t_b, basis = _case_window(name, progress_text, batch, entry)
    hits = []
    for pat in pats:
        for h in sorted(root.glob(pat)):
            m = _STAMP_RE.search(h.parent.name)
            if m and t_a - ROW_DIR_SLACK_S <= _stamp_time(m.group(1)) <= t_b + ROW_DIR_SLACK_S and h not in hits:
                hits.append(h)
    if len(hits) != 1:
        raise InputError(f"{name}: no '-> <folder>' line in {log.name} and {len(hits)} runner folder(s) of tag {tag} "
                         f"in the case window ({basis} +- {ROW_DIR_SLACK_S:g} s): {[str(h) for h in hits]}")
    return hits[0], {"source": "time_window", "window_basis": basis, "slack_s": ROW_DIR_SLACK_S,
                     "log": str(log) if log.is_file() else None}


def seal_check(rules_dir: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"rules_dir": str(rules_dir), "files": {}, "ok": True, "missing": []}
    for name, want in RULES_SEALS.items():
        md, sf = rules_dir / name, rules_dir / name.replace(".md", ".sha256")
        if not md.exists() or not sf.exists():
            out["missing"].append(name)
            out["ok"] = False
            continue
        got = sha256_file(md)
        sealed = sf.read_text(encoding="utf-8").split()[0]
        ok = got == want == sealed
        out["files"][name] = {"sha256": got, "sealed": sealed, "tool": want, "ok": ok}
        out["ok"] &= ok
    return out


def disclose(root: Path = ROOT) -> dict[str, Any]:
    new = Path(__file__).resolve()
    out = {"new": new.relative_to(root).as_posix() if new.is_relative_to(root) else str(new), "pairs": []}
    for rel, scope in DISCLOSE_PAIRS:
        old = root / rel
        entry: dict[str, Any] = {"old": rel, "scope": scope}
        if not old.exists():
            entry["error"] = "old file missing"
        else:
            try:
                r = subprocess.run(["git", "diff", "--no-index", "--numstat", "--", str(old), str(new)],
                                   capture_output=True, text=True, timeout=60, cwd=root)
                parts = r.stdout.split()
                entry.update(added=int(parts[0]), deleted=int(parts[1]), old_sha256=sha256_file(old))
            except (OSError, subprocess.SubprocessError, ValueError, IndexError) as e:
                entry["error"] = f"git diff failed: {type(e).__name__}"
        out["pairs"].append(entry)
    out["new_sha256"] = sha256_file(new)
    return out


def parse_assumptions(items: list[str]) -> dict[str, str]:
    asm = dict(ASSUMPTIONS)
    for it in items:
        k, _, v = it.partition("=")
        k = k.strip()
        if k not in asm or not v:
            raise InputError(f"--assume {it!r}: unknown key or empty value")
        if k in ASSUMPTION_CHOICES and v not in ASSUMPTION_CHOICES[k]:
            raise InputError(f"--assume {k}: {v!r} not in {ASSUMPTION_CHOICES[k]}")
        asm[k] = v
    return asm


def cmd_judge(args) -> tuple[int, dict[str, Any]]:
    asm = parse_assumptions(args.assume or [])
    params = load_params(Path(args.params))
    seals = seal_check(Path(args.rules_dir))
    if seals["missing"]:
        raise InputError(f"rules files missing: {seals['missing']}")
    targets: list[tuple[Path, dict[str, Any] | None]] = []
    for b in args.batch or []:
        targets += batch_rows(Path(b), Path(args.results_root) if args.results_root else None)
    for r in args.row or []:
        targets.append((Path(r), None))
    if not targets:
        raise InputError("no --batch / --row given")
    rows, stops, origin_bad, skipped = [], [], [], []
    for d, meta in targets:
        row = load_row(d)
        crit = (meta or {}).get("criteria_id")
        if row["engine"] == "openloop" or str(crit) in OPENLOOP_CRITERIA:
            skipped.append({"dir": str(d), "case": (meta or {}).get("case", row["name"]), "engine": row["engine"],
                            "criteria_id": crit, "inputs": row["files"], "row_dir": (meta or {}).get("_row_dir"),
                            "skipped": "openloop_not_judged_here", "rule": OPENLOOP_SKIP_RULE,
                            "note": "C-6 / C-7 values: result.json p3a (path 1) and openloop_compare.py analyse "
                                    "(path 2); this tool reads neither"})
            continue
        rid = row_id_of(row, meta)
        if row["engine"] == "SCM":
            body = judge_scm(row, rid, params, asm)
        else:
            body = judge_rigid(row, params, asm)
        oc = origin_check(row)
        entry = {"dir": str(d), "case": (meta or {}).get("case", row["name"]), "engine": row["engine"], "row_id": rid,
                 "criteria_id": (meta or {}).get("criteria_id"), "t0_s": row["t0"], "inputs": row["files"],
                 "row_dir": (meta or {}).get("_row_dir"), "origin_check_R5_B1": oc, **body}
        if body["items"].get("C1_R40", {}).get("stop"):
            stops.append({"case": entry["case"], "reason": "R40-2 hold (not judgeable, ask)"})
        if oc["ok"] is False:
            origin_bad.append(entry["case"])
        rows.append(entry)
    tds = [r["items"]["departure_t_D"] for r in rows if r["engine"] == "SCM"]
    td_diff = [abs(x["diff_from_runner_s"]) for x in tds if x.get("diff_from_runner_s") is not None]
    deviates = {k: v for k, v in asm.items() if ASSUMPTIONS[k] != v}
    doc = {"tool": TOOL_VERSION, "rules": "v5_resume_4368_rules.md + rev1 .. rev6 (rev5 R5-A1, rev6 R6-A / R6-B)",
           "definitions_C": asm, "deviates_from_rev6": deviates or None, "d_numbers": D_NUMBERS,
           "params": params, "seals": seals, "disclosure": disclose(), "rows": rows, "stops": stops,
           "origin_failed": origin_bad, "skipped_rows": skipped,
           "t_D_vs_runner_R6_B4": {"scm_rows": len(tds), "rows_differing": sum(1 for x in tds if x["differs_from_runner"]),
                                   "max_abs_diff_s": max(td_diff) if td_diff else None},
           "demoted_items": {r["case"]: r.get("demoted_items") for r in rows if r.get("demoted_items")}}
    code = 0 if seals["ok"] and not stops and not origin_bad else 1
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=_json_default) + "\n",
                              encoding="utf-8", newline="\n")
    summary = {"rows": len(rows), "seals_ok": seals["ok"], "stops": len(stops), "origin_failed": len(origin_bad),
               "deviates_from_rev6": sorted(deviates),
               "grades": {r["case"]: r.get("grade") for r in rows},
               "skipped": {s["case"]: s["skipped"] for s in skipped}, "out": str(args.out)}
    return code, summary


def _json_default(x: Any) -> Any:
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return str(x)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    j = sub.add_parser("judge")
    j.add_argument("--out", required=True)
    j.add_argument("--batch", action="append")
    j.add_argument("--row", action="append")
    j.add_argument("--results-root")
    j.add_argument("--rules-dir", default=str(RULES_DIR_DEFAULT))
    j.add_argument("--params", default=str(ROOT / "02_params" / "rexome33.yaml"))
    j.add_argument("--assume", action="append", help="C-n=value (see ASSUMPTIONS)")
    d = sub.add_parser("disclose")
    d.add_argument("--out")
    s = sub.add_parser("seals")
    s.add_argument("--rules-dir", default=str(RULES_DIR_DEFAULT))
    return ap


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as e:
        code = 0 if e.code == 0 else 2
        print("errors", 0 if code == 0 else 1)
        print(json.dumps({"exit": code, "error": "argument error" if code else None}))
        return code
    try:
        if args.cmd == "judge":
            code, summary = cmd_judge(args)
        elif args.cmd == "disclose":
            summary = disclose()
            if args.out:
                Path(args.out).write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8", newline="\n")
            code = 0 if not any("error" in p for p in summary["pairs"]) else 1
        else:
            summary = seal_check(Path(args.rules_dir))
            code = 2 if summary["missing"] else (0 if summary["ok"] else 1)
    except InputError as e:
        print("errors 1")
        print(json.dumps({"exit": 2, "error": str(e)}, ensure_ascii=False))
        return 2
    except Exception as e:  # noqa: BLE001 - exit 3 with the trace on stderr
        traceback.print_exc()
        print("errors 1")
        print(json.dumps({"exit": 3, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        return 3
    print("errors", 0 if code == 0 else 1)
    print(json.dumps({"exit": code, **summary}, ensure_ascii=False, default=_json_default))
    return code


if __name__ == "__main__":
    sys.exit(main())
