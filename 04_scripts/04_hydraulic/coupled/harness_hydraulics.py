"""Adapter: the v5 plant options on the reduced harness (spec ``v5_hydraulic_impl_spec.md`` 2.0).

It holds no controller logic. :func:`make_hydraulics_plant_class` puts the options on the
flow-limited plant the way ``harness_flow`` does; ``verdict_runs.execute(..., hydraulics=...)``
installs it. Without options no line of this module runs and the commands stay bit for bit.

Inner step of an armed plant (spec 2.0, the numbers are the rows of its table):
  5   ``_rod_force``: law, then the M2 shift of ``sref``, then the kernel (law C, friction)

M2 (spec 2.3): the harness has no tracked rod pressure, so this class solves its first-order lag.
The start is ``p_r0 - G_r / A_ann`` at the release, the target comes from
``RodChamberLegParams.moving_target_rod_pressure_Pa`` (the law is not copied here) with the net oil
force. Revision 3: the lag is capped by the valve flow of the kernel speed
(``rod_release.flow_limited_rod_pressure``, the function L2b calls), ``C_r`` from ``kh``, ``kr``.
Revision 4 (``flow_limited_r4``, 2026-11-07): the base release decay ``Gr = r0 exp(-(t - t_rel) /
tau)`` of ``RodSidePlant`` already moves ``Gr / k_h``, so M2 reads ``p_hat = p + Delta w`` with
``Delta = Gr(t_rel) / A_ann`` (set at the release) and ``w = exp(-(t - t_rel) / tau)`` (the same
``tau``): ``Delta w`` equals ``Gr / A_ann`` of every moving step. Revision 5 (``flow_limited_r5``,
2026-11-07, plan B): a leg that locks after an extension gets the anchor
``p_r0 = max(min(p_tr, p_ext + max(p_tr - p*, 0)), p_floor)`` instead of ``p_ext`` (``p_tr``
the lag of the last moving step, ``p*`` the extension target of the lock step's net force); the lock step keeps
the moving ``Gr``, so the knee moves from the next step on (as on L2b). Retract locks keep
``p_ret``. All pressures are model values and ASSUMPTIONS.

436.9 plant options (``06_analysis/02_control/j_p3_cause/jp3_remedy_spec.md`` 3, all off by
default; off = none of their lines runs):
  P1 ``line_fill_gate``          ``CheckOpenGate`` in front of the flow limit: a locked leg keeps
                                 its lock (speed 0) until the check of its direction opened
  P2 ``lock_anchor_continuous``  every lock: ``p_r0 = max(p_lag, p_floor) + G_r,lock / A_ann``, so
                                 the locked truth starts at the lag; the knee counts from the truth
                                 (``_locked_knee_m``); the r5 extension anchor is off
  P3 ``rod_flow_cap_all``        M2 law ``flow_limited_r6`` (flow cap on all four branches)
  P4 ``rod_reading_truth``       the controller's rod reading is the M2 truth
                                 (:func:`with_plant_truth_pressures`, event path ``r64``)
Records of a run with any 436.9 option or ③ revision 5: the per-read J-P3 trace in
``extend_bound_check`` (revision 5 keys) and the per-lock ``lock_log``. With
:func:`enable_p1_read_record` (D0 split runner only) a P1 plant also logs its line state at each
controller read (:class:`P1ReadLog`, T4h arrays ``p1_*``); off, no line of it runs.

Pressures gauge [Pa], speeds m/s, extension positive.
"""
from __future__ import annotations

import dataclasses
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SOURCE_DIR = Path(__file__).resolve().parents[3] / "03_src"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))
_COUPLED_DIR = Path(__file__).resolve().parent
if str(_COUPLED_DIR) not in sys.path:  # j_p3_inputs (a sibling) for the B2 evidence keys
    sys.path.append(str(_COUPLED_DIR))

from j_p3_inputs import ROD_READING_EVIDENCE_KEYS  # noqa: E402

from outrigger_sim.control.extend_start_bound import (  # noqa: E402
    ExtendBoundCheck,
    TensionTruthCounter,
    extend_bound_states,
    plant_leg_states,
)
from outrigger_sim.hydraulics.check_open_delay import (  # noqa: E402
    CheckDelayCircuit,
    CheckDelayInputs,
    CheckOpenDelay,
    CheckOpenGate,
    CheckOpenGateP1Patch,
)
from outrigger_sim.hydraulics.rod_chamber import (  # noqa: E402
    RodChamberLegParams,
    RodChamberMode,
)
from outrigger_sim.hydraulics.rod_release import (  # noqa: E402
    ReleaseStart,
    RodPressureFlowLaw,
    RodPressureFlowLawR6,
    RodReleaseShift,
    release_weight,
)
from outrigger_sim.hydraulics.v5_options import (  # noqa: E402
    LOCK_SPEED_EPS_M_S,
    HydraulicOptions,
    apply_controller_options,
    check_lock_start_b_config,
    check_lock_window_meta,
    check_probe_d6_config,
    validate,
)
from outrigger_sim.sensors.rod_side import LegMode, RodSideParams, RodSideSynth  # noqa: E402

LEG_COUNT = 4
UNUSED_OUTER_STIFFNESS_N_M = math.inf
"""``moving_target_rod_pressure_Pa`` does not read the outer stiffness; soil rows change it."""
STROKE_LOWER_END_M = 0.0
MAX_LOGGED_LOCK_EVENTS = 2000
HARNESS_VALVE_TAU_S = 0.1
"""The harness valve lag is always on with this value (``c2py_r8d1_closed_loop.VALVE_LAG_S``)."""
_LAST_STEPPED: list = [None]
"""The plant stepped last in this process (the one the next controller read measures)."""
_LAST_ARMED: list = [None]
"""The plant armed last in this process (the event branch runs on it), for the run record."""
_INSTALLED: dict = {}
_LAST_PRESET: list = [None]
CONTROL_PERIOD_S = 0.1
"""R8 C2 period `T` (spec 2.6: plant rule alone needs `t_c <= T`)."""
WAIT_SPEED_FACTOR = 2.0
"""Spec 2.5: a waiting leg hands the law ``2 eps`` so that it stays in its moving branch."""
TIME_TOL_S = 1.0e-9
ANCHOR_EXCESS_COUNTED_PA = 0.1e5
"""Criteria rev. 6 4.5: an extension lock with ``p_r0 - p_ext`` above this is counted."""
ANCHOR_RISK_PA = 11.0e5
"""Criteria rev. 6 4.5: ``p_r0 - p_ext`` above 11 bar (``p_r0`` above the 13 bar fallback
start)."""
BAR = 1.0e5


class _RodPressureLag:
    """Moving rod pressure of one plant: lag capped by the valve flow (module docstring).

    Args:
        plant: The armed harness plant.
        flow_law: The law (r5 :class:`RodPressureFlowLaw` by default; P3 the r6 law, which
            also reads the head pressure of the step).
    """

    def __init__(self, plant, flow_law: RodPressureFlowLaw | None = None) -> None:
        head_area_m2 = plant.flow_limiter.params.A_h
        self._legs = [
            RodChamberLegParams(
                head_area_m2=float(head_area_m2[i]),
                annulus_area_m2=float(plant.A_ann[i]),
                head_stiffness_N_m=float(plant.kh[i]),
                rod_stiffness_N_m=float(plant.kr[i]),
                outer_stiffness_N_m=UNUSED_OUTER_STIFFNESS_N_M,
                rod_weight_N=0.0)
            for i in range(LEG_COUNT)]
        self.flow_law = RodPressureFlowLaw() if flow_law is None else flow_law
        # the harness oil columns are frozen at e_op, so C_r is one value per leg
        self._compliance_m3_Pa = [
            self.flow_law.rod_compliance_m3_Pa(leg.annulus_area_m2, leg.head_stiffness_N_m,
                                               leg.rod_stiffness_N_m)
            for leg in self._legs]
        self._step_s = float(plant.dt)
        self._lag_s = float(plant.tau)
        self.pressure_Pa = np.zeros(LEG_COUNT)
        self.last_target_Pa = np.full(LEG_COUNT, np.nan)
        """``p*`` the law used in the last moving step per leg (the J-P3c / RET share boundary,
        ``hydraulics_remedy_review.md`` 10; NaN before the first moving step)."""

    def start(self, leg: int, pressure_Pa: float) -> None:
        self.pressure_Pa[leg] = pressure_Pa

    def relax(self, leg: int, direction: float, force_N: float, speed_m_s: float) -> float:
        """One inner step of ``leg``; ``speed_m_s`` is the kernel speed of the step."""
        mode = RodChamberMode.EXT if direction > 0.0 else RodChamberMode.RET
        params = self._legs[leg]
        target_Pa = params.moving_target_rod_pressure_Pa(mode, force_N)
        self.last_target_Pa[leg] = target_Pa
        previous_Pa = float(self.pressure_Pa[leg])
        if isinstance(self.flow_law, RodPressureFlowLawR6):  # P3: the law reads F and p_bA
            self.pressure_Pa[leg] = self.flow_law.rod_pressure_with_force_Pa(
                previous_Pa, target_Pa, speed_m_s, self._step_s, self._lag_s,
                self._compliance_m3_Pa[leg], params.head_area_m2, params.annulus_area_m2,
                mode is RodChamberMode.RET, force_N, params.p_head_back_retract_Pa)
            return self.pressure_Pa[leg]
        self.pressure_Pa[leg] = self.flow_law.rod_pressure_Pa(
            previous_Pa, target_Pa, speed_m_s, self._step_s, self._lag_s,
            self._compliance_m3_Pa[leg], params.head_area_m2, params.annulus_area_m2,
            is_retract=mode is RodChamberMode.RET)
        return self.pressure_Pa[leg]

    def extension_target_Pa(self, leg: int, force_N: float) -> float:
        """``p*`` of an extension at the net force ``force_N``."""
        return self._legs[leg].moving_target_rod_pressure_Pa(RodChamberMode.EXT, force_N)

    def extension_excess_Pa(self, leg: int, force_N: float) -> float:
        """``max(p_tr - p*, 0)``: the rod pressure an ended extension had not yet relieved
        (``p_tr`` = the lag of the last moving step, ``p*`` = extension target at ``force_N``)."""
        return max(float(self.pressure_Pa[leg]) - self.extension_target_Pa(leg, force_N), 0.0)


