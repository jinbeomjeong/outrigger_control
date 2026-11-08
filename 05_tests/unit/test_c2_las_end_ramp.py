"""C2 LAS-b end ramp ``end_ramp_periods`` (``N_r``, ``las_revA_targeted_rules.md`` 1.3 and 7.3).

After a ``sum`` / ``time`` end whose last acted period was scaled (``lambda_0 < 1``), the command
is scaled by ``lambda_m = lambda_0 + (1 - lambda_0) m / (N_r + 1)``, ``m = 1..N_r`` from the end
period on, floored at the slow mean; LOC, not LEVEL, soil mode, re-approach and leaving the zone
(no soil response) cancel it. ``N_r`` 0 keeps the b0 / P5 commands bit for bit. Benches and
stage helpers are those of ``test_c2_las.py``; the closed-loop bit tests are R-0 / R-0P5 of the
rules, run outside the unit tests.
"""

from __future__ import annotations

import pickle
from dataclasses import replace

import numpy as np
import pytest
from test_c2_las import (  # same test folder
    FAST_SPEEDS_M_S,
    HEAVY_LOADS_N,
    MORE_TWISTED_LOADS_N,
    TWISTED_LOADS_N,
    _block_s2,
    _block_s3,
    _block_s4,
    _block_s5,
    las_config,
    slow_mean_m_s,
    stage,
)
from test_c2_p30 import geometry, level_bench  # noqa: F401

from outrigger_sim.control.c2 import (
    LIFTOFF_SLOW_END_EVENT,
    LIFTOFF_SLOW_EVENT,
    LIFTOFF_SLOW_RAMP_END_EVENT,
    C2Config,
    C2Controller,
    LiftoffApproachSlowSettings,
    LiftoffRampEnd,
    LiftoffSlowEnd,
    liftoff_ramp_factor,
)

RAMP_RULE = 4
RAMP_LONG = 6
BETAS = (3.5, 4.5)
REAPPROACHING_RL = np.array([False, False, True, False])
SUM_END_STEPS = 5
"""HEAVY periods after the start until the ``sum`` end (the fifth is the end period)."""
TIME_END_STEPS = 15
TAIL_STEPS = 10
FACTOR_TOLERANCE = 1e-15
SLOW_SPEEDS_FRACTION = 0.5
"""A command below the slow mean: an acted period that is not scaled (``lambda_0`` = 1)."""


def bench_controller(bench_geometry, end_ramp_periods: int | None, beta: float = 3.5,
                     require_soil_response: bool = True) -> C2Controller:
    """LEVEL bench of ``test_c2_las.py`` (crawler zone, no LOC, t 20 s); ``None`` leaves the
    field at its class default."""
    changes = {"light_leg_fraction_of_F_min": beta,
               "require_soil_response": require_soil_response}
    if end_ramp_periods is not None:
        changes["end_ramp_periods"] = end_ramp_periods
    controller = level_bench(bench_geometry, las_config(**changes)).controller
    controller._state.in_crawler_zone = True
    controller._state.liftoff_slow = None
    controller._las_t_s = 20.0
    if not require_soil_response:
        controller.config = replace(controller.config,
                                    soil=replace(controller.config.soil, enable=False))
    return controller


def start(controller: C2Controller) -> None:
    stage(controller, TWISTED_LOADS_N)
    stage(controller, MORE_TWISTED_LOADS_N)


def run_to_sum_end(controller: C2Controller) -> list[np.ndarray]:
    """Start, then HEAVY periods; the last returned output is the end period's."""
    start(controller)
    return [stage(controller, HEAVY_LOADS_N) for _ in range(SUM_END_STEPS)]


def slow_and_ramp_events(controller: C2Controller) -> list[str]:
    prefixes = (f"{LIFTOFF_SLOW_EVENT}:", f"{LIFTOFF_SLOW_END_EVENT}:",
                f"{LIFTOFF_SLOW_RAMP_END_EVENT}:")
    return [event.name for event in controller.events if event.name.startswith(prefixes)]


def ramp_meta(controller: C2Controller) -> dict:
    return controller.meta()["liftoff_approach_slow"]["ramp"]


def lambda_0(controller: C2Controller, speeds=FAST_SPEEDS_M_S) -> float:
    return slow_mean_m_s(controller) / float(np.mean(speeds))


