"""Wrapper tokens P37t / R4c20 / R4c30 (control spec 428.5.2, P-S8-37) and P38z / P38z25 (spec
429.3 / 429.5, P-S8-38 ZIC) of ``s9_slope_fix_candidates.py`` and their layer modules
``p37_floor_twist.py`` / ``p38_integral_clamp.py``.

Unit tests of the token parsing and combinations, the twist ledger (delta tau, sign, limit,
settle condition, LOC clear), the R4 conditions, the ZIC rule (cap, sign, window, HOLD_ALL
restore order), the P38z1 first-DONE window (spec 429.7) and the reconstruction check of
429.5 (3). The command-hash identity (tokens off = current, three cases), the H-1 offsets and
the replay trend are CLI runs.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "04_scripts" / "03_control" / "s9", ROOT / "04_scripts" / "03_control" / "s8"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import p37_floor_twist as p37  # noqa: E402
import p38_integral_clamp as p38  # noqa: E402
import s9_slope_fix_candidates as fx  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

FLAT_RAD = (math.radians(0.4), math.radians(-0.3))
TILTED_RAD = (math.radians(1.3), 0.0)
BASE_STROKE_M = np.array([0.30, 0.31, 0.29, 0.30])


@pytest.fixture(scope="module")
def params():
    return load_params()


def candidate_controller(params, name: str, *, phase=c2.C2Phase.LEVEL):
    cls = fx.make_candidate_class(c2, c2.C2Controller, fx.parse_candidate(name))
    # The tokens were built on the preset before the spec 429.11 switch (SGS and R4 off);
    # with R4 in the preset the token R4c would find the target already raised.
    pre_switch = c2.C2Config().with_10hz_d1(soil_stop=False, flat_soil_margin_m=0.0)
    controller = cls.from_params(params, pre_switch)
    controller.reset()
    controller._state.phase = phase
    return controller


def reading_at(t_s: float, rod_stroke_m) -> SimpleNamespace:
    strokes = np.asarray(rod_stroke_m, float)
    return SimpleNamespace(t_s=t_s, rod_stroke_m=strokes, motor_stroke_m=strokes.copy())


def confirm_loc(controller, *, soil_mode: bool = False, settle_rad=FLAT_RAD) -> None:
    soil = controller._soil_state()
    soil.is_liftoff_confirmed = True
    soil.soil_mode_start_s = 1.0 if soil_mode else None
    soil.clearance_at_plateau_start_m = 0.0
    controller._settle_attitude_rad = lambda: settle_rad


def settle_attitude(controller) -> None:
    state = controller._state
    state.completion_roll_rad, state.completion_pitch_rad = controller._target_rad()


def event_names(controller) -> list[str]:
    return [e.name for e in controller.events]


# --- tokens --------------------------------------------------------------------------------------


def test_token_values() -> None:
    assert fx.parse_candidate("P37t").p37
    assert fx.parse_candidate("R4c20").r4_margin_m == pytest.approx(0.02)
    assert fx.parse_candidate("R4c30").r4_margin_m == pytest.approx(0.03)
    assert fx.parse_candidate("P38z").p38 and fx.parse_candidate("P38z").p38_cap_fraction == 0.5
    assert fx.parse_candidate("P38z25").p38_cap_fraction == 0.25
    assert fx.parse_candidate("P38z+p38_cap_fraction=0.4").p38_cap_fraction == pytest.approx(0.4)
    current = fx.parse_candidate("current")
    assert not current.p37 and current.r4_margin_m == 0.0 and not current.p38
    assert fx.parse_candidate("P38z").p38_window == p38.WINDOW_FIRST_READY  # P38z hash kept
    redesign = fx.parse_candidate("P38z1")
    assert redesign.p38 and redesign.p38_cap_fraction == 0.5
    assert redesign.integral_clamp_settings().window == p38.WINDOW_FIRST_DONE
    combined = fx.parse_candidate("R4c30+P38z1")
    assert combined.r4_margin_m == pytest.approx(0.03) and combined.p38_window == "first_done"
    with pytest.raises(ValueError, match="window"):
        p38.IntegralClampSettings(enable=True, window="first_probe")


def test_combination_and_alternatives() -> None:
    combined = fx.parse_candidate("P36s+P37t+R4c30+P38z")
    assert combined.p36s and combined.p37 and combined.p38
    assert combined.r4_margin_m == pytest.approx(0.03)
    assert fx.parse_candidate("P36c5+R4c20").p36  # different groups combine
    for name in ("R4c20+R4c30", "P38z+P38z25", "P38z+P38z1", "P38z25+P38z1", "P36c5+P36c8"):
        with pytest.raises(ValueError, match="alternatives"):
            fx.parse_candidate(name)


def test_layers_only_when_on(params) -> None:
    assert candidate_controller(params, "P36s").__class__.__name__ == "CandidateC2"
    combined = candidate_controller(params, "P36s+P37t+R4c30+P38z")
    names = [cls.__name__ for cls in type(combined).__mro__]
    assert names[:3] == ["IntegralClampFloorTwistCandidateC2", "FloorTwistCandidateC2",
                         "CandidateC2"]


# --- R1' twist ledger ----------------------------------------------------------------------------


def test_rod_twist() -> None:
    assert p37.rod_twist_m([0.4, 0.3, 0.2, 0.1]) == pytest.approx((0.4 - 0.3) - (0.2 - 0.1))


@pytest.mark.parametrize(("leg", "d_tau_m", "expected_m"), [
    (3, 0.0425, 0.0425),    # RR, H-1 trace: tau +42.5 mm -> d +42.5 mm
    (0, 0.030, 0.030),      # FL
    (1, 0.020, -0.020),     # FR: negative twist coefficient
    (2, -0.012, 0.012),     # RL
    (3, 0.0049, None),      # below 5 mm
    (3, -0.0049, None),
])
def test_twist_offset_increment(leg, d_tau_m, expected_m) -> None:
    out = p37.twist_offset_increment_m(leg, 0.010, 0.010 + d_tau_m, 0.005)
    assert out == (None if expected_m is None else pytest.approx(expected_m))


def start_and_contact(controller, leg: int, t_s: float, strokes) -> None:
    lifted = controller.config.r8.lifted_reapproach
    controller._begin_reapproach(leg, reading_at(t_s, strokes), lifted)
    controller._end_reapproach(leg, reading_at(t_s + 0.4, strokes), "contact")


def test_ledger_books_after_contact_and_settle(params) -> None:
    controller = candidate_controller(params, "P37t")
    confirm_loc(controller)
    start_and_contact(controller, 3, 30.0, BASE_STROKE_M)
    after = BASE_STROKE_M + np.array([0.0, 0.0, 0.0, 0.040])  # RR extended 40 mm
    controller._state.last_reading = reading_at(32.0, after)
    controller._state.completion_roll_rad = math.radians(0.05)  # not settled: waits
    controller._p37_settle_pending(32.0)
    assert not controller.p37_state.applied and 3 in controller.p37_state.pending
    settle_attitude(controller)
    controller._p37_settle_pending(33.0)
    np.testing.assert_allclose(controller.p37_state.offsets_m, [0, 0, 0, 0.040])
    assert event_names(controller)[-1] == "INFO_FLOOR_DROP_OFFSET:RR:40.0"
    assert not controller.p37_state.pending
    expected = controller.geometry.clearance_corners_m(after - np.array([0, 0, 0, 0.040]))
    np.testing.assert_allclose(controller._clearance_corners_m(after), expected)
    record = p37.floor_twist_record(controller)
    assert fx.has_candidate_acted({"metrics": {"p37": record}})
    assert fx.acted_parts({"metrics": {"p37": record}}) == ["P37t"]


def test_ledger_limit_and_accumulation(params) -> None:
    controller = candidate_controller(params, "P37t")
    confirm_loc(controller)
    strokes = BASE_STROKE_M.copy()
    for step, t_s in enumerate((30.0, 40.0)):
        start_and_contact(controller, 0, t_s, strokes)
        strokes = strokes + np.array([0.035, 0.0, 0.0, 0.0])
        controller._state.last_reading = reading_at(t_s + 2.0, strokes)
        settle_attitude(controller)
        controller._p37_settle_pending(t_s + 2.0)
        assert len(controller.p37_state.applied) == step + 1
    assert controller.p37_state.offsets_m[0] == pytest.approx(0.06)  # 70 mm cut at 60
    assert controller.p37_state.applied[-1]["capped"]


def test_no_offset_without_contact_before_loc_or_while_active(params) -> None:
    controller = candidate_controller(params, "P37t")
    lifted = controller.config.r8.lifted_reapproach
    controller._begin_reapproach(1, reading_at(10.0, BASE_STROKE_M), lifted)  # before the LOC
    assert not controller.p37_state.pending
    controller._end_reapproach(1, reading_at(10.5, BASE_STROKE_M), "contact")
    confirm_loc(controller)
    controller._begin_reapproach(1, reading_at(20.0, BASE_STROKE_M), lifted)
    controller._end_reapproach(1, reading_at(21.0, BASE_STROKE_M), "no_contact")
    assert not controller.p37_state.pending
    controller._begin_reapproach(2, reading_at(30.0, BASE_STROKE_M), lifted)  # still active
    controller._end_reapproach(2, reading_at(30.4, BASE_STROKE_M), "contact")
    controller._begin_reapproach(0, reading_at(30.5, BASE_STROKE_M), lifted)
    controller._state.last_reading = reading_at(31.0, BASE_STROKE_M + [0, 0, -0.02, 0])
    settle_attitude(controller)
    controller._p37_settle_pending(31.0)
    assert not controller.p37_state.applied  # a re-approach is active: waits


def test_small_twist_is_skipped_and_new_loc_clears(params) -> None:
    controller = candidate_controller(params, "P37t")
    confirm_loc(controller)
    start_and_contact(controller, 3, 30.0, BASE_STROKE_M)
    controller._state.last_reading = reading_at(31.0, BASE_STROKE_M + [0, 0, 0, 0.003])
    settle_attitude(controller)
    controller._p37_settle_pending(31.0)
    assert controller.p37_state.skipped[0]["reason"] == "below_min"
    controller.p37_state.offsets_m[3] = 0.02
    controller._apply_slope_clearance_margin(40.0)  # what a new LOC runs
    assert not controller.p37_state.offsets_m.any() and controller.p37_state.ledger_clears == 1


def test_held_run_is_booked_after_the_other_reapproach_ends(params) -> None:
    """Spec 428.5.3 item 3: a contacted run waits (not skipped) while another leg re-approaches
    and is booked with the twist of the first settled period after that."""
    controller = candidate_controller(params, "P37t")
    confirm_loc(controller)
    lifted = controller.config.r8.lifted_reapproach
    start_and_contact(controller, 3, 30.0, BASE_STROKE_M)
    controller._begin_reapproach(0, reading_at(30.5, BASE_STROKE_M), lifted)  # FL lifted
    settle_attitude(controller)
    controller._state.last_reading = reading_at(31.0, BASE_STROKE_M + [0, 0, 0, 0.010])
    controller._p37_settle_pending(31.0)
    assert not controller.p37_state.applied and not controller.p37_state.skipped
    assert controller.p37_state.pending[3]["deferred"]
    controller._end_reapproach(0, reading_at(31.4, BASE_STROKE_M), "contact")
    controller._state.last_reading = reading_at(32.0, BASE_STROKE_M + [0, 0, 0, 0.040])
    controller._p37_settle_pending(32.0)
    rr_row = next(row for row in controller.p37_state.applied if row["leg"] == "RR")
    assert rr_row["d_tau_mm"] == pytest.approx(40.0) and rr_row["deferred"]
    assert controller.p37_state.offsets_m[3] == pytest.approx(0.040)
    assert not controller.p37_state.pending


def test_held_run_at_run_end_is_pending_at_end(params) -> None:
    controller = candidate_controller(params, "P37t")
    confirm_loc(controller)
    start_and_contact(controller, 3, 30.0, BASE_STROKE_M)
    lifted = controller.config.r8.lifted_reapproach
    controller._begin_reapproach(1, reading_at(31.0, BASE_STROKE_M), lifted)  # never ends
    controller._state.last_reading = reading_at(45.0, BASE_STROKE_M)
    controller._p37_settle_pending(45.0)
    record = p37.floor_twist_record(controller)
    assert record["pending_legs"] == ["FR", "RR"] and record["pending_at_end_n"] == 2
    row = next(row for row in record["skipped"] if row["leg"] == "RR")
    assert not next(row for row in record["skipped"] if row["leg"] == "FR")["contacted"]
    assert row["reason"] == p37.SKIP_PENDING_AT_END and row["at"] == p37.PENDING_END_RUN_END
    assert row["leg"] == "RR" and row["t_s"] == 45.0 and row["contacted"] and row["deferred"]
    assert 3 in controller.p37_state.pending  # the record does not change the state
    assert not fx.has_candidate_acted({"metrics": {"p37": record}})


@pytest.mark.parametrize("at", ["new_loc", "loc_revoked"])
def test_held_run_dropped_at_loc_change(params, at) -> None:
    controller = candidate_controller(params, "P37t")
    confirm_loc(controller)
    start_and_contact(controller, 2, 30.0, BASE_STROKE_M)
    if at == "new_loc":
        controller._apply_slope_clearance_margin(40.0)
    else:
        controller._soil_state().is_liftoff_confirmed = False
        controller._p37_settle_pending(40.0)
    state = controller.p37_state
    assert not state.pending and state.pending_dropped == 1 and not state.applied
    assert state.skipped[-1] == {"t_s": 40.0, "leg": "RL", "reason": "pending_at_end",
                                 "at": at, "t_start_s": 30.0, "contacted": True,
                                 "deferred": False}
    assert p37.floor_twist_record(controller)["pending_at_end_n"] == 1


def test_zero_ledger_uses_the_base_path(params) -> None:
    controller = candidate_controller(params, "P37t")
    plain = candidate_controller(params, "current")
    np.testing.assert_array_equal(controller._clearance_corners_m(BASE_STROKE_M),
                                  plain._clearance_corners_m(BASE_STROKE_M))


# --- R4 flat-soil margin -------------------------------------------------------------------------


@pytest.mark.parametrize(("soil_mode", "settle", "has_target", "due"), [
    (True, FLAT_RAD, False, True),
    (False, FLAT_RAD, False, False),
    (True, TILTED_RAD, False, False),
    (True, None, False, False),
    (True, FLAT_RAD, True, False),  # P-S8-31 already raised the target
])
def test_flat_soil_margin_conditions(soil_mode, settle, has_target, due) -> None:
    assert p37.is_flat_soil_margin_due(soil_mode, settle, math.radians(1.0), has_target) is due


def test_flat_soil_margin_on_the_controller(params) -> None:
    controller = candidate_controller(params, "R4c30")
    confirm_loc(controller, soil_mode=True)
    controller._apply_slope_clearance_margin(25.0)
    target_m = controller.config.thresholds.clearance_target_m + 0.03
    assert controller._clearance_target_m() == pytest.approx(target_m)
    assert event_names(controller)[-1] == f"INFO_LOC_FLAT_SOIL_MARGIN:{target_m * 1e3:.0f}"
    assert fx.acted_parts({"metrics": {"p37": p37.floor_twist_record(controller)}}) == ["R4c"]
    controller._apply_slope_clearance_margin(30.0)  # target set: no second application
    assert len(controller.p37_state.flat_margins) == 1


def test_flat_soil_margin_not_without_soil_mode(params) -> None:
    controller = candidate_controller(params, "R4c20")
    confirm_loc(controller, soil_mode=False)
    controller._apply_slope_clearance_margin(25.0)
    assert controller._state.clearance_target_m is None


# --- P38 ZIC -------------------------------------------------------------------------------------


def test_integral_cap_value(params) -> None:
    config = c2.C2Config().with_10hz_d1()
    cap = p38.integral_cap(0.5, config.thresholds.done_attitude_rad,
                           config.gains.attitude_kp_1_s, config.gains.attitude_ki_1_s2)
    assert cap == pytest.approx(0.00524, abs=5e-6)  # spec 429.2: 0.00524 rad s (0.015 deg)


@pytest.mark.parametrize(("error", "integral", "expected"), [
    (-1e-4, 0.010, 0.005),    # pushes past the target, above the cap: cut
    (1e-4, -0.010, -0.005),
    (1e-4, 0.010, 0.010),     # same sign: the steady-state part is kept
    (-1e-4, 0.004, 0.004),    # below the cap
    (0.0, 0.010, 0.010),      # e = 0
    (-1e-4, 0.0, 0.0),
])
def test_clamp_rule(error, integral, expected) -> None:
    assert p38.clamped_integral(error, integral, 0.005) == expected


def run_pi(controller, error_rad: float, integral: float) -> tuple[float, float]:
    controller._p38_axis = 0
    try:
        return controller._attitude_pi(error_rad, integral)
    finally:
        controller._p38_axis = None


def test_window(params) -> None:
    controller = candidate_controller(params, "P38z")
    controller._state.last_reading = reading_at(10.0, BASE_STROKE_M)
    error, wound = -math.radians(0.1), 0.0150
    assert run_pi(controller, error, wound)[1] > 0.014  # before the LOC: untouched
    confirm_loc(controller)
    rate, cut = run_pi(controller, error, wound)
    cap = 0.5 * controller.config.thresholds.done_attitude_rad * 20.0
    assert cut == pytest.approx(cap)
    gains = controller.config.gains
    assert rate == pytest.approx(gains.attitude_kp_1_s * error + gains.attitude_ki_1_s2 * cap)
    assert event_names(controller)[-1].startswith("INFO_ATT_INT_CLAMP:roll:")
    controller._soil_state().is_liftoff_confirmed = False  # LOC revoked: the window stays
    assert run_pi(controller, error, wound)[1] == pytest.approx(cap)
    controller._state.phase = c2.C2Phase.DONE  # outside LEVEL
    assert run_pi(controller, error, wound)[1] > 0.014
    controller._state.phase = c2.C2Phase.LEVEL
    controller.p38_state.has_entered_ready = True  # after the first READY
    assert run_pi(controller, error, wound)[1] > 0.014
    record = p38.integral_clamp_record(controller)
    assert record["clamp_count"] == 2 and fx.acted_parts({"metrics": {"p38": record}}) == ["P38z"]


def phase_driven_controller(params, monkeypatch, name: str):
    """Candidate controller whose base ``update`` only sets the phase carried by the reading,
    so the ZIC layer's end-of-update latches can be driven period by period."""
    controller = candidate_controller(params, name)
    base_class = type(controller).__mro__[1]

    def set_phase(self, measurements):
        self._state.phase = measurements.phase
        self._state.last_reading = measurements
        return np.zeros(4)

    monkeypatch.setattr(base_class, "update", set_phase)
    return controller


