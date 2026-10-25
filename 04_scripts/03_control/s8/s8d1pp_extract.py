"""Rev. 49 (D1'' details, R41-1..3): per-run 10 Hz series for the D1'' head-step rule study.

Read-only on the Chrono records (Chrono-dev python, no Chrono import). Uses the replay helpers of
05_tests/unit/test_two_pressure_d1_imu.py (the inputs the controller's monitor saw: meas.* at the
10 Hz sample, phase of the period before, IMU last 10 ms partial-mean body-z specific force).

Per run it stores (one npz per run in <out_dir>):
  t, head_Pa, rod_Pa, sum_N (sum of net head/rod reading forces, no zero offsets: they cancel in
  one-period differences), f_z (last 10 ms partial mean), f_z_prev (the one before),
  phase (before), band_N (leg band before), commanded,
  lever_true / lever_noisy: (alpha x r)_z [m/s^2] over the last 10 ms partial mean, alpha from the
    difference of the last two 10 ms means of the body angular rate computed from the 1 ms pad
    record quaternion (truth), noisy = + gyro white noise of a 10 ms mean (normal grade ARW
    0.30 deg/sqrt(h) -> sigma 6.17e-4 rad/s per 10 ms mean, ASSUMPTION = sensors/imu.py normal grade),
    NaN where the 1 ms record does not cover the period,
  fseal_sum_N: true sum of seal forces at the sample (1 ms pad record f_seal), NaN if not covered,
  sumFcyl_N: true sum of cylinder forces at the sample,
  seal_limits_N (4), t_ev (NaN if none), batch, run.
Lever arm: (alpha x r)_z = 0.881 alpha_x + 0.150 alpha_y (dynamics_model.md 5.28, all levels).
Seed: numpy default_rng(49) per run index order (sorted).
Usage: python -I s8d1pp_extract.py <project_root> <out_dir> <batch_dir> [<batch_dir> ...]
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
root, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(root / "03_src"))
sys.path.insert(0, str(root / "05_tests" / "unit"))
import test_two_pressure_d1_imu as tools  # noqa: E402

out.mkdir(parents=True, exist_ok=True)
A_P, A_R = tools.HEAD_AREA, tools.ANNULUS
SIGMA_GYRO_10MS = 0.30 * np.pi / 180.0 / 60.0 * np.sqrt(1.0 / (2 * 0.01))
LEVER = np.array([0.881, 0.150])


def omega_body(t, q):
    """Body angular velocity (body frame) from wxyz quaternions (body -> world), central difference."""
    qd = np.gradient(q, t, axis=0)
    w, x, y, z = q.T
    # omega_body = 2 * conj(q) * qdot (vector part)
    dw, dx, dy, dz = qd.T
    ox = 2 * (w * dx - x * dw - y * dz + z * dy)
    oy = 2 * (w * dy + x * dz - y * dw - z * dx)
    oz = 2 * (w * dz - x * dy + y * dx - z * dw)
    return np.column_stack([ox, oy, oz])


def runs(batch: Path):
    for sub in (batch / "bases", batch / "episodes", batch):
        if sub.is_dir():
            for d in sorted(sub.iterdir()):
                if d.is_dir() and not d.name.startswith("_") and (d / "record" / "record.npz").exists() \
                        and (d / "r8_series.npz").exists():
                    yield d


rng = np.random.default_rng(49)
index = []
for b in sys.argv[3:]:
    b = Path(b)
    for d in runs(b):
        target = out / f"{b.name}__{d.name}.npz"
        try:
            inp = tools.run_inputs(d)
        except KeyError as exc:  # pressure-only runs have no leg band / IMU samples
            print("skip", b.name, d.name, exc)
            continue
        with np.load(d / "r8_series.npz") as r8:
            fz_prev = r8["imu_samples"][:, -2, 2]
        t = inp.t_s
        net = inp.head_Pa * A_P - inp.rod_Pa * A_R
        meta = json.loads((d / "record" / "meta.json").read_text(encoding="utf-8"))
        s8 = meta["run"]["engine"]["actuator"].get("s8") or {}
        limits = np.array(((s8.get("seal_friction") or {}).get("limits_N")) or [0.0] * 4, float)
        res = json.loads((d / "result.json").read_text(encoding="utf-8"))
        t_ev = res.get("event_t_s")
        t_ev = float(t_ev) if t_ev is not None else np.nan
        n = t.size
        lev_true = np.full(n, np.nan)
        fseal = np.full(n, np.nan)
        sumF = np.full(n, np.nan)
        if (d / "pads.npz").exists():
            with np.load(d / "pads.npz", allow_pickle=True) as z:
                tp = z["t"]
                q = z["body_quat_wxyz"]
                fs = z["f_seal"].sum(axis=1)
                fc = z["F_cyl"].sum(axis=1)
            om = omega_body(tp, q)
            for k in range(n):
                a, m, e = t[k] - 0.02, t[k] - 0.01, t[k]
                if a < tp[0] + 0.002 or e > tp[-1] + 1e-9:
                    continue
                w1 = (tp > a + 1e-9) & (tp <= m + 1e-9)
                w2 = (tp > m + 1e-9) & (tp <= e + 1e-9)
                if w1.sum() < 5 or w2.sum() < 5:
                    continue
                alpha = (om[w2].mean(0) - om[w1].mean(0)) / 0.01
                lev_true[k] = LEVER[0] * alpha[0] + LEVER[1] * alpha[1]
                j = int(np.argmin(np.abs(tp - e)))
                fseal[k] = fs[j]
                sumF[k] = fc[j]
        noise = rng.standard_normal((n, 2, 2)) * SIGMA_GYRO_10MS  # (period, mean index, axis x/y)
        alpha_noise = (noise[:, 1, :] - noise[:, 0, :]) / 0.01
        lev_noisy = lev_true + alpha_noise @ LEVER
        np.savez_compressed(target, t=t, head_Pa=inp.head_Pa, rod_Pa=inp.rod_Pa,
                            sum_N=net.sum(axis=1), net_N=net, f_z=inp.f_z_m_s2, f_z_prev=fz_prev,
                            phase=inp.phase.astype(str), band_N=inp.band_N, commanded=inp.commanded_m_s,
                            stroke=inp.stroke_m, lever_true=lev_true, lever_noisy=lev_noisy, fseal_sum_N=fseal,
                            sumFcyl_N=sumF, seal_limits_N=limits, t_ev=t_ev)
        index.append(dict(batch=b.name, run=d.name, n=int(n), fs_mean_kN=float(limits.mean() / 1e3),
                          has_pads=bool(np.isfinite(lev_true).any())))
        print(b.name, d.name, n, round(limits.mean() / 1e3, 2), bool(np.isfinite(lev_true).any()), flush=True)
(out / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
print("runs", len(index))
