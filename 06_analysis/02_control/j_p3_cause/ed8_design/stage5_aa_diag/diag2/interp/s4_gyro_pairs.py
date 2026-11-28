"""Interp diag2 step 1: for each B (gyro to all consumers) trace, the periods k (before the step)
and k+1 (the step) of the primary monitor: residual r with the lever correction, the lever term
M lever_z, raw f_z, and the diag1 r without it. Writes interp/gyro_pairs.csv."""
import csv
import json
import sys
from pathlib import Path

D2 = Path(sys.argv[1])
D1 = D2.parent
first_b = {r["label"]: r for r in csv.DictReader(open(D2 / "first_step_period_B.csv", encoding="utf-8"))}
d1 = list(csv.DictReader(open(D1 / "interp" / "residual_split.csv", encoding="utf-8")))


def rows_of(path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(doc, dict):
        for key in ("rows", "trace", "periods"):
            if key in doc:
                return doc[key]
        raise KeyError(list(doc)[:10])
    return doc


out = []
for path in sorted((D2 / "traces_B").glob("trace_*.json")):
    label = path.stem[len("trace_"):]
    f = first_b[label]
    t_step = float(f["t_s"])
    rows = rows_of(path)
    step_rows = [r for r in rows if abs(float(r["t_s"]) - t_step) < 1e-6 and r.get("residual_change_N") is not None
                 and r.get("head_step_candidates")]
    mon = step_rows[0]["monitor"]
    mine = sorted([r for r in rows if r["monitor"] == mon], key=lambda r: float(r["t_s"]))
    i = next(j for j, r in enumerate(mine) if abs(float(r["t_s"]) - t_step) < 1e-6)
    for tag, r in (("k", mine[i - 1]), ("k+1", mine[i])):
        m = r.get("mass_kg")
        lev = r.get("lever_z_m_s2")
        a = next((x for x in d1 if x["label"] == label[:2] and abs(float(x["t_s"]) - float(r["t_s"])) < 1e-3), None)
        out.append({"label": label[:2], "period": tag, "t_s": round(float(r["t_s"]), 3),
                    "f_z_raw": r.get("f_z_raw_m_s2"), "lever_z_m_s2": lev,
                    "M_lever_kN": None if (lev is None or m is None) else round(m * lev / 1e3, 2),
                    "r_B_kN": None if r.get("residual_N") is None else round(r["residual_N"] / 1e3, 2),
                    "r_diag1_kN": None if a is None else a["residual_kN"],
                    "lever_share_estimate_diag1_kN": None if a is None else a["lever_share_kN"],
                    "dr_B_kN": None if r.get("residual_change_N") is None else round(r["residual_change_N"] / 1e3, 2)})
with open(D2 / "interp" / "gyro_pairs.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)
for o in out:
    print(o)