@dataclass(frozen=True)
class ExtensionLock:
    """One lock after an extension (criteria rev. 6 4.5 log)."""

    t_s: float
    leg: int
    tracked_Pa: float
    target_Pa: float
    anchor_Pa: float
    knee_N: float


class _AnchorRecord:
    """Criteria rev. 6 4.5 counters per leg (the Chrono judge uses the same names)."""

    def __init__(self) -> None:
        self.locks = [0] * LEG_COUNT
        self.excess_locks = [0] * LEG_COUNT
        self.risk_locks = [0] * LEG_COUNT
        self.max_excess_Pa = [0.0] * LEG_COUNT
        self.max_knee_N = [0.0] * LEG_COUNT
        self.log: list[ExtensionLock] = []

    def add(self, lock: ExtensionLock, excess_Pa: float) -> None:
        """``excess_Pa`` = ``p_r0 - p_ext`` of the lock."""
        leg = lock.leg
        self.locks[leg] += 1
        self.excess_locks[leg] += int(excess_Pa > ANCHOR_EXCESS_COUNTED_PA)
        self.risk_locks[leg] += int(excess_Pa > ANCHOR_RISK_PA)
        self.max_excess_Pa[leg] = max(self.max_excess_Pa[leg], excess_Pa)
        self.max_knee_N[leg] = max(self.max_knee_N[leg], lock.knee_N)
        if len(self.log) < MAX_LOGGED_LOCK_EVENTS:
            self.log.append(lock)

    def record(self) -> dict:
        return {"ext_lock_count": list(self.locks),
                "ext_lock_excess_count": list(self.excess_locks),
                "ext_lock_excess_max_bar": [value / BAR for value in self.max_excess_Pa],
                "ext_lock_risk_count": list(self.risk_locks),
                "ext_lock_knee_max_kN": [value / 1e3 for value in self.max_knee_N],
                "ext_lock_log": [[round(lock.t_s, 6), lock.leg, lock.tracked_Pa,
                                  lock.target_Pa, lock.anchor_Pa, lock.knee_N]
                                 for lock in self.log],
                "ext_lock_log_columns": ["t_s", "leg", "p_tr_Pa", "p_star_Pa", "p_r0_Pa",
                                         "dF_knee_N"]}


LOCK_LOG_COLUMNS = ("t_lock_s", "leg", "direction", "p_tr_before_Pa", "p_r0_Pa", "Gr_lock_N",
                    "p_tr_after_Pa", "dp_tr_step_Pa", "dp_h_step_Pa", "t_release_s",
                    "release_cause", "gate_wait_s", "dF_lock_N", "dp_tr_lock_Pa",
                    "monitor_class_at_lock", "monitor_stretch_open")
"""``jp3_remedy_spec.md`` 6.3 per-lock row."""
RELOCK_STEP_COUNTED_PA = 1.0e5
"""Hydraulics 7 recommendation: a lock whose truth steps by more than 1 bar is counted."""
RELEASE_BY_GATE = "gate"
RELEASE_BY_COMMAND = "command"
SEED_LOG_COLUMNS = ("t_s", "leg", "p_h_Pa", "p_r_locked_Pa", "seed_Pa", "step_Pa",
                    "dp_h_read_Pa", "net_force_step_N", "net_force_release_step_N",
                    "net_force_seed_step_N", "m2_previous_unset", "m2_shift_clipped")
"""Edition 4 ``p1_retract_seed_log`` row (spec 6.3; ``leg`` = index as in ``lock_log``).

* ``net_force_step_N`` = the read net force step at the seed instant, ``dp_h_read A_h - step
  A_ann``: 0 by definition (the head reading is solved from the net force), an implementation
  check column, never judged (addendum 4a-2 3.2).
* ``net_force_release_step_N`` = the plant force change over the whole release step, which
  also holds the lag's first relax step (a record).
* ``net_force_seed_step_N`` (addendum 4a-2 3.2, the judged column of P4-4 / T-JR-15 / T-JR-18):
  ``[F_after - F_before] - k_o s_relax`` with ``s_relax = A_ann [(p_start + Delta) - (p_relax
  + Delta w)] / k_h``, the force step the seed itself makes in the release step (0 when the M2
  re-anchor holds the seed, about ``-k_o A_ann dp_seed / k_h`` when it does not).
* ``m2_previous_unset``: the release step had no M2 previous pressure (its shift is 0,
  ``s_relax`` = 0); ``m2_shift_clipped``: the leg's shift of that step was clipped by the stroke
  room (the row cannot split the seed share: not judgeable).

Every value is read from the plant after it computed it; no plant arithmetic changes."""


STALE_SEED_COLUMNS = ("t_release_s", "leg", "seed_from_moving_open", "seed_Pa",
                      "p_r_locked_Pa")
"""Edition 7 3.3 / 3.5 ``stale_seed_release`` log row of an old P1 plant: one per release that
started at a retract opening seed; ``seed_from_moving_open`` = the seed came from a retract
opening while the leg was not locked (the stale M2 seed: such a release is a
``plant_seed_artifact`` of ③ rev 7). Record only."""
FILL_RELEASE_COLUMNS = ("t_release_s", "leg", "p_r_locked_Pa", "fill_rise_Pa")
"""Edition 7 (a) ``p1_fill_release_log`` row: a release that started at the locked truth plus
its held retract fill rise."""


@dataclass(frozen=True)
class ReleaseStepRecord:
    """Plant values of one M2 release step, read after ``s_ref += shift`` (per leg).

    Attributes:
        net_force_after_N: ``pressure()`` after the shift.
        relaxed_Pa: ``p_relax``, the lag pressure after this step's ``relax``.
        weight: ``w`` of the base release decay this step.
        head_stiffness_N_m: ``k_h`` the shift used.
        oil_stiffness_N_m: ``k_o`` of ``pressure()``.
        is_clipped: The leg's shift was clipped by the stroke room this step.
    """

    net_force_after_N: np.ndarray
    relaxed_Pa: np.ndarray
    weight: np.ndarray
    head_stiffness_N_m: np.ndarray
    oil_stiffness_N_m: np.ndarray
    is_clipped: np.ndarray


