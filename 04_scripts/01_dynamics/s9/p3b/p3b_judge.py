"""S9 P3b dynamics judgement support values, main part (dynamics_model.md rev. 53, 5.37.10 / 5.38).

Per P3b case (24, from the summary rows): departure / LOC / creep-stop times, pad sinkage
(at departure, end, max) and creep, pad normal force max / end against the continuous Bekker
static sinkage at the max load (5.37.10 check 1), end equilibrium (pads + crawler) / W, true
W ratio at LOC against the C2 ``W_ratio``, rod weights, cylinder force and stroke margins,
attitude drift after the creep stop, and the runner check flags (5.38.1).
Also the dt checks D1 (settle, dt 5e-5 vs P2' dt 1e-4) and D2 (P3a G1 B lift, dt 5e-5 vs
1e-4) of 5.37.10, and the 5.37.1 P3a-7 attitude recomputation.

Frame: body x forward, y left, z up; roll > 0 left up, pitch > 0 nose down;
g = (0, 0, -9.80665). Sinkage + = pad bottom below the SCM plane (crawler bottom + 4 mm).
SI unless the key says mm / kN / deg.

Inputs (git-external raw data under 07_results/S9):
  batch_P3b_20261026_122444/P3b_*/ (step_series.npz 1 ms, result.json),
  batch_DT_20261026_122444/ (D1 / D2 runs), batch_P3a_20261026_092653/ (P3a reference),
  and 06_analysis/01_chrono/19_S9/s9_P3b_summary.json, s9_P2prime_summary.json,
  s9_P3a_summary.json.
Output: one intermediate JSON (merged by ``merge_out.py``).

Usage (dynamics-dev):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s9/p3b/p3b_judge.py <out_json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
B = ROOT / "07_results" / "S9" / "batch_P3b_20261026_122444"
DT = ROOT / "07_results" / "S9" / "batch_DT_20261026_122444"
P3A = ROOT / "07_results" / "S9" / "batch_P3a_20261026_092653"
SUMM = ROOT / "06_analysis" / "01_chrono" / "19_S9"
LEGS = ("FL", "FR", "RL", "RR")
G = 9.80665
F_LIM = np.array([278.7e3, 278.7e3, 199.6e3, 199.6e3])  # N, extend force limit per leg
STROKE_END = 0.6848  # m, end-margin reference stroke


def soil(r):
    """SCM soil and pad parameters of one run (from the run meta)."""
    sc = r["meta"]["scm"]["soil"]["chrono"]
    pv = r["meta"]["pad_variant"]
    area = np.array([pv["pad_bottom_area_m2"][k] for k in LEGS])
    b = np.array([pv["pad_bekker_b_m"][k] for k in LEGS])
    return dict(n=sc["n"], K=sc["elastic_K"], R=sc["damping_R"], keq=sc["Kc"] / b + sc["Kphi"],
                A=area, Kc=sc["Kc"], Kphi=sc["Kphi"], b=b, c=sc.get("cohesion"),
                phi=sc.get("friction_angle"))


def bekker_s(N, so):
    """Continuous Bekker static sinkage at pad normal load N."""
    p = np.maximum(N / so["A"], 0.0)
    return (p / so["keq"]) ** (1.0 / so["n"])


def idx(t, tq):
    return int(np.clip(np.searchsorted(t, tq), 0, len(t) - 1))


def case(name, srow):
    """Judgement support values of one P3b case."""
    d = np.load(B / name / "step_series.npz")
    r = json.loads((B / name / "result.json").read_text("utf-8"))
    so = soil(r)
    t = d["t_s"]
    sink = d["pad_sinkage_geometric_m"]
    pn = d["scm_pad_normal_N"]
    Fc = d["F_cyl_N"]
    sm = d["s_motor_m"]
    rp = d["roll_pitch_deg"]
    z0 = d["z_origin_m"]
    cn = d["scm_crawler_normal_N"]
    W = r["p3b"]["weight_N"]
    Wref = r["c2_soil"]["W_ref_N"]
    dep = srow["departure"]["t_departure_s"]
    loc = srow["P3-2_loc"]["t_loc_s"]
    cs = srow["creep_stop"]["t_final_two_sided_s"]
    i_dep, i_loc = idx(t, dep), idx(t, loc)
    last = t >= t[-1] - 1.0
    i_nmax = np.argmax(pn, axis=0)
    nmax = pn.max(axis=0)
    smax = sink.max(axis=0)
    s_bek_nmax = bekker_s(nmax, so)
    end_pn = pn[last].mean(axis=0)
    end_sink = sink[last].mean(axis=0)
    # equilibrium at the end (pads + crawler vs total weight)
    eq_end = (end_pn.sum() + cn[last].mean()) / W
    # true W ratio at LOC: sum F_cyl (true) / W_ref, 0.2 s mean before LOC
    w = (t > loc - 0.2) & (t <= loc)
    true_ratio_loc = Fc[w].sum(axis=1).mean() / Wref
    # rod weights: pad normal - F_cyl at end (should be moving-mass weight)
    rodw = end_pn - Fc[last].mean(axis=0)
    # dep -> LOC kinematics
    d_ext = (sm[i_loc] - sm[i_dep])
    d_sink = (sink[i_loc] - sink[i_dep])
    d_z0 = z0[i_loc] - z0[i_dep]
    # creep: sinkage increase dep -> creep stop
    i_cs = idx(t, cs)
    creep_mm = (sink[i_cs] - sink[i_dep]) * 1e3
    late_creep_mm = (sink[-1] - sink[i_cs]) * 1e3
    # attitude drift after creep stop
    rp_cs = rp[i_cs]
    rp_end = rp[last].mean(axis=0)
    p34 = srow["P3-4_attitude"]
    tu = srow["track_utilisation"]["max"]
    w_ratio_gap = r["c2_soil"]["W_ratio"] - true_ratio_loc
    check_keys = ("P3-2_within", "P3-3_within", "P3-4_within_0p2", "P3-5_within",
                  "P3-6_within", "P3-8_within")
    res = {
        "soil": srow["soil"], "pad": srow["pad_variant"], "level": srow["level"],
        "fs_kN": srow["fs_kN"],
        "soil_n": so["n"], "keq_N_m^(2+n)": so["keq"].tolist(), "R": so["R"],
        "A_m2": so["A"].tolist(),
        "t_dep_s": dep, "t_loc_s": loc, "loc_minus_dep_s": loc - dep, "t_creep_stop_s": cs,
        "creep_after_dep_s": cs - dep, "t_first_done_s": srow["P3-2_loc"]["t_first_done_s"],
        "t_ready_last_s": p34["t_ready_last_entry_s"],
        "dep_to_loc_ext_mm": (d_ext * 1e3).tolist(), "dep_to_loc_sink_mm": (d_sink * 1e3).tolist(),
        "dep_to_loc_z0_mm": d_z0 * 1e3,
        "sink_dep_mm": (sink[i_dep] * 1e3).tolist(), "sink_end_mm": (end_sink * 1e3).tolist(),
        "sink_max_mm": (smax * 1e3).tolist(),
        "creep_dep_to_stop_mm": creep_mm.tolist(), "creep_after_stop_mm": late_creep_mm.tolist(),
        "pad_N_max_kN": (nmax / 1e3).tolist(), "t_pad_N_max_s": t[i_nmax].tolist(),
        "pad_N_end_kN": (end_pn / 1e3).tolist(),
        "bekker_s_at_Nmax_mm": (s_bek_nmax * 1e3).tolist(),
        "sink_max_over_bekker": (smax / s_bek_nmax).tolist(),
        "pad_pressure_max_kPa": (nmax / so["A"] / 1e3).tolist(),
        "eq_end_total_over_W": eq_end, "crawler_end_N": float(cn[last].mean()),
        "rod_weight_end_N": rodw.tolist(),
        "W_ratio_c2": r["c2_soil"]["W_ratio"], "W_ratio_true_loc": true_ratio_loc,
        "W_ratio_gap": w_ratio_gap,
        "W_ratio_gap_over_4Fs": (
            w_ratio_gap * Wref / (4e3 * srow["fs_kN"]) if srow["fs_kN"] > 0 else None),
        "F_cyl_max_kN": (Fc.max(axis=0) / 1e3).tolist(),
        "F_ratio_max": float((Fc.max(axis=0) / F_LIM).max()),
        "s_motor_max_m": sm.max(axis=0).tolist(),
        "stroke_margin_mm": float((STROKE_END - sm.max()) * 1e3),
        "pad_tilt_max_deg": r["p3_records"]["pad_tilt_max_deg"],
        "track_util_max": tu, "crawler_recontact": srow["departure"]["recontact_count"],
        "crawler_N_max_after_confirm_N": srow["departure"]["crawler_normal_max_after_confirm_N"],
        "settle_roll_pitch_deg": srow["settle_reference"]["roll_pitch_deg"],
        "settle_z0_mm": srow["settle_reference"]["z_origin_m"] * 1e3,
        "settle_sink_mm": (
            np.array(srow["settle_reference"]["pad_sinkage_geometric_m"]) * 1e3).tolist(),
        "p34_absmax_deg": p34["p34_absmax_overall_deg"], "p34_within": p34["within_0p2"],
        "end_roll_pitch_deg": rp_end.tolist(), "rp_at_creep_stop_deg": rp_cs.tolist(),
        "drift_creepstop_to_end_deg": (rp_end - rp_cs).tolist(),
        "post_liftoff_absmax_deg": p34["post_liftoff_absmax_deg"],
        "nonfinite": r["monitor"]["nonfinite_steps"],
        "sat_steps": r["monitor"]["saturation_step_count"],
        "pre_liftoff_min_F_cyl_kN": [
            lg["F_min_N"] / 1e3 for lg in srow["pre_liftoff_min_F_cyl"]["legs"]],
        "P3-3_min_after_kN": [x / 1e3 for x in srow["P3-3_leg_force"]["F_min_after_N"]],
        "checks": {k: srow["checks"][k] for k in check_keys},
        "us_per_step": srow["us_per_step"], "wall_h": srow["wall_s"] / 3600,
        "settle_dt": r["meta"]["dt_s"], "params_sha": r["meta"]["params_sha256"][:8],
        "scm_run_sha": r["meta"]["scm_run_sha256"][:8],
    }
    return res


def _d1_settle_check():
    """D1: settle dt 5e-5 vs P2' G1 (dt 1e-4), window 7-8 s means."""
    d = np.load(DT / "DT_G1_B_top_M14s_dashpot8s_dt5e-5" / "series.npz")
    t = d["t_s"]
    w = (t > 7.0) & (t <= 8.0 + 1e-9)
    pitch = d["roll_pitch_deg"][w, 1].mean()
    roll = d["roll_pitch_deg"][w, 0].mean()
    z0 = d["body_pos_m"][w, 2].mean() * 1e3 if "body_pos_m" in d.files else np.nan
    p2_rows = json.loads((SUMM / "s9_P2prime_summary.json").read_text("utf-8"))["rows"]
    p2 = p2_rows["P2prime_G1_top_M14s_dashpot8s"]
    return {"dt5e-5": {"pitch_deg": pitch, "roll_deg": roll, "z0_mm": z0},
            "P2prime_dt1e-4": {"pitch_deg": p2["pitch_mean_deg"], "roll_deg": p2["roll_mean_deg"],
                               "z0_mm": p2["z0_mean_mm"]},
            "pitch_rel_pct": 100 * (pitch / p2["pitch_mean_deg"] - 1),
            "z0_rel_pct": 100 * (z0 / p2["z0_mean_mm"] - 1),
            "pitch_abs_diff_deg": pitch - p2["pitch_mean_deg"],
            "z0_abs_diff_mm": z0 - p2["z0_mean_mm"]}


