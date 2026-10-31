"""RV6 X6-rp2 (spec 430.3.5, J1 B top roll_pos k 0.6 = +2.64 deg) final-controller Chrono judgement, harness
comparison and READY-gap decomposition (same procedure as final_x_rb2_judge.py; the roll_neg pair X6-rb2 is the
reference run).

Inputs (all read-only):
  <case>/result.json, <case>/result_rejudge_rev60.json (run_S9.py rejudge), <case>/record/record.npz,
  <case>/step_series.npz, <case>/completion_series.npz,
  <evidence>/x6rp2_pmax.json, <evidence>/x6rb2_pmax.json (final_rep_pmax.py),
  06_analysis/02_control/s9/rev85/finB2_h9.json (H9 rows).
Stroke quantities as in final_x_rb2_judge.py: controller reading = record 'meas.stroke' (guard 682.8 mm);
harness max_stroke_mm = max(plant.sref); true rod stroke = record 'stroke_true' (gate 684.8 mm).
Gap quantities: P3-5 judge value = s9_rows 'rut_clearance_m' (10 Hz, crawler vs the rut reference along the slope
normal, minimum from the first READY entry); controller estimate = completion_series 'clearance_filtered_m'.
Usage: python -I final_x_rp2_judge.py <repo root> <out json>
           [--add KEY CASE_DIR HARNESS_FILE HARNESS_ID PMAX_JSON [--duration S]] [--only KEY [KEY ...]]
  --add      judge one more case (paths relative to the repo root or absolute); repeatable. Example for
             X6-rp3 (spec 430.3.6, roll_pos k 0.5 = +2.2 deg; harness twin = the H3 row, H9 has no k 0.5):
             --add X6-rp3 07_results/S9/<batch>/S9SL_X6rb_J1_B_top_Fs4_r2p2_p0
                   06_analysis/02_control/s9/rev85/finB2_harness_rejudged.json "H3|J1|B|top|roll_pos@k0.5"
                   06_analysis/02_control/s9/rev85/evidence/x6rp3_pmax.json
  --duration run duration [s] of the --add cases (default 160; the settle 8 s is added).
  --only     judge only these keys (default: all).
"""
import argparse
import json
from pathlib import Path

import numpy as np

_ap = argparse.ArgumentParser()
_ap.add_argument("root")
_ap.add_argument("out")
_ap.add_argument("--add", nargs=5, action="append", default=[],
                 metavar=("KEY", "CASE_DIR", "HARNESS_FILE", "HARNESS_ID", "PMAX_JSON"))
_ap.add_argument("--duration", type=float, default=160.0)
_ap.add_argument("--only", nargs="+", default=None)
ARGS = _ap.parse_args()
ROOT, OUT = Path(ARGS.root), Path(ARGS.out)
EV = ROOT / "06_analysis/02_control/s9/rev85/evidence"
H = ROOT / "06_analysis/02_control/s9/rev85"
LEGS = ("FL", "FR", "RL", "RR")
GUARD_MM, GATE_MM, FAULT_MM, SENSOR_END_MM = 682.8, 684.8, 693.8, 694.8
F_MIN_N = 9415.0
DT_S, SETTLE_S = 1e-4, 8.0
IMU_RULE_DEG = 0.118
H6_STROKE_MM, H6_GAP_SLOPE_MM = 23.0, -15.0
P35_MIN_MM = 25.0
FEATURE_TAGS = ("WARN", "FAULT", "FLAT_SOIL_MARGIN", "LOC_CLEARANCE", "LOC_REVOKED", "DIFF_SINK", "TWIST_UNSETTLED",
                "LIFT_PAUSED", "LOC_WINDOW", "LIFT_STROKE", "crawler_liftoff", "ready", "relevel", "probe_start")

CASES = {
    "X6-rp2": {
        "case": ROOT / "07_results/S9/batch_RV6_20261031_070613/S9SL_X6rb_J1_B_top_Fs4_r2p64_p0",
        "pmax": EV / "x6rp2_pmax.json", "harness_file": H / "finB2_h9.json",
        "harness_id": "H9|J1|B|top|roll_pos@k0.6", "duration_s": 160.0,
    },
    "X6-rb2": {
        "case": ROOT / "07_results/S9/batch_RV6_20261031_025137/S9SL_X6rb_J1_B_top_Fs4_rm2p64_p0",
        "pmax": EV / "x6rb2_pmax.json", "harness_file": H / "finB2_h9.json",
        "harness_id": "H9|J1|B|top|roll_neg@k0.6", "duration_s": 160.0,
    },
}


