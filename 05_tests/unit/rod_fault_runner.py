"""Run one r79 key with ``r79_sensor_screen.run_job`` of a given project root (X-10 tests).

Writes the result row to ``<out json>`` (``json.dumps(row, default=float)``, the form of the
r79 runners) and prints one JSON line with its error (or None). The root may be another
checkout (the commit before X-10), so the code under test is the one of that root; the
environment selects setting, rod model, T4h folder and plan as for a real run. A harness run
(numba): about one to two minutes per key.

``X10_REV5_ALIAS=<name>=<setting>`` (edition 5 tests) registers ``<name>`` in this process as
the edition 4a revision 5 options of ``<setting>`` (``run_v5.JP3_REV5_SETTINGS``), so that the
X-10 bit-for-bit test (i) runs VBJ with revision 5 on the edition 5 code (test only: no
runner or setting list carries the alias).

Usage: python -I -B rod_fault_runner.py <project root> <r79 key> <out json>
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
for _path in (ROOT / "04_scripts" / "03_control" / "s8", ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import r79_sensor_screen as screen  # noqa: E402

REV5_ALIAS_ENV = "X10_REV5_ALIAS"


def register_rev5_alias() -> None:
    """The ``X10_REV5_ALIAS`` setting of this process (nothing without the variable)."""
    alias = os.environ.get(REV5_ALIAS_ENV)
    if not alias:
        return
    name, source = alias.split("=", 1)
    coupled_dir = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
    if str(coupled_dir) not in sys.path:
        sys.path.insert(0, str(coupled_dir))
    import run_v5

    run_v5.ALL_SETTINGS[name] = run_v5.JP3_REV5_SETTINGS[source]


def main() -> None:
    key, out_path = sys.argv[2], Path(sys.argv[3])
    register_rev5_alias()
    row = screen.run_job(key)
    out_path.write_text(json.dumps(row, default=float), encoding="utf-8")
    print(json.dumps({"error": row.get("error"), "module_file": screen.__file__,
                      "rod_fault_imported": "rod_fault_plan" in sys.modules}))


if __name__ == "__main__":
    main()
