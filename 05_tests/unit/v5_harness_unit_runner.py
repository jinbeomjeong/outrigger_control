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
S8_DIR = PROJECT_ROOT / "04_scripts" / "03_control" / "s8"
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
SETTLE_AFTER_MOVE_S = 30.0
"""M2-6 (revised 2026-11-06): stand still this long after the FL move."""
SETTLED_MEAN_FROM_S = 10.0
"""M2-6: mean of the FL force from this time after the move to the end of the rest; the
lightly damped rocking (two modes) is still a few kN at 3 s, so a 0.5 s mean there is not the
settled value."""
VALVE_TAU_S = 0.1


class HarnessBench:
    """One harness plant with the options and the chunk loop of the closed-loop harness."""

    def __init__(self, options) -> None:
        import importlib

        importlib.import_module("verdict_runs")  # first: it puts the harness folders on sys.path
        import harness_hydraulics
        from harness_flow import FlowSetting, make_flow_plant_class
        from params import load_params

        rodside = importlib.import_module("s8_g4_rodside_check")
        soil = importlib.import_module("s9_soil_closed_loop")
        self.cl = soil._imports()[0]
        self.c_lock, self.c_move = soil.C_LOCK, soil.C_MOVE
        self.v_max = load_params().v_max
        off = FlowSetting(is_enabled=False)
        base = make_flow_plant_class(rodside.make_plant_class(self.cl), off)
        if options.lock_closure is not None:
            harness_hydraulics.install_overlap_cut(self.cl, options.lock_closure, self.v_max,
                                                   harness_hydraulics.LOCK_SPEED_EPS_M_S)
        plant_class = harness_hydraulics.make_hydraulics_plant_class(
            base, options, (self.c_lock, self.c_move))
        self.plant = plant_class("top", 0.0, 0.0, Fs=0.0)
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
    """C2 / C3 on the harness: FL extends 0.25 v_max for 0.5 s from a lock, then all legs stand
    still for 30 s; settled FL force = mean over 10 .. 30 s after the move."""
    bench = HarnessBench(options)
    bench.lift_and_arm()
    bench.plant.p_r0[FRONT_LEFT] = rod_pressure_FL_Pa
    command = np.zeros(4)
    command[FRONT_LEFT] = QUARTER * bench.v_max
    bench.run(command, MOVE_S)
    forces = bench.run(np.zeros(4), SETTLE_AFTER_MOVE_S)
    first_settled = round(SETTLED_MEAN_FROM_S / bench.cl.LAG_CHUNK_S)
    return float(np.mean([row[FRONT_LEFT] for row in forces[first_settled:]]))


def check_m2_6() -> dict:
    """Spec M2-6 (revised, v5_criteria revision section to follow): harness plant C2 - C3,
    settled FL force difference [kN] (mean 10 .. 30 s after the move), M2 on and off."""
    from outrigger_sim.hydraulics.v5_options import HydraulicOptions

    out = {}
    for name, options in (("on", HydraulicOptions(rod_release_force=True)),
                          ("off", HydraulicOptions())):
        high = front_left_release_force_N(options, ROD_PRESSURE_RETRACT_PA)
        low = front_left_release_force_N(options, ROD_PRESSURE_EXTEND_PA)
        out[f"difference_{name}_kN"] = (high - low) / 1e3
    return out


TAIL_RUN_S = 1.5
OVERLAP_TABLE_S = {(0.02, 0.25): 0.253, (0.02, 1.0): 0.391}
"""Spec 2.5 hand values of t_ol - t_0 [s]."""


def _lock_closure_options(delay_s: float = 0.05):
    from outrigger_sim.hydraulics.v5_options import HydraulicOptions, LockClosureSetting

    return HydraulicOptions(lock_closure=LockClosureSetting(0.02, delay_s))


def _front_left_tail(bench: HarnessBench, fraction: float, restart_after_s: float | None = None
                     ) -> tuple[float, float | None, float | None]:
    """(t_0, first cut chunk start, first FL lock time after t_0)."""
    command = np.zeros(4)
    command[FRONT_LEFT] = fraction * bench.v_max
    bench.run(command, 1.0)
    t_zero = bench.plant.t
    rows_before = len(bench.plant.flow_limiter.rows())
    if restart_after_s is None:
        bench.run(np.zeros(4), TAIL_RUN_S)
    else:
        cut_s = t_zero + VALVE_TAU_S * np.log(fraction / 0.02)
        bench.run(np.zeros(4), cut_s + restart_after_s - t_zero)
        bench.run(command, 1.0)
    rows = bench.plant.flow_limiter.rows()[rows_before:]
    zero = np.flatnonzero(rows[:, 1 + FRONT_LEFT] == 0.0)
    cut_t = float(rows[zero[0], 0]) if zero.size else None
    locks = [t for t, leg, locked in bench.plant.lock_events
             if leg == FRONT_LEFT and locked and t >= t_zero]
    return t_zero, cut_t, (locks[0] if locks else None)


