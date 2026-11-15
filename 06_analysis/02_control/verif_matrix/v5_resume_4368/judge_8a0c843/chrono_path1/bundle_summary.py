"""Summary of one chrono_bundle_grade output: stops, t_lift checks, unjudged items, row grades.

Usage: python -I -B bundle_summary.py <bundle_<B>.json> <out.txt>
"""

import json
import sys
from pathlib import Path


def main() -> int:
    doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    lines = [f"bundle {doc['bundle']}", f"grade {json.dumps(doc.get('bundle_grade'), ensure_ascii=False)}"]
    lines += [f"stop {s['case']}: {s['reason']}" for s in doc.get("stops", [])]
    t_lift = doc.get("runner_t_lift_R19_5") or {}
    lines.append(f"t_lift present {t_lift.get('present')} max {t_lift.get('max_difference_s')} "
                 f"stop_rows {t_lift.get('stop_rows')}")
    for case, check in (t_lift.get("checks") or {}).items():
        lines.append(f"  {case}: runner {check.get('runner_t_lift_s')} (rel "
                     f"{check.get('runner_liftoff_rel_s')}, t0 {check.get('t0_s')}) D-29 "
                     f"{check.get('t_lift_D29_s')} -> 10Hz {check.get('t_lift_D29_10Hz_s')} "
                     f"basis {check.get('basis')} diff {check.get('difference_s')} "
                     f"stop {check.get('stop')}")
    unjudged = doc.get("runner_unjudged_R19_4") or {}
    lines.append(f"unjudged {unjudged.get('count')} {unjudged.get('items')} "
                 f"unknown {unjudged.get('unknown_kind_items')}")
    for row in doc.get("rows", []):
        lines.append(f"row {row['case']} {row.get('role')} {row.get('grade')} "
                     f"judged_true {row['items'][0].get('judged_true_items') if row.get('items') else None} "
                     f"missing {row.get('missing_inputs')} "
                     f"count_ok {(row.get('runner_count_check_R19_4') or {}).get('ok')}")
    Path(sys.argv[2]).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
