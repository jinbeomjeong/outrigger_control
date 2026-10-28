"""C2 P-S8-29 (user decision 2026-10-28, variant V2b of ``r73_p29_screen.py``): the relaxed
twist condition of the completion on a creeping pad (tests T1 .. T9 of the task).

Synthetic 10 Hz benches of ``test_c2_r8d1.py`` (no CHECK, pressure judge, soil response off, so
the lower load estimate is the reading). The lift-off confirmation is forced through the soil
state. The bench strokes do not follow the commands, so a twist load the bench reads stays
until the bench changes it. The closed-loop acceptance (``r73_p29_screen.py`` with the project
controller against the rev. 73 V2b hashes) runs outside the unit tests.
"""

from __future__ import annotations

import json
import pickle
from collections.abc import Callable
from dataclasses import replace

import numpy as np
import pytest
from test_c2_r8d1 import (  # same test folder
    NO_REAPPROACH,
    PERIOD_S,
    STEADY_LOAD_N,
    TOUCH_HOLD_SAMPLES,
    Bench,
    bench_config,
    operating_strokes,
    ready_bench,
)

from outrigger_sim.control.c2 import (
    TWIST_RELAX_DONE_EVENT,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    TwistCompletionRelaxSettings,
    _Reading,
    _RunState,
)
from outrigger_sim.params import LEG_ORDER, load_params

RR = LEG_ORDER.index("RR")
SETTLE_S = 10.0
WINDOW_S = 5.0
RELAXED_TWIST_N = 12e3
"""Above ``done_twist_N`` (3 kN), below ``max_twist_N`` (15 kN)."""
TOO_LARGE_TWIST_N = 16e3
SMALL_TWIST_N = 2e3
"""Below ``done_twist_N``: the plain rule."""
FALL_PER_PERIOD_N = 20.0
RUN_LIMIT_S = 40.0
LOAD_MARGIN_N = 500.0
TIME_TOLERANCE_S = 1e-9


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def without_relax(config: C2Config) -> C2Config:
    return replace(config, twist_completion_relax=TwistCompletionRelaxSettings())


def forces_with_twist(
    geometry: C2Geometry, twist_N: float, fixed_leg_force_N: dict[int, float] | None = None
) -> np.ndarray:
    """Leg readings around ``STEADY_LOAD_N`` whose twist load ``n . F`` is ``twist_N``; legs in
    ``fixed_leg_force_N`` keep their given reading and the others carry the twist."""
    fixed = fixed_leg_force_N or {}
    forces = np.full(4, STEADY_LOAD_N)
    direction = geometry.twist_vector.copy()
    for leg, force_N in fixed.items():
        forces[leg] = force_N
        direction[leg] = 0.0
    shortfall_N = twist_N - float(geometry.twist_vector @ forces)
    return forces + shortfall_N * direction / float(direction @ direction)


