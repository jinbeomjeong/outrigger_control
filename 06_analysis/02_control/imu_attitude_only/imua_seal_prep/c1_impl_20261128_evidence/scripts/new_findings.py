"""Ruff findings on lines added by the working-tree diff (vs HEAD) of the given files.

Usage: python new_findings.py <repo> <ruff.exe> <file> [...]
"""
import re
import subprocess
import sys

repo, ruff, files = sys.argv[1], sys.argv[2], sys.argv[3:]
total = 0
for f in files:
    diff = subprocess.run(["git", "-C", repo, "diff", "-U0", "HEAD", "--", f], capture_output=True,
                          text=True, encoding="utf-8", check=True).stdout
    added = set()
    for m in re.finditer(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", diff, re.M):
        start, n = int(m.group(1)), int(m.group(2) or 1)
        added.update(range(start, start + n))
    out = subprocess.run([ruff, "check", "--no-cache", "--output-format", "concise", f], cwd=repo,
                         capture_output=True, text=True, encoding="utf-8").stdout
    for line in out.splitlines():
        m = re.match(r"^.+?:(\d+):\d+: (\S+) (.*)$", line)
        if m and int(m.group(1)) in added:
            total += 1
            print(f, m.group(1), m.group(2), m.group(3))
print("new findings", total)
