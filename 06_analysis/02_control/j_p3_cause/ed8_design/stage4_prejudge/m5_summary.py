"""Compact view of ``m5_keys.json``: per line kind the keys that are not present on every
line, the meta lookup states and the form counts (counts only).

Usage: python -I -B m5_summary.py <m5_keys.json> <out.txt>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    lines: list[str] = []
    for name, entry in report["files"].items():
        lines.append(f"== {name}: {entry['lines']} lines")
        if "document" in entry:
            lines.append(f"   document: {entry['document']}")
        for kind, part in entry["kinds"].items():
            total = part["lines"]
            incomplete = {key: counts for key, counts in part["keys"].items()
                          if counts.get("present", 0) != total}
            lines.append(f"  -- {kind}: {total} lines, all-present keys "
                         f"{len(part['keys']) - len(incomplete)}/{len(part['keys'])}")
            for key, counts in incomplete.items():
                lines.append(f"     not all present: {key} {counts}")
            meta = {key: counts for key, counts in part["meta_lookup"].items()
                    if set(counts) != {"line_present/meta_present"}
                    and set(counts) != {"line_present/meta_absent"}}
            for key, counts in meta.items():
                lines.append(f"     meta lookup: {key} {counts}")
            lines.append(f"     form: {part['form']['counts']}")
            if part["form"]["reason_token_distribution"]:
                lines.append(f"     reason tokens: {part['form']['reason_token_distribution']}")
    lines.append(f"== v0_smoke: {json.dumps(report['v0_smoke'])}")
    Path(sys.argv[2]).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
