"""436.9 case replay C and D (``06_analysis/02_control/j_p3_cause/jp3_remedy_spec.md`` 5.3): the
R12 bottom-FL-Fs4 offset 0.0 case on the VB plant with the P1 line-fill gate only.

* ``VBG4`` (C, test only): P1 with the ③ bound of revision 4. The combination is refused by
  ``v5_options`` (counterexample ⑥); this script turns ``ALLOW_GATE_WITH_REV4_FOR_TEST`` on at its
  top level, so the spawned workers (which import this file as ``__mp_main__``) run it too.
* ``VBG5`` (D): P1 with ③ revision 5 (tag ``final_C4G2_P3H``).

Both settings live in this script only (spec 4.2: not in ``run_v5.SETTINGS``). Cases A, B and E
are the ``run_v5`` batch ``j9_cases``. One JSON line per run (``run_v5.run_one``); T4h records in
``<out stem>_t4h/``.

Usage (dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_case_replay.py --out <jsonl> [--workers N]
      [--mask HEX] [--settings VBG4,VBG5]
This runner writes no run identity: run it under ``jp3_run_identity.py wrap <jsonl> -- ...``
(start / end records with git head and ``is_clean``, prelaunch audit M-1).
"""
from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import run_v5  # noqa: E402  (puts the harness folders and 03_src on sys.path)

from outrigger_sim.hydraulics import v5_options  # noqa: E402

v5_options.ALLOW_GATE_WITH_REV4_FOR_TEST = True  # case C only (spec 4.2)
_VB_PLANT_GATE = {**run_v5._VB_PLANT, "line_fill_gate": run_v5._vn(1.0)}
CASE_SETTINGS = {"VBG4": (True, {**_VB_PLANT_GATE, **run_v5._P3}),
                 "VBG5": (True, {**_VB_PLANT_GATE, **run_v5._P3H})}
"""Spec 5.3 C (P1 + revision 4, test only) and D (P1 + revision 5)."""
run_v5.ALL_SETTINGS.update(CASE_SETTINGS)
run_v5.T4H_SETTINGS = (*run_v5.T4H_SETTINGS, *CASE_SETTINGS)


def case_jobs(settings: tuple[str, ...]) -> list[dict]:
    row = {"case": "R12", "eps": 0.0, "offset_s": 0.0, "twin": dict(run_v5.J9_CASE_TWIN)}
    return [{**row, "setting": setting} for setting in settings]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--mask", default=None, help="hex affinity mask, inherited by the workers")
    parser.add_argument("--settings", default=",".join(CASE_SETTINGS))
    args = parser.parse_args()
    settings = tuple(name for name in args.settings.split(",") if name)
    unknown = sorted(set(settings) - set(CASE_SETTINGS))
    if unknown:
        parser.error(f"--settings takes {sorted(CASE_SETTINGS)}, got {unknown}")
    t4h_dir = args.out.with_name(f"{args.out.stem}_t4h")
    jobs = case_jobs(settings)
    mask = None if args.mask is None else int(args.mask, 16)
    for job in jobs:
        job["mask"], job["t4h_dir"] = mask, str(t4h_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool, \
            args.out.open("a", encoding="utf-8") as handle:
        for record in pool.imap_unordered(run_v5.run_one, jobs):
            for key in run_v5.RUNTIME_JOB_KEYS:
                record["job"].pop(key, None)
            handle.write(json.dumps(record, default=lambda v: v.item() if hasattr(v, "item")
                                    else str(v)) + "\n")
            handle.flush()
            print(record["job"]["setting"], record.get("error", "")[:200]
                  or record["commands_sha256"][:8], flush=True)


if __name__ == "__main__":
    main()
