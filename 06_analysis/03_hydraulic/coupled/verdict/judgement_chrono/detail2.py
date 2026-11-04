"""Follow-up detail for the interim verdict: R12 trigger timing, lift-off transient, setting checks,
reduced-model transient. Read only; writes detail2.json next to this file.

Run: conda run -n dynamics-dev python -I detail2.py
"""
from __future__ import annotations

import ctypes
import json
import sys
from ctypes import wintypes
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
HERE = ROOT / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono"
V = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "03_src"))
S8 = ROOT / "07_results/S8"
CASES = {
    "R2": "K24_top_fdown3.5_Fs4", "R4": "K24_top_roll5.5_Fs4", "R16": "G1L_RE1bF_FL_top_o050_Fs4",
    "R12": "E_G4_Fs4", "R6": "K0V_top_rpB_Fs0", "R8": "A_middle_rpB_Fs0", "R9": "A_bottom_rpB_Fs0",
}
LEGS = ("FL", "FR", "RL", "RR")
TWIST = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
K_NOM = 2.2705179e7


def pin(mask: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    kernel.SetProcessAffinityMask.restype = wintypes.BOOL
    if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), mask):
        raise OSError(ctypes.get_last_error(), "SetProcessAffinityMask")


def folder(prefix: str, case: str) -> Path:
    return sorted(S8.glob(f"{prefix}_{case}_2*"))[-1] / case


def load(prefix: str, case: str) -> dict:
    d = folder(prefix, case)
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    with np.load(d / "pads.npz", allow_pickle=False) as z:
        pads = {k: z[k] for k in ("t", "F_cyl", "F_cyl_min_interval", "airborne", "N")}
    with np.load(d / "r8_series.npz", allow_pickle=False) as z:
        r8 = {k: z[k] for k in z.files if k not in ("imu_samples", "imu_gyro_samples")}
    with np.load(d / "record" / "record.npz", allow_pickle=False) as z:
        rec = {k: z[k] for k in ("t", "F_crawler", "F_cyl")}
    offset = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    return {"res": res, "pads": pads, "r8": r8, "rec": rec, "offset": offset, "dir": d}


