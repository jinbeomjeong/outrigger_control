"""Read the stored flow-off and flow-on S8 soil runs (arguments, phases, events, batch layout). Read only."""
import json
from pathlib import Path

S9 = Path(r"C:\workspace\outrigger_control\07_results\S9")
CASE = "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0"
for b in sorted(S9.glob("*")):
    if (b / CASE / "result.json").exists():
        print("HAS", b.name)
d = S9 / "batch_FINAL-REP_20261030_223359" / CASE
print(sorted(p.name for p in d.iterdir()))
print(sorted(p.name for p in d.parent.iterdir())[:12])
r = json.loads((d / "result.json").read_text(encoding="utf-8"))
print("top keys", list(r)[:70])
print("args", json.dumps(r.get("args"))[:1800])
print("phases", json.dumps(r.get("phases"))[:900])
ev = r.get("events") or r.get("controller_events") or []
print("events", json.dumps(ev)[:1400])
print("code_state", json.dumps(r.get("code_state"))[:400])
for k in ("t0_s", "loop_start_s", "start_t_s", "wall_s", "runner"):
    if k in r:
        print(k, str(r[k])[:300])
