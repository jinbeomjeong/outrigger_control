"""Runner of the coupling-verdict table (criteria 8.4 bundles A .. E plus the pair base OFF).

Bundle ``CL`` (not part of the default) repeats cases with the leg command clipped to v_max:
``CL_OFF_<case>``, ``CL_<case>_eta0.85``, ``CL_<case>_eta0.90`` in ``verdict/clip``.

Resumable: a run with a result file of the same definition is skipped. Every run leaves
``<run id>.json`` and ``<run id>.npz`` (10 Hz commands, attitude filter, integrals) in ``--out``,
a failure ``<run id>.error.json`` (run again on resume), and one line in ``progress.log``. Each
run has its own worker process, which isolates the harness' module patches and a crash. The
harness does not pin itself: the workers inherit ``--affinity``.

Usage (project root, dynamics-dev):
  <python> -I -B 04_scripts/04_hydraulic/coupled/run_verdict.py --bundles OFF,A,B,C,D,E --workers 28
      [--cases R1,S1] [--affinity 0xMASK] [--decide S6=alias_s5] [--out DIR] [--list]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from dataclasses import asdict
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
# named here, not left to the import order: ``-I`` puts neither folder on the path
for _path in (HERE, S9_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402
from params import load_params  # noqa: E402
from verdict_cases import (  # noqa: E402
    ALL_CASE_IDS,
    CASES,
    CLIP_BUNDLE,
    DECISION_OPTIONS,
    STATUS_DECISION,
    VerdictRun,
    build_clip_runs,
    build_runs,
    resolve_case,
)

DEFAULT_OUT = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "verdict"
CLIP_OUT = DEFAULT_OUT / "clip"
PROGRESS_LOG = "progress.log"
DEFINITION_VERSION = 2
ALIAS_OF_S5 = "alias_s5"
"""``--decide S6=alias_s5``: S6 takes the S5 result of the same bundle, nothing is run."""


def definition_digest(run: VerdictRun, decision: str | None) -> str:
    """Changes when the run's definition changes, so a stale result is not reused."""
    definition = {"version": DEFINITION_VERSION, "run_id": run.run_id, "case": run.case_id,
                  "setting": asdict(run.setting), "decision": decision}
    if run.clip_command:  # only here: an unclipped run keeps the digest stored in its result
        definition["clip_v_max_m_s"] = load_params().v_max
    if run.hydraulics is not None:  # v5 options: same rule, the stored digests stay valid
        definition["hydraulics"] = run.hydraulics.to_dict()
    return hashlib.sha256(json.dumps(definition, sort_keys=True).encode("utf-8")).hexdigest()


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    return str(value)


