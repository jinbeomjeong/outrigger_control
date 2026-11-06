"""Checks of aggregate_v5.golden_check: which V0 phase is compared with the golden off run.

Run: python -I -B -m pytest <this file> (dynamics-dev or python-dev, from the project root).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from aggregate_v5 import golden_check  # noqa: E402

GOLDEN_HASH = "a" * 64
OTHER_HASH = "b" * 64


def _write_golden(folder: Path, case: str, offset_s: float | None) -> None:
    record = {"commands_sha256": GOLDEN_HASH, "offset_s": offset_s}
    folder.joinpath(f"OFF_{case}.json").write_text(json.dumps(record), encoding="utf-8")


def _row(case: str, phase: str, commands_sha256: str, setting: str = "V0") -> dict:
    return {"row": case, "phase": phase, "setting": setting,
            "commands_sha256": commands_sha256}


def test_event_row_is_compared_at_the_golden_offset_only(tmp_path):
    _write_golden(tmp_path, "R15", 0.05)
    rows = [_row("R15", "offset 0.05", GOLDEN_HASH), _row("R15", "offset 0.0", OTHER_HASH)]

    checks = golden_check(rows, tmp_path)

    assert checks == [{"row": "R15", "phase": "offset 0.05", "golden_offset_s": 0.05,
                       "equal": True}]


def test_steady_row_is_compared_at_eps_zero(tmp_path):
    _write_golden(tmp_path, "S1", None)
    rows = [_row("S1", "eps 0.0", OTHER_HASH), _row("S1", "eps 0.002", GOLDEN_HASH)]

    checks = golden_check(rows, tmp_path)

    assert checks == [{"row": "S1", "phase": "eps 0.0", "golden_offset_s": None,
                       "equal": False}]


def test_other_settings_are_not_compared(tmp_path):
    _write_golden(tmp_path, "R12", 0.0)

    assert golden_check([_row("R12", "offset 0.0", GOLDEN_HASH, setting="VB")], tmp_path) == []
