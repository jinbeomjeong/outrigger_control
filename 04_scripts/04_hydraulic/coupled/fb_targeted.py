"""FB (command flow budget + saturation detection) targeted runs on the reduced harness
(sealed ``fb_targeted_rules.md`` and its sealed addendum ``fb_targeted_rules_rev1.md``;
design copy ``fb_design.md``).

The candidates wrap ``c2.C2Controller`` in the worker process only (spawned,
``maxtasksperchild=1``); no project file changes. LAS-b is the controller's own (03_src,
merged in bacb2d2, on in the R8 preset): rules 3.1 line 80 says a merged 03_src LAS-b replaces
the ``las_targeted`` wrapper once F-0 reproduces with it, so a worker checks that the preset
has LAS-b on with the ``b0`` values (else it stops) and installs the FB wrapper only (for the
candidates that have one); the ``las_targeted`` wrapper is never installed. One run is
``run_v5.run_one`` of a ``d1_rows`` job or a ``run_v5`` verdict / U-9 job; its line gets an
``fb`` and an ``las`` block.

The ``las`` block is built from the controller meta ``liftoff_approach_slow``, in the fields
of ``las_targeted.las_block`` (``candidate`` "b0", ``mode`` "act", ``source`` names the meta):
  params           <- settings (alpha = sum_on_fraction_W, beta = light_leg_fraction_of_F_min,
                      gamma = slow_mean_fraction, alpha_end = sum_off_fraction_W,
                      n_end = off_periods, t_max_s = max_s, rho_on = rho_on)
  start_t_s, end_t_s, end_reason, active_periods, scaled_periods <- start_s, end_s,
                      end_reason, active_periods, scaled_periods
  start_leg        <- index of the meta's leg name (FL, FR, RL, RR = 0 .. 3)
  soil_enable, W_ref_N <- ``config.soil.enable``, ``_reference_weight_N()`` (a constant)
  wrapper_reached  <- the run has a LAS-b state (the meta has ``start_s``)
  s7p_first        None: the 03_src meta has no "first S7' period" record; it adds
                      ``start_rho`` / ``start_rho_prev`` (rho of the start period instead)
  loc_minus_t_off_s, t_loc_s, t_off_s <- ``las_targeted.loc_delay_record`` (unchanged).

Candidates (rules 2):
  L       the preset as it is (LAS-b on, no FB wrapper installed). The comparison reference.
  LF      L + budget FB-a (rules 1.1) + detection FB-b (rules 1.2).
  LF-off  the FB wrapper installed with ``enable=False`` (F-0 only): must reproduce L.
  OL-L    L + the open-loop equivalent: from the first LEVEL period on, for 8.0 s, the
          return of ``_level_step`` is v_max on every leg (design 3.1 wrapper: a DONE inside
          the window is put back to LEVEL), then the normal loop; increment limit, delay and
          (OL-LF) budget still apply. F-5 only.
  OL-LF   LF + the open-loop equivalent.

FB-a (rules 1.1): after ``_apply_output_ramp`` (increment limit or FAULT stop 0) the output is
scaled by ``min(1, Q_b / Q(u))``, ``Q(u) = sum_i A_i(u_i) |u_i|`` (head area extending,
annulus area retracting), and the scaled value is stored as ``previous_output_m_s``.
``Q_nom = rho eta_v,min Q_th`` with ``Q_th`` = YAML ``actuator.pump_flow_m3_s``, eta 0.85,
rho 0.98; ``Q_b = Q_nom`` at the start.

FB-b (rules 1.2), at the end of every ``update`` (after the command): the valve model
(first-order lag tau_v 0.1 s of the returned command, x_0 = 0) gives the period mean m_k,
the stroke reading gives v_k = (s_{k+1} - s_k) / T_s and r_k = v_k / m_k. Evaluated legs:
(1) m >= 0.3 v_max, (2) s_{k+1} < stroke_soft_max - 0.02 m, (3) every leg
|a_k - a_{k-1}| <= 0.1 v_max (a_{-1} = 0, as x_0 = 0), and for U only (4) the load-change
gate |F_{k+1} - F_k| <= 0.02 k_oil(s_{k+1}) m_k T_s. U: >= 3 evaluated legs with r < 0.93;
A97: all four legs evaluated, sum A_h v / sum A_h m < 0.97, periods k and k+1 both TOUCH and
no ``touch_seen`` leg. Each rule confirms after 2 periods in a row (a false period, or a period
outside its stage condition, sets its counter to 0); a confirmation sets
``Q_b <- max(0.5 Q_nom, min(Q_b, 0.97 Q_del))`` (``Q_del`` = sum_i A_i(v_i) |v_i|), sets that
counter to 0 and adds ``INFO_FLOW_BUDGET_CUT:<U|A97>``; Q_b never rises again in a run.
"Period k is TOUCH" = the controller phase at the end of update k (the phase
``verdict_metrics.chunk_phases`` gives the chunks that period's command drives).

Bundles (rules 3.2): F-0 4, F-1 92, F-2 192 (LF only; L = stored ``v5/las/las_T1.jsonl`` /
``las_T2.jsonl`` b0 act lines), F-3 32, F-4 28 (rev1 1: verdict case ``R2ra``, i.e. ``R2``
with decision ``reanchor_on``, instead of ``R2``), F-5 12. Output
``06_analysis/03_hydraulic/coupled/v5/fb/fb_F<n>.jsonl`` (appended; finished lines skipped).

Run identity (``fb.identity`` of every line): ``git rev-parse HEAD``, whether tracked files
differ from it (``git_dirty``, ``dirty_files``), the sha256 of ``fb_targeted.py``,
``las_targeted.py`` and ``03_src/outrigger_sim/control/c2.py``, and the thread variables (set
to 1 here, not ``setdefault``; a worker whose value is not 1 writes an error line). Resuming
into a file whose lines carry another commit or other tool hashes stops, so does an F-0 file
of another identity (H-2) and a line of another identity arriving during the batch.
``fb.events_total`` / ``events_truncated`` record how many events the run had against the
first 400 that ``verdict_runs._finish`` stores in ``events``.

Stops (rules 6, rev1 3): H-1 (rules, addendum rev1 or design missing, a ``.sha256`` without a
value, or the sha256 of the rules or of rev1 is not the sealed one) before any run; H-2:
F-1 .. F-5 run only after F-0 passed C-7 (``fb_judge.check_c7``); H-3: an error line is
retried once, a second error stops the bundle (a run whose plant or controller was not
captured is an error line); H-4: 5 C-2 violations in a bundle stop it (finished lines stay,
and the lines already in the file count).

Usage (dynamics-dev python, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/fb_targeted.py list [--bundle F-0 ..]
  python -I -B 04_scripts/04_hydraulic/coupled/fb_targeted.py run --bundle F-0
      [--workers 4] [--affinity HEX] [--out <jsonl>] [--keys K1,K2] [--limit N]
Exit codes: 0 done / counts equal, 1 mismatch, a stop (H-2 .. H-4) or a run error,
2 input error (H-1 included).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import queue
import re
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from multiprocessing import get_context
from pathlib import Path

# As run_v5: one BLAS / OpenMP thread, set before numpy loads (here and in every spawned
# worker, which inherits them). Multi-threaded reductions change the command hash, so the
# value is forced (a caller's other value would make lines of another run identity).
THREAD_VARIABLES = ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                    "NUMBA_NUM_THREADS")
for _name in THREAD_VARIABLES:
    os.environ[_name] = "1"
os.environ.setdefault("MKL_THREADING_LAYER", "TBB")

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

RULES_DIR = ROOT / "06_analysis" / "02_control" / "verif_matrix"
RULES_PATH = RULES_DIR / "fb_targeted_rules.md"
RULES_SHA_PATH = RULES_DIR / "fb_targeted_rules.sha256"
DESIGN_PATH = RULES_DIR / "fb_design.md"
RULES_SHA256 = "e517b0d08bc46100bb20ec3824de5066cdb8890715f03f3e9a1299437e5dcb89"
"""``fb_targeted_rules.sha256`` (sealed 2026-11-08 17:19:52 +09:00)."""
RULES_REV1_PATH = RULES_DIR / "fb_targeted_rules_rev1.md"
RULES_REV1_SHA_PATH = RULES_DIR / "fb_targeted_rules_rev1.sha256"
RULES_REV1_SHA256 = "0163b6c3f065bd18320c6857c605186112f411ff7c20e02f403bf82a26ba9d63"
"""``fb_targeted_rules_rev1.sha256`` (sealed addendum 2026-11-08 17:45:04 +09:00: F-4 R2 ->
R2ra, readings I-1 .. I-8, H-1 extended to rev1)."""
V5_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
OUT_DIR = V5_DIR / "fb"
LAS_STORED_PATHS = (V5_DIR / "las" / "las_T1.jsonl", V5_DIR / "las" / "las_T2.jsonl")
"""Rules 3.2 F-2: the L lines (b0 act) of the LAS-b T-1 / T-2 stages."""
YAML_PATH = ROOT / "02_params" / "rexome33.yaml"
M3_S_TO_L_MIN = 6.0e4

# Rules 1.1 / 1.2 values (sealed; no variants, rules 2 last line).
ETA_V_MIN = 0.85
BUDGET_MARGIN = 0.98
TAU_V_S = 0.1
MIN_MEAN_FRACTION = 0.3
SOFT_END_MARGIN_M = 0.02
STEADY_FRACTION = 0.1
LOAD_GATE_FRACTION = 0.02
U_RATIO = 0.93
U_MIN_LEGS = 3
A97_RATIO = 0.97
CONFIRM_PERIODS = 2
MIN_EVALUATED_LEGS = 2
CUT_FACTOR = 0.97
FLOOR_FRACTION = 0.5
OPEN_LOOP_S = 8.0
TIME_TOLERANCE_S = 1e-9
RULE_U = "U"
RULE_A97 = "A97"
CUT_EVENT = "INFO_FLOW_BUDGET_CUT"
PHASE_TOUCH = "touch"

BUNDLES = ("F-0", "F-1", "F-2", "F-3", "F-4", "F-5")
BUNDLE_COUNTS = {"F-0": 4, "F-1": 92, "F-2": 192, "F-3": 32, "F-4": 28, "F-5": 12}
F0_KEYS = ("D1|H-R-A|rigid+J1@FR|T|diag-op|K1|VB|e0", "D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0")
F1_EXTRA_ETA = 0.70
F1_EXTRA_CASES = ("S2", "S3", "R3", "S5")
F3_VB_ROWS = (
    "D1|H-S-0|G1|T|flat|K1", "D1|H-S-0|G1|T|diag-rec|K1",
    "D1|H-S-0|J1|T|flat|K1", "D1|H-S-0|J1|T|diag-rec|K1",
    "D1|H-S-0|J2|T|flat|K1", "D1|H-S-0|J2|T|diag-rec|K1",
    "D1|H-S-1|S1|T|flat|K1", "D1|H-S-1|S1|M|flat|K1", "D1|H-S-1|S1|B|flat|K1",
    "D1|H-S-A|G1+J1@FL|T|flat|K1", "D1|H-S-A|G1+J1@RL|T|flat|K1",
    "D1|H-S-A|G1+J1@FR|T|diag-psa-soil|K1", "D1|H-S-A-J2|G1+J2@FL|T|flat|K1",
    "D1|H-R-A-J2|rigid+J2@FL|T|flat|K1", "D1|H-R-A-S1|rigid+S1@FL|T|flat|K1",
)
F3_V0_KEYS = ("D1|H-S-0|J1|T|flat|K1|V0|e0",)
F4_D1_ROWS = (
    "D1|H-R-A-stop|rigid+J1@RL|T|fup-op|K1", "D1|H-S-C|J1|T|flat|K1|c-mid@FL",
    "D1|H-S-C|J1|T|flat|K1|c-mid@RL", "D1|H-S-C-g|J1|T|fdown-rec|K1|c-mid@FL|dsb_gated_off",
)
F4_CASES = ("R2ra", "R12", "R14", "R15", "R16")
"""Rules 3.2 F-4 with rev1 1: verdict cases at the first ``run_v5._phase_jobs`` job (eps 0).
``R2ra`` is case ``R2`` with decision ``reanchor_on`` (the original ``R2``, decision
``reanchor_off``, skips the REANCHOR path the row is meant to test, so it is not run)."""
F4_SETTINGS = ("V0", "VB")
F5_ROWS = ("D1|H-S-0|J1|T|flat|K1", "D1|H-S-0|J2|T|flat|K1", "D1|H-R-0|rigid|T|flat|K1")
F5_SETTINGS = ("VB", "V0")
C2_STOP_COUNT = 5
"""Rules 6 H-4."""

LAS_CANDIDATE = "b0"
LAS_MODE = "act"
LAS_SOURCE = "03_src c2 meta liftoff_approach_slow"
LAS_PARAM_SETTINGS = {
    "alpha": "sum_on_fraction_W", "beta": "light_leg_fraction_of_F_min",
    "gamma": "slow_mean_fraction", "alpha_end": "sum_off_fraction_W", "n_end": "off_periods",
    "t_max_s": "max_s", "rho_on": "rho_on",
}
"""``las_targeted.LasParams`` field -> ``c2.LiftoffApproachSlowSettings`` field."""
C2_PATH = ROOT / "03_src" / "outrigger_sim" / "control" / "c2.py"
IDENTITY_FILES = {"fb_targeted.py": HERE / "fb_targeted.py",
                  "las_targeted.py": HERE / "las_targeted.py", "c2.py": C2_PATH}
"""Files whose sha256 every line records (rules 3.1 run identity)."""
IDENTITY_KEYS = ("git_head", "sha256")
"""What must be equal between lines of one bundle file (resume, H-2, during a batch)."""
DIRTY_FILES_SHOWN = 20
GIT_TIMEOUT_S = 60
EVENTS_STORED_LIMIT = 400
"""``verdict_runs._finish`` keeps the first 400 events in ``events`` (recorded, not changed)."""
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


# ------------------------------------------------------------------------------- candidates
@dataclass(frozen=True)
class FbParams:
    """One FB candidate (rules 2). ``has_wrapper`` False = L (no FB wrapper installed)."""

    has_wrapper: bool
    enable: bool = False
    open_loop_s: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict) -> FbParams:
        return cls(**values)


CANDIDATES: dict[str, FbParams] = {
    "L": FbParams(has_wrapper=False),
    "LF": FbParams(has_wrapper=True, enable=True),
    "LF-off": FbParams(has_wrapper=True, enable=False),
    "OL-L": FbParams(has_wrapper=True, enable=False, open_loop_s=OPEN_LOOP_S),
    "OL-LF": FbParams(has_wrapper=True, enable=True, open_loop_s=OPEN_LOOP_S),
}
BUNDLE_CANDIDATES = {"F-0": ("L", "LF-off"), "F-1": ("L", "LF"), "F-2": ("LF",),
                     "F-3": ("L", "LF"), "F-4": ("L", "LF"), "F-5": ("OL-L", "OL-LF")}


# ------------------------------------------------------------------------------- FB-a
def areas_for(speeds, head_area_m2, annulus_area_m2) -> np.ndarray:
    """``A_i(u_i)``: head area for an extending (or still) leg, annulus area retracting."""
    speeds = np.asarray(speeds, float)
    return np.where(speeds < 0.0, annulus_area_m2, head_area_m2)


def command_flow_m3_s(speeds, head_area_m2, annulus_area_m2) -> float:
    """``Q(u) = sum_i A_i(u_i) |u_i|``."""
    speeds = np.asarray(speeds, float)
    return float(np.sum(areas_for(speeds, head_area_m2, annulus_area_m2) * np.abs(speeds)))


def budget_scale(flow_m3_s: float, budget_m3_s: float) -> float:
    """``min(1, Q_b / Q(u))`` (1 for a zero command)."""
    if flow_m3_s <= budget_m3_s:
        return 1.0
    return budget_m3_s / flow_m3_s


def nominal_budget_m3_s(pump_flow_m3_s: float) -> float:
    """``Q_nom = rho eta_v,min Q_th`` (rules 1.1)."""
    return BUDGET_MARGIN * ETA_V_MIN * pump_flow_m3_s


def pump_flow_m3_s(yaml_path: Path = YAML_PATH) -> float:
    """YAML ``actuator.pump_flow_m3_s``."""
    import yaml

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    return float(data["actuator"]["pump_flow_m3_s"])


# ------------------------------------------------------------------------------- FB-b
@dataclass(frozen=True)
class DetectGeometry:
    """What the detector reads of ``C2Geometry`` (a copy keeps the pure functions testable)."""

    head_area_m2: np.ndarray
    annulus_area_m2: np.ndarray
    max_speed_m_s: float
    stroke_soft_max_m: float
    oil_bulk_modulus_Pa: float
    oil_dead_length_m: float

    @classmethod
    def of(cls, geometry) -> DetectGeometry:
        return cls(np.asarray(geometry.head_area_m2, float).copy(),
                   np.asarray(geometry.annulus_area_m2, float).copy(),
                   float(geometry.max_speed_m_s), float(geometry.stroke_soft_max_m),
                   float(geometry.oil_bulk_modulus_Pa), float(geometry.oil_dead_length_m))

    def oil_stiffness_N_m(self, stroke_m) -> np.ndarray:
        """``C2Geometry.oil_stiffness_N_m``: ``beta A_h / (dead + e)``."""
        return (self.oil_bulk_modulus_Pa * self.head_area_m2
                / (self.oil_dead_length_m + np.asarray(stroke_m, float)))


@dataclass(frozen=True)
class PeriodSample:
    """Period k as the evaluation in update k+1 needs it."""

    stroke_m: np.ndarray
    force_N: np.ndarray
    mean_m_s: np.ndarray
    """``m_k``: valve-model mean of the returned command ``a_k`` over the period."""
    command_m_s: np.ndarray
    previous_command_m_s: np.ndarray
    phase: str


@dataclass
class Cut:
    t_s: float
    rule: str
    budget_L_min: float
    delivered_L_min: float


@dataclass
class FbState:
    """Per-controller FB state (instance attribute ``_fb_run``) and the ``fb`` meta."""

    nominal_m3_s: float
    budget_m3_s: float
    valve_m_s: np.ndarray = field(default_factory=lambda: np.zeros(4))
    previous: PeriodSample | None = None
    u_count: int = 0
    a97_count: int = 0
    cuts: list[Cut] = field(default_factory=list)
    acted_periods: dict[str, int] = field(default_factory=dict)
    min_scale: float = 1.0
    max_flow_over_budget: float = 0.0
    evaluated_periods: int = 0
    r_min: list[float] = field(default_factory=lambda: [math.inf] * 4)
    sum_ratio_min: float = math.inf
    """Smallest sum A_h v / sum A_h m over periods with >= 2 evaluated legs."""
    a97_ratio_min: float = math.inf
    """The same over the periods A97 evaluated (4 legs, TOUCH free air)."""
    t_first_touch_s: float | None = None
    level_t0_s: float | None = None
    open_loop_periods: int = 0


@dataclass(frozen=True)
class Evaluation:
    """Result of one evaluation period (for tests and the meta)."""

    evaluated: np.ndarray
    ratios: np.ndarray
    sum_ratio: float | None
    is_u_period: bool
    is_a97_period: bool
    fired: tuple[str, ...]


def valve_step(valve_m_s: np.ndarray, command_m_s: np.ndarray, period_s: float,
               tau_v_s: float = TAU_V_S) -> tuple[np.ndarray, np.ndarray]:
    """(m_k, x_{k+1}) of the first-order valve model for the command ``a_k`` (rules 1.2)."""
    decay = math.exp(-period_s / tau_v_s)
    mean_gain = tau_v_s / period_s * (1.0 - decay)
    mean = command_m_s + (valve_m_s - command_m_s) * mean_gain
    return mean, command_m_s + (valve_m_s - command_m_s) * decay


def evaluated_legs(sample: PeriodSample, stroke_now_m: np.ndarray,
                   geometry: DetectGeometry) -> np.ndarray:
    """Conditions 1 .. 3 of rules 1.2 per leg."""
    v_max = geometry.max_speed_m_s
    is_moving = sample.mean_m_s >= MIN_MEAN_FRACTION * v_max
    is_short_of_end = stroke_now_m < geometry.stroke_soft_max_m - SOFT_END_MARGIN_M
    change = np.abs(sample.command_m_s - sample.previous_command_m_s)
    is_steady = bool(np.all(change <= STEADY_FRACTION * v_max))
    return is_moving & is_short_of_end & is_steady


def load_change_gate(sample: PeriodSample, stroke_now_m: np.ndarray, force_now_N: np.ndarray,
                     geometry: DetectGeometry, period_s: float) -> np.ndarray:
    """Condition 4 (U only): |F_{k+1} - F_k| <= 0.02 k_oil(s_{k+1}) m_k T_s."""
    allowed = (LOAD_GATE_FRACTION * geometry.oil_stiffness_N_m(stroke_now_m)
               * sample.mean_m_s * period_s)
    return np.abs(force_now_N - sample.force_N) <= allowed


def evaluate_period(state: FbState, sample: PeriodSample, stroke_now_m: np.ndarray,
                    force_now_N: np.ndarray, phase_now: str, has_touch_seen: bool,
                    geometry: DetectGeometry, period_s: float) -> Evaluation:
    """Counters of U and A97 for period k (``sample``) in update k+1; the confirmed rules.

    The caller applies the cut of each confirmed rule (:func:`apply_cut`).
    """
    speeds = (stroke_now_m - sample.stroke_m) / period_s
    evaluated = evaluated_legs(sample, stroke_now_m, geometry)
    safe_mean = np.where(evaluated, sample.mean_m_s, 1.0)
    ratios = np.where(evaluated, speeds / safe_mean, np.nan)
    if int(evaluated.sum()) < MIN_EVALUATED_LEGS:
        state.u_count = state.a97_count = 0
        return Evaluation(evaluated, ratios, None, False, False, ())
    state.evaluated_periods += 1
    for leg in np.flatnonzero(evaluated):
        state.r_min[leg] = min(state.r_min[leg], float(ratios[leg]))
    head = geometry.head_area_m2
    delivered_sum = np.sum((head * speeds)[evaluated])
    sum_ratio = float(delivered_sum / np.sum((head * sample.mean_m_s)[evaluated]))
    state.sum_ratio_min = min(state.sum_ratio_min, sum_ratio)
    u_legs = evaluated & load_change_gate(sample, stroke_now_m, force_now_N, geometry, period_s)
    is_u_period = int(np.sum(u_legs & (ratios < U_RATIO))) >= U_MIN_LEGS
    state.u_count = state.u_count + 1 if is_u_period else 0
    is_a97_stage = (sample.phase == PHASE_TOUCH and phase_now == PHASE_TOUCH
                    and not has_touch_seen)
    is_a97_period = False
    if is_a97_stage and int(evaluated.sum()) == 4:
        state.a97_ratio_min = min(state.a97_ratio_min, sum_ratio)
        is_a97_period = sum_ratio < A97_RATIO
    state.a97_count = state.a97_count + 1 if (is_a97_stage and is_a97_period) else 0
    fired = []
    if state.u_count >= CONFIRM_PERIODS:
        fired.append(RULE_U)
        state.u_count = 0
    if state.a97_count >= CONFIRM_PERIODS:
        fired.append(RULE_A97)
        state.a97_count = 0
    return Evaluation(evaluated, ratios, sum_ratio, is_u_period, is_a97_period, tuple(fired))


def apply_cut(state: FbState, rule: str, delivered_speeds_m_s: np.ndarray,
              geometry: DetectGeometry, t_s: float) -> str:
    """``Q_b <- max(0.5 Q_nom, min(Q_b, 0.97 Q_del))``; returns the event name."""
    delivered = command_flow_m3_s(delivered_speeds_m_s, geometry.head_area_m2,
                                  geometry.annulus_area_m2)
    state.budget_m3_s = max(FLOOR_FRACTION * state.nominal_m3_s,
                            min(state.budget_m3_s, CUT_FACTOR * delivered))
    state.cuts.append(Cut(round(float(t_s), 6), rule, state.budget_m3_s * M3_S_TO_L_MIN,
                          delivered * M3_S_TO_L_MIN))
    return f"{CUT_EVENT}:{rule}"


def detect_step(state: FbState, stroke_m, force_N, command_m_s, phase: str,
                has_touch_seen: bool, geometry: DetectGeometry, period_s: float,
                t_s: float) -> list[str]:
    """One update end: evaluate period k (if any), then the valve model for ``a_{k+1}``.

    Returns:
        The event names to add (one per confirmed rule).
    """
    stroke_m = np.asarray(stroke_m, float).copy()
    force_N = np.asarray(force_N, float).copy()
    command_m_s = np.asarray(command_m_s, float).copy()
    events = []
    previous = state.previous
    if previous is not None:
        evaluation = evaluate_period(state, previous, stroke_m, force_N, phase, has_touch_seen,
                                     geometry, period_s)
        delivered = (stroke_m - previous.stroke_m) / period_s
        events = [apply_cut(state, rule, delivered, geometry, t_s) for rule in evaluation.fired]
    if phase == PHASE_TOUCH and state.t_first_touch_s is None:
        state.t_first_touch_s = float(t_s)
    mean, state.valve_m_s = valve_step(state.valve_m_s, command_m_s, period_s)
    previous_command = np.zeros(4) if previous is None else previous.command_m_s
    state.previous = PeriodSample(stroke_m, force_N, mean, command_m_s, previous_command, phase)
    return events


def budget_output(state: FbState, output_m_s: np.ndarray, geometry, phase: str) -> np.ndarray:
    """FB-a on the ramp output: the input object when the budget does not act."""
    flow = command_flow_m3_s(output_m_s, geometry.head_area_m2, geometry.annulus_area_m2)
    state.max_flow_over_budget = max(state.max_flow_over_budget, flow / state.budget_m3_s)
    scale = budget_scale(flow, state.budget_m3_s)
    if scale >= 1.0:
        return output_m_s
    state.acted_periods[phase] = state.acted_periods.get(phase, 0) + 1
    state.min_scale = min(state.min_scale, scale)
    return output_m_s * scale


def _finite_or_none(value: float) -> float | None:
    return value if math.isfinite(value) else None


def budget_meta(state: FbState | None, params: FbParams) -> dict | None:
    """Rules 3.1 budget meta of a run (``None`` without an FB wrapper)."""
    if state is None:
        return None
    return {"enable": params.enable, "Q_nom_L_min": state.nominal_m3_s * M3_S_TO_L_MIN,
            "Q_b_final_L_min": state.budget_m3_s * M3_S_TO_L_MIN,
            "acted_periods": dict(state.acted_periods), "min_scale": state.min_scale,
            "max_Q_over_Qb": state.max_flow_over_budget,
            "cuts": [asdict(cut) for cut in state.cuts],
            "evaluated_periods": state.evaluated_periods,
            "r_min": [_finite_or_none(value) for value in state.r_min],
            "sum_ratio_min": _finite_or_none(state.sum_ratio_min),
            "a97_ratio_min": _finite_or_none(state.a97_ratio_min),
            "t_first_touch_s": state.t_first_touch_s, "level_t0_s": state.level_t0_s,
            "open_loop_periods": state.open_loop_periods}


# ------------------------------------------------------------------------------- the wrapper
_INSTALLED: dict = {}


def _state_of(controller, nominal_m3_s: float) -> FbState:
    state = controller.__dict__.get("_fb_run")
    if state is None:
        state = FbState(nominal_m3_s=nominal_m3_s, budget_m3_s=nominal_m3_s)
        controller.__dict__["_fb_run"] = state
    return state


def install(params: FbParams, controller_class=None, phase_enum=None,
            pump_m3_s: float | None = None) -> None:
    """Patch the controller class of this process (once per worker, after LAS-b).

    Args:
        params: The candidate; ``has_wrapper`` must be true.
        controller_class: ``c2.C2Controller`` by default (tests pass a stand-in).
        phase_enum: ``c2.C2Phase`` by default (needs ``LEVEL`` and ``DONE``).
        pump_m3_s: ``Q_th``; None = YAML ``actuator.pump_flow_m3_s``.

    Raises:
        RuntimeError: Installed twice in one process.
        ValueError: A candidate without a wrapper (L).
    """
    if _INSTALLED:
        raise RuntimeError("fb_targeted.install: already installed in this process")
    if not params.has_wrapper:
        raise ValueError("candidate L has no FB wrapper")
    if controller_class is None or phase_enum is None:
        from outrigger_sim.control import c2

        controller_class = controller_class or c2.C2Controller
        phase_enum = phase_enum or c2.C2Phase
    nominal = nominal_budget_m3_s(pump_flow_m3_s() if pump_m3_s is None else pump_m3_s)
    cls = controller_class
    original_ramp = cls._apply_output_ramp
    original_update = cls.update
    original_level_step = cls._level_step

    def apply_output_ramp(self, leg_speeds):
        output = original_ramp(self, leg_speeds)
        if not params.enable:
            return output
        state = _state_of(self, nominal)
        scaled = budget_output(state, output, self.geometry, str(self._state.phase))
        if scaled is not output:
            self._state.previous_output_m_s = scaled
        return scaled

    def update(self, measurements):
        command = original_update(self, measurements)
        if not params.enable:
            return command
        state = _state_of(self, nominal)
        reading = self._state.last_reading
        geometry = DetectGeometry.of(self.geometry)
        events = detect_step(state, reading.motor_stroke_m, reading.cylinder_force_N,
                             command.leg_speed_m_s, str(self._state.phase),
                             bool(np.any(self._state.touch_seen)), geometry,
                             float(self.config.period_s), float(measurements.t_s))
        for name in events:
            self._add_event(measurements.t_s, name)
        return command

    def level_step(self, reading):
        speeds = original_level_step(self, reading)
        if params.open_loop_s is None:
            return speeds
        state = _state_of(self, nominal)
        if self._state.phase not in (phase_enum.LEVEL, phase_enum.DONE):
            return speeds
        t_s = float(reading.t_s)
        if state.level_t0_s is None:
            state.level_t0_s = t_s
        if t_s - state.level_t0_s >= params.open_loop_s - TIME_TOLERANCE_S:
            return speeds
        state.open_loop_periods += 1
        if self._state.phase is phase_enum.DONE:
            self._state.phase = phase_enum.LEVEL
        return np.full(4, float(self.geometry.max_speed_m_s))

    cls._apply_output_ramp = apply_output_ramp
    cls.update = update
    cls._level_step = level_step
    _INSTALLED.update(params=params, cls=cls, originals=(original_ramp, original_update,
                                                         original_level_step))


def uninstall() -> None:
    """Undo :func:`install` (tests only; workers never uninstall)."""
    if not _INSTALLED:
        return
    cls = _INSTALLED["cls"]
    cls._apply_output_ramp, cls.update, cls._level_step = _INSTALLED["originals"]
    _INSTALLED.clear()


# ------------------------------------------------------------------------------- jobs
def fb_key(job: dict) -> str:
    """``las_targeted.composite_key`` of a D-1 job; ``<case>|<setting>|eta<eta>|e<eps>``
    (+ ``|o<offset>``, ``|<decision>``) of a verdict / U-9 job."""
    if "d1" in job:
        import las_targeted

        return las_targeted.composite_key(job)
    eta = job.get("eta_v")
    key = f"{job['case']}|{job['setting']}|eta{'def' if eta is None else f'{eta:g}'}"
    key += f"|e{float(job.get('eps', 0.0)):g}"
    if job.get("offset_s") is not None:
        key += f"|o{job['offset_s']:g}"
    if job.get("decision"):
        key += f"|{job['decision']}"
    return key


def _d1_jobs(keys) -> list[dict]:
    import las_targeted

    return las_targeted.jobs_for_keys(list(keys))


def _with_suffix(rows, setting: str) -> list[str]:
    return [f"{row}|{setting}|e0" for row in rows]


def bundle_base_jobs(bundle: str) -> list[dict]:
    """``run_v5`` jobs of a bundle (rules 3.2), before the candidate is attached.

    Raises:
        ValueError: Unknown bundle.
    """
    import las_targeted
    import run_v5

    if bundle == "F-0":
        return _d1_jobs(F0_KEYS)
    if bundle == "F-1":
        extra = [{"case": case, "eps": 0.0, "setting": "VB", "eta_v": F1_EXTRA_ETA,
                  "u9_metrics": True} for case in F1_EXTRA_CASES]
        return run_v5.u9_targeted_jobs() + extra
    if bundle == "F-2":
        return _d1_jobs(las_targeted.stage_keys("T-1") + las_targeted.stage_keys("T-2"))
    if bundle == "F-3":
        return _d1_jobs(_with_suffix(F3_VB_ROWS, "VB") + list(F3_V0_KEYS))
    if bundle == "F-4":
        verdict = [{**run_v5._phase_jobs(case)[0], "setting": setting, "u9_metrics": True}
                   for case in F4_CASES for setting in F4_SETTINGS]
        return _d1_jobs(_with_suffix(F4_D1_ROWS, "VB")) + verdict
    if bundle == "F-5":
        keys = [key for setting in F5_SETTINGS for key in _with_suffix(F5_ROWS, setting)]
        return _d1_jobs(keys)
    raise ValueError(f"unknown bundle {bundle!r}")


def bundle_jobs(bundle: str, mask: int | None = None, keys: list[str] | None = None
                ) -> list[dict]:
    """One job per (key, candidate); the candidates of a key next to each other (H-4 pairs
    finish together), VB first (the longer runs start early)."""
    base = bundle_base_jobs(bundle)
    if keys is not None:
        wanted = set(keys)
        base = [job for job in base if fb_key(job) in wanted]
    ordered = sorted(base, key=lambda job: job["setting"] != "VB")
    jobs = []
    for job in ordered:
        for name in BUNDLE_CANDIDATES[bundle]:
            jobs.append({**job, "mask": mask,
                         "fb": {"name": name, "bundle": bundle,
                                "params": CANDIDATES[name].to_dict()}})
    return jobs


# ------------------------------------------------------------------------------- H-1
def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed_check(rules_path: Path = RULES_PATH, sha_path: Path = RULES_SHA_PATH,
                 design_path: Path = DESIGN_PATH, rev1_path: Path = RULES_REV1_PATH,
                 rev1_sha_path: Path = RULES_REV1_SHA_PATH) -> list[str]:
    """Problems of H-1 (empty = the sealed rules, the sealed addendum rev1 and the design copy
    are there; rev1 3 adds the addendum to the original check)."""
    problems = [f"missing {path}"
                for path in (rules_path, sha_path, rev1_path, rev1_sha_path, design_path)
                if not path.exists()]
    if problems:
        return problems
    problems += _seal_problems(rules_path, sha_path, RULES_SHA256)
    problems += _seal_problems(rev1_path, rev1_sha_path, RULES_REV1_SHA256)
    return problems


def _sealed_value(sha_path: Path) -> str | None:
    """The first token of a ``.sha256`` file when it is a sha256 hex value, else None."""
    try:
        tokens = sha_path.read_text(encoding="utf-8").split()
    except (OSError, UnicodeDecodeError):
        return None
    if not tokens or SHA256_PATTERN.fullmatch(tokens[0].lower()) is None:
        return None
    return tokens[0].lower()


def _seal_problems(text_path: Path, sha_path: Path, expected_sha256: str) -> list[str]:
    """The ``.sha256`` file holds ``expected_sha256`` (first token) and the text hashes to it;
    a file without a sha256 value (empty, unreadable) is a problem too (H-1)."""
    sealed = _sealed_value(sha_path)
    if sealed is None:
        return [f"{sha_path.name} holds no sha256 value"]
    problems = []
    if sealed != expected_sha256:
        problems.append(f"{sha_path.name} holds {sealed}, the tool expects {expected_sha256}")
    digest = file_sha256(text_path)
    if digest != sealed:
        problems.append(f"{text_path.name} sha256 {digest} != sealed {sealed}")
    return problems


# ------------------------------------------------------------------------------- identity
def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                               text=True, encoding="utf-8", check=True, timeout=GIT_TIMEOUT_S)
    return completed.stdout


def thread_values(environ=None) -> dict[str, str | None]:
    """The thread variables (and the MKL threading layer) as the process sees them."""
    environ = os.environ if environ is None else environ
    return {name: environ.get(name) for name in (*THREAD_VARIABLES, "MKL_THREADING_LAYER")}


def thread_problems(values: dict[str, str | None]) -> list[str]:
    """Thread variables that are not 1 (such a run would not reproduce the command hash)."""
    return [f"{name}={values.get(name)!r}" for name in THREAD_VARIABLES
            if values.get(name) != "1"]


def run_identity(root: Path = ROOT, files: dict[str, Path] | None = None) -> dict:
    """Commit, tracked-file changes, tool sha256 and thread variables of this run.

    Untracked files do not count as dirty: the sealed rules are untracked copies by design.

    Raises:
        subprocess.CalledProcessError, OSError: git or a tool file is not there.
    """
    files = IDENTITY_FILES if files is None else files
    dirty = _git(root, "status", "--porcelain", "--untracked-files=no").splitlines()
    return {"git_head": _git(root, "rev-parse", "HEAD").strip(), "git_dirty": bool(dirty),
            "dirty_files": [line[3:] for line in dirty[:DIRTY_FILES_SHOWN]],
            "sha256": {name: file_sha256(path) for name, path in files.items()},
            "threads": thread_values()}


def identity_mismatch(recorded: dict | None, current: dict) -> list[str]:
    """How a line's ``fb.identity`` differs from ``current`` (commit and tool hashes)."""
    if not recorded:
        return ["no run identity"]
    return [f"{name} {recorded.get(name)} != {current.get(name)}" for name in IDENTITY_KEYS
            if recorded.get(name) != current.get(name)]


