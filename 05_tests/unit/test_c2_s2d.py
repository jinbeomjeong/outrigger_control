"""C2 S-2 soil-mode start deferral S2D (``06_analysis/02_control/verif_matrix/
s2_soil_defer_rules.md`` 1.2, appendix A.1 unit tests).

* settings: defaults (deferral off), validation (``ValueError``), old soil-state pickles,
* bit preservation: with the defaults the sink benches of ``test_c2_soil.py`` give the command
  and event digests of the code before S2D (commit 765b9fb); ``mode_defer_periods`` 0 given
  explicitly and the shadow record (S2D values + ``mode_defer_shadow``) give them too,
* entry: each failing condition (no tail, rise large, rise not falling, mean load low) starts
  the soil mode as before; all conditions true defers (latch held, no soil mode, event),
* end: the four expiry reasons and ``loc``; on expiry the S-4 push base is the deferral start,
* bench: during a deferral the latch stays held and no leg retracts (K-S4).
"""

from __future__ import annotations

import hashlib
import math
import pickle
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_c2_r8d1 import PERIOD_S  # same test folder
from test_c2_soil import (
    SinkBench,
    event_names,
    level_controller,
    reference_weight_N,
    soil_config,
    window_reading,
)

from outrigger_sim.control.c2 import (
    SOIL_EVENT_LIFTOFF_CONFIRMED,
    SOIL_EVENT_MODE_DEFER,
    SOIL_EVENT_MODE_DEFER_END,
    SOIL_EVENT_MODE_START,
    SOIL_MODE_SOURCE_EXPIRY,
    SOIL_MODE_SOURCE_RELEASE,
    C2Controller,
    C2Geometry,
    C2Phase,
    SoilDeferEnd,
    SoilResponseSettings,
    _SoilState,
)
from outrigger_sim.params import load_params

S2D_VALUES = {"mode_defer_periods": 5, "mode_defer_stroke_m": 0.006,
              "mode_defer_rise_factor": 4.0}
"""Rules 1.3 / 2: the S2D candidate."""
BASE_LOAD_FRACTION = 0.95
"""Sink benches: the load sum starts at 0.95 ``W_ref`` and saturates (exponential)."""
LOAD_SHAPES = {"defer_loc": (30e3, 0.008), "defer_periods": (60e3, 0.01),
               "rise_large": (80e3, 0.012)}
