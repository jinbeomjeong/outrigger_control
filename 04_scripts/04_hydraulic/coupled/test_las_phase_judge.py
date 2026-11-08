"""Checks of the D-b judge aid (``las_phase_judge.py``) on synthetic lines.

Run (dynamics-dev): python -I -B -m pytest <this file> -p no:cacheprovider
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import las_phase_judge as lj  # noqa: E402

PHASE_PATTERN = {0: (11.0, 9), 1: (9.8, 5), 2: (10.5, 7), 3: (10.2, 6), 4: (11.1, 10)}
"""j -> (F_RL kN, active periods): a phase saw-tooth whose order follows the active periods."""


def make_line(key, centre, j, f_kN, active, rho=0.25, digest=None, excluded=False) -> dict:
    anchor_hash = None
    for anchor in lj.ANCHORS.values():
        if anchor["centre"] == centre and anchor["j"] == j:
            anchor_hash = anchor["hashes"][key]
    return {"commands_sha256": digest or anchor_hash or f"h-{key}-{centre}-{j}",
            "diag": {"key": key,
                     "touch_budget": {"centre": centre, "j": j, "s": 1.0,
                                      "excluded": excluded,
                                      "level_budget_periods": 1 if excluded else 0},
                     "summary": {"F_RL_kN": f_kN, "las_active_periods": active,
                                 "las_start_rho": rho, "las_start_rho_prev": 0.2,
                                 "las_start_period": 8, "las_end_reason": "sum",
                                 "t_touch_end_s": 22.3, "t_lift_s": 23.4,
                                 "gates_false_before_start": ["S7p_rise"],
                                 "gate_consistent": True}}}


def grid_lines(values, overrides=None) -> list[dict]:
    """``values(key, centre, j) -> (F, active)`` over the full 30-point grid."""
    lines = []
    for key in lj.KEYS:
        for centre in lj.CENTRES:
            for j in range(5):
                f_kN, active = values(key, centre, j)
                lines.append(make_line(key, centre, j, f_kN, active,
                                       **(overrides or {}).get((key, centre, j), {})))
    return lines


def test_phase_pattern_is_the_phase_verdict():
    result = lj.judge(grid_lines(lambda key, centre, j: PHASE_PATTERN[j]))
    assert result["anchors_pass"]
    assert result["flags"]["P1"] and result["flags"]["P2"] and result["flags"]["P3"]
    assert result["flags"]["P4"] and result["verdict"] == lj.VERDICT_PHASE
    measures = result["measures"][lj.KEY_VB]["1"]
    assert abs(measures["R_c"] - 1.2) < 1e-9 and abs(measures["P_c"] - 0.1) < 1e-9
    assert measures["exceptions"] == 0 and measures["predicting_pairs"] == 10


def test_speed_pattern_is_the_speed_verdict():
    means = {"1": 12.0, "0.94": 11.0, "nom": 10.0}
    result = lj.judge(grid_lines(lambda key, centre, j: (means[centre] + 0.05 * (j % 2), 7)))
    assert not result["flags"]["P1"] and result["flags"]["speed"]
    assert result["verdict"] == lj.VERDICT_SPEED


def test_order_exceptions_break_p3():
    swapped = {**PHASE_PATTERN, 1: (11.5, 5), 3: (11.4, 6)}  # fewer active, higher F
    result = lj.judge(grid_lines(lambda key, centre, j: swapped[j]))
    assert result["measures"][lj.KEY_VB]["1"]["exceptions"] > lj.P3_MAX_EXCEPTIONS
    assert not result["flags"]["P3"] and result["verdict"] != lj.VERDICT_PHASE


def test_anchor_failure_is_undecidable():
    overrides = {(lj.KEY_V0, "nom", 0): {"digest": "f" * 64}}
    result = lj.judge(grid_lines(lambda key, centre, j: PHASE_PATTERN[j], overrides))
    assert not result["anchors_pass"] and result["verdict"] == lj.VERDICT_UNDECIDABLE


def test_excluded_or_missing_point_is_undecidable():
    overrides = {(lj.KEY_VB, "0.94", 3): {"excluded": True}}
    result = lj.judge(grid_lines(lambda key, centre, j: PHASE_PATTERN[j], overrides))
    assert result["excluded"] and result["verdict"] == lj.VERDICT_UNDECIDABLE
    partial = grid_lines(lambda key, centre, j: PHASE_PATTERN[j])[:-1]
    assert lj.judge(partial)["missing"] == [f"{lj.KEY_V0} cnom j4"]


def test_predicts_lower_reading():
    a = {"active": 5, "rho": 0.28}
    assert lj.predicts_lower(a, {"active": 9, "rho": 0.20}) is True
    assert lj.predicts_lower({"active": 9, "rho": 0.20}, a) is False
    assert lj.predicts_lower({"active": 5, "rho": 0.20}, {"active": 9, "rho": 0.28}) is None
    assert lj.predicts_lower(a, dict(a)) is None


def test_report_markdown_lists_the_anchors():
    result = lj.judge(grid_lines(lambda key, centre, j: PHASE_PATTERN[j]))
    text = lj.report_markdown(result, Path("diag_Db.jsonl"))
    assert "A-1" in text and "A-2" in text and "**phase**" in text