class _LockLog:
    """Per-lock record of the plant (spec 6.3, record only): the truth step at the lock, the
    release that ends it and the monitor's class of the read before the lock."""

    def __init__(self) -> None:
        self.rows: list[list] = []
        self._open: dict[int, dict] = {}
        """Leg -> the open row (its lock values) until the release."""
        self.gate_held_since_s = np.full(LEG_COUNT, np.nan)
        """P1: start of a nonzero command the gate holds back on a locked leg."""
        self.lock_count = 0
        self.step_over_1bar_count = 0
        self.max_abs_step_Pa = 0.0
        self.retract_seed_count = 0
        self.retract_seed_step_max_Pa = 0.0
        """T-JR-15: the P1 retract M2 seed steps the rod pressure at a release (not a lock
        step, counted apart)."""
        self.seed_rows: list[dict] = []
        self._pending_seed_rows: list[dict] = []

    def on_retract_seed(self, step_Pa: float, row: dict | None = None) -> None:
        """One P1 retract seed; ``row`` = its ``p1_retract_seed_log`` values (edition 4,
        spec 6.3) without ``net_force_step_N``, which :meth:`finish_seed_rows` adds after
        the M2 reference shift of the same inner step."""
        self.retract_seed_count += 1
        if abs(step_Pa) > abs(self.retract_seed_step_max_Pa):
            self.retract_seed_step_max_Pa = step_Pa
        if row is not None and len(self.seed_rows) < MAX_LOGGED_LOCK_EVENTS:
            self.seed_rows.append(row)
            self._pending_seed_rows.append(row)

    def finish_seed_rows(self, step: ReleaseStepRecord) -> None:
        """The seed rows of this release step after its M2 shift: ``net_force_release_step_N``
        (the seed instant plus the lag's first relax step, a record) and the judged
        ``net_force_seed_step_N`` (:data:`SEED_LOG_COLUMNS`)."""
        for row in self._pending_seed_rows:
            leg = row["leg"]
            release_step_N = float(step.net_force_after_N[leg]) - row.pop("net_force_before_N")
            drop_Pa, annulus = row.pop("drop_Pa"), row.pop("annulus_m2")
            relax_shift_m = 0.0
            if not row["m2_previous_unset"]:
                relax_shift_m = annulus * ((row["seed_Pa"] + drop_Pa)
                                           - (float(step.relaxed_Pa[leg])
                                              + drop_Pa * float(step.weight[leg]))
                                           ) / float(step.head_stiffness_N_m[leg])
            row["net_force_release_step_N"] = release_step_N
            row["net_force_seed_step_N"] = (release_step_N
                                            - float(step.oil_stiffness_N_m[leg]) * relax_shift_m)
            row["m2_shift_clipped"] = bool(step.is_clipped[leg])
        self._pending_seed_rows = []

    def on_lock(self, plant, leg: int, p_tr_before_Pa: float, monitor_trace: dict | None) -> None:
        annulus = float(plant.A_ann[leg])
        p_tr_after_Pa = float(plant.p_r0[leg]) - float(plant.Gr_lock[leg]) / annulus
        step_Pa = p_tr_after_Pa - p_tr_before_Pa
        head_area = float(plant.flow_limiter.params.A_h[leg])
        self.lock_count += 1
        if math.isfinite(step_Pa):
            self.step_over_1bar_count += int(abs(step_Pa) > RELOCK_STEP_COUNTED_PA)
            self.max_abs_step_Pa = max(self.max_abs_step_Pa, abs(step_Pa))
        classes = (monitor_trace or {}).get("class")
        model = (monitor_trace or {}).get("model_bound_Pa")
        self._open[leg] = {
            "t_lock_s": round(float(plant.t), 6), "leg": leg,
            "direction": float(plant.last_dir[leg]), "p_tr_before_Pa": p_tr_before_Pa,
            "p_r0_Pa": float(plant.p_r0[leg]), "Gr_lock_N": float(plant.Gr_lock[leg]),
            "p_tr_after_Pa": p_tr_after_Pa, "dp_tr_step_Pa": step_Pa,
            "dp_h_step_Pa": step_Pa * annulus / head_area,
            "force_at_lock_N": float(plant.pressure()[leg]),
            "monitor_class_at_lock": None if classes is None else classes[leg],
            "monitor_stretch_open": None if model is None else bool(math.isfinite(model[leg]))}

    def on_release(self, plant, leg: int, locked_truth_Pa: float) -> None:
        row = self._open.pop(leg, None)
        held_since_s = self.gate_held_since_s[leg]
        self.gate_held_since_s[leg] = np.nan
        if row is None:  # the armed start lock (not a logged lock)
            return
        is_gate = math.isfinite(held_since_s)
        row.update(t_release_s=round(float(plant.t), 6),
                   release_cause=RELEASE_BY_GATE if is_gate else RELEASE_BY_COMMAND,
                   gate_wait_s=float(plant.t) - held_since_s if is_gate else 0.0,
                   dF_lock_N=float(plant.pressure()[leg]) - row.pop("force_at_lock_N"),
                   dp_tr_lock_Pa=locked_truth_Pa - row["p_tr_after_Pa"])
        self._append(row)

    def note_gate_holds(self, t_s: float, is_held: np.ndarray) -> None:
        for leg in np.flatnonzero(is_held):
            if np.isnan(self.gate_held_since_s[leg]):
                self.gate_held_since_s[leg] = t_s

    def _append(self, row: dict) -> None:
        if len(self.rows) < MAX_LOGGED_LOCK_EVENTS:
            self.rows.append([row.get(column) for column in LOCK_LOG_COLUMNS])

    def record(self) -> dict:
        open_rows = []
        for row in self._open.values():
            pending = {key: value for key, value in row.items() if key != "force_at_lock_N"}
            open_rows.append([pending.get(column) for column in LOCK_LOG_COLUMNS])
        rows = (self.rows + open_rows)[:MAX_LOGGED_LOCK_EVENTS]
        return {"lock_log": rows, "lock_log_columns": list(LOCK_LOG_COLUMNS),
                "relock_count": self.lock_count,
                "relock_step_over_1bar_count": self.step_over_1bar_count,
                "max_abs_dp_tr_step_bar": self.max_abs_step_Pa / BAR,
                "p1_retract_seed_count": self.retract_seed_count,
                "p1_retract_seed_step_max_bar": self.retract_seed_step_max_Pa / BAR,
                "p1_retract_seed_log": [[row.get(column) for column in SEED_LOG_COLUMNS]
                                        for row in self.seed_rows],
                "p1_retract_seed_log_columns": list(SEED_LOG_COLUMNS)}


P1_READ_ARRAY_PREFIX = "p1_"
"""T4h array names of the per-read P1 record (``p1_<field>``)."""
P1_READ_FLOAT_FIELDS = ("x_m", "need_m", "drain_m_s", "valve_speed_m_s")
P1_READ_FLAG_FIELDS = ("is_open", "charged", "rod_released", "gate_held")
_P1_READ_RECORD: list[bool] = [False]
"""D0 split (2026-11-23): True = every P1 plant armed later in this process logs its line
state at each controller read. Off by default, so the T4h records of other runs keep their
arrays; record only either way (:func:`enable_p1_read_record`)."""


def enable_p1_read_record() -> None:
    """Turn the per-read P1 record on for the rest of this process (record only)."""
    _P1_READ_RECORD[0] = True


def is_p1_read_record_on() -> bool:
    return _P1_READ_RECORD[0]


class P1ReadLog:
    """P1 line state at the controller reads (D0 split, hydraulics review 7; record only).

    One row per read: the ``CheckOpenGate`` state after the chunk that ended at the read and
    the values of that chunk. ``x_m`` is the line state in stroke units (extend: head area,
    retract: annulus, as ``check_open_delay``), ``need_m`` the retract dead stroke (NaN on
    another step), ``drain_m_s`` the neutral drain, ``valve_speed_m_s`` the speed in front of
    the gate, ``gate_held`` a locked leg with ``|u| > eps`` that the gate kept at speed 0.
    """

    def __init__(self) -> None:
        self.t_s: list[float] = []
        self.rows: list[dict[str, np.ndarray]] = []
        self._chunk_held = np.zeros(LEG_COUNT, bool)
        self._chunk_speed_m_s = np.full(LEG_COUNT, np.nan)

    def note_chunk(self, is_held: np.ndarray, valve_speed_m_s: np.ndarray) -> None:
        self._chunk_held = np.asarray(is_held, bool).copy()
        self._chunk_speed_m_s = np.asarray(valve_speed_m_s, float).copy()

    def note_read(self, t_s: float, gate: CheckOpenGate) -> None:
        self.t_s.append(float(t_s))
        self.rows.append({
            "x_m": np.asarray(gate.x, float).copy(),
            "need_m": np.asarray(gate.step_need_m, float).copy(),
            "drain_m_s": np.asarray(gate.step_drain_m_s, float).copy(),
            "valve_speed_m_s": self._chunk_speed_m_s.copy(),
            "line_dir": np.asarray(gate.line_dir, np.int8).copy(),
            "is_open": np.asarray(gate.is_open, bool).copy(),
            "charged": np.asarray(gate.charged, bool).copy(),
            "rod_released": np.asarray(gate.rod_released, bool).copy(),
            "gate_held": self._chunk_held.copy()})

    def arrays_at(self, t_s: np.ndarray) -> dict[str, np.ndarray]:
        """``p1_*`` arrays on the T4h reads ``t_s`` (row k = the logged read at ``t_s[k]``);
        ``p1_read_found`` marks the reads that have a logged row (NaN / 0 / False elsewhere)."""
        t_s = np.asarray(t_s, float)
        shape = (len(t_s), LEG_COUNT)
        arrays: dict[str, np.ndarray] = {name: np.full(shape, np.nan)
                                         for name in P1_READ_FLOAT_FIELDS}
        arrays.update({name: np.zeros(shape, bool) for name in P1_READ_FLAG_FIELDS})
        arrays["line_dir"] = np.zeros(shape, np.int8)
        found = np.zeros(len(t_s), bool)
        logged_t = np.asarray(self.t_s, float)
        for k, read_t in enumerate(t_s):
            matches = np.flatnonzero(np.abs(logged_t - read_t) <= TIME_TOL_S)
            if not len(matches):
                continue
            found[k] = True
            row = self.rows[int(matches[-1])]  # a repeated read keeps its last state
            for name, values in row.items():
                arrays[name][k] = values
        out = {P1_READ_ARRAY_PREFIX + name: values for name, values in arrays.items()}
        out[P1_READ_ARRAY_PREFIX + "read_found"] = found
        return out


