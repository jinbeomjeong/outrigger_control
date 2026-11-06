"""v5 options on the real ``L2bForceActuator`` hook (spec ``v5_hydraulic_impl_spec.md`` 3.1).

Fake motors stand in for Chrono: the leg positions come from a massless-rod 3-DOF body or a fixed
body, as the review wrapper ``04_scripts/04_hydraulic/pressure_review/m2_check.py`` did. The law,
speed reference and the hook are the project classes.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.actuation import SpeedReference  # noqa: E402
from outrigger_sim.chrono.l2b_actuator import L2bForceActuator  # noqa: E402
from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide  # noqa: E402
from outrigger_sim.hydraulics.seal_friction import SealFriction  # noqa: E402
from outrigger_sim.params import load_params as load_yaml_params  # noqa: E402

pytestmark = pytest.mark.chrono

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BAR = 1.0e5
DT_S = 1.0e-4
VALVE_TAU_S = 0.1
RELEASE_TAU_S = 0.05
LOCK_EPS_M_S = 1.0e-6
FLOOR_ABS_PA = 1.0e4
STROKE_RANGE_M = (0.0, 0.9)
C_LOCK_N_S_M = np.array([34403.5, 34403.5, 30348.5, 30348.5])
C_MOVE_N_S_M = np.array([100206.0, 100206.0, 86949.0, 86949.0])
END_SAMPLES = 200
"""The review wrapper takes the end force over the last 200 samples."""
FRONT_LEFT = 0
ROD_PRESSURE_RETRACT_PA = 34.818 * BAR
ROD_PRESSURE_EXTEND_PA = 2.0 * BAR
SEAL_FRICTION_N = 4.0e3
ALL_UP = (1.0, 1.0, 1.0, 1.0)
FRONT_LEFT_QUARTER = (0.25, 0.0, 0.0, 0.0)
ALL_ZERO = (0.0, 0.0, 0.0, 0.0)


def _load_coupled_params() -> ModuleType:
    """The review's parameter module by path: its bare name ``params`` is taken in Chrono-dev."""
    path = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled" / "params.py"
    spec = importlib.util.spec_from_file_location("v5_coupled_params", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


COUPLED = _load_coupled_params()
P = COUPLED.load_params()


@dataclass
class _Case:
    """One review case: command fractions of v_max from their start times on."""

    t_end_s: float
    commands: list[tuple[float, tuple[float, ...]]]
    rod_pressure_Pa: np.ndarray = field(default_factory=lambda: np.full(4, ROD_PRESSURE_EXTEND_PA))
    is_body_fixed: bool = False
    seal_friction_N: float = 0.0


def _release_case(rod_pressure_FL_Pa: float, *, is_body_fixed: bool,
                  friction_N: float = 0.0) -> _Case:
    """C2 / C3 of the review: FL extends 0.25 v_max for 0.5 s from a lock, the others stay."""
    pressure = np.full(4, ROD_PRESSURE_EXTEND_PA)
    pressure[FRONT_LEFT] = rod_pressure_FL_Pa
    commands = [(1.5, FRONT_LEFT_QUARTER), (2.0, ALL_ZERO)]
    return _Case(3.0, commands, pressure, is_body_fixed, friction_N)


class _FakeMotor:
    def __init__(self, position_m: float) -> None:
        self.position_m = position_m
        self.speed_m_s = 0.0

    def GetMotorPos(self) -> float:
        return self.position_m

    def GetMotorPosDt(self) -> float:
        return self.speed_m_s


class _FakeForceFunction:
    def SetConstant(self, value: float) -> None:
        self.value = value


def _make_actuator(case: _Case, **actuator_options) -> tuple[L2bForceActuator, list[_FakeMotor]]:
    start_force_N = COUPLED.static_loads(P)
    has_friction = case.seal_friction_N > 0.0
    outer_stiffness = np.full(4, np.inf) if has_friction else P.k_st
    law = L2bRodSide(head_area_m2=P.A_h, annulus_area_m2=P.A_r, k_out_N_m=outer_stiffness,
                     bulk_modulus_Pa=P.beta, head_dead_length_m=P.L0h,
                     rod_dead_length_m=[P.L0r] * 4, stroke_m=P.stroke,
                     p_r0_after_extend_Pa=case.rod_pressure_Pa,
                     p_r0_after_retract_Pa=case.rod_pressure_Pa, p_floor_abs_Pa=FLOOR_ABS_PA,
                     release_tau_s=RELEASE_TAU_S, lock_eps_m_s=LOCK_EPS_M_S)
    series = np.array([1.0 / (1.0 / (P.beta * P.A_h[i] / (P.L0h + P.s0[i])) + 1.0 / P.k_st[i])
                       for i in range(4)])
    reference = SpeedReference(P.s0 + start_force_N / series, [STROKE_RANGE_M] * 4,
                               max_speed_m_s=P.v_max, ramp_s=0.1)
    reference.configure_valve(tau_s=VALVE_TAU_S)
    motors = [_FakeMotor(float(position)) for position in P.s0]
    friction = None
    if has_friction:
        friction = SealFriction(np.full(4, case.seal_friction_N), P.k_st)
    # k_frame and k_concrete are lumped in k_rod: k_out of the actuator equals P.k_st
    actuator = L2bForceActuator(
        motors, [_FakeForceFunction() for _ in range(4)], reference, bulk_modulus_Pa=P.beta,
        dead_length_m=P.L0h, frame_stiffness_N_m=1.0e15, head_area_m2=P.A_h, k_rod_N_m=P.k_st,
        k_concrete_N_m=None, damping_locked_N_s_m=C_LOCK_N_S_M, damping_moving_N_s_m=C_MOVE_N_S_M,
        rod_side=law, seal_friction=friction, **actuator_options)
    actuator.set_initial_force(start_force_N)
    actuator.on_step_end()
    return actuator, motors


@dataclass
class _Run:
    """Leg forces per step and the state a continuation needs."""

    force_N: np.ndarray
    heave_roll_pitch: np.ndarray
    rate: np.ndarray


def _command_at(case: _Case, t_s: float) -> np.ndarray:
    command = np.zeros(4)
    for start_s, fractions in case.commands:
        if t_s >= start_s:
            command = np.array(fractions)
    return command * P.v_max


def _step_body(case, start_force_N, force_N, coordinates, rates) -> None:
    if case.is_body_fixed:
        return
    delta_N = force_N - start_force_N
    load = np.array([delta_N.sum(), (P.yp * delta_N).sum(), (-P.xp * delta_N).sum()])
    rates += load / np.array([P.mass, P.I_roll, P.I_pitch]) * DT_S
    coordinates += rates * DT_S


def _run(case: _Case, actuator: L2bForceActuator, motors: list[_FakeMotor], *, first_step: int = 0,
         last_step: int | None = None, start: tuple[np.ndarray, np.ndarray] | None = None) -> _Run:
    start_force_N = COUPLED.static_loads(P)
    last = round(case.t_end_s / DT_S) + 1 if last_step is None else last_step
    coordinates, rates = (np.zeros(3), np.zeros(3)) if start is None else start
    forces = np.empty((last - first_step, 4))
    for row, k in enumerate(range(first_step, last)):
        t_s = k * DT_S
        heave_rate = rates[0] + P.yp * rates[1] - P.xp * rates[2]
        extension = P.s0 + coordinates[0] + P.yp * coordinates[1] - P.xp * coordinates[2]
        for i, motor in enumerate(motors):
            motor.position_m, motor.speed_m_s = float(extension[i]), float(heave_rate[i])
        actuator.set_command(_command_at(case, t_s))
        actuator.hook(t_s, DT_S)
        forces[row] = actuator.force_N
        _step_body(case, start_force_N, forces[row], coordinates, rates)
        actuator.on_step_end()
    return _Run(forces, coordinates, rates)


def _end_force_N(case: _Case, *, with_m2: bool) -> np.ndarray:
    actuator, motors = _make_actuator(case)
    if with_m2:
        actuator.configure_rod_release()
    run = _run(case, actuator, motors)
    return run.force_N[-END_SAMPLES:].mean(axis=0)


def _front_left_pair(*, with_m2: bool, is_body_fixed: bool, friction_N: float = 0.0) -> float:
    """End force of FL, rod 34.818 bar minus rod 2 bar at the release [kN]."""
    high = _end_force_N(_release_case(ROD_PRESSURE_RETRACT_PA, is_body_fixed=is_body_fixed,
                                      friction_N=friction_N), with_m2=with_m2)
    low = _end_force_N(_release_case(ROD_PRESSURE_EXTEND_PA, is_body_fixed=is_body_fixed,
                                     friction_N=friction_N), with_m2=with_m2)
    return float(high[FRONT_LEFT] - low[FRONT_LEFT]) / 1e3


def test_m2_1_body_fixed_pair_is_the_hand_value_and_zero_without_the_option() -> None:
    """Spec M2-1: 10.89 +- 0.3 kN (hand 10.893, numpy 10.879, wrapper with revision 3 10.702)."""
    assert _front_left_pair(with_m2=True, is_body_fixed=True) == pytest.approx(10.89, abs=0.3)
    assert _front_left_pair(with_m2=False, is_body_fixed=True) == 0.0


def test_m2_1_equals_the_stored_wrapper_value() -> None:
    """The hook reproduces the 3-DOF review wrapper with the revision 3 law (hydraulics-expert
    ``law.json`` 2026-11-06, ``pa``: 10.702 kN end difference; the plain lag gave 10.700)."""
    assert _front_left_pair(with_m2=True, is_body_fixed=True) == pytest.approx(10.702, abs=0.001)


def test_m2_2_free_body_pair_of_front_left() -> None:
    """Spec M2-2: 4.13 .. 4.25 +- 0.5 kN (Hopsan 4.13, numpy 4.20). With revision 3 the value
    at 3.0 s is 4.316 kN (wrapper ``pa``); this mean of the last 200 steps is 4.224 kN."""
    difference_kN = _front_left_pair(with_m2=True, is_body_fixed=False)
    assert 4.13 - 0.5 <= difference_kN <= 4.25 + 0.5


def test_m2_3_four_legs_stop_changes_the_end_force_by_almost_nothing() -> None:
    """Spec M2-3: case A, end force with and without M2 within 0.05 kN."""
    case = _Case(4.0, [(0.0, ALL_UP), (2.0, ALL_ZERO)])
    difference_N = _end_force_N(case, with_m2=True) - _end_force_N(case, with_m2=False)
    assert np.abs(difference_N).max() <= 50.0


def test_m2_4_friction_path_pair_is_the_hand_value() -> None:
    """Spec M2-4: F_s 4 kN, hand value only (no Hopsan reference): 10.89 +- 0.3 kN."""
    difference_kN = _front_left_pair(with_m2=True, is_body_fixed=True, friction_N=SEAL_FRICTION_N)
    assert difference_kN == pytest.approx(10.89, abs=0.3)
    assert _front_left_pair(with_m2=False, is_body_fixed=True, friction_N=SEAL_FRICTION_N) == 0.0


def test_m2_7_snapshot_continuation_is_bit_identical() -> None:
    case = _release_case(ROD_PRESSURE_RETRACT_PA, is_body_fixed=False)
    split_step = round(1.6 / DT_S)
    whole, whole_motors = _make_actuator(case)
    whole.configure_rod_release()
    expected = _run(case, whole, whole_motors)

    first, first_motors = _make_actuator(case)
    first.configure_rod_release()
    head = _run(case, first, first_motors, last_step=split_step)
    second, second_motors = _make_actuator(case)
    second.configure_rod_release()
    second.restore_state(first.state_arrays())
    tail = _run(case, second, second_motors, first_step=split_step,
                start=(head.heave_roll_pitch.copy(), head.rate.copy()))
    assert np.array_equal(np.vstack([head.force_N, tail.force_N]), expected.force_N)
    assert np.array_equal(second.rod_release_record()["m2_shift_total_mm"],
                          whole.rod_release_record()["m2_shift_total_mm"])


def test_m2_8_extend_then_retract_changes_the_sign_of_the_shift() -> None:
    """Spec M2-8: no reference value; a retract start raises p_r, so the shift goes down."""
    case = _Case(2.2, [(0.2, FRONT_LEFT_QUARTER), (1.0, tuple(-x for x in FRONT_LEFT_QUARTER))],
                 is_body_fixed=True)
    actuator, motors = _make_actuator(case)
    actuator.configure_rod_release()
    _run(case, actuator, motors, last_step=round(0.95 / DT_S))
    shift_extending_m = actuator.rod_release_record()["m2_shift_total_mm"][FRONT_LEFT]
    _run(case, actuator, motors, first_step=round(0.95 / DT_S))
    shift_after_retract_m = actuator.rod_release_record()["m2_shift_total_mm"][FRONT_LEFT]
    assert shift_after_retract_m < shift_extending_m


def test_m2_off_writes_no_snapshot_key_and_on_writes_them() -> None:
    case = _release_case(ROD_PRESSURE_RETRACT_PA, is_body_fixed=True)
    off, off_motors = _make_actuator(case)
    _run(case, off, off_motors, last_step=2)
    assert not [key for key in off.state_arrays() if key.startswith("m2_")]
    assert off.rod_release_record() is None
    assert "rod_release" not in off.meta()
    assert off.rod_side.rod_pressure_flow_law is None
    on, on_motors = _make_actuator(case)
    on.configure_rod_release()
    _run(case, on, on_motors, last_step=2)
    assert "m2_p_prev_Pa" in on.state_arrays()
    assert "m2_shift_total_m" in on.state_arrays()
    assert {key for key in on.state_arrays() if key.startswith("m2_")} == {
        "m2_p_prev_Pa", "m2_shift_total_m", "m2_clipped_steps"}  # revision 3: no new state
    assert on.meta()["rod_release"]["law"] == "flow_limited_r3"
    assert on.meta()["rod_release"]["pressure_law"]["tank_pressure_Pa"] == 2.0e5


def test_m2_shift_is_clipped_at_the_soft_limit_and_counted() -> None:
    case = _release_case(ROD_PRESSURE_RETRACT_PA, is_body_fixed=True)
    actuator, motors = _make_actuator(case)
    actuator.configure_rod_release()
    high = actuator.reference.s_ref_m + 1.0e-5
    actuator.reference.set_soft_limits(hi_m=high)
    _run(case, actuator, motors)
    assert np.all(actuator.reference.s_ref_m <= high)
    assert actuator.rod_release_record()["m2_clipped_steps"][FRONT_LEFT] > 0


def test_m2_with_counterbalance_is_refused() -> None:
    actuator, _motors = _make_actuator(_release_case(ROD_PRESSURE_RETRACT_PA, is_body_fixed=True))
    actuator.counterbalance = object()  # the CB path has never been tested with M2
    with pytest.raises(ValueError, match="counterbalance"):
        actuator.configure_rod_release()


def test_from_params_without_the_option_has_no_rod_release() -> None:
    params = load_yaml_params(model="L2b_NSC")
    motors = [_FakeMotor(0.3) for _ in range(4)]
    functions = [_FakeForceFunction() for _ in range(4)]
    plain = L2bForceActuator.from_params(params, motors, functions, [0.3] * 4)
    with_m2 = L2bForceActuator.from_params(params, motors, functions, [0.3] * 4, rod_release=True)
    assert plain.rod_release_record() is None
    assert with_m2.rod_release_record() is not None

# --- LC: overlap tail cut and check closing delay (spec 2.5, L-1 .. L-8) ----------------------

TAIL_START_S = 1.0
"""Command 0 from here on; 1 s at a constant command settles the 0.1 s valve lag (e^-10)."""
TAIL_RUN_S = 3.0
OVERLAP_TABLE_S = {(0.01, 0.25): 0.322, (0.01, 1.0): 0.461, (0.02, 0.25): 0.253,
                   (0.02, 1.0): 0.391, (0.05, 0.25): 0.161, (0.05, 1.0): 0.300}
"""Spec 2.5 hand values of t_ol - t_0 [s] per (delta_ol, command / v_max)."""
LOST_STROKE_MM = {0.01: 0.0209, 0.02: 0.0418, 0.05: 0.1046}
FORCE_STEP_N = {0: 42.0, 2: 36.0}
"""Spec L-3, delta_ol 2 %: c_move u_ol of FL and RL."""
REAR_LEFT = 2


@dataclass
class _Tail:
    t_s: np.ndarray
    speed_m_s: np.ndarray
    force_N: np.ndarray
    locked: np.ndarray
    s_ref_m: np.ndarray


def _lock_closure(ratio: float, delay_s: float):
    from outrigger_sim.hydraulics.v5_options import LockClosureSetting

    return LockClosureSetting(ratio, delay_s)


def _drive_tail(leg: int, fraction: float, *, ratio: float | None, delay_s: float = 0.05,
                restart_s: float | None = None, actuator=None, motors=None, first_step: int = 0,
                last_step: int | None = None) -> tuple[_Tail, L2bForceActuator, list]:
    """Body fixed; ``leg`` at ``fraction`` v_max until ``TAIL_START_S``, then 0 (again the same
    command from ``restart_s`` on)."""
    if actuator is None:
        case = _Case(TAIL_START_S + TAIL_RUN_S, [], is_body_fixed=True)
        actuator, motors = _make_actuator(case)
        if ratio is not None:
            actuator.configure_lock_closure(_lock_closure(ratio, delay_s))
    last = round((TAIL_START_S + TAIL_RUN_S) / DT_S) if last_step is None else last_step
    rows = {name: [] for name in ("t", "u", "F", "locked", "s_ref")}
    for k in range(first_step, last):
        t_s = k * DT_S
        command = np.zeros(4)
        if t_s < TAIL_START_S or (restart_s is not None and t_s >= restart_s):
            command[leg] = fraction * P.v_max
        actuator.set_command(command)
        actuator.hook(t_s, DT_S)
        actuator.on_step_end()
        rows["t"].append(t_s)
        rows["u"].append(actuator.reference.u_applied_m_s[leg])
        rows["F"].append(actuator.force_N[leg])
        rows["locked"].append(bool(actuator.rod_side.locked[leg]))
        rows["s_ref"].append(actuator.reference.s_ref_m[leg])
    tail = _Tail(*(np.array(rows[name]) for name in ("t", "u", "F", "locked", "s_ref")))
    return tail, actuator, motors


def _first_index_after(tail: _Tail, flags: np.ndarray, t_from_s: float) -> int:
    return int(np.flatnonzero(flags & (tail.t_s >= t_from_s - 1e-12))[0])


@pytest.mark.parametrize("ratio, fraction", sorted(OVERLAP_TABLE_S))
def test_l1_cut_time_is_the_hand_value(ratio, fraction) -> None:
    tail, _, _ = _drive_tail(FRONT_LEFT, fraction, ratio=ratio)
    cut = _first_index_after(tail, tail.speed_m_s == 0.0,
                             TAIL_START_S)
    elapsed_s = tail.t_s[cut] - TAIL_START_S
    overlap_speed = ratio * P.v_max
    formula_s = VALVE_TAU_S * np.log(max(fraction * P.v_max, overlap_speed) / overlap_speed)
    assert abs(elapsed_s - formula_s) <= DT_S + 1e-12
    assert abs(elapsed_s - OVERLAP_TABLE_S[(ratio, fraction)]) <= 0.001


@pytest.mark.parametrize("ratio", sorted(LOST_STROKE_MM))
def test_l2_cut_loses_the_tail_stroke(ratio) -> None:
    with_cut, _, _ = _drive_tail(FRONT_LEFT, 1.0, ratio=ratio)
    without, _, _ = _drive_tail(FRONT_LEFT, 1.0, ratio=None)
    lost_mm = (without.s_ref_m[-1] - with_cut.s_ref_m[-1]) * 1e3
    assert lost_mm == pytest.approx(LOST_STROKE_MM[ratio], rel=0.01)


@pytest.mark.parametrize("leg", sorted(FORCE_STEP_N))
def test_l3_force_step_at_the_cut_is_the_moving_dashpot(leg) -> None:
    tail, _, _ = _drive_tail(leg, 1.0, ratio=0.02)
    cut = _first_index_after(tail, tail.speed_m_s == 0.0, TAIL_START_S)
    force = tail.force_N
    step_N = (force[cut] - force[cut - 1]) - (force[cut - 1] - force[cut - 2])
    assert -step_N == pytest.approx(FORCE_STEP_N[leg], rel=0.05)


@pytest.mark.parametrize("delay_s", [0.02, 0.05, 0.10])
def test_l4_lock_follows_the_cut_by_the_closing_delay_without_a_force_step(delay_s) -> None:
    tail, _, _ = _drive_tail(FRONT_LEFT, 1.0, ratio=0.02, delay_s=delay_s)
    cut = _first_index_after(tail, tail.speed_m_s == 0.0, TAIL_START_S)
    lock = _first_index_after(tail, tail.locked, TAIL_START_S)
    assert abs(tail.t_s[lock] - tail.t_s[cut] - delay_s) <= DT_S + 1e-9
    differences = np.diff(tail.force_N[lock - 5:lock + 5])
    assert abs(differences[4]) <= 1.0


def test_l5_new_command_inside_the_delay_does_not_lock() -> None:
    probe, _, _ = _drive_tail(FRONT_LEFT, 1.0, ratio=0.02, delay_s=0.05)
    cut_s = probe.t_s[_first_index_after(probe, probe.speed_m_s == 0.0, TAIL_START_S)]
    tail, actuator, _ = _drive_tail(FRONT_LEFT, 1.0, ratio=0.02, delay_s=0.05,
                                    restart_s=cut_s + 0.025)
    assert not tail.locked[tail.t_s >= TAIL_START_S].any()
    assert not actuator.rod_side.locked[FRONT_LEFT]  # no new anchor: it moves on


def test_l6_small_non_zero_command_keeps_flowing() -> None:
    case = _Case(2.0, [], is_body_fixed=True)
    actuator, _ = _make_actuator(case)
    actuator.configure_lock_closure(_lock_closure(0.02, 0.05))
    command = np.zeros(4)
    command[FRONT_LEFT] = 0.16e-3
    for k in range(round(2.0 / DT_S)):
        actuator.set_command(command)
        actuator.hook(k * DT_S, DT_S)
        actuator.on_step_end()
    assert actuator.reference.u_applied_m_s[FRONT_LEFT] == pytest.approx(0.16e-3, rel=1e-6)
    assert actuator.reference.overlap_cut_steps[FRONT_LEFT] == 0


def test_l7_snapshot_inside_the_delay_continues_bit_identically() -> None:
    whole, _, _ = _drive_tail(FRONT_LEFT, 1.0, ratio=0.02, delay_s=0.05)
    cut = _first_index_after(whole, whole.speed_m_s == 0.0, TAIL_START_S)
    split = cut + round(0.025 / DT_S)
    head, first, _ = _drive_tail(FRONT_LEFT, 1.0, ratio=0.02, delay_s=0.05, last_step=split)
    case = _Case(TAIL_START_S + TAIL_RUN_S, [], is_body_fixed=True)
    second, motors = _make_actuator(case)
    second.configure_lock_closure(_lock_closure(0.02, 0.05))
    second.restore_state(first.state_arrays())
    rest, _, _ = _drive_tail(FRONT_LEFT, 1.0, ratio=0.02, actuator=second, motors=motors,
                             first_step=split)
    assert np.array_equal(np.concatenate([head.force_N, rest.force_N]), whole.force_N)
    assert np.array_equal(np.concatenate([head.locked, rest.locked]), whole.locked)


def test_l8_without_the_option_nothing_changes() -> None:
    case = _Case(1.0, [], is_body_fixed=True)
    actuator, _ = _make_actuator(case)
    assert actuator.rod_side.closing_delay_s == 0.0
    assert not actuator.reference.lock_closure_on
    assert "lock_closure" not in actuator.meta()
    plain, _, _ = _drive_tail(FRONT_LEFT, 1.0, ratio=None)
    assert plain.speed_m_s[-1] != 0.0  # the epsilon tail of the exponential valve is still there


def test_lc_refuses_the_counterbalance_and_a_plant_without_the_valve_model() -> None:
    case = _Case(1.0, [], is_body_fixed=True)
    actuator, _ = _make_actuator(case)
    actuator.counterbalance = object()
    with pytest.raises(ValueError, match="counterbalance"):
        actuator.configure_lock_closure(_lock_closure(0.02, 0.05))
    reference = SpeedReference([0.3] * 4, [STROKE_RANGE_M] * 4, max_speed_m_s=P.v_max, ramp_s=0.1)
    with pytest.raises(ValueError, match="valve model"):
        reference.configure_lock_closure(_lock_closure(0.02, 0.05), zero_command_m_s=1e-6)

# --- M1c on the L2b hook (spec 2.4, C-6, C-7) ----------------------------------------------------

def _check_delay_circuit():
    from outrigger_sim.hydraulics.check_open_delay import CheckDelayCircuit

    return CheckDelayCircuit(head_area_m2=P.A_h, annulus_area_m2=P.A_r, stroke_m=P.stroke,
                             rod_dead_length_m=P.L0r, head_dead_length_m=P.L0h,
                             bulk_modulus_Pa=P.beta, tank_pressure_Pa=2e5, max_speed_m_s=P.v_max,
                             compensator_drop_Pa=P.dp_comp)


def _m1c_actuator(kind: str):
    from outrigger_sim.hydraulics.v5_options import CheckDelaySetting

    case = _Case(3.0, [], is_body_fixed=True)
    actuator, motors = _make_actuator(case)
    actuator.configure_check_delay(CheckDelaySetting(kind), _check_delay_circuit())
    return actuator, motors


def _drive_front_left(actuator, speed_m_s: float, duration_s: float, first_step: int = 0):
    command = np.zeros(4)
    command[FRONT_LEFT] = speed_m_s
    speeds = []
    for k in range(first_step, first_step + round(duration_s / DT_S)):
        actuator.set_command(command)
        actuator.hook(k * DT_S, DT_S)
        actuator.on_step_end()
        speeds.append(actuator.reference.u_applied_m_s[FRONT_LEFT])
    return np.array(speeds)


def test_c6_hook_inputs_are_the_harness_definitions() -> None:
    """Spec C-6: p_h = (F_p + p_r A_ann) / A_p without the floor, the law's lock state and p_r;
    the friction-sign question of C-6 needs the harness kernel and is not settled here."""
    actuator, _ = _m1c_actuator("BL")
    _drive_front_left(actuator, 0.0, 0.01)
    inputs = actuator._check_delay.inputs
    oil = actuator.rod_side
    expected_head = (actuator.acting_pressure_force_N + oil.rod_pressure_Pa * P.A_r) / P.A_h
    assert np.array_equal(inputs.p_h, expected_head)
    assert np.array_equal(inputs.p_r, oil.rod_pressure_Pa)
    assert np.array_equal(inputs.locked, oil.locked)
    assert np.all(inputs.band_N == 0.0)


def test_m1c_holds_the_extending_leg_then_lets_it_go() -> None:
    actuator, _ = _m1c_actuator("BL")
    _drive_front_left(actuator, 0.0, 0.01)
    speeds = _drive_front_left(actuator, 0.25 * P.v_max, 2.0, first_step=100)
    held = np.flatnonzero(speeds <= 2e-6)
    assert held.size > 0 and speeds[-1] > 0.2 * P.v_max
    summary = actuator.check_delay_summary()
    assert summary["unit_status"] == "below_criteria_reference_only"
    assert summary["n_fills"][FRONT_LEFT][0] == 1


def test_c7_step_convergence_of_the_head_opening() -> None:
    """Spec C-7: head opening stroke with 1 ms against 1e-4 s steps within 1 %."""
    from outrigger_sim.hydraulics.check_open_delay import CheckDelayInputs, CheckOpenDelay
    from outrigger_sim.hydraulics.v5_options import CheckDelaySetting

    strokes = []
    for dt in (1e-3, 1e-4):
        model = CheckOpenDelay(CheckDelaySetting("VN"), _check_delay_circuit())
        u = np.zeros(4)
        u[FRONT_LEFT] = 0.25 * P.v_max
        pushed = 0.0
        for k in range(round(10.0 / dt)):
            model.filter(CheckDelayInputs(k * dt, dt, u, np.full(4, 89.5e5), np.full(4, 2e5),
                                          np.ones(4, bool), np.zeros(4), np.zeros(4), P.s0))
            pushed += u[FRONT_LEFT] * dt
            if model.is_open[FRONT_LEFT]:
                break
        strokes.append(pushed)
    assert strokes[0] == pytest.approx(strokes[1], rel=0.01)


def test_m1c_snapshot_round_trip_and_refusals() -> None:
    from outrigger_sim.hydraulics.v5_options import CheckDelaySetting

    first, _ = _m1c_actuator("VN")
    _drive_front_left(first, 0.0, 0.01)
    _drive_front_left(first, 0.25 * P.v_max, 0.05, first_step=100)
    second, _ = _m1c_actuator("VN")
    second.restore_state(first.state_arrays())
    a = _drive_front_left(first, 0.25 * P.v_max, 0.5, first_step=600)
    b = _drive_front_left(second, 0.25 * P.v_max, 0.5, first_step=600)
    assert np.array_equal(a, b)
    plain, _ = _make_actuator(_Case(1.0, [], is_body_fixed=True))
    assert not [key for key in plain.state_arrays() if key.startswith("m1c_")]
    plain.counterbalance = object()
    with pytest.raises(ValueError, match="counterbalance"):
        plain.configure_check_delay(CheckDelaySetting("VN"), _check_delay_circuit())
    reference = SpeedReference([0.3] * 4, [STROKE_RANGE_M] * 4, max_speed_m_s=P.v_max, ramp_s=0.1)
    with pytest.raises(ValueError, match="valve model"):
        reference.set_check_delay(object())
