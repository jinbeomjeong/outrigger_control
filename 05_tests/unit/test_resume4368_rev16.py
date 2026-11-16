"""436.8 R4 harness re-judgement, path 1 tools (R4 common block e451f067, rules rev13 .. rev25).

RD-2 seal lists (26 revisions), RD-8 ``breach_reads`` form, the RD-7 3 J-P3 input field, rev16
R16-6 J11 with RD-10, the RD-7 lists and their notation, rev16 R16-7 grid grade, R16-3 ABL
expectations, R16-4 V0 tag recomputation, ``r4-lists``, ``h11`` (R16-8), ``h12`` (R16-9 6 with
rev17 R17-2a), C-9 .. C-11 record helpers (R16-11 / R16-11b), RD-13 item lists, RD-5 key map and
RD-1 5 ``head-check``. Synthetic inputs only; no harness, Chrono or judgement run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parents[2]
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
SCRIPTS = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "scripts"
for _path in (COUPLED, SCRIPTS, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import h6_judge_4368 as h6j  # noqa: E402
import judge4368_common as common  # noqa: E402
import judge_stage1_4368 as stage1  # noqa: E402
import resume4368_judge as judge  # noqa: E402
import u3_judge_4368 as u3j  # noqa: E402

TAG_P3 = "final_C4G2_P3_LAS_K1"
TAG_V0 = "final_C4G2_LAS_K1"
REV25 = ("v5_resume_4368_rules_rev25.md",
         "c0b778fd3f53996a2caed37e373975afea591b3c798784843cb9e7eeaac6f233")


def _write_json(path: Path, document) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _write_jsonl(path: Path, lines: list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


def _bound(reads, **extra) -> dict:
    return {"breach_reads": list(reads), "min_gap_bar": [1.0, -2.5, 3.0, 4.0],
            "first_breach_t_s": [None, 12.3, None, None], **extra}


def _main(argv: list[str], out: Path) -> tuple[int, dict]:
    code = judge.main([*argv, "--out", str(out)])
    return code, json.loads(out.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- RD-2 seals
def test_both_harness_seal_lists_are_the_26_revisions() -> None:
    names = ["v5_resume_4368_rules.md", *(f"v5_resume_4368_rules_rev{n}.md"
                                          for n in range(1, 26))]
    assert [name for name, _ in common.SEALED_RULES] == names
    assert [name for name, _ in judge.SEALED_REVISIONS] == names
    assert dict(common.SEALED_RULES) == dict(judge.SEALED_REVISIONS)
    assert REV25 in common.SEALED_RULES


def test_stored_rules_match_the_26_seals() -> None:
    assert common.seal_report()["problems"] == []
    assert judge.sealed_rules_check()["problems"] == []


def test_a_missing_rev25_seal_file_is_s1(tmp_path: Path) -> None:
    for name, _ in judge.SEALED_REVISIONS:
        source = common.RULES_DIR / name
        for path in (source, source.with_suffix(".sha256")):
            shutil.copy2(path, tmp_path / path.name)
    (tmp_path / REV25[0].replace(".md", ".sha256")).unlink()
    assert judge.sealed_rules_check(tmp_path)["stop_S1"] is True
    assert common.seal_report(tmp_path)["stop_S1"] is True


# --------------------------------------------------------------------- RD-8 / RD-7 3 J-P3
@pytest.mark.parametrize("reads, ok", [
    ([0, 0, 0, 0], True), ([0, 2, 0, 1], True), ([], False), ([0, 0, 0], False),
    ([0, 0, 0, 0, 0], False), ([0, 0.0, 0, 0], False), ([0, -1, 0, 0], False),
    ([0, True, 0, 0], False), ([0, None, 0, 0], False), (None, False),
])
def test_breach_reads_form(reads, ok) -> None:
    assert (common.breach_reads_problem({"breach_reads": reads}) is None) is ok


def _assess(item, **changes):
    arguments = {"tag": TAG_P3, "rod_reading": True, "rod_basis": "test",
                 "head_only_declared": False, **changes}
    return common.assess_j_p3(item, **arguments)


def test_wrong_length_breach_reads_is_not_judgeable_never_a_pass() -> None:
    out = _assess({"hydraulics_record": {"extend_bound_check": _bound([0, 0, 0])}})
    assert out["status"] == common.NOT_JUDGEABLE and out["rd8_problem"]
    empty = _assess({"hydraulics_record": {"extend_bound_check": {"breach_reads": [],
                                                                  "rule": "x"}}})
    assert empty["status"] == common.NOT_JUDGEABLE


def test_j_p3_pass_breach_rows_and_not_applicable() -> None:
    assert _assess({"hydraulics_record": {"extend_bound_check": _bound([0] * 4)}})[
        "status"] == common.J_P3_PASS
    breach = _assess({"hydraulics_record": {"extend_bound_check": _bound([0, 3, 0, 0])}})
    assert breach["status"] == common.J_P3_H7 and breach["breach_reads_sum"] == 3
    assert breach["rows"] == [{"leg": "FR", "breach_reads": 3, "min_gap_bar": -2.5,
                               "first_breach_t_s": 12.3}]
    assert _assess({}, tag=TAG_V0)["status"] == common.J_P3_NOT_APPLICABLE
    assert _assess({}, rod_reading=None)["status"] == common.NOT_JUDGEABLE
    assert _assess({}, rod_stop="S-2: x")["status"] == common.J_P3_S2


def test_top_level_copy_with_other_breach_reads_is_not_judgeable() -> None:
    """RD-7 3: the input is hydraulics_record.extend_bound_check; a top-level copy must match."""
    item = {"hydraulics_record": {"extend_bound_check": _bound([0, 0, 0, 0])},
            "extend_bound_check": _bound([0, 1, 0, 0])}
    assert _assess(item)["status"] == common.NOT_JUDGEABLE
    item["extend_bound_check"] = _bound([0, 0, 0, 0])
    assert _assess(item)["status"] == common.J_P3_PASS


def test_u3_item_input_is_under_v5() -> None:
    item = {"v5": {"hydraulics_record": {"extend_bound_check": _bound([1, 0, 0, 0])}}}
    bound, problem = common.j_p3_bound(item)
    assert bound["breach_reads"] == [1, 0, 0, 0] and problem is None


def test_list_values_are_the_recorded_elements_or_null() -> None:
    """Supplement 3-3: min_gap_bar / first_breach_t_s elements moved as recorded; a missing,
    non-number or non-finite element is null; no Pa key is converted."""
    bound = {"min_gap_bar": [0.123456789012345, float("nan"), "x", float("inf")],
             "first_breach_t_s": [12.3456789, None, True, 1],
             "min_gap_Pa": [1e5, 2e5, 3e5, 4e5]}
    assert [common.min_gap_bar(bound, i) for i in range(4)] == [0.123456789012345, None, None,
                                                                None]
    assert [common._per_leg(bound, "first_breach_t_s", i) for i in range(4)] == [12.3456789,
                                                                                 None, None, 1]
    assert common.min_gap_bar({"min_gap_Pa": [1e5, 2e5, 3e5, -4e5]}, 3) is None


def test_h6_and_stage1_use_the_rd8_form() -> None:
    run = {"key": "k", "controller_tag": TAG_P3, "head_only_declared": False,
           "controller_settings": {h6j.EXTEND_START_SETTING: "tracked_bound"},
           "hydraulics_record": {"extend_bound_check": _bound([0, 0])}}
    out = h6j.j_p3(run, ())
    assert out["case"] == h6j.J_P3_NOT_JUDGEABLE and out["missing"] and out["rd8_problem"]
    line = {"controller_tag": TAG_P3, "head_only_declared": False, "is_event": False,
            "row": "R1", "bound_check": _bound([0, 0]), "rod_reading": True,
            "t4h_lookup": {"status": common.T4H_FOUND}}
    assert stage1.j_p3_item(line)[0]["kind"] == "not_judgeable"


# ------------------------------------------------------------------------- R16-6 / RD-10 J11
def _lwa(legs=("RL",), **values):
    by_leg = {"FL": 0, "FR": 0, "RL": 0, "RR": 0, **values}
    return {"fallback_legs": {leg: {} for leg in legs}, "n_late_fallback_by_leg": by_leg,
            "n_late_fallback": sum(v or 0 for v in by_leg.values())}


@pytest.mark.parametrize("block, setting, state, marker", [
    (_lwa(RL=1), "VB", common.J11_STOP, common.STOP_H7),
    (_lwa(RL=1), "LS2", common.J11_STOP, common.STOP_LE),
    (_lwa(FL=5), "VB", common.J11_PASS, None),  # FL is not an actual fallback leg
    (_lwa(RL=None), "VB", common.NOT_JUDGEABLE, None),
    (None, "VB", common.NOT_JUDGEABLE, None),
    ([1, 2], "LS1", common.NOT_JUDGEABLE, None),
    (None, "V0", common.J11_NO_INPUT, None),
    (None, "V5", common.J11_NO_INPUT, None),
    (_lwa(RL=2), "V7", common.J11_RECORD, None),
    ({"n_late": None, "reason": "no rod reading"}, "VB", common.J11_PASS, None),
])
def test_assess_j11(block, setting, state, marker) -> None:
    out = common.assess_j11(block, setting)
    assert (out["state"], out["marker"]) == (state, marker)


def test_j11_list_rows_carry_the_leg_value_and_marker() -> None:
    rows = common.j11_list_rows(common.assess_j11(_lwa(("RL", "FR"), RL=2, FR=1), "VB"),
                                bundle="H-10", result_file="r.jsonl", location="line 3",
                                key="R12", setting="VB")
    assert [(r["leg"], r["n_late_fallback_by_leg"], r["marker"]) for r in rows] == [
        ("FR", 1, "H-7"), ("RL", 2, "H-7")]


# -------------------------------------------------------------------------- RD-7 3 notation
def test_physical_line_numbers_count_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "h9_stage1.jsonl"
    path.write_text('{"a": 1}\n\n{"a": 2}\n', encoding="utf-8")
    assert [n for n, _ in common.read_jsonl_numbered(path)] == [1, 3]


@pytest.mark.parametrize("name, item, expected", [
    ("h1_d1.jsonl", {"job": {"d1": {"key": "K"}, "setting": "VB"}}, ("K", "VB")),
    ("h10_reuse_rerun.jsonl", {"job": {"case": "R3", "setting": "LS1"}}, ("R3", "LS1")),
    ("h8_noise_VB.json", {"key": "k", "v5_setting": "VB"}, ("k", "VB")),
    ("grid_r67_top.json", {"key": "g", "v5_setting": "VB"}, ("g", "VB")),
    ("u3_g8_VB.json", {"id": "slope|x", "v5": {"v5_setting": "VB"}}, ("slope|x", "VB")),
    ("u3_D_VB.json", {"key": "kk", "id": "i", "v5": {"v5_setting": "VB"}}, ("kk", "VB")),
    ("u6_b5_main_VB.json", {"case": "A1-J1", "v5": {"v5_setting": "VB"}}, ("A1-J1", "VB")),
    ("other.json", {"key": "x"}, (None, None)),
])
def test_key_and_setting_by_file_form(name, item, expected) -> None:
    assert common.key_and_setting(name, item) == expected


def test_list_order_bundle_number_file_location_leg_k() -> None:
    rows = [{"bundle": "H-10", "result_file": "a", "location": "line 2", "leg": "FL"},
            {"bundle": "H-9", "result_file": "b", "location": "results[10].runs[0]"},
            {"bundle": "H-9", "result_file": "b", "location": "results[2].runs[11]"},
            {"bundle": "H-9", "result_file": "a", "location": "line 10", "leg": "RR"},
            {"bundle": "H-9", "result_file": "a", "location": "line 10", "leg": "FR"}]
    ordered = sorted(rows, key=common.list_sort_key)
    assert [(r["bundle"], r["location"], r.get("leg")) for r in ordered] == [
        ("H-9", "line 10", "FR"), ("H-9", "line 10", "RR"), ("H-9", "results[2].runs[11]", None),
        ("H-9", "results[10].runs[0]", None), ("H-10", "line 2", "FL")]


# --------------------------------------------------------------------------- R16-7 grid grade
def _grid(runs_reads, tag=TAG_P3, event="G4", lwa=None) -> dict:
    blocks = lwa if lwa is not None else [_lwa()] * len(runs_reads)
    runs = [{"event": event, "offset_s": float(i), "commands_sha256": "h",
             "hydraulics_record": {"extend_bound_check": _bound(reads)},
             "lock_window_alignment": block, "resume_k1": {"applicable": True}}
            for i, (reads, block) in enumerate(zip(runs_reads, blocks, strict=True))]
    return {"meta": {"spec": judge.GRID_SPEC, "v5_setting": "VB"},
            "results": [{"key": "screen|top|0.0|level|FR", "v5_setting": "VB",
                         "controller_tag": tag, "runs": runs}]}


def test_grid_grade_marker_list_and_not_judgeable(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "h9_grid" / "grid_r67_main.json",
                       _grid([[0, 0, 0, 0], [0, 0, 2, 0], [0, 0]]))
    out = stage1.grid_grade([path])
    assert out["markers"] == [common.STOP_H7] and out["grade"] == common.NOT_JUDGEABLE
    assert out["J-P3_not_judgeable_RD8"] == 1 and out["p3_runs_RD9"] == 3
    row = out["J-P3_violations_RD7"][0]
    assert (row["location"], row["leg"], row["breach_reads"], row["setting"]) == (
        "results[0].runs[1]", "RL", 2, "VB")
    clean = stage1.grid_grade([_write_json(tmp_path / "h9_grid" / "grid_r69_top.json",
                                           _grid([[0, 0, 0, 0]]))])
    assert clean["grade"] == "통과" and clean["markers"] == []


def test_grid_runs_get_j11_and_rd10(tmp_path: Path) -> None:
    """Supplement 2-2: J11 per grid run (setting VB), RD-10 block missing = 판정 불가."""
    path = _write_json(tmp_path / "h9_grid" / "grid_r67_top.json",
                       _grid([[0] * 4, [0] * 4, [0] * 4],
                             lwa=[_lwa(RL=2), None, _lwa()]))
    out = stage1.grid_grade([path])
    assert [(r["location"], r["leg"], r["marker"]) for r in out["J11_stops_RD7"]] == [
        ("results[0].runs[0]", "RL", "H-7")]
    assert out["J11_RD10"] == {"not_judgeable": 1, "no_input": 0}
    assert "J11 멈춤 H-7" in out["markers"] and out["grade"] == common.NOT_JUDGEABLE


def test_grid_setting_is_the_job_v5_setting_only(tmp_path: Path) -> None:
    """Supplement 3-6: no meta fallback; a job without v5_setting makes its runs' J11 판정 불가."""
    document = _grid([[0] * 4, [0] * 4])
    del document["results"][0]["v5_setting"]
    out = stage1.grid_grade([_write_json(tmp_path / "h9_grid" / "grid_r69_top.json", document)])
    assert out["J11_RD10"]["not_judgeable"] == 2 and out["grade"] == common.NOT_JUDGEABLE
    assert common.assess_j11(_lwa(), None)["state"] == common.NOT_JUDGEABLE


