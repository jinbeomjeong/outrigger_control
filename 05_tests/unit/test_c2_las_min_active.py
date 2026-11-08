"""C2 LAS-b ``min_active_periods`` (``n_min``, ``las_rev_targeted_rules.md`` 1.4 and 7.1).

The ``sum`` end needs ``a_k >= n_min`` acted periods; the safety / phase ends and ``time`` do
not wait. ``n_min`` up to 4 changes nothing (with ``off_periods`` 5, ``a_k >= c_k - 1 >= 4`` when
``sum`` holds), so the default 0 keeps the b0 commands bit for bit. Benches and stage helpers
are those of ``test_c2_las.py``; the closed-loop bit test is R-0 of the rules, run outside the
unit tests.
"""

from __future__ import annotations

import pickle
from dataclasses import replace

import numpy as np
import pytest
from test_c2_las import (  # same test folder
    HEAVY_LOADS_N,
    MORE_TWISTED_LOADS_N,
    TWISTED_LOADS_N,
    _block_s2,
    _block_s3,
    _block_s4,
    _block_s5,
    las_config,
    stage,
)
from test_c2_p30 import geometry, level_bench  # noqa: F401

from outrigger_sim.control.c2 import (
    C2Config,
    C2Controller,
    LiftoffApproachSlowSettings,
    LiftoffSlowEnd,
)

HEAVY_TWISTED_LOADS_N = np.array([180e3, 15e3, 30e3, 140e3])
"""Sum 365 kN (above the 0.85 W_ref ``sum`` level), FR lightest, rho 0.753 (above
``MORE_TWISTED_LOADS_N``): a start period whose load already counts for ``sum``."""
REAPPROACHING_RL = np.array([False, False, True, False])
N_MIN_INERT = (0, 1, 2, 3, 4)
N_MIN_RULE = 8
TAIL_STEPS = 3
"""Steps after the scenario (a second start must not differ either)."""


def bench_controller(bench_geometry, min_active_periods: int,
                     require_soil_response: bool = True) -> C2Controller:
    """LEVEL bench of ``test_c2_las.py`` with ``n_min`` set: crawler zone, no LOC, t 20 s."""
    config = las_config(min_active_periods=min_active_periods,
                        require_soil_response=require_soil_response)
    controller = level_bench(bench_geometry, config).controller
    controller._state.in_crawler_zone = True
    controller._state.liftoff_slow = None
    controller._las_t_s = 20.0
    return controller


def without_soil_response(controller: C2Controller) -> None:
    controller.config = replace(controller.config,
                                soil=replace(controller.config.soil, enable=False))


SCENARIOS = {
    # name: (start loads, steps after the start: (state change, loads, re-approach flags))
    "sum, start counted (a = 4)": (HEAVY_TWISTED_LOADS_N, [(None, HEAVY_LOADS_N, None)] * 12),
    "sum after a dip": (MORE_TWISTED_LOADS_N,
                        [(None, HEAVY_LOADS_N, None)] * 5 + [(None, MORE_TWISTED_LOADS_N, None)]
                        + [(None, HEAVY_LOADS_N, None)] * 12),
    "time": (MORE_TWISTED_LOADS_N, [(None, MORE_TWISTED_LOADS_N, None)] * 16),
    "loc": (MORE_TWISTED_LOADS_N, [(None, HEAVY_LOADS_N, None), (_block_s3, HEAVY_LOADS_N, None)]),
    "phase": (MORE_TWISTED_LOADS_N, [(None, HEAVY_LOADS_N, None),
                                     (_block_s2, HEAVY_LOADS_N, None)]),
    "soil": (MORE_TWISTED_LOADS_N, [(None, HEAVY_LOADS_N, None),
                                    (_block_s4, HEAVY_LOADS_N, None)]),
    "reapproach": (MORE_TWISTED_LOADS_N, [(None, HEAVY_LOADS_N, None),
                                          (None, HEAVY_LOADS_N, REAPPROACHING_RL)]),
}


def run_scenario(bench_geometry, min_active_periods: int, name: str,
                 require_soil_response: bool = True) -> tuple[list[bytes], dict]:
    """Per-period command bytes and the LAS-b meta of one scenario."""
    controller = bench_controller(bench_geometry, min_active_periods, require_soil_response)
    if not require_soil_response:
        without_soil_response(controller)
    start_loads, steps = SCENARIOS[name]
    commands = [stage(controller, TWISTED_LOADS_N), stage(controller, start_loads)]
    for action, loads, reapproaching in steps:
        if action is not None:
            action(controller)
        commands.append(stage(controller, loads, reapproaching=reapproaching))
    for _ in range(TAIL_STEPS):
        commands.append(stage(controller, MORE_TWISTED_LOADS_N))
    meta = controller.meta()["liftoff_approach_slow"]
    assert meta["start_s"] is not None, name  # every scenario starts the slowdown
    return [np.asarray(command).tobytes() for command in commands], meta


# --- settings ------------------------------------------------------------------------------------


def test_default_is_zero_and_the_preset_keeps_it() -> None:
    assert LiftoffApproachSlowSettings().min_active_periods == 0
    assert C2Config().with_10hz_d1().liftoff_approach_slow.min_active_periods == 0


