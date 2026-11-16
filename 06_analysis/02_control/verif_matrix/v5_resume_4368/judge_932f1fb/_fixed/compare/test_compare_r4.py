"""Synthetic-input tests of compare_r4.py: equal, different, empty list, missing column / file."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).with_name("compare_r4.py")
_spec = importlib.util.spec_from_file_location("compare_r4", MODULE_PATH)
compare = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compare)

RK = "06_analysis/03_hydraulic/coupled/v5/resume_k1"
LK = "06_analysis/02_control/v5_rerun/las_k1"
GRID_FILE = f"{RK}/h9_grid/grid_r67_main.json"
H10_FILE = f"{RK}/h10_reuse_rerun.jsonl"
FAMILY_KEYS = ("screen|top|0.0|ready|FL", "screen|top|0.0|ready|FR")
G5_KEYS = sorted(compare.JD2_KEYS)
G6_KEYS = sorted(compare.JD7_KEYS)
EXIT_INPUT_ERROR = 2
ITEM_COUNT = 21
INPUT_FILE_COUNT = 18  # 8 path 1 outputs + 9 path 2 outputs + the baseline
RD8_MARKER = "J-P3 입력 형식(RD-8)"
RD9_COUNT = 10
DG3_SUBSTITUTED = 3
LEG_SECONDS = [0.0, 0.005, 0.0, 0.25]
P3_VALUES = {item: True for item in compare.P3_CHECK_KEYS}


def path1_bundles() -> dict:
    bundles = {}
    for bundle in compare.RD9_BUNDLES:
        entry: dict = {"markers": [], "p3_units_RD9": RD9_COUNT}
        if bundle in compare.RD8_BUNDLES:
            entry["RD-8"] = {
                "lines_with_breach_reads": 5,
                "wrong_form": 0,
                "top_level_mismatch_RD7_3": 0,
                "vb_pass_without_breach_reads": 0,
            }
        if bundle in compare.RD8_JUDGED_BUNDLES:
            entry["J-P3_not_judgeable"] = {"RD-8": 0, "all": 1, "S-2": 0}
            entry["J11_RD10"] = {"not_judgeable": 1, "no_input": 2}
        bundles[bundle] = entry
    bundles["H-4"]["markers"] = [RD8_MARKER]
    bundles["H-8"]["dg3_replaced_excluded"] = {f"{RK}/h8_noise_VB.json": DG3_SUBSTITUTED}
    return bundles


def path2_harness_bundles() -> dict:
    bundles = {}
    for bundle in compare.RD9_BUNDLES:
        r4: dict = {"rd9_p3_on": RD9_COUNT}
        if bundle in compare.RD8_BUNDLES:
            r4["rd8"] = {
                "lines_present": 5,
                "breach_reads_bad_format": 0,
                "breach_reads_mismatch": 0,
                "jp3_pass_without_breach_reads": 0,
                "lines": [],
            }
        bundles[bundle] = {"gates": [], "r4": r4}
    bundles["H-4"]["gates"] = [RD8_MARKER]
    return bundles


def path1_x16_records() -> dict:
    common = {"rc": 0, "last_sample_s": 120.0, "first_ready_s": 50.0}
    c9 = {
        **common,
        "decisions": [{"k": 0}],
        "soil_mode_start_s": None,
        "loc_s": 30.0,
        "controller_commands_sha256": "ab",
        "max_stroke_mm": 600.0,
        "end_rut_gap_mm": 5.0,
        "P3": P3_VALUES,
    }
    c10 = {
        **common,
        "t_D_s": 40.0,
        "F_below_F_min_ms": [s * 1000.0 for s in LEG_SECONDS],
        "F_below_F_min_plus_2kN_ms": [s * 1000.0 for s in LEG_SECONDS],
        "F_min_after_N": [1.0e4] * 4,
        "t_min_after_s": [41.0] * 4,
        "F_min_transient_N": [9.0e3] * 4,
        "G6": {"G6-1": {"P3": "P3-1", "value": "pass"}, "G6-6": {"P3": None, "value": "fail"}},
        "P3-3_within": True,
        "end_phase": "ready",
        "max_stroke_mm": 600.0,
        "patch_leg": "FL",
        "patch_leg_sinkage_end_mm": 12.0,
        "times_note": "free text, not compared",
    }
    c11 = {
        **common,
        "first_loc_s": 30.0,
        "final_loc_s": 31.0,
        "loc_cancels": 1,
        "loc_period_crawler_max_N": 100.0,
        "loc_period_crawler_max_over_W": 0.001,
        "loc_period_ge_0p01W": False,
        "final_loc_differs": True,
        "final_loc_period_crawler_max_N": 90.0,
        "final_loc_period_crawler_max_over_W": 0.0009,
        "final_loc_period_ge_0p01W": False,
    }
    return {
        "rows": {
            "C9on": {"bundle": "C-9", "items": c9, "problems": ["x"]},
            "C10": {"bundle": "C-10", "items": c10},
            "C11": {"bundle": "C-11", "items": c11},
        },
        "bundles": {
            "C-9": {
                "state": "기록 완료",
                "p18_premise": {"holds": True},
                "controller_commands_same": True,
            },
            "C-10": {"state": "기록 완료"},
            "C-11": {"state": "기록 완료"},
        },
        "identity_stops": {},
    }


def path2_c16() -> dict:
    common = {"rc": 0, "last_sample_t_s": 120.0, "first_ready_s": 50.0}
    c9 = {
        **common,
        "decisions": [{"k": 0}],
        "soil_mode_start_t_s": None,
        "loc_t_s": 30.0,
        "controller_commands_sha256": "ab",
        "max_stroke_mm": 600.0,
        "end_rut_gap_mm": 5.0,
        "P3": {key: True for key in compare.P3_CHECK_KEYS.values()},
        "rc_source": "C:/elsewhere/C9on_run.done",
    }
    legs = [
        {
            "t_below_F_min_s": s,
            "t_below_F_min_plus_2kN_s": s,
            "F_min_after_N": 1.0e4,
            "t_min_after_s": 41.0,
            "F_min_transient_N": 9.0e3,
        }
        for s in LEG_SECONDS
    ]
    c10 = {
        **common,
        "force": {"t_departure_s": 40.0, "legs": legs},
        "G6": {"G6-1": True, "G6-6": "미달"},
        "P3-3": True,
        "end_phase": "ready",
        "max_stroke_mm": 600.0,
        "patch_leg": "FL",
        "patch_leg_sinkage_mm": 12.0,
    }
    c11 = {
        **common,
        "loc_first_t_s": 30.0,
        "loc_final_t_s": 31.0,
        "loc_revokes": 1,
        "loc_period_crawler_max_N": 100.0,
        "loc_period_crawler_max_over_W": 0.001,
        "above_0p01W": False,
        "final_loc_period": {
            "t_loc_s": 31.0,
            "crawler_max_N": 90.0,
            "crawler_max_over_W": 0.0009,
            "above_0p01W": False,
        },
    }
    return {
        "rows": {
            "C9on": {"bundle": "C-9", "present": True, "items": c9},
            "C10": {"bundle": "C-10", "present": True, "items": c10},
            "C11": {"bundle": "C-11", "present": True, "items": c11},
        },
        "bundles": {name: {"status": "기록 완료"} for name in compare.C16_BUNDLES},
        "C-9_P-18": {"premise": True, "commands_equal": True},
        "stops": [],
    }


def path2_merge_counts() -> dict:
    bundles = compare.RD9_V5C_BUNDLES
    return {
        "RD-8": {b: {"format": 0, "top_level_mismatch": 0} for b in bundles},
        "RD-9": {b: {"p3_on": RD9_COUNT, "scanned": 20} for b in bundles},
        "RD-10": {b: {"undecidable": 1, "input_missing": 2} for b in bundles},
        "RD-13_sha256": {b: "cc" for b in bundles},
    }


def jp3_row(file_key: str, location_key: str) -> dict:
    return {
        "bundle": "H-10",
        file_key: H10_FILE,
        location_key: "line 7",
        "leg": "FL",
        "key": "R12|bottom|FL|Fs4",
        "setting": "VB",
        "breach_reads": 2,
        "min_gap_bar": -1.25,
        "first_breach_t_s": 12.5,
    }


def s6_row(file_key: str, location_key: str, line: int) -> dict:
    return {
        "bundle": "H-8",
        file_key: f"{RK}/h8_noise_VB.json",
        location_key: f"results[{line}]",
        "k": 0,
        "key": f"key{line}",
        "setting": "VB",
        "family": "균일 연약",
        "t_loc_s": 30.125,
        "n_P": 3,
        "n_S": 1,
        "dP": 2,
    }


def g_rows(file_key: str, location_key: str, keys: list[str], name: str) -> list[dict]:
    return [
        {
            "bundle": "H-3",
            file_key: f"{LK}/u3_{name}_VB.json",
            location_key: f"records[{index}]",
            "key": key,
        }
        for index, key in enumerate(keys)
    ]


def grid_row(file_key: str) -> dict:
    return {
        file_key: GRID_FILE,
        "key": "screen|top|0.0|ready|FL",
        "event": "G4",
        "offset_s": 0.025,
        "vb_false_gates": ["end_att"],
        "v0_false_gates": [],
    }


def family_row(file_key: str, condition_key: str, condition: object) -> dict:
    return {
        file_key: GRID_FILE,
        "key": FAMILY_KEYS[0],
        "event": "FS24",
        "offset_s": 0.05,
        "vb_pass": False,
        "v0_pass": True,
        "vb_false_gates": ["Fmin_after_W"],
        "v0_false_gates": [],
        "vb_pass_without_two": True,
        "v0_pass_without_two": True,
        condition_key: condition,
    }


def path1_documents() -> dict[str, dict]:
    return {
        "r4_lists.json": {
            "lists": {
                "J-P3": [jp3_row("result_file", "location")],
                "J11": [],
                "S-6": [s6_row("result_file", "location", 3)],
            },
            "bundles": path1_bundles(),
        },
        "x16_records.json": path1_x16_records(),
        "item_list.json": {
            "lists": {"H-1": {"file": "items_H-1.json", "sha256": "aa", "items": 9}}
        },
        "u3_judge.json": {
            "R4": {
                "G-5_list_RD7": g_rows("result_file", "location", G5_KEYS, "slope"),
                "G-6_list_RD7": g_rows("result_file", "location", G6_KEYS, "g8"),
            }
        },
        "h11.json": {"G-3": True, "false_pairs_RD7": []},
        "grid_h10.json": {
            "v0_pair_source": {"source": "저장 V0 격자", "sample_jobs": 8, "sample_jobs_same": 8},
            "raw_pass_to_fail": [grid_row("result_file")],
            "N_raw": 1,
            "excluded_pass_to_fail": [grid_row("result_file")],
            "N_F": 1,
            "family_f_rows": [family_row("result_file", "condition", True)],
            "application_condition": True,
            "record": {
                "pass_to_pass": 700,
                "fail_to_pass": 3,
                "fail_to_fail": 64,
                "fault": 0,
                "fault_rows": [],
                "not_judgeable": [],
            },
            "h10_marker": "멈춤 H-10",
            "h10_grid_selected": {"count": "N_F", "value": 1},
        },
        "family_f.json": {
            "k": {f"{setting}|{key}": 2 for setting in ("V0", "VB") for key in FAMILY_KEYS},
            "R-1": {key: True for key in FAMILY_KEYS},
            "R-2": True,
            "R-3": True,
            "R-4": True,
            "R-3_violations": [],
            "R-4_violations": [],
            "result": "통과",
        },
        "jp_reuse.json": {
            "rows_count": 12,
            "stop_markers": [],
            "reuse": True,
            "rows": [
                {
                    "batch": "batch_V5-JP-VB",
                    "case": "c1",
                    "run_id": "b/c1",
                    "events_unreadable": False,
                    "events": 40,
                    "flat_soil_margin_applied": 0,
                    "soil_mode_start": 0,
                    "shadow_lines": 1,
                    "shadow_unreadable": False,
                    "condition1_shadow_silent": True,
                    "condition2_k1_no_effect": True,
                }
            ],
        },
    }


def path2_documents() -> dict[str, dict]:
    return {
        "harness.json": {
            "stop_S6_list": {"rows": [s6_row("result_file", "position", 3)]},
            "bundles": path2_harness_bundles(),
        },
        "p2v5c_merge.json": {
            "RD-7": {
                "J-P3": {"H-6": [], "H-10": [jp3_row("file", "position")]},
                "J11": {"H-6": [], "H-10": []},
            },
            **path2_merge_counts(),
        },
        "p2v5c_noise.json": {
            "R4": {
                "H-8_dg3_substituted": {
                    "keys_in_noise_VB": 135,
                    "p3_on": DG3_SUBSTITUTED,
                    "p3_on_judged_in_H-8": RD9_COUNT - DG3_SUBSTITUTED,
                }
            }
        },
        "c16.json": path2_c16(),
        "rd13_items.json": {"list_sha256": {"H-1": "bb"}},
        "p2v5c_grid.json": {
            "v0_pair": {"source": "stored", "sample": {"jobs": 8, "same": 8}},
            "grid": {
                "a_pass_to_fail_raw": [grid_row("file")],
                "N_raw": 1,
                "c_pass_to_fail_family_F_excluded": [grid_row("file")],
                "N_F": 1,
                "b_family_F_table": [family_row("file", "applicable", True)],
                "family_F_applicable": True,
                "grid_records": {
                    "pass_to_pass": 700,
                    "fail_to_pass": 3,
                    "fail_to_fail": 64,
                    "N_fault": 0,
                    "fault_rows": [],
                    "undecidable_rows": [],
                },
                "supplement6_inputs": {"h10_marker": True},
                "h10_grid_term": {"uses": "N_F", "value": 1},
                "family_F_rule": {
                    "k": {f"{key}|{setting}": 2 for setting in ("V0", "VB") for key in FAMILY_KEYS},
                    "R1": {key: True for key in FAMILY_KEYS},
                    "R2": {"ok": True},
                    "R3": {"ok": True, "violations": []},
                    "R4": {"ok": True, "violations": []},
                    "result": "pass",
                },
            },
        },
        "u3.json": {
            "U-3": {
                "G-5_list": {"rows": g_rows("result_file", "position", G5_KEYS, "slope")},
                "G-6_list": {"rows": g_rows("result_file", "position", G6_KEYS, "g8")},
            }
        },
        "g3.json": {"G-3": True, "G-3_false_list": {"rows": []}},
        "jp.json": {
            "n_rows": 12,
            "stop_markers": [],
            "reuse": True,
            "rows": [
                {
                    "batch": "batch_V5-JP-VB",
                    "case": "c1",
                    "run_id": "b/c1",
                    "events_unreadable": False,
                    "n_events": 40,
                    "n_r4c30": 0,
                    "n_soil_mode_start": 0,
                    "n_shadow_lines": 1,
                    "shadow_unreadable": False,
                    "cond1": True,
                    "cond2": True,
                }
            ],
        },
    }


def baseline_document() -> dict:
    return {
        "jp_base": [
            {"bundle": "H-10", "file": H10_FILE, "location": "line 7", "leg": "FL", "info": {}}
        ],
        "s6_base": [
            {
                "bundle": "H-8",
                "file": f"{RK}/h8_noise_VB.json",
                "location": "results[3]",
                "info": {},
            }
        ],
    }


@pytest.fixture
def documents() -> dict[str, dict]:
    return {"path1": path1_documents(), "path2": path2_documents(), "baseline": baseline_document()}


def write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")


def run_compare(tmp_path: Path, documents: dict, monkeypatch) -> tuple[int, dict]:
    for side in ("path1", "path2"):
        for name, document in documents[side].items():
            write_json(tmp_path / side / name, document)
    baseline = tmp_path / "baseline.json"
    write_json(baseline, documents["baseline"])
    monkeypatch.setattr(
        compare, "BASELINE_SHA256", hashlib.sha256(baseline.read_bytes()).hexdigest()
    )
    out = tmp_path / "report.json"
    code = compare.main(
        [
            "--path1-dir",
            str(tmp_path / "path1"),
            "--path2-dir",
            str(tmp_path / "path2"),
            "--baseline",
            str(baseline),
            "--out",
            str(out),
        ]
    )
    return code, json.loads(out.read_text(encoding="utf-8"))


def statuses(report: dict) -> dict[str, str]:
    return {item["item"]: item["status"] for item in report["items"]}


def test_equal_outputs_give_exit_0(tmp_path, documents, monkeypatch):
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert code == 0, [item for item in report["items"] if item["status"] != "equal"]
    assert set(statuses(report).values()) == {"equal"}
    assert len(report["items"]) == ITEM_COUNT


def test_report_records_input_and_own_sha256(tmp_path, documents, monkeypatch):
    _code, report = run_compare(tmp_path, documents, monkeypatch)
    assert report["tool_sha256"] == hashlib.sha256(MODULE_PATH.read_bytes()).hexdigest()
    assert report["column_map_sha256"] == compare.column_map_record()["sha256"]
    records = {(r["side"], r["name"]): r["sha256"] for r in report["inputs"]}
    assert len(records) == INPUT_FILE_COUNT
    assert all(records.values())


def test_value_difference_gives_exit_1(tmp_path, documents, monkeypatch):
    row = documents["path2"]["p2v5c_merge.json"]["RD-7"]["J-P3"]["H-10"][0]
    row["breach_reads"] = 3
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert code == 1
    item = next(i for i in report["items"] if i["item"].startswith("RD-7 J-P3"))
    assert item["status"] == "differ"
    assert item["detail"]["value_differences"][0]["column"] == "breach_reads"


def test_row_on_one_side_differs_in_list_and_baseline(tmp_path, documents, monkeypatch):
    documents["path1"]["r4_lists.json"]["lists"]["S-6"].append(s6_row("result_file", "location", 9))
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert code == 1
    found = statuses(report)
    assert found["RD-7 S-6 list (RD-7 2)"] == "differ"
    assert found["JD-3 S-6 = s6_base"] == "differ"


def test_numbers_within_tolerance_are_equal(tmp_path, documents, monkeypatch):
    row = documents["path2"]["p2v5c_merge.json"]["RD-7"]["J-P3"]["H-10"][0]
    row["first_breach_t_s"] = 12.5 + 1e-12
    code, _report = run_compare(tmp_path, documents, monkeypatch)
    assert code == 0


def test_bool_never_equals_number():
    assert not compare.values_equal(True, 1)
    assert compare.values_equal(1, 1.0)


def test_three_valued_words_are_one_class(tmp_path, documents, monkeypatch):
    documents["path1"]["grid_h10.json"]["application_condition"] = "판정 불가"
    documents["path2"]["p2v5c_grid.json"]["grid"]["family_F_applicable"] = "undecidable"
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert statuses(report)["S5-3 (b) family F table and application condition"] == "equal"
    assert code == 0


def test_g5_key_set_other_than_block_differs(tmp_path, documents, monkeypatch):
    documents["path1"]["u3_judge.json"]["R4"]["G-5_list_RD7"][0]["key"] = "other|key"
    documents["path2"]["u3.json"]["U-3"]["G-5_list"]["rows"][0]["key"] = "other|key"
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert code == 1
    assert statuses(report)["JD-2 G-5 (5 keys)"] == "differ"


def test_empty_required_list_gives_exit_2(tmp_path, documents, monkeypatch):
    documents["path2"]["harness.json"]["stop_S6_list"]["rows"] = []
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert code == EXIT_INPUT_ERROR
    found = statuses(report)
    assert found["RD-7 S-6 list (RD-7 2)"] == "missing"
    assert found["JD-3 S-6 = s6_base"] == "missing"


def test_empty_optional_list_is_allowed(tmp_path, documents, monkeypatch):
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert statuses(report)["RD-7 J11 list (RD-7 2)"] == "equal"
    assert code == 0


def test_missing_column_gives_exit_2(tmp_path, documents, monkeypatch):
    del documents["path2"]["harness.json"]["stop_S6_list"]["rows"][0]["position"]
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert code == EXIT_INPUT_ERROR
    item = next(i for i in report["items"] if i["item"] == "RD-7 S-6 list (RD-7 2)")
    assert item["status"] == "missing"
    assert "position" in item["detail"]["input_error"]


def test_missing_key_path_gives_exit_2(tmp_path, documents, monkeypatch):
    del documents["path1"]["u3_judge.json"]["R4"]
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert code == EXIT_INPUT_ERROR
    assert statuses(report)["JD-7 G-6 (3 keys)"] == "missing"


def test_output_file_with_another_name_gives_exit_2(tmp_path, documents, monkeypatch):
    documents["path2"]["p2v5c_merge_v2.json"] = documents["path2"].pop("p2v5c_merge.json")
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert code == EXIT_INPUT_ERROR
    item = next(i for i in report["items"] if i["item"].startswith("RD-7 J-P3"))
    assert "p2v5c_merge.json" in item["detail"]["input_error"]


def test_baseline_sha_other_than_fixed_gives_exit_2(tmp_path, documents):
    for side in ("path1", "path2"):
        for name, document in documents[side].items():
            write_json(tmp_path / side / name, document)
    baseline = tmp_path / "baseline.json"
    write_json(baseline, documents["baseline"])
    out = tmp_path / "report.json"
    code = compare.main(
        [
            "--path1-dir",
            str(tmp_path / "path1"),
            "--path2-dir",
            str(tmp_path / "path2"),
            "--baseline",
            str(baseline),
            "--out",
            str(out),
        ]
    )
    assert code == EXIT_INPUT_ERROR
    report = json.loads(out.read_text(encoding="utf-8"))
    assert statuses(report)["JD-1 J-P3 = jp_base"] == "missing"


def test_family_rule_shapes_are_mapped(tmp_path, documents, monkeypatch):
    p1 = documents["path1"]["family_f.json"]
    p2 = documents["path2"]["p2v5c_grid.json"]["grid"]["family_F_rule"]
    p1["R-4"], p1["result"] = False, "실패"
    p1["R-4_violations"] = [{"key": FAMILY_KEYS[1], "offset_s": 0, "gates": ["end_att"]}]
    p2["R4"] = {"ok": False, "violations": [[FAMILY_KEYS[1], 0.0, ["end_att"]]]}
    p2["result"] = "fail"
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert statuses(report)["S4-5 family F R-1 .. R-4"] == "equal"
    assert code == 0


def test_both_pair_sources_undecided_skip_lists(tmp_path, documents, monkeypatch):
    grid1 = documents["path1"]["grid_h10.json"]
    for name in (
        "raw_pass_to_fail",
        "N_raw",
        "excluded_pass_to_fail",
        "N_F",
        "family_f_rows",
        "record",
    ):
        del grid1[name]
    grid1["v0_pair_source"]["source"] = "판정 불가"
    documents["path2"]["p2v5c_grid.json"]["v0_pair"]["source"] = "undecidable"
    code, report = run_compare(tmp_path, documents, monkeypatch)
    found = statuses(report)
    assert found["S5-3 (a) raw pass->fail, N_raw"] == "equal"
    assert found["S6-2 V0 pair source"] == "equal"
    assert code == 0


RD8_ITEM = "RD-8 undecidable counts and marker"
RD9_ITEM = "RD-9 ③-on counts and H-8 dg3 substitution"
RD10_ITEM = "RD-10 J11 undecidable / input missing"
C16_ITEM = "C-9 .. C-11 records (K-10, CD-10 keys excluded)"


def test_rd8_count_difference_differs(tmp_path, documents, monkeypatch):
    documents["path2"]["harness.json"]["bundles"]["H-1"]["r4"]["rd8"]["breach_reads_bad_format"] = 1
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert statuses(report)[RD8_ITEM] == "differ"
    assert code == 1


def test_rd8_judged_count_uses_v5c_format(tmp_path, documents, monkeypatch):
    documents["path2"]["p2v5c_merge.json"]["RD-8"]["H-9"]["format"] = 2
    code, report = run_compare(tmp_path, documents, monkeypatch)
    item = next(i for i in report["items"] if i["item"] == RD8_ITEM)
    assert item["detail"]["H-9"] == {"path1": {"wrong_form": 0}, "path2": {"wrong_form": 2}}
    assert code == 1


def test_rd9_v5c_count_is_compared_too(tmp_path, documents, monkeypatch):
    documents["path2"]["p2v5c_merge.json"]["RD-9"]["H-9"]["p3_on"] = RD9_COUNT + 1
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert statuses(report)[RD9_ITEM] == "differ"
    assert code == 1


def test_rd9_dg3_substitution_is_compared(tmp_path, documents, monkeypatch):
    excluded = documents["path1"]["r4_lists.json"]["bundles"]["H-8"]["dg3_replaced_excluded"]
    excluded[f"{RK}/h8_noise_VB.json"] = DG3_SUBSTITUTED + 1
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert statuses(report)[RD9_ITEM] == "differ"
    assert code == 1


def test_rd10_missing_count_gives_exit_2(tmp_path, documents, monkeypatch):
    del documents["path2"]["p2v5c_merge.json"]["RD-10"]["H-6"]["input_missing"]
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert statuses(report)[RD10_ITEM] == "missing"
    assert code == EXIT_INPUT_ERROR


def test_c16_leg_seconds_compared_as_milliseconds(tmp_path, documents, monkeypatch):
    legs = documents["path2"]["c16.json"]["rows"]["C10"]["items"]["force"]["legs"]
    legs[3]["t_below_F_min_s"] = 0.251
    code, report = run_compare(tmp_path, documents, monkeypatch)
    item = next(i for i in report["items"] if i["item"] == C16_ITEM)
    assert [d["item"] for d in item["detail"]["item_differences"]] == ["F_below_F_min_ms"]
    assert code == 1


def test_c16_free_text_and_paths_are_not_compared(tmp_path, documents, monkeypatch):
    documents["path2"]["c16.json"]["rows"]["C9on"]["items"]["rc_source"] = "D:/other"
    documents["path1"]["x16_records.json"]["rows"]["C10"]["items"]["times_note"] = "other"
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert statuses(report)[C16_ITEM] == "equal"
    assert code == 0


def test_c16_identity_stop_on_one_side_differs(tmp_path, documents, monkeypatch):
    documents["path2"]["c16.json"]["stops"] = [{"code": "S-12", "where": "C-9:C9on", "why": "x"}]
    code, report = run_compare(tmp_path, documents, monkeypatch)
    item = next(i for i in report["items"] if i["item"] == C16_ITEM)
    assert item["detail"]["identity_stops"]["path2"] == [["C9on", "S-12"]]
    assert code == 1


def test_c16_row_on_one_side_differs(tmp_path, documents, monkeypatch):
    del documents["path1"]["x16_records.json"]["rows"]["C11"]
    code, report = run_compare(tmp_path, documents, monkeypatch)
    item = next(i for i in report["items"] if i["item"] == C16_ITEM)
    assert item["detail"]["item_differences"] == [{"row": "C11", "only_in": "path2"}]
    assert code == 1


def test_rd13_sha_is_recorded_not_compared(tmp_path, documents, monkeypatch):
    del documents["path1"]["item_list.json"]
    code, report = run_compare(tmp_path, documents, monkeypatch)
    assert "not_read" in report["rd13_sha256"]["path1"]
    assert report["rd13_sha256"]["path2"] == {"H-1": "bb"}
    assert code == 0


def test_show_map_prints_sha(capsys):
    assert compare.main(["--show-map"]) == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(last)["column_map_sha256"] == compare.column_map_record()["sha256"]
