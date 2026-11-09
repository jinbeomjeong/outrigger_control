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

Two more readers replace REXOME33-era constants of ``run_mast_bending_check.py``:

* ``load_crawler_handover_window`` - quasi-static first pad touch -> crawler load 0
  (``key_values / events_s``), cross-checked against ``reference.json``
  ``lift_V4_compliant_crawler`` layout D. Replaces 15.584 - 15.050 = 0.534 s.
* ``load_dynamic_deviation`` - largest |damped 3-DoF - quasi-static| pad reaction difference
  (leg zeta 0.03), cross-checked against the zeta sensitivity case. Replaces 23.2 kN.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEG_EXTENSION_LOADS_JSON = PROJECT_ROOT / "06_analysis" / "00_dynamics" / "leg_extension_loads.json"
REFERENCE_JSON = PROJECT_ROOT / "06_analysis" / "00_dynamics" / "reference.json"
LEG_NAMES = ("FL", "FR", "RL", "RR")
DAMPED_CHECK_PATH = ("validation", "quasi_static_check (damped 3-DoF)")
DAMPED_PER_LEG_PATH = (*DAMPED_CHECK_PATH, "per_leg")
PEAK_PAD_FORCE_KEY = "peak_pad_force_N"

EVENTS_PATH = ("key_values", "events_s")
CRAWLER_OFF_KEY = "crawler_off"
REFERENCE_LAYOUT_D = "D rollers + gapped end shoes (YAML contact.crawler.sphere_layout)"
REFERENCE_EVENTS_PATH = (
    "lift_V4_compliant_crawler",
    "layouts",
    REFERENCE_LAYOUT_D,
    "quasi_static_events_s",
)
# reference.json rounds the event times to 1 ms; 1.5 ms allows that rounding plus a margin.
REFERENCE_EVENT_TOLERANCE_S = 1.5e-3
# Two legs touching within 1 ms of each other are a near tie: a different first leg is then
# only a warning (the rounded reference may name the other leg).
FIRST_TOUCH_TIE_S = 1.0e-3
HANDOVER_DEFINITION = (
    "quasi-static first pad touch -> quasi-static crawler load 0, layout D, top, mass case C"
)
HANDOVER_REPLACES = (
    "REXOME33 constant 15.584 - 15.050 = 0.534 s (mixed: quasi-static off, dynamic FL touch)"
)

DEVIATION_KEY = "max_abs_diff_pad_N (FL, FR, RL, RR)"
DEVIATION_AT_KEY = "max_abs_diff_pad_N_at_s"
ZETA_SENSITIVITY_PATH = ("validation", "quasi_static_check_leg_zeta_sensitivity")
# Only the nominal leg zeta 0.03 case; the zeta 0.1 case happens to hold 23220 N, which looks
# like the old 23.2 kN constant but is a different damping.
NOMINAL_ZETA_CASE_PATH = (*ZETA_SENSITIVITY_PATH, "cases", "zeta_leg_0.03")
CASE_DEVIATION_KEY = "max_abs_diff_vs_quasi_static_N"
NOMINAL_CRAWLER_ZETA = 0.05
DEVIATION_CROSS_CHECK_REL_TOL = 1e-6
DEVIATION_QUANTITY = (
    "max |F_pad(damped 3-DoF, leg zeta 0.03, crawler zeta 0.05) - F_pad(quasi-static)|"
    " over legs and time"
)


class LegExtensionLoadsError(RuntimeError):
    """leg_extension_loads.json is missing or does not hold the expected peak keys."""


@dataclass(frozen=True)
class CrawlerHandoverWindow:
    """Quasi-static crawler hand-over window of the open-loop lift, with its provenance.

    Attributes:
        first_touch_s: Earliest quasi-static pad touch over the four legs [s].
        first_touch_leg: Leg that touches first.
        crawler_off_s: Quasi-static time the crawler floor load reaches 0 [s].
        duration_s: ``crawler_off_s - first_touch_s`` [s].
        source: Files, SHA-256, key paths, definition and reference cross-check.
    """

    first_touch_s: float
    first_touch_leg: str
    crawler_off_s: float
    duration_s: float
    source: dict[str, Any]


@dataclass(frozen=True)
class DynamicDeviation:
    """Largest dynamic-minus-quasi-static pad reaction difference, with its provenance.

    Attributes:
        max_N: Largest per-leg |difference| [N].
        max_leg: Leg that carries ``max_N``.
        per_leg_N: Per-leg maximum |difference| in FL, FR, RL, RR order [N].
        at_s: Time of the largest difference [s].
        source: File, key paths, SHA-256 and the cross-check record.
    """

    max_N: float
    max_leg: str
    per_leg_N: tuple[float, ...]
    at_s: float
    source: dict[str, Any]


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


