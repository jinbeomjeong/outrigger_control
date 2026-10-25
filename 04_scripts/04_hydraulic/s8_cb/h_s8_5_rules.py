"""H-S8-5 part C: hold-rule variants on the physical drain grid (pilot check and CB), by subset.

Rules (readings with a static offset e in {-4, 0, +4} bar; trigger = one-period drop > 100 bar):
  cur1   : p(k+1) <= max(p_hi, rho p(k))                     (P-S8-21, rho 0.5, one period)
  exc1   : p(k+1) <= p_hi + rho (p(k) - p_hi)                 (excess form)
  curN   : p(k+N) <= max(p_hi, rho p(k)), N = 2, 3            (longer hold, same form)
  mono   : hold while each next sample drops by >= delta below the previous one and is > p_hi;
           explained when a sample is <= p_hi within T_hold; fallback on a stall / rise / timeout
Usage: python -I h_s8_5_rules.py <out.json>
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h_s8_5_physical_drain as ph  # noqa: E402

N_S = 42  # samples: 4.1 s after the opening
PHASES = np.arange(0.0, 0.1, 0.01)


def samples(prm: dict) -> np.ndarray:
    t = (-PHASES[:, None] + 0.1 * np.arange(N_S)[None, :]).reshape(1, -1)
    n = prm["y0"].shape[0]
    return (ph.pressure(t, prm) / ph.BAR).reshape(n, PHASES.size, N_S)


def rules(r: np.ndarray, p_hi: np.ndarray) -> dict:
    hi = p_hi[:, None, None]
    drop = r[:, :, :-1] - r[:, :, 1:]
    trig = drop > ph.DP_MAX
    has = trig.any(axis=2)
    k = np.argmax(trig, axis=2) + 1
    out = {"has": has}
    take = lambda j: np.take_along_axis(r, np.minimum(k + j, N_S - 1)[..., None], 2)[..., 0]  # noqa: E731
    p1 = take(0)
    h = hi[..., 0]
    for n in (1, 2, 3, 5):
        out[f"cur{n}"] = has & (take(n) > np.maximum(h, 0.5 * p1))
    out["exc1"] = has & (take(1) > h + 0.5 * np.maximum(p1 - h, 0.0))
    out["exc2"] = has & (take(2) > h + 0.5 * np.maximum(p1 - h, 0.0))
    for delta, t_hold in ((0.5, 2.0), (1.0, 2.0), (2.0, 2.0), (1.0, 1.0), (1.0, 3.0), (1.0, 4.0)):
        nh = int(round(t_hold / 0.1))
        fail = np.zeros_like(has)
        done = np.zeros_like(has)
        for j in range(1, nh + 1):
            pj = take(j)
            pprev = take(j - 1)
            ok_end = pj <= h
            stall = (~ok_end) & (pj > pprev - delta)
            fail |= has & ~done & stall
            done |= ok_end | stall
        fail |= has & ~done  # timeout above p_hi
        out[f"mono_d{delta}_T{t_hold}"] = fail
    return {k2: v.any(axis=1) for k2, v in out.items()}


def main() -> None:
    out_path = Path(sys.argv[1])
    g = {"beta": (0.69e9, 1.0e9, 1.6e9), "l0r": (0.02, 0.05, 0.10), "s": (0.1, 0.3, 0.5, 0.65),
         "u": (0.05, 0.1, 0.25, 0.5, 1.0), "tau_v": (0.0, 0.02, 0.05, 0.1, 0.2),
         "dpc": (5.0, 10.0, 20.0), "kappa": (1.0, 0.5), "hose": (0.0, 1.0)}
    cases = {"pilot": ((125.0, 174.0, 250.0, 350.0), (0.0,)),
             "cb": ((250.0, 290.0, 324.0), (131.0, 156.0))}
    names = ("leg", "beta", "l0r", "s", "p_pre", "u", "tau_v", "dpc", "kappa", "hose", "p_reg")
    result = {}
    for valve, (pp, preg) in cases.items():
        for free in (True, False):
            combos = list(itertools.product(("front", "rear"), g["beta"], g["l0r"], g["s"], pp,
                                            g["u"], g["tau_v"], g["dpc"], g["kappa"], g["hose"],
                                            preg))
            arr = {nm: np.array([c[j] for c in combos]) for j, nm in enumerate(names)}
            parts: dict = {e: {} for e in (-4.0, 0.0, 4.0)}
            for i0 in range(0, len(combos), 3000):
                sub = combos[i0:i0 + 3000]
                prm = ph.build(sub, free)
                p_reg = np.array([c[-1] for c in sub])
                p_hi = np.where(p_reg > 0, p_reg + 15.0, ph.P_HI)
                smp = samples(prm)
                for e in parts:
                    rr = rules(smp + e, p_hi)
                    for kk, v in rr.items():
                        parts[e].setdefault(kk, []).append(v)
            acc = {e: {kk: np.concatenate(v) for kk, v in d.items()} for e, d in parts.items()}
            p_inf_raw = ph.build(combos, free)["p_inf_raw"] / ph.BAR
            floor_ok = (arr["p_reg"] > 0) | (p_inf_raw + 4.0 <= ph.P_HI - 0.5)
            result.setdefault("floor", {})[f"{valve}_{free}"] = {
                "p_inf_bar_max": float(p_inf_raw.max()),
                "floor_not_ok": int((~floor_ok).sum()),
                "floor_not_ok_combos": sorted({(str(a), float(b), float(c)) for a, b, c in zip(
                    arr["leg"][~floor_ok], arr["kappa"][~floor_ok], arr["dpc"][~floor_ok],
                    strict=True)})}
            subsets = {
                "floor_ok": floor_ok,
                "floor_ok_no_hose": floor_ok & (arr["hose"] == 0),
                "floor_ok_no_hose_ppre<=174": floor_ok & (arr["hose"] == 0)
                & (arr["p_pre"] <= 174),
                "floor_ok_ppre<=174": floor_ok & (arr["p_pre"] <= 174),
                "floor_ok_u>=0.25": floor_ok & (arr["u"] >= 0.25),
                "floor_ok_no_hose_u>=0.25": floor_ok & (arr["hose"] == 0) & (arr["u"] >= 0.25),
                "all": np.ones(len(combos), bool),
                "no_hose": arr["hose"] == 0,
                "no_hose_ppre<=174": (arr["hose"] == 0) & (arr["p_pre"] <= 174),
                "ppre<=174": arr["p_pre"] <= 174,
                "no_hose_u>=0.25": (arr["hose"] == 0) & (arr["u"] >= 0.25),
                "u>=0.25": arr["u"] >= 0.25,
                "kappa1_no_hose_ppre<=174_tauv<=0.1": (arr["kappa"] == 1) & (arr["hose"] == 0)
                & (arr["p_pre"] <= 174) & (arr["tau_v"] <= 0.1),
            }
            res = {}
            for sname, m in subsets.items():
                if not m.any():
                    continue
                row = {"n": int(m.sum())}
                for kk in acc[0.0]:
                    # worst over the sensor offsets
                    worst = np.zeros(int(m.sum()), bool)
                    for e in acc:
                        worst |= acc[e][kk][m]
                    row[kk] = int(worst.sum())
                res[sname] = row
            result[f"{valve}_{'free' if free else 'stuck'}"] = res
            print(valve, free, json.dumps(res, indent=0))
    out_path.write_text(json.dumps(result, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
