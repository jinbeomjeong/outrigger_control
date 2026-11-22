"""Run worktree tests against the stored data of the main checkout (E axis).

Some tests find their stored results from their own location
(``PROJECT_ROOT = Path(__file__).resolve().parents[2]`` then
``PROJECT_ROOT / "07_results" / ...``). In a git worktree the git-ignored
results are absent, so those tests skip; run from the main checkout they test
the main checkout's code. Links from a worktree into the results are banned
(2026-11-20). This tool generalises the 436.9 edition 5 workaround
(``make_data_copies.py``, 2026-11-22):

1. copy the ``--test`` files, plus every ``conftest.py`` / ``__init__.py``
   between the worktree root and them, into ``<scratch>/wt_tests_<stamp>/tree/``
   with the same relative paths;
2. in each copy pin ``__file__`` to the original path (code, fixtures and helper
   paths stay on the worktree) and wrap only the data paths (``X / "07_results"``
   and similar, ``--rebase-dir``) so that they resolve below ``--data-root``
   (``_source_rebase.py``);
3. run the project's pytest on the copies with the worktree's ini file (``-c``,
   so ``pythonpath`` and markers come from the worktree), ``--rootdir`` the copy
   tree (node ids look like the originals), the worktree as current folder, and
   the probe plugin ``_wt_probe.py``, which records where the ``--probe-module``
   modules were imported from in every process (xdist workers too);
4. report pytest's outcome from its JUnit XML (a skip is a warning: here it is
   a verification gap), the probe, the rebased paths, and whether the originals
   are byte-for-byte unchanged; then delete the run folder (``--keep`` keeps it).

Unlike the other verif tools this one runs code: the project's tests. It never
writes into the worktree or the data root (``--scratch`` and ``--out`` must lie
outside both) and only kills the process tree it started (on ``--timeout``).

Exit codes:

* 0: pytest exit 0, every test ran (no skip or xfail), every probe module came
  from the worktree, originals unchanged.
* 1: findings: failed or error tests, skips, xfails, no tests, a probe module
  imported from elsewhere or not at all, no data path rebased, pytest
  interrupted / internal error / timeout, an original changed.
* 2: input error: missing folder, file or interpreter, a test outside the
  worktree, a ``--rebase-dir`` the data root lacks, ``--scratch`` or ``--out``
  inside the worktree or data root, an original that does not parse, pytest
  usage error (pytest exit 4).
* 3: internal error of this tool.

Usage:
    python worktree_tests.py --worktree WT --data-root MAIN --python PY
        --scratch DIR --test FILE [...] --probe-module NAME [...]
        [--rebase-dir 07_results ...] [--support FILE ...] [--pin-module NAME ...]
        [--inifile FILE] [--env NAME=VALUE ...] [--timeout S] [--keep]
        [--out REPORT] [--format md|json] [--fail-on error|warning]
        [-- EXTRA PYTEST ARGS]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import decode_bytes, expand_file_patterns, is_within, require_output_outside
from _findings import (
    Finding,
    Severity,
    add_report_arguments,
    count_by_category,
    count_by_severity,
    deliver_report,
    exit_code_for,
    finding_to_dict,
    findings_markdown,
    severity_summary_text,
    sort_findings,
)
from _source_rebase import RebaseResult, rebase_source
from junit_skips import TestCase, case_findings, read_test_cases

TOOL_NAME = "worktree_tests"
DEFAULT_REBASE_DIRS = ("07_results",)
DEFAULT_TIMEOUT_S = 3600.0
PLUGIN_SOURCE = Path(__file__).resolve().parent / "_wt_probe.py"
PLUGIN_MODULE = "_wt_probe"
CONFIG_VARIABLE = "WT_TESTS_CONFIG"
SCAFFOLD_NAMES = ("conftest.py", "__init__.py")
DROPPED_VARIABLES = ("PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS")
INI_CANDIDATES = (
    ("pytest.ini", ""),
    ("pyproject.toml", "[tool.pytest.ini_options]"),
    ("tox.ini", "[pytest]"),
    ("setup.cfg", "[tool:pytest]"),
)
LOG_TAIL_LINES = 60
MAX_LISTED = 10
TIMEOUT_EXIT = -1
PYTEST_USAGE_ERROR = 4
PYTEST_EXIT_TEXT = {
    TIMEOUT_EXIT: "시간 초과",
    0: "모든 시험 통과",
    1: "실패한 시험 있음",
    2: "중단됨(interrupted)",
    3: "pytest 내부 오류",
    4: "pytest 사용법 오류",
    5: "수집된 시험 없음",
}
PYTEST_EXIT_CATEGORIES = {
    TIMEOUT_EXIT: "pytest_timeout",
    2: "pytest_interrupted",
    3: "pytest_internal_error",
    5: "no_tests",
}
FAILING_OUTCOMES = ("failed", "error", "xpassed")
PYTEST_PLACE = "pytest"
PROBE_PLACE = "probe"
PROBE_KINDS = {
    "not_loaded": (
        Severity.WARNING,
        "probe_not_loaded",
        "어느 pytest 프로세스도 import하지 않았다(확인 불가)",
    ),
    "foreign": (Severity.ERROR, "probe_foreign", "worktree 밖에서 import됨"),
    "worktree": (Severity.INFO, "probe_worktree", "worktree에서 import됨"),
}


@dataclass(frozen=True)
class CopiedFile:
    """One file copied into the run tree, and what its rewrite touched."""

    original: Path
    relative: Path
    is_test: bool
    rebase: RebaseResult


@dataclass(frozen=True)
class RunPlan:
    """Everything the run needs, checked before anything is written."""

    worktree: Path
    data_root: Path
    python: Path
    tests: list[Path]
    support: list[Path]
    rebase_dirs: list[str]
    probe_modules: list[str]
    pin_modules: list[str]
    inifile: Path | None
    scratch: Path
    environment: dict[str, str]
    timeout_s: float
    extra_args: list[str]
    keep: bool


@dataclass
class RunFolders:
    """The run folder and its parts (all below ``--scratch``)."""

    root: Path
    tree: Path = field(init=False)
    probe: Path = field(init=False)
    junit: Path = field(init=False)
    log: Path = field(init=False)
    config: Path = field(init=False)

    def __post_init__(self) -> None:
        self.tree = self.root / "tree"
        self.probe = self.root / "probe"
        self.junit = self.root / "junit.xml"
        self.log = self.root / "pytest.log"
        self.config = self.root / "wt_tests_config.json"


@dataclass(frozen=True)
class PytestRun:
    """Exit code (``TIMEOUT_EXIT`` on timeout), wall time and the log tail."""

    exit_code: int
    wall_s: float
    log_tail: list[str]


@dataclass(frozen=True)
class RunFacts:
    """What one run produced, read before the run folder is deleted."""

    copies: list[CopiedFile]
    original_sha256: dict[str, str]
    command: list[str]
    dropped_environment: list[str]
    pytest_run: PytestRun
    cases: list[TestCase]
    probe_records: list[dict]
    junit_written: bool


def _tool_finding(
    severity: Severity, category: str, message: str, place: str = PYTEST_PLACE
) -> Finding:
    """A finding about the run as a whole (no file line)."""
    return Finding(severity, category, place, 0, message)


# --- inputs ------------------------------------------------------------------------


def _existing_folder(text: str, role: str) -> Path:
    path = Path(text).expanduser().resolve()
    if not path.is_dir():
        raise InputError(f"{role} is not a folder: {path}")
    return path


def _files_below(patterns: list[str], worktree: Path, role: str) -> list[Path]:
    files = expand_file_patterns(patterns, worktree) if patterns else []
    for path in files:
        if not is_within(path, worktree):
            raise InputError(f"{role} is not inside the worktree: {path}")
    return files


def _environment_overrides(pairs: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for pair in pairs:
        name, separator, value = pair.partition("=")
        if not separator or not name:
            raise InputError(f"--env needs NAME=VALUE: {pair}")
        overrides[name] = value
    return overrides


def _find_inifile(worktree: Path, given: str | None) -> Path | None:
    if given is not None:
        path = Path(given).expanduser()
        path = (path if path.is_absolute() else worktree / path).resolve()
        if not path.is_file():
            raise InputError(f"--inifile not found: {path}")
        return path
    for name, marker in INI_CANDIDATES:
        path = worktree / name
        if not path.is_file():
            continue
        if not marker or marker in decode_bytes(path.read_bytes())[0]:
            return path
    return None


def _check_rebase_dirs(names: list[str], data_root: Path) -> list[str]:
    for name in names:
        if not name or Path(name).name != name:
            raise InputError(f"--rebase-dir must be one folder name: {name!r}")
        if not (data_root / name).is_dir():
            raise InputError(f"--rebase-dir {name} is not a folder of the data root")
    return list(dict.fromkeys(names))


def _check_scratch(scratch: Path, worktree: Path, data_root: Path) -> None:
    for folder, role in ((worktree, "worktree"), (data_root, "data root")):
        if is_within(scratch, folder):
            raise InputError(f"--scratch must not be inside the {role}: {scratch}")


def build_plan(args: argparse.Namespace) -> RunPlan:
    """Check every input and return the run plan (nothing is written yet).

    Raises:
        InputError: If a folder, file or option is unusable.
    """
    worktree = _existing_folder(args.worktree, "--worktree")
    data_root = _existing_folder(args.data_root, "--data-root")
    if worktree == data_root:
        raise InputError("--worktree and --data-root are the same folder")
    python = Path(args.python).expanduser().resolve()
    if not python.is_file():
        raise InputError(f"--python not found: {python}")
    tests = _files_below(args.test, worktree, "--test")
    support_files = _files_below(args.support, worktree, "--support")
    scratch = Path(args.scratch).expanduser().resolve()
    _check_scratch(scratch, worktree, data_root)
    require_output_outside(args.out, tests, [worktree, data_root])
    rebase_names = args.rebase_dir or list(DEFAULT_REBASE_DIRS)
    return RunPlan(
        worktree=worktree,
        data_root=data_root,
        python=python,
        tests=tests,
        support=[path for path in support_files if path not in tests],
        rebase_dirs=_check_rebase_dirs(rebase_names, data_root),
        probe_modules=list(dict.fromkeys(args.probe_module)),
        pin_modules=list(dict.fromkeys(args.pin_module)),
        inifile=_find_inifile(worktree, args.inifile),
        scratch=scratch,
        environment=_environment_overrides(args.env),
        timeout_s=args.timeout,
        extra_args=list(args.pytest_args),
        keep=args.keep,
    )


# --- copies ------------------------------------------------------------------------


def _scaffold_files(tests: list[Path], worktree: Path) -> list[Path]:
    """``conftest.py`` and ``__init__.py`` from the worktree root down to each test."""
    found: list[Path] = []
    for test in tests:
        folders = [test.parent, *test.parent.parents]
        for folder in reversed(folders):
            if not is_within(folder, worktree):
                continue
            for name in SCAFFOLD_NAMES:
                candidate = folder / name
                if candidate.is_file() and candidate not in found:
                    found.append(candidate)
    return [path for path in found if path not in tests]


def _copy_one(
    original: Path, plan: RunPlan, tree: Path, *, is_test: bool
) -> CopiedFile:
    relative = original.relative_to(plan.worktree)
    source_text = decode_bytes(original.read_bytes())[0]
    try:
        rebase = rebase_source(source_text, original, plan.rebase_dirs)
    except SyntaxError as error:
        raise InputError(f"cannot parse {original}: {error}") from error
    target = tree / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    # newline="": keep the source's line endings; text mode on Windows turned a CRLF
    # source into "\r\r\n", which doubles the line numbers and breaks "\" continuations
    target.write_text(rebase.text, encoding="utf-8", newline="")
    return CopiedFile(original, relative, is_test, rebase)


def copy_sources(plan: RunPlan, tree: Path) -> list[CopiedFile]:
    """Copy tests, their scaffolding and ``--support`` files into ``tree``."""
    copies = [_copy_one(path, plan, tree, is_test=True) for path in plan.tests]
    others = [*_scaffold_files(plan.tests, plan.worktree), *plan.support]
    for path in dict.fromkeys(others):
        copies.append(_copy_one(path, plan, tree, is_test=False))
    return copies


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- run ---------------------------------------------------------------------------


def _write_plugin(plan: RunPlan, folders: RunFolders, copies: list[CopiedFile]) -> None:
    shutil.copyfile(PLUGIN_SOURCE, folders.root / f"{PLUGIN_MODULE}.py")
    folders.probe.mkdir()
    config = {
        "worktree": str(plan.worktree),
        "data_root": str(plan.data_root),
        "rebase_dirs": plan.rebase_dirs,
        "probe_modules": plan.probe_modules,
        "pin_modules": plan.pin_modules,
        "support_paths": sorted({str(copy.original.parent) for copy in copies}),
        "probe_dir": str(folders.probe),
    }
    folders.config.write_text(json.dumps(config, indent=2), encoding="utf-8")


def pytest_command(
    plan: RunPlan, folders: RunFolders, copies: list[CopiedFile]
) -> list[str]:
    """The pytest command line (copies only, worktree ini, probe plugin)."""
    command = [str(plan.python), "-B", "-m", "pytest"]
    command += [str(folders.tree / copy.relative) for copy in copies if copy.is_test]
    # Only the mirrored conftest files count; none from folders above the copies.
    command += ["--rootdir", str(folders.tree), "--confcutdir", str(folders.tree)]
    if plan.inifile is not None:
        command += ["-c", str(plan.inifile)]
    command += ["-p", "no:cacheprovider", "-p", PLUGIN_MODULE]
    command += ["--junitxml", str(folders.junit), "-q", "-rfEsxX"]
    return [*command, *plan.extra_args]


def pytest_environment(
    plan: RunPlan, folders: RunFolders
) -> tuple[dict[str, str], list[str]]:
    """Child environment and the inherited variables that were dropped."""
    environment = dict(os.environ)
    dropped = [
        name for name in DROPPED_VARIABLES if environment.pop(name, None) is not None
    ]
    environment["PYTHONPATH"] = str(folders.root)  # only the probe plugin
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment[CONFIG_VARIABLE] = str(folders.config)
    environment.update(plan.environment)
    return environment, dropped


def _kill_process_tree(process: subprocess.Popen) -> None:
    """Kill the pytest process this tool started and its descendants (by PID).

    Without psutil only the direct child is killed (xdist workers may stay).
    """
    try:
        import psutil  # optional; python-dev has it
    except ImportError:
        process.kill()
        return
    try:
        children = psutil.Process(process.pid).children(recursive=True)
    except psutil.Error:
        children = []
    for child in children:
        try:
            child.kill()
        except psutil.Error:
            continue
    process.kill()


def run_pytest(
    command: list[str], environment: dict[str, str], plan: RunPlan, folders: RunFolders
) -> PytestRun:
    """Run pytest from the worktree with its output in the run folder's log."""
    started = time.perf_counter()
    with folders.log.open("w", encoding="utf-8", errors="replace") as log:
        process = subprocess.Popen(
            command,
            cwd=plan.worktree,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            exit_code = process.wait(timeout=plan.timeout_s)
        except subprocess.TimeoutExpired:
            _kill_process_tree(process)
            process.wait()
            exit_code = TIMEOUT_EXIT
    wall_s = round(time.perf_counter() - started, 1)
    log_text = decode_bytes(folders.log.read_bytes())[0]
    return PytestRun(exit_code, wall_s, log_text.splitlines()[-LOG_TAIL_LINES:])


def read_probe_records(probe_dir: Path) -> list[dict]:
    """The probe records written by every pytest process (controller and workers)."""
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(probe_dir.glob("probe_*.json"))
    ]


