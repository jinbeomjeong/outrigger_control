"""D0 plant split of the 606f8713 j9_main failure (record, user decision 2026-11-23).

Fast checks: the seven variants and eight keys, the test-only switch of D0-3 and that importing
the runner switches nothing, the ``_empty_line`` record fix of ``check_open_delay`` and the
per-read P1 log. The slow check runs the harness in dynamics-dev: V0 keeps its golden hash,
VBJ (no D0 switch) and D0-1 (P1 read record on) keep the 606f8713 j9_main command hashes, every
variant runs the plant it names, and the runner and the summary work end to end from another
working directory.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from outrigger_sim.hydraulics import v5_options
from outrigger_sim.hydraulics.check_open_delay import (
    CheckDelayCircuit,
    CheckDelayInputs,
    CheckOpenGate,
)
from outrigger_sim.hydraulics.v5_options import CheckDelaySetting, HydraulicOptions, controller_tag

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
CHECK_RUNNER = Path(__file__).resolve().with_name("d0_split_check_runner.py")
RUNNER = COUPLED_DIR / "d0_plant_split.py"
SUMMARY = COUPLED_DIR / "d0_plant_split_summary.py"
GOLDEN_R12 = PROJECT_ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "golden_off" \
    / "OFF_R12.json"
TIMEOUT_S = 1800
BAR = 1.0e5
FL = 0

EXPECTED_KEYS = ("R12_o0.0", "R12_top-FL-Fs8-o0.0", "R12_bottom-FL-Fs4-o0.0",
                 "R12_top-FR-Fs4-o0.0", "R15_o0.0", "R15_o0.05", "S5_e0.0", "S1_e0.003")
J9_MAIN_VBJ_HASH = {
    "R12_o0.0": "018a5b60b41fe671f5d8d8fa7bda072bb2f087090ea7ba5573ae9041d943f10d",
    "S5_e0.0": "4d1ebcb74794b475903d12373a6dd60aee453bc896e5774474f7c6d8ccc8b7e7",
}
"""``commands_sha256`` of the VBJ lines of run 606f8713 ``j9main_a1/j9_main.jsonl`` (read
2026-11-23; S5 is also the T8 hash of the cause analysis 0.1)."""
SLOW_KEYS = ("R12_o0.0", "S5_e0.0")
"""Event path and steady path."""


@pytest.fixture(scope="module")
def d0():
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        import d0_plant_split as module

        yield module
    finally:
        sys.path.remove(str(COUPLED_DIR))


# ---------------------------------------------------------------------------- definitions
def test_variants_are_the_user_decision(d0) -> None:
    vbj = d0.run_v5.JP3_SETTINGS["VBJ"]
    vb = d0.run_v5.SETTINGS["VB"]
    assert vbj[1]["line_fill_gate"] == {"kind": "VN", "volume_scale": 1.0, "c_v": 0.02}
    nominal = vbj[1]["line_fill_gate"]
    without_gate = {k: v for k, v in vbj[1].items() if k != "line_fill_gate"}
    expected = {
        "D0-1": vbj[1],
        "D0-2": without_gate,
        "D0-3": {**vb[1], "line_fill_gate": nominal},
        "D0-4": {**vbj[1], "line_fill_gate": {**nominal, "volume_scale": 0.5}},
        "D0-5": {**vbj[1], "line_fill_gate": {**nominal, "c_v": 0.002}},
        "D0-6": {**vbj[1], "line_fill_gate": {**nominal, "c_v": 0.04}},
        "D0-7": {**vbj[1], "line_fill_gate": {**nominal, "volume_scale": 0.5, "c_v": 0.002}},
    }
    assert {name: plant for name, (_, plant) in d0.D0_SETTINGS.items()} == expected
    assert all(is_flow for is_flow, _ in d0.D0_SETTINGS.values()) and vbj[0] and vb[0]
    assert d0.D0_BASE_SETTING == {"D0-3": "VB", **{n: "VBJ" for n in expected if n != "D0-3"}}


def test_importing_the_runner_switches_nothing(d0) -> None:
    import harness_hydraulics

    assert not set(d0.D0_SETTINGS) & set(d0.run_v5.ALL_SETTINGS)
    assert not set(d0.D0_SETTINGS) & set(d0.run_v5.T4H_SETTINGS)
    assert v5_options.ALLOW_GATE_WITH_REV4_FOR_TEST is False
    assert harness_hydraulics.is_p1_read_record_on() is False


def test_keys_are_eight_j9_main_jobs_and_the_batch_is_56(d0) -> None:
    assert tuple(d0.D0_KEYS) == EXPECTED_KEYS
    j9_main = {d0.run_v5.job_key(job) for job in d0.run_v5.j9_main_jobs()}
    for job in d0.D0_KEYS.values():
        assert d0.run_v5.job_key({**job, "setting": "VBJ"}) in j9_main, job
    jobs = d0.d0_jobs()
    assert len(jobs) == 56 == len({d0.run_v5.job_key(job) for job in jobs})
    assert d0.run_v5.t4h_file_name(jobs[0]) == "R12_o0.0_D0-1.npz"


def test_d0_3_runs_only_with_the_test_switch_and_keeps_the_vb_tag(d0, monkeypatch) -> None:
    with pytest.raises(ValueError, match="revision 4"):
        HydraulicOptions.from_dict(d0.D0_SETTINGS["D0-3"][1])
    monkeypatch.setattr(v5_options, "ALLOW_GATE_WITH_REV4_FOR_TEST", True)
    for name, (_, plant) in d0.D0_SETTINGS.items():
        options = HydraulicOptions.from_dict(plant)
        v5_options.validate(options, period_s=0.1)
        expected_tag = "final_C4G2_P3" if name == "D0-3" else "final_C4G2_P3W"
        assert controller_tag(options) == expected_tag, name
        assert (options.line_fill_gate is None) == (name == "D0-2"), name


# ---------------------------------------------------------------------- check_open_delay
def _circuit() -> CheckDelayCircuit:
    return CheckDelayCircuit(head_area_m2=np.full(4, 1.3273e-2),
                             annulus_area_m2=np.full(4, 3.770e-3), stroke_m=0.7,
                             rod_dead_length_m=0.05, head_dead_length_m=0.05,
                             bulk_modulus_Pa=1.0e9, tank_pressure_Pa=2.0e5,
                             max_speed_m_s=0.020924, compensator_drop_Pa=10.0e5)


def _inputs(t_s: float, dt_s: float, speed_FL_m_s: float) -> CheckDelayInputs:
    u = np.zeros(4)
    u[FL] = speed_FL_m_s
    return CheckDelayInputs(t_s, dt_s, u, np.full(4, 90.0 * BAR), np.full(4, 2.0 * BAR),
                            np.ones(4, bool), np.zeros(4), np.zeros(4), np.full(4, 0.4))


def _empty_line_before_the_fix(model, i: int) -> None:
    """``CheckOpenDelay._empty_line`` of e029dc8c (no ``fill_start_t`` reset)."""
    model.x[i] = 0.0
    model.is_open[i] = False
    model.charged[i] = False
    model.line_dir[i] = 0
    model.crept[i] = 0.0
    model.rod_released[i] = False
    model.p_b_after[i] = np.nan


def _held_retract_then_extend(model) -> list:
    """FL retracts slowly (held, the dead stroke never fills) for 0.3 s, then extends at
    0.25 v_max until the head check opens; the per-step outputs."""
    dt_s, outputs = 1.0e-3, []
    for k in range(300):
        outputs.append(model.filter(_inputs(k * dt_s, dt_s, -1.0e-4)))
    for k in range(300, 3000):
        outputs.append(model.filter(_inputs(k * dt_s, dt_s, 0.25 * 0.020924)))
        if model.is_open[FL]:
            break
    return outputs


def test_direction_change_resets_the_fill_start() -> None:
    model = CheckOpenGate(CheckDelaySetting("VN"), _circuit())
    _held_retract_then_extend(model)
    extend_fills = [fill for fill in model.fills if fill[2] == FL and fill[3] == 1]
    assert len(extend_fills) == 1
    start_s, open_s = extend_fills[0][:2]
    assert start_s == pytest.approx(0.3, abs=1e-9)  # the first extend step, not the retract hold
    assert open_s > start_s


def test_the_record_fix_leaves_speeds_and_line_state_alone(monkeypatch) -> None:
    fixed = CheckOpenGate(CheckDelaySetting("VN"), _circuit())
    old = CheckOpenGate(CheckDelaySetting("VN"), _circuit())
    monkeypatch.setattr(old, "_empty_line", lambda i: _empty_line_before_the_fix(old, i))
    for new_out, old_out in zip(_held_retract_then_extend(fixed), _held_retract_then_extend(old),
                                strict=True):
        assert np.array_equal(new_out.speed_m_s, old_out.speed_m_s)
        assert np.array_equal(new_out.opening_rod_pressure_Pa, old_out.opening_rod_pressure_Pa,
                              equal_nan=True)
    for name in ("x", "line_dir", "is_open", "charged", "rod_released"):
        assert np.array_equal(getattr(fixed, name), getattr(old, name)), name
    assert [fill[1:] for fill in fixed.fills] == [fill[1:] for fill in old.fills]
    assert [fill[0] for fill in old.fills if fill[3] == 1 and fill[2] == FL] == [0.0]


def test_step_record_fields_name_the_active_legs_only() -> None:
    model = CheckOpenGate(CheckDelaySetting("VN"), _circuit())
    model.filter(_inputs(0.0, 1.0e-3, -1.0e-4))
    assert np.isfinite(model.step_need_m[FL]) and model.step_need_m[FL] > 0.0
    assert np.isfinite(model.step_drain_m_s[FL])
    assert np.isnan(model.step_need_m[1:]).all() and np.isnan(model.step_drain_m_s[1:]).all()
    model.filter(_inputs(1.0e-3, 1.0e-3, 1.0e-3))  # the extend step has a drain, no need
    assert np.isnan(model.step_need_m[FL]) and np.isfinite(model.step_drain_m_s[FL])


# ---------------------------------------------------------------------------- P1 read log
def test_p1_read_log_aligns_on_the_t4h_reads(d0) -> None:
    import harness_hydraulics

    log = harness_hydraulics.P1ReadLog()
    gate = SimpleNamespace(x=np.array([1e-4, 0, 0, 0]), step_need_m=np.full(4, np.nan),
                           step_drain_m_s=np.zeros(4), line_dir=np.array([1, 0, 0, -1]),
                           is_open=np.zeros(4, bool), charged=np.zeros(4, bool),
                           rod_released=np.array([True, False, False, False]))
    log.note_chunk(np.array([True, False, False, False]), np.array([2e-4, 0, 0, 0]))
    log.note_read(0.1, gate)
    gate.x = np.array([2e-4, 0, 0, 0])
    log.note_read(0.2, gate)
    arrays = log.arrays_at(np.array([0.1, 0.15, 0.2]))
    assert arrays["p1_read_found"].tolist() == [True, False, True]
    assert arrays["p1_x_m"][:, 0].tolist()[0] == 1e-4 and arrays["p1_x_m"][2, 0] == 2e-4
    assert np.isnan(arrays["p1_x_m"][1]).all()
    assert arrays["p1_line_dir"][0].tolist() == [1, 0, 0, -1]
    assert arrays["p1_gate_held"][:, 0].tolist() == [True, False, True]
    assert all(value.shape[0] == 3 for value in arrays.values())


# ------------------------------------------------------------------- CLI refusals (cheap)
def _run(script: Path, *arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([str(HARNESS_PYTHON), "-I", "-B", str(script), *arguments],
                          cwd=cwd, env=environment, capture_output=True, text=True,
                          encoding="utf-8", timeout=TIMEOUT_S)


def _last_json(process: subprocess.CompletedProcess) -> dict:
    return json.loads(process.stdout.strip().splitlines()[-1])


def test_runner_lists_56_jobs_and_refuses_unknown_names(tmp_path: Path) -> None:
    listed = _run(RUNNER, "--out", str(tmp_path / "d0.jsonl"), "--list", cwd=tmp_path)
    assert listed.returncode == 0 and _last_json(listed)["planned"] == 56
    bad = _run(RUNNER, "--out", str(tmp_path / "d0.jsonl"), "--variants", "D0-9", cwd=tmp_path)
    assert bad.returncode == 2 and _last_json(bad)["status"] == "input_error"
    assert not (tmp_path / "d0.jsonl").exists()


def test_runner_tool_error_is_exit_3(tmp_path: Path) -> None:
    folder_as_out = tmp_path / "taken.jsonl"
    folder_as_out.mkdir()  # reading the done keys of a folder fails before any run
    process = _run(RUNNER, "--out", str(folder_as_out), "--keys", "R12_o0.0",
                   "--variants", "D0-1", cwd=tmp_path)
    assert process.returncode == 3 and _last_json(process)["status"] == "tool_error"


def test_summary_input_errors_incomplete_and_tool_error(tmp_path: Path) -> None:
    missing = _run(SUMMARY, "--rows", str(tmp_path / "none.jsonl"),
                   "--out", str(tmp_path / "a.json"), cwd=tmp_path)
    assert missing.returncode == 2 and _last_json(missing)["status"] == "input_error"
    rows = tmp_path / "rows.jsonl"
    rows.write_text(json.dumps({"job": {"case": "S5", "eps": 0.0, "setting": "D0-1"},
                                "error": "x"}) + "\n", encoding="utf-8")
    incomplete = _run(SUMMARY, "--rows", str(rows), "--out", str(tmp_path / "b.json"),
                      cwd=tmp_path)
    assert incomplete.returncode == 2 and _last_json(incomplete)["status"] == "incomplete"
    report = json.loads((tmp_path / "b.json").read_text(encoding="utf-8"))
    assert len(report["checks"]["error_lines"]) == 1 and len(report["checks"]["missing_jobs"]) == 56
    existing = _run(SUMMARY, "--rows", str(rows), "--out", str(tmp_path / "b.json"), cwd=tmp_path)
    assert existing.returncode == 2 and _last_json(existing)["status"] == "input_error"
    broken = tmp_path / "broken.jsonl"
    broken.write_text("{not json\n", encoding="utf-8")
    tool = _run(SUMMARY, "--rows", str(broken), "--out", str(tmp_path / "c.json"), cwd=tmp_path)
    assert tool.returncode == 3 and _last_json(tool)["status"] == "tool_error"


# ------------------------------------------------------------------ harness (dynamics-dev)
def _check_job(job: dict, folder: Path) -> subprocess.Popen:
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "PYTHONDONTWRITEBYTECODE": "1"}
    folder.mkdir(parents=True)
    return subprocess.Popen([str(HARNESS_PYTHON), "-I", "-B", str(CHECK_RUNNER), json.dumps(job),
                             str(folder / "t4h"), str(folder / "report.json")],
                            cwd=folder, env=environment)


@pytest.fixture(scope="module")
def harness_runs(tmp_path_factory, d0) -> dict:
    """All harness runs at once: the D0 runner on two keys x seven variants, and V0 / VBJ
    through ``run_v5.run_one`` without any D0 switch (each from its own working folder)."""
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")
    root = tmp_path_factory.mktemp("d0")
    work = root / "work"
    work.mkdir()
    out = root / "runs" / "d0.jsonl"
    environment = {**os.environ, "MKL_THREADING_LAYER": "TBB", "PYTHONDONTWRITEBYTECODE": "1"}
    runner = subprocess.Popen([str(HARNESS_PYTHON), "-I", "-B", str(RUNNER), "--out", str(out),
                               "--keys", ",".join(SLOW_KEYS), "--workers", "14"],
                              cwd=work, env=environment, stdout=subprocess.PIPE, text=True,
                              encoding="utf-8")
    checks = {"V0_R12_o0.0": {**d0.D0_KEYS["R12_o0.0"], "setting": "V0"},
              **{f"VBJ_{key}": {**d0.D0_KEYS[key], "setting": "VBJ"} for key in SLOW_KEYS}}
    processes = {name: _check_job(job, root / name) for name, job in checks.items()}
    stdout, _ = runner.communicate(timeout=TIMEOUT_S)
    for process in processes.values():
        process.wait(timeout=TIMEOUT_S)
    assert all(process.returncode == 0 for process in processes.values())
    reports = {name: json.loads((root / name / "report.json").read_text(encoding="utf-8"))
               for name in processes}
    lines = [json.loads(text) for text in out.read_text(encoding="utf-8").splitlines()]
    return {"root": root, "out": out, "runner_exit": runner.returncode,
            "runner_last": json.loads(stdout.strip().splitlines()[-1]), "reports": reports,
            "lines": {(line["job"]["setting"], d0.key_name(line["job"])): line for line in lines}}


@pytest.mark.slow
def test_off_paths_keep_the_golden_and_the_j9_main_hashes(harness_runs) -> None:
    reports = harness_runs["reports"]
    golden = json.loads(GOLDEN_R12.read_text(encoding="utf-8"))["commands_sha256"]
    assert reports["V0_R12_o0.0"]["hash"] == golden
    for key in SLOW_KEYS:
        report = reports[f"VBJ_{key}"]
        assert report["hash"] == J9_MAIN_VBJ_HASH[key], key
        assert not any(name.startswith("p1_") for name in report["t4h_arrays"]), key
        assert report["has_p1_read_record"] is False
    assert all(report["foreign_modules"] == [] for report in reports.values())


@pytest.mark.slow
def test_d0_1_with_the_p1_read_record_keeps_commands_and_values(harness_runs) -> None:
    for key in SLOW_KEYS:
        line = harness_runs["lines"][("D0-1", key)]
        off = harness_runs["reports"][f"VBJ_{key}"]
        assert line["commands_sha256"] == J9_MAIN_VBJ_HASH[key] == off["hash"], key
        # JSON text: a NaN value compares equal to itself only this way
        assert _json_text(line["values"]) == _json_text(off["values"]), key
        assert _json_text(line["event_output"]) == _json_text(off["event_output"]), key


def _json_text(value) -> str:
    return json.dumps(value, sort_keys=True)


@pytest.mark.slow
def test_every_variant_runs_its_plant(harness_runs, d0, monkeypatch) -> None:
    monkeypatch.setattr(v5_options, "ALLOW_GATE_WITH_REV4_FOR_TEST", True)
    assert harness_runs["runner_exit"] == 0
    assert harness_runs["runner_last"]["status"] == "ok"
    assert harness_runs["runner_last"]["run"] == 2 * len(d0.D0_SETTINGS)
    t4h = harness_runs["out"].with_name("d0_t4h")
    for (variant, key), line in harness_runs["lines"].items():
        options = HydraulicOptions.from_dict(d0.D0_SETTINGS[variant][1])
        assert line["hydraulic_options"] == options.to_dict(), (variant, key)
        tag = "final_C4G2_P3_LAS_K1" if variant == "D0-3" else "final_C4G2_P3W_LAS_K1"
        assert line["controller_tag"] == tag, (variant, key)
        assert line["d0"]["foreign_modules"] == [] and line["d0"]["variant"] == variant
        gate_record = (line["hydraulics_record"] or {}).get("line_fill_gate")
        with np.load(t4h / line["t4h_file"], allow_pickle=False) as data:
            if options.line_fill_gate is None:
                assert gate_record is None and "p1_read_found" not in data.files
                continue
            assert gate_record["setting"] == {
                "kind": "VN", "volume_scale": options.line_fill_gate.volume_scale,
                "c_v": options.line_fill_gate.c_v}, (variant, key)
            assert data["p1_read_found"].all(), (variant, key)
            assert data["p1_x_m"].shape == data["command_m_s"].shape


@pytest.mark.slow
def test_progress_and_identity_files(harness_runs) -> None:
    out = harness_runs["out"]
    progress = json.loads(out.with_name("d0.progress.json").read_text(encoding="utf-8"))
    assert progress["stage"] == "end" and progress["done"] == progress["total"] == 14
    assert set(progress) == {"stage", "done", "total", "unit", "started_at", "updated_at"}
    identity = json.loads(out.with_name("d0.identity.json").read_text(encoding="utf-8"))
    assert set(identity) == {"start", "end"}


@pytest.mark.slow
def test_summary_end_to_end_from_another_folder(harness_runs, tmp_path: Path) -> None:
    out = harness_runs["out"]
    reference = tmp_path / "reference.jsonl"
    reference_lines = []
    for key in SLOW_KEYS:  # the two 606f8713 VBJ lines, reduced to what the summary reads
        job = {**harness_runs["lines"][("D0-1", key)]["job"], "setting": "VBJ"}
        reference_lines.append(json.dumps({"job": job, "commands_sha256": J9_MAIN_VBJ_HASH[key]}))
    reference.write_text("\n".join(reference_lines) + "\n", encoding="utf-8")
    keys = ",".join(SLOW_KEYS)
    process = _run(SUMMARY, "--rows", str(out), "--out", str(tmp_path / "s.json"),
                   "--reference", str(reference), "--keys", keys, cwd=tmp_path)
    assert process.returncode == 0, process.stdout + process.stderr
    report = json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))
    assert report["status"] == "written" and len(report["rows"]) == 14
    checks = report["checks"]
    assert checks["line_problems"] == {} and checks["missing_jobs"] == []
    assert checks["unplanned_jobs"] == [] and checks["error_lines"] == []
    assert checks["d0_1_reference"] == {key: True for key in SLOW_KEYS}
    for row in report["rows"]:
        assert {row[item] for item in ("J1", "J2", "J3", "J4", "J5")} <= {
            "pass", "fail", "flag", "record", "undetermined", "n/a"}
        assert row["held_fraction"] is not None and row["final_phase"] is not None
        assert ("held_filling" in row) == (row["variant"] != "D0-2")
    assert (tmp_path / "s.csv").is_file()
    wrong = tmp_path / "wrong.jsonl"
    wrong.write_text(reference.read_text(encoding="utf-8").replace(
        J9_MAIN_VBJ_HASH["S5_e0.0"], "0" * 64), encoding="utf-8")
    defect = _run(SUMMARY, "--rows", str(out), "--out", str(tmp_path / "w.json"),
                  "--reference", str(wrong), "--keys", keys, cwd=tmp_path)
    assert defect.returncode == 2 and _last_json(defect)["status"] == "setting_defect"
