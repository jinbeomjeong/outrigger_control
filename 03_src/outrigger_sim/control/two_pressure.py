"""Two-pressure load reading of C2 R6-P: net force, sensor diagnosis, fallback, rod-side watch.

``00_docs/04_control/s6_control_spec.md`` 51.1 (P-1 .. P-8), 53.3 (diagnosis thresholds and the
fallback of U45), 53.4 (P-9 .. P-13) and 61.3 (P-15, P-16); user decisions U43 .. U52. Engine
independent: it sees the delivered head and rod-side pressures, the controller's own leg
commands and its phase.

* Load estimate (P-2, U43): ``F = p_h A_p - p_r A_ann`` per leg (``net``); ``head_only`` and a
  measurement without a rod-side pressure give ``p_h A_p``, the R5 reading bit for bit.
* Diagnosis (P-4, 53.3): D1 range / step / stuck / NaN on both sensors, D2 rod side while
  extending, D3 while retracting (off by default), D4 physical lower bound when locked (held
  2 samples / 0.1 s, spec 110.2), D5 sum of the load changes in READY (warning only, held
  ``sum_hold_s``), D6 probe
  consistency (off by default). The geometry / pressure conflicts D7 (K-3, K-6) are raised by
  the controller's GE2 step.
* Load baseline (spec 110.1): D5, the E-5 drift and ``Delta F1`` compare against a baseline of
  their own, stored by the controller in READY / DONE after the commands have been zero for
  ``load_reference_settle_s`` (never at the TOUCH end), and are judged only while the commands
  stay zero that long. The baseline is the mean of the command-free readings of the stay over
  ``load_reference_mean_s`` (spec 120), not one sample on the heave ringing.
* Fallback (P-5, U45 = 53.3): a rod-side fault switches that leg alone, latched, to the head
  reading with a model upper bound of the rod-side pressure ``p_r_hat`` removed for the lower
  bound judgements (``lower``); BELOW uses the head reading plus the -0.9 bar floor
  (``upper``); the twist loop keeps the head reading (``nominal``). A head-side fault is a
  FAULT of the run.
* Rod-side watch (P-13, U46): locked ``p_r`` above 350 / 300 bar, predicted lift-off pressure
  ``p_r + r (F + m_rod g) / A_ann`` above 350 bar, a slow rise without load change (info).
* Shadows (no command depends on them, ``shadow_`` events): the load drop ``Delta F1`` against
  the load baseline (P-6, U47) and the retraction lift-off confirmation of the one-sided band
  (P-11, U50).
* Lock valve (P-S8-11, U-S8-23, spec rev. 46 216.10): with the counterbalance option the CB
  regulates the moving rod-side pressure (hydraulics ``s8_seal_friction_counterbalance.md``
  4.3), so the D2 upper bound and the fallback estimate follow the CB law in terms of the
  measured head pressure (:class:`CounterbalanceRodModel`). The pilot-check path is unchanged
  bit for bit. D2 / D3 judge a leg only while its measured stroke moves in the commanded
  direction (216.3 design note: a stuck valve); on by default for both lock valves since
  U-S8-28 (P-S8-12 ②, spec rev. 47 217.6 (2)).
* D1' explained steps (U-S8-26, P-S8-12 ①, spec rev. 47 217.5): a one-period change above
  ``max_step_Pa`` that the hydraulics explain (lock law, pilot check opening, load
  redistribution) is ``INFO_PRESSURE_STEP:<leg>:<head|rod>:<reason>``, not a fault; the
  10 Hz samples gather the physical steps of five 20 ms periods (ML pilot 104-168 bar).
  ``step_rule = "jump"`` keeps the old rule (every such change is a fault).
* D1'' (U-S8-31, P-S8-14, spec rev. 48 218.4, the default ``step_rule = "explained_imu"``):
  once the crawler is off the ground (LEVEL onward) a head step is explained by the IMU
  residual ``r = sum F - M_eff f_z`` instead of the force sum (a vertical bounce moves the sum,
  not ``r``); ``f_z`` is the last IMU sample of the period (10 ms partial mean, body z) minus
  the lever term ``(alpha x r)_z`` from the last two gyro partial means (P-S8-14 ⑤, on by
  default; without gyro samples uncorrected with ``WARN_D1_IMU_GYRO_MISSING`` once). ``M_eff``
  is the median ``sum F / f_z`` of the last READY stay (U-S8-36; ``nominal`` and ``slope``
  are options only, no seal ambiguity band). Before the crawler is off, without ``M_eff`` or
  without the IMU input (``WARN_D1_IMU_INPUT_MISSING``, once) the D1' sum rule applies. A
  rod-side fall gains the reason ``lock_load_regain`` (a locked leg taking load back: head
  up, stroke still, ``-dp_r / dp_h <= 1.4 R_ub(s)``). ``step_rule = "explained"`` is D1' bit
  for bit. Every head fault names its reason in ``INFO_HEAD_PRESSURE_FAULT_REASON``.
* D1' rod drain hold (P-S8-21, spec rev. 54 260.5): a rod-side fall under a positive command
  that ends still above the D2 extend range (a lifted-off locked leg's 125-174 bar draining
  with ``tau_d`` about 50-55 ms, sampled at 21-28 bar) is held one period, the reading still
  used; the next reading in ``[p_lo, p_hi + 0.5 (p_k - p_hi)]`` (rev. 55 268.3, R-2; ``p_hi``
  the D2 extend upper bound, with the CB its law bound) makes it
  ``INFO_PRESSURE_STEP:<leg>:rod:check_draining``, any other the D1 fallback one period late.
* Locked fallback estimate (P-S8-13, hydraulics H-S8-2, ``s8_seal_friction_counterbalance.md``
  10.4): on a command-free stretch ``p_r_hat`` is an upper bound over every lock-instant
  candidate of the valve-lag window, with the ratio bound ``R_ub(s)`` of the oil column
  lengths at the largest measured stroke of the window, and at least the last valid rod-side
  reading carried by the same bound (:meth:`TwoPressureMonitor._update_column_bound`).
  ``locked_ratio_rule = "fixed"`` keeps the 1.296 / 1.232 estimate bit for bit (regression).
* CB moving estimate (P-S8-15, hydraulics ``s8_seal_friction_counterbalance.md`` 11.2): with
  the counterbalance the moving ``p_r_hat`` is an upper bound of the CB law behind the plant's
  rod-side lag ``tau_cb`` (R4D), started from the last period's ``p_r_hat``, with both laws for
  ``N_rev`` periods after a reversal or a start and margins 23.4 / 1.2 bar; the lock start
  values ``M_j`` of the moving samples are that bound. ``counterbalance_moving_rule = "law"``
  (:meth:`TwoPressureSettings.with_cb_law_estimate`) is the 9.6 estimate; the pilot check
  is unchanged.
* R-5 fallback slope inputs (P-S8-22, spec rev. 61 302 / 304 ②, ④): with a
  :class:`FallbackRatioChoice` passed to :meth:`TwoPressureMonitor.read` (the controller does
  so for ``fast_relevel.fallback_slope = "nominal_gap"``), a fallback leg whose last ``n + 1``
  samples lie in one column-bound lock stretch gets :class:`FallbackSlopeInputs` (head drop,
  depth below the anchor, ``R_lvl``, ``R_hi``, ``R_rate``); ``plant_meta`` (L1 runs) also
  raises the level ratio to ``max(R_ub, kappa R_plant)`` (302.6), and ``online`` keeps the
  last two-sensor locked ratio of every leg. Without a choice nothing changes, bit for bit.

Every threshold here depends on the cylinder dimensions; the defaults are the values of spec 53
for the YAML cylinder and are settings only, to be replaced after the REXOME35 recalculation
(spec 61.2, 61.3). Units SI (Pa, N, m, s); per-leg arrays follow ``LEG_ORDER``.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import asdict, dataclass, field, replace
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.params import LEG_ORDER
from outrigger_sim.sensors.pressure_error import (
    SIGNAL_CURRENT_RANGE_MA,
    pressure_to_current_mA,
)
from outrigger_sim.signals import LEG_COUNT

BAR_PA = 1e5

# R8 (10 Hz) diagnosis constants, spec rev. 29 126 #3 (ASSUMPTION where the spec says so)
R8_LOAD_REFERENCE_SETTLE_S = 0.5
R8_LOAD_REFERENCE_MEAN_S = 1.5
R8_D4_MIN_SAMPLES = 2
R8_D4_HOLD_S = 0.2
R8_SUM_HOLD_S = 0.5
R8_DRIFT_HOLD_S = 30.0

CB_ROD_MARGIN_PA = 15.0 * BAR_PA
"""D2 margin on the CB law (hydraulics H-S8-1, ``s8_seal_friction_counterbalance.md`` 9.5):
normal-grade deterministic worst ``e_r - psi e_h`` 14.3 bar; +3 bar gave up to 20 % false
fallbacks per leg path, +15 bar none (ASSUMPTION, control to accept the duller detection)."""
CB_EXTEND_ESTIMATE_MARGIN_PA = 23.4 * BAR_PA
"""Fallback ``p_r_hat`` while extending (P-S8-15 ④, hydraulics 11.2): sensor share
``psi e_h,max`` 11.4 bar (9.6) + 12 bar for the rod-side lag between samples (record max
11.4 bar)."""
CB_RETRACT_ESTIMATE_MARGIN_PA = 1.2 * BAR_PA
"""Fallback ``p_r_hat`` while retracting (P-S8-15 ④): ``e_h,max / psi`` 0.7 bar + 0.5 bar."""
CB_LAW_EXTEND_ESTIMATE_MARGIN_PA = 11.4 * BAR_PA
CB_LAW_RETRACT_ESTIMATE_MARGIN_PA = 0.7 * BAR_PA
"""Margins of the 9.6 estimate before P-S8-15 (regression, :meth:`with_cb_law_estimate`)."""
CB_LAG_TAU_WITHOUT_YAML_S = 0.05
"""CB rod-side tracking lag upper bound ``tau_cb`` for monitors built without the YAML; the
controller passes ``actuator.rod_side.release_tau_s`` (P-S8-15 ①)."""
CB_DIRECTION_SETTLED_FRACTION = 0.05
"""P-S8-15 ③: the spool direction is uncertain until the valve lag has decayed to 5 %
(``N_rev = ceil(tau_v ln(1 / 0.05) / T)``, 3 periods at 0.1 s)."""
STROKE_CHECK_SPEED_FRACTION = 0.1
"""P-S8-11 ③ (216.3): measured stroke rate, in the commanded direction, that confirms a move."""
EXPLAINED_STEP_SUM_RATIO = 0.5
"""D1' head step (217.5, 217.12 ASSUMPTION): explained when the four-leg net-force sum changes
by less than this fraction of the step's own force ``|dp_h| A_p`` (observed 0.007 / 0.079 for
load redistribution, about 1 for a head sensor jump)."""
ROD_DRAIN_HOLD_RATIO = 0.5
"""D1' ``check_draining`` (P-S8-21, spec rev. 55 268.3, R-1 / R-2): a rod-side fall held one
period is explained when the next reading is at most ``p_hi + rho (p_k - p_hi)``. Hydraulics
H-S8-5: the plant drains with ``tau_d`` 0.050 s to 5.0 bar g, the reading ratio after a step is
at most 0.34 (no failure over 9,396 steps)."""
IMU_RESIDUAL_STEP_RATIO = 0.5
"""D1'' head step (218.4): explained when the IMU residual changes by less than this fraction
of the step's own force ``|dp_h| A_p`` (ML pilot rerun: real steps 0.00-0.22, a sensor jump
about 1)."""
IMU_MASS_MIN_SAMPLES = 3
"""READY samples a stay needs before its ``M_eff`` is used (the rev. 48 analysis minimum)."""
IMU_MASS_WINDOW_S = 60.0
"""ASSUMPTION: ``M_eff`` is the median over at most the newest 60 s of the READY stay (bounds
the buffer of a long stay; the median does not need more)."""
REGAIN_STROKE_CHANGE_MAX_M = 1e-3
"""``lock_load_regain`` (218.16 ASSUMPTION): one-period stroke reading change, about 3 x the
0.35 mm reading error."""
REGAIN_RATIO_MARGIN = 1.4
"""``lock_load_regain``: ``-dp_r / dp_h <= 1.4 R_ub(s)`` (H-S8-2 10.3 (a): the point ratio
exceeds the static one by up to 38 %)."""
BODY_MASS_WITHOUT_YAML_KG = 38400.8366
"""Superstructure mass (YAML ``superstructure.auger_levels.top.mass_kg``) for monitors built
without the YAML; the controller passes the run's value (dynamics rev. 41 R41-1: the Newton
fit of ``sum F_cyl = M f_z`` gives this mass, 38,399.9-38,402.0 kg)."""
IMU_LEVER_ARM_WITHOUT_YAML_M = (0.31 - 0.460190503, 0.88 + 0.00136232581, 0.040 - 2.18347069)
"""IMU mount C1 minus the top-level centre of mass (body axes) for monitors built without the
YAML; the controller passes the run's value."""
IMU_MASS_SLOPE_MIN_SAMPLES = 50
IMU_MASS_SLOPE_MIN_RMS_M_S2 = 0.02
"""ASSUMPTION: the slope calibration of ``M_eff`` needs this many lifted moving periods and
this RMS of the one-period ``f_z`` change before it is used."""
IMU_GYRO_SAMPLE_PERIOD_S = 0.01
"""IMU partial-mean interval of the gyro samples (100 Hz IMU path, spec 139 P-3): the angular
acceleration of the lever term is their difference over this time."""
IMU_RULE_META_KEYS = (
    "imu_residual_step_ratio",
    "imu_mass_min_samples",
    "imu_mass_calibration",
    "imu_mass_nominal_kg",
    "imu_mass_slope_min_samples",
    "imu_mass_slope_min_rms_m_s2",
    "imu_lever_correction",
    "imu_lever_arm_m",
    "imu_gyro_sample_period_s",
    "imu_seal_band_factor",
    "regain_stroke_change_max_m",
    "regain_ratio_margin",
)
LOCK_VALVE_META_KEYS = (
    "lock_valve",
    "counterbalance",
    "counterbalance_rod_margin_Pa",
    "counterbalance_extend_estimate_margin_Pa",
    "counterbalance_retract_estimate_margin_Pa",
    "counterbalance_moving_rule",
    "counterbalance_lag_tau_s",
)
STROKE_CHECK_META_KEYS = ("moving_stroke_check", "moving_stroke_speed_fraction")

# P-S8-13 (hydraulics H-S8-2, s8_seal_friction_counterbalance.md 10.4 / 10.8; ASSUMPTION)
LOCKED_RATIO_KAPPA = 1.10
"""Two-chamber ``beta`` ratio margin (10.2 table 2: up to 1.101 for rod side <= 350 bar)."""
LOCKED_RATIO_HEAD_DEAD_MAX_M = 0.08
LOCKED_RATIO_ROD_DEAD_MIN_M = 0.02
"""``L_0h`` / ``L_0r`` ends of the sensitivity range (user decision 2026-10-22, Q-M12 open)."""
LOCKED_RATIO_STROKE_MARGIN_M = 0.005
"""Stroke reading error 0.35 mm plus the ``s_ref`` against reading difference (10.2)."""
LOCKED_RATIO_STROKE_END_GAP_M = 1e-3
"""``s' <= s_max - 1 mm`` keeps ``R_ub`` finite (10.4 ①)."""
LOCK_WINDOW_VALVE_TAU_S = 0.1
"""R8 valve model lag ``tau_v`` (10.4 ②; the real valve is U-R8-9)."""
LOCK_WINDOW_EPS_M_S = 1e-6
"""Plant lock threshold ``|u| <= eps`` (L2b rod side ``lock_eps_m_s``)."""
LOCKED_START_EXTEND_PA = 13.0 * BAR_PA
"""Pilot-check start after an extension: D2 extend upper bound 12 bar + 1 bar (10.4 ③)."""
LOCKED_START_LOOKBACK_S = 0.3
"""Moving samples this long before the stretch also give start values (6 x the 50 ms lag)."""
STROKE_MAX_WITHOUT_YAML_M = 0.70
"""``s_max`` for monitors built without the YAML (tests); the controller passes
``actuator.stroke_m``."""
RETRACT_LOCK_ROD_PRESSURE_WITHOUT_YAML_PA = (34.818 * BAR_PA, 34.352 * BAR_PA,
                                             31.193 * BAR_PA, 30.591 * BAR_PA)
"""YAML ``actuator.rod_side.p_r0_after_retract_Pa`` (2026-10-22) for monitors built without
the YAML; the controller passes the YAML values."""
COLUMN_BOUND_META_KEYS = (
    "locked_ratio_kappa",
    "locked_ratio_head_dead_max_m",
    "locked_ratio_rod_dead_min_m",
    "locked_ratio_stroke_margin_m",
    "locked_ratio_stroke_max_m",
    "lock_window_valve_tau_s",
    "lock_window_eps_m_s",
    "locked_start_extend_Pa",
    "locked_start_retract_floor_Pa",
    "locked_start_lookback_s",
)

# P-S8-22 R-5 fallback slope (spec rev. 61 302.4, 304 ①, ④)
NOMINAL_DEAD_LENGTH_M = 0.05
"""ASSUMPTION (spec 305 (1), hydraulics nominal): ``L_0h`` = ``L_0r`` = 0.05 m of ``R_nom(s)``."""
ONLINE_RATIO_MIN_HEAD_CHANGE_PA = 5.0 * BAR_PA
ONLINE_RATIO_MAX_STROKE_CHANGE_M = 5e-3
"""Spec 302.4 (1): an online ``-dp_r / dp_h`` needs a head change of at least 5 bar with the
stroke reading within 5 mm of its reference sample."""


