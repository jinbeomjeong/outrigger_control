"""436.9 edition 6 probe (``jp3_remedy_spec_v6.md`` 4.2): the share of A(i), A(ii) and B.

Before the seal, a design input (spec 4.2, public): the eight D0 keys (the j9_main VBJ failure
keys of run 606f8713, ``d0_plant_split.D0_KEY_JOBS``) x five plants x eight controller arms =
320 runs: the arms of spec revision 1 4.2 (sha 4653c0c4, user decisions 2026-11-23; "B" =
B1 + B3, B2 off, A(ii) retraction only) plus "all - B3" (Q6-12). R14 is no probe key.

=======  ===========================================================================
plant    P1 line-fill gate on the VBJ plant (P1 .. P4 + LC, ``run_v5.ed6_plant``)
=======  ===========================================================================
J        nominal (VN, volume 1.0, c_v 0.02) - the VBJ plant
c005     c_v 0.005 (= ``VBLc005``)
c04      c_v 0.04 (= ``VBLc04``)
v05      volume_scale 0.5 (= ``VBLv05``)
v15      volume_scale 1.5 (= ``VBLv15``)
=======  ===========================================================================

=======  ================  ========================================================
arm      components        controller
=======  ================  ========================================================
a2       A_ii              spec 4.2 arm 1. Every arm: ③ revision 6 (tag
b        B1, B3            ``final_C4G2_P3W_LAS_K1_LSB``) plus its components
a2b      A_ii, B1, B3      (``HydraulicOptions.lsb_components``); arms 2 and 3
a1b      A_i, B1, B3       arm 4 (= all - A(ii))
a1a2     A_i, A_ii         arm 5 (= all - B)
a1a2b    A_i, A_ii, B1,    arm 6 (all)
         B3
a1a2bh   as a1a2b          arm 7: ``a2_hold_after_fill_s`` 1.0 (one increment held as a
                           speed floor after the plan, until a witness, at most 1 s)
a1a2b1   A_i, A_ii, B1     arm 8 (= all - B3, Q6-12)
=======  ================  ========================================================

Setting names ``P6-<plant>-<arm>`` (``P6-c04-a1a2b``); they live in this script only
(``d0_plant_split`` precedent: ``run_v5.SETTINGS`` and its pinned digests stay).
:func:`install_probe_switches` (the parent before reading ``--out``, every worker before its
run, never at import) adds them to ``run_v5`` with their T4h record and turns the per-read P1
record on (record only, ``harness_hydraulics.enable_p1_read_record``).

``--lsb-param NAME=VALUE`` (repeatable) sets an edition 6 threshold of every probe setting
(``LockStartBSettings`` fields, the spec 3 placeholders); the parent passes them to the workers
in :data:`PARAMETERS_ENV`. They are part of each line's ``hydraulic_options`` (a file run with
other values is refused: ``run_v5._done_keys``).

Output: one ``run_v5.run_one`` line per run in ``--out`` (appended, finished jobs skipped), an
``ed6_probe`` block per line (plant, arm, parameters, modules imported from another checkout),
T4h records in ``<out stem>_t4h/`` (with the ``lsb_*`` and ``p1_*`` per-read arrays), the run
identity ``<out stem>.identity.json`` (start and end) and the progress file
``<out stem>.progress.json`` (keys ``stage``, ``done``, ``total``, ``unit``, ``started_at``,
``updated_at``; no result values). The share decision and the summary are
``ed6_probe_share.py``.

======  =============================================================
exit    meaning
======  =============================================================
0       every planned job has a line without error
1       some line has an error (the batch went on)
2       input error (unknown plant, arm, key or parameter, bad mask)
3       tool error
======  =============================================================

Usage (dynamics-dev, checkout root):
  python -I -B 04_scripts/04_hydraulic/coupled/ed6_probe.py --out <jsonl> [--workers N]
      [--mask HEX] [--plants J,c04] [--arms a2,a1a2b] [--keys R12_o0.0,S5_e0.0]
      [--lsb-param NAME=VALUE ...] [--list]
The stdout's last line is JSON with ``status``, the counts and the output path.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import d0_plant_split as d0  # noqa: E402  (imports run_v5; importing it switches nothing)
import run_v5  # noqa: E402

from outrigger_sim.control.lock_start_b import LockStartBSettings, parameter_names  # noqa: E402

EXIT_OK, EXIT_ERROR_LINES, EXIT_INPUT, EXIT_TOOL = 0, 1, 2, 3
SETTING_PREFIX = "P6"
PLANTS: dict[str, str | None] = {"J": None, "c005": "c005", "c04": "c04", "v05": "v05",
                                 "v15": "v15"}
"""Plant name -> ``run_v5.ED6_P1_SENSITIVITY`` key (None = the nominal VBJ plant)."""
_B = ("B1", "B3")
ARMS: dict[str, tuple[str, ...]] = {"a2": ("A_ii",), "b": _B, "a2b": ("A_ii", *_B),
                                    "a1b": ("A_i", *_B), "a1a2": ("A_i", "A_ii"),
                                    "a1a2b": ("A_i", "A_ii", *_B),
                                    "a1a2bh": ("A_i", "A_ii", *_B),
                                    "a1a2b1": ("A_i", "A_ii", "B1")}
"""Arm name -> components (spec revision 1 4.2 arms 1 .. 7 and "all - B3")."""
ARM_PARAMETERS: dict[str, dict] = {"a1a2bh": {"a2_hold_after_fill_s": 1.0}}
"""Arm-own ``LockStartBSettings`` values (on top of ``--lsb-param``; the arm wins)."""
PARAMETERS_ENV = "ED6_PROBE_LSB_PARAMETERS"
"""JSON object of the ``--lsb-param`` values; the parent sets it before the pool."""
PROGRESS_UNIT = "run"


def setting_name(plant: str, arm: str) -> str:
    return f"{SETTING_PREFIX}-{plant}-{arm}"


def split_setting_name(name: str) -> tuple[str, str]:
    """``(plant, arm)`` of a probe setting name.

    Raises:
        ValueError: Not a probe setting name.
    """
    prefix, plant, arm = (name.split("-") + ["", ""])[:3]
    if prefix != SETTING_PREFIX or plant not in PLANTS or arm not in ARMS:
        raise ValueError(f"{name!r} is not a probe setting")
    return plant, arm


def probe_settings(parameters: dict | None = None) -> dict[str, tuple[bool, dict]]:
    """Every probe setting: (flow limit on, plant options as ``HydraulicOptions`` keys)."""
    settings = {}
    for plant, sensitivity in PLANTS.items():
        for arm, components in ARMS.items():
            options = {**run_v5.ed6_plant(sensitivity), **run_v5._P3W,
                       "lsb_components": list(components)}
            arm_parameters = {**(parameters or {}), **ARM_PARAMETERS.get(arm, {})}
            if arm_parameters:
                options["lsb_parameters"] = arm_parameters
            settings[setting_name(plant, arm)] = (True, options)
    return settings


def parameters_from_environment() -> dict:
    text = os.environ.get(PARAMETERS_ENV)
    return {} if not text else json.loads(text)


def install_probe_switches() -> None:
    """The process-wide probe switches (idempotent; the parent before reading ``--out``, every
    worker before its run): the probe settings in ``run_v5`` (with their T4h record) and the
    per-read P1 record. Importing this module changes nothing (the unit tests import it)."""
    import harness_hydraulics  # after run_v5: it needs the harness folders on sys.path

    harness_hydraulics.enable_p1_read_record()
    settings = probe_settings(parameters_from_environment())
    run_v5.ALL_SETTINGS.update(settings)
    missing = tuple(name for name in settings if name not in run_v5.T4H_SETTINGS)
    run_v5.T4H_SETTINGS = (*run_v5.T4H_SETTINGS, *missing)


def probe_jobs(plants: tuple[str, ...] = tuple(PLANTS), arms: tuple[str, ...] = tuple(ARMS),
               keys: tuple[str, ...] = tuple(d0.D0_KEYS)) -> list[dict]:
    """Plant-major, then arm, then key (320 jobs for the defaults)."""
    return [{**d0.D0_KEYS[key], "setting": setting_name(plant, arm)}
            for plant in plants for arm in arms for key in keys]


def run_probe_job(job: dict) -> dict:
    """Worker: one ``run_v5.run_one`` line with the ``ed6_probe`` record block."""
    import harness_hydraulics

    install_probe_switches()
    record = run_v5.run_one(job)
    plant, arm = split_setting_name(job["setting"])
    record["ed6_probe"] = {"plant": plant, "arm": arm, "components": list(ARMS[arm]),
                           "lsb_parameters": parameters_from_environment(),
                           "p1_read_record": harness_hydraulics.is_p1_read_record_on(),
                           "foreign_modules": d0.modules_outside_checkout()}
    return record


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


class ProgressFile:
    """``<out stem>.progress.json``: counts only, replaced atomically after every run."""

    def __init__(self, out: Path, total: int) -> None:
        self.path = out.with_name(f"{out.stem}.progress.json")
        self.state = {"stage": "run", "done": 0, "total": total, "unit": PROGRESS_UNIT,
                      "started_at": _now(), "updated_at": _now()}
        self._write()

    def advance(self) -> None:
        self.state["done"] += 1
        self.state["updated_at"] = _now()
        self._write()

    def finish(self) -> None:
        self.state["stage"] = "end"
        self.state["updated_at"] = _now()
        self._write()

    def _write(self) -> None:
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(json.dumps(self.state), encoding="utf-8")
        os.replace(temporary, self.path)


def parse_parameters(items: list[str] | None) -> dict:
    """``NAME=VALUE`` items as JSON values, checked against ``LockStartBSettings``.

    Raises:
        ValueError: An item without ``=``, an unknown name, or a value the settings refuse.
    """
    parameters: dict = {}
    for item in items or []:
        name, separator, text = item.partition("=")
        if not separator or name not in parameter_names():
            raise ValueError(f"--lsb-param {item!r}: NAME=VALUE with NAME in "
                             f"{sorted(parameter_names())}")
        parameters[name] = json.loads(text)
    LockStartBSettings(components=("A_i",), **parameters)  # refuses a bad value here
    return parameters


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="output jsonl (appended)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--mask", default=None, help="hex affinity mask, inherited by the workers")
    parser.add_argument("--plants", default=None, help=f"comma list of {list(PLANTS)}")
    parser.add_argument("--arms", default=None, help=f"comma list of {list(ARMS)}")
    parser.add_argument("--keys", default=None, help=f"comma list of {list(d0.D0_KEYS)}")
    parser.add_argument("--lsb-param", action="append", default=None, metavar="NAME=VALUE",
                        help="an edition 6 threshold of every probe setting (JSON value)")
    parser.add_argument("--list", action="store_true", help="print the jobs to do and stop")
    return parser


def run_batch(args: argparse.Namespace, jobs: list[dict]) -> dict:
    """Run the jobs not in ``args.out`` yet; the counts of the whole planned batch."""
    install_probe_switches()
    out = args.out.resolve()
    done = run_v5._done_keys(out)
    todo = [job for job in jobs if run_v5.job_key(job) not in done]
    mask = None if args.mask is None else int(args.mask, 16)
    for job in todo:
        job["mask"], job["t4h_dir"] = mask, str(out.with_name(f"{out.stem}_t4h"))
    out.parent.mkdir(parents=True, exist_ok=True)
    run_v5._write_identity(out, "start")
    progress = ProgressFile(out, len(todo))
    error_lines = 0
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool, \
            out.open("a", encoding="utf-8") as handle:
        for count, record in enumerate(pool.imap_unordered(run_probe_job, todo), 1):
            d0._write_line(handle, record)
            progress.advance()
            error_lines += "error" in record
            state = record.get("error", "")[:200] or f"{record['wall_s']}s"
            print(f"{count}/{len(todo)} {record['job']['setting']} "
                  f"{d0.key_name(record['job'])}: {state}", flush=True)
    progress.finish()
    run_v5._write_identity(out, "end")
    return {"planned": len(jobs), "run": len(todo), "skipped_done": len(jobs) - len(todo),
            "error_lines": error_lines}


def _selection(args: argparse.Namespace) -> list[dict]:
    """The planned jobs of the CLI choice (refusals raise ``ValueError``)."""
    plants = d0._names(args.plants, PLANTS, "plants")
    arms = d0._names(args.arms, ARMS, "arms")
    keys = d0._names(args.keys, d0.D0_KEYS, "keys")
    if args.mask is not None:
        int(args.mask, 16)
    return probe_jobs(plants, arms, keys)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        jobs = _selection(args)
        parameters = parse_parameters(args.lsb_param)
    except ValueError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}), flush=True)
        return EXIT_INPUT
    if parameters:
        os.environ[PARAMETERS_ENV] = json.dumps(parameters, sort_keys=True)
    if args.list:
        for job in jobs:
            print(job["setting"], d0.key_name(job), flush=True)
        print(json.dumps({"status": "listed", "planned": len(jobs), "out": str(args.out)}))
        return EXIT_OK
    try:
        counts = run_batch(args, jobs)
    except Exception:  # every unexpected failure is a tool error (exit 3), never a result
        traceback.print_exc()
        print(json.dumps({"status": "tool_error", "out": str(args.out)}), flush=True)
        return EXIT_TOOL
    status = "error_lines" if counts["error_lines"] else "ok"
    print(json.dumps({"status": status, **counts, "out": str(args.out)}), flush=True)
    return EXIT_ERROR_LINES if counts["error_lines"] else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
