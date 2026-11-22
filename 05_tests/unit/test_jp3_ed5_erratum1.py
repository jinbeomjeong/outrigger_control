"""436.9 edition 5 erratum 1 (``jp3_remedy_spec_v5_erratum1.md``) and the control review of
``8a3c48c7``: X11 on ③ revision 5 (1), case D as ``VBG6`` (2), T-JR-13 on revision 6 only (4),
the P5-4 proxy disclosure (8) and the X-4 dry keys, T4h presence and 78fd5d2d comparison (9).

The scripts that patch ``run_v5`` globals at import (``jp3_x11_replay``, ``jp3_case_replay``)
are probed in a child interpreter so that no other test sees their settings.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import j_p3_inputs as inputs  # noqa: E402
import jp3_dryrun_evidence as dryrun  # noqa: E402
import jp3_fixed_inputs as fixed  # noqa: E402
import jp3_fixed_inputs_list as fixed_list  # noqa: E402
import jp3_p5_fixed_values as p5  # noqa: E402
import jp3_p51_compare as p51  # noqa: E402
import jp3_rerun_match as rerun  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
from test_jp3_addendum_4a2 import REPLAY_REPORTS, T4H_NAMES  # noqa: E402
from test_jp3_addendum_4a3 import SELECTION, _summary_files  # noqa: E402

KEY_FILE_TABLE = {
    "g6": ("L2|s25|g6|0|g6|G1+J1@FL|top|Fs0",
           "1a79e02fc33ae8844d0cd5672e9e5e745215c354e58e9a8095376939c4335e74"),
    "g8": ("L2|s25|g8|0|slope|edge|top|4.0|ref|none|0",
           "b7c7470a800ce1146d30caefa8050fbb1a73c18058af2b23af7dedf399619bd4"),
    "ref": ("L2|s25|ref|0|rigid|B|0,0",
            "95ce6f27b44bb13b76fe8fb02d056f6dc5ae1de9be28b29d1529b8fbbd965299")}
"""Erratum 1 9.1 table (generated key, key file sha256), typed from the document."""
A, B = "a" * 64, "b" * 64


def _child(code: str) -> dict:
    """Run ``code`` in a child interpreter (project root, coupled scripts on the path); its
    last stdout line is JSON."""
    prelude = (f"import sys, json; sys.path.insert(0, {str(COUPLED_DIR)!r}); "
               "sys.dont_write_bytecode = True\n")
    completed = subprocess.run(  # noqa: S603 (this interpreter, fixed code)
        [sys.executable, "-I", "-B", "-c", prelude + code], cwd=ROOT, capture_output=True,
        text=True, encoding="utf-8", check=False, timeout=300)
    assert completed.returncode == 0, completed.stderr[-2000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


# ------------------------------------------------------------------------------- 1 / 2
def test_x11_stays_on_revision_5_and_case_d_runs_revision_6() -> None:
    """Erratum 1 1: ``LSJ4_X11`` = the edition 4a P4-5a arm (③ rev 5), LSJ4 itself rev 6;
    2: ``VBG6`` = the case D plant on ③ rev 6, ``VBG4`` unchanged (rev 4)."""
    found = _child(
        "import jp3_x11_replay, jp3_case_replay, run_v5\n"
        "from outrigger_sim.hydraulics.v5_options import HydraulicOptions as H\n"
        "rev = lambda options: H.from_dict(options).extend_start_revision\n"
        "print(json.dumps({'x11': run_v5.options_of('LSJ4_X11')[1].extend_start_revision,\n"
        "  'lsj4': run_v5.options_of('LSJ4')[1].extend_start_revision,\n"
        "  'x11_is_rev5_lsj4': run_v5.ALL_SETTINGS['LSJ4_X11']"
        " == run_v5.JP3_REV5_SETTINGS['LSJ4'],\n"
        "  'vbg6': rev(jp3_case_replay.CASE_SETTINGS['VBG6'][1]),\n"
        "  'vbg4': rev(jp3_case_replay.CASE_SETTINGS['VBG4'][1]),\n"
        "  'vbg6_in_run_v5': 'VBG6' in run_v5.SETTINGS,\n"
        "  'previous': jp3_case_replay.CASE_D_PREVIOUS_SETTING}))\n")
    assert found == {"x11": 5, "lsj4": 6, "x11_is_rev5_lsj4": True, "vbg6": 6, "vbg4": 4,
                     "vbg6_in_run_v5": False, "previous": {"VBG6": "VBG5"}}


def test_vbg6_is_a_test_only_setting_of_every_j_p3_input() -> None:
    """Erratum 1 2: one ``VBG6`` row makes the whole J-P3 input a setting defect."""
    assert inputs.is_test_only_setting("VBG6") and inputs.is_test_only_setting("VBG5")
    assert inputs.is_test_only_setting("LSJ4_X11") and not inputs.is_test_only_setting("VBJ")


def test_p51_x11_always_equal_and_vbg6_pairs_with_vbg5(tmp_path) -> None:
    """Erratum 1 1: the X11 hash equals 78fd5d2d's whatever the fallbacks; 2: VBG6 against
    the edition 4a VBG5 job, equal when neither side has a fallback, else recorded."""
    fallback = [[3.0, "WARN_ROD_PRESSURE_FALLBACK:FR"]]

    def row(setting, sha, events=()):
        return {"job": {"case": "R12", "eps": 0.0, "setting": setting, "mask": 3},
                "commands_sha256": sha, "events": [list(event) for event in events]}

    report = p51.compare([row("LSJ4_X11", A, fallback)], [row("LSJ4_X11", B, fallback)], None,
                         None)
    assert report["status"] == "differ" and report["judged_pairs"] == 1
    report = p51.compare([row("VBG5", A)], [row("VBG6", B)], None, None)
    assert report["status"] == "differ" and report["pairs"] == 1
    report = p51.compare([row("VBG5", A)], [row("VBG6", B, fallback)], None, None)
    assert report["fallback_pairs_recorded"] == 1 and report["differing_pairs"] == 0
    report = p51.compare([row("VBG5", A)], [row("VBG6", A)], None, None)
    assert report["status"] == "pass"


def test_p52_reads_cases_a_to_f_only(tmp_path) -> None:
    check = {"rule_revision": 6, "jp3a_breach_reads": [0] * 4,
             "jp3b_breach_over_tol_reads": [0] * 4, "jp3c_breach_reads": [0] * 4,
             "jp3_r58_witness_carries": [0] * 4, "jp3_r59_substeps": [0] * 4,
             "jp3_r510_candidates": [0] * 4}
    rows = tmp_path / "rows.jsonl"
    rows.write_text("".join(json.dumps(line) + "\n" for line in (
        {"job": {"case": "R12", "setting": "VBG6"},
         "hydraulics_record": {"extend_bound_check": check}},
        {"job": {"case": "R12", "setting": "LSJ4_X11"},
         "hydraulics_record": {"extend_bound_check": {"rule_revision": 5}}})),
        encoding="utf-8")
    report = p5.p52([rows])
    assert [row["setting"] for row in report["rows"]] == ["VBG6"]
    assert report["excluded_rows"][0]["setting"] == "LSJ4_X11" and report["problems"] == []


# ------------------------------------------------------------------------------- 4 / 8
def test_t_jr_13_takes_revision_6_reports_only() -> None:
    problems = tjr.compare.Problems()
    tjr.judge_t_jr_13([dict(report) for report in REPLAY_REPORTS], T4H_NAMES, problems)
    assert problems.not_judgeable == []
    problems = tjr.compare.Problems()
    tjr.judge_t_jr_13([{**report, "extend_start_revision": 5} for report in REPLAY_REPORTS],
                      T4H_NAMES, problems)
    assert len([text for text in problems.not_judgeable if "extend_start_revision 5" in text]) == 2


def test_p54_discloses_the_proxy_and_its_gains() -> None:
    """Erratum 2 2-2 (erratum 1 8 made exact): front 3.521 / rear 3.025, 1.327 / 0.950 kN per
    head-reading bar."""
    disclosure = p5.proxy_disclosure()
    assert disclosure["head_error_gain"] == {"front": 3.521, "rear": 3.025}
    assert disclosure["max_over_kN_per_head_bar"] == {"front": 1.327, "rear": 0.95}
    assert "front 3.521, rear 3.025" in disclosure["text"]
    assert "front 1.327 kN, rear 0.950 kN" in disclosure["text"]
    assert disclosure["judged"] is False and disclosure["dominated_reads_use_it"] is False
    assert "A_ann" in disclosure["definition"]


# ------------------------------------------------------------------------------- 9.1
def test_dry_key_file_sha_constants_are_the_erratum_table() -> None:
    for family, (key, sha) in KEY_FILE_TABLE.items():
        assert hashlib.sha256((key + "\r\n").encode("utf-8")).hexdigest() == sha, family
        assert fixed.DRY_KEYS_FILE_SHA256_BY_FAMILY[family] == sha, family
    assert fixed.DRY_KEYS_FILE_SHA256_G8 == KEY_FILE_TABLE["g8"][1]
    assert fixed.DRY_KEYS_FILE_SHA256_REF == KEY_FILE_TABLE["ref"][1]


def test_dry_family_key_file_of_another_key_stops(tmp_path) -> None:
    written = dryrun.write_family_keys_file(tmp_path / "g8.txt", KEY_FILE_TABLE["g8"][0], "g8")
    assert written["sha256"] == KEY_FILE_TABLE["g8"][1]
    with pytest.raises(dryrun.Stop, match="not the fixed"):
        dryrun.write_family_keys_file(tmp_path / "ref.txt", "L2|s26|ref|0|rigid|B|0,0", "ref")
    with pytest.raises(dryrun.Stop, match="never overwritten"):
        dryrun.write_family_keys_file(tmp_path / "g8.txt", KEY_FILE_TABLE["g8"][0], "g8")


def test_summary_refuses_a_g8_key_file_of_another_sha(tmp_path) -> None:
    events, r79 = _summary_files(tmp_path)
    selection = json.loads(json.dumps(SELECTION))
    selection["r79_families"]["g8"]["keys_file"]["sha256"] = "8" * 64
    summary, code = dryrun.summarize(selection, events, r79)
    assert code == dryrun.EXIT_NOT_JUDGEABLE
    assert any(row.get("keys_file_problems") for row in summary["rows"]
               if row["run"].endswith("_g8"))


# ------------------------------------------------------------------------------- 9.2 (다)
def _with_t4h(tmp_path: Path, drop: str | None = None) -> tuple[dict, dict, dict]:
    """The summary inputs with a T4h record per r79 line (``drop``: one array left out)."""
    events, r79 = _summary_files(tmp_path)
    folders = {name: tmp_path / f"{name.replace(':', '_')}_t4h" for name in r79}
    for name, path in r79.items():
        folders[name].mkdir()
        document = json.loads(path.read_text(encoding="utf-8"))
        record = document["results"][0]
        record["t4h_file"] = "cand_current_L2_s25.npz"  # the same name in every folder
        arrays = {array: np.zeros((3, 4), np.int32) for array in dryrun.T4H_REQUIRED_ARRAYS}
        arrays["meta_json"] = np.array(json.dumps({"events": []}))
        if drop is not None and name == "VBH":
            arrays.pop(drop)
        np.savez(folders[name] / record["t4h_file"], **arrays)
        path.write_text(json.dumps(document), encoding="utf-8")
    return events, r79, folders


def test_dry_t4h_holds_the_rev6_arrays_and_events(tmp_path) -> None:
    events, r79, folders = _with_t4h(tmp_path)
    summary, code = dryrun.summarize(SELECTION, events, r79, folders)
    assert code == dryrun.EXIT_DONE, summary
    assert all(row.get("t4h_problems") == [] for row in summary["rows"] if "family" in row)


@pytest.mark.parametrize("drop", ["jp3_r59_end_guard_substeps", "meta_json"])
def test_dry_t4h_without_an_array_or_events_is_not_judgeable(tmp_path, drop) -> None:
    events, r79, folders = _with_t4h(tmp_path, drop)
    summary, code = dryrun.summarize(SELECTION, events, r79, folders)
    assert code == dryrun.EXIT_NOT_JUDGEABLE
    problems = [problem for row in summary["rows"] if row["run"] == "r79_VBH"
                for problem in row["t4h_problems"]]
    assert problems and all(("missing" in text) for text in problems)


def test_dry_summarize_edition_5_needs_every_t4h_folder(tmp_path, monkeypatch, capsys) -> None:
    events, r79, folders = _with_t4h(tmp_path)
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps(SELECTION), encoding="utf-8")
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    base = ["summarize", "--selection", str(selection), "--edition", "5",
            "--event", *[f"{k}={v}" for k, v in events.items()],
            "--r79", *[f"{k}={v}" for k, v in r79.items()]]
    every = [f"{name}={folder}" for name, folder in folders.items()]
    assert len(every) == 6
    code = dryrun.main([*base, "--out", str(tmp_path / "s1.json"), "--r79-t4h", *every])
    assert code == dryrun.EXIT_DONE, (tmp_path / "s1.json").read_text(encoding="utf-8")
    code = dryrun.main([*base, "--out", str(tmp_path / "s2.json"), "--r79-t4h", *every[:5]])
    assert code == dryrun.EXIT_NOT_JUDGEABLE


# ------------------------------------------------------------------------------- seed rule
def test_seed_rule_12b_blocks_start_at_40_and_c_dry_stays_90_91() -> None:
    """Erratum 1 seed rule 1 / 4: b1 .. b4 start at 40 .. 43 (30 .. 33 never again: a raise
    only adds 10), the c dry seeds stay 90 / 91."""
    import jp3_12b_plan as plan

    assert plan.BLOCK_SEEDS == (40, 41, 42, 43) and plan.SEED_STEP == 10
    assert plan.DRY_SEEDS == (90, 91)
    seeds, repeats = plan.block_seeds(["L2|g6|0|x"], frozenset({"L2|s41|g6|0|x"}))
    assert seeds == (50, 51, 52, 53) and repeats == 1


HARNESS_KEY_FILES = ("test_x10_rod_fault.py",)
"""The unit tests that run r79 keys through the harness (X-10)."""
KEY_LITERAL = re.compile(r"""["']((?:cand=[^"'#\s]*#)?L\d+[A-Za-z]*\|s(\d+)\|[^"'\s]*)["']""")


