"""Checks of the harness adapter and the verdict tables, without any harness run.

The flow-limited chunks use random and synthetic inputs and a stub plant, not a simulated case.
Run (dynamics-dev): python -I -B -m pytest <this file> -p no:cacheprovider
"""
from __future__ import annotations

import copy
import importlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from harness_flow import (  # noqa: E402
    COLUMN,
    FlowLimiter,
    FlowSetting,
    U,
    V,
    install_command_clip,
    make_flow_plant_class,
)
from params import load_params  # noqa: E402
from verdict_cases import ALL_CASE_IDS, build_clip_runs, build_runs, resolve_case  # noqa: E402
from verdict_metrics import count_disjoint_swaps, flow_conservation, saturation_inputs  # noqa: E402

P = load_params()
RNG = np.random.default_rng(20261104)
LOW_FLOW_ETA = 0.85
STORED_OFF_R1_DIGEST = "8b559936468481e55594cbcfc5193f53feec325672e731dbd1caca100e7d50de"
"""``definition_sha256`` in verdict/OFF_R1.json; if it moves, the stored results stop resuming."""
SETTINGS =[FlowSetting(eta_v=0.95), FlowSetting(eta_v=LOW_FLOW_ETA),
            FlowSetting(eta_v=LOW_FLOW_ETA, dp_comp_Pa=6e5, dp_unload_Pa=12e5),
            FlowSetting(eta_v=LOW_FLOW_ETA, dp_comp_Pa=20e5, dp_unload_Pa=30e5),
            FlowSetting(eta_v=LOW_FLOW_ETA, law="proportional"),
            FlowSetting(eta_v=LOW_FLOW_ETA, width_Pa=2e5)]


class StubPlant:
    """Plant interface of the harness: step integrates nothing and keeps the last input."""

    def __init__(self):
        self.armed = False
        self.t = 0.0
        self.Wr = np.zeros(4)
        self.sref = np.zeros(4)
        self.last_input = None
        self.oil_force = np.array([90e3, 88e3, 60e3, 58e3])

    def step(self, u, nsteps):
        self.last_input = np.array(u, float)
        self.t += nsteps * 5e-4
        accumulated = np.zeros(24)
        accumulated[11:15] = self.oil_force
        return accumulated

    def pressure(self):
        return self.oil_force

    def attitude(self):
        return 0.0, 0.0


def test_row_count_and_columns_are_consistent():
    assert COLUMN["t"] == 0
    assert U.stop - U.start == 4 and V.start == U.stop


@pytest.mark.parametrize("setting", SETTINGS)
def test_fast_path_decision_agrees_with_share(setting):
    """Where the fast path applies, the full solution is exactly the request."""
    limiter = FlowLimiter(setting)
    hits = 0
    for _ in range(1500):
        u = RNG.uniform(-P.v_max, P.v_max, 4) * RNG.choice([0.0, 0.1, 1.0], 4)
        force = RNG.uniform(-2e3, 150e3, 4)
        p_load = limiter.pump.load_pressures_Pa(u, force)
        if limiter.pump.is_demand_met_with_margin(u, p_load):
            hits += 1
            assert np.array_equal(limiter.pump.solve(u, p_load).speed_m_s, u)
    assert hits > 100


def test_four_legs_at_v_max_take_the_fast_path_at_the_design_point():
    pump = FlowLimiter(FlowSetting(eta_v=0.95)).pump
    u = np.full(4, P.v_max)
    assert pump.is_demand_met_with_margin(u, pump.load_pressures_Pa(u, np.full(4, 90e3)))


def test_load_pressure_formula():
    limiter = FlowLimiter(FlowSetting())
    u = np.array([P.v_max, -P.v_max, 0.0, P.v_max / 2])
    force = np.array([100e3, 100e3, 100e3, 50e3])
    pressures = limiter.pump.load_pressures_Pa(u, force)
    back = (P.A_r[0] / (P.K_spool[0] / P.v_max * P.bt_ratio)) ** 2
    assert pressures[0] == pytest.approx((force[0] + P.A_r[0] * (P.p_T + back)) / P.A_h[0])
    assert pressures[1] == P.p_pilot


