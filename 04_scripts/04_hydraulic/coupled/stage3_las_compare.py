"""Criteria revision 12a: record each LAS-tag rerun row of v5 stage 3 against its stored row.

Revision 12a amends revision 12 2.2 (``v5_criteria_rev12a.md`` 1, 3 and 4). A record tool, not
a judgement (revision 12 2.2: "기록만 한다"). Per row of the rerun ``batch.json`` (one or
more files, ``07_results/S9/batch_V5-STAGE3-LAS_<stamp>/batch.json``):

* stored row folder: row field ``stored_result`` (case folder or its ``result.json``), or an
  entry of ``--stored-map`` (JSON ``{case: path}``; the map wins). Relative paths are read
  against ``--root``.
* rerun row folder: S9 rows ``<batch.json folder>/<case>``; run_S8C rows the folder of
  ``s8c_check.result_json``.
* conditions (revision 12a 1 "해시 비교가 성립하는 조건"): ``--threads`` (``result.json``
  ``args.threads``, else ``num_threads_chrono``; run_S8C has none on both sides) and the pool
  (``placement.mode``, else ``case.json`` ``runner.placement.mode``, the rerun side also the
  batch row ``pool``). Either different, or a stored row not on P cores -> ``not_comparable``
  (no comparison).
* ``OMP_WAIT_POLICY`` is recorded only (revision 12a 3): ``{value, source}`` per side from
  ``result.json`` ``placement.omp_wait_policy``, else ``case.json``
  ``runner.placement.omp_wait_policy``, else the rerun batch row field ``omp_wait_policy``,
  else ``unrecorded``; ``omp_equal`` says whether the two values match.
* check 1: command arrays bit-identical. S9: ``controller_commands.npz`` ``issued_u_m_s``;
  run_S8C: ``r8_series.npz`` ``issued_u``.
* check 2: controller events (time, name) equal (``controller_events.json``, else
  ``result.json`` ``events``).
* check 3 (rows of checks 1 and 2 equal): ``controller_meta`` / ``v5_hydraulics`` differ only
  in ``controller_tag``, the ``liftoff_approach_slow`` block, the ③ keys of
  ``p3_chrono_check`` (revision 10 1) and ``two_pressure.fallback_rod_estimate_Pa`` under
  revision 10 conditions A, B, C (``p3_chrono_check.fallback_estimate_conditions``). Other
  differing keys are recorded for a cause check (python-expert).
* plant check (revision 12a 4, amended by revision 12b 2; rows meeting the conditions): plant
  arrays compared byte for byte (dtype and shape included) with their time array. S9:
  ``step_series.npz`` (time ``t_s``); run_S8C: ``pads.npz`` (time ``t``); core arrays in
  ``CORE_PLANT_ARRAYS``, auxiliary (crawler normal force) in ``AUX_PLANT_ARRAYS``. t_p = time of
  the first differing plant sample, t_c = time of the first differing command period (+inf
  when equal). t_p < t_c - 1e-6 s -> ``not_comparable`` ("plant diverged first"). The file, a
  core or the time array absent on either side -> ``not_comparable`` ("plant series
  missing: <side>:<name>"); an auxiliary array absent on both sides is left out
  (``plant_check.excluded_arrays``), absent on one side only -> ``not_comparable``
  ("auxiliary plant array on one side only: <name> (<side without it>)"). Checks 1-3 stay
  recorded.

Row status: ``silent_confirmed`` (checks 1 and 2 equal: LAS-b and ③ not acting),
``differs`` (first differing control period index and time, the events of that period,
``INFO_LIFTOFF_SLOW*`` and fallback events), ``not_comparable`` (reasons) or ``missing``
(reasons). ``plant_check`` times are JSON numbers; +inf is written as ``Infinity``.

Read only. Writes one JSON file; the last stdout line is a ``status`` JSON.
Exit code 0 = recorded (``differs`` included), 2 = input error: a batch file or the stored map
unreadable, a batch row count other than ``--expect-rows`` or no row compared.

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/stage3_las_compare.py <out_json>
      --batch-json 07_results/S9/batch_V5-STAGE3-LAS_<stamp>/batch.json [--batch-json ...]
      [--stored-map stored_map.json] [--expect-rows 37] [--root <project root>]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:  # -I drops the script folder from sys.path
    sys.path.insert(0, str(HERE))

import p3_chrono_check as p3_check  # noqa: E402

ROOT = HERE.parents[2]
DEFAULT_EXPECTED_ROWS = 37
"""Criteria revision 12 2.1: 34 stage 3 rows + 3 pair rows."""
RULE = ("criteria revision 12a (rev. 12 2.2 amended), sha256 e171141dce180fbb; "
        "revision 12b, sha256 0d17f87e9532d558")
CONTROL_PERIOD_S = 0.1
EVENT_TIME_TOL_S = 1e-6
"""Event times and control instants of one run share the engine clock (rounding only)."""
PLANT_FIRST_TOL_S = EVENT_TIME_TOL_S
"""Revision 12a 4 and 7: plant first when t_p < t_c - this margin."""
MAX_LISTED_EVENTS = 20
LIFTOFF_SLOW_EVENT_PREFIX = "INFO_LIFTOFF_SLOW"
UNRECORDED = "unrecorded"
P_CORE_POOL = "P"
POOL_NAMES = {"pcore": P_CORE_POOL, "ecore": "E"}
META_BLOCKS = ("controller_meta", "v5_hydraulics")
CONTROLLER_TAG_KEY = "controller_tag"
LAS_META_BLOCK = "liftoff_approach_slow"
FALLBACK_ESTIMATE_PATH = f"controller_meta.{p3_check.FALLBACK_ESTIMATE_PATH}"
S8C_SCRIPT_NAME = "run_S8C.py"


class RowKind(StrEnum):
    S9 = "S9"
    S8C = "S8C"


class RowStatus(StrEnum):
    SILENT_CONFIRMED = "silent_confirmed"
    DIFFERS = "differs"
    NOT_COMPARABLE = "not_comparable"
    MISSING = "missing"


class InputError(Exception):
    """An input that makes the whole record meaningless (exit code 2)."""


@dataclass(frozen=True)
class CommandSource:
    file_name: str
    time_key: str
    command_key: str


COMMAND_SOURCES = {
    RowKind.S9: CommandSource("controller_commands.npz", "t_s", "issued_u_m_s"),
    RowKind.S8C: CommandSource("r8_series.npz", "t", "issued_u"),
}


@dataclass(frozen=True)
class PlantSource:
    """Plant series file and its time array of a row kind (revision 12a 4), axis 0 = sample."""

    file_name: str
    time_key: str


PLANT_SOURCES = {
    RowKind.S9: PlantSource("step_series.npz", "t_s"),
    RowKind.S8C: PlantSource("pads.npz", "t"),
}
CORE_PLANT_ARRAYS = {
    RowKind.S9: ("F_cyl_N", "s_motor_m", "roll_pitch_deg", "z_origin_m", "scm_pad_normal_N"),
    RowKind.S8C: ("F_cyl", "s_motor", "body_quat_wxyz", "N"),
}
"""Revision 12b 2: may not be absent (the time array is core as well)."""
AUX_PLANT_ARRAYS = {
    RowKind.S9: ("scm_crawler_normal_N",),
    RowKind.S8C: ("crawler_normal_N",),
}
"""Revision 12b 2: crawler normal force; left out when absent on both sides (V0 rows record
no ``V5_RECORD_FIELDS``, revision 12b 1)."""


@dataclass(frozen=True)
class BatchRow:
    case: str
    kind: RowKind
    batch_json: Path
    fields: dict[str, Any]


@dataclass(frozen=True)
class CaseRun:
    """One case folder with its ``result.json`` (and ``case.json`` of run_S8C, if any)."""

    folder: Path
    result: dict[str, Any]
    case_json: dict[str, Any]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(path_text: str, root: Path) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else root / path


def _row_kind(row: dict[str, Any]) -> RowKind:
    is_s8c = "s8c_case_id" in row or any(
        Path(str(item)).name == S8C_SCRIPT_NAME for item in row.get("argv", []))
    return RowKind.S8C if is_s8c else RowKind.S9


def load_batch_rows(batch_jsons: list[Path]) -> list[BatchRow]:
    """Rows of the rerun ``batch.json`` files, in file order.

    Raises:
        InputError: A file missing, unreadable or without a ``cases`` list.
    """
    rows = []
    for batch_json in batch_jsons:
        try:
            cases = _read_json(batch_json)["cases"]
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise InputError(f"batch file {batch_json}: {error!r}") from error
        for row in cases:
            rows.append(BatchRow(str(row["case"]), _row_kind(row), batch_json, row))
    return rows


def load_stored_map(map_path: Path | None) -> dict[str, str]:
    """``{case: stored folder}`` of ``--stored-map`` (empty without it).

    Raises:
        InputError: The file missing, unreadable or not a JSON object of strings.
    """
    if map_path is None:
        return {}
    try:
        mapping = _read_json(map_path)
    except (OSError, ValueError) as error:
        raise InputError(f"stored map {map_path}: {error!r}") from error
    if not isinstance(mapping, dict) or not all(isinstance(v, str) for v in mapping.values()):
        raise InputError(f"stored map {map_path}: not a JSON object {{case: path}}")
    return mapping


def _rerun_folder(row: BatchRow) -> Path | None:
    if row.kind is RowKind.S9:
        return row.batch_json.parent / row.case
    result_json = (row.fields.get("s8c_check") or {}).get("result_json")
    return None if result_json is None else Path(result_json).parent


def _stored_folder(row: BatchRow, stored_map: dict[str, str],
                   root: Path) -> tuple[Path | None, str | None]:
    """(stored case folder, source of the path) or (None, None)."""
    if row.case in stored_map:
        path, source = _resolve(stored_map[row.case], root), "stored_map"
    elif row.fields.get("stored_result"):
        path, source = _resolve(str(row.fields["stored_result"]), root), "row.stored_result"
    else:
        return None, None
    return (path.parent if path.is_file() else path), source


def _load_case_run(folder: Path | None, kind: RowKind, side: str) -> tuple[CaseRun | None, list]:
    """The case run of a folder, or None with the reasons it is missing."""
    if folder is None:
        return None, [f"{side}: no case folder named"]
    command_file = folder / COMMAND_SOURCES[kind].file_name
    missing = [f"{side}: {path} missing" for path in (folder / "result.json", command_file)
               if not path.is_file()]
    if missing:
        return None, missing
    case_json_path = folder / "case.json"
    case_json = _read_json(case_json_path) if case_json_path.is_file() else {}
    return CaseRun(folder, _read_json(folder / "result.json"), case_json), []


def _placement(run: CaseRun) -> dict[str, Any]:
    placement = run.result.get("placement")
    if isinstance(placement, dict):
        return placement
    return (run.case_json.get("runner") or {}).get("placement") or {}


def _pool(run: CaseRun, row_pool: str | None) -> str:
    mode = _placement(run).get("mode") or row_pool
    return POOL_NAMES.get(str(mode), UNRECORDED)


def omp_wait_policy(run: CaseRun, row_value: str | None = None) -> dict[str, str]:
    """``{value, source}`` of ``OMP_WAIT_POLICY`` (revision 12a 3, recorded only).

    Args:
        run: The case run.
        row_value: Batch row field ``omp_wait_policy`` (rerun side only).
    """
    result_placement = run.result.get("placement")
    if isinstance(result_placement, dict) and result_placement.get("omp_wait_policy"):
        return {"value": str(result_placement["omp_wait_policy"]),
                "source": "result.json placement.omp_wait_policy"}
    runner_placement = (run.case_json.get("runner") or {}).get("placement") or {}
    if runner_placement.get("omp_wait_policy"):
        return {"value": str(runner_placement["omp_wait_policy"]),
                "source": "case.json runner.placement.omp_wait_policy"}
    if row_value:
        return {"value": str(row_value), "source": "batch row omp_wait_policy"}
    return {"value": UNRECORDED, "source": UNRECORDED}


def run_conditions(run: CaseRun, row_pool: str | None = None,
                   row_omp: str | None = None) -> dict[str, Any]:
    """``threads``, ``pool`` (conditions) and ``omp_wait_policy`` (record) of a run."""
    threads = (run.result.get("args") or {}).get("threads")
    if threads is None:
        threads = run.result.get("num_threads_chrono")
    return {"threads": threads, "pool": _pool(run, row_pool),
            "omp_wait_policy": omp_wait_policy(run, row_omp)}


def not_comparable_reasons(stored: dict[str, Any], rerun: dict[str, Any]) -> list[str]:
    """Why the hash comparison does not hold (empty = comparable; revision 12a 1).

    ``omp_wait_policy`` is not a condition (revision 12a 3).
    """
    reasons = [f"{key}: stored {stored[key]!r}, rerun {rerun[key]!r}"
               for key in ("threads", "pool") if stored[key] != rerun[key]]
    if stored["pool"] != P_CORE_POOL:  # equal pools off P cores are not comparable either
        reasons.append(f"stored pool {stored['pool']!r} (not P cores)")
    return reasons


def load_commands(run: CaseRun, kind: RowKind) -> tuple[np.ndarray, np.ndarray]:
    """(control instants, issued commands) of a run."""
    source = COMMAND_SOURCES[kind]
    with np.load(run.folder / source.file_name, allow_pickle=False) as data:
        return np.asarray(data[source.time_key]), np.asarray(data[source.command_key])


def _row_bytes(commands: np.ndarray) -> np.ndarray:
    rows = np.ascontiguousarray(commands.reshape(len(commands), -1))
    return rows.view(np.uint8).reshape(len(commands), -1)


def first_differing_period(stored: np.ndarray, rerun: np.ndarray) -> int | None:
    """First control period index whose command rows differ bit for bit (None = identical)."""
    if stored.dtype != rerun.dtype or stored.shape[1:] != rerun.shape[1:]:
        return 0
    common = min(len(stored), len(rerun))
    same = np.all(_row_bytes(stored[:common]) == _row_bytes(rerun[:common]), axis=1)
    if not same.all():
        return int(np.argmin(same))
    return None if len(stored) == len(rerun) else common


def load_events(run: CaseRun) -> list[tuple[float, str]]:
    """(time, name) of the controller events (``controller_events.json`` or ``result.json``)."""
    if (run.folder / "controller_events.json").is_file():
        return p3_check.controller_events(run.folder)
    return [(float(event["t_s"]), str(event["name"])) for event in run.result.get("events", [])]


def _first_event_difference(stored: list, rerun: list) -> dict[str, Any] | None:
    for index, (stored_event, rerun_event) in enumerate(zip(stored, rerun, strict=False)):
        if stored_event != rerun_event:
            return {"index": index, "stored": stored_event, "rerun": rerun_event}
    if len(stored) == len(rerun):
        return None
    index = min(len(stored), len(rerun))
    return {"index": index, "stored": stored[index] if index < len(stored) else None,
            "rerun": rerun[index] if index < len(rerun) else None}


def _period_window(times: np.ndarray, index: int) -> tuple[float, float]:
    """(start, end] of the control period ending at sample ``index``."""
    end = float(times[index])
    start = float(times[index - 1]) if index > 0 else end - CONTROL_PERIOD_S
    return start + EVENT_TIME_TOL_S, end + EVENT_TIME_TOL_S


def _events_in(events: list, window: tuple[float, float]) -> list[tuple[float, str]]:
    return [event for event in events if window[0] < event[0] <= window[1]]


def _named_events(events: list, prefix: str) -> list[tuple[float, str]]:
    return [event for event in events if event[1].startswith(prefix)][:MAX_LISTED_EVENTS]


def _period_time(times: np.ndarray, index: int) -> float | None:
    return float(times[index]) if index < len(times) else None


def difference_record(index: int, times: dict[str, np.ndarray],
                      events: dict[str, list]) -> dict[str, Any]:
    """First differing period: index, times and the events of that period (both runs)."""
    longer = times["rerun"] if len(times["rerun"]) > index else times["stored"]
    record = {"index": index,
              "t_s": {side: _period_time(t, index) for side, t in times.items()}}
    if index < len(longer):
        window = _period_window(longer, index)
        record["period_window_s"] = list(window)
        record["events_in_period"] = {side: _events_in(items, window)
                                      for side, items in events.items()}
    return record


def _meta_path_category(path: str) -> str | None:
    parts = path.split(".")
    if CONTROLLER_TAG_KEY in parts:
        return CONTROLLER_TAG_KEY
    if LAS_META_BLOCK in parts:
        return LAS_META_BLOCK
    if p3_check.is_p3_path(path):
        return "p3"
    return None


def meta_check(stored: CaseRun, rerun: CaseRun, rerun_events: list,
               is_silent: bool) -> dict[str, Any]:
    """Check 3: differing meta paths split into allowed and other (revision 12 2.2)."""
    paths = []
    for block in META_BLOCKS:
        paths += p3_check.differing_paths(stored.result.get(block), rerun.result.get(block),
                                          block)
    allowed: dict[str, list[str]] = {}
    other = []
    for path in paths:
        category = _meta_path_category(path)
        if category is not None:
            allowed.setdefault(category, []).append(path)
        elif path != FALLBACK_ESTIMATE_PATH:
            other.append(path)
    fallback = None
    if FALLBACK_ESTIMATE_PATH in paths:
        fallback = p3_check.fallback_estimate_conditions(
            stored.result.get("controller_meta") or {}, rerun.result.get("controller_meta") or {},
            rerun_events, is_silent, is_silent)
        if not fallback["all"]:
            other.append(FALLBACK_ESTIMATE_PATH)
    return {"applies": is_silent, "allowed_paths": allowed, "other_paths": other,
            "revision10_fallback_estimate": fallback,
            "only_allowed": None if not is_silent else not other}


def compare_runs(stored: CaseRun, rerun: CaseRun, kind: RowKind) -> dict[str, Any]:
    """Checks 1-3 of a comparable row."""
    stored_times, stored_commands = load_commands(stored, kind)
    rerun_times, rerun_commands = load_commands(rerun, kind)
    first_period = first_differing_period(stored_commands, rerun_commands)
    events = {"stored": load_events(stored), "rerun": load_events(rerun)}
    event_difference = _first_event_difference(events["stored"], events["rerun"])
    is_silent = first_period is None and event_difference is None
    record: dict[str, Any] = {
        "status": RowStatus.SILENT_CONFIRMED if is_silent else RowStatus.DIFFERS,
        "check1_commands_bit_identical": first_period is None,
        "check2_events_equal": event_difference is None,
        "command_shape": {"stored": list(stored_commands.shape),
                          "rerun": list(rerun_commands.shape)},
        "times_bit_identical": (stored_times.dtype == rerun_times.dtype
                                and np.array_equal(stored_times, rerun_times)),
        "event_count": {side: len(items) for side, items in events.items()},
        "first_event_difference": event_difference,
        "check3_meta": meta_check(stored, rerun, events["rerun"], is_silent)}
    if first_period is not None:
        record["first_difference"] = difference_record(
            first_period, {"stored": stored_times, "rerun": rerun_times}, events)
    if not is_silent:
        record["rerun_liftoff_slow_events"] = _named_events(events["rerun"],
                                                            LIFTOFF_SLOW_EVENT_PREFIX)
        record["rerun_fallback_events"] = _named_events(events["rerun"],
                                                        p3_check.FALLBACK_EVENT)
    return record


def _plant_keys(kind: RowKind) -> tuple[str, ...]:
    """Time, core and auxiliary keys in comparison order."""
    return (PLANT_SOURCES[kind].time_key, *CORE_PLANT_ARRAYS[kind], *AUX_PLANT_ARRAYS[kind])


def load_plant_series(run: CaseRun, kind: RowKind) -> dict[str, np.ndarray] | None:
    """The plant keys present in a run's plant file (None = the file is absent)."""
    path = run.folder / PLANT_SOURCES[kind].file_name
    if not path.is_file():
        return None
    with np.load(path, allow_pickle=False) as data:
        return {key: np.asarray(data[key]) for key in _plant_keys(kind) if key in data.files}


