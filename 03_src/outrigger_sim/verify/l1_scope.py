"""M4: fast lift-off windows outside the L1 scope (rod-oil local mode).

``00_docs/01_dynamics/dynamics_model.md`` 5.15.2 (revision 32 supplement 1),
``00_docs/02_hydraulic/rod_side_pressure.md`` 17. A locked leg whose ground falls away fast
lifts off with a separation speed; in the real cylinder the rod then rings on the two locked
oil columns (about 100 Hz, tension -8 to -24 kN for RE1b-F), a transient L1 cannot produce
(no rod degree of freedom). For about three periods after such a lift-off the leg's cylinder
quantities are therefore not judged; a closed-form estimate is reported instead.

**Event** (5.15.2 (1)): a leg in LOCK or FLOOR enters LIFT at a sample where the separation
speed ``v_rel`` (patch descent speed minus the ball-centre descent speed along the floor
normal, m/s, > 0 = separating) is at least ``v_th = 1 kN / sqrt((k_h + k_r) m_rod)``.

**Window** (5.15.2 (2)): ``[t_lift, t_lift + 30 ms]`` of that leg, ended early at re-contact
(first later sample not in LIFT). Excluded for that leg: cylinder force (and its minimum /
tension), the virtual head and rod pressures, the two-sensor net force, ``stroke_true``, and
with them the 350 bar and cavitation checks of the window. The excluded samples are replaced
by the leg's last sample before the window (sample and hold), so that minimum, maximum and
threshold checks see nothing from the window and every other sample stays bit for bit.

**Report** (5.15.2 (3)): ``F_ten(zeta) = -v_rel sqrt((k_h + k_r) m_rod) D(zeta)``,
``D = exp(-zeta atan2(sqrt(1 - zeta^2), zeta) / sqrt(1 - zeta^2))``, zeta 0 / 0.1 / 0.3;
``p_r,max = p_r,LIFT + r |F_ten| / A_ann``, ``p_h,min = p_h,LIFT - (1 - r) |F_ten| / A_p`` with
``r = k_r / (k_h + k_r)``; pad acceleration ``|F_ten| / m_rod``. With M1 the window's cylinder
force must stay ``>= -m_rod g - 0.5 kN`` (model sanity check, not a physical judgement).

**Inputs**: ``settle_velocity.npz`` beside ``pads.npz`` in the case directory (settlement cases
only, every engine step, cad-expert 2026-10-22; loaded by ``verify/s6_control.load_case`` as
``case["settle_velocity"]``): ``t`` (s), ``mode`` (n, 4) int8 ``RodChamberMode`` (-1 = machine
not stepped), ``v_patch_n`` and ``v_ball_n`` (n, 4) m/s along the floor normal, **up +**. With
M4's down-positive convention v_rel = v_ball_n - v_patch_n. Optional ``p_head_Pa`` /
``p_rod_Pa`` (machine pressures) feed the report's pressure rows (None without them). A case
without the file is left untouched (no windows, judgements bit-identical); so is a case whose
file holds no event. ``t_lift`` is the first LIFT step.

Leg values from the YAML: ``k_h`` = ``contact.rigid_floor.L1.derivation.k_oil_N_m``, ``k_r`` =
``actuator.rod_side.k_rod_side_N_m``, ``m_rod`` = ``legs.<leg>.moving_part.mass_kg``, areas of
``sensors.hydraulic``. Units SI, LEG_ORDER.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.hydraulics.rod_chamber import RodChamberMode
from outrigger_sim.params import LEG_ORDER, Params
from outrigger_sim.sensors.hydraulic import (
    leg_annulus_areas_from_params,
    leg_head_areas_from_params,
)

WINDOW_S = 0.030
"""About three rod-oil periods (97.7 / 102.4 Hz front / rear), 5.15.2 (2)."""
TENSION_THRESHOLD_N = 1000.0
"""Closed-form zeta-0 tension that makes a lift-off an event (about m_rod g), 5.15.2 (1)."""
SANITY_MARGIN_N = 500.0
"""M1 sanity check: window cylinder force >= -m_rod g - 0.5 kN (rod_side_pressure.md 17.4)."""
ZETAS = (0.0, 0.1, 0.3)
"""Rod-mode damping ratios of the closed-form report."""
REASON = "rod-oil local mode (L1 has no rod DoF), rod_side_pressure.md 17 M4"
ESTIMATE_NOTE = (
    "L1 representation outside - closed-form estimate; conservative: rod lag neglected, about "
    "+17 % against hydraulics B (dynamics_model.md 5.15.1)"
)
SETTLE_VELOCITY_FILE = "settle_velocity.npz"
CASE_KEY = "settle_velocity"
"""Key of the loaded file in a case of ``verify/s6_control.load_case``."""
MODE_KEY = "mode"
BALL_SPEED_KEY = "v_ball_n"
PATCH_SPEED_KEY = "v_patch_n"
HEAD_PRESSURE_KEY = "p_head_Pa"
ROD_PRESSURE_KEY = "p_rod_Pa"
PAD_EXCLUDED_KEYS = ("F_cyl", "F_cyl_min_interval", "head_pressure", "stroke_true")
"""Per-leg pad-record arrays held over a window."""
RECORD_EXCLUDED_KEYS = ("F_cyl", "stroke_true", "meas.head_pressure", "meas.rod_pressure")
"""Per-leg Record arrays held over a window (cylinder force, truth stroke, virtual sensors)."""
_LOCKED_BEFORE_LIFT = (int(RodChamberMode.LOCK), int(RodChamberMode.FLOOR))
_K_HEAD_KEY = "contact.rigid_floor.L1.derivation.k_oil_N_m"
_K_ROD_KEY = "actuator.rod_side.k_rod_side_N_m"
ArrayLikeFloat = Sequence[float] | NDArray[np.float64]
ArrayLikeInt = Sequence[int] | NDArray[np.int64]


@dataclass(frozen=True)
class RodOilLeg:
    """Rod-oil local mode values of one leg (YAML)."""

    leg: str
    head_stiffness_N_m: float
    rod_stiffness_N_m: float
    rod_mass_kg: float
    head_area_m2: float
    annulus_area_m2: float

    @property
    def impedance_N_s_m(self) -> float:
        """``sqrt((k_h + k_r) m_rod)``."""
        return math.sqrt((self.head_stiffness_N_m + self.rod_stiffness_N_m) * self.rod_mass_kg)

    @property
    def separation_threshold_m_s(self) -> float:
        """``v_th = 1 kN / sqrt((k_h + k_r) m_rod)``."""
        return TENSION_THRESHOLD_N / self.impedance_N_s_m

    @property
    def rod_share(self) -> float:
        """``r = k_r / (k_h + k_r)``."""
        return self.rod_stiffness_N_m / (self.head_stiffness_N_m + self.rod_stiffness_N_m)

    @property
    def mode_frequency_Hz(self) -> float:
        both_N_m = self.head_stiffness_N_m + self.rod_stiffness_N_m
        return math.sqrt(both_N_m / self.rod_mass_kg) / (2.0 * math.pi)


@dataclass(frozen=True)
class ScopeWindow:
    """One excluded window of one leg (times as in the input time base)."""

    leg_index: int
    t_from_s: float
    t_to_s: float
    separation_speed_m_s: float
    ended_by_recontact: bool

    @property
    def leg(self) -> str:
        return LEG_ORDER[self.leg_index]

    def to_meta(self) -> dict[str, Any]:
        """The ``outside_L1_scope`` entry (5.15.2 (2))."""
        return {
            "leg": self.leg,
            "t_from": self.t_from_s,
            "t_to": self.t_to_s,
            "reason": REASON,
            "v_rel_m_s": self.separation_speed_m_s,
            "ended_by_recontact": self.ended_by_recontact,
        }


def _per_leg(value: Any, leg: str) -> float:
    return float(value[leg]) if isinstance(value, Mapping) else float(value)


def rod_oil_legs_from_params(params: Params) -> tuple[RodOilLeg, ...]:
    """Per-leg rod-oil values in LEG_ORDER (module docstring)."""
    k_head = params.get(_K_HEAD_KEY)
    k_rod = params.get(_K_ROD_KEY)
    head_areas = leg_head_areas_from_params(params)
    annulus_areas = leg_annulus_areas_from_params(params)
    return tuple(
        RodOilLeg(
            leg=leg,
            head_stiffness_N_m=_per_leg(k_head, leg),
            rod_stiffness_N_m=_per_leg(k_rod, leg),
            rod_mass_kg=float(leg_params.moving_part.mass_kg),
            head_area_m2=float(head_areas[i]),
            annulus_area_m2=float(annulus_areas[i]),
        )
        for i, (leg, leg_params) in enumerate(zip(LEG_ORDER, params.legs, strict=True))
    )


def _window_end(
    t_s: NDArray[np.float64], mode: NDArray[np.int64], start: int
) -> tuple[float, bool]:
    """End of the window from the LIFT sample ``start``: re-contact or ``t_lift + 30 ms``."""
    t_limit = float(t_s[start]) + WINDOW_S
    for k in range(start + 1, len(t_s)):
        if float(t_s[k]) > t_limit:
            break
        if int(mode[k]) != int(RodChamberMode.LIFT):
            return float(t_s[k]), True
    return t_limit, False


def detect_scope_windows(
    t_s: ArrayLikeFloat,
    mode: ArrayLikeInt,
    separation_speed_m_s: ArrayLikeFloat,
    legs: Sequence[RodOilLeg],
) -> list[ScopeWindow]:
    """Fast lift-off windows (5.15.2 (1), (2)) of samples ``t_s`` (n,), ``mode`` and
    ``separation_speed_m_s`` (n, legs), sorted by leg then time."""
    t = np.asarray(t_s, dtype=float)
    modes = np.asarray(mode, dtype=np.int64)
    speeds = np.asarray(separation_speed_m_s, dtype=float)
    windows: list[ScopeWindow] = []
    for i, leg in enumerate(legs):
        threshold = leg.separation_threshold_m_s
        for k in range(1, len(t)):
            enters_lift = (
                int(modes[k - 1, i]) in _LOCKED_BEFORE_LIFT
                and int(modes[k, i]) == int(RodChamberMode.LIFT)
            )
            if not (enters_lift and float(speeds[k, i]) >= threshold):
                continue
            t_to, by_recontact = _window_end(t, modes[:, i], k)
            windows.append(ScopeWindow(i, float(t[k]), t_to, float(speeds[k, i]), by_recontact))
    return windows


def exclusion_mask(
    t_s: ArrayLikeFloat, windows: Sequence[ScopeWindow], leg_count: int = len(LEG_ORDER)
) -> NDArray[np.bool_]:
    """(n, legs) True on the samples of each leg's windows (closed interval)."""
    t = np.asarray(t_s, dtype=float)
    mask = np.zeros((len(t), leg_count), dtype=bool)
    for window in windows:
        mask[:, window.leg_index] |= (t >= window.t_from_s) & (t <= window.t_to_s)
    return mask


