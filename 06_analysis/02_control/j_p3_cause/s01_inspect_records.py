"""Step 1: dump the J-P3 breach records (extend_bound_check) for the five lines.

Read-only. Prints the job identity, extend_bound_check block, and the T4h npz
keys/shapes for the matching replay record.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\workspace\outrigger_control")
RK1 = ROOT / r"06_analysis\03_hydraulic\coupled\v5\resume_k1"


def find_key(d, key, path=""):
    out = []
    if isinstance(d, dict):
        for k, v in d.items():
            p = f"{path}.{k}" if path else k
            if k == key:
                out.append((p, v))
            out += find_key(v, key, p)
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out += find_key(v, key, f"{path}[{i}]")
    return out


def main():
    lines = (RK1 / "h10_reuse_rerun.jsonl").read_text(encoding="utf-8").splitlines()
    for ln in (28, 172, 245):
        rec = json.loads(lines[ln - 1])
        print("=" * 80)
        print("line", ln, json.dumps(rec["job"]))
        for p, v in find_key(rec, "extend_bound_check"):
            print(p)
            print(json.dumps(v, indent=1)[:4000])
    for fn, ri, rj in (("grid_r67_top.json", 13, 3), ("grid_r69_bottom.json", 12, 0)):
        d = json.loads((RK1 / "h9_grid" / fn).read_text(encoding="utf-8"))
        res = d["results"][ri]
        print("=" * 80)
        print(fn, ri, rj, {k: v for k, v in res.items() if k != "runs"})
        run = res["runs"][rj]
        print("run keys", list(run.keys())[:40])
        for p, v in find_key(run, "extend_bound_check"):
            print(p)
            print(json.dumps(v, indent=1)[:4000])
    if len(sys.argv) > 1:
        z = np.load(sys.argv[1], allow_pickle=True)
        for k in z.files:
            a = z[k]
            print(k, a.shape, a.dtype)


if __name__ == "__main__":
    main()
