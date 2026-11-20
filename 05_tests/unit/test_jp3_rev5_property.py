"""T-JR-04 (``jp3_remedy_spec.md`` 5.2): the ③ revision 5 monitor against a single-leg plant.

The plant is a reduced RR leg of the harness law (body fixed, the net force ``F(t)`` given):
locked, the truth follows the trapped two-chamber split ``p_r = p_lock + r (F_lock - F) /
A_ann`` (floor clip); moving, the M2 lag of ``flow_limited_rod_pressure`` (r5) or ``_r6`` (P3)
towards ``moving_target_rod_pressure_Pa``; the lock law releases at ``|u| > eps`` and locks at
``|u| <= eps`` (no LC delay). Options: P1 (``CheckOpenGate`` VN in front of the lock law, 1 ms
chunks), P2 (continuous relock anchor; without it the r5 anchors: extension ``max(min(p_m, p_ext
+ (p_m - p*)+), p_floor)``, retraction ``p_ret``). The force is linear inside each period, so
the head extremes lie at the reads (counterexample ⑨ is outside this test).

Every read goes through :class:`ExtendBoundCheckRev5` with the monitor's own class and used
bound; the judged keys must stay 0 on the P1 .. P3 plant (cases ⑤ ⑦ ⑧ and a seeded sweep).
On the old plant revision 4 shows the 436.8 breach of case ⑤ (counterexample record).
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control import extend_start_bound as esb
from outrigger_sim.control.extend_start_bound import (
    EXTEND_HOLD_REVISION,
    ExtendBoundCheck,
    ExtendBoundCheckRev5,
    ExtendStartBound,
    extend_bound_states,
    plant_leg_states,
)
from outrigger_sim.control.two_pressure import (
    RodSensorState,
    TwoPressureMonitor,
    TwoPressureSettings,
)
from outrigger_sim.hydraulics.check_open_delay import (
    CheckDelayCircuit,
    CheckDelayInputs,
    CheckOpenGate,
)
from outrigger_sim.hydraulics.rod_chamber import RodChamberLegParams, RodChamberMode
from outrigger_sim.hydraulics.rod_release import (
    RodPressureFlowLaw,
    flow_limited_rod_pressure,
    flow_limited_rod_pressure_r6,
)
from outrigger_sim.hydraulics.v5_options import CheckDelaySetting

BAR = 1e5
PERIOD_S, CHUNK_S, STEP_S = 0.1, 1e-3, 5e-4
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
V_MAX = 0.020924
RR = 3
EPS_M_S = 1e-6
VALVE_TAU_S, LAG_S = 0.1, 0.05
P_FLOOR_PA = 0.1e5 - 1.01325e5
P_EXT_PA, P_RET_PA = 2.0e5, 30.591e5
RETRACT_ANCHOR_PA = (34.818e5, 34.352e5, 31.193e5, P_RET_PA)
E_OP_M, L0_M, BETA_PA, STROKE_MAX_M = 0.3909, 0.05, 1.0e9, 0.70
E_OP_BY_LEG_M = (0.4011, 0.4011, 0.3909, 0.3909)
"""Harness operating extension per leg (front 0.4011 m, rear 0.3909 m; hydraulics review 5)."""
SEED = 20261116
OTHER_LEGS_HEAD_PA, OTHER_LEGS_ROD_PA = 60.0e5, 5.0e5
FL = 0


class LegPlant:
    """Reduced leg (module docstring); RR by default."""

    def __init__(self, start_truth_Pa: float, force_N: float, *, gate: bool, r6: bool,
                 continuous_anchor: bool, leg: int = RR) -> None:
        self.leg = leg
        self.head_area, self.annulus = float(HEAD_AREA[leg]), float(ANNULUS[leg])
        e_op = E_OP_BY_LEG_M[leg]
        k_h = BETA_PA * self.head_area / (L0_M + e_op)
        k_r = BETA_PA * self.annulus / (L0_M + STROKE_MAX_M - e_op)
        self.params = RodChamberLegParams(head_area_m2=self.head_area,
                                          annulus_area_m2=self.annulus, head_stiffness_N_m=k_h,
                                          rod_stiffness_N_m=k_r, outer_stiffness_N_m=math.inf,
                                          rod_weight_N=0.0)
        self.compliance = RodPressureFlowLaw.rod_compliance_m3_Pa(self.annulus, k_h, k_r)
        self.share = k_r / (k_h + k_r)
        self.r6, self.continuous_anchor = r6, continuous_anchor
        self.locked, self.last_dir, self.valve_m_s = True, 1.0, 0.0
        self.lock_Pa, self.lock_force_N, self.moving_Pa = start_truth_Pa, force_N, start_truth_Pa
        self.force_N = force_N
        self.last_target_Pa = math.nan
        """``p*`` of the last moving step (the J-P3c / RET share boundary)."""
        self.seed_Pa = math.nan
        """P1 retract M2 seed of the release (decision 147)."""
        self.gate = None
        if gate:
            circuit = CheckDelayCircuit(HEAD_AREA.copy(), ANNULUS.copy(), STROKE_MAX_M, L0_M, L0_M,
                                        BETA_PA, 2.0e5, V_MAX, 10.0e5)
            self.gate = CheckOpenGate(CheckDelaySetting("VN"), circuit)

    def truth_Pa(self) -> float:
        if not self.locked:
            return self.moving_Pa
        split = self.share * (self.lock_force_N - self.force_N) / self.annulus
        return max(self.lock_Pa + split, P_FLOOR_PA)

    def head_Pa(self) -> float:
        return (self.force_N + self.truth_Pa() * self.annulus) / self.head_area

    def period(self, command_m_s: float, force_end_N: float) -> None:
        force_start_N = self.force_N
        chunks = round(PERIOD_S / CHUNK_S)
        for chunk in range(chunks):
            keep = math.exp(-CHUNK_S / VALVE_TAU_S)
            mean = command_m_s + (self.valve_m_s - command_m_s) * (VALVE_TAU_S / CHUNK_S) * (
                1.0 - keep)
            self.valve_m_s = command_m_s + (self.valve_m_s - command_m_s) * keep
            speed = self._gated_speed(mean)
            for step in range(2):
                fraction = (chunk * 2 + step + 1) / (2 * chunks)
                self.force_N = force_start_N + (force_end_N - force_start_N) * fraction
                self._step(speed)

    def _gated_speed(self, mean_m_s: float) -> float:
        if self.gate is None:
            return mean_m_s
        u = np.zeros(4)
        u[self.leg] = mean_m_s
        locked = np.zeros(4, bool)
        locked[self.leg] = self.locked
        inputs = CheckDelayInputs(0.0, CHUNK_S, u, np.full(4, self.head_Pa()),
                                  np.full(4, self.truth_Pa()), locked, np.zeros(4),
                                  np.zeros(4), np.full(4, E_OP_BY_LEG_M[self.leg]))
        output = self.gate.filter(inputs)
        seed_Pa = float(output.opening_rod_pressure_Pa[self.leg])
        if math.isfinite(seed_Pa):
            self.seed_Pa = seed_Pa
        return float(output.speed_m_s[self.leg])

    def _step(self, speed_m_s: float) -> None:
        if self.locked and abs(speed_m_s) > EPS_M_S:
            self.moving_Pa = self.truth_Pa() if math.isnan(self.seed_Pa) else self.seed_Pa
            self.seed_Pa = math.nan
            self.locked = False
        if not self.locked and abs(speed_m_s) <= EPS_M_S:
            self._lock()
            return
        if self.locked:
            return
        self.last_dir = 1.0 if speed_m_s > 0.0 else -1.0
        is_retract = self.last_dir < 0.0
        mode = RodChamberMode.RET if is_retract else RodChamberMode.EXT
        target = self.params.moving_target_rod_pressure_Pa(mode, self.force_N)
        self.last_target_Pa = target
        if self.r6:
            self.moving_Pa = flow_limited_rod_pressure_r6(
                self.moving_Pa, target, speed_m_s, STEP_S, LAG_S, self.compliance,
                self.head_area, self.annulus, is_retract, self.force_N,
                self.params.p_head_back_retract_Pa)
        else:
            self.moving_Pa = flow_limited_rod_pressure(
                self.moving_Pa, target, speed_m_s, STEP_S, LAG_S, self.compliance,
                self.head_area, self.annulus, is_retract)

    def _lock(self) -> None:
        if self.continuous_anchor:
            anchor_Pa = max(self.moving_Pa, P_FLOOR_PA)
        elif self.last_dir > 0.0:
            target = self.params.moving_target_rod_pressure_Pa(RodChamberMode.EXT, self.force_N)
            excess = max(self.moving_Pa - target, 0.0)
            anchor_Pa = max(min(self.moving_Pa, P_EXT_PA + excess), P_FLOOR_PA)
        else:
            anchor_Pa = P_RET_PA
        self.locked, self.lock_Pa, self.lock_force_N = True, anchor_Pa, self.force_N


def _monitor(revision: int, leg: int = RR, bound_changes: dict | None = None,
             retract_floor_Pa: tuple | None = None) -> TwoPressureMonitor:
    bound = ExtendStartBound(revision=revision, **(bound_changes or {}))
    settings = replace(TwoPressureSettings().with_r8_period(), extend_start_rule="tracked_bound",
                       extend_start_bound=bound)
    floor = RETRACT_ANCHOR_PA if retract_floor_Pa is None else retract_floor_Pa
    monitor = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, 9414.59, PERIOD_S,
                                 settings=settings, stroke_max_m=STROKE_MAX_M,
                                 retract_lock_rod_pressure_Pa=floor)
    monitor.rod_state[leg] = RodSensorState.FALLBACK
    return monitor


def _closed_loop(plant: LegPlant, commands_m_s, forces_N, revision: int,
                 lower_N: list | None = None, *, bound_changes: dict | None = None,
                 retract_floor_Pa: tuple | None = None, head_read_error_Pa: float = 0.0,
                 reads: list | None = None, monitors: list | None = None) -> dict:
    """Run the schedule (acting command and end force per period); returns the J-P3 record
    (revision 5 keys with revision 5, the revision 4 ``breach_reads`` otherwise).
    ``lower_N`` collects ``(class, plant state, p_tr, p*, lower force)`` of the leg per read;
    ``reads`` collects ``(t, class, used bound, p_tr, true head, trace row)`` of the leg (edition
    4 cases); ``head_read_error_Pa`` is added to the leg's head reading."""
    leg = plant.leg
    monitor = _monitor(revision, leg, bound_changes, retract_floor_Pa)
    if monitors is not None:
        monitors.append(monitor)
    tolerance = 600.0 / ANNULUS
    rev5, rev4 = ExtendBoundCheckRev5(tolerance, "ideal"), ExtendBoundCheck(ANNULUS)
    for period, (command, force) in enumerate(zip(commands_m_s, forces_N, strict=True)):
        plant.period(command, force)
        head = np.full(4, OTHER_LEGS_HEAD_PA)
        rod = np.full(4, OTHER_LEGS_ROD_PA)
        head[leg], rod[leg] = plant.head_Pa() + head_read_error_Pa, plant.truth_Pa()
        commanded = np.zeros(4)
        commanded[leg] = command
        forces = monitor.read((period + 1) * PERIOD_S, head, rod, commanded, False, 2e3,
                              stroke_m=np.full(4, E_OP_BY_LEG_M[leg]))
        plant_rod = np.full(4, np.nan)
        plant_rod[leg] = plant.truth_Pa()
        target = np.full(4, np.nan)
        target[leg] = math.nan if plant.locked else plant.last_target_Pa  # 3rd edition 6.3
        locked = np.zeros(4, bool)
        locked[leg] = plant.locked
        direction = np.ones(4)
        direction[leg] = plant.last_dir
        states = plant_leg_states(locked, direction)
        if revision == EXTEND_HOLD_REVISION:
            row = monitor.extend_bound_trace_row()
            rev5.add((period + 1) * PERIOD_S, row["class"], row["used_bound_Pa"], plant_rod,
                     states, row, target)
            if lower_N is not None:
                lower_N.append((row["class"][leg], states[leg], plant.truth_Pa(),
                                plant.last_target_Pa, float(forces.lower[leg])))
            if reads is not None:
                reads.append(((period + 1) * PERIOD_S, row["class"][leg],
                              row["used_bound_Pa"][leg], plant.truth_Pa(), plant.head_Pa(),
                              row))
        else:
            rev4.add((period + 1) * PERIOD_S, monitor.extend_bound_Pa(), plant_rod,
                     extend_bound_states(locked, direction), monitor.locked_model_bound_Pa())
    return rev5.record() if revision == EXTEND_HOLD_REVISION else rev4.record()


