"""Run-time L1-R switch of the Chrono run scripts (bundle B, dynamics_model.md 5.12 / 4097 table).

The YAML keeps ``actuator.rod_side.mechanics: "off"`` (single source of parameters, not edited by
hand) and the params loader cannot read that text key, so the run scripts pass the mechanics as
the ``L1Model(rod_side_mechanics=...)`` override. The value comes from the environment variable
:data:`ENV_MECHANICS` so that the spawned case processes of ``outrigger_sim.batch`` see the same
setting as their parent.

* unset / ``""``: no override, the YAML value (``off``): bundle A behaviour, bit for bit;
* ``one_sided_parallel``: L1-R on (bundle B);
* ``off``: explicit off (regression runs that must not mix with bundle A outputs).

Every output root of a run with an explicit value gets the suffix :func:`suffix` (``_L1R`` /
``_L1Roff``), so the bundle-B results, indexes and summaries never overwrite bundle A ones
(the index guard keys on the params sha256, which an override does not change).

Not supported with L1-R on (``chrono/rod_chamber_link`` docstring): the
``stroke_model="extension"`` truth. Ground-settlement legs are supported since 2026-10-22 (the
deflection is measured against the moving patch body): :func:`mechanics_for` returns the same
override with or without settlement legs and :func:`fallback_note` is always None. Bundle-B
results before that date ran the settlement cases with mechanics ``"off"`` (their meta
``l1r.fallback`` says so).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ENV_MECHANICS = "OUTRIGGER_ROD_SIDE_MECHANICS"
ALLOWED = ("off", "one_sided_parallel")


def mechanics() -> str | None:
    """Override from the environment (``None`` = no override, YAML value)."""
    value = os.environ.get(ENV_MECHANICS, "").strip()
    if not value:
        return None
    if value not in ALLOWED:
        raise SystemExit(f"{ENV_MECHANICS}={value!r}: expected one of {ALLOWED}")
    return value


def is_on() -> bool:
    return mechanics() == "one_sided_parallel"


def mechanics_for(*, settlement: bool = False) -> str | None:  # noqa: ARG001 - kept API
    """The override for one model (the same with or without settlement legs)."""
    return mechanics()


def fallback_note(*, settlement: bool) -> str | None:  # noqa: ARG001 - kept API
    """Why a case ran with another mechanics than the bundle: never (None) since settlement
    legs support L1-R."""
    return None


def suffix() -> str:
    """Output-root suffix: ``""`` without override, ``_L1R`` on, ``_L1Roff`` explicit off."""
    value = mechanics()
    if value is None:
        return ""
    return "_L1R" if value == "one_sided_parallel" else "_L1Roff"


def tagged(path: Path) -> Path:
    """``path`` with :func:`suffix` added to its last name (before the extension of a file)."""
    s = suffix()
    if not s:
        return path
    if path.suffix:
        return path.with_name(path.stem + s + path.suffix)
    return path.with_name(path.name + s)


def meta() -> dict[str, Any]:
    return {"env": ENV_MECHANICS, "rod_side_mechanics_override": mechanics(),
            "output_suffix": suffix(),
            "note": "None = YAML actuator.rod_side.mechanics (off); see l1r_variant docstring"}


__all__ = ["ENV_MECHANICS", "fallback_note", "is_on", "mechanics", "mechanics_for", "meta",
           "suffix", "tagged"]