def _path(p):
    q = Path(p)
    return q if q.is_absolute() else ROOT / q


for _key, _case, _hfile, _hid, _pmax in ARGS.add:
    CASES[_key] = {"case": _path(_case), "pmax": _path(_pmax), "harness_file": _path(_hfile),
                   "harness_id": _hid, "duration_s": ARGS.duration}
if ARGS.only:
    CASES = {k: v for k, v in CASES.items() if k in ARGS.only}


def rnd(a, n=2):
    return np.round(np.asarray(a, dtype=float), n).tolist()


def load_run(case):
    res = json.loads((case / "result.json").read_text(encoding="utf-8"))
    with np.load(case / "record" / "record.npz") as z:
        rec = {k: np.asarray(z[k]) for k in ("t", "meas.stroke", "stroke_true", "s_ref", "F_cyl", "body_pos")}
    with np.load(case / "step_series.npz") as z:
        st = {k: np.asarray(z[k]) for k in ("t_s", "pad_sinkage_geometric_m", "scm_pad_normal_N", "s_motor_m",
                                            "scm_crawler_normal_N", "roll_pitch_deg")}
    with np.load(case / "completion_series.npz") as z:
        cs = {k: np.asarray(z[k]) for k in ("t_s", "clearance_filtered_m", "phase")}
    rows = res["s9_rows"]
    s9 = {"t_s": np.array([float(r["t_s"]) for r in rows]),
          "rut_m": np.array([np.nan if r.get("rut_clearance_m") is None else float(r["rut_clearance_m"])
                             for r in rows]),
          "gap_min_m": np.array([np.nan if r.get("crawler_gap_min_m") is None else float(r["crawler_gap_min_m"])
                                 for r in rows])}
    return res, rec, st, cs, s9


def at(t, arr, ts):
    return arr[int(np.argmin(abs(t - ts)))]


def marks_of(res, rj):
    ev = [(float(e["t_s"]), str(e["name"])) for e in res["events"]]
    t_loc = [tt for tt, n in ev if n == "crawler_liftoff_confirmed"]
    t_ready = [float(p["t_s"]) for p in res["phases"] if str(p["phase"]).upper() == "READY"]
    p35 = rj["p3b"]["P3-5_clearance_stroke"]
    return {"loc_first": t_loc[0] if t_loc else None, "loc_final": t_loc[-1] if t_loc else None,
            "first_ready": t_ready[0] if t_ready else None, "p35_min": p35.get("t_at_min_s"),
            "end": float(res["s9_rows"][-1]["t_s"])}


def gap_profile(res, rj, rec, st, cs, s9):
    """Gap (judge value and controller estimate), reading stroke and pad sinkage at the key events."""
    t0 = float(res["t_loop_start_s"])
    marks = marks_of(res, rj)
    out = {}
    for k, ts in marks.items():
        if ts is None:
            continue
        out[k] = {"t_loop_s": round(ts - t0, 2),
                  "rut_clearance_mm": round(float(at(s9["t_s"], s9["rut_m"], ts)) * 1e3, 2),
                  "crawler_gap_min_mm": round(float(at(s9["t_s"], s9["gap_min_m"], ts)) * 1e3, 2),
                  "controller_clearance_mm": round(float(at(cs["t_s"], cs["clearance_filtered_m"], ts)) * 1e3, 2),
                  "reading_mm": dict(zip(LEGS, rnd(at(rec["t"], rec["meas.stroke"], ts) * 1e3))),
                  "pad_sinkage_mm": dict(zip(LEGS, rnd(at(st["t_s"], st["pad_sinkage_geometric_m"], ts) * 1e3))),
                  "pad_normal_kN": dict(zip(LEGS, rnd(at(st["t_s"], st["scm_pad_normal_N"], ts) / 1e3))),
                  "roll_pitch_deg": rnd(at(st["t_s"], st["roll_pitch_deg"], ts), 3)}
    out["pad_sinkage_max_mm"] = dict(zip(LEGS, rnd(st["pad_sinkage_geometric_m"].max(axis=0) * 1e3)))
    lf, rd = out.get("loc_final"), out.get("first_ready")
    if lf and rd:
        out["loc_to_ready"] = {
            "rut_clearance_gain_mm": round(rd["rut_clearance_mm"] - lf["rut_clearance_mm"], 2),
            "controller_clearance_gain_mm": round(rd["controller_clearance_mm"] - lf["controller_clearance_mm"], 2),
            "controller_minus_rut_at_loc_mm": round(lf["controller_clearance_mm"] - lf["rut_clearance_mm"], 2),
            "controller_minus_rut_at_ready_mm": round(rd["controller_clearance_mm"] - rd["rut_clearance_mm"], 2),
            "pad_sinkage_increase_mm": {g: round(rd["pad_sinkage_mm"][g] - lf["pad_sinkage_mm"][g], 2) for g in LEGS},
            "reading_increase_mm": {g: round(rd["reading_mm"][g] - lf["reading_mm"][g], 2) for g in LEGS},
        }
    # 1 s series of the judge gap after the first READY (shape of the minimum)
    if rd:
        tr = marks["first_ready"]
        sel = (s9["t_s"] >= tr - 1e-9) & np.isfinite(s9["rut_m"])
        tt, gg = s9["t_s"][sel], s9["rut_m"][sel]
        grid = np.arange(tr, tt[-1] + 1e-9, 5.0)
        out["rut_after_ready_5s"] = [{"t_loop_s": round(float(g - t0), 1),
                                      "rut_mm": round(float(at(tt, gg, g)) * 1e3, 2)} for g in grid]
        out["rut_after_ready_max_mm"] = round(float(gg.max()) * 1e3, 2)
    return out


