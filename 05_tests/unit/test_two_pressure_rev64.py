"""D1'' mass before READY, the crawler re-contact watch and the D1 step rule suspended after a
head fault of ``control/two_pressure`` (P-S8-23 ① / ③, control spec rev. 64 321.3 / 322.2,
user decisions U-S8-69 (가) and U-S8-70 of 2026-10-27; P-S8-25 ④, spec rev. 65 332.4).

Synthetic cases on the benches of ``test_two_pressure_d1_imu.py``:

* (a) the class defaults keep the rule before P-S8-23 (no source event, D1' before READY),
* (b) a 110 bar head step with a vertical bounce: D1' faults it while the crawler carries load;
  once the crawler is off and before READY the YAML mass explains it (also 8 % off),
* the source event ``INFO_D1_IMU_MASS_SOURCE`` once per change (``yaml`` -> ``ready``),
* (c) spec rev. 65 329 ②: a READY residual of -40 kN for 2.0 s gives one warning (18th
  sample), -40 kN for 1.1 s none; -10 kN for 2.0 s clears it,
* T11 (monitor part): after a head fault with ``suspend_steps_after_head_fault`` no step of
  any leg is judged, range faults still are; ``INFO_D1_STEP_SUSPENDED`` once,
* settings and monitors pickled before P-S8-23 / P-S8-25.
"""

from __future__ import annotations

import copy
import json
import pickle
from dataclasses import replace

import numpy as np
import pytest
from test_two_pressure_d1_imu import (  # same test folder
    ANNULUS,
    BODY_MASS_KG,
    F_MIN_N,
    FL,
    FR,
    GRAVITY_M_S2,
    HEAD_AREA,
    LOAD_N,
    PERIOD_S,
    RL,
    RR,
    STILL,
    V_MAX,
    _Bench,
    _bounce,
    _pressures,
    _steps,
)

from outrigger_sim.control.two_pressure import (
    IMU_MASS_SOURCE_EVENT,
    RECONTACT_CLEARED_EVENT,
    RECONTACT_META_KEYS,
    RECONTACT_SUSPECTED_EVENT,
    STEP_SUSPENDED_EVENT,
    TwoPressureMonitor,
    TwoPressureSettings,
)

SOURCE_YAML = f"{IMU_MASS_SOURCE_EVENT}:yaml"
SOURCE_READY = f"{IMU_MASS_SOURCE_EVENT}:ready"
RECONTACT_DROP_N = 40e3
"""322.2 test (c): the crawler takes 40 kN back (above the 30 kN threshold)."""
SMALL_DROP_N = 10e3
"""322.2 test (c): a residual 10 kN low clears (above -15 kN)."""
WINDOW_SAMPLES = 10
"""1 s at 10 Hz: the residual mean and each hold."""


def _monitor(body_mass_kg: float = BODY_MASS_KG, **changes) -> TwoPressureMonitor:
    settings = replace(TwoPressureSettings().with_r8_period(), **changes)
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S, settings=settings,
                              stroke_max_m=0.70, body_mass_kg=body_mass_kg)


def _rev64_monitor(body_mass_kg: float = BODY_MASS_KG) -> TwoPressureMonitor:
    return _monitor(body_mass_kg, imu_mass_before_ready="yaml", crawler_recontact_watch=True)


def _sources(names: list[str]) -> list[str]:
    return [name for name in names if name.startswith(IMU_MASS_SOURCE_EVENT)]


# --- (a) class defaults --------------------------------------------------------------------------


def test_class_defaults_are_off() -> None:
    settings = TwoPressureSettings()
    assert settings.imu_mass_before_ready is None
    assert not settings.crawler_recontact_watch
    meta = settings.to_meta()  # the keys before P-S8-23 only
    assert "imu_mass_before_ready" not in meta
    assert not set(RECONTACT_META_KEYS) & set(meta)
    on = replace(settings, imu_mass_before_ready="yaml", crawler_recontact_watch=True).to_meta()
    assert set(RECONTACT_META_KEYS) <= set(on)
    assert on["imu_mass_before_ready"] == "yaml"