def _stage1_line(case: str, setting: str, tag: str, reads, lwa, t4h: str | None) -> dict:
    line = {"job": {"case": case, "setting": setting}, "controller_tag": tag,
            "head_only_declared": False,
            "hydraulics_record": {"extend_bound_check": None if reads is None else _bound(reads)},
            "lock_window_alignment": lwa}
    if t4h is not None:
        line["t4h_file"] = t4h
    return line


def test_stage1_r4_lines_block(tmp_path: Path) -> None:
    path = tmp_path / "h10_reuse_rerun.jsonl"
    folder = tmp_path / "h10_reuse_rerun_t4h"
    folder.mkdir()
    np.savez(folder / "a.npz", rod_pressure_Pa=np.array([2.0e6]))
    lines = [_stage1_line("R3", "VB", TAG_P3, [0, 0, 0, 2], _lwa(RL=1), "a.npz"),
             _stage1_line("R4", "VB", TAG_P3, [0, 0], _lwa(), "a.npz"),
             _stage1_line("R3", "V0", TAG_V0, None, None, None),
             _stage1_line("R5", "LS3", TAG_P3, [0, 0, 0, 0], None, "a.npz")]
    path.write_text(json.dumps(lines[0]) + "\n\n" + "".join(json.dumps(x) + "\n"
                                                            for x in lines[1:]),
                    encoding="utf-8")
    numbered = common.read_jsonl_numbered(path)
    block = stage1.r4_lines_block("H-10", path, numbered,
                                  tuple(common.t4h_folders(path, [r for _, r in numbered])))
    assert block["p3_lines_RD9"] == 3 and block["J-P3_not_judgeable_RD8"] == 1
    assert [(r["location"], r["leg"], r["key"]) for r in block["J-P3_violations_RD7"]] == [
        ("line 1", "RR", "R3")]
    assert [(r["location"], r["leg"], r["marker"]) for r in block["J11_stops_RD7"]] == [
        ("line 1", "RL", "H-7")]
    assert block["J11_RD10"] == {"not_judgeable": 1, "no_input": 1}
    markers = stage1.r4_markers("H-10", block)
    assert "H-10 J-P3: 멈춤 H-7" in markers and "H-10 J11: 멈춤 H-7" in markers