def scale_of(output: np.ndarray, speeds=FAST_SPEEDS_M_S) -> np.ndarray:
    return np.asarray(output) / np.asarray(speeds)


# --- settings ------------------------------------------------------------------------------------


def test_default_is_zero_and_the_preset_keeps_it() -> None:
    assert LiftoffApproachSlowSettings().end_ramp_periods == 0
    assert C2Config().with_10hz_d1().liftoff_approach_slow.end_ramp_periods == 0


@pytest.mark.parametrize("bad", [-1, 4.0, True, "4", None])
def test_negative_or_not_an_int_is_a_value_error(bad) -> None:
    with pytest.raises(ValueError, match="end_ramp_periods"):
        LiftoffApproachSlowSettings(end_ramp_periods=bad)


def test_old_pickle_reads_zero(geometry) -> None:  # noqa: F811
    preset = C2Config().with_10hz_d1()
    copied = pickle.loads(pickle.dumps(C2Controller(geometry, preset)))
    copied.config.liftoff_approach_slow.__dict__.pop("end_ramp_periods")
    aged = pickle.loads(pickle.dumps(copied))
    assert "end_ramp_periods" not in aged.config.liftoff_approach_slow.__dict__
    assert aged.config.liftoff_approach_slow.end_ramp_periods == 0
    assert aged.config.liftoff_approach_slow == preset.liftoff_approach_slow


def test_meta_has_the_setting_and_the_ramp_block(geometry) -> None:  # noqa: F811
    controller = bench_controller(geometry, RAMP_RULE)
    assert controller.meta()["liftoff_approach_slow"]["settings"]["end_ramp_periods"] == 4
    start(controller)
    assert ramp_meta(controller) == {"n_r": 4, "start_factor": None, "periods_applied": 0,
                                     "scaled_periods": 0, "end_t_s": None, "end_reason": None}


# --- N_r 0: bit for bit, no new events -----------------------------------------------------------


SCENARIOS = {
    "sum": [(None, HEAVY_LOADS_N, None)] * SUM_END_STEPS,
    "time": [(None, MORE_TWISTED_LOADS_N, None)] * TIME_END_STEPS,
    "loc": [(None, HEAVY_LOADS_N, None), (_block_s3, HEAVY_LOADS_N, None)],
    "phase": [(None, HEAVY_LOADS_N, None), (_block_s2, HEAVY_LOADS_N, None)],
    "soil": [(None, HEAVY_LOADS_N, None), (_block_s4, HEAVY_LOADS_N, None)],
    "reapproach": [(None, HEAVY_LOADS_N, None), (None, HEAVY_LOADS_N, REAPPROACHING_RL)],
}
"""Steps after :func:`start`: (state change before the step, loads, re-approach flags)."""


def run_scenario(bench_geometry, end_ramp_periods: int | None, name: str, beta: float = 3.5
                 ) -> tuple[list[np.ndarray], C2Controller]:
    controller = bench_controller(bench_geometry, end_ramp_periods, beta)
    start(controller)
    outputs = []
    for action, loads, reapproaching in SCENARIOS[name]:
        if action is not None:
            action(controller)
        outputs.append(stage(controller, loads, reapproaching=reapproaching))
    for _ in range(TAIL_STEPS):
        outputs.append(stage(controller, HEAVY_LOADS_N))
    return outputs, controller


@pytest.mark.parametrize("beta", BETAS)
@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_n_r_zero_is_bit_identical_and_quiet(geometry, name, beta) -> None:  # noqa: F811
    default_outputs, default_controller = run_scenario(geometry, None, name, beta)
    zero_outputs, zero_controller = run_scenario(geometry, 0, name, beta)
    assert [out.tobytes() for out in zero_outputs] == [out.tobytes() for out in default_outputs]
    end_index = len(SCENARIOS[name]) - 1
    assert all(out is FAST_SPEEDS_M_S for out in zero_outputs[end_index:])  # b0: end keeps u
    assert slow_and_ramp_events(zero_controller) == slow_and_ramp_events(default_controller)
    assert not any(event.startswith(LIFTOFF_SLOW_RAMP_END_EVENT)
                   for event in slow_and_ramp_events(zero_controller))
    assert ramp_meta(zero_controller)["periods_applied"] == 0
    assert ramp_meta(zero_controller)["start_factor"] is None


# --- N_r 4: the scale column ---------------------------------------------------------------------


