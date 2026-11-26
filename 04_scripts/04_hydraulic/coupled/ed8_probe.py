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
a8       the edition 8 VBN controller (spec v8 3.6: (i-b) off, R2 witness record, PSW,
         warning (0.8, 3.6), H3', L-2; ``run_v5.PROBE_D6_ED8`` and
         ``run_v5.ED8_CONTROLLER_CHANGES``)
a8_*_off a8 without one change: ``a8_psw_off`` (P8-5), ``a8_h3_off`` (P8-8), ``a8_l2_off``
         (P8-15)
B_impl   P8-16 review arm B: a2w + H3' (PSW off, warning 2.3)
L2_impl  P8-16 review arm L2: ``B_impl`` + L-2
a2w_psw  P8-6: a2w + PSW (direction A with the scale window)
=======  ==================================================================================

==========  ========================================================================
plant       plant options (``run_v5``)
==========  ========================================================================
M           ``ed7_plant()`` (= the VBM plant)
M<key>      ``ed7_plant(<key>)`` for the ten ``run_v5.ED7_SENSITIVITY`` keys (= VBM<key>)
LSM1..LSM4  ``ed7_plant()`` with the LSM<n> lock closure (= the LSM<n> plant)
L           ``ed6_plant()`` (= the VBL plant)
KM0         ``ed7_plant()`` with ③ off (= the VBKM0 plant): the r79 rows of part p816 with
            the rod fault plan ``--r79-plan``; not in the default ``--plants`` of the other
            parts
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
p816        the 27 P8-14 keys (spec v8 12 P8-16): :data:`P816_V5_ROWS` (23, run_v5 path)
            and :data:`P816_R79_KEYS` on KM0 (4, r79 path as ``p814_rerun.py``; needs
            ``--r79-plan`` with :data:`P816_R79_PLAN_SHA256`)
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
      [--part main,d,j9main,file,p816] [--jobs-file <json>] [--plants M,LSM4] [--arms a2,a2w]
      [--keys K1,K2] [--workers N] [--mask HEX] [--r79-plan <json>] [--resume] [--list]
P8-16 (spec v8 12): ``--part p816 --arms B_impl,L2_impl --r79-plan <P814 plan>``, then
``p816_compare.py`` against the P8-14 ``raw/runs.jsonl``.
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
H3_PRIME = {"short_run_exit_samples": 4, "short_run_s": 0.5}
"""Edition 8 H3' alone (spec v8 3.7, ``ed8_settings`` form)."""
ARMS: dict[str, tuple[str, ...]] = {
    **ed7_probe.ARMS, "a2w": ed7_probe.ARMS["a2"],
    **{arm: tuple(run_v5.LSB_COMPONENTS_ED7) for arm in (
        "a8", "a8_psw_off", "a8_h3_off", "a8_l2_off", "B_impl", "L2_impl", "a2w_psw")},
}
ARM_PARAMETERS: dict[str, dict] = dict(ed7_probe.ARM_PARAMETERS)
ARM_PROBE_D6: dict[str, dict | None] = {
    **{arm: dict(run_v5.PROBE_D6_ED7) for arm in ed7_probe.ARMS},
    **{arm: None for arm in ed7_probe.ARMS_WITHOUT_D6},
    "a2w": dict(PROBE_D6_WITNESS_ONLY),
    **{arm: dict(run_v5.PROBE_D6_ED8) for arm in ("a8", "a8_psw_off", "a8_h3_off",
                                                   "a8_l2_off")},
    "B_impl": dict(PROBE_D6_WITNESS_ONLY),
    "L2_impl": dict(PROBE_D6_WITNESS_ONLY),
    "a2w_psw": dict(PROBE_D6_WITNESS_ONLY),
}
"""``probe_d6_settings`` per arm (None = the D6 settings off)."""


def _ed8_without(*names: str) -> dict:
    return {key: value for key, value in run_v5.ED8_CONTROLLER_CHANGES.items()
            if key not in names}