def _absent_core(series: dict[str, dict[str, np.ndarray] | None], kind: RowKind) -> list[str]:
    """``<side>:<name>`` of the absent plant file, time or core arrays."""
    core_keys = (PLANT_SOURCES[kind].time_key, *CORE_PLANT_ARRAYS[kind])
    absent = []
    for side, arrays in series.items():
        if arrays is None:
            absent.append(f"{side}:{PLANT_SOURCES[kind].file_name}")
            continue
        absent += [f"{side}:{key}" for key in core_keys if key not in arrays]
    return absent


def _split_auxiliary(series: dict[str, dict[str, np.ndarray]],
                     kind: RowKind) -> tuple[list[str], list[str]]:
    """(auxiliary arrays absent on both sides, ``<name> (<side without it>)`` of one side)."""
    excluded, one_side = [], []
    for key in AUX_PLANT_ARRAYS[kind]:
        sides_without = [side for side, arrays in series.items() if key not in arrays]
        if len(sides_without) == len(series):
            excluded.append(key)
        elif sides_without:
            one_side.append(f"{key} ({sides_without[0]})")
    return excluded, one_side


def _sample_time(times: dict[str, np.ndarray], index: int) -> float:
    """Earliest time of sample ``index`` over the sides that have it."""
    return min(float(side_times[index]) for side_times in times.values()
               if index < len(side_times))


