"""Tests for the study-2 sensor adapter (04_scripts/03_control/s8/r79_sensor_screen.py) and its
judge (r79_sensor_judge.py); no harness run (the harness modules are imported lazily)."""

from __future__ import annotations

import importlib.util
import sys
import types
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.control.c2 import C2Config
from outrigger_sim.control.zero_calibration import ZeroCalibrationMode
from outrigger_sim.signals import Measurements

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "04_scripts" / "03_control" / "s8"
F_MIN_N = 9414.6
WEIGHT_N = 3.77e5
TWIST_VECTOR = np.array([0.476, -0.476, -0.523, 0.523])


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


screen = _load("r79_sensor_screen")
judge = _load("r79_sensor_judge")


def _ideal_measurements(rod: bool = False) -> Measurements:
    forces = np.array([[0.01 * k, -0.02 * k, 9.80665 + 1e-4 * k] for k in range(10)])
    return Measurements(
        t_s=12.3, specific_force_m_s2=forces.mean(axis=0),
        angular_rate_rad_s=np.array([1e-4, -2e-4, 0.0]),
        head_pressure_Pa=np.array([40e5, 41e5, 52e5, 53e5]),
        stroke_m=np.array([0.31, 0.32, 0.33, 0.34]),
        stroke_corrected_m=np.array([0.309, 0.319, 0.329, 0.339]),
        rod_pressure_Pa=np.array([2e5, 2e5, 2e5, 2e5]) if rod else None,
        imu_specific_force_samples_m_s2=forces)


def _gyro(n: int = 10) -> tuple[np.ndarray, np.ndarray]:
    return np.tile([1e-4, -2e-4, 0.0], (n, 1)), 12.2 + 0.01 * np.arange(1, n + 1)


def _fake_split(plant, m, head_area):
    rod = np.full(4, 3e5)
    return replace(m, head_pressure_Pa=m.head_pressure_Pa + rod * 0.3, rod_pressure_Pa=rod)


# --------------------------------------------------------------------------------------- seeds
def test_case_seed_formula_and_level_independence():
    assert screen.case_seed(1, 2, 7) == 20261028 + 100000 + 2000 + 7
    level, seed_index, case = screen.parse_job_key("L3|s2|g8|7|main|flat|top|4.0|FL|raised|200.0")
    assert (level.name, seed_index, case.group, case.index) == ("L3", 2, 1, 7)
    assert case.inner == "main|flat|top|4.0|FL|raised|200.0"


# --------------------------------------------------------------------------------------- config
def _preset_like() -> C2Config:
    config = C2Config().with_10hz_d1()
    return replace(config, target=replace(config.target, check_time_s=0.0),
                   zero_calibration=replace(config.zero_calibration,
                                            mode=ZeroCalibrationMode.OFF))


def test_level_config_l0_keeps_the_preset_object():
    config = _preset_like()
    assert screen.level_config(config, screen.LEVELS["L0"]) is config


def test_level_config_turns_check_and_zero_calibration_on():
    config = screen.level_config(_preset_like(), screen.LEVELS["L2"])
    assert config.target.check_time_s == screen.CHECK_TIME_S
    assert config.zero_calibration.mode is ZeroCalibrationMode.AIRBORNE_ROUNDTRIP
    assert config.target.gyro_noise_std_rad_s > 0.0
    ideal = screen.level_config(_preset_like(), screen.LEVELS["L1"])
    assert ideal.target.gyro_noise_std_rad_s == 0.0
    nocal = screen.level_config(_preset_like(), screen.LEVELS["L2nocal"])
    assert nocal.zero_calibration.mode is ZeroCalibrationMode.OFF
    assert nocal.target.check_time_s == screen.CHECK_TIME_S


