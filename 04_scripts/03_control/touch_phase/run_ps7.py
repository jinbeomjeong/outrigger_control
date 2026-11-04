"""PS-7 (pre-grounded leg) regression of a TOUCH candidate on the r68 screen path (T-1 .. T-5, D8).

Usage (dynamics-dev): python -I run_ps7.py <candidate or E> [--workers N] [--mask HEX]
Output: 06_analysis/02_control/touch_phase/ps7_<candidate>.json. Deterministic.
"""
from __future__ import annotations

import argparse
import json
import sys
from itertools import product
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "06_analysis" / "02_control" / "touch_phase"
for _path in (HERE, ROOT / "04_scripts" / "03_control" / "s8", ROOT / "04_scripts" / "03_control" / "r8d1"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
CASES = ("ref", "PS7a_RR", "PS7a_FL", "PS7b_RR", "PS7c_RR")
LEVELS = ("top", "bottom")
FS = (0.0, 8.0)


def run_one(job: dict) -> dict:
    import run_touch_phase as rtp

    rtp.pin(job["mask"])
    sys.argv = ["run_ps7", str(ROOT)]  # the r51 / r67 / r68 modules read the root from argv
    import candidates
    import r68_p27_screen as r68

    r51 = r68.r51
    _, c2, _ = r51._imports()
    candidates.install_candidate(None if job["cand"] == "E" else job["cand"])
    result = r68.run_job(f"ps7|{job['case']}|{job['level']}|{job['fs']}|proj")
    result["cand"] = job["cand"]
    result["trim"] = dict(candidates.RECORD)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cand")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--mask", default="0x0F000000")
    args = parser.parse_args()
    mask = int(args.mask, 16)
    if (OUT / f"ps7_{args.cand}.json").exists():
        print("already done", args.cand)
        return
    import run_touch_phase as rtp

    rtp.pin(mask)
    jobs = [{"case": c, "level": lv, "fs": fs, "cand": args.cand, "mask": mask}
            for c, lv, fs in product(CASES, LEVELS, FS)]
    out = []
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool:
        for rec in pool.imap_unordered(run_one, jobs):
            out.append(rec)
            touch = rec.get("touch", {})
            print(rec.get("key"), rec.get("error", ""), "min", rec.get("min_F_after_liftoff_kN"), "pass", rec.get("pass"),
                  "ready", rec.get("t_ready"), "T3", touch.get("extra_stroke_mm"), "T4", touch.get("max_abs_att_deg"),
                  "D", rec.get("trim", {}).get("D_hat_kN"), rec.get("cmd_sha256"), flush=True)
    (OUT / f"ps7_{args.cand}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
