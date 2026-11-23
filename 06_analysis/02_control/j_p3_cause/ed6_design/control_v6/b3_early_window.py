"""R12/G4 early-response window of the judged VBJ rows (606f8713 j9_main T4h, read only).

For each R12 row (32 keys): first force-drop read of the minimum leg, R-5 relevel_predicted
time, re-approach start, and the LEVEL command between them decomposed with the sign-pattern
proxy heave = mean(u), twist = (u_FL - u_FR - u_RL + u_RR) / 4 (twist vector sign FL+, FR-,
RL-, RR+; residual = roll/pitch part). Speeds mm/s, forces kN, T_s 0.1 s, d = 1.
Output: b3_early_window.csv, b3_early_window.json (this folder). control-expert 2026-11-23.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\606f8713\j9main_a1")
OUT = Path(__file__).resolve().parent
LEGS = ("FL", "FR", "RL", "RR")
SIGN = np.array([1.0, -1.0, -1.0, 1.0])


def main() -> None:
    rows = []
    with open(RUN / "j9_main.jsonl", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d["job"]["setting"] != "VBJ" or d["job"]["case"] != "R12":
                continue
            z = np.load(RUN / "j9_main_t4h" / d["t4h_file"], allow_pickle=False)
            meta = json.loads(str(z["meta_json"]))
            t_ev = d["t_event_s"]
            ev = [(e[0], e[1]) for e in meta["events"] if e[0] >= t_ev - 1e-9]
            t_r5 = next((t for t, n in ev if n.startswith("relevel_predicted")), None)
            r5_leg = next((n.split(":")[1] for t, n in ev if n.startswith("relevel_predicted")), None)
            t_ra = next((t for t, n in ev if n.startswith("leg_reapproach_start")), None)
            t = z["t_s"]
            u = z["command_m_s"] * 1e3
            fmin = z["true_force_min_N"] / 1e3
            mfw = d["event_output"]["min_F_after_W_kN"]
            leg = LEGS.index(min(mfw, key=mfw.get))
            i0 = int(np.searchsorted(t, t_ev - 1e-9))
            base = fmin[i0, leg]
            drop = np.flatnonzero((t > t_ev) & (fmin[:, leg] < base - 1.0))
            t_drop = float(t[drop[0]]) if len(drop) else None
            # LEVEL reads after the R-5 read up to the re-approach decision read (its twist
            # command appears one read later, d = 1)
            win = (t > (t_r5 or 1e9) + 1e-9) & (t <= (t_ra or -1) + 1e-9)
            uw = u[win]
            heave = uw.mean(axis=1)
            twist = (uw @ SIGN) / 4.0
            resid = np.abs(uw - heave[:, None] - twist[:, None] * SIGN).max(axis=1) if len(uw) else np.array([])
            rows.append({
                "key": d["t4h_file"].rsplit("_", 1)[0], "min_leg": LEGS[leg], "r5_leg": r5_leg,
                "t_event_s": t_ev, "t_force_drop_s": t_drop, "t_relevel_predicted_s": t_r5,
                "t_reapproach_start_s": t_ra,
                "drop_to_r5_s": None if t_drop is None or t_r5 is None else round(t_r5 - t_drop, 2),
                "r5_to_reapproach_s": None if t_r5 is None or t_ra is None else round(t_ra - t_r5, 2),
                "window_reads": int(win.sum()),
                "heave_mean_mm_s": round(float(heave.mean()), 3) if len(uw) else None,
                "twist_mean_mm_s": round(float(twist.mean()), 3) if len(uw) else None,
                "resid_max_mm_s": round(float(resid.max()), 3) if len(uw) else None,
                "min_leg_force_at_r5_kN": None if t_r5 is None else round(float(fmin[np.searchsorted(t, t_r5 - 1e-9), leg]), 2),
            })
    with open(OUT / "b3_early_window.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    def stat(k):
        v = [r[k] for r in rows if r[k] is not None]
        return {"n": len(v), "min": min(v), "median": float(np.median(v)), "max": max(v)}

    summ = {k: stat(k) for k in ("drop_to_r5_s", "r5_to_reapproach_s", "window_reads", "heave_mean_mm_s",
                                 "twist_mean_mm_s", "resid_max_mm_s", "min_leg_force_at_r5_kN")}
    summ["rows"] = len(rows)
    summ["r5_leg_equals_min_leg"] = sum(1 for r in rows if r["r5_leg"] == r["min_leg"])
    (OUT / "b3_early_window.json").write_text(json.dumps(summ, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