def stale_lines(lines: list[dict], current: dict) -> list[str]:
    """Labels of lines whose run identity is not ``current`` (resume, H-2)."""
    out = []
    for record in lines:
        fb = record.get("fb") or {}
        problems = identity_mismatch(fb.get("identity"), current)
        if problems:
            out.append(f"{fb.get('candidate')} {fb.get('key')}: {'; '.join(problems)}")
    return out


# ------------------------------------------------------------------------------- LAS-b (03_src)
def las_params_of(settings: dict) -> dict:
    """``LasParams.to_dict`` of ``asdict(LiftoffApproachSlowSettings)`` (``kind`` "lasb")."""
    values = {name: settings[field_name] for name, field_name in LAS_PARAM_SETTINGS.items()}
    return {"kind": "lasb", **values}


def preset_las_problems(settings) -> list[str]:
    """Why ``settings`` is not LAS-b ``b0`` acting (rules 3.1: L = the 03_src LAS-b)."""
    import las_targeted

    if settings is None:
        return ["no liftoff_approach_slow settings"]
    problems = []
    if not settings.enable:
        problems.append("liftoff_approach_slow.enable is False")
    if not settings.require_soil_response:
        problems.append("liftoff_approach_slow.require_soil_response is False")
    expected = las_targeted.CANDIDATES[LAS_CANDIDATE].to_dict()
    actual = las_params_of(asdict(settings))
    problems += [f"{name} {actual[name]!r} != b0 {expected[name]!r}" for name in actual
                 if actual[name] != expected[name]]
    return problems