def _judged_sum(record: dict, leg: int = RR) -> int:
    return (record["jp3a_breach_reads"][leg] + record["jp3b_breach_over_tol_reads"][leg]
            + record["jp3c_breach_reads"][leg])


NEW_PLANT = {"gate": True, "r6": True, "continuous_anchor": True}
OLD_PLANT = {"gate": False, "r6": False, "continuous_anchor": False}


LOAD_PER_ROD_BAR_N = 1.0e5 * 3.14159265e-3 / 0.2887
"""Load drop of a locked RR leg that raises its rod side by 1 bar (``A_ann / r``, 1.088 kN)."""


def _case_5():
    """⑤: the run-start lock at ``p_ext`` 2 bar, the load leaves the leg until the rod side
    holds about 39 bar, a long lock, -2 um/s one period, +2 um/s, the load leaves again at
    -70 kN/s for 0.3 s, then 4.7 mm/s."""
    loading = list(np.linspace(70e3, 30e3, 5))
    commands = [0.0] * 10 + [-2e-6, 2e-6] + [0.0] * 3 + [4.71e-3] * 6
    forces = loading + [30e3] * 7 + [23e3, 16e3, 9e3] + [9e3] * 6
    return P_EXT_PA, 70e3, commands, forces


def _case_7():
    """⑦: a 2 bar lock, then -0.2 mm/s (a hold command) for 2 s."""
    return P_EXT_PA, 20e3, [0.0] * 5 + [-0.2e-3] * 20 + [0.0] * 3, [20e3] * 28


