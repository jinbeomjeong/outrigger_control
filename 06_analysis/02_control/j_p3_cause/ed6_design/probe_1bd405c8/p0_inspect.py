"""Print the share / groups / checks blocks of the edition 6 probe share file (read only)."""
import json
from pathlib import Path

P = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\1bd405c8\ed6_probe_a1")
d = json.loads((P / "ed6_probe_share.json").read_text(encoding="utf-8"))
for k in ("share", "groups", "checks", "lsb_parameters"):
    s = json.dumps(d[k], ensure_ascii=False, indent=1)
    print("=====", k, len(s))
    print(s[:5000])
