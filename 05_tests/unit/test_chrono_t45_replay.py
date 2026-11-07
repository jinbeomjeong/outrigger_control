"""v5 stage 3 R-4 / R-6 tools (``stage3_impl_spec.md`` 1 R-4, 2): ``chrono_lock_window`` and
``chrono_t45_replay`` (criteria rev. 6 4-7).

Synthetic checks run everywhere; the stored Chrono records (``07_results``, git-ignored) are
skipped when absent: T4-0 on a V0 record (spec #7 (b)) and the copied-state T5 against a full
replay (spec #5).
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
V0_RECORD = (PROJECT_ROOT / "07_results" / "S8" / "final_G1L_RE1bF_FL_top_Fs0_20261106_110152"
             / "G1L_RE1bF_FL_top_Fs0")
"""FINAL C4G2 rigid V0 row (stored, not a stage 3 record)."""
VB_RECORD = (PROJECT_ROOT / "07_results" / "S8" / "probe_rigid_vb_20261106_162854"
             / "K24_top_fdown3.5_Fs4")
"""VB cost probe (M2 r3 + LC + controller window), stored."""
VB_STAGE3_RECORD = (PROJECT_ROOT / "07_results" / "S8" / "v5s3_VB_E_G4_Fs4_20261107_194230"
                    / "E_G4_Fs4")
"""Stage 3 VB event row (M2 r5, ``hydraulics_record`` with ``m2_releases``), stored."""
WEIGHT_N = 376.7e3
STAGE3_RESULTS = PROJECT_ROOT / "07_results" / "S8"
"""Case folders of batch ``V5-STAGE3_20261107_184341`` (``v5s3_<setting>_<case>_<stamp>``)."""
STAGE3_ROW_COUNT = 23
STAGE3_T45_ROWS = {
    "VB": ("K0V_top_fup3.5_Fs0", "K0_top_fup3.2_Fs0", "K0V_top_roll5.5_Fs0",
           "K0_top_fdown3.2_Fs0", "K0V_top_fdown3.5_Fs0", "E_G4_Fs8", "K0_top_rpBop_Fs0",
           "E_RE1bF_Fs0", "E_RE1bF_Fs8", "K8_top_rpB_Fs8", "S_top_fdown3.5_wika_Fs8",
           "K8_top_fdown3.5_Fs8"),
    "LS1": ("K0V_top_fup3.5_Fs0", "E_G4_Fs8", "E_RE1bF_Fs8"),
    "LS4": ("K0V_top_fup3.5_Fs0", "E_G4_Fs8", "E_RE1bF_Fs8")}
"""The 18 T4 / T5 rows of the stage 3 judgement (criteria rev. 7 5: VB 12 + LS 6)."""
REV7_REFERENCE = (PROJECT_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "rev7_ref"
                  / "h7_exclusion_v2.json")


def _stage3_case(setting: str, case: str) -> Path:
    folders = sorted(STAGE3_RESULTS.glob(f"v5s3_{setting}_{case}_2*"))
    assert len(folders) == 1, (setting, case, folders)
    return folders[0] / case


@pytest.fixture(scope="module")
def t45():
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        yield importlib.import_module("chrono_t45_replay")
    finally:
        sys.path.remove(str(COUPLED_DIR))


@pytest.fixture(scope="module")
def lock_window():
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        yield importlib.import_module("chrono_lock_window")
    finally:
        sys.path.remove(str(COUPLED_DIR))


def test_c_samples_outside_the_alignment_tolerance_have_no_truth(t45) -> None:
    """Spec #7 (c): ``j = searchsorted(t_pads, t_k - 1e-9)``, truth only within 0.5 ms."""
    t_pads = np.array([0.0, 1.0e-3, 2.0e-3, 3.0e-3])
    t_s = np.array([1.0e-3, 2.0e-3 - 0.4e-3, 3.0e-3 + 0.6e-3, 2.0e-3 + 1e-10])
    index, has_truth = t45.align_truth(t_pads, t_s)
    assert index.tolist() == [1, 2, 3, 2]
    assert has_truth.tolist() == [True, True, False, True]


def test_command_free_stretches(t45) -> None:
    acting = np.array([0.0, 0.0, 1.0, 0.0, -1.0, 0.0, 0.0])
    assert t45.command_free_stretches(acting) == [(0, 1), (3, 3), (5, 6)]


