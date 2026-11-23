"""Review checks for erratum 8 draft: 30 s rounding boundary and (1) floor bound variants."""
import json
import math
from decimal import Decimal
from pathlib import Path

from scipy.stats import beta

out = {}
cases = {"30.0000005": 30.0000005, "130.0000005-100.0": 130.0000005 - 100.0,
         "130.000001-100.0": 130.000001 - 100.0, "130.0000004-100.0": 130.0000004 - 100.0,
         "130.0-100.0": 130.0 - 100.0, "30.000001": 30.000001}
out["rounding"] = {k: {"exact": str(Decimal(v)), "round6": round(v, 6), "counts": round(v, 6) > 30}
                   for k, v in cases.items()}
n_line, n_case, n_pairs = 494, 167, 334
rates = {"line_95up": 1 - 0.05 ** (1 / n_line), "case_95up": 1 - 0.05 ** (1 / n_case),
         "line_50up": 1 - 0.5 ** (1 / n_line),
         "jeffreys_mean": 0.5 / (n_line + 1), "jeffreys_95up": float(beta.ppf(0.95, 0.5, n_line + 0.5))}
out["rates"] = rates
out["P1"] = {r: {str(c): 1 - math.exp(-p * c * n_pairs) for c in (0.127, 0.189, 1.0)}
             for r, p in rates.items()}
p23 = {"F0": 0.0, "F2u": 0.0035, "F3": 0.0206, "F3h": 0.5191}
out["joint_bounds_line95"] = {
    s: {"indep": 1 - (1 - out["P1"]["line_95up"][str(c)]) * (1 - v),
        "max": max(out["P1"]["line_95up"][str(c)], v),
        "sum": min(1.0, out["P1"]["line_95up"][str(c)] + v)}
    for s, v, c in (("F0", p23["F0"], 0.127), ("F2u", p23["F2u"], 0.189), ("F3", p23["F3"], 1.0),
                    ("F3h", p23["F3h"], 1.0))}
# b4 MDE80 by linear interpolation (e8_b4_ext.json, k = 9)
b4 = json.loads(Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause"
                     r"\ed5_design\stats_e8\e8_b4_ext.json").read_text(encoding="utf-8"))
mde = {}
for s, v in b4["scenarios"].items():
    pts = [(d, v[f"delta_{d}"]["k9"]) for d in (0.0, 0.01, 0.02, 0.03, 0.04)]
    for (d0, p0), (d1, p1) in zip(pts, pts[1:], strict=False):
        if p0 < 0.8 <= p1:
            mde[s] = 100 * (d0 + (0.8 - p0) * (d1 - d0) / (p1 - p0))
            break
out["b4_mde80_pct"] = mde
Path(__file__).with_suffix(".json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("ok")
