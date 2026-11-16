"""R4 allow list (rev16:323-325 (다)/(라)) files not in the 28-row blob table: compare blob ids at R3f, R4, M4.

Usage: python -I _unchanged_blobs.py <repo> <blob_table.tsv> <out.json>
"""
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

repo, tsv, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
R3F, R4, M4 = "8a0c843", "1ab93f0", "932f1fb"
C = "04_scripts/04_hydraulic/coupled/"
P2 = "06_analysis/02_control/verif_matrix/v5_resume_4368/path2/"
P5 = "06_analysis/02_control/verif_matrix/v5_resume_4368/path2_v5c/"
patterns = [C + n for n in ("judge_stage1_4368.py", "judge4368_common.py", "u3_judge_4368.py", "h8_noise_judge_4368.py",
                            "h6_judge_4368.py", "README_judges_4368.md")]
patterns += ["06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py", "05_tests/unit/test_judges_4368.py",
             "05_tests/unit/test_judges_4368_h6_h8.py", "05_tests/unit/test_resume4368*.py"]
patterns += [P2 + n for n in ("README.md", "p2_4368.py", "p2_u3.py", "p2_v5j.py", "test_p2_4368.py", "test_p2_u3.py",
                              "test_p2_v5j.py", "p2_x16.py", "test_p2_x16.py")]
patterns += [P5 + n for n in ("README.md", "p2v5c_common.py", "p2v5c_grid.py", "p2v5c_noise.py", "p2v5c_stage1.py",
                              "test_p2v5c.py")]


def tree(commit):
    o = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", commit], capture_output=True, text=True, check=True)
    return {l.split("\t", 1)[1]: l.split()[2] for l in o.stdout.splitlines()}


t3, t4, tm = tree(R3F), tree(R4), tree(M4)
listed = sorted({f for f in t4 if any(fnmatch.fnmatch(f, p) for p in patterns)})
changed = {l.split("\t")[0] for l in tsv.read_text("utf-8").splitlines()[1:] if l.strip()}
rows = []
for f in listed:
    if f in changed:
        continue
    rows.append({"file": f, "R3f": t3.get(f), "R4": t4.get(f), "M4": tm.get(f),
                 "same": t3.get(f) == t4.get(f) == tm.get(f)})
missing_from_r4 = [p for p in patterns if not any(fnmatch.fnmatch(f, p) for f in t4)]
res = {"listed_in_allow_list": len(listed), "in_blob_table": len(changed & set(listed)),
       "unchanged_checked": len(rows), "unchanged_same": sum(r["same"] for r in rows),
       "patterns_without_file": missing_from_r4, "rows": rows}
out.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k != "rows"}))
for r in rows:
    print(r["same"], r["file"])