"""(amplitude N, length m): the release defers then LOC / defers then expires on ``periods`` /
rises more than 8 kN (no deferral)."""
PRE_S2D_DIGESTS_BY_ENV = {
    "dynamics-dev": {
        "defer_loc": "df7985a327cfbf2004a1e5d0587611ca216b17bc4239db52894d4fdd887a48f8",
        "defer_periods": "4f14d08a7274214f74c43feeebaf95159223787814468c5cf032eb4113880260",
        "rise_large": "cb702649ff52969e2c66c375eee19c7f605a4a5df087c1e8896c6e7dfc581e56",
        "pinned": "3c710a353e6c952f2131e29a5001c33edcae930dab07399d3b3aabb405ab6f56",
    },
    "Chrono-dev": {
        "defer_loc": "454d6abfd8036906d96368bed17e3ce57a3c2b218ee39052c3a314e8fa0c908f",
        "defer_periods": "1cd940325e29ae3d2654b01634fbd882ca136fb20a1a9ce5c32fcae941d699e0",
        "rise_large": "b357d487e5f245e7fced62c628f94716d2978652f088c10ee3b41a921ac15da9",
        "pinned": "8d25dc034f653f060cc5db2ffd50d8cb45d1be491b30f964cc18ce06dd3e10e4",
    },
}
"""sha256 of the applied commands (``float64`` bytes) and the ``(t_s, name)`` event list of each
bench with ``soil_config()``, computed with ``git archive 765b9fb 03_src 02_params`` (c2 before
S2D) on 2026-11-09. The digests depend on the env's BLAS (both envs run numpy 2.5.4 and still
differ), so they are kept per conda env; other envs skip the comparison with the old code."""
PRE_REV2_S2D_DIGESTS_BY_ENV = {
    "dynamics-dev": {
        "defer_loc": "ebdb7658bd24a02c384772b47647c141789b0ab67a4fd1885df92213e512b3c5",
        "defer_periods": "5e13658c15619160435fded1c301ee92cdcba61141c9d17418739e1a9728ffeb",
    },
    "Chrono-dev": {
        "defer_loc": "1ade85f3e3affc342ee980511f3711041ca1c656c94b2957322e23312f65bb36",
        "defer_periods": "d325d2c36ea87735c73e663fbca081d367073737c06431271004a59516800cb0",
    },
}
"""Digests (as :data:`PRE_S2D_DIGESTS_BY_ENV`) of the deferring benches with the S2D values,
computed with ``git archive aa86073 03_src 02_params 05_tests/unit`` (c2 before the rev2 start
history) on 2026-11-09, env ``python.exe`` called directly (``conda run -n dynamics-dev`` sets
the MKL threading layer and gives other digests)."""
BENCH_NAMES = ("defer_loc", "defer_periods", "rise_large", "pinned")
PINNED_START_FRACTION = 0.9
PINNED_LOAD_RATE_N_M = 0.6e6
BENCH_LIMIT_S = 60.0
START_T_S = 2.0
START_STROKE_M = 0.37
FALLING_RISES_N = (5000.0, 4500.0, 4000.0, 3500.0, 3000.0, 2500.0, 2200.0)
STROKE_STEP_M = 0.001


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


# --- benches ----------------------------------------------------------------------------------


def load_of(name: str, geometry: C2Geometry):
    weight = reference_weight_N(geometry)
    if name == "pinned":
        return lambda progress: PINNED_START_FRACTION * weight + PINNED_LOAD_RATE_N_M * progress
    amplitude_N, length_m = LOAD_SHAPES[name]
    return lambda progress: BASE_LOAD_FRACTION * weight + amplitude_N * (
        1.0 - math.exp(-max(progress, 0.0) / length_m))


def run_bench(geometry: C2Geometry, name: str, **soil_changes) -> tuple[SinkBench, list[bool]]:
    """Run to READY / FAULT; also returns the latch state after each period."""
    bench = SinkBench.touching(geometry, soil_config(**soil_changes), load_of(name, geometry))
    controller = bench.controller
    latches = []
    while controller.phase not in (C2Phase.READY, C2Phase.FAULT) and bench.t_s < BENCH_LIMIT_S:
        bench.step()
        latches.append(bool(controller._state.in_crawler_zone))
    return bench, latches


def bench_digest(bench: SinkBench) -> str:
    digest = hashlib.sha256(np.array(bench.outputs).tobytes())
    events = [(event.t_s, event.name) for event in bench.controller.events]
    digest.update(repr(events).encode())
    return digest.hexdigest()


def pre_s2d_digest(name: str, stored: dict = PRE_S2D_DIGESTS_BY_ENV) -> str:
    """The stored digest of this conda env (skips in an env without stored digests)."""
    env_name = Path(sys.prefix).name
    digests = stored.get(env_name)
    if digests is None:
        pytest.skip(f"no stored bench digests for env {env_name!r}")
    return digests[name]


@pytest.mark.parametrize("name", BENCH_NAMES)
def test_defaults_are_bit_identical_to_the_code_before_s2d(geometry, name) -> None:
    bench, _ = run_bench(geometry, name)
    assert bench_digest(bench) == pre_s2d_digest(name)


