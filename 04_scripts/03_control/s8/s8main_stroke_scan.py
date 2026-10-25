"""Rev. 51: stroke-end scan over all main-ML episodes (stroke-end FAULT, near misses).

Usage: python -I s8main_stroke_scan.py <batch_dir> <out_json>
Per episode (10 Hz controller record, engine time):
  - episode kind / leg / depth / ramp, base floor, level, F_s
  - motor stroke reading (meas.stroke) per leg at the branch (first sample) and its max after
    the branch, the reserve to the soft end s_soft - 1 mm (= FAULT test level), phases seen,
    first FAULT time, attitude (roll, pitch from body quaternion) at the FAULT or at the end,
    last 1 s heave / attitude command components of the end leg
Soft end: stroke_soft_max_m from controller_meta.geometry if present, else 0.6948 m.
Read only, no random numbers.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
LEGS = ["FL", "FR", "RL", "RR"]
batch = Path(sys.argv[1])
out = Path(sys.argv[2])


def rp(q):
    w, x, y, z = q.T
    roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
    return np.degrees(roll), np.degrees(pitch)


rows = []
for case in sorted((batch / "episodes").iterdir()):
    if not case.is_dir() or case.name.startswith("_"):
        continue
    cj = json.loads((case / "case.json").read_text(encoding="utf-8"))
    st = cj["settings"]
    base, ep = st["base"], st["episode"]
    res = json.loads((case / "result.json").read_text(encoding="utf-8"))
    geo = res.get("controller_meta", {}).get("geometry", {})
    soft = float(geo.get("stroke_soft_max_m", 0.6948))
    rec = np.load(case / "record" / "record.npz", allow_pickle=True)
    r8 = np.load(case / "r8_series.npz", allow_pickle=True)
    t = rec["t"]
    s = rec["meas.stroke"]
    ph = np.char.lower(np.array([str(p) for p in r8["phase"]]))
    kf = np.flatnonzero(ph == "fault")
    t_fault = float(r8["t"][kf[0]]) if len(kf) else None
    ev_t = float(res.get("event_t_s") or res.get("branch_t_s") or t[0])
    after = t >= ev_t
    s0 = s[np.searchsorted(t, ev_t) - 1] if np.searchsorted(t, ev_t) > 0 else s[0]
    smax = s[after].max(axis=0) if after.any() else s.max(axis=0)
    k_end = kf[0] if len(kf) else len(t) - 1
    k_rec = min(np.searchsorted(t, r8["t"][k_end]), len(t) - 1)
    roll, pitch = rp(rec["body_quat_wxyz"][k_rec:k_rec + 1])
    rows.append({
        "case": case.name,
        "kind": ep.get("kind"), "leg": ep.get("leg"), "depth_mm": 1e3 * float(ep.get("depth_m") or 0.0),
        "ramp_s": ep.get("ramp_s"), "level": base.get("level"), "floor_deg": base.get("floor_deg"),
        "fs_kN": base.get("fs_kN"), "soft_max_m": soft,
        "stroke_at_event_m": [float(x) for x in s0], "stroke_max_after_m": [float(x) for x in smax],
        "reserve_at_event_mm": [1e3 * (soft - 1e-3 - float(x)) for x in s0],
        "fault_t_s": t_fault, "phases": sorted(set(ph.tolist())), "final_phase": str(ph[-1]),
        "roll_pitch_deg_at_fault_or_end": [float(roll[0]), float(pitch[0])],
        "event_t_s": ev_t,
    })

json.dump({"rows": rows}, open(out, "w", encoding="utf-8"), indent=1)
n = len(rows)
faults = [r for r in rows if r["fault_t_s"] is not None]
print(f"episodes {n}, FAULT {len(faults)}")
for r in faults:
    L = LEGS.index(r["leg"]) if r["leg"] in LEGS else None
    print(f"  {r['case']}: {r['kind']} {r['leg']} {r['depth_mm']:.1f} mm, floor {r['floor_deg']}, {r['level']}, Fs {r['fs_kN']}, fault {r['fault_t_s']:.2f} (judge {r['fault_t_s']-3:.2f}), "
          f"stroke@event {np.round(r['stroke_at_event_m'],4)}, max {np.round(r['stroke_max_after_m'],4)}, reserve@event {np.round(r['reserve_at_event_mm'],1)} mm, att {np.round(r['roll_pitch_deg_at_fault_or_end'],3)}")
# settle episodes whose depth exceeds the settled leg's reserve
print("\nsettle episodes, depth vs reserve of the settled leg (reserve = soft - 1 mm - stroke at event):")
cnt_over = 0
near = []
for r in rows:
    if r["kind"] == "settle" and r["leg"] in LEGS:
        L = LEGS.index(r["leg"])
        res_mm = r["reserve_at_event_mm"][L]
        if r["depth_mm"] > res_mm:
            cnt_over += 1
            print(f"  OVER {r['case']}: depth {r['depth_mm']:.1f} > reserve {res_mm:.1f} mm, fault {r['fault_t_s']}, final {r['final_phase']}, att {np.round(r['roll_pitch_deg_at_fault_or_end'],3)}")
        elif r["depth_mm"] > res_mm - 10:
            near.append((r["case"], r["depth_mm"], res_mm, r["fault_t_s"], r["final_phase"]))
print(f"over: {cnt_over}; within 10 mm: {len(near)}")
for x in near:
    print(f"  near {x[0]}: depth {x[1]:.1f}, reserve {x[2]:.1f} mm, fault {x[3]}, final {x[4]}")
mx = max(max(r["stroke_max_after_m"]) for r in rows)
print(f"max stroke reading over all episodes after the event: {mx:.4f} m")
res_all = np.array([min(r["reserve_at_event_mm"]) for r in rows])
print(f"min reserve at the event over all episodes: {res_all.min():.1f} mm; p05 {np.percentile(res_all,5):.1f} mm")