def execute(plan: RunPlan, folders: RunFolders) -> RunFacts:
    """Copy, run pytest and read its outputs (the run folder still exists).

    Raises:
        InputError: If an original does not parse or pytest reports a usage error.
    """
    copies = copy_sources(plan, folders.tree)
    original_sha256 = {str(copy.original): _sha256(copy.original) for copy in copies}
    _write_plugin(plan, folders, copies)
    command = pytest_command(plan, folders, copies)
    environment, dropped = pytest_environment(plan, folders)
    pytest_run = run_pytest(command, environment, plan, folders)
    if pytest_run.exit_code == PYTEST_USAGE_ERROR:
        tail = " / ".join(pytest_run.log_tail[-5:])
        raise InputError(f"pytest usage error (exit 4): {tail}")
    junit_written = folders.junit.is_file()
    return RunFacts(
        copies=copies,
        original_sha256=original_sha256,
        command=command,
        dropped_environment=dropped,
        pytest_run=pytest_run,
        cases=read_test_cases(folders.junit) if junit_written else [],
        probe_records=read_probe_records(folders.probe),
        junit_written=junit_written,
    )


# --- findings ----------------------------------------------------------------------


def _test_file_for(case: TestCase, copies: list[CopiedFile]) -> str:
    for copy in copies:
        dotted = copy.relative.with_suffix("").as_posix().replace("/", ".")
        if case.classname == dotted or case.classname.startswith(dotted + "."):
            return copy.relative.as_posix()
    return PYTEST_PLACE


