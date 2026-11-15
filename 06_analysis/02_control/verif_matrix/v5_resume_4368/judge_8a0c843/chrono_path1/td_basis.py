"""Per bundle: the t_D definition chrono_rows_judge used (C-4 = R6-B4 count) and its runner
difference (R6-B4 record), from the R3b ``judge_<B>.json`` outputs.

Usage: python -I -B td_basis.py <folder> <out.json>
"""

import json
import sys
from pathlib import Path

BUNDLES = ("C1", "C2", "C3", "C4", "C5", "C6C7", "OC5PROBE", "OC5")


def main() -> int:
    folder, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    report = {}
    for bundle in BUNDLES:
        doc = json.loads((folder / f"judge_{bundle}.json").read_text(encoding="utf-8"))
        rules = sorted({row["items"]["departure_t_D"]["rule"] for row in doc["rows"]
                        if "departure_t_D" in row.get("items", {})})
        report[bundle] = {"C-4": doc["definitions_C"]["C-4"], "deviates": doc["deviates_from_rev6"],
                          "scm_rows": doc["t_D_vs_runner_R6_B4"]["scm_rows"],
                          "rows_differing_from_runner": doc["t_D_vs_runner_R6_B4"]["rows_differing"],
                          "max_abs_diff_s": doc["t_D_vs_runner_R6_B4"]["max_abs_diff_s"],
                          "rule_texts": rules, "stops": doc["stops"],
                          "grades": {row["case"]: row.get("grade") for row in doc["rows"]}}
    out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    for bundle, entry in report.items():
        print(bundle, entry["C-4"], entry["scm_rows"], entry["rows_differing_from_runner"],
              entry["max_abs_diff_s"], len(entry["stops"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
