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


LIFTED_LEG = 1
"""M2-14: FR, the leg of the independent two-chamber model (hydraulics-expert P-1)."""
LIFT_LOCK_FORCE_N = 116.106e3
"""FR static cylinder force of the independent model."""
ROD_WEIGHT_N = 150.0 * 9.81
"""Rod and pad weight of the independent model (ASSUMPTION there, kept for the same kick)."""
FLOOR_STIFFNESS_N_M = 2.0e8
GROUND_DROP_M, GROUND_DROP_S = 0.024, 0.3
"""The floor under FR falls 24 mm along a 3-4-5 polynomial: the locked leg lifts off."""
RELEASE_AT_S = 0.17
KICK_END_S = 1.2
KERNEL_STEP_S = 5.0e-4
M2_14_SPEEDS = (0.25, 1.0)
"""Command fractions of v_max of the independent model cases."""


def _poly345(fraction: float) -> float:
    x = min(max(fraction, 0.0), 1.0)
    return x**3 * (10.0 - 15.0 * x + 6.0 * x * x)


class _BodyFixedLegs:
    """Harness kernel stand-in for M2-14: per leg a massless rod between the oil spring
    ``k_h (s_ref - x)`` and a pad on a stiff floor; the body (cylinder barrels) stays put.

    It offers what ``RodSidePlant`` and the v5 adapter read of the harness ``FlexPlant``.
    """

    def __init__(self, floor_move_m: float = GROUND_DROP_M,
                 floor_move_s: float = GROUND_DROP_S) -> None:
        import dyn_model as dm
        import l2b_reference as l2b
        from params import load_params

        p = dm.load_params()
        self.geo = dm.geometry_from_params(p)
        legs = l2b.leg_parameters(p, self.geo)
        extension_m = np.zeros(4) + np.asarray(legs["e_op"], float)
        self.ko = np.asarray(legs["k_h_f"](extension_m), float)
        circuit = load_params()  # the M1c circuit of the harness (``_check_delay_circuit``)
        self.flow_limiter = _Namespace(params=_Namespace(
            A_h=np.asarray(legs["A_p"], float), A_r=circuit.A_r, stroke=circuit.stroke,
            L0r=circuit.L0r, L0h=circuit.L0h, beta=circuit.beta, p_T=circuit.p_T,
            v_max=circuit.v_max, dp_comp=circuit.dp_comp))
        self.floor_move_m, self.floor_move_s = floor_move_m, floor_move_s
        self.Fs = np.zeros(4)
        self.f = np.zeros(4)
        """No seal friction (M2-14b, M2-14c: F_s 0)."""
        self.cn = np.zeros(4)
        """Dashpot the adapter sets; the massless rods here do not use it."""
        self.dt = KERNEL_STEP_S
        self.t = 0.0
        self.x = extension_m.copy()
        self.sref = self.x + (LIFT_LOCK_FORCE_N - ROD_WEIGHT_N) / self.ko
        self.floor_start_m = self.x - LIFT_LOCK_FORCE_N / FLOOR_STIFFNESS_N_M
        self.acc = np.zeros(32)
        self.hist_t, self.hist = [], []

    def floor_m(self, t_s: float) -> np.ndarray:
        floor = self.floor_start_m.copy()
        floor[LIFTED_LEG] += self.floor_move_m * _poly345(t_s / self.floor_move_s)
        return floor

    def step(self, u, nsteps: int) -> np.ndarray:
        for _ in range(nsteps):
            self.t += self.dt
            self.sref = self.sref + np.asarray(u, float) * self.dt
            floor = self.floor_m(self.t)
            free = self.sref + ROD_WEIGHT_N / self.ko
            pressed = ((self.ko * self.sref + ROD_WEIGHT_N + FLOOR_STIFFNESS_N_M * floor)
                       / (self.ko + FLOOR_STIFFNESS_N_M))
            self.x = np.where(free <= floor, free, pressed)
        return self.acc[:24]


class _Namespace:
    def __init__(self, **values) -> None:
        self.__dict__.update(values)


