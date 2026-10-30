"""Check the final B5 main run (16 table cases) against the wide run and the inferred values; finalize the TBD table.

Checks: meta r72_path_env / controller_settings, every (case, controller) present and error-free, the 12 cases with a
wide twin equal by command hash and table cells, the 4 override cases (A4, B2) equal to the inferred (previous) cells,
and the figure / table files newer than the main run. Updates <tbd json> in place: every C2 cell from the main run,
status 'final (fin_b5_main)'.
Usage (dynamics-dev): python -I b5_final_main_check.py <project root> <tbd json> <out json>
"""
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
TBD = Path(sys.argv[2])
OUT = Path(sys.argv[3])
R = ROOT / "06_analysis" / "02_control" / "s9" / "rev84"
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))
from b5_baseline_compare import CASES  # noqa: E402
from b5_baseline_table import backfill_gates, cells  # noqa: E402

CTRL = ("C2", "ABL", "IND")
KEYS = ("att", "ready", "fmin", "crawler", "p")
TAG = {"att": "att", "READY": "ready", "minF": "fmin", "gap": "crawler", "pmax": "p"}


def load(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    for r in d["records"]:
        backfill_gates(r)
    return d


main = load(R / "fin_b5_main.json")
wide = {(r["case"], r["controller"]): r for r in load(R / "fin2_b5_wide_official.json")["records"]}
old_main = {(r["case"], r["controller"]): r for r in load(R / "b5_main.json")["records"]}
mrec = {(r["case"], r["controller"]): r for r in main["records"]}
res = {"meta": {k: main["meta"].get(k) for k in ("jobs", "workers", "wall_s", "affinity", "r72_path_env",
                                                   "controller_settings", "official")},
       "missing": [(c, k) for c in CASES for k in CTRL if (c, k) not in mrec],
       "errors": [k for k, r in mrec.items() if "error" in r], "cases": {}}
g6 = [r for r in main["records"] if CASES[r["case"]]["harness"] == "g6"]
res["g6_soil_model"] = sorted({(r["case"], r.get("soil_model"), r.get("r72_path")) for r in g6})
for case, spec in CASES.items():
    plain = not any(k in spec for k in ("fs_kN", "event", "hold_s"))
    new_cells = cells({k: mrec[(case, k)] for k in CTRL})
    row = {"cells": new_cells}
    if plain:
        wid = ("S|" if spec["harness"] == "slope" else "G|") + spec["src"]
        row["vs_wide_hash"] = {k: mrec[(case, k)]["commands_sha256"] == wide[(wid, k)]["commands_sha256"] for k in CTRL}
        row["vs_wide_cells"] = new_cells == cells({k: wide[(wid, k)] for k in CTRL})
    else:
        old_cells = cells({k: old_main[(case, k)] for k in CTRL})
        row["vs_inferred_cells"] = new_cells == old_cells
        row["vs_previous_hash"] = {k: mrec[(case, k)]["commands_sha256"] == old_main[(case, k)]["commands_sha256"]
                                   for k in CTRL}
        row["previous_cells"] = old_cells
    res["cases"][case] = row
main_mtime = (R / "fin_b5_main.json").stat().st_mtime
res["outputs_newer_than_main"] = {n: (R / n).exists() and (R / n).stat().st_mtime >= main_mtime
                                  for n in ("fin_b5_paper.md", "fin_b5_paper_rows.tex", "fin_b5_paper_summary.json",
                                            "fin_b5_figure.pdf", "fin_b5_figure.png")}
res["paper_summary"] = json.loads((R / "fin_b5_paper_summary.json").read_text(encoding="utf-8"))

tbd = json.loads(TBD.read_text(encoding="utf-8"))
changed = []
for key, entry in tbd.items():
    tag = key.rsplit(":", 1)[1].rstrip("]")
    value = res["cases"][entry["case"]]["cells"][TAG[tag]].split(" / ")[0]
    if value != entry["value"]:
        changed.append((key, entry["value"], value))
    entry["value"] = value
    entry["status"] = "final (fin_b5_main)"
TBD.write_text(json.dumps(tbd, indent=1, ensure_ascii=False), encoding="utf-8")
res["tbd_value_changes"] = changed
OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps({"meta": res["meta"], "missing": res["missing"], "errors": res["errors"],
                  "g6": res["g6_soil_model"], "outputs": res["outputs_newer_than_main"],
                  "tbd_changes": changed,
                  "rows": {c: {k: v for k, v in r.items() if k.startswith("vs_")} for c, r in res["cases"].items()},
                  "override_cells": {c: r["cells"] for c, r in res["cases"].items() if "vs_inferred_cells" in r}},
                 indent=1, ensure_ascii=True))
