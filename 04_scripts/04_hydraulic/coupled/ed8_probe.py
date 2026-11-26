"""436.9 edition 8 probe driver (``ed7_j9fail_8a2a52ce/cause_analysis.md`` 7 A, 8 P-3).

Before the edition 8 seal, a record probe (public, not a judgement). It runs the rows of four
sources on probe plants with probe controller arms, as ``run_v5.run_one`` lines, and turns on
the record-only switches: the edition 8 records (P-1 probe stiffness rounds, P-2 A(i)-b block
reasons, ``verdict_runs.enable_ed8_record``) and the per-read P1 record. ``ed7_probe.py`` stays
as it was (its 654 jobs are part of the edition 7 records).

=======  ==================================================================================
arm      controller (every arm: ③ rev 7, tag ``final_C4G2_P3X_LAS_K1_LSB``)
=======  ==================================================================================
a1..a6   the arms of ``ed7_probe.ARMS`` (a2 = the sealed edition 7 VBM controller)
c2       ``ed7_probe`` control arm: a2 with the D6 witness and the retract target off
a2w      **a2 - (i-b)**: a2 with the D6 witness on and the probe retract position target
         (i-b) off (``probe_d6_settings`` = :data:`PROBE_D6_WITNESS_ONLY`; direction A of the
         cause analysis: no retract target, the witness as a record)
=======  ==================================================================================

==========  ========================================================================
plant       plant options (``run_v5``)
==========  ========================================================================
M           ``ed7_plant()`` (= the VBM plant)
M<key>      ``ed7_plant(<key>)`` for the ten ``run_v5.ED7_SENSITIVITY`` keys (= VBM<key>)
LSM1..LSM4  ``ed7_plant()`` with the LSM<n> lock closure (= the LSM<n> plant)
L           ``ed6_plant()`` (= the VBL plant)
==========  ========================================================================

So ``P8-M-a2`` has the options of VBM, ``P8-LSM4-a2`` those of LSM4 and ``P8-Mslow-a2`` those
of VBMslow: their commands equal the stored edition 7 lines of the same row (a unit test and
``test_ed8_harness.py`` check it).

==========  ========================================================================
--part      rows (comma list; the union, one job per (setting, row))
==========  ========================================================================
main        the 15 ``ed7_probe.PROBE_KEY_JOBS`` rows on every ``--plants`` plant
d           the 12 ``ed7_probe.D_KEY_JOBS`` rows on the plants M and Mslow
j9main      the 388 rows of the ``run_v5`` ``ed7_j9_main`` batch, each on the plant of its
            setting (VBM -> M, LSM<n> -> LSM<n>)
file        the rows of ``--jobs-file``, each on the plant of its setting
            (:data:`SETTING_PLANT`): a JSON list of jobs, or the sealed key-file shape
            ``{"lines": [{"job": ...}]}`` (``sens_keys_ed7.json``: 460 rows)
==========  ========================================================================

Every row runs once per ``--arms`` arm (default :data:`DEFAULT_ARMS`); ``--plants`` and
``--keys`` (``d0_plant_split.key_name``, e.g. ``R12_top-FR-Fs0-o0.05``) filter the rows.

Output: one line per job in ``--out`` with an ``ed8_probe`` block (plant, arm, part, source
setting, components, ``lsb_parameters``, ``probe_d6_settings``, record switches, modules
imported from another checkout), T4h records in ``<out stem>_t4h/``, the run identity
``<out stem>.identity.json`` (start and end), the selection ``<out stem>.selection.json``
(CLI choice, jobs-file sha256, planned job count and the sha256 of the planned job keys) and
the progress file ``<out stem>.progress.json`` (keys ``stage``, ``done``, ``total``, ``unit``,
``started_at``, ``updated_at``; counts only, no result value; ``total`` = the jobs still to
run).

An existing ``--out`` is refused (exit 2) unless ``--resume`` is given; with ``--resume`` the
stored selection must be the same plan (the same planned job keys), and finished jobs are
skipped. Use a new ``--out`` for every run step.

======  =============================================================
exit    meaning
======  =============================================================
0       every planned job has a line without error
1       some line has an error (the batch went on)
2       input error (unknown plant, arm, part, key or setting, bad mask, a missing or
        unreadable jobs file, an existing --out without --resume, another plan on resume,
        an empty plan)
3       tool error
======  =============================================================

Usage (dynamics-dev, checkout root):
  python -I -B 04_scripts/04_hydraulic/coupled/ed8_probe.py --out <jsonl>
      [--part main,d,j9main,file] [--jobs-file <json>] [--plants M,LSM4] [--arms a2,a2w]
      [--keys K1,K2] [--workers N] [--mask HEX] [--resume] [--list]
The stdout's last line is JSON with ``status``, the counts and the output path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import d0_plant_split as d0  # noqa: E402  (imports run_v5; importing it switches nothing)
import ed6_probe  # noqa: E402  (ProgressFile)
import ed7_probe  # noqa: E402  (the edition 7 arms and key rows)
import run_v5  # noqa: E402

EXIT_OK, EXIT_ERROR_LINES, EXIT_INPUT, EXIT_TOOL = 0, 1, 2, 3
SETTING_PREFIX = "P8"
RECORD_BLOCK = "ed8_probe"
PROBE_D6_WITNESS_ONLY = {"witness": True, "retract_position_target": False}
"""Arm a2w: the D6 E3 witness (record and D6 input) without the (i-b) retract target."""
ARMS: dict[str, tuple[str, ...]] = {**ed7_probe.ARMS, "a2w": ed7_probe.ARMS["a2"]}
ARM_PARAMETERS: dict[str, dict] = dict(ed7_probe.ARM_PARAMETERS)
ARM_PROBE_D6: dict[str, dict | None] = {
    **{arm: dict(run_v5.PROBE_D6_ED7) for arm in ed7_probe.ARMS},
    **{arm: None for arm in ed7_probe.ARMS_WITHOUT_D6},
    "a2w": dict(PROBE_D6_WITNESS_ONLY),
}
"""``probe_d6_settings`` per arm (None = the D6 settings off)."""
DEFAULT_ARMS = ("a2", "a2w")
"""The two arms of the cause analysis 7 A experiment 2."""
LS_PLANTS = tuple(f"LSM{n}" for n in run_v5.LS_CLOSURES)
PLANTS: tuple[str, ...] = ("M", *(f"M{key}" for key in run_v5.ED7_SENSITIVITY), *LS_PLANTS,
                           "L")
SETTING_PLANT: dict[str, str] = {"VBM": "M",
                                 **{f"VBM{key}": f"M{key}" for key in run_v5.ED7_SENSITIVITY},
                                 **{name: name for name in LS_PLANTS}, "VBL": "L"}
"""Setting of a source row -> the probe plant with its plant options."""
PLANT_SETTING: dict[str, str] = {plant: setting for setting, plant in SETTING_PLANT.items()}
PARTS = ("main", "d", "j9main", "file")
D_PART_PLANTS = ed7_probe.D_PART_PLANTS
PROGRESS_UNIT = "run"


def setting_name(plant: str, arm: str) -> str:
    return f"{SETTING_PREFIX}-{plant}-{arm}"


def split_setting_name(name: str) -> tuple[str, str]:
    """``(plant, arm)`` of an edition 8 probe setting name.

    Raises:
        ValueError: Not an edition 8 probe setting name.
    """
    prefix, plant, arm = (name.split("-") + ["", ""])[:3]
    if prefix != SETTING_PREFIX or plant not in PLANTS or arm not in ARMS:
        raise ValueError(f"{name!r} is not an edition 8 probe setting")
    return plant, arm


def plant_options(plant: str) -> dict:
    """The plant options of a probe plant (the plant part of its source setting)."""
    if plant == "L":
        return run_v5.ed6_plant()
    if plant in LS_PLANTS:
        closure = run_v5.ED7_SETTINGS[plant][1]["lock_closure"]
        return {**run_v5.ed7_plant(), "lock_closure": dict(closure)}
    return run_v5.ed7_plant(None if plant == "M" else plant[1:])


def arm_options(arm: str) -> dict:
    """The controller options of an arm (③ rev 7, components, parameters, D6 settings)."""
    options = {**run_v5._P3X, "lsb_components": list(ARMS[arm])}
    if ARM_PARAMETERS.get(arm):
        options["lsb_parameters"] = dict(ARM_PARAMETERS[arm])
    if ARM_PROBE_D6[arm] is not None:
        options["probe_d6_settings"] = dict(ARM_PROBE_D6[arm])
    return options


def probe_settings() -> dict[str, tuple[bool, dict]]:
    """Every edition 8 probe setting: (flow limit on, ``HydraulicOptions`` keys)."""
    return {setting_name(plant, arm): (True, {**plant_options(plant), **arm_options(arm)})
            for plant in PLANTS for arm in ARMS}


def install_probe_switches() -> None:
    """The process-wide probe switches (idempotent; the parent before reading ``--out``, every
    worker before its run, never at import): the probe settings in ``run_v5`` with their T4h
    record, the per-read P1 record and the edition 8 records (record only)."""
    import harness_hydraulics  # after run_v5: it needs the harness folders on sys.path
    import verdict_runs

    harness_hydraulics.enable_p1_read_record()
    verdict_runs.enable_ed8_record()
    settings = probe_settings()
    run_v5.ALL_SETTINGS.update(settings)
    missing = tuple(name for name in settings if name not in run_v5.T4H_SETTINGS)
    run_v5.T4H_SETTINGS = (*run_v5.T4H_SETTINGS, *missing)


# ----------------------------------------------------------------------------- the plan
def _row_of(job: dict) -> dict:
    return {key: value for key, value in job.items() if key != "setting"}


def _rows_on_plants(rows: list[dict], plants: tuple[str, ...]) -> list[tuple[str, dict]]:
    return [(plant, dict(row)) for plant in plants for row in rows]


def _rows_of_settings(jobs: list[dict], what: str) -> list[tuple[str, dict]]:
    """(plant, row) of jobs that name a source setting.

    Raises:
        ValueError: A job without a setting of :data:`SETTING_PLANT`.
    """
    pairs = []
    for job in jobs:
        plant = SETTING_PLANT.get(job.get("setting"))
        if plant is None:
            raise ValueError(f"{what}: setting {job.get('setting')!r} is not one of "
                             f"{sorted(SETTING_PLANT)}")
        pairs.append((plant, _row_of(job)))
    return pairs


def read_jobs_file(path: Path) -> tuple[list[dict], str]:
    """The jobs of a jobs file and its sha256.

    Raises:
        ValueError: A missing or unreadable file, or neither shape.
    """
    try:
        data = Path(path).read_bytes()
        document = json.loads(data)
    except (OSError, ValueError) as exc:
        raise ValueError(f"--jobs-file {path}: {exc}") from exc
    if isinstance(document, dict) and isinstance(document.get("lines"), list):
        jobs = [line.get("job") for line in document["lines"]]
    elif isinstance(document, list):
        jobs = document
    else:
        raise ValueError(f"--jobs-file {path}: neither a list of jobs nor {{'lines': [...]}}")
    if not all(isinstance(job, dict) for job in jobs):
        raise ValueError(f"--jobs-file {path}: a line without a job object")
    return [dict(job) for job in jobs], hashlib.sha256(data).hexdigest()


def source_rows(parts: tuple[str, ...], plants: tuple[str, ...],
                file_jobs: list[dict] | None) -> list[tuple[str, str, dict]]:
    """(part, plant, row) of the chosen sources, before the arms and the key filter.

    Raises:
        ValueError: ``file`` without jobs, or a source row of an unknown setting.
    """
    rows: list[tuple[str, str, dict]] = []
    if "main" in parts:
        main = _rows_on_plants([dict(job) for job in ed7_probe.PROBE_KEY_JOBS], plants)
        rows += [("main", plant, row) for plant, row in main]
    if "d" in parts:
        d_plants = tuple(plant for plant in D_PART_PLANTS if plant in plants)
        d_rows = _rows_on_plants([dict(job) for job in ed7_probe.D_KEY_JOBS], d_plants)
        rows += [("d", plant, row) for plant, row in d_rows]
    if "j9main" in parts:
        j9main = run_v5.ed7_batch_jobs(run_v5.ED7_J9_MAIN_BATCH)
        rows += [("j9main", plant, row) for plant, row in _rows_of_settings(j9main, "j9main")
                 if plant in plants]
    if "file" in parts:
        if file_jobs is None:
            raise ValueError("--part file needs --jobs-file")
        rows += [("file", plant, row) for plant, row in _rows_of_settings(file_jobs, "file")
                 if plant in plants]
    return rows


def probe_jobs(parts: tuple[str, ...], plants: tuple[str, ...], arms: tuple[str, ...],
               keys: tuple[str, ...] | None = None,
               file_jobs: list[dict] | None = None) -> list[dict]:
    """The planned jobs: source rows (part order, then plant, then row) x arms, the key filter
    applied, one job per (setting, row) (the first part that names it).

    Raises:
        ValueError: As :func:`source_rows`.
    """
    jobs, seen = [], set()
    for part, plant, row in source_rows(parts, plants, file_jobs):
        if keys is not None and d0.key_name(row) not in keys:
            continue
        for arm in arms:
            job = {**row, "setting": setting_name(plant, arm)}
            identity = run_v5.job_key(job)
            if identity in seen:
                continue
            seen.add(identity)
            jobs.append({**job, "_part": part})
    return jobs


def plan_sha256(jobs: list[dict]) -> str:
    """sha256 of the sorted planned job keys (the resume check)."""
    keys = sorted(run_v5.job_key(_without_part(job)) for job in jobs)
    return hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest()


def _without_part(job: dict) -> dict:
    return {key: value for key, value in job.items() if key != "_part"}


# ----------------------------------------------------------------------------- the run
def run_probe_job(job: dict) -> dict:
    """Worker: one ``run_v5.run_one`` line with the ``ed8_probe`` record block."""
    import harness_hydraulics
    import verdict_runs

    install_probe_switches()
    part = job.pop("_part")
    record = run_v5.run_one(job)
    plant, arm = split_setting_name(job["setting"])
    record[RECORD_BLOCK] = {"plant": plant, "arm": arm, "part": part,
                            "source_setting": PLANT_SETTING[plant],
                            "components": list(ARMS[arm]),
                            "lsb_parameters": dict(ARM_PARAMETERS.get(arm, {})),
                            "probe_d6_settings": ARM_PROBE_D6[arm],
                            "p1_read_record": harness_hydraulics.is_p1_read_record_on(),
                            "ed8_record": verdict_runs.is_ed8_record_on(),
                            "foreign_modules": d0.modules_outside_checkout()}
    return record


def _selection_path(out: Path) -> Path:
    return out.with_name(f"{out.stem}.selection.json")


def _check_output(out: Path, selection: dict, is_resume: bool) -> None:
    """Rule (나′): a new output path per run step; ``--resume`` only for the same plan.

    Raises:
        ValueError: An existing output without ``--resume``, a resume without the stored
            selection or with another plan.
    """
    if not out.exists():
        return
    if not is_resume:
        raise ValueError(f"--out {out} exists: use a new path (or --resume for the same plan)")
    stored_path = _selection_path(out)
    if not stored_path.exists():
        raise ValueError(f"--resume: {stored_path.name} is missing")
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    if stored.get("plan_sha256") != selection["plan_sha256"]:
        raise ValueError("--resume: the stored selection is another plan")


def run_batch(args: argparse.Namespace, jobs: list[dict], selection: dict) -> dict:
    """Run the planned jobs not in ``args.out`` yet; the counts of the whole plan."""
    install_probe_switches()
    out = args.out.resolve()
    done = run_v5._done_keys(out)
    todo = [job for job in jobs if run_v5.job_key(_without_part(job)) not in done]
    mask = None if args.mask is None else int(args.mask, 16)
    for job in todo:
        job["mask"], job["t4h_dir"] = mask, str(out.with_name(f"{out.stem}_t4h"))
    out.parent.mkdir(parents=True, exist_ok=True)
    selection_path = _selection_path(out)
    if not selection_path.exists():
        selection_path.write_text(json.dumps(selection, indent=1), encoding="utf-8")
    run_v5._write_identity(out, "start")
    progress = ed6_probe.ProgressFile(out, len(todo))
    error_lines = 0
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool, \
            out.open("a", encoding="utf-8") as handle:
        for count, record in enumerate(pool.imap_unordered(run_probe_job, todo), 1):
            d0._write_line(handle, record)
            progress.advance()
            error_lines += "error" in record
            state = "error" if "error" in record else f"{record['wall_s']}s"
            print(f"{count}/{len(todo)} {record['job']['setting']} "
                  f"{d0.key_name(record['job'])}: {state}", flush=True)
    progress.finish()
    run_v5._write_identity(out, "end")
    return {"planned": len(jobs), "run": len(todo), "skipped_done": len(jobs) - len(todo),
            "error_lines": error_lines}


# ----------------------------------------------------------------------------- the CLI
def _parts(text: str) -> tuple[str, ...]:
    parts = tuple(name for name in text.split(",") if name)
    unknown = sorted(set(parts) - set(PARTS))
    if not parts or unknown:
        raise ValueError(f"--part takes {list(PARTS)}, got {unknown or parts}")
    return parts


def _selection(args: argparse.Namespace) -> tuple[list[dict], dict]:
    """The planned jobs of the CLI choice and the selection record (refusals raise
    ``ValueError``)."""
    parts = _parts(args.part)
    plants = d0._names(args.plants, dict.fromkeys(PLANTS), "plants")
    arms = d0._names(args.arms or ",".join(DEFAULT_ARMS), ARMS, "arms")
    keys = None if args.keys is None else tuple(name for name in args.keys.split(",") if name)
    if args.mask is not None:
        int(args.mask, 16)
    file_jobs, file_sha256 = (None, None)
    if args.jobs_file is not None:
        file_jobs, file_sha256 = read_jobs_file(args.jobs_file)
    elif "file" in parts:
        raise ValueError("--part file needs --jobs-file")
    jobs = probe_jobs(parts, plants, arms, keys, file_jobs)
    if keys is not None:
        found = {d0.key_name(job) for job in jobs}
        missing = sorted(set(keys) - found)
        if missing:
            raise ValueError(f"--keys {missing}: no row of the chosen parts and plants")
    if not jobs:
        raise ValueError("the selection plans no job")
    selection = {"part": list(parts), "plants": list(plants), "arms": list(arms),
                 "keys": None if keys is None else list(keys),
                 "jobs_file": None if args.jobs_file is None else str(args.jobs_file),
                 "jobs_file_sha256": file_sha256, "planned": len(jobs),
                 "plan_sha256": plan_sha256(jobs)}
    return jobs, selection


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="output jsonl (a new path)")
    parser.add_argument("--part", default="main", help=f"comma list of {list(PARTS)}")
    parser.add_argument("--jobs-file", type=Path, default=None,
                        help="rows of part 'file' (job list or {'lines': [{'job': ...}]})")
    parser.add_argument("--plants", default=None, help=f"comma list of {list(PLANTS)}")
    parser.add_argument("--arms", default=None,
                        help=f"comma list of {list(ARMS)} (default {','.join(DEFAULT_ARMS)})")
    parser.add_argument("--keys", default=None, help="comma list of row keys (key_name)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--mask", default=None, help="hex affinity mask, inherited by the workers")
    parser.add_argument("--resume", action="store_true",
                        help="append to an existing --out of the same plan")
    parser.add_argument("--list", action="store_true", help="print the planned jobs and stop")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        jobs, selection = _selection(args)
        if not args.list:
            _check_output(args.out.resolve(), selection, args.resume)
    except ValueError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}), flush=True)
        return EXIT_INPUT
    if args.list:
        for job in jobs:
            print(job["_part"], job["setting"], d0.key_name(job), flush=True)
        print(json.dumps({"status": "listed", "planned": len(jobs),
                          "plan_sha256": selection["plan_sha256"], "out": str(args.out)}))
        return EXIT_OK
    try:
        counts = run_batch(args, jobs, selection)
    except Exception:  # every unexpected failure is a tool error (exit 3), never a result
        traceback.print_exc()
        print(json.dumps({"status": "tool_error", "out": str(args.out)}), flush=True)
        return EXIT_TOOL
    status = "error_lines" if counts["error_lines"] else "ok"
    print(json.dumps({"status": status, **counts, "out": str(args.out)}), flush=True)
    return EXIT_ERROR_LINES if counts["error_lines"] else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
