"""K-2 post-run audit fixes (2026-11-11): acc_d8 exit code on error rows, the ACC_PROVENANCE interpreter record,
full ``problems`` / ``failed_rows`` lists of ``k2_judge`` and the V-7 SCM record adapter ``k2_v7_scm_rows``.

The adapter tests build synthetic SCM case folders (no simulation). The acc_d8 end-to-end test runs one harness
case of the V-3 ``L1eq`` arm on a ``kt`` row, which the plant refuses (``crawler_kt_rel together with
ktcr_rel_kn``), so the run has exactly one error row (about 1 min).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
K2_SCRIPTS = ROOT / "04_scripts" / "03_control" / "k2"
ACCEPTANCE = ROOT / "04_scripts" / "03_control" / "touch_phase" / "acceptance"
ACC_D8 = ACCEPTANCE / "acc_d8.py"
ADAPTER = K2_SCRIPTS / "k2_v7_scm_rows.py"
K2_POINTS = ROOT / "06_analysis" / "02_control" / "k2" / "k2_points_5p5_3p5.json"
for _folder in (K2_SCRIPTS, ROOT / "04_scripts" / "03_control" / "d8x"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import k2_judge  # noqa: E402
import k2_v7_scm_rows as adapter  # noqa: E402

CHILD_TIMEOUT_S = 600


def _child_env() -> dict[str, str]:
    return dict(os.environ, ACC_WT=str(ROOT), PYTHONDONTWRITEBYTECODE="1")


def _run(argv: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", *argv], capture_output=True, text=True,
                          env=_child_env(), cwd=str(ROOT), timeout=CHILD_TIMEOUT_S, check=False, **kwargs)


# --- acc_d8 exit code -----------------------------------------------------------------------------------------
def test_acc_d8_exit_code_rule() -> None:
    code = ("import json, sys; folder = sys.argv[1]; sys.argv = ['acc_d8.py', 'x.json']; "
            "sys.path.insert(0, folder); import acc_d8; "
            "rows = [{'id': 'a'}, {'id': 'b', 'error': 'E'}]; "
            "print(json.dumps([acc_d8.count_error_rows(rows), acc_d8.exit_code_for(0, False), "
            "acc_d8.exit_code_for(1, False), acc_d8.exit_code_for(3, True), acc_d8.EXIT_ROW_ERRORS]))")
    done = _run(["-c", code, str(ACCEPTANCE)])
    assert done.returncode == 0, done.stderr[-3000:]
    assert json.loads(done.stdout.strip().splitlines()[-1]) == [1, 0, 2, 0, 2]


def test_acc_d8_error_row_ends_with_code_2_and_allow_errors_keeps_0(tmp_path) -> None:
    base = [str(ACC_D8), "--points", str(K2_POINTS), "--k1", "off", "--aug", "L1eq", "--stages", "kt",
            "--limit", "1", "--workers", "1"]
    out = tmp_path / "ra.json"
    done = _run([*base[:1], str(out), *base[1:]])
    assert done.returncode == 2, done.stderr[-3000:]
    assert done.stdout.strip().splitlines()[-1].endswith("errors 1")
    runs = json.loads(out.read_text(encoding="utf-8"))["runs"]
    assert len(runs) == 1 and "crawler_kt_rel together with ktcr_rel_kn" in runs[0]["error"]
    # the partial file makes the second start reuse the row: same output, the old exit 0 with the option
    again = _run([*base[:1], str(out), *base[1:], "--allow-errors"])
    assert again.returncode == 0, again.stderr[-3000:]
    assert json.loads(out.read_text(encoding="utf-8"))["runs"] == runs


# --- ACC_PROVENANCE interpreter -------------------------------------------------------------------------------
def test_write_provenance_records_the_interpreter(tmp_path) -> None:
    target = tmp_path / "provenance" / "step.json"
    code = ("import sys; from pathlib import Path; folder, out, src = sys.argv[1], sys.argv[2], sys.argv[3]; "
            "sys.path[:0] = [folder, src]; import acc_common; "
            "acc_common.write_provenance(Path(out), {'script': 's.py', 'argv': []}); "
            "print('meta' , sorted(acc_common.provenance()))")
    done = _run(["-c", code, str(ACCEPTANCE), str(target), str(ROOT / "03_src")])
    assert done.returncode == 0, done.stderr[-3000:]
    record = json.loads(target.read_text(encoding="utf-8"))
    assert record["python_executable"] == sys.executable
    assert record["python_version"].split()[0] == sys.version.split()[0]
    assert record["script"] == "s.py" and "c2_sha256" in record
    assert "python_executable" not in done.stdout  # the run meta (provenance()) keeps its keys


# --- k2_judge full lists --------------------------------------------------------------------------------------
def _runs_file(tmp_path: Path, name: str, runs: list[dict]) -> str:
    path = tmp_path / name
    path.write_text(json.dumps({"runs": runs}), encoding="utf-8")
    return str(path)


def test_options_off_and_aug_problems_list_every_row(tmp_path) -> None:
    runs = [{"id": f"r{i}", "aug_arm": "AUG"} for i in range(50)]
    assert len(k2_judge.options_off_problems([_runs_file(tmp_path, "a.json", runs)], "V-2")) == 50
    error_rows = [{"id": f"e{i}", "error": "ValueError"} for i in range(48)]
    problems = k2_judge._aug_problems([_runs_file(tmp_path, "b.json", error_rows)], "L1eq")
    assert len(problems) == 48 and all(p.startswith("E-5 e") for p in problems)


def test_failed_rows_are_not_cut_at_300() -> None:
    rows = [{"id": f"r{i}", "k1_on": False, "verdict": "fail", "fail_items": ["J3"], "not_judgeable": []}
            for i in range(450)]
    rows.append({"id": "ok", "k1_on": False, "verdict": "pass", "fail_items": [], "not_judgeable": []})
    assert len(k2_judge._failed({"off": rows})) == 450


def test_v5_evidence_lists_every_row() -> None:
    docs = [{"meta": {}, "runs": [{"key": f"k{i}", "touch_creep_latch": True, "controller_tag": "x_TCL"}
                                  for i in range(60)]}]
    assert len(k2_judge.v5_evidence("d8", "off", docs)) == 60


def test_markdown_marks_a_cut_value() -> None:
    short = k2_judge._markdown_value(["a"])
    assert "truncated" not in short
    long_value = [f"problem {i}" for i in range(400)]
    text = k2_judge._markdown_value(long_value)
    assert "truncated: true" in text and "400 items" in text
    assert f"{len(json.dumps(long_value))} chars" in text


# --- V-7 SCM record adapter -----------------------------------------------------------------------------------
T0_S = 8.0
SERIES_END_S = 40.0
LIFT_SAMPLE_S = 14.0
J1_DIP = (16.5, 2, 9000.0)
READY_S = {"off": 15.0, "tcl": 15.0}


def _write_case(folder: Path, name: str, ready_s: float) -> None:
    is_tcl = name.endswith("_tcl")
    folder.mkdir(parents=True)
    (folder / "record").mkdir()
    t = np.round(np.arange(T0_S + 0.001, SERIES_END_S + 1e-9, 0.001), 6)
    normal = np.where(t[:, None] >= 10.0, 20000.0, 0.0) * np.ones((1, 4))
    normal[np.isclose(t, LIFT_SAMPLE_S)] = 0.0
    force = np.full((t.size, 4), 30000.0)
    force[np.isclose(t, J1_DIP[0]), J1_DIP[1]] = J1_DIP[2]
    sinkage = np.where(t[:, None] >= 10.0, 0.002, -0.3) * np.ones((1, 4))
    stroke = np.full((t.size, 4), 0.34)
    attitude = np.zeros((t.size, 2))
    attitude[t >= ready_s] = [0.01, -0.02]
    np.savez_compressed(folder / "step_series.npz", t_s=t, scm_pad_normal_N=normal, F_cyl_N=force,
                        pad_sinkage_geometric_m=sinkage, s_motor_m=stroke, roll_pitch_deg=attitude)
    tr = np.round(np.arange(T0_S + 0.1, SERIES_END_S + 1e-9, 0.1), 6)
    crawler = np.zeros((tr.size, 3))
    crawler[tr < 13.0, 2] = 1e5
    u_applied = np.zeros((tr.size, 4))
    u_applied[tr < 12.0] = 0.002
    cyl = np.full((tr.size, 4), 0.013273229 * 9e6)
    np.savez_compressed(folder / "record" / "record.npz", t=tr, F_crawler=crawler, F_cyl=cyl, u_applied=u_applied)
    (folder / "record" / "meta.json").write_text("{}", encoding="utf-8")
    latches = [{"leg": leg, "t_s": 11.9, "reason": "load_window", "creep_travel_m": 0.0016} for leg in adapter.LEG_NAMES]
    events = [{"t_s": 11.9, "name": f"INFO_TOUCH_CREEP_LATCH:{leg}"} for leg in adapter.LEG_NAMES] if is_tcl else []
    events += [{"t_s": 13.0, "name": "crawler_liftoff_confirmed"}]
    if is_tcl:
        events.append({"t_s": 11.95, "name": "INFO_TOUCH_CREEP_CAP:RR"})
    result = {
        "t_loop_start_s": T0_S,
        "phases": [{"t_s": 8.1, "phase": "check"}, {"t_s": 9.0, "phase": "touch"},
                   {"t_s": 12.0, "phase": "level"}, {"t_s": ready_s, "phase": "ready"}],
        "events": sorted(events, key=lambda e: e["t_s"]),
        "args": {"case": name, "floor_roll": 0.0, "floor_pitch": 0.0, "fs_kN": 4.0},
        "meta": {"actuator": {"head_area_m2": [0.013273229] * 4}},
        "c2_setup": {"expect_controller": {"name": "tag_TCL" if is_tcl else "tag", "checks": [{"ok": True}],
                                           "ok": True},
                     "k1_order_gate_effective": True, "touch_creep_effective": is_tcl,
                     "touch_creep": "on" if is_tcl else "off"},
        "controller_meta": {"target": {"target_rad": [0.0, 0.0]},
                            "touch_creep_latch": {"latches": latches if is_tcl else []},
                            "touch_twist_hold": {"twist_load_estimate_N": -220.0}},
        "p3b": {"departure": {"t_departure_s": 12.5}, "P3-1_crawler": {"recontact_count": 0}},
    }
    (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")


def _batch(tmp_path: Path, ready_tcl_j1: float = 15.0) -> Path:
    batch = tmp_path / "결과 batch_k2_v7"
    cases = []
    for name in adapter.EXPECTED_CASES:
        ready = ready_tcl_j1 if name == "K2V7_P3b_J1_B_top_Fs4_tcl" else 15.0
        _write_case(batch / name, name, ready)
        cases.append({"case": name, "rc": 0})
    (batch / "batch.json").write_text(json.dumps({"cases": cases}), encoding="utf-8")
    return batch


def _tree(folder: Path) -> dict[str, str]:
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


def _adapter(*argv) -> subprocess.CompletedProcess:
    return _run([str(ADAPTER), *[str(a) for a in argv]])


def test_adapter_rows_keys_values_and_batch_unchanged(tmp_path) -> None:
    batch = _batch(tmp_path, ready_tcl_j1=26.0)
    before = _tree(batch)
    out_dir = tmp_path / "v7_rows"
    report = tmp_path / "report.json"
    done = _adapter("--out-report", report, "rows", "--batch", batch, "--out-dir", out_dir)
    assert done.returncode == 0, done.stdout + done.stderr[-3000:]
    assert _tree(batch) == before
    summary = json.loads(report.read_text(encoding="utf-8"))
    pairs = {pair["tcl"]: pair for pair in summary["pairs"]}
    assert pairs["K2V7_P3b_J1_B_top_Fs4_tcl"]["ready_delay_s"] == pytest.approx(11.0)
    assert pairs["K2V7_P3b_J1_B_top_Fs4_tcl"]["report_to_user"] is True  # CAP 1 and READY + 11 s
    row = json.loads((out_dir / "K2V7_P3b_J1_B_top_Fs4_tcl" / "k2_row.json").read_text(encoding="utf-8"))
    assert set(k2_judge.CHRONO_ROW_KEYS) <= set(row)
    assert row["record_only"] is True and row["note"] == adapter.RECORD_NOTE
    assert row["input_sha256"]["result.json"] == hashlib.sha256(
        (batch / "K2V7_P3b_J1_B_top_Fs4_tcl" / "result.json").read_bytes()).hexdigest()
    assert row["controller_tag"] == "tag_TCL" and row["touch_creep_latch"] is True
    assert row["t_touch_s"] == pytest.approx(4.0) and row["t_touch_start_s"] == pytest.approx(1.0)
    assert row["t_crawler_off_s"] == pytest.approx(5.0) and row["t_loc_s"] == pytest.approx(5.0)
    assert row["J1_min_cyl_after_lift_N"] == J1_DIP[2] and row["J1_leg"] == J1_DIP[1]
    assert row["J1_t_s"] == pytest.approx(J1_DIP[0] - T0_S)
    assert row["J3_pad_lift_samples"] == 1 and row["J3_pad_normal_min_N"] == 0.0
    assert row["J4_att_max_after_ready_deg"] == pytest.approx(0.02)
    assert row["J6_max_moving_bar"] == pytest.approx(90.0) and row["J6_max_locked_bar"] == pytest.approx(90.0)
    assert row["cap_events"] == 1 and row["false_latch_legs"] == []
    legs = row["v7_record"]["latch_legs"]
    assert set(legs) == set(adapter.LEG_NAMES)
    assert legs["FL"]["latch_t_s"] == pytest.approx(3.9) and legs["FL"]["pad_sinkage_geometric_m"] == 0.002
    assert row["events"][0][0] == pytest.approx(3.9)
    with np.load(out_dir / "K2V7_P3b_J1_B_top_Fs4_tcl" / "k2_pads.npz", allow_pickle=False) as pads:
        assert pads["N"].shape == (32000, 4) and pads["t"][0] == pytest.approx(0.001)
    off = json.loads((out_dir / "K2V7_P3b_J1_B_top_Fs4_off" / "k2_row.json").read_text(encoding="utf-8"))
    assert off["cap_events"] == 0 and off["v7_record"]["latch_legs"] == {}


def test_adapter_refuses_outputs_in_the_batch_and_existing_files(tmp_path) -> None:
    batch = _batch(tmp_path)
    assert _adapter("rows", "--batch", batch, "--out-dir", batch / "rows").returncode == 2
    out_dir = tmp_path / "rows"
    assert _adapter("rows", "--batch", batch, "--out-dir", out_dir).returncode == 0
    assert _adapter("rows", "--batch", batch, "--out-dir", out_dir).returncode == 2
    assert _adapter("rows", "--batch", batch, "--out-dir", out_dir, "--overwrite").returncode == 0
    (batch / "K2V7_P3b_J2_B_top_Fs4_off" / "step_series.npz").unlink()
    assert _adapter("rows", "--batch", batch, "--out-dir", tmp_path / "rows2").returncode == 1


def test_fill_manifest_and_record_v7(tmp_path) -> None:
    batch = _batch(tmp_path)
    rows = tmp_path / "v7_rows"
    assert _adapter("rows", "--batch", batch, "--out-dir", rows).returncode == 0
    manifest = {"v7": {"rows": {name: {"row_json": f"{{BATCH_V7}}\\{name}\\k2_row.json",
                                       "pads_npz": f"{{BATCH_V7}}\\{name}\\k2_pads.npz"}
                                for name in adapter.EXPECTED_CASES}}}
    source = tmp_path / "k2_manifest.json"
    source.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    filled = tmp_path / "judgement" / "k2_manifest_v7filled.json"
    report = tmp_path / "fill.json"
    done = _adapter("--out-report", report, "fill-manifest", "--manifest", source, "--batch-v7", rows,
                    "--out", filled)
    assert done.returncode == 0, done.stdout + done.stderr[-3000:]
    assert json.loads(report.read_text(encoding="utf-8"))["replaced"] == 8
    assert "{BATCH_V7}" not in filled.read_text(encoding="utf-8")
    record = tmp_path / "record_v7.json"
    judged = _run([str(K2_SCRIPTS / "k2_judge.py"), "--out", str(record), "record-v7", "--manifest", str(filled)])
    assert judged.returncode == 0, judged.stdout + judged.stderr[-3000:]
    rows_out = json.loads(record.read_text(encoding="utf-8"))["rows"]
    assert rows_out["K2V7_P3b_J1_B_top_Fs4_tcl"]["latches"] == 4 and rows_out["K2V7_P3b_J1_B_top_Fs4_tcl"]["cap"] == 1
    # the source stays; another placeholder left is an input error; --out = source is refused
    assert "{BATCH_V7}" in source.read_text(encoding="utf-8")
    manifest["v7"]["commit"] = "{JUDGE_COMMIT}"
    source.write_text(json.dumps(manifest), encoding="utf-8")
    left = _adapter("--out-report", report, "fill-manifest", "--manifest", source, "--batch-v7", rows,
                    "--out", tmp_path / "f2.json")
    assert left.returncode == 2
    assert json.loads(report.read_text(encoding="utf-8"))["placeholders_left"] == ["{JUDGE_COMMIT}"]
    assert _adapter("fill-manifest", "--manifest", source, "--batch-v7", rows, "--out", source).returncode == 2
