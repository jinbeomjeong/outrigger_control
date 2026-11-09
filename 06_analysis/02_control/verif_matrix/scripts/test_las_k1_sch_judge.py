"""Unit tests of ``las_k1_sch_judge.py`` on synthetic batch folders (no Chrono, no git).

Run (dynamics-dev, PowerShell):
  $env:PYTHONDONTWRITEBYTECODE = '1'
  C:\\ProgramData\\miniforge3\\envs\\dynamics-dev\\python.exe -I -m pytest -q -p no:cacheprovider
      06_analysis/02_control/verif_matrix/scripts/test_las_k1_sch_judge.py
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

JUDGE_PATH = Path(__file__).resolve().with_name("las_k1_sch_judge.py")
_SPEC = importlib.util.spec_from_file_location("las_k1_sch_judge", JUDGE_PATH)
judge = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = judge  # dataclasses look the module up while the class is built
_SPEC.loader.exec_module(judge)

HEAD = "a" * 40
T_LOC_S = 35.4
N_LOC = 354
FIRST_COMMAND_PERIOD = 81
N_COMMANDS = 2000
STEP_DT_S = 0.01
T_END_S = 208.0


# ---------------------------------------------------------------- synthetic rows
def decision(applied: bool) -> dict[str, Any]:
    return {
        "t_loc_s": T_LOC_S,
        "t_P_s": 34.8,
        "t_S_s": 35.0,
        "n_P": 348,
        "n_S": 350,
        "dP": -2,
        "r4_due_without_gate": True,
        "would_block": True,
        "applied": applied,
    }


def passing_checks() -> dict[str, Any]:
    return {key: True for key in judge.C2_CHECK_KEYS}


def result_json(case: str, gate: str) -> dict[str, Any]:
    is_on = gate == "on"
    margin_event = (
        "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order" if is_on else "INFO_LOC_FLAT_SOIL_MARGIN:80"
    )
    target_m = 0.05 if is_on else 0.05 + 0.03
    args = {
        **judge.EXPECTED_ARGS,
        "threads": 4,
        "k1_order_gate": gate,
        "case": case,
        "out_root": "batch",
    }
    return {
        "args": args,
        "num_threads_chrono": 4,
        "placement": {"mode": "pcore", "affinity_ok": True, "power_throttling_off_ok": True},
        "hull_hook": {
            "mode": "fast",
            "requested": "fast",
            "fallback_reason": None,
            "dll_sha256": judge.DLL_SHA256,
            "dll_sha_validated": True,
        },
        "v5_hydraulics": {"controller_tag": judge.CONTROLLER_TAG},
        "c2_setup": {"expect_controller": {"ok": True}, "k1_order_gate": gate},
        "code_state": {
            "files_at_start": {
                module: {"sha256": judge.CRLF_SHA256_BY_PATH[path]}
                for module, path in judge.RECORDED_CONTROLLER_FILES
            },
            "git_at_start": {"head": HEAD, "dirty": []},
        },
        "controller_meta": {
            "slope_clearance_margin": {
                "clearance_target_m": target_m,
                "is_applied": False,
                "flat_soil_margin_applied": not is_on,
                "order_gate": {"enabled": is_on, "decisions": [decision(applied=not is_on)]},
            }
        },
        "events": [
            {"t_s": 35.0, "name": "soil_mode_start"},
            {"t_s": T_LOC_S, "name": "crawler_liftoff_confirmed"},
            {"t_s": T_LOC_S, "name": margin_event},
        ],
        "phases": [{"t_s": 8.1, "phase": "check"}, {"t_s": 60.0, "phase": "ready"}],
        "p3b": {
            "checks": passing_checks(),
            "departure": {"departed": True, "t_departure_s": 33.0, "t_confirmed_s": 33.5},
            "P3-1_crawler": {"recontact_events": {"events": []}},
            "P3-3_leg_force": {"F_min_after_N": [20000.0] * 4, "t_min_after_s": [50.0] * 4},
            "P3-5_clearance_stroke": {"s_motor_max_m": [0.47 if is_on else 0.50, 0.3, 0.3, 0.3]},
        },
        "p3b_ext": {
            "crawler_gap": {
                "grid_end_m": 0.05 if is_on else 0.08,
                "end_m": 0.045 if is_on else 0.075,
                "after_first_ready": {"grid_min_m": 0.05, "all_min_m": 0.045},
            }
        },
        "s9_rows": [{"crawler_gap_point_near_sinkage_m": 0.004}],
    }


def batch_entry(case: str, gate: str) -> dict[str, Any]:
    other = judge.CASE_GATEON if gate == "off" else judge.CASE_GATEOFF
    return {
        "case": case,
        "argv": ["python", "run_S9.py", "level", "--soil", "G1", "--k1-order-gate", gate],
        "rc": 0,
        "pool": "pcore",
        "omp_wait_policy": "PASSIVE",
        "hull_hook_requested": "fast",
        "hull_hook_effective": {"mode": "fast", "fallback_reason": None},
        "code_at_launch": {
            "files": {
                path: judge.CRLF_SHA256_BY_PATH[path] for _, path in judge.RECORDED_CONTROLLER_FILES
            },
            "git": {"head": HEAD, "dirty": []},
        },
        "pair_case": other,
        "las_candidate": "P0",
        "k1_candidate": "K1on" if gate == "on" else "K1off",
        "k1_order_gate": gate,
    }


def commands(gate: str) -> dict[str, np.ndarray]:
    periods = np.arange(FIRST_COMMAND_PERIOD, FIRST_COMMAND_PERIOD + N_COMMANDS)
    issued = np.zeros((N_COMMANDS, 4))
    if gate == "on":
        issued[periods >= N_LOC] += 1e-3
    return {"t_s": periods * 0.1, "issued_u_m_s": issued}


def step_series() -> dict[str, np.ndarray]:
    t_s = np.arange(8.0, T_END_S + STEP_DT_S / 2, STEP_DT_S)
    return {"t_s": t_s, "scm_crawler_normal_N": np.zeros_like(t_s)}


class SyntheticBatch:
    """Editable pair written as a batch folder by :meth:`write`."""

    def __init__(self) -> None:
        self.results = {case: result_json(case, gate) for case, gate in judge.GATE_OF_CASE.items()}
        self.entries = {case: batch_entry(case, gate) for case, gate in judge.GATE_OF_CASE.items()}
        self.commands = {case: commands(gate) for case, gate in judge.GATE_OF_CASE.items()}
        self.steps = {case: step_series() for case in judge.GATE_OF_CASE}

    @property
    def off(self) -> dict[str, Any]:
        return self.results[judge.CASE_GATEOFF]

    @property
    def on(self) -> dict[str, Any]:
        return self.results[judge.CASE_GATEON]

    def write(self, folder: Path) -> Path:
        folder.mkdir(parents=True)
        batch = {"cases": list(self.entries.values()), "failed": False, "mixed_hull_mode": False}
        (folder / "batch.json").write_text(json.dumps(batch), encoding="utf-8")
        (folder / "progress.log").write_text(
            "".join(f"START {c} x\nEND {c} x rc=0\n" for c in judge.GATE_OF_CASE), encoding="utf-8"
        )
        for case in judge.GATE_OF_CASE:
            row = folder / case
            row.mkdir()
            (row / "result.json").write_text(json.dumps(self.results[case]), encoding="utf-8")
            np.savez(row / "step_series.npz", **self.steps[case])
            np.savez(row / "controller_commands.npz", **self.commands[case])
        return folder


def identity_record(kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "all_ok": True,
        "taken_utc": "2026-11-09T10:00:00+00:00",
        "head": {"sha": HEAD},
        "code_diff": {"quiet": True, "changed_paths": None},
        "git_status": {"lines": []},
        "tool": {"sha256": judge.sha256_file(judge.TOOL_PATH)},
        "code_files": [{"path": "x", "worktree_sha256": "1", "blob_sha256": "2"}],
        "dll": {"sha256": judge.DLL_SHA256},
    }


@pytest.fixture
def no_git(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(judge, "git_diff_is_empty", lambda root, base, head: True)
    monkeypatch.setattr(judge, "sealed_rules_record", lambda root: {"files": {}, "ok": True})


def run_judge(
    tmp_path: Path, synthetic: SyntheticBatch, postrun_record: dict[str, Any] | None = None
) -> dict[str, Any]:
    batch_dir = synthetic.write(tmp_path / "batch_V5-LAS-K1-CHRONO_test")
    prelaunch, postrun = tmp_path / "pre.json", tmp_path / "post.json"
    prelaunch.write_text(json.dumps(identity_record("prelaunch")), encoding="utf-8")
    record = identity_record("postrun") if postrun_record is None else postrun_record
    postrun.write_text(json.dumps(record), encoding="utf-8")
    return judge.judge_batch(batch_dir, tmp_path, prelaunch, postrun)


def check_by_id(doc: dict[str, Any], section: str, check_id: str) -> dict[str, Any]:
    return next(c for c in doc[section] if c["id"] == check_id)


# ---------------------------------------------------------------- tests
def test_pass(tmp_path: Path, no_git: None) -> None:
    doc = run_judge(tmp_path, SyntheticBatch())
    assert doc["status"] == "pass", (doc["stop_reasons"], doc["fail_reasons"])
    assert doc["k1"]["active"] and doc["k1"]["n_loc"] == N_LOC
    prefix = check_by_id(doc, "structure", "K-S7")
    assert (
        prefix["ok"]
        and prefix["k_diff"] == N_LOC
        and prefix["prefix_rows"]["gateoff"] == N_LOC - 81
    )
    assert doc["pair"]["C-S"]["increase_m"] == pytest.approx(-0.03)
    assert doc["predictions"]["Q-C2"][7]["inside"] is True  # s_max delta -30 mm


def test_gateon_only_failure_is_fail(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.steps[judge.CASE_GATEON]["scm_crawler_normal_N"][-20:] = 500.0
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "fail"
    assert doc["e6"]["grade"]["gateon_only_failed"] == ["E-6a"]


def test_both_rows_failing_the_same_item_is_stop(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    for case in judge.GATE_OF_CASE:
        synthetic.steps[case]["scm_crawler_normal_N"][-20:] = 500.0
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "stop"
    assert "E-6 both: E-6a" in doc["stop_reasons"]


def test_fail_wins_over_stop(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.on["p3b"]["P3-5_clearance_stroke"]["s_motor_max_m"] = [0.502, 0.3, 0.3, 0.3]  # +2 mm
    synthetic.entries[judge.CASE_GATEON]["rc"] = 1  # K-0i false
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "fail"
    assert "C-S" in doc["fail_reasons"] and "K-0i" in doc["stop_reasons"]


def test_k1_inactive(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    for case in judge.GATE_OF_CASE:
        meta = synthetic.results[case]["controller_meta"]["slope_clearance_margin"]
        meta["order_gate"]["decisions"] = []
        meta["clearance_target_m"] = 0.05
        synthetic.results[case]["events"] = [
            e for e in synthetic.results[case]["events"] if not e["name"].startswith("INFO_")
        ]
        synthetic.commands[case] = commands("off")
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "k1_inactive"
    assert doc["k1"]["inactive_reason"] == "decisions empty"
    assert check_by_id(doc, "structure", "K-4")["ok"]


def test_k1_inactive_with_different_commands_is_stop(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    for case in judge.GATE_OF_CASE:
        meta = synthetic.results[case]["controller_meta"]["slope_clearance_margin"]
        meta["order_gate"]["decisions"][0]["would_block"] = False
        meta["order_gate"]["decisions"][0]["applied"] = True
        meta["order_gate"]["decisions"][0]["t_P_s"] = 35.5  # n_P > n_S
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "stop" and "K-4" in doc["stop_reasons"]


def test_prefix_mismatch_is_stop(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    issued = synthetic.commands[judge.CASE_GATEON]["issued_u_m_s"]
    issued[100 - FIRST_COMMAND_PERIOD + 50] += 1e-6  # period 150 < n_LOC
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "stop" and "K-S7" in doc["stop_reasons"]
    prefix = check_by_id(doc, "structure", "K-S7")
    assert prefix["prefix_sha256"]["gateoff"] != prefix["prefix_sha256"]["gateon"]
    assert prefix["k_diff"] == 150


def test_empty_prefix_is_not_a_pass(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    for case in judge.GATE_OF_CASE:
        decisions = synthetic.results[case]["controller_meta"]["slope_clearance_margin"][
            "order_gate"
        ]["decisions"]
        decisions[0]["t_loc_s"] = 8.0  # n_LOC 80 is before the first command period 81
    doc = run_judge(tmp_path, synthetic)
    assert check_by_id(doc, "structure", "K-S7")["ok"] is False


def test_e6b_flag_band(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.on["p3b_ext"]["crawler_gap"]["grid_end_m"] = 0.010
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "pass"
    assert doc["e6"]["gateon"]["E-6b"]["outcome"] == "flag"
    assert "E-6_post_event_clearance" in doc["flags"]["gateon"]


def test_e6b_at_or_below_zero_fails(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.on["p3b_ext"]["crawler_gap"]["grid_end_m"] = 0.0
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "fail" and "E-6 gateon only: E-6b" in doc["fail_reasons"]


def test_no_departure_makes_e6c_false(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.on["p3b"]["departure"] = {"departed": False}
    doc = run_judge(tmp_path, synthetic)
    assert doc["e6"]["gateon"]["E-6c"]["ok"] is False
    assert doc["status"] == "fail"


def test_missing_meta_is_incomplete(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    del synthetic.on["controller_meta"]["slope_clearance_margin"]["order_gate"]
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "incomplete"
    assert any("order_gate: missing" in r for r in doc["incomplete_reasons"])


def test_error_block_is_incomplete(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.off["p3b_ext"]["crawler_gap"] = {"error": "ValueError: x"}
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "incomplete"


def test_extra_row_is_stop(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    extra = copy.deepcopy(synthetic.entries[judge.CASE_GATEON])
    extra["case"] = "SCh_extra"
    synthetic.entries["SCh_extra"] = extra
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "stop"


def test_c2_union_rule_and_new_fault(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    del synthetic.off["p3b"]["checks"]["P3-7_within"]  # baseline None
    synthetic.on["p3b"]["checks"]["P3-7_within"] = False
    synthetic.on["events"].append({"t_s": 90.0, "name": "WARN_LEG_REAPPROACH_NO_CONTACT:FL"})
    doc = run_judge(tmp_path, synthetic)
    items = {v["item"] for v in doc["pair"]["C-2"]["violations"]}
    assert items == {"P3-7_within", "WARN_LEG_REAPPROACH_NO_CONTACT"}
    assert doc["status"] == "fail"


def test_git_at_start_error_falls_back_to_batch(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.on["code_state"]["git_at_start"] = {"error": "TimeoutExpired: git"}
    doc = run_judge(tmp_path, synthetic)
    k0a = check_by_id(doc, "identity", "K-0a")
    assert k0a["ok"] and "batch.json" in k0a["heads"][judge.CASE_GATEON]["source"]


def test_postrun_difference_breaks_k0d(tmp_path: Path, no_git: None) -> None:
    batch_dir = SyntheticBatch().write(tmp_path / "batch")
    prelaunch, postrun = tmp_path / "pre.json", tmp_path / "post.json"
    prelaunch.write_text(json.dumps(identity_record("prelaunch")), encoding="utf-8")
    changed = identity_record("postrun")
    changed["dll"]["sha256"] = "0" * 64
    postrun.write_text(json.dumps(changed), encoding="utf-8")
    doc = judge.judge_batch(batch_dir, tmp_path, prelaunch, postrun)
    assert doc["status"] == "stop" and "K-0d" in doc["stop_reasons"]


GIT_CALLS: list[tuple[str, ...]] = []


def fake_git(root: Path, *args: str) -> Any:
    GIT_CALLS.append(args)
    replies = {
        "rev-parse": (0, f"{HEAD}\n".encode()),
        "diff": (1, b"") if "--quiet" in args else (0, b"04_scripts/02_chrono/run_S2a.py\n"),
        "status": (0, b" M 04_scripts/02_chrono/run_S2a.py\n?? 04_scripts/new.py\n"),
        "show": (0, b""),
    }
    returncode, stdout = replies[args[0]]
    return judge.GitResult(returncode, stdout, None)


def test_prelaunch_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(judge, "run_git", fake_git)
    out = tmp_path / "pre.json"
    code = judge.main(["prelaunch", "--root", str(tmp_path), "--out", str(out)])
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert code == 2 and doc["status"] == "stop"
    assert doc["checks"]["(2) code_diff_empty"] is False
    assert doc["code_diff"]["changed_paths"] == ["04_scripts/02_chrono/run_S2a.py"]
    # rev1 R1-2 (T-2): the former allow-list file is now unexpected as well
    assert doc["git_status"]["unexpected"] == [
        " M 04_scripts/02_chrono/run_S2a.py",
        "?? 04_scripts/new.py",
    ]
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["exit_code"] == 2


# ---------------------------------------------------------------- plan rev1 (T-10)
def test_rev1_base_commit_and_empty_allow_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert judge.BASE_COMMIT == "92d22e0ea5fe527ec87bdbc7ed08fa477329345f"
    assert judge.ALLOWED_DIRTY == frozenset()
    assert judge.SEALED_RULES["las_k1_sch_plan_rev1.md"] == judge.PLAN_REV1_SHA256
    assert judge.SEALED_RULES["las_k1_sch_plan.md"] == judge.PLAN_SHA256
    GIT_CALLS.clear()
    monkeypatch.setattr(judge, "run_git", fake_git)
    snapshot = judge.identity_snapshot(tmp_path, "prelaunch")
    quiet_calls = [c for c in GIT_CALLS if c[:2] == ("diff", "--quiet")]
    assert quiet_calls == [
        ("diff", "--quiet", judge.BASE_COMMIT, HEAD, "--", *judge.CODE_DIFF_PATHS)
    ]
    assert set(snapshot["plan_sha256"]) == {"las_k1_sch_plan.md", "las_k1_sch_plan_rev1.md"}


def test_k0k_tool_sha_mismatch_is_stop(tmp_path: Path, no_git: None) -> None:
    record = identity_record("postrun")
    record["tool"]["sha256"] = "f" * 64
    doc = run_judge(tmp_path, SyntheticBatch(), postrun_record=record)
    assert doc["status"] == "stop" and doc["stop_reasons"] == ["K-0k"]


def test_k0k_missing_tool_record_is_stop(tmp_path: Path, no_git: None) -> None:
    record = identity_record("postrun")
    del record["tool"]
    doc = run_judge(tmp_path, SyntheticBatch(), postrun_record=record)
    assert doc["status"] == "stop" and "K-0k" in doc["stop_reasons"]


def test_missing_grid_end_is_incomplete(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.on["p3b_ext"]["crawler_gap"]["grid_end_m"] = None
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "incomplete" and doc["fail_reasons"] == []
    assert doc["e6"]["gateon"]["E-6b"]["failed"] is False


def test_empty_end_window_is_incomplete(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.steps[judge.CASE_GATEON]["t_s"][-1] = np.nan  # t_end NaN -> no sample in the window
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "incomplete"
    assert any("E-6a: empty end window" in r for r in doc["incomplete_reasons"])


def test_missing_stroke_is_incomplete(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.off["p3b"]["P3-5_clearance_stroke"]["s_motor_max_m"] = []
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "incomplete" and "C-S" not in doc["fail_reasons"]


def test_missing_baseline_force_is_incomplete_not_not_applicable(
    tmp_path: Path, no_git: None
) -> None:
    synthetic = SyntheticBatch()
    del synthetic.off["p3b"]["P3-3_leg_force"]["F_min_after_N"]
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "incomplete"
    assert doc["pair"]["C-F"]["applicable"] is None


def test_force_below_floor_is_not_applicable(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.off["p3b"]["P3-3_leg_force"]["F_min_after_N"] = [9000.0] * 4
    synthetic.on["p3b"]["P3-3_leg_force"]["F_min_after_N"] = [8000.0] * 4
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "pass" and doc["pair"]["C-F"]["applicable"] is False


def test_missing_value_with_structural_stop_is_stop(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.on["p3b_ext"]["crawler_gap"]["grid_end_m"] = None
    synthetic.entries[judge.CASE_GATEON]["rc"] = 1  # K-0i
    doc = run_judge(tmp_path, synthetic)
    assert doc["status"] == "stop"
    assert "K-0i" in doc["stop_reasons"] and doc["incomplete_reasons"]


def test_i8_band_with_crawler_load_counts_only_e6a(tmp_path: Path, no_git: None) -> None:
    synthetic = SyntheticBatch()
    synthetic.on["p3b_ext"]["crawler_gap"]["grid_end_m"] = 0.010
    synthetic.steps[judge.CASE_GATEON]["scm_crawler_normal_N"][-20:] = 500.0
    doc = run_judge(tmp_path, synthetic)
    e6b = doc["e6"]["gateon"]["E-6b"]
    assert e6b["outcome"] == "below_25mm_with_crawler_load"
    assert e6b["failed"] is False and e6b["flag"] is None
    assert "E-6_post_event_clearance" not in doc["flags"]["gateon"]
    assert doc["status"] == "fail" and doc["fail_reasons"] == ["E-6 gateon only: E-6a"]


def test_main_exit_code_and_last_line_json(
    tmp_path: Path, no_git: None, capsys: pytest.CaptureFixture
) -> None:
    batch_dir = SyntheticBatch().write(tmp_path / "batch")
    prelaunch, postrun = tmp_path / "pre.json", tmp_path / "post.json"
    prelaunch.write_text(json.dumps(identity_record("prelaunch")), encoding="utf-8")
    postrun.write_text(json.dumps(identity_record("postrun")), encoding="utf-8")
    out = tmp_path / "judge.json"
    code = judge.main(
        [
            "judge",
            "--batch",
            str(batch_dir),
            "--root",
            str(tmp_path),
            "--prelaunch",
            str(prelaunch),
            "--postrun",
            str(postrun),
            "--out",
            str(out),
        ]
    )
    last = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and last["status"] == "pass"
    assert json.loads(out.read_text(encoding="utf-8"))["exit_code"] == 0