def test_r4_lock_events_from_the_law_state(lock_window) -> None:
    """Criteria rev. 6 6: 0 -> 1 / 1 -> 0 transitions; -1 (no armed law) reads as locked."""
    t_s = np.array([0.0, 0.001, 0.002, 0.003, 0.004])
    law = np.array([[-1, 0, 1, 1], [-1, 0, 1, 1], [1, 0, 0, 1], [1, 1, 0, 1], [0, 1, 1, 1]])
    events = lock_window.lock_events_from_law_state(t_s, law)
    assert events == [(0.0, 1, False), (0.002, 2, False), (0.003, 1, True), (0.004, 0, False),
                      (0.004, 2, True)]


def test_lift_times_first_sample_contacts_and_sustained(t45) -> None:
    """D-a: first ``<= 0`` after the pre-lift phases; a brief re-contact is counted and the
    sustained time follows the last sample above 0.01 W."""
    t_ms = np.arange(0.0, 3.0, 1e-3)
    normal = np.where(t_ms < 2.0, 50.0e3, 0.0)
    normal[(t_ms >= 2.2) & (t_ms < 2.205)] = 5.0e3  # above 0.01 W for 5 ms
    period_t = np.arange(0.1, 3.05, 0.1)
    period_phase = np.where(period_t < 0.5, "touch", "level")
    record = t45.lift_times(t_ms, normal, period_t, period_phase, WEIGHT_N)
    assert record["t_lift_s"] == pytest.approx(2.0)
    assert record["relift_contacts"]["samples"] == 5
    assert record["relift_contacts"]["max_N"] == 5.0e3
    assert record["t_lift_sus_s"] == pytest.approx(2.205)
    assert record["false_liftoff"] is False


def test_lift_times_ignore_a_pre_lift_phase_and_flag_a_false_liftoff(t45) -> None:
    t_ms = np.arange(0.0, 3.0, 1e-3)
    normal = np.where((t_ms < 0.3) | ((t_ms >= 1.0) & (t_ms < 2.0)), 0.0, 50.0e3)
    normal[t_ms >= 2.5] = 0.0
    period_t = np.arange(0.1, 3.05, 0.1)
    period_phase = np.where(period_t < 0.5, "check", "level")
    record = t45.lift_times(t_ms, normal, period_t, period_phase, WEIGHT_N)
    assert record["t_lift_s"] == pytest.approx(1.0)  # the zero in "check" does not count
    assert record["false_liftoff"] is True
    assert record["t_lift_sus_s"] == pytest.approx(2.5)


def test_bracket_10hz_split_time(t45) -> None:
    t_s = np.array([27.2, 27.3, 27.4, 27.5])
    record = t45.bracket_lift_10hz(t_s, np.array([60e3, 41.3e3, 0.0, 0.0]),
                                   np.array(["level"] * 4))
    assert record["t_a_s"] == 27.3 and record["t_b_s"] == 27.4
    assert record["t_lift_s"] == pytest.approx(27.301)


def test_ext_lock_counters_from_released_locks(t45) -> None:
    """Criteria rev. 6 4.5: an anchor equal to ``p_ret`` is a retract lock; the others count
    with ``p_r0 - p_ext``."""
    rod_side = SimpleNamespace(
        p_r0_after_extend_Pa=(2.0e5,) * 4, p_r0_after_retract_Pa=(34.818e5, 34.352e5,
                                                                 31.193e5, 30.591e5),
        p_floor_abs_Pa=1.0e4, annulus_area_m2=(3.76991118e-3,) * 2 + (3.14159265e-3,) * 2,
        rod_dead_length_m=(0.05,) * 4, stroke_m=0.70)
    params = SimpleNamespace(l2b=SimpleNamespace(
        rod_side=rod_side, actuator=SimpleNamespace(oil_bulk_modulus_eff_Pa=1.0e9)))
    releases = [{"leg": 0, "p_r0_Pa": 34.818e5, "s_ref_rel_m": 0.3, "k_h_at_rel_N_m": 4e7},
                {"leg": 0, "p_r0_Pa": 14.0e5, "s_ref_rel_m": 0.3, "k_h_at_rel_N_m": 4e7},
                {"leg": 2, "p_r0_Pa": 2.05e5, "s_ref_rel_m": 0.3, "k_h_at_rel_N_m": 3e7}]
    record = t45.ext_lock_counters({"m2_releases": releases}, params)
    assert record["ext_lock_count"] == [1, 0, 1, 0]
    assert record["ext_lock_excess_count"] == [1, 0, 0, 0]
    assert record["ext_lock_risk_count"] == [1, 0, 0, 0]
    assert record["ext_lock_excess_max_bar"][0] == pytest.approx(12.0)
    k_r = 1.0e9 * 3.76991118e-3 / (0.05 + 0.70 - 0.3)
    knee = (14.0e5 - (1.0e4 - 101325.0)) * 3.76991118e-3 * (4e7 + k_r) / k_r / 1e3
    assert record["ext_lock_knee_max_kN"][0] == pytest.approx(knee, rel=1e-12)


