"""Run one r79 key with ``r79_sensor_screen.run_job`` of a given project root (X-10 tests).

Writes the result row to ``<out json>`` (``json.dumps(row, default=float)``, the form of the
r79 runners) and prints one JSON line with its error (or None). The root may be another
checkout (the commit before X-10), so the code under test is the one of that root; the
environment selects setting, rod model, T4h folder and plan as for a real run. A harness run
(numba): about one to two minutes per key.

Usage: python -I -B rod_fault_runner.py <project root> <r79 key> <out json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
for _path in (ROOT / "04_scripts" / "03_control" / "s8", ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import r79_sensor_screen as screen  # noqa: E402


def main() -> None:
    key, out_path = sys.argv[2], Path(sys.argv[3])
    row = screen.run_job(key)
    out_path.write_text(json.dumps(row, default=float), encoding="utf-8")
    print(json.dumps({"error": row.get("error"), "module_file": screen.__file__,
                      "rod_fault_imported": "rod_fault_plan" in sys.modules}))


if __name__ == "__main__":
    main()
