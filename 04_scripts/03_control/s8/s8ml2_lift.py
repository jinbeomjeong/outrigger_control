"""Rev. 48: U-S8-30, pad lift after a settlement in the ML pilot rerun, mechanism split.

For every 'settle' episode: settled leg, depth, ramp (Poly345 profile), mean settle speed,
F_s, level, beta, L0r, and from the 1 ms record (pads 'airborne', engine time) the longest
lift after the event and which leg. For the longest lift:
  t_a / t_b      lift start / end
  lat_cmd        first 10 Hz sample with issued u > 0.5 mm/s on the lifted leg, minus t_a
  lat_valve      first time the plant valve output on that leg exceeds 2 mm/s, minus t_a
  u_mean         mean issued u on the lifted leg in [t_a, t_b] (mm/s)
  ds_leg         s_motor gain of the lifted leg in [t_a, t_b] (mm)
  gap_max        max pad gap over the lift: pad ball-centre z change since t_a minus the ground
                 patch z change (settled leg only; other legs ground fixed) (mm)
  events         controller events on that leg in [t_a - 0.3, t_b + 0.3]
Also the settlement remaining after t_a (depth not yet done when the pad left the ground).
Writes a JSON table and prints one line per episode.
Usage: python -I s8ml2_lift.py <out_json> <batch_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
LEGS = ["FL", "FR", "RL", "RR"]


def poly345(x):
    x = np.clip(x, 0.0, 1.0)
    return 10 * x**3 - 15 * x**4 + 6 * x**5


rows = []
batch = Path(sys.argv[2])
for d in sorted((batch / "episodes").iterdir()):
    if d.name.startswith("_") or not (d / "result.json").exists():
        continue
    case = json.loads((d / "case.json").read_text(encoding="utf-8"))["settings"]
    ep = case["episode"]
    if ep.get("kind") != "settle":
        continue
    base = case["base"]
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    t_ev = float(res["event_t_s"])
    pads = np.load(d / "pads.npz", allow_pickle=True)
    r8 = np.load(d / "r8_series.npz", allow_pickle=True)
    tp = pads["t"]
    air = pads["airborne"]
    after = tp >= t_ev
    best = (0.0, None, None, None)
    for L in range(4):
        a = air[:, L] & after
        if not a.any():
            continue
        edges = np.diff(np.concatenate([[0], a.astype(int), [0]]))
        starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1) - 1
        for s0, s1 in zip(starts, ends):
            dur = tp[s1] - tp[s0]
            if dur > best[0]:
                best = (dur, L, tp[s0], tp[s1])
    sleg = LEGS.index(ep["leg"])
    depth, ramp = float(ep["depth_m"]), float(ep["ramp_s"])
    row = dict(run=d.name, leg_settle=ep["leg"], depth_mm=round(depth * 1e3, 1), ramp_s=ramp,
               v_settle_mm_s=round(depth * 1e3 / ramp, 1), fs_kN=base["fs_kN"], level=base["level"],
               beta=base["beta_GPa"], L0r=base.get("rod_dead_length_m"), floor=base["floor_deg"],
               lift_s=round(best[0], 3), lift_leg=LEGS[best[1]] if best[1] is not None else None)
    if best[1] is not None:
        L, ta, tb = best[1], best[2], best[3]
        t8 = r8["t"]
        iu = r8["issued_u"][:, L] * 1e3
        vu = r8["valve_u"][:, L] * 1e3
        k_cmd = np.flatnonzero((t8 >= ta - 1e-9) & (iu > 0.5))
        row["lat_cmd_s"] = round(float(t8[k_cmd[0]] - ta), 3) if len(k_cmd) else None
        k_v = np.flatnonzero((t8 >= ta - 1e-9) & (vu > 2.0))
        row["lat_valve_s"] = round(float(t8[k_v[0]] - ta), 3) if len(k_v) else None
        w = (t8 >= ta) & (t8 <= tb)
        row["u_mean_mm_s"] = round(float(iu[w].mean()), 2) if w.any() else None
        row["u_others_mean_mm_s"] = [round(float(r8["issued_u"][w, j].mean() * 1e3), 2) if w.any() else None for j in range(4)]
        ja, jb = np.searchsorted(tp, ta), np.searchsorted(tp, tb)
        row["ds_leg_mm"] = round(float((pads["s_motor"][jb, L] - pads["s_motor"][ja, L]) * 1e3), 2)
        zb = pads["ball_centre_world"][:, L, 2]
        zg = np.zeros_like(tp)
        if L == sleg:
            zg = -depth * poly345((tp - t_ev) / ramp)
        gap = (zb[ja:jb + 1] - zb[ja]) - (zg[ja:jb + 1] - zg[ja])
        row["gap_max_mm"] = round(float(gap.max() * 1e3), 2)
        row["t_gap_max_rel_s"] = round(float(tp[ja + int(np.argmax(gap))] - ta), 3)
        row["settle_left_mm"] = round(float((depth - depth * poly345((ta - t_ev) / ramp)) * 1e3), 2) if L == sleg else None
        row["t_a_rel_event_s"] = round(ta - t_ev, 3)
        ev = [str(e) for e in json.loads((d / "controller_events.json").read_text(encoding="utf-8"))]
        sel = []
        for e in ev:
            te = float(e.split("t_s=")[1].split(",")[0])
            if ta - 0.3 <= te <= tb + 0.3 and (LEGS[L] in e) and "INFO_PRESSURE_STEP" not in e:
                sel.append(f"{te - ta:+.2f}:{e.split(chr(39))[1]}")
        row["events"] = sel
        # phase at lift start
        k0 = np.searchsorted(t8, ta)
        row["phase_at_lift"] = str(r8["phase"][min(k0, len(t8) - 1)])
    rows.append(row)
    print(f"{row['run']:9s} settle {row['leg_settle']} {row['depth_mm']:5.1f} mm/{ramp:.3f} s ({row['v_settle_mm_s']:6.1f} mm/s) Fs {row['fs_kN']:.1f}"
          f" | lift {row['lift_s']:.3f} s {row['lift_leg']}"
          + (f" t_a+{row['t_a_rel_event_s']:.2f} left {row['settle_left_mm']} gap {row['gap_max_mm']} mm @+{row['t_gap_max_rel_s']:.2f}"
             f" lat_cmd {row['lat_cmd_s']} lat_valve {row['lat_valve_s']} u {row['u_mean_mm_s']} ds {row['ds_leg_mm']} others {row['u_others_mean_mm_s']}"
             f" {row['events'][:4]}" if row["lift_leg"] else ""))
Path(sys.argv[1]).write_text(json.dumps(rows, indent=1), encoding="utf-8")
