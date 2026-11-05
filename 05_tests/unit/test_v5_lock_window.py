"""Controller lock window of the v5 lock closure (spec ``v5_hydraulic_impl_spec.md`` 2.6).

W-1 (window values), W-1b (the window end counts from k0 = t0 + T, synthetic input), W-3, W-4, W-5
(off = the window and meta before LC), L-10 (BL with LC refused) and the meta check of criteria P-4.
"""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pytest

from outrigger_sim.control.c2 import C2Config
from outrigger_sim.control.two_pressure import TwoPressureMonitor, TwoPressureSettings
from outrigger_sim.hydraulics.v5_options import (
    CheckDelaySetting,
    HydraulicOptions,
    LockClosureSetting,
    apply_lock_window,
    check_lock_window_meta,
    validate,
)

BAR = 1e5
PERIOD_S = 0.1
VALVE_TAU_S = 0.1
V_MAX = 0.020924
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
ROD_WEIGHT_N = np.array([1047.19, 1047.19, 717.48, 717.48])
F_MIN_N = 9414.59
FR = 1
WINDOW_TABLE_S = {(0.01, 0.05, 0.25): 0.472, (0.01, 0.05, 1.0): 0.611,
                  (0.02, 0.05, 0.25): 0.403, (0.02, 0.05, 1.0): 0.541,
                  (0.05, 0.05, 0.25): 0.311, (0.05, 0.05, 1.0): 0.450,
                  (0.02, 0.10, 0.25): 0.453, (0.02, 0.10, 1.0): 0.591}
"""Spec W-1: (delta_ol, t_c, |u_last| / v_max) -> W [s]."""


def _options(ratio: float, delay_s: float, *, window: bool = True,
             check_delay: CheckDelaySetting | None = None) -> HydraulicOptions:
    return HydraulicOptions(lock_closure=LockClosureSetting(ratio, delay_s),
                            lock_window_follows_plant=window, check_delay=check_delay)


def _window_end_s(settings: TwoPressureSettings, last_command_m_s: float) -> float:
    """Synthetic: FR commanded at t0 = 0, command-free from k0 = t0 + T on."""
    monitor = TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S, settings=settings,
                                 rod_weight_N=ROD_WEIGHT_N, stroke_max_m=0.70)
    commanded = np.zeros(4)
    commanded[FR] = last_command_m_s
    for t_s, command in ((0.0, commanded), (PERIOD_S, np.zeros(4))):
        monitor.read(t_s, np.full(4, 80 * BAR), np.full(4, 5 * BAR), command, False, 2e3,
                     stroke_m=np.full(4, 0.3))
    return monitor._lock_stretches[FR].window_end_s


@pytest.mark.parametrize("key", sorted(WINDOW_TABLE_S))
def test_w1_window_values_and_w1b_k0(key) -> None:
    ratio, delay_s, fraction = key
    config = apply_lock_window(C2Config().with_10hz_d1(), _options(ratio, delay_s), V_MAX,
                               VALVE_TAU_S)
    end_s = _window_end_s(config.two_pressure, fraction * V_MAX)
    k0_s = 0.0 + PERIOD_S
    assert end_s - k0_s == pytest.approx(WINDOW_TABLE_S[key], abs=0.0005)
    expected = (VALVE_TAU_S * math.log(max(fraction, ratio) / ratio) + delay_s + PERIOD_S)
    assert end_s - k0_s == pytest.approx(expected, rel=1e-12)


def test_w3_controller_alone_stops_the_run() -> None:
    with pytest.raises(SystemExit):
        validate(HydraulicOptions(lock_window_follows_plant=True), period_s=PERIOD_S)


def test_w4_plant_alone_with_t_c_above_the_period_is_refused() -> None:
    with pytest.raises(ValueError, match="t_c"):
        validate(_options(0.02, 0.15, window=False), period_s=PERIOD_S)
    validate(_options(0.02, 0.10, window=False), period_s=PERIOD_S)
    validate(_options(0.02, 0.15), period_s=PERIOD_S)


def test_w5_window_off_is_the_old_object_meta_and_window() -> None:
    config = C2Config().with_10hz_d1()
    assert apply_lock_window(config, _options(0.02, 0.05, window=False), V_MAX, VALVE_TAU_S) \
        is config
    meta = config.two_pressure.to_meta()
    assert "lock_window_closing_delay_s" not in meta
    old_rule = replace(config.two_pressure, lock_window_closing_delay_s=0.0)
    assert _window_end_s(old_rule, V_MAX) == _window_end_s(config.two_pressure, V_MAX)
    eps = config.two_pressure.lock_window_eps_m_s
    old_end_s = PERIOD_S + VALVE_TAU_S * math.log(V_MAX / eps) + PERIOD_S
    assert _window_end_s(config.two_pressure, V_MAX) == old_end_s


def test_l10_bl_with_lc_is_refused_and_vn_passes() -> None:
    with pytest.raises(ValueError, match="D-6"):
        validate(_options(0.02, 0.05, check_delay=CheckDelaySetting("BL")), period_s=PERIOD_S)
    validate(_options(0.02, 0.05, check_delay=CheckDelaySetting("VN")), period_s=PERIOD_S)


def test_lc_and_m2_refuse_the_counterbalance_and_l1() -> None:
    with pytest.raises(ValueError, match="counterbalance"):
        validate(_options(0.02, 0.05), period_s=PERIOD_S, lock_valve="counterbalance")
    with pytest.raises(SystemExit):
        validate(HydraulicOptions(rod_release_force=True), period_s=PERIOD_S, engine="L1")


def test_meta_check_of_the_window() -> None:
    options = _options(0.02, 0.05)
    config = apply_lock_window(C2Config().with_10hz_d1(), options, V_MAX, VALVE_TAU_S)
    meta = config.two_pressure.to_meta()
    assert meta["lock_window_closing_delay_s"] == 0.05
    check_lock_window_meta(meta, options, V_MAX, VALVE_TAU_S)
    with pytest.raises(RuntimeError):
        check_lock_window_meta(C2Config().with_10hz_d1().two_pressure.to_meta(), options, V_MAX,
                               VALVE_TAU_S)


@pytest.mark.parametrize("arguments", [(0.0, 0.05, 0.1), (4e-4, -0.01, 0.1), (4e-4, 0.05, 0.0)])
def test_with_lock_closure_ranges(arguments) -> None:
    with pytest.raises(ValueError):
        TwoPressureSettings().with_lock_closure(*arguments)
