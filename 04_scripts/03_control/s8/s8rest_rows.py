"""Dump verify_S8C.json rows filtered by item / case substrings (read only).

Usage: python -I s8rest_rows.py <verify_json> <item_substr|-> <case_substr|-> [maxlen]
  "-" means no filter. With item "LIST" prints the distinct item names and counts.
"""
import json
import sys
from collections import Counter

v = json.load(open(sys.argv[1], encoding="utf-8"))
rows = v["rows"]
item_s, case_s = sys.argv[2], sys.argv[3]
maxlen = int(sys.argv[4]) if len(sys.argv) > 4 else 700
if item_s == "LIST":
    c = Counter((r["item"], r.get("kind")) for r in rows)
    for (item, kind), n in sorted(c.items()):
        print(f"{n:4d} {kind:9s} {item}")
    sys.exit()
for r in rows:
    if item_s != "-" and item_s not in r["item"]:
        continue
    if case_s != "-" and case_s not in str(r["case"]):
        continue
    s = json.dumps(r, ensure_ascii=False)
    print(s[:maxlen])
