"""EOL risk of reading tracked files from a fresh T26 worktree (core.autocrlf=true) instead of the main checkout.

1. For every file tracked at the commit: the bytes a fresh autocrlf=true checkout would write (blob for -text,
   binary or i/crlf; LF->CRLF for i/lf text) vs the main working-copy bytes. Files that differ = EOL-changed set.
2. In the original judge outputs (top-level *.json of the three folders), every 64-hex string leaf that is
   compared under excl_fields_r3 (not under an S / F / I entry) is looked up in the sha index of the EOL-changed
   files (main raw sha). Only counts and file paths are printed, never output values.

Usage: python -I -B -X utf8 eol_risk.py <main repo> <commit> <judge_932f1fb dir> <excl_fields_r3.py dir> <out.json>
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
    spec = importlib.util.spec_from_file_location("excl_r3", Path(rules_dir) / "excl_fields_r3.py")
    r3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r3)

    eol = git(repo, "ls-files", "--eol").decode("utf-8", "replace").splitlines()
    tracked_head = set(git(repo, "ls-tree", "-r", "--name-only", commit).decode("utf-8", "replace").splitlines())
    changed = {}
    n_checked = 0
    since = set(git(repo, "diff", "--name-only", commit, "HEAD").decode("utf-8", "replace").splitlines())
    for line in eol:
        meta, _, path = line.partition("\t")
        if path not in tracked_head:
            continue
        f = Path(repo) / path
        if not f.is_file():
            continue
        parts = meta.split()
        i_eol, w_eol = parts[0], parts[1]
        attr = parts[2] if len(parts) > 2 else "attr/"
        # fresh checkout with core.autocrlf=true: i/lf text without -text -> w/crlf, else index EOL kept
        if "-text" in attr or i_eol in ("i/-text", "i/none", "i/crlf", "i/mixed"):
            predicted = i_eol.replace("i/", "w/")
        else:
            predicted = "w/crlf"
        n_checked += 1
        if predicted != w_eol or path in since:
            # bytes of the commit blob (what the original run read at M4) in both EOL forms, and the main copy
            blob = git(repo, "show", f"{commit}:{path}")
            data = f.read_bytes()
            lf = blob.replace(b"\r\n", b"\n")
            for kind, variant in (("blob_lf", lf), ("blob_crlf", lf.replace(b"\n", b"\r\n")), ("main_raw", data)):
                changed.setdefault(hashlib.sha256(variant).hexdigest(), f"{path} [{kind}]")

    rules = r3.Rules("932f1fb1724f074e4ee93a9c02193c7c840d13c4", "judge_932f1fb", {}, repo, [])
    hits = []
    n_hex = 0
    for d in r3.DIRS:
        for jf in sorted((Path(judge_dir) / d).glob("*.json")):
            key = (d, jf.name)
            if key in r3.SKIP_D_FILES:
                continue
            data = json.load(open(jf, encoding="utf-8"))
            acc = set()
            r3.walk(data, [], acc, rules, d, jf.name, r3.SKIP_D_SUBTREES.get(key, ()))
            excl = [p for p, c in acc if c in ("S", "F", "I")]

            def visit(o, path):
                nonlocal n_hex
                if isinstance(o, dict):
                    collapse = len(o) > r3.WIDE
                    for k, v in o.items():
                        visit(v, path + ("{*}" if collapse else str(k),))
                elif isinstance(o, list):
                    for v in o:
                        visit(v, path + ("[]",))
                elif isinstance(o, str) and HEX64.match(o):
                    if any(tuple(path[:len(s)]) == tuple(s) for s in r3.SKIP_D_SUBTREES.get(key, ())):
                        return
                    if any(path[:len(e)] == e for e in excl):
                        return
                    n_hex += 1
                    if o in changed:
                        hits.append({"file": f"{d}/{jf.name}", "path": list(path), "tracked_file": changed[o]})

            visit(data, ())
    res = {"tracked_files_checked": n_checked,
           "eol_changed_files": len({v.rsplit(" [", 1)[0] for v in changed.values()}),
           "compared_hex64_leaves": n_hex, "hits": hits}
    Path(out).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in res.items()}))


if __name__ == "__main__":
    main()
