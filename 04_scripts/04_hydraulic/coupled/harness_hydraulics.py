"""Adapter: the v5 plant options on the reduced harness (spec ``v5_hydraulic_impl_spec.md`` 2.0).

It holds no controller logic. :func:`make_hydraulics_plant_class` puts the options on the
flow-limited plant the way ``harness_flow`` does; ``verdict_runs.execute(..., hydraulics=...)``
installs it. Without options no line of this module runs and the commands stay bit for bit.

Inner step of an armed plant (spec 2.0, the numbers are the rows of its table):
  5   ``_rod_force``: law, then the M2 shift of ``sref``, then the kernel (law C, friction)

M2 (spec 2.3): the harness has no tracked rod pressure, so this class solves its first-order lag.
The start is ``p_r0 - G_r / A_ann`` at the release, the target comes from
``RodChamberLegParams.moving_target_rod_pressure_Pa`` (the law is not copied here) with the net oil
force. Revision 3: the lag is capped by the valve flow of the kernel speed
(``rod_release.flow_limited_rod_pressure``, the function L2b calls), ``C_r`` from ``kh``, ``kr``.
Revision 4 (``flow_limited_r4``, 2026-11-07): the base release decay ``Gr = r0 exp(-(t - t_rel) /
tau)`` of ``RodSidePlant`` already moves ``Gr / k_h``, so M2 reads ``p_hat = p + Delta w`` with
``Delta = Gr(t_rel) / A_ann`` (set at the release) and ``w = exp(-(t - t_rel) / tau)`` (the same
``tau``): ``Delta w`` equals ``Gr / A_ann`` of every moving step. Revision 5 (``flow_limited_r5``,
2026-11-07, plan B): a leg that locks after an extension gets the anchor
``p_r0 = max(min(p_tr, p_ext + max(p_tr - p*, 0)), p_floor)`` instead of ``p_ext`` (``p_tr``
the lag of the last moving step, ``p*`` the extension target of the lock step's net force); the lock step keeps
the moving ``Gr``, so the knee moves from the next step on (as on L2b). Retract locks keep
``p_ret``. All pressures are model values and ASSUMPTIONS.

Pressures gauge [Pa], speeds m/s, extension positive.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
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
from outrigger_sim.hydraulics.rod_release import (  # noqa: E402
    ReleaseStart,
    RodPressureFlowLaw,
    RodReleaseShift,
    release_weight,
)
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
ANCHOR_EXCESS_COUNTED_PA = 0.1e5
"""Criteria rev. 6 4.5: an extension lock with ``p_r0 - p_ext`` above this is counted."""
ANCHOR_RISK_PA = 11.0e5
"""Criteria rev. 6 4.5: ``p_r0 - p_ext`` above 11 bar (``p_r0`` above the 13 bar fallback
start)."""
BAR = 1.0e5


class _RodPressureLag:
    """Moving rod pressure of one plant: lag capped by the valve flow (module docstring)."""

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
        self.flow_law = RodPressureFlowLaw()
        # the harness oil columns are frozen at e_op, so C_r is one value per leg
        self._compliance_m3_Pa = [
            self.flow_law.rod_compliance_m3_Pa(leg.annulus_area_m2, leg.head_stiffness_N_m,
                                               leg.rod_stiffness_N_m)
            for leg in self._legs]
        self._step_s = float(plant.dt)
        self._lag_s = float(plant.tau)
        self.pressure_Pa = np.zeros(LEG_COUNT)

    def start(self, leg: int, pressure_Pa: float) -> None:
        self.pressure_Pa[leg] = pressure_Pa

    def relax(self, leg: int, direction: float, force_N: float, speed_m_s: float) -> float:
        """One inner step of ``leg``; ``speed_m_s`` is the kernel speed of the step."""
        mode = RodChamberMode.EXT if direction > 0.0 else RodChamberMode.RET
        params = self._legs[leg]
        target_Pa = params.moving_target_rod_pressure_Pa(mode, force_N)
        self.pressure_Pa[leg] = self.flow_law.rod_pressure_Pa(
            float(self.pressure_Pa[leg]), target_Pa, speed_m_s, self._step_s, self._lag_s,
            self._compliance_m3_Pa[leg], params.head_area_m2, params.annulus_area_m2,
            is_retract=mode is RodChamberMode.RET)
        return self.pressure_Pa[leg]

    def extension_target_Pa(self, leg: int, force_N: float) -> float:
        """``p*`` of an extension at the net force ``force_N``."""
        return self._legs[leg].moving_target_rod_pressure_Pa(RodChamberMode.EXT, force_N)

    def extension_excess_Pa(self, leg: int, force_N: float) -> float:
        """``max(p_tr - p*, 0)``: the rod pressure an ended extension had not yet relieved
        (``p_tr`` = the lag of the last moving step, ``p*`` = extension target at ``force_N``)."""
        return max(float(self.pressure_Pa[leg]) - self.extension_target_Pa(leg, force_N), 0.0)


@dataclass(frozen=True)
class ExtensionLock:
    """One lock after an extension (criteria rev. 6 4.5 log)."""

    t_s: float
    leg: int
    tracked_Pa: float
    target_Pa: float
    anchor_Pa: float
    knee_N: float


class _AnchorRecord:
    """Criteria rev. 6 4.5 counters per leg (the Chrono judge uses the same names)."""

    def __init__(self) -> None:
        self.locks = [0] * LEG_COUNT
        self.excess_locks = [0] * LEG_COUNT
        self.risk_locks = [0] * LEG_COUNT
        self.max_excess_Pa = [0.0] * LEG_COUNT
        self.max_knee_N = [0.0] * LEG_COUNT
        self.log: list[ExtensionLock] = []

    def add(self, lock: ExtensionLock, excess_Pa: float) -> None:
        """``excess_Pa`` = ``p_r0 - p_ext`` of the lock."""
        leg = lock.leg
        self.locks[leg] += 1
        self.excess_locks[leg] += int(excess_Pa > ANCHOR_EXCESS_COUNTED_PA)
        self.risk_locks[leg] += int(excess_Pa > ANCHOR_RISK_PA)
        self.max_excess_Pa[leg] = max(self.max_excess_Pa[leg], excess_Pa)
        self.max_knee_N[leg] = max(self.max_knee_N[leg], lock.knee_N)
        if len(self.log) < MAX_LOGGED_LOCK_EVENTS:
            self.log.append(lock)

    def record(self) -> dict:
        return {"ext_lock_count": list(self.locks),
                "ext_lock_excess_count": list(self.excess_locks),
                "ext_lock_excess_max_bar": [value / BAR for value in self.max_excess_Pa],
                "ext_lock_risk_count": list(self.risk_locks),
                "ext_lock_knee_max_kN": [value / 1e3 for value in self.max_knee_N],
                "ext_lock_log": [[round(lock.t_s, 6), lock.leg, lock.tracked_Pa,
                                  lock.target_Pa, lock.anchor_Pa, lock.knee_N]
                                 for lock in self.log],
                "ext_lock_log_columns": ["t_s", "leg", "p_tr_Pa", "p_star_Pa", "p_r0_Pa",
                                         "dF_knee_N"]}


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
                self.anchor_record = _AnchorRecord()
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
            """Spec 2.4: M2 starts its release at the M1c opening pressure (no double creep);
            the seed goes into ``p`` only, ``Delta`` stays (revision 4)."""
            if self.rod_release is None:
                return
            self.rod_pressure_seed_Pa[leg] = pressure_Pa

        def _rod_force(self, u):
            was_locked = self.locked.copy()
            kernel_speed_m_s = np.asarray(u, float)  # the flow cap reads it, not the 2 eps wait
            if closure is not None:
                u = self._closing_delay_speed(kernel_speed_m_s)
            rod_force_N = super()._rod_force(u)
            self._record_lock_changes(was_locked)
            if self.rod_release is not None:
                self._anchor_extension_locks(was_locked)
                self._shift_reference_for_rod_pressure(rod_force_N, was_locked, kernel_speed_m_s)
            return rod_force_N

        def _anchor_extension_locks(self, was_locked) -> None:
            """Revision 5: the anchor of a leg locked in this step after an extension keeps the
            unrelieved rod pressure, ``p_r0 = max(min(p_tr, p_ext + max(p_tr - p*, 0)),
            p_floor)`` (the ``min`` matches L2b, hydraulics-expert 2026-11-07: never above the
            tracked pressure; ``p_tr >= p* > p_ext`` in the YAML conditions keeps it inert)."""
            newly_locked = self.locked & ~was_locked & (self.last_dir > 0)
            if not newly_locked.any():
                return
            net_force_N = self.pressure()
            lag = self.rod_pressure_lag
            for i in np.flatnonzero(newly_locked):
                leg = int(i)
                tracked_Pa = float(lag.pressure_Pa[leg])
                target_Pa = lag.extension_target_Pa(leg, float(net_force_N[leg]))
                excess_Pa = max(tracked_Pa - target_Pa, 0.0)
                anchor_Pa = max(min(tracked_Pa, float(self.p_ext[leg]) + excess_Pa),
                                self.p_floor)
                self.p_r0[leg] = anchor_Pa
                knee_N = ((anchor_Pa - self.p_floor) * self.A_ann[leg]
                          * (self.kh[leg] + self.kr[leg]) / self.kr[leg])
                lock = ExtensionLock(float(self.t), leg, tracked_Pa, target_Pa, anchor_Pa,
                                     float(knee_N))
                self.anchor_record.add(lock, anchor_Pa - float(self.p_ext[leg]))

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

        def _shift_reference_for_rod_pressure(self, rod_force_N, was_locked,
                                              kernel_speed_m_s) -> None:
            """Spec 2.3: M2 on the state after the law; acts from this inner step on."""
            pressure_Pa = self.p_r0 - rod_force_N / self.A_ann
            net_force_N = self.pressure()
            lag = self.rod_pressure_lag
            speed_m_s = np.broadcast_to(kernel_speed_m_s, (LEG_COUNT,))
            weight = np.zeros(LEG_COUNT)
            for i in np.flatnonzero(~self.locked):
                if was_locked[i]:
                    self._start_release(i, float(pressure_Pa[i]), float(rod_force_N[i]))
                pressure_Pa[i] = lag.relax(i, float(self.last_dir[i]), float(net_force_N[i]),
                                           float(speed_m_s[i]))
                weight[i] = release_weight(float(self.t - self.t_rel[i]), float(self.tau))
            shift_m = self.rod_release.shift_m(
                pressure_Pa, self.kh, ~self.locked, STROKE_LOWER_END_M - self.sref,
                self.geo.stroke - self.sref, release_weight=weight, t_s=float(self.t))
            self.sref += shift_m

        def _start_release(self, leg: int, locked_pressure_Pa: float,
                           release_force_N: float) -> None:
            """The lag starts at the locked pressure or the M1c seed; ``Delta = Gr(t_rel) /
            A_ann`` (= ``p_r0 - p_r,rel``; ``Gr`` is ``r0`` in the release step)."""
            seed_Pa = self.rod_pressure_seed_Pa[leg]
            start_Pa = locked_pressure_Pa if np.isnan(seed_Pa) else float(seed_Pa)
            self.rod_pressure_seed_Pa[leg] = np.nan
            self.rod_pressure_lag.start(leg, start_Pa)
            self.rod_release.release(
                leg, ReleaseStart(start_Pa, release_force_N / float(self.A_ann[leg])))

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


LIFT_TIME_TOL_S = 1e-9


def clipped_steps_by_lift(clip_times_s: list[list[float]], total: list[int],
                          t_lift_s: float | None) -> dict:
    """v5 criteria rev. 2 2.1: M2 clipped steps per leg before (t < t_lift - 1e-9) and after the
    first crawler lift-off; without a lift-off every clip counts after.

    Raises:
        RuntimeError: The split does not add up to the clipped-step total.
    """
    pre = [0 if t_lift_s is None else sum(t < t_lift_s - LIFT_TIME_TOL_S for t in times)
           for times in clip_times_s]
    post = [len(times) - before for times, before in zip(clip_times_s, pre, strict=True)]
    if [a + b for a, b in zip(pre, post, strict=True)] != list(total):
        raise RuntimeError(f"M2 clip split {pre} + {post} != total {list(total)}")
    return {"m2_clipped_steps_pre_lift": pre, "m2_clipped_steps_post_lift": post,
            "m2_clip_split_t_lift_s": t_lift_s}


def plant_record(plant, t_lift_s: float | None = None) -> dict:
    """Per-leg v5 totals of one plant for the result (M2 shift, clipped steps split at the
    first lift-off ``t_lift_s``)."""
    if plant is None:
        return {}
    record = {}
    if getattr(plant, "rod_release", None) is not None:
        record["m2_law"] = plant.rod_pressure_lag.flow_law.meta()
        record.update(plant.rod_release.record())
        record.update(plant.anchor_record.record())
        record.update(clipped_steps_by_lift(plant.rod_release.clip_times_s,
                                            record["m2_clipped_steps"], t_lift_s))
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


def last_armed_record(t_lift_s: float | None = None) -> dict:
    return plant_record(_LAST_ARMED[0], t_lift_s)


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
