"""P7-11 scope check of the judge commit T (spec v7 5.2): T is a descendant of C on one line,
its diff against C changes only ``04_scripts`` / ``05_tests`` paths, ``03_src`` is C's tree, and
no run path module of the list (``05_tests/data/ed7_run_path_modules_<C8>.json``) differs.

Usage (python-dev ``python.exe -I -B``):
  python -I -B t_scope_check.py --repo <judge worktree> --run-commit <C> --judge-commit <T>
      --out <scope.json>
Exit 0 in scope, 1 out of scope, 2 input error (git failure, existing --out).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ALLOWED_PREFIXES = ("04_scripts/", "05_tests/")


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                               timeout=300, check=False)
    if completed.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {completed.stderr.strip()[:300]}")
    return completed.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--run-commit", required=True)
    parser.add_argument("--judge-commit", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        print(json.dumps({"status": "input_error", "reason": "--out exists"}))
        return 2
    run = git(args.repo, "rev-parse", f"{args.run_commit}^{{commit}}").strip()
    judge = git(args.repo, "rev-parse", f"{args.judge_commit}^{{commit}}").strip()
    chain = git(args.repo, "rev-list", "--first-parent", f"{run}..{judge}").split()
    is_descendant = subprocess.run(["git", "-C", str(args.repo), "merge-base", "--is-ancestor",
                                    run, judge], check=False).returncode == 0
    changed = git(args.repo, "diff", "--name-only", run, judge).split("\n")
    changed = [path for path in changed if path]
    outside = [path for path in changed if not path.startswith(ALLOWED_PREFIXES)]
    src_same = (git(args.repo, "rev-parse", f"{run}:03_src").strip()
                == git(args.repo, "rev-parse", f"{judge}:03_src").strip())
    listing = json.loads(git(args.repo, "show", f"{judge}:05_tests/data/"
                                                f"ed7_run_path_modules_{run[:8]}.json"))
    run_path = {entry["path"] for entry in listing["files"]}
    touched = sorted(set(changed) & run_path)
    head = git(args.repo, "rev-parse", "HEAD").strip()
    status = git(args.repo, "status", "--porcelain")
    report = {"rule": "jp3_remedy_spec_v7.md 5.2 / P7-11 (T scope)", "run_commit": run,
              "judge_commit": judge, "commits_after_run_commit": chain,
              "is_descendant": is_descendant, "changed_paths": changed,
              "outside_allowed_prefixes": outside, "src_tree_same": src_same,
              "run_path_files": len(run_path), "run_path_files_changed": touched,
              "checkout": {"head": head, "is_clean": not status.strip()}}
    in_scope = is_descendant and not outside and src_same and not touched
    report["status"] = "in_scope" if in_scope else "out_of_scope"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"status": report["status"], "changed": len(changed),
                      "outside": len(outside), "run_path_changed": len(touched),
                      "out": str(args.out)}))
    return 0 if in_scope else 1


if __name__ == "__main__":
    sys.exit(main())
