"""Diagnostic: the R12 bottom-FL-Fs4 case on LSJ4 with ``carry_end_rule = "fresh_stretch"``
(the spec 3rd edition 2.1 form) on the 221456d code, without changing it.

221456d has no switch constant for the rule (``ExtendStartBound.carry_end_rule`` defaults to
``inherit_when_gate_shut`` and ``apply_controller_options`` builds the default). This file
wraps ``apply_controller_options`` at its top level, so every spawned worker (which imports
this file as ``__mp_main__``) builds the revision 5 bound with ``fresh_stretch``. The two
names that hold the function (``v5_options`` and ``harness_hydraulics``) are both replaced.
The setting name in the output is ``LSJ4`` (the job of ``run_v5.j9_case_jobs``); the rule is
recorded in the T4h meta (``two_pressure_settings.extend_start_bound.carry_end_rule``) and in
``carry_end_rule`` of every line written here.

Usage (dynamics-dev, worktree root as cwd):
  python -I -B fresh_stretch_replay.py <worktree root> --out <jsonl> [--mask HEX]
"""

import argparse
import dataclasses
import json
import sys
from multiprocessing import get_context
from pathlib import Path

WORKTREE = Path(sys.argv[1]).resolve()
COUPLED = WORKTREE / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED) not in sys.path:
    sys.path.insert(0, str(COUPLED))

import harness_hydraulics  # noqa: E402
import run_v5  # noqa: E402

from outrigger_sim.hydraulics import v5_options  # noqa: E402

CARRY_END_RULE = "fresh_stretch"
_apply_controller_options = v5_options.apply_controller_options


def apply_with_fresh_stretch(config, options, v_max_m_s, valve_tau_s):
    """The 221456d function, then the revision 5 bound with ``carry_end_rule`` replaced."""
    config = _apply_controller_options(config, options, v_max_m_s, valve_tau_s)
    two_pressure = config.two_pressure
    bound = two_pressure.extend_start_bound
    if bound is None or not bound.is_hold_revision:
        return config
    bound = dataclasses.replace(bound, carry_end_rule=CARRY_END_RULE)
    return dataclasses.replace(config, two_pressure=dataclasses.replace(
        two_pressure, extend_start_bound=bound))


v5_options.apply_controller_options = apply_with_fresh_stretch
harness_hydraulics.apply_controller_options = apply_with_fresh_stretch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("worktree")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mask", default=None)
    args = parser.parse_args()
    jobs = [job for job in run_v5.j9_case_jobs() if job["setting"] == "LSJ4"]
    t4h_dir = args.out.with_name(f"{args.out.stem}_t4h")
    mask = None if args.mask is None else int(args.mask, 16)
    for job in jobs:
        job["mask"], job["t4h_dir"] = mask, str(t4h_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with get_context("spawn").Pool(1, maxtasksperchild=1) as pool, \
            args.out.open("a", encoding="utf-8") as handle:
        for record in pool.imap_unordered(run_v5.run_one, jobs):
            for key in run_v5.RUNTIME_JOB_KEYS:
                record["job"].pop(key, None)
            record["carry_end_rule"] = CARRY_END_RULE
            handle.write(json.dumps(record, default=lambda v: v.item() if hasattr(v, "item")
                                    else str(v)) + "\n")
            print(record["job"]["setting"], record.get("error", "")[:300]
                  or record["commands_sha256"][:8], flush=True)


if __name__ == "__main__":
    main()
