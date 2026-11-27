"""436.9 edition 8 stage 4 judgement: P8-4 against the rule baseline (spec 12 P8-4, 364 행).

The rule baseline of P8-4 is the parent of C8 (41e107e9). The formal T8''' / T8'''' suites were
compared with the previous judge commit, not with that baseline, and ran in a judge worktree
without ``07_results`` (plain pytest, OUTRIGGER_RECORDS_ROOT set), while the C8 suite ran through
tools/verif/worktree_tests.py (main checkout data attached). This script counts, for each test
of the T8'''' formal junit, its state in the C8-parent baseline junit and in the C8 run junit,
and reports the skipped / failed tests of T8'''' that passed in the baseline, split by the core
patterns of the P8-4 judgement (suite_judgement.json ``core_patterns``). Test names and skip
reasons are printed for those tests only; no test output text.

Usage (python-dev): python.exe -X utf8 -I -B p84_baseline_chain_stage4.py OUT_JSON
Exit: 0 written / 2 an input error.
"""
from __future__ import annotations

import fnmatch
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ED8 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design")
FILES = {
    "base_41e107e9": ED8 / "p84_suite_41e107e9_56849248" / "base" / "junit.xml",
    "run_C8_56849248": ED8 / "p84_suite_41e107e9_56849248" / "run" / "junit.xml",
    # C8 in a plain judge-style worktree run (implementation report, no main data attached)
    "C8_plain_56849248": ED8 / "impl_report_ed8" / "tests" / "junit_C8_56849248.xml",
    "T8ppp_2263b246": ED8 / "p84_suite_T8ppp_2263b246" / "junit_T8ppp_2263b246.xml",
    "T8pppp_7ea78232": ED8 / "p84_suite_T8pppp_7ea78232" / "junit_T8pppp_7ea78232.xml",
}
CORE = ("test_jp3_*", "test_ed6_*", "test_run_v5*", "test_lock_start_b*", "test_c2*",
        "test_extend_start_bound*")


def cases(path: Path) -> dict[str, tuple[str, str]]:
    out = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        name = f"{case.get('classname')}::{case.get('name')}"
        state, reason = "passed", ""
        for tag in ("failure", "error", "skipped"):
            element = case.find(tag)
            if element is not None:
                state, reason = tag, (element.get("message") or "")[:160]
                break
        out[name] = (state, reason)
    return out


def is_core(name: str) -> bool:
    module = name.split("::", 1)[0].rsplit(".", 1)[-1]
    return any(fnmatch.fnmatch(module, pattern) for pattern in CORE)


def main(argv: list[str]) -> int:
    if len(argv) != 1 or Path(argv[0]).exists():
        print(json.dumps({"status": "input_error"}))
        return 2
    data = {label: cases(path) for label, path in FILES.items()}
    summary = {label: {"tests": len(c), "states": dict(Counter(s for s, _ in c.values()))}
               for label, c in data.items()}
    base, run, new = data["base_41e107e9"], data["run_C8_56849248"], data["T8pppp_7ea78232"]
    plain = data["C8_plain_56849248"]
    rows = []
    for name, (state, reason) in sorted(new.items()):
        if state == "passed":
            continue
        rows.append({"test": name, "T8pppp": state, "reason": reason,
                     "base_41e107e9": base.get(name, ("absent", ""))[0],
                     "run_C8": run.get(name, ("absent", ""))[0],
                     "C8_plain": plain.get(name, ("absent", ""))[0], "core": is_core(name)})
    passed_in_base = [r for r in rows if r["base_41e107e9"] == "passed"]
    result = {
        "summary": summary,
        "T8pppp_not_passed_by_C8_plain_state": dict(Counter(r["C8_plain"] for r in rows)),
        "T8pppp_not_passed_but_passed_in_C8_plain": sorted(
            r["test"] for r in rows if r["C8_plain"] == "passed"),
        "T8pppp_not_passed": len(rows),
        "T8pppp_not_passed_by_base_state": dict(Counter(r["base_41e107e9"] for r in rows)),
        "T8pppp_not_passed_but_passed_in_base": len(passed_in_base),
        "of_which_core": sum(r["core"] for r in passed_in_base),
        "of_which_skipped": sum(r["T8pppp"] == "skipped" for r in passed_in_base),
        "of_which_failed": sum(r["T8pppp"] in ("failure", "error") for r in passed_in_base),
        "skip_reasons_of_those": dict(Counter(
            ("07_results/... not present" if "not present" in r["reason"] else r["reason"][:60])
            for r in passed_in_base if r["T8pppp"] == "skipped")),
        "core_tests_not_passed_T8pppp": sorted(r["test"] for r in rows if r["core"]),
        "tests_new_since_C8_run": sum(1 for n in new if n not in run),
        "rows": rows,
    }
    Path(argv[0]).write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                             encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in (
        "T8pppp_not_passed_by_C8_plain_state", "T8pppp_not_passed_but_passed_in_C8_plain",
        "T8pppp_not_passed", "T8pppp_not_passed_by_base_state",
        "T8pppp_not_passed_but_passed_in_base", "of_which_core", "of_which_skipped",
        "of_which_failed", "tests_new_since_C8_run")}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
