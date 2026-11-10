"""K-2: TOUCH latch on a load window with a slow creep (control-expert design, 2026-11-10).

Synthetic 10 Hz benches of ``test_c2_r8d1.py`` (pressure judge: the touchdown load is the
reading and ``touch_seen`` latches on one sample). The bench strokes do not follow the
commands; the stroke-cap test moves them by hand. The increment limit is off in the creep
benches, so the computed command is the TOUCH speed of the period.
"""

from __future__ import annotations

import argparse
import pickle
from dataclasses import replace

import numpy as np
import pytest
from test_c2_r8d1 import (  # same test folder
    FL,
    STEADY_LOAD_N,
    TOUCH_HOLD_SAMPLES,
    Bench,
    bench_config,
    computed_command,
    operating_strokes,
)

from outrigger_sim.control import touch_creep_option
from outrigger_sim.control.c2 import (
    TOUCH_CREEP_CAP_EVENT,
    TOUCH_CREEP_LATCH_EVENT,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    TouchCreepLatchSettings,
)
from outrigger_sim.hydraulics import v5_options
from outrigger_sim.params import load_params

CREEP_FRACTION = 0.05
LATCH_WINDOW = 5
CAP_M = 0.015
AIRBORNE_LOAD_N = 1.0e3
"""Below the touchdown level (1.5 ``F_min``): the leg has not touched."""
AIRBORNE_SAMPLES = 2


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def creep_config(*, is_on: bool = True) -> C2Config:
    config = bench_config(increment_limit=None)
    return replace(config, touch_creep_latch=TouchCreepLatchSettings(enable=is_on))


def creep_bench(geometry: C2Geometry, *, is_on: bool = True) -> Bench:
    """A bench in TOUCH after a few airborne samples on every leg."""
    bench = Bench(C2Controller(geometry, creep_config(is_on=is_on)), geometry,
                  operating_strokes(geometry))
    for _ in range(AIRBORNE_SAMPLES):
        bench.step(np.full(4, AIRBORNE_LOAD_N))
    assert bench.controller.phase is C2Phase.TOUCH
    return bench


def forces_with_fl(fl_load_N: float) -> np.ndarray:
    forces = np.full(4, STEADY_LOAD_N)
    forces[FL] = fl_load_N
    return forces


def step_fl_loads(bench: Bench, fl_loads_N) -> list[np.ndarray]:
    commands = []
    for load_N in fl_loads_N:
        bench.step(forces_with_fl(load_N))
        commands.append(computed_command(bench.controller))
    return commands


def creep_speed(geometry: C2Geometry) -> float:
    return CREEP_FRACTION * geometry.max_speed_m_s


def latches_of(controller: C2Controller) -> dict[str, dict]:
    return {latch["leg"]: latch for latch in controller.meta()["touch_creep_latch"]["latches"]}


# --- settings ------------------------------------------------------------------------------------


def test_off_by_default_and_in_the_preset() -> None:
    assert C2Config().touch_creep_latch == TouchCreepLatchSettings()
    assert C2Config.touch_creep_latch == TouchCreepLatchSettings()  # class attribute (old pickles)
    assert C2Config().touch_creep_latch.enable is False
    assert C2Config().with_10hz_d1().touch_creep_latch == TouchCreepLatchSettings()
    settings = TouchCreepLatchSettings()
    assert (settings.creep_frac, settings.latch_window, settings.cap_m) == (
        CREEP_FRACTION, LATCH_WINDOW, CAP_M)
    assert (settings.latch_mean_factor, settings.latch_min_factor) == (1.5, 1.0)


def test_preset_keyword_turns_only_the_latch_on() -> None:
    """K2-8: ``with_10hz_d1(touch_creep_latch=False)`` is the preset; ``True`` the K-2 arm."""
    preset = C2Config().with_10hz_d1()
    assert C2Config().with_10hz_d1(touch_creep_latch=False) == preset
    k2 = C2Config().with_10hz_d1(touch_creep_latch=True)
    assert k2.touch_creep_latch == TouchCreepLatchSettings(enable=True)
    assert replace(k2, touch_creep_latch=TouchCreepLatchSettings()) == preset