def test_m2_records_read_beta_from_the_loaded_l2b_params(t45) -> None:
    """Regression (stage 3 judgement 2026-11-07): ``beta`` is ``params.l2b.actuator``, not the
    L1 ``params.actuator`` (AttributeError on every row with a ``hydraulics_record``)."""
    from outrigger_sim.params import load_params

    params = load_params(level="top", model="L2b_NSC")
    assert not hasattr(params.actuator, "oil_bulk_modulus_eff_Pa")
    releases = [{"leg": 0, "p_r0_Pa": 14.0e5, "s_ref_rel_m": 0.3, "k_h_at_rel_N_m": 4e7}]
    record = t45.ext_lock_counters({"m2_releases": releases}, params)
    assert record["ext_lock_count"] == [1, 0, 0, 0]
    assert t45.release_judgements({"m2_releases": []}, params, (0.0133,) * 4) == {
        "releases": [], "flags": []}


@pytest.mark.skipif(not VB_STAGE3_RECORD.is_dir(), reason="stored stage 3 VB record not present")
def test_replay_case_of_a_stage3_vb_record_with_m2_records(t45) -> None:
    """A stage 3 VB row with ``hydraulics_record`` replays to the end; the values equal
    control-expert's work-around run (``s3_t45_records.json``, 2026-11-07)."""
    row = t45.replay_case(VB_STAGE3_RECORD)
    assert row["settings_equal"] and row["t4_0"]
    assert row["T4"]["over_0p6kN"] == 0
    ext_lock = row["ext_lock"]
    assert ext_lock["ext_lock_count"] == [6, 8, 8, 8]
    assert ext_lock["ext_lock_risk_count"] == [0, 0, 0, 0]
    assert ext_lock["ext_lock_knee_max_kN"] == pytest.approx(
        [59.100620627354026, 59.100620627354026, 42.44353503099572, 42.44353503099572],
        rel=1e-12)
    judgement = row["m2_release_judgement"]
    assert len(judgement["releases"]) == 42 and judgement["flags"] == []


@pytest.mark.skipif(not V0_RECORD.is_dir(), reason="stored V0 Chrono record not present")
def test_b_t4_0_on_a_stored_v0_record(t45) -> None:
    """Spec #7 (b): the settings rebuild and the replay with the run's events reproduce the
    recorded lower reading; T4 runs on it."""
    row = t45.replay_case(V0_RECORD)
    assert row["settings_equal"], row["setting_differences"]
    assert row["t4_0"] and row["max_relative_difference"] <= 1e-12
    assert row["lift"]["t_lift_basis"] == "bracket_10Hz"
    assert row["lift"]["t_a_s"] == pytest.approx(27.3, abs=1e-6)  # dynamics-expert D-a
    assert set(row["T4"]["legs"]) == {"FL", "FR", "RL", "RR"}


@pytest.mark.skipif(not VB_RECORD.is_dir(), reason="stored VB Chrono record not present")
def test_t5_copied_state_equals_a_full_replay(t45) -> None:
    """Spec #5: the T5 start from a copied monitor state equals a full replay with that leg
    forced at the start."""
    record = t45.load_case(VB_RECORD)
    check = t45.t5_naive_check(record, samples=3)
    assert check["compared"] == 3
    assert check["max_abs_difference_N"] == 0.0


@pytest.mark.skipif(not VB_RECORD.is_dir(), reason="stored VB Chrono record not present")
def test_r4_lock_window_of_a_stored_vb_record(lock_window) -> None:
    record = lock_window.chrono_lock_window_alignment(VB_RECORD)
    assert record["n_late_fallback"] == 0
    assert sum(record["judged_by_leg"].values()) > 0


# ------------------------------------------------------------------- criteria rev. 7 (3)
def test_rev7_e5_reads_the_last_nonzero_command_before_the_row(t45) -> None:
    """E5: the last nonzero acting command before ``k`` (not ``k`` itself) is a retraction."""
    acting = np.array([[0.0], [-1.0], [0.0], [0.0], [2.0], [0.0], [-3.0]])
    retraction = t45.last_motion_was_retraction(acting)
    assert retraction[:, 0].tolist() == [False, False, True, True, True, False, False]


def test_rev7_sensor_model_row_key(t45) -> None:
    """3.3: ``settings.bundle_c.sensor_model``; a missing key (or the top level) is false."""
    assert t45.is_sensor_model_row({"settings": {"bundle_c": {"sensor_model": True}}})
    assert not t45.is_sensor_model_row({"settings": {"bundle_c": {"sensor_model": False}}})
    assert not t45.is_sensor_model_row({"settings": {}})
    assert not t45.is_sensor_model_row({"bundle_c": {"sensor_model": True}})


