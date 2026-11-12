"""Run one study-1 case twice, with and without the settle v2 record (436.8 Q-U1 = A).

Prints one JSON line: the two ``run.commands_sha256`` values and the settle v2 status. The record
is computed from the finished result, so the two hashes must be the same. Used by
``test_resume4368_rev1.py``; a harness run (dynamics-dev, about a minute).

Usage: python -I -B settle_v2_hash_runner.py <project root> <case id>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
for _path in (S9_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import s9_slope_fix_candidates as fix  # noqa: E402
import s9_soil_slope as slope  # noqa: E402


def main() -> None:
    case_id = sys.argv[2]
    case = next(case for _, case in fix.suite_cases("slope") if case["id"] == case_id)
    with_record = slope.run_one(dict(case))
    original = slope._settle_v2_record
    slope._settle_v2_record = lambda result: {"status": "disabled"}
    try:
        without_record = slope.run_one(dict(case))
    finally:
        slope._settle_v2_record = original
    print(
        json.dumps(
            {
                "with": with_record.get("run", {}).get("commands_sha256"),
                "without": without_record.get("run", {}).get("commands_sha256"),
                "error": with_record.get("error") or without_record.get("error"),
                "settle_v2": with_record.get(slope.SETTLE_V2_KEY),
                "record_fields_settle_v2": fix.slope_record_fields(with_record).get("settle_v2")
                is not None,
            }
        )
    )


if __name__ == "__main__":
    main()
