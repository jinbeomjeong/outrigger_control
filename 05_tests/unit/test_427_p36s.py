"""Wrapper token P36s of ``s9_slope_fix_candidates.py`` (control spec 427.9 / 427.10, P-S8-36 SGS:
soil guard stop) and the ``stroke_limited_stop`` class of ``soil_guard_stop_rule.py``.

427.10 tests: the soil sign (soil mode / c_min(t_P) and the settle tilt / cleared after a LOC
revocation), the stop in the first guard period, the safe-stop conditions and the judges'
class. The command-hash test (token off = current, three cases) and the two representative
cases are CLI runs of the wrapper, not unit tests.
"""

from __future__ import annotations

import contextlib
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

import s9_slope_fix_candidates as fx  # noqa: E402
import s9_soil_slope as slope  # noqa: E402
import soil_guard_stop_rule as stop_rule  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

F_MIN_KN = 9.415
TILTED_RAD = (math.radians(1.2), 0.0)
LEVEL_RAD = (math.radians(0.9), math.radians(-0.5))
GUARDED_FR = np.array([False, True, False, False])
SOIL_STOP_FR = "FAULT_LIFT_STROKE_LIMIT:soil:FR"


@pytest.fixture(scope="module")
def params():
    return load_params()


def p36s_controller(params, name: str = "P36s", *, phase=c2.C2Phase.LEVEL):
    cls = fx.make_candidate_class(c2, c2.C2Controller, fx.parse_candidate(name))
    controller = cls.from_params(params, c2.C2Config().with_10hz_d1())
    controller.reset()
    controller._state.phase = phase
    return controller


def confirm_loc(controller, t_s: float, *, soil_mode: bool = False,
                c_min_at_P_m: float | None = 0.0, settle_rad=LEVEL_RAD) -> None:
    """The LOC state the latch reads, then the latch itself (as after ``_confirm_liftoff``)."""
    soil = controller._soil_state()
    soil.is_liftoff_confirmed = True
    soil.soil_mode_start_s = 1.0 if soil_mode else None
    soil.clearance_at_plateau_start_m = c_min_at_P_m
    controller._settle_attitude_rad = lambda: settle_rad
    controller._p36s_latch_soil_sign(t_s)


def event_names(controller) -> list[str]:
    return [e.name for e in controller.events]


# --- token ---------------------------------------------------------------------------------------


def test_token_and_default() -> None:
    assert fx.parse_candidate("P36s").p36s
    assert not fx.parse_candidate("current").p36s
    assert "P36s" in fx.CANDIDATE_TOKENS


# --- soil sign -----------------------------------------------------------------------------------


def test_soil_sign_from_the_soil_mode(params) -> None:
    controller = p36s_controller(params)
    confirm_loc(controller, 20.0, soil_mode=True, c_min_at_P_m=0.0)
    assert controller.fix.p36s_soil_sign == fx.P36S_SIGN_SOIL_MODE
    assert controller._has_loc_soil_sign()


@pytest.mark.parametrize(("c_min_at_P_m", "settle_rad", "sign"), [
    (0.011, TILTED_RAD, fx.P36S_SIGN_CLEARANCE_TILT),
    (0.009, TILTED_RAD, None),          # c_min(t_P) not above 10 mm
    (0.011, LEVEL_RAD, None),           # settle tilt not above 1 deg
    (None, TILTED_RAD, None),
])
def test_soil_sign_from_clearance_and_tilt(params, c_min_at_P_m, settle_rad, sign) -> None:
    controller = p36s_controller(params)
    confirm_loc(controller, 20.0, c_min_at_P_m=c_min_at_P_m, settle_rad=settle_rad)
    assert controller.fix.p36s_soil_sign == sign
    assert controller._has_loc_soil_sign() is (sign is not None)  # the L1gs gate of 03_src


def test_no_latch_without_a_confirmed_loc(params) -> None:
    controller = p36s_controller(params)
    controller._soil_state().soil_mode_start_s = 1.0
    controller._p36s_latch_soil_sign(20.0)
    assert controller.fix.p36s_soil_sign is None and controller.fix.p36s_sign_history == []


@pytest.mark.parametrize("revoke", ["project_revoke", "l1_token_revoke", "e2_clear"])
def test_loc_revocation_clears_the_sign_and_the_next_loc_judges_again(params, revoke) -> None:
    controller = p36s_controller(params)
    confirm_loc(controller, 20.0, soil_mode=True)
    controller._p36s_clear_soil_sign_without_loc(20.5)  # LOC still confirmed: kept
    assert controller.fix.p36s_soil_sign == fx.P36S_SIGN_SOIL_MODE
    if revoke == "project_revoke":
        controller._revoke_loc(21.0, 3000.0)  # 03_src P-S8-33
    elif revoke == "l1_token_revoke":
        controller._revoke_liftoff(21.0, 3000.0)  # wrapper L1 / L1g / L1gs
    else:
        controller._clear_liftoff_confirmation()  # E2 / P36 re-lift
    controller._p36s_clear_soil_sign_without_loc(21.0)  # what ``update`` runs after the period
    assert controller.fix.p36s_soil_sign is None
    assert controller.fix.p36s_sign_history[-1]["cleared"]
    confirm_loc(controller, 25.0, c_min_at_P_m=0.002, settle_rad=LEVEL_RAD)
    assert controller.fix.p36s_soil_sign is None  # a LOC without either sign
    confirm_loc(controller, 30.0, c_min_at_P_m=0.015, settle_rad=TILTED_RAD)
    assert controller.fix.p36s_soil_sign == fx.P36S_SIGN_CLEARANCE_TILT