class LoadEstimate(StrEnum):
    """Load estimate of C2 (P-2, U43)."""

    NET = "net"
    """``p_h A_p - p_r A_ann`` when a rod-side pressure is measured (R6 default)."""
    HEAD_ONLY = "head_only"
    """``p_h A_p`` (R5; the rod-side pressure is ignored)."""


class LockValve(StrEnum):
    """Lock valve of the legs (YAML ``actuator.lock_valve``)."""

    PILOT_CHECK = "pilot_check"
    COUNTERBALANCE = "counterbalance"


class StepRule(StrEnum):
    """D1 rule for a one-period change above ``max_step_Pa`` (U-S8-26)."""

    EXPLAINED_IMU = "explained_imu"
    """D1'' (218.4, U-S8-31, default): D1' with the IMU residual head rule once the crawler is
    off and the rod-side reason ``lock_load_regain``."""
    EXPLAINED = "explained"
    """D1' (217.5): a step the hydraulics explain is ``INFO_PRESSURE_STEP``; others fault."""
    JUMP = "jump"
    """Every such step is a fault (the rule before U-S8-26)."""


class ImuMassCalibration(StrEnum):
    """``M_eff`` of the D1'' IMU residual (dynamics rev. 41 R41-1; control to decide)."""

    NOMINAL = "nominal"
    """The superstructure mass (YAML, or ``imu_mass_nominal_kg``): the Newton fit mass."""
    SLOPE = "slope"
    """Slope of the one-period ``d sum F`` on ``d f_z`` over lifted moving periods (the seal
    preload drops out as an intercept); used once enough samples and excitation exist."""
    MEDIAN = "median"
    """Median ``sum F / f_z`` of the last READY stay (218.4; biased up to +5.9 % by the
    stuck-seal preload)."""


class StepReason(StrEnum):
    """Why a D1 step is explained (the last field of ``INFO_PRESSURE_STEP``)."""

    LOCK_LOAD_LOSS = "lock_load_loss"
    """Rod side up, head down, leg locked this and the last period (lock law)."""
    CHECK_OPENED = "check_opened"
    """Rod side down into the D2 extend range under a positive command (pilot check open)."""
    LOAD_REDISTRIBUTION = "load_redistribution"
    """Head step with the four-leg net-force sum nearly unchanged."""
    IMU_RESIDUAL = "imu_residual"
    """D1'' head step with the IMU residual ``sum F - M_eff f_z`` nearly unchanged."""
    LOCK_LOAD_REGAIN = "lock_load_regain"
    """D1'' rod side down, head up, stroke still, ratio within ``1.4 R_ub(s)`` (a locked leg
    taking load back, the lock law in reverse)."""
    CHECK_DRAINING = "check_draining"
    """P-S8-21: rod side down under a positive command but still above the D2 extend range
    (the trapped lift-off pressure draining with ``tau_d`` about 50-55 ms), held one period
    and confirmed by the next reading (:data:`ROD_DRAIN_HOLD_RATIO`)."""


class LockedRatioRule(StrEnum):
    """Locked ``-dp_r / dp_h`` of the fallback estimate (P-S8-13)."""

    COLUMN_BOUND = "column_bound"
    """10.4 ①-⑥: ``R_ub(s)`` of the lock stroke, lock window, start candidates, reading bound."""
    FIXED = "fixed"
    """``fallback_locked_ratio`` from the first command-free sample (the rule before P-S8-13,
    kept bit for bit for regression)."""


class CbMovingRule(StrEnum):
    """Fallback ``p_r_hat`` of a moving leg with the counterbalance (P-S8-15)."""

    LAG_BOUND = "lag_bound"
    """Hydraulics 11.2 R4D: the CB law behind a first-order lag ``tau_cb``, as an upper bound
    ``Y_k = max(L_k, a Y_k-1 + (1 - a) max(L_k-1, L_k))``; both laws while the direction is
    uncertain."""
    LAW = "law"
    """The CB law at this head reading (9.6, the rule before P-S8-15; regression)."""


class EstimateSource(StrEnum):
    """Which bound gave the fallback ``p_r_hat`` (meta, 10.4 ⑦)."""

    MODEL = "model"
    READING = "reading"


class FallbackRatioSource(StrEnum):
    """Where ``R_rate`` / ``R_hi`` of the R-5 fallback slope come from (P-S8-22, spec 302.4)."""

    PLANT_META = "plant_meta"
    """L1-R runs: ``R_hi = R_rate`` = the fixed plant ratio (``fallback_locked_ratio``, at least
    the plant meta value); the level ratio becomes ``max(R_ub, kappa R_plant)`` (302.6)."""
    COLUMN_NOMINAL = "column_nominal"
    """Machine and L2b: ``R_hi = R_ub(s) / kappa``, ``R_rate = R_nom(s)`` (nominal dead lengths)."""
    ONLINE = "online"
    """As ``column_nominal``, but ``R_rate = min(R_hat, R_hi)`` with ``R_hat`` the last two-sensor
    locked ratio of the leg (``column_nominal`` without one, warned once)."""


class RodSensorState(StrEnum):
    OK = "ok"
    FALLBACK = "fallback"


class HeadSensorState(StrEnum):
    OK = "ok"
    FAULT = "fault"


FRONT_REAR = (0, 0, 1, 1)
"""Index of the front / rear value of a per-leg pair, LEG_ORDER (FL, FR, RL, RR)."""


def _per_leg(front: float, rear: float) -> tuple[float, ...]:
    return tuple((front, rear)[side] for side in FRONT_REAR)


ROD_WEIGHT_WITHOUT_YAML_N = _per_leg(1047.0, 701.0)
"""``m_rod g`` for monitors built without the YAML (tests); the controller passes the YAML
moving-part masses (spec 76.4 (2))."""


def _four(values: ArrayLike, name: str) -> NDArray[np.float64]:
    array = np.array(np.broadcast_to(np.asarray(values, dtype=float), (LEG_COUNT,)))
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name}: expected {LEG_COUNT} finite values, got {values!r}")
    return array


@dataclass(frozen=True)
class CounterbalanceRodModel:
    """Rod-side pressure the counterbalance regulates while a leg moves (P-S8-11).

    Hydraulics ``s8_seal_friction_counterbalance.md`` 4.3 writes the regulation with the
    pressure force ``F_p``; with ``F_p = p_h A_p - p_r A_ann`` it becomes a law of the measured
    head pressure alone (no area, no friction):

    * extend (rod-side CB meters B, pilot ~ ``p_h``): ``p_r = max(p_back, p_set - psi p_h)``
    * retract (head CB meters A, pilot ~ ``p_r``): ``p_r = (p_set - p_h) / psi``

    The lock-instant ``p_r0`` is the same law at the last moving sample. Gauge pressures [Pa].
    """

    p_set_Pa: float
    pilot_ratio: float
    back_pressure_Pa: float

    def __post_init__(self) -> None:
        if not self.pilot_ratio > 0.0:
            raise ValueError(
                f"pilot_ratio must be > 0 for the CB rod-side law, got {self.pilot_ratio!r} "
                "(the port-relief variant, pilot ratio 0, is not modelled by the diagnosis)"
            )

    @classmethod
    def from_params(cls, counterbalance: Any) -> CounterbalanceRodModel:
        """From :class:`outrigger_sim.params.CounterbalanceParams` (YAML
        ``actuator.counterbalance``) or any object with the same attribute names."""
        return cls(
            p_set_Pa=float(counterbalance.p_set_Pa),
            pilot_ratio=float(counterbalance.pilot_ratio),
            back_pressure_Pa=float(counterbalance.back_pressure_Pa),
        )

    def extend_rod_pressure_Pa(self, head_pressure_Pa: float) -> float:
        return max(self.back_pressure_Pa, self.p_set_Pa - self.pilot_ratio * head_pressure_Pa)

    def retract_rod_pressure_Pa(self, head_pressure_Pa: float) -> float:
        return max(0.0, (self.p_set_Pa - head_pressure_Pa) / self.pilot_ratio)


