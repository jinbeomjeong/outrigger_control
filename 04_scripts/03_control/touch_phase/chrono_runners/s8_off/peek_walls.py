"""Stored walls of the flow-off and flow-on S8 soil rows, for the budget figures of the report. Read only."""
import json
from pathlib import Path

S9 = Path(r"C:\workspace\outrigger_control\07_results\S9")
CASE = "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0"
for b in ("batch_FINAL-REP_20261030_223359", "batch_COUPLED_eta085_20261104_142213"):
    r = json.loads((S9 / b / CASE / "result.json").read_text(encoding="utf-8"))
    print(b, {k: r.get(k) for k in ("wall_s", "settle_wall_s", "loop_wall_s", "n_steps", "us_per_step", "t_loop_start_s")},
          "placement", str(r.get("placement"))[:160], "phases", [(round(p["t_s"], 1), p["phase"]) for p in r["phases"]],
          "loc", [round(e["t_s"], 1) for e in r["events"] if e["name"] == "crawler_liftoff_confirmed"])
