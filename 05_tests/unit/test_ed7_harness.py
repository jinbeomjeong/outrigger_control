"""Edition 7 on the reduced harness (dynamics-dev subprocesses; ``jp3_remedy_spec_v7.md`` 5).

P7-0: the edition 6 settings with the edition 7 parts off keep the command hashes of the
edition 6 run 79495405 (``j9_runs/79495405/records_after_stop/B_a1/j9_main.jsonl`` and
``sens.jsonl``, ``impl_t8_a1/ed6_t8.jsonl``, read on 2026-11-24), carry no edition 7 key and
gain only the record key ``stale_seed_release`` (old P1 plant). The settings without P1 (V0,
VB, ...) are the edition 6 test's P6-0 (``test_ed6_harness.py``). On: VBM lines carry the
``_P3X`` tag, the four components, ``probe_d6_settings`` / ``probe_d6_record``, the
``p1_patch`` options and the A(i)-b arrays; P7-1 preview (VBM and VBM0 on R12). The probe runner
(654 jobs, refusals, a two-job run) and the ③ rev 7 condition tool end to end from another
working folder.
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
CHECK_RUNNER = Path(__file__).resolve().with_name("ed7_check_runner.py")
PROBE = COUPLED_DIR / "ed7_probe.py"
CONDITION = COUPLED_DIR / "jp3_rev7_condition.py"
TIMEOUT_S = 2400

R12 = {"case": "R12", "eps": 0.0, "offset_s": 0.0}
S5 = {"case": "S5", "eps": 0.0}
ED6_HASHES = {
    "VBL_R12": ({**R12, "setting": "VBL"},
                "b14c53e3e9f17298def8898cb676c0154d7704105df4d8f3669b053563b8239b"),
    "VBL_S5": ({**S5, "setting": "VBL"},
               "fb1e0cfda44ea87c7ffdbd36340dfd8737119e586b52f3093de5b78d7b706cca"),
    "LSL1_R12": ({**R12, "setting": "LSL1"},
                 "3ed6efcff9221b619e5953f61a8ba6165806b492ee88e43b6441fa7723f49f63"),
    "LSL4_S5": ({**S5, "setting": "LSL4"},
                "13ddb64d82bfd86e16361868dfadcb3f1aa5c0b575701a9d6824da68956aa47d"),
    "VBLc04_S5": ({**S5, "setting": "VBLc04"},
                  "e0c2095d610239f653cd373f1be2711b9b5687befb279a3142c902cda66e8e48"),
    "VBLv15_R12": ({**R12, "setting": "VBLv15"},
                   "6424b9889af49283c21d56b13d4a7fe11dcc151069905e93936e9a5c5fad3b57"),
    "VBL0_S5": ({**S5, "setting": "VBL0"},
                "fb1e0cfda44ea87c7ffdbd36340dfd8737119e586b52f3093de5b78d7b706cca"),
}
"""P7-0 (spec 5): (job, the 79495405 ``commands_sha256``)."""
ON_JOBS = {"VBM_R12": {**R12, "setting": "VBM"}, "VBM0_R12": {**R12, "setting": "VBM0"},
           "VBMslow_S5": {**S5, "setting": "VBMslow"}}
ED7_TAG = "final_C4G2_P3X_LAS_K1_LSB"
ED7_COMPONENTS = ["A_i", "A_ib", "A_ii", "B3"]
ED7_LINE_KEYS = {"probe_d6_settings", "probe_d6_record"}
PROBE_RUN = ("--plants", "M", "--arms", "a2,c2", "--keys", "R12_o0.0", "--part", "main")


def _environment() -> dict:
    return {**os.environ, "MKL_THREADING_LAYER": "TBB", "PYTHONDONTWRITEBYTECODE": "1"}


def _needs_harness() -> None:
    if not HARNESS_PYTHON.exists():
        pytest.skip("dynamics-dev missing")


def _run(script: Path, *arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    _needs_harness()
    return subprocess.run([str(HARNESS_PYTHON), "-I", "-B", str(script), *arguments],
                          cwd=cwd, env=_environment(), capture_output=True, text=True,
                          encoding="utf-8", timeout=TIMEOUT_S)


def _last_json(process: subprocess.CompletedProcess) -> dict:
    return json.loads(process.stdout.strip().splitlines()[-1])


def _check_job(job: dict, folder: Path) -> subprocess.Popen:
    folder.mkdir(parents=True)
    return subprocess.Popen([str(HARNESS_PYTHON), "-I", "-B", str(CHECK_RUNNER), json.dumps(job),
                             str(folder / "t4h"), str(folder / "report.json")],
                            cwd=folder, env=_environment())


@pytest.fixture(scope="module")
def harness(tmp_path_factory) -> dict:
    """Every harness run at once, each from its own working folder."""
    _needs_harness()
    root = tmp_path_factory.mktemp("ed7")
    jobs = {**{name: job for name, (job, _) in ED6_HASHES.items()}, **ON_JOBS}
    processes = {name: _check_job(job, root / name) for name, job in jobs.items()}
    probe_out = root / "probe" / "ed7_probe.jsonl"
    (root / "probe_work").mkdir()
    probe = subprocess.Popen([str(HARNESS_PYTHON), "-I", "-B", str(PROBE), "--out",
                              str(probe_out), *PROBE_RUN, "--workers", "2"],
                             cwd=root / "probe_work", env=_environment(),
                             stdout=subprocess.PIPE, text=True, encoding="utf-8")
    probe_stdout, _ = probe.communicate(timeout=TIMEOUT_S)
    for process in processes.values():
        process.wait(timeout=TIMEOUT_S)
    failed = [name for name, process in processes.items() if process.returncode != 0]
    assert not failed, failed
    reports = {name: json.loads((root / name / "report.json").read_text(encoding="utf-8"))
               for name in processes}
    return {"root": root, "reports": reports, "probe_out": probe_out,
            "probe_exit": probe.returncode,
            "probe_last": json.loads(probe_stdout.strip().splitlines()[-1])}


@pytest.mark.slow
def test_p7_0_edition_6_settings_keep_the_run_hashes(harness) -> None:
    for name, (_, stored) in ED6_HASHES.items():
        report = harness["reports"][name]
        assert report["hash"] == stored, name
        assert not ED7_LINE_KEYS & set(report["line_keys"]), name
        assert "_P3X" not in (report["controller_tag"] or ""), name
        assert not {"p1_patch", "probe_d6_settings", "extend_start_rev7"} & set(
            report["hydraulic_options"]), name
        assert "A_ib" not in (report["lsb_components"] or []), name
        assert "blind" not in (report["lsb_record"] or {}), name
        assert not any(array.startswith("lsb_ib_") for array in report["t4h"]["arrays"]), name
        assert "probe_d6_settings" not in report["t4h"]["meta_keys"], name
        stale = report["stale_seed_release"]  # the record key of the old P1 plant
        assert stale is not None and set(stale) == {"releases_with_seed", "stale_releases",
                                                   "log_rows", "log_truncated", "log",
                                                   "log_columns"}, name
        assert stale["releases_with_seed"] == stale["log_rows"], name  # nothing truncated
        assert "stale_seed_release" in report["t4h"]["meta_keys"], name
        assert report["foreign_modules"] == [], name


@pytest.mark.slow
def test_vbm_lines_carry_the_edition_7_identity_and_records(harness) -> None:
    for name in ON_JOBS:
        report = harness["reports"][name]
        assert report["lsb_components"] == ED7_COMPONENTS, name
        assert "blind" in report["lsb_record"], name
        assert report["probe_d6_settings"]["witness"] is True, name
        assert report["probe_d6_settings"]["retract_position_target"] is True, name
        assert report["hydraulic_options"]["p1_patch"]["k_ext_form"] == "b0", name
        assert report["stale_seed_release"] is None, name  # (d): no seed path
        assert "p1_fill_release_log" in report["hydraulics_record_keys"], name
        assert {"lsb_ib_floor_m_s", "lsb_ib_on", "lsb_ib_twist_load_N"} <= set(
            report["t4h"]["arrays"]), name
        assert {"probe_d6_settings", "probe_d6_record"} <= set(report["t4h"]["meta_keys"])
        assert report["foreign_modules"] == [], name
        blind = report["lsb_record"]["blind"]  # records of the user decision 2026-11-24
        assert {entry["path"] for entry in blind["level_done"]} <= {"strict", "relax"}, name
        over = blind["twist_over_limit"]
        assert over["entries"] == len(over["episodes"]) and over["limit_N"] == 15.0e3, name
    reports = harness["reports"]
    assert len(reports["VBM_R12"]["lsb_record"]["blind"]["level_done"]) >= 1  # R12 ends DONE
    assert reports["VBM_R12"]["controller_tag"] == ED7_TAG
    assert reports["VBMslow_S5"]["controller_tag"] == ED7_TAG
    assert reports["VBM0_R12"]["controller_tag"] == "final_C4G2_LAS_K1_LSB"
    assert reports["VBMslow_S5"]["hydraulic_options"]["p1_patch"]["line_scale"] == 1.5
    assert reports["VBM_R12"]["hash"] != ED6_HASHES["VBL_R12"][1]  # the supplement acts


@pytest.mark.slow
def test_p7_1_preview_vbm_and_vbm0_command_the_same_on_r12(harness) -> None:
    """Spec 5 P7-1 (T8): without a ③ substitution VBM and VBM0 give the same commands."""
    reports = harness["reports"]
    assert reports["VBM_R12"]["hash"] == reports["VBM0_R12"]["hash"]


@pytest.mark.slow
def test_probe_runner_and_the_condition_tool_end_to_end(harness, tmp_path: Path) -> None:
    assert harness["probe_exit"] == 0 and harness["probe_last"]["status"] == "ok"
    assert harness["probe_last"]["run"] == 2
    lines = [json.loads(text) for text in
             harness["probe_out"].read_text(encoding="utf-8").splitlines()]
    by_setting = {line["job"]["setting"]: line for line in lines}
    assert set(by_setting) == {"P7-M-a2", "P7-M-c2"}
    assert "probe_d6_settings" in by_setting["P7-M-a2"]
    assert "probe_d6_settings" not in by_setting["P7-M-c2"]
    assert by_setting["P7-M-a2"]["ed7_probe"]["part"] == "main"
    process = _run(CONDITION, "--rows", str(harness["probe_out"]), "--out",
                   str(tmp_path / "condition.json"), cwd=tmp_path)
    assert process.returncode in (0, 1), process.stdout + process.stderr
    report = json.loads((tmp_path / "condition.json").read_text(encoding="utf-8"))
    assert report["summary"]["judged_lines"] == 2
    assert all(entry["state"] in ("judged", "fail") for entry in report["lines"])


# ------------------------------------------------------------------ CLI (cheap, no run)
def test_probe_lists_654_jobs_and_refuses_bad_input(tmp_path: Path) -> None:
    listed = _run(PROBE, "--out", str(tmp_path / "p.jsonl"), "--list", cwd=tmp_path)
    assert listed.returncode == 0 and _last_json(listed)["planned"] == 654
    for bad in (("--plants", "X"), ("--arms", "a9"), ("--part", "z"), ("--keys", "R99_o0")):
        process = _run(PROBE, "--out", str(tmp_path / "p.jsonl"), *bad, cwd=tmp_path)
        assert process.returncode == 2 and _last_json(process)["status"] == "input_error", bad
    assert not (tmp_path / "p.jsonl").exists()


def test_condition_tool_input_errors(tmp_path: Path) -> None:
    missing = _run(CONDITION, "--rows", str(tmp_path / "none.jsonl"), "--out",
                   str(tmp_path / "a.json"), cwd=tmp_path)
    assert missing.returncode == 2 and _last_json(missing)["status"] == "input_error"
    (tmp_path / "b.json").write_text("{}", encoding="utf-8")
    existing = _run(CONDITION, "--rows", str(tmp_path / "none.jsonl"), "--out",
                    str(tmp_path / "b.json"), cwd=tmp_path)
    assert existing.returncode == 2 and _last_json(existing)["status"] == "input_error"


def test_importing_the_probe_switches_nothing() -> None:
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        import ed7_probe as probe
        import harness_hydraulics
    finally:
        sys.path.remove(str(COUPLED_DIR))
    assert not any(name.startswith("P7-") for name in probe.run_v5.ALL_SETTINGS)
    assert not any(name.startswith("P7-") for name in probe.run_v5.T4H_SETTINGS)
    assert harness_hydraulics.is_p1_read_record_on() is False