@dataclass(frozen=True)
class TwoPressureSettings:
    """Thresholds of the two-pressure reading (spec 64.2 defaults for the REXOME35 cylinders,
    replacing 53.3 / 53.4; every value ASSUMPTION unless the spec says otherwise).

    Names follow the spec items; ``*_Pa`` gauge pressures, ``*_N`` cylinder forces; tuples are
    per leg (LEG_ORDER).
    """

    diagnostics: bool = True
    """Run D1-D6, the fallback and the rod-side watch (``False`` = net force only)."""
    # D1
    sensor_range_Pa: tuple[float, float] = (-6.0 * BAR_PA, 410.0 * BAR_PA)
    """U72 (spec 72, 76.1): raw-value range; a normal sensor reads about -1.3 bar at 0 bar,
    which the old [-1, 400] bar range judged a fault."""
    signal_current_range_mA: tuple[float, float] | None = SIGNAL_CURRENT_RANGE_MA
    """U72: a reading whose 4-20 mA current lies outside this range (NAMUR NE 43) is a
    fault; ``None`` = no current check."""
    max_step_Pa: float = 100.0 * BAR_PA
    """Largest change of one reading in one period (a 20 ms design value, spec 53 / 64.2)."""
    step_rule: StepRule = StepRule.EXPLAINED_IMU
    """U-S8-31: ``explained_imu`` (D1'', 218.4, default), ``explained`` (D1', 217.5) or
    ``jump`` (every step above ``max_step_Pa`` is a fault). A settings object pickled before
    this field reads the class default; one pickled with ``explained`` keeps it (refresh it
    with :meth:`TwoPressureMonitor.refresh_settings`)."""
    explained_step_sum_ratio: float = EXPLAINED_STEP_SUM_RATIO
    rod_drain_hold_ratio: float | None = ROD_DRAIN_HOLD_RATIO
    """P-S8-21 ``rho`` of the ``check_draining`` hold (D1' and D1''); ``None`` = no hold (the
    rod-side rule before P-S8-21, bit for bit). Class default, so settings pickled before it
    read 0.5."""
    # D1'' (P-S8-14). Class defaults, so settings pickled before it read them.
    imu_residual_step_ratio: float = IMU_RESIDUAL_STEP_RATIO
    imu_mass_min_samples: int = IMU_MASS_MIN_SAMPLES
    """``median``: READY samples a stay needs before its median is used."""
    imu_mass_calibration: ImuMassCalibration = ImuMassCalibration.MEDIAN
    """``median`` (U-S8-36, control rev. 49 219). ``nominal`` and ``slope`` are kept as
    options only (dynamics R41-1); the slope of the 10 Hz controller readings scattered
    -90 % .. +580 % on the ML / p1r records."""
    imu_mass_nominal_kg: float | None = None
    """``nominal``: ``None`` = the YAML superstructure mass given to the monitor."""
    imu_mass_slope_min_samples: int = IMU_MASS_SLOPE_MIN_SAMPLES
    imu_mass_slope_min_rms_m_s2: float = IMU_MASS_SLOPE_MIN_RMS_M_S2
    imu_lever_correction: bool = True
    """P-S8-14 ⑤ (U-S8-36): ``f_z`` minus ``(alpha x r)_z``, ``alpha`` = (last - previous
    gyro partial mean) / ``imu_gyro_sample_period_s``; without gyro samples no correction
    (``WARN_D1_IMU_GYRO_MISSING`` once, when a step is judged; then the rev. 48 D1'' bit for
    bit)."""
    imu_lever_arm_m: tuple[float, float, float] | None = None
    """``r`` = IMU mount - centre of mass of the auger level, body axes; ``None`` = the value
    the controller computes from the params and gives to the monitor."""
    imu_gyro_sample_period_s: float = IMU_GYRO_SAMPLE_PERIOD_S
    imu_seal_band_factor: float = 0.0
    """Seal ambiguity band (dynamics R41-3): not used (U-S8-36); only 0 is accepted."""
    regain_stroke_change_max_m: float = REGAIN_STROKE_CHANGE_MAX_M
    regain_ratio_margin: float = REGAIN_RATIO_MARGIN
    pressure_noise_std_Pa: float = 0.0
    """Sensor noise of the run (0.3 bar for the specified sensors, P-16): widens the range by
    3 sigma and enables the stuck check (a reading that did not change over
    ``stuck_window_s``). 0 for ideal sensors (no stuck check)."""
    stuck_window_s: float = 10.0
    # D2 / D3
    moving_speed_fraction: float = 0.25
    moving_settle_s: float = 1.0
    """D2 / D3 judge a leg after a continuous move this long (64.2: >= 1 s)."""
    reversal_exclusion_s: float = 2.0
    """D2: not checked for this long after a retract -> extend reversal (64.2 R-H5: the
    pressure of the retraction end stays 128-191 bar into the next extension)."""
    extend_min_head_Pa: float = 20.0 * BAR_PA
    extend_rod_range_Pa: tuple[float, float] = (-1.0 * BAR_PA, 12.0 * BAR_PA)
    violation_hold_s: float = 1.0
    retract_check: bool = True
    """D3 (64.2): lower bound ``0.5 (3 + (p_h - 3) / 6 + 1)`` bar, upper 215 bar."""
    retract_pilot_ratio: float = 6.0
    retract_head_back_Pa: float = 3.0 * BAR_PA
    retract_cracking_Pa: float = 1.0 * BAR_PA
    retract_upper_Pa: float = 215.0 * BAR_PA
    # D4 / D5
    force_sigma_N: tuple[float, ...] = _per_leg(414.0, 300.0)
    """1 sigma of one two-sensor force reading (0.3 bar per sensor, 64.2)."""
    d4_min_samples: int = 2
    d4_hold_s: float = 0.1
    """110.2 (ASSUMPTION, 3 x the 30 ms M4 window): D4 falls back only after at least
    ``d4_min_samples`` violating samples in a row covering ``d4_hold_s`` (samples x period);
    the first violating sample is ``INFO_ROD_D4_TRANSIENT``."""
    sum_extra_N: float = 2500.0
    sum_hold_s: float = 0.5
    """D5 warns only when the sum change stays beyond its limit this long while judged
    (ASSUMPTION, not in spec 110.1): a floor event's dynamic transient (RE1b-F replay: sum
    -63 kN while the body drops, before the controller's first re-level command) is no sensor
    inconsistency; a static mismatch persists. 0 = the first sample warns."""
    load_reference_settle_s: float = 0.5
    """110.1 (ASSUMPTION: U67 tail 0.3 s + a few heave periods): the load baseline of D5, E-5
    and ``Delta F1`` needs every leg command zero for this long, and they are judged only
    while that holds."""
    load_reference_mean_s: float = 0.5
    """120 (ASSUMPTION, R7 25 samples): the load baseline is the mean nominal reading over this
    long before the store, so the 8.7 Hz heave ringing after a tail or probe does not bias it
    (one sample: up to -3.4 kN). Only command-free samples of the READY / DONE stay count; a
    value up to one period is the single-sample baseline of 110.1."""
    # D6
    probe_consistency_check: bool = True
    """D6 (64.2): ``p_r`` at the R hold end - at the E hold end >= max(3 bar, p_h / 12)."""
    probe_rise_min_Pa: float = 3.0 * BAR_PA
    probe_rise_head_ratio: float = 1.0 / 12.0
    probe_misses: int = 2
    # fallback (U45 a', 64.2)
    fallback_extend_Pa: float = 8.0 * BAR_PA
    fallback_pilot_ratio: float = 3.0
    fallback_head_back_Pa: float = 15.0 * BAR_PA
    fallback_cracking_Pa: float = 3.0 * BAR_PA
    fallback_locked_ratio: tuple[float, ...] = _per_leg(1.296, 1.232)
    """``-dp_r / dp_h`` of a locked leg (D8 ratio, hydraulics 12.2); used only by
    ``locked_ratio_rule = "fixed"``."""
    fallback_floor_Pa: float = -0.9 * BAR_PA
    fallback_min_band_N: float = 13e3
    """U65: the friction band of a fallback leg is at least this (its head-only F_s estimate
    and probe midpoint are not used)."""
    # locked fallback estimate (P-S8-13, hydraulics H-S8-2 10.4). Every field below has a
    # class default, so settings pickled before P-S8-13 read the column bound.
    locked_ratio_rule: LockedRatioRule = LockedRatioRule.COLUMN_BOUND
    """``column_bound`` (10.4 ①-⑥) or ``fixed`` (``fallback_locked_ratio``, the old estimate
    bit for bit, regression)."""
    locked_ratio_kappa: float = LOCKED_RATIO_KAPPA
    locked_ratio_head_dead_max_m: float = LOCKED_RATIO_HEAD_DEAD_MAX_M
    locked_ratio_rod_dead_min_m: float = LOCKED_RATIO_ROD_DEAD_MIN_M
    locked_ratio_stroke_margin_m: float = LOCKED_RATIO_STROKE_MARGIN_M
    locked_ratio_stroke_max_m: float | None = None
    """``s_max`` of ``R_ub``; ``None`` = YAML ``actuator.stroke_m`` given to the monitor."""
    lock_window_valve_tau_s: float = LOCK_WINDOW_VALVE_TAU_S
    """Valve lag of the lock window ``W = tau_v ln(max(|u_last|, eps) / eps) + T``; 0 = the
    first command-free sample alone."""
    lock_window_eps_m_s: float = LOCK_WINDOW_EPS_M_S
    locked_start_extend_Pa: float = LOCKED_START_EXTEND_PA
    """Pilot-check ``p_r_hat`` while extending and the start after an extension (the
    counterbalance keeps its CB law)."""
    locked_start_retract_floor_Pa: tuple[float, ...] | None = None
    """Lower end of the pilot-check start after a retraction per leg; ``None`` = YAML
    ``actuator.rod_side.p_r0_after_retract_Pa`` given to the monitor."""
    locked_start_lookback_s: float = LOCKED_START_LOOKBACK_S
    fallback_lower_deficit_cap_N: float | None = None
    """Open option for control (H-S8-2 10.7 ②), off by default: the lower-bound reading of a
    fallback leg is not taken below ``F_min - cap``, so the guard / re-approach deficit
    against ``F_min`` saturates at ``cap``. It gives up the upper-bound property of
    ``p_r_hat``; ``None`` = no cap."""
    # rod-side watch (P-13)
    rod_limit_Pa: float = 350.0 * BAR_PA
    """``rod_pressure_limit_Pa`` (ASSUMPTION 350 bar until the rod-side rating, Q-R5)."""
    rod_warning_margin_Pa: float = 5.0 * BAR_PA
    """E-4 (U72): ``rod_pressure_over_limit`` is raised above ``rod_limit_Pa`` minus this
    (345 bar; the sensor error near 350 bar is about 3 bar after the calibration)."""
    rod_prewarning_Pa: float = 300.0 * BAR_PA
    liftoff_rod_share: tuple[float, ...] = _per_leg(0.269, 0.289)
    """U49 ``r`` (upper value, L_0r 0.05 m; hydraulics 12.2)."""
    rod_weight_N: tuple[float, ...] | None = None
    """``m_rod g`` per leg; ``None`` = the YAML ``legs.<leg>.moving_part.mass_kg`` x g given
    to the monitor (spec 76.4 (2), single source), or :data:`ROD_WEIGHT_WITHOUT_YAML_N`
    without one."""
    rising_window_s: float = 10.0
    rising_min_Pa: float = 5.0 * BAR_PA
    rising_load_tolerance_N: float = 3000.0
    # shadows
    load_drop_N: float = 20000.0
    """P-6 (U47): ``Delta F`` below ``-load_drop_N`` for ``load_drop_hold_s``."""
    load_drop_hold_s: float = 0.5
    retract_speed_fraction: float = 0.1
    retract_settle_s: float = 0.3
    retract_average_s: float = 0.5
    retract_pad_limit_N: float = 2500.0
    """P-11 (U50): retraction lift-off when ``mean F + F_band + m_rod g`` is below this."""
    # E-5 static load sum drift (72.1 (6), U73)
    drift_sum_N: float | None = 4000.0
    """``WARN_PRESSURE_DRIFT`` when ``|sum F - sum F_ref|`` stays above this for
    ``drift_hold_s`` in READY (ASSUMPTION: 4 x 0.6 kN calibration residue + noise margin);
    ``None`` = off. Only the change of the sum is used, never ``sum F = W``."""
    drift_hold_s: float = 30.0
    # lock valve (P-S8-11, spec rev. 46 216.10)
    lock_valve: LockValve = LockValve.PILOT_CHECK
    """``counterbalance`` (hydraulics H-S8-1 9.5 / 9.6): D2 upper bound
    ``max(extend_rod_range_Pa[1], p_set - psi p_h) + counterbalance_rod_margin_Pa`` and the
    fallback estimate ``p_r_hat`` from the CB law plus its margins (extend at any positive
    command, retract; the lock start is the last moving value, i.e. the CB ``p_r0``).
    Set with :meth:`with_lock_valve`."""
    counterbalance: CounterbalanceRodModel | None = None
    """CB law of ``lock_valve = counterbalance`` (YAML ``actuator.counterbalance``)."""
    counterbalance_rod_margin_Pa: float = CB_ROD_MARGIN_PA
    counterbalance_extend_estimate_margin_Pa: float = CB_EXTEND_ESTIMATE_MARGIN_PA
    counterbalance_retract_estimate_margin_Pa: float = CB_RETRACT_ESTIMATE_MARGIN_PA
    counterbalance_moving_rule: CbMovingRule = CbMovingRule.LAG_BOUND
    """P-S8-15 (class default, so settings pickled before it read ``lag_bound``; their stored
    margins stay the old 11.4 / 0.7 bar until refreshed). Column-bound rule only: ``fixed``
    keeps the CB law."""
    counterbalance_lag_tau_s: float | None = None
    """``tau_cb`` of ``lag_bound``; ``None`` = YAML ``actuator.rod_side.release_tau_s`` given to
    the monitor (U-S8-H5: the real CB response bound replaces it)."""
    moving_stroke_check: bool = True
    """P-S8-11 ③, on by default since U-S8-28: D2 / D3 judge a leg only while its measured
    stroke changed in the commanded direction by at least ``moving_stroke_speed_fraction
    v_max`` over the last period; a leg not confirmed restarts its violation hold. Without a
    stroke reading the leg is not judged. A settings object pickled before U-S8-28 keeps its
    stored ``False`` (refresh it with :meth:`TwoPressureMonitor.refresh_settings`)."""
    moving_stroke_speed_fraction: float = STROKE_CHECK_SPEED_FRACTION

    def __post_init__(self) -> None:
        object.__setattr__(self, "lock_valve", LockValve(self.lock_valve))
        object.__setattr__(self, "step_rule", StepRule(self.step_rule))
        object.__setattr__(self, "locked_ratio_rule", LockedRatioRule(self.locked_ratio_rule))
        object.__setattr__(self, "counterbalance_moving_rule",
                           CbMovingRule(self.counterbalance_moving_rule))
        object.__setattr__(self, "imu_mass_calibration",
                           ImuMassCalibration(self.imu_mass_calibration))
        if self.imu_lever_arm_m is not None:
            object.__setattr__(self, "imu_lever_arm_m",
                               tuple(float(value) for value in self.imu_lever_arm_m))
        ratio = self.rod_drain_hold_ratio
        if ratio is not None and not (math.isfinite(ratio) and ratio >= 0.0):
            raise ValueError(f"rod_drain_hold_ratio: expected a finite ratio >= 0 or None, "
                             f"got {ratio!r}")
        if self.imu_seal_band_factor != 0.0:
            raise ValueError("imu_seal_band_factor: the seal ambiguity band is not implemented "
                             "(U-S8-36, control rev. 49 219); only 0 is accepted")
        if self.lock_valve is LockValve.COUNTERBALANCE and self.counterbalance is None:
            raise ValueError("lock_valve = counterbalance needs the CB law (counterbalance)")

    def with_lock_valve(
        self, lock_valve: str, counterbalance: Any | None = None
    ) -> TwoPressureSettings:
        """Copy for the lock valve of the run (P-S8-11).

        Args:
            lock_valve: YAML ``actuator.lock_valve`` (``pilot_check`` or ``counterbalance``).
            counterbalance: YAML ``actuator.counterbalance``
                (:class:`outrigger_sim.params.CounterbalanceParams`); needed for
                ``counterbalance``, ignored for ``pilot_check``.

        Returns:
            ``pilot_check``: a copy without a CB law (the default behaviour; the stroke check
            keeps its setting); ``counterbalance``: a copy with
            :class:`CounterbalanceRodModel` of ``counterbalance`` and the stroke check on
            (H-S8-1 9.5: a locked leg under a positive command follows the lock law, not the
            CB law). Margins and the stroke check stay settings (``dataclasses.replace``).

        Raises:
            ValueError: Unknown lock valve, or ``counterbalance`` without its parameters.
        """
        valve = LockValve(lock_valve)
        if valve is LockValve.PILOT_CHECK:
            return replace(self, lock_valve=valve, counterbalance=None)
        if counterbalance is None:
            raise ValueError("lock_valve = counterbalance needs actuator.counterbalance")
        model = CounterbalanceRodModel.from_params(counterbalance)
        return replace(self, lock_valve=valve, counterbalance=model, moving_stroke_check=True)

    def with_cb_law_estimate(self) -> TwoPressureSettings:
        """Copy with the CB moving estimate before P-S8-15 (9.6 law, margins 11.4 / 0.7 bar),
        for regression replays."""
        return replace(
            self,
            counterbalance_moving_rule=CbMovingRule.LAW,
            counterbalance_extend_estimate_margin_Pa=CB_LAW_EXTEND_ESTIMATE_MARGIN_PA,
            counterbalance_retract_estimate_margin_Pa=CB_LAW_RETRACT_ESTIMATE_MARGIN_PA,
        )

    def with_r8_period(self) -> TwoPressureSettings:
        """Copy with the 10 Hz (R8) diagnosis constants of spec rev. 29 126 #3.

        Load baseline settle 0.5 s (5 samples) and mean 1.5 s (15 samples, twice the 0.77 s
        period of the 8.7 Hz heave aliased to 1.3 Hz, ASSUMPTION), D4 two samples = 0.2 s
        (110.2), D5 hold 0.5 s (5 samples), E-5 hold 30 s. Only these fields are touched.
        """
        return replace(
            self,
            load_reference_settle_s=R8_LOAD_REFERENCE_SETTLE_S,
            load_reference_mean_s=R8_LOAD_REFERENCE_MEAN_S,
            d4_min_samples=R8_D4_MIN_SAMPLES,
            d4_hold_s=R8_D4_HOLD_S,
            sum_hold_s=R8_SUM_HOLD_S,
            drift_hold_s=R8_DRIFT_HOLD_S,
        )

    def to_meta(self) -> dict[str, Any]:
        """Settings for the run meta. The P-S8-11 keys appear only when in use (counterbalance,
        stroke check on; the stroke check is on by default since U-S8-28), the P-S8-13 column
        bound keys only with ``locked_ratio_rule = "column_bound"``, the D1'' keys only with
        ``step_rule = "explained_imu"``."""
        meta = {key: list(value) if isinstance(value, tuple) else value
                for key, value in asdict(self).items()}
        meta["step_rule"] = str(self.step_rule)
        if self.step_rule is not StepRule.EXPLAINED_IMU:
            for key in IMU_RULE_META_KEYS:
                del meta[key]
        else:
            meta["imu_mass_calibration"] = str(self.imu_mass_calibration)
        meta["locked_ratio_rule"] = str(self.locked_ratio_rule)
        if self.locked_ratio_rule is LockedRatioRule.FIXED:
            for key in COLUMN_BOUND_META_KEYS:
                del meta[key]
        if self.lock_valve is LockValve.PILOT_CHECK:
            for key in LOCK_VALVE_META_KEYS:
                del meta[key]
        else:
            meta["lock_valve"] = str(self.lock_valve)
            meta["counterbalance_moving_rule"] = str(self.counterbalance_moving_rule)
        if not self.moving_stroke_check:
            for key in STROKE_CHECK_META_KEYS:
                del meta[key]
        return meta


@dataclass(frozen=True)
class FallbackRatioChoice:
    """Ratio choice of the R-5 fallback slope (P-S8-22, spec 302.4 / 302.6), built by the
    controller from ``FastRelevelSettings``.

    Attributes:
        source: Where ``R_rate`` and ``R_hi`` come from.
        rate_intervals: R-5 ``n``: the head drop is taken over this many periods.
        nominal_head_dead_m: ``L_0h`` of ``R_nom(s)``.
        nominal_rod_dead_m: ``L_0r`` of ``R_nom(s)``.
        plant_ratio: Fixed L1-R plant ratio per leg (plant meta); ``None`` = the settings'
            ``fallback_locked_ratio``.
    """

    source: FallbackRatioSource
    rate_intervals: int
    nominal_head_dead_m: float = NOMINAL_DEAD_LENGTH_M
    nominal_rod_dead_m: float = NOMINAL_DEAD_LENGTH_M
    plant_ratio: tuple[float, ...] | None = None


@dataclass(frozen=True)
class FallbackSlopeInputs:
    """R-5 inputs of one fallback leg in a lock stretch (spec 302.1, 304 ②).

    Attributes:
        head_drop_Pa: ``Delta h_k = p_h(k - n) - p_h(k)``.
        depth_Pa: ``d_k = (h_a - p_h(k))^+`` below the anchor of the level bound.
        level_ratio: ``R_lvl``, the ratio of the level bound (after the 302.6 raise).
        high_ratio: ``R_hi``, the largest true ratio to cover.
        rate_ratio: ``R_rate``, the nominal ratio, already cut to ``[0, R_hi]``.
        head_area_m2: ``A_p`` of the leg.
        annulus_area_m2: ``A_ann`` of the leg.
    """

    head_drop_Pa: float
    depth_Pa: float
    level_ratio: float
    high_ratio: float
    rate_ratio: float
    head_area_m2: float
    annulus_area_m2: float

    def force_gain_N_per_Pa(self, ratio: float) -> float:
        """``G(R) = A_p + R A_ann``: force drop per pascal of head drop [N/Pa]."""
        return self.head_area_m2 + ratio * self.annulus_area_m2

    @property
    def level_reserve_N(self) -> float:
        """``C_k = (R_lvl - R_hi) A_ann d_k``: conservatism the level bound already holds."""
        return (self.level_ratio - self.high_ratio) * self.annulus_area_m2 * self.depth_Pa

    def drop_N(self, rate_intervals: int, horizon_periods: int) -> tuple[float, float]:
        """302.2 ``D_k = max{G(R_rate) Dh, G(R_hi) Dh - (n / h) C_k}`` over ``n`` periods.

        Returns:
            (``D_k``, gap): the gap is how far the covering term lies above the nominal
            term (0 when the nominal term decides), both in N over ``n`` periods.
        """
        nominal_N = self.force_gain_N_per_Pa(self.rate_ratio) * self.head_drop_Pa
        covering_N = (self.force_gain_N_per_Pa(self.high_ratio) * self.head_drop_Pa
                      - rate_intervals / horizon_periods * self.level_reserve_N)
        return max(nominal_N, covering_N), max(covering_N - nominal_N, 0.0)


@dataclass(frozen=True, eq=False)
class PressureForces:
    """Cylinder-force readings of one period (N, (4,) each).

    Attributes:
        nominal: The load reading: net force, the head reading on a fallback leg (twist loop,
            completion, GE1' deflection, REANCHOR stop).
        lower: Lower-bound reading for ABOVE, guard, P5, Q2 and the probe: ``nominal`` except
            on a fallback leg (head reading minus ``p_r_hat A_ann``).
        upper: Upper-bound reading for BELOW (fallback leg: head reading plus the floor).
        head_only: ``p_h A_p`` (P-3: the 350 bar check uses the raw head pressure).
    """

    nominal: NDArray[np.float64]
    lower: NDArray[np.float64]
    upper: NDArray[np.float64]
    head_only: NDArray[np.float64]


@dataclass
class _LegWatch:
    """Per-leg bookkeeping of the diagnosis."""

    moving_since_s: float | None = None
    moving_sign: float = 0.0
    violation_since_s: float | None = None
    rod_estimate_Pa: float = 0.0
    lock_rod_estimate_Pa: float | None = None
    lock_head_Pa: float | None = None
    load_drop_since_s: float | None = None
    d4_violation_samples: int = 0
    probe_misses: int = 0
    retract_samples: int = 0
    last_retract_t_s: float = -math.inf


@dataclass(frozen=True)
class _ImuInput:
    """D1'' inputs of one period (see :meth:`TwoPressureMonitor.read`)."""

    f_z_m_s2: float | None
    """Body-z specific force of the last IMU sample, minus the lever term when corrected."""
    is_crawler_lifted: bool
    is_lever_missing: bool = False
    """The lever correction is on but no gyro samples came (``f_z`` uncorrected)."""

    @property
    def has_f_z(self) -> bool:
        return self.f_z_m_s2 is not None and math.isfinite(self.f_z_m_s2)


