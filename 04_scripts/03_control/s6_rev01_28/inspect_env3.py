"""Show maps and rules entries of target_envelope.json."""
import json
import sys

d = json.load(open(sys.argv[1]))
m = d["maps"]["top|flat"]
print("maps keys", list(m.keys()) if isinstance(m, dict) else type(m))
if isinstance(m, dict):
    for k, v in m.items():
        if isinstance(v, list):
            print(k, len(v), (len(v[0]) if v and isinstance(v[0], list) else ""), str(v[0])[:200])
        else:
            print(k, str(v)[:200])
r = d["rules"]
print(json.dumps(r["note"])[:600])
print(json.dumps(r["R_rec_rel44_32_abs44_32"])[:3000])
print(json.dumps(d["intersection"])[:1500])
