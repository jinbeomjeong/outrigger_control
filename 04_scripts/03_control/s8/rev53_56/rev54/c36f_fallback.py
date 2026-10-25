"""Locate the 17 bundle-A rod-pressure fallbacks relative to the event and the re-approach runs.

For each A run with a fallback: event time (result.json), fallback event from
controller_events.json, nearby re-approach start/contact/deferred events, pad state of that
leg (airborne?), plant rod/head pressure 1 ms around the sample, and the same leg's rod
pressure in the 768 run (F1 defect) for comparison.
"""
import json
import os
import re
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
# ---
ROOT = str(REPO / r"07_results\S8")
A = ROOT + r"\c36_20261025_155317\A_rt\episodes"
REF = ROOT + r"\ml_main_20261025_090131\episodes"
VA = ROOT + r"\c36_20261025_155317\A_rt\verify_S8ML.json"
LEGS = ["FL", "FR", "RL", "RR"]
pat = re.compile(r"t_s=([0-9.]+), name='([^']+)'")


def events(path):
    ev = json.load(open(os.path.join(path, "controller_events.json"), encoding="utf-8"))
    out = []
    for e in ev:
        m = pat.search(e)
        if m:
            out.append((float(m.group(1)), m.group(2)))
    return out


va = json.load(open(VA, encoding="utf-8"))
cases = [c for c, m in va["ml_metrics"].items() if (m.get("rod_fallback") or {}).get("events")]
print("cases", len(cases))
stats = []
for c in cases:
    r = json.load(open(os.path.join(A, c, "result.json"), encoding="utf-8"))
    te = r["event_t_s"]
    ev = events(os.path.join(A, c))
    fb = [(t, n) for t, n in ev if "FALLBACK" in n.upper() or "ROD_" in n.upper()]
    rf = va["ml_metrics"][c]["rod_fallback"]
    rt = va["ml_metrics"][c].get("rt") or {}
    p = np.load(os.path.join(A, c, "pads.npz"))
    t = p["t"]
    print("==", c, "event", round(te, 2), "fallback meta", json.dumps(rf, default=str)[:300])
    for t0, n in fb:
        print("   fb-event", round(t0 - te, 2), n)
    near = [(round(t0 - te, 2), n) for t0, n in ev if "reapproach" in n and -0.1 <= t0 - te <= 4]
    print("   reapproach", near)
    print("   rt runs", [(x["start_s"], x["leg"], x["is_retrigger"], x["outcome"], x.get("end_s")) for x in rt.get("runs", [])])
    for t0, n in fb:
        leg = None
        for i, L in enumerate(LEGS):
            if n.endswith(":" + L) or (":" + L + ":") in n:
                leg = i
        if leg is None:
            continue
        w = (t >= t0 - 0.35) & (t <= t0 + 0.15)
        sel = np.where(w)[0][::25]
        print("   leg", LEGS[leg], "t-te, N[kN], airborne, rod[bar], head[bar], s_motor[mm], F_cyl[kN]")
        for i in sel:
            print(f"     {t[i]-te:+.3f} {p['N_raw'][i, leg]/1e3:7.2f} {bool(p['airborne'][i, leg])!s:5} "
                  f"{p['rod_pressure'][i, leg]/1e5:7.2f} {p['head_pressure'][i, leg]/1e5:7.2f} "
                  f"{p['s_motor'][i, leg]*1e3:8.3f} {p['F_cyl'][i, leg]/1e3:7.2f}")
        # 768 same leg
        q = np.load(os.path.join(REF, c, "pads.npz"))
        r2 = json.load(open(os.path.join(REF, c, "result.json"), encoding="utf-8"))
        tq = q["t"] - r2["event_t_s"] + te
        w2 = (tq >= t0 - 0.35) & (tq <= t0 + 0.15)
        sel2 = np.where(w2)[0][::25]
        print("   768 same leg rod[bar] / airborne:",
              [(round(tq[i] - te, 3), round(q['rod_pressure'][i, leg] / 1e5, 1), bool(q['airborne'][i, leg])) for i in sel2])
        ev2 = events(os.path.join(REF, c))
        print("   768 reapproach", [(round(t2 - r2["event_t_s"], 2), n2) for t2, n2 in ev2 if "reapproach" in n2 and -0.1 <= t2 - r2["event_t_s"] <= 4])