def _case_8():
    """⑧: the load raises the locked rod side to about 50 bar, -1 mm/s for 0.5 s, then
    +4.7 mm/s."""
    drop_N = 48.0 * LOAD_PER_ROD_BAR_N
    commands = [0.0] * 6 + [-1e-3] * 5 + [4.71e-3] * 6
    forces = list(np.linspace(19e3 + drop_N, 19e3, 4)) + [19e3] * 13
    return P_EXT_PA, 19e3 + drop_N, commands, forces


@pytest.mark.parametrize("case", [_case_5, _case_7, _case_8], ids=["5", "7", "8"])
def test_t_jr_04_cases_hold_the_bound_on_the_new_plant(case) -> None:
    start_Pa, force_N, commands, forces = case()
    record = _closed_loop(LegPlant(start_Pa, force_N, **NEW_PLANT), commands, forces,
                          EXTEND_HOLD_REVISION)
    assert _judged_sum(record) == 0, {key: record[key] for key in
                                      ("jp3a_min_gap_bar", "jp3b_min_gap_bar",
                                       "jp3c_min_gap_bar", "class_reads")}


def test_t_jr_04_case_5_breaks_revision_4_on_the_gated_plant() -> None:
    """Counterexample ⑥ (spec 2.7, case replay C): revision 4 without the tracker gate on the
    P1 plant breaches at the first read after the release (the moving estimate starts
    relieving before the line opened the checks); revision 5 does not (the case test above).

    The 436.8 breach itself (old plant, LC relock steps) needs the full harness plant; the
    reduced old plant here has no LC and no ``G_r,lock`` residue, so it is the stored case
    replay A that reproduces it (``run_v5`` batch ``j9_cases``)."""
    start_Pa, force_N, commands, forces = _case_5()
    record = _closed_loop(LegPlant(start_Pa, force_N, **NEW_PLANT), commands, forces, 4)
    assert record["breach_reads"][RR] >= 1
    assert record["first_breach_t_s"][RR] == pytest.approx(1.6)  # the 4.71 mm/s period


