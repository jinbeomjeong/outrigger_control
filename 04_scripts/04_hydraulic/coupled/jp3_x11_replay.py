"""436.9 edition 4a counterexample arm (``jp3_remedy_spec.md`` 13.3, P4-5a; J4a-13): case
replay E LSJ4 (R12 bottom-FL-Fs4 offset 0.0) with the test-only rules of ``extend_start_bound``.

* ``--arm both`` (setting ``LSJ4_X11``, judged against P4-5a): ``carry_end_rule =
  "fresh_stretch"`` and ``retract_start_rule = "model_only"`` (the edition 3 rev 5 behaviour).
* ``--arm fresh_only`` (setting ``LSJ4F_X11``, record only): ``fresh_stretch`` alone.

The module turns both test constants on and wraps ``apply_controller_options`` at its top level,
so every spawned worker (which imports this file as ``__mp_main__``) builds the bound with the
arm's rules (the arm travels in the environment variable :data:`ARM_ENV`). The two names that
hold the function (``v5_options`` and ``harness_hydraulics``) are both replaced. The rows carry
the rules in ``extend_bound_check`` (``carry_end_rule``, ``retract_start_rule``), so the J-P3
judgement refuses them (13.6); the setting names end in ``_X11`` and stay out of every
judgement list (R6). Write to an own folder.

Usage (dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_x11_replay.py --out <own folder>/<jsonl>
      [--arm both|fresh_only] [--mask HEX]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import harness_hydraulics  # noqa: E402
import run_v5  # noqa: E402  (puts the harness folders and 03_src on sys.path)

from outrigger_sim.control import extend_start_bound  # noqa: E402
from outrigger_sim.hydraulics import v5_options  # noqa: E402

ARM_ENV = "JP3_X11_ARM"
ARMS = {"both": ("LSJ4_X11", {"carry_end_rule": "fresh_stretch",
                              "retract_start_rule": "model_only"}),
        "fresh_only": ("LSJ4F_X11", {"carry_end_rule": "fresh_stretch"})}
"""Arm -> (setting name, bound rule changes)."""
BASE_SETTING = "LSJ4"

extend_start_bound.ALLOW_FRESH_STRETCH_FOR_TEST = True
extend_start_bound.ALLOW_MODEL_ONLY_RETRACT_START_FOR_TEST = True
for _name, _ in ARMS.values():
    run_v5.ALL_SETTINGS[_name] = run_v5.JP3_SETTINGS[BASE_SETTING]
run_v5.T4H_SETTINGS = (*run_v5.T4H_SETTINGS, *(name for name, _ in ARMS.values()))
_apply_controller_options = v5_options.apply_controller_options


def apply_with_test_rules(config, options, v_max_m_s, valve_tau_s):
    """The library function, then the revision 5 bound with the arm's rules."""
    config = _apply_controller_options(config, options, v_max_m_s, valve_tau_s)
    two_pressure = config.two_pressure
    bound = two_pressure.extend_start_bound
    arm = os.environ.get(ARM_ENV)
    if bound is None or not bound.is_hold_revision or arm not in ARMS:
        return config
    bound = dataclasses.replace(bound, **ARMS[arm][1])
    return dataclasses.replace(config, two_pressure=dataclasses.replace(
        two_pressure, extend_start_bound=bound))


v5_options.apply_controller_options = apply_with_test_rules
harness_hydraulics.apply_controller_options = apply_with_test_rules


def arm_jobs(arm: str) -> list[dict]:
    """The case E LSJ4 job under the arm's setting name."""
    setting = ARMS[arm][0]
    return [{**job, "setting": setting} for job in run_v5.j9_case_jobs()
            if job["setting"] == BASE_SETTING]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--arm", choices=sorted(ARMS), default="both")
    parser.add_argument("--mask", default=None, help="hex affinity mask, inherited by the worker")
    args = parser.parse_args()
    os.environ[ARM_ENV] = args.arm  # the spawned worker inherits it
    t4h_dir = args.out.with_name(f"{args.out.stem}_t4h")
    jobs = arm_jobs(args.arm)
    mask = None if args.mask is None else int(args.mask, 16)
    for job in jobs:
        job["mask"], job["t4h_dir"] = mask, str(t4h_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with get_context("spawn").Pool(1, maxtasksperchild=1) as pool, \
            args.out.open("a", encoding="utf-8") as handle:
        for record in pool.imap_unordered(run_v5.run_one, jobs):
            for key in run_v5.RUNTIME_JOB_KEYS:
                record["job"].pop(key, None)
            record["test_only_arm"] = args.arm
            handle.write(json.dumps(record, default=lambda v: v.item() if hasattr(v, "item")
                                    else str(v)) + "\n")
            print(record["job"]["setting"], record.get("error", "")[:300]
                  or record["commands_sha256"][:8], flush=True)


if __name__ == "__main__":
    main()
