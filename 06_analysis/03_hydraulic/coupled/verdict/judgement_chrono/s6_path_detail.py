"""S6 and S1 path detail: why first READY and maximum stroke differ between limit on and stored off (criteria 9.1, cause
study of the reduced-model mismatch). Reads the run folders only. Writes s6_path_detail.json.

Run: conda run -n dynamics-dev python -I s6_path_detail.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
HERE = ROOT / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono"
S9 = ROOT / "07_results/S9"
ON = S9 / "batch_COUPLED_eta085_20261104_142213"
CASES = {"S6": ("P3b_J2_B_top_Fs4_m1p1_t180", S9 / "batch_FINAL-REP-X_20261031_020716"),
         "S1": ("P3b_J1_B_top_Fs4", S9 / "batch_FINAL-REP_20261030_223359")}
OK_KEYS = ("ok_attitude", "ok_clearance", "ok_twist", "ok_loc", "ok_twist_strict", "on_target")


def spans(t, mask):
    edges = np.diff(np.concatenate(([0], mask.astype(int), [0])))
    return [[round(float(t[a]), 1), round(float(t[b - 1]), 1)] for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True)]


def side(path: Path) -> dict:
    res = json.loads((path / "result.json").read_text(encoding="utf-8"))
    t0 = float(res["t_loop_start_s"])
    with np.load(path / "completion_series.npz", allow_pickle=False) as z:
        comp = {k: np.asarray(z[k]) for k in z.files}
    with np.load(path / "step_series.npz", allow_pickle=False) as z:
        st = {k: np.asarray(z[k]) for k in ("t_s", "s_motor_m", "roll_pitch_deg", "scm_crawler_normal_N", "z_origin_m", "pad_sinkage_geometric_m")}
    with np.load(path / "controller_commands.npz", allow_pickle=False) as z:
        tc, u = np.asarray(z["t_s"]) - t0, np.asarray(z["issued_u_m_s"])
    tcomp = comp["t_s"] - t0
    t = st["t_s"] - t0
    phases = [(float(p["t_s"]) - t0, str(p["phase"]).lower()) for p in res["phases"]]
    first_done = next(x for x, n in phases if n == "done")
    events = [(float(e["t_s"]) - t0, str(e["name"])) for e in res["events"]]
    locs = [x for x, n in events if n == "crawler_liftoff_confirmed"]
    window = (tcomp >= locs[-1]) & (tcomp <= first_done + 0.05)
    gates = {k: spans(tcomp[window], comp[k][window].astype(bool)) for k in OK_KEYS if k in comp}
    dev = comp["deviation_rad"]
    dev_abs = np.abs(np.degrees(dev)).reshape(len(tcomp), -1).max(axis=1)
    out = {"phases": [[round(x, 2), n] for x, n in phases], "locs": [round(x, 2) for x in locs], "first_done_s": first_done, "gates_from_final_loc_to_first_done": gates}
    for name, tq in (("at_final_loc", locs[-1]), ("at_first_done", first_done)):
        k = min(int(np.searchsorted(t, tq)), len(t) - 1)
        kc = min(int(np.searchsorted(tcomp, tq)), len(tcomp) - 1)
        out[name] = {"s_motor_mm": (st["s_motor_m"][k] * 1e3).round(2).tolist(), "attitude_deg": st["roll_pitch_deg"][k].round(4).tolist(), "z_mm": float(st["z_origin_m"][k] * 1e3),
                     "sinkage_mm": (st["pad_sinkage_geometric_m"][k] * 1e3).round(2).tolist(), "clearance_filtered_mm": float(comp["clearance_filtered_m"][kc] * 1e3), "D_kN": float(comp["D_raw_N"][kc] / 1e3)}
    sel = (tc >= locs[0]) & (tc <= first_done)
    out["mean_u_loc_to_done_mm_s"] = (u[sel].mean(axis=0) * 1e3).round(3).tolist()
    ks = (t >= locs[-1]) & (t <= first_done)
    out["attitude_abs_max_loc_to_done_deg"] = np.abs(st["roll_pitch_deg"][ks]).max(axis=0).round(4).tolist()
    level = (tcomp >= locs[-1]) & (tcomp <= first_done)
    out["deviation_time_above_0p03_s"] = float((dev_abs[level] > 0.03).sum() * 0.1)
    out["deviation_last_above_0p03_rel_s"] = float(tcomp[level][np.flatnonzero(dev_abs[level] > 0.03)[-1]]) if (dev_abs[level] > 0.03).any() else None
    out["p3_1"] = (res.get("p3b") or {}).get("P3-1_recontact")
    out["stroke_reading_end_mm"] = None
    return out


out = {}
for cid, (case, off) in CASES.items():
    out[cid] = {"on": side(ON / case), "off": side(off / case)}
(HERE / "s6_path_detail.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
for cid, b in out.items():
    print("==", cid)
    for s in ("on", "off"):
        x = dict(b[s])
        p = x.pop("p3_1")
        print(s, json.dumps(x, ensure_ascii=False, default=float))
        print(" p3_1", json.dumps(p, ensure_ascii=False, default=float)[:900])
