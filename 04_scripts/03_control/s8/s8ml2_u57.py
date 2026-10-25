"""Rev. 48: U-S8-30 lifts split into the primary support-loss leg and U57 secondary lifts.

Primary leg = the leg with the largest cumulative lift after the settlement (the settled leg
when the CG stays inside the remaining tripod, else its diagonal partner tips off).
U57 physical window (spec 62): [event, primary last re-contact + T3 0.82 s], capped at 5 s.
Secondary (U57) = the other three legs inside the window: summed lift time and max gap.
Gap: pad ball-centre z change since the lift start minus the ground-patch change (settled leg,
Poly345 profile); other legs sit on the fixed floor.
Also the primary re-contact time from the event (first lift start -> last re-contact).
With the third argument 'pair', the event legs are the settled leg and its diagonal partner
(tipping), U57 then covers the two adjacent legs; the primary is the event leg lifted longest.
Usage: python -I s8ml2_u57.py <out_json> <batch_dir> [pair]
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
LEGS = ["FL", "FR", "RL", "RR"]
T3 = 0.82
EVENT_PAIR = len(sys.argv) > 3 and sys.argv[3] == 'pair'  # event legs = settled leg + its diagonal
CAP = 5.0


def poly345(x):
    x = np.clip(x, 0.0, 1.0)
    return 10 * x**3 - 15 * x**4 + 6 * x**5


def intervals(mask):
    edges = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1) - 1))


rows = []
batch = Path(sys.argv[2])
for d in sorted((batch / "episodes").iterdir()):
    if d.name.startswith("_") or not (d / "result.json").exists():
        continue
    st = json.loads((d / "case.json").read_text(encoding="utf-8"))["settings"]
    ep = st["episode"]
    if ep.get("kind") != "settle":
        continue
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    t_ev = float(res["event_t_s"])
    pads = np.load(d / "pads.npz", allow_pickle=True)
    tp = pads["t"]
    air = pads["airborne"] & (tp >= t_ev)[:, None]
    dt = np.median(np.diff(tp))
    cum = air.sum(axis=0) * dt
    if cum.max() <= 0:
        continue
    depth, ramp = float(ep["depth_m"]), float(ep["ramp_s"])
    sleg = LEGS.index(ep["leg"])
    zg = np.zeros((len(tp), 4))
    zg[:, sleg] = -depth * poly345((tp - t_ev) / ramp)
    zb = pads["ball_centre_world"][:, :, 2]

    def gap_of(L, s0, s1):
        g = (zb[s0:s1 + 1, L] - zb[s0, L]) - (zg[s0:s1 + 1, L] - zg[s0, L])
        return float(g.max())

    DIAG = {0: 3, 3: 0, 1: 2, 2: 1}
    event_legs = (sleg, DIAG[sleg]) if EVENT_PAIR else (int(np.argmax(cum)),)
    P = max(event_legs, key=lambda L: cum[L])
    ivp = intervals(air[:, P])
    t_first, t_last = tp[ivp[0][0]], tp[ivp[-1][1]]
    gap_p = max(gap_of(P, a, b) for a, b in ivp)
    w_end = min(t_last + T3, t_ev + CAP)
    sec_sum, sec_gap, sec_detail = 0.0, 0.0, {}
    outside = 0.0
    for L in range(4):
        if L in event_legs:
            continue
        for a, b in intervals(air[:, L]):
            dur = tp[b] - tp[a] + dt
            if tp[a] <= w_end:
                sec_sum += dur
                sec_gap = max(sec_gap, gap_of(L, a, b))
                sec_detail[LEGS[L]] = round(sec_detail.get(LEGS[L], 0.0) + dur, 3)
            else:
                outside += dur
    row = dict(run=d.name, settle=ep["leg"], depth_mm=round(depth * 1e3, 1), ramp_s=ramp,
               v_mm_s=round(depth * 1e3 / ramp, 1), fs_kN=st["base"]["fs_kN"],
               primary=LEGS[P], primary_is_settled=(P == sleg), primary_cum_s=round(float(cum[P]), 3),
               primary_recontact_from_event_s=round(float(t_last - t_ev), 3),
               primary_first_lift_rel_event_s=round(float(t_first - t_ev), 3),
               primary_gap_mm=round(gap_p * 1e3, 2), window_s=round(w_end - t_ev, 2),
               u57_sum_s=round(sec_sum, 3), u57_gap_mm=round(sec_gap * 1e3, 2), u57_legs=sec_detail,
               outside_window_s=round(outside, 3))
    row["u57_pass"] = bool(row["u57_sum_s"] <= 0.5 and row["u57_gap_mm"] <= 2.0 and outside == 0.0)
    rows.append(row)
    print(f"{d.name:9s} settle {ep['leg']} {row['depth_mm']:5.1f}mm {row['v_mm_s']:6.1f}mm/s | primary {row['primary']}"
          f"{'(settled)' if P == sleg else '(tipped) '} cum {row['primary_cum_s']:.3f} s recontact +{row['primary_recontact_from_event_s']:.2f} s gap {row['primary_gap_mm']:5.1f} mm"
          f" | U57 sum {row['u57_sum_s']:.3f} s gap {row['u57_gap_mm']:.2f} mm {sec_detail} outside {outside:.3f} -> {'pass' if row['u57_pass'] else 'FAIL'}")
Path(sys.argv[1]).write_text(json.dumps(rows, indent=1), encoding="utf-8")
print("settle episodes with any lift:", len(rows), " U57 fail:", sum(not r["u57_pass"] for r in rows))
