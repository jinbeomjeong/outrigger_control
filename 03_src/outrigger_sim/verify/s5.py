"""S5 checks: auger three levels (V0 auger composition, V10 = V1 + modes 1-2 per level).

``00_docs/03_chrono/chrono_build_plan.md`` S5; ``dynamics_model.md`` 5 V10 row (rev. 13,
option A). Engine independent: inputs are YAML mass properties, still-window means and the
identification rows of ``verify/metrics`` (through ``verify.s4``). Automatic pass / fail is a
pre-check; the physical judgement is the dynamics-expert's.

V0 (auger) (``dynamics_model.md`` 5.9, rev. 22, user decision U1 = (a), 2026-10-21):
``superstructure.fixed_part`` + ``superstructure.auger_moving_set_at_cad_pose`` translated by
``auger_travel_m`` along body z must give ``superstructure.auger_levels.<level>`` (mass, centre
of mass, inertia about the centre of mass, body axes).

* Judged (row ``V0(auger)``): every one of the 10 elements (mass, CoM xyz, Ixx Iyy Izz Ixy Ixz
  Iyz) within its printed-digit rounding bound ``h_ref + sum_k |dy/dx_k| h_k``
  (:func:`composition_rounding_bound`). The YAML prints 9 significant digits, so the plan 1e-9
  cannot be guaranteed: the rounding bound alone is ~1.4e-8 (mass) to ~1.7e-8 (inertia).
* The travel is exact (the exporter composes the level from ``auger_levels.json`` ``travel_mm``
  and writes the same number), so the bound has no travel term; row ``V0(auger) travel``
  checks that premise (:func:`auger_travel_check`).
* Recorded (id ``info``): the plan 1e-9 metrics -- mass relative, CoM absolute [m], inertia
  ``max |dI| / max |I|``.

This differs from ``verify.s1`` V0 on purpose: S1 checks that Chrono copies the YAML doubles,
so it uses an element-wise relative 1e-9 (an exact copy); S5 checks the consistency of numbers
that were rounded before they were written, so it uses the element-wise rounding bound.

V10 per level (plan S5 table; load rule per user decision U2 = B, 2026-10-21):

* V1 (judged): still-window mean pad contact force per leg vs the independent P-delta
  nonlinear solution (``s1_pdelta_check.json`` ``<level>.nonlinear_contact_N``),
  ``|diff| <= 0.01 % W/4`` (W = ``statics / total_weight_incl_rods_N``); the sum of the pad
  contact forces vs W at the S1 tolerance (1e-4 rel).
* V1 (recorded, id ``info``): the same forces vs the linear reference
  ``levels / <level> / contact_force_N`` at 1 % W/4 (the S1 V1 tolerance). The difference is
  the P-delta share, which grows with W^2 while the tolerance grows with W.
* modes 1-2: judged natural frequency (``verify.s4.judged_value``: projection fit on the level
  mode shapes, ERA where the fit residual or the ERA cross-check fails) within +-3 % of
  ``V7_ball_centre_bushing_rev13 / f_damped_Hz`` (``|lambda| / 2 pi`` = natural frequency of
  that damped mode, the S2a / S4 rule); the ``f_undamped_Hz`` difference is recorded.
* order: modes 1 and 2 each rise strictly top < middle < bottom.
* zeta (minus ``r omega dt / 2``) is recorded against the level reference (information,
  +-30 % as in V7).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.verify.checks import CheckResult, check_abs, check_equal, check_max, check_rel
from outrigger_sim.verify.s1 import (
    V0_POS_ABS_TOL_M,
    V0_REL_TOL,
    V1_LEG_FRACTION_OF_QUARTER_WEIGHT,
    V1_SUM_REL_TOL,
)
from outrigger_sim.verify.s2a import V7_FREQ_REL_TOL, V7_ZETA_REL_TOL
from outrigger_sim.verify.s4 import ModeRow, judged_value

LEVELS = ("top", "middle", "bottom")
"""YAML ``superstructure.auger_level_order`` (checked by the tests)."""
V10_MODES = (0, 1)
"""0-based modes judged by V10 (first two)."""
V10_EXCITATIONS = ("roll", "pitch")
V10_PDELTA_FRACTION_OF_QUARTER_WEIGHT = 1.0e-4
"""V10 V1 judged: Chrono - P-delta nonlinear solution <= 0.01 % W/4 (rev. 22, U2 = B). About 4x
the float32 contact-distance quantum k_n ulp ~ 2.5 N per pad."""
V10_LINEAR_FRACTION_OF_QUARTER_WEIGHT = V1_LEG_FRACTION_OF_QUARTER_WEIGHT
"""V10 V1 recorded: Chrono - linear reference <= 1 % W/4 (the S1 V1 tolerance, rev. 22)."""
AUGER_TRAVEL_ABS_TOL_M = 1.0e-12
"""YAML ``auger_travel_m`` vs ``auger_levels.json`` ``travel_mm`` x 1e-3 (same printed number)."""
PDELTA_CONTACT_KEY = "nonlinear_contact_N"
"""Per-level key of the P-delta pad contact forces in ``s1_pdelta_check.json``."""
V0_INFO_NOTE = "9 significant digits printed: not reachable, rev. 22 (recorded)"
MASS_PROPS_ELEMENTS = ("mass", "com x", "com y", "com z", "Ixx", "Iyy", "Izz", "Ixy", "Ixz",
                       "Iyz")
"""Order of :func:`_flatten` (units kg, m x3, kg m^2 x6)."""


# --- V0 (auger) --------------------------------------------------------------------------------


@dataclass(frozen=True)
class MassProps:
    """Mass [kg], centre of mass [m] and inertia about it [kg m^2], body axes."""

    mass_kg: float
    com_m: NDArray[np.float64]
    inertia_kg_m2: NDArray[np.float64]

    @classmethod
    def from_mapping(cls, block: Mapping) -> MassProps:
        """From a YAML block with ``mass_kg``, ``com_m``, ``inertia_kg_m2``."""
        return cls(float(block["mass_kg"]), np.asarray(block["com_m"], dtype=float),
                   np.asarray(block["inertia_kg_m2"], dtype=float))


def _shift(mass: float, r: NDArray[np.float64]) -> NDArray[np.float64]:
    """Parallel-axis term ``m (|r|^2 I - r r^T)``."""
    return mass * (float(r @ r) * np.eye(3) - np.outer(r, r))


def compose_auger_level(fixed: MassProps, moving: MassProps, travel_m: float) -> MassProps:
    """Fixed part + moving set translated by ``travel_m`` along body +z (no rotation)."""
    com_moving = moving.com_m + np.array([0.0, 0.0, float(travel_m)])
    mass = fixed.mass_kg + moving.mass_kg
    com = (fixed.mass_kg * fixed.com_m + moving.mass_kg * com_moving) / mass
    inertia = (fixed.inertia_kg_m2 + _shift(fixed.mass_kg, fixed.com_m - com)
               + moving.inertia_kg_m2 + _shift(moving.mass_kg, com_moving - com))
    return MassProps(mass, com, inertia)


def printed_half_unit(value: float) -> float:
    """Half a unit in the last digit of the shortest repr of ``value`` (the YAML text the
    exporter wrote, read back as a float). 0 for exact zero."""
    if value == 0.0:
        return 0.0
    exponent = Decimal(repr(float(value))).normalize().as_tuple().exponent
    return 0.5 * 10.0 ** int(exponent)


def _flatten(p: MassProps) -> NDArray[np.float64]:
    i = p.inertia_kg_m2
    return np.array([p.mass_kg, *p.com_m, i[0, 0], i[1, 1], i[2, 2], i[0, 1], i[0, 2], i[1, 2]])


def _unflatten(x: Sequence[float]) -> MassProps:
    m, cx, cy, cz, ixx, iyy, izz, ixy, ixz, iyz = (float(v) for v in x)
    inertia = np.array([[ixx, ixy, ixz], [ixy, iyy, iyz], [ixz, iyz, izz]])
    return MassProps(m, np.array([cx, cy, cz]), inertia)


def composition_rounding_bound(fixed: MassProps, moving: MassProps, travel_m: float,
                               reference: MassProps) -> MassProps:
    """First-order bound of ``|compose - reference|`` caused by the printed digits only.

    Every number of ``fixed``, ``moving`` and ``reference`` may be off by half a unit in its
    last printed digit (:func:`printed_half_unit`); the bound per output element y_j is
    ``h_ref,j + sum_k |dy_j / dx_k| h_k`` (central differences with step ``h_k``, k over the
    20 fixed + moving numbers). The travel is exact (rev. 22: the level values and
    ``auger_travel_m`` come from the same ``auger_levels.json`` number, checked by
    :func:`auger_travel_check`), so it gets no rounding term; with one, its 5e-6 m half unit
    would take up to 98 % of the inertia bound and hide a 0.01 kg m^2 error.

    Args:
        fixed: YAML ``superstructure.fixed_part``.
        moving: YAML ``superstructure.auger_moving_set_at_cad_pose``.
        travel_m: Level travel along body +z (YAML ``auger_travel_m``).
        reference: YAML ``superstructure.auger_levels.<level>``.

    Returns:
        The bound per element, packed as a :class:`MassProps` (all entries >= 0).
    """
    inputs = np.concatenate([_flatten(fixed), _flatten(moving)])
    halves = np.array([printed_half_unit(v) for v in inputs])

    def composed_elements(x: NDArray[np.float64]) -> NDArray[np.float64]:
        return _flatten(compose_auger_level(_unflatten(x[:10]), _unflatten(x[10:]), travel_m))

    bound = np.array([printed_half_unit(v) for v in _flatten(reference)])
    for k, half in enumerate(halves):
        if half == 0.0:
            continue
        up, down = inputs.copy(), inputs.copy()
        up[k] += half
        down[k] -= half
        bound += np.abs(composed_elements(up) - composed_elements(down)) / 2.0
    return _unflatten(bound)


def _residual_over_bound(residual: NDArray[np.float64],
                         bound: NDArray[np.float64]) -> NDArray[np.float64]:
    """``|residual| / bound`` per element; a zero bound gives 0 (exact) or inf (any residual)."""
    magnitude = np.abs(residual)
    ratio = np.full_like(magnitude, np.inf)
    positive = bound > 0.0
    ratio[positive] = magnitude[positive] / bound[positive]
    ratio[~positive & (magnitude == 0.0)] = 0.0
    return ratio


def _rounding_bound_check(level: str, composed: MassProps, reference: MassProps,
                          bound: MassProps, key: str) -> CheckResult:
    """Judged V0 (auger) row: element-wise ``|composed - reference| <= bound``."""
    got, ref, limit = _flatten(composed), _flatten(reference), _flatten(bound)
    residual = got - ref
    ratio = _residual_over_bound(residual, limit)
    worst = int(np.argmax(ratio))
    passed = bool(np.all(np.isfinite(got)) and np.all(np.abs(residual) <= limit))
    note = (f"max |residual| / bound = {ratio[worst]:.3g} ({MASS_PROPS_ELEMENTS[worst]}); "
            "residual " + ", ".join(f"{v:.3g}" for v in residual)
            + "; bound " + ", ".join(f"{v:.3g}" for v in limit)
            + " (order " + ", ".join(MASS_PROPS_ELEMENTS) + "; kg, m, kg m^2)")
    return CheckResult("V0(auger)", f"{level}: fixed + moving set = level values, each element "
                       "within its printed-digit rounding bound", got, ref, limit, "abs",
                       "kg, m, kg m^2", passed, ref_key=key, deviation=residual, note=note)


def auger_v0_checks(level: str, composed: MassProps, reference: MassProps,
                    bound: MassProps, *, key: str = "") -> list[CheckResult]:
    """V0 (auger) rows of one level (rev. 22, U1 = (a)).

    Args:
        level: Auger level name (``top`` / ``middle`` / ``bottom``).
        composed: :func:`compose_auger_level` of the YAML parts at the level travel.
        reference: YAML ``superstructure.auger_levels.<level>``.
        bound: :func:`composition_rounding_bound` of the same inputs.
        key: Reference key prefix; default ``YAML superstructure.auger_levels.<level>``.

    Returns:
        One judged row ``V0(auger)`` (element-wise rounding bound), then three ``info`` rows
        with the plan 1e-9 metrics (mass relative, CoM absolute [m], inertia relative to
        ``max |I|``), which 9 printed digits cannot guarantee.
    """
    key = key or f"YAML superstructure.auger_levels.{level}"
    i_max = float(np.abs(reference.inertia_kg_m2).max())
    return [
        _rounding_bound_check(level, composed, reference, bound, key),
        check_rel("info", f"{level}: V0(auger) plan 1e-9, mass relative", composed.mass_kg,
                  reference.mass_kg, V0_REL_TOL, "kg", ref_key=key + ".mass_kg",
                  note=V0_INFO_NOTE),
        check_abs("info", f"{level}: V0(auger) plan 1e-9, centre of mass", composed.com_m,
                  reference.com_m, V0_POS_ABS_TOL_M, "m", ref_key=key + ".com_m",
                  note=V0_INFO_NOTE),
        check_abs("info", f"{level}: V0(auger) plan 1e-9, inertia about the CoM relative to "
                  "max |I|", composed.inertia_kg_m2, reference.inertia_kg_m2,
                  V0_REL_TOL * i_max, "kg m^2", ref_key=key + ".inertia_kg_m2",
                  note=f"tol = 1e-9 x max |I| = {V0_REL_TOL * i_max:.3g} kg m^2; "
                  + V0_INFO_NOTE),
    ]


def auger_travel_check(level: str, travel_m: float, travel_mm_json: float, *,
                       key: str = "") -> CheckResult:
    """Row ``V0(auger) travel``: YAML ``auger_travel_m`` = ``auger_levels.json`` travel_mm x 1e-3.

    This is the premise of the travel-free rounding bound (:func:`composition_rounding_bound`).

    Args:
        level: Auger level name.
        travel_m: YAML ``superstructure.auger_levels.<level>.auger_travel_m`` [m].
        travel_mm_json: ``auger_levels.json`` ``levels.<level>.travel_mm`` [mm].
        key: Reference key; default names the JSON entry.
    """
    key = key or f"auger_levels.json levels.{level}.travel_mm x 1e-3"
    return check_abs("V0(auger) travel", f"{level}: YAML auger_travel_m = auger_levels.json "
                     "travel_mm x 1e-3", float(travel_m), float(travel_mm_json) * 1.0e-3,
                     AUGER_TRAVEL_ABS_TOL_M, "m", ref_key=key,
                     note="the level values are composed from this number (rev. 22)")


def auger_v0_residuals(composed: MassProps, reference: MassProps) -> dict[str, float]:
    """Plan-metric residuals (mass rel, com max abs m, inertia max abs / max |I|)."""
    return {
        "mass_rel": abs(composed.mass_kg / reference.mass_kg - 1.0),
        "com_max_abs_m": float(np.abs(composed.com_m - reference.com_m).max()),
        "inertia_max_abs_kg_m2": float(np.abs(composed.inertia_kg_m2
                                              - reference.inertia_kg_m2).max()),
        "inertia_rel_to_max": float(np.abs(composed.inertia_kg_m2 - reference.inertia_kg_m2).max()
                                    / np.abs(reference.inertia_kg_m2).max()),
    }


# --- V10 -----------------------------------------------------------------------------------------


def pdelta_contact_forces_N(pdelta_check: Mapping[str, Any], level: str) -> NDArray[np.float64]:
    """P-delta nonlinear pad contact forces of one level (FL, FR, RL, RR) [N].

    Args:
        pdelta_check: Parsed ``06_analysis/00_dynamics/s1_pdelta_check.json``.
        level: Auger level name.

    Raises:
        KeyError: The file has no ``<level>.nonlinear_contact_N`` (the judged V1 row needs it).
        ValueError: The entry is not four forces.
    """
    try:
        forces = np.asarray(pdelta_check[level][PDELTA_CONTACT_KEY], dtype=float)
    except KeyError as missing:
        raise KeyError(f"s1_pdelta_check.json has no {level}.{PDELTA_CONTACT_KEY}") from missing
    if forces.shape != (4,):
        raise ValueError(f"s1_pdelta_check.json {level}.{PDELTA_CONTACT_KEY}: expected 4 forces, "
                         f"got shape {forces.shape}")
    return forces


def v10_load_checks(level: str, *, contact_mean_N: ArrayLike, pdelta_contact_N: ArrayLike,
                    ref_contact_N: ArrayLike, total_weight_N: float, pdelta_key: str,
                    ref_key: str, weight_key: str) -> list[CheckResult]:
    """V1 rows of one level (rev. 22, U2 = B).

    Args:
        level: Auger level name.
        contact_mean_N: Still-window mean pad contact force per leg (FL, FR, RL, RR) [N].
        pdelta_contact_N: P-delta nonlinear solution (:func:`pdelta_contact_forces_N`).
        ref_contact_N: Linear reference ``levels / <level> / contact_force_N``.
        total_weight_N: W = ``statics / total_weight_incl_rods_N``.
        pdelta_key: Source of ``pdelta_contact_N`` (for the row).
        ref_key: Source of ``ref_contact_N``.
        weight_key: Source of ``total_weight_N``.

    Returns:
        ``V10`` Chrono - P-delta per leg (0.01 % W/4), ``info`` Chrono - linear reference per leg
        (1 % W/4, recorded), ``V10`` sum of the pad contact forces vs W (1e-4 rel).
    """
    contact = np.asarray(contact_mean_N, dtype=float)
    quarter_weight_N = float(total_weight_N) / 4.0
    pdelta_tol_N = V10_PDELTA_FRACTION_OF_QUARTER_WEIGHT * quarter_weight_N
    linear_tol_N = V10_LINEAR_FRACTION_OF_QUARTER_WEIGHT * quarter_weight_N
    return [
        check_abs("V10", f"{level}: V1 pad contact force per leg vs P-delta nonlinear solution",
                  contact, pdelta_contact_N, pdelta_tol_N, "N", ref_key=pdelta_key,
                  note=f"tol = 0.01 % W/4 = {pdelta_tol_N:.4g} N (rev. 22, U2 = B)"),
        check_abs("info", f"{level}: V1 pad contact force per leg vs linear reference, recorded",
                  contact, ref_contact_N, linear_tol_N, "N", ref_key=ref_key,
                  note=f"tol = 1 % W/4 = {linear_tol_N:.4g} N (S1 V1); the difference is the "
                  "P-delta share"),
        check_rel("V10", f"{level}: V1 sum of pad contact forces", float(contact.sum()),
                  float(total_weight_N), V1_SUM_REL_TOL, "N", ref_key=weight_key),
    ]


def v10_mode_checks(level: str, rows: Sequence[ModeRow], *, ref_key_f: str,
                    ref_key_zeta: str) -> list[CheckResult]:
    """Modes 1-2 of one level: judged natural frequency +-3 % (V10), zeta +-30 % (info)."""
    out: list[CheckResult] = []
    for r in rows:
        j = judged_value(r)
        tag = f"{level}: mode {r.mode} ({r.run} run, {j.source})"
        out.append(check_rel("V10", f"{tag} natural frequency", j.f_Hz, r.f_ref_Hz,
                             V7_FREQ_REL_TOL, "Hz", ref_key=ref_key_f,
                             note=f"f_n = |lambda| / 2 pi vs f_damped_Hz (|lambda| / 2 pi); "
                             f"{j.reason}"))
        out.append(check_rel("info", f"{tag} zeta (- r omega dt/2), recorded", j.zeta,
                             r.zeta_ref, V7_ZETA_REL_TOL, "-", ref_key=ref_key_zeta,
                             note=f"zeta_num {r.zeta_num:.3g} subtracted; not judged by V10"))
    return out


def v10_order_checks(f_by_level: Mapping[str, Sequence[float]],
                     levels: Sequence[str] = LEVELS) -> list[CheckResult]:
    """Each judged mode frequency rises strictly along ``levels`` (top < middle < bottom)."""
    out: list[CheckResult] = []
    n = min(len(f_by_level[lv]) for lv in levels)
    for i in range(n):
        f = [float(f_by_level[lv][i]) for lv in levels]
        steps = np.diff(f)
        ok = bool(np.all(np.isfinite(f)) and np.all(steps > 0.0))
        out.append(check_equal("V10", f"mode {i + 1} order {' < '.join(levels)}", ok, True,
                               note="f " + " / ".join(f"{v:.4f}" for v in f) + " Hz"))
    return out


def v10_health_checks(level: str, yield_steps: Sequence[Sequence[int]] | Sequence[int],
                      n_events: int) -> list[CheckResult]:
    """No bushing yield / event in the V10 runs (V7 premise)."""
    ys = np.asarray(yield_steps, dtype=float).ravel()
    return [check_max("V13", f"{level}: bushing yield steps (all runs)", ys, 0.0, "steps"),
            check_max("V13", f"{level}: bushing events (all runs)", float(n_events), 0.0, "-")]


def summarize_check_ids(checks: Sequence[Mapping]) -> dict[str, bool]:
    """``{id: all passed}`` of JSON check rows (``info`` rows excluded)."""
    out: dict[str, bool] = {}
    for c in checks:
        if c["id"] == "info":
            continue
        out[c["id"]] = out.get(c["id"], True) and bool(c["passed"])
    return out
