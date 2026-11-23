"""Census of ``WARN_PROBE_STIFFNESS_OUT_OF_RANGE`` (user decision 2026-11-24, a record).

Every line of three result files, from the line's T4h record (``meta_json`` ``events``: the
whole event list; the line's own ``events`` keeps only the first 200 WARN / FAULT names):

* ``probe``  ``j9_runs/1bd405c8/ed6_probe_a1/ed6_probe.jsonl`` (320 lines, every key)
* ``b1off``  ``ed6_design/probe_1bd405c8/b1off_check/ed6_probe_a1a2b3.jsonl`` (40 lines)
* ``j9main`` ``j9_runs/606f8713/j9main_a1/j9_main.jsonl`` (edition 5 VBJ / LSJ, 388 lines)

Only these named files and their ``<stem>_t4h`` folders are opened (no folder walk; the
blinded ``cdry_a1`` files are never read). Per warning: the read time, the phase of the last
T4h read at or before it, and the raw median stiffness ratio of the event text (the token
before the first ``:`` is the event name, ``c2.py``: ``WARN_PROBE_STIFFNESS_OUT_OF_RANGE:
{raw:.3f}``). Per line: the count, the first warning, and the line's other WARN / FAULT names
(first tokens), for the "sole condition" of the later J7 rule.

Writes ``stiffwarn_lines.csv`` (one row per line), ``stiffwarn_events.csv`` (one row per
warning) and ``stiffwarn_census.json`` (counts, input sha256) next to this file; an existing
output is refused. Exit 0 = written, 2 = input error (missing file, a line without its T4h,
existing output), 3 = tool error. The stdout's last line is JSON with ``status`` and counts.

Usage (python-dev):  python -I -B stiffwarn_census.py <project root>
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import traceback
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
EVENT = "WARN_PROBE_STIFFNESS_OUT_OF_RANGE"
SOURCES = {
    "probe": "06_analysis/02_control/j_p3_cause/j9_runs/1bd405c8/ed6_probe_a1/ed6_probe.jsonl",
    "b1off": "06_analysis/02_control/j_p3_cause/ed6_design/probe_1bd405c8/b1off_check/"
             "ed6_probe_a1a2b3.jsonl",
    "j9main": "06_analysis/02_control/j_p3_cause/j9_runs/606f8713/j9main_a1/j9_main.jsonl",
}
OUTPUTS = ("stiffwarn_lines.csv", "stiffwarn_events.csv", "stiffwarn_census.json")
EXIT_WRITTEN, EXIT_INPUT, EXIT_TOOL = 0, 2, 3
TIME_TOLERANCE_S = 1e-6


class InputError(Exception):
    """No output can be written (exit 2)."""


def key_of(job: dict) -> str:
    """``<row>_<phase>`` as ``run_v5.t4h_file_name`` without the setting."""
    row = "R2ra" if job.get("decision") == "reanchor_on" else job["case"]
    if job.get("twin"):
        twin = job["twin"]
        phase = f"{twin['level']}-{twin['leg']}-Fs{twin['fs_kN']:g}-o{job.get('offset_s')}"
    elif job.get("offset_s") is not None:
        phase = f"o{job['offset_s']}"
    else:
        phase = f"e{job.get('eps', 0.0)}"
    return f"{row}_{phase}"


def plant_arm(setting: str) -> tuple[str, str]:
    """Probe settings ``P6-<plant>-<arm>``; other settings have neither."""
    parts = setting.split("-")
    if len(parts) == 3 and parts[0] == "P6":
        return parts[1], parts[2]
    return "", ""


def phase_at(times: np.ndarray, phases: list[str], t_s: float) -> str:
    index = int(np.searchsorted(times, t_s + TIME_TOLERANCE_S, side="right")) - 1
    return phases[index] if index >= 0 else ""


def census_of(source: str, path: Path) -> tuple[list[dict], list[dict]]:
    t4h_dir = path.with_name(f"{path.stem}_t4h")
    lines, events = [], []
    for text in path.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        record = json.loads(text)
        job = record["job"]
        setting = job["setting"]
        plant, arm = plant_arm(setting)
        base = {"source": source, "setting": setting, "plant": plant, "arm": arm,
                "key": key_of(job)}
        if "error" in record:
            lines.append({**base, "error": True})
            continue
        t4h_path = t4h_dir / record.get("t4h_file", "")
        if not record.get("t4h_file") or not t4h_path.is_file():
            raise InputError(f"{source}: no T4h for {base}")
        with np.load(t4h_path, allow_pickle=False) as data:
            meta = json.loads(str(data["meta_json"]))
            times = np.asarray(data["t_s"], float)
            phases = [str(value).lower() for value in data["phase"]]
        all_events = [(float(t), str(name)) for t, name in meta["events"]]
        own = [(t, name) for t, name in all_events if name.split(":", 1)[0] == EVENT]
        other = sorted({name.split(":", 1)[0] for _, name in all_events
                        if name.startswith(("WARN", "FAULT")) and
                        name.split(":", 1)[0] != EVENT})
        for t_s, name in own:
            raw_text = name.split(":", 1)[1] if ":" in name else ""
            events.append({**base, "t_s": round(t_s, 3), "phase": phase_at(times, phases, t_s),
                           "raw_ratio": float(raw_text) if raw_text else None})
        lines.append({**base, "error": False, "warnings": len(own),
                      "first_t_s": round(own[0][0], 3) if own else None,
                      "first_raw_ratio": (events[-len(own)]["raw_ratio"] if own else None),
                      "other_warn_fault_names": " ".join(other)})
    return lines, events


def write_csv(path: Path, rows: list[dict]) -> None:
    columns: list[str] = []
    for row in rows:
        columns += [name for name in row if name not in columns]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def counts(lines: list[dict], events: list[dict]) -> dict:
    out: dict = {}
    for source in SOURCES:
        own_lines = [line for line in lines if line["source"] == source]
        own_events = [event for event in events if event["source"] == source]
        out[source] = {
            "lines": len(own_lines), "error_lines": sum(line["error"] for line in own_lines),
            "lines_with_warning": sum(bool(line.get("warnings")) for line in own_lines),
            "warnings": len(own_events),
            "warning_lines_by_setting": dict(Counter(line["setting"] for line in own_lines
                                                     if line.get("warnings"))),
            "warning_lines_by_key": dict(Counter(line["key"] for line in own_lines
                                                 if line.get("warnings"))),
            "warnings_by_phase": dict(Counter(event["phase"] for event in own_events)),
            "sole_warning_lines": sum(bool(line.get("warnings"))
                                      and not line.get("other_warn_fault_names")
                                      for line in own_lines)}
        if any(line["arm"] for line in own_lines):
            out[source]["warning_lines_by_arm"] = dict(Counter(
                line["arm"] for line in own_lines if line.get("warnings")))
            out[source]["warning_lines_by_plant"] = dict(Counter(
                line["plant"] for line in own_lines if line.get("warnings")))
    return out


def main(argv: list[str]) -> int:
    try:
        if len(argv) != 2:
            raise InputError("one argument: the project root")
        root = Path(argv[1])
        if any((HERE / name).exists() for name in OUTPUTS):
            raise InputError("an output exists (never overwritten)")
        inputs, lines, events = {}, [], []
        for source, relative in SOURCES.items():
            path = root / relative
            if not path.is_file():
                raise InputError(f"{path} not found")
            inputs[source] = {"path": relative,
                              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            source_lines, source_events = census_of(source, path)
            lines += source_lines
            events += source_events
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}))
        return EXIT_INPUT
    except Exception:  # every unexpected failure is a tool error (exit 3)
        traceback.print_exc()
        print(json.dumps({"status": "tool_error"}))
        return EXIT_TOOL
    report = {"event": EVENT, "rule": "the whole T4h event list of every line; phase = the "
              "last T4h read at or before the event", "inputs": inputs,
              "counts": counts(lines, events)}
    write_csv(HERE / "stiffwarn_lines.csv", lines)
    write_csv(HERE / "stiffwarn_events.csv", events)
    (HERE / "stiffwarn_census.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"status": "written", "lines": len(lines), "warnings": len(events)}))
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main(sys.argv))
