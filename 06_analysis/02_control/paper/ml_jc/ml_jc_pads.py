"""1 ms pad record around every J_C-missed episode; sample-count tables per set; run outcome of missed runs."""
import json
import os
from collections import Counter

import numpy as np

S = r"C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\ctrl_v4den"
ROOT = r"C:\workspace\outrigger_control"
LEGS = ("FL", "FR", "RL", "RR")
FMIN = 9.41458911
h = json.load(open(S + r"\ml_jc_head.json", encoding="utf-8"))
GATE = ("E_", "N_")


def src(m):
    p = str(m["source"])
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


first = True
out = []
for name in ("test", "OOD-1", "OOD-2", "MLJ", "validation", "train"):
    print("\n=====", name)
    scored = [(it["meta"], r) for it in h[name] for r in it["rows"] if r["scope"] == "scored"]
    tab = Counter()
    for m, r in scored:
        tab[("1 sample" if r["samples"] == 1 else ">=2", "lift" if r["is_lift"] else "under", "miss" if r["JC_first_decision_s"] is None else "caught")] += 1
    print(sorted(tab.items()))
    miss = [(m, r) for m, r in scored if r["JC_first_decision_s"] is None]
    print("miss with true at sample < F_min:", sum(r["true_at_samples_min_kN"] < FMIN for _, r in miss), "of", len(miss))
    print("miss phases", Counter(r["phase_on"] for _, r in miss), "probe rounds==0:", sum(r["probe_rounds_before"] == 0 for _, r in miss), "dt_event<=0.3:", sum((r["t_since_event_s"] or 99) <= 0.3001 for _, r in miss))
    print("all-episode phases", Counter(r["phase_on"] for _, r in scored))
    for m, r in sorted(miss, key=lambda x: x[1]["run"]):
        folder = src(m)
        res = json.load(open(os.path.join(folder, "result.json"), encoding="utf-8"))
        if first:
            print("result keys", list(res.keys()))
            print("event", json.dumps(res.get("event"), default=str)[:400], "spec", json.dumps(res.get("spec"), default=str)[:400], "stage2", res.get("stage2"))
            first = False
        pads = np.load(os.path.join(folder, "pads.npz"), allow_pickle=False)
        if name == "test" and r["run"] == "ML38_ep1":
            print("pads keys", pads.files)
        i = LEGS.index(r["leg"])
        t = pads["t"]
        win = (t >= r["t_on_s"] - 1.0) & (t <= r["t_on_s"] + 1.0)
        f = pads["F_cyl"][win, i] / 1e3
        tw = t[win]
        dt = np.median(np.diff(tw))
        n = pads["N"][win, i] if "N" in pads.files else None
        air = pads["airborne"][win, i].astype(bool) if "airborne" in pads.files else None
        under = f < FMIN
        spec = res.get("spec") or (res.get("event") if isinstance(res.get("event"), dict) else {}) or {}
        end = res.get("s8_end") or {}
        row = {"set": name, "run": r["run"], "leg": r["leg"], "ev_leg": spec.get("leg"), "ev_kind": spec.get("kind"), "stage2": res.get("stage2"), "t_on": round(r["t_on_s"], 1),
               "min_F_1ms": round(float(f.min()), 2), "t_min_rel_on": round(float(tw[np.argmin(f)] - r["t_on_s"]), 3), "under_s": round(float(under.sum() * dt), 3),
               "air_s": None if air is None else round(float(air.sum() * dt), 3), "N_le0_s": None if n is None else round(float((n <= 0).sum() * dt), 3),
               "max_F_1ms": round(float(f.max()), 1), "final_phase": end.get("final_phase"), "end_reason": end.get("reason"), "failed": res.get("failed")}
        if "F_cyl_min_interval" in pads.files:
            row["min_interval_end_run"] = None
        out.append(row)
        if name in ("test", "OOD-1", "OOD-2", "MLJ"):
            print(row)
print("\nMisses total", len(out), "under_s stats", np.percentile([o["under_s"] for o in out], [0, 50, 100]), "air_s", np.percentile([o["air_s"] or 0 for o in out], [0, 50, 100]))
print("event-leg misses", sum(o["ev_leg"] == o["leg"] for o in out), "final", Counter(str(o["final_phase"]) for o in out))
gate = [(it["meta"], r) for it in h["EN"] for r in it["rows"] if r["run"].startswith(GATE)]
print("\nE/N rows", len(gate), Counter((r["scope"], "1" if r["samples"] == 1 else ">=2", r["is_lift"], r["JC_first_decision_s"] is None) for _, r in gate))
print("E/N sample counts", sorted(Counter(r["samples"] for _, r in gate).items()))
for name in ("test", "OOD-1", "OOD-2"):
    sc = [r for it in h[name] for r in it["rows"] if r["scope"] == "scored"]
    print(name, "sample counts", sorted(Counter(r["samples"] for r in sc).items()))
    print("  phase of runs events: level", sum(r["phase_on"] == "level" for r in sc), "ready", sum(r["phase_on"] == "ready" for r in sc), "dt_event quantiles", np.percentile([r["t_since_event_s"] if r["t_since_event_s"] is not None else 99 for r in sc], [10, 50, 90]))
json.dump(out, open(S + r"\ml_jc_missed_pads.json", "w", encoding="utf-8"), indent=0, default=str)
