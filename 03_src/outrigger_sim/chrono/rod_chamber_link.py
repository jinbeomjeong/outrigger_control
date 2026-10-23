"""Chrono side of L1-R: the rod-side chamber state machine connected to the L1 model.

``00_docs/01_dynamics/dynamics_model.md`` 5.12.4-5.12.8 (revision 30, form (i) with predictor,
dt 2e-4 s kept, one LOCK-based ``c_n``), ``00_docs/02_hydraulic/rod_side_pressure.md`` 14. The
state machine itself is the engine-independent
:class:`outrigger_sim.hydraulics.rod_chamber.RodChamberStateMachine` (used, not changed here);
this module only feeds it Chrono signals and applies its force.

**Per step** (``L1Model.after_step``; hook order of ``dynamics_model.md`` 4.6 ruling 2):

1. state copy, 2. ground bushing (R15),
2b. :meth:`L1RodChamber.step`: ``machine.step(t, dt, u, delta, d delta, s_motor, F_cyl)`` with

   * ``t`` = ``ChTime``, ``dt`` = the engine step, ``u`` = ``actuator.acting_u_m_s`` (the speed
     of the step just taken, after ramp / braking / law-C saturation: the same mask as the
     actuator's lock, also after a saturation stop),
   * ``delta = r - n . (c - p0)`` and ``d delta = -n . v_c`` of the pad sphere centre ``c``
     (``TransformPointLocalToParent`` / ``PointSpeedLocalToParent``, double precision), floor
     normal ``n`` and surface point ``p0`` as the probe uses them,
   * ``s_motor`` = ``GetMotorPos()``, ``F_cyl`` = ``GetMotorForce()``.

   None of these inputs is changed by the actuator hook (3) or by the closed-loop callback at
   the head of the actuator hooks: the hook only sets the motor function of the next segment
   (``acting_u`` is fixed in ``on_step_end``) and the callback only sets a command. Running the
   machine here therefore gives exactly the values it would give after hook 3, and the
   callback (controller, sensor truth) reads the machine output of the **same** step.
3. actuator hooks (closed-loop callback, then the actuator),
4. external loads: :meth:`L1RodChamber.apply_force` empties the leg's own accumulator and adds
   ``extra_force_N`` once, along the floor normal at the sphere contact point ``c - r n``
   (``AccumulateForce``), then the other load hooks.

**Timing (pychrono 10.0.0, measured 2026-10-22 with a ball on an SMC floor, scratchpad probe):**
the SMC contact force of a step is evaluated from the state at the step start; a body
accumulator set in a hook after step ``n`` is loaded by the Update at the end of step ``n + 1``
and acts in step ``n + 2`` (acceleration change seen exactly two steps after the hook). The SMC
force of step ``n + 2`` uses ``delta_{n+1}``, so the force evaluated at the predicted
``delta_n + d delta_n dt`` (machine option ``predictor``) is aligned with it (14.5 "P"). After a
step that starts with a full Update (a ground bushing was created or removed) the accumulator
acts one step earlier; the predicted value is then one step ahead (error ``(k_n' - k_n) d delta
dt``, about 30 N at 20 mm/s, for one step) - accepted, like the other hook inputs (R15).

**Total normal force** (Q-D2): with mechanics on, the ground bushing (touch / lift, ``mu N`` of
the return mapping) reads ``normal_force_N`` of the machine output that acted during the step
just taken, i.e. the output of the previous step (its deflection is the one the SMC force of
that step used); the record (``L1Model.truth``) uses the output of the same step. The machine's
``N`` is elastic (``k_n delta + F_x``, no dashpot term); with mechanics off the bushing keeps
reading the Chrono contact force (bit-identical to the model before L1-R).

**One-sided pad force** (M1, ``00_docs/02_hydraulic/rod_side_pressure.md`` 17.1): Chrono clips
the SMC force at zero, ``N_smc = max(0, k_n delta + c_n d delta)`` (M3, probed 2026-10-22 with
a ball leaving an SMC floor at 1 m/s: applied 0 N against -10.8 kN unclipped). A machine
``F_x < 0`` kept while the dashpot drives ``N_smc`` to zero would pull the pad to the floor
(at a fast lift-off about ``-F_pad dk / k_n'``, -18.5 kN on RR). The force put on the
accumulator is therefore :func:`one_sided_extra_force_N`: ``max(0, Phi + c_n d delta) -
N_smc`` at the deflection the machine evaluated (predicted), with ``c_n = g_n m_eff`` as Chrono
applies it, and 0 without overlap. Without a clip this is the machine's ``F_x`` bit for bit.
The machine output itself (``extra_force_N``, the elastic ``normal_force_N`` read by the ground
bushing, the LIFT switch at ``Phi <= 0``) is unchanged (M2).

**Sensor truth**: ``chrono/truth.L1SensorTruth`` takes ``head_pressure_Pa``, ``rod_pressure_Pa``
and ``stroke_true_m`` of the same step from :attr:`L1RodChamber.last_step`. With mechanics off
the machine's legacy output is ``F_cyl / A_p`` and ``s_motor - F_cyl / k_h``; the parameters
are aligned to the head areas of ``sensors.hydraulic.leg_head_areas_from_params`` and to
``contact.rigid_floor.L1.derivation.k_oil_N_m`` so that this is bit-identical to the present
truth (checked by the regression test).

**Cost**: ``machine.step`` costs about 40 us per engine step (four legs, module dataclasses;
the L1 step is about 225 us, measured 2026-10-22, P-core). With mechanics on it runs every
step. With mechanics off it runs only when its output is consumed (a
:attr:`L1RodChamber.step_observers` entry, e.g. a sensor source, or
:attr:`L1RodChamber.step_when_off`); otherwise the truth uses the formulas, which equal the
legacy output bit for bit.

**Parameters** (:func:`leg_params_from_params`):
``RodChamberLegParams.from_pad_stiffness(CylinderOilColumns(...), k_n, m_rod g)`` per leg, with

* ``bore`` / ``rod``: ``legs.<leg>.cylinder.{bore,rod}_diameter_m`` (else the common
  ``actuator.*``), ``e_op`` = ``contact.rigid_floor.L1.derivation.operating_extension_m``
  (Q-D7), ``s_max`` = ``actuator.stroke_m``, ``L_0h`` = ``actuator.oil_dead_length_m``,
  ``L_0r`` = ``actuator.rod_side.column_length_m - (s_max - e_op)`` (else ``L_0h``, the
  hydraulics 14.3 value 0.05 m, ASSUMPTION), ``beta`` = ``actuator.oil_bulk_modulus_eff_Pa``;
* ``k_n`` = ``contact.rigid_floor.L1.kn_per_pad_N_m`` rounded to float32, the value the SMC
  material holds (``ChContactMaterialSMC`` stores ``float``), so that ``N = k_n delta + F_x``
  is the locked law exactly;
* then aligned (``dataclasses.replace``, relative change checked <= 1e-6): ``A_p``, ``A_ann``
  to the YAML areas, ``k_h`` to ``derivation.k_oil_N_m``, ``k_r`` to
  ``actuator.rod_side.k_rod_side_N_m`` (when given), ``k_out`` re-solved from ``k_n``;
* ``p_rod_locked_after_extend_Pa`` = ``actuator.rod_side.p_r0_after_extend_Pa``, the floor =
  ``actuator.rod_side.p_floor_Pa`` (absolute); options ``mechanics``, ``predictor``,
  ``lock_eps_m_s``, ``release_tau_s``. Without ``actuator.rod_side`` the mechanics is ``off``.

The pad dashpot: ``contact.rigid_floor.L1.gn_per_pad_1_s`` (the LOCK-based value of the
REXOME35 YAML, one value in every state, Q-D3) with mechanics on and off;
``L1Model(head_only_dashpot=True)`` takes ``gn_per_pad_head_only_1_s`` for a regression against
the pre-L1-R head-only model (``chrono/contact.pad_material_values``).

**Snapshot** (R16, part prefix :data:`PART_PREFIX`): the machine's ``l1r_*`` keys, the last
output (``engine_last_*``), and the accumulator content set by the last hook and loaded by
Chrono's last Update (force world, torque body-local as Chrono stores them) with the
full-Update flag, rebuilt like the actuator (``restore_state`` loads, ``finish_restore`` sets
the post-hook value). A snapshot without ``rod_chamber.*`` keys restores the module default
("locked after an extension at the current force and deflection" on the next standstill step,
Q-D6); :attr:`L1RodChamber.state_defaulted` and the meta key ``l1r_state_defaulted`` mark it.

**Ground-settlement legs** (``L1Model(settlement_legs=...)``, ``chrono/ground_settlement``):
the pad patch of such a leg sits on its own patch body, which a position motor translates
along the floor normal. Chrono's SMC contact of that pad is with the patch body, so the
deflection fed to the machine is measured against the patch surface: the patch offset
``s = n . (x_patch - x_floor)`` is taken off the height and the patch velocity off the rate,
``delta = r - (n . (c - p0) - s)`` and ``d delta = -n . (v_c - v_patch)`` (patch pose and
velocity after the step, the state the next SMC force uses). The patch body has the floor's
orientation (checked by the ground bushing) and only translates, so the surface point of the
patch is ``p0`` moved by ``s n``. Legs without settlement keep the fixed-floor expressions
unchanged (bit-identical); with mechanics off every leg keeps them (the legacy output and the
snapshot stay bit-identical; its ``normal_force_N`` is then not consumed). The extra force
acts on the leg only, like the contact on a fixed floor (the patch body is motion-driven; a
reaction on it would only change its motor force).

Not supported with mechanics on: the ``stroke_model="extension"`` sensor truth. Units SI,
world frame Z-up, LEG_ORDER.
"""