# --------------------------------------------------------------------------------------- adapter
@pytest.mark.parametrize("rod", [False, True])
def test_l0_adapter_is_bit_identical(rod):
    ideal = _ideal_measurements(rod)
    adapter = screen.SensorAdapter(screen.LEVELS["L0"], seed=5, split_pressures=_fake_split)
    gyro, times = _gyro()
    out = adapter.deliver(ideal, None, None, gyro, times)
    for name in ("specific_force_m_s2", "angular_rate_rad_s", "head_pressure_Pa", "stroke_m",
                 "stroke_corrected_m", "imu_specific_force_samples_m_s2"):
        assert np.array_equal(getattr(out, name), getattr(ideal, name)), name
    assert np.array_equal(out.specific_force_m_s2,
                          np.mean(list(ideal.imu_specific_force_samples_m_s2), axis=0))
    assert (out.rod_pressure_Pa is None) == (not rod)
    assert out.imu_angular_rate_samples_rad_s is None


def test_l1_adapter_adds_rod_channel_and_gyro_samples_without_noise():
    ideal = _ideal_measurements()
    adapter = screen.SensorAdapter(screen.LEVELS["L1"], seed=5, split_pressures=_fake_split)
    gyro, times = _gyro()
    out = adapter.deliver(ideal, None, None, gyro, times)
    assert np.array_equal(out.rod_pressure_Pa, np.full(4, 3e5))
    assert np.array_equal(out.imu_angular_rate_samples_rad_s, gyro)
    assert np.allclose(out.angular_rate_rad_s, gyro.mean(axis=0))
    assert np.array_equal(out.stroke_m, ideal.stroke_m)


def test_graded_adapters_with_one_seed_share_the_noise_draws():
    gyro, times = _gyro()
    normal = screen.SensorAdapter(screen.LEVELS["L2"], 11, _fake_split)
    worst = screen.SensorAdapter(screen.LEVELS["L4"], 11, _fake_split)
    other = screen.SensorAdapter(screen.LEVELS["L2"], 12, _fake_split)
    a = normal.deliver(_ideal_measurements(), None, None, gyro, times)
    b = worst.deliver(_ideal_measurements(), None, None, gyro, times)
    c = other.deliver(_ideal_measurements(), None, None, gyro, times)
    assert np.array_equal(a.stroke_m, b.stroke_m)  # stroke noise: same stream on both grades
    assert not np.array_equal(a.head_pressure_Pa, b.head_pressure_Pa)
    assert not np.array_equal(a.stroke_m, c.stroke_m)


def test_extend_vent_split_keeps_the_net_force():
    area_ann = np.array([3.77e-3, 3.77e-3, 3.14e-3, 3.14e-3])
    head_area = np.array([1.3273e-2, 1.3273e-2, 9.5033e-3, 9.5033e-3])
    net = np.array([50e3, 60e3, 40e3, 45e3])
    plant = types.SimpleNamespace(
        locked=np.array([False, True, False, False]), last_dir=np.array([1.0, 1.0, -1.0, 1.0]),
        p_r0=np.full(4, 34e5), p_ext=np.full(4, 2e5), Gr=np.full(4, 100.0), A_ann=area_ann,
        pressure=lambda: net)
    out = screen.split_extend_vent(plant, _ideal_measurements(), head_area)
    harness_p_r = 34e5 - 100.0 / area_ann
    assert out.rod_pressure_Pa == pytest.approx([2e5, harness_p_r[1], harness_p_r[2], 2e5])
    rebuilt = out.head_pressure_Pa * head_area - out.rod_pressure_Pa * area_ann
    assert rebuilt == pytest.approx(net)


FL_HEAD_AREA_M2 = 1.3273e-2
FL_ANNULUS_M2 = 3.7699e-3


def _rod_plant(locked, last_dir, net_N, gr=0.0, gr_lock=0.0, p_r0=2e5):
    return types.SimpleNamespace(
        armed=True, locked=np.array(locked), last_dir=np.array(last_dir, float),
        A_ann=np.array([FL_ANNULUS_M2, FL_ANNULUS_M2, 3.1416e-3, 3.1416e-3]),
        Gr=np.full(4, gr), Gr_lock=np.full(4, gr_lock), p_r0=np.full(4, p_r0),
        x=np.full(4, 0.3), pressure=lambda: np.full(4, net_N))