def check_preset_las() -> None:
    """The R8 preset of this process has LAS-b ``b0`` on (the condition of L).

    Raises:
        RuntimeError: LAS-b off or other values, or the ``las_targeted`` wrapper installed.
    """
    import las_targeted

    from outrigger_sim.control import c2

    if las_targeted._INSTALLED:
        raise RuntimeError("the las_targeted wrapper is installed: LAS-b would act twice")
    problems = preset_las_problems(c2.C2Config().with_10hz_d1().liftoff_approach_slow)
    if problems:
        raise RuntimeError(f"R8 preset is not LAS-b b0: {problems}")


def las_block_from_meta(meta: dict, soil_enable: bool, weight_ref_N: float,
                        harness: dict | None, leg_order=("FL", "FR", "RL", "RR")) -> dict:
    """The ``las`` block of a line from the controller meta ``liftoff_approach_slow``, in the
    fields of ``las_targeted.las_block`` (mapping in the module docstring)."""
    import las_targeted

    block = {"candidate": LAS_CANDIDATE, "params": las_params_of(meta["settings"]),
             "mode": LAS_MODE, "source": LAS_SOURCE,
             **las_targeted.loc_delay_record(harness)}
    if "start_s" not in meta:
        return {**block, "wrapper_reached": False}
    leg = meta["start_leg"]
    block.update(wrapper_reached=True, soil_enable=bool(soil_enable),
                 W_ref_N=float(weight_ref_N), start_t_s=meta["start_s"],
                 start_leg=None if leg is None else list(leg_order).index(leg),
                 end_t_s=meta["end_s"], end_reason=meta["end_reason"],
                 active_periods=meta["active_periods"], scaled_periods=meta["scaled_periods"],
                 s7p_first=None, start_rho=meta["start_rho"],
                 start_rho_prev=meta["start_rho_prev"])
    return block