# --- stop ----------------------------------------------------------------------------------------


def test_guard_period_with_the_sign_stops_and_blocks_done(params) -> None:
    controller = p36s_controller(params)
    confirm_loc(controller, 20.0, soil_mode=True)
    state = controller._state
    state.roll_integral, state.pitch_integral = 0.01, -0.02
    controller._record_lift_guard_period(40.0, GUARDED_FR, c2.LiftGuardMode.SHIFT_DOWN)
    assert controller.fix.p36s_due["legs"] == (1,)
    state.phase = c2.C2Phase.DONE  # what the LEVEL step of this period decided
    state.roll_integral = 0.5  # wound during the period: the stop keeps the start values
    out = controller._p36s_stop((0.01, -0.02), np.full(4, 0.003))
    np.testing.assert_array_equal(out, np.zeros(4))
    assert state.phase in (c2.C2Phase.FAULT, c2.C2Phase.FAULT_REGROUND)
    assert (state.roll_integral, state.pitch_integral) == (0.01, -0.02)
    assert event_names(controller)[-1] == SOIL_STOP_FR
    stop = controller.fix.p36s_stop
    assert stop["t_s"] == 40.0 and stop["legs"] == "FR" and stop["mode"] == "shift_down"
    assert stop["done_blocked"] and stop["soil_sign"] == fx.P36S_SIGN_SOIL_MODE
    assert controller.fix.p36s_due is None


def test_no_stop_without_the_sign(params) -> None:
    controller = p36s_controller(params)
    confirm_loc(controller, 20.0, c_min_at_P_m=0.002)
    controller._record_lift_guard_period(40.0, GUARDED_FR, c2.LiftGuardMode.HOLD_ALL)
    assert controller.fix.p36s_due is None and controller.fix.p36s_guard_t_s is None


def test_record_only_without_the_token(params) -> None:
    controller = p36s_controller(params, name="current")
    confirm_loc(controller, 20.0, soil_mode=True)
    controller._record_lift_guard_period(40.0, GUARDED_FR, c2.LiftGuardMode.HOLD_ALL)
    controller._record_lift_guard_period(40.1, GUARDED_FR, c2.LiftGuardMode.HOLD_ALL)
    assert controller.fix.p36s_due is None
    record = fx.p36s_record(controller.fix)
    assert record["guard_t_s"] == 40.0 and record["stop"] is None
    assert record["soil_sign"] == fx.P36S_SIGN_SOIL_MODE
    assert not fx.has_candidate_acted({"metrics": {"p36s": record}})


def test_a_fault_of_the_level_step_is_kept(params) -> None:
    controller = p36s_controller(params)
    confirm_loc(controller, 20.0, soil_mode=True)
    controller._record_lift_guard_period(40.0, GUARDED_FR, c2.LiftGuardMode.HOLD_ALL)
    controller._state.phase = c2.C2Phase.FAULT  # e.g. FAULT_STROKE_END in the same period
    speeds = np.zeros(4)
    assert controller._p36s_stop((0.0, 0.0), speeds) is speeds
    assert controller.fix.p36s_stop is None and controller.fix.p36s_preempted == "fault"
    assert SOIL_STOP_FR not in event_names(controller)


def test_stop_is_an_acted_fix() -> None:
    fix = fx._FixState()
    fix.p36s_stop = {"t_s": 40.0, "legs": "FR"}
    assert fx.has_candidate_acted({"metrics": {"p36s": fx.p36s_record(fix)}})


# --- safe-stop rule ------------------------------------------------------------------------------


def pressure_record(max_bar: float = 150.0, saturation_ms: int = 0) -> dict:
    return {"max_moving_bar": max_bar, "saturation_ms": saturation_ms}


def safe_stop_row(names=("WARN_LIFT_STROKE_LIMITED:FR", SOIL_STOP_FR), lifted=(),
                  min_force_kN=12.0, pressure=None):
    return stop_rule.stroke_limited_stop_row(
        list(names), list(lifted), min_force_kN, F_MIN_KN,
        pressure_record() if pressure is None else pressure)


def test_rule_without_a_soil_stop_is_none() -> None:
    assert safe_stop_row(names=("FAULT_LIFT_STROKE_LIMIT:FR",)) is None


def test_rule_all_conditions_pass() -> None:
    row = safe_stop_row()
    assert row["pass"] and all(row["conditions"].values())
    assert row["stop_event"] == SOIL_STOP_FR


