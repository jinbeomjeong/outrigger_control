"""10 Hz valve command / 10 Hz instantaneous pressure sampling: hydraulic-side estimates.

(a) ZOH 100 ms velocity-command steps through a first-order valve (tau_v) into a per-leg
    heave SDOF (f_h 7.4 Hz, zeta 0.03 / 0.1, velocity source = pressure-compensated flow):
    dynamic force = m_eff * x'' (deviation from the quasi-static load).
    Hose water hammer between MCV and PO check (Joukowsky with closure-time reduction).
(b)/(c) Worst-case under-read of a decaying ringing peak by a 10 Hz instantaneous sampler
    (all grid phases), and alias frequencies of the modes.

SI internally; pressures reported in bar (gauge differences). Assumptions are listed in the
JSON 'assumptions' block.
Run: conda run -n hydraulics-dev python -I ctrl10hz_check.py <out.json>
(result of record: 06_analysis/03_hydraulic/ctrl10hz_hydraulic_check.json, rod_side_pressure.md 18)

Archived 2026-10-25 unchanged from the 2026-10-22 session scratchpad (hyd-run/l1r_drop).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

V_MAX = 0.020924
F_H = 7.4
TS = 0.1
LEGS = {
    # head area, annulus area, head-only moving stiffness k_n (YAML kn_per_pad_N_m), r share
    "front": {"A_p": math.pi / 4 * 0.130**2, "A_ann": math.pi / 4 * (0.130**2 - 0.110**2),
              "k": 25905744.2, "r": 0.269},
    "rear": {"A_p": math.pi / 4 * 0.110**2, "A_ann": math.pi / 4 * (0.110**2 - 0.090**2),
             "k": 19504614.9, "r": 0.289},
}


def simulate(k: float, zeta: float, tau_v: float, u_steps: np.ndarray, dt: float = 1e-4,
             t_tail: float = 1.5) -> tuple[np.ndarray, np.ndarray]:
    """u_steps: command per 100 ms frame (ZOH). Returns t, dynamic force m x''."""
    w = 2 * math.pi * F_H
    m = k / w**2
    c = 2 * zeta * math.sqrt(k * m)
    n_frames = len(u_steps)
    n = int((n_frames * TS + t_tail) / dt)
    s = x = v = 0.0
    u_act = 0.0
    t = np.arange(n) * dt
    f = np.empty(n)
    for i in range(n):
        frame = min(int(t[i] / TS), n_frames - 1) if t[i] < n_frames * TS else n_frames - 1
        u_cmd = u_steps[frame]
        if tau_v > 0:
            u_act += (u_cmd - u_act) * (1 - math.exp(-dt / tau_v))
        else:
            u_act = u_cmd
        s += u_act * dt
        fs = k * (s - x) + c * (u_act - v)
        a = fs / m
        v += a * dt
        x += v * dt
        f[i] = fs
    return t, f


def ringing_underread(f_mode: float, zeta: float, n_phase: int = 400) -> dict:
    """Decaying ringing A e^{-zeta w t} cos(w_d t) from t = 0 (peak at t = 0, amplitude 1).
    10 Hz sampler with grid phase phi in [0, TS): best sample value vs true peak 1."""
    w = 2 * math.pi * f_mode
    wd = w * math.sqrt(1 - zeta**2)
    worst_best = 1.0
    worst_first = 1.0
    for j in range(n_phase):
        t0 = TS * j / n_phase
        ts = t0 + TS * np.arange(0, 30)
        y = np.exp(-zeta * w * ts) * np.cos(wd * ts)
        worst_best = min(worst_best, float(y.max()))
        worst_first = min(worst_first, float(y[0]))
    alias = abs(f_mode - round(f_mode / (1 / TS)) * (1 / TS))
    return {"f_Hz": f_mode, "zeta": zeta, "alias_Hz": alias,
            "worst_best_sample_of_peak": worst_best,
            "worst_first_sample": worst_first,
            "amplitude_left_after_100ms": math.exp(-zeta * w * TS),
            "amplitude_left_after_300ms": math.exp(-zeta * w * 3 * TS)}


def main() -> None:
    out = Path(sys.argv[1])
    res: dict = {"assumptions": {
        "valve": "first-order velocity lag tau_v 0 (ideal) / 0.02 / 0.05 / 0.1 / 0.15 s; "
                 "0.15 s ~ bench step 90 % 0.31-0.39 s (unit_test_noload_analysis.md)",
        "plant": "per-leg heave SDOF f 7.4 Hz, m_eff = k_n / w^2, zeta 0.03 (locked) / 0.1 "
                 "(moving); single-leg steps also excite rocking / twist (not modelled)",
        "hose": "3/8 in (ID 9.5 mm), 4 m, effective beta 0.5 GPa, rho 870 kg/m3",
    }, "a": {}, "hammer": {}, "ringing": {}}
    cases = {
        "start_0_to_vmax": np.array([V_MAX] * 10),
        "stop_vmax_to_0": np.array([V_MAX] * 10 + [0.0] * 10),
        "step_0.1vmax": np.array([0.1 * V_MAX] * 10),
        "alternate_pm0.1vmax_5Hz": np.array([0.1 * V_MAX, -0.1 * V_MAX] * 15),
        "staircase_ramp_1s": np.array([V_MAX * min(1.0, (i + 1) / 10) for i in range(20)]),
    }
    for leg, p in LEGS.items():
        for tau in (0.0, 0.02, 0.05, 0.1, 0.15):
            for zeta in (0.03, 0.1):
                for name, u in cases.items():
                    t, f = simulate(p["k"], zeta, tau, u)
                    if name == "stop_vmax_to_0":
                        f = f[t >= 1.0]  # after the start transient (frame 10)
                    elif name == "alternate_pm0.1vmax_5Hz":
                        f = f[(t >= 2.0) & (t < 3.0)]  # steady periodic
                    peak = float(np.max(np.abs(f)))
                    key = f"{leg}_tau{tau}_zeta{zeta}_{name}"
                    res["a"][key] = {
                        "dF_peak_kN": peak / 1e3,
                        "dp_head_bar_moving": peak / p["A_p"] / 1e5,
                        "dp_head_bar_locked": (1 - p["r"]) * peak / p["A_p"] / 1e5,
                    }
        # hose water hammer on closing (line MCV <-> POC), extension at v_max
        q = p["A_p"] * V_MAX
        area = math.pi / 4 * 0.0095**2
        u_fl = q / area
        a_wave = math.sqrt(0.5e9 / 870.0)
        dp_j = 870.0 * a_wave * u_fl
        t_ref = 2 * 4.0 / a_wave
        res["hammer"][leg] = {"Q_L_min": q * 6e4, "u_m_s": u_fl, "a_m_s": a_wave,
                              "dp_joukowsky_bar": dp_j / 1e5, "2L_over_a_ms": t_ref * 1e3}
        for tau in (0.02, 0.05, 0.1, 0.15):
            t_close = 2.3 * tau  # 10-90 %
            res["hammer"][leg][f"dp_bar_tau{tau}"] = dp_j / 1e5 * min(1.0, t_ref / t_close)
    for f_mode, zeta in ((7.4, 0.03), (7.4, 0.1), (6.6, 0.03), (8.2, 0.03), (1.8, 0.007),
                         (102.4, 0.03), (102.4, 0.1), (102.4, 0.3), (85.0, 0.1), (130.0, 0.1),
                         (247.0, 0.3), (289.0, 0.3)):
        res["ringing"][f"{f_mode}Hz_zeta{zeta}"] = ringing_underread(f_mode, zeta)
    out.write_text(json.dumps(res, indent=1))
    # compact print
    for k_, v_ in res["a"].items():
        if "zeta0.03" in k_ or "alternate" in k_:
            print(k_, {kk: round(vv, 2) for kk, vv in v_.items()})
    print(json.dumps(res["hammer"], indent=1))
    print(json.dumps(res["ringing"], indent=1))


if __name__ == "__main__":
    main()
