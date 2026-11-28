"""Changed lines (git diff -U0 HEAD, plus untracked new files) not covered in a coverage json."""

import json
import re
import subprocess
import sys
from pathlib import Path

WT = Path(sys.argv[1])
COV = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
FILES = sys.argv[3:]

diff = subprocess.run(["git", "-C", str(WT), "diff", "-U0", "HEAD", "--", *FILES],
                      capture_output=True, text=True, encoding="utf-8", check=True).stdout
changed: dict[str, set[int]] = {}
current = None
for line in diff.splitlines():
    if line.startswith("+++ b/"):
        current = line[6:]
        changed.setdefault(current, set())
    match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
    if match and current:
        start, count = int(match.group(1)), int(match.group(2) or 1)
        changed[current].update(range(start, start + count))
for name in FILES:
    if name not in changed:  # new file: every line counts
        path = WT / name
        if path.is_file():
            changed[name] = set(range(1, len(path.read_text(encoding="utf-8").splitlines()) + 1))
files = {key.replace("\\", "/"): value for key, value in COV["files"].items()}
for name, lines in sorted(changed.items()):
    entry = next((v for k, v in files.items() if k.endswith(name)), None)
    if entry is None:
        print(name, "not in the coverage data")
        continue
    executable = set(entry["executed_lines"]) | set(entry["missing_lines"])
    missing = sorted(lines & set(entry["missing_lines"]))
    measured = lines & executable
    print(f"{name}: file {entry['summary']['percent_covered_display']}% "
          f"(branches {entry['summary'].get('covered_branches')}/"
          f"{entry['summary'].get('num_branches')}); changed executable {len(measured)}, "
          f"not covered {len(missing)}: {missing}")
