"""V9 (a) record rule: first-order dt convergence of the S7 L2b force laws on a numpy replica.

dynamics_model.md rev. 35, 5.22.3 (user decision 2026-10-24 after the V9 (b) runs: the Chrono
error ratio is dominated by PSOR noise, so the ratio is recorded and the order of the explicit
axial / lateral laws is shown on a replica of the same time discretisation).

Replica (linear, about the settled pose, top level): superstructure 6 DoF about its CoM; rods on
the rigid NSC contact (fixed). Axial law per leg (vertical at the pad xy): FL moving k2(e_op) +
c_mov, the other legs LOCK k1(e_op) = series(k_h + k_r, k_out) + c_lock (l2b_reference.leg_parameters);
lateral spring kt + ct (x, y) at the pad contact point. Input: FL s_ref ramp of the V9 case
(+1 mm at 0.5 mm/s, command ramp 0.1 s to the speed and back, YAML actuator.command_ramp_s),
then hold. Time stepping as Chrono EULER_IMPLICIT_LINEARIZED for explicit force laws: semi-
implicit Euler v+ = v + dt M^-1 f(q, v, u_lag), q+ = q + dt v+, with the law input s_ref one step
late (hook inputs lag one step, run_S7 input_lag_steps 1). Output = law force F_RL sampled every
1 ms, the judge metric = min of the 20-sample centred mean minus the first-50 ms mean.
Reference: the same scheme at dt 1e-6 s and Richardson (p = 1) from 2e-6 / 1e-6 s.

Units SI. Output 06_analysis/00_dynamics/v9_semi_implicit_replica.json.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numba
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402
import l2b_reference as l2b  # noqa: E402

DTS = (1.0e-4, 5.0e-5, 2.5e-5, 1.0e-5, 5.0e-6, 2.0e-6, 1.0e-6)
T_END = 6.0           # s: 0.2 s still + 2.1 s move + settle (transient extreme inside)
T_START = 0.2
DELTA = 1.0e-3
SPEED = 5.0e-4
SAMPLE = 1.0e-3
WINDOW = 20
BASE_S = 0.05
MOVING, TEST = 0, 2   # FL moves, RL force is the metric (as judge_S7 V9)


def matrices():
    p = dm.load_params()
    geo = dm.geometry_from_params(p)
    lp = l2b.leg_parameters(p, geo)
    body = dm.body_from_params(p, "top")
    e = np.full(4, lp["e_op"]) if np.ndim(lp["e_op"]) == 0 else np.asarray(lp["e_op"], float)
    k_h, k_r = lp["k_h_f"](e), lp["k_r_f"](e)
    k1 = dm.series(k_h + k_r, lp["k_out"])
    k2 = dm.series(k_h, lp["k_out"])
    kv = k1.copy(); kv[MOVING] = k2[MOVING]
    cv = np.array(lp["c_lock"], float).copy(); cv[MOVING] = np.asarray(lp["c_mov"], float)[MOVING]
    kt = np.broadcast_to(np.asarray(lp["kt"], float), (4,))
    ct = np.broadcast_to(np.asarray(lp["ct"], float), (4,))
    z_pad = geo.pad_z_retracted - e
    az = np.zeros((4, 6))
    K = np.zeros((6, 6)); C = np.zeros((6, 6))
    for i in range(4):
        d = np.array([*geo.pad_xy[i], z_pad[i]]) - body.com
        ax, ay, a_z = dm.a_vec(d)
        az[i] = a_z
        K += kv[i] * np.outer(a_z, a_z) + kt[i] * (np.outer(ax, ax) + np.outer(ay, ay))
        C += cv[i] * np.outer(a_z, a_z) + ct[i] * (np.outer(ax, ax) + np.outer(ay, ay))
    M = dm.mass_6dof(body)
    info = {"k_axial_N_m": kv.tolist(), "c_axial_N_s_m": cv.tolist(), "kt_N_m": kt.tolist(),
            "ct_N_s_m": ct.tolist(), "e_op_m": e.tolist(),
            "command_ramp_s": float(p["actuator"]["command_ramp_s"])}
    return M, K, C, az, kv, cv, info


def s_ref_rate(t, ramp):
    """FL s_ref rate: trapezoid 0 -> SPEED in ramp, hold, -> 0 in ramp; travel DELTA."""
    t_move = DELTA / SPEED  # travel time at full speed incl. half ramps on each side
    tau = t - T_START
    if tau <= 0.0 or tau >= t_move + ramp:
        return 0.0
    if tau < ramp:
        return SPEED * tau / ramp
    if tau > t_move:
        return SPEED * (t_move + ramp - tau) / ramp
    return SPEED


@numba.njit(cache=False)
def integrate(Minv, K, C, az, kv, cv, rate, dt, n_steps, every, i_test):
    q = np.zeros(6); v = np.zeros(6)
    s = 0.0; s_lag = 0.0; r_lag = 0.0
    out = np.empty(n_steps // every + 1)
    j = 0
    for n in range(n_steps):
        # law input one step late
        F_in = np.zeros(6)
        F_in += az[0] * (kv[0] * s_lag + cv[0] * r_lag)
        f = -K @ q - C @ v + F_in
        if n % every == 0:
            # law force of the test leg (compression +), from the state used in this step
            out[j] = -(kv[i_test] * (az[i_test] @ q) + cv[i_test] * (az[i_test] @ v))
            j += 1
        v = v + dt * (Minv @ f)
        q = q + dt * v
        s_lag = s; r_lag = rate[n]
        s = s + dt * rate[n]
    return out[:j]


def metric(y):
    c = np.cumsum(np.concatenate([[0.0], y]))
    m = (c[WINDOW:] - c[:-WINDOW]) / WINDOW
    base = y[: int(round(BASE_S / SAMPLE))].mean()
    return float((m - base).min())


def main():
    M, K, C, az, kv, cv, info = matrices()
    Minv = np.linalg.inv(M)
    ramp = info["command_ramp_s"]
    res = {"method": " ".join(__doc__.split("\n\n")[1].split()), "parameters": info, "runs": {}}
    vals = {}
    for dt in DTS:
        n = int(round(T_END / dt))
        every = int(round(SAMPLE / dt))
        t = np.arange(n) * dt
        rate = np.array([s_ref_rate(x, ramp) for x in t])
        t0 = time.perf_counter()
        y = integrate(Minv, K, C, az, kv, cv, rate, dt, n, every, TEST)
        vals[dt] = metric(y)
        res["runs"][f"{dt:g}"] = {"transient_RL_dF_min_N": vals[dt],
                                  "final_RL_dF_N": float(y[-200:].mean() - y[:50].mean()),
                                  "wall_s": round(time.perf_counter() - t0, 2)}
        print(f"dt {dt:g}: {vals[dt]:.6f} N")
    ref = 2 * vals[1e-6] - vals[2e-6]
    err = {f"{d:g}": vals[d] - ref for d in DTS}
    a, b, c = vals[1e-4], vals[5e-5], vals[2.5e-5]
    res["richardson_reference_N"] = ref
    res["error_vs_richardson_N"] = err
    res["error_ratio (1e-4/5e-5/2.5e-5)"] = (a - b) / (b - c)
    res["error_ratio (5e-5/2.5e-5/1.25e-5 via err)"] = err["5e-05"] / err["2.5e-05"]
    res["error_vs_1e-5_N"] = {f"{d:g}": vals[d] - vals[1e-5] for d in (1e-4, 5e-5, 2.5e-5)}
    print(json.dumps({k: res[k] for k in res if k.startswith("error")}, indent=1))
    out = ROOT / "06_analysis" / "00_dynamics" / "v9_semi_implicit_replica.json"
    out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print("out:", out)


if __name__ == "__main__":
    main()
