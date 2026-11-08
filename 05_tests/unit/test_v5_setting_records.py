"""v5 harness run records (user decisions 2026-11-08): the E-6 pressure-zero allowance record and
its use by ``t4h_replay``.

The harness runs go through ``v5_setting_run_runner.py`` in dynamics-dev (numba harness) and are
compared with the stored ``run_v5`` batch lines (``06_analysis/.../v5/main.jsonl``, git-ignored:
skipped when absent).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
RUNNER = Path(__file__).resolve().with_name("v5_setting_run_runner.py")
TIMEOUT_S = 900
FAILURE_ALLOWANCE_N = (5500.0, 5500.0, 4000.0, 4000.0)
"""``ZeroCalibrationSettings.failure_allowance_N`` (front 5.5, rear 4.0 kN)."""
V5_RESULTS = PROJECT_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
V5_MAIN_JSONL = V5_RESULTS / "main.jsonl"
VB_JOB = {"case": "R6", "eps": 0.001, "setting": "VB"}
VB_STORED_HASH = "d0eaa3a019e18bd6ee572666848bac3114432264ac2b4d305a261b300ea0925c"
"""``item8.jsonl`` line of ``VB_JOB`` (r5, ③ off; no fallback leg: T8 keeps it)."""
V0_JOB = {"case": "S8", "eps": 0.001, "setting": "V0"}
V0_STORED_HASH = "2f655199bd67468ffae7f48c942c9c80d7b91e32d2fa35780012c4a91e531d1f"
"""``main.jsonl`` line of ``V0_JOB`` (final_C4G2, no v5 option)."""
LS1_JOB = {"case": "S8", "eps": 0.003, "setting": "LS1"}
LS1_STORED_HASH = "991926ff424247fb8a7fce94331884468fcdc0a405d4443cb2bf3ed11648aa23"
"""``main.jsonl`` line of ``LS1_JOB`` (stage 2 harness batch, M2 r5, final_C4G2)."""


@pytest.fixture(scope="module")
def t4h_replay():
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        import t4h_replay as module

        yield module
    finally:
        sys.path.remove(str(COUPLED_DIR))


def run_job(job: dict, tmp_path: Path) -> dict:
    """``job`` through ``run_v5.run_one`` in dynamics-dev; the runner's report."""
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")
    out_path = tmp_path / "report.json"
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "PYTHONDONTWRITEBYTECODE": "1"}
    subprocess.run([str(HARNESS_PYTHON), "-I", "-B", str(RUNNER), json.dumps(job),
                    str(tmp_path / "t4h"), str(out_path)],
                   check=True, env=environment, timeout=TIMEOUT_S)
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report.pop("foreign_modules") == []
    return report


@pytest.fixture(scope="module")
def run_v5():
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        import run_v5 as module

        yield module
    finally:
        sys.path.remove(str(COUPLED_DIR))


# ------------------------------------------------- criteria revision 8: VB / LS = final_C4G2_P3
def test_vb_and_ls_settings_carry_the_p3_bound_and_the_others_do_not(run_v5) -> None:
    """Revision 8 3.1: VB, LS1 .. LS4 on; V0 .. V3, L1, L2 off; V4 .. V8 off (M1c)."""
    from outrigger_sim.hydraulics.v5_options import HydraulicOptions, controller_tag

    for name, (_, plant) in run_v5.SETTINGS.items():
        options = HydraulicOptions.from_dict(plant) if plant else None
        is_p3 = name == "VB" or name.startswith("LS")
        assert (controller_tag(options) == "final_C4G2_P3") == is_p3, name
        if options is not None and not is_p3:
            assert "extend_start_tracked" not in options.to_dict(), name
    vb, v8 = run_v5.SETTINGS["VB"][1], run_v5.SETTINGS["V8"][1]
    assert {k: v for k, v in vb.items() if k != "extend_start_tracked"} == {
        k: v for k, v in v8.items() if k != "check_delay"}


def test_p3_option_is_refused_with_m1c_and_keeps_the_off_dict() -> None:
    from outrigger_sim.hydraulics.v5_options import (
        CheckDelaySetting,
        HydraulicOptions,
        LockClosureSetting,
    )

    with pytest.raises(ValueError, match="M1c"):
        HydraulicOptions(rod_release_force=True, check_delay=CheckDelaySetting("VN"),
                         extend_start_tracked=True)
    off = HydraulicOptions(rod_release_force=True, lock_closure=LockClosureSetting(0.02, 0.05),
                           lock_window_follows_plant=True)
    assert "extend_start_tracked" not in off.to_dict()  # the stored VB digests' dict
    assert HydraulicOptions(**{**vars(off), "extend_start_tracked": True}).to_dict()[
        "extend_start_tracked"] is True


