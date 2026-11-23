"""436.9 edition 6 erratum 2 2-2: the existing-failure list of the full unit suite and the run
commit judgement against it.

Both sides run the same command (``run_steps_ed6/full_suite_ed6.ps1``: every
``05_tests/unit/test_*.py`` through ``tools/verif/worktree_tests.py``) - the baseline on the
merge-base of the run commit and master, then the run commit. This tool reads their JUnit XML.

``baseline``  writes the existing-failure list: one line ``<outcome>\\t<test id>`` per test that
              did not pass at the merge-base (failed, error, skipped, xfailed), the merge-base sha
              on the first line (``# merge_base <sha>``), and ``<list>.sha256`` beside it.
``judge``     the run commit's JUnit against that list (its sha256 asserted first):

  * a failed / error test that is not failed / error in the list: a new failure (failed);
  * a core test (file stem matching :data:`CORE_PATTERNS`) that does not pass - failed, error,
    skipped or xfailed - is failed whatever the list says (the core range is never exempt;
    a skip or xfail there is "not passing");
  * any other skip / xfail is allowed only when the same test id is skipped / xfailed in the
    list; otherwise failed (a new test must pass);
  * an existing failure outside the core range that still fails is a record.

No automatic rerun. Exit codes (stdout's last line is JSON with ``status`` and counts):

====  =================  ====================================================================
exit  status             meaning
====  =================  ====================================================================
0     ``pass``           ``baseline``: list written; ``judge``: no finding above
1     ``failed``         ``judge``: a new failure, a core test not passing, a new skip / xfail
2     ``not_judgeable``  a JUnit file missing or without tests, the list sha256 other than
                         given, an existing ``--out``
3     ``error``          a tool error (every unexpected exception)
====  =================  ====================================================================

Usage (any Python 3.10+, standard library only):
  python -I -B jp3_ed6_suite.py baseline --junit <base junit.xml> --merge-base <sha>
      --out <existing_failures.txt>
  python -I -B jp3_ed6_suite.py judge --junit <run junit.xml> --baseline-list <list>
      --baseline-sha256 <sha> --out <judgement.json>
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import sys
import xml.etree.ElementTree as ElementTree  # noqa: S405 (our own pytest JUnit output)
from pathlib import Path

EXIT_PASS, EXIT_FAILED, EXIT_STOP, EXIT_ERROR = 0, 1, 2, 3
CORE_PATTERNS = ("test_jp3_*", "test_ed6_*", "test_run_v5*", "test_lock_start_b*", "test_c2*",
                 "test_extend_start_bound*")
"""Erratum 2 2-2: the core range (file stems of ``jp3_*``, ``ed6_*``, ``run_v5``,
``lock_start_b``, ``c2``, ``extend_start_bound`` tests); never exempt."""
FAILING = ("failed", "error")
NOT_RUN = ("skipped", "xfailed")
HEADER_PREFIX = "# merge_base "


class NotJudgeable(Exception):
    """An input that does not allow a judgement (exit 2)."""


def read_outcomes(junit: Path) -> dict[str, str]:
    """Test id -> ``passed`` / ``failed`` / ``error`` / ``skipped`` / ``xfailed``.

    Raises:
        NotJudgeable: The file is missing or has no test case.
    """
    if not junit.is_file():
        raise NotJudgeable(f"{junit} missing")
    root = ElementTree.parse(junit).getroot()  # noqa: S314 (local pytest output)
    outcomes: dict[str, str] = {}
    for case in root.iter("testcase"):
        test_id = f"{case.get('classname', '')}::{case.get('name', '')}"
        outcomes[test_id] = _outcome(case)
    if not outcomes:
        raise NotJudgeable(f"{junit} has no test case")
    return outcomes


def _outcome(case: ElementTree.Element) -> str:
    if case.find("failure") is not None:
        return "failed"
    if case.find("error") is not None:
        return "error"
    skipped = case.find("skipped")
    if skipped is not None:
        return "xfailed" if skipped.get("type") == "pytest.xfail" else "skipped"
    return "passed"


def is_core(test_id: str) -> bool:
    """A test of the core range (a ``test_*`` part of its class name matches a pattern)."""
    parts = test_id.split("::", 1)[0].split(".")
    return any(fnmatch.fnmatchcase(part, pattern) for part in parts
               for pattern in CORE_PATTERNS)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_baseline(junit: Path, merge_base: str, out: Path) -> dict:
    """``baseline`` (module docstring)."""
    outcomes = read_outcomes(junit)
    lines = [f"{HEADER_PREFIX}{merge_base}"]
    lines += [f"{outcome}\t{test_id}" for test_id, outcome in sorted(outcomes.items())
              if outcome != "passed"]
    with out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    digest = file_sha256(out)
    with out.with_name(out.name + ".sha256").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{digest} *{out.name}\n")
    return {"status": "pass", "tests": len(outcomes), "not_passing": len(lines) - 1,
            "list": str(out), "list_sha256": digest}


def read_baseline(path: Path, expected_sha256: str) -> dict[str, str]:
    """Test id -> outcome of the existing-failure list.

    Raises:
        NotJudgeable: The list is missing or its sha256 is not the given one.
    """
    if not path.is_file():
        raise NotJudgeable(f"{path} missing")
    if file_sha256(path) != expected_sha256:
        raise NotJudgeable(f"{path} sha256 is not {expected_sha256}")
    listed = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        outcome, test_id = line.split("\t", 1)
        listed[test_id] = outcome
    return listed


def judge(junit: Path, baseline: Path, baseline_sha256: str) -> dict:
    """``judge`` (module docstring)."""
    listed = read_baseline(baseline, baseline_sha256)
    outcomes = read_outcomes(junit)
    findings: dict[str, list[str]] = {"new_failure": [], "core_not_passing": [],
                                      "new_skip_or_xfail": []}
    records = []
    for test_id, outcome in sorted(outcomes.items()):
        if outcome == "passed":
            continue
        before = listed.get(test_id)
        if is_core(test_id):
            findings["core_not_passing"].append(f"{outcome}\t{test_id}")
        elif outcome in FAILING and before not in FAILING:
            findings["new_failure"].append(f"{outcome}\t{test_id}")
        elif outcome in NOT_RUN and before not in NOT_RUN:
            findings["new_skip_or_xfail"].append(f"{outcome}\t{test_id}")
        else:
            records.append(f"{outcome}\t{test_id} (list: {before})")
    failed = any(findings.values())
    counts = {outcome: sum(value == outcome for value in outcomes.values())
              for outcome in ("passed", *FAILING, *NOT_RUN)}
    return {"rule": "jp3_remedy_spec_v6_erratum2.md 2-2", "core_patterns": list(CORE_PATTERNS),
            "inputs": {"junit": {"path": str(junit), "sha256": file_sha256(junit)},
                       "baseline_list": {"path": str(baseline), "sha256": baseline_sha256}},
            "tests": len(outcomes), "counts": counts, "findings": findings,
            "existing_failures_record": records, "status": "failed" if failed else "pass"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    baseline = sub.add_parser("baseline")
    baseline.add_argument("--junit", type=Path, required=True)
    baseline.add_argument("--merge-base", required=True)
    baseline.add_argument("--out", type=Path, required=True)
    run = sub.add_parser("judge")
    run.add_argument("--junit", type=Path, required=True)
    run.add_argument("--baseline-list", type=Path, required=True)
    run.add_argument("--baseline-sha256", required=True)
    run.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.out.exists():
        print(json.dumps({"status": "not_judgeable", "reason": "--out exists"}))
        return EXIT_STOP
    try:
        if args.command == "baseline":
            summary = write_baseline(args.junit, args.merge_base, args.out)
            print(json.dumps(summary))
            return EXIT_PASS
        report = judge(args.junit, args.baseline_list, args.baseline_sha256)
    except NotJudgeable as exc:
        print(json.dumps({"status": "not_judgeable", "reason": str(exc)}))
        return EXIT_STOP
    except Exception as exc:  # noqa: BLE001 (every other failure is a tool error)
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    print(json.dumps({"status": report["status"], "tests": report["tests"],
                      **{name: len(items) for name, items in report["findings"].items()},
                      "out": str(args.out)}))
    return EXIT_FAILED if report["status"] == "failed" else EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
