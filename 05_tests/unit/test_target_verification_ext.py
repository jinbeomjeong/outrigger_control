"""D8x extended verification mode ``verification_ext`` (rev1: roll 5.7, nose down 3.7, nose up 3.6).

Rules ``06_analysis/02_control/d8x/d8x_rules_rev1.md`` 1.1, 1.3 and 9.2 item 1 (replacing
``d8x_rules.md`` 9.2 item 1): the floor equals the crawler attitude (identity settle map); the
``for_level`` cases take their expectation from the inverse map. The user nose-up override is
refused in both verification modes.
"""

from __future__ import annotations

import math

import pytest

from outrigger_sim.control.c2 import TargetSettings
from outrigger_sim.control.target import (
    VERIFICATION_EXT_HALF_SPANS_DEG,
    VERIFICATION_USAGE_TOLERANCE,
    AttitudeTarget,
    CrawlerSettleMap,
    SlopeLimitMode,
    TargetCheck,
    TargetCode,
    TargetLimits,
    check_target,
    floor_usage,
)

RPX_DEG = (2.8632, 1.8413)
RPX_REJECT_SCALE = 1.0126
RP05_DEG = (2.7699, 1.7813)
"""The bundle-C floor outside the 5.5 / 3.5 deg diamond (A1 rejection function check)."""
LEVELS = ("top", "middle", "bottom")

REV1_TABLE = [
    ("rpX", RPX_DEG, TargetCode.ACCEPTED),
    ("rpX x 1.0126", (RPX_DEG[0] * RPX_REJECT_SCALE, RPX_DEG[1] * RPX_REJECT_SCALE),
     TargetCode.REJ_SLOPE_D8),
    ("fup3.6", (0.0, -3.6), TargetCode.ACCEPTED),
    ("nose up 3.7 (asymmetry)", (0.0, -3.7), TargetCode.REJ_SLOPE_D8),
    ("fdown3.7", (0.0, 3.7), TargetCode.ACCEPTED),
    ("rpX+-", (2.8242, -1.8162), TargetCode.ACCEPTED),
]
"""Rev1 9.2 item 1 test table: (name, floor (roll, pitch) deg, expected code)."""


def _radians(pair_deg: tuple[float, float]) -> tuple[float, float]:
    return math.radians(pair_deg[0]), math.radians(pair_deg[1])


def _identity_check(mode: SlopeLimitMode, floor_deg: tuple[float, float]) -> TargetCheck:
    """A level target with the floor = the crawler attitude (identity settle map)."""
    return check_target(AttitudeTarget(), _radians(floor_deg), TargetLimits.for_mode(mode))


def _rev1_usage(roll_deg: float, pitch_deg: float) -> float:
    """Rev1 1.1: |phi| / 5.7 + |theta| / Theta(theta), Theta 3.7 nose down, 3.6 nose up."""
    pitch_span = 3.7 if pitch_deg >= 0.0 else 3.6
    return abs(roll_deg) / 5.7 + abs(pitch_deg) / pitch_span


def test_extended_limits_are_the_rev1_fields() -> None:
    limits = TargetLimits.for_mode(SlopeLimitMode.VERIFICATION_EXT)
    assert limits.relative_roll_span_rad == math.radians(5.7)
    assert limits.relative_pitch_span_rad == math.radians(3.7)
    assert limits.relative_pitch_span_nose_up_rad == math.radians(3.6)
    assert limits.usage_tolerance == VERIFICATION_USAGE_TOLERANCE == 0.01
    defaults = TargetLimits()
    for name in ("max_roll_rad", "max_pitch_rad", "absolute_roll_span_rad",
                 "absolute_pitch_span_rad"):
        assert getattr(limits, name) == getattr(defaults, name)
    assert SlopeLimitMode("verification_ext") is SlopeLimitMode.VERIFICATION_EXT
    assert VERIFICATION_EXT_HALF_SPANS_DEG == {"roll": 5.7, "pitch_nose_down": 3.7,
                                               "pitch_nose_up": 3.6}


@pytest.mark.parametrize(("name", "floor_deg", "expected"), REV1_TABLE,
                         ids=[row[0] for row in REV1_TABLE])