def test_disabled_limiter_returns_the_request_bits():
    setting = FlowSetting(is_enabled=False, eta_v=LOW_FLOW_ETA)
    plant_class = make_flow_plant_class(StubPlant, setting)
    plant = plant_class()
    plant.armed = True
    u = np.full(4, P.v_max)
    plant.step(u, 2)
    assert plant.last_input.tobytes() == u.tobytes()
    assert plant.flow_limiter.solved_chunks == 0


def test_not_armed_plant_bypasses_the_limiter():
    plant = make_flow_plant_class(StubPlant, FlowSetting(eta_v=LOW_FLOW_ETA))()
    plant.step(np.full(4, P.v_max), 2)
    assert len(plant.flow_limiter.rows()) == 0


def test_limited_plant_conserves_flow_and_outputs_operating_point():
    plant = make_flow_plant_class(StubPlant, FlowSetting(eta_v=LOW_FLOW_ETA))()
    plant.armed = True
    u = np.full(4, P.v_max)
    for _ in range(1200):
        plant.step(u, 2)
    limiter = plant.flow_limiter
    rows = limiter.rows()
    assert len(rows) == 1200
    assert np.all(plant.last_input <= u) and np.any(plant.last_input < u)
    conservation = flow_conservation(rows, limiter.supply_m3_s, limiter.counters())
    assert conservation["max_sum_Q_over_supply_minus_1"] <= 1e-6
    assert conservation["demand_met_chunks"] == 0
    inputs = saturation_inputs(rows, {})
    assert inputs["sets"], "the steady saturation lasts 1.2 s"
    point = next(iter(inputs["sets"].values()))["operating_point"]
    assert point["p_P_Pa"] > 0 and point["u_m_s"]["FL"] == pytest.approx(P.v_max)


def test_deepcopy_keeps_an_independent_record():
    plant = make_flow_plant_class(StubPlant, FlowSetting(eta_v=0.95))()
    plant.armed = True
    plant.step(np.zeros(4), 2)
    branch = copy.deepcopy(plant)
    branch.step(np.zeros(4), 2)
    assert len(plant.flow_limiter.rows()) == 1
    assert len(branch.flow_limiter.rows()) == 2


def test_swaps_count_only_disjoint_groups():
    fl, fr, rl = 1, 2, 4
    masks = np.array([fl, fl | fr, fr, 0, fr, rl, fl | rl, rl, fl], float)
    count, indices = count_disjoint_swaps(masks)
    assert count == 2
    assert indices.tolist() == [5, 8]


def test_run_table_has_the_sixty_runs_of_the_criteria():
    runs = build_runs()
    on_runs = [r for r in runs if r.bundle != "OFF"]
    counts = {bundle: sum(r.bundle == bundle for r in on_runs) for bundle in "ABCDE"}
    assert counts == {"A": 24, "B": 24, "C": 2, "D": 6, "E": 4}
    assert sum(r.bundle == "OFF" for r in runs) == len(ALL_CASE_IDS) == 24
    assert len({r.run_id for r in runs}) == len(runs)
    assert all(r.setting.eta_v == 0.95 for r in runs if r.bundle == "C")
    assert all(r.setting.is_enabled for r in on_runs)


def test_decision_cases_wait_for_a_choice():
    assert resolve_case("R13", {}) is None
    assert resolve_case("S6", {}) is None
    assert resolve_case("R13", {"R13": "ss_fs4"}).twin.event == "SS"
    assert resolve_case("S6", {"S6": "run_180s"}).twin.stored_id == "H6|J2|B|top|flat|m1.1"
    with pytest.raises(ValueError):
        resolve_case("R13", {"R13": "other"})


