"""Family F lines of the 436.8 conditional run (rules ``v5_resume_4368_rules_rev3.md`` R3-E2).

The two r67 runs (V0, VB) of the v5 criteria rev5 5.2 keys at 16 phases run every screen event;
this script writes the FS24 runs as ``h9_family_F.jsonl``: one line per (setting, key, phase),
each the r67 run record as written (gates, final phase, fault periods, ``commands_sha256``,
``resume_k1`` block) plus ``setting``, ``key``, ``source`` and ``source_sha256``. It reads the
two outputs only; it runs nothing.

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/resume_k1_family_f.py <V0 json> <VB json>
      [--event FS24] --out <h9_family_F.jsonl>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SETTINGS = ("V0", "VB")
DEFAULT_EVENT = "FS24"


def family_lines(path: Path, setting: str, event: str) -> list[dict]:
    """The ``event`` runs of one r67 output as lines (result key and setting added)."""
    data = path.read_bytes()
    document = json.loads(data.decode("utf-8"))
    sha256 = hashlib.sha256(data).hexdigest()
    meta = document.get("meta") or {}
    lines = []
    for result in document.get("results") or []:
        for run in result.get("runs") or []:
            if run.get("event") != event:
                continue
            lines.append(
                {
                    "setting": setting,
                    "key": result.get("key"),
                    # rev4 R4-B5: the line carries the run's setting and controller tag
                    "v5_setting": result.get("v5_setting", meta.get("v5_setting")),
                    "controller_tag": run.get("controller_tag", result.get("controller_tag")),
                    **run,
                    "source": str(path),
                    "source_sha256": sha256,
                }
            )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("v0", type=Path)
    parser.add_argument("vb", type=Path)
    parser.add_argument("--event", default=DEFAULT_EVENT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    lines = []
    for setting, path in zip(SETTINGS, (args.v0, args.vb), strict=True):
        lines += family_lines(path, setting, args.event)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    print(json.dumps({"lines": len(lines), "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