def test_u3_g5_g6_list_rows_by_location(tmp_path: Path) -> None:
    path = tmp_path / "u3_g8_VB.json"
    payload = {"records": [{"id": "slope|a", "suite": "g8", "v5": {"v5_setting": "VB"}},
                           {"id": "slope|b", "suite": "g8", "v5": {"v5_setting": "VB"}}]}
    places = u3j.item_places(path, payload)
    keys = [u3j.base.v5_rerun.entry_key(item) for item in payload["records"]]
    rows = u3j.list_rows([keys[1], keys[0]], places)
    assert [(r["location"], r["key"], r["bundle"]) for r in rows] == [
        ("records[0]", "slope|a", "H-3"), ("records[1]", "slope|b", "H-3")]


# ------------------------------------------------------------------------- R16-3 / R16-4
def _abl_line(controller="ABL", tag="ABL_LAS_K1", require=False) -> dict:
    settings = dict(judge.LAS_PRESET, require_soil_response=require)
    return {"case": "A1-J1", "controller": controller,
            "v5": {"controller_tag": tag, "resume_k1": {
                "applicable": True, "k1_order_gate_request": "preset",
                "k1_order_gate_effective": True,
                "slope_clearance_margin": {"settings": {"flat_soil_margin_order_gate": True,
                                                        "flat_soil_margin_m": 0.0}},
                "liftoff_approach_slow": {"settings": settings}}}}


