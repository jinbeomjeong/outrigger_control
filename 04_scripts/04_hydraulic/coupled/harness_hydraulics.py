"""Adapter: the v5 plant options on the reduced harness (spec ``v5_hydraulic_impl_spec.md`` 2.0).

It holds no controller logic. :func:`make_hydraulics_plant_class` puts the options on the
flow-limited plant the way ``harness_flow`` does; ``verdict_runs.execute(..., hydraulics=...)``
installs it. Without options no line of this module runs and the commands stay bit for bit.

Inner step of an armed plant (spec 2.0, the numbers are the rows of its table):
  5   ``_rod_force``: law, then the M2 shift of ``sref``, then the kernel (law C, friction)

M2 (spec 2.3): the harness has no tracked rod pressure, so this class solves its first-order lag.
The start is ``p_r0 - G_r / A_ann`` at the release, the target comes from
``RodChamberLegParams.moving_target_rod_pressure_Pa`` (the law is not copied here) with the net oil
force. All pressures are model values and ASSUMPTIONS.

Pressures gauge [Pa], speeds m/s, extension positive.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

SOURCE_DIR = Path(__file__).resolve().parents[3] / "03_src"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from outrigger_sim.hydraulics.check_open_delay import (  # noqa: E402
    CheckDelayCircuit,
    CheckDelayInputs,
    CheckOpenDelay,
)
from outrigger_sim.hydraulics.rod_chamber import (  # noqa: E402
    RodChamberLegParams,
    RodChamberMode,
)
from outrigger_sim.hydraulics.rod_release import RodReleaseShift  # noqa: E402
from outrigger_sim.hydraulics.v5_options import (  # noqa: E402
    LOCK_SPEED_EPS_M_S,
    HydraulicOptions,
    apply_lock_window,
    check_lock_window_meta,
    validate,
)

LEG_COUNT = 4
UNUSED_OUTER_STIFFNESS_N_M = math.inf
"""``moving_target_rod_pressure_Pa`` does not read the outer stiffness; soil rows change it."""
STROKE_LOWER_END_M = 0.0
MAX_LOGGED_LOCK_EVENTS = 2000
HARNESS_VALVE_TAU_S = 0.1
"""The harness valve lag is always on with this value (``c2py_r8d1_closed_loop.VALVE_LAG_S``)."""
_LAST_ARMED: list = [None]
"""The plant armed last in this process (the event branch runs on it), for the run record."""
_INSTALLED: dict = {}
_LAST_PRESET: list = [None]
CONTROL_PERIOD_S = 0.1
"""R8 C2 period `T` (spec 2.6: plant rule alone needs `t_c <= T`)."""
WAIT_SPEED_FACTOR = 2.0
"""Spec 2.5: a waiting leg hands the law ``2 eps`` so that it stays in its moving branch."""
TIME_TOL_S = 1.0e-9


class _RodPressureLag:
    """First-order lag of the moving rod pressure of one plant (module docstring)."""

    def __init__(self, plant) -> None:
        head_area_m2 = plant.flow_limiter.params.A_h
        self._legs = [
            RodChamberLegParams(
                head_area_m2=float(head_area_m2[i]),
                annulus_area_m2=float(plant.A_ann[i]),
                head_stiffness_N_m=float(plant.kh[i]),
                rod_stiffness_N_m=float(plant.kr[i]),
                outer_stiffness_N_m=UNUSED_OUTER_STIFFNESS_N_M,
                rod_weight_N=0.0)
            for i in range(LEG_COUNT)]
        self._keep = math.exp(-plant.dt / plant.tau)
        self.pressure_Pa = np.zeros(LEG_COUNT)

    def start(self, leg: int, pressure_Pa: float) -> None:
        self.pressure_Pa[leg] = pressure_Pa

    def relax(self, leg: int, direction: float, force_N: float) -> float:
        mode = RodChamberMode.EXT if direction > 0.0 else RodChamberMode.RET
        target_Pa = self._legs[leg].moving_target_rod_pressure_Pa(mode, force_N)
        self.pressure_Pa[leg] = target_Pa + (self.pressure_Pa[leg] - target_Pa) * self._keep
        return self.pressure_Pa[leg]


def make_hydraulics_plant_class(base: type, options: HydraulicOptions,
                                damping_N_s_m: tuple[np.ndarray, np.ndarray] | None = None) -> type:
    """Subclass of the flow-limited plant ``base`` with the v5 options.

    Args:
        base: Class from ``harness_flow.make_flow_plant_class``.
        options: The options; ``flow`` is the job of ``FlowSetting`` on the harness.
        damping_N_s_m: (locked, moving) leg dashpots; with LC the plant picks them by its lock
            state at the start of each chunk (the harness picks them by the valve output).

    Returns:
        The plant class, deep-copied state included (the event branches copy plants).
    """
    closure = options.lock_closure
    if (closure is not None or options.check_delay is not None) and damping_N_s_m is None:
        raise ValueError("LC and M1c on the harness need the locked and moving dashpots")

    class HydraulicsPlant(base):
        """Harness plant with the v5 options (module docstring)."""

        def arm(self):
            result = super().arm()
            _LAST_ARMED[0] = self
            self.rod_release = None
            if options.rod_release_force:
                self.rod_release = RodReleaseShift(self.A_ann)
                self.rod_pressure_lag = _RodPressureLag(self)
            self.lock_pending_since_s = np.full(LEG_COUNT, np.nan)
            self.lock_events = []
            self.rod_pressure_seed_Pa = np.full(LEG_COUNT, np.nan)
            self.check_delay = None
            if options.check_delay is not None:
                self.check_delay = CheckOpenDelay(options.check_delay,
                                                  _check_delay_circuit(self.flow_limiter.params))
            return result

        def step(self, u, nsteps):
            if not self.armed:
                return super().step(u, nsteps)
            if closure is not None:
                # spec 2.5: the dashpot follows the law's lock state, not the valve output
                self.cn = np.where(self.locked, damping_N_s_m[0], damping_N_s_m[1])
            if self.check_delay is None:
                return super().step(u, nsteps)
            return self._step_with_check_delay(np.asarray(u, float), nsteps)

        def _step_with_check_delay(self, u: np.ndarray, nsteps: int):
            """Spec 2.0 rows 3 and 6: M1c in front of the flow limit, its shift after the chunk
            (the order of ``m1c_plant.M1cPlant.step``)."""
            output = self.check_delay.filter(self._check_delay_inputs(u, nsteps))
            for i in np.flatnonzero(output.creep_shift_m != 0.0):
                self.sref[i] -= output.creep_shift_m[i]
                if self.locked[i]:
                    self.c_lock[i] -= output.creep_shift_m[i]
            for i in np.flatnonzero(output.lock_damping):
                self.cn = np.array(self.cn, float)
                self.cn[i] = damping_N_s_m[0][i]
            for i in np.flatnonzero(np.isfinite(output.opening_rod_pressure_Pa)):
                self._seed_rod_pressure(int(i), float(output.opening_rod_pressure_Pa[i]))
            accumulated = super().step(output.speed_m_s, nsteps)
            if output.opening_shift_m.any():
                self.sref -= output.opening_shift_m
            return accumulated

        def _check_delay_inputs(self, u: np.ndarray, nsteps: int) -> CheckDelayInputs:
            rod_Pa = (np.asarray(self.p_r0, float) - np.asarray(self.Gr, float)
                      / np.asarray(self.A_ann, float))
            head_Pa = (self.pressure() + rod_Pa * self.A_ann) / self.check_delay.A_h
            knee_m = (self.p_r0 - self.p_floor) * self.A_ann / self.kr
            void_m = np.where(self.locked,
                              np.maximum(self.sref - self.x - self.c_lock - knee_m, 0.0), 0.0)
            band_N = np.asarray(self.Fs, float) - np.asarray(self.f, float)
            return CheckDelayInputs(self.t, nsteps * self.dt, u, head_Pa, rod_Pa, self.locked,
                                    void_m, band_N, self.sref)

        def _seed_rod_pressure(self, leg: int, pressure_Pa: float) -> None:
            """Spec 2.4: M2 starts its release at the M1c opening pressure (no double creep)."""
            if self.rod_release is None:
                return
            self.rod_pressure_seed_Pa[leg] = pressure_Pa
            self.rod_release.seed_pressure(leg, pressure_Pa)

        def _rod_force(self, u):
            was_locked = self.locked.copy()
            if closure is not None:
                u = self._closing_delay_speed(np.asarray(u, float))
            rod_force_N = super()._rod_force(u)
            self._record_lock_changes(was_locked)
            if self.rod_release is not None:
                self._shift_reference_for_rod_pressure(rod_force_N, was_locked)
            return rod_force_N

        def _closing_delay_speed(self, u: np.ndarray) -> np.ndarray:
            """Spec 2.5 timer: a leg whose flow stopped stays in the moving law for ``t_c``.

            The law gets ``2 eps`` in its last direction while the leg waits (the kernel still
            gets ``u = 0``), then 0, so it locks ``t_c`` after the cut; a command inside the wait
            releases without a lock (H5).
            """
            law_speed = u.copy()
            for i in range(LEG_COUNT):
                if self.locked[i] or abs(u[i]) > self.eps:
                    self.lock_pending_since_s[i] = np.nan
                    continue
                if np.isnan(self.lock_pending_since_s[i]):
                    self.lock_pending_since_s[i] = self.t
                if self.t - self.lock_pending_since_s[i] < closure.closing_delay_s - TIME_TOL_S:
                    law_speed[i] = WAIT_SPEED_FACTOR * self.eps * self.last_dir[i]
            return law_speed

        def _record_lock_changes(self, was_locked) -> None:
            for i in np.flatnonzero(self.locked != was_locked):
                self.lock_events.append((round(float(self.t), 6), int(i), bool(self.locked[i])))

        def _shift_reference_for_rod_pressure(self, rod_force_N, was_locked) -> None:
            """Spec 2.3: M2 on the state after the law; acts from this inner step on."""
            pressure_Pa = self.p_r0 - rod_force_N / self.A_ann
            net_force_N = self.pressure()
            lag = self.rod_pressure_lag
            for i in np.flatnonzero(~self.locked):
                if was_locked[i]:
                    seed_Pa = self.rod_pressure_seed_Pa[i]
                    lag.start(i, float(pressure_Pa[i] if np.isnan(seed_Pa) else seed_Pa))
                    self.rod_pressure_seed_Pa[i] = np.nan
                pressure_Pa[i] = lag.relax(i, float(self.last_dir[i]), float(net_force_N[i]))
            shift_m = self.rod_release.shift_m(
                pressure_Pa, self.kh, ~self.locked, STROKE_LOWER_END_M - self.sref,
                self.geo.stroke - self.sref)
            self.sref += shift_m

    HydraulicsPlant.v5_options = options
    return HydraulicsPlant


def install_overlap_cut(closed_loop_module, setting, v_max_m_s: float, zero_command_m_s: float):
    """Spec 2.5 on the harness: replace ``closed_loop_module._lagged_step`` by one that stops the
    chunk mean valve speed of a zero command at or below ``u_ol`` (``install_command_clip``
    precedent; the ``is_*`` markers stay). The valve state keeps decaying."""
    lagged_step = closed_loop_module._lagged_step
    overlap_speed = setting.overlap_speed_m_s(v_max_m_s)

    class _CutPlant:
        """The plant as ``_lagged_step`` sees it: ``step`` gets the cut chunk mean speed."""

        def __init__(self, plant, command):
            self._plant, self._command, self.dt = plant, command, plant.dt

        def step(self, mean_speed, nsteps):
            cut = ((np.abs(self._command) <= zero_command_m_s)
                   & (np.abs(mean_speed) <= overlap_speed) & (mean_speed != 0.0))
            return self._plant.step(np.where(cut, 0.0, mean_speed), nsteps)

    def lagged_step_with_overlap_cut(plant, command, valve, steps):
        return lagged_step(_CutPlant(plant, np.asarray(command, float)), command, valve, steps)

    markers = {name: value for name, value in getattr(lagged_step, "__dict__", {}).items()
               if name.startswith("is_")}
    lagged_step_with_overlap_cut.__dict__.update(markers)
    closed_loop_module._lagged_step = lagged_step_with_overlap_cut


def plant_record(plant) -> dict:
    """Per-leg v5 totals of one plant for the result (M2 shift, clipped steps)."""
    if plant is None:
        return {}
    record = {}
    if getattr(plant, "rod_release", None) is not None:
        record.update(plant.rod_release.record())
    if getattr(plant, "lock_events", None) is not None:
        record["lock_events"] = plant.lock_events[:MAX_LOGGED_LOCK_EVENTS]
    if getattr(plant, "check_delay", None) is not None:
        record["check_delay"] = plant.check_delay.summary()
    return record


def _check_delay_circuit(params) -> CheckDelayCircuit:
    """The M1c circuit from the harness parameters (``params.py``, as ``m1c_plant.M1cState``)."""
    return CheckDelayCircuit(head_area_m2=np.asarray(params.A_h, float),
                             annulus_area_m2=np.asarray(params.A_r, float),
                             stroke_m=float(params.stroke), rod_dead_length_m=float(params.L0r),
                             head_dead_length_m=float(params.L0h),
                             bulk_modulus_Pa=float(params.beta), tank_pressure_Pa=float(params.p_T),
                             max_speed_m_s=float(params.v_max),
                             compensator_drop_Pa=float(params.dp_comp))


def options_of(plant) -> HydraulicOptions:
    return getattr(type(plant), "v5_options", HydraulicOptions())


def last_armed_record() -> dict:
    return plant_record(_LAST_ARMED[0])


def install(verdict_runs_module, options: HydraulicOptions) -> None:
    """Every plant built from now on in this process carries ``options``.

    The patch stays for the rest of the process, so a worker runs one such case.

    Raises:
        ValueError: Options the harness takes elsewhere or does not have.
    """
    if options.flow is not None:
        raise ValueError("the harness flow limit is the FlowSetting of the run, not options.flow")
    validate(options, period_s=CONTROL_PERIOD_S)
    if options.valve_tau_s is not None and options.valve_tau_s != HARNESS_VALVE_TAU_S:
        raise ValueError(f"the harness valve lag is fixed at {HARNESS_VALVE_TAU_S} s")
    if _INSTALLED.get(id(verdict_runs_module)) is not None:
        if _INSTALLED[id(verdict_runs_module)] != options:
            raise RuntimeError("other v5 options are installed in this process already")
        return
    _INSTALLED[id(verdict_runs_module)] = options
    make_flow_plant_class = verdict_runs_module.make_flow_plant_class
    import s9_soil_closed_loop as soil
    from params import load_params

    damping = (soil.C_LOCK, soil.C_MOVE)
    if options.lock_closure is not None:
        install_overlap_cut(soil._imports()[0], options.lock_closure, load_params().v_max,
                            LOCK_SPEED_EPS_M_S)

    def make_class(base, setting):
        return make_hydraulics_plant_class(make_flow_plant_class(base, setting), options, damping)

    if options.lock_window_follows_plant:
        install_lock_window(options, load_params().v_max)

    verdict_runs_module.make_flow_plant_class = make_class


def install_lock_window(options: HydraulicOptions, v_max_m_s: float) -> None:
    """Every ``C2Config.with_10hz_d1`` preset of this process gets the plant lock window
    (spec 2.6; ``acc_common.py`` precedent). Once per process; the last preset is kept for the
    meta check (:func:`check_last_lock_window`)."""
    from outrigger_sim.control import c2

    if getattr(c2.C2Config, "_v5_lock_window", None) is not None:
        if c2.C2Config._v5_lock_window != options:
            raise RuntimeError("another lock window is installed in this process already")
        return
    preset = c2.C2Config.with_10hz_d1

    def with_10hz_d1(self, *args, **kwargs):
        config = apply_lock_window(preset(self, *args, **kwargs), options, v_max_m_s,
                                   HARNESS_VALVE_TAU_S)
        _LAST_PRESET[0] = config
        return config

    c2.C2Config.with_10hz_d1 = with_10hz_d1
    c2.C2Config._v5_lock_window = options


def check_last_lock_window(options: HydraulicOptions, v_max_m_s: float) -> None:
    """Criteria P-4: the preset the run built carries the window of ``options``.

    Raises:
        RuntimeError: No preset was built, or its meta differs.
    """
    if _LAST_PRESET[0] is None:
        raise RuntimeError("no C2 preset was built with the lock window installed")
    check_lock_window_meta(_LAST_PRESET[0].two_pressure.to_meta(), options, v_max_m_s,
                           HARNESS_VALVE_TAU_S)