def las_block_of(controller, harness: dict | None) -> dict:
    """The ``las`` block of a finished run (its controller must have LAS-b b0 on).

    Raises:
        RuntimeError: The run's controller does not have LAS-b ``b0`` on.
    """
    from outrigger_sim.control import c2

    settings = getattr(controller.config, "liftoff_approach_slow", None)
    problems = preset_las_problems(settings)
    if problems:
        raise RuntimeError(f"the run's controller is not LAS-b b0: {problems}")
    return las_block_from_meta(controller.meta()["liftoff_approach_slow"],
                               controller.config.soil.enable,
                               controller._reference_weight_N(), harness, c2.LEG_ORDER)


def event_count_record(controller) -> dict:
    """How many events the run stored against the ``events`` limit of ``verdict_runs``."""
    import verdict_runs

    total = len(verdict_runs._stored_events(controller))
    return {"events_total": total, "events_truncated": total > EVENTS_STORED_LIMIT,
            "events_stored_limit": EVENTS_STORED_LIMIT}


# ------------------------------------------------------------------------------- worker
_CAPTURE: dict = {}


def _capture_runs() -> None:
    """Keep the plant and controller of the finished run (as ``las_targeted``)."""
    import d1_runs
    import verdict_runs

    original_finish = verdict_runs._finish

    def finish(plant, controller, extra, t4h=None, **options):
        _CAPTURE.update(finish_plant=plant, finish_controller=controller)
        return original_finish(plant, controller, extra, t4h, **options)

    verdict_runs._finish = finish
    original_record = d1_runs.d1_record

    def d1_record(row, setting_name, eps, result, plant, controller, harness):
        _CAPTURE.update(plant=plant, controller=controller, harness=harness)
        return original_record(row, setting_name, eps, result, plant, controller, harness)

    d1_runs.d1_record = d1_record