def test_class_defaults_judge_a_step_before_ready_with_d1_prime() -> None:
    """Without ``imu_mass_before_ready`` the crawler-off step before any READY stay keeps the
    D1' sum rule (the rule before P-S8-23): the bounce faults, no source event."""
    bench = _Bench(_monitor())
    _bounce(bench)
    assert bench.monitor.head_fault_legs == [FR]
    assert _sources(bench.names) == []


def test_the_rev64_settings_leave_the_forces_of_a_quiet_run() -> None:
    """Without a step the forces are bit for bit those of the class defaults."""
    readings = []
    for monitor in (_monitor(), _rev64_monitor()):
        bench = _Bench(monitor)
        forces = []
        for k in range(30):
            load = LOAD_N * (1.0 + 0.01 * np.sin(0.7 * k))
            out = monitor.read(bench.t_s, *_pressures(load), STILL, k >= 10, 2e3,
                               stroke_m=np.full(4, 0.552),
                               imu_specific_force_z_m_s2=GRAVITY_M_S2, is_crawler_lifted=True)
            forces.append(np.stack([out.nominal, out.lower, out.upper, out.head_only]))
            bench.t_s += PERIOD_S
        readings.append(np.array(forces))
    np.testing.assert_array_equal(readings[0], readings[1])


# --- (b) the YAML mass before READY --------------------------------------------------------------


def test_step_with_the_crawler_on_the_ground_is_judged_by_d1_prime() -> None:
    """Before the LOC (``is_crawler_lifted`` False) D1'' does not apply: the bounce faults."""
    bench = _Bench(_rev64_monitor())
    _bounce(bench, lifted=False)
    assert bench.monitor.head_fault_legs == [FR]
    assert _sources(bench.names) == []


@pytest.mark.parametrize("mass_error", [0.0, 0.08, -0.035])
def test_step_after_the_loc_before_ready_is_explained_by_the_yaml_mass(mass_error) -> None:
    """321.3: the YAML mass explains the bounce step; the READY range of 321.2
    (-3.5 .. +8.0 %) changes the residual by at most 12 kN against 0.5 J = 73 kN."""
    bench = _Bench(_rev64_monitor(BODY_MASS_KG * (1.0 + mass_error)))
    _bounce(bench)
    assert bench.monitor.head_fault_legs == []
    assert _steps(bench.names) == ["INFO_PRESSURE_STEP:FR:head:imu_residual"]
    assert _sources(bench.names) == [SOURCE_YAML]
    assert bench.monitor.d1_imu_mass_kg() == pytest.approx(BODY_MASS_KG * (1.0 + mass_error))


def test_source_event_once_per_change() -> None:
    bench = _Bench(_rev64_monitor())
    for _ in range(3):
        bench.read(*_pressures(LOAD_N))  # lifted, no READY mass: YAML
    bench.ready_stay(5)  # the median appears on the third READY sample
    for _ in range(3):
        bench.read(*_pressures(LOAD_N))
    assert _sources(bench.names) == [SOURCE_YAML, SOURCE_READY]
    assert bench.monitor.meta()["d1_imu_mass_source"] == "ready"


def test_ready_mass_replaces_the_yaml_mass() -> None:
    bench = _Bench(_rev64_monitor(body_mass_kg=50e3))
    assert bench.monitor.d1_imu_mass_kg() == pytest.approx(50e3)
    bench.ready_stay(3)
    assert bench.monitor.d1_imu_mass_kg() == pytest.approx(BODY_MASS_KG)


def test_no_mass_and_no_event_while_the_crawler_carries_load() -> None:
    bench = _Bench(_rev64_monitor())
    for _ in range(3):
        bench.read(*_pressures(LOAD_N), lifted=False)
    assert _sources(bench.names) == []


# --- (c) crawler re-contact ----------------------------------------------------------------------