def _key_text(keys: tuple[str, ...]) -> str:
    return " / ".join(keys)


def _read_json(path: Path, producer_hint: str) -> tuple[bytes, Any]:
    if not path.is_file():
        raise LegExtensionLoadsError(f"{path} not found; {producer_hint}")
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def _number(tree: Any, keys: tuple[str, ...], path: Path) -> float:
    value = _walk(tree, keys, path)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise LegExtensionLoadsError(f"{path}: {_key_text(keys)} is not a number")
    return float(value)


def _file_record(path: Path, raw: bytes) -> dict[str, str]:
    return {"file": _project_relative(path), "sha256": hashlib.sha256(raw).hexdigest()}


def _check_against_reference(
    window: tuple[float, str, float],
    touch_s: dict[str, float],
    reference: tuple[float, str, float],
    reference_path: Path,
) -> float:
    """Compare (first touch, first leg, crawler off) with reference.json; return the max |diff|."""
    first_touch_s, first_touch_leg, crawler_off_s = window
    ref_touch_s, ref_leg, ref_off_s = reference
    diffs = {"first touch": first_touch_s - ref_touch_s, "crawler off": crawler_off_s - ref_off_s}
    for label, diff in diffs.items():
        if abs(diff) > REFERENCE_EVENT_TOLERANCE_S:
            raise LegExtensionLoadsError(
                f"{label} differs from {reference_path} by {diff * 1e3:.3f} ms "
                f"(> {REFERENCE_EVENT_TOLERANCE_S * 1e3:g} ms); rerun the lift checks"
            )
    if ref_leg != first_touch_leg:
        if ref_leg not in touch_s:
            raise LegExtensionLoadsError(f"{reference_path}: unknown first_touch_leg {ref_leg!r}")
        tie_gap_s = touch_s[ref_leg] - first_touch_s
        if tie_gap_s > FIRST_TOUCH_TIE_S:
            raise LegExtensionLoadsError(
                f"first touch leg {first_touch_leg} differs from {reference_path} ({ref_leg}); "
                f"{ref_leg} touches {tie_gap_s * 1e3:.3f} ms later"
            )
        warnings.warn(
            f"first touch leg {first_touch_leg} vs reference {ref_leg}: near tie "
            f"({tie_gap_s * 1e3:.3f} ms <= {FIRST_TOUCH_TIE_S * 1e3:g} ms)",
            stacklevel=3,
        )
    return max(abs(diff) for diff in diffs.values())


def load_crawler_handover_window(
    path: Path = LEG_EXTENSION_LOADS_JSON, ref_path: Path = REFERENCE_JSON
) -> CrawlerHandoverWindow:
    """Read the quasi-static crawler hand-over window (first pad touch -> crawler off).

    Args:
        path: leg_extension_loads.json to read (default: the project result file).
        ref_path: reference.json holding the independent layout-D quasi-static events.

    Returns:
        The window and its provenance record.

    Raises:
        LegExtensionLoadsError: A file or key is missing, a value is not a number, the window
            is not positive, or the events disagree with reference.json (more than 1.5 ms, or
            another first leg that is not a near tie within 1 ms).
    """
    raw, tree = _read_json(path, "run 04_scripts/01_dynamics/run_leg_extension_loads.py first")
    ref_raw, ref_tree = _read_json(ref_path, "reference.json is a tracked project result")

    touch_s = {leg: _number(tree, (*EVENTS_PATH, f"touch_{leg}"), path) for leg in LEG_NAMES}
    first_touch_leg = min(LEG_NAMES, key=lambda leg: touch_s[leg])
    first_touch_s = touch_s[first_touch_leg]
    crawler_off_s = _number(tree, (*EVENTS_PATH, CRAWLER_OFF_KEY), path)
    duration_s = crawler_off_s - first_touch_s
    if duration_s <= 0.0:
        raise LegExtensionLoadsError(
            f"{path}: crawler_off ({crawler_off_s}) is not after the first touch ({first_touch_s})"
        )

    ref_leg = _walk(ref_tree, (*REFERENCE_EVENTS_PATH, "first_touch_leg"), ref_path)
    reference = (
        _number(ref_tree, (*REFERENCE_EVENTS_PATH, "first_touch_s"), ref_path),
        str(ref_leg),
        _number(ref_tree, (*REFERENCE_EVENTS_PATH, "crawler_fully_off_s"), ref_path),
    )
    max_diff_s = _check_against_reference(
        (first_touch_s, first_touch_leg, crawler_off_s), touch_s, reference, ref_path
    )

    source = {
        "leg_extension_loads": dict(
            _file_record(path, raw),
            keys=[
                _key_text((*EVENTS_PATH, "touch_<leg>")),
                _key_text((*EVENTS_PATH, CRAWLER_OFF_KEY)),
            ],
        ),
        "reference": dict(
            _file_record(ref_path, ref_raw),
            key=_key_text(REFERENCE_EVENTS_PATH),
            fields=["first_touch_s", "crawler_fully_off_s", "first_touch_leg"],
        ),
        "definition": HANDOVER_DEFINITION,
        "reference_check_max_abs_diff_s": max_diff_s,
        "replaces": HANDOVER_REPLACES,
    }
    return CrawlerHandoverWindow(
        first_touch_s=first_touch_s,
        first_touch_leg=first_touch_leg,
        crawler_off_s=crawler_off_s,
        duration_s=duration_s,
        source=source,
    )