def test_config_pickled_before_k2_reads_off() -> None:
    older_config = pickle.loads(pickle.dumps(C2Config()))
    object.__delattr__(older_config, "touch_creep_latch")
    assert older_config.touch_creep_latch.enable is False


@pytest.mark.parametrize("bad", [
    {"creep_frac": 0.0}, {"creep_frac": 1.5}, {"latch_window": 0}, {"latch_window": 2.0},
    {"latch_window": True}, {"latch_mean_factor": -1.0}, {"latch_min_factor": -0.1},
    {"cap_m": 0.0},
])
def test_bad_settings_are_refused(bad) -> None:
    with pytest.raises(ValueError):
        TouchCreepLatchSettings(**bad)


def test_meta_has_the_block_with_the_rule_off(geometry) -> None:
    bench = Bench(C2Controller(geometry, bench_config()), geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    meta = bench.controller.meta()["touch_creep_latch"]
    assert meta["settings"]["enable"] is False
    assert meta["latches"] == []


# --- the rule ------------------------------------------------------------------------------------


def test_first_contact_sample_creeps_instead_of_stopping(geometry) -> None:
    """Off: a candidate stops on its first touchdown sample. On: it creeps at 0.05 v_max."""
    bench_off = creep_bench(geometry, is_on=False)
    bench_off.step(np.full(4, STEADY_LOAD_N))
    np.testing.assert_array_equal(computed_command(bench_off.controller), np.zeros(4))
    bench_on = creep_bench(geometry)
    bench_on.step(np.full(4, STEADY_LOAD_N))
    np.testing.assert_allclose(computed_command(bench_on.controller),
                               np.full(4, creep_speed(geometry)), rtol=0, atol=1e-15)


def test_window_latch_and_level_entry(geometry) -> None:
    """Five touchdown samples above both levels latch every leg: TOUCH -> LEVEL one sample
    earlier than the 0.5 s hold (six samples)."""
    bench = creep_bench(geometry)
    for _ in range(LATCH_WINDOW - 1):
        bench.step(np.full(4, STEADY_LOAD_N))
        assert bench.controller.phase is C2Phase.TOUCH
    bench.step(np.full(4, STEADY_LOAD_N))
    assert bench.controller.phase is C2Phase.LEVEL
    latches = latches_of(bench.controller)
    assert set(latches) == {"FL", "FR", "RL", "RR"}
    assert {latch["reason"] for latch in latches.values()} == {"load_window"}
    assert latches["FL"]["window_mean_N"] == pytest.approx(STEADY_LOAD_N)
    names = [event.name for event in bench.controller.events]
    for leg in ("FL", "FR", "RL", "RR"):  # T-K2-6
        assert names.count(f"{TOUCH_CREEP_LATCH_EVENT}:{leg}") == 1
    assert not [name for name in names if name.startswith("INFO_TOUCH_DIP_HELD")]


def test_four_samples_do_not_latch(geometry) -> None:
    """T-K2-3: a window of four samples never latches, whatever the loads."""
    bench = Bench(C2Controller(geometry, creep_config()), geometry, operating_strokes(geometry))
    for _ in range(LATCH_WINDOW - 1):
        bench.step(np.full(4, STEADY_LOAD_N))
    assert latches_of(bench.controller) == {}
    bench.step(np.full(4, STEADY_LOAD_N))
    assert set(latches_of(bench.controller)) == {"FL", "FR", "RL", "RR"}


@pytest.mark.parametrize(("offset_N", "is_latched"), [(1.0, True), (-1.0, False)])
def test_window_mean_boundary(geometry, offset_N, is_latched) -> None:
    """T-K2-3: a window mean 1 N above 1.5 F_min latches, 1 N below does not."""
    F_min_N = geometry.F_min_N
    first_N = 1.6 * F_min_N  # sets touch_seen
    rest_N = (5 * (1.5 * F_min_N + offset_N) - first_N) / 4
    bench = creep_bench(geometry)  # earlier windows hold an airborne sample (minimum fails)
    step_fl_loads(bench, [first_N, rest_N, rest_N, rest_N, rest_N])
    assert ("FL" in latches_of(bench.controller)) is is_latched


@pytest.mark.parametrize(("offset_N", "is_latched"), [(0.0, True), (-1.0, False)])
def test_window_minimum_boundary(geometry, offset_N, is_latched) -> None:
    """T-K2-3: a window minimum of exactly 1.0 F_min latches, 1 N below does not."""
    F_min_N = geometry.F_min_N
    bench = creep_bench(geometry)
    step_fl_loads(bench, [3.0 * F_min_N] * 4 + [F_min_N + offset_N])
    assert ("FL" in latches_of(bench.controller)) is is_latched


def test_creep_speed_holds_in_a_dip(geometry) -> None:
    """T-K2-3: a touch_seen leg keeps v_cr on a sample below the touchdown level."""
    F_min_N = geometry.F_min_N
    bench = creep_bench(geometry)
    commands = step_fl_loads(bench, np.array([2.0, 0.2, 0.2]) * F_min_N)
    for command in commands:
        assert command[FL] == pytest.approx(creep_speed(geometry))


def test_latch_needs_the_window_minimum(geometry) -> None:
    """Mean above 1.5 F_min with one sample below F_min: no latch until that sample leaves."""
    F_min_N = geometry.F_min_N
    bench = creep_bench(geometry)
    commands = step_fl_loads(bench, np.array([3.0, 3.0, 0.5, 3.0, 3.0]) * F_min_N)
    assert "FL" not in latches_of(bench.controller)
    assert commands[-1][FL] == pytest.approx(creep_speed(geometry))
    step_fl_loads(bench, np.array([3.0, 3.0]) * F_min_N)
    assert "FL" not in latches_of(bench.controller)  # the 0.5 F_min sample is still inside
    step_fl_loads(bench, [3.0 * F_min_N])
    assert latches_of(bench.controller)["FL"]["reason"] == "load_window"


def test_latch_needs_the_window_mean(geometry) -> None:
    F_min_N = geometry.F_min_N
    bench = creep_bench(geometry)
    commands = step_fl_loads(bench, np.array([1.6, 1.4, 1.4, 1.4, 1.4, 1.4]) * F_min_N)
    assert "FL" not in latches_of(bench.controller)
    assert commands[-1][FL] == pytest.approx(creep_speed(geometry))


def test_leg_latches_inside_a_dip(geometry) -> None:
    """Three samples below the touchdown level (beyond the two of P-S8-27) still latch."""
    F_min_N = geometry.F_min_N
    bench = creep_bench(geometry)
    step_fl_loads(bench, np.array([2.3, 1.2, 1.1, 1.2, 2.3]) * F_min_N)
    latch = latches_of(bench.controller)["FL"]
    assert latch["reason"] == "load_window"
    assert latch["window_min_N"] == pytest.approx(1.1 * F_min_N)
    assert bench.controller.phase is C2Phase.LEVEL


def test_latched_leg_stops_and_the_others_creep(geometry) -> None:
    F_min_N = geometry.F_min_N
    bench = creep_bench(geometry)
    forces = np.array([3.0, 1.4, 1.4, 1.4]) * F_min_N
    forces[1:] = [1.6 * F_min_N] * 3  # seen, then held below the mean level
    bench.step(forces)
    low = np.array([3.0, 1.4, 1.4, 1.4]) * F_min_N
    for _ in range(LATCH_WINDOW - 1):
        bench.step(low)
    assert set(latches_of(bench.controller)) == {"FL"}
    command = computed_command(bench.controller)
    assert command[FL] == 0.0
    np.testing.assert_allclose(command[1:], creep_speed(geometry), rtol=0, atol=1e-15)
    bench.step(low)
    assert computed_command(bench.controller)[FL] == 0.0


def test_stroke_cap_latches_with_an_event(geometry) -> None:
    F_min_N = geometry.F_min_N
    bench = creep_bench(geometry)
    step_fl_loads(bench, [1.6 * F_min_N])  # touch_seen: the cap reference stroke
    step_fl_loads(bench, [1.2 * F_min_N])
    assert "FL" not in latches_of(bench.controller)
    bench.strokes_m = bench.strokes_m.copy()
    bench.strokes_m[FL] += CAP_M - 1e-4
    step_fl_loads(bench, [1.2 * F_min_N])
    assert "FL" not in latches_of(bench.controller)
    bench.strokes_m[FL] += 1e-4
    commands = step_fl_loads(bench, [1.2 * F_min_N])
    latch = latches_of(bench.controller)["FL"]
    assert latch["reason"] == "stroke_cap"
    assert latch["creep_travel_m"] == pytest.approx(CAP_M)
    assert commands[-1][FL] == 0.0
    names = [event.name for event in bench.controller.events]
    assert names.count(f"{TOUCH_CREEP_CAP_EVENT}:FL") == 1
    assert names.count(f"{TOUCH_CREEP_LATCH_EVENT}:FL") == 1


def test_leg_before_touch_seen_keeps_its_approach_speed(geometry) -> None:
    """No creep and no stop before the first touchdown sample (R-2 window or v_max as off)."""
    bench_on = creep_bench(geometry)
    bench_off = creep_bench(geometry, is_on=False)
    np.testing.assert_array_equal(computed_command(bench_on.controller),
                                  computed_command(bench_off.controller))
    assert np.all(computed_command(bench_on.controller) > creep_speed(geometry))


# --- tags and runner option ----------------------------------------------------------------------


def test_tcl_tag_suffix_is_last() -> None:
    on = replace(C2Config().with_10hz_d1(), touch_creep_latch=TouchCreepLatchSettings(enable=True))
    assert v5_options.controller_tag(None, C2Config().with_10hz_d1()) == "final_C4G2_LAS_K1"
    tag = v5_options.controller_tag(None, on)
    assert tag == "final_C4G2_LAS_K1_TCL"
    assert v5_options.is_touch_creep_tag(tag)
    assert v5_options.is_order_gate_tag(tag) and v5_options.is_liftoff_slow_tag(tag)
    assert v5_options.switch_base_tag(tag) == "final_C4G2"
    assert v5_options.is_extend_start_tag("final_C4G2_P3_LAS_K1_TCL")
    assert v5_options.with_liftoff_slow_tag("final_C4G2_K1_TCL") == "final_C4G2_LAS_K1_TCL"
    assert v5_options.with_order_gate_tag("final_C4G2_LAS_TCL") == "final_C4G2_LAS_K1_TCL"
    assert v5_options.with_touch_creep_tag(None) == "final_C4G2_TCL"
    assert v5_options.with_touch_creep_tag(tag) == tag
    assert not v5_options.is_touch_creep_tag("final_C4G2_LAS_K1")


def _parsed(tokens: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    touch_creep_option.add_touch_creep_argument(parser)
    return parser.parse_args(tokens)


def test_option_absent_is_the_preset_without_an_attribute() -> None:
    args = _parsed([])
    assert not hasattr(args, "k2")
    request = touch_creep_option.touch_creep_request(args)
    assert request == "preset"
    preset = C2Config().with_10hz_d1()
    assert touch_creep_option.with_touch_creep(preset, request) is preset
    assert touch_creep_option.touch_creep_record(request, preset) == {
        "touch_creep": "preset", "touch_creep_effective": False}


@pytest.mark.parametrize("value", ["off", "on"])
def test_explicit_request_sets_only_the_switch(value) -> None:
    preset = C2Config().with_10hz_d1()
    config = touch_creep_option.with_touch_creep(preset, value)
    assert config.touch_creep_latch.enable is (value == "on")
    assert replace(config, touch_creep_latch=TouchCreepLatchSettings()) == preset
    touch_creep_option.check_built_touch_creep(value, config)
    with pytest.raises(SystemExit):
        touch_creep_option.check_built_touch_creep("on" if value == "off" else "off", config)
    assert touch_creep_option.touch_creep_record(value, config)["touch_creep_effective"] is (
        value == "on")


def test_bad_option_value_is_refused() -> None:
    with pytest.raises(SystemExit):
        _parsed(["--k2", "maybe"])
