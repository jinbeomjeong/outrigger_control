"""Controller tags of the LAS-b and K1 switches (``las_k1_rules_adopt.md`` 9.2).

``_LAS`` (LAS-b) comes first, ``_K1`` (the R4c30 order gate) after it. The suffix helpers must
read a ``_LAS_K1`` tag as a LAS-b tag and must not append ``_LAS`` to it a second time (the two
silent failures of 9.2). The ③ judgement reads the base tag, so all eight combinations of
LAS-b x gate x ③ are fixed here (post-switch audit W-1, user decision (a) 2026-11-10).
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from outrigger_sim.control.c2 import C2Config
from outrigger_sim.hydraulics.v5_options import (
    EXTEND_START_LAS_K1_CONTROLLER_TAG,
    EXTEND_START_TAGS,
    LAS_K1_CONTROLLER_TAG,
    ORDER_GATE_TAG_SUFFIX,
    HydraulicOptions,
    controller_tag,
    is_extend_start_tag,
    is_liftoff_slow_tag,
    is_order_gate_on,
    is_order_gate_tag,
    switch_base_tag,
    with_liftoff_slow_tag,
    with_order_gate_tag,
    with_switch_tags,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

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


# ------------------------------------------------------- LAS-b x K1 gate x ③ (audit W-1)
SWITCH_COMBINATIONS = [
    # (LAS-b on, K1 gate on, ③ on, recorded tag; None = the runner's final_C4G2)
    (False, False, False, None),
    (False, False, True, "final_C4G2_P3"),
    (True, False, False, "final_C4G2_LAS"),
    (True, False, True, "final_C4G2_P3_LAS"),
    (False, True, False, "final_C4G2_K1"),
    (False, True, True, "final_C4G2_P3_K1"),
    (True, True, False, "final_C4G2_LAS_K1"),
    (True, True, True, "final_C4G2_P3_LAS_K1"),
]
"""Every switch combination: ``final_C4G2_P3_K1`` (``run_S9 level --las-off --k1-order-gate on``
with ③) is outside ``EXTEND_START_TAGS`` and was dropped from J-P3 before the fix."""
V_MAX_M_S = 0.020924
VALVE_TAU_S = 0.1


def _combination_config(is_las_on: bool, is_gate_on: bool, is_p3_on: bool):
    """The run-time controller of one combination and the v5 options of its run."""
    from outrigger_sim.hydraulics.v5_options import apply_controller_options

    config = C2Config().with_10hz_d1(liftoff_approach_slow=is_las_on,
                                     flat_soil_margin_order_gate=is_gate_on)
    if not is_p3_on:
        return config, None
    return apply_controller_options(config, P3_OPTIONS, V_MAX_M_S, VALVE_TAU_S), P3_OPTIONS


@pytest.fixture(scope="module")
def run_s9():
    pytest.importorskip("pychrono")
    folder = str(PROJECT_ROOT / "04_scripts" / "02_chrono")
    sys.path.insert(0, folder)
    try:
        import run_S9
    finally:
        sys.path.remove(folder)
    return run_S9


@pytest.mark.parametrize(("is_las_on", "is_gate_on", "is_p3_on", "expected_tag"),
                         SWITCH_COMBINATIONS)
def test_switch_combination_tags_and_readers(is_las_on, is_gate_on, is_p3_on,
                                             expected_tag) -> None:
    config, options = _combination_config(is_las_on, is_gate_on, is_p3_on)
    tag = controller_tag(options, config)
    assert tag == expected_tag
    assert is_liftoff_slow_tag(tag) is is_las_on
    assert is_order_gate_tag(tag) is is_gate_on
    assert is_extend_start_tag(tag) is is_p3_on
    abl_tag = with_switch_tags("ABL", config)  # the ABL family never has ③
    assert is_liftoff_slow_tag(abl_tag) is is_las_on
    assert is_order_gate_tag(abl_tag) is is_gate_on
    assert not is_extend_start_tag(abl_tag)


@pytest.mark.parametrize(("is_las_on", "is_gate_on", "is_p3_on", "expected_tag"),
                         SWITCH_COMBINATIONS)
def test_switch_combination_j_p3_consumers(is_las_on, is_gate_on, is_p3_on,
                                           expected_tag) -> None:
    """The ③ consumers of the audit (``j_p3_inputs.is_p3_expected``, ``v5_rerun.j_p3_status``;
    ``chrono_t45_replay`` and ``u3_reuse`` call the same ``is_extend_start_tag``)."""
    import j_p3_inputs
    import v5_rerun

    assert j_p3_inputs.is_p3_expected(expected_tag, None) is is_p3_on
    status = v5_rerun.j_p3_status(expected_tag, None, False, False)
    assert (status != v5_rerun.J_P3_NOT_APPLICABLE) is is_p3_on


@pytest.mark.parametrize(("is_las_on", "is_gate_on", "is_p3_on", "expected_tag"),
                         SWITCH_COMBINATIONS)
def test_switch_combination_passes_its_run_s9_expectation(run_s9, is_las_on, is_gate_on,
                                                          is_p3_on, expected_tag) -> None:
    """``--expect-controller <tag>`` accepts the controller of its own combination and refuses
    every combination with another LAS-b or gate value (a tag without ``_P3`` does not check
    that ③ is off, so the ③ pair of the same switches is not compared)."""
    config, _ = _combination_config(is_las_on, is_gate_on, is_p3_on)
    name = expected_tag or run_s9.FINAL_CONTROLLER
    assert name in run_s9.CONTROLLER_EXPECTATIONS
    assert run_s9.controller_expectation(config, name)["ok"]
    parsed = run_s9.build_parser().parse_args(["level", "--soil", "J1", "--expect-controller",
                                               name])
    assert parsed.expect_controller == name
    for other in SWITCH_COMBINATIONS:
        if other[:2] == (is_las_on, is_gate_on):
            continue
        other_config, _ = _combination_config(*other[:3])
        assert not run_s9.controller_expectation(other_config, name)["ok"], other


@pytest.mark.parametrize(
    ("tag", "base"),
    [
        ("final_C4G2_P3_LAS_K1", "final_C4G2_P3"),
        ("final_C4G2_P3_K1", "final_C4G2_P3"),
        ("final_C4G2_P3_LAS", "final_C4G2_P3"),
        ("ABL_LAS_K1", "ABL"),
        ("ABL_K1", "ABL"),
        ("final_C4G2_P3_K1_LAS", "final_C4G2_P3_K1"),  # not a generated order: not ③
    ],
)
def test_switch_base_tag(tag, base) -> None:
    assert switch_base_tag(tag) == base
    assert is_extend_start_tag(tag) is (base == "final_C4G2_P3")
    assert not is_extend_start_tag(None)