def test_dyn_map_locked_value_and_floor():
    model = screen.DynMapRodModel()
    plant = _rod_plant([True] * 4, [1.0] * 4, 50e3, gr=100.0, gr_lock=50.0)
    model.step_chunk(plant, np.zeros(4), 1e-3)
    assert model.rod_Pa == pytest.approx(2e5 - 50.0 / plant.A_ann)
    deep = _rod_plant([True] * 4, [1.0] * 4, 50e3, gr=5e3)
    assert model.locked_value_Pa(deep) == pytest.approx(np.full(4, 0.1e5 - 1.01325e5))


def test_dyn_map_retract_lock_target_matches_the_yaml_constant():
    model = screen.DynMapRodModel()
    model._setup(_rod_plant([True] * 4, [1.0] * 4, 0.0))
    from outrigger_sim.sensors.rod_side import LegMode

    mode = np.full(4, LegMode.RETRACT)
    target = model._targets.moving_target_Pa(np.full(4, 118.099e3), mode, 0.0)
    assert target[0] / 1e5 == pytest.approx(34.818, abs=0.05)  # YAML p_r0_after_retract FL


def test_dyn_map_moving_leg_relaxes_with_the_exact_step_and_keeps_the_net_force():
    model = screen.DynMapRodModel()
    model.step_chunk(_rod_plant([True] * 4, [1.0] * 4, 50e3, p_r0=30e5), np.zeros(4), 1e-3)
    start = model.rod_Pa.copy()
    moving = _rod_plant([False] * 4, [1.0] * 4, 50e3, p_r0=30e5)
    model.step_chunk(moving, np.zeros(4), 1e-3)
    target = 2e5  # extend, u = 0: max(p_T0, -F / A_ann)
    decay = np.exp(-1e-3 / screen.ROD_LAG_S)
    assert model.rod_Pa == pytest.approx(target + (start - target) * decay)
    head_area = np.array([FL_HEAD_AREA_M2, FL_HEAD_AREA_M2, 9.5033e-3, 9.5033e-3])
    out = model(moving, _ideal_measurements(), head_area)
    rebuilt = out.head_pressure_Pa * head_area - out.rod_pressure_Pa * moving.A_ann
    assert rebuilt == pytest.approx(np.full(4, 50e3))
    assert set(model.meta()["max_abs_delta_p_r_vs_RodSideSynth_bar"]) == {"locked", "moving"}


def test_adapter_rejects_a_gyro_count_mismatch():
    adapter = screen.SensorAdapter(screen.LEVELS["L1"], 1, _fake_split)
    gyro, times = _gyro(9)
    with pytest.raises(RuntimeError, match="9 gyro samples for 10"):
        adapter.deliver(_ideal_measurements(), None, None, gyro, times)


def test_chunk_probe_takes_the_gyro_at_every_sample_end():
    plant = types.SimpleNamespace(Wr=np.full(4, 100.0), w=np.zeros(3), t=0.0)

    def lagged_step(plant_, cmd, valve, lag_steps):
        plant_.t += 0.001
        plant_.w = np.array([plant_.t, 0.0, 0.0])
        acc = np.zeros(16)
        acc[11:15] = 1000.0 * plant_.t
        acc[15] = 5.0 if plant_.t < 0.0105 else 0.0
        return acc

    probe = screen.ChunkProbe(lagged_step, 10)
    for _ in range(20):
        probe(plant, None, None, 2)
    assert [round(t, 6) for t in probe.sample_times] == [0.01, 0.02]
    assert probe.gyro_samples[1][0] == pytest.approx(0.02)
    assert probe.force_min == pytest.approx(np.full(4, 1.0 - 100.0))
    assert probe.crawler_max == 5.0
    probe.reset_period()
    assert probe.gyro_samples == [] and probe.crawler_max == 0.0