@pytest.mark.parametrize("name", BENCH_NAMES)
def test_explicit_zero_and_the_shadow_record_are_bit_identical(geometry, name) -> None:
    """Env independent: N_d 0 given explicitly and the shadow record equal the defaults."""
    default, _ = run_bench(geometry, name)
    zero, _ = run_bench(geometry, name, mode_defer_periods=0)
    shadow, _ = run_bench(geometry, name, mode_defer_shadow=True, **S2D_VALUES)
    assert bench_digest(zero) == bench_digest(default)
    assert bench_digest(shadow) == bench_digest(default)
    assert event_names(shadow.controller, SOIL_EVENT_MODE_DEFER) == []


@pytest.mark.parametrize("name", ("defer_loc", "defer_periods"))
def test_the_start_history_keeps_the_s2d_commands(geometry, name) -> None:
    """rev2 RS2-6: the start / deferral history is record only; with the deferral acting the
    commands and events are those of the code before it."""
    bench, _ = run_bench(geometry, name, **S2D_VALUES)
    assert bench_digest(bench) == pre_s2d_digest(name, PRE_REV2_S2D_DIGESTS_BY_ENV)
    meta = bench.controller.meta()["soil"]
    assert len(meta["deferrals"]) == 1 and meta["deferrals"][0] == meta["defer"]["deferral"]


def test_the_shadow_record_names_the_deferral_it_would_have_made(geometry) -> None:
    bench, _ = run_bench(geometry, "defer_periods", mode_defer_shadow=True, **S2D_VALUES)
    defer = bench.controller.meta()["soil"]["defer"]
    (check,) = defer["checks"]
    assert check["entered"] and check["shadow"] and check["failures"] == []
    assert defer["deferral"] is None
    assert defer["shadow"]["start_s"] == pytest.approx(check["t_s"])
    assert defer["shadow"]["end_reason"] is not None
    (soil_start_s,) = [event.t_s for event in bench.controller.events
                       if event.name == SOIL_EVENT_MODE_START]
    assert soil_start_s == pytest.approx(check["t_s"])  # the soil mode itself is not deferred
    meta = bench.controller.meta()["soil"]
    assert meta["deferrals"] == []  # the history holds acting deferrals only
    (start,) = meta["mode_starts"]
    assert start["t_s"] == soil_start_s and start["source"] == SOIL_MODE_SOURCE_RELEASE


# --- settings ---------------------------------------------------------------------------------


def test_settings_defaults_mean_no_deferral() -> None:
    settings = SoilResponseSettings()
    assert settings.mode_defer_periods == 0
    assert settings.mode_defer_stroke_m == 0.0
    assert settings.mode_defer_rise_factor == 4.0
    assert settings.mode_defer_shadow is False
    meta = settings.to_meta()
    assert meta["mode_defer_periods"] == 0 and meta["mode_defer_shadow"] is False


@pytest.mark.parametrize(
    "changes",
    [{"mode_defer_periods": -1}, {"mode_defer_periods": 2.0}, {"mode_defer_periods": True},
     {"mode_defer_periods": "5"}, {"mode_defer_stroke_m": -0.001},
     {"mode_defer_stroke_m": math.nan}, {"mode_defer_rise_factor": 0.0},
     {"mode_defer_rise_factor": -4.0}, {"mode_defer_shadow": 1}],
)
def test_invalid_settings_raise(changes) -> None:
    with pytest.raises(ValueError):
        SoilResponseSettings(**changes)


def test_old_soil_state_pickle_reads_no_deferral() -> None:
    soil = _SoilState()
    for name in ("window_t_s", "last_tail_ok", "last_rise_N", "prev_rise_N",
                 "last_tail_mean_load_N", "defer", "shadow_defer", "defer_checks"):
        del soil.__dict__[name]
    restored = pickle.loads(pickle.dumps(soil))
    assert restored.defer is None and restored.shadow_defer is None
    assert restored.last_tail_ok is False and restored.defer_checks == ()


# --- direct calls: entry and end --------------------------------------------------------------