AFFINITY_SCRIPT = """
import ctypes
import sys
from multiprocessing import Pool

sys.path.insert(0, sys.argv[1])


def read_mask(_=None):
    kernel = ctypes.WinDLL("kernel32")
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.GetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
                                              ctypes.POINTER(ctypes.c_size_t)]
    process, system = ctypes.c_size_t(), ctypes.c_size_t()
    kernel.GetProcessAffinityMask(kernel.GetCurrentProcess(), ctypes.byref(process),
                                  ctypes.byref(system))
    return process.value


if __name__ == "__main__":
    import run_verdict

    run_verdict._set_affinity(sys.argv[2])
    with Pool(1) as pool:
        print(read_mask(), pool.apply(read_mask, (0,)))
"""
AFFINITY_TEST_MASK = 0x3
DECISIONS = {"R13": "ss_fs4", "S6": "alias_s5", "R2": "reanchor_on"}


@pytest.mark.skipif(sys.platform != "win32", reason="Windows affinity call")
def test_affinity_reaches_the_parent_and_a_spawned_worker_under_isolated_mode(tmp_path):
    """``-I`` as the runner is started: the import must not depend on the working directory."""
    script = tmp_path / "read_affinity.py"
    script.write_text(AFFINITY_SCRIPT, encoding="utf-8")
    done = subprocess.run(
        [sys.executable, "-I", "-B", str(script), str(HERE), hex(AFFINITY_TEST_MASK)],
        capture_output=True, text=True, cwd=tmp_path, timeout=240)
    assert done.returncode == 0, done.stderr
    assert done.stdout.split()[-2:] == [str(AFFINITY_TEST_MASK)] * 2


def test_bad_affinity_mask_is_refused():
    import run_verdict

    with pytest.raises(ValueError):
        run_verdict._set_affinity("not_a_mask")