from __future__ import annotations

import dataclasses
import logging
import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
import pychrono as ch
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.chrono.contact import pad_material_values
from outrigger_sim.hydraulics.rod_chamber import (
    STATE_KEYS as MACHINE_STATE_KEYS,
)
from outrigger_sim.hydraulics.rod_chamber import (
    CylinderOilColumns,
    LockPressureSource,
    RodChamberLegParams,
    RodChamberOptions,
    RodChamberStateMachine,
    RodChamberStep,
    RodSideMechanics,
)
from outrigger_sim.params import LEG_ORDER, Params, ParamsError
from outrigger_sim.sensors.hydraulic import (
    leg_annulus_areas_from_params,
    leg_head_areas_from_params,
)

PART_PREFIX = "rod_chamber"
"""Snapshot key prefix (``rod_chamber.<key>``)."""

ROD_SIDE_KEY = "actuator.rod_side"
MECHANICS_KEY = "actuator.rod_side.mechanics"
K_OIL_KEY = "contact.rigid_floor.L1.derivation.k_oil_N_m"
E_OP_KEY = "contact.rigid_floor.L1.derivation.operating_extension_m"
KN_KEY = "contact.rigid_floor.L1.kn_per_pad_N_m"

logger = logging.getLogger(__name__)

ALIGN_REL_TOL = 1.0e-6
"""Largest relative change allowed when aligning a computed value to its (rounded) YAML key."""
BULK_MODULUS_KEY = "actuator.oil_bulk_modulus_eff_Pa"
"""A run-time override of this key (beta sensitivity) recomputes ``k_h`` and ``k_r`` with the
run's beta; the derived YAML ``k_oil_N_m`` / ``k_rod_side_N_m`` (file beta) are then not the
alignment targets."""

