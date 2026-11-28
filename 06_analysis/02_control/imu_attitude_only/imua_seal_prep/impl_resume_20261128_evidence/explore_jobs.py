"""Counts of the D-1 jobs (families, eps) and the U-3 / U-6 key files (worktree code)."""

import sys
from collections import Counter
from pathlib import Path

WT = Path(sys.argv[1])
sys.path.insert(0, str(WT / "04_scripts" / "04_hydraulic" / "coupled"))
sys.path.insert(0, str(WT / "03_src"))

import run_v5  # noqa: E402
import v5_rerun  # noqa: E402

jobs = run_v5.batch_jobs("d1")
print("d1 jobs", len(jobs), Counter(j["setting"] for j in jobs))
families = Counter((j["d1"]["key"].split("|")[1], j["setting"]) for j in jobs)
print("families", len({f for f, _ in families}), sorted(families.items())[:30])
print("eps", Counter(j.get("eps", 0.0) for j in jobs))
keys = Counter((j["d1"]["key"], j["setting"]) for j in jobs)
print("keys per setting", Counter(s for _, s in keys), "max lines per key", max(keys.values()))
RV85 = WT / "06_analysis/02_control/s9/rev85"
RV84 = WT / "06_analysis/02_control/s9/rev84"
total = 0
for suite, ids in (("slope", "finB2_harness"), ("h9", "finB2_h9"), ("h6", "finB2_harness"),
                   ("g6", "finB2_p0"), ("g8", "finB2_p0"), ("p3b", "finB2_p0"),
                   ("x426b", "finB2_x426b")):
    n = len(v5_rerun.ids_from(RV85 / f"{ids}.json", "B", (suite,)))
    total += n
    print("u3", suite, n)
for study, ids in (("C", "fin_x426_C"), ("D", "fin_x426_D")):
    n = len(v5_rerun.ids_from(RV85 / f"{ids}.json", "B"))
    total += n
    print("u3", study, n)
print("u3 total keys", total)
wide = v5_rerun.ids_from(RV84 / "fin2_b5_wide_official.json", "B")
main = v5_rerun.ids_from(RV84 / "fin_b5_main.json")
print("u6 wide", len(wide), "main", len(main))
