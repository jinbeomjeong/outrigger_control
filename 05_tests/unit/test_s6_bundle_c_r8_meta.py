"""Bundle-C judge against the P-R8-9 ... 11 controller meta (spec rev. 32 160 / 163):
CHECK window ``target.check_window`` (absolute engine time, raw-tilt box samples) and the D-group
``relevel_predicted`` count with PROBE aborts (``probe_aborted_low_load``) split off."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from outrigger_sim.frames import quat_from_euler_zyx
from outrigger_sim.verify import s6_bundle_c as bc

T0 = 90.0


def _case(check_window, *, phases=None, ctrl=(0.0, 0.01), quiet=True) -> dict:
    t = np.round(np.arange(100.0, 110.0 + 1e-9, 0.1), 10)  # Record 10 Hz, absolute time
    pitch = np.where((t > 104.0 + 1e-9) & (t <= 105.0 + 1e-9), 0.01, 0.02)
    quat = quat_from_euler_zyx(np.zeros_like(t), pitch, np.zeros_like(t))
    target = {"check_average_s": 1.0, "limits_rad": {}, "crawler_settle_map": None,
              "check_attitude_source": "raw_tilt", "check_window": check_window}
    return {
        "dir": None,
        "pads": None,
        "rec": {"t": t, "body_quat_wxyz": quat},
        "result": {
            "settings": {"start_t_s": T0, "bundle_c": {"imu_sample_period_s": 0.01}},
            "phases": phases if phases is not None else [[0.1, "check"], [20.0, "touch"]],
            "acceptance": {"last_check": {"crawler_attitude_rad": list(ctrl), "code": "OK"}},
            "controller_meta": {"target": target},
        },
    }


def _window(t_last: float = 105.0, n: int = 100) -> dict:
    return {"t_judged_s": t_last, "t_first_sample_s": t_last - (n - 1) * 0.01,
            "t_last_sample_s": t_last, "sample_count": n, "quiet_start_s": 103.5,
            "last_nonzero_command_t_s": 103.0, "is_quiet_window_full": True}


def test_check_window_meta_is_absolute_and_covers_the_box_samples() -> None:
    ca = bc.check_attitude_metrics(_case(_window()))
    assert ca["window_abs_s"] == pytest.approx([104.0, 105.0])
    assert ca["n_samples"] == 10  # Record 104.1 ... 105.0
    assert ca["truth_deg"][1] == pytest.approx(math.degrees(0.01))
    assert ca["error_maxabs_deg"] == pytest.approx(0.0, abs=1e-9)
    assert ca["window_source"].startswith("controller meta target.check_window")
    assert ca["check_window"]["is_quiet_window_full"] is True
    rows = bc._check_attitude_rows({"case": "X", "grade": "ideal", "check_attitude": ca})
    assert rows[0]["passed"] is True


def test_check_window_shifted_by_t0_would_miss_the_record() -> None:
    """A relative-time window (absolute - t0) finds no Record sample: guards the clock."""
    w = _window()
    w = {**w, "t_first_sample_s": w["t_first_sample_s"] - T0,
         "t_last_sample_s": w["t_last_sample_s"] - T0}
    ca = bc.check_attitude_metrics(_case(w))
    assert "no Record 10 Hz sample" in ca["status"]


def test_check_window_none_falls_back_to_the_decision_instant() -> None:
    ca = bc.check_attitude_metrics(_case(None, phases=[[0.1, "check"], [15.0, "touch"]]))
    assert ca["window_abs_s"] == pytest.approx([104.0, 105.0])
    assert "fallback" in ca["window_source"]
    assert ca["error_maxabs_deg"] == pytest.approx(0.0, abs=1e-9)


def test_check_window_error_detected() -> None:
    ca = bc.check_attitude_metrics(_case(_window(), ctrl=(0.0, 0.02)))
    assert ca["error_deg"][1] == pytest.approx(math.degrees(0.01))


# --- D group relevel_predicted ---------------------------------------------------------------


def _ev(t: float, name: str) -> str:
    return f"C2Event(t_s={t!r}, name='{name}')"


def _relevel_case(events) -> dict:
    return {"result": {"settings": {"start_t_s": T0},
                       "phases": [[0.1, "check"], [10.0, "ready"], [12.0, "probe"],
                                  [13.0, "level"], [20.0, "ready"]]},
            "events": events}


def test_relevel_probe_abort_split_from_other() -> None:
    case = _relevel_case([
        _ev(T0 + 13.0, "relevel_predicted:RR"),
        _ev(T0 + 13.0, "probe_aborted_low_load:RR"),
        _ev(T0 + 25.0, "relevel_predicted:FL"),
    ])
    rv = bc.relevel_metrics(case)
    assert rv["counts"] == {"probe_abort": 1, "other": 1}
    assert rv["probe_abort"][0]["phase_before"] == "probe"
    assert rv["probe_abort"][0]["abort_legs"] == ["RR"]
    assert rv["other"][0]["leg"] == "FL" and rv["other"][0]["phase_before"] == "ready"
    m = {"case": "C1_G1_top_flat", "rerun_group": "D", "relevel_predicted": rv}
    (row,) = bc._relevel_rows(m)
    assert row["value"] == 1 and row["passed"] is False


def test_relevel_d_group_passes_with_probe_abort_only() -> None:
    rv = bc.relevel_metrics(_relevel_case([
        _ev(T0 + 13.0, "probe_aborted_low_load:RR"), _ev(T0 + 13.0, "relevel_predicted:RR")]))
    (row,) = bc._relevel_rows({"case": "X", "rerun_group": "D", "relevel_predicted": rv})
    assert row["value"] == 0 and row["passed"] is True and "1 with probe_aborted" in row["note"]
    # outside the D group: report only; no R-5 at all: no row
    (rep,) = bc._relevel_rows({"case": "X", "rerun_group": "B", "relevel_predicted": rv})
    assert rep["kind"] == "report" and rep["passed"] is None
    empty = bc.relevel_metrics(_relevel_case([]))
    assert bc._relevel_rows({"case": "X", "rerun_group": "B", "relevel_predicted": empty}) == []
    (d0,) = bc._relevel_rows({"case": "X", "rerun_group": "D", "relevel_predicted": empty})
    assert d0["passed"] is True


def test_rerun_groups_from_batch_meta(tmp_path) -> None:
    (tmp_path / "batch_meta.json").write_text(
        json.dumps({"groups": {"C": ["a"], "D": ["b", "c"]}}), encoding="utf-8")
    assert bc.rerun_groups(tmp_path) == {"a": "C", "b": "D", "c": "D"}
    assert bc.rerun_groups(tmp_path / "missing") == {}
