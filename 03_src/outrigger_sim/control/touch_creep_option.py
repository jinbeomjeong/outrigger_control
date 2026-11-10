"""Runner option ``--k2 {preset,off,on}`` of the K-2 TOUCH creep latch.

K-2 (``C2Config.touch_creep_latch``, :class:`~outrigger_sim.control.c2.TouchCreepLatchSettings`)
is off in the class and in the preset, so ``preset`` (the default, also an absent option) leaves
a run as it was; ``off`` / ``on`` set ``touch_creep_latch.enable`` explicitly, the way
``--k1-order-gate`` sets the LAS-b K1 order gate. Every run records the request and the value
the built controller holds, so an audit sees a wrapper and the preset applied twice.

One option word ``--k2`` (``k2_touch_creep_rules.md`` 9.1-3; ``acc_d8.py --k2 on|off`` takes no
``preset``). Records:
  * ``run_S9 level``: ``c2_setup.touch_creep`` / ``c2_setup.touch_creep_effective``
    (:func:`touch_creep_record`);
  * other runners (the Chrono L1-R / L2b runners are cad-expert's, rules 9.3):
    ``touch_creep_requested`` / ``touch_creep_effective`` (:func:`touch_creep_run_record`);
  * the controller meta block ``controller_meta.touch_creep_latch`` (settings, latches).
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from typing import Any

TOUCH_CREEP_OPTION = "--k2"
TOUCH_CREEP_DEST = "k2"
TOUCH_CREEP_PRESET = "preset"
TOUCH_CREEP_CHOICES = (TOUCH_CREEP_PRESET, "off", "on")


def add_touch_creep_argument(parser: argparse.ArgumentParser) -> None:
    """Add :data:`TOUCH_CREEP_OPTION` to ``parser``.

    Absent, the namespace gets no attribute (``argparse.SUPPRESS``), so ``vars(args)`` of a run
    without the option stays as before; :func:`touch_creep_request` reads it as preset.
    """
    parser.add_argument(
        TOUCH_CREEP_OPTION,
        dest=TOUCH_CREEP_DEST,
        choices=TOUCH_CREEP_CHOICES,
        default=argparse.SUPPRESS,
        help="K-2 TOUCH creep latch (touch_creep_latch.enable, not adopted): preset (default) "
        "keeps the preset value (off), on / off set it explicitly and are checked on the built "
        "controller. Absent = preset, no attribute",
    )


def touch_creep_request(args: argparse.Namespace) -> str:
    """The ``--k2`` request; :data:`TOUCH_CREEP_PRESET` when the namespace has none.

    Raises:
        SystemExit: A value outside :data:`TOUCH_CREEP_CHOICES`.
    """
    request = getattr(args, TOUCH_CREEP_DEST, None)
    if request is None:
        return TOUCH_CREEP_PRESET
    if request not in TOUCH_CREEP_CHOICES:
        raise SystemExit(
            f"{TOUCH_CREEP_OPTION} must be one of {TOUCH_CREEP_CHOICES}, got {request!r}"
        )
    return request


def is_explicit_request(request: str) -> bool:
    """``off`` / ``on``: the request sets the value instead of keeping the preset."""
    return request != TOUCH_CREEP_PRESET


def with_touch_creep(config: Any, request: str) -> Any:
    """``config`` with ``touch_creep_latch.enable`` set by an explicit request (unchanged for
    preset)."""
    if not is_explicit_request(request):
        return config
    latch = replace(config.touch_creep_latch, enable=request == "on")
    return replace(config, touch_creep_latch=latch)


def is_touch_creep_enabled(config: Any) -> bool:
    """``touch_creep_latch.enable`` of a C2 config (False for a config without the block)."""
    return bool(getattr(getattr(config, "touch_creep_latch", None), "enable", False))


def touch_creep_record(request: str, config: Any) -> dict[str, Any]:
    """``{"touch_creep": request, "touch_creep_effective": enable}`` (``run_S9 c2_setup``)."""
    return {"touch_creep": request, "touch_creep_effective": is_touch_creep_enabled(config)}


def touch_creep_run_record(request: str, config: Any) -> dict[str, Any]:
    """``{"touch_creep_requested": request, "touch_creep_effective": enable}`` (S6C / S8C)."""
    return {
        "touch_creep_requested": request,
        "touch_creep_effective": is_touch_creep_enabled(config),
    }


def check_built_touch_creep(request: str, config: Any) -> None:
    """Refuse a built controller whose ``touch_creep_latch.enable`` differs from an explicit
    request.

    Raises:
        SystemExit: The config does not hold the requested value.
    """
    if not is_explicit_request(request):
        return
    if is_touch_creep_enabled(config) is not (request == "on"):
        raise SystemExit(
            f"{TOUCH_CREEP_OPTION} {request}: the built controller has "
            f"touch_creep_latch.enable = {is_touch_creep_enabled(config)!r}"
        )