@pytest.mark.parametrize("beta", BETAS)
def test_sum_end_ramp_scale_column(geometry, beta) -> None:  # noqa: F811
    controller = bench_controller(geometry, RAMP_RULE, beta)
    outputs = run_to_sum_end(controller)
    outputs += [stage(controller, HEAVY_LOADS_N) for _ in range(TAIL_STEPS)]
    end_index = SUM_END_STEPS - 1
    lambda0 = lambda_0(controller)
    for m in range(1, RAMP_RULE + 1):
        expected = lambda0 + (1.0 - lambda0) * m / (RAMP_RULE + 1)
        got = scale_of(outputs[end_index + m - 1])
        assert np.max(np.abs(got - expected)) <= FACTOR_TOLERANCE, m
    assert all(out is FAST_SPEEDS_M_S for out in outputs[end_index + RAMP_RULE:])
    meta = controller.meta()["liftoff_approach_slow"]
    assert meta["end_reason"] == str(LiftoffSlowEnd.SUM)
    assert abs(meta["ramp"]["start_factor"] - lambda0) <= FACTOR_TOLERANCE
    assert meta["ramp"]["periods_applied"] == meta["ramp"]["scaled_periods"] == RAMP_RULE
    assert meta["ramp"]["end_reason"] == str(LiftoffRampEnd.DONE)
    assert meta["ramp"]["end_t_s"] == pytest.approx(meta["end_s"] + 0.1 * (RAMP_RULE - 1))
    assert slow_and_ramp_events(controller) == [
        f"{LIFTOFF_SLOW_EVENT}:FR", f"{LIFTOFF_SLOW_END_EVENT}:sum",
        f"{LIFTOFF_SLOW_RAMP_END_EVENT}:done"]


def test_time_end_starts_the_ramp_and_n_r_six_runs_six(geometry) -> None:  # noqa: F811
    controller = bench_controller(geometry, RAMP_LONG)
    start(controller)
    outputs = [stage(controller, MORE_TWISTED_LOADS_N) for _ in range(TIME_END_STEPS)]
    outputs += [stage(controller, MORE_TWISTED_LOADS_N) for _ in range(TAIL_STEPS)]
    assert controller.meta()["liftoff_approach_slow"]["end_reason"] == str(LiftoffSlowEnd.TIME)
    end_index = TIME_END_STEPS - 1
    lambda0 = lambda_0(controller)
    factors = [float(scale_of(out)[0]) for out in outputs[end_index:end_index + RAMP_LONG]]
    expected = [liftoff_ramp_factor(lambda0, m, RAMP_LONG) for m in range(1, RAMP_LONG + 1)]
    assert np.max(np.abs(np.array(factors) - expected)) <= FACTOR_TOLERANCE
    assert outputs[end_index + RAMP_LONG] is FAST_SPEEDS_M_S
    assert ramp_meta(controller)["periods_applied"] == RAMP_LONG


def test_factor_formula_by_hand() -> None:
    assert liftoff_ramp_factor(1 / 3, 1, 4) == pytest.approx(1 / 3 + (2 / 3) / 5, abs=1e-15)
    assert liftoff_ramp_factor(0.2, 4, 4) == pytest.approx(0.2 + 0.8 * 4 / 5, abs=1e-15)
    assert liftoff_ramp_factor(0.2, 5, 4) == pytest.approx(1.0, abs=1e-15)


# --- the floor at the slow mean ------------------------------------------------------------------


def test_floor_at_the_slow_mean_and_a_slow_command_passes(geometry) -> None:  # noqa: F811
    controller = bench_controller(geometry, RAMP_RULE)
    run_to_sum_end(controller)  # m = 1 at the end period
    slow_mean = slow_mean_m_s(controller)
    near = np.full(4, 1.2 * slow_mean)  # gamma v_max / mean = 0.83 > lambda_2
    out = stage(controller, HEAVY_LOADS_N, near)
    assert float(np.mean(out)) == pytest.approx(slow_mean, rel=1e-15)
    below = np.full(4, SLOW_SPEEDS_FRACTION * slow_mean)
    assert stage(controller, HEAVY_LOADS_N, below) is below
    ramp = ramp_meta(controller)
    assert ramp["periods_applied"] == 3 and ramp["scaled_periods"] == 2


# --- cancels and ends without a ramp -------------------------------------------------------------


