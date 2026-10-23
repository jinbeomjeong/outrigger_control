"""C2 pressure zero calibration and the sensor-error rules (E-2 .. E-6; control spec 72.1,
76.1, 76.2; U71 .. U73).

Synthetic bench: the legs hang in the air (net force ``-m_rod g``, rod side 2 bar) until the
test sets a load; the strokes follow the commands; injected head offsets stand for the sensor
zero errors. The real sensor model (normal grade) drives the accuracy test.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from types import SimpleNamespace

import numpy as np
import pytest

from outrigger_sim.control.c2 import C2Config, C2Controller, C2Geometry, C2Phase
from outrigger_sim.control.target import AttitudeTarget
from outrigger_sim.control.two_pressure import TwoPressureMonitor, TwoPressureSettings
from outrigger_sim.control.zero_calibration import (
    LegCalibrationStatus,
    SkipReason,
    ZeroCalibrationMode,
)
from outrigger_sim.params import LEG_ORDER, load_params
from outrigger_sim.sensors.hydraulic import LegSensorModel, wika_a10_leg_sensor_config
from outrigger_sim.signals import Measurements

GRAVITY_M_S2 = 9.80665
PERIOD_S = 0.02
BAR = 1e5
ROD_BAR = 2.0
TIME_LIMIT_S = 30.0
FL, RR = LEG_ORDER.index("FL"), LEG_ORDER.index("RR")


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def _rod_weight_N() -> np.ndarray:
    """YAML moving-part weight per leg (spec 76.4 (2)); rear 73.163 kg -> 717.5 N."""
    return C2Geometry.from_params(load_params()).rod_weight_N


@dataclass
class _Bench:
    """Readings of hanging legs (or ``load_N``), optional head offsets and sensor model."""

    controller: C2Controller
    geometry: C2Geometry
    load_N: Callable[[_Bench], np.ndarray] | None = None
    head_offset_Pa: np.ndarray = field(default_factory=lambda: np.zeros(4))
    rod_offset_Pa: np.ndarray = field(default_factory=lambda: np.zeros(4))
    sensors: LegSensorModel | None = None
    oil_temperature_C: float | None = None
    t_s: float = 0.0
    travel_m: np.ndarray = field(default_factory=lambda: np.zeros(4))
    commands: list[np.ndarray] = field(default_factory=list)

    def forces(self) -> np.ndarray:
        if self.load_N is not None:
            return self.load_N(self)
        return -_rod_weight_N()

    def step(self) -> np.ndarray:
        self.t_s += PERIOD_S
        geometry = self.geometry
        strokes = geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m + self.travel_m
        rod = np.full(4, ROD_BAR * BAR)
        head = (self.forces() + rod * geometry.annulus_area_m2) / geometry.head_area_m2
        if self.sensors is not None:
            reading = self.sensors.measure(head, strokes, strokes, rod, t_s=self.t_s)
            head, rod = reading.head_pressure_Pa, reading.rod_pressure_Pa
        measurements = Measurements(
            t_s=self.t_s,
            specific_force_m_s2=np.array([0.0, 0.0, GRAVITY_M_S2]),
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=head + self.head_offset_Pa,
            stroke_m=strokes,
            stroke_corrected_m=strokes,
            rod_pressure_Pa=rod + self.rod_offset_Pa,
            oil_temperature_C=self.oil_temperature_C,
        )
        command = np.asarray(self.controller.update(measurements).leg_speed_m_s)
        self.travel_m = self.travel_m + command * PERIOD_S
        self.commands.append(command)
        return command

    def run_until(self, is_done: Callable[[], bool]) -> None:
        while not is_done() and self.t_s < TIME_LIMIT_S:
            self.step()
        assert is_done()

    def run_check(self) -> None:
        self.run_until(lambda: self.controller.phase is not C2Phase.CHECK)


def _bench(geometry, config: C2Config | None = None, **fields) -> _Bench:
    return _Bench(C2Controller(geometry, config or C2Config()), geometry, **fields)


def _names(controller: C2Controller) -> list[str]:
    return [event.name for event in controller.events]


def _results(controller: C2Controller):
    return controller._state.zero_calibration.results


def _offset_Pa(geometry, leg: int, force_N: float) -> np.ndarray:
    offset = np.zeros(4)
    offset[leg] = force_N / geometry.head_area_m2[leg]
    return offset


# --- E-3: the round trip ---------------------------------------------------------------------


def test_head_offset_of_4_bar_is_measured_and_removed(geometry) -> None:
    """73.1 E-3: +4 bar on the FL head -> c_FL = +5.31 kN +- 0.1 kN; the others ~0; the
    readings after CHECK are the true forces again."""
    offset = np.zeros(4)
    offset[FL] = 4.0 * BAR
    bench = _bench(geometry, head_offset_Pa=offset)
    bench.run_check()
    controller = bench.controller
    results = _results(controller)
    assert all(result.status is LegCalibrationStatus.CALIBRATED for result in results)
    assert results[FL].offset_N == pytest.approx(4.0 * BAR * geometry.head_area_m2[FL], abs=100.0)
    assert results[FL].offset_N == pytest.approx(5.31e3, abs=100.0)
    for leg in (1, 2, 3):
        assert abs(results[leg].offset_N) < 1.0
    np.testing.assert_array_equal(controller._pressures.offset_allowance_N, np.zeros(4))
    bench.step()
    np.testing.assert_allclose(controller._state.last_forces.nominal, -_rod_weight_N(), atol=1.0)
    assert _names(controller).count("INFO_PRESSURE_ZERO_CALIBRATED:FL") == 1


def test_round_trip_moves_3_mm_at_a_quarter_of_v_max_in_check(geometry) -> None:
    """72.1 (1): +3 mm, hold, -3 mm, hold, four legs together; CHECK ends after it."""
    bench = _bench(geometry)
    bench.run_check()
    commands = np.array(bench.commands)
    speed = 0.25 * geometry.max_speed_m_s
    assert np.max(commands) <= speed + 1e-12 and np.min(commands) >= -speed - 1e-12
    assert np.all(np.max(commands, axis=0) > 0.0) and np.all(np.min(commands, axis=0) < 0.0)
    calibration = bench.controller._state.zero_calibration
    duration_s = calibration.t_end_s - calibration.t_start_s
    assert 1.0 + 2 * 3e-3 / speed - 0.2 < duration_s < 1.0 + 2 * 3e-3 / speed + 0.5
    np.testing.assert_allclose(np.abs(bench.travel_m), 0.0, atol=0.5e-3)  # back to the start


def test_meta_reports_the_calibration(geometry) -> None:
    bench = _bench(geometry)
    bench.run_check()
    meta = bench.controller.meta()["zero_calibration"]
    assert meta["is_active"] and meta["settings"]["mode"] == "airborne_roundtrip"
    assert meta["result"]["legs"]["FL"]["status"] == "calibrated"
    assert meta["offsets_N"] == pytest.approx([0.0] * 4, abs=1.0)


# --- 76.2 failure handling ---------------------------------------------------------------------


def _zero_warnings(controller: C2Controller) -> list[str]:
    return [name for name in _names(controller) if name.startswith("WARN_PRESSURE_ZERO")]


def test_implausible_offset_takes_the_allowance_on_that_leg_only(geometry) -> None:
    # 76.2 test (1) as amended by 76.4 (1): the plausibility path is the negative offset.
    """76.2 test (1): about -8.3 kN on FL (head -4 bar, rod side +8 bar) -> implausible,
    c_FL = 0, allowance 5.5 kN on FL, one event.

    A +8 kN offset reads 7 kN in the air, above F_min / 2: the grounded rule of 76.2 skips
    that leg before the plausibility check (same handling, see the next test). A head offset
    of -8 kN alone (-6 bar) is a D1 head fault."""
    rod_offset = np.zeros(4)
    rod_offset[FL] = 8.0 * BAR
    head_offset = np.zeros(4)
    head_offset[FL] = -4.0 * BAR
    expected_N = -4.0 * BAR * geometry.head_area_m2[FL] - 8.0 * BAR * geometry.annulus_area_m2[FL]
    bench = _bench(geometry, head_offset_Pa=head_offset, rod_offset_Pa=rod_offset)
    bench.run_check()
    controller = bench.controller
    results = _results(controller)
    assert results[FL].status is LegCalibrationStatus.IMPLAUSIBLE
    assert results[FL].offset_N == 0.0
    assert results[FL].measured_offset_N == pytest.approx(expected_N, abs=100.0)
    assert expected_N < -7e3
    np.testing.assert_array_equal(controller._pressures.offset_allowance_N, [5500.0, 0, 0, 0])
    assert _zero_warnings(controller) == ["WARN_PRESSURE_ZERO_IMPLAUSIBLE:FL"]


def test_positive_8_kN_offset_reads_as_grounded_with_the_same_handling(geometry) -> None:
    """76.2 test (1') (76.4 (1)): +8 kN reads 7 kN in the air -> skipped as grounded, the
    allowance on FL only, one event."""
    bench = _bench(geometry, head_offset_Pa=_offset_Pa(geometry, FL, 8e3))
    bench.run_check()
    controller = bench.controller
    assert _results(controller)[FL].reason is SkipReason.GROUNDED
    np.testing.assert_array_equal(controller._pressures.offset_allowance_N, [5500.0, 0, 0, 0])
    assert _zero_warnings(controller) == ["WARN_PRESSURE_ZERO_SKIPPED:FL:grounded"]


def test_grounded_leg_is_skipped_and_gets_the_allowance(geometry) -> None:
    """76.2 test (2): RR bears 30 kN at CHECK -> skipped (no motion) + allowance 4.0 kN."""

    def load_N(bench: _Bench) -> np.ndarray:
        forces = -_rod_weight_N()
        forces[RR] = 30e3
        return forces

    bench = _bench(geometry, load_N=load_N)
    bench.run_check()
    controller = bench.controller
    result = _results(controller)[RR]
    assert result.status is LegCalibrationStatus.SKIPPED
    assert result.reason is SkipReason.GROUNDED
    assert np.all(np.array(bench.commands)[:-1, RR] == 0.0)
    np.testing.assert_array_equal(controller._pressures.offset_allowance_N, [0, 0, 0, 4000.0])
    assert "WARN_PRESSURE_ZERO_SKIPPED:RR:grounded" in _names(controller)


def test_all_legs_failing_warns_and_levelling_goes_on(geometry) -> None:
    offset = np.array([10.0, 10.0, 10.0, 10.0]) * BAR
    bench = _bench(geometry, head_offset_Pa=offset)
    bench.run_check()
    controller = bench.controller
    assert controller.phase is C2Phase.TOUCH
    assert "WARN_PRESSURE_ZERO_ALL_FAILED" in _names(controller)
    np.testing.assert_array_equal(controller._pressures.offset_allowance_N,
                                  [5500.0, 5500.0, 4000.0, 4000.0])


def test_allowance_lowers_only_the_lower_bound_reading(geometry) -> None:
    """E-6: the allowance acts on ``lower`` (guard, P5, Q2, ABOVE), not on ``nominal`` (twist
    loop) or ``upper`` (BELOW)."""
    bench = _bench(geometry, head_offset_Pa=_offset_Pa(geometry, FL, 8e3))
    bench.run_check()
    bench.step()
    forces = bench.controller._state.last_forces
    assert forces.lower[FL] == pytest.approx(forces.nominal[FL] - 5500.0)
    assert forces.upper[FL] == forces.nominal[FL]
    np.testing.assert_array_equal(forces.lower[1:], forces.nominal[1:])


@pytest.mark.parametrize("seed", range(8))
def test_calibrated_normal_sensors_read_the_guard_level_within_0_6_kN(geometry, seed) -> None:
    """76.2 test (3): normal-grade sensors, four legs calibrated, no allowance; the mean
    lower-bound reading at the guard level (F_min + 5 kN) is within 0.6 kN of the truth."""
    sensors = LegSensorModel(wika_a10_leg_sensor_config("normal"), seed)
    guard_level_N = geometry.F_min_N + 5e3
    bench = _bench(geometry, sensors=sensors)
    bench.run_check()
    controller = bench.controller
    assert all(r.status is LegCalibrationStatus.CALIBRATED for r in _results(controller))
    np.testing.assert_array_equal(controller._pressures.offset_allowance_N, np.zeros(4))
    bench.load_N = lambda _: np.full(4, guard_level_N)
    readings = []
    for _ in range(50):
        bench.step()
        readings.append(controller._state.last_forces.lower)
    error_N = np.mean(readings, axis=0) - guard_level_N
    assert np.all(np.abs(error_N) <= 600.0), error_N


# --- calibration off --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "config",
    [
        C2Config().with_r5_behaviour(),
        replace(C2Config(), zero_calibration=replace(
            C2Config().zero_calibration, mode=ZeroCalibrationMode.OFF)),
    ],
)
def test_calibration_off_keeps_check_still(geometry, config) -> None:
    """76.2 test (4): off (legacy) -> CHECK commands zero, CHECK lasts check_time_s, no
    offsets or allowance. (The bit identity with the R6-P code was checked by paired runs of
    the old and new source trees.)"""
    bench = _bench(geometry, config, head_offset_Pa=_offset_Pa(geometry, FL, 8e3))
    bench.run_check()
    controller = bench.controller
    assert controller._state.zero_calibration is None
    assert np.all(np.array(bench.commands)[:-1] == 0.0)
    assert bench.t_s == pytest.approx(PERIOD_S + config.target.check_time_s, abs=1e-9)
    np.testing.assert_array_equal(controller._pressures.zero_offsets_N, np.zeros(4))
    assert not any("PRESSURE_ZERO" in name for name in _names(controller))


def test_calibration_on_without_check_takes_the_allowance_on_all_legs(geometry) -> None:
    """76.4 (3) a: on, but CHECK has no length -> one ``...:all:no_check`` warning and the
    failure allowance on every leg; no motion, TOUCH at once."""
    config = replace(C2Config(), target=replace(C2Config().target, check_time_s=0.0))
    bench = _bench(geometry, config)
    bench.step()
    controller = bench.controller
    assert controller.phase is C2Phase.TOUCH
    assert _zero_warnings(controller) == ["WARN_PRESSURE_ZERO_SKIPPED:all:no_check"]
    np.testing.assert_array_equal(controller._pressures.offset_allowance_N,
                                  [5500.0, 5500.0, 4000.0, 4000.0])
    assert all(r.reason is SkipReason.NO_CHECK for r in _results(controller))


def test_off_without_check_keeps_the_legacy_reading(geometry) -> None:
    config = replace(
        C2Config(),
        target=replace(C2Config().target, check_time_s=0.0),
        zero_calibration=replace(C2Config().zero_calibration, mode=ZeroCalibrationMode.OFF),
    )
    bench = _bench(geometry, config)
    bench.step()
    assert bench.controller._state.zero_calibration is None
    np.testing.assert_array_equal(bench.controller._pressures.offset_allowance_N, np.zeros(4))


def test_restarted_check_reuses_calibrated_legs_and_retries_the_others(geometry) -> None:
    """76.4 (3) b: CHECK 1 calibrates FL..RL (FL +4 bar) and skips the grounded RR; the target
    is refused (IDLE). After the restart RR hangs: only RR moves and calibrates, FL keeps
    its first offset, the RR allowance is released, no warning is repeated."""
    offset = np.zeros(4)
    offset[FL] = 4.0 * BAR
    refused = replace(C2Config().target, target=AttitudeTarget.from_degrees(30.0, 0.0))
    is_rr_grounded = True

    def load_N(bench: _Bench) -> np.ndarray:
        forces = -_rod_weight_N()
        if is_rr_grounded:
            forces[RR] = 30e3
        return forces

    bench = _bench(geometry, replace(C2Config(), target=refused), load_N=load_N,
                   head_offset_Pa=offset)
    bench.run_until(lambda: bench.controller.phase is C2Phase.IDLE)
    controller = bench.controller
    first_FL_offset_N = _results(controller)[FL].offset_N
    np.testing.assert_array_equal(controller._pressures.offset_allowance_N, [0, 0, 0, 4000.0])
    is_rr_grounded = False
    controller.request_target(AttitudeTarget())
    commands_before = len(bench.commands)
    bench.run_check()
    results = _results(controller)
    assert all(result.status is LegCalibrationStatus.CALIBRATED for result in results)
    assert results[FL].offset_N == first_FL_offset_N
    second_check = np.array(bench.commands[commands_before:-1])  # the last one is TOUCH
    assert np.all(second_check[:, :RR] == 0.0) and np.any(second_check[:, RR] != 0.0)
    np.testing.assert_array_equal(controller._pressures.offset_allowance_N, np.zeros(4))
    assert controller._state.zero_calibration.to_meta()["reused_legs"] == ["FL", "FR", "RL"]
    assert _names(controller).count("INFO_PRESSURE_ZERO_CALIBRATED:FL") == 1
    assert _names(controller).count("INFO_PRESSURE_ZERO_CALIBRATED:RR") == 1


def test_rod_weight_comes_from_the_yaml_moving_parts(geometry) -> None:
    """76.4 (2): m_rod g = legs.<leg>.moving_part.mass_kg x g (rear 73.163 kg -> 717.5 N)."""
    params = load_params()
    expected = [leg.moving_part.mass_kg * params.meta.gravity_m_s2 for leg in params.legs]
    np.testing.assert_allclose(geometry.rod_weight_N, expected, rtol=1e-12)
    assert geometry.rod_weight_N[RR] == pytest.approx(717.5, abs=0.1)
    controller = C2Controller(geometry, C2Config())
    np.testing.assert_allclose(controller._pressures.rod_weight_N, expected, rtol=1e-12)
    explicit = replace(C2Config().two_pressure, rod_weight_N=(1000.0,) * 4)
    controller = C2Controller(geometry, replace(C2Config(), two_pressure=explicit))
    np.testing.assert_array_equal(controller._pressures.rod_weight_N, [1000.0] * 4)


def test_r5_preset_turns_the_revision_14_settings_off() -> None:
    legacy = C2Config().with_r5_behaviour()
    assert legacy.zero_calibration.mode is ZeroCalibrationMode.OFF
    assert legacy.thresholds.locked_pressure_warning_margin_Pa == 0.0
    assert legacy.thresholds.locked_pressure_prewarning_Pa is None
    assert legacy.pressure_offset_allowance_N == (0.0,) * 4


# --- E-4, E-5 ---------------------------------------------------------------------------------


def test_locked_head_warning_at_345_bar_and_prewarning_at_300_bar(geometry) -> None:
    controller = C2Controller(geometry, C2Config())
    area = geometry.head_area_m2
    head_bar = np.array([346.0, 344.0, 299.0, 200.0])
    reading = SimpleNamespace(t_s=1.0, head_only_force_N=head_bar * BAR * area)
    controller._report_locked_pressure(reading)
    controller._report_locked_pressure(reading)
    names = _names(controller)
    assert names.count("locked_pressure_over_limit:FL") == 1
    assert "locked_pressure_over_limit:FR" not in names
    assert names.count("locked_pressure_prewarning:FR") == 1
    assert "locked_pressure_prewarning:RL" not in names
    legacy = C2Controller(geometry, C2Config().with_r5_behaviour())
    legacy._report_locked_pressure(reading)
    assert _names(legacy) == []  # R5: 350 bar, no pre-warning


def test_oil_temperature_change_asks_for_recalibration(geometry) -> None:
    bench = _bench(geometry, oil_temperature_C=40.0)
    bench.run_check()
    controller = bench.controller
    assert controller._state.calibration_oil_temperature_C == 40.0
    bench.oil_temperature_C = 54.0
    bench.step()
    assert "WARN_PRESSURE_RECAL_DUE" not in _names(controller)
    bench.oil_temperature_C = 55.5
    bench.step()
    bench.step()
    assert _names(controller).count("WARN_PRESSURE_RECAL_DUE") == 1


# --- monitor: E-2 range, E-4 rod side, E-5 drift, E-6 overlap -----------------------------------

HEAD_AREA = np.array([1.3273e-2, 1.3273e-2, 9.5033e-3, 9.5033e-3])
ANNULUS = np.array([3.7699e-3, 3.7699e-3, 3.1416e-3, 3.1416e-3])
LOADS_N = np.array([118e3, 118e3, 72e3, 72e3])
STILL = np.zeros(4)


def _monitor(**settings) -> TwoPressureMonitor:
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, 0.022, 9414.55, PERIOD_S,
                              settings=TwoPressureSettings(**settings))


def _head_rod(loads_N=LOADS_N, rod_bar=ROD_BAR):
    rod = np.full(4, rod_bar * BAR)
    return (loads_N + rod * ANNULUS) / HEAD_AREA, rod


@pytest.mark.parametrize(
    ("head_bar", "is_fault"),
    [(-1.3, False), (-4.9, False), (-5.5, True), (409.0, False), (411.0, True)],
)
def test_d1_uses_the_raw_range_and_the_signal_current(head_bar, is_fault) -> None:
    """E-2 / U72: raw [-6, 410] bar and 3.8 .. 20.5 mA (-5 .. 412.5 bar)."""
    monitor = _monitor()
    head, rod = _head_rod()
    head[0] = head_bar * BAR
    monitor.read(0.0, head, rod, STILL, False, 2e3)
    assert (monitor.head_fault_legs == [0]) is is_fault


def test_rod_side_warning_at_345_bar() -> None:
    names = []
    for rod_bar in (344.0, 346.0):
        monitor = _monitor()
        rod = np.full(4, ROD_BAR * BAR)
        rod[1] = rod_bar * BAR
        head = (LOADS_N + rod * ANNULUS) / HEAD_AREA
        monitor.read(0.0, head, rod, STILL, True, 2e3)
        names.append([name for name, _ in monitor.pop_events()])
    assert "rod_pressure_over_limit:FR" not in names[0]
    assert "rod_pressure_prewarning:FR" in names[0]
    assert "rod_pressure_over_limit:FR" in names[1]


@pytest.mark.parametrize(
    ("sum_change_N", "duration_s", "warns"),
    [(0.0, 40.0, False), (3500.0, 40.0, False), (5000.0, 29.0, False), (5000.0, 31.0, True)],
)
def test_load_sum_drift_after_the_ready_reference(sum_change_N, duration_s, warns) -> None:
    """E-5 / 72.1 (6): |sum F - sum F_ref| > 4 kN for 30 s in READY -> one warning."""
    monitor = _monitor()
    monitor.store_load_reference(0.0, LOADS_N)
    loads = LOADS_N + sum_change_N / 4.0
    head, rod = _head_rod(loads)
    for k in range(round(duration_s / PERIOD_S) + 1):
        monitor.read(k * PERIOD_S, head, rod, STILL, True, 2e3)
    names = [name for name, _ in monitor.pop_events()]
    assert names.count("WARN_PRESSURE_DRIFT") == (1 if warns else 0)


def test_allowance_and_fallback_bound_are_not_added() -> None:
    """76.2: on a fallback leg only the larger of the model bound and the allowance is
    deducted; zero offsets come off every reading but ``head_only``."""
    monitor = _monitor()
    head, rod = _head_rod()
    rod_dropout = rod.copy()
    rod_dropout[RR] = np.nan
    monitor.read(0.0, head, rod_dropout, STILL, True, 2e3)
    assert monitor.fallback_legs == [RR]
    plain = monitor.read(0.02, head, rod_dropout, STILL, True, 2e3)
    fallback_bound = plain.nominal[RR] - plain.lower[RR]
    assert fallback_bound > 0.0
    for allowance in (0.5 * fallback_bound, 2.0 * fallback_bound):
        monitor.set_offset_allowance_N([4000.0, 0.0, 0.0, allowance])
        forces = monitor.read(0.04, head, rod_dropout, STILL, True, 2e3)
        expected = forces.nominal[RR] - max(fallback_bound, allowance)
        assert forces.lower[RR] == pytest.approx(expected, rel=1e-9)
        assert forces.lower[FL] == pytest.approx(forces.nominal[FL] - 4000.0, rel=1e-12)
    monitor.set_zero_offsets_N([1000.0, 0.0, 0.0, 0.0])
    forces = monitor.read(0.06, head, rod_dropout, STILL, True, 2e3)
    assert forces.nominal[FL] == pytest.approx(LOADS_N[FL] - 1000.0, rel=1e-9)
    assert forces.head_only[FL] == pytest.approx(head[FL] * HEAD_AREA[FL], rel=1e-12)