ARM_ED8: dict[str, dict | None] = {
    "a8": dict(run_v5.ED8_CONTROLLER_CHANGES),
    "a8_psw_off": _ed8_without("psw_min_travel_m"),
    "a8_h3_off": _ed8_without(*H3_PRIME),
    "a8_l2_off": _ed8_without("locked_drift_waiver"),
    "B_impl": dict(H3_PRIME),
    "L2_impl": {**H3_PRIME, "locked_drift_waiver": True},
    "a2w_psw": {"psw_min_travel_m": run_v5.ED8_CONTROLLER_CHANGES["psw_min_travel_m"]},
}
"""``ed8_settings`` per arm (absent = off). ``a8`` = the VBN controller (spec v8 3.6; with
``probe_d6_settings`` R2); the ``a8_*_off`` arms take one change out (P8-5 PSW, P8-8 H3',
P8-15 L-2: "the rest of the edition 8 controller the same"); ``B_impl`` = a2w + H3' and
``L2_impl`` = ``B_impl`` + L-2 (P8-16: the review arms B and L2 of P8-14, warning 2.3, PSW
off); ``a2w_psw`` = a2w + PSW (P8-6: the first-round ``K1_sc`` of direction A)."""
DEFAULT_ARMS = ("a2", "a2w")
"""The two arms of the cause analysis 7 A experiment 2."""
LS_PLANTS = tuple(f"LSM{n}" for n in run_v5.LS_CLOSURES)
P3_OFF_PLANTS = ("KM0",)
"""Plants whose arms run with ③ off: ``KM0`` = the VBKM0 plant (rod fault plan, r79 path)."""
PLANTS: tuple[str, ...] = ("M", *(f"M{key}" for key in run_v5.ED7_SENSITIVITY), *LS_PLANTS,
                           "L", *P3_OFF_PLANTS)
SETTING_PLANT: dict[str, str] = {"VBM": "M",
                                 **{f"VBM{key}": f"M{key}" for key in run_v5.ED7_SENSITIVITY},
                                 **{name: name for name in LS_PLANTS}, "VBL": "L",
                                 "VBKM0": "KM0"}
"""Setting of a source row -> the probe plant with its plant options."""
PLANT_SETTING: dict[str, str] = {plant: setting for setting, plant in SETTING_PLANT.items()}
PARTS = ("main", "d", "j9main", "file", "p816")
D_PART_PLANTS = ed7_probe.D_PART_PLANTS
PROGRESS_UNIT = "run"


def _r12(level: str, leg: str, fs_kN: float, offset_s: float, event: str | None = None,
         timing: str | None = None) -> dict:
    twin: dict = {"level": level, "leg": leg, "fs_kN": fs_kN}
    if event is not None:
        twin.update(event=event, timing=timing)
    return {"case": "R12", "eps": 0.0, "offset_s": offset_s, "twin": twin}


P816_V5_ROWS: tuple[tuple[str, dict], ...] = (
    ("M", _r12("bottom", "FR", 4.0, 0.075, "RE1bF", "ready")),
    ("LSM4", _r12("top", "FR", 0.0, 0.05)),
    ("Mslow", _r12("top", "FL", 0.0, 0.0)),
    *(("M", _r12("bottom", leg, fs, 0.0, "RE1bF", "ready"))
      for leg, fs in (("FR", 0.0), ("FL", 4.0), ("FL", 2.0), ("FR", 2.0), ("FR", 4.0))),
    ("M", _r12("bottom", "FR", 8.0, 0.0, "FS24", "ready")),
    ("M", _r12("bottom", "FL", 2.0, 0.025, "RE1bF", "ready")),
    ("M", _r12("bottom", "FR", 2.0, 0.075, "RE1bF", "ready")),
    *(("M", {"case": "R15", "eps": 0.0, "offset_s": offset}) for offset in (0.0, 0.05)),
    *(("M", {"case": "R16", "eps": 0.0, "offset_s": offset})
      for offset in (0.0, 0.025, 0.05, 0.075)),
    ("M", {"case": "S7", "eps": 0.002}),
    ("M", _r12("top", "FR", 8.0, 0.0)),
    ("M", _r12("top", "FL", 8.0, 0.0, "RE1bF", "level")),
    ("M", {"case": "S4", "eps": 0.002}),
    ("M", {"case": "R2", "eps": 0.001}),
    ("M", {"case": "S8", "eps": 0.0}),
)
"""P8-16 (spec v8 12, the P8-14 keys): the 23 VBM-family rows of
``control_level_deadlock/probe_8a2a52ce/p814_rerun.py`` (the deadlock key, the two D-3 keys, the
17 other P8-9 keys and S4 e0.002, R2 e0.001, S8 e0.0) on their probe plants (VBM -> M, LSM4,
VBMslow -> Mslow)."""
P816_R79_KEYS = ("cand=current#L2|s40|g6|52|ref|J1|top|Fs0",
                 "cand=current#L2|s40|g6|56|ref|J2|top|Fs0",
                 "cand=current#L2|s40|g6|59|ref|J2|bottom|Fs4",
                 "cand=current#L2|s41|ref|16|J1|B|0,0")
