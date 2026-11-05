"""controller_settings difference by level, against the preset and the both run; L1 base gate failures both vs C4G2-only vs stored off judgement. E core 27."""
import json
from pathlib import Path

import psutil

psutil.Process().cpu_affinity([27])
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
O = ACC / "c4g2_only"
d = json.loads((O / "noise/r79_L1L2.json").read_text(encoding="utf-8"))
b = json.loads((ACC / "noise/r79_L1L2.json").read_text(encoding="utf-8"))
pre = d["meta"]["preset_settings"]
print("meta preset same as both meta", pre == b["meta"]["preset_settings"])
for lv in ("L1", "L2"):
    rows = [x for x in d["results"] if x["level"] == lv]
    cs = rows[0].get("controller_settings")
    print(lv, "n", len(rows), "has settings", sum("controller_settings" in x for x in rows), "diff keys vs preset", [k for k in set(pre) | set(cs or {}) if (cs or {}).get(k) != pre.get(k)][:10], "distinct", len({json.dumps(x.get("controller_settings"), sort_keys=True) for x in rows}))
rows_b = {x["key"]: x for x in b["results"]}
print("settings differ from both row", sum(x.get("controller_settings") != rows_b[x["key"]].get("controller_settings") for x in d["results"]))
g = lambda doc: {x["key"].split("#")[1]: [k for k, ok in x["base"].get("gates", {}).items() if not ok] for x in doc["results"] if x["level"] == "L1" and x["base"].get("pass") is False}
a, c = g(d), g(b)
print("L1 base fail c4g2", len(a), "both", len(c), "only c4g2", {k: a[k] for k in a if k not in c}, "only both", {k: c[k] for k in c if k not in a}, "gate diff", {k: (a[k], c[k]) for k in a if k in c and a[k] != c[k]})
print("L1 G6-3 fails c4g2", [k for k, v in a.items() if "G6-3_Fmin" in v], "both", [k for k, v in c.items() if "G6-3_Fmin" in v])