def with_plant_truth_pressures(plant, m, ha):
    """P4 reading (spec 3): rod = the M2 truth ``plant_rod_pressure_Pa()`` (moving: the lag,
    locked: ``p_r0 - G_r / A_ann``), head = ``(F_net + p_r A_ann) / A_h``; the sensor error
    model acts on it afterwards as before.

    Raises:
        RuntimeError: The plant has no M2 truth (P4 needs M2).
    """
    truth = plant.plant_rod_pressure_Pa() if hasattr(plant, "plant_rod_pressure_Pa") else None
    if truth is None:
        raise RuntimeError("rod_reading_truth needs the v5 harness plant with M2")
    # addendum 4a-2 B2 evidence 1 (record only): counted inside the P4 reading itself
    plant.rod_reading_truth_calls = getattr(plant, "rod_reading_truth_calls", 0) + 1
    rod_Pa = np.asarray(truth, float)
    head_Pa = (np.asarray(plant.pressure(), float) + rod_Pa * np.asarray(plant.A_ann, float)) / ha
    return dataclasses.replace(m, head_pressure_Pa=head_Pa, rod_pressure_Pa=rod_Pa)


SENSOR_GRADE_IDEAL = "ideal"
_SENSOR_GRADE: list = [SENSOR_GRADE_IDEAL]
"""Pressure sensor grade of the rows of this process (``extend_bound_check.sensor_grade``,
2nd edition 6.1): the harness reading as it is (``verdict_runs``) is ``ideal``; a runner with
a sensor error model declares its grade (:func:`declare_sensor_grade`)."""


def declare_sensor_grade(grade: str) -> None:
    """The row grade of the following runs of this process (``ideal``, ``normal``,
    ``conservative``, ``old_worst``; r79 levels L0 / L1 ideal, L2* normal, L3, L4).

    Raises:
        ValueError: An unknown grade.
    """
    from outrigger_sim.control.extend_start_bound import SENSOR_GRADES

    if grade not in SENSOR_GRADES:
        raise ValueError(f"sensor grade {grade!r} is not one of {SENSOR_GRADES}")
    _SENSOR_GRADE[0] = grade


def _records_jp3(options: HydraulicOptions) -> bool:
    """The per-lock and per-read 436.9 records run with ③ revision 5 or any P1 .. P4 option."""
    return bool(options.extend_start_hold or options.line_fill_gate is not None
                or options.lock_anchor_continuous or options.rod_flow_cap_all
                or options.rod_reading_truth)