def test_abl_line_expects_require_soil_response_false() -> None:
    assert judge.harness_record_problems(_abl_line()) == []
    assert judge.harness_record_problems(_abl_line(require=True))
    c2 = _abl_line(controller="C2", tag=TAG_P3, require=False)
    assert any("require_soil_response" in p for p in judge.harness_record_problems(c2))


@pytest.mark.parametrize("controller, tag", [("ABL", TAG_P3), ("C2", "ABL_LAS_K1")])
def test_abl_name_and_tag_must_agree(controller, tag) -> None:
    problems = judge.harness_record_problems(_abl_line(controller=controller, tag=tag))
    assert problems and problems[0].startswith(judge.KIND_DEFECT_PREFIX)


def _r79(**changes) -> dict:
    record = {"key": "L2|s0|g6|1|ref|J1|top|Fs0", "seed_index": 0, "harness": "g6",
              "inner": "x", "v5_setting": "V0", "controller_tag": TAG_V0,
              "resume_k1": {"applicable": True,
                            "liftoff_approach_slow": {"settings": {"enable": True}},
                            "slope_clearance_margin": {
                                "settings": {"flat_soil_margin_order_gate": True}}}}
    record.update(changes)
    return record


def test_v0_result_without_hydraulic_options_reads_as_extend_start_off() -> None:
    assert judge._tag_recompute_record(_r79())["status"] == judge.TAG_MATCH
    assert judge._tag_recompute_record(_r79(v5_setting="VB"))["not_computable"] is True
    wrong = judge._tag_recompute_record(_r79(controller_tag=TAG_P3))
    assert wrong["status"] == judge.TAG_STOP


# --------------------------------------------------------------------------------- r4-lists
def _decision(block=True, due=True, k=0) -> dict:
    return {"t_loc_s": 30.0 + k, "n_P": 213, "n_S": 218, "dP": -5, "would_block": block,
            "r4_due_without_gate": due, "applied": False}


def _resume_block(decisions=()) -> dict:
    return {"applicable": True, "slope_clearance_margin": {
        "order_gate": {"decisions": list(decisions)}}}


def _build_root(root: Path, family: str = "균일 연약") -> Path:
    resume, las = root / judge.RESUME_K1_DIR, root / judge.LAS_K1_DIR
    vb_pass = {"job": {"d1": {"key": "D1|a", "group": "H-S-0"}, "setting": "VB"},
               "controller_tag": TAG_P3, "d1": {"j_p3": "pass"},
               "resume_k1": _resume_block([_decision(), _decision(block=False, k=1)])}
    v0 = {"job": {"d1": {"key": "D1|b", "group": "H-R-0"}, "setting": "V0"},
          "controller_tag": TAG_V0, "resume_k1": _resume_block()}
    _write_jsonl(resume / "h1_d1.jsonl", [vb_pass, v0])
    u3 = {"records": [{"id": "base|G1|B|top|Fs0", "suite": "p3b",
                       "v5": {"v5_setting": "VB", "controller_tag": TAG_P3, "j_p3": "pass",
                              "hydraulics_record": {"extend_bound_check": _bound([0, 0, 0])},
                              "resume_k1": _resume_block()}}]}
    _write_json(las / "u3_p3b_VB.json", u3)
    h6 = {"results": [{"key": "cand=current#L3|s0|g6|1|ref|J1|top|Fs0", "v5_setting": "VB",
                       "seed_index": 0, "harness": "g6", "inner": "x",
                       "controller_tag": TAG_P3, "head_only_declared": False,
                       "hydraulics_record": {"extend_bound_check": _bound([0, 1, 0, 0])},
                       "extend_bound_check": _bound([0, 1, 0, 0]),
                       "lock_window_alignment": _lwa(RL=1), "resume_k1": _resume_block()}]}
    _write_json(resume / "h6_dg3_v4on.json", h6)
    _write_json(resume / "h9_grid" / "grid_r67_main.json",
                _grid([[0, 0, 0, 0], [2, 0, 0, 0]], event="other"))
    # the RV1-6 table keys run_v5 lines by run_v5.job_key (= record_key here)
    return _write_json(root / "family.json", {"rows": [
        {"key": judge.record_key(vb_pass), "family": family}]})


def test_r4_lists_end_to_end(tmp_path: Path) -> None:
    table = _build_root(tmp_path)
    grid = tmp_path / judge.RESUME_K1_DIR / "h9_grid" / "grid_r67_main.json"
    document = json.loads(grid.read_text(encoding="utf-8"))
    document["results"][0]["runs"][0]["resume_k1"] = _resume_block([_decision()])
    grid.write_text(json.dumps(document), encoding="utf-8")
    code, report = _main(["r4-lists", "--root", str(tmp_path), "--family-table", str(table),
                          "--bundles", "H-1", "H-3", "H-6", "H-9"], tmp_path / "lists.json")
    assert code == 1
    h1, h3 = report["bundles"]["H-1"], report["bundles"]["H-3"]
    assert h1["RD-8"]["vb_pass_without_breach_reads"] == 1
    assert common.MARKER_JP3_FORM in h1["markers"] and h1["p3_units_RD9"] == 1
    assert h3["RD-8"]["wrong_form"] == 1 and common.MARKER_JP3_FORM in h3["markers"]
    s6 = report["lists"]["S-6"]
    assert [(r["bundle"], r["location"], r["k"]) for r in s6] == [
        ("H-1", "line 1", 0), ("H-9", "results[0].runs[0]", 0)]
    assert s6[0]["family"] == "균일 연약" and s6[0]["dP"] == -5
    assert s6[0]["result_file"] == f"{judge.RESUME_K1_DIR}/h1_d1.jsonl"
    jp3 = report["lists"]["J-P3"]
    assert [(r["bundle"], r["location"], r["leg"]) for r in jp3] == [
        ("H-6", "results[0]", "FR"), ("H-9", "results[0].runs[1]", "FL")]
    assert jp3[0]["key"] == "cand=current#L3|s0|g6|1|ref|J1|top|Fs0"
    assert [(r["bundle"], r["leg"], r["marker"]) for r in report["lists"]["J11"]] == [
        ("H-6", "RL", "H-7")]
    assert report["bundles"]["H-9"]["missing_files"]  # the other grid files and h9_stage1


def _r79_line(key: str, setting: str, tag: str, reads, lwa) -> dict:
    bound = None if reads is None else _bound(reads)
    return {"key": key, "v5_setting": setting, "seed_index": 0, "harness": "g6", "inner": "x",
            "controller_tag": tag, "head_only_declared": False,
            "hydraulics_record": {"extend_bound_check": bound}, "extend_bound_check": bound,
            "lock_window_alignment": lwa, "resume_k1": _resume_block()}