def _lifted_leg_plant(options, floor_move_m: float = GROUND_DROP_M,
                      floor_move_s: float = GROUND_DROP_S):
    import importlib

    importlib.import_module("verdict_runs")  # first: it puts the harness folders on sys.path
    import harness_hydraulics

    rodside = importlib.import_module("s8_g4_rodside_check")
    rodside._setup_path()
    # the kernel stand-in has no dashpot: M1c only needs the arrays to exist
    dashpots = (np.zeros(4), np.zeros(4)) if options.check_delay is not None else None
    plant_class = harness_hydraulics.make_hydraulics_plant_class(
        rodside.make_plant_class(_Namespace(rmf=_Namespace(FlexPlant=_BodyFixedLegs))), options,
        dashpots)
    plant = plant_class(floor_move_m, floor_move_s)
    plant.arm()
    return plant


def _lifted_leg_release(options, fraction: float, v_max_m_s: float) -> dict:
    """FR lifts off while locked, then extends from ``RELEASE_AT_S`` at ``fraction`` v_max
    through the 0.1 s valve lag; kick = pad travel beyond the integrated speed at 1.2 s."""
    from outrigger_sim.hydraulics.rod_chamber import RodChamberMode
    from outrigger_sim.hydraulics.rod_release import release_weight

    plant = _lifted_leg_plant(options)
    leg = LIFTED_LEG
    speed_m_s = np.zeros(4)
    travel_m, x_before_m, lock_pressure_Pa, worst_form_Pa = 0.0, None, None, 0.0
    rod_pressure_at_release_Pa = None
    for _ in range(round(KICK_END_S / KERNEL_STEP_S)):
        t_s = plant.t
        speed_m_s[leg] = 0.0
        if t_s >= RELEASE_AT_S:
            speed_m_s[leg] = fraction * v_max_m_s * (1.0 - np.exp(-(t_s - RELEASE_AT_S)
                                                                  / VALVE_TAU_S))
        if x_before_m is None and abs(speed_m_s[leg]) > plant.eps:
            x_before_m = float(plant.x[leg])
            lock_pressure_Pa = float(plant.p_r0[leg])
            rod_pressure_at_release_Pa = float(plant.p_r0[leg] - plant.Gr[leg] / plant.A_ann[leg])
        plant.step(speed_m_s.copy(), 1)
        travel_m += speed_m_s[leg] * KERNEL_STEP_S
        release = getattr(plant, "rod_release", None)
        if release is not None and not plant.locked[leg]:
            weighted_Pa = release.release_drop_Pa[leg] * release_weight(
                t_s - float(plant.t_rel[leg]), float(plant.tau))
            worst_form_Pa = max(worst_form_Pa,
                                abs(weighted_Pa - float(plant.Gr[leg] / plant.A_ann[leg])))
    out = {"kick_mm": (float(plant.x[leg]) - x_before_m - travel_m) * 1e3,
           "rod_pressure_at_release_bar": rod_pressure_at_release_Pa / BAR,
           "lock_pressure_bar": lock_pressure_Pa / BAR}
    if release is not None:
        lag_leg = plant.rod_pressure_lag._legs[leg]
        target_Pa = lag_leg.moving_target_rod_pressure_Pa(RodChamberMode.EXT,
                                                         float(plant.pressure()[leg]))
        out.update({"m2_total_mm": float(release.shift_total_m[leg]) * 1e3,
                    "expected_total_mm": float(plant.A_ann[leg] * (lock_pressure_Pa - target_Pa)
                                               / plant.kh[leg]) * 1e3,
                    "target_bar": target_Pa / BAR,
                    "max_delta_w_minus_gr_over_a_Pa": worst_form_Pa})
    return out


def check_m2_14() -> dict:
    """Spec M2-14 (revision 4): a lifted FR leg released on the harness plant law with a fixed
    body. M2 total = ``A_ann (p_r0 - p*) / k_h``; kick within 5 % of the independent two-chamber
    model (1.0556 mm at 0.25 v_max, 1.0305 mm at v_max). M2 off gives the base decay alone."""
    from params import load_params

    from outrigger_sim.hydraulics.v5_options import HydraulicOptions

    v_max_m_s = load_params().v_max
    out = {}
    for fraction in M2_14_SPEEDS:
        for name, options in (("on", HydraulicOptions(rod_release_force=True)),
                              ("off", HydraulicOptions())):
            out[f"{name}_{fraction}"] = _lifted_leg_release(options, fraction, v_max_m_s)
    return out


CHUNK_STEPS = 2
"""M2-14b, M2-14c: M1c filters each 1 ms chunk (2 kernel steps), as the replica does."""
FLOOR_RISE_M, FLOOR_RISE_S = -0.0005, 0.05
"""M2-14c: the floor under FR rises 0.5 mm while it is locked (load up, Delta 2.91 bar)."""
M1C_KINDS = ("VN", "BL")


