"""L1-R (user decision 2026-10-22, Q16 option b): rod-side chamber as a one-way nonlinear parallel
spring in L1. Hydraulic specification numbers for rod_side_pressure.md section 14.

1. parameters per leg type vs extension e (stroke 0.70 m)
2. reference implementation of the locked rod-side law (pad-force coordinates and piston
   coordinates) and unit-test reference cases
3. discrete-time error of the two implementation candidates
   (i)  contact-stiffness state machine (extra pad-level spring Delta_k, anchored at the lock)
   (ii) piston DOF (oil springs between barrel and rod body, rod body on the contact path)
   schemes: E0 explicit at x_n (like SMC contact), E1 hook one step late (x_{n-1}),
            P predictor (x_{n-1} + h v_{n-1}), I implicit (linearised backward Euler, TSDA+Jacobian)
   -> numerical damping of the relevant modes from the eigenvalues of the discrete map
4. transition / spike time simulations (run in parallel processes): load ramp through the floor
   knee, unload to lift-off, lock entry anchored vs naive

All pressures gauge unless *_abs. Run: conda run -n hydraulics-dev python -I l1r_rod_spring_spec.py
"""
from __future__ import annotations

import argparse
import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

BAR = 1.0e5
P_ATM = 1.01325e5
P_FLOOR_ABS = 0.1e5  # ASSUMPTION
FLOOR_G = P_FLOOR_ABS - P_ATM
BETA = 1.0e9
S_MAX = 0.70
L0H = 0.05  # ASSUMPTION
L0R = 0.05  # ASSUMPTION
G = 9.80665
M_ROD = {"front": 106.784, "rear": 71.5}  # rear: cad shape-synthesis estimate (Q-C3)
K_OUT = {"front": 2.166e8, "rear": 2.051e8}  # dynamics 5.11.2 (rod + frame + contact series)
GEOM = {"front": (0.130, 0.110, 0.4011), "rear": (0.110, 0.090, 0.3909)}  # bore, rod, e_op (dyn 5.11.2)
F_STATIC = {"front": 118.25e3, "rear": 72.8e3}
PSI, P_CR, P_BA, P_BB = 3.5, 3 * BAR, 5 * BAR, 5 * BAR
P_R0_EXT = 2 * BAR
ALPHA = 6.5e-4
S_SUPPORT = 4.77e6


def areas(leg):
    b, r, _ = GEOM[leg]
    a_p = math.pi / 4 * b * b
    return a_p, math.pi / 4 * (b * b - r * r)


def stiff(leg, e=None, l0r=L0R, beta=BETA):
    a_p, a_ann = areas(leg)
    e = GEOM[leg][2] if e is None else e
    k_h = beta * a_p / (L0H + e)
    k_r = beta * a_ann / (S_MAX - e + l0r)
    ser = lambda *k: 1 / sum(1 / x for x in k)  # noqa: E731
    kn = ser(k_h, K_OUT[leg])
    kn2 = ser(k_h + k_r, K_OUT[leg])
    return {"e": e, "k_h": k_h, "k_r": k_r, "r": k_r / (k_h + k_r), "kn": kn, "kn_rod": kn2, "dk": kn2 - kn,
            "q_lag": (kn2 - kn) / kn2, "A_p": a_p, "A_ann": a_ann, "L_r": S_MAX - e + l0r, "L_h": L0H + e}


def p_r_retract_threshold(leg, f_cyl):
    a_p, a_ann = areas(leg)
    phi = a_p / a_ann
    p_h = max(P_BA, (f_cyl / a_ann + P_CR + P_BA * (1 - 1 / PSI)) / (phi - 1 / PSI))
    return (p_h * a_p - f_cyl) / a_ann