def hold_excluded(values: NDArray[Any], mask: NDArray[np.bool_]) -> NDArray[Any]:
    """Copy of ``values`` (n, legs, ...) with each masked sample replaced by the leg's last
    unmasked sample before it (a window at the record start keeps its own samples)."""
    out = np.array(values, copy=True)
    for i in range(mask.shape[1]):
        last_valid: int | None = None
        for k in range(mask.shape[0]):
            if not mask[k, i]:
                last_valid = k
            elif last_valid is not None:
                out[k, i] = out[last_valid, i]
    return out


def tension_estimate_N(separation_speed_m_s: float, impedance_N_s_m: float, zeta: float) -> float:
    """First tension trough ``F_ten(zeta)`` of the rod-oil mode (5.15.2 (3)), N (< 0)."""
    damping = 1.0
    if zeta > 0.0:
        root = math.sqrt(1.0 - zeta * zeta)
        damping = math.exp(-zeta * math.atan2(root, zeta) / root)
    return -separation_speed_m_s * impedance_N_s_m * damping


def _sample_at(series: NDArray[np.float64] | None, t_s: NDArray[np.float64], at_s: float,
               leg: int) -> float | None:
    if series is None:
        return None
    k = int(np.searchsorted(t_s, at_s))
    return None if k >= len(t_s) else float(series[k, leg])


