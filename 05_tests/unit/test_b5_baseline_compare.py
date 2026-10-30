"""B5 baseline comparison (``04_scripts/03_control/s9/b5_baseline_compare.py``): the C2 command
hash against the R2DS acceptance records, the IND wrapper (output delay d = 1, increment limit
0.25 v_max per period) and the rigid-floor-only floor-drop event.

The hash checks run the reduced harness in a subprocess (numba, dynamics-dev; about 30 s each).
``A1-rigid`` runs by default; the soil cases are marked ``slow``:
``python.exe -I -m pytest 05_tests/unit/test_b5_baseline_compare.py -m slow``.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control import c8
from outrigger_sim.params import load_params
from outrigger_sim.signals import Measurements

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "04_scripts" / "03_control" / "s9" / "b5_baseline_compare.py"
sys.path.insert(0, str(SCRIPT.parent))

import b5_baseline_compare as b5  # noqa: E402

GRAVITY_M_S2 = 9.80665
SCRIPT_TIMEOUT_S = 600
R2DS_C2_HASHES = {
    # rev83/R2DS_slope.json, candidate "current"
    "A1-rigid": "a91e95796d41e1a06dd5513b1a191bbd0b5bb12e5cfa50e9df8feafebb27820f",
    "A1-J1": "58f77b7b7420e275c99bbf2abca49f7d4d3f72efc448a948ff468ca7b2d033d0",
    # rev83/R2DS_g6.json, g6|G1+J1@RR|top|Fs4, candidate "current"
    "A3-G1+J1@RR": "69288ee341a21bb170add6bdcd63e6106f2014316d3fa976b1a7362eb2cfd551",
}


# ------------------------------------------------------------------------------ C2 hashes
def _run_b5(case_id: str, out_path: Path) -> dict:
    environment = dict(os.environ, MKL_THREADING_LAYER="TBB", PYTHONDONTWRITEBYTECODE="1")
    completed = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "run", "--cases", case_id, "--controllers", "C2",
         "--workers", "1", "--out", str(out_path)],
        cwd=ROOT, env=environment, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=SCRIPT_TIMEOUT_S, check=False)
    assert completed.returncode == 0, completed.stderr[-3000:]
    (record,) = json.loads(out_path.read_text(encoding="utf-8"))["records"]
    return record


@pytest.mark.parametrize("case_id", [
    "A1-rigid",
    pytest.param("A1-J1", marks=pytest.mark.slow),
    pytest.param("A3-G1+J1@RR", marks=pytest.mark.slow),
])
def test_c2_command_hash_matches_r2ds(case_id: str, tmp_path: Path) -> None:
    pytest.importorskip("numba", reason="the reduced plant kernel needs numba (dynamics-dev)")
    record = _run_b5(case_id, tmp_path / "b5.json")
    assert "error" not in record, record.get("tb")
    assert record["commands_sha256"] == R2DS_C2_HASHES[case_id]


# -------------------------------------------------------------------------------- IND wrapper
def _untouched_measurements(t_s: float, geometry) -> Measurements:
    """Level body, retracted legs, no load: C8 stays in TOUCH and asks v_max on every leg."""
    strokes = geometry.pad_bottom_z_retracted_m - geometry.crawler_bottom_z_m
    level = np.array([0.0, 0.0, GRAVITY_M_S2])
    return Measurements(
        t_s=t_s, specific_force_m_s2=level, angular_rate_rad_s=np.zeros(3),
        head_pressure_Pa=np.zeros(4), stroke_m=strokes, stroke_corrected_m=strokes,
        imu_specific_force_samples_m_s2=np.tile(level, (10, 1)))


def test_industry_output_is_one_period_late_and_increment_limited() -> None:
    params = load_params()
    industry = b5.IndustryC8.from_params(params)
    plain = c8.C8Controller.from_params(params, industry.settings)
    v_max = industry.geometry.max_speed_m_s
    period_s = industry.period_s
    assert period_s == pytest.approx(0.1)

    delayed, undelayed = [], []
    for k in range(8):
        measurements = _untouched_measurements(period_s * (k + 1), industry.geometry)
        delayed.append(np.asarray(industry.update(measurements).leg_speed_m_s))
        undelayed.append(np.asarray(plain.update(measurements).leg_speed_m_s))

    np.testing.assert_array_equal(delayed[0], np.zeros(4))
    for k in range(1, 8):
        np.testing.assert_allclose(delayed[k], undelayed[k - 1], rtol=0, atol=1e-15)
    steps = np.diff(np.vstack([np.zeros(4), *delayed]), axis=0)
    assert np.max(np.abs(steps)) <= 0.25 * v_max * (1 + 1e-12)
    np.testing.assert_allclose(delayed[1], np.full(4, 0.25 * v_max))
    np.testing.assert_allclose(delayed[5], np.full(4, v_max))


def test_industry_reset_clears_the_delayed_command() -> None:
    industry = b5.IndustryC8.from_params(load_params())
    for k in range(3):
        industry.update(_untouched_measurements(0.1 * (k + 1), industry.geometry))
    industry.reset()
    command = industry.update(_untouched_measurements(0.4, industry.geometry))
    np.testing.assert_array_equal(command.leg_speed_m_s, np.zeros(4))


def test_harness_wrapper_maps_the_phase_and_records_changes() -> None:
    wrapper = b5.HarnessIndustry(b5.IndustryC8.from_params(load_params()))
    assert wrapper.phase is b5.C2Phase.TOUCH
    wrapper.inner.phase = c8.C8Phase.LIFT
    wrapper.update(_untouched_measurements(0.1, wrapper.geometry))
    assert wrapper.phase is b5.C2Phase.LEVEL
    assert [event.name for event in wrapper.events] == ["ind_phase:lift"]
    assert math.isclose(wrapper.events[0].t_s, 0.1)


# ------------------------------------------------------------------------------- floor drop
def test_every_table_case_is_valid() -> None:
    for case_id in b5.CASES:
        b5.case_spec(case_id)


def test_every_table_case_has_a_display_name() -> None:
    assert set(b5.CASE_DISPLAY_NAMES) == set(b5.CASES)
    names = list(b5.CASE_DISPLAY_NAMES.values())
    assert all(name.strip() for name in names)
    assert len(set(names)) == len(names), "two cases share a display name"


def test_floor_drop_event_is_accepted_on_the_rigid_floor() -> None:
    spec = b5.case_spec("A4-G4RR-Fs8")
    assert spec["event"][0] == "RR"


@pytest.mark.parametrize("spec", [
    {"harness": "slope", "src": "H1|J1|B|top|flat", "event": ("RR", 0.0115, 2.0, 2.0)},
    {"harness": "g6", "src": "g6|G1+J1@RR|top|Fs4", "event": ("RR", 0.0115, 2.0, 2.0)},
    {"harness": "g6", "src": "g6r|rigid+J1@FL|top|Fs4", "event": ("FL", 0.01, 1.0, 1.0)},
])
def test_floor_drop_event_on_a_soil_case_raises(spec: dict, monkeypatch) -> None:
    monkeypatch.setitem(b5.CASES, "X-soil-event", spec)
    with pytest.raises(ValueError, match="rigid floor"):
        b5.case_spec("X-soil-event")
    assert any("rigid floor" in text
               for text in b5._invalid_arguments(["X-soil-event"], ["C2"]))
