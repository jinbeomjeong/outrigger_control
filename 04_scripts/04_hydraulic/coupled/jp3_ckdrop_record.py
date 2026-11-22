"""436.9 edition 5 erratum 2 2-9.5: the record of the T-CK and DROPOUT bundles (spec v5 6.4; a
record, no judgement, no status other than written / not computed).

Per line (case x leg x arm) of every run given:
* T-CK: ``zero_calibration.legs[*].status``, the latch time (``rod_fault.latched.t_s``), the
  FAULT events (names of the T4h ``meta_json`` events) and the first READY
  (``base.t_ready_s``, else ``base.t_ready``); per (case key, seed, fault leg) the VBK line
  against the VBK0 line (``tck_pairs``): the new (name, leg) FAULT pairs and ``PHASE_FAULT``
  on VBK only, both READY times and their difference, "VBK0 reached, VBK not";
* DROPOUT: the count of ``FAULT_HEAD_PRESSURE`` events (T4h meta events), the latch record;
  the D1' / D1'' undecided period count is not computed ("기록 키 없음: 시뮬레이션 경로 변경
  필요").
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

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import jp3_12b_judge as judge  # noqa: E402

BUNDLES = ("tck", "dropout")
LEGS = ("FL", "FR", "RL", "RR")
ARMS = ("VBK0", "VBK")
FAULT_PREFIX = "FAULT"
HEAD_PRESSURE_FAULT = "FAULT_HEAD_PRESSURE"
D1_UNDECIDED_REASON = "기록 키 없음: 시뮬레이션 경로 변경 필요"
"""Erratum 2 final: the D1' / D1'' undecided period count stays not computed (no record key in
the run lines or the T4h records; adding one changes the simulation path)."""
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


def _t4h(row: dict, folder: Path | None) -> tuple[list | None, list | None]:
    """(meta events, ``phase`` array) of the line's T4h record (None: not found / no array)."""
    name = row.get("t4h_file")
    if folder is None or not name or not (folder / Path(str(name)).name).is_file():
        return None, None
    with np.load(folder / Path(str(name)).name, allow_pickle=False) as data:
        events = json.loads(str(data["meta_json"])).get("events")
        phase = [str(value) for value in data["phase"]] if "phase" in data.files else None
    return events, phase


def _events(row: dict, folder: Path | None) -> list | None:
    return _t4h(row, folder)[0]


def _ready(row: dict) -> float | None:
    base = row.get("base") or {}
    return base.get("t_ready_s", base.get("t_ready"))


def tck_pairs(lines_by_id: dict, t4h: dict) -> list[dict]:
    """Erratum 2 final (2-9.5): per (case key, seed, fault leg) the VBK line against the VBK0
    line - the (name, leg) FAULT pairs and the ``PHASE_FAULT`` entry on VBK only
    (``jp3_12b_judge.fault_pairs`` / ``phase_fault_pairs``), both first READY times and their
    difference, "VBK0 reached, VBK not". A record, no threshold."""
    out = []
    for leg in LEGS:
        rows0 = {row.get("key"): row for row in lines_by_id.get(("tck", leg, "VBK0"), [])}
        rows1 = {row.get("key"): row for row in lines_by_id.get(("tck", leg, "VBK"), [])}
        for key in sorted(set(rows0) | set(rows1), key=str):
            pair = {"key": key, "fault_leg": leg}
            if key not in rows0 or key not in rows1:
                out.append({**pair, "computed": False, "reason": "the pair has one arm only"})
                continue
            sides = {}
            for arm, row in (("VBK0", rows0[key]), ("VBK", rows1[key])):
                events, phase = _t4h(row, t4h.get(("tck", leg, arm)))
                sides[arm] = None if events is None else (
                    judge.fault_pairs(events) | (judge.phase_fault_pairs(phase)
                                                 if phase is not None else set()))
            ready0, ready1 = _ready(rows0[key]), _ready(rows1[key])
            pair.update(ready_vbk0_s=ready0, ready_vbk_s=ready1,
                        ready_difference_s=None if None in (ready0, ready1) else ready1 - ready0,
                        vbk0_ready_vbk_not=ready0 is not None and ready1 is None)
            if None in sides.values():
                pair["new_faults"] = {"computed": False, "reason": "a T4h record missing"}
            else:
                pair["new_faults"] = sorted(list(item) for item in sides["VBK"] - sides["VBK0"])
            out.append(pair)
    return out


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
    lines, lines_by_id = [], {}
    for ident, path in sorted(runs.items()):
        bundle, leg, arm = ident
        where = {"bundle": bundle, "fault_leg": leg, "arm": arm, "run": str(path)}
        if not path.is_file():
            lines.append({**where, "computed": False, "reason": "run file missing"})
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        rows = document["results"] if isinstance(document, dict) else document
        lines_by_id[ident] = rows
        if not rows:
            lines.append({**where, "computed": False, "reason": "no line"})
        for row in rows:
            lines.append({**where, **line_record(bundle, row, t4h.get(ident))})
    expected = len(BUNDLES) * len(LEGS) * len(ARMS)
    return {"rule": "jp3_remedy_spec_v5_erratum2.md 2-9.5 (spec v5 6.4, a record)",
            "status": "written", "runs": len(runs), "runs_expected": expected,
            "lines": lines, "tck_pairs": tck_pairs(lines_by_id, t4h)}


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
