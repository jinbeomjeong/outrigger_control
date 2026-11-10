"""Tests of the ideal-sensor stage 1 tools (plan 8.6 with rev1 R1-7).

``ideal_sensor_targeted.py``: LOC rule (debounce, hysteresis, node gap), revocation count, IZ
sinking-rate slope, S4 chunk mean, tags, the K1-off arm, the keys / plan file gates and the
bundle counts; ``r64_g4_ideal_s4.py``: the chunk jump split; the two replay tools: IDEAL records
refused with exit 2. The ``sim`` tests run harness rows in a dynamics-dev subprocess (the
stored hashes are that env's) against the main checkout's stored lines; they are skipped when
either is missing.

Run (Chrono-dev, project root): python -I -B -m pytest <this file> -p no:cacheprovider
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src", ROOT / "04_scripts" / "03_control" / "s8"):
    sys.path.insert(0, str(_path))

import ideal_sensor_targeted as ideal  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
import r64_g4_ideal_s4 as hf  # noqa: E402

from outrigger_sim.control import c2  # noqa: E402
from outrigger_sim.hydraulics import v5_options  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

DYNAMICS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
E_CORE_MASK = "0FFF0000"
SHD_KEYS = ("D1|H-S-A|G1+J1@FL|B|flat|K1|V0|e0.002",  # A_P0 (stored Y-Pa)
            "D1|H-S-0|J2|B|fdown-rec|K1|V0|e0.002",  # C (stored S-C)
            "D1|H-R-0|rigid|T|roll-val|K1|V0|e0.002")  # F (stored las_T2 b0)
IZ_RIGID_KEY = SHD_KEYS[2]
"""Shortest stored rows of their sets; the F row is a pure rigid floor (H-R-0)."""


def main_checkout_root() -> Path | None:
    """This checkout when it has the stored lines, else the main checkout's root."""
    marker = ideal.V5_RELATIVE / "soil_defer" / "s2d_SC.jsonl"
    if (ROOT / marker).exists():
        return ROOT
    try:
        common = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute",
                                 "--git-common-dir"], capture_output=True, text=True,
                                check=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    candidate = Path(common).parent
    return candidate if (candidate / marker).exists() else None


# ------------------------------------------------------------------------------- LOC rule
def test_loc_needs_two_contact_free_periods_and_returns_the_first() -> None:
    rule = ideal.IdealLocRule()
    assert rule.step(True, 0.010, "a") is None
    assert rule.step(False, 0.010, "b") is None
    assert rule.step(False, 0.010, "c") == "b"


def test_contact_restarts_the_debounce() -> None:
    rule = ideal.IdealLocRule()
    assert rule.step(False, 0.010, "a") is None
    assert rule.step(True, 0.010, "b") is None
    assert rule.step(False, 0.010, "c") is None
    assert rule.step(False, 0.010, "d") == "c"


def test_gap_hysteresis() -> None:
    rule = ideal.IdealLocRule()
    assert rule.step(True, 0.0025, 0) is None  # latch on above 2 mm
    assert rule.step(False, 0.0012, 1) is None  # 1.2 mm: still on (off below 1 mm)
    assert rule.step(False, 0.0012, 2) == 1
    rule = ideal.IdealLocRule()
    rule.step(True, 0.0025, 0)
    rule.step(True, 0.0009, 1)  # below 1 mm: off
    assert rule.step(False, 0.0015, 2) is None  # 1.5 mm does not switch it on again
    assert rule.step(False, 0.0015, 3) is None
    assert rule.step(False, 0.0021, 4) == 2


def test_revocation_after_one_contact_period() -> None:
    run = ideal.ContactRun()
    assert ideal.REVOKE_CONTACT_PERIODS == 1
    assert run.step(False) is False
    assert run.step(True) is True
    assert run.step(False) is False


def _source(box_min_m: float, node_min_m: float) -> ideal.IdealSource:
    return ideal.IdealSource(
        t_s=1.0, chunks=100, cr_max_N=0.0, has_crawler_contact=False,
        g_box_m=np.array([box_min_m, 0.01, 0.01, 0.01]), g_node_min_m=node_min_m,
        z_m=np.zeros(4), sp_m=None, corner_h_plane_m=None, p_bar_head_Pa=np.zeros(4),
        p_bar_rod_Pa=None, f_z_bar_m_s2=None, is_last_chunk_equal=True)