def released_controller(geometry: C2Geometry, **soil_changes) -> C2Controller:
    """LEVEL, latch released before the LOC (the S-2 branch of the next hold call)."""
    controller = level_controller(geometry, **{**S2D_VALUES, **soil_changes})
    controller._state.in_crawler_zone = False
    return controller


def set_window(controller: C2Controller, t_s: float, rise_N: float | None,
               prev_rise_N: float | None, load_fraction: float = 1.0) -> None:
    """This period's S-1 window values as ``_update_liftoff_window`` leaves them."""
    soil = controller._soil_state()
    soil.window_t_s = float(t_s)
    soil.last_tail_ok = rise_N is not None
    soil.last_rise_N = rise_N
    soil.prev_rise_N = prev_rise_N
    weight = reference_weight_N(controller.geometry)
    soil.last_tail_mean_load_N = None if rise_N is None else load_fraction * weight


def hold(controller: C2Controller, t_s: float, mean_stroke_m: float) -> None:
    reading = window_reading(controller.geometry, t_s, mean_stroke_m, 0.0)
    # window_reading adds the operating strokes; shift so the mean is mean_stroke_m.
    shift = mean_stroke_m - float(np.mean(reading.motor_stroke_m))
    reading = replace(reading, motor_stroke_m=reading.motor_stroke_m + shift,
                      rod_stroke_m=reading.rod_stroke_m + shift)
    controller._hold_crawler_zone_until_liftoff(reading)


def enter(controller: C2Controller) -> None:
    set_window(controller, START_T_S, FALLING_RISES_N[1], FALLING_RISES_N[0])
    hold(controller, START_T_S, START_STROKE_M)


@pytest.mark.parametrize(
    ("rise_N", "prev_rise_N", "load_fraction", "failure"),
    [(None, None, 1.0, "no_tail"), (8000.1, 9000.0, 1.0, "rise_large"),
     (3500.0, 3000.0, 1.0, "rise_not_falling"), (3000.0, 3000.0, 1.0, "rise_not_falling"),
     (3000.0, None, 1.0, "rise_not_falling"), (3000.0, 4000.0, 0.849, "load_low")],
)
def test_a_failing_entry_condition_starts_the_soil_mode(
    geometry, rise_N, prev_rise_N, load_fraction, failure
) -> None:
    controller = released_controller(geometry)
    set_window(controller, START_T_S, rise_N, prev_rise_N, load_fraction)
    hold(controller, START_T_S, START_STROKE_M)
    soil = controller._soil_state()
    assert soil.is_soil_mode and soil.soil_mode_start_s == START_T_S
    assert soil.soil_mode_start_stroke_m == pytest.approx(START_STROKE_M)
    assert soil.defer is None
    (check,) = soil.defer_checks
    assert check["entered"] is False and failure in check["failures"]
    assert event_names(controller, SOIL_EVENT_MODE_DEFER) == []


def test_entry_conditions_at_their_limits_defer(geometry) -> None:
    controller = released_controller(geometry)
    set_window(controller, START_T_S, 8000.0, 8000.5, 0.85)  # R = k_d R_0, L = 0.85 W
    hold(controller, START_T_S, START_STROKE_M)
    soil = controller._soil_state()
    assert soil.defer is not None and not soil.is_soil_mode


def test_entry_record_keeps_the_rise_delta(geometry) -> None:
    """rev1 RS1-3: ``rise_delta_N`` = R_k - R_{k-1} (None without R_{k-1}), record only."""
    controller = released_controller(geometry)
    set_window(controller, START_T_S, 8000.0, 8000.5, 0.85)
    hold(controller, START_T_S, START_STROKE_M)
    (check,) = controller._soil_state().defer_checks
    assert check["rise_delta_N"] == pytest.approx(-0.5)
    no_previous = released_controller(geometry)
    set_window(no_previous, START_T_S, 3000.0, None)
    hold(no_previous, START_T_S, START_STROKE_M)
    (check,) = no_previous._soil_state().defer_checks
    assert check["rise_delta_N"] is None


