"""Rev. 48: head-sensor FAULT without a fault injection (ML-0 gate) in the ML pilot rerun.

For one episode, prints the 10 Hz controller samples around the FAULT: per leg the sensor
reading the monitor saw (record 'meas.head_pressure' / 'meas.rod_pressure'), its one-period
change, the true 1 ms pressure at the sample, the issued command, and the D1' head-step test
quantities: the four-leg net-force sum change |d sum| (from the readings, as the monitor does)
and the step force |dp_h| A_p of the stepping leg, ratio = |d sum| / (|dp_h| A_p) (explained
when < 0.5). Also the true four-leg sum of F_cyl and the body vertical acceleration, to tell a
load redistribution from a dynamic load change (impact / free fall), and contact flags.

Usage: python -I s8ml2_head_fault.py <case_dir> [t_before_s t_after_s]
Times are engine times (controller events use the same clock; judge rows are engine - 3 s).
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
A_P = np.array([1.3273e-2, 1.3273e-2, 9.503e-3, 9.503e-3])
A_ANN = np.array([3.770e-3, 3.770e-3, 3.142e-3, 3.142e-3])
LEGS = ["FL", "FR", "RL", "RR"]

case = Path(sys.argv[1])
tb = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
ta = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
ev = json.loads((case / "controller_events.json").read_text(encoding="utf-8"))
ev = [str(e) for e in ev]
t_fault = None
for e in ev:
    if "FAULT_HEAD_PRESSURE" in e or "WARN_ROD_PRESSURE_FALLBACK" in e or "INFO_ROD_PRESSURE_FAULT_REASON" in e:
        print(" ", e)
        if "FAULT_HEAD_PRESSURE" in e and t_fault is None:
            t_fault = float(e.split("t_s=")[1].split(",")[0])
res = json.loads((case / "result.json").read_text(encoding="utf-8"))
print("episode", res.get("episode"), "event_t", res.get("event_t_s"))
rec = np.load(case / "record" / "record.npz", allow_pickle=True)
r8 = np.load(case / "r8_series.npz", allow_pickle=True)
pads = np.load(case / "pads.npz", allow_pickle=True)
t = rec["t"]
assert np.allclose(t, r8["t"]), "record and r8 clocks differ"
tp = pads["t"]
idx = np.clip(np.searchsorted(tp, t - 1e-9), 0, len(tp) - 1)
hm = rec["meas.head_pressure"] / 1e5
rm = rec["meas.rod_pressure"] / 1e5
ht = pads["head_pressure"][idx] / 1e5
rt = pads["rod_pressure"][idx] / 1e5
net_m = (hm * A_P - rm * A_ANN) * 1e2  # kN
Fsum_true = pads["F_cyl"][idx].sum(axis=1) / 1e3
az = rec["body_vel"][:, 2]
contact = rec["pad_in_contact"]
air = pads["airborne"][idx]
u = r8["issued_u"] * 1e3
ref = t_fault if t_fault is not None else float(res.get("event_t_s"))
print(f"reference time {ref:.2f} s")
print("   t   phase   | head meas (dp) per leg                     | rod meas (dp) per leg                    | u issued mm/s            | dsum kN  ratio(step legs) | sumF_true vz   air")
for k in np.flatnonzero((t >= ref - tb) & (t <= ref + ta)):
    dh = hm[k] - hm[k - 1]
    dr = rm[k] - rm[k - 1]
    dsum = net_m[k].sum() - net_m[k - 1].sum()
    ratios = []
    for L in range(4):
        if abs(dh[L]) > 100:
            ratios.append(f"{LEGS[L]}:{abs(dsum)/(abs(dh[L])*A_P[L]*1e2):.2f}")
    hs = " ".join(f"{hm[k,L]:6.1f}({dh[L]:+6.1f})" for L in range(4))
    rs = " ".join(f"{rm[k,L]:6.1f}({dr[L]:+6.1f})" for L in range(4))
    us = " ".join(f"{u[k,L]:+5.1f}" for L in range(4))
    print(f" {t[k]:6.2f} {str(r8['phase'][k]):7s} | {hs} | {rs} | {us} | {dsum:+7.1f} {','.join(ratios):10s} | {Fsum_true[k]:7.1f} {az[k]:+.3f} {''.join('A' if a else '.' for a in air[k])}")
# true 1 ms pressures over the faulting period, for the fault leg
if t_fault is not None:
    for e in ev:
        if "FAULT_HEAD_PRESSURE" in e:
            leg = LEGS.index(e.split("FAULT_HEAD_PRESSURE:")[1][:2])
            m = (tp > t_fault - 0.25) & (tp <= t_fault + 0.01)
            print(f" 1 ms head {LEGS[leg]} {t_fault-0.25:.2f}..{t_fault:.2f}: min {pads['head_pressure'][m, leg].min()/1e5:.1f} max {pads['head_pressure'][m, leg].max()/1e5:.1f} bar;"
                  f" sum F_cyl min {pads['F_cyl'][m].sum(axis=1).min()/1e3:.1f} max {pads['F_cyl'][m].sum(axis=1).max()/1e3:.1f} kN")