"""P8-16: the four edition 5 VBK0 deadlock keys (spec v8 3.8), r79 path on the plant KM0."""
P816_R79_PLAN_SHA256 = "99e506534669f4779dd4f44c31b90836b4f5f23a955bae374c83afc82597a463"
"""The P8-14 r79 rod fault plan (``raw/plans/P814-{B,L1,L2}-VBKM0.json``; spec v8 header)."""
R79_ROD_MODEL = "plant_truth"
CHECKOUT_ROOT = HERE.parents[2]
R79_DIR = CHECKOUT_ROOT / "04_scripts" / "03_control" / "s8"


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
    if plant in P3_OFF_PLANTS:
        return run_v5.ed7_plant()
    return run_v5.ed7_plant(None if plant == "M" else plant[1:])


def arm_options(arm: str, *, has_p3: bool = True) -> dict:
    """The controller options of an arm (③ rev 7 unless ``has_p3`` is False, components,
    parameters, D6 settings, edition 8 settings)."""
    options = {**(run_v5._P3X if has_p3 else {}), "lsb_components": list(ARMS[arm])}
    if ARM_PARAMETERS.get(arm):
        options["lsb_parameters"] = dict(ARM_PARAMETERS[arm])
    if ARM_PROBE_D6[arm] is not None:
        options["probe_d6_settings"] = dict(ARM_PROBE_D6[arm])
    if ARM_ED8.get(arm):
        options["ed8_settings"] = dict(ARM_ED8[arm])
    return options