def closed_form_report(
    window: ScopeWindow,
    leg: RodOilLeg,
    rod_pressure_lift_Pa: float | None = None,
    head_pressure_lift_Pa: float | None = None,
) -> dict[str, Any]:
    """Report row of one event (5.15.2 (3)); pressures None when the LIFT values are unknown."""
    rows = []
    for zeta in ZETAS:
        tension_N = tension_estimate_N(window.separation_speed_m_s, leg.impedance_N_s_m, zeta)
        rod_rise_Pa = leg.rod_share * abs(tension_N) / leg.annulus_area_m2
        head_drop_Pa = (1.0 - leg.rod_share) * abs(tension_N) / leg.head_area_m2
        rows.append({
            "zeta": zeta,
            "F_ten_N": tension_N,
            "p_r_max_Pa": None if rod_pressure_lift_Pa is None
            else rod_pressure_lift_Pa + rod_rise_Pa,
            "p_h_min_Pa": None if head_pressure_lift_Pa is None
            else head_pressure_lift_Pa - head_drop_Pa,
            "pad_acceleration_m_s2": abs(tension_N) / leg.rod_mass_kg,
        })
    return {
        "leg": window.leg,
        "t_lift": window.t_from_s,
        "v_rel_m_s": window.separation_speed_m_s,
        "first_trough_t": window.t_from_s + 1.0 / (4.0 * leg.mode_frequency_Hz),
        "rod_oil_mode_Hz": leg.mode_frequency_Hz,
        "impedance_N_s_m": leg.impedance_N_s_m,
        "p_r_lift_Pa": rod_pressure_lift_Pa,
        "p_h_lift_Pa": head_pressure_lift_Pa,
        "estimates": rows,
        "note": ESTIMATE_NOTE,
    }