def test_rev1_table_with_the_identity_map(name, floor_deg, expected) -> None:
    check = _identity_check(SlopeLimitMode.VERIFICATION_EXT, floor_deg)
    assert check.code is expected, name
    assert check.floor_usage == pytest.approx(_rev1_usage(*floor_deg), abs=1e-12)


def test_rev1_usage_values_of_the_table() -> None:
    assert _rev1_usage(RPX_DEG[0] * RPX_REJECT_SCALE, RPX_DEG[1] * RPX_REJECT_SCALE) == (
        pytest.approx(1.01256, abs=5e-6))
    assert _rev1_usage(0.0, -3.7) == pytest.approx(1.02778, abs=5e-6)


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize(("name", "floor_deg", "expected"), REV1_TABLE,
                         ids=[row[0] for row in REV1_TABLE])
def test_rev1_table_with_the_level_map(level, name, floor_deg, expected) -> None:
    """The crawler attitude of the floor by the level map; the map brings the floor back."""
    settle_map = CrawlerSettleMap.for_level(level)
    crawler_rad = settle_map.crawler_from_floor(_radians(floor_deg))
    floor_back = settle_map.floor_from_crawler(crawler_rad)
    limits = TargetLimits.for_mode(SlopeLimitMode.VERIFICATION_EXT)
    is_inside = floor_usage(floor_back, limits) <= 1.0 + limits.usage_tolerance
    check = check_target(AttitudeTarget(), crawler_rad, limits, settle_map=settle_map)
    assert check.code is (TargetCode.ACCEPTED if is_inside else TargetCode.REJ_SLOPE_D8)
    assert check.code is expected, name


@pytest.mark.parametrize("level", LEVELS)
def test_verification_mode_still_rejects_rp05(level: str) -> None:
    assert _identity_check(SlopeLimitMode.VERIFICATION, RP05_DEG).code is TargetCode.REJ_SLOPE_D8
    settle_map = CrawlerSettleMap.for_level(level)
    crawler_rad = settle_map.crawler_from_floor(_radians(RP05_DEG))
    limits = TargetLimits.for_mode(SlopeLimitMode.VERIFICATION)
    check = check_target(AttitudeTarget(), crawler_rad, limits, settle_map=settle_map)
    assert check.code is TargetCode.REJ_SLOPE_D8


@pytest.mark.parametrize(("roll_deg", "pitch_deg"),
                         [(0.0, 3.7), (0.0, -3.6), (5.7, 0.0), (-5.7, 0.0)])
def test_vertices_on_the_extended_boundary(roll_deg, pitch_deg) -> None:
    limits = TargetLimits.for_mode(SlopeLimitMode.VERIFICATION_EXT)
    assert floor_usage(_radians((roll_deg, pitch_deg)), limits) == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize("mode", [SlopeLimitMode.VERIFICATION, SlopeLimitMode.VERIFICATION_EXT])
def test_settings_refuse_the_nose_up_override_in_both_verification_modes(mode) -> None:
    with pytest.raises(ValueError, match="relative_pitch_span_nose_up_rad"):
        TargetSettings(slope_limit_mode=mode, relative_pitch_span_nose_up_rad=math.radians(3.1))


def test_target_settings_use_the_mode_limits() -> None:
    settings = TargetSettings(
        slope_limit_mode="verification_ext",
        crawler_settle_map=CrawlerSettleMap.for_level("top"),
    )
    assert settings.slope_limit_mode is SlopeLimitMode.VERIFICATION_EXT
    assert settings.limits == TargetLimits.for_mode(SlopeLimitMode.VERIFICATION_EXT)
    assert settings.limits.relative_pitch_span_nose_up_rad == math.radians(3.6)


def test_existing_modes_are_unchanged() -> None:
    """Operating (4.4 / 3.2, 1e-9) and verification (5.5 / 3.5 symmetric, 0.01) as before."""
    assert TargetLimits.for_mode(SlopeLimitMode.OPERATING) == TargetLimits()
    assert TargetLimits.for_mode(SlopeLimitMode.VERIFICATION) == TargetLimits(
        relative_roll_span_rad=math.radians(5.5),
        relative_pitch_span_rad=math.radians(3.5),
        usage_tolerance=0.01,
    )
    assert [mode.value for mode in SlopeLimitMode] == [
        "operating", "verification", "verification_ext"
    ]
