"""Largest failure count with one-sided 95 % CP upper bound <= 3 %, two paths; replay rejudge summary."""
import json
from pathlib import Path

from scipy.optimize import brentq
from scipy.stats import beta, binom

for n in (855, 501):
    for k in range(0, 40):
        u = float(beta.ppf(0.95, k + 1, n - k))
        v = brentq(lambda p: binom.cdf(k, n, p) - 0.05, 1e-15, 1 - 1e-15, xtol=1e-15)
        if u > 0.03:
            print(n, "first above", k, u, v, "largest ok", k - 1)
            break
d = json.loads(Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono\c4g2_k1_replay_rejudge.json").read_text(encoding="utf-8"))
print(json.dumps(d, ensure_ascii=False)[:1200])
