"""C2 P-S8-31 slope clearance margin (control spec 414 / 417.5, user decision 2026-10-29,
decision 11: variant E3c10), tests 1 .. 12 of 414.4.

Synthetic 10 Hz benches of ``test_c2_r8d1.py`` / ``test_c2_p28.py``; the LOC is forced through
``_confirm_liftoff`` with one plateau sample, the settle attitude is set in the soil state (no
CHECK) or as the CHECK crawler attitude. Test 11 runs the study-1 harness of
``s9_slope_fix_candidates.py`` in a subprocess (slow).
"""

from __future__ import annotations

import json
import math
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_c2_p28 import level_bench, p28_config, plateau_sample, stroke_reading  # same folder
from test_c2_r8d1 import operating_strokes  # same test folder

from outrigger_sim.control.c2 import (
    SLOPE_MARGIN_EVENT,
    C2Config,
    C2Controller,
    C2Geometry,
    C2Thresholds,
    RodStrokeFallback,
    SlopeClearanceMarginSettings,
    _RunState,
)
from outrigger_sim.control.target import AttitudeTarget, TargetAcceptance
from outrigger_sim.params import load_params
from outrigger_sim.sensors.imu import STANDARD_GRAVITY_M_S2

ROOT = Path(__file__).resolve().parents[2]
TARGET_M = 0.05
RAISED_TARGET_M = 0.08
SOIL_SIGN_CLEARANCE_M = 0.015
"""``c_min(t_P)`` of the forced LOC sample: above the 10 mm soil sign."""
TILT_RAD = math.radians(1.2)
STEPS_AFTER_LOC = 40
WRAPPER_CASE = "H3|J1|B|top|roll_pos@k0.75"
WRAPPER_RECORDS = ROOT / "06_analysis" / "02_control" / "s9" / "rev81" / "fix_slope_E3c.json"
WRAPPER_SCRIPT = ROOT / "04_scripts" / "03_control" / "s9" / "s9_slope_fix_candidates.py"
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
"""The study-1 harness needs dynamics-dev (numba, sympy), not the Chrono-dev test env."""


@pytest.fixture(scope="module")
def geometry() -> C2Geometry:
    return C2Geometry.from_params(load_params())


def margin_config(**margin_changes) -> C2Config:
    """Bench preset with the soil response of the R8 preset and the R8 slope margin."""
    config = p28_config()
    assert config.slope_clearance_margin.enable  # bench_config derives from with_10hz_d1
    return replace(
        config, slope_clearance_margin=replace(config.slope_clearance_margin, **margin_changes)
    )


def confirm_liftoff(
    controller: C2Controller,
    geometry: C2Geometry,
    settle_rad: tuple[float, float] | None,
    clearance_at_P_m: float = SOIL_SIGN_CLEARANCE_M,
    t_s: float = 5.0,
) -> None:
    """Force a LOC whose plateau-start sample reads exactly ``clearance_at_P_m`` on every
    corner (set directly: the stroke round trip would add rounding at the 10 mm boundary)."""
    controller._soil_state().settle_attitude_rad = settle_rad
    sample = plateau_sample(geometry, geometry.operating_extension_m(clearance_at_P_m), t_s)
    sample = replace(sample, corner_clearance_m=np.full(4, clearance_at_P_m))
    weight_N = geometry.superstructure_mass_kg * STANDARD_GRAVITY_M_S2
    controller._confirm_liftoff(t_s, [sample], weight_N)


def margin_events(controller: C2Controller) -> list[str]:
    return [event.name for event in controller.events
            if event.name.startswith(SLOPE_MARGIN_EVENT)]


def is_applied(controller: C2Controller) -> bool:
    return controller._clearance_target_m() != TARGET_M


# --- 1, 2: settings ----------------------------------------------------------------------------


def test_1_class_default_is_off_and_keeps_the_target(geometry) -> None:
    config = C2Config()
    assert config.slope_clearance_margin == SlopeClearanceMarginSettings()
    assert not config.slope_clearance_margin.enable
    assert _RunState.clearance_target_m is None  # class attribute (old pickles)
    controller = C2Controller(geometry, replace(p28_config(),
                                                slope_clearance_margin=SlopeClearanceMarginSettings()))
    confirm_liftoff(controller, geometry, (TILT_RAD, 0.0))
    assert controller._clearance_target_m() == TARGET_M
    assert margin_events(controller) == []


