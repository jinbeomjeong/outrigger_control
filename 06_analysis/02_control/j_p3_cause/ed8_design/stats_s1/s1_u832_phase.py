"""U832 phase-lock check: bottom-front RE1bF-ready lines by offset, editions 6 and 7.

Line identities come from the stored pool csv (used_ed6 flags) and the sealed G1 key file.
Failure labels are the published ones only (ed6 judgement / ed7 judgement 3.3):
  ed6 U832 fails: bottom-FL-Fs2 o0.0, bottom-FR-Fs2 o0.0, bottom-FR-Fs4 o0.0
  ed7 U832 fails: bottom-FR-Fs0 o0.0, bottom-FL-Fs4 o0.0
"""

import csv
import json
import sys
from pathlib import Path

from scipy import stats

POOL_CSV = Path(sys.argv[1])
G1_JSON = Path(sys.argv[2])
OUT = Path(sys.argv[3])

FAIL6 = {("FL", 2.0, 0.0), ("FR", 2.0, 0.0), ("FR", 4.0, 0.0)}
FAIL7 = {("FR", 0.0, 0.0), ("FL", 4.0, 0.0)}

ed6 = []
for r in csv.DictReader(POOL_CSV.open(encoding="utf-8")):
    if (r["level"] == "bottom" and r["leg"] in ("FL", "FR") and r["event"] == "RE1bF"
            and r["timing"] == "ready" and r["used_ed6"] == "True"):
        ed6.append((r["leg"], float(r["fs_kN"]), float(r["offset_s"]), r["v0_pass"]))
ed7 = []
for ln in json.loads(G1_JSON.read_text(encoding="utf-8"))["lines"]:
    t = ln["twin"] if "twin" in ln else ln["job"]["twin"]
    if (t["level"] == "bottom" and t["leg"] in ("FL", "FR") and t["event"] == "RE1bF"
            and t["timing"] == "ready"):
        ed7.append((t["leg"], float(t["fs_kN"]), float(ln["job"]["offset_s"]), "True"))


def table(lines, fails):
    a = sum(1 for x in lines if x[2] == 0.0 and x[:3] in fails)
    b = sum(1 for x in lines if x[2] == 0.0) - a
    c = sum(1 for x in lines if x[2] != 0.0 and x[:3] in fails)
    d = sum(1 for x in lines if x[2] != 0.0) - c
    return [[a, b], [c, d]]


t6 = table(ed6, FAIL6)
t7 = table(ed7, FAIL7)
tt = [[t6[0][0] + t7[0][0], t6[0][1] + t7[0][1]], [t6[1][0] + t7[1][0], t6[1][1] + t7[1][1]]]
res = {
    "ed6_lines": sorted(ed6), "ed7_lines": sorted(ed7),
    "table_rows_o0_vs_other_cols_fail_pass": {"ed6": t6, "ed7": t7, "pooled": tt},
    "fisher_one_sided_pooled_p": float(stats.fisher_exact(tt, alternative="greater")[1]),
    "note": "lines in different editions differ in controller (VBL vs VBM); pooled test is"
            " descriptive, post-result",
}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps({"status": "ok", "pooled": tt, "p": res["fisher_one_sided_pooled_p"]}))