def r12_trace(on: dict, off: dict) -> dict:
    out = {}
    te = {"on": float(on["res"]["event_t_s"]), "off": float(off["res"]["event_t_s"])}
    table = []
    for k in np.arange(-5, 26):
        row = {"t_rel": round(k * 0.1, 1)}
        for name, s in (("on", on), ("off", off)):
            t8 = s["r8"]["t"] - s["offset"]
            j = int(np.argmin(np.abs(t8 - (te[name] + k * 0.1))))
            tp = s["pads"]["t"] - s["offset"]
            p = int(np.searchsorted(tp, t8[j]))
            row[name] = {"F_RR": round(float(s["pads"]["F_cyl"][p, 3]) / 1e3, 3),
                         "Fhat_RR": round(float(s["r8"]["F_hat_N"][j, 3]) / 1e3, 3),
                         "Flow_RR": round(float(s["r8"]["F_lower_N"][j, 3]) / 1e3, 3),
                         "Flow_est_RR": round(float(s["r8"]["F_lower_est_N"][j, 3]) / 1e3, 3),
                         "u_RR_mm_s": round(float(s["r8"]["issued_u"][j, 3]) * 1e3, 3),
                         "reapp_mm_s": round(float(s["r8"]["cmp_reapproach_u"][j, 3]) * 1e3, 3),
                         "phase": str(s["r8"]["phase"][j])}
        table.append(row)
    out["table"] = table
    grid = np.arange(-1.0, 3.0, 0.01)
    f = {}
    for name, s in (("on", on), ("off", off)):
        tp = s["pads"]["t"] - s["offset"] - te[name]
        f[name] = np.interp(grid, tp, s["pads"]["F_cyl"][:, 3]) / 1e3
    delta = f["on"] - f["off"]
    out["delta_F_RR_on_minus_off"] = {f"{g:+.2f}": round(float(delta[int(np.argmin(np.abs(grid - g)))]), 3)
                                      for g in (-1.0, -0.5, 0.0, 0.3, 0.6, 0.8, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.0)}
    # first order counterfactual: the off curve shifted by the pre-event offset, no trigger shift
    pre = float(delta[(grid >= -1.0) & (grid < 0.0)].mean())
    tp_off = off["pads"]["t"] - off["offset"] - te["off"]
    post = (tp_off >= 0) & (tp_off <= 20)
    out["pre_event_offset_kN"] = pre
    out["counterfactual_no_trigger_shift_min_kN"] = float(off["pads"]["F_cyl_min_interval"][post, 3].min() / 1e3 + pre)
    # load rate of the off curve around the minimum
    sel = (tp_off >= 1.2) & (tp_off <= 1.5)
    out["off_rate_kN_s_1p2_1p5"] = float(np.polyfit(tp_off[sel], off["pads"]["F_cyl"][sel, 3] / 1e3, 1)[0])
    # twist: deficit split and the closed form
    with np.load(on["dir"] / "flow_series.npz", allow_pickle=True) as z:
        rows, cols = z["rows"], [str(c) for c in z["columns"]]
    idx = {c: i for i, c in enumerate(cols)}
    d_end = rows[-1, [idx[f"deficit_integral_{leg}"] for leg in LEGS]]
    t_flow = rows[:, idx["t"]] - float(on["res"]["runner"]["start_t_s"])
    k20 = int(np.searchsorted(t_flow, 22.0))
    d_touch = rows[k20, [idx[f"deficit_integral_{leg}"] for leg in LEGS]]
    out["deficit_mm_after_touch"] = (d_touch * 1e3).round(4).tolist()
    out["deficit_mm_end"] = (d_end * 1e3).round(4).tolist()
    tau = float(TWIST @ (-(d_end - d_touch)))
    out["twist_from_level_deficit_mm"] = tau * 1e3
    out["dD_closed_form_kN_Sknom"] = tau * K_NOM / 1e3
    win = {}
    for name, s in (("on", on), ("off", off)):
        tp = s["pads"]["t"] - s["offset"]
        sel = (tp >= te[name] - 1) & (tp < te[name])
        win[name] = s["pads"]["F_cyl"][sel].mean(axis=0) / 1e3
    df = win["on"] - win["off"]
    dD = float(TWIST @ df)
    out["dF_pre_event_kN"] = df.round(3).tolist()
    out["dD_measured_kN"] = dD
    out["dF_twist_part_kN"] = (dD * TWIST).round(3).tolist()
    out["dF_residual_kN"] = (df - dD * TWIST).round(3).tolist()
    return out


def lift_transient(on: dict, off: dict, case_id: str) -> dict:
    res = {}
    for name, s in (("on", on), ("off", off)):
        tp = s["pads"]["t"] - s["offset"]
        phases = [p for p in s["res"]["phases"] if p[1] == "level"]
        touch_end = phases[0][0]
        rec_t = s["rec"]["t"] - s["offset"]
        fc = np.linalg.norm(s["rec"]["F_crawler"], axis=1) / 1e3
        k0 = int(np.argmax((rec_t > touch_end) & (fc < 1e-6)))
        t_zero = float(rec_t[k0])
        windows = {}
        f = s["pads"]["F_cyl_min_interval"] / 1e3
        for lab, a, b in (("-0.3..+0.5", t_zero - 0.3, t_zero + 0.5), ("0..+0.5", t_zero, t_zero + 0.5), ("+0.5..+8", t_zero + 0.5, t_zero + 8.0)):
            sel = (tp >= a) & (tp <= b)
            i = np.unravel_index(np.argmin(f[sel]), f[sel].shape)
            windows[lab] = {"min_kN": round(float(f[sel][i]), 3), "leg": LEGS[i[1]], "t_rel_s": round(float(tp[sel][i[0]] - t_zero), 3)}
        res[name] = {"touch_end_s": touch_end, "crawler_zero_at_10Hz_s": t_zero, "crawler_force_kN_at_samples": fc[k0 - 2: k0 + 2].round(3).tolist(), "windows": windows}
        sel = (tp >= t_zero - 0.3) & (tp <= t_zero + 0.4)
        res[name]["F_RL_kN_every_50ms"] = [[round(float(a - t_zero), 3), round(float(b), 2)] for a, b in
                                           zip(tp[sel][::50], s["pads"]["F_cyl"][sel, 2][::50] / 1e3, strict=True)]
    return res


