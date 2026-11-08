"""Checks of the D-b judge aid (``las_phase_judge.py``, rev1 rules) on synthetic lines.

Run (dynamics-dev): python -I -B -m pytest <this file> -p no:cacheprovider
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import las_phase_judge as lj  # noqa: E402

PHASE_PATTERN = {0: (11.0, 9), 1: (9.75, 5), 2: (10.5, 7), 3: (10.25, 6), 4: (11.125, 10)}
"""j -> (F_RL kN, active periods): a phase saw-tooth whose order follows the active periods
(constant rho: every pair is a strict dominance, 10 predicting pairs, no contradiction).
Multiples of 1/8 kN keep the boundary comparisons exact in binary."""


def make_line(key, centre, j, f_kN, active, rho=0.25, digest=None, excluded=False,
              gate_consistent=True) -> dict:
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
                                 "gate_consistent": gate_consistent}}}


def grid_lines(values, overrides=None) -> list[dict]:
    """``values(key, centre, j) -> (F, active[, rho])`` over the full 30-point grid."""
    lines = []
    for key in lj.KEYS:
        for centre in lj.CENTRES:
            for j in range(5):
                f_kN, active, *rest = values(key, centre, j)
                options = {"rho": rest[0]} if rest else {}
                options.update((overrides or {}).get((key, centre, j), {}))
                lines.append(make_line(key, centre, j, f_kN, active, **options))
    return lines


def _phase(key, centre, j):
    return PHASE_PATTERN[j]


# ------------------------------------------------------------------------------- verdicts
def test_phase_pattern_is_the_phase_verdict():
    result = lj.judge(grid_lines(_phase))
    assert result["exclusion_problems"] == []
    flags = result["flags"]
    assert flags["P1"] and flags["P2"] and flags["P3"] == lj.P3_PASS and flags["P4"]
    assert result["verdict"] == lj.VERDICT_PHASE
    cell = result["measures"][lj.KEY_VB]["1"]
    assert cell["R_c"] == 1.25 and cell["P_c"] == 0.125
    assert cell["p3"] == {"not_started": 0, "predicting_pairs": 10, "contradictions": 0,
                          "status": lj.P3_PASS}


def test_audit_probe_without_predictions_is_undecidable():
    """The audit probe: R_c >= 1 kN but equal active and rho, so no pair predicts anything
    (the old judge passed P3 on the empty set and said "phase")."""
    result = lj.judge(grid_lines(lambda key, centre, j: (PHASE_PATTERN[j][0], 7)))
    cell = result["measures"][lj.KEY_VB]["1"]
    assert cell["p3_evaluated"] and cell["p3"]["predicting_pairs"] == 0
    assert result["flags"]["P3"] == lj.P3_UNDETERMINED
    assert result["verdict"] == lj.VERDICT_UNDECIDABLE


def test_cell_with_only_crossed_pairs_is_undetermined():
    crossed = {0: (11.0, 5, 0.20), 1: (9.8, 6, 0.21), 2: (10.5, 7, 0.22), 3: (10.2, 8, 0.23),
               4: (11.1, 9, 0.24)}  # more active always comes with a larger rho
    result = lj.judge(grid_lines(lambda key, centre, j: crossed[j]))
    p3 = result["measures"][lj.KEY_V0]["0.94"]["p3"]
    assert p3["predicting_pairs"] == 0 and p3["status"] == lj.P3_UNDETERMINED
    assert result["verdict"] == lj.VERDICT_UNDECIDABLE


def test_two_lines_without_a_start_make_p3_undetermined():
    overrides = {(lj.KEY_VB, "1", 1): {"rho": None}, (lj.KEY_VB, "1", 2): {"rho": None}}
    result = lj.judge(grid_lines(_phase, overrides))
    p3 = result["measures"][lj.KEY_VB]["1"]["p3"]
    assert p3["not_started"] == 2 and p3["status"] == lj.P3_UNDETERMINED
    assert result["verdict"] == lj.VERDICT_UNDECIDABLE


def test_contradictions_need_more_than_the_margin():
    within = {**PHASE_PATTERN, 1: (10.4, 5)}  # 0.15 kN above j 3 (predicted higher): no count
    p3 = lj.judge(grid_lines(lambda key, centre, j: within[j]))["measures"][lj.KEY_VB]["1"]["p3"]
    assert p3["contradictions"] == 0
    swapped = {**PHASE_PATTERN, 1: (11.5, 5), 3: (11.4, 6)}  # fewer active, F well above
    result = lj.judge(grid_lines(lambda key, centre, j: swapped[j]))
    assert result["measures"][lj.KEY_VB]["1"]["p3"]["contradictions"] > 1
    assert result["flags"]["P3"] == lj.P3_FAIL and result["verdict"] != lj.VERDICT_PHASE


def _with_means(means: dict[str, float]):
    """The phase pattern shifted per centre: R_c 1.25 kN, M_c = means[centre]."""
    base = sum(PHASE_PATTERN[j][0] for j in lj.PHASE_STEPS) / len(lj.PHASE_STEPS)

    def values(key, centre, j):
        f_kN, active = PHASE_PATTERN[j]
        return f_kN - base + means[centre], active

    return values


def test_phase_and_mixed_are_exclusive_at_the_boundary():
    at_edge = lj.judge(grid_lines(_with_means({"1": 11.25, "0.94": 10.625, "nom": 10.0})))
    keys = at_edge["keys"][lj.KEY_VB]
    assert keys["M_change"] == keys["max_R_c"] == 1.25  # change == max R_c
    assert at_edge["flags"]["phase"] and not at_edge["flags"]["mixed"]
    assert at_edge["verdict"] == lj.VERDICT_PHASE
    beyond = lj.judge(grid_lines(_with_means({"1": 11.375, "0.94": 10.625, "nom": 10.0})))
    assert beyond["flags"]["mixed"] and not beyond["flags"]["phase"]
    assert beyond["verdict"] == lj.VERDICT_MIXED


def test_speed_pattern_is_the_speed_verdict():
    means = {"1": 12.0, "0.94": 11.0, "nom": 10.0}
    result = lj.judge(grid_lines(lambda key, centre, j: (means[centre] + 0.05 * (j % 2), 7)))
    assert result["flags"]["P3"] == lj.P3_NOT_EVALUATED and result["flags"]["speed"]
    assert result["verdict"] == lj.VERDICT_SPEED


def test_speed_condition_on_one_key_only_is_not_speed():
    def values(key, centre, j):
        if key == lj.KEY_VB:
            return {"1": 12.0, "0.94": 11.0, "nom": 10.0}[centre] + 0.05 * (j % 2), 7
        return 11.0 + 0.05 * (j % 2), 7  # V0 flat: no change

    result = lj.judge(grid_lines(values))
    assert result["keys"][lj.KEY_VB]["speed_ok"] and not result["keys"][lj.KEY_V0]["speed_ok"]
    assert not result["flags"]["speed"] and result["verdict"] == lj.VERDICT_UNDECIDABLE


def test_speed_needs_the_same_direction_on_both_keys():
    def values(key, centre, j):
        means = {"1": 12.0, "0.94": 11.0, "nom": 10.0}
        if key == lj.KEY_V0:
            means = {"1": 10.0, "0.94": 11.0, "nom": 12.0}
        return means[centre], 7

    result = lj.judge(grid_lines(values))
    assert all(result["keys"][key]["speed_ok"] for key in lj.KEYS)
    assert not result["flags"]["speed"]


# ------------------------------------------------------------------------------- exclusion
def test_anchor_mismatch_is_undecidable_tool():
    overrides = {(lj.KEY_V0, "nom", 0): {"digest": "f" * 64}}
    result = lj.judge(grid_lines(_phase, overrides))
    assert not result["anchors_pass"] and result["verdict"] == lj.VERDICT_UNDECIDABLE_TOOL


def test_level_budget_or_gate_inconsistency_is_undecidable_tool():
    for override in ({"excluded": True}, {"gate_consistent": False}):
        result = lj.judge(grid_lines(_phase, {(lj.KEY_VB, "0.94", 3): override}))
        assert result["exclusion_problems"]
        assert result["verdict"] == lj.VERDICT_UNDECIDABLE_TOOL


def test_error_line_or_fewer_than_30_lines_is_undecidable_tool():
    lines = grid_lines(_phase)
    partial = lj.judge(lines[:-1])
    assert partial["verdict"] == lj.VERDICT_UNDECIDABLE_TOOL
    assert any("29 of 30" in problem for problem in partial["exclusion_problems"])
    with_error = lj.judge([*lines, {"error": "boom", "diag": {"key": lj.KEY_VB}}])
    assert with_error["verdict"] == lj.VERDICT_UNDECIDABLE_TOOL


# ------------------------------------------------------------------------------- pieces
def test_predicts_lower_is_dominance():
    a = {"active": 5, "rho": 0.28}
    assert lj.predicts_lower(a, {"active": 9, "rho": 0.20})
    assert lj.predicts_lower(a, {"active": 5, "rho": 0.20})  # equal active, larger rho
    assert lj.predicts_lower(a, {"active": 9, "rho": 0.28})  # fewer active, equal rho
    assert not lj.predicts_lower({"active": 9, "rho": 0.20}, a)
    assert not lj.predicts_lower({"active": 5, "rho": 0.20}, {"active": 9, "rho": 0.28})
    assert not lj.predicts_lower({"active": 9, "rho": 0.28}, {"active": 5, "rho": 0.20})
    assert not lj.predicts_lower(a, dict(a))


def test_report_markdown_lists_anchors_and_p3_counts():
    result = lj.judge(grid_lines(_phase))
    text = lj.report_markdown(result, Path("diag_Db.jsonl"))
    assert "A-1" in text and "A-2" in text and "**phase**" in text
    assert "predicting pairs" in text and "contradictions" in text
