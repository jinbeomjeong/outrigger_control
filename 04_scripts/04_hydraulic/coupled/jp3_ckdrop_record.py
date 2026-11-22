"""436.9 edition 5 erratum 2 2-9.5: the record of the T-CK and DROPOUT bundles (spec v5 6.4; a
record, no judgement, no status other than written / not computed).

Per line (case x leg x arm) of every run given:
* T-CK: ``zero_calibration.legs[*].status``, the latch time (``rod_fault.latched.t_s``), the
  FAULT events (names of the T4h ``meta_json`` events) and the first READY
  (``base.t_ready_s``, else ``base.t_ready``);
* DROPOUT: the count of ``FAULT_HEAD_PRESSURE`` events (T4h meta events), the latch record;
  the D1' / D1'' undecided period count has no record key in the run lines or the T4h
  records: written as not computed with that reason.
A missing run, line or T4h record is written as not computed for that line.

Usage (python-dev or Chrono-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_ckdrop_record.py --out <record.json>
      --run tck:FL:VBK0=<run json> --t4h tck:FL:VBK0=<T4h folder> ... (16 runs)
Exit 0 written, 2 a malformed argument or an existing ``--out``, 3 a tool error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

BUNDLES = ("tck", "dropout")
LEGS = ("FL", "FR", "RL", "RR")
ARMS = ("VBK0", "VBK")
FAULT_PREFIX = "FAULT"
HEAD_PRESSURE_FAULT = "FAULT_HEAD_PRESSURE"
D1_UNDECIDED_REASON = ("no record key: the run lines and T4h records hold no D1' / D1'' "
                       "undecided period count")
EXIT_WRITTEN, EXIT_INPUT, EXIT_ERROR = 0, 2, 3


def parse_ids(values: list[str], option: str) -> dict[tuple[str, str, str], Path]:
    out = {}
    for value in values:
        name, separator, path = value.partition("=")
        parts = tuple(name.split(":"))
        if (not separator or len(parts) != 3 or parts[0] not in BUNDLES or parts[1] not in LEGS
                or parts[2] not in ARMS or parts in out):
            raise ValueError(f"{option} {value!r}: <tck|dropout>:<leg>:<VBK0|VBK>=<path>")
        out[parts] = Path(path)
    return out


def _events(row: dict, folder: Path | None) -> list | None:
    name = row.get("t4h_file")
    if folder is None or not name or not (folder / Path(str(name)).name).is_file():
        return None
    with np.load(folder / Path(str(name)).name, allow_pickle=False) as data:
        return json.loads(str(data["meta_json"])).get("events")


def line_record(bundle: str, row: dict, folder: Path | None) -> dict:
    fault = row.get("rod_fault") or {}
    base = row.get("base") or {}
    events = _events(row, folder)
    out = {"key": row.get("key"), "fault_id": fault.get("fault_id"),
           "latched": fault.get("latched"), "first_applied_t_s": fault.get("first_applied_t_s"),
           "t_ready_s": base.get("t_ready_s", base.get("t_ready"))}
    if events is None:
        out["events"] = {"computed": False, "reason": "no T4h record of the line"}
    else:
        names = [str(event[1]) for event in events]
        out["fault_events"] = sorted({name for name in names if name.startswith(FAULT_PREFIX)})
    if bundle == "tck":
        legs = ((row.get("zero_calibration") or {}).get("legs")) or {}
        out["zero_calibration_status"] = {leg: (legs.get(leg) or {}).get("status")
                                          for leg in LEGS}
    else:
        if events is not None:
            out["fault_head_pressure_count"] = sum(
                str(event[1]).startswith(HEAD_PRESSURE_FAULT) for event in events)
        out["d1_undecided_periods"] = {"computed": False, "reason": D1_UNDECIDED_REASON}
    return out


def record(runs: dict, t4h: dict) -> dict:
    lines = []
    for ident, path in sorted(runs.items()):
        bundle, leg, arm = ident
        where = {"bundle": bundle, "fault_leg": leg, "arm": arm, "run": str(path)}
        if not path.is_file():
            lines.append({**where, "computed": False, "reason": "run file missing"})
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        rows = document["results"] if isinstance(document, dict) else document
        if not rows:
            lines.append({**where, "computed": False, "reason": "no line"})
        for row in rows:
            lines.append({**where, **line_record(bundle, row, t4h.get(ident))})
    expected = len(BUNDLES) * len(LEGS) * len(ARMS)
    return {"rule": "jp3_remedy_spec_v5_erratum2.md 2-9.5 (spec v5 6.4, a record)",
            "status": "written", "runs": len(runs), "runs_expected": expected,
            "lines": lines}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", action="append", required=True)
    parser.add_argument("--t4h", action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        print(json.dumps({"status": "not_computed", "reason": "--out exists"}))
        return EXIT_INPUT
    try:
        runs, t4h = parse_ids(args.run, "--run"), parse_ids(args.t4h, "--t4h")
    except ValueError as exc:
        print(f"input error: {exc}", file=sys.stderr)
        print(json.dumps({"status": "not_computed"}))
        return EXIT_INPUT
    try:
        report = record(runs, t4h)
    except Exception as exc:  # noqa: BLE001 (every other failure is a tool error)
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({"status": "error"}))
        return EXIT_ERROR
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1, default=str)
    print(json.dumps({"status": "written", "lines": len(report["lines"]), "out": str(args.out)}))
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main())
