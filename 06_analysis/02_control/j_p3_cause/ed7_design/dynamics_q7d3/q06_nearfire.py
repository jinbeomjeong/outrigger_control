"""Q7-D3: near-fire reads of the A_ib blind counter while |D_ctl| > 15 kN in LEVEL
(a2 repro). For each line take the read with the largest stretch count among
|D|>15 reads; report leg, time since event, D, the leg's acting command and
whether a shot in that command's sign would reduce |D| (rank-1 sign n_i*u_i vs D)."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\b46bdf8f\repro_a2")
N_TW = np.array([0.4761, -0.4761, -0.5228, 0.5228])
LEGS = ("FL", "FR", "RL", "RR")
U_HOLD = 0.209243e-3
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
a = ap.parse_args()
rows = []
with open(RUN / "ed7_probe_a2.jsonl", encoding="utf-8") as fh:
    for raw in fh:
        rec = json.loads(raw)
        key = Path(rec["t4h_file"]).stem
        z = np.load(RUN / "ed7_probe_a2_t4h" / Path(rec["t4h_file"]).name, allow_pickle=False)
        t = z["t_s"]
        ph = z["phase"]
        Dc = z["lsb_ib_twist_load_N"]
        st = z["lsb_ib_stretch_periods"]
        uin = z["lsb_input_m_s"]
        over = (ph == "level") & np.isfinite(Dc) & (np.abs(Dc) > 15e3)
        if not over.any():
            continue
        s_over = np.where(over[:, None], st, -1)
        i, j = np.unravel_index(np.argmax(s_over), s_over.shape)
        te = rec.get("t_event_s")
        # how many legs simultaneously blind with stretch >= 10 at that read
        nblind = int(np.sum(st[i] >= 10))
        u = uin[i, j]
        reduces = np.sign(N_TW[j] * u) != np.sign(Dc[i])
        # all blind legs: twist-sign pattern?
        sgn = np.sign(uin[i])
        twist_pattern = bool(np.all(sgn != 0) and (np.all(sgn == np.sign(N_TW)) or np.all(sgn == -np.sign(N_TW))))
        rows.append({"line": key, "t_s": round(float(t[i]), 2), "t_since_event_s": round(float(t[i] - te), 2) if te is not None else None,
                     "leg": LEGS[j], "stretch": int(st[i, j]), "D_kN": round(float(Dc[i]) / 1e3, 2),
                     "u_mm_s": round(float(u) * 1e3, 4), "u_over_hold": round(float(abs(u) / U_HOLD), 3),
                     "reduces_absD": bool(reduces), "legs_stretch_ge10": nblind,
                     "all4_twist_sign_pattern": twist_pattern,
                     "u_all_mm_s": [round(float(x) * 1e3, 4) for x in uin[i]]})
df = pd.DataFrame(rows).sort_values("stretch", ascending=False)
df.to_csv(Path(a.out).with_suffix(".csv"), index=False)
L = []
L.append(f"lines {len(df)}; stretch>=20: {int((df.stretch>=20).sum())}, >=14: {int((df.stretch>=14).sum())}")
L.append("top rows:\n" + df.head(15).to_string())
L.append("reduces_absD among stretch>=14: " + df[df.stretch >= 14].reduces_absD.value_counts().to_string().replace("\n", " | "))
L.append("all4 twist pattern among stretch>=14: " + df[df.stretch >= 14].all4_twist_sign_pattern.value_counts().to_string().replace("\n", " | "))
L.append("t_since_event among stretch>=14: " + df[df.stretch >= 14].t_since_event_s.describe().round(2).to_string().replace("\n", " | "))
txt = "\n".join(L)
Path(a.out).write_text(txt, encoding="utf-8")
print(txt)