class _M1cRecorder:
    """Wraps ``plant.check_delay.filter`` and ``plant.rod_release.release`` of one plant: the
    delivered speed, the creep and opening shifts of the leg, and the release start."""

    def __init__(self, plant, leg: int) -> None:
        self.leg = leg
        self.delivered_m_s = None
        self.creep_m = 0.0
        self.opening_m = 0.0
        self.release_start = None
        if plant.check_delay is not None:
            self._filter = plant.check_delay.filter
            plant.check_delay.filter = self._recorded_filter
        self._release = plant.rod_release.release
        plant.rod_release.release = self._recorded_release

    def _recorded_filter(self, inputs):
        output = self._filter(inputs)
        self.delivered_m_s = float(output.speed_m_s[self.leg])
        self.creep_m += float(output.creep_shift_m[self.leg])
        self.opening_m += float(output.opening_shift_m[self.leg])
        return output

    def _recorded_release(self, leg, start) -> None:
        if leg == self.leg:
            self.release_start = start
        self._release(leg, start)


def _release_with_m1c(options, fraction: float, v_max_m_s: float, floor_move_m: float,
                      floor_move_s: float) -> dict:
    """FR locked while its floor moves, then a command of ``fraction`` v_max (negative =
    retract) from ``RELEASE_AT_S`` through the 0.1 s valve lag, in 1 ms chunks (M2-14b, 14c)."""
    from outrigger_sim.hydraulics.rod_release import release_weight

    plant = _lifted_leg_plant(options, floor_move_m, floor_move_s)
    leg = LIFTED_LEG
    recorder = _M1cRecorder(plant, leg)
    chunk_s = CHUNK_STEPS * KERNEL_STEP_S
    command_m_s = np.zeros(4)
    commanded_m, delivered_m = 0.0, 0.0
    x_before_m, release_t_s = None, None
    for _ in range(round(KICK_END_S / chunk_s)):
        t_s = plant.t
        command_m_s[leg] = 0.0
        if t_s >= RELEASE_AT_S:
            command_m_s[leg] = fraction * v_max_m_s * (1.0 - np.exp(-(t_s - RELEASE_AT_S)
                                                                    / VALVE_TAU_S))
        was_locked, x_chunk_start_m = bool(plant.locked[leg]), float(plant.x[leg])
        recorder.delivered_m_s = None
        plant.step(command_m_s.copy(), CHUNK_STEPS)
        delivered_m_s = (command_m_s[leg] if recorder.delivered_m_s is None
                         else recorder.delivered_m_s)
        commanded_m += command_m_s[leg] * chunk_s
        delivered_m += delivered_m_s * chunk_s
        if was_locked and not plant.locked[leg] and release_t_s is None:
            x_before_m, release_t_s = x_chunk_start_m, t_s  # releases at the first inner step
    release = plant.rod_release
    start = recorder.release_start
    area_m2, head_N_m = float(plant.A_ann[leg]), float(plant.kh[leg])
    end_Pa = float(plant.rod_pressure_lag.pressure_Pa[leg])
    drop_Pa = float(release.release_drop_Pa[leg])
    weight_end = release_weight(plant.t - plant.dt - float(plant.t_rel[leg]), float(plant.tau))
    m2_total_m = float(release.shift_total_m[leg])
    kernel_Pa = (float(plant.p_r0[leg]) - float(plant.Gr[leg]) / area_m2
                 - head_N_m / area_m2 * (m2_total_m - recorder.creep_m))
    return {
        "release_delay_ms": (release_t_s - RELEASE_AT_S) * 1e3,
        "start_bar": start.start_pressure_Pa / BAR, "delta_bar": start.drop_Pa / BAR,
        "rod_pressure_at_release_bar": (float(plant.p_r0[leg]) - start.drop_Pa) / BAR,
        "end_bar": end_Pa / BAR, "weight_end": weight_end,
        "m2_total_mm": m2_total_m * 1e3,
        "formula_total_mm": area_m2 * (start.start_pressure_Pa + drop_Pa - end_Pa
                                       - drop_Pa * weight_end) / head_N_m * 1e3,
        "kick_vs_delivered_mm": (float(plant.x[leg]) - x_before_m - delivered_m) * 1e3,
        "lost_stroke_mm": (commanded_m - delivered_m) * 1e3,
        "creep_mm": -recorder.creep_m * 1e3, "opening_shift_mm": recorder.opening_m * 1e3,
        "kernel_minus_tracked_bar": (kernel_Pa - end_Pa) / BAR,
    }