def _ready_with_baseline(monitor: TwoPressureMonitor, samples: int = 60) -> _Bench:
    """A READY stay at rest with the load watch open (baseline stored after 6 samples). The
    default 6 s keeps the stay median on the weight through the drops of the cases."""
    bench = _Bench(monitor)
    for index in range(samples):
        bench.read(*_pressures(LOAD_N), locked=True)
        if index == 5:
            monitor.store_load_reference(bench.t_s, LOAD_N)
    assert monitor.is_load_watch_open
    return bench


def _read_drop(bench: _Bench, drop_N: float, samples: int) -> None:
    """READY samples with the leg sum ``drop_N`` below the weight (the crawler takes it)."""
    load = LOAD_N - drop_N / 4.0
    for _ in range(samples):
        bench.read(*_pressures(load), locked=True)


def _recontact_events(names: list[str]) -> list[str]:
    return [name for name in names if name in (RECONTACT_SUSPECTED_EVENT, RECONTACT_CLEARED_EVENT)]


def test_residual_drop_is_suspected_once_after_mean_and_hold() -> None:
    """A -40 kN residual step: the 1 s mean passes -30 kN on the 8th sample, the suspicion
    follows after 1 s more (18th sample) with one warning."""
    monitor = _rev64_monitor()
    bench = _ready_with_baseline(monitor)
    _read_drop(bench, RECONTACT_DROP_N, 17)
    assert not monitor.is_crawler_recontact_suspected
    _read_drop(bench, RECONTACT_DROP_N, 1)
    assert monitor.is_crawler_recontact_suspected
    _read_drop(bench, RECONTACT_DROP_N, 10)
    assert _recontact_events(bench.names) == [RECONTACT_SUSPECTED_EVENT]
    meta = monitor.meta()["crawler_recontact"]
    assert meta["is_suspected"] and meta["suspected_count"] == 1
    assert meta["last_residual_change_N"] == pytest.approx(-RECONTACT_DROP_N)
    assert meta["reference_residual_N"] == pytest.approx(0.0, abs=1e-6)


def test_small_residual_clears_the_suspicion_once() -> None:
    """Back to -10 kN: the mean passes -15 kN on the 9th sample, cleared 1 s later."""
    monitor = _rev64_monitor()
    bench = _ready_with_baseline(monitor)
    _read_drop(bench, RECONTACT_DROP_N, 20)
    assert monitor.is_crawler_recontact_suspected
    _read_drop(bench, SMALL_DROP_N, 18)
    assert monitor.is_crawler_recontact_suspected
    _read_drop(bench, SMALL_DROP_N, 1)
    assert not monitor.is_crawler_recontact_suspected
    _read_drop(bench, SMALL_DROP_N, 10)
    assert _recontact_events(bench.names) == [RECONTACT_SUSPECTED_EVENT, RECONTACT_CLEARED_EVENT]


def test_short_residual_drop_is_not_suspected() -> None:
    """1.1 s of -40 kN: the 1 s mean is below -30 kN for only 0.4 s, short of the hold."""
    monitor = _rev64_monitor()
    bench = _ready_with_baseline(monitor)
    _read_drop(bench, RECONTACT_DROP_N, 11)
    _read_drop(bench, 0.0, 20)
    assert _recontact_events(bench.names) == []


def test_threshold_follows_the_seal_friction() -> None:
    """``max(30 kN, 2 sum F_s + 10 kN)``: with ``sum F_s`` = 16 kN the threshold is 42 kN, so
    a 40 kN drop is no suspicion."""
    monitor = _rev64_monitor()
    bench = _ready_with_baseline(monitor)
    load = LOAD_N - RECONTACT_DROP_N / 4.0
    for _ in range(30):
        monitor.read(bench.t_s, *_pressures(load), STILL, True, 2e3,
                     stroke_m=np.full(4, 0.552), imu_specific_force_z_m_s2=GRAVITY_M_S2,
                     is_crawler_lifted=True, seal_friction_sum_N=16e3)
        bench.t_s += PERIOD_S
    assert not monitor.is_crawler_recontact_suspected
    assert monitor.meta()["crawler_recontact"]["last_threshold_N"] == pytest.approx(42e3)


