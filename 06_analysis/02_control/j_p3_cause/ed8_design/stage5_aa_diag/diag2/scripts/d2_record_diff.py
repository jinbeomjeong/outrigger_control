"""Leaf paths where B / C records differ from the diagnosis-1 trace-off record (names only)."""

import json
import sys
from pathlib import Path

folder = Path(sys.argv[1])
IGNORED = {"wall_s", "label", "trace", "two_pressure_file", "diag"}


def leaves(value, prefix=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, f"{prefix}.{key}" if prefix else key)
    else:
        yield prefix, value


def load(path):
    return {r["label"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines())}


base = load(folder.parent / "runs_trace_off.jsonl")
lines = []
for step in ("B_gyro_all_trace_on.jsonl", "C_gyro_d1only_trace_on.jsonl"):
    for label, record in load(folder / step).items():
        a = dict(leaves({k: v for k, v in base[label].items() if k not in IGNORED}))
        b = dict(leaves({k: v for k, v in record.items() if k not in IGNORED}))
        diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        lines.append(f"{step[0]} {label}: {diff}")
b_records, c_records = load(folder / "B_gyro_all_trace_on.jsonl"), load(folder / "C_gyro_d1only_trace_on.jsonl")
for label in b_records:
    same = {k: v for k, v in b_records[label].items() if k not in IGNORED} == {
        k: v for k, v in c_records[label].items() if k not in IGNORED}
    lines.append(f"B==C {label}: {same}")
Path(sys.argv[2]).write_text("\n".join(lines), encoding="utf-8")