def junit_findings(cases: list[TestCase], copies: list[CopiedFile]) -> list[Finding]:
    """Failures, skips (warnings: a verification gap) and xfails, by test file."""
    findings = []
    for case in cases:
        place = _test_file_for(case, copies)
        for item in case_findings([case], [], fail_on_skip=True):
            findings.append(
                Finding(
                    item.severity, item.category, place, 0, item.message, item.target
                )
            )
    return findings


def pytest_exit_findings(facts: RunFacts) -> list[Finding]:
    """Findings from pytest's exit code that the test cases do not already show."""
    exit_code = facts.pytest_run.exit_code
    findings = []
    category = PYTEST_EXIT_CATEGORIES.get(exit_code)
    if category is not None:
        text = f"pytest 종료 {exit_code}: {PYTEST_EXIT_TEXT[exit_code]}"
        findings.append(_tool_finding(Severity.ERROR, category, text))
    if not facts.junit_written:
        text = "JUnit XML이 없다(pytest가 끝까지 돌지 못함)"
        findings.append(_tool_finding(Severity.ERROR, "junit_missing", text))
        return findings
    has_failure = any(case.outcome in FAILING_OUTCOMES for case in facts.cases)
    if exit_code == 1 and not has_failure:
        text = "pytest 종료 1인데 JUnit에 실패가 없다(로그 끝 확인)"
        findings.append(_tool_finding(Severity.ERROR, "pytest_failed_unseen", text))
    if not facts.cases and category != "no_tests":
        text = "시험 0개: 빈 실행은 통과가 아니다"
        findings.append(_tool_finding(Severity.ERROR, "no_tests", text))
    return findings


