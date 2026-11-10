"""Run a script with the R8 preset as it was just before the LAS-b K1 switch.

The switch (``las_k1_rules_adopt.md`` 9.1, after the K1 re-measure judgement
``las_k1_rem_judgement.md``) turned ``flat_soil_margin_order_gate`` (the R4c30 order gate) on in
``C2Config.with_10hz_d1``. This runner gives the preset the old default for that keyword only
and then calls the script's ``main()``, so every other preset keyword stays as it is now: it
reproduces only the gate-off LAS-b results before the switch (tags ``final_C4G2_LAS`` /
``final_C4G2_P3_LAS`` / ``ABL_LAS``, e.g. the K1off lines of ``v5/las/k1/``). The gate-on
diagnostic rows run before the switch under those tags (S-Ch gateon, REM R7 / R8 / F1 / F2) are
reproduced only by a checkout of their result's ``git_at_start`` commit: since the switch the
old tags check the gate off (post-switch audit R-2). Results older than
the LAS-b switch need ``pre_las_preset_runner.py``, older ones ``pre_c4g2_preset_runner.py`` or
``pre_switch_preset_runner.py`` (all keep the K1 gate off as well).

Limit: a keyword runner keeps every other change of the later commits; a bit-for-bit
reproduction of a stored result needs the code of its ``git_at_start`` commit.

The patch runs at import time, so spawned pool workers (which re-import this file as
``__mp_main__``) get it too; a caller that passes the keyword explicitly still gets what it asks
for.

Usage:
  python -I -B pre_k1_preset_runner.py <script.py> [script arguments ...]
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

# The harness drivers (run_v5, las_targeted, k1_targeted) fix one BLAS / OpenMP thread before
# numpy loads; this runner imports c2 (and numpy) before them, so it must set them first (the
# lesson of pre_las_preset_runner.py, 2026-11-08).
for _name in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_name, "1")
os.environ.setdefault("MKL_THREADING_LAYER", "TBB")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "03_src"
PRE_K1_FLAT_SOIL_MARGIN_ORDER_GATE = False

if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


def _install_pre_k1_preset() -> None:
    from outrigger_sim.control import c2

    switched_preset = c2.C2Config.with_10hz_d1

    def pre_k1_preset(
        self,
        *,
        flat_soil_margin_order_gate: bool = PRE_K1_FLAT_SOIL_MARGIN_ORDER_GATE,
        **keywords,
    ):
        return switched_preset(
            self, flat_soil_margin_order_gate=flat_soil_margin_order_gate, **keywords
        )

    c2.C2Config.with_10hz_d1 = pre_k1_preset


_install_pre_k1_preset()


def main() -> None:
    script = Path(sys.argv[1]).resolve()
    if str(script.parent) not in sys.path:
        sys.path.insert(0, str(script.parent))  # passed on to spawned workers with sys.path
    sys.argv = [str(script), *sys.argv[2:]]
    importlib.import_module(script.stem).main()


if __name__ == "__main__":
    main()