def write_json_atomic(path: Path, payload: dict) -> None:
    """A result file exists only when complete, whatever stops the process."""
    temporary = path.with_suffix(f"{path.suffix}.tmp{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=1, default=_json_default), encoding="utf-8")
    os.replace(temporary, path)


def is_complete(out_dir: Path, run: VerdictRun, decision: str | None) -> bool:
    path = out_dir / f"{run.run_id}.json"
    if not path.is_file():
        return False
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return stored.get("definition_sha256") == definition_digest(run, decision)


def todo_runs(runs: list[VerdictRun], out_dir: Path, decisions: dict) -> list[VerdictRun]:
    """Runs without a result of the same definition (the decision is part of it)."""
    return [run for run in runs if not is_complete(out_dir, run, decisions.get(run.case_id))]


def _run_one(job: tuple[VerdictRun, str | None, dict, str]) -> dict:
    """Worker entry: runs one table row and writes its files."""
    run, decision, decisions, out_text = job
    out_dir = Path(out_text)
    t_start = time.perf_counter()
    header = {"run_id": run.run_id, "bundle": run.bundle, "case_id": run.case_id,
              "chrono_name": CASES[run.case_id].chrono_name, "setting": asdict(run.setting),
              "decision": decision, "clip_command": run.clip_command,
              "definition_sha256": definition_digest(run, decision)}
    try:
        import verdict_runs

        result, series = verdict_runs.execute(resolve_case(run.case_id, decisions), run.setting,
                                              decision, clip_command=run.clip_command,
                                              hydraulics=run.hydraulics)
        if "error" in result:
            raise RuntimeError(f"{result['error']}\n{result.get('tb')}")
    except Exception as exc:  # the batch goes on; resume runs this row again
        write_json_atomic(out_dir / f"{run.run_id}.error.json",
                          {**header, "error": repr(exc), "trace": traceback.format_exc()})
        return {"run_id": run.run_id, "status": "error", "wall_s": time.perf_counter() - t_start,
                "error": repr(exc)}
    wall_s = round(time.perf_counter() - t_start, 1)
    np.savez_compressed(out_dir / f"{run.run_id}.npz", **series)
    write_json_atomic(out_dir / f"{run.run_id}.json", {**header, "wall_s": wall_s, **result})
    (out_dir / f"{run.run_id}.error.json").unlink(missing_ok=True)
    return {"run_id": run.run_id, "status": "done", "wall_s": wall_s}


def selected_runs(bundles: list[str], cases: list[str]) -> list[VerdictRun]:
    return [run for run in (*build_runs(), *build_clip_runs())
            if run.bundle in bundles and (not cases or run.case_id in cases)]


def default_out_dir(bundles: list[str]) -> Path:
    """The clipped runs keep to their own folder: their pair base is not the stored OFF."""
    return CLIP_OUT if bundles == [CLIP_BUNDLE] else DEFAULT_OUT


def split_runs(runs: list[VerdictRun], decisions: dict) -> tuple[list, list, list]:
    """(runnable, pending a decision, aliased to S5)."""
    runnable, pending, aliased = [], [], []
    for run in runs:
        if resolve_case(run.case_id, decisions) is None:
            pending.append(run)
        elif decisions.get(run.case_id) == ALIAS_OF_S5:
            aliased.append(run)
        else:
            runnable.append(run)
    return runnable, pending, aliased


def _log_line(out_dir: Path, text: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {text}"
    print(line, flush=True)
    with open(out_dir / PROGRESS_LOG, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def parse_decisions(items: list[str]) -> dict[str, str]:
    decisions = {}
    for item in items:
        case_id, _, choice = item.partition("=")
        if choice not in DECISION_OPTIONS.get(case_id, ()):
            raise ValueError(f"--decide {item!r}: choices {DECISION_OPTIONS}")
        decisions[case_id] = choice
    return decisions


def _set_affinity(mask_text: str | None) -> dict | None:
    """Pin this process, the spawned workers inherit it; returns the masks read back.

    Raises:
        RuntimeError: the mask did not apply.
    """
    if mask_text is None:
        return None
    import s9_soil_slope as slope

    return slope.set_parent_affinity(slope.parse_affinity(mask_text))


def _print_table(runs, pending, aliased, out_dir: Path, decisions: dict) -> None:
    for run in runs:
        state = "done" if is_complete(out_dir, run, decisions.get(run.case_id)) else "todo"
        print(run.run_id, run.bundle, CASES[run.case_id].twin_status,
              decisions.get(run.case_id, "-"), state)
    print(f"runnable {len(runs)} pending {[r.run_id for r in pending]} "
          f"aliased {[r.run_id for r in aliased]}")
    unresolved = [c for c in ALL_CASE_IDS if CASES[c].twin_status == STATUS_DECISION
                  and c not in decisions]
    print("cases waiting for --decide:", unresolved)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundles", default="OFF,A,B,C,D,E")
    parser.add_argument("--cases", default="", help="comma list of case ids (default all)")
    parser.add_argument("--workers", type=int, required=True)
    parser.add_argument("--affinity", default=None, help="hex mask, inherited by the workers")
    parser.add_argument("--decide", action="append", default=[], help="case=option")
    parser.add_argument("--out", type=Path, default=None,
                        help=f"default {DEFAULT_OUT}, for --bundles {CLIP_BUNDLE} {CLIP_OUT}")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    decisions = parse_decisions(args.decide)
    cases = [c for c in args.cases.split(",") if c]
    bundles = args.bundles.split(",")
    out_dir = args.out or default_out_dir(bundles)
    runs = selected_runs(bundles, cases)
    runnable, pending, aliased = split_runs(runs, decisions)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.list:
        _print_table(runnable, pending, aliased, out_dir, decisions)
        return
    todo = todo_runs(runnable, out_dir, decisions)
    _log_line(out_dir, f"start bundles={args.bundles} todo={len(todo)} of {len(runnable)} "
                       f"pending={[r.run_id for r in pending]} workers={args.workers}")
    if not todo:
        return
    placement = _set_affinity(args.affinity)
    if placement is not None:
        _log_line(out_dir, f"affinity {placement}")
    import verdict_runs

    verdict_runs.warm_numba_cache()
    jobs = [(run, decisions.get(run.case_id), decisions, str(out_dir)) for run in todo]
    n_failed = 0
    with Pool(max(1, min(args.workers, len(jobs))), maxtasksperchild=1) as pool:
        for finished, outcome in enumerate(pool.imap_unordered(_run_one, jobs, chunksize=1), 1):
            n_failed += outcome["status"] != "done"
            _log_line(out_dir, f"{finished}/{len(jobs)} {outcome['run_id']} {outcome['status']} "
                               f"wall {outcome['wall_s']:.1f} s {outcome.get('error', '')}")
    _log_line(out_dir, f"end failed={n_failed}")
    if n_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
