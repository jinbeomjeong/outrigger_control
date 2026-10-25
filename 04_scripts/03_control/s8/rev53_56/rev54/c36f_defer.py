"""Deferred re-approach starts (RT) vs the post-window force dip of the deferred leg."""
import json
import os
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
va = json.load(open(VA, encoding="utf-8"))
for c, m in va["ml_metrics"].items():
    rt = m.get("rt") or {}
    if not rt.get("deferred"):
        continue
    r = json.load(open(os.path.join(A, c, "result.json"), encoding="utf-8"))
    te = r["event_t_s"]
    p = np.load(os.path.join(A, c, "pads.npz"))
    t = p["t"] - te
    F = p["F_cyl"] / 1e3
    rr = json.load(open(os.path.join(REF, c, "result.json"), encoding="utf-8"))
    q = np.load(os.path.join(REF, c, "pads.npz"))
    tq = q["t"] - rr["event_t_s"]
    Fq = q["F_cyl"] / 1e3
    print("==", c, "runs", [(x["start_s"], x["leg"], x["is_retrigger"]) for x in rt["runs"]])
    for td, leg in rt["deferred_rel_s"]:
        k = LEGS.index(leg)
        nxt = [x["start_s"] for x in rt["runs"] if x["leg"] == leg and x["start_s"] >= td]
        t_end = (nxt[0] if nxt else td + 1.0) + 0.3
        w = (t >= td) & (t <= t_end)
        wq = (tq >= td) & (tq <= t_end)
        print(f"   deferred {leg} at {td:.1f} s, next start {nxt[0] if nxt else None}; min F {leg} in [{td:.1f}, {t_end:.1f}] "
              f"A {F[w, k].min():.2f} kN vs 768 {Fq[wq, k].min():.2f} kN; leg F at deferral A {F[np.argmin(abs(t-td)), k]:.1f}")