def check_m2_14b() -> dict:
    """Spec M2-14b (hydraulics-expert 2026-11-07): the M2-14 lift-off with M1c VN / BL (and
    without M1c for the kick difference). Extension re-approach: no seed, start = p_r,rel."""
    from params import load_params

    from outrigger_sim.hydraulics.v5_options import CheckDelaySetting, HydraulicOptions

    v_max_m_s = load_params().v_max
    out = {}
    for fraction in M2_14_SPEEDS:
        out[f"off_{fraction}"] = _release_with_m1c(
            HydraulicOptions(rod_release_force=True), fraction, v_max_m_s, GROUND_DROP_M,
            GROUND_DROP_S)
        for kind in M1C_KINDS:
            options = HydraulicOptions(rod_release_force=True,
                                       check_delay=CheckDelaySetting(kind))
            out[f"{kind}_{fraction}"] = _release_with_m1c(options, fraction, v_max_m_s,
                                                          GROUND_DROP_M, GROUND_DROP_S)
    return out


def check_m2_14c() -> dict:
    """Spec M2-14c (optional): FR loaded while locked (floor +0.5 mm), then 0.25 v_max retract
    with M1c VN / BL: creep, seed and the kernel pressure invariant at 1.2 s."""
    from params import load_params

    from outrigger_sim.hydraulics.v5_options import CheckDelaySetting, HydraulicOptions

    v_max_m_s = load_params().v_max
    return {kind: _release_with_m1c(
        HydraulicOptions(rod_release_force=True, check_delay=CheckDelaySetting(kind)),
        -0.25, v_max_m_s, FLOOR_RISE_M, FLOOR_RISE_S) for kind in M1C_KINDS}


ANCHOR_START_PA = 34.818 * BAR
"""Revision 5 units: the extension starts from a retract lock anchor (spec table)."""
ANCHOR_REFERENCE_STEP_S = 1.0e-4
"""The 1-leg replica of the spec runs at the L2b step."""
ANCHOR_HOLD_S = 0.05
ANCHOR_LOAD_RISE_M, ANCHOR_LOAD_RISE_S = -3.0e-3, 3.0
"""After the lock the floor under the leg rises 3 mm in 3 s: the rod reading reaches the floor
pressure (the knee) well before the end."""
HANGING_FORCE_N = 40.0e3
"""U4: the leg hangs with this net pull (``F = -40 kN``)."""
FREE_FLOOR_M = 1.0
ANCHOR_CASES = (
    ("U1", 0, 0.01, 0.5, False), ("U1", 2, 0.01, 0.5, False),
    ("U2", 0, 0.10, 0.1, False), ("U2", 2, 0.10, 0.1, False),
    ("U2b", 0, 0.01, 1.0, False),
    ("U3", 0, 0.01, 5.0, False), ("U3", 2, 0.01, 5.0, False),
    ("U3b", 0, 0.25, 0.1, False),
    ("U4", 0, 0.01, 1.0, True),
)
"""(name, leg, fraction of v_max, extension time [s], hanging): spec ``r5_spec.md`` table."""


class _AnchorLegs(_BodyFixedLegs):
    """``_BodyFixedLegs`` with one chosen leg whose floor rises from ``rise_from_s`` on, or
    which hangs free with a pull of :data:`HANGING_FORCE_N` (the stand-in rod weight)."""

    def __init__(self, leg: int, is_hanging: bool) -> None:
        super().__init__(floor_move_m=0.0, floor_move_s=1.0)
        self.leg = leg
        self.rise_from_s = np.inf
        self.rod_weight_N = np.full(4, ROD_WEIGHT_N)
        self.is_hanging = is_hanging
        if is_hanging:
            self.rod_weight_N[leg] = HANGING_FORCE_N
            self.floor_start_m[leg] = FREE_FLOOR_M

    def floor_m(self, t_s: float) -> np.ndarray:
        floor = self.floor_start_m.copy()
        if t_s > self.rise_from_s:
            floor[self.leg] += ANCHOR_LOAD_RISE_M * _poly345(
                (t_s - self.rise_from_s) / ANCHOR_LOAD_RISE_S)
        return floor

    def step(self, u, nsteps: int) -> np.ndarray:
        for _ in range(nsteps):
            self.t += self.dt
            self.sref = self.sref + np.asarray(u, float) * self.dt
            floor = self.floor_m(self.t)
            free = self.sref + self.rod_weight_N / self.ko
            pressed = ((self.ko * self.sref + self.rod_weight_N + FLOOR_STIFFNESS_N_M * floor)
                       / (self.ko + FLOOR_STIFFNESS_N_M))
            self.x = np.where(free <= floor, free, pressed)
        return self.acc[:24]


