"""D-S8-7 (dynamics_model.md rev. 41): physics of the D1'' IMU residual r = sum F_hat - M_eff f_z_hat.

Body-z Newton equation of the superstructure (crawler lifted, rods excluded; cylinder forces act along the
body z axis, the lateral rod bushings act in body x / y):
    sum_i F_cyl,i = M f_com,z ,   f_IMU,z = f_com,z + (alpha x r)_z + (omega x (omega x r))_z,
r = IMU point (C1, body (0.31, 0.88, 0.04) m) - CoM of the level. F_cyl = rod axial force (oil + seal friction);
the pressure sensors see F_p = F_cyl - f_seal.

Data (ds87_extract.py npz, 1 ms pads record and 10 Hz r8 series): the IMU sub-means 'q_imu' (10 per period,
sub-mean j covers [t_k - 0.1 + 0.01 j, t_k - 0.1 + 0.01 (j + 1)], sensor model included), the 1 ms interval-mean
cylinder force, the 1 ms quaternion (wxyz, body -> world). omega_body from the quaternion (central difference),
mean alpha over a 10 ms window = (omega(end) - omega(start)) / 0.01 s.

Checks:
 (1) Newton / M_eff: least-squares M over all sub-windows (event - 2 .. + 8 s) of
     mean(sum F_cyl) = M [f_imu - mean (alpha x r)_z]; also without the rotation term; M_eff as the D1''
     rule (median sum F_p / f_imu over the pre-event READY periods, truth forces, no pressure-sensor error).
 (2) Decomposition of the one-period change of the D1'' residual at the 10 Hz instants t_k (truth pressure
     force F_p(t_k), IMU last sub-mean):
        r_k = [sum F_cyl(t_k) - mean_last10 sum F_cyl]  (timing: instantaneous sample vs 10 ms mean)
              - sum f_seal(t_k)                          (seal friction)
              - M mean_last10 (alpha x r)_z              (IMU lever arm)
              + (M - M_eff) f_imu + e_imu M_eff          (mass / sensor)
     Distribution of |d term| over the transient periods (event .. event + 5 s) for each term and for |d r|
     with four rule variants: 'spec' (last sub-mean), 'rot' (+ lever-arm correction from the angular rate,
     M_eff (alpha x r)_z with alpha from the last two 10 ms gyro means), 'ext' (last + 0.5 (last - previous)),
     'rot+ext'. Threshold reference 0.5 x 100 bar x A_p: rear 47.5 kN, front 66.4 kN.
Writes 06_analysis/00_dynamics/ds87_imu.json.
Usage: python -I ds87_imu.py <extract_dir> [RUN ...]   (no RUN = all settle episodes in index.json)
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402

P = dm.load_params()
OUT = ROOT / "06_analysis" / "00_dynamics" / "ds87_imu.json"
M_YAML = float(P["superstructure"]["auger_levels"]["top"]["mass_kg"])


def omega_body(t, q):
    """Body angular velocity (body frame) from wxyz quaternions (body -> world), central difference."""
    dq = np.gradient(q, t, axis=0)
    w, x, y, z = q.T
    dw, dx, dy, dz = dq.T
    # 2 * conj(q) (x) dq, vector part
    ox = 2 * (w * dx - x * dw - y * dz + z * dy)
    oy = 2 * (w * dy + x * dz - y * dw - z * dx)
    oz = 2 * (w * dz - x * dy + y * dx - z * dw)
    return np.column_stack([ox, oy, oz])


def stats(v):
    v = np.abs(np.asarray(v))
    if not len(v):
        return None
    return dict(n=int(len(v)), p50=round(float(np.percentile(v, 50)) / 1e3, 2),
                p99=round(float(np.percentile(v, 99)) / 1e3, 2), max=round(float(v.max()) / 1e3, 2))


src = Path(sys.argv[1])
index = json.loads((src / "index.json").read_text(encoding="utf-8"))
runs = sys.argv[2:] or [e["run"] for e in index]
pool = {k: [] for k in ("timing", "seal", "lever", "rest", "dr_spec", "dr_rot", "dr_ext", "dr_rotext", "dr_sum")}
fits = []
per_run = {}
for run in runs:
    z = np.load(src / f"{run}.npz", allow_pickle=True)
    info = json.loads(str(z["info"]))
    t_ev = info["t_ev"]
    lvl = dm.body_from_params(P, info["level"])
    rvec = np.array(info["imu_point"]) - lvl.com
    tp = z["p_t"]
    Fc = z["p_F_cyl_mean_interval"].sum(1)  # mean over each 1 ms interval
    Fc_inst = z["p_F_cyl"].sum(1)
    fs = z["p_f_seal"].sum(1)
    om = omega_body(tp, z["p_body_quat_wxyz"])
    qt, imu = z["q_t"], z["q_imu"][:, :, 2]
    phase = np.array([str(p) for p in z["q_phase"]])
    # (1) sub-window table
    rows = []
    for k, tk in enumerate(qt):
        if tk < tp[0] + 0.12 or tk > tp[-1]:
            continue
        for j in range(10):
            a, b = tk - 0.1 + 0.01 * j, tk - 0.1 + 0.01 * (j + 1)
            w = (tp > a + 1e-6) & (tp <= b + 1e-6)
            if w.sum() < 9:
                continue
            ia, ib = np.searchsorted(tp, a), np.searchsorted(tp, b)
            ib = min(ib, len(tp) - 1)
            alpha = (om[ib] - om[ia]) / (tp[ib] - tp[ia])
            wm = om[w].mean(0)
            lever = np.cross(alpha, rvec)[2] + np.cross(wm, np.cross(wm, rvec))[2]
            rows.append((tk, j, Fc[w].mean(), imu[k, j], lever))
    rows = np.array(rows)
    Fm, fi, lev = rows[:, 2], rows[:, 3], rows[:, 4]
    M_rot = float(np.dot(Fm, fi - lev) / np.dot(fi - lev, fi - lev))
    M_norot = float(np.dot(Fm, fi) / np.dot(fi, fi))
    after = (rows[:, 0] > t_ev) & (rows[:, 0] < t_ev + 5)
    res_rot = Fm - M_rot * (fi - lev)
    res_norot = Fm - M_norot * fi
    # (2) D1'' residual at t_k
    ready = (phase == "ready") & (qt < t_ev - 0.05) & (qt > tp[0] + 0.12)
    kk = [k for k, tk in enumerate(qt) if tp[0] + 0.12 < tk <= tp[-1]]
    tk_arr = qt[kk]
    i_k = np.searchsorted(tp, tk_arr - 1e-6)
    Fp_k = z["p_F_pressure"][i_k].sum(1)
    Fc_k = Fc_inst[i_k]
    last = imu[kk, -1]
    prev = imu[kk, -2]
    M_eff = float(np.median(Fp_k[ready[kk]] / last[ready[kk]])) if ready[kk].any() else M_rot
    # truth terms at t_k
    mean_last = np.array([Fc[(tp > tk - 0.01 + 1e-6) & (tp <= tk + 1e-6)].mean() for tk in tk_arr])
    timing = Fc_k - mean_last
    seal = -fs[i_k]
    lev_last = np.empty(len(kk))
    lev_prev = np.empty(len(kk))
    for n, tk in enumerate(tk_arr):
        ia, ib = np.searchsorted(tp, tk - 0.01), np.searchsorted(tp, tk - 1e-6)
        ip = np.searchsorted(tp, tk - 0.02)
        lev_last[n] = np.cross((om[ib] - om[ia]) / max(tp[ib] - tp[ia], 1e-9), rvec)[2]
        lev_prev[n] = np.cross((om[ia] - om[ip]) / max(tp[ia] - tp[ip], 1e-9), rvec)[2]
    lever_k = -M_rot * lev_last
    r_spec = Fp_k - M_eff * last
    rest = r_spec - timing - seal - lever_k
    # gyro-based lever correction (as a 100 Hz gyro would allow): alpha from the last two 10 ms gyro means
    om_last = np.array([om[(tp > tk - 0.01 + 1e-6) & (tp <= tk + 1e-6)].mean(0) for tk in tk_arr])
    om_prev = np.array([om[(tp > tk - 0.02 + 1e-6) & (tp <= tk - 0.01 + 1e-6)].mean(0) for tk in tk_arr])
    lev_gyro = np.cross((om_last - om_prev) / 0.01, rvec)[:, 2]
    r_rot = Fp_k - M_eff * (last - lev_gyro)
    ext = last + 0.5 * (last - prev)
    r_ext = Fp_k - M_eff * ext
    r_rotext = Fp_k - M_eff * (ext - lev_gyro)
    sum_rule = Fp_k
    trans = (tk_arr > t_ev) & (tk_arr <= t_ev + 5.0)
    d = lambda x: np.diff(x)[trans[1:]]  # noqa: E731
    for key, x in (("timing", timing), ("seal", seal), ("lever", lever_k), ("rest", rest), ("dr_spec", r_spec),
                   ("dr_rot", r_rot), ("dr_ext", r_ext), ("dr_rotext", r_rotext), ("dr_sum", sum_rule)):
        pool[key] += list(d(x))
    pr = dict(M_fit_rot=round(M_rot, 1), M_fit_norot=round(M_norot, 1), M_eff_ready=round(M_eff, 1),
              M_yaml=M_YAML, r_imu_m=np.round(rvec, 3).tolist(),
              newton_resid_rot_kN=stats(res_rot[after]), newton_resid_norot_kN=stats(res_norot[after]),
              d_timing=stats(d(timing)), d_seal=stats(d(seal)), d_lever=stats(d(lever_k)), d_rest=stats(d(rest)),
              dr_spec=stats(d(r_spec)), dr_rot=stats(d(r_rot)), dr_ext=stats(d(r_ext)),
              dr_rotext=stats(d(r_rotext)), d_sum=stats(d(sum_rule)))
    per_run[run] = pr
    fits.append((M_rot, M_norot, M_eff))
    if len(sys.argv) > 2 or run in ("ML00_ep5", "ML08_ep4", "ML10_ep4", "ML11_ep4", "ML17_ep4", "ML18_ep6", "ML21_ep1"):
        print(f"{run:9s} M fit rot {M_rot:8.1f} norot {M_norot:8.1f} ready {M_eff:8.1f} (yaml {M_YAML:.1f})"
              f" | newton resid p99/max rot {pr['newton_resid_rot_kN']['p99']}/{pr['newton_resid_rot_kN']['max']}"
              f" norot {pr['newton_resid_norot_kN']['p99']}/{pr['newton_resid_norot_kN']['max']} kN")
        print(f"          |d| p99/max kN: timing {pr['d_timing']['p99']}/{pr['d_timing']['max']} seal {pr['d_seal']['p99']}/{pr['d_seal']['max']}"
              f" lever {pr['d_lever']['p99']}/{pr['d_lever']['max']} rest {pr['d_rest']['p99']}/{pr['d_rest']['max']}"
              f" | dr spec {pr['dr_spec']['p99']}/{pr['dr_spec']['max']} rot {pr['dr_rot']['p99']}/{pr['dr_rot']['max']}"
              f" ext {pr['dr_ext']['p99']}/{pr['dr_ext']['max']} rot+ext {pr['dr_rotext']['p99']}/{pr['dr_rotext']['max']}"
              f" | d sum {pr['d_sum']['p99']}/{pr['d_sum']['max']}")
fits = np.array(fits)
summary = {k: stats(v) for k, v in pool.items()}
summary["M_fit_rot_range"] = [round(float(fits[:, 0].min()), 1), round(float(fits[:, 0].max()), 1)]
summary["M_fit_norot_range"] = [round(float(fits[:, 1].min()), 1), round(float(fits[:, 1].max()), 1)]
summary["M_eff_ready_range"] = [round(float(fits[:, 2].min()), 1), round(float(fits[:, 2].max()), 1)]
summary["n_runs"] = len(runs)
print("ALL", json.dumps(summary))
OUT.write_text(json.dumps(dict(summary=summary, runs=per_run), indent=1), encoding="utf-8")
print("wrote", OUT)