AIRBORNE_FORCE_N = -1.0e3
"""Case ⑩ / T-JR-16: an airborne front leg (``F`` about ``-m_rod g``)."""
FILL_EXCESS_LIMIT_BAR = 5.6 + 0.5
"""T-JR-16: ``p*_ret - retract model`` by hand (+5.6 bar) plus the 0.5 bar allowance."""
FILL_LOWER_LIMIT_N = 1.2e3
"""T-JR-16: the fallback lower bound of the fill reads stays below 1.2 kN (< F_min)."""


def test_t_jr_04_case_10_and_t_jr_16_airborne_front_retract_is_the_fill_share() -> None:
    """⑩ / T-JR-16 (3rd edition 5.2, 5.5): an airborne front leg locked after an extension at
    the P2 anchor 5 bar, then a retraction at v_max on the P1 .. P3 plant: the carry_ret reads
    of the still locked plant (line filling) are trapped (``jp3c_reads``, no breach); the moving
    ones at or below the plant's last target go to ``jp3c_fill`` (excess <= 6.1 bar, lower
    bound <= 1.2 kN)."""
    commands = [0.0] * 5 + [-V_MAX] * 10
    forces = [AIRBORNE_FORCE_N] * 15
    plant = LegPlant(5.0e5, AIRBORNE_FORCE_N, leg=FL, **NEW_PLANT)
    reads = []
    record = _closed_loop(plant, commands, forces, EXTEND_HOLD_REVISION, reads)
    assert record["jp3c_breach_reads"][FL] == 0
    assert _judged_sum(record, FL) == 0
    locked_carry = [row for row in reads if row[0] == "carry_ret" and row[1].startswith("locked")]
    # the airborne line fills within the first period here (retract need at p_h 0.7 bar), so
    # a locked carry_ret read at a period end may not occur; when it does it is trapped
    assert record["jp3c_reads"][FL] >= len(locked_carry)
    fill = [row for row in reads if row[0] == "carry_ret" and row[1].startswith("moving")
            and row[2] <= row[3]]
    assert record["jp3c_fill_reads"][FL] == len(fill) > 0
    excess = record["jp3c_fill_max_excess_bar"][FL]
    assert excess is not None and excess <= FILL_EXCESS_LIMIT_BAR
    assert all(row[4] <= FILL_LOWER_LIMIT_N for row in fill)


LOADED_FORCE_N = 25.0e3
"""T-JR-17 ③: a loaded leg, where the closed form ``phi p_bA - F / A_ann`` is far off."""


def test_t_jr_17_loaded_leg_fill_reads_stay_in_the_fill_share() -> None:
    """3rd edition T-JR-17 ③: a loaded RR leg (25 kN) locked at 2 bar, then a v_max retraction:
    the moving carry_ret reads that fill towards the plant target are ``jp3c_fill`` (they do
    not leak into the judged set), and the judged keys stay 0."""
    commands = [0.0] * 4 + [-V_MAX] * 10
    forces = [LOADED_FORCE_N] * 14
    plant = LegPlant(P_EXT_PA, LOADED_FORCE_N, **NEW_PLANT)
    reads = []
    record = _closed_loop(plant, commands, forces, EXTEND_HOLD_REVISION, reads)
    moving_fill = [row for row in reads if row[0] == "carry_ret"
                   and row[1].startswith("moving") and row[2] <= row[3]]
    assert record["jp3c_fill_reads"][RR] == len(moving_fill)
    assert _judged_sum(record) == 0


def _random_schedule(rng: np.random.Generator):
    """30 periods after a run-start lock (2 .. 6 lock periods with the load moving)."""
    commands, forces = [], []
    force = rng.uniform(5e3, 60e3)
    for _ in range(int(rng.integers(2, 7))):
        force = float(np.clip(force + rng.uniform(-8e3, 8e3), 2e3, 80e3))
        commands.append(0.0)
        forces.append(force)
    while len(commands) < 30:
        kind = rng.integers(4)
        level = (0.0 if kind == 0 else rng.uniform(0.0005, 0.01) if kind == 1
                 else rng.uniform(0.012, 0.25))
        sign = rng.choice((-1.0, 1.0))
        for _ in range(int(rng.integers(1, 6))):
            force = float(np.clip(force + rng.uniform(-8e3, 8e3), 2e3, 80e3))
            commands.append(sign * level * V_MAX)
            forces.append(force)
    return commands[:30], forces[:30]


def test_t_jr_04_random_schedules_hold_the_bound_on_the_new_plant() -> None:
    """Seeded sweep (20261116): 150 schedules of zero, micro and large commands with direction
    changes and a moving load; revision 5 on the P1 .. P3 plant has no judged breach."""
    rng = np.random.default_rng(SEED)
    failures = []
    for sequence in range(150):
        commands, forces = _random_schedule(rng)
        record = _closed_loop(LegPlant(P_EXT_PA, forces[0], **NEW_PLANT), commands, forces,
                              EXTEND_HOLD_REVISION)
        if _judged_sum(record):
            failures.append((sequence, record["jp3a_min_gap_bar"][RR],
                             record["jp3b_min_gap_bar"][RR], record["jp3c_min_gap_bar"][RR]))
    assert failures == []


