"""Unit tests of the P5r4 + K1 run tool (no simulation: stand-in controllers and configs)."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import las_p5r4k1_targeted as tool  # noqa: E402


@dataclass(frozen=True)
class Las:
    enable: bool = True
    light_leg_fraction_of_F_min: float = 3.5
    min_active_periods: int = 0
    end_ramp_periods: int = 0


@dataclass(frozen=True)
class Margin:
    flat_soil_margin_order_gate: bool = True


@dataclass(frozen=True)
class Config:
    liftoff_approach_slow: Las = field(default_factory=Las)
    slope_clearance_margin: Margin = field(default_factory=Margin)


def counts() -> dict[str, int]:
    return {"applications": 0, "kept_target": 0, "las_off": 0}


def test_override_applies_once_to_b0_and_keeps_a_p5r4_config():
    preset = Las()
    target = tool.p5r4_settings(preset)
    assert (target.light_leg_fraction_of_F_min, target.end_ramp_periods) == (4.5, 4)
    seen = counts()
    first = tool.p5r4_config(Config(), preset, target, seen)
    again = tool.p5r4_config(first, preset, target, seen)
    assert first.liftoff_approach_slow == target and again is first
    assert seen == {"applications": 1, "kept_target": 1, "las_off": 0}


def test_override_refuses_another_las_and_keeps_las_off():
    preset = Las()
    target = tool.p5r4_settings(preset)
    with pytest.raises(RuntimeError):
        tool.p5r4_config(Config(Las(light_leg_fraction_of_F_min=5.0)), preset, target,
                         counts())
    seen = counts()
    off = Config(Las(enable=False))
    assert tool.p5r4_config(off, preset, target, seen) is off and seen["las_off"] == 1


def test_preset_problems_gate_ramp_and_touch_creep():
    assert tool.preset_problems(Config()) == []
    assert tool.preset_problems(Config(slope_clearance_margin=Margin(False)))
    assert tool.preset_problems(Config(Las(end_ramp_periods=4)))
    creep = SimpleNamespace(**vars(Config()), touch_creep_latch=SimpleNamespace(enable=True))
    assert any("touch_creep" in text for text in tool.preset_problems(creep))


class StandIn:
    """A controller class with the two methods the hooks wrap."""

    def __init__(self, geometry, config=None):
        self.config = config
        self.soil = SimpleNamespace(liftoff_s=None, plateau_start_s=None, corner_bias_raw_m=None,
                                    corner_bias_m=[0.0] * 4, is_loc_anchor_applied=False,
                                    clearance_at_plateau_start_m=None)

    def _soil_state(self):
        return self.soil

    def _confirm_liftoff(self, t_s, tail, mean_load_N):
        self.soil.liftoff_s, self.soil.plateau_start_s = t_s, t_s - 1.0
        self.soil.corner_bias_raw_m = [0.01, 0.0, 0.0, 0.0]
        self.soil.corner_bias_m = [0.01, 0.0, 0.0, 0.0]

    def meta(self):
        return {"soil": {"t_P_s": self.soil.plateau_start_s, "bias_corner_m": [0.01, 0, 0, 0]},
                "slope_clearance_margin": {"order_gate": {"enabled": True, "decisions": []},
                                           "flat_soil_margin_applied": []}}


@pytest.fixture
def stand_in():
    cls = type("StandInCopy", (StandIn,), {})
    yield cls
    tool.uninstall()


def test_correction_witness_records_every_loc_read_only(stand_in):
    tool.install_correction_witness(stand_in)
    controller = stand_in(None, Config())
    controller._confirm_liftoff(40.0, [], 1.0)
    controller._confirm_liftoff(50.0, [], 1.0)
    calls = tool.anchor_record(controller)["loc_calls"]
    assert [call["t_loc_s"] for call in calls] == [40.0, 50.0]
    assert calls[0]["t_P_s"] == 39.0 and calls[0]["bias_corner_m"][0] == 0.01
    with pytest.raises(RuntimeError):
        tool.install_correction_witness(stand_in)


def test_override_wrapper_on_a_class(stand_in):
    tool.install_p5r4_override(Las(), stand_in)
    controller = stand_in(None, Config())
    assert controller.config.liftoff_approach_slow.end_ramp_periods == 4
    assert tool.OVERRIDE_COUNTS["applications"] == 1


def test_gate_is_read_from_the_run_controller():
    controller = StandIn(None, replace(Config(), slope_clearance_margin=Margin(True)))
    record = tool.k1_record(controller)
    assert record["setting"] is True and record["enabled"] is True
