"""J_C misses in the stored Chrono event batches (C-S8-71/72/74): episode values from the replay rows and the 1 ms pad record."""
import json
import os
from collections import Counter

import numpy as np

R = r"C:\workspace\outrigger_control"
A = os.path.join(R, r"06_analysis\02_control\s8")
FILES = [r"rev65\verify_S8C_c68b_c71.json", r"rev68\verify_S8C_c72_u75.json", r"rev68\verify_S8C_c74_u75.json"]
LEGS = ("FL", "FR", "RL", "RR")
FMIN = 9.41458911
for f in FILES:
    v = json.load(open(os.path.join(A, f), encoding="utf-8"))
    batch = v["meta"]["batch"]
    root = batch if os.path.isabs(batch) else os.path.join(R, batch)
    print("=====", f, batch, "judge rev", str(v["meta"].get("judge_revision"))[:80])
    samples = Counter()
    for case, met in v["s8_metrics"].items():
        it = met.get("item9")
        if not it or "replay" not in it or not isinstance(it["replay"], dict) or "J_C" not in it["replay"]:
            continue
        for e, ep in zip(it["replay"]["J_C"]["episodes"], it["replay"]["J_P"]["episodes"], strict=True):
            n = int(round((e["t_off_s"] - e["t_on_s"]) / 0.1)) + 1
            jm = e["first_decision_s"] is None
            samples[("1" if n == 1 else ">=2", "miss" if jm else "caught", "transient" if e["crawler_transient"] else "")] += 1
            if not jm:
                continue
            folder = os.path.join(root, case)
            res = json.load(open(os.path.join(folder, "result.json"), encoding="utf-8"))
            pads = np.load(os.path.join(folder, "pads.npz"), allow_pickle=False)
            rec = np.load(os.path.join(folder, "record", "record.npz"), allow_pickle=False)
            off = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
            t = pads["t"] - off
            i = LEGS.index(e["leg"])
            lo, hi = e["t_on_s"] - 0.1, e["t_off_s"]
            w = (t > lo) & (t <= hi + 1e-9)
            dt = np.median(np.diff(t))
            fw = pads["F_cyl"][w, i] / 1e3
            t_end = t[w][-1]
            print(f" {case} {e['leg']} t_on={e['t_on_s']:.1f} ev={res.get('event_t_s')} samples={n} lift={e['is_lift']} transient={e['crawler_transient']} sampling_only={e['sampling_only']} act={e['action_delay_s']} JPmiss={ep['first_decision_s'] is None} "
                  f"off={off:.2f} min={fw.min():.2f} samples_F={[round(float(np.interp(e["t_on_s"] + k * 0.1, t, pads["F_cyl"][:, i])) / 1e3, 1) for k in range(n)]} under_ms={(fw < FMIN).sum() * dt * 1e3:.0f} air_ms={pads['airborne'][w, i].astype(bool).sum() * dt * 1e3:.0f}")
    print(" tally", sorted(samples.items()))
