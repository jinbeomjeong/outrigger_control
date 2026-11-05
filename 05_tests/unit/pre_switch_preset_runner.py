"""Run a harness script with the R8 preset as it was before the spec 429.11 switch.

The switch (2026-10-30) turned P-S8-36 SGS (``soil_stop``) and P-S8-37 R4
(``flat_soil_margin_m`` 0.03 m) on in ``C2Config.with_10hz_d1``, and the user decision of
2026-11-04 turned ``clip_returned_command`` on. The subprocess hash tests compare the project
preset with wrapper hashes stored before those changes, so they run their harness through this
runner: it gives ``with_10hz_d1`` the old keyword defaults (all off) and then calls the script's
``main()``. The patch runs at import time, so spawned pool workers (which re-import this file as
``__mp_main__``) get it too; a caller that passes the keywords explicitly still gets what it
asks for.

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
PRE_SWITCH_CLIP_RETURNED_COMMAND = False
PRE_SWITCH_TOUCH_TWIST_HOLD = False
PRE_SWITCH_REAPPROACH_RETRIGGER_TWO_SAMPLES = False

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
        clip_returned_command: bool = PRE_SWITCH_CLIP_RETURNED_COMMAND,
        touch_twist_hold: bool = PRE_SWITCH_TOUCH_TWIST_HOLD,
        reapproach_retrigger_two_samples: bool = PRE_SWITCH_REAPPROACH_RETRIGGER_TWO_SAMPLES,
    ):
        return switched_preset(
            self,
            soil_stop=soil_stop,
            flat_soil_margin_m=flat_soil_margin_m,
            clip_returned_command=clip_returned_command,
            touch_twist_hold=touch_twist_hold,
            reapproach_retrigger_two_samples=reapproach_retrigger_two_samples,
        )

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