def touched_bench(geometry: C2Geometry, config: C2Config, *, force_liftoff: bool = True) -> Bench:
    """LEVEL on a level floor with the crawler clear; the LOC forced unless told not to."""
    bench = Bench(C2Controller(geometry, config), geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    assert bench.controller.phase is C2Phase.LEVEL
    if force_liftoff:
        bench.controller._soil_state().is_liftoff_confirmed = True
    return bench


def run_level(
    bench: Bench, forces_at: Callable[[int], np.ndarray], limit_s: float = RUN_LIMIT_S
) -> None:
    """Step LEVEL with ``forces_at(period index)`` until another phase or ``limit_s``."""
    start_s = bench.t_s
    period = 0
    while bench.controller.phase is C2Phase.LEVEL and bench.t_s - start_s < limit_s:
        bench.step(forces_at(period))
        period += 1


def relaxed_events(controller: C2Controller) -> list[str]:
    return [
        event.name
        for event in controller.events
        if event.name.startswith(f"{TWIST_RELAX_DONE_EVENT}:")
    ]


def twist_meta(controller: C2Controller) -> dict:
    return json.loads(json.dumps(controller.meta()))["twist_relax"]


# --- T1 / T9 settings ------------------------------------------------------------------------


def test_t1_class_default_is_off() -> None:
    assert C2Config().twist_completion_relax == TwistCompletionRelaxSettings()
    assert not TwistCompletionRelaxSettings().enable
    assert _RunState.twist_relax_settled_since_s is None  # class attribute (old pickles)
    assert _RunState.twist_relax_history is None


def test_t1_preset_on_a_level_bench_commands_as_without_relax(geometry) -> None:
    """With ``|D|`` at zero the relaxation never acts: the R8 bench run is bit for bit the run
    with it off."""
    preset = ready_bench(geometry, bench_config())
    old = ready_bench(geometry, without_relax(bench_config()))
    np.testing.assert_array_equal(np.array(preset.outputs), np.array(old.outputs))
    assert relaxed_events(preset.controller) == []


def test_t9_preset_values() -> None:
    preset = C2Config().with_10hz_d1()
    assert preset.twist_completion_relax == TwistCompletionRelaxSettings(
        enable=True,
        settle_s=SETTLE_S,
        window_s=WINDOW_S,
        drop_N=0.0,
        rise_tol_N=600.0,  # U-S8-80 (b), 2026-10-28
        max_twist_N=15000.0,
        require_loads_ge_F_min=True,
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"settle_s": 0.0},
        {"window_s": -1.0},
        {"drop_N": -1.0},
        {"rise_tol_N": -1.0},
        {"max_twist_N": -1.0},
    ],
)
def test_t9_settings_validation(bad) -> None:
    with pytest.raises(ValueError):
        TwistCompletionRelaxSettings(**bad)


def test_old_pickle_reads_the_relax_off(geometry) -> None:
    """Configs and run states pickled before P-S8-29 read the class-level defaults."""
    controller = C2Controller(geometry, C2Config())
    copied = pickle.loads(pickle.dumps(controller))
    copied.config.__dict__.pop("twist_completion_relax")
    for name in ("twist_relax_settled_since_s", "twist_relax_history", "twist_relax_done_count"):
        copied._state.__dict__.pop(name)
    aged = pickle.loads(pickle.dumps(copied))
    assert aged.config.twist_completion_relax == TwistCompletionRelaxSettings()
    assert aged._state.twist_relax_history is None
    assert twist_meta(aged)["n_relaxed_done"] == 0


# --- T2 .. T4 the relaxed DONE ------------------------------------------------------------------


def test_t2_falling_twist_completes_relaxed_once(geometry) -> None:
    bench = touched_bench(geometry, bench_config())
    start_s = bench.t_s

    def falling(period: int) -> np.ndarray:
        return forces_with_twist(geometry, 13e3 - FALL_PER_PERIOD_N * period)

    run_level(bench, falling)
    controller = bench.controller
    assert controller.phase is C2Phase.DONE
    # settle 10 s (the first settled period is the first LEVEL period after the LOC), then the
    # 1 s completion hold
    assert bench.t_s - start_s == pytest.approx(SETTLE_S + 1.0 + PERIOD_S, abs=1e-6)
    (event,) = relaxed_events(controller)
    twist_kN = float(event.split(":", 1)[1])
    assert 3.0 < twist_kN < 15.0
    meta = twist_meta(controller)
    assert meta["n_relaxed_done"] == 1
    assert meta["last_D_N"] / 1e3 == pytest.approx(twist_kN, abs=0.05)


def test_t2_without_relax_stays_in_level(geometry) -> None:
    bench = touched_bench(geometry, without_relax(bench_config()))
    run_level(bench, lambda _: forces_with_twist(geometry, RELAXED_TWIST_N), limit_s=20.0)
    assert bench.controller.phase is C2Phase.LEVEL
    assert relaxed_events(bench.controller) == []