def step(controller, t_s: float, phase) -> None:
    reading = reading_at(t_s, BASE_STROKE_M)
    reading.phase = phase
    controller.update(reading)


WOUND_ERROR_RAD, WOUND_INTEGRAL = -math.radians(0.1), 0.0150


def is_cut(controller) -> bool:
    return run_pi(controller, WOUND_ERROR_RAD, WOUND_INTEGRAL)[1] < 0.014


def test_first_done_window_ends_at_the_first_done(params, monkeypatch) -> None:
    controller = phase_driven_controller(params, monkeypatch, "P38z1")
    step(controller, 5.0, c2.C2Phase.DONE)  # a DONE before the first LOC opens nothing
    assert controller.p38_state.first_done_s is None
    confirm_loc(controller)
    step(controller, 10.0, c2.C2Phase.LEVEL)
    assert controller.p38_state.first_loc_s == 10.0
    assert is_cut(controller)  # inside: the first LOC to the first DONE
    controller._soil_state().is_liftoff_confirmed = False  # LOC revoked: the window stays (P38z)
    step(controller, 20.0, c2.C2Phase.LEVEL)
    assert is_cut(controller)
    step(controller, 50.0, c2.C2Phase.DONE)
    assert controller.p38_state.first_done_s == 50.0
    for phase in (c2.C2Phase.PROBE, c2.C2Phase.LEVEL):  # the re-level after the probe
        step(controller, 60.0, phase)
    assert not is_cut(controller)
    record = p38.integral_clamp_record(controller)
    assert record["window"] == "first_done" and record["first_done_s"] == 50.0
    assert record["clamp_count"] == 2 and fx.acted_parts({"metrics": {"p38": record}}) == ["P38z"]


