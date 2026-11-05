"""G8C3 judgement numbers: guard-coordinate strokes, line constants a, bound b <= c_RL(t_P) + 5 mm, stop threshold, pre-set criteria. Writes g8c3_judgement.json."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono\g8c3")
B = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_g8c3_20261105")
c2o = json.loads((HERE / "c2_out.json").read_text(encoding="utf-8"))
vals = json.loads((OUT / "g8c3_values.json").read_text(encoding="utf-8"))
SLOPE = 1.0066
rows = {}
by_row = {x["row"]: (cid, x) for cid, x in vals["extra"].items()}
for name in ("A3off", "E1", "R2L1", "R3L1", "R2", "R3"):
    o = c2o[name]
    fr = o["coords_FR_max_mm"]["meas_stroke_guard"]
    b = o["anchor_FL_FR_RL_RR"][2]
    c = o["c_tP_FL_FR_RL_RR"][2]
    a_max = fr - SLOPE * b
    a_pred = o["pred_at_done"] - SLOPE * b
    thr = (682.8 - a_pred) / SLOPE
    bound = c + 5.0
    row = dict(FR_guard_max_mm=fr, FR_values_file_mm=o["coords_FR_max_mm"]["record_s_motor"], b_RL=b, c_RL_tP=c, a_max=round(a_max, 2), pred_at_done=o["pred_at_done"], guard_margin_at_done_mm=o["guard_margin_mm"],
               b_stop=round(thr, 2), b_upper_bound=round(bound, 2), bound_to_stop_mm=round(thr - bound, 2), t_P=round(o["t_P"], 1), t_loc=round(o["t_loc"], 1), since_level=round(o["t_P"] - o["t_level"], 1), cc_tP=round(o["cc_tP"], 2), cc_loc=round(o["cc_loc"], 2), cc_done=round(o["cc_done"], 2),
               cc_end=round(o["cc_end"], 2), ce_done=o["ce_at_done"], overlift=round(o["cc_done"] - o["ce_at_done"], 1), recon_err_mm=o["recon_err_mm"], neighbours=o["neighbours"])
    if name in by_row:
        cid, x = by_row[name]
        m = vals["metrics"][cid]
        side = json.loads((B / cid / "g8c_job_side.json").read_text(encoding="utf-8"))
        row.update(min_kN=m["min_cyl_after_liftoff"]["min_kN"], min_leg=m["min_cyl_after_liftoff"]["leg"], per_leg=m["min_cyl_after_liftoff"]["per_leg_kN"], ready=m["times_s"]["ready"], hold=x["hold"], pauses=x["pauses"], reapproach=len(x["reapproach"]), guard=x["guard"],
                   lift=m["lift_after_liftoff_s"], att_end=m["att_end_mean_deg"], stroke_gate_max=max(m["stroke_max_mm"]), c2_sha=side["c2_sha256"], main_tree=side["main_tree_modules_at_end"], redirected=len(side["redirected"]), seed=x["seed"], grade=x["grade"])
    rows[name] = row
    print(name, {k: v for k, v in row.items() if k not in ("neighbours", "per_leg", "hold", "pauses", "guard", "lift")})
pairs = {}
for label, on, off in (("edge L1-R F_s 0", "E1", "A3off"), ("rpB L1-R F_s 0", "R3L1", "R2L1"), ("rpB L2b F_s 4", "R3", "R2")):
    x, y = rows[on], rows[off]
    d = x["FR_guard_max_mm"] - y["FR_guard_max_mm"]
    db = x["b_RL"] - y["b_RL"]
    pairs[label] = dict(dFR=round(d, 2), db=round(db, 2), residual=round(d - SLOPE * db, 3), slope=round(d / db, 4))
    print(label, pairs[label])
harness = {"off_L1": dict(FR=684.28, b=-61.0, c=-62.03, pred=682.11), "on_L1": dict(FR=683.30, b=-62.2, c=-62.38, pred=681.13)}
for k, h in harness.items():
    h["a_max"] = round(h["FR"] - SLOPE * h["b"], 2)
    h["b_stop"] = round((682.8 - (h["pred"] - SLOPE * h["b"])) / SLOPE, 2)
    h["b_upper_bound"] = h["c"] + 5
    print(k, h)
criteria = {"judge_rows_failed": len(vals["failed_rows"]), "flags": vals["flags"], "n_rows": len(vals["rows"])}
print(criteria)
(OUT / "g8c3_judgement.json").write_text(json.dumps({"code": "74032be, c2 sha 28482b8d, K1 off, flow limit off, negative feedback, T_s 0.1 s, d = 1, ideal sensors, seed 12345", "slope_from_harness": SLOPE, "rows": rows, "pairs": pairs, "harness_L1": harness, "criteria": criteria}, indent=1, default=float), encoding="utf-8")
