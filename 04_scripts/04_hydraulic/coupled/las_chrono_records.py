"""T4h-like records of stored Chrono L2b runs for the LAS-b shadow judge (J-6, J_P runs).

``las_judgement.md`` 8.4 / J-6: the J_P Chrono runs (``07_results/S8/v5jp_*``) store per
control update ``r8_series.npz`` (``t``, ``phase`` after the update, ``F_lower_est_N``,
``issued_u``) and ``controller_events.json``. ``F_lower_est_N`` is
``C2Controller._load_estimate_N(last_forces.lower)`` taken after the update (``run_S8C.py``
``S8Series``), i.e. the same quantity ``verdict_runs.LoggedController`` logs as
``lower_estimate_N`` for the harness T4h records (las_shadow confirmation 1: the seal bands
after a LEVEL update equal those at the LAS-b point). This module writes one npz per run with
``t_s``, ``phase``, ``lower_estimate_N``, ``command_m_s`` and ``meta_json`` (events,
``F_min_N``, ``soil_enable``, ``period_s``, source paths), which ``las_shadow.py judge --t4h``
reads in its ``stored`` mode (``W_ref`` from the YAML).

A run without ``F_lower_est_N`` (S9 ``r8_series``: no L-hat, no band) is reported as
``not_convertible``; those need the closed-loop replay of J-5 (not here).

Usage (dynamics-dev python, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/las_chrono_records.py <run dir> ... --out-dir DIR
Exit codes: 0 all converted / 1 some not convertible / 2 input error. Last stdout line: JSON.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT / "03_src") not in sys.path:
    sys.path.insert(0, str(ROOT / "03_src"))

EVENT_PATTERN = re.compile(r"C2Event\(t_s=([-0-9.eE+]+), name='(.*)'\)")
SERIES_NAME = "r8_series.npz"
EVENTS_NAME = "controller_events.json"
RESULT_NAME = "result.json"


def parse_events(lines: list[str]) -> list[tuple[float, str]]:
    """``controller_events.json`` entries (``repr`` of ``C2Event``) as ``(t_s, name)``.

    Raises:
        ValueError: An entry that is not a ``C2Event`` repr.
    """
    events = []
    for line in lines:
        match = EVENT_PATTERN.fullmatch(str(line).strip())
        if match is None:
            raise ValueError(f"not a C2Event entry: {line!r}")
        events.append((float(match.group(1)), match.group(2)))
    return events


def _f_min_N(controller_meta: dict) -> float:
    geometry = controller_meta.get("geometry") or {}
    if geometry.get("F_min_N") is not None:
        return float(geometry["F_min_N"])
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.params import load_params

    return float(C2Geometry.from_params(load_params()).F_min_N)


def find_run_dirs(paths: list[Path]) -> list[Path]:
    """Folders holding ``r8_series.npz`` under the given paths (a run folder itself or a batch)."""
    found = []
    for path in paths:
        if (path / SERIES_NAME).exists():
            found.append(path)
        else:
            found += sorted(series.parent for series in path.rglob(SERIES_NAME))
    return found


def convert_run(run_dir: Path, out_dir: Path) -> dict:
    """One run -> ``<out_dir>/<batch>__<case>.npz``; the status line of the run."""
    status = {"run": str(run_dir)}
    with np.load(run_dir / SERIES_NAME, allow_pickle=False) as series:
        if "F_lower_est_N" not in series.files:
            return {**status, "status": "not_convertible", "why": "no F_lower_est_N"}
        arrays = {"t_s": np.asarray(series["t"], float),
                  "phase": np.asarray(series["phase"]).astype(str),
                  "lower_estimate_N": np.asarray(series["F_lower_est_N"], float).reshape(-1, 4),
                  "command_m_s": np.asarray(series["issued_u"], float).reshape(-1, 4)}
    events = parse_events(json.loads((run_dir / EVENTS_NAME).read_text(encoding="utf-8")))
    result = json.loads((run_dir / RESULT_NAME).read_text(encoding="utf-8"))
    controller_meta = result.get("controller_meta") or {}
    soil = (controller_meta.get("soil") or {}).get("settings") or {}
    meta = {"events": events, "F_min_N": _f_min_N(controller_meta),
            "soil_enable": soil.get("enable"), "period_s": controller_meta.get("period_s"),
            "job": {"chrono_run": f"{run_dir.parent.name}/{run_dir.name}"},
            "lower_estimate_rule": "run_S8C S8Series F_lower_est_N (after each update)",
            "source_files": [SERIES_NAME, EVENTS_NAME, RESULT_NAME]}
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run_dir.parent.name}__{run_dir.name}.npz"
    np.savez_compressed(path, meta_json=np.array(json.dumps(meta)), **arrays)
    return {**status, "status": "converted", "npz": path.name, "rows": int(arrays["t_s"].size)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs", type=Path, nargs="+", help="run folders or batch folders")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        run_dirs = find_run_dirs(args.runs)
        if not run_dirs:
            raise ValueError(f"no {SERIES_NAME} under {[str(p) for p in args.runs]}")
        rows = [convert_run(run_dir, args.out_dir) for run_dir in run_dirs]
    except (OSError, KeyError, ValueError) as exc:
        print(f"input error: {exc!r}")
        return 2
    for row in rows:
        print(json.dumps(row))
    failed = sum(row["status"] != "converted" for row in rows)
    print(json.dumps({"runs": len(rows), "converted": len(rows) - failed,
                      "not_convertible": failed, "out_dir": str(args.out_dir)}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
