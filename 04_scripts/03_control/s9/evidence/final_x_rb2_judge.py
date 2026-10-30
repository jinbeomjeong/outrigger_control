"""FINAL-REP-X (spec 432.5.1, J2 B top x1.1, 180 s) and RV6 X6-rb2 (spec 430.3.2, J1 B top roll_neg k 0.6 = -2.64 deg)
final-controller Chrono judgement and harness comparison (same procedure as final6_d150_judge.py).

Inputs (all read-only):
  <case>/result.json, <case>/result_rejudge_rev60.json (run_S9.py rejudge), <case>/record/record.npz,
  <case>/step_series.npz, <case>/controller_commands.npz,
  <evidence>/final_rep_x_pmax.json, <evidence>/x6rb2_pmax.json (final_rep_pmax.py),
  06_analysis/02_control/s9/rev85/finB2_harness_rejudged.json (H6 row), finB2_h9.json (H9 rows).
Reference runs (read-only): the 120 s FINAL-REP J2 B x1.1 run (command identity before its end) and the X6-rb
(k 0.65) run (stroke / sinkage decomposition).
Stroke quantities as in final6_d150_judge.py: controller reading = record 'meas.stroke' (guard 682.8 mm,
R7 release 642.8 mm); harness max_stroke_mm = max(plant.sref) = the same controller-side quantity; true rod stroke
= record 'stroke_true' (gate 684.8 mm).
Usage: python -I final_x_rb2_judge.py <repo root> <out json>
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
EV = ROOT / "06_analysis/02_control/s9/rev85/evidence"
H = ROOT / "06_analysis/02_control/s9/rev85"
LEGS = ("FL", "FR", "RL", "RR")
GUARD_MM, GATE_MM, FAULT_MM, SENSOR_END_MM, DS_RELEASE_MM = 682.8, 684.8, 693.8, 694.8, 642.8
F_MIN_N = 9415.0
DT_S, SETTLE_S = 1e-4, 8.0
IMU_RULE_DEG = 0.118
H6_STROKE_MM = 23.0
FEATURE_TAGS = ("WARN", "FAULT", "FLAT_SOIL_MARGIN", "LOC_CLEARANCE", "LOC_REVOKED", "DIFF_SINK", "TWIST_UNSETTLED",
                "LIFT_PAUSED", "LOC_WINDOW", "LIFT_STROKE", "crawler_liftoff", "ready", "relevel", "probe_start")

CASES = {
    "FINAL-REP-X": {
        "case": ROOT / "07_results/S9/batch_FINAL-REP-X_20261031_020716/P3b_J2_B_top_Fs4_m1p1_t180",
        "pmax": EV / "final_rep_x_pmax.json", "harness_file": H / "finB2_harness_rejudged.json",
        "harness_id": "H6|J2|B|top|flat|m1.1", "duration_s": 180.0,
        "ref": ROOT / "07_results/S9/batch_FINAL-REP_20261030_223359/P3b_J2_B_top_Fs4_m1p1", "ref_duration_s": 120.0,
    },
    "X6-rb2": {
        "case": ROOT / "07_results/S9/batch_RV6_20261031_025137/S9SL_X6rb_J1_B_top_Fs4_rm2p64_p0",
        "pmax": EV / "x6rb2_pmax.json", "harness_file": H / "finB2_h9.json",
        "harness_id": "H9|J1|B|top|roll_neg@k0.6", "duration_s": 160.0,
        "ref": ROOT / "07_results/S9/batch_FINAL-REP_20261030_223359/S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0",
        "ref_duration_s": 160.0, "ref_harness_id": "H9|J1|B|top|roll_neg@k0.65",
    },
}


def rnd(a, n=2):
    return np.round(np.asarray(a, dtype=float), n).tolist()


def load_run(case):
    res = json.loads((case / "result.json").read_text(encoding="utf-8"))
    with np.load(case / "record" / "record.npz") as z:
        rec = {k: np.asarray(z[k]) for k in ("t", "meas.stroke", "stroke_true", "s_ref", "F_cyl", "body_pos")}
    with np.load(case / "step_series.npz") as z:
        st = {k: np.asarray(z[k]) for k in ("t_s", "pad_sinkage_geometric_m", "scm_pad_normal_N", "s_motor_m",
                                            "scm_crawler_normal_N", "roll_pitch_deg")}
    return res, rec, st


def at(t, arr, ts):
    return arr[int(np.argmin(abs(t - ts)))]


def stroke_profile(res, rec, st):
    """Reading / true stroke and pad sinkage at the key events (absolute times)."""
    t = rec["t"]
    ev = [(float(e["t_s"]), str(e["name"])) for e in res["events"]]
    t_loc = [tt for tt, n in ev if n == "crawler_liftoff_confirmed"]
    t_ready = [float(p["t_s"]) for p in res["phases"] if str(p["phase"]).upper() == "READY"]
    marks = {"loc_first": t_loc[0] if t_loc else None, "loc_final": t_loc[-1] if t_loc else None,
             "first_ready": t_ready[0] if t_ready else None, "last_ready": t_ready[-1] if t_ready else None,
             "end": float(t[-1])}
    out = {}
    for k, ts in marks.items():
        if ts is None:
            continue
        out[k] = {"t_s": round(ts, 2),
                  "reading_mm": dict(zip(LEGS, rnd(at(t, rec["meas.stroke"], ts) * 1e3))),
                  "true_mm": dict(zip(LEGS, rnd(at(t, rec["stroke_true"], ts) * 1e3))),
                  "pad_sinkage_mm": dict(zip(LEGS, rnd(at(st["t_s"], st["pad_sinkage_geometric_m"], ts) * 1e3))),
                  "pad_normal_kN": dict(zip(LEGS, rnd(at(st["t_s"], st["scm_pad_normal_N"], ts) / 1e3)))}
    out["pad_sinkage_max_mm"] = dict(zip(LEGS, rnd(st["pad_sinkage_geometric_m"].max(axis=0) * 1e3)))
    return out


def time_check(res, rec, st, duration_s):
    n = int(res["n_steps"])
    expect = int(round((duration_s + SETTLE_S) / DT_S))
    return {"duration_arg_s": (res.get("args") or {}).get("duration"), "n_steps": n, "n_steps_expected": expect,
            "steps_ok": n == expect, "t_loop_start_s": res["t_loop_start_s"],
            "record_t_last_s": round(float(rec["t"][-1]), 4), "record_n": int(rec["t"].size),
            "step_series_t_last_s": round(float(st["t_s"][-1]), 4), "step_series_n": int(st["t_s"].size),
            "wall_s": res.get("wall_s"), "us_per_step": res.get("us_per_step")}


def cmd_identity(case, ref, t_end_abs):
    """controller_commands.npz rows with t < t_end_abs of the reference run: bitwise equality of every array."""
    with np.load(case / "controller_commands.npz") as a, np.load(ref / "controller_commands.npz") as b:
        ta, tb = np.asarray(a["t_s"]), np.asarray(b["t_s"])
        ma, mb = ta < t_end_abs - 1e-9, tb < t_end_abs - 1e-9
        out = {"keys": list(a.files), "rows_case": int(ma.sum()), "rows_ref": int(mb.sum()), "arrays": {}}
        for k in a.files:
            if k not in b.files:
                out["arrays"][k] = "missing in ref"
                continue
            xa, xb = np.asarray(a[k])[ma] if a[k].shape[:1] == ta.shape else np.asarray(a[k]), \
                np.asarray(b[k])[mb] if b[k].shape[:1] == tb.shape else np.asarray(b[k])
            if xa.shape != xb.shape:
                out["arrays"][k] = f"shape {xa.shape} vs {xb.shape}"
                continue
            eq = np.array_equal(xa, xb, equal_nan=True)
            if eq:
                out["arrays"][k] = "equal"
            else:
                d = np.nonzero(~((xa == xb) | (np.isnan(xa) & np.isnan(xb)) if xa.dtype.kind == "f" else xa != xb))
                out["arrays"][k] = {"equal": False, "first_diff_row": int(d[0][0]) if d[0].size else None,
                                    "first_diff_t_s": float(ta[ma][d[0][0]]) if d[0].size else None}
        out["all_equal"] = all(v == "equal" for v in out["arrays"].values())
    return out


def harness_row(path, hid):
    d = json.loads(path.read_text(encoding="utf-8"))
    r = next(r for r in d["records"] if r["id"] == hid)
    keep = ("id", "verdict", "failed_rows", "t_ready_s", "min_force_kN", "att_end_deg", "max_stroke_mm", "final_phase",
            "rut_ready_mm", "crawler_N_max_after_ready", "warnings", "flags", "soil_stop", "metrics")
    return {k: r.get(k) for k in keep}


def judge(name, cfg):
    case = cfg["case"]
    res, rec, st = load_run(case)
    rj = json.loads((case / "result_rejudge_rev60.json").read_text(encoding="utf-8"))
    pm = json.loads(cfg["pmax"].read_text(encoding="utf-8"))["cases"][case.name]
    hz = harness_row(cfg["harness_file"], cfg["harness_id"])
    p3b, chk = rj["p3b"], rj["p3b"]["checks"]
    t0 = float(res["t_loop_start_s"])
    t = rec["t"]
    s_read, s_true, s_ref = rec["meas.stroke"] * 1e3, rec["stroke_true"] * 1e3, rec["s_ref"] * 1e3
    read_max, true_max = s_read.max(axis=0), s_true.max(axis=0)
    leg = int(read_max.argmax())
    i_lead = int(s_read[:, leg].argmax())
    ev = [(float(e["t_s"]), str(e["name"])) for e in res["events"]]
    feat = [{"t_s": round(tt, 2), "t_loop_s": round(tt - t0, 2), "name": n} for tt, n in ev
            if any(k in n for k in FEATURE_TAGS)]
    warn_fault = [f for f in feat if f["name"].startswith(("WARN", "FAULT"))]
    sgs = [f for f in feat if "LIFT_STROKE" in f["name"]]
    r9 = [f for f in feat if "FLAT_SOIL_MARGIN" in f["name"]]
    e3 = [f for f in feat if "LOC_CLEARANCE_MARGIN" in f["name"]]
    ready = p3b["P3-6_ready"]
    att = p3b["P3-4_attitude"]
    force = p3b["P3-3_leg_force"]
    loc = p3b["P3-2_loc"]
    dep = p3b.get("departure") or {}
    ready_phases = [round(float(p["t_s"]) - t0, 2) for p in res["phases"] if str(p["phase"]).upper() == "READY"]
    c_ready_mm = chk["P3-5_rut_clearance_min_after_first_ready_m"] * 1e3
    allow = att["sensor_allowance_left_deg"]
    chrono = {
        "ready_first_s_loop": ready["t_ready_after_loop_start_s"], "ready_limit_s": ready["limit_s"],
        "ready_phases_s_loop": ready_phases,
        "min_force_after_departure_kN": min(force["F_min_after_N"]) / 1e3,
        "min_force_leg": LEGS[int(np.argmin(force["F_min_after_N"]))],
        "gap_after_first_ready_mm": c_ready_mm,
        "end_attitude_absmax_deg": att["p34_absmax_overall_deg"], "end_1s_roll_pitch_deg": att.get("end_mean_roll_pitch_deg"),
        "p34_window_s": att.get("p34_window_length_s"), "p34_window_abs_s": chk.get("P3-4_window_s"),
        "imu_allowance_left_deg": allow, "imu_allowance_vs_0p118": allow >= IMU_RULE_DEG,
        "stroke_reading_max_mm": dict(zip(LEGS, rnd(read_max))),
        "stroke_reading_max_t_loop_s": dict(zip(LEGS, rnd(t[s_read.argmax(axis=0)] - t0))),
        "stroke_true_max_mm": dict(zip(LEGS, rnd(true_max))),
        "s_ref_max_mm": dict(zip(LEGS, rnd(s_ref.max(axis=0)))),
        "reading_minus_sref_at_lead_max_mm": float(s_read[i_lead, leg] - s_ref[i_lead, leg]),
        "lead_leg": LEGS[leg],
        "margin_reading_to_guard_mm": GUARD_MM - float(read_max[leg]),
        "margin_true_to_gate_mm": GATE_MM - float(true_max.max()),
        "margin_reading_to_fault_mm": FAULT_MM - float(read_max[leg]),
        "margin_reading_to_sensor_end_mm": SENSOR_END_MM - float(read_max[leg]),
        "max_moving_pressure_bar": pm["max_moving_pressure_bar"], "max_any_state_bar": pm["max_any_state_bar"],
        "measured_head_max_bar": pm["measured_head_max_bar"], "pressure_peak_leg": pm["peak_leg"],
        "pressure_ratio_180": pm.get("ratio_to_judge_180"),
    }
    rows = {
        "P3-1": {"pass": bool(chk["P3-1_crawler_zero_after_ready"] and chk["P3-1_recontact_pass"]),
                 "recontact_count": dep.get("recontact_count"),
                 "crawler_normal_max_after_confirm_N": dep.get("crawler_normal_max_after_confirm_N")},
        "P3-2": {"verdict": chk["P3-2_verdict"], "loc_minus_departure_s": chk["P3-2_loc_minus_departure_s"],
                 "limit_s": chk["P3-2_limit_s"], "loc_revokes": chk["loc_revokes"],
                 "late_loc_revoked": chk["P3-2_late_loc_revoked"], "soil_mode_used": loc.get("soil_mode_used"),
                 "crawler_normal_at_loc_N": loc.get("crawler_normal_at_loc_N")},
        "P3-3": {"pass": chk["P3-3_within"], "min_kN": chrono["min_force_after_departure_kN"], "F_min_kN": F_MIN_N / 1e3},
        "P3-4": {"pass": chk["P3-4_within_0p2"], "absmax_deg": att["p34_absmax_overall_deg"],
                 "window_short": att.get("window_short"), "creep_vibration_suspect": att.get("creep_vibration_suspect"),
                 "imu_allowance_left_deg": allow},
        "P3-5": {"pass": chk["P3-5_within"], "gap_mm": c_ready_mm, "s_true_max_mm": float(true_max.max()),
                 "gate_mm": GATE_MM},
        "P3-6": {"pass": chk["P3-6_within"], "ready_s_loop": chrono["ready_first_s_loop"], "limit_s": ready["limit_s"]},
        "P3-7": {"pass": chk["P3-7_within"], "rise_min_loaded_N": chk["P3-7_rise_min_loaded_N"], "record_row": True},
        "P3-8": {"pass": chk["P3-8_within"]},
    }
    judged = {k: v for k, v in rows.items() if k != "P3-7"}
    all_ok = all(v.get("pass", v.get("verdict") in ("pass", "flag")) for v in judged.values())
    hs = float(hz["max_stroke_mm"])
    cmp_ = {
        "stroke_controller_quantity_mm": {"harness": hs, "chrono": float(read_max.max()),
                                          "chrono_minus_harness": float(read_max.max()) - hs,
                                          "within_H6_plus23": float(read_max.max()) - hs <= H6_STROKE_MM},
        "guard_margin_mm": {"harness": GUARD_MM - hs, "chrono": GUARD_MM - float(read_max.max())},
        "ready_s": {"harness": hz["t_ready_s"], "chrono": chrono["ready_first_s_loop"],
                    "chrono_minus_harness": chrono["ready_first_s_loop"] - hz["t_ready_s"]},
        "gap_mm": {"harness": hz["rut_ready_mm"], "chrono": c_ready_mm,
                   "chrono_minus_harness": c_ready_mm - hz["rut_ready_mm"]},
        "min_force_kN": {"harness": hz["min_force_kN"], "chrono": chrono["min_force_after_departure_kN"],
                         "ratio_harness_over_chrono": hz["min_force_kN"] / chrono["min_force_after_departure_kN"]},
        "end_attitude_deg": {"harness_end": hz["att_end_deg"], "chrono_absmax": att["p34_absmax_overall_deg"]},
        "verdict": {"harness": hz["verdict"], "chrono": "pass" if all_ok and not warn_fault and not sgs else
                    ("stroke_limited_stop" if sgs else "check")},
    }
    out = {
        "case": case.name, "folder": case.relative_to(ROOT).as_posix(), "harness_id": cfg["harness_id"],
        "controller": (res.get("args") or {}).get("expect_controller"),
        "code_state": (res.get("code_state") or {}).get("state"),
        "mass_scale": res.get("mass_scale"),
        "rejudge": {"unchanged_blocks_equal": rj["unchanged_blocks_equal"], "params_file_match": rj["params_file_match"]},
        "time_check": time_check(res, rec, st, cfg["duration_s"]),
        "classification": "stroke_limited_stop" if sgs else "pass",
        "verdict": "pass" if all_ok and not warn_fault and not sgs else ("stroke_limited_stop" if sgs else "check"),
        "flags": [k for k, v in rows.items() if v.get("verdict") == "flag"],
        "rows": rows, "chrono": chrono, "warn_fault_events": warn_fault, "feature_events": feat,
        "R9_events": r9, "E3c10_events": e3, "SGS_events": sgs,
        "stroke_profile": stroke_profile(res, rec, st),
        "harness": hz, "harness_vs_chrono": cmp_,
    }
    ref = cfg.get("ref")
    if ref is not None and ref.exists():
        rres, rrec, rst = load_run(ref)
        r_read = rrec["meas.stroke"] * 1e3
        rr = {"folder": ref.relative_to(ROOT).as_posix(),
              "stroke_reading_max_mm": dict(zip(LEGS, rnd(r_read.max(axis=0)))),
              "stroke_profile": stroke_profile(rres, rrec, rst),
              "events": [{"t_loop_s": round(float(e["t_s"]) - float(rres["t_loop_start_s"]), 2), "name": e["name"]}
                         for e in rres["events"] if any(k in str(e["name"]) for k in FEATURE_TAGS)]}
        if name == "FINAL-REP-X":
            rr["cmd_identity_before_ref_end"] = cmd_identity(case, ref, cfg["ref_duration_s"] + SETTLE_S)
        if cfg.get("ref_harness_id"):
            rr["harness"] = harness_row(cfg["harness_file"], cfg["ref_harness_id"])
        out["reference_run"] = rr
    return out


result = {"script": "04_scripts/03_control/s9/evidence/final_x_rb2_judge.py",
          "notes": ["Times *_loop_s are loop-relative (absolute - t_loop_start_s = 8.0 s).",
                    "Stroke comparison uses the controller reading (Chrono meas.stroke) vs harness max(plant.sref).",
                    "P3-7 is a record row (400.2 practice); P3-2 FLAG under 419.8 / 424.10.2 counts as within rules.",
                    f"IMU selection rule {IMU_RULE_DEG} deg (U-S9P-16, user decision 2026-10-31); H-6 stroke "
                    f"+{H6_STROKE_MM} mm (432.4.5)."]}
for n, c in CASES.items():
    result[n] = judge(n, c)
OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
for n in CASES:
    o = result[n]
    print("==", n, o["verdict"], o["classification"], "flags", o["flags"])
    print(" time", json.dumps(o["time_check"]))
    print(" rows", json.dumps(o["rows"], default=float))
    print(" chrono", json.dumps(o["chrono"], default=float))
    print(" cmp", json.dumps(o["harness_vs_chrono"], default=float))
    print(" feat", o["feature_events"])
    print(" profile", json.dumps(o["stroke_profile"]))
    if "reference_run" in o:
        rr = o["reference_run"]
        print(" ref", rr["folder"], rr["stroke_reading_max_mm"])
        print(" ref profile", json.dumps(rr["stroke_profile"]))
        print(" ref events", rr["events"])
        if "cmd_identity_before_ref_end" in rr:
            print(" cmd identity", json.dumps(rr["cmd_identity_before_ref_end"]))
        if "harness" in rr:
            print(" ref harness", rr["harness"]["max_stroke_mm"], rr["harness"]["verdict"])
