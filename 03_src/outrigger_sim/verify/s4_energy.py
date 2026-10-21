"""S4 V8(b) energy-budget checks (engine independent).

``00_docs/03_chrono/chrono_build_plan.md`` S4 (V8(b)); ``dynamics_model.md`` 5 V8 (b) (term
definitions) and rev. 19, 5.8 (dyn final ruling 2026-10-21: judged definitions below).
Automatic pass / fail is a pre-check; the physical judgement is the dynamics-expert's.

* residual ``R(t) = (E_mech(t) - E_mech(t0)) + D_visc(t) + D_slip(t) - W_m(t)``, ``E_mech`` =
  kinetic + gravity + pad contact springs + bushing springs, ``D_*`` and ``W_m`` accumulated
  from ``t0`` (the instant after the initial velocity is set); ``R > 0`` = energy created;
* reference energy ``E_ref = max(E_kin(t0), D_visc,end + D_slip,end)`` (motor work excluded);
* every case: (1) ``max_t R <= 1e-3 E_ref`` (no energy creation), (4) ``R_end <= 0`` and
  ``|R_end| <= 0.10 (D_visc,end + D_slip,end)``, (5) ``D_slip / sum mu N |delta a|`` in
  1.00-1.05;
* a case run at ``dt`` and ``2 dt``: (2) ``R_end(2 dt) / R_end(dt)`` in [1.6, 2.4] (first
  order), (3) ``|2 R_end(dt) - R_end(2 dt)| <= 0.01 E_ref`` (Richardson value at dt -> 0);
* recorded only: the former ``max |R| / E_ref`` (``E_ref`` = ``E_kin0 + max |W_m|``), the
  diagnostic shares (anchor lag, bushing implicit, kinetic implicit, contact explicit,
  remainder) with their dt ratios and Richardson values, ``R(0.25 s) / R_end``, bushing
  event counts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from outrigger_sim.verify.checks import CheckResult, check_max

V8B_CREATION_REL_MAX = 1.0e-3
"""(1) max_t R <= 1e-3 E_ref (dyn rev. 19)."""
V8B_END_LOSS_FRACTION_MAX = 0.10
"""(4) |R_end| <= 0.10 (D_visc + D_slip) with R_end <= 0."""
V8B_SLIP_RATIO_BAND = (1.00, 1.05)
"""(5) D_slip / sum mu N |delta a| (plan S4 V8(b))."""
V8B_DT_RATIO_BAND = (1.6, 2.4)
"""(2) R_end(2 dt) / R_end(dt)."""
V8B_RICHARDSON_REL_MAX = 0.01
"""(3) |2 R_end(dt) - R_end(2 dt)| <= 0.01 E_ref."""
V8B_EARLY_S = 0.25
"""R(0.25 s) / R_end recorded (share of the residual made while sliding)."""
V8B_OLD_RESIDUAL_REL_MAX = 0.01
"""Former pre-check max |R| / (E_kin0 + max |W_m|) <= 1 %: recorded only since rev. 19."""

BUDGET_TERMS = (
    "kinetic",
    "gravity",
    "contact_spring",
    "bushing_spring",
    "dissipated_viscous",
    "dissipated_slip",
    "motor_work",
)
DIAGNOSTIC_TERMS = ("bushing_lag", "bushing_implicit", "kinetic_implicit", "contact_explicit")
"""Read-only discrete shares of ``R`` (``chrono/energy.EnergyBudgetTerms``)."""


def _col(columns: Mapping[str, ArrayLike], name: str) -> np.ndarray:
    return np.asarray(columns[name], dtype=float)


def residual_series(columns: Mapping[str, ArrayLike]) -> np.ndarray:
    """``R(t)`` [J] from budget columns (``signals.ENERGY_TERMS`` names; row 0 = ``t0``)."""
    c = {k: _col(columns, k) for k in BUDGET_TERMS}
    mech = c["kinetic"] + c["gravity"] + c["contact_spring"] + c["bushing_spring"]
    return (
        (mech - mech[0])
        + (c["dissipated_viscous"] - c["dissipated_viscous"][0])
        + (c["dissipated_slip"] - c["dissipated_slip"][0])
        - (c["motor_work"] - c["motor_work"][0])
    )


def dissipation_end_J(columns: Mapping[str, ArrayLike]) -> float:
    """``D_visc,end + D_slip,end`` (from ``t0``) [J]."""
    dv = _col(columns, "dissipated_viscous")
    ds = _col(columns, "dissipated_slip")
    return float(dv[-1] - dv[0] + ds[-1] - ds[0])


def reference_energy_J(columns: Mapping[str, ArrayLike]) -> float:
    """``E_ref = max(E_kin(t0), D_visc,end + D_slip,end)`` [J] (dyn rev. 19)."""
    return float(max(_col(columns, "kinetic")[0], dissipation_end_J(columns)))


def reference_energy_old_J(columns: Mapping[str, ArrayLike]) -> float:
    """Former ``E_kin(t0) + max |W_m - W_m(t0)|`` [J] (recorded only)."""
    w = _col(columns, "motor_work")
    return float(_col(columns, "kinetic")[0] + np.max(np.abs(w - w[0])))


def budget_summary(t_s: ArrayLike, columns: Mapping[str, ArrayLike]) -> dict[str, Any]:
    """Term values, residual statistics and diagnostic shares of one run (J)."""
    t = np.asarray(t_s, dtype=float)
    r = residual_series(columns)
    e_ref = reference_energy_J(columns)
    e_old = reference_energy_old_J(columns)
    i_abs = int(np.argmax(np.abs(r)))
    i_early = int(np.searchsorted(t - t[0], V8B_EARLY_S - 1e-9))
    out: dict[str, Any] = {
        "t0_s": float(t[0]),
        "t_end_s": float(t[-1]),
        "E_ref_J": e_ref,
        "E_kin0_J": float(_col(columns, "kinetic")[0]),
        "dissipation_end_J": dissipation_end_J(columns),
        "terms_initial_J": {k: float(_col(columns, k)[0]) for k in BUDGET_TERMS},
        "terms_final_J": {k: float(_col(columns, k)[-1]) for k in BUDGET_TERMS},
        "change_J": {k: float(_col(columns, k)[-1] - _col(columns, k)[0]) for k in BUDGET_TERMS},
        "residual_end_J": float(r[-1]),
        "residual_max_signed_J": float(np.max(r)),
        "residual_max_t_s": float(t[int(np.argmax(r))]),
        "residual_max_abs_J": float(abs(r[i_abs])),
        "residual_early_J": float(r[min(i_early, len(r) - 1)]),
        "residual_early_over_end": float(r[min(i_early, len(r) - 1)] / r[-1])
        if r[-1] != 0.0
        else float("nan"),
        "residual_creation_rel": float(np.max(r) / e_ref),
        "residual_end_over_dissipation": float(r[-1] / dissipation_end_J(columns))
        if dissipation_end_J(columns) > 0.0
        else float("nan"),
        "old_E_ref_J": e_old,
        "old_residual_max_rel": float(abs(r[i_abs]) / e_old),
    }
    present = [k for k in DIAGNOSTIC_TERMS if k in columns]
    shares = {k: float(_col(columns, k)[-1] - _col(columns, k)[0]) for k in present}
    out["diagnostics_end_J"] = shares
    out["remainder_end_J"] = float(r[-1] - sum(shares.values()))
    out["diagnostics_complete"] = len(present) == len(DIAGNOSTIC_TERMS)
    return out


def slip_ratio(slip_dissipation_J: float, coulomb_work_J: float) -> float:
    """``D_slip / sum mu N |delta a|`` (NaN when there was no yield)."""
    if not coulomb_work_J > 0.0:
        return float("nan")
    return float(slip_dissipation_J / coulomb_work_J)


def v8b_checks(
    case: str,
    *,
    residual_max_signed_J: float,
    residual_end_J: float,
    dissipation_end_J: float,
    e_ref_J: float,
    slip_dissipation_J: float,
    coulomb_work_J: float,
    yield_steps: Sequence[int],
    crawler_contact_max_N: float,
) -> list[CheckResult]:
    """Checks (1), (4), (5) of one run plus two scenario-validity checks (module docstring)."""
    ratio = slip_ratio(slip_dissipation_J, coulomb_work_J)
    lo, hi = V8B_SLIP_RATIO_BAND
    creation = residual_max_signed_J / e_ref_J
    loss = abs(residual_end_J) / dissipation_end_J if dissipation_end_J > 0.0 else float("inf")
    return [
        CheckResult(
            "V8(b)-1",
            f"{case}: no energy creation, max_t R / E_ref",
            creation,
            None,
            V8B_CREATION_REL_MAX,
            "max",
            "-",
            bool(np.isfinite(creation) and creation <= V8B_CREATION_REL_MAX),
            note="E_ref = max(E_kin0, D_visc + D_slip) (dyn rev. 19)",
        ),
        CheckResult(
            "V8(b)-4",
            f"{case}: end residual is a loss, R_end <= 0 and |R_end| / (D_visc + D_slip)",
            loss,
            None,
            V8B_END_LOSS_FRACTION_MAX,
            "max",
            "-",
            bool(residual_end_J <= 0.0 and loss <= V8B_END_LOSS_FRACTION_MAX),
            note=f"R_end = {residual_end_J:.3f} J",
        ),
        CheckResult(
            "V8(b)-5",
            f"{case}: D_slip / sum mu N |delta a|",
            ratio,
            [lo, hi],
            [lo, hi],
            "band",
            "-",
            bool(np.isfinite(ratio) and lo <= ratio <= hi),
            note="all legs, every yielding return mapping of the window",
        ),
        CheckResult(
            "V8(b)",
            f"{case}: bushing yield occurred (scenario validity)",
            int(np.sum(yield_steps)),
            "> 0",
            0,
            "min",
            "steps",
            bool(np.sum(yield_steps) > 0),
        ),
        check_max(
            "V8(b)",
            f"{case}: no crawler contact (budget covers the pads only)",
            crawler_contact_max_N,
            0.0,
            "N",
        ),
    ]


def v8b_pair_checks(
    label: str, *, dt_s: float, residual_end_dt_J: float, residual_end_2dt_J: float,
    e_ref_J: float,
) -> list[CheckResult]:
    """Checks (2) and (3) of one case run at ``dt`` and ``2 dt``."""
    ratio = (
        residual_end_2dt_J / residual_end_dt_J if residual_end_dt_J != 0.0 else float("nan")
    )
    lo, hi = V8B_DT_RATIO_BAND
    richardson = 2.0 * residual_end_dt_J - residual_end_2dt_J
    return [
        CheckResult(
            "V8(b)-2",
            f"{label}: R_end(2 dt) / R_end(dt), dt {dt_s:.0e} s",
            ratio,
            [lo, hi],
            [lo, hi],
            "band",
            "-",
            bool(np.isfinite(ratio) and lo <= ratio <= hi),
        ),
        CheckResult(
            "V8(b)-3",
            f"{label}: Richardson |2 R_end(dt) - R_end(2 dt)| / E_ref, dt {dt_s:.0e} s",
            abs(richardson) / e_ref_J,
            None,
            V8B_RICHARDSON_REL_MAX,
            "max",
            "-",
            bool(abs(richardson) <= V8B_RICHARDSON_REL_MAX * e_ref_J),
            note=f"2 R(dt) - R(2 dt) = {richardson:.3f} J",
        ),
    ]


def dt_ratio_record(values_by_dt: Mapping[float, float]) -> dict[str, Any]:
    """Ratios ``X(2 dt) / X(dt)`` and Richardson values ``2 X(dt) - X(2 dt)`` of a quantity
    known at several dts (recorded)."""
    dts = sorted(values_by_dt)
    pairs = []
    for small in dts:
        large = next((d for d in dts if np.isclose(d, 2.0 * small, rtol=1e-9)), None)
        if large is None:
            continue
        a, b = values_by_dt[small], values_by_dt[large]
        pairs.append({
            "dt_s": small,
            "two_dt_s": large,
            "value_dt": float(a),
            "value_2dt": float(b),
            "ratio_2dt_over_dt": float(b / a) if a != 0.0 else float("nan"),
            "richardson_dt0": float(2.0 * a - b),
        })
    return {"dt_s": dts, "values": [float(values_by_dt[d]) for d in dts], "pairs": pairs}
