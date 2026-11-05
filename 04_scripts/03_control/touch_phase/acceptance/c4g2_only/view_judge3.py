"""L1 conditions of the C4G2-only noise bundle: false LOC in L1 (reference flags on the L2 rows), errors, controller settings mismatch, L1 G6-7 gate. Stored both vs C4G2-only failing keys. E core 27."""
import json
from pathlib import Path

import psutil

psutil.Process().cpu_affinity([27])
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
O = ACC / "c4g2_only"
r = json.loads((O / "noise/r79_L1L2_judgement.json").read_text(encoding="utf-8"))
print("false_loc_L1 rows", sum(x["rows"]["S-5"].get("false_loc_L1", False) for x in r["runs"]), "false_loc rows", sum(x["rows"]["S-5"].get("false_loc", False) for x in r["runs"]))
d = json.loads((O / "noise/r79_L1L2.json").read_text(encoding="utf-8"))
meta = d["meta"]
print({k: meta.get(k) for k in ("n_jobs", "n_errors", "git_head", "c2_py_sha256")})
pre = meta.get("preset_settings", {})
print("settings mismatch rows", sum(x.get("controller_settings") != pre for x in d["results"]), "L1 failing gate", [(x["key"].split("#")[1][:44], [g for g, ok in x["base"].get("gates", {}).items() if not ok]) for x in d["results"] if x["level"] == "L1" and x["base"].get("pass") is False][:8])
both = json.loads((ACC / "noise/r79_L1L2_judgement.json").read_text(encoding="utf-8"))
f = lambda j: {x["key"].split("#")[1] for x in j["runs"] if not x["pass"]}
a, b = f(r), f(both)
print("fail c4g2", len(a), "both", len(b), "only both", sorted(a ^ b & b), "only c4g2", sorted(a - b), "only in both", sorted(b - a))
