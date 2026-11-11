"""Unit tests of the path 1 harness judge and the G-S tool (synthetic lines only)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import las_p5r4k1_gs as gs  # noqa: E402
import las_p5r4k1_judge as pj  # noqa: E402

KEY = "D1|H-S-0|J1|T|flat|K1|VB|e0"


def make_line(arm: str, sha: str = "a" * 64, *, started: float | None = 20.0,
              decisions=None, events=None, bundle: str = "Z-C", key: str = KEY,
              stroke: float = 0.5, force: float = 12000.0, ready: float = 60.0) -> dict:
    """A minimal finished harness line with every field the judge reads."""
    candidate = pj.ARM_CANDIDATE[arm]
    beta, n_min, n_r = pj.CANDIDATE_VALUES[candidate]
    settings = {"light_leg_fraction_of_F_min": beta, "min_active_periods": n_min,
                "end_ramp_periods": n_r}
    return {
        "job": {"setting": "VB", "eps": 0.0, "d1": {}},
        "commands_sha256": sha, "final_phase": "ready",
        "event_names": events if events is not None else {},
        "controller_tag": "final_C4G2_P3_LAS_K1", "las_candidate": candidate,
        "d1": {"verdict": "pass", "items": {"P3-1_x": True, "P3-5_y": True}, "fail_items": [],
               "t_ready_s": ready, "stroke_max_m": stroke, "F_judged_min_N": force},
        "values": {"events": {"t_loc_first_s": 30.0, "t_loc_last_s": 30.0}},
        "las": {"candidate": candidate, "start_t_s": started, "end_t_s": None,
                "params": {"beta": beta, "n_min": n_min, "n_r": n_r},
                "ramp": {"periods_applied": 0, "end_t_s": None}},
        "rev": {"key": key, "candidate": candidate, "settings": settings,
                "settings_match": True, "label": candidate},
        "k1": {"enabled": True, "setting": True, "decisions": decisions or [],
               "r4_applied": False, "would_block_any": False, "loc_calls": []},
        "effective": {"flat_soil_margin_order_gate": True, "touch_creep_latch_enable": False},
        "anchor": {"soil_meta": {"t_P_s": 29.0, "bias_corner_raw_m": [0, 0, 0, 0],
                                 "bias_corner_m": [0, 0, 0, 0], "loc_anchor_bias_mm": None,
                                 "loc_anchor_applied": False}, "loc_calls": []},
        "p5k": {"bundle": bundle, "arm": arm, "las_candidate": candidate,
                "is_liftoff_slow_tag": True, "touch_creep_latch_enabled": False,
                "override": {"applications": 1 if arm == pj.ARM_CAND else 0}},
    }


def decision(applied: bool, d_p: int = 30) -> dict:
    return {"t_loc_s": 40.0, "t_P_s": 40.0, "t_S_s": 40.0 - d_p * 0.1, "n_P": 400,
            "n_S": 400 - d_p, "dP": d_p, "r4_due_without_gate": True,
            "would_block": d_p <= 0, "applied": applied}


# ------------------------------------------------------------------------------- 16.6 order
@pytest.mark.parametrize(("statuses", "expected"), [
    ([pj.STATUS_FAIL, pj.STATUS_PASS], pj.STATUS_FAIL),
    ([pj.STATUS_UNDECIDABLE, pj.STATUS_PASS], pj.STATUS_UNDECIDABLE),
    ([pj.STATUS_FAIL, pj.STATUS_UNDECIDABLE], pj.STATUS_UNDECIDABLE),
    ([pj.STATUS_FAIL, pj.STATUS_STOP, pj.STATUS_UNDECIDABLE], pj.STATUS_STOP),
    ([pj.STATUS_INCOMPLETE, pj.STATUS_FAIL], pj.STATUS_UNDECIDABLE),
])
def test_priority_stop_undecidable_fail_pass(statuses, expected):
    assert pj.worst_status(statuses) == expected


def _completeness(missing=()):
    return {arm: {"expected": 1, "finished": 1, "error_lines": 0, "errors_left": [],
                  "missing": list(missing), "duplicates": [], "out_of_list": [], "reruns": []}
            for arm in (pj.ARM_REF, pj.ARM_CAND)}


def test_bundle_status_fail_under_undecidable_is_undecidable():
    result = {"criteria": {"C-S": pj.criterion(False, ["k"]), "C-2": pj.criterion(None)}}
    status, reasons = pj.bundle_status("Z-C", result, _completeness(), {"ok": True,
                                                                       "problems": {}}, [])
    assert status == pj.STATUS_UNDECIDABLE
    assert any(text.startswith("C-S") for text in reasons)


def test_bundle_status_missing_line_is_undecidable_even_with_a_failure():
    result = {"criteria": {"C-S": pj.criterion(False, ["k"])}}
    status, _ = pj.bundle_status("Z-C", result, _completeness(missing=["x"]),
                                 {"ok": True, "problems": {}}, [])
    assert status == pj.STATUS_UNDECIDABLE


# ------------------------------------------------------------------------------- 3 PAIR_DIVERGE
def test_pair_diverge_when_cand_not_started_and_hash_differs():
    pair = pj.pair_record(KEY, make_line(pj.ARM_CAND, "b" * 64, started=None),
                          make_line(pj.ARM_REF), None)
    assert pair["PAIR_DIVERGE"] is True and pair["PAIR_CMD_DIFF"] is False
    status, _ = pj.bundle_status("Z-C", {"PAIR_DIVERGE": [KEY], "criteria": {}},
                                 _completeness(), {"ok": True, "problems": {}}, [])
    assert status == pj.STATUS_STOP


def test_started_cand_with_other_hash_is_only_recorded():
    pair = pj.pair_record(KEY, make_line(pj.ARM_CAND, "b" * 64), make_line(pj.ARM_REF), None)
    assert pair["PAIR_DIVERGE"] is False and pair["PAIR_CMD_DIFF"] is True


def test_not_started_equal_hash_is_neither():
    pair = pj.pair_record(KEY, make_line(pj.ARM_CAND, started=None), make_line(pj.ARM_REF),
                          None)
    assert not pair["PAIR_DIVERGE"] and not pair["PAIR_CMD_DIFF"]


# ------------------------------------------------------------------------------- CK-1
def test_ck1_r4_lost():
    record = pj.ck1_record(make_line(pj.ARM_CAND, decisions=[decision(False, 0)]),
                           make_line(pj.ARM_REF, decisions=[decision(True)]))
    assert record["R4_LOST"] is True and record["R4_GAINED"] is False


def test_ck1_r4_gained_is_a_flag():
    record = pj.ck1_record(make_line(pj.ARM_CAND, decisions=[decision(True, 5)]),
                           make_line(pj.ARM_REF, decisions=[]))
    assert record["R4_GAINED"] is True and record["R4_LOST"] is False
    assert record["thin_margin"] is True


def test_ck1_missing_decisions_is_undecidable():
    cand = make_line(pj.ARM_CAND)
    del cand["k1"]["decisions"]
    with pytest.raises(pj.MissingField):
        pj.ck1_record(cand, make_line(pj.ARM_REF))


# ------------------------------------------------------------------------------- C-2 / P3 / C-S
def test_missing_d1_items_opens_only_the_criteria_that_read_it():
    cand = make_line(pj.ARM_CAND)
    del cand["d1"]["items"]
    pair = pj.pair_record(KEY, cand, make_line(pj.ARM_REF), None)
    assert set(pair["undecided"]) == {"C-2", "P3"}
    criteria = pj._pair_criteria("Z-C", {KEY: pair}, False,
                                 pj.Bases(lists={"Z-C": [KEY], "Z-S": []}))
    assert criteria["C-2"]["ok"] is None and criteria["P3"]["ok"] is None
    assert criteria["C-S"]["ok"] is True and criteria["CK-1"]["ok"] is True


def test_missing_stroke_key_opens_only_c_s():
    cand = make_line(pj.ARM_CAND)
    del cand["d1"]["stroke_max_m"]
    pair = pj.pair_record(KEY, cand, make_line(pj.ARM_REF), None)
    assert set(pair["undecided"]) == {"C-S"}


@pytest.mark.parametrize(("ref", "cand", "scope", "violation"), [
    (None, 12000.0, pj.RANGE_OUT_REF_NONE, False),
    (None, None, pj.RANGE_OUT_REF_NONE, False),
    (10000.0, None, pj.RANGE_OUT, False),
    (12000.0, None, pj.RANGE_IN, True),
    (12000.0, 10000.0, pj.RANGE_IN, True),
    (12000.0, 11000.0, pj.RANGE_IN, False),
])
def test_rv2_2_c_f_none_rules(ref, cand, scope, violation):
    assert pj.cf_state(ref, cand) == (scope, violation)


@pytest.mark.parametrize(("ref", "cand", "scope", "violation"), [
    (None, 0.5, pj.RANGE_OUT_REF_NONE, False),
    (None, None, pj.RANGE_OUT_REF_NONE, False),
    (0.5, None, pj.RANGE_IN, True),
    (0.5, 0.5015, pj.RANGE_IN, True),
    (0.5, 0.501, pj.RANGE_IN, False),
])
def test_rv2_2_c_s_none_rules(ref, cand, scope, violation):
    assert pj.cs_state(ref, cand) == (scope, violation)


def test_ref_none_stroke_is_listed_not_failed():
    ref = make_line(pj.ARM_REF)
    ref["d1"]["stroke_max_m"] = None
    pairs = {KEY: pj.pair_record(KEY, make_line(pj.ARM_CAND), ref, None)}
    criteria = pj._pair_criteria("Z-C", pairs, False, pj.Bases(lists={"Z-C": [KEY], "Z-S": []}))
    assert criteria["C-S"]["ok"] is True and criteria["C-S"]["ref_none"] == [KEY]


def _clock(starts, resets):
    return {"loss_s": 5.0, "clock_starts_s": starts,
            "resets": [{"t_s": t, "names": []} for t in resets]}


def test_rv2_11_restart_must_be_in_a_later_period_than_the_end():
    ref = make_line(pj.ARM_REF, ready=60.0)
    rx = {**ref, "done_clock": {"loss_s": 0.0}}
    cand = make_line(pj.ARM_CAND, "b" * 64, ready=63.0)
    cand["las"]["ramp"]["end_t_s"] = 30.0
    cand["done_clock"] = _clock([25.0, 35.0], [30.04])
    assert pj.exception_record(cand, ref, rx)["is_exception"] is False
    cand["done_clock"] = _clock([25.0, 35.0], [30.2])
    assert pj.exception_record(cand, ref, rx)["is_exception"] is True
    cand["las"]["ramp"]["end_t_s"] = None
    cand["las"]["end_t_s"] = None
    assert pj.exception_record(cand, ref, rx)["is_exception"] is False


def test_rv2_6_bt_x_must_match_every_bundle_of_the_key():
    assert pj._hash_matches({"commands_sha256": "a"}, ["a", "a"]) is True
    assert pj._hash_matches({"commands_sha256": "a"}, ["a", "b"]) is False


def test_rv2_14_exact_job_key_names():
    line = make_line(pj.ARM_REF)
    line["job"]["k1_scale_note"] = 1
    assert pj.gate_problems(line) == []
    line["job"]["k1_candidate"] = "K1on"
    assert any("RV2-14" in text for text in pj.gate_problems(line))


def test_rv2_8_errors_total_and_left():
    error = {"error": "y", "rev": {"key": "other"},
             "p5k": {"bundle": "Z-C", "arm": pj.ARM_REF, "attempt": 1}}
    lines = [make_line(pj.ARM_REF), error,
             {**error, "p5k": {**error["p5k"], "attempt": 2}}]
    parts, _ = pj.split_lines(lines)
    ctx = pj.Context(pj.Bases(lists={"Z-C": [KEY, "other"]}), pj.References(), parts, [])
    completeness = pj.arm_completeness("Z-C", pj.ARM_REF, ctx, [])
    assert completeness["errors_total"] == 2 and completeness["errors_left"] == ["other"]


def test_criteria_list_violations_and_stay_undecidable_with_an_open_pair():
    cand = make_line(pj.ARM_CAND, "b" * 64, stroke=0.503)
    cand["d1"]["items"]["P3-5_y"] = False
    pairs = {KEY: pj.pair_record(KEY, cand, make_line(pj.ARM_REF), None)}
    bases = pj.Bases(lists={"Z-C": [KEY], "Z-S": []})
    closed = pj._pair_criteria("Z-C", pairs, [], bases)
    assert closed["C-S"]["ok"] is False and closed["P3"]["ok"] is False
    opened = pj._pair_criteria("Z-C", pairs, ["other: missing x"], bases)
    assert opened["C-S"]["ok"] is None and opened["C-S"]["count"] == 1


def test_exact_event_names_skip_event_is_not_a_margin_event():
    line = make_line(pj.ARM_REF, events={"INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order": 1})
    assert pj.event_count(line, pj.FLAT_SOIL_MARGIN_EVENT) == 0
    assert pj.event_count(line, pj.SKIP_EVENT) == 1


# ------------------------------------------------------------------------------- R-1 / R-2
def test_ready_population_empty_set_rules():
    equal = {KEY: {"changed": False, "dt_s": 0.0}}
    assert pj.ready_population(equal)["R-1"] is True
    changed_without_values = {KEY: {"changed": True, "dt_s": None}}
    assert pj.ready_population(changed_without_values)["R-1"] is None


# ------------------------------------------------------------------------------- rev1 anchor
def test_anchor_paths_by_event_name():
    assert pj.anchor_path_of(1, 0) == pj.PATH_CORNER_BIAS
    assert pj.anchor_path_of(0, 2) == pj.PATH_ANCHOR
    assert pj.anchor_path_of(1, 1) == pj.PATH_BOTH
    assert pj.anchor_path_of(0, 0) == pj.PATH_NONE


def test_anchor_sample_shift_flag_true_false_none():
    ref = make_line(pj.ARM_REF, events={"INFO_CLEARANCE_BIAS:1,2": 1,
                                        "crawler_liftoff_confirmed": 1})
    cand = make_line(pj.ARM_CAND, events={"crawler_liftoff_confirmed": 1})
    cand["anchor"]["soil_meta"]["t_P_s"] = 29.1
    assert pj.anchor_record(cand, ref)[pj.FLAG_ANCHOR_SAMPLE_SHIFT] is True
    same = make_line(pj.ARM_CAND, events={"crawler_liftoff_confirmed": 1})
    assert pj.anchor_record(same, ref)[pj.FLAG_ANCHOR_SAMPLE_SHIFT] is False
    plain_ref = make_line(pj.ARM_REF, events={"crawler_liftoff_confirmed": 1})
    assert pj.anchor_record(cand, plain_ref)[pj.FLAG_ANCHOR_SAMPLE_SHIFT] is False
    for line in (ref, cand):
        del line["anchor"]
    record = pj.anchor_record(cand, ref)
    assert record[pj.FLAG_ANCHOR_SAMPLE_SHIFT] is None
    assert record["ANCHOR_RECORD_MISSING"]


def test_anchor_effect_lists_only_violating_pairs():
    pairs = {"a": {"is_case": False, "C-S_violation": True, "P3": [],
                   "anchor": {pj.FLAG_ANCHOR_SAMPLE_SHIFT: True}},
             "b": {"is_case": False, "C-S_violation": False, "P3": ["x"],
                   "anchor": {pj.FLAG_ANCHOR_SAMPLE_SHIFT: None}},
             "c": {"is_case": False, "C-S_violation": False, "P3": [],
                   "anchor": {pj.FLAG_ANCHOR_SAMPLE_SHIFT: True}}}
    effect = pj.anchor_effect(pairs)
    assert effect == {"anchor_effect_possible": ["a"], "anchor_effect_unknown": ["b"]}


# ------------------------------------------------------------------------------- K checks
def test_k_checks_pass_on_a_clean_line_and_catch_a_k1_token():
    line = make_line(pj.ARM_CAND)
    assert pj.tag_problems(line) == [] and pj.gate_problems(line) == []
    assert pj.las_problems(line) == []
    line["rev"]["label"] = "P5r4-K1on"
    assert pj.gate_problems(line)


def test_gate_read_from_the_run_controller_record():
    line = make_line(pj.ARM_REF)
    line["effective"]["flat_soil_margin_order_gate"] = False
    assert any("effective" in text for text in pj.gate_problems(line))


# ------------------------------------------------------------------------------- G-S
def test_gs_stage_and_check_report_only_names():
    assert gs.stage_of(KEY, None, {"setting": "VB", "eps": 0.0}) == "H-S-0|VB|e0"
    assert gs.stage_of("x#P5r4-LQ-c1-j0p25", "P5r4-LQ-c1-j0p25",
                       {"setting": "V0", "eps": 0.002}) == "LQ|V0|e+"
    row = {"bundle": "Z-C", "arm": pj.ARM_CAND, "unit": KEY, "stage": "s"}
    line = make_line(pj.ARM_CAND)
    line["p5k"]["gs"] = True
    result = gs.check_row(line, row)
    assert "done_clock.loss_s" in result["missing_fields"]
    assert set(result) >= {"missing_fields", "K-3", "K-4", "K-5", "ok"}
    assert result["ok"] is False


def test_chrono_gs_rows_come_from_rows_gs_true(tmp_path):
    module = tmp_path / "las_p5r4_k1_chrono_rows.py"
    module.write_text(
        "ROWS = ()\n"
        "def rows(gs=False):\n"
        "    ids = ['A1','A2','A3','A4','A5','A6','B1','B2','C1','C2','C3','C4']\n"
        "    duration = '10' if gs else '160'\n"
        "    return [{'p5k_id': i, 'case': 'GS_' + i if gs else i, 'las_candidate': 'P0',\n"
        "             'argv': ['py', 'run_S9.py', '--duration', duration]} for i in ids]\n",
        encoding="utf-8")
    rows, source = gs.chrono_rows(10.0, module)
    assert "rows(gs=True)" in source and len(rows) == 12
    assert rows[0]["case"] == "GS_A1" and rows[0]["argv"][-2:] == ["--duration", "10"]
    rows, _ = gs.chrono_rows(5.0, module)
    assert rows[0]["argv"][-2:] == ["--duration", "5"]


# ------------------------------------------------------------------------------- rev3
IN, OUT = 0.5e-9, 2e-9
"""rev3 test offsets: inside the 1e-9 tolerance (equal to the threshold) and outside it."""


def test_rv3_1_comparison_helpers_at_the_threshold():
    assert pj.is_at_least(10.4 - IN, 10.4) and not pj.is_at_least(10.4 - OUT, 10.4)
    assert pj.is_below(10.4 - OUT, 10.4) and not pj.is_below(10.4 - IN, 10.4)
    assert pj.is_at_most(1.0 + IN, 1.0) and not pj.is_at_most(1.0 + OUT, 1.0)
    assert pj.is_above(1.0 + OUT, 1.0) and not pj.is_above(1.0 + IN, 1.0)


@pytest.mark.parametrize(("offset", "violation"), [(IN, False), (OUT, True)])
def test_rv3_t5_c_s_increase_at_1_mm(offset, violation):
    assert pj.cs_state(0.5, 0.501 + offset)[1] is violation


@pytest.mark.parametrize(("offset", "scope", "violation"), [
    (-IN, pj.RANGE_IN, False), (-OUT, pj.RANGE_OUT, False)])
def test_rv3_t4_c_f_scope_and_cand_at_the_line(offset, scope, violation):
    line = pj.C_FLOOR_N + offset
    assert pj.cf_state(line, line) == (scope, violation)
    assert pj.cf_state(pj.C_FLOOR_N, pj.C_FLOOR_N - OUT) == (pj.RANGE_IN, True)


def _grid_line(f_rl: float, f_judged: float) -> dict:
    return {"diag": {"summary": {"F_RL_kN": f_rl, "F_judged_min_kN": f_judged}}}


def test_rv3_t1_t2_floors_with_tolerance():
    lines = {("VB", "1", 0): _grid_line(10.4 - IN, 12.0), ("VB", "1", 1): _grid_line(12.0,
                                                                                    10.4 - OUT)}
    failures, _ = pj.force_failures(pj.PART_RG, lines, pj.GRID_FORCE_FLOOR_KN)
    assert [f["point"] for f in failures] == [["VB", "1", 1]]
    g2p, _ = pj.force_failures(pj.PART_RG, {("V0", "1", 0): _grid_line(
        pj.G2P_FLOOR_KN - IN, pj.G2P_FLOOR_KN - IN)}, pj.G2P_FLOOR_KN)
    assert g2p == []


def test_rv3_t15_band_counts_each_value():
    lines = {("VB", "1", 0): _grid_line(10.41, 10.4 - IN),
             ("VB", "1", 1): _grid_line(pj.BAND_TOP_KN - IN, 10.4 - OUT)}
    _, between = pj.force_failures(pj.PART_RG, lines, pj.GRID_FORCE_FLOOR_KN)
    assert len(between) == 2 and all("('VB', '1', 0)" in text for text in between)


def test_rv3_t7_claim_needs_more_than_1_s_plus_tolerance():
    ref = make_line(pj.ARM_REF, ready=60.0)
    for ready, expected in ((61.0 + IN, False), (61.0 + OUT, True)):
        pair = pj.pair_record(KEY, make_line(pj.ARM_CAND, "b" * 64, ready=ready), ref, None)
        assert ("exception" in pair) is expected


def _periods_line(times):
    return {"diag": {"periods": [{"t_s": t, "cmd_mm_s": [1.0]} for t in times]}}


def test_rv3_w1_k_a2_window_in_whole_periods():
    rows = pj._commands_before(_periods_line([12.199999999999999, 12.299999999999999, 12.3]),
                               12.3)
    assert [t for t, _ in rows] == [12.199999999999999]


def test_rv3_t19_k_a4_float_window_end_with_tolerance():
    table = [[30.0, 1], [30.1 - IN, 2], [30.1 - OUT, 3], [30.05, 4]]
    rows = pj.ka4_window_rows(table, 30.0, 30.1, 30.0)
    assert [row[1] for row in rows] == [1, 3, 4]


def test_rv3_w3_restart_window_in_whole_periods():
    ref = make_line(pj.ARM_REF, ready=60.0)
    rx = {**ref, "done_clock": {"loss_s": 0.0}}
    cand = make_line(pj.ARM_CAND, "b" * 64, ready=63.0)
    cand["las"]["ramp"]["end_t_s"] = 30.0
    cand["done_clock"] = _clock([25.000000000000004, 35.0], [24.999999999999996])
    assert pj.exception_record(cand, ref, rx)["is_exception"] is False
    cand["done_clock"] = _clock([25.0, 35.0], [24.9])
    assert pj.exception_record(cand, ref, rx)["is_exception"] is True


def test_rv3_5_rev3_is_checked_but_not_recorded_on_lines():
    assert pj.RULES_REV3_NAME in pj.judge_rules()
    assert pj.RULES_REV3_NAME not in pj.sealed_rules()
    assert pj.judge_rules()[pj.RULES_REV3_NAME] == (
        "31ba01dff9defb4b7274b27b9df1a427c460fa9ccc5efd84f5a3145e0d3ef8f6")


def test_audit13_d1_ready_field_is_required_in_g_s():
    assert "values.times.t_first_ready_s" in gs.D1_FIELDS


def test_with_duration_replaces_only_duration():
    assert gs.with_duration(["--case", "x", "--duration", "160"], 10.0) == [
        "--case", "x", "--duration", "10"]