def probe_settings() -> dict[str, tuple[bool, dict]]:
    """Every edition 8 probe setting: (flow limit on, ``HydraulicOptions`` keys)."""
    return {setting_name(plant, arm): (True, {**plant_options(plant),
                                              **arm_options(arm,
                                                            has_p3=plant not in P3_OFF_PLANTS)})
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
    rod_fault = tuple(name for name in settings if split_setting_name(name)[0] in P3_OFF_PLANTS
                      and name not in run_v5.ROD_FAULT_SETTINGS)
    run_v5.ROD_FAULT_SETTINGS = (*run_v5.ROD_FAULT_SETTINGS, *rod_fault)


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
    if "p816" in parts:
        rows += [("p816", plant, dict(row)) for plant, row in P816_V5_ROWS if plant in plants]
        if "KM0" in plants:
            rows += [("p816", "KM0", {"r79_key": key}) for key in P816_R79_KEYS]
    return rows


def row_label(row: dict) -> str:
    """The row name of ``--keys`` and the console: the r79 key of an r79 row, else
    ``d0_plant_split.key_name``."""
    return row["r79_key"] if "r79_key" in row else d0.key_name(row)


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
        if keys is not None and row_label(row) not in keys:
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
    """Worker: one ``run_v5.run_one`` line (an r79 row: :func:`run_r79_row`) with the
    ``ed8_probe`` record block."""
    import harness_hydraulics
    import verdict_runs

    install_probe_switches()
    part = job.pop("_part")
    plan = job.pop("_r79_plan", None)
    if "r79_key" in job:
        record = run_r79_row(job, plan)
    else:
        record = run_v5.run_one(job)
    plant, arm = split_setting_name(job["setting"])
    record[RECORD_BLOCK] = {"plant": plant, "arm": arm, "part": part,
                            "source_setting": PLANT_SETTING[plant],
                            "components": list(ARMS[arm]),
                            "lsb_parameters": dict(ARM_PARAMETERS.get(arm, {})),
                            "probe_d6_settings": ARM_PROBE_D6[arm],
                            "ed8_settings": ARM_ED8.get(arm),
                            "p1_read_record": harness_hydraulics.is_p1_read_record_on(),
                            "ed8_record": verdict_runs.is_ed8_record_on(),
                            "foreign_modules": d0.modules_outside_checkout()}
    return record


def run_r79_row(job: dict, plan: str | None) -> dict:
    """One r79 row (P8-16 ``KM0`` keys) as P8-14 ran it (``p814_rerun.py`` worker): the r79
    adapter of this checkout with ``R79_V5_SETTING`` = the probe setting, the rod fault plan
    ``plan``, ``R79_ROD_MODEL`` :data:`R79_ROD_MODEL`, the T4h folder of the job and the
    project root as ``sys.argv[1]`` (``r51_reapp_closed_loop`` reads it at import). An r79
    failure is an error line (the batch goes on)."""
    import os
    import time

    t_start = time.perf_counter()
    setting, key = job["setting"], job["r79_key"]
    t4h_dir = Path(job["t4h_dir"]) / f"r79_{setting}"
    try:
        if plan is None:
            raise ValueError("an r79 row needs --r79-plan")
        t4h_dir.mkdir(parents=True, exist_ok=True)
        os.environ.update({"R79_V5_SETTING": setting, "R79_ROD_MODEL": R79_ROD_MODEL,
                           "R79_T4H_DIR": str(t4h_dir), "R79_ROD_FAULT_PLAN": str(plan)})
        if str(R79_DIR) not in sys.path:
            sys.path.insert(0, str(R79_DIR))
        sys.argv = [sys.argv[0], str(CHECKOUT_ROOT)]
        if job.get("mask") is not None:  # as run_v5.run_one does for its jobs
            import s9_soil_slope as slope

            slope.set_parent_affinity(int(job["mask"]))
        import r79_L3L4_final as final

        record = final.run_one(key)
    except Exception as exc:  # the batch goes on; the line records the failure
        record = {"error": repr(exc), "tb": traceback.format_exc()[-3000:],
                  "wall_s": round(time.perf_counter() - t_start, 1)}
    record["job"] = dict(job)
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
        if "r79_key" in job:
            job["_r79_plan"] = str(Path(args.r79_plan).resolve())
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
                  f"{row_label(record['job'])}: {state}", flush=True)
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
    default_plants = PLANTS if "p816" in parts else tuple(
        plant for plant in PLANTS if plant not in P3_OFF_PLANTS)
    plants = (default_plants if args.plants is None
              else d0._names(args.plants, dict.fromkeys(PLANTS), "plants"))
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
        found = {row_label(job) for job in jobs}
        missing = sorted(set(keys) - found)
        if missing:
            raise ValueError(f"--keys {missing}: no row of the chosen parts and plants")
    if not jobs:
        raise ValueError("the selection plans no job")
    plan_sha = _checked_r79_plan(args.r79_plan, any("r79_key" in job for job in jobs))
    selection = {"part": list(parts), "plants": list(plants), "arms": list(arms),
                 "keys": None if keys is None else list(keys),
                 "jobs_file": None if args.jobs_file is None else str(args.jobs_file),
                 "jobs_file_sha256": file_sha256, "planned": len(jobs),
                 "plan_sha256": plan_sha256(jobs),
                 "r79_plan": None if args.r79_plan is None else str(args.r79_plan),
                 "r79_plan_sha256": plan_sha}
    return jobs, selection


def _checked_r79_plan(path: Path | None, has_r79_rows: bool) -> str | None:
    """The sha256 of ``--r79-plan`` (None without r79 rows).

    Raises:
        ValueError: r79 rows without a plan, an unreadable plan, or a plan whose sha256 is not
            :data:`P816_R79_PLAN_SHA256` (P8-16: the P8-14 plan bytes).
    """
    if not has_r79_rows:
        return None
    if path is None:
        raise ValueError("the r79 rows (part p816, plant KM0) need --r79-plan")
    try:
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError(f"--r79-plan {path}: {exc}") from exc
    if digest != P816_R79_PLAN_SHA256:
        raise ValueError(f"--r79-plan {path}: sha256 {digest} is not the P8-14 plan "
                         f"{P816_R79_PLAN_SHA256}")
    return digest


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
    parser.add_argument("--r79-plan", type=Path, default=None,
                        help="rod fault plan of the r79 rows (part p816, plant KM0; sha256 "
                             "checked)")
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
            print(job["_part"], job["setting"], row_label(job), flush=True)
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
