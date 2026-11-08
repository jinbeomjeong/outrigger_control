"""Checks of the T4h shadow gate (``las_shadow.py``, ``las_targeted_rules.md`` 4 and
``las_targeted_rules_rev1.md`` 2, 4), no harness run.

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


def _twisting_loads() -> np.ndarray:
    """Sum 0.65 W_ref + 2 F_min, min 2 F_min (FL); RR falls 1 kN per period, so rho (about
    0.43) rises in every period: S7' holds wherever the previous update was a LEVEL step."""
    steps = np.arange(10)[:, None]
    base = np.array([2 * F_MIN_N, 0.3 * W_REF_N, 0.2 * W_REF_N, 0.15 * W_REF_N])
    return base + steps * np.array([0.0, 0.0, 1e3, -1e3])


def _record(events, loads=None, phases=None) -> ls.ShadowRecord:
    t_s = np.round(np.arange(1, 11) * 0.1, 10)
    return ls.ShadowRecord(name="r.npz", t_s=t_s, phase=np.array(phases or PHASES),
                           lower_estimate_N=_twisting_loads() if loads is None else loads,
                           events=events, F_min_N=F_MIN_N, weight_ref_N=W_REF_N,
                           soil_enable=True, job=None, commands_sha256=None)


def test_the_first_level_step_has_no_previous_rho() -> None:
    result = ls.shadow_judge(_record([]), B0)
    # update 2 (t 0.3) is the first LEVEL step: no rho_{k-1}, S7' false; update 3 fires
    assert result["status"] == ls.FIRES and result["first_fire_t_s"] == pytest.approx(0.4)
    assert result["s7p_first_t_s"] == pytest.approx(0.4) and result["mode"] == ls.MODE_STORED


def test_events_at_t_k_close_the_gate_in_that_period() -> None:
    assert ls.shadow_judge(_record([(0.4, "crawler_liftoff_confirmed")]), B0)["status"] == (
        ls.SILENT)
    result = ls.shadow_judge(_record([(0.3, "leg_reapproach_start:FL"),
                                      (0.5, "leg_reapproach_contact:FL")]), B0)
    assert result["first_fire_t_s"] == pytest.approx(0.5)
    result = ls.shadow_judge(_record([(0.5, "soil_mode_start")]), B0)
    assert result["first_fire_t_s"] == pytest.approx(0.4)
    assert ls.shadow_judge(_record([(0.4, "soil_mode_start")]), B0)["status"] == ls.SILENT


def test_a_non_level_period_clears_the_previous_rho() -> None:
    phases = ["touch", "level", "level", "check", "level", "level", "level", "level", "done",
              "ready"]
    flags = ls.level_step_flags(np.array(phases))
    assert flags.tolist() == [False, False, True, True, False, True, True, True, True, False]
    s7 = ls.s7_prime(_twisting_loads(), flags, B0, W_REF_N, F_MIN_N)
    assert s7.tolist() == [False, False, False, True, True, False, True, True, True, True]


def test_falling_or_equal_rho_does_not_fire() -> None:
    falling = _twisting_loads()[::-1].copy()
    assert ls.shadow_judge(_record([], loads=falling), B0)["status"] == ls.SILENT
    flat = np.tile(_twisting_loads()[0], (10, 1))
    result = ls.shadow_judge(_record([], loads=flat), B0)
    assert result["status"] == ls.SILENT and result["blocked"]["closest"]["false"] == ["S7"]
    assert result["blocked"]["max_pre_loc_rho"] == pytest.approx(
        lt.diagonal_deficit_ratio(flat[0])[0])


def test_band_mode_widens_each_condition_to_the_safe_side() -> None:
    flags = np.ones(2, bool)  # both LEVEL steps: update 1 has a rho_{k-1}
    delta_N = 100.0
    base = np.array([[2 * F_MIN_N, 0.3 * W_REF_N, 0.2 * W_REF_N, 0.15 * W_REF_N]] * 2)

    def fires(loads: np.ndarray, delta: float) -> bool:
        return bool(ls.s7_prime(loads, flags, B0, W_REF_N, F_MIN_N, delta)[1])

    equal = base.copy()  # rho_k == rho_{k-1}: exact false, band (> -16 delta / sum) true
    assert not fires(equal, 0.0) and fires(equal, delta_N)
    shy = base.copy()  # sum 3 delta below alpha W_ref
    shy[:, 1] -= shy[1].sum() - (B0.alpha * W_REF_N - 3 * delta_N)
    shy[1, 3] -= 1.0  # keep rho rising
    assert not fires(shy, 0.0) and fires(shy, delta_N)
    heavy = base.copy()  # min L at beta F_min (not <): band adds delta
    heavy[:, 0] = B0.beta * F_MIN_N
    heavy[1, 3] -= 1.0
    assert not fires(heavy, 0.0) and fires(heavy, delta_N)