@pytest.mark.parametrize(("kwargs", "condition"), [
    ({"names": ("FAULT_STROKE_END:FR", SOIL_STOP_FR)}, "stop_reason_soil"),
    ({"names": (SOIL_STOP_FR, "FAULT_STROKE_END:FR")}, "no_stroke_end_fault"),
    ({"lifted": ("RL",)}, "no_leg_lift"),
    ({"min_force_kN": 9.0}, "min_force_after_off"),
    ({"min_force_kN": None}, "min_force_after_off"),
    ({"pressure": pressure_record(180.5)}, "moving_pressure"),
    ({"pressure": pressure_record(saturation_ms=1)}, "no_saturation"),
    ({"pressure": {}}, "moving_pressure"),
])
def test_rule_one_violation_fails(kwargs, condition) -> None:
    row = safe_stop_row(**kwargs)
    assert not row["pass"] and not row["conditions"][condition]


def test_moving_pressure_record() -> None:
    record = stop_rule.MovingPressureRecord()
    area_m2 = np.array([0.01, 0.01, 0.01, 0.01])
    record.add(1.0, [190e3, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0], area_m2)  # standing: ignored
    record.add(1.001, [170e3, 100e3, 0.0, 0.0], [0.0, -0.01, 0.0, 0.0], area_m2)
    record.add(1.002, [215e3, 0.0, 0.0, 0.0], [0.01, 0.0, 0.0, 0.0], area_m2)
    out = record.to_dict()
    assert out["max_moving_bar"] == pytest.approx(215.0) and out["max_moving_leg"] == "FL"
    assert out["saturation_ms"] == 1 and out["chunks"] == 3
    assert out["max_extending_bar"] == pytest.approx(215.0)


# --- judges --------------------------------------------------------------------------------------


def classify_with(soil_stop) -> str:
    p3 = {"P3-1": {"pass": True}, "fault_ready": {"pass": False, "has_fault": True}}
    stroke = {"stroke_faults": [SOIL_STOP_FR], "guard_warning": True, "pass": False,
              "lifted_legs": []}
    if soil_stop is not None:
        stroke["soil_stop"] = soil_stop
    return slope.classify(p3, stroke, None)


def test_slope_classify() -> None:
    assert classify_with(safe_stop_row()) == slope.VERDICT_STROKE_LIMITED_STOP
    assert classify_with(safe_stop_row(lifted=("FL",))) == slope.VERDICT_FAIL
    assert classify_with(None) == slope.VERDICT_FAIL  # a stored row without the key: as before


@contextlib.contextmanager
def _argv_as_root():
    saved = sys.argv
    sys.argv = [saved[0] if saved else "", str(ROOT)]  # r72 reads the root at import
    try:
        yield
    finally:
        sys.argv = saved


def test_r72_soil_stop_record() -> None:
    with _argv_as_root():
        import r72_g6_screen as g6
    plant = SimpleNamespace(Wr=np.array([1000.0, 1000.0, 700.0, 700.0]))
    names = ["WARN_LIFT_STROKE_LIMITED:FR", SOIL_STOP_FR]
    controller = SimpleNamespace(events=[SimpleNamespace(name=name) for name in names])
    out = {"t_level_s": 10.0}
    pressure = stop_rule.MovingPressureRecord()
    pressure.max_moving_bar = 120.0
    g6._CAP.clear()
    g6._CAP.update(moving_pressure=pressure, fmin_log=[
        (9.9, np.array([-2000.0, 50e3, 50e3, 50e3])),  # before LEVEL: not a lift
        (10.1, np.array([40e3, 40e3, 30e3, 30e3]))])
    row = g6._soil_stop_record(controller, plant, out, 12.0, F_MIN_KN)
    assert row["pass"] and row["lifted_legs"] == []
    g6._CAP["fmin_log"].append((10.2, np.array([40e3, 40e3, -800.0, 30e3])))  # RL contact <= 0
    row = g6._soil_stop_record(controller, plant, out, 12.0, F_MIN_KN)
    assert not row["pass"] and row["lifted_legs"] == ["RL"]
    controller.events = [SimpleNamespace(name="FAULT_LIFT_STROKE_LIMIT:FR")]
    assert g6._soil_stop_record(controller, plant, out, 12.0, F_MIN_KN) is None
    g6._CAP.clear()


def test_compare_counts_a_safe_stop_apart() -> None:
    before = {"verdict": "stroke_limited_pass", "passed": True, "hash": "a"}
    after = {"suite": "slope", "id": "H3|J2|B|top|roll_pos@k0.75", "candidate": "P36s",
             "verdict": fx.VERDICT_STROKE_LIMITED_STOP, "passed": False, "hash": "b",
             "metrics": {"p36s": {"stop": {"t_s": 40.0}}}}
    summary = fx.summarize([{**before, "suite": "slope", "id": after["id"],
                             "candidate": fx.BASELINE}, after])
    entry = summary["by_suite_candidate"]["slope|P36s"]
    assert (entry["safe_stop"], entry["pass_to_safe_stop"], entry["pass_to_fail"]) == (1, 1, 0)
    row = summary["rows"][0]
    assert row["safe_stop_after"] and row["acted"]
    assert "pass -> stroke_limited_stop" in row["a3_reasons"]
