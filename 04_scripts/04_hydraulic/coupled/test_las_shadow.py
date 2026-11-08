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
    # rev2 R-10: one rule-H record first, the others as before
    head_only = [line("h1", ls.MODE_HEAD_ONLY, {"case": "R3"}),
                 line("h2", ls.MODE_HEAD_ONLY, {"case": "R4"})]
    assert [p["file"] for p in ls.pick_silent(head_only + lines, 3)] == ["h1", "e1", "e2"]
    assert [p["file"] for p in ls.pick_silent(head_only + lines[:1], 3)] == ["h1", "h2", "s1"]


# ------------------------------------------------------------------------------- rule H
HEAD_AREA_M2 = np.array([0.013273229, 0.013273229, 0.00950331778, 0.00950331778])
T_S = np.round(np.arange(1, 7) * 0.1, 10)


def test_rule_h_is_head_force_minus_offset_allowance_and_band() -> None:
    from outrigger_sim.control.c2 import ContactJudge

    head_Pa = np.full((6, 4), 100e5)
    zero_N = np.array([500.0, -300.0, 0.0, 200.0])
    allowance_N = np.array([5500.0, 0.0, 4000.0, 0.0])
    is_offset = np.zeros((6, 4), bool)
    is_offset[3:] = True
    has_allowance = np.zeros((6, 4), bool)
    has_allowance[4:] = True
    lower = ls.rule_h_lower_N(head_Pa, HEAD_AREA_M2, zero_N, is_offset, allowance_N,
                              has_allowance)
    head_N = 100e5 * HEAD_AREA_M2
    np.testing.assert_array_equal(lower[0], head_N)
    np.testing.assert_array_equal(lower[3], head_N - zero_N)
    np.testing.assert_array_equal(lower[5], head_N - zero_N - allowance_N)

    class Config:
        contact = ContactJudge.COMBINED

    bands = np.full((6, 4), 4e3)
    np.testing.assert_array_equal(ls.load_estimate_transform(Config, lower, bands),
                                  lower - bands)
    Config.contact = ContactJudge.PRESSURE  # b = 0
    np.testing.assert_array_equal(ls.load_estimate_transform(Config, lower, bands), lower)


def test_offset_starts_after_the_calibration_row_allowance_after_from_s() -> None:
    events = [(0.3, "INFO_PRESSURE_ZERO_CALIBRATED:FL"), (0.3, "INFO_PRESSURE_ZERO_CALIBRATED:RR")]
    is_offset, has_allowance = ls.correction_masks(T_S, events, 0.1, 0.3)
    # calibration event at row 2 (t 0.3): the offset acts from row 3 on, per leg
    assert is_offset[:, 0].tolist() == [False, False, False, True, True, True]
    assert not is_offset[:, 1].any() and is_offset[:, 3].tolist() == is_offset[:, 0].tolist()
    # from_s 0.3: the rows after it, every leg
    assert has_allowance.tolist() == [[t > 0.3 + 1e-9] * 4 for t in T_S]
    _, without_from = ls.correction_masks(T_S, events, 0.1, None)
    np.testing.assert_array_equal(without_from, is_offset)
    no_calibration, no_allowance = ls.correction_masks(T_S, [], 0.1, None)
    assert not no_calibration.any() and not no_allowance.any()


def test_head_only_basis_by_source_marker() -> None:
    nan_rod = {"rod_pressure_Pa": np.full((3, 4), np.nan)}
    finite_rod = {"rod_pressure_Pa": np.full((3, 4), 2e5)}
    assert ls.head_only_basis({}, {}) == "no rod_pressure_Pa"
    assert ls.head_only_basis(nan_rod, {}) == "rod_pressure_Pa all NaN"  # main / item8 / p3
    assert ls.head_only_basis(nan_rod, {"head_only_declared": True}) == (
        "rod_pressure_Pa all NaN; head_only_declared")  # u9_targeted
    setting = {"two_pressure_settings": {"load_estimate": "LoadEstimate.HEAD_ONLY"}}
    assert ls.head_only_basis(finite_rod, setting) == "LoadEstimate.HEAD_ONLY"
    assert ls.head_only_basis(finite_rod, {"two_pressure_settings": {"load_estimate": "net"}}) \
        is None
    with pytest.raises(ValueError, match="head_only_declared"):
        ls.head_only_basis(finite_rod, {"head_only_declared": True})


def test_head_fault_before_loc_only() -> None:
    fault = [(2.0, "FAULT_HEAD_PRESSURE:FL"), (5.0, "crawler_liftoff_confirmed")]
    assert ls.head_fault_before_loc(fault).startswith("FAULT_HEAD_PRESSURE:FL")
    after = [(5.0, "crawler_liftoff_confirmed"), (6.0, "FAULT_HEAD_PRESSURE:FL")]
    assert ls.head_fault_before_loc(after) is None
    assert ls.head_fault_before_loc([(3.0, "fault_reground_start:FR")]) is not None
    assert ls.head_fault_before_loc([(3.0, "INFO_PRESSURE_STEP:FL")]) is None


