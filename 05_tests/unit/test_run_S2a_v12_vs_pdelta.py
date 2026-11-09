"""``run_S2a.v12_vs_pdelta`` on synthetic inputs: stale-weight guard and rev. 13 comparison.

The pdelta check file and the stored case results are synthetic; the references are the
project ``reference.json`` (the rev. 13 P-delta prediction and the V12 vertical reactions).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify.reference import (
    SLOPE_V12_L1,
    SLOPE_V12_L1_PLAN_A_EXPECTED_DIFF_REV13,
    load_references,
)

ROOT = Path(__file__).resolve().parents[2]
RUN_PARAMS_SHA = "61078f29"
CHRONO_OFFSET_N = np.array([0.4, -0.3, 0.2, -0.1])
"""Chrono - reference - prediction of the synthetic runs (N per leg)."""
CHECK_RUN_DIFF_N = np.array([67.4, 50.9, -51.8, -66.9])
"""Chrono - reference vertical of the run the synthetic pdelta file read (N per leg)."""


def _script():
    path = ROOT / "04_scripts" / "02_chrono" / "run_S2a.py"
    spec = importlib.util.spec_from_file_location("run_S2a_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_S2a_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def run_s2a():
    return _script()


@pytest.fixture(scope="module")
def refs():
    return load_references()


def _current_weight_N(refs, case: str) -> float:
    return float(np.sum(refs.get(SLOPE_V12_L1, case=case)["contact_vertical_N"]))


def _prediction_N(refs, case: str) -> np.ndarray:
    block = refs.get(SLOPE_V12_L1_PLAN_A_EXPECTED_DIFF_REV13, case=case)
    return np.asarray(block["P_delta_nonlinear_minus_linear_vertical_N"], dtype=float)


def _results(run_s2a, refs) -> dict:
    """Stored-result stand-ins: Chrono vertical = reference + prediction + CHRONO_OFFSET_N."""
    results = {}
    for name, case in run_s2a.V12_CASES.items():
        reference = np.zeros((4, 3))
        reference[:, 2] = refs.get(SLOPE_V12_L1, case=case)["contact_vertical_N"]
        chrono = reference.copy()
        chrono[:, 2] += _prediction_N(refs, case) + CHRONO_OFFSET_N
        results[name] = {
            "window": {"reaction_world_mean_N": chrono.tolist()},
            "reference": {"reaction_world_N": reference.tolist()},
            "ground_bushing": {"force_point": "ball_centre"},
        }
    return results


def _write_check(
    path: Path,
    run_s2a,
    refs,
    *,
    weight_offset_N: float = 0.0,
    force_point: str = "ball_centre",
    chrono_sha: str | None = RUN_PARAMS_SHA,
) -> Path:
    check: dict = {"meta": {"chrono_ground_bushing_force_point": [force_point]}}
    for name, case in run_s2a.V12_CASES.items():
        check[name] = {
            "W_N": _current_weight_N(refs, case) + weight_offset_N,
            "chrono_minus_reference_vertical_N": CHECK_RUN_DIFF_N.tolist(),
            "contact_minus_ball_nonlinear_vertical_N": [80.7, 83.6, -83.1, -81.2],
            "chrono_params_sha256": chrono_sha,
        }
    path.write_text(json.dumps(check), encoding="utf-8")
    return path


def _shas(run_s2a) -> dict[str, str]:
    return {name: RUN_PARAMS_SHA for name in run_s2a.V12_CASES}


def test_missing_pdelta_file_gives_none(run_s2a, refs, tmp_path) -> None:
    out = run_s2a.v12_vs_pdelta(
        _results(run_s2a, refs), refs, _shas(run_s2a), check_path=tmp_path / "absent.json"
    )
    assert out is None


def test_stale_weight_writes_only_the_stale_status(run_s2a, refs, tmp_path) -> None:
    check = _write_check(tmp_path / "pdelta.json", run_s2a, refs, weight_offset_N=2177.0)
    out = run_s2a.v12_vs_pdelta(_results(run_s2a, refs), refs, _shas(run_s2a), check_path=check)
    first_case = next(iter(run_s2a.V12_CASES.values()))
    w_current = _current_weight_N(refs, first_case)
    assert set(out) == {"status", "W_N_source", "W_N_current"}
    assert out["status"] == "stale_source"
    assert out["W_N_current"] == pytest.approx(w_current)
    assert out["W_N_source"] == pytest.approx(w_current + 2177.0)


def test_weight_just_above_tolerance_is_stale(run_s2a, refs, tmp_path) -> None:
    check = _write_check(tmp_path / "pdelta.json", run_s2a, refs, weight_offset_N=-1.01)
    out = run_s2a.v12_vs_pdelta(_results(run_s2a, refs), refs, _shas(run_s2a), check_path=check)
    assert out["status"] == "stale_source"


def test_current_weight_compares_with_the_rev13_prediction(run_s2a, refs, tmp_path) -> None:
    check = _write_check(tmp_path / "pdelta.json", run_s2a, refs, weight_offset_N=0.5)
    out = run_s2a.v12_vs_pdelta(_results(run_s2a, refs), refs, _shas(run_s2a), check_path=check)
    assert out["status"] == "complete"
    assert out["prediction_key"].endswith(
        "L1_plan_A_expected_chrono_minus_reference_rev13 / "
        "P_delta_nonlinear_minus_linear_vertical_N"
    )
    for name, case in run_s2a.V12_CASES.items():
        entry = out[name]
        np.testing.assert_allclose(entry["prediction_pdelta_rev13_N"], _prediction_N(refs, case))
        np.testing.assert_allclose(entry["chrono_minus_prediction_N"], CHRONO_OFFSET_N, atol=1e-9)
        np.testing.assert_allclose(
            entry["pdelta_check_run_chrono_minus_reference_N"], CHECK_RUN_DIFF_N
        )
        assert "before_contact_point_chrono_minus_reference_N" not in entry
        assert "prediction_ball_centre_N" not in entry
        # the pdelta file read a ball-centre run: no sphere lever removed to derive
        assert "sphere_lever_removed_N" not in entry


def test_pitch2_rev13_prediction_values(run_s2a, refs, tmp_path) -> None:
    check = _write_check(tmp_path / "pdelta.json", run_s2a, refs)
    out = run_s2a.v12_vs_pdelta(_results(run_s2a, refs), refs, _shas(run_s2a), check_path=check)
    np.testing.assert_allclose(
        out["v12_pitch2"]["prediction_pdelta_rev13_N"], [32.28, 14.01, -16.89, -29.41], atol=0.01
    )


def test_sphere_lever_removed_needs_a_contact_run_of_the_same_params(
    run_s2a, refs, tmp_path
) -> None:
    results = _results(run_s2a, refs)
    same = _write_check(tmp_path / "same.json", run_s2a, refs, force_point="contact_point")
    out = run_s2a.v12_vs_pdelta(results, refs, _shas(run_s2a), check_path=same)
    for name, case in run_s2a.V12_CASES.items():
        chrono_minus_reference = _prediction_N(refs, case) + CHRONO_OFFSET_N
        np.testing.assert_allclose(
            out[name]["sphere_lever_removed_N"],
            CHECK_RUN_DIFF_N - chrono_minus_reference,
            atol=1e-9,
        )

    other = _write_check(
        tmp_path / "other.json", run_s2a, refs, force_point="contact_point", chrono_sha="0ld"
    )
    out = run_s2a.v12_vs_pdelta(results, refs, _shas(run_s2a), check_path=other)
    assert all("sphere_lever_removed_N" not in out[name] for name in run_s2a.V12_CASES)

    unknown = _write_check(
        tmp_path / "unknown.json", run_s2a, refs, force_point="contact_point", chrono_sha=None
    )
    out = run_s2a.v12_vs_pdelta(results, refs, _shas(run_s2a), check_path=unknown)
    assert all("sphere_lever_removed_N" not in out[name] for name in run_s2a.V12_CASES)
