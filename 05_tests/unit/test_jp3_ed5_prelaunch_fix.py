"""436.9 edition 5 prelaunch audit fixes (``ed5_design/audit_prelaunch_ed5_step0.md``):

* B-1 (a): every (plan, key file) pair the run steps hand to the r79 runner passes the runner's
  X-10 guard as the runner applies it (``r79_L3L4_final`` keys file -> job keys ->
  ``rod_fault_plan.load_plan`` + ``key_problems``), no simulation: b1 .. b4 (steps 6b / 6c),
  c90 / c91 (step 0) and the 8 T-CK / DROPOUT pairs (step 7b), made by X-11 and the ckdrop
  selection from the stored case source;
* B-2: the P5-2 record (judged key total of the P4-on rev 6 rows only), ``p52-compare`` and the
  fixed-record gate of ``step_p5fixed.ps1``;
* W-1: a VBJ J-P3 H-7 stop leaves a judged-failure marker that refuses a new attempt;
* W-3: step (1) goes on only with the c dry check written and c < 0.5.

The run step gates run alone under pwsh (``record_gates_ed5.ps1``); a missing pwsh fails.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
for _path in (COUPLED_DIR, S8_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import jp3_12b_plan as plan  # noqa: E402
import jp3_ckdrop_plan as ckdrop  # noqa: E402
import jp3_fixed_inputs as fixed  # noqa: E402
import jp3_p5_fixed_values as p5  # noqa: E402
import rod_fault_plan as rfp  # noqa: E402

DATA_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT", ROOT))
NOISE = (DATA_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "resume_k1"
         / "h8_noise_VB.json")
STEPS = ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "prelaunch_j9" / "run_steps_ed5"
GATES_PS1 = STEPS / "record_gates_ed5.ps1"

STEP_PAIRS = {
    "step0_cdry.ps1": ('"$X11Folder\\${Run}_plan.json"', '"$X11Folder\\${Run}_keys.txt"'),
    "step6b_vbk0.ps1": ('"$X11Folder\\${Block}_plan.json"', '"$X11Folder\\${Block}_keys.txt"'),
    "step6c_vbk.ps1": ('"$X11Folder\\${Block}_plan.json"', '"$X11Folder\\${Block}_keys.txt"'),
    "step7b_ckdrop.ps1": ('"$CkdropFolder\\${Bundle}_${Leg}_plan.json"',
                          '"$CkdropFolder\\${Bundle}_keys.txt"'),
}
"""The plan and key file each step hands to one runner (the R79_ROD_FAULT_PLAN environment
and ``--keys-file``)."""


# ------------------------------------------------------------------------------- B-1
def _runner_job_keys(keys_file: Path) -> list[str]:
    """The job keys of a run as ``r79_L3L4_final.cmd_run`` makes them from ``--keys-file``
    (the r72 / r67 screens it imports read the root from ``sys.argv[1]``, as the runner's
    ``las_t3_dg3.py <root> run ...`` command line gives it)."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sys, "argv", [str(COUPLED_DIR / "las_t3_dg3.py"), str(ROOT), "run"])
        import r79_L3L4_final as final

        listed = final.read_keys_file(keys_file)
        assert final.keys_file_problems(listed, ["L2"]) == [], keys_file
        return [final.candidate_key(final.screen.split_candidate(key)[1]) for key in listed]


@pytest.fixture(scope="module")
def prelaunch_outputs(tmp_path_factory) -> dict:
    """X-11 and the ckdrop selection from the stored case source (an empty scan root)."""
    if not NOISE.is_file():
        pytest.skip("stored h8_noise_VB.json not present (OUTRIGGER_RECORDS_ROOT)")
    folder = tmp_path_factory.mktemp("prelaunch")
    scan = folder / "scan"
    scan.mkdir()
    x11 = folder / "x11"
    plan.select(NOISE, scan, x11, noise_sha256=fixed.NOISE_VB_SHA256)
    selection = x11 / "selection.json"
    ck = folder / "ckdrop"
    ckdrop.select(selection, hashlib.sha256(selection.read_bytes()).hexdigest(), scan, (), ck)
    return {"x11": x11, "ckdrop": ck}


