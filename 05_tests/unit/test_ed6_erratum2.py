"""436.9 edition 6 erratum 2 (``jp3_remedy_spec_v6_erratum2.md``): the step 5 judge
sub-commands of ``jp3_ed6_judge.py`` (``hash-match``, ``d0-1``, ``t8``, ``cases``; Y-14), the
``run_v5`` batches ``ed6_t8`` / ``ed6_cases``, the edition 6 judged marker
``judged:t12_VBL_jp3`` and the L1a ``l1-hash-record`` (2-4), and the run step stop on a
placeholder left in the run configuration (2-4, exit 3).

Synthetic rows only (no simulation); every ``main`` runs with the working folder elsewhere
(tool rule (가)). The PowerShell checks need pwsh (PowerShell 7); a missing pwsh fails.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import j_p3_inputs  # noqa: E402
import jp3_ed6_judge as ed6  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
import judge4368_common as common  # noqa: E402
import run_v5  # noqa: E402

STEPS = ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "prelaunch_j9" / "run_steps_ed6"
HASH_A = "a" * 64
HASH_B = "b" * 64
T8_CASES = 22


@pytest.fixture(autouse=True)
def _elsewhere(tmp_path, monkeypatch) -> None:
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")


def _write_rows(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _line(job: dict, digest: str = HASH_A, events: list | None = None) -> dict:
    return {"job": job, "commands_sha256": digest, "event_names": [],
            "events": events if events is not None else []}


def _run(tmp_path: Path, *argv: str) -> tuple[int, dict]:
    out = tmp_path / f"report_{len(list(tmp_path.glob('report_*.json')))}.json"
    code = ed6.main([*argv, "--out", str(out)])
    return code, json.loads(out.read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------- hash-match
REFERENCE_JOBS = [{"case": "R12", "eps": 0.0, "offset_s": 0.0, "setting": setting}
                  for setting in ("VB", "LS1", "LS2")]


@pytest.mark.parametrize(("change", "code", "status"), [
    (None, 0, "pass"),
    ("differ", 1, "failed"),
    ("missing", 2, "not_judgeable"),
    ("extra", 2, "not_judgeable"),
    ("error", 2, "not_judgeable"),
    ("short_hash", 2, "not_judgeable"),
])
def test_hash_match(tmp_path, change, code, status) -> None:
    """Every reference job has one rerun line with the same commands_sha256 (pass); another
    hash fails; a missing / extra / error line or a broken hash is not judgeable."""
    reference = _write_rows(tmp_path / "reference.jsonl", [_line(job) for job in REFERENCE_JOBS])
    rerun = [_line(job) for job in REFERENCE_JOBS]
    if change == "differ":
        rerun[1]["commands_sha256"] = HASH_B
    elif change == "missing":
        rerun.pop()
    elif change == "extra":
        rerun.append(_line({**REFERENCE_JOBS[0], "setting": "LS3"}))
    elif change == "error":
        rerun[0]["error"] = "boom"
    elif change == "short_hash":
        rerun[0]["commands_sha256"] = "abc"
    rows = _write_rows(tmp_path / "rows.jsonl", rerun)
    got, report = _run(tmp_path, "hash-match", "--reference", str(reference), "--rows", str(rows))
    assert (got, report["status"]) == (code, status)
    if change is None:
        assert report["compared"] == len(REFERENCE_JOBS)
        assert report["status_basis"] == {"failures": [], "setting_defects": [],
                                          "not_judgeable": []}


def test_hash_match_missing_file_is_not_judgeable(tmp_path) -> None:
    reference = _write_rows(tmp_path / "reference.jsonl", [_line(REFERENCE_JOBS[0])])
    got, report = _run(tmp_path, "hash-match", "--reference", str(reference), "--rows",
                       str(tmp_path / "none.jsonl"))
    assert (got, report["status"]) == (2, "not_judgeable")


def _d0_rows(setting: str, count: int) -> list[dict]:
    return [_line({"case": f"S{index}", "eps": 0.003, "setting": setting})
            for index in range(count)]


@pytest.mark.parametrize(("variant_lines", "code", "status"), [
    (8, 0, "pass"), (7, 2, "not_judgeable"),
])
def test_d0_1_keeps_variant_1_and_needs_8_lines(tmp_path, variant_lines, code, status) -> None:
    """d0-1: only the D0-1 lines of the stored D0 run are the reference (8 of them)."""
    stored = _write_rows(tmp_path / "d0.jsonl",
                         _d0_rows("D0-1", variant_lines) + _d0_rows("D0-2", 8))
    rows = _write_rows(tmp_path / "d0_1.jsonl", _d0_rows("D0-1", variant_lines))
    got, report = _run(tmp_path, "d0-1", "--reference", str(stored), "--rows", str(rows))
    assert (got, report["status"]) == (code, status)
    assert report["setting"] == "D0-1"


# ------------------------------------------------------------------------------- t8
def _main_jsonl(tmp_path: Path) -> Path:
    lines = []
    for index in range(T8_CASES):
        job = {"case": f"C{index:02d}", "eps": 0.0, "offset_s": 0.0, "setting": "VB"}
        lines.append({"job": job})
        lines.append({"job": {**job, "setting": "V0"}})
    return _write_rows(tmp_path / "main.jsonl", lines)


def _t8_rows(main_jsonl: Path) -> list[dict]:
    return [_line(job) for job in run_v5.ed6_t8_jobs(main_jsonl)]


FALLBACK = [[1.0, "WARN_ROD_PRESSURE_FALLBACK:FL"]]


@pytest.mark.parametrize(("change", "code", "status"), [
    (None, 0, "pass"),
    ("differ", 1, "failed"),
    ("fallback_one", 0, "pass"),
    ("fallback_all", 2, "not_judgeable"),
    ("missing", 2, "not_judgeable"),
    ("no_events", 2, "not_judgeable"),
])
def test_t8(tmp_path, change, code, status) -> None:
    """P6-1: VBL = VBL0 commands per pair without a fallback; a fallback pair is a record; no
    pair without a fallback, a missing line or a line without event keys is not judgeable."""
    main_jsonl = _main_jsonl(tmp_path)
    rows = _t8_rows(main_jsonl)
    assert len(rows) == 2 * T8_CASES
    if change == "differ":
        rows[0]["commands_sha256"] = HASH_B
    elif change == "fallback_one":
        rows[0]["events"] = FALLBACK
        rows[0]["commands_sha256"] = HASH_B  # a fallback pair is not compared
    elif change == "fallback_all":
        for row in rows:
            row["events"] = FALLBACK
    elif change == "missing":
        rows.pop()
    elif change == "no_events":
        del rows[3]["events"]
    path = _write_rows(tmp_path / "ed6_t8.jsonl", rows)
    got, report = _run(tmp_path, "t8", "--rows", str(path), "--main-jsonl", str(main_jsonl))
    assert (got, report["status"]) == (code, status)
    if change == "fallback_one":
        assert report["fallback_pairs_record"] == ["C00"]
        assert report["judged_pairs"] == T8_CASES - 1


def test_ed6_batches() -> None:
    """run_v5: ed6_cases = cases E and F x VBL, LSL1 .. LSL4 on the event path."""
    jobs = run_v5.batch_jobs(run_v5.ED6_CASES_BATCH)
    assert len(jobs) == 10
    assert {job["setting"] for job in jobs} == set(run_v5.ED6_JUDGED_SETTINGS)
    assert {(job["twin"]["leg"], job["offset_s"]) for job in jobs} == {("FL", 0.0),
                                                                       ("FR", 0.075)}
    assert run_v5.ED6_T8_SETTINGS == ("VBL", "VBL0")


# ------------------------------------------------------------------------------- cases
def _jp3(judged: int, breach: int = 0) -> dict:
    status = "H-7" if breach else ("pass" if judged else "no_judged_runs")
    return {"status": status, "status_by_revision": {},
            "rev5": {"status": status, "runs_judged": judged, "runs_with_breach": breach}}


@pytest.mark.parametrize(("judged", "breach", "identity", "code", "status"), [
    (10, 0, [], 0, "pass"),
    (10, 1, [], 1, "failed"),
    (9, 0, [], 2, "setting_defect"),
    (0, 0, [], 2, "not_judgeable"),
    (10, 0, ["controller_tag"], 2, "setting_defect"),
])
def test_cases(tmp_path, monkeypatch, judged, breach, identity, code, status) -> None:
    """P6-2: J-P3 key 0 on 10 judged rows; another count is a setting defect, 0 not
    judgeable, a breach H-7 failed, an identity defect a setting defect."""
    rows = [_line(job) for job in run_v5.ed6_case_jobs()]
    path = _write_rows(tmp_path / "ed6_cases.jsonl", rows)
    monkeypatch.setattr(common, "t4h_folders", lambda *_: [])
    monkeypatch.setattr(ed6.base, "j_p3_rows", lambda rows, folders: rows)
    monkeypatch.setattr(j_p3_inputs, "j_p3_over_rows", lambda *_, **__: _jp3(judged, breach))
    monkeypatch.setattr(ed6, "sealed_lsb_settings", lambda: {})
    monkeypatch.setattr(ed6, "ed6_identity_problems", lambda *_, **__: list(identity))
    got, report = _run(tmp_path, "cases", "--rows", str(path))
    assert (got, report["status"]) == (code, status)
    assert report["rows"] == 10


def test_cases_rows_not_the_batch_are_not_judgeable(tmp_path, monkeypatch) -> None:
    rows = [_line(job) for job in run_v5.ed6_case_jobs()][:-1]
    path = _write_rows(tmp_path / "ed6_cases.jsonl", rows)
    monkeypatch.setattr(common, "t4h_folders", lambda *_: [])
    monkeypatch.setattr(ed6.base, "j_p3_rows", lambda rows, folders: rows)
    monkeypatch.setattr(j_p3_inputs, "j_p3_over_rows", lambda *_, **__: _jp3(9))
    monkeypatch.setattr(ed6, "sealed_lsb_settings", lambda: {})
    monkeypatch.setattr(ed6, "ed6_identity_problems", lambda *_, **__: [])
    got, report = _run(tmp_path, "cases", "--rows", str(path))
    assert got == 2
    assert any("ed6_cases jobs" in reason for reason in report["status_basis"]["not_judgeable"])


# ------------------------------------------------------------------------------- l1 hash
def _l1(path: Path, digests: list[str]) -> Path:
    results = [{"harness": "H", "inner": str(index), "base": {"commands_sha256": digest}}
               for index, digest in enumerate(digests)]
    path.write_text(json.dumps({"results": results}), encoding="utf-8")
    return path


def test_l1_hash_record_vbl_bundle(tmp_path) -> None:
    """Erratum 2 2-4: the L1a VBL / VBL0 pair (a record; counts only)."""
    vbl = _l1(tmp_path / "L1a_VBL.json", [HASH_A, HASH_A])
    vbl0 = _l1(tmp_path / "L1a_VBL0.json", [HASH_A, HASH_B])
    out = tmp_path / "l1_hash_record.json"
    assert tjr.main(["l1-hash-record", "--bundle", "VBL", "--vbl-l1", str(vbl), "--vbl0-l1",
                     str(vbl0), "--out", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert (report["pairs"], report["same_command_hash"], report["other_command_hash"]) == (2, 1, 1)
    missing = tmp_path / "missing.json"
    assert tjr.main(["l1-hash-record", "--bundle", "VBL", "--vbl-l1", str(vbl), "--vbl0-l1",
                     str(tmp_path / "none.json"), "--out", str(missing)]) == 2
    reasons = json.loads(missing.read_text(encoding="utf-8"))["not_judgeable"]
    assert any(reason.startswith("VBL0 L1 run") for reason in reasons)


# ------------------------------------------------------------------------------- suite
def _junit(path: Path, cases: dict[str, str]) -> Path:
    """``classname::name`` -> outcome (passed / failed / error / skipped / xfailed)."""
    body = []
    for test_id, outcome in cases.items():
        classname, name = test_id.split("::")
        inner = {"passed": "", "failed": "<failure message='x'/>", "error": "<error message='x'/>",
                 "skipped": "<skipped type='pytest.skip' message='x'/>",
                 "xfailed": "<skipped type='pytest.xfail' message='x'/>"}[outcome]
        body.append(f"<testcase classname='{classname}' name='{name}'>{inner}</testcase>")
    path.write_text("<testsuites><testsuite name='pytest'>" + "".join(body)
                    + "</testsuite></testsuites>", encoding="utf-8")
    return path


BASE_CASES = {"05_tests.unit.test_other::test_a": "failed",
              "05_tests.unit.test_other::test_b": "skipped",
              "05_tests.unit.test_other::test_c": "passed",
              "05_tests.unit.test_ed6_x::test_d": "passed"}


@pytest.mark.parametrize(("change", "code", "finding"), [
    ({}, 0, None),
    ({"05_tests.unit.test_other::test_c": "failed"}, 1, "new_failure"),
    ({"05_tests.unit.test_ed6_x::test_d": "skipped"}, 1, "core_not_passing"),
    ({"05_tests.unit.test_jp3_y::test_new": "xfailed"}, 1, "core_not_passing"),
    ({"05_tests.unit.test_other::test_new": "skipped"}, 1, "new_skip_or_xfail"),
    ({"05_tests.unit.test_other::test_a": "skipped"}, 1, "new_skip_or_xfail"),
    ({"05_tests.unit.test_other::test_b": "failed"}, 1, "new_failure"),
    ({"05_tests.unit.test_other::test_new": "passed"}, 0, None),
])
def test_suite_judge(tmp_path, change, code, finding) -> None:
    """Erratum 2 2-2: new failures and core tests not passing fail; another skip passes only
    when the baseline skipped the same test; an existing failure outside the core is a record."""
    import jp3_ed6_suite as suite

    listed = tmp_path / "existing_failures.txt"
    assert suite.main(["baseline", "--junit", str(_junit(tmp_path / "base.xml", BASE_CASES)),
                       "--merge-base", "f" * 40, "--out", str(listed)]) == 0
    lines = listed.read_text(encoding="utf-8").splitlines()
    assert lines == ["# merge_base " + "f" * 40,
                     "failed\t05_tests.unit.test_other::test_a",
                     "skipped\t05_tests.unit.test_other::test_b"]
    sha = (tmp_path / "existing_failures.txt.sha256").read_text(encoding="utf-8").split()[0]
    run = _junit(tmp_path / "run.xml", {**BASE_CASES, **change})
    out = tmp_path / "judgement.json"
    assert suite.main(["judge", "--junit", str(run), "--baseline-list", str(listed),
                       "--baseline-sha256", sha, "--out", str(out)]) == code
    report = json.loads(out.read_text(encoding="utf-8"))
    flagged = {name for name, items in report["findings"].items() if items}
    assert flagged == ({finding} if finding else set())
    if not change:
        assert report["existing_failures_record"] == [
            "failed\t05_tests.unit.test_other::test_a (list: failed)",
            "skipped\t05_tests.unit.test_other::test_b (list: skipped)"]


def test_suite_judge_inputs(tmp_path) -> None:
    """Another baseline sha256, a missing or empty JUnit: not judgeable (2)."""
    import jp3_ed6_suite as suite

    listed = tmp_path / "list.txt"
    assert suite.main(["baseline", "--junit", str(_junit(tmp_path / "b.xml", BASE_CASES)),
                       "--merge-base", "f" * 40, "--out", str(listed)]) == 0
    run = _junit(tmp_path / "r.xml", BASE_CASES)
    assert suite.main(["judge", "--junit", str(run), "--baseline-list", str(listed),
                       "--baseline-sha256", "0" * 64, "--out", str(tmp_path / "a.json")]) == 2
    sha = (tmp_path / "list.txt.sha256").read_text(encoding="utf-8").split()[0]
    assert suite.main(["judge", "--junit", str(tmp_path / "none.xml"), "--baseline-list",
                       str(listed), "--baseline-sha256", sha,
                       "--out", str(tmp_path / "b.json")]) == 2
    empty = _junit(tmp_path / "empty.xml", {})
    assert suite.main(["judge", "--junit", str(empty), "--baseline-list", str(listed),
                       "--baseline-sha256", sha, "--out", str(tmp_path / "c.json")]) == 2
    assert suite.CORE_PATTERNS == ("test_jp3_*", "test_ed6_*", "test_run_v5*",
                                   "test_lock_start_b*", "test_c2*", "test_extend_start_bound*")


# ------------------------------------------------------------------------------- pwsh
def _pwsh() -> str:
    pwsh = shutil.which("pwsh")
    assert pwsh is not None, "pwsh (PowerShell 7) is needed for the run step tests"
    return pwsh


def _gate(tmp_path: Path, body: str, report: dict) -> str:
    """``body`` after dot-sourcing the edition 5 and edition 6 record gates alone; ``{r}`` =
    the report file. The last output line."""
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    script = tmp_path / f"gate_{len(list(tmp_path.glob('gate_*.ps1')))}.ps1"
    gates5 = STEPS.parent / "run_steps_ed5" / "record_gates_ed5.ps1"
    script.write_text(f". '{gates5}'\n. '{STEPS / 'record_gates_ed6.ps1'}'\n"
                      + body.replace("{r}", f"'{path}'") + "\n", encoding="utf-8")
    done = subprocess.run([_pwsh(), "-NoProfile", "-NonInteractive", "-File", str(script)],
                          capture_output=True, text=True, encoding="utf-8", timeout=120,
                          check=False)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip().splitlines()[-1]


H7 = {"jp3_outcome": "H-7", "J-P3": {"status": "H-7", "runs_judged": 1},
      "failures": ["VBL: J-P3 H-7"], "record_failures": [], "setting_defects": [],
      "not_judgeable": []}


def test_h7_stop_leaves_the_vbl_marker(tmp_path) -> None:
    """Erratum 2 2-4: a synthetic T-JR-12a VBL H-7 stops 1 and leaves 'judged:t12_VBL_jp3'
    (the edition 5 name stays with the edition 5 function); a record-only report leaves none."""
    body = ("$Stop = Get-RecordToolStop {r} -VbjJp3\n"
            "$Markers = Get-Ed6JudgedFailureMarkers $Stop -Jp3\n"
            "$Keys = ($Markers.Keys | ForEach-Object { \"$_=$($Markers[$_])\" }) -join ','\n"
            "Write-Output \"$($Stop.code)|$Keys\"")
    assert _gate(tmp_path, body, H7) == "1|judged:t12_VBL_jp3=1"
    record = ["VBL: 1 new_fault keys"]
    record_only = {**H7, "jp3_outcome": "pass", "J-P3": {"status": "pass", "runs_judged": 1},
                   "failures": record, "record_failures": record}
    none = ("$Stop = Get-RecordToolStop {r} -VbjJp3\n"
            "$Markers = Get-Ed6JudgedFailureMarkers $Stop -Jp3\n"
            "Write-Output \"go=$($null -eq $Stop) n=$($Markers.Count)\"")
    assert _gate(tmp_path, none, record_only) == "go=True n=0"
    edition5 = ("$Stop = Get-RecordToolStop {r} -VbjJp3\n"
                "$Markers = Get-JudgedFailureMarkers $Stop -VbjJp3\n"
                "Write-Output (($Markers.Keys) -join ',')")
    assert _gate(tmp_path, edition5, H7) == "judged:t12_VBJ_jp3"


def test_marker_refuses_a_new_attempt(tmp_path) -> None:
    """A stop record with the edition 6 marker refuses a new attempt (Get-RefusedPreviousStop
    reads every 'judged:*' code); the record tool code alone does not."""
    body = ("$Reason = Get-RefusedPreviousStop {r} @('tool:t12_VBL')\n"
            "if ($Reason) { Write-Output 'refused' } else { Write-Output 'go' }")
    assert _gate(tmp_path, body, {"codes": {"tool:t12_VBL": 1, "judged:t12_VBL_jp3": 1}}) \
        == "refused"
    assert _gate(tmp_path, body, {"codes": {"tool:t12_VBL": 1}}) == "go"


@pytest.mark.parametrize("config", [
    {"run_commit": "<ED6_RUN_COMMIT>", "worktree": "<ED6_RUN_WORKTREE>"},
    {"run_commit": "0" * 40, "worktree": "<ED6_RUN_WORKTREE>"},
    None,
])
def test_placeholder_left_stops_3(tmp_path, config) -> None:
    """Erratum 2 2-4: a run configuration with a placeholder left (or none) ends the step with
    exit 3 before any step folder (Exit-Ed6), whatever step is started."""
    dry_root = tmp_path / "dry"
    dry_root.mkdir()
    if config is not None:
        (dry_root / "ed6_run_config.json").write_text(json.dumps(config), encoding="utf-8")
    environment = {**os.environ, "ED6_DRY_RUN_ROOT": str(dry_root)}
    for step in ("step_l1ref_ed6.ps1", "step5_impl_ed6.ps1"):
        extra = ["-Part", "t8", "-MaskHex", "0x1", "-Workers", "1"] if step.startswith("step5") \
            else []
        done = subprocess.run([_pwsh(), "-NoProfile", "-NonInteractive", "-File",
                               str(STEPS / step), *extra], capture_output=True, text=True,
                              encoding="utf-8", timeout=120, check=False, env=environment)
        assert done.returncode == 3, (step, done.stdout, done.stderr)
        assert "STOP:" in done.stdout
    assert not (dry_root / "j9_runs").exists()


def test_template_still_holds_its_placeholders() -> None:
    template = json.loads((STEPS / "ed6_run_config.template.json").read_text(encoding="utf-8"))
    assert str(template["run_commit"]).startswith("<ED6_")
    assert str(template["worktree"]).startswith("<ED6_")
