"""Ed. 6 B3 dynamics judgement, part 2 (dynamics-expert, 2026-11-23, analysis only).

(a) Harness check of the rank-1 twist law on R12 VBJ (READY, all legs locked, floor sink only):
    pattern dF / n and the RR load per mm of floor sink (fit of the harness quintic
    D tau^3 (10 - 15 tau + 6 tau^2), D 11.5 mm, 2 s; rate_compare.py convention).
(b) Protection latency with d = 1 (10 Hz reads, command decided at read k acts on [k+1, k+2]):
    quasi-static rank-1 sim at 1 ms, worst start load sweep, required protect level / speed cap.
(c) R12: early start (B3) vs baseline on the 32 VBJ R12 rows, two estimates:
    G-shift superposition of the recorded twist response, and a mechanistic rank-1 model with
    the VBJ fill delays (extend 0.1 s, retract 0.7 s; A(ii) variants 0.4 / 0.1 s).
(d) Aliasing: rigid-body modes (3-DoF vertical and 6-DoF with pad lateral springs) aliased at
    10 Hz, minimum oscillation amplitude that fires R-5 on a steady mean load (rate_intervals 3,
    20 kN/s, horizon 4, P5 = F_min + 7.0 kN), and the recorded READY intra-period dips of all
    j9_main VBJ rows.
Inputs read only: YAML, j9_main T4h + jsonl of run 606f8713, ed6 b3_early_window.csv.
Writes one JSON (--out). stdout ASCII.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(r"C:\workspace\outrigger_control")
RUN = ROOT / r"06_analysis\02_control\j_p3_cause\j9_runs\606f8713\j9main_a1"
EW = ROOT / r"06_analysis\02_control\j_p3_cause\ed6_design\control_v6\b3_early_window.csv"
LEGS = ("FL", "FR", "RL", "RR")
T_S = 0.1
DT = 1e-3
V_MAX = 0.0209243016
V_TW = 0.25 * V_MAX
F_MIN = 9414.58911
PROTECT = F_MIN + 5000.0
P5 = F_MIN + 7000.0
D_SINK = 0.0115
RAMP = 2.0
N = np.array([0.476072, -0.476072, -0.522834, 0.522834])   # part 1, A^T n = 0
K_TW = {"lock": 29.233e6, "mixed": 24.911e6, "move": 21.702e6}   # part 1 (harness strokes)


def quintic(t):
    tau = np.clip(np.asarray(t, float) / RAMP, 0.0, 1.0)
    return D_SINK * tau**3 * (10.0 - 15.0 * tau + 6.0 * tau**2)


# ------------------------------------------------------------------ (a) harness pattern check
def pattern_check():
    z = np.load(RUN / "j9_main_t4h" / "R12_o0.0_VBJ.npz", allow_pickle=False)
    t, F = z["t_s"], z["true_force_N"]
    i0, i1 = np.searchsorted(t, 46.9 - 1e-9), np.searchsorted(t, 48.2 - 1e-9)
    dF = F[i1] - F[i0]
    ratio = dF / N
    # fit RR load per mm of sink: F_RR(t) = F0 - kf * quintic(t - t0), t in [46.9, 48.2]
    sel = (t >= 46.9 - 1e-9) & (t <= 48.2 + 1e-9)
    best = None
    for t0 in np.arange(46.6, 47.2, 0.005):
        q = quintic(t[sel] - t0)
        y = F[sel, 3] - F[i0, 3]
        kf = -float(q @ y / (q @ q)) if q @ q > 0 else 0.0
        r = float(np.sqrt(np.mean((y + kf * q) ** 2)))
        if best is None or r < best[2]:
            best = (float(t0), kf, r)
    return {"dF_46.9_to_48.2_kN": (dF / 1e3).round(2).tolist(),
            "dF_over_n_kN": (ratio / 1e3).round(1).tolist(),
            "spread_of_dF_over_n_pct": round(float((ratio.max() - ratio.min()) / abs(ratio.mean()) * 100), 1),
            "fit_RR": {"t0_s": round(best[0], 3), "kN_per_mm": round(best[1] / 1e6, 3),
                       "rms_kN": round(best[2] / 1e3, 3)},
            "rank1_lock_prediction_kN_per_mm": round(K_TW["lock"] * N[3] ** 2 / 1e6, 3)}


# ------------------------------------------------------------------ (b) protection latency
def protect_sim(F0_p, k_tw, n_p_abs, protect_N, frac=1.0, ext_delay=0.0, ret_delay=0.0,
                max_periods=5, cap_m=0.065 * 0.04, valve_tau=0.0):
    """Quasi-static: protected leg p loses k_tw |n_p| (n^T ds); fastest leg at frac V_TW.
    Reads every 0.1 s; decision at read k drives [t_{k+1}, t_{k+2}] (d = 1). B3 decided at
    read 0 (the R-5 read). Ext legs move after ext_delay from their first nonzero output,
    retract legs after ret_delay. Returns min load and periods run."""
    F0 = np.atleast_1d(np.asarray(F0_p, float))
    nmax = np.abs(N).max()
    speed = frac * V_TW * np.abs(N) / nmax          # per-leg speed magnitude (twist vector)
    ext = np.array([True, False, False, True])        # RR twist: FL, RR extend
    per = int(round(T_S / DT))
    n_steps = (max_periods + 4) * per
    F = F0.copy()
    travel_fast = np.zeros_like(F)
    decisions = np.zeros((max_periods + 4, F.size), bool)
    out_start = np.full(F.size, np.nan)
    F_min_seen = F.copy()
    allowed = np.ones(F.size, bool)
    vel = np.zeros((F.size, 4))
    for k in range(n_steps):
        t = k * DT
        if k % per == 0:                               # read
            m = k // per
            if m < max_periods:
                allowed = allowed & (travel_fast < cap_m) & (F >= protect_N)
            else:
                allowed = np.zeros(F.size, bool)
            decisions[m] = allowed
        m_out = k // per - 1                           # decision acting now (d = 1)
        on = decisions[m_out] if m_out >= 0 else np.zeros(F.size, bool)
        newly = on & np.isnan(out_start)
        out_start[newly] = t
        s_since = np.where(on, t - np.nan_to_num(out_start), -1.0)
        mv = np.where(ext[None, :], s_since[:, None] >= ext_delay, s_since[:, None] >= ret_delay)
        target = np.where(mv & on[:, None], speed[None, :], 0.0)
        if valve_tau > 0:
            vel = vel + (target - vel) * DT / valve_tau
        else:
            vel = target
        nTds = (vel @ np.abs(N)) * DT                  # all legs move along +/- n
        F = F - k_tw * n_p_abs * nTds
        travel_fast = travel_fast + vel.max(axis=1) * DT
        F_min_seen = np.minimum(F_min_seen, F)
    if np.ndim(F0_p) == 0:
        return float(F_min_seen[0]), int(decisions[:, 0].sum())
    return F_min_seen, decisions.sum(axis=0)


def protection():
    out = {}
    n_p = abs(N[2])   # rear protected leg (RL for an RR twist) has the larger |n|
    cases = {"rigid_move_all": dict(k_tw=K_TW["move"]),
             "rigid_move_beta1.6": dict(k_tw=32.698e6),
             "rigid_vbj_fill_ext0.1_ret0.7": dict(k_tw=K_TW["mixed"], ext_delay=0.1, ret_delay=0.7),
             "rigid_move_valve_tau20ms": dict(k_tw=K_TW["move"], valve_tau=0.02),
             "soil_J1_elastic": dict(k_tw=9.159e6),
             "rigid_deck_kd_1e8": dict(k_tw=17.832e6)}
    for name, kw in cases.items():
        grid = np.arange(PROTECT, PROTECT + 60e3, 100.0)
        fm, npr = protect_sim(grid, n_p_abs=n_p, protect_N=PROTECT, **kw)
        iw = int(np.argmin(fm))
        worst = (grid[iw], float(fm[iw]), int(npr[iw]))
        # false-R-5 exposure from typical protected loads, no protection hit
        expo = {}
        for F0 in (30e3, 45e3, 60e3, 72e3, 112e3):
            for per in (4, 5):
                fmin, nper = protect_sim(F0, n_p_abs=n_p, protect_N=PROTECT, max_periods=per,
                                         cap_m=1.0, **kw)
                expo[f"F0_{F0/1e3:.0f}kN_{per}per"] = round(fmin / 1e3, 2)
        out[name] = {"worst_start_kN": round(worst[0] / 1e3, 2), "worst_min_kN": round(worst[1] / 1e3, 2),
                     "periods_run": worst[2], "exposure_min_kN": expo}
    # required protect level (all moving rigid) and speed cap for the 5 kN margin
    req = {}
    for name, k_tw in (("move", K_TW["move"]), ("beta1.6", 32.698e6)):
        for target, lab in ((0.0, "no_lift"), (F_MIN, "keep_F_min")):
            lo, hi = PROTECT, PROTECT + 80e3
            for _ in range(30):
                mid = 0.5 * (lo + hi)
                w = float(protect_sim(np.arange(mid, mid + 40e3, 100.0), k_tw, n_p, mid)[0].min())
                lo, hi = (mid, hi) if w < target else (lo, mid)
            req[f"{name}_{lab}_protect_level_kN"] = round(hi / 1e3, 2)
            lo, hi = 0.0, 1.0
            for _ in range(30):
                mid = 0.5 * (lo + hi)
                w = float(protect_sim(np.arange(PROTECT, PROTECT + 40e3, 100.0), k_tw, n_p, PROTECT,
                                      frac=mid)[0].min())
                lo, hi = (mid, hi) if w >= target else (lo, mid)
            req[f"{name}_{lab}_speed_fraction_of_0.25vmax"] = round(lo, 4)
            req[f"{name}_{lab}_fastest_mm_s"] = round(lo * V_TW * 1e3, 3)
    out["required"] = req
    return out


# ------------------------------------------------------------------ (c) R12 early start
def r12_rows():
    rows = {}
    with open(EW, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["key"]] = r
    res = []
    prot_at_r5 = []
    for key, r in rows.items():
        z = np.load(RUN / "j9_main_t4h" / f"{key}_VBJ.npz", allow_pickle=False)
        t, F, Fm = z["t_s"], z["true_force_N"], z["true_force_min_N"]
        j = LEGS.index(r["r5_leg"])
        t_ev, t_r5, t_ra = float(r["t_event_s"]), float(r["t_relevel_predicted_s"]), float(r["t_reapproach_start_s"])
        sgn = np.sign(N[j])
        prot = [i for i in range(4) if np.sign(N[i]) != sgn]
        i5 = int(np.searchsorted(t, t_r5 - 1e-9))
        prot_at_r5.append(float(F[i5, prot].min()))
        t_c = t_ra + T_S
        sel = (t >= t_ev - 1e-9) & (t <= t_c + 1e-9)
        i0 = int(np.searchsorted(t, t_ev - 1e-9))
        best = None
        for t0 in np.arange(t_ev - 0.3, t_ev + 0.4, 0.005):
            q = quintic(t[sel] - t0)
            y = F[sel, j] - F[i0, j]
            if q @ q <= 0:
                continue
            kf = -float(q @ y / (q @ q))
            rr = float(np.sqrt(np.mean((y + kf * q) ** 2)))
            if best is None or rr < best[2]:
                best = (t0, kf, rr)
        t0, kf, rms = best

        def floor(tt):
            return F[i0, j] - kf * quintic(np.asarray(tt) - t0)
        # G-shift
        tg = t[t >= t_c - 1e-9]
        G_inst = F[t >= t_c - 1e-9, j] - floor(tg)
        G_min = Fm[t >= t_c - 1e-9, j] - floor(tg)
        tau = tg - t_c
        shift = t_ra - t_r5
        t_c3 = t_c - shift
        win = (tau <= 2.0)
        base_min = float(np.min(Fm[(t >= t_c - 1e-9) & (t <= t_c + 2.0), j]))
        b3_inst = floor(t_c3 + tau[win]) + G_inst[win]
        b3_min = floor(t_c3 + tau[win]) + G_min[win]
        pre = (t >= t_ev) & (t < t_c3 - 1e-9)
        b3_min_all = min(float(np.min(b3_min)), float(np.min(Fm[pre, j])) if pre.any() else math.inf)
        # mechanistic rank-1
        mech = {}
        nmax = float(np.abs(N).max())
        s_ext = float(np.sum(N[[i for i in range(4) if i not in prot]] ** 2)) / nmax
        s_ret = float(np.sum(N[prot] ** 2)) / nmax
        tt = np.arange(t_ev, t_c + 2.5, DT)
        dd = np.diff(quintic(tt - t0), prepend=quintic(tt[0] - t0))
        for lab, (de, drr) in {"vbj": (0.1, 0.7), "aii_0.4": (0.1, 0.4), "aii_0.1": (0.1, 0.1),
                               "nofill": (0.0, 0.0)}.items():
            vals = []
            for tc in (t_c, t_c3):
                s_since = tt - tc
                ext_on = s_since >= de
                ret_on = s_since >= drr
                ktw = np.where(ext_on & ret_on, K_TW["move"],
                               np.where(ext_on | ret_on, K_TW["mixed"], K_TW["lock"]))
                nTv = V_TW * (ext_on * s_ext + ret_on * s_ret)
                dF = ktw * abs(N[j]) * nTv * DT - ktw * N[j] ** 2 * dd
                Fj = F[i0, j] + np.cumsum(dF)
                vals.append(float(Fj.min()) / 1e3)
            mech[lab] = {"base_kN": round(vals[0], 2), "b3_kN": round(vals[1], 2),
                         "gain_kN": round(vals[1] - vals[0], 2)}
        res.append({"key": key, "leg": r["r5_leg"], "shift_s": round(shift, 2),
                    "fit_kN_per_mm": round(kf / 1e6, 3), "fit_rms_kN": round(rms / 1e3, 3),
                    "base_min_kN": round(base_min / 1e3, 2), "gshift_b3_min_kN": round(b3_min_all / 1e3, 2),
                    "gshift_gain_kN": round((b3_min_all - base_min) / 1e3, 2), "mech": mech})
    g = np.array([x["gshift_gain_kN"] for x in res])
    b3 = np.array([x["gshift_b3_min_kN"] for x in res])
    summ = {"n": len(res), "gshift_gain_kN_min_med_max": [float(g.min()), float(np.median(g)), float(g.max())],
            "gshift_b3_min_kN_min_med_max": [float(b3.min()), float(np.median(b3)), float(b3.max())],
            "base_min_kN_min_med_max": [float(min(x["base_min_kN"] for x in res)),
                                        float(np.median([x["base_min_kN"] for x in res])),
                                        float(max(x["base_min_kN"] for x in res))],
            "b3_rows_below_F_min_gshift": int(np.sum(b3 < F_MIN / 1e3)),
            "protected_min_load_at_r5_kN_min_med": [round(min(prot_at_r5) / 1e3, 2),
                                                     round(float(np.median(prot_at_r5)) / 1e3, 2)]}
    for lab in ("vbj", "aii_0.4", "aii_0.1", "nofill"):
        gg = np.array([x["mech"][lab]["gain_kN"] for x in res])
        bb = np.array([x["mech"][lab]["b3_kN"] for x in res])
        ba = np.array([x["mech"][lab]["base_kN"] for x in res])
        summ[f"mech_{lab}"] = {"base_min_med_max": [float(ba.min()), float(np.median(ba)), float(ba.max())],
                               "b3_min_med_max": [float(bb.min()), float(np.median(bb)), float(bb.max())],
                               "gain_min_med_max": [float(gg.min()), float(np.median(gg)), float(gg.max())]}
    return {"summary": summ, "rows": res}


# ------------------------------------------------------------------ (d) aliasing
def modes(p, level="top"):
    lv = p["superstructure"]["auger_levels"][level]
    m = float(lv["mass_kg"])
    com = np.array(lv["com_m"])
    I = np.array(lv["inertia_kg_m2"])
    der = p["contact"]["rigid_floor"]["L1"]["derivation"]
    kz = np.array([der["k_lock_N_m"][g] for g in LEGS])
    kt = np.array([p["contact"]["rigid_floor"]["L1"]["kt_per_pad_N_m"][g] for g in LEGS])
    xy = np.array([[p["legs"][g]["cylinder_axis_xy_m"][1], p["legs"][g]["cylinder_axis_xy_m"][0]] for g in LEGS])
    zc = float(p["ground"]["crawler_bottom_z_m"])     # contact at the floor (crawler lifted 50 mm)
    out = {}
    # 3-DoF vertical: q = (z, phi, theta) about com
    r = xy - com[:2]
    Jv = np.column_stack([np.ones(4), r[:, 1], -r[:, 0]])
    K3 = Jv.T @ np.diag(kz) @ Jv
    M3 = np.diag([m, I[0, 0], I[1, 1]])
    M3[1, 2] = M3[2, 1] = I[0, 1]
    w2 = np.sort(np.linalg.eigvals(np.linalg.solve(M3, K3)).real)
    out["3dof_Hz"] = (np.sqrt(w2) / 2 / math.pi).round(3).tolist()
    # 6-DoF small motion: point i velocity = v + w x r_i
    K6 = np.zeros((6, 6))
    for i in range(4):
        ri = np.array([xy[i, 0], xy[i, 1], zc]) - com
        Rx = np.array([[0, ri[2], -ri[1]], [-ri[2], 0, ri[0]], [ri[1], -ri[0], 0]])   # d = v - r x w
        Ji = np.hstack([np.eye(3), Rx])
        Ki = np.diag([kt[i], kt[i], kz[i]])
        K6 += Ji.T @ Ki @ Ji
    M6 = np.zeros((6, 6))
    M6[:3, :3] = m * np.eye(3)
    M6[3:, 3:] = I
    ev, vec = np.linalg.eig(np.linalg.solve(M6, K6))
    order = np.argsort(ev.real)
    f6 = np.sqrt(ev.real[order]) / 2 / math.pi
    out["6dof_Hz"] = f6.round(3).tolist()
    out["alias_10Hz_Hz"] = {f"{f:.3f}": round(abs(f - 10.0 * round(f / 10.0)), 3) for f in list(f6) + [8.88]}
    return out


def r5_fires(y):
    d = (y[0] - y[3]) / 3.0
    return (d / T_S > 20e3) and (y[2] > y[3]) and (y[3] - 4.0 * d < P5)


def alias_threshold():
    """Minimum amplitude (at the window's first read) of a damped sinusoid on a steady mean
    load that fires R-5 for some phase."""
    out = {}
    for f, zeta in ((8.88, 0.03), (8.88, 0.10), (4.0, 0.016), (6.0, 0.02), (1.12, 0.03)):
        wn = 2 * math.pi * f
        sig = zeta * wn
        wd = wn * math.sqrt(1 - zeta**2)
        tk = np.arange(4) * T_S
        row = {}
        for Fbar in (20e3, 30e3, 45e3, 60e3, 72e3, 116e3):
            amin = math.inf
            for phi in np.linspace(0, 2 * math.pi, 721):
                shape = np.exp(-sig * tk) * np.cos(wd * tk + phi)
                lo, hi = 0.0, 300e3
                if not r5_fires(Fbar + hi * shape):
                    continue
                for _ in range(50):
                    mid = 0.5 * (lo + hi)
                    lo, hi = (lo, mid) if r5_fires(Fbar + mid * shape) else (mid, hi)
                amin = min(amin, hi)
            row[f"mean_{Fbar/1e3:.0f}kN"] = None if math.isinf(amin) else round(amin / 1e3, 2)
        out[f"f{f}_zeta{zeta}"] = row
    return out


def recorded_ready_dips():
    """All j9_main VBJ rows: in READY, max (F(t_k) - min over (t_k-1, t_k]) per leg = intra-period
    dip (>= 2 a for a mode near 10 Hz), and the R-5 surrogate on the 10 Hz true force."""
    dips = []
    fires = []
    drop_rates = []
    for line in open(RUN / "j9_main.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if d["job"]["setting"] != "VBJ":
            continue
        z = np.load(RUN / "j9_main_t4h" / d["t4h_file"], allow_pickle=False)
        t, F, Fm, ph = z["t_s"], z["true_force_N"], z["true_force_min_N"], z["phase"]
        rd = ph == "ready"
        if not rd.any():
            continue
        dip = np.nanmax(np.where(rd[:, None], F - Fm, np.nan))
        dips.append((d["t4h_file"], float(dip)))
        idx = np.flatnonzero(rd)
        for i in idx:
            if i < 3 or not rd[i - 3:i + 1].all():
                continue
            for leg in range(4):
                y = F[i - 3:i + 1, leg]
                drop_rates.append((float((y[0] - y[3]) / 3 / T_S), d["t4h_file"], float(t[i]), leg))
                if r5_fires(y):
                    fires.append((d["t4h_file"], float(t[i]), LEGS[leg]))
    dips.sort(key=lambda x: -x[1])
    drop_rates.sort(key=lambda x: -x[0])
    return {"rows": len(dips), "max_ready_dip_kN_top5": [(a, round(b / 1e3, 3)) for a, b in dips[:5]],
            "median_ready_dip_kN": round(float(np.median([b for _, b in dips])) / 1e3, 3),
            "surrogate_r5_fires_true_force": fires[:40], "n_surrogate_fires": len(fires),
            "top_drop_rates_kN_s_nonR12R14": [(round(a / 1e3, 2), f, round(tt, 2), LEGS[l])
                                              for a, f, tt, l in drop_rates
                                              if not (f.startswith("R12") or f.startswith("R14"))][:8]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    p = yaml.safe_load((ROOT / "02_params" / "rexome33.yaml").read_text(encoding="utf-8"))
    out = {"pattern_check": pattern_check(), "protection": protection(), "r12": r12_rows(),
           "modes": {lv: modes(p, lv) for lv in ("top", "middle", "bottom")},
           "alias_threshold": alias_threshold(), "recorded_ready": recorded_ready_dips()}
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
