"""C8 V0 smoke (re-audit M'-3, control NB-1 decision 6.1): the two jobs of ``jobs.json`` run by
``run_v5.run_one`` of the C8 checkout (the run_v5 pool path: spawn, one task per worker, the
job ``mask`` sets the worker affinity), lines into ``v0_smoke.jsonl`` with the run identity
at the start and the end (``run_v5._write_identity``).

Usage (dynamics-dev ``python.exe -I -B``, the C8 checkout as the current folder):
  python -I -B run_smoke.py <C8 checkout> <runner folder> <mask hex>
"""
import argparse
import json
import sys
from pathlib import Path

TREE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
if TREE is not None:
    for _path in (TREE / "04_scripts" / "04_hydraulic" / "coupled", TREE / "03_src"):
        if str(_path) not in sys.path:
            sys.path.insert(0, str(_path))


def main() -> int:
    import run_v5
    import verdict_runs

    folder = Path(sys.argv[2])
    mask = int(sys.argv[3], 16)
    out = folder / "v0_smoke.jsonl"
    if out.exists():
        print(json.dumps({"status": "input_error", "reason": f"{out} exists"}))
        return 2
    jobs = json.loads((folder / "jobs.json").read_text(encoding="utf-8"))
    for job in jobs:
        job["mask"] = mask
        job["t4h_dir"] = str(folder / "t4h")
    verdict_runs.warm_numba_cache()
    run_v5._write_identity(out, "start")
    run_v5._run_pool(argparse.Namespace(workers=len(jobs)), jobs, out)
    run_v5._write_identity(out, "end")
    print(json.dumps({"status": "written", "lines": len(jobs), "out": str(out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