# ----------------------------------------------------------------------------- locked law
class LockedRodLaw:
    """Reference law in pad-force coordinates (quasi-static, rod inertia ignored).

    Anchor at lock entry: (F_lock, delta_lock, p_r0). While locked the pad force is an elastic
    (history-free) function of the pad deflection delta:
        F < F_fl : dF/ddelta = kn_rod   (rod side above the floor)
        F >= F_fl: dF/ddelta = kn       (rod side at the floor)
    with F_fl = F_lock + (p_r0 - p_floor) A_ann / r. Rod pressure p_r = p_r0 - r (F - F_lock)/A_ann,
    clamped at the floor. Contact unilateral: F >= 0 (lift-off), F_cyl = F - m g.
    """

    def __init__(self, leg, f_lock, delta_lock, p_r0, exact_log=False):
        self.s = stiff(leg)
        self.f_lock, self.d_lock, self.p_r0 = f_lock, delta_lock, p_r0
        self.f_fl = f_lock + (p_r0 - FLOOR_G) * self.s["A_ann"] / self.s["r"]
        self.d_fl = delta_lock + (self.f_fl - f_lock) / self.s["kn_rod"]
        self.exact_log = exact_log

    def force(self, delta):
        if delta <= self.d_fl:
            f = self.f_lock + self.s["kn_rod"] * (delta - self.d_lock)
        else:
            f = self.f_fl + self.s["kn"] * (delta - self.d_fl)
        return max(f, 0.0)

    def stiffness(self, delta):
        if self.force(delta) <= 0:
            return 0.0
        return self.s["kn_rod"] if delta <= self.d_fl else self.s["kn"]

    def p_r(self, f_pad):
        """Rod pressure as a function of the pad force (lift-off: F_pad -> 0 holds the lift-off value)."""
        df_oil = f_pad - self.f_lock  # = change of F_cyl (quasi-static, rod inertia ignored)
        if self.exact_log:
            # piston shift from the head+rod oil springs, exact log law for the rod chamber
            dx = -df_oil / (self.s["k_h"] + self.s["k_r"])
            v0 = self.s["A_ann"] * self.s["L_r"]
            p = self.p_r0 + BETA * math.log(v0 / (v0 - self.s["A_ann"] * dx))
        else:
            p = self.p_r0 - self.s["r"] * df_oil / self.s["A_ann"]
        return max(p, FLOOR_G)


def reference_cases():
    """Unit-test reference cases: input history -> expected p_r, pad stiffness."""
    out = []
    for leg in ("front", "rear"):
        s = stiff(leg)
        fl = F_STATIC[leg]
        d0 = fl / s["kn"]  # moving (head only) deflection at the lock
        thr = p_r_retract_threshold(leg, fl)
        for lock, pr0 in (("EXT", P_R0_EXT), ("RET", thr)):
            law = LockedRodLaw(leg, fl, d0, pr0)
            for df in (-10e3, +3e3, +10e3, +60e3, -(fl + MG(leg))):
                f = fl + df
                if f <= 0:
                    # lift-off: pad force 0; oil force at F_cyl = -m g, rod pressure from the oil change
                    df_oil = -(fl + MG(leg))
                    p = max(pr0 - s["r"] * df_oil / s["A_ann"], FLOOR_G)
                    k = 0.0
                    delta = law.d_lock - (fl + MG(leg)) / s["kn_rod"]  # pad force F_cyl + m g -> 0
                else:
                    # invert force(delta)
                    if f <= law.f_fl:
                        delta = law.d_lock + df / s["kn_rod"]
                    else:
                        delta = law.d_fl + (f - law.f_fl) / s["kn"]
                    p = law.p_r(f)
                    k = law.stiffness(delta)
                exact = LockedRodLaw(leg, fl, d0, pr0, exact_log=True)
                p_exact = exact.p_r(max(f, 0.0)) if f > 0 else max(
                    pr0 + BETA * math.log(1 / (1 - s["A_ann"] * (fl + MG(leg)) / (s["k_h"] + s["k_r"])
                                              / (s["A_ann"] * s["L_r"]))), FLOOR_G)
                out.append({"leg": leg, "lock_from": lock, "F_lock_kN": fl / 1e3, "p_r0_bar": pr0 / BAR,
                            "dF_pad_kN": df / 1e3, "F_floor_kN": law.f_fl / 1e3,
                            "delta_minus_lock_mm": (delta - law.d_lock) * 1e3,
                            "p_r_bar_linear": p / BAR, "p_r_bar_exact_log": p_exact / BAR,
                            "k_pad_N_m": k, "state": ("LIFT" if f <= 0 else "FLOOR" if f > law.f_fl else "LOCK")})
    return out


def MG(leg):  # noqa: N802
    return M_ROD[leg] * G


