"""Copies of the R8 sample periods agree with their source ``control/c2.py`` (YAML bundle D3).

Decision D3 (2026-10-25): the control cycle and IMU sample periods stay in ``c2.py``
(``R8_PERIOD_S``, ``R8_IMU_SAMPLE_PERIOD_S``) and are not moved into the YAML, so that a change of
the controller variant does not invalidate the plant snapshots. The copies below must follow it.
Scripts in ``04_scripts`` are not imported (they pull in pychrono / numba); their module-level
constant is read from the source with :mod:`ast`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from outrigger_sim.control import c2, two_pressure

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_S6C_PATH = PROJECT_ROOT / "04_scripts" / "02_chrono" / "run_S6C.py"
CYCLE_TIMING_PATH = PROJECT_ROOT / "04_scripts" / "03_control" / "c2_cycle_timing.py"


def _module_constant(path: Path, name: str) -> object:
    """Value of the module-level assignment ``name = <literal>`` in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise LookupError(f"{path}: no module-level assignment {name} = <literal>")


def test_control_period_copy_equals_c2() -> None:
    assert _module_constant(CYCLE_TIMING_PATH, "R8_PERIOD_S") == c2.R8_PERIOD_S


@pytest.mark.parametrize(
    ("label", "value"),
    [
        ("run_S6C.IMU_SAMPLE_PERIOD_S", _module_constant(RUN_S6C_PATH, "IMU_SAMPLE_PERIOD_S")),
        ("two_pressure.IMU_GYRO_SAMPLE_PERIOD_S", two_pressure.IMU_GYRO_SAMPLE_PERIOD_S),
    ],
)
def test_imu_sample_period_copy_equals_c2(label: str, value: object) -> None:
    assert value == c2.R8_IMU_SAMPLE_PERIOD_S, label
