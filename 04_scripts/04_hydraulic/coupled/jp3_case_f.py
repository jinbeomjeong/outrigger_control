"""436.9 edition 4a case F (``jp3_remedy_spec.md`` 13.8, J4a-14; addendum 4a-1): the
``grid_r67_top`` FR row (key ``screen|top|8.0|ready|FR``, offset 0.075 s) under the settings of
case A (VB, LS1 .. LS4), B (VBH, LSH1 .. LSH4) and E (VBJ, LSJ1 .. LSJ4): 15 runs of
``04_scripts/03_control/s8/r67_g1_screen.py``, one output JSON per setting.

F-A is compared with the stored grid (``results[13].runs[3]``: FR 3 / -0.900 bar @ 48.7 s),
F-B with the F-A command hash (T8); F-E is recorded (addendum 4a-1: no baseline row).

Usage (project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_case_f.py <out folder> [--print]
      [--python <dynamics-dev python>]
``--print`` writes the 15 commands without running them (the main session launches them).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCREEN = ROOT / "04_scripts" / "03_control" / "s8" / "r67_g1_screen.py"
CASE_F_KEY = "screen|top|8.0|ready|FR"
CASE_F_OFFSET_S = "0.075"
CASE_F_SETTINGS = {"A": ("VB", "LS1", "LS2", "LS3", "LS4"),
                   "B": ("VBH", "LSH1", "LSH2", "LSH3", "LSH4"),
                   "E": ("VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4")}
DEFAULT_PYTHON = r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe"


def case_f_runs(out_folder: Path) -> list[tuple[str, str, Path]]:
    """(group, setting, output JSON) of the 15 runs."""
    return [(group, setting, out_folder / f"case_f_{group}_{setting}.json")
            for group, settings in CASE_F_SETTINGS.items() for setting in settings]


def run_environment(setting: str) -> dict[str, str]:
    return {**os.environ, "R67_V5_SETTING": setting, "R67_OFFSETS": CASE_F_OFFSET_S,
            "MKL_THREADING_LAYER": "TBB", "PYTHONDONTWRITEBYTECODE": "1"}


def command(python: str, out_json: Path) -> list[str]:
    """``r67_g1_screen.py <project_root> <out_json> [workers] --keys <key>``."""
    return [python, "-I", "-B", str(SCREEN), str(ROOT), str(out_json), "1",
            "--keys", CASE_F_KEY]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_folder", type=Path)
    parser.add_argument("--print", action="store_true", dest="only_print")
    parser.add_argument("--python", default=DEFAULT_PYTHON)
    args = parser.parse_args()
    args.out_folder.mkdir(parents=True, exist_ok=True)
    failed = 0
    for group, setting, out_json in case_f_runs(args.out_folder):
        line = command(args.python, out_json)
        if args.only_print:
            print(f"$env:R67_V5_SETTING='{setting}'; $env:R67_OFFSETS='{CASE_F_OFFSET_S}'; & "
                  + " ".join(f'"{part}"' if " " in part or "|" in part else part
                             for part in line))
            continue
        result = subprocess.run(line, env=run_environment(setting), cwd=ROOT, check=False)
        print(group, setting, "exit", result.returncode, flush=True)
        failed += int(result.returncode != 0)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