def _step_pairs(outputs: dict) -> dict[str, list[tuple[Path, Path]]]:
    """Every (plan, key file) pair of the run steps with the folders of ``outputs``."""
    x11, ck = outputs["x11"], outputs["ckdrop"]
    return {
        "step0_cdry.ps1": [(x11 / f"{run}_plan.json", x11 / f"{run}_keys.txt")
                           for run in ("c90", "c91")],
        "step6b_vbk0.ps1": [(x11 / f"b{j}_plan.json", x11 / f"b{j}_keys.txt") for j in range(1, 5)],
        "step6c_vbk.ps1": [(x11 / f"b{j}_plan.json", x11 / f"b{j}_keys.txt") for j in range(1, 5)],
        "step7b_ckdrop.ps1": [(ck / f"{bundle}_{leg}_plan.json", ck / f"{bundle}_keys.txt")
                              for bundle in ("tck", "dropout")
                              for leg in ("FL", "FR", "RL", "RR")],
    }


def test_step_scripts_hand_these_plan_key_pairs() -> None:
    """The pairs below are the ones the step scripts build (a changed script breaks this)."""
    for script, (plan_text, keys_text) in STEP_PAIRS.items():
        text = (STEPS / script).read_text(encoding="utf-8")
        assert plan_text in text and keys_text in text, script
    step0 = (STEPS / "step0_cdry.ps1").read_text(encoding="utf-8")
    assert "c90_91" not in step0  # B-1: no shared dry plan any more


def test_every_run_step_pair_passes_the_runner_guard(prelaunch_outputs) -> None:
    """B-1 (a): load_plan + key_problems on the runner's job keys of every pair - b1 .. b4,
    c90 / c91 and the 8 T-CK / DROPOUT pairs; the guard (plan = jobs exactly) as it is."""
    pairs = _step_pairs(prelaunch_outputs)
    assert [len(pairs[name]) for name in STEP_PAIRS] == [2, 4, 4, 8]
    for script, items in pairs.items():
        for plan_path, keys_path in items:
            loaded = rfp.load_plan(plan_path)
            problems = loaded.key_problems(_runner_job_keys(keys_path))
            assert problems == [], (script, plan_path.name, keys_path.name, problems)


def test_the_guard_still_refuses_a_plan_beyond_the_jobs(prelaunch_outputs, tmp_path) -> None:
    """The old shared dry plan (both seeds) against one seed's key file is refused: the guard
    is not weakened."""
    x11 = prelaunch_outputs["x11"]
    faults = {}
    for run in ("c90", "c91"):
        faults.update(json.loads((x11 / f"{run}_plan.json").read_text(encoding="utf-8"))["faults"])
    shared = tmp_path / "c90_91_plan.json"
    shared.write_text(json.dumps({"schema": plan.PLAN_SCHEMA, "faults": faults}), encoding="utf-8")
    problems = rfp.load_plan(shared).key_problems(_runner_job_keys(x11 / "c90_keys.txt"))
    assert any("no job of the run" in text for text in problems)


# ------------------------------------------------------------------------------- B-2
def _case_row(setting: str, revision: int, *, p4: bool, witness=(0, 1, 0, 0), judged=0,
              case: str = "R12") -> dict:
    check = {"rule_revision": revision, "jp3a_breach_reads": [judged, 0, 0, 0],
             "jp3b_breach_over_tol_reads": [0] * 4, "jp3c_breach_reads": [0] * 4,
             "jp3_r58_witness_carries": list(witness), "jp3_r59_substeps": [0, 300, 0, 0],
             "jp3_r510_candidates": [0, 2, 0, 0]}
    return {"job": {"case": case, "setting": setting, "mask": "0xFFFF", "t4h_dir": "x"},
            "hydraulic_options": {"rod_reading_truth": p4},
            "hydraulics_record": {"extend_bound_check": check}}


