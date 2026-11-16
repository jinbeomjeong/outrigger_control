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

import math
from dataclasses import replace

import numpy as np
import pytest

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


def _monitor(revision: int, leg: int = RR) -> TwoPressureMonitor:
    bound = ExtendStartBound(revision=revision)
    settings = replace(TwoPressureSettings().with_r8_period(), extend_start_rule="tracked_bound",
                       extend_start_bound=bound)
    monitor = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, 9414.59, PERIOD_S,
                                 settings=settings, stroke_max_m=STROKE_MAX_M,
                                 retract_lock_rod_pressure_Pa=RETRACT_ANCHOR_PA)
    monitor.rod_state[leg] = RodSensorState.FALLBACK
    return monitor


def _closed_loop(plant: LegPlant, commands_m_s, forces_N, revision: int,
                 lower_N: list | None = None) -> dict:
    """Run the schedule (acting command and end force per period); returns the J-P3 record
    (revision 5 keys with revision 5, the revision 4 ``breach_reads`` otherwise).
    ``lower_N`` collects ``(class, plant state, p_tr, p*, lower force)`` of the leg per read."""
    leg = plant.leg
    monitor = _monitor(revision, leg)
    tolerance = 600.0 / ANNULUS
    rev5, rev4 = ExtendBoundCheckRev5(tolerance, "ideal"), ExtendBoundCheck(ANNULUS)
    for period, (command, force) in enumerate(zip(commands_m_s, forces_N, strict=True)):
        plant.period(command, force)
        head = np.full(4, OTHER_LEGS_HEAD_PA)
        rod = np.full(4, OTHER_LEGS_ROD_PA)
        head[leg], rod[leg] = plant.head_Pa(), plant.truth_Pa()
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