def _d2_lift_check():
    """D2: P3a G1 B dt 5e-5 vs dt 1e-4 (end-window means, peaks, P3a records)."""
    a = np.load(DT / "DT_P3a_G1_B_dt5e-5" / "series.npz")
    ra = json.loads((DT / "DT_P3a_G1_B_dt5e-5" / "result.json").read_text("utf-8"))
    b = np.load(P3A / "P3a_G1_B" / "series.npz")
    rb = json.loads((P3A / "P3a_G1_B" / "result.json").read_text("utf-8"))
    res = {}
    for tag, dd, rr in (("dt5e-5", a, ra), ("dt1e-4", b, rb)):
        tt = dd["t_s"]
        last = tt >= tt[-1] - 1.0
        p3 = rr["p3a"]
        res[tag] = {
            "t_end": float(tt[-1]),
            "end_sink_mm": (dd["pad_sinkage_geometric_m"][last].mean(axis=0) * 1e3).tolist(),
            "end_rp_deg": dd["roll_pitch_deg"][last].mean(axis=0).tolist(),
            "end_point_rp_deg": dd["roll_pitch_deg"][-1].tolist(),
            "F_max_kN": (dd["F_cyl_N"].max(axis=0) / 1e3).tolist(),
            "s_motor_max": dd["s_motor_m"].max(axis=0).tolist(),
            "pad_tilt_max": dd["pad_tilt_deg"].max(axis=0).tolist(),
            "p3a_keys": list(p3.keys()),
        }
        for k in ("P3a-2_liftoff", "P3a-4_stroke", "P3a-5_pad_tilt", "liftoff", "abort"):
            if k in p3:
                res[tag][k] = p3[k]
    A, Bv = res["dt5e-5"], res["dt1e-4"]
    sa, sb = np.array(A["end_sink_mm"]), np.array(Bv["end_sink_mm"])
    res["end_sink_rel_pct"] = (100 * (sa / sb - 1)).tolist()
    res["end_rp_diff_deg"] = (np.array(A["end_rp_deg"]) - np.array(Bv["end_rp_deg"])).tolist()
    res["end_point_rp_diff_deg"] = (
        np.array(A["end_point_rp_deg"]) - np.array(Bv["end_point_rp_deg"])).tolist()
    res["F_max_rel_pct"] = (
        100 * (np.array(A["F_max_kN"]) / np.array(Bv["F_max_kN"]) - 1)).tolist()
    res["s_motor_max_diff_mm"] = (
        1e3 * (np.array(A["s_motor_max"]) - np.array(Bv["s_motor_max"]))).tolist()
    return res


