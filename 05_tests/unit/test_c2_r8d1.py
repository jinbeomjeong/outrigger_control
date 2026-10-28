"""C2 R8-D1 preset (``s6_control_spec.md`` rev. 26 101 (3)-(9), rev. 30 136 / 139; design C2).

* the preset values and the R7 defaults (``C2Config()`` keeps every R8 setting off),
* replay of the revision-30 harness traces (``export_c2_r8d1_traces.py``, configuration
  ``C2_tv0.1``): with the parts the harness does not have turned off, c2.py returns the
  harness command one period later (d = 1) to the last bits,
* the pieces one by one on synthetic readings at 10 Hz: output delay, increment limit, R-1,
  R-2, sample confirmation, R-3, stroke-end slowdown, twist filter, stiffness normalisation,
  R-5 (horizon 4, P-R8-10), the 100 Hz attitude filter, the raw-tilt CHECK attitude (P-R8-9)
  and the PROBE low-load abort (P-R8-11).

The closed loop on the reduced plant (needs numba) is ``test_c2_r8d1_closed_loop.py``.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control.c2 import (
    COMMAND_COMPONENT_NAMES,
    R8_D1_SETTINGS,
    R8_D1_TOUCH_FREE_AIR_CAP_EXCESS_N,
    R8_REVISION,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Phase,
    C2Thresholds,
    ContactJudge,
    FastRelevelSettings,
    IncrementLimit,
    IntegratorBandMode,
    LiftedReapproachSettings,
    OutputLimit,
    PreLocLiftPauseSettings,
    R8Settings,
    ReanchorSettings,
    ReapproachMode,
    SampleConfirmation,
    SoilResponseSettings,
    StopPredictor,
    TargetSettings,
    TwistCompletionRelaxSettings,
    TwistGainReference,
    twist_rates,
)
from outrigger_sim.control.fault_reground import FaultRegroundSettings
from outrigger_sim.control.ground_contact import (
    LoadBand,
    ProbeProfile,
    ProbeResult,
    ProbeSettings,
    RegroundRule,
    StiffnessWindow,
)
from outrigger_sim.control.target import TargetAcceptance
from outrigger_sim.control.two_pressure import TwoPressureSettings
from outrigger_sim.control.zero_calibration import (
    LegCalibrationStatus,
    SkipReason,
    ZeroCalibration,
    ZeroCalibrationMode,
)
from outrigger_sim.frames import roll_pitch_from_specific_force
from outrigger_sim.params import LEG_ORDER, load_params
from outrigger_sim.sensors.attitude import CascadedLowPass
from outrigger_sim.signals import InvalidSignalError, Measurements

GRAVITY_M_S2 = 9.80665
PERIOD_S = 0.1
TRACE_DIR = Path(__file__).resolve().parents[1] / "data"
TRACE_STEM = "c2_r8d1_traces"
REPLAY_TOLERANCE_M_S = 1e-12
"""As the R1 replay (test_c2.py): the pressure round trip and the pad-plane fit differ from the
harness in the last bits only."""
TOUCH_HOLD_SAMPLES = 6
"""Touch hold 0.5 s at 10 Hz: the load is seen on 6 samples (t0 ... t0 + 0.5 s)."""
REANCHOR_OVERSHOOT_LIMIT_N = 500.0
"""Spec 139 P-6: overshoot of the stop on a synthetic ramp <= 0.5 kN."""
STEADY_LOAD_N = 80e3
BENCH_LOAD_STIFFNESS_N_M = 1.6e7
"""Synthetic readings gain this much per metre of applied extension (as test_c2.py)."""
LIFT_SPIKE_N = 23e3
"""Hydraulics 18: a leg lifting fast can read +23 kN on the first 10 Hz sample."""
SINK_RATE_M_S = 5.75e-3
"""Spec 134 G4-type sink: 11.5 mm in 2 s."""
READY_SETTLE_PERIODS = 10
"""Periods after READY entry: the 1.5 mm ready_heave tail (3 periods) and its 0.2 s settle."""
SLOW_UNLOAD_PER_PERIOD_N = 1.5e3
"""15 kN/s: below the R-5 rate threshold (20 kN/s)."""
G4_UNLOAD_RATE_N_S = 70e3
"""Spec 157.1: the Chrono G4 sink unloads RR at about 70 kN/s."""
IMU_PERIOD_S = 0.01
CHECK_TILT_RAD = (math.radians(1.0), math.radians(-2.0))
"""Crawler attitude of the CHECK bench (inside the operating diamond 4.4 / 3.2 deg)."""
ROUND_TRIP_TILT_PER_M_RAD = math.radians(0.3) / 3e-3
"""CHECK bench: the body tilts 0.3 deg in pitch per 3 mm of mean leg extension (quasi-static,
part of the truth)."""
ROCKING_AMPLITUDE_RAD = math.radians(0.3)
ROCKING_FREQUENCY_HZ = 2.0
ROCKING_DECAY_S = 0.15
"""CHECK bench: 0.3 deg 2 Hz rocking while the legs move, decaying with this time constant
after the last move (spec 158.1: +-0.3 deg raw tilt during the round trip)."""
RAW_CHECK_ERROR_LIMIT_RAD = math.radians(0.005)
"""Spec 163.1 P-R8-9 test: CHECK error <= 0.005 deg (the task asks <= 0.01 deg)."""
FILTERED_CHECK_ERROR_MIN_RAD = math.radians(0.05)
"""Spec 163.1: the filtered-attitude CHECK errs >= 0.05 deg on the same input (regression)."""
RR = LEG_ORDER.index("RR")
FL = LEG_ORDER.index("FL")


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def bench_config(**r8_changes) -> C2Config:
    """The preset on synthetic benches: no CHECK, pressure judge, IMU on the period mean, zero
    calibration off (without CHECK it would leave its allowance on every leg), soil response
    off (the bench strokes do not follow the commands, so the lift-off confirmation of spec
    rev. 57 285 never comes and DONE would wait for it; ``test_c2_soil.py`` turns it on)."""
    base = C2Config(
        target=TargetSettings(check_time_s=0.0, acceptance=TargetAcceptance.OFF),
        contact=ContactJudge.PRESSURE,
        output_ramp_time_s=None,
    )
    config = base.with_10hz_d1()
    r8 = replace(config.r8, imu_sample_period_s=None, **r8_changes)
    zero_calibration = replace(config.zero_calibration, mode=ZeroCalibrationMode.OFF)
    return replace(
        config, r8=r8, zero_calibration=zero_calibration, soil=SoilResponseSettings()
    )


R7_TOUCH_RULE = {
    "touch_free_air_min_travel_m": None,
    "touch_free_air_min_samples": 1,
    "touch_seen_samples": 1,
}
"""The TOUCH free-air rule before P-S8-6 (spec rev. 43 213.3.1 'current')."""
NO_REAPPROACH = {"lifted_reapproach": LiftedReapproachSettings()}
"""Re-approach off: tests of the twist, guard and P5 terms on a reading at ``F_min`` (below the
1.4 ``F_min`` start of P-S8-5, the re-approach would replace the twist and guard terms)."""


def operating_strokes(geometry: C2Geometry) -> np.ndarray:
    """Strokes with every pad on a level floor and the crawler 50 mm above it."""
    return geometry.operating_extension_m(0.05)


def up_in_body(tilt_rad: tuple[float, float]) -> np.ndarray:
    roll, pitch = tilt_rad
    return GRAVITY_M_S2 * np.array(
        [-math.sin(pitch), math.sin(roll) * math.cos(pitch), math.cos(roll) * math.cos(pitch)]
    )


def measurements(
    t_s: float,
    geometry: C2Geometry,
    cylinder_force_N: np.ndarray,
    stroke_m: np.ndarray,
    *,
    tilt_rad: tuple[float, float] = (0.0, 0.0),
) -> Measurements:
    return Measurements(
        t_s=t_s,
        specific_force_m_s2=up_in_body(tilt_rad),
        angular_rate_rad_s=np.zeros(3),
        head_pressure_Pa=np.asarray(cylinder_force_N) / geometry.head_area_m2,
        stroke_m=stroke_m,
        stroke_corrected_m=stroke_m,
    )


@dataclass
class Bench:
    """Synthetic 10 Hz readings: each leg ``STEADY_LOAD_N`` plus the bench stiffness times its
    applied REANCHOR travel (the controller's returned, already delayed command; as the 50 Hz
    bench of test_c2.py, the readings follow the commands only in REANCHOR)."""

    controller: C2Controller
    geometry: C2Geometry
    strokes_m: np.ndarray
    t_s: float = 0.0
    travel_m: np.ndarray = field(default_factory=lambda: np.zeros(4))
    tilt_rad: tuple[float, float] = (0.0, 0.0)
    outputs: list[np.ndarray] = field(default_factory=list)

    def forces_N(self) -> np.ndarray:
        return STEADY_LOAD_N + BENCH_LOAD_STIFFNESS_N_M * self.travel_m

    def step(self, forces_N: np.ndarray | None = None) -> np.ndarray:
        self.t_s = round(self.t_s + PERIOD_S, 10)
        forces = self.forces_N() if forces_N is None else forces_N
        reading = measurements(
            self.t_s, self.geometry, forces, self.strokes_m, tilt_rad=self.tilt_rad
        )
        command = np.array(self.controller.update(reading).leg_speed_m_s)
        if self.controller.phase is C2Phase.REANCHOR:
            self.travel_m = self.travel_m + command * PERIOD_S
        self.outputs.append(command)
        return command

    def run_while(self, phase: C2Phase, limit_s: float = 200.0) -> None:
        while self.controller.phase is phase and self.t_s < limit_s:
            self.step()


def ready_bench(geometry: C2Geometry, config: C2Config, *, pitch_deg: float = 0.0) -> Bench:
    """Touch down on a crawler pitched ``pitch_deg``, level (readings level from then on) and
    stop at the first phase after LEVEL (READY, or REANCHOR on a slope)."""
    controller = C2Controller(geometry, config)
    bench = Bench(controller, geometry, operating_strokes(geometry))
    bench.tilt_rad = (0.0, math.radians(pitch_deg))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    assert controller.phase is C2Phase.LEVEL
    bench.tilt_rad = (0.0, 0.0)
    bench.run_while(C2Phase.LEVEL)
    bench.run_while(C2Phase.DONE)
    if controller.phase is C2Phase.READY:
        for _ in range(READY_SETTLE_PERIODS):  # a ready_heave tail suspends the P5 check
            bench.step()
    return bench


# --- preset values and R7 defaults -------------------------------------------------------------


def test_default_config_keeps_every_r8_setting_off() -> None:
    config = C2Config()
    assert config.r8 == R8Settings()
    assert not config.r8.is_active
    assert not config.r8.lifted_reapproach.enable  # P-R8-12 / P-R8-13 off in R7
    assert config.filters.twist_load_time_constant_s is None
    assert config.reanchor.stop_predictor is StopPredictor.OFF
    assert config.zero_calibration.max_hold_std_per_leg_N is None
    assert not config.fault_reground.enable  # P-S8-24 off by default
    assert config.two_pressure.imu_mass_before_ready is None  # P-S8-23 off by default
    assert not config.two_pressure.crawler_recontact_watch
    meta = C2Controller.from_params(load_params()).meta()
    assert meta["revision"] == "R7"
    assert meta["timing"] == {"d": 0, "late_imu": False, "delta_s": None,
                              "imu_sample_period_s": None}
    assert meta["locked_pressure_warning_note"] is None


def test_preset_values() -> None:
    """Spec 136 C2 column and 139 P-1..P-9 with the user decisions of 2026-10-24."""
    base = C2Config()
    config = base.with_10hz_d1()
    assert config.period_s == 0.1
    assert config.output_ramp_time_s is None
    gains = config.gains
    assert (gains.attitude_kp_1_s, gains.attitude_ki_1_s2) == (0.2, 0.01)
    assert (gains.twist_ktw_1_s, gains.guard_kg_1_s) == (0.5, 0.15)  # U-R8-7
    assert gains.heave_kz_1_s == base.gains.heave_kz_1_s
    assert config.filters.attitude_time_constant_s == 0.8
    assert config.filters.attitude_stage_count == 2
    assert config.filters.twist_load_time_constant_s == 0.2
    r8 = config.r8
    assert r8 == R8_D1_SETTINGS
    assert r8.output_delay_periods == 1
    assert r8.imu_sample_period_s == 0.01
    assert r8.increment_limit == IncrementLimit(0.25, 0.25)
    assert (r8.touch_window_m, r8.touch_window_speed_fraction) == (0.04, 0.5)
    assert r8.confirmation == SampleConfirmation(3, 2, 2)
    assert (r8.end_slowdown_window_m, r8.end_slowdown_speed_fraction) == (0.015, 0.25)
    assert r8.twist_gain_reference is TwistGainReference.MEASURED_SII
    assert r8.pre_probe_stiffness_scale == 1.2  # rev. 31 P-R8-1 (spec 143)
    assert (r8.measured_stiffness_scale_min, r8.measured_stiffness_scale_max) == (1.0, 1.5)
    assert r8.stiffness_warning_range == (0.8, 2.3)  # P-R8-3, upper end rev. 35 P-R8-16
    # Rev. 32 163.1: R-5 on with horizon 4 (U-R8-13), raw-tilt CHECK, PROBE abort (U-R8-14).
    # Rev. 61 304 ① (U-S8-61): the fallback slope with the operating ratio source.
    assert r8.fast_relevel == FastRelevelSettings(
        horizon_periods=4, fallback_slope="nominal_gap", fallback_ratio_source="column_nominal"
    )
    assert r8.check_attitude_from_raw_tilt and r8.uses_raw_check_attitude
    assert r8.probe_abort_on_low_load
    # Rev. 34 174.4 / 179.1 P-R8-13 (U-R8-21): twist-mode re-approach replaces P-R8-12;
    # rev. 43 213.8 P-S8-5 (U-S8-9): start level 1.4 F_min; rev. 52 228.3 P-S8-16 (U-S8-49):
    # re-trigger rule RT; rev. 57 285 P-S9-10 (U-S9-C4): time limit 10 s.
    assert r8.lifted_reapproach == LiftedReapproachSettings(
        enable=True, mode=ReapproachMode.TWIST, load_fraction_of_F_min=1.4, samples=1,
        single_leg=True, exit_margin_N=5000.0, exit_samples=3, twist_speed_fraction=0.25,
        protect_margin_N=5000.0, speed_fraction=0.25, max_travel_m=0.04,
        retrigger_window_s=2.0, retrigger_speed_factor=0.6, opposite_window_s=0.8,
        opposite_strong_level_N=0.0, opposite_strong_samples=2, max_duration_s=10.0,
    )
    # Rev. 57 285 (U-S9-C1): the soil response with its defaults; rev. 70 369.1 (P-S8-28):
    # with the LOC anchor on.
    assert config.soil == SoilResponseSettings(enable=True, loc_anchor_enable=True)
    # Rev. 43 213.8 P-S8-6 (U-S8-11): TOUCH free air from moving samples.
    assert r8.touch_free_air_min_travel_m == 0.5e-3
    assert (r8.touch_free_air_min_samples, r8.touch_seen_samples) == (3, 2)
    # Rev. 67 344.3 P-S8-26 (U-S8-73): free-air reference cap m_rod g + F_s,cap.
    assert r8.touch_free_air_cap_excess_N == (8000.0, 8000.0, 6666.4, 6666.4)
    # Rev. 68 356.3 P-S8-27 (U-S8-76 (a)): two dips held; off outside the preset.
    assert r8.touch_hold_dip_samples == 2
    assert R8Settings().touch_hold_dip_samples == 0
    assert config.target.check_quiet_after_motion_s == 0.5
    assert config.reanchor.stop_predictor is StopPredictor.READING_RATE
    calibration = config.zero_calibration
    assert calibration.hold_s == 1.0
    assert calibration.max_hold_std_per_leg_N == (730.0, 730.0, 530.0, 530.0)
    assert calibration.hold_std_ddof == 1
    # Rev. 64 321.3 / 322.2 (U-S8-69, U-S8-70): YAML mass before READY, re-contact watch;
    # rev. 65 332.4 (P-S8-25): D1 step rule suspended after a head fault.
    assert config.two_pressure == replace(
        TwoPressureSettings().with_r8_period(),
        imu_mass_before_ready="yaml",
        crawler_recontact_watch=True,
        suspend_steps_after_head_fault=True,
    )
    # Rev. 64 323 (U-S8-68): FAULT_REGROUND; rev. 65 332.5 (P-S8-25): its corrected keys;
    # rev. 70 369.4 (P-S8-28, U-S8-79): the stroke-end entry.
    assert config.fault_reground == FaultRegroundSettings(
        enable=True,
        attitude_abort=False,
        contact_rule="all_legs_hold",
        hold_confirm_samples=10,
        own_pre_fault_cue=True,
        plane_gap_scaled=True,
        stroke_end_entry=True,
        stroke_end_travel_m=0.030,
    )
    # User decision 2026-10-27: the READY tail skip check keeps 0.5 mm for the overshoot;
    # the other tail keys and the default (0, the earlier rule) stay.
    assert config.lock_tail == replace(base.lock_tail, end_overshoot_margin_m=0.0005)
    assert base.lock_tail.end_overshoot_margin_m == 0.0
    # User decision 2026-10-28 (P-S8-29, V2b): relaxed twist completion on; off by default.
    assert config.twist_completion_relax == TwistCompletionRelaxSettings(
        enable=True,
        settle_s=10.0,
        window_s=5.0,
        drop_N=0.0,
        rise_tol_N=600.0,  # U-S8-80 (b), 2026-10-28
        max_twist_N=15000.0,
        require_loads_ge_F_min=True,
    )
    assert not base.twist_completion_relax.enable
    # User decision 2026-10-28 (P-S8-30, P30fz): pre-LOC slow lift and fast re-approach on.
    assert config.pre_loc_lift_pause == PreLocLiftPauseSettings(
        enable=True,
        on_fraction_of_F_min=3.0,
        off_fraction_of_F_min=3.5,
        falling_N=2000.0,
        max_pause_s=3.0,
        slow_lift_mean_fraction=0.16,
        reapproach_speed_factor=4.0,
        only_before_soil_mode=True,
    )
    assert not base.pre_loc_lift_pause.enable


def test_preset_leaves_the_other_settings() -> None:
    thresholds = C2Thresholds(guard_margin_N=6000.0, relevel_load_margin_N=9000.0)
    config = C2Config(thresholds=thresholds, initial_seal_band_N=11e3).with_10hz_d1()
    assert config.thresholds == thresholds
    assert config.initial_seal_band_N == 11e3
    assert config.contact is ContactJudge.COMBINED


def test_preset_meta_records_timing_and_gain_reference(geometry) -> None:
    controller = C2Controller(geometry, C2Config().with_10hz_d1())
    meta = controller.meta()
    json.dumps(meta)
    assert meta["revision"] == R8_REVISION
    assert meta["timing"] == {"d": 1, "late_imu": False, "delta_s": None,
                              "imu_sample_period_s": 0.01}
    stiffness_meta = meta["twist_gain_stiffness"]
    assert stiffness_meta["reference"] == "measured_Sii"
    assert stiffness_meta["stiffness_N_m"] == 1.2 * geometry.nominal_pad_stiffness_N_m
    # P-R8-7: before a probe round nothing measured, the pre-probe scale in use.
    assert stiffness_meta["scale_in_use"] == 1.2
    assert stiffness_meta["measured_scale"] is None
    assert stiffness_meta["raw_ratio"] is None
    assert stiffness_meta["grounded_leg_count"] is None
    assert stiffness_meta["denominator"].startswith("load_sensitivity_diag_N_m")
    assert stiffness_meta["denominator_N_m"] == geometry.load_sensitivity_diag_N_m.tolist()
    assert "quasi-static" in meta["locked_pressure_warning_note"]
    assert meta["gains"]["guard_kg_1_s"] == 0.15


def test_increment_limit_replaces_the_soft_ramp() -> None:
    with pytest.raises(ValueError, match="increment_limit"):
        replace(C2Config().with_10hz_d1(), output_ramp_time_s=0.1)


@pytest.mark.parametrize(
    "make_invalid",
    [
        lambda: R8Settings(output_delay_periods=-1),
        lambda: R8Settings(output_delay_periods=True),
        lambda: R8Settings(imu_sample_period_s=0.0),
        lambda: R8Settings(touch_window_speed_fraction=0.0),
        lambda: R8Settings(end_slowdown_speed_fraction=1.5),
        lambda: R8Settings(pre_probe_stiffness_scale=0.0),
        lambda: R8Settings(measured_stiffness_scale_min=0.0),
        lambda: R8Settings(measured_stiffness_scale_max=0.0, measured_stiffness_scale_min=None),
        lambda: R8Settings(measured_stiffness_scale_max=0.9),  # below the 1.0 minimum
        lambda: R8Settings(stiffness_warning_range=(1.5, 0.8)),
        lambda: R8Settings(stiffness_warning_range=(0.0, 1.5)),
        lambda: IncrementLimit(fraction_per_period=0.0),
        lambda: SampleConfirmation(above_samples=0),
        lambda: FastRelevelSettings(rate_intervals=0),
        lambda: FastRelevelSettings(horizon_periods=0),
        lambda: FastRelevelSettings(horizon_periods=2.0),
        lambda: TargetSettings(check_quiet_after_motion_s=-0.1),
        lambda: ReanchorSettings(stop_predictor_intervals=0),
        lambda: LiftedReapproachSettings(load_fraction_of_F_min=0.0),
        lambda: LiftedReapproachSettings(load_fraction_of_F_min=2.01),  # (0, 2], P-S8-5
        lambda: R8Settings(touch_free_air_min_travel_m=0.0),
        lambda: R8Settings(touch_free_air_min_samples=0),
        lambda: R8Settings(touch_seen_samples=True),
        lambda: R8Settings(touch_free_air_cap_excess_N=(8000.0, 8000.0, 6666.4)),
        lambda: R8Settings(touch_free_air_cap_excess_N=(8000.0, 8000.0, 6666.4, 0.0)),
        lambda: R8Settings(touch_free_air_cap_excess_N=(8000.0, 8000.0, 6666.4, math.nan)),
        lambda: R8Settings(touch_hold_dip_samples=-1),
        lambda: R8Settings(touch_hold_dip_samples=True),
        lambda: R8Settings(touch_hold_dip_samples=1.0),
        lambda: LiftedReapproachSettings(samples=0),
        lambda: LiftedReapproachSettings(samples=True),
        lambda: LiftedReapproachSettings(speed_fraction=0.0),
        lambda: LiftedReapproachSettings(max_travel_m=0.0),
        lambda: LiftedReapproachSettings(mode="both"),
        lambda: LiftedReapproachSettings(exit_samples=0),
        lambda: LiftedReapproachSettings(exit_samples=2.0),
        lambda: LiftedReapproachSettings(exit_margin_N=-1.0),
        lambda: LiftedReapproachSettings(protect_margin_N=-1.0),
        lambda: LiftedReapproachSettings(twist_speed_fraction=0.0),
        lambda: LiftedReapproachSettings(twist_speed_fraction=1.5),
    ],
)
def test_invalid_r8_settings_are_rejected(make_invalid) -> None:
    with pytest.raises(ValueError):
        make_invalid()


def test_reset_restarts_the_buffer_and_the_twist_filter(geometry) -> None:
    strokes = np.full(4, 0.1)
    controller = C2Controller(geometry, bench_config())
    first = [controller.update(measurements(0.1 * (k + 1), geometry, np.zeros(4), strokes))
             for k in range(4)]
    controller.reset()
    second = [controller.update(measurements(0.1 * (k + 1), geometry, np.zeros(4), strokes))
              for k in range(4)]
    for before, after in zip(first, second, strict=True):
        np.testing.assert_array_equal(before.leg_speed_m_s, after.leg_speed_m_s)
    np.testing.assert_array_equal(second[0].leg_speed_m_s, 0.0)


# --- replay of the revision-30 harness ---------------------------------------------------------


@pytest.fixture(scope="module")
def trace_meta() -> dict:
    return json.loads((TRACE_DIR / f"{TRACE_STEM}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def trace_rows() -> np.ndarray:
    return np.load(TRACE_DIR / f"{TRACE_STEM}.npy", allow_pickle=False)


def harness_replay_config() -> C2Config:
    """The preset with what the harness controller (``C2R8F`` on R1 ``R:BS_hold``) has: no
    CHECK, pressure judge, R2 probe and thresholds (per-axis band, 3 kN P5), no REANCHOR (the
    harness T / G cases have none), IMU on the period mean, the increment limit, sample
    confirmation and end slowdown off (the harness ramps in its loop and has neither rule), and
    the twist / guard gains on ``k_nom`` (the revision-30 harness had no stiffness scaling; the
    preset's pre-probe 1.2 of revision 31 is not in the traces)."""
    r2_probe = ProbeSettings(
        use_combined_verdict=False,
        profile=ProbeProfile.RECT,
        stroke_guard_margin_m=None,
        reground_rule=RegroundRule.VERDICT,
        attitude_ripple_ratio=None,
        attitude_drift_ratio=None,
        stiffness_window=StiffnessWindow.FULL,
    )
    r2_thresholds = C2Thresholds(
        integrator_band_mode=IntegratorBandMode.AXIS,
        relevel_load_margin_N=3000.0,
        allow_legacy_relevel_margin=True,
    )
    legacy = C2Config(
        contact=ContactJudge.PRESSURE,
        output_ramp_time_s=None,
        reanchor=ReanchorSettings(enable=False),
        target=TargetSettings(check_time_s=0.0, acceptance=TargetAcceptance.OFF),
        probe=r2_probe,
        thresholds=r2_thresholds,
    ).with_r41_behaviour()
    config = legacy.with_10hz_d1()
    r8 = replace(
        config.r8,
        imu_sample_period_s=None,
        increment_limit=None,
        confirmation=SampleConfirmation(),
        end_slowdown_window_m=None,
        twist_gain_reference=TwistGainReference.NOMINAL,
        fast_relevel=None,  # the revision-30 harness had no R-5
        probe_abort_on_low_load=False,
        lifted_reapproach=LiftedReapproachSettings(),  # nor P-R8-12 (its G case lifts RR)
        touch_hold_dip_samples=0,  # nor the P-S8-27 dip hold (its TOUCH loads dip)
    )
    return replace(config, r8=r8)


def replay(geometry: C2Geometry, rows: np.ndarray) -> tuple[np.ndarray, list[str]]:
    controller = C2Controller(geometry, harness_replay_config())
    outputs, phases = [], []
    for row in rows:
        reading = Measurements(
            t_s=float(row["t_s"]),
            specific_force_m_s2=row["specific_force_m_s2"],
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=row["cylinder_force_N"] / geometry.head_area_m2,
            stroke_m=row["motor_stroke_m"],
            stroke_corrected_m=row["rod_stroke_m"],
        )
        outputs.append(controller.update(reading).leg_speed_m_s)
        phases.append(controller.phase.name)
    return np.array(outputs), phases


def test_traces_are_the_spec_runs(trace_meta) -> None:
    """The recorded harness runs give the revision-30 results of the same cases (spec 134)."""
    assert trace_meta["configuration"] == "C2_tv0.1"
    for case in trace_meta["cases"]:
        recorded, published = case["metrics"], case["published_metrics"]
        for key in ("t_touch_s", "t_ready_s", "min_true_cyl_force_kN", "ss_true_att_deg_maxabs"):
            assert recorded[key] == published[key], (case["id"], key)
    settle = trace_meta["cases"][2]["metrics"]
    assert settle["min_true_after_sink_kN"] == -0.72  # spec 134 G4 table, C2 beta 1.6


@pytest.mark.parametrize("case_index", range(3))
def test_replay_matches_the_harness_one_period_later(
    geometry, trace_meta, trace_rows, case_index
) -> None:
    """P-1 / P-2: the harness command of ``t_k`` leaves c2.py at ``t_(k+1)`` (d = 1); phases
    equal; the first output is zero speed."""
    rows = trace_rows[trace_rows["case"] == case_index]
    outputs, phases = replay(geometry, rows)
    code_to_name = {code: name for name, code in trace_meta["phase_codes"].items()}
    assert phases == [code_to_name[int(code)] for code in rows["phase_code"]]
    np.testing.assert_array_equal(outputs[0], 0.0)
    np.testing.assert_allclose(
        outputs[1:], rows["leg_speed_m_s"][:-1], rtol=0, atol=REPLAY_TOLERANCE_M_S
    )


def test_replay_of_the_settlement_exercises_the_guard(trace_meta, trace_rows) -> None:
    rows = trace_rows[trace_rows["case"] == 2]
    assert trace_meta["cases"][2]["id"].startswith("G|")
    assert rows["guard_steps"][-1] > 0


# --- output delay (P-2) ------------------------------------------------------------------------


def test_output_is_one_period_late(geometry) -> None:
    """d = 1 returns the d = 0 command of the period before (TOUCH and LEVEL, same readings)."""
    delayed = Bench(C2Controller(geometry, bench_config()), geometry, operating_strokes(geometry))
    prompt = Bench(
        C2Controller(geometry, bench_config(output_delay_periods=0)),
        geometry,
        operating_strokes(geometry),
    )
    rng = np.random.default_rng(7)
    for _ in range(30):
        forces = STEADY_LOAD_N + rng.normal(0.0, 3e3, 4)
        delayed.step(forces)
        prompt.step(forces)
    assert prompt.controller.phase is delayed.controller.phase is C2Phase.LEVEL
    np.testing.assert_array_equal(delayed.outputs[0], 0.0)
    np.testing.assert_array_equal(np.array(delayed.outputs[1:]), np.array(prompt.outputs[:-1]))
    assert np.any(np.array(prompt.outputs[TOUCH_HOLD_SAMPLES:]) != 0.0)


# --- increment limit (101 (3)) -----------------------------------------------------------------


def test_increment_limit_steps_to_the_touch_speed(geometry) -> None:
    """TOUCH asks for v_max from rest: 0.25, 0.5, 0.75, 1.0 v_max, one period late."""
    strokes = np.full(4, 0.1)  # far from the touch window
    bench = Bench(C2Controller(geometry, bench_config()), geometry, strokes)
    outputs = [bench.step(np.zeros(4)) for _ in range(6)]
    v_max = geometry.max_speed_m_s
    expected = np.array([0.0, 0.25, 0.5, 0.75, 1.0, 1.0]) * v_max
    np.testing.assert_allclose(np.array(outputs)[:, 0], expected, rtol=0, atol=1e-15)


def test_asymmetric_limit_lets_the_guard_direction_move_faster(geometry) -> None:
    """99.4 option: guard direction 0.25, everything else 0.1 v_max per period."""
    limit = IncrementLimit(fraction_per_period=0.1, guard_fraction_per_period=0.25)
    controller = C2Controller(geometry, bench_config(increment_limit=limit))
    v_max = geometry.max_speed_m_s
    state = controller._state  # the increment limit acts on internal state; set it directly
    state.previous_output_m_s = np.zeros(4)
    state.guard_m_s = geometry.twist_vector * 1e-3  # guard asks FL, RR up, FR, RL down
    request = np.array([1.0, 1.0, -1.0, 1.0]) * v_max
    change = controller._limited_increment(request)
    np.testing.assert_allclose(change / v_max, [0.25, 0.1, -0.25, 0.25], rtol=0, atol=1e-15)
    state.guard_m_s = None
    np.testing.assert_allclose(
        controller._limited_increment(request) / v_max, [0.1, 0.1, -0.1, 0.1], atol=1e-15
    )


def test_ready_heave_tail_rises_within_the_increment_limit(geometry) -> None:
    """99.3 ``ready_heave``: 0.1 -> 0.2 -> 0.25 v_max with the 0.1 limit, 1.5 mm in total."""
    limit = IncrementLimit(fraction_per_period=0.1, guard_fraction_per_period=0.1)
    controller = C2Controller(geometry, bench_config(increment_limit=limit))
    speeds = np.array(controller._tail_speeds())
    v_max = geometry.max_speed_m_s
    np.testing.assert_allclose(speeds[:3] / v_max, [0.1, 0.2, 0.25], rtol=0, atol=1e-12)
    assert np.all(np.abs(np.diff(speeds)) <= 0.1 * v_max * (1 + 1e-12))
    assert speeds.sum() * PERIOD_S == pytest.approx(controller.config.lock_tail.tail_m, rel=1e-9)


# --- R-1 predicted REANCHOR stop (P-6) -------------------------------------------------------


def reanchor_stop_overshoot_N(geometry: C2Geometry, predictor: StopPredictor) -> float:
    """First REANCHOR step on a 3 deg nose-down crawler: stop reading minus the lowest target
    reading of the step (readings follow the applied, one-period-late command)."""
    config = bench_config()
    config = replace(config, reanchor=replace(config.reanchor, stop_predictor=predictor))
    bench = ready_bench(geometry, config, pitch_deg=3.0)
    controller = bench.controller
    assert controller.phase is C2Phase.REANCHOR
    lowest_reading_N = math.inf
    for _ in range(200):
        bench.step()
        lowest_reading_N = min(lowest_reading_N, float(bench.forces_N()[RR]))
        meta = controller.meta()["reanchor"]
        if meta["stop_readings_N"] and controller._state.reanchor.stage.name == "RETURN":
            break
    stop_N = controller.meta()["reanchor"]["stop_force_N"][0]
    return stop_N - lowest_reading_N


def test_predicted_stop_keeps_the_overshoot_small(geometry) -> None:
    """P-6: with ``1 + d`` periods of prediction the stop overshoots <= 0.5 kN; on the reading
    alone the late output overshoots by more than one period of unloading."""
    with_predictor = reanchor_stop_overshoot_N(geometry, StopPredictor.READING_RATE)
    without = reanchor_stop_overshoot_N(geometry, StopPredictor.OFF)
    assert with_predictor <= REANCHOR_OVERSHOOT_LIMIT_N
    assert without > REANCHOR_OVERSHOOT_LIMIT_N


def test_predicted_stop_is_recorded(geometry) -> None:
    bench = ready_bench(geometry, bench_config(), pitch_deg=3.0)
    controller = bench.controller
    while not controller.meta()["reanchor"]["stop_readings_N"] and bench.t_s < 200.0:
        bench.step()
    reanchor = controller.meta()["reanchor"]
    reading = reanchor["stop_readings_N"][0]
    predicted = reanchor["stop_predicted_readings_N"][0]
    assert reading["leg"] == predicted["leg"] == "RR"
    assert predicted["reading_N"] < reading["reading_N"]
    assert predicted["reading_N"] <= reanchor["stop_force_N"][0] < reading["reading_N"]


# --- R-2 touch window (101 (5)) ------------------------------------------------------------


def touch_speeds(
    geometry: C2Geometry, strokes: np.ndarray, forces: np.ndarray, **r8_changes
) -> np.ndarray:
    """TOUCH command of the first period without delay or increment limit."""
    config = bench_config(output_delay_periods=0, increment_limit=None, **r8_changes)
    controller = C2Controller(geometry, config)
    return np.array(controller.update(measurements(0.1, geometry, forces, strokes)).leg_speed_m_s)


def test_touch_window_halves_the_speed_near_the_floor(geometry) -> None:
    touch = geometry.operating_extension_m(0.0)
    strokes = touch - np.array([0.05, 0.039, 0.02, 0.0])
    speeds = touch_speeds(geometry, strokes, np.zeros(4))
    v_max = geometry.max_speed_m_s
    np.testing.assert_allclose(speeds / v_max, [1.0, 0.5, 0.5, 0.5], rtol=0, atol=1e-15)


def test_a_leg_that_has_seen_its_load_approaches_slowly(geometry) -> None:
    """Inside or outside the window, a leg that has seen its touch load keeps 0.25 v_max."""
    touch = geometry.operating_extension_m(0.0)
    strokes = touch - 0.05
    loads = np.array([0.0, 0.0, 0.0, 2.0 * geometry.F_min_N])
    # Without the P-S8-27 dip hold, the zero load below drops the RR candidate at once.
    controller = C2Controller(
        geometry,
        bench_config(output_delay_periods=0, increment_limit=None, touch_hold_dip_samples=0),
    )
    controller.update(measurements(0.1, geometry, loads, strokes))  # RR waits for its hold
    speeds = controller.update(measurements(0.2, geometry, np.zeros(4), strokes)).leg_speed_m_s
    v_max = geometry.max_speed_m_s
    np.testing.assert_allclose(speeds / v_max, [1.0, 1.0, 1.0, 0.25], rtol=0, atol=1e-15)


# --- sample confirmation (101 (6)) -----------------------------------------------------------


def combined_controller(geometry: C2Geometry) -> C2Controller:
    return C2Controller(geometry, replace(bench_config(), contact=ContactJudge.COMBINED))


def test_one_spike_sample_is_not_grounded(geometry) -> None:
    """(a) A lifted leg reading +23 kN on one sample stays AMBIGUOUS; three samples -> ABOVE."""
    controller = combined_controller(geometry)
    strokes = np.full(4, 0.1)
    grounded_N = geometry.F_min_N + controller.config.initial_seal_band_N + LIFT_SPIKE_N
    spike = np.array([grounded_N, 0.0, 0.0, 0.0])
    bands = []
    for k, forces in enumerate([spike, np.zeros(4), spike, spike, spike]):
        controller.update(measurements(0.1 * (k + 1), geometry, forces, strokes))
        bands.append(controller.load_bands[FL])
    assert bands == [
        LoadBand.AMBIGUOUS,
        LoadBand.AMBIGUOUS,
        LoadBand.AMBIGUOUS,
        LoadBand.AMBIGUOUS,
        LoadBand.ABOVE,
    ]


def test_below_needs_two_samples(geometry) -> None:
    """(b) With a measured 1 kN band a lifted leg (-W_rod) is BELOW from its second sample."""
    config = replace(bench_config(), contact=ContactJudge.COMBINED, initial_seal_band_N=1e3)
    controller = C2Controller(geometry, config)
    strokes = np.full(4, 0.1)
    loaded = np.full(4, STEADY_LOAD_N)
    lifted = loaded.copy()
    lifted[FL] = -1e3
    bands = []
    for k, forces in enumerate([loaded, loaded, loaded, lifted, lifted]):
        controller.update(measurements(0.1 * (k + 1), geometry, forces, strokes))
        bands.append(controller.load_bands[FL])
    assert bands[2:] == [LoadBand.ABOVE, LoadBand.AMBIGUOUS, LoadBand.BELOW]


def test_ready_relevels_on_the_second_low_sample(geometry) -> None:
    """(c) P5 needs two samples in a row; one low sample leaves READY (R-5 off: a step down
    is a fast fall it would act on at once)."""
    bench = ready_bench(geometry, bench_config(fast_relevel=None, **NO_REAPPROACH))
    controller = bench.controller
    assert controller.phase is C2Phase.READY
    low = np.full(4, STEADY_LOAD_N)
    low[RR] = geometry.F_min_N
    bench.step(low)
    assert controller.phase is C2Phase.READY
    bench.step()
    bench.step(low)
    assert controller.phase is C2Phase.READY
    bench.step(low)
    assert controller.phase is C2Phase.LEVEL


def test_guard_acts_on_the_first_low_sample(geometry) -> None:
    """(d) The F_min guard keeps the one-sample reaction (raw reading)."""
    bench = ready_bench(geometry, bench_config(**NO_REAPPROACH))
    low = np.full(4, STEADY_LOAD_N)
    low[RR] = geometry.F_min_N
    bench.step(low)
    bench.step(low)  # P5 -> LEVEL in this period, the guard acts in its LEVEL step
    assert bench.controller.phase is C2Phase.LEVEL
    assert bench.controller._state.guard_m_s is not None


# --- R-3 zero calibration hold (101 (7)) -------------------------------------------------------


def calibration_result(settings, hold_scatter_N: float, leg: int):
    calibration = ZeroCalibration(settings, 0.02, np.full(4, 700.0), 0.69)
    calibration.start(0.0, np.full(4, 0.1), np.zeros(4, dtype=bool))
    pattern = np.tile([1.0, -1.0], 5) * hold_scatter_N * math.sqrt(0.9)  # sample std (ddof 1)
    t_s, strokes, sample = 0.0, np.full(4, 0.1), 0
    while not calibration.is_finished and t_s < 30.0:
        t_s = round(t_s + PERIOD_S, 10)
        forces = np.full(4, -700.0)
        forces[leg] += pattern[sample % pattern.size]
        sample += 1
        speeds = calibration.step(t_s, strokes, forces)
        strokes = strokes + speeds * PERIOD_S
    return calibration.results[leg]


@pytest.mark.parametrize(("leg", "scatter_N", "is_steady"),
                         [(0, 700.0, True), (0, 760.0, False), (3, 500.0, True),
                          (3, 560.0, False)])
def test_zero_calibration_hold_scatter_limits(leg, scatter_N, is_steady) -> None:
    """R-3: hold 1.0 s (10 samples), sample std limit 0.73 kN front / 0.53 kN rear."""
    settings = C2Config().with_10hz_d1().zero_calibration
    result = calibration_result(settings, scatter_N, leg)
    if is_steady:
        assert result.status is LegCalibrationStatus.CALIBRATED
    else:
        assert result.reason is SkipReason.UNSTEADY


# --- stroke-end slowdown (101 (8)) -------------------------------------------------------------


def test_extension_slows_near_the_stroke_end(geometry) -> None:
    """Within 15 mm below ``soft end - 10 mm`` no extending leg exceeds 0.25 v_max (vector
    scaled); a leg there retracting or slower is not limited."""
    end_margin_stroke = geometry.stroke_soft_max_m - 0.010
    strokes = np.full(4, 0.1)
    strokes[FL] = end_margin_stroke - 0.010  # inside the 15 mm window
    no_window = {"touch_window_m": None}  # FL is past its touch extension
    speeds = touch_speeds(geometry, strokes, np.zeros(4), **no_window)
    v_max = geometry.max_speed_m_s
    np.testing.assert_allclose(speeds / v_max, [0.25] * 4, rtol=0, atol=1e-15)
    strokes[FL] = end_margin_stroke - 0.020  # outside
    np.testing.assert_allclose(
        touch_speeds(geometry, strokes, np.zeros(4), **no_window) / v_max,
        [1.0] * 4,
        rtol=0,
        atol=1e-15,
    )


# --- twist filter and stiffness normalisation (P-4, P-5) ------------------------------------


def level_twist_and_guard(controller: C2Controller, geometry: C2Geometry, forces: np.ndarray):
    """One LEVEL period: (twist channel of the computed command, guard share)."""
    strokes = operating_strokes(geometry)
    balanced = np.full(4, STEADY_LOAD_N)
    level_periods = 3  # the twist filter starts on the first LEVEL reading (n^T P = 0)
    for k in range(TOUCH_HOLD_SAMPLES + level_periods):
        controller.update(measurements(0.1 * (k + 1), geometry, balanced, strokes))
    assert controller.phase is C2Phase.LEVEL
    t_s = 0.1 * (TOUCH_HOLD_SAMPLES + level_periods + 1)
    controller.update(measurements(t_s, geometry, forces, strokes))
    computed = controller._state.previous_output_m_s  # before the output buffer
    guard = controller._state.guard_m_s
    return geometry.decompose(computed)[3], None if guard is None else guard.copy()


def test_twist_filter_leaves_the_guard_reading(geometry) -> None:
    """P-4: the 0.2 s filter slows the twist term, the guard sees the raw low reading."""
    forces = np.full(4, STEADY_LOAD_N)
    forces[RR] = geometry.F_min_N  # twist load and a guard deficit at once
    no_limit = {"output_delay_periods": 0, "increment_limit": None, **NO_REAPPROACH}
    filtered = C2Controller(geometry, bench_config(**no_limit))
    raw_config = bench_config(**no_limit)
    raw_config = replace(raw_config, filters=replace(raw_config.filters,
                                                     twist_load_time_constant_s=None))
    raw = C2Controller(geometry, raw_config)
    twist_filtered, guard_filtered = level_twist_and_guard(filtered, geometry, forces)
    twist_raw, guard_raw = level_twist_and_guard(raw, geometry, forces)
    np.testing.assert_array_equal(guard_filtered, guard_raw)
    assert abs(twist_filtered) < abs(twist_raw)


def test_measured_stiffness_scales_twist_and_guard(geometry) -> None:
    """P-5: a measured stiffness 1.3 x nominal makes the twist and guard terms 1 / 1.3."""
    gains = C2Config().with_10hz_d1().gains
    thresholds = C2Thresholds()
    loads = np.full(4, STEADY_LOAD_N)
    loads[RR] = geometry.F_min_N
    nominal = twist_rates(20e3, loads, geometry, gains, thresholds)
    stiff = twist_rates(
        20e3, loads, geometry, gains, thresholds, 1.3 * geometry.nominal_pad_stiffness_N_m
    )
    assert stiff.twist_m_s == pytest.approx(nominal.twist_m_s / 1.3, rel=1e-12)
    assert stiff.guard_m_s == pytest.approx(nominal.guard_m_s / 1.3, rel=1e-12)


def probe_results(scale_per_leg: list[float], nominal_N_m: np.ndarray) -> tuple:
    return tuple(
        ProbeResult(leg, 50e3, 0.0, scale * nominal_N_m[leg], True, is_grounded_by_stiffness=True)
        for leg, scale in enumerate(scale_per_leg)
    )


PROBE_T_S = 50.0
STIFFNESS_WARNING = "WARN_PROBE_STIFFNESS_OUT_OF_RANGE"


def stiffness_warnings(controller: C2Controller) -> list[str]:
    return [event.name for event in controller.events if event.name.startswith(STIFFNESS_WARNING)]


def test_pre_probe_scale_divides_twist_and_guard_by_1_2(geometry) -> None:
    """P-R8-1: before the first probe the twist and guard commands are 1 / 1.2 of k_nom's."""
    forces = np.full(4, STEADY_LOAD_N)
    forces[RR] = geometry.F_min_N  # twist load and a guard deficit at once
    no_limit = {"output_delay_periods": 0, "increment_limit": None, **NO_REAPPROACH}
    preset = C2Controller(geometry, bench_config(**no_limit))
    on_k_nom = C2Controller(
        geometry, bench_config(twist_gain_reference=TwistGainReference.NOMINAL, **no_limit)
    )
    twist_preset, guard_preset = level_twist_and_guard(preset, geometry, forces)
    twist_k_nom, guard_k_nom = level_twist_and_guard(on_k_nom, geometry, forces)
    assert guard_k_nom is not None and np.any(guard_k_nom != 0.0)
    np.testing.assert_allclose(guard_preset, guard_k_nom / 1.2, rtol=1e-12, atol=0)
    assert twist_preset == pytest.approx(twist_k_nom / 1.2, rel=1e-9)


def test_probe_ratio_is_against_the_head_only_nominal(geometry) -> None:
    """P-R8-2: a probe reading the head-only nominal ``S_ii`` gives 1.0, the U63 C1 values
    (which hold the L1-R rod-side share) give about 1.13."""
    head_only = geometry.load_sensitivity_diag_N_m
    controller = C2Controller(geometry, bench_config())
    controller._update_twist_stiffness_scale(probe_results([1.0] * 4, head_only), PROBE_T_S)
    assert controller._state.twist_stiffness_scale == pytest.approx(1.0, rel=1e-12)
    u63 = np.asarray(controller.config.probe_correction_sensitivity_N_m)
    controller._update_twist_stiffness_scale(probe_results([1.0] * 4, u63), PROBE_T_S)
    expected = float(np.median(u63 / head_only))
    assert controller._state.twist_stiffness_scale == pytest.approx(expected, rel=1e-12)
    assert 1.12 < expected < 1.14


def test_probe_scale_is_the_median_of_the_grounded_legs(geometry) -> None:
    """P-R8-3: one leg x3 does not move the median; each round replaces the scale."""
    head_only = geometry.load_sensitivity_diag_N_m
    controller = C2Controller(geometry, bench_config())
    controller._update_twist_stiffness_scale(
        probe_results([1.3, 1.3, 1.3, 3.9], head_only), PROBE_T_S
    )
    k_nom = geometry.nominal_pad_stiffness_N_m
    assert controller._twist_gain_stiffness_N_m() == pytest.approx(1.3 * k_nom, rel=1e-12)
    controller._update_twist_stiffness_scale(probe_results([1.1] * 4, head_only), PROBE_T_S)
    assert controller._twist_gain_stiffness_N_m() == pytest.approx(1.1 * k_nom, rel=1e-12)
    assert stiffness_warnings(controller) == []
    stiffness_meta = controller.meta()["twist_gain_stiffness"]
    assert stiffness_meta["raw_ratio"] == pytest.approx(1.1, rel=1e-12)
    assert stiffness_meta["grounded_leg_count"] == 4


def test_two_grounded_legs_keep_the_previous_scale(geometry) -> None:
    """P-R8-3: under 3 legs with a stiffness cue the scale stays (pre-probe 1.2 or last)."""
    head_only = geometry.load_sensitivity_diag_N_m
    controller = C2Controller(geometry, bench_config())
    two_legs = probe_results([1.4, 1.4, 1.4, 1.4], head_only)
    two_legs = tuple(
        replace(result, is_grounded_by_stiffness=result.leg_index < 2) for result in two_legs
    )
    controller._update_twist_stiffness_scale(two_legs, PROBE_T_S)
    k_nom = geometry.nominal_pad_stiffness_N_m
    assert controller._twist_gain_stiffness_N_m() == pytest.approx(1.2 * k_nom, rel=1e-12)
    stiffness_meta = controller.meta()["twist_gain_stiffness"]
    assert (stiffness_meta["raw_ratio"], stiffness_meta["grounded_leg_count"]) == (None, 2)
    controller._update_twist_stiffness_scale(probe_results([1.3] * 4, head_only), PROBE_T_S)
    controller._update_twist_stiffness_scale(two_legs, PROBE_T_S)
    assert controller._twist_gain_stiffness_N_m() == pytest.approx(1.3 * k_nom, rel=1e-12)


@pytest.mark.parametrize(
    ("ratio", "expected_scale", "is_warned"),
    [
        (2.4, 1.5, True),
        (2.3, 1.5, False),
        (2.17, 1.5, False),
        (1.7, 1.5, False),
        (1.5, 1.5, False),
        (0.9, 1.0, False),
        (0.8, 1.0, False),
        (0.7, 1.0, True),
    ],
)
def test_probe_scale_bounds_and_warning(geometry, ratio, expected_scale, is_warned) -> None:
    """P-R8-3: the scale stays in [1.0, 1.5]; a raw median above 2.3 (P-R8-16, rev. 35: beta
    1.6 GPa reads 2.17 and no longer warns) or below 0.8 warns once per round with its value,
    the bounded value is used."""
    head_only = geometry.load_sensitivity_diag_N_m
    controller = C2Controller(geometry, bench_config())
    controller._update_twist_stiffness_scale(probe_results([ratio] * 4, head_only), PROBE_T_S)
    assert controller._state.twist_stiffness_scale == pytest.approx(expected_scale, rel=1e-12)
    expected_events = [f"{STIFFNESS_WARNING}:{ratio:.3f}"] if is_warned else []
    assert stiffness_warnings(controller) == expected_events
    stiffness_meta = controller.meta()["twist_gain_stiffness"]
    assert stiffness_meta["raw_ratio"] == pytest.approx(ratio, rel=1e-12)
    assert stiffness_meta["scale_in_use"] == pytest.approx(expected_scale, rel=1e-12)


def test_nominal_reference_ignores_the_probe(geometry) -> None:
    nominal_reference = C2Controller(
        geometry, bench_config(twist_gain_reference=TwistGainReference.NOMINAL)
    )
    head_only = geometry.load_sensitivity_diag_N_m
    nominal_reference._update_twist_stiffness_scale(
        probe_results([1.3] * 4, head_only), PROBE_T_S
    )
    assert nominal_reference._twist_gain_stiffness_N_m() is None  # k_nom unchanged (R7)
    assert nominal_reference.meta()["twist_gain_stiffness"]["scale_in_use"] == 1.0


# --- FAULT stop and computed output (P-R8-5, P-R8-6) -------------------------------------------


def full_speed_touch_bench(geometry: C2Geometry) -> Bench:
    """TOUCH from rest far from the floor: the computed command reaches v_max in 4 periods."""
    bench = Bench(C2Controller(geometry, bench_config()), geometry, np.full(4, 0.1))
    for _ in range(5):
        bench.step(np.zeros(4))
    v_max = geometry.max_speed_m_s
    np.testing.assert_allclose(bench.controller.computed_output_m_s, v_max, rtol=0, atol=1e-15)
    return bench


def test_fault_stop_skips_the_increment_limit(geometry) -> None:
    """P-R8-5: at full speed a FAULT computes 0 at once (not 0.75 v_max); the output delay
    stays, so the returned command is v_max once more and 0 the period after."""
    bench = full_speed_touch_bench(geometry)
    controller = bench.controller
    controller._state.phase = C2Phase.FAULT  # as _take_pressure_events / the stroke-end fault
    returned = bench.step(np.zeros(4))
    np.testing.assert_array_equal(controller.computed_output_m_s, 0.0)
    np.testing.assert_allclose(returned, geometry.max_speed_m_s, rtol=0, atol=1e-15)
    np.testing.assert_array_equal(bench.step(np.zeros(4)), 0.0)


def test_computed_output_is_the_next_returned_command(geometry) -> None:
    """P-R8-6: the computed command of ``t_k`` is returned at ``t_(k+1)``; it is a copy."""
    bench = Bench(C2Controller(geometry, bench_config()), geometry, np.full(4, 0.1))
    computed = []
    for _ in range(6):
        bench.step(np.zeros(4))
        computed.append(bench.controller.computed_output_m_s)
    np.testing.assert_array_equal(np.array(bench.outputs[1:]), np.array(computed[:-1]))
    computed[-1][:] = -1.0
    assert np.all(bench.controller.computed_output_m_s >= 0.0)


# --- R-5 (P-9; on in the preset with horizon 4, P-R8-10) ----------------------------------


def sink_until_relevel(geometry: C2Geometry, config: C2Config) -> float:
    """READY, then RR unloads at the G4 sink rate times the RR load sensitivity."""
    bench = ready_bench(geometry, config)
    controller = bench.controller
    assert controller.phase is C2Phase.READY
    drop_per_period_N = SINK_RATE_M_S * geometry.load_sensitivity_diag_N_m[RR] * PERIOD_S
    forces = np.full(4, STEADY_LOAD_N)
    while controller.phase is C2Phase.READY and bench.t_s < 300.0:
        forces[RR] -= drop_per_period_N
        bench.step(forces.copy())
    return bench.t_s


def test_fast_relevel_starts_earlier_on_a_sink(geometry) -> None:
    """P-9: the re-level starts at least one period earlier with R-5 (20 kN/s, 3 periods)."""
    without = sink_until_relevel(geometry, bench_config(fast_relevel=None))
    with_r5 = sink_until_relevel(geometry, bench_config(fast_relevel=FastRelevelSettings()))
    assert with_r5 <= without - PERIOD_S + 1e-9


def ramp_until_relevel(geometry: C2Geometry, config: C2Config) -> tuple[float, list[str]]:
    """READY, then RR unloads at ``G4_UNLOAD_RATE_N_S`` (spec 157.1); the re-level time and
    the events from the ramp start on."""
    bench = ready_bench(geometry, config)
    controller = bench.controller
    assert controller.phase is C2Phase.READY
    events_before = len(controller.events)
    forces = np.full(4, STEADY_LOAD_N)
    while controller.phase is C2Phase.READY and bench.t_s < 300.0:
        forces[RR] -= G4_UNLOAD_RATE_N_S * PERIOD_S
        bench.step(forces.copy())
    return bench.t_s, [event.name for event in controller.events[events_before:]]


def test_fast_relevel_horizon_4_starts_two_periods_earlier(geometry) -> None:
    """P-R8-10: on the 70 kN/s ramp the horizon 4 (preset) re-levels 2 periods before the
    horizon ``1 + d`` = 2, both on R-5 (``relevel_predicted:RR``)."""
    horizon_2, events_2 = ramp_until_relevel(
        geometry, bench_config(fast_relevel=FastRelevelSettings())
    )
    horizon_4, events_4 = ramp_until_relevel(geometry, bench_config())
    assert horizon_4 == pytest.approx(horizon_2 - 2 * PERIOD_S, abs=1e-9)
    assert events_2 == events_4 == ["relevel_predicted:RR"]


def test_fast_relevel_ignores_a_slow_fall_with_horizon_4(geometry) -> None:
    """P-R8-10: a 15 kN/s fall (below the 20 kN/s rate) to just above P5 does not trigger."""
    bench = ready_bench(geometry, bench_config())
    controller = bench.controller
    above_p5_N = geometry.F_min_N + controller.config.thresholds.relevel_load_margin_N + 1e3
    forces = bench.forces_N()
    for _ in range(80):
        forces[RR] = max(forces[RR] - SLOW_UNLOAD_PER_PERIOD_N, above_p5_N)
        bench.step(forces.copy())
    assert controller.phase is C2Phase.READY
    assert not any(event.name.startswith("relevel_predicted") for event in controller.events)


@pytest.mark.parametrize("horizon_periods", [None, 4])
@pytest.mark.parametrize("spike_period", range(4))
def test_fast_relevel_ignores_an_upward_spike(geometry, spike_period, horizon_periods) -> None:
    """P-9: one +23 kN sample near the P5 level does not trigger (falling direction only)."""
    fast_relevel = FastRelevelSettings(horizon_periods=horizon_periods)
    bench = ready_bench(geometry, bench_config(fast_relevel=fast_relevel))
    controller = bench.controller
    near_p5 = bench.forces_N()
    near_p5[RR] = geometry.F_min_N + controller.config.thresholds.relevel_load_margin_N + 3e3
    forces = bench.forces_N()
    while forces[RR] > near_p5[RR]:  # unload slowly to just above P5
        forces[RR] = max(forces[RR] - SLOW_UNLOAD_PER_PERIOD_N, near_p5[RR])
        bench.step(forces.copy())
    for period in range(4 + 8):
        forces = near_p5.copy()
        if period == 4 + spike_period:
            forces[RR] += LIFT_SPIKE_N
        bench.step(forces)
    assert controller.phase is C2Phase.READY
    assert not any(event.name.startswith("relevel_predicted") for event in controller.events)


# --- 100 Hz attitude filter (P-3) ----------------------------------------------------------


def test_attitude_filter_runs_on_the_imu_samples(geometry) -> None:
    """A tilt step inside a period: each 10 Hz value equals the 100 Hz filter at that time."""
    config = replace(bench_config(), r8=replace(bench_config().r8, imu_sample_period_s=0.01))
    controller = C2Controller(geometry, config)
    reference = CascadedLowPass(0.8, 2, 0.01)
    strokes = np.full(4, 0.1)
    step_sample = 35  # the tilt changes in the middle of the fourth period
    for period in range(20):
        tilts = [
            (0.0, 0.0) if period * 10 + k < step_sample else (math.radians(1.0), 0.0)
            for k in range(10)
        ]
        samples = np.array([up_in_body(tilt) for tilt in tilts])
        for sample in samples:
            expected = reference.update(list(roll_pitch_from_specific_force(sample)))
        reading = replace(
            measurements(0.1 * (period + 1), geometry, np.zeros(4), strokes),
            specific_force_m_s2=samples.mean(axis=0),
            imu_specific_force_samples_m_s2=samples,
        )
        controller.update(reading)
        np.testing.assert_allclose(controller.filtered_attitude_rad, expected, rtol=0, atol=1e-15)


def test_attitude_filter_needs_the_imu_samples(geometry) -> None:
    controller = C2Controller(geometry, C2Config().with_10hz_d1())
    with pytest.raises(ValueError, match="imu_specific_force_samples_m_s2"):
        controller.update(measurements(0.1, geometry, np.zeros(4), np.full(4, 0.1)))


def test_imu_samples_are_validated() -> None:
    base = {
        "t_s": 0.1,
        "specific_force_m_s2": np.zeros(3),
        "angular_rate_rad_s": np.zeros(3),
        "head_pressure_Pa": np.zeros(4),
        "stroke_m": np.zeros(4),
    }
    reading = Measurements(**base, imu_specific_force_samples_m_s2=np.zeros((10, 3)))
    assert reading.imu_specific_force_samples_m_s2.shape == (10, 3)
    assert not reading.imu_specific_force_samples_m_s2.flags.writeable
    for bad in (np.zeros((0, 3)), np.zeros(3), np.full((2, 3), np.nan)):
        with pytest.raises(InvalidSignalError):
            Measurements(**base, imu_specific_force_samples_m_s2=bad)


# --- P-R8-9 raw-tilt CHECK attitude ------------------------------------------------------------


@dataclass
class CheckBench:
    """10 Hz CHECK of the preset with the zero-calibration round trip on 10 ms IMU samples.

    The strokes follow the returned (one-period-late) commands. The tilt is the CHECK crawler
    attitude, plus a quasi-static pitch with the mean leg extension (part of the truth), plus
    a 2 Hz rocking while a leg moves that decays after the last move (the transient).
    """

    controller: C2Controller
    start_strokes_m: np.ndarray
    t_s: float = 0.0
    applied_m_s: np.ndarray = field(default_factory=lambda: np.zeros(4))
    motion_end_s: float | None = None

    def __post_init__(self) -> None:
        self.strokes_m = self.start_strokes_m.copy()

    def quasi_static_tilt_rad(self, mean_extension_m: float) -> tuple[float, float]:
        roll, pitch = CHECK_TILT_RAD
        return roll, pitch + ROUND_TRIP_TILT_PER_M_RAD * mean_extension_m

    def rocking_rad(self, t_s: float, is_moving: bool) -> float:
        if not is_moving and self.motion_end_s is None:
            return 0.0
        oscillation = ROCKING_AMPLITUDE_RAD * math.sin(2.0 * math.pi * ROCKING_FREQUENCY_HZ * t_s)
        if is_moving:
            return oscillation
        return oscillation * math.exp(-(t_s - self.motion_end_s) / ROCKING_DECAY_S)

    def imu_samples(self, period_start_s: float, is_moving: bool) -> np.ndarray:
        samples = []
        for k in range(1, round(PERIOD_S / IMU_PERIOD_S) + 1):
            sample_t_s = period_start_s + k * IMU_PERIOD_S
            elapsed_s = sample_t_s - period_start_s
            extension_m = self.strokes_m - self.start_strokes_m + self.applied_m_s * elapsed_s
            roll, pitch = self.quasi_static_tilt_rad(float(extension_m.mean()))
            rocking = self.rocking_rad(sample_t_s, is_moving)
            samples.append(up_in_body((roll + 0.5 * rocking, pitch + rocking)))
        return np.array(samples)

    def step(self) -> None:
        period_start_s = self.t_s
        self.t_s = round(self.t_s + PERIOD_S, 10)
        is_moving = bool(np.any(self.applied_m_s != 0.0))
        if is_moving:
            self.motion_end_s = self.t_s
        samples = self.imu_samples(period_start_s, is_moving)
        self.strokes_m = self.strokes_m + self.applied_m_s * PERIOD_S
        reading = Measurements(
            t_s=self.t_s,
            specific_force_m_s2=samples.mean(axis=0),
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=np.zeros(4),
            stroke_m=self.strokes_m,
            stroke_corrected_m=self.strokes_m,
            imu_specific_force_samples_m_s2=samples,
        )
        self.applied_m_s = np.array(self.controller.update(reading).leg_speed_m_s)

    def run_check(self, limit_s: float = 15.0) -> None:
        while self.controller.phase is C2Phase.CHECK and self.t_s < limit_s:
            self.step()

    def check_error_rad(self) -> float:
        """Largest roll / pitch error of ``(phi_c, theta_c)`` against the true attitude."""
        extension_m = float((self.strokes_m - self.start_strokes_m).mean())
        truth = np.array(self.quasi_static_tilt_rad(extension_m))
        return float(np.max(np.abs(np.array(self.controller.crawler_attitude_rad) - truth)))


def check_bench(geometry: C2Geometry, *, is_raw_tilt: bool) -> CheckBench:
    config = C2Config().with_10hz_d1()
    config = replace(config, r8=replace(config.r8, check_attitude_from_raw_tilt=is_raw_tilt))
    bench = CheckBench(C2Controller(geometry, config), np.full(4, 0.1))
    bench.run_check()
    assert bench.controller.phase is C2Phase.TOUCH
    assert bench.motion_end_s is not None  # the round trip moved the legs
    return bench


def test_raw_tilt_check_attitude_ignores_the_round_trip_transient(geometry) -> None:
    """P-R8-9: the mean raw tilt of the quiet window is within 0.005 deg of the truth; the
    filtered-attitude CHECK (rev. 31) errs by >= 0.05 deg on the same input."""
    raw = check_bench(geometry, is_raw_tilt=True)
    filtered = check_bench(geometry, is_raw_tilt=False)
    assert raw.check_error_rad() <= RAW_CHECK_ERROR_LIMIT_RAD
    assert filtered.check_error_rad() >= FILTERED_CHECK_ERROR_MIN_RAD
    assert raw.t_s > filtered.t_s  # the quiet window extends CHECK past the round trip


def test_raw_tilt_check_window_starts_after_the_quiet_time(geometry) -> None:
    bench = check_bench(geometry, is_raw_tilt=True)
    target_meta = bench.controller.meta()["target"]
    json.dumps(target_meta)
    window = target_meta["check_window"]
    assert target_meta["check_attitude_source"] == "raw_tilt"
    assert window["sample_count"] == 100  # 1 s of 10 ms samples
    assert window["is_quiet_window_full"]
    assert window["quiet_start_s"] == pytest.approx(window["last_nonzero_command_t_s"] + 0.5)
    assert window["t_first_sample_s"] >= window["quiet_start_s"] - 1e-9
    assert window["t_last_sample_s"] == pytest.approx(window["t_judged_s"])


def test_raw_tilt_check_needs_the_imu_samples() -> None:
    """Spec 158.1: without IMU-rate samples (R7 path) the switch does nothing."""
    r8 = replace(C2Config().with_10hz_d1().r8, imu_sample_period_s=None)
    assert r8.check_attitude_from_raw_tilt and not r8.uses_raw_check_attitude


# --- P-R8-11 PROBE abort on a low load ---------------------------------------------------------


FREE_AIR_PERIODS = 51
"""Combined judge: the free-air reading is the median of the first 5 s (zero loads here)."""


def combined_bench(geometry: C2Geometry, **r8_changes) -> Bench:
    """Combined judge bench after its free-air window (zero loads), in TOUCH. The strokes of
    this bench do not move in TOUCH, so it keeps the R7 free-air rule (P-S8-6 judges only
    moving samples and would never touch; its own tests are at the end of the file)."""
    config = replace(bench_config(**(R7_TOUCH_RULE | r8_changes)), contact=ContactJudge.COMBINED)
    bench = Bench(C2Controller(geometry, config), geometry, operating_strokes(geometry))
    for _ in range(FREE_AIR_PERIODS):
        bench.step(np.zeros(4))
    assert bench.controller.phase is C2Phase.TOUCH
    return bench


def probe_bench(geometry: C2Geometry, **r8_changes) -> Bench:
    """Combined judge: touch down, level and stop in the first PROBE period that moves FL."""
    bench = combined_bench(geometry, **r8_changes)
    controller = bench.controller
    bench.run_while(C2Phase.TOUCH)
    bench.run_while(C2Phase.LEVEL)
    bench.run_while(C2Phase.DONE)
    assert controller.phase is C2Phase.PROBE
    assert controller._probed_leg() == FL
    return bench


def steps_until_level(bench: Bench, forces_N: np.ndarray, limit: int = 10) -> int:
    for step in range(1, limit + 1):
        bench.step(forces_N)
        if bench.controller.phase is C2Phase.LEVEL:
            return step
    return limit + 1


@pytest.mark.parametrize(("fast_relevel", "expected_steps"),
                         [(R8_D1_SETTINGS.fast_relevel, 1), (None, 2)])
def test_low_load_on_another_leg_stops_the_probe(geometry, fast_relevel, expected_steps) -> None:
    """P-R8-11: RR drops to 0 while FL is probed -> LEVEL within 2 periods (R-5 on: at once,
    P5 alone: on its second sample), event ``probe_aborted_low_load:RR``. The re-approach is
    off here: P-R8-13 would re-level on the first sample (its own test below)."""
    bench = probe_bench(geometry, fast_relevel=fast_relevel, **NO_REAPPROACH)
    forces = np.full(4, STEADY_LOAD_N)
    forces[RR] = 0.0
    assert steps_until_level(bench, forces) == expected_steps
    names = [event.name for event in bench.controller.events]
    assert "probe_aborted_low_load:RR" in names
    assert ("relevel_predicted:RR" in names) == (fast_relevel is not None)


def test_unloading_the_probed_leg_does_not_stop_the_probe(geometry) -> None:
    bench = probe_bench(geometry)
    forces = np.full(4, STEADY_LOAD_N)
    forces[FL] = 0.0
    for _ in range(3):
        bench.step(forces)
        assert bench.controller.phase is C2Phase.PROBE
    assert not any(
        event.name.startswith(("probe_aborted", "relevel_predicted", "leg_reapproach"))
        for event in bench.controller.events
    )


def test_probe_without_a_low_load_is_unchanged(geometry) -> None:
    """P-R8-11 regression: with steady loads the abort rule changes no command or phase."""
    runs = []
    for is_abort_on in (True, False):
        bench = combined_bench(geometry, probe_abort_on_low_load=is_abort_on)
        phases = []
        for _ in range(400):
            bench.step()
            phases.append(bench.controller.phase)
        runs.append((np.array(bench.outputs), phases))
    assert C2Phase.PROBE in runs[0][1] and runs[0][1][-1] is C2Phase.READY
    np.testing.assert_array_equal(runs[0][0], runs[1][0])
    assert runs[0][1] == runs[1][1]


# --- lifted-leg re-approach, leg mode (P-R8-12, rev. 33 172.1) ------------------------------


LIFTED_READING_N = -1e3
"""Spec 172.1 test: a grounded leg's reading steps to -1 kN (the rod weight hanging)."""
LEG_MODE ={"lifted_reapproach": LiftedReapproachSettings.leg_mode()}
"""P-R8-12 as revision 33 ran it (kept as an option by U-R8-21)."""


def reapproach_names(controller: C2Controller) -> list[str]:
    return [event.name for event in controller.events
            if event.name.startswith(("leg_reapproach_", "WARN_LEG_REAPPROACH_"))]


def lifted_rr_forces(rr_reading_N: float = LIFTED_READING_N) -> np.ndarray:
    forces = np.full(4, STEADY_LOAD_N)
    forces[RR] = rr_reading_N
    return forces


def computed_command(controller: C2Controller) -> np.ndarray:
    """The command computed this period, before the output buffer (d = 1)."""
    return controller._state.previous_output_m_s.copy()


def test_lifted_leg_reapproaches_from_the_second_low_sample(geometry) -> None:
    """RR steps to -1 kN in READY: R-5 re-levels at once, the second low sample starts the
    re-approach, the next output (d = 1) moves RR at 0.25 v_max = 5.23 mm/s."""
    bench = ready_bench(geometry, bench_config(**LEG_MODE))
    controller = bench.controller
    lifted = lifted_rr_forces()
    bench.step(lifted)
    assert controller.phase is C2Phase.LEVEL  # R-5 (relevel_predicted:RR)
    assert reapproach_names(controller) == []
    bench.step(lifted)
    assert reapproach_names(controller) == ["leg_reapproach_start:RR"]
    reapproach_speed = 0.25 * geometry.max_speed_m_s
    assert computed_command(controller)[RR] == reapproach_speed
    assert bench.outputs[-1][RR] != reapproach_speed
    bench.step(lifted)
    assert bench.outputs[-1][RR] == reapproach_speed
    assert reapproach_speed == pytest.approx(5.23e-3, abs=0.01e-3)


def test_reapproach_holds_the_twist_and_guard_terms(geometry) -> None:
    """While RR re-approaches tau_dot = 0: the other legs keep only their attitude and heave
    terms, i.e. the guard-path command of the same period less its twist component."""
    benches = {}
    for name, r8_changes in (("on", LEG_MODE), ("off", NO_REAPPROACH)):
        bench = ready_bench(geometry, bench_config(**r8_changes))
        bench.step(lifted_rr_forces())
        bench.step(lifted_rr_forces())
        benches[name] = bench
    held = benches["on"].controller
    guarded = benches["off"].controller
    assert held._state.guard_m_s is None
    assert guarded._state.guard_m_s is not None
    guard_path = computed_command(guarded)
    twist_rate = geometry.decompose(guard_path)[3]
    assert abs(twist_rate) > 1e-5
    without_twist = guard_path - geometry.twist_vector * twist_rate
    others = [FL, LEG_ORDER.index("FR"), LEG_ORDER.index("RL")]
    np.testing.assert_allclose(
        computed_command(held)[others], without_twist[others], rtol=0, atol=1e-12
    )


def test_reapproach_ends_on_f_min_and_the_guard_returns(geometry) -> None:
    """One sample at F_min ends the re-approach (``leg_reapproach_contact:RR``); the guard
    acts again in the same period (F_min < F_min + 5 kN)."""
    bench = ready_bench(geometry, bench_config(**LEG_MODE))
    controller = bench.controller
    for _ in range(5):
        bench.step(lifted_rr_forces())
    assert controller.phase is C2Phase.LEVEL
    assert controller._state.guard_m_s is None
    bench.step(lifted_rr_forces(geometry.F_min_N))
    assert reapproach_names(controller) == ["leg_reapproach_start:RR",
                                            "leg_reapproach_contact:RR"]
    assert controller._state.guard_m_s is not None
    assert computed_command(controller)[RR] != 0.25 * geometry.max_speed_m_s
    (interval,) = controller.meta()["lifted_reapproach"]
    assert interval["leg"] == "RR" and interval["outcome"] == "contact"


def test_reapproach_without_contact_warns_after_40_mm(geometry) -> None:
    """RR stays in the air while its stroke follows the command: past 40 mm of travel the
    warning ``WARN_LEG_REAPPROACH_NO_CONTACT:RR``, then the guard path, and no second search
    while RR has not borne F_min again."""
    bench = ready_bench(geometry, bench_config(**LEG_MODE))
    controller = bench.controller
    while "WARN_LEG_REAPPROACH_NO_CONTACT:RR" not in reapproach_names(controller):
        assert bench.t_s < 200.0
        command = bench.step(lifted_rr_forces())
        bench.strokes_m = bench.strokes_m.copy()
        bench.strokes_m[RR] += command[RR] * PERIOD_S
    (interval,) = controller.meta()["lifted_reapproach"]
    assert interval["outcome"] == "no_contact"
    assert 0.04 < interval["travel_m"] <= 0.04 + 0.25 * geometry.max_speed_m_s * PERIOD_S
    for _ in range(20):
        bench.step(lifted_rr_forces())
    assert controller._state.guard_m_s is not None
    assert reapproach_names(controller).count("leg_reapproach_start:RR") == 1


@pytest.mark.parametrize("mode_changes", [{}, LEG_MODE], ids=["twist", "leg"])
def test_g4_type_fall_does_not_start_a_reapproach(geometry, mode_changes) -> None:
    """A 70 kN/s fall that stops at 14 kN (the leg keeps bearing) re-levels by R-5 but never
    reads below the start level (1.4 F_min = 13.2 kN in the preset, P-S8-5; 0.5 F_min in leg
    mode; not even on one sample, P-R8-13), so the re-approach stays off and the commands are
    those with the re-approach off."""
    outputs = {}
    for name, r8_changes in (("on", mode_changes), ("off", NO_REAPPROACH)):
        bench = ready_bench(geometry, bench_config(**r8_changes))
        forces = np.full(4, STEADY_LOAD_N)
        for _ in range(60):
            forces[RR] = max(forces[RR] - G4_UNLOAD_RATE_N_S * PERIOD_S, 14e3)
            bench.step(forces.copy())
        assert reapproach_names(bench.controller) == []
        assert "relevel_predicted:RR" in [event.name for event in bench.controller.events]
        outputs[name] = np.array(bench.outputs)
    np.testing.assert_array_equal(outputs["on"], outputs["off"])


def test_reapproach_from_probe_returns_to_level(geometry) -> None:
    """A non-probed leg lifting in PROBE starts its re-approach and the run re-levels (R-5
    off here, so P5 and P-R8-12 meet on the second sample)."""
    bench = probe_bench(geometry, fast_relevel=None, **LEG_MODE)
    lifted = lifted_rr_forces()
    bench.step(lifted)
    assert bench.controller.phase is C2Phase.PROBE
    bench.step(lifted)
    assert bench.controller.phase is C2Phase.LEVEL
    names = [event.name for event in bench.controller.events]
    assert "leg_reapproach_start:RR" in names and "probe_aborted_low_load:RR" in names


# --- lifted-leg re-approach, twist mode (P-R8-13, rev. 34 174.4 / 179.1) ----------------------


FR = LEG_ORDER.index("FR")
RL = LEG_ORDER.index("RL")
EXIT_MARGIN_N = 5e3
TWIST_REAPPROACH_RR_MM_S = (4.76, -4.76, -5.23, 5.23)
"""Spec 179.1: ``n tau_dot_lift`` with RR lifted, FL / FR / RL / RR (mm/s)."""
TWIST_REAPPROACH_TOLERANCE_MM_S = 0.01


class ComponentRecorder(C2Controller):
    """C2 that keeps the unscaled LEVEL command of every period next to its components."""

    def __init__(self, geometry: C2Geometry, config: C2Config) -> None:
        super().__init__(geometry, config)
        self.unscaled_log: list[tuple[np.ndarray, np.ndarray]] = []

    def _record_command_components(self, rates, unscaled_speeds, reapproaching) -> None:
        super()._record_command_components(rates, unscaled_speeds, reapproaching)
        self.unscaled_log.append((unscaled_speeds.copy(), reapproaching.copy()))


def twist_ready_bench(geometry: C2Geometry) -> Bench:
    """READY bench with the preset re-approach (twist mode)."""
    bench = ready_bench(geometry, bench_config())
    assert bench.controller.config.r8.lifted_reapproach.mode is ReapproachMode.TWIST
    return bench


def test_twist_reapproach_starts_on_one_low_sample(geometry) -> None:
    """RR steps to -1 kN in READY: the first low sample starts the re-approach; the command
    is ``n tau_dot_lift`` (fastest leg 0.25 v_max) plus the attitude and heave terms and is
    output one period later (d = 1)."""
    bench = twist_ready_bench(geometry)
    controller = bench.controller
    bench.step(lifted_rr_forces())
    assert reapproach_names(controller) == ["leg_reapproach_start:RR"]
    assert controller.phase is C2Phase.LEVEL
    components = controller.command_components_m_s
    np.testing.assert_allclose(
        components["reapproach"] * 1e3, TWIST_REAPPROACH_RR_MM_S,
        atol=TWIST_REAPPROACH_TOLERANCE_MM_S,
    )
    assert np.max(np.abs(components["reapproach"])) == pytest.approx(
        0.25 * geometry.max_speed_m_s, rel=1e-12
    )
    np.testing.assert_array_equal(components["twist"], 0.0)
    np.testing.assert_array_equal(components["guard"], 0.0)
    expected = components["attitude"] + components["heave"] + components["reapproach"]
    computed = computed_command(controller)
    np.testing.assert_allclose(computed, expected, rtol=0, atol=1e-12)
    assert not np.allclose(bench.outputs[-1], computed)
    bench.step(lifted_rr_forces())
    np.testing.assert_array_equal(bench.outputs[-1], computed)
    (interval,) = controller.meta()["lifted_reapproach"]
    assert interval["mode"] == "twist" and interval["outcome"] is None


@pytest.mark.parametrize(("lower_N", "starts"), [(12e3, True), (14e3, False)])
def test_twist_reapproach_starts_below_1_4_f_min(geometry, lower_N, starts) -> None:
    """P-S8-5 (spec rev. 42 212.10, U-S8-9): a low-load RR (lower bound 12 kN, one sample)
    starts the re-approach below 1.4 F_min = 13.2 kN; 14 kN does not."""
    bench = twist_ready_bench(geometry)
    bench.step(lifted_rr_forces(lower_N))
    expected = ["leg_reapproach_start:RR"] if starts else []
    assert reapproach_names(bench.controller) == expected


@pytest.mark.parametrize("fraction", [1.0, 2.0])
def test_reapproach_start_fraction_accepts_up_to_two(fraction) -> None:
    assert LiftedReapproachSettings(load_fraction_of_F_min=fraction).load_fraction_of_F_min == (
        fraction
    )


def test_twist_reapproach_watches_no_other_leg_while_active(geometry) -> None:
    """``single_leg``: FL reading -1 kN while RR re-approaches starts nothing."""
    bench = twist_ready_bench(geometry)
    bench.step(lifted_rr_forces())
    both_lifted = lifted_rr_forces()
    both_lifted[FL] = LIFTED_READING_N
    for _ in range(3):
        bench.step(both_lifted)
    assert reapproach_names(bench.controller) == ["leg_reapproach_start:RR"]
    assert bench.controller._state.reapproach_low_counts[FL] == 0


def test_twist_reapproach_ends_on_three_samples_at_the_exit_level(geometry) -> None:
    """Readings at ``F_min + 5 kN``: two samples keep it going, a sample just below restarts
    the count, the third sample in a row ends it (``leg_reapproach_contact:RR``)."""
    bench = twist_ready_bench(geometry)
    controller = bench.controller
    bench.step(lifted_rr_forces())
    exit_level = geometry.F_min_N + EXIT_MARGIN_N
    for reading in (exit_level, exit_level, exit_level - 1.0, exit_level, exit_level):
        bench.step(lifted_rr_forces(reading))
        assert reapproach_names(controller) == ["leg_reapproach_start:RR"]
    assert controller._state.active_reapproaches[RR].exit_samples_seen == 2
    bench.step(lifted_rr_forces(exit_level))
    assert reapproach_names(controller) == ["leg_reapproach_start:RR",
                                            "leg_reapproach_contact:RR"]
    (interval,) = controller.meta()["lifted_reapproach"]
    assert interval["outcome"] == "contact" and interval["exit_samples_seen"] == 3
    np.testing.assert_array_equal(controller.command_components_m_s["reapproach"], 0.0)


def test_twist_reapproach_protects_another_grounded_leg(geometry) -> None:
    """FR reading below ``F_min + 5 kN`` while RR re-approaches: ``tau_dot`` = 0 that period;
    back above it, the twist re-approach returns."""
    bench = twist_ready_bench(geometry)
    controller = bench.controller
    bench.step(lifted_rr_forces())
    low_fr = lifted_rr_forces()
    low_fr[FR] = geometry.F_min_N + EXIT_MARGIN_N - 1.0
    bench.step(low_fr)
    np.testing.assert_array_equal(controller.command_components_m_s["reapproach"], 0.0)
    assert controller._state.guard_m_s is None  # the guard stays replaced
    bench.step(lifted_rr_forces())
    np.testing.assert_allclose(
        controller.command_components_m_s["reapproach"] * 1e3, TWIST_REAPPROACH_RR_MM_S,
        atol=TWIST_REAPPROACH_TOLERANCE_MM_S,
    )
    (interval,) = controller.meta()["lifted_reapproach"]
    assert interval["protected_periods"] == 1


def test_twist_reapproach_does_not_protect_the_extended_diagonal_leg(geometry) -> None:
    """FL (extended by the RR twist, its load rises) reading 0 while rocking keeps the twist
    re-approach going; only the retracted legs FR and RL are protected."""
    bench = twist_ready_bench(geometry)
    controller = bench.controller
    bench.step(lifted_rr_forces())
    fl_lifted = lifted_rr_forces()
    fl_lifted[FL] = 0.0
    bench.step(fl_lifted)
    np.testing.assert_allclose(
        controller.command_components_m_s["reapproach"] * 1e3, TWIST_REAPPROACH_RR_MM_S,
        atol=TWIST_REAPPROACH_TOLERANCE_MM_S,
    )
    low_rl = lifted_rr_forces()
    low_rl[RL] = 0.0
    bench.step(low_rl)
    np.testing.assert_array_equal(controller.command_components_m_s["reapproach"], 0.0)


def test_twist_reapproach_without_contact_warns_after_40_mm(geometry) -> None:
    bench = twist_ready_bench(geometry)
    controller = bench.controller
    while "WARN_LEG_REAPPROACH_NO_CONTACT:RR" not in reapproach_names(controller):
        assert bench.t_s < 200.0
        command = bench.step(lifted_rr_forces())
        bench.strokes_m = bench.strokes_m.copy()
        bench.strokes_m[RR] += command[RR] * PERIOD_S
    (interval,) = controller.meta()["lifted_reapproach"]
    assert interval["outcome"] == "no_contact" and interval["travel_m"] > 0.04


def test_twist_reapproach_from_probe_returns_to_level_at_once(geometry) -> None:
    """One low sample on a non-probed leg (R-5 off): re-approach and LEVEL in that period."""
    bench = probe_bench(geometry, fast_relevel=None)
    bench.step(lifted_rr_forces())
    assert bench.controller.phase is C2Phase.LEVEL
    names = [event.name for event in bench.controller.events]
    assert "leg_reapproach_start:RR" in names and "probe_aborted_low_load:RR" in names


# --- command components (P-R8-14, rev. 34 179.1) -----------------------------------------------


COMPONENT_SUM_TOLERANCE_M_S = 1e-12
"""Spec 179.1 P-R8-14: component sum = unscaled computed command within 1e-12 m/s."""


@pytest.mark.parametrize("mode_changes", [{}, LEG_MODE], ids=["twist", "leg"])
def test_command_components_add_up_to_the_unscaled_level_command(geometry, mode_changes) -> None:
    """Touch-down, levelling, a G4-type fall (guard) and a lifted RR (re-approach): in every
    LEVEL period the five parts add up to the unscaled command (leg mode: with the lifted
    leg at its override speed)."""
    controller = ComponentRecorder(geometry, bench_config(**mode_changes))
    bench = Bench(controller, geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    bench.run_while(C2Phase.LEVEL)
    forces = np.full(4, STEADY_LOAD_N)
    sums_checked = 0
    seen_parts = set()
    bench.tilt_rad = (math.radians(0.3), math.radians(-0.2))  # keeps the attitude term busy
    for step in range(40):
        # 14 kN: inside the guard (F_min + 5 kN) and above the 1.4 F_min re-approach start.
        forces[RR] = max(forces[RR] - G4_UNLOAD_RATE_N_S * PERIOD_S, 14e3)
        level_periods_before = len(controller.unscaled_log)
        bench.step(lifted_rr_forces() if step >= 20 else forces.copy())
        if len(controller.unscaled_log) == level_periods_before:
            continue  # no LEVEL step this period
        components = controller.command_components_m_s
        assert tuple(components) == COMMAND_COMPONENT_NAMES
        np.testing.assert_array_equal(components["phase_path"], 0.0)
        unscaled, reapproaching = controller.unscaled_log[-1]
        expected = unscaled.copy()
        if mode_changes:
            expected[reapproaching] = 0.25 * geometry.max_speed_m_s
        total = sum(components.values())
        np.testing.assert_allclose(total, expected, rtol=0, atol=COMPONENT_SUM_TOLERANCE_M_S)
        sums_checked += 1
        seen_parts |= {name for name, speeds in components.items() if np.any(speeds != 0.0)}
    assert sums_checked >= 20
    assert {"attitude", "guard", "reapproach"} <= seen_parts


def test_command_components_outside_level_are_the_phase_path(geometry) -> None:
    """P-R8-15: a TOUCH period holds its command in ``phase_path``, the LEVEL parts are 0."""
    controller = C2Controller(geometry, bench_config())
    assert controller.command_components_m_s == {}  # before the first period
    bench = Bench(controller, geometry, np.full(4, 0.1))
    bench.step(np.zeros(4))  # free air: every leg extends
    assert controller.phase is C2Phase.TOUCH
    components = controller.command_components_m_s
    assert tuple(components) == COMMAND_COMPONENT_NAMES
    assert np.all(components["phase_path"] > 0.0)
    for name in COMMAND_COMPONENT_NAMES[:-1]:
        np.testing.assert_array_equal(components[name], 0.0)
    np.testing.assert_array_equal(components["phase_path"], controller.raw_output_m_s)


# --- raw command and limit flags (P-R8-15, rev. 35 188.2) --------------------------------------


RAW_SUM_TOLERANCE_M_S = 1e-12
"""Spec 188.2 P-R8-15: component sum = ``raw_u`` = ``computed_u`` within 1e-12 m/s."""


def test_raw_output_and_flags_before_the_first_period(geometry) -> None:
    controller = C2Controller(geometry, bench_config())
    np.testing.assert_array_equal(controller.raw_output_m_s, 0.0)
    flags = controller.output_limit_flags
    assert tuple(flags) == tuple(limit.value for limit in OutputLimit)
    assert not any(legs.any() for legs in flags.values())


@pytest.mark.parametrize("mode_changes", [{}, LEG_MODE], ids=["twist", "leg"])
def test_components_add_up_to_the_raw_output_in_every_phase(geometry, mode_changes) -> None:
    """Combined bench from TOUCH through LEVEL, PROBE and READY, then a lifted RR: in every
    period the parts add up to ``raw_u``; where no limit acted ``raw_u`` is ``computed_u``
    (to the rounding of the increment step), and in TOUCH, LEVEL and PROBE there are such
    periods."""
    bench = combined_bench(geometry, **mode_changes)
    controller = bench.controller
    unlimited_phases = set()
    limited_periods = 0

    def check_period() -> None:
        nonlocal limited_periods
        raw = controller.raw_output_m_s
        total = sum(controller.command_components_m_s.values())
        np.testing.assert_allclose(total, raw, rtol=0, atol=RAW_SUM_TOLERANCE_M_S)
        if any(legs.any() for legs in controller.output_limit_flags.values()):
            limited_periods += 1
            return
        np.testing.assert_allclose(
            controller.computed_output_m_s, raw, rtol=0, atol=RAW_SUM_TOLERANCE_M_S
        )
        unlimited_phases.add(phase_of_the_command)

    while controller.phase is not C2Phase.READY and bench.t_s < 200.0:
        phase_of_the_command = controller.phase
        bench.step()
        check_period()
    for step in range(20):
        phase_of_the_command = controller.phase
        bench.step(lifted_rr_forces() if step >= 5 else None)
        check_period()
    assert {C2Phase.TOUCH, C2Phase.LEVEL, C2Phase.PROBE} <= unlimited_phases
    assert limited_periods > 0  # the increment limit acts on the TOUCH start


def test_increment_limit_flag_on_the_touch_start(geometry) -> None:
    """First TOUCH period from rest: ``raw_u`` = v_max, computed 0.25 v_max, all legs flagged
    by the increment limit only; at full speed nothing is flagged."""
    controller = C2Controller(geometry, bench_config())
    bench = Bench(controller, geometry, np.full(4, 0.1))
    bench.step(np.zeros(4))
    v_max = geometry.max_speed_m_s
    np.testing.assert_array_equal(controller.raw_output_m_s, v_max)
    np.testing.assert_allclose(controller.computed_output_m_s, 0.25 * v_max, rtol=0, atol=1e-15)
    flags = controller.output_limit_flags
    assert flags[OutputLimit.INCREMENT.value].all()
    other_limits = [limit for limit in OutputLimit if limit is not OutputLimit.INCREMENT]
    assert not any(flags[limit.value].any() for limit in other_limits)
    for _ in range(4):
        bench.step(np.zeros(4))
    assert not any(legs.any() for legs in controller.output_limit_flags.values())
    np.testing.assert_allclose(
        controller.computed_output_m_s, controller.raw_output_m_s,
        rtol=0, atol=RAW_SUM_TOLERANCE_M_S,
    )


def test_stroke_end_flag_on_the_end_slowdown(geometry) -> None:
    """FL inside the end-slowdown window: the whole TOUCH vector is scaled, every leg flagged
    as ``stroke_end``."""
    strokes = np.full(4, 0.1)
    strokes[FL] = geometry.stroke_soft_max_m - 0.020
    config = bench_config(output_delay_periods=0, increment_limit=None, touch_window_m=None)
    controller = C2Controller(geometry, config)
    controller.update(measurements(0.1, geometry, np.zeros(4), strokes))
    np.testing.assert_array_equal(controller.raw_output_m_s, geometry.max_speed_m_s)
    flags = controller.output_limit_flags
    assert flags[OutputLimit.STROKE_END.value].all()
    assert not flags[OutputLimit.INCREMENT.value].any()


def test_speed_scale_flag_on_a_large_attitude_error(geometry) -> None:
    """LEVEL with a 10 deg roll error: the unscaled command exceeds v_max and is scaled."""
    config = bench_config(output_delay_periods=0, increment_limit=None)
    controller = C2Controller(geometry, config)
    bench = Bench(controller, geometry, operating_strokes(geometry))
    for _ in range(TOUCH_HOLD_SAMPLES):
        bench.step()
    assert controller.phase is C2Phase.LEVEL
    bench.tilt_rad = (math.radians(10.0), 0.0)
    for _ in range(30):  # the 2-stage attitude filter settles
        bench.step()
    raw = controller.raw_output_m_s
    assert np.max(np.abs(raw)) > geometry.max_speed_m_s
    assert controller.output_limit_flags[OutputLimit.SPEED_SCALE.value].any()
    np.testing.assert_allclose(
        controller.computed_output_m_s,
        raw * (geometry.max_speed_m_s / np.max(np.abs(raw))),
        rtol=1e-12,
        atol=0,
    )


def test_raw_output_and_flags_are_copies(geometry) -> None:
    bench = Bench(C2Controller(geometry, bench_config()), geometry, np.full(4, 0.1))
    bench.step(np.zeros(4))
    controller = bench.controller
    controller.raw_output_m_s[:] = -1.0
    controller.output_limit_flags[OutputLimit.INCREMENT.value][:] = False
    assert np.all(controller.raw_output_m_s > 0.0)
    assert controller.output_limit_flags[OutputLimit.INCREMENT.value].all()


def test_command_components_are_copies(geometry) -> None:
    bench = twist_ready_bench(geometry)
    bench.step(lifted_rr_forces())
    components = bench.controller.command_components_m_s
    components["reapproach"][:] = 0.0
    assert np.any(bench.controller.command_components_m_s["reapproach"] != 0.0)


# --- TOUCH free-air reference from moving samples (P-S8-6, rev. 43 213.3.1 / 213.8) ----------


CHECK_END_READING_FS8_N = -8.97e3
"""Spec 213.3.1: front leg, F_s 8 kN, the CHECK end holds a retraction (-F_s - m g)."""
EXTENDING_READING_FS8_N = 7.02e3
"""Spec 213.3.1: the same leg extending in the air (+F_s - m g)."""
HANGING_READING_FS0_N = -1.0472e3
"""F_s 0: the rod weight hanging (-m g, front)."""
TOUCHDOWN_STEP_N = 30e3
"""Spec 213.8 P-S8-6 test 2: the pad load step on contact."""
FREE_AIR_SAMPLES_BEFORE_STEP = 10


def touch_config(**r8_changes) -> C2Config:
    """The preset with the combined judge and no CHECK (TOUCH from the first sample)."""
    config = replace(bench_config(), contact=ContactJudge.COMBINED)
    return replace(config, r8=replace(config.r8, **r8_changes))


@dataclass
class TouchBench:
    """10 Hz TOUCH readings given per sample; the motor strokes follow the returned (delayed,
    d = 1) commands, so the first two samples do not move (spec 213.3.1)."""

    controller: C2Controller
    geometry: C2Geometry
    strokes_m: np.ndarray = field(default_factory=lambda: np.full(4, 0.1))
    t_s: float = 0.0

    def step(self, cylinder_force_N: np.ndarray) -> np.ndarray:
        """One period; a negative force is read on the rod side (``p_h A_p - p_r A_ann``)."""
        self.t_s = round(self.t_s + PERIOD_S, 10)
        force = np.asarray(cylinder_force_N, dtype=float)
        reading = Measurements(
            t_s=self.t_s,
            specific_force_m_s2=up_in_body((0.0, 0.0)),
            angular_rate_rad_s=np.zeros(3),
            head_pressure_Pa=np.maximum(force, 0.0) / self.geometry.head_area_m2,
            rod_pressure_Pa=np.maximum(-force, 0.0) / self.geometry.annulus_area_m2,
            stroke_m=self.strokes_m.copy(),
            stroke_corrected_m=self.strokes_m.copy(),
        )
        command = np.array(self.controller.update(reading).leg_speed_m_s)
        self.strokes_m = self.strokes_m + command * PERIOD_S
        return self.controller._state.touch_seen.copy()


def run_touch(geometry: C2Geometry, readings_N: list[float], **r8_changes) -> list[np.ndarray]:
    """``touch_seen`` after each sample; every leg gets the same reading."""
    bench = TouchBench(C2Controller(geometry, touch_config(**r8_changes)), geometry)
    seen = []
    for reading in readings_N:
        seen.append(bench.step(np.full(4, reading)))
        assert bench.controller.phase is C2Phase.TOUCH or seen[-1].all()
    return seen


def first_seen_sample(seen: list[np.ndarray]) -> np.ndarray:
    """Index of the first sample with ``touch_seen`` per leg (-1 = never)."""
    stacked = np.array(seen)
    return np.where(stacked.any(axis=0), stacked.argmax(axis=0), -1)


def fs8_free_air_readings(sample_count: int) -> list[float]:
    """Spec 213.8 test 1: [-8.97, -8.97, +7.02, +7.02, ...] kN."""
    return [CHECK_END_READING_FS8_N] * 2 + [EXTENDING_READING_FS8_N] * (sample_count - 2)


def test_touch_friction_reversal_in_the_air_is_not_touchdown(geometry) -> None:
    """P-S8-6 test 1: the friction reversal (+16 kN on the third sample) does not latch
    ``touch_seen``; the R7 rule latched it there (14.94 kN >= 1.5 F_min, spec 213.3.1)."""
    readings = fs8_free_air_readings(30)
    seen = run_touch(geometry, readings)
    assert not np.array(seen).any()
    r7_seen = run_touch(geometry, readings, **R7_TOUCH_RULE)
    np.testing.assert_array_equal(first_seen_sample(r7_seen), [2, 2, 2, 2])


def test_touch_step_latches_after_two_samples(geometry) -> None:
    """P-S8-6 test 2: a +30 kN step after the friction reversal latches on its second
    sample."""
    readings = fs8_free_air_readings(FREE_AIR_SAMPLES_BEFORE_STEP)
    readings += [EXTENDING_READING_FS8_N + TOUCHDOWN_STEP_N] * 3
    seen = run_touch(geometry, readings)
    step_sample = FREE_AIR_SAMPLES_BEFORE_STEP
    np.testing.assert_array_equal(first_seen_sample(seen), [step_sample + 1] * 4)


def test_touch_without_friction_is_at_most_one_sample_late(geometry) -> None:
    """P-S8-6 test 3: F_s 0 (the reading only the hanging rod weight): the new rule sees the
    contact step one sample after the R7 rule, never earlier."""
    readings = [HANGING_READING_FS0_N] * FREE_AIR_SAMPLES_BEFORE_STEP
    readings += [HANGING_READING_FS0_N + TOUCHDOWN_STEP_N] * 3
    new_first = first_seen_sample(run_touch(geometry, readings))
    r7_first = first_seen_sample(run_touch(geometry, readings, **R7_TOUCH_RULE))
    np.testing.assert_array_equal(r7_first, [FREE_AIR_SAMPLES_BEFORE_STEP] * 4)
    np.testing.assert_array_equal(new_first - r7_first, [1, 1, 1, 1])


def test_touch_waits_for_three_moving_samples(geometry) -> None:
    """A load step on the first moving samples is not judged before the reference holds
    three moving samples (its touchdown load is -inf until then)."""
    bench = TouchBench(C2Controller(geometry, touch_config()), geometry)
    for _ in range(4):  # samples 0, 1 still; 2, 3 moving
        bench.step(np.full(4, EXTENDING_READING_FS8_N))
    assert np.isnan(bench.controller._state.free_air_force_N).all()
    bench.step(np.full(4, EXTENDING_READING_FS8_N))  # third moving sample
    np.testing.assert_allclose(bench.controller._state.free_air_force_N, EXTENDING_READING_FS8_N)


def test_touch_uses_the_rod_weight_of_each_leg(geometry) -> None:
    """P-S8-6: front 1047 N, rear 718 N. A step 0.9 kN above ``1.5 F_min`` over the free air
    reaches the touchdown load on the rear legs only."""
    rod_weight = geometry.rod_weight_N
    assert rod_weight is not None
    assert rod_weight[:2] == pytest.approx(1047.2, abs=1.0)
    assert rod_weight[2:] == pytest.approx(717.5, abs=1.0)
    touch_level = 1.5 * geometry.F_min_N
    readings = fs8_free_air_readings(FREE_AIR_SAMPLES_BEFORE_STEP)
    readings += [EXTENDING_READING_FS8_N + touch_level + 900.0] * 2
    seen = run_touch(geometry, readings)
    np.testing.assert_array_equal(seen[-1], [False, False, True, True])


# --- TOUCH free-air reference cap (P-S8-26, rev. 67 344.3, U-S8-73) -------------------------

PREGROUNDED_READING_N = 30e3
"""A leg already carrying ground load in TOUCH (PS-7a): its free-air median is this reading."""
PREGROUNDED_SAMPLES = 12
CAP_EVENT_PREFIX = "INFO_TOUCH_FREE_AIR_CAPPED:"


def cap_events(controller: C2Controller) -> list[str]:
    return [event.name for event in controller.events if event.name.startswith(CAP_EVENT_PREFIX)]


def touch_bench_run(
    geometry: C2Geometry, readings_N: list[float], **r8_changes
) -> tuple[TouchBench, list[np.ndarray]]:
    """Like :func:`run_touch`, keeping the bench (events, reference) for the checks."""
    bench = TouchBench(C2Controller(geometry, touch_config(**r8_changes)), geometry)
    seen = [bench.step(np.full(4, reading)) for reading in readings_N]
    return bench, seen


def test_cap_latches_a_leg_grounded_before_touch(geometry) -> None:
    """P-S8-26: a constant 30 kN reading is its own free-air median (touchdown load
    ``-m_rod g``, never latched). The cap cuts the reference to ``m_rod g + F_s,cap``, so the
    leg latches on the second sample after its reference holds three moving samples."""
    readings = [PREGROUNDED_READING_N] * PREGROUNDED_SAMPLES
    uncapped, uncapped_seen = touch_bench_run(
        geometry, readings, touch_free_air_cap_excess_N=None
    )
    assert not np.array(uncapped_seen).any()
    assert cap_events(uncapped.controller) == []

    capped, capped_seen = touch_bench_run(geometry, readings)
    # Samples 0, 1 still (d = 1); moving samples 2, 3, 4 fill the reference; 4, 5 latch.
    np.testing.assert_array_equal(first_seen_sample(capped_seen), [5, 5, 5, 5])
    rod_weight = np.asarray(geometry.rod_weight_N)
    expected_reference = rod_weight + np.array(R8_D1_TOUCH_FREE_AIR_CAP_EXCESS_N)
    np.testing.assert_array_equal(capped.controller._state.free_air_force_N, expected_reference)


def test_cap_event_is_recorded_once_per_leg(geometry) -> None:
    bench, _ = touch_bench_run(geometry, [PREGROUNDED_READING_N] * PREGROUNDED_SAMPLES)
    assert sorted(cap_events(bench.controller)) == sorted(
        f"{CAP_EVENT_PREFIX}{leg}" for leg in LEG_ORDER
    )


def test_cap_leaves_an_airborne_leg_with_friction_unchanged(geometry) -> None:
    """F_s 8 kN in the air (7.02 kN, below the rear cap 7.38 kN): no cap, the P-S8-6 result
    of the touchdown step (test 2) is kept bit for bit."""
    readings = fs8_free_air_readings(FREE_AIR_SAMPLES_BEFORE_STEP)
    readings += [EXTENDING_READING_FS8_N + TOUCHDOWN_STEP_N] * 3
    capped, capped_seen = touch_bench_run(geometry, readings)
    uncapped, uncapped_seen = touch_bench_run(
        geometry, readings, touch_free_air_cap_excess_N=None
    )
    assert cap_events(capped.controller) == []
    np.testing.assert_array_equal(np.array(capped_seen), np.array(uncapped_seen))
    np.testing.assert_array_equal(
        capped.controller._state.free_air_force_N, uncapped.controller._state.free_air_force_N
    )


# --- TOUCH latch candidate holds over dips (P-S8-27, rev. 68 356.3, U-S8-76 (a)) -------------

DIP_EVENT_PREFIX = "INFO_TOUCH_DIP_HELD:"
LOAD_SAMPLE = "L"
DIP_SAMPLE = "d"
STEP_SAMPLE = FREE_AIR_SAMPLES_BEFORE_STEP
"""Index of the first sample after the free air (the first ``LOAD_SAMPLE``)."""
LOADED_READING_FS0_N = HANGING_READING_FS0_N + TOUCHDOWN_STEP_N
LATCH_OFFSET = TOUCH_HOLD_SAMPLES - 1
"""A candidate started on step offset 0 latches on offset 5 (0.5 s at 10 Hz)."""


@dataclass
class DipRun:
    """Per sample after the step: candidate start, latches, pre-delay output, dip counts."""

    bench: TouchBench
    candidate_since_s: list[list[float | None]] = field(default_factory=list)
    touched: list[np.ndarray] = field(default_factory=list)
    outputs_m_s: list[np.ndarray] = field(default_factory=list)
    dip_counts: list[tuple[int, ...]] = field(default_factory=list)

    @property
    def step_t_s(self) -> float:
        return round((STEP_SAMPLE + 1) * PERIOD_S, 10)

    def latch_offset(self) -> np.ndarray:
        """First step offset each leg is touched on (-1 = never)."""
        return first_seen_sample(self.touched)

    def dip_events(self) -> list[str]:
        events = self.bench.controller.events
        return [event.name for event in events if event.name.startswith(DIP_EVENT_PREFIX)]


def leg_reading(sample: str) -> float:
    return LOADED_READING_FS0_N if sample == LOAD_SAMPLE else HANGING_READING_FS0_N


def run_dips(geometry: C2Geometry, patterns: str | list[str], **r8_changes) -> DipRun:
    """F_s 0 free air, then per leg the samples of ``patterns`` (one string = every leg)."""
    leg_patterns = [patterns] * 4 if isinstance(patterns, str) else patterns
    bench = TouchBench(C2Controller(geometry, touch_config(**r8_changes)), geometry)
    for _ in range(STEP_SAMPLE):
        bench.step(np.full(4, HANGING_READING_FS0_N))
    run = DipRun(bench)
    state = bench.controller._state
    for samples in zip(*leg_patterns, strict=True):
        bench.step(np.array([leg_reading(sample) for sample in samples]))
        run.candidate_since_s.append(list(state.touch_candidate_since_s))
        run.touched.append(state.touched.copy())
        run.outputs_m_s.append(state.output_queue[-1].copy())
        run.dip_counts.append(state.touch_dip_counts)
    return run


def test_dip_hold_changes_nothing_without_a_dip(geometry) -> None:
    """356.3 (1): no dip, the same commands with the hold off (0) and the preset (2)."""
    pattern = LOAD_SAMPLE * (LATCH_OFFSET + 3)
    held = run_dips(geometry, pattern)
    plain = run_dips(geometry, pattern, touch_hold_dip_samples=0)
    np.testing.assert_array_equal(np.array(held.outputs_m_s), np.array(plain.outputs_m_s))
    np.testing.assert_array_equal(held.latch_offset(), [LATCH_OFFSET] * 4)
    assert held.dip_events() == []


def test_dip_hold_off_drops_the_candidate_on_one_dip(geometry) -> None:
    """356.3 (1): ``touch_hold_dip_samples`` 0 is the P-S8-26 rule: one dip drops the
    candidate, the leg extends again and latches 0.5 s after the next load sample."""
    run = run_dips(geometry, "LLd" + "L" * 8, touch_hold_dip_samples=0)
    assert run.candidate_since_s[2] == [None] * 4
    np.testing.assert_array_equal(run.latch_offset(), [3 + LATCH_OFFSET] * 4)
    assert run.dip_events() == []
    meta = run.bench.controller.meta()
    json.dumps(meta)
    assert meta["touch"] == {"dip_held_samples": [0, 0, 0, 0]}


@pytest.mark.parametrize("dip_count", [1, 2])
def test_dip_hold_keeps_the_candidate_and_waits(geometry, dip_count) -> None:
    """356.3 (2): one or two dips in a row keep the candidate (its start stays), the legs
    wait (speed 0: the command is the one without the dips, ramped down by the increment
    limit) and latch 0.5 s after the candidate start, on a load sample."""
    pattern = "LL" + DIP_SAMPLE * dip_count + "L" * 6
    run = run_dips(geometry, pattern)
    undisturbed = run_dips(geometry, LOAD_SAMPLE * len(pattern))
    np.testing.assert_array_equal(np.array(run.outputs_m_s), np.array(undisturbed.outputs_m_s))
    for offset in range(2, 2 + dip_count):
        assert run.candidate_since_s[offset] == [run.step_t_s] * 4
        assert run.dip_counts[offset] == (offset - 1,) * 4
    np.testing.assert_array_equal(run.latch_offset(), [LATCH_OFFSET] * 4)
    assert sorted(run.dip_events()) == sorted(f"{DIP_EVENT_PREFIX}{leg}" for leg in LEG_ORDER)
    meta = run.bench.controller.meta()
    assert meta["touch"] == {"dip_held_samples": [dip_count] * 4}


def test_dip_hold_records_one_event_over_separate_dips(geometry) -> None:
    """Two dips apart: the count restarts on the load sample between them, the event stays
    once per leg and the meta adds both."""
    run = run_dips(geometry, "LLdLdL")
    assert run.dip_counts[3] == (0, 0, 0, 0)
    np.testing.assert_array_equal(run.latch_offset(), [LATCH_OFFSET] * 4)
    assert len(run.dip_events()) == 4
    assert run.bench.controller.meta()["touch"] == {"dip_held_samples": [2, 2, 2, 2]}


def test_three_dips_drop_the_candidate_and_extend_again(geometry) -> None:
    """356.3 (3): the third dip in a row drops the candidate as before (re-extension)."""
    run = run_dips(geometry, "LLddd" + "L" * 7)
    assert run.candidate_since_s[3] == [run.step_t_s] * 4
    assert run.candidate_since_s[4] == [None] * 4
    assert run.dip_counts[4] == (0, 0, 0, 0)
    # The held legs had ramped down to 0 (offset 3); the drop sends them out again.
    np.testing.assert_array_equal(run.outputs_m_s[3], np.zeros(4))
    assert np.all(run.outputs_m_s[4] > 0.0)
    np.testing.assert_array_equal(run.latch_offset(), [5 + LATCH_OFFSET] * 4)
    assert run.bench.controller.meta()["touch"] == {"dip_held_samples": [2, 2, 2, 2]}


def test_dip_hold_needs_touch_seen(geometry) -> None:
    """356.3 (4): on the first approach (``touch_seen`` needs two load samples in a row) a
    dip drops the candidate; no dip is held."""
    run = run_dips(geometry, "Ld" + "L" * 7)
    assert run.candidate_since_s[1] == [None] * 4
    assert run.dip_counts[1] == (0, 0, 0, 0)
    np.testing.assert_array_equal(run.latch_offset(), [2 + LATCH_OFFSET] * 4)
    assert run.dip_events() == []


def test_dip_hold_leaves_latched_legs_and_level(geometry) -> None:
    """356.3 (5): a dip on latched legs (front) counts nothing, the rear candidates hold it;
    after all legs latched (LEVEL) dips count nothing."""
    front = "L" * (LATCH_OFFSET + 1) + "d" + "L" * 6
    rear = "ddd" + "L" * 3 + "d" + "L" * 6
    run = run_dips(geometry, [front, front, rear, rear])
    dip_offset = LATCH_OFFSET + 1
    assert run.dip_counts[dip_offset] == (0, 0, 1, 1)
    assert sorted(run.dip_events()) == [f"{DIP_EVENT_PREFIX}RL", f"{DIP_EVENT_PREFIX}RR"]
    np.testing.assert_array_equal(run.latch_offset(), [LATCH_OFFSET] * 2 + [3 + LATCH_OFFSET] * 2)
    assert run.bench.controller.phase is not C2Phase.TOUCH
    level_dips = run_dips(geometry, "L" * (LATCH_OFFSET + 1) + "dd")
    assert level_dips.bench.controller.phase is not C2Phase.TOUCH
    assert level_dips.dip_counts[-1] == (0, 0, 0, 0)
    assert level_dips.dip_events() == []
