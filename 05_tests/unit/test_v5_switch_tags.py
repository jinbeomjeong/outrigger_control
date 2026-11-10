"""Controller tags of the LAS-b and K1 switches (``las_k1_rules_adopt.md`` 9.2).

``_LAS`` (LAS-b) comes first, ``_K1`` (the R4c30 order gate) after it. The suffix helpers must
read a ``_LAS_K1`` tag as a LAS-b tag and must not append ``_LAS`` to it a second time (the two
silent failures of 9.2).
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from outrigger_sim.control.c2 import C2Config
from outrigger_sim.hydraulics.v5_options import (
    EXTEND_START_LAS_K1_CONTROLLER_TAG,
    EXTEND_START_TAGS,
    LAS_K1_CONTROLLER_TAG,
    ORDER_GATE_TAG_SUFFIX,
    HydraulicOptions,
    controller_tag,
    is_liftoff_slow_tag,
    is_order_gate_on,
    is_order_gate_tag,
    with_liftoff_slow_tag,
    with_order_gate_tag,
    with_switch_tags,
)

P3_OPTIONS = HydraulicOptions(extend_start_tracked=True)


def _with_gate(config: C2Config, is_on: bool) -> C2Config:
    margin = replace(config.slope_clearance_margin, flat_soil_margin_order_gate=is_on)
    return replace(config, slope_clearance_margin=margin)


def test_tag_constants() -> None:
    assert ORDER_GATE_TAG_SUFFIX == "_K1"
    assert LAS_K1_CONTROLLER_TAG == "final_C4G2_LAS_K1"
    assert EXTEND_START_LAS_K1_CONTROLLER_TAG == "final_C4G2_P3_LAS_K1"
    assert EXTEND_START_TAGS == ("final_C4G2_P3", "final_C4G2_P3_LAS", "final_C4G2_P3_LAS_K1")


@pytest.mark.parametrize(
    ("tag", "is_las", "is_k1"),
    [
        (None, False, False),
        ("final_C4G2", False, False),
        ("final_C4G2_LAS", True, False),
        ("final_C4G2_P3_LAS_K1", True, True),
        ("ABL_LAS_K1", True, True),
        ("final_C4G2_K1", False, True),
        ("IND", False, False),
    ],
)
def test_suffix_readers(tag, is_las, is_k1) -> None:
    assert is_liftoff_slow_tag(tag) is is_las
    assert is_order_gate_tag(tag) is is_k1


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        (None, "final_C4G2_LAS"),
        ("ABL", "ABL_LAS"),
        ("final_C4G2_LAS", "final_C4G2_LAS"),
        ("final_C4G2_P3_LAS_K1", "final_C4G2_P3_LAS_K1"),  # no second _LAS
        ("final_C4G2_K1", "final_C4G2_LAS_K1"),  # _K1 stays last
    ],
)
def test_with_liftoff_slow_tag(tag, expected) -> None:
    assert with_liftoff_slow_tag(tag) == expected


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        (None, "final_C4G2_K1"),
        ("ABL_LAS", "ABL_LAS_K1"),
        ("final_C4G2_P3_LAS_K1", "final_C4G2_P3_LAS_K1"),
    ],
)
def test_with_order_gate_tag(tag, expected) -> None:
    assert with_order_gate_tag(tag) == expected


def test_controller_tag_follows_the_switches_of_the_config() -> None:
    preset = C2Config().with_10hz_d1()
    assert is_order_gate_on(preset) and not is_order_gate_on(C2Config()) and not is_order_gate_on(None)
    assert controller_tag(None, preset) == "final_C4G2_LAS_K1"
    assert controller_tag(P3_OPTIONS, preset) == "final_C4G2_P3_LAS_K1"
    pre_k1 = _with_gate(preset, False)
    assert controller_tag(None, pre_k1) == "final_C4G2_LAS"
    assert controller_tag(P3_OPTIONS, pre_k1) == "final_C4G2_P3_LAS"
    pre_las = C2Config().with_10hz_d1(liftoff_approach_slow=False, flat_soil_margin_order_gate=False)
    assert controller_tag(None, pre_las) is None  # the runner's final_C4G2
    assert controller_tag(P3_OPTIONS, pre_las) == "final_C4G2_P3"
    assert controller_tag(P3_OPTIONS) == "final_C4G2_P3"  # without a config: the tag before LAS-b


def test_with_switch_tags_is_idempotent() -> None:
    preset = C2Config().with_10hz_d1()
    once = with_switch_tags("ABL", preset)
    assert once == "ABL_LAS_K1"
    assert with_switch_tags(once, preset) == once
    assert with_switch_tags("IND", object()) == "IND"  # a config without the blocks