def _anchor_plant(options, leg: int, is_hanging: bool):
    import importlib

    importlib.import_module("verdict_runs")  # first: it puts the harness folders on sys.path
    import harness_hydraulics

    rodside = importlib.import_module("s8_g4_rodside_check")
    rodside._setup_path()
    plant_class = harness_hydraulics.make_hydraulics_plant_class(
        rodside.make_plant_class(_Namespace(rmf=_Namespace(FlexPlant=_AnchorLegs))), options)
    plant = plant_class(leg, is_hanging)
    plant.step(np.zeros(4), 1)  # not armed yet: settles x of a hanging leg
    plant.arm()
    plant.p_r0[leg] = ANCHOR_START_PA
    return plant


def _extension_target_Pa(plant, leg: int) -> float:
    from outrigger_sim.hydraulics.rod_chamber import RodChamberMode

    pull_N = HANGING_FORCE_N if plant.is_hanging else 0.0
    return plant.rod_pressure_lag._legs[leg].moving_target_rod_pressure_Pa(RodChamberMode.EXT,
                                                                           -pull_N)


def _anchor_replica_Pa(plant, leg: int, speed_m_s: float, duration_s: float,
                       step_s: float) -> float:
    """1-leg replica of the extension lag at the harness ``k_h``, ``k_r`` (fixed at e_op)."""
    from outrigger_sim.hydraulics.rod_release import RodPressureFlowLaw

    params = plant.rod_pressure_lag._legs[leg]
    law = RodPressureFlowLaw()
    compliance = law.rod_compliance_m3_Pa(params.annulus_area_m2, params.head_stiffness_N_m,
                                          params.rod_stiffness_N_m)
    target_Pa = _extension_target_Pa(plant, leg)
    pressure_Pa = ANCHOR_START_PA
    for _ in range(round(duration_s / step_s)):
        pressure_Pa = law.rod_pressure_Pa(pressure_Pa, target_Pa, speed_m_s, step_s,
                                          float(plant.tau), compliance, params.head_area_m2,
                                          params.annulus_area_m2, is_retract=False)
    return pressure_Pa


def _knee_force_N(plant, leg: int, anchor_Pa: float) -> float:
    """Spec ``dF_knee = (p_r0 - p_floor) A_ann (k_h + k_r) / k_r``."""
    return float((anchor_Pa - plant.p_floor) * plant.A_ann[leg]
                 * (plant.kh[leg] + plant.kr[leg]) / plant.kr[leg])


def _measured_knee_force_N(plant, leg: int) -> float | None:
    """Load the locked leg up (floor rise) until its rod reading clamps at ``p_floor``; the
    force change from the lock to the clamp, extrapolated on the last two unclamped steps."""
    plant.rise_from_s = plant.t
    force_lock_N = float(plant.pressure()[leg])
    samples = []
    for _ in range(round(ANCHOR_LOAD_RISE_S / plant.dt)):
        plant.step(np.zeros(4), 1)
        rod_Pa = float(plant.p_r0[leg] - plant.Gr[leg] / plant.A_ann[leg])
        if rod_Pa <= plant.p_floor + 1e-6:
            if len(samples) < 2:
                return None
            (force_a, rod_a), (force_b, rod_b) = samples[-2], samples[-1]
            slope = (force_b - force_a) / (rod_b - rod_a)
            return force_b + slope * (plant.p_floor - rod_b) - force_lock_N
        samples.append((float(plant.pressure()[leg]), rod_Pa))
    return None