def module_locations(records: list[dict], name: str) -> dict[str, list[str]]:
    """Location -> workers that imported the module from there."""
    locations: dict[str, list[str]] = {}
    for record in records:
        location = record["modules"].get(name)
        if location is not None:
            locations.setdefault(location, []).append(record["worker"])
    return locations


def probe_verdicts(plan: RunPlan, records: list[dict]) -> dict[str, str]:
    """Per probe module: ``worktree``, ``foreign`` or ``not_loaded``."""
    verdicts = {}
    for name in plan.probe_modules:
        locations = module_locations(records, name)
        if not locations:
            verdicts[name] = "not_loaded"
        elif all(is_within(Path(path), plan.worktree) for path in locations):
            verdicts[name] = "worktree"
        else:
            verdicts[name] = "foreign"
    return verdicts


def probe_findings(records: list[dict], verdicts: dict[str, str]) -> list[Finding]:
    """Where each probe module came from, in every process."""
    if not records:
        text = "probe 기록이 없다(플러그인이 실행되지 않음)"
        return [_tool_finding(Severity.ERROR, "probe_missing", text, PROBE_PLACE)]
    findings = []
    for name, verdict in verdicts.items():
        severity, category, text = PROBE_KINDS[verdict]
        locations = module_locations(records, name)
        if locations:
            shown = "; ".join(
                f"{path} ({', '.join(workers)})" for path, workers in locations.items()
            )
            text = f"{text}: {shown}"
        findings.append(Finding(severity, category, PROBE_PLACE, 0, text, name))
    return findings


