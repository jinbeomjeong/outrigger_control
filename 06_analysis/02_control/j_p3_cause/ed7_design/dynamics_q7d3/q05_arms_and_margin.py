"""Q7-D3: (A) arm comparison a2/a3/a4 from the control probe-check shot table
(probe 6bfb2560, all arms), sanity match of a2 shots with the b46bdf8f repro;
(B) blind-stretch margin of the |D|>15 kN branch during LEVEL reads in the a2 repro
(how close the 25-period blind counter came while |D_ctl| > 15 kN);
(C) |D| transition table of a2 shots relative to the strict window (3 kN) and 15 kN.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\b46bdf8f\repro_a2")
CTRL = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\control_v7_review\probe_6bfb2560_check\out\ib_shots.csv")
ap = argparse.ArgumentParser()
ap.add_argument("--q02", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
L = []
p = L.append

cs = pd.read_csv(CTRL)
cs["absDb"] = cs.twist_before_N.abs() / 1e3
cs["absDa"] = cs.twist_after_N.abs() / 1e3
p("(A) shots per arm (6 plants): " + cs.groupby("arm").size().to_string().replace("\n", " | "))
vb5 = cs[cs.plant != "L"]
p("    VBM5 shots/grew per arm:\n" + vb5.groupby("arm").twist_grew.agg(["count", "sum", "mean"]).round(3).to_string())
p("    |D_before| kN per arm (VBM5):\n" + vb5.groupby("arm").absDb.describe().round(2).to_string())
p("    max |D_after| kN per arm (all): " + cs.groupby("arm").absDa.max().round(2).to_string().replace("\n", " | "))
p("    shots with |D_before|>15 kN per arm: " + cs.assign(h=cs.absDb > 15).groupby("arm").h.sum().to_string().replace("\n", " | "))
p("    shots with |D_after|>15 kN per arm: " + cs.assign(h=cs.absDa > 15).groupby("arm").h.sum().to_string().replace("\n", " | "))
# extra shots of a3 vs a2 (match by key, plant, leg, sign, start time)
k = ["key", "plant", "leg", "sign"]
a2 = cs[cs.arm == "a2"].copy()
a3 = cs[cs.arm == "a3"].copy()
a4 = cs[cs.arm == "a4"].copy()
a2["st"] = a2.start_t_s.round(1)
a3["st"] = a3.start_t_s.round(1)
a4["st"] = a4.start_t_s.round(1)
m = a3.merge(a2[k + ["st"]], on=k + ["st"], how="left", indicator=True)
extra = m[m._merge == "left_only"]
p(f"    a3 shots not in a2 (same key/plant/leg/sign/start 0.1 s): {len(extra)}")
if len(extra):
    p(extra[["key", "plant", "leg", "sign", "start_t_s", "absDb", "absDa", "twist_grew", "end"]].round(2).to_string())
m4 = a4.merge(a2[k + ["st"]], on=k + ["st"], how="outer", indicator=True)
p(f"    a4 vs a2 shot sets: both {int((m4._merge=='both').sum())}, a4 only {int((m4._merge=='left_only').sum())}, a2 only {int((m4._merge=='right_only').sum())}")
# sanity: a2 control table vs repro
rp = pd.read_csv(Path(a.q02) / "a2_shots.csv")
rp["st"] = rp.start_t_s.round(1)
p(f"    a2 shots probe 6bfb2560 {len(a2)} vs repro b46bdf8f {len(rp)}")

# (B) blind-stretch margin during |D|>15 LEVEL reads
mx = []
ge25 = 0
with open(RUN / "ed7_probe_a2.jsonl", encoding="utf-8") as fh:
    for raw in fh:
        rec = json.loads(raw)
        z = np.load(RUN / "ed7_probe_a2_t4h" / Path(rec["t4h_file"]).name, allow_pickle=False)
        ph = z["phase"]
        Dc = z["lsb_ib_twist_load_N"]
        st = z["lsb_ib_stretch_periods"]
        over = (ph == "level") & np.isfinite(Dc) & (np.abs(Dc) > 15e3)
        if over.any():
            v = int(st[over].max())
            mx.append(v)
            ge25 += int((st[over] >= 25).any())
mx = np.asarray(mx)
p(f"(B) lines with |D_ctl|>15 LEVEL reads: {mx.size}; max blind-stretch count during those reads: max {mx.max()}, median {np.median(mx):.0f}, p90 {np.percentile(mx,90):.0f}; lines reaching >=25: {ge25}")
p("    distribution of per-line max stretch: " + pd.Series(mx).value_counts().sort_index().to_string().replace("\n", " | "))

# (C) transition of a2 shots
rp["b"] = pd.cut(rp.D_before_rec_kN.abs(), [0, 3, 15, 1e9], right=False, labels=["<3", "3-15", ">=15"])
rp["a"] = pd.cut(rp.D_after_rec_kN.abs(), [0, 3, 15, 1e9], right=False, labels=["<3", "3-15", ">=15"])
p("(C) a2 repro shots |D| before -> after (kN):\n" + pd.crosstab(rp.b, rp.a).to_string())
vb = rp[rp.plant != "L"]
p("    VBM5 only:\n" + pd.crosstab(vb.b, vb.a).to_string())
txt = "\n".join(L)
Path(a.out).write_text(txt, encoding="utf-8")
print(txt)
