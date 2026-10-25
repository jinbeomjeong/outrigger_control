"""S7 control-3 prep: crawler lift-off transient, L1 (compliant SMC crawler) vs L2b-NSC (rigid NSC crawler).

dynamics_model.md 5.25 (rev. 39). Read-only analysis of existing Chrono results (no Chrono run):
batches ``07_results/S7/ctrl3_20261024_154939`` (all L1 cases; L2b rpB, flat, fdown3.5) and
``07_results/S7/ctrl3_rerun_20261024_162807`` (L2b roll5.5, fup3.5, settle map = identity).

Per case (times relative to the controller start t0; lift-off ``lo`` = verify_S7C ``times_s.liftoff``,
first 10 Hz record sample after the last positive crawler z force):
* crawler force: 10 Hz record ``F_crawler`` (world) before lift-off; unloading rate dFz/dt (least squares
  over [lo - 0.6, lo - 0.1] s); quasi-static crawler wrench from the 1 ms pad forces
  (F_cr = W_vec - sum R_i, M_cr = - sum (p_i - c) x R_i, 50 ms mean) and its centre of pressure on the
  crawler-bottom plane (body frame) -> which track / end carries the last load;
* oscillation: net pad wrench on the body about its CoM (pad force R_world at the ball centre, body
  frame) band-passed 0.7 .. 15 Hz (Butterworth 4, zero phase); projection on the mass-normalised modes
  of the linear 6-DoF L1 model at the lift-off geometry (eta_dd_j = phi_j^T w, modal amplitude
  |eta_dd|/omega^2, modal energy (eta_dd)^2 / (2 omega^2)); leg force half amplitude after a
  1 .. 4 Hz band-pass (rocking band) and the C-R18 crude half amplitude (force - 1 s centred mean).

Pad force ``R_world`` = force of the floor on the pad (L2b: ``R_world_1ms`` raw 1 ms mean of the NSC
contact force). After the lift-off the pad wrench + gravity is the inertial wrench of the body (the rods
are <= 0.5 % of the mass, ignored). World z up, g = -9.80665 z m/s^2, body frame x fwd y left z up,
quaternions wxyz (Chrono). Units SI, angles deg, forces kN in the output.

Run (project root, dynamics-dev)::

    conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s7_liftoff_transient.py
Writes 06_analysis/01_chrono/17_S7/S7_liftoff_transient.json (+ .png), about 30 s.
"""
from __future__ import annotations

import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "01_dynamics"))
import dyn_model as dm  # noqa: E402

B1 = "07_results/S7/ctrl3_20261024_154939"
B2 = "07_results/S7/ctrl3_rerun_20261024_162807"
# pair name -> (case suffix, L1 batch, L2b batch)
PAIRS = {
    "rpB": ("D8_top_rpB_b1.0", B1, B1),
    "roll5.5": ("D8_top_roll5.5_b1.0", B1, B2),
    "fup3.5": ("D8_top_fup3.5_b1.0", B1, B2),
    "flat": ("smoke_top_flat", B1, B1),
    "fdown3.5": ("H4V_top_fdown3.5", B1, B1),
}
LEGS = dm.LEG_NAMES
OUT = ROOT / "06_analysis" / "01_chrono" / "17_S7" / "S7_liftoff_transient.json"
P = dm.load_params()
GEO = dm.geometry_from_params(P)
L1Y = P["contact"]["rigid_floor"]["L1"]
K_PAD = np.array([float(L1Y["kn_per_pad_N_m"][n]) for n in LEGS])
K_T = np.array([float(L1Y["bushing_stiffness_per_pad_N_m"][n]) for n in LEGS])
ZF = float(P["ground"]["crawler_bottom_z_m"])
BODY = dm.body_from_params(P, "top")