def _run_objects(job: dict):
    """(plant, controller) of the run's record (``las_targeted.run_controller`` rule)."""
    if "d1" in job:
        return _CAPTURE.get("plant"), _CAPTURE.get("controller")
    return _CAPTURE.get("finish_plant"), _CAPTURE.get("finish_controller")


def _limited_counts(rows: np.ndarray) -> np.ndarray:
    from harness_flow import COLUMN

    masks = rows[:, COLUMN["limited_mask"]].astype(int)
    return np.array([bin(int(mask)).count("1") for mask in masks])


def saturation_by_phase(rows: np.ndarray, phases: np.ndarray) -> dict:
    """Plant 1 ms record: time with any leg / >= 3 legs limited per phase and in all."""
    from harness_flow import COLUMN

    if len(rows) == 0:
        return {"all": {"any_s": 0.0, "ge3_s": 0.0}}
    t = rows[:, COLUMN["t"]]
    dt = np.diff(t, prepend=t[0])
    counts = _limited_counts(rows)
    out = {}
    for phase in sorted({str(p) for p in phases}):
        selected = phases == phase
        out[phase] = {"any_s": float(dt[selected & (counts > 0)].sum()),
                      "ge3_s": float(dt[selected & (counts >= 3)].sum())}
    out["all"] = {"any_s": float(dt[counts > 0].sum()), "ge3_s": float(dt[counts >= 3].sum())}
    return out


