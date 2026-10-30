"""Would the P-S8-38 ZIC (c 0.5) have acted on a recorded Chrono S9 run? (control spec 431.2)

The 10-26 P3b batch (``07_results/S9/batch_P3b_20261026_122444``, 24 cases) has no
``r8_series.npz``, so the control record scan (``ctrl-final/feature_scan.py``) left its ZIC
column empty. This script rebuilds the attitude PI of spec 429.1 from what those runs do have and
applies the ZIC rule of spec 429.3 offline (record only, no re-run).

Reconstruction (spec 429.1, as ``feature_scan.zic_scan``):
  attitude -> 10 ms box means (100 Hz) -> 2 x first-order low pass tau 0.8 s (Euler, 100 Hz)
  -> 10 Hz PI at the period start sample, e = -attitude (target 0), integrate an axis while
  0.01 deg < |e_axis| and max |e| < 0.2 deg (joint band), |I| <= 0.02 rad s, I = 0 before the
  first LEVEL entry, kept through DONE / PROBE; ZIC window = first LOC up to the first READY,
  LEVEL periods; cut ``I <- sign(I) I_cap`` when sign(I) != sign(e) and |I| > I_cap,
  I_cap = 0.5 x 0.03 deg x Kp / Ki.
Two attitude sources per case:
  ``1khz``  ``step_series.npz`` ``roll_pitch_deg`` (1 kHz true attitude; the 10-26 runs have it,
            only the 10 Hz phase file is missing). Phases come from ``result.json`` ``s9_rows``
            ``c2_phase`` (the same 10 Hz rows as ``r8_series.npz`` ``phase``).
  ``10hz``  ``s9_rows`` ``roll_pitch_deg`` (10 Hz instants) linearly interpolated to 100 Hz, the
            approximation a run without the 1 kHz file would need. Its error is measured
            against ``1khz`` on every case.
Checks per case:
  command fit  the reconstructed PI rate (unclamped) against the pitch / roll antisymmetric
               part of the recorded leg commands (``controller_commands.npz``) over the LEVEL
               periods from the first LOC to the first DONE; R^2, lever, lag (0 / 1 period).
  margin       peak |I| / I_cap over the window periods where I pushes past the target (the
               value a clamp compares; 1.0 = the clamp threshold).
  sign margin  the ZIC sign test flips when e crosses 0, so a clamp usually fires at a tiny
               |e|. "acted" is robust when the free integral also pushes past the target with
               |e| >= ``SIGN_MARGIN_DEG`` and |I| > 1.2 I_cap somewhere in the window;
               "not acted" is robust when no uncut period has |I| > I_cap at |e| below the
               margin (validation: S9SL C3, 1 kHz none, 10 Hz one clamp).
Confidence: "high" = 1 kHz source, both sources give the same verdict, pitch fit R^2 >= 0.95,
the margin at least ``MARGIN_CLEAR`` away from 1 and no sign sensitivity; "medium" = same
verdict but one of these missed; "low" = the sources disagree or no fit.
Validation (``--validate``): the cases of the control scan with ``r8_series.npz``; the
``1khz`` path must give the scan's clamp count (same method), and the ``10hz`` path error is
reported as the reference for the approximation.

Usage (project root):
  python -I p38_p3b_recon.py [--out JSON] [--scan SCAN_JSON] [CASE_DIR ...]
Units SI unless the key says otherwise (deg, mm/s).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_BATCH = ROOT / "07_results" / "S9" / "batch_P3b_20261026_122444"
DEFAULT_OUT = ROOT / "06_analysis" / "02_control" / "s9" / "rev85" / "p38_p3b_recon.json"
RESULTS_ROOT = ROOT / "07_results" / "S9"

ATTITUDE_KP_1_S = 0.2
ATTITUDE_KI_1_S2 = 0.01
DONE_ATTITUDE_RAD = math.radians(0.03)
CAP_FRACTION = 0.5
INTEGRAL_CAP = CAP_FRACTION * DONE_ATTITUDE_RAD * ATTITUDE_KP_1_S / ATTITUDE_KI_1_S2
INTEGRAL_LIMIT_RAD_S = 0.02
JOINT_BAND_RAD = (math.radians(0.01), math.radians(0.2))
FILTER_TAU_S = 0.8
FILTER_STAGES = 2
FILTER_PERIOD_S = 0.01
CONTROL_PERIOD_S = 0.1
STEPS_PER_FILTER_SAMPLE = 10
TIME_EPS_S = 1e-9
AXES = ("roll", "pitch")

MARGIN_CLEAR = 0.2
"""|peak ratio - 1| at or above this: the verdict does not hinge on the reconstruction error."""
SIGN_MARGIN_DEG = 0.0025
"""Attitude error band where the ZIC sign test is not trusted: above the largest 10 Hz vs 1 kHz
filtered-attitude difference of the validation cases (0.0021 deg) and the 429.1 deviation
reconstruction error (max 0.0014 deg). A first clamp at |e| below it, or an uncut period with
|I| > I_cap and |e| below it, makes the verdict sign-sensitive."""
FIT_R2_MIN = 0.95
FIT_LAGS = (0, 1)
LEG_SIGNS_PITCH = np.array([0.5, 0.5, -0.5, -0.5])
"""Front minus rear mean of the leg commands, order FL, FR, RL, RR."""
LEG_SIGNS_ROLL = np.array([0.5, -0.5, 0.5, -0.5])
"""Left minus right mean of the leg commands."""

LOC_EVENT = "crawler_liftoff_confirmed"
PHASE_LEVEL = "level"
PHASE_READY = "ready"
PHASE_DONE = "done"


# --------------------------------------------------------------------------------- loading
@dataclass(frozen=True)
class CaseRecord:
    """What the reconstruction reads from one Chrono S9 case folder."""

    name: str
    control_t_s: np.ndarray
    control_phase: tuple[str, ...]
    control_attitude_deg: np.ndarray
    fine_t_s: np.ndarray | None
    fine_attitude_deg: np.ndarray | None
    t_level0_s: float | None
    t_first_loc_s: float | None
    t_first_ready_s: float | None
    t_first_done_s: float | None
    command_t_s: np.ndarray | None
    command_u_m_s: np.ndarray | None
    imu_grade: str | None


def _first_time(pairs, name: str) -> float | None:
    return next((t_s for t_s, label in pairs if label == name), None)


def load_case(case_dir: Path) -> CaseRecord:
    """Read result.json rows, the 1 kHz step series and the leg commands of one case."""
    result = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    rows = result["s9_rows"]
    phases = [(float(p["t_s"]), p["phase"]) for p in result.get("phases") or []]
    events = [(float(e["t_s"]), e["name"]) for e in result.get("events") or []]
    fine_t_s = fine_attitude_deg = None
    step_path = case_dir / "step_series.npz"
    if step_path.exists():
        with np.load(step_path, allow_pickle=False) as series:
            fine_t_s = np.asarray(series["t_s"], dtype=float)
            fine_attitude_deg = np.asarray(series["roll_pitch_deg"], dtype=float)
    command_t_s = command_u = None
    command_path = case_dir / "controller_commands.npz"
    if command_path.exists():
        with np.load(command_path, allow_pickle=False) as commands:
            command_t_s = np.asarray(commands["t_s"], dtype=float)
            command_u = np.asarray(commands["issued_u_m_s"], dtype=float)
    return CaseRecord(
        name=f"{case_dir.parent.name}/{case_dir.name}",
        control_t_s=np.array([float(r["t_s"]) for r in rows]),
        control_phase=tuple(str(r["c2_phase"]).lower() for r in rows),
        control_attitude_deg=np.array([r["roll_pitch_deg"] for r in rows], dtype=float),
        fine_t_s=fine_t_s, fine_attitude_deg=fine_attitude_deg,
        t_level0_s=_first_time(phases, PHASE_LEVEL),
        t_first_loc_s=_first_time(events, LOC_EVENT),
        t_first_ready_s=_first_time(phases, PHASE_READY),
        t_first_done_s=_first_time(phases, PHASE_DONE),
        command_t_s=command_t_s, command_u_m_s=command_u,
        imu_grade=(result.get("args") or {}).get("imu_grade"))


# ------------------------------------------------------------------------- attitude filter
def _two_stage_low_pass(samples: np.ndarray) -> np.ndarray:
    """The completion / PI attitude filter: FILTER_STAGES Euler first-order stages at 100 Hz."""
    gain = FILTER_PERIOD_S / FILTER_TAU_S
    stages = [samples[0].copy() for _ in range(FILTER_STAGES)]
    out = np.empty_like(samples)
    out[0] = samples[0]
    for k in range(1, len(samples)):
        value = samples[k]
        for stage in stages:
            stage += gain * (value - stage)
            value = stage
        out[k] = value
    return out


def filtered_from_fine(t_s: np.ndarray, attitude_deg: np.ndarray):
    """(100 Hz times, filtered attitude rad) from the 1 kHz series (10 ms box means)."""
    n_boxes = len(t_s) // STEPS_PER_FILTER_SAMPLE
    used = n_boxes * STEPS_PER_FILTER_SAMPLE
    box_t_s = t_s[STEPS_PER_FILTER_SAMPLE - 1:used:STEPS_PER_FILTER_SAMPLE]
    boxes = np.radians(attitude_deg[:used]).reshape(n_boxes, STEPS_PER_FILTER_SAMPLE, 2)
    return box_t_s, _two_stage_low_pass(boxes.mean(axis=1))


def filtered_from_control_rows(t_s: np.ndarray, attitude_deg: np.ndarray):
    """(100 Hz times, filtered attitude rad) from the 10 Hz instants, linearly interpolated."""
    grid_t_s = np.arange(t_s[0], t_s[-1] + TIME_EPS_S, FILTER_PERIOD_S)
    attitude_rad = np.radians(attitude_deg)
    samples = np.column_stack([np.interp(grid_t_s, t_s, attitude_rad[:, axis])
                               for axis in range(2)])
    return grid_t_s, _two_stage_low_pass(samples)


# ------------------------------------------------------------------------------ PI replay
@dataclass
class PiTrace:
    """10 Hz PI reconstruction of one attitude source (unclamped and ZIC-clamped)."""

    error_rad: np.ndarray
    integral_free: np.ndarray
    integral_zic: np.ndarray
    clamps: list
    peak_ratio: float
    """Peak |I| / I_cap where I pushes past the target inside the window (0 when never)."""
    near_flip_periods: int
    """Window periods with |I| > I_cap and |e| < SIGN_MARGIN_DEG that were not cut: a small
    attitude error could flip the sign test there and add a clamp."""
    robust_clamp_periods: int
    """Window periods where the free integral pushes past the target with |e| >=
    SIGN_MARGIN_DEG and |I| > (1 + MARGIN_CLEAR) I_cap: a clamp no sub-margin error removes
    (the ZIC integral equals the free one up to the first cut)."""


def _integrate(integral: np.ndarray, error: np.ndarray) -> None:
    joint_error = float(np.abs(error).max())
    for axis in range(2):
        if JOINT_BAND_RAD[0] < abs(error[axis]) and joint_error < JOINT_BAND_RAD[1]:
            integral[axis] = np.clip(integral[axis] + error[axis] * CONTROL_PERIOD_S,
                                     -INTEGRAL_LIMIT_RAD_S, INTEGRAL_LIMIT_RAD_S)


def _is_opposing(error: float, integral: float) -> bool:
    return error != 0.0 and integral != 0.0 and np.sign(integral) != np.sign(error)


def replay_pi(case: CaseRecord, filter_t_s: np.ndarray, filtered_rad: np.ndarray) -> PiTrace:
    """Run the 10 Hz PI twice (free, with the ZIC) on one filtered attitude source."""
    n_periods = len(case.control_t_s)
    sample_index = np.clip(np.searchsorted(filter_t_s, case.control_t_s - TIME_EPS_S),
                           0, len(filter_t_s) - 1)
    window_end_s = case.t_first_ready_s if case.t_first_ready_s is not None else math.inf
    free, zic = np.zeros(2), np.zeros(2)
    errors = np.zeros((n_periods, 2))
    free_trace, zic_trace = np.zeros((n_periods, 2)), np.zeros((n_periods, 2))
    clamps, peak_ratio, near_flip_periods, robust_clamp_periods = [], 0.0, 0, 0
    sign_margin_rad = math.radians(SIGN_MARGIN_DEG)
    robust_level = (1.0 + MARGIN_CLEAR) * INTEGRAL_CAP
    for k, t_s in enumerate(case.control_t_s):
        if case.t_level0_s is None or t_s < case.t_level0_s - TIME_EPS_S:
            free[:], zic[:] = 0.0, 0.0
        elif case.control_phase[k] == PHASE_LEVEL:
            error = -filtered_rad[sample_index[k]]
            errors[k] = error
            _integrate(free, error)
            _integrate(zic, error)
            in_window = (case.t_first_loc_s is not None
                         and case.t_first_loc_s - TIME_EPS_S <= t_s < window_end_s)
            for axis in range(2) if in_window else ():
                robust_clamp_periods += int(_is_opposing(error[axis], free[axis])
                                            and abs(error[axis]) >= sign_margin_rad
                                            and abs(free[axis]) > robust_level)
                if not _is_opposing(error[axis], zic[axis]):
                    is_near = abs(zic[axis]) > INTEGRAL_CAP and abs(error[axis]) < sign_margin_rad
                    near_flip_periods += int(is_near)
                    continue
                peak_ratio = max(peak_ratio, abs(zic[axis]) / INTEGRAL_CAP)
                if abs(zic[axis]) > INTEGRAL_CAP:
                    clamps.append({"t_s": round(float(t_s), 2), "axis": AXES[axis],
                                   "before": round(float(zic[axis]), 6),
                                   "error_deg": round(math.degrees(float(error[axis])), 5)})
                    zic[axis] = math.copysign(INTEGRAL_CAP, zic[axis])
        free_trace[k], zic_trace[k] = free, zic
    return PiTrace(errors, free_trace, zic_trace, clamps, peak_ratio, near_flip_periods,
                   robust_clamp_periods)


# ---------------------------------------------------------------------------- checks
def _fit_window(case: CaseRecord) -> np.ndarray:
    """LEVEL periods from the first LOC to the first DONE (READY when no DONE)."""
    end_s = case.t_first_done_s if case.t_first_done_s is not None else case.t_first_ready_s
    if case.t_first_loc_s is None:
        return np.zeros(len(case.control_t_s), dtype=bool)
    end_s = math.inf if end_s is None else end_s
    is_level = np.array([phase == PHASE_LEVEL for phase in case.control_phase])
    in_time = (case.control_t_s >= case.t_first_loc_s - TIME_EPS_S) & (case.control_t_s < end_s)
    return is_level & in_time


def _linear_fit(x: np.ndarray, y: np.ndarray) -> dict:
    design = np.column_stack([x, np.ones_like(x)])
    (slope, offset), *_ = np.linalg.lstsq(design, y, rcond=None)
    residual = y - design @ np.array([slope, offset])
    spread = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum(residual ** 2)) / spread if spread > 0.0 else float("nan")
    return {"lever_m": float(slope), "offset_mm_s": float(offset) * 1e3, "r2": r2}


def command_fit(case: CaseRecord, trace: PiTrace) -> dict | None:
    """Reconstructed PI rate (free) against the antisymmetric leg commands, best lag."""
    if case.command_u_m_s is None:
        return None
    window = _fit_window(case)
    if window.sum() < 10:
        return None
    rate = ATTITUDE_KP_1_S * trace.error_rad + ATTITUDE_KI_1_S2 * trace.integral_free
    command_index = np.searchsorted(case.command_t_s, case.control_t_s - TIME_EPS_S)
    best = None
    for lag in FIT_LAGS:
        index = command_index + lag
        usable = window & (index < len(case.command_t_s))
        commands = case.command_u_m_s[index[usable]]
        fits = {"lag_periods": lag, "n": int(usable.sum()),
                "pitch": _linear_fit(rate[usable, 1], commands @ LEG_SIGNS_PITCH),
                "roll": _linear_fit(rate[usable, 0], commands @ LEG_SIGNS_ROLL)}
        if best is None or fits["pitch"]["r2"] > best["pitch"]["r2"]:
            best = fits
    return best


def _first_clamp_times(clamps: list) -> dict[str, float]:
    first: dict[str, float] = {}
    for clamp in clamps:
        first.setdefault(clamp["axis"], clamp["t_s"])
    return first


def source_difference(case: CaseRecord, fine: PiTrace, coarse: PiTrace) -> dict:
    """Error of the 10 Hz source against the 1 kHz one (LEVEL periods from the first LEVEL)."""
    used = np.array([phase == PHASE_LEVEL for phase in case.control_phase])
    if not used.any():
        return {"n_level_periods": 0}
    fine_times = _first_clamp_times(fine.clamps)
    coarse_times = _first_clamp_times(coarse.clamps)
    first_shift = {axis: round(coarse_times[axis] - fine_times[axis], 2)
                   for axis in AXES if axis in fine_times and axis in coarse_times}
    return {
        "n_level_periods": int(used.sum()),
        "error_max_abs_deg": float(np.degrees(
            np.abs(fine.error_rad[used] - coarse.error_rad[used]).max())),
        "integral_max_abs_rad_s": float(np.abs(fine.integral_free[used]
                                               - coarse.integral_free[used]).max()),
        "integral_max_abs_over_cap": float(np.abs(fine.integral_free[used]
                                                  - coarse.integral_free[used]).max()
                                           / INTEGRAL_CAP),
        "peak_ratio_difference": coarse.peak_ratio - fine.peak_ratio,
        "first_clamp_shift_s": first_shift,
    }


def _sign_sensitivity(trace: PiTrace) -> str | None:
    """Reason text when the verdict hinges on the sign of a sub-margin attitude error."""
    if trace.clamps and not trace.robust_clamp_periods:
        return "every clamp needs |e| < margin or |I| < 1.2 I_cap (free integral)"
    if not trace.clamps and trace.near_flip_periods:
        return f"{trace.near_flip_periods} uncut periods with |I| > I_cap at |e| < margin"
    return None


def judge_confidence(trace: PiTrace, sources_agree: bool, fit: dict | None,
                     has_fine: bool) -> tuple[str, list[str]]:
    """("high" | "medium" | "low", reasons for a lower level)."""
    if not sources_agree:
        return "low", ["10 Hz and 1 kHz sources disagree"]
    reasons = []
    if not has_fine:
        reasons.append("10 Hz source only")
    if fit is None:
        return "low", [*reasons, "no command fit"]
    if not fit["pitch"]["r2"] >= FIT_R2_MIN:
        reasons.append(f"pitch fit R2 {fit['pitch']['r2']:.3f} < {FIT_R2_MIN}")
    if abs(trace.peak_ratio - 1.0) < MARGIN_CLEAR:
        side = "above" if trace.clamps else "below"
        reasons.append(f"peak |I|/I_cap {trace.peak_ratio:.2f} {side} 1 by < {MARGIN_CLEAR}")
    sign_reason = _sign_sensitivity(trace)
    if sign_reason:
        reasons.append(sign_reason)
    return ("high" if not reasons else "medium"), reasons


# ------------------------------------------------------------------------------- driver
def analyse_case(case_dir: Path) -> dict:
    """Both reconstructions, the checks and the verdict of one case."""
    case = load_case(case_dir)
    coarse = replay_pi(case, *filtered_from_control_rows(case.control_t_s,
                                                         case.control_attitude_deg))
    has_fine = case.fine_t_s is not None
    fine = replay_pi(case, *filtered_from_fine(case.fine_t_s, case.fine_attitude_deg)) \
        if has_fine else None
    primary = fine if has_fine else coarse
    acted = bool(primary.clamps)
    sources_agree = (not has_fine) or (bool(coarse.clamps) == acted)
    fit = command_fit(case, primary)
    confidence, reasons = judge_confidence(primary, sources_agree, fit, has_fine)
    return {
        "case": case.name, "imu_grade": case.imu_grade,
        "t_level0_s": case.t_level0_s, "t_first_loc_s": case.t_first_loc_s,
        "t_first_done_s": case.t_first_done_s, "t_first_ready_s": case.t_first_ready_s,
        "primary_source": "1khz" if has_fine else "10hz",
        "zic_acted": acted, "zic_clamps": len(primary.clamps),
        "zic_first": primary.clamps[:3], "peak_ratio": round(primary.peak_ratio, 4),
        "near_flip_periods": primary.near_flip_periods,
        "robust_clamp_periods": primary.robust_clamp_periods,
        "coarse_10hz": {"zic_acted": bool(coarse.clamps), "zic_clamps": len(coarse.clamps),
                        "zic_first": coarse.clamps[:3],
                        "peak_ratio": round(coarse.peak_ratio, 4)},
        "approximation_error_10hz": source_difference(case, fine, coarse) if has_fine else None,
        "command_fit": fit,
        "confidence": confidence, "confidence_reasons": reasons,
    }


def _scan_cases(scan_path: Path) -> list[tuple[Path, int | None]]:
    """(case dir, scan clamp count) of the control scan rows that had ``r8_series.npz``."""
    rows = json.loads(scan_path.read_text(encoding="utf-8"))
    out = []
    for row in rows:
        if row.get("ZIC_clamps") is None:
            continue
        out.append((RESULTS_ROOT / row["case"], row["ZIC_clamps"]))
    return out


def validate(scan_path: Path) -> dict:
    """The 1 kHz path against the scan counts and the 10 Hz approximation error on the cases
    with a 10 Hz phase file."""
    rows = []
    for case_dir, scan_clamps in _scan_cases(scan_path):
        result = analyse_case(case_dir)
        error = result["approximation_error_10hz"] or {}
        rows.append({"case": result["case"], "scan_clamps": scan_clamps,
                     "clamps_1khz": result["zic_clamps"],
                     "clamps_10hz": result["coarse_10hz"]["zic_clamps"],
                     "verdict_1khz": result["zic_acted"],
                     "verdict_10hz": result["coarse_10hz"]["zic_acted"],
                     "peak_ratio_1khz": result["peak_ratio"],
                     "peak_ratio_10hz": result["coarse_10hz"]["peak_ratio"],
                     "integral_max_abs_over_cap": error.get("integral_max_abs_over_cap"),
                     "error_max_abs_deg": error.get("error_max_abs_deg"),
                     "pitch_fit_r2": (result["command_fit"] or {}).get("pitch", {}).get("r2"),
                     "near_flip_periods_1khz": result["near_flip_periods"],
                     "confidence": result["confidence"],
                     "confidence_reasons": result["confidence_reasons"]})
    over_cap = [r["integral_max_abs_over_cap"] for r in rows
                if r["integral_max_abs_over_cap"] is not None]
    ratio_diff = [float(abs(r["peak_ratio_10hz"] - r["peak_ratio_1khz"])) for r in rows]
    return {"n": len(rows),
            "clamp_count_equals_scan": sum(r["clamps_1khz"] == r["scan_clamps"] for r in rows),
            "verdict_10hz_equals_1khz": sum(r["verdict_10hz"] == r["verdict_1khz"]
                                            for r in rows),
            "integral_diff_over_cap_max": max(over_cap, default=None),
            "peak_ratio_abs_diff_max": max(ratio_diff, default=None),
            "rows": rows}


def summarise(rows: list[dict]) -> dict:
    acted = [r["case"].split("/")[-1] for r in rows if r["zic_acted"]]
    return {"n": len(rows), "acted": len(acted), "not_acted": len(rows) - len(acted),
            "acted_cases": acted,
            "confidence": {level: sum(r["confidence"] == level for r in rows)
                           for level in ("high", "medium", "low")},
            "sources_disagree": [r["case"] for r in rows
                                 if r["coarse_10hz"]["zic_acted"] != r["zic_acted"]]}


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cases", nargs="*", type=Path,
                        help=f"case folders (default: every case of {DEFAULT_BATCH.name})")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--scan", type=Path, default=None,
                        help="control scan.json: validate on its cases with r8_series.npz")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    case_dirs = args.cases or sorted(p for p in DEFAULT_BATCH.iterdir() if p.is_dir())
    rows = []
    for case_dir in case_dirs:
        row = analyse_case(case_dir)
        rows.append(row)
        print(row["case"], row["zic_acted"], row["zic_clamps"], row["peak_ratio"],
              row["confidence"], flush=True)
    payload = {
        "meta": {
            "script": "04_scripts/03_control/s9/p38_p3b_recon.py", "spec": "431.2, 429.1, 429.3",
            "rule": {"cap_fraction": CAP_FRACTION, "integral_cap_rad_s": INTEGRAL_CAP,
                     "kp_1_s": ATTITUDE_KP_1_S, "ki_1_s2": ATTITUDE_KI_1_S2,
                     "done_attitude_deg": math.degrees(DONE_ATTITUDE_RAD),
                     "joint_band_deg": [math.degrees(v) for v in JOINT_BAND_RAD],
                     "integral_limit_rad_s": INTEGRAL_LIMIT_RAD_S,
                     "filter": f"{FILTER_STAGES} x tau {FILTER_TAU_S} s Euler at 100 Hz"},
            "sources": {"1khz": "step_series.npz roll_pitch_deg, 10 ms box means",
                        "10hz": "result.json s9_rows roll_pitch_deg, linear to 100 Hz",
                        "phases": "result.json s9_rows c2_phase (= r8_series phase)"},
            "confidence_rule": {"margin_clear": MARGIN_CLEAR, "fit_r2_min": FIT_R2_MIN},
            "note": ("the 10-26 runs carry the 1 kHz true attitude; only r8_series.npz is "
                     "missing. The true attitude ignores the IMU grade error of the run."),
        },
        "summary": summarise(rows),
        "validation": validate(args.scan) if args.scan else None,
        "cases": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=1))
    if payload["validation"]:
        validation = payload["validation"]
        print({k: v for k, v in validation.items() if k != "rows"})
    print("->", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