def make_hydraulics_plant_class(base: type, options: HydraulicOptions,
                                damping_N_s_m: tuple[np.ndarray, np.ndarray] | None = None) -> type:
    """Subclass of the flow-limited plant ``base`` with the v5 options.

    Args:
        base: Class from ``harness_flow.make_flow_plant_class``.
        options: The options; ``flow`` is the job of ``FlowSetting`` on the harness.
        damping_N_s_m: (locked, moving) leg dashpots; with LC the plant picks them by its lock
            state at the start of each chunk (the harness picks them by the valve output).

    Returns:
        The plant class, deep-copied state included (the event branches copy plants).
    """
    closure = options.lock_closure
    if (closure is not None or options.check_delay is not None) and damping_N_s_m is None:
        raise ValueError("LC and M1c on the harness need the locked and moving dashpots")
    records_jp3 = _records_jp3(options)

    class HydraulicsPlant(base):
        """Harness plant with the v5 options (module docstring)."""

        def arm(self):
            result = super().arm()
            _LAST_ARMED[0] = self
            self.rod_release = None
            if options.rod_release_force:
                flow_law = RodPressureFlowLawR6() if options.rod_flow_cap_all else None
                self.rod_release = (RodReleaseShift(self.A_ann) if flow_law is None
                                    else RodReleaseShift(self.A_ann, flow_law.law_revision))
                self.rod_pressure_lag = _RodPressureLag(self, flow_law)
                self.anchor_record = _AnchorRecord()
            self.lock_pending_since_s = np.full(LEG_COUNT, np.nan)
            self.lock_events = []
            self.rod_pressure_seed_Pa = np.full(LEG_COUNT, np.nan)
            self.check_delay = None
            if options.check_delay is not None:
                self.check_delay = CheckOpenDelay(options.check_delay,
                                                  _check_delay_circuit(self.flow_limiter.params))
            self.line_fill_gate = None
            self.stale_seed_log = None
            if options.p1_patch is not None:  # edition 7 P1 supplement (a)(c)(d)
                self.line_fill_gate = CheckOpenGateP1Patch(
                    options.line_fill_gate, _check_delay_circuit(self.flow_limiter.params),
                    options.p1_patch)
                self.fill_release_log = []
            elif options.line_fill_gate is not None:  # P1
                self.line_fill_gate = CheckOpenGate(
                    options.line_fill_gate, _check_delay_circuit(self.flow_limiter.params))
                # edition 7 3.3 record key of the old plant (no command reads it)
                self.stale_seed_log = []
                self.stale_seed_counts = [0, 0]
                """Every seeded release and the stale ones among them (the log is capped)."""
                self.seed_from_moving = np.zeros(LEG_COUNT, bool)
            self.p1_read_log = (P1ReadLog() if self.line_fill_gate is not None
                                and is_p1_read_record_on() else None)
            self.lock_log = _LockLog() if records_jp3 else None
            self.last_monitor_trace = None
            """The monitor's revision 5 trace of the last read (the lock log's class)."""
            self.tension_truth = TensionTruthCounter()
            self.extend_targets = _extend_target_model(self)
            self.extend_bound_check = None
            """Created on the first controller read with the ③ bound on (5.5); None = off."""
            return result

        def step(self, u, nsteps):
            _LAST_STEPPED[0] = self
            if not self.armed:
                return super().step(u, nsteps)
            if closure is not None:
                # spec 2.5: the dashpot follows the law's lock state, not the valve output
                self.cn = np.where(self.locked, damping_N_s_m[0], damping_N_s_m[1])
            if self.check_delay is not None:
                accumulated = self._step_with_check_delay(np.asarray(u, float), nsteps)
            elif self.line_fill_gate is not None:
                accumulated = self._step_with_line_fill_gate(np.asarray(u, float), nsteps)
            else:
                accumulated = super().step(u, nsteps)
            self._count_tension_truth(u, nsteps)
            return accumulated

        def _step_with_line_fill_gate(self, u: np.ndarray, nsteps: int):
            """P1: the gate's speeds in front of the flow limit (a held leg stays locked); the
            retract M2 seed is kept (user decision 147, ``CheckOpenGate``)."""
            speed_m_s = np.array(np.broadcast_to(u, (LEG_COUNT,)), dtype=float)
            output = self.line_fill_gate.filter(
                self._check_delay_inputs(speed_m_s, nsteps, self.line_fill_gate))
            if self.lock_log is not None or self.p1_read_log is not None:
                is_held = (np.asarray(self.locked, bool) & (np.abs(speed_m_s) > self.eps)
                           & (output.speed_m_s == 0.0))
                if self.lock_log is not None:
                    self.lock_log.note_gate_holds(float(self.t), is_held)
                if self.p1_read_log is not None:  # D0 record only
                    self.p1_read_log.note_chunk(is_held, speed_m_s)
            for i in np.flatnonzero(np.isfinite(output.opening_rod_pressure_Pa)):
                self._seed_rod_pressure(int(i), float(output.opening_rod_pressure_Pa[i]))
                if self.stale_seed_log is not None:  # record only: the seed's source
                    self.seed_from_moving[i] = not bool(np.asarray(self.locked, bool)[i])
            return super().step(output.speed_m_s, nsteps)

        def note_p1_read(self, t_s: float) -> None:
            """Controller read at ``t_s`` (the plant has not moved since): log the P1 state
            when the D0 record is on (record only)."""
            if getattr(self, "p1_read_log", None) is not None:
                self.p1_read_log.note_read(t_s, self.line_fill_gate)

        def p1_read_arrays(self, t_s: np.ndarray) -> dict[str, np.ndarray]:
            """The ``p1_*`` T4h arrays on the reads ``t_s``; empty with the record off."""
            log = getattr(self, "p1_read_log", None)
            return {} if log is None else log.arrays_at(t_s)

        def _count_tension_truth(self, u, nsteps: int) -> None:
            """Premise ① truth of this chunk (``tension_premise.md`` S-2, record only): an
            unlocked leg with valve speed > 0 and the plant extend target ``p*`` above
            ``p_bB``; ``p*`` = ``RodSideSynth.moving_target_Pa`` of the net force."""
            valve_m_s = np.broadcast_to(np.asarray(u, float), (LEG_COUNT,))
            is_extending = ~np.asarray(self.locked, bool) & (valve_m_s > 0.0)
            if not is_extending.any():
                return
            mode = np.where(is_extending, LegMode.EXTEND, LegMode.LOCKED)
            target_Pa = self.extend_targets.moving_target_Pa(
                np.asarray(self.pressure(), float), mode, np.abs(valve_m_s))
            self.tension_truth.add(is_extending, target_Pa, nsteps * float(self.dt),
                                   float(self.t), self.plant_rod_pressure_Pa())

        def plant_rod_pressure_Pa(self) -> np.ndarray | None:
            """``p_tr`` per leg: the M2 lag of a moving leg, ``p_r0 - G_r / A_ann`` of a locked
            one (5.5); None without M2 (no moving rod pressure in this plant)."""
            if self.rod_release is None:
                return None
            locked_Pa = (np.asarray(self.p_r0, float)
                         - np.asarray(self.Gr, float) / np.asarray(self.A_ann, float))
            if self._has_p1_patch():  # edition 7 (a): the held / trapped retract fill rise
                locked_Pa = locked_Pa + np.asarray(self.line_fill_gate.fill_rise_Pa, float)
            return np.where(np.asarray(self.locked, bool), locked_Pa,
                            self.rod_pressure_lag.pressure_Pa)

        def _has_p1_patch(self) -> bool:
            return isinstance(getattr(self, "line_fill_gate", None), CheckOpenGateP1Patch)

        def check_extend_bound(self, t_s: float, bound_Pa: np.ndarray,
                               locked_model_bound_Pa: np.ndarray | None = None,
                               locked_sources: list | None = None,
                               trace: dict | None = None) -> None:
            """5.5 / 6.4: the controller's ③ bound (and its locked model bound ④) of the read
            at ``t_s`` against this plant (record only; the plant has not moved since).
            ``trace`` = the monitor's revision 5 per-read trace (436.9 J-P3 keys)."""
            self.last_monitor_trace = trace
            plant_Pa = self.plant_rod_pressure_Pa()
            if plant_Pa is None:
                return
            if self.extend_bound_check is None:
                self.extend_bound_check = ExtendBoundCheck(self.A_ann)
                self.extend_bound_check.sensor_grade = _SENSOR_GRADE[0]
            revision_5 = {} if trace is None else {
                "period_classes": trace["class"], "used_bounds": trace["used_bound_Pa"],
                "plant_states": plant_leg_states(self.locked, self.last_dir),
                "trace_row": trace,
                # 3rd edition 6.3: the target of the last moving step; NaN on locked legs
                "p_star_ret_Pa": np.where(np.asarray(self.locked, bool), np.nan,
                                          self.rod_pressure_lag.last_target_Pa),
                # edition 4.1 record: the false-drop count of retract_tracker reads
                "true_force_N": np.asarray(self.pressure(), float).copy()}
            self.extend_bound_check.add(t_s, bound_Pa, plant_Pa,
                                        extend_bound_states(self.locked, self.last_dir),
                                        locked_model_bound_Pa, locked_sources, **revision_5)

        def _step_with_check_delay(self, u: np.ndarray, nsteps: int):
            """Spec 2.0 rows 3 and 6: M1c in front of the flow limit, its shift after the chunk
            (the order of ``m1c_plant.M1cPlant.step``)."""
            output = self.check_delay.filter(self._check_delay_inputs(u, nsteps))
            for i in np.flatnonzero(output.creep_shift_m != 0.0):
                self.sref[i] -= output.creep_shift_m[i]
                if self.locked[i]:
                    self.c_lock[i] -= output.creep_shift_m[i]
            for i in np.flatnonzero(output.lock_damping):
                self.cn = np.array(self.cn, float)
                self.cn[i] = damping_N_s_m[0][i]
            for i in np.flatnonzero(np.isfinite(output.opening_rod_pressure_Pa)):
                self._seed_rod_pressure(int(i), float(output.opening_rod_pressure_Pa[i]))
            accumulated = super().step(output.speed_m_s, nsteps)
            if output.opening_shift_m.any():
                self.sref -= output.opening_shift_m
            return accumulated

        def _check_delay_inputs(self, u: np.ndarray, nsteps: int,
                                model=None) -> CheckDelayInputs:
            """M1c inputs (``model`` = the M1c or P1 object; default M1c). The knee is the
            plant's ``_locked_knee_m`` (the P2 truth-based knee with P2, review 2.4; the same
            value as before 436.9 without P2)."""
            model = self.check_delay if model is None else model
            rod_Pa = (np.asarray(self.p_r0, float) - np.asarray(self.Gr, float)
                      / np.asarray(self.A_ann, float))
            head_Pa = (self.pressure() + rod_Pa * self.A_ann) / model.A_h
            knee_m = np.array([self._locked_knee_m(i) for i in range(LEG_COUNT)])
            void_m = np.where(self.locked,
                              np.maximum(self.sref - self.x - self.c_lock - knee_m, 0.0), 0.0)
            band_N = np.asarray(self.Fs, float) - np.asarray(self.f, float)
            return CheckDelayInputs(self.t, nsteps * self.dt, u, head_Pa, rod_Pa, self.locked,
                                    void_m, band_N, self.sref)

        def _seed_rod_pressure(self, leg: int, pressure_Pa: float) -> None:
            """Spec 2.4: M2 starts its release at the M1c opening pressure (no double creep);
            the seed goes into ``p`` only, ``Delta`` stays (revision 4)."""
            if self.rod_release is None:
                return
            self.rod_pressure_seed_Pa[leg] = pressure_Pa

        def _rod_force(self, u):
            was_locked = self.locked.copy()
            kernel_speed_m_s = np.asarray(u, float)  # the flow cap reads it, not the 2 eps wait
            if closure is not None:
                u = self._closing_delay_speed(kernel_speed_m_s)
            rod_force_N = super()._rod_force(u)
            self._record_lock_changes(was_locked)
            tracked_before_Pa = None
            if self.lock_log is not None:  # 436.9 records only
                self._log_releases(was_locked, rod_force_N)
                tracked_before_Pa = (np.full(LEG_COUNT, np.nan) if self.rod_release is None
                                     else self.rod_pressure_lag.pressure_Pa.copy())
            if self.rod_release is not None:
                if options.lock_anchor_continuous:
                    self._anchor_continuous(was_locked)
                else:
                    self._anchor_extension_locks(was_locked)
                self._shift_reference_for_rod_pressure(rod_force_N, was_locked, kernel_speed_m_s)
            if tracked_before_Pa is not None:
                self._log_locks(was_locked, tracked_before_Pa)
            if self._has_p1_patch():  # edition 7 (a): a new lock starts without a fill rise
                for i in np.flatnonzero(self.locked & ~was_locked):
                    self.line_fill_gate.clear_fill(int(i))
            return rod_force_N

        def _log_releases(self, was_locked, rod_force_N) -> None:
            """Released legs of this step: the locked truth ``p_r0 - G_r / A_ann`` at the
            release (``G_r`` = ``r0`` of the release step)."""
            for i in np.flatnonzero(was_locked & ~self.locked):
                leg = int(i)
                truth_Pa = float(self.p_r0[leg]) - float(rod_force_N[leg]) / float(self.A_ann[leg])
                self.lock_log.on_release(self, leg, truth_Pa)

        def _log_locks(self, was_locked, tracked_before_Pa) -> None:
            """Legs locked in this step (after the anchor of this step was set)."""
            for i in np.flatnonzero(self.locked & ~was_locked):
                leg = int(i)
                self.lock_log.on_lock(self, leg, float(tracked_before_Pa[leg]),
                                      self.last_monitor_trace)

        def _anchor_continuous(self, was_locked) -> None:
            """P2: every leg locked in this step anchors at ``p_r0 = max(p_lag, p_floor) +
            G_r,lock / A_ann`` (``p_lag`` = M2 lag of the last moving step), so the locked truth
            ``p_r0 - G_r / A_ann`` starts at the lag; extension locks keep the 4.5 record."""
            newly_locked = self.locked & ~was_locked
            if not newly_locked.any():
                return
            lag = self.rod_pressure_lag
            net_force_N = self.pressure()
            for i in np.flatnonzero(newly_locked):
                leg = int(i)
                tracked_Pa = float(lag.pressure_Pa[leg])
                truth_Pa = max(tracked_Pa, self.p_floor)
                annulus = float(self.A_ann[leg])
                self.p_r0[leg] = truth_Pa + float(self.Gr_lock[leg]) / annulus
                if self.last_dir[leg] <= 0:
                    continue
                target_Pa = lag.extension_target_Pa(leg, float(net_force_N[leg]))
                knee_N = ((truth_Pa - self.p_floor) * annulus
                          * (self.kh[leg] + self.kr[leg]) / self.kr[leg])
                lock = ExtensionLock(float(self.t), leg, tracked_Pa, target_Pa,
                                     float(self.p_r0[leg]), float(knee_N))
                self.anchor_record.add(lock, truth_Pa - float(self.p_ext[leg]))

        def _anchor_extension_locks(self, was_locked) -> None:
            """Revision 5: the anchor of a leg locked in this step after an extension keeps the
            unrelieved rod pressure, ``p_r0 = max(min(p_tr, p_ext + max(p_tr - p*, 0)),
            p_floor)`` (the ``min`` matches L2b, hydraulics-expert 2026-11-07: never above the
            tracked pressure; ``p_tr >= p* > p_ext`` in the YAML conditions keeps it inert)."""
            newly_locked = self.locked & ~was_locked & (self.last_dir > 0)
            if not newly_locked.any():
                return
            net_force_N = self.pressure()
            lag = self.rod_pressure_lag
            for i in np.flatnonzero(newly_locked):
                leg = int(i)
                tracked_Pa = float(lag.pressure_Pa[leg])
                target_Pa = lag.extension_target_Pa(leg, float(net_force_N[leg]))
                excess_Pa = max(tracked_Pa - target_Pa, 0.0)
                anchor_Pa = max(min(tracked_Pa, float(self.p_ext[leg]) + excess_Pa),
                                self.p_floor)
                self.p_r0[leg] = anchor_Pa
                knee_N = ((anchor_Pa - self.p_floor) * self.A_ann[leg]
                          * (self.kh[leg] + self.kr[leg]) / self.kr[leg])
                lock = ExtensionLock(float(self.t), leg, tracked_Pa, target_Pa, anchor_Pa,
                                     float(knee_N))
                self.anchor_record.add(lock, anchor_Pa - float(self.p_ext[leg]))

        def _closing_delay_speed(self, u: np.ndarray) -> np.ndarray:
            """Spec 2.5 timer: a leg whose flow stopped stays in the moving law for ``t_c``.

            The law gets ``2 eps`` in its last direction while the leg waits (the kernel still
            gets ``u = 0``), then 0, so it locks ``t_c`` after the cut; a command inside the wait
            releases without a lock (H5).
            """
            law_speed = u.copy()
            for i in range(LEG_COUNT):
                if self.locked[i] or abs(u[i]) > self.eps:
                    self.lock_pending_since_s[i] = np.nan
                    continue
                if np.isnan(self.lock_pending_since_s[i]):
                    self.lock_pending_since_s[i] = self.t
                if self.t - self.lock_pending_since_s[i] < closure.closing_delay_s - TIME_TOL_S:
                    law_speed[i] = WAIT_SPEED_FACTOR * self.eps * self.last_dir[i]
            return law_speed

        def _record_lock_changes(self, was_locked) -> None:
            for i in np.flatnonzero(self.locked != was_locked):
                self.lock_events.append((round(float(self.t), 6), int(i), bool(self.locked[i])))

        def _shift_reference_for_rod_pressure(self, rod_force_N, was_locked,
                                              kernel_speed_m_s) -> None:
            """Spec 2.3: M2 on the state after the law; acts from this inner step on."""
            pressure_Pa = self.p_r0 - rod_force_N / self.A_ann
            net_force_N = self.pressure()
            lag = self.rod_pressure_lag
            speed_m_s = np.broadcast_to(kernel_speed_m_s, (LEG_COUNT,))
            weight = np.zeros(LEG_COUNT)
            for i in np.flatnonzero(~self.locked):
                if was_locked[i]:
                    self._start_release(i, float(pressure_Pa[i]), float(rod_force_N[i]),
                                        float(net_force_N[i]))
                pressure_Pa[i] = lag.relax(i, float(self.last_dir[i]), float(net_force_N[i]),
                                           float(speed_m_s[i]))
                weight[i] = release_weight(float(self.t - self.t_rel[i]), float(self.tau))
            clipped_before = (None if self.lock_log is None
                              else self.rod_release.clipped_steps)  # a copy (record only)
            shift_m = self.rod_release.shift_m(
                pressure_Pa, self.kh, ~self.locked, STROKE_LOWER_END_M - self.sref,
                self.geo.stroke - self.sref, release_weight=weight, t_s=float(self.t))
            self.sref += shift_m
            if self.lock_log is not None:  # record only: reads the values computed above
                self.lock_log.finish_seed_rows(ReleaseStepRecord(
                    net_force_after_N=np.asarray(self.pressure(), float),
                    relaxed_Pa=pressure_Pa.copy(), weight=weight.copy(),
                    head_stiffness_N_m=np.broadcast_to(np.asarray(self.kh, float),
                                                       (LEG_COUNT,)).copy(),
                    oil_stiffness_N_m=np.broadcast_to(np.asarray(self.ko, float),
                                                      (LEG_COUNT,)).copy(),
                    is_clipped=self.rod_release.clipped_steps != clipped_before))

        def _start_release(self, leg: int, locked_pressure_Pa: float,
                           release_force_N: float, net_force_N: float = math.nan) -> None:
            """The lag starts at the locked pressure or the M1c seed; ``Delta = Gr(t_rel) /
            A_ann`` (= ``p_r0 - p_r,rel``; ``Gr`` is ``r0`` in the release step)."""
            seed_Pa = self.rod_pressure_seed_Pa[leg]
            if self._has_p1_patch():  # edition 7 (a)(d): the truth with its fill rise, no seed
                seed_Pa = self._fill_release_start_Pa(leg, locked_pressure_Pa)
            elif self.stale_seed_log is not None and not np.isnan(seed_Pa):
                self._log_stale_seed(leg, locked_pressure_Pa, float(seed_Pa))
            start_Pa = locked_pressure_Pa if np.isnan(seed_Pa) else float(seed_Pa)
            drop_Pa = release_force_N / float(self.A_ann[leg])
            if self.lock_log is not None and not np.isnan(seed_Pa):
                self.lock_log.on_retract_seed(
                    start_Pa - locked_pressure_Pa,
                    self._seed_row(leg, locked_pressure_Pa, start_Pa, drop_Pa, net_force_N))
            self.rod_pressure_seed_Pa[leg] = np.nan
            self.rod_pressure_lag.start(leg, start_Pa)
            self.rod_release.release(leg, ReleaseStart(start_Pa, drop_Pa))

        def _fill_release_start_Pa(self, leg: int, locked_pressure_Pa: float) -> float:
            """Edition 7 (a): the release starts at the locked truth plus the held fill rise
            (NaN without a rise: the plain locked start); the rise is then gone."""
            gate = self.line_fill_gate
            rise_Pa = float(gate.fill_rise_Pa[leg])
            gate.clear_fill(leg)
            self.rod_pressure_seed_Pa[leg] = np.nan  # (d): never a seed path
            if not rise_Pa > 0.0:
                return math.nan
            if len(self.fill_release_log) < MAX_LOGGED_LOCK_EVENTS:
                self.fill_release_log.append([round(float(self.t), 6), leg,
                                              locked_pressure_Pa, rise_Pa])
            return locked_pressure_Pa + rise_Pa

        def _log_stale_seed(self, leg: int, locked_pressure_Pa: float, seed_Pa: float) -> None:
            """Edition 7 3.3 record of the old plant (``stale_seed_release``): a release that
            starts at a retract opening seed, and whether that seed came from an opening while
            the leg was moving (the stale M2 seed of hydraulics H1). Record only."""
            is_stale = bool(self.seed_from_moving[leg])
            self.stale_seed_counts[0] += 1
            self.stale_seed_counts[1] += int(is_stale)
            if len(self.stale_seed_log) < MAX_LOGGED_LOCK_EVENTS:
                self.stale_seed_log.append([round(float(self.t), 6), leg, is_stale, seed_Pa,
                                            locked_pressure_Pa])
            self.seed_from_moving[leg] = False

        def stale_seed_release_record(self) -> dict | None:
            """``stale_seed_release`` of an old P1 plant (None for the others). The counts
            cover every seeded release; the log keeps the first
            :data:`MAX_LOGGED_LOCK_EVENTS` rows and ``log_truncated`` says when it lost some
            (hydraulics review ``hydraulics_p1a_review.md`` 3)."""
            log = getattr(self, "stale_seed_log", None)
            if log is None:
                return None
            releases, stale = self.stale_seed_counts
            return {"releases_with_seed": releases, "stale_releases": stale,
                    "log_rows": len(log), "log_truncated": releases > len(log),
                    "log": [list(row) for row in log],
                    "log_columns": list(STALE_SEED_COLUMNS)}

        def _seed_row(self, leg: int, locked_pressure_Pa: float, seed_Pa: float,
                      drop_Pa: float, net_force_N: float) -> dict:
            """The ``p1_retract_seed_log`` values known at the release (record only); the
            release step's values follow in :meth:`_LockLog.finish_seed_rows`."""
            step_Pa = seed_Pa - locked_pressure_Pa
            annulus = float(self.A_ann[leg])
            head_area = float(self.flow_limiter.params.A_h[leg])
            return {
                "t_s": round(float(self.t), 6), "leg": leg,
                "p_h_Pa": (net_force_N + locked_pressure_Pa * annulus) / head_area,
                "p_r_locked_Pa": locked_pressure_Pa, "seed_Pa": seed_Pa,
                "step_Pa": step_Pa, "dp_h_read_Pa": step_Pa * annulus / head_area,
                "net_force_step_N": (step_Pa * annulus / head_area) * head_area
                - step_Pa * annulus,
                "net_force_before_N": net_force_N, "drop_Pa": drop_Pa, "annulus_m2": annulus,
                "m2_previous_unset": not self.rod_release.has_previous_pressure}

    if options.lock_anchor_continuous:
        HydraulicsPlant._locked_knee_m = _continuous_knee_m
    HydraulicsPlant.v5_options = options
    return HydraulicsPlant


