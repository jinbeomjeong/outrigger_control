"""Cross-check the closed-form drain (h_s8_5_physical_drain) against a numerical ODE (solve_ivp)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h_s8_5_physical_drain as ph  # noqa: E402

CASES = [
    ("rear", 1.0e9, 0.05, 0.5, 174.0, 0.25, 0.1, 10.0, 1.0, 0.0, 0.0),
    ("front", 0.69e9, 0.10, 0.1, 350.0, 0.05, 0.2, 20.0, 0.5, 1.0, 0.0),
    ("rear", 1.6e9, 0.02, 0.65, 250.0, 1.0, 0.0, 5.0, 1.0, 1.0, 0.0),
    ("rear", 1.0e9, 0.05, 0.3, 324.0, 0.25, 0.05, 10.0, 0.5, 0.0, 143.0),
]


def ode(case: tuple, free: bool, t_eval: np.ndarray) -> np.ndarray:
    leg, beta, l0r, s, p_pre, u_frac, tau_v, dpc, kappa, hose, p_reg = case
    a_p, a_ann = ph.LEGS[leg]
    phi = a_p / a_ann
    v_r = a_ann * (ph.STROKE - s + l0r)
    v_h = a_p * (ph.L0H + s)
    c_ch = (v_r + (v_h / phi**2 if free else 0.0)) / beta
    c_h = hose * ph.HOSE_V / ph.HOSE_BETA
    c = c_ch + c_h
    p0 = (c_ch * p_pre * ph.BAR + c_h * ph.P_T) / c
    u = u_frac * ph.V_MAX
    k = kappa * a_p * u / np.sqrt(dpc * ph.BAR)
    q = a_ann * u if free else 0.0

    def rhs(t: float, p: float) -> float:
        a = 1.0 - np.exp(-t / tau_v) if tau_v > 0 else 1.0
        return (q * a - k * a * np.sqrt(max(p - ph.P_T, 0.0))) / c

    # explicit RK4 on p (independent of the closed form in y = sqrt(p - p_T)), dt 5 us
    dt = 5e-6
    n = int(round(t_eval[-1] / dt))
    p = p0
    t = 0.0
    out_t, out_p = [0.0], [p0]
    for _ in range(n):
        k1 = rhs(t, p)
        k2 = rhs(t + dt / 2, p + dt / 2 * k1)
        k3 = rhs(t + dt / 2, p + dt / 2 * k2)
        k4 = rhs(t + dt, p + dt * k3)
        p = max(p + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4), ph.P_T)
        t += dt
        out_t.append(t)
        out_p.append(p)
    pr = np.interp(t_eval, out_t, out_p)
    if p_reg > 0:
        pr = np.maximum(pr, p_reg * ph.BAR)
    return pr / ph.BAR


def main() -> None:
    t = np.linspace(1e-4, 0.6, 61)
    worst = 0.0
    for case in CASES:
        for free in (True, False):
            prm = ph.build([case], free)
            p_cf = ph.pressure(t[None, :], prm)[0] / ph.BAR
            p_num = ode(case, free, t)
            d = np.max(np.abs(p_cf - p_num))
            worst = max(worst, d)
            print(case[0], case[4], "free" if free else "stuck", f"max |closed - ode| = {d:.4f} bar",
                  f"p(0.1)={np.interp(0.1, t, p_cf):.2f}/{np.interp(0.1, t, p_num):.2f}")
    print(f"worst {worst:.4f} bar")


if __name__ == "__main__":
    main()
