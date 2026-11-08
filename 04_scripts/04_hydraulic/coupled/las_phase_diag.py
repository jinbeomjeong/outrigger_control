"""LAS-b phase diagnosis on the reduced harness (FB rejected, user decision 2026-11-08).

Pre-registration: ``06_analysis/02_control/verif_matrix/las_phase_diag_plan.md`` (control-expert,
sealed; sha256 :data:`PLAN_SHA256`). Where this text and the plan differ, the plan wins. ``run``
and ``judge`` stop with exit 2 when the plan file is missing or has another sha256.

Background (``fb_judgement.md``, control-expert): on the G-3 keys
``D1|H-R-A|rigid+J1@FR|T|diag-op|K3|{VB,V0}|e0.002`` the FB budget delays the TOUCH end, LAS-b
(03_src ``C2Config.with_10hz_d1().liftoff_approach_slow``) starts one sample later and the RL
minimum falls. This tool records why, without changing a command.

Bundles (one line per run):
  D-a  4 runs: the two G-3 keys x {L (no FB), LF (FB rev3 on, ``fb_targeted`` wrapper)}.
  D-b 30 runs (plan 1): the two G-3 keys x candidate ``LT`` (TOUCH-only budget) on the grid
       centre s_c in {1.0, 0.94, s_nom} x j = 0..4. ``LT`` installs no FB wrapper (detection
       U / A97 off); a ramp hook scales the ramp output by ``fb_targeted.budget_output`` with
       ``Q_b = s Q(4 v_max)`` only in a period whose phase is TOUCH at the ramp (any other
       phase: no budget, as L). The ramp output and ``previous_output_m_s`` are handled as the
       FB wrapper does, so A-2 can reproduce LF bit for bit.
         s_{c,j} = s_c T_c / (T_c + j delta),  T_c = T_1 / s_c,  delta = 0.025 s,
         T_1 = 165 x 0.1 x 0.8768421 = 14.468 s (plan 1.2).
       The budget is computed as ``base x T_c / (T_c + j delta)`` with base = Q(4 v_max) for
       s_c = 1.0, 0.94 Q(4 v_max) for 0.94 and the LF nominal ``Q_nom`` itself for the s_nom
       centre (plan "0.8768421" = ``Q_nom / Q(4 v_max)`` of the YAML, recorded as ``s_nom``):
       j = 0 of that centre is then exactly the LF budget. Every acted period is counted by the
       phase at the end of its update; ``level_budget_periods`` != 0 marks the line
       ``excluded`` (plan 1.1: a tool defect candidate).
       Anchors (plan 1.3, checked by ``judge``): A-1 s_c 1.0 j 0 = stored L (b0 act,
       ``las_T1.jsonl``) hash, A-2 s_nom j 0 = stored ``fb_F2.jsonl`` LF hash (both keys).
  D-c  2 runs (optional): verdict key ``S5|V0|etadef|e0.002`` (F-1) x {L, LF}, last LOC ~ DONE.
Run path: ``run_v5.run_one`` (D-1 branch for the G-3 keys, verdict branch for S5), spawned
workers with ``maxtasksperchild=1``; ``fb_targeted._install_candidate`` checks the thread
variables and that the preset has LAS-b ``b0`` on and installs the FB wrapper for LF; then this
tool's hooks.

The recorder (``diag.record`` true) patches, in the worker only and after FB:
  ``C2Controller.update`` (outermost), ``C2Controller._apply_liftoff_approach_slow``,
  ``C2Controller._apply_output_ramp`` (D-b only: the TOUCH budget) and the module function
  ``fb_targeted.budget_output`` (record of every budget call). Each record hook calls the
  original with the same arguments, returns its result object unchanged, copies what it reads
  and calls only reading methods (``_load_estimate_N``, ``_diff_sink_rates_m_s``,
  ``plant.attitude``). Lazily created controller states are read as attributes.
  ``--no-record`` keeps only the D-b budget hook (the on / off command hash check).

Line = the ``run_v5`` line (``commands_sha256``, ``d1``, ``values`` ...) + ``fb``
(``fb_targeted._fb_block``) + ``las`` (``las_block_of``) + ``diag``:
  key, bundle, candidate (``L`` / ``LF`` / ``LT-c<centre>-j<j>``), record, identity (commit,
  ``code_diff_sha256``, tool sha256 with this file and ``las_phase_judge.py``, threads,
  ``plan_sha256``), touch_budget (D-b: centre, j, s, s_c, s_nom, T_1_s, T_c_s,
  Q_b_L_min, Q_full_L_min, Q_nom_L_min, acted_by_end_phase, level_budget_periods, excluded),
  window {t0_s, t1_s, rule}: D-a / D-b first TOUCH end - 0.5 s .. first LOC after it + 2 s
      (no LOC: run end); D-c last LOC onset - 0.5 s .. first DONE after it + 1 s,
  summary (plan 2): F_RL_kN (RL minimum of the 1 ms true force after the lift-off,
      ``values.forces.t_lift_s``), t_RL_min_s, min_leg_after_lift, min_after_lift_kN,
      F_judged_min_kN (``d1``, all legs, D8), t_touch_end_s, t_lift_s, t_las_start_s,
      las_start_period (periods from the TOUCH end), las_start_rho, las_start_rho_prev,
      las_active_periods, las_scaled_periods, las_end_s, las_end_reason,
      gates_false_before_start (the gates false in the LEVEL period before the start),
      level_budget_periods, gate_consistent (every LAS period of the run), t_loc_s,
      t_loc_last_s, t_done_after_loc_s, touch_min_scale (FB meta, LF), window,
  touch_ends [every TOUCH -> other phase transition]: t_s, phase_after, motor_stroke_mm,
      rod_stroke_mm, filtered_attitude_deg, plant (g6 path: t_s, stroke_ref_mm, pad_x_mm,
      attitude_true_deg, soil_sinkage_mm = ``plant.soil.z`` (FR is the J1 patch; rigid legs 0),
      soil_plastic_mm = ``soil.sp``, soil_force_kN),
  force_window: 1 ms plant rows around the RL minimum after the lift-off, +-0.5 s, columns
      [t, true_force_FL..RR (N), v_FL..RR (delivered m/s), u_FL..RR (demanded m/s),
      crawler (N), roll, pitch (rad)],
  periods [one per controller update inside the window]: t_s, phase_before, phase,
      cmd_mm_s (returned command), loads_kN (lower load estimate), loc, soil_mode,
      in_crawler_zone, reapproaching,
      las (LEVEL with LAS-b on): gates {S1 soil or not required, S2 LEVEL, S3 no LOC seen,
          S4 no soil mode, S5 crawler zone, S6 no reapproach, S7_sum sum L >= alpha W_ref,
          S7_light min L < beta F_min, S7p_rise rho >= rho_on and rho > rho_{k-1},
          S8 mean u > gamma v_max}, all_hold, sum_over_W, min_over_F_min, lightest_leg, rho,
          rho_prev, mean_u_over_v_max, armed_before, active_before, started, active_after,
          end_reason, sum_periods, is_scaled, input_mm_s, output_mm_s, gate_consistent,
      budget (a ``budget_output`` call): phase, Q_b_L_min, Q_in_L_min, acted, scale,
      done (LEVEL / DONE, P-S8-29 on): D_kN, complete_since_s, settled_s, is_settled,
          window_span_s, is_window_full, oldest_kN, newest_kN, largest_kN, is_non_increasing,
          is_D_small, min_load_over_F_min,
      diff_sink (DSb75): gate_open, first_loc_s, watch_over, above_periods, below_periods,
          r_mm_s [front, rear], hold {axis, legs, periods, t_start_s}.
Output: ``06_analysis/03_hydraulic/coupled/v5/las/diag/diag_<bundle>.jsonl``, opened with
``"x"`` (exit 2 when it exists). ``--out`` must lie in that folder or outside the project.

Usage (dynamics-dev python.exe, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/las_phase_diag.py list [--bundle D-a ..]
  python -I -B 04_scripts/04_hydraulic/coupled/las_phase_diag.py run --bundle D-b
      [--workers 4] [--affinity HEX] [--out <jsonl>] [--keys K1,K2] [--candidates L1,L2]
      [--limit N] [--no-record]
  python -I -B 04_scripts/04_hydraulic/coupled/las_phase_diag.py judge <diag_Db.jsonl>
      [--out <md>]
Exit codes: 0 done, 1 a run error / a run identity change (run) or anchors failed (judge),
2 input error (plan check included).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fb_targeted as fb  # noqa: E402  (sets the thread variables before numpy loads)
import numpy as np  # noqa: E402

ROOT = fb.ROOT
DIAG_DIR = fb.V5_DIR / "las" / "diag"
PLAN_PATH = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "las_phase_diag_plan.md"
PLAN_SHA256 = "0f24fcbef1ec802259428ba91c6f2892a7b10d5bd236c89eb6064c1f81967785"
"""``las_phase_diag_plan.md`` as sealed by control-expert (2026-11-08)."""
G3_KEYS = ("D1|H-R-A|rigid+J1@FR|T|diag-op|K3|VB|e0.002",
           "D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0.002")
F1_KEY = "S5|V0|etadef|e0.002"
BUNDLES = ("D-a", "D-b", "D-c")
LEG_ORDER = ("FL", "FR", "RL", "RR")
FOCUS_LEG = "RL"

# Plan 1.2 grid.
CENTRE_NOMINAL = "nom"
GRID_CENTRES = ("1", "0.94", CENTRE_NOMINAL)
"""s_c labels: 1.0, 0.94 and s_nom (the plan's 0.8768421, the LF ``Q_nom / Q(4 v_max)``)."""
CENTRE_SCALES = {"1": 1.0, "0.94": 0.94}
GRID_STEPS = (0, 1, 2, 3, 4)
GRID_DELAY_STEP_S = 0.025
TOUCH_FREE_PERIODS = 165
PERIOD_S = 0.1
PLAN_S_NOM = 0.8768421
T1_S = TOUCH_FREE_PERIODS * PERIOD_S * PLAN_S_NOM
"""TOUCH free extension time at s = 1 (plan 1.2: 14.468 s)."""

BUNDLE_COUNTS = {"D-a": 4, "D-b": len(G3_KEYS) * len(GRID_CENTRES) * len(GRID_STEPS),
                 "D-c": 2}
FORCE_WINDOW_HALF_S = 0.5
TOUCH_END_LEAD_S = 0.5
LOC_TAIL_S = 2.0
LOC_LEAD_S = 0.5
DONE_TAIL_S = 1.0
TIME_TOLERANCE_S = 1e-9
M_TO_MM = 1e3
N_TO_KN = 1e-3
PHASE_TOUCH = "touch"
PHASE_LEVEL = "level"
LEVEL_PHASES = ("level", "done")
CANDIDATE_L = "L"
CANDIDATE_LF = "LF"
CANDIDATE_LT = "LT"
IDENTITY_FILES = {**fb.IDENTITY_FILES, "las_phase_diag.py": HERE / "las_phase_diag.py",
                  "las_phase_judge.py": HERE / "las_phase_judge.py"}
FORCE_WINDOW_COLUMNS = ("t", *(f"true_force_{leg}" for leg in LEG_ORDER),
                        *(f"v_{leg}" for leg in LEG_ORDER), *(f"u_{leg}" for leg in LEG_ORDER),
                        "crawler", "roll", "pitch")


# ------------------------------------------------------------------------------- plan check
def plan_problem(path: Path = PLAN_PATH, expected: str = PLAN_SHA256) -> str | None:
    """Why the run may not start (None = the sealed plan is there with its sha256)."""
    if not path.exists():
        return f"missing {path}"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        return f"{path.name} sha256 {digest} != sealed {expected}"
    return None


# ------------------------------------------------------------------------------- pure helpers
def finite_or_none(value) -> float | None:
    """``float(value)`` when finite, else None (JSON has no NaN)."""
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def rounded_list(values, scale: float = 1.0, digits: int = 4) -> list[float | None]:
    """Values times ``scale``, rounded; NaN -> None."""
    out = []
    for value in np.asarray(values, float).ravel():
        scaled = finite_or_none(value * scale)
        out.append(None if scaled is None else round(scaled, digits))
    return out


@dataclass(frozen=True)
class GateLimits:
    """The LAS-b start thresholds of one controller (``LiftoffApproachSlowSettings``)."""

    sum_on_fraction_W: float
    light_leg_fraction_of_F_min: float
    slow_mean_fraction: float
    rho_on: float
    weight_ref_N: float
    F_min_N: float
    max_speed_m_s: float

    @classmethod
    def of(cls, controller) -> GateLimits:
        settings = controller.config.liftoff_approach_slow
        return cls(float(settings.sum_on_fraction_W),
                   float(settings.light_leg_fraction_of_F_min),
                   float(settings.slow_mean_fraction), float(settings.rho_on),
                   float(controller._reference_weight_N()),
                   float(controller.geometry.F_min_N), float(controller.geometry.max_speed_m_s))


@dataclass(frozen=True)
class GateFlags:
    """The state conditions S1 .. S6 as the controller saw them in the period."""

    is_soil_window: bool
    """S1: ``soil.enable or not require_soil_response``."""
    is_level: bool
    has_loc_been_seen: bool
    has_soil_mode_started: bool
    is_in_crawler_zone: bool
    is_reapproaching: bool


def gate_record(loads_N, rho: float, lightest_leg: int, previous_rho: float | None,
                leg_speeds_m_s, flags: GateFlags, limits: GateLimits) -> dict:
    """S1 .. S8 of LAS-b (c2 ``_liftoff_slow_start_gates_hold``) with the values behind them."""
    loads_N = np.asarray(loads_N, float)
    load_sum_N = float(np.sum(loads_N))
    lightest_N = float(np.min(loads_N))
    mean_speed = float(np.mean(np.asarray(leg_speeds_m_s, float)))
    is_rising = previous_rho is not None and rho >= limits.rho_on and rho > previous_rho
    gates = {
        "S1": flags.is_soil_window, "S2": flags.is_level, "S3": not flags.has_loc_been_seen,
        "S4": not flags.has_soil_mode_started, "S5": flags.is_in_crawler_zone,
        "S6": not flags.is_reapproaching,
        "S7_sum": load_sum_N >= limits.sum_on_fraction_W * limits.weight_ref_N,
        "S7_light": lightest_N < limits.light_leg_fraction_of_F_min * limits.F_min_N,
        "S7p_rise": bool(is_rising),
        "S8": mean_speed > limits.slow_mean_fraction * limits.max_speed_m_s,
    }
    return {"gates": gates, "all_hold": all(gates.values()),
            "sum_over_W": load_sum_N / limits.weight_ref_N,
            "min_over_F_min": lightest_N / limits.F_min_N,
            "lightest_leg": LEG_ORDER[int(lightest_leg)], "rho": finite_or_none(rho),
            "rho_prev": finite_or_none(previous_rho),
            "mean_u_over_v_max": mean_speed / limits.max_speed_m_s}


@dataclass(frozen=True)
class RelaxSettings:
    """P-S8-29 (V2b) values the DONE record compares with (``TwistCompletionRelax``)."""

    settle_s: float
    window_s: float
    drop_N: float
    rise_tol_N: float
    max_twist_N: float
    period_s: float


def done_gate_values(t_s: float, history: list[tuple[float, float]],
                     settled_since_s: float | None, twist_load_N: float,
                     settings: RelaxSettings) -> dict:
    """The V2b DONE items of a period (c2 ``_is_twist_relax_ok``), record only."""
    settled_s = None if settled_since_s is None else t_s - settled_since_s
    out = {"D_kN": twist_load_N * N_TO_KN, "settled_s": settled_s,
           "is_settled": settled_s is not None
           and settled_s >= settings.settle_s - TIME_TOLERANCE_S,
           "is_D_small": abs(twist_load_N) <= settings.max_twist_N}
    if not history:
        return {**out, "window_span_s": None, "is_window_full": False, "oldest_kN": None,
                "newest_kN": None, "largest_kN": None, "is_non_increasing": False}
    oldest_N, newest_N = history[0][1], history[-1][1]
    largest_N = max(value for _, value in history)
    span_s = history[-1][0] - history[0][0]
    return {**out, "window_span_s": span_s,
            "is_window_full": span_s >= settings.window_s - settings.period_s - TIME_TOLERANCE_S,
            "oldest_kN": oldest_N * N_TO_KN, "newest_kN": newest_N * N_TO_KN,
            "largest_kN": largest_N * N_TO_KN,
            "is_non_increasing": newest_N <= oldest_N - settings.drop_N
            and largest_N <= oldest_N + settings.rise_tol_N}


def first_touch_end_s(touch_ends: list[dict]) -> float | None:
    return touch_ends[0]["t_s"] if touch_ends else None


def first_loc_after_s(periods: list[dict], t_from_s: float | None) -> float | None:
    """The first period at or after ``t_from_s`` with a confirmed LOC."""
    for period in periods:
        if period["loc"] and (t_from_s is None or period["t_s"] >= t_from_s - TIME_TOLERANCE_S):
            return period["t_s"]
    return None


def last_loc_onset_s(periods: list[dict]) -> float | None:
    """The last period whose LOC is confirmed and whose previous period's was not."""
    onset = None
    was_loc = False
    for period in periods:
        if period["loc"] and not was_loc:
            onset = period["t_s"]
        was_loc = period["loc"]
    return onset


def first_done_after_s(periods: list[dict], t_from_s: float) -> float | None:
    for period in periods:
        if period["phase"] == "done" and period["t_s"] >= t_from_s - TIME_TOLERANCE_S:
            return period["t_s"]
    return None


def record_window(bundle: str, periods: list[dict], touch_ends: list[dict]) -> dict:
    """``{t0_s, t1_s, rule}`` of the periods a bundle keeps (module docstring)."""
    t_end_s = periods[-1]["t_s"] if periods else None
    if bundle == "D-c":
        t_loc_s = last_loc_onset_s(periods)
        if t_loc_s is None:
            return {"t0_s": None, "t1_s": t_end_s, "rule": "no LOC: whole run"}
        t_done_s = first_done_after_s(periods, t_loc_s)
        t1_s = t_end_s if t_done_s is None else t_done_s + DONE_TAIL_S
        return {"t0_s": t_loc_s - LOC_LEAD_S, "t1_s": t1_s,
                "rule": "last LOC onset - 0.5 s .. first DONE after it + 1 s"}
    t_touch_s = first_touch_end_s(touch_ends)
    t0_s = None if t_touch_s is None else t_touch_s - TOUCH_END_LEAD_S
    t_loc_s = first_loc_after_s(periods, t_touch_s)
    t1_s = t_end_s if t_loc_s is None else t_loc_s + LOC_TAIL_S
    return {"t0_s": t0_s, "t1_s": t1_s,
            "rule": "first TOUCH end - 0.5 s .. first LOC after it + 2 s"}


def periods_in(periods: list[dict], window: dict) -> list[dict]:
    t0_s = -math.inf if window["t0_s"] is None else window["t0_s"] - TIME_TOLERANCE_S
    t1_s = math.inf if window["t1_s"] is None else window["t1_s"] + TIME_TOLERANCE_S
    return [period for period in periods if t0_s <= period["t_s"] <= t1_s]


def las_start_details(periods: list[dict]) -> dict:
    """The LAS-b start period, the gates false in the LEVEL period before it and whether every
    recorded LAS period is gate-consistent (plan 2)."""
    previous_las = None
    start = {"gates_false_before_start": None, "has_level_period_before_start": False}
    for period in periods:
        las = period.get("las")
        if las is None:
            continue
        if las["started"]:
            if previous_las is not None:
                start = {"gates_false_before_start": [
                    name for name, ok in previous_las["gates"].items() if not ok],
                    "has_level_period_before_start": True}
            break
        previous_las = las
    consistent = [period["las"]["gate_consistent"] for period in periods if period.get("las")]
    return {**start, "gate_consistent": all(consistent) if consistent else None,
            "las_periods_recorded": len(consistent)}


def periods_between(t_from_s: float | None, t_to_s: float | None,
                    period_s: float = PERIOD_S) -> int | None:
    """Whole control periods from ``t_from_s`` to ``t_to_s``."""
    if t_from_s is None or t_to_s is None:
        return None
    return round((t_to_s - t_from_s) / period_s)


def force_window(rows: np.ndarray, columns: dict[str, int], t_lift_s: float | None,
                 focus_leg: str = FOCUS_LEG, half_width_s: float = FORCE_WINDOW_HALF_S
                 ) -> dict | None:
    """The 1 ms rows around the focus leg's smallest true force after the lift-off.

    Returns:
        None without rows or a lift-off time; else the minimum (focus leg and all legs) and
        the rows of :data:`FORCE_WINDOW_COLUMNS` within +-``half_width_s`` of it.
    """
    if t_lift_s is None or len(rows) == 0:
        return None
    t = rows[:, columns["t"]]
    after = np.flatnonzero(t >= t_lift_s - TIME_TOLERANCE_S)
    if after.size == 0:
        return None
    force_columns = [columns[f"true_force_{leg}"] for leg in LEG_ORDER]
    forces = rows[after][:, force_columns]
    focus_index = LEG_ORDER.index(focus_leg)
    focus_row = int(after[int(np.argmin(forces[:, focus_index]))])
    t_focus_s = float(t[focus_row])
    smallest_by_leg = forces.min(axis=0)
    selected = np.abs(t - t_focus_s) <= half_width_s + TIME_TOLERANCE_S
    kept = rows[selected][:, [columns[name] for name in FORCE_WINDOW_COLUMNS]]
    return {"focus_leg": focus_leg, "t_focus_min_s": t_focus_s,
            "focus_min_kN": float(rows[focus_row, columns[f"true_force_{focus_leg}"]]) * N_TO_KN,
            "min_leg": LEG_ORDER[int(np.argmin(smallest_by_leg))],
            "min_kN": float(smallest_by_leg.min()) * N_TO_KN,
            "columns": list(FORCE_WINDOW_COLUMNS),
            "rows": [rounded_list(row, digits=7) for row in kept]}


def full_flow_m3_s(head_area_m2, annulus_area_m2, max_speed_m_s: float) -> float:
    """``Q(4 v_max)``: all four legs extending at v_max."""
    return fb.command_flow_m3_s(np.full(4, float(max_speed_m_s)), head_area_m2, annulus_area_m2)


@dataclass(frozen=True)
class TouchBudget:
    """D-b grid point ``(centre, j)`` resolved for one geometry (plan 1.2)."""

    centre: str
    j: int
    budget_m3_s: float
    full_m3_s: float
    nominal_m3_s: float
    centre_scale: float
    centre_time_s: float

    @property
    def scale(self) -> float:
        return self.budget_m3_s / self.full_m3_s

    def record(self) -> dict:
        return {"centre": self.centre, "j": self.j, "s": self.scale, "s_c": self.centre_scale,
                "s_nom": self.nominal_m3_s / self.full_m3_s, "T_1_s": T1_S,
                "T_c_s": self.centre_time_s, "delay_s": self.j * GRID_DELAY_STEP_S,
                "Q_b_L_min": self.budget_m3_s * fb.M3_S_TO_L_MIN,
                "Q_full_L_min": self.full_m3_s * fb.M3_S_TO_L_MIN,
                "Q_nom_L_min": self.nominal_m3_s * fb.M3_S_TO_L_MIN}


def touch_budget_for(centre: str, j: int, full_m3_s: float, nominal_m3_s: float
                     ) -> TouchBudget:
    """``Q_b = base T_c / (T_c + j delta)``; base = s_c Q(4 v_max), or ``Q_nom`` itself for the
    nominal centre (its j = 0 is then exactly the LF budget, anchor A-2).

    Raises:
        ValueError: Unknown centre or j.
    """
    if j not in GRID_STEPS:
        raise ValueError(f"grid step j={j} not in {GRID_STEPS}")
    if centre == CENTRE_NOMINAL:
        centre_scale = nominal_m3_s / full_m3_s
        base_m3_s = nominal_m3_s
    elif centre in CENTRE_SCALES:
        centre_scale = CENTRE_SCALES[centre]
        base_m3_s = centre_scale * full_m3_s
    else:
        raise ValueError(f"unknown grid centre {centre!r}")
    centre_time_s = T1_S / centre_scale
    factor = centre_time_s / (centre_time_s + j * GRID_DELAY_STEP_S)
    return TouchBudget(centre, j, base_m3_s * factor, full_m3_s, nominal_m3_s, centre_scale,
                       centre_time_s)


# ------------------------------------------------------------------------------- recorder
@dataclass
class RunLog:
    """What the hooks collect for one controller (``controller.__dict__["_las_diag"]``)."""

    periods: list[dict] = field(default_factory=list)
    touch_ends: list[dict] = field(default_factory=list)
    touch_budget: TouchBudget | None = None
    budget_state: fb.FbState | None = None
    acted_by_end_phase: dict[str, int] = field(default_factory=dict)


_PERIOD: dict = {}
"""Parts of the running period's record (one controller at a time in a worker)."""
_INSTALLED: dict = {}
LOG_ATTRIBUTE = "_las_diag"


def _log_of(controller) -> RunLog:
    log = controller.__dict__.get(LOG_ATTRIBUTE)
    if log is None:
        log = RunLog()
        controller.__dict__[LOG_ATTRIBUTE] = log
    return log


def _soil_flags(controller) -> tuple[bool, bool]:
    """(LOC confirmed, soil mode started), read without creating the soil state."""
    soil = controller._state.soil
    if soil is None:
        return False, False
    return bool(soil.is_liftoff_confirmed), bool(soil.is_soil_mode
                                                 or soil.soil_mode_start_s is not None)


@dataclass(frozen=True)
class _SlowSnapshot:
    is_armed: bool
    is_active: bool
    previous_rho: float | None
    end_s: float | None


def _slow_snapshot(slow) -> _SlowSnapshot:
    if slow is None:
        return _SlowSnapshot(True, False, None, None)
    return _SlowSnapshot(slow.is_armed, slow.is_active, slow.previous_rho, slow.end_s)


def _las_period_record(controller, reading, speeds_in, reapproaching, before: _SlowSnapshot,
                       output) -> dict:
    from outrigger_sim.control import c2

    slow = controller._state.liftoff_slow
    loads_N = np.array(controller._load_estimate_N(reading.cylinder_force_lower_N), float)
    rho, lightest = c2.diagonal_deficit_ratio(loads_N)
    is_loc, is_soil_mode = _soil_flags(controller)
    settings = controller.config.liftoff_approach_slow
    flags = GateFlags(bool(controller.config.soil.enable or not settings.require_soil_response),
                      controller._state.phase is c2.C2Phase.LEVEL,
                      bool(slow.has_loc_been_seen), is_soil_mode,
                      bool(controller._state.in_crawler_zone), bool(np.any(reapproaching)))
    record = gate_record(loads_N, rho, lightest, before.previous_rho, speeds_in, flags,
                         GateLimits.of(controller))
    is_started = before.is_armed and not slow.is_armed
    has_ended = before.end_s is None and slow.end_s is not None
    record.update(
        armed_before=before.is_armed, active_before=before.is_active, started=is_started,
        active_after=bool(slow.is_active),
        end_reason=str(slow.end_reason) if has_ended else None,
        sum_periods=int(slow.sum_periods), is_loc_now=is_loc,
        is_scaled=not np.array_equal(np.asarray(output, float), speeds_in),
        input_mm_s=rounded_list(speeds_in, M_TO_MM), output_mm_s=rounded_list(output, M_TO_MM),
        gate_consistent=(before.is_armed and record["all_hold"]) == is_started)
    return record


def _las_hook(original):
    def apply_liftoff_approach_slow(self, reading, leg_speeds, reapproaching):
        before = _slow_snapshot(self._state.liftoff_slow)
        speeds_in = np.array(leg_speeds, float)
        reapproach = np.array(reapproaching, bool)
        output = original(self, reading, leg_speeds, reapproaching)
        _PERIOD["las"] = _las_period_record(self, reading, speeds_in, reapproach, before,
                                            output)
        _PERIOD["reapproaching"] = [LEG_ORDER[i] for i in np.flatnonzero(reapproach)]
        return output

    return apply_liftoff_approach_slow


def _budget_hook(original):
    def budget_output(state, output_m_s, geometry, phase, clip_returned=False):
        budget_before = float(state.budget_m3_s)
        result = original(state, output_m_s, geometry, phase, clip_returned)
        is_acted = result is not output_m_s
        largest_in = float(np.max(np.abs(output_m_s)))
        scale = (float(np.max(np.abs(result))) / largest_in) if is_acted and largest_in else 1.0
        flow = fb.command_flow_m3_s(output_m_s, geometry.head_area_m2, geometry.annulus_area_m2)
        _PERIOD["budget"] = {"phase": phase, "Q_b_L_min": budget_before * fb.M3_S_TO_L_MIN,
                             "Q_in_L_min": flow * fb.M3_S_TO_L_MIN, "acted": is_acted,
                             "scale": scale}
        return result

    return budget_output


def _touch_budget_state(controller, centre: str, j: int, nominal_m3_s: float) -> fb.FbState:
    """The run's TOUCH budget (created on the first ramp call from the run's geometry)."""
    log = _log_of(controller)
    if log.budget_state is None:
        geometry = controller.geometry
        full_m3_s = full_flow_m3_s(geometry.head_area_m2, geometry.annulus_area_m2,
                                   geometry.max_speed_m_s)
        log.touch_budget = touch_budget_for(centre, j, full_m3_s, nominal_m3_s)
        log.budget_state = fb.FbState(nominal_m3_s=nominal_m3_s,
                                      budget_m3_s=log.touch_budget.budget_m3_s)
    return log.budget_state


def _ramp_hook(original, centre: str, j: int, nominal_m3_s: float):
    """D-b: the FB-a budget of ``fb_targeted`` on the ramp output, TOUCH periods only."""

    def apply_output_ramp(self, leg_speeds):
        output = original(self, leg_speeds)
        phase = str(self._state.phase)
        if phase != PHASE_TOUCH:
            return output
        state = _touch_budget_state(self, centre, j, nominal_m3_s)
        clip_returned = bool(getattr(self.config, "clip_returned_command", False))
        scaled = fb.budget_output(state, output, self.geometry, phase, clip_returned)
        if scaled is not output:
            self._state.previous_output_m_s = scaled
            _PERIOD["touch_budget_acted"] = True
        return scaled

    return apply_output_ramp


def _relax_settings(controller) -> RelaxSettings:
    settings = controller.config.twist_completion_relax
    return RelaxSettings(float(settings.settle_s), float(settings.window_s),
                         float(settings.drop_N), float(settings.rise_tol_N),
                         float(settings.max_twist_N), float(controller.config.period_s))


def _done_record(controller, t_s: float) -> dict | None:
    if not controller.config.twist_completion_relax.enable:
        return None
    state = controller._state
    reading = state.last_reading
    twist_N = float(controller.geometry.twist_vector @ np.asarray(reading.cylinder_force_N))
    history = list(state.twist_relax_history or ())
    out = done_gate_values(t_s, history, state.twist_relax_settled_since_s, twist_N,
                           _relax_settings(controller))
    loads_N = np.array(controller._load_estimate_N(reading.cylinder_force_lower_N), float)
    out["complete_since_s"] = state.complete_since_s
    out["min_load_over_F_min"] = float(loads_N.min()) / float(controller.geometry.F_min_N)
    return out


def _diff_sink_record(controller) -> dict | None:
    sink = controller._state.diff_sink
    if sink is None:
        return None
    rates = controller._diff_sink_rates_m_s()  # sink exists: reads its deques only
    hold = sink.hold
    return {"gate_open": bool(sink.is_gate_open), "first_loc_s": sink.first_loc_s,
            "watch_over": bool(sink.is_watch_over), "above_periods": int(sink.above_periods),
            "below_periods": int(sink.below_periods),
            "r_mm_s": None if rates is None else rounded_list(rates, M_TO_MM),
            "hold": None if hold is None else {
                "axis": int(hold.axis), "legs": [LEG_ORDER[leg] for leg in hold.legs],
                "periods": int(hold.periods), "t_start_s": float(hold.t_start_s)}}


def _period_record(controller, t_s: float, phase_before: str, command) -> dict:
    state = controller._state
    phase = str(state.phase)
    is_loc, is_soil_mode = _soil_flags(controller)
    loads_N = np.array(controller._load_estimate_N(state.last_reading.cylinder_force_lower_N),
                       float)
    record = {"t_s": t_s, "phase_before": phase_before, "phase": phase,
              "cmd_mm_s": rounded_list(command.leg_speed_m_s, M_TO_MM),
              "loads_kN": rounded_list(loads_N, N_TO_KN), "loc": is_loc,
              "soil_mode": is_soil_mode, "in_crawler_zone": bool(state.in_crawler_zone),
              "reapproaching": _PERIOD.get("reapproaching"), "las": _PERIOD.get("las"),
              "budget": _PERIOD.get("budget"), "done": None, "diff_sink": None}
    if phase_before in LEVEL_PHASES or phase in LEVEL_PHASES:
        record["done"] = _done_record(controller, t_s)
        record["diff_sink"] = _diff_sink_record(controller)
    return record


def _harness_plant():
    """The plant of the running g6 job (``r72_g6_screen._CAP``), None on other paths."""
    module = sys.modules.get("r72_g6_screen")
    return None if module is None else module._CAP.get("plant")


def _plant_snapshot(plant) -> dict:
    out = {"t_s": float(plant.t), "stroke_ref_mm": rounded_list(plant.sref, M_TO_MM),
           "pad_x_mm": rounded_list(plant.x, M_TO_MM),
           "attitude_true_deg": [math.degrees(value) for value in plant.attitude()]}
    soil = getattr(plant, "soil", None)
    if soil is not None:
        out.update(soil_sinkage_mm=rounded_list(soil.z, M_TO_MM),
                   soil_plastic_mm=rounded_list(soil.sp, M_TO_MM),
                   soil_force_kN=rounded_list(soil.force, N_TO_KN))
    return out


def _touch_end_record(controller, t_s: float) -> dict:
    reading = controller._state.last_reading
    record = {"t_s": t_s, "phase_after": str(controller._state.phase),
              "motor_stroke_mm": rounded_list(reading.motor_stroke_m, M_TO_MM),
              "rod_stroke_mm": rounded_list(reading.rod_stroke_m, M_TO_MM),
              "filtered_attitude_deg": [math.degrees(v)
                                        for v in controller.filtered_attitude_rad]}
    plant = _harness_plant()
    if plant is not None:
        record["plant"] = _plant_snapshot(plant)
    return record


def _count_touch_budget(controller) -> None:
    """Count an acted TOUCH budget by the phase at the end of the update (plan 1.1)."""
    if not _PERIOD.get("touch_budget_acted"):
        return
    counts = _log_of(controller).acted_by_end_phase
    phase = str(controller._state.phase)
    counts[phase] = counts.get(phase, 0) + 1


def _update_hook(original, is_recording: bool):
    def update(self, measurements):
        _PERIOD.clear()
        phase_before = str(self._state.phase)
        command = original(self, measurements)
        _count_touch_budget(self)
        if not is_recording:
            return command
        t_s = float(measurements.t_s)
        log = _log_of(self)
        log.periods.append(_period_record(self, t_s, phase_before, command))
        if phase_before == PHASE_TOUCH and str(self._state.phase) != PHASE_TOUCH:
            log.touch_ends.append(_touch_end_record(self, t_s))
        return command

    return update


def install(is_recording: bool, grid_point: tuple[str, int] | None = None,
            controller_class=None, nominal_m3_s: float | None = None) -> None:
    """Patch this worker's controller class (after the FB wrapper) and ``fb.budget_output``.

    Args:
        is_recording: Install the recording hooks (False: only the D-b budget, if any).
        grid_point: D-b ``(centre, j)`` (None = no TOUCH budget).
        controller_class: ``c2.C2Controller`` by default (tests pass a stand-in).
        nominal_m3_s: ``Q_nom``; None = the FB value from the YAML.

    Raises:
        RuntimeError: Installed twice in one process, or ``c2.C2Controller`` is already
            replaced (``verdict_runs.install_logged_controller`` subclasses the original later;
            patching the subclass would drop its period log).
    """
    if _INSTALLED:
        raise RuntimeError("las_phase_diag.install: already installed in this process")
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
        if controller_class.__name__ != "C2Controller":
            raise RuntimeError(f"c2.C2Controller is {controller_class.__name__}, not the original")
    if nominal_m3_s is None:
        nominal_m3_s = fb.nominal_budget_m3_s(fb.pump_flow_m3_s())
    cls = controller_class
    originals = {"update": cls.update, "las": cls._apply_liftoff_approach_slow,
                 "ramp": cls._apply_output_ramp, "budget": fb.budget_output}
    cls.update = _update_hook(originals["update"], is_recording)
    if grid_point is not None:
        centre, j = grid_point
        touch_budget_for(centre, j, 1.0, 1.0)  # validates the point before any run
        cls._apply_output_ramp = _ramp_hook(originals["ramp"], centre, j, nominal_m3_s)
    if is_recording:
        cls._apply_liftoff_approach_slow = _las_hook(originals["las"])
        fb.budget_output = _budget_hook(originals["budget"])
    _INSTALLED.update(cls=cls, originals=originals)


def uninstall() -> None:
    """Undo :func:`install` (tests only)."""
    if not _INSTALLED:
        return
    cls, originals = _INSTALLED["cls"], _INSTALLED["originals"]
    cls.update = originals["update"]
    cls._apply_liftoff_approach_slow = originals["las"]
    cls._apply_output_ramp = originals["ramp"]
    fb.budget_output = originals["budget"]
    _INSTALLED.clear()
    _PERIOD.clear()


# ------------------------------------------------------------------------------- jobs
def grid_label(centre: str, j: int) -> str:
    return f"{CANDIDATE_LT}-c{centre}-j{j}"


def _diag_job(base: dict, bundle: str, label: str, fb_candidate: str,
              grid_point: tuple[str, int] | None, mask: int | None, is_recording: bool) -> dict:
    return {**base, "mask": mask,
            "diag": {"bundle": bundle, "label": label, "fb_candidate": fb_candidate,
                     "grid_point": None if grid_point is None else list(grid_point),
                     "record": is_recording}}


def bundle_base_jobs(bundle: str) -> list[dict]:
    """``run_v5`` jobs of a bundle's keys (VB first: the longer runs start early).

    Raises:
        ValueError: Unknown bundle, or the F-1 bundle has no ``S5|V0|etadef|e0.002`` job.
    """
    import las_targeted

    if bundle in ("D-a", "D-b"):
        jobs = las_targeted.jobs_for_keys(list(G3_KEYS))
        return sorted(jobs, key=lambda job: job["setting"] != "VB")
    if bundle == "D-c":
        jobs = [job for job in fb.bundle_base_jobs("F-1") if fb.fb_key(job) == F1_KEY]
        if len(jobs) != 1:
            raise ValueError(f"F-1 has {len(jobs)} jobs with key {F1_KEY}")
        return jobs
    raise ValueError(f"unknown bundle {bundle!r}")


def _variants(bundle: str) -> list[tuple[str, str, tuple[str, int] | None]]:
    """(label, ``fb_targeted`` candidate, grid point) of a bundle's candidates."""
    if bundle == "D-b":
        return [(grid_label(centre, j), CANDIDATE_L, (centre, j))
                for centre in GRID_CENTRES for j in GRID_STEPS]
    return [(CANDIDATE_L, CANDIDATE_L, None), (CANDIDATE_LF, CANDIDATE_LF, None)]


def bundle_jobs(bundle: str, mask: int | None = None, is_recording: bool = True,
                keys: list[str] | None = None, candidates: list[str] | None = None
                ) -> list[dict]:
    """One job per (key, candidate) of a bundle (module docstring)."""
    base = bundle_base_jobs(bundle)
    if keys is not None:
        base = [job for job in base if fb.fb_key(job) in set(keys)]
    jobs = []
    for job in base:
        for label, fb_candidate, grid_point in _variants(bundle):
            if candidates is None or label in candidates:
                jobs.append(_diag_job(job, bundle, label, fb_candidate, grid_point, mask,
                                      is_recording))
    return jobs


def job_label(job: dict) -> tuple[str, str]:
    return fb.fb_key(job), job["diag"]["label"]


# ------------------------------------------------------------------------------- worker
def touch_budget_record(log: RunLog) -> dict | None:
    """The D-b block: the grid point, the acted periods by end phase and the exclusion."""
    if log.touch_budget is None:
        return None
    level_periods = sum(count for phase, count in log.acted_by_end_phase.items()
                        if phase != PHASE_TOUCH)
    return {**log.touch_budget.record(), "acted_by_end_phase": dict(log.acted_by_end_phase),
            "level_budget_periods": level_periods, "excluded": level_periods != 0}


def _summary(line: dict, las: dict, log: RunLog, window: dict, forces: dict | None,
             budget_block: dict | None) -> dict:
    fb_budget = (line.get("fb") or {}).get("budget") or {}
    d1 = line.get("d1") or {}
    forces = forces or {}
    t_touch_s = first_touch_end_s(log.touch_ends)
    t_loc_last_s = last_loc_onset_s(log.periods)
    f_judged = d1.get("F_judged_min_N")
    return {
        "F_RL_kN": forces.get("focus_min_kN"), "t_RL_min_s": forces.get("t_focus_min_s"),
        "min_leg_after_lift": forces.get("min_leg"), "min_after_lift_kN": forces.get("min_kN"),
        "F_judged_min_kN": None if f_judged is None else f_judged * N_TO_KN,
        "t_touch_end_s": t_touch_s,
        "t_lift_s": ((line.get("values") or {}).get("forces") or {}).get("t_lift_s"),
        "t_las_start_s": las.get("start_t_s"),
        "las_start_period": periods_between(t_touch_s, las.get("start_t_s")),
        "las_start_rho": las.get("start_rho"), "las_start_rho_prev": las.get("start_rho_prev"),
        "las_active_periods": las.get("active_periods"),
        "las_scaled_periods": las.get("scaled_periods"), "las_end_s": las.get("end_t_s"),
        "las_end_reason": las.get("end_reason"),
        **las_start_details(log.periods),
        "level_budget_periods": None if budget_block is None
        else budget_block["level_budget_periods"],
        "t_loc_s": first_loc_after_s(log.periods, t_touch_s), "t_loc_last_s": t_loc_last_s,
        "t_done_after_loc_s": None if t_loc_last_s is None
        else first_done_after_s(log.periods, t_loc_last_s),
        "touch_min_scale": (fb_budget.get("min_scale_by_phase") or {}).get(PHASE_TOUCH),
        "window": window}


def diag_block(entry: dict, line: dict, las: dict, controller, plant, identity: dict) -> dict:
    """The ``diag`` block of a finished run (module docstring)."""
    from harness_flow import COLUMN

    log = controller.__dict__.get(LOG_ATTRIBUTE) or RunLog()
    budget_block = touch_budget_record(log)
    block = {"bundle": entry["bundle"], "candidate": entry["label"],
             "record": entry["record"], "identity": identity, "touch_budget": budget_block}
    if not entry["record"]:
        return block
    window = record_window(entry["bundle"], log.periods, log.touch_ends)
    t_lift_s = ((line.get("values") or {}).get("forces") or {}).get("t_lift_s")
    forces = force_window(plant.flow_limiter.rows(), COLUMN, t_lift_s)
    block.update(summary=_summary(line, las, log, window, forces, budget_block), window=window,
                 touch_ends=log.touch_ends, force_window=forces,
                 periods=periods_in(log.periods, window), periods_total=len(log.periods))
    return block


def run_identity() -> dict:
    """``fb_targeted.run_identity`` with this tool's files and the plan sha256."""
    return {**fb.run_identity(files=IDENTITY_FILES), "plan_sha256": PLAN_SHA256}


def _install_all(entry: dict) -> fb.FbParams:
    params = fb.CANDIDATES[entry["fb_candidate"]]
    fb._install_candidate(params)  # thread check, preset LAS-b b0, FB wrapper, run capture
    grid_point = None if entry["grid_point"] is None else tuple(entry["grid_point"])
    if entry["record"] or grid_point is not None:
        install(entry["record"], grid_point)
    return params


def run_diag_job(job: dict) -> dict:
    """Worker: install FB (LF), the TOUCH budget (D-b) and the recorder, run the job, add
    ``fb``, ``las`` and ``diag``."""
    t_start = time.perf_counter()
    entry = job.pop("diag")
    head = {"job": job, "diag": {"bundle": entry["bundle"], "candidate": entry["label"],
                                 "key": fb.fb_key(job)}}
    try:
        import run_v5  # sys.path and thread variables first

        identity = run_identity()
        params = _install_all(entry)
    except Exception as exc:  # recorded as an error line; the batch goes on
        return {**head, "error": f"install: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    line = run_v5.run_one(job)
    if "error" in line:
        return {**line, "diag": head["diag"]}
    try:
        plant, controller = fb._run_objects(job)
        fb_entry = {"name": entry["label"], "bundle": entry["bundle"]}
        line["fb"] = fb._fb_block(fb_entry, job, params, controller, plant, identity)
        line["las"] = fb.las_block_of(controller, fb._CAPTURE.get("harness"))
        line["diag"] = {"key": fb.fb_key(job),
                        **diag_block(entry, line, line["las"], controller, plant, identity)}
    except Exception as exc:
        return {**head, "error": f"metrics: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    return line


# ------------------------------------------------------------------------------- batch / CLI
def default_out(bundle: str) -> Path:
    return DIAG_DIR / f"diag_{bundle.replace('-', '')}.jsonl"


def out_path_problem(path: Path, out_dir: Path = DIAG_DIR, root: Path = ROOT) -> str | None:
    """Why ``--out`` is refused: inside the project it must lie in ``v5/las/diag/``, and the
    file must not exist (it is opened with ``"x"``)."""
    resolved = path.resolve()
    if resolved.is_relative_to(root.resolve()) and not resolved.is_relative_to(
            out_dir.resolve()):
        return f"--out {path} is inside the project but not in {out_dir}"
    if resolved.exists():
        return f"--out {path} exists (new files only)"
    return None


def _json_default(value):
    return value.item() if hasattr(value, "item") else str(value)


def _print_line(count: int, total: int, record: dict) -> None:
    diag = record.get("diag") or {}
    if "error" in record:
        state = f"ERROR {record['error'][:200]}"
    else:
        summary = diag.get("summary") or {}
        budget = diag.get("touch_budget") or {}
        state = (f"{(record.get('d1') or {}).get('verdict', record.get('final_phase'))} "
                 f"{record['commands_sha256'][:12]} s {budget.get('s')} "
                 f"touch_end {summary.get('t_touch_end_s')} "
                 f"start +{summary.get('las_start_period')} rho {summary.get('las_start_rho')} "
                 f"active {summary.get('las_active_periods')} "
                 f"F_RL {summary.get('F_RL_kN')} kN {record['wall_s']}s")
    print(f"{count}/{total} {diag.get('candidate')} {diag.get('key')}: {state}", flush=True)


def run_batch(jobs: list[dict], path: Path, workers: int, current_identity: dict) -> dict:
    """Run the jobs in spawned workers (one run each) and write every line to the new file.

    Returns:
        ``runs``, ``errors`` and ``stop`` (None or a run identity change).
    """
    import verdict_runs

    verdict_runs.warm_numba_cache()
    path.parent.mkdir(parents=True, exist_ok=True)
    runs = errors = 0
    stop = None
    with path.open("x", encoding="utf-8") as handle, \
            get_context("spawn").Pool(workers, maxtasksperchild=1) as pool:
        for record in pool.imap_unordered(run_diag_job, jobs):
            record["job"].pop("mask", None)
            handle.write(json.dumps(record, default=_json_default) + "\n")
            handle.flush()
            runs += 1
            _print_line(runs, len(jobs), record)
            if "error" in record:
                errors += 1
                continue
            problems = fb.identity_mismatch(record["diag"].get("identity"), current_identity)
            if problems:
                stop = f"run identity changed during the batch: {problems[:3]}"
                pool.terminate()
                break
    return {"runs": runs, "errors": errors, "stop": stop}


def list_bundle(bundle: str) -> tuple[list[str], list[str]]:
    """(report lines, problems): the runs of a bundle against :data:`BUNDLE_COUNTS`."""
    jobs = bundle_jobs(bundle)
    labels = [job_label(job) for job in jobs]
    lines = [f"{bundle}: {len(jobs)} runs (expected {BUNDLE_COUNTS[bundle]})"]
    lines += [f"  {key}  {label}" for key, label in labels]
    problems = []
    if len(jobs) != BUNDLE_COUNTS[bundle] or len(set(labels)) != len(labels):
        problems.append(f"{bundle}: {len(jobs)} runs (unique {len(set(labels))})")
    return lines, problems


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="runs of the bundles")
    listing.add_argument("--bundle", nargs="+", choices=BUNDLES, default=list(BUNDLES))
    run = sub.add_parser("run", help="run a bundle into a new file")
    run.add_argument("--bundle", required=True, choices=BUNDLES)
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--affinity", default=None, help="hex mask, set in every worker")
    run.add_argument("--out", type=Path, default=None)
    run.add_argument("--keys", default=None, help="comma-separated keys (subset)")
    run.add_argument("--candidates", default=None,
                     help="comma-separated candidate labels (subset), e.g. LF or LT-c1-j0")
    run.add_argument("--limit", type=int, default=None, help="first N runs only")
    run.add_argument("--no-record", action="store_true",
                     help="no recording hooks (on / off command hash check)")
    judge = sub.add_parser("judge", help="plan 1.3 anchors and plan 3 measures of a D-b file")
    judge.add_argument("path", type=Path)
    judge.add_argument("--out", type=Path, default=None, help="new Markdown file")
    return parser.parse_args(argv)


def _run_command(args) -> int:
    path = args.out or default_out(args.bundle)
    problem = out_path_problem(path)
    if problem is not None:
        print(f"input error: {problem}")
        print(json.dumps({"bundle": args.bundle, "stop": "out", "reason": problem}))
        return 2
    try:
        identity = run_identity()
        mask = None if args.affinity is None else int(args.affinity, 16)
        jobs = bundle_jobs(args.bundle, mask, not args.no_record,
                           args.keys.split(",") if args.keys else None,
                           args.candidates.split(",") if args.candidates else None)
    except (KeyError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"input error: {exc!r}")
        return 2
    jobs = jobs if args.limit is None else jobs[: args.limit]
    if not jobs:
        print("input error: no runs selected")
        return 2
    print(f"run identity: {identity['git_head']} dirty {identity['git_dirty']} "
          f"code_diff {identity['code_diff_sha256'][:12]}", flush=True)
    print(f"{args.bundle}: {len(jobs)} runs -> {path}", flush=True)
    summary = run_batch(jobs, path, args.workers, identity)
    print(json.dumps({"bundle": args.bundle, "out": str(path), **summary}))
    return 1 if summary["errors"] or summary["stop"] else 0


def _judge_command(args) -> int:
    import las_phase_judge

    if args.out is not None and args.out.exists():
        print(f"input error: --out {args.out} exists (new files only)")
        return 2
    try:
        lines = las_phase_judge.read_lines(args.path)
    except (OSError, ValueError) as exc:
        print(f"input error: {exc!r}")
        return 2
    result = las_phase_judge.judge(lines)
    report = las_phase_judge.report_markdown(result, args.path)
    print(report)
    if args.out is not None:
        with args.out.open("x", encoding="utf-8") as handle:
            handle.write(report)
    print(json.dumps({"verdict": result["verdict"], "anchors_pass": result["anchors_pass"],
                      "excluded": result["excluded"], "missing": result["missing"]}))
    return 0 if result["anchors_pass"] else 1


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command in ("run", "judge"):
        problem = plan_problem()
        if problem is not None:
            print(f"input error (plan): {problem}")
            print(json.dumps({"stop": "plan", "reason": problem}))
            return 2
        return _run_command(args) if args.command == "run" else _judge_command(args)
    all_problems = []
    for bundle in args.bundle:
        lines, problems = list_bundle(bundle)
        print("\n".join(lines))
        all_problems += problems
    for problem in all_problems:
        print(f"MISMATCH {problem}")
    print(json.dumps({"bundles": args.bundle, "counts_equal": not all_problems}))
    return 1 if all_problems else 0


if __name__ == "__main__":
    sys.exit(main())
