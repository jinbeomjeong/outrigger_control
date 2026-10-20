"""Shared paths and settings of the linear-solver benchmark (pychrono 10, Chrono-dev).

Scripts in this folder run with ``python -I`` (safe path: the script folder is not on
``sys.path``), so each script inserts this folder before ``import bench_common``. This module
then puts ``04_scripts/00_cad`` (project path constants, ``cad_common``) and ``03_src``
(``outrigger_sim``) on ``sys.path``.

Outputs:
  * per-run results, logs, GIF frames: ``07_results/solver_benchmark/`` (git-ignored)
  * summary JSON / PNG and the three GIFs: ``06_analysis/01_chrono/solver_benchmark*``
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_CAD_SCRIPTS = HERE.parents[1] / "00_cad"
if str(_CAD_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CAD_SCRIPTS))

import cad_common  # noqa: E402

PROJECT_ROOT = cad_common.PROJECT_ROOT
SRC_DIR = PROJECT_ROOT / "03_src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

RESULTS_DIR = PROJECT_ROOT / "07_results" / "solver_benchmark"
"""Per-run JSON (``<phase>/<case>.json``), ``log.txt``, ``gif_frames/``, ``gif_<case>.json``."""
ANALYSIS_DIR = PROJECT_ROOT / "06_analysis" / "01_chrono"
"""Summary ``solver_benchmark.json`` / ``.png`` and ``solver_benchmark_{L1,SCM,scale}.gif``."""

SUMMARY_JSON = ANALYSIS_DIR / "solver_benchmark.json"
SUMMARY_PNG = ANALYSIS_DIR / "solver_benchmark.png"
GIF_PATHS = {
    "l1": ANALYSIS_DIR / "solver_benchmark_L1.gif",
    "scm": ANALYSIS_DIR / "solver_benchmark_SCM.gif",
    "scale": ANALYSIS_DIR / "solver_benchmark_scale.gif",
}

# SCM soil: ASSUMPTION for this benchmark only (literature 'heavy clay, 25 % moisture',
# Wong, Theory of Ground Vehicles, Bekker table: n 0.13, kc 12.70 kN/m^(n+1),
# kphi 1555.95 kN/m^(n+2), c 68.95 kPa, phi 34 deg); Janosi 0.01 m, elastic K 2e8 Pa/m,
# damping R 3e4 Pa s/m are Chrono SCM demo-order values (not soil data).
SCM_PARAMS = {
    "Kphi": 1555.95e3,
    "Kc": 12.70e3,
    "n": 0.13,
    "cohesion_Pa": 68.95e3,
    "friction_deg": 34.0,
    "janosi_m": 0.01,
    "elastic_K": 2e8,
    "damping_R": 3e4,
}
