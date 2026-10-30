"""Record-only additions of control spec 427.12.1 / 427.12.3 and 428.5.3 (no command change).

- ``soil_guard_stop_rule.stop_state_record``: ``stop_with_crawler_loaded`` (true crawler force at
  the soil-guard stop > 0.01 W) and the four-leg true F_cyl minimum of the stop period; the
  ``stroke_limited_stop`` class rule is unchanged (a stop before the crawler lift-off stays fail).
- ``s9_soil_slope.stroke_row`` attaches the records to its ``soil_stop`` row.
- ``p37_floor_twist``: ``p37_offset_across_revoke`` counts LOC revocations passed with a booked
  ledger offset.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "04_scripts" / "03_control" / "s9", ROOT / "04_scripts" / "03_control" / "s8"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import p37_floor_twist as p37  # noqa: E402
import s9_slope_fix_candidates as fx  # noqa: E402
import s9_soil_slope as slope  # noqa: E402
import soil_guard_stop_rule as stop_rule  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

F_MIN_KN = 9.415
WEIGHT_N = 376_700.0
SOIL_STOP_FR = "FAULT_LIFT_STROKE_LIMIT:soil:FR"
STOP_EVENTS = [(30.0, "WARN_LIFT_STROKE_LIMITED:FR"), (36.8, SOIL_STOP_FR)]
LEG_FORCE_ROWS_KN = [(36.7, [40.0, 30.0, 50.0, 45.0]), (36.8, [41.0, 12.8, 52.0, 44.0]),
                     (36.9, [5.0, 5.0, 5.0, 5.0])]


def crawler_series(force_at_stop_N: float) -> list[tuple[float, float]]:
    return [(36.798, 90_000.0), (36.799, 80_000.0), (36.8, force_at_stop_N), (36.801, 0.0)]


# --- stop_state_record ---------------------------------------------------------------------------


def test_03_src_stop_event_is_judged_by_the_same_rule() -> None:
    """The judge reads events only, so a 03_src ``soil_stop`` run gets the same records."""
    assert c2.LIFT_GUARD_SOIL_STOP_EVENT == stop_rule.SOIL_STOP_EVENT


def test_soil_stop_time() -> None:
    assert stop_rule.soil_stop_time_s(STOP_EVENTS) == pytest.approx(36.8)
    assert stop_rule.soil_stop_time_s([(1.0, "FAULT_LIFT_STROKE_LIMIT:FR")]) is None


@pytest.mark.parametrize(("crawler_N", "expected"), [
    (65_000.0, True),     # 427.12 false-LOC stops: 7 .. 65 kN on the crawler
    (3_767.0, False),     # exactly 0.01 W: not above
    (3_768.0, True),
    (0.0, False),
])
def test_stop_with_crawler_loaded(crawler_N, expected) -> None:
    record = stop_rule.stop_state_record(36.8, crawler_series(crawler_N), WEIGHT_N,
                                         LEG_FORCE_ROWS_KN)
    assert record["stop_with_crawler_loaded"] is expected
    assert record["crawler_N_at_stop"] == pytest.approx(crawler_N)
    assert record["crawler_loaded_threshold_N"] == pytest.approx(0.01 * WEIGHT_N)


def test_leg_minimum_of_the_stop_period() -> None:
    record = stop_rule.stop_state_record(36.8, crawler_series(0.0), WEIGHT_N, LEG_FORCE_ROWS_KN)
    assert record["min_true_Fcyl_at_stop_kN"] == pytest.approx(12.8)  # row at 36.8, not 36.9
    assert record["true_Fcyl_at_stop_kN"] == [41.0, 12.8, 52.0, 44.0]
    assert record["stop_t_s"] == pytest.approx(36.8)


def test_unknown_inputs_give_none() -> None:
    no_stop = stop_rule.stop_state_record(None, crawler_series(1e5), WEIGHT_N, LEG_FORCE_ROWS_KN)
    assert no_stop["stop_with_crawler_loaded"] is None
    assert no_stop["min_true_Fcyl_at_stop_kN"] is None
    record = stop_rule.stop_state_record(36.8, [], None, [])
    assert record["stop_with_crawler_loaded"] is None
    assert record["min_true_Fcyl_at_stop_kN"] is None
    before_first = stop_rule.stop_state_record(1.0, crawler_series(0.0), None, LEG_FORCE_ROWS_KN)
    assert before_first["crawler_N_at_stop"] is None
    assert before_first["min_true_Fcyl_at_stop_kN"] is None


# --- class rule unchanged ------------------------------------------------------------------------


def test_records_do_not_change_the_class() -> None:
    """427.12.1 item 1: a stop before the crawler lift-off (no minimum after it) stays fail."""
    names = [name for _, name in STOP_EVENTS]
    pressure = {"max_moving_bar": 101.2, "saturation_ms": 0}
    loaded = stop_rule.stop_state_record(36.8, crawler_series(22_000.0), WEIGHT_N,
                                         LEG_FORCE_ROWS_KN)
    plain = stop_rule.stroke_limited_stop_row(names, [], None, F_MIN_KN, pressure)
    recorded = stop_rule.stroke_limited_stop_row(names, [], None, F_MIN_KN, pressure, loaded)
    assert not plain["pass"] and not recorded["pass"]
    assert plain["conditions"] == recorded["conditions"]
    assert recorded["stop_with_crawler_loaded"] is True
    assert recorded["min_true_Fcyl_at_stop_kN"] == pytest.approx(12.8)
    assert plain["stop_with_crawler_loaded"] is None and plain["stop_state"] is None
    passing = stop_rule.stroke_limited_stop_row(names, [], 69.3, F_MIN_KN, pressure,
                                                stop_rule.stop_state_record(
                                                    36.8, crawler_series(0.0), WEIGHT_N,
                                                    LEG_FORCE_ROWS_KN))
    assert passing["pass"] and passing["stop_with_crawler_loaded"] is False


def slope_record(events) -> dict:
    t_s = [row[0] for row in LEG_FORCE_ROWS_KN]
    return {"events": events, "case": {"group": "H5", "soil": "rigid", "pad": "B"},
            "run": {"min_true_Fcyl_after_off_kN": None, "max_motor_stroke_mm": 680.2},
            "F_min_kN": F_MIN_KN, "weight_N": WEIGHT_N, "rod_weight_kN": [0.3] * 4,
            "crawler_series": crawler_series(22_000.0),
            "moving_pressure": {"max_moving_bar": 101.2, "saturation_ms": 0},
            "log": {"t_s": t_s, "phase": ["level"] * len(t_s),
                    "fmin_kN": [row[1] for row in LEG_FORCE_ROWS_KN]}}


def test_slope_stroke_row_carries_the_records() -> None:
    row = slope.stroke_row(slope_record(STOP_EVENTS))
    soil_stop = row["soil_stop"]
    assert not soil_stop["pass"]
    assert soil_stop["stop_with_crawler_loaded"] is True
    assert soil_stop["min_true_Fcyl_at_stop_kN"] == pytest.approx(12.8)
    assert "soil_stop" not in slope.stroke_row(slope_record(STOP_EVENTS[:1]))


# --- P37t p37_offset_across_revoke ---------------------------------------------------------------


@pytest.fixture(scope="module")
def params():
    return load_params()


def p37_controller(params):
    cls = fx.make_candidate_class(c2, c2.C2Controller, fx.parse_candidate("P37t"))
    controller = cls.from_params(params, c2.C2Config().with_10hz_d1())
    controller.reset()
    controller._state.phase = c2.C2Phase.LEVEL
    controller._soil_state().is_liftoff_confirmed = True
    return controller


def test_offset_across_revoke_counts_booked_offsets(params) -> None:
    controller = p37_controller(params)
    controller._revoke_loc(20.0, 3_000.0)  # empty ledger: not counted
    assert p37.floor_twist_record(controller)["p37_offset_across_revoke"] == 0
    controller._soil_state().is_liftoff_confirmed = True
    controller.p37_state.offsets_m[3] = 0.0221
    controller._revoke_loc(40.0, 3_000.0)
    record = p37.floor_twist_record(controller)
    assert record["p37_offset_across_revoke"] == 1
    assert record["offset_across_revoke_rows"] == [{"t_s": 40.0,
                                                    "offsets_mm": [0.0, 0.0, 0.0, 22.1]}]
    np.testing.assert_allclose(controller.p37_state.offsets_m, [0, 0, 0, 0.0221])  # kept
    assert "INFO_LOC_REVOKED:3.0" in [e.name for e in controller.events]


def test_offset_across_revoke_absent_without_p37(params) -> None:
    controller = c2.C2Controller.from_params(params, c2.C2Config().with_10hz_d1())
    controller.reset()
    assert p37.floor_twist_record(controller) is None
