"""Count U-3 key strings that appear in more than one study (pairing collision risk if study is dropped)."""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

V = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5paper_imua_stats")
seen = defaultdict(set)
dup_in_study = 0
per = defaultdict(set)
for r in csv.DictReader((V / "u3_cluster_map.csv").open(encoding="utf-8")):
    if r["key"] in per[r["study"]]:
        dup_in_study += 1
    per[r["study"]].add(r["key"])
    seen[r["key"]].add(r["study"])
multi = {k: sorted(v) for k, v in seen.items() if len(v) > 1}
out = {"distinct_keys": len(seen), "keys_in_multiple_studies": len(multi), "examples": list(multi.items())[:5],
       "duplicate_keys_within_study": dup_in_study}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out))
