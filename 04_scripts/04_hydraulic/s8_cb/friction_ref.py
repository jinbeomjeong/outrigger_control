"""S8 seal-friction spec: single-leg reference cases and CB rod-side lock pressures.

Model (spec section 1): oil-only law G(c_oil) in parallel with a Coulomb element |f| <= F_s
(rigid stick by default, optional stick spring k_st), both in series with k_out.
F = k_out (s_p - s) = G(s_ref - s_p) + f; pressure force = F - f = G.
Locked oil law (rod side on, k_out -> inf form of L2bRodSide):
    G = F_lock + k_h dco + k_r min(dco, dco_knee), dco_knee = dF_knee / (k_h + k_r)
Usage: python -I friction_ref.py <out.json>
"""

import json
import sys

import numpy as np

P_ATM = 1.0e5
LEG = {
    "front": dict(A_p=0.013273229, A_ann=0.00376991118, k_h=29424138.7, k_r=10805133.8,
                  k_out=None, k_ax=25905744.2, F0=118099.0, p_r0=2.0e5),
    "rear": dict(A_p=0.00950331778, A_ann=0.00314159265, k_h=21554361.0, k_r=8748517.55,
                 k_out=None, k_ax=19504614.9, F0=72097.0, p_r0=2.0e5),
}
P_FLOOR_G = 0.1e5 - P_ATM
for leg in LEG.values():
    leg["k_out"] = 1.0 / (1.0 / leg["k_ax"] - 1.0 / leg["k_h"])


def make_locked(leg):
    share = leg["k_r"] / (leg["k_h"] + leg["k_r"])
    dF_knee = (leg["p_r0"] - P_FLOOR_G) * leg["A_ann"] / share
    kk = leg["k_h"] + leg["k_r"]

    def G(dco):
        return leg["F0"] + leg["k_h"] * dco + leg["k_r"] * min(dco, dF_knee / kk)

    def dG(dco):
        return kk if dco < dF_knee / kk else leg["k_h"]

    return G, dG, dF_knee


def composite(leg, dc):
    """Existing L2b locked law (k_out in series), dc = change of s_ref - s since lock."""
    k1 = 1.0 / (1.0 / (leg["k_h"] + leg["k_r"]) + 1.0 / leg["k_out"])
    k2 = 1.0 / (1.0 / leg["k_h"] + 1.0 / leg["k_out"])
    _, _, dF_knee = make_locked(leg)
    return leg["F0"] + k2 * dc + (k1 - k2) * min(dc, dF_knee / k1)


def step(leg, G, dG, s, s_ref, sp_prev, w_prev, F_s, k_st=np.inf):
    """One return-mapping step (spec 1.4). Coordinates: c_oil = s_ref - s_p measured from
    the lock anchor (dco). Returns s_p, w, f, F, stick."""
    k_out = leg["k_out"]

    def solve(f_fun_const, k_extra, w):
        # k_out (sp - s) = G(s_ref - sp) + f, f = const or k_st (w - sp); Newton on monotone h
        sp = sp_prev
        for _ in range(50):
            f = f_fun_const if k_extra == 0.0 else k_extra * (w - sp)
            h = k_out * (sp - s) - G(s_ref - sp) - f
            dh = k_out + dG(s_ref - sp) + k_extra
            dsp = -h / dh
            sp += dsp
            if abs(dsp) < 1e-15:
                break
        return sp

    if np.isinf(k_st):
        sp = sp_prev                          # rigid stick trial
        f_tr = k_out * (sp - s) - G(s_ref - sp)
        if abs(f_tr) <= F_s:
            return sp, sp, f_tr, k_out * (sp - s), True
        f = np.sign(f_tr) * F_s
        sp = solve(f, 0.0, None)
        return sp, sp, f, k_out * (sp - s), False
    sp = solve(None, k_st, w_prev)            # elastic (stick-spring) trial
    f_tr = k_st * (w_prev - sp)
    if abs(f_tr) <= F_s:
        return sp, w_prev, f_tr, k_out * (sp - s), True
    f = np.sign(f_tr) * F_s
    sp = solve(f, 0.0, None)
    return sp, sp + f / k_st, f, k_out * (sp - s), False