def _head_only_npz(path: Path, events: list, meta_extra: dict | None = None) -> Path:
    meta = {"events": events, "F_min_N": F_MIN_N, "W_ref_N": W_REF_N, "soil_enable": True,
            "job": {"case": "R1", "eps": 0.0, "setting": "VB"},
            "two_pressure_settings": {}, "hydraulic_options": {}, **(meta_extra or {})}
    np.savez(path, t_s=np.round(np.arange(1, 11) * 0.1, 10), phase=np.array(PHASES),
             head_pressure_Pa=np.full((10, 4), 50e5), seal_band_N=np.zeros((10, 4)),
             rod_pressure_Pa=np.full((10, 4), np.nan), meta_json=np.array(json.dumps(meta)))
    return path


def test_rule_h_records_carry_mode_source_and_exclusions(tmp_path: Path,
                                                         monkeypatch) -> None:
    calls = []

    def fake_rule_h(arrays, meta, name):
        calls.append(name)
        return _twisting_loads(), None

    monkeypatch.setattr(ls, "rule_h_load_estimate_N", fake_rule_h)
    folder = tmp_path / "u9_targeted" / "t4h"
    folder.mkdir(parents=True)
    exact = ls.RebuildSetting(0.0, ls.MODE_EXACT)
    path = _head_only_npz(folder / "R1_e0.0_VB.npz", [])
    result = ls.judge_file(path, B0, rule_h=exact)
    assert result["status"] == ls.FIRES and result["mode"] == ls.MODE_HEAD_ONLY
    assert result["source"] == "u9_targeted" and result["rule_h_mode"] == ls.MODE_EXACT
    assert result["head_only_basis"] == "rod_pressure_Pa all NaN"
    band = ls.judge_file(path, B0, rule_h=ls.RebuildSetting(40.0, ls.MODE_BAND))
    assert band["delta_N"] == 40.0
    faulty = _head_only_npz(folder / "R2_e0.0_VB.npz", [(0.5, "FAULT_HEAD_PRESSURE:RL")])
    excluded = ls.judge_file(faulty, B0, rule_h=exact)
    assert excluded["status"] == ls.UNDECIDABLE and excluded["reason"].startswith(
        "R-7: head fault before LOC")
    stop = ls.judge_file(path, B0, rule_h=ls.RebuildSetting(900.0, ls.MODE_REJECT))
    assert stop["reason"].startswith("H-9")
    assert calls == ["R1_e0.0_VB.npz", "R1_e0.0_VB.npz"]  # excluded records never rebuilt
    # without --r8 a head-only record stays outside (as rev1)
    assert ls.judge_file(path, B0)["status"] == ls.UNDECIDABLE


def test_r8_coverage_and_verdict() -> None:
    def sample(source: str, setting: str = "VB", eps: float = 0.0, stored: bool = True):
        return ls.RerunSample(source, {"case": "R1", "setting": setting, "eps": eps},
                              Path(f"{source}.npz") if stored else None)

    samples = [sample("main"), sample("main", "LS1", 0.002), sample("item8", eps=0.001),
               sample("p3_hash"), sample("u9_targeted"), sample("u9_targeted", eps=0.003)]
    assert ls.r8_coverage(samples) == ["settings ['LS1', 'VB'] (VB and V0 needed)"]
    samples.append(sample("main", "V0", stored=False))
    assert ls.r8_coverage(samples) == []
    assert ls.r8_coverage(samples[1:])[0] == "main: 1 samples < 2"
    stored_rows = [{"file": "d", "source": "D-1", "status": "compared", "max_abs_N": 0.0}]
    rerun_rows = [{"label": "main/x", "source": "main", "status": "compared",
                   "rerun": {"status": "compared", "max_abs_N": 0.5},
                   "original": {"status": "compared", "max_abs_N": 30.0}}]
    verdict = ls.r8_verdict(stored_rows, rerun_rows, [])
    assert verdict["complete"] and verdict["mode"] == ls.MODE_BAND
    assert verdict["max_abs_N"] == 30.0 and verdict["by_source"]["main"]["max_abs_N"] == 30.0
    rerun_rows[0]["original"]["max_abs_N"] = 501.0
    assert ls.r8_verdict(stored_rows, rerun_rows, [])["stop_H9"]
    incomplete = ls.r8_verdict([], rerun_rows, [])
    assert not incomplete["complete"] and "(a)" in incomplete["problems"][0]