def time_check(res, rec, st, duration_s):
    n = int(res["n_steps"])
    expect = int(round((duration_s + SETTLE_S) / DT_S))
    return {"duration_arg_s": (res.get("args") or {}).get("duration"), "n_steps": n, "n_steps_expected": expect,
            "steps_ok": n == expect, "t_loop_start_s": res["t_loop_start_s"],
            "record_t_last_s": round(float(rec["t"][-1]), 4), "record_n": int(rec["t"].size),
            "step_series_t_last_s": round(float(st["t_s"][-1]), 4), "step_series_n": int(st["t_s"].size),
            "wall_s": res.get("wall_s"), "us_per_step": res.get("us_per_step")}


def harness_row(path, hid):
    d = json.loads(path.read_text(encoding="utf-8"))
    r = next(r for r in d["records"] if r["id"] == hid)
    keep = ("id", "verdict", "failed_rows", "t_ready_s", "min_force_kN", "att_end_deg", "max_stroke_mm", "final_phase",
            "rut_ready_mm", "crawler_N_max_after_ready", "warnings", "flags", "soil_stop", "metrics")
    return {k: r.get(k) for k in keep}


def judge(name, cfg):
    case = cfg["case"]
    res, rec, st, cs, s9 = load_run(case)
    rj = json.loads((case / "result_rejudge_rev60.json").read_text(encoding="utf-8"))
    pm = json.loads(cfg["pmax"].read_text(encoding="utf-8"))["cases"][case.name]
    hz = harness_row(cfg["harness_file"], cfg["harness_id"])
    p3b, chk = rj["p3b"], rj["p3b"]["checks"]
    t0 = float(res["t_loop_start_s"])
    t = rec["t"]
    s_read, s_true, s_ref = rec["meas.stroke"] * 1e3, rec["stroke_true"] * 1e3, rec["s_ref"] * 1e3
    read_max, true_max = s_read.max(axis=0), s_true.max(axis=0)
    leg = int(read_max.argmax())
    ev = [(float(e["t_s"]), str(e["name"])) for e in res["events"]]
    feat = [{"t_s": round(tt, 2), "t_loop_s": round(tt - t0, 2), "name": n} for tt, n in ev
            if any(k in n for k in FEATURE_TAGS)]
    warn_fault = [f for f in feat if f["name"].startswith(("WARN", "FAULT"))]
    sgs = [f for f in feat if "LIFT_STROKE" in f["name"]]
    ready, att, force = p3b["P3-6_ready"], p3b["P3-4_attitude"], p3b["P3-3_leg_force"]
    loc, dep, p35 = p3b["P3-2_loc"], p3b.get("departure") or {}, p3b["P3-5_clearance_stroke"]
    ready_phases = [round(float(p["t_s"]) - t0, 2) for p in res["phases"] if str(p["phase"]).upper() == "READY"]
    c_ready_mm = chk["P3-5_rut_clearance_min_after_first_ready_m"] * 1e3
    allow = att["sensor_allowance_left_deg"]
    chrono = {
        "ready_first_s_loop": ready["t_ready_after_loop_start_s"], "ready_limit_s": ready["limit_s"],
        "ready_phases_s_loop": ready_phases,
        "min_force_after_departure_kN": min(force["F_min_after_N"]) / 1e3,
        "min_force_leg": LEGS[int(np.argmin(force["F_min_after_N"]))],
        "gap_after_first_ready_mm": c_ready_mm,
        "gap_min_t_loop_s": None if p35.get("t_at_min_s") is None else round(p35["t_at_min_s"] - t0, 2),
        "gap_end_mm": None if p35.get("rut_clearance_end_m") is None else p35["rut_clearance_end_m"] * 1e3,
        "gap_at_loc_mm": None if p35.get("rut_clearance_at_loc_m") is None else p35["rut_clearance_at_loc_m"] * 1e3,
        "end_attitude_absmax_deg": att["p34_absmax_overall_deg"], "end_1s_roll_pitch_deg": att.get("end_mean_roll_pitch_deg"),
        "p34_window_s": att.get("p34_window_length_s"),
        "imu_allowance_left_deg": allow, "imu_allowance_vs_0p118": allow >= IMU_RULE_DEG,
        "stroke_reading_max_mm": dict(zip(LEGS, rnd(read_max))),
        "stroke_reading_max_t_loop_s": dict(zip(LEGS, rnd(t[s_read.argmax(axis=0)] - t0))),
        "stroke_true_max_mm": dict(zip(LEGS, rnd(true_max))),
        "s_ref_max_mm": dict(zip(LEGS, rnd(s_ref.max(axis=0)))),
        "lead_leg": LEGS[leg],
        "margin_reading_to_guard_mm": GUARD_MM - float(read_max[leg]),
        "margin_true_to_gate_mm": GATE_MM - float(true_max.max()),
        "margin_reading_to_fault_mm": FAULT_MM - float(read_max[leg]),
        "max_moving_pressure_bar": pm["max_moving_pressure_bar"], "max_any_state_bar": pm["max_any_state_bar"],
        "measured_head_max_bar": pm["measured_head_max_bar"], "pressure_peak_leg": pm["peak_leg"],
        "pressure_ratio_180": pm.get("ratio_to_judge_180"),
        "soil": {k: (res.get("c2_soil") or {}).get(k) for k in ("soil_mode", "clearance_at_P_m", "clearance_at_loc_m",
                                                               "settle_attitude_rad", "push_m", "loc_anchor_applied")},
    }
    rows = {
        "P3-1": {"pass": bool(chk["P3-1_crawler_zero_after_ready"] and chk["P3-1_recontact_pass"]),
                 "recontact_count": dep.get("recontact_count"),
                 "crawler_normal_max_after_confirm_N": dep.get("crawler_normal_max_after_confirm_N")},
        "P3-2": {"verdict": chk["P3-2_verdict"], "loc_minus_departure_s": chk["P3-2_loc_minus_departure_s"],
                 "limit_s": chk["P3-2_limit_s"], "loc_revokes": chk["loc_revokes"],
                 "soil_mode_used": loc.get("soil_mode_used"), "crawler_normal_at_loc_N": loc.get("crawler_normal_at_loc_N")},
        "P3-3": {"pass": chk["P3-3_within"], "min_kN": chrono["min_force_after_departure_kN"], "F_min_kN": F_MIN_N / 1e3},
        "P3-4": {"pass": chk["P3-4_within_0p2"], "absmax_deg": att["p34_absmax_overall_deg"],
                 "window_short": att.get("window_short"), "imu_allowance_left_deg": allow},
        "P3-5": {"pass": chk["P3-5_within"], "gap_mm": c_ready_mm, "limit_mm": P35_MIN_MM,
                 "shortfall_mm": P35_MIN_MM - c_ready_mm, "s_true_max_mm": float(true_max.max()),
                 "stroke_within": p35.get("stroke_within")},
        "P3-6": {"pass": chk["P3-6_within"], "ready_s_loop": chrono["ready_first_s_loop"], "limit_s": ready["limit_s"]},
        "P3-7": {"pass": chk["P3-7_within"], "rise_min_loaded_N": chk["P3-7_rise_min_loaded_N"], "record_row": True},
        "P3-8": {"pass": chk["P3-8_within"]},
    }
    judged = {k: v for k, v in rows.items() if k != "P3-7"}
    failed = [k for k, v in judged.items() if not v.get("pass", v.get("verdict") in ("pass", "flag"))]
    hs = float(hz["max_stroke_mm"])
    gap_diff = c_ready_mm - hz["rut_ready_mm"]
    cmp_ = {
        "stroke_controller_quantity_mm": {"harness": hs, "chrono": float(read_max.max()),
                                          "chrono_minus_harness": float(read_max.max()) - hs,
                                          "within_H6_plus23": float(read_max.max()) - hs <= H6_STROKE_MM},
        "guard_margin_mm": {"harness": GUARD_MM - hs, "chrono": GUARD_MM - float(read_max.max())},
        "ready_s": {"harness": hz["t_ready_s"], "chrono": chrono["ready_first_s_loop"],
                    "chrono_minus_harness": chrono["ready_first_s_loop"] - hz["t_ready_s"]},
        "gap_mm": {"harness": hz["rut_ready_mm"], "chrono": c_ready_mm, "chrono_minus_harness": gap_diff,
                   "within_H6_slope_minus15": gap_diff >= H6_GAP_SLOPE_MM,
                   "harness_minus15_prediction_mm": hz["rut_ready_mm"] + H6_GAP_SLOPE_MM},
        "min_force_kN": {"harness": hz["min_force_kN"], "chrono": chrono["min_force_after_departure_kN"],
                         "ratio_harness_over_chrono": hz["min_force_kN"] / chrono["min_force_after_departure_kN"]},
        "end_attitude_deg": {"harness_end": hz["att_end_deg"], "chrono_absmax": att["p34_absmax_overall_deg"]},
        "verdict": {"harness": hz["verdict"],
                    "chrono": "pass" if not failed and not warn_fault and not sgs else
                    ("stroke_limited_stop" if sgs else "fail")},
    }
    return {
        "case": case.name, "folder": case.relative_to(ROOT).as_posix(), "harness_id": cfg["harness_id"],
        "controller": (res.get("args") or {}).get("expect_controller"),
        "code_state": (res.get("code_state") or {}).get("state"), "mass_scale": res.get("mass_scale"),
        "rejudge": {"unchanged_blocks_equal": rj["unchanged_blocks_equal"], "params_file_match": rj["params_file_match"]},
        "time_check": time_check(res, rec, st, cfg["duration_s"]),
        "verdict": cmp_["verdict"]["chrono"], "failed_rows": failed,
        "flags": [k for k, v in rows.items() if v.get("verdict") == "flag"],
        "rows": rows, "chrono": chrono, "warn_fault_events": warn_fault, "feature_events": feat,
        "R9_events": [f for f in feat if "FLAT_SOIL_MARGIN" in f["name"]],
        "E3c10_events": [f for f in feat if "LOC_CLEARANCE_MARGIN" in f["name"]],
        "L1gs_events": [f for f in feat if "LOC_REVOKED" in f["name"]],
        "DSb75_events": [f for f in feat if "DIFF_SINK" in f["name"]],
        "SGS_events": sgs,
        "gap_profile": gap_profile(res, rj, rec, st, cs, s9),
        "harness": hz, "harness_vs_chrono": cmp_,
    }