def first_plant_difference(stored: dict[str, np.ndarray], rerun: dict[str, np.ndarray],
                           time_key: str) -> tuple[float, str | None]:
    """(t_p, first differing array name); (+inf, None) when all arrays are identical.

    Arrays are compared byte for byte per sample (time array included); the array with the
    earliest differing sample wins, ties in key order.
    """
    first_index, first_array = None, None
    for key in stored:
        index = first_differing_period(stored[key], rerun[key])
        if index is not None and (first_index is None or index < first_index):
            first_index, first_array = index, key
    if first_index is None:
        return float("inf"), None
    times = {"stored": stored[time_key], "rerun": rerun[time_key]}
    return _sample_time(times, first_index), first_array


def command_divergence_time(comparison: dict[str, Any]) -> float:
    """t_c: rerun time of the first differing command period (+inf when commands equal)."""
    first = comparison.get("first_difference")
    if first is None:
        return float("inf")
    times = first["t_s"]
    return times["rerun"] if times["rerun"] is not None else times["stored"]


def plant_check(stored: CaseRun, rerun: CaseRun, kind: RowKind,
                t_c_s: float) -> dict[str, Any]:
    """Revision 12a 4 / 12b 2: does the plant diverge before the commands do?"""
    series = {"stored": load_plant_series(stored, kind),
              "rerun": load_plant_series(rerun, kind)}
    check: dict[str, Any] = {"t_p_s": None, "t_c_s": t_c_s, "first_array": None,
                             "plant_first": None, "excluded_arrays": []}
    absent_core = _absent_core(series, kind)
    if absent_core:
        return {**check, "missing": absent_core}
    present = {side: arrays for side, arrays in series.items() if arrays is not None}
    excluded, one_side = _split_auxiliary(present, kind)
    check["excluded_arrays"] = excluded
    if one_side:
        return {**check, "auxiliary_one_side": one_side}
    compared = {side: {key: value for key, value in arrays.items() if key not in excluded}
                for side, arrays in present.items()}
    t_p_s, first_array = first_plant_difference(compared["stored"], compared["rerun"],
                                                PLANT_SOURCES[kind].time_key)
    return {**check, "t_p_s": t_p_s, "first_array": first_array,
            "plant_first": t_p_s < t_c_s - PLANT_FIRST_TOL_S}