OUTPUT_FIELDS = (
    "mode",
    "extra_force_N",
    "normal_force_N",
    "pad_stiffness_N_m",
    "head_pressure_Pa",
    "rod_pressure_Pa",
    "stroke_true_m",
    "cylinder_force_N",
    "piston_travel_m",
)
"""Fields of :class:`RodChamberStep` kept in the snapshot as ``engine_last_<field>``."""

ENGINE_KEYS = (
    "engine_last_t_s",
    *(f"engine_last_{name}" for name in OUTPUT_FIELDS),
    "engine_pending_force_world_N",
    "engine_pending_torque_local_N_m",
    "engine_loaded_force_world_N",
    "engine_loaded_torque_local_N_m",
    "engine_next_step_full_update",
    "engine_mechanics_on",
)

LockPressureProvider = Callable[[], ArrayLike | None]
StepObserver = Callable[[RodChamberStep], None]


def _optional(params: Params, key: str) -> Any | None:
    try:
        return params.get(key)
    except ParamsError:
        return None


def _per_leg_value(value: Any, leg: str, index: int) -> float:
    """A per-leg YAML value (mapping by leg name, sequence in LEG_ORDER) or a scalar."""
    if isinstance(value, Mapping):
        return float(value[leg])
    if isinstance(value, (list, tuple)):
        return float(value[index])
    return float(value)


def mechanics_from_params(
    params: Params, override: RodSideMechanics | str | None = None
) -> RodSideMechanics:
    """``actuator.rod_side.mechanics``; ``off`` when the YAML has no such key. ``override``
    (``L1Model(rod_side_mechanics=...)``) wins: the params loader cannot read the text key yet
    (2026-10-22), so tests and smoke runs switch L1-R on through the constructor."""
    if override is not None:
        return RodSideMechanics(str(override))
    value = _optional(params, MECHANICS_KEY)
    return RodSideMechanics.OFF if value is None else RodSideMechanics(str(value))


def options_from_params(
    params: Params, mechanics: RodSideMechanics | str | None = None
) -> RodChamberOptions:
    """Machine options from ``actuator.rod_side.*`` (module defaults for missing keys);
    ``mechanics`` overrides the YAML key (:func:`mechanics_from_params`)."""
    chosen = mechanics_from_params(params, mechanics)
    block = _optional(params, ROD_SIDE_KEY)
    if block is None:
        return RodChamberOptions(mechanics=chosen)
    defaults = RodChamberOptions()
    return RodChamberOptions(
        mechanics=chosen,
        predictor=bool(block.get("predictor", defaults.predictor)),
        lock_pressure_source=LockPressureSource(
            str(block.get("lock_pressure_source", defaults.lock_pressure_source))
        ),
        mode_epsilon_m_s=float(block.get("lock_eps_m_s", defaults.mode_epsilon_m_s)),
        poc_close_delay_s=float(block.get("poc_close_delay_s", defaults.poc_close_delay_s)),
        rod_pressure_lag_s=float(block.get("release_tau_s", defaults.rod_pressure_lag_s)),
    )


def _aligned(computed: float, target: float, name: str) -> float:
    rel = abs(computed - target) / abs(target)
    if not rel <= ALIGN_REL_TOL:
        raise ValueError(
            f"{name}: computed {computed!r} differs from the YAML {target!r} by {rel:.3e} "
            f"(> {ALIGN_REL_TOL:g}); the YAML and the oil-column geometry disagree"
        )
    return float(target)