def test_r4_lists_h8_leaves_out_the_dg3_keys_and_v0_records(tmp_path: Path) -> None:
    """Supplement 2-1 with 3-1 / 3-2: dg3-replaced keys leave the h8_noise_VB lists only (a
    seedext VB line with the same key stays), they still count in RD-9; V0 J11 is a record."""
    resume = tmp_path / judge.RESUME_K1_DIR
    replaced, kept = "L3|s0|g6|1|ref|J1|top|Fs0", "L3|s1|g6|1|ref|J1|top|Fs0"
    _write_json(tmp_path / judge.DG3_KEY_SOURCE, {"results": [{"key": f"cand=current#{replaced}"}]})
    _write_json(resume / "h8_noise_VB.json", {"results": [
        _r79_line(f"cand=current#{replaced}", "VB", TAG_P3, [0, 1, 0, 0], _lwa(RL=1)),
        _r79_line(f"cand=current#{kept}", "VB", TAG_P3, [1, 0, 0, 0], _lwa(RL=1))]})
    _write_json(resume / "h8_noise_V0.json", {"results": [
        _r79_line(kept, "V0", TAG_V0, None, _lwa(RL=3))]})
    _write_json(resume / "h8_seedext_VB.json", {"results": [
        _r79_line(f"cand=current#{replaced}", "VB", TAG_P3, [0, 0, 2, 0], _lwa())]})
    table = _write_json(tmp_path / "family.json", {"rows": []})
    _, report = _main(["r4-lists", "--root", str(tmp_path), "--family-table", str(table),
                       "--bundles", "H-8"], tmp_path / "lists.json")
    assert [(r["result_file"].rsplit("/", 1)[-1], r["location"], r["leg"])
            for r in report["lists"]["J-P3"]] == [("h8_noise_VB.json", "results[1]", "FL"),
                                                  ("h8_seedext_VB.json", "results[0]", "RL")]
    assert [(r["result_file"].rsplit("/", 1)[-1], r["location"]) for r in report["lists"]["J11"]
            ] == [("h8_noise_VB.json", "results[1]")]
    bundle = report["bundles"]["H-8"]
    assert list(bundle["dg3_replaced_excluded"].values()) == [1]
    assert bundle["p3_units_RD9"] == 3 and report["dg3_key_source"]["keys"] == 1


def test_r4_lists_grid_runs_are_in_the_j11_list(tmp_path: Path) -> None:
    grid = tmp_path / judge.RESUME_K1_DIR / "h9_grid" / "grid_r69_bottom.json"
    _write_json(grid, _grid([[0] * 4, [0] * 4], lwa=[_lwa(), _lwa(("FR",), FR=1)]))
    table = _write_json(tmp_path / "family.json", {"rows": []})
    _, report = _main(["r4-lists", "--root", str(tmp_path), "--family-table", str(table),
                       "--bundles", "H-9"], tmp_path / "lists.json")
    assert [(r["location"], r["leg"], r["setting"]) for r in report["lists"]["J11"]] == [
        ("results[0].runs[1]", "FR", "VB")]


@pytest.mark.parametrize("src, family", [
    ("g6|G1+J1@FL|top|Fs0", "patch_or_sink"), ("slope|J1|top|4.0", "uniform"),
    ("g6|rigid|top|Fs8", "rigid"), ("g6|rigid+S1@FR|top|Fs4", "patch_or_sink"),
    ("drop_RR_30|top", None), ("", None),
])
def test_u6_src_ground_token_family(src, family) -> None:
    """Supplement 2-7: the inner key is ``src``, not the case name."""
    assert judge.u6_src_family({"case": "A1-J1", "src": src}) == family


def test_r4_lists_patch_family_is_no_s6(tmp_path: Path) -> None:
    table = _build_root(tmp_path, family="패치·처방 침하")
    _, report = _main(["r4-lists", "--root", str(tmp_path), "--family-table", str(table),
                       "--bundles", "H-1"], tmp_path / "lists.json")
    assert report["lists"]["S-6"] == []


# ------------------------------------------------------------------------- H-11 (R16-8)
def _h11_dirs(tmp_path: Path, differ_key: str | None = None) -> tuple[Path, Path]:
    h11, las = tmp_path / "H-11", tmp_path / "las_k1"
    files: dict[tuple[Path, str], dict] = {}
    for pair in judge.H11_PAIRS:
        for folder, name in ((h11, pair.new_file),
                             (h11 if pair.target_in_h11 else las, pair.target_file)):
            container = "records" if pair.key_field in ("id", "case") and "D_" not in name \
                else "results"
            document = files.setdefault((folder, name), {container: []})
            value = "same" if not (differ_key == pair.key and folder == h11
                                   and name == pair.new_file) else "other"
            item = {pair.key_field: pair.key}
            if pair.controller:
                item["controller"] = pair.controller
            target = item
            for part in pair.compare_field.split(".")[:-1]:
                target = target.setdefault(part, {})
            target[pair.compare_field.split(".")[-1]] = value
            next(iter(document.values())).append(item)
    for (folder, name), document in files.items():
        _write_json(folder / name, document)
    for name in judge.H11_RUN_FILES:
        entry = {"git": {"head": judge.R2_COMMIT, "is_clean": True}}
        _write_json(h11 / name.replace(".json", ".identity.json"),
                    {"start": [entry], "end": [entry]})
    return h11, las


def test_h11_all_pairs_same_is_g3_true(tmp_path: Path) -> None:
    h11, las = _h11_dirs(tmp_path)
    code, report = _main(["h11", "--h11-dir", str(h11), "--las-k1-dir", str(las)],
                         tmp_path / "h11.json")
    assert code == 0 and report["G-3"] is True and report["pass"] is True
    assert len(report["pairs"]) == 8 and report["false_pairs_RD7"] == []


def test_h11_one_hash_differs_is_g3_false_with_the_pair_row(tmp_path: Path) -> None:
    h11, las = _h11_dirs(tmp_path, differ_key="A1-J1")
    code, report = _main(["h11", "--h11-dir", str(h11), "--las-k1-dir", str(las)],
                         tmp_path / "h11.json")
    assert code == 1 and report["G-3"] is False and report["pass"] is False
    assert report["false_pairs_RD7"] == [{
        "script": "b5_baseline_compare.py", "key": "A1-J1", "compare_field": "commands_sha256",
        "no_option_hash": "other", "target_hash": "same", "no_option_lines": 1,
        "target_lines": 1}]


