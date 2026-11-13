"""436.8 rules rev11 (``v5_resume_4368_rules_rev11.md``, sealed 9bac4524) in the path 1 tools.

R11-7: the three seal lists carry rev11. R11-1: ``record-check`` expects the switches of the
line kind (H-0 by ``t3.bundle`` / ``t3.las`` / ``t3.gate``: R-0 off / off, R-0K off / on, T-3K
on / on, other lines the preset); R-0 / R-0K gate requests are recorded only; undecidable kind
inputs are S-3 (G-S: S-11). R11-2: T4h files are looked up in the runner convention folders
only; one other folder only without them; several hits or none = S-2. R11-3: ``dg3-hash --h7``
records the H-6 / H-7 same-hash count and the ③ split. Synthetic inputs only.
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parents[2]
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
CHRONO_SCRIPTS = ROOT / "04_scripts" / "02_chrono"
SCRIPTS = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "scripts"
for _path in (COUPLED, CHRONO_SCRIPTS, SCRIPTS, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import chrono_rows_judge_4368 as chrono_judge  # noqa: E402
import judge4368_common as common  # noqa: E402
import resume4368_judge as judge  # noqa: E402

REV11_NAME = "v5_resume_4368_rules_rev11.md"
REV11_SHA256 = "9bac452470faf74f921aa7474b3dabad781dac1ba6c3493aff998e69e430617f"
TAG_P3 = "final_C4G2_P3_LAS_K1"
TAG_V0 = "final_C4G2_LAS_K1"
T4H_NAME = "cand_current_L3_s1_g8_34_main_flat_top_4.0_FL_raised_200.0.npz"
"""The T4h file name H-6 and H-7 share in G-S ba2da55 (same key list, rev1 RV1-3.2)."""
DG3_KEY = "cand=current#L3|s1|g8|34|main|flat|top|4.0|FL|raised|200.0"
COMMANDS_SHA256 = "1b1ad1d074c0e5b79a5daaf279bcc4f9facc33b6123160ceed54360debabe259"


# ------------------------------------------------------------------------------ R11-7 seals
def test_every_path1_seal_list_has_rev11() -> None:
    assert (judge.RULES_REV11_NAME, judge.RULES_REV11_SHA256) == (REV11_NAME, REV11_SHA256)
    assert (REV11_NAME, REV11_SHA256) in judge.SEALED_REVISIONS
    assert (REV11_NAME, REV11_SHA256) in common.SEALED_RULES
    assert chrono_judge.RULES_SEALS[REV11_NAME] == REV11_SHA256


def test_stored_rev11_matches_its_seal() -> None:
    assert judge.sealed_rules_check()["problems"] == []
    assert common.seal_report()["problems"] == []
    assert chrono_judge.seal_check(common.RULES_DIR)["ok"] is True


def _copy_sealed_rules(target: Path) -> None:
    for name in [*chrono_judge.RULES_SEALS, *(n for n, _ in judge.SEALED_REVISIONS)]:
        source = common.RULES_DIR / name
        for path in (source, source.with_suffix(".sha256")):
            shutil.copy2(path, target / path.name)


def _seal_findings(folder: Path) -> tuple[bool, bool, bool]:
    """(resume4368_judge S-1, judge4368_common S-1, chrono seal not ok) for one rules folder."""
    return (judge.sealed_rules_check(folder)["stop_S1"], common.seal_report(folder)["stop_S1"],
            not chrono_judge.seal_check(folder)["ok"])


@pytest.mark.parametrize("missing", [REV11_NAME, REV11_NAME.replace(".md", ".sha256")])
def test_a_missing_rev11_file_is_s1(tmp_path: Path, missing: str) -> None:
    _copy_sealed_rules(tmp_path)
    assert _seal_findings(tmp_path) == (False, False, False)
    (tmp_path / missing).unlink()
    assert _seal_findings(tmp_path) == (True, True, True)


def test_a_changed_rev11_file_is_s1(tmp_path: Path) -> None:
    _copy_sealed_rules(tmp_path)
    rules = tmp_path / REV11_NAME
    rules.write_bytes(rules.read_bytes().replace(b"\n", b"\r\n"))  # sealed raw: CRLF differs
    assert _seal_findings(tmp_path) == (True, True, True)


# ------------------------------------------------------------------------ R11-1 line kinds
def _block(*, is_las_on: bool, is_gate_on: bool, request: str = "preset") -> dict:
    """A ``resume_k1`` block shaped like the G-S ba2da55 records."""
    return {
        "applicable": True,
        "k1_order_gate_request": request,
        "k1_order_gate_effective": is_gate_on,
        "liftoff_approach_slow": {"settings": {**judge.LAS_PRESET, "enable": is_las_on}},
        "slope_clearance_margin": {
            "settings": {"flat_soil_margin_order_gate": is_gate_on, "flat_soil_margin_m": 0.03},
            "order_gate": {"enabled": is_gate_on, "decisions": []},
        },
        "event_counts": {"flat_soil_margin_applied": 0, "flat_soil_margin_skipped_order": 0,
                         "soil_mode_start": 0},
    }


def _t3_line(bundle: str | None, las: str | None, gate: str | None, block: dict) -> dict:
    t3 = {"bundle": bundle, "line_key": "D1|H-S-0|G1|T|flat|K1|V0|e0", "kind": "d1",
          "las": las, "gate": gate, "rules": "rev5"}
    t3 = {key: value for key, value in t3.items() if value is not None}
    return {"job": {"d1": {"key": "D1|H-S-0|G1|T|flat|K1"}, "eps": 0.0, "setting": "V0"},
            "t3": t3, judge.RECORD_KEY: block}


R0_LINE = _t3_line("R-0", "off", "off", _block(is_las_on=False, is_gate_on=False))
"""The G-S ba2da55 ``t3k_r0_proxy/las_T3_R0.jsonl`` line (switches as recorded)."""


@pytest.mark.parametrize(
    ("bundle", "las", "gate", "kind", "is_las_on", "is_gate_on", "is_request_checked"),
    [
        ("R-0", "off", "off", "R-0", False, False, False),
        ("R-0K", "off", "on", "R-0K", False, True, False),
        ("T-3a", "on", "on", "T-3K", True, True, True),
        ("T-3b", "on", "on", "T-3K", True, True, True),
        ("T-3c", "on", "on", "T-3K", True, True, True),
    ],
)
def test_h0_line_kinds_follow_the_r11_1_table(bundle, las, gate, kind, is_las_on, is_gate_on,
                                              is_request_checked) -> None:
    line_kind = judge.harness_line_kind(_t3_line(bundle, las, gate, {}))
    assert (line_kind.name, line_kind.is_las_on, line_kind.is_gate_on,
            line_kind.is_request_checked, line_kind.defect) == (
        kind, is_las_on, is_gate_on, is_request_checked, None)


def test_a_line_without_t3_expects_the_preset() -> None:
    kind = judge.harness_line_kind({"job": {}})
    assert (kind.name, kind.is_las_on, kind.is_gate_on, kind.is_request_checked) == (
        "preset", True, True, True)


def test_the_gs_r0_line_has_no_problem_any_more() -> None:
    """G-S ba2da55: S-3 on this line before rev11 (gate / LAS-b expected on)."""
    assert judge.harness_record_problems(R0_LINE) == []


def test_r0_and_r0k_gate_requests_are_recorded_only() -> None:
    r0k = _t3_line("R-0K", "off", "on",
                   _block(is_las_on=False, is_gate_on=True, request="on"))
    assert judge.harness_record_problems(r0k) == []
    t3k = _t3_line("T-3a", "on", "on", _block(is_las_on=True, is_gate_on=True, request="on"))
    assert judge.harness_record_problems(t3k) == ["k1_order_gate_request 'on' != 'preset'"]


def test_las_b_off_lines_compare_only_enable() -> None:
    line = copy.deepcopy(R0_LINE)
    line[judge.RECORD_KEY]["liftoff_approach_slow"]["settings"]["max_s"] = 9.0
    assert judge.harness_record_problems(line) == []
    line[judge.RECORD_KEY]["liftoff_approach_slow"]["settings"]["enable"] = True
    assert judge.harness_record_problems(line) == ["LAS-b enable True != False"]


@pytest.mark.parametrize(
    ("is_las_on", "is_gate_on", "expected"),
    [
        (True, False, ["k1_order_gate_effective False != True",
                       "flat_soil_margin_order_gate False != True"]),
        (False, True, ["liftoff_approach_slow.settings.enable False != True"]),
    ],
)
def test_t3k_lines_need_both_switches_on(is_las_on, is_gate_on, expected) -> None:
    line = _t3_line("T-3b", "on", "on", _block(is_las_on=is_las_on, is_gate_on=is_gate_on))
    assert judge.harness_record_problems(line) == expected


def test_r0_line_with_the_gate_on_is_a_problem() -> None:
    line = _t3_line("R-0", "off", "off", _block(is_las_on=False, is_gate_on=True))
    assert judge.harness_record_problems(line) == [
        "k1_order_gate_effective True != False", "flat_soil_margin_order_gate True != False"]


def test_a_preset_line_keeps_the_original_4_2_expectations() -> None:
    line = {"job": {"case": "x"}, judge.RECORD_KEY: _block(is_las_on=False, is_gate_on=False)}
    assert judge.harness_record_problems(line) == [
        "k1_order_gate_effective False != True", "flat_soil_margin_order_gate False != True",
        "liftoff_approach_slow.settings.enable False != True"]


@pytest.mark.parametrize(
    ("bundle", "las", "gate", "fragment"),
    [
        ("R-0", None, "off", "t3.las missing"),
        ("R-0", "off", None, "t3.gate missing"),
        (None, "off", "off", "t3.bundle missing"),
        ("R-0", "off", "on", "of bundle 'R-0'"),  # R-0 with the R-0K pair
        ("R-0K", "on", "on", "of bundle 'R-0K'"),
        ("T-3a", "off", "on", "of bundle 'T-3a'"),
        ("T-9", "on", "on", "unknown t3.bundle"),
    ],
)
def test_undecidable_kind_inputs_are_one_problem(bundle, las, gate, fragment) -> None:
    line = _t3_line(bundle, las, gate, _block(is_las_on=False, is_gate_on=False))
    kind = judge.harness_line_kind(line)
    assert kind.name is None and fragment in kind.defect
    assert judge.harness_record_problems(line) == [kind.defect]


def test_a_t3_value_that_is_not_a_dict_is_a_defect() -> None:
    line = {"job": {}, "t3": "R-0", judge.RECORD_KEY: _block(is_las_on=True, is_gate_on=True)}
    assert judge.harness_line_kind(line).defect is not None


def _run_cli(argv: list[str], monkeypatch) -> tuple[int, dict | None]:
    monkeypatch.setattr(judge, "sealed_rules_check", lambda: {"problems": [], "stop_S1": False})
    code = judge.main(argv)
    out = Path(argv[argv.index("--out") + 1])
    return code, (json.loads(out.read_text(encoding="utf-8")) if out.is_file() else None)


def _write_jsonl(path: Path, lines: list[dict]) -> Path:
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


def test_record_check_passes_the_gs_r0_proxy_file(tmp_path: Path, monkeypatch) -> None:
    header = {"header": {"bundles": ["R-0"]}}
    jsonl = _write_jsonl(tmp_path / "las_T3_R0.jsonl", [header, R0_LINE])
    code, report = _run_cli(["record-check", "--harness", str(jsonl), "--out",
                             str(tmp_path / "rc.json")], monkeypatch)
    assert code == 0 and report["stop_S3"] is False and report["stop_S11"] is False
    assert report["harness_line_kinds_R11_1"] == {"R-0": 1}
    assert report["kind_input_defects_R11_1"] == 0


@pytest.mark.parametrize(("extra", "stop_s3", "stop_s11"), [([], True, False),
                                                             (["--gs"], False, True)])
def test_kind_defects_are_s3_in_a_main_run_and_s11_in_gs(tmp_path: Path, monkeypatch, extra,
                                                         stop_s3, stop_s11) -> None:
    broken = _t3_line("R-0", "off", None, _block(is_las_on=False, is_gate_on=False))
    jsonl = _write_jsonl(tmp_path / "las_T3_R0.jsonl", [R0_LINE, broken])
    code, report = _run_cli(["record-check", "--harness", str(jsonl), *extra, "--out",
                             str(tmp_path / "rc.json")], monkeypatch)
    assert code == 1 and report["kind_input_defects_R11_1"] == 1
    assert (report["stop_S3"], report["stop_S11"]) == (stop_s3, stop_s11)
    assert report["mode"] == ("G-S" if extra else "main")


def test_gs_mode_keeps_other_problems_as_s3(tmp_path: Path, monkeypatch) -> None:
    wrong = _t3_line("R-0", "off", "off", _block(is_las_on=True, is_gate_on=False))
    jsonl = _write_jsonl(tmp_path / "las_T3_R0.jsonl", [wrong])
    code, report = _run_cli(["record-check", "--harness", str(jsonl), "--gs", "--out",
                             str(tmp_path / "rc.json")], monkeypatch)
    assert code == 1 and (report["stop_S3"], report["stop_S11"]) == (True, False)


def test_r0_request_is_reported_as_recorded(tmp_path: Path, monkeypatch) -> None:
    jsonl = _write_jsonl(tmp_path / "las_T3_R0.jsonl", [R0_LINE])
    _, report = _run_cli(["record-check", "--harness", str(jsonl), "--all", "--out",
                          str(tmp_path / "rc.json")], monkeypatch)
    assert report["harness"][0]["gate_request_recorded"] == "preset"


# --------------------------------------------------------------------------- R11-2 T4h lookup
def _r79(top_tag: str, t4h_file: str | None = T4H_NAME, *, is_extend_start: bool) -> dict:
    options = {"m2_law": "flow_limited_r5"}
    if is_extend_start:
        options["extend_start_tracked"] = True
    return {"key": DG3_KEY, "seed_index": 0, "harness": "g8", "inner": 0,
            "controller_tag": top_tag, "t4h_file": t4h_file,
            "commands_sha256": COMMANDS_SHA256, "hydraulic_options": options,
            "controller_settings": {"two_pressure.extend_start_rule":
                                    "tracked_bound" if is_extend_start else "constant"}}


def _write_t4h(folder: Path, name: str, tag: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    np.savez(folder / name, t_s=np.zeros(2),
             meta_json=np.array(json.dumps({"controller_tag": tag})))


def _write_result(path: Path, results: list[dict]) -> Path:
    path.write_text(json.dumps({"meta": {}, "results": results}), encoding="utf-8")
    return path


@pytest.fixture()
def dg3_pair(tmp_path: Path) -> tuple[Path, Path]:
    """G-S ba2da55 layout: H-6 and H-7 results, each with a ``<stem>_t4h/`` folder holding a T4h
    file of the same name (H-6 tag ③ on, H-7 tag ③ off)."""
    _write_t4h(tmp_path / "h6_dg3_v4on_t4h", T4H_NAME, TAG_P3)
    _write_t4h(tmp_path / "h7_dg3_off_t4h", T4H_NAME, TAG_V0)
    h6 = _write_result(tmp_path / "h6_dg3_v4on.json", [_r79(TAG_P3, is_extend_start=True)])
    h7 = _write_result(tmp_path / "h7_dg3_off.json", [_r79(TAG_V0, is_extend_start=False)])
    return h6, h7


def test_h7_takes_its_own_convention_folder(dg3_pair) -> None:
    """The G-S ba2da55 h7 false S-2: with the T4h folders passed as ``--t4h-dir`` the H-7 line
    picked the H-6 file of the same name first. Without ``--t4h-dir`` each result reads its own
    ``<stem>_t4h/``."""
    check = judge.r79_tag_check(list(dg3_pair))
    assert (check["compared"], check["mismatched"], check["stop_S2"]) == (2, 0, False)
    h6, h7 = dg3_pair
    assert check["t4h_folders_searched_R11_2"] == {
        str(h6): [str(h6.with_name("h6_dg3_v4on_t4h"))],
        str(h7): [str(h7.with_name("h7_dg3_off_t4h"))]}


def test_the_ba2da55_t4h_dir_list_is_an_input_error(dg3_pair, monkeypatch, tmp_path) -> None:
    """The G-S ba2da55 command passed every T4h folder (8): now exit 2 (S-11), no judgement."""
    h6, h7 = dg3_pair
    folders = [str(h6.with_name("h6_dg3_v4on_t4h")), str(h7.with_name("h7_dg3_off_t4h"))]
    with pytest.raises(judge.InputError, match="at most one"):
        judge.r79_tag_check([h6, h7], [Path(f) for f in folders])
    for command in ("record-check", "gs"):
        argv = [command, "--harness", str(h6), str(h7)]
        for folder in folders:
            argv += ["--t4h-dir", folder]
        code, report = _run_cli([*argv, "--out", str(tmp_path / f"{command}.json")], monkeypatch)
        assert (code, report) == (2, None)


def test_one_folder_next_to_a_convention_folder_is_an_input_error(dg3_pair) -> None:
    h6, h7 = dg3_pair
    with pytest.raises(judge.InputError, match="convention folder"):
        judge.r79_tag_check([h7], [h6.with_name("h6_dg3_v4on_t4h")])


def test_one_folder_is_used_without_a_convention_folder(tmp_path: Path) -> None:
    _write_t4h(tmp_path / "elsewhere", T4H_NAME, TAG_V0)
    result = _write_result(tmp_path / "h7.json", [_r79(TAG_V0, is_extend_start=False)])
    check = judge.r79_tag_check([result], [tmp_path / "elsewhere"])
    assert (check["mismatched"], check["stop_S2"]) == (0, False)


def test_a_folder_given_for_a_file_without_t4h_records_is_not_an_error(tmp_path: Path) -> None:
    (tmp_path / "t4h").mkdir()
    result = _write_result(tmp_path / "seedext.json", [_r79(TAG_V0, None, is_extend_start=False)])
    check = judge.r79_tag_check([result], [tmp_path / "elsewhere"])
    assert check["by_method"] == {"t4h_meta": 0, "recompute": 1}


def test_the_same_name_in_both_convention_folders_is_s2(tmp_path: Path) -> None:
    _write_t4h(tmp_path / "h7_t4h", T4H_NAME, TAG_V0)
    _write_t4h(tmp_path / "t4h", T4H_NAME, TAG_V0)
    result = _write_result(tmp_path / "h7.json", [_r79(TAG_V0, is_extend_start=False)])
    check = judge.r79_tag_check([result])
    assert check["stop_S2"] is True and "found 2 times" in check["rows"][0]["reason"]


def test_no_file_in_the_search_is_s2(tmp_path: Path) -> None:
    (tmp_path / "h7_t4h").mkdir()
    result = _write_result(tmp_path / "h7.json", [_r79(TAG_V0, is_extend_start=False)])
    check = judge.r79_tag_check([result])
    assert check["stop_S2"] is True and "not found" in check["rows"][0]["reason"]


# ------------------------------------------------------------------- R11-3 H-6 / H-7 hashes
def test_dg3_hash_records_the_h6_h7_same_hash_count_and_split(dg3_pair, monkeypatch,
                                                              tmp_path) -> None:
    h6, h7 = dg3_pair
    code, report = _run_cli(["dg3-hash", "--h6", str(h6), "--h7", str(h7), "--out",
                             str(tmp_path / "dg3.json")], monkeypatch)
    block = report["h6_vs_h7"]
    assert code == 0 and report["record_state"] == "기록"
    assert (block["keys"], block["same_hash_count_R11_3"]) == (1, 1)
    assert block["extend_start_split_R11_3"] == {"keys": 1, "split": 1, "not_split": []}


def test_an_h7_line_with_the_extend_start_rule_is_not_split(tmp_path: Path) -> None:
    h6 = _write_result(tmp_path / "h6.json", [_r79(TAG_P3, is_extend_start=True)])
    h7 = _write_result(tmp_path / "h7.json", [_r79(TAG_V0, is_extend_start=True)])
    block = judge.h6_vs_h7(h6, h7)
    assert block["extend_start_split_R11_3"]["not_split"] == [DG3_KEY.split("#", 1)[1]]


# -------------------------------------------------------------------- R11-5 G-S row grades
def test_chrono_judge_counts_the_grades_for_the_record_only() -> None:
    rows = [{"grade": "fail"}, {"grade": None}, {"grade": "pass"}, {"grade": "fail"}]
    block = chrono_judge.grade_counts(rows)
    assert block["counts"] == {"None": 1, "fail": 2, "pass": 1} and block["rows"] == 4
    assert "R11-5" in block["note"]


# --------------------------------------------------------------- R11-4 commit identity (S-12)
HEAD = "ba2da55efac55b37a2f5493ae403ede772f583c6"
OTHER = "4312b8ec604bc9c755805c754ed19183a5c071ec"


def _meta(git: dict | None = None, **extra) -> dict:
    meta = {"case": "row", **extra}
    if git is not None:
        meta["code_at_launch"] = {"files": {}, "git": git}
    return meta


def _git(head: str = HEAD, dirty: list[str] | None = None) -> dict:
    dirty = dirty or []
    return {"head": head, "paths": ["03_src"], "dirty": dirty, "clean": not dirty,
            "taken_utc": "2026-11-13T05:00:00+00:00"}


def _row(engine: str, result: dict | None = None) -> dict:
    return {"engine": engine, "name": "row", "result": result or {}}


def _level_result(git: dict | None) -> dict:
    return {"code_state": {"files_at_start": {}, "git_at_start": git}}


@pytest.mark.parametrize("engine", ["SCM", "L2b", "L1R", "openloop"])
def test_the_same_commit_matches(engine) -> None:
    result = _level_result(_git()) if engine in ("SCM", "openloop") else {}
    identity = chrono_judge.commit_identity(_meta(_git()), _row(engine, result), "ba2da55")
    assert identity["status"] == "match" and identity["problems"] == []


@pytest.mark.parametrize(
    ("meta", "fragment"),
    [
        (_meta(), "code_at_launch missing"),  # the G-S ba2da55 open-loop row
        (_meta({"error": "CalledProcessError: git"}), "git.error"),
        (_meta(_git(OTHER)), "is not git_at_start"),
        (_meta({"paths": []}), "git.head missing"),
    ],
)
def test_batch_records_that_do_not_show_the_commit_are_s12(meta, fragment) -> None:
    identity = chrono_judge.commit_identity(meta, _row("openloop"), "ba2da55")
    assert identity["status"] == "S-12" and fragment in identity["problems"][0]


def test_l2b_rows_without_a_result_record_are_not_stopped() -> None:
    identity = chrono_judge.commit_identity(_meta(_git()), _row("L2b"), "ba2da55")
    assert (identity["status"], identity["result_head"]) == ("match", "no_result_record")


@pytest.mark.parametrize("git", [_git(OTHER), {"error": "TimeoutExpired: git"}])
def test_a_level_result_record_of_another_commit_is_s12(git) -> None:
    row = _row("SCM", _level_result(git))
    identity = chrono_judge.commit_identity(_meta(_git()), row, "ba2da55")
    assert identity["status"] == "S-12" and "result.json" in identity["problems"][0]


def test_a_failed_code_state_record_is_s12_on_a_level_row() -> None:
    row = _row("SCM", {"code_state": {"error": "OSError: x"}})
    assert chrono_judge.commit_identity(_meta(_git()), row, "ba2da55")["status"] == "S-12"


def test_an_open_loop_result_head_is_recorded_only() -> None:
    row = _row("openloop", _level_result(_git(OTHER)))
    identity = chrono_judge.commit_identity(_meta(_git()), row, "ba2da55")
    assert identity["status"] == "match"
    assert "is not git_at_start" in identity["result_problem_recorded"]


def test_a_dirty_tree_is_recorded_only() -> None:
    identity = chrono_judge.commit_identity(_meta(_git(dirty=[" M 03_src/x.py"])), _row("L1R"),
                                            "ba2da55")
    assert identity["status"] == "match" and identity["dirty"] == [" M 03_src/x.py"]


def test_row_inputs_without_a_batch_entry_are_recorded() -> None:
    identity = chrono_judge.commit_identity(None, _row("SCM", _level_result(_git())), "ba2da55")
    assert (identity["status"], identity["batch_head"]) == ("no_batch_entry", None)


@pytest.mark.parametrize("value", ["ba2da5", "BA2DA55", "ba2da55x", HEAD + "0"])
def test_a_malformed_git_at_start_is_an_input_error(value) -> None:
    with pytest.raises(chrono_judge.InputError, match="R11-4"):
        chrono_judge.parse_git_at_start(value)


def test_judge_needs_git_at_start(tmp_path: Path, capsys) -> None:
    code = chrono_judge.main(["judge", "--out", str(tmp_path / "o.json"), "--row", str(tmp_path)])
    assert code == 2 and json.loads(capsys.readouterr().out.strip().splitlines()[-1])["exit"] == 2


GS_BA2DA55 = (Path(r"C:\workspace\outrigger_control\07_results\S9")
              / "batch_V5-RESUME-K1-GS_20261113_130358")


@pytest.mark.skipif(not (GS_BA2DA55 / "batch.json").is_file(),
                    reason="G-S ba2da55 batch not present")
def test_the_gs_ba2da55_batch_stops_only_on_the_open_loop_row(tmp_path: Path) -> None:
    """Recorded before the runner change: the open-loop row has no code_at_launch (S-12); the 11
    other rows carry ba2da55."""
    out = tmp_path / "gs.json"
    chrono_judge.main(["judge", "--git-at-start", "ba2da55", "--out", str(out),
                       "--batch", str(GS_BA2DA55),
                       "--results-root", str(GS_BA2DA55.parents[1])])
    block = json.loads(out.read_text(encoding="utf-8"))["commit_identity_R11_4"]
    assert block["s12_rows"] == ["GS_P3a_G1_B_VB_prop_lift10"]
    assert block["counts"] == {"S-12": 1, "match": 11} and block["dirty_rows_recorded"] == []