def test_seed_rule_harness_test_keys_use_s95_to_s99() -> None:
    """Erratum 1 seed rule 2: every r79 key a test runs through the harness has s95 .. s99."""
    for name in HARNESS_KEY_FILES:
        text = (Path(__file__).parent / name).read_text(encoding="utf-8")
        seeds = [int(seed) for _, seed in KEY_LITERAL.findall(text)]
        assert seeds and all(95 <= seed <= 99 for seed in seeds), (name, sorted(set(seeds)))


def test_seed_rule_05_tests_scan_is_12b_only(tmp_path) -> None:
    """Erratum 1 seed rule 3: the test-source scan is part of the 12b selection (a required
    ``--scan-extra``); the dry (X-4) scan reads its ``--scan-root`` alone, so the fixed test
    inputs ``s25`` / ``s26`` never push the dry seed."""
    import inspect

    import jp3_12b_plan as plan

    assert list(inspect.signature(dryrun.scan_r79_keys).parameters) == ["scan_root"]
    assert "scan_extra" not in inspect.getsource(dryrun)
    with pytest.raises(SystemExit):  # the 12b selection without --scan-extra
        plan.main(["--noise", "n", "--scan-root", str(tmp_path), "--out-dir", str(tmp_path)])


# ------------------------------------------------------------------------------- 6.6 list
def _git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(["git", "-C", str(repo), *arguments], capture_output=True,  # noqa: S603, S607
                               text=True, check=True, timeout=120)
    return completed.stdout.strip()