def test_h11_dirty_identity_is_s12_and_u3_judge_stops_on_false_g3(tmp_path: Path) -> None:
    h11, las = _h11_dirs(tmp_path)
    _write_json(h11 / "u3_C_none.identity.json",
                {"start": [{"git": {"head": judge.R2_COMMIT, "is_clean": False}}],
                 "end": [{"git": {"head": judge.R2_COMMIT, "is_clean": True}}]})
    code, report = _main(["h11", "--h11-dir", str(h11), "--las-k1-dir", str(las)],
                         tmp_path / "h11.json")
    assert code == 1 and report["G-3"] is True and report["pass"] is False
    stopped = u3j.judge(argparse.Namespace(g3=str(tmp_path / "h11.json")))
    assert stopped["findings"] and "G-3" in stopped["status"]


# --------------------------------------------------------------------- H-12 (R16-9 6, R17-2a)
def _t4h(path: Path, fallback=(None, None, 5.0, None), locked_after=True) -> Path:
    t_s = np.arange(0.0, 10.0, 0.1)
    locked = np.zeros((t_s.size, 4), dtype=np.int8)
    if locked_after:
        locked[60:, 2] = 1
    command = np.zeros((t_s.size, 4))
    meta = {"job": {"key": path.stem}, "fallback_start_s": list(fallback)}
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, t_s=t_s, locked=locked, command_m_s=command, meta_json=json.dumps(meta))
    return path


def _replay(tmp_path: Path, over: dict[str, dict]) -> Path:
    rows = [{"file": name, "over_0p6kN_by_leg": {"FL": 0, "FR": 0, "RL": 0, "RR": 0, **legs},
             "max_excess_N": 1.0, "unlocked_tail_over_0p6kN_by_leg": {},
             "recorded_lower_max_abs_N": 1e-12, "settings_equal": True}
            for name, legs in over.items()]
    return _write_json(tmp_path / "replay.json", {"rows": rows})


def _h12(tmp_path: Path, over: dict[str, dict], **t4h) -> dict:
    for name in over:
        _t4h(tmp_path / "H-12" / "t4h" / name, **t4h)
    _, report = _main(["h12", "--h12-dir", str(tmp_path / "H-12"), "--replay",
                       str(_replay(tmp_path, over))], tmp_path / "h12.json")
    return report


def test_h12_forced_leg_excess_only_is_the_range_gap(tmp_path: Path) -> None:
    """R17-2a: FR over in the forced replay, actual fallback leg RL clean -> ranges differ."""
    report = _h12(tmp_path, {"a.npz": {"FR": 1}, "b.npz": {}, "c.npz": {}})
    assert report["range_forced_four_legs_H7"] is True
    assert report["range_actual_fallback_legs_H7"] is False
    assert report["markers"] == [judge.H12_GAP_MARKER] and report["state"] == "기록 완료"
    assert report["keys"][0]["actual_fallback_legs"] == ["RL"]


def test_h12_actual_leg_excess_is_h7_in_both_ranges(tmp_path: Path) -> None:
    report = _h12(tmp_path, {"a.npz": {"RL": 2}, "b.npz": {}, "c.npz": {}})
    assert report["markers"] == [judge.STOP_H7_TEXT]


def test_h12_empty_window_leaves_the_bundle_incomplete(tmp_path: Path) -> None:
    report = _h12(tmp_path, {"a.npz": {}, "b.npz": {}, "c.npz": {}}, locked_after=False)
    assert report["state"] == "기록 불완전" and not any(k["judged"] for k in report["keys"])
    assert report["keys"][0]["locked_samples_after_fallback"] == {"RL": 0}


def test_locked_samples_use_the_previous_period_command() -> None:
    arrays = {"t_s": np.array([0.0, 0.1, 0.2]), "locked": np.ones((3, 4)),
              "command_m_s": np.array([[0.0] * 4, [0.01, 0, 0, 0], [0.0] * 4])}
    assert judge.locked_samples_after(arrays, 0.0, 0) == 2  # sample 2 acts on 0.01
    assert judge.locked_samples_after(arrays, 0.1, 1) == 2


# -------------------------------------------------------------- C-9 .. C-11 (R16-11 / R16-11b)
def _identity_files(folder: Path, row_id: str, *, head=judge.R2_COMMIT, env=None,
                    case: str = "c") -> None:
    pre = {"ok": True, "dry": False, "head": head, "tracked_status": [], "case": case,
           "forbidden_env": {name: None for name in judge.FORBIDDEN_IDENTITY_ENV},
           "dll_sha256": judge.HULL_DLL_SHA256}
    post = {"ok": True, "head": head, "tracked_status": [], "reflog_new_since_pre": [],
            "forbidden_env": {name: None for name in judge.FORBIDDEN_IDENTITY_ENV}}
    if env:
        post["forbidden_env"][env] = "1"
    _write_json(folder / f"{row_id}_pre.json", pre)
    _write_json(folder / f"{row_id}_post.json", post)


def _x16_result(mask=0x000F) -> dict:
    return {"code_state": {"git_at_start": {"head": judge.R2_COMMIT}}, "num_threads_chrono": 4,
            "placement": {"omp_wait_policy": "PASSIVE", "affinity_mask_process":
                          f"0x{mask:08X}", "mode": "pcore"},
            "hull_hook": {"mode": "fast", "dll_sha_validated": True,
                          "dll_sha256": judge.HULL_DLL_SHA256}}


def test_x16_identity_ok_and_its_stops(tmp_path: Path) -> None:
    _identity_files(tmp_path, "C9on")
    assert judge.x16_identity("C9on", "c", 0x000F, tmp_path, _x16_result())["ok"] is True
    wrong_mask = judge.x16_identity("C9on", "c", 0x00F0, tmp_path, _x16_result())
    assert wrong_mask["S-4"] and not wrong_mask["S-12"]
    _identity_files(tmp_path, "C9off", head="0" * 40, env="MIXED_HULL_MODE")
    bad = judge.x16_identity("C9off", "c", 0x000F, tmp_path, _x16_result())
    assert bad["S-12"] and bad["S-4"]


