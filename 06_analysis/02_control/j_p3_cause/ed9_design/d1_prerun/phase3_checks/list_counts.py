"""run_v5 --list dry runs of every R3 batch at a worktree (counts only, nothing run).

argv: <dynamics-dev python> <worktree> <held-out keys> <census keys> <main.jsonl> <out json>
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

python, worktree, heldout, census, main_jsonl, out = sys.argv[1:]
RUN_V5 = Path(worktree) / "04_scripts" / "04_hydraulic" / "coupled" / "run_v5.py"
CASES = [
    ("ed8_heldout_v0", ["--jobs-file", heldout]), ("ed8_heldout_aa2", ["--jobs-file", heldout]),
    ("ed8_heldout_aa3", ["--jobs-file", heldout]),
    ("ed9_heldout_same_shape_off", ["--jobs-file", heldout]), ("ed9_census_v0_off", []),
    ("ed9_heldout_v0", ["--jobs-file", heldout]), ("ed9_heldout_aa2", ["--jobs-file", heldout]),
    ("ed9_heldout_aa3", ["--jobs-file", heldout]),
    ("ed9_heldout_same_shape", ["--jobs-file", heldout]), ("ed9_census_v0", []),
    ("ed9_keys", ["--jobs-file", census]), ("ed9_keys", ["--jobs-file", heldout]),
    ("ed9_t8", ["--p3-hash-source", main_jsonl]), ("ed9_cases", []),
    ("ed9_heldout_aa2", []),  # B-1 check: without --jobs-file it must refuse
]
LINE = re.compile(r"^(\S+): (\d+) runs, (\d+) to do$")


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", worktree, *args], capture_output=True, text=True,
                          timeout=120, check=True).stdout.strip()


results = []
start = {"head": git("rev-parse", "HEAD"), "status": git("status", "--porcelain", "--ignored")}
for batch, extra in CASES:
    done = subprocess.run([python, "-I", "-B", str(RUN_V5), batch, "--list", *extra],
                          capture_output=True, text=True, timeout=600, cwd=worktree,
                          env=os.environ.copy(), check=False)
    match = next((LINE.match(text) for text in done.stdout.splitlines() if LINE.match(text)),
                 None)
    results.append({"batch": batch, "args": [Path(a).name if Path(a).exists() else a
                                             for a in extra],
                    "exit": done.returncode, "runs": int(match.group(2)) if match else None})
end = {"head": git("rev-parse", "HEAD"), "status": git("status", "--porcelain", "--ignored")}
Path(out).write_text(json.dumps({"worktree": worktree, "start": start, "end": end,
                                 "results": results}, indent=1), encoding="utf-8")
for entry in results:
    print(entry["batch"], entry["args"], "exit", entry["exit"], "runs", entry["runs"])
print("head", start["head"], end["head"], "status lines", len(start["status"].splitlines()),
      len(end["status"].splitlines()))
