"""FINAL6 (spec 426.9.D.1 (가), 432.x): judge the final-controller Chrono run P3b_J2_B_top_Fs4_sgRRd150
(= harness H8|J2|B|top|flat|RR:d150) and compare it with the harness prediction (d_r4_cmp.json).

Inputs (all read-only):
  <case>/result.json, <case>/result_rejudge_rev60.json (run_S9.py rejudge), <case>/record/record.npz,
  <evidence>/final6_sgRRd150_pmax.json (final_rep_pmax.py), <evidence>/d_r4_cmp.json (d_r4_cmp.py).
Stroke quantities (same names as the controller / judge):
  - controller reading = record 'meas.stroke' (motor stroke; the R1 lift stroke guard and the R7 stroke release compare
    this with s_g = 682.8 mm / 642.8 mm, c2.py _lift_guarded_legs / _diff_sink_stroke_limit_m); the harness
    max_motor_stroke_mm is max(plant.sref) = the same controller-side quantity;
  - true rod stroke = record 'stroke_true' (= p3b P3-5 s_motor_max_m within 0.2 mm), judged against the 684.8 mm gate.
Usage: python -I final6_d150_judge.py <repo root> <out json>
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
CASE = ROOT / "07_results/S9/batch_FINAL6_20261031_000833/P3b_J2_B_top_Fs4_sgRRd150"
EV = ROOT / "06_analysis/02_control/s9/rev85/evidence"
HARNESS_ID = "H8|J2|B|top|flat|RR:d150"
LEGS = ("FL", "FR", "RL", "RR")
GUARD_MM, GATE_MM, FAULT_MM, SENSOR_END_MM, DS_RELEASE_MM = 682.8, 684.8, 693.8, 694.8, 642.8
F_MIN_N = 9415.0
FEATURE_TAGS = ("WARN", "FAULT", "FLAT_SOIL_MARGIN", "LOC_CLEARANCE", "LOC_REVOKED", "DIFF_SINK", "TWIST_UNSETTLED",
                "LIFT_PAUSED", "LOC_WINDOW", "LIFT_STROKE")

res = json.loads((CASE / "result.json").read_text(encoding="utf-8"))
rj = json.loads((CASE / "result_rejudge_rev60.json").read_text(encoding="utf-8"))
pmax = json.loads((EV / "final6_sgRRd150_pmax.json").read_text(encoding="utf-8"))["cases"][CASE.name]
harness = {r["id"]: r for r in json.loads((EV / "d_r4_cmp.json").read_text(encoding="utf-8"))}[HARNESS_ID]
p3b = rj["p3b"]
chk = p3b["checks"]
t0 = float(res["t_loop_start_s"])

with np.load(CASE / "record" / "record.npz") as z:
    t = np.asarray(z["t"])
    s_read = np.asarray(z["meas.stroke"]) * 1e3
    s_true = np.asarray(z["stroke_true"]) * 1e3
i_read, i_true = s_read.argmax(axis=0), s_true.argmax(axis=0)
read_max, true_max = s_read.max(axis=0), s_true.max(axis=0)
leg = int(read_max.argmax())

events = [(float(e["t_s"]), str(e["name"])) for e in res["events"]]
feat = [{"t_s": round(tt, 2), "t_loop_s": round(tt - t0, 2), "name": n} for tt, n in events
        if any(k in n for k in FEATURE_TAGS)]
warn_fault = [f for f in feat if f["name"].startswith(("WARN", "FAULT"))]
sgs = [f for f in feat if "LIFT_STROKE" in f["name"]]
r9 = [f for f in feat if "FLAT_SOIL_MARGIN" in f["name"]]
ds_rel = [f for f in feat if f["name"].startswith("INFO_DIFF_SINK_RELEASE")]
ds_read = None
if ds_rel:
    j = int(np.argmin(abs(t - ds_rel[0]["t_s"])))
    ds_read = {"t_s": round(float(t[j]), 2), "reading_mm": dict(zip(LEGS, np.round(s_read[j], 1).tolist())),
               "true_mm": dict(zip(LEGS, np.round(s_true[j], 1).tolist())), "release_limit_mm": DS_RELEASE_MM}

ready = p3b["P3-6_ready"]
att = p3b["P3-4_attitude"]
force = p3b["P3-3_leg_force"]
loc = p3b["P3-2_loc"]
dep = p3b.get("departure") or {}
c_ready_m = chk["P3-5_rut_clearance_min_after_first_ready_m"]
chrono = {
    "ready_s_loop": ready["t_ready_after_loop_start_s"], "ready_limit_s": ready["limit_s"],
    "min_force_after_departure_kN": min(force["F_min_after_N"]) / 1e3,
    "min_force_leg": LEGS[int(np.argmin(force["F_min_after_N"]))],
    "gap_after_first_ready_mm": c_ready_m * 1e3,
    "end_attitude_absmax_deg": att["p34_absmax_overall_deg"], "end_1s_roll_pitch_deg": att["end_mean_roll_pitch_deg"],
    "p34_window_s": att["p34_window_length_s"], "imu_allowance_left_deg": att["sensor_allowance_left_deg"],
    "stroke_reading_max_mm": dict(zip(LEGS, np.round(read_max, 2).tolist())),
    "stroke_reading_max_t_loop_s": dict(zip(LEGS, np.round(t[i_read] - t0, 2).tolist())),
    "stroke_true_max_mm": dict(zip(LEGS, np.round(true_max, 2).tolist())),
    "p35_s_motor_max_mm": [round(v * 1e3, 2) for v in p3b["P3-5_clearance_stroke"]["s_motor_max_m"]],
    "margin_reading_to_guard_mm": GUARD_MM - float(read_max[leg]),
    "margin_true_to_gate_mm": GATE_MM - float(true_max.max()),
    "margin_reading_to_fault_mm": FAULT_MM - float(read_max[leg]),
    "margin_reading_to_sensor_end_mm": SENSOR_END_MM - float(read_max[leg]),
    "margin_true_to_sensor_end_mm": SENSOR_END_MM - float(true_max.max()),
    "max_moving_pressure_bar": pmax["max_moving_pressure_bar"], "max_any_state_bar": pmax["max_any_state_bar"],
    "measured_head_max_bar": pmax["measured_head_max_bar"], "pressure_peak_leg": pmax["peak_leg"],
}
same_q = {
    "stroke_controller_quantity_mm": {"harness": harness["s_new"], "chrono": float(read_max.max()),
                                      "chrono_minus_harness": float(read_max.max()) - harness["s_new"]},
    "stroke_harness_vs_chrono_true_mm (mixed quantity, former 432.4 practice)": {
        "harness": harness["s_new"], "chrono": float(true_max.max()),
        "chrono_minus_harness": float(true_max.max()) - harness["s_new"]},
    "guard_margin_mm": {"harness": GUARD_MM - harness["s_new"], "chrono": GUARD_MM - float(read_max.max())},
    "ready_s": {"harness": harness["ready_new"], "chrono": chrono["ready_s_loop"],
                "chrono_minus_harness": chrono["ready_s_loop"] - harness["ready_new"]},
    "gap_mm": {"harness": harness["gap_new"], "chrono": chrono["gap_after_first_ready_mm"],
               "chrono_minus_harness": chrono["gap_after_first_ready_mm"] - harness["gap_new"]},
    "min_force_kN": {"harness": harness["minF_new"], "chrono": chrono["min_force_after_departure_kN"],
                     "ratio_harness_over_chrono": harness["minF_new"] / chrono["min_force_after_departure_kN"]},
    "R9_applied": {"harness": harness["r4"], "chrono": bool(r9)},
    "guard_events": {"harness": harness["guard"], "chrono": [f["name"] for f in sgs]},
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
             "window_short": att["window_short"], "creep_vibration_suspect": att["creep_vibration_suspect"],
             "imu_allowance_left_deg": att["sensor_allowance_left_deg"],
             "imu_allowance_vs_U_S9P_16_0p119": att["sensor_allowance_left_deg"] >= 0.119},
    "P3-5": {"pass": chk["P3-5_within"], "gap_mm": chrono["gap_after_first_ready_mm"],
             "s_true_max_mm": float(true_max.max()), "gate_mm": GATE_MM},
    "P3-6": {"pass": chk["P3-6_within"], "ready_s_loop": chrono["ready_s_loop"], "limit_s": ready["limit_s"]},
    "P3-7": {"pass": chk["P3-7_within"], "rise_min_loaded_N": chk["P3-7_rise_min_loaded_N"]},
    "P3-8": {"pass": chk["P3-8_within"]},
}
all_pass = all(v.get("pass", v.get("verdict") == "pass") for v in rows.values())
out = {
    "case": CASE.name, "folder": CASE.relative_to(ROOT).as_posix(), "harness_id": HARNESS_ID,
    "controller": (res.get("args") or {}).get("expect_controller"),
    "code_state": (res.get("code_state") or {}).get("state"),
    "rejudge": {"unchanged_blocks_equal": rj["unchanged_blocks_equal"], "params_file_match": rj["params_file_match"],
                "inputs_sha256": rj["inputs_sha256"]},
    "wall_s": res.get("wall_s"), "t_loop_start_s": t0,
    "phases": [(round(float(p["t_s"]) - t0, 2), p["phase"]) for p in res["phases"]],
    "verdict": "pass" if all_pass and not warn_fault else "check",
    "classification": "pass" if not sgs else "stroke_limited_stop",
    "rows": rows, "chrono": chrono, "warn_fault_events": warn_fault, "feature_events": feat,
    "R7_stroke_release": ds_read, "harness_vs_chrono": same_q,
    "notes": [
        "Times *_loop_s are loop-relative (absolute - t_loop_start_s).",
        "Same-quantity stroke comparison is controller reading (Chrono meas.stroke) vs harness max(plant.sref); the "
        "P3-5 / 432.4 Chrono stroke (s_motor_max_m) is the true rod stroke, about 5-6 mm below the reading "
        "(oil / contact compliance F/k at about 68 kN on RR).",
    ],
}
OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
print(json.dumps({k: out[k] for k in ("verdict", "classification")}, ensure_ascii=False))
print(json.dumps(rows, ensure_ascii=False, default=float))
print(json.dumps(same_q, ensure_ascii=False, default=float))
print("margins", {k: round(v, 2) for k, v in chrono.items() if k.startswith("margin")})
print("R7 release", ds_read)
print("warn/fault", warn_fault, "sgs", sgs, "r9", r9)
