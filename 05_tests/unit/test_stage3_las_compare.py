"""``stage3_las_compare`` (criteria revision 12a, amending 12 2.2): the four row results, the
allowed meta keys, the empty set, the row count guard, ``OMP_WAIT_POLICY`` as a record only and
the plant check. Synthetic case folders and batch files."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import stage3_las_compare as las  # noqa: E402

PERIODS = 6
TIMES_S = 10.0 + 0.1 * np.arange(1, PERIODS + 1)
COMMANDS = np.linspace(-0.02, 0.02, PERIODS * 4).reshape(PERIODS, 4)
EVENTS = [{"t_s": 10.1, "name": "INFO_PRESSURE_ZERO_CALIBRATED:FL"},
          {"t_s": 10.5, "name": "INFO_READY"}]
ESTIMATE_PA = [1.5e6, 1.4e6, 1.3e6, 1.2e6]
S9_ARGV = ["python.exe", "run_S9.py", "level", "--threads", "4"]
S8C_ARGV = ["python.exe", "C:\\x\\04_scripts\\02_chrono\\run_S8C.py", "run"]
PLANT_SAMPLES = 60
PLANT_TIMES_S = 10.0 + 0.01 * np.arange(1, PLANT_SAMPLES + 1)
"""Plant samples every 10 ms; sample 39 is t = 10.4 s, the command instant of period 3."""
PLANT_WIDTHS = {"roll_pitch_deg": 2, "z_origin_m": 0, "scm_crawler_normal_N": 2,
                "body_quat_wxyz": 4, "crawler_normal_N": 0}
"""Second axis of the plant arrays (0 = one value per sample); the rest have four legs."""


def _plant(kind: las.RowKind, changes: dict[str, int] | None = None,
           drop: tuple[str, ...] = ()) -> dict[str, np.ndarray]:
    """Plant series of a row kind; ``changes`` = {array: first changed sample index}."""
    source = las.PLANT_SOURCES[kind]
    series = {source.time_key: PLANT_TIMES_S.copy()}
    for number, key in enumerate(source.array_keys):
        width = PLANT_WIDTHS.get(key, 4)
        shape = (PLANT_SAMPLES,) if width == 0 else (PLANT_SAMPLES, width)
        series[key] = np.full(shape, 1000.0 + number)
    for key, index in (changes or {}).items():
        series[key][index:] += 1.0
    return {key: value for key, value in series.items() if key not in drop}


def _result(*, pool: str = "pcore", threads: int | None = 4, omp: str | None = "PASSIVE",
            tag: str | None = None, extra_meta: dict | None = None,
            estimate_Pa: list[float] | None = None) -> dict[str, Any]:
    placement: dict[str, Any] = {"mode": pool}
    if omp is not None:
        placement["omp_wait_policy"] = omp
    meta = {"two_pressure": {"settings": {}, "fallback_rod_estimate_Pa": estimate_Pa
                             or ESTIMATE_PA},
            **(extra_meta or {})}
    v5 = {"hydraulic_options": {"valve_tau_s": 0.1}}
    if tag is not None:
        v5["controller_tag"] = tag
    return {"placement": placement, "args": {"threads": threads}, "controller_meta": meta,
            "v5_hydraulics": v5}


def _s9_case(folder: Path, *, commands: np.ndarray = COMMANDS, events: list | None = None,
             plant: dict[str, np.ndarray] | None = None, **result_options: Any) -> Path:
    folder.mkdir(parents=True)
    np.savez(folder / "controller_commands.npz", t_s=TIMES_S[:len(commands)],
             issued_u_m_s=commands)
    np.savez(folder / "step_series.npz", **(_plant(las.RowKind.S9) if plant is None else plant))
    result = {**_result(**result_options), "events": EVENTS if events is None else events}
    (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")
    return folder


def _s8c_case(folder: Path, *, commands: np.ndarray = COMMANDS, events: list | None = None,
              pool: str = "pcore", plant: dict[str, np.ndarray] | None = None,
              **result_options: Any) -> Path:
    """run_S8C layout: placement in ``case.json`` runner, events as ``C2Event(...)`` strings."""
    folder.mkdir(parents=True)
    np.savez(folder / "r8_series.npz", t=TIMES_S[:len(commands)], issued_u=commands)
    np.savez(folder / "pads.npz", **(_plant(las.RowKind.S8C) if plant is None else plant))
    result = _result(threads=None, **result_options)
    placement = result.pop("placement")
    placement["mode"] = pool
    (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")
    (folder / "case.json").write_text(json.dumps({"runner": {"placement": placement}}),
                                      encoding="utf-8")
    texts = [f"C2Event(t_s={e['t_s']!r}, name='{e['name']}')"
             for e in (EVENTS if events is None else events)]
    (folder / "controller_events.json").write_text(json.dumps(texts), encoding="utf-8")
    return folder


def _s9_row(case: str, stored: Path | None, pool: str = "pcore") -> dict[str, Any]:
    row: dict[str, Any] = {"case": case, "argv": S9_ARGV, "pool": pool}
    if stored is not None:
        row["stored_result"] = str(stored)
    return row


def _s8c_row(case: str, stored: Path, rerun: Path) -> dict[str, Any]:
    return {"case": case, "argv": S8C_ARGV, "pool": "pcore", "s8c_case_id": case,
            "stored_result": str(stored),
            "s8c_check": {"result_json": str(rerun / "result.json")}}


def _batch(folder: Path, rows: list[dict]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "batch.json"
    path.write_text(json.dumps({"batch": "V5-STAGE3-LAS", "cases": rows}), encoding="utf-8")
    return path


def _report(batch_json: Path, expected_rows: int, stored_map: Path | None = None) -> dict:
    return las.build_report([batch_json], stored_map, expected_rows, batch_json.parent)


def _only_row(report: dict) -> dict:
    (row,) = report["rows"]
    return row


@pytest.fixture()
def rerun_batch(tmp_path: Path) -> Path:
    return tmp_path / "batch_V5-STAGE3-LAS_x"


def test_silent_row_with_allowed_meta_keys(tmp_path: Path, rerun_batch: Path) -> None:
    stored = _s9_case(tmp_path / "stored" / "A")
    raised_Pa = [value + 1e5 for value in ESTIMATE_PA]
    las_meta = {"liftoff_approach_slow": {"enable": True, "fraction": 0.3},
                "two_pressure": {"settings": {"extend_start_rule": "tracked_bound"},
                                 "fallback_rod_estimate_Pa": raised_Pa}}
    _s9_case(rerun_batch / "A", tag="final_C4G2_P3_LAS", extra_meta=las_meta)
    row = _only_row(_report(_batch(rerun_batch, [_s9_row("A", stored)]), 1))
    assert row["status"] == las.RowStatus.SILENT_CONFIRMED
    meta = row["check3_meta"]
    assert meta["only_allowed"] and meta["other_paths"] == []
    assert set(meta["allowed_paths"]) == {"controller_tag", "liftoff_approach_slow", "p3"}
    assert meta["revision10_fallback_estimate"]["all"]


def test_other_meta_key_is_recorded_for_cause_check(tmp_path: Path, rerun_batch: Path) -> None:
    stored = _s9_case(tmp_path / "stored" / "A")
    _s9_case(rerun_batch / "A", extra_meta={"gains": {"Kp": 0.3}})
    report = _report(_batch(rerun_batch, [_s9_row("A", stored)]), 1)
    row = _only_row(report)
    assert row["status"] == las.RowStatus.SILENT_CONFIRMED
    assert row["check3_meta"]["other_paths"] == ["controller_meta.gains"]
    assert report["summary"]["meta_unexpected_cases"] == ["A"]


def test_lowered_fallback_estimate_is_not_allowed(tmp_path: Path, rerun_batch: Path) -> None:
    stored = _s9_case(tmp_path / "stored" / "A")
    lowered_Pa = [*ESTIMATE_PA[:3], ESTIMATE_PA[3] - 2.0]
    _s9_case(rerun_batch / "A", estimate_Pa=lowered_Pa)
    row = _only_row(_report(_batch(rerun_batch, [_s9_row("A", stored)]), 1))
    assert row["check3_meta"]["other_paths"] == [las.FALLBACK_ESTIMATE_PATH]
    assert row["check3_meta"]["only_allowed"] is False


def test_s8c_row_differs_at_first_period(tmp_path: Path) -> None:
    stored = _s8c_case(tmp_path / "S8" / "stored" / "B")
    changed = COMMANDS.copy()
    changed[3, 2] *= 0.6
    slow_events = [*EVENTS[:1], {"t_s": 10.4, "name": "INFO_LIFTOFF_SLOW:RL"}, *EVENTS[1:]]
    rerun = _s8c_case(tmp_path / "S8" / "rerun" / "B", commands=changed, events=slow_events)
    row = _only_row(_report(_batch(tmp_path / "batch", [_s8c_row("B", stored, rerun)]), 1))
    assert row["kind"] == las.RowKind.S8C
    assert row["status"] == las.RowStatus.DIFFERS
    assert not row["check1_commands_bit_identical"] and not row["check2_events_equal"]
    first = row["first_difference"]
    assert first["index"] == 3
    assert first["t_s"]["rerun"] == pytest.approx(10.4)
    assert first["events_in_period"]["rerun"] == [(10.4, "INFO_LIFTOFF_SLOW:RL")]
    assert first["events_in_period"]["stored"] == []
    assert row["rerun_liftoff_slow_events"] == [(10.4, "INFO_LIFTOFF_SLOW:RL")]
    assert row["check3_meta"]["applies"] is False


def test_longer_rerun_differs_after_the_common_prefix(tmp_path: Path, rerun_batch: Path) -> None:
    stored = _s9_case(tmp_path / "stored" / "A", commands=COMMANDS[:4])
    _s9_case(rerun_batch / "A")
    row = _only_row(_report(_batch(rerun_batch, [_s9_row("A", stored)]), 1))
    assert row["status"] == las.RowStatus.DIFFERS
    assert row["first_difference"]["index"] == 4
    assert row["first_difference"]["t_s"]["stored"] is None


def test_one_flipped_bit_differs() -> None:
    flipped = COMMANDS.copy()
    flipped.view(np.uint64)[2, 1] ^= 1
    assert las.first_differing_period(COMMANDS, flipped) == 2
    assert las.first_differing_period(COMMANDS, COMMANDS.copy()) is None


@pytest.mark.parametrize(("stored_options", "rerun_options", "reason_start"), [
    ({"pool": "ecore"}, {"pool": "ecore"}, "stored pool 'E'"),
    ({}, {"threads": 2}, "threads"),
    ({}, {"pool": "ecore"}, "pool"),
])
def test_not_comparable_conditions(tmp_path: Path, rerun_batch: Path, stored_options: dict,
                                   rerun_options: dict, reason_start: str) -> None:
    stored = _s9_case(tmp_path / "stored" / "A", **stored_options)
    _s9_case(rerun_batch / "A", **rerun_options)
    row = _only_row(_report(_batch(rerun_batch, [_s9_row("A", stored)]), 1))
    assert row["status"] == las.RowStatus.NOT_COMPARABLE
    assert any(reason.startswith(reason_start) for reason in row["reasons"])
    assert "check1_commands_bit_identical" not in row


def test_unrecorded_omp_against_passive_is_compared(tmp_path: Path, rerun_batch: Path) -> None:
    stored = _s9_case(tmp_path / "stored" / "A", omp=None)
    _s9_case(rerun_batch / "A", omp="PASSIVE")
    row = _only_row(_report(_batch(rerun_batch, [_s9_row("A", stored)]), 1))
    assert row["status"] == las.RowStatus.SILENT_CONFIRMED
    conditions = row["conditions"]
    assert conditions["stored"]["omp_wait_policy"] == {"value": "unrecorded",
                                                       "source": "unrecorded"}
    assert conditions["rerun"]["omp_wait_policy"] == {
        "value": "PASSIVE", "source": "result.json placement.omp_wait_policy"}
    assert conditions["omp_equal"] is False
    assert row["plant_check"]["plant_first"] is False


def test_omp_sources_case_json_then_batch_row(tmp_path: Path) -> None:
    stored = _s8c_case(tmp_path / "S8" / "stored" / "B")
    rerun = _s8c_case(tmp_path / "S8" / "rerun" / "B", omp=None)
    row_fields = {**_s8c_row("B", stored, rerun), "omp_wait_policy": "PASSIVE"}
    row = _only_row(_report(_batch(tmp_path / "batch", [row_fields]), 1))
    assert row["conditions"]["stored"]["omp_wait_policy"] == {
        "value": "PASSIVE", "source": "case.json runner.placement.omp_wait_policy"}
    assert row["conditions"]["rerun"]["omp_wait_policy"] == {
        "value": "PASSIVE", "source": "batch row omp_wait_policy"}
    assert row["conditions"]["omp_equal"] is True
    assert row["status"] == las.RowStatus.SILENT_CONFIRMED


def _changed_commands() -> np.ndarray:
    """Commands that differ from period 3 on (t_c = 10.4 s)."""
    changed = COMMANDS.copy()
    changed[3:, 0] *= 0.6
    return changed


def test_plant_diverging_before_commands_is_not_comparable(tmp_path: Path,
                                                           rerun_batch: Path) -> None:
    stored = _s9_case(tmp_path / "stored" / "A")
    _s9_case(rerun_batch / "A", commands=_changed_commands(),
             plant=_plant(las.RowKind.S9, {"z_origin_m": 20}))
    report = _report(_batch(rerun_batch, [_s9_row("A", stored)]), 1)
    row = _only_row(report)
    assert row["status"] == las.RowStatus.NOT_COMPARABLE
    check = row["plant_check"]
    assert check["plant_first"] is True and check["first_array"] == "z_origin_m"
    assert check["t_p_s"] == pytest.approx(10.21)
    assert check["t_c_s"] == pytest.approx(10.4)
    assert row["reasons"][0].startswith("plant diverged first (t_p=10.21")
    assert "array=z_origin_m" in row["reasons"][0]
    assert row["check1_commands_bit_identical"] is False  # checks 1-3 stay recorded
    assert report["summary"]["counts"]["plant_first"] == ["A"]
    assert report["summary"]["counts"]["not_comparable"] == 1


def test_plant_differing_with_equal_commands_is_not_comparable(tmp_path: Path) -> None:
    stored = _s8c_case(tmp_path / "S8" / "stored" / "B")
    rerun = _s8c_case(tmp_path / "S8" / "rerun" / "B",
                      plant=_plant(las.RowKind.S8C, {"crawler_normal_N": 55}))
    row = _only_row(_report(_batch(tmp_path / "batch", [_s8c_row("B", stored, rerun)]), 1))
    assert row["status"] == las.RowStatus.NOT_COMPARABLE
    assert row["check1_commands_bit_identical"] and row["check2_events_equal"]
    check = row["plant_check"]
    assert check["t_c_s"] == float("inf") and check["plant_first"] is True
    assert check["first_array"] == "crawler_normal_N"
    assert check["t_p_s"] == pytest.approx(10.56)


@pytest.mark.parametrize("plant_change_index", [39, 45])
def test_plant_following_the_commands_differs(tmp_path: Path, rerun_batch: Path,
                                              plant_change_index: int) -> None:
    """The plant changes at t_c (sample 39, 10.4 s) or after it: the LAS row ``differs``."""
    stored = _s9_case(tmp_path / "stored" / "A")
    _s9_case(rerun_batch / "A", commands=_changed_commands(),
             plant=_plant(las.RowKind.S9, {"F_cyl_N": plant_change_index}))
    report = _report(_batch(rerun_batch, [_s9_row("A", stored)]), 1)
    row = _only_row(report)
    assert row["status"] == las.RowStatus.DIFFERS
    assert row["plant_check"]["plant_first"] is False
    assert row["plant_check"]["first_array"] == "F_cyl_N"
    assert report["summary"]["counts"]["plant_first"] == []


def test_absent_plant_key_is_not_comparable(tmp_path: Path, rerun_batch: Path) -> None:
    stored = _s9_case(tmp_path / "stored" / "A",
                      plant=_plant(las.RowKind.S9, drop=("scm_crawler_normal_N",)))
    _s9_case(rerun_batch / "A")
    row = _only_row(_report(_batch(rerun_batch, [_s9_row("A", stored)]), 1))
    assert row["status"] == las.RowStatus.NOT_COMPARABLE
    assert row["reasons"] == [
        "plant series missing: stored step_series.npz key scm_crawler_normal_N"]
    assert row["plant_check"]["plant_first"] is None


def test_absent_plant_file_is_not_comparable(tmp_path: Path, rerun_batch: Path) -> None:
    stored = _s9_case(tmp_path / "stored" / "A")
    (_s9_case(rerun_batch / "A") / "step_series.npz").unlink()
    row = _only_row(_report(_batch(rerun_batch, [_s9_row("A", stored)]), 1))
    assert row["status"] == las.RowStatus.NOT_COMPARABLE
    assert row["reasons"] == ["plant series missing: rerun step_series.npz"]


def test_plant_length_only_difference_is_the_next_sample() -> None:
    longer = _plant(las.RowKind.S9)
    shorter = {key: value[:30] for key, value in longer.items()}
    t_p_s, first_array = las.first_plant_difference(shorter, longer, "t_s")
    assert t_p_s == pytest.approx(PLANT_TIMES_S[30]) and first_array == "t_s"
    assert las.first_plant_difference(longer, _plant(las.RowKind.S9), "t_s") == (
        float("inf"), None)


def test_plant_dtype_difference_is_the_first_sample() -> None:
    stored = _plant(las.RowKind.S9)
    rerun = {**stored, "s_motor_m": stored["s_motor_m"].astype(np.float32)}
    assert las.first_plant_difference(stored, rerun, "t_s") == (PLANT_TIMES_S[0], "s_motor_m")


def test_missing_stored_result_and_rerun_folder(tmp_path: Path, rerun_batch: Path) -> None:
    stored = _s9_case(tmp_path / "stored" / "C")
    _s9_case(rerun_batch / "A")
    rows = [_s9_row("A", None), _s9_row("C", stored)]
    report = _report(_batch(rerun_batch, rows), 2)
    statuses = {row["case"]: row for row in report["rows"]}
    assert statuses["A"]["status"] == las.RowStatus.MISSING
    assert statuses["A"]["reasons"] == ["stored: no case folder named"]
    assert statuses["C"]["status"] == las.RowStatus.MISSING
    assert any("rerun" in reason for reason in statuses["C"]["reasons"])
    assert report["summary"]["errors"] == ["no row compared (empty set)"]


def test_stored_map_wins_and_result_json_path_is_accepted(tmp_path: Path,
                                                         rerun_batch: Path) -> None:
    wrong = _s9_case(tmp_path / "wrong" / "A", commands=COMMANDS[:2])
    right = _s9_case(tmp_path / "right" / "A")
    _s9_case(rerun_batch / "A")
    stored_map = tmp_path / "stored_map.json"
    stored_map.write_text(json.dumps({"A": str(right / "result.json")}), encoding="utf-8")
    row = _only_row(_report(_batch(rerun_batch, [_s9_row("A", wrong)]), 1, stored_map))
    assert row["stored_source"] == "stored_map"
    assert row["stored"] == str(right)
    assert row["status"] == las.RowStatus.SILENT_CONFIRMED


def _run_main(capsys: pytest.CaptureFixture, *args: str) -> tuple[int, dict]:
    code = las.main(list(args))
    last_line = capsys.readouterr().out.strip().splitlines()[-1]
    return code, json.loads(last_line)


def test_main_exit_zero_with_differs(tmp_path: Path, rerun_batch: Path,
                                     capsys: pytest.CaptureFixture) -> None:
    stored = _s9_case(tmp_path / "stored" / "A", commands=COMMANDS * 2.0)
    _s9_case(rerun_batch / "A")
    batch_json = _batch(rerun_batch, [_s9_row("A", stored)])
    out_json = tmp_path / "out.json"
    code, status = _run_main(capsys, str(out_json), "--batch-json", str(batch_json),
                             "--expect-rows", "1")
    assert code == 0 and status["status"] == "ok"
    assert status["counts"]["differs"] == 1
    assert json.loads(out_json.read_text(encoding="utf-8"))["not_a_judgement"]


def test_main_row_count_mismatch_is_exit_two(tmp_path: Path, rerun_batch: Path,
                                             capsys: pytest.CaptureFixture) -> None:
    stored = _s9_case(tmp_path / "stored" / "A")
    _s9_case(rerun_batch / "A")
    batch_json = _batch(rerun_batch, [_s9_row("A", stored)])
    code, status = _run_main(capsys, str(tmp_path / "out.json"), "--batch-json",
                             str(batch_json))
    assert code == 2 and status["status"] == "input_error"
    assert status["errors"] == [f"1 batch rows, expected {las.DEFAULT_EXPECTED_ROWS}"]


def test_main_empty_batch_is_exit_two(tmp_path: Path, rerun_batch: Path,
                                      capsys: pytest.CaptureFixture) -> None:
    batch_json = _batch(rerun_batch, [])
    code, status = _run_main(capsys, str(tmp_path / "out.json"), "--batch-json",
                             str(batch_json), "--expect-rows", "0")
    assert code == 2 and status["errors"] == ["no row compared (empty set)"]


def test_main_missing_batch_file_is_exit_two(tmp_path: Path,
                                             capsys: pytest.CaptureFixture) -> None:
    code, status = _run_main(capsys, str(tmp_path / "out.json"), "--batch-json",
                             str(tmp_path / "absent" / "batch.json"))
    assert code == 2 and status["status"] == "input_error"
    assert not (tmp_path / "out.json").exists()


def test_main_bad_stored_map_is_exit_two(tmp_path: Path, rerun_batch: Path,
                                         capsys: pytest.CaptureFixture) -> None:
    batch_json = _batch(rerun_batch, [_s9_row("A", None)])
    stored_map = tmp_path / "stored_map.json"
    stored_map.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    code, status = _run_main(capsys, str(tmp_path / "out.json"), "--batch-json",
                             str(batch_json), "--stored-map", str(stored_map),
                             "--expect-rows", "1")
    assert code == 2 and "stored map" in status["errors"][0]