def open_loop_window(rows: np.ndarray, t0_s: float, t1_s: float) -> dict:
    """F-5 window values (design 3.1): stroke increments from the delivered speeds, true
    attitude change, smallest true cylinder force, crawler lift-off time."""
    from harness_flow import COLUMN, TRUE_FORCE, V

    t = rows[:, COLUMN["t"]]
    dt = np.diff(t, prepend=t[0])
    selected = (t >= t0_s) & (t <= t1_s)
    increments_m = (rows[selected][:, V] * dt[selected][:, None]).sum(axis=0)
    true_force = rows[selected][:, TRUE_FORCE]
    roll = rows[selected][:, COLUMN["roll"]]
    pitch = rows[selected][:, COLUMN["pitch"]]
    off = np.flatnonzero(rows[selected][:, COLUMN["crawler"]] <= 1.0)
    counts = _limited_counts(rows[selected])
    roll_change = float(np.degrees(roll[-1] - roll[0]))
    pitch_change = float(np.degrees(pitch[-1] - pitch[0]))
    return {"t0_s": t0_s, "t1_s": t1_s,
            "stroke_inc_mm": (increments_m * 1e3).tolist(),
            "stroke_spread_mm": float((increments_m.max() - increments_m.min()) * 1e3),
            "roll_change_deg": roll_change, "pitch_change_deg": pitch_change,
            "attitude_change_deg": math.hypot(roll_change, pitch_change),
            "min_true_force_kN": float(np.nanmin(true_force) / 1e3),
            "min_true_force_leg": int(np.nanargmin(np.nanmin(true_force, axis=0))),
            "t_crawler_off_s": None if off.size == 0 else float(t[selected][off[0]]),
            "any_limited_s": float(dt[selected][counts > 0].sum()),
            "ge3_limited_s": float(dt[selected][counts >= 3].sum())}


