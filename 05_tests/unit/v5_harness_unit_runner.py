"""Unit checks of the v5 harness options on the reduced plant; writes one JSON (spec 3.1).

Helper of ``test_v5_harness_units.py``: the harness needs dynamics-dev (numba), the tests run in
Chrono-dev. No controller runs here: the plant is lifted onto its legs by a fixed command, then a
check drives single legs. All values are model values of ASSUMPTION inputs.

Usage:
  python -I -B v5_harness_unit_runner.py <check> <out.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "03_src"
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
MAIN_TREE_ROOT = Path(r"C:\workspace\outrigger_control")
"""``r8d1_td.py`` inserts a folder of this tree whichever checkout it runs in."""


class _ThisCheckoutSysPath(list):
    """``sys.path`` whose ``insert`` maps a main-tree folder onto this checkout (git worktree)."""

    def insert(self, index, folder) -> None:
        path = Path(folder)
        if path.is_relative_to(MAIN_TREE_ROOT) and not path.is_relative_to(PROJECT_ROOT):
            folder = str(PROJECT_ROOT / path.relative_to(MAIN_TREE_ROOT))
        super().insert(index, folder)


sys.path = _ThisCheckoutSysPath(sys.path)
for _path in (COUPLED_DIR, SOURCE_DIR):
    sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402

LIFT_EXTRA_S = 1.0
"""Keep lifting this long after the crawler force reached zero."""
REST_S = 3.0
LIFT_LIMIT_S = 60.0
FRONT_LEFT = 0
BAR = 1.0e5
ROD_PRESSURE_RETRACT_PA = 34.818 * BAR
ROD_PRESSURE_EXTEND_PA = 2.0 * BAR
QUARTER = 0.25
MOVE_S = 0.5
AFTER_MOVE_S = 3.0
END_MEAN_S = 0.5


class HarnessBench:
    """One harness plant with the options and the chunk loop of the closed-loop harness."""

    def __init__(self, options) -> None:
        import harness_hydraulics
        import s8_g4_rodside_check as rodside
        import s9_soil_closed_loop as soil
        import verdict_runs  # noqa: F401  (puts the harness folders on sys.path)
        from harness_flow import FlowSetting, make_flow_plant_class
        from params import load_params

        self.cl = soil._imports()[0]
        self.c_lock, self.c_move = soil.C_LOCK, soil.C_MOVE
        self.v_max = load_params().v_max
        off = FlowSetting(is_enabled=False)
        base = make_flow_plant_class(rodside.make_plant_class(self.cl), off)
        self.plant = harness_hydraulics.make_hydraulics_plant_class(base, options)(
            "top", 0.0, 0.0, Fs=0.0)
        self.plant.step(np.zeros(4), int(round(self.cl.rcc.SETTLE_ON_CRAWLER_S / self.plant.dt)))
        self.plant.t = 0.0
        self.valve = np.zeros(4)
        self.lag_steps = round(self.cl.LAG_CHUNK_S / self.plant.dt)

    def chunk(self, command: np.ndarray) -> np.ndarray:
        """One 1 ms chunk as the harness runs it (damping by the valve, lagged step)."""
        plant = self.plant
        plant.cn = np.where(np.abs(self.valve) > 1e-6, self.c_move, self.c_lock)
        return self.cl._lagged_step(plant, np.asarray(command, float), self.valve, self.lag_steps)

    def run(self, command, duration_s: float) -> list[np.ndarray]:
        forces = []
        for _ in range(round(duration_s / self.cl.LAG_CHUNK_S)):
            self.chunk(command)
            forces.append(self.plant.true_cyl_force().copy())
        return forces

    def lift_and_arm(self) -> None:
        """All legs up at v_max until the crawler is off, rest, arm the rod-side law."""
        up = np.full(4, self.v_max)
        t_free = None
        while self.plant.t < LIFT_LIMIT_S:
            accumulated = self.chunk(up)
            if t_free is None and float(accumulated[15]) <= 0.0:
                t_free = self.plant.t
            if t_free is not None and self.plant.t >= t_free + LIFT_EXTRA_S:
                break
        if t_free is None:
            raise RuntimeError("the crawler did not leave the ground")
        self.run(np.zeros(4), REST_S)
        self.plant.arm()


def front_left_release_force_N(options, rod_pressure_FL_Pa: float) -> float:
    """C2 / C3 on the harness: FL extends 0.25 v_max for 0.5 s from a lock, end force of FL."""
    bench = HarnessBench(options)
    bench.lift_and_arm()
    bench.plant.p_r0[FRONT_LEFT] = rod_pressure_FL_Pa
    command = np.zeros(4)
    command[FRONT_LEFT] = QUARTER * bench.v_max
    bench.run(command, MOVE_S)
    forces = bench.run(np.zeros(4), AFTER_MOVE_S)
    last = round(END_MEAN_S / bench.cl.LAG_CHUNK_S)
    return float(np.mean([row[FRONT_LEFT] for row in forces[-last:]]))


def check_m2_6() -> dict:
    """Spec M2-6: harness plant C2 - C3, FL end force difference [kN], M2 on and off."""
    from outrigger_sim.hydraulics.v5_options import HydraulicOptions

    out = {}
    for name, options in (("on", HydraulicOptions(rod_release_force=True)),
                          ("off", HydraulicOptions())):
        high = front_left_release_force_N(options, ROD_PRESSURE_RETRACT_PA)
        low = front_left_release_force_N(options, ROD_PRESSURE_EXTEND_PA)
        out[f"difference_{name}_kN"] = (high - low) / 1e3
    return out


CHECKS = {"m2_6": check_m2_6}


def _modules_outside_project() -> list[str]:
    foreign = []
    for module in list(sys.modules.values()):
        file_name = getattr(module, "__file__", None)
        if file_name is None:
            continue
        path = Path(file_name).resolve()
        if path.is_relative_to(MAIN_TREE_ROOT) and not path.is_relative_to(PROJECT_ROOT):
            foreign.append(str(path))
    return foreign


def main() -> None:
    check, out_path = sys.argv[1], Path(sys.argv[2])
    report = CHECKS[check]()
    report["foreign_modules"] = _modules_outside_project()
    out_path.write_text(json.dumps(report, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