def check_lc() -> dict:
    """Spec L-1, L-4, L-5, L-7 on the harness plant (delta_ol 2 %)."""
    out = {}
    for fraction in (0.25, 1.0):
        bench = HarnessBench(_lock_closure_options())
        bench.lift_and_arm()
        t_zero, cut_t, lock_t = _front_left_tail(bench, fraction)
        out[f"l1_cut_after_zero_s_{fraction}"] = cut_t - t_zero
        out[f"l1_formula_s_{fraction}"] = VALVE_TAU_S * float(np.log(fraction / 0.02))
        out[f"l1_table_s_{fraction}"] = OVERLAP_TABLE_S[(0.02, fraction)]
    for delay_s in (0.02, 0.05, 0.10):
        bench = HarnessBench(_lock_closure_options(delay_s))
        bench.lift_and_arm()
        _, cut_t, lock_t = _front_left_tail(bench, 1.0)
        out[f"l4_lock_after_cut_s_{delay_s}"] = lock_t - cut_t
    bench = HarnessBench(_lock_closure_options())
    bench.lift_and_arm()
    _, _, lock_t = _front_left_tail(bench, 1.0, restart_after_s=0.025)
    out["l5_lock_time_after_restart"] = lock_t
    out["l7_copy_equal"] = _deepcopy_continuation_is_equal()
    return out


def _deepcopy_continuation_is_equal() -> bool:
    import copy

    bench = HarnessBench(_lock_closure_options())
    bench.lift_and_arm()
    command = np.zeros(4)
    command[FRONT_LEFT] = bench.v_max
    bench.run(command, 1.0)
    bench.run(np.zeros(4), 0.391 + 0.025)
    twin = copy.copy(bench)  # the harness modules stay shared, the plant state is copied
    twin.plant, twin.valve = copy.deepcopy(bench.plant), bench.valve.copy()
    first = bench.run(np.zeros(4), 0.5)
    second = twin.run(np.zeros(4), 0.5)
    return bool(np.array_equal(np.array(first), np.array(second))
                and bench.plant.lock_events == twin.plant.lock_events)


def check_c8() -> dict:
    """Spec C-8: M2 + M1c BL, FL retracts from a lock: creep + M2 = A_ann (p_rod - p_r) / k_h
    once, not twice (M2 starts the release at the M1c opening pressure)."""
    from outrigger_sim.hydraulics.v5_options import CheckDelaySetting, HydraulicOptions

    bench = HarnessBench(HydraulicOptions(rod_release_force=True,
                                          check_delay=CheckDelaySetting("BL")))
    bench.lift_and_arm()
    plant = bench.plant
    command = np.zeros(4)
    command[FRONT_LEFT] = -QUARTER * bench.v_max
    shifts, fills = [], []
    for _ in range(round(0.6 / bench.cl.LAG_CHUNK_S)):
        bench.chunk(command)
        shifts.append(float(plant.rod_release.shift_total_m[FRONT_LEFT]))
        fills.append(int(plant.check_delay.n_fills[FRONT_LEFT, 1]))
    opened = fills.index(1) if 1 in fills else None
    summary = plant.check_delay.summary()
    out = {"opened_chunk": opened, "creep_mm": summary["creep_mm"][FRONT_LEFT],
           "discharge_mm": summary["discharge_mm"][FRONT_LEFT]}
    if opened is not None:
        before = shifts[opened - 1] if opened > 0 else 0.0
        out["m2_first_5_chunks_mm"] = (shifts[min(opened + 5, len(shifts) - 1)] - before) * 1e3
        out["m2_to_end_mm"] = (shifts[-1] - before) * 1e3
    return out


def check_x1_locked() -> dict:
    """v5 X-1 (5): with LC the ``plant.locked`` that the r79 ``DynMapRodModel`` reads follows
    the closing-delay timer: FL extends at v_max for 1 s, then a zero command; the first chunk
    end with ``plant.locked[FL]`` True is compared with the cut chunk and the lock event."""
    delay_s = 0.05
    bench = HarnessBench(_lock_closure_options(delay_s))
    sys.path.append(str(S8_DIR))  # after the harness folders: only r79 comes from here
    import r79_sensor_screen as r79

    bench.lift_and_arm()
    command = np.zeros(4)
    command[FRONT_LEFT] = bench.v_max
    bench.run(command, 1.0)
    t_zero = bench.plant.t
    rows_before = len(bench.plant.flow_limiter.rows())
    rod_model = r79.DynMapRodModel()
    locked_times, locked_reads, locked_values = [], [], []
    for _ in range(round(TAIL_RUN_S / bench.cl.LAG_CHUNK_S)):
        bench.chunk(np.zeros(4))
        rod_model.step_chunk(bench.plant, bench.valve, bench.cl.LAG_CHUNK_S)
        if bench.plant.locked[FRONT_LEFT] and not locked_times:
            locked_times.append(bench.plant.t)
            locked_reads.append(float(rod_model.rod_Pa[FRONT_LEFT]))
            locked_values.append(float(rod_model.locked_value_Pa(bench.plant)[FRONT_LEFT]))
    rows = bench.plant.flow_limiter.rows()[rows_before:]
    zero = np.flatnonzero(rows[:, 1 + FRONT_LEFT] == 0.0)
    cut_t = float(rows[zero[0], 0]) if zero.size else None
    locks = [t for t, leg, locked in bench.plant.lock_events
             if leg == FRONT_LEFT and locked and t >= t_zero]
    return {"cut_t": cut_t, "first_locked_chunk_end": locked_times[0] if locked_times else None,
            "lock_event_t": locks[0] if locks else None, "delay_s": delay_s,
            "rod_reading_at_lock_Pa": locked_reads[0] if locked_reads else None,
            "locked_value_Pa": locked_values[0] if locked_values else None}


CHECKS = {"m2_6": check_m2_6, "lc": check_lc, "c8": check_c8, "x1_locked": check_x1_locked}


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
