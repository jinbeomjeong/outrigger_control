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

Status of a set of judged lines (spec 6.1 order: fail > setting_defect > not_judgeable >
pass): a judged line with a condition breach fails; a judged line without the T4h arrays or the
event time is a ``setting_defect``; no condition read on any judged line is ``not_judgeable``
(never a pass).

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


def line_condition(line: dict, arrays: dict | None) -> dict:
    """The condition entry of one result line (``arrays`` = its T4h arrays, None = missing)."""
    entry = {"setting": line["job"]["setting"], "t4h_file": line.get("t4h_file"),
             "is_judged_plant": is_judged_plant(line)}
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
    """The rev 7 condition status of the judged lines (record lines are counted apart)."""
    judged = [entry for entry in entries if entry["is_judged_plant"]]
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
            "record_lines": len(entries) - len(judged),
            "record_artifact_reads": sum((entry.get("breach_seed_classes") or {})
                                         .get(ARTIFACT, 0) for entry in entries)}


def read_arrays(path: Path) -> dict | None:
    if not path.is_file():
        return None
    with np.load(path, allow_pickle=False) as data:
        if any(name not in data.files for name in T4H_ARRAYS):
            return None
        return {name: np.array(data[name]) for name in T4H_ARRAYS}


def build_report(rows_path: Path, t4h_dir: Path) -> dict:
    if not rows_path.is_file():
        raise InputError(f"--rows {rows_path} not found")
    if not t4h_dir.is_dir():
        raise InputError(f"T4h folder {t4h_dir} not found")
    lines = [json.loads(text) for text in rows_path.read_text(encoding="utf-8").splitlines()
             if text.strip()]
    entries = []
    for line in lines:
        if "error" in line:
            continue
        name = line.get("t4h_file")
        arrays = None if name is None else read_arrays(t4h_dir / name)
        entries.append(line_condition(line, arrays))
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
                      "record_lines": summary["record_lines"], "out": str(args.out)}),
          flush=True)
    return EXIT_PASS if summary["status"] == "pass" else EXIT_FINDING


if __name__ == "__main__":
    sys.exit(main())