def _loc(controller):
    _block_s3(controller)


CANCELS = {"loc": (_loc, None), "phase": (_block_s2, None), "soil": (_block_s4, None),
           "reapproach": (None, REAPPROACHING_RL)}


@pytest.mark.parametrize("reason", sorted(CANCELS))
def test_cancel_during_the_ramp(geometry, reason) -> None:  # noqa: F811
    controller = bench_controller(geometry, RAMP_RULE)
    run_to_sum_end(controller)
    action, reapproaching = CANCELS[reason]
    if action is not None:
        action(controller)
    assert stage(controller, HEAVY_LOADS_N, reapproaching=reapproaching) is FAST_SPEEDS_M_S
    assert stage(controller, HEAVY_LOADS_N) is FAST_SPEEDS_M_S
    ramp = ramp_meta(controller)
    assert ramp["end_reason"] == reason and ramp["periods_applied"] == 1
    assert slow_and_ramp_events(controller)[-1] == f"{LIFTOFF_SLOW_RAMP_END_EVENT}:{reason}"


def test_cancel_on_a_period_without_a_level_step(geometry) -> None:  # noqa: F811
    controller = bench_controller(geometry, RAMP_RULE)
    run_to_sum_end(controller)
    slow = controller._liftoff_slow_state()
    slow.has_level_step_run = False
    controller._finish_liftoff_slow_period(21.0)
    assert ramp_meta(controller)["end_reason"] == str(LiftoffRampEnd.PHASE)
    assert ramp_meta(controller)["end_t_s"] == pytest.approx(21.0)
    assert stage(controller, HEAVY_LOADS_N) is FAST_SPEEDS_M_S


def test_zone_cancel_without_the_soil_response(geometry) -> None:  # noqa: F811
    controller = bench_controller(geometry, RAMP_RULE, require_soil_response=False)
    run_to_sum_end(controller)
    assert controller.meta()["liftoff_approach_slow"]["end_reason"] == str(LiftoffSlowEnd.SUM)
    _block_s5(controller)
    assert stage(controller, HEAVY_LOADS_N) is FAST_SPEEDS_M_S
    assert ramp_meta(controller)["end_reason"] == str(LiftoffRampEnd.ZONE)


@pytest.mark.parametrize("name", ["loc", "phase", "soil", "reapproach"])
def test_no_ramp_after_a_safety_or_phase_end(geometry, name) -> None:  # noqa: F811
    outputs, controller = run_scenario(geometry, RAMP_RULE, name)
    reference, _ = run_scenario(geometry, 0, name)
    assert [out.tobytes() for out in outputs] == [out.tobytes() for out in reference]
    assert controller.meta()["liftoff_approach_slow"]["end_reason"] == name
    assert ramp_meta(controller)["periods_applied"] == 0
    assert not any(event.startswith(LIFTOFF_SLOW_RAMP_END_EVENT)
                   for event in slow_and_ramp_events(controller))


def test_no_ramp_after_a_zone_end(geometry) -> None:  # noqa: F811
    controller = bench_controller(geometry, RAMP_RULE, require_soil_response=False)
    start(controller)
    stage(controller, HEAVY_LOADS_N)
    _block_s5(controller)
    assert stage(controller, HEAVY_LOADS_N) is FAST_SPEEDS_M_S
    assert controller.meta()["liftoff_approach_slow"]["end_reason"] == str(LiftoffSlowEnd.ZONE)
    assert stage(controller, HEAVY_LOADS_N) is FAST_SPEEDS_M_S
    assert ramp_meta(controller)["periods_applied"] == 0


def test_no_ramp_when_lambda_0_is_one(geometry) -> None:  # noqa: F811
    """The last acted period was not scaled (its command already below the slow mean)."""
    controller = bench_controller(geometry, RAMP_RULE)
    start(controller)
    slow = np.full(4, SLOW_SPEEDS_FRACTION * slow_mean_m_s(controller))
    for _ in range(SUM_END_STEPS - 1):
        stage(controller, HEAVY_LOADS_N, slow)
    assert stage(controller, HEAVY_LOADS_N) is FAST_SPEEDS_M_S  # end period, no ramp
    assert controller._liftoff_slow_state().last_scale_factor == 1.0
    assert ramp_meta(controller)["periods_applied"] == 0
    assert ramp_meta(controller)["start_factor"] is None
