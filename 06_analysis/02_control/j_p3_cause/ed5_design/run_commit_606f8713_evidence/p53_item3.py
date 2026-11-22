"""Erratum 5 5-1 item 3: test functions newly added to existing test files in BASE..HEAD.

Two readings, printed side by side: '+def test_' / '-def test_' lines of
git diff --diff-filter=M -U0 (the ae9d0b2d extraction), and module-level test function
names present at HEAD but not at BASE (ast).
"""

import ast
import re
import subprocess
import sys

REPO = r"C:\workspace\outrigger_control"
DEF_LINE = re.compile(r"^([+-])\s*(?:async\s+)?def (test_\w+)")


def git(*arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", REPO, *arguments], capture_output=True, check=True
    ).stdout.decode("utf-8")


def test_names(revision: str, path: str) -> set[str]:
    tree = ast.parse(git("show", f"{revision}:{path}"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


def main() -> None:
    base, head = sys.argv[1], sys.argv[2]
    modified = git(
        "diff", "--name-only", "--diff-filter=M", base, head, "--", "05_tests/unit/test_*.py"
    ).split()
    for path in modified:
        added, removed = [], []
        for line in git("diff", "-U0", base, head, "--", path).splitlines():
            match = DEF_LINE.match(line)
            if match and not line.startswith(("+++", "---")):
                (added if match.group(1) == "+" else removed).append(match.group(2))
        new_by_ast = sorted(test_names(head, path) - test_names(base, path))
        gone_by_ast = sorted(test_names(base, path) - test_names(head, path))
        name = path.rsplit("/", 1)[-1]
        print(f"{name}: diff +{sorted(set(added) - set(removed))} -{sorted(set(removed) - set(added))}")
        print(f"{name}: ast new {new_by_ast} gone {gone_by_ast}")


if __name__ == "__main__":
    main()
