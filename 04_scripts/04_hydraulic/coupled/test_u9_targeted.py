"""Checks of the U-9 targeted batch (``u9_targeted_rules_rev1.md`` 3.2 P-1 .. P-3), no harness run.

The U9 values are checked on synthetic 1 ms chunk rows; the batch on the job lists.
Run (dynamics-dev): python -I -B -m pytest <this file> -p no:cacheprovider
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
import run_v5  # noqa: E402
from harness_flow import COLUMN, COLUMNS, U  # noqa: E402
from verdict_metrics import u9_values  # noqa: E402

CHUNKS = 1000
MOVING_SPEED_M_S = 0.01
RAMP_DEG_PER_CHUNK = 1e-3
ALL_LEGS = 0b1111


def _synthetic_run() -> tuple[np.ndarray, np.ndarray, dict]:
    """1 s of chunks: TOUCH 0-99, LEVEL 100-899, DONE 900-999, every leg moving except RR on
    300-549. Limited masks: k = 2 on 100-299, 3 on 300-549 (mask 15, RR at rest), 4 on 550-699,
    1 on 700-749, 4 on 750-799 (a 50 ms run), 0 on 800-899, 4 on DONE. Roll ramps 1 deg/s over
    300-699 (the k >= 3 run)."""
    rows = np.zeros((CHUNKS, len(COLUMNS)))
    index = np.arange(CHUNKS)
    rows[:, COLUMN["t"]] = (index + 1) * 1e-3
    rows[:, U] = MOVING_SPEED_M_S
    rows[300:550, U.start + 3] = 0.0
    limited = np.zeros(CHUNKS)
    for first, last, mask in ((100, 299, 0b0011), (300, 699, ALL_LEGS), (700, 749, 0b0001),
                              (750, 799, ALL_LEGS), (900, 999, ALL_LEGS)):
        limited[first: last + 1] = mask
    rows[:, COLUMN["limited_mask"]] = limited
    roll_deg = np.clip(index - 300, 0, 399) * RAMP_DEG_PER_CHUNK
    rows[:, COLUMN["roll"]] = np.radians(roll_deg)
    phases = np.full(CHUNKS, "level", dtype=object)
    phases[:100] = "touch"
    phases[900:] = "done"
    period_t = np.arange(1, 11) * 0.1
    filtered = np.column_stack([np.arange(1, 11) * 0.01, -np.arange(1, 11) * 0.01])
    return rows, phases, {"t": period_t, "filtered_deg": filtered}


# ------------------------------------------------------------------------------- P-3 values
def test_time_per_limited_leg_count_and_longest_runs() -> None:
    values = u9_values(*_synthetic_run())
    assert values["level_count_s"] == {"1": 0.05, "2": 0.2, "3": 0.25, "4": 0.2}
    assert values["post_touch_count_s"] == {"1": 0.05, "2": 0.2, "3": 0.25, "4": 0.3}
    assert values["longest_ge3_s"] == 0.4
    assert values["longest_eq4_s"] == 0.15


def test_ge3_run_holds_the_attitude_change_and_the_filtered_ends() -> None:
    values = u9_values(*_synthetic_run())
    assert values["ge3_runs_count"] == 1  # the 50 ms run is below 0.1 s
    (run,) = values["ge3_runs"]
    assert run["t_start_s"] == 0.301 and run["dur_s"] == 0.4
    assert run["set_at_middle"] == ["FL", "FR", "RL"]  # RR limited but at rest
    assert run["attitude_start_deg"] == {"roll": 0.0, "pitch": 0.0}
    assert run["max_abs_delta_deg"] == {"roll": 0.399, "pitch": 0.0}
    assert run["filtered_start_deg"] == {"t_s": 0.3, "roll": 0.03, "pitch": -0.03}
    assert run["filtered_end_deg"] == {"t_s": 0.7, "roll": 0.07, "pitch": -0.07}
    assert run["max_abs_rate_deg_s"] == {"roll": pytest.approx(1.0), "pitch": 0.0}
    assert values["level_sat_rate_max_deg_s"] == {"roll": pytest.approx(1.0), "pitch": 0.0}


def test_no_k3_run_gives_an_empty_list_and_flow_off_an_empty_dict() -> None:
    rows, phases, period = _synthetic_run()
    rows[:, COLUMN["limited_mask"]] = np.minimum(rows[:, COLUMN["limited_mask"]], 0b0011)
    values = u9_values(rows, phases, period)
    assert values["ge3_runs"] == [] and values["ge3_runs_count"] == 0
    assert values["longest_ge3_s"] == 0.0 and values["longest_eq4_s"] == 0.0
    rows[:, COLUMN["limited_mask"]] = 0
    assert u9_values(rows, phases, period)["level_sat_rate_max_deg_s"] is None
    assert u9_values(rows, phases, period, is_flow_on=False) == {}


# ---------------------------------------------------------------------------- P-1 / P-2 jobs
def test_u9_batch_is_14_keys_by_3_settings() -> None:
    jobs = run_v5.batch_jobs(run_v5.U9_BATCH)
    assert len(jobs) == 42
    assert len({run_v5.job_key(job) for job in jobs}) == 42
    assert all(job["u9_metrics"] is True for job in jobs)
    keys = {(job["case"], job["eps"]) for job in jobs}
    assert len(keys) == 14
    assert {eps for case, eps in keys if case == "S3"} == {0.0, 2e-3}
    settings = [(job["setting"], job.get("eta_v")) for job in jobs]
    assert {s: settings.count(s) for s in set(settings)} == {
        ("V0", None): 14, ("VB", 0.85): 14, ("VB", 0.80): 14}
    names = [run_v5.t4h_file_name(job) for job in jobs if job["setting"] in run_v5.T4H_SETTINGS]
    assert len(names) == len(set(names)) == 28
    assert "S2_e0.002_VB-eta0.8.npz" in names and "S2_e0.002_VB-eta0.85.npz" in names


def test_eta_v_sets_the_supply_and_is_refused_without_the_flow_limit() -> None:
    default, _ = run_v5.options_of("VB")
    same, _ = run_v5.options_of("VB", 0.85)
    low, _ = run_v5.options_of("VB", 0.80)
    assert default == same and default.eta_v == run_v5.ETA_V
    assert low.eta_v == 0.80 and low.is_enabled
    with pytest.raises(ValueError, match="no flow limit"):
        run_v5.options_of("V0", 0.85)


def test_jobs_without_the_new_keys_keep_their_names() -> None:
    assert run_v5.batch_jobs("smoke") == [
        {"case": "R12", "eps": 0.0, "offset_s": 0.0, "setting": "V0"}]
    assert run_v5.t4h_file_name({"case": "S2", "eps": 0.002, "setting": "VB"}) == (
        "S2_e0.002_VB.npz")