def reduced_transient(cid: str) -> dict:
    out = {}
    for name, stem in (("on", f"A_{cid}_eta0.85"), ("off", f"OFF_{cid}")):
        j = json.loads((V / f"{stem}.json").read_text(encoding="utf-8"))
        val = j["values"]
        block = {"after_liftoff": val["forces"]["after_liftoff"], "first_8s": val["forces"].get("first_8s"), "after_8s": val["forces"].get("after_8s"),
                 "times": {k: v for k, v in val["times"].items() if "lift" in k or "ready" in k or "touch" in k or "loc" in k}}
        with np.load(V / f"{stem}.npz", allow_pickle=False) as z:
            files = list(z.files)
            block["npz_keys"] = files[:12]
            if "rows" in files and "true_force" in " ".join(files):
                pass
            if "rows" in files:
                rows = z["rows"]
                cols = None
                from importlib import import_module  # noqa: F401
                block["rows_shape"] = rows.shape
        out[name] = block
    return out


def checks() -> dict:
    out = {}
    for cid, case in CASES.items():
        on = json.loads((folder("coupled_eta085", case) / "result.json").read_text(encoding="utf-8"))
        off = json.loads((folder("final", case) / "result.json").read_text(encoding="utf-8"))
        so, sf = on["settings"], off["settings"]
        cfg_same = so.get("controller_config") == sf.get("controller_config")
        keys_diff = sorted(k for k in set(so) | set(sf) if so.get(k) != sf.get(k))
        out[cid] = {"controller_config_same": cfg_same, "settings_keys_differ": keys_diff,
                    "seed": [on.get("seed"), off.get("seed")], "flow": on["flow_limit"]["setting"],
                    "flow_enabled": on["flow_limit"]["enabled"], "tau_v_s": [so["bundle_c"].get("tau_v_s"), sf["bundle_c"].get("tau_v_s")],
                    "code": on["flow_limit"]["code_sha256"], "stopped": [on["s8_end"]["stopped_at_target"], off["s8_end"]["stopped_at_target"]],
                    "timeout": [on["s8_end"]["timeout"], off["s8_end"]["timeout"]],
                    "nonfinite": [on["monitor"]["nonfinite_steps"], off["monitor"]["nonfinite_steps"]]}
    return out


def main() -> None:
    pin(0x0C000000)
    report = {"checks": checks()}
    on12, off12 = load("coupled_eta085", CASES["R12"]), load("final", CASES["R12"])
    report["R12"] = r12_trace(on12, off12)
    report["lift"] = {}
    for cid in ("R4", "R6", "R8", "R9"):
        report["lift"][cid] = lift_transient(load("coupled_eta085", CASES[cid]), load("final", CASES[cid]), cid)
    report["reduced"] = {cid: reduced_transient(cid) for cid in ("R4", "R6", "R8", "R9", "R12")}
    (HERE / "detail2.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(json.dumps(report["checks"], default=str)[:3000])
    for row in report["R12"]["table"]:
        print(row["t_rel"], row["on"], "|", row["off"])
    print({k: v for k, v in report["R12"].items() if k != "table"})
    print(json.dumps(report["lift"], default=str)[:7000])
    print(json.dumps(report["reduced"], default=str)[:5000])


if __name__ == "__main__":
    main()