def test_controller_options_turn_the_rule_on_and_leave_the_preset_off() -> None:
    """T-P3-1: preset and class default stay ``constant``; the option alone switches."""
    from outrigger_sim.control.c2 import C2Config
    from outrigger_sim.hydraulics.v5_options import HydraulicOptions, apply_controller_options

    preset = C2Config().with_10hz_d1()
    assert "extend_start_rule" not in preset.two_pressure.to_meta()
    assert apply_controller_options(preset, HydraulicOptions(), 0.02, 0.1) is preset
    tracked = apply_controller_options(preset, HydraulicOptions(extend_start_tracked=True),
                                       0.02, 0.1)
    meta = tracked.two_pressure.to_meta()
    assert meta["extend_start_rule"] == "tracked_bound"
    assert meta["extend_start_bound"]["revision"] == 4


def test_j_p3_judgement() -> None:
    from outrigger_sim.control.extend_start_bound import J_P3_NAME, j_p3_judgement

    clean = {"breach_reads": [0, 0, 0, 0], "margin_used_reads": [0, 2, 0, 0],
             "locked_breach_over_tol_reads": [0, 0, 0, 0]}
    assert J_P3_NAME == "extend_bound_check.ext_moving.breach_reads == 0"
    assert j_p3_judgement([clean, clean])["status"] == "pass"
    assert j_p3_judgement([clean])["margin_used_reads_flag"] == 2
    breach = {**clean, "breach_reads": [0, 1, 0, 0]}
    assert j_p3_judgement([clean, breach])["status"] == "H-7"
    assert j_p3_judgement([clean, None])["status"] == "setting_defect"
    assert j_p3_judgement([clean, None], [True, False])["status"] == "pass"
    assert j_p3_judgement([])["status"] == "no_p3_runs"


@pytest.mark.skipif(not V5_MAIN_JSONL.is_file(), reason="stored main.jsonl not present")
def test_p3_hash_batch_is_the_22_cases_of_revision_8(run_v5) -> None:
    """Revision 8 7.2: per case the first VB line of ``main.jsonl`` (22 cases, its table)."""
    jobs = run_v5.p3_hash_jobs()
    assert len(jobs) == 22
    lines = dict((job["case"], number) for number, job in jobs)
    assert lines["R1"] == 1111 and lines["R12"] == 397 and lines["S8"] == 445
    assert all(job["setting"] == "VB" for _, job in jobs)


def test_t4h_record_names(t4h_replay) -> None:
    """Revision 8 2 #3: the ③-off override is ``T4h-const``, everything else ``T4h``."""
    assert t4h_replay.record_name(None) == "T4h"
    assert t4h_replay.record_name("tracked_bound") == "T4h"
    assert t4h_replay.record_name("constant") == "T4h-const"


# ------------------------------------------------------------------ E-6 allowance in the replay
def test_rebuilt_allowance_takes_the_failed_legs_from_the_calibration_events(t4h_replay) -> None:
    events = [(1.0, "INFO_D1_X"), (4.3, "INFO_PRESSURE_ZERO_CALIBRATED:FL"),
              (4.3, "WARN_PRESSURE_ZERO_SKIPPED:FR:grounded"),
              (4.3, "WARN_PRESSURE_ZERO_IMPLAUSIBLE:RR"), (4.3, "INFO_PRESSURE_ZERO_CALIBRATED:RL")]
    allowance = t4h_replay.rebuilt_offset_allowance(events, FAILURE_ALLOWANCE_N, (0.0,) * 4)
    assert allowance.deduction_N.tolist() == [0.0, 5500.0, 0.0, 4000.0]
    assert allowance.from_s == 4.3


def test_rebuilt_allowance_of_a_run_without_a_check_or_a_calibration(t4h_replay) -> None:
    all_skipped = [(0.0, "WARN_PRESSURE_ZERO_SKIPPED:all:no_check")]
    allowance = t4h_replay.rebuilt_offset_allowance(all_skipped, FAILURE_ALLOWANCE_N, (0.0,) * 4)
    assert allowance.deduction_N.tolist() == list(FAILURE_ALLOWANCE_N)
    none = t4h_replay.rebuilt_offset_allowance([], FAILURE_ALLOWANCE_N, (0.0,) * 4)
    assert none.deduction_N.tolist() == [0.0] * 4 and none.from_s is None
    with pytest.raises(ValueError, match="setting"):
        t4h_replay.rebuilt_offset_allowance([], FAILURE_ALLOWANCE_N, (1.0, 0.0, 0.0, 0.0))


def test_recorded_allowance_comes_before_the_rebuilt_one(t4h_replay) -> None:
    meta = {"pressure_offset_allowance_N": [0.0, 0.0, 4000.0, 0.0],
            "pressure_offset_allowance_from_s": 4.7,
            "events": [(4.7, "WARN_PRESSURE_ZERO_SKIPPED:FL:grounded")]}
    allowance = t4h_replay.offset_allowance_of(meta, config=None)
    assert allowance.deduction_N.tolist() == [0.0, 0.0, 4000.0, 0.0]
    assert allowance.from_s == 4.7 and allowance.note == "recorded"


# ---------------------------------------------------------------------- harness runs (dynamics-dev)
DG3_OFF_T4H = V5_RESULTS / "dg3" / "off" / "t4h"
"""Dg-3 r79 records (135, ③ off, written before the allowance record), git-ignored."""
DG3_RECORDS = 135
DG3_ALLOWANCE_RECORDS = 42
RECORDED_LOWER_TOLERANCE_N = 1e-6


