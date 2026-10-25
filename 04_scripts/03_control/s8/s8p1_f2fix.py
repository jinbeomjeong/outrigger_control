"""Recompute F2 with the spec-199 lower bound F_hat - F_band (per leg) and the F1 pattern.

Truth F = 1 ms rod-axis force at the 10 Hz sample instant (same as verify/s8_control.py).
Also report F_lower_N (controller last_forces.lower) - F_hat to show it is not band-subtracted.
"""
import sys, os, json, numpy as np

base = sys.argv[1]
v = json.load(open(os.path.join(base, "verify_S8C.json"), encoding="utf-8"))
times = {m["case"]: m["times_s"] for m in v["metrics"]}
out = {}
for name in sorted(os.listdir(base)):
    d = os.path.join(base, name)
    if not os.path.isdir(d):
        continue
    res = json.load(open(os.path.join(d, "result.json"), encoding="utf-8"))
    st = res["settings"]
    pads = np.load(os.path.join(d, "pads.npz"))
    r8 = np.load(os.path.join(d, "r8_series.npz"))
    tm = times[name]
    t0 = tm["t0"]
    tp = pads["t"]
    t = r8["t"]
    idx = np.clip(np.searchsorted(tp, t - 1e-9), 0, tp.size - 1)
    F = pads["F_cyl"][idx]
    f_seal = pads["f_seal"][idx]
    Fhat = r8["F_hat_N"]
    band = r8["leg_band_N"]
    if not np.isfinite(band).any():
        band = np.repeat(r8["F_band_N"][:, None], 4, axis=1)
    low_ctrl = r8["F_lower_N"]
    low_spec = Fhat - band
    lo = tm.get("liftoff")
    after = (t - t0) >= (lo if lo is not None else np.inf)
    share = 600.0 if st.get("grade") == "wika" or "wika" in name else 100.0
    exc_spec = (low_spec - F)[after]
    exc_ctrl = (low_ctrl - F)[after]
    eps = Fhat - F
    ph = r8["phase"]
    rec = {
        "ctrl_lower_minus_Fhat_kN": [float(np.nanmin(low_ctrl - Fhat)) / 1e3, float(np.nanmax(low_ctrl - Fhat)) / 1e3],
        "F2_ctrl_max_kN": float(np.nanmax(exc_ctrl)) / 1e3,
        "F2_spec_max_kN": float(np.nanmax(exc_spec)) / 1e3,
        "F2_spec_viol": int(np.sum(exc_spec > share + 1.0)),
        "band_min_after_kN": float(np.nanmin(band[after])) / 1e3,
        "eps_plus_f_maxabs_kN": float(np.nanmax(np.abs((eps + f_seal)[after]))) / 1e3,
    }
    # F1 by phase after the zero calibration (phase != check)
    post = ph != "check"
    rec["F1_maxabs_eps_postcheck_kN"] = float(np.nanmax(np.abs(eps[post]))) / 1e3
    rec["F1_eps_plus_f_postcheck_kN"] = [float(np.nanmin((eps + f_seal)[post])) / 1e3, float(np.nanmax((eps + f_seal)[post])) / 1e3]
    out[name] = rec
for k, r in out.items():
    print(f"{k:26s} ctrl_low-Fhat[{r['ctrl_lower_minus_Fhat_kN'][0]:.2f},{r['ctrl_lower_minus_Fhat_kN'][1]:.2f}] "
          f"F2ctrl {r['F2_ctrl_max_kN']:.2f}  F2spec {r['F2_spec_max_kN']:.2f} viol {r['F2_spec_viol']}  "
          f"band_min {r['band_min_after_kN']:.2f}  |eps+f| {r['eps_plus_f_maxabs_kN']:.2f}  "
          f"post-check eps+f [{r['F1_eps_plus_f_postcheck_kN'][0]:.2f},{r['F1_eps_plus_f_postcheck_kN'][1]:.2f}]")
json.dump(out, open(sys.argv[2], "w"), indent=1)
