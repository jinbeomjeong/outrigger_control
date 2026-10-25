"""Re-judge recorded S8 batches with the judge of a given ``03_src`` tree (no Chrono run).

Moved from the cad scratchpad (``cad-run/rejudge54.py``, ``cad-run/rejudge55.py``,
``cad-run55/rejudge56.py``, 2026-10-25). This file is ``rejudge56.py``; the rev. 54 and rev. 55
versions are its subsets (rev. 54: ml768 / mlj / p1r / rest; rev. 55: + A / B / C / D without
``deferred_ref``). ``D`` gets ``deferred_ref`` (MLJ batch) only when the judge supports it
(``judge_batch(..., deferred_ref=...)``, C-S8-42, judge rev. 56), so the same command reproduces
the rev. 54 / 55 outputs on a tree holding that judge.

Sources are read only. Outputs ``<out>/verify_<kind>_<which>_<tag>.json``.

usage (Chrono-dev python)::

    python -I -X utf8 rejudge_batches.py --src <03_src dir> --tag new56 --out <dir>
        [--results 07_results/S8] [which ...]

which: A B C D ml768 mlj p1r rest (default all). Copies of the 2026-10-25 outputs (local only,
``07_results`` is gitignored): ``07_results/S8/archive/18_S8_extra/rejudge/{rev54,rev55,rev56}/``
(A B C D mlj p1r rest) and ``07_results/S8/archive/rejudge_ml768/{rev54,rev55,rev56}/`` (ml768).
Git keeps summaries only: ``06_analysis/01_chrono/18_S8/rejudge/{rev54,rev55,rev56}/``.
"""
import argparse
import inspect
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
ALL = ["A", "B", "C", "D", "ml768", "mlj", "p1r", "rest"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", type=Path, required=True, help="03_src tree whose judge is used")
    ap.add_argument("--tag", required=True, help="file name tag, e.g. rev54 / pre55 / new56")
    ap.add_argument("--out", type=Path, required=True, help="output folder (created)")
    ap.add_argument("--results", type=Path,
                    default=Path(__file__).resolve().parents[3] / "07_results" / "S8",
                    help="07_results/S8 folder holding the recorded batches")
    ap.add_argument("which", nargs="*", help=f"subset of {' '.join(ALL)} (default all)")
    a = ap.parse_args(argv)
    bad = [w for w in a.which if w not in ALL]
    if bad:
        ap.error(f"unknown batch key(s) {bad}; choose from {ALL}")
    sys.path.insert(0, str(a.src.resolve()))
    from outrigger_sim.verify import s8_control as v  # noqa: E402

    print("module:", v.__file__, flush=True)
    r = a.results.resolve()
    ml = r / "ml_main_20261025_090131"
    mlj = r / "mlj_20261025_080212"
    p1 = r / "p1_20261024_204911"
    p1r = r / "p1r_20261024_222013"
    rest = r / "rest_20261024_233615"
    c36 = r / "c36_20261025_155317"
    has_dref = "deferred_ref" in inspect.signature(v.judge_batch).parameters
    out, tag = a.out, a.tag
    out.mkdir(parents=True, exist_ok=True)
    for w in a.which or ALL:
        t = time.perf_counter()
        if w == "A":
            p = v.judge_ml_batch(c36 / "A_rt", out / f"verify_S8ML_A_{tag}.json", ref_batch=ml)
        elif w == "B":
            p = v.judge_ml_batch(c36 / "B_f1only", out / f"verify_S8ML_B_{tag}.json",
                                 ref_batch=ml)
        elif w == "C":
            p = v.judge_batch(c36 / "C_gate", out / f"verify_S8C_C_{tag}.json", ref_batch=p1r,
                              lookup_batches=[p1r, rest])
        elif w == "D":
            kw = {"deferred_ref": mlj} if has_dref else {}
            p = v.judge_batch(c36 / "D_fs24", out / f"verify_S8C_D_{tag}.json",
                              lookup_batches=[p1r], **kw)
        elif w == "ml768":
            p = v.judge_ml_batch(ml, out / f"verify_S8ML_ml768_{tag}.json")
        elif w == "mlj":
            p = v.judge_batch(ml / "judged", out / f"verify_S8C_mlj_{tag}.json",
                              lookup_batches=[p1r])
        elif w == "p1r":
            p = v.judge_batch(p1r, out / f"verify_S8C_p1r_{tag}.json", ref_batch=p1,
                              lookup_batches=[p1, rest])
        elif w == "rest":
            p = v.judge_batch(rest, out / f"verify_S8C_rest_{tag}.json", ref_batch=p1r,
                              lookup_batches=[p1r])
        else:
            raise SystemExit(f"unknown {w}")
        print(f"{w}: {p} {time.perf_counter() - t:.1f} s", flush=True)


if __name__ == "__main__":
    main()
