"""Edition 6 on the reduced harness (dynamics-dev subprocesses; ``jp3_remedy_spec_v6.md`` 5).

P6-0: every setting with the components off keeps the 606f8713 command hashes (V0 golden, V0
of ``main.jsonl``, VBJ / VBJ0 / VB / VBH / LSJ4 of j9_main and T8, LS1 / LSH1 of the j9_cases
event row, two 12b VBK0 b1 keys through ``las_t3_dg3``), with no edition 6 key in its line
or T4h. On: VBL lines carry the ``_LSB`` tag, ``lsb_components``, ``lsb_record`` and the
``lsb_*`` arrays on every T4h read; P6-1 preview (VBL R12 against VBL0 R12); P6-6 (B3 alone
on lines without R-5 keeps the VBJ commands). The probe runner
(320 jobs, refusals) and the share tool end to end from another working folder.

The stored hashes were read on 2026-11-23 from the main checkout's 606f8713 run folders
(``j9_runs/606f8713``: ``j9main_a1/j9_main.jsonl``, ``t8_a1/j9_t8.jsonl``,
``cases_a1/j9_cases.jsonl``, ``12b_vbk0_base_a1/VBK0_b1.json.partial.jsonl``) and the
stored ``v5/main.jsonl``.
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
MAIN_CHECKOUT = Path(r"C:\workspace\outrigger_control")
HARNESS_PYTHON = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe")
CHECK_RUNNER = Path(__file__).resolve().with_name("ed6_check_runner.py")
PROBE = COUPLED_DIR / "ed6_probe.py"
SHARE = COUPLED_DIR / "ed6_probe_share.py"
LAS_T3 = COUPLED_DIR / "las_t3_dg3.py"
V0_MAIN = MAIN_CHECKOUT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "main.jsonl"
V0_MAIN_SHA256 = "9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e"
X11_INPUTS = MAIN_CHECKOUT / "06_analysis" / "02_control" / "j_p3_cause" / "prelaunch_j9" \
    / "ed5_inputs" / "x11"
TIMEOUT_S = 2400

R12 = {"case": "R12", "eps": 0.0, "offset_s": 0.0}
S5 = {"case": "S5", "eps": 0.0}
R15 = {"case": "R15", "eps": 0.0, "offset_s": 0.05}
CASE_ROW = {"case": "R12", "eps": 0.0, "offset_s": 0.0,
            "twin": {"level": "bottom", "leg": "FL", "fs_kN": 4.0}}
OFF_HASHES = {
    "V0_R12": ({**R12, "setting": "V0"},
               "aa147ff6d2839b90dc27de7baff5bc2b24c330b1a3d5be169ff5b739a801b20b"),
    "V0_S5": ({**S5, "setting": "V0"},
              "6dba5b4113b3636aa29893af318c9969b53608039816bc04fd24f9ca6f9358b0"),
    "VBJ_R12": ({**R12, "setting": "VBJ"},
                "018a5b60b41fe671f5d8d8fa7bda072bb2f087090ea7ba5573ae9041d943f10d"),
    "VBJ_S5": ({**S5, "setting": "VBJ"},
               "4d1ebcb74794b475903d12373a6dd60aee453bc896e5774474f7c6d8ccc8b7e7"),
    "VBJ0_S5": ({**S5, "setting": "VBJ0"},
                "4d1ebcb74794b475903d12373a6dd60aee453bc896e5774474f7c6d8ccc8b7e7"),
    "VB_S5": ({**S5, "setting": "VB"},
              "63fe4c965a162fb7c78d57a748ef473d292671f158213ab8605a044d827d0ccc"),
    "VB_R15": ({**R15, "setting": "VB"},
               "55bca14142a32c9b35654b12058c40758368a354c82b28dc5c27e0bdef90700d"),
    "VBH_S5": ({**S5, "setting": "VBH"},
               "63fe4c965a162fb7c78d57a748ef473d292671f158213ab8605a044d827d0ccc"),
    "LSJ4_R12": ({**R12, "setting": "LSJ4"},
                 "bdd82f905f080f52adfdfdb453f9cd8cb0ff8fa60a35099e77139abaab155e77"),
    "LS1_case": ({**CASE_ROW, "setting": "LS1"},
                 "bd50065cc09de3413589ea80eedebfd4ea6e28786012002c99d8209ba7bdf89b"),
    "LSH1_case": ({**CASE_ROW, "setting": "LSH1"},
                  "bd50065cc09de3413589ea80eedebfd4ea6e28786012002c99d8209ba7bdf89b"),
}
"""P6-0 (spec 5): (job, the 606f8713 / stored ``commands_sha256``)."""
VBK0_KEYS = {"L2|s40|g6|0|g6|G1+J1@FL|top|Fs0":
             "d2fa5c8a3c00c964c6f66118d5c25b6df835cd5de91671aa9d0acf430f1bd6a6",
             "L2|s40|g6|1|g6|G1+J1@FL|top|Fs4":
             "c9b73f0a1a352fc5390fd3bcf055b6beb4fec671d9f779f91977f4334723a290"}
"""12b VBK0 b1 sample: key -> 606f8713 command hash (``VBK0_b1.json.partial.jsonl``)."""
ON_JOBS = {"VBL_R12": {**R12, "setting": "VBL"}, "VBL0_R12": {**R12, "setting": "VBL0"},
           "VBL_S5": {**S5, "setting": "VBL"}}
B3_ONLY_SETTING = "VBJ_B3_TEST"
"""P6-6 (spec revision 1 5): the VBJ plant and ③ revision 6 with B3 alone (test only)."""
B3_ONLY_JOBS = {"B3_S5": ({**S5, "setting": B3_ONLY_SETTING}, OFF_HASHES["VBJ_S5"][1]),
                "B3_R15": ({**R15, "setting": B3_ONLY_SETTING},
                           "fe88988aa5e72d17cdabb41200182e50e1124c4adfc25ad7084565a0a59c39e2")}
"""Lines without an R-5 ``relevel_predicted`` (``b3_r5_census``: R-5 only on R12 and R14):
B3 on must give the VBJ command hash (S5 e0.0 and R15 o0.05 of the 606f8713 j9_main)."""
PROBE_KEYS = "R12_o0.0,S5_e0.0"
LSB_TAG = "final_C4G2_P3W_LAS_K1_LSB"


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


def _b3_only_settings() -> dict:
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        import run_v5
    finally:
        sys.path.remove(str(COUPLED_DIR))
    flow, plant = run_v5.JP3_SETTINGS["VBJ"]
    return {B3_ONLY_SETTING: [flow, {**plant, "lsb_components": ["B3"]}]}


def _check_job(job: dict, folder: Path, extra: dict | None = None) -> subprocess.Popen:
    folder.mkdir(parents=True)
    arguments = [str(HARNESS_PYTHON), "-I", "-B", str(CHECK_RUNNER), json.dumps(job),
                 str(folder / "t4h"), str(folder / "report.json")]
    if extra is not None:
        arguments.append(json.dumps(extra))
    return subprocess.Popen(arguments, cwd=folder, env=_environment())


def _vbk0_plan(path: Path) -> None:
    """The b1 rod fault plan cut to the sample keys (the runner refuses plan keys that are no
    job of the run)."""
    plan = json.loads((X11_INPUTS / "b1_plan.json").read_text(encoding="utf-8"))
    plan["faults"] = {key: fault for key, fault in plan["faults"].items()
                      if key.split("#", 1)[-1] in VBK0_KEYS}
    assert len(plan["faults"]) == len(VBK0_KEYS)
    path.write_text(json.dumps(plan), encoding="utf-8")


def _vbk0_run(folder: Path) -> subprocess.Popen:
    folder.mkdir(parents=True)
    keys = folder / "keys.txt"
    keys.write_text("\n".join(VBK0_KEYS) + "\n", encoding="utf-8")
    _vbk0_plan(folder / "b1_plan_sample.json")
    environment = {**_environment(), "R72_PATH": "per_leg", "LAS_T3_DG3_LAS": "on",
                   "LAS_T3_DG3_K1": "on", "LAS_T3_DG3_P3": "on", "R79_V5_SETTING": "VBK0",
                   "R79_ROD_MODEL": "plant_truth",
                   "R79_ROD_FAULT_PLAN": str(folder / "b1_plan_sample.json"),
                   "R79_T4H_DIR": str(folder / "t4h")}
    return subprocess.Popen([str(HARNESS_PYTHON), "-I", "-B", str(LAS_T3), str(PROJECT_ROOT),
                             "run", str(folder / "vbk0.json"), "--levels", "L2", "--keys-file",
                             str(keys), "--workers", str(len(VBK0_KEYS))],
                            cwd=folder, env=environment,
                            stdout=(folder / "run.log").open("w", encoding="utf-8"),
                            stderr=subprocess.STDOUT)


@pytest.fixture(scope="module")
def harness(tmp_path_factory) -> dict:
    """Every harness run at once, each from its own working folder."""
    _needs_harness()
    if not V0_MAIN.is_file() or not (X11_INPUTS / "b1_plan.json").is_file():
        pytest.skip("the main checkout's stored inputs are missing")
    root = tmp_path_factory.mktemp("ed6")
    processes = {name: _check_job(job, root / name)
                 for name, (job, _) in OFF_HASHES.items()}
    processes.update({name: _check_job(job, root / name) for name, job in ON_JOBS.items()})
    b3_only = _b3_only_settings()
    processes.update({name: _check_job(job, root / name, b3_only)
                      for name, (job, _) in B3_ONLY_JOBS.items()})
    vbk0 = _vbk0_run(root / "vbk0")
    probe_out = root / "probe" / "ed6_probe.jsonl"
    (root / "probe_work").mkdir()
    probe = subprocess.Popen([str(HARNESS_PYTHON), "-I", "-B", str(PROBE), "--out",
                              str(probe_out), "--plants", "J", "--arms", "a1a2b,a1a2bh",
                              "--keys", PROBE_KEYS, "--workers", "4"],
                             cwd=root / "probe_work", env=_environment(),
                             stdout=subprocess.PIPE, text=True, encoding="utf-8")
    probe_stdout, _ = probe.communicate(timeout=TIMEOUT_S)
    vbk0.wait(timeout=TIMEOUT_S)
    for process in processes.values():
        process.wait(timeout=TIMEOUT_S)
    failed = [name for name, process in processes.items() if process.returncode != 0]
    assert not failed, failed
    reports = {name: json.loads((root / name / "report.json").read_text(encoding="utf-8"))
               for name in processes}
    vbk0_lines = [json.loads(text) for text in
                  (root / "vbk0" / "vbk0.json.partial.jsonl").read_text(
                      encoding="utf-8").splitlines() if text.strip()]
    return {"root": root, "reports": reports, "vbk0_exit": vbk0.returncode,
            "vbk0_lines": vbk0_lines, "probe_out": probe_out, "probe_exit": probe.returncode,
            "probe_last": json.loads(probe_stdout.strip().splitlines()[-1])}


@pytest.mark.slow
def test_p6_0_off_settings_keep_the_stored_command_hashes(harness) -> None:
    reports = harness["reports"]
    for name, (_, stored) in OFF_HASHES.items():
        report = reports[name]
        assert report["hash"] == stored, name
        assert not report["has_lsb_components"] and report["lsb_record"] is None, name
        assert "lsb" not in (report["controller_tag"] or ""), name
        assert "lsb_components" not in (report["hydraulic_options"] or {}), name
        arrays = report["t4h"]["arrays"] or []
        assert not any(array.startswith("lsb_") for array in arrays), name
        assert report["foreign_modules"] == [], name


@pytest.mark.slow
def test_p6_0_12b_vbk0_sample_keeps_its_hashes(harness) -> None:
    assert harness["vbk0_exit"] == 0
    found = {line["key"].split("#", 1)[-1]: line["commands_sha256"]
             for line in harness["vbk0_lines"]}
    assert found == VBK0_KEYS
    assert all(line["controller_tag"] == "final_C4G2_LAS_K1" for line in harness["vbk0_lines"])


@pytest.mark.slow
def test_vbl_lines_carry_the_edition_6_identity_and_records(harness) -> None:
    reports = harness["reports"]
    for name in ("VBL_R12", "VBL_S5"):
        report = reports[name]
        assert report["controller_tag"] == LSB_TAG, name
        assert report["lsb_components"] == ["A_i", "A_ii", "B1", "B3"], name
        assert report["hydraulic_options"]["lsb_components"] == ["A_i", "A_ii", "B1", "B3"], name
        assert report["lsb_record"]["components"] == ["A_i", "A_ii", "B1", "B3"], name
        t4h = report["t4h"]
        assert t4h["lsb_read_found"] == t4h["reads"] > 0, name
        assert t4h["meta_controller_tag"] == LSB_TAG, name
        assert t4h["meta_lsb_components"] == ["A_i", "A_ii", "B1", "B3"], name
        assert report["foreign_modules"] == [], name
    assert reports["VBL_R12"]["hash"] != OFF_HASHES["VBJ_R12"][1]  # the components act
    assert reports["VBL0_R12"]["controller_tag"] == "final_C4G2_LAS_K1_LSB"


@pytest.mark.slow
def test_p6_6_b3_without_r5_keeps_the_commands(harness) -> None:
    for name, (_, stored) in B3_ONLY_JOBS.items():
        report = harness["reports"][name]
        assert report["hash"] == stored, name
        assert report["lsb_components"] == ["B3"], name
        assert report["lsb_record"]["b3_episodes"] == [], name
        assert "relevel_predicted" not in " ".join(report["event_names"] or []), name


@pytest.mark.slow
def test_p6_1_preview_vbl_and_vbl0_command_the_same_on_r12(harness) -> None:
    """Spec 5 P6-1 (T8, the VBJ / VBJ0 R12 pair has no ③ substitution): A and B do not read
    the ③ state, so VBL and VBL0 give the same commands."""
    reports = harness["reports"]
    assert reports["VBL_R12"]["hash"] == reports["VBL0_R12"]["hash"]


@pytest.mark.slow
def test_probe_runner_lines_and_the_share_tool_end_to_end(harness, tmp_path: Path) -> None:
    assert harness["probe_exit"] == 0 and harness["probe_last"]["status"] == "ok"
    assert harness["probe_last"]["run"] == 4
    lines = [json.loads(text) for text in
             harness["probe_out"].read_text(encoding="utf-8").splitlines()]
    hold = [line for line in lines if line["job"]["setting"] == "P6-J-a1a2bh"]
    assert all(line["hydraulic_options"]["lsb_parameters"] == {"a2_hold_after_fill_s": 1.0}
               for line in hold) and len(hold) == 2
    process = _run(SHARE, "--rows", str(harness["probe_out"]), "--v0", str(V0_MAIN),
                   "--v0-sha256", V0_MAIN_SHA256, "--out", str(tmp_path / "share.json"),
                   "--plants", "J", "--arms", "a1a2b,a1a2bh", "--keys", PROBE_KEYS,
                   cwd=tmp_path)
    assert process.returncode == 2, process.stdout + process.stderr
    report = json.loads((tmp_path / "share.json").read_text(encoding="utf-8"))
    assert report["status"] == "not_judgeable"  # the compared arms were not run
    assert report["checks"]["line_problems"] == {} and report["checks"]["missing_jobs"] == []
    assert len(report["rows"]) == 4
    assert {"stall_signature", "lsb_a2_raised_periods", "min_force_kN", "J1"} <= set(
        report["rows"][0])
    assert set(report["groups"]) == {"J a1a2b", "J a1a2bh"}
    assert (tmp_path / "share.csv").is_file()


# ------------------------------------------------------------------ CLI (cheap, no run)
def test_probe_lists_320_jobs_and_refuses_bad_input(tmp_path: Path) -> None:
    listed = _run(PROBE, "--out", str(tmp_path / "p.jsonl"), "--list", cwd=tmp_path)
    assert listed.returncode == 0 and _last_json(listed)["planned"] == 320
    for bad in (("--plants", "X"), ("--arms", "a9"), ("--lsb-param", "nope=1"),
                ("--lsb-param", "a1_cap_m_s=-1")):
        process = _run(PROBE, "--out", str(tmp_path / "p.jsonl"), *bad, cwd=tmp_path)
        assert process.returncode == 2 and _last_json(process)["status"] == "input_error", bad
    assert not (tmp_path / "p.jsonl").exists()


def test_share_tool_input_errors(tmp_path: Path) -> None:
    missing = _run(SHARE, "--rows", str(tmp_path / "none.jsonl"), "--v0", str(V0_MAIN),
                   "--v0-sha256", V0_MAIN_SHA256, "--out", str(tmp_path / "a.json"),
                   cwd=tmp_path)
    assert missing.returncode == 2 and _last_json(missing)["status"] == "input_error"
    (tmp_path / "b.json").write_text("{}", encoding="utf-8")
    existing = _run(SHARE, "--rows", str(tmp_path / "none.jsonl"), "--v0", str(V0_MAIN),
                    "--v0-sha256", V0_MAIN_SHA256, "--out", str(tmp_path / "b.json"),
                    cwd=tmp_path)
    assert existing.returncode == 2 and _last_json(existing)["status"] == "input_error"


def test_importing_the_probe_switches_nothing() -> None:
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        import ed6_probe as probe
        import harness_hydraulics
    finally:
        sys.path.remove(str(COUPLED_DIR))
    assert not any(name.startswith("P6-") for name in probe.run_v5.ALL_SETTINGS)
    assert not any(name.startswith("P6-") for name in probe.run_v5.T4H_SETTINGS)
    assert harness_hydraulics.is_p1_read_record_on() is False
    assert len(probe.probe_jobs()) == 320 and len(probe.ARMS) == 8
    settings = probe.probe_settings()
    assert settings["P6-c04-a1a2bh"][1]["lsb_parameters"] == {"a2_hold_after_fill_s": 1.0}
    assert "lsb_parameters" not in settings["P6-c04-a1a2b"][1]
    assert settings["P6-c04-a2"][1]["line_fill_gate"]["c_v"] == 0.04