# ----------------------------------------------------------------------------- discrete maps
def discrete_damping(m, k_explicit, k_special, c, h, scheme):
    """1-DOF: semi-implicit (symplectic) Euler for explicit forces; k_special treated by `scheme`.
    Returns (zeta_discrete, f_discrete_Hz)."""
    if scheme == "I":  # implicit linearised on k_special and c (TSDA with Jacobian)
        # v' = v + h(-ke x - ks (x + h v') - c v')/m ; x' = x + h v'
        a = 1 + h * c / m + h * h * k_special / m
        # state (x, v): v' = (v - h ke x/m - h ks x/m)/a
        A = np.zeros((2, 2))
        A[1, 0] = -h * (k_explicit + k_special) / m / a
        A[1, 1] = 1 / a
        A[0, :] = [1 + h * A[1, 0], h * A[1, 1]]
    else:
        # state (x_n, v_n, x_{n-1}, v_{n-1})
        A = np.zeros((4, 4))
        # force = -ke x_n - c v_n - ks * x_eval
        if scheme == "E0":
            ev = np.array([1.0, 0, 0, 0])
        elif scheme == "E1":
            ev = np.array([0, 0, 1.0, 0])
        elif scheme == "P":
            ev = np.array([0, 0, 1.0, h])
        else:
            raise ValueError(scheme)
        frow = -k_explicit * np.array([1.0, 0, 0, 0]) - c * np.array([0, 1.0, 0, 0]) - k_special * ev
        vrow = np.array([0, 1.0, 0, 0]) + h * frow / m
        xrow = np.array([1.0, 0, 0, 0]) + h * vrow
        A[0], A[1] = xrow, vrow
        A[2] = [1, 0, 0, 0]
        A[3] = [0, 1, 0, 0]
    lam = np.linalg.eigvals(A)
    lam = lam[np.abs(lam.imag) > 1e-12]
    lam = lam[np.argmax(np.abs(lam))] if len(lam) else None
    if lam is None:
        return float("nan"), float("nan")
    s = np.log(lam) / h
    return float(-s.real / abs(s)), float(abs(s.imag) / (2 * math.pi))


def damping_table():
    rows = []
    for leg in ("front", "rear"):
        st = stiff(leg)
        # (i) leg-axial dominated modes: heave 7.4 Hz zeta 0.03, rocking 1.8 Hz zeta 0.007 (dyn)
        for mode, f_hz, zeta in (("heave", 7.4, 0.03), ("rocking", 1.8, 0.007)):
            w = 2 * math.pi * f_hz
            k_tot = st["kn_rod"]
            m = k_tot / w**2
            c = 2 * zeta * math.sqrt(k_tot * m)
            ks = st["dk"]
            for h in (2e-4, 1e-4, 1e-5):
                for sch in ("E0", "E1", "P"):
                    z, f = discrete_damping(m, k_tot - ks, ks, c, h, sch)
                    z_ref, _ = discrete_damping(m, k_tot, 0.0, c, h, "E0")  # same mode, no special part
                    rows.append({"impl": "(i) contact state machine", "leg": leg, "mode": mode, "h": h,
                                 "scheme": sch, "zeta_phys": zeta, "zeta_disc": z,
                                 "dzeta_vs_all_explicit": z - z_ref, "dzeta_pct_of_phys": (z - z_ref) / zeta * 100,
                                 "f_Hz": f, "q_special": ks / k_tot})
        # (ii) rod local mode: rod body on oil springs (k_h + k_r) and the outer path k_out, zeta 0.30
        m = M_ROD[leg]
        k_oil = st["k_h"] + st["k_r"]
        k_tot = k_oil + K_OUT[leg]
        w = math.sqrt(k_tot / m)
        c = 2 * 0.30 * math.sqrt(k_tot * m)
        for h in (2e-4, 1e-4, 5e-5, 1e-5):
            for sch in ("E0", "E1", "P", "I"):
                # oil springs = special part; outer path (contact) explicit
                z, f = discrete_damping(m, K_OUT[leg], k_oil, c, h, sch)
                rows.append({"impl": "(ii) piston DOF", "leg": leg, "mode": "rod local", "h": h, "scheme": sch,
                             "zeta_phys": 0.30, "zeta_disc": z, "dzeta_vs_phys": z - 0.30,
                             "f_Hz": f, "f_cont_Hz": w / (2 * math.pi), "w_h": w * h, "q_special": k_oil / k_tot})
    return rows