def test_s4_fault_in_the_level_step_closes_s2() -> None:
    phases = ["touch", "level", "level", "fault", "fault", "fault", "fault", "fault", "fault",
              "fault"]
    record = _record([(0.4, "WARN_CRAWLER_LIFTOFF_UNCONFIRMED")], phases=phases)
    assert ls.shadow_judge(record, B0)["status"] == ls.SILENT


def test_relevel_counts_and_silent_lists_the_blocked_gate() -> None:
    phases = ["touch", "level", "done", "level", "level", "level", "level", "level", "done",
              "ready"]
    flags = ls.level_step_flags(np.array(phases))
    assert flags.tolist() == [False, False, True, True, True, True, True, True, True, False]
    loads = _twisting_loads()
    loads[:, 0] = 4 * F_MIN_N
    result = ls.shadow_judge(_record([], loads=loads, phases=phases), B0)
    assert result["status"] == ls.SILENT
    assert result["blocked"]["closest"]["false"] == ["S7"]
    assert result["blocked"]["false_counts"]["S7"] == result["blocked"]["level_steps"] == 7


def test_missing_lower_estimate_is_undecidable_without_r2(tmp_path: Path) -> None:
    path = tmp_path / "old.npz"
    np.savez(path, t_s=np.zeros(2), phase=np.array(["level", "level"]),
             meta_json=np.array(json.dumps({"events": [], "F_min_N": F_MIN_N})))
    result = ls.judge_file(path, B0)
    assert result["status"] == ls.UNDECIDABLE and "lower_estimate_N" in result["reason"]
    rejected = ls.judge_file(path, B0, ls.RebuildSetting(600.0, ls.MODE_REJECT))
    assert rejected["reason"].startswith("R-5: R-2 delta")
    no_fields = ls.judge_file(path, B0, ls.RebuildSetting(0.0, ls.MODE_EXACT))
    assert no_fields["reason"].startswith("R-5: rebuild failed") and "head_pressure_Pa" in (
        no_fields["reason"])


# ------------------------------------------------------------------------------- R-2
def test_rebuild_mode_limits() -> None:
    assert ls.rebuild_mode(0.0) == ls.rebuild_mode(1.0) == ls.MODE_EXACT
    assert ls.rebuild_mode(1.01) == ls.rebuild_mode(500.0) == ls.MODE_BAND
    assert ls.rebuild_mode(500.1) == ls.rebuild_mode(float("nan")) == ls.MODE_REJECT


def test_abs_difference_nan_rules() -> None:
    a = np.array([1.0, np.nan, np.nan, 5.0])
    b = np.array([1.5, np.nan, 2.0, 5.0])
    assert ls._abs_difference(a, b).tolist() == [0.5, 0.0, np.inf, 0.0]


def test_load_estimate_transform_is_the_controllers_function() -> None:
    from outrigger_sim.control.c2 import ContactJudge

    class Config:
        contact = ContactJudge.COMBINED

    lower = np.array([[20e3, 30e3, 40e3, 50e3]])
    bands = np.array([[1e3, 2e3, 13e3, 0.0]])
    np.testing.assert_array_equal(ls.load_estimate_transform(Config, lower, bands),
                                  lower - bands)
    Config.contact = ContactJudge.PRESSURE
    np.testing.assert_array_equal(ls.load_estimate_transform(Config, lower, bands), lower)
    assert ls.transform_name(Config).startswith("identity")


