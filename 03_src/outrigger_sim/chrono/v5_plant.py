"""v5 plant options on an L2b actuator of a Chrono run (``v5_hydraulic_impl_spec.md`` 2.0).

One place for ``run_S8C`` and ``run_S9``: the order of spec 2.0 (valve lag, LC, M1c, M2; the flow
limit stays where those runners already set it, after this), the M1c circuit from the YAML and the
record of the run summary. Without options no function here changes anything: callers skip it and
write no key (``vars(args)``, meta and result unchanged).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from outrigger_sim.hydraulics.check_open_delay import CheckDelayCircuit
from outrigger_sim.hydraulics.flow_share import FlowShareAssumptions
from outrigger_sim.hydraulics.v5_options import HydraulicOptions
from outrigger_sim.params import Params

VALVE_AMP_RAMP = "none"
"""Spec 2.2: the soil rows turn the spool lag on without an amplifier ramp."""


def check_delay_circuit(params: Params) -> CheckDelayCircuit:
    """The M1c circuit of the L2b YAML (``params`` loaded with ``model="L2b_NSC"``).

    Tank pressure and compensator drop are the flow-share ASSUMPTIONS (the harness uses the same).

    Raises:
        ValueError: Rod dead lengths that differ per leg (the ported model takes one value).
    """
    actuator = params.l2b.actuator
    rod_side = params.l2b.rod_side
    rod_dead = {float(value) for value in rod_side.rod_dead_length_m}
    if len(rod_dead) != 1:
        raise ValueError(f"M1c takes one rod dead length, the YAML has {sorted(rod_dead)}")
    assumptions = FlowShareAssumptions(eta_v=1.0)
    return CheckDelayCircuit(
        head_area_m2=np.asarray(actuator.head_area_m2, float),
        annulus_area_m2=np.asarray(rod_side.annulus_area_m2, float),
        stroke_m=float(rod_side.stroke_m), rod_dead_length_m=rod_dead.pop(),
        head_dead_length_m=float(actuator.oil_dead_length_m),
        bulk_modulus_Pa=float(actuator.oil_bulk_modulus_eff_Pa),
        tank_pressure_Pa=assumptions.tank_pressure_Pa,
        max_speed_m_s=float(params.actuator.max_speed_m_s),
        compensator_drop_Pa=assumptions.compensator_drop_Pa)


def apply_plant_options(actuator: Any, options: HydraulicOptions, params: Params) -> dict[str, Any]:
    """Configure the L2b actuator with the plant options, in the order of spec 2.0.

    Args:
        actuator: ``L2bForceActuator`` right after the model build (before ``set_flow_limit``).
        options: The run's options (validated by ``v5_options.validate``).
        params: L2b parameters of the plant.

    Returns:
        The meta block of the run (``hydraulic_options`` and what was configured).

    Raises:
        ValueError: An option the actuator refuses (no valve model, counterbalance, ...).
    """
    if options.valve_tau_s is not None:
        actuator.configure_valve(tau_s=options.valve_tau_s, amp_ramp=VALVE_AMP_RAMP)
    if options.lock_closure is not None:
        actuator.configure_lock_closure(options.lock_closure)
    if options.check_delay is not None:
        actuator.configure_check_delay(options.check_delay, check_delay_circuit(params))
    if options.rod_release_force:
        actuator.configure_rod_release()
    return {"hydraulic_options": options.to_dict(), "actuator": {
        key: value for key, value in actuator.meta().items()
        if key in ("rod_release", "lock_closure", "check_delay", "valve")}}


def plant_records(actuator: Any) -> dict[str, Any]:
    """Per-leg v5 records of the run (M2 shift, M1c fills, LC cut steps)."""
    out: dict[str, Any] = {}
    if actuator.rod_release_record() is not None:
        out["rod_release"] = actuator.rod_release_record()
    if actuator.check_delay_summary() is not None:
        out["check_delay"] = actuator.check_delay_summary()
    if actuator.reference.lock_closure_on:
        out["overlap_cut_steps"] = actuator.reference.overlap_cut_steps.tolist()
    return out


__all__ = ["apply_plant_options", "check_delay_circuit", "plant_records"]
