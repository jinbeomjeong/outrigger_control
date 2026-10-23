"""Assemble 06_analysis/00_dynamics/s6_control_spec.json from the scratch results (envelope check + target sims)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

S = Path(sys.argv[1])
OUT = Path(sys.argv[2])

env = json.loads((S / "envelope_check.json").read_text())
runs = []
for name in ("target_sim.json", "target_sim_change2.json", "target_sim_change3.json"):
    runs += json.loads((S / name).read_text())["runs"]

KEYS = ("id", "group", "level", "floor_deg", "target_deg", "change", "ra_mode", "contact", "fails",
        "t_touch_s", "t_done_s", "t_ready_s", "t_level_after_touch_s", "ready_times_s", "changed_at_s",
        "t_change_to_ready_s", "min_true_cyl_force_kN", "min_true_leg", "max_pressure_bar", "stroke_limit_steps",
        "force_sat_210bar_steps", "s_max_seen_mm", "s_final_mm", "s_overshoot_mm", "s_max_after_change_mm",
        "min_true_crawler_clearance_after_change_mm", "min_true_cyl_after_change_kN",
        "att_overshoot_after_change_deg", "ss_err_vs_target_deg", "final_clearance_mm", "ra", "ra_reruns")
compact = [{k: r.get(k) for k in KEYS if k in r} for r in runs if "error" not in r]
errors = [r["id"] for r in runs if "error" in r]


def pick(prefix):
    return [r for r in compact if r["id"].startswith(prefix)]


def mx(rs, key):
    return max(r[key] for r in rs if r.get(key) is not None)


def mn(rs, key):
    return min(r[key] for r in rs if r.get(key) is not None)


A = pick("A|") + pick("reg|")
B = pick("B|")
reg = {r["id"]: r for r in pick("reg|")}
q11 = {"t_done_s": 36.06, "t_reanchor_start_s": 38.10, "t_reanchor_end_s": 52.58, "t_ready_s": 53.64,
       "stop_readings_kN": [44.73, 32.32, 32.39, 32.21], "Ft_final_max_kN": 16.81, "min_true_kN": 29.61}
r0 = reg["reg|V:pitch+3.5|t0|rel"]
reg_check = {
    "reference": "c2_design.md 17.7 Q11 (reduced model, top, nose-down 3.5 deg, rigid, seed 12345, d1, pressure)",
    "this_run": {"t_done_s": r0["t_done_s"], "t_reanchor_start_s": r0["ra"]["t_start_s"],
                 "t_reanchor_end_s": r0["ra"]["t_end_s"], "t_ready_s": r0["t_ready_s"],
                 "stop_readings_kN": r0["ra"]["stop_readings_kN"], "Ft_final_max_kN": max(r0["ra"]["Ft_final_kN"]),
                 "min_true_kN": r0["ra"]["min_true_cyl_post_liftoff_substep_kN"]},
    "q11": q11,
}
reg_check["match"] = (abs(reg_check["this_run"]["t_ready_s"] - q11["t_ready_s"]) < 1e-9
                      and reg_check["this_run"]["stop_readings_kN"] == q11["stop_readings_kN"]
                      and abs(reg_check["this_run"]["Ft_final_max_kN"] - q11["Ft_final_max_kN"]) < 1e-9)

trig = {}
for r in B:
    nm, mode = r["id"].rsplit("|", 1)
    trig.setdefault(nm[2:], {})[mode] = {
        "outcome": r["ra"]["outcome"], "theta_c_abs_deg": r["ra"]["theta_crawler_abs_deg"],
        "theta_rel_deg": r["ra"]["theta_ground_deg"], "Ft_at_done_max_kN": max(r["ra"]["Ft_at_done_kN"]),
        "Ft_final_max_kN": max(r["ra"]["Ft_final_kN"]), "Ft_final_kN": r["ra"]["Ft_final_kN"],
        "min_true_kN": r["ra"]["min_true_cyl_post_liftoff_substep_kN"], "t_level_after_touch_s": r["t_level_after_touch_s"]}

chg = {}
for r in pick("C|") + pick("C2|") + pick("C3|"):
    chg[r["id"]] = {"t_change_to_ready_s": r.get("t_change_to_ready_s"),
                    "min_true_crawler_clearance_after_change_mm": r.get("min_true_crawler_clearance_after_change_mm"),
                    "s_max_after_change_mm": max(r["s_max_after_change_mm"]) if r.get("s_max_after_change_mm") else None,
                    "s_final_max_mm": max(r["s_final_mm"]),
                    "min_true_cyl_after_change_kN": r.get("min_true_cyl_after_change_kN"),
                    "att_overshoot_after_change_deg": r.get("att_overshoot_after_change_deg"),
                    "ss_err_vs_target_deg": r.get("ss_err_vs_target_deg"),
                    "Ft_final_max_kN": max(r["ra"]["Ft_final_kN"]), "reanchor": r["ra"]["outcome"],
                    "ra_reruns": r.get("ra_reruns"), "fails": r["fails"]}

over = [{"id": r["id"], "s_max_mm": max(r["s_max_seen_mm"]), "s_final_max_mm": max(r["s_final_mm"]),
         "overshoot_mm": r["s_overshoot_mm"], "left_to_680_mm": round(680 - max(r["s_max_seen_mm"]), 2),
         "reanchor": r["ra"]["outcome"], "min_true_kN": r["min_true_cyl_force_kN"],
         "ss_err_vs_target_deg": r["ss_err_vs_target_deg"], "max_pressure_bar": r["max_pressure_bar"],
         "fails": r["fails"]} for r in A]

spec = {
    "meta": {
        "title": "S6 control specification, numerical basis (control-expert, 2026-10-21)",
        "doc": "00_docs/04_control/s6_control_spec.md",
        "conventions": "body x fwd, y left, z up; roll > 0 left up, pitch > 0 nose down; floor slope = attitude on the "
                       "crawler; leg speed > 0 = extension; negative feedback u = -K y in all C2 channels; discrete "
                       "T = 20 ms ZOH, plant dt 5e-4 s (reduced 6-DoF), 1 step extra delay + 0.1 s output ramp; "
                       "SI inside, mm / kN / deg / bar in this file",
        "plant": "reduced 6-DoF + crawler layout D + pad tangential bushing (run_pad_tangential_check.TPlant), rigid "
                 "mast, case C mass, beta 1.0 GPa, F_s 0, IMU ideal, seed 12345",
        "controller": "run_c2_reanchor.C2RN (C2 R1 'R:BS_hold' + REANCHOR H4) wrapped by scratch C2RT: target offset "
                      "on the measured attitude, REANCHOR trigger rel/abs/off, target change after READY, target ramp",
        "scripts_scratch": ["s6_envelope_check.py", "s6_target_sim.py", "s6_summary.py", "s6_build_spec_json.py"],
        "inputs_read_only": ["06_analysis/00_dynamics/target_envelope.json", "02_params/rexome33.yaml",
                             "04_scripts/03_control/run_c2_reanchor.py (+ imports)"],
        "n_runs": len(runs), "errors": errors,
    },
    "regression_zero_target": reg_check,
    "envelope_rule_A": env,
    "overshoot_runs": over,
    "overshoot_summary": {
        "max_overshoot_no_reanchor_mm": max(o["overshoot_mm"] for o in over if not str(o["reanchor"]).startswith("completed")),
        "max_overshoot_with_reanchor_mm": max(o["overshoot_mm"] for o in over if str(o["reanchor"]).startswith("completed")),
        "worst_s_max_mm_accepted_rule_A_runs": max(o["s_max_mm"] for o in over if not o["id"].startswith(("A|V:", "reg|"))),
        "worst_s_max_mm_verification_vertex": max(o["s_max_mm"] for o in over if o["id"].startswith(("A|V:", "reg|"))),
        "min_true_kN": min(o["min_true_kN"] for o in over),
        "max_ss_err_vs_target_deg": max(o["ss_err_vs_target_deg"] for o in over),
        "max_pressure_bar": max(o["max_pressure_bar"] for o in over),
        "fails": sorted({f for o in over for f in o["fails"]}),
    },
    "reanchor_trigger": trig,
    "target_change": chg,
    "runs_compact": compact,
}
# ---------------------------------------------------------------- Chrono S6 run matrix and wall-clock estimate
# ASSUMPTIONS: L1 dt 2e-4 s; pad-bearing 160 us/step -> 0.80 s wall per sim s; crawler-bearing 70 us/step -> 0.35;
# 10 s process start + model build per case; crawler settle 65.5 s (YAML settle_on_crawler_min_s) once per
# (level, floor) snapshot; phase lengths from the reduced model (touch ~17 s of which ~15 s crawler-bearing,
# levelling 18 s without / 37 s with REANCHOR, combined probe 6 s, 10 s after READY, settle scenario +40 s,
# target change +60 s); 7 concurrent P-core processes at the single-process step cost.
W_PAD, W_CRW, W_START = 0.80, 0.35, 10.0


def wall(pad_s, crawler_s=15.0):
    return round(W_START + pad_s * W_PAD + crawler_s * W_CRW, 1)


L_NORA, L_RA, PROBE, POST = 18.0, 37.0, 6.0, 10.0
groups = [
    # id, items, n, pad seconds per case, note
    ("G1_reduced_compare", "1", 3, 2 + L_NORA + POST, "top x {flat, diag 3, roll +3}, pressure"),
    ("G2_core", "2,3,4,5,7,8", 6, 2 + L_NORA + PROBE + POST, "3 levels x {flat, roll +5.5}, ideal IMU, combined"),
    ("G2_core_RA", "2,3,4,5,7,8,R", 6, 2 + L_RA + PROBE + POST, "3 levels x {nose-down 3.5, nose-up 3.5}, combined"),
    ("G3_grades_flat", "2", 4, 2 + L_NORA + PROBE + POST, "top flat x {excellent, normal, normal+rep, factory}"),
    ("G3_grades_RA", "2", 3, 2 + L_RA + PROBE + POST, "top nose-down 3.5 x {excellent, normal, normal+rep}"),
    ("G4_settle", "6", 2, 2 + L_NORA + POST + 40.0, "top flat RR 11.5 mm, pressure / combined"),
    ("G5_target", "T", 2, 2 + L_RA + PROBE + POST + 30.0, "top flat target pitch +3 (rel H4); 0 -> +3 change w/ ramp"),
    ("G5_reject", "T", 1, 0.0, "start rejected (target (4, 3)): 5 s, no motion"),
    ("G6_slope_friction", "R,1", 4, 2 + L_RA + POST, "top +-3.5 x H4 on/off, pressure, 1 ms pad record"),
]
matrix = []
serial = 0.0
for gid, items, n, pad_s, note in groups:
    w = wall(pad_s) if pad_s > 0 else 15.0
    matrix.append({"group": gid, "items": items, "runs": n, "sim_pad_s_per_run": pad_s, "wall_s_per_run": w,
                   "wall_s_total": round(n * w, 1), "note": note})
    serial += n * w
settles = 14        # unique (level, floor): top 6 (flat, +-3.5, roll 5.5, diag 3, roll 3), middle / bottom 4 each
settle_wall = settles * (W_START + 65.5 * W_CRW)
serial += settle_wall
n_runs = sum(g[2] for g in groups)
spec["chrono_matrix"] = {
    "assumptions": "dt 2e-4 s; 0.80 s/s pad-bearing (160 us/step), 0.35 s/s crawler-bearing (70 us/step); 10 s start "
                   "per process; settle snapshot 65.5 s per (level, floor); 7 concurrent P-core processes",
    "groups": matrix, "runs": n_runs, "settle_snapshots": settles, "settle_wall_s": round(settle_wall, 1),
    "serial_wall_s": round(serial, 1), "parallel7_wall_s_ideal": round(serial / 7, 1),
    "parallel7_wall_s_with_imbalance": round(serial / 7 * 1.3 + 100, 1),
    "full_item2_matrix_extra": {"runs": 60 - 6 - 6 - 7, "note": "3 levels x 4 floors x 5 grades minus the runs above",
                                "wall_s_serial": round((60 - 19) * wall(2 + 27 + PROBE + POST), 1)},
}
OUT.write_text(json.dumps(spec, indent=1, ensure_ascii=False))
print(json.dumps(spec["chrono_matrix"], indent=1))
print(json.dumps(spec["overshoot_summary"], indent=1))
print("regression match", reg_check["match"], "errors", errors)
