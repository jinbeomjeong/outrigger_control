"""Dynamic peak pad reaction of the open-loop lift, read from leg_extension_loads.json.

The checks that need "the largest pad reaction while the legs lift the body off the crawler"
(dynamics_model.md 3.7) used to carry the REXOME33-era constant 141 kN. They now read the
current result of ``run_leg_extension_loads.py`` instead, so the value follows the YAML.

Source block: ``validation / quasi_static_check (damped 3-DoF) / per_leg / <leg> /
peak_pad_force_N`` - the damped 3-DoF transition with the nominal leg damping (zeta 0.03),
auger top, crawler layout D. It is the same key path as
``outrigger_sim.verify.reference.LEG_EXTENSION_DAMPED_PEAK_PAD_FORCE_N``; this module does not
import 03_src so that the dynamics and CAD checks stay independent of the simulation code.

Pad reaction vs cylinder force: the pad reaction includes the rod weight
(F_pad = F_cyl + m_rod g, ``meta.cylinder_force_definition``). The block also stores
``max_peak_cylinder_force_N`` under the zeta sensitivity; callers that need the oil-column
force should read that key instead.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEG_EXTENSION_LOADS_JSON = PROJECT_ROOT / "06_analysis" / "00_dynamics" / "leg_extension_loads.json"
LEG_NAMES = ("FL", "FR", "RL", "RR")
DAMPED_PER_LEG_PATH = ("validation", "quasi_static_check (damped 3-DoF)", "per_leg")
PEAK_PAD_FORCE_KEY = "peak_pad_force_N"


class LegExtensionLoadsError(RuntimeError):
    """leg_extension_loads.json is missing or does not hold the expected peak keys."""


@dataclass(frozen=True)
class DynamicPeakPadForce:
    """Largest dynamic pad reaction over the four legs, with its provenance.

    Attributes:
        max_N: Largest per-leg peak pad reaction [N].
        max_leg: Leg that carries ``max_N``.
        per_leg_N: Peak pad reaction per leg in FL, FR, RL, RR order [N].
        source: File, key path, SHA-256 and producing script, for the result JSON.
    """

    max_N: float
    max_leg: str
    per_leg_N: tuple[float, ...]
    source: dict[str, Any]


def _project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def _walk(tree: Any, keys: tuple[str, ...], path: Path) -> Any:
    node = tree
    walked: list[str] = []
    for key in keys:
        walked.append(key)
        if not isinstance(node, dict) or key not in node:
            raise LegExtensionLoadsError(f"{path}: key {' / '.join(walked)!r} not found")
        node = node[key]
    return node


def load_dynamic_peak_pad_force(path: Path = LEG_EXTENSION_LOADS_JSON) -> DynamicPeakPadForce:
    """Read the per-leg dynamic peak pad reaction and return its maximum.

    Args:
        path: leg_extension_loads.json to read (default: the project result file).

    Returns:
        The maximum over the legs, the per-leg values and the provenance record.

    Raises:
        LegExtensionLoadsError: The file is missing, or a key or a numeric value is absent.
    """
    if not path.is_file():
        raise LegExtensionLoadsError(
            f"{path} not found; run 04_scripts/01_dynamics/run_leg_extension_loads.py first"
        )
    raw = path.read_bytes()
    tree = json.loads(raw.decode("utf-8"))
    per_leg_N = []
    for leg in LEG_NAMES:
        value = _walk(tree, (*DAMPED_PER_LEG_PATH, leg, PEAK_PAD_FORCE_KEY), path)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            key = " / ".join((*DAMPED_PER_LEG_PATH, leg, PEAK_PAD_FORCE_KEY))
            raise LegExtensionLoadsError(f"{path}: {key} is not a number")
        per_leg_N.append(float(value))
    max_index = max(range(len(LEG_NAMES)), key=lambda i: per_leg_N[i])
    meta = tree.get("meta", {})
    source = {
        "file": _project_relative(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "key": " / ".join((*DAMPED_PER_LEG_PATH, "<leg>", PEAK_PAD_FORCE_KEY)),
        "reduction": "max over FL, FR, RL, RR",
        "quantity": "pad reaction incl. rod weight (F_pad = F_cyl + m_rod g)",
        "producer": meta.get("script"),
        "producer_params": meta.get("params"),
        "auger_level": meta.get("auger_level"),
        "mass_case": meta.get("mass_case"),
    }
    return DynamicPeakPadForce(
        max_N=per_leg_N[max_index],
        max_leg=LEG_NAMES[max_index],
        per_leg_N=tuple(per_leg_N),
        source=source,
    )