def test_entry_holds_the_latch_without_soil_mode(geometry) -> None:
    controller = released_controller(geometry)
    enter(controller)
    soil = controller._soil_state()
    assert controller._state.in_crawler_zone is True
    assert not soil.is_soil_mode and soil.soil_mode_start_s is None
    assert not controller._is_in_soil_mode() and not controller._has_soil_mode_started()
    assert soil.defer.start_s == START_T_S and soil.defer.periods == 1
    assert event_names(controller, SOIL_EVENT_MODE_DEFER) == [SOIL_EVENT_MODE_DEFER]


def test_zero_periods_never_defer(geometry) -> None:
    controller = released_controller(geometry, mode_defer_periods=0)
    enter(controller)
    soil = controller._soil_state()
    assert soil.is_soil_mode and soil.defer is None and soil.defer_checks == ()


def continue_falling(controller: C2Controller, periods: int, stroke_step_m: float) -> float:
    """``periods`` more deferral periods with a falling rise; returns the last time."""
    t_s = START_T_S
    for index in range(periods):
        t_s = round(START_T_S + (index + 1) * PERIOD_S, 10)
        set_window(controller, t_s, FALLING_RISES_N[index + 2], FALLING_RISES_N[index + 1])
        hold(controller, t_s, START_STROKE_M + (index + 1) * stroke_step_m)
    return t_s


def assert_expired(controller: C2Controller, t_s: float, reason: SoilDeferEnd) -> None:
    soil = controller._soil_state()
    assert soil.defer.end_reason is reason and soil.defer.end_s == pytest.approx(t_s)
    assert soil.is_soil_mode and soil.soil_mode_start_s == pytest.approx(t_s)
    assert soil.soil_mode_start_stroke_m == START_STROKE_M  # S-4 base = deferral start
    assert controller._state.in_crawler_zone is True
    assert event_names(controller, SOIL_EVENT_MODE_DEFER_END) == [
        f"{SOIL_EVENT_MODE_DEFER_END}:{reason}"]
    (start,) = [event for event in controller.events if event.name == SOIL_EVENT_MODE_START]
    assert start.t_s == pytest.approx(t_s)


def test_expiry_after_the_period_limit(geometry) -> None:
    controller = released_controller(geometry)
    enter(controller)
    continue_falling(controller, 4, STROKE_STEP_M)
    soil = controller._soil_state()
    assert soil.defer.is_active and soil.defer.periods == 5 and not soil.is_soil_mode
    expiry_s = round(START_T_S + 5 * PERIOD_S, 10)
    set_window(controller, expiry_s, FALLING_RISES_N[6], FALLING_RISES_N[5])
    hold(controller, expiry_s, START_STROKE_M + 5 * STROKE_STEP_M)
    assert_expired(controller, expiry_s, SoilDeferEnd.PERIODS)
    assert expiry_s - START_T_S <= 0.5 + 1e-9  # Q-S3 bound


def test_expiry_on_the_stroke_progress_and_s4_push_from_the_deferral_start(geometry) -> None:
    controller = released_controller(geometry)
    enter(controller)
    t_s = START_T_S + PERIOD_S
    set_window(controller, t_s, FALLING_RISES_N[2], FALLING_RISES_N[1])
    hold(controller, t_s, START_STROKE_M + S2D_VALUES["mode_defer_stroke_m"])
    assert_expired(controller, t_s, SoilDeferEnd.STROKE)
    assert controller._soil_state().push_m == pytest.approx(S2D_VALUES["mode_defer_stroke_m"])


def test_s4_fault_counts_the_deferral_stroke(geometry) -> None:
    controller = released_controller(geometry, max_push_m=0.005)
    enter(controller)
    t_s = START_T_S + PERIOD_S
    set_window(controller, t_s, FALLING_RISES_N[2], FALLING_RISES_N[1])
    hold(controller, t_s, START_STROKE_M + S2D_VALUES["mode_defer_stroke_m"])
    assert controller._state.phase is C2Phase.FAULT


