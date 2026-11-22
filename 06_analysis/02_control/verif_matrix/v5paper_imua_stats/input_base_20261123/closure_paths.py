"""For every data path in closure_sites.tsv: tracked file count at the commit, main file count, untracked in main.

Usage: python -I -B -X utf8 closure_paths.py <repo> <commit> <closure_sites.tsv> <out.tsv>
"""
import re
import subprocess
import sys
from pathlib import Path

PART = re.compile(r'"([^"]+)"')


def path_of(text):
    m = re.search(r'(ROOT|PROJECT_ROOT|parents\[\d\]|_SCRIPTS\.parent)\)?\s*/\s*(.*)', text)
    if not m:
        return None
    parts = []
    for tok in re.split(r"\s*/\s*", m.group(2)):
        q = PART.match(tok.strip().lstrip("("))
        if not q:
            break
        parts.append(q.group(1))
    return "/".join(parts) if parts else None


def main():
    repo, commit, tsv, out = sys.argv[1:5]
    seen = {}
    for line in Path(tsv).read_text("utf-8").splitlines()[1:]:
        f, _, _, text = line.split("\t", 3)
        p = path_of(text)
        if p:
            seen.setdefault(p, set()).add(f)
    rows = ["data_path\ttracked_at_commit\tmain_files\tmain_untracked\tdiff_commit_vs_main_head\tused_by"]
    for p in sorted(seen):
        tracked = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "--name-only", commit, "--", p],
                                 capture_output=True, text=True).stdout.split()
        q = Path(repo) / p
        main_files = (1 if q.is_file() else sum(1 for x in q.rglob("*") if x.is_file()) if q.is_dir() else 0)
        untracked = subprocess.run(["git", "-C", repo, "ls-files", "--others", "--exclude-standard", "--", p],
                                   capture_output=True, text=True).stdout.split()
        ignored = subprocess.run(["git", "-C", repo, "ls-files", "--others", "--ignored", "--exclude-standard", "--", p],
                                 capture_output=True, text=True).stdout.split()
        diff = subprocess.run(["git", "-C", repo, "diff", "--name-only", commit, "HEAD", "--", p],
                              capture_output=True, text=True).stdout.split()
        rows.append(f"{p}\t{len(tracked)}\t{main_files}\t{len(untracked) + len(ignored)}\t{len(diff)}\t"
                    + ",".join(sorted(Path(x).name for x in seen[p])))
    Path(out).write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    print(len(rows) - 1)


if __name__ == "__main__":
    main()