def _continuous_knee_m(plant, i: int) -> float:
    """P2 knee: the locked truth ``p_r0 - G_r / A_ann`` reaches ``p_floor`` at the knee (the
    base knee counts from ``p_r0``, which is off by ``G_r,lock / A_ann`` after a relock)."""
    truth_anchor_Pa = plant.p_r0[i] - plant.Gr_lock[i] / plant.A_ann[i]
    return (truth_anchor_Pa - plant.p_floor) * plant.A_ann[i] / plant.kr[i]


def install_overlap_cut(closed_loop_module, setting, v_max_m_s: float, zero_command_m_s: float):
    """Spec 2.5 on the harness: replace ``closed_loop_module._lagged_step`` by one that stops the
    chunk mean valve speed of a zero command at or below ``u_ol`` (``install_command_clip``
    precedent; the ``is_*`` markers stay). The valve state keeps decaying."""
    lagged_step = closed_loop_module._lagged_step
    overlap_speed = setting.overlap_speed_m_s(v_max_m_s)

    class _CutPlant:
        """The plant as ``_lagged_step`` sees it: ``step`` gets the cut chunk mean speed."""

        def __init__(self, plant, command):
            self._plant, self._command, self.dt = plant, command, plant.dt

        def step(self, mean_speed, nsteps):
            cut = ((np.abs(self._command) <= zero_command_m_s)
                   & (np.abs(mean_speed) <= overlap_speed) & (mean_speed != 0.0))
            return self._plant.step(np.where(cut, 0.0, mean_speed), nsteps)

    def lagged_step_with_overlap_cut(plant, command, valve, steps):
        return lagged_step(_CutPlant(plant, np.asarray(command, float)), command, valve, steps)

    markers = {name: value for name, value in getattr(lagged_step, "__dict__", {}).items()
               if name.startswith("is_")}
    lagged_step_with_overlap_cut.__dict__.update(markers)
    closed_loop_module._lagged_step = lagged_step_with_overlap_cut


