"""436.9 edition 8 stage 4 judgement: P8-4 junit counts of the gate-bearing tests (C axis).

Counts, per JUnit file (T8'''' formal, T8''' formal), the tests and their states, and for the
gate-bearing test files (P8-6, P8-10, P8-11 run-path, edition 8 judge tests and the new P8-0
key tests) the passed / failed / error / skipped counts. Prints test names only for the
non-passed tests of those files. No test output text is printed.

Usage (python-dev): python.exe -X utf8 -I -B junit_critical_stage4.py OUT_JSON
Exit: 0 no gate-bearing test is failed, an error or skipped / 1 otherwise / 2 an input error.
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ED8 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design")
JUNITS = {
    "T8pppp_7ea78232": ED8 / "p84_suite_T8pppp_7ea78232" / "junit_T8pppp_7ea78232.xml",
    "T8ppp_2263b246": ED8 / "p84_suite_T8ppp_2263b246" / "junit_T8ppp_2263b246.xml",
}
GROUPS = {
    "P8-6 (test_p86*)": r"(::|\.)test_p86",
    "P8-10 (test_p8_10*)": r"(::|\.)test_p8_10",
    "P8-11 (test_ed8_run_path)": r"\.test_ed8_run_path::",
    "P8-0 key (test_ed8_gate_p80_key)": r"\.test_ed8_gate_p80_key::",
    "gate judge (test_ed8_gate_judge)": r"\.test_ed8_gate_judge::",
    "D-1 settings (test_ed8_jp3_settings)": r"\.test_ed8_jp3_settings::",
    "all test_ed8_*": r"\.test_ed8_",
}


def state(case: ET.Element) -> str:
    for tag in ("failure", "error", "skipped"):
        if case.find(tag) is not None:
            return tag
    return "passed"


def main(argv: list[str]) -> int:
    if len(argv) != 1 or Path(argv[0]).exists():
        print(json.dumps({"status": "input_error"}))
        return 2
    result, bad = {}, False
    for name, path in JUNITS.items():
        cases = [(f"{c.get('classname')}::{c.get('name')}", state(c))
                 for c in ET.parse(path).getroot().iter("testcase")]
        groups = {}
        for label, pattern in GROUPS.items():
            hit = [(n, s) for n, s in cases if re.search(pattern, n)]
            groups[label] = {"tests": len(hit), "states": dict(Counter(s for _, s in hit)),
                             "not_passed": sorted(n for n, s in hit if s != "passed")}
            bad |= name.startswith("T8pppp") and bool(groups[label]["not_passed"])
        result[name] = {"tests": len(cases), "states": dict(Counter(s for _, s in cases)),
                        "failed_or_error": sorted(n for n, s in cases if s in ("failure", "error")),
                        "groups": groups}
    result["summary"] = {"gate_tests_all_passed_T8pppp": not bad}
    Path(argv[0]).write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                             encoding="utf-8", newline="\n")
    print(json.dumps(result["summary"]))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
