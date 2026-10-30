"""Run a harness script with the R8 preset as it was before the spec 429.11 switch.

The switch (2026-10-30) turned P-S8-36 SGS (``soil_stop``) and P-S8-37 R4
(``flat_soil_margin_m`` 0.03 m) on in ``C2Config.with_10hz_d1``. The subprocess hash tests
compare the project preset with wrapper hashes stored before that switch, so they run their
harness through this runner: it gives ``with_10hz_d1`` the old keyword defaults (both off) and
then calls the script's ``main()``. The patch runs at import time, so spawned pool workers
(which re-import this file as ``__mp_main__``) get it too; a caller that passes the keywords
explicitly still gets what it asks for.

Usage:
  python -I -B pre_switch_preset_runner.py <script.py> [script arguments ...]
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "03_src"
PRE_SWITCH_SOIL_STOP = False
PRE_SWITCH_FLAT_SOIL_MARGIN_M = 0.0

if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


def _install_pre_switch_preset() -> None:
    from outrigger_sim.control import c2

    switched_preset = c2.C2Config.with_10hz_d1

    def pre_switch_preset(
        self,
        *,
        soil_stop: bool = PRE_SWITCH_SOIL_STOP,
        flat_soil_margin_m: float = PRE_SWITCH_FLAT_SOIL_MARGIN_M,
    ):
        return switched_preset(self, soil_stop=soil_stop, flat_soil_margin_m=flat_soil_margin_m)

    c2.C2Config.with_10hz_d1 = pre_switch_preset


_install_pre_switch_preset()


def main() -> None:
    script = Path(sys.argv[1]).resolve()
    if str(script.parent) not in sys.path:
        sys.path.insert(0, str(script.parent))  # passed on to spawned workers with sys.path
    sys.argv = [str(script), *sys.argv[2:]]
    importlib.import_module(script.stem).main()


if __name__ == "__main__":
    main()
