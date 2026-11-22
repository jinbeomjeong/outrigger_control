"""436.9 J-P3 edition 5 erratum 6 6-6 input form (``jp3_remedy_spec_v5_erratum6.md`` line 112;
pre-merge audit of ``ed5-fix3`` S-1): the judge paths that pair with stored files, run end to
end through ``main`` on stored lines copied into the edition 5 form - only the setting name,
the tag and the ③ identity changed (VBG5 -> VBG6, revision 5 -> 6 with the sealed edition 5
identity, ``_P3H`` -> ``_P3W``), plus the record keys edition 5 writes where a stored line
predates them (P4 evidence, seed log, lock window record).

Inputs: the stored baseline ``221456d``, the stored H-6 / h10 files and their fixed T4h lists,
and the edition 4a run ``78fd5d2d`` outputs (allowed: no edition 5 judgement value is read).
No edition 5 run output and no ``j9_runs/**/judge`` file is used. Each test asserts one exact
exit code and every problem class.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import jp3_baseline_compare as compare  # noqa: E402
import jp3_case_judge as case_judge  # noqa: E402
import jp3_p51_compare as p51  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
from j_p3_inputs import P3_RULE, REVISION_KEY, RULE_KEY  # noqa: E402

DATA_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT") or ROOT)
CAUSE = DATA_ROOT / "06_analysis" / "02_control" / "j_p3_cause"
RESUME_K1 = DATA_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "resume_k1"
BASELINE = CAUSE / "baseline_221456d"
RUN_4A = CAUSE / "j9_runs" / "78fd5d2d"
H6 = RESUME_K1 / "h6_dg3_v4on.json"
GRID = RESUME_K1 / "h9_grid" / "grid_r67_top.json"
T4H_SUMS = (CAUSE / "prelaunch_j9" / "h10_reuse_rerun_t4h.SHA256SUMS",
            CAUSE / "prelaunch_j9" / "h6_dg3_v4on_t4h.SHA256SUMS")
REV6_IDENTITY = compare.IDENTITY_OF_REVISION[6]
SEED_COLUMNS = ["net_force_seed_step_N", "m2_shift_clipped"]
pytestmark = pytest.mark.skipif(
    not all(path.exists() for path in (BASELINE, RUN_4A, H6, GRID, *T4H_SUMS)),
    reason="stored baseline / H-6 / 78fd5d2d outputs not present")


@pytest.fixture
def elsewhere(tmp_path, monkeypatch) -> Path:
    folder = tmp_path / "elsewhere"
    folder.mkdir()
    monkeypatch.chdir(folder)
    return folder


def _read_rows(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(document, dict):  # a run file, or a JSON lines file of one row
        return document["results"] if "results" in document else [document]
    return document


def _write_rows(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _write_json(path: Path, document) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _check(row: dict) -> dict:
    return (row.get("hydraulics_record") or {}).get("extend_bound_check") or {}


def edition5(row: dict) -> dict:
    """A stored line in the edition 5 form: VBG5 -> VBG6 (setting and ``v5_setting``), a
    revision 5 ③ record -> revision 6 with the sealed edition 5 identity (the X11 arm stays
    revision 5, erratum 1 1), the tag ``_P3H`` -> ``_P3W``."""
    new = copy.deepcopy(row)
    job = new.get("job") or {}
    if job.get("setting") == "VBG5":
        job["setting"] = "VBG6"
    if new.get("v5_setting") == "VBG5":
        new["v5_setting"] = "VBG6"
    setting = job.get("setting") or new.get("v5_setting")
    check = _check(new)
    if check.get("rule_revision") == 5 and not str(setting).endswith("_X11"):
        check.update(REV6_IDENTITY, rule_revision=6)
    if new.get(REVISION_KEY) == 5 and not str(setting).endswith("_X11"):
        new[REVISION_KEY] = 6
    tag = new.get("controller_tag")
    if isinstance(tag, str) and "_P3H" in tag:
        new["controller_tag"] = tag.replace("_P3H", "_P3W")
    return new


def _classes(report: dict) -> dict:
    return {kind: report.get(kind) for kind in ("failures", "setting_defects", "not_judgeable")}


# --- case-f / x11 (jp3_case_judge) on the stored 78fd5d2d rows -----------------------------------

def test_case_f_on_the_stored_rows_in_the_edition5_form(tmp_path, elsewhere) -> None:
    rows = [edition5(row) for row in _read_rows(RUN_4A / "casef_a1" / "j9_case_f.jsonl")]
    assert {_check(row).get("rule_revision") for row in rows} <= {6, None}
    rows_file = _write_rows(tmp_path / "run" / "j9_case_f.jsonl", rows)
    out = tmp_path / "case_f.json"
    code = case_judge.main(["case-f", "--rows", str(rows_file), "--grid", str(GRID),
                            "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == compare.EXIT_PASS and report["status"] == "pass", _classes(report)
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}


def test_x11_on_the_baseline_lsj4_and_the_stored_x11_row(tmp_path, elsewhere) -> None:
    source = RUN_4A / "cases_a1" / "lsj4_x11.jsonl"
    rows = [edition5(row) for row in _read_rows(source)]
    assert [_check(row).get("rule_revision") for row in rows] == [case_judge.X11_REVISION]
    both = _write_rows(tmp_path / "run" / "lsj4_x11.jsonl", rows)
    shutil.copytree(RUN_4A / "cases_a1" / "lsj4_x11_t4h", tmp_path / "run" / "lsj4_x11_t4h")
    out = tmp_path / "x11.json"
    code = case_judge.main(["x11", "--both", str(both), "--baseline", str(BASELINE),
                            "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == compare.EXIT_PASS and report["status"] == "pass", _classes(report)
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}


# --- P5-1 (jp3_p51_compare): the 78fd5d2d rows against their edition 5 copies --------------------

def _p51(tmp_path: Path, name: str, change=None) -> tuple[int, dict]:
    old = RUN_4A / "cases_a1" / name
    rows = [edition5(row) for row in _read_rows(old)]
    if change is not None:
        change(rows)
    new = _write_rows(tmp_path / "run" / name, rows)
    out = tmp_path / f"p51_{Path(name).stem}.json"
    code = p51.main(["--old", str(old), "--new", str(new), "--out", str(out)])
    return code, json.loads(out.read_text(encoding="utf-8"))


@pytest.mark.parametrize("name, settings", [
    ("j9_cases.jsonl", 15), ("cd.jsonl", 2)])
def test_p51_on_the_stored_rows_and_their_edition5_copies(tmp_path, elsewhere, name,
                                                          settings) -> None:
    """P5-1 pairs every 78fd5d2d row with its edition 5 copy (cd: VBG5 with VBG6): equal hashes
    pass (exit 0) with no problem."""
    code, report = _p51(tmp_path / "a", name)
    assert code == p51.EXIT_PASS and report["status"] == "pass", report.get("problems")
    assert report["problems"] == [] and report["pairs"] == settings


def test_p51_changed_hash_of_an_always_judged_row_stops(tmp_path, elsewhere) -> None:
    """VB (③ revision 4, :data:`ALWAYS_EQUAL_SETTINGS`) is judged whatever the fallbacks: its
    copy with another hash stops P5-1 (exit 1), no other problem."""
    def change(rows: list[dict]) -> None:
        next(row for row in rows if row["job"]["setting"] == "VB")["commands_sha256"] = "f" * 64

    code, report = _p51(tmp_path, "j9_cases.jsonl", change)
    assert code == p51.EXIT_DIFFER and report["status"] == "differ"
    assert report["differing_pairs"] == 1 and report["problems"] == []


# --- t8 T-JR-10 / 11 (jp3_tjr_judge) on the stored h10 lines -------------------------------------

H10 = RESUME_K1 / "h10_reuse_rerun.jsonl"
MAIN_JSONL = DATA_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "main.jsonl"


def _t8(tmp_path: Path, change=None) -> tuple[int, dict]:
    """``t8`` with the stored h10 file and ``main.jsonl`` (the fixed files) against the
    78fd5d2d ``j9_t8`` rows in the edition 5 form (their T4h copied next to them)."""
    rows = [edition5(row) for row in _read_rows(RUN_4A / "t8_a1" / "j9_t8.jsonl")]
    if change is not None:
        change(rows)
    run = tmp_path / "run"
    rerun = _write_rows(run / "j9_t8.jsonl", rows)
    shutil.copytree(RUN_4A / "t8_a1" / "j9_t8_t4h", run / "j9_t8_t4h")
    out = tmp_path / "t8.json"
    code = tjr.main(["t8", "--stored", str(H10), "--rerun", str(rerun), "--main-jsonl",
                     str(MAIN_JSONL), "--out", str(out)])
    return code, json.loads(out.read_text(encoding="utf-8"))


@pytest.mark.skipif(not (H10.is_file() and MAIN_JSONL.is_file()), reason="stored h10 not present")
def test_t8_on_the_stored_h10_lines(tmp_path, elsewhere) -> None:
    """T-JR-10 (VBH against the stored h10 VB lines) and T-JR-11 (VBJ against VBJ0) on the
    edition 5 form of the 78fd5d2d rerun (VBH / VBJ ③ revision 6)."""
    code, report = _t8(tmp_path / "a")
    assert code == compare.EXIT_PASS and report["status"] == "pass", _classes(report)
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    assert report["T-JR-10"]["status"] == report["T-JR-11"]["status"] == compare.STATUS_PASS

    def change(rows: list[dict]) -> None:
        next(row for row in rows if row["job"]["setting"] == "VBJ")["commands_sha256"] = "f" * 64

    code, report = _t8(tmp_path / "b", change)
    assert code == compare.EXIT_FAILED and report["status"] == "failed"
    assert report["T-JR-11"]["status"] == compare.STATUS_FAILED
    assert report["T-JR-10"]["status"] == compare.STATUS_PASS
    assert report["failures"] == ["T-JR-11: 1/22 command hashes differ"]
    assert report["setting_defects"] == [] and report["not_judgeable"] == []


# --- t12 VBH / VBJ (jp3_tjr_judge, T-JR-12a) on the stored H-6 and the 78fd5d2d VBJ0 lines -------

@pytest.fixture
def pass_grades(monkeypatch):
    """Every graded line passes (the r79 grading is not this test's subject; the judge file
    only has to name every line, 4a-8 5)."""
    import h8_noise_judge_4368 as h8

    monkeypatch.setattr(h8, "grade_lines", lambda results, judge: {
        h8.plain_key(run["key"]): {"grade": h8.GRADE_PASS, "level": run["level"]}
        for run in results if "error" not in run})


def _judge_file(path: Path, document: dict) -> tuple[Path, str]:
    """A synthetic r79 judge file naming every line of ``document`` (no stored judge read)."""
    judge = {"runs": [{"key": line["key"]} for line in document["results"]],
             "unmatched": [], "errors": []}
    written = _write_json(path, judge)
    return written, compare.file_sha256(written)


def _t12(tmp_path: Path, bundle: str, base: Path, new_document: dict) -> tuple[int, dict]:
    run = tmp_path / "run"
    new = _write_json(run / f"dg3_{bundle}.json", new_document)
    base_document = json.loads(base.read_text(encoding="utf-8"))
    base_judge, base_sha = _judge_file(run / "base_judge.json", base_document)
    new_judge, new_sha = _judge_file(run / "new_judge.json", new_document)
    out = tmp_path / f"t12_{bundle}.json"
    code = tjr.main(["t12", "--bundle", bundle, "--base", str(base), "--base-judge",
                     str(base_judge), "--base-judge-sha256", base_sha, "--new", str(new),
                     "--new-judge", str(new_judge), "--new-judge-sha256", new_sha,
                     "--out", str(out)])
    return code, json.loads(out.read_text(encoding="utf-8"))


def test_t12_vbh_on_the_stored_h6(tmp_path, elsewhere, pass_grades) -> None:
    """T-JR-12a VBH: the stored H-6 as base, its VBH copy (edition 5 form) as new."""
    code, report = _t12(tmp_path, "VBH", H6, _h6_document("VBH"))
    assert code == compare.EXIT_PASS and report["status"] == "pass", _classes(report)
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}


def _vbj_from_vbj0(document: dict) -> dict:
    """The 78fd5d2d VBJ0 lines (③ off) as VBJ lines: ``v5_setting`` VBJ and a revision 6 ③
    record of the sealed identity with zero J-P3 judged keys (the L2 line judged)."""
    out = copy.deepcopy(document)
    for line in out["results"]:
        line["v5_setting"] = "VBJ"
        line[RULE_KEY], line[REVISION_KEY] = P3_RULE, 6  # the ③ run keys of a rev 6 line
        record = line.setdefault("hydraulics_record", {})
        record["extend_bound_check"] = {
            **(record.get("extend_bound_check") or {}), **REV6_IDENTITY, "rule_revision": 6,
            **{key: [0, 0, 0, 0] for key in compare.JUDGED_KEYS},
            # the r79 output form: the L2 line normal grade (judged), L3 conservative (record)
            "sensor_grade": "normal" if line.get("level") == tjr.JUDGED_LEVEL else "conservative",
            "jp3_judged_row": line.get("level") == tjr.JUDGED_LEVEL}
    return out


def test_t12_vbj_on_the_stored_vbj0_lines(tmp_path, elsewhere, pass_grades) -> None:
    """T-JR-12a VBJ: the 78fd5d2d VBJ0 lines as base, their VBJ copy as new."""
    base = RUN_4A / "dg3_a1" / "dg3_VBJ0.json"
    new_document = _vbj_from_vbj0(json.loads(base.read_text(encoding="utf-8")))
    code, report = _t12(tmp_path, "VBJ", base, new_document)
    assert code == compare.EXIT_PASS and report["status"] == "pass", _classes(report)
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    assert report["jp3_outcome"] == "pass"


# --- records T-JR-13 .. 15 (jp3_tjr_judge) on the stored T4h lists and H-6 keys ------------------

def _sums_names(path: Path) -> list[str]:
    return sorted(line.split(maxsplit=1)[1].lstrip("*")
                  for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _replay_report(sums: Path) -> dict:
    names = _sums_names(sums)
    return {"runs": len(names), "runs_over": 0, "extend_start_revision": tjr.REPLAY_REVISION,
            "rows": [{"file": name} for name in names], "J-P3": {"status": "pass"}}


def _with_seed_and_relock(line: dict) -> dict:
    record = line.setdefault("hydraulics_record", {})
    record.setdefault("p1_retract_seed_log_columns", ["t_s", "leg", *SEED_COLUMNS])
    record.setdefault("p1_retract_seed_log", [[1.0, 2, 0.0, False]])
    record["p1_retract_seed_count"] = len(record["p1_retract_seed_log"])
    record.setdefault("relock_step_over_1bar_count", 0)
    return line


def _h6_document(setting: str) -> dict:
    """The stored H-6 lines as a T-JR-12a output of ``setting`` (edition 5 form): the
    ``v5_setting``, a revision 6 ③ record of the sealed identity, and what an edition 5 r79
    output carries beside (meta ``keys_file`` = the stored H-6, the P4 evidence of a P4-off
    run - truth 0, monitor reads > 0 -, the lock window record)."""
    document = json.loads(H6.read_text(encoding="utf-8"))
    for line in document["results"]:
        line["v5_setting"] = setting
        line.setdefault("lock_window_alignment", {}).setdefault("n_late_fallback", 0)
        record = line.setdefault("hydraulics_record", {})
        record["extend_bound_check"] = {**(record.get("extend_bound_check") or {}),
                                        **REV6_IDENTITY, "rule_revision": 6}
        record.setdefault("rod_reading_truth_calls", 0)
        record.setdefault("two_pressure_reads", 9)
    meta = dict(document.get("meta") or {})
    meta["keys_file"] = {"sha256": compare.file_sha256(H6), "n_keys": len(document["results"])}
    return {**document, "meta": meta,
            "results": [edition5(line) for line in document["results"]]}


def test_records_on_the_stored_t4h_lists_and_h6_keys(tmp_path, elsewhere) -> None:
    """T-JR-13 against the fixed T4h lists (426 / 135 names), T-JR-14 / 15 on the stored H-6
    keys: VBH / VBJ copies of the stored H-6 lines and the five 78fd5d2d case E rows."""
    run = tmp_path / "run"
    replays = [_write_json(run / f"t4h_replay_{index}.json", _replay_report(sums))
               for index, sums in enumerate(T4H_SUMS)]
    vbh = _write_json(run / "dg3_VBH.json", _h6_document("VBH"))
    vbj_document = _h6_document("VBJ")
    vbj_document["results"] = [_with_seed_and_relock(line) for line in vbj_document["results"]]
    vbj = _write_json(run / "dg3_VBJ.json", vbj_document)
    case_rows = [_with_seed_and_relock(edition5(row))
                 for row in _read_rows(RUN_4A / "cases_a1" / "j9_cases.jsonl")
                 if row["job"]["setting"] in tjr.T_JR_15_JUDGED_SETTINGS]
    cases = _write_rows(run / "j9_cases.jsonl", case_rows)
    out = tmp_path / "records.json"
    code = tjr.main(["records", "--replay", *map(str, replays), "--t4h-sums",
                     *map(str, T4H_SUMS), "--dg3", str(vbh), str(vbj), "--h6", str(H6),
                     "--lock-rows", str(vbj), str(cases), "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == compare.EXIT_PASS and report["status"] == "pass", _classes(report)
    assert _classes(report) == {"failures": [], "setting_defects": [], "not_judgeable": []}
    assert [row["runs"] for row in report["T-JR-13"]] == [426, 135]
    assert report["T-JR-15"]["judged_rows"] == 5 + 135
