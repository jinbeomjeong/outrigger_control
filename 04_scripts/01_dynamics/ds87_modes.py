"""D-S8-7 (dynamics_model.md rev. 41): rocking / heave after a fast settlement - Chrono identification vs
linear modes of the L2b leg model.

Part A, Chrono (records extracted by ds87_extract.py, Chrono-dev): for each listed episode
  * body roll / pitch from the 1 ms quaternion (wxyz, body -> world, ZYX: roll about x, pitch about y),
    minus the pre-event median; sum of the cylinder forces / W (W = pre-event median sum, 1 ms).
  * ESPRIT (matrix pencil, Hankel SVD) on the 5 ms means, windows [0.25, 1.5] s, [1.5, 3.5] s, [3.5, 7.5] s
    after the event; a quadratic trend is removed first (controller drift). Reported: dominant pole (largest
    amplitude) in 0.8 .. 4 Hz for roll / pitch, and in 4 .. 20 Hz for the sum / W, f [Hz] and zeta.
  * lift-off share: fraction of time any pad is airborne per window.
Part B, linear model (dyn_model.model_10dof: 6-DoF body + 4 rod axial DoF; body = YAML level, rods separate):
  oil spring k_o between body and rod, outer spring k_out (rod, frame, concrete; NSC pad rigid) between rod
  and floor, lateral bushing at the pad. Strokes, beta, L0r of the episode at the event. Configurations
    C4h  four legs, k_o = k_h(s) = beta A_p / (L0h + s)                  (moving or loading above the knee)
    C4b  four legs, k_o = k_h + k_r, k_r = beta A_ann / (L0r + 0.7 - s)  (locked, unloading below the knee)
    C4s  four legs, oil rigid (seal stuck: k = k_out)                      (upper bound)
    C3-<leg>  that leg removed (contact and lateral), k_o = k_h
  Damping: c_locked on the oil spring, lateral bushing damping; complex modes -> f_n, zeta.
Writes 06_analysis/00_dynamics/ds87_modes.json.
Usage: python -I ds87_modes.py <extract_dir> RUN [RUN ...]
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
GEO = dm.geometry_from_params(P)
LEGS = list(dm.LEG_NAMES)
OUT = ROOT / "06_analysis" / "00_dynamics" / "ds87_modes.json"
A_ANN = np.array([dm.annulus_area(i) for i in range(4)])
STROKE = 0.70


def rp_from_quat(q):
    w, x, y, z = q.T
    R20 = 2 * (x * z - w * y)
    R21 = 2 * (y * z + w * x)
    R22 = 1 - 2 * (x * x + y * y)
    return np.arctan2(R21, R22), -np.arcsin(np.clip(R20, -1, 1))


def esprit(x, dt, p=10):
    x = np.asarray(x, float)
    N = len(x)
    L = N // 2
    H = np.lib.stride_tricks.sliding_window_view(x, N - L + 1)[:L]
    U, s, _ = np.linalg.svd(H, full_matrices=False)
    Us = U[:, :p]
    Phi = np.linalg.lstsq(Us[:-1], Us[1:], rcond=None)[0]
    z = np.linalg.eigvals(Phi)
    V = np.vander(z, N, increasing=True).T
    a = np.linalg.lstsq(V, x.astype(complex), rcond=None)[0]
    lam = np.log(z) / dt
    f = np.abs(lam.imag) / (2 * np.pi)
    wn = np.abs(lam)
    zeta = -lam.real / np.where(wn > 0, wn, 1)
    return f, zeta, np.abs(a), wn / (2 * np.pi)


def dominant(x, dt, band, p=10):
    f, zeta, amp, fn = esprit(x, dt, p)
    sel = (f >= band[0]) & (f <= band[1])
    if not sel.any():
        return None
    k = np.flatnonzero(sel)[np.argmax(amp[sel])]
    return dict(f_Hz=round(float(f[k]), 3), zeta=round(float(zeta[k]), 4), amp=float(amp[k]))


def block_mean(t, x, h):
    n = int(round(h / np.median(np.diff(t))))
    m = len(x) // n
    return t[: m * n].reshape(m, n).mean(1), x[: m * n].reshape(m, n, *x.shape[1:]).mean(1)


def chrono_part(z, info):
    t = z["p_t"] - info["t_ev"]
    F = z["p_F_cyl"]
    pre = (t > -1.5) & (t < -0.1)
    W = float(np.median(F[pre].sum(1)))
    roll, pitch = rp_from_quat(z["p_body_quat_wxyz"])
    roll = np.degrees(roll - np.median(roll[pre]))
    pitch = np.degrees(pitch - np.median(pitch[pre]))
    sF = F.sum(1) / W
    air = z["p_airborne"].any(1)
    out = dict(W_kN=round(W / 1e3, 2), M_from_W_kg=round(W / 9.80665, 1), windows={})
    for lo, hi in ((0.25, 1.5), (1.5, 3.5), (3.5, 7.5)):
        w = (t >= lo) & (t < hi)
        if w.sum() < 500:
            continue
        tb, X = block_mean(t[w], np.column_stack([roll[w], pitch[w], sF[w]]), 0.005)
        res = {}
        for j, name, band in ((0, "roll", (0.8, 4.0)), (1, "pitch", (0.8, 4.0)), (2, "sumF", (4.0, 20.0))):
            y = X[:, j] - np.polyval(np.polyfit(tb, X[:, j], 2), tb)
            res[name] = dominant(y, 0.005, band)
            res[name + "_rms"] = round(float(y.std()), 4)
        res["airborne_share"] = round(float(air[w].mean()), 3)
        res["sumF_min_max"] = [round(float(sF[w].min()), 3), round(float(sF[w].max()), 3)]
        out["windows"][f"{lo}-{hi}"] = res
    w = (t >= 0) & (t < 2)
    out["sumF_min_max_0_2"] = [round(float(sF[w].min()), 3), round(float(sF[w].max()), 3)]
    return out


def linear_part(z, info):
    t = z["p_t"] - info["t_ev"]
    pre = (t > -0.6) & (t < -0.1)
    s = np.median(z["p_s_link"][pre], axis=0)
    F0 = np.median(z["p_F_cyl"][pre], axis=0)
    beta = info["beta_Pa"]
    Ap = np.array(info["head_area_m2"])
    L0h = info["head_dead_m"]
    L0r = info["L0r_m"]
    k_h = beta * Ap / (L0h + s)
    k_r = beta * A_ANN / (L0r + STROKE - s)
    k_out = 1 / (1 / np.array(info["k_rod_N_m"]) + 1 / info["frame_N_m"] + 1 / info["k_concrete_N_m"])
    body = dm.body_from_params(P, info["level"])
    kh = np.array(info["k_lat"])
    ch = np.array(info["c_lat"])
    co = np.array(info["c_locked"])
    res = dict(strokes_m=np.round(s, 4).tolist(), F0_kN=np.round(F0 / 1e3, 2).tolist(),
               k_h=np.round(k_h, -3).tolist(), k_r=np.round(k_r, -3).tolist(), k_out=np.round(k_out, -3).tolist(),
               k_series_h=np.round(1 / (1 / k_h + 1 / k_out), -3).tolist(),
               k_series_b=np.round(1 / (1 / (k_h + k_r) + 1 / k_out), -3).tolist(),
               k_op_override=info["k_op"], configs={})
    cm = np.array(info["c_moving"])
    cfgs = {"C4h": (k_h, np.ones(4, bool), co), "C4h-cmov": (k_h, np.ones(4, bool), cm),
            "C4b": (k_h + k_r, np.ones(4, bool), co), "C4s": (np.full(4, 1e12), np.ones(4, bool), co)}
    for i, n in enumerate(LEGS):
        on = np.ones(4, bool)
        on[i] = False
        cfgs[f"C3-{n}"] = (k_h, on, co)
        cfgs[f"C3b-{n}"] = (k_h + k_r, on, co)
        cfgs[f"C3s-{n}"] = (np.full(4, 1e12), on, co)
    for name, (ko, on, cdamp) in cfgs.items():
        kc = np.where(on, k_out, 1.0)  # removed leg: 1 N/m (avoids 1/0 in the static split)
        M, K, C, labels, _ = dm.model_10dof(body, GEO, s, ko, kc, np.where(on, kh, 0.0), co=cdamp, cc=np.zeros(4),
                                            ch=np.where(on, ch, 0.0))
        w2, f, Phi, cls, orth = dm.modal(M, K, labels)
        fn, zeta = dm.complex_modes(M, K, C)
        body_modes = []
        for j in range(10):
            if f[j] < 40:
                body_modes.append(dict(f_Hz=round(float(f[j]), 3), shape=cls[j]))
        # damped: match by nearest frequency
        for bm in body_modes:
            k = int(np.argmin(np.abs(fn - bm["f_Hz"])))
            bm["zeta"] = round(float(zeta[k]), 4)
        res["configs"][name] = dict(modes=body_modes, orth=float(orth))
    return res


def main():
    src = Path(sys.argv[1])
    out = {}
    for run in sys.argv[2:]:
        z = np.load(src / f"{run}.npz", allow_pickle=True)
        info = json.loads(str(z["info"]))
        a = chrono_part(z, info)
        b = linear_part(z, info)
        out[run] = dict(info={k: info[k] for k in ("leg", "depth_m", "ramp_s", "level", "fs_kN", "beta_Pa", "L0r_m")},
                        chrono=a, linear=b)
        print(f"== {run} {info['leg']} {info['depth_m']*1e3:.1f} mm/{info['ramp_s']:.3f} s {info['level']} Fs {info['fs_kN']}"
              f" W {a['W_kN']} kN sumF/W 0-2 s {a['sumF_min_max_0_2']}")
        print("   F0", b["F0_kN"], "s", b["strokes_m"], "k_series_h", b["k_series_h"], "k_series_b", b["k_series_b"],
              "k_op", b["k_op_override"])
        for wn, r in a["windows"].items():
            print(f"   chrono {wn:8s} roll {r['roll']} pitch {r['pitch']} sumF {r['sumF']} air {r['airborne_share']}"
                  f" rms r/p {r['roll_rms']}/{r['pitch_rms']} deg")
        for cn, c in b["configs"].items():
            print(f"   {cn:9s} " + "; ".join(f"{m['f_Hz']:.2f} Hz z{m['zeta']:.3f} {list(m['shape'].keys())[:2]}"
                                           for m in c["modes"][:7]))
    OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
