"""Rev. 51: find the cause of an un-injected FAULT in a main-ML episode (no head fault, no reason).

Usage: python -I s8main_fault.py <case_dir> [t_before_s t_after_s]
Prints: npz keys, phase transitions (r8_series 'phase', engine time), result.json keys mentioning
fault/limit/stroke, and around the first FAULT sample the 10 Hz readings: stroke (meas), motor
position, head/rod readings, issued command, attitude, plus 1 ms true stroke extremes.
Times: engine time (judge time = engine - 3 s).
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
LEGS = ["FL", "FR", "RL", "RR"]
case = Path(sys.argv[1])
tb = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
ta = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3

rec = np.load(case / "record" / "record.npz", allow_pickle=True)
r8 = np.load(case / "r8_series.npz", allow_pickle=True)
pads = np.load(case / "pads.npz", allow_pickle=True)
s8 = np.load(case / "s8_series.npz", allow_pickle=True)
print("record keys:", sorted(rec.files))
print("r8 keys:", sorted(r8.files))
print("pads keys:", sorted(pads.files))
print("s8 keys:", sorted(s8.files))
res = json.loads((case / "result.json").read_text(encoding="utf-8"))


def walk(o, path=""):
    if isinstance(o, dict):
        for k, x in o.items():
            walk(x, f"{path}.{k}")
    elif isinstance(o, list) and len(o) < 50:
        for i, x in enumerate(o):
            walk(x, f"{path}[{i}]")
    else:
        low = path.lower()
        if any(w in low for w in ("fault", "limit", "stroke", "end", "phase", "reason", "safe", "stop")):
            s = json.dumps(o, ensure_ascii=False) if not isinstance(o, np.ndarray) else str(o)
            print(f"  result{path} = {s[:300]}")


if "--walk" in sys.argv:
    walk(res)
print("result top keys:", list(res.keys()))
for k in ("fault", "faults", "fault_t_s", "fault_reason", "controller_fault", "phase_final", "status"):
    if k in res:
        print(f"  result.{k} = {json.dumps(res[k], ensure_ascii=False)[:600]}")
cm = res.get("controller_meta", {})
print("controller_meta keys:", list(cm.keys()))
for k in cm:
    if "fault" in k.lower() or "limit" in k.lower():
        print(f"  controller_meta.{k} = {json.dumps(cm[k], ensure_ascii=False)[:800]}")
t = r8["t"]
ph = np.array([str(p) for p in r8["phase"]])
chg = np.flatnonzero(np.r_[True, ph[1:] != ph[:-1]])
print("phase transitions (engine s):", [(round(float(t[i]), 2), ph[i]) for i in chg])
kf = np.flatnonzero(np.char.lower(ph.astype(str)) == "fault")
if len(kf) == 0:
    print("no FAULT phase")
    sys.exit()
tf = float(t[kf[0]])
print(f"first FAULT sample {tf:.2f} s (judge {tf-3:.2f})")
# candidate per-sample arrays in the record
for key in sorted(rec.files):
    a = rec[key]
    if a.ndim >= 1 and len(a) == len(t) and a.dtype.kind in "fiub":
        k0 = kf[0]
        seg = a[max(k0 - 3, 0):k0 + 2]
        print(f"  rec {key:35s} {np.array2string(np.asarray(seg, dtype=float), precision=4, max_line_width=250)}")
for key in sorted(r8.files):
    a = r8[key]
    if a.ndim >= 1 and len(a) == len(t) and a.dtype.kind in "fiub":
        k0 = kf[0]
        seg = a[max(k0 - 3, 0):k0 + 2]
        print(f"  r8  {key:35s} {np.array2string(np.asarray(seg, dtype=float), precision=4, max_line_width=250)}")
tp = pads["t"]
m = (tp > tf - tb) & (tp <= tf + ta)
for key in ("stroke", "s_motor", "stroke_true", "F_cyl", "head_pressure", "rod_pressure"):
    if key in pads.files:
        a = pads[key][m]
        print(f"  pads {key}: min {np.array2string(a.min(axis=0), precision=4)} max {np.array2string(a.max(axis=0), precision=4)}")