def test_drop_is_not_judged_while_a_leg_moves() -> None:
    """The window is READY with the commands zero for the settle time (110.1)."""
    monitor = _rev64_monitor()
    bench = _ready_with_baseline(monitor)
    moving = np.array([V_MAX, 0.0, 0.0, 0.0])
    for _ in range(30):
        bench.read(*_pressures(LOAD_N - RECONTACT_DROP_N / 4.0), locked=True, command=moving)
    assert not monitor.is_crawler_recontact_suspected


def test_reference_stays_on_the_stay_start_when_the_median_follows_the_drop() -> None:
    """A re-contact right after a short stay start: the median moves to the dropped sum, the
    reference keeps the first second of the stay, so the change still reads -40 kN."""
    monitor = _rev64_monitor()
    bench = _ready_with_baseline(monitor, samples=10)
    _read_drop(bench, RECONTACT_DROP_N, 60)
    assert monitor._imu_mass_kg == pytest.approx(BODY_MASS_KG - RECONTACT_DROP_N / GRAVITY_M_S2)
    assert monitor.is_crawler_recontact_suspected
    change_N = monitor.meta()["crawler_recontact"]["last_residual_change_N"]
    assert change_N == pytest.approx(-RECONTACT_DROP_N)


def test_watch_off_raises_nothing() -> None:
    monitor = _monitor(imu_mass_before_ready="yaml")
    bench = _ready_with_baseline(monitor)
    _read_drop(bench, RECONTACT_DROP_N, 30)
    assert not monitor.is_crawler_recontact_suspected
    assert _recontact_events(bench.names) == []
    assert "crawler_recontact" not in monitor.meta()


# --- T11: D1 step rule suspended after a head fault (P-S8-25 ④) ----------------------------------

STEP_JUMP_PA = 150e5
"""A one-period jump within the sensor range (a D1 step)."""
OUT_OF_RANGE_PA = 500e5
"""A head reading beyond the 0-400 bar range (a D1 range fault)."""


def _faulted_bench(**changes) -> _Bench:
    """Three quiet samples, then FL's head reading leaves the range (FAULT_HEAD_PRESSURE:FL)."""
    bench = _Bench(_monitor(**changes))
    for _ in range(3):
        bench.read(*_pressures(LOAD_N))
    head, rod = _pressures(LOAD_N)
    head[FL] = OUT_OF_RANGE_PA
    bench.read(head, rod)
    assert bench.monitor.head_fault_legs == [FL]
    return bench


def _read_with_jumps(bench: _Bench, head_jump_Pa: dict[int, float],
                     rod_jump_Pa: dict[int, float] | None = None) -> None:
    head, rod = _pressures(LOAD_N)
    head[FL] = OUT_OF_RANGE_PA
    for leg, jump_Pa in head_jump_Pa.items():
        head[leg] += jump_Pa
    for leg, jump_Pa in (rod_jump_Pa or {}).items():
        rod[leg] += jump_Pa
    bench.read(head, rod)


def _suspended_events(names: list[str]) -> list[str]:
    return [name for name in names if name.startswith(STEP_SUSPENDED_EVENT)]


def test_t11_without_suspension_a_step_after_a_fault_is_a_fault() -> None:
    bench = _faulted_bench()
    _read_with_jumps(bench, {FR: STEP_JUMP_PA})
    assert bench.monitor.head_fault_legs == [FL, FR]
    assert _suspended_events(bench.names) == []
    assert "suspend_steps_after_head_fault" not in bench.monitor.settings.to_meta()


