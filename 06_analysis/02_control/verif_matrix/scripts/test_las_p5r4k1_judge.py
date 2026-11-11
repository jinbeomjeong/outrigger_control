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
def test_missing_d1_items_makes_the_pair_undecidable():
    cand = make_line(pj.ARM_CAND)
    del cand["d1"]["items"]
    with pytest.raises(pj.MissingField):
        pj.pair_record(KEY, cand, make_line(pj.ARM_REF), None)


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
    pairs = {"a": {"is_case": False, "stroke_increase_m": 0.002, "P3": [],
                   "anchor": {pj.FLAG_ANCHOR_SAMPLE_SHIFT: True}},
             "b": {"is_case": False, "stroke_increase_m": 0.0, "P3": ["x"],
                   "anchor": {pj.FLAG_ANCHOR_SAMPLE_SHIFT: None}},
             "c": {"is_case": False, "stroke_increase_m": 0.0, "P3": [],
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


def test_with_duration_replaces_only_duration():
    assert gs.with_duration(["--case", "x", "--duration", "160"], 10.0) == [
        "--case", "x", "--duration", "10"]
