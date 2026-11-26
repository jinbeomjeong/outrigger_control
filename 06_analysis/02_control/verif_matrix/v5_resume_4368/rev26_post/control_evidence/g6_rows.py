"""Print the stored U-3 g6 rows of the two G-5 keys (VB records[97]/[101] and the V0 rows with the same id):
structure first, then verdict-like fields."""
import json
from pathlib import Path

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\v5_rerun\las_k1")
KEYS = ["g6r|rigid+S1@FL|top|Fs4", "g6r|rigid+S1@FR|top|Fs4"]


def short(v, n=700):
    return json.dumps(v, ensure_ascii=False)[:n]


for setting in ("VB", "V0"):
    data = json.loads((D / f"u3_g6_{setting}.json").read_text("utf-8"))
    recs = data["records"]
    for i, r in enumerate(recs):
        if r.get("id") in KEYS:
            print(f"== {setting} records[{i}] id={r.get('id')} keys={list(r)}")
            for k, v in r.items():
                if isinstance(v, dict):
                    print(f"  {k}: dict keys={list(v)[:40]}")
                else:
                    print(f"  {k}: {short(v, 200)}")
