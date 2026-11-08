"""Checks of the T4h shadow gate (``las_shadow.py``, ``las_targeted_rules.md`` 4), no harness run.

Synthetic 10-period records: phase sequence, events at the period times, lower estimates.
Run (dynamics-dev): python -I -B -m pytest <this file> -p no:cacheprovider
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import las_shadow as ls  # noqa: E402
import las_targeted as lt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

B0 = lt.CANDIDATES["b0"]
W_REF_N = 376_600.0
F_MIN_N = 9414.589
PHASES = ["touch", "level", "level", "level", "level", "level", "level", "level", "done",
          "ready"]
"""Update 0 TOUCH; update 1 is the TOUCH -> LEVEL period (no LEVEL step yet); 2 .. 8 LEVEL."""


def _record(events, loads=None, phases=None) -> ls.ShadowRecord:
    t_s = np.round(np.arange(1, 11) * 0.1, 10)
    if loads is None:  # sum 0.65 W_ref + 2 F_min, min 2 F_min: S7 true
        loads = np.tile([2 * F_MIN_N, 0.3 * W_REF_N, 0.2 * W_REF_N, 0.15 * W_REF_N], (10, 1))
    return ls.ShadowRecord(name="r.npz", t_s=t_s, phase=np.array(phases or PHASES),
                           lower_estimate_N=loads, events=events, F_min_N=F_MIN_N,
                           weight_ref_N=W_REF_N, soil_enable=True, job=None,
                           commands_sha256=None)


def test_first_level_step_follows_the_touch_period() -> None:
    result = ls.shadow_judge(_record([]), B0)
    assert result["status"] == ls.FIRES and result["first_fire_t_s"] == pytest.approx(0.3)


def test_events_at_t_k_close_the_gate_in_that_period() -> None:
    assert ls.shadow_judge(_record([(0.3, "crawler_liftoff_confirmed")]), B0)["status"] == (
        ls.SILENT)
    result = ls.shadow_judge(_record([(0.3, "leg_reapproach_start:FL"),
                                      (0.5, "leg_reapproach_contact:FL")]), B0)
    assert result["first_fire_t_s"] == pytest.approx(0.5)
    result = ls.shadow_judge(_record([(0.4, "soil_mode_start")]), B0)
    assert result["first_fire_t_s"] == pytest.approx(0.3)
    assert ls.shadow_judge(_record([(0.3, "soil_mode_start")]), B0)["status"] == ls.SILENT


def test_s4_fault_in_the_level_step_closes_s2() -> None:
    phases = ["touch", "level", "fault", "fault", "fault", "fault", "fault", "fault", "fault",
              "fault"]
    record = _record([(0.3, "WARN_CRAWLER_LIFTOFF_UNCONFIRMED")], phases=phases)
    assert ls.shadow_judge(record, B0)["status"] == ls.SILENT


def test_relevel_counts_and_silent_lists_the_blocked_gate() -> None:
    phases = ["touch", "level", "done", "level", "level", "level", "level", "level", "done",
              "ready"]
    flags = ls.level_step_flags(np.array(phases))
    assert flags.tolist() == [False, False, True, True, True, True, True, True, True, False]
    loads = np.tile([4 * F_MIN_N, 0.3 * W_REF_N, 0.2 * W_REF_N, 0.15 * W_REF_N], (10, 1))
    result = ls.shadow_judge(_record([], loads=loads, phases=phases), B0)
    assert result["status"] == ls.SILENT
    assert result["blocked"]["closest"]["false"] == ["S7"]
    assert result["blocked"]["false_counts"]["S7"] == result["blocked"]["level_steps"] == 7


def test_missing_lower_estimate_is_undecidable(tmp_path: Path) -> None:
    path = tmp_path / "old.npz"
    np.savez(path, t_s=np.zeros(2), phase=np.array(["level", "level"]),
             meta_json=np.array(json.dumps({"events": [], "F_min_N": F_MIN_N})))
    result = ls.judge_file(path, B0)
    assert result["status"] == ls.UNDECIDABLE and "lower_estimate_N" in result["reason"]


def test_v1_verdict_needs_both_outcomes_and_settings() -> None:
    def row(key: str, setting: str, first: float | None) -> dict:
        return {"key": key, "setting": setting, "online_first_s": first, "match": True}

    rows = [row(f"k{i}", "VB" if i % 2 else "V0", 1.0 if i < 5 else None) for i in range(10)]
    assert ls.v1_verdict(rows)["passed"]
    assert not ls.v1_verdict(rows[:9])["passed"]
    rows[0]["match"] = False
    assert ls.v1_verdict(rows)["problems"] == ["mismatch ['k0']"]
