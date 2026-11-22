"""Compared 64-hex leaves of the original 436.8 judge outputs that equal the sha256 of a 03_src / 02_params file.

For every file under 03_src and 02_params tracked at the commit, the sha256 of the commit blob in LF and CRLF form
is indexed. Every 64-hex string leaf that excl_fields_r4 does not exclude (not under S / F / I) is looked up.
Only file paths and JSON paths are printed, never output values.

Usage: python -I -B -X utf8 src_sha_leaves.py <repo> <commit> <judge_932f1fb dir> <excl_fields_r4.py dir> <out.json>
"""
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True).stdout


def main():
    repo, commit, judge_dir, rules_dir, out = sys.argv[1:6]
    spec = importlib.util.spec_from_file_location("excl_r4", Path(rules_dir) / "excl_fields_r4.py")
    r4 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r4)
    files = git(repo, "ls-tree", "-r", "--name-only", commit, "--", "03_src", "02_params").decode().splitlines()
    index = {}
    for f in files:
        lf = git(repo, "show", f"{commit}:{f}").replace(b"\r\n", b"\n")
        index[hashlib.sha256(lf).hexdigest()] = f"{f} [lf]"
        index.setdefault(hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest(), f"{f} [crlf]")
    rules = r4.Rules(commit, "judge_932f1fb", {}, repo, [])
    hits, n_hex = [], 0
    for d in r4.DIRS:
        for jf in sorted((Path(judge_dir) / d).glob("*.json")):
            key = (d, jf.name)
            data = json.load(open(jf, encoding="utf-8"))
            acc = set()
            r4.walk(data, [], acc, rules, d, jf.name, ())
            excl = [p for p, c in acc if c in ("S", "F", "I")]

            def visit(o, path):
                nonlocal n_hex
                if isinstance(o, dict):
                    collapse = len(o) > r4.WIDE
                    for k, v in o.items():
                        visit(v, path + ("{*}" if collapse else str(k),))
                elif isinstance(o, list):
                    for v in o:
                        visit(v, path + ("[]",))
                elif isinstance(o, str) and HEX64.match(o) and not any(path[:len(e)] == e for e in excl):
                    n_hex += 1
                    if o in index:
                        hits.append({"file": f"{d}/{jf.name}", "path": list(path), "src_file": index[o],
                                     "d_scope": key not in r4.SKIP_D_FILES})

            visit(data, ())
    res = {"src_params_files": len(files), "compared_hex64_leaves": n_hex, "hits": hits}
    Path(out).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"src_params_files": len(files), "compared_hex64_leaves": n_hex, "hits": len(hits)}))


if __name__ == "__main__":
    main()