def test_t3_twist_above_the_limit_is_not_relaxed(geometry) -> None:
    bench = touched_bench(geometry, bench_config())
    run_level(bench, lambda _: forces_with_twist(geometry, TOO_LARGE_TWIST_N), limit_s=20.0)
    assert bench.controller.phase is C2Phase.LEVEL
    assert relaxed_events(bench.controller) == []


def test_t4b_standing_twist_is_relaxed(geometry) -> None:
    """V2b: ``drop_N`` 0 accepts a twist load that does not change at all."""
    bench = touched_bench(geometry, bench_config())
    run_level(bench, lambda _: forces_with_twist(geometry, RELAXED_TWIST_N))
    assert bench.controller.phase is C2Phase.DONE
    assert len(relaxed_events(bench.controller)) == 1


def relax_verdicts(
    controller: C2Controller,
    geometry: C2Geometry,
    twist_at: Callable[[float], float],
    times_s: np.ndarray,
    *,
    is_on_target_at: Callable[[float], bool] = lambda _: True,
) -> dict[float, bool]:
    """``_is_twist_relax_ok`` by time over ``times_s`` with the clearance condition met."""
    verdicts = {}
    for t_s in times_s:
        t_s = float(t_s)
        twist_N = twist_at(t_s)
        reading = load_reading(t_s, forces_with_twist(geometry, twist_N))
        verdicts[t_s] = controller._is_twist_relax_ok(reading, twist_N, is_on_target_at(t_s), True)
    return verdicts


def load_reading(t_s: float, forces_N: np.ndarray) -> _Reading:
    strokes = np.full(4, 0.3)
    return _Reading(
        t_s=t_s,
        cylinder_force_N=forces_N,
        rod_stroke_m=strokes,
        motor_stroke_m=strokes,
        cylinder_force_lowpass_N=forces_N,
        cylinder_force_lower_N=forces_N,
        cylinder_force_upper_N=forces_N,
        head_only_force_N=forces_N,
    )


def level_controller_after_loc(geometry: C2Geometry) -> C2Controller:
    controller = C2Controller(geometry, bench_config())
    controller._state.phase = C2Phase.LEVEL
    controller._soil_state().is_liftoff_confirmed = True
    return controller


def period_times(end_s: float) -> np.ndarray:
    return np.round(np.arange(1, round(end_s / PERIOD_S) + 1) * PERIOD_S, 10)


@pytest.mark.parametrize(("bump_N", "is_relaxed"), [(700.0, False), (500.0, True)])
def test_t4a_rise_inside_the_window(geometry, bump_N, is_relaxed) -> None:
    """One sample ``bump_N`` above the standing ``|D|`` at 8 s: at 10.1 s (settled, window
    5.1 .. 10.1 s) a rise above the preset 0.6 kN (U-S8-80 (b)) blocks the relaxation; once the
    bump has left the window it is allowed again."""
    controller = level_controller_after_loc(geometry)

    def twist_with_bump(t_s: float) -> float:
        return RELAXED_TWIST_N + (bump_N if abs(t_s - 8.0) < TIME_TOLERANCE_S else 0.0)

    verdicts = relax_verdicts(controller, geometry, twist_with_bump, period_times(13.5))
    assert verdicts[10.1] is is_relaxed
    assert verdicts[13.1] is True


# --- T5 .. T8 conditions -------------------------------------------------------------------------


def test_t5_a_break_of_the_attitude_condition_restarts_the_settle_time(geometry) -> None:
    controller = level_controller_after_loc(geometry)
    state = controller._state
    verdicts = relax_verdicts(
        controller,
        geometry,
        lambda _: RELAXED_TWIST_N,
        period_times(25.0),
        is_on_target_at=lambda t_s: abs(t_s - 6.0) > TIME_TOLERANCE_S,
    )
    assert verdicts[6.0] is False
    assert verdicts[11.0] is False  # without the break: 0.1 s + 10 s
    assert verdicts[16.0] is False  # settled again since 6.1 s
    assert verdicts[16.1] is True
    assert state.twist_relax_settled_since_s == pytest.approx(6.1)
    assert state.twist_relax_history[0][0] == pytest.approx(25.0 - WINDOW_S)


