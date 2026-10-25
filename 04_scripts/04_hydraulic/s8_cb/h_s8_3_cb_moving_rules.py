"""H-S8-3 item 2: CB moving fallback estimate (s8 spec 9.6) against the Chrono CB records.

For every leg and every 10 Hz sample with an applied command != 0 (applied = issued output of
the previous period, d = 1) the rod-side truth p_r (1 ms record at the sample instant) is
compared with candidate estimates evaluated on the 10 Hz head reading:

  L_k   = CB law of the commanded direction at the head reading
          extend  max(p_back, p_set - psi p_h);  retract max(0, (p_set - p_h) / psi)
  R0    = L_k                                            (9.6 as implemented, before margin)
  R1    = max(L_k, L_k-1)                                (one-period hold)
  R2    = lag bound: Y_k = max(L_k, L_k + (Y_k-1 - L_k-1) e^-T/tau
                                     + (L_k-1 - L_k)(tau/T)(1 - e^-T/tau))
          (exact for a first-order rod-side lag tau and a linear head path between samples)
  R2D   = R2 with L = max(extend law, retract law) while the modelled spool (controller copy of
          the valve lag tau_v on the issued commands) still has the other sign or |u_v| < 5 %
          v_max (direction of the plant regulation not certain)
  R3    = max(R2D, R1)
Start of a moving stretch: Y_k0-1 = p_r,true(k0-1) (stands for the locked upper bound of
P-S8-13, which the records show to be >= truth within 0.6 kN).

Output per rule: max (p_r,true - estimate) [bar] and [kN] over all moving samples, i.e. the
lag allowance the margin must add on top of the sensor share (11.4 / 0.7 bar), and the cost
(median / p90 over-estimate).

Usage: python -I h_s8_3_cb_moving_rules.py <out.json> <batch_dir> [<batch_dir> ...]
Read only. No random numbers.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

BAR = 1e5
LEGS = ("FL", "FR", "RL", "RR")
A_P = np.array([0.013273229, 0.013273229, 0.00950331778, 0.00950331778])
A_R = np.array([0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265])
T = 0.1
V_MAX = 0.020924
N_REV = 3
RULES = ("R0", "R1", "R2", "R2D", "R3", "R4D")
WATCH = (("CB_H4V_fdown3.5_Fs0", "RR", 26.0), ("CB_H4V_fdown3.5_Fs0", "RR", 26.4),
         ("CB_H4V_fdown3.5_Fs0", "RR", 26.5))


def load(case: Path):
    meta = json.loads((case / "record" / "meta.json").read_text(encoding="utf-8"))
    act = meta["run"]["engine"]["actuator"]
    s8 = act.get("s8", {})
    if not isinstance(s8, dict) or s8.get("lock_valve") != "counterbalance":
        return None
    cb = s8["counterbalance"]["params"]
    tau_r = float(act["rod_side"]["release_tau_s"])
    valve = act.get("valve", {})
    tau_v = float(valve.get("tau_v_s") or 0.0)
    with np.load(case / "pads.npz", allow_pickle=True) as z:
        p = {k: z[k] for k in ("t", "head_pressure", "rod_pressure")}
    with np.load(case / "r8_series.npz", allow_pickle=True) as z:
        r8 = {k: z[k] for k in ("t", "issued_u", "valve_u")}
    with np.load(case / "record" / "record.npz", allow_pickle=True) as z:
        rec = {k: z[k] for k in ("t", "meas.head_pressure", "u_applied")}
    return cb, tau_r, tau_v, p, r8, rec


def laws(cb, head):
    p_set, psi, back = cb["p_set_Pa"], cb["pilot_ratio"], cb["back_pressure_Pa"]
    return max(back, p_set - psi * head), max(0.0, (p_set - head) / psi)


def run_case(case: Path):
    got = load(case)
    if got is None:
        return []
    cb, tau_r, tau_v, p, r8, rec = got
    t = r8["t"]
    ir = np.clip(np.searchsorted(rec["t"], t - 1e-9), 0, rec["t"].size - 1)
    ip = np.clip(np.searchsorted(p["t"], t - 1e-9), 0, p["t"].size - 1)
    e = math.exp(-T / tau_r)
    g = tau_r / T * (1.0 - e)
    rows = []
    for leg in range(4):
        cmd = np.r_[0.0, r8["issued_u"][:-1, leg]]
        hm = rec["meas.head_pressure"][ir, leg]
        prt = p["rod_pressure"][ip, leg]
        y = {r: math.nan for r in ("R2", "R2D")}
        l_prev = {r: math.nan for r in ("R1", "R2", "R2D")}
        u_pl = rec["u_applied"][ir, leg]
        y4 = [math.nan, math.nan]
        for k in range(t.size):
            sign = math.copysign(1.0, cmd[k]) if cmd[k] != 0.0 else 0.0
            if sign == 0.0:
                y = {r: math.nan for r in y}
                l_prev = {r: math.nan for r in l_prev}
                y4 = [math.nan, math.nan]
                continue
            ext, ret = laws(cb, hm[k])
            l_dir = ext if sign > 0 else ret
            # direction not certain: the applied command changed sign (or started from 0)
            # within the last N_rev periods (spool lag tau_v ln(20) = 3 periods at 0.1 s)
            prev = [cmd[k - j] for j in range(1, N_REV + 1) if k - j >= 0]
            unsure = any(c * sign <= 0.0 for c in prev)
            u_v = float(u_pl[k])
            l_both = max(ext, ret) if unsure else l_dir
            est = {"R0": l_dir}
            # R1 one-period hold
            lp = l_prev["R1"]
            est["R1"] = l_dir if math.isnan(lp) else max(l_dir, lp)
            # R2 / R2D lag bound
            for r, lk in (("R2", l_dir), ("R2D", l_both)):
                if math.isnan(y[r]):
                    # stretch start: previous sample command-free; Y = rod truth there (stand-in
                    # for the locked upper bound), L_k-1 = law of this direction at its head
                    if k == 0:
                        y[r], l_prev[r] = lk, lk
                    else:
                        e0, r0 = laws(cb, hm[k - 1])
                        lp = (max(e0, r0) if r == "R2D" else (e0 if sign > 0 else r0))
                        y[r], l_prev[r] = float(prt[k - 1]), lp
                yk = max(lk, lk + (y[r] - l_prev[r]) * e + (l_prev[r] - lk) * g)
                y[r], est[r] = yk, yk
            est["R3"] = max(est["R2D"], est["R1"])
            # R4D worst monotone path: the law sits at max(L_k-1, L_k) for the whole period
            if math.isnan(y4[0]):
                if k == 0:
                    y4 = [l_both, l_both]
                else:
                    e0, r0 = laws(cb, hm[k - 1])
                    y4 = [float(prt[k - 1]), max(e0, r0) if unsure else (e0 if sign > 0 else r0)]
            top = max(y4[1], l_both)
            y4 = [max(l_both, e * y4[0] + (1.0 - e) * top), l_both]
            est["R4D"] = y4[0]
            l_prev = {"R1": l_dir, "R2": l_dir, "R2D": l_both}
            rows.append({"case": case.name, "leg": LEGS[leg], "t": round(float(t[k]), 2),
                         "sign": sign, "u_plant": u_v, "unsure": bool(unsure),
                         "plant_other_dir": bool(u_v * sign < 0.0),
                         "p_r": float(prt[k]), "p_h": float(hm[k]),
                         **{r: float(est[r]) for r in RULES}})
    return rows


def summary(rows):
    out = {}
    for r in RULES:
        under = np.array([x["p_r"] - x[r] for x in rows])
        a_r = np.array([A_R[LEGS.index(x["leg"])] for x in rows])
        k = int(np.argmax(under))
        over = -under
        out[r] = {"max_under_bar": round(float(under[k]) / BAR, 2),
                  "max_under_kN": round(float(np.max(under * a_r)) / 1e3, 2),
                  "at": f"{rows[k]['case']} {rows[k]['leg']} {rows[k]['t']}",
                  "n_under_gt_0p6kN_with_11p4": int(np.sum((under - 11.4 * BAR) * a_r > 600.0)),
                  "over_p50_bar": round(float(np.median(over)) / BAR, 2),
                  "over_p90_bar": round(float(np.percentile(over, 90)) / BAR, 2),
                  "top5": [f"{rows[i]['case']} {rows[i]['leg']} {rows[i]['t']} "
                           f"{under[i] / BAR:.1f} bar" for i in np.argsort(-under)[:5]]}
    return out


def main() -> None:
    out_path = Path(sys.argv[1])
    rows = []
    for b in sys.argv[2:]:
        for pads in sorted(Path(b).rglob("pads.npz")):
            rows += run_case(pads.parent)
    watch = []
    for c, leg, tt in WATCH:
        for x in rows:
            if x["case"] == c and x["leg"] == leg and abs(x["t"] - tt) < 1e-6:
                watch.append({"case": c, "leg": leg, "t": tt,
                              "p_r_true_bar": round(x["p_r"] / BAR, 2),
                              **{r: round((x["p_r"] - x[r]) / BAR, 2) for r in RULES}})
    # extra margin over the sensor share 11.4 / 0.7 bar that each rule needs (records have no
    # sensor error): max(p_r,true - rule) - share, per direction
    res = {"n_samples": len(rows), "watch_under_bar": watch, "summary": summary(rows),
           "by_direction": {s: summary([x for x in rows if x["sign"] == s])
                            for s in (1.0, -1.0) if any(x["sign"] == s for x in rows)}}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
