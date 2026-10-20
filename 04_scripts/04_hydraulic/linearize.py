"""Linear L2 plant data for control-expert / dynamics-expert (spec 8) and the discrete-coupling
stability map (spec 5).

Outputs 06_analysis/03_hydraulic/l2_linear_plant.json:
  A  k_oil(e) per leg geometry: head only, + rod side (pressurised), beta and L0 sensitivity
  B  single-leg locked / moving state space (physical topology), transfer functions and frequency
     response samples; hydraulic natural frequency (analytic) for every leg and auger level mass
  C  per-leg hydraulic element for the multi-leg models (inputs u_v, link velocity; output F)
  D  discrete coupling map: numerical damping / stability of a stiff force law applied through a
     Python hook with 0 or 1 step lag (and with the lag predictor), as a function of omega dt

Run (conda hydraulics-dev): python -I 04_scripts/04_hydraulic/linearize.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import control as ct
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_params as lp  # noqa: E402

OUT = lp.OUT_DIR / "l2_linear_plant.json"
LEGS = ("FL", "FR", "RL", "RR")


def k_oil_table() -> dict:
    y = lp.load_yaml()
    act = y["actuator"]
    D, d = act["bore_diameter_m"], act["rod_diameter_m"]
    A_A = math.pi / 4 * D ** 2
    A_B = math.pi / 4 * (D ** 2 - d ** 2)
    stroke = act["stroke_m"]
    e = np.round(np.linspace(0.0, stroke, 18), 4)
    out = {"e_m": e.tolist(), "A_A_m2": A_A, "A_B_m2": A_B, "cases": {}}
    for beta in (0.69e9, 1.0e9, 1.6e9):
        for L0 in (0.0, 0.05, 0.15):
            if L0 == 0.0:
                kA = [beta * A_A / max(x, 1e-3) for x in e]   # e = 0 with no dead volume is singular
            else:
                kA = [beta * A_A / (L0 + x) for x in e]
            kB = [beta * A_B / (stroke - x + L0) if (stroke - x + L0) > 1e-3 else float("nan") for x in e]
            out["cases"][f"beta_{beta / 1e9:.2f}GPa_L0_{L0:.2f}m"] = {
                "k_oil_head_N_m": kA, "k_oil_rod_side_pressurised_N_m": kB}
    out["note"] = ("k_oil = beta A^2 / V; head: V = A_A (L0 + e); rod side (only if the trapped rod "
                   "chamber is pressurised; at 2 bar g it cavitates after about 0.1 mm of push-in, spec 3.2): "
                   "V = A_B (stroke - e + L0). L0 = 0 at e = 0 is clipped at 1 mm.")
    return out


def single_leg_ss(leg: str = "FL", moving: bool = False, level: str = "top") -> tuple[ct.StateSpace, dict]:
    """Physical topology: states [xM, vM, xr, vr, pA_g]; inputs [q_head, F_D2]; outputs
    [pA_g, F_sensor, s - s0, xM, F_ground]. Head chamber only (rod side ~ tank pressure)."""
    prm, c = lp.build(leg=leg)
    y = lp.load_yaml()
    F0 = float(y["superstructure"]["auger_levels"][level]["static_leg_loads_N"][leg])
    M = F0 / c["g"]
    A = c["A_A"]
    V = prm.geometry.dead_volume_head_m3 + A * c["s0"]
    beta = prm.fluid.beta_L_Pa
    ch = c["c_h_moving"] if moving else c["c_h_locked"]
    kg, mr = c["k_g"], c["m_r"]
    kh = beta / V  # dp/dV
    # s = xM - xr ; sdot = vM - vr ; F_cyl = A pA - ch sdot
    Am = np.array([
        [0, 1, 0, 0, 0],
        [0, -ch / M, 0, ch / M, A / M],
        [0, 0, 0, 1, 0],
        [0, ch / mr, -kg / mr, -ch / mr, -A / mr],
        [0, -kh * A, 0, kh * A, 0],
    ])
    Bm = np.array([[0, 0], [0, -1 / M], [0, 0], [0, 0], [kh, 0]])
    Cm = np.array([
        [0, 0, 0, 0, 1],
        [0, 0, 0, 0, A],
        [1, 0, -1, 0, 0],
        [1, 0, 0, 0, 0],
        [0, 0, -kg, 0, 0],
    ])
    sys_ = ct.ss(Am, Bm, Cm, np.zeros((5, 2)),
                 inputs=["q_head", "F_D2"], outputs=["pA_g", "F_sensor", "ds", "xM", "dF_ground"],
                 states=["xM", "vM", "xr", "vr", "pA_g"])
    k_oil = beta * A ** 2 / V
    k_ax = 1 / (1 / k_oil + 1 / kg)
    wn = math.sqrt(k_ax / M)
    info = {"leg": leg, "level": level, "moving": moving, "M_kg": M, "m_rod_kg": mr, "V_A_m3": V,
            "beta_Pa": beta, "c_h_N_s_m": ch, "k_oil_N_m": k_oil, "k_g_N_m": kg, "k_ax_N_m": k_ax,
            "f_h_analytic_Hz": wn / (2 * math.pi),
            "zeta_analytic": ch * (kg / (kg + k_oil)) ** 2 / (2 * math.sqrt(k_ax * M)),
            "f_rod_local_Hz": math.sqrt((k_oil + kg) / mr) / (2 * math.pi)}
    return sys_, info


def modes(sys_: ct.StateSpace) -> list:
    ev = np.linalg.eigvals(sys_.A)
    out = []
    for lam in sorted(ev, key=lambda z: abs(z)):
        if lam.imag > 0:
            out.append({"f_n_Hz": abs(lam) / (2 * math.pi), "f_d_Hz": lam.imag / (2 * math.pi),
                        "zeta": -lam.real / abs(lam)})
    return out


def freq_samples(sys_: ct.StateSpace, inp: int, outp: int, freqs) -> dict:
    w = 2 * np.pi * np.asarray(freqs)
    resp = ct.frequency_response(sys_[outp, inp], w)
    mag = np.abs(resp.complex).ravel()
    ph = np.degrees(np.unwrap(np.angle(resp.complex).ravel()))
    return {"f_Hz": list(freqs), "mag": mag.tolist(), "phase_deg": ph.tolist()}


def discrete_map(omega_h: float, zeta: float, lag: int, predict: bool) -> tuple[float, float, float]:
    """1-DOF m x'' = -k x - c x' with the force from a hook (semi-implicit Euler + lag).

    Returns (zeta_discrete, f_ratio = f_disc/f_cont, spectral radius). Unit mass, omega = 1, h = omega_h.
    State z_n = [x_n, v_n, x_{n-1}, v_{n-1}, ...]; force applied in step n+1 = f(x_{n-lag}, v_{n-lag})
    (predictor: x_{n-lag} + lag h v_{n-lag}).
    """
    h = omega_h
    k, c = 1.0, 2 * zeta
    n = 2 * (lag + 1)
    T = np.zeros((n, n))
    # force row (as a function of the delayed state)
    j = 2 * lag
    fx, fv = -k, -c
    if predict and lag > 0:
        fv = fv - k * lag * h
    # v_{n+1} = v_n + h (fx x_{n-lag} + fv v_{n-lag}); x_{n+1} = x_n + h v_{n+1}
    T[1, 1] = 1.0
    T[1, j] += h * fx
    T[1, j + 1] += h * fv
    T[0, 0] = 1.0
    T[0, :] += h * T[1, :]
    for i in range(2, n):
        T[i, i - 2] = 1.0
    ev = np.linalg.eigvals(T)
    # physical pair: the one closest to exp(i h)
    target = np.exp(complex(-zeta * h, h * math.sqrt(max(1 - zeta ** 2, 0.0))))
    lam = ev[np.argmin(np.abs(ev - target))]
    s = np.log(lam) / h
    zd = -s.real / abs(s)
    return float(zd), float(abs(s.imag)), float(np.max(np.abs(ev)))


def lag_table() -> dict:
    modes_hz = {"rocking_1": 1.80, "rocking_2": 3.00, "heave_single_leg": 6.61, "heave_L1": 7.39,
                "rod_on_axial_spring_L2b_NSC": 70.6, "rod_airborne_e0": 194.0,
                "rod_local_single_leg": 239.0, "rod_local_L2_SMC": 286.6}
    out = {"modes_Hz": modes_hz, "rows": []}
    for dt in (1e-4, 5e-5, 1e-5):
        for name, f in modes_hz.items():
            wh = 2 * math.pi * f * dt
            for zeta in (0.0, 0.03):
                row = {"dt_s": dt, "mode": name, "f_Hz": f, "omega_dt": wh, "zeta_phys": zeta}
                for tag, lag, pred in (("lag0", 0, False), ("lag1", 1, False), ("lag1_pred", 1, True)):
                    zd, fr, rho = discrete_map(wh, zeta, lag, pred)
                    row[f"zeta_{tag}"] = zd
                    row[f"dzeta_{tag}"] = zd - zeta
                    row[f"f_ratio_{tag}"] = fr / math.sqrt(1 - zeta ** 2)
                    row[f"stable_{tag}"] = rho <= 1.0 + 1e-12
                out["rows"].append(row)
    # stability limits (zeta = 0.03): largest omega dt that is stable
    lim = {}
    for tag, lag, pred in (("lag0", 0, False), ("lag1", 1, False), ("lag1_pred", 1, True)):
        for zeta in (0.0, 0.03, 0.1, 0.3):
            lo, hi = 1e-4, 4.0
            if discrete_map(lo, zeta, lag, pred)[2] > 1 + 1e-12:
                lim[f"{tag}_zeta{zeta}"] = 0.0
                continue
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                if discrete_map(mid, zeta, lag, pred)[2] <= 1 + 1e-12:
                    lo = mid
                else:
                    hi = mid
            lim[f"{tag}_zeta{zeta}"] = lo
    out["stable_omega_dt_limit"] = lim
    out["note"] = ("semi-implicit Euler with the actuator force from a post-step hook. lag0 = force from "
                   "the state at the end of the previous step (textbook symplectic Euler); lag1 = the "
                   "pychrono hook delay of dynamics_model.md 4.6 (force set after step n acts in step "
                   "n+2); lag1_pred = force evaluated at x + h v (spec 5.3). zeta_* = discrete-map "
                   "damping of the physical pair; dzeta = numerical damping (negative = energy added).")
    return out


def main() -> None:
    res = {"meta": {"script": "04_scripts/04_hydraulic/linearize.py", "env": "conda hydraulics-dev",
                    "control_version": ct.__version__, "date": "2026-10-20",
                    "pressure": "gauge (linear, deviations from the static point)",
                    "units": "SI: m, m/s, Pa, N, m^3/s, s"}}
    res["A_k_oil"] = k_oil_table()
    B = {}
    freqs = [0.05, 0.1, 0.2, 0.32, 0.5, 1.0, 2.0, 5.0, 6.6, 10.0, 20.0]
    for leg in LEGS:
        for level in ("top", "middle", "bottom"):
            for moving in (False, True):
                s_, info = single_leg_ss(leg, moving, level)
                key = f"{leg}_{level}_{'moving' if moving else 'locked'}"
                entry = {"info": info, "modes": modes(s_)}
                if leg == "FL" and level == "top":
                    entry["A"] = s_.A.tolist()
                    entry["B"] = s_.B.tolist()
                    entry["C"] = s_.C.tolist()
                    entry["D"] = s_.D.tolist()
                    entry["inputs"] = s_.input_labels
                    entry["outputs"] = s_.output_labels
                    entry["states"] = s_.state_labels
                    # the oil amount is a pure integrator of q (one zero eigenvalue): evaluate the
                    # disturbance gains at 1e-6 Hz instead of s = 0
                    s_lo = 2j * math.pi * 1e-6
                    entry["dc_gain"] = {
                        "dpA_dFD2_Pa_per_N": float(np.real(s_[0, 1](s_lo))),
                        "ds_dFD2_m_per_N": float(np.real(s_[2, 1](s_lo))),
                        "dxM_dFD2_m_per_N": float(np.real(s_[3, 1](s_lo))),
                        "dpA_dq_Pa_per_m3_s_steady_motion": float(np.real(s_[0, 0](s_lo))),
                        "note": "q -> s, xM is an integrator (velocity A^-1 per m^3/s); q -> p_A steady "
                                "value = c_h / A_A^2 (dashpot pressure while moving)",
                    }
                    entry["freq_F_D2_to_pA"] = freq_samples(s_, 1, 0, freqs)
                    # velocity-command input: q = A_A u  ->  s/u has an integrator; give pA/u
                    entry["freq_q_to_pA"] = freq_samples(s_, 0, 0, freqs)
                    entry["freq_q_to_ds"] = freq_samples(s_, 0, 2, freqs)
                B[key] = entry
    res["B_single_leg"] = B
    res["C_leg_element"] = {
        "description": "per-leg hydraulic element for multi-leg linear models (locked or moving)",
        "states": ["p_A_g (head chamber gauge pressure)"],
        "inputs": ["u_v: section velocity command after the ramp [m/s] (q = A_A u_v)",
                   "s_dot: piston velocity relative to the barrel [m/s]"],
        "outputs": ["F: actuator force on the rod chain [N] = A_A p_A - c_h s_dot"],
        "equations": "dp_A/dt = beta/V_A(e) (A_A u_v - A_A s_dot);  F = A_A p_A - c_h s_dot",
        "equivalent": "F = k_oil(e) (s_ref - s) + c_h (s_ref_dot - s_dot) with s_ref = int u_v dt, "
                      "k_oil(e) = beta A_A / (L0 + e)  (identical to the L2 force law of dynamics_model.md 2.3)",
        "ramp": "u_v = rate_limit(u, v_max / T_ramp) (nonlinear; T_ramp 0.1 s, rate 0.2267 m/s^2)",
        "c_h": "c_h = c_ax_YAML (1 + k_oil/k_g)^2 when the dashpot sits across the oil only (spec 3.5)",
    }
    res["D_lag_map"] = lag_table()
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")
    b = B["FL_top_locked"]
    print("FL top locked:", json.dumps(b["info"], indent=0)[:900])
    print("modes:", b["modes"])
    print("lag limits:", res["D_lag_map"]["stable_omega_dt_limit"])


if __name__ == "__main__":
    main()