def rebase_totals(records: list[dict]) -> dict[str, int]:
    """Run-time rebase counts summed over the processes."""
    totals = {"rebased": 0, "already_in_data_root": 0, "unmatched": 0}
    for record in records:
        for key in totals:
            totals[key] += int(record["rebase"][key])
    return totals


def rewrite_findings(copies: list[CopiedFile]) -> list[Finding]:
    """What the static rewrite could not cover."""
    findings = []
    for copy in copies:
        place = copy.relative.as_posix()
        for note in copy.rebase.unwrapped_literals:
            text = (
                f"감싸지 않은 데이터 경로 글자 {note.text!r}: 여기는 worktree를 읽는다"
            )
            findings.append(
                Finding(
                    Severity.WARNING, "data_literal_not_rebased", place, note.line, text
                )
            )
        if copy.is_test and not copy.rebase.wrapped:
            text = "바꿀 데이터 경로가 없다(worktree에서 그냥 돌려도 같다)"
            findings.append(Finding(Severity.INFO, "no_data_paths", place, 0, text))
    return findings


def rebase_count_findings(records: list[dict]) -> list[Finding]:
    """Run-time rebase counts: none rebased, or values outside both roots."""
    if not records:
        return []
    findings = []
    totals = rebase_totals(records)
    if totals["rebased"] == 0:
        text = "실행 중 데이터 경로가 한 번도 바뀌지 않았다"
        findings.append(
            _tool_finding(Severity.WARNING, "rebase_never_used", text, PROBE_PLACE)
        )
    if totals["unmatched"]:
        # Paths outside both roots (tmp_path fixtures, absolute main paths) are
        # left alone on purpose; listed so a reader can spot an unexpected root.
        values = sorted(
            {value for item in records for value in item["unmatched_values"]}
        )
        text = (
            f"worktree·데이터 root 밖이라 그대로 둔 값 {totals['unmatched']}회: "
            f"{values[:MAX_LISTED]}"
        )
        findings.append(
            _tool_finding(Severity.INFO, "rebase_unmatched", text, PROBE_PLACE)
        )
    return findings