@pytest.mark.parametrize(("rise_N", "prev_rise_N"), [(4500.0, 4500.0), (4600.0, 4500.0),
                                                      (8000.5, 9000.0)])
def test_expiry_on_a_growing_or_large_rise(geometry, rise_N, prev_rise_N) -> None:
    controller = released_controller(geometry)
    enter(controller)
    t_s = START_T_S + PERIOD_S
    set_window(controller, t_s, rise_N, prev_rise_N)
    hold(controller, t_s, START_STROKE_M + STROKE_STEP_M)
    assert_expired(controller, t_s, SoilDeferEnd.RISE)


def test_expiry_on_a_missing_window_tail(geometry) -> None:
    controller = released_controller(geometry)
    enter(controller)
    t_s = START_T_S + PERIOD_S
    set_window(controller, t_s, None, None)
    hold(controller, t_s, START_STROKE_M + STROKE_STEP_M)
    assert_expired(controller, t_s, SoilDeferEnd.WINDOW)


def test_window_values_of_another_period_count_as_no_tail(geometry) -> None:
    controller = released_controller(geometry)
    enter(controller)
    t_s = START_T_S + PERIOD_S  # the window was not updated in this period
    hold(controller, t_s, START_STROKE_M + STROKE_STEP_M)
    assert_expired(controller, t_s, SoilDeferEnd.WINDOW)


def test_the_loc_ends_the_deferral_without_soil_mode(geometry) -> None:
    controller = released_controller(geometry)
    enter(controller)
    continue_falling(controller, 2, STROKE_STEP_M)
    controller._soil_state().is_liftoff_confirmed = True
    t_loc = START_T_S + 3 * PERIOD_S
    hold(controller, t_loc, START_STROKE_M + 3 * STROKE_STEP_M)
    soil = controller._soil_state()
    assert soil.defer.end_reason is SoilDeferEnd.LOC and soil.defer.periods == 3
    assert not soil.is_soil_mode and soil.soil_mode_start_s is None
    assert event_names(controller, SOIL_EVENT_MODE_DEFER_END) == [
        f"{SOIL_EVENT_MODE_DEFER_END}:loc"]
    hold(controller, t_loc + PERIOD_S, START_STROKE_M)  # later periods: nothing more
    assert len(event_names(controller, SOIL_EVENT_MODE_DEFER_END)) == 1


def test_window_record_keeps_the_previous_rise_only_for_the_previous_period(geometry) -> None:
    controller = level_controller(geometry)
    soil = controller._soil_state()
    soil.window_t_s, soil.last_tail_ok, soil.last_rise_N = 1.0, True, 3000.0
    controller._start_window_record(1.1)
    assert soil.prev_rise_N == 3000.0 and soil.last_rise_N is None and not soil.last_tail_ok
    soil.last_tail_ok, soil.last_rise_N = True, 2500.0
    controller._start_window_record(1.5)  # four periods later
    assert soil.prev_rise_N is None


# --- rev2 RS2-1: start and deferral history ---------------------------------------------------


def history(controller: C2Controller) -> tuple[list[dict], list[dict]]:
    meta = controller.meta()["soil"]
    return meta["mode_starts"], meta["deferrals"]


def count_named(controller: C2Controller, name: str) -> int:
    """Events named exactly ``name`` (``event_names`` matches by prefix)."""
    return sum(1 for event in controller.events if event.name == name)


def expire_on_periods(controller: C2Controller) -> float:
    """Enter at ``START_T_S`` and expire on ``periods``; returns the expiry time."""
    enter(controller)
    continue_falling(controller, 4, STROKE_STEP_M)
    expiry_s = round(START_T_S + 5 * PERIOD_S, 10)
    set_window(controller, expiry_s, FALLING_RISES_N[6], FALLING_RISES_N[5])
    hold(controller, expiry_s, START_STROKE_M + 5 * STROKE_STEP_M)
    return expiry_s