def test_r2_verdict_takes_the_largest_difference() -> None:
    rows = [{"file": "a", "status": "compared", "rows": 3, "max_abs_N": 0.2,
             "transform": "t", "transform_max_abs_N": 0.0},
            {"file": "b", "status": "compared", "rows": 2, "max_abs_N": 12.0, "transform": "t"},
            {"file": "c", "status": "no stored L-hat"}]
    verdict = ls.r2_verdict(rows)
    assert verdict["max_abs_N"] == 12.0 and verdict["mode"] == ls.MODE_BAND
    assert verdict["records"] == 2 and verdict["without_stored"] == 1
    assert verdict["worst_file"] == "b" and verdict["compared_rows"] == 5
    assert ls.r2_verdict(rows[2:])["mode"] == ls.MODE_REJECT


# ------------------------------------------------------------------------------- V-1 / V-2
def _v1_row(key: str, setting: str, first: float | None, **extra) -> dict:
    return {"key": key, "setting": setting, "online_first_s": first, "online_s7p_s": first,
            "match": True, **extra}


def test_v1_verdict_needs_both_outcomes_settings_and_rebuilt_records() -> None:
    rows = [_v1_row(f"D1|H-R-A|k{i}", "VB" if i % 2 else "V0", 1.0 if i < 5 else None,
                    rebuilt_applicable=True, rebuilt_match=True, rebuilt_status=ls.SILENT,
                    rebuilt_mode=ls.MODE_EXACT)
            for i in range(10)]
    assert ls.v1_verdict(rows)["passed"]
    assert not ls.v1_verdict(rows[:9])["passed"]
    rows[0]["match"] = False
    assert ls.v1_verdict(rows)["problems"] == ["mismatch ['D1|H-R-A|k0']"]
    rows[0]["match"] = True
    for row in rows[2:]:
        row["rebuilt_applicable"] = False  # head-only records: not on the rebuild path
    assert "R-6" in ls.v1_verdict(rows)["problems"][0]


def test_head_only_records_are_outside_the_replay() -> None:
    arrays = {name: np.zeros((2, 4)) for name in ls.REBUILD_ARRAYS}
    meta = {name: {"x": 1} for name in ls.REBUILD_META}
    arrays["rod_pressure_Pa"] = np.full((2, 4), np.nan)
    assert "head-only" in ls.replay_gap(arrays, meta)
    arrays["rod_pressure_Pa"][1, 2] = 1e5
    assert ls.replay_gap(arrays, meta) is None
    assert "meta.events" in ls.replay_gap(arrays, {})


def test_h8_lists_rigid_records_with_s7_prime() -> None:
    rows = [_v1_row("D1|H-R-0|rigid|T|roll+op|K1|V0|e0", "V0", None),
            _v1_row("D1|H-R-A|rigid+J1@FR|T|diag-op|K1|V0|e0", "V0", 21.0)]
    assert not ls.h8_record(rows)["stop"]
    rows[0] = {**rows[0], "online_first_s": 20.7}
    record = ls.h8_record(rows)
    assert record["stop"] and record["start_gate"] == ["D1|H-R-0|rigid|T|roll+op|K1|V0|e0"]


def test_band_rebuild_match_is_one_sided() -> None:
    band = {"status": ls.FIRES, "mode": ls.MODE_BAND, "first_fire_t_s": 20.0}
    assert ls._rebuilt_match(20.5, band) == (True, False)
    assert ls._rebuilt_match(19.5, band) == (False, False)
    assert ls._rebuilt_match(None, band) == (True, True)
    exact = {**band, "mode": ls.MODE_EXACT, "s7p_first_t_s": 19.0}
    assert ls._rebuilt_match(20.5, exact, 19.0) == (False, False)
    assert ls._rebuilt_match(20.0, exact, 19.0) == (True, False)
    assert ls._rebuilt_match(20.0, exact, 18.9) == (False, False)


def test_pick_silent_prefers_rebuilt_rerunnable_records() -> None:
    def line(name: str, mode: str, job: dict | None) -> dict:
        return {"file": name, "status": ls.SILENT, "mode": mode, "job": job,
                "commands_sha256": "a" * 64}

    lines = [line("s1", ls.MODE_STORED, {"case": "R1"}), line("x", ls.MODE_EXACT, {"key": "k"}),
             line("e1", ls.MODE_EXACT, {"case": "R2"}), line("e2", ls.MODE_BAND, {"d1": {}})]
    assert [p["file"] for p in ls.pick_silent(lines, 3)] == ["e1", "e2", "s1"]
