"""Phase run-length sequence after the event, bundle A vs 768, plus final-phase summary."""
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
ids = json.load(open(ROOT + r"\c36_20261025_155317\c36_meta.json", encoding="utf-8"))["ids"]["A"]


def seq(path):
    r = json.load(open(os.path.join(path, "result.json"), encoding="utf-8"))
    te = r["event_t_s"]
    s = np.load(os.path.join(path, "r8_series.npz"))
    t, ph = s["t"], s["phase"]
    out = []
    for ti, p in zip(t, ph):
        if ti < te - 0.05:
            continue
        if not out or out[-1][0] != p:
            out.append([p, round(ti - te, 1)])
    return out


def ready_entry(sq):
    """Time of the first 'ready' after a 'done' (re-READY after the re-level)."""
    seen_done = False
    for p, t in sq:
        if p == "done":
            seen_done = True
        if p == "ready" and seen_done:
            return t
    return None


ra, rr = [], []
for e in ids:
    a, b = seq(os.path.join(A, e)), seq(os.path.join(REF, e))
    ta, tb = ready_entry(a), ready_entry(b)
    ra.append(ta)
    rr.append(tb)
    print(e, "A:", a, "\n      R:", b)
pairs = [(e, x, y) for e, x, y in zip(ids, ra, rr)]
both = [(e, x, y) for e, x, y in pairs if x is not None and y is not None]
d = np.array([x - y for _, x, y in both])
print("re-READY (first ready after done) both:", len(both), "A none:", [e for e, x, _ in pairs if x is None],
      "R none:", [e for e, _, y in pairs if y is None])
print("delta A-R: max %+.1f median %+.1f min %+.1f; later count %d" % (d.max(), np.median(d), d.min(), int((d > 0.05).sum())))
print("worst later:", sorted(both, key=lambda z: -(z[1] - z[2]))[:6])
print("A re-READY max:", max(x for _, x, _ in both), "R max:", max(y for _, _, y in both))