def cycle(name, F_s, amp=0.5e-3, n=200, k_st=np.inf):
    """Locked leg (s_ref fixed = 0 at the lock anchor), link displacement s moved quasi-
    statically: c = s_ref - s from 0 -> +amp -> -amp -> 0 (load up, down, back)."""
    leg = LEG[name]
    G, dG, dF_knee = make_locked(leg)
    s_ref = 0.0
    sp = 0.0 + leg["F0"] / leg["k_out"] * 0.0   # dco = 0 at lock; s_p measured from anchor
    # anchor: at lock s_p0 = 0 (c_oil = 0) and s0 = s_p0 - F0/k_out, f = 0
    s0 = -leg["F0"] / leg["k_out"]
    path = np.concatenate([np.linspace(0, amp, n), np.linspace(amp, -amp, 2 * n),
                           np.linspace(-amp, 0, n)])
    w = sp
    rows = []
    for c in path:
        s = s0 - c
        sp, w, f, F, stick = step(leg, G, dG, s, s_ref, sp, w, F_s, k_st)
        rows.append((c, F, F - f, f, sp, stick))
    rows = np.array([(r[0], r[1], r[2], r[3], r[4], float(r[5])) for r in rows])
    pick = {}
    for label, idx in (("c=+amp", n - 1), ("c=0 (down)", n - 1 + n), ("c=-amp", 3 * n - 1),
                       ("c=0 (end)", 4 * n - 1)):
        r = rows[idx]
        pick[label] = {"c_mm": r[0] * 1e3, "F_true_kN": r[1] / 1e3,
                       "F_pressure_kN": r[2] / 1e3, "f_kN": r[3] / 1e3,
                       "s_p_um": r[4] * 1e6, "stick": bool(r[5])}
    # first slip on the way up
    up = rows[:n]
    slip_idx = np.where(up[:, 5] < 0.5)[0]
    pick["first_slip_c_um"] = float(up[slip_idx[0], 0] * 1e6) if len(slip_idx) else None
    pick["first_slip_c_um_analytic"] = F_s / leg["k_out"] * 1e6
    return pick


def regression(name):
    leg = LEG[name]
    G, dG, _ = make_locked(leg)
    s0 = -leg["F0"] / leg["k_out"]
    worst = 0.0
    sp = 0.0
    for c in np.linspace(-2e-3, 2e-3, 401):
        sp, _, f, F, _ = step(leg, G, dG, s0 - c, 0.0, sp, sp, 0.0)
        worst = max(worst, abs(F - composite(leg, c)) / abs(composite(leg, c)))
    return worst


def cb_rod_lock(name, F, psi, p_set=330e5, p_back=2e5):
    leg = LEG[name]
    A_p, A_r = leg["A_p"], leg["A_ann"]
    ext = (p_set * A_p - psi * F) / (A_p + psi * A_r)          # rod CB regulating, extension
    ret = (p_set * A_p - F) / (psi * A_p + A_r)                # head CB regulating, retraction
    return {"p_r0_after_extend_bar_g": max(ext, p_back) / 1e5,
            "p_r0_after_retract_bar_g": ret / 1e5,
            "p_h_extend_bar_g": (F + max(ext, p_back) * A_r) / A_p / 1e5,
            "psi_needed_for_full_open_on_extend": (p_set - p_back) / ((F + p_back * A_r) / A_p)}


def main():
    out = {"k_out_N_m": {k: v["k_out"] for k, v in LEG.items()},
           "stick_to_lock_stiffness_ratio": {
               k: v["k_out"] / (1 / (1 / (v["k_h"] + v["k_r"]) + 1 / v["k_out"]))
               for k, v in LEG.items()},
           "regression_Fs0_vs_composite_max_rel": {k: regression(k) for k in LEG}}
    out["cycle_front_Fs4kN_amp0p5mm"] = cycle("front", 4e3)
    out["cycle_front_Fs4kN_kst1e8"] = cycle("front", 4e3, k_st=1e8)
    out["cycle_rear_Fs3p333kN_amp0p5mm"] = cycle("rear", 4e3 * 0.8333)
    # seal pressure model (spec 1.2): F_s = F_0 + kappa (pi D |p_h - p_r| + pi d p_r)
    F0, Fm = 1.27e3, 3.72e3
    D, d = 0.130, 0.110
    dp_test, pr_test = 120.0, 165.0
    kappa = (Fm - F0) / (np.pi * D * dp_test + np.pi * d * pr_test)   # N/(m bar)
    ext = {}
    for lab, ph, pr, DD, dd in (("front_locked_static", 89.0, 2.0, D, d),
                                ("front_locked_200bar", 200.0, 2.0, D, d),
                                ("front_liftoff_path", 50.0, 190.0, D, d),
                                ("rear_locked_static", 76.0, 2.0, 0.110, 0.090)):
        ext[lab] = (F0 * (DD + dd) / (D + d)
                    + kappa * (np.pi * DD * abs(ph - pr) + np.pi * dd * pr)) / 1e3
    out["seal_pressure_model"] = {"kappa_N_per_m_bar": kappa, "F_s_kN": ext,
                                  "head_only_linear_front_static_kN":
                                      (F0 + (Fm - F0) / 46.6 * 89.0) / 1e3,
                                  "rod_only_linear_front_static_kN":
                                      (F0 + (Fm - F0) / 165.0 * 2.0) / 1e3}
    out["cb_rod_lock"] = {f"{name}_psi{psi}": cb_rod_lock(name, F, psi)
                          for name, F in (("front", 118.1e3), ("rear", 72.1e3))
                          for psi in (3, 4, 8)}
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
