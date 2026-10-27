"""dynamics_model.md rev. 55: damping of the ~2 Hz locked rocking mode (L2b-NSC, F_s = 0) after FAULT.

Question (s6_control_spec.md rev. 66, 336.3 / 337, U-S8-72 (da)): the 2.03 Hz lock-state mode decays with
zeta ~0.0083..0.009 (r65_c68b_decay.py, 1 s window envelope). Is this what the model's damping terms give,
and why is it far below the leg zeta 0.03 of damping_survey.md?

Part A, Chrono record (read only), window [anchor + 1 s, end] (anchor = first FAULT, else last READY):
  * state: mean stroke s_link, mean F_cyl, rod / head pressure range, seal stuck / pad sliding / airborne
    shares (seal friction, pad Coulomb slip and lift-off are the only non-viscous dissipation paths);
  * ESPRIT (5 ms means, linear trend removed) on F_cyl per leg, roll, pitch in consecutive 3 s windows
    -> f, zeta vs amplitude;
  * complex amplitudes at the identified pole (least squares on [1, t, e^-st cos wt, e^-st sin wt]) of
    F_cyl, s_link, lateral forces, roll, pitch (mode shape from the record);
  * per-leg secant stiffness dF_cyl / d(-s_link) on the loading / unloading half (rod-side knee check);
  * energy split from the record: mean dissipated power of the axial dashpots c (u - ds) with u = 0
    (c ds^2) and of the lateral bushings (c_t (dF_lat / dt / k_t)^2), mode energy = elastic energy at the
    amplitude minus the geometric (P-delta) part -> zeta_rec = P / (2 w E).
Part B, independent linear model (numpy, not the Chrono code): rigid superstructure 6-DoF (YAML level),
  per leg an axial spring k_ax + dashpot c_lock between the attachment point and the rigid floor (rod mass
  neglected, 0.2 % of the mass; the 10-DoF variant with rod DoF is also evaluated), a lateral spring
  k_t + dashpot c_t at the pad, geometric stiffness of the recorded mean pad forces.
  Stiffness variants: 'rec' (record secant k), 'h' head only series(k_h(s), k_rod, k_frame, k_concrete),
  'b' both chambers series(k_h + k_r, ...). Damping: YAML LOCK c_lock (actuator law, rev. 33) and the
  actual lateral bushing damping (2x the Chrono input).
  Output per variant: f, zeta (complex eigenvalues), zeta split per element
  zeta_e = phi^T C_e phi / (2 w phi^T M phi) and strain-energy shares (axial, lateral, geometric);
  discrete semi-implicit Euler map at dt 1e-4 s (Chrono hook forces are explicit) for the dt effect.
Writes 06_analysis/00_dynamics/r65_lock_rocking_damping.json.

Usage: python -I r65_lock_rocking_damping.py <case_dir> [<case_dir> ...]
Units SI (N, m, s, rad); printed forces kN. Body frame x forward, y left, z up; roll about x, pitch about y.
Quaternion order in pads.npz: w, x, y, z (body -> world).
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
OUT = ROOT / "06_analysis" / "00_dynamics" / "r65_lock_rocking_damping.json"

ACT = P["actuator"]
BETA = float(ACT["oil_bulk_modulus_eff_Pa"])
L0H = float(ACT["oil_dead_length_m"])
L0R = float(ACT["rod_dead_length_m"])
K_FRAME = float(ACT["frame_stiffness_N_m"])
STROKE = float(ACT["stroke_m"])
L1 = P["contact"]["rigid_floor"]["L1"]
K_ROD = np.array([L1["derivation"]["k_rod_N_m"][n] for n in LEGS], float)
K_CONC = float(P["contact"]["rigid_floor"]["concrete"]["k_N_m"])
C_LOCK = np.array([L1["cn_per_pad_N_s_m"][n] for n in LEGS], float)  # actuator law locked c (rev. 33)
K_LAT = np.array([ACT["L2b_NSC"]["lateral_bushing_N_m"][n] for n in LEGS], float)
C_LAT = 2.0 * np.array([ACT["L2b_NSC"]["lateral_bushing_damping_input_N_s_m"][n] for n in LEGS], float)
A_P = np.array([P["legs"][n]["cylinder"]["head_area_m2"] for n in LEGS], float)
A_ANN = np.array([P["legs"][n]["cylinder"]["annulus_area_m2"] for n in LEGS], float)
ZETA_REF = float(L1["derivation"]["damping_ratio"])
F_REF_HZ = float(L1["derivation"]["damping_reference_mode_Hz"])
DT_CHRONO = 1e-4


# ------------------------------------------------------------------ record helpers
def rp_from_quat(q):
    w, x, y, z = q.T
    r20 = 2 * (x * z - w * y)
    r21 = 2 * (y * z + w * x)
    r22 = 1 - 2 * (x * x + y * y)
    return np.arctan2(r21, r22), -np.arcsin(np.clip(r20, -1, 1))


def esprit(x, dt, p=8):
    x = np.asarray(x, float)
    n = len(x)
    L = n // 2
    H = np.lib.stride_tricks.sliding_window_view(x, n - L + 1)[:L]
    U, _, _ = np.linalg.svd(H, full_matrices=False)
    Us = U[:, :p]
    Phi = np.linalg.lstsq(Us[:-1], Us[1:], rcond=None)[0]
    z = np.linalg.eigvals(Phi)
    V = np.vander(z, n, increasing=True).T
    a = np.linalg.lstsq(V, x.astype(complex), rcond=None)[0]
    lam = np.log(z) / dt
    f = np.abs(lam.imag) / (2 * np.pi)
    wn = np.abs(lam)
    zeta = -lam.real / np.where(wn > 0, wn, 1)
    return f, zeta, np.abs(a)


def dominant(x, dt, band=(1.0, 5.0)):
    f, zeta, amp = esprit(x, dt)
    sel = (f >= band[0]) & (f <= band[1])
    if not sel.any():
        return None
    k = np.flatnonzero(sel)[np.argmax(amp[sel])]
    return float(f[k]), float(zeta[k]), float(2 * amp[k])


def block_mean(t, x, h):
    n = int(round(h / np.median(np.diff(t))))
    m = len(x) // n
    return t[: m * n].reshape(m, n).mean(1), x[: m * n].reshape(m, n, *x.shape[1:]).mean(1)


def anchor_time(case: Path):
    r8 = np.load(case / "r8_series.npz", allow_pickle=True)
    ph = np.array([str(p).split(".")[-1].lower() for p in r8["phase"]])
    t = np.asarray(r8["t"], float)
    idx = np.flatnonzero(ph == "fault")
    if idx.size:
        return float(t[idx[0]]), "fault"
    prev = np.concatenate([np.array([""]), ph[:-1]])
    ready = np.flatnonzero((ph == "ready") & (prev != "ready"))
    return float(t[ready[-1]]), "last_ready"


def complex_amp(t, x, f, zeta):
    """x ~ a0 + a1 t + Re(A e^{(-s + i w) t}); returns complex A (amplitude at t[0])."""
    w = 2 * np.pi * f
    s = zeta * w
    tt = t - t[0]
    e = np.exp(-s * tt)
    B = np.column_stack([np.ones_like(tt), tt, e * np.cos(w * tt), e * np.sin(w * tt)])
    c = np.linalg.lstsq(B, x, rcond=None)[0]
    return complex(c[2], -c[3])


# ------------------------------------------------------------------ model helpers
def k_ax_variants(s):
    k_h = BETA * A_P / (L0H + s)
    k_r = BETA * A_ANN / (L0R + STROKE - s)
    ser = lambda k: 1.0 / (1.0 / k + 1.0 / K_ROD + 1.0 / K_FRAME + 1.0 / K_CONC)  # noqa: E731
    return {"h": ser(k_h), "b": ser(k_h + k_r)}, k_h, k_r


def assemble6(body, ext, kax, cax, klat, clat, F_pad):
    """6-DoF body, axial spring/dashpot at the attachment point (vertical), lateral at the pad bottom.
    Returns M, K, C, element list [(name, k-matrix, c-matrix)], geometric matrix."""
    M = dm.mass_6dof(body)
    K = np.zeros((6, 6))
    C = np.zeros((6, 6))
    elems = []
    Kg = np.zeros((6, 6))
    for i in range(4):
        d_att = np.array([*GEO.pad_xy[i], GEO.attach_z[i]]) - body.com
        d_pad = np.array([*GEO.pad_xy[i], GEO.pad_z_retracted[i] - ext[i]]) - body.com
        _, _, az = dm.a_vec(d_att)
        ax, ay, _ = dm.a_vec(d_pad)
        Ka = kax[i] * np.outer(az, az)
        Ca = cax[i] * np.outer(az, az)
        Kl = klat[i] * (np.outer(ax, ax) + np.outer(ay, ay))
        Cl = clat[i] * (np.outer(ax, ax) + np.outer(ay, ay))
        K += Ka + Kl
        C += Ca + Cl
        elems.append((f"axial {LEGS[i]}", Ka, Ca))
        elems.append((f"lateral {LEGS[i]}", Kl, Cl))
        Kg[3:, 3:] -= F_pad[i] * dm._hz(d_pad)
    K += Kg
    return M, K, C, elems, Kg


def modal_split(M, K, C, elems, Kg, band=(1.0, 5.0)):
    from scipy.linalg import eigh

    w2, Phi = eigh(K, M)
    fn_c, z_c = dm.complex_modes(M, K, C)
    rows = []
    for j in range(len(w2)):
        f = np.sqrt(max(w2[j], 0)) / (2 * np.pi)
        if not band[0] <= f <= band[1]:
            continue
        ph = Phi[:, j]
        w = 2 * np.pi * f
        U_tot = 0.5 * ph @ K @ ph  # = w^2 / 2 (mass-normalised)
        e_kin = ph * (M @ ph)
        e_kin = e_kin / e_kin.sum()
        shape = {dm.DOF6[k]: round(float(e_kin[k]), 3) for k in np.argsort(-e_kin)[:3] if e_kin[k] > 0.02}
        split = {}
        strain = {}
        for name, Ke, Ce in elems:
            split[name] = float(ph @ Ce @ ph / (2 * w))
            strain[name] = float(0.5 * ph @ Ke @ ph / U_tot)
        strain["geometric"] = float(0.5 * ph @ Kg @ ph / U_tot)
        k = int(np.argmin(np.abs(fn_c - f)))
        ax = sum(v for n, v in split.items() if n.startswith("axial"))
        la = sum(v for n, v in split.items() if n.startswith("lateral"))
        rows.append(dict(f_Hz=round(f, 4), f_damped_model_Hz=round(float(fn_c[k]), 4), zeta=round(float(z_c[k]), 5),
                         zeta_axial=round(ax, 5), zeta_lateral=round(la, 5), zeta_sum=round(ax + la, 5),
                         zeta_per_element={n: round(v, 5) for n, v in split.items()},
                         strain_share_axial=round(sum(v for n, v in strain.items() if n.startswith("axial")), 4),
                         strain_share_lateral=round(sum(v for n, v in strain.items() if n.startswith("lateral")), 4),
                         strain_share_geometric=round(strain["geometric"], 4),
                         strain_per_element={n: round(v, 4) for n, v in strain.items()}, shape=shape,
                         phi_roll_pitch_yaw=[round(float(v), 6) for v in ph[3:]],
                         phi_xyz=[round(float(v), 6) for v in ph[:3]]))
    return rows


def discrete_semi_implicit(M, K, C, dt, f_target):
    """Explicit forces from the state at t_n, v_{n+1} = v_n + dt M^-1 F_n, x_{n+1} = x_n + dt v_{n+1}."""
    n = M.shape[0]
    Mi = np.linalg.inv(M)
    A = np.block([[np.eye(n) - dt * dt * Mi @ K, dt * (np.eye(n) - dt * Mi @ C)],
                  [-dt * Mi @ K, np.eye(n) - dt * Mi @ C]])
    z = np.linalg.eigvals(A)
    lam = np.log(z.astype(complex)) / dt
    lam = lam[lam.imag > 0]
    wn = np.abs(lam)
    k = int(np.argmin(np.abs(wn / (2 * np.pi) - f_target)))
    return float(wn[k] / (2 * np.pi)), float(-lam[k].real / wn[k])


# ------------------------------------------------------------------ main
def record_part(case: Path):
    t0, kind = anchor_time(case)
    z = np.load(case / "pads.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    w = t >= t0 + 1.0
    t = t[w]
    F = np.asarray(z["F_cyl"], float)[w]
    s = np.asarray(z["s_link"], float)[w]
    pr = np.asarray(z["rod_pressure"], float)[w]
    ph = np.asarray(z["head_pressure"], float)[w]
    lat = np.asarray(z["lateral_force_world"], float)[w]
    roll, pitch = rp_from_quat(np.asarray(z["body_quat_wxyz"], float)[w])
    stuck = np.asarray(z["seal_stuck"], bool)[w]
    slide = np.asarray(z["sliding"], bool)[w]
    air = np.asarray(z["airborne"], bool)[w]
    fseal = np.asarray(z["f_seal"], float)[w]
    out = dict(case=case.name, anchor=kind, t0_s=round(t0, 3), window_s=[round(float(t[0]), 3), round(float(t[-1]), 3)],
               F_mean_kN=np.round(F.mean(0) / 1e3, 2).tolist(), sumF_mean_kN=round(float(F.sum(1).mean() / 1e3), 2),
               s_mean_m=np.round(s.mean(0), 5).tolist(),
               rod_p_bar_min_max=[[round(float(a) / 1e5, 2), round(float(b) / 1e5, 2)]
                                  for a, b in zip(pr.min(0), pr.max(0), strict=True)],
               head_p_bar_min_max=[[round(float(a) / 1e5, 1), round(float(b) / 1e5, 1)]
                                   for a, b in zip(ph.min(0), ph.max(0), strict=True)],
               seal_stuck_share=np.round(stuck.mean(0), 3).tolist(), pad_sliding_share=np.round(slide.mean(0), 4).tolist(),
               airborne_share=np.round(air.mean(0), 4).tolist(), f_seal_abs_max_N=np.round(np.abs(fseal).max(0), 1).tolist())
    # ESPRIT in consecutive 3 s windows
    tb, X = block_mean(t, np.column_stack([F / 1e3, np.degrees(roll), np.degrees(pitch)]), 0.005)
    names = [f"F_{n}" for n in LEGS] + ["roll", "pitch"]
    seq = []
    a = tb[0]
    while a + 3.0 <= tb[-1] + 1e-9:
        m = (tb >= a) & (tb < a + 3.0)
        row = dict(t_rel_s=round(float(a - t0), 1))
        for j, nm in enumerate(names):
            y = X[m, j] - np.polyval(np.polyfit(tb[m], X[m, j], 1), tb[m])
            d = dominant(y, 0.005)
            row[nm] = None if d is None else [round(d[0], 4), round(d[1], 5), round(d[2], 4)]
        seq.append(row)
        a += 3.0
    out["esprit_3s"] = seq
    first = seq[0]
    f0 = float(np.median([first[f"F_{n}"][0] for n in LEGS]))
    z0 = float(np.median([first[f"F_{n}"][1] for n in LEGS]))
    out["f0_Hz"], out["zeta0"] = round(f0, 4), round(z0, 5)
    # complex amplitudes over the first 3 s at full rate
    m = t < t[0] + 3.0
    tt = t[m]
    amp = {}
    for i, n in enumerate(LEGS):
        amp[f"F_{n}"] = complex_amp(tt, F[m, i], f0, z0)
        amp[f"s_{n}"] = complex_amp(tt, s[m, i], f0, z0)
        amp[f"latx_{n}"] = complex_amp(tt, lat[m, i, 0], f0, z0)
        amp[f"laty_{n}"] = complex_amp(tt, lat[m, i, 1], f0, z0)
    amp["roll"] = complex_amp(tt, roll[m], f0, z0)
    amp["pitch"] = complex_amp(tt, pitch[m], f0, z0)
    ref = amp["roll"]
    out["amplitudes_first3s"] = {k: [float(abs(v)), round(float(np.degrees(np.angle(v / ref))), 1)] for k, v in amp.items()}
    # secant stiffness: F vs (-s) on loading (F above mean) and unloading (below) halves
    ksec = {}
    for i, n in enumerate(LEGS):
        x = -(s[m, i] - s[m, i].mean())
        y = F[m, i] - F[m, i].mean()
        up, dn = y > 0, y <= 0
        ksec[n] = dict(all=float(np.polyfit(x, y, 1)[0]), loading=float(np.polyfit(x[up], y[up], 1)[0]),
                       unloading=float(np.polyfit(x[dn], y[dn], 1)[0]))
    out["k_secant_N_m"] = {n: {k: round(v, -3) for k, v in d.items()} for n, d in ksec.items()}
    # record energy split over the first 3 s
    wv = 2 * np.pi * f0
    ds = np.gradient(s[m], tt, axis=0)
    dlat = np.gradient(lat[m], tt, axis=0)  # (n,4,2)
    P_ax = (C_LOCK * ds ** 2).mean(0)
    P_lat = (C_LAT[:, None] * (dlat / K_LAT[None, :, None]) ** 2).sum(-1).mean(0)
    kk = np.array([ksec[n]["all"] for n in LEGS])
    # energies at the window start amplitudes, decayed average over the window: mean of e^{-2 s t}
    decay = float(np.mean(np.exp(-2 * z0 * wv * (tt - tt[0]))))
    E_ax = 0.5 * np.array([abs(amp[f"F_{n}"]) ** 2 / kk[i] for i, n in enumerate(LEGS)]) * decay
    E_lat = 0.5 * np.array([(abs(amp[f"latx_{n}"]) ** 2 + abs(amp[f"laty_{n}"]) ** 2) / K_LAT[i]
                            for i, n in enumerate(LEGS)]) * decay
    # raw-rate powers contain the NSC step noise; use the fitted harmonic for the budget, keep raw as record
    P_ax_raw, P_lat_raw = P_ax, P_lat
    P_ax = 0.5 * C_LOCK * wv ** 2 * np.array([abs(amp[f"s_{n}"]) ** 2 for n in LEGS]) * decay
    P_lat = 0.5 * C_LAT * wv ** 2 * np.array([(abs(amp[f"latx_{n}"]) ** 2 + abs(amp[f"laty_{n}"]) ** 2)
                                              for n in LEGS]) / K_LAT ** 2 * decay
    out["record_energy_first3s"] = dict(P_axial_raw_W=np.round(P_ax_raw, 2).tolist(),
                                        P_lateral_raw_W=np.round(P_lat_raw, 2).tolist(),
                                        P_axial_W=np.round(P_ax, 2).tolist(), P_lateral_W=np.round(P_lat, 2).tolist(),
                                        E_axial_J=np.round(E_ax, 2).tolist(), E_lateral_J=np.round(E_lat, 2).tolist())
    return out, dict(t0=t0, s_mean=s.mean(0), F_mean=F.mean(0), roll_amp=amp["roll"], pitch_amp=amp["pitch"],
                     P_ax=P_ax, P_lat=P_lat, E_ax=E_ax, E_lat=E_lat, f0=f0, ksec=kk, decay=decay)


def model_part(rec, level="top"):
    body = dm.body_from_params(P, level)
    ext = rec["s_mean"]
    F_pad = rec["F_mean"]
    kv, k_h, k_r = k_ax_variants(ext)
    variants = {"rec": rec["ksec"], "h": kv["h"], "b": kv["b"]}
    res = dict(k_h_oil=np.round(k_h, -3).tolist(), k_r_oil=np.round(k_r, -3).tolist(),
               k_ax={k: np.round(v, -3).tolist() for k, v in variants.items()},
               c_lock=C_LOCK.tolist(), k_lat=K_LAT.tolist(), c_lat_actual=C_LAT.tolist(),
               c_over_k_axial_s={k: np.round(C_LOCK / v, 6).tolist() for k, v in variants.items()},
               c_over_k_lateral_s=np.round(C_LAT / K_LAT, 6).tolist(), variants={})
    for name, kax in variants.items():
        M, K, C, elems, Kg = assemble6(body, ext, kax, C_LOCK, K_LAT, C_LAT, F_pad)
        rows = modal_split(M, K, C, elems, Kg)
        for r in rows:
            fd, zd = discrete_semi_implicit(M, K, C, DT_CHRONO, r["f_Hz"])
            r["discrete_dt1e-4"] = [round(fd, 4), round(zd, 5)]
            # what-if: lateral dashpots off / axial off / c sized for zeta_ref at this mode
        M0, K0, C0, el0, _ = assemble6(body, ext, kax, C_LOCK, K_LAT, np.zeros(4), F_pad)
        M1, K1, C1, el1, _ = assemble6(body, ext, kax, np.zeros(4), K_LAT, C_LAT, F_pad)
        fz0 = dm.complex_modes(M0, K0, C0)
        fz1 = dm.complex_modes(M1, K1, C1)
        for r in rows:
            k0 = int(np.argmin(np.abs(fz0[0] - r["f_Hz"])))
            k1 = int(np.argmin(np.abs(fz1[0] - r["f_Hz"])))
            r["zeta_lateral_c_off"] = round(float(fz0[1][k0]), 5)
            r["zeta_axial_c_off"] = round(float(fz1[1][k1]), 5)
        res["variants"][name] = rows
    # 10-DoF cross-check (rods as axial DoF, rigid floor), 'rec' stiffness
    M, K, C, labels, _ = dm.model_10dof(body, GEO, ext, rec["ksec"], np.full(4, 1e12), K_LAT, co=C_LOCK,
                                        cc=np.zeros(4), ch=C_LAT)
    fn, zt = dm.complex_modes(M, K, C)
    sel = (fn > 1.0) & (fn < 5.0)
    res["model10_rec_f_zeta"] = [[round(float(a), 4), round(float(b), 5)] for a, b in zip(fn[sel], zt[sel], strict=True)]
    return res, body


def record_zeta(rec, body):
    """zeta from the record energy split: P = 2 zeta w E, E = elastic - geometric (recorded roll/pitch)."""
    w = 2 * np.pi * rec["f0"]
    Kg = np.zeros((3, 3))
    for i in range(4):
        d_pad = np.array([*GEO.pad_xy[i], GEO.pad_z_retracted[i] - rec["s_mean"][i]]) - body.com
        Kg -= rec["F_mean"][i] * dm._hz(d_pad)
    th = np.array([rec["roll_amp"], rec["pitch_amp"], 0.0])
    E_geo = 0.5 * float(np.real(np.conj(th) @ Kg @ th))
    E_el = float(rec["E_ax"].sum() + rec["E_lat"].sum())
    E_geo *= rec["decay"]  # same window-average decay factor as the elastic energies
    E_tot = E_el + E_geo
    P = float(rec["P_ax"].sum() + rec["P_lat"].sum())
    return dict(E_elastic_J=round(E_el, 2), E_geometric_J=round(E_geo, 2), E_mode_J=round(E_tot, 2),
                P_total_W=round(P, 3), P_axial_share=round(float(rec["P_ax"].sum()) / P, 3),
                zeta_record_energy_no_geo=round(P / (2 * w * E_el), 5),
                zeta_record_energy=round(P / (2 * w * E_tot), 5))


def main():
    out = dict(meta=dict(script="04_scripts/01_dynamics/r65_lock_rocking_damping.py", zeta_ref=ZETA_REF,
                         f_ref_Hz=F_REF_HZ, beta_Pa=BETA, L0h_m=L0H, L0r_m=L0R, k_frame=K_FRAME, k_concrete=K_CONC,
                         note="c_lat = 2 x Chrono input (bushing damping acts at 2x); c_lock = YAML LOCK basis"),
               cases={})
    for arg in sys.argv[1:]:
        case = Path(arg)
        rj, rec = record_part(case)
        mres, body = model_part(rec)
        rj["record_zeta_energy"] = record_zeta(rec, body)
        out["cases"][case.name] = dict(record=rj, model=mres)
        print(f"== {case.name}  anchor {rj['anchor']} t0 {rj['t0_s']}  f0 {rj['f0_Hz']} Hz zeta0 {rj['zeta0']}")
        print("   F_mean kN", rj["F_mean_kN"], "sum", rj["sumF_mean_kN"], "s_mean", rj["s_mean_m"])
        print("   rod p bar", rj["rod_p_bar_min_max"], "head p bar", rj["head_p_bar_min_max"])
        print("   seal stuck", rj["seal_stuck_share"], "pad sliding", rj["pad_sliding_share"], "airborne",
              rj["airborne_share"], "|f_seal| max N", rj["f_seal_abs_max_N"])
        for row in rj["esprit_3s"]:
            print("   esprit", row)
        print("   amplitudes (abs, phase vs roll deg)",
              {k: (round(v[0], 6 if k in ('roll', 'pitch') or k.startswith('s_') else 1), v[1])
               for k, v in rj["amplitudes_first3s"].items()})
        print("   k_secant", rj["k_secant_N_m"])
        print("   record energy", rj["record_energy_first3s"], rj["record_zeta_energy"])
        print("   model k_ax", mres["k_ax"], "c/k ax", mres["c_over_k_axial_s"], "c/k lat", mres["c_over_k_lateral_s"])
        for vn, rows in mres["variants"].items():
            for r in rows:
                print(f"   model {vn:3s} f {r['f_Hz']} zeta {r['zeta']} (ax {r['zeta_axial']} lat {r['zeta_lateral']})"
                      f" disc {r['discrete_dt1e-4']} latoff {r['zeta_lateral_c_off']} axoff {r['zeta_axial_c_off']}"
                      f" strain ax/lat/geo {r['strain_share_axial']}/{r['strain_share_lateral']}/{r['strain_share_geometric']}"
                      f" shape {r['shape']} rpy {r['phi_roll_pitch_yaw']}")
        print("   model10 rec", mres["model10_rec_f_zeta"])
    OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