def test_run_exit_code_from_the_first_line_of_the_only_done_mark(tmp_path: Path) -> None:
    """Supplement 2-4: logs_*/<short>_run.done, first line only; 0 or 2+ marks or no exit= on
    the first line = no rc (the row is 기록 불완전)."""
    (tmp_path / "logs_Y1").mkdir()
    (tmp_path / "logs_Y1" / "C9on_run.done").write_text("2026 exit=0 wall_s=5\nexit=3\n",
                                                        encoding="utf-8")
    assert judge.run_exit_code(tmp_path, "C9on") == (0, None)
    assert judge.run_exit_code(tmp_path, "C9off")[0] is None
    assert judge.run_exit_code(tmp_path, None)[0] is None
    (tmp_path / "logs_X1").mkdir()
    (tmp_path / "logs_X1" / "C9on_run.done").write_text("exit=0\n", encoding="utf-8")
    rc, reason = judge.run_exit_code(tmp_path, "C9on")
    assert rc is None and reason.startswith("2 ")
    (tmp_path / "logs_X1" / "C11VB_run.done").write_text("started\nexit=0\n", encoding="utf-8")
    assert judge.run_exit_code(tmp_path, "C11VB")[0] is None


def test_short_names_come_from_the_pre_identity_case(tmp_path: Path) -> None:
    _identity_files(tmp_path, "C9on", case="R4368X_G1_B_top_Fs4_V0_gateon")
    _identity_files(tmp_path, "C11VB", case="R4368X_J2_B_top_Fs0_L2_VB")
    assert judge.short_names_by_case(tmp_path) == {"R4368X_G1_B_top_Fs4_V0_gateon": "C9on",
                                                    "R4368X_J2_B_top_Fs0_L2_VB": "C11VB"}


def _p3(name, verdict=None, value=None) -> dict:
    return {"item": name, "verdict": verdict, "value": value}


def test_scm_p3_items_uses_the_path1_chrono_code_and_fails_soft(tmp_path: Path) -> None:
    rows_judge, bundle = judge._chrono_modules()
    assert callable(bundle.p3_items) and callable(rows_judge.judge_scm)
    assert judge.scm_p3_items(tmp_path, {}) is None  # no result.json: 기록 불완전, no crash
    assert judge.g6_gates(tmp_path, {}) is None


def test_g6_from_p3_by_the_cd11_table() -> None:
    items = [_p3("P3-1", "pass"), _p3("P3-2", "flag"), _p3("P3-3", "fail"), _p3("P3-4", "pass"),
             _p3("P3-5", None, "해당 없음(rigid_base)"), _p3("P3-8", "flag")]
    judged = {"ready_D-27_D-28": {"t_ready_rel_s": 70.0, "READY_le_120s": True},
              "P3-8_D-34_D-35": {"fault": False}}
    gates = judge.g6_from_p3(items, judged)
    assert {name: gate["value"] for name, gate in gates.items()} == {
        "G6-1": "pass", "G6-2": "flag", "G6-3": "fail", "G6-4": "pass",
        "G6-5": "해당 없음(rigid_base)", "G6-7": "flag", "G6-6": "pass", "READY_le_120s": "pass"}
    no_ready = judge.g6_from_p3(items, {"ready_D-27_D-28": {"t_ready_rel_s": None},
                                        "P3-8_D-34_D-35": {"fault": False}})
    assert no_ready["G6-6"]["value"] == "fail" and no_ready["READY_le_120s"]["value"] == "fail"
    faulted = judge.g6_from_p3(items, {**judged, "P3-8_D-34_D-35": {"fault": True}})
    assert faulted["G6-6"]["value"] == "fail"


def test_p18_premise() -> None:
    good = {"duration_s": 120, "threads": 4, "placement_mode": "pcore",
            "items": {"rc": 0, "last_sample_s": 119.95, "first_ready_s": 70.0}}
    assert judge.p18_premise(good, good)["holds"] is True
    short = {**good, "items": {**good["items"], "last_sample_s": 119.0}}
    assert judge.p18_premise(good, short)["holds"] is False


def test_c11_loc_period_crawler_maximum(tmp_path: Path) -> None:
    t_s = np.round(np.arange(0.0, 20.0, 0.001), 6)
    crawler = np.where((t_s > 9.9) & (t_s <= 10.0), 2000.0, 0.0)
    crawler[t_s == 9.9] = 99999.0  # the sample at t_loc - 0.1 s is not in the period
    np.savez(tmp_path / "step_series.npz", t_s=t_s, scm_crawler_normal_N=crawler)
    result = {"p3b": {"P3-2_loc": {"t_loc_first_s": 10.0}, "weight_N": 100000.0,
                      "checks": {"loc_revokes": 0}}}
    items = judge.c11_items(tmp_path, result)
    assert items["loc_period_crawler_max_N"] == 2000.0
    assert items["loc_period_ge_0p01W"] is True and items["loc_cancels"] == 0
    assert "final_loc_period_crawler_max_N" not in items
    # supplement 2-6: a cancelled LOC also records the final-LOC values
    result["p3b"]["P3-2_loc"]["t_loc_final_s"] = 15.0
    result["p3b"]["checks"]["loc_revokes"] = 1
    items = judge.c11_items(tmp_path, result)
    assert items["final_loc_differs"] is True
    assert items["final_loc_period_crawler_max_N"] == 0.0
    assert items["final_loc_period_ge_0p01W"] is False


X16_IDS = {"R4368X_G1_B_top_Fs4_V0_gateon": "C9on", "R4368X_G1_B_top_Fs4_V0_gateoff": "C9off",
           "R4368X_rigidS1FL_B_top_Fs4_V0": "C10FLV0", "R4368X_rigidS1FL_B_top_Fs4_VB": "C10FLVB",
           "R4368X_rigidS1FR_B_top_Fs4_V0": "C10FRV0", "R4368X_rigidS1FR_B_top_Fs4_VB": "C10FRVB",
           "R4368X_J2_B_top_Fs0_L2_V0": "C11V0", "R4368X_J2_B_top_Fs0_L2_VB": "C11VB"}