# ----------------------------------------------------------------------------- time simulations
def sim_case(args):
    """Heave-mode mass on the (i) locked law; external force ramp through the knee and to lift-off.
    scheme: 'ref' (h 1e-6, E0 on the whole law), 'E0', 'E1', 'P' (special = law - kn*delta part),
    'naive' (extra spring Delta_k * delta, not anchored -> lock entry jump)."""
    leg, scheme, h, lock_from = args
    st = stiff(leg)
    w = 2 * math.pi * 7.4
    m = st["kn_rod"] / w**2
    c = 2 * 0.03 * math.sqrt(st["kn_rod"] * m)
    fl = F_STATIC[leg]
    pr0 = P_R0_EXT if lock_from == "EXT" else p_r_retract_threshold(leg, fl)
    d_lock = fl / st["kn"]
    law = LockedRodLaw(leg, fl, d_lock, pr0)
    hh = 1e-6 if scheme == "ref" else h
    t_lock, t_end = 0.05, 1.25

    def f_ext(t):  # downward load on the leg (pad force at equilibrium)
        if t < 0.25:
            return fl
        if t < 0.65:
            return fl + (261e3 - fl) * (t - 0.25) / 0.4
        if t < 0.85:
            return 261e3
        return max(261e3 - (261e3 + 20e3) * (t - 0.85) / 0.4, -20e3)  # drives to lift-off

    x, v = d_lock, 0.0
    hist = []
    x_prev, v_prev = x, v
    n = int(t_end / hh)
    rec_every = max(1, int(1e-3 / hh))
    for i in range(n):
        t = i * hh
        locked = t >= t_lock
        if not locked:
            f_spr = st["kn"] * x
        elif scheme in ("ref", "E0"):
            f_spr = law.force(x)
        elif scheme in ("E1", "P"):
            xe = x_prev if scheme == "E1" else x_prev + hh * v_prev
            # SMC part (head only, explicit at x_n) + special part lagged/predicted
            f_spr = st["kn"] * x + (law.force(xe) - st["kn"] * xe) if law.force(xe) > 0 else 0.0
            f_spr = max(f_spr, 0.0)
        elif scheme == "naive":
            f_spr = max(st["kn"] * x + st["dk"] * min(x, law.d_fl), 0.0)
        else:
            raise ValueError(scheme)
        f_damp = c * v if f_spr > 0 else 0.0
        a = (f_ext(t) - f_spr - f_damp) / m
        x_prev, v_prev = x, v
        v = v + hh * a
        x = x + hh * v
        if i % rec_every == 0:
            hist.append((t, x, f_spr))
    arr = np.array(hist)
    return {"leg": leg, "scheme": scheme, "h": h, "lock_from": lock_from, "t": arr[:, 0].tolist(),
            "x": arr[:, 1].tolist(), "F": arr[:, 2].tolist()}


