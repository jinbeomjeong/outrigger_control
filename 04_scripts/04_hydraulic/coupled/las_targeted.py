"""LAS-b targeted runs on the reduced harness (sealed ``las_targeted_rules.md`` 1 .. 2).

The candidates wrap ``C2Controller._apply_pre_loc_lift_pause`` in the worker process only
(spawned, ``maxtasksperchild=1``); no project file changes. One run is ``run_v5.run_one`` of a
``d1_rows`` job, its line gets an ``las`` block.

Candidates (rules 1.3):
  current   the wrapper is installed and returns the command unchanged (T-0 reproduction)
  b0 .. b-T20  LAS-b (rules 1.2): one start per run when S1 .. S8 hold, then the command is
            scaled to the mean ``gamma v_max`` until an end reason (loc, phase, soil, reapproach,
            sum, time). Events ``INFO_LIFTOFF_SLOW:<leg>`` / ``INFO_LIFTOFF_SLOW_END:<reason>``.
  LASa      comparison only (rules 1.3): control-expert ``probe.py`` intervention ``approach``,
            i.e. ``_approach`` (every pre-LOC crawler-zone period with sum L >= alpha W_ref, mean
            scaled to gamma v_max) plus ``_slow_lift_scaled`` (P30fz completed by a scale).
            As the probe it tests the *current* LOC (``_is_in_pre_loc_window``); the rules' S3
            ("no LOC in this run") differs after a LOC revocation: the ``las`` block counts the
            periods it acted on after one (``acted_after_revoke_periods``).
  custom    LAS-b with ``--alpha --beta --gamma --alpha-end --n-end --t-max``.
``--gate-only`` (V-1 of rules 4): the start gates of the candidate are evaluated in every LEVEL
step and recorded, the command is never changed; ``--gate-npz-dir`` writes a T4h-like record
(``t_s``, ``phase``, ``lower_estimate_N``, ``command_m_s``, ``meta_json``) per run for
``las_shadow.py v1``.

Where the gates read the controller (rules 1.1 / 1.2): the wrapper runs right after
``_apply_pre_loc_lift_pause`` in ``_level_step`` (before the DSb75 addition). S6 is the
``reapproaching`` vector of this ``_level_step`` (captured from ``_apply_reapproach_speeds``,
which receives it); S3 latches every LOC seen by a LEVEL step (a LOC is confirmed only in
``_update_liftoff_window`` at the start of ``_level_step``, a revocation acts after the
command, so the latch sees every LOC). A period without a LEVEL step (``_phase_command`` did not
reach the wrapper) ends an active slowdown with reason ``phase`` (S2 false in that period).

Usage (dynamics-dev python, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/las_targeted.py list --stage T-0|T-1|T-2|V-1
      [--rules <md>] [--baseline <d1.jsonl>]
  python -I -B 04_scripts/04_hydraulic/coupled/las_targeted.py run --stage T-1
      --candidate b0 b-a5 ... [--workers 4] [--affinity HEX] [--out <jsonl>]
      [--gate-only] [--gate-npz-dir DIR] [--keys K1,K2] [--limit N]
Exit codes: 0 done / keys equal, 1 mismatch or a run error, 2 input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from multiprocessing import get_context
from pathlib import Path

# As run_v5: one BLAS / OpenMP thread, set before numpy loads (here and in every spawned
# worker, which inherits them). Multi-threaded reductions change the command hash.
for _name in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_name, "1")
os.environ.setdefault("MKL_THREADING_LAYER", "TBB")

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

OUT_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "las"
BASELINE_PATH = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "d1.jsonl"
RULES_PATH = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "las_targeted_rules.md"
RULES_SHA256 = "00b48fd834d81b9d499015f2d44380623e9fbcb2f1515913a8fd0589503eaf40"
"""``las_targeted_rules.sha256`` (sealed 2026-11-08)."""

KIND_OFF = "off"
KIND_LASB = "lasb"
KIND_LASA = "lasa"
MODE_ACT = "act"
MODE_GATE = "gate"
START_EVENT = "INFO_LIFTOFF_SLOW"
END_EVENT = "INFO_LIFTOFF_SLOW_END"
END_REASONS = ("loc", "phase", "soil", "reapproach", "sum", "time")
"""Rules 1.2 end table, in the order they are tested."""
TIME_TOLERANCE_S = 1e-9
GATE_NAMES = ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8")

FAMILY_ROW_KEYS = ("D1|H-R-A|rigid+J1@FR|T|diag-op|K1", "D1|H-R-A|rigid+J1@FR|T|diag-op|K3")
"""Rules appendix A: the G-3 family rows (x V0 / VB x eps 0 / 2e-3 = 8 keys)."""
T0_KEYS = ("D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0", "D1|H-R-A|rigid+J1@FR|T|diag-op|K1|VB|e0")
T2_RIGID_LEVEL = "top"
T2_RIGID_SLOPES = ("roll+op", "roll+val", "roll-op", "roll-val", "diag-op", "diag-val")
"""Rules 2: H-R-0 top roll / diagonal slopes x K1 / K3 (12 rows x 4 = 48 keys)."""
V1_KEYS = (
    "D1|H-R-A|rigid+J1@FR|T|diag-op|K1|V0|e0", "D1|H-R-A|rigid+J1@FR|T|diag-op|K1|VB|e0",
    "D1|H-R-A|rigid+J1@FR|T|diag-op|K3|V0|e0", "D1|H-R-A|rigid+J1@FR|T|diag-op|K3|VB|e0",
    "D1|H-R-0|rigid|T|roll+op|K1|V0|e0", "D1|H-R-0|rigid|T|roll+op|K1|VB|e0",
    "D1|H-R-0|rigid|T|diag-op|K3|V0|e0", "D1|H-R-0|rigid|T|diag-op|K3|VB|e0",
    "D1|H-R-A|rigid+J1@FL|T|flat|K1|V0|e0", "D1|H-R-A|rigid+J1@FL|T|flat|K1|VB|e0",
    "D1|H-R-0|rigid|T|flat|K1|V0|e0", "D1|H-R-0|rigid|M|flat|K1|V0|e0",
    "D1|H-R-0|rigid|B|flat|K1|V0|e0", "D1|H-R-0|rigid|T|fdown-op|K1|V0|e0",
    "D1|H-R-0|rigid|T|flat|K1|VB|e0", "D1|H-R-A|rigid+J1@RL|T|flat|K1|V0|e0",
    "D1|H-R-A|rigid+J1@RL|T|fup-psa|K1|V0|e0", "D1|H-R-A|rigid+J1@RL|T|flat|K1|VB|e0",
)
"""V-1 instrumented runs (rules 4: >= 10, >= 3 firing and >= 3 silent, VB and V0). With b0
(gate-only, 2026-11-08) the first 10 gave 9 firing (the rigid roll / diagonal rows fire too)
and 1 silent; the last 8 (flat, nose-down and rear-patch rows) were all silent."""
STAGES = ("T-0", "T-1", "T-2", "V-1")
STAGE_COUNTS = {"T-0": 2, "T-1": 8, "T-2": 184, "V-1": 18}


# ------------------------------------------------------------------------------- candidates
@dataclass(frozen=True)
class LasParams:
    """One candidate (rules 1.3). ``None`` = the condition does not exist (LAS-a)."""

    kind: str
    alpha: float | None = None
    beta: float | None = None
    gamma: float | None = None
    alpha_end: float | None = None
    n_end: int | None = None
    t_max_s: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict) -> LasParams:
        return cls(**values)


def _lasb(alpha: float = 0.6, t_max_s: float = 1.5) -> LasParams:
    return LasParams(KIND_LASB, alpha=alpha, beta=3.5, gamma=0.16, alpha_end=0.85, n_end=5,
                     t_max_s=t_max_s)


CANDIDATES: dict[str, LasParams] = {
    "current": LasParams(KIND_OFF),
    "b0": _lasb(),
    "b-a5": _lasb(alpha=0.5),
    "b-a7": _lasb(alpha=0.7),
    "b-T10": _lasb(t_max_s=1.0),
    "b-T20": _lasb(t_max_s=2.0),
    "LASa": LasParams(KIND_LASA, alpha=0.6, gamma=0.16),
}
LASB_VARIANTS = ("b0", "b-a5", "b-a7", "b-T10", "b-T20")
CLOSENESS_TO_B0 = ("b0", "b-T20", "b-T10", "b-a7", "b-a5")
"""Rules 3.2 step 3.3: tie order, closest to b0 first."""
T1_CANDIDATES = (*LASB_VARIANTS, "LASa")


def candidate_label(name: str, params: LasParams) -> str:
    """The name; ``custom`` carries its parameters (one label per parameter set)."""
    if name != "custom":
        return name
    return (f"custom(a={params.alpha:g},b={params.beta:g},g={params.gamma:g},"
            f"ae={params.alpha_end:g},n={params.n_end},T={params.t_max_s:g})")


# ------------------------------------------------------------------------------- the rule
@dataclass(frozen=True)
class GateInputs:
    """What the LAS-b gates read in one LEVEL step (rules 1.1, 1.2)."""

    t_s: float
    soil_enable: bool
    is_level: bool
    has_loc_been_seen: bool
    has_soil_mode_started: bool
    in_crawler_zone: bool
    is_reapproaching: bool
    loads_N: tuple[float, float, float, float]
    weight_ref_N: float
    F_min_N: float
    mean_speed_m_s: float
    v_max_m_s: float

    @property
    def load_sum_N(self) -> float:
        return float(np.sum(self.loads_N))


def sum_gate(inputs: GateInputs, params: LasParams) -> bool:
    """S7 first part: sum L >= alpha W_ref."""
    return inputs.load_sum_N >= params.alpha * inputs.weight_ref_N


def min_gate(inputs: GateInputs, params: LasParams) -> bool:
    """S7 second part: min L < beta F_min (always true without beta, LAS-a)."""
    if params.beta is None:
        return True
    return float(np.min(inputs.loads_N)) < params.beta * inputs.F_min_N


def start_gates(inputs: GateInputs, params: LasParams) -> dict[str, bool]:
    """S1 .. S8 of rules 1.2 for one LEVEL step."""
    return {
        "S1": bool(inputs.soil_enable),
        "S2": bool(inputs.is_level),
        "S3": not inputs.has_loc_been_seen,
        "S4": not inputs.has_soil_mode_started,
        "S5": bool(inputs.in_crawler_zone),
        "S6": not inputs.is_reapproaching,
        "S7": sum_gate(inputs, params) and min_gate(inputs, params),
        "S8": inputs.mean_speed_m_s > params.gamma * inputs.v_max_m_s,
    }


def scale_to_mean(speeds: np.ndarray, cap_m_s: float) -> np.ndarray:
    """``u cap / mean(u)`` when the mean exceeds ``cap_m_s``; else ``u`` itself (same object)."""
    mean_m_s = float(np.mean(speeds))
    if mean_m_s <= cap_m_s:
        return speeds
    return speeds * (cap_m_s / mean_m_s)


@dataclass
class LasbState:
    """Rules 1.2 state of one run plus what the ``las`` block reports."""

    is_armed: bool = True
    is_active: bool = False
    t_start_s: float | None = None
    sum_count: int = 0
    start_leg: int | None = None
    end_t_s: float | None = None
    end_reason: str | None = None
    active_periods: int = 0
    scaled_periods: int = 0


def end_reason(inputs: GateInputs, state: LasbState, params: LasParams) -> str | None:
    """The end reason of an active period (rules 1.2 end table), ``None`` to go on.

    The ``sum`` counter is updated here (it counts only while active and returns to 0 on a
    period below ``alpha_end W_ref``).
    """
    if inputs.has_loc_been_seen:
        return "loc"
    if not inputs.is_level:
        return "phase"
    if inputs.has_soil_mode_started:
        return "soil"
    if inputs.is_reapproaching:
        return "reapproach"
    if inputs.load_sum_N >= params.alpha_end * inputs.weight_ref_N:
        state.sum_count += 1
    else:
        state.sum_count = 0
    if state.sum_count >= params.n_end:
        return "sum"
    if inputs.t_s - state.t_start_s >= params.t_max_s - TIME_TOLERANCE_S:
        return "time"
    return None


def lasb_step(state: LasbState, inputs: GateInputs, params: LasParams,
              speeds: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """One LEVEL step of LAS-b: start, end check, action. Returns the speeds (the input object
    when nothing acts) and the event names to add."""
    events: list[str] = []
    if state.is_armed and all(start_gates(inputs, params).values()):
        state.is_armed = False
        state.is_active = True
        state.t_start_s = inputs.t_s
        state.start_leg = int(np.argmin(inputs.loads_N))
        events.append(f"{START_EVENT}:{state.start_leg}")
    if not state.is_active:
        return speeds, events
    reason = end_reason(inputs, state, params)
    if reason is not None:
        end_slowdown(state, inputs.t_s, reason)
        events.append(f"{END_EVENT}:{reason}")
        return speeds, events
    state.active_periods += 1
    scaled = scale_to_mean(speeds, params.gamma * inputs.v_max_m_s)
    if scaled is not speeds:
        state.scaled_periods += 1
    return scaled, events


def end_slowdown(state: LasbState, t_s: float, reason: str) -> None:
    state.is_active = False
    state.end_t_s = float(t_s)
    state.end_reason = reason


# ------------------------------------------------------------------------------- run state
@dataclass
class GateRecord:
    """Gate-only bookkeeping (V-1): first LEVEL step with S1 .. S7 (S8 left out, as the
    shadow judge) and with S1 .. S8; S5 false while S1, S2 and S3 hold (rules 4 premise)."""

    first_s1_s7_t_s: float | None = None
    first_s1_s8_t_s: float | None = None
    level_steps: int = 0
    zone_false_with_s1_s3: int = 0


@dataclass
class LasRun:
    """Per-controller state of the wrapper (instance attribute ``_las_run``)."""

    params: LasParams
    mode: str
    lasb: LasbState = field(default_factory=LasbState)
    gates: GateRecord = field(default_factory=GateRecord)
    has_loc_been_seen: bool = False
    is_reapproaching: bool = False
    has_level_step_run: bool = False
    weight_ref_N: float | None = None
    soil_enable: bool | None = None
    lasa_acted_periods: int = 0
    lasa_first_t_s: float | None = None
    lasa_last_t_s: float | None = None
    lasa_acted_after_revoke: int = 0


def _run_of(controller, params: LasParams, mode: str) -> LasRun:
    run = controller.__dict__.get("_las_run")
    if run is None:
        run = LasRun(params, mode)
        controller.__dict__["_las_run"] = run
    return run


def _gate_inputs(controller, reading, speeds: np.ndarray, run: LasRun, c2) -> GateInputs:
    loads = np.asarray(controller._load_estimate_N(reading.cylinder_force_lower_N), float)
    geometry = controller.geometry
    return GateInputs(
        t_s=float(reading.t_s),
        soil_enable=bool(controller.config.soil.enable),
        is_level=controller._state.phase is c2.C2Phase.LEVEL,
        has_loc_been_seen=run.has_loc_been_seen,
        has_soil_mode_started=bool(controller._has_soil_mode_started()),
        in_crawler_zone=bool(controller._state.in_crawler_zone),
        is_reapproaching=run.is_reapproaching,
        loads_N=tuple(float(v) for v in loads),
        weight_ref_N=float(controller._reference_weight_N()),
        F_min_N=float(geometry.F_min_N),
        mean_speed_m_s=float(np.mean(speeds)),
        v_max_m_s=float(geometry.max_speed_m_s),
    )


def _note_gates(run: LasRun, inputs: GateInputs, gates: dict[str, bool]) -> None:
    record = run.gates
    record.level_steps += 1
    if gates["S1"] and gates["S2"] and gates["S3"] and not gates["S5"]:
        record.zone_false_with_s1_s3 += 1
    if record.first_s1_s7_t_s is None and all(gates[name] for name in GATE_NAMES[:7]):
        record.first_s1_s7_t_s = inputs.t_s
    if record.first_s1_s8_t_s is None and all(gates.values()):
        record.first_s1_s8_t_s = inputs.t_s


def _lasa_step(controller, reading, speeds: np.ndarray, run: LasRun) -> np.ndarray:
    """``probe.py`` ``_approach`` after the P30fz stage (the probe's own expressions)."""
    params = run.params
    loads = controller._load_estimate_N(reading.cylinder_force_lower_N)
    ratio = float(np.sum(loads)) / controller._reference_weight_N()
    cap_m_s = params.gamma * controller.geometry.max_speed_m_s
    if not (controller._is_in_pre_loc_window() and controller._state.in_crawler_zone
            and ratio >= params.alpha):
        return speeds
    mean_m_s = float(np.mean(speeds))
    if mean_m_s <= cap_m_s:
        return speeds
    t_s = float(reading.t_s)
    run.lasa_acted_periods += 1
    run.lasa_first_t_s = t_s if run.lasa_first_t_s is None else run.lasa_first_t_s
    run.lasa_last_t_s = t_s
    if run.has_loc_been_seen:
        run.lasa_acted_after_revoke += 1
    return speeds * (cap_m_s / mean_m_s)


def _slow_lift_scaled(original):
    """``probe.py`` ``_slow_lift_scaled``: P30fz, then a scale to the slow-lift mean."""

    def slow_lift(self, leg_speeds):
        settings = self.config.pre_loc_lift_pause
        slow_mean = settings.slow_lift_mean_fraction * self.geometry.max_speed_m_s
        out = original(self, leg_speeds)
        mean_m_s = float(np.mean(out))
        if mean_m_s > slow_mean:
            out = out * (slow_mean / mean_m_s)
        return out

    return slow_lift


_INSTALLED: dict = {}


def install(params: LasParams, mode: str = MODE_ACT) -> None:
    """Patch ``c2.C2Controller`` of this process (call once per worker, before the run).

    Raises:
        RuntimeError: Installed twice in one process.
        ValueError: ``--gate-only`` with a candidate that is not LAS-b (it would act).
    """
    if _INSTALLED:
        raise RuntimeError("las_targeted.install: already installed in this process")
    if mode == MODE_GATE and params.kind != KIND_LASB:
        raise ValueError(f"gate-only needs a LAS-b candidate, got kind {params.kind!r}")
    from outrigger_sim.control import c2

    cls = c2.C2Controller
    original_reapproach = cls._apply_reapproach_speeds
    original_pause = cls._apply_pre_loc_lift_pause
    original_phase_command = cls._phase_command

    def apply_reapproach_speeds(self, leg_speeds, reapproaching):
        run = _run_of(self, params, mode)
        run.is_reapproaching = bool(np.any(reapproaching))  # this _level_step's vector (S6)
        return original_reapproach(self, leg_speeds, reapproaching)

    def apply_pre_loc_lift_pause(self, reading, leg_speeds):
        speeds = original_pause(self, reading, leg_speeds)
        run = _run_of(self, params, mode)
        run.has_level_step_run = True
        run.has_loc_been_seen = run.has_loc_been_seen or self._is_liftoff_confirmed()
        run.weight_ref_N = float(self._reference_weight_N())
        run.soil_enable = bool(self.config.soil.enable)
        if params.kind == KIND_OFF:
            return speeds
        if params.kind == KIND_LASA:
            return _lasa_step(self, reading, speeds, run)
        inputs = _gate_inputs(self, reading, speeds, run, c2)
        if mode == MODE_GATE:
            _note_gates(run, inputs, start_gates(inputs, params))
            return speeds
        scaled, events = lasb_step(run.lasb, inputs, params, speeds)
        for name in events:
            self._add_event(reading.t_s, _named_event(name, c2.LEG_ORDER))
        return scaled

    def phase_command(self, reading):
        run = _run_of(self, params, mode)
        run.has_level_step_run = False
        speeds = original_phase_command(self, reading)
        if not run.has_level_step_run and run.lasb.is_active and mode == MODE_ACT:
            end_slowdown(run.lasb, float(reading.t_s), "phase")  # S2 false: no LEVEL step
            self._add_event(reading.t_s, f"{END_EVENT}:phase")
        return speeds

    cls._apply_reapproach_speeds = apply_reapproach_speeds
    cls._apply_pre_loc_lift_pause = apply_pre_loc_lift_pause
    cls._phase_command = phase_command
    if params.kind == KIND_LASA:
        cls._slow_lift = _slow_lift_scaled(cls._slow_lift)
    _INSTALLED.update(params=params, mode=mode)


def _named_event(name: str, leg_order) -> str:
    """``INFO_LIFTOFF_SLOW:<index>`` -> ``INFO_LIFTOFF_SLOW:<leg name>``."""
    head, _, tail = name.partition(":")
    if head == START_EVENT:
        return f"{START_EVENT}:{leg_order[int(tail)]}"
    return name


# ------------------------------------------------------------------------------- jobs
def composite_key(job: dict) -> str:
    """``<row key>|<setting>|e<eps>`` (``d1_runs.d1_record`` key) of a D-1 job; another
    ``run_v5`` job (``las_shadow.py v2`` reruns) is named by ``run_v5.job_key``."""
    if "d1" not in job:
        return json.dumps({k: v for k, v in sorted(job.items()) if k not in ("mask", "t4h_dir")})
    return f"{job['d1']['key']}|{job['setting']}|e{float(job['eps']):g}"


def _t2_rows(rows) -> list:
    family = set(FAMILY_ROW_KEYS)
    picked = [row for row in rows if row.group == "H-R-A" and row.key not in family]
    picked += [row for row in rows if row.group == "H-R-0" and row.level == T2_RIGID_LEVEL
               and row.slope_name in T2_RIGID_SLOPES]
    return picked


def stage_keys(stage: str) -> list[str]:
    """Composite keys of a stage (rules 2; ``V-1`` = :data:`V1_KEYS`).

    Raises:
        ValueError: Unknown stage.
    """
    import d1_rows

    if stage == "T-0":
        return list(T0_KEYS)
    if stage == "V-1":
        return list(V1_KEYS)
    rows = d1_rows.all_rows()
    if stage == "T-1":
        picked = [row for row in rows if row.key in FAMILY_ROW_KEYS]
    elif stage == "T-2":
        picked = _t2_rows(rows)
    else:
        raise ValueError(f"unknown stage {stage!r}")
    keys = {row.key for row in picked}
    return [composite_key(job) for job in d1_rows.jobs() if job["d1"]["key"] in keys]


def jobs_for_keys(keys: list[str]) -> list[dict]:
    """``d1_rows.jobs()`` entries of the composite keys, in key order.

    Raises:
        KeyError: A key that is not a D-1 job.
    """
    import d1_rows

    by_key = {composite_key(job): job for job in d1_rows.jobs()}
    missing = [key for key in keys if key not in by_key]
    if missing:
        raise KeyError(f"not D-1 jobs: {missing[:5]}")
    return [by_key[key] for key in keys]


# ------------------------------------------------------------------------------- list check
def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unescape(cell: str) -> str:
    return cell.strip().strip("`").replace("\\|", "|")


def sealed_appendix(path: Path) -> dict[str, list[dict]]:
    """Keys of the sealed text: ``T-0`` (rules 2 table), ``T-1`` (appendix A), ``T-2``
    (appendix B); appendix rows carry verdict, F_judged_min [kN] and the hash prefix."""
    text = path.read_text(encoding="utf-8")
    out: dict[str, list[dict]] = {"T-0": [], "T-1": [], "T-2": []}
    t0_line = next(line for line in text.splitlines() if line.startswith("| T-0"))
    out["T-0"] = [{"key": _unescape(key)} for key in re.findall(r"`(D1[^`]*)`", t0_line)]
    section = None
    for line in text.splitlines():
        if line.startswith("## 부록 A"):
            section = "T-1"
        elif line.startswith("## 부록 B"):
            section = "T-2"
        elif line.startswith("## "):
            section = None
        if section is None or not line.startswith("| `D1"):
            continue
        cells = re.split(r"(?<!\\)\|", line)[1:-1]
        key, verdict, f_kN, prefix = (cell.strip() for cell in cells)
        out[section].append({"key": _unescape(key), "verdict": verdict, "F_kN": float(f_kN),
                             "sha_prefix": prefix})
    return out


def load_baseline(path: Path) -> dict[str, dict]:
    """``d1.key`` -> stored line of ``v5/d1.jsonl``."""
    lines = {}
    for text in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(text)
        if "d1" in record:
            lines[record["d1"]["key"]] = record
    return lines


def list_check(stage: str, rules_path: Path, baseline_path: Path) -> tuple[list[str], list[str]]:
    """(report lines, problems) of ``list``: count, sealed keys, baseline columns."""
    keys = stage_keys(stage)
    lines = [f"{stage}: {len(keys)} keys (expected {STAGE_COUNTS[stage]})"]
    problems = []
    if len(keys) != STAGE_COUNTS[stage] or len(set(keys)) != len(keys):
        problems.append(f"count {len(keys)} (unique {len(set(keys))}) != {STAGE_COUNTS[stage]}")
    digest = file_sha256(rules_path)
    lines.append(f"rules {rules_path.name} sha256 {digest[:12]} "
                 f"({'sealed' if digest == RULES_SHA256 else 'NOT the sealed text'})")
    if digest != RULES_SHA256:
        problems.append(f"rules sha256 {digest} != sealed {RULES_SHA256}")
    baseline = load_baseline(baseline_path)
    missing = [key for key in keys if key not in baseline]
    if missing:
        problems.append(f"{len(missing)} keys without a baseline line: {missing[:3]}")
    if stage in ("T-0", "T-1", "T-2"):
        sealed = sealed_appendix(rules_path)[stage]
        sealed_keys = [entry["key"] for entry in sealed]
        if set(sealed_keys) != set(keys):
            problems.append(f"keys differ from the sealed text: only here "
                            f"{sorted(set(keys) - set(sealed_keys))[:3]}, only sealed "
                            f"{sorted(set(sealed_keys) - set(keys))[:3]}")
        problems += _appendix_column_problems(sealed, baseline)
    for key in keys:
        record = baseline.get(key)
        state = "-" if record is None else (
            f"{record['d1']['verdict']:<12} F {record['d1']['F_judged_min_N'] / 1e3:8.3f} kN  "
            f"{record['commands_sha256'][:12]}")
        lines.append(f"  {key:<52} {state}")
    return lines, problems


def _appendix_column_problems(sealed: list[dict], baseline: dict[str, dict]) -> list[str]:
    problems = []
    for entry in sealed:
        record = baseline.get(entry["key"])
        if record is None or "sha_prefix" not in entry:
            continue
        d1 = record["d1"]
        if not record["commands_sha256"].startswith(entry["sha_prefix"]):
            problems.append(f"{entry['key']}: hash {record['commands_sha256'][:12]} != "
                            f"sealed {entry['sha_prefix']}")
        if d1["verdict"] != entry["verdict"]:
            problems.append(f"{entry['key']}: verdict {d1['verdict']} != {entry['verdict']}")
        if round(d1["F_judged_min_N"] / 1e3, 3) != entry["F_kN"]:
            problems.append(f"{entry['key']}: F {d1['F_judged_min_N'] / 1e3:.3f} kN != "
                            f"{entry['F_kN']}")
    return problems


# ------------------------------------------------------------------------------- worker
_CAPTURE: dict = {}


def _capture_d1_record() -> None:
    import d1_runs

    original = d1_runs.d1_record

    def d1_record(row, setting_name, eps, result, plant, controller, harness):
        _CAPTURE.update(controller=controller, harness=harness)
        return original(row, setting_name, eps, result, plant, controller, harness)

    d1_runs.d1_record = d1_record


def loc_delay_record(harness: dict | None) -> dict:
    """The judge's LOC - t_off (r72 G6 record of a g6 row, P3-2 row of a steady row)."""
    if not harness:
        return {"loc_minus_t_off_s": None, "t_loc_s": None, "t_off_s": None}
    source = harness
    if "loc_delay_s" not in harness:
        source = ((harness.get("rows") or {}).get("P3-2")) or {}
    return {"loc_minus_t_off_s": source.get("loc_delay_s"), "t_loc_s": source.get("t_loc_s"),
            "t_off_s": source.get("t_off_s")}


def las_block(name: str, params: LasParams, mode: str, run: LasRun | None,
              harness: dict | None) -> dict:
    """The ``las`` block of a line."""
    block = {"candidate": name, "params": params.to_dict(), "mode": mode,
             **loc_delay_record(harness)}
    if run is None:
        return {**block, "wrapper_reached": False}
    state = run.lasb
    block.update(wrapper_reached=True, soil_enable=run.soil_enable, W_ref_N=run.weight_ref_N,
                 start_t_s=state.t_start_s, start_leg=state.start_leg, end_t_s=state.end_t_s,
                 end_reason=state.end_reason, active_periods=state.active_periods,
                 scaled_periods=state.scaled_periods)
    if params.kind == KIND_LASA:
        block.update(start_t_s=run.lasa_first_t_s, end_t_s=run.lasa_last_t_s,
                     active_periods=run.lasa_acted_periods,
                     scaled_periods=run.lasa_acted_periods,
                     acted_after_revoke_periods=run.lasa_acted_after_revoke)
    if mode == MODE_GATE:
        block["gates"] = asdict(run.gates)
    return block


def gate_file_name(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9.\-]+", "_", key) + ".npz"


def write_gate_record(directory: Path, key: str, controller, line: dict, run: LasRun) -> Path:
    """T4h-like record of an instrumented run (``las_shadow.py`` reads it as a T4h)."""
    import verdict_runs

    period = verdict_runs.period_arrays(controller)
    meta = {"job": line["job"], "commands_sha256": line.get("commands_sha256"),
            "F_min_N": float(controller.geometry.F_min_N), "W_ref_N": run.weight_ref_N,
            "v_max_m_s": float(controller.geometry.max_speed_m_s),
            "soil_enable": run.soil_enable, "period_s": controller.config.period_s,
            "events": [(float(event.t_s), event.name) for event in controller.events],
            "las_gates": asdict(run.gates), "las_params": run.params.to_dict(),
            "lower_estimate_rule": "verdict_runs LoggedController._logged_lower_estimate_N"}
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / gate_file_name(key)
    np.savez_compressed(path, t_s=period["t"], phase=period["phase"].astype(str),
                        lower_estimate_N=period["lower_estimate_N"],
                        command_m_s=period["command"], meta_json=np.array(json.dumps(meta)))
    return path


def run_las_job(job: dict) -> dict:
    """Worker: install the candidate, run the D-1 job with ``run_v5.run_one``, add ``las``."""
    t_start = time.perf_counter()
    las = job.pop("las")
    params = LasParams.from_dict(las["params"])
    try:
        import run_v5  # sys.path and thread variables first

        install(params, las["mode"])
        _capture_d1_record()
    except Exception as exc:  # recorded as an error line, the batch goes on
        return {"job": job, "error": f"install: {exc!r}", "las": {"candidate": las["name"]},
                "wall_s": round(time.perf_counter() - t_start, 1)}
    line = run_v5.run_one(job)
    controller = _CAPTURE.get("controller")
    run = None if controller is None else controller.__dict__.get("_las_run")
    line["las"] = las_block(las["name"], params, las["mode"], run, _CAPTURE.get("harness"))
    line["las"]["key"] = composite_key(job)
    if las.get("gate_npz_dir") and run is not None and "error" not in line:
        path = write_gate_record(Path(las["gate_npz_dir"]), composite_key(job), controller,
                                 line, run)
        line["las"]["gate_npz"] = path.name
    return line


# ------------------------------------------------------------------------------- batch
def done_labels(path: Path) -> set[tuple[str, str, str]]:
    """(key, candidate label, mode) of the finished (error-free) lines of ``path``."""
    if not path.exists():
        return set()
    done = set()
    for text in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(text)
        if "error" in record or "las" not in record:
            continue
        las = record["las"]
        done.add((las.get("key") or composite_key(record["job"]), las["candidate"], las["mode"]))
    return done


def build_jobs(keys: list[str], candidates: list[tuple[str, LasParams]], mode: str,
               mask: int | None, gate_npz_dir: str | None) -> list[dict]:
    """One job per (candidate, key); VB keys first (the longer runs start early)."""
    base = jobs_for_keys(keys)
    ordered = sorted(base, key=lambda job: job["setting"] != "VB")
    jobs = []
    for name, params in candidates:
        jobs += with_las(ordered, name, params, mode, mask, gate_npz_dir)
    return jobs


def with_las(base_jobs: list[dict], name: str, params: LasParams, mode: str,
             mask: int | None, gate_npz_dir: str | None = None) -> list[dict]:
    """``run_v5`` jobs with the ``las`` entry :func:`run_las_job` reads."""
    return [{**job, "mask": mask, "las": {"name": name, "params": params.to_dict(),
                                          "mode": mode, "gate_npz_dir": gate_npz_dir}}
            for job in base_jobs]


def _custom_params(args) -> LasParams:
    values = (args.alpha, args.beta, args.gamma, args.alpha_end, args.n_end, args.t_max)
    if any(value is None for value in values):
        raise ValueError("custom needs --alpha --beta --gamma --alpha-end --n-end --t-max")
    return LasParams(KIND_LASB, alpha=args.alpha, beta=args.beta, gamma=args.gamma,
                     alpha_end=args.alpha_end, n_end=int(args.n_end), t_max_s=args.t_max)


def resolve_candidates(names: list[str], args) -> list[tuple[str, LasParams]]:
    """(label, params) per requested name.

    Raises:
        ValueError: Unknown name or incomplete custom parameters.
    """
    out = []
    for name in names:
        if name == "custom":
            params = _custom_params(args)
        elif name in CANDIDATES:
            params = CANDIDATES[name]
        else:
            raise ValueError(f"unknown candidate {name!r} ({', '.join(CANDIDATES)}, custom)")
        out.append((candidate_label(name, params), params))
    return out


def default_out(stage: str) -> Path:
    return OUT_DIR / f"las_{stage.replace('-', '')}.jsonl"


def run_batch(jobs: list[dict], path: Path, workers: int) -> int:
    """Run the jobs in spawned workers (one run each), append the lines; the error count."""
    import verdict_runs

    verdict_runs.warm_numba_cache()
    path.parent.mkdir(parents=True, exist_ok=True)
    errors = 0
    with get_context("spawn").Pool(workers, maxtasksperchild=1) as pool, \
            path.open("a", encoding="utf-8") as handle:
        for count, record in enumerate(pool.imap_unordered(run_las_job, jobs), 1):
            record["job"].pop("mask", None)
            handle.write(json.dumps(record, default=lambda v: v.item() if hasattr(v, "item")
                                    else str(v)) + "\n")
            handle.flush()
            las = record.get("las") or {}
            if "error" in record:
                errors += 1
                state = record["error"][:200]
            else:
                d1 = record.get("d1") or {}
                state = (f"{d1.get('verdict', record['final_phase'])} "
                         f"F {d1.get('F_judged_min_N')} N {record['commands_sha256'][:12]} "
                         f"start {las.get('start_t_s')} end {las.get('end_reason')} "
                         f"{record['wall_s']}s")
            print(f"{count}/{len(jobs)} {las.get('candidate')} {las.get('key')}: {state}",
                  flush=True)
    return errors


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="keys of a stage against the sealed text")
    listing.add_argument("--stage", required=True, choices=STAGES)
    listing.add_argument("--rules", type=Path, default=RULES_PATH)
    listing.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    run = sub.add_parser("run", help="run a stage")
    run.add_argument("--stage", required=True, choices=STAGES)
    run.add_argument("--candidate", nargs="+", required=True)
    for name in ("--alpha", "--beta", "--gamma", "--alpha-end", "--t-max"):
        run.add_argument(name, type=float)
    run.add_argument("--n-end", type=int)
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--affinity", default=None, help="hex mask, set in every worker")
    run.add_argument("--out", type=Path, default=None)
    run.add_argument("--gate-only", action="store_true")
    run.add_argument("--gate-npz-dir", type=Path, default=None)
    run.add_argument("--keys", default=None, help="comma-separated composite keys (subset)")
    run.add_argument("--limit", type=int, default=None, help="first N jobs only (checks)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "list":
        try:
            lines, problems = list_check(args.stage, args.rules, args.baseline)
        except (OSError, KeyError, ValueError) as exc:
            print(f"input error: {exc!r}")
            return 2
        print("\n".join(lines))
        for problem in problems:
            print(f"MISMATCH {problem}")
        print(json.dumps({"stage": args.stage, "count": len(stage_keys(args.stage)),
                          "equal_to_sealed": not problems, "problems": len(problems)}))
        return 1 if problems else 0
    try:
        candidates = resolve_candidates(args.candidate, args)
        keys = args.keys.split(",") if args.keys else stage_keys(args.stage)
        mode = MODE_GATE if args.gate_only else MODE_ACT
        if mode == MODE_GATE and any(p.kind != KIND_LASB for _, p in candidates):
            raise ValueError("--gate-only takes LAS-b candidates only")
        mask = None if args.affinity is None else int(args.affinity, 16)
        gate_dir = None if args.gate_npz_dir is None else str(args.gate_npz_dir.resolve())
        jobs = build_jobs(keys, candidates, mode, mask, gate_dir)
    except (KeyError, ValueError) as exc:
        print(f"input error: {exc}")
        return 2
    path = args.out or default_out(args.stage)
    done = done_labels(path)
    todo = [job for job in jobs
            if (composite_key(job), job["las"]["name"], job["las"]["mode"]) not in done]
    if args.limit is not None:
        todo = todo[: args.limit]
    print(f"{args.stage}: {len(jobs)} runs, {len(todo)} to do -> {path}", flush=True)
    errors = run_batch(todo, path, args.workers) if todo else 0
    print(json.dumps({"stage": args.stage, "out": str(path), "runs": len(todo),
                      "errors": errors}))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