def test_t5_relevel_and_touch_exit_clear_the_history(geometry) -> None:
    controller = level_controller_after_loc(geometry)
    relax_verdicts(controller, geometry, lambda _: RELAXED_TWIST_N, period_times(2.0))
    assert controller._state.twist_relax_settled_since_s is not None
    controller._start_relevel()
    assert controller._state.twist_relax_settled_since_s is None
    assert len(controller._state.twist_relax_history) == 0
    bench = touched_bench(geometry, bench_config())
    assert bench.controller._state.twist_relax_settled_since_s is None


def test_t6_no_relax_before_the_liftoff_confirmation(geometry) -> None:
    bench = touched_bench(geometry, bench_config(), force_liftoff=False)
    run_level(bench, lambda _: forces_with_twist(geometry, RELAXED_TWIST_N), limit_s=15.0)
    assert bench.controller.phase is C2Phase.LEVEL
    assert bench.controller._state.twist_relax_settled_since_s is None
    # the settle time starts at the LOC
    bench.controller._soil_state().is_liftoff_confirmed = True
    loc_s = bench.t_s
    run_level(bench, lambda _: forces_with_twist(geometry, RELAXED_TWIST_N))
    assert bench.controller.phase is C2Phase.DONE
    assert bench.t_s - loc_s == pytest.approx(SETTLE_S + 1.0 + PERIOD_S, abs=1e-6)


@pytest.mark.parametrize(
    ("margin_N", "phase"), [(-LOAD_MARGIN_N, "LEVEL"), (LOAD_MARGIN_N, "DONE")]
)
def test_t7_a_leg_below_F_min_blocks_the_relax(geometry, margin_N, phase) -> None:
    """RR reads ``F_min -/+ 0.5 kN`` (re-approach off, it would start below 1.4 ``F_min``)."""
    rr_force_N = geometry.F_min_N + margin_N
    forces = forces_with_twist(geometry, RELAXED_TWIST_N, {RR: rr_force_N})
    assert forces.min() == pytest.approx(rr_force_N)
    bench = touched_bench(geometry, bench_config(**NO_REAPPROACH))
    run_level(bench, lambda _: forces, limit_s=20.0)
    assert bench.controller.phase is C2Phase[phase]


def test_t7_load_check_can_be_turned_off(geometry) -> None:
    config = bench_config(**NO_REAPPROACH)
    relax = replace(config.twist_completion_relax, require_loads_ge_F_min=False)
    forces = forces_with_twist(geometry, RELAXED_TWIST_N, {RR: geometry.F_min_N - LOAD_MARGIN_N})
    bench = touched_bench(geometry, replace(config, twist_completion_relax=relax))
    run_level(bench, lambda _: forces, limit_s=20.0)
    assert bench.controller.phase is C2Phase.DONE


def test_t8_small_twist_keeps_the_plain_rule(geometry) -> None:
    """``|D|`` below 3 kN: DONE as before, without the event, and the same commands."""
    runs = []
    for config in (bench_config(), without_relax(bench_config())):
        bench = touched_bench(geometry, config)
        run_level(bench, lambda _: forces_with_twist(geometry, SMALL_TWIST_N))
        runs.append(bench)
    assert runs[0].controller.phase is C2Phase.DONE
    assert runs[0].t_s == runs[1].t_s
    np.testing.assert_array_equal(np.array(runs[0].outputs), np.array(runs[1].outputs))
    assert relaxed_events(runs[0].controller) == []
    assert twist_meta(runs[0].controller)["n_relaxed_done"] == 0
    # the history runs on while |D| is small (as the r73 harness)
    assert runs[0].controller._state.twist_relax_settled_since_s is not None
