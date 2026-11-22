"""Smoke check: dependencies import, and each tool runs once on a tiny fixture.

Tools: seal_check, gate_scan, record_check (identity, recount), timeline,
replay_recount, log_errors and placeholder_scan (2026-11-11),
threshold_boundary and missing_scan (2026-11-15), ps1_lint (regex parser, so
no PowerShell is needed) and handoff_leak (2026-11-16), baseline_check (sums,
identity), ref_check (``--no-git``) and junit_skips (2026-11-17), gate_scan on a
missing-key default and junit_skips on an xfail (2026-11-20; these two runs also
check that their category appears in the summary), placeholder_scan with
``--pattern-set angle``, key_presence (all present / one key absent),
baseline_check sums with ``--base repo-root`` and the default base's
``sums_base_hint``, gate_scan on a record value opened with no base folder
(2026-11-21; the runs with a category check it in the summary), worktree_tests
on a two-file worktree inside its data root, run with this interpreter's pytest
(2026-11-22, category ``probe_worktree``).

Prints one JSON object; its last key is ``"status"`` (``"ok"`` or ``"fail"``).
Exit code 0 when every tool returned its expected exit code (and category),
otherwise 1.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
RUN_TIMEOUT_S = 60
DEPENDENCIES = ("numpy",)

RULE_TEXT = "# 규칙\n\n작성: smoke, 2001-01-01.\n"
RESULTS_TEXT = (
    '{"job": {"setting": "V0"}, "d1": {"verdict": "pass", "F_N": 12000.0}}\n'
    '{"job": {"setting": "V0"}, "d1": {"verdict": "pass", "F_N": 11000.0}}\n'
)
GATE_TEXT = 'def judge(rows):\n    return {"pass": all(rows)}\n'
MISSING_KEY_TEXT = (
    "def judge(rows, check):\n"
    '    keys = ["a", "b"]\n'
    "    total = sum(sum(check.get(k) or [0]) for k in keys)\n"
    '    return {"pass": total == 0}\n'
)
XFAIL_JUNIT_TEXT = (
    '<testsuite><testcase classname="t" name="test_prediction">'
    '<skipped type="pytest.xfail" message="known gap"/></testcase>'
    '<testcase classname="t" name="test_ok"/></testsuite>\n'
)
SOURCE_TEXT = (
    '{"rev": {"key": "k1"}, "commands_sha256": "h1"}\n'
    '{"rev": {"key": "k2"}, "commands_sha256": "h2"}\n'
)
REPLAY_TEXT = '{"key": "k1", "hash": "h1"}\n{"key": "k2", "hash": "h2"}\n'
LOG_TEXT = "done out.json errors 0\n"
MANIFEST_TEXT = '{"row_json": "C:\\\\batch\\\\row.json"}\n'
SCORES_TEXT = "fold,score\n0,0.2500\n0,0.9000\n"
PS1_TEXT = "$Grid = @('a')\nforeach ($grid in 'b') { $grid }\nWrite-Output $Grid\n"
NAMES_TEXT = '{"files": ["judge_secret.py"]}\n'
HANDOFF_TEXT = "<!-- 공통 시작 -->\n본문\n<!-- 공통 끝 -->\n- judge_secret.py\n"
IDENTITY_TEXT = (
    json.dumps(
        {
            "start": [
                {
                    "time": "2001-01-01 00:00:00 +0900",
                    "git": {"head": "a" * 40, "is_clean": True},
                }
            ]
        }
    )
    + "\n"
)
SPEC_TEXT = "# 명세\n\n- 규칙 `rules/s_rules.md`, 키 `keys_missing.txt`\n"
ANGLE_STEPS_TEXT = '{"argv": ["--out", "<prelaunch>\\\\p1a.json"]}\n'
ROW_PATH_TEXT = (
    "from pathlib import Path\n\n\n"
    "def compare(new):\n"
    '    return Path(new["t4h_file"]).read_bytes()\n'
)
WORKTREE_TEST_TEXT = (
    "from pathlib import Path\n\n"
    "import smoke_probe_mod\n\n"
    "ROOT = Path(__file__).resolve().parents[1]\n\n\n"
    "def test_stored():\n"
    '    assert (ROOT / "07_results" / "a.txt").read_text(encoding="utf-8") == "x"\n'
    "    assert smoke_probe_mod.VALUE == 1\n"
)
FIXTURE_FOLDERS = (
    "rules", "results", "code", "code_keys", "code_paths", "replay", "logs",
    "scripts", "handoff", "baseline", "baseline_root", "docs",
    "wt_main/07_results", "wt_main/wt/tests", "wt_scratch",
)  # fmt: skip
JUNIT_TEXT = (
    '<testsuite><testcase classname="t" name="test_ok"/>'
    '<testcase classname="t" name="test_records">'
    '<skipped message="records not present"/>'
    "</testcase></testsuite>\n"
)
# Tool -> (arguments with {folder} placeholders, expected exit code).
RUNS = {
    "seal_check.py": (["{folder}/rules/s_rules.md", "--no-git"], 1),
    "gate_scan.py": (["{folder}/code"], 1),
    "record_check.py identity": (
        ["identity", "{folder}/results/r.jsonl", "--uniform", "job.setting"],
        0,
    ),
    "record_check.py recount": (
        [
            "recount",
            "{folder}/results/r.jsonl",
            "--min",
            "d1.F_N",
            "--expect",
            "min=11000",
        ],
        0,
    ),
    "timeline.py": (
        [
            "--rules",
            "{folder}/rules/s_rules.md",
            "--results",
            "{folder}/results/r.jsonl",
            "--no-git",
            "--fail-on",
            "error",
        ],
        0,
    ),
    "replay_recount.py": (
        [
            "--replay",
            "{folder}/replay/replay.jsonl",
            "--source",
            "{folder}/results/source.jsonl",
            "--source-key",
            "rev.key",
            "--expect",
            "hash_same=2",
        ],
        0,
    ),
    "log_errors.py": (["{folder}/logs"], 0),
    "placeholder_scan.py": (["--repo", "{folder}", "results/manifest.json"], 0),
    "threshold_boundary.py": (
        [
            "{folder}/results/scores.csv",
            "--score",
            "score",
            "--threshold",
            "0.25",
            "--op",
            ">",
            "--group-by",
            "fold",
        ],
        1,
    ),
    "missing_scan.py": (["{folder}/results", "--preset", "v5-resume-4368"], 0),
    "ps1_lint.py": (["{folder}/scripts/run.ps1", "--parser", "regex"], 1),
    "handoff_leak.py": (
        ["{folder}/handoff/h.md", "--names", "{folder}/names.json", "--blocks"],
        1,
    ),
    "baseline_check.py sums": (["sums", "{folder}/baseline/SHA256SUMS", "--no-git"], 0),
    "baseline_check.py identity": (
        ["identity", "{folder}/baseline", "--expect-commit", "aaaaaaa", "--no-git"],
        0,
    ),
    "ref_check.py": (["--repo", "{folder}", "docs/spec.md", "--no-git"], 1),
    "junit_skips.py": (["{folder}/junit.xml", "--critical", "test_records"], 1),
    "gate_scan.py missing_key": (["{folder}/code_keys"], 1),
    "junit_skips.py xfail": (["{folder}/junit_xfail.xml"], 1),
    "placeholder_scan.py angle": (
        ["--repo", "{folder}", "results/steps.json", "--pattern-set", "angle"],
        1,
    ),
    "key_presence.py": (
        ["{folder}/results/r.jsonl", "--key", "job.setting,d1.verdict"],
        0,
    ),
    "key_presence.py absent": (
        ["{folder}/results/r.jsonl", "--key", "d1.not_recorded"],
        1,
    ),
    "baseline_check.py sums repo-root": (
        [
            "sums",
            "{folder}/baseline_root/SHA256SUMS",
            "--base",
            "repo-root",
            "--repo",
            "{folder}",
            "--no-git",
        ],
        0,
    ),
    "baseline_check.py sums hint": (
        ["sums", "{folder}/baseline_root/SHA256SUMS", "--repo", "{folder}", "--no-git"],
        1,
    ),
    "gate_scan.py row_paths": (["{folder}/code_paths"], 1),
    "worktree_tests.py": (
        [
            "--worktree",
            "{folder}/wt_main/wt",
            "--data-root",
            "{folder}/wt_main",
            "--python",
            "{python}",
            "--scratch",
            "{folder}/wt_scratch",
            "--test",
            "tests/test_stored.py",
            "--probe-module",
            "smoke_probe_mod",
        ],
        0,
    ),
}
# Run label -> a category its summary must contain.
EXPECTED_CATEGORIES = {
    "gate_scan.py missing_key": "missing_key_default_pass",
    "junit_skips.py xfail": "xfailed",
    "placeholder_scan.py angle": "placeholder_unfilled",
    "key_presence.py absent": "key_absent",
    "baseline_check.py sums hint": "sums_base_hint",
    "gate_scan.py row_paths": "row_value_path_no_base",
    "worktree_tests.py": "probe_worktree",
}


def _dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in DEPENDENCIES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "missing (npz is skipped)"
    return versions


def _write_baseline(folder: Path) -> None:
    """A baseline folder whose SHA256SUMS names its one identity file."""
    baseline = folder / "baseline"
    identity = baseline / "run.identity.json"
    identity.write_bytes(IDENTITY_TEXT.encode("utf-8"))
    digest = hashlib.sha256(identity.read_bytes()).hexdigest()
    sums_line = f"{digest}  {identity.name}\n"
    (baseline / "SHA256SUMS").write_bytes(sums_line.encode("utf-8"))
    # The same entry named from the fixture root (a repo-root relative list).
    root_line = f"{digest}  baseline/{identity.name}\n"
    (folder / "baseline_root" / "SHA256SUMS").write_bytes(root_line.encode("utf-8"))


def _write_fixture(folder: Path) -> None:
    for name in FIXTURE_FOLDERS:
        (folder / name).mkdir(parents=True)
    _write_baseline(folder)
    (folder / "wt_main" / "07_results" / "a.txt").write_bytes(b"x")
    tests = folder / "wt_main" / "wt" / "tests"
    (tests / "test_stored.py").write_bytes(WORKTREE_TEST_TEXT.encode("utf-8"))
    (tests / "smoke_probe_mod.py").write_bytes(b"VALUE = 1\n")
    (folder / "docs" / "spec.md").write_bytes(SPEC_TEXT.encode("utf-8"))
    (folder / "junit.xml").write_bytes(JUNIT_TEXT.encode("utf-8"))
    (folder / "scripts" / "run.ps1").write_bytes(PS1_TEXT.encode("utf-8"))
    (folder / "names.json").write_bytes(NAMES_TEXT.encode("utf-8"))
    (folder / "handoff" / "h.md").write_bytes(HANDOFF_TEXT.encode("utf-8"))
    (folder / "logs" / "step.log").write_bytes(LOG_TEXT.encode("utf-8"))
    (folder / "results" / "manifest.json").write_bytes(MANIFEST_TEXT.encode("utf-8"))
    (folder / "results" / "scores.csv").write_bytes(SCORES_TEXT.encode("utf-8"))
    (folder / "results" / "source.jsonl").write_bytes(SOURCE_TEXT.encode("utf-8"))
    (folder / "replay" / "replay.jsonl").write_bytes(REPLAY_TEXT.encode("utf-8"))
    rule = folder / "rules" / "s_rules.md"
    rule.write_bytes(RULE_TEXT.encode("utf-8"))
    digest = hashlib.sha256(rule.read_bytes()).hexdigest()
    (folder / "rules" / "s_rules.sha256").write_text(
        f"{digest}  s_rules.md  sealed 2001-01-01 00:00:00 +09:00 (smoke)\n",
        encoding="utf-8",
    )
    (folder / "results" / "r.jsonl").write_bytes(RESULTS_TEXT.encode("utf-8"))
    (folder / "code" / "judge.py").write_bytes(GATE_TEXT.encode("utf-8"))
    (folder / "code_keys" / "judge.py").write_bytes(MISSING_KEY_TEXT.encode("utf-8"))
    (folder / "junit_xfail.xml").write_bytes(XFAIL_JUNIT_TEXT.encode("utf-8"))
    (folder / "results" / "steps.json").write_bytes(ANGLE_STEPS_TEXT.encode("utf-8"))
    (folder / "code_paths" / "compare.py").write_bytes(ROW_PATH_TEXT.encode("utf-8"))


def _run_command(script: str, arguments: list[str]) -> dict[str, object]:
    command = [sys.executable, "-I", "-B", str(TOOLS_DIR / script), *arguments]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=RUN_TIMEOUT_S,
        check=False,
    )
    lines = completed.stdout.strip().splitlines()
    summary = json.loads(lines[-1]) if lines else {}
    return {"exit_code": completed.returncode, "summary": summary}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
    versions = _dependency_versions()
    results: dict[str, object] = {}
    is_ok = True
    with tempfile.TemporaryDirectory(prefix="verif-smoke-") as folder_text:
        folder = Path(folder_text)
        _write_fixture(folder)
        for label, (arguments, expected_exit) in RUNS.items():
            script = label.split()[0]
            filled = [
                argument.format(folder=folder, python=sys.executable)
                for argument in arguments
            ]
            outcome = _run_command(script, filled)
            outcome["expected_exit_code"] = expected_exit
            results[label] = outcome
            is_ok = is_ok and outcome["exit_code"] == expected_exit
            if label in EXPECTED_CATEGORIES:
                categories = outcome["summary"].get("categories", {})
                has_category = EXPECTED_CATEGORIES[label] in categories
                outcome["expected_category"] = EXPECTED_CATEGORIES[label]
                is_ok = is_ok and has_category
    report = {
        "python": sys.version.split()[0],
        "dependencies": versions,
        "runs": results,
        "status": "ok" if is_ok else "fail",
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0 if is_ok else 1


if __name__ == "__main__":
    sys.exit(main())