def sanity_check(
    t_s: ArrayLikeFloat,
    cylinder_force_N: NDArray[np.float64],
    windows: Sequence[ScopeWindow],
    legs: Sequence[RodOilLeg],
    gravity_m_s2: float,
) -> list[dict[str, Any]]:
    """M1 model check per window: min cylinder force >= -m_rod g - 0.5 kN (unheld values)."""
    t = np.asarray(t_s, dtype=float)
    rows = []
    for window in windows:
        inside = (t >= window.t_from_s) & (t <= window.t_to_s)
        limit_N = -legs[window.leg_index].rod_mass_kg * gravity_m_s2 - SANITY_MARGIN_N
        minimum = (
            float(np.min(cylinder_force_N[inside, window.leg_index])) if inside.any() else None
        )
        rows.append({
            "leg": window.leg,
            "t_from": window.t_from_s,
            "min_F_cyl_N": minimum,
            "limit_N": limit_N,
            "passed": None if minimum is None else minimum >= limit_N,
        })
    return rows


def _held(arrays: Mapping[str, NDArray[Any]], keys: Sequence[str], mask: NDArray[np.bool_]
          ) -> dict[str, NDArray[Any]]:
    out = dict(arrays)
    for key in keys:
        if key in out and np.ndim(out[key]) >= 2 and np.shape(out[key])[1] == mask.shape[1]:
            out[key] = hold_excluded(out[key], mask)
    return out