def plant_check_reasons(check: dict[str, Any]) -> list[str]:
    """``not_comparable`` reasons of a plant check (empty = comparison stands)."""
    if check.get("missing"):
        return [f"plant series missing: {', '.join(check['missing'])}"]
    if check.get("auxiliary_one_side"):
        return [f"auxiliary plant array on one side only: {item}"
                for item in check["auxiliary_one_side"]]
    if check["plant_first"]:
        return [f"plant diverged first (t_p={check['t_p_s']}, t_c={check['t_c_s']}, "
                f"array={check['first_array']})"]
    return []


def record_row(row: BatchRow, stored_map: dict[str, str], root: Path) -> dict[str, Any]:
    """The record of one rerun row (status and its details)."""
    stored_dir, stored_source = _stored_folder(row, stored_map, root)
    rerun_dir = _rerun_folder(row)
    record: dict[str, Any] = {"case": row.case, "kind": row.kind,
                              "batch_json": str(row.batch_json),
                              "rerun": None if rerun_dir is None else str(rerun_dir),
                              "stored": None if stored_dir is None else str(stored_dir),
                              "stored_source": stored_source}
    stored, stored_missing = _load_case_run(stored_dir, row.kind, "stored")
    rerun, rerun_missing = _load_case_run(rerun_dir, row.kind, "rerun")
    if stored is None or rerun is None:
        return {**record, "status": RowStatus.MISSING, "reasons": stored_missing + rerun_missing}
    conditions = {"stored": run_conditions(stored),
                  "rerun": run_conditions(rerun, row.fields.get("pool"),
                                          row.fields.get("omp_wait_policy"))}
    conditions["omp_equal"] = (conditions["stored"]["omp_wait_policy"]["value"]
                               == conditions["rerun"]["omp_wait_policy"]["value"])
    record["conditions"] = conditions
    reasons = not_comparable_reasons(conditions["stored"], conditions["rerun"])
    if reasons:
        return {**record, "status": RowStatus.NOT_COMPARABLE, "reasons": reasons}
    comparison = compare_runs(stored, rerun, row.kind)
    check = plant_check(stored, rerun, row.kind, command_divergence_time(comparison))
    record = {**record, **comparison, "plant_check": check}
    plant_reasons = plant_check_reasons(check)
    if plant_reasons:  # checks 1-3 stay recorded; only the status changes (revision 12a 4)
        return {**record, "status": RowStatus.NOT_COMPARABLE, "reasons": plant_reasons}
    return record


