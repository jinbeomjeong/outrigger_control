"""③ rev 7 condition rows (``jp3_remedy_spec_v7.md`` 3.5, 6.1; spec 8 Y7-4).

The rev 7 judged set adds, on a judged plant (the VBM family, P1 supplement on), the
``carry_ext`` reads of the first PROBE stage after the event time on every leg that went
``locked_ext`` -> ``moving_ext`` in that stage (the H-7 reads of edition 6). Per line:

* ``condition_reads`` / ``condition_breach_reads``: those reads and the ones whose plant rod
  truth exceeds the used bound by more than 1 Pa (the jp3a breach of
  ``extend_start_bound.ExtendBoundCheck``: ``used - p_tr < -1 Pa``).
* On an old plant (no P1 supplement: VBL, VBJ, ...) the line is a record only: each breach is
  ``plant_seed_artifact`` when the release before it started at a seed that came from a moving
  retract opening (``stale_seed_release`` of the line, harness record key), ``seed_not_stale``
  when its seed was not stale, ``no_seed`` without a logged seed, ``seed_log_truncated`` after
  the last row of a capped log; without the record key the line is ``not_judgeable`` (a
  record line; it never changes a judged status).
* A declared head-only line (steady path; T4h meta ``head_only_declared``, else the line's, the
  addendum 4a-7 1.1 order; an undeclared line is an event-path line) has no ③ trace and no
  event: state ``head_only``, outside the judged set on every plant (user decision 2026-11-24).
  One that still carries a ``jp3_*`` condition array or an event time contradicts its
  declaration: ``setting_defect`` on a judged plant, ``not_judgeable`` on an old plant.

Status of a set of judged lines (spec 6.1 order: fail > setting_defect > not_judgeable >
pass): a judged line with a condition breach fails; an event-path judged line without the T4h
arrays or the event time, or a contradicting head-only line, is a ``setting_defect``; no
condition read on any judged line is ``not_judgeable`` (never a pass). ``summary.states``
counts every line state; ``head_only_lines`` the head-only lines per plant kind.

Usage (python-dev or dynamics-dev, checkout root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_rev7_condition.py --rows <run.jsonl>
      --out <report.json> [--t4h-dir <folder>]
The T4h records default to ``<rows stem>_t4h/``. The stdout's last line is JSON with
``status``, the counts and the report path.

======  ===================  ============================================================
exit    status               meaning
======  ===================  ============================================================
0       ``pass``             report written; judged lines with condition reads, no breach
1       ``fail``             report written; a judged condition read breached
1       ``setting_defect``   report written; a judged line misses its inputs
1       ``not_judgeable``    report written; no judged condition read (or no judged line)
2       ``input_error``      no report: missing rows file / T4h folder, an existing ``--out``
3       ``tool_error``       an unexpected failure
======  ===================  ============================================================
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from outrigger_sim.control.extend_start_bound import (  # noqa: E402
    BOUND_CHECK_TOLERANCE_PA,
    PERIOD_CLASS_CODES,
    PLANT_STATE_CODES,
    PeriodClass,
)

EXIT_PASS, EXIT_FINDING, EXIT_INPUT, EXIT_TOOL = 0, 1, 2, 3
PROBE_PHASE = "probe"
CARRY_EXT_CODE = PERIOD_CLASS_CODES[PeriodClass.CARRY_EXT]
LOCKED_EXT_CODE = PLANT_STATE_CODES["locked_ext"]
MOVING_EXT_CODE = PLANT_STATE_CODES["moving_ext"]
JUDGED_PLANT_KEY = "p1_patch"
"""A line whose ``hydraulic_options`` carry the P1 supplement is on a judged (VBM) plant."""
STALE_KEY = "stale_seed_release"
ARTIFACT, SEED_NOT_STALE, NO_SEED = "plant_seed_artifact", "seed_not_stale", "no_seed"
LOG_TRUNCATED = "seed_log_truncated"
"""A breach after the last row of a capped ``stale_seed_release`` log: class unknown."""
STATUS_ORDER = ("pass", "not_judgeable", "setting_defect", "fail")
"""Spec 6.1: fail > setting_defect > not_judgeable > pass."""
T4H_ARRAYS = ("t_s", "phase", "jp3_t_s", "jp3_class", "jp3_plant_state", "jp3_p_tr_Pa",
              "jp3_used_bound_Pa")
CONDITION_TRACE_ARRAYS = tuple(name for name in T4H_ARRAYS if name.startswith("jp3_"))
"""The ③ trace arrays a declared head-only line must not have."""
HEAD_ONLY_KEY = "head_only_declared"
HEAD_ONLY_STATE = "head_only"
"""A declared head-only (steady path) line: no ③ trace, no event, the condition does not apply
(``jp3_baseline_compare.is_head_only_line`` order without the harness rule)."""


class InputError(Exception):
    """No report can be written (exit 2)."""


@dataclass(frozen=True)
class ConditionRead:
    """One ``carry_ext`` read of the condition (gap = used bound - plant truth)."""

    t_s: float
    leg: int
    gap_Pa: float
    is_breach: bool
    t_transition_s: float
    """Time of the read at which the leg was first seen ``moving_ext`` after ``locked_ext``."""


def first_probe_window(t_s: np.ndarray, phases: np.ndarray,
                       t_event_s: float) -> tuple[float, float] | None:
    """``(t_first, t_last)`` of the first PROBE stretch whose reads start at or after the
    event time (None without one)."""
    is_probe = np.array([str(phase).lower() == PROBE_PHASE for phase in phases])
    after = np.flatnonzero(is_probe & (np.asarray(t_s, float) >= t_event_s))
    if not after.size:
        return None
    start = int(after[0])
    end = start
    while end + 1 < len(is_probe) and is_probe[end + 1]:
        end += 1
    return float(t_s[start]), float(t_s[end])


def condition_reads(arrays: dict, t_event_s: float) -> list[ConditionRead]:
    """The rev 7 condition reads of one T4h record (module docstring)."""
    window = first_probe_window(arrays["t_s"], arrays["phase"], t_event_s)
    if window is None:
        return []
    times = np.asarray(arrays["jp3_t_s"], float)
    inside = np.flatnonzero((times >= window[0] - 1e-9) & (times <= window[1] + 1e-9))
    if not inside.size:
        return []
    states = np.asarray(arrays["jp3_plant_state"])[inside]
    classes = np.asarray(arrays["jp3_class"])[inside]
    gaps = (np.asarray(arrays["jp3_used_bound_Pa"], float)[inside]
            - np.asarray(arrays["jp3_p_tr_Pa"], float)[inside])
    reads = []
    for leg in range(states.shape[1]):
        transitions = [k for k in range(1, len(inside))
                       if states[k - 1, leg] == LOCKED_EXT_CODE
                       and states[k, leg] == MOVING_EXT_CODE]
        if not transitions:
            continue
        t_transition = float(times[inside[transitions[0]]])
        for k in np.flatnonzero(classes[:, leg] == CARRY_EXT_CODE):
            gap = float(gaps[k, leg])
            reads.append(ConditionRead(t_s=float(times[inside[k]]), leg=leg, gap_Pa=gap,
                                       is_breach=bool(np.isfinite(gap)
                                                      and gap < -BOUND_CHECK_TOLERANCE_PA),
                                       t_transition_s=t_transition))
    return reads


def release_seed_class(stale_record: dict, leg: int, t_read_s: float,
                       t_window_start_s: float) -> str:
    """The seed class of the release before a condition read on an old plant: the last
    logged seeded release of the leg in ``(t_window_start - 0.1 s, t_read]``. A read after the
    last row of a truncated log (``log_truncated``) is :data:`LOG_TRUNCATED`, not
    :data:`NO_SEED`: its release may have been cut from the log."""
    columns = stale_record.get("log_columns") or []
    rows = [dict(zip(columns, row, strict=True)) for row in stale_record.get("log") or []]
    earlier = [row for row in rows if int(row["leg"]) == leg
               and t_window_start_s - 0.1 - 1e-9 < float(row["t_release_s"]) <= t_read_s + 1e-9]
    if stale_record.get("log_truncated"):
        last_logged_s = max((float(row["t_release_s"]) for row in rows), default=-np.inf)
        if t_read_s > last_logged_s:
            return LOG_TRUNCATED
    if not earlier:
        return NO_SEED
    return ARTIFACT if bool(earlier[-1]["seed_from_moving_open"]) else SEED_NOT_STALE


def is_judged_plant(line: dict) -> bool:
    return bool((line.get("hydraulic_options") or {}).get(JUDGED_PLANT_KEY))


def is_head_only_declared(line: dict, meta: dict | None) -> bool:
    """Addendum 4a-7 1.1 order: the T4h meta ``head_only_declared``, else the line's, else
    not declared (an undeclared line is an event-path line, the strict side)."""
    if meta is not None and meta.get(HEAD_ONLY_KEY) is not None:
        return bool(meta[HEAD_ONLY_KEY])
    if line.get(HEAD_ONLY_KEY) is not None:
        return bool(line[HEAD_ONLY_KEY])
    return False


def head_only_contradictions(line: dict, array_names: frozenset[str]) -> list[str]:
    """What a declared head-only line must not have: the ③ trace arrays, an event time."""
    found = sorted(name for name in CONDITION_TRACE_ARRAYS if name in array_names)
    if line.get("t_event_s") is not None:
        found.append("t_event_s")
    return found


def _head_only_entry(entry: dict, line: dict, array_names: frozenset[str]) -> dict:
    """A declared head-only (steady path) line: the condition does not apply (a record). With
    ③ arrays or an event time it contradicts its declaration: a setting defect on a judged
    plant (user decision 2026-11-24), not judgeable on an old plant."""
    contradictions = head_only_contradictions(line, array_names)
    if not contradictions:
        return {**entry, "state": HEAD_ONLY_STATE}
    state = "setting_defect" if entry["is_judged_plant"] else "not_judgeable"
    return {**entry, "state": state, "head_only_contradictions": contradictions}


def line_condition(line: dict, arrays: dict | None, meta: dict | None = None,
                   array_names: frozenset[str] = frozenset()) -> dict:
    """The condition entry of one result line (``arrays`` = its T4h condition arrays, None =
    missing; ``meta`` / ``array_names`` = the T4h meta and every array name, for the head-only
    declaration)."""
    entry = {"setting": line["job"]["setting"], "t4h_file": line.get("t4h_file"),
             "is_judged_plant": is_judged_plant(line),
             "head_only_declared": is_head_only_declared(line, meta)}
    if entry["head_only_declared"]:
        names = array_names | (frozenset(arrays) if arrays is not None else frozenset())
        return _head_only_entry(entry, line, names)
    t_event = line.get("t_event_s")
    if arrays is None or t_event is None:
        missing = [] if arrays is not None else ["t4h arrays"]
        missing += [] if t_event is not None else ["t_event_s"]
        return {**entry, "state": "setting_defect" if entry["is_judged_plant"]
                else "not_judgeable", "missing": missing}
    reads = condition_reads(arrays, float(t_event))
    entry.update(condition_reads=len(reads),
                 condition_breach_reads=sum(read.is_breach for read in reads),
                 reads=[asdict(read) for read in reads])
    if entry["is_judged_plant"]:
        entry["state"] = "fail" if entry["condition_breach_reads"] else "judged"
        return entry
    stale = (line.get("hydraulics_record") or {}).get(STALE_KEY)
    if stale is None:
        return {**entry, "state": "not_judgeable", "missing": [STALE_KEY]}
    window = first_probe_window(arrays["t_s"], arrays["phase"], float(t_event))
    classes = [release_seed_class(stale, read.leg, read.t_s, window[0]) for read in reads
               if read.is_breach]
    entry.update(state="record", breach_seed_classes={name: classes.count(name)
                                                      for name in (ARTIFACT, SEED_NOT_STALE,
                                                                   NO_SEED, LOG_TRUNCATED)})
    return entry


def summarize(entries: list[dict]) -> dict:
    """The rev 7 condition status of the judged lines (head-only and record lines are counted
    apart; a head-only line never enters the judged count)."""
    head_only = [entry for entry in entries if entry["state"] == HEAD_ONLY_STATE]
    judged = [entry for entry in entries
              if entry["is_judged_plant"] and entry["state"] != HEAD_ONLY_STATE]
    records = [entry for entry in entries
               if not entry["is_judged_plant"] and entry["state"] != HEAD_ONLY_STATE]
    status = "pass"
    if any(entry["state"] == "fail" for entry in judged):
        status = "fail"
    elif any(entry["state"] == "setting_defect" for entry in judged):
        status = "setting_defect"
    elif sum(entry.get("condition_reads", 0) for entry in judged) == 0:
        status = "not_judgeable"
    return {"status": status, "judged_lines": len(judged),
            "judged_lines_with_condition": sum(entry.get("condition_reads", 0) > 0
                                               for entry in judged),
            "judged_condition_reads": sum(entry.get("condition_reads", 0) for entry in judged),
            "judged_breach_reads": sum(entry.get("condition_breach_reads", 0)
                                       for entry in judged),
            "record_lines": len(records),
            "head_only_lines": {"judged_plant": sum(e["is_judged_plant"] for e in head_only),
                                "record_plant": sum(not e["is_judged_plant"]
                                                    for e in head_only)},
            "states": dict(sorted(Counter(entry["state"] for entry in entries).items())),
            "record_artifact_reads": sum((entry.get("breach_seed_classes") or {})
                                         .get(ARTIFACT, 0) for entry in entries)}


@dataclass(frozen=True)
class T4hRecord:
    """What the tool reads of one T4h npz: the condition arrays (None when one is missing),
    every array name and the meta (None without ``meta_json``)."""

    arrays: dict | None
    array_names: frozenset[str]
    meta: dict | None


def read_t4h(path: Path) -> T4hRecord | None:
    """The T4h record of a line (None when the file does not exist)."""
    if not path.is_file():
        return None
    with np.load(path, allow_pickle=False) as data:
        names = frozenset(data.files)
        meta = json.loads(str(data["meta_json"])) if "meta_json" in names else None
        arrays = (None if any(name not in names for name in T4H_ARRAYS)
                  else {name: np.array(data[name]) for name in T4H_ARRAYS})
    return T4hRecord(arrays, names, meta)


def read_arrays(path: Path) -> dict | None:
    record = read_t4h(path)
    return None if record is None else record.arrays


def build_report(rows_path: Path, t4h_dir: Path) -> dict:
    if not rows_path.is_file():
        raise InputError(f"--rows {rows_path} not found")
    if not t4h_dir.is_dir():
        raise InputError(f"T4h folder {t4h_dir} not found")
    entries = []
    with rows_path.open(encoding="utf-8") as handle:  # streamed: probe files are large
        for text in handle:
            if not text.strip():
                continue
            line = json.loads(text)
            if "error" in line:
                continue
            name = line.get("t4h_file")
            record = None if name is None else read_t4h(t4h_dir / name)
            if record is None:
                entries.append(line_condition(line, None))
            else:
                entries.append(line_condition(line, record.arrays, record.meta,
                                              record.array_names))
    return {"rule": "jp3_remedy_spec_v7.md 3.5 / 6.1 (③ rev 7 judged set)",
            "rows_file": str(rows_path), "t4h_dir": str(t4h_dir),
            "summary": summarize(entries), "lines": entries}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="report json (new file)")
    parser.add_argument("--t4h-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise InputError(f"--out {args.out} exists (a report is never overwritten)")
        rows = args.rows.resolve()
        t4h_dir = args.t4h_dir or rows.with_name(f"{rows.stem}_t4h")
        report = build_report(rows, t4h_dir)
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}), flush=True)
        return EXIT_INPUT
    except Exception:  # every unexpected failure is a tool error (exit 3)
        traceback.print_exc()
        print(json.dumps({"status": "tool_error"}), flush=True)
        return EXIT_TOOL
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    summary = report["summary"]
    print(json.dumps({"status": summary["status"], "judged_lines": summary["judged_lines"],
                      "judged_condition_reads": summary["judged_condition_reads"],
                      "record_lines": summary["record_lines"],
                      "head_only_lines": summary["head_only_lines"],
                      "states": summary["states"], "out": str(args.out)}),
          flush=True)
    return EXIT_PASS if summary["status"] == "pass" else EXIT_FINDING


if __name__ == "__main__":
    sys.exit(main())
