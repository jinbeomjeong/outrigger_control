"""The P7-11 test range of the judge commit T (spec v7 5.2): the test files T changed or added,
every test file that imports a judge tool, and the core patterns (``suite_judgement.json``
``core_patterns`` and ``test_ed7_*``). Prints the worktree-relative paths, one per line.

Usage: python -I -B t_scope_tests.py --repo <judge worktree> --run-commit <C> [--out <list>]
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

CORE_PATTERNS = ("test_jp3_*", "test_ed6_*", "test_run_v5*", "test_lock_start_b*", "test_c2*",
                 "test_extend_start_bound*", "test_ed7_*")
JUDGE_MODULES = re.compile(
    r"^\s*(?:import|from)\s+(jp3_\w*judge\w*|jp3_ed7_rules|jp3_rev7_condition|"
    r"ed7_condition3_adoption|ed7_key_lists|judge_stage1_4368|judge4368_common|jp3_12b_ppred|"
    r"jp3_t8_rules)\b", re.MULTILINE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--run-commit", required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    unit = args.repo / "05_tests" / "unit"
    tests = sorted(path for path in unit.glob("test_*.py"))
    changed = subprocess.run(["git", "-C", str(args.repo), "diff", "--name-only",
                              args.run_commit, "HEAD", "--", "05_tests/unit"],
                             capture_output=True, text=True, check=True).stdout.split()
    picked = set(changed)
    for path in tests:
        relative = path.relative_to(args.repo).as_posix()
        if any(fnmatch.fnmatchcase(path.stem, pattern) for pattern in CORE_PATTERNS):
            picked.add(relative)
        elif JUDGE_MODULES.search(path.read_text(encoding="utf-8", errors="replace")):
            picked.add(relative)
    lines = sorted(path for path in picked if path.endswith(".py"))
    text = "\n".join(lines) + "\n"
    if args.out is not None:
        with args.out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