@dataclass
class _LockStretch:
    """P-S8-13 state of one leg for the column-bound fallback estimate (10.4 ②-⑤).

    A stretch is the run of samples whose acting command is zero; it opens at the first such
    sample ``k0`` and closes at the next non-zero command.
    """

    last_sign: float = 1.0
    """Direction of the last non-zero command; +1 at the run start (locked after an
    extension, as the reset estimate), 0 = unknown (state created for an old pickle)."""
    last_command_m_s: float = 0.0
    """``u_last`` of the lock window (0 = none: the window is one period)."""
    moving_starts: deque[tuple[float, float]] = field(default_factory=deque)
    """(t, start value of the moving model) of the moving samples of the lookback."""
    is_open: bool = False
    start_t_s: float = math.nan
    window_end_s: float = math.nan
    previous_moving_max_Pa: float = -math.inf
    """Largest moving-model start value within ``locked_start_lookback_s`` before ``k0``."""
    candidates: list[tuple[float, float]] = field(default_factory=list)
    """(start value ``M_j``, head reading ``p_h,j``) of the lock-instant candidates."""
    stroke_window_max_m: float = -math.inf
    """``s_w``: largest finite stroke reading of the candidates."""
    valid_rod_Pa: float | None = None
    """Last valid rod-side reading of the stretch (``k_v``), ``None`` = none."""
    valid_head_max_Pa: float = -math.inf
    """``H_v``: head at ``k_v`` and the largest window head after it."""
    valid_stroke_m: float = -math.inf
    ratio_bound: float = math.nan
    estimate_source: EstimateSource = EstimateSource.MODEL
    anchor_head_Pa: float = math.nan
    """Head reading of the candidate (or ``H_v``) that gave the estimate."""
    start_Pa: float = math.nan
    """Start value (``M_j`` or the valid reading) that gave the estimate."""
    # P-S8-15 CB lag bound (immutable defaults: class attributes for pickles before it)
    recent_commands_m_s: tuple[float, ...] = ()
    """Applied commands of the last ``N_rev`` periods, oldest first (③)."""
    previous_head_Pa: float = math.nan
    lag_bound_Pa: float = math.nan
    """``Y_k-1`` of the moving stretch (pre-margin); NaN = no moving stretch yet (①)."""
    lag_law_Pa: float = math.nan
    """``L_k-1``: the CB law (or both laws) at the last head reading."""
    # P-S8-22 (immutable defaults: class attributes for pickles before it)
    ratio_stroke_m: float = math.nan
    """Stroke reading behind ``ratio_bound`` (-inf = none; NaN = not yet computed)."""
    online_reference: tuple[float, float, float] | None = None
    """(head, rod, stroke) of the first two-sensor sample after the lock window (④)."""

    def summary(self, leg: int) -> dict[str, Any]:
        """Meta row of the stretch (10.4 ⑦)."""
        return {
            "leg": LEG_ORDER[leg],
            "t_start_s": self.start_t_s,
            "window_end_s": self.window_end_s,
            "stroke_window_max_m": _finite_or_none(self.stroke_window_max_m),
            "ratio_bound": _finite_or_none(self.ratio_bound),
            "anchor_head_Pa": _finite_or_none(self.anchor_head_Pa),
            "start_Pa": _finite_or_none(self.start_Pa),
            "source": str(self.estimate_source),
        }


def _finite_or_none(value: float) -> float | None:
    return float(value) if math.isfinite(value) else None


@dataclass
class _ReadyBaseline:
    """Load baseline of D5, E-5 and ``Delta F1`` (110.1; no longer the GE1' reference)."""

    loads_N: NDArray[np.float64]
    t_s: float
    is_active: bool = True
    """``False`` from a new READY / DONE stay until the next store (stale baseline)."""
    load_drop_flagged: set[int] = field(default_factory=set)
    sum_mismatch_since_s: float | None = None
    """D5: start of the unbroken run of judged samples with the sum change beyond the limit."""
    is_sum_warned: bool = False
    drift_since_s: float | None = None
    """E-5: start of the unbroken run of samples with the sum change above the limit."""
    drift_fallback_count: int = 0
    """Fallback legs at the start of that run (a new fallback is an event: the run restarts)."""


