"""One place that reads the S8 seal-friction / counterbalance plant state (C-S8-1, C-S8-2).

The plant itself (``hydraulics/seal_friction.py``, ``hydraulics/counterbalance.py``,
``chrono/l2b_actuator.py``, YAML ``actuator.seal_friction.*`` / ``actuator.counterbalance.*``)
is written in parallel by another work package after
``00_docs/02_hydraulic/s8_seal_friction_counterbalance.md`` (spec 2.5, 4.2, 5 C-1 ... C-8).
Its attribute names were not fixed when this module was written, so every access of the S8
runner, the pad recorder and the judge goes through here; adapt the name tables below (and
only them) when the plant lands.

Quantities (names of the hydraulics spec, sign of spec 1):

* ``f_N``           seal friction on the piston ``f`` (+ = pushes the piston outward), per leg;
* ``stuck``         stick state (bool);
* ``s_p_m``         piston position ``s_p`` (= stroke sensor truth);
* ``F_s_N``         Coulomb limit in use per leg;
* ``dissipation_J`` accumulated friction dissipation; ``slip_transitions`` count;
* CB: ``cb_y`` opening, ``cb_delta_m`` accumulated push-back ``delta_cb``, ``cb_volume_m3``.

Pressure force (two-sensor net force truth) ``F_p = F - f`` (spec 2.5 step 5); with no
friction object, ``F_p = F`` (the S7 path, bit-identical). Timing: read inside a per-step hook
**before** the force-law hook (the runner step callback), the friction state belongs to the
force that acted in the step just taken (``acting_force_N``).

Case configuration: :func:`seal_friction_overrides` / :func:`lock_valve_overrides` give the
parameter overrides for a friction level (front leg, U-S8-H1; rear = x ``rear_scale``, the
plant applies it) and the lock valve. Without the YAML keys a level > 0 or the counterbalance
raises :class:`PlantNotAvailableError` (level 0 + pilot check = the S7 plant, always possible).

Units SI.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray

# --- name tables (adapt here when the plant lands) ---------------------------------------
FRICTION_OBJECT_ATTRS = ("seal_friction", "friction", "seal")
"""Attribute of ``L2bForceActuator`` holding the friction element (spec C-3)."""
FRICTION_FIELDS: dict[str, tuple[str, ...]] = {
    "f_N": ("f_N", "friction_N", "force_N", "f"),
    "stuck": ("stuck", "is_stuck", "sticking", "stick"),
    "s_p_m": ("s_p_m", "piston_m", "piston_position_m", "s_piston_m", "s_p"),
    "F_s_N": ("F_s_N", "limit_N", "fs_N", "level_N"),
    "dissipation_J": ("dissipation_J", "dissipated_J", "energy_dissipated_J"),
    "slip_transitions": ("slip_transitions", "slip_count", "transitions"),
}
CB_OBJECT_ATTRS = ("counterbalance", "cb", "lock_valve_element")
CB_FIELDS: dict[str, tuple[str, ...]] = {
    "cb_y": ("y", "opening", "y_open"),
    "cb_delta_m": ("delta_cb_m", "delta_m", "shift_m", "push_back_m"),
    "cb_volume_m3": ("volume_m3", "discharged_m3", "vented_m3"),
}
ACTING_ATTRS = {"f_N": "acting_friction_N", "s_p_m": "acting_piston_m"}
"""``L2bForceActuator`` views of the state that acted in the last step (plant 2026-10-24)."""
PRESSURE_FORCE_ATTRS =("acting_pressure_force_N", "pressure_force_N")
"""Actuator property ``F_p`` of the step just taken, when the plant provides one."""
FRICTION_LEVEL_KEY = "actuator.seal_friction.level_N"
LOCK_VALVE_KEY = "actuator.lock_valve"
LOCK_VALVES = ("pilot_check", "counterbalance")


class PlantNotAvailableError(RuntimeError):
    """The S8 friction / counterbalance plant needed by a case is not installed."""


def _get(obj: Any, names: tuple[str, ...]) -> Any:
    for n in names:
        if hasattr(obj, n):
            v = getattr(obj, n)
            return v() if callable(v) else v
    return None


def friction_object(actuator: Any) -> Any:
    return next((getattr(actuator, a) for a in FRICTION_OBJECT_ATTRS
                 if getattr(actuator, a, None) is not None), None)


def cb_object(actuator: Any) -> Any:
    return next((getattr(actuator, a) for a in CB_OBJECT_ATTRS
                 if getattr(actuator, a, None) is not None), None)


def friction_state(actuator: Any) -> dict[str, NDArray[Any]] | None:
    """Per-leg friction state (module docstring) or None without a friction element."""
    obj = friction_object(actuator)
    if obj is None:
        return None
    n = actuator.n_legs
    out: dict[str, NDArray[Any]] = {}
    for key, names in FRICTION_FIELDS.items():
        v = _get(obj, names)
        if v is None:
            dtype = bool if key == "stuck" else float
            out[key] = np.full(n, False if dtype is bool else np.nan, dtype=dtype)
        else:
            out[key] = np.array(np.broadcast_to(np.asarray(v), (n,)),
                                dtype=bool if key == "stuck" else float)
    # the actuator's "acting" views belong to the force of the step just taken (prefer them)
    for key, attr in ACTING_ATTRS.items():
        v = getattr(actuator, attr, None)
        if v is not None:
            out[key] = np.asarray(v, dtype=float).reshape(n).copy()
    return out


def cb_state(actuator: Any) -> dict[str, NDArray[Any]] | None:
    obj = cb_object(actuator)
    if obj is None:
        return None
    n = actuator.n_legs
    out = {}
    for key, names in CB_FIELDS.items():
        v = _get(obj, names)
        out[key] = (np.full(n, np.nan) if v is None
                    else np.array(np.broadcast_to(np.asarray(v, float), (n,)), dtype=float))
    return out


def pressure_force_N(actuator: Any, acting_force_N: NDArray[np.float64] | None = None
                     ) -> NDArray[np.float64]:
    """``F_p = F - f`` of the step just taken (module docstring)."""
    v = _get(actuator, PRESSURE_FORCE_ATTRS)
    if v is not None:
        return np.asarray(v, dtype=float).copy()
    f_act = actuator.acting_force_N if acting_force_N is None else acting_force_N
    st = friction_state(actuator)
    if st is None:
        return np.asarray(f_act, dtype=float).copy()
    f = np.nan_to_num(st["f_N"], nan=0.0)
    return np.asarray(f_act, dtype=float) - f


def piston_position_m(actuator: Any, s_link_m, acting_force_N) -> NDArray[np.float64]:
    """Stroke sensor truth: the friction state ``s_p`` when present, else ``s + F / k_out``."""
    fn = getattr(actuator, "stroke_sensor_true_m", None)
    if callable(fn):
        return np.asarray(fn(s_link_m), dtype=float).copy()
    st = friction_state(actuator)
    if st is not None and np.all(np.isfinite(st["s_p_m"])):
        return st["s_p_m"].copy()
    return actuator.stroke_true_m(s_link_m, acting_force_N)


def plant_available(params: Any) -> dict[str, bool]:
    """Which S8 YAML keys the loaded parameters carry."""
    def has(key: str) -> bool:
        try:
            params.get(key)
            return True
        except Exception:  # noqa: BLE001 - missing key in any form
            return False

    return {"seal_friction": has(FRICTION_LEVEL_KEY), "lock_valve": has(LOCK_VALVE_KEY)}


def seal_friction_overrides(params: Any, level_N: float) -> dict[str, Any]:
    """Overrides for the friction level (front leg Coulomb limit, U-S8-H1). Level 0 gives no
    override when the key does not exist (S7 plant)."""
    level = float(level_N)
    if not plant_available(params)["seal_friction"]:
        if level == 0.0:
            return {}
        raise PlantNotAvailableError(
            f"seal friction level {level:g} N needs {FRICTION_LEVEL_KEY} (hydraulics C-1) and the "
            "friction element (C-3); not installed")
    return {FRICTION_LEVEL_KEY: level}


def lock_valve_overrides(params: Any, lock_valve: str) -> dict[str, Any]:
    if lock_valve not in LOCK_VALVES:
        raise ValueError(f"lock_valve must be one of {LOCK_VALVES}: {lock_valve!r}")
    if not plant_available(params)["lock_valve"]:
        if lock_valve == "pilot_check":
            return {}
        raise PlantNotAvailableError("counterbalance needs actuator.lock_valve and the CB element")
    return {LOCK_VALVE_KEY: lock_valve}


def check_model(model: Any, level_N: float, lock_valve: str) -> dict[str, Any]:
    """After the build: the model has the elements the case asks for (refuse silently-ignored
    overrides). Returns the meta."""
    act = model.actuator
    fr = friction_object(act)
    cb = cb_object(act)
    if float(level_N) > 0.0 and fr is None:
        raise PlantNotAvailableError(
            f"F_s {level_N:g} N requested but L2bForceActuator has no friction element "
            f"(looked for {FRICTION_OBJECT_ATTRS})")
    if lock_valve == "counterbalance" and cb is None:
        raise PlantNotAvailableError("counterbalance requested but no CB element on the actuator")
    meta = getattr(fr, "meta", None)
    cb_meta = getattr(cb, "meta", None)
    return {"seal_friction_level_N": float(level_N), "lock_valve": lock_valve,
            "friction_element": None if fr is None else type(fr).__name__,
            "friction_meta": meta() if callable(meta) else None,
            "cb_element": None if cb is None else type(cb).__name__,
            "cb_meta": cb_meta() if callable(cb_meta) else None,
            "adapter": __name__}


def adapter_meta() -> Mapping[str, Any]:
    return {"friction_object_attrs": FRICTION_OBJECT_ATTRS, "friction_fields": FRICTION_FIELDS,
            "cb_object_attrs": CB_OBJECT_ATTRS, "cb_fields": CB_FIELDS,
            "pressure_force_attrs": PRESSURE_FORCE_ATTRS,
            "friction_level_key": FRICTION_LEVEL_KEY, "lock_valve_key": LOCK_VALVE_KEY}


__all__ = ["FRICTION_LEVEL_KEY", "LOCK_VALVES", "PlantNotAvailableError", "adapter_meta",
           "cb_state", "check_model", "friction_state", "lock_valve_overrides",
           "piston_position_m", "plant_available", "pressure_force_N", "seal_friction_overrides"]
