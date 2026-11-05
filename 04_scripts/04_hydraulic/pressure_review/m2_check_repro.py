"""Check the stored ``m2_check.json`` law values with the copied ``m2_check.run_law``.

Only the Python law runs: the Hopsan and numpy columns of the stored file need Hopsan and long runs,
and they are inputs of the review, not of this check. ``poc_*.py`` and ``m1_m2_build.py`` in this
folder are kept as a record and are not run.

Usage (hydraulics-dev): python -I -B m2_check_repro.py
Exit code 0 = all stored law values reproduced within ``TOLERANCE_KN``.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402, F401  (sets sys.path for the project modules)
import four_leg as fl  # noqa: E402
import m2_check  # noqa: E402
import numpy as np  # noqa: E402
from common import OUT  # noqa: E402
from params import load_params  # noqa: E402

TOLERANCE_KN = 1.0e-6
LAST_SAMPLES = 200
"""``m2_check.main`` averages the end force over the last 200 samples."""
CLOSED_CASES = ("A_stop_all_eta95", "B_twist", "C2_release_ground", "C3_release_ground_r2")


def _difference(new: np.ndarray, stored: list[float]) -> float:
    return float(np.abs(np.asarray(new, float) - np.asarray(stored, float)).max())


def _closed_loop_errors(params, cases_by_name: dict, stored: dict) -> dict[str, float]:
    errors = {}
    for name in CLOSED_CASES:
        case = cases_by_name[name]
        grid, command, _ = fl.command_series(case, params)
        for tag, is_on in (("law", False), ("law_m2", True)):
            result = m2_check.run_law(case, params, grid, command, is_on)
            stats = fl.window_stats(result, case.t_event, case.t_end)
            for key in ("dF_max_kN", "dF_min_kN", "F_end_kN"):
                errors[f"{name}.{tag}.{key}"] = _difference(stats[key], stored[name][tag][key])
    return errors


def _fixed_body_errors(params, cases_by_name: dict, stored: dict) -> dict[str, float]:
    errors = {}
    pairs = (("C2_release_ground", "F_fixed_r35"), ("C3_release_ground_r2", "F_fixed_r2"))
    for case_name, stored_name in pairs:
        case = copy.copy(cases_by_name[case_name])
        case.body_fixed = True
        grid, command, _ = fl.command_series(case, params)
        for tag, is_on in (("law", False), ("law_m2", True)):
            result = m2_check.run_law(case, params, grid, command, is_on, True)
            end_force_kN = float(result["F"][-LAST_SAMPLES:, 0].mean()) / 1e3
            stored_kN = stored["F_end_kN"][stored_name][tag]
            errors[f"{stored_name}.{tag}"] = abs(end_force_kN - stored_kN)
    return errors


def main() -> None:
    params = load_params()
    fl.AH[:] = params.A_h
    fl.AR[:] = params.A_r
    cases_by_name = {case.name: case for case in fl.cases(params)}
    stored = json.loads((OUT / "m2_check.json").read_text(encoding="utf-8"))
    errors = _closed_loop_errors(params, cases_by_name, stored["closed"])
    errors |= _fixed_body_errors(params, cases_by_name, stored["fixed_body"])
    worst_key = max(errors, key=errors.get)
    print(json.dumps({"values": len(errors), "worst": worst_key, "worst_kN": errors[worst_key]}))
    sys.exit(0 if errors[worst_key] <= TOLERANCE_KN else 1)


if __name__ == "__main__":
    main()
