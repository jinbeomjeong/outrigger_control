"""Run a script with the R8 preset as it was just before the LAS-b switch (2026-11-08).

The switch turned ``liftoff_approach_slow`` (LAS-b, variant b0 of ``las_targeted_rules.md``) on
in ``C2Config.with_10hz_d1``; the later K1 switch (``las_k1_rules_adopt.md`` 9) turned
``flat_soil_margin_order_gate`` on. This runner gives the preset the old defaults of these two
keywords (both off) and then calls the script's ``main()``, so every other preset keyword stays
as it is now (``final_C4G2`` / ``final_C4G2_P3`` results, e.g. ``v5/d1.jsonl``). Results of the
LAS-b preset before the K1 switch (``final_C4G2_LAS`` / ``final_C4G2_P3_LAS``) need
``pre_k1_preset_runner.py``. Results older than the C4G2 switch need
``pre_c4g2_preset_runner.py``, older ones ``pre_switch_preset_runner.py`` (both keep LAS-b and
the K1 gate off as well).

The patch runs at import time, so spawned pool workers (which re-import this file as
``__mp_main__``) get it too; a caller that passes the keyword explicitly still gets what it asks
for.

Usage:
  python -I -B pre_las_preset_runner.py <script.py> [script arguments ...]
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

# The harness drivers (run_v5, las_targeted) fix one BLAS / OpenMP thread before numpy loads;
# this runner imports c2 (and numpy) before them, so it must set them first: with the default
# thread count the stored command hashes of the v5 main rows are not reproduced (2026-11-08).
for _name in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_name, "1")
os.environ.setdefault("MKL_THREADING_LAYER", "TBB")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "03_src"
PRE_LAS_LIFTOFF_APPROACH_SLOW = False
PRE_LAS_FLAT_SOIL_MARGIN_ORDER_GATE = False
"""The K1 order gate came after LAS-b, so the pre-LAS-b preset has it off too."""

if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


def _install_pre_las_preset() -> None:
    from outrigger_sim.control import c2

    switched_preset = c2.C2Config.with_10hz_d1

    def pre_las_preset(
        self,
        *,
        liftoff_approach_slow: bool = PRE_LAS_LIFTOFF_APPROACH_SLOW,
        flat_soil_margin_order_gate: bool = PRE_LAS_FLAT_SOIL_MARGIN_ORDER_GATE,
        **keywords,
    ):
        return switched_preset(
            self,
            liftoff_approach_slow=liftoff_approach_slow,
            flat_soil_margin_order_gate=flat_soil_margin_order_gate,
            **keywords,
        )

    c2.C2Config.with_10hz_d1 = pre_las_preset


_install_pre_las_preset()


def main() -> None:
    script = Path(sys.argv[1]).resolve()
    if str(script.parent) not in sys.path:
        sys.path.insert(0, str(script.parent))  # passed on to spawned workers with sys.path
    sys.argv = [str(script), *sys.argv[2:]]
    importlib.import_module(script.stem).main()


if __name__ == "__main__":
    main()