def qmat(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def mean_win(x, n):
    """Centred moving mean over n samples along axis 0 (edges shrink)."""
    c = np.cumsum(np.concatenate([np.zeros((1,) + x.shape[1:]), x]), axis=0)
    i = np.arange(len(x))
    lo = np.clip(i - n // 2, 0, len(x))
    hi = np.clip(i + n // 2 + 1, 0, len(x))
    return (c[hi] - c[lo]) / (hi - lo).reshape((-1,) + (1,) * (x.ndim - 1))


def modes_at(R, pos, balls_w, ext, F0):
    """Linear 6-DoF L1 modes (q = [u, rot] about the CoM, body frame) at the lift-off geometry."""
    bw = dm.body_with_rods(P, GEO, "top", ext)
    pts_b = (balls_w - pos) @ R  # (4,3) ball centres in the body frame
    M = dm.mass_6dof(bw)
    K = np.zeros((6, 6))
    for i in range(4):
        d = pts_b[i] - bw.com
        ax, ay, az = dm.a_vec(d)
        K += K_PAD[i] * np.outer(az, az) + K_T[i] * (np.outer(ax, ax) + np.outer(ay, ay))
        K[3:, 3:] -= F0[i] * dm._hz(d)
    w2, f, Phi, cls, orth = dm.modal(M, K, dm.DOF6)
    return bw, f, Phi, cls, orth


def analyse(args):
    pair, eng = args
    suf, b1, b2 = PAIRS[pair]
    B = ROOT / (b1 if eng == "L1" else b2)
    case = f"{eng}_{suf}"
    vj = json.loads((B / "verify_S7C.json").read_text(encoding="utf-8"))
    met = {m["case"]: m for m in vj["metrics"]}[case]
    tm = met["times_s"]
    t0, lo = tm["t0"], tm["liftoff"]
    p = np.load(B / case / "pads.npz")
    r = np.load(B / case / "record" / "record.npz")
    tp = p["t"] - t0
    tr = r["t"] - t0
    sel = (tp >= lo - 3.0) & (tp <= lo + 10.0)
    tp = tp[sel]
    Rw = (p["R_world_1ms"] if "R_world_1ms" in p.files else p["R_world"])[sel]
    balls = p["ball_centre_world"][sel]
    Fcyl = p["F_cyl_min_interval"][sel]
    smot = p["s_motor"][sel]
    if "body_quat_wxyz" in p.files:
        qs = p["body_quat_wxyz"][sel]
    else:  # 10 Hz record, normalised linear interpolation (attitude changes slowly)
        qs = np.column_stack([np.interp(tp, tr, r["body_quat_wxyz"][:, k]) for k in range(4)])
    pos = np.column_stack([np.interp(tp, tr, r["body_pos"][:, k]) for k in range(3)])
    Rm = np.array([qmat(q) for q in qs])
    com_w = pos + np.einsum("nij,j->ni", Rm, BODY.com)
    F = Rw.sum(axis=1)
    M = np.cross(balls - com_w[:, None, :], Rw).sum(axis=1)
    Fb = np.einsum("nji,nj->ni", Rm, F)
    Mb = np.einsum("nji,nj->ni", Rm, M)
    late = (tp >= lo + 5.0) & (tp <= lo + 8.0)
    Wvec = F[late].mean(axis=0)
    # --- quasi-static crawler wrench (world -> body), 50 ms mean
    Fcr = mean_win(Wvec[None, :] - F, 51)
    Mcr = mean_win(-M, 51)
    Fcr_b = np.einsum("nji,nj->ni", Rm, Fcr)
    Mcr_b = np.einsum("nji,nj->ni", Rm, Mcr)
    zc = ZF - BODY.com[2]  # crawler bottom plane relative to the CoM (body frame)

    def cop(k):
        fx, fy, fz = Fcr_b[k]
        mx, my, _ = Mcr_b[k]
        if fz < 2e3:
            return None
        y = (mx + zc * fy) / fz
        x = -(my - zc * fx) / fz
        return [float(x + BODY.com[0]), float(y + BODY.com[1])]

    pre = {}
    for dtb in (1.0, 0.5, 0.3, 0.2, 0.1, 0.05):
        k = int(np.argmin(np.abs(tp - (lo - dtb))))
        pre[f"-{dtb:g}"] = {"Fz_qs_kN": float(Fcr_b[k, 2] / 1e3),
                            "Fh_qs_kN": float(np.hypot(*Fcr[k, :2]) / 1e3),
                            "cop_xy_body_m": cop(k)}
    # --- recorded 10 Hz crawler force
    w10 = (tr >= lo - 1.05) & (tr <= lo + 0.25)
    rec10 = [{"t_minus_lo_s": round(float(a - lo), 3), "Fz_kN": float(b[2] / 1e3),
              "Fh_kN": float(np.hypot(b[0], b[1]) / 1e3)} for a, b in zip(tr[w10], r["F_crawler"][w10])]
    fit = (tr >= lo - 0.6) & (tr <= lo - 0.1)
    rate = float(np.polyfit(tr[fit], r["F_crawler"][fit, 2], 1)[0]) if fit.sum() >= 2 else math.nan
    # time from 50 % of the crawler load at lo - 1 s to zero (quasi-static 1 ms)
    k1 = int(np.argmin(np.abs(tp - (lo - 1.0))))
    ref = Fcr_b[k1, 2]
    pos_ = np.where((tp <= lo + 0.3) & (Fcr_b[:, 2] > 0.02 * Wvec[2]))[0]
    t_lo_qs = float(tp[pos_[-1]]) if len(pos_) else math.nan
    a50 = np.where((tp > lo - 3) & (tp <= t_lo_qs) & (Fcr_b[:, 2] <= 0.5 * ref))[0]
    t50 = float(tp[a50[0]]) if len(a50) else math.nan
    # load still on the crawler 0.1 s before the quasi-static lift-off and its release rate
    k01 = int(np.argmin(np.abs(tp - (t_lo_qs - 0.1))))
    k02 = int(np.argmin(np.abs(tp - (t_lo_qs - 0.2))))
    release = {"t_liftoff_qs_s": t_lo_qs, "t_liftoff_qs_minus_lo_s": t_lo_qs - lo,
               "Fz_1s_before_kN": float(ref / 1e3), "t50_before_liftoff_s": t_lo_qs - t50,
               "Fz_0p1s_before_kN": float(Fcr_b[k01, 2] / 1e3), "Fz_0p2s_before_kN": float(Fcr_b[k02, 2] / 1e3),
               "Fh_0p1s_before_kN": float(np.hypot(*Fcr[k01, :2]) / 1e3),
               "rate_last_0p1s_kN_s": float((Fcr_b[k01, 2] - 0.0) / 0.1 / 1e3),
               "rate_fit_10Hz_kN_s": rate / 1e3}
    # --- oscillation of the pad wrench on the body
    fs = 1.0 / np.median(np.diff(tp))
    sos = butter(4, [0.7, 15.0], btype="band", fs=fs, output="sos")
    wb = np.column_stack([Fb, Mb])
    wosc = sosfiltfilt(sos, wb, axis=0)
    a03 = (tp >= lo) & (tp <= lo + 3.0)
    a36 = (tp >= lo + 3.0) & (tp <= lo + 6.0)
    kl = int(np.argmin(np.abs(tp - lo)))
    ext = smot[kl]
    F0 = Fcyl[late].mean(axis=0)
    bw, f, Phi, cls, orth = modes_at(Rm[kl], pos[kl], balls[kl], ext, F0)
    om = 2 * np.pi * f
    eta_dd = wosc @ Phi  # (n, 6) modal accelerations (mass-normalised modes)
    modal = []
    for j in range(6):
        e03 = float((eta_dd[a03, j] ** 2).max() / (2 * om[j] ** 2))
        e36 = float((eta_dd[a36, j] ** 2).max() / (2 * om[j] ** 2))
        modal.append({"f_Hz": float(f[j]), "dof": cls[j], "amp_0_3": float(np.abs(eta_dd[a03, j]).max() / om[j] ** 2),
                      "E_max_0_3_J": e03, "E_max_3_6_J": e36})
    # (no Duhamel estimate here: the quasi-static crawler wrench W - sum R equals the true crawler wrench minus
    # M a, i.e. omega^2 eta in modal form, so it carries no dynamic information; see s7_liftoff_replica.py)
    # leg force rocking band 1..4 Hz and the C-R18 crude half amplitude
    sos2 = butter(4, [1.0, 4.0], btype="band", fs=fs, output="sos")
    fo = sosfiltfilt(sos2, Fcyl, axis=0)
    crude = Fcyl - mean_win(Fcyl, 1001)
    legs = {}
    for i, n in enumerate(LEGS):
        legs[n] = {"band_1_4Hz_halfamp_0_3_kN": float((fo[a03, i].max() - fo[a03, i].min()) / 2e3),
                   "band_1_4Hz_halfamp_3_6_kN": float((fo[a36, i].max() - fo[a36, i].min()) / 2e3),
                   "crude_halfamp_0_3_kN": float((crude[a03, i].max() - crude[a03, i].min()) / 2e3),
                   "min_raw_0_3_kN": float(Fcyl[a03, i].min() / 1e3)}
    # body angular rate (10 Hz record, body frame) peak after lift-off
    wr = (tr >= lo) & (tr <= lo + 3.0)
    omega_pk = np.abs(r["body_omega"][wr]).max(axis=0)
    # load step: leg force change from lo - 0.1 s to lo + 0.05 s (20 ms means)
    m20 = mean_win(Fcyl, 21)
    ka = int(np.argmin(np.abs(tp - (t_lo_qs - 0.1))))
    kb = int(np.argmin(np.abs(tp - (t_lo_qs + 0.05))))
    out = {"case": case, "batch": b1 if eng == "L1" else b2, "t0_s": t0, "liftoff_s": lo,
           "W_vec_kN": (Wvec / 1e3).tolist(),
           "crawler_10Hz": rec10, "crawler_qs_before_liftoff": pre, "release": release,
           "wrench_osc_peak_0_3": {k: float(np.abs(wosc[a03, j]).max() / 1e3)
                                   for j, k in enumerate(("Fx_kN", "Fy_kN", "Fz_kN", "Mx_kNm", "My_kNm", "Mz_kNm"))},
           "wrench_osc_peak_3_6": {k: float(np.abs(wosc[a36, j]).max() / 1e3)
                                   for j, k in enumerate(("Fx_kN", "Fy_kN", "Fz_kN", "Mx_kNm", "My_kNm", "Mz_kNm"))},
           "modes": modal, "mode_orthogonality": float(orth),
           "legs": legs, "body_omega_peak_0_3_mrad_s": (omega_pk * 1e3).tolist(),
           "leg_step_kN": ((m20[kb] - m20[ka]) / 1e3).tolist(),
           "stroke_at_liftoff_m": ext.tolist()}
    # series for the figure (decimated 5 ms)
    keep = (tp >= lo - 1.5) & (tp <= lo + 6.0)
    out["_series"] = {"t": (tp[keep][::5] - lo).tolist(), "Fcr_z": (Fcr_b[keep, 2][::5] / 1e3).tolist(),
                      "Mx": (wosc[keep, 3][::5] / 1e3).tolist(), "My": (wosc[keep, 4][::5] / 1e3).tolist(),
                      "Fcyl": (Fcyl[keep][::5] / 1e3).tolist()}
    return pair, eng, out


def figure(res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pairs = list(PAIRS)
    fig, ax = plt.subplots(3, len(pairs), figsize=(4.2 * len(pairs), 9), sharex=True)
    col = {"L1": "#1f77b4", "L2b": "#d62728"}
    for j, pr in enumerate(pairs):
        for eng in ("L1", "L2b"):
            s = res[pr][eng]["_series"]
            ax[0, j].plot(s["t"], s["Fcr_z"], color=col[eng], lw=1, label=eng)
            ax[1, j].plot(s["t"], s["Mx"], color=col[eng], lw=0.8, label=eng)
            ax[2, j].plot(s["t"], s["My"], color=col[eng], lw=0.8, label=eng)
        ax[0, j].set_title(pr)
        ax[0, j].set_ylabel("crawler Fz quasi-static [kN]")
        ax[1, j].set_ylabel("pad Mx about CoM, 0.7-15 Hz [kN m]")
        ax[2, j].set_ylabel("pad My about CoM, 0.7-15 Hz [kN m]")
        ax[2, j].set_xlabel("t - lift-off [s]")
        for a in ax[:, j]:
            a.axvline(0, color="k", lw=0.5)
            a.grid(alpha=0.3)
        ax[0, j].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main():
    jobs = [(pr, e) for pr in PAIRS for e in ("L1", "L2b")]
    with ProcessPoolExecutor(max_workers=min(10, len(jobs))) as ex:
        out = list(ex.map(analyse, jobs))
    res = {pr: {} for pr in PAIRS}
    for pr, e, o in out:
        res[pr][e] = o
    figure(res, OUT.with_suffix(".png"))
    for pr in res:
        for e in res[pr]:
            res[pr][e].pop("_series")
    summary = {}
    for pr in PAIRS:
        a, b = res[pr]["L1"], res[pr]["L2b"]
        summary[pr] = {
            "band_halfamp_0_3_L2b_over_L1": {n: b["legs"][n]["band_1_4Hz_halfamp_0_3_kN"]
                                             / a["legs"][n]["band_1_4Hz_halfamp_0_3_kN"] for n in LEGS},
            "modal_E_0_3_J": {f"{e}": [round(m["E_max_0_3_J"], 3) for m in res[pr][e]["modes"]] for e in ("L1", "L2b")},
            "modal_f_Hz": [round(m["f_Hz"], 3) for m in a["modes"]],
            "release_L1": a["release"], "release_L2b": b["release"],
        }
    doc = {"meta": {"script": "04_scripts/01_dynamics/s7_liftoff_transient.py", "doc": "dynamics_model.md 5.25",
                    "frames": "world z up, g -9.80665 z; body x fwd y left z up; quaternion wxyz",
                    "pad_force": "R_world (L2b R_world_1ms) at the ball centre, floor on pad",
                    "bands": {"wrench": [0.7, 15.0], "leg": [1.0, 4.0]}},
           "summary": summary, "cases": res}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    for pr in PAIRS:
        print(f"== {pr}")
        for e in ("L1", "L2b"):
            o = res[pr][e]
            rl = o["release"]
            print(f"  {e:3s} lo {o['liftoff_s']:.2f} (qs {rl['t_liftoff_qs_minus_lo_s']:+.3f}) "
                  f"Fz 1s {rl['Fz_1s_before_kN']:.1f} 0.2s {rl['Fz_0p2s_before_kN']:.1f} 0.1s {rl['Fz_0p1s_before_kN']:.1f}"
                  f" Fh0.1 {rl['Fh_0p1s_before_kN']:.1f} t50 {rl['t50_before_liftoff_s']:.3f} rate10 {rl['rate_fit_10Hz_kN_s']:.0f} kN/s")
            print("      cop " + " ".join(f"{k}:{v['cop_xy_body_m']}" for k, v in o["crawler_qs_before_liftoff"].items()))
            print("      wrench pk 0-3 " + " ".join(f"{k} {v:.1f}" for k, v in o["wrench_osc_peak_0_3"].items()))
            print("      modes " + " ".join(f"{m['f_Hz']:.2f}Hz {list(m['dof'])[:2]} E {m['E_max_0_3_J']:.2f}/{m['E_max_3_6_J']:.2f}"
                                       for m in o["modes"]))
            print("      legs band 0-3 " + " ".join(f"{n} {o['legs'][n]['band_1_4Hz_halfamp_0_3_kN']:.2f}"
                                              f"({o['legs'][n]['crude_halfamp_0_3_kN']:.2f})" for n in LEGS)
                  + f" omega pk {np.round(o['body_omega_peak_0_3_mrad_s'], 2)} step {np.round(o['leg_step_kN'], 1)}")
            print("      10Hz " + " ".join(f"{d['t_minus_lo_s']:+.1f}:{d['Fz_kN']:.0f}/{d['Fh_kN']:.1f}" for d in o["crawler_10Hz"]))


if __name__ == "__main__":
    main()
