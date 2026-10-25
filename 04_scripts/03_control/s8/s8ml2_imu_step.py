"""Rev. 48: can the IMU vertical specific force explain D1 head steps that the four-leg sum rule
(D1' head, ratio |d sum| / (|dp_h| A_p) < 0.5) calls unexplained?

Physics: with the pads carrying the upper body (crawler off the ground), the sum of the leg
net forces is M (g + a_z) plus rotational terms, i.e. M_eff f_z at the IMU. A load
redistribution and a vertical bounce both keep the residual r = sum F_read - M_eff f_z(t_k)
nearly unchanged; a head-sensor jump moves r by the whole step force.

M_eff is calibrated per run from the READY samples before the event (sum / f_z median).
f_z(t_k) uses the IMU 10 ms sub-period means of the period ending at t_k (r8 'imu_samples'):
variant 'last' = last sub-mean, 'extrap' = last + 0.5 (last - previous) (centre -> t_k).
Readings are the controller inputs (record 'meas.*'), as the monitor sees them.

Prints every head step > 100 bar with ratio_sum, ratio_imu(last), ratio_imu(extrap), and per
batch the distribution of |d r| over transient periods (some |dp_h| > 30 bar), to compare with
0.5 x the force of a 100 bar head jump (rear 47.5 kN, front 66.4 kN).
Also writes a JSON summary.
Usage: python -I s8ml2_imu_step.py <out_json> <batch_dir> [...]
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
A_P = np.array([1.3273e-2, 1.3273e-2, 9.503e-3, 9.503e-3])
A_ANN = np.array([3.770e-3, 3.770e-3, 3.142e-3, 3.142e-3])
LEGS = ["FL", "FR", "RL", "RR"]
LIMIT = 100.0


def runs(batch: Path):
    for sub in (batch / "bases", batch / "episodes", batch):
        if sub.is_dir():
            for d in sorted(sub.iterdir()):
                if d.is_dir() and not d.name.startswith("_") and (d / "record" / "record.npz").exists() \
                        and (d / "r8_series.npz").exists():
                    yield d


out = {"steps": [], "batches": {}}
for b in sys.argv[2:]:
    b = Path(b)
    dr_all = {"last": [], "extrap": [], "sum": []}
    nsteps = 0
    for d in runs(b):
        rec = np.load(d / "record" / "record.npz", allow_pickle=True)
        r8 = np.load(d / "r8_series.npz", allow_pickle=True)
        if "imu_samples" not in r8.files or "meas.head_pressure" not in rec.files:
            continue
        t = rec["t"]
        hm = rec["meas.head_pressure"] / 1e5
        rm = rec["meas.rod_pressure"] / 1e5
        net = (hm * A_P - rm * A_ANN) * 1e2  # kN
        s = net.sum(axis=1)
        imu = r8["imu_samples"][:, :, 2]
        f_last = imu[:, -1]
        f_ext = imu[:, -1] + 0.5 * (imu[:, -1] - imu[:, -2])
        phase = np.array([str(p) for p in r8["phase"]])
        try:
            res = json.loads((d / "result.json").read_text(encoding="utf-8"))
            t_ev = float(res.get("event_t_s") or t[-1])
        except Exception:
            t_ev = t[-1]
        ready = (phase == "ready") & (t < t_ev - 0.05)
        if ready.sum() < 3:
            continue
        m_eff = np.median(s[ready] / f_last[ready])  # kN per m/s^2
        r_last = s - m_eff * f_last
        r_ext = s - m_eff * f_ext
        dh = np.diff(hm, axis=0)
        ds = np.diff(s)
        drl = np.diff(r_last)
        dre = np.diff(r_ext)
        trans = np.abs(dh).max(axis=1) > 30.0
        dr_all["last"] += list(np.abs(drl[trans]))
        dr_all["extrap"] += list(np.abs(dre[trans]))
        dr_all["sum"] += list(np.abs(ds[trans]))
        for k in np.flatnonzero(trans & (np.abs(drl) >= 40.0)):
            crawler = rec["F_crawler"][k + 1] if "F_crawler" in rec.files else None
            print(f"   big |d r| {d.name:28s} t {t[k+1]:6.2f} phase {phase[k+1]:8s} d r(last) {drl[k]:+7.1f} kN"
                  f" max|dp_h| {np.abs(dh[k]).max():5.1f} bar crawler {np.round(crawler/1e3, 1) if crawler is not None else '-'} kN")
        for k, leg in zip(*np.nonzero(np.abs(dh) > LIMIT)):
            own = abs(dh[k, leg]) * A_P[leg] * 1e2
            row = dict(run=d.name, batch=b.name, leg=LEGS[leg], t=round(float(t[k + 1]), 2), dp=round(float(dh[k, leg]), 1),
                       own_kN=round(own, 1), ratio_sum=round(abs(ds[k]) / own, 3),
                       ratio_imu_last=round(abs(drl[k]) / own, 3), ratio_imu_extrap=round(abs(dre[k]) / own, 3),
                       m_eff_t=round(m_eff * 1e3 / 1e3, 3))
            out["steps"].append(row)
            nsteps += 1
            print(f"  {d.name:10s} {LEGS[leg]} t {t[k+1]:6.2f} dp {dh[k, leg]:+7.1f} own {own:6.1f} kN"
                  f"  sum {row['ratio_sum']:.2f}  imu_last {row['ratio_imu_last']:.2f}  imu_ext {row['ratio_imu_extrap']:.2f}")
    summ = {}
    for key, v in dr_all.items():
        v = np.array(v)
        if len(v):
            summ[key] = dict(n=int(len(v)), p50=float(np.percentile(v, 50)), p90=float(np.percentile(v, 90)),
                             p99=float(np.percentile(v, 99)), max=float(v.max()),
                             over_47_5=int((v >= 47.5).sum()))
    out["batches"][b.name] = dict(head_steps=nsteps, transient_abs_dr_kN=summ)
    print(f"{b.name}: head steps > {LIMIT:g} bar {nsteps}; |d r| over transient periods [kN]:")
    for key, x in summ.items():
        print(f"   {key:6s} n {x['n']} p50 {x['p50']:.1f} p90 {x['p90']:.1f} p99 {x['p99']:.1f} max {x['max']:.1f} (>= 47.5: {x['over_47_5']})")
Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
