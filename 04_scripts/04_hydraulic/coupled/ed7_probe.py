"""436.9 edition 7 probe (``jp3_remedy_spec_v7.md`` 4 step 2): component shares, condition 3.

Before the seal, a design input (public, not a judgement). Two parts:

* main part: :data:`PROBE_KEY_JOBS` (15 keys, spec 4.2 key list ``>= 14``) x six plants x
  seven controller arms = 630 runs;
* ③ prediction check (P7-8): the 12 grid keys of the edition 6 record part D
  (:data:`D_KEY_JOBS`, ``ed6-records`` 3ecf61f1 ``d_grid_keys12.json``, sha256
  :data:`D_KEY_FILE_SHA256`) x plants ``M`` and ``Mslow`` x arm ``a2`` = 24 runs.

=======  ===================================================================================
plant    plant options (``run_v5``)
=======  ===================================================================================
M        ``ed7_plant()``: the VBJ plant with the P1 supplement (a)(c)(d), nominal (= VBM)
Mslow    ``ed7_plant("slow")`` (= VBMslow)
Mfast    ``ed7_plant("fast")`` (= VBMfast)
Mc005    ``ed7_plant("c005")`` (= VBMc005)
Mc04     ``ed7_plant("c04")`` (= VBMc04)
L        ``ed6_plant()``: the edition 6 VBL plant (no supplement; the share of the supplement)
=======  ===================================================================================

=======  =========================  =============================================================
arm      components                 controller (every arm: ③ rev 7, tag ``final_C4G2_P3X_LAS_K1
                                    _LSB``, and the D6 witness + probe retract target unless noted)
=======  =========================  =============================================================
a1       A_i, A_ii, B3              spec 4.2 arm 1: the edition 6 sealed range
a2       A_i, A_ib, A_ii, B3        arm 2: the edition 7 draft (condition 3 (다), latch, protect)
a3       as a2                      arm 3: condition 3 = first draft (LEVEL completion open)
a4       as a2                      arm 4: condition 3 = (나) (attitude or clearance open)
a5       A_i, A_ib, A_ii            arm 5: a2 - B3
a6       A_ib, A_ii, B3             arm 6: a2 - A(i) (its edition 6 trigger off, A(i)-b on)
c2       as a2                      control arm: a2 with the D6 witness and the retract target off
=======  =========================  =============================================================

Setting names ``P7-<plant>-<arm>`` (``P7-Mslow-a2``); they live in this script only.
:func:`install_probe_switches` (the parent before reading ``--out``, every worker before its
run, never at import) adds them to ``run_v5`` with their T4h record and turns the per-read P1
record on (record only).

Output: one ``run_v5.run_one`` line per run in ``--out`` (appended, finished jobs skipped), an
``ed7_probe`` block per line (plant, arm, part, components, the arm's ``lsb_parameters``,
modules imported from another checkout), T4h records in ``<out stem>_t4h/``, the run identity
``<out stem>.identity.json`` (start and end) and the progress file ``<out stem>.progress.json``
(keys ``stage``, ``done``, ``total``, ``unit``, ``started_at``, ``updated_at``; counts only, no
result value). The share and condition 3 decisions are a later tool (spec 4.2 rules).

======  =============================================================
exit    meaning
======  =============================================================
0       every planned job has a line without error
1       some line has an error (the batch went on)
2       input error (unknown plant, arm, key or part, bad mask)
3       tool error
======  =============================================================

Usage (dynamics-dev, checkout root):
  python -I -B 04_scripts/04_hydraulic/coupled/ed7_probe.py --out <jsonl> [--workers N]
      [--mask HEX] [--part main|d|all] [--plants M,Mslow] [--arms a2,a3] [--keys K1,K2]
      [--list]
The stdout's last line is JSON with ``status``, the counts and the output path.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import d0_plant_split as d0  # noqa: E402  (imports run_v5; importing it switches nothing)
import ed6_probe  # noqa: E402  (ProgressFile, the line writer precedent)
import run_v5  # noqa: E402

EXIT_OK, EXIT_ERROR_LINES, EXIT_INPUT, EXIT_TOOL = 0, 1, 2, 3
SETTING_PREFIX = "P7"
PLANTS: dict[str, str | None] = {"M": None, "Mslow": "slow", "Mfast": "fast", "Mc005": "c005",
                                 "Mc04": "c04", "L": "ed6"}
"""Plant name -> ``run_v5.ED7_SENSITIVITY`` key (None = nominal VBM, ``ed6`` = the VBL plant)."""
_A2 = ("A_i", "A_ib", "A_ii", "B3")
ARMS: dict[str, tuple[str, ...]] = {"a1": ("A_i", "A_ii", "B3"), "a2": _A2, "a3": _A2,
                                    "a4": _A2, "a5": ("A_i", "A_ib", "A_ii"),
                                    "a6": ("A_ib", "A_ii", "B3"), "c2": _A2}
ARM_PARAMETERS: dict[str, dict] = {"a3": {"ib_condition": "level_incomplete"},
                                   "a4": {"ib_condition": "attitude_clearance"}}
ARMS_WITHOUT_D6 = ("c2",)
"""The control arm without the D6 witness and the probe retract target (spec 4.2)."""
PROBE_KEY_JOBS: tuple[dict, ...] = (
    {"case": "R12", "eps": 0.0, "offset_s": 0.0,
     "twin": {"level": "top", "leg": "FR", "fs_kN": 0.0}},
    {"case": "R12", "eps": 0.0, "offset_s": 0.05,
     "twin": {"level": "top", "leg": "FR", "fs_kN": 0.0}},
    {"case": "R12", "eps": 0.0, "offset_s": 0.0,
     "twin": {"level": "top", "leg": "RL", "fs_kN": 0.0}},
    {"case": "S7", "eps": 0.001},
    {"case": "R2", "eps": 0.001},
    {"case": "R2", "eps": 0.003},
    {"case": "S4", "eps": 0.002},
    *d0.D0_KEY_JOBS,
)
"""Spec 4.2 keys (stats S3): the (가) failure keys R12 top-FR-Fs0 o0.0 / o0.05 (also the
counterfactual C dwell key of FR-Fs0), the counterfactual C dwell key top-RL-Fs0 o0.0
(``cf_f3_blind_band.csv``), the long normal-row dwells S7 e0.001 (sensitivity v05, 49 s),
R2 e0.001 / e0.003 (LSL) and S4 e0.002 (the S4 phase with the most dwell rows in
``dynamics_v7/d2_dwells.csv``; chosen by python-expert, 확인 필요), and the eight D0 keys of
the edition 6 probe: 15 keys."""
_D_TWINS = (("top", "RR", 0.0, "FS24", 0.0), ("bottom", "RR", 0.0, "FS24", 0.05),
            ("top", "RL", 8.0, "FS24", 0.025), ("bottom", "FL", 2.0, "FS24", 0.075),
            ("top", "RR", 0.0, "G4", 0.075), ("bottom", "RR", 0.0, "G4", 0.05),
            ("bottom", "RL", 4.0, "G4", 0.025), ("bottom", "RR", 2.0, "G4", 0.0),
            ("top", "RR", 0.0, "RE1bF", 0.0), ("bottom", "RR", 0.0, "RE1bF", 0.05),
            ("top", "RL", 4.0, "RE1bF", 0.025), ("top", "RR", 4.0, "RE1bF", 0.075))
D_KEY_JOBS: tuple[dict, ...] = tuple(
    {"case": "R12", "eps": 0.0, "offset_s": offset,
     "twin": {"level": level, "leg": leg, "fs_kN": fs, "event": event, "timing": "level"}}
    for level, leg, fs, event, offset in _D_TWINS)
"""The 12 jobs of ``d_grid_keys12.json`` (the H-7 LEVEL breach lines of the edition 6 grid,
record part D), in its order; a unit test reads the blob and compares."""
D_KEY_FILE_SHA256 = "a995abff9d73816f58a0e3d67a59f18b3e60fb006fe48d824012b79b57d87981"
D_KEY_FILE_BLOB = ("3ecf61f1:06_analysis/02_control/j_p3_cause/prelaunch_j9/run_records_ed6/"
                   "d_grid_keys12.json")
D_PART_PLANTS, D_PART_ARM = ("M", "Mslow"), "a2"
PARTS = ("main", "d", "all")
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
        raise ValueError(f"{name!r} is not an edition 7 probe setting")
    return plant, arm


def _plant_options(plant: str) -> dict:
    sensitivity = PLANTS[plant]
    if sensitivity == "ed6":
        return run_v5.ed6_plant()
    return run_v5.ed7_plant(sensitivity)


def probe_settings() -> dict[str, tuple[bool, dict]]:
    """Every probe setting: (flow limit on, plant options as ``HydraulicOptions`` keys)."""
    settings = {}
    for plant in PLANTS:
        for arm, components in ARMS.items():
            options = {**_plant_options(plant), **run_v5._P3X,
                       "lsb_components": list(components)}
            if ARM_PARAMETERS.get(arm):
                options["lsb_parameters"] = dict(ARM_PARAMETERS[arm])
            if arm not in ARMS_WITHOUT_D6:
                options["probe_d6_settings"] = dict(run_v5.PROBE_D6_ED7)
            settings[setting_name(plant, arm)] = (True, options)
    return settings


def install_probe_switches() -> None:
    """The process-wide probe switches (idempotent; the parent before reading ``--out``, every
    worker before its run): the probe settings in ``run_v5`` (with their T4h record) and the
    per-read P1 record. Importing this module changes nothing (the unit tests import it)."""
    import harness_hydraulics  # after run_v5: it needs the harness folders on sys.path

    harness_hydraulics.enable_p1_read_record()
    settings = probe_settings()
    run_v5.ALL_SETTINGS.update(settings)
    missing = tuple(name for name in settings if name not in run_v5.T4H_SETTINGS)
    run_v5.T4H_SETTINGS = (*run_v5.T4H_SETTINGS, *missing)


KEYS: dict[str, dict] = {d0.key_name(job): dict(job) for job in PROBE_KEY_JOBS}
D_KEYS: dict[str, dict] = {d0.key_name(job): dict(job) for job in D_KEY_JOBS}


def probe_jobs(plants: tuple[str, ...] = tuple(PLANTS), arms: tuple[str, ...] = tuple(ARMS),
               keys: tuple[str, ...] = tuple(KEYS), part: str = "all") -> list[dict]:
    """Plant-major, then arm, then key; the D part (24 jobs) after the main part (630)."""
    jobs = []
    if part in ("main", "all"):
        jobs += [{**KEYS[key], "setting": setting_name(plant, arm)}
                 for plant in plants for arm in arms for key in keys]
    if part in ("d", "all"):
        jobs += [{**D_KEYS[key], "setting": setting_name(plant, D_PART_ARM)}
                 for plant in D_PART_PLANTS for key in D_KEYS]
    return jobs


def run_probe_job(job: dict) -> dict:
    """Worker: one ``run_v5.run_one`` line with the ``ed7_probe`` record block."""
    import harness_hydraulics

    install_probe_switches()
    record = run_v5.run_one(job)
    plant, arm = split_setting_name(job["setting"])
    record["ed7_probe"] = {"plant": plant, "arm": arm,
                           "part": "d" if _is_d_job(job) else "main",
                           "components": list(ARMS[arm]),
                           "lsb_parameters": dict(ARM_PARAMETERS.get(arm, {})),
                           "probe_d6": arm not in ARMS_WITHOUT_D6,
                           "p1_read_record": harness_hydraulics.is_p1_read_record_on(),
                           "foreign_modules": d0.modules_outside_checkout()}
    return record


def _is_d_job(job: dict) -> bool:
    """A D-part job: its twin names a grid event (the main-part keys have none)."""
    return "event" in (job.get("twin") or {})


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
    progress = ed6_probe.ProgressFile(out, len(todo))
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
    if args.part not in PARTS:
        raise ValueError(f"--part {args.part}: one of {PARTS}")
    plants = d0._names(args.plants, PLANTS, "plants")
    arms = d0._names(args.arms, ARMS, "arms")
    keys = d0._names(args.keys, KEYS, "keys")
    if args.mask is not None:
        int(args.mask, 16)
    return probe_jobs(plants, arms, keys, args.part)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="output jsonl (appended)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--mask", default=None, help="hex affinity mask, inherited by the workers")
    parser.add_argument("--part", default="all", help=f"one of {PARTS}")
    parser.add_argument("--plants", default=None, help=f"comma list of {list(PLANTS)}")
    parser.add_argument("--arms", default=None, help=f"comma list of {list(ARMS)}")
    parser.add_argument("--keys", default=None, help="comma list of the main-part keys")
    parser.add_argument("--list", action="store_true", help="print the jobs to do and stop")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        jobs = _selection(args)
    except ValueError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}), flush=True)
        return EXIT_INPUT
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
