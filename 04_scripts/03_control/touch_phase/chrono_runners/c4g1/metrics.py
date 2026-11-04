"""C4G1 Chrono values against the flow-off pairs. Same definitions as dF_cause/decompose.py chrono() and cad_asym/analyze.py. No judgement.

Usage:
  python -I -B -X utf8 metrics.py expected              -> touch_phase/chrono/expected_before_run.json
  python -I -B -X utf8 metrics.py rigid <stamp>         -> judge + touch_phase/chrono/c4g1_rigid_values.json
  python -I -B -X utf8 metrics.py s7 <run dir>          -> touch_phase/chrono/c4g1_s7_values.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WT = HERE / "wt"
MAIN = Path(r"C:\workspace\outrigger_control")
S8 = MAIN / "07_results" / "S8"
OUT = MAIN / "06_analysis/02_control/touch_phase/chrono"
ASYM = HERE.parent / "cad_asym" / "runs" / "batch_164123"
LEGS = ("FL", "FR", "RL", "RR")
N = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
K_NOM_KN_MM = 6.679788447853166 / 0.2941966802395609
"""Harness R4 row D_hat / delta_tau (rows_C4G1_compare.json); only for the expected target below."""
F_MIN_KN = 9.41458911
T_CUT = 40.0
"""The R9 gap pair runs stop here (relative time), so one window ends here for all rigid rows."""
RIGID = {"R9_mirror2_d000": ("A_bottom_rpB_Fs0", ASYM / "mirror2_d000"), "R9_mirror2_d035": ("A_bottom_rpB_Fs0", ASYM / "mirror2_d035"),
         "R9_sym": ("A_bottom_rpB_Fs0", S8 / "final_A_bottom_rpB_Fs0_20261031_011936/A_bottom_rpB_Fs0"),
         "R4": ("K24_top_roll5.5_Fs4", S8 / "final_K24_top_roll5.5_Fs4_20261030_230357/K24_top_roll5.5_Fs4")}
S7_OFF = MAIN / "07_results/S9/batch_FINAL-REP_20261030_223359/S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0"


def attitude_deg(q) -> list[float]:
    w, x, y, z = q
    return [float(np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))), float(np.degrees(np.arcsin(2 * (w * y - z * x))))]


def rigid_metrics(d: Path) -> dict:
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    p = np.load(d / "pads.npz", allow_pickle=False)
    rec = np.load(d / "record/record.npz", allow_pickle=False)
    r8 = np.load(d / "r8_series.npz", allow_pickle=False)
    off = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    t, F, Fm, s = p["t"] - off, p["F_cyl"] / 1e3, p["F_cyl_min_interval"] / 1e3, p["s_motor"] * 1e3
    crt, crf = rec["t"] - off, np.linalg.norm(rec["F_crawler"], axis=1) / 1e3
    pt = r8["t"] - off
    te = float(pt[np.flatnonzero(~np.isin(r8["phase"], ("idle", "check", "touch")))[0]])
    W = float(np.median(F[(t > te - 8) & (t < te - 6)].sum(axis=1)) + np.median(crf[(crt > te - 8) & (crt < te - 6)]))
    sm = np.convolve(F.sum(axis=1), np.ones(20) / 20, "same")
    tl = float(t[np.flatnonzero((t > te) & (W - sm < 3.0))[0]])
    tz = float(crt[(crf == 0.0) & (crt > te)][0])
    ke, kl, kz = int(np.searchsorted(t, te)), int(np.searchsorted(t, tl)), int(np.searchsorted(t, tz))
    k8, kcut = int(np.searchsorted(t, tl + 8.0)), int(np.searchsorted(t, T_CUT))

    def leg_min(a, b) -> dict:
        return {leg: float(Fm[a:b, i].min()) for i, leg in enumerate(LEGS)}

    out = {"dir": str(d), "t_te_s": te, "t_lift_s": tl, "lift_after_te_s": tl - te, "t_crawler_zero_s": tz, "W_kN": W,
           "tau_te_mm": float(N @ s[ke]), "tau_lift_mm": float(N @ s[kl]), "D_te_kN": float(F[ke - 200:ke].mean(axis=0) @ N),
           "D_lift_kN": float(F[kl:kl + 400].mean(axis=0) @ N), "F_win_kN": [float(v) for v in F[kl:kl + 400].mean(axis=0)],
           "F_min_lift8_kN": leg_min(kl, k8), "F_min_zero_to_cut_kN": leg_min(kz, kcut),
           "F_min_after_zero_all_kN": leg_min(kz, len(t)), "ready_t_s": res.get("ready_t_s"), "end_t_s": float(res["s8_end"]["end_t_s"]),
           "final_phase": res["s8_end"].get("final_phase"), "stroke_max_mm": [float(v) for v in s.max(axis=0)], "stroke_end_mm": [float(v) for v in s[-1]],
           "end_attitude_deg": attitude_deg(p["body_quat_wxyz"][-1]), "head_pressure_max_bar": None if "head_pressure" not in p.files else float(p["head_pressure"].max() / 1e5),
           "wall_s": (res.get("runner") or {}).get("wall_s")}
    return out


def s7_metrics(d: Path) -> dict:
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    st = np.load(d / "step_series.npz", allow_pickle=False)
    t, F, s = st["t_s"], st["F_cyl_N"] / 1e3, st["s_motor_m"] * 1e3
    cr = st["scm_crawler_normal_N"] / 1e3
    ph = res["phases"]
    te = next(float(p["t_s"]) for p in ph if p["phase"] == "level")
    W = float(np.median(F[(t > te - 8) & (t < te - 6)].sum(axis=1)) + np.median(cr[(t > te - 8) & (t < te - 6)]))
    sm = np.convolve(F.sum(axis=1), np.ones(20) / 20, "same")
    hit = np.flatnonzero((t > te) & (W - sm < 3.0))
    tl = None if hit.size == 0 else float(t[hit[0]])
    ke = int(np.searchsorted(t, te))
    kl = None if tl is None else int(np.searchsorted(t, tl))
    z = np.flatnonzero((t > te) & (cr == 0.0))
    tz = None if z.size == 0 else float(t[z[0]])
    tend = float(res["phases"][-1]["t_s"])
    kend = int(np.searchsorted(t, tend))
    start = kl if kl is not None else ke
    meta = (res.get("controller_meta") or {}).get("touch_twist_hold")
    names = [e["name"] for e in res["events"]]
    rp = st["roll_pitch_deg"]
    return {"dir": str(d), "t_loop_start_s": res["t_loop_start_s"], "phases": ph, "t_te_s": te, "t_lift_s": tl, "t_crawler_zero_s": tz, "W_kN": W,
            "tau_te_mm": float(N @ s[ke]), "tau_lift_mm": None if kl is None else float(N @ s[kl]), "D_te_kN": float(F[ke - 200:ke].mean(axis=0) @ N),
            "D_lift_kN": None if kl is None else float(F[kl:kl + 400].mean(axis=0) @ N),
            "F_min_after_lift_sample_kN": {leg: float(F[start:, i].min()) for i, leg in enumerate(LEGS)},
            "stroke_max_mm": [float(v) for v in s.max(axis=0)], "stroke_at_last_phase_mm": [float(v) for v in s[min(kend, len(t) - 1)]],
            "roll_pitch_at_last_phase_deg": [float(v) for v in rp[min(kend, len(t) - 1)]], "roll_pitch_end_deg": [float(v) for v in rp[-1]],
            "events_info": [e for e in res["events"] if any(k in e["name"] for k in ("TOUCH_TWIST", "LOC", "FAULT", "WARN", "liftoff", "PAUSED"))],
            "touch_twist_hold": meta, "names_hold": [n for n in names if "TOUCH_TWIST" in n],
            "checks": (res.get("p3b") or {}).get("checks"), "wall_s": res.get("wall_s"), "code_state": res.get("code_state", {}).get("state")}


def expected() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    off = {k: rigid_metrics(v[1]) for k, v in RIGID.items()}
    off["S7"] = s7_metrics(S7_OFF)
    target = {k: float(np.clip(-v["D_te_kN"] / K_NOM_KN_MM, -3.0, 3.0)) for k, v in off.items()}
    doc = {"written_before_run": True, "note": "Off values and expectations only; no acceptance rule here, control-expert judges.",
           "code": {"commit": "15176d153465b45c6bbd58aec5bed2732b9696e8", "c2_sha256": "02ca442c3be01ab3c91822b3101c0c1054f1b59c878555ced14c7393af58afd4", "worktree": str(WT)},
           "pairs": {k: str(v[1]) for k, v in RIGID.items()} | {"S7": str(S7_OFF)},
           "pair_notes": {"R9 gap pairs": "cad_asym code (agent-ae9039e69988d5282), flow off, stopped at 40 s after the settle: no READY, no end attitude, no judge rows on the off side.",
                          "C2 clip": "The off pairs have the returned clip off (they are older than it); new rows have it on, so a difference from the off value holds both changes."},
           "expected": {
               "target_tau_star_mm_from_off_D_te": target, "k_nom_kN_mm_used": K_NOM_KN_MM,
               "rule": "c2.py TouchTwistHoldSettings: tau* = clip(-D_hat / k_nom, +-3 mm), D_hat from the last 3 TOUCH readings, gain 2.5 1/s, 1.5 s, dead band 1 kN. D_te stays the off value since it is before the hold, unless TOUCH differs (no TOUCH rule was changed, so expect bit-equal up to TOUCH end, apart from the C2 clip).",
               "D_lift": "Moves toward 0 for rows with an INFO_TOUCH_TWIST_HOLD; R9_mirror2_d035 (off D_te 38 kN, the largest) moves most. R9_sym off D_te 0.002 kN is inside the 1 kN dead band: no hold expected, so D_lift 19.7 kN stays apart from the G1 vector ramp and the clip. R4 off D_te 1.13 kN is at the band edge: a hold with target near -0.05 mm or none. Size on Chrono unknown in advance: harness R2 D_te 11.9 to D_lift 2.2.",
               "F_min": "Min force after lift-off up for rows with a large twist before; R9 mirror2 d035 RL 29.5 kN off value. Harness R4: F_min 54.63 to 54.12 kN (small down).",
               "paused_periods": "Expect 0 unless a re-approach falls in the 1.5 s hold; INFO_LIFT_PAUSED was seen on R9 mirror2 d035 off.",
               "S7": "Stored off stops with FAULT_LIFT_STROKE_LIMIT:soil:FL at 50.4 s absolute (42.4 s loop). A stroke-guard stop is expected to stay; D_te from soil differs, hold starts if |D_hat| >= 1 kN.",
               "cost": "Rigid 380 to 860 s per row at 4 at once with the two S8 SCM runs."},
           "off_values": off}
    (OUT / "expected_before_run.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: {q: (round(v[q], 3) if isinstance(v[q], float) else v[q]) for q in ("t_te_s", "tau_te_mm", "D_te_kN", "D_lift_kN", "t_lift_s")} for k, v in off.items()}, indent=0))
    print("target", target)


def rigid(stamp: str) -> None:
    sys.path.insert(0, str(WT / "03_src"))
    from outrigger_sim.verify.s8_control import judge_batch

    exp = json.loads((OUT / "expected_before_run.json").read_text(encoding="utf-8"))
    rows = {}
    for row, (cid, _pair) in RIGID.items():
        b = S8 / f"c4g1_{row}_{stamp}"
        vf = OUT / f"verify_{b.name}.json"
        judge_batch(b, vf, root=MAIN, ref_batch=None, lookup_batches=[], deferred_ref=None)
        doc = json.loads(vf.read_text(encoding="utf-8"))
        d = b / cid
        m = rigid_metrics(d)
        res = json.loads((d / "result.json").read_text(encoding="utf-8"))
        ev = json.loads((d / "controller_events.json").read_text(encoding="utf-8"))
        side = json.loads((d / "c4g1_job_side.json").read_text(encoding="utf-8"))
        items = {r["item"]: r for r in doc["rows"] if r.get("case") == cid}
        keep = {k: items[k]["value"] for k in items if k.startswith(("3 F_min", "2 attitude", "4 max", "run", "C1 D8", "C2 REANCHOR"))}
        o = exp["off_values"][row]
        diff = {q: None if not isinstance(o.get(q), (int, float)) or not isinstance(m.get(q), (int, float)) else m[q] - o[q]
                for q in ("t_te_s", "t_lift_s", "tau_te_mm", "tau_lift_mm", "D_te_kN", "D_lift_kN", "ready_t_s")}
        diff["F_min_zero_to_cut_kN"] = {g: m["F_min_zero_to_cut_kN"][g] - o["F_min_zero_to_cut_kN"][g] for g in LEGS}
        diff["F_min_lift8_kN"] = {g: m["F_min_lift8_kN"][g] - o["F_min_lift8_kN"][g] for g in LEGS}
        rows[row] = {"on": m, "off": o, "on_minus_off": diff, "rows": keep, "meta_failed": doc["meta"].get("failed"), "meta_hold": doc["meta"].get("hold"), "failed_rows": [k for k, r in items.items() if r.get("passed") is False],
                     "touch_twist_hold": (res.get("controller_meta") or {}).get("touch_twist_hold"), "events_hold": [str(e) for e in ev if "TOUCH_TWIST" in str(e)],
                     "events_warn": [str(e) for e in ev if any(k in str(e) for k in ("WARN", "FAULT", "PAUSED", "reapproach"))], "side": side}
    (OUT / "c4g1_rigid_values.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("written", OUT / "c4g1_rigid_values.json")


if __name__ == "__main__":
    if sys.argv[1] == "expected":
        expected()
    elif sys.argv[1] == "rigid":
        rigid(sys.argv[2])
    else:
        v = {"on": s7_metrics(Path(sys.argv[2])), "off": s7_metrics(S7_OFF)}
        (OUT / "c4g1_s7_values.json").write_text(json.dumps(v, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        print("written", OUT / "c4g1_s7_values.json")