def separation_speed_m_s(velocity: Mapping[str, NDArray[Any]]) -> NDArray[np.float64]:
    """``v_rel = v_ball_n - v_patch_n`` (n, 4), down-positive, of a ``settle_velocity`` file."""
    ball = np.asarray(velocity[BALL_SPEED_KEY], dtype=float)
    patch = np.asarray(velocity[PATCH_SPEED_KEY], dtype=float)
    return ball - patch


def _event_reports(
    windows: Sequence[ScopeWindow], legs: Sequence[RodOilLeg], velocity: Mapping[str, Any]
) -> list[dict[str, Any]]:
    t = np.asarray(velocity["t"], dtype=float)
    head = velocity.get(HEAD_PRESSURE_KEY)
    rod = velocity.get(ROD_PRESSURE_KEY)
    reports = []
    for window in windows:
        leg = window.leg_index
        reports.append(closed_form_report(
            window, legs[leg],
            _sample_at(None if rod is None else np.asarray(rod), t, window.t_from_s, leg),
            _sample_at(None if head is None else np.asarray(head), t, window.t_from_s, leg),
        ))
    return reports


def _sanity_rows(case, windows, legs, params) -> list[dict[str, Any]]:
    pads = case.get("pads")
    if pads is None:
        return []
    force = pads.get("F_cyl_min_interval", pads["F_cyl"])  # every physics step when present
    return sanity_check(pads["t"], np.asarray(force, dtype=float), windows, legs,
                        float(params.meta.gravity_m_s2))


def _held_case(case: Mapping[str, Any], windows: Sequence[ScopeWindow]) -> dict[str, Any]:
    held = dict(case)
    pads = case.get("pads")
    if pads is not None:
        held["pads"] = _held(pads, PAD_EXCLUDED_KEYS, exclusion_mask(pads["t"], windows))
    rec = case["rec"]
    held["rec"] = _held(rec, RECORD_EXCLUDED_KEYS, exclusion_mask(rec["t"], windows))
    return held


def _relative_times(rows: Sequence[dict[str, Any]], t0_s: float) -> None:
    for row in rows:
        for key in ("t_from", "t_to", "t_lift", "first_trough_t"):
            if row.get(key) is not None:
                row[key] -= t0_s


def apply_to_case(
    case: Mapping[str, Any], params: Params
) -> tuple[Mapping[str, Any], dict[str, Any] | None]:
    """Detect the windows of a loaded case (``verify/s6_control.load_case``) and hold the
    excluded quantities.

    Returns:
        ``(case, None)`` unchanged without a ``settle_velocity`` file or without an event;
        else a shallow copy with held ``pads`` / ``rec`` arrays and the scope result
        (``outside_L1_scope`` entries, report and M1 sanity rows; times relative to the
        case start like the other metrics).
    """
    velocity = case.get(CASE_KEY)
    if velocity is None:
        return case, None
    legs = rod_oil_legs_from_params(params)
    windows = detect_scope_windows(
        velocity["t"], velocity[MODE_KEY], separation_speed_m_s(velocity), legs
    )
    if not windows:
        return case, None
    entries = [window.to_meta() for window in windows]
    reports = _event_reports(windows, legs, velocity)
    sanity = _sanity_rows(case, windows, legs, params)
    t0_s = float(case["result"]["settings"]["start_t_s"])
    _relative_times([*entries, *reports, *sanity], t0_s)
    return _held_case(case, windows), {
        "outside_L1_scope": entries, "report": reports, "sanity_M1": sanity,
    }


__all__ = [
    "REASON",
    "WINDOW_S",
    "RodOilLeg",
    "ScopeWindow",
    "apply_to_case",
    "closed_form_report",
    "detect_scope_windows",
    "exclusion_mask",
    "hold_excluded",
    "rod_oil_legs_from_params",
    "sanity_check",
    "separation_speed_m_s",
    "tension_estimate_N",
]