def _x16_row_folder(out: Path, case: str, bundle: str, mask: int, *, commands: bytes) -> None:
    folder = out / bundle / case
    (folder / "record").mkdir(parents=True)
    t_s = np.round(np.arange(0.0, 120.0, 0.001), 6)
    crawler = np.where(t_s < 50.0, 50000.0, 0.0)
    force = np.full((t_s.size, 4), 20000.0)
    force[(t_s > 51.0) & (t_s <= 51.05), 2] = 9000.0
    np.savez(folder / "step_series.npz", t_s=t_s, scm_crawler_normal_N=crawler, F_cyl_N=force)
    (folder / "controller_commands.npz").write_bytes(commands)
    for name in ("r8_series.npz", "completion_series.npz", "record/record.npz",
                 "flow_series.npz"):
        (folder / name).write_bytes(b"x")
    (folder / "record" / "meta.json").write_text("{}", encoding="utf-8")
    result = {**_x16_result(mask), "args": {"duration": 120, "rigid_base": "FL"},
              "phases": [{"t_s": 1.0, "phase": "check"}, {"t_s": 70.0, "phase": "ready"}],
              "controller_meta": {"slope_clearance_margin": {"order_gate": {"decisions": []}}},
              "c2_soil": {"soil_mode_t_s": None, "t_loc_s": 50.2},
              "p3b": {"weight_N": 300000.0, "checks": {"P3-3_within": True, "loc_revokes": 0},
                      "P3-2_loc": {"t_loc_first_s": 50.2},
                      "P3-3_leg_force": {"F_min_after_N": [20000.0, 20000.0, 9000.0, 20000.0],
                                         "t_min_after_s": [60.0, 60.0, 51.01, 60.0],
                                         "F_min_transient_N": [1.0, 1.0, 1.0, 1.0]},
                      "P3-5_clearance_stroke": {"s_motor_max_m": [0.5, 0.5, 0.6, 0.6],
                                                "rut_clearance_end_m": 0.04}},
              "p3b_ext": {"pad_sinkage": {"end_mm": {"FL": 12.0}, "max_mm": {"FL": 13.0}}}}
    _write_json(folder / "result.json", result)


def test_x16_records_end_to_end(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(judge, "g6_gates",
                        lambda folder, result: {"G6-3": {"P3": "P3-3", "value": "fail"}})
    out = tmp_path / "OUT"
    rows = []
    for case, (bundle, cell, mask) in judge.X16_ROWS.items():
        row_id = X16_IDS[case]
        argv = ["level", "--case", case] + (["--flow-eta-v", "0.85"] if case.endswith("VB")
                                             else [])
        rows.append({"id": row_id, "case": case, "cell": cell, "mask": f"0x{mask:08X}",
                     "argv": argv})
        _x16_row_folder(out, case, bundle, mask, commands=b"same")
        _identity_files(out / "_identity", row_id, case=case)
        done = out / "_runners" / f"logs_{cell}" / f"{row_id}_run.done"
        done.parent.mkdir(parents=True, exist_ok=True)
        done.write_text("t exit=0 wall_s=1\n", encoding="utf-8")
    _write_json(out / "_tools" / "rows.json", {"rows": rows})
    code, report = _main(["x16-records", "--out-root", str(out)], tmp_path / "x16.json")
    assert code == 0, report["bundles"]
    assert {name: part["state"] for name, part in report["bundles"].items()} == {
        "C-9": "기록 완료", "C-10": "기록 완료", "C-11": "기록 완료"}
    assert report["bundles"]["C-9"]["controller_commands_same"] is True
    c10 = report["rows"]["R4368X_rigidS1FL_B_top_Fs4_VB"]["items"]
    assert c10["F_below_F_min_ms"][2] == 50.0 and c10["patch_leg_sinkage_end_mm"] == 12.0
    c11 = report["rows"]["R4368X_J2_B_top_Fs0_L2_V0"]["items"]
    assert c11["loc_period_crawler_max_N"] == 0.0 and c11["loc_period_ge_0p01W"] is False
    (out / "C-11" / "R4368X_J2_B_top_Fs0_L2_VB" / "flow_series.npz").unlink()
    code, report = _main(["x16-records", "--out-root", str(out)], tmp_path / "x16.json")
    assert code == 1 and report["bundles"]["C-11"]["state"] == "기록 불완전"
    # supplement 2-4: a second _run.done mark of a row leaves it 기록 불완전
    extra = out / "_runners" / "logs_extra" / "C10FLV0_run.done"
    extra.parent.mkdir(parents=True)
    extra.write_text("t exit=0\n", encoding="utf-8")
    _, report = _main(["x16-records", "--out-root", str(out)], tmp_path / "x16.json")
    assert report["bundles"]["C-10"]["state"] == "기록 불완전"
    assert any("rc:" in p for p in report["rows"]["R4368X_rigidS1FL_B_top_Fs4_V0"]["problems"])


# ---------------------------------------------------------------------- RD-13 / RD-5 / RD-1
def test_item_lists_are_fixed_bytes_per_bundle(tmp_path: Path) -> None:
    code, report = _main(["item-list", "--out-dir", str(tmp_path / "items")],
                         tmp_path / "items.json")
    assert code == 0
    expected = {*(f"H-{n}" for n in range(1, 13)), "C-9", "C-10", "C-11", "J_P"}
    assert set(report["lists"]) == expected
    for bundle, entry in report["lists"].items():
        data = (tmp_path / "items" / entry["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        assert data == judge.item_list_bytes(bundle)
        kinds = {item["구분"] for item in json.loads(data)["items"]}
        assert kinds <= {"등급 항목", "기록", "관문"}


def test_key_map_draft_names_the_identity_categories(tmp_path: Path) -> None:
    code, report = _main(["key-map"], tmp_path / "keys.json")
    categories = " ".join(row["category"] for row in report["rows"])
    assert code == 0 and "봉인 블록" in categories and "출력 위치" in categories


def test_head_check_is_s12_unless_head_is_m4(tmp_path: Path) -> None:
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    code, report = _main(["head-check", "--expect", head], tmp_path / "head.json")
    assert code == 0 and report["markers"] == []
    code, report = _main(["head-check", "--expect", "0" * 40], tmp_path / "head.json")
    assert code == 1 and report["markers"] == ["S-12 (HEAD is not M4)"]


def test_head_check_blobs_same_for_one_commit(tmp_path: Path) -> None:
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    code, report = _main(["head-check", "--expect", head, "--r4", head, "--files",
                          "04_scripts/04_hydraulic/coupled/judge4368_common.py"],
                         tmp_path / "head.json")
    assert report["blobs"][0]["same"] is True
    assert code == (0 if not report["src_params_changed"] else 1)
