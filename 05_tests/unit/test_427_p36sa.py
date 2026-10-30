"""Wrapper token P36sa of ``s9_slope_fix_candidates.py`` (control spec 427.12.2 (나), user
decision 2026-10-30): the P-S8-36 SGS stop armed at every LOC of a soil-response run.

The P36s token itself is unchanged (``test_427_p36s.py``); here: the token and its
alternative, the latch at a LOC without the L1gs sign, the clearing after a revocation, the
stop, the unchanged P36s sign, and the combinations with P37t / R4c / P38z.
"""

from __future__ import annotations

import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "04_scripts" / "03_control" / "s9", ROOT / "04_scripts" / "03_control" / "s8"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import s9_slope_fix_candidates as fx  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

LEVEL_RAD = (math.radians(0.5), 0.0)
GUARDED_RR = np.array([False, False, False, True])


@pytest.fixture(scope="module")
def params():
    return load_params()


def controller_for(params, name: str, *, soil_enabled: bool = True):
    cls = fx.make_candidate_class(c2, c2.C2Controller, fx.parse_candidate(name))
    config = c2.C2Config().with_10hz_d1()
    if not soil_enabled:
        config = replace(config, soil=replace(config.soil, enable=False))
    controller = cls.from_params(params, config)
    controller.reset()
    controller._state.phase = c2.C2Phase.LEVEL
    return controller


def confirm_plain_loc(controller, t_s: float) -> None:
    """A LOC without either L1gs reason: no soil mode, c_min(t_P) 2 mm, level settle."""
    soil = controller._soil_state()
    soil.is_liftoff_confirmed = True
    soil.soil_mode_start_s = None
    soil.clearance_at_plateau_start_m = 0.002
    controller._settle_attitude_rad = lambda: LEVEL_RAD
    controller._p36s_latch_soil_sign(t_s)


def test_token() -> None:
    settings = fx.parse_candidate("P36sa")
    assert settings.p36s and settings.p36s_all_loc
    assert not fx.parse_candidate("P36s").p36s_all_loc
    with pytest.raises(ValueError, match="alternatives"):
        fx.parse_candidate("P36s+P36sa")


def test_every_loc_latches_and_p36s_does_not(params) -> None:
    wide = controller_for(params, "P36sa")
    confirm_plain_loc(wide, 20.0)
    assert wide.fix.p36s_soil_sign == fx.P36S_SIGN_ANY_LOC
    narrow = controller_for(params, "P36s")
    confirm_plain_loc(narrow, 20.0)
    assert narrow.fix.p36s_soil_sign is None  # P36s unchanged


def test_l1gs_reason_is_kept(params) -> None:
    controller = controller_for(params, "P36sa")
    confirm_plain_loc(controller, 20.0)
    controller._soil_state().soil_mode_start_s = 3.0
    controller._p36s_latch_soil_sign(21.0)
    assert controller.fix.p36s_soil_sign == fx.P36S_SIGN_SOIL_MODE


def test_no_sign_without_the_soil_response(params) -> None:
    controller = controller_for(params, "P36sa", soil_enabled=False)
    assert controller._p36s_soil_sign() is None


def test_revocation_clears_and_the_stop_runs(params) -> None:
    controller = controller_for(params, "P36sa")
    confirm_plain_loc(controller, 20.0)
    controller._revoke_loc(21.0, 3000.0)
    controller._p36s_clear_soil_sign_without_loc(21.0)
    assert controller.fix.p36s_soil_sign is None
    assert controller.fix.p36s_sign_history[-1]["cleared"]
    confirm_plain_loc(controller, 25.0)
    controller._record_lift_guard_period(40.0, GUARDED_RR, c2.LiftGuardMode.SHIFT_DOWN)
    out = controller._p36s_stop((0.0, 0.0), np.full(4, 0.002))
    np.testing.assert_array_equal(out, np.zeros(4))
    assert controller.events[-1].name == "FAULT_LIFT_STROKE_LIMIT:soil:RR"
    assert controller.fix.p36s_stop["soil_sign"] == fx.P36S_SIGN_ANY_LOC
    record = {"metrics": {"p36s": fx.p36s_record(controller.fix)}}
    assert fx.has_candidate_acted(record) and fx.acted_parts(record) == ["P36s"]


def test_combinations(params) -> None:
    settings = fx.parse_candidate("P36sa+P37t+R4c30+P38z")
    assert settings.p36s_all_loc and settings.p37 and settings.p38
    assert settings.r4_margin_m == pytest.approx(0.03)
    controller = controller_for(params, "P36sa+P37t+R4c30+P38z")
    assert type(controller).__name__ == "IntegralClampFloorTwistCandidateC2"
