"""R-5 fallback-slope ratio source per simulation engine (P-S8-22, U-S8-61, control spec 304 (1)).

The R8-D1 preset (``C2Config().with_10hz_d1()``) runs the R-5 fallback slope
``nominal_gap`` with ``fallback_ratio_source = column_nominal``: the machine value, also used
for L2b-NSC and the SCM (S9 ``level``) runs. L1 / L1-R runs use ``plant_meta``: the fixed
ratio of the L1-R plant that the run was built with,

    R_i = k_r,i A_p,i / (k_h,i A_ann,i)

per leg, from :func:`outrigger_sim.chrono.rod_chamber_link.leg_params_from_params` of the
**plant** parameters (``model.params``, i.e. with the case overrides such as a sensitivity
``beta``): ``rod_stiffness_N_m``, ``head_stiffness_N_m``, ``head_area_m2``,
``annulus_area_m2``. YAML 2026-10-26 (top / bottom auger): FL / FR 1.29292, RL / RR 1.22779.

:func:`with_engine_fallback_ratio` is the one place the runners choose it. A config without
R-5 (``r8.fast_relevel`` None, e.g. the R7 ``C2Config()`` of stage 2) or with the
``level`` slope does not read the ratio and is returned unchanged.

No pychrono import at module level (``rod_chamber_link`` is imported inside
:func:`plant_fallback_ratio`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

PLANT_META = "plant_meta"
COLUMN_NOMINAL = "column_nominal"

ENGINE_RATIO_SOURCE: dict[str, str] = {
    "L1": PLANT_META,
    "L1R": PLANT_META,
    "L1-R": PLANT_META,
    "L2b": COLUMN_NOMINAL,
    "L2b_NSC": COLUMN_NOMINAL,
    "SCM": COLUMN_NOMINAL,
    "S9": COLUMN_NOMINAL,
}
"""Spec 304 (1) / U-S8-61: L1 runs ``plant_meta``, L2b-NSC and SCM keep the preset
``column_nominal``."""

RULE = "P-S8-22 / U-S8-61 (s6_control_spec 302.4, 304 (1)): L1 plant_meta, L2b / SCM column_nominal"

L1_FALLBACK_SOURCE_ENV = "OUTRIGGER_L1_FALLBACK_RATIO_SOURCE"
"""B(iii): comparison override of the L1 ratio source (``plant_meta`` / ``column_nominal``).
Set = meta ``fallback_ratio_source_override: env`` + a stdout warning; the batch runners refuse
to start with it unless ``--allow-env-override`` (:func:`refuse_env_override`). Single runs use
the CLI argument ``--fallback-ratio-source`` instead (``s9_merge/m3_run.py``)."""

L1_SOURCE_CHOICES = (PLANT_META, COLUMN_NOMINAL)

RATIO_PARAM_PREFIXES = (
    "actuator.oil_dead_length_m",
    "actuator.rod_dead_length_m",
    "actuator.rod_side",
    "actuator.oil_bulk_modulus_eff_Pa",
    "actuator.stroke_m",
    "actuator.bore_diameter_m",
    "actuator.rod_diameter_m",
    "actuator.annulus_area_m2",
    "contact.rigid_floor.L1.derivation.k_oil_N_m",
    "contact.rigid_floor.L1.derivation.operating_extension_m",
    "legs.",
)
"""Parameter paths that enter ``leg_params_from_params`` stiffnesses / areas (and so the
ratio); ``legs.`` is narrowed to ``legs.<leg>.cylinder``."""

DEAD_LENGTH_PREFIXES = (
    "actuator.oil_dead_length_m",          # L_0h
    "actuator.rod_dead_length_m",          # L_0r
    "actuator.rod_side.column_length_m",   # L_0r = column - (s_max - e_op)
)
"""B(i): an override of ``L_0h`` / ``L_0r`` changes the plant ratio away from the YAML value;
the meta marks it ``known_plant_ratio_upper`` (control decision 2026-10-26)."""


def _matches(key: str, prefix: str) -> bool:
    return key == prefix or key.startswith(prefix + ".")


def ratio_override_keys(plant_params: Any) -> list[str]:
    """Override keys of ``plant_params`` (``Params.overrides``) that enter the plant ratio."""
    overrides = getattr(plant_params, "overrides", None) or {}
    out = []
    for key in sorted(str(k) for k in overrides):
        if key.startswith("legs."):
            if ".cylinder" in key:
                out.append(key)
        elif any(_matches(key, p) for p in RATIO_PARAM_PREFIXES):
            out.append(key)
    return out


def plant_ratio_source_meta(plant_params: Any) -> dict[str, Any]:
    """B(i) ``fallback_plant_ratio_source``: ``plant_params``, the ratio-relevant override keys
    and whether ``L_0h`` / ``L_0r`` were overridden (``known_plant_ratio_upper``)."""
    keys = ratio_override_keys(plant_params)
    dead = [k for k in keys if any(_matches(k, p) for p in DEAD_LENGTH_PREFIXES)]
    return {"kind": "plant_params", "ratio_override_keys": keys,
            "dead_length_override_keys": dead, "known_plant_ratio_upper": bool(dead)}


def env_override_value() -> str | None:
    """Value of :data:`L1_FALLBACK_SOURCE_ENV` (None when unset / empty)."""
    import os

    value = os.environ.get(L1_FALLBACK_SOURCE_ENV, "").strip()
    return value or None


def refuse_env_override(allow: bool, runner: str) -> str | None:
    """Batch runners: SystemExit when :data:`L1_FALLBACK_SOURCE_ENV` is set and ``allow`` is
    False; with ``allow`` print the warning and return the value (None = unset)."""
    value = env_override_value()
    if value is None:
        return None
    if not allow:
        raise SystemExit(f"{runner}: {L1_FALLBACK_SOURCE_ENV}={value!r} is set; batch runs refuse "
                         "the L1 fallback-ratio override (U-S8-61). Unset it, or pass "
                         "--allow-env-override for a comparison batch.")
    print(f"WARNING {runner}: {L1_FALLBACK_SOURCE_ENV}={value!r} overrides the L1 R-5 fallback "
          "ratio source of every L1 case (--allow-env-override)", flush=True)
    return value


def ratio_from_leg_params(leg_params: Sequence[Any]) -> tuple[float, ...]:
    """``k_r A_p / (k_h A_ann)`` per leg of ``RodChamberLegParams``-like objects."""
    return tuple(
        float(lp.rod_stiffness_N_m) * float(lp.head_area_m2)
        / (float(lp.head_stiffness_N_m) * float(lp.annulus_area_m2))
        for lp in leg_params
    )


def plant_fallback_ratio(plant_params: Any) -> tuple[float, ...]:
    """L1-R plant ratio per leg (FL, FR, RL, RR) of ``plant_params`` (module docstring)."""
    from outrigger_sim.chrono.rod_chamber_link import leg_params_from_params

    legs, _records = leg_params_from_params(plant_params)
    return ratio_from_leg_params(legs)


def plant_fallback_ratio_of_model(model: Any) -> tuple[float, ...]:
    """L1-R plant ratio of a built L1 model: the leg parameters its rod-side machine holds
    (``model.rod_chamber.leg_params``), else :func:`plant_fallback_ratio` of ``model.params``
    (same function, so the same values; raises if the machine parameters cannot be built)."""
    chamber = getattr(model, "rod_chamber", None)
    legs = list(getattr(chamber, "leg_params", None) or [])
    if legs:
        return ratio_from_leg_params(legs)
    return plant_fallback_ratio(model.params)


def engine_ratio_source(engine: str) -> str:
    """Ratio source of ``engine`` (:data:`ENGINE_RATIO_SOURCE`); unknown engines raise."""
    try:
        return ENGINE_RATIO_SOURCE[engine]
    except KeyError:
        raise ValueError(
            f"unknown engine {engine!r} for the R-5 fallback ratio; {sorted(ENGINE_RATIO_SOURCE)}"
        ) from None


def with_engine_fallback_ratio(
    config: Any, engine: str, plant_params: Any = None, *,
    plant_ratio: Sequence[float] | None = None,
) -> tuple[Any, dict[str, Any]]:
    """``config`` with the R-5 fallback ratio source of ``engine``; returns (config, meta).

    * R-5 off (``config.r8.fast_relevel`` None) or ``fallback_slope`` not ``nominal_gap``:
      unchanged (``meta["applied"]`` False, ``reason``).
    * ``column_nominal`` engines (L2b-NSC, SCM): unchanged (the preset value is kept).
    * ``plant_meta`` engines (L1, L1-R): ``config.with_fallback_ratio_source("plant_meta",
      ratio)`` with ``ratio`` = ``plant_ratio`` if given, else :func:`plant_fallback_ratio`
      of ``plant_params``.

    Args:
        config: ``C2Config``.
        engine: ``L1`` / ``L1R`` / ``L2b_NSC`` / ``SCM`` (:data:`ENGINE_RATIO_SOURCE`).
        plant_params: Plant ``Params`` of the run (``model.params``); needed for
            ``plant_meta`` without ``plant_ratio``.
        plant_ratio: Precomputed per-leg ratio (tests, replays).
    """
    source = engine_ratio_source(engine)
    meta: dict[str, Any] = {"engine": engine, "source_rule": source, "rule": RULE}
    r8 = getattr(config, "r8", None)
    fast_relevel = getattr(r8, "fast_relevel", None)
    if fast_relevel is None:
        return config, {**meta, "applied": False, "reason": "R-5 off (r8.fast_relevel None)"}
    if not getattr(fast_relevel, "uses_fallback_slope", False):
        return config, {**meta, "applied": False,
                        "reason": f"fallback_slope {getattr(fast_relevel, 'fallback_slope', None)!s}"
                                  " (ratio not used)"}
    if source == COLUMN_NOMINAL:
        current = str(fast_relevel.fallback_ratio_source)
        return config, {**meta, "applied": False, "fallback_ratio_source": current,
                        "reason": "preset kept (L2b / SCM)"}
    if plant_ratio is None:
        if plant_params is None:
            raise ValueError(f"engine {engine!r}: plant_meta needs plant_params or plant_ratio")
        ratio = plant_fallback_ratio(plant_params)
        origin = "rod_chamber_link.leg_params_from_params(plant params)"
    else:
        ratio = tuple(float(v) for v in plant_ratio)
        origin = "given"
    out = config.with_fallback_ratio_source(PLANT_META, ratio)
    source_meta = (plant_ratio_source_meta(plant_params) if plant_params is not None
                   else {"kind": "given", "ratio_override_keys": None,
                         "dead_length_override_keys": None, "known_plant_ratio_upper": None})
    return out, {**meta, "applied": True, "fallback_ratio_source": PLANT_META,
                 "fallback_plant_ratio": list(ratio), "ratio_origin": origin,
                 "fallback_plant_ratio_source": source_meta,
                 "formula": "k_r A_p / (k_h A_ann) per leg (FL, FR, RL, RR)"}


def controller_meta_addendum(meta: dict[str, Any]) -> dict[str, Any]:
    """Keys a runner adds to the recorded ``controller_meta.r8.fast_relevel`` (B(i) / B(iii)):
    ``fallback_plant_ratio`` (as in the config), ``fallback_plant_ratio_source`` and
    ``fallback_ratio_source_override`` (None / ``env`` / ``cli``)."""
    return {"fallback_plant_ratio": meta.get("fallback_plant_ratio"),
            "fallback_plant_ratio_source": meta.get("fallback_plant_ratio_source"),
            "fallback_ratio_source_override": meta.get("fallback_ratio_source_override")}


def add_to_controller_meta(controller_meta: dict[str, Any], meta: dict[str, Any]) -> None:
    """Put :func:`controller_meta_addendum` into ``controller_meta['r8']['fast_relevel']`` (in
    place; nothing when R-5 is off, i.e. no ``fast_relevel`` mapping)."""
    fast = (controller_meta.get("r8") or {}).get("fast_relevel")
    if isinstance(fast, dict):
        add = controller_meta_addendum(meta)
        if fast.get("fallback_plant_ratio") is not None:
            add["fallback_plant_ratio"] = fast["fallback_plant_ratio"]  # the controller's own
        fast.update(add)


__all__ = [
    "COLUMN_NOMINAL",
    "ENGINE_RATIO_SOURCE",
    "L1_FALLBACK_SOURCE_ENV",
    "L1_SOURCE_CHOICES",
    "PLANT_META",
    "add_to_controller_meta",
    "controller_meta_addendum",
    "engine_ratio_source",
    "env_override_value",
    "plant_ratio_source_meta",
    "ratio_override_keys",
    "refuse_env_override",
    "plant_fallback_ratio",
    "plant_fallback_ratio_of_model",
    "ratio_from_leg_params",
    "with_engine_fallback_ratio",
]
