"""Which final-controller additions would act on a recorded Chrono S9 run (record only, no re-run).

Moved 2026-10-30 unchanged from session scratchpad ctrl-final/feature_scan.py (paths are arguments).

Per case: SGS any_loc (P36sa: a lift-stroke guard period after a confirmed LOC), SGS soil-sign (P36s), P37t
(re-approach contact after a LOC), R4 (soil mode used before the LOC and settle tilt <= 1 deg), ZIC c 0.5 (P38z:
reconstructed PI integral clamp after the first LOC up to the first READY; 1 kHz true attitude -> 100 Hz box means ->
2 x tau 0.8 s -> 10 Hz PI, joint band (0.01, 0.2) deg, |I| <= 0.02, reset at the LEVEL start). L1gs / DSb come from
control-fix/final_ctrl_offline.py (run separately). Output JSON lines + a summary.

Usage: python -I feature_scan.py <out_json> <case_dir> [<case_dir> ...]
"""
import json, math, sys
from pathlib import Path
import numpy as np

KP, KI = 0.2, 0.01
BAND = (math.radians(0.01), math.radians(0.2))
ILIM = 0.02
CAP = 0.5 * math.radians(0.03) * KP / KI


def lowpass(x, tau, n, T):
    a = T / tau
    st = [x[0].copy() for _ in range(n)]
    out = np.empty_like(x)
    out[0] = x[0]
    for k in range(1, len(x)):
        inp = x[k]
        for s in st:
            s += a * (inp - s)
            inp = s
        out[k] = inp
    return out


def zic_scan(case: Path, r: dict, locs: list, t_level0: float, t_ready: float | None):
    with np.load(case / "step_series.npz") as z:
        ts = np.asarray(z["t_s"]); rp = np.radians(np.asarray(z["roll_pitch_deg"]))
    with np.load(case / "r8_series.npz", allow_pickle=True) as z:
        t10 = np.asarray(z["t"]); ph = np.array([str(p) for p in z["phase"]])
    n100 = len(ts) // 10
    t100 = ts[9:n100 * 10:10]
    att = lowpass(rp[:n100 * 10].reshape(n100, 10, 2).mean(axis=1), 0.8, 2, 0.01)
    idx = np.clip(np.searchsorted(t100, t10 - 1e-9), 0, n100 - 1)
    I = np.zeros(2); clamps = []
    t_end = t_ready if t_ready is not None else 1e9
    for k, t in enumerate(t10):
        p = ph[k].lower()
        if t < t_level0 - 1e-9:
            I[:] = 0.0
            continue
        if "level" not in p:
            continue
        e = -att[idx[k]]
        jn = np.abs(e).max()
        for ax in range(2):
            if BAND[0] < abs(e[ax]) and jn < BAND[1]:
                I[ax] = np.clip(I[ax] + e[ax] * 0.1, -ILIM, ILIM)
        if locs and locs[0] - 1e-9 <= t < t_end:
            for ax in range(2):
                if e[ax] != 0 and np.sign(I[ax]) != np.sign(e[ax]) and abs(I[ax]) > CAP:
                    clamps.append((round(float(t), 2), ax, round(float(I[ax]), 5)))
                    I[ax] = np.sign(I[ax]) * CAP
    return clamps


def scan(case: Path) -> dict:
    r = json.loads((case / "result.json").read_text("utf-8"))
    ev = [(float(e["t_s"]), e["name"]) for e in r.get("events") or []]
    ph = [(float(p["t_s"]), p["phase"]) for p in r.get("phases") or []]
    locs = [t for t, n in ev if n == "crawler_liftoff_confirmed"]
    out = {"case": f"{case.parent.name}/{case.name}", "loc": bool(locs)}
    t_level0 = next((t for t, n in ph if n == "level"), None)
    t_ready = next((t for t, n in ph if n == "ready"), None)
    cs = r.get("code_state") or {}
    out["code_state"] = cs.get("state")
    out["imu_grade"] = (r.get("args") or {}).get("imu_grade")
    guard = [t for t, n in ev if n.startswith("WARN_LIFT_STROKE_LIMITED")]
    soil = r.get("c2_soil") or {}
    out["guard_after_loc"] = bool(locs and any(t >= locs[0] for t in guard))
    settle = soil.get("settle_attitude_rad") or [0.0, 0.0]
    tilt = max(abs(settle[0]), abs(settle[1]))
    soil_start = [t for t, n in ev if n == "soil_mode_start"]
    c_tp = soil.get("clearance_at_P_m")
    sign = bool(locs) and (bool(soil_start and soil_start[0] < locs[-1]) or
                           (c_tp is not None and c_tp > 0.010 and tilt > math.radians(1.0)))
    out["soil_sign"] = sign
    out["SGS_P36s"] = bool(out["guard_after_loc"] and sign)
    out["SGS_P36sa"] = out["guard_after_loc"]
    contacts = [t for t, n in ev if n.startswith("leg_reapproach_contact") or n.startswith("fault_reground_contact")]
    out["P37t_candidate"] = bool(locs and any(t > locs[0] for t in contacts))
    out["R4"] = bool(locs and soil_start and soil_start[0] < locs[-1] and tilt <= math.radians(1.0))
    out["n_guard"] = len(guard)
    if t_level0 is not None and (case / "step_series.npz").exists() and (case / "r8_series.npz").exists():
        cl = zic_scan(case, r, locs, t_level0, t_ready)
        out["ZIC_clamps"] = len(cl)
        out["ZIC_first"] = cl[:2]
    else:
        out["ZIC_clamps"] = None
    return out


if __name__ == "__main__":
    out_path = Path(sys.argv[1])
    rows = []
    for p in sys.argv[2:]:
        try:
            o = scan(Path(p))
        except Exception as exc:  # report and continue
            o = {"case": p, "error": repr(exc)}
        rows.append(o)
        print(json.dumps(o, ensure_ascii=False), flush=True)
    out_path.write_text(json.dumps(rows, indent=1, ensure_ascii=False), "utf-8")
