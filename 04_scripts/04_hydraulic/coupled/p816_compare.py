"""436.9 edition 8 P8-16: the implementation arms against the P8-14 review arms.

``jp3_remedy_spec_v8_rules.md`` 12 P8-16 (judgement, gate): the reference is one file, the
P8-14 ``raw/runs.jsonl`` (sha256 :data:`REFERENCE_SHA256`); its B and L2 lines (27 keys each:
23 VBM-family run_v5 rows and 4 edition 5 r79 rows) give the table (arm, key,
``commands_sha256``). The run is an ``ed8_probe.py --part p816 --arms B_impl,L2_impl`` output:
``B_impl`` answers B, ``L2_impl`` answers L2. Every one of the 54 keys must have exactly one run
line without error and with ``commands_sha256`` (completeness 27/27, 27/27); a missing, error,
hash-less or duplicated line fails, and so does a run line of these arms outside the table.
All 54 equal = pass; any difference = fail ("implementation defect": every reference is a run).

======  ==============================================================================
exit    meaning
======  ==============================================================================
0       pass: 54 of 54 keys present once and equal
1       fail: a difference, a missing / error / hash-less / duplicated line, or an extra
        line of the two arms
2       input error: a missing or unreadable file, a reference with another sha256 or
        another B / L2 table than 27 + 27 keys, an existing ``--out``
3       tool error (any unexpected failure)
======  ==============================================================================

The report (``--out``, a new path) has the status, the counts per arm and one entry per key
(reference and run hash, state). The stdout's last line is JSON with ``status``, the counts
and the report path.

Usage (any Python 3.10+; paths absolute or relative to the current folder):
  python -I -B p816_compare.py --reference <P8-14 raw/runs.jsonl> --run <ed8_probe jsonl>
      --out <report.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from collections import Counter
from pathlib import Path

EXIT_PASS, EXIT_FAIL, EXIT_INPUT, EXIT_TOOL = 0, 1, 2, 3
REFERENCE_SHA256 = "89efe66fc521f6d58c8c90304a9258747eef45d422ef43666a53f5ddd7fa9418"
"""The P8-14 ``control_level_deadlock/probe_8a2a52ce/raw/runs.jsonl`` (spec v8 header)."""
ARM_OF_REFERENCE = {"B": "B_impl", "L2": "L2_impl"}
"""P8-14 arm -> the ed8_probe implementation arm."""
PLANT_OF_REFERENCE = {"VBM": "M", "LSM4": "LSM4", "VBMslow": "Mslow", "VBKM0": "KM0"}
"""P8-14 plant (the key's edition 7 setting) -> the ed8_probe plant."""
KEYS_PER_ARM = 27
RUNTIME_JOB_KEYS = ("mask", "t4h_dir", "setting", "_part", "_r79_plan")
"""Job entries that are not part of the row identity."""
PROBE_BLOCK = "ed8_probe"


class InputError(ValueError):
    """An input the comparison cannot use (exit 2)."""


def _read_lines(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"{path}: {exc}") from exc
    try:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    except ValueError as exc:
        raise InputError(f"{path}: not JSON lines ({exc})") from exc


def row_identity(job: dict) -> str:
    """The row of a job without its setting and runtime entries (sorted JSON)."""
    row = {key: value for key, value in job.items() if key not in RUNTIME_JOB_KEYS}
    return json.dumps(row, sort_keys=True)


def reference_table(path: Path) -> dict[tuple[str, str, str], str]:
    """``(implementation arm, plant, row) -> commands_sha256`` of the reference B / L2 lines.

    Raises:
        InputError: Another sha256, an error or hash-less B / L2 line, a duplicated key, or
            not 27 keys per arm.
    """
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise InputError(f"--reference {path}: {exc}") from exc
    if digest != REFERENCE_SHA256:
        raise InputError(f"--reference {path}: sha256 {digest} is not {REFERENCE_SHA256}")
    table: dict[tuple[str, str, str], str] = {}
    for line in _read_lines(path):
        job = line.get("p814_job") or {}
        prefix, arm, plant = ((job.get("setting") or "").split("-") + ["", "", ""])[:3]
        if prefix != "P814" or arm not in ARM_OF_REFERENCE:
            continue
        if "error" in line or not line.get("commands_sha256"):
            raise InputError(f"reference line {job} has no command hash")
        key = (ARM_OF_REFERENCE[arm], PLANT_OF_REFERENCE[plant], row_identity(job))
        if key in table:
            raise InputError(f"reference key {key} twice")
        table[key] = line["commands_sha256"]
    per_arm = Counter(arm for arm, _, _ in table)
    if any(per_arm[arm] != KEYS_PER_ARM for arm in ARM_OF_REFERENCE.values()):
        raise InputError(f"reference table {dict(per_arm)}, {KEYS_PER_ARM} keys per arm expected")
    return table


def run_lines(path: Path) -> dict[tuple[str, str, str], list[dict]]:
    """The run lines of the implementation arms by ``(arm, plant, row)``."""
    lines: dict[tuple[str, str, str], list[dict]] = {}
    for line in _read_lines(path):
        block = line.get(PROBE_BLOCK) or {}
        if block.get("arm") not in ARM_OF_REFERENCE.values():
            continue
        key = (block["arm"], block.get("plant"), row_identity(line.get("job") or {}))
        lines.setdefault(key, []).append(line)
    return lines


def _state_of(expected: str, found: list[dict]) -> tuple[str, str | None]:
    """``(state, run hash)`` of one reference key."""
    if not found:
        return "missing", None
    if len(found) > 1:
        return "duplicated", None
    line = found[0]
    if "error" in line:
        return "error", None
    run_hash = line.get("commands_sha256")
    if not run_hash:
        return "no_hash", None
    return ("equal" if run_hash == expected else "differ"), run_hash


def compare(reference: dict[tuple[str, str, str], str],
            lines: dict[tuple[str, str, str], list[dict]]) -> dict:
    """The P8-16 report: one entry per reference key, the counts, the extra run keys and the
    status (pass only with every key ``equal`` and no extra key)."""
    entries = []
    counts: dict[str, Counter] = {arm: Counter() for arm in ARM_OF_REFERENCE.values()}
    for (arm, plant, row), expected in sorted(reference.items()):
        state, run_hash = _state_of(expected, lines.get((arm, plant, row), []))
        counts[arm][state] += 1
        entries.append({"arm": arm, "plant": plant, "row": json.loads(row), "state": state,
                        "reference_sha256": expected, "run_sha256": run_hash})
    extra = sorted(set(lines) - set(reference))
    is_pass = not extra and all(entry["state"] == "equal" for entry in entries)
    return {"status": "pass" if is_pass else "fail",
            "counts": {arm: dict(counter) for arm, counter in counts.items()},
            "equal": sum(entry["state"] == "equal" for entry in entries),
            "keys": len(entries),
            "extra_run_keys": [{"arm": arm, "plant": plant, "row": json.loads(row)}
                               for arm, plant, row in extra],
            "entries": entries}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reference", type=Path, required=True,
                        help="the P8-14 raw/runs.jsonl")
    parser.add_argument("--run", type=Path, required=True, help="the ed8_probe p816 output")
    parser.add_argument("--out", type=Path, required=True, help="report JSON (a new path)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    out = args.out.resolve()
    try:
        if out.exists():
            raise InputError(f"--out {out} exists: use a new path")
        reference = reference_table(args.reference.resolve())
        lines = run_lines(args.run.resolve())
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}), flush=True)
        return EXIT_INPUT
    try:
        report = compare(reference, lines)
        report.update(reference=str(args.reference.resolve()), run=str(args.run.resolve()),
                      reference_sha256=REFERENCE_SHA256,
                      run_sha256=hashlib.sha256(args.run.resolve().read_bytes()).hexdigest())
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    except Exception:  # every unexpected failure is a tool error (exit 3), never a result
        traceback.print_exc()
        print(json.dumps({"status": "tool_error", "out": str(out)}), flush=True)
        return EXIT_TOOL
    print(json.dumps({"status": report["status"], "equal": report["equal"],
                      "keys": report["keys"], "counts": report["counts"],
                      "extra_run_keys": len(report["extra_run_keys"]), "out": str(out)}),
          flush=True)
    return EXIT_PASS if report["status"] == "pass" else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
