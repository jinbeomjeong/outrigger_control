"""Show run/settle structure of rev80 'runs' files and the settle_new block of the compare file (read-only)."""
import json
from pathlib import Path

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev80")
for n in ("base_harness.json", "soil_harness.json", "sensor_harness.json", "beta_harness.json"):
    doc = json.loads((D / n).read_text(encoding="utf-8"))
    runs = doc["runs"]
    seq = list(runs.values()) if isinstance(runs, dict) else runs
    print("==", n, "n_cases", doc["meta"].get("n_cases"), "runs", len(seq), "set", doc["meta"].get("set"))
    r = seq[0]
    print("   keys:", list(r)[:40])
    for k in ("settle", "settle_check"):
        if k in r:
            print("   ", k, json.dumps(r[k])[:1200])
    print("   id:", r.get("id"), "case:", json.dumps(r.get("case"))[:250])
doc = json.loads((D / "s9_uniform_compare.json").read_text(encoding="utf-8"))
c = doc["cases"][0]
print("== compare settle_new", json.dumps(c["settle_new"])[:1200])
print("   summary", json.dumps(doc["summary"])[:1500])