def leg_params_from_params(
    params: Params,
) -> tuple[list[RodChamberLegParams], list[dict[str, Any]]]:
    """Per-leg machine parameters (module docstring) and the alignment record for the meta."""
    gravity = float(params.meta.gravity_m_s2)
    stroke = float(params.get("actuator.stroke_m"))
    dead_head = float(params.get("actuator.oil_dead_length_m"))
    beta = float(params.get(BULK_MODULUS_KEY))
    is_beta_overridden = BULK_MODULUS_KEY in params.overrides
    k_oil = params.get(K_OIL_KEY)
    e_op = params.get(E_OP_KEY)
    kn = params.get(KN_KEY)
    block = _optional(params, ROD_SIDE_KEY) or {}
    head_areas = leg_head_areas_from_params(params)
    annulus_areas = leg_annulus_areas_from_params(params)
    common_bore = float(params.get("actuator.bore_diameter_m"))
    common_rod = float(params.get("actuator.rod_diameter_m"))
    out: list[RodChamberLegParams] = []
    records: list[dict[str, Any]] = []
    for i, (leg, leg_params) in enumerate(zip(LEG_ORDER, params.legs, strict=True)):
        bore = _optional(params, f"legs.{leg}.cylinder.bore_diameter_m")
        rod = _optional(params, f"legs.{leg}.cylinder.rod_diameter_m")
        bore = common_bore if bore is None else float(bore)
        rod = common_rod if rod is None else float(rod)
        extension = _per_leg_value(e_op, leg, i)
        column = block.get("column_length_m")
        dead_rod = (
            dead_head if column is None else _per_leg_value(column, leg, i) - (stroke - extension)
        )
        columns = CylinderOilColumns(
            bore_m=bore,
            rod_m=rod,
            extension_m=extension,
            stroke_max_m=stroke,
            head_dead_length_m=dead_head,
            rod_dead_length_m=dead_rod,
            bulk_modulus_Pa=beta,
        )
        kn_yaml = _per_leg_value(kn, leg, i)
        kn_smc = float(np.float32(kn_yaml))  # what ChContactMaterialSMC holds
        options: dict[str, float] = {}
        p_r0 = block.get("p_r0_after_extend_Pa")
        if p_r0 is not None:
            options["p_rod_locked_after_extend_Pa"] = _per_leg_value(p_r0, leg, i)
        if block.get("p_floor_Pa") is not None:
            options["cavitation_floor_abs_Pa"] = float(block["p_floor_Pa"])
        rod_weight = float(leg_params.moving_part.mass_kg) * gravity
        built = RodChamberLegParams.from_pad_stiffness(columns, kn_smc, rod_weight, **options)
        head = _aligned(built.head_area_m2, float(head_areas[i]), f"{leg} head area")
        annulus = _aligned(built.annulus_area_m2, float(annulus_areas[i]), f"{leg} annulus area")
        if is_beta_overridden:
            k_head = float(built.head_stiffness_N_m)  # the run's beta (sensitivity case)
        else:
            k_head = _aligned(
                built.head_stiffness_N_m, _per_leg_value(k_oil, leg, i), f"{leg} k_oil"
            )
        k_rod_yaml = block.get("k_rod_side_N_m")
        k_rod = (
            built.rod_stiffness_N_m
            if k_rod_yaml is None or is_beta_overridden
            else _aligned(built.rod_stiffness_N_m, _per_leg_value(k_rod_yaml, leg, i),
                          f"{leg} k_rod_side")
        )
        k_out = 1.0 / (1.0 / kn_smc - 1.0 / k_head)
        aligned = dataclasses.replace(
            built,
            head_area_m2=head,
            annulus_area_m2=annulus,
            head_stiffness_N_m=k_head,
            rod_stiffness_N_m=k_rod,
            outer_stiffness_N_m=k_out,
        )
        out.append(aligned)
        records.append(
            {
                "leg": leg,
                "bore_m": bore,
                "rod_m": rod,
                "extension_m": extension,
                "rod_dead_length_m": dead_rod,
                "kn_yaml_N_m": kn_yaml,
                "kn_smc_float32_N_m": kn_smc,
                "computed_head_area_m2": built.head_area_m2,
                "computed_annulus_area_m2": built.annulus_area_m2,
                "computed_head_stiffness_N_m": built.head_stiffness_N_m,
                "computed_rod_stiffness_N_m": built.rod_stiffness_N_m,
                "computed_outer_stiffness_N_m": built.outer_stiffness_N_m,
                "outer_stiffness_N_m": k_out,
                "rod_mass_kg": float(leg_params.moving_part.mass_kg),
                "head_stiffness_source": (
                    "run beta (override)" if is_beta_overridden else "YAML k_oil_N_m"
                ),
            }
        )
    return out, records


def _v(v: Any) -> NDArray[np.float64]:
    return np.array([v.x, v.y, v.z], dtype=float)


def one_sided_extra_force_N(
    extra_force_N: float, spring_force_N: float, damping_force_N: float
) -> float:
    """Extra force that keeps the total pad normal force non-negative (M1, rod_side_pressure.md
    17.1) for a pad in contact (``delta > 0``).

    Chrono's SMC force is ``N_smc = max(0, k_n delta + c_n d delta)`` (clipped, M3). With
    ``N_tot = max(0, Phi + c_n d delta)``, ``Phi = k_n delta + F_x`` the machine's elastic total,
    the applied extra force is ``N_tot - N_smc``. Without a clip the machine's ``F_x`` is returned
    unchanged (bit for bit); the function is continuous across both clip boundaries.

    Args:
        extra_force_N: The machine's ``F_x`` at the evaluated deflection.
        spring_force_N: ``k_n delta`` at the same deflection.
        damping_force_N: ``c_n d delta`` (SMC Hooke dashpot, ``d delta`` > 0 = closing).
    """
    smc_N = spring_force_N + damping_force_N
    total_N = spring_force_N + extra_force_N + damping_force_N
    if smc_N >= 0.0 and total_N >= 0.0:
        return extra_force_N
    return max(0.0, total_N) - max(0.0, smc_N)