def test_loc_gap_uses_the_node_minimum() -> None:
    """rev1 R1-3 ②: box minimum below the threshold, node minimum above it."""
    assert ideal.LOC_GAP_REFERENCE == "node"
    source = _source(box_min_m=-0.004, node_min_m=0.003)
    assert ideal.loc_gap_m(source) == pytest.approx(0.003)
    node, box = ideal.IdealLocRule(), ideal.IdealLocRule()
    results = []
    for index in range(3):
        results.append((node.step(False, ideal.loc_gap_m(source), index),
                        box.step(False, ideal.loc_gap_m(source, "box"), index)))
    assert results[1] == (0, None)
    assert all(box_result is None for _, box_result in results)


class _StubPlant:
    """Rigid body pitched by ``theta`` above a level floor (``n = e_z``), lifted by ``h``."""

    def __init__(self, theta: float, h: float) -> None:
        self.q = theta
        self.r = np.array([0.0, 0.0, h])
        self.nrm = np.array([0.0, 0.0, 1.0])
        self.body = SimpleNamespace(com=np.zeros(3))
        self.geo = SimpleNamespace(crawler_xy_box=((-3.0, 3.0), (-1.4, 1.4)),
                                   crawler_bottom_z=-1.0)
        xs = np.linspace(-2.6, 2.6, 6)
        self.cr_rel = np.array([[x, y, -1.0] for x in xs for y in (-1.2, 1.2)])


