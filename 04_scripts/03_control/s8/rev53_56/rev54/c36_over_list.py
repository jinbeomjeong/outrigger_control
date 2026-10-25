"""Print the over-limit runs of the C-S8-36 twist-work record row in a rev52 judge json."""
import json
import sys

d = json.loads(open(sys.argv[1], encoding="utf-8").read())
aff = set(json.loads(open(sys.argv[2], encoding="utf-8").read())["affected"])
for r in d["rows"]:
    if str(r.get("item", r.get("name", ""))).startswith("C-S8-36 twist") or "twist-mode actuator work" in json.dumps(r)[:300]:
        over = r.get("over") or {}
        print(len(over), r.get("value"))
        for c, v in sorted(over.items(), key=lambda kv: -kv[1]):
            print(c, round(v, 1), "AFF" if c in aff else "-")