def original_findings(original_sha256: dict[str, str]) -> list[Finding]:
    """Error for any original whose bytes changed during the run."""
    findings = []
    for path_text, digest in original_sha256.items():
        path = Path(path_text)
        if not path.is_file() or _sha256(path) != digest:
            text = "원본 파일이 실행 중 바뀌었다"
            findings.append(
                Finding(Severity.ERROR, "original_changed", path_text, 0, text)
            )
    return findings


# --- report ------------------------------------------------------------------------


def outcome_counts(cases: list[TestCase]) -> dict[str, int]:
    """Number of test cases per outcome (JUnit)."""
    counts = {"tests": len(cases)}
    for key, outcome in (
        ("passed", "passed"),
        ("failed", "failed"),
        ("errors", "error"),
        ("skipped", "skipped"),
        ("xfailed", "xfailed"),
        ("xpassed", "xpassed"),
    ):
        counts[key] = sum(1 for case in cases if case.outcome == outcome)
    return counts


def _copy_rows(copies: list[CopiedFile]) -> list[dict[str, object]]:
    rows = []
    for copy in copies:
        wrapped = [{"line": n.line, "expression": n.text} for n in copy.rebase.wrapped]
        unwrapped = [
            {"line": note.line, "text": note.text}
            for note in copy.rebase.unwrapped_literals
        ]
        rows.append(
            {
                "file": copy.relative.as_posix(),
                "is_test": copy.is_test,
                "file_references": copy.rebase.file_references,
                "wrapped": wrapped,
                "unwrapped_literals": unwrapped,
            }
        )
    return rows