def confirm_and_revoke(controller: C2Controller, t_s: float) -> None:
    """A LOC, then the P-S8-33 revocation (soil state back to "no LOC", no soil mode)."""
    controller._soil_state().is_liftoff_confirmed = True
    controller._revoke_loc(t_s, 5e3)
    controller._state.in_crawler_zone = False  # the latch releases again before a new LOC


def test_a_release_start_is_recorded(geometry) -> None:
    controller = released_controller(geometry)
    set_window(controller, START_T_S, None, None)  # no tail: soil mode at the release
    hold(controller, START_T_S, START_STROKE_M)
    starts, deferrals = history(controller)
    (start,) = starts
    assert start["t_s"] == START_T_S and start["source"] == SOIL_MODE_SOURCE_RELEASE
    assert start["push_base_stroke_m"] == controller._soil_state().soil_mode_start_stroke_m
    assert deferrals == []


def test_expiry_revoke_release_restart_keeps_the_history(geometry) -> None:
    """The stalled S-D case (rev2 RS2-0): expiry, LOC revocation, release restart. The meta's
    last push base is the restart's; the history keeps the expiry start with the deferral
    start stroke (K-S5 reads it)."""
    controller = released_controller(geometry)
    expiry_s = expire_on_periods(controller)
    revoke_s = expiry_s + 2.4
    confirm_and_revoke(controller, revoke_s)
    restart_s = round(revoke_s + 0.6, 10)
    restart_stroke_m = START_STROKE_M + 0.047
    set_window(controller, restart_s, None, None)  # window emptied by the revocation
    hold(controller, restart_s, restart_stroke_m)
    starts, deferrals = history(controller)
    assert [start["source"] for start in starts] == [SOIL_MODE_SOURCE_EXPIRY,
                                                    SOIL_MODE_SOURCE_RELEASE]
    (deferral,) = deferrals
    assert deferral["end_reason"] == "periods" and deferral["periods"] == 5
    assert starts[0]["t_s"] == deferral["end_s"] == expiry_s
    assert starts[0]["push_base_stroke_m"] == deferral["start_stroke_m"] == START_STROKE_M
    assert starts[1]["t_s"] == restart_s
    assert starts[1]["push_base_stroke_m"] == pytest.approx(restart_stroke_m)
    meta = controller.meta()["soil"]
    assert meta["soil_mode_start_stroke_m"] == starts[1]["push_base_stroke_m"]  # last value
    assert len(event_names(controller, SOIL_EVENT_MODE_START)) == len(starts)
    assert count_named(controller, SOIL_EVENT_MODE_DEFER) == len(deferrals)
    entry_check = controller._soil_state().defer_checks[-1]
    assert entry_check["failures"] == ["no_tail"]  # the restart re-evaluated the entry


def test_expiry_revoke_reentry_expiry_records_both_deferrals(geometry) -> None:
    """Re-entry after a revocation (rev2 RS2-2): a second deferral and a second expiry start,
    each with its own deferral start stroke."""
    controller = released_controller(geometry)
    expiry_s = expire_on_periods(controller)
    confirm_and_revoke(controller, expiry_s + 2.4)
    reentry_s = round(expiry_s + 3.0, 10)
    second_stroke_m = START_STROKE_M + 0.047
    set_window(controller, reentry_s, FALLING_RISES_N[1], FALLING_RISES_N[0])
    hold(controller, reentry_s, second_stroke_m)
    soil = controller._soil_state()
    assert soil.defer.is_active and not soil.is_soil_mode
    end_s = round(reentry_s + PERIOD_S, 10)
    set_window(controller, end_s, 4600.0, 4500.0)  # growing rise
    hold(controller, end_s, second_stroke_m + STROKE_STEP_M)
    starts, deferrals = history(controller)
    assert [deferral["end_reason"] for deferral in deferrals] == ["periods", "rise"]
    assert [start["source"] for start in starts] == [SOIL_MODE_SOURCE_EXPIRY] * 2
    for start, deferral in zip(starts, deferrals, strict=True):
        assert start["t_s"] == deferral["end_s"]
        assert start["push_base_stroke_m"] == deferral["start_stroke_m"]
    assert deferrals[1]["start_stroke_m"] == pytest.approx(second_stroke_m)
    assert deferrals[1]["rise_delta_N"] == FALLING_RISES_N[1] - FALLING_RISES_N[0]
    assert count_named(controller, SOIL_EVENT_MODE_DEFER) == 2


