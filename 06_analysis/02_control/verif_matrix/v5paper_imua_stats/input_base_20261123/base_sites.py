"""List lines that use the tool-repository base (repo / ROOT / root) with their enclosing function.

Usage: python -I -B base_sites.py <out.tsv> <src dir> [<src dir> ...]
Only non-test .py files are scanned. Read-only on the sources.
"""
import ast
import re
import sys
from pathlib import Path

PAT = re.compile(r"\b(repo|ROOT|REPO_DEFAULT|data_root)\b")


def enclosing(tree):
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            spans.append((node.lineno, node.end_lineno, node.name))
    return spans


def main():
    out = Path(sys.argv[1])
    rows = []
    for d in sys.argv[2:]:
        for f in sorted(Path(d).glob("*.py")):
            if "test_" in f.name:
                continue
            text = f.read_text("utf-8")
            spans = enclosing(ast.parse(text))
            for i, line in enumerate(text.splitlines(), 1):
                if not PAT.search(line) or line.lstrip().startswith("#"):
                    continue
                inner = [s for s in spans if s[0] <= i <= s[1]]
                name = min(inner, key=lambda s: s[1] - s[0])[2] if inner else "<module>"
                rows.append(f"{f.name.split('__')[-1]}\t{i}\t{name}\t{line.strip()[:150]}")
    out.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    print(len(rows))


if __name__ == "__main__":
    main()