result = {"script": "04_scripts/03_control/s9/evidence/final_x_rp2_judge.py",
          "notes": ["Times *_loop_s are loop-relative (absolute - t_loop_start_s = 8.0 s).",
                    "Stroke comparison uses the controller reading (Chrono meas.stroke) vs harness max(plant.sref).",
                    "P3-7 is a record row (400.2 practice); P3-2 FLAG under 419.8 / 424.10.2 counts as within rules.",
                    f"IMU selection rule {IMU_RULE_DEG} deg (U-S9P-16); H-6 stroke +{H6_STROKE_MM} mm (432.4.5), "
                    f"soft slope gap {H6_GAP_SLOPE_MM} mm (432.4.7); P3-5 limit {P35_MIN_MM} mm (U-S9-C3).",
                    "X6-rb2 is recomputed here as the roll_neg reference (same values as final_x_rb2_judge.json) "
                    "with the gap decomposition added."]}
for n, c in CASES.items():
    result[n] = judge(n, c)
OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
for n in CASES:
    o = result[n]
    print("==", n, o["verdict"], "failed", o["failed_rows"], "flags", o["flags"], o["controller"], o["code_state"])
    print(" time", json.dumps(o["time_check"]))
    print(" rejudge", o["rejudge"])
    print(" rows", json.dumps(o["rows"], default=float))
    print(" chrono", json.dumps(o["chrono"], default=float))
    print(" cmp", json.dumps(o["harness_vs_chrono"], default=float))
    print(" feat", o["feature_events"])
    print(" gap", json.dumps(o["gap_profile"]))