def _contact_damping_N_s_m(model: Any, ground_bodies: Sequence[ch.ChBody]) -> NDArray[np.float64]:
    """``c_n = g_n m_eff`` per pad as Chrono applies it (``g_n`` float32 as the SMC material
    stores it, ``m_eff`` of the leg and its ground body; the convention of ``chrono/energy``)."""
    head_only = bool(getattr(model, "head_only_dashpot", False))
    values = []
    for i, (leg, ground) in enumerate(zip(model.legs, ground_bodies, strict=True)):
        gn = float(np.float32(pad_material_values(model.params, i, head_only).gn_1_s))
        m_leg, m_ground = float(leg.GetMass()), float(ground.GetMass())
        values.append(gn * m_leg * m_ground / (m_leg + m_ground))
    return np.array(values)


def _patch_bodies_by_leg(model: Any) -> tuple[ch.ChBody | None, ...]:
    """The settlement patch body under each leg's pad (LEG_ORDER), None on the fixed floor."""
    settlement = getattr(model, "settlement", None)
    by_name: dict[str, ch.ChBody] = {}
    if settlement is not None:
        by_name = dict(zip(settlement.leg_names, settlement.bodies, strict=True))
    return tuple(by_name.get(name) for name in LEG_ORDER[: len(model.legs)])


