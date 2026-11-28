"""D1 trace of ``control/two_pressure`` (436.9 edition 8 stage-5 A/A diagnosis, record only).

The trace is off by default; on, it records every diagnosed period and leaves every reading,
event and the monitor state as they are without it (same synthetic periods, two monitors).
"""

from __future__ import annotations

import pickle

import numpy as np
import pytest

from outrigger_sim.control import two_pressure
from outrigger_sim.control.two_pressure import (
    TwoPressureMonitor,
    TwoPressureSettings,
    start_d1_trace,
    stop_d1_trace,
)

BAR = 1e5
PERIOD_S = 0.1
HEAD_AREA = np.array([1.3273229e-2, 1.3273229e-2, 9.50331778e-3, 9.50331778e-3])
ANNULUS = np.array([3.76991118e-3, 3.76991118e-3, 3.14159265e-3, 3.14159265e-3])
V_MAX = 0.020924
F_MIN_N = 9414.59
GRAVITY_M_S2 = 9.80665
LOAD_N = 2.0 * np.array([118e3, 118e3, 72e3, 72e3])
STILL = np.zeros(4)
STROKE_M = 0.552
FR, RL = 1, 2
GYRO_AT_REST = np.zeros((2, 3))
GYRO_SPIN_UP = np.array([[0.0, 0.0, 0.0], [2e-4, -1e-4, 0.0]])
"""Two gyro partial means 10 ms apart: a small roll and pitch acceleration (lever term about
0.02 m/s^2, far below what would leave the load shift unexplained)."""
IMU_LEVER_ARM_M = (0.31, 0.88, 0.040)


@pytest.fixture(autouse=True)
def _trace_off_around_each_test():
    stop_d1_trace()
    yield
    stop_d1_trace()


def _monitor() -> TwoPressureMonitor:
    settings = TwoPressureSettings().with_r8_period()
    assert settings.imu_lever_correction  # the GYRO_MISSING branch below needs it
    return TwoPressureMonitor(HEAD_AREA, ANNULUS, V_MAX, F_MIN_N, PERIOD_S, settings=settings,
                              stroke_max_m=0.70, imu_lever_arm_m=IMU_LEVER_ARM_M)


def _pressures(load_N, rod_bar=2.0):
    rod = np.full(4, rod_bar * BAR)
    return (np.asarray(load_N, dtype=float) + rod * ANNULUS) / HEAD_AREA, rod


def _periods() -> list[dict]:
    """READY stay, lifted periods with and without gyro samples, a load shift between legs
    (explained), a head sensor jump (unexplained) and a period after it."""
    periods = [{"load": LOAD_N, "locked": True, "gyro": GYRO_AT_REST} for _ in range(5)]
    periods.append({"load": LOAD_N, "gyro": GYRO_SPIN_UP})
    shifted = LOAD_N + np.array([0.0, 120e3, -120e3, 0.0])  # FR +90 bar, RL -126 bar
    periods.append({"load": shifted, "gyro": None})  # no gyro: WARN_D1_IMU_GYRO_MISSING
    periods.append({"load": shifted, "gyro": GYRO_AT_REST, "jump_bar": {RL: 150.0}})
    periods.append({"load": shifted, "gyro": GYRO_AT_REST, "jump_bar": {RL: 150.0}})
    return periods


def _run(monitor: TwoPressureMonitor) -> tuple[list[np.ndarray], list[list[str]]]:
    readings, events = [], []
    for k, period in enumerate(_periods()):
        head, rod = _pressures(period["load"])
        for leg, jump_bar in period.get("jump_bar", {}).items():
            head[leg] += jump_bar * BAR
        out = monitor.read(k * PERIOD_S, head, rod, STILL, period.get("locked", False), 2e3,
                           stroke_m=np.full(4, STROKE_M),
                           imu_specific_force_z_m_s2=GRAVITY_M_S2, is_crawler_lifted=True,
                           imu_gyro_rad_s=period["gyro"])
        readings.append(np.stack([out.nominal, out.lower, out.upper, out.head_only]))
        events.append([name for name, _ in monitor.pop_events()])
    return readings, events


def test_trace_is_off_by_default() -> None:
    assert two_pressure._active_d1_trace is None
    _run(_monitor())
    assert stop_d1_trace() is None


def test_trace_on_changes_no_reading_event_or_state() -> None:
    plain = _monitor()
    plain_readings, plain_events = _run(plain)
    traced = _monitor()
    trace = start_d1_trace()
    traced_readings, traced_events = _run(traced)
    assert stop_d1_trace() is trace
    assert len(trace.rows) == len(_periods())
    for plain_reading, traced_reading in zip(plain_readings, traced_readings, strict=True):
        assert plain_reading.tobytes() == traced_reading.tobytes()
    assert traced_events == plain_events
    assert pickle.dumps(traced) == pickle.dumps(plain)


def test_trace_rows_hold_the_judgement() -> None:
    trace = start_d1_trace()
    _, events = _run(_monitor())
    rows = trace.rows
    assert list(trace.monitors) == [rows[0]["monitor"]]
    assert trace.monitors[rows[0]["monitor"]]["settings"]["max_step_Pa"] == 100.0 * BAR
    assert "dp_head_Pa" not in rows[0]  # no period before the first

    spin_up = rows[5]
    assert spin_up["lever_z_m_s2"] is not None and spin_up["lever_z_m_s2"] != 0.0
    assert spin_up["f_z_raw_m_s2"] - spin_up["lever_z_m_s2"] == spin_up["f_z_used_m_s2"]

    shift = rows[6]
    assert shift["is_lever_missing"] and shift["lever_z_m_s2"] is None
    assert "WARN_D1_IMU_GYRO_MISSING" in shift["events"]
    assert shift["head_step_candidates"] == ["RL"]  # FR +90 bar stays below 100 bar
    assert shift["step_rule_branch"] == "imu_residual"
    assert shift["judged_change_N"] == shift["residual_change_N"]
    candidate = shift["candidates"]["RL"]
    assert candidate["threshold_N"] == pytest.approx(0.5 * abs(candidate["dp_head_Pa"])
                                                     * HEAD_AREA[RL])
    assert not candidate["is_unexplained"] and shift["head_fault_reasons"] == {}

    jump = rows[7]
    assert jump["candidates"]["RL"]["is_unexplained"]
    assert jump["head_fault_reasons"] == {"RL": "D1_step"}
    assert "FAULT_HEAD_PRESSURE:RL" in jump["events"]
    assert set(jump["events"]) <= set(events[7])
    assert "candidates" not in rows[8]  # step rule suspended or no new step