@pytest.mark.slow
@pytest.mark.skipif(not DG3_OFF_T4H.is_dir(), reason="Dg-3 records not present")
def test_rebuilt_allowance_replays_the_dg3_lower_readings(t4h_replay) -> None:
    """control-expert check (2026-11-08): with the run's own events and the rebuilt allowance
    the replay gives each run's own lower reading (42 records have a failed calibration)."""
    files = sorted(DG3_OFF_T4H.glob("*.npz"))
    assert len(files) == DG3_RECORDS
    rows = [t4h_replay.replay_values(path, check_recorded=True) for path in files]
    assert max(row["recorded_lower_max_abs_N"] for row in rows) <= RECORDED_LOWER_TOLERANCE_N
    assert sum(any(row["offset_allowance_N"]) for row in rows) == DG3_ALLOWANCE_RECORDS


DG3_V4_ON_T4H = V5_RESULTS / "dg3" / "v4_on_t4h"
"""Dg-3 v4 records (③ revision 4 on through the preset, options without the ③ key)."""


@pytest.mark.slow
@pytest.mark.skipif(not DG3_V4_ON_T4H.is_dir(), reason="Dg-3 v4 records not present")
def test_p3_records_replay_with_their_own_setting(t4h_replay) -> None:
    """Revision 8 7.1 (e): a ③-on record rebuilds the ③-on monitor from its meta (no
    override) and gives its own lower reading."""
    for path in sorted(DG3_V4_ON_T4H.glob("*.npz"))[:5]:
        row = t4h_replay.replay_values(path, check_recorded=True)
        assert row["run_extend_start_rule"] == "tracked_bound"
        assert row["extend_start_revision"] == 4
        assert row["recorded_lower_max_abs_N"] <= RECORDED_LOWER_TOLERANCE_N, path.name


@pytest.mark.slow
def test_allowance_record_leaves_the_command_hash_alone(tmp_path: Path) -> None:
    """The allowance fields are read after the run: an LS1 row with its T4h record keeps the
    stored command hash, and its T4h meta carries the fields (no calibration: 0, no start)."""
    report = run_job(LS1_JOB, tmp_path)
    assert report["hash"] == LS1_STORED_HASH
    t4h = report["t4h"]
    assert t4h["pressure_offset_allowance_N"] == [0.0] * 4
    # the stage 2 rows run without a CHECK zero calibration: no calibration end
    assert t4h["pressure_offset_allowance_from_s"] is None
    # criteria revision 8: LS runs final_C4G2_P3, its commands unchanged without a fallback
    assert report["controller_tag"] == t4h["controller_tag"] == "final_C4G2_P3"
    assert t4h["extend_start_rule"] == "tracked_bound"


@pytest.mark.slow
def test_vb_with_the_p3_bound_keeps_the_stored_hash_and_judges_j_p3(tmp_path: Path) -> None:
    """Revision 8 3.1 / 3.2 (T8): a VB row without a fallback leg keeps the ③-off command
    hash; the run records the tag and the ③ rule. This steady row reads the head pressures
    only, so the ③ tracker never runs and the J-P3 record is null by construction."""
    from outrigger_sim.control.extend_start_bound import j_p3_judgement

    report = run_job(VB_JOB, tmp_path)
    assert report["hash"] == VB_STORED_HASH
    assert report["controller_tag"] == "final_C4G2_P3"
    assert report["hydraulic_options"]["extend_start_tracked"] is True
    assert report["t4h"]["extend_start_rule"] == "tracked_bound"
    assert report["t4h"]["has_rod_reading"] is False and report["extend_bound_check"] is None
    judgement = j_p3_judgement([None], [False])
    assert judgement["status"] == "pass" and judgement["no_rod_reading_runs"] == 1


VB_EVENT_JOB = {"case": "R12", "eps": 0.0, "offset_s": 0.0,
                "twin": {"level": "top", "leg": "FL", "fs_kN": 8.0}, "setting": "VB"}
VB_EVENT_STORED_HASH = "0df0c58b04c1aa4654e6d79c01d91c084794f3634b0b271fa4d270ba7547ff90"
"""``main.jsonl`` line 397 (revision 8 7.2 row 12, ③ off)."""


@pytest.mark.slow
def test_vb_event_row_with_rod_readings_passes_j_p3(tmp_path: Path) -> None:
    """Revision 8 3.2 on a row with rod readings: the record exists, no ext_moving breach, and
    the command hash is the ③-off one (row 12 of the 7.2 table)."""
    report = run_job(VB_EVENT_JOB, tmp_path)
    assert report["hash"] == VB_EVENT_STORED_HASH
    assert report["t4h"]["has_rod_reading"] is True
    check = report["extend_bound_check"]
    assert check is not None and sum(check["breach_reads"]) == 0


@pytest.mark.slow
def test_v0_keeps_final_c4g2(tmp_path: Path) -> None:
    """Revision 8 3.1: V0 is not a ③ setting: same hash, no tag."""
    report = run_job(V0_JOB, tmp_path)
    assert report["hash"] == V0_STORED_HASH
    assert report["controller_tag"] is None and report["hydraulic_options"] is None