def summarize(rows: list[dict[str, Any]], expected_rows: int) -> dict[str, Any]:
    """Status counts, the input errors of the row set and the rows for a meta cause check.

    ``counts["plant_first"]`` lists the rows whose plant diverged first (revision 12a 4; the
    main session reports them).
    """
    counts: dict[str, Any] = {status.value: 0 for status in RowStatus}
    for row in rows:
        counts[row["status"]] += 1
    counts["plant_first"] = [row["case"] for row in rows
                             if row.get("plant_check", {}).get("plant_first")]
    errors = []
    if len(rows) != expected_rows:
        errors.append(f"{len(rows)} batch rows, expected {expected_rows}")
    compared = counts[RowStatus.SILENT_CONFIRMED] + counts[RowStatus.DIFFERS]
    if compared == 0:
        errors.append("no row compared (empty set)")
    meta_unexpected = [row["case"] for row in rows
                       if row.get("check3_meta", {}).get("only_allowed") is False]
    return {"status": "input_error" if errors else "ok", "errors": errors, "rows": len(rows),
            "expected_rows": expected_rows, "compared": compared, "counts": counts,
            "meta_unexpected_cases": meta_unexpected}


def build_report(batch_jsons: list[Path], stored_map_path: Path | None, expected_rows: int,
                 root: Path) -> dict[str, Any]:
    """The whole record (``summary`` holds the status).

    Raises:
        InputError: A batch file or the stored map unreadable.
    """
    stored_map = load_stored_map(stored_map_path)
    rows = [record_row(row, stored_map, root) for row in load_batch_rows(batch_jsons)]
    return {"rule": RULE, "not_a_judgement": True,
            "inputs": {"batch_json": [str(path) for path in batch_jsons],
                       "stored_map": None if stored_map_path is None else str(stored_map_path),
                       "root": str(root)},
            "summary": summarize(rows, expected_rows), "rows": rows}


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_json", help="record JSON to write")
    parser.add_argument("--batch-json", action="append", required=True,
                        help="rerun batch.json (repeat for more than one batch folder)")
    parser.add_argument("--stored-map", default=None,
                        help="JSON {case: stored case folder}; wins over row stored_result")
    parser.add_argument("--expect-rows", type=int, default=DEFAULT_EXPECTED_ROWS,
                        help=f"rerun row count (default {DEFAULT_EXPECTED_ROWS}, revision 12 2.1)")
    parser.add_argument("--root", default=str(ROOT),
                        help="folder that relative stored paths are read against")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = build_report([Path(path) for path in args.batch_json],
                              None if args.stored_map is None else Path(args.stored_map),
                              args.expect_rows, Path(args.root))
    except InputError as error:
        print(json.dumps({"status": "input_error", "errors": [str(error)]}))
        return 2
    Path(args.out_json).write_text(json.dumps(report, indent=1), encoding="utf-8")
    summary = report["summary"]
    print(json.dumps({**summary, "out": args.out_json}))
    return 2 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
