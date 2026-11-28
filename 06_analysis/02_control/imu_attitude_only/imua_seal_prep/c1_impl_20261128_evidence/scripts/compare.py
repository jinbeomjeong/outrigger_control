"""Bit comparison of two case folders (before / after the C-1 edit, same argv, no A-type arguments).

Every ``*.npz`` (recursive): same file set, same array names, dtype, shape and values (``array_equal`` with
``equal_nan``). Every ``*.json``: recursive comparison; differing leaves are listed and split into volatile ones
(wall clock, placement, timestamps, paths, PIDs, file mtimes / git state at start) and the rest. Exit 0 = all arrays
equal and no non-volatile JSON difference.

Usage: python compare.py <before dir> <after dir> [--out report.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

VOLATILE = re.compile(r"(wall|us_per_step|placement|build_s|taken_utc|mtime|git_at_start|_utc$|pid|affinity|"
                      r"time_stamp|stamp|perf|elapsed|hostname|cpu|^.*\.path$|out_root|argv|files_at_start|"
                      r"code_state|run_id|created|started|finished|wall_s)", re.I)


def leaves(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, f"{path}.{k}" if path else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, f"{path}[{i}]")
    else:
        yield path, x


def json_diff(a, b):
    la, lb = dict(leaves(a)), dict(leaves(b))
    out = []
    for k in sorted(set(la) | set(lb)):
        va, vb = la.get(k, "<absent>"), lb.get(k, "<absent>")
        if va != vb and not (isinstance(va, float) and isinstance(vb, float) and va != va and vb != vb):
            out.append((k, va, vb))
    return out


def npz_digest(p: Path) -> str:
    h = hashlib.sha256()
    with np.load(p, allow_pickle=False) as d:
        for k in sorted(d.files):
            a = d[k]
            h.update(k.encode())
            h.update(str(a.dtype).encode())
            h.update(str(a.shape).encode())
            h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--out")
    a = ap.parse_args()
    b0, b1 = Path(a.before), Path(a.after)
    rep = {"before": str(b0), "after": str(b1), "npz": {}, "json": {}, "ok": True}
    n0 = sorted(p.relative_to(b0).as_posix() for p in b0.rglob("*.npz"))
    n1 = sorted(p.relative_to(b1).as_posix() for p in b1.rglob("*.npz"))
    rep["npz_files_equal_sets"] = n0 == n1
    rep["ok"] &= n0 == n1
    for rel in n0:
        if rel not in n1:
            continue
        p0, p1 = b0 / rel, b1 / rel
        with np.load(p0, allow_pickle=False) as d0, np.load(p1, allow_pickle=False) as d1:
            same_keys = sorted(d0.files) == sorted(d1.files)
            bad = [k for k in d0.files if k in d1.files and not (
                d0[k].dtype == d1[k].dtype and d0[k].shape == d1[k].shape
                and np.array_equal(d0[k], d1[k], equal_nan=d0[k].dtype.kind in "fc"))]
        rep["npz"][rel] = {"same_keys": same_keys, "arrays": len(d0.files) if same_keys else None,
                           "differing_arrays": bad, "digest_before": npz_digest(p0), "digest_after": npz_digest(p1)}
        rep["ok"] &= same_keys and not bad
    j0 = sorted(p.relative_to(b0).as_posix() for p in b0.rglob("*.json"))
    j1 = sorted(p.relative_to(b1).as_posix() for p in b1.rglob("*.json"))
    rep["json_files_equal_sets"] = j0 == j1
    rep["ok"] &= j0 == j1
    for rel in j0:
        if rel not in j1:
            continue
        d = json_diff(json.loads((b0 / rel).read_text(encoding="utf-8")),
                      json.loads((b1 / rel).read_text(encoding="utf-8")))
        vol = [k for k, _, _ in d if VOLATILE.search(k)]
        rest = [(k, va, vb) for k, va, vb in d if not VOLATILE.search(k)]
        rep["json"][rel] = {"differing_leaves": len(d), "volatile": vol[:60], "volatile_count": len(vol),
                            "non_volatile": [[k, str(va)[:160], str(vb)[:160]] for k, va, vb in rest][:60],
                            "non_volatile_count": len(rest)}
        rep["ok"] &= not rest
    txt = json.dumps(rep, indent=1, default=str)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
    for rel, r in rep["npz"].items():
        print("npz", rel, "equal" if r["same_keys"] and not r["differing_arrays"] else f"DIFF {r['differing_arrays']}",
              r["digest_before"][:12], r["digest_after"][:12])
    for rel, r in rep["json"].items():
        print("json", rel, "volatile", r["volatile_count"], "non-volatile", r["non_volatile_count"],
              r["non_volatile"][:5])
    print("ok", rep["ok"])
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