def test_rev7_guard_keeps_e_samples_with_a_nonnegative_forced_lower(t45) -> None:
    """3.2: an E sample leaves only below 0 kN; the others stay judged and are counted."""
    candidate = np.array([True, True, True, False])
    lower = np.array([-4.5e3, 0.0, np.nan, -9.0e3])
    excluded, violations = t45.guarded_exclusion(candidate, lower)
    assert excluded.tolist() == [True, False, False, False]
    assert violations.tolist() == [False, True, True, False]


def test_rev7_b1_own_excess(t45) -> None:
    """3.3: equals the raw excess where the plain path is not optimistic."""
    raw = np.array([1.0e3, 1.0e3, 0.2e3])
    plain = np.array([-0.5e3, 0.7e3, 0.9e3])
    assert t45.own_excess_N(raw, plain).tolist() == [1.0e3, 0.3e3, -0.7e3]


@pytest.mark.slow
@pytest.mark.skipif(not STAGE3_RESULTS.is_dir() or not any(STAGE3_RESULTS.glob("v5s3_*")),
                    reason="stored stage 3 records not present")
def test_rev7_regression_on_the_stage3_records(t45) -> None:
    """Criteria rev. 7 4 / 5: the 18 stored stage 3 rows give the sealed reference values
    (``rev7_ref/h7_exclusion_v2.json``, off path); T5 runs on the F_s 8 rows (the only rows
    with T5 excess under rev. 6). The guard is 3.2 (forced lower < 0), not ``guard_bad``."""
    folders = sorted(path for path in STAGE3_RESULTS.glob("v5s3_*/*")
                     if (path / "result.json").is_file())
    assert len(folders) == STAGE3_ROW_COUNT
    sensor_rows = [folder.name for folder in folders if t45.is_sensor_model_row(
        json.loads((folder / "result.json").read_text(encoding="utf-8")))]
    assert sensor_rows == ["S_top_fdown3.5_wika_Fs8"]

    reference = {(row["setting"], row["case"]): row["off"] for row in json.loads(
        REV7_REFERENCE.read_text(encoding="utf-8"))["rows"]}
    rows = []
    for setting, cases in STAGE3_T45_ROWS.items():
        for case in cases:
            row = t45.replay_case(_stage3_case(setting, case), with_t5="Fs8" in case,
                                  criteria=t45.CRITERIA_REV7)
            assert row["settings_equal"] and row["t4_0"], (setting, case)
            expected, t4 = reference[(setting, case)], row["T4"]
            assert t4["judged_samples_rev6"] == expected["T4_before"]["n"], (setting, case)
            assert t4["judged_samples"] == expected["T4_after"]["n"], (setting, case)
            assert t4["e_excluded"] == expected["excluded"], (setting, case)
            assert t4["e1_to_e4_samples"] == expected["excluded_no_E5"], (setting, case)
            assert t4["over_0p6kN_rev6"] == expected["T4_before"]["over"], (setting, case)
            assert t4["raw_over_0p6kN"] == expected["T4_after"]["over"], (setting, case)
            rows.append(row)

    totals = t45.rev7_summary(rows)
    assert totals["T4_judged_samples_rev6"] == 26_380
    assert totals["T4_judged_samples"] == 26_210
    assert totals["T4_e_excluded"] == 170
    assert totals["T4_e1_to_e4_samples"] == 386
    assert totals["T4_over_0p6kN_rev6"] == 75
    assert totals["T4_raw_over_0p6kN"] == 5
    assert sum(row["T4"]["over_0p6kN"] for row in rows) == 0
    assert totals["T4_guard_violations"] == 0
    assert totals["T4_check_precal_grounded"] == 0
    assert sum(leg["e_excluded_over_0p6kN"] for row in rows
               for leg in row["T4"]["legs"].values()) == 70
    assert totals["T5_over_0p6kN_rev6"] == 104
    assert totals["T5_raw_over_0p6kN"] == 31
    assert sum(row["T5"]["over_0p6kN"] for row in rows if "T5" in row) == 0
    assert totals["T5_guard_violations"] == 0
    assert totals["T5_e_excluded"] == 148
    assert totals["sensor_model_rows"] == 1
    own_max_N = 0.18899124462126202e3
    assert totals["T4_max_own_excess_N"] == pytest.approx(own_max_N, rel=1e-9)
    assert totals["T5_max_own_excess_N"] == pytest.approx(own_max_N, rel=1e-9)
