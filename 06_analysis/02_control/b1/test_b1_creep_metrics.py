"""Unit tests of the B1 path 1 tool ``b1_creep_metrics.py`` (synthetic inputs only).

Covered: the 4.4 threshold forms at ``L +- 0.5e-9`` (same = inclusive side) and ``L +- 2e-9``,
the 4.5 integer periods and window ends, the empty-set rules (NA, E-6, bundle states, E-5), the
user decisions C-1 .. C-5, the 7.2 ``m_L`` and T-14, the 6 grid record and its fallback, D-f
cases and an end-to-end ``judge`` run on synthetic Chrono folders and harness records.

Run (python-dev): ``python -m pytest -q -p no:cacheprovider 06_analysis/02_control/b1``
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import b1_creep_metrics as bm  # noqa: E402

ROOT = HERE.parents[2]
YAML = ROOT / "02_params" / "rexome33.yaml"
SOIL_SETS = ROOT / "02_params" / "scm_soil_sets.json"
C2_FILE = ROOT / "03_src" / "outrigger_sim" / "control" / "c2.py"
HALF = 0.5e-9
TWO = 2e-9


@pytest.fixture(scope="module")
def geo() -> bm.Geometry:
    return bm.read_geometry(YAML, SOIL_SETS, C2_FILE)


# ------------------------------------------------------------------------- record builders
def make_record(*, n_count=40, s_max_leg=0, s_peak=0.60, n_peak=20, n_loc=10, n_ready=30,
                level="bottom", sink_step=1e-4, events=(), with_controller=True,
                run_id="R", source="harness") -> bm.RunRecord:
    """Strokes rise linearly to ``s_peak`` on ``s_max_leg`` at ``n_peak`` and stay below."""
    n = np.arange(n_count, dtype=np.int64)
    stroke = np.full((n_count, 4), 0.30)
    ramp = np.minimum(n, n_peak) / n_peak
    stroke[:, s_max_leg] = 0.30 + (s_peak - 0.30) * ramp
    sink = np.outer(n * sink_step, np.ones(4))
    ev = [(n_loc * 0.1, bm.EV_LOC), *events]
    rec = bm.RunRecord(run_id=run_id, source=source, level=level, n=n, stroke=stroke,
                       sink=sink, events=ev, t_ready_s=None if n_ready is None else n_ready * 0.1)
    if with_controller:
        rec.load = np.full((n_count, 4), 90_000.0)
        rec.att = np.zeros((n_count, 2))
        rec.c_hat = np.full(n_count, 0.05)
        rec.c_hat_corner = np.full((n_count, 4), 0.05)
        rec.c_target = np.full(n_count, 0.05)
    return rec


def grid_for(rec: bm.RunRecord, geo: bm.Geometry, n_contact: float, *, periods=None,
             residual: float = 0.0) -> bm.GridRecord:
    """A grid record with ``b_hull = b_poly`` and a law residual ``r_sigma = residual``."""
    periods = np.asarray(rec.n if periods is None else periods, dtype=np.int64)
    k = len(periods)
    area = np.tile(geo.pad_area_m2, (k, 1))
    perimeter = 2.0 * area / geo.pad_b_poly_m
    z = np.vstack([rec.sink[int(np.flatnonzero(rec.n == p)[0])] for p in periods])
    delta = 0.01
    law = n_contact * delta * delta * (geo.kc / geo.pad_b_poly_m + geo.kphi) * z ** geo.n_soil
    sigma = law / (1.0 - residual / geo.n_soil) if residual else law
    return bm.GridRecord(n=periods, n_contact=np.full((k, 4), float(n_contact)),
                         hull_area=area, hull_perimeter=perimeter, z_geo=z, sigma_sum=sigma,
                         grid_m=delta)


# ------------------------------------------------------------------------- 4.4 threshold forms
@pytest.mark.parametrize(("value", "expected"), [
    (0.003 + HALF, "0"), (0.003 + TWO, "+"), (-(0.003 + HALF), "0"), (-(0.003 + TWO), "-"),
    (0.0, "0")])
def test_t3_point_classes(value, expected) -> None:
    assert bm.classify_band(value, value, bm.HC_M) == expected


def test_t3_band_straddling_threshold_is_undetermined() -> None:
    assert bm.classify_band(0.002, 0.004, bm.HC_M) == "undetermined"
    assert bm.classify_band(0.003 + TWO, 0.009, bm.HC_M) == "+"
    assert bm.classify_band(-0.009, -0.003 - TWO, bm.HC_M) == "-"


def _da_chrono(raw: float, corr: float | None, rows=("C1",)) -> dict:
    out = {}
    for r in rows:
        out[r] = {"b_star": 0, "grid": {"dz_post_corr": [corr, None, None, None]},
                  "metrics": {"M-4": {"dz_post": [raw, 0.0, 0.0, 0.0], "z_R": [0.1, 0, 0, 0]}}}
    return out


def _da_harness(value: float, rows=("C1",)) -> dict:
    return {bm.harness_run_id("H-P", r, s, 0.0): {"M-4": {"dz_post": [value, 0.0, 0.0, 0.0]}}
            for r in rows for s in ("VB", "V0")}


@pytest.mark.parametrize(("excess", "expected"), [(HALF, "ZA-1"), (TWO, "ZA-2"),
                                                  (-HALF, "ZA-1")])
def test_t1_d_a_raw_threshold(excess, expected) -> None:
    grade = bm.grade_D_a(_da_chrono(0.010 + 0.003 + excess, None), _da_harness(0.010), ["C1"])
    assert grade["raw_grade"] == expected
    assert grade["grade"] == expected  # corr NA -> final = raw (C-5 (a))
    assert grade["corr_grade"] == bm.NA


def test_c5_raw_za2_corr_za1_gives_za2_with_raw_excess_correction() -> None:
    grade = bm.grade_D_a(_da_chrono(0.020, 0.011), _da_harness(0.010), ["C1"])
    assert (grade["raw_grade"], grade["corr_grade"], grade["grade"]) == ("ZA-2", "ZA-1", "ZA-2")
    assert grade["harness_correction_m"] == pytest.approx(0.010)
    assert "격자 몫 포함 보정" in grade["flags"] and "격자 위상 의존" in grade["flags"]


def test_c5_corr_za2_alone_still_gives_za2() -> None:
    grade = bm.grade_D_a(_da_chrono(0.011, 0.020), _da_harness(0.010), ["C1"])
    assert (grade["raw_grade"], grade["corr_grade"], grade["grade"]) == ("ZA-1", "ZA-2", "ZA-2")
    assert grade["harness_correction_m"] is None


def _db(own_os: float | None, pair_os: float | None) -> tuple[dict, dict]:
    chrono = {"C1": {"b_star": 0, "metrics": {"M-5": {
        "delta_os": None if own_os is None else [own_os, 0, 0, 0]}}}}
    harness = {bm.harness_run_id("H-P", "C1", "VB", 0.0): {"M-5": {
        "delta_os": None if pair_os is None else [pair_os, 0, 0, 0]}}}
    return chrono, harness


@pytest.mark.parametrize(("value", "expected"), [(0.005 + HALF, "OS-FINAL"),
                                                 (0.005 + TWO, "OS-MAX")])
def test_t2_d_b_threshold(value, expected) -> None:
    assert bm.grade_D_b(*_db(value, 0.0), ["C1"])["grade"] == expected
    assert bm.grade_D_b(*_db(0.0, value), ["C1"])["grade"] == expected


def test_d_b_row_without_ready_leaves_the_count_and_empty_set_is_na() -> None:
    grade = bm.grade_D_b(*_db(None, 0.030), ["C1"])
    assert grade["grade"] == bm.NA and grade["row_count"] == 0
    assert grade["dropped_no_ready"] == ["C1"]


def _dd(errors: dict[str, float], is_sgs=False, t14_ok=True) -> dict:
    full = {q: [errors.get(q), 0, 0, 0] for q in bm.PRED_ORDER}
    return {"C1": {"b_star": 0, "metrics": {
        "M-6": {"errors": full}, "is_sgs": is_sgs,
        "predictor_inputs": {"t14": {"ok": t14_ok}}}}}


@pytest.mark.parametrize(("value", "expected"), [(0.010 + HALF, "PRED-P-A"),
                                                 (0.010 + TWO, "PRED-FAIL")])
def test_t4_d_d_threshold(value, expected) -> None:
    errors = {"P-A": value, "P-B": 0.05, "P-D": 0.05, "P-C": 0.05}
    assert bm.grade_D_d(_dd(errors), ["C1"])["grade"] == expected


def test_t4_tie_within_eps_takes_the_simpler_candidate() -> None:
    errors = {"P-A": 0.004 + HALF, "P-B": 0.004, "P-D": 0.004, "P-C": 0.003}
    assert bm.grade_D_d(_dd(errors), ["C1"])["grade"] == "PRED-P-C"
    errors["P-C"] = 0.004 - HALF
    assert bm.grade_D_d(_dd(errors), ["C1"])["grade"] == "PRED-P-A"


def test_d_d_t14_mismatch_row_leaves_and_sgs_marks_lower_bound() -> None:
    errors = {"P-A": 0.001, "P-B": 0.001, "P-D": 0.001, "P-C": 0.001}
    assert bm.grade_D_d(_dd(errors, t14_ok=False), ["C1"])["grade"] == bm.NA
    graded = bm.grade_D_d(_dd(errors, is_sgs=True), ["C1"])
    assert "하한 포함" in graded["flags"]


def test_d_d_candidate_na_when_one_row_lacks_it() -> None:
    errors = {"P-A": 0.002, "P-B": None, "P-D": None, "P-C": None}
    graded = bm.grade_D_d(_dd(errors), ["C1"])
    assert graded["E_q"]["P-B"] == bm.NA and graded["grade"] == "PRED-P-A"


def _dg(e_c6: float, e_best: float) -> tuple[dict, dict]:
    chrono = {"C6": {"b_star": 0, "metrics": {"M-6": {"errors": {"P-A": [e_c6, 0, 0, 0]}},
                                               "is_sgs": False}}}
    d_d = {"grade": "PRED-P-A", "q_star": "P-A", "E_q": {"P-A": e_best}}
    return chrono, d_d


@pytest.mark.parametrize(("excess", "expected"), [(HALF, "W-OK"), (TWO, "W-EXT")])
def test_t6_d_g_threshold(excess, expected) -> None:
    chrono, d_d = _dg(0.004 + 0.005 + excess, 0.004)
    assert bm.grade_D_g(chrono, {"C6": "VALID"}, d_d)["grade"] == expected


def test_d_g_na_without_c6_or_after_pred_fail() -> None:
    chrono, d_d = _dg(0.001, 0.004)
    assert bm.grade_D_g(chrono, {"C6": "MISSING"}, d_d)["grade"] == bm.NA
    d_d["grade"] = "PRED-FAIL"
    assert bm.grade_D_g(chrono, {"C6": "VALID"}, d_d)["grade"] == "W-NA"


# ------------------------------------------------------------------------- D-e and C-3
def _de_rows(geo, g_values, *, valid_grid=True, z=0.1, sgs=False) -> tuple[dict, dict]:
    chrono, statuses = {}, {}
    for r, g in zip(bm.NEED_ROWS, g_values, strict=True):
        point = {"state": "valid", "delta_grid": 0.0} if valid_grid else {"state": "no_record"}
        chrono[r] = {"b_star": 0, "grid": {"points": {"max": [point, {}, {}, {}]}},
                     "metrics": {"M-2": {"g_m": g}, "M-4": {"z_max": [z, 0, 0, 0]},
                                 "is_sgs": sgs}}
        statuses[r] = "VALID"
    return chrono, statuses


def test_t5_d_e_threshold_with_valid_grid(geo) -> None:
    f_max = bm.F_PHASE_BAND[bm.FRONT][1]
    shift = 0.1 * (1.0 - 1.0 / f_max)
    chrono, statuses = _de_rows(geo, [0.020 + shift - HALF] * 3)
    assert bm.grade_D_e(chrono, statuses, geo)["grade"] == "NEED-RECHECK"
    chrono, statuses = _de_rows(geo, [0.020 + shift - TWO] * 3)
    assert bm.grade_D_e(chrono, statuses, geo)["grade"] == "B1-OPEN"


def test_c3_d_e_without_record_uses_the_band_width(geo) -> None:
    f_min, f_max = bm.F_PHASE_BAND[bm.FRONT]
    width = 0.1 * (f_max - f_min)
    chrono, statuses = _de_rows(geo, [0.020 + width] * 3, valid_grid=False)
    graded = bm.grade_D_e(chrono, statuses, geo)
    assert graded["grade"] == "NEED-RECHECK"
    assert graded["per_row"]["C1"]["g_tilde_m"] == pytest.approx(0.020, abs=1e-15)
    chrono, statuses = _de_rows(geo, [0.5] * 3, sgs=True)
    assert bm.grade_D_e(chrono, statuses, geo)["grade"] == "B1-OPEN"


# ------------------------------------------------------------------------- 4.5 periods, C-1
def test_event_time_rounds_to_integer_period() -> None:
    assert bm.period_index(12.299999999984673) == 123
    assert bm.period_index(12.3000000001) == 123


def test_series_lookup_takes_the_sample_at_tau() -> None:
    t = np.arange(0, 2.0005, 0.001)
    values = np.arange(len(t), dtype=float)[:, None] * np.ones((1, 4))
    assert bm.series_at(t, values, 10)[0] == 1000.0  # tau = 1.0 s -> sample 1000
    assert bm.series_at(t, values, 30) is None  # tau 3.0 s beyond the series


def test_t_max_first_period_of_the_maximum_within_eps() -> None:
    rec = make_record(n_peak=20)
    rec.stroke[25, 0] = rec.stroke[20, 0] + HALF  # same maximum within eps: earliest period
    timing = bm.run_timing(rec)
    assert timing.n_max == 20 and timing.b_star == 0
    rec.stroke[25, 0] = rec.stroke[20, 0] + TWO
    assert bm.run_timing(rec).n_max == 25


def test_c1_window_end_is_max_of_t_max_and_t_ready() -> None:
    rec = make_record(n_peak=20, n_ready=30, n_loc=10)
    timing = bm.run_timing(rec)
    assert timing.n_e == 30
    rows = bm.Rows(rec.n)
    sinks = bm.sink_metrics(rec, rows, timing)
    assert sinks["dz_post"][0] == pytest.approx((30 - 10) * 1e-4)
    assert sinks["dz_L_to_max"][0] == pytest.approx((20 - 10) * 1e-4)
    rec2 = make_record(n_peak=20, n_ready=None)
    assert bm.run_timing(rec2).n_e == 20


def test_c2_per_leg_window_uses_each_legs_maximum() -> None:
    rec = make_record(n_peak=20, n_ready=15)
    rec.stroke[:, 1] = 0.30 + 0.001 * np.minimum(rec.n, 35)  # FR max at period 35
    timing = bm.run_timing(rec)
    assert timing.n_max_leg[1] == 35 and timing.n_e_leg[1] == 35
    assert timing.n_e_leg[2] == 15  # flat leg: max at period 0, window end = t_R


def test_loc_last_and_revokes_counted() -> None:
    rec = make_record(n_loc=10, events=[(1.5, bm.EV_REVOKE + ":2.1"), (1.8, bm.EV_LOC)])
    timing = bm.run_timing(rec)
    assert (timing.n_L1, timing.n_L, timing.revokes) == (10, 18, 1)


# ------------------------------------------------------------------------- 7.2 m_L, T-14
def test_m_l_is_the_last_margin_event_up_to_the_last_loc() -> None:
    rec = make_record(n_loc=10, events=[(0.9, f"{bm.EV_E3C10}:80"),
                                        (1.5, f"{bm.EV_R4C30}:90")])
    assert bm.margin_at_loc(rec, 10)["m_L_m"] == pytest.approx(0.030)
    assert bm.margin_at_loc(rec, 15)["m_L_m"] == pytest.approx(0.040)
    plain = make_record()
    assert bm.margin_at_loc(plain, 10)["m_L_m"] == 0.0


def test_r4_skip_event_is_not_a_margin() -> None:
    assert bm.margin_event_mm(bm.EV_R4_SKIP) is None
    assert bm.margin_event_mm(f"{bm.EV_E3C10}:50") == 50


@pytest.mark.parametrize(("offset", "ok"), [(5e-4 - 1e-12, True), (5e-4 + 1e-9, False)])
def test_t14_rounding_tolerance(offset, ok) -> None:
    rec = make_record(events=[(0.5, f"{bm.EV_E3C10}:80")])
    rec.c_target[:] = 0.080 + offset
    check = bm.t14_check(rec, bm.Rows(rec.n), 10, 0.080)
    assert check["ok"] is ok


# ------------------------------------------------------------------------- predictors, C-2
def test_p_a_geometry_sign_and_clearance_lift(geo) -> None:
    rec = make_record(level="top")
    rec.att[:, 1] = 0.01  # nose down 10 mrad: front legs extend
    rec.c_hat[:] = 0.03
    inputs = bm.predictor_inputs(rec, bm.Rows(rec.n), bm.run_timing(rec), geo)
    preds, _ = bm.predictions(inputs, None, geo)
    expected = rec.stroke[10, 0] + geo.pad_xy_m[0, 0] * 0.01 + (0.05 - 0.03)
    assert preds["P-A"][0] == pytest.approx(expected)
    assert preds["P-B"][0] is None  # constants NA


def test_p_d_power_term_and_nonpositive_peak(geo) -> None:
    assert bm.power_term(1.0e5, 1.0e4) == pytest.approx(1.1e5 ** 5 - 1.0e5 ** 5)
    assert bm.power_term(1.0e5, -5.0) == 0.0
    assert bm.power_term(0.0, 1.0e4) is None


def _harness_runs(geo, kappas) -> dict:
    runs = {}
    for k, scale in enumerate(kappas):
        rec = make_record(level="bottom", sink_step=1e-4 * scale, run_id=f"H-P|C{k + 1}|VB|e0")
        rec.load[:] = geo.static_loads_N["bottom"] - 10_000.0
        runs[rec.run_id] = bm.HarnessRun({"run_id": rec.run_id}, rec)
    return runs


def test_c2_constants_kappa_c_type_and_ratio_flag(geo) -> None:
    runs = _harness_runs(geo, [1.0, 1.4])
    constants = bm.harness_constants(runs, geo)
    dz = (30 - 10) * 1e-4 * 1.4  # per-leg window end = t_R (flat legs) for the scaled run
    assert constants["kappa_z_m_per_N"][bm.REAR] == pytest.approx(dz / 10_000.0)
    assert constants["kappa_ratio"][bm.REAR]["kappa_nonlinear"] is False
    runs = _harness_runs(geo, [1.0, 1.6])
    assert bm.harness_constants(runs, geo)["kappa_ratio"][bm.REAR]["kappa_nonlinear"] is True
    # RR carries the smaller static load, so its power term is smaller and its C the largest
    term = bm.power_term(geo.static_loads_N["bottom"][3] - 10_000.0, 10_000.0)
    assert bm.harness_constants(runs, geo)["C_type"][bm.REAR] == pytest.approx(
        (30 - 10) * 1e-4 * 1.6 / term)


def test_e2_constants_na_without_loc(geo) -> None:
    rec = make_record(run_id="H-P|C1|VB|e0")
    rec.events = []
    constants = bm.harness_constants({rec.run_id: bm.HarnessRun({}, rec)}, geo)
    assert constants["kappa_z_m_per_N"][bm.FRONT] == bm.NA
    assert constants["excluded"]["no_loc_runs"] == [rec.run_id]
    clean = bm.constants_for_prediction(constants)
    assert clean["kappa_z_m_per_N"][bm.FRONT] is None


# ------------------------------------------------------------------------- 6 grid, C-4, C-5
def test_c4_grid_validity_band_boundaries(geo) -> None:
    rec = make_record()
    nominal = geo.pad_area_m2[0] / 1e-4
    for n_contact, expected in ((nominal, "valid"), (0.95 * nominal - 1e-10, "valid"),
                                (0.95 * nominal - 1e-6, "invalid"),
                                (1.05 * nominal + 1e-10, "valid"),
                                (1.05 * nominal + 1e-6, "invalid")):
        rec.grid = grid_for(rec, geo, n_contact)
        assert bm.grid_point(rec, geo, 0, 12)["state"] == expected, n_contact


def test_c4_law_residual_boundary(geo) -> None:
    rec = make_record()
    nominal = geo.pad_area_m2[0] / 1e-4
    rec.grid = grid_for(rec, geo, nominal, residual=0.005 * (1 - 1e-9))
    assert bm.grid_point(rec, geo, 0, 12)["check_ii"] is True
    rec.grid = grid_for(rec, geo, nominal, residual=0.00501)
    assert bm.grid_point(rec, geo, 0, 12)["check_ii"] is False


def test_c4_same_period_only(geo) -> None:
    rec = make_record()
    rec.grid = grid_for(rec, geo, geo.pad_area_m2[0] / 1e-4, periods=[9, 11])
    assert bm.grid_point(rec, geo, 0, 10)["state"] == "no_record"
    assert bm.grid_point(rec, geo, 0, 11)["state"] == "valid"


def test_grid_factor_one_at_nominal_contact(geo) -> None:
    rec = make_record()
    rec.grid = grid_for(rec, geo, geo.pad_area_m2[0] / 1e-4)
    assert bm.grid_point(rec, geo, 0, 12)["f"] == pytest.approx(1.0, abs=1e-12)


def test_c5_corrected_increment_needs_both_records(geo) -> None:
    rec = make_record(n_peak=20, n_ready=30)
    nominal = geo.pad_area_m2 / 1e-4
    rec.grid = grid_for(rec, geo, float(nominal[0]), periods=[10, 30])
    metrics = bm.run_metrics(rec, geo, None)
    grid = bm.grid_metrics(rec, metrics, geo)
    assert grid["dz_post_corr"][0] == pytest.approx((30 - 10) * 1e-4, abs=1e-15)
    assert grid["z_e_df_eL"][0] == pytest.approx(0.0, abs=1e-15)
    rec.grid = grid_for(rec, geo, float(nominal[0]), periods=[30])  # no t_L record
    grid = bm.grid_metrics(rec, metrics, geo)
    assert grid["dz_post_corr"][0] is None


def test_window_mode_record_off_window_is_no_record(geo) -> None:
    rec = make_record(n_count=60, n_peak=50, n_ready=55)
    rec.grid = grid_for(rec, geo, geo.pad_area_m2[0] / 1e-4, periods=[*range(0, 31), 40, 50])
    metrics = bm.run_metrics(rec, geo, None)
    grid = bm.grid_metrics(rec, metrics, geo)
    assert grid["points"]["R"][0]["state"] == "no_record"  # n_R 55 outside the windows
    assert grid["points"]["max"][0]["state"] == "valid"


def test_d_c_fallback_band_and_node_step(geo) -> None:
    chrono_row = {"b_star": 0, "grid": None, "metrics": {
        "M-2": {"s_max": [0.650, 0, 0, 0]}, "M-4": {"z_max": [0.095, 0, 0, 0]}}}
    pair = {"M-2": {"s_max": [0.640, 0, 0, 0]}}
    result = bm.d_c_row(chrono_row, pair, geo)
    f_min, f_max = bm.F_PHASE_BAND[bm.FRONT]
    assert result["corr_low_m"] == pytest.approx(0.010 - 0.095 * (1 - 1 / f_max))
    assert result["corr_high_m"] == pytest.approx(0.010 - 0.095 * (1 - 1 / f_min))
    assert "대체 범위" in result["flags"]
    assert result["corr_class"] == "+"
    chrono_row["grid"] = {"points": {"max": [{"state": "valid", "delta_grid": 0.0095,
                                               "dz_1n": 0.001}, {}, {}, {}]}}
    result = bm.d_c_row(chrono_row, pair, geo)
    assert result["corr_class"] == "0" and "절점 계단 수준" in result["flags"]


# ------------------------------------------------------------------------- empty sets
def test_grade_with_no_rows_is_na_and_self_check_catches_a_violation() -> None:
    assert bm._grade("D-x", [], grade="OS-MAX")["grade"] == bm.NA
    with pytest.raises(AssertionError):
        bm.self_check({"D-x": {"row_count": 0, "grade": "OS-MAX"}})


def _harness_pairs(rows) -> dict:
    return {bm.harness_run_id("H-P", r, "VB", 0.0): object() for r in rows}


def test_bundle_states() -> None:
    valid = dict.fromkeys(bm.CHRONO_ROWS, "VALID")
    assert bm.bundle_state(valid, _harness_pairs(bm.R_ROWS)) == "COMPLETE"
    assert bm.bundle_state({**valid, "C3": "MISSING"}, _harness_pairs(bm.R_ROWS)) == "PARTIAL"
    assert bm.bundle_state({**valid, "C6": "NO_LOC"}, _harness_pairs(bm.R_ROWS)) == "PARTIAL"
    assert bm.bundle_state({**valid, "C4": "INVALID"},
                           _harness_pairs(bm.R_ROWS)) == "UNDETERMINED"
    assert bm.bundle_state(valid, _harness_pairs(("C1", "C2", "C4", "C5"))) == "UNDETERMINED"


def test_d_f_cases() -> None:
    chrono = {"C5": {"metrics": {"is_sgs": True}}}
    statuses = {"C5": "VALID"}

    def harness(vb, v0):
        out = {}
        for setting, value in (("VB", vb), ("V0", v0)):
            if value is not None:
                out[bm.harness_run_id("H-M0", "C5", setting, 0.0)] = {
                    "is_sgs": value == "sgs", "has_ready": value == "ready",
                    "M-8": {"R4c30": [f"{bm.EV_R4C30}:80"] if value == "r4" else []}}
        return out

    assert bm.grade_D_f(chrono, statuses, {}, harness("sgs", "sgs"))["grade"] == "FUP-OUT"
    assert bm.grade_D_f(chrono, statuses, {}, harness("sgs", "ready"))["grade"] == "FUP-IN"
    graded = bm.grade_D_f(chrono, statuses, {}, harness("r4", "r4"))
    assert graded["grade"] == bm.NA and graded["row_count"] == 0  # E-3
    assert bm.grade_D_f({"C5": {"metrics": {"is_sgs": False}}}, statuses, {},
                        harness("sgs", "sgs"))["grade"] == "FUP-NA"
    # Q-4 (a): one pair left (the other R4c30 or absent / invalid by V-4)
    graded = bm.grade_D_f(chrono, statuses, {}, harness("r4", "sgs"))
    assert graded["grade"] == "FUP-OUT" and "짝 1개" in graded["flags"]
    graded = bm.grade_D_f(chrono, statuses, {}, harness(None, "ready"))
    assert graded["grade"] == "FUP-IN" and "짝 1개" in graded["flags"]


# ------------------------------------------------------------------------- P-G (R-3, Q-8)
def test_crawler_corners_from_the_c2_source(geo) -> None:
    corners = geo.crawler_corners_xy_m
    assert corners.shape == (4, 2)
    assert corners[0].tolist() == [-1.840, -1.366] and corners[3].tolist() == [1.844, 1.366]


def test_plane_fit_reproduces_a_plane_exactly(geo) -> None:
    a, b, c = 0.002, 0.003, -0.001
    pads = a + b * geo.pad_xy_m[:, 1] - c * geo.pad_xy_m[:, 0]
    corners = bm.plane_corner_values(geo.pad_xy_m, pads, geo.crawler_corners_xy_m)
    expected = a + b * geo.crawler_corners_xy_m[:, 1] - c * geo.crawler_corners_xy_m[:, 0]
    assert corners == pytest.approx(expected, abs=1e-15)


def _p_g_inputs(geo, *, pitch=0.01, roll=0.0, corners=(0.03, 0.04, 0.05, 0.06), m_l=0.03):
    rho = geo.crawler_corners_xy_m[:, 0] * pitch - geo.crawler_corners_xy_m[:, 1] * roll
    ds = geo.pad_xy_m[:, 0] * pitch - geo.pad_xy_m[:, 1] * roll
    return {"s_L": [0.40] * 4, "ds_geo": ds.tolist(), "c_hat_L_m": min(corners),
            "c_hat_corner_L_m": list(corners), "rho": rho.tolist(),
            "m_L": {"m_L_m": m_l}, "W_hat": [10_000.0] * 4, "F_pk": [80_000.0] * 4}


def test_p_g_formula(geo) -> None:
    constants = {"kappa_z_m_per_N": {bm.FRONT: 1e-6, bm.REAR: 2e-6},
                 "C_type": {bm.FRONT: 1e-27, bm.REAR: 2e-27}, "delta_allow_m": 0.004}
    inputs = _p_g_inputs(geo)
    preds, terms = bm.predictions(inputs, constants, geo)
    dz_hat = [constants["C_type"][bm.PAD_TYPE[i]] * bm.power_term(80_000.0, 10_000.0)
              for i in range(4)]
    z_hat = bm.plane_corner_values(geo.pad_xy_m, dz_hat, geo.crawler_corners_xy_m)
    total = np.array(inputs["c_hat_corner_L_m"]) + np.array(inputs["rho"]) + z_hat
    lift = max(0.05 + 0.03 - total.min(), 0.0)
    for i in range(4):
        assert preds["P-G"][i] == pytest.approx(0.40 + inputs["ds_geo"][i] + lift + dz_hat[i])
        assert preds["P-D"][i] == pytest.approx(preds["P-A"][i] + dz_hat[i])
    assert terms["k_star"] == int(np.argmin(total))
    assert preds["P-C"][0] == pytest.approx(preds["P-B"][0] + 0.004)


def test_p_g_clips_the_corner_lift_at_zero(geo) -> None:
    constants = {"kappa_z_m_per_N": {}, "C_type": {bm.FRONT: 0.0, bm.REAR: 0.0}}
    preds, terms = bm.predictions(_p_g_inputs(geo, pitch=0.0, corners=(0.2,) * 4), constants,
                                  geo)
    assert terms["lift_m"] == 0.0 and preds["P-G"][0] == pytest.approx(0.40)


def test_p_g_na_without_c_type_or_corners(geo) -> None:
    preds, terms = bm.predictions(_p_g_inputs(geo), {"C_type": {}}, geo)
    assert preds["P-G"] == [None] * 4 and terms is None
    inputs = _p_g_inputs(geo)
    inputs["c_hat_corner_L_m"] = None
    preds, _ = bm.predictions(inputs, {"C_type": {bm.FRONT: 1e-27, bm.REAR: 1e-27}}, geo)
    assert preds["P-G"] == [None] * 4 and preds["P-D"][0] is not None


@pytest.mark.parametrize(("value", "expected"), [(0.010 + HALF, "PRED-P-G"),
                                                 (0.010 + TWO, "PRED-FAIL")])
def test_t4_p_g_threshold_and_order(value, expected) -> None:
    errors = {"P-A": 0.05, "P-B": 0.05, "P-D": 0.05, "P-G": value, "P-C": value + HALF}
    assert bm.grade_D_d(_dd(errors), ["C1"])["grade"] == expected


def test_tie_p_d_before_p_g_before_p_c() -> None:
    errors = {"P-A": 0.05, "P-B": 0.05, "P-D": 0.004 + HALF, "P-G": 0.004, "P-C": 0.004}
    assert bm.grade_D_d(_dd(errors), ["C1"])["grade"] == "PRED-P-D"
    errors["P-D"] = 0.05
    assert bm.grade_D_d(_dd(errors), ["C1"])["grade"] == "PRED-P-G"


def test_p_a_limit_record_heave_and_epsilon(geo) -> None:
    rec = make_record(n_peak=20, n_ready=30, n_loc=10)
    rec.c_hat[30] = 0.0832
    metrics = bm.run_metrics(rec, geo, None)
    limit = metrics["p_a_limit"]
    expected_h = (rec.stroke[20] - rec.stroke[10]) - (rec.sink[20] - rec.sink[10])
    assert limit["h_max"]["legs_m"] == pytest.approx(expected_h.tolist())
    assert limit["epsilon_m"] == pytest.approx(0.0832 - 0.05)


# ------------------------------------------------------------------------- M-12 Chrono (Q-7)
def test_chrono_anchor_reconstruction_centred_tilt(geo) -> None:
    rec = make_record(n_count=60, n_loc=40, n_peak=50, n_ready=55)
    rec.imu = {"t_s": np.arange(0, 6.0, 0.01), "tilt": np.zeros((600, 2))}
    rec.imu["tilt"][(rec.imu["t_s"] > 3.4) & (rec.imu["t_s"] < 3.6), 1] = 0.002
    rec.att[35, 1] = 0.002  # single sample at t_P: tilted; the centred mean is smaller
    rec.c_hat_corner[:] = 0.03
    rec.soil_meta = {"t_P_s": 3.5, "clearance_at_P_m": 0.03, "settle_attitude_rad": [0.0, 0.0],
                     "settings": {"corner_bias_deadzone_m": 0.005, "loc_anchor_enable": False}}
    metrics = bm.run_metrics(rec, geo, None)
    shadow = bm.chrono_anchor_shadow(rec, metrics, geo)
    loc = shadow["locs"][0]
    assert loc["path"] == "1" and loc["window_half_s"] == pytest.approx(0.5)
    window = (rec.imu["t_s"] >= 3.0 - 1e-6) & (rec.imu["t_s"] <= 4.0 + 1e-6)
    centred = rec.imu["tilt"][window].mean(axis=0)
    corners = geo.crawler_corners_xy_m

    def bias(pitch):
        rise = -corners[:, 0] * pitch
        return np.maximum(0.03 - (rise - rise.min()), 0.0)

    expected = float(np.min(0.03 + bias(0.002) - bias(centred[1])))
    assert loc["c_hat_tL_shadow_mm"] == pytest.approx(expected * 1e3)
    rec.imu = None
    assert bm.chrono_anchor_shadow(rec, metrics, geo) is None


# ------------------------------------------------------------------------- end to end
def _write_npz(path: Path, **arrays) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, **arrays)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _chrono_case(batch: Path, row_id: str, geo: bm.Geometry) -> None:
    row = bm.CHRONO_ROWS[row_id]
    folder = batch / row.case
    n_count = int(round(row.duration_s / 0.1))
    t = np.arange(n_count) * 0.1
    leg = bm.LEGS.index(row.budget_leg)
    stroke = np.full((n_count, 4), 0.40)
    stroke[:, leg] = 0.40 + 0.2 * np.minimum(np.arange(n_count), 800) / 800
    _write_npz(folder / "record" / "record.npz", t=t, **{"meas.stroke": stroke})
    t_1ms = np.arange(0, n_count * 0.1 + 1e-9, 0.01)
    sink = np.outer(t_1ms * 1e-4, np.ones(4)) + 0.05
    _write_npz(folder / "step_series.npz", t_s=t_1ms, pad_sinkage_geometric_m=sink,
               scm_pad_normal_N=np.full((len(t_1ms), 4), 9e4),
               scm_crawler_normal_N=np.zeros(len(t_1ms)))
    n = np.arange(n_count, dtype=np.int64)
    loads = np.tile(geo.static_loads_N[row.level] - 5_000.0, (n_count, 1))
    z_10 = np.outer(n * 0.1 * 1e-4, np.ones(4)) + 0.05
    grid = _grid_fields(geo, z_10)
    imu_t = np.arange(0, n_count * 0.1, 0.01)
    pad_xy = np.tile(geo.pad_xy_m, (n_count, 1, 1))
    _write_npz(folder / bm.CHRONO_B1_RECORD, n=n, n_cycle=n.copy(), t_s=n * 0.1,
               computed=np.ones(n_count, dtype=bool), load_read_N=loads,
               att_raw_rad=np.zeros((n_count, 2)), c_hat_m=np.full(n_count, 0.06),
               c_hat_corner_m=np.full((n_count, 4), 0.06), c_target_m=np.full(n_count, 0.05),
               pad_bottom_centre_plane_xy_m=pad_xy,
               pad_yaw_plane_rad=np.full((n_count, 4), 0.3),
               imu_n_cycle=(imu_t / 0.1).astype(np.int64), imu_t_s=imu_t,
               imu_raw_roll_rad=np.zeros(len(imu_t)), imu_raw_pitch_rad=np.zeros(len(imu_t)),
               imu_specific_force_m_s2=np.zeros((len(imu_t), 3)), **grid)
    s9_rows = [{"t_s": k * 0.1, "pad_nodes": [
        {name: float(grid[name][k, i]) for name in bm.PAD_NODES_FIELDS} for i in range(4)]}
        for k in (0, 300, 800)]
    result = {
        "s9_rows": s9_rows,
        "events": [{"t_s": 30.0, "name": bm.EV_LOC}],
        "p3b": {"P3-5_clearance_stroke": {"t_first_ready_s": 100.0},
                "P3-2_loc": {"t_departure_s": 29.0}, "creep_stop": {"t_final_s": 110.0},
                "weight_N": 4e5},
        "args": {"expect_controller": bm.CTRL_TAG_VB,
                 "mass_scale": bm.C6_MASS_SCALE if row_id == "C6" else 1.0},
        "c2_setup": {"expect_controller": {"name": bm.CTRL_TAG_VB, "ok": True}},
        "num_threads_chrono": 4, "meta": {"scm": {"grid_m": 0.01}},
        "hull_hook": {"mode": "fast", "requested": "fast", "dll_sha256": bm.HULL_DLL_SHA},
        "c2_soil": {"W_ref_N": geo.superstructure_mass_kg[row.level] * 9.80665,
                    "t_P_s": 29.0, "clearance_at_P_m": 0.0, "settle_attitude_rad": [0.0, 0.0],
                    "bias_corner_m": [0.0] * 4,
                    "settings": {"corner_bias_deadzone_m": 0.005, "loc_anchor_enable": False}},
        "controller_meta": {"slope_clearance_margin": {"clearance_target_m": 0.05}},
        "final_phase": "ready"}
    (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")


def _grid_fields(geo: bm.Geometry, z: np.ndarray) -> dict[str, np.ndarray]:
    """R-G1 arrays (n, 4) of full contact (``N_h = A / Delta^2``, ``b_hull = b_poly``: f = 1)."""
    count = len(z)
    area = np.tile(geo.pad_area_m2, (count, 1))
    n_contact = np.rint(area / 1e-4)
    law = n_contact * 1e-4 * (geo.kc / geo.pad_b_poly_m + geo.kphi) * z ** geo.n_soil
    return {"n_inside": n_contact.astype(np.int64), "n_contact": n_contact.astype(np.int64),
            "n_sigma_negative": np.zeros((count, 4), dtype=np.int64),
            "contact_hull_area_m2": n_contact * 1e-4,
            "contact_hull_perimeter_m": 2.0 * n_contact * 1e-4 / geo.pad_b_poly_m,
            "sinkage_geometric_m": z, "sigma_sum_area_N": law,
            "sinkage_mean_contact_m": z.copy()}


def _harness_files(folder: Path, geo: bm.Geometry, run_ids: list[str]) -> Path:
    lines = []
    for run_id in run_ids:
        group, row_id, setting, eps_text = run_id.split("|")
        level = bm.CHRONO_ROWS[row_id].level
        n_count = 1200
        n = np.arange(n_count, dtype=np.int64)
        stroke = np.full((n_count, 4), 0.40)
        stroke[:, 0] = 0.40 + 0.19 * np.minimum(n, 800) / 800
        sha = _write_npz(folder / "npz" / f"{run_id.replace('|', '_')}.npz", n=n,
                         t_s=n * 0.1, stroke_read_m=stroke,
                         sink_m=np.outer(n * 1e-5, np.ones(4)) + 0.05,
                         load_read_N=np.tile(geo.static_loads_N[level] - 5_000.0, (n_count, 1)),
                         att_raw_rad=np.zeros((n_count, 2)), c_hat_m=np.full(n_count, 0.06),
                         c_hat_corner_m=np.full((n_count, 4), 0.06),
                         c_target_m=np.full(n_count, 0.05))
        lines.append({"run_id": run_id, "group": group, "row_id": row_id, "setting": setting,
                      "eps": float(eps_text[1:]), "level": level, "error": None,
                      "controller": {"clearance_target_final_m": 0.05},
                      "controller_tag": bm._expected_tag(setting),
                      "npz": f"npz/{run_id.replace('|', '_')}.npz", "npz_sha256": sha,
                      "events": [[30.0, bm.EV_LOC]], "t_first_ready_s": 95.0,
                      "commands_sha256": "h-" + row_id, "d1_key": f"D1|H-S-0|J2|{row_id}",
                      "loc_shadow": None})
    path = folder / "b1_H.jsonl"
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


def _all_harness_ids() -> list[str]:
    ids = [bm.harness_run_id("H-P", r, s, e) for r in bm.R_ROWS for s in ("VB", "V0")
           for e in (0.0, 2e-3)]
    ids += [bm.harness_run_id("H-W", "C6", s, e) for s in ("VB", "V0") for e in (0.0, 2e-3)]
    ids += [bm.harness_run_id("H-M0", r, s, 0.0) for r in ("C1", "C5") for s in ("VB", "V0")]
    ids += [bm.harness_run_id("H-SH0", r, "VB", 0.0) for r in ("C1", "C2", "C4", "C5")]
    return ids


def _identity(errors_left: int = 0) -> dict:
    return {"rows": {r: {"ok": True, "rc": 0} for r in bm.CHRONO_ROWS},
            "runner_log": {"errors_total": errors_left, "errors_left": errors_left}}


@pytest.fixture()
def e2e(tmp_path, geo) -> dict:
    batch = tmp_path / "batch"
    for row_id in bm.CHRONO_ROWS:
        _chrono_case(batch, row_id, geo)
    harness = _harness_files(tmp_path / "harness", geo, _all_harness_ids())
    identity = tmp_path / "identity.json"
    identity.write_text(json.dumps(_identity()), encoding="utf-8")
    return {"batch": batch, "harness": harness, "identity": identity, "tmp": tmp_path}


def _judge(e2e, **extra) -> tuple[int, dict]:
    out = e2e["tmp"] / "metrics.json"
    argv = ["judge", "--chrono-batch", str(e2e["batch"]), "--harness", str(e2e["harness"]),
            "--identity", str(extra.get("identity", e2e["identity"])), "--out", str(out)]
    code = bm.main(argv)
    return code, json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}


def test_e2e_complete_bundle_grades_every_code(e2e) -> None:
    code, data = _judge(e2e)
    assert code == bm.EXIT_OK
    assert data["bundle"] == "COMPLETE"
    assert set(data["grades"]) == {"D-a", "D-b", "D-c", "D-d", "D-e", "D-f", "D-g", "D-h"}
    assert data["grades"]["D-h"]["grade"] == bm.NA  # no P7_REF given
    assert data["grades"]["D-a"]["row_count"] == 5
    assert data["rows"]["C1"]["metrics"]["M-1"]["n_L"] == 300


def test_e2e_missing_core_row_is_undetermined(e2e) -> None:
    (e2e["batch"] / bm.CHRONO_ROWS["C2"].case / "result.json").unlink()
    code, data = _judge(e2e)
    assert code == bm.EXIT_FOUND and data["bundle"] == "UNDETERMINED"
    assert data["row_states"]["C2"]["status"] == "MISSING"
    assert all(g["grade"] == bm.NA for g in data["grades"].values())


def test_e2e_runner_errors_left_block(e2e) -> None:
    identity = e2e["tmp"] / "identity_e5.json"
    identity.write_text(json.dumps(_identity(errors_left=1)), encoding="utf-8")
    code, data = _judge(e2e, identity=identity)
    assert code == bm.EXIT_FOUND and data["blocked"] == ["E-5"]


def test_e2e_identity_failure_makes_the_row_invalid(e2e) -> None:
    identity = _identity()
    identity["rows"]["C3"]["ok"] = False
    path = e2e["tmp"] / "identity_c3.json"
    path.write_text(json.dumps(identity), encoding="utf-8")
    code, data = _judge(e2e, identity=path)
    assert code == bm.EXIT_OK and data["bundle"] == "PARTIAL"
    assert data["row_states"]["C3"]["status"] == "INVALID"
    for code_name in ("D-a", "D-b", "D-c", "D-d"):  # rules 3.2: every grade on R
        assert "PARTIAL (C3)" in data["grades"][code_name]["flags"], code_name
    assert "PARTIAL (C3)" not in data["grades"]["D-e"]["flags"]


def test_e2e_grid_record_read_and_f_one(e2e) -> None:
    _, data = _judge(e2e)
    row = data["rows"]["C1"]
    assert row["pad_nodes_check"]["consistent"] is True
    assert row["pad_nodes_check"]["compared"] > 0
    point = row["grid"]["points"]["max"][0]
    assert point["state"] == "valid" and point["f"] == pytest.approx(1.0, abs=1e-9)
    assert row["shadow"]["locs"][0]["diff_tL_mm"] == pytest.approx(0.0, abs=1e-9)


def test_e2e_cad_keys_m4h_and_imu(e2e) -> None:
    _, data = _judge(e2e)
    row = data["rows"]["C1"]
    assert row["metrics"]["M-4h"]["xy_shift_m"] == [0.0] * 4
    assert row["metrics"]["M-4h"]["yaw_change_rad"] == [0.0] * 4  # initial yaw 0.3 cancels
    assert row["shadow"]["locs"][0]["window_samples"] > 0


def _rewrite_npz(path: Path, **changes) -> None:
    with np.load(path, allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    for key, value in changes.items():
        if value is None:
            arrays.pop(key)
        else:
            arrays[key] = value
    np.savez(path, **arrays)


def test_e2e_not_computed_period_has_no_grid_record(e2e) -> None:
    path = e2e["batch"] / bm.CHRONO_ROWS["C1"].case / bm.CHRONO_B1_RECORD
    with np.load(path, allow_pickle=False) as data:
        computed = data["computed"].copy()
    computed[800] = False  # t_max of the synthetic rows
    _rewrite_npz(path, computed=computed)
    _, data = _judge(e2e)
    assert data["rows"]["C1"]["grid"]["points"]["max"][0]["state"] == "no_record"
    assert data["rows"]["C1"]["pad_nodes_check"]["consistent"] is True


def test_e2e_missing_r_c1_makes_d_d_na_with_the_row_named(e2e) -> None:
    path = e2e["batch"] / bm.CHRONO_ROWS["C2"].case / bm.CHRONO_B1_RECORD
    _rewrite_npz(path, att_raw_rad=None)
    _, data = _judge(e2e)
    grade = data["grades"]["D-d"]
    assert grade["grade"] == bm.NA
    assert any(flag.startswith("R-C1 없음") and "C2" in flag for flag in grade["flags"])
    assert data["row_states"]["C2"]["status"] == "VALID"  # rules 6: not INVALID


def test_e2e_pad_nodes_mismatch_invalidates_the_grid_record(e2e) -> None:
    path = e2e["batch"] / bm.CHRONO_ROWS["C1"].case / "result.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    result["s9_rows"][1]["pad_nodes"][0]["n_contact"] += 1.0
    path.write_text(json.dumps(result), encoding="utf-8")
    _, data = _judge(e2e)
    row = data["rows"]["C1"]
    assert row["pad_nodes_check"]["consistent"] is False and row["grid"] is None
    assert data["rows"]["C2"]["grid"] is not None


def test_e2e_harness_tag_mismatch_is_refused(e2e) -> None:
    lines = [json.loads(t) for t in e2e["harness"].read_text(encoding="utf-8").splitlines()]
    for line in lines:
        if line["run_id"] == bm.harness_run_id("H-P", "C3", "VB", 0.0):
            line["controller_tag"] = "final_C4G2_P3_LAS"
    e2e["harness"].write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")
    code, data = _judge(e2e)
    assert data["bundle"] == "UNDETERMINED"  # E-1: an H-P VB e0 pair is missing
    assert any("E-1" in r["reason"] for r in data["harness_refused"])


def test_constants_subcommand_and_file_check(e2e) -> None:
    out = e2e["tmp"] / "constants.json"
    assert bm.main(["constants", "--harness", str(e2e["harness"]), "--out", str(out)]) == 0
    code, _ = _judge(e2e)
    assert code == bm.EXIT_OK
    data = json.loads(out.read_text(encoding="utf-8"))
    data["delta_allow_m"] = 1.0
    out.write_text(json.dumps(data), encoding="utf-8")
    argv = ["judge", "--chrono-batch", str(e2e["batch"]), "--harness", str(e2e["harness"]),
            "--identity", str(e2e["identity"]), "--constants", str(out),
            "--out", str(e2e["tmp"] / "m2.json")]
    assert bm.main(argv) == bm.EXIT_INPUT


def test_input_error_exit_code(tmp_path) -> None:
    argv = ["constants", "--harness", str(tmp_path / "absent.jsonl"),
            "--out", str(tmp_path / "c.json")]
    assert bm.main(argv) == bm.EXIT_INPUT
