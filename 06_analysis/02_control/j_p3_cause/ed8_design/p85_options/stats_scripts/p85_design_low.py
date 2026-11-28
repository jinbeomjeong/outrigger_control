"""Reach probability of the sealed P8-5 rule at design-time replay lower bounds."""
import json
import sys

from scipy import stats

out = {}
for name, p in (("k02A_wilson_low", 0.6226415635484043), ("k02A_exact_low", 0.5872200830116173),
                ("k02A_point", 10 / 11), ("k02a2_point", 0.5)):
    out[name] = {"p": p, "P_reach15_of_23": float(stats.binom.sf(14, 23, p)),
                 "E_same": 23 * p}
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)
print(json.dumps({"status": "ok"}))