LIFT_TIME_TOL_S = 1e-9


def clipped_steps_by_lift(clip_times_s: list[list[float]], total: list[int],
                          t_lift_s: float | None) -> dict:
    """v5 criteria rev. 2 2.1: M2 clipped steps per leg before (t < t_lift - 1e-9) and after the
    first crawler lift-off; without a lift-off every clip counts after.

    Raises:
        RuntimeError: The split does not add up to the clipped-step total.
    """
    pre = [0 if t_lift_s is None else sum(t < t_lift_s - LIFT_TIME_TOL_S for t in times)
           for times in clip_times_s]
    post = [len(times) - before for times, before in zip(clip_times_s, pre, strict=True)]
    if [a + b for a, b in zip(pre, post, strict=True)] != list(total):
        raise RuntimeError(f"M2 clip split {pre} + {post} != total {list(total)}")
    return {"m2_clipped_steps_pre_lift": pre, "m2_clipped_steps_post_lift": post,
            "m2_clip_split_t_lift_s": t_lift_s}


def plant_record(plant, t_lift_s: float | None = None) -> dict:
    """Per-leg v5 totals of one plant for the result (M2 shift, clipped steps split at the
    first lift-off ``t_lift_s``)."""
    if plant is None:
        return {}
    record = {}
    if getattr(plant, "rod_release", None) is not None:
        record["m2_law"] = plant.rod_pressure_lag.flow_law.meta()
        record.update(plant.rod_release.record())
        record.update(plant.anchor_record.record())
        record.update(clipped_steps_by_lift(plant.rod_release.clip_times_s,
                                            record["m2_clipped_steps"], t_lift_s))
    if getattr(plant, "lock_events", None) is not None:
        record["lock_events"] = plant.lock_events[:MAX_LOGGED_LOCK_EVENTS]
    if getattr(plant, "check_delay", None) is not None:
        record["check_delay"] = plant.check_delay.summary()
    if getattr(plant, "line_fill_gate", None) is not None:
        record["line_fill_gate"] = plant.line_fill_gate.summary()
        record["p1_output_exceptions"] = list(plant.line_fill_gate.summary()["output_exceptions"])
    stale_record = getattr(plant, "stale_seed_release_record", None)
    if stale_record is not None and stale_record() is not None:  # edition 7 3.3, old P1 plant
        record["stale_seed_release"] = stale_record()
    if getattr(plant, "fill_release_log", None) is not None:  # edition 7 P1 supplement
        record["p1_fill_release_log"] = [list(row) for row in plant.fill_release_log]
        record["p1_fill_release_log_columns"] = list(FILL_RELEASE_COLUMNS)
    if getattr(plant, "p1_read_log", None) is not None:  # D0 record only
        record["p1_read_record"] = {"reads": len(plant.p1_read_log.t_s),
                                    "t4h_prefix": P1_READ_ARRAY_PREFIX}
    if getattr(plant, "lock_log", None) is not None:
        record.update(plant.lock_log.record())
    if getattr(plant, "extend_targets", None) is not None:  # an armed v5 plant (B2 evidence)
        record.update({key: int(getattr(plant, key, 0)) for key in ROD_READING_EVIDENCE_KEYS})
    if getattr(plant, "tension_truth", None) is not None:
        record["tension_truth"] = plant.tension_truth.record()
        check = getattr(plant, "extend_bound_check", None)
        record["extend_bound_check"] = None if check is None else check.record()
    return record


def install_extend_bound_check() -> None:
    """Every ``c2.C2Controller`` of this process hands its ③ bound to the plant it reads after
    each update (``tension_premise.md`` 5.5; record only, the output is untouched). The plant
    is the harness plant stepped last, taken only when its time equals the read time."""
    from outrigger_sim.control import c2

    base = c2.C2Controller
    if getattr(base, "_extend_bound_checked", False):
        return

    class BoundCheckedController(base):
        _extend_bound_checked = True

        def update(self, measurements):
            output = super().update(measurements)
            plant = _LAST_STEPPED[0]
            check = getattr(plant, "check_extend_bound", None)
            if check is None or abs(float(plant.t) - float(measurements.t_s)) > TIME_TOL_S:
                return output
            note_p1_read = getattr(plant, "note_p1_read", None)
            if note_p1_read is not None:  # D0 per-read P1 record (no-op while it is off)
                note_p1_read(float(measurements.t_s))
            if _has_rod_reading(measurements):  # addendum 4a-2 B2 evidence 2 (record only)
                plant.two_pressure_reads = getattr(plant, "two_pressure_reads", 0) + 1
            bound_Pa = self.extend_bound_Pa()
            if bound_Pa is not None:
                trace = self.extend_bound_trace_row()  # None below ③ revision 5
                revision_5 = {} if trace is None else {"trace": trace}
                check(float(measurements.t_s), bound_Pa, self.locked_model_bound_Pa(),
                      self.locked_model_bound_sources(), **revision_5)
            return output

    c2.C2Controller = BoundCheckedController


