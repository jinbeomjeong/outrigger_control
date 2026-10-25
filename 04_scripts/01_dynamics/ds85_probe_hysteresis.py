"""D-S8-5 (3): residual load after a probe round trip (T2 - T0) from the seal-friction change.

Rigid deck, four legs, NSC pads stuck, crawler lifted. Per leg j (seal_friction.py model 2.1):
    s_ref - s_p = (F - f) / k_oil,   s_p - s = F / k_out
=>  s_ref,j - (A q)_j = F_j / k_ser,j - f_j / k_oil,j,     k_ser = series(k_oil, k_out)
Load changes that keep the deck in equilibrium are self-balanced twist loads dF = lam n
(n = twist vector, n^T A = 0). A round trip returns s_ref, so projecting on n:
    lam = sum_j n_j df_j / k_oil,j  /  sum_j n_j^2 / k_ser,j                       (*)
The friction change df_j of every leg (probed leg: reversal f0 -> f2; other legs: stuck, so
df_j = dF_j, or slipping) leaves the residual twist load. Counterfactual 'others frictionless'
(df_j = 0 for j != i): lam_free = n_i df_i / k_oil,i / sum n_j^2 / k_ser,j.

k_oil,j, k_out,j fitted per leg from the 1 ms record over the READY/PROBE span by least squares:
(F - f) vs (s_motor - s_piston) and F vs (s_piston - s_link) (offsets free).
Usage: python -I ds85_probe_hysteresis.py <out json> <case dir> [...]
"""
import json
import os
import sys

import numpy as np

N_TWIST = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
LEGS = ("FL", "FR", "RL", "RR")


def fit_k(x, y):
    X = np.c_[x, np.ones_like(x)]
    sol, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ sol
    return float(sol[0]), float(np.std(resid))


def main():
    out = {}
    for d in sys.argv[2:]:
        case = os.path.basename(d)
        pads = np.load(os.path.join(d, "pads.npz"))
        ph = json.load(open(os.path.join(d, "probe_history.json"), encoding="utf-8"))
        t = pads["t"]
        F, f = pads["F_cyl"], pads["f_seal"]
        s_ref, s_p, s_l = pads["s_motor"], pads["s_piston"], pads["s_link"]
        rows = [r for r in ph[0] if not r.get("is_skipped") and r.get("t_move_start_s") is not None]
        t_a = min(r["t_move_start_s"] for r in rows) - 2.0
        t_b = max(r["t_second_hold_end_s"] for r in rows) + 0.5
        w = (t >= t_a) & (t <= t_b)
        k_oil = np.zeros(4)
        k_out = np.zeros(4)
        fit = {}
        for j in range(4):
            k_oil[j], e1 = fit_k(s_ref[w, j] - s_p[w, j], F[w, j] - f[w, j])
            k_out[j], e2 = fit_k(s_p[w, j] - s_l[w, j], F[w, j])
            fit[LEGS[j]] = {"k_oil_N_m": k_oil[j], "resid_N": e1, "k_out_N_m": k_out[j], "resid_out_N": e2}
        k_ser = 1.0 / (1.0 / k_oil + 1.0 / k_out)
        den = float(np.sum(N_TWIST**2 / k_ser))
        res = {"fit": fit, "probes": []}
        print(f"== {case}  k_oil [MN/m] {np.round(k_oil / 1e6, 2)}  k_out {np.round(k_out / 1e6, 0)}  "
              f"fit resid [N] {[round(v['resid_N']) for v in fit.values()]}")
        for r in rows:
            i = r["leg_index"]
            ta, t2 = r["t_move_start_s"], r["t_second_hold_end_s"]
            b = (t >= ta - 0.5) & (t < ta)
            e = (t >= t2 - 0.1) & (t <= t2 + 0.1)
            dF = F[e].mean(axis=0) - F[b].mean(axis=0)
            df = f[e].mean(axis=0) - f[b].mean(axis=0)
            lam_fit = float(N_TWIST @ dF)  # n is unit length
            shape_res = float(np.linalg.norm(dF - lam_fit * N_TWIST))
            lam_pred = float(np.sum(N_TWIST * df / k_oil) / den)
            lam_free = float(N_TWIST[i] * df[i] / k_oil[i] / den)
            stuck_others = [bool(pads["seal_stuck"][b | e, j].all()) for j in range(4)]
            row = {"leg": LEGS[i], "dF_kN": (dF / 1e3).tolist(), "df_kN": (df / 1e3).tolist(),
                   "lam_fit_kN": lam_fit / 1e3, "shape_residual_kN": shape_res / 1e3,
                   "lam_pred_kN": lam_pred / 1e3, "lam_free_kN": lam_free / 1e3,
                   "dF_i_kN": dF[i] / 1e3, "dF_i_pred_kN": lam_pred * N_TWIST[i] / 1e3,
                   "dF_i_free_kN": lam_free * N_TWIST[i] / 1e3, "stuck_before_after": stuck_others,
                   "f0_i_kN": float(f[b, i].mean() / 1e3), "f2_i_kN": float(f[e, i].mean() / 1e3)}
            res["probes"].append(row)
            print(f"  probe {LEGS[i]}: dF {np.round(dF / 1e3, 2)} df {np.round(df / 1e3, 2)} kN | lam fit {lam_fit / 1e3:+.2f} "
                  f"(shape res {shape_res / 1e3:.2f}) pred {lam_pred / 1e3:+.2f} free {lam_free / 1e3:+.2f} | dF_i {dF[i] / 1e3:+.2f} "
                  f"pred {lam_pred * N_TWIST[i] / 1e3:+.2f} free {lam_free * N_TWIST[i] / 1e3:+.2f} | f0 {f[b, i].mean() / 1e3:+.2f}"
                  f" f2 {f[e, i].mean() / 1e3:+.2f} stuck {stuck_others}")
        out[case] = res
    json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1)
    print("wrote", sys.argv[1])


if __name__ == "__main__":
    main()
