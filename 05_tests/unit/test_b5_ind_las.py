"""IND_LAS head-force lift-off approach slowdown (spec 436.9.4 table, delegation W-5).

T-I1 .. T-I10: the gates, ends, action and records of ``b5_baseline_compare.IndustryC8Las``
on synthetic loads (the C8 phase step is called directly), the bit identity with IND when it
does not act, the event order of ``HarnessIndustry`` and the U-6 record-only wiring. No
harness run (the 242 runs of rules rev2 3 are not run here).
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control import c2, c8
from outrigger_sim.params import load_params
from outrigger_sim.signals import Measurements

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))
sys.path.insert(0, str(ROOT / "04_scripts" / "04_hydraulic" / "coupled"))

import b5_baseline_compare as b5  # noqa: E402
import v5_rerun  # noqa: E402

GRAVITY_M_S2 = 9.80665
PERIOD_S = 0.1
TWISTED_LOADS_N = np.array([120e3, 20e3, 30e3, 110e3])
"""Sum 280 kN (above 0.6 W_ref), FR lightest (below 3.5 F_min), rho 0.643."""
MORE_TWISTED_LOADS_N = np.array([121e3, 19e3, 30e3, 110e3])
"""Same sum, rho a little higher (rising)."""
HEAVY_LOADS_N = np.array([150e3, 20e3, 30e3, 150e3])
"""Sum 350 kN: above 0.85 W_ref, the ``sum`` end level."""
RETRACTED_M = np.zeros(4)
"""Rod strokes with the crawler clearance below its target (LIFT goes on)."""
EXTENDED_M = np.full(4, 0.69)
"""Rod strokes with the clearance above its target (LIFT -> REGROUND)."""


@pytest.fixture
def adapter() -> b5.IndustryC8Las:
    """IND_LAS in LIFT at t = 20 s."""
    controller = b5.IndustryC8Las.from_params(load_params())
    controller.phase = c8.C8Phase.LIFT
    controller._t_s = 20.0
    return controller


def lift_step(controller, loads_N, rod_stroke_m=RETRACTED_M) -> np.ndarray:
    controller._t_s = round(controller._t_s + PERIOD_S, 10)
    return controller._phase_command(controller._t_s, np.asarray(loads_N, float), rod_stroke_m)


def start(controller) -> np.ndarray:
    lift_step(controller, TWISTED_LOADS_N)
    return lift_step(controller, MORE_TWISTED_LOADS_N)


def event_names(controller) -> list[str]:
    return [name for _, name in controller._pending_events]


def slow_mean_m_s(controller) -> float:
    return 0.16 * controller.geometry.max_speed_m_s


# T-I1 ----------------------------------------------------------------------- settings
def test_i1_settings_are_the_c2_b0_constants_and_frozen() -> None:
    settings = b5.IndustryLiftoffSlowSettings()
    assert (settings.enable, settings.sum_on_fraction_W, settings.light_leg_fraction_of_F_min,
            settings.slow_mean_fraction, settings.sum_off_fraction_W, settings.off_periods,
            settings.max_s, settings.rho_on) == (
        True, c2.R8_LAS_SUM_ON_FRACTION_W, c2.R8_LAS_LIGHT_LEG_FRACTION_OF_F_MIN,
        c2.R8_LAS_SLOW_MEAN_FRACTION, c2.R8_LAS_SUM_OFF_FRACTION_W, c2.R8_LAS_OFF_PERIODS,
        c2.R8_LAS_MAX_S, c2.R8_LAS_RHO_ON)
    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.enable = False


# T-I2 ----------------------------------------------------------------------- start, action
def test_i2_start_on_a_rising_twist_in_lift_and_scale_to_the_slow_mean(adapter) -> None:
    v_max = adapter.geometry.max_speed_m_s
    first = lift_step(adapter, TWISTED_LOADS_N)
    np.testing.assert_array_equal(first, np.full(4, v_max))  # no rho_{k-1}: not rising
    scaled = lift_step(adapter, MORE_TWISTED_LOADS_N)
    np.testing.assert_array_equal(scaled, np.full(4, v_max) * (slow_mean_m_s(adapter) / v_max))
    assert event_names(adapter) == [f"{c2.LIFTOFF_SLOW_EVENT}:FR"]
    meta = adapter.meta()["liftoff_approach_slow"]
    assert meta["load_basis"] == "head_only"
    assert meta["start_s"] == pytest.approx(20.2) and meta["start_leg"] == "FR"
    assert meta["start_rho"] == c2.diagonal_deficit_ratio(MORE_TWISTED_LOADS_N)[0]
    assert meta["start_rho_prev"] == c2.diagonal_deficit_ratio(TWISTED_LOADS_N)[0]
    assert meta["active_periods"] == 1 and meta["scaled_periods"] == 1


# T-I3 ----------------------------------------------------------------------- S7' gates
@pytest.mark.parametrize(("name", "first", "second"), [
    ("sum below alpha W_ref", TWISTED_LOADS_N * 0.5, MORE_TWISTED_LOADS_N * 0.5),
    ("light leg not below beta F_min",
     np.array([90e3, 40e3, 45e3, 105e3]), np.array([91e3, 39.5e3, 45e3, 105e3])),
    ("rho below rho_on", np.array([70e3, 30e3, 110e3, 70e3]), np.array([71e3, 29e3, 110e3, 70e3])),
    ("rho not rising", MORE_TWISTED_LOADS_N, TWISTED_LOADS_N),
])
def test_i3_s7_prime_blocks(adapter, name, first, second) -> None:
    lift_step(adapter, first)
    np.testing.assert_array_equal(lift_step(adapter, second),
                                  np.full(4, adapter.geometry.max_speed_m_s))
    assert event_names(adapter) == [], name


# T-I4 ----------------------------------------------------------------------- S2: only LIFT
def test_i4_no_start_outside_lift_and_rho_is_forgotten(adapter) -> None:
    lift_step(adapter, TWISTED_LOADS_N)
    adapter.phase = c8.C8Phase.ATTITUDE  # attitude step: not a LIFT period
    adapter._slow_roll_rad = adapter._slow_pitch_rad = 1.0  # stays in ATTITUDE
    lift_step(adapter, MORE_TWISTED_LOADS_N)
    assert adapter._slow.previous_rho is None and event_names(adapter) == []
    adapter.phase = c8.C8Phase.LIFT
    lift_step(adapter, MORE_TWISTED_LOADS_N)  # first LIFT step again: no rho_{k-1}
    assert event_names(adapter) == []


# T-I5 ----------------------------------------------------------------------- end phase
def test_i5_lift_to_reground_period_ends_with_phase_and_keeps_its_command(adapter) -> None:
    start(adapter)
    out = lift_step(adapter, MORE_TWISTED_LOADS_N, EXTENDED_M)  # _lift moves on to REGROUND
    np.testing.assert_array_equal(out, np.zeros(4))
    assert adapter.phase is c8.C8Phase.REGROUND
    assert event_names(adapter) == [f"{c2.LIFTOFF_SLOW_EVENT}:FR",
                                    f"{c2.LIFTOFF_SLOW_END_EVENT}:phase"]
    assert adapter.meta()["liftoff_approach_slow"]["end_reason"] == "phase"


# T-I6 ----------------------------------------------------------------------- end sum
def test_i6_end_on_the_load_sum_after_five_active_periods_in_a_row(adapter) -> None:
    v_max = adapter.geometry.max_speed_m_s
    start(adapter)
    for _ in range(4):
        assert not np.array_equal(lift_step(adapter, HEAVY_LOADS_N), np.full(4, v_max))
    lift_step(adapter, MORE_TWISTED_LOADS_N)  # below: the count returns to 0
    for _ in range(4):
        lift_step(adapter, HEAVY_LOADS_N)
    np.testing.assert_array_equal(lift_step(adapter, HEAVY_LOADS_N), np.full(4, v_max))
    assert event_names(adapter)[-1] == f"{c2.LIFTOFF_SLOW_END_EVENT}:sum"
    assert adapter._slow.end_s == pytest.approx(21.2)


# T-I7 ----------------------------------------------------------------------- end time
def test_i7_end_on_time(adapter) -> None:
    start(adapter)  # t_start 20.2 s
    for _ in range(14):
        lift_step(adapter, MORE_TWISTED_LOADS_N)
    np.testing.assert_array_equal(lift_step(adapter, MORE_TWISTED_LOADS_N),
                                  np.full(4, adapter.geometry.max_speed_m_s))
    meta = adapter.meta()["liftoff_approach_slow"]
    assert meta["end_reason"] == "time" and meta["end_s"] == pytest.approx(21.7)
    assert meta["active_periods"] == 15


# T-I8 ----------------------------------------------------------------------- one start
def test_i8_one_start_per_run_and_none_after_lift_was_left(adapter) -> None:
    start(adapter)
    for _ in range(15):
        lift_step(adapter, MORE_TWISTED_LOADS_N)  # ends on time
    lift_step(adapter, TWISTED_LOADS_N)
    lift_step(adapter, MORE_TWISTED_LOADS_N)  # gates hold again: no second start
    assert sum(name.startswith(f"{c2.LIFTOFF_SLOW_EVENT}:") for name in event_names(adapter)) == 1
    fresh = b5.IndustryC8Las.from_params(load_params())
    fresh.phase = c8.C8Phase.LIFT
    fresh._t_s = 20.0
    lift_step(fresh, TWISTED_LOADS_N, EXTENDED_M)  # leaves LIFT
    fresh.phase = c8.C8Phase.LIFT  # (a C8 run never comes back; forced here)
    start(fresh)
    assert event_names(fresh) == [] and fresh._slow.has_left_lift


# T-I9 ----------------------------------------------------------------------- bit identity
def _measurements(t_s: float, head_Pa: np.ndarray, geometry) -> Measurements:
    strokes = geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m
    level = np.array([0.0, 0.0, GRAVITY_M_S2])
    return Measurements(
        t_s=t_s, specific_force_m_s2=level, angular_rate_rad_s=np.zeros(3),
        head_pressure_Pa=head_Pa, stroke_m=strokes, stroke_corrected_m=strokes,
        imu_specific_force_samples_m_s2=np.tile(level, (10, 1)))


def _commands(controller, loads_N: list[np.ndarray]) -> list[np.ndarray]:
    controller.phase = c8.C8Phase.LIFT
    head_area = controller.geometry.head_area_m2
    return [np.asarray(controller.update(_measurements(PERIOD_S * (k + 1), loads / head_area,
                                                       controller.geometry)).leg_speed_m_s)
            for k, loads in enumerate(loads_N)]


@pytest.mark.parametrize("enable", [False, True])
def test_i9_off_or_silent_gives_the_ind_bits(enable: bool) -> None:
    """(b) ``enable`` False = IND; (c) gates never hold (sum low) = IND, bit for bit."""
    params = load_params()
    loads = [TWISTED_LOADS_N, MORE_TWISTED_LOADS_N] * 4 if not enable else \
        [TWISTED_LOADS_N * 0.5, MORE_TWISTED_LOADS_N * 0.5] * 4
    adapter = b5.IndustryC8Las.from_params(params)
    adapter.slow_settings = b5.IndustryLiftoffSlowSettings(enable=enable)
    reference = b5.IndustryC8.from_params(params)
    for ours, theirs in zip(_commands(adapter, loads), _commands(reference, loads), strict=True):
        assert ours.tobytes() == theirs.tobytes()
    assert adapter.drain_events() == []


def test_i9_acting_run_differs_from_ind_and_acts_before_the_ramp_and_delay() -> None:
    params = load_params()
    loads = [TWISTED_LOADS_N, MORE_TWISTED_LOADS_N] + [MORE_TWISTED_LOADS_N] * 6
    ours = _commands(b5.IndustryC8Las.from_params(params), loads)
    theirs = _commands(b5.IndustryC8.from_params(params), loads)
    v_max = params.actuator.max_speed_m_s
    assert ours[1].tobytes() == theirs[1].tobytes()  # the start period's command is a period late
    assert np.all(ours[-1] <= 0.16 * v_max * (1 + 1e-12))  # ramped down to the slow mean
    assert np.max(np.abs(np.diff(np.vstack(ours), axis=0))) <= 0.25 * v_max * (1 + 1e-12)


# T-I10 ---------------------------------------------------------------------- records, wiring
def test_i10_harness_adds_the_slowdown_events_after_the_phase_event() -> None:
    wrapper = b5.HarnessIndustry(b5.IndustryC8Las.from_params(load_params()), name="IND_LAS")
    assert wrapper.name == "IND_LAS" and b5.HarnessIndustry(
        b5.IndustryC8.from_params(load_params())).name == "IND"
    inner = wrapper.inner
    inner.phase = c8.C8Phase.LIFT
    inner._pending_events.append((0.1, f"{c2.LIFTOFF_SLOW_EVENT}:FR"))
    original = inner._phase_command

    def phase_command(t_s, force_N, rod_stroke_m):  # move to REGROUND in this period
        inner.phase = c8.C8Phase.REGROUND
        return np.zeros(4)

    inner._phase_command = phase_command
    wrapper.update(_measurements(0.1, np.zeros(4), wrapper.geometry))
    inner._phase_command = original
    assert [event.name for event in wrapper.events] == [
        "ind_phase:reground", f"{c2.LIFTOFF_SLOW_EVENT}:FR"]


def test_i10_u6_record_only_wiring(tmp_path) -> None:
    assert "IND_LAS" in b5.CONTROLLERS and "IND_LAS" not in b5.DEFAULT_CONTROLLERS
    assert b5.V5_CONTROLLERS == ("C2", "ABL", "IND") and b5.V5_RECORD_CONTROLLERS == ("IND_LAS",)
    assert v5_rerun.TAG_IND_LAS == "IND_LAS"
    assert v5_rerun.controller_tag(None, "IND_LAS") == "IND_LAS"
    definition = v5_rerun.definition("VB", "IND_LAS")
    assert definition["controller_tag"] == "IND_LAS"
    assert definition["hydraulic_options"] == v5_rerun.definition("VB", "IND")["hydraulic_options"]
    assert not definition["hydraulic_options"].get("extend_start_tracked", False)  # ③ off
    assert v5_rerun.j_p3_status("IND_LAS", None, False, True) == "not_applicable"
    rerun = v5_rerun.RerunOptions("VB")
    assert b5._rerun_case_ids(["A1-rigid"], ["IND_LAS"], rerun) == ["A1-rigid"]
    with pytest.raises(SystemExit, match="alone"):
        b5._rerun_case_ids(["A1-rigid"], ["IND", "IND_LAS"], rerun)
    args = b5._parse_args(["run", "--cases", "wide", "--controllers", "IND_LAS",
                           "--v5-setting", "VB"])
    assert b5._out_path(args, v5_rerun.options_from_args(args)) == (
        v5_rerun.OUT_DIR / "las" / "u6_b5_wide_VB_IND_LAS.json")
    assert b5._parse_args(["run"]).controllers == "C2,ABL,IND,ABL28"


def test_i11_ind_las_needs_the_v5_setting() -> None:
    """Integrity Low: without ``--v5-setting`` the default file is ``rev84/b5_<label>.json``."""
    with pytest.raises(SystemExit, match="needs --v5-setting"):
        b5._rerun_case_ids(["A1-rigid"], ["IND_LAS"], v5_rerun.RerunOptions())
    with pytest.raises(SystemExit, match="needs --v5-setting"):
        b5.main(["run", "--cases", "A1-rigid", "--controllers", "IND_LAS"])
    assert b5._rerun_case_ids(["A1-rigid"], ["C2", "IND"], v5_rerun.RerunOptions()) == [
        "A1-rigid"]


def test_i12_u6_default_file_is_in_las() -> None:
    args = b5._parse_args(["run", "--cases", "wide", "--v5-setting", "VB"])
    assert b5._out_path(args, v5_rerun.options_from_args(args)) == (
        v5_rerun.LAS_OUT_DIR / "u6_b5_wide_VB.json")
