"""Start check of the sweep: arm B delta 0 against stored soil_A rows (command hash, key values) and the hold state in the harness base."""
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
new = {r["key"]: r for r in json.loads((ACC / "soil/soil_A.json").read_text(encoding="utf-8"))["results"]}
KEY = {"FLFs0": "A|G1|FL|Fs0|two", "FLFs8": "A|G1|FL|Fs8|two", "RRFs0": "A|G1|RR|Fs0|two"}
for line in path.read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    if "error" in r:
        print(r)
        continue
    st = new[KEY[r["row"]]]
    run = [x for x in st["runs"] if x["event"] == "RE1bF" and x["timing"] == "level"][0]
    print(r["row"], r["delta"], "t_ev", r["t_ev"], run["t_ev_s"], "hash same", r["commands_sha256"] == run["commands_sha256"], "base hash same", r["base"]["commands_sha256"] == st["base"]["commands_sha256"],
          "union", r["pair_union_s"], run["pair_union_s"], "ready", r["t_ready_back_s"], run["t_ready_back_s"], "hold", r["base"]["hold"], "wall", r["wall_s"])
