"""Run identity record of a 436.8 runner output (rules ``v5_resume_4368_rules_rev1.md`` RV1-3.1).

The r79 / r67 / r69 runners write no identity of their own. A step before and a step after each
such run call this script, which appends ``run_v5._write_identity``'s ``run_identity`` record to
``<output stem>.identity.json`` next to the output (the same sidecar ``run_v5 --out`` writes).
It writes the sidecar only; it never starts a run.

Usage (dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/resume_k1_identity.py <output> --moment start|end
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v5  # noqa: E402

MOMENTS = ("start", "end")


def sidecar_path(output: Path) -> Path:
    """``<output stem>.identity.json`` (``h6_dg3_v4on.json`` -> ``h6_dg3_v4on.identity.json``)."""
    return output.with_name(output.stem + ".identity.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path, help="the runner output the record belongs to")
    parser.add_argument("--moment", required=True, choices=MOMENTS)
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    run_v5._write_identity(args.output, args.moment)
    print(f"{args.moment} identity -> {sidecar_path(args.output)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
