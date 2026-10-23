"""Separation speed of a dropping-ground leg with the machine corner free to fall (hydraulics rod_side_pressure.md 17.1
used a fixed corner). RR ground patch drops d = 30 mm with a Poly345 ramp T (RE1b-F: 0.05 s); L1-R 6-DoF replica
(l1r_reference), all legs LOCK after an extension, RR unloads on k1 (LOCK) until its elastic force Phi = 0 (lift).

Downward speeds positive. v_rel = v_ground - v_corner (rod relative to barrel at separation; the rod follows the
pad until F = 0 because k_out >> k_h + k_r). Variants: body force on RR elastic only (physical: the body sees the
oil-spring force) / with the L1-R Kelvin dashpot c_n (as Chrono L1-R). Fixed corner = hydraulics assumption.
dynamics_model.md rev. 32 supplement 1 (5.15). usage: run_drop_separation_check.py [out.json]
(default 06_analysis/00_dynamics/drop_separation_check.json; dynamics-dev, about 10 s)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402
import l1r_reference as L  # noqa: E402

D = 0.030
RR = 3


def poly345(t, T):
    if t <= 0:
        return 0.0, 0.0
    if t >= T:
        return D, 0.0
    u = t / T
    return D * (10 * u**3 - 15 * u**4 + 6 * u**5), D / T * (30 * u**2 - 60 * u**3 + 30 * u**4)


def tension(v, kk, m, zeta):
    f = v * math.sqrt(kk * m)
    if zeta > 0:
        f *= math.exp(-zeta * math.atan2(math.sqrt(1 - zeta**2), zeta) / math.sqrt(1 - zeta**2))
    return f


def main():
    p = dm.load_params()
    geo = dm.geometry_from_params(p)
    lp = L.leg_parameters(p, geo)
    m_rod = float(geo.rod_mass[RR])
    kk = float(lp["k_h"][RR] + lp["k_r"][RR])
    res = {"meta": {"case": "RR ground drop 30 mm, Poly345 ramp T, from the static state, all legs LOCK (p_r0 2 bar)",
                    "k_h_plus_k_r_N_m": kk, "m_rod_kg": m_rod, "sqrt_k_m_N_s_m": math.sqrt(kk * m_rod),
                    "frame": "body z up; speeds here downward positive"}}
    for lvl in ("top", "middle", "bottom"):
        lv = L.Level(p, geo, lp, lvl)
        F0 = float(lv.F0[RR])
        for T in (0.05, 0.1, 0.2):
            row = {}
            # fixed corner: elastic lift when the ground has dropped F0 / k1
            u_lo, u_hi = 0.0, T
            for _ in range(80):
                mid = 0.5 * (u_lo + u_hi)
                u_lo, u_hi = (mid, u_hi) if poly345(mid, T)[0] < F0 / lp["k1"][RR] else (u_lo, mid)
            g_fix, vg_fix = poly345(u_hi, T)
            row["fixed_corner"] = {"t_sep_ms": u_hi * 1e3, "ground_drop_mm": g_fix * 1e3, "v_rel_m_s": vg_fix}
            for variant in ("elastic_only", "with_cn"):
                rep = L.Replica(lv, lp["knee_ext"])
                if variant == "elastic_only":
                    rep.C = rep.C - lp["cn"][RR] * np.outer(lv.az[RR], lv.az[RR])
                    rep.cn = lp["cn"].copy(); rep.cn[RR] = 0.0
                st = L.LegStates()

                def e_fun(t, T=T):
                    g, vg = poly345(t, T)
                    e = np.zeros(4); ed = np.zeros(4)
                    e[RR], ed[RR] = -g, -vg
                    return e, ed

                def ev(t, x):
                    e, _ = e_fun(t)
                    return rep.normal(t, x[:6], e, st)[RR]
                ev.terminal = True
                ev.direction = -1
                Minv = np.linalg.inv(lv.M)

                def rhs(t, x):
                    q, v = x[:6], x[6:]
                    e, ed = e_fun(t)
                    dd = -lv.az @ q + e
                    Fx = rep.extra(t, dd, st)
                    gen = lv.az.T @ (lp["k2"] * e + rep.cn * ed + Fx)
                    return np.r_[v, Minv @ (gen - rep.K @ q - rep.C @ v)]
                sol = solve_ivp(rhs, (0, T), np.zeros(12), method="DOP853", rtol=1e-11, atol=1e-14, events=ev,
                                max_step=T / 400)
                ts = float(sol.t_events[0][0])
                x = sol.y_events[0][0]
                g, vg = poly345(ts, T)
                vc = float(-(lv.az[RR] @ x[6:]))          # corner (RR ball point) downward speed
                zc = float(-(lv.az[RR] @ x[:6]))
                row[variant] = {"t_sep_ms": ts * 1e3, "ground_drop_mm": g * 1e3, "v_ground_m_s": vg,
                                "v_corner_m_s": vc, "corner_drop_mm": zc * 1e3, "v_rel_m_s": vg - vc,
                                "v_rel_over_fixed": (vg - vc) / vg_fix}
            ph = row["elastic_only"]["v_rel_m_s"]
            row["tension_estimate_kN (closed form, v_rel elastic_only)"] = {
                f"zeta {z}": -tension(ph, kk, m_rod, z) / 1e3 for z in (0.0, 0.1, 0.3)}
            row["tension_estimate_kN (fixed corner)"] = {
                f"zeta {z}": -tension(vg_fix, kk, m_rod, z) / 1e3 for z in (0.0, 0.1, 0.3)}
            res[f"{lvl} T={T}"] = row
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else dm.PROJECT_ROOT / "06_analysis" / "00_dynamics" / "drop_separation_check.json"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1)
    print("written", out)
    for k, v in res.items():
        print(k, json.dumps(v, default=float)[:900])


if __name__ == "__main__":
    main()
