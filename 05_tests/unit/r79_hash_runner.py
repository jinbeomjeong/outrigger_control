"""Run one r79 key twice, with and without the command log (436.8 rules rev3 R3-E4).

Prints one JSON line: ``base.commands_sha256`` of both runs, the new top-level
``commands_sha256`` and whether the second run has none. The log is record only, so the base
hashes must be the same. Used by ``test_resume4368_rev1.py``; a harness run (dynamics-dev).

Usage: python -I -B r79_hash_runner.py <project root> <r79 key>   (env R79_V5_SETTING set)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
for _path in (S8_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import r79_sensor_screen as screen  # noqa: E402


def main() -> None:
    key = sys.argv[2]
    # without the log first: the log, once installed, stays in the process
    original_install, original_hash = screen._install_command_log, screen._commands_sha256
    screen._install_command_log = lambda: None
    screen._commands_sha256 = lambda ctrl: None
    try:
        without_log = screen.run_job(key)
    finally:
        screen._install_command_log, screen._commands_sha256 = original_install, original_hash
    with_log = screen.run_job(key)
    print(
        json.dumps(
            {
                "error": with_log.get("error") or without_log.get("error"),
                "base_with": (with_log.get("base") or {}).get("commands_sha256"),
                "base_without": (without_log.get("base") or {}).get("commands_sha256"),
                "top": with_log.get(screen.COMMANDS_SHA256_KEY),
                "top_without": without_log.get(screen.COMMANDS_SHA256_KEY),
            }
        )
    )


if __name__ == "__main__":
    main()
