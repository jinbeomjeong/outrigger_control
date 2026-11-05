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
    """Spec M2-1: 10.89 +- 0.3 kN (hand 10.893, numpy 10.879, wrapper 10.700)."""
    assert _front_left_pair(with_m2=True, is_body_fixed=True) == pytest.approx(10.89, abs=0.3)
    assert _front_left_pair(with_m2=False, is_body_fixed=True) == 0.0


def test_m2_1_equals_the_stored_wrapper_value() -> None:
    """The hook reproduces the review wrapper of ``m2_check.json`` (10.700 kN end difference)."""
    assert _front_left_pair(with_m2=True, is_body_fixed=True) == pytest.approx(10.700, abs=0.001)


def test_m2_2_free_body_pair_of_front_left() -> None:
    """Spec M2-2: 4.13 .. 4.25 +- 0.5 kN (Hopsan 4.13, numpy 4.20, wrapper 4.25)."""
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
    on, on_motors = _make_actuator(case)
    on.configure_rod_release()
    _run(case, on, on_motors, last_step=2)
    assert "m2_p_prev_Pa" in on.state_arrays()
    assert "m2_shift_total_m" in on.state_arrays()


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
