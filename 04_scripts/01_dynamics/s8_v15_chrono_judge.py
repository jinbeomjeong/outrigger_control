"""S8 V15 Chrono batch: dynamics-expert ruling support (dynamics_model.md rev. 42).

Reads the batch records only (no Chrono run, no state change) and writes
``06_analysis/00_dynamics/s8/s8_v15_chrono_judge.json``.

Questions:
 1. RL net reading at lift-off sits ~0.45 kN under the reference for every F_s > 0: split the
    difference into the true force part and the friction part, and test the band-edge ratchet
    explanation (high-frequency rod-force noise keeps a near-edge Coulomb element inside the
    band by about the noise amplitude; the deficit is then F_s independent).
 2. "All legs sliding at lift-off": stuck fraction vs creep (net piston slip in the expected
    direction) and time since the last slip step.
 3. Ledger: where the residual R accrues (dt 1e-4 vs 1e-5 windows), and whether it equals the
    recorded D_visc (explicit lagged dashpot work vs NSC contact dissipation).
 4. D_f vs the reduced-model reference.

Run (Chrono-dev, numpy only): python -I s8_v15_chrono_judge.py
Conventions: legs FL FR RL RR, compression +, f + pushes the piston outward, G = F - f.
Units SI inside, mm / kN in names only.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "07_results" / "S8" / "v15_20261025_132215"
REF = ROOT / "06_analysis" / "00_dynamics" / "s8_v15_reference.json"
DYN = ROOT / "06_analysis" / "00_dynamics" / "s8_v15_dynamic_check.json"
OUT = ROOT / "06_analysis" / "00_dynamics" / "s8" / "s8_v15_chrono_judge.json"
LEGS = ("FL", "FR", "RL", "RR")
SIGN = np.array([-1.0, -1.0, -1.0, 1.0])  # expected friction sign at lift-off (5.26.2)
REAR = 0.8333
W = 20  # 20 ms centred mean (judge rule)


def mmean(a: np.ndarray, w: int) -> np.ndarray:
    a = np.asarray(a, float)
    flat = a.reshape(a.shape[0], -1)
    c = np.vstack([np.zeros((1, flat.shape[1])), np.cumsum(flat, axis=0)])
    n = flat.shape[0]
    lo = np.clip(np.arange(n) - w // 2, 0, n)
    hi = np.clip(np.arange(n) - w // 2 + w, 0, n)
    return ((c[hi] - c[lo]) / (hi - lo)[:, None]).reshape(a.shape)


def limits(fs: float) -> np.ndarray:
    return np.array([fs, fs, REAR * fs, REAR * fs])


def case_a(cid: str, fs: float, ref: dict) -> dict:
    z = np.load(BATCH / cid / "series.npz")
    res = json.loads((BATCH / cid / "result.json").read_text(encoding="utf-8"))
    tl = res["timeline"]
    t = z["t_s"]
    m = t >= tl["motion_start_t_s"]
    t, lam = t[m], z["lam_m"][m]
    F, f, G, N = (z[k][m] for k in ("F_N", "f_N", "Fp_N", "N_N"))
    stuck, sp, dt = z["stuck_frac"][m], z["s_p_m"][m], z["dt_s"][m]
    Nmin = z["N_min_N"][m]
    lim = limits(fs) if fs > 0 else np.zeros(4)
    Ns = mmean(N, W)
    k = int(np.flatnonzero(Ns[:, 2] <= 0.0)[0])  # RL lift-off (smoothed, judge rule)
    out: dict = {"t_liftoff_s": float(t[k]), "lam_liftoff_mm": 1e3 * float(lam[k])}
    out["identity_max_abs_G_minus_F_plus_f_N"] = float(np.max(np.abs(G - (F - f))))
    # high-frequency rod-force noise (1 ms block level; per-step noise is larger)
    hf = F - mmean(F, W)
    out["windows"] = {}
    for name, lo, hi in (("lam 9.0-10.0 mm", 9.0, 10.0), ("lam 10.0-10.8 mm", 10.0, 10.8),
                         ("lam 10.8 mm - lift-off-0.1 mm", 10.8, out["lam_liftoff_mm"] - 0.1),
                         ("last 0.1 mm before lift-off", out["lam_liftoff_mm"] - 0.1,
                          out["lam_liftoff_mm"])):
        sel = (1e3 * lam >= lo) & (1e3 * lam < hi)
        if not np.any(sel):
            continue
        row = {"n_blocks": int(sel.sum()), "dt_s": sorted({float(x) for x in dt[sel]}),
               "hf_rod_force_std_1ms_N": np.std(hf[sel], axis=0).round(1).tolist(),
               "mean_contact_N": np.mean(N[sel], axis=0).round(0).tolist(),
               "stuck_fraction_mean": np.mean(stuck[sel], axis=0).round(4).tolist()}
        if fs > 0:
            deficit = lim - SIGN * f[sel]  # distance of f from the expected band edge
            row["edge_deficit_mean_N"] = np.mean(deficit, axis=0).round(1).tolist()
            row["edge_deficit_p05_N"] = np.percentile(deficit, 5, axis=0).round(1).tolist()
            # piston slip in the window [um] (expected direction = sign of slip with f)
            dsp = 1e6 * (sp[sel][-1] - sp[sel][0])
            row["piston_net_slip_um"] = dsp.round(3).tolist()
        out["windows"][name] = row
    # time since the last block with a slip step, at lift-off
    if fs > 0:
        last = []
        for i in range(4):
            idx = np.flatnonzero(stuck[: k + 1, i] < 1.0)
            last.append(None if idx.size == 0 else float(t[k] - t[idx[-1]]))
        out["time_since_last_slip_at_liftoff_s"] = last
    # reading decomposition at lift-off (judge values, 20 ms mean, interpolated)
    ra = ref["at_liftoff"]
    j = res["judge"]["metrics"]["at_liftoff"]
    g, fl, tr = j["net_N"][2], j["f_N"][2], j["true_N"][2]
    out["RL_at_liftoff"] = {
        "G_N": g, "G_ref_N": ra["net_reading_N (G = F - f)"], "diff_N": g - ra["net_reading_N (G = F - f)"],
        "true_part_N (F - F_ref)": tr - ra["true_cyl_force_N (= -m_rod g)"],
        "friction_part_N (-(f - f_ref))": -(fl - ra["friction_N"]),
        "upper_bound_F_s_minus_mg_N": lim[2] + tr if fs > 0 else tr,
        "G_minus_upper_bound_N": g - (lim[2] + tr) if fs > 0 else 0.0,
    }
    # block-level minimum contact in the last 0.2 s before lift-off (intermittency)
    sel = (t > t[k] - 0.2) & (t <= t[k])
    out["RL_blocks_with_zero_contact_min_last_0p2s"] = int(np.sum(Nmin[sel, 2] <= 0.0))
    out["RL_blocks_last_0p2s"] = int(sel.sum())
    # ledger: residual accrual split by dt regime
    cols = ("E_kin_J", "E_grav_J", "U_lat_J", "U_ax_J", "D_visc_J", "D_f_J", "W_m_J", "W_L_J",
            "W_res_J", "W_switch_J")
    L = {c: z[c][m] for c in cols}
    ok = np.isfinite(L["E_kin_J"])
    e = L["E_kin_J"] + L["E_grav_J"] + L["U_lat_J"] + L["U_ax_J"]
    r = np.full(t.shape, np.nan)
    i0 = int(np.flatnonzero(ok)[0])
    r[ok] = ((e - e[i0]) + (L["D_visc_J"] - L["D_visc_J"][i0]) + (L["D_f_J"] - L["D_f_J"][i0])
             - (L["W_m_J"] - L["W_m_J"][i0]) - (L["W_L_J"] - L["W_L_J"][i0])
             - (L["W_res_J"] - L["W_res_J"][i0]) - (L["W_switch_J"] - L["W_switch_J"][i0]))[ok]
    dv = L["D_visc_J"] - L["D_visc_J"][i0]
    coarse = ok & (dt > 5e-5)
    fine = ok & (dt < 5e-5)
    ic = np.flatnonzero(coarse)
    jf = np.flatnonzero(fine)
    out["ledger"] = {
        "R_end_J": float(r[ok][-1]), "D_visc_end_J": float(dv[ok][-1]),
        "R_minus_Dvisc_end_J": float(r[ok][-1] - dv[ok][-1]),
        "max_abs_R_minus_Dvisc_J": float(np.nanmax(np.abs(r[ok] - dv[ok]))),
        "Dvisc_rate_coarse_W": float((dv[ic[-1]] - dv[ic[0]]) / (t[ic[-1]] - t[ic[0]])),
        "Dvisc_rate_fine_W": (float((dv[jf[-1]] - dv[jf[0]]) / (t[jf[-1]] - t[jf[0]]))
                              if jf.size > 2 else None),
        "Dvisc_in_fine_window_J": float(dv[jf[-1]] - dv[jf[0]]) if jf.size > 2 else None,
        "fine_window_s": float(t[jf[-1]] - t[jf[0]]) if jf.size > 2 else None,
    }
    return out


def case_b(cid: str, fs: float) -> dict:
    z = np.load(BATCH / cid / "series.npz")
    res = json.loads((BATCH / cid / "result.json").read_text(encoding="utf-8"))
    tl = res["timeline"]
    t = z["t_s"]
    f = z["f_N"]
    lim = limits(fs) if fs > 0 else np.zeros(4)
    out = {}
    for name, a, b in (("hold before motion", tl["motion_start_t_s"] - 1.0, tl["motion_start_t_s"]),
                       ("outbound 50-100 s", 50.0, 100.0), ("return 150-200 s", 150.0, 200.0),
                       ("final hold last 1 s", tl["end_t_s"] - 1.0, tl["end_t_s"])):
        sel = (t >= a) & (t <= b)
        hf = z["F_N"] - mmean(z["F_N"], W)
        row = {"hf_rod_force_std_1ms_N": np.std(hf[sel], axis=0).round(1).tolist(),
               "stuck_fraction_mean": np.mean(z["stuck_frac"][sel], axis=0).round(4).tolist(),
               "f_mean_N": np.mean(f[sel], axis=0).round(1).tolist()}
        if fs > 0:
            row["edge_deficit_mean_N"] = (lim - np.abs(np.mean(f[sel], axis=0))).round(1).tolist()
        out[name] = row
    dv = z["D_visc_J"]
    ok = np.isfinite(dv)
    tt = t[ok]
    out["Dvisc_rate_W"] = float((dv[ok][-1] - dv[ok][0]) / (tt[-1] - tt[0]))
    return out


def main() -> None:
    ref = json.loads(REF.read_text(encoding="utf-8"))["V15_rev39"]["rod_side"]
    dyn = json.loads(DYN.read_text(encoding="utf-8"))
    out: dict = {"source": str(BATCH.relative_to(ROOT)), "cases": {}}
    for cid, fs in (("V15a_L0", 0.0), ("V15a_L2", 2000.0), ("V15a_L4", 4000.0),
                    ("V15a_L8", 8000.0), ("V15a_L8_v005", 8000.0)):
        r = ref["a_upsweep_unilateral"][f"L{int(fs / 1000)}"]
        out["cases"][cid] = case_a(cid, fs, r)
    for cid, fs in (("V15b_L0", 0.0), ("V15b_L4", 4000.0), ("V15b_L8", 8000.0)):
        out["cases"][cid] = case_b(cid, fs)
    # D_f vs reduced model (time-domain check, rod_side, 0.1 mm/s, 1e-4 s)
    summ = json.loads((BATCH / "v15_summary.json").read_text(encoding="utf-8"))["cases"]
    dfs = {}
    for cid, c in summ.items():
        if "v005" in cid or c.get("D_f_J", 0.0) == 0.0:
            continue
        kind, lv = cid[3], float(cid.split("_L")[1]) * 1000.0  # "V15a_L2" -> "a", 2000
        rr = [x for x in dyn["runs"] if x["variant"] == "rod_side" and x["kind"] == kind
              and abs(x["F_s_front_N"] - lv) < 1 and abs(x["u_m_s"] - 1e-4) < 1e-12
              and abs(x["dt_s"] - 1e-4) < 1e-12]
        if rr:
            d_ref = rr[0]["ledger"]["D_f_J"]
            dfs[cid] = {"chrono_J": c["D_f_J"], "reduced_J": d_ref,
                        "rel": c["D_f_J"] / d_ref - 1.0}
    out["D_f"] = dfs
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
