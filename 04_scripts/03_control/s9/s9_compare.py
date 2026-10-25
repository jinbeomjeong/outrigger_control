"""Compare base (project C2) and loc (soil rule) runs of an s9 result file: command hashes and judged metrics.

python s9_compare.py <json> [loc_prefix]  -> prints the non-identical cases and a summary; writes <json>_cmp.json
"""
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
loc = sys.argv[2] if len(sys.argv) > 2 else "loc"
d = json.loads(p.read_text(encoding="utf-8"))
runs = {r["id"]: r for r in d["runs"]}
if len(sys.argv) > 3:  # loc runs from a second file (base runs of the first file kept)
    d2 = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
    runs = {k: v for k, v in runs.items() if k.startswith("base|")}
    runs.update({r["id"]: r for r in d2["runs"]})
    p = Path(sys.argv[3])
KEYS = ("t_done_s", "t_ready_s", "final_phase", "crawler_N_at_ready", "min_margin_after_off_kN", "att_end_deg",
        "max_motor_stroke_mm", "n_reapproach", "n_probe_rounds", "n_relevel", "n_warn")
out = {"identical": [], "different": []}
for k, r in runs.items():
    if not k.startswith("base|"):
        continue
    k2 = loc + k[4:]
    if k2 not in runs:
        continue
    r2 = runs[k2]
    if "error" in r or "error" in r2:
        out["different"].append({"id": k, "error": r.get("error") or r2.get("error")})
        continue
    if r["commands_sha256"] == r2["commands_sha256"]:
        out["identical"].append(k)
        continue
    diff = {}
    for kk in KEYS:
        a, b = r.get(kk), r2.get(kk)
        if a != b:
            diff[kk] = (a, b)
    meta = r2.get("soil_rule_meta", {})
    out["different"].append({"id": k, "diff": diff, "loc_log": meta.get("log"), "bias_mm": meta.get("bias_mm")})
print(len(out["identical"]), "identical,", len(out["different"]), "different")
for x in out["different"]:
    print(x["id"], x.get("loc_log"), {k: v for k, v in x.get("diff", {}).items()})
# LOC timing on the loc runs: clearance estimate at the confirmation (rigid margin to the 20 mm release)
Path(str(p).replace(".json", "_cmp.json")).write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