class TwoPressureMonitor:
    """Net force, diagnosis, fallback and rod-side watch of the four legs (module docstring).

    Args:
        head_area_m2: ``A_p`` per leg (4,).
        annulus_area_m2: ``A_ann`` per leg (4,).
        max_speed_m_s: ``v_max`` (moving conditions).
        F_min_N: ``F_min`` (a leg is grounded for D2 / D3 when ``F - F_band >= F_min``).
        period_s: Control period.
        load_estimate: ``net`` or ``head_only``.
        settings: Thresholds.
        rod_weight_N: ``m_rod g`` per leg from the YAML; an explicit
            ``settings.rod_weight_N`` wins.
        stroke_max_m: YAML ``actuator.stroke_m`` for ``R_ub`` (P-S8-13); an explicit
            ``settings.locked_ratio_stroke_max_m`` wins.
        retract_lock_rod_pressure_Pa: YAML ``actuator.rod_side.p_r0_after_retract_Pa`` per
            leg (P-S8-13 start after a retraction); an explicit
            ``settings.locked_start_retract_floor_Pa`` wins.
        counterbalance_lag_tau_s: YAML ``actuator.rod_side.release_tau_s`` (P-S8-15 ``tau_cb``);
            an explicit ``settings.counterbalance_lag_tau_s`` wins.
        body_mass_kg: Superstructure mass of the run (D1'' ``nominal``); an explicit
            ``settings.imu_mass_nominal_kg`` wins.
        imu_lever_arm_m: IMU mount minus the centre of mass, body axes (D1'' lever term); an
            explicit ``settings.imu_lever_arm_m`` wins.
    """

    # Class-level defaults of the attributes added by P-S8-11: a monitor pickled before them
    # (ML ``branch.pkl``) lacks the instance attributes and must keep running unchanged.
    _previous_stroke_m: NDArray[np.float64] | None = None
    _stroke_rate_m_s: NDArray[np.float64] | None = None
    """P-S8-11 ③: measured stroke change over the last period / period (``None`` before two
    stroke readings)."""
    _previous_commanded_m_s: NDArray[np.float64] | None = None
    """D1' (P-S8-12): the acting command of the last diagnosed period (``None`` = unknown: a
    new monitor, or one pickled before P-S8-12; this period's command stands in for it)."""
    # P-S8-13: class defaults for monitors pickled before it.
    _column_stroke_max_m: float = STROKE_MAX_WITHOUT_YAML_M
    _retract_lock_floor_Pa: tuple[float, ...] = RETRACT_LOCK_ROD_PRESSURE_WITHOUT_YAML_PA
    _lock_stretches: list[_LockStretch] | None = None
    """Per-leg column-bound state; ``None`` = not yet created (an old pickle: created with an
    unknown last direction on the next read)."""
    _fallback_lock_log: list[dict[str, Any]] | None = None
    """Closed stretches of fallback legs (meta, 10.4 ⑦)."""
    # P-S8-14 (D1''): class defaults for monitors pickled before it.
    _imu_mass_ratios_kg: deque[float] | None = None
    """``sum F / f_z`` of the current READY stay (newest last); ``None`` = not yet created."""
    _imu_mass_kg: float | None = None
    """``M_eff`` of the last READY stay with enough samples; ``None`` = none yet."""
    _previous_imu_f_z_m_s2: float | None = None
    """IMU ``f_z`` of the last diagnosed period (``None`` = not given)."""
    _was_locked_phase: bool = False
    """The last diagnosed period was READY (a READY stay starts on the change)."""
    _cb_lag_tau_s: float = CB_LAG_TAU_WITHOUT_YAML_S
    """P-S8-15 ``tau_cb`` (class default for monitors pickled before it)."""
    _body_mass_kg: float = BODY_MASS_WITHOUT_YAML_KG
    _imu_lever_arm_m: tuple[float, float, float] = IMU_LEVER_ARM_WITHOUT_YAML_M
    _imu_slope_sums: tuple[float, float, int] = (0.0, 0.0, 0)
    """``slope``: (sum d(sum F) d f_z, sum d f_z^2, count) over lifted moving periods."""
    _rod_drain_held_Pa: list[float | None] | None = None
    """P-S8-21: per leg the rod-side reading of a ``check_draining`` fall held for the next
    period (``None`` = no hold); the list itself ``None`` = a monitor pickled before it."""
    # P-S8-22: class defaults for monitors pickled before it.
    _r5_ratio_choice: FallbackRatioChoice | None = None
    """The choice of the last read; ``None`` = R-5 fallback slope off (nothing changes)."""
    _r5_inputs: list[FallbackSlopeInputs | None] | None = None
    """Per leg the R-5 inputs of the last read (``None`` = the leg does not qualify)."""
    _online_ratios: list[float | None] | None = None
    """④ per leg the last two-sensor locked ``-dp_r / dp_h`` (kept once the leg falls back)."""
    _BUFFER_SIZING_FIELDS = (
        "stuck_window_s",
        "rising_window_s",
        "retract_average_s",
        "load_reference_mean_s",
    )
    """Settings that size the history buffers in :meth:`reset` (fixed for a running monitor)."""

    def __init__(
        self,
        head_area_m2: ArrayLike,
        annulus_area_m2: ArrayLike,
        max_speed_m_s: float,
        F_min_N: float,
        period_s: float,
        load_estimate: LoadEstimate = LoadEstimate.NET,
        settings: TwoPressureSettings | None = None,
        rod_weight_N: ArrayLike | None = None,
        stroke_max_m: float | None = None,
        retract_lock_rod_pressure_Pa: ArrayLike | None = None,
        counterbalance_lag_tau_s: float | None = None,
        body_mass_kg: float | None = None,
        imu_lever_arm_m: ArrayLike | None = None,
    ) -> None:
        self.head_area_m2 = np.asarray(head_area_m2, dtype=float)
        self.annulus_area_m2 = np.asarray(annulus_area_m2, dtype=float)
        self.max_speed_m_s = float(max_speed_m_s)
        self.F_min_N = float(F_min_N)
        self.period_s = float(period_s)
        self.load_estimate = LoadEstimate(load_estimate)
        self.settings = settings or TwoPressureSettings()
        weight = self.settings.rod_weight_N
        if weight is None:
            weight = ROD_WEIGHT_WITHOUT_YAML_N if rod_weight_N is None else rod_weight_N
        self.rod_weight_N = _four(weight, "rod_weight_N")
        self._column_stroke_max_m = self._resolve_stroke_max_m(stroke_max_m)
        self._retract_lock_floor_Pa = self._resolve_retract_floor_Pa(retract_lock_rod_pressure_Pa)
        self._cb_lag_tau_s = self._resolve_cb_lag_tau_s(counterbalance_lag_tau_s)
        if body_mass_kg is not None:
            self._body_mass_kg = float(body_mass_kg)
        if imu_lever_arm_m is not None:
            arm = np.asarray(imu_lever_arm_m, dtype=float)
            self._imu_lever_arm_m = (float(arm[0]), float(arm[1]), float(arm[2]))
        self.reset()

    def _resolve_cb_lag_tau_s(self, tau_s: float | None) -> float:
        explicit = self.settings.counterbalance_lag_tau_s
        value = explicit if explicit is not None else tau_s
        if value is None:
            return CB_LAG_TAU_WITHOUT_YAML_S
        if not (math.isfinite(value) and value >= 0.0):
            raise ValueError(f"counterbalance_lag_tau_s: expected a finite tau >= 0, got {value!r}")
        return float(value)

    def _resolve_stroke_max_m(self, stroke_max_m: float | None) -> float:
        explicit = self.settings.locked_ratio_stroke_max_m
        value = explicit if explicit is not None else stroke_max_m
        if value is None:
            return STROKE_MAX_WITHOUT_YAML_M
        if not (math.isfinite(value) and value > LOCKED_RATIO_STROKE_END_GAP_M):
            raise ValueError(f"stroke_max_m: expected a finite stroke > 1 mm, got {value!r}")
        return float(value)

    def _resolve_retract_floor_Pa(self, retract_Pa: ArrayLike | None) -> tuple[float, ...]:
        explicit = self.settings.locked_start_retract_floor_Pa
        value = explicit if explicit is not None else retract_Pa
        if value is None:
            return RETRACT_LOCK_ROD_PRESSURE_WITHOUT_YAML_PA
        return tuple(float(v) for v in _four(value, "retract_lock_rod_pressure_Pa"))

    def reset(self) -> None:
        self.rod_state = [RodSensorState.OK] * LEG_COUNT
        self.head_state = [HeadSensorState.OK] * LEG_COUNT
        self.has_rod_sensor = False
        """A rod-side pressure was seen (and used) in this run."""
        # start = locked after an extension (rod side at the return back pressure)
        start_estimate = self.settings.fallback_extend_Pa
        self._legs = [_LegWatch(rod_estimate_Pa=start_estimate) for _ in range(LEG_COUNT)]
        self._previous: tuple[NDArray[np.float64], NDArray[np.float64] | None] | None = None
        window = max(1, round(self.settings.stuck_window_s / self.period_s))
        self._stuck_history: deque[tuple[NDArray, NDArray | None]] = deque(maxlen=window)
        rising = max(1, round(self.settings.rising_window_s / self.period_s))
        self._ready_history: deque[tuple[NDArray, NDArray]] = deque(maxlen=rising)
        self._retract_history: deque[NDArray] = deque(
            maxlen=max(1, round(self.settings.retract_average_s / self.period_s)))
        self._history: deque[tuple[float, NDArray, NDArray | None]] = deque(
            maxlen=max(1, round(20.0 / self.period_s)))
        self._baseline: _ReadyBaseline | None = None
        self._command_free_samples: int | None = None
        """Reads in a row whose acting command was zero on every leg; ``None`` = no command
        seen yet (command-free since ever, as the controller's GE1'-c count)."""
        mean_samples = max(1, round(self.settings.load_reference_mean_s / self.period_s))
        self._load_samples: deque[NDArray[np.float64]] = deque(maxlen=mean_samples)
        """120: command-free nominal readings of the current READY / DONE stay (newest last),
        averaged into the load baseline; emptied by a command and by a new stay."""
        self._load_reference_log: list[dict[str, Any]] = []
        self._load_sum_log: list[dict[str, Any]] = []
        self._reported: set[str] = set()
        self._events: list[tuple[str, bool]] = []
        self.zero_offsets_N = np.zeros(LEG_COUNT)
        """E-3: ``c_i`` removed from every force reading (CHECK zero calibration)."""
        self.offset_allowance_N = np.zeros(LEG_COUNT)
        """E-6: deduction of the lower-bound reading (the larger of it and the fallback
        bound is used, never both)."""
        self._previous_stroke_m = None
        self._stroke_rate_m_s = None
        self._previous_commanded_m_s = None
        self._lock_stretches = [_LockStretch() for _ in range(LEG_COUNT)]
        self._fallback_lock_log = []
        self._imu_mass_ratios_kg = None
        self._imu_mass_kg = None
        self._previous_imu_f_z_m_s2 = None
        self._was_locked_phase = False
        self._imu_slope_sums = (0.0, 0.0, 0)
        self._rod_drain_held_Pa = [None] * LEG_COUNT
        self._r5_ratio_choice = None
        self._r5_inputs = [None] * LEG_COUNT
        self._online_ratios = [None] * LEG_COUNT

    def refresh_settings(self, settings: TwoPressureSettings) -> None:
        """Use ``settings`` from the next read on, keeping the run's state.

        For a monitor restored from a pickle written by older code (ML ``branch.pkl``,
        C-S8-25 ③): its stored settings miss the later defaults (U-S8-26 step rule, U-S8-28
        stroke check). The fallback, fault and baseline state carry over unchanged, and so
        does the rod weight resolved at construction.

        Args:
            settings: The thresholds to use (typically the current code's run settings).

        Raises:
            ValueError: A setting that sizes the history buffers differs from the running one
                (that would need :meth:`reset`).
        """
        changed = [name for name in self._BUFFER_SIZING_FIELDS
                   if getattr(settings, name) != getattr(self.settings, name)]
        if changed:
            raise ValueError(f"refresh_settings cannot change the buffer sizes: {changed}")
        self.settings = settings
        if settings.locked_ratio_stroke_max_m is not None:
            self._column_stroke_max_m = self._resolve_stroke_max_m(None)
        if settings.locked_start_retract_floor_Pa is not None:
            self._retract_lock_floor_Pa = self._resolve_retract_floor_Pa(None)
        if settings.counterbalance_lag_tau_s is not None:
            self._cb_lag_tau_s = self._resolve_cb_lag_tau_s(None)

    # --- public ---

    @property
    def fallback_legs(self) -> list[int]:
        return [leg for leg, state in enumerate(self.rod_state) if state is RodSensorState.FALLBACK]

    @property
    def head_fault_legs(self) -> list[int]:
        return [leg for leg, state in enumerate(self.head_state) if state is HeadSensorState.FAULT]

    def set_zero_offsets_N(self, offsets_N: ArrayLike) -> None:
        """E-3: net-force zero offsets ``c_i`` removed from now on (0 = not calibrated)."""
        self.zero_offsets_N = _four(offsets_N, "offsets_N")

    def set_offset_allowance_N(self, allowance_N: ArrayLike) -> None:
        """E-6: lower-bound deduction per leg from now on (``>= 0``)."""
        allowance = _four(allowance_N, "allowance_N")
        if np.any(allowance < 0.0):
            raise ValueError(f"allowance_N: expected values >= 0, got {allowance_N!r}")
        self.offset_allowance_N = allowance

    def pop_events(self) -> list[tuple[str, bool]]:
        """(name, is_warning) raised since the last call."""
        events, self._events = self._events, []
        return events

    def read(
        self,
        t_s: float,
        head_pressure_Pa: NDArray[np.float64],
        rod_pressure_Pa: NDArray[np.float64] | None,
        commanded_m_s: NDArray[np.float64],
        is_locked_phase: bool,
        seal_band_N: float | NDArray[np.float64],
        stroke_m: ArrayLike | None = None,
        imu_specific_force_z_m_s2: float | None = None,
        is_crawler_lifted: bool = False,
        imu_gyro_rad_s: ArrayLike | None = None,
        r5_fallback_ratios: FallbackRatioChoice | None = None,
    ) -> PressureForces:
        """One period: the force readings; diagnosis and watch events go to :meth:`pop_events`.

        ``commanded_m_s`` = the controller's output of the previous period (what the legs do
        now); ``is_locked_phase`` = READY (legs locked, D4 / D5 / rod-side watch, the
        ``median`` mass samples of D1''); ``stroke_m`` = measured strokes, used by the stroke
        check of D2 / D3, the lock stroke of the fallback estimate (P-S8-13) and
        ``lock_load_regain``; ``imu_specific_force_z_m_s2`` = body-z specific force of the
        last IMU sample of the period (10 ms partial mean ending at ``t_s``, D1''; ``None`` =
        not available); ``is_crawler_lifted`` = the phase is LEVEL or later (D1'' applies);
        ``imu_gyro_rad_s`` = the last two gyro partial means of the period (10 ms each,
        oldest first, body axes, shape (2, 2) x-y or (2, 3); D1'' lever term; ``None`` = no
        gyro samples); ``r5_fallback_ratios`` = the R-5 fallback slope choice (P-S8-22,
        :meth:`r5_fallback_inputs`; ``None`` = off, bit for bit the reading before it).
        """
        self._r5_ratio_choice = r5_fallback_ratios
        self._r5_inputs = [None] * LEG_COUNT
        self._update_stroke_rate(stroke_m)
        self._count_command_free(commanded_m_s)
        head_only = head_pressure_Pa * self.head_area_m2
        if rod_pressure_Pa is None or self.load_estimate is LoadEstimate.HEAD_ONLY:
            forces = self._corrected(PressureForces(head_only, head_only, head_only, head_only))
            self._collect_load_sample(forces.nominal)
            if self.settings.diagnostics:
                self._watch_drift(t_s, forces.nominal, is_locked_phase)
            return forces
        self.has_rod_sensor = True
        rod = np.asarray(rod_pressure_Pa, dtype=float)
        if self.settings.diagnostics:
            net = head_only - rod * self.annulus_area_m2
            if self._has_zero_offsets:
                net = net - self.zero_offsets_N
            grounded = net - seal_band_N >= self.F_min_N
            imu_input = self._imu_input(imu_specific_force_z_m_s2, is_crawler_lifted,
                                        imu_gyro_rad_s)
            self._diagnose_sensors(t_s, head_pressure_Pa, rod, commanded_m_s, grounded,
                                   imu_input)
            if self.settings.step_rule is StepRule.EXPLAINED_IMU:
                self._track_imu_mass(head_pressure_Pa, rod, imu_input, is_locked_phase)
        self._update_rod_estimates(t_s, head_pressure_Pa, rod, commanded_m_s, stroke_m)
        forces = self._forces(head_pressure_Pa, rod, head_only)
        self._collect_load_sample(forces.nominal)
        if self.settings.diagnostics:
            self._check_locked(t_s, rod, forces, is_locked_phase, seal_band_N)
            self._watch_retraction(forces.nominal, commanded_m_s, seal_band_N)
            self._watch_drift(t_s, forces.nominal, is_locked_phase)
        self._history.append((float(t_s), np.array(rod), np.array(head_pressure_Pa)))
        if r5_fallback_ratios is not None:
            self._update_r5_inputs(r5_fallback_ratios)
        return forces

    @property
    def command_free_s(self) -> float:
        """Time every leg command has been zero up to the last read (``inf`` before any
        command); the command read at ``t`` acted over the period before ``t``."""
        if self._command_free_samples is None:
            return math.inf
        return self._command_free_samples * self.period_s

    @property
    def is_load_watch_open(self) -> bool:
        """110.1 (4): D5, E-5 and ``Delta F1`` are judged now (active baseline, commands zero
        for ``load_reference_settle_s``)."""
        baseline = self._baseline
        if baseline is None or not baseline.is_active:
            return False
        return self.command_free_s >= self.settings.load_reference_settle_s - 1e-9

    def store_load_reference(
        self, t_s: float, loads_N: NDArray[np.float64], source: str = ""
    ) -> None:
        """Store the load baseline of D5, E-5 and ``Delta F1`` (110.1, 120).

        The controller calls this on the first READY / DONE period with the GE1'-c gate open
        and the commands zero for ``load_reference_settle_s``, never at the TOUCH end. The
        baseline is the mean of the command-free readings of this stay over the last
        ``load_reference_mean_s`` (this period's reading included); ``loads_N`` is used only
        when none is buffered. The sum change against the previous baseline is logged (the
        sum should not change).

        Args:
            t_s: Time of the reading.
            loads_N: Nominal cylinder-force readings of this period (4,).
            source: Phase that stored it (meta).
        """
        sample_count = len(self._load_samples)
        if sample_count:
            loads = np.mean(np.array(self._load_samples), axis=0)
        else:
            loads = np.array(loads_N, dtype=float)
        sum_N = float(np.sum(loads))
        previous = self._baseline
        previous_sum_N = None if previous is None else float(np.sum(previous.loads_N))
        sum_change_N = None if previous_sum_N is None else sum_N - previous_sum_N
        self._load_reference_log.append({
            "t_s": float(t_s),
            "source": source,
            "sum_N": sum_N,
            "previous_sum_N": previous_sum_N,
            "sum_change_N": sum_change_N,
            "mean_window_s": self.settings.load_reference_mean_s,
            "sample_count": max(sample_count, 1),
            "last_sample_sum_N": float(np.sum(loads_N)),
        })
        self._baseline = _ReadyBaseline(loads, float(t_s))

    def suspend_load_reference(self) -> None:
        """A new READY / DONE stay began: the old baseline is not judged until the next
        :meth:`store_load_reference` (110.1 (5)), and the readings of the stay before are
        dropped from the baseline mean; the newest one, read in the period that entered the
        stay, is kept when command-free (120)."""
        newest = self._load_samples[-1] if self._load_samples else None
        self._load_samples.clear()
        if newest is not None:
            self._load_samples.append(newest)
        if self._baseline is not None:
            self._baseline.is_active = False
            self._baseline.drift_since_s = None

    def load_change_N(self, loads_N: NDArray[np.float64]) -> NDArray[np.float64] | None:
        """``F - F(t_ref)`` against the last load baseline (``None`` before one)."""
        if self._baseline is None:
            return None
        return np.asarray(loads_N, dtype=float) - self._baseline.loads_N

    def probe_round_finished(self, results) -> None:
        """D6 (off by default): the rod side must rise from the extend hold to the retract
        hold of a probe (31-37 bar trapped after a retraction, 53.3)."""
        if not (self.settings.diagnostics and self.settings.probe_consistency_check):
            return
        for result in results:
            leg = result.leg_index
            if result.is_skipped or self.rod_state[leg] is RodSensorState.FALLBACK:
                continue
            extend_s, retract_s = result.t_first_hold_end_s, result.t_second_hold_end_s
            if result.is_reversed:
                extend_s, retract_s = retract_s, extend_s
            at_extend, at_retract = self._sample_at(extend_s), self._sample_at(retract_s)
            if at_extend is None or at_retract is None:
                continue
            rise = at_retract[0][leg] - at_extend[0][leg]
            required = max(self.settings.probe_rise_min_Pa,
                           self.settings.probe_rise_head_ratio * at_retract[1][leg])
            watch = self._legs[leg]
            watch.probe_misses = watch.probe_misses + 1 if rise < required else 0
            if watch.probe_misses >= self.settings.probe_misses:
                self._fall_back(leg, "D6")

    def leg_seal_bands_N(self, seal_band_N: float) -> NDArray[np.float64]:
        """U65: per-leg friction band; a fallback leg takes at least ``fallback_min_band_N``."""
        bands = np.full(LEG_COUNT, float(seal_band_N))
        for leg in self.fallback_legs:
            bands[leg] = max(bands[leg], self.settings.fallback_min_band_N)
        return bands

    def r5_fallback_inputs(self, leg: int) -> FallbackSlopeInputs | None:
        """P-S8-22: the R-5 fallback slope inputs of ``leg`` from the last read.

        ``None`` unless that read had a :class:`FallbackRatioChoice` and the leg met spec
        302.2 conditions 1-3: a rod-side fallback leg on the column bound, whose last
        ``n + 1`` samples all lie in one open lock stretch (stretch start at or before
        ``t_(k-n)``, so no command in between), with a finite level bound.
        """
        inputs = self._r5_inputs
        return None if inputs is None else inputs[leg]

    def meta(self) -> dict[str, Any]:
        optional = {}
        if self.settings.step_rule is StepRule.EXPLAINED_IMU:
            optional["d1_imu_mass_kg"] = self._imu_mass_estimate_kg()
            optional["d1_imu_median_mass_kg"] = self._imu_mass_kg
            optional["d1_imu_slope_mass_kg"] = self._imu_slope_mass_kg()
            optional["d1_imu_slope_samples"] = self._imu_slope_sums[2]
        if self._uses_cb_lag_bound:
            optional["counterbalance_lag_tau_s_used"] = self._cb_lag_tau_s
        if self._is_tracking_online_ratio:
            optional["r5_online_ratio"] = list(self._online_ratios or [None] * LEG_COUNT)
        return {
            **optional,
            "load_estimate": str(self.load_estimate),
            "has_rod_sensor": self.has_rod_sensor,
            "rod_sensor_state": {LEG_ORDER[i]: str(s) for i, s in enumerate(self.rod_state)},
            "head_sensor_state": {LEG_ORDER[i]: str(s) for i, s in enumerate(self.head_state)},
            "fallback_rod_estimate_Pa": [w.rod_estimate_Pa for w in self._legs],
            "fallback_estimate_rule": str(self.settings.locked_ratio_rule),
            **self._fallback_lock_meta(),
            "zero_offsets_N": self.zero_offsets_N.tolist(),
            "offset_allowance_N": self.offset_allowance_N.tolist(),
            "head_area_m2": self.head_area_m2.tolist(),
            "annulus_area_m2": self.annulus_area_m2.tolist(),
            "rod_weight_N": self.rod_weight_N.tolist(),
            "load_reference": list(self._load_reference_log),
            "load_sum_events": list(self._load_sum_log),
            "settings": self.settings.to_meta(),
        }

    # --- events ---

    def _event_once(self, name: str, is_warning: bool = True) -> None:
        if name not in self._reported:
            self._reported.add(name)
            self._events.append((name, is_warning))

    def _fall_back(self, leg: int, reason: str) -> None:
        if self.rod_state[leg] is RodSensorState.FALLBACK:
            return
        self.rod_state[leg] = RodSensorState.FALLBACK
        self._event_once(f"WARN_ROD_PRESSURE_FALLBACK:{LEG_ORDER[leg]}")
        self._event_once(f"INFO_ROD_PRESSURE_FAULT_REASON:{LEG_ORDER[leg]}:{reason}", False)

    def _head_fault(self, leg: int, reason: str) -> None:
        """FAULT of the run; ``reason`` (``D1_step``, ``D1_range``, ``D1_current``,
        ``D1_nonfinite``, ``D1_stuck``) goes to ``INFO_HEAD_PRESSURE_FAULT_REASON`` (218.4)."""
        if self.head_state[leg] is HeadSensorState.FAULT:
            return
        self.head_state[leg] = HeadSensorState.FAULT
        self._event_once(f"FAULT_HEAD_PRESSURE:{LEG_ORDER[leg]}")
        self._event_once(f"INFO_HEAD_PRESSURE_FAULT_REASON:{LEG_ORDER[leg]}:{reason}", False)

    # --- D1, D2, D3 ---

    def _diagnose_sensors(self, t_s, head, rod, commanded, grounded, imu_input) -> None:
        head_faults = self._sensor_fault_reasons(head)
        rod_faults = self._sensor_fault_reasons(rod)
        head_steps, rod_steps = self._pressure_steps(head, rod, head_faults, rod_faults)
        step_rule = self.settings.step_rule
        if step_rule is StepRule.EXPLAINED_IMU:
            self._track_imu_slope(head, rod, commanded, imu_input,
                                  has_step=bool(head_steps or rod_steps))
        head_step_reasons = {leg: "D1_step" for leg in head_steps}
        unconfirmed_drains = self._resolve_rod_drain_holds(head, rod)
        if step_rule is not StepRule.JUMP:
            head_step_reasons = self._unexplained_head_steps(head_steps, head, rod, imu_input)
            rod_steps = self._unexplained_rod_steps(rod_steps, head, rod, commanded)
        for leg in sorted(set(head_faults) | set(head_step_reasons)):
            self._head_fault(leg, head_faults.get(leg) or head_step_reasons[leg])
        for leg in sorted(set(rod_faults) | set(rod_steps) | set(unconfirmed_drains)):
            self._fall_back(leg, "D1")
        self._stuck_history.append((np.array(head), np.array(rod)))
        for name, legs in self._stuck_legs().items():
            for leg in legs:
                if name == "head":
                    self._head_fault(leg, "D1_stuck")
                else:
                    self._fall_back(leg, "D1_stuck")
        self._previous = (np.array(head), np.array(rod))
        self._previous_commanded_m_s = np.array(commanded, dtype=float)
        self._previous_imu_f_z_m_s2 = imu_input.f_z_m_s2 if imu_input.has_f_z else None
        self._check_moving(t_s, head, rod, commanded, grounded)

    def _sensor_fault_reasons(self, values: NDArray[np.float64]) -> dict[int, str]:
        """D1 per leg (ascending): ``D1_nonfinite``, ``D1_range`` (outside the range widened by
        3 sigma of the noise) or ``D1_current`` (4-20 mA signal), the first that applies."""
        settings = self.settings
        margin = 3.0 * settings.pressure_noise_std_Pa
        low, high = settings.sensor_range_Pa
        with np.errstate(invalid="ignore"):
            is_nonfinite = ~np.isfinite(values)
            is_out_of_range = (values < low - margin) | (values > high + margin)
            is_bad_current = np.zeros(LEG_COUNT, dtype=bool)
            if settings.signal_current_range_mA is not None:
                current_low, current_high = settings.signal_current_range_mA
                current = pressure_to_current_mA(values)
                is_bad_current = (current < current_low) | (current > current_high)
        reasons = {}
        for leg in range(LEG_COUNT):
            if is_nonfinite[leg]:
                reasons[leg] = "D1_nonfinite"
            elif is_out_of_range[leg]:
                reasons[leg] = "D1_range"
            elif is_bad_current[leg]:
                reasons[leg] = "D1_current"
        return reasons

    def _pressure_steps(
        self, head, rod, head_faults: list[int], rod_faults: list[int]
    ) -> tuple[list[int], list[int]]:
        """D1 step: legs whose reading changed by more than ``max_step_Pa`` since the last
        period, without the legs already faulty by range or current (head, rod)."""
        if self._previous is None:
            return [], []
        head_previous, rod_previous = self._previous
        limit = self.settings.max_step_Pa
        steps = []
        for values, previous, faults in ((head, head_previous, head_faults),
                                         (rod, rod_previous, rod_faults)):
            with np.errstate(invalid="ignore"):
                jumped = np.abs(values - previous) > limit
            steps.append([int(leg) for leg in np.flatnonzero(jumped) if leg not in faults])
        return steps[0], steps[1]

    def _unexplained_head_steps(self, legs: list[int], head, rod, imu_input) -> dict[int, str]:
        """D1' head (217.5): a step is explained when the four-leg net-force sum changed by
        less than ``explained_step_sum_ratio |dp_h| A_p`` (the load moved between legs; a
        sensor jump moves the sum by the whole step force). D1'' (218.4) uses the change of
        the IMU residual ``sum F - M_eff f_z`` against ``imu_residual_step_ratio |dp_h| A_p``
        when :meth:`_imu_residual_mass_kg` gives a mass. A non-finite sum explains none.

        Returns:
            Fault reason (``D1_step``) per unexplained leg.
        """
        if not legs:
            return {}
        head_previous, rod_previous = self._previous
        net_sum_N = self._net_sum_N(head, rod)
        previous_sum_N = self._net_sum_N(head_previous, rod_previous)
        mass_kg = self._imu_residual_mass_kg(imu_input)
        if mass_kg is not None:
            residual_change_N = abs((net_sum_N - mass_kg * imu_input.f_z_m_s2)
                                    - (previous_sum_N - mass_kg * self._previous_imu_f_z_m_s2))
            unexplained = self._judge_head_steps(legs, head, residual_change_N,
                                                 self.settings.imu_residual_step_ratio,
                                                 StepReason.IMU_RESIDUAL)
        else:
            unexplained = self._judge_head_steps(legs, head, abs(net_sum_N - previous_sum_N),
                                                 self.settings.explained_step_sum_ratio,
                                                 StepReason.LOAD_REDISTRIBUTION)
        return {leg: "D1_step" for leg in unexplained}

    def _net_sum_N(self, head, rod) -> float:
        """Four-leg net-force sum of the raw readings (no zero offsets: they cancel in a
        change, and ``M_eff`` is taken on the same sum)."""
        return float(np.sum(head * self.head_area_m2 - rod * self.annulus_area_m2))

    def _judge_head_steps(self, legs, head, change_N, ratio, reason) -> list[int]:
        """Legs whose step force times ``ratio`` does not exceed ``change_N`` (unexplained);
        the others are logged as explained by ``reason``."""
        head_previous, _ = self._previous
        unexplained = []
        for leg in legs:
            step_force_N = abs(head[leg] - head_previous[leg]) * self.head_area_m2[leg]
            if change_N < ratio * step_force_N:
                self._log_explained_step(leg, "head", reason)
            else:
                unexplained.append(leg)
        return unexplained

    def _imu_residual_mass_kg(self, imu_input: _ImuInput) -> float | None:
        """``M_eff`` when D1'' applies: rule ``explained_imu``, crawler off, a mass
        (:meth:`_imu_mass_estimate_kg`) and ``f_z`` of this and the last period. A missing
        ``f_z`` now falls back to D1' with ``WARN_D1_IMU_INPUT_MISSING`` (once, 218.15 (e));
        no gyro samples with the lever correction on warn ``WARN_D1_IMU_GYRO_MISSING`` (once)
        and use ``f_z`` uncorrected; the other cases fall back silently (no mass yet, the
        first period after a restore)."""
        if self.settings.step_rule is not StepRule.EXPLAINED_IMU:
            return None
        if not imu_input.is_crawler_lifted:
            return None
        if not imu_input.has_f_z:
            self._event_once("WARN_D1_IMU_INPUT_MISSING")
            return None
        if imu_input.is_lever_missing:
            self._event_once("WARN_D1_IMU_GYRO_MISSING")
        if self._previous_imu_f_z_m_s2 is None:
            return None
        return self._imu_mass_estimate_kg()

    def _imu_mass_estimate_kg(self) -> float | None:
        """``M_eff`` of ``imu_mass_calibration`` (dynamics R41-1); ``None`` = not available."""
        settings = self.settings
        calibration = settings.imu_mass_calibration
        if calibration is ImuMassCalibration.NOMINAL:
            nominal_kg = settings.imu_mass_nominal_kg
            return self._body_mass_kg if nominal_kg is None else float(nominal_kg)
        if calibration is ImuMassCalibration.MEDIAN:
            return self._imu_mass_kg
        return self._imu_slope_mass_kg()

    def _imu_slope_mass_kg(self) -> float | None:
        cross, square, count = self._imu_slope_sums
        settings = self.settings
        if count < settings.imu_mass_slope_min_samples or square <= 0.0:
            return None
        if math.sqrt(square / count) < settings.imu_mass_slope_min_rms_m_s2:
            return None
        return cross / square

    def _track_imu_slope(self, head, rod, commanded, imu_input, *, has_step: bool) -> None:
        """``slope``: one-period ``d sum F`` and ``d f_z`` of lifted moving periods without a
        D1 step candidate (run before ``_previous`` is overwritten)."""
        is_moving = bool(np.any(np.asarray(commanded) != 0.0))
        previous_f_z = self._previous_imu_f_z_m_s2
        if (has_step or not is_moving or not imu_input.is_crawler_lifted
                or not imu_input.has_f_z or previous_f_z is None or self._previous is None):
            return
        sum_change_N = self._net_sum_N(head, rod) - self._net_sum_N(*self._previous)
        f_change = imu_input.f_z_m_s2 - previous_f_z
        if not (math.isfinite(sum_change_N) and math.isfinite(f_change)):
            return
        cross, square, count = self._imu_slope_sums
        self._imu_slope_sums = (cross + sum_change_N * f_change, square + f_change**2,
                                count + 1)

    def _imu_input(self, f_z_m_s2, is_crawler_lifted, gyro_rad_s) -> _ImuInput:
        """D1'' inputs; with ``imu_lever_correction`` ``f_z - (alpha x r)_z``, ``alpha`` =
        (last - previous gyro partial mean) / ``imu_gyro_sample_period_s`` (P-S8-14 ⑤,
        dynamics R41-2; the centripetal term is left out). A constant gyro bias cancels in the
        difference."""
        settings = self.settings
        if f_z_m_s2 is None or not settings.imu_lever_correction:
            return _ImuInput(f_z_m_s2, is_crawler_lifted)
        gyro = None if gyro_rad_s is None else np.asarray(gyro_rad_s, dtype=float)
        if gyro is None or gyro.shape[0] < 2 or not np.all(np.isfinite(gyro[-2:, :2])):
            return _ImuInput(f_z_m_s2, is_crawler_lifted, is_lever_missing=True)
        alpha_x, alpha_y = (gyro[-1, :2] - gyro[-2, :2]) / settings.imu_gyro_sample_period_s
        arm = settings.imu_lever_arm_m or self._imu_lever_arm_m
        lever_z = float(alpha_x * arm[1] - alpha_y * arm[0])
        return _ImuInput(float(f_z_m_s2) - lever_z, is_crawler_lifted)

    def _track_imu_mass(self, head, rod, imu_input: _ImuInput, is_locked_phase: bool) -> None:
        """``median`` (218.4): the median of ``sum F / f_z`` over the READY stay, from
        ``imu_mass_min_samples`` samples on; a new stay keeps the last value until then. Runs
        after the diagnosis, so a step is judged on the mass before its own sample."""
        is_new_stay = is_locked_phase and not self._was_locked_phase
        self._was_locked_phase = is_locked_phase
        if self._imu_mass_ratios_kg is None or is_new_stay:
            window = max(1, round(IMU_MASS_WINDOW_S / self.period_s))
            self._imu_mass_ratios_kg = deque(maxlen=window)
        if not is_locked_phase or not imu_input.has_f_z or imu_input.f_z_m_s2 <= 0.0:
            return
        ratio_kg = self._net_sum_N(head, rod) / imu_input.f_z_m_s2
        if not math.isfinite(ratio_kg):
            return
        self._imu_mass_ratios_kg.append(ratio_kg)
        if len(self._imu_mass_ratios_kg) >= self.settings.imu_mass_min_samples:
            self._imu_mass_kg = float(np.median(self._imu_mass_ratios_kg))

    def _unexplained_rod_steps(self, legs: list[int], head, rod, commanded) -> list[int]:
        """D1' rod side (217.5); see :meth:`_rod_step_reason`. A fall that only
        :meth:`_is_rod_draining` explains is held for the next period (P-S8-21), not
        returned."""
        command_before = self._previous_commanded_m_s
        if command_before is None:
            command_before = commanded
        unexplained = []
        for leg in legs:
            reason = self._rod_step_reason(leg, head, rod, commanded, command_before)
            if reason is not None:
                self._log_explained_step(leg, "rod", reason)
            elif self._is_rod_draining(leg, head, rod, commanded, command_before):
                self._rod_drain_held_Pa[leg] = float(rod[leg])
            else:
                unexplained.append(leg)
        return unexplained

    def _is_rod_draining(self, leg, head, rod, commanded, command_before) -> bool:
        """P-S8-21 ① (260.5): the rod side fell, a positive command this or the last period
        opened the check, and the new reading is still above the D2 extend range ``p_hi``
        (the CB law bound with the counterbalance): the trapped lift-off pressure draining
        to return, sampled before it settles. Off with ``rod_drain_hold_ratio = None``."""
        if self.settings.rod_drain_hold_ratio is None:
            return False
        _, rod_previous = self._previous
        is_falling = rod[leg] < rod_previous[leg]
        is_check_opened = commanded[leg] > 0.0 or command_before[leg] > 0.0
        _, high_Pa = self._extend_rod_range_Pa(head[leg])
        return bool(is_falling and is_check_opened and rod[leg] > high_Pa)

    def _resolve_rod_drain_holds(self, head, rod) -> list[int]:
        """P-S8-21 ②: a leg held last period is ``INFO_PRESSURE_STEP:<leg>:rod:check_draining``
        when :meth:`_is_drain_confirmed`, else a D1 fallback now
        (one period later than without the hold). Every hold ends here.

        Returns:
            The held legs whose drain this reading does not confirm.
        """
        held = self._rod_drain_held_Pa
        if held is None:  # a monitor pickled before P-S8-21
            self._rod_drain_held_Pa = [None] * LEG_COUNT
            return []
        unconfirmed = []
        for leg, held_Pa in enumerate(held):
            if held_Pa is None:
                continue
            held[leg] = None
            if self._is_drain_confirmed(leg, head, rod, held_Pa):
                self._log_explained_step(leg, "rod", StepReason.CHECK_DRAINING)
            else:
                unconfirmed.append(leg)
        return unconfirmed

    def _is_drain_confirmed(self, leg, head, rod, held_Pa: float) -> bool:
        """Excess form of spec rev. 55 268.3 #2 (R-2): ``p_k+1 <= p_hi + rho (p_k - p_hi)``,
        ``p_hi`` the D2 extend upper bound of :meth:`_extend_rod_range_Pa` (R-4) at this
        period's head reading. The lower bound ``p_lo`` is ours (ASSUMPTION: the spec names
        only the upper one; a reading that drops below the extend range is no drain)."""
        ratio = self.settings.rod_drain_hold_ratio or 0.0
        low_Pa, high_Pa = self._extend_rod_range_Pa(head[leg])
        return bool(low_Pa <= rod[leg] <= high_Pa + ratio * (held_Pa - high_Pa))

    def _rod_step_reason(self, leg, head, rod, commanded, command_before) -> StepReason | None:
        """Rise: the leg is locked (command zero this and the last period) and the head fell
        in the same period, the lock law of a fast load loss. Fall: a positive command this or
        the last period (pilot check opened) and the new reading lies in the D2 extend range,
        the trapped rod side draining to return; D1'' also :meth:`_is_lock_load_regain`.
        Otherwise ``None`` (a sensor jump)."""
        head_previous, rod_previous = self._previous
        rod_change_Pa = rod[leg] - rod_previous[leg]
        is_locked = commanded[leg] == 0.0 and command_before[leg] == 0.0
        if rod_change_Pa > 0.0 and is_locked and head[leg] < head_previous[leg]:
            return StepReason.LOCK_LOAD_LOSS
        is_check_opened = commanded[leg] > 0.0 or command_before[leg] > 0.0
        low_Pa, high_Pa = self._extend_rod_range_Pa(head[leg])
        if rod_change_Pa < 0.0 and is_check_opened and low_Pa <= rod[leg] <= high_Pa:
            return StepReason.CHECK_OPENED
        is_imu_rule = self.settings.step_rule is StepRule.EXPLAINED_IMU
        if rod_change_Pa < 0.0 and is_imu_rule and self._is_lock_load_regain(leg, head, rod):
            return StepReason.LOCK_LOAD_REGAIN
        return None

    def _is_lock_load_regain(self, leg, head, rod) -> bool:
        """218.4 ②: the head rose in the same period, the stroke reading moved by at most
        ``regain_stroke_change_max_m`` and ``-dp_r / dp_h <= regain_ratio_margin R_ub(s)``
        (``R_ub`` of P-S8-13 ① at this period's stroke reading). No stroke reading: no."""
        head_previous, rod_previous = self._previous
        head_rise_Pa = head[leg] - head_previous[leg]
        stroke_rate = self._stroke_rate_m_s
        if not head_rise_Pa > 0.0 or stroke_rate is None or self._previous_stroke_m is None:
            return False
        stroke_m = float(self._previous_stroke_m[leg])  # this period's reading
        stroke_change_m = abs(float(stroke_rate[leg])) * self.period_s
        if not (math.isfinite(stroke_m) and math.isfinite(stroke_change_m)):
            return False
        settings = self.settings
        if stroke_change_m > settings.regain_stroke_change_max_m:
            return False
        ratio = -(rod[leg] - rod_previous[leg]) / head_rise_Pa
        return ratio <= settings.regain_ratio_margin * self._ratio_bound(leg, stroke_m)

    def _log_explained_step(self, leg: int, sensor: str, reason: StepReason) -> None:
        """Every explained step is recorded (not once per run): it is information, no fault."""
        self._events.append((f"INFO_PRESSURE_STEP:{LEG_ORDER[leg]}:{sensor}:{reason}", False))

    def _stuck_legs(self) -> dict[str, list[int]]:
        """D1 stuck: a reading that did not change at all over the window (noise > 0 only)."""
        history = self._stuck_history
        if self.settings.pressure_noise_std_Pa <= 0.0 or len(history) < history.maxlen:
            return {}
        out = {}
        for index, name in ((0, "head"), (1, "rod")):
            samples = np.array([entry[index] for entry in history])
            with np.errstate(invalid="ignore"):
                spread = np.ptp(samples, axis=0)
            out[name] = [int(leg) for leg in np.flatnonzero(spread == 0.0)]
        return out

    def _check_moving(self, t_s, head, rod, commanded, grounded) -> None:
        """D2 (extend) and D3 (retract) on a grounded leg moving for the settle time; D2 not
        within ``reversal_exclusion_s`` of a retraction (R-H5)."""
        settings = self.settings
        for leg in range(LEG_COUNT):
            watch = self._legs[leg]
            sign = self._moving_sign(commanded[leg], settings.moving_speed_fraction)
            if commanded[leg] < 0.0:
                watch.last_retract_t_s = float(t_s)
            if sign != watch.moving_sign:
                watch.moving_sign, watch.moving_since_s = sign, (t_s if sign else None)
                watch.violation_since_s = None
            if not sign or not grounded[leg]:
                continue
            if t_s - watch.moving_since_s < settings.moving_settle_s - 1e-9:
                continue
            after_retract_s = t_s - watch.last_retract_t_s
            if sign > 0 and after_retract_s < settings.reversal_exclusion_s - 1e-9:
                continue
            if settings.moving_stroke_check and not self._is_stroke_moving(leg, sign):
                watch.violation_since_s = None
                continue
            is_violation = self._moving_violation(sign, head[leg], rod[leg])
            if is_violation is None:
                continue
            if not is_violation:
                watch.violation_since_s = None
                continue
            if watch.violation_since_s is None:
                watch.violation_since_s = t_s
            if t_s - watch.violation_since_s >= settings.violation_hold_s - 1e-9:
                self._fall_back(leg, "D2" if sign > 0 else "D3")

    def _moving_sign(self, command_m_s: float, fraction: float) -> float:
        if abs(command_m_s) < fraction * self.max_speed_m_s:
            return 0.0
        return math.copysign(1.0, command_m_s)

    def _moving_violation(self, sign: float, head_Pa: float, rod_Pa: float) -> bool | None:
        """``None`` when the check does not apply."""
        settings = self.settings
        if not math.isfinite(rod_Pa) or head_Pa < settings.extend_min_head_Pa:
            return None
        if sign > 0:
            low, high = self._extend_rod_range_Pa(head_Pa)
            return not low <= rod_Pa <= high
        if not settings.retract_check:
            return None
        threshold = (settings.retract_head_back_Pa
                     + (head_Pa - settings.retract_head_back_Pa) / settings.retract_pilot_ratio
                     + settings.retract_cracking_Pa)
        return not 0.5 * threshold <= rod_Pa <= settings.retract_upper_Pa

    def _extend_rod_range_Pa(self, head_Pa: float) -> tuple[float, float]:
        """D2 rod-side range of an extending leg: ``extend_rod_range_Pa`` (pilot check), with
        the upper bound ``max(high, CB law) + counterbalance_rod_margin_Pa`` (CB, H-S8-1 9.5)."""
        settings = self.settings
        low, high = settings.extend_rod_range_Pa
        if settings.counterbalance is not None:
            law_Pa = settings.counterbalance.extend_rod_pressure_Pa(head_Pa)
            high = max(high, law_Pa) + settings.counterbalance_rod_margin_Pa
        return low, high

    def _update_stroke_rate(self, stroke_m: ArrayLike | None) -> None:
        if stroke_m is None:
            self._previous_stroke_m = None
            self._stroke_rate_m_s = None
            return
        stroke = np.array(stroke_m, dtype=float)
        if self._previous_stroke_m is not None:
            self._stroke_rate_m_s = (stroke - self._previous_stroke_m) / self.period_s
        self._previous_stroke_m = stroke

    def _is_stroke_moving(self, leg: int, sign: float) -> bool:
        """P-S8-11 ③: the measured stroke moved in the commanded direction fast enough."""
        rate = self._stroke_rate_m_s
        if rate is None or not math.isfinite(rate[leg]):
            return False
        threshold = self.settings.moving_stroke_speed_fraction * self.max_speed_m_s
        return sign * rate[leg] >= threshold

    # --- fallback estimate (53.3) ---

    def _update_rod_estimates(self, t_s, head, rod, commanded, stroke_m=None) -> None:
        """Model upper bound ``p_r_hat`` of every leg (used on fallback legs only)."""
        if self.settings.locked_ratio_rule is LockedRatioRule.FIXED:
            self._update_fixed_ratio_estimates(head, commanded)
            return
        stroke = (np.full(LEG_COUNT, np.nan) if stroke_m is None
                  else np.asarray(stroke_m, dtype=float))
        for leg in range(LEG_COUNT):
            self._update_column_bound(leg, float(t_s), float(head[leg]), float(rod[leg]),
                                      float(commanded[leg]), float(stroke[leg]))

    def _update_fixed_ratio_estimates(self, head, commanded) -> None:
        """The estimate before P-S8-13 (``locked_ratio_rule = "fixed"``): the moving value of
        the last moving sample, plus ``fallback_locked_ratio`` times the head drop from the
        first command-free sample."""
        settings = self.settings
        for leg in range(LEG_COUNT):
            watch = self._legs[leg]
            command = commanded[leg]
            if command > 0.0:
                watch.rod_estimate_Pa = self._extend_rod_estimate_Pa(
                    head[leg], settings.fallback_extend_Pa)
                watch.lock_rod_estimate_Pa = None
            elif command < 0.0:
                watch.rod_estimate_Pa = self._retract_rod_estimate_Pa(head[leg])
                watch.lock_rod_estimate_Pa = None
            else:
                if watch.lock_rod_estimate_Pa is None:
                    watch.lock_rod_estimate_Pa = watch.rod_estimate_Pa
                    watch.lock_head_Pa = float(head[leg])
                head_drop = max(0.0, watch.lock_head_Pa - float(head[leg]))
                watch.rod_estimate_Pa = (watch.lock_rod_estimate_Pa
                                         + settings.fallback_locked_ratio[leg] * head_drop)

    # --- column-bound fallback estimate (P-S8-13, hydraulics H-S8-2 10.4) ---

    def _stretch_states(self) -> list[_LockStretch]:
        """The per-leg state; a monitor pickled before P-S8-13 gets one with an unknown last
        direction (its first stretch takes the larger start of both directions)."""
        if self._lock_stretches is None:
            self._lock_stretches = [_LockStretch(last_sign=0.0) for _ in range(LEG_COUNT)]
        return self._lock_stretches

    def _update_column_bound(self, leg, t_s, head_Pa, rod_Pa, command_m_s, stroke_m) -> None:
        """10.4 ①-⑥ for one leg and period.

        Moving (command != 0): the moving model (pilot extend ``locked_start_extend_Pa``) and
        its start value are kept for the lookback. Command-free: the samples of the lock
        window are lock-instant candidates ``(M_j, p_h,j)``; ``p_r_hat`` is the larger of the
        model bound ``max_j [M_j + R_ub (p_h,j - p_h)^+]`` and the reading bound
        ``p_r,read(k_v) + R_ub (H_v - p_h)^+`` (no lift-off cap, ⑥).
        """
        watch, stretch = self._legs[leg], self._stretch_states()[leg]
        if command_m_s != 0.0:
            self._close_lock_stretch(leg, stretch)
            if self._uses_cb_lag_bound:
                # P-S8-15: the start value M of the lookback is the lag bound itself (⑤).
                moving_Pa = self._cb_lag_bound_estimate_Pa(
                    stretch, head_Pa, command_m_s, watch.rod_estimate_Pa)
                self._track_moving_leg(leg, stretch, t_s, head_Pa, command_m_s, moving_Pa)
            else:
                self._track_moving_leg(leg, stretch, t_s, head_Pa, command_m_s)
                moving_Pa = self._moving_rod_estimate_Pa(leg, stretch.last_sign, head_Pa)
            watch.rod_estimate_Pa = moving_Pa
            watch.lock_rod_estimate_Pa = None
        else:
            stretch.lag_bound_Pa = math.nan
            if not stretch.is_open:
                self._open_lock_stretch(leg, stretch, t_s)
            if t_s < stretch.window_end_s - 1e-9 or not stretch.candidates:
                self._add_lock_candidate(leg, stretch, head_Pa, stroke_m)
            self._track_valid_reading(leg, stretch, t_s, head_Pa, rod_Pa, stroke_m)
            if self._is_tracking_online_ratio:
                self._track_online_ratio(leg, stretch, t_s, head_Pa, rod_Pa, stroke_m)
            watch.rod_estimate_Pa = self._locked_upper_bound_Pa(leg, stretch, head_Pa)
        self._remember_command(stretch, head_Pa, command_m_s)

    def _track_moving_leg(self, leg, stretch, t_s, head_Pa, command_m_s,
                          start_Pa: float | None = None) -> None:
        """Keep the moving start value of the lookback (③): ``start_Pa``, or the moving model
        of the new direction at this head."""
        stretch.last_sign = math.copysign(1.0, command_m_s)
        stretch.last_command_m_s = command_m_s
        if start_Pa is None:
            start_Pa = self._lock_start_model_Pa(leg, stretch.last_sign, head_Pa)
        history = stretch.moving_starts
        history.append((t_s, start_Pa))
        lookback_start_s = t_s - self.settings.locked_start_lookback_s - self.period_s
        while history and history[0][0] < lookback_start_s:
            history.popleft()

    # --- CB moving estimate (P-S8-15, hydraulics 11.2) ---

    @property
    def _uses_cb_lag_bound(self) -> bool:
        """The CB lag bound applies (counterbalance, ``lag_bound``, column-bound rule)."""
        settings = self.settings
        return (settings.counterbalance is not None
                and settings.counterbalance_moving_rule is CbMovingRule.LAG_BOUND
                and settings.locked_ratio_rule is LockedRatioRule.COLUMN_BOUND)

    @property
    def _direction_unsure_periods(self) -> int:
        """③ ``N_rev = ceil(tau_v ln(1 / 0.05) / T)`` (3 at ``tau_v`` 0.1 s, T 0.1 s)."""
        decay_s = self.settings.lock_window_valve_tau_s * math.log(
            1.0 / CB_DIRECTION_SETTLED_FRACTION)
        return math.ceil(decay_s / self.period_s - 1e-9)

    def _remember_command(self, stretch, head_Pa: float, command_m_s: float) -> None:
        count = self._direction_unsure_periods
        recent = (*stretch.recent_commands_m_s, command_m_s)
        stretch.recent_commands_m_s = recent[-count:] if count > 0 else ()
        stretch.previous_head_Pa = head_Pa

    def _is_direction_unsure(self, stretch, sign: float) -> bool:
        """③: an applied command of the last ``N_rev`` periods had the other sign or was zero
        (a period not yet seen, after a restore or at the run start, counts as zero)."""
        count = self._direction_unsure_periods
        if count <= 0:
            return False
        recent = stretch.recent_commands_m_s
        if len(recent) < count:
            return True
        return any(command * sign <= 0.0 for command in recent[-count:])

    def _cb_laws_Pa(self, head_Pa: float, sign: float, is_unsure: bool) -> tuple[float, float]:
        """(``L``, margin) at ``head_Pa``: the law of the direction and its margin, or while
        the direction is uncertain the larger law with the larger margin (④). The margin of
        the larger law alone is not a bound: with the retract law larger, a plant still
        extending reads up to ``ext + psi e_h`` = ``ext + 11.4 bar``, above ``ret + 1.2``."""
        settings = self.settings
        model = settings.counterbalance
        extend_Pa = model.extend_rod_pressure_Pa(head_Pa)
        retract_Pa = model.retract_rod_pressure_Pa(head_Pa)
        extend_margin_Pa = settings.counterbalance_extend_estimate_margin_Pa
        retract_margin_Pa = settings.counterbalance_retract_estimate_margin_Pa
        if is_unsure:
            return max(extend_Pa, retract_Pa), max(extend_margin_Pa, retract_margin_Pa)
        if sign > 0.0:
            return extend_Pa, extend_margin_Pa
        return retract_Pa, retract_margin_Pa

    def _cb_lag_bound_estimate_Pa(self, stretch, head_Pa, command_m_s,
                                  previous_estimate_Pa) -> float:
        """① R4D ``Y_k = max(L_k, a Y_k-1 + (1 - a) max(L_k-1, L_k))``, ``a = e^(-T / tau_cb)``,
        plus the margin. ② The first moving sample starts from the last period's ``p_r_hat``
        (the locked upper bound) and the law at the last head reading."""
        sign = math.copysign(1.0, command_m_s)
        is_unsure = self._is_direction_unsure(stretch, sign)
        law_Pa, margin_Pa = self._cb_laws_Pa(head_Pa, sign, is_unsure)
        if math.isnan(stretch.lag_bound_Pa):
            stretch.lag_bound_Pa = previous_estimate_Pa
            previous_head_Pa = stretch.previous_head_Pa
            stretch.lag_law_Pa = (law_Pa if not math.isfinite(previous_head_Pa)
                                  else self._cb_laws_Pa(previous_head_Pa, sign, is_unsure)[0])
        tau_s = self._cb_lag_tau_s
        decay = math.exp(-self.period_s / tau_s) if tau_s > 0.0 else 0.0
        top_Pa = max(stretch.lag_law_Pa, law_Pa)
        stretch.lag_bound_Pa = max(law_Pa, decay * stretch.lag_bound_Pa + (1.0 - decay) * top_Pa)
        stretch.lag_law_Pa = law_Pa
        return stretch.lag_bound_Pa + margin_Pa

    def _open_lock_stretch(self, leg, stretch, t_s) -> None:
        """``k0``: the window ``W = tau_v ln(max(|u_last|, eps) / eps) + T`` (10.4 ②) and the
        largest moving start value of the lookback (③)."""
        settings = self.settings
        eps = settings.lock_window_eps_m_s
        decay_s = settings.lock_window_valve_tau_s * math.log(
            max(abs(stretch.last_command_m_s), eps) / eps)
        lookback_start_s = t_s - settings.locked_start_lookback_s - 1e-9
        recent = [value for sample_t_s, value in stretch.moving_starts
                  if sample_t_s >= lookback_start_s]
        stretch.is_open = True
        stretch.start_t_s = t_s
        stretch.window_end_s = t_s + decay_s + self.period_s
        stretch.previous_moving_max_Pa = max(recent, default=-math.inf)
        stretch.candidates = []
        stretch.stroke_window_max_m = -math.inf
        stretch.valid_rod_Pa = None
        stretch.valid_head_max_Pa = -math.inf
        stretch.valid_stroke_m = -math.inf
        stretch.online_reference = None
        self._seed_from_old_anchor(leg, stretch)

    def _seed_from_old_anchor(self, leg, stretch) -> None:
        """A monitor pickled before P-S8-13 inside a stretch keeps its old lock anchor as one
        more candidate (its own direction is unknown)."""
        watch = self._legs[leg]
        if stretch.last_sign != 0.0 or watch.lock_rod_estimate_Pa is None:
            return
        if watch.lock_head_Pa is not None:
            stretch.candidates.append((watch.lock_rod_estimate_Pa, watch.lock_head_Pa))

    def _close_lock_stretch(self, leg, stretch) -> None:
        if not stretch.is_open:
            return
        stretch.is_open = False
        if self.rod_state[leg] is RodSensorState.FALLBACK:
            if self._fallback_lock_log is None:
                self._fallback_lock_log = []
            self._fallback_lock_log.append(stretch.summary(leg))

    def _add_lock_candidate(self, leg, stretch, head_Pa, stroke_m) -> None:
        start_Pa = max(self._lock_start_model_Pa(leg, stretch.last_sign, head_Pa),
                       stretch.previous_moving_max_Pa)
        stretch.candidates.append((start_Pa, head_Pa))
        if math.isfinite(stroke_m):
            stretch.stroke_window_max_m = max(stretch.stroke_window_max_m, stroke_m)

    def _track_valid_reading(self, leg, stretch, t_s, head_Pa, rod_Pa, stroke_m) -> None:
        """⑤: ``k_v`` is the newest sample with the rod sensor not fallen back (after D1-D3 of
        this period); ``H_v`` adds the window heads after it."""
        is_valid = (self.rod_state[leg] is RodSensorState.OK and math.isfinite(rod_Pa)
                    and math.isfinite(head_Pa))
        if is_valid:
            stretch.valid_rod_Pa = rod_Pa
            stretch.valid_head_max_Pa = head_Pa
            stretch.valid_stroke_m = stroke_m if math.isfinite(stroke_m) else -math.inf
        elif stretch.valid_rod_Pa is not None and t_s < stretch.window_end_s - 1e-9:
            stretch.valid_head_max_Pa = max(stretch.valid_head_max_Pa, head_Pa)

    def _locked_upper_bound_Pa(self, leg, stretch, head_Pa) -> float:
        """④ model bound and ⑤ reading bound, the larger one; the meta fields follow it."""
        ratio = self._level_ratio(leg, self._ratio_bound(leg, stretch.stroke_window_max_m))
        best_Pa, best_start_Pa, best_head_Pa = -math.inf, math.nan, math.nan
        for start_Pa, candidate_head_Pa in stretch.candidates:
            bound_Pa = start_Pa + ratio * max(candidate_head_Pa - head_Pa, 0.0)
            if bound_Pa > best_Pa:
                best_Pa, best_start_Pa, best_head_Pa = bound_Pa, start_Pa, candidate_head_Pa
        stretch.ratio_bound = ratio
        stretch.ratio_stroke_m = stretch.stroke_window_max_m
        stretch.estimate_source = EstimateSource.MODEL
        if stretch.valid_rod_Pa is not None:
            reading_stroke_m = max(stretch.stroke_window_max_m, stretch.valid_stroke_m)
            reading_ratio = self._level_ratio(leg, self._ratio_bound(leg, reading_stroke_m))
            reading_Pa = stretch.valid_rod_Pa + reading_ratio * max(
                stretch.valid_head_max_Pa - head_Pa, 0.0)
            if reading_Pa > best_Pa:
                best_Pa = reading_Pa
                best_start_Pa, best_head_Pa = stretch.valid_rod_Pa, stretch.valid_head_max_Pa
                stretch.ratio_bound = reading_ratio
                stretch.ratio_stroke_m = reading_stroke_m
                stretch.estimate_source = EstimateSource.READING
        stretch.start_Pa, stretch.anchor_head_Pa = best_start_Pa, best_head_Pa
        return best_Pa

    def _ratio_bound(self, leg: int, stroke_m: float) -> float:
        """① ``R_ub = kappa (L_0h,max + s') / (L_0r,min + s_max - s')``,
        ``s' = min(s + ds, s_max - 1 mm)`` (not below 0); without a stroke reading
        ``s' = s_max - 1 mm`` (in effect a lift-off assumption) and a warning on a fallback
        leg."""
        settings = self.settings
        stroke_max_m = self._column_stroke_max_m
        end_m = stroke_max_m - LOCKED_RATIO_STROKE_END_GAP_M
        if math.isfinite(stroke_m):
            bound_stroke_m = min(max(stroke_m + settings.locked_ratio_stroke_margin_m, 0.0),
                                 end_m)
        else:
            bound_stroke_m = end_m
            if self.rod_state[leg] is RodSensorState.FALLBACK:
                self._event_once(f"WARN_FALLBACK_LOCK_STROKE_UNKNOWN:{LEG_ORDER[leg]}")
        head_column_m = settings.locked_ratio_head_dead_max_m + bound_stroke_m
        rod_column_m = settings.locked_ratio_rod_dead_min_m + stroke_max_m - bound_stroke_m
        return settings.locked_ratio_kappa * head_column_m / rod_column_m

    # --- R-5 fallback slope (P-S8-22, spec rev. 61 302, 304 ② / ④) ---

    def _plant_ratio(self, leg: int) -> float:
        """``R_plant``: the plant meta ratio of the choice, else ``fallback_locked_ratio``."""
        plant_ratio = self._r5_ratio_choice.plant_ratio
        if plant_ratio is None:
            return self.settings.fallback_locked_ratio[leg]
        return plant_ratio[leg]

    def _level_ratio(self, leg: int, column_ratio: float) -> float:
        """302.6 (L1 runs, ``plant_meta`` only): ``R_lvl = max(R_ub, kappa R_plant)``, so that a
        short lock stroke (``R_ub`` below the fixed L1-R ratio) keeps the level bound."""
        choice = self._r5_ratio_choice
        if choice is None or choice.source is not FallbackRatioSource.PLANT_META:
            return column_ratio
        return max(column_ratio, self.settings.locked_ratio_kappa * self._plant_ratio(leg))

    def _high_ratio(self, leg: int, stroke_m: float) -> float:
        """``R_hi`` (302.4): the fixed L1 setting (at least the plant ratio) for ``plant_meta``,
        else the worst-case column ratio ``R_ub(s) / kappa``."""
        if self._r5_ratio_choice.source is FallbackRatioSource.PLANT_META:
            return max(self.settings.fallback_locked_ratio[leg], self._plant_ratio(leg))
        return self._ratio_bound(leg, stroke_m) / self.settings.locked_ratio_kappa

    def _nominal_ratio(self, stroke_m: float) -> float:
        """``R_nom(s) = (L_0h + s) / (L_0r + s_max - s)`` at the stroke reading itself (no
        5 mm margin: 302.5 reproduces 7.77 / 7.84 that way), ``s`` cut to ``[0, s_max]``."""
        choice = self._r5_ratio_choice
        stroke_max_m = self._column_stroke_max_m
        stroke = min(max(stroke_m, 0.0), stroke_max_m)
        return ((choice.nominal_head_dead_m + stroke)
                / (choice.nominal_rod_dead_m + stroke_max_m - stroke))

    def _rate_ratio(self, leg: int, stroke_m: float, high_ratio: float) -> float:
        """``R_rate`` (302.4), cut to ``[0, R_hi]``. ASSUMPTION: without a stroke reading
        ``R_rate = R_hi`` (no nominal relief; the soundness does not depend on it)."""
        source = self._r5_ratio_choice.source
        if source is FallbackRatioSource.PLANT_META or not math.isfinite(stroke_m):
            return high_ratio
        rate_ratio = self._nominal_ratio(stroke_m)
        if source is FallbackRatioSource.ONLINE:
            online_ratio = self._online_ratios[leg] if self._online_ratios else None
            if online_ratio is None:
                self._event_once(f"WARN_R5_ONLINE_RATIO_MISSING:{LEG_ORDER[leg]}")
            else:
                rate_ratio = online_ratio
        return min(max(rate_ratio, 0.0), high_ratio)

    @property
    def _is_tracking_online_ratio(self) -> bool:
        choice = self._r5_ratio_choice
        return choice is not None and choice.source is FallbackRatioSource.ONLINE

    def _track_online_ratio(self, leg, stretch, t_s, head_Pa, rod_Pa, stroke_m) -> None:
        """④ ``R_hat = -dp_r / dp_h`` against the first two-sensor sample after the lock window
        (ASSUMPTION: the window keeps the valve-closing samples out), once the head moved
        at least 5 bar with the stroke within 5 mm; the last value is kept per leg and is
        no longer updated after the leg falls back."""
        is_valid = (self.rod_state[leg] is RodSensorState.OK and math.isfinite(rod_Pa)
                    and math.isfinite(head_Pa) and math.isfinite(stroke_m))
        if not is_valid or t_s < stretch.window_end_s - 1e-9:
            return
        reference = stretch.online_reference
        if reference is None:
            stretch.online_reference = (head_Pa, rod_Pa, stroke_m)
            return
        reference_head_Pa, reference_rod_Pa, reference_stroke_m = reference
        head_change_Pa = head_Pa - reference_head_Pa
        if abs(head_change_Pa) < ONLINE_RATIO_MIN_HEAD_CHANGE_PA:
            return
        if abs(stroke_m - reference_stroke_m) > ONLINE_RATIO_MAX_STROKE_CHANGE_M:
            return
        if self._online_ratios is None:
            self._online_ratios = [None] * LEG_COUNT
        self._online_ratios[leg] = -(rod_Pa - reference_rod_Pa) / head_change_Pa

    def _update_r5_inputs(self, choice: FallbackRatioChoice) -> None:
        if (not self.settings.diagnostics
                or self.settings.locked_ratio_rule is not LockedRatioRule.COLUMN_BOUND):
            return
        for leg in self.fallback_legs:
            self._r5_inputs[leg] = self._r5_inputs_of_leg(leg, choice.rate_intervals)

    def _r5_inputs_of_leg(self, leg: int, rate_intervals: int) -> FallbackSlopeInputs | None:
        """302.2 conditions 2 and 3 for a fallback leg, then the inputs of 302.1."""
        history = self._history
        stretch = self._stretch_states()[leg]
        if len(history) < rate_intervals + 1 or not stretch.is_open:
            return None
        t_now_s, _, head_now = history[-1]
        t_old_s, _, head_old = history[-1 - rate_intervals]
        is_consecutive = abs(t_now_s - t_old_s - rate_intervals * self.period_s) < (
            0.5 * self.period_s)
        if not is_consecutive or stretch.start_t_s > t_old_s + 1e-9:
            return None
        if not (math.isfinite(stretch.anchor_head_Pa) and math.isfinite(stretch.ratio_bound)):
            return None
        head_Pa = float(head_now[leg])
        stroke_m = stretch.ratio_stroke_m
        high_ratio = self._high_ratio(leg, stroke_m)
        return FallbackSlopeInputs(
            head_drop_Pa=float(head_old[leg]) - head_Pa,
            depth_Pa=max(stretch.anchor_head_Pa - head_Pa, 0.0),
            level_ratio=stretch.ratio_bound,
            high_ratio=high_ratio,
            rate_ratio=self._rate_ratio(leg, stroke_m, high_ratio),
            head_area_m2=float(self.head_area_m2[leg]),
            annulus_area_m2=float(self.annulus_area_m2[leg]),
        )

    def _moving_rod_estimate_Pa(self, leg: int, sign: float, head_Pa: float) -> float:
        """``p_r_hat`` of a moving leg: unchanged but for the pilot extend value (10.4 ③)."""
        if sign > 0.0:
            return self._extend_rod_estimate_Pa(head_Pa, self.settings.locked_start_extend_Pa)
        return self._retract_rod_estimate_Pa(head_Pa)

    def _lock_start_model_Pa(self, leg: int, sign: float, head_Pa: float) -> float:
        """③ start value ``M`` of a lock after a move in direction ``sign``: the moving
        estimate, after a pilot-check retraction at least the plant's
        ``p_r0_after_retract``; ``sign`` 0 (unknown) takes the larger of both."""
        if sign == 0.0:
            return max(self._lock_start_model_Pa(leg, 1.0, head_Pa),
                       self._lock_start_model_Pa(leg, -1.0, head_Pa))
        moving_Pa = self._moving_rod_estimate_Pa(leg, sign, head_Pa)
        if sign < 0.0 and self.settings.counterbalance is None:
            return max(moving_Pa, self._retract_lock_floor_Pa[leg])
        return moving_Pa

    def _fallback_lock_meta(self) -> dict[str, Any]:
        """10.4 ⑦: the current stretch of every fallback leg and the closed ones (column bound
        only; nothing for the fixed rule)."""
        if self.settings.locked_ratio_rule is LockedRatioRule.FIXED:
            return {}
        stretches = self._lock_stretches or []
        current = [stretch.summary(leg) for leg, stretch in enumerate(stretches)
                   if stretch.is_open and self.rod_state[leg] is RodSensorState.FALLBACK]
        return {"fallback_lock_stroke_max_m": self._column_stroke_max_m,
                "fallback_lock_retract_floor_Pa": list(self._retract_lock_floor_Pa),
                "fallback_lock_current": current,
                "fallback_lock_log": list(self._fallback_lock_log or [])}

    def _extend_rod_estimate_Pa(self, head_Pa: float, pilot_extend_Pa: float) -> float:
        """``p_r_hat`` while extending (any positive command): ``pilot_extend_Pa`` (pilot
        check: return back pressure), or the CB law plus its upper-bound share
        (counterbalance, H-S8-1 9.6)."""
        settings = self.settings
        model = settings.counterbalance
        if model is None:
            return pilot_extend_Pa
        return (model.extend_rod_pressure_Pa(head_Pa)
                + settings.counterbalance_extend_estimate_margin_Pa)

    def _retract_rod_estimate_Pa(self, head_Pa: float) -> float:
        """``p_r_hat`` while retracting: pilot threshold of the check (pilot check), or the CB
        law plus its upper-bound share (counterbalance, 9.6)."""
        settings = self.settings
        model = settings.counterbalance
        if model is not None:
            return (model.retract_rod_pressure_Pa(head_Pa)
                    + settings.counterbalance_retract_estimate_margin_Pa)
        back = settings.fallback_head_back_Pa
        return (back + (head_Pa - back) / settings.fallback_pilot_ratio
                + settings.fallback_cracking_Pa)

    def _forces(self, head, rod, head_only) -> PressureForces:
        net = head_only - rod * self.annulus_area_m2
        fallback = np.zeros(LEG_COUNT, dtype=bool)
        fallback[self.fallback_legs] = True
        if not fallback.any():
            return self._corrected(PressureForces(net, net, net, head_only))
        forces = self._fallback_forces(fallback, head_only, net)
        cap_N = self.settings.fallback_lower_deficit_cap_N
        if cap_N is None:
            return forces
        capped_lower = np.where(fallback, np.maximum(forces.lower, self.F_min_N - cap_N),
                                forces.lower)
        return replace(forces, lower=capped_lower)

    def _fallback_forces(self, fallback, head_only, net) -> PressureForces:
        estimate = np.array([watch.rod_estimate_Pa for watch in self._legs])
        nominal = np.where(fallback, head_only, net)
        upper = np.where(
            fallback, head_only - self.settings.fallback_floor_Pa * self.annulus_area_m2, net)
        if not self._has_offset_allowance:
            lower = np.where(fallback, head_only - estimate * self.annulus_area_m2, net)
            return self._corrected(PressureForces(nominal, lower, upper, head_only))
        # 76.2: only the larger of the fallback bound and the E-6 allowance is deducted.
        fallback_bound = np.where(fallback, estimate * self.annulus_area_m2, 0.0)
        deduction = np.maximum(fallback_bound, self.offset_allowance_N)
        offsets = self.zero_offsets_N
        return PressureForces(
            nominal - offsets, nominal - offsets - deduction, upper - offsets, head_only
        )

    @property
    def _has_zero_offsets(self) -> bool:
        return bool(np.any(self.zero_offsets_N != 0.0))

    @property
    def _has_offset_allowance(self) -> bool:
        return bool(np.any(self.offset_allowance_N != 0.0))

    def _corrected(self, forces: PressureForces) -> PressureForces:
        """E-3 offsets off every reading but ``head_only``, E-6 allowance off ``lower``.

        Without offsets and allowance the readings pass unchanged (same arrays), so the
        uncalibrated runs stay bit for bit."""
        if not (self._has_zero_offsets or self._has_offset_allowance):
            return forces
        offsets = self.zero_offsets_N
        nominal = forces.nominal - offsets
        lower = forces.lower - offsets - self.offset_allowance_N
        upper = forces.upper - offsets
        return PressureForces(nominal, lower, upper, forces.head_only)

    # --- locked checks: D4, D5, rod-side watch, Delta F1 ---

    def _check_locked(self, t_s, rod, forces, is_locked_phase, seal_band_N) -> None:
        if not is_locked_phase:
            self._ready_history.clear()
            for watch in self._legs:
                watch.load_drop_since_s = None
                watch.d4_violation_samples = 0
            return
        self._check_physical_lower_bound(forces.nominal, seal_band_N)
        self._watch_rod_side(rod, forces.nominal)
        self._ready_history.append((np.array(rod), np.array(forces.nominal)))
        self._watch_rising_rod_pressure()
        if self.is_load_watch_open:
            self._watch_load_changes(t_s, forces.nominal, seal_band_N)
            return
        for watch in self._legs:
            watch.load_drop_since_s = None
        if self._baseline is not None:
            self._baseline.sum_mismatch_since_s = None

    def _check_physical_lower_bound(self, loads, seal_band_N) -> None:
        """D4 with the 110.2 hold: a reading below ``-(m_rod g + F_band) - 3 sigma`` falls the
        leg back only after ``d4_min_samples`` samples in a row covering ``d4_hold_s``; a
        shorter dip (an M4 drop transient read by one sample) is ``INFO_ROD_D4_TRANSIENT``."""
        settings = self.settings
        lower_bound = -(self.rod_weight_N + seal_band_N) - 3.0 * np.array(
            settings.force_sigma_N)
        for leg in range(LEG_COUNT):
            watch = self._legs[leg]
            is_judged = (self.rod_state[leg] is RodSensorState.OK
                         and self.head_state[leg] is not HeadSensorState.FAULT)
            if not (is_judged and loads[leg] < lower_bound[leg]):
                watch.d4_violation_samples = 0
                continue
            watch.d4_violation_samples += 1
            if watch.d4_violation_samples == 1:
                self._events.append((f"INFO_ROD_D4_TRANSIENT:{LEG_ORDER[leg]}", False))
            held_s = watch.d4_violation_samples * self.period_s
            if (watch.d4_violation_samples >= settings.d4_min_samples
                    and held_s >= settings.d4_hold_s - 1e-9):
                self._fall_back(leg, "D4")

    def _watch_rod_side(self, rod, loads) -> None:
        settings = self.settings
        share = np.array(settings.liftoff_rod_share)
        predicted = rod + share * (loads + self.rod_weight_N) / self.annulus_area_m2
        warning_Pa = settings.rod_limit_Pa - settings.rod_warning_margin_Pa
        for leg in range(LEG_COUNT):
            if self.rod_state[leg] is RodSensorState.FALLBACK or not math.isfinite(rod[leg]):
                continue
            name = LEG_ORDER[leg]
            if rod[leg] > warning_Pa:
                self._event_once(f"rod_pressure_over_limit:{name}")
            if rod[leg] > settings.rod_prewarning_Pa:
                self._event_once(f"rod_pressure_prewarning:{name}")
            if predicted[leg] > settings.rod_limit_Pa:
                self._event_once(f"WARN_ROD_LIFTOFF_OVERPRESSURE_RISK:{name}")

    def _watch_rising_rod_pressure(self) -> None:
        """P-13 (4): ``p_r`` up by ``rising_min_Pa`` over the window without a load change."""
        history = self._ready_history
        if len(history) < history.maxlen:
            return
        settings = self.settings
        count = max(1, round(1.0 / self.period_s))
        rods = np.array([entry[0] for entry in history])
        loads = np.array([entry[1] for entry in history])
        rise = rods[-count:].mean(axis=0) - rods[:count].mean(axis=0)
        load_change = np.abs(loads[-count:].mean(axis=0) - loads[:count].mean(axis=0))
        rising = (rise >= settings.rising_min_Pa) & (load_change < settings.rising_load_tolerance_N)
        for leg in np.flatnonzero(rising):
            self._event_once(f"INFO_ROD_PRESSURE_RISING:{LEG_ORDER[leg]}", False)

    def _watch_load_changes(self, t_s, loads, seal_band_N) -> None:
        """P-6 ``Delta F1`` shadow and the D5 sum check against the load baseline (called only
        while :attr:`is_load_watch_open`)."""
        baseline = self._baseline
        settings = self.settings
        change = loads - baseline.loads_N
        allowed = 4.0 * float(np.max(seal_band_N)) + settings.sum_extra_N
        if abs(float(change.sum())) <= allowed:
            baseline.sum_mismatch_since_s = None
        elif baseline.sum_mismatch_since_s is None:
            baseline.sum_mismatch_since_s = float(t_s)
        is_held = (baseline.sum_mismatch_since_s is not None
                   and t_s - baseline.sum_mismatch_since_s >= settings.sum_hold_s - 1e-9)
        if is_held and not baseline.is_sum_warned:
            baseline.is_sum_warned = True
            self._events.append(("WARN_LOAD_SUM_MISMATCH", True))
            self._log_load_sum_event(t_s, "WARN_LOAD_SUM_MISMATCH", loads, allowed)
        for leg in range(LEG_COUNT):
            watch = self._legs[leg]
            if change[leg] >= -settings.load_drop_N:
                watch.load_drop_since_s = None
                continue
            if watch.load_drop_since_s is None:
                watch.load_drop_since_s = t_s
            held = t_s - watch.load_drop_since_s >= settings.load_drop_hold_s - 1e-9
            if held and leg not in baseline.load_drop_flagged:
                baseline.load_drop_flagged.add(leg)
                self._events.append((f"shadow_load_drop:{LEG_ORDER[leg]}", False))

    # --- E-5 static load sum drift ---

    def _watch_drift(self, t_s: float, loads: NDArray[np.float64], is_locked_phase: bool) -> None:
        """72.1 (6): ``|sum F - sum F_ref| > drift_sum_N`` for ``drift_hold_s`` in READY with
        no external-force event meanwhile (a load-drop condition or a new fallback restarts
        the hold) -> ``WARN_PRESSURE_DRIFT`` once per run. Judged only while
        :attr:`is_load_watch_open` (110.1): a command restarts the hold."""
        settings = self.settings
        baseline = self._baseline
        is_judged = is_locked_phase and self.is_load_watch_open
        if settings.drift_sum_N is None or baseline is None or not is_judged:
            if baseline is not None:
                baseline.drift_since_s = None
            return
        change = abs(float(np.sum(loads) - np.sum(baseline.loads_N)))
        is_disturbed = any(watch.load_drop_since_s is not None for watch in self._legs)
        fallback_count = len(self.fallback_legs)
        if change <= settings.drift_sum_N or is_disturbed:
            baseline.drift_since_s = None
            return
        if baseline.drift_since_s is None or fallback_count != baseline.drift_fallback_count:
            baseline.drift_since_s = float(t_s)
            baseline.drift_fallback_count = fallback_count
        if t_s - baseline.drift_since_s >= settings.drift_hold_s - 1e-9:
            if "WARN_PRESSURE_DRIFT" not in self._reported:
                self._log_load_sum_event(t_s, "WARN_PRESSURE_DRIFT", loads, settings.drift_sum_N)
            self._event_once("WARN_PRESSURE_DRIFT")

    def _log_load_sum_event(self, t_s, name, loads, allowed_N) -> None:
        """110.1: sum, baseline sum and limit of a D5 / E-5 warning (meta ``load_sum_events``)."""
        self._load_sum_log.append({
            "t_s": float(t_s),
            "event": name,
            "sum_N": float(np.sum(loads)),
            "reference_sum_N": float(np.sum(self._baseline.loads_N)),
            "reference_t_s": self._baseline.t_s,
            "allowed_N": float(allowed_N),
        })

    def _count_command_free(self, commanded_m_s) -> None:
        if np.any(np.asarray(commanded_m_s) != 0.0):
            self._command_free_samples = 0
        elif self._command_free_samples is not None:
            self._command_free_samples += 1

    def _collect_load_sample(self, loads_N: NDArray[np.float64]) -> None:
        """120: buffer a command-free reading for the baseline mean; a command empties it."""
        if self._command_free_samples == 0:
            self._load_samples.clear()
            return
        self._load_samples.append(np.array(loads_N, dtype=float))

    # --- P-11 retraction lift-off shadow ---

    def _watch_retraction(self, loads, commanded, seal_band_N) -> None:
        """P-11 (U50, shadow): while a leg retracts at >= the speed fraction, after the settle
        time, the mean net force over the last ``retract_average_s`` plus ``F_band`` and the
        rod weight is the upper bound of the pad force (one-sided band: retracting reads
        ``L - F_s``); below ``retract_pad_limit_N`` the lift-off is confirmed (once per
        retraction)."""
        settings = self.settings
        self._retract_history.append(np.array(loads))
        settle = round(settings.retract_settle_s / self.period_s)
        average = self._retract_history.maxlen or 1
        threshold = settings.retract_speed_fraction * self.max_speed_m_s
        for leg in range(LEG_COUNT):
            watch = self._legs[leg]
            key = f"shadow_retract_liftoff:{LEG_ORDER[leg]}"
            if commanded[leg] > -threshold:
                watch.retract_samples = 0
                self._reported.discard(key)  # one confirmation per retraction
                continue
            watch.retract_samples += 1
            if watch.retract_samples < settle + average:
                continue
            mean_load = float(np.mean([entry[leg] for entry in self._retract_history]))
            band = float(np.broadcast_to(seal_band_N, LEG_COUNT)[leg])
            if mean_load + band + self.rod_weight_N[leg] < settings.retract_pad_limit_N:
                self._event_once(key, False)

    def _sample_at(self, t_s: float):
        if not math.isfinite(t_s) or not self._history:
            return None
        nearest = min(self._history, key=lambda entry: abs(entry[0] - t_s))
        if abs(nearest[0] - t_s) > self.period_s:
            return None
        return nearest[1], nearest[2]