def test_1_no_firing_keeps_the_commands_of_the_margin_off(geometry) -> None:
    """A LOC below the tilt: preset and margin-off runs command bit for bit alike."""
    outputs = []
    for config in (margin_config(), margin_config(enable=False)):
        bench = level_bench(geometry, config, operating_strokes(geometry))
        confirm_liftoff(bench.controller, geometry, (math.radians(0.9), 0.0), t_s=bench.t_s)
        for _ in range(STEPS_AFTER_LOC):
            bench.step()
        outputs.append(np.array(bench.outputs))
    np.testing.assert_array_equal(outputs[0], outputs[1])


def test_2_r8_preset_values() -> None:
    settings = C2Config().with_10hz_d1().slope_clearance_margin
    assert settings == SlopeClearanceMarginSettings(
        enable=True,
        tilt_min_rad=math.radians(1.0),
        margin_m=0.030,
        require_soil_use=False,
        min_clearance_at_P_m=0.010,
    )
    assert C2Config().with_soil_response().slope_clearance_margin == settings


# --- 3 .. 6: firing ----------------------------------------------------------------------------


@pytest.mark.parametrize("settle_rad", [(TILT_RAD, 0.0), (0.0, -TILT_RAD)])
def test_3_tilted_settle_raises_the_target_once(geometry, settle_rad) -> None:
    controller = C2Controller(geometry, margin_config())
    confirm_liftoff(controller, geometry, settle_rad)
    assert controller._clearance_target_m() == pytest.approx(RAISED_TARGET_M, abs=1e-15)
    assert margin_events(controller) == [f"{SLOPE_MARGIN_EVENT}:80"]
    meta = json.loads(json.dumps(controller.meta()))["slope_clearance_margin"]
    assert meta["is_applied"] and meta["t_applied_s"] == 5.0
    assert meta["clearance_target_m"] == pytest.approx(RAISED_TARGET_M)
    assert meta["settle_attitude_deg"] == pytest.approx([math.degrees(v) for v in settle_rad])
    assert controller.config.thresholds.clearance_target_m == TARGET_M  # config unchanged


@pytest.mark.parametrize("settle_rad", [(math.radians(1.0), 0.0), (0.0, math.radians(-0.9)),
                                        None])
def test_4_boundary_tilts_and_unknown_settle_do_not_fire(geometry, settle_rad) -> None:
    controller = C2Controller(geometry, margin_config())
    confirm_liftoff(controller, geometry, settle_rad)
    assert not is_applied(controller)
    assert margin_events(controller) == []
    assert controller.meta()["slope_clearance_margin"]["is_applied"] is False


def test_5_a_second_loc_does_not_add_the_margin_again(geometry) -> None:
    controller = C2Controller(geometry, margin_config())
    confirm_liftoff(controller, geometry, (TILT_RAD, 0.0), t_s=5.0)
    controller._soil_state().is_liftoff_confirmed = False
    confirm_liftoff(controller, geometry, (TILT_RAD, 0.0), t_s=9.0)
    assert controller._clearance_target_m() == pytest.approx(RAISED_TARGET_M, abs=1e-15)
    assert len(margin_events(controller)) == 1


def test_6_reset_restores_the_configured_target(geometry) -> None:
    controller = C2Controller(geometry, margin_config())
    confirm_liftoff(controller, geometry, (TILT_RAD, 0.0))
    assert is_applied(controller)
    controller.reset()
    assert controller._clearance_target_m() == TARGET_M
    assert controller.meta()["slope_clearance_margin"]["t_applied_s"] is None
    confirm_liftoff(controller, geometry, (TILT_RAD, 0.0))  # the second run fires again
    assert controller._clearance_target_m() == pytest.approx(RAISED_TARGET_M, abs=1e-15)


# --- 7: every run-time use reads the effective target -------------------------------------------