def test_first_ready_window_keeps_the_relevel(params, monkeypatch) -> None:
    controller = phase_driven_controller(params, monkeypatch, "P38z")
    confirm_loc(controller)
    step(controller, 10.0, c2.C2Phase.LEVEL)
    step(controller, 50.0, c2.C2Phase.DONE)
    step(controller, 60.0, c2.C2Phase.LEVEL)
    assert controller.p38_state.first_done_s == 50.0  # recorded, but not a window end
    assert is_cut(controller)
    step(controller, 80.0, c2.C2Phase.READY)
    step(controller, 90.0, c2.C2Phase.LEVEL)
    assert not is_cut(controller)
    assert p38.integral_clamp_record(controller)["window"] == "first_ready"


def test_first_done_window_also_ends_at_ready(params, monkeypatch) -> None:
    controller = phase_driven_controller(params, monkeypatch, "R4c30+P38z1")
    confirm_loc(controller)
    step(controller, 10.0, c2.C2Phase.LEVEL)
    step(controller, 40.0, c2.C2Phase.READY)
    step(controller, 45.0, c2.C2Phase.LEVEL)
    assert controller.p38_state.first_done_s is None and not is_cut(controller)


def test_axis_names_through_attitude_rates(params) -> None:
    controller = candidate_controller(params, "P38z25")
    confirm_loc(controller)
    state = controller._state
    state.last_reading = reading_at(20.0, BASE_STROKE_M)
    state.roll_rad, state.pitch_rad = math.radians(0.05), -math.radians(0.05)
    state.roll_integral, state.pitch_integral = 0.012, -0.012
    controller._attitude_rates()
    axes = [row["axis"] for row in controller.p38_state.clamps]
    assert axes == ["roll", "pitch"]
    cap = 0.25 * controller.config.thresholds.done_attitude_rad * 20.0
    assert (state.roll_integral, state.pitch_integral) == pytest.approx((cap, -cap))