def compare(results):
    ref = {(r["leg"], r["lock_from"]): r for r in results if r["scheme"] == "ref"}
    out = []
    for r in results:
        if r["scheme"] == "ref":
            continue
        rf = ref[(r["leg"], r["lock_from"])]
        n = min(len(r["F"]), len(rf["F"]))
        F, Fr = np.array(r["F"][:n]), np.array(rf["F"][:n])
        t = np.array(r["t"][:n])
        d = F - Fr
        w_lock = (t >= 0.049) & (t <= 0.1)
        w_knee = (t >= 0.25) & (t <= 0.35)
        w_lift = (t >= 0.85) & (t <= 1.25)
        lift_t = t[np.argmax(F <= 0)] if np.any(F <= 0) else None
        lift_tr = t[np.argmax(Fr <= 0)] if np.any(Fr <= 0) else None
        out.append({"leg": r["leg"], "lock_from": r["lock_from"], "scheme": r["scheme"], "h": r["h"],
                    "max_abs_dF_kN": float(np.max(np.abs(d)) / 1e3),
                    "max_abs_dF_lock_window_kN": float(np.max(np.abs(d[w_lock])) / 1e3),
                    "max_abs_dF_knee_window_kN": float(np.max(np.abs(d[w_knee])) / 1e3),
                    "max_abs_dF_liftoff_window_kN": float(np.max(np.abs(d[w_lift])) / 1e3),
                    "peak_F_kN": float(F.max() / 1e3), "peak_F_ref_kN": float(Fr.max() / 1e3),
                    "liftoff_t": lift_t, "liftoff_t_ref": lift_tr})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[2] / "06_analysis" / "03_hydraulic")
    args = ap.parse_args()
    res = {}
    # 1. parameters
    par = {}
    for leg in ("front", "rear"):
        rows = []
        for e in (0.10, 0.20, 0.30, GEOM[leg][2], 0.50, 0.60, 0.68):
            for l0r in (0.02, 0.05, 0.2, 0.6):
                s = stiff(leg, e=e, l0r=l0r)
                rows.append({k: s[k] for k in ("e", "k_h", "k_r", "r", "kn", "kn_rod", "dk", "q_lag")} | {"L0r": l0r})
        for beta in (0.69e9, 1.6e9):
            s = stiff(leg, beta=beta)
            rows.append({k: s[k] for k in ("e", "k_h", "k_r", "r", "kn", "kn_rod", "dk", "q_lag")} | {"L0r": L0R, "beta": beta})
        s = stiff(leg)
        dp_k = ALPHA / (1 / BETA + s["A_ann"] / (s["L_r"] * (s["k_h"] + S_SUPPORT)))
        par[leg] = {"rows": rows, "nominal": s, "p_r0_EXT_bar": P_R0_EXT / BAR,
                    "p_r0_RET_static_bar": p_r_retract_threshold(leg, F_STATIC[leg]) / BAR,
                    "thermal_bar_per_K": dp_k / BAR, "m_rod_kg": M_ROD[leg]}
    res["parameters"] = par
    # 2. reference cases
    res["reference_cases"] = reference_cases()
    # 3. damping
    res["damping"] = damping_table()
    # 4. time sims in parallel
    jobs = []
    for leg in ("front", "rear"):
        for lock_from in ("EXT", "RET"):
            jobs.append((leg, "ref", 1e-6, lock_from))
            for h in (2e-4, 1e-4):
                for sch in ("E0", "E1", "P", "naive"):
                    jobs.append((leg, sch, h, lock_from))
    with ProcessPoolExecutor() as ex:
        results = list(ex.map(sim_case, jobs))
    res["transition_sims"] = compare(results)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "l1r_rod_spring_spec.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    # console
    for leg, p in par.items():
        n = p["nominal"]
        print(leg, {k: round(v, 5) if isinstance(v, float) else v for k, v in n.items()},
              "p_r0_RET", round(p["p_r0_RET_static_bar"], 2), "thermal", round(p["thermal_bar_per_K"], 3))
        for r in p["rows"]:
            if r["L0r"] in (0.05,) and "beta" not in r:
                print(f"   e {r['e']:.4f} k_h {r['k_h']:.4e} k_r {r['k_r']:.4e} r {r['r']:.3f} "
                      f"kn {r['kn']:.4e} kn_rod {r['kn_rod']:.4e} dk {r['dk']:.4e}")
    for r in res["reference_cases"]:
        print(f"REF {r['leg']:5s} {r['lock_from']} F_lock {r['F_lock_kN']:.2f} p_r0 {r['p_r0_bar']:.2f} dF {r['dF_pad_kN']:+.2f}"
              f" -> state {r['state']:5s} d {r['delta_minus_lock_mm']:+.4f} mm p_r {r['p_r_bar_linear']:.3f}"
              f" (log {r['p_r_bar_exact_log']:.3f}) k {r['k_pad_N_m']:.4e} F_fl {r['F_floor_kN']:.2f}")
    for r in res["damping"]:
        if r["impl"].startswith("(i)"):
            print(f"DAMP {r['impl'][:3]} {r['leg']:5s} {r['mode']:8s} h {r['h']:.0e} {r['scheme']:2s}"
                  f" zeta {r['zeta_disc']:.5f} dz {r['dzeta_vs_all_explicit']:+.6f} ({r['dzeta_pct_of_phys']:+.1f} %)")
        else:
            print(f"DAMP {r['impl'][:4]} {r['leg']:5s} {r['mode']:8s} h {r['h']:.0e} {r['scheme']:2s}"
                  f" zeta {r['zeta_disc']:.4f} dz {r['dzeta_vs_phys']:+.4f}"
                  f" f {r['f_Hz']:.1f}/{r['f_cont_Hz']:.1f} wh {r['w_h']:.3f}")
    for r in res["transition_sims"]:
        print(f"SIM {r['leg']:5s} {r['lock_from']} {r['scheme']:5s} h {r['h']:.0e} max dF {r['max_abs_dF_kN']:.3f}"
              f" lock {r['max_abs_dF_lock_window_kN']:.3f} knee {r['max_abs_dF_knee_window_kN']:.3f}"
              f" lift {r['max_abs_dF_liftoff_window_kN']:.3f} kN, liftoff {r['liftoff_t']} vs {r['liftoff_t_ref']}")


if __name__ == "__main__":
    main()