def _overview_lines(report: dict, findings: list[Finding]) -> list[str]:
    summary = report["summary"]
    counts = report["tests"]
    probe = ", ".join(
        f"`{name}` {verdict}" for name, verdict in summary["probe"].items()
    )
    return [
        (
            f"- worktree `{report['worktree']}`, 데이터 root `{report['data_root']}`, "
            f"바꾼 폴더 {', '.join(report['rebase_dirs'])}"
        ),
        (
            f"- pytest 종료 {summary['pytest_exit']}({summary['pytest_exit_text']}), "
            f"{report['pytest']['wall_s']} s · 시험 {counts['tests']}: "
            f"통과 {counts['passed']}, 실패 {counts['failed']}, "
            f"오류 {counts['errors']}, "
            f"건너뜀 {counts['skipped']}, 예상 실패 {counts['xfailed']}, "
            f"XPASS {counts['xpassed']}"
        ),
        f"- probe: {probe}",
        (
            f"- 실행 중 바뀐 데이터 경로 {report['rebase_totals']['rebased']}회, "
            f"원본 불변 {summary['originals_unchanged']}, "
            f"실행 폴더 삭제 {summary['run_dir_removed']}"
        ),
        f"- {severity_summary_text(findings)}",
    ]


def _markdown(report: dict, findings: list[Finding]) -> list[str]:
    lines = [
        "# worktree_tests — worktree 코드 + 메인 checkout 저장 자료 시험",
        "",
        *_overview_lines(report, findings),
        "",
        "## 복사본",
        "",
        "| 파일 | 시험 | `__file__` | 감싼 경로 | 감싸지 않은 글자 |",
        "|---|---|---|---|---|",
    ]
    for row in report["copies"]:
        wrapped = "<br>".join(
            f"{item['line']}: `{item['expression']}`" for item in row["wrapped"]
        )
        is_test = "예" if row["is_test"] else "-"
        lines.append(
            f"| `{row['file']}` | {is_test} | {row['file_references']} "
            f"| {wrapped or '-'} | {len(row['unwrapped_literals'])} |"
        )
    log_tail = report["pytest"]["log_tail"]
    findings_part = ["## 발견 사항", "", *findings_markdown(findings)]
    log_part = ["## pytest 로그 끝", "", "```text", *log_tail, "```"]
    return [*lines, "", *findings_part, "", *log_part]


def _remove_run_folder(folders: RunFolders) -> list[Finding]:
    try:
        shutil.rmtree(folders.root)
    except OSError as error:
        text = f"실행 폴더를 지우지 못했다: {error}"
        return [Finding(Severity.WARNING, "cleanup_failed", str(folders.root), 0, text)]
    return []


def _new_run_folders(scratch: Path) -> RunFolders:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    folders = RunFolders(scratch / f"wt_tests_{stamp}_{os.getpid()}")
    folders.root.mkdir(parents=True, exist_ok=False)  # never reuse an old run
    return folders


def collect_findings(
    facts: RunFacts, verdicts: dict[str, str], cleanup: list[Finding]
) -> list[Finding]:
    """Every finding of the run, sorted."""
    return sort_findings(
        [
            *junit_findings(facts.cases, facts.copies),
            *pytest_exit_findings(facts),
            *probe_findings(facts.probe_records, verdicts),
            *rewrite_findings(facts.copies),
            *rebase_count_findings(facts.probe_records),
            *original_findings(facts.original_sha256),
            *cleanup,
        ]
    )


