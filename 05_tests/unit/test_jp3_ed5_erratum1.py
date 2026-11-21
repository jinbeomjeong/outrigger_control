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
    assert code == rerun.STATUS_RANK[status]
    assert not any(name.endswith((rerun.FALLBACK_SUFFIX, rerun.ALWAYS_EQUAL_SUFFIX))
                   for name in entry["compared"])


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
