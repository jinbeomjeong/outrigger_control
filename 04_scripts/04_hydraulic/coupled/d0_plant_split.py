"""436.9 edition 5 j9_main failure (run 606f8713), D0 plant split: a record, not a judgement.

The eight j9_main VBJ failure keys run on seven plant variants (user decision 2026-11-23;
``06_analysis/02_control/j_p3_cause/ed5_j9fail_606f8713/j9fail_cause_analysis.md`` 4 and
``hydraulics/h1_p1_review_report.md`` 7). Each variant keeps the controller of its base setting:
VBJ variants run ③ revision 6 (tag ``final_C4G2_P3W_LAS_K1``), D0-3 the VB controller (③
revision 4, tag ``final_C4G2_P3_LAS_K1``).

=======  =================================================  ===========================
variant  plant                                              controller (base setting)
=======  =================================================  ===========================
D0-1     VBJ: P1 (VN, volume x1, c_v 0.02) + P2 + P3 + P4   VBJ
D0-2     VBJ without P1 (P2 .. P4 only)                     VBJ
D0-3     VB (old plant) + P1 nominal                        VB (test only, see below)
D0-4     VBJ, P1 volume_scale 0.5                           VBJ
D0-5     VBJ, P1 c_v 0.002                                  VBJ
D0-6     VBJ, P1 c_v 0.04                                   VBJ
D0-7     VBJ, P1 c_v 0.002 + volume_scale 0.5               VBJ
=======  =================================================  ===========================

The settings live in this script only (``jp3_case_replay`` precedent: not in ``run_v5.SETTINGS``,
so no pinned setting, tag or stored digest changes). D0-3 is P1 with the ③ bound of revision 4,
which ``v5_options`` refuses (counterexample ⑥: the revision 4 tracker has no line-fill gate);
:func:`install_d0_switches` (the parent and every worker, never at import) turns
``ALLOW_GATE_WITH_REV4_FOR_TEST`` on, as ``jp3_case_replay`` does for case C (``VBG4`` is the
same plant and controller). The ③ tracker of every variant
keeps its own nominal P1 values (``LineFillGateParams``); only the plant gate changes.

Every P1 run logs its line state at each controller read (``harness_hydraulics.P1ReadLog``,
T4h arrays ``p1_*``); record only, the commands do not change.

Output: one ``run_v5.run_one`` line per run in ``--out`` (appended, finished jobs skipped), a
``d0`` block per line (variant, the test-only switch, modules imported from another checkout),
T4h records in ``<out stem>_t4h/``, the run identity ``<out stem>.identity.json`` (start and
end) and the progress file ``<out stem>.progress.json`` (keys ``stage``, ``done``, ``total``,
``unit``, ``started_at``, ``updated_at``; no result values).

======  =============================================================
exit    meaning
======  =============================================================
0       every planned job has a line without error
1       some line has an error (the batch went on)
2       input error (unknown variant or key, bad mask)
3       tool error
======  =============================================================

Usage (dynamics-dev, checkout root):
  python -I -B 04_scripts/04_hydraulic/coupled/d0_plant_split.py --out <jsonl> [--workers N]
      [--mask HEX] [--variants D0-1,D0-2] [--keys R12_o0.0,S5_e0.0] [--list]
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

import run_v5  # noqa: E402  (puts the harness folders and 03_src on sys.path)

from outrigger_sim.hydraulics import v5_options  # noqa: E402

EXIT_OK, EXIT_ERROR_LINES, EXIT_INPUT, EXIT_TOOL = 0, 1, 2, 3
MAIN_CHECKOUT = Path(r"C:\workspace\outrigger_control")
"""The main checkout: a worktree run must import no project module from it."""
PROGRESS_UNIT = "run"


def _gate(volume_scale: float = 1.0, c_v: float = 0.02) -> dict:
    return {"kind": "VN", "volume_scale": volume_scale, "c_v": c_v}


def _without_gate(plant: dict) -> dict:
    return {key: value for key, value in plant.items() if key != "line_fill_gate"}


_VBJ_PLANT = run_v5.JP3_SETTINGS["VBJ"][1]
_VB_PLANT = run_v5.SETTINGS["VB"][1]
D0_SETTINGS: dict[str, tuple[bool, dict]] = {
    "D0-1": (True, dict(_VBJ_PLANT)),
    "D0-2": (True, _without_gate(_VBJ_PLANT)),
    "D0-3": (True, {**_VB_PLANT, "line_fill_gate": _gate()}),
    "D0-4": (True, {**_VBJ_PLANT, "line_fill_gate": _gate(volume_scale=0.5)}),
    "D0-5": (True, {**_VBJ_PLANT, "line_fill_gate": _gate(c_v=0.002)}),
    "D0-6": (True, {**_VBJ_PLANT, "line_fill_gate": _gate(c_v=0.04)}),
    "D0-7": (True, {**_VBJ_PLANT, "line_fill_gate": _gate(volume_scale=0.5, c_v=0.002)}),
}
"""(flow limit on, plant options) per variant (module docstring table)."""
D0_BASE_SETTING = {"D0-1": "VBJ", "D0-2": "VBJ", "D0-3": "VB", "D0-4": "VBJ", "D0-5": "VBJ",
                   "D0-6": "VBJ", "D0-7": "VBJ"}
"""The setting whose controller (and flow limit) each variant keeps."""
D0_KEY_JOBS: tuple[dict, ...] = (
    {"case": "R12", "eps": 0.0, "offset_s": 0.0},
    {"case": "R12", "eps": 0.0, "offset_s": 0.0,
     "twin": {"level": "top", "leg": "FL", "fs_kN": 8.0}},
    {"case": "R12", "eps": 0.0, "offset_s": 0.0,
     "twin": {"level": "bottom", "leg": "FL", "fs_kN": 4.0}},
    {"case": "R12", "eps": 0.0, "offset_s": 0.0,
     "twin": {"level": "top", "leg": "FR", "fs_kN": 4.0}},
    {"case": "R15", "eps": 0.0, "offset_s": 0.0},
    {"case": "R15", "eps": 0.0, "offset_s": 0.05},
    {"case": "S5", "eps": 0.0},
    {"case": "S1", "eps": 0.003},
)
"""The eight j9_main VBJ failure keys (cause analysis 4, D0 row): R12 o0.0, R12
top-FL-Fs8-o0.0, G4 bottom-FL-Fs4-o0.0, G4 top-FR-Fs4-o0.0, R15 o0.0 / o0.05, S5 eps 0,
S1 eps 0.003; each a job of the ``run_v5`` ``j9_main`` batch."""


def install_d0_switches() -> None:
    """The process-wide D0 switches (idempotent; the parent before reading ``--out``, every
    worker before its run): the D0 settings in ``run_v5`` (with their T4h record), the
    test-only P1 + ③ revision 4 permission for D0-3 and the per-read P1 record. Importing
    this module changes nothing (the unit tests import it)."""
    import harness_hydraulics  # after run_v5: it needs the harness folders on sys.path

    v5_options.ALLOW_GATE_WITH_REV4_FOR_TEST = True  # D0-3 only (VBG4 precedent, docstring)
    harness_hydraulics.enable_p1_read_record()
    run_v5.ALL_SETTINGS.update(D0_SETTINGS)
    missing = tuple(name for name in D0_SETTINGS if name not in run_v5.T4H_SETTINGS)
    run_v5.T4H_SETTINGS = (*run_v5.T4H_SETTINGS, *missing)


def key_name(job: dict) -> str:
    """The T4h stem of a key (``R12_top-FL-Fs8-o0.0``, ``S5_e0.0``), without the setting."""
    return run_v5.t4h_file_name({**job, "setting": "X"}).rsplit("_", 1)[0]


D0_KEYS: dict[str, dict] = {key_name(job): dict(job) for job in D0_KEY_JOBS}


def d0_jobs(variants: tuple[str, ...] = tuple(D0_SETTINGS),
            keys: tuple[str, ...] = tuple(D0_KEYS)) -> list[dict]:
    """Variant-major job list (56 jobs for the defaults)."""
    return [{**D0_KEYS[key], "setting": variant} for variant in variants for key in keys]


def modules_outside_checkout() -> list[str]:
    """Project modules imported from the main checkout while this file runs in another one."""
    root = run_v5.ROOT.resolve()
    foreign = []
    for module in list(sys.modules.values()):
        file_name = getattr(module, "__file__", None)
        if file_name is None:
            continue
        path = Path(file_name).resolve()
        if path.is_relative_to(MAIN_CHECKOUT) and not path.is_relative_to(root):
            foreign.append(str(path))
    return sorted(foreign)


def run_d0_job(job: dict) -> dict:
    """Worker: one ``run_v5.run_one`` line with the ``d0`` record block."""
    import harness_hydraulics

    install_d0_switches()
    record = run_v5.run_one(job)
    variant = job["setting"]
    record["d0"] = {"variant": variant, "base_setting": D0_BASE_SETTING[variant],
                    "allow_gate_with_rev4_for_test": v5_options.ALLOW_GATE_WITH_REV4_FOR_TEST,
                    "p1_read_record": harness_hydraulics.is_p1_read_record_on(),
                    "foreign_modules": modules_outside_checkout()}
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


def _names(text: str | None, known: dict, what: str) -> tuple[str, ...]:
    if text is None:
        return tuple(known)
    names = tuple(name for name in text.split(",") if name)
    unknown = sorted(set(names) - set(known))
    if not names or unknown:
        raise ValueError(f"--{what} takes {sorted(known)}, got {unknown or names}")
    return names


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="output jsonl (appended)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--mask", default=None, help="hex affinity mask, inherited by the workers")
    parser.add_argument("--variants", default=None, help=f"comma list of {list(D0_SETTINGS)}")
    parser.add_argument("--keys", default=None, help=f"comma list of {list(D0_KEYS)}")
    parser.add_argument("--list", action="store_true", help="print the jobs to do and stop")
    return parser


def _write_line(handle, record: dict) -> None:
    for key in run_v5.RUNTIME_JOB_KEYS:
        record["job"].pop(key, None)
    handle.write(json.dumps(record, default=lambda v: v.item() if hasattr(v, "item")
                            else str(v)) + "\n")
    handle.flush()


def run_batch(args: argparse.Namespace, jobs: list[dict]) -> dict:
    """Run the jobs not in ``args.out`` yet; the counts of the whole planned batch."""
    install_d0_switches()
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
        for count, record in enumerate(pool.imap_unordered(run_d0_job, todo), 1):
            _write_line(handle, record)
            progress.advance()
            error_lines += "error" in record
            state = record.get("error", "")[:200] or f"{record['wall_s']}s"
            print(f"{count}/{len(todo)} {record['job']['setting']} "
                  f"{key_name(record['job'])}: {state}", flush=True)
    progress.finish()
    run_v5._write_identity(out, "end")
    return {"planned": len(jobs), "run": len(todo), "skipped_done": len(jobs) - len(todo),
            "error_lines": error_lines}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        variants = _names(args.variants, D0_SETTINGS, "variants")
        keys = _names(args.keys, D0_KEYS, "keys")
        if args.mask is not None:
            int(args.mask, 16)
    except ValueError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}), flush=True)
        return EXIT_INPUT
    jobs = d0_jobs(variants, keys)
    if args.list:
        for job in jobs:
            print(job["setting"], key_name(job), flush=True)
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