def test_7_commands_equal_the_wrapper_that_replaces_the_config(geometry) -> None:
    """Spec 414.2 (5): the reference wrapper swapped ``self.config`` for one with the raised
    target at the LOC. Heave error, completion and the other run-time uses must then give the
    same commands as the implementation's run-state target."""
    implementation = level_bench(geometry, margin_config(), operating_strokes(geometry))
    wrapper = level_bench(geometry, margin_config(enable=False), operating_strokes(geometry))
    confirm_liftoff(implementation.controller, geometry, (TILT_RAD, 0.0),
                    t_s=implementation.t_s)
    confirm_liftoff(wrapper.controller, geometry, (TILT_RAD, 0.0), t_s=wrapper.t_s)
    config = wrapper.controller.config
    wrapper.controller.config = replace(
        config, thresholds=replace(config.thresholds, clearance_target_m=RAISED_TARGET_M))
    for _ in range(STEPS_AFTER_LOC):
        implementation.step()
        wrapper.step()
    np.testing.assert_array_equal(np.array(implementation.outputs), np.array(wrapper.outputs))
    assert np.any(np.array(implementation.outputs)[-STEPS_AFTER_LOC:] > 0.0)  # heave acts


def test_7_completion_clearance_uses_the_effective_target(geometry) -> None:
    controller = C2Controller(geometry, margin_config())
    assert controller._is_clearance_done(TARGET_M)
    confirm_liftoff(controller, geometry, (TILT_RAD, 0.0))
    assert not controller._is_clearance_done(TARGET_M)
    assert controller._is_clearance_done(RAISED_TARGET_M)


def test_7_target_acceptance_predicts_at_the_effective_target(geometry, monkeypatch) -> None:
    config = margin_config()
    config = replace(config, target=replace(config.target, acceptance=TargetAcceptance.REJECT))
    controller = C2Controller(geometry, config)
    seen_targets: list[float] = []
    original = C2Geometry.predicted_strokes_m

    def spy(self, motor, rod, change, clearance_target_m, corner_bias_m=None):
        seen_targets.append(clearance_target_m)
        return original(self, motor, rod, change, clearance_target_m, corner_bias_m=corner_bias_m)

    monkeypatch.setattr(C2Geometry, "predicted_strokes_m", spy)
    strokes = operating_strokes(geometry)
    reading = stroke_reading(5.0, strokes, strokes)
    controller._is_stroke_feasible(AttitudeTarget(), reading)
    confirm_liftoff(controller, geometry, (TILT_RAD, 0.0))
    controller._is_stroke_feasible(AttitudeTarget(), reading)
    assert seen_targets == [TARGET_M, pytest.approx(RAISED_TARGET_M, abs=1e-15)]


def test_7_rod_stroke_fallback_uses_the_effective_operating_point(geometry) -> None:
    controller = C2Controller(geometry, margin_config())
    assert controller.config.rod_stroke_fallback is not RodStrokeFallback.STROKE_OIL_COLUMN
    strokes = operating_strokes(geometry)
    forces = np.full(4, 80e3)
    confirm_liftoff(controller, geometry, (TILT_RAD, 0.0))
    stiffness = geometry.oil_stiffness_N_m(geometry.operating_extension_m(RAISED_TARGET_M))
    np.testing.assert_array_equal(controller._rod_stroke_without_sensor(strokes, forces),
                                  strokes - forces / stiffness)


# --- 8 .. 10, 12: conditions and validation -----------------------------------------------------


def test_8_require_soil_use_needs_the_soil_mode_or_a_corner_bias(geometry) -> None:
    """E3 original: without soil mode and with the bias inside the dead zone it stays off."""
    controller = C2Controller(geometry, margin_config(require_soil_use=True))
    confirm_liftoff(controller, geometry, (TILT_RAD, 0.0))
    soil = controller._soil_state()
    assert soil.soil_mode_start_s is None and not soil.has_corner_bias
    assert not is_applied(controller)
    with_soil_mode = C2Controller(geometry, margin_config(require_soil_use=True))
    with_soil_mode._soil_state().soil_mode_start_s = 3.0
    confirm_liftoff(with_soil_mode, geometry, (TILT_RAD, 0.0))
    assert is_applied(with_soil_mode)


