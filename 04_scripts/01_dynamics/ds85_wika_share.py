"""D-S8-5 (1): WIKA normal-grade + zero calibration -- decompose the near-F_min reading error.

Spec s6_control_spec.md rev. 43 213.3.4 / rev. 44 214.5 (question 2-a), U70 / U71.
Reading model (sensors/pressure_error.py, sensors/hydraulic.py), per leg i:

    F_hat = (p_h + e_h(p_h) + n_h) A_p - (p_r + e_r(p_r) + n_r) A_ann = F - f + E_s + n
    F_cal = F_hat - c_i,      r = F_cal - (F - f) = E_s(t) - c_i + n(t)
    c_i   = (F_e + F_r)/2 + m_rod g  = c_sens + c_fric + c_noise
            c_sens  = mean of E_s over the two CHECK holds
            c_fric  = -(mean f_e + mean f_r)/2 + (mean F_e + mean F_r)/2 + m_rod g   (ideal sensor)
    => r = [E_s(t) - c_sens] - c_fric + [n(t) - c_noise]

E_s from the drawn terms in result.json (runner.sensors.pressure_error_terms), true gauge pressures
from pads.npz at the 10 Hz control rows. Areas fitted from pads (F_pressure = p_h A_p - p_r A_ann).
Bands: 'verdict' F in [F_min - 5, F_min + 10] kN, 'script' F in [-5, +10] kN (s8p1r_f1.py),
'air' = no pad contact and F < 0.5 kN.

Monte Carlo (seed 20261024): N_MC draws of the normal-grade terms (uniform, spec 71 table, +-4 bar
clip), same pressure states as the record, noise sigma 0.20 bar per sensor; per run the max over
the band rows of |dE_s + n - c_noise| -> distribution of the run maximum per leg and over 4 legs.

Usage: python -I ds85_wika_share.py <out json> <case dir> [<case dir> ...]
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, r"C:\workspace\outrigger_control\03_src")
from outrigger_sim.sensors.pressure_error import (  # noqa: E402
    PressureErrorTerms, draw_unit_terms, error_terms_from_unit)

F_MIN = 9414.59
FS_N = 8000.0  # F_s of the WIKA cases (front; rear 0.8333 F_s)
ROD_W = np.array([1047.2, 1047.2, 718.0, 718.0])
SIGMA_P = 0.20e5
N_MC = 20000
RNG = np.random.default_rng(20261024)
LEGS = ("FL", "FR", "RL", "RR")


def terms_from_meta(meta):
    arr = {k: np.zeros((2, 4)) for k in ("offset_Pa", "gain", "nonlinearity_Pa",
                                          "temperature_offset_Pa", "temperature_gain")}
    for s, side in enumerate(("head", "rod")):
        for i, leg in enumerate(LEGS):
            for k in arr:
                arr[k][s, i] = meta[f"{side}:{leg}"][k]
    return arr


def static_error(arr, side, leg, p):
    t = PressureErrorTerms(arr["offset_Pa"][side, leg], arr["gain"][side, leg],
                           arr["nonlinearity_Pa"][side, leg], arr["temperature_offset_Pa"][side, leg],
                           arr["temperature_gain"][side, leg], 4.0e5)
    return t.error_Pa(p)


def hold_rows(t8, u, leg, ph):
    """Rows of the two calibration holds (zero command after a move, 1.0 s, inclusive)."""
    k_chk = np.flatnonzero(ph == "check")
    seg = []
    for k in k_chk:
        s = np.sign(round(u[k, leg] * 1e6))
        if not seg or seg[-1][0] != s:
            seg.append([s, k])
    starts = [k for s, k in seg[1:] if s == 0]
    rows = []
    for k0 in starts[:2]:
        rows.append([k for k in k_chk if t8[k0] - 1e-9 <= t8[k] <= t8[k0] + 1.0 + 1e-9])
    return rows


def analyse(d):
    with open(os.path.join(d, "result.json"), encoding="utf-8") as fh:
        res = json.load(fh)
    pads = np.load(os.path.join(d, "pads.npz"))
    r8 = np.load(os.path.join(d, "r8_series.npz"))
    terms = res["runner"]["sensors"].get("pressure_error_terms")
    zc = res["controller_meta"]["zero_calibration"]
    c_i = np.array(zc["offsets_N"])
    t8, ph = r8["t"], r8["phase"]
    u = r8[os.environ.get("DS85_U", "computed_u")]
    tp = pads["t"]
    idx = np.clip(np.searchsorted(tp, t8 - 1e-9), 0, tp.size - 1)
    F = pads["F_cyl"][idx]
    f = pads["f_seal"][idx]
    p_h = pads["head_pressure"][idx]
    p_r = pads["rod_pressure"][idx]
    N = pads["N_raw"][idx] if "N_raw" in pads.files else None
    air = pads["airborne"][idx]
    A = []
    for leg in range(4):
        X = np.c_[pads["head_pressure"][:, leg], -pads["rod_pressure"][:, leg]]
        A.append(np.linalg.lstsq(X, pads["F_pressure"][:, leg], rcond=None)[0])
    A = np.array(A)
    arr = terms_from_meta(terms) if terms else None
    Es = np.zeros_like(F)
    if arr is not None:
        for leg in range(4):
            Es[:, leg] = (static_error(arr, 0, leg, p_h[:, leg]) * A[leg, 0]
                          - static_error(arr, 1, leg, p_r[:, leg]) * A[leg, 1])
    F_hat = r8["F_hat_N"]
    F_cal = r8["F_nominal_N"] if "F_nominal_N" in r8.files else F_hat - c_i[None, :]
    post = t8 > zc["result"]["t_end_s"] + 1e-9
    out = {"case": os.path.basename(d), "areas_m2": A.tolist(), "legs": {}}
    sig_F = SIGMA_P * np.hypot(A[:, 0], A[:, 1])
    for leg in range(4):
        hr = hold_rows(t8, u, leg, ph)
        he, hrr = hr
        Fe = F_hat[he, leg].mean()
        Fr = F_hat[hrr, leg].mean()
        c_rebuilt = 0.5 * (Fe + Fr) + ROD_W[leg]
        ideal = F - f
        c_fric = 0.5 * (ideal[he, leg].mean() + ideal[hrr, leg].mean()) + ROD_W[leg]
        c_sens = 0.5 * (Es[he, leg].mean() + Es[hrr, leg].mean())
        n_res = (F_hat - (F - f) - Es)[:, leg]  # noise (+ quantisation) per row
        c_noise = 0.5 * (n_res[he].mean() + n_res[hrr].mean())
        r = F_cal[:, leg] - (F[:, leg] - f[:, leg])
        dE = Es[:, leg] - c_sens
        bands = {
            "verdict": post & (F[:, leg] >= F_MIN - 5e3) & (F[:, leg] <= F_MIN + 10e3),
            "script": post & (F[:, leg] >= -5e3) & (F[:, leg] <= 10e3),
            "air": post & air[:, leg] & (F[:, leg] < 500.0),
            "all": post & (ph != "check"),
        }
        L = {"c_i_N": c_i[leg], "c_rebuilt_N": c_rebuilt, "c_sens_N": c_sens, "c_fric_N": c_fric,
             "c_noise_N": c_noise, "sigma_noise_N": float(np.std(n_res[post])),
             "sigma_noise_model_N": float(sig_F[leg]),
             "hold_p_bar": {"E": [float(p_h[he, leg].mean() / 1e5), float(p_r[he, leg].mean() / 1e5)],
                            "R": [float(p_h[hrr, leg].mean() / 1e5), float(p_r[hrr, leg].mean() / 1e5)]},
             "hold_rows": [len(he), len(hrr)], "bands": {}}
        for name, m in bands.items():
            if not m.any():
                L["bands"][name] = None
                continue
            k = np.flatnonzero(m)[np.argmax(np.abs(r[m]))]
            L["bands"][name] = {
                "n": int(m.sum()),
                "max_abs_r_N": float(abs(r[k])), "r_N": float(r[k]), "t_s": float(t8[k]), "phase": str(ph[k]),
                "F_N": float(F[k, leg]), "dE_N": float(dE[k]), "minus_c_fric_N": float(-c_fric),
                "noise_N": float(n_res[k] - c_noise),
                "p_bar": [float(p_h[k, leg] / 1e5), float(p_r[k, leg] / 1e5)],
                "dE_range_N": [float(dE[m].min()), float(dE[m].max())],
                "p_h_range_bar": [float(p_h[m, leg].min() / 1e5), float(p_h[m, leg].max() / 1e5)],
                "p_r_range_bar": [float(p_r[m, leg].min() / 1e5), float(p_r[m, leg].max() / 1e5)],
                "max_abs_r_without_fric_N": float(np.abs(r[m] + c_fric).max()),
                "max_abs_static_part_N": float(np.abs(dE[m]).max()),
                "rows_p": np.c_[p_h[m, leg], p_r[m, leg]].tolist(),
                "rows_Ff": np.c_[F[m, leg], f[m, leg]].tolist(), "c_fric_N": float(c_fric),
                "hold_p": [np.c_[p_h[he, leg], p_r[he, leg]].tolist(), np.c_[p_h[hrr, leg], p_r[hrr, leg]].tolist()],
            }
        out["legs"][LEGS[leg]] = L
    return out, A


def monte_carlo(case_out, A, band):
    """Run-max of |dE + n - c_noise| for random normal-grade terms on the recorded states."""
    res = {}
    run_max_all = np.zeros(N_MC)
    static_all = np.zeros(N_MC)
    f1_all = np.full(N_MC, -np.inf)
    fric_all = np.zeros(N_MC)
    for leg, name in enumerate(LEGS):
        b = case_out["legs"][name]["bands"].get(band)
        if not b:
            continue
        rows = np.array(b["rows_p"])
        he, hrr = (np.array(x) for x in b["hold_p"])
        if os.environ.get("DS85_FLAT_ROD"):
            # counterfactual: retract hold without the rod-side pressure rise (rod = extend-hold value)
            hrr = hrr.copy()
            hrr[:, 1] = he[:, 1].mean()
        unit = draw_unit_terms(RNG, (N_MC, 2))  # (N_MC, side, 7)
        terms = error_terms_from_unit(unit, "normal")

        def E(side, p):  # (N_MC, n_rows)
            t = PressureErrorTerms(terms.offset_Pa[:, side, None], terms.gain[:, side, None],
                                   terms.nonlinearity_Pa[:, side, None],
                                   terms.temperature_offset_Pa[:, side, None],
                                   terms.temperature_gain[:, side, None], 4.0e5)
            return t.error_Pa(p[None, :])

        def Ef(ph_, pr_):
            return E(0, ph_) * A[leg, 0] - E(1, pr_) * A[leg, 1]

        c_sens = 0.5 * (Ef(he[:, 0], he[:, 1]).mean(axis=1) + Ef(hrr[:, 0], hrr[:, 1]).mean(axis=1))
        dE = Ef(rows[:, 0], rows[:, 1]) - c_sens[:, None]
        sig = SIGMA_P * np.hypot(A[leg, 0], A[leg, 1])
        noise = RNG.normal(0.0, sig, dE.shape)
        n_cal = RNG.normal(0.0, sig / np.sqrt(len(he) + len(hrr)), (N_MC, 1))  # mean of 2 holds
        tot = np.abs(dE + noise - n_cal).max(axis=1)
        Ff = np.array(b["rows_Ff"])
        fs_leg = FS_N * (1.0 if leg < 2 else 0.8333)
        rr = dE + noise - n_cal - b["c_fric_N"]
        with_fric = np.abs(rr).max(axis=1)
        f1_need = (np.abs(rr - Ff[None, :, 1]) - fs_leg - 0.025 * np.abs(Ff[None, :, 0])).max(axis=1)
        f1_all = np.maximum(f1_all, f1_need)
        fric_all = np.maximum(fric_all, with_fric)
        stat = np.abs(dE).max(axis=1)
        run_max_all = np.maximum(run_max_all, tot)
        static_all = np.maximum(static_all, stat)
        q = lambda x: {p: float(np.percentile(x, p)) for p in (50, 90, 95, 99)} | {"max": float(x.max())}
        res[name] = {"n_rows": int(rows.shape[0]), "sigma_N": float(sig), "static_only": q(stat), "with_noise": q(tot),
                     "with_noise_and_c_fric": q(with_fric), "F1_const_needed": q(f1_need)}
    q = lambda x: {p: float(np.percentile(x, p)) for p in (50, 90, 95, 99)} | {"max": float(x.max())}
    res["all_legs"] = {"static_only": q(static_all), "with_noise": q(run_max_all),
                        "with_noise_and_c_fric": q(fric_all), "F1_const_needed": q(f1_all),
                        "P_fail_F1_const": {str(c): float((f1_all > c).mean()) for c in (600.0, 850.0, 1000.0, 1300.0, 1500.0)},
                        "P_exceed_near": {str(c): float((fric_all > c).mean()) for c in (600.0, 850.0, 1000.0, 1300.0)}}
    return res


def main():
    out_path = sys.argv[1]
    report = {"seed": 20261024, "N_MC": N_MC, "sigma_p_bar": SIGMA_P / 1e5, "cases": []}
    for d in sys.argv[2:]:
        case_out, A = analyse(d)
        case_out["mc"] = {b: monte_carlo(case_out, A, b) for b in ("verdict", "script", "air", "all")}
        for L in case_out["legs"].values():
            for b in L["bands"].values():
                if b:
                    b.pop("rows_p"), b.pop("hold_p"), b.pop("rows_Ff")
        report["cases"].append(case_out)
        print("==", case_out["case"])
        for name, L in case_out["legs"].items():
            print(f" {name}: c_i {L['c_i_N']:+8.1f} rebuilt {L['c_rebuilt_N']:+8.1f} = sens {L['c_sens_N']:+8.1f}"
                  f" + fric {L['c_fric_N']:+7.1f} + noise {L['c_noise_N']:+6.1f} | sigma n {L['sigma_noise_N']:.0f}"
                  f" (model {L['sigma_noise_model_N']:.0f}) holds E {L['hold_p_bar']['E']} R {L['hold_p_bar']['R']}")
            for bn, b in L["bands"].items():
                if b:
                    print(f"    {bn:7s} n {b['n']:4d} max|r| {b['max_abs_r_N']:7.1f} (r {b['r_N']:+7.1f} = dE {b['dE_N']:+7.1f}"
                          f" - c_fric {b['minus_c_fric_N']:+7.1f} + n {b['noise_N']:+6.1f}) t {b['t_s']:.1f} {b['phase']}"
                          f" F {b['F_N'] / 1e3:6.2f} kN p {b['p_bar'][0]:.1f}/{b['p_bar'][1]:.1f} bar"
                          f" | max|static| {b['max_abs_static_part_N']:.0f} max|r+c_fric| {b['max_abs_r_without_fric_N']:.0f}"
                          f" p_h {b['p_h_range_bar'][0]:.1f}..{b['p_h_range_bar'][1]:.1f} p_r {b['p_r_range_bar'][0]:.1f}..{b['p_r_range_bar'][1]:.1f}")
        for bn, mc in case_out["mc"].items():
            a = mc["all_legs"]
            print(f"  MC {bn:7s} 4-leg run max: static p50 {a['static_only'][50]:.0f} p95 {a['static_only'][95]:.0f}"
                  f" max {a['static_only']['max']:.0f} | +noise p50 {a['with_noise'][50]:.0f} p95 {a['with_noise'][95]:.0f}"
                  f" p99 {a['with_noise'][99]:.0f} max {a['with_noise']['max']:.0f} | +noise+c_fric p50 {a['with_noise_and_c_fric'][50]:.0f}"
                  f" p95 {a['with_noise_and_c_fric'][95]:.0f} p99 {a['with_noise_and_c_fric'][99]:.0f} N")
            print(f"      F1 const needed p50 {a['F1_const_needed'][50]:.0f} p95 {a['F1_const_needed'][95]:.0f} p99 {a['F1_const_needed'][99]:.0f}"
                  f" | P_fail {a['P_fail_F1_const']} | P_near {a['P_exceed_near']}")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, default=float)
    print("wrote", out_path)


if __name__ == "__main__":
    main()