def _pitch_rotation(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def test_node_loc_comes_before_the_box_loc_on_a_slope() -> None:
    """rev1 R1-1: ``g_node_min >= g_box_min``; lifting a pitched body, the node rule fires first."""
    node, box = ideal.IdealLocRule(), ideal.IdealLocRule()
    node_t = box_t = None
    for step in range(200):
        plant = _StubPlant(np.radians(2.0), 1.08 + 0.0005 * step)
        box_gap = float(np.min(ideal.crawler_box_gaps_m(plant, _pitch_rotation)))
        node_gap = float(np.min(ideal.crawler_node_gaps_m(plant, _pitch_rotation)))
        assert node_gap >= box_gap
        if node_t is None and node.step(False, node_gap, step) is not None:
            node_t = step
        if box_t is None and box.step(False, box_gap, step) is not None:
            box_t = step
    assert node_t is not None and box_t is not None and node_t < box_t


# ------------------------------------------------------------------------------- IZ slope
def test_iz_rate_is_the_one_second_least_squares_slope() -> None:
    """rev1 R1-4: linear sinkage gives its slope; a bend differs from the last period
    difference; axes FL - FR, RL - RR."""
    times = np.arange(10) * 0.1
    linear = np.column_stack([0.003 * times, np.zeros(10), 0.001 * times, 0.002 * times])
    rates = ideal.axis_differences(ideal.window_lsq_slopes(times, linear))
    assert rates == pytest.approx([0.003, -0.001])
    bent = linear.copy()
    bent[-1, 0] += 0.001  # last period jumps 1 mm on FL
    lsq = ideal.axis_differences(ideal.window_lsq_slopes(times, bent))
    period_difference = ideal.axis_differences((bent[-1] - bent[-2]) / 0.1)
    assert lsq[0] != pytest.approx(period_difference[0])
    assert lsq[0] == pytest.approx(0.003 + 0.001 * (times[-1] - times.mean())
                                   / ((times - times.mean()) ** 2).sum())


def test_iz_rates_follow_the_dsb75_window_times() -> None:
    controller = ideal.IdealSensorC2.from_params(load_params(), c2.C2Config().with_10hz_d1())
    controller.reset()
    times = [round(0.1 * k, 1) for k in range(10)]
    controller._state.diff_sink = SimpleNamespace(strokes=[(t, np.zeros(4)) for t in times])
    controller._ideal.z_by_t = {t: np.array([0.002 * t, 0.0, 0.0, 0.0]) for t in times}
    assert controller._ideal_sink_rates_m_s() == pytest.approx([0.002, 0.0])


# ------------------------------------------------------------------------------- S4
class _PressurePlant:
    def __init__(self) -> None:
        self.value = np.full(4, 1.0e5)

    def pressure(self):
        return self.value.copy()


def test_s4_mean_constant_and_step_split() -> None:
    accumulator = ideal.ChunkAccumulator()
    plant = _PressurePlant()
    for _ in range(100):
        accumulator.on_chunk(plant, np.zeros(24))
    _, _, chunks = accumulator.take()
    heads, rods = ideal._chunk_pressures(chunks, 1.0, None, False)
    assert rods is None and ideal.period_mean(heads) == pytest.approx(plant.value)
    jump, phase_ms = 150e5, 33
    means = []
    for period in range(2):
        for chunk in range(1, 101):
            t_ms = period * 100 + chunk
            plant.value = np.full(4, 1.0e5) + (jump if t_ms > phase_ms else 0.0)
            accumulator.on_chunk(plant, np.zeros(24))
        means.append(ideal.period_mean(ideal._chunk_pressures(accumulator.take()[2], 1.0, None,
                                                          False)[0])[0])
    assert means[0] - 1.0e5 == pytest.approx((1 - phase_ms / 100) * jump)
    assert means[1] - means[0] == pytest.approx(phase_ms / 100 * jump)


class _StepPlant(_PressurePlant):
    dt = 1e-3

    def step(self, mean_speed, nsteps):
        return np.zeros(24)


def test_chunk_hook_sees_the_plant_behind_the_overlap_cut() -> None:
    """VB / LS: ``install_overlap_cut`` wraps the hook and passes a ``_CutPlant`` view; the
    hook must record the plant itself (I-0 attempt 1, 2026-11-10)."""
    import harness_hydraulics

    closed_loop = SimpleNamespace(_lagged_step=lambda plant, command, valve, steps:
                                  plant.step(command, steps))
    ideal.install_chunk_hook(closed_loop)
    setting = SimpleNamespace(overlap_speed_m_s=lambda v_max: 0.0)
    harness_hydraulics.install_overlap_cut(closed_loop, setting, 0.02, 1e-9)
    plant = _StepPlant()
    ideal.ACCUMULATOR.take()
    closed_loop._lagged_step(plant, np.zeros(4), np.zeros(4), 1)
    assert ideal.ACCUMULATOR.plant is plant
    count, _, chunks = ideal.ACCUMULATOR.take()
    assert count == 1 and np.array_equal(chunks[0].net_N, plant.value)
    ideal.ACCUMULATOR.plant = None

@pytest.mark.parametrize("phase_ms", hf.PHASES_MS)
def test_hf_chunk_jump_splits_over_two_periods(phase_ms) -> None:
    t_ev = 40.0
    t_arm = hf.arm_time_s(t_ev, 0.05, phase_ms)
    first = [t_ev + k * 1e-3 for k in range(1, 101)]
    active = sum(hf.is_jump_active(t, t_arm) for t in first)
    assert active == 100 - phase_ms
    assert hf.arm_period_index(t_ev, t_arm) == 1
    assert hf.is_jump_active(t_ev + 0.1, t_arm)  # the base reading of that period has it


# ------------------------------------------------------------------------------- tags, K1
def test_ideal_tags_are_not_any_switch_tag() -> None:
    for base in ("final_C4G2_LAS_K1", "final_C4G2_P3_LAS_K1", "final_C4G2_LAS",
                 "final_C4G2_P3_LAS"):
        for variant in ideal.Variant:
            tag = ideal.ideal_tag(base, variant)
            assert tag == f"{base}_IDEAL-{variant.value}"
            assert ideal.is_ideal_tag(tag)
            assert not v5_options.is_liftoff_slow_tag(tag)
            assert not v5_options.is_order_gate_tag(tag)
            assert not v5_options.is_extend_start_tag(tag)


def _controller(variant: str, arm: str, base=c2.C2Controller):
    cls = ideal.ideal_controller_class(base, ideal.IdealSettings(variant, arm))
    return cls.from_params(load_params(), c2.C2Config().with_10hz_d1())


def test_k1_off_arm_installs_the_gate_false() -> None:
    assert c2.C2Config().with_10hz_d1().slope_clearance_margin.flat_soil_margin_order_gate
    off = _controller("SHD", ideal.K1_ARM_OFF)
    on = _controller("SHD", ideal.K1_ARM_ON)
    assert off.config.slope_clearance_margin.flat_soil_margin_order_gate is False
    assert on.config.slope_clearance_margin.flat_soil_margin_order_gate is True
    assert ideal.base_tag_of({"setting": "V0"}, off) == "final_C4G2_LAS"
    assert ideal.base_tag_of({"setting": "V0"}, on) == "final_C4G2_LAS_K1"


def test_k1_request_effective_mismatch_raises() -> None:
    class GateForcedOn(c2.C2Controller):
        def __init__(self, geometry, config=None):
            from dataclasses import replace

            margin = replace(config.slope_clearance_margin, flat_soil_margin_order_gate=True)
            super().__init__(geometry, replace(config, slope_clearance_margin=margin))

    with pytest.raises(RuntimeError, match="K1 order gate"):
        _controller("SHD", ideal.K1_ARM_OFF, GateForcedOn)


def test_igb_turns_both_margins_off_and_records_them() -> None:
    controller = _controller("IGB", ideal.K1_ARM_ON)
    margin = controller.config.slope_clearance_margin
    assert margin.enable is False and margin.flat_soil_margin_m == 0.0
    assert controller._ideal_disabled == {"slope_clearance_margin.enable": True,
                                          "slope_clearance_margin.flat_soil_margin_m": 0.03}


def test_shd_controller_without_source_is_the_parent() -> None:
    """No chunk hook (no plant): every override returns the parent result."""
    shd, plain = _controller("IGA", ideal.K1_ARM_ON), c2.C2Controller.from_params(
        load_params(), c2.C2Config().with_10hz_d1())
    rod = np.array([0.1, 0.12, 0.09, 0.11])
    assert np.array_equal(shd._clearance_corners_m(rod), plain._clearance_corners_m(rod))


# ------------------------------------------------------------------------------- replay tools
def _write_npz(path: Path, tag: str) -> None:
    np.savez(path, meta_json=np.array(json.dumps({"controller_tag": tag})))


def _run(args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    env = {**os.environ, "MKL_THREADING_LAYER": "TBB"}
    return subprocess.run([sys.executable, "-I", "-B", *args], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env, timeout=600)


def test_t4h_replay_refuses_ideal_records(tmp_path: Path) -> None:
    import t4h_replay

    t4h_replay.reject_ideal_record({"controller_tag": "final_C4G2_P3_LAS_K1"}, "x")
    with pytest.raises(t4h_replay.IdealRecordError):
        t4h_replay.reject_ideal_record({"controller_tag": "final_C4G2_P3_LAS_K1_IDEAL-S4"}, "x")
    record = tmp_path / "R1_e0_VB.npz"
    _write_npz(record, "final_C4G2_P3_LAS_K1_IDEAL-IGA")
    done = _run([str(HERE / "t4h_replay.py"), str(tmp_path / "out.json"), str(record)])
    assert done.returncode == 2, done.stdout + done.stderr
    assert "_IDEAL-IGA" in done.stdout
    assert not (tmp_path / "out.json").exists()


def test_chrono_replay_refuses_ideal_records(tmp_path: Path) -> None:
    import chrono_t45_replay as chrono

    chrono.reject_ideal_record({"controller_tag": "final_C4G2_P3_LAS_K1"}, "x")
    with pytest.raises(chrono.IdealRecordError):
        chrono.reject_ideal_record({"c2_setup": {"expect_controller": {
            "name": "final_C4G2_LAS_IDEAL-SHD"}}}, "x")
    case = tmp_path / "case"
    case.mkdir()
    (case / "result.json").write_text(json.dumps({"controller_tag": "final_C4G2_LAS_K1_IDEAL-IZ"}),
                                      encoding="utf-8")
    done = _run([str(HERE / "chrono_t45_replay.py"), str(tmp_path / "out.json"), str(case)])
    assert done.returncode == 2, done.stdout + done.stderr
    assert "_IDEAL-IZ" in done.stdout


# ------------------------------------------------------------------------------- inputs
def test_registered_keys_and_plan_files_pass() -> None:
    key_sets, problems = ideal.load_key_sets(ideal.KEYS_PATH)
    assert problems == []
    assert sum(len(key_sets.sets[name]) for name in ideal.UNION_P0_SETS) == ideal.UNION_P0_COUNT
    assert ideal.plan_problems([ideal.PLAN_PATH, ideal.PLAN_REV1_PATH]) == []
    assert ideal.plan_problems([ideal.PLAN_REV1_PATH, ideal.PLAN_PATH]) != []


def test_bundle_key_counts() -> None:
    key_sets, _ = ideal.load_key_sets(ideal.KEYS_PATH)
    counts = {name: len(spec.variants) * len(ideal.bundle_keys(spec, key_sets)) * len(spec.arms)
              for name, spec in ideal.BUNDLES.items()}
    assert counts == ideal.BUNDLE_COUNTS
    assert sum(counts.values()) == 859
    i0 = ideal.bundle_keys(ideal.BUNDLES["I-0"], key_sets)
    assert [key for _, key in i0[6:10]] == key_sets.sets["F"][:4]


def test_runner_refuses_a_changed_keys_file(tmp_path: Path, capsys) -> None:
    changed = tmp_path / "keys.json"
    changed.write_bytes(ideal.KEYS_PATH.read_bytes() + b"\n")
    assert ideal.main(["list", "--keys-file", str(changed)]) == 2
    assert ideal.main(["run", "--bundle", "I-0", "--keys-file", str(changed)]) == 2
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["stop"] == "input"


def test_list_on_the_stored_lines() -> None:
    root = main_checkout_root()
    if root is None:
        pytest.skip("stored lines not found (main checkout v5)")
    done = _run([str(HERE / "ideal_sensor_targeted.py"), "list", "--stored-root", str(root)])
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    assert "I-1: 805 runs" in done.stdout


# ------------------------------------------------------------------------------- harness rows
@pytest.fixture(scope="module")
def harness_lines(tmp_path_factory) -> dict[str, list[dict]]:
    """Runner trials in parallel: SHD on the three V0 keys, the whole I-0 bundle (VB rows, the
    overlap-cut plant view included) and IZ on the rigid key."""
    root = main_checkout_root()
    if root is None or not DYNAMICS_PYTHON.exists():
        pytest.skip("stored lines or dynamics-dev not found")
    env = {**os.environ, "MKL_THREADING_LAYER": "TBB", "MKL_NUM_THREADS": "1",
           "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "NUMBA_NUM_THREADS": "1"}
    requests = {"shd": ("I-1", "SHD", ",".join(SHD_KEYS), 3),
                "i0": ("I-0", "SHD", None, 8),
                "iz": ("I-1", "IZ", IZ_RIGID_KEY, 1)}
    folders = {name: tmp_path_factory.mktemp(name) for name in requests}
    processes = {}
    for name, (bundle, variant, keys, workers) in requests.items():
        command = [str(DYNAMICS_PYTHON), "-I", "-B", str(HERE / "ideal_sensor_targeted.py"),
                   "run", "--bundle", bundle, "--variant", variant, "--stored-root", str(root),
                   "--trial-out", str(folders[name]), "--workers", str(workers),
                   "--affinity", E_CORE_MASK, "--pool", "E"]
        if keys is not None:
            command += ["--keys", keys]
        processes[name] = subprocess.Popen(
            command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace")
    out = {}
    for name, process in processes.items():
        text, _ = process.communicate(timeout=1800)
        assert process.returncode == 0, text[-3000:]
        bundle, variant = requests[name][:2]
        path = folders[name] / ideal.out_name(bundle, variant)
        out[name] = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return out


@pytest.mark.sim
def test_i0_shd_reproduces_every_stored_hash(harness_lines) -> None:
    """All 14 I-0 rows (A_P0 V0 / VB, the boundary key, F rigid VB, E soil VB)."""
    lines = harness_lines["i0"]
    assert len(lines) == ideal.BUNDLE_COUNTS["I-0"]
    assert all("error" not in line for line in lines)
    assert {line["job"]["setting"] for line in lines} == {"V0", "VB"}
    for line in lines:
        assert line["ideal"]["matches_stored"], line["ideal"]["key"]
        assert line["ideal"]["last_chunk_mismatches"] == 0
        assert line["ideal"]["chunk_anomaly_count"] == 0
        assert line["controller_tag"] == f"{line['ideal']['base_tag']}_IDEAL-SHD"

@pytest.mark.sim
def test_shd_reproduces_the_stored_hashes(harness_lines) -> None:
    lines = harness_lines["shd"]
    assert sorted(line["ideal"]["key"] for line in lines) == sorted(SHD_KEYS)
    for line in lines:
        assert line["ideal"]["matches_stored"], line["ideal"]["key"]
        assert line["controller_tag"] == "final_C4G2_LAS_K1_IDEAL-SHD"
        assert line["ideal"]["last_chunk_mismatches"] == 0
        assert line["ideal"]["chunk_anomaly_count"] == 0
        periods = line["ideal"]["periods"]
        assert set(ideal.PERIOD_FIELDS) <= set(periods)
        assert all(len(periods[name]) == len(periods["t_s"]) for name in ideal.PERIOD_FIELDS)
        assert all(min(g) == g_min for g, g_min in zip(periods["g_box"], periods["g_min"],
                                                      strict=True))
        assert line["ideal"]["plan_sha256"] == list(ideal.PLAN_SHA256_LIST)


@pytest.mark.sim
def test_iz_on_a_rigid_floor_keeps_the_hash(harness_lines) -> None:
    (line,) = harness_lines["iz"]
    assert line["ideal"]["matches_stored"]
    assert line["controller_tag"] == "final_C4G2_LAS_K1_IDEAL-IZ"
