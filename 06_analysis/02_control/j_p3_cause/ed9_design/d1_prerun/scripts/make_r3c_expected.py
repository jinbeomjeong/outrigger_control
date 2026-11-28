"""R3c ⑥② allowed set (audit ``audit_r3_prerun/report.md`` M-4): the 9 unique jobs control
``ed9_design/control_cm_switch/report.md`` 2.4 expects to change with C-m (a D1_step FAULT in
C0), as job keys in the ``compare_identity.py --allowed-from`` form.

The labels are those of control 2.4 (table row 1), named as in ``r3c_jobs.json``: J1
(= J1shape_o0.0875), J4, S1 and J1shape o 0.0835 / 0.0845 / 0.0855 / 0.0865 / 0.0885 / 0.0895.
Only job definitions are read. The output records the label list, its source and the
``r3c_jobs.json`` sha256; ``groups.r3c_expected.d1_step_keys`` holds the job keys.

Usage (python-dev ``python.exe -I -B``)::

    python make_r3c_expected.py --jobs <r3c_jobs.json> --out <r3c_expected_d1_step.json>

Exit codes: 0 written; 2 input error (a missing label or file, an existing ``--out``).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

GROUP = "r3c_expected"
EXPECTED_LABELS = ("J1_l179_FR_Fs0_level_30mm004_o0875", "J4_l270_FR_Fs1_ready_default_o0875",
                   "S1_l173_FL_Fs2_level_30mm004_o0875", "J1shape_o0.0835", "J1shape_o0.0845",
                   "J1shape_o0.0855", "J1shape_o0.0865", "J1shape_o0.0885", "J1shape_o0.0895")
"""Control 2.4 row 1 (9 unique jobs; J1 is also J1shape_o0.0875)."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists() or not args.jobs.is_file():
        print(json.dumps({"status": "input_error"}))
        return 2
    entries = json.loads(args.jobs.read_text(encoding="utf-8"))
    by_label = {}
    for entry in entries:
        for label in entry["labels"]:
            by_label[label] = entry["job"]
    missing = [label for label in EXPECTED_LABELS if label not in by_label]
    if missing:
        print(json.dumps({"status": "input_error", "missing_labels": missing}))
        return 2
    keys = [json.dumps(by_label[label], sort_keys=True) for label in EXPECTED_LABELS]
    if len(set(keys)) != len(EXPECTED_LABELS):
        print(json.dumps({"status": "input_error", "reason": "repeated jobs"}))
        return 2
    document = {"rule": "control_cm_switch/report.md 2.4 row 1 (C0 D1_step FAULT jobs, "
                        "expected to change with C-m); audit M-4",
                "source_jobs": {"path": str(args.jobs),
                                "sha256": hashlib.sha256(args.jobs.read_bytes()).hexdigest()},
                "labels": list(EXPECTED_LABELS),
                "groups": {GROUP: {"d1_step_keys": keys, "d1_step_lines": len(keys)}}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(document, handle, indent=1)
    print(json.dumps({"status": "ok", "jobs": len(keys), "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
