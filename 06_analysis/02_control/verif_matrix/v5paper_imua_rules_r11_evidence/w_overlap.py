"""Which v5-imua-side changed files (932f1fb1..H_I) fall in the rev26 W tracked-data list."""
import fnmatch
import json
import subprocess
import sys

REPO = r"C:\workspace\outrigger_control"
H_I = sys.argv[2] if len(sys.argv) > 2 else "b0416724"
W_PATTERNS = [
    "02_params/rexome33.yaml", "02_params/scm_soil_sets.json", "02_params/pad_variants.json",
    "06_analysis/00_dynamics/slope_crawler_settle.json",
    "06_analysis/00_dynamics/pad_bekker_p0_soilsets.json",
    "06_analysis/02_control/s8/rev76/*", "06_analysis/02_control/s8/s8_rev52_cs836_scope.json",
    "06_analysis/02_control/s9/rev80/*",
    "06_analysis/02_control/verif_matrix/v5_resume_4368/chrono_rows_manifest.json",
    "06_analysis/02_control/verif_matrix/*.md", "06_analysis/02_control/verif_matrix/*.sha256",
    "06_analysis/03_hydraulic/coupled/v5/v5_criteria*.md",
]
out = subprocess.run(["git", "-C", REPO, "diff", "--name-only", "932f1fb1", H_I],
                     capture_output=True, text=True, encoding="utf-8").stdout.split()
hits = {}
for f in out:
    for p in W_PATTERNS:
        if fnmatch.fnmatchcase(f, p) and ("/" not in f[len(p.rsplit("/", 1)[0]) + 1:]
                                          if p.endswith("*") or "*" in p.rsplit("/", 1)[-1]
                                          else True):
            hits.setdefault(p, []).append(f)
other = [f for f in out if f.startswith((".claude", "CLAUDE.md", "00_docs"))]
res = {"H_I": H_I, "n_changed": len(out), "w_hits": hits, "non_code_top": other}
json.dump(res, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
