"""Spec 426.7 A (study A, ``04_scripts/03_control/s9/s9_soil_event_screen.py``): job keys, the
soil event floor (T-6) and the recorded control period (T-1: with the head reading and no event
it is the s9 ``control_period`` bit for bit). Needs numba (dynamics-dev / Chrono-dev)."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("numba")

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "04_scripts" / "03_control" / "s9", ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import s9_soil_closed_loop as sl  # noqa: E402
import s9_soil_event_screen as screen  # noqa: E402

T1_PERIODS = 300
MEASUREMENT_FIELDS = ("t_s", "specific_force_m_s2", "angular_rate_rad_s", "head_pressure_Pa",
                      "stroke_m", "stroke_corrected_m", "imu_specific_force_samples_m_s2")


# ----------------------------------------------------------------------------------- job keys
def test_job_sets_of_spec_426_3() -> None:
    sizes = {name: len(screen.all_jobs(name)) for name in ("main", "head", "j1", "all", "all_j1")}
    assert sizes == {"main": 12, "head": 4, "j1": 4, "all": 16, "all_j1": 20}
    keys = screen.all_jobs("all")
    assert len(set(keys)) == 16
    assert "A|J2|RR|Fs8|two" in keys and "A|rigid|FL|Fs0|head" in keys
    assert all(screen.EventJob.from_key(k).key == k for k in keys)
    with pytest.raises(ValueError):
        screen.all_jobs("x")


def test_readings_override_and_filter() -> None:
    head = screen.select_jobs("all", readings="head")
    assert len(head) == 12 and all(k.endswith("|head") for k in head)  # rigid head jobs once
    assert screen.select_jobs("all", "J2|RR") == ["A|J2|RR|Fs0|two", "A|J2|RR|Fs8|two"]


@pytest.mark.parametrize("key", ["B|J2|RR|Fs8|two", "A|J2|XX|Fs8|two", "A|J2|RR|8|two",
                                 "A|J2|RR|Fs8|rod"])
def test_bad_job_keys(key) -> None:
    with pytest.raises(ValueError):
        screen.EventJob.from_key(key)


def test_event_table_speeds() -> None:
    """Fast = faster than v_max (r67): FS24 and RE1bF; G4 and SS are slow."""
    v_max = 0.020924
    fast = {k for k, ev in screen.EVENTS.items() if ev["depth"] / ev["ramp"] > v_max}
    assert fast == {"FS24", "RE1bF"}
    assert set(screen.TIMING_EVENTS["ready"]) | set(screen.TIMING_EVENTS["level"]) == set(
        screen.EVENTS)


# ------------------------------------------------------------------------- T-6 event floor
def _fake_plant(has_soil: bool):
    soil = None
    if has_soil:
        soil = SimpleNamespace(h=np.array([0.31, 0.32, 0.33, 0.34]),
                               z=np.array([0.1, 0.2, 0.3, 0.4]),
                               sp=np.array([0.01, 0.02, 0.03, 0.04]),
                               sy=np.array([1e4, 2e4, 3e4, 4e4]))
    return SimpleNamespace(t=0.0, soil=soil, goff=np.zeros(4))


def test_t6_soil_event_lowers_only_the_reference_surface() -> None:
    plant = _fake_plant(True)
    h0 = plant.soil.h.copy()
    state = [plant.soil.z.copy(), plant.soil.sp.copy(), plant.soil.sy.copy()]
    floor = screen.soil_event_floor(3, 0.030, 0.05, t_ev=1.0)
    for t_s in np.arange(0.5, 1.2, 1e-3):
        plant.t = float(t_s)
        floor(plant)
        if t_s < 1.0 - 1e-9:
            assert plant.soil.h[3] == h0[3]
    assert abs((plant.soil.h[3] - h0[3]) - (-0.030)) <= 1e-12
    assert np.array_equal(plant.soil.h[:3], h0[:3])
    for before, after in zip(state, (plant.soil.z, plant.soil.sp, plant.soil.sy), strict=True):
        assert np.array_equal(before, after)
    assert not plant.goff.any()  # the soil event does not use goff (soil_floor rewrites it)


def test_t6_rigid_event_is_the_r67_floor_offset() -> None:
    plant = _fake_plant(False)
    floor = screen.soil_event_floor(0, 0.0115, 2.0, t_ev=0.0)
    plant.t = 1.0
    floor(plant)
    assert plant.goff[0] == pytest.approx(0.0115 * screen.poly345(0.5))
    plant.t = 2.5
    floor(plant)
    assert plant.goff[0] == 0.0115 and not plant.goff[1:].any()


def test_poly345_ends() -> None:
    assert screen.poly345(-1.0) == 0.0 and screen.poly345(0.0) == 0.0
    assert screen.poly345(1.0) == 1.0 and screen.poly345(2.0) == 1.0
    assert screen.poly345(0.5) == pytest.approx(0.5)


# ----------------------------------------------------------------------- T-1 control period
@pytest.fixture(scope="module")
def harness():
    cl, c2, meas = sl._imports()
    return cl, c2, meas


def test_t1_recorded_period_is_the_s9_period(harness) -> None:
    """``control_period_rec(readings="head", floor_fn=None)`` (with a 1 ms record) = the s9
    ``control_period`` over 300 closed-loop periods from the same deepcopied state."""
    cl, c2, meas = harness
    plant, ctrl, _ = screen.make_event_base(cl, c2, "J2", "top", "B", 4.0)
    plant_s9, ctrl_s9 = copy.deepcopy(plant), copy.deepcopy(ctrl)
    ha = ctrl.geometry.head_area_m2
    cmd, valve, cmd_s9, valve_s9 = np.zeros(4), np.zeros(4), np.zeros(4), np.zeros(4)
    rec, rec_s9, rows = {}, {}, []
    for _ in range(T1_PERIODS):
        m = screen.control_period_rec(cl, meas, plant, cmd, valve, ha, ctrl.period_s, rec,
                                      rows=rows, readings=screen.READINGS_HEAD)
        m_s9 = sl.control_period(cl, meas, plant_s9, cmd_s9, valve_s9, ha, ctrl_s9.period_s,
                                 rec_s9)
        for name in MEASUREMENT_FIELDS:
            assert np.array_equal(np.asarray(getattr(m, name)), np.asarray(getattr(m_s9, name)))
        assert np.array_equal(rec["fmin"], rec_s9["fmin"]) and rec["crmax"] == rec_s9["crmax"]
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        cmd_s9 = np.array(ctrl_s9.update(m_s9).leg_speed_m_s)
        assert cmd.tobytes() == cmd_s9.tobytes()
    assert len(rows) == T1_PERIODS * 100 and len(rows[0]) == len(screen.ROW_COLUMNS)
    assert str(ctrl.phase) == str(ctrl_s9.phase)


def test_unknown_readings(harness) -> None:
    cl, _, meas = harness
    with pytest.raises(ValueError):
        screen.control_period_rec(cl, meas, None, None, None, None, 0.1, {}, readings="rod")