def test_the_history_survives_a_new_lifting_cycle(geometry) -> None:
    """The soil state is replaced at TOUCH entry (P-S9-6); the run history is not."""
    controller = released_controller(geometry)
    expire_on_periods(controller)
    controller._state.soil = _SoilState()
    starts, deferrals = history(controller)
    assert len(starts) == 1 and len(deferrals) == 1
    assert controller.meta()["soil"]["soil_mode_t_s"] is None


def test_old_run_state_pickle_reads_an_empty_history(geometry) -> None:
    controller = level_controller(geometry)
    state = controller._state
    for name in ("soil_mode_starts", "soil_deferrals"):
        state.__dict__.pop(name, None)
    restored = pickle.loads(pickle.dumps(state))
    assert restored.soil_mode_starts == () and restored.soil_deferrals == ()


# --- benches: the deferral acting -------------------------------------------------------------


def deferral_periods(bench: SinkBench, meta: dict) -> list[int]:
    deferral = meta["defer"]["deferral"]
    end_s = deferral["end_s"]
    return [index for index, t_s in enumerate(bench.times_s)
            if deferral["start_s"] - 1e-9 <= t_s and (end_s is None or t_s < end_s - 1e-9)]


@pytest.mark.parametrize(("name", "reason"), [("defer_loc", "loc"),
                                              ("defer_periods", "periods")])
def test_bench_deferral_holds_the_latch_and_retracts_no_leg(geometry, name, reason) -> None:
    bench, latches = run_bench(geometry, name, **S2D_VALUES)
    controller = bench.controller
    assert controller.phase is C2Phase.READY
    meta = controller.meta()["soil"]
    assert meta["defer"]["deferral"]["end_reason"] == reason
    periods = deferral_periods(bench, meta)
    assert len(periods) == meta["defer"]["deferral"]["periods"]
    assert all(latches[index] for index in periods)
    assert min(float(np.min(bench.outputs[index])) for index in periods) >= 0.0
    if reason == "loc":
        assert meta["soil_mode_t_s"] is None
        assert event_names(controller, SOIL_EVENT_LIFTOFF_CONFIRMED)
    else:
        deferral = meta["defer"]["deferral"]
        assert meta["soil_mode_t_s"] == pytest.approx(deferral["end_s"])
        assert meta["soil_mode_start_stroke_m"] == deferral["start_stroke_m"]
        assert deferral["end_s"] - deferral["start_s"] <= 0.5 + 1e-9


def test_bench_without_entry_is_unchanged_by_s2d(geometry) -> None:
    """K-S2 on a bench: no deferral entry (rise above 8 kN) -> the pre-S2D commands.

    The pinned bench is not used here: its rise is constant up to rounding, so the strict
    "falling" condition can hold by a few ulp and the release may defer.
    """
    default, _ = run_bench(geometry, "rise_large")
    bench, _ = run_bench(geometry, "rise_large", **S2D_VALUES)
    assert bench.controller.meta()["soil"]["defer"]["checks"][0]["entered"] is False
    assert bench_digest(bench) == bench_digest(default)
