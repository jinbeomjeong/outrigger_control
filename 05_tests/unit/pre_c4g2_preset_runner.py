"""Run a script with the R8 preset as it was just before the C4G2 switch (spec 433, 2026-11-05).

The switch turned ``touch_twist_hold`` on in ``C2Config.with_10hz_d1``. This runner gives the
preset the old default for that keyword only and then calls the script's ``main()``, so
``soil_stop``, ``flat_soil_margin_m`` and ``clip_returned_command`` stay as they are now. It
reproduces the "off" acceptance rows (``acceptance/c4g2_only/grid/*_off.json``, ``d8_main_off``)
and runs a study wrapper of ``touch_phase/candidates.py`` on the preset it was written for. Results
older than the 2026-11-04 clip or the spec 429.11 switch need ``pre_switch_preset_runner.py``.

The patch runs at import time, so spawned pool workers (which re-import this file as
``__mp_main__``) get it too; a caller that passes the keyword explicitly still gets what it asks
for.

Usage:
  python -I -B pre_c4g2_preset_runner.py <script.py> [script arguments ...]
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "03_src"
PRE_C4G2_TOUCH_TWIST_HOLD = False
PRE_C4G2_LIFTOFF_APPROACH_SLOW = False
"""LAS-b came after C4G2 (2026-11-08), so the pre-C4G2 preset has it off too."""

if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


def _install_pre_c4g2_preset() -> None:
    from outrigger_sim.control import c2

    switched_preset = c2.C2Config.with_10hz_d1

    def pre_c4g2_preset(
        self,
        *,
        touch_twist_hold: bool = PRE_C4G2_TOUCH_TWIST_HOLD,
        liftoff_approach_slow: bool = PRE_C4G2_LIFTOFF_APPROACH_SLOW,
        **keywords,
    ):
        return switched_preset(
            self,
            touch_twist_hold=touch_twist_hold,
            liftoff_approach_slow=liftoff_approach_slow,
            **keywords,
        )

    c2.C2Config.with_10hz_d1 = pre_c4g2_preset


_install_pre_c4g2_preset()


def main() -> None:
    script = Path(sys.argv[1]).resolve()
    if str(script.parent) not in sys.path:
        sys.path.insert(0, str(script.parent))  # passed on to spawned workers with sys.path
    sys.argv = [str(script), *sys.argv[2:]]
    importlib.import_module(script.stem).main()


if __name__ == "__main__":
    main()
