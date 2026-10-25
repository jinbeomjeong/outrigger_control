"""Bundle A vs 768: minimum true rod force between the U-S8-32 window end and re-READY (or run end).

Same quantity as the S8C record row "3 F_min window end .. re-READY" (F_min + 5 kN reference),
computed directly from pads.npz (1 ms F_cyl) for the ML episodes.
"""
import json
import os
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # rev53_56/rejudge_paths.py
from rejudge_paths import rejudge_file  # noqa: E402  (re-judge archive, env S8_REJUDGE_ML768_DIR)
# ---
ROOT = str(REPO / r"07_results\S8")
A = ROOT + r"\c36_20261025_155317\A_rt\episodes"
REF = ROOT + r"\ml_main_20261025_090131\episodes"
VA = ROOT + r"\c36_20261025_155317\A_rt\verify_S8ML.json"
RJ = str(rejudge_file("rev54", "verify_S8ML_ml768_rev54.json"))
F_MIN = 9.414589110
LEGS = ["FL", "FR", "RL", "RR"]


def post_min(path, wend):
    r = json.load(open(os.path.join(path, "result.json"), encoding="utf-8"))
    te = r["event_t_s"]
    s = np.load(os.path.join(path, "r8_series.npz"))
    ts, ph = s["t"] - te, s["phase"]
    rr = None
    seen_done = False
    for t, p in zip(ts, ph):
        if t < 0:
            continue
        if p == "done":
            seen_done = True
        if p == "ready" and seen_done:
            rr = t
            break
    p = np.load(os.path.join(path, "pads.npz"))
    t = p["t"] - te
    F = p["F_cyl"] / 1e3
    w = (t >= wend) & (t <= (rr if rr is not None else t[-1]))
    i, k = np.unravel_index(np.argmin(F[w]), F[w].shape)
    return float(F[w][i, k]), LEGS[k], float(t[w][i])


va = json.load(open(VA, encoding="utf-8"))
rj = json.load(open(RJ, encoding="utf-8"))
rows = []
for c, m in va["ml_metrics"].items():
    wa = (m.get("u_s8_32") or {}).get("window_end_rel_s")
    wb = (rj["ml_metrics"][c].get("u_s8_32") or {}).get("window_end_rel_s")
    if wa is None or wb is None:
        continue
    a = post_min(os.path.join(A, c), wa)
    b = post_min(os.path.join(REF, c), wb)
    rows.append((c, a, b, wa, wb))
print("episodes with a U-S8-32 window:", len(rows))
dl = [(c, a[0] - b[0]) for c, a, b, _, _ in rows]
worse = [(c, round(a[0], 2), a[1], round(a[2], 2), round(b[0], 2), b[1], round(b[2], 2)) for c, a, b, _, _ in rows if a[0] < b[0] - 1.0]
print("A < 768 - 1 kN:", len(worse), worse)
print("A below F_min:", [(c, round(a[0], 2), a[1], round(a[2], 2)) for c, a, b, _, _ in rows if a[0] < F_MIN])
print("768 below F_min:", [(c, round(b[0], 2), b[1], round(b[2], 2)) for c, a, b, _, _ in rows if b[0] < F_MIN])
print("A below F_min+5:", sum(a[0] < F_MIN + 5 for _, a, _, _, _ in rows), " 768 below F_min+5:", sum(b[0] < F_MIN + 5 for _, _, b, _, _ in rows))
print("A min overall:", min(rows, key=lambda r: r[1][0])[:2], " 768 min overall:", min(rows, key=lambda r: r[2][0])[0], min(r[2][0] for r in rows))
print("median delta A-768 [kN]: %+.2f" % np.median([d for _, d in dl]))