def test_9_check_on_uses_the_crawler_attitude(geometry) -> None:
    config = margin_config()
    config = replace(config, target=replace(config.target, check_time_s=2.0))
    controller = C2Controller(geometry, config)
    controller._state.crawler_attitude_rad = (TILT_RAD, 0.0)
    confirm_liftoff(controller, geometry, settle_rad=(0.0, 0.0))  # soil settle level: ignored
    assert is_applied(controller)
    level_crawler = C2Controller(geometry, config)
    level_crawler._state.crawler_attitude_rad = (0.0, 0.0)
    confirm_liftoff(level_crawler, geometry, settle_rad=(TILT_RAD, 0.0))
    assert not is_applied(level_crawler)


@pytest.mark.parametrize("changes", [{"margin_m": -1e-3}, {"tilt_min_rad": -1e-3}])
def test_10_settings_validation(changes) -> None:
    with pytest.raises(ValueError):
        SlopeClearanceMarginSettings(**changes)


def test_10_raised_target_above_the_z1_limit_is_refused(geometry) -> None:
    """``c* + margin`` must stay at or below 92.39 mm (Z1); 0.08 m passes."""
    C2Controller(geometry, margin_config())
    with pytest.raises(ValueError, match="clearance_target_m"):
        C2Controller(geometry, margin_config(margin_m=0.043))
    high_target = replace(margin_config(), thresholds=C2Thresholds(clearance_target_m=0.07))
    with pytest.raises(ValueError, match="clearance_target_m"):
        C2Controller(geometry, high_target)
    C2Controller(geometry, replace(high_target, slope_clearance_margin=replace(
        high_target.slope_clearance_margin, enable=False)))  # off: only the target is checked


@pytest.mark.parametrize(("clearance_mm", "fires"), [(9.9, False), (10.0, False), (10.1, True)])
def test_12_soil_sign_boundary(geometry, clearance_mm, fires) -> None:
    controller = C2Controller(geometry, margin_config())
    confirm_liftoff(controller, geometry, (TILT_RAD, 0.0), clearance_at_P_m=clearance_mm * 1e-3)
    assert controller._soil_state().clearance_at_plateau_start_m == clearance_mm * 1e-3
    assert is_applied(controller) is fires


def test_12_no_soil_sign_condition_without_the_threshold(geometry) -> None:
    controller = C2Controller(geometry, margin_config(min_clearance_at_P_m=None))
    confirm_liftoff(controller, geometry, (TILT_RAD, 0.0), clearance_at_P_m=-0.004)
    assert is_applied(controller)


# --- 11: wrapper hash ---------------------------------------------------------------------------


@pytest.mark.slow
def test_11_study_1_case_matches_the_e3c10_wrapper_hash(tmp_path) -> None:
    """The project preset now is E3c10: the harness's "current" controller of
    ``H3|J1|B|top|roll_pos@k0.75`` commands as the stored E3c10 wrapper record (decision 11)."""
    if not HARNESS_PYTHON.exists() or not WRAPPER_RECORDS.exists():
        pytest.skip("dynamics-dev or the rev. 81 E3c records missing")
    records = json.loads(WRAPPER_RECORDS.read_text(encoding="utf-8"))["records"]
    expected = next(r["hash"] for r in records
                    if r["id"] == WRAPPER_CASE and r["candidate"] == "E3c10")
    out_path = tmp_path / "p31_wrapper_case.json"
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "OMP_NUM_THREADS": "1"}
    subprocess.run(
        [str(HARNESS_PYTHON), "-I", str(WRAPPER_SCRIPT), "run", "--suite", "slope",
         "--candidates", "current", "--filter", WRAPPER_CASE, "--workers", "1",
         "--out", str(out_path)],
        cwd=ROOT, env=environment, check=True, capture_output=True, timeout=1800,
    )
    (record,) = json.loads(out_path.read_text(encoding="utf-8"))["records"]
    assert "error" not in record, record.get("error")
    assert record["hash"] == expected
