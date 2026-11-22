"""Appendix A files of the 436.8 rules: tracked at 932f1fb? main working copy raw/LF sha vs the table.

Usage: python -I -B appx_a_check.py <main checkout> <out.tsv>
Prints counts only; the TSV lists path, tracked, main_exists, raw_ok, lf_ok, main_has_crlf, blob_ok, attr.
"""
import ast
import hashlib
import re
import subprocess
import sys
from pathlib import Path

COMMIT = "932f1fb1724f074e4ee93a9c02193c7c840d13c4"
RULES = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules.md"
P2 = "06_analysis/02_control/verif_matrix/v5_resume_4368/path2/p2_4368.py"
ROW = re.compile(r"^\| `([^`]+)`[^|]*\| `([0-9a-f]{64})` \|")


def git(repo, *a, binary=False):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True)
    return r.returncode, (r.stdout if binary else r.stdout.decode("utf-8", "replace"))


def appendix_rows(text):
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("## 부록 A."))
    out, folder = [], ""
    for l in lines[start + 1:]:
        if l.startswith("## "):
            break
        m = ROW.match(l)
        if not m:
            continue
        p, s = m.groups()
        if p.startswith("…/"):
            p = f"{folder}/{p[2:]}"
        folder = p.rsplit("/", 1)[0]
        out.append((p, s))
    return out


def p2_appendix(src):
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "APPENDIX_A" for t in node.targets):
            try:
                return dict(ast.literal_eval(node.value))
            except ValueError:
                return None
    return None


def main():
    repo, out = sys.argv[1], Path(sys.argv[2])
    _, rules = git(repo, "show", f"{COMMIT}:{RULES}")
    rows = appendix_rows(rules)
    _, p2src = git(repo, "show", f"{COMMIT}:{P2}")
    p2 = p2_appendix(p2src)
    lines = ["path\ttracked\tmain_exists\traw_ok\tlf_ok\tmain_crlf\tblob_ok\ttext_attr\tin_p2"]
    counts = {"rows": len(rows), "untracked": 0, "missing_main": 0, "raw_ok": 0, "lf_only": 0, "main_crlf": 0,
              "p2_keys": None if p2 is None else len(p2), "p2_same_set": None}
    for p, want in rows:
        rc, blob = git(repo, "show", f"{COMMIT}:{p}", binary=True)
        tracked = rc == 0
        f = Path(repo) / p
        exists = f.is_file()
        data = f.read_bytes() if exists else b""
        raw_ok = exists and hashlib.sha256(data).hexdigest() == want
        lf_ok = exists and hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest() == want
        crlf = b"\r\n" in data
        blob_ok = tracked and hashlib.sha256(blob).hexdigest() == want
        _, attr = git(repo, "check-attr", "text", "--", p)
        attr = attr.strip().rsplit(":", 1)[-1].strip()
        counts["untracked"] += not tracked
        counts["missing_main"] += not exists
        counts["raw_ok"] += raw_ok
        counts["lf_only"] += (lf_ok and not raw_ok)
        counts["main_crlf"] += crlf
        lines.append(f"{p}\t{tracked}\t{exists}\t{raw_ok}\t{lf_ok}\t{crlf}\t{blob_ok}\t{attr}\t{p2 is not None and p in p2}")
    if p2 is not None:
        counts["p2_same_set"] = set(p2) == {p for p, _ in rows}
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(counts)


if __name__ == "__main__":
    main()
