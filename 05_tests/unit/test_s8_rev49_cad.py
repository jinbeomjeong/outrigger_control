"""Spec rev. 49 219.11 cad work (U-S8-36 ... 40).

* C-S8-31: ``R8Series`` records ``imu_gyro_samples`` (periods x 10 x 3, the delivered gyro
  10 ms partial means; NaN without IMU-rate samples).
* C-S8-27 update: event-leg re-contact gate 3.0 s with the 2.5 s nominal-damping flag
  (U-S8-37); forced-retract events in the 203.1 definition (U-S8-39).
* C-S8-32: the offline D1'' ratio ``|dr| / J`` of actual head steps > 100 bar, with and without
  the gyro lever term, and its record row per F_s grade.
* U-S8-40: ``run_S8C`` MLJ reuse check / copy and the judged mode of the ML plan.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from outrigger_sim.params import load_params
from outrigger_sim.sensors.imu import IMU_MOUNT_C1_BODY_M
from outrigger_sim.verify import s8_control as v

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "04_scripts" / "02_chrono"
GRAVITY_M_S2 = 9.80665
BAR = 1e5


@pytest.fixture(scope="module")
def run_s6c():
    """Load the script as a module; its import-time env settings are undone afterwards."""
    env = dict(os.environ)
    path = list(sys.path)
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("run_S6C_test49", SCRIPTS / "run_S6C.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        os.environ.clear()
        os.environ.update(env)
    yield mod
    sys.modules.pop(spec.name, None)
    sys.path[:] = path


@pytest.fixture(scope="module")
def run_s8c():
    pytest.importorskip("pychrono")
    env = dict(os.environ)
    path = list(sys.path)
    sys.path.insert(0, str(SCRIPTS))
    try:
        import run_S8C  # noqa: PLC0415
    finally:
        os.environ.clear()
        os.environ.update(env)
    yield run_S8C
    sys.path[:] = path


@pytest.fixture(scope="module")
def params_top():
    return load_params(level="top")


# --- C-S8-31 -----------------------------------------------------------------------------------


def _fake_series(run_s6c):
    model = SimpleNamespace(actuator=SimpleNamespace(valve_state_m_s=np.zeros(4),
                                                     amp_output_m_s=np.zeros(4)))
    c2 = SimpleNamespace(probe_history=[], meta=lambda: {}, _state=None, events=[],
                         phase=SimpleNamespace(value="ready"), computed_output_m_s=None,
                         command_components_m_s={})
    return run_s6c.R8Series(model, c2)


def test_r8_series_records_the_gyro_samples(run_s6c, tmp_path) -> None:
    s = _fake_series(run_s6c)
    force = np.tile([0.0, 0.0, GRAVITY_M_S2], (10, 1))
    gyro = np.arange(30, dtype=float).reshape(10, 3) * 1e-4
    cmd = SimpleNamespace(leg_speed_m_s=np.zeros(4))
    s(SimpleNamespace(t_s=1.0, imu_specific_force_samples_m_s2=force,
                      imu_angular_rate_samples_rad_s=gyro), cmd)
    s(SimpleNamespace(t_s=1.1, imu_specific_force_samples_m_s2=None), cmd)  # no gyro attr
    info = s.save(tmp_path / "r8.npz")
    with np.load(tmp_path / "r8.npz") as arr:
        assert arr["imu_gyro_samples"].shape == (2, 10, 3)
        assert np.array_equal(arr["imu_gyro_samples"][0], gyro)
        assert np.isnan(arr["imu_gyro_samples"][1]).all()
        assert np.array_equal(arr["imu_samples"][0], force)
    assert info["imu_gyro_available"] is True


# --- C-S8-27 update: U-S8-37 -------------------------------------------------------------------


def _settle_split(recontact_rel_s: float, *, fault_t_s=None):
    t = np.arange(0.0, 8.0, 1e-3)
    air = np.zeros((t.size, 4), bool)
    air[(t >= 0.5) & (t < 1.0), 1] = True  # FR (settled) lifts 0.5 s
    air[(t >= recontact_rel_s - 0.4) & (t < recontact_rel_s), 2] = True  # RL diagonal last
    z = np.zeros((t.size, 4))
    return v.settle_lift_split(t, air, z, 0.0, "FR", 0.024, 0.3, t3_s=1.2, fault_t_s=fault_t_s)


@pytest.mark.parametrize(("recontact_s", "is_pass", "within_nominal"),
                         [(2.4, True, True), (2.7, True, False), (3.2, False, False)])
def test_event_leg_gate_is_3_s_and_2_5_s_is_a_flag(recontact_s, is_pass, within_nominal) -> None:
    sp = _settle_split(recontact_s)
    assert sp["event_recontact_max_rel_s"] == pytest.approx(recontact_s, abs=2e-3)
    assert sp["event_pass"] is is_pass
    assert sp["event_recontact_within_nominal"] is within_nominal
    rows = v.u_s8_32_rows("X", sp)
    assert rows[1]["passed"] is is_pass
    assert rows[1]["value"][3] is within_nominal
    assert ("FLAG re-contact" in rows[1]["note"]) is (not within_nominal)


def test_event_leg_gate_keeps_cumulative_lift_and_fault() -> None:
    assert _settle_split(2.0, fault_t_s=1.0)["event_pass"] is False


# --- C-S8-27 update: U-S8-39 -------------------------------------------------------------------


def _forced_pads(f_min_N, rod_weight_N):
    tp = np.arange(0.0, 3.0, 1e-3) + 1e-3
    f = np.full((tp.size, 4), 40e3)
    f[(tp > 1.2) & (tp < 1.203), 3] = f_min_N - 100.0  # RR dips below F_min for 3 ms
    f[(tp > 2.6) & (tp < 2.602), 0] = -rod_weight_N[0] + 100.0  # FL lift (after the window)
    return tp, {"F_cyl_min_interval": f}


def test_forced_event_203_1_uses_the_1_ms_minimum_of_each_window(params_top) -> None:
    f_min = float(params_top.control.F_min_cylinder_N)
    w = v._rod_weight_N(params_top)
    tp, pads = _forced_pads(f_min, w)
    t10 = np.arange(0.0, 3.01, 0.1)
    f_inst = np.full((t10.size, 4), 40e3)  # the 10 Hz instants miss the 3 ms dip
    ev = v.forced_event_203_1(pads, tp, t10, 1.0, 2.0, f_min, w, "RL", f_inst)
    assert ev["U_or_L"] is True and ev["L"] is False
    assert ev["U_legs"] == ["RR"] and ev["L_legs"] == []
    assert ev["forced_leg_U_or_L"] is False
    assert ev["first_window_end_s"] == pytest.approx(1.3)
    assert ev["inst_10hz_below_F_min"] is False
    wide = v.forced_event_203_1(pads, tp, t10, 1.0, 2.9, f_min, w, "FL", f_inst)
    assert wide["L"] is True and wide["L_legs"] == ["FL"] and wide["forced_leg_L"] is True


# --- C-S8-32 -----------------------------------------------------------------------------------


def _write_case(d: Path, params, *, with_gyro: bool, alpha_x: float, ready_mass_kg: float):
    """Six READY periods at rest, then LEVEL; at period 8 FR's head steps +110 bar with the
    four-leg sum kept and a roll kick ``alpha_x`` that reads as f_z at the IMU."""
    n = 10
    t = 100.0 + 0.1 * np.arange(n)
    phase = np.array(["ready"] * 6 + ["level"] * 4)
    a_p, a_ann, _ = v.cylinder_areas_m2(params)
    loads = np.tile(ready_mass_kg * GRAVITY_M_S2 * np.array([0.3, 0.3, 0.2, 0.2]), (n, 1))
    moved = 110.0 * BAR * a_p[1]
    loads[8:] += np.array([-moved, moved, 0.0, 0.0])
    rod = np.full((n, 4), 2.0 * BAR)
    head = (loads + rod * a_ann) / a_p
    arm = np.asarray(IMU_MOUNT_C1_BODY_M) - np.asarray(params.superstructure.mass_properties.com_m)
    imu = np.zeros((n, 10, 3))
    imu[:, :, 2] = GRAVITY_M_S2
    gyro = np.zeros((n, 10, 3))
    gyro[8, -1, 0] = alpha_x * 0.01
    imu[8, -1, 2] += alpha_x * arm[1]
    arrays = {"t": t, "phase": phase, "imu_samples": imu}
    if with_gyro:
        arrays["imu_gyro_samples"] = gyro
    np.savez(d / "r8_series.npz", **arrays)
    f_hat = head * a_p - rod * a_ann
    np.savez(d / "s8_series.npz", t=t, phase=phase, F_hat_N=f_hat, F_nominal_N=f_hat)
    (d / "record").mkdir()
    np.savez(d / "record" / "record.npz", t=t, **{"meas.head_pressure": head,
                                                   "meas.rod_pressure": rod})
    return moved


@pytest.mark.parametrize("with_gyro", [True, False])
def test_d1pp_ratio_with_and_without_the_lever_term(tmp_path, params_top, with_gyro) -> None:
    mass = 38000.0
    moved = _write_case(tmp_path, params_top, with_gyro=with_gyro, alpha_x=1.5,
                        ready_mass_kg=mass)
    out = v.d1pp_step_ratios(tmp_path, params_top, settings={})
    steps = out["steps"]
    assert {s["leg"] for s in steps} == {"FL", "FR"}
    fr = next(s for s in steps if s["leg"] == "FR")
    assert fr["M_eff_source"] == "ready_median" and fr["M_eff_kg"] == pytest.approx(mass)
    assert fr["dp_bar"] == pytest.approx(110.0)
    arm_y = IMU_MOUNT_C1_BODY_M[1] - params_top.superstructure.mass_properties.com_m[1]
    uncorrected = mass * 1.5 * arm_y / moved
    assert fr["ratio_uncorrected"] == pytest.approx(uncorrected, rel=1e-9)
    assert fr["ratio"] == pytest.approx(0.0 if with_gyro else uncorrected, abs=1e-9)
    assert out["lever_correction_available"] is with_gyro


def test_d1pp_ratio_row_flags_by_grade(tmp_path, params_top) -> None:
    _write_case(tmp_path, params_top, with_gyro=False, alpha_x=1.5, ready_mass_kg=38000.0)
    d1 = v.d1pp_step_ratios(tmp_path, params_top, settings={})
    row = v.d1pp_ratio_rows({"A": {"d1pp": d1, "fs_mean_kN": 0.0},
                             "B": {"d1pp": {"steps": []}, "fs_mean_kN": 6.0}})[0]
    assert row["kind"] == "record" and row["passed"] is None
    ratio = max(s["ratio"] for s in d1["steps"])
    assert row["value"]["0"]["steps"] == 2
    assert row["value"]["0"]["ratio_max"] == pytest.approx(round(ratio, 4))
    assert row["value"][">5"] == {"steps": 0, "ratio_max": None}
    assert row["flagged_grades"] == (["0"] if ratio >= v.D1PP_RATIO_FLAG else [])


def test_fs_grade_edges() -> None:
    assert [v._fs_grade(x) for x in (0.0, 2.5, 2.6, 5.0, 5.1, None)] == [
        "0", "<=2.5", "<=5", "<=5", ">5", "unknown"]


# --- U-S8-40 -----------------------------------------------------------------------------------


def _fake_mlj_batch(root: Path, ids, *, failed=()):
    root.mkdir()
    (root / "batch_meta.json").write_text(json.dumps({"mode": "run", "set": "mlj"}), "utf-8")
    for cid in ids:
        d = root / cid
        d.mkdir()
        (d / "result.json").write_text(json.dumps({"settings": {}}), "utf-8")
        status = "failed" if cid in failed else "ok"
        (d / "case.log").write_text(f"case {cid} finished: {status}\n", "utf-8")


def test_mlj_reuse_copies_a_finished_batch(run_s8c, tmp_path) -> None:
    ids = [c.case_id for c in run_s8c.case_set("mlj")]
    assert len(ids) == 6
    src = tmp_path / "mlj_x"
    _fake_mlj_batch(src, ids)
    check = run_s8c.check_mlj_batch(src)
    assert check["cases"] == ids and set(check["status"].values()) == {"ok"}
    meta = run_s8c.reuse_mlj(tmp_path / "main" / "judged", check)
    assert meta["reused_from"] == str(src)
    for cid in ids:
        assert (tmp_path / "main" / "judged" / cid / "result.json").exists()
        assert (src / cid / "result.json").exists()  # the source stays


def test_mlj_reuse_refuses_a_failed_case(run_s8c, tmp_path) -> None:
    ids = [c.case_id for c in run_s8c.case_set("mlj")]
    src = tmp_path / "mlj_y"
    _fake_mlj_batch(src, ids, failed=(ids[0],))
    with pytest.raises(SystemExit):
        run_s8c.check_mlj_batch(src)


def test_ml_plan_judged_modes(run_s8c) -> None:
    run = run_s8c.ml_plan("main", "run")
    skip = run_s8c.ml_plan("main", "skip")
    reuse = run_s8c.ml_plan("main", "reuse")
    assert run["judged_mode"] == "run" and len(run["judged_wall_p_s"]) == 6
    assert skip["judged_cases"] == [] and skip["judged_wall_p_s"] == []
    assert reuse["judged_wall_p_s"] == [] and len(reuse["judged_cases"]) == 6
    assert reuse["makespan"]["p7e8"]["total_s"] == skip["makespan"]["p7e8"]["total_s"]
    assert run["makespan"]["p7e8"]["total_s"] > skip["makespan"]["p7e8"]["total_s"]
    assert run_s8c._judged_mode("pilot", None, False) == "skip"
    with pytest.raises(SystemExit):
        run_s8c._judged_mode("main", Path("x"), True)
