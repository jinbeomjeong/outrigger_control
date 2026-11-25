"""Q7-H6 (3): (i-b) probe end offset in the probe 6bfb2560 T4h (position target on: arms a1-a6).

Per leg in phase 'probe': an extend block (command > 0) directly followed by a retract block
(command < 0). s0 = oil-coordinate stroke (`motor_stroke_m`) on the read before the extend block,
s_end = stroke on the last read before the next nonzero command (or the end of the probe phase).
e = s_end - s0 (negative: the leg ended below its probe start = over-travel). Record only.

Usage: python -I -B s15_probe_end.py <t4h dir> <out csv>
"""
import csv
import sys
from pathlib import Path

import numpy as np

T4H, OUT = Path(sys.argv[1]), Path(sys.argv[2])
LEGS = ("FL", "FR", "RL", "RR")
rows = []
for path in sorted(T4H.glob("*_P7-M*-a[1-6].npz")):
    setting = path.stem.split("_P7-")[1]
    plant = setting.rsplit("-", 1)[0]
    with np.load(path, allow_pickle=False) as d:
        t, phase = d["t_s"], d["phase"]
        cmd, s = d["command_m_s"], d["motor_stroke_m"]
    probe = phase == "probe"
    for leg in range(4):
        sign = np.where(probe, np.sign(np.where(np.abs(cmd[:, leg]) > 1e-9, cmd[:, leg], 0.0)), 9)
        k, n = 0, len(t)
        while k < n:
            if sign[k] != 1:
                k += 1
                continue
            start = k
            while k < n and sign[k] == 1:
                k += 1
            while k < n and sign[k] == 0:      # hold between extend and retract
                k += 1
            if k >= n or sign[k] != -1 or start == 0:
                continue
            ret_start = k
            while k < n and sign[k] == -1:
                k += 1
            ret_end = k
            while k < n and sign[k] == 0:
                k += 1
            last = k - 1
            if last < ret_end:
                continue
            s0 = float(s[start - 1, leg])
            rows.append({"file": path.name, "plant": plant, "leg": LEGS[leg],
                         "t_start": round(float(t[start]), 2),
                         "ext_mm": round((float(np.max(s[start:ret_start + 1, leg])) - s0) * 1e3, 3),
                         "ret_cmd_mm": round(float(-np.sum(cmd[ret_start:ret_end, leg]) * 0.1) * 1e3, 3),
                         "settle_reads": int(last - ret_end + 1),
                         "e_mm": round((float(s[last, leg]) - s0) * 1e3, 3)})
with OUT.open("w", newline="\n", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
e = np.array([r["e_mm"] for r in rows])
settled = np.array([r["settle_reads"] >= 5 for r in rows])
print(f"rounds {len(rows)}, settled (>= 5 zero reads) {settled.sum()}")
for name, mask in (("all", np.ones(len(rows), bool)), ("settled", settled)):
    v = e[mask]
    print(f"  {name}: e mm min {v.min():.3f} p05 {np.percentile(v, 5):.3f} median {np.median(v):.3f} "
          f"p95 {np.percentile(v, 95):.3f} max {v.max():.3f}; |e|>0.5: {np.sum(np.abs(v) > 0.5)}, "
          f"e<-0.8: {np.sum(v < -0.8)}")
for plant in sorted({r["plant"] for r in rows}):
    v = np.array([r["e_mm"] for r, ok in zip(rows, settled) if ok and r["plant"] == plant])
    if len(v):
        print(f"  {plant}: n {len(v)} median {np.median(v):.3f} p05 {np.percentile(v, 5):.3f} "
              f"p95 {np.percentile(v, 95):.3f} min {v.min():.3f}")
