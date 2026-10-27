"""Engine-free closed loop of the C2 R8-D1 preset on the reduced plant (spec rev. 30 134).

``04_scripts/03_control/r8d1/c2py_r8d1_closed_loop.py`` runs, in a subprocess (the harness
modules patch the plant classes of their process):

* the representative C2 cases of the revision-30 harness with the project controller and
  :meth:`C2Config.with_10hz_d1` (increment limit and output delay in the controller); the
  metrics are compared with the harness values of the same cases,
* top / level floor with the full preset and the 100 Hz attitude filter on 10 ms IMU samples,
* every run again with the lifted-leg re-approach (P-R8-13) off: same command hash where no
  leg lifts again,
* ``v34_drop.py preset``: an RR floor drop of 30 mm (spec rev. 34 174) with the P-R8-13
  preset against the control harness variant ``tw0.25_s1``.

Tolerances: spec 138 C-1 judges Chrono against the reduced values within +-10 %; the same band
is used for the touch and READY times; the peak pressure must stay below the 210 bar relief.
The minimum true cylinder force
is one-sided: at least the criterion ``F_min + 5 kN`` and not below 90 % of the harness value.
The harness models the increment limit as a continuous ramp in its loop, c2.py steps the
command once per period (spec 101 (3)), which raises the minimum force of the roll+ case from
38.9 to 51.9 kN; with the harness ramp instead of the c2.py limit the case gives 38.88 kN (the
harness 38.85 kN).

The reduced plant kernel needs numba (dynamics-dev); the module is skipped elsewhere:
``python.exe -I -m pytest 05_tests/unit/test_c2_r8d1_closed_loop.py`` with the dynamics-dev
interpreter (about 50 s).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("numba", reason="the reduced plant kernel needs numba (dynamics-dev)")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "04_scripts" / "03_control" / "r8d1" / "c2py_r8d1_closed_loop.py"
DROP_SCRIPT = SCRIPT.with_name("v34_drop.py")
DROP_REFERENCE = (
    PROJECT_ROOT / "06_analysis" / "02_control" / "r8_10hz" / "d1" / "v34_drop_top_final.json"
)
DROP_SUM_TOLERANCE_S = 0.005
DROP_LIFT_TOLERANCE_MM = 0.05
DROP_CONTACT_TOLERANCE_S = 0.01
"""The preset reproduced the harness variant exactly (2026-10-24); the bands only absorb
numba / BLAS rounding on another machine."""
U57_LIFT_SUM_S = 0.5
U57_LIFT_MM = 2.0
TRACE_META = PROJECT_ROOT / "05_tests" / "data" / "c2_r8d1_traces.json"
RELATIVE_TOLERANCE = 0.10  # spec 138 C-1 "축소 값 +-10 %"
MIN_FORCE_FLOOR_RATIO = 0.9
F_MIN_CRITERION_MARGIN_KN = 5.0  # D8: F_min + 5 kN on the true force
ACCURACY_TARGET_DEG = 0.2  # CLAUDE.md: steady-state error +-0.2 deg
MOVING_PRESSURE_LIMIT_BAR = 210.0
"""CLAUDE.md: MCV relief while moving. The peak is a record in spec 134, not a judged value;
the stepped increment of c2.py raises it (roll+ 114.4 -> 127.3 bar)."""
SETTLE_MIN_FORCE_ALLOWANCE_KN = 1.0
"""G4-type sink: the harness C2 lifts RR to -W_rod (-0.72 kN, spec 134); c2.py may not do
worse by more than this."""
SCRIPT_TIMEOUT_S = 600
SETTLE_REAPPROACH_START_FRACTION = 1.4
"""P-S8-5 (U-S8-9): the re-approach starts on a lower bound below 1.4 F_min, so the G-type
sink re-approach is legitimate only if RR truly fell below it (and it keeps RR above F_min:
3.04 kN with the 0.5 F_min start, 12.98 kN with 1.4, 2026-10-24)."""
SETTLE_REAPPROACH_MAX_S = 0.5
SETTLE_REAPPROACH_MAX_TRAVEL_M = 0.005
"""U57 net travel limit (spec 177): the re-approach of a leg that only just unloaded."""


@pytest.fixture(scope="module")
def closed_loop(tmp_path_factory) -> dict:
    out_path = tmp_path_factory.mktemp("r8d1") / "closed_loop.json"
    environment = dict(os.environ, MKL_THREADING_LAYER="TBB", PYTHONDONTWRITEBYTECODE="1")
    completed = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(out_path)],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT_S,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-3000:]
    return json.loads(out_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def harness_metrics() -> dict[str, dict]:
    meta = json.loads(TRACE_META.read_text(encoding="utf-8"))
    return {case["id"]: case["metrics"] for case in meta["cases"]}


@pytest.fixture(scope="module")
def f_min_kN(closed_loop) -> float:
    return closed_loop["imu_100hz"]["F_min_N"] / 1e3


def test_every_harness_case_ran_with_the_preset(closed_loop, harness_metrics) -> None:
    assert [run["id"] for run in closed_loop["harness"]] == list(harness_metrics)
    for run in closed_loop["harness"]:
        assert run["meta_revision"].startswith("R8-D1")
        assert run["fails"] == []


@pytest.mark.parametrize("case_index", range(3))
def test_harness_case_metrics(closed_loop, harness_metrics, f_min_kN, case_index) -> None:
    run = closed_loop["harness"][case_index]
    metrics = run["metrics"]
    reference = harness_metrics[run["id"]]
    for key in ("t_touch_s", "t_ready_s"):
        assert metrics[key] == pytest.approx(reference[key], rel=RELATIVE_TOLERANCE), key
    assert metrics["max_pressure_bar"] <= MOVING_PRESSURE_LIMIT_BAR
    min_force = metrics["min_true_cyl_force_kN"]
    assert min_force >= f_min_kN + F_MIN_CRITERION_MARGIN_KN
    assert min_force >= MIN_FORCE_FLOOR_RATIO * reference["min_true_cyl_force_kN"]
    assert metrics["ss_true_att_deg_maxabs"] <= ACCURACY_TARGET_DEG


def test_settlement_case_recovers_like_the_harness(closed_loop, harness_metrics, f_min_kN) -> None:
    run = next(run for run in closed_loop["harness"] if run["id"].startswith("G|"))
    metrics = run["metrics"]
    reference = harness_metrics[run["id"]]
    assert metrics["min_true_after_sink_kN"] >= (
        reference["min_true_after_sink_kN"] - SETTLE_MIN_FORCE_ALLOWANCE_KN
    )
    assert min(metrics["final_true_kN"]) >= f_min_kN
    assert metrics["final_true_kN"] == pytest.approx(
        reference["final_true_kN"], rel=RELATIVE_TOLERANCE
    )


def test_reapproach_leaves_the_runs_without_a_lifted_leg_unchanged(closed_loop, f_min_kN) -> None:
    """P-R8-13 (spec 179.1): in the runs where no leg lifts again the re-approach never starts
    and the commands are bit for bit those with it off. Only the G-type sink of the
    revision-30 harness starts one: its RR unloads below the 1.4 F_min start (P-S8-5, U-S8-9;
    with the 0.5 F_min start it fell to about 3 kN first), which the one-sample watch of
    P-R8-13 catches, and now RR stays above F_min. That re-approach ends on contact within
    0.5 s and a few mm; the recovery metrics are judged by
    :func:`test_settlement_case_recovers_like_the_harness`."""
    runs_on = [*closed_loop["harness"], closed_loop["imu_100hz"]]
    runs_off = [*closed_loop["harness_without_reapproach"],
                closed_loop["imu_100hz_without_reapproach"]]
    for run_on, run_off in zip(runs_on, runs_off, strict=True):
        if run_on.get("id", "").startswith("G|"):
            min_after_sink_kN = run_on["metrics"]["min_true_after_sink_kN"]
            assert f_min_kN <= min_after_sink_kN < SETTLE_REAPPROACH_START_FRACTION * f_min_kN
            assert [interval["outcome"] for interval in run_on["reapproach_intervals"]] == [
                "contact"
            ]
            (interval,) = run_on["reapproach_intervals"]
            assert interval["leg"] == "RR" and interval["mode"] == "twist"
            assert interval["end_s"] - interval["start_s"] <= SETTLE_REAPPROACH_MAX_S
            assert abs(interval["travel_m"]) <= SETTLE_REAPPROACH_MAX_TRAVEL_M
            continue
        assert run_on["reapproach_events"] == run_on["reapproach_intervals"] == []
        assert run_on["commands_sha256"] == run_off["commands_sha256"]


@pytest.fixture(scope="module")
def drop_runs(tmp_path_factory) -> dict[tuple[str, str], dict]:
    """``v34_drop.py preset preset_p30off`` (top, events F and P) by ``(variant, mode)``: the
    full preset, and the preset without P-S8-30 (the P-R8-13 mechanism alone)."""
    out_path = tmp_path_factory.mktemp("v34") / "drop.json"
    environment = dict(os.environ, MKL_THREADING_LAYER="TBB", PYTHONDONTWRITEBYTECODE="1",
                       V34_MODES="F,P", V34_LEVEL="top")
    completed = subprocess.run(
        [sys.executable, "-I", str(DROP_SCRIPT), str(out_path), "preset", "preset_p30off"],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT_S,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-3000:]
    runs = json.loads(out_path.read_text(encoding="utf-8"))
    return {(run["variant"], run["mode"]): run for run in runs}


def fl_lift_summary(run: dict) -> tuple[float, float]:
    """FL lift-off time sum (s) and largest FL pad gap (mm) in the 5 s window."""
    fl = run["lifts"]["FL"]
    return fl["sum_s"], max(episode[2] for episode in fl["episodes"])


def harness_variant_reference(mode: str) -> dict:
    """The control harness variant ``tw0.25_s1`` (spec 174.2) of event mode ``mode``."""
    reference_runs = json.loads(DROP_REFERENCE.read_text(encoding="utf-8"))
    return next(
        run for run in reference_runs if run["mode"] == mode and run["variant"] == "tw0.25_s1"
    )


@pytest.mark.parametrize("mode", ["F", "P"])
def test_twist_reapproach_reproduces_the_harness_variant(drop_runs, mode) -> None:
    """Spec 179.1: the c2.py preset gives the control harness variant ``tw0.25_s1`` (spec 174.2,
    ``v34_drop_top_final.json``), within U57 (FL sum <= 0.5 s, lift <= 2 mm). P-S8-30 off: the
    mechanism alone."""
    reference = harness_variant_reference(mode)
    run = drop_runs[("preset_p30off", mode)]
    fl_sum_s, fl_lift_mm = fl_lift_summary(run)
    reference_sum_s, reference_lift_mm = fl_lift_summary(reference)
    assert fl_sum_s == pytest.approx(reference_sum_s, abs=DROP_SUM_TOLERANCE_S)
    assert fl_lift_mm == pytest.approx(reference_lift_mm, abs=DROP_LIFT_TOLERANCE_MM)
    assert run["RR_first_contact_s"] == pytest.approx(
        reference["RR_first_contact_s"], abs=DROP_CONTACT_TOLERANCE_S
    )
    assert run["RR_firm_contact_s"] == pytest.approx(
        reference["RR_firm_contact_s"], abs=DROP_CONTACT_TOLERANCE_S
    )
    assert set(run["lifts"]) == {"FL", "RR"}  # no other leg lifts
    assert fl_sum_s <= U57_LIFT_SUM_S and fl_lift_mm <= U57_LIFT_MM


@pytest.mark.parametrize("mode", ["F", "P"])
def test_full_preset_drop_stays_within_u57(drop_runs, mode) -> None:
    """The full preset (P-S8-30 on): its pre-LOC slowdown changes the state at the drop (P:
    FL lift 1.51 -> 1.58 mm), so it is judged on U57 and the RR contact times of
    ``tw0.25_s1``, not on the reproduction bands."""
    reference = harness_variant_reference(mode)
    run = drop_runs[("preset", mode)]
    fl_sum_s, fl_lift_mm = fl_lift_summary(run)
    assert fl_sum_s <= U57_LIFT_SUM_S
    assert fl_lift_mm <= U57_LIFT_MM
    assert set(run["lifts"]) == {"FL", "RR"}  # no other leg lifts
    assert run["RR_first_contact_s"] == pytest.approx(
        reference["RR_first_contact_s"], abs=DROP_CONTACT_TOLERANCE_S
    )
    assert run["RR_firm_contact_s"] == pytest.approx(
        reference["RR_firm_contact_s"], abs=DROP_CONTACT_TOLERANCE_S
    )


def test_full_preset_with_the_100hz_attitude_filter_levels(closed_loop) -> None:
    run = closed_loop["imu_100hz"]
    assert run["phase"] == "ready"
    assert run["timing"] == {"d": 1, "late_imu": False, "delta_s": None,
                             "imu_sample_period_s": 0.01}
    assert run["probe_rounds"] == 1
    assert run["max_abs_attitude_after_ready_deg"] <= ACCURACY_TARGET_DEG
    f_min_N = run["F_min_N"]
    assert run["min_true_cyl_force_after_liftoff_N"] >= f_min_N + F_MIN_CRITERION_MARGIN_KN * 1e3
    assert run["min_pad_contact_after_liftoff_N"] > 0.0
    assert run["twist_gain_stiffness"]["reference"] == "measured_Sii"
