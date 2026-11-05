"""Assemble k1soil_values.json in the judgement folder and compare the Julia metrics with the stored judge and a numpy recomputation of the same rows.
Tolerances: against the stored judge = its rounding (0.005 kN, 0.0005 s + one 1 ms sample where the interval convention differs); numpy vs Julia, relative 1e-9."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono\k1soil\k1soil_values.json")
BATCH = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_k1soil_G1_20261105")
LEGS = ("FL", "FR", "RL", "RR")
raw = json.loads((HERE / "raw_values.json").read_text(encoding="utf-8"))
a2 = json.loads((HERE / "analyze2.json").read_text(encoding="utf-8"))
a3 = json.loads((HERE / "analyze3.json").read_text(encoding="utf-8"))
r9 = json.loads((HERE / "replay_item9.json").read_text(encoding="utf-8"))
osc = json.loads((HERE / "osc.json").read_text(encoding="utf-8"))
work = json.loads((HERE / "work.json").read_text(encoding="utf-8"))
jl = json.loads((HERE / "xval" / "julia_metrics.json").read_text(encoding="utf-8"))
idx = json.loads((HERE / "xval" / "index.json").read_text(encoding="utf-8"))

worst = {"stored_force_kN": 0.0, "stored_time_s": 0.0, "numpy_julia_rel": 0.0}
detail = {}
for key, v in idx.items():
    tag, s = key.split("_", 1)
    j = raw[tag]["rows"][s]["judgement"]
    J = jl[key]
    r = np.fromfile(v["path"], dtype="<f8").reshape(-1, 9)
    t = r[:, 0] - v["t_ev"]
    F = r[:, 5:9]
    post = t > J["W_end_s"]
    for i, leg in enumerate(LEGS):
        np_min = float(F[post, i].min()) / 1e3
        worst["numpy_julia_rel"] = max(worst["numpy_julia_rel"], abs(np_min - J["min_F_after_W_kN"][leg]) / max(abs(np_min), 1e-9))
        worst["stored_force_kN"] = max(worst["stored_force_kN"], abs(J["min_F_after_W_kN"][leg] - j["min_F_after_W_kN"][leg]), abs(J["min_F_after_event_kN"][leg] - j["min_F_after_event_kN"][leg]))
    for leg, val in J["adj_min_F_in_W_kN"].items():
        worst["stored_force_kN"] = max(worst["stored_force_kN"], abs(val - j["adj_min_F_in_W_kN"][leg]))
    d_t = [abs(J["pair_union_s"] - j["pair_union_s"]), abs(J["pair_last_touch_s"] - j["pair_last_touch_s"]), abs(J["W_end_s"] - j["W_end_s"])]
    for leg, val in j["lifts"].items():
        d_t += [abs(J["lifts"][leg]["sum_s"] - val["sum_s"]), abs(J["lifts"][leg]["last_touch_s"] - val["last_touch_s"])]
    worst["stored_time_s"] = max(worst["stored_time_s"], *d_t)
    detail[key] = {"julia_pair_union_s": J["pair_union_s"], "stored_pair_union_s": j["pair_union_s"], "julia_last_touch_s": J["pair_last_touch_s"], "stored_last_touch_s": j["pair_last_touch_s"], "julia_margin_Fmin_after_W_kN": J["margin_Fmin_after_W_kN"], "stored_margin_kN": j["margins"]["Fmin_after_W_minus_Fmin_kN"]}
print(json.dumps(worst), json.dumps(detail, indent=0)[:1800])

rows = {}
for tag in ("FLFs0", "FLFs8", "RRFs0"):
    o = raw[tag]
    rows[tag] = {"leg": o["leg"], "fs_kN": o["fs_kN"], "command_first_diff": o["pair"], "completion_after_event": a2[tag]["completion"], "after_W_with_times": a2[tag]["after_W"], "common_window": a2[tag]["common_window"], "pre_event": a2[tag]["pre_event"],
                 "C_S8_41": a3["cs841"][tag], "harness": a3["harness"][tag], "tail_creep": a3["creep"][tag], "D_profile_after_event_kN": work[f"D_profile_{tag}"]}
    for s, r in o["rows"].items():
        rows[tag][s] = {k: r.get(k) for k in ("case", "config_name", "c2_sha256", "config", "retrigger_samples", "hold_enabled", "hold", "main_tree_modules_at_end", "wall_s", "t_loop_start_s", "phases", "t_ev_s", "trigger", "prefix_check", "driver", "commands_sha", "judgement", "series", "events_rel", "history", "p3b_checks", "D_raw_at_ev_kN", "D_loop_at_ev_kN")}
values = {"scope": "K1 soil Chrono batch 20261105, values from stored runs only. No simulation. Feedback negative, controller T_s 0.1 s, d = 1, flow limit off. F_cyl = rod axial force, 1 ms, not a load.",
          "code": {"runs": "74032be, c2.py sha256 28482b8d...", "item_9_replay": r9["code"]}, "F_min_N": 9414.6, "rows": rows, "item_9": r9["rows"], "ready_tail": {k: v for k, v in osc.items()}, "tail_work": {k: v for k, v in work.items() if k.startswith("FL") and "hold" not in k}, "hold_command_twist": {k: v for k, v in work.items() if k.startswith("hold_")},
          "cross_check": {"path": "Julia 1.13.2 via julia-mcp, control-julia project, xval.jl on the same exported rows", "worst": worst, "detail": detail, "note": "Arithmetic on stored rows only; not an independent simulation."}}
OUT.write_text(json.dumps(values, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("written", OUT, OUT.stat().st_size)
