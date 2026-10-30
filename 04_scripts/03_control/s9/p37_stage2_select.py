"""Spec 427.11 stage 2: the runs the stage 1 combination acted in, as run selections.

Reads the stage 1 comparison files and writes one selection file per runner:
  wrapper  ``s9_slope_fix_candidates.py compare`` outputs (``comparison`` rows with ``acted``)
           -> ``<prefix>_<suite>_ids.txt``: the ``--ids`` value (ids joined by ";")
  study A / r67  ``screen_candidate_compare.py`` outputs (rows with ``acted``)
           -> ``<prefix>_A_filter.txt`` / ``<prefix>_r67_filter.txt``: the ``R426A_FILTER`` /
              ``R67_FILTER`` value (job keys joined by ","; a job runs all its branches)
Only the parts given by ``--parts`` count (default: P36s, P37t, R4c: the P38z part has its own
full run, spec 429.5). Prints the counts.

Usage:
  python -I p37_stage2_select.py --prefix <dir/stem> [--parts P36s,P37t,R4c]
      [--wrapper CMP.json ...] [--study-a CMP.json] [--r67 CMP.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_PARTS = ("P36s", "P37t", "R4c")


def _has_part(acted_parts: str, parts: set[str]) -> bool:
    return bool(parts & set(filter(None, (acted_parts or "").split("+"))))


def wrapper_ids(paths: list[Path], parts: set[str]) -> dict[str, list[str]]:
    """Suite -> ids whose candidate run acted with one of ``parts``."""
    selected: dict[str, list[str]] = {}
    for path in paths:
        for row in json.loads(path.read_text(encoding="utf-8"))["comparison"]:
            if _has_part(row.get("acted_parts", ""), parts):
                selected.setdefault(row["suite"], []).append(row["id"])
    return {suite: sorted(set(ids)) for suite, ids in selected.items()}


def screen_job_keys(path: Path, parts: set[str]) -> list[str]:
    """Job keys (branch key without the branch fields) with an acted run."""
    keys = set()
    for row in json.loads(path.read_text(encoding="utf-8"))["rows"]:
        if not _has_part(row.get("acted_parts", ""), parts):
            continue
        fields = row["key"].split("|")
        keys.add("|".join(fields[:-2]))  # study A: <job>|timing|event, r67: <job>|event|offset
    return sorted(keys)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--parts", default=",".join(DEFAULT_PARTS))
    parser.add_argument("--wrapper", type=Path, nargs="*", default=[])
    parser.add_argument("--study-a", type=Path)
    parser.add_argument("--r67", type=Path)
    args = parser.parse_args()
    parts = {part for part in args.parts.split(",") if part}
    args.prefix.parent.mkdir(parents=True, exist_ok=True)
    for suite, ids in wrapper_ids(args.wrapper, parts).items():
        Path(f"{args.prefix}_{suite}_ids.txt").write_text(";".join(ids), encoding="utf-8")
        print(suite, len(ids), "ids")
    for name, path in (("A", args.study_a), ("r67", args.r67)):
        if path is None:
            continue
        keys = screen_job_keys(path, parts)
        Path(f"{args.prefix}_{name}_filter.txt").write_text(",".join(keys), encoding="utf-8")
        print(name, len(keys), "jobs")


if __name__ == "__main__":
    main()
