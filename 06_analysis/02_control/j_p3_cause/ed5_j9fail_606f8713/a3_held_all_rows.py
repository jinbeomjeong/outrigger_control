"""j9_main 606f8713 failure analysis, step A3: LEVEL gate-hold fraction on every row (read only).

held fraction = LEVEL leg-reads with the plant locked and |u| > 1e-6 m/s divided by LEVEL
leg-reads with |u| > 1e-6 m/s (T4h, 10 Hz reads, T_s 0.1 s). Stored VB (old plant) 100 rows
against VBJ / LSJ1..4 (P1..P4 plant + ③ rev 6) 388 rows. First READY [s] from the row values.

Outputs (this folder): a3_held_all.csv, a3_summary.json
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
V5 = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
RUN = ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "j9_runs" / "606f8713" / "j9main_a1"
OUT = Path(__file__).resolve().parent
EPS = 1.0e-6


def held_fraction(path: Path) -> tuple[float, int]:
    z = np.load(path, allow_pickle=False)
    ph = np.char.lower(z["phase"].astype(str))
    u = np.abs(z["command_m_s"])
    lv = (ph == "level")[:, None]
    cmd = lv & (u > EPS)
    held = cmd & z["locked"]
    return float(held.sum() / max(cmd.sum(), 1)), int(held.sum())


def main() -> None:
    recs = []
    for src, base, settings in ((V5 / "main.jsonl", V5 / "main" / "t4h", {"VB"}),
                                (RUN / "j9_main.jsonl", RUN / "j9_main_t4h", None)):
        with open(src, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                s = d["job"]["setting"]
                if settings and s not in settings:
                    continue
                hf, n = held_fraction(base / d["t4h_file"])
                recs.append({"key": d["t4h_file"].rsplit("_", 1)[0], "setting": s,
                             "final_phase": d.get("final_phase"),
                             "t_first_ready_s": d["values"]["times"].get("t_first_ready_s"),
                             "held_fraction": round(hf, 4), "held_leg_reads": n})
    with open(OUT / "a3_held_all.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(recs[0].keys()))
        w.writeheader()
        w.writerows(recs)
    vb = {r["key"]: r for r in recs if r["setting"] == "VB"}
    summ = {}
    for s in ("VB", "VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4"):
        rs = [r for r in recs if r["setting"] == s]
        hf = np.array([r["held_fraction"] for r in rs])
        not_ready = [r for r in rs if r["final_phase"] != "ready" and not r["key"].startswith("S8")]
        summ[s] = {"rows": len(rs), "held_fraction_max": float(hf.max()),
                   "rows_held_gt_0p10": int((hf > 0.10).sum()),
                   "rows_held_gt_0p10_keys": sorted(r["key"] for r in rs if r["held_fraction"] > 0.10),
                   "rows_not_ready_excl_S8": len(not_ready),
                   "not_ready_held_min": (min(r["held_fraction"] for r in not_ready) if not_ready else None)}
        if s != "VB":
            dts = [r["t_first_ready_s"] - vb[r["key"]]["t_first_ready_s"] for r in rs
                   if r["key"] in vb and r["t_first_ready_s"] is not None
                   and vb[r["key"]]["t_first_ready_s"] is not None]
            summ[s]["first_ready_minus_VB_s"] = {"n": len(dts), "median": float(np.median(dts)),
                                                 "p90": float(np.percentile(dts, 90)), "max": float(max(dts))}
    with open(OUT / "a3_summary.json", "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