def _per_leg_deviation(tree: Any, path: Path) -> tuple[float, ...]:
    keys = (*DAMPED_CHECK_PATH, DEVIATION_KEY)
    values = _walk(tree, keys, path)
    if not isinstance(values, list) or len(values) != len(LEG_NAMES):
        raise LegExtensionLoadsError(f"{path}: {_key_text(keys)} is not a list of four numbers")
    for value in values:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise LegExtensionLoadsError(f"{path}: {_key_text(keys)} holds a non-number")
    return tuple(float(value) for value in values)


def load_dynamic_deviation(path: Path = LEG_EXTENSION_LOADS_JSON) -> DynamicDeviation:
    """Read the largest dynamic-minus-quasi-static pad reaction difference (leg zeta 0.03).

    Args:
        path: leg_extension_loads.json to read (default: the project result file).

    Returns:
        The maximum over the legs, the per-leg values, its time and the provenance record.

    Raises:
        LegExtensionLoadsError: The file or a key is missing, a value is not a number, the
            nominal zeta case disagrees (relative difference > 1e-6), or its crawler zeta is
            not 0.05.
    """
    raw, tree = _read_json(path, "run 04_scripts/01_dynamics/run_leg_extension_loads.py first")
    per_leg_N = _per_leg_deviation(tree, path)
    at_s = _number(tree, (*DAMPED_CHECK_PATH, DEVIATION_AT_KEY), path)
    max_index = max(range(len(LEG_NAMES)), key=lambda i: per_leg_N[i])
    max_N = per_leg_N[max_index]

    crawler_zeta = _number(tree, (*ZETA_SENSITIVITY_PATH, "crawler_zeta"), path)
    if crawler_zeta != NOMINAL_CRAWLER_ZETA:
        raise LegExtensionLoadsError(
            f"{path}: crawler_zeta {crawler_zeta} of the zeta sensitivity is not "
            f"{NOMINAL_CRAWLER_ZETA}"
        )
    case_N = _number(tree, (*NOMINAL_ZETA_CASE_PATH, CASE_DEVIATION_KEY), path)
    rel_diff = abs(case_N - max_N) / max(abs(max_N), 1e-12)
    if rel_diff > DEVIATION_CROSS_CHECK_REL_TOL:
        raise LegExtensionLoadsError(
            f"{path}: {_key_text((*NOMINAL_ZETA_CASE_PATH, CASE_DEVIATION_KEY))} = {case_N} "
            f"differs from max({DEVIATION_KEY}) = {max_N} (relative {rel_diff:.3g})"
        )

    source = dict(
        _file_record(path, raw),
        key=_key_text((*DAMPED_CHECK_PATH, DEVIATION_KEY)),
        at_key=_key_text((*DAMPED_CHECK_PATH, DEVIATION_AT_KEY)),
        reduction="max over FL, FR, RL, RR",
        quantity=DEVIATION_QUANTITY,
        cross_check_key=_key_text((*NOMINAL_ZETA_CASE_PATH, CASE_DEVIATION_KEY)),
        cross_check_rel_diff=rel_diff,
        replaces="REXOME33 constant 23.2 kN",
    )
    return DynamicDeviation(
        max_N=max_N,
        max_leg=LEG_NAMES[max_index],
        per_leg_N=per_leg_N,
        at_s=at_s,
        source=source,
    )


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
