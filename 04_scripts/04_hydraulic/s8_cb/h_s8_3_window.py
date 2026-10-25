"""H-S8-3 item 3: P-S8-13 lock window with a physical lock model, on the existing records.

Window variants (controller side, 10 Hz):
  eps   W = tau_v ln(max(|u_last|, eps) / eps) + T,  eps = 1e-6 m/s (current P-S8-13 (2))
  ol    W = tau_v ln(max(|u_last|, u_ol) / u_ol) + t_c + T,  u_ol = delta v_max (spool overlap
        flow edge), t_c = check closing delay (pilot decay + poppet seat)
For each command-free stretch of every case: the P-S8-13 estimate (h_s8_2_lock_ratio.
window_estimate, same start values and R_ub) with that window, the over-estimate at the stretch
end (truth - lower bound, kN) and the optimism max (lower bound - truth). The records come from
the plant with eps = 1e-6, so a stretch whose plant lock (1 ms) is later than the new window is
counted separately: there the new window is not valid for this plant (it needs the plant change
of the same rule) and its optimism is reported, not judged.

Usage: python -I h_s8_3_window.py <out.json> <batch_dir> [<batch_dir> ...]
Read only. No random numbers.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h_s8_2_lock_ratio as h2  # noqa: E402

V_MAX = 0.020924
T = 0.1
VARIANTS = {"eps": None, "ol1_tc50": (0.01, 0.05), "ol2_tc50": (0.02, 0.05),
            "ol5_tc50": (0.05, 0.05), "ol2_tc100": (0.02, 0.10)}


def window(u_last, tau_v, variant):
    if variant is None:
        return h2.lock_window_s(u_last, tau_v)
    delta, t_c = variant
    u_ol = delta * V_MAX
    return tau_v * math.log(max(abs(u_last), u_ol) / u_ol) + t_c + T


def stretches(case):
    r8, rec, p = case["r8"], case["rec"], case["pads"]
    t = r8["t"]
    ir = np.clip(np.searchsorted(rec["t"], t - 1e-9), 0, rec["t"].size - 1)
    ip = np.clip(np.searchsorted(p["t"], t - 1e-9), 0, p["t"].size - 1)
    out = []
    for leg in range(4):
        cmd = np.r_[0.0, r8["issued_u"][:-1, leg]]
        hm = rec["meas.head_pressure"][ir, leg]
        st = rec["meas.stroke"][ir, leg]
        ph_true = p["head_pressure"][ip, leg]
        f_true = p["F_pressure"][ip, leg]
        f_floor = -math.inf  # no lift-off cap (P-S8-13 (6))
        k, last_sign, last_u, hist = 0, 1.0, 0.0, []
        n = t.size
        while k < n:
            if cmd[k] != 0.0:
                hist.append((t[k], h2.model_moving(case, float(np.sign(cmd[k])), hm[k], leg)))
                last_sign, last_u = float(np.sign(cmd[k])), float(cmd[k])
                k += 1
                continue
            k0 = k
            while k < n and cmd[k] == 0.0:
                k += 1
            if k0 == 0:
                continue
            idx = np.arange(k0, k)
            m_prev = max([v for (tt, v) in hist if tt >= t[k0] - h2.PREV_S - 1e-9], default=-np.inf)
            jl = h2.true_lock_time(p, leg, t[k0] - 0.1, t[k - 1])
            delay = float(p["t"][jl] - t[k0]) if jl is not None else math.nan
            row = {"case": case["name"], "leg": h2.LEGS[leg], "t0": round(float(t[k0]), 2),
                   "u_last_mm_s": 1e3 * last_u, "lock_delay_s": delay}
            for name, var in VARIANTS.items():
                w_s = window(last_u, case["tau_v"], var)
                in_w = t[idx] < t[k0] + w_s - 1e-9
                in_w[0] = True
                est = h2.window_estimate(case, last_sign, hm[idx], st[idx], in_w, leg, m_prev)
                low = np.maximum(ph_true[idx] * h2.A_P[leg] - est * h2.A_R[leg], f_floor)
                err = low - f_true[idx]
                row[name] = {"W_s": w_s, "opt_max_kN": float(err.max()) / 1e3,
                             "over_end_kN": float(-err[-1]) / 1e3,
                             "plant_lock_after_W": bool(not math.isnan(delay) and delay > w_s)}
            out.append(row)
    return out


def main() -> None:
    out_path = Path(sys.argv[1])
    rows = []
    for b in sys.argv[2:]:
        for c in h2.find_cases(Path(b)):
            case = h2.load_case(c)
            if case is None:
                continue
            rows += stretches(case)
        print(b, len(rows), flush=True)
    res = {"n_stretches": len(rows), "variants": {}}
    for name in VARIANTS:
        w = np.array([r[name]["W_s"] for r in rows])
        late = np.array([r[name]["plant_lock_after_W"] for r in rows])
        opt = np.array([r[name]["opt_max_kN"] for r in rows])
        over = np.array([r[name]["over_end_kN"] for r in rows])
        ok = ~late
        res["variants"][name] = {
            "W_s_min_p50_max": [round(float(w.min()), 3), round(float(np.median(w)), 3),
                                round(float(w.max()), 3)],
            "n_plant_lock_after_W": int(late.sum()),
            "opt_max_kN_consistent": round(float(opt[ok].max()), 3),
            "opt_max_kN_inconsistent": round(float(opt[late].max()), 3) if late.any() else None,
            "n_opt_gt_0p6_inconsistent": int(np.sum(opt[late] > 0.6)) if late.any() else 0,
            "over_end_kN_p50_p90_p99_max_consistent": [
                round(float(np.percentile(over[ok], q)), 2) for q in (50, 90, 99, 100)],
            "n_over_end_gt_20kN_consistent": int(np.sum(over[ok] > 20.0)),
        }
    d = np.array([r["lock_delay_s"] for r in rows])
    d = d[np.isfinite(d)]
    res["plant_lock_delay_s_min_p50_p90_max"] = [round(float(np.percentile(d, q)), 3)
                                                 for q in (0, 50, 90, 100)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"summary": res, "rows": rows}, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