def test_negative_is_a_value_error() -> None:
    with pytest.raises(ValueError, match="min_active_periods"):
        LiftoffApproachSlowSettings(min_active_periods=-1)


def test_old_pickle_reads_zero(geometry) -> None:  # noqa: F811
    preset = C2Config().with_10hz_d1()
    copied = pickle.loads(pickle.dumps(C2Controller(geometry, preset)))
    copied.config.liftoff_approach_slow.__dict__.pop("min_active_periods")
    aged = pickle.loads(pickle.dumps(copied))
    assert "min_active_periods" not in aged.config.liftoff_approach_slow.__dict__
    assert aged.config.liftoff_approach_slow.min_active_periods == 0
    assert aged.config.liftoff_approach_slow == preset.liftoff_approach_slow


def test_meta_settings_have_the_new_key(geometry) -> None:  # noqa: F811
    meta = C2Controller(geometry, C2Config().with_10hz_d1()).meta()["liftoff_approach_slow"]
    assert meta["settings"]["min_active_periods"] == 0


# --- n_min 0 .. 4: bit for bit -------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(SCENARIOS))
@pytest.mark.parametrize("min_active_periods", N_MIN_INERT[1:])
def test_n_min_up_to_four_is_bit_identical(geometry, name, min_active_periods) -> None:  # noqa: F811
    reference_commands, reference_meta = run_scenario(geometry, 0, name)
    commands, meta = run_scenario(geometry, min_active_periods, name)
    assert commands == reference_commands
    assert {**meta, "settings": None} == {**reference_meta, "settings": None}


def test_the_edge_scenario_ends_on_sum_at_four_periods(geometry) -> None:  # noqa: F811
    """``a = c - 1 = 4`` is reachable, so 4 is the largest inert ``n_min`` and 5 is not."""
    _, meta = run_scenario(geometry, 0, "sum, start counted (a = 4)")
    assert meta["end_reason"] == str(LiftoffSlowEnd.SUM)
    assert meta["active_periods"] == 4
    reference_commands, _ = run_scenario(geometry, 0, "sum, start counted (a = 4)")
    commands, meta_5 = run_scenario(geometry, 5, "sum, start counted (a = 4)")
    assert commands != reference_commands
    assert meta_5["active_periods"] == 5


# --- n_min 8 -------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["sum, start counted (a = 4)", "sum after a dip"])
def test_n_min_eight_sum_end_has_eight_acted_periods(geometry, name) -> None:  # noqa: F811
    _, meta = run_scenario(geometry, N_MIN_RULE, name)
    assert meta["end_reason"] == str(LiftoffSlowEnd.SUM)
    assert meta["active_periods"] >= N_MIN_RULE


def test_the_sum_count_keeps_counting_and_resets_while_waiting(geometry) -> None:  # noqa: F811
    """Rules 1.4: the counter is b0's; a dip below the level while waiting sets it to 0."""
    _, meta_b0 = run_scenario(geometry, 0, "sum after a dip")
    assert meta_b0["active_periods"] == 5  # b0: c reaches 5 at a = 5
    _, meta = run_scenario(geometry, N_MIN_RULE, "sum after a dip")
    # n_min 8 waits (c 5 at a 5), the dip (a 6) sets c to 0, then c is 5 again at a = 11.
    assert meta["end_reason"] == str(LiftoffSlowEnd.SUM)
    assert meta["active_periods"] == 11


@pytest.mark.parametrize("name", ["loc", "phase", "soil", "reapproach"])
def test_n_min_eight_does_not_hold_the_safety_ends(geometry, name) -> None:  # noqa: F811
    reference_commands, reference_meta = run_scenario(geometry, 0, name)
    commands, meta = run_scenario(geometry, N_MIN_RULE, name)
    assert meta["end_reason"] == name == reference_meta["end_reason"]
    assert meta["active_periods"] < N_MIN_RULE
    assert commands == reference_commands


def test_n_min_eight_does_not_hold_the_zone_end(geometry) -> None:  # noqa: F811
    """U-6 ABL (``require_soil_response`` False): ``zone`` ends before 8 periods too."""
    controller = bench_controller(geometry, N_MIN_RULE, require_soil_response=False)
    without_soil_response(controller)
    stage(controller, TWISTED_LOADS_N)
    stage(controller, MORE_TWISTED_LOADS_N)
    stage(controller, HEAVY_LOADS_N)
    _block_s5(controller)
    stage(controller, HEAVY_LOADS_N)
    meta = controller.meta()["liftoff_approach_slow"]
    assert meta["end_reason"] == str(LiftoffSlowEnd.ZONE)
    assert meta["active_periods"] == 2


def test_n_min_eight_time_end_is_unchanged(geometry) -> None:  # noqa: F811
    reference_commands, reference_meta = run_scenario(geometry, 0, "time")
    commands, meta = run_scenario(geometry, N_MIN_RULE, "time")
    assert meta["end_reason"] == str(LiftoffSlowEnd.TIME)
    assert meta["active_periods"] == reference_meta["active_periods"] == 15
    assert commands == reference_commands
