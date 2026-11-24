"""Summaries of the record-only judge outputs: j9main, sens (B_a1) and grid (A_a1): status,
status basis, failing units / items, cluster, R15 worsening, J7 exemptions, J-P3 rows."""
import json
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405"
            r"\records_after_stop")
FILES = {"j9main": ROOT / "B_a1/j9main_judge.json", "sens": ROOT / "B_a1/sens_judge.json",
         "grid": ROOT / "A_a1/grid_judge.json"}


def short(value, limit=1500):
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + f"... ({len(text)} chars)"


def main():
    for name, path in FILES.items():
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"===== {name}: keys {sorted(data)}")
        print("status", data.get("status"))
        print("basis", short(data.get("status_basis")))
        for key in ("failing_units", "cluster", "probe_unit_stops", "R15_worsening", "r15_worsening",
                    "vb_fail_pair_items", "vb_fail_by_item", "L-a", "L-b", "L-c", "L-e",
                    "stops", "J-P3_judged_rows", "opportunity_failures", "fault_lines",
                    "opportunities", "lines", "identity_defects", "not_judgeable_items",
                    "j7_stiffness_exempt", "warn_records"):
            if key in data:
                print(f"-- {key}: {short(data[key])}")


if __name__ == "__main__":
    main()