class L1RodChamber:
    """The L1-R state machine of an :class:`~outrigger_sim.chrono.model.L1Model` (module
    docstring). Built by the model; one instance per model.

    Attributes:
        machine: The engine-independent state machine (the only owner of the L1-R state).
        enabled: Mechanics ``one_sided_parallel`` (False: ``off``, no force, no accumulator).
        last_step: Output of the latest :meth:`step` (None before the first step).
        lock_pressure_provider: Optional callable returning ``rod_pressure_at_lock_Pa`` for
            the next machine step (TRACKED ``p_r0`` from a sensor synthesis, rod_side.py).
        step_observers: Callables receiving every new :attr:`last_step` (e.g. a sensor source
            that reads the machine output).
    """

    def __init__(self, model: Any, mechanics: RodSideMechanics | str | None = None) -> None:
        params: Params = model.params
        self._model = model
        self._system = model.system
        self.mechanics_overridden = mechanics is not None
        self.options = options_from_params(params, mechanics)
        self.enabled = self.options.mechanics is RodSideMechanics.ONE_SIDED_PARALLEL
        self.unavailable_reason: str | None = None
        """Mechanics off only: why the machine could not be built (e.g. a sensitivity
        ``k_n`` above the head oil stiffness); ``None`` = built. Nothing consumes the machine
        with mechanics off unless a sensor source or observer is attached, which then fails."""
        self.machine: RodChamberStateMachine | None = None
        self.leg_params: list[RodChamberLegParams] = []
        self._align_records: list[dict[str, Any]] = []
        try:
            self.leg_params, self._align_records = leg_params_from_params(params)
            self.machine = RodChamberStateMachine(self.leg_params, self.options)
        except ValueError as error:
            if self.enabled:
                raise
            self.unavailable_reason = str(error)
            logger.warning("L1-R machine not built (mechanics off): %s", error)
        self._legs = tuple(model.legs)
        # Mechanics off keeps the fixed-floor deflection for every leg: its machine output and
        # snapshot keys then stay bit-identical to the model before settlement support (the
        # legacy output's delta-based fields are not consumed with mechanics off).
        self._patch_bodies = (
            _patch_bodies_by_leg(model) if self.enabled else (None,) * len(self._legs)
        )
        """Per leg: the settlement patch body under its pad, or None (fixed floor)."""
        self._centres_local_ch = tuple(model.sphere_centres_local_ch)
        self._radii = np.asarray(model.sphere_radii_m, dtype=float)
        self._accumulators: tuple[int, ...] = ()
        self._contact_damping = np.zeros(len(self._legs))
        if self.enabled:
            self._accumulators = tuple(int(body.AddAccumulator()) for body in self._legs)
            ground_bodies = [
                model.floor if patch is None else patch for patch in self._patch_bodies
            ]
            self._contact_damping = _contact_damping_N_s_m(model, ground_bodies)
        n = len(self._legs)
        self.applied_extra_force_N = np.zeros(n)
        """Extra force set on the accumulators by the latest :meth:`apply_force` input: the
        machine's ``extra_force_N`` made one-sided (:func:`one_sided_extra_force_N`)."""
        self._pending_force = np.zeros((n, 3))
        self._pending_torque = np.zeros((n, 3))
        self._loaded_force = np.zeros((n, 3))
        self._loaded_torque = np.zeros((n, 3))
        self._post_restore: tuple[NDArray[np.float64], NDArray[np.float64]] | None = None
        self.last_step: RodChamberStep | None = None
        self.last_t_s = math.nan
        self.last_deflection_m = np.full(n, np.nan)
        self.last_deflection_rate_m_s = np.full(n, np.nan)
        self.lock_pressure_provider: LockPressureProvider | None = None
        self.step_observers: list[StepObserver] = []
        self.sensor_source: Any | None = None
        """Optional ``sensors.rod_side.RodChamberSensorSource`` over :attr:`machine`
        (:meth:`attach_sensor_source`); when set, every machine step goes through its
        ``step`` (the source keeps the output for its ``update`` at control instants)."""
        self.step_when_off = False
        """Step the machine every engine step also with mechanics off (its legacy output is
        then the sensor truth; bit-identical to the formulas). Default False: with mechanics
        off and no observer the machine is idle (its ``step`` costs about 40 us per engine
        step, measured 2026-10-22) and ``chrono/truth`` uses the formulas."""
        self.state_defaulted = False

    # --- views --------------------------------------------------------------------------

    @property
    def mechanics(self) -> RodSideMechanics:
        return self.options.mechanics

    def output_at(self, t_s: float) -> RodChamberStep | None:
        """:attr:`last_step` if it belongs to time ``t_s`` (same float), else None."""
        if self.last_step is None or self.last_t_s != t_s:
            return None
        return self.last_step

    def bushing_normal_force_N(self) -> list[float] | None:
        """Ground-bushing normal-force source (Q-D2): ``normal_force_N`` of the output that
        acted during the step just taken (the previous output); None before the first step
        (the bushing then reads the Chrono contact force)."""
        if self.last_step is None:
            return None
        return [float(v) for v in self.last_step.normal_force_N]

    @property
    def acting_force_world_N(self) -> NDArray[np.float64]:
        """Accumulator force Chrono loaded at its last Update (acts in the next step)."""
        return self._loaded_force.copy()

    # --- per step -----------------------------------------------------------------------

    def deflection(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Pad sphere penetration ``delta`` and its rate (module docstring), per leg; a
        settlement leg is measured against its moving patch body."""
        n = self._model.bushing.normal_world()
        nx, ny, nz = float(n[0]), float(n[1]), float(n[2])
        px, py, pz = (float(c) for c in self._model.floor_point_world_m)
        floor_pos = self._model.floor.GetPos()
        count = len(self._legs)
        delta = np.empty(count)
        rate = np.empty(count)
        for i, (body, local, patch) in enumerate(
            zip(self._legs, self._centres_local_ch, self._patch_bodies, strict=True)
        ):
            c = body.TransformPointLocalToParent(local)
            v = body.PointSpeedLocalToParent(local)
            height = (c.x - px) * nx + (c.y - py) * ny + (c.z - pz) * nz
            speed_along_normal = v.x * nx + v.y * ny + v.z * nz
            if patch is not None:
                patch_pos = patch.GetPos()
                patch_vel = patch.GetPosDt()
                patch_offset = (
                    (patch_pos.x - floor_pos.x) * nx
                    + (patch_pos.y - floor_pos.y) * ny
                    + (patch_pos.z - floor_pos.z) * nz
                )
                height -= patch_offset
                speed_along_normal -= patch_vel.x * nx + patch_vel.y * ny + patch_vel.z * nz
            delta[i] = self._radii[i] - height
            rate[i] = -speed_along_normal
        return delta, rate

    @property
    def is_stepping(self) -> bool:
        """Whether :meth:`step` advances the machine (mechanics on, a sensor source, an
        observer, or :attr:`step_when_off`)."""
        return (
            self.enabled
            or self.step_when_off
            or self.sensor_source is not None
            or bool(self.step_observers)
        )

    def attach_sensor_source(self, source: Any | None) -> None:
        """Route the machine steps through ``source.step`` (None detaches).

        Raises:
            ValueError: The source wraps another machine (one owner of the L1-R state).
        """
        if source is not None:
            self._require_machine()
        if source is not None and getattr(source, "machine", None) is not self.machine:
            raise ValueError("the sensor source must wrap this engine's RodChamberStateMachine")
        self.sensor_source = source

    def step(self, dt_s: float) -> RodChamberStep | None:
        """Machine step at the end of the step just taken (``L1Model.after_step`` 2b); None
        (nothing done) when :attr:`is_stepping` is False."""
        if not self.is_stepping:
            return None
        machine = self._require_machine()
        model = self._model
        t = float(self._system.GetChTime())
        delta, rate = self.deflection()
        motors = model.motors
        s_motor = np.array([m.GetMotorPos() for m in motors], dtype=float)
        f_cyl = np.array([m.GetMotorForce() for m in motors], dtype=float)
        u = model.u_applied_m_s
        signals: dict[str, Any] = {
            "time_s": t,
            "step_s": float(dt_s),
            "applied_speed_m_s": u,
            "pad_deflection_m": delta,
            "pad_deflection_rate_m_s": rate,
            "motor_position_m": s_motor,
            "cylinder_force_N": f_cyl,
        }
        if self.lock_pressure_provider is not None:
            signals["rod_pressure_at_lock_Pa"] = self.lock_pressure_provider()
        source = self.sensor_source
        if source is None:
            out = machine.step(**signals)
        else:
            # pass-through of the machine step that keeps the output (sensors/rod_side
            # RodChamberSensorSource; it may add the TRACKED lock pressure of its synthesis)
            out = source.step(**signals)
        self.last_step = out
        self.last_t_s = t
        self.last_deflection_m = delta
        self.last_deflection_rate_m_s = rate
        if self.enabled:
            self.applied_extra_force_N = self._one_sided_extra_forces(out, delta, rate, dt_s)
        for observer in self.step_observers:
            observer(out)
        return out

    def _one_sided_extra_forces(
        self, out: RodChamberStep, delta: NDArray[np.float64], rate: NDArray[np.float64],
        dt_s: float,
    ) -> NDArray[np.float64]:
        """The machine's ``extra_force_N`` made one-sided per leg (M1): at the deflection the
        machine evaluated (predicted with ``predictor``) and the dashpot of the SMC contact;
        no extra force without overlap."""
        applied = np.zeros(len(self._legs))
        for i, leg_params in enumerate(self.leg_params):
            rate_i = float(rate[i])
            evaluated_m = float(delta[i])
            if self.options.predictor:
                evaluated_m = evaluated_m + rate_i * float(dt_s)
            if not evaluated_m > 0.0:
                continue
            applied[i] = one_sided_extra_force_N(
                float(out.extra_force_N[i]),
                leg_params.pad_stiffness_head_only_N_m * evaluated_m,
                float(self._contact_damping[i]) * rate_i,
            )
        return applied

    def apply_force(self) -> None:
        """Load stage (4): :attr:`applied_extra_force_N` along the floor normal at the sphere
        contact point, one accumulator per leg, emptied and filled once. No-op with mechanics
        off."""
        if not self.enabled or self.last_step is None:
            return
        n = self._model.bushing.normal_world()
        nx, ny, nz = float(n[0]), float(n[1]), float(n[2])
        for i, (body, local, acc) in enumerate(
            zip(self._legs, self._centres_local_ch, self._accumulators, strict=True)
        ):
            fx = float(self.applied_extra_force_N[i])
            c = body.TransformPointLocalToParent(local)
            r = float(self._radii[i])
            point = ch.ChVector3d(c.x - r * nx, c.y - r * ny, c.z - r * nz)
            body.EmptyAccumulator(acc)
            body.AccumulateForce(acc, ch.ChVector3d(fx * nx, fx * ny, fx * nz), point, False)
            self._pending_force[i] = _v(body.GetAccumulatedForce(acc))
            self._pending_torque[i] = _v(body.GetAccumulatedTorque(acc))

    def on_step_end(self) -> None:
        """After ``DoStepDynamics``: its end Update loaded the accumulator content."""
        self._loaded_force = self._pending_force.copy()
        self._loaded_torque = self._pending_torque.copy()

    # --- snapshot (R16) -----------------------------------------------------------------

    def _require_machine(self) -> RodChamberStateMachine:
        if self.machine is None:
            raise RuntimeError(f"L1-R machine not available: {self.unavailable_reason}")
        return self.machine

    def state_arrays(self) -> dict[str, NDArray[Any]]:
        arrays: dict[str, NDArray[Any]] = (
            {} if self.machine is None else dict(self.machine.state_arrays())
        )
        n = len(self._legs)
        last = self.last_step
        arrays["engine_last_t_s"] = np.array([self.last_t_s])
        for name in OUTPUT_FIELDS:
            value = np.full(n, np.nan) if last is None else getattr(last, name)
            arrays[f"engine_last_{name}"] = np.array(value, dtype=float)
        arrays["engine_pending_force_world_N"] = self._pending_force.copy()
        arrays["engine_pending_torque_local_N_m"] = self._pending_torque.copy()
        arrays["engine_loaded_force_world_N"] = self._loaded_force.copy()
        arrays["engine_loaded_torque_local_N_m"] = self._loaded_torque.copy()
        arrays["engine_next_step_full_update"] = np.array([not self._system.IsUpdated()])
        arrays["engine_mechanics_on"] = np.array([self.enabled])
        return arrays

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        """Restore :meth:`state_arrays` (bodies are already set; see the module docstring)."""
        missing = [k for k in ENGINE_KEYS if k not in arrays]
        if missing:
            raise ValueError(f"rod chamber state lacks {missing}")
        saved_on = bool(np.asarray(arrays["engine_mechanics_on"]).reshape(-1)[0])
        if saved_on != self.enabled:
            raise ValueError(
                f"snapshot rod-chamber mechanics on = {saved_on}, this model {self.enabled} "
                "(the mechanics override is not part of Params.sha256)"
            )
        if self.machine is not None:
            self.machine.restore_state(
                {k: arrays[k] for k in MACHINE_STATE_KEYS if k in arrays}
            )
            self.state_defaulted = self.machine.state_defaulted
        t_last = float(np.asarray(arrays["engine_last_t_s"]).reshape(-1)[0])
        if math.isnan(t_last):
            self.last_step = None
        else:
            fields = {
                name: np.array(arrays[f"engine_last_{name}"], dtype=float) for name in OUTPUT_FIELDS
            }
            fields["mode"] = fields["mode"].astype(np.int64)
            self.last_step = RodChamberStep(**fields)
        self.last_t_s = t_last
        if self.sensor_source is not None:
            self.sensor_source.last_step = self.last_step
        self._pending_force = np.array(arrays["engine_pending_force_world_N"], dtype=float)
        self._pending_torque = np.array(arrays["engine_pending_torque_local_N_m"], dtype=float)
        self._loaded_force = np.array(arrays["engine_loaded_force_world_N"], dtype=float)
        self._loaded_torque = np.array(arrays["engine_loaded_torque_local_N_m"], dtype=float)
        full = bool(np.asarray(arrays["engine_next_step_full_update"]).reshape(-1)[0])
        if full:
            self._set_accumulators(self._pending_force, self._pending_torque)
            self._post_restore = None
        else:
            self._set_accumulators(self._loaded_force, self._loaded_torque)
            self._post_restore = (self._pending_force.copy(), self._pending_torque.copy())

    def finish_restore(self) -> None:
        """After the restore's system Update: the post-hook accumulator content."""
        if self._post_restore is not None:
            self._set_accumulators(*self._post_restore)
            self._post_restore = None

    def restore_default(self) -> None:
        """Snapshot without ``rod_chamber.*`` keys (Q-D6): module default state, zero force."""
        if self.machine is not None:
            self.machine.restore_state({})
        self.state_defaulted = True
        self.last_step = None
        self.last_t_s = math.nan
        if self.sensor_source is not None:
            self.sensor_source.last_step = None
        zero = np.zeros_like(self._pending_force)
        self._pending_force = zero.copy()
        self._pending_torque = zero.copy()
        self._loaded_force = zero.copy()
        self._loaded_torque = zero.copy()
        self._set_accumulators(zero, zero)
        self._post_restore = None

    def _set_accumulators(
        self, force_world: NDArray[np.float64], torque_local: NDArray[np.float64]
    ) -> None:
        """Rebuild the accumulators bit for bit: the force at the COG (zero torque) plus the
        stored body-local torque. No accumulators with mechanics off."""
        if not self.enabled:
            return
        for i, (body, acc) in enumerate(zip(self._legs, self._accumulators, strict=True)):
            body.EmptyAccumulator(acc)
            f = force_world[i]
            t = torque_local[i]
            body.AccumulateForce(acc, ch.ChVector3d(*(float(c) for c in f)), body.GetPos(), False)
            body.AccumulateTorque(acc, ch.ChVector3d(*(float(c) for c in t)), True)

    # --- meta ---------------------------------------------------------------------------

    def _unavailable_machine_meta(self) -> dict[str, Any]:
        return {
            "model": "L1-R (dynamics_model.md 5.12.4, rod_side_pressure.md 14), form (i)",
            "l1_rod_chamber_mechanics": str(self.options.mechanics),
            "l1r_state_defaulted": False,
            "machine_unavailable_reason": self.unavailable_reason,
        }

    def meta(self) -> dict[str, Any]:
        meta = (
            self._unavailable_machine_meta() if self.machine is None else self.machine.meta()
        )
        meta["l1r_state_defaulted"] = bool(self.state_defaulted or meta["l1r_state_defaulted"])
        meta.update(
            engine_link="outrigger_sim.chrono.rod_chamber_link.L1RodChamber",
            enabled=self.enabled,
            mechanics_source=(
                "L1Model(rod_side_mechanics=...) override" if self.mechanics_overridden
                else "YAML actuator.rod_side.mechanics (off when absent)"
            ),
            stepping=self.is_stepping,
            sensor_source=None if self.sensor_source is None else type(self.sensor_source).__name__,
            hook_order=(
                "after_step: probe -> ground bushing (N = machine normal_force_N of the previous "
                "step with mechanics on) -> machine.step (t, dt, acting_u, delta / d delta at the "
                "sphere centre, GetMotorPos, GetMotorForce) -> actuator hooks (callback, "
                "actuator) -> extra_force_N along the floor normal at the contact point "
                "(own accumulator, load stage) -> load hooks -> record"
            ),
            accumulator_lag=(
                "set after step n, loaded at the end of step n+1, acts in step n+2 (measured "
                "2026-10-22); predictor horizon = engine dt"
            ),
            damping=(
                "contact.rigid_floor.L1.gn_per_pad_head_only_1_s (head_only_dashpot)"
                if getattr(self._model, "head_only_dashpot", False)
                else "contact.rigid_floor.L1.gn_per_pad_1_s (LOCK basis with REXOME35, every state)"
            ),
            parameter_alignment=self._align_records,
            applied_extra_force=(
                "one-sided: max(0, Phi + c_n d delta) - max(0, k_n delta + c_n d delta) at the "
                "evaluated deflection, 0 without overlap (rod_side_pressure.md 17.1 M1); "
                "machine F_x when no clip"
            ),
            contact_damping_N_s_m=[float(c) for c in self._contact_damping],
        )
        settling = [
            name
            for name, patch in zip(LEG_ORDER, self._patch_bodies, strict=False)
            if patch is not None
        ]
        if settling:  # key only with settlement legs: other runs keep their meta unchanged
            meta["settlement_deflection"] = {
                "legs": settling,
                "reference": "patch body surface (delta - patch offset along n, rate - patch "
                "velocity along n)",
            }
        return meta


__all__ = [
    "ENGINE_KEYS",
    "OUTPUT_FIELDS",
    "PART_PREFIX",
    "L1RodChamber",
    "leg_params_from_params",
    "mechanics_from_params",
    "one_sided_extra_force_N",
    "options_from_params",
]
