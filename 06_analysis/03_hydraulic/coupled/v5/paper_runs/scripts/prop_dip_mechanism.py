"""Rear pre-liftoff force dip: J1 pad B open-loop lift, V0 (= v4) vs VB proportional (speed x 0.8947).

Question: why is the rear minimum cylinder force 9.28/9.17 kN (prop) vs 11.66/11.73 kN (V0) when the
geometric path is the same?  Reads series.npz (1 ms) and result.json of both runs, aligns them by the
rear pad contact time (swivel event) and by stroke progress, and splits the rear leg force into
rate-dependent terms:
  leg dashpot  F_d = c_move (u - ds/dt)              (l2b_actuator.py: F = spring + c (u - ds))
  SCM rate     F_R = R A dz/dt                         (Chrono SCM damping_R, pad bottom area)
Output: JSON to argv[1], short ASCII table to stdout.
Units SI in the arrays; kN / mm / mm/s / deg in the printout.
"""
import json
import sys
from pathlib import Path

import numpy as np

R = Path(r"C:\workspace\outrigger_control\07_results\S9")
RUNS = {
    "V0": (R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0", 0.020924),
    "prop": (R / "batch_V5-OPENLOOP-VB-PROP_20261108_164953/P3a_J1_B_VB_prop", 0.020924 * 0.894736837447082),
    "prio": (R / "batch_V5-OPENLOOP-VB_20261108_112044/P3a_J1_B_VB", None),
}
F_MIN = 9414.58911
C_MOVE = np.array([100206.06547702239, 100206.06547702239, 86949.01443833958, 86949.01443833958])
R_SCM = 992000.0
AREA = np.array([0.1071, 0.1071, 0.0607, 0.0607])
M_BODY = None  # read from p3a weight


def load(path):
    res = json.loads((path / "result.json").read_text("utf-8"))
    z = np.load(path / "series.npz")
    d = {k: z[k] for k in z.files}
    d["W"] = res["p3a"]["weight_N"]
    ev = res["swivel"]["events"]
    d["t_contact"] = [min(e[0] for e in ev if e[1] == i) for i in range(4)]
    fs = path / "flow_series.npz"
    if fs.exists():
        f = np.load(fs)
        cols = [str(c) for c in f["columns"]]
        d["flow"] = {c: f["rows"][:, j] for j, c in enumerate(cols)}
    return d


def deriv(t, y):
    return np.gradient(y, t, axis=0)


out = {"rule": __doc__.split("\n")[0], "runs": {}}
D = {}
for name, (p, u0) in RUNS.items():
    d = load(p)
    t = d["t_s"]
    sm = d["s_motor_m"]
    sk = d["pad_sinkage_geometric_m"]
    fc = d["F_cyl_N"]
    ds = deriv(t, sm)
    dz = deriv(t, sk)
    if "flow" in d:
        u = np.column_stack([np.interp(t, d["flow"]["t"], d["flow"][f"v_{l}"]) for l in ("FL", "FR", "RL", "RR")])
    else:
        u = np.where(t[:, None] > 8.1, u0, np.nan) * np.ones((1, 4))
    Fd = C_MOVE * (u - ds)
    FR = R_SCM * AREA * np.clip(dz, 0, None)
    zb = d["body_pos_m"][:, 2]
    zb_dd = deriv(t, deriv(t, zb))
    pitch = d["roll_pitch_deg"][:, 1]
    wy = d["body_omega_world_rad_s"][:, 1]
    wy_d = deriv(t, wy)
    cr = d["scm_crawler_normal_N"]
    tc = d["t_contact"]
    # window: rear contact - 0.05 .. liftoff
    k_min = [None] * 4
    above = [np.nonzero((t > 8) & (fc[:, i] > 1.4 * F_MIN))[0][0] for i in range(4)]
    lo = np.nonzero((t > 8) & (cr < 0.01 * d["W"]))[0][0]
    for i in (2, 3):
        seg = slice(above[i], lo + 1)
        k_min[i] = above[i] + int(np.argmin(fc[seg, i]))
    for i in (0, 1):
        k_min[i] = above[i] + int(np.argmin(fc[above[i]:lo + 1, i]))
    D[name] = dict(t=t, sm=sm, sk=sk, fc=fc, ds=ds, dz=dz, u=u, Fd=Fd, FR=FR, zb=zb, zb_dd=zb_dd,
                   pitch=pitch, wy=wy, wy_d=wy_d, cr=cr, tc=tc, k_min=k_min, N=d["scm_pad_normal_N"], W=d["W"])
    # rear peak before the min (max between contact and min)
    kr = k_min[2]
    k_c = int(np.searchsorted(t, tc[2]))
    k_pk = k_c + int(np.argmax(fc[k_c:kr + 1, 2]))
    kf = int(np.searchsorted(t, tc[0]))
    def snap(k):
        return {
            "t_s": float(t[k]), "t_minus_rear_contact_s": float(t[k] - tc[2]),
            "s_motor_mm": (sm[k] * 1e3).round(3).tolist(),
            "progress_rear_mm": float((sm[k, 2] - sm[k_c, 2]) * 1e3),
            "F_cyl_kN": (fc[k] / 1e3).round(3).tolist(), "pad_N_kN": (d["scm_pad_normal_N"][k] / 1e3).round(3).tolist(),
            "crawler_kN": float(cr[k] / 1e3),
            "sink_mm": (sk[k] * 1e3).round(3).tolist(), "sink_rate_mm_s": (dz[k] * 1e3).round(3).tolist(),
            "ds_mm_s": (ds[k] * 1e3).round(3).tolist(), "u_mm_s": (u[k] * 1e3).round(3).tolist(),
            "leg_dashpot_kN": (Fd[k] / 1e3).round(3).tolist(), "scm_rate_kN": (FR[k] / 1e3).round(3).tolist(),
            "pitch_deg": float(pitch[k]), "pitch_rate_deg_s": float(np.degrees(wy[k])),
            "pitch_acc_deg_s2": float(np.degrees(wy_d[k])),
            "z_body_mm": float(zb[k] * 1e3), "m_zdd_kN": float(d["W"] / 9.80665 * zb_dd[k] / 1e3),
        }
    out["runs"][name] = {
        "t_contact_s": tc, "front_minus_rear_contact_s": tc[0] - tc[2],
        "front_minus_rear_contact_stroke_mm": float((sm[kf, 2] - sm[k_c, 2]) * 1e3) if True else None,
        "t_1p4Fmin_s": [float(t[a]) for a in above], "t_liftoff_s": float(t[lo]),
        "at_rear_contact": snap(k_c), "at_rear_peak": snap(k_pk), "at_front_contact": snap(kf),
        "at_rear_min": snap(kr), "at_front_min": snap(k_min[0]),
    }

# progress-aligned comparison: rear force vs rear stroke progress since rear contact
grid = np.arange(-1.0, 12.01, 0.25)  # mm
cmp = []
for name in ("V0", "prop"):
    e = D[name]
    k_c = int(np.searchsorted(e["t"], e["tc"][2]))
    pr = (e["sm"][:, 2] - e["sm"][k_c, 2]) * 1e3
    m = (e["t"] > e["tc"][2] - 0.1) & (e["t"] < e["tc"][2] + 0.7)
    e["prog"] = (pr[m], m)
rows = []
for g in grid:
    row = {"prog_mm": float(g)}
    for name in ("V0", "prop"):
        e = D[name]
        pr, m = e["prog"]
        idx = np.nonzero(m)[0]
        j = idx[int(np.argmin(np.abs(pr - g)))]
        row[name] = {"t_rel_s": float(e["t"][j] - e["tc"][2]),
                     "F_rear_kN": float(e["fc"][j, 2:].mean() / 1e3), "F_front_kN": float(e["fc"][j, :2].mean() / 1e3),
                     "crawler_kN": float(e["cr"][j] / 1e3), "pitch_deg": float(e["pitch"][j]),
                     "sink_rear_mm": float(e["sk"][j, 2:].mean() * 1e3), "sink_front_mm": float(e["sk"][j, :2].mean() * 1e3),
                     "zdot_rear_mm_s": float(e["dz"][j, 2:].mean() * 1e3), "zdot_front_mm_s": float(e["dz"][j, :2].mean() * 1e3),
                     "Fd_rear_kN": float(e["Fd"][j, 2:].mean() / 1e3), "FR_rear_kN": float(e["FR"][j, 2:].mean() / 1e3),
                     "Fd_front_kN": float(e["Fd"][j, :2].mean() / 1e3), "FR_front_kN": float(e["FR"][j, :2].mean() / 1e3),
                     "zbody_mm": float(e["zb"][j] * 1e3), "pitch_rate_deg_s": float(np.degrees(e["wy"][j]))}
    rows.append(row)
out["progress_aligned"] = rows

Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=float), "utf-8")
for name, r in out["runs"].items():
    print(f"== {name} contact {np.round(r['t_contact_s'], 4)} gap {r['front_minus_rear_contact_s']:.4f} s "
          f"{r['front_minus_rear_contact_stroke_mm']:.3f} mm liftoff {r['t_liftoff_s']:.3f}")
    for key in ("at_rear_contact", "at_rear_peak", "at_front_contact", "at_rear_min", "at_front_min"):
        s = r[key]
        print(f"  {key:16s} t {s['t_s']:.3f} (+{s['t_minus_rear_contact_s']:.3f}) prog {s['progress_rear_mm']:.2f} "
              f"F {s['F_cyl_kN']} cr {s['crawler_kN']:.1f} sink {s['sink_mm']} zdot {s['sink_rate_mm_s']} "
              f"ds {s['ds_mm_s']} Fd {s['leg_dashpot_kN']} FR {s['scm_rate_kN']} pitch {s['pitch_deg']:.4f} "
              f"q {s['pitch_rate_deg_s']:.4f} mzdd {s['m_zdd_kN']:.2f}")
print("prog | V0: t Fr Ff cr pitch zr zf zdr zdf Fdr FRr | prop: same")
for row in rows:
    a, b = row["V0"], row["prop"]
    print(f"{row['prog_mm']:5.2f} | {a['t_rel_s']:.3f} {a['F_rear_kN']:6.2f} {a['F_front_kN']:6.2f} {a['crawler_kN']:6.1f} "
          f"{a['pitch_deg']:.4f} {a['sink_rear_mm']:6.2f} {a['sink_front_mm']:6.2f} {a['zdot_rear_mm_s']:6.2f} "
          f"{a['zdot_front_mm_s']:6.2f} {a['Fd_rear_kN']:5.2f} {a['FR_rear_kN']:5.2f} | {b['t_rel_s']:.3f} "
          f"{b['F_rear_kN']:6.2f} {b['F_front_kN']:6.2f} {b['crawler_kN']:6.1f} {b['pitch_deg']:.4f} {b['sink_rear_mm']:6.2f} "
          f"{b['sink_front_mm']:6.2f} {b['zdot_rear_mm_s']:6.2f} {b['zdot_front_mm_s']:6.2f} {b['Fd_rear_kN']:5.2f} {b['FR_rear_kN']:5.2f}")