# --- edition 4 cases (jp3_remedy_spec.md 5.2, 5.7, 13.3; J4a-12) -------------------------------

BOTH_TEST_RULES = {"carry_end_rule": "fresh_stretch", "retract_start_rule": "model_only"}
"""Edition 4a 13.3: the counterexample arm turns both test-only rules on (edition 3 rev 5)."""
LOW_RETRACT_FLOOR_PA = (5.0e5,) * 4
"""``p_ret`` below the retract model (the ⑪b premise "p_ret floor <= retract model")."""
HEAD_FALL_PA_S = 30.0e5


def _allow_test_rules(monkeypatch) -> None:
    monkeypatch.setattr(esb, "ALLOW_FRESH_STRETCH_FOR_TEST", True)
    monkeypatch.setattr(esb, "ALLOW_MODEL_ONLY_RETRACT_START_FOR_TEST", True)


def _force_step_for_head_rate_N(plant: LegPlant, head_rate_Pa_s: float) -> float:
    """Force change per period of a locked leg whose head moves at ``head_rate_Pa_s``."""
    return head_rate_Pa_s * PERIOD_S * plant.head_area / (1.0 - plant.share)


def _case_11(plant: LegPlant):
    """⑪: an extension lock (head 73 bar, p_tr 31 bar), the load leaving the locked leg (head
    -30 bar/s) through -1.4 u_hold for 2 periods (gate need not reached) and -0.99 u_hold for 3
    periods (hold)."""
    hold_m_s = 0.01 * V_MAX
    commands = [0.0] * 3 + [-1.4 * hold_m_s] * 2 + [-0.99 * hold_m_s] * 3
    step_N = _force_step_for_head_rate_N(plant, -HEAD_FALL_PA_S)
    forces = [plant.force_N + step_N * (k + 1) for k in range(len(commands))]
    return commands, forces


def _plant_11() -> LegPlant:
    force_N = 73.0e5 * HEAD_AREA[RR] - 31.0e5 * ANNULUS[RR]
    return LegPlant(31.0e5, force_N, **NEW_PLANT)


def test_t_jr_04_case_11_r5_6_keeps_the_hold_above_the_locked_truth() -> None:
    """⑪ (edition 4): R5-6 covers the hold reads (J-P3b 0) and the stretch inherits."""
    plant = _plant_11()
    commands, forces = _case_11(plant)
    reads, monitors = [], []
    record = _closed_loop(plant, commands, forces, EXTEND_HOLD_REVISION, reads=reads,
                          monitors=monitors)
    assert plant.locked  # P1: the micro commands never left the lock
    hold_gaps = [used - truth for _, cls, used, truth, _, _ in reads if cls == "hold"]
    assert len(hold_gaps) == 3 and min(hold_gaps) >= 0.0
    assert record["jp3b_breach_over_tol_reads"][RR] == 0
    assert monitors[0]._lock_stretches[RR].inherited_candidates >= 1


def test_t_jr_04_case_11_counterexample_arm_needs_both_test_rules(monkeypatch) -> None:
    """⑪ edition 4a 13.3: with ``fresh_stretch`` and ``model_only`` the first hold read's ④ is
    the retract model and ``p_tr - ④ > 0.6 kN / A_ann`` (counterexample, record). The
    ``fresh_stretch``-only arm is a record (13.3: not judged); in this unit case the load keeps
    leaving the leg through the hold, so its ``p_hat + delta_m`` (raised to ④c in the carry)
    falls behind the truth too: 1 read over the tolerance (see the edition 4a report)."""
    _allow_test_rules(monkeypatch)
    plant = _plant_11()
    commands, forces = _case_11(plant)
    reads = []
    record = _closed_loop(plant, commands, forces, EXTEND_HOLD_REVISION,
                          bound_changes=BOTH_TEST_RULES, reads=reads)
    _, _, used, truth, head, row = next(read for read in reads if read[1] == "hold")
    assert row["model_bound_source"][RR] in ("pilot_model", "previous_moving")
    assert used == pytest.approx(13.0e5 + head / 3.0, abs=2e5)
    assert truth - used > 600.0 / ANNULUS[RR]
    assert record["jp3b_breach_over_tol_reads"][RR] >= 1


