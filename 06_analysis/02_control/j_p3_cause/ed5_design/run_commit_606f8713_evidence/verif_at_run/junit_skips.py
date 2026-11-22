"""JUnit skip check (E axis): which tests did not run, and were any of them required?

2026-11-16: a record regression suite ended "N passed, 3 skipped" and was almost
read as "all passed"; the three skips were record tests whose input folder was
missing. Run pytest with ``--junitxml=<scratchpad>\\junit.xml`` and give that
file here.

For each JUnit XML (pytest, or any ``<testsuite>``/``<testcase>`` writer):

* every skipped test case with its type and reason (``<skipped message=…>``);
* skips matching a ``--critical`` regex (on ``classname::name``, file and
  reason) are ``critical_skipped`` errors: the required test did not run;
* a ``--critical`` pattern that matches no test case at all is
  ``critical_absent`` (the test was not even collected);
* failures and errors are ``test_failed``; zero test cases is ``no_tests``
  (an empty run is not a pass); other skips are ``skipped`` info, or warnings
  with ``--fail-on-skip``.
* expected failures are counted apart from skips (2026-11-20): ``xfailed``
  (``<skipped type="pytest.xfail">``) is a warning, because a sealed prediction
  test marked xfail hides whether its prediction held; a strict XPASS
  (``<failure message="[XPASS(strict)] ...">``) is ``xpassed``, an error. A
  ``--critical`` match on an xfail is ``critical_skipped`` as before. pytest's
  JUnit XML does not record whether an xfail is strict, and writes a non-strict
  XPASS as a plain pass, so ``strict`` is ``null`` for xfails and non-strict
  XPASSes cannot be seen here.

Usage:
    python junit_skips.py JUNIT_XML_OR_GLOB [...] [--critical REGEX ...]
        [--fail-on-skip] [--out REPORT] [--format md|json] [--fail-on error|warning]

Exit codes: 0 nothing at ``--fail-on`` level, 1 findings, 2 input error, 3 bug.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# The JUnit files are local pytest output, not untrusted downloads; expat in
# Python 3.13 also refuses entity expansion attacks (billion laughs).
from xml.etree import ElementTree  # nosec B405

# `python -I` (safe_path) does not put the script's folder on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _cli import InputError, ToolOutcome, configure_console, parse_arguments, run_tool
from _files import expand_file_patterns, require_output_outside
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
    sort_findings,
)

TOOL_NAME = "junit_skips"
OUTCOME_TAGS = ("failure", "error", "skipped")
TAG_OUTCOMES = {"failure": "failed", "error": "error", "skipped": "skipped"}
XFAIL_TYPE = "pytest.xfail"
STRICT_XPASS_PREFIX = "[XPASS(strict)]"
MAX_REASON_CHARS = 200
STRICT_TEXT = {"True": "예", "False": "아니오"}  # None (not recorded) -> "-"


@dataclass(frozen=True)
class TestCase:
    """One ``<testcase>`` and its outcome.

    ``outcome`` is ``passed``, ``failed``, ``error``, ``skipped``, ``xfailed`` or
    ``xpassed``. ``strict`` is known only for a strict XPASS (``True``); JUnit
    XML does not say whether an xfail is strict (``None``).
    """

    report: Path
    classname: str
    name: str
    file: str
    outcome: str
    kind: str
    reason: str
    strict: bool | None = None

    @property
    def node_id(self) -> str:
        return f"{self.classname}::{self.name}" if self.classname else self.name

    def subject(self) -> str:
        """Text the ``--critical`` patterns are matched against."""
        return " ".join(part for part in (self.node_id, self.file, self.reason) if part)

    def to_dict(self) -> dict[str, object]:
        return {
            "report": str(self.report),
            "node_id": self.node_id,
            "file": self.file,
            "outcome": self.outcome,
            "type": self.kind,
            "reason": self.reason,
            "strict": self.strict,
        }


@dataclass(frozen=True)
class Outcome:
    """What the first failure/error/skipped child of a ``<testcase>`` says."""

    outcome: str
    kind: str = ""
    reason: str = ""
    strict: bool | None = None


def _outcome_of(element: ElementTree.Element) -> Outcome:
    """The outcome from the first failure/error/skipped child (none = passed)."""
    for tag in OUTCOME_TAGS:
        child = element.find(tag)
        if child is None:
            continue
        message = child.get("message") or (child.text or "").strip()
        reason = " ".join(message.split())
        kind = child.get("type", "")
        if tag == "skipped" and kind == XFAIL_TYPE:
            return Outcome("xfailed", kind, reason[:MAX_REASON_CHARS])
        if tag == "failure" and reason.startswith(STRICT_XPASS_PREFIX):
            unexpected_pass = reason.removeprefix(STRICT_XPASS_PREFIX).strip()
            return Outcome("xpassed", kind, unexpected_pass[:MAX_REASON_CHARS], True)
        return Outcome(TAG_OUTCOMES[tag], kind, reason[:MAX_REASON_CHARS])
    return Outcome("passed")


def read_test_cases(path: Path) -> list[TestCase]:
    """Every ``<testcase>`` of one JUnit XML file.

    Raises:
        InputError: If the file cannot be read or is not XML.
    """
    try:
        tree = ElementTree.parse(path)  # nosec B314 - local test report
    except (OSError, ElementTree.ParseError) as error:
        raise InputError(f"cannot read JUnit XML {path}: {error}") from error
    cases = []
    for element in tree.getroot().iter("testcase"):
        outcome = _outcome_of(element)
        cases.append(
            TestCase(
                report=path,
                classname=element.get("classname", ""),
                name=element.get("name", ""),
                file=element.get("file", ""),
                outcome=outcome.outcome,
                kind=outcome.kind,
                reason=outcome.reason,
                strict=outcome.strict,
            )
        )
    return cases


def _finding(case: TestCase, severity: Severity, category: str, text: str) -> Finding:
    return Finding(
        severity, category, str(case.report), 0, f"{case.node_id}: {text}", case.node_id
    )


def _critical_skip_finding(case: TestCase, matched: list[str]) -> Finding:
    what = "예상 실패(xfail)로 가려짐" if case.outcome == "xfailed" else "건너뜀"
    text = (
        f"필수 시험이 {what} = 미실행 (패턴 {', '.join(matched)}, "
        f"사유: {case.reason or '-'})"
    )
    return _finding(case, Severity.ERROR, "critical_skipped", text)


def _skip_finding(case: TestCase, fail_on_skip: bool) -> Finding:
    if case.outcome == "xfailed":
        text = (
            f"예상 실패(xfail, strict 여부는 JUnit에 없음): {case.reason or '-'} "
            "— 예측 시험이면 결과가 가려진다"
        )
        return _finding(case, Severity.WARNING, "xfailed", text)
    severity = Severity.WARNING if fail_on_skip else Severity.INFO
    text = f"건너뜀 ({case.kind or '-'}: {case.reason or '-'})"
    return _finding(case, severity, "skipped", text)


def case_findings(
    cases: list[TestCase], critical: list[re.Pattern[str]], fail_on_skip: bool
) -> list[Finding]:
    """Failures, XPASSes, (critical) skips and xfails of the test cases.

    Also used by ``worktree_tests.py``.
    """
    findings = []
    for case in cases:
        if case.outcome in ("failed", "error"):
            text = f"{case.outcome} ({case.reason or case.kind or '사유 없음'})"
            findings.append(_finding(case, Severity.ERROR, "test_failed", text))
        elif case.outcome == "xpassed":
            text = f"예상 실패가 통과함(XPASS, strict): {case.reason or '-'}"
            findings.append(_finding(case, Severity.ERROR, "xpassed", text))
        elif case.outcome in ("skipped", "xfailed"):
            subject = case.subject()
            matched = [item.pattern for item in critical if item.search(subject)]
            if matched:
                findings.append(_critical_skip_finding(case, matched))
            else:
                findings.append(_skip_finding(case, fail_on_skip))
    return findings


def _absent_findings(
    cases: list[TestCase], critical: list[re.Pattern[str]], reports: list[Path]
) -> list[Finding]:
    findings = []
    for pattern in critical:
        if not any(pattern.search(case.subject()) for case in cases):
            message = f"`--critical {pattern.pattern}`에 맞는 시험이 하나도 없음(수집되지 않음)"
            findings.append(
                Finding(
                    Severity.ERROR,
                    "critical_absent",
                    str(reports[0]),
                    0,
                    message,
                    pattern.pattern,
                )
            )
    return findings


def _markdown(report: dict[str, object], findings: list[Finding]) -> list[str]:
    summary = report["summary"]
    counts = (
        f"- 보고서 {summary['reports']}개, 시험 {summary['tests']}개: "
        f"통과 {summary['passed']}, 실패 {summary['failed']}, 오류 {summary['errors']}, "
        f"건너뜀 {summary['skipped']}, 예상 실패 {summary['xfailed']}, "
        f"예상 실패 통과 {summary['xpassed']}(필수 {summary['critical_skipped']})"
    )
    return [
        "# 시험 건너뜀 점검 (junit_skips)",
        "",
        counts,
        (
            "- 건너뜀·예상 실패는 통과가 아니다. "
            "필수 시험의 건너뜀·예상 실패는 미실행으로 센다."
        ),
        (
            "- JUnit XML에는 xfail의 strict 여부가 없고, "
            "strict 아닌 XPASS는 통과로 적힌다."
        ),
        "",
        "## 건너뜀",
        "",
        *_case_table(report["cases"], "skipped", "건너뛴 시험 없음."),
        "",
        "## 예상 실패 (xfail·XPASS)",
        "",
        *_case_table(report["cases"], ("xfailed", "xpassed"), "예상 실패 없음."),
        "",
        "## 발견 사항",
        "",
        *findings_markdown(findings),
    ]


def _case_table(
    cases: list[dict[str, object]], outcomes: str | tuple[str, ...], empty_text: str
) -> list[str]:
    wanted = (outcomes,) if isinstance(outcomes, str) else outcomes
    selected = [item for item in cases if item["outcome"] in wanted]
    if not selected:
        return [empty_text]
    lines = ["| 시험 | 결과 | 종류 | strict | 사유 |", "|---|---|---|---|---|"]
    for item in selected:
        reason = str(item["reason"]).replace("|", "\\|") or "-"
        strict = STRICT_TEXT.get(str(item["strict"]), "-")
        lines.append(
            f"| `{item['node_id']}` | {item['outcome']} | {item['type'] or '-'} "
            f"| {strict} | {reason} |"
        )
    return lines


def run_junit_skips(args: argparse.Namespace) -> ToolOutcome:
    """List skipped tests and flag required ones that did not run."""
    try:
        critical = [re.compile(pattern) for pattern in args.critical or []]
    except re.error as error:
        raise InputError(f"invalid --critical regex: {error}") from error
    reports = expand_file_patterns(args.reports, Path.cwd())
    require_output_outside(args.out, reports)
    cases = [case for path in reports for case in read_test_cases(path)]

    findings = case_findings(cases, critical, args.fail_on_skip)
    findings += _absent_findings(cases, critical, reports)
    if not cases:
        message = "시험 0개: 빈 실행은 통과가 아니다"
        findings.append(
            Finding(Severity.ERROR, "no_tests", str(reports[0]), 0, message)
        )
    findings = sort_findings(findings)

    def count(outcome: str) -> int:
        return sum(1 for case in cases if case.outcome == outcome)

    summary = {
        "tool": TOOL_NAME,
        "command": "check",
        "reports": len(reports),
        "tests": len(cases),
        "passed": count("passed"),
        "failed": count("failed"),
        "errors": count("error"),
        "skipped": count("skipped"),
        "xfailed": count("xfailed"),
        "xpassed": count("xpassed"),
        "critical_skipped": sum(
            1 for item in findings if item.category == "critical_skipped"
        ),
        **count_by_severity(findings),
        "categories": count_by_category(findings),
    }
    report = {
        "tool": TOOL_NAME,
        "critical": [pattern.pattern for pattern in critical],
        "cases": [case.to_dict() for case in cases if case.outcome != "passed"],
        "summary": summary,
        "findings": [finding_to_dict(item) for item in findings],
    }
    lines = deliver_report(args, _markdown(report, findings), report, reports)
    return ToolOutcome(exit_code_for(findings, Severity(args.fail_on)), lines, summary)


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="junit_skips.py",
        description=(
            "JUnit XML에서 건너뛴 시험·예상 실패(xfail·XPASS)와 사유를 뽑고, "
            "필수 시험의 건너뜀을 미실행으로 표시한다."
        ),
    )
    parser.add_argument("reports", nargs="+", help="JUnit XML files or glob patterns")
    parser.add_argument(
        "--critical",
        action="append",
        metavar="REGEX",
        help="tests that must run (classname::name, file or reason); repeatable",
    )
    parser.add_argument(
        "--fail-on-skip",
        action="store_true",
        help="report every other skip as a warning (xfails are warnings already)",
    )
    add_report_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the exit code."""
    configure_console()
    args = parse_arguments(build_parser(), argv)
    return run_tool(lambda: run_junit_skips(args))


if __name__ == "__main__":
    sys.exit(main())