def run_metrics(plant, controller, state: FbState | None, params: FbParams) -> dict:
    """Rules 3.1 per-line values from the plant record and the controller log."""
    import verdict_runs
    from verdict_metrics import chunk_phases, u9_values

    limiter = plant.flow_limiter
    rows = limiter.rows()
    period = verdict_runs.period_arrays(controller)
    phases = chunk_phases(rows, period["t"], period["phase"])
    out = {"saturation_s": saturation_by_phase(rows, phases),
           "u9_values": u9_values(rows, phases, period,
                                  is_flow_on=limiter.setting.is_enabled)}
    if params.open_loop_s is not None and state is not None and state.level_t0_s is not None:
        out["open_loop"] = open_loop_window(rows, state.level_t0_s,
                                            state.level_t0_s + params.open_loop_s)
    return out


def _install_candidate(params: FbParams) -> None:
    """The preset's own LAS-b (checked on, never the ``las_targeted`` wrapper), then FB."""
    problems = thread_problems(thread_values())
    if problems:
        raise RuntimeError(f"thread variables not 1: {problems}")
    check_preset_las()
    if params.has_wrapper:
        install(params)
    _capture_runs()


def _fb_block(entry: dict, job: dict, params: FbParams, controller, plant,
              identity: dict) -> dict:
    """The ``fb`` block; the plant and the controller of the run must have been captured.

    Raises:
        RuntimeError: No plant or no controller (a run without metrics is an error line).
    """
    if plant is None or controller is None:
        raise RuntimeError(f"run objects not captured (plant {plant is not None}, "
                           f"controller {controller is not None})")
    state = controller.__dict__.get("_fb_run")
    block = {"candidate": entry["name"], "bundle": entry["bundle"], "key": fb_key(job),
             "params": params.to_dict(), "wrapper_installed": params.has_wrapper,
             "las_source": LAS_SOURCE, "identity": identity,
             "budget": budget_meta(state, params), **event_count_record(controller)}
    block.update(run_metrics(plant, controller, state, params))
    return block