def test_t11_suspension_judges_no_step_but_the_range() -> None:
    bench = _faulted_bench(suspend_steps_after_head_fault=True)
    monitor = bench.monitor
    assert _suspended_events(bench.names) == [f"{STEP_SUSPENDED_EVENT}:FL"]
    assert monitor.is_step_rule_suspended
    _read_with_jumps(bench, {FR: STEP_JUMP_PA}, {RL: STEP_JUMP_PA})
    _read_with_jumps(bench, {FR: 2.0 * STEP_JUMP_PA}, {RL: 2.0 * STEP_JUMP_PA})
    assert monitor.head_fault_legs == [FL]
    assert RL not in monitor.fallback_legs
    _read_with_jumps(bench, {FR: OUT_OF_RANGE_PA})
    assert monitor.head_fault_legs == [FL, FR]
    assert _suspended_events(bench.names) == [f"{STEP_SUSPENDED_EVENT}:FL"]
    assert monitor.meta()["d1_step_suspended_by"] == "FL"
    assert monitor.settings.to_meta()["suspend_steps_after_head_fault"] is True


def test_t11_suspension_starts_on_the_read_after_the_fault() -> None:
    """A step on the fault sample itself is still judged (the suspension follows the fault)."""
    bench = _Bench(_monitor(suspend_steps_after_head_fault=True))
    for _ in range(3):
        bench.read(*_pressures(LOAD_N))
    head, rod = _pressures(LOAD_N)
    head[FL] = OUT_OF_RANGE_PA
    head[FR] += STEP_JUMP_PA
    bench.read(head, rod)
    assert bench.monitor.head_fault_legs == [FL, FR]


def test_t11_suspend_on_request() -> None:
    bench = _Bench(_monitor())
    bench.read(*_pressures(LOAD_N))
    bench.monitor.suspend_step_rule(RR)
    bench.monitor.suspend_step_rule(FR)  # a second call changes nothing
    head, rod = _pressures(LOAD_N)
    head[FR] += STEP_JUMP_PA
    bench.read(head, rod)
    assert bench.monitor.head_fault_legs == []
    assert _suspended_events(bench.names) == [f"{STEP_SUSPENDED_EVENT}:RR"]


def test_t11_monitor_pickled_before_p_s8_25_judges_steps() -> None:
    old = copy.deepcopy(_monitor(suspend_steps_after_head_fault=True))
    del old.__dict__["_step_rule_suspended_by"]
    restored = pickle.loads(pickle.dumps(old))
    assert not restored.is_step_rule_suspended
    bench = _Bench(restored)
    for _ in range(2):
        bench.read(*_pressures(LOAD_N))
    head, rod = _pressures(LOAD_N)
    head[FL] = OUT_OF_RANGE_PA
    bench.read(head, rod)
    assert restored.is_step_rule_suspended


# --- pickles -------------------------------------------------------------------------------------

REV64_SETTING_KEYS = ("imu_mass_before_ready", *RECONTACT_META_KEYS)
REV64_MONITOR_ATTRIBUTES = ("_imu_mass_source", "_imu_mass_pairs", "_imu_mass_reference_pairs",
                            "_recontact", "_held_head_Pa")


def test_settings_pickled_before_p_s8_23_read_off() -> None:
    state = dict(TwoPressureSettings().with_r8_period().__dict__)
    for key in REV64_SETTING_KEYS:
        del state[key]
    old = object.__new__(TwoPressureSettings)
    old.__dict__.update(state)
    restored = pickle.loads(pickle.dumps(old))
    assert restored.imu_mass_before_ready is None and not restored.crawler_recontact_watch
    assert restored.recontact_hold_s == 1.0
    json.dumps(restored.to_meta())


def test_monitor_pickled_before_p_s8_23_runs_with_the_new_settings() -> None:
    new = _monitor()
    bench = _Bench(new)
    bench.ready_stay(2)
    old = copy.deepcopy(new)
    for name in REV64_MONITOR_ATTRIBUTES:
        del old.__dict__[name]
    restored = pickle.loads(pickle.dumps(old))
    restored.refresh_settings(_rev64_monitor().settings)
    restored_bench = _Bench(restored, t_s=bench.t_s)
    for index in range(15):
        restored_bench.read(*_pressures(LOAD_N), locked=True)
        if index == 5:
            restored.store_load_reference(restored_bench.t_s, LOAD_N)
    _read_drop(restored_bench, RECONTACT_DROP_N, 20)
    assert restored.is_crawler_recontact_suspected
    json.dumps(restored.meta())