def dt_checks():
    """Time-step checks D1 and D2 (5.37.10)."""
    return {"D1": _d1_settle_check(), "D2": _d2_lift_check()}


def p3a_attitude():
    """5.37.1 P3a-7 recompute: end point, last-1 s mean, vs settle end and vs lift-off."""
    s = json.loads((SUMM / "s9_P3a_summary.json").read_text("utf-8"))["rows"]
    out = {}
    for c in ("P3a_J1_B", "P3a_J1_A", "P3a_G1_B", "P3a_G1_A"):
        a = s[c]["records"]["P3a-7_attitude"]
        d = np.load(P3A / c / "series.npz")
        t = d["t_s"]
        rp = d["roll_pitch_deg"]
        last = t >= t[-1] - 1.0
        ref = np.array(a["settle_end_roll_pitch_deg"])
        lo = np.array(a["d_roll_pitch_at_liftoff_deg"]) + ref
        out[c] = {"json_d_end": a["d_roll_pitch_end_deg"],
                  "json_d_at_liftoff": a["d_roll_pitch_at_liftoff_deg"],
                  "recalc_d_end_point": (rp[-1] - ref).tolist(),
                  "recalc_d_last1s_mean": (rp[last].mean(axis=0) - ref).tolist(),
                  "end_vs_liftoff": (rp[-1] - lo).tolist(),
                  "settle_ref": ref.tolist(), "end_abs": rp[-1].tolist()}
    return out


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_json", type=Path)
    return parser.parse_args()


def main():
    args = _parse_args()
    summ = json.loads((SUMM / "s9_P3b_summary.json").read_text("utf-8"))
    rows = {k: case(k, v) for k, v in summ["rows"].items()}
    out = {"cases": rows, "dt": dt_checks(), "p3a_attitude": p3a_attitude()}
    args.out_json.write_text(json.dumps(out, indent=1, default=float), "utf-8")
    print("ok", len(rows))


if __name__ == "__main__":
    main()
