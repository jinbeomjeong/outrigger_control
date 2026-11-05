"""Rest of the noise verdict, L1 conditions, L2 failing rows with their kind, provenance of the steps. E core 27."""
import json
from pathlib import Path

import psutil

psutil.Process().cpu_affinity([27])
O = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance\c4g2_only")
j = json.loads((O / "judgement.json").read_text(encoding="utf-8"))
n = j["noise_L2"]
print({k: (v if not isinstance(v, (list, dict)) else (len(v) if isinstance(v, list) else list(v)[:12])) for k, v in n.items()})
for k in n:
    if k not in ("pass_to_fail", "fail_to_pass") and isinstance(n[k], (list, dict)):
        print(k, json.dumps(n[k], default=str)[:900])
r = json.loads((O / "noise/r79_L1L2_judgement.json").read_text(encoding="utf-8"))
print("judgement keys", list(r))
rows = r.get("runs") or r.get("rows") or []
print("n runs", len(rows), "first", {k: rows[0][k] for k in list(rows[0])[:12]} if rows else None)
fails = [x for x in rows if x.get("level") == "L2" and not x.get("pass", x.get("passed", True)) and not any(s in x.get("key", "") for s in ("S1@FL", "S1@FR"))]
print("L2 fail rows", [(x["key"].split("#")[1][:48], x.get("failed") or x.get("failed_rows")) for x in fails][:14])
print("table L1", [{k: t.get(k) for k in ("level", "group", "runs")} | {"any": t.get("any", {}).get("fail")} for t in r.get("table", [])][:8])
for k in ("unmatched", "errors", "false_loc", "settings_mismatch", "false_loc_L1", "controller_settings_mismatch"):
    if k in r:
        print(k, json.dumps(r[k], default=str)[:300])
keys = [k for k in r if "loc" in k.lower() or "setting" in k.lower() or "L1" in k]
print("loc/setting keys", {k: json.dumps(r[k], default=str)[:300] for k in keys})
p = json.loads((O / "provenance/grid_r67_main.json").read_text(encoding="utf-8"))
print("prov grid", {k: p.get(k) for k in ("combo", "touch_twist_hold", "retrigger_samples", "git_head")})
print("L3 flips", json.dumps(j["noise_L3_record"]["L3"].get("flips_vs_pre_R6"), default=str)[:1200])
