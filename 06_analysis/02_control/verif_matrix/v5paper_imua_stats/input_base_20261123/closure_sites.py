"""Static import closure of the rev26 judge entry scripts at a commit, and the lines in that closure that
build a path from the module's own location (tool-repository base).

Usage: python -I -B -X utf8 closure_sites.py <repo> <commit> <out.tsv>
Read-only (git show / ls-tree). Over-approximates: every plain imported name is matched to every tracked
.py file of that stem under the searched folders.
"""
import ast
import re
import subprocess
import sys
from collections import deque
from pathlib import PurePosixPath

SEARCH = ("03_src/", "04_scripts/", "06_analysis/02_control/verif_matrix/scripts/",
          "06_analysis/02_control/verif_matrix/v5_resume_4368/path2/",
          "06_analysis/02_control/verif_matrix/v5_resume_4368/path2_v5c/",
          "06_analysis/03_hydraulic/coupled/v5/paper_runs/scripts/")
CO = "04_scripts/04_hydraulic/coupled/"
P2 = "06_analysis/02_control/verif_matrix/v5_resume_4368/path2/"
V5C = "06_analysis/02_control/verif_matrix/v5_resume_4368/path2_v5c/"
ENTRIES = {
    "path1": ["06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py"]
             + [CO + n for n in ("resume_k1_family.py", "t4h_replay.py", "d1_judge_4368.py", "u3_judge_k1.py",
                                 "u3_judge_4368.py", "u9_judge_4368.py", "h8_noise_judge_4368.py",
                                 "h6_judge_4368.py", "judge_stage1_4368.py")]
             + ["04_scripts/03_control/s8/r79_sensor_judge.py", "04_scripts/03_control/s8/r79_L3L4_final.py"],
    "path2": [P2 + n for n in ("p2_4368.py", "p2_x16.py", "p2_d1.py", "p2_u3.py", "p2_v5j.py")]
             + [V5C + n for n in ("p2v5c_common.py", "p2v5c_stage1.py", "p2v5c_grid.py", "p2v5c_noise.py")]
             + ["04_scripts/03_control/s8/r79_sensor_judge.py"],
}
BASE = re.compile(r"__file__|\bROOT\b|\bREPO\b|PROJECT_ROOT|REPO_ROOT|\bHERE\b|parents\[\d\]|REPO_DEFAULT|_HERE\b")
DATA = re.compile(r"06_analysis|07_results|08_test_data|01_cad|02_params|rexome33")
NAMES = re.compile(r"import_module\(\s*[\"']([\w.]+)[\"']|spec_from_file_location\(\s*[\"']([\w.]+)[\"']")


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True).stdout.decode("utf-8", "replace")


def imported(src):
    names = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return names
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
            for a in node.names:
                names.add(a.name)
    for m in NAMES.finditer(src):
        names.add((m.group(1) or m.group(2)).split(".")[0])
    return names


def main():
    repo, commit, out = sys.argv[1:4]
    files = [f for f in git(repo, "ls-tree", "-r", "--name-only", commit).splitlines()
             if f.endswith(".py") and f.startswith(SEARCH) and "/test_" not in f and not f.split("/")[-1].startswith("test_")]
    by_stem = {}
    for f in files:
        by_stem.setdefault(PurePosixPath(f).stem, []).append(f)
    rows = ["path\tclosure_of\tline\ttext"]
    summary = {}
    for name, entries in ENTRIES.items():
        seen, q = set(), deque(entries)
        while q:
            f = q.popleft()
            if f in seen:
                continue
            seen.add(f)
            src = git(repo, "show", f"{commit}:{f}")
            for n in imported(src):
                for g in by_stem.get(n, []):
                    if g not in seen:
                        q.append(g)
        hits = 0
        for f in sorted(seen):
            src = git(repo, "show", f"{commit}:{f}")
            for i, line in enumerate(src.splitlines(), 1):
                s = line.strip()
                if s.startswith("#") or not BASE.search(s) or not DATA.search(s):
                    continue
                rows.append(f"{f}\t{name}\t{i}\t{s[:160]}")
                hits += 1
        summary[name] = {"closure_files": len(seen), "data_base_lines": hits}
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(rows) + "\n")
    print(summary)


if __name__ == "__main__":
    main()