def run_fb_job(job: dict) -> dict:
    """Worker: check the preset LAS-b, install the candidate, run the job, add ``fb`` and
    ``las``."""
    t_start = time.perf_counter()
    entry = job.pop("fb")
    params = FbParams.from_dict(entry["params"])
    error_head = {"job": job, "fb": {"candidate": entry["name"], "bundle": entry["bundle"],
                                     "key": fb_key(job)}}
    try:
        import run_v5  # sys.path and thread variables first

        identity = run_identity()
        _install_candidate(params)
    except Exception as exc:  # recorded as an error line, the batch decides (H-3)
        return {**error_head, "error": f"install: {exc!r}",
                "wall_s": round(time.perf_counter() - t_start, 1)}
    line = run_v5.run_one(job)
    if "error" in line:
        return {**line, "fb": error_head["fb"]}
    try:
        plant, controller = _run_objects(job)
        line["fb"] = _fb_block(entry, job, params, controller, plant, identity)
        line["las"] = las_block_of(controller, _CAPTURE.get("harness"))
    except Exception as exc:
        return {**error_head, "error": f"metrics: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    return line


# ------------------------------------------------------------------------------- batch
def done_labels(path: Path) -> set[tuple[str, str]]:
    """(key, candidate) of the finished (error-free) lines of ``path``."""
    if not path.exists():
        return set()
    done = set()
    for text in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(text)
        if "error" in record or "fb" not in record:
            continue
        done.add((record["fb"]["key"], record["fb"]["candidate"]))
    return done


def default_out(bundle: str) -> Path:
    return OUT_DIR / f"fb_{bundle.replace('-', '')}.jsonl"


def _json_default(value):
    return value.item() if hasattr(value, "item") else str(value)


@dataclass
class BatchWatch:
    """H-3 retries and the H-4 count of one bundle (the file's earlier lines included), and
    the run identity of the arriving lines."""

    bundle: str
    stored_reference: dict
    current_identity: dict | None = None
    """None = no identity check (the earlier lines of the file were checked by ``main``)."""
    lines: dict = field(default_factory=dict)
    c2_violations: list = field(default_factory=list)
    retried: set = field(default_factory=set)
    identity_problems: list = field(default_factory=list)

    def note(self, record: dict) -> None:
        """Add a finished line; count the C-2 violations of a completed pair."""
        import fb_judge

        key, name = record["fb"]["key"], record["fb"]["candidate"]
        if self.current_identity is not None:
            for problem in identity_mismatch(record["fb"].get("identity"),
                                             self.current_identity):
                self.identity_problems.append(f"{name} {key}: {problem}")
        self.lines.setdefault(key, {})[name] = record
        pair = fb_judge.reference_and_candidate(self.bundle, key, self.lines[key],
                                                self.stored_reference)
        if pair is None:
            return
        reference, candidate = pair
        for violation in fb_judge.c2_violations(reference, candidate):
            self.c2_violations.append(f"{key}: {violation}")


def _print_line(count: int, total: int, record: dict) -> None:
    fb = record.get("fb") or {}
    if "error" in record:
        state = f"ERROR {record['error'][:200]}"
    else:
        budget = fb.get("budget") or {}
        d1 = record.get("d1") or {}
        sat = (fb.get("saturation_s") or {}).get("all", {})
        state = (f"{d1.get('verdict', record['final_phase'])} {record['commands_sha256'][:12]} "
                 f"sat {sat.get('any_s')} cuts {len(budget.get('cuts') or [])} "
                 f"{record['wall_s']}s")
    print(f"{count}/{total} {fb.get('candidate')} {fb.get('key')}: {state}", flush=True)


def preloaded_watch(bundle: str, stored_reference: dict | None, existing_lines: list[dict],
                    current_identity: dict | None) -> BatchWatch:
    """A watch that already holds the file's finished lines, so H-4 counts across resumes."""
    watch = BatchWatch(bundle, stored_reference or {})
    for record in existing_lines:
        watch.note(record)
    watch.current_identity = current_identity
    return watch


def run_batch(jobs: list[dict], path: Path, workers: int, bundle: str,
              stored_reference: dict | None = None, existing_lines: list[dict] | None = None,
              current_identity: dict | None = None) -> dict:
    """Run the jobs in spawned workers (one run each), append the lines (H-3, H-4).

    Args:
        existing_lines: The error-free lines already in ``path`` (their C-2 violations count
            for H-4).
        current_identity: The run identity every new line must carry (None = not checked).

    Returns:
        ``runs``, ``errors`` (lines with an error after the retry), ``stop`` (None or the
        reason) and ``c2_violations``.
    """
    watch = preloaded_watch(bundle, stored_reference, existing_lines or [], current_identity)
    if len(watch.c2_violations) >= C2_STOP_COUNT:
        return {"runs": 0, "errors": 0, "c2_violations": watch.c2_violations,
                "stop": f"H-4: {len(watch.c2_violations)} C-2 violations in the file already"}
    import verdict_runs

    verdict_runs.warm_numba_cache()
    path.parent.mkdir(parents=True, exist_ok=True)
    error_path = path.with_name(path.stem + "_errors.jsonl")
    results: queue.Queue = queue.Queue()
    by_label = {(fb_key(job), job["fb"]["name"]): job for job in jobs}
    stop = None
    errors = 0
    written = 0
    with get_context("spawn").Pool(workers, maxtasksperchild=1) as pool, \
            path.open("a", encoding="utf-8") as handle:

        def submit(job: dict) -> None:
            pool.apply_async(run_fb_job, (json.loads(json.dumps(job)),), callback=results.put,
                             error_callback=lambda exc: results.put({"pool_error": repr(exc)}))

        for job in jobs:
            submit(job)
        pending = len(jobs)
        while pending and stop is None:
            record = results.get()
            pending -= 1
            if "pool_error" in record:
                stop, errors = f"pool error {record['pool_error']}", errors + 1
                break
            record["job"].pop("mask", None)
            label = (record["fb"]["key"], record["fb"]["candidate"])
            if "error" in record:
                with error_path.open("a", encoding="utf-8") as error_handle:
                    error_handle.write(json.dumps(record, default=_json_default) + "\n")
                _print_line(written, len(jobs), record)
                if label in watch.retried:
                    errors += 1
                    stop = f"H-3: {label} failed twice"
                    break
                watch.retried.add(label)
                submit(by_label[label])
                pending += 1
                continue
            handle.write(json.dumps(record, default=_json_default) + "\n")
            handle.flush()
            written += 1
            _print_line(written, len(jobs), record)
            watch.note(record)
            if watch.identity_problems:
                stop = f"run identity changed during the batch: {watch.identity_problems[:3]}"
            elif len(watch.c2_violations) >= C2_STOP_COUNT:
                stop = f"H-4: {len(watch.c2_violations)} C-2 violations"
        if stop is not None:
            pool.terminate()
    return {"runs": written, "errors": errors, "stop": stop,
            "c2_violations": watch.c2_violations}


# ------------------------------------------------------------------------------- list / CLI
def list_bundle(bundle: str) -> tuple[list[str], list[str]]:
    """(report lines, problems) of ``list``: count against rules 3.2, unique keys."""
    jobs = bundle_jobs(bundle)
    labels = [(fb_key(job), job["fb"]["name"]) for job in jobs]
    keys = sorted({key for key, _ in labels})
    lines = [f"{bundle}: {len(jobs)} runs = {len(keys)} keys x "
             f"{', '.join(BUNDLE_CANDIDATES[bundle])} (expected {BUNDLE_COUNTS[bundle]})"]
    problems = []
    if len(jobs) != BUNDLE_COUNTS[bundle] or len(set(labels)) != len(labels):
        problems.append(f"{bundle}: {len(jobs)} runs (unique {len(set(labels))}) != "
                        f"{BUNDLE_COUNTS[bundle]}")
    if bundle == "F-2":
        import fb_judge

        stored = fb_judge.load_stored_reference(LAS_STORED_PATHS)
        missing = [key for key in keys if key not in stored]
        lines.append(f"  stored L (b0 act) lines: {len(keys) - len(missing)}/{len(keys)}")
        if missing:
            problems.append(f"F-2: {len(missing)} keys without a stored L line: {missing[:3]}")
    lines += [f"  {key}" for key in keys]
    return lines, problems


def _check_f0_gate(out_dir: Path, current_identity: dict) -> str | None:
    """H-2: the reason F-1 .. F-5 may not run (None = F-0 passed C-7 with this identity)."""
    import fb_judge

    f0_path = out_dir / "fb_F0.jsonl"
    if not f0_path.exists():
        return f"no {f0_path.name}: run F-0 first (H-2)"
    f0_lines = fb_judge.read_lines(f0_path)
    stale = stale_lines(f0_lines, current_identity)
    if stale:
        return f"F-0 lines of another run identity (H-2): {stale[:3]}"
    result = fb_judge.check_c7(f0_lines, fb_judge.load_stored_reference(LAS_STORED_PATHS[:1]))
    return None if result["pass"] else f"F-0 C-7 not passed (H-2): {result['problems']}"


def _existing_lines(path: Path) -> list[dict]:
    """The error-free ``fb`` lines of ``path`` (``[]`` without the file)."""
    import fb_judge

    return [record for record in fb_judge.read_lines(path) if "fb" in record]


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="runs of the bundles against rules 3.2")
    listing.add_argument("--bundle", nargs="+", choices=BUNDLES, default=list(BUNDLES))
    run = sub.add_parser("run", help="run a bundle")
    run.add_argument("--bundle", required=True, choices=BUNDLES)
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--affinity", default=None, help="hex mask, set in every worker")
    run.add_argument("--out", type=Path, default=None)
    run.add_argument("--keys", default=None, help="comma-separated keys (subset, checks)")
    run.add_argument("--limit", type=int, default=None, help="first N runs only (checks)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    problems = sealed_check()
    if problems:
        print("\n".join(f"H-1 {problem}" for problem in problems))
        print(json.dumps({"stop": "H-1", "problems": problems}))
        return 2
    if args.command == "list":
        all_problems = []
        for bundle in args.bundle:
            lines, bundle_problems = list_bundle(bundle)
            print("\n".join(lines))
            all_problems += bundle_problems
        for problem in all_problems:
            print(f"MISMATCH {problem}")
        print(json.dumps({"bundles": args.bundle, "counts_equal": not all_problems,
                          "problems": len(all_problems)}))
        return 1 if all_problems else 0
    path = args.out or default_out(args.bundle)
    try:
        identity = run_identity()
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"input error: run identity: {exc!r}")
        return 2
    print(f"run identity: {identity['git_head']} dirty {identity['git_dirty']} "
          f"threads {identity['threads']}", flush=True)
    if args.bundle != "F-0":
        reason = _check_f0_gate(path.parent, identity)
        if reason is not None:
            print(reason)
            print(json.dumps({"bundle": args.bundle, "stop": "H-2", "reason": reason}))
            return 1
    existing = _existing_lines(path)
    stale = stale_lines(existing, identity)
    if stale:
        reason = f"{path.name} has lines of another run identity: {stale[:3]}"
        print(reason)
        print(json.dumps({"bundle": args.bundle, "stop": "identity", "reason": reason,
                          "stale_lines": len(stale)}))
        return 1
    try:
        mask = None if args.affinity is None else int(args.affinity, 16)
        keys = args.keys.split(",") if args.keys else None
        jobs = bundle_jobs(args.bundle, mask, keys)
    except (KeyError, OSError, ValueError) as exc:
        print(f"input error: {exc}")
        return 2
    done = done_labels(path)
    todo = [job for job in jobs if (fb_key(job), job["fb"]["name"]) not in done]
    if args.limit is not None:
        todo = todo[: args.limit]
    print(f"{args.bundle}: {len(jobs)} runs, {len(todo)} to do -> {path}", flush=True)
    stored = None
    if args.bundle == "F-2":
        import fb_judge

        stored = fb_judge.load_stored_reference(LAS_STORED_PATHS)
    summary = (run_batch(todo, path, args.workers, args.bundle, stored, existing, identity)
               if todo else {"runs": 0, "errors": 0, "stop": None, "c2_violations": []})
    print(json.dumps({"bundle": args.bundle, "out": str(path), **summary}))
    return 1 if summary["errors"] or summary["stop"] else 0


if __name__ == "__main__":
    sys.exit(main())