# --------------------------------------------------------------------------------------- summary
def test_largest_rise_and_twist_load():
    assert screen.largest_rise(np.array([5.0, 4.0, 4.5, 3.0, 3.2])) == pytest.approx(0.5)
    assert screen.largest_rise(np.array([3.0, 2.0, 1.0])) == 0.0
    forces = np.array([[10.0, 1.0, 2.0, 20.0]])
    assert screen.twist_load_N(forces, np.array([0.5, -0.5, -0.5, 0.5]))[0] == 13.5


def _truth(n: int = 120) -> dict:
    t_s = 0.1 * np.arange(1, n + 1)
    phase = np.array(["check"] * 5 + ["level"] * (n - 15) + ["done"] * 5 + ["ready"] * 5)
    crawler = np.where(t_s < 3.0, 1e5, 0.0)
    crawler[60] = 500.0  # one re-contact after the departure
    forces = np.full((n, 4), 60e3)
    forces[40, 1] = 50e3
    forces[39, 1] = 50.5e3
    return {"t_s": t_s, "phase": phase, "stroke_m": np.full((n, 4), 0.5),
            "force_N": forces, "force_min_N": forces - 100.0, "crawler_max_N": crawler}


def test_summarise_run_departure_loc_pause_and_relax():
    truth = _truth()
    events = [(3.2, "crawler_liftoff_confirmed"), (4.1, "INFO_LIFT_PAUSED:FR"),
              (10.6, "INFO_TWIST_UNSETTLED:-3.1"), (11.0, "WARN_LIFT_STROKE_LIMITED:FL"),
              (11.5, "INFO_LOC_CLEARANCE_ANCHOR:1,2,3,4")]
    summary = screen.summarise_run(truth, events, F_MIN_N, WEIGHT_N, TWIST_VECTOR)
    assert summary["t_check_end_s"] == pytest.approx(0.6)
    assert summary["t_off_s"] == pytest.approx(3.0)
    assert summary["loc_minus_off_s"] == pytest.approx(0.2)
    assert summary["n_recontact_after_off"] == 1
    assert summary["crawler_at_loc_N"] == 0.0
    pause = summary["lift_pauses"][0]
    assert pause["leg"] == "FR" and pause["true_drop_kN"] == pytest.approx(0.5)
    relax = summary["twist_relax"][0]
    assert relax["true_abs_D_kN"] == pytest.approx(0.0)
    assert relax["D_meas_kN"] == -3.1
    assert relax["D_read_error_kN"] == pytest.approx(3.1)
    assert relax["true_min_F_to_ready_kN"] == pytest.approx(59.9)
    assert not relax["true_below_F_min"] and not relax["true_below_F_min_to_ready"]
    assert summary["anchor_applied"] and summary["guard_events"] == [(11.0,
                                                                      "WARN_LIFT_STROKE_LIMITED:FL")]
    assert summary["warn_fault"] == ["WARN_LIFT_STROKE_LIMITED"]
    assert summary["n_done_entries"] == 1
    assert summary["max_true_stroke_mm"] == pytest.approx(500.0)


# --------------------------------------------------------------------------------------- sets
def test_g6_core_rule_and_g8_partial_set():
    assert screen.is_g6_core("g6|G1+J1@RL|top|Fs0")
    assert screen.is_g6_core("g6r|rigid+S1@FR|bottom|Fs4")
    assert not screen.is_g6_core("g6|G1+S1@FR|bottom|Fs4")
    assert not screen.is_g6_core("g6|G1+J1@FL|top|Fs0")
    assert screen.is_g6_core("ref|rigid|top|Fs4")
    assert screen.is_g6_core("ref|G1|bottom|Fs0")
    assert not screen.is_g6_core("ref|J1|top|Fs4")
    assert screen.is_g6_rear("g6r|rigid+J2@RR|bottom|Fs4")
    assert not screen.is_g6_rear("g6r|rigid+S1@FR|bottom|Fs4")
    assert not screen.is_g6_rear("ref|G1|top|Fs0")
    keys = screen.g8_keys()
    assert len(keys) == len(set(keys)) == 50