def _store_result(out_dir, run, decision):
    import run_verdict

    payload = {"run_id": run.run_id,
               "definition_sha256": run_verdict.definition_digest(run, decision)}
    (out_dir / f"{run.run_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def _runs_finished_before_the_decisions(tmp_path):
    """Results as they stand: OFF without S6 / R13 and C, all made without a decision."""
    import run_verdict

    runs, _, aliased = run_verdict.split_runs(build_runs(), DECISIONS)
    for run in build_runs():
        if run.bundle == "C" or (run.bundle == "OFF" and run.case_id not in ("S6", "R13")):
            _store_result(tmp_path, run, None)
    return runs, aliased


def test_decisions_give_the_expected_table(tmp_path):
    import run_verdict

    runs, aliased = _runs_finished_before_the_decisions(tmp_path)
    assert sorted(r.run_id for r in aliased) == ["A_S6_eta0.85", "B_S6_eta0.90", "OFF_S6"]
    todo = run_verdict.todo_runs(runs, tmp_path, DECISIONS)
    counts = {b: sum(r.bundle == b for r in todo) for b in ("OFF", "A", "B", "C", "D", "E")}
    assert (len(runs), len(todo)) == (81, 58)
    assert counts == {"OFF": 2, "A": 23, "B": 23, "C": 0, "D": 6, "E": 4}
    assert sorted(r.run_id for r in todo if r.bundle == "OFF") == ["OFF_R13", "OFF_R2"]


def test_decision_is_part_of_the_resume_key(tmp_path):
    import run_verdict

    off_r2 = next(r for r in build_runs() if r.run_id == "OFF_R2")
    _store_result(tmp_path, off_r2, None)
    assert run_verdict.is_complete(tmp_path, off_r2, None)
    assert not run_verdict.is_complete(tmp_path, off_r2, "reanchor_on")
    _store_result(tmp_path, off_r2, "reanchor_on")
    assert run_verdict.is_complete(tmp_path, off_r2, "reanchor_on")
    assert not run_verdict.is_complete(tmp_path, off_r2, None)


@pytest.mark.parametrize("decision, is_on", [("reanchor_on", True), ("reanchor_off", False),
                                             (None, False)])
def test_reanchor_decision_reaches_the_harness_input(decision, is_on):
    import verdict_runs  # sets the harness path before the next import
    from verdict_cases import CASES, REANCHOR_ON

    slope = importlib.import_module("s9_soil_slope")
    twin = resolve_case("R2", {} if decision is None else {"R2": decision}).twin
    payload = verdict_runs._steady_case_dict(twin, slope, decision == REANCHOR_ON)
    assert slope.run_case_input(payload)["variant"]["reanchor"] is is_on
    assert (payload["roll_deg"], payload["pitch_deg"]) == (0.0, 3.5)
    assert CASES["R2"].twin.stored_id == "base|rigid|0,3.5|top|Fs4|b1"


def test_r13_decision_gives_the_ss_branch_of_the_runner():
    from verdict_cases import PATH_EVENT

    case = resolve_case("R13", DECISIONS)
    assert case.path == PATH_EVENT
    twin = case.twin
    assert (twin.event, twin.leg, twin.timing, twin.fs_kN) == ("SS", "RR", "ready", 4.0)


def test_clip_bundle_is_outside_the_criteria_table_and_has_its_own_ids():
    import run_verdict

    default_bundles = ["OFF", "A", "B", "C", "D", "E"]
    assert not [r for r in run_verdict.selected_runs(default_bundles, []) if r.clip_command]
    clipped = run_verdict.selected_runs(["CL"], ["S1"])
    assert sorted(r.run_id for r in clipped) == ["CL_OFF_S1", "CL_S1_eta0.85", "CL_S1_eta0.90"]
    assert all(r.clip_command for r in clipped)
    stored_ids = {r.run_id for r in build_runs()}
    assert not stored_ids & {r.run_id for r in build_clip_runs()}
    assert run_verdict.default_out_dir(["CL"]) == run_verdict.CLIP_OUT
    assert run_verdict.default_out_dir(["OFF", "A"]) == run_verdict.DEFAULT_OUT


def test_clip_is_part_of_the_resume_key_and_absent_from_the_stored_key(tmp_path):
    import run_verdict

    plain = next(r for r in build_runs() if r.run_id == "OFF_R1")
    clipped = replace(plain, clip_command=True)
    plain_digest = run_verdict.definition_digest(plain, None)
    assert plain_digest != run_verdict.definition_digest(clipped, None)
    _store_result(tmp_path, plain, None)
    assert not run_verdict.is_complete(tmp_path, clipped, None)
    assert plain_digest == STORED_OFF_R1_DIGEST


def test_command_clip_limits_the_valve_input_and_keeps_the_command():
    module = SimpleNamespace(_lagged_step=None)
    seen = []

    def lagged_step(plant, command, valve, steps):
        seen.append(np.array(command))
        valve[:] = command
        return "accumulated"

    lagged_step.is_truth_hook = True
    module._lagged_step = lagged_step
    record = install_command_clip(module, P.v_max)
    command = np.array([2.0, -2.0, 0.5, -0.5]) * P.v_max
    original = command.copy()
    valve = np.zeros(4)
    assert module._lagged_step(None, command, valve, 2) == "accumulated"
    assert seen[0].tolist() == [P.v_max, -P.v_max, 0.5 * P.v_max, -0.5 * P.v_max]
    assert command.tobytes() == original.tobytes()
    assert record.peak_command_m_s == pytest.approx(2.0 * P.v_max)
    assert record.peak_valve_m_s == pytest.approx(P.v_max)
    assert module._lagged_step.is_truth_hook


def test_reanchor_on_off_run_is_not_compared_with_the_stored_row():
    import aggregate_verdict

    runs = {"OFF_R2": {"bundle": "OFF", "case_id": "R2", "decision": "reanchor_on",
                       "harness_commands_sha256": "x"}}
    assert aggregate_verdict.off_identity(runs)[0]["is_same"] is None