@pytest.fixture()
def list_repo(tmp_path, monkeypatch):
    """A repository with the inputs of one fixed list (code, data, X-11 and dry selections)."""
    repo = tmp_path / "repo"
    files = {"04_scripts/tool.py": "print(1)\n", "06_analysis/doc.md": "rule\n",
             fixed_list.NOISE_PATH: "{}\n"}
    for path, text in files.items():
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_bytes(text.encode("utf-8"))
    (repo / "06_analysis/doc.md.sha256").write_text(
        hashlib.sha256(b"rule\n").hexdigest() + "  doc.md\n", encoding="utf-8")
    x11 = repo / "06_analysis/x11"
    x11.mkdir()
    (x11 / "b1_plan.json").write_text("{}", encoding="utf-8")
    (x11 / "selection.json").write_text(json.dumps({"outputs": {
        "b1_plan.json": hashlib.sha256(b"{}").hexdigest()}}), encoding="utf-8")
    dry = repo / "06_analysis/dry"
    dry.mkdir()
    keys = {}
    for family, (key, _) in KEY_FILE_TABLE.items():
        keys[family] = dry / f"key_{family}.txt"
        keys[family].write_bytes((key + "\r\n").encode("utf-8"))
    (dry / "selection.json").write_text(json.dumps({
        "r79_keys_file": {"path": str(keys["g6"])},
        "r79_families": {family: {"keys_file": {"path": str(path)}}
                         for family, path in keys.items()}}), encoding="utf-8")
    entries = tmp_path / "entries.txt"
    entries.write_text("# comment\n04_scripts/tool.py\n06_analysis/doc.md*\n"
                       f"{fixed_list.NOISE_PATH}\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "-c", "core.autocrlf=false", "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x")
    monkeypatch.setattr(fixed_list.fixed, "NOISE_VB_SHA256", hashlib.sha256(b"{}\n").hexdigest())
    worktree = tmp_path / "run_worktree"  # the run checkout: clean at the run commit
    subprocess.run(["git", "clone", "-q", str(repo), str(worktree)], check=True,  # noqa: S603, S607
                   capture_output=True, timeout=120)
    return repo, entries, _git(repo, "rev-parse", "HEAD"), worktree


def _list_args(repo: Path, entries: Path, commit: str, out: Path, worktree: Path) -> list[str]:
    return ["--repo", str(repo), "--worktree", str(worktree), "--commit", commit, "--entries",
            str(entries), "--x11-selection", str(repo / "06_analysis/x11/selection.json"),
            "--dry-selection", str(repo / "06_analysis/dry/selection.json"), "--out", str(out)]


def test_fixed_list_lines_and_refusals(list_repo, tmp_path, monkeypatch) -> None:
    repo, entries, commit, worktree = list_repo
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    out = tmp_path / f"FIXED_INPUTS_{commit[:8]}.SHA256SUMS"
    l1_run = repo / "06_analysis" / "l1ref" / "L1_VBJ0.json"  # erratum 2 2-1: --add
    l1_run.parent.mkdir()
    l1_run.write_text("{}", encoding="utf-8")
    assert fixed_list.main([*_list_args(repo, entries, commit, out, worktree),
                            "--add", str(l1_run)]) == 0
    lines = out.read_bytes().decode("utf-8").split("\n")
    assert lines[-1] == "" and all(" *" in line for line in lines[:-1])
    paths = [line.split(" *", 1)[1] for line in lines[:-1]]
    assert paths[:4] == ["04_scripts/tool.py", "06_analysis/doc.md", "06_analysis/doc.md.sha256",
                         fixed_list.NOISE_PATH]
    assert {"06_analysis/x11/b1_plan.json", "06_analysis/dry/key_g8.txt",
            "06_analysis/l1ref/L1_VBJ0.json"} <= set(paths)
    assert fixed_list.main(_list_args(repo, entries, commit, out, worktree)) == 2  # exists

    def refused(name: str, change) -> None:
        change()
        target = tmp_path / f"{name}_{commit[:8]}.txt"
        assert fixed_list.main(_list_args(repo, entries, commit, target, worktree)) == 2, name
        assert not target.exists()

    tool = repo / "04_scripts/tool.py"
    refused("blob", lambda: tool.write_text("print(2)\n", encoding="utf-8"))  # not the blob
    tool.write_text("print(1)\n", encoding="utf-8")
    key_ref = repo / "06_analysis/dry/key_ref.txt"
    refused("key", lambda: key_ref.write_bytes(b"L2|s26|ref|0|rigid|B|0,0\r\n"))  # 9.1 sha
    key_ref.write_bytes((KEY_FILE_TABLE["ref"][0] + "\r\n").encode("utf-8"))
    sidecar = repo / "06_analysis/doc.md.sha256"
    refused("sidecar", lambda: sidecar.write_text("0" * 64 + "  doc.md\n", encoding="utf-8"))
    sidecar.write_text(hashlib.sha256(b"rule\n").hexdigest() + "  doc.md\n", encoding="utf-8")
    other = tmp_path / "z_00000000.txt"
    assert fixed_list.main(_list_args(repo, entries, "0" * 40, other, worktree)) == 2  # HEAD
    (worktree / "04_scripts/tool.py").write_text("dirty\n", encoding="utf-8")
    refused("dirty", lambda: None)  # the run worktree is not clean


# ------------------------------------------------------------------------------- 9.3
def _dry_folder(folder: Path, *, r79_hash=A, r79_fallback=False, vbj0_hash=A,
                vbj0_fallback=False, check_value=0, wall_s=1.0) -> Path:
    folder.mkdir(parents=True)
    for setting in ("VBJ", "VBH"):
        record = {"key": f"cand=current#{KEY_FILE_TABLE['g6'][0]}", "seed_index": 25,
                  "commands_sha256": r79_hash if setting == "VBJ" else A, "wall_s": wall_s,
                  "r79": {"rod_fallback": [[1.0, "FR"]] if (r79_fallback and setting == "VBJ")
                          else []},
                  "rod_fallback_reasons": [],
                  "hydraulics_record": {"rod_reading_truth_calls": [3, 0, 0, 0],
                                        "two_pressure_reads": [3, 0, 0, 0],
                                        "extend_bound_check": {"value": check_value}}}
        (folder / f"r79_{setting}.json").write_text(
            json.dumps({"meta": {"wall_s_this_start": wall_s}, "results": [record]}),
            encoding="utf-8")
    for setting in ("VBJ", "VBH", "VBJ0"):
        is_vbj0 = setting == "VBJ0"
        events = [[1.0, "WARN_ROD_PRESSURE_FALLBACK:FR"]] if (is_vbj0 and vbj0_fallback) else []
        row = {"job": {"case": "R14", "setting": setting, "mask": 3}, "wall_s": wall_s,
               "commands_sha256": vbj0_hash if is_vbj0 else A, "events": events,
               "hydraulics_record": {"rod_reading_truth_calls": 1, "two_pressure_reads": 1}}
        (folder / f"event_{setting}.jsonl").write_text(json.dumps(row) + "\n",
                                                       encoding="utf-8")
    return folder


def _compare(old: Path, new: Path, item: str = "dry5") -> tuple[dict, int]:
    report, code = rerun.compare_items([rerun.Side(old.parent, old, {})],
                                       rerun.Side(new.parent, new, {}), [item])
    return report["items"][item], code


@pytest.mark.parametrize(("change", "status", "recorded"), [
    ({}, "same", []),
    ({"r79_hash": B}, "differs", []),
    ({"r79_hash": B, "r79_fallback": True}, "same", ["r79_VBJ.json commands_sha256"]),
    ({"vbj0_hash": B, "vbj0_fallback": True}, "differs", []),
    ({"check_value": 7, "wall_s": 9.0}, "same", []),
])
def test_dry5_against_78fd5d2d(tmp_path, change, status, recorded) -> None:
    """9.3: the g6 r79 lines and the event hashes under the P5-1 rule; VBJ0 equal whatever
    the fallbacks; ``extend_bound_check`` and run meta not compared."""
    old = _dry_folder(tmp_path / "old" / "dry_a1")
    new = _dry_folder(tmp_path / "new" / "dry_a1", **change)
    entry, code = _compare(old, new)
    assert entry["status"] == status, entry
    assert entry["by_old"]["old"]["recorded_only"] == recorded
    assert code == rerun.EXIT_OF_STATUS[status]
    assert not any(name.endswith((rerun.FALLBACK_SUFFIX, rerun.ALWAYS_EQUAL_SUFFIX))
                   for name in entry["compared"])


def test_compare_problems_status_order() -> None:
    """Erratum 2 2-10 for the T8 / case / T-JR judges (``jp3_baseline_compare.Problems``)."""
    problems = tjr.compare.Problems()
    problems.setting_defects.append("d")
    problems.not_judgeable.append("n")
    assert problems.status() == tjr.compare.STATUS_SETTING_DEFECT
    problems.failures.append("f")
    assert problems.status() == tjr.compare.STATUS_FAILED
    assert problems.as_dict()["setting_defects"] == ["d"]


def test_p51_differ_outranks_the_problems() -> None:
    """Erratum 2 2-10: a differing judged pair with a one-sided row is ``differ`` (exit 1),
    the problem kept; the one-sided row alone stays not judgeable."""
    job = {"setting": "VBJ0", "case": "x"}
    old = [{"job": job, "commands_sha256": "a" * 64}]
    new = [{"job": job, "commands_sha256": "b" * 64},
           {"job": {"setting": "VBJ0", "case": "y"}, "commands_sha256": "a" * 64}]
    report = p51.compare(old, new, None, None)
    assert report["status"] == "differ" and report["problems"]
    same = p51.compare(old, [{"job": job, "commands_sha256": "a" * 64}, new[1]], None, None)
    assert same["status"] == "not_judgeable"


def test_rerun_match_differs_outranks_missing(monkeypatch) -> None:
    """Erratum 2 2-10: one item differs, another misses an input: exit 1, the missing item
    kept as missing; a missing input alone stays exit 2."""
    values = {("old", "a"): {"x": 1}, ("new", "a"): {"x": 2}, ("old", "b"): None,
              ("new", "b"): {"y": 1}}

    def item_values(side, item):
        found = values[(side.root.name, item)]
        if found is None:
            raise rerun.Missing("no file")
        return found
    monkeypatch.setattr(rerun, "item_values", item_values)

    class Side:
        def __init__(self, name: str) -> None:
            self.root = Path(name)
    report, code = rerun.compare_items([Side("old")], Side("new"), ["a", "b"])
    assert code == rerun.EXIT_DIFFERS
    assert report["items"]["a"]["status"] == "differs"
    assert report["items"]["b"]["status"] == "missing"
    _, code = rerun.compare_items([Side("old")], Side("new"), ["b"])
    assert code == rerun.EXIT_MISSING


def test_rerun_match_nonzero_baseline_code_is_not_judgeable(monkeypatch) -> None:
    """Erratum 2 2-10.1 4: a baseline tool exit code not 0 is never compared (exit 2)."""
    values = {"old": {"code tool:case_f": 2, "x": 1}, "new": {"code tool:case_f": 2, "x": 1}}
    monkeypatch.setattr(rerun, "item_values", lambda side, item: dict(values[side.root.name]))

    class Side:
        def __init__(self, name: str) -> None:
            self.root = Path(name)
    report, code = rerun.compare_items([Side("old")], Side("new"), ["casef"])
    assert code == rerun.EXIT_MISSING and report["items"]["casef"]["status"] == "missing"
    assert report["items"]["casef"]["by_old"]["old"]["nonzero_baseline_codes"] == [
        "code tool:case_f"]
    values["old"]["code tool:case_f"] = values["new"]["code tool:case_f"] = 0
    _, code = rerun.compare_items([Side("old")], Side("new"), ["casef"])
    assert code == rerun.EXIT_SAME


def _hold_row(breaches: int = 0, **record) -> dict:
    check = {"rule_revision": 6, "spec_edition": "fe6f5844",
             "carry_end_rule": "inherit_when_gate_shut", "retract_start_rule": "with_tracker",
             "identity_consistent": True, "sensor_grade": "normal",
             "jp3a_breach_reads": [breaches, 0, 0, 0], "jp3b_breach_over_tol_reads": [0] * 4,
             "jp3c_breach_reads": [0] * 4, **record}
    return {"p3_expected": True, "run_extend_start_rule": "tracked_bound",
            "run_extend_start_revision": 6, "setting": "VBJ", "extend_bound_check": check}


def _dg3_lines(*records: dict) -> list[dict]:
    return [{"hydraulics_record": {"extend_bound_check": record}} for record in records]


def test_dg3_j_p3_reads_h7_under_a_defect() -> None:
    """Re-audit K-1 / 2-10.1 5: the T-JR-12a VBJ J-P3 reads H-7 from its judged row although a
    defect row makes the combined status setting_defect; the defect stays a reason."""
    breach, defect = _hold_row(breaches=1), _hold_row(carry_end_rule="fresh_stretch")
    problems = tjr.compare.Problems()
    record = tjr._dg3_j_p3(_dg3_lines(breach["extend_bound_check"],
                                      defect["extend_bound_check"]), problems)
    assert record["status"] == "setting_defect"
    assert record["h7_from_judged_rows"] is True and record["outcome"] == "H-7"
    assert problems.failures == ["VBJ: J-P3 H-7"]
    assert problems.setting_defects == ["VBJ: J-P3 setting defect"]
    clean = tjr._dg3_j_p3(_dg3_lines(_hold_row()["extend_bound_check"]), tjr.compare.Problems())
    assert (clean["outcome"], clean["h7_from_judged_rows"]) == ("pass", False)


@pytest.mark.parametrize(("outcome", "failures"), [("pass", ["VBJ: 1 new_fault keys"]),
                                                   ("H-7", ["VBJ: J-P3 H-7"])])
def test_t12_vbj_report_carries_the_jp3_outcome(tmp_path, monkeypatch, capsys, outcome,
                                               failures) -> None:
    """K-1: the t12 VBJ report holds ``jp3_outcome`` apart from the 13.9 record; both cases
    exit 1 (a record failure / the J-P3 failure) - the run step tells them apart."""
    def judge_t12(bundle, base, base_judge, new, new_judge):
        problems = tjr.compare.Problems()
        problems.failures += failures
        return {"J-P3": {"outcome": outcome}}, problems
    monkeypatch.setattr(tjr, "judge_t12", judge_t12)
    for name in ("t12_input_problems", "judge_sha_problems", "t12_judge_row_problems",
                 "t12_file_defects"):
        monkeypatch.setattr(tjr, name, lambda *args, **kwargs: [])
    monkeypatch.setattr(tjr, "_read_json", lambda path: {})
    out = tmp_path / "t12_VBJ.json"
    code = tjr.main(["t12", "--bundle", "VBJ", "--base", "b.json", "--base-judge", "bj.json",
                     "--base-judge-sha256", "a" * 64, "--new", "n.json", "--new-judge",
                     "nj.json", "--new-judge-sha256", "b" * 64, "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == 1 and report["jp3_outcome"] == outcome
    capsys.readouterr()


GATES_PS1 = (ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "prelaunch_j9"
             / "run_steps_ed5" / "record_gates_ed5.ps1")


def _gate(tmp_path: Path, report: dict, *, vbj: bool = True, call: str | None = None) -> str:
    """Run a gate of ``record_gates_ed5.ps1`` alone on a report (pwsh): ``Get-RecordToolStop``
    or ``call`` (a command with ``{report}`` for the report path)."""
    import shutil

    pwsh = shutil.which("pwsh")
    assert pwsh is not None, "pwsh (PowerShell 7) is needed for the run step gate tests"
    index = len(list(tmp_path.glob("gate_*.json")))
    report_path = tmp_path / f"gate_{index}.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    script = tmp_path / f"gate_{index}.ps1"
    switch = " -VbjJp3" if vbj else ""
    command = (f"Get-RecordToolStop '{report_path}'{switch}" if call is None
               else call.format(report=f"'{report_path}'"))
    script.write_text(
        f". '{GATES_PS1}'\n$Stop = {command}\n"
        "if ($Stop) { Write-Output \"$($Stop.code)|$($Stop.reason)\" }\n"
        "else { Write-Output 'go' }\n",
        encoding="utf-8")
    done = subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-File", str(script)],
                          capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip().splitlines()[-1]


RECORD_FAILURE = "VBJ: 1 new_fault keys"
JP3_BLOCK = {"status": "pass", "runs_judged": 1}


def _vbj_report(**changes) -> dict:
    report = {"jp3_outcome": "pass", "J-P3": dict(JP3_BLOCK), "failures": [],
              "record_failures": [], "setting_defects": [], "not_judgeable": []}
    report.update(changes)
    return report


def test_record_gate_13_9_record_failure_alone_goes_on(tmp_path) -> None:
    """Erratum 3 3-1 (4): a 13.9 record failure only - go on (VBJ and VBH)."""
    report = _vbj_report(failures=[RECORD_FAILURE], record_failures=[RECORD_FAILURE])
    assert _gate(tmp_path, report) == "go"
    vbh = {key: value for key, value in report.items() if key not in ("jp3_outcome", "J-P3")}
    assert _gate(tmp_path, vbh, vbj=False) == "go"


def test_record_gate_vbj_jp3_h7_with_a_defect_stops_1(tmp_path) -> None:
    """3-1 (1): VBJ J-P3 H-7 (read from its judged rows) with a setting defect: exit 1."""
    report = _vbj_report(jp3_outcome="H-7", failures=["VBJ: J-P3 H-7"],
                         setting_defects=["VBJ: J-P3 setting defect"],
                         **{"J-P3": {"status": "setting_defect", "runs_judged": 1}})
    assert _gate(tmp_path, report).startswith("1|")


def test_record_gate_vbj_without_a_jp3_judgement_stops_2(tmp_path) -> None:
    """3-1 (2): no J-P3 block, a block without its keys, or 0 judged rows: exit 2."""
    no_block = {key: value for key, value in _vbj_report().items() if key != "J-P3"}
    assert _gate(tmp_path, {**no_block, "jp3_outcome": "not_computed"}).startswith("2|")
    assert _gate(tmp_path, _vbj_report(**{"J-P3": {"status": "pass"}})).startswith("2|")
    zero = _vbj_report(**{"J-P3": {"status": "no_judged_runs", "runs_judged": 0}})
    assert _gate(tmp_path, zero).startswith("2|")


def test_record_gate_record_failure_with_a_setting_defect_stops_2(tmp_path) -> None:
    """3-1 (3): a 13.9 record failure and a setting defect: exit 2."""
    report = _vbj_report(failures=[RECORD_FAILURE], record_failures=[RECORD_FAILURE],
                         setting_defects=["new k: line evidence"])
    assert _gate(tmp_path, report).startswith("2|")
    assert _gate(tmp_path, {**report, "setting_defects": [], "not_judgeable": ["x"]}
                 ).startswith("2|")


def test_record_gate_failure_outside_the_record_list_stops_2(tmp_path) -> None:
    """3-1 closed list: a failure not in ``record_failures`` is an input defect (exit 2); a
    report without the lists is a tool error (3)."""
    report = _vbj_report(failures=[RECORD_FAILURE, "VBJ: something else"],
                         record_failures=[RECORD_FAILURE])
    assert _gate(tmp_path, report).startswith("2|")
    without = {key: value for key, value in _vbj_report().items() if key != "record_failures"}
    assert _gate(tmp_path, without).startswith("3|")


GRADE_DIFFERENCE = "stored r79 judge: 2 keys of other grades (record)"
"""A base-judge-compare R-2 failure (``_grade_differences``)."""


def _compare_report(failures: list[str]) -> dict:
    return {"failures": failures, "record_failures": [], "setting_defects": [],
            "not_judgeable": []}


@pytest.mark.parametrize("match_item", ["p1", "p1_content"])
def test_p1_grade_difference_stops_2_on_both_paths(tmp_path, match_item) -> None:
    """Erratum 3 3-1 (sealed 7bab9217): "sha 경로 + 등급 차이 -> P-1 종료 2" and "내용 경로 +
    등급 차이 -> P-1 종료 2" (base-judge-compare exit 1, its R-2 difference no record)."""
    report = _compare_report([GRADE_DIFFERENCE])
    call = f"Get-P1CompareStop {{report}} 1 '{match_item}'"
    assert _gate(tmp_path, report, call=call).startswith("2|")
    clean = f"Get-P1CompareStop {{report}} 0 '{match_item}'"
    assert _gate(tmp_path, _compare_report([]), call=clean) == "go"
    assert _gate(tmp_path, report, call="Get-P1CompareStop {report} 1 'other'").startswith("3|")
    # the same report through the record gate alone: outside the record list, an input defect
    assert _gate(tmp_path, report, vbj=False).startswith("2|")


def test_base_judge_compare_has_no_record_failures(tmp_path, monkeypatch, capsys) -> None:
    """3-1: the R-2 grade difference stays out of ``record_failures`` (exit 1 of the tool)."""
    def compare_base_judges(inputs):
        problems = tjr.compare.Problems()
        problems.failures.append(GRADE_DIFFERENCE)
        return {"record_only": "R-2"}, problems, []
    monkeypatch.setattr(tjr, "compare_base_judges", compare_base_judges)
    out = tmp_path / "h6_judge_compare.json"
    code = tjr.main(["base-judge-compare", "--h6", "h6.json", "--new-judge", "nj.json",
                     "--new-judge-sha256", "a" * 64, "--stored-judge", "sj.json",
                     "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == 1 and report["record_failures"] == []
    assert report["failures"] == [GRADE_DIFFERENCE]
    capsys.readouterr()


def test_record_failure_and_a_failure_outside_the_list_stop_2(tmp_path, monkeypatch) -> None:
    """Audit item 2 (erratum 3 3-1): the gate tells records by string equality, so a real t12
    13.9 failure must be the same string in ``failures`` and ``record_failures``; with it a
    failure outside the list stops 2, alone the record goes on."""
    import h8_noise_judge_4368 as h8
    from test_jp3_addendum_4a2 import _dg3_document

    monkeypatch.setattr(h8, "grade_lines", lambda results, judge: {
        h8.plain_key(run["key"]): {"grade": h8.GRADE_PASS, "level": run["level"]}
        for run in results})
    report, problems = tjr.judge_t12("VBH", _dg3_document(setting="VB"), {},
                                     _dg3_document(fault="FAULT_NEW"), {})
    assert problems.failures and report["record_failures"] == problems.failures
    written = {**report, **problems.as_dict()}
    assert _gate(tmp_path, written, vbj=False) == "go"
    outside = {**written, "failures": [*problems.failures, "VBH: something else"]}
    assert _gate(tmp_path, outside, vbj=False).startswith("2|")


def test_worse_status_default_order_unchanged() -> None:
    """2-10.1 5 (coordinator item 3): the sealed tools' order stays; edition 5 passes its own."""
    assert inputs._worse_status("H-7", "setting_defect") == "setting_defect"
    assert inputs._worse_status("H-7", "no_judged_runs") == "no_judged_runs"
    assert inputs._worse_status("H-7", "setting_defect", inputs.STATUS_ORDER_ED5) == "H-7"
    assert inputs._worse_status("pass", "no_judged_runs", inputs.STATUS_ORDER_ED5) == (
        "no_judged_runs")


def test_j_p3_over_rows_edition5_order_reads_h7_first() -> None:
    """A breach on a judged rev 6 row and a defect row: default setting_defect (sealed order,
    unchanged); edition 5 order H-7 with the defect kept in the revision judgement."""
    rows = [_hold_row(breaches=1), _hold_row(carry_end_rule="fresh_stretch")]
    default = inputs.j_p3_over_rows([dict(row) for row in rows])
    assert default["status"] == "setting_defect"
    assert default["status_by_revision"]["6"] == "setting_defect"
    edition5 = inputs.j_p3_over_rows([dict(row) for row in rows], edition5_order=True)
    assert edition5["status"] == "H-7" and edition5["status_by_revision"]["6"] == "H-7"
    assert edition5["rev6"]["status"] == "setting_defect"  # the revision's own result kept
    assert inputs.has_judged_breach(edition5["rev6"])
    clean = inputs.j_p3_over_rows([_hold_row()], edition5_order=True)
    assert clean["status"] == "pass"
    unkeyed = {key: value for key, value in _hold_row(breaches=1).items()
               if key != "run_extend_start_revision"}
    mixed = inputs.j_p3_over_rows([_hold_row(breaches=1), unkeyed], edition5_order=True)
    assert mixed["status"] == "H-7" and mixed["revision_key_missing_runs"] == 1


def test_dry5_retry_compares_whole_lines_without_run_meta(tmp_path) -> None:
    first = _dry_folder(tmp_path / "run" / "dry_a1")
    entry, _ = _compare(first, _dry_folder(tmp_path / "run2" / "dry_a2", wall_s=5.0),
                        "dry5_retry")
    assert entry["status"] == "same"
    entry, _ = _compare(first, _dry_folder(tmp_path / "run3" / "dry_a2", check_value=1),
                        "dry5_retry")
    assert entry["status"] == "differs"


def test_rerun_match_old_folder_option(tmp_path, monkeypatch) -> None:
    old = _dry_folder(tmp_path / "commit" / "dry_a1")
    new = _dry_folder(tmp_path / "commit" / "dry_a2")
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    codes = tmp_path / "codes.json"
    codes.write_text("{}", encoding="utf-8")
    out = tmp_path / "retry.json"
    code = rerun.main(["--old", str(old.parent), "--old-folder", str(old), "--new",
                       str(new.parent), "--new-folder", str(new), "--new-codes", str(codes),
                       "--items", "dry5_retry", "--out", str(out)])
    assert code == rerun.EXIT_SAME, out.read_text(encoding="utf-8")
    with pytest.raises(SystemExit):
        rerun.main(["--old", str(old.parent), "--old-folder", str(old), "--new",
                    str(new.parent), "--items", "dry", "--out", str(tmp_path / "x.json")])