# --------------------------------------------------------------------------------------- judge
def test_clopper_pearson_upper_matches_the_spec_values():
    assert judge.clopper_pearson_upper(0, 19) == pytest.approx(0.1459, abs=1e-4)
    assert judge.clopper_pearson_upper(3, 71) == pytest.approx(0.1056, abs=1e-4)
    assert judge.clopper_pearson_upper(0, 0) is None
    assert judge.clopper_pearson_upper(5, 5) == 1.0


def _run(level="L2", passed=True, **summary):
    base = {"t_check_end_s": 10.0, "t_off_s": 30.0, "t_loc_s": 31.0, "loc_minus_off_s": 1.0,
            "n_recontact_after_off": 0, "crawler_at_loc_N": 0.0, "crawler_at_loc_over_W": 0.0,
            "min_true_F_after_off_kN": 30.0, "max_true_stroke_mm": 600.0, "guard_events": [],
            "n_stroke_end_fault": 0, "anchor_applied": False, "twist_relax": [],
            "n_done_entries": 1, "lift_pauses": [], "warn_fault": [], "F_min_kN": 9.4146,
            "W_N": WEIGHT_N, "c_min_tP_mm": 10.0}
    base.update(summary)
    return {"key": f"{level}|s0|g6|0|x", "level": level, "seed_index": 0, "harness": "g6",
            "inner": "x", "base": {"pass": passed, "t_ready_s": 80.0}, "r79": base,
            "zero_calibration": {"all_calibrated": True}}


def _relax(t_s=60.0, true_abs=16.0, error=0.5, low=False):
    return {"t_s": t_s, "true_abs_D_kN": true_abs, "D_read_error_kN": error,
            "D_meas_kN": -14.0, "D_true_kN": -true_abs, "true_below_F_min": False,
            "true_below_F_min_to_ready": low, "true_min_F_to_ready_kN": 30.0,
            "window_rise_kN": 0.2}


def _pause(t_s=25.0, leg="RR", drop=0.4, ratio=3.8):
    return {"t_s": t_s, "leg": leg, "true_drop_kN": drop, "true_F_over_F_min": ratio}


def test_judge_rows_s2_and_s6():
    ref = _run("L1")
    assert judge.judge_run(_run(), ref)["pass"]
    guard = _run(guard_events=[(40.0, "WARN_LIFT_STROKE_LIMITED:FL")], max_true_stroke_mm=650.0)
    assert judge.judge_s2(guard, ref)["misfire"]
    assert judge.judge_s2(_run(max_true_stroke_mm=690.0), ref)["miss"]
    assert judge.judge_s6(_run(warn_fault=["FAULT_STROKE_END"]), ref)["new_fault"]
    assert not judge.judge_run(_run(passed=False), ref)["rows"]["S-1"]["ok"]


def test_s3_fails_only_outside_the_read_band_and_new_against_l1():
    ref = _run("L1")
    outside = judge.judge_s3(_run(twist_relax=[_relax(true_abs=16.0, error=0.5)]), ref)
    assert not outside["ok"] and outside["fail_over_band_new"]
    inside = judge.judge_s3(_run(twist_relax=[_relax(true_abs=15.4, error=0.5)]), ref)
    assert inside["ok"] and inside["flags"] == ["S3_true_over_band"]
    ref_same = _run("L1", t_check_end_s=4.0, twist_relax=[_relax(t_s=56.0, true_abs=5.0)])
    paired = judge.judge_s3(_run(twist_relax=[_relax(true_abs=16.0)]), ref_same)
    assert paired["ok"] and paired["flags"] == ["S3_true_over_band"]
    low = judge.judge_s3(_run(twist_relax=[_relax(true_abs=5.0, low=True)]), ref_same)
    assert not low["ok"] and low["fail_low_to_ready"]
    late = _run()
    late["base"]["t_ready_s"] = 120.0
    assert judge.judge_s3(late, ref_same)["miss"]


