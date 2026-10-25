"""Rev. 51: re-approach ping-pong scan over all main-ML episodes + post-FAULT state check.

Usage: python -I s8main_reapp_scan.py <batch_dir> <out_json>
Per episode (controller_events, engine time, relative to result.event_t_s):
  - number of leg_reapproach_start events after the event, number of leg changes between
    consecutive starts, last start time, starts later than event + 1.5 s
For FAULT episodes (r8 phase 'fault'): 1 ms min F_cyl per leg and airborne time per leg from
the FAULT to the run end, max |roll|, |pitch| change over that span.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
LEGS = ["FL", "FR", "RL", "RR"]
batch = Path(sys.argv[1])
out = Path(sys.argv[2])
rows = []
for case in sorted((batch / "episodes").iterdir()):
    if not case.is_dir() or case.name.startswith("_"):
        continue
    res = json.loads((case / "result.json").read_text(encoding="utf-8"))
    cj = json.loads((case / "case.json").read_text(encoding="utf-8"))
    ep = cj["settings"]["episode"]
    b = cj["settings"]["base"]
    t_ev = float(res.get("event_t_s") or res.get("branch_t_s"))
    ev = json.loads((case / "controller_events.json").read_text(encoding="utf-8"))
    starts = []
    for e in ev:
        s = str(e)
        if "leg_reapproach_start:" in s:
            ts = float(s.split("t_s=")[1].split(",")[0])
            if ts >= t_ev - 1e-6:
                starts.append((ts - t_ev, s.split("leg_reapproach_start:")[1][:2]))
    changes = sum(1 for a, c in zip(starts, starts[1:]) if a[1] != c[1])
    row = {"case": case.name, "kind": ep.get("kind"), "leg": ep.get("leg"),
           "depth_mm": 1e3 * float(ep.get("depth_m") or 0), "ramp_s": ep.get("ramp_s"),
           "level": b["level"], "fs_kN": b["fs_kN"], "beta_GPa": b["beta_GPa"],
           "n_starts": len(starts), "leg_changes": changes,
           "last_start_rel_s": starts[-1][0] if starts else None,
           "late_starts": [round(x[0], 2) for x in starts if x[0] > 1.5]}
    r8 = np.load(case / "r8_series.npz", allow_pickle=True)
    ph = np.char.lower(np.array([str(p) for p in r8["phase"]]))
    kf = np.flatnonzero(ph == "fault")
    if len(kf):
        tf = float(r8["t"][kf[0]])
        pads = np.load(case / "pads.npz", allow_pickle=True)
        m = pads["t"] >= tf
        Fm = pads["F_cyl"][m].min(axis=0) / 1e3
        air = pads["airborne"][m].sum(axis=0) * float(np.median(np.diff(pads["t"])))
        rec = np.load(case / "record" / "record.npz", allow_pickle=True)
        q = rec["body_quat_wxyz"]
        w, x, y, z = q.T
        roll = np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
        pitch = np.degrees(np.arcsin(np.clip(2 * (w * y - z * x), -1, 1)))
        mr = rec["t"] >= tf
        row["post_fault"] = {"t_fault": tf, "t_end": float(pads["t"][-1]), "Fmin_kN": Fm.round(2).tolist(),
                             "air_s": air.round(3).tolist(),
                             "roll_deg": [float(roll[mr].min()), float(roll[mr].max())],
                             "pitch_deg": [float(pitch[mr].min()), float(pitch[mr].max())]}
    rows.append(row)
json.dump({"rows": rows}, open(out, "w", encoding="utf-8"), indent=1)
n = np.array([r["n_starts"] for r in rows])
ch = np.array([r["leg_changes"] for r in rows])
late = np.array([len(r["late_starts"]) for r in rows])
print(f"episodes {len(rows)}; with any re-approach {int((n>0).sum())}; starts p50/p95/max {np.median(n[n>0]):.0f}/{np.percentile(n[n>0],95):.0f}/{n.max()}")
print(f"episodes with >= 3 starts later than event + 1.5 s: {int((late>=3).sum())}; >= 2: {int((late>=2).sum())}")
for r in sorted(rows, key=lambda r: -len(r["late_starts"]))[:15]:
    print(f"  {r['case']:9s} {r['kind']} {r['leg']} {r['depth_mm']:.1f} mm ramp {r['ramp_s']} | {r['level']} Fs {r['fs_kN']:.2f} beta {r['beta_GPa']:.2f} | starts {r['n_starts']} changes {r['leg_changes']} late {r['late_starts']}")
print("\npost-FAULT state:")
for r in rows:
    if "post_fault" in r:
        p = r["post_fault"]
        print(f"  {r['case']}: FAULT {p['t_fault']:.2f}..{p['t_end']:.2f} s, min F {p['Fmin_kN']} kN, air {p['air_s']} s, roll {np.round(p['roll_deg'],3)}, pitch {np.round(p['pitch_deg'],3)} deg")
