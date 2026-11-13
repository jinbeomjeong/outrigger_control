"""Unit tests of the 436.8 path 1 H-6 judge and H-8 re-aggregation (rules rev5 R5-A1, synthetic
inputs only; no stored result is read)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import h6_judge_4368 as h6j  # noqa: E402
import h8_noise_judge_4368 as h8j  # noqa: E402

GATES = ("S-1", "S-2", "S-3", "S-4", "S-5", "S-6")


def _row(**s4):
    rows = {name: {"ok": True, "flags": []} for name in GATES}
    rows["S-4"] = {
        "ok": True,
        "fail_misfire_new": False,
        "miss": False,
        "gate_fail": False,
        "recontact_new": False,
        "flags": [],
        **s4,
    }
    rows["S-6"]["new_fault"] = []
    return {"rows": rows, "pass": all(r["ok"] for r in rows.values())}


def _run(key="L2|s0|g6|1|ref|J1|top|Fs0", level="L2", is_flag=False, **extra):
    return {
        "key": f"cand=current#{key}",
        "level": level,
        "harness": "g6",
        "case_index": 1,
        "inner": "ref|J1|top|Fs0",
        "seed_index": 0,
        "v5_setting": "VB",
        "base": {"late_loc_reapproach": {"is_flag": is_flag}},
        "r79": {"crawler_at_loc_over_W": 0.0, "warn_fault": []},
        **extra,
    }


# ------------------------------------------------------------------------------ line grades
def test_late_loc_only_with_419_8_flag_is_the_13_2_flag():
    row = _row(ok=False, gate_fail=True)
    grade = h8j.grade_line(row, _run(is_flag=True))
    assert grade["grade"] == "flag" and "S4_late_loc" in grade["flags"]
    assert h8j.grade_line(row, _run(is_flag=False))["grade"] == "fail"


def test_strict_recontact_and_unexplained_s4_fail():
    row = _row(ok=False, gate_fail=True, recontact_new=True)
    grade = h8j.grade_line(row, _run(is_flag=True))
    assert grade["grade"] == "fail" and grade["s4_causes"] == ["recontact_strict_fail"]
    unexplained = h8j.grade_line(_row(ok=False), _run())
    assert unexplained["grade"] == "fail" and unexplained["s4_unexplained"]  # rev5 R5-C2


def test_missing_judge_row_or_key_is_not_judgeable():
    assert h8j.grade_line(None, _run())["grade"] == "판정 불가"
    row = _row()
    del row["rows"]["S-4"]["miss"]
    assert h8j.grade_line(row, _run())["grade"] == "판정 불가"


# ------------------------------------------------------------------------------ bundle numbers
def test_cp_two_roots_agree_and_n835_allows_16():
    assert h8j.cp_upper_beta(16, 835) == pytest.approx(h8j.cp_upper_binom(16, 835), abs=1e-12)
    assert h8j.cp_upper_beta(16, 835) <= 0.03 < h8j.cp_upper_beta(17, 835)
    assert h8j.cp_upper_beta(0, 0) is None and h8j.cp_upper_beta(3, 3) == 1.0


def test_level_summary_excludes_s1_front_and_pad_a():
    grades = {
        "a": {"level": "L2", "inner": "g6|G1+S1@FL|top|Fs4", "grade": "fail"},
        "b": {"level": "L2", "inner": "J1|A|0,0", "grade": "fail"},
        "c": {"level": "L2", "inner": "ref|J1|top|Fs0", "grade": "fail", "failed_gates": ["S-5"]},
        "d": {"level": "L2", "inner": "ref|J1|top|Fs0", "grade": "pass"},
    }
    found = h8j.level_summary(grades, "L2")
    assert found["n"] == 2 and found["excluded_s1_front_pad_a"] == 2 and found["failures"] == 1


def test_exclusion_constants_equal_the_runner():
    tree = ast.parse((h8j.R79_FINAL).read_text(encoding="utf-8"))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            values[node.targets[0].id] = node.value
    assert ast.literal_eval(values["S1_FRONT_MARKERS"]) == h8j.S1_FRONT_MARKERS
    pattern_call = values["PAD_A_INNER"]  # re.compile(<pattern>)
    assert ast.literal_eval(pattern_call.args[0]) == h8j.PAD_A_INNER.pattern


def test_l1_gate_counts_and_settings_mismatch_without_judge_key():
    reference = _run(key="L1|s0|g6|1|ref|J1|top|Fs0", level="L1")
    reference["r79"]["crawler_at_loc_over_W"] = 0.02  # false LOC
    orphan = _run(key="L2|s0|g6|2|ref|J1|top|Fs0")
    orphan["case_index"] = 2
    other_setting = _run(key="L2|s1|g6|1|ref|J1|top|Fs0", v5_setting="V0")
    other_setting["v5_setting"] = "V0"
    results = [reference, orphan, other_setting]
    judge = {"reference": [{"group": "all", "false_loc": 1}], "unmatched": ["x"], "errors": []}
    found = h8j.l1_gate([{"meta": {"n_errors": 0}}], results, judge, "VB")
    assert found["direct"] == {
        "false_loc": 1,
        "unmatched": 1,
        "errors": 0,
        "settings_mismatch": 1,
    }
    assert found["is_violated"] and not found["is_count_mismatch"]
    assert found["comparisons"]["settings_mismatch"] == "대조 대상 없음"  # rev5 R5-C1
    judge["unmatched"] = []
    assert h8j.l1_gate([{"meta": {}}], results, judge, "VB")["is_count_mismatch"]


def test_substitution_by_plain_key_and_hash_record():
    noise = [_run(commands_sha256="a"), _run(key="L3|s0|g6|1|ref|J1|top|Fs0", level="L3")]
    h6 = [{**_run(commands_sha256="a"), "key": "L2|s0|g6|1|ref|J1|top|Fs0", "from_h6": True}]
    merged, record = h8j.substitute_lines(noise, h6)
    assert merged[0].get("from_h6") and record["replaced"] == 1
    assert record["hash_same_top_level"] == 1 and record["hash_record_incomplete"] == 0


def test_seedext_fisher_wording_and_hash_check():
    def grades(failures):
        return {
            f"L2|s{i}|g6|56|ref|J2|top|Fs0": {
                "level": "L2",
                "inner": "ref|J2|top|Fs0",
                "grade": "fail" if i < failures else "pass",
                "failed_gates": ["S-5"] if i < failures else [],
            }
            for i in range(25)
        }

    found = h8j.seedext_summary(grades(16), grades(1))["L2|g6|56|ref|J2|top|Fs0"]
    assert found["wording"] == h8j.WORDING_SUSPECT and found["is_n_expected"]
    same = h8j.seedext_summary(grades(3), grades(2))["L2|g6|56|ref|J2|top|Fs0"]
    assert same["wording"] == h8j.WORDING_SCATTER
    seed = [_run(commands_sha256="a"), {**_run(commands_sha256="b"), "seed_index": 9}]
    check = h8j.seed_hash_check(seed, [_run(commands_sha256="c")])
    assert check["checked"] == 1 and check["different"] == ["L2|s0|g6|1|ref|J1|top|Fs0"]


def test_bundle_status_h10_on_cp_over_3pct():
    level = {
        "is_within_3pct": False,
        "cp95_upper_beta": 0.04,
        "failures": 20,
        "n": 835,
        "not_judgeable": [],
    }
    report = {
        "VB": {"L2": level, "L1_gate": {"is_violated": False, "is_count_mismatch": False}},
        "seed_hash_H15": {"VB": {"different": []}},
        "dg3_substitution": {"without_noise_line": []},
        "seedext": {},
        "judge_runs": {},
    }
    status, findings = h8j.bundle_status(report)
    assert status == "멈춤" and findings[0].startswith("H-10")


# ------------------------------------------------------------------------------------- H-6
def _h6_run(**changes):
    run = _run(
        key="L3|s0|g6|1|ref|J1|top|Fs0",
        level="L3",
        controller_tag="final_C4G2_P3_LAS_K1",
        controller_settings={"two_pressure.extend_start_rule": "tracked_bound"},
        extend_bound_check={"breach_reads": [0, 0, 0, 0]},
        head_only_declared=False,
        hydraulics_record={"m2_clipped_steps_post_lift": [0, 0, 0, 0]},
        lock_window_alignment={"fallback_legs": {"FL": {}}, "n_late_fallback": 0},
    )
    run.update(changes)
    return run


def _h6_line(run, l1_faults=()):
    reference = _run(key="L1|s0|g6|1|ref|J1|top|Fs0", level="L1")
    reference["r79"]["warn_fault"] = list(l1_faults)
    references = {h8j.pair_key(reference): [reference]}
    rows = {h8j.plain_key(run["key"]): _row()}
    return h6j.judge_line(run, references, rows, ())


def test_h6_clean_line_passes():
    line = _h6_line(_h6_run())
    assert not line["stops"] and not line["problems"] and line["new_fault"] == []
    assert h6j.bundle_grade([line])[0] == "통과"


def test_h6_stops_j_p3_j9_and_fallback_n_late():
    assert _h6_line(_h6_run(extend_bound_check={"breach_reads": [0, 1, 0, 0]}))["stops"] == ["H-7"]
    assert _h6_line(_h6_run(extend_bound_check=None))["stops"] == ["setting_defect"]
    clipped = _h6_run(hydraulics_record={"m2_clipped_steps_post_lift": [0, 0, 2, 0]})
    assert _h6_line(clipped)["stops"] == ["H-9"]
    late = _h6_run(lock_window_alignment={"fallback_legs": {"FL": {}}, "n_late_fallback": 1})
    line = _h6_line(late)
    assert line["stops"] == ["H-7"] and h6j.bundle_grade([line])[0] == "멈춤"


def test_h6_new_fault_is_below_and_missing_keys_not_judgeable():
    run = _h6_run()
    run["r79"]["warn_fault"] = ["FAULT_STROKE_END", "WARN_X"]
    line = _h6_line(run)
    assert line["new_fault"] == ["FAULT_STROKE_END"] and h6j.bundle_grade([line])[0] == "미달"
    assert _h6_line(run, l1_faults=["FAULT_STROKE_END"])["new_fault"] == []
    missing = _h6_line(_h6_run(hydraulics_record={}))
    late_none = _h6_line(
        _h6_run(lock_window_alignment={"fallback_legs": {"FL": {}}, "n_late_fallback": None})
    )
    assert missing["problems"] and late_none["problems"]
    # 판정 불가 beats 미달 (original rules 8.1)
    assert h6j.bundle_grade([line, missing])[0] == "판정 불가"


def test_h6_j_p3_reads_the_extend_start_from_the_tag_rev8():
    """Rev8 R8-2: a line whose tag is not ③ has no J-P3; a ③ line without the recorded
    extend_start_rule is 판정 불가 for J-P3."""
    not_p3 = _h6_line(_h6_run(controller_tag="final_C4G2_LAS_K1",
                              extend_bound_check={"breach_reads": [0, 1, 0, 0]}))
    assert not_p3["j_p3"]["case"] == "not_applicable" and not_p3["stops"] == []
    no_rule = _h6_line(_h6_run(controller_settings={}))
    assert no_rule["j_p3"]["case"] == "not_judgeable" and no_rule["stops"] == []
    assert h6j.bundle_grade([no_rule])[0] == "판정 불가"
