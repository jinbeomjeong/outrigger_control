"""V0 (auger), plan S5: fixed_part + auger_moving_set_at_cad_pose moved by the level travel
along body z = superstructure.auger_levels.<level> (mass, CoM, inertia about the CoM)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.params import load_params
from outrigger_sim.verify import s1
from outrigger_sim.verify.s5 import (
    LEVELS,
    MassProps,
    _flatten,
    auger_travel_check,
    auger_v0_checks,
    auger_v0_residuals,
    compose_auger_level,
    composition_rounding_bound,
    printed_half_unit,
    summarize_check_ids,
)

ROOT = Path(__file__).resolve().parents[2]
DYN_V0_CHECK = ROOT / "06_analysis" / "00_dynamics" / "s5_v0_check.json"
"""dynamics-expert exact-rational V0 (auger) check (dynamics_model.md 5.9, rev. 22)."""


def _auger_levels_json(params) -> dict:
    path = ROOT / params.get("meta.sources.auger_levels")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def yaml_parts():
    p = load_params()
    return (p, MassProps.from_mapping(p.get("superstructure.fixed_part")),
            MassProps.from_mapping(p.get("superstructure.auger_moving_set_at_cad_pose")))


def test_composition_of_exact_inputs() -> None:
    """Two point-like boxes: analytic mass, CoM and parallel-axis inertia."""
    a = MassProps(2.0, np.array([0.0, 0.0, 0.0]), np.diag([1.0, 2.0, 3.0]))
    b = MassProps(1.0, np.array([0.0, 0.0, 1.0]), np.diag([0.5, 0.5, 0.5]))
    c = compose_auger_level(a, b, 2.0)  # b ends at z = 3
    assert c.mass_kg == 3.0
    assert np.allclose(c.com_m, [0.0, 0.0, 1.0], atol=1e-15)
    # parallel axis: a at distance 1, b at distance 2 along z
    expect = np.diag([1.0, 2.0, 3.0]) + np.diag([2.0, 2.0, 0.0]) * 1.0 \
        + np.diag([0.5, 0.5, 0.5]) + np.diag([4.0, 4.0, 0.0]) * 1.0
    assert np.allclose(c.inertia_kg_m2, expect, atol=1e-14)
    r = auger_v0_residuals(c, c)
    assert all(v == 0.0 for v in r.values())


def test_printed_half_unit() -> None:
    assert printed_half_unit(38555.6638) == pytest.approx(5e-5)
    assert printed_half_unit(-0.00147659077) == pytest.approx(5e-12)
    assert printed_half_unit(2.99598) == pytest.approx(5e-6)
    assert printed_half_unit(0.0) == 0.0


def test_travel_range_holds_the_levels(yaml_parts) -> None:
    p, _, _ = yaml_parts
    lo, hi = p.get("superstructure.auger_moving_set_at_cad_pose.travel_range_m")
    travels = [p.get(f"superstructure.auger_levels.{lv}.auger_travel_m") for lv in LEVELS]
    assert travels[0] == hi and travels[2] == lo and lo < travels[1] < hi
    # middle = midpoint of the range, to the printed 1e-5 m (the midpoint is -1.302815)
    assert travels[1] == pytest.approx(0.5 * (lo + hi), abs=1e-5)


def _level_inputs(yaml_parts, level):
    p, fixed, moving = yaml_parts
    block = p.get(f"superstructure.auger_levels.{level}")
    return fixed, moving, float(block["auger_travel_m"]), MassProps.from_mapping(block)


def _judged_v0_row(fixed, moving, travel_m, reference):
    composed = compose_auger_level(fixed, moving, travel_m)
    bound = composition_rounding_bound(fixed, moving, travel_m, reference)
    return auger_v0_checks("level", composed, reference, bound)[0]


def _with_inertia_offset(props: MassProps, row: int, col: int, offset: float) -> MassProps:
    inertia = props.inertia_kg_m2.copy()
    inertia[row, col] += offset
    if row != col:
        inertia[col, row] += offset
    return MassProps(props.mass_kg, props.com_m, inertia)


@pytest.mark.parametrize("level", LEVELS)
def test_v0_auger_within_printed_digits(yaml_parts, level) -> None:
    fixed, moving, travel_m, ref = _level_inputs(yaml_parts, level)
    comp = compose_auger_level(fixed, moving, travel_m)
    bound = composition_rounding_bound(fixed, moving, travel_m, ref)
    res = auger_v0_residuals(comp, ref)
    # mass meets the plan 1e-9 directly; CoM / inertia are limited by 9 printed digits
    assert res["mass_rel"] <= 1e-9
    assert res["com_max_abs_m"] <= 1e-8
    assert res["inertia_rel_to_max"] <= 1e-8
    judged = auger_v0_checks(level, comp, ref, bound)[0]
    assert judged.id == "V0(auger)" and judged.passed, judged.note
    # the combined level body is a valid rigid body
    eig = np.linalg.eigvalsh(comp.inertia_kg_m2)
    assert np.all(eig > 0) and eig[0] + eig[1] >= eig[2]
    assert np.allclose(comp.inertia_kg_m2, comp.inertia_kg_m2.T)


def _dyn_v0_check(level: str) -> dict:
    return json.loads(DYN_V0_CHECK.read_text(encoding="utf-8"))["A_v0_auger"][level]


def _is_dyn_check_of_this_yaml(dyn: dict, composed: MassProps, reference: MassProps) -> bool:
    """The dynamics exact check holds the residual composed - YAML table of the YAML it was
    run on; a different residual (beyond 1 % of its bound) means a newer YAML table."""
    ours = _flatten(composed) - _flatten(reference)
    theirs = np.array(list(dyn["residual"].values()))
    bound = np.array(list(dyn["bound_no_travel"].values()))
    return bool(np.all(np.abs(ours - theirs) <= 0.01 * bound))


@pytest.mark.parametrize("level", LEVELS)
def test_v0_auger_matches_dynamics_exact_check(yaml_parts, level) -> None:
    """Bound without the travel term and the residual / bound ratio = dyn's exact rational
    (expected values from s5_v0_check.json, which must be of the current YAML table)."""
    fixed, moving, travel_m, ref = _level_inputs(yaml_parts, level)
    dyn = _dyn_v0_check(level)
    composed = compose_auger_level(fixed, moving, travel_m)
    if not _is_dyn_check_of_this_yaml(dyn, composed, ref):
        pytest.skip(
            "s5_v0_check.json predates the YAML auger table; re-run "
            "04_scripts/01_dynamics/run_s5_v0_check.py (dynamics-expert)"
        )
    bound = composition_rounding_bound(fixed, moving, travel_m, ref)
    dyn_bound = np.array(list(dyn["bound_no_travel"].values()))
    assert np.allclose(_flatten(bound), dyn_bound, rtol=1e-6, atol=0.0)
    judged = _judged_v0_row(fixed, moving, travel_m, ref)
    ratio = np.abs(np.asarray(judged.deviation)) / np.asarray(judged.tol)
    assert ratio.max() < 1.0
    assert ratio.max() == pytest.approx(dyn["max_residual_over_bound_no_travel"], rel=1e-4)


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize(("name", "row", "col", "offset"), [
    ("Ixx +0.01 kg m^2", 0, 0, 0.01),
    ("Iyz +1e-3 kg m^2", 1, 2, 1.0e-3),
])
def test_v0_auger_catches_level_inertia_error(yaml_parts, level, name, row, col,
                                              offset) -> None:
    fixed, moving, travel_m, ref = _level_inputs(yaml_parts, level)
    wrong_ref = _with_inertia_offset(ref, row, col, offset)
    assert not _judged_v0_row(fixed, moving, travel_m, wrong_ref).passed, name


@pytest.mark.parametrize("level", LEVELS)
def test_v0_auger_catches_travel_error(yaml_parts, level) -> None:
    """Travel +0.01 mm from another source: both the composition row and the travel row fail."""
    p, _, _ = yaml_parts
    fixed, moving, travel_m, ref = _level_inputs(yaml_parts, level)
    wrong_travel_m = travel_m + 1.0e-5
    assert not _judged_v0_row(fixed, moving, wrong_travel_m, ref).passed
    travel_mm = _auger_levels_json(p)["levels"][level]["travel_mm"]
    assert auger_travel_check(level, travel_m, travel_mm).passed
    assert not auger_travel_check(level, wrong_travel_m, travel_mm).passed


def test_v0_auger_plan_metrics_are_info_rows(yaml_parts) -> None:
    fixed, moving, travel_m, ref = _level_inputs(yaml_parts, "middle")
    comp = compose_auger_level(fixed, moving, travel_m)
    rows = auger_v0_checks("middle", comp, ref,
                           composition_rounding_bound(fixed, moving, travel_m, ref))
    assert [r.id for r in rows] == ["V0(auger)", "info", "info", "info"]
    assert all("rev. 22" in r.note for r in rows[1:])
    # middle CoM 4.1e-9 m > 1e-9: recorded as failed, not part of the verdict
    assert not rows[2].passed
    assert summarize_check_ids([r.as_dict() for r in rows]) == {"V0(auger)": True}


@pytest.mark.parametrize("level", LEVELS)
def test_yaml_travel_equals_auger_levels_json(yaml_parts, level) -> None:
    p, _, _ = yaml_parts
    travel_m = float(p.get(f"superstructure.auger_levels.{level}.auger_travel_m"))
    travel_mm = _auger_levels_json(p)["levels"][level]["travel_mm"]
    row = auger_travel_check(level, travel_m, travel_mm)
    assert row.id == "V0(auger) travel" and row.passed


def test_s1_v0_rule_unchanged() -> None:
    """S1 V0 stays the element-wise copy check at 1e-9 (rev. 22 changes S5 only)."""
    assert s1.V0_REL_TOL == 1.0e-9
    assert s1.V0_POS_ABS_TOL_M == 1.0e-9
    assert s1.V1_LEG_FRACTION_OF_QUARTER_WEIGHT == 1.0e-2