def test_s4_fails_on_new_pauses_meeting_both_conditions():
    ref = _run("L1")
    assert not judge.judge_s4(_run(lift_pauses=[_pause()]), ref)["ok"]
    assert judge.judge_s4(_run(lift_pauses=[_pause(drop=2.0)]), ref)["ok"]
    ref_paused = _run("L1", t_check_end_s=4.0, lift_pauses=[_pause(t_s=19.5)])
    matched = judge.judge_s4(_run(lift_pauses=[_pause()]), ref_paused)
    assert matched["ok"] and matched["flags"] == ["S4_baseline"]
    other_leg = judge.judge_s4(_run(lift_pauses=[_pause(leg="RL")]), ref_paused)
    assert not other_leg["ok"]
    ref_low = _run("L1", lift_pauses=[_pause(drop=3.0, ratio=2.0)])
    assert judge.judge_s4(_run(min_true_F_after_off_kN=20.0), ref_low)["miss"]
    assert judge.judge_s4(_run(loc_minus_off_s=3.5), ref)["gate_fail"]


def _recontacts(*classes):
    return {"t_departure_confirmed_s": 30.1, "pass": "strict_fail" not in classes,
            "flags": ["P3-1_transient_recontact"] if "transient_flag" in classes else [],
            "events": [{"t_start_s": 30.5, "t_end_s": 30.7, "duration_s": 0.2,
                        "max_normal_N": 5e3, "max_over_W": 0.013, "ended_before_loc": True,
                        "class": name} for name in classes]}


def test_s4_counts_only_strict_recontacts_and_flags_transients():
    """Spec 407.2 (3): U-S9-G6d classes decide; a transient recontact is a FLAG only."""
    ref = _run("L1", recontact_events=_recontacts())
    transient = judge.judge_s4(_run(n_recontact_after_off=1,
                                    recontact_events=_recontacts("transient_flag")), ref)
    assert transient["ok"] and transient["flags"] == ["S4_transient_recontact"]
    strict = judge.judge_s4(_run(n_recontact_after_off=1,
                                 recontact_events=_recontacts("strict_fail")), ref)
    assert not strict["ok"] and strict["gate_fail"] and strict["recontact_new"]
    ref_strict = _run("L1", recontact_events=_recontacts("strict_fail"))
    assert judge.judge_s4(_run(recontact_events=_recontacts("strict_fail")), ref_strict)["ok"]
    # records without the classes keep the harness count
    assert not judge.judge_s4(_run(n_recontact_after_off=1), _run("L1"))["ok"]


def _chatter_events(start_s=31.2, duration_s=0.07, peak_over_threshold=1.06):
    threshold = 0.01 * WEIGHT_N
    return {"t_departure_confirmed_s": 30.1, "pass": False, "flags": [],
            "events": [{"t_start_s": start_s, "t_end_s": start_s + duration_s,
                        "duration_s": duration_s, "max_normal_N": peak_over_threshold * threshold,
                        "max_over_W": 0.01 * peak_over_threshold, "ended_before_loc": False,
                        "class": "strict_fail"}]}


def test_threshold_chatter_is_a_flag_in_s4_and_g6_1():
    """Spec 423.4 (Q-G): a stored strict recontact 0.2 s after the LOC (t_LOC 31.0 s), 0.07 s,
    1.06 x 0.01 W is re-judged as chatter: S-4 FLAG, G6-1 passes (stored gate False)."""
    ref = _run("L1", recontact_events=_recontacts())
    run = _run(recontact_events=_chatter_events())
    run["base"]["gates"] = {"G6-1_crawler": False, "G6-7_preloc": True}
    s4 = judge.judge_s4(run, ref)
    assert s4["ok"] and s4["flags"] == ["S4_threshold_chatter"]
    gate, record = judge.g61_gate(run)
    assert gate and record["switched_to_flag"] and record["ready_part_assumed"]
    assert record["flags"] == ["P3-1_threshold_chatter"]
    assert judge.harness_verdict(run["base"], run) and not judge.harness_verdict(run["base"])
    strict = _run(recontact_events=_chatter_events(duration_s=0.2))
    strict["base"]["gates"] = {"G6-1_crawler": False, "G6-7_preloc": True}
    assert not judge.g61_gate(strict)[0] and not judge.judge_s4(strict, ref)["ok"]
    loaded = _run(recontact_events=_chatter_events())
    loaded["base"]["gates"] = {"G6-1_crawler": False, "G6-7_preloc": True}
    loaded["base"]["crawler_N_max_after_ready"] = 50.0  # READY window load stays a failure
    assert judge.g61_gate(loaded)[0] is False


