"""Item 5a recomputed: 50-sample window (as judged, = 5 s at 10 Hz) vs 10-sample (1 s) window,
and where the maximum sits (phase, time) to separate the levelling ramp from rocking."""
import json
import sys
from pathlib import Path

import numpy as np

batch = Path(sys.argv[1])


def rp_from_quat(q):
    w, x, y, z = q.T
    roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
    return np.degrees(np.column_stack([roll, pitch]))


def amp(a, win):
    if len(a) <= 2 * win:
        return None, None
    k = np.ones(win) / win
    mov = np.column_stack([np.convolve(a[:, i], k, mode="same") for i in range(2)])
    dev = np.abs(a - mov)[win:len(a) - win]
    i = int(np.argmax(dev.max(axis=1)))
    return float(dev.max()), i + win


ver = json.loads((batch / "verify_S6C.json").read_text(encoding="utf-8"))
judged = {r["case"]: r["value"] for r in ver["rows"] if r["item"] == "5a rocking amplitude"}
print(f"{'case':40s} judged  w50    w10    w10_after_READY  max_at(t,phase) w50")
for case, v in sorted(judged.items()):
    rec = np.load(batch / case / "record" / "record.npz")
    r8 = np.load(batch / case / "r8_series.npz")
    t = rec["t"]
    a = rp_from_quat(rec["body_quat_wxyz"])
    fc = rec["F_crawler"][:, 2]
    lift = np.where(fc < 1.0)[0]
    i0 = lift[0] if lift.size else 0
    a50, i50 = amp(a[i0:], 50)
    a10, _ = amp(a[i0:], 10)
    ready = np.where(r8["phase"] == "ready")[0]
    a10r = amp(a[ready[0]:], 10)[0] if ready.size else None
    ph = r8["phase"][i0 + i50] if i50 is not None else "-"
    print(f"{case:40s} {v:.4f}  {a50:.4f}  {a10:.4f}  {a10r if a10r is None else round(a10r,4)}   {t[i0+i50]:.1f} {ph}")