def _anchor_case(options, leg: int, fraction: float, duration_s: float, is_hanging: bool,
                 v_max_m_s: float) -> dict:
    """Extend ``leg`` at ``fraction`` v_max (a step, no valve lag: the replica's constant u)
    for ``duration_s`` from the 34.818 bar anchor, then lock; the anchor, the lock step force
    and (pressed legs) the knee measured by loading the locked leg up."""
    plant = _anchor_plant(options, leg, is_hanging)
    speed_m_s = np.zeros(4)
    speed_m_s[leg] = fraction * v_max_m_s
    for _ in range(round(duration_s / plant.dt)):
        plant.step(speed_m_s, 1)
    tracked_Pa = (None if plant.rod_release is None
                  else float(plant.rod_pressure_lag.pressure_Pa[leg]))
    force_before_lock_N = float(plant.pressure()[leg])
    gr_before_lock_N = float(plant.Gr[leg])
    plant.step(np.zeros(4), 1)  # the lock step
    anchor_Pa = float(plant.p_r0[leg])
    out = {"locked": bool(plant.locked[leg]), "p_r0_Pa": anchor_Pa, "p_r0_bar": anchor_Pa / BAR,
           "lock_step_gr_minus_before_N": float(plant.Gr[leg]) - gr_before_lock_N,
           "lock_step_force_minus_before_N": float(plant.pressure()[leg]) - force_before_lock_N,
           "knee_formula_kN": _knee_force_N(plant, leg, anchor_Pa) / 1e3}
    if tracked_Pa is not None:
        target_Pa = _extension_target_Pa(plant, leg)
        reference_Pa = _anchor_replica_Pa(plant, leg, speed_m_s[leg], duration_s,
                                          ANCHOR_REFERENCE_STEP_S)
        reference_anchor_Pa = max(plant.p_ext[leg] + max(reference_Pa - target_Pa, 0.0),
                                  plant.p_floor)
        out.update({
            "p_tr_bar": tracked_Pa / BAR, "target_bar": target_Pa / BAR,
            "replica_p_tr_bar": reference_Pa / BAR,
            "replica_harness_step_p_tr_bar": _anchor_replica_Pa(
                plant, leg, speed_m_s[leg], duration_s, plant.dt) / BAR,
            "replica_p_r0_bar": reference_anchor_Pa / BAR,
            "replica_knee_kN": _knee_force_N(plant, leg, reference_anchor_Pa) / 1e3,
            "record": plant.anchor_record.record()})
    for _ in range(round(ANCHOR_HOLD_S / plant.dt)):
        plant.step(np.zeros(4), 1)
    if not is_hanging:
        measured_N = _measured_knee_force_N(plant, leg)
        out["measured_knee_kN"] = None if measured_N is None else measured_N / 1e3
    return out


def _retract_lock_case(options, leg: int, v_max_m_s: float) -> dict:
    """U10: 1 % v_max retract for 0.5 s from the extension anchor, then the lock."""
    plant = _anchor_plant(options, leg, is_hanging=False)
    plant.p_r0[leg] = plant.p_ext[leg]
    speed_m_s = np.zeros(4)
    speed_m_s[leg] = -0.01 * v_max_m_s
    for _ in range(round(0.5 / plant.dt)):
        plant.step(speed_m_s, 1)
    plant.step(np.zeros(4), 1)
    return {"locked": bool(plant.locked[leg]), "p_r0_Pa": float(plant.p_r0[leg]),
            "p_ret_Pa": float(plant.p_ret[leg])}


def check_anchor_r5() -> dict:
    """M2 revision 5 (spec ``r5_spec.md``): the extension lock anchor on the harness plant law
    (body fixed, kernel step 5e-4 s) against the 1-leg replica at the harness ``k_h``, ``k_r``;
    U1 with M2 off keeps ``p_ext``; U10 retract locks keep ``p_ret`` with M2 on and off."""
    from params import load_params

    from outrigger_sim.hydraulics.v5_options import HydraulicOptions

    v_max_m_s = load_params().v_max
    on, off = HydraulicOptions(rod_release_force=True), HydraulicOptions()
    out = {}
    for name, leg, fraction, duration_s, is_hanging in ANCHOR_CASES:
        out[f"{name}_{leg}"] = _anchor_case(on, leg, fraction, duration_s, is_hanging,
                                            v_max_m_s)
    for leg in (0, 2):
        out[f"U1_off_{leg}"] = _anchor_case(off, leg, 0.01, 0.5, False, v_max_m_s)
        out[f"U10_on_{leg}"] = _retract_lock_case(on, leg, v_max_m_s)
        out[f"U10_off_{leg}"] = _retract_lock_case(off, leg, v_max_m_s)
    return out


CHECKS = {"m2_6": check_m2_6, "lc": check_lc, "c8": check_c8, "x1_locked": check_x1_locked,
          "m2_14": check_m2_14, "m2_14b": check_m2_14b, "m2_14c": check_m2_14c,
          "anchor_r5": check_anchor_r5}


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
