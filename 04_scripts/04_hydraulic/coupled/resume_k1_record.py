"""Record-only LAS-b / K1 order-gate block of one harness run (436.8 rules, ``v5_resume_4368_rules.md``).

The 436.8 judgement reads, per harness line, the same quantities a Chrono ``result.json`` keeps
under
``c2_setup`` and ``controller_meta`` (rules 4.2 record check, 7.2 K1 classification). The harness
lines had
none of them, so every harness runner of the 436.8 bundles adds this block under :data:`RECORD_KEY`
after the
run. It reads the controller only (``meta()`` and ``events``): commands, hashes and verdicts do not
change.

Block (``RECORD_KEY``):
  applicable                       False for a controller without a C2 configuration (IND / IND_LAS)
  k1_order_gate_request            ``preset`` (harness runs never request a gate) or the D8x job's ``on`` / ``off``
  k1_order_gate_effective          ``config.slope_clearance_margin.flat_soil_margin_order_gate``
  liftoff_approach_slow            ``settings`` (the 9 values of run_S9 ``_LAS_EXPECTATIONS``), ``start_s``,
                                   ``end_s``, ``end_reason`` (controller meta; absent when the meta
                                   lacks them)
  slope_clearance_margin           ``settings.enable``, ``settings.flat_soil_margin_order_gate``,
                                   ``settings.flat_soil_margin_m``,
                                   ``order_gate`` (``enabled``, ``decisions``: controller meta as it
                                   is)
  event_counts                     over all controller events (the stored event lists drop some names):
                                   ``flat_soil_margin_applied``
                                   (``INFO_LOC_FLAT_SOIL_MARGIN:<mm>``),
                                   ``flat_soil_margin_skipped_order``
                                   (``INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order``),
                                   ``soil_mode_start`` (``soil_mode_start``)
"""

from __future__ import annotations

from typing import Any

RECORD_KEY = "resume_k1"
REQUEST_PRESET = "preset"
LAS_SETTING_NAMES = (
    "enable",
    "sum_on_fraction_W",
    "light_leg_fraction_of_F_min",
    "slow_mean_fraction",
    "sum_off_fraction_W",
    "off_periods",
    "max_s",
    "rho_on",
    "require_soil_response",
)
"""The 9 LAS-b settings run_S9 ``_LAS_EXPECTATIONS`` checks (436.8 rules 4.2 "9값")."""
APPLIED_EVENT_PREFIX = "INFO_LOC_FLAT_SOIL_MARGIN:"
"""R4c30 applied: ``c2.FLAT_SOIL_MARGIN_EVENT`` + ``:<target mm>``."""
SKIPPED_ORDER_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"
"""``c2.FLAT_SOIL_MARGIN_ORDER_SKIP_EVENT``."""
SOIL_MODE_START_EVENT = "soil_mode_start"
"""``c2.SOIL_EVENT_MODE_START``."""


def _plain(value: Any) -> Any:
    """JSON-safe copy (numpy scalars, enums and tuples of the meta)."""
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def event_counts(names: list[str]) -> dict[str, int]:
    """The three event counts of the block from the controller event names."""
    return {
        "flat_soil_margin_applied": sum(name.startswith(APPLIED_EVENT_PREFIX) for name in names),
        "flat_soil_margin_skipped_order": sum(name == SKIPPED_ORDER_EVENT for name in names),
        "soil_mode_start": sum(name == SOIL_MODE_START_EVENT for name in names),
    }


def controller_record(controller: Any, *, request: str = REQUEST_PRESET) -> dict[str, Any]:
    """The :data:`RECORD_KEY` block of a finished run's controller (module docstring).

    Args:
        controller: The run's controller (a C2 controller, or a C8-skeleton controller without one).
        request: The gate request of the run (``preset`` unless a D8x job set it).
    """
    config = getattr(controller, "config", None)
    margin_config = getattr(config, "slope_clearance_margin", None)
    if margin_config is None or not callable(getattr(controller, "meta", None)):
        return {"applicable": False, "reason": "no C2 configuration (C8 skeleton)"}
    meta = controller.meta()
    las = meta.get("liftoff_approach_slow") or {}
    las_settings = las.get("settings") or {}
    margin = meta.get("slope_clearance_margin") or {}
    margin_settings = margin.get("settings") or {}
    names = [str(event.name) for event in getattr(controller, "events", [])]
    return _plain(
        {
            "applicable": True,
            "k1_order_gate_request": request,
            "k1_order_gate_effective": bool(margin_config.flat_soil_margin_order_gate),
            # start_s / end_s / end_reason only when the meta has them: a missing key stays missing
            # (436.8 rules 7.2 / 9.3: absent is "판정 불가", not "미작동")
            "liftoff_approach_slow": {
                "settings": {name: las_settings.get(name) for name in LAS_SETTING_NAMES},
                **{key: las[key] for key in ("start_s", "end_s", "end_reason") if key in las},
            },
            "slope_clearance_margin": {
                "settings": {
                    # las_targeted_rules_rev5 2.2: every line shows R4c30 is on (z4371)
                    "enable": margin_settings.get("enable"),
                    "flat_soil_margin_order_gate": margin_settings.get(
                        "flat_soil_margin_order_gate"
                    ),
                    "flat_soil_margin_m": margin_settings.get("flat_soil_margin_m"),
                },
                "order_gate": margin.get("order_gate"),
            },
            "event_counts": event_counts(names),
        }
    )
