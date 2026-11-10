"""The four pre-switch preset runners give the R8 preset the K1 order gate off.

Each runner patches ``C2Config.with_10hz_d1`` when it is imported and then runs a script's
``main()``. A probe script run through each runner (in a fresh subprocess, as the runners are
used) reads the preset it gets (post-switch audit R-5, ``las_k1_switch_post_audit.md``).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

UNIT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = UNIT_DIR.parents[1]
RUNNER_TIMEOUT_S = 120
PROBE_SOURCE = '''
import json
import sys


def main():
    from outrigger_sim.control.c2 import C2Config

    preset = C2Config().with_10hz_d1()
    print(json.dumps({
        "order_gate": preset.slope_clearance_margin.flat_soil_margin_order_gate,
        "liftoff_approach_slow": preset.liftoff_approach_slow.enable,
        "class_default_gate": C2Config().slope_clearance_margin.flat_soil_margin_order_gate,
    }))
'''
RUNNERS = [
    # (runner file, LAS-b of its preset)
    ("pre_k1_preset_runner.py", True),
    ("pre_las_preset_runner.py", False),
    ("pre_c4g2_preset_runner.py", False),
    ("pre_switch_preset_runner.py", False),
]


def _preset_through_runner(runner: Path, probe_dir: Path) -> dict:
    probe = probe_dir / "preset_probe.py"
    probe.write_text(PROBE_SOURCE, encoding="utf-8")
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MKL_THREADING_LAYER="TBB")
    completed = subprocess.run(
        [sys.executable, "-I", "-B", str(runner), str(probe)],
        cwd=PROJECT_ROOT, env=environment, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=RUNNER_TIMEOUT_S, check=False)
    assert completed.returncode == 0, completed.stderr[-3000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize(("runner_name", "is_las_on"), RUNNERS)
def test_runner_preset_has_the_order_gate_off(runner_name: str, is_las_on: bool,
                                              tmp_path: Path) -> None:
    preset = _preset_through_runner(UNIT_DIR / runner_name, tmp_path)
    assert preset["order_gate"] is False
    assert preset["liftoff_approach_slow"] is is_las_on
    assert preset["class_default_gate"] is False


def test_the_preset_without_a_runner_has_the_order_gate_on(tmp_path: Path) -> None:
    """Control case: the probe itself is not what turns the gate off."""
    probe = tmp_path / "preset_probe.py"
    probe.write_text(PROBE_SOURCE + "\nmain()\n", encoding="utf-8")
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MKL_THREADING_LAYER="TBB",
                       PYTHONPATH=str(PROJECT_ROOT / "03_src"))
    completed = subprocess.run(
        [sys.executable, "-B", str(probe)], cwd=PROJECT_ROOT, env=environment,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=RUNNER_TIMEOUT_S, check=False)
    assert completed.returncode == 0, completed.stderr[-3000:]
    preset = json.loads(completed.stdout.strip().splitlines()[-1])
    assert preset["order_gate"] is True and preset["liftoff_approach_slow"] is True
