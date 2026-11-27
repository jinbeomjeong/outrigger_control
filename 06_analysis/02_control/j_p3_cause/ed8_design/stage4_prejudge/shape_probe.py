"""Value-blind shape probe of the edition 8 stage 4 outputs (C8 56849248).

Prints, per output file and line kind (job setting, or ``ed8_probe`` arm / plant), the line
count and the top-level key names with how many lines carry each (non-null). No value is
printed: setting / arm / plant names are job identities, not judged values.

Usage: python -I -B shape_probe.py <stage root> <out.json>
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

STAGE_FILES = {
    "impl_p80": ["ed7_probe_a2.jsonl"],
    "impl_p816": ["p816.jsonl"],
    "impl_p85": ["p85.jsonl"],
    "impl_p88": ["p88.jsonl"],
    "impl_p815": ["p815.jsonl"],
    "impl_t8": ["ed8_t8.jsonl"],
    "impl_cases": ["ed8_cases.jsonl"],
    "l1ref": ["L1_VBN.json", "L1_VBN0.json", "L1a_VBN.json", "L1a_VBN0.json"],
}


def read_lines(path: Path) -> tuple[list[dict], str]:
    if path.suffix == ".jsonl":
        text = path.read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()], "jsonl"
    document = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(document, dict):
        top = sorted(document)
        return list(document.get("results") or []), f"json top keys {top}"
    return list(document), "json list"


def kind_of(row: dict) -> str:
    probe = row.get("ed8_probe")
    if isinstance(probe, dict):
        return f"arm={probe.get('arm')} plant={probe.get('plant')}"
    job = row.get("job")
    if isinstance(job, dict) and "setting" in job:
        return f"setting={job.get('setting')}"
    if "v5_setting" in row:
        return f"v5_setting={row.get('v5_setting')}"
    return "unknown"


def main() -> int:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    report: dict = {}
    for stage, names in STAGE_FILES.items():
        for name in names:
            path = root / f"{stage}_a1" / name
            rows, form = read_lines(path)
            kinds: dict[str, Counter] = defaultdict(Counter)
            counts: Counter = Counter()
            for row in rows:
                kind = kind_of(row)
                counts[kind] += 1
                for key, value in row.items():
                    kinds[kind][key if value is not None else f"{key} (null)"] += 1
            report[f"{stage}/{name}"] = {
                "form": form, "lines": len(rows),
                "kinds": {kind: {"lines": counts[kind], "keys": dict(sorted(keys.items()))}
                          for kind, keys in sorted(kinds.items())}}
            print(f"{stage}/{name}: {form}, {len(rows)} lines, kinds {dict(counts)}")
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
