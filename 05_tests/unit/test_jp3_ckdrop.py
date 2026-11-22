"""436.9 edition 5 erratum 2 2-9.5: the T-CK / DROPOUT plans (``jp3_ckdrop_plan.py``) and their
record (``jp3_ckdrop_record.py``) on synthetic inputs, the working folder elsewhere."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "04_scripts" / "04_hydraulic" / "coupled",
              ROOT / "04_scripts" / "03_control" / "s8"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import jp3_ckdrop_plan as ckdrop  # noqa: E402
import jp3_ckdrop_record as record  # noqa: E402
import rod_fault_plan as rfp  # noqa: E402

CASES = ["L2|g6|0|x0|top|Fs0", "L2|g6|1|x1|top|Fs0"]


def _selection(tmp_path: Path) -> tuple[Path, str]:
    document = {"cell_table": [{"rank": rank, "case": case, "leg": "FL", "phase": "tau_C"}
                               for rank, case in enumerate([*CASES, "L2|g6|2|x2|top|Fs0"])],
                "blocks": {f"b{j}": {"seed_index": 40 + j} for j in range(4)}}
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_plans_seeds_and_faults(tmp_path) -> None:
    selection, sha = _selection(tmp_path)
    scan, tests = tmp_path / "scan", tmp_path / "05_tests"
    scan.mkdir()
    tests.mkdir()
    (scan / "probe.json").write_text(json.dumps({"key": "L2|s80|g6|0|x0|top|Fs0"}),
                                     encoding="utf-8")  # s80 taken: T-CK moves to s81
    out = tmp_path / "ckdrop"
    document = ckdrop.select(selection, sha, scan, (tests,), out)
    assert document["seeds"]["tck"] == {"start": 80, "seed": 81, "repeats": 1}
    assert document["seeds"]["dropout"] == {"start": 81, "seed": 82, "repeats": 1}
    assert document["lines_per_bundle"] == 16
    assert (out / "tck_keys.txt").read_text(encoding="utf-8").splitlines() == [
        "L2|s81|g6|0|x0|top|Fs0", "L2|s81|g6|1|x1|top|Fs0"]
    for name, digest in document["outputs"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
    tck = rfp.load_plan(out / "tck_RL_plan.json")
    faults = list(tck.faults.values())
    assert len(faults) == 2 and {f.leg for f in faults} == {"RL"}
    assert all(f.anchor.text == "phase_enter:CHECK" and f.delay_reads == 0 for f in faults)
    assert all(f.kind == "STUCK" and f.value_bar == -100.0 for f in faults)
    dropout = rfp.load_plan(out / "dropout_FL_plan.json")
    assert {f.kind for f in dropout.faults.values()} == {"DROPOUT"}
    with pytest.raises(ckdrop.plan.NotUsable, match="has files"):
        ckdrop.select(selection, sha, scan, (tests,), out)
    with pytest.raises(ckdrop.plan.NotUsable, match="sha256"):
        ckdrop.select(selection, "0" * 64, scan, (tests,), tmp_path / "other")


def test_taken_seeds_are_skipped() -> None:
    seed, repeats = ckdrop.bundle_seed(89, CASES, frozenset(), {90, 91, 89})
    assert (seed, repeats) == (92, 3)
    # erratum 6 6-3: the new c dry seeds 92 / 93 are taken too
    assert {92, 93} <= ckdrop.TAKEN_SEEDS
    seed, repeats = ckdrop.bundle_seed(89, CASES, frozenset(), set(ckdrop.TAKEN_SEEDS) | {89})
    assert (seed, repeats) == (94, 5)


def test_record_lines_and_not_computed(tmp_path, monkeypatch, capsys) -> None:
    t4h = tmp_path / "t4h"
    t4h.mkdir()
    events = [[1.0, "FAULT_HEAD_PRESSURE:FL"], [2.0, "FAULT_HEAD_PRESSURE:FL"], [3.0, "WARN_X"]]
    np.savez(t4h / "a.npz", meta_json=np.array(json.dumps({"events": events})))
    run = tmp_path / "run.json"
    run.write_text(json.dumps({"results": [{
        "key": "cand=current#L2|s81|g6|0|x0|top|Fs0", "t4h_file": "a.npz",
        "rod_fault": {"fault_id": "f", "latched": {"t_s": 5.0}}, "base": {"t_ready_s": 40.0},
        "zero_calibration": {"legs": {"FL": {"status": "calibrated"}}}}]}), encoding="utf-8")
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    out = tmp_path / "record.json"
    assert record.main(["--run", f"dropout:FL:VBK={run}", "--t4h", f"dropout:FL:VBK={t4h}",
                        "--run", f"tck:FL:VBK0={run}", "--t4h", f"tck:FL:VBK0={t4h}",
                        "--run", f"tck:FR:VBK0={tmp_path / 'none.json'}",
                        "--out", str(out)]) == 0
    lines = json.loads(out.read_text(encoding="utf-8"))["lines"]
    dropout = next(line for line in lines if line["bundle"] == "dropout")
    assert dropout["fault_head_pressure_count"] == 2
    assert dropout["d1_undecided_periods"]["computed"] is False
    tck = next(line for line in lines if line["bundle"] == "tck" and line["fault_leg"] == "FL")
    assert tck["zero_calibration_status"]["FL"] == "calibrated"
    assert tck["fault_events"] == ["FAULT_HEAD_PRESSURE:FL"] and tck["t_ready_s"] == 40.0
    assert dropout["d1_undecided_periods"]["reason"] == "기록 키 없음: 시뮬레이션 경로 변경 필요"
    missing = next(line for line in lines if line["fault_leg"] == "FR")
    assert missing["computed"] is False
    pairs = json.loads(out.read_text(encoding="utf-8"))["tck_pairs"]
    assert pairs == [{"key": "cand=current#L2|s81|g6|0|x0|top|Fs0", "fault_leg": "FL",
                      "computed": False, "reason": "the pair has one arm only"}]
    assert record.main(["--run", "bad=x", "--out", str(tmp_path / "b.json")]) == 2


def _tck_arm(tmp_path: Path, arm: str, rows: list[tuple[str, list, list | None, float | None]]
             ) -> tuple[Path, Path]:
    """Run file and T4h folder of one T-CK arm: rows of (key, events, phase, t_ready_s)."""
    folder = tmp_path / f"t4h_{arm}"
    folder.mkdir()
    results = []
    for index, (key, events, phase, ready) in enumerate(rows):
        arrays = {"meta_json": np.array(json.dumps({"events": events}))}
        if phase is not None:
            arrays["phase"] = np.array(phase)
        np.savez(folder / f"r{index}.npz", **arrays)
        results.append({"key": key, "t4h_file": f"r{index}.npz", "rod_fault": {},
                        "base": {"t_ready_s": ready}})
    run = tmp_path / f"run_{arm}.json"
    run.write_text(json.dumps({"results": results}), encoding="utf-8")
    return run, folder


def test_tck_pairs_new_faults_and_ready(tmp_path, monkeypatch) -> None:
    key_a, key_b = "cand=current#L2|s80|g6|0|x0|top|Fs0", "cand=current#L2|s80|g9|1|x0|top|Fs0"
    run0, t4h0 = _tck_arm(tmp_path, "VBK0", [
        (key_a, [[1.0, "FAULT_ROD_PRESSURE:FL"]], ["CHECK", "LIFT"], 40.0),
        (key_b, [], ["CHECK", "LIFT"], 50.0)])
    run1, t4h1 = _tck_arm(tmp_path, "VBK", [
        (key_a, [[1.0, "FAULT_ROD_PRESSURE:FL"], [2.0, "FAULT_STUCK:FR"]],
         ["CHECK", "fault", "fault"], 42.5),
        (key_b, [], ["CHECK", "LIFT"], None)])
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    out = tmp_path / "record.json"
    assert record.main(["--run", f"tck:FL:VBK0={run0}", "--t4h", f"tck:FL:VBK0={t4h0}",
                        "--run", f"tck:FL:VBK={run1}", "--t4h", f"tck:FL:VBK={t4h1}",
                        "--out", str(out)]) == 0
    pairs = {pair["key"]: pair for pair in json.loads(out.read_text(encoding="utf-8"))["tck_pairs"]}
    assert pairs[key_a] == {"key": key_a, "fault_leg": "FL", "ready_vbk0_s": 40.0,
                            "ready_vbk_s": 42.5, "ready_difference_s": 2.5,
                            "vbk0_ready_vbk_not": False,
                            "new_faults": [["FAULT_STUCK", "FR"], ["PHASE_FAULT", "–"]]}
    assert pairs[key_b] == {"key": key_b, "fault_leg": "FL", "ready_vbk0_s": 50.0,
                            "ready_vbk_s": None, "ready_difference_s": None,
                            "vbk0_ready_vbk_not": True, "new_faults": []}


def test_tck_pairs_missing_t4h_is_not_computed(tmp_path) -> None:
    key = "cand=current#L2|s80|g6|0|x0|top|Fs0"
    run0, t4h0 = _tck_arm(tmp_path, "VBK0", [(key, [], None, 40.0)])
    run1, _ = _tck_arm(tmp_path, "VBK", [(key, [], None, 41.0)])
    report = record.record({("tck", "FL", "VBK0"): run0, ("tck", "FL", "VBK"): run1},
                           {("tck", "FL", "VBK0"): t4h0})
    (pair,) = report["tck_pairs"]
    assert pair["new_faults"] == {"computed": False, "reason": "a T4h record missing"}
    assert pair["ready_difference_s"] == 1.0 and pair["vbk0_ready_vbk_not"] is False
