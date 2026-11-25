"""Q7-D3 follow-up checks on the a2 repro:
(1) level_done instants that fall inside a |D|>15 episode window (boundary or real?),
(2) shots that 'grew' |D|: zero-crossing vs same-sign growth,
(3) controller D vs true D (n^T F_true) at shot triggers and inside episodes,
(4) episode onset relative to event, D at LEVEL entry.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\b46bdf8f\repro_a2")
N_TW = np.array([0.4761, -0.4761, -0.5228, 0.5228])

ap = argparse.ArgumentParser()
ap.add_argument("--q02", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
q = Path(a.q02)
ep = pd.read_csv(q / "a2_twist_over_limit_episodes.csv")
dn = pd.read_csv(q / "a2_level_done.csv")
sh = pd.read_csv(q / "a2_shots.csv")
L = []
p = L.append

# (1)
rows = []
for _, d in dn.iterrows():
    e = ep[(ep.key == d.key) & (ep.plant == d.plant)]
    for _, r in e.iterrows():
        if r.start_t_s <= d.t_s <= r.end_t_s:
            rows.append((d.key, d.plant, d.t_s, d.twist_load_kN, r.start_t_s, r.end_t_s, r.max_abs_twist_kN))
p(f"(1) level_done inside episode windows: {len(rows)}")
for x in rows[:10]:
    p("   " + str(tuple(round(v, 3) if isinstance(v, float) else v for v in x)))
same_t = sum(1 for x in rows if abs(x[2] - x[5]) < 1e-6 or abs(x[2] - x[4]) < 1e-6)
p(f"    of which done time equals episode start or end: {same_t}")

# (2)
g = sh[sh.twist_grew]
cross = np.sign(g.D_before_rec_kN) != np.sign(g.D_after_rec_kN)
p(f"(2) grew shots {len(g)}: zero-crossing {int(cross.sum())}, same-sign growth {int((~cross).sum())}")
p("    same-sign growth rows: \n" + g[~cross][["key", "plant", "leg", "sign", "D_before_rec_kN", "D_after_rec_kN", "dD_rec_kN", "stroke_change_mm"]].round(3).to_string())
p("    |D_after| of zero-crossing grew shots: " + g[cross].D_after_rec_kN.abs().describe().round(2).to_string().replace("\n", " | "))
p(f"    grew shots with |D_after| >= 3 kN (outside strict window): {int((g.D_after_rec_kN.abs() >= 3).sum())}; of all shots |D_before|>=3: {int((sh.D_before_rec_kN.abs() >= 3).sum())}, |D_after|>=3: {int((sh.D_after_rec_kN.abs() >= 3).sum())}")
# (3) controller D vs true D at shot trigger and episode starts
diffs = []
ep_true_max = []
seen = {}
with open(RUN / "ed7_probe_a2.jsonl", encoding="utf-8") as fh:
    for raw in fh:
        rec = json.loads(raw)
        job = rec["job"]
        plant = job["setting"].split("-")[1]
        key = Path(rec["t4h_file"]).stem.rsplit("_P7-", 1)[0]
        z = np.load(RUN / "ed7_probe_a2_t4h" / Path(rec["t4h_file"]).name, allow_pickle=False)
        t = z["t_s"]
        Dt = z["true_force_N"] @ N_TW
        Dc = z["lsb_ib_twist_load_N"]
        ph = z["phase"]
        lvl = (ph == "level") & np.isfinite(Dc)
        if lvl.any():
            diffs.append(np.abs(Dc[lvl] - Dt[lvl]))
        # LEVEL entry D after event
        te = rec.get("t_event_s")
        if te is not None:
            idx = np.flatnonzero((ph == "level") & (t >= te))
            if idx.size:
                i0 = idx[0]
                seen.setdefault("entry_absD_true_kN", []).append(abs(Dt[i0]) / 1e3)
                seen.setdefault("entry_dt_s", []).append(t[i0] - te)
                # max |D_true| in first 10 s after event during LEVEL
                w = (t >= te) & (t <= te + 10) & (ph == "level")
                seen.setdefault("max_absD_true_10s_kN", []).append(np.max(np.abs(Dt[w])) / 1e3)
                # |D| ctl at last LEVEL read before DONE/READY
                seen.setdefault("phase_before_event", []).append(str(ph[max(0, np.searchsorted(t, te) - 1)]))
                # true min force during the episode window
        # min true force while |Dc|>15 during LEVEL
        over = lvl & (np.abs(Dc) > 15e3)
        if over.any():
            ep_true_max.append(z["true_force_min_N"][over].min() / 1e3 if "true_force_min_N" in z.files else np.nan)
d = np.concatenate(diffs)
p(f"(3) |D_ctl - D_true| over LEVEL reads: median {np.median(d)/1e3:.2f} kN, p95 {np.percentile(d,95)/1e3:.2f}, max {d.max()/1e3:.2f}")
for k, v in seen.items():
    if k == "phase_before_event":
        p(f"    {k}: " + pd.Series(v).value_counts().to_string().replace("\n", " | "))
    else:
        v = np.asarray(v)
        p(f"    {k}: n {v.size}, median {np.median(v):.2f}, p90 {np.percentile(v,90):.2f}, max {v.max():.2f}")
e = np.asarray(ep_true_max)
p(f"    min true leg force during |D_ctl|>15 LEVEL reads (per line): min {np.nanmin(e):.2f} kN, median {np.nanmedian(e):.2f}")
# (4) after the last |D|>15 episode of each line: time to the next level_done, shots in between
gap_rows = []
for (k, pl), e in ep.groupby(["key", "plant"]):
    last_end = e.end_t_s.max()
    dd = dn[(dn.key == k) & (dn.plant == pl) & (dn.t_s >= last_end)]
    nxt = dd.t_s.min() if len(dd) else np.nan
    path = dd.sort_values("t_s").path.iloc[0] if len(dd) else "none"
    ss = sh[(sh.key == k) & (sh.plant == pl) & (sh.start_t_s >= last_end) & (sh.start_t_s <= (nxt if np.isfinite(nxt) else 1e9))]
    gap_rows.append((k, pl, last_end, nxt - last_end, path, len(ss)))
g4 = pd.DataFrame(gap_rows, columns=["key", "plant", "last_ep_end", "to_done_s", "path", "shots_between"])
p(f"(4) lines with episodes {len(g4)}: next DONE path counts " + g4.path.value_counts().to_string().replace("\n", " | "))
p("    time from last episode end to DONE [s]: " + g4.to_done_s.describe().round(2).to_string().replace("\n", " | "))
p(f"    lines with A_ib shots between last episode and DONE: {int((g4.shots_between > 0).sum())} (shots {int(g4.shots_between.sum())})")
g4.to_csv(Path(a.out).with_suffix(".gap.csv"), index=False)
txt = "\n".join(L)
Path(a.out).write_text(txt, encoding="utf-8")
print(txt)
