"""Reconcile the run counts of section 434.8: branched ML episodes vs base and MLJ runs."""
import json
from collections import Counter
from pathlib import Path

from scipy.stats import beta, fisher_exact

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\paper\ml_jc")
h = json.load(open(D / "ml_jc_head.json", encoding="utf-8"))
SETS = ("train", "validation", "test", "OOD-1", "OOD-2", "MLJ")


def kind(run):
    return "MLJ" if run.startswith("MLJ") else ("branch" if "_ep" in run else "base")


tab = Counter()
miss_rows = Counter()
ep_rows = Counter()
names = {}
for s in SETS:
    for it in h[s]:
        run = str(it["meta"]["episode_id"])
        k = kind(run)
        rows = [r for r in it["rows"] if r["scope"] == "scored"]
        m = sum(r["JC_first_decision_s"] is None for r in rows)
        tab[k, "runs"] += 1
        tab[k, "with_episodes"] += bool(rows)
        tab[k, "with_miss"] += m > 0
        ep_rows[k] += len(rows)
        miss_rows[k] += m
        if k != "branch" and rows:
            names[run] = (len(rows), m)
print(dict(sorted(tab.items())))
print("episodes by kind", dict(ep_rows), "misses by kind", dict(miss_rows))
print("non-branch runs with episodes", names)
for lab, a, n in (("all", 41, 318), ("branch only", 40, 316)):
    print(lab, a, n, round(a / n, 4), "CP one-sided upper", round(float(beta.ppf(0.95, a + 1, n - a)), 4))
print("Fisher", fisher_exact([[6, 34], [35, 241]]))