def test_hold_all_restore_runs_after_the_cut(params) -> None:
    controller = candidate_controller(params, "P38z")
    confirm_loc(controller)
    state = controller._state
    state.roll_rad, state.pitch_rad = math.radians(0.05), 0.0
    state.roll_integral, state.pitch_integral = 0.012, 0.0
    reading = reading_at(20.0, BASE_STROKE_M)
    state.last_reading = reading

    def level_step(_reading):
        controller._attitude_rates()
        state.lift_guard_mode = c2.LiftGuardMode.HOLD_ALL
        return np.zeros(4)

    controller._level_step = level_step
    controller._has_lift_guard_hold_expired = lambda t_s: False
    c2.C2Controller._level(controller, reading)
    assert controller.p38_state.clamp_count == 1  # the period's output used the cut integral
    assert state.roll_integral == 0.012  # 369.2 restore of the period start wins


def reference_pi(errors, integral: float, config, cap: float) -> list[float]:
    """429.1 reconstruction: conditional integration (band, limit) at 10 Hz, then the ZIC."""
    band_low, band_high = config.thresholds.integrator_band_rad
    limit = config.thresholds.integrator_limit_rad_s
    out = []
    for error in errors:
        if band_low < abs(error) < band_high:
            integral = min(limit, max(-limit, integral + error * config.period_s))
        if error != 0.0 and integral != 0.0 and np.sign(integral) != np.sign(error):
            integral = math.copysign(min(abs(integral), cap), integral)
        out.append(integral)
    return out


def test_reconstruction_match(params) -> None:
    controller = candidate_controller(params, "P38z")
    confirm_loc(controller)
    controller._state.last_reading = reading_at(30.0, BASE_STROKE_M)
    config = controller.config
    t = np.arange(0.0, 40.0, config.period_s)
    errors = np.radians(-0.25 * np.exp(-t / 6.0) * np.cos(2 * np.pi * t / 18.0)
                        + 0.004 * np.sin(1.3 * t))
    cap = p38.integral_cap(0.5, config.thresholds.done_attitude_rad,
                           config.gains.attitude_kp_1_s, config.gains.attitude_ki_1_s2)
    expected = reference_pi(errors, 0.0135, config, cap)
    integral, got = 0.0135, []
    for error in errors:
        integral = run_pi(controller, float(error), integral)[1]
        got.append(integral)
    np.testing.assert_allclose(got, expected, rtol=0.0, atol=1e-12)
    assert controller.p38_state.clamp_count >= 1
