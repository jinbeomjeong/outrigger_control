"""Inspect rejudge file layout, event record format, p3b keys, and the structure of soil_event.base across the rows."""
import json
from pathlib import Path

BATCH = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_k1soil_G1_20261105")
CH = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono")
rj = json.loads((CH / "c4g2_k1_replay_rejudge.json").read_text(encoding="utf-8"))
print("REJ top", list(rj) if isinstance(rj, dict) else type(rj))
print(json.dumps(rj, default=str)[:2500])
for name in ("S9EV_G1_FLFs0_RE1bF_off", "S9EV_G1_FLFs8_RE1bF_on", "S9EV_G1_RRFs0_RE1bF_on", "S9EV_G1_FLFs0_base"):
    res = json.loads((BATCH / name / "result.json").read_text(encoding="utf-8"))
    print("=====", name)
    se = res.get("soil_event")
    print("base", json.dumps(se.get("base") if se else None, default=str)[:800])
    print("phases", json.dumps(res["phases"], default=str)[:700])
    ev = res["events"]
    print("events n", len(ev), json.dumps(ev[:3], default=str)[:400])
    print("history n", len(res["c2_lifted_reapproach_history"]), json.dumps(res["c2_lifted_reapproach_history"], default=str)[:1200])
    print("lifted", json.dumps(res["c2_lifted_reapproach"], default=str)[:800])
    print("p3b keys", list(res["p3b"]))
    print("p3b_ext keys", list(res["p3b_ext"]))
    print("p3_records keys", list(res["p3_records"]))
    print("controller_meta keys", list(res["controller_meta"]))
    print("code_state", json.dumps(res["code_state"], default=str)[:400])
    print("s9_rows n", len(res["s9_rows"]), json.dumps(res["s9_rows"][:2], default=str)[:600])
    print("hold", json.dumps(res["controller_meta"].get("touch_twist_hold"), default=str)[:400])