def _write_rows(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def test_p52_judged_total_counts_the_p4_on_rev6_rows_only(tmp_path) -> None:
    """Erratum 1 1A (B-2): a P4-off rev 6 row (VBH) and a rev 4 row (VB) with judged keys do
    not enter the total; their keys stay per row."""
    rows = _write_rows(tmp_path / "j9_cases.jsonl", [
        _case_row("VBJ", 6, p4=True), _case_row("VBH", 6, p4=False, judged=3),
        _case_row("VB", 4, p4=False, judged=2)])
    report = p5.p52([rows])
    assert report["judged_key_total"] == 0
    assert (report["rev6_rows"], report["p4_on_rev6_rows"]) == (2, 1)
    vbh = next(row for row in report["rows"] if row["setting"] == "VBH")
    assert vbh["jp3a_breach_reads_sum"] == 3 and vbh["source"] == "j9_cases.jsonl"
    assert "mask" not in vbh["identity"] and "t4h_dir" not in vbh["identity"]
    with_p4 = p5.p52([_write_rows(tmp_path / "e.jsonl", [_case_row("LSJ1", 6, p4=True,
                                                                    judged=1)])])
    assert with_p4["judged_key_total"] == 1


def test_stored_violation_of_case_a_does_not_stop_the_fixed_step(tmp_path) -> None:
    """Erratum 4 4-1: A's stored violation (VB / LS, rev 4: judged keys > 0) and a P4-off rev 6
    row's keys are records; the step_p5fixed gate stops only on the P4-on rev 6 rows. The
    record keeps the rows files' sha256 and the disclosure sentence."""
    rows = _write_rows(tmp_path / "j9_cases.jsonl", [
        _case_row("VB", 4, p4=False, judged=2), _case_row("LS2", 4, p4=False, judged=3),
        _case_row("VBH", 6, p4=False, judged=1), _case_row("VBJ", 6, p4=True)])
    report = p5.p52([rows])
    assert report["judged_key_total"] == 0
    assert report["judged_key_record"] == {"rev4_rows": 5, "p4_off_rev6_rows": 1}
    assert report["inputs"] == [{"path": str(rows),
                                 "sha256": hashlib.sha256(rows.read_bytes()).hexdigest()}]
    assert report["disclosure"] == p5.P52_DISCLOSURE
    out = _gate(tmp_path, "$Stop = Get-P5FixedStop {r}\n" + SHOW, {"r": report})
    assert out == "go"
    common = (STEPS / "common_ed5.ps1").read_text(encoding="utf-8")
    assert f"$P5FixedDisclosure = '{p5.P52_DISCLOSURE}'" in common


def test_p52_problems_stop_the_fixed_step_with_exit_2(tmp_path) -> None:
    """Erratum 4 4-1 (audit N-1): a fixed record with problems is not fixed - no ③ record, a
    judged key missing, a rev 6 row without its R5-8 .. R5-10 counts each stop 2."""
    no_record = {"job": {"case": "R1", "setting": "VBJ"}, "hydraulic_options": {}}
    no_judged = _case_row("VBJ", 6, p4=True)
    del no_judged["hydraulics_record"]["extend_bound_check"]["jp3a_breach_reads"]
    no_counts = _case_row("LSJ1", 6, p4=True)
    del no_counts["hydraulics_record"]["extend_bound_check"]["jp3_r510_candidates"]
    for name, bad in (("record", no_record), ("judged", no_judged), ("counts", no_counts)):
        rows = _write_rows(tmp_path / name / "j9_cases.jsonl", [_case_row("VBJ", 6, p4=True),
                                                                bad])
        report = p5.p52([rows])
        assert report["problems"], name
        out = _gate(tmp_path / name, "$Stop = Get-P5FixedStop {r}\n" + SHOW, {"r": report})
        assert out.startswith("2|"), (name, out)


def test_p52_compare_without_a_fixed_count_is_not_judgeable(tmp_path, monkeypatch,
                                                           capsys) -> None:
    """Erratum 4 4-1 (audit N-1): a rev 6 count missing on either side is not judgeable (exit
    2), never a pass of two missing values."""
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    gap = _case_row("VBJ", 6, p4=True)
    del gap["hydraulics_record"]["extend_bound_check"]["jp3_r58_witness_carries"]
    code, report = _compare(tmp_path, [gap], [gap], "both_missing")
    assert code == 2 and report["status"] == "not_judgeable" and not report["failures"]
    code, report = _compare(tmp_path, [_case_row("VBJ", 6, p4=True)], [gap], "new_missing")
    assert code == 2 and report["not_judgeable"]
    capsys.readouterr()


def test_p54_record_lists_the_input_files_sha(tmp_path, monkeypatch) -> None:
    """Erratum 4 4-1: the P5-4 record lists every T4h file it replays with its sha256."""
    folder = tmp_path / "VBH_t4h"
    folder.mkdir()
    for index in range(3):
        (folder / f"k{index}.npz").write_bytes(bytes([index]) * 10)
    monkeypatch.setattr(p5, "p54_record", lambda path, revision: {
        "file": path.name, "revision": revision, "dominated_reads": 1, "stretches": 0,
        "max_over_kN": []})
    monkeypatch.setattr(p5, "proxy_disclosure", lambda: {})
    report = p5.p54(folder)
    assert [entry["file"] for entry in report["inputs"]] == ["k0.npz", "k1.npz", "k2.npz"]
    assert report["inputs"][1]["sha256"] == hashlib.sha256(bytes([1]) * 10).hexdigest()


def test_dry_union_check(prelaunch_outputs) -> None:
    """Erratum 4 4-2: X-11 records that c90 + c91 are the 160 pairs, 20 per cell; a broken
    union is not usable; step 0 reads the record."""
    selection = json.loads((prelaunch_outputs["x11"] / "selection.json").read_text(
        encoding="utf-8"))
    check = selection["dry"]["union_check"]
    assert check["ok"] is True and (check["pairs"], check["cells"]) == (160, 8)
    assert set(check["per_cell"].values()) == {20}
    plans = {seed: json.loads((prelaunch_outputs["x11"] / f"c{seed}_plan.json").read_text(
        encoding="utf-8")) for seed in plan.DRY_SEEDS}
    plans[91]["faults"].pop(next(iter(plans[91]["faults"])))
    with pytest.raises(plan.NotUsable, match="160 pairs"):
        plan.dry_union_check(plans)
    assert "union_check" in (STEPS / "step0_cdry.ps1").read_text(encoding="utf-8")


def test_fixed_values_commit_record_and_closure_path() -> None:
    """Erratum 4 4-1: step_p5fixed names the run commit and the disclosure; -Part list takes
    another commit's records only through a jp3_import_closure.py report (listed too)."""
    step = (STEPS / "step_p5fixed.ps1").read_text(encoding="utf-8")
    assert "Codes['p5fixed_commit'] = $RunCommit" in step
    assert "Codes['p5fixed_disclosure'] = $P5FixedDisclosure" in step
    prelaunch = (STEPS / "prelaunch_ed5.ps1").read_text(encoding="utf-8")
    assert "$P5FixedCommit -ne $RunCommit" in prelaunch
    assert "jp3_import_closure.py" in prelaunch and "--add', $Closure" in prelaunch


def _fixed(tmp_path: Path, rows: list[dict]) -> tuple[Path, str]:
    source = _write_rows(tmp_path / "fixed_src" / "j9_cases.jsonl", rows)
    path = tmp_path / "p52.json"
    path.write_text(json.dumps(p5.p52([source])), encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _compare(tmp_path: Path, fixed_rows: list[dict], new_rows: list[dict], name: str,
             sha: str | None = None) -> tuple[int, dict]:
    fixed_path, fixed_sha = _fixed(tmp_path / name, fixed_rows)
    new = _write_rows(tmp_path / name / "new" / "j9_cases.jsonl", new_rows)
    out = tmp_path / name / "compare.json"
    code = p5.main(["p52-compare", "--fixed", str(fixed_path), "--fixed-sha256", sha or fixed_sha,
                    "--rows", f"j9_cases.jsonl={new}", "--out", str(out)])
    return code, (json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {})


def test_p52_compare_pass_differ_judged_and_not_judgeable(tmp_path, monkeypatch, capsys) -> None:
    """B-2 stops: a rev 6 count differing from the fixed one (exit 1), a P4-on judged key > 0
    (exit 1); another sha256 / row set (exit 2); the same rows pass (exit 0). The run-time
    fields (mask, T4h folder) are no part of a row's identity."""
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    base = [_case_row("VBJ", 6, p4=True), _case_row("VBH", 6, p4=False),
            _case_row("VB", 4, p4=False, judged=2)]
    moved = [dict(row, job={**row["job"], "t4h_dir": "elsewhere"}) for row in base]
    assert _compare(tmp_path, base, moved, "same")[0] == 0
    differing = [_case_row("VBJ", 6, p4=True), _case_row("VBH", 6, p4=False, witness=(0, 2, 0, 0)),
                 base[2]]
    code, report = _compare(tmp_path, base, differing, "differ")
    assert code == 1 and any("differ from the fixed" in text for text in report["failures"])
    judged = [_case_row("VBJ", 6, p4=True, judged=1), base[1], base[2]]
    code, report = _compare(tmp_path, base, judged, "judged")
    assert code == 1 and any("judged key > 0" in text for text in report["failures"])
    code, report = _compare(tmp_path, base, base[:2], "missing")
    assert code == 2 and report["not_judgeable"]
    assert _compare(tmp_path, base, base, "sha", sha="0" * 64)[0] == 2
    capsys.readouterr()


# ------------------------------------------------------------------------------- pwsh gates
def _gate(tmp_path: Path, body: str, files: dict[str, dict] | None = None) -> str:
    """Run ``body`` after dot-sourcing ``record_gates_ed5.ps1`` alone (``{name}`` = a JSON file
    of ``files``); the last output line."""
    pwsh = shutil.which("pwsh")
    assert pwsh is not None, "pwsh (PowerShell 7) is needed for the run step gate tests"
    paths = {}
    for name, document in (files or {}).items():
        paths[name] = tmp_path / f"{name}.json"
        paths[name].write_text(json.dumps(document), encoding="utf-8")
    index = len(list(tmp_path.glob("gate_*.ps1")))
    script = tmp_path / f"gate_{index}.ps1"
    for name, path in paths.items():  # str.replace: the PowerShell body has its own braces
        body = body.replace("{" + name + "}", f"'{path}'")
    script.write_text(f". '{GATES_PS1}'\n{body}\n", encoding="utf-8")
    done = subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-File", str(script)],
                          capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip().splitlines()[-1]


SHOW = "if ($Stop) { Write-Output \"$($Stop.code)|$($Stop.reason)\" } else { Write-Output 'go' }"


def test_p5fixed_gate(tmp_path) -> None:
    """B-2 at step_p5fixed: problems / an empty rev 6 or P4-on set stop 2, a judged key > 0
    stops 1, a full record goes on."""
    good = {"problems": [], "rev6_rows": 30, "p4_on_rev6_rows": 10, "judged_key_total": 0}
    cases = {"good": (good, "go"), "problem": ({**good, "problems": ["x"]}, "2|"),
             "empty": ({**good, "p4_on_rev6_rows": 0}, "2|"),
             "judged": ({**good, "judged_key_total": 1}, "1|"),
             "lacking": ({"problems": []}, "3|")}
    for name, (document, expected) in cases.items():
        out = _gate(tmp_path, "$Stop = Get-P5FixedStop {r}\n" + SHOW, {"r": document})
        assert out.startswith(expected), name


def test_dry_c_gate_of_step1(tmp_path) -> None:
    """W-3: step (1) goes on with the c dry check written and c < 0.5; c >= 0.5, no c or
    another status stops 2."""
    cases = {"low": ({"status": "written", "c": 0.3}, "go"),
             "half": ({"status": "written", "c": 0.5}, "2|"),
             "none": ({"status": "written", "c": None}, "2|"),
             "status": ({"status": "not_judgeable", "c": 0.1}, "2|")}
    for name, (document, expected) in cases.items():
        out = _gate(tmp_path, "$Stop = Get-DryCStop {r}\n" + SHOW, {"r": document})
        assert out.startswith(expected), name
    assert _gate(tmp_path, f"$Stop = Get-DryCStop '{tmp_path / 'absent.json'}'\n" + SHOW
                 ).startswith("3|")
    step1 = (STEPS / "step1_p1.ps1").read_text(encoding="utf-8")
    assert re.search(r"Initialize-Ed5Step 'p1' \$Attempt @\('cdry'\)", step1)
    assert "Get-DryCStop" in step1


def test_h7_stop_marker_refuses_a_new_attempt(tmp_path) -> None:
    """W-1: Get-RecordToolStop -VbjJp3 exit 1 leaves 'judged:t12_VBJ_jp3' = 1; a stop record
    with it refuses a new attempt; a record tool's exit 1 alone (t12_VBJ, a record) does not."""
    h7 = {"jp3_outcome": "H-7", "J-P3": {"status": "H-7", "runs_judged": 1},
          "failures": ["VBJ: J-P3 H-7"], "record_failures": [], "setting_defects": [],
          "not_judgeable": []}
    body = ("$Stop = Get-RecordToolStop {r} -VbjJp3\n"
            "$Markers = Get-JudgedFailureMarkers $Stop -VbjJp3\n"
            "Write-Output (($Markers.Keys | ForEach-Object { \"$_=$($Markers[$_])\" }) -join ',')")
    assert _gate(tmp_path, body, {"r": h7}) == "judged:t12_VBJ_jp3=1"
    no_marker = ("$Stop = Get-RecordToolStop {r} -VbjJp3\n"
                 "$Markers = Get-JudgedFailureMarkers $Stop -VbjJp3\n"
                 "Write-Output \"n=$($Markers.Count)\"")
    record = ["VBJ: 1 new_fault keys"]
    record_only = {**h7, "jp3_outcome": "pass", "J-P3": {"status": "pass", "runs_judged": 1},
                   "failures": record, "record_failures": record}
    assert _gate(tmp_path, no_marker, {"r": record_only}) == "n=0"
    refuse = ("$Reason = Get-RefusedPreviousStop {s} @('tool:base_judge_compare', 'tool:t12_VBJ')\n"
              "if ($Reason) { Write-Output \"refused|$Reason\" } else { Write-Output 'go' }")
    marked = {"codes": {"tool:t12_VBJ": 1, "judged:t12_VBJ_jp3": 1}}
    assert _gate(tmp_path, refuse, {"s": marked}).startswith("refused|")
    assert _gate(tmp_path, refuse, {"s": {"codes": {"tool:t12_VBJ": 1}}}) == "go"
    assert _gate(tmp_path, refuse, {"s": {"codes": {"tool:case_f": 1}}}).startswith("refused|")
    common = (STEPS / "common_ed5.ps1").read_text(encoding="utf-8")
    assert "function Read-PreviousStops" in common and "Get-RefusedPreviousStop" in common
    assert "Get-JudgedFailureMarkers" in common