def test_recontact_summary_and_merge_of_reruns():
    base = {"crawler_recontact": {
        "departure": {"t_confirmed_s": 30.1},
        "recontact_events": {"pass": True, "flags": ["P3-1_transient_recontact"],
                             "events": [{**_recontacts("transient_flag")["events"][0],
                                         "extra": 1}]}}}
    summary = screen.recontact_summary(base)
    assert summary["t_departure_confirmed_s"] == 30.1 and "extra" not in summary["events"][0]
    assert screen.recontact_summary({}) is None
    stored = [{**_run(), "key": "a", "base": {"commands_sha256": "h1"}},
              {**_run(), "key": "b", "base": {"commands_sha256": "h2"}}]
    reruns = [{**_run(), "key": "b", "base": {"commands_sha256": "h2", "new": True}},
              {**_run(), "key": "c", "base": {"commands_sha256": "h3"}}]
    merged, merge = judge.merge_reruns(stored, reruns)
    assert [r["key"] for r in merged] == ["a", "b"] and merged[1]["base"]["new"]
    assert merge["replaced"] == 1 and merge["hash_differs"] == []
    assert merge["rerun_without_stored"] == ["c"]
    reruns[0]["base"]["commands_sha256"] = "other"
    assert judge.merge_reruns(stored, reruns)[1]["hash_differs"] == ["b"]


def test_s5_fails_only_against_a_clean_l1_or_a_rise():
    clean = _run("L1")
    assert not judge.judge_s5(_run(crawler_at_loc_over_W=0.02), clean)["ok"]
    loaded = _run("L1", crawler_at_loc_over_W=0.18)
    baseline = judge.judge_s5(_run(crawler_at_loc_over_W=0.185), loaded)
    assert baseline["ok"] and baseline["flags"] == ["S5_baseline"]
    assert not judge.judge_s5(_run(crawler_at_loc_over_W=0.20), loaded)["ok"]


def test_harness_verdict_applies_the_preloc_flag_rules():
    gates = {"G6-3_Fmin": True, "G6-6_fault_ready": True, "G6-7_preloc": False}
    base = {"gates": gates, "pass": False, "final_phase": "ready", "preloc_flag_ok": True}
    assert judge.harness_verdict(base)
    assert judge.harness_verdict({**base, "preloc_flag_ok": False})
    assert not judge.harness_verdict({**base, "preloc_flag_ok": None})
    assert not judge.harness_verdict({**base, "preloc_flag_ok": False,
                                      "gates": {**gates, "G6-3_Fmin": False}})
    assert judge.harness_verdict({"pass": True, "gates": {"fault0": True}})


def test_judge_results_pairs_with_l1_and_aggregates():
    results = [_run("L1"), _run("L2"), _run("L2", passed=False), _run("L0")]
    report = judge.judge_results(results)
    table = {(e["level"], e["group"]): e for e in report["table"]}
    assert table[("L2", "all")]["runs"] == 2
    assert table[("L2", "all")]["S-1"]["fail"] == 1
    assert report["unmatched"] == [] and report["errors"] == []


def test_identity_rows_compare_command_hashes():
    run = {"key": "L0|s0|g8|0|k", "level": "L0", "harness": "g8", "inner": "k",
           "base": {"cmd_sha256": "abc", "pass": True}, "wall_s": 1.0}
    rows = judge.identity_rows([run], {"g8|k": ("abc", True)})
    assert rows[0]["identical"] and rows[0]["pass_same"]
    rows = judge.identity_rows([run], {"g8|k": ("fff", True)})
    assert not rows[0]["identical"]