class HookedLegPlant(LegPlant):
    """⑪b test hook (spec 5.2): the leg stays locked until ``release_at_s`` (the tracker gate
    opening sub-step, the worst case the comparison principle allows), then the base law."""

    def __init__(self, *args, release_at_s: float = math.inf, compliance: float | None = None,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.release_at_s = release_at_s
        self.chunk_start_s = 0.0
        if compliance is not None:
            self.compliance = compliance

    def _gated_speed(self, mean_m_s: float) -> float:
        start_s = self.chunk_start_s
        self.chunk_start_s += CHUNK_S
        return 0.0 if start_s < self.release_at_s - 1e-12 else mean_m_s


RETRACT_HOOK_COMPLIANCE_M3_PA = 1.586e-12
"""``C_r`` of the P4-6 table (review ``cr09``)."""


def _locked_by_load_drop(leg: int, truth_Pa: float, force_N: float, periods: int = 10):
    """Commands and forces of a lock from 2 bar whose load leaves until the locked truth is
    ``truth_Pa`` at ``force_N`` (④ follows with ``R_ub``: the premise A1 ④ >= p_tr)."""
    probe = LegPlant(P_EXT_PA, force_N, gate=False, r6=True, continuous_anchor=True, leg=leg)
    start_N = force_N + (truth_Pa - P_EXT_PA) * probe.annulus / probe.share
    forces = list(np.linspace(start_N, force_N, periods)) + [force_N] * 3
    return start_N, [0.0] * len(forces), forces


CARRY_PERIODS_MAX = 200


def _hooked_run(start_N: float, commands: list, forces: list, release_at_s: float,
                rules: dict | None) -> tuple[list, TwoPressureMonitor]:
    plant = HookedLegPlant(P_EXT_PA, start_N, gate=False, r6=True, continuous_anchor=True,
                           release_at_s=release_at_s, compliance=RETRACT_HOOK_COMPLIANCE_M3_PA)
    monitors, reads = [], []
    _closed_loop(plant, commands, forces, EXTEND_HOLD_REVISION, bound_changes=rules,
                 retract_floor_Pa=LOW_RETRACT_FLOOR_PA, reads=reads, monitors=monitors)
    return reads, monitors[0]


def _gate_open_s(reads: list, monitor: TwoPressureMonitor) -> float:
    carry_start_s = next(t for t, cls, *_ in reads if cls == "carry_ret") - PERIOD_S
    return carry_start_s + monitor._extend_tracker.gate_open_substeps[RR][0] * CHUNK_S


def _run_11b(speed_m_s, after_gate_s, force_N, truth_Pa, rules) -> tuple[list, float]:
    """Pass 1 finds the tracker gate opening with the plant held locked; pass 2 releases the
    plant at that sub-step, retracts ``after_gate_s`` more, then 0 for 1 s. Returns the reads
    after the retraction and the gate opening time [s]."""
    start_N, commands, forces = _locked_by_load_drop(RR, truth_Pa, force_N)
    probe_commands = commands + [-speed_m_s] * CARRY_PERIODS_MAX
    probe_forces = forces + [force_N] * CARRY_PERIODS_MAX
    reads, monitor = _hooked_run(start_N, probe_commands, probe_forces, math.inf, rules)
    open_s = _gate_open_s(reads, monitor)
    open_read = next(k for k, read in enumerate(reads) if read[5]["gate_open"][RR])
    end_read = open_read + 1 + round(after_gate_s / PERIOD_S)
    run_commands = probe_commands[:end_read] + [0.0] * 10
    run_forces = probe_forces[:end_read] + [force_N] * 10
    reads, monitor = _hooked_run(start_N, run_commands, run_forces, open_s, rules)
    assert _gate_open_s(reads, monitor) == pytest.approx(open_s)  # the release keeps it
    return reads[end_read:], open_s


P4_6_TABLE = [
    # F kN, speed m/s, time after the gate s, HOLD start p_tr bar, edition 3 gap bar, lower gap
    (14.8e3, 0.3e-3, 0.1, 58.52, -33.88, 1.88),
    (14.8e3, 0.3e-3, 0.2, 57.15, -32.66, 3.25),
    (14.8e3, 0.3e-3, 0.5, 53.13, -29.08, 7.27),
    (14.8e3, 1.0e-3, 0.1, 55.35, -31.06, 5.05),
    (14.8e3, 1.0e-3, 0.2, 50.95, -27.14, 9.45),
    (5.0e3, 0.3e-3, 0.2, 57.92, -36.78, 2.58),
]
"""The sealed P4-6 table (edition 4 5.7). Addendum 4a-2 1.2 / 1.4: its numbers are a
prediction premise error (not "적중"); the tests below record them and hard-assert only the
soundness part."""
P4_6_TRUTH_PA = {14.8e3: 59.9e5, 5.0e3: 60.0e5}
P4_6_OPENING_ROWS = [row for row in P4_6_TABLE if row[1] >= 1.0e-3]
"""Rows whose retract speed opens the tracker gate."""
P4_6_SLOW_ROWS = [row for row in P4_6_TABLE if row[1] < 1.0e-3]
"""Rows whose gate does not open within 20 s (4a-2 1.2: no exposure, recorded)."""
P4_6_COLUMNS = ("force_N", "speed_m_s", "after_s", "start_bar", "old_gap_bar", "lower_gap_bar")
MODEL_ONLY_GAP_LIMIT_BAR = -20.0
RECORD_DIR_ENV = "JP3_RECORD_DIR"
"""Addendum 4a-2 1.4 record tests: a folder for their JSON records (unset = pytest's tmp_path
only); every record also goes to the JUnit XML through ``record_property``."""


def _write_record(name: str, payload: dict, record_property, tmp_path) -> None:
    """A record test's values (4a-2 1.4: written, not asserted)."""
    text = json.dumps(payload, indent=1, default=float)
    record_property(name, text)
    (tmp_path / f"{name}.json").write_text(text, encoding="utf-8")
    folder = os.environ.get(RECORD_DIR_ENV)
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        (Path(folder) / f"{name}.json").write_text(text, encoding="utf-8")


def _p4_6_opening_values(force_N, speed_m_s, after_s) -> dict:
    """One 1 mm/s row: the record values of 4a-2 1.4 and the inputs of its soundness asserts."""
    truth_Pa = P4_6_TRUTH_PA[force_N]
    after, open_s = _run_11b(speed_m_s, after_s, force_N, truth_Pa, None)
    old_after, _ = _run_11b(speed_m_s, after_s, force_N, truth_Pa,
                            {"retract_start_rule": "model_only"})
    gaps = [(used - truth) / BAR for _, cls, used, truth, _, _ in after
            if cls in ("lock", "hold")]
    return {"hold_start_p_tr_bar": after[0][3] / BAR,
            "model_only_gap_bar": (old_after[0][2] - old_after[0][3]) / BAR,
            "r5_7_gap_bar": min(gaps) if gaps else None,
            "first_read_source": after[0][5]["model_bound_source"][RR],
            "gate_opened": True, "gate_open_s": open_s}


@pytest.mark.parametrize(P4_6_COLUMNS, P4_6_OPENING_ROWS)
def test_t_jr_04_case_11b_p4_6_soundness_of_the_opening_rows(
        monkeypatch, record_property, tmp_path, force_N, speed_m_s, after_s, start_bar,
        old_gap_bar, lower_gap_bar) -> None:
    """⑪b (P4-6, 1 mm/s rows; addendum 4a-2 1.4): the plant leaves its lock at the gate
    opening sub-step, retracts, then stops. Recorded: HOLD start ``p_tr``, the ``model_only``
    gap, the R5-7 gap, the gate opening. Hard (the soundness part): R5-7 gap >= 0 and >= the
    table's lower gap, the first read's source ``retract_tracker``, ``model_only`` <= -20 bar."""
    _allow_test_rules(monkeypatch)
    values = _p4_6_opening_values(force_N, speed_m_s, after_s)
    row = dict(zip(P4_6_COLUMNS, (force_N, speed_m_s, after_s, start_bar, old_gap_bar,
                                  lower_gap_bar), strict=True))
    _write_record(f"P4-6_F{force_N / 1e3:g}kN_{speed_m_s * 1e3:g}mms_{after_s:g}s",
                  {"table_row": row, **values}, record_property, tmp_path)
    assert values["r5_7_gap_bar"] is not None
    assert values["r5_7_gap_bar"] >= 0.0
    assert values["r5_7_gap_bar"] >= lower_gap_bar - 1e-6
    assert values["first_read_source"] == "retract_tracker"
    assert values["model_only_gap_bar"] <= MODEL_ONLY_GAP_LIMIT_BAR


@pytest.mark.parametrize(P4_6_COLUMNS, P4_6_SLOW_ROWS)
def test_t_jr_04_case_11b_p4_6_slow_rows_have_no_exposure(
        record_property, tmp_path, force_N, speed_m_s, after_s, start_bar, old_gap_bar,
        lower_gap_bar) -> None:
    """The 0.3 mm/s rows of P4-6 (addendum 4a-2 1.2 / 1.4): ``kappa_x`` 0.8 x 0.3 mm/s =
    1.15 % ``v_max`` lies below the VN drain cut-off (``c_v`` 2 %), so the tracker gate never
    opens within 20 s and the hooked plant never leaves its lock. Hard: no gate opening and the
    used bound (④ or ④c) >= ``p_tr`` at every read (no ⑪b exposure). The row's RET time after
    the gate does not exist, so the run is the same for its ``after_s``."""
    start_N, commands, forces = _locked_by_load_drop(RR, P4_6_TRUTH_PA[force_N], force_N)
    commands += [-speed_m_s] * CARRY_PERIODS_MAX
    forces += [force_N] * CARRY_PERIODS_MAX
    reads, monitor = _hooked_run(start_N, commands, forces, math.inf, None)
    gaps = [(used - truth) / BAR for _, _, used, truth, _, _ in reads if math.isfinite(used)]
    row = dict(zip(P4_6_COLUMNS, (force_N, speed_m_s, after_s, start_bar, old_gap_bar,
                                  lower_gap_bar), strict=True))
    _write_record(f"P4-6_F{force_N / 1e3:g}kN_{speed_m_s * 1e3:g}mms_{after_s:g}s",
                  {"table_row": row, "gate_opened": False, "reads": len(reads),
                   "unbounded_reads": len(reads) - len(gaps),
                   "min_used_minus_p_tr_bar": min(gaps) if gaps else None},
                  record_property, tmp_path)
    assert monitor._extend_tracker.gate_open_substeps[RR] == []
    assert not any(read[5]["gate_open"][RR] for read in reads)
    assert len(gaps) == len(reads) and min(gaps) >= 0.0


HR11_EXCESS_BAR = 27.4
HR11_READ_ERROR_PA = -4.62e5
HR11_MARGIN_BAR = 4.30


def _run_11b_p1(n_ret: int, rules: dict | None, band_N: float):
    """⑪b-P1 (hydraulics review 11.1 model): FL, F 2 kN, locked p_r0 60 bar, P1 + P3 plant,
    -0.5 mm/s for ``n_ret`` periods then 0; head reading = truth - 4.62 bar."""
    force_N, truth_Pa = 2.0e3, 60.0e5
    start_N, commands, forces = _locked_by_load_drop(FL, truth_Pa, force_N)
    commands += [-0.5e-3] * n_ret + [0.0] * 8
    forces += [force_N] * (n_ret + 8)
    plant = BandLegPlant(P_EXT_PA, start_N, leg=FL, band_N=band_N, **NEW_PLANT)
    monitors, reads = [], []
    _closed_loop(plant, commands, forces, EXTEND_HOLD_REVISION, bound_changes=rules,
                 retract_floor_Pa=LOW_RETRACT_FLOOR_PA, head_read_error_Pa=HR11_READ_ERROR_PA,
                 reads=reads, monitors=monitors)
    lead = len(commands) - n_ret - 8
    return reads, lead, monitors[0]


class BandLegPlant(LegPlant):
    """The P1 plant with a seal band ``F_band`` in the gate inputs (⑪b-P1 band variants)."""

    def __init__(self, *args, band_N: float = 0.0, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.band_N = band_N

    def _gated_speed(self, mean_m_s: float) -> float:
        u = np.zeros(4)
        u[self.leg] = mean_m_s
        locked = np.zeros(4, bool)
        locked[self.leg] = self.locked
        band = np.zeros(4)
        band[self.leg] = self.band_N
        inputs = CheckDelayInputs(0.0, CHUNK_S, u, np.full(4, self.head_Pa()),
                                  np.full(4, self.truth_Pa()), locked, np.zeros(4), band,
                                  np.full(4, E_OP_BY_LEG_M[self.leg]))
        output = self.gate.filter(inputs)
        seed_Pa = float(output.opening_rod_pressure_Pa[self.leg])
        if math.isfinite(seed_Pa):
            self.seed_Pa = seed_Pa
        return float(output.speed_m_s[self.leg])


def _shortest_ret(band_N: float) -> tuple[int, list, int]:
    """The smallest N whose tracker gate opens inside the retraction (review q1)."""
    reads, lead, _ = _run_11b_p1(80, None, band_N)
    open_read = next(k for k, read in enumerate(reads[lead:]) if read[5]["gate_open"][FL])
    return open_read + 1, reads, lead


def _first_excess_bar(after: list) -> float:
    """The plant's first post-retraction excess over the retract model ``13 + p_h / 3``
    (hydraulics q1 definition, true head)."""
    _, _, _, truth, head, _ = after[0]
    return (truth - (13.0e5 + head / 3.0)) / BAR


HR11_N_RET = 14
"""N of the review model q1 at this point (its gate keeps ``p_h0 - 4.62 bar + e_h``; addendum
4a-2 6: the P4-7 basis)."""
MONITOR_N_RET = 12
"""N with the monitor's gate as written in addendum 4a-2 1.1 (its ``p_h_ub`` follows the
head reading, which falls once the P1 plant has left its lock); recorded, never asserted: the
monitor's own shortest N is recorded beside it."""
P4_7_BANDS_N = (0.0, 4.0e3)
P4_7_N_VALUES = (MONITOR_N_RET, HR11_N_RET)


def _p4_7_values(n_ret: int, band_N: float) -> dict:
    """``model_only`` first-read excess and the R5-7 margin of one N and band."""
    reads, lead, _ = _run_11b_p1(n_ret, {"retract_start_rule": "model_only"}, band_N)
    model_only_after = reads[lead + n_ret:]
    reads, lead, _ = _run_11b_p1(n_ret, None, band_N)
    after = reads[lead + n_ret:]
    margins = [(used - truth) / BAR for _, cls, used, truth, _, _ in after
               if cls in ("lock", "hold")]
    first_used, first_truth = model_only_after[0][2], model_only_after[0][3]
    return {"model_only_first_excess_bar": _first_excess_bar(model_only_after),
            "model_only_first_p_tr_minus_bound_bar": (first_truth - first_used) / BAR,
            "r5_7_min_margin_bar": min(margins) if margins else None}


def test_t_jr_04_case_11b_p1_p4_7(monkeypatch, record_property, tmp_path) -> None:
    """⑪b-P1 (P4-7; addendum 4a-2 1.2, 1.4, 6). Recorded: per N (12, 14) and band (0, 4 kN)
    the ``model_only`` first HOLD excess and the R5-7 margin, and the monitor's own shortest N
    per band. Hard: at q1's N = 14 the larger excess of the two bands is +27.4 +-0.5 bar
    (regression against the review model), and the R5-7 margin >= +4.30 bar at N = 12 and 14
    on both bands."""
    _allow_test_rules(monkeypatch)
    values = {f"N{n_ret}_band{band_N / 1e3:g}kN": _p4_7_values(n_ret, band_N)
              for n_ret in P4_7_N_VALUES for band_N in P4_7_BANDS_N}
    shortest = {f"band{band_N / 1e3:g}kN": _shortest_ret(band_N)[0] for band_N in P4_7_BANDS_N}
    _write_record("P4-7", {"values": values, "monitor_shortest_N": shortest},
                  record_property, tmp_path)
    excess_at_14 = [values[f"N{HR11_N_RET}_band{band_N / 1e3:g}kN"]
                    ["model_only_first_excess_bar"] for band_N in P4_7_BANDS_N]
    assert max(excess_at_14) == pytest.approx(HR11_EXCESS_BAR, abs=0.5), excess_at_14
    for name, row in values.items():
        assert row["r5_7_min_margin_bar"] is not None, name
        assert row["r5_7_min_margin_bar"] >= HR11_MARGIN_BAR, name