def _has_rod_reading(measurements) -> bool:
    """The controller read a rod-side pressure this period (a finite value on some leg)."""
    rod_Pa = getattr(measurements, "rod_pressure_Pa", None)
    return rod_Pa is not None and bool(np.isfinite(np.asarray(rod_Pa, float)).any())


def _extend_target_model(plant):
    """``RodSideSynth`` of the plant's legs for its ``moving_target_Pa`` (the extend target the
    ``dyn_map`` rod reading of r79 uses; the stroke, dead length and period do not enter it)."""
    from outrigger_sim.params import load_params

    params = load_params()
    flow_params = plant.flow_limiter.params
    return RodSideSynth(RodSideParams.from_params(params), np.asarray(flow_params.A_h, float),
                        np.asarray(plant.A_ann, float), float(flow_params.stroke),
                        float(flow_params.L0h), CONTROL_PERIOD_S)


def _check_delay_circuit(params) -> CheckDelayCircuit:
    """The M1c circuit from the harness parameters (``params.py``, as ``m1c_plant.M1cState``)."""
    return CheckDelayCircuit(head_area_m2=np.asarray(params.A_h, float),
                             annulus_area_m2=np.asarray(params.A_r, float),
                             stroke_m=float(params.stroke), rod_dead_length_m=float(params.L0r),
                             head_dead_length_m=float(params.L0h),
                             bulk_modulus_Pa=float(params.beta), tank_pressure_Pa=float(params.p_T),
                             max_speed_m_s=float(params.v_max),
                             compensator_drop_Pa=float(params.dp_comp))


def options_of(plant) -> HydraulicOptions:
    return getattr(type(plant), "v5_options", HydraulicOptions())


def last_armed_record(t_lift_s: float | None = None) -> dict:
    return plant_record(_LAST_ARMED[0], t_lift_s)


def install(verdict_runs_module, options: HydraulicOptions) -> None:
    """Every plant built from now on in this process carries ``options``.

    The patch stays for the rest of the process, so a worker runs one such case.

    Raises:
        ValueError: Options the harness takes elsewhere or does not have.
    """
    if options.flow is not None:
        raise ValueError("the harness flow limit is the FlowSetting of the run, not options.flow")
    validate(options, period_s=CONTROL_PERIOD_S)
    if options.valve_tau_s is not None and options.valve_tau_s != HARNESS_VALVE_TAU_S:
        raise ValueError(f"the harness valve lag is fixed at {HARNESS_VALVE_TAU_S} s")
    if _INSTALLED.get(id(verdict_runs_module)) is not None:
        if _INSTALLED[id(verdict_runs_module)] != options:
            raise RuntimeError("other v5 options are installed in this process already")
        return
    _INSTALLED[id(verdict_runs_module)] = options
    make_flow_plant_class = verdict_runs_module.make_flow_plant_class
    import s9_soil_closed_loop as soil
    from params import load_params

    damping = (soil.C_LOCK, soil.C_MOVE)
    if options.lock_closure is not None:
        install_overlap_cut(soil._imports()[0], options.lock_closure, load_params().v_max,
                            LOCK_SPEED_EPS_M_S)

    def make_class(base, setting):
        return make_hydraulics_plant_class(make_flow_plant_class(base, setting), options, damping)

    if (options.lock_window_follows_plant or options.extend_start_tracked
            or options.lsb_components or options.probe_d6_settings):
        install_lock_window(options, load_params().v_max)
    install_extend_bound_check()
    if options.rod_reading_truth:
        install_rod_reading_truth()

    verdict_runs_module.make_flow_plant_class = make_class


R64_MODULE = "r64_g4_closed_loop"


def install_rod_reading_truth() -> None:
    """P4 on the event path: the S8 harness reads ``r64.with_two_pressures`` at call time, so
    the module attribute becomes :func:`with_plant_truth_pressures` once the S8 modules are
    imported (``s9_soil_event_screen._s8_modules``, which imports them under its own argv).
    The steady path gives no rod reading (criteria revision 9 3.1) and is not touched.

    Addendum 4a-2 B2: an ``r64_g4_closed_loop`` module imported already (the standalone
    ``r67_g1_screen`` worker imports it before it installs the setting) is patched at once; the
    evidence keys :data:`ROD_READING_EVIDENCE_KEYS` show whether the reading reached the
    controller on any path (r79 takes P4 through its own ``R79_ROD_MODEL=plant_truth``)."""
    import s9_soil_event_screen as study_a

    imported_r64 = sys.modules.get(R64_MODULE)
    if imported_r64 is not None:
        imported_r64.with_two_pressures = with_plant_truth_pressures
    if getattr(study_a._s8_modules, "_rod_reading_truth", False):
        return
    load_s8_modules = study_a._s8_modules

    def s8_modules_with_truth_reading():
        modules = load_s8_modules()
        modules["r64"].with_two_pressures = with_plant_truth_pressures
        return modules

    s8_modules_with_truth_reading._rod_reading_truth = True
    study_a._s8_modules = s8_modules_with_truth_reading


def install_lock_window(options: HydraulicOptions, v_max_m_s: float) -> None:
    """Every ``C2Config.with_10hz_d1`` preset of this process gets the controller options of
    ``options`` (``apply_controller_options``: the plant lock window, spec 2.6, ``acc_common.py``
    precedent, the ③ start bound of the VB / LS definition, criteria revision 8, and the
    edition 6 components). Once per process; the last preset is kept for the meta checks
    (:func:`check_last_lock_window`, :func:`check_last_lock_start_b`)."""
    from outrigger_sim.control import c2

    if getattr(c2.C2Config, "_v5_lock_window", None) is not None:
        if c2.C2Config._v5_lock_window != options:
            raise RuntimeError("another lock window is installed in this process already")
        return
    preset = c2.C2Config.with_10hz_d1

    def with_10hz_d1(self, *args, **kwargs):
        config = apply_controller_options(preset(self, *args, **kwargs), options, v_max_m_s,
                                          HARNESS_VALVE_TAU_S)
        _LAST_PRESET[0] = config
        return config

    c2.C2Config.with_10hz_d1 = with_10hz_d1
    c2.C2Config._v5_lock_window = options


def check_last_extend_start(options: HydraulicOptions) -> None:
    """Criteria revision 8 3.1: a run with ``extend_start_tracked`` built its preset with the
    ③ start bound.

    Raises:
        RuntimeError: No preset was built, or its two-pressure rule is not the bound.
    """
    if not options.extend_start_tracked:
        return
    preset = _LAST_PRESET[0]
    meta = {} if preset is None else preset.two_pressure.to_meta()
    rule = meta.get("extend_start_rule")
    if rule != "tracked_bound":
        raise RuntimeError(f"extend_start_tracked run with the preset rule {rule!r}")
    revision = (meta.get("extend_start_bound") or {}).get("revision")
    if revision != options.extend_start_revision:  # 436.9: hold runs build revision 5
        raise RuntimeError(f"③ bound revision {revision!r} of the preset is not "
                           f"{options.extend_start_revision} of the options")


def check_last_lock_start_b(options: HydraulicOptions, run_config=None) -> None:
    """Edition 6 identity guard (``jp3_remedy_spec_v6.md`` 3.4): the preset this process built
    and the run's own controller config both carry the components and thresholds of
    ``options``.

    Raises:
        RuntimeError: No preset was built, or a config differs from the options.
    """
    if _LAST_PRESET[0] is None:
        raise RuntimeError("no C2 preset was built with the edition 6 options installed")
    check_lock_start_b_config(_LAST_PRESET[0], options)
    if run_config is not None:
        check_lock_start_b_config(run_config, options)


def check_last_probe_d6(options: HydraulicOptions, run_config=None) -> None:
    """Edition 7 identity guard (``jp3_remedy_spec_v7.md`` 6.1 ``probe_d6_settings``): the
    preset this process built and the run's own config carry the D6 settings of ``options``.

    Raises:
        RuntimeError: No preset was built, or a config differs from the options.
    """
    if _LAST_PRESET[0] is None:
        raise RuntimeError("no C2 preset was built with the edition 7 options installed")
    check_probe_d6_config(_LAST_PRESET[0], options)
    if run_config is not None:
        check_probe_d6_config(run_config, options)


def check_last_lock_window(options: HydraulicOptions, v_max_m_s: float) -> None:
    """Criteria P-4: the preset the run built carries the window of ``options``.

    Raises:
        RuntimeError: No preset was built, or its meta differs.
    """
    if _LAST_PRESET[0] is None:
        raise RuntimeError("no C2 preset was built with the lock window installed")
    check_lock_window_meta(_LAST_PRESET[0].two_pressure.to_meta(), options, v_max_m_s,
                           HARNESS_VALVE_TAU_S)