def build_report(
    plan: RunPlan, folders: RunFolders, facts: RunFacts, findings: list[Finding]
) -> tuple[dict, dict]:
    """The full report and the summary (last stdout line)."""
    exit_code = facts.pytest_run.exit_code
    verdicts = probe_verdicts(plan, facts.probe_records)
    totals = rebase_totals(facts.probe_records)
    summary = {
        "tool": TOOL_NAME,
        "command": "run",
        "pytest_exit": exit_code,
        "pytest_exit_text": PYTEST_EXIT_TEXT.get(exit_code, "알 수 없는 종료 코드"),
        **outcome_counts(facts.cases),
        "probe": verdicts,
        "rebased_paths": totals["rebased"],
        "copies": len(facts.copies),
        "originals_unchanged": not any(
            item.category == "original_changed" for item in findings
        ),
        "run_dir_removed": not folders.root.exists(),
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "worktree": str(plan.worktree),
        "data_root": str(plan.data_root),
        "python": str(plan.python),
        "inifile": None if plan.inifile is None else str(plan.inifile),
        "rebase_dirs": plan.rebase_dirs,
        "probe_modules": plan.probe_modules,
        "pin_modules": plan.pin_modules,
        "run_dir": str(folders.root),
        "pytest": {
            "command": facts.command,
            "cwd": str(plan.worktree),
            "dropped_environment": facts.dropped_environment,
            "set_environment": sorted(plan.environment),
            "exit_code": exit_code,
            "wall_s": facts.pytest_run.wall_s,
            "log_tail": facts.pytest_run.log_tail,
        },
        "tests": outcome_counts(facts.cases),
        "cases": [case.to_dict() for case in facts.cases if case.outcome != "passed"],
        "probe_records": facts.probe_records,
        "rebase_totals": totals,
        "copies": _copy_rows(facts.copies),
        "originals": facts.original_sha256,
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    return report, summary


def run_worktree_tests(args: argparse.Namespace) -> ToolOutcome:
    """Copy, rewrite, run, judge and clean up."""
    plan = build_plan(args)
    folders = _new_run_folders(plan.scratch)
    try:
        facts = execute(plan, folders)
    finally:
        cleanup = [] if plan.keep else _remove_run_folder(folders)
    verdicts = probe_verdicts(plan, facts.probe_records)
    findings = collect_findings(facts, verdicts, cleanup)
    report, summary = build_report(plan, folders, facts, findings)
    lines = deliver_report(args, _markdown(report, findings), report, plan.tests)
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="worktree_tests.py",
        description=(
            "worktree 시험 파일을 scratch에 복사해 저장 자료 경로만 메인 checkout으로 "
            "바꾸고, worktree 코드로 pytest를 돌려 결과·import 출처(probe)를 낸다."
        ),
    )
    many = {"nargs": "+", "action": "extend"}
    parser.add_argument("--worktree", required=True, help="worktree whose code runs")
    parser.add_argument(
        "--data-root", required=True, help="folder with the stored data (main checkout)"
    )
    parser.add_argument("--python", required=True, help="project interpreter")
    parser.add_argument(
        "--scratch", required=True, help="parent of the run folder (outside both roots)"
    )
    parser.add_argument(
        "--test", **many, required=True, help="test files or globs (worktree-relative)"
    )
    parser.add_argument(
        "--probe-module",
        **many,
        required=True,
        help="modules that must come from the worktree",
    )
    parser.add_argument(
        "--rebase-dir",
        **many,
        default=[],
        help="folders read from the data root (default 07_results)",
    )
    parser.add_argument(
        "--support",
        **many,
        default=[],
        help="extra worktree modules to copy and rewrite",
    )
    parser.add_argument(
        "--pin-module",
        **many,
        default=[],
        help="import at pytest_configure, before the tests",
    )
    parser.add_argument("--inifile", help="pytest ini file (default: the worktree's)")
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="environment variable for pytest; repeatable",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        help=f"seconds before pytest's process tree is killed ({DEFAULT_TIMEOUT_S:g})",
    )
    parser.add_argument(
        "--keep", action="store_true", help="keep the run folder (copies, junit, log)"
    )
    add_report_arguments(parser)
    return parser


def _split_pytest_args(argv: list[str]) -> tuple[list[str], list[str]]:
    """Arguments after the first ``--`` go to pytest unchanged."""
    if "--" not in argv:
        return argv, []
    index = argv.index("--")
    return argv[:index], argv[index + 1 :]


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    own_args, pytest_args = _split_pytest_args(sys.argv[1:] if argv is None else argv)
    args = parse_arguments(build_parser(), own_args)
    args.pytest_args = pytest_args
    return run_tool(lambda: run_worktree_tests(args))


if __name__ == "__main__":
    sys.exit(main())
