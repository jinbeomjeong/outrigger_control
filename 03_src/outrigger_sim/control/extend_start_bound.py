"""Recursive upper bound of the rod pressure after an extension (option ``tracked_bound``).

``06_analysis/03_hydraulic/coupled/v5/p3_extend_start_spec.md`` 3 / 4 (control-expert, plan D-p),
with the hydraulics-expert review of 2026-11-07 (``p3_review.md``): B hose factor on ``C_r`` and
no counted relief while the pump saturates or the stroke is at its end.

The controller runs the plant's own pure function
(:func:`outrigger_sim.hydraulics.rod_release.flow_limited_rod_pressure`) on conservative inputs
in 1 ms sub-steps per leg::

    valve      u_v <- u + (u_v - u) exp(-dt / tau_v)              (acting command u)
    speed      u_lb = kappa_x max(mean u_v over the sub-step, 0),
               0 if u_v <= 0, if the acting command is 0 (|u| <= eps) and u_v < delta_ol v_max
               (the plant's tail cut; v2, spec 3 (i)), if the pump demand
               sum A_h |u_v| (extend) + A_ann |u_v| (retract) > eta_v Q_pump with per leg the
               larger |u_v| of the sub-step start and end, if the stroke reading >= the end
               margin, or (revision 3) if the head reading of the period or of the previous
               one is >= p_sat 200 bar or NaN (relief stop: valve open, no flow)
    pressure   p <- flow_limited_rod_pressure(p, p_bB, u_lb, dt, tau, h C_r(s), ...)
    retract    p <- max(p, p_ret, retract moving model)   (no sub-steps)
    re-extend  p <- max(p, ④) before the first extending period after a lock stretch
               (revision 4; ④ = the monitor's locked model bound of the stretch's last read)
    C_r(s)     A_ann^2 (1/k_r + 1/k_h), k_h = beta A_h / (L0h + s),
               k_r = beta A_ann / (L0r + s_max - s), times the hose factor h

The relief speed is the exact sub-step mean of the valve, not its end value: with v2 a ramp
from rest counts from the first sub-step, and the end value over the whole sub-step relieved up to
210 Pa more than the plant there (T-P3-3, seed 20261107, plant step 1e-4 s).

Records kept by the plant adapters (harness ``harness_hydraulics``, L2b actuator; record only):

* ``hydraulics_record.extend_bound_check`` (:class:`ExtendBoundCheck`, ``tension_premise.md``
  5.4, 6.3): per leg, moving legs ``reads``, ``breach_reads``, ``margin_used_reads``,
  ``min_gap_bar``, ``min_gap_t_s``, ``first_breach_t_s``; legs locked after an extension
  against the monitor's ④ ``locked_reads``, ``locked_unpaired_reads``,
  ``locked_breach_reads``, ``locked_breach_over_tol_reads``, ``locked_min_gap_bar``,
  ``locked_min_gap_t_s``, ``locked_bound_source``, ``locked_tolerance_bar`` and the
  diagnostic ``locked_vs_extend_bound_reads``; ``retract_reads``, ``retract_breach_reads``;
  ``null`` = option off or no rod reading. Rule of a ③-on run (:data:`EXTEND_BOUND_CHECK_RULE`):
  moving ``sum(breach_reads) == 0`` passes (J-P3, criteria revision 8 3.2) and margin use is a
  FLAG; locked legs are judged by the VB T4h replay with the ③-on setting (``over_0p6kN ==
  0``; ``T4h-P3`` before revision 8), ``locked_breach_over_tol_reads > 0`` is a cross-check
  FLAG.
* ``hydraulics_record.tension_truth`` (:class:`TensionTruthCounter`): premise ① diagnostic
  (``substeps``, ``substeps_over_margin``, ``active_substeps``, ``min_p_tr_minus_p_star_bar``).

The step is increasing in ``p``, decreasing in the speed and increasing in ``C_r``, so a lower
speed and a larger compliance from an equal or higher start bound the plant from above (spec 3).
Every parameter is an ASSUMPTION (hydraulics-expert review); units SI, gauge pressures.

Revision 5 (436.9, ``06_analysis/02_control/j_p3_cause/jp3_remedy_spec.md`` 2; user decisions
144-146): the monitor classifies every period (:class:`PeriodClass`) and hands the class to
:meth:`ExtendStartTracker.advance`::

    lock       u = 0                          revision 4 as it is
    hold       0 < |u| <= u_hold              valve follows u, no relief, no retract floor
    carry_ext  |u| > u_hold after a lock      p <- max(p, ④c) every period; relief counts from the
                                              sub-step after the line-fill gate opened (R5-4)
    carry_ret  |u| < -u_hold after a lock     p <- max(p, ④c, retract floor), no relief
    ext / ret  otherwise                      revision 4

``u_hold = hold_speed_ratio v_max`` (0.01 v_max, decision 146). The line-fill gate
(:class:`LineFillGateBound`) fills the M1c line with ``kappa_x`` times the valve estimate and
opens no earlier than the P1 plant (spec 2.4; gate values of user decision 147: ``e_h`` 9 bar,
retract need at ``F_band`` 0 and ``p_r`` = floor). A carry run that ends in a lock or hold
period with the gate still shut hands its candidates to the new stretch (``carry_end_rule``,
implementer addition pending control-expert confirmation). A revision 4 meta stays as it was
(:meth:`ExtendStartBound.to_meta`).

Revision 6 (edition 5, ``06_analysis/02_control/j_p3_cause/jp3_remedy_spec_v5.md`` 4) adds to
revision 5, on every leg whatever its rod sensor state (4.5; only a fallback leg's lower bound
reaches a command, so a run without a fallback has the revision 5 commands, P5-1):

* R5-8 release witness (monitor): a carry read ``n`` with ``sign(u_n) (s_n - s_ref) >= 1.0 mm``
  (``stroke_m`` oil-volume reading, ``s_ref`` = the reading of the read before the carry's
  first period or its last direction change) ends the carry as an open gate would: from the
  next read EXT / RET, no ④c raise, no R5-6 inheritance.
* R5-9 retract relief (this tracker, 1 ms sub-steps): in a same-sign retract run (RET /
  CARRY_RET) after release evidence (a retract witness or the gate opening, the earlier one;
  from the next sub-step)::

      p <- max(p - A_ann kappa_x |u_v| f_lb dt / (h C_r(s)),
               p*_ub + (p - p*_ub) exp(-dt / tau), max(p_ret, 13 bar + p_h^ub / 3))

  with ``f_lb``, ``p*_ub = p*_ret(p_h^ub A_h - p_floor A_ann)`` and ``p_h^lb`` / ``p_h^ub`` of
  :class:`ReleaseReliefParams`. A sub-step of pump saturation, of a head reading at the relief
  stop or NaN, of a zero acting command, or with the stroke reading at or below 15.2 mm (the
  retract end guard, ``r59_end_guard_substeps``) takes the floor term only. A lock or hold
  period stops it; a sign change or a new run clears the evidence.
* R5-10 (monitor): a retracting hold candidate after a retract run with R5-9 on is
  ``max(13 bar + p_h / 3, p_ret, p_hat + delta_m)``.
* ``M_j``: the window candidates after a retraction keep R5-7 at each sample's ``p_hat(t_j)``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from outrigger_sim.hydraulics.check_open_delay import (
    CheckValveValues,
    RetractConfig,
    retract_dead,
)
from outrigger_sim.hydraulics.rod_release import RodPressureFlowLaw, flow_limited_rod_pressure
from outrigger_sim.params import LEG_ORDER

BAR_PA = 1.0e5
LEG_COUNT = 4

EXTEND_START_REVISION = 4
"""Revision of the bound rule in the meta (v2: overlap cut with a zero command only, sub-step
mean valve, start / end saturation test; spec 3 and its v2 review. 3: no relief counted in a
period whose head reading or the previous one is at the relief stop, spec 10. 4: an extension
that ends a lock stretch starts at ``max(p, ④)``, ④ = the monitor's model bound of the stretch's
last read, spec 11). A
``tracked_bound`` meta of another revision, or without one (v1), is refused
(:func:`check_extend_start_meta`)."""
TRACKED_BOUND_RULE = "tracked_bound"

BOUND_BULK_MODULUS_PA = 0.69e9
BOUND_HEAD_DEAD_LENGTH_M = 0.08
BOUND_ROD_DEAD_LENGTH_M = 0.10
"""Sensitivity ends of the oil columns (spec 3: a larger ``C_r`` relieves slower)."""
BOUND_HOSE_FACTOR = 1.40
"""``1 + h_B``: B hose volume on ``C_r`` (hydraulics-expert review 2026-11-07, item 1)."""
BOUND_SPEED_FACTOR = 0.8
"""``kappa_x``: delivered speed lower bound over the valve estimate (flow share, ``b_T``)."""
BOUND_OVERLAP_CUT_RATIO = 0.05
"""``delta_ol,max``: with a zero acting command, below this valve fraction of ``v_max`` no relief
is counted (LS2 end). A small non-zero command flows in the plant (spec L-6) and counts
``kappa_x u_v`` (v2, user decision 2026-11-07; v1 cut every command below it)."""
ZERO_COMMAND_M_S = 1.0e-6
"""``eps`` of a zero acting command: the plant cuts the tail at ``|u| <= eps`` (L2b
``LOCK_EPS_M_S``, the harness ``install_overlap_cut``), so the bound treats it as zero too."""
BOUND_LAG_S = 0.05
BOUND_BACK_PRESSURE_PA = 5.0 * BAR_PA
"""``p_bB``: extension target of the plant (its ASSUMPTION)."""
BOUND_MARGIN_PA = 0.5 * BAR_PA
"""``delta_m``: sub-step and reading-delay margin added to the bound."""
BOUND_SUBSTEP_S = 1.0e-3
BOUND_PUMP_FLOW_M3_S = 60.2e-3 / 60.0
"""``Q_pump`` 60.2 L/min (YAML ``actuator`` pump)."""
BOUND_VOLUMETRIC_EFFICIENCY = 0.85
"""``eta_v`` of the saturation test; the lower end of the plant values (VB 0.85, nominal 0.95)
counts saturation earlier (ASSUMPTION)."""
BOUND_STROKE_END_M = 0.6848
"""End-margin stroke: at or beyond it the end braking may slow the leg (no relief counted)."""
BOUND_SATURATION_STOP_HEAD_PA = 200.0e5
"""``p_sat`` (spec 10, revision 3): a head reading at or above it (or NaN) in the period or the
previous one means the leg may stand at the relief stop (210 bar) with its valve open, so no
relief is counted. ASSUMPTION: relief 210 bar minus a 10 bar reading allowance (at least twice
the normal-grade +-4 bar)."""

EXTEND_HOLD_REVISION = 5
"""436.9 revision (module docstring): micro-command lock hold R5-1 / R5-5, retract hold
candidate R5-2 (rule (i)), exit seed in both directions R5-3, line-fill gate R5-4."""
EXTEND_WITNESS_REVISION = 6
"""436.9 edition 5 (``jp3_remedy_spec_v5.md`` 4): revision 5 plus the release witness R5-8,
the retract relief bound R5-9 after release evidence, the retract hold candidate R5-10 and
the re-lock start ``M_j`` of each window sample (module docstring, revision 6)."""
EXTEND_SEED_FIX_REVISION = 7
"""436.9 edition 7 (``jp3_remedy_spec_v7.md`` 3.5, ③ rev 7): the bound of revision 6 unchanged
(no new bound term, so the commands are those of revision 6, P7-1); the revision changes the
judged set (the ``carry_ext`` reads of the first PROBE after the event on a leg that went
``locked_ext`` -> ``moving_ext``) and the identity (``rule_revision`` 7, base tag
``final_C4G2_P3X``)."""
SUPPORTED_REVISIONS = (EXTEND_START_REVISION, EXTEND_HOLD_REVISION, EXTEND_WITNESS_REVISION,
                       EXTEND_SEED_FIX_REVISION)
HOLD_REVISIONS = (EXTEND_HOLD_REVISION, EXTEND_WITNESS_REVISION, EXTEND_SEED_FIX_REVISION)
"""Revisions with the period classes of revision 5 (revisions 6 and 7 build on them)."""
WITNESS_REVISIONS = (EXTEND_WITNESS_REVISION, EXTEND_SEED_FIX_REVISION)
"""Revisions with R5-8 .. R5-10 (revision 7 runs the bound of revision 6)."""
HOLD_SPEED_RATIO = 0.01
"""``u_hold / v_max`` (user decision 146: the ratio, 0.20924 mm/s at the YAML ``v_max``)."""
HOLD_SPEED_RATIO_MAX = 0.012
"""Upper end of ``u_hold / v_max`` for which the hold premise holds under P1 (VN, ``c_v`` 0.02):
a loaded leg (``p_h`` >= 10 bar) does not leave its lock below 1.23 % ``v_max``
(``hydraulics_remedy_review.md`` 2.2; user decision 147)."""
RETRACT_HOLD_RULE = "retract_model_candidate"
"""R5-2 rule (i): a retracting hold or carry period adds ``(max(retract model, p_ret), p_h)``."""
EXIT_SEED_RULE = "both"
"""R5-3: the first carry period after a lock seeds ``max(p, ④)`` in both directions."""
JP3_SPEC_EDITION = "8be9de22"
"""First 8 hex digits of the sha256 of the sealed ``jp3_remedy_spec.md`` edition 4a (13.6): the
``spec_edition`` of every revision 5 ``extend_bound_check``; the judgement refuses other values
(output of an older edition's code)."""
JP3_SPEC_EDITION_V5 = "fe6f5844"
"""First 8 hex digits of the sha256 of the sealed ``jp3_remedy_spec_v5.md`` (edition 5): the
``spec_edition`` of every revision 6 record."""
JP3_SPEC_EDITION_V7 = "10902ffd"
"""Edition 7: the first 8 hex digits of the sha256 of the sealed ``jp3_remedy_spec_v7.md``
(revision 6, 10902ffd..., master e241638d; spec 5.1): the ``spec_edition`` of every revision 7
record. The draft value 85ce6e2a (revision 2) of the probe lines is replaced at the run commit;
an identity value, no command changes."""
JP3_SPEC_EDITION_OF_REVISION = {EXTEND_HOLD_REVISION: JP3_SPEC_EDITION,
                                EXTEND_WITNESS_REVISION: JP3_SPEC_EDITION_V5,
                                EXTEND_SEED_FIX_REVISION: JP3_SPEC_EDITION_V7}
"""The sealed edition each hold revision's record must carry (13.6 / edition 5 4.6)."""
CARRY_END_INHERIT = "inherit_when_gate_shut"
"""R5-6 (spec 2.9, user decision 152): a carry run that ends in a lock or hold period before
the tracker gate opened hands its candidates to the new stretch (the plant may never have left
its lock; case replay E, LSJ4 FL 49.0 s)."""
CARRY_END_SPEC_2_1 = "fresh_stretch"
"""Edition 3 spec 2.1: the new stretch starts with new candidates only. Unsound (counterexample
⑪); accepted only with :data:`ALLOW_FRESH_STRETCH_FOR_TEST`."""
CARRY_END_RULES = (CARRY_END_INHERIT,)
"""The settable ``carry_end_rule`` values (edition 4a 13.7)."""
RETRACT_START_WITH_TRACKER = "with_tracker"
"""R5-7 (spec 2.10): after a retraction the lock start model is ``max(retract model, p_ret,
p_hat + delta_m)``."""
RETRACT_START_MODEL_ONLY = "model_only"
"""Edition 3 behaviour (no ``p_hat`` term); accepted only with
:data:`ALLOW_MODEL_ONLY_RETRACT_START_FOR_TEST`."""
RETRACT_START_RULES = (RETRACT_START_WITH_TRACKER,)
"""The settable ``retract_start_rule`` values (edition 4a 13.7)."""
ALLOW_FRESH_STRETCH_FOR_TEST = False
"""Test only (edition 4a 13.7): accept ``carry_end_rule = "fresh_stretch"``. No option, preset
or CLI path sets it; rows built with it run under a ``*_X11`` setting name in their own folder
and the judgement refuses them."""
ALLOW_MODEL_ONLY_RETRACT_START_FOR_TEST = False
"""Test only (edition 4a 13.7): accept ``retract_start_rule = "model_only"`` (as above)."""
REVISION_5_FIELDS = ("hold_speed_ratio", "retract_hold_rule", "exit_seed_rule",
                     "line_fill_gate", "carry_end_rule", "retract_start_rule")
"""Fields of :class:`ExtendStartBound` that a revision 4 meta does not carry."""
GATE_HEAD_READING_MARGIN_PA = 9.0e5
"""``e_h`` of the gate, normal sensor grade (user decision 147; ``hydraulics_remedy_review.md``
3.4: ``b_read`` 4.62 bar + intra-period head bump 3.6 bar + 0.8 bar; 0 early openings in the
review grid). ASSUMPTION (the bump is an observed ringing value)."""
GATE_RETRACT_FRICTION_BAND_N = 0.0
"""``F_band`` of the retract need upper bound: the need falls with ``F_band``, so 0 is the
conservative end (user decision 147, review 3.3; the spec's 8 kN was the wrong end)."""
GATE_ROD_FLOOR_PA = 0.1e5 - 1.01325e5
"""``p_r`` of the retract need upper bound: the floor 0.1 bar abs as a gauge value (-0.913 bar;
the need falls with ``p_r``; user decision 147, review 3.3)."""
REVISION_6_FIELDS = ("release_relief",)
"""Fields of :class:`ExtendStartBound` that a revision 4 or 5 meta does not carry."""


@dataclass(frozen=True)
class ReleaseReliefParams:
    """Revision 6 values of R5-8 and R5-9 (``jp3_remedy_spec_v5.md`` 4.1, 4.2; ASSUMPTIONS, all
    on the conservative side). ``kappa_x``, ``h C_r(s)`` and ``tau`` are the bound's own
    ``speed_factor``, compliance and ``lag_s``.

    Attributes:
        witness_stroke_m: ``Delta s_w`` of the release witness (1.0 mm).
        head_reading_margin_Pa: ``e_h`` of ``p_h^lb`` / ``p_h^ub`` (9 bar).
        head_back_Pa: ``p_bA`` of ``f_lb`` and of the retract target ``p*_ret`` (5 bar).
        tank_Pa: ``p_T`` of ``f_lb`` (2 bar).
        retract_end_stroke_m: ``s_lo`` of the retract end guard (15.2 mm).
        pilot_ratio: ``psi`` of ``p*_ret`` (plant POC pilot ratio 3.5).
        crack_Pa: ``p_cr`` of ``p*_ret`` (3 bar).
        relief_Pa: Upper clip of ``p*_ret`` (210 bar).
        rod_floor_Pa: ``p_floor`` of ``F_ub = p_h^ub A_h - p_floor A_ann`` (0.1 bar abs).
    """

    witness_stroke_m: float = 1.0e-3
    head_reading_margin_Pa: float = 9.0e5
    head_back_Pa: float = 5.0e5
    tank_Pa: float = 2.0e5
    retract_end_stroke_m: float = 0.0152
    pilot_ratio: float = 3.5
    crack_Pa: float = 3.0e5
    relief_Pa: float = 210.0e5
    rod_floor_Pa: float = GATE_ROD_FLOOR_PA

    def __post_init__(self) -> None:
        positive = ("witness_stroke_m", "pilot_ratio", "relief_Pa")
        for name in positive:
            value = getattr(self, name)
            if not (math.isfinite(value) and value > 0.0):
                raise ValueError(f"{name} must be a finite value > 0, got {value!r}")
        if not self.head_back_Pa > self.tank_Pa:
            raise ValueError("head_back_Pa (p_bA) must exceed tank_Pa (p_T)")
        if not (math.isfinite(self.retract_end_stroke_m) and self.retract_end_stroke_m >= 0.0):
            raise ValueError("retract_end_stroke_m must be a finite value >= 0")


def retract_target_rod_pressure_Pa(force_N: float, head_area_m2: float, annulus_area_m2: float,
                                   params: ReleaseReliefParams) -> float:
    """``p*_ret(F)`` of the plant (``RodChamberLegParams.moving_target_rod_pressure_Pa`` with
    the RET mode: the head POC pilot threshold, clipped at the relief), on the values of
    ``params``.

    Args:
        force_N: Cylinder net force ``F``.
        head_area_m2: ``A_h``.
        annulus_area_m2: ``A_ann``.
        params: ``psi``, ``p_cr``, ``p_bA`` and the relief.
    """
    area_ratio = head_area_m2 / annulus_area_m2
    inverse_pilot = 1.0 / params.pilot_ratio
    threshold_head_Pa = (force_N / annulus_area_m2 + params.crack_Pa
                         + params.head_back_Pa * (1.0 - inverse_pilot)) / (
        area_ratio - inverse_pilot)
    head_Pa = max(params.head_back_Pa, threshold_head_Pa)
    target_Pa = (head_Pa * head_area_m2 - force_N) / annulus_area_m2
    return min(target_Pa, params.relief_Pa)


def release_witness_moved_m(command_m_s: float, stroke_m: float, reference_m: float) -> float:
    """R5-8 movement ``sign(u_n) (s_n - s_ref)`` of a carry read (spec v5 4.1); NaN when the
    stroke reading or the reference is unknown. The carry is witnessed when this is at least
    ``witness_stroke_m`` (a NaN never is)."""
    if not (math.isfinite(stroke_m) and math.isfinite(reference_m)):
        return math.nan
    return math.copysign(1.0, command_m_s) * (stroke_m - reference_m)


def relief_flow_factor(head_lower_Pa: float, params: ReleaseReliefParams) -> float:
    """``f_lb = [sqrt((p_h^lb - p_T)^+ / (p_bA - p_T)) - 1]^+`` (0 for a NaN head)."""
    if not math.isfinite(head_lower_Pa):
        return 0.0
    ratio = max(head_lower_Pa - params.tank_Pa, 0.0) / (params.head_back_Pa - params.tank_Pa)
    return max(math.sqrt(ratio) - 1.0, 0.0)


@dataclass(frozen=True)
class LineFillGateParams:
    """Line-fill gate of the tracker (spec 2.4 table; P1 nominal values plus conservative inputs).

    Attributes:
        line_volume_m3: ``V_line`` (``CheckValveValues``, Q-M9).
        hose_bulk_modulus_Pa: ``beta_hose``.
        pilot_ratio: ``psi``.
        crack_pressure_Pa: ``p_cr``.
        tank_pressure_Pa: ``p_T``.
        neutral_fraction: ``f_n`` of the VN neutral leak.
        vent_closing_opening: ``c_v`` (fraction of ``v_max``).
        compensator_drop_Pa: ``dp_comp`` of ``K_n``.
        fill_speed_factor: ``kappa_x`` on the valve estimate.
        head_reading_margin_Pa: ``e_h`` on the head reading.
        retract_friction_band_N: ``F_band`` end of the retract need grid.
        retract_bulk_modulus_Pa: ``beta`` of the retract need.
        retract_rod_dead_length_m: ``L0r`` of the retract need.
        retract_head_dead_length_m: ``L0h`` of the retract need.
        rod_floor_Pa: Low end of the retract need ``p_r`` grid.
    """

    line_volume_m3: float = CheckValveValues.v_line_m3
    hose_bulk_modulus_Pa: float = CheckValveValues.beta_hose_Pa
    pilot_ratio: float = CheckValveValues.psi
    crack_pressure_Pa: float = CheckValveValues.p_crack_Pa
    tank_pressure_Pa: float = 2.0e5
    neutral_fraction: float = CheckValveValues.neutral_fraction
    vent_closing_opening: float = 0.02
    compensator_drop_Pa: float = 10.0e5
    fill_speed_factor: float = BOUND_SPEED_FACTOR
    head_reading_margin_Pa: float = GATE_HEAD_READING_MARGIN_PA
    retract_friction_band_N: float = GATE_RETRACT_FRICTION_BAND_N
    retract_bulk_modulus_Pa: float = BOUND_BULK_MODULUS_PA
    retract_rod_dead_length_m: float = BOUND_ROD_DEAD_LENGTH_M
    retract_head_dead_length_m: float = BOUND_HEAD_DEAD_LENGTH_M
    rod_floor_Pa: float = GATE_ROD_FLOOR_PA

    def __post_init__(self) -> None:
        positive = ("line_volume_m3", "hose_bulk_modulus_Pa", "pilot_ratio",
                    "vent_closing_opening", "compensator_drop_Pa", "retract_bulk_modulus_Pa")
        for name in positive:
            value = getattr(self, name)
            if not (math.isfinite(value) and value > 0.0):
                raise ValueError(f"{name} must be a finite value > 0, got {value!r}")
        if not 0.0 < self.fill_speed_factor <= 1.0:
            raise ValueError(f"fill_speed_factor must be in (0, 1], got "
                             f"{self.fill_speed_factor!r}")


@dataclass(frozen=True)
class ExtendStartBound:
    """Conservative parameters of the bound (spec 3 table, review 2026-11-07; ASSUMPTIONS).

    Attributes:
        bulk_modulus_Pa: ``beta`` of ``C_r``.
        head_dead_length_m: ``L0h``.
        rod_dead_length_m: ``L0r``.
        hose_factor: ``1 + h_B`` on ``C_r``.
        speed_factor: ``kappa_x``.
        overlap_cut_ratio: ``delta_ol,max`` (fraction of ``v_max``).
        lag_s: ``tau`` of the pressure lag.
        back_pressure_Pa: ``p_bB``.
        margin_Pa: ``delta_m``.
        substep_s: Sub-step ``dt``.
        pump_flow_m3_s: ``Q_pump``.
        volumetric_efficiency: ``eta_v`` of the saturation test.
        stroke_end_m: End-margin stroke.
        saturation_stop_head_Pa: ``p_sat`` of the relief-stop test.
        revision: Rule revision, :data:`SUPPORTED_REVISIONS` (class default 4).
        hold_speed_ratio: Revision 5 ``u_hold / v_max``.
        retract_hold_rule: Revision 5 R5-2 rule (only :data:`RETRACT_HOLD_RULE`).
        exit_seed_rule: Revision 5 R5-3 rule (only :data:`EXIT_SEED_RULE`).
        line_fill_gate: Revision 5 R5-4 gate; None on revision 5 = the defaults.
        carry_end_rule: Revision 5 end of a carry run in a lock or hold period, R5-6
            (:data:`CARRY_END_RULES`; ``fresh_stretch`` only under the test constant).
        retract_start_rule: Revision 5 lock start model after a retraction, R5-7
            (:data:`RETRACT_START_RULES`; ``model_only`` only under the test constant).
        release_relief: Revision 6 R5-8 / R5-9 values; None on revision 6 = the defaults
            (left out of a revision 4 or 5 meta).
    """

    bulk_modulus_Pa: float = BOUND_BULK_MODULUS_PA
    head_dead_length_m: float = BOUND_HEAD_DEAD_LENGTH_M
    rod_dead_length_m: float = BOUND_ROD_DEAD_LENGTH_M
    hose_factor: float = BOUND_HOSE_FACTOR
    speed_factor: float = BOUND_SPEED_FACTOR
    overlap_cut_ratio: float = BOUND_OVERLAP_CUT_RATIO
    lag_s: float = BOUND_LAG_S
    back_pressure_Pa: float = BOUND_BACK_PRESSURE_PA
    margin_Pa: float = BOUND_MARGIN_PA
    substep_s: float = BOUND_SUBSTEP_S
    pump_flow_m3_s: float = BOUND_PUMP_FLOW_M3_S
    volumetric_efficiency: float = BOUND_VOLUMETRIC_EFFICIENCY
    stroke_end_m: float = BOUND_STROKE_END_M
    saturation_stop_head_Pa: float = BOUND_SATURATION_STOP_HEAD_PA
    revision: int = EXTEND_START_REVISION
    hold_speed_ratio: float = HOLD_SPEED_RATIO
    retract_hold_rule: str = RETRACT_HOLD_RULE
    exit_seed_rule: str = EXIT_SEED_RULE
    line_fill_gate: LineFillGateParams | None = None
    carry_end_rule: str = CARRY_END_INHERIT
    retract_start_rule: str = RETRACT_START_WITH_TRACKER
    release_relief: ReleaseReliefParams | None = None

    def __post_init__(self) -> None:
        if self.revision not in SUPPORTED_REVISIONS:
            raise ValueError(f"extend start bound revision {self.revision!r}: this code runs "
                             f"revisions {SUPPORTED_REVISIONS} only")
        positive = ("bulk_modulus_Pa", "hose_factor", "substep_s", "pump_flow_m3_s",
                    "volumetric_efficiency")
        for name in positive:
            value = getattr(self, name)
            if not (math.isfinite(value) and value > 0.0):
                raise ValueError(f"{name} must be a finite value > 0, got {value!r}")
        if not 0.0 <= self.speed_factor <= 1.0:
            raise ValueError(f"speed_factor must be in [0, 1], got {self.speed_factor!r}")
        if not (self.lag_s >= 0.0 and self.margin_Pa >= 0.0):
            raise ValueError("lag_s and margin_Pa must be >= 0")
        if self.is_hold_revision:
            self._check_hold_fields()
        if self.is_witness_revision and self.release_relief is None:
            object.__setattr__(self, "release_relief", ReleaseReliefParams())
        elif not self.is_witness_revision and self.release_relief is not None:
            raise ValueError(f"release_relief is a revision 6 field (revision {self.revision})")

    def _check_hold_fields(self) -> None:
        if not 0.0 < self.hold_speed_ratio <= HOLD_SPEED_RATIO_MAX:
            raise ValueError(f"hold_speed_ratio must be in (0, {HOLD_SPEED_RATIO_MAX}] (the hold "
                             f"premise under P1), got {self.hold_speed_ratio!r}")
        if self.retract_hold_rule != RETRACT_HOLD_RULE:
            raise ValueError(f"retract_hold_rule {self.retract_hold_rule!r}: only "
                             f"{RETRACT_HOLD_RULE!r} (rule (i), decision 146)")
        if self.exit_seed_rule != EXIT_SEED_RULE:
            raise ValueError(f"exit_seed_rule {self.exit_seed_rule!r}: only {EXIT_SEED_RULE!r}")
        self.check_allowed()
        if self.line_fill_gate is None:
            object.__setattr__(self, "line_fill_gate", LineFillGateParams())

    def check_allowed(self) -> None:
        """Refuse the test-only rule values unless their test constant is on (edition 4a
        13.7). A pickle restores without ``__post_init__``, so the monitor calls this again
        when it builds or reopens its revision 5 state.

        Raises:
            ValueError: An unknown value, or a test-only value with its constant off.
        """
        rules = (("carry_end_rule", CARRY_END_RULES, CARRY_END_SPEC_2_1,
                  ALLOW_FRESH_STRETCH_FOR_TEST, "ALLOW_FRESH_STRETCH_FOR_TEST"),
                 ("retract_start_rule", RETRACT_START_RULES, RETRACT_START_MODEL_ONLY,
                  ALLOW_MODEL_ONLY_RETRACT_START_FOR_TEST,
                  "ALLOW_MODEL_ONLY_RETRACT_START_FOR_TEST"))
        for name, allowed, test_value, is_test_allowed, constant in rules:
            # getattr: a bound pickled before the field has the class default
            value = getattr(self, name)
            if value in allowed or (value == test_value and is_test_allowed):
                continue
            if value == test_value:
                raise ValueError(f"{name} {value!r} is a test-only value (module constant "
                                 f"{constant} is off)")
            raise ValueError(f"{name} {value!r}: one of {allowed}")

    @property
    def uses_retract_tracker_start(self) -> bool:
        """R5-7 is on (revision 5 with ``retract_start_rule`` ``with_tracker``)."""
        return self.is_hold_revision and self.retract_start_rule == RETRACT_START_WITH_TRACKER

    def identity(self) -> dict[str, Any]:
        """Edition 4a 13.6: the rule identity a revision 5 record carries; a revision 6 record
        carries the edition 5 ``spec_edition`` and its ``rule_revision`` (4.6)."""
        identity: dict[str, Any] = {
            "spec_edition": JP3_SPEC_EDITION_OF_REVISION.get(self.revision, JP3_SPEC_EDITION),
            "carry_end_rule": self.carry_end_rule,
            "retract_start_rule": self.retract_start_rule}
        if self.is_witness_revision:
            identity["rule_revision"] = self.revision
        return identity

    @property
    def is_hold_revision(self) -> bool:
        """Revision 5 or 6 (436.9): the period classes, the hold and the line-fill gate."""
        return self.revision in HOLD_REVISIONS

    @property
    def is_witness_revision(self) -> bool:
        """Revision 6 (edition 5): R5-8 witness, R5-9 retract relief, R5-10 hold candidate;
        revision 7 runs the same bound (edition 7 3.5)."""
        return self.revision in WITNESS_REVISIONS

    def hold_speed_m_s(self, max_speed_m_s: float) -> float:
        """``u_hold`` of revision 5."""
        return self.hold_speed_ratio * max_speed_m_s

    def to_meta(self) -> dict[str, Any]:
        """The fields; a revision 4 meta keeps exactly its keys of before 436.9 (the revision 5
        fields are left out) and a revision 5 meta its keys of before edition 5 (the revision 6
        fields are left out), so stored metas and digests compare as before."""
        meta = asdict(self)
        if not self.is_witness_revision:
            for name in REVISION_6_FIELDS:
                meta.pop(name, None)
        if not self.is_hold_revision:
            for name in REVISION_5_FIELDS:
                del meta[name]
        return meta


@dataclass(frozen=True)
class BoundGeometry:
    """Per-leg cylinder data of the bound (from the monitor).

    Attributes:
        head_area_m2: ``A_h`` per leg.
        annulus_area_m2: ``A_ann`` per leg.
        stroke_max_m: ``s_max``.
        max_speed_m_s: ``v_max``.
        valve_tau_s: ``tau_v`` of the controller's valve model.
    """

    head_area_m2: tuple[float, ...]
    annulus_area_m2: tuple[float, ...]
    stroke_max_m: float
    max_speed_m_s: float
    valve_tau_s: float


class PeriodClass(StrEnum):
    """Revision 5 class of one leg and period (spec 2.1; the J-P3 read class of 6.2)."""

    LOCK = "lock"
    HOLD = "hold"
    CARRY_EXT = "carry_ext"
    CARRY_RET = "carry_ret"
    EXT = "ext"
    RET = "ret"

    @property
    def is_carry(self) -> bool:
        return self in (PeriodClass.CARRY_EXT, PeriodClass.CARRY_RET)

    @property
    def is_locked(self) -> bool:
        """The monitor keeps a lock stretch open (``lock`` and ``hold``)."""
        return self in (PeriodClass.LOCK, PeriodClass.HOLD)

    @property
    def is_retracting(self) -> bool:
        return self in (PeriodClass.CARRY_RET, PeriodClass.RET)


PERIOD_CLASS_CODES = {period_class: code for code, period_class in enumerate(PeriodClass)}
"""``int8`` codes of the per-read T4h arrays (``jp3_class``); -1 = no class."""


def period_class_of(command_m_s: float, hold_speed_m_s: float, follows_lock: bool,
                    is_gate_open: bool) -> PeriodClass:
    """Spec 2.1 table for one leg.

    Args:
        command_m_s: Acting command ``u_k``.
        hold_speed_m_s: ``u_hold``.
        follows_lock: The lock stretch was open at the previous read, or the previous period
            was a carry period.
        is_gate_open: The tracker's line-fill gate is open at the period start.
    """
    if command_m_s == 0.0:
        return PeriodClass.LOCK
    if abs(command_m_s) <= hold_speed_m_s:
        return PeriodClass.HOLD
    is_extending = command_m_s > 0.0
    if follows_lock and not is_gate_open:
        return PeriodClass.CARRY_EXT if is_extending else PeriodClass.CARRY_RET
    return PeriodClass.EXT if is_extending else PeriodClass.RET


def retract_need_upper_bound(params: LineFillGateParams, head_ub_Pa: float, stroke_m: float,
                             head_area_m2: float, annulus_area_m2: float,
                             stroke_max_m: float) -> tuple[float, float]:
    """``(need_ub, p_open)`` of a retraction (:meth:`LineFillGateBound.retract_need_m`): the
    M1c ``retract_dead`` need at the conservative inputs of ``params`` (``p_r`` = floor,
    ``F_band``, void 0, ``beta``, ``L0r``, ``L0h``); a NaN stroke takes stroke 0 (the need
    falls with the stroke). Edition 7 3.2 caps the probe retract with the same function."""
    retract_config = RetractConfig(
        rod_forward=True, volume_scale=1.0, v_line_m3=params.line_volume_m3,
        beta_hose_Pa=params.hose_bulk_modulus_Pa, psi=params.pilot_ratio,
        p_crack_Pa=params.crack_pressure_Pa)
    stroke = stroke_m if math.isfinite(stroke_m) else 0.0
    result = retract_dead(
        retract_config, head_ub_Pa, params.rod_floor_Pa, params.retract_friction_band_N,
        stroke, 0.0, head_area_m2, annulus_area_m2, stroke_max_m,
        params.retract_rod_dead_length_m, params.retract_head_dead_length_m,
        params.retract_bulk_modulus_Pa, params.tank_pressure_Pa)
    return result["need"], result["p_open"]


class LineFillGateBound:
    """R5-4 line-fill gate of the tracker (spec 2.4), one line state ``x_hat`` per leg.

    Extension, per 1 ms sub-step with the mean valve estimate ``u_v``::

        x_hat <- max(x_hat + (kappa_x max(u_v, 0) - d_hat) dt, 0),
        d_hat = K_n g sqrt(max(p_A - p_T, 0)) / A_h,  g = (1 - |u_v| / (c_v v_max))+
        p_A = p_T + x_hat A_h beta_hose / V_line
        open: p_A >= max(p_h_ub + p_cr, p_T + (p_hat + p_cr - p_T) / psi)

    Retraction: ``x_hat`` in ``A_ann`` stroke units with the M1c retract drain; open at
    ``x_hat >= need_ub`` (:meth:`retract_need_m`). The gate fills slower and opens later than
    the P1 plant (``kappa_x`` on the speed, the ``psi p_B`` term dropped, conservative need), so
    the tracker never counts relief before the plant leaves its lock.

    Args:
        params: Gate values.
        head_area_m2: ``A_h`` per leg.
        annulus_area_m2: ``A_ann`` per leg.
        stroke_max_m: ``s_max``.
        max_speed_m_s: ``v_max``.
    """

    def __init__(self, params: LineFillGateParams, head_area_m2: ArrayLike,
                 annulus_area_m2: ArrayLike, stroke_max_m: float, max_speed_m_s: float) -> None:
        self.params = params
        self.head_area_m2 = np.asarray(head_area_m2, dtype=float).reshape(LEG_COUNT)
        self.annulus_area_m2 = np.asarray(annulus_area_m2, dtype=float).reshape(LEG_COUNT)
        self.stroke_max_m = float(stroke_max_m)
        self.max_speed_m_s = float(max_speed_m_s)
        self.neutral_coefficient = (params.neutral_fraction * self.head_area_m2
                                    * self.max_speed_m_s
                                    / math.sqrt(params.compensator_drop_Pa))
        """``K_n`` per leg (the M1c ``K_land`` of a VN circuit)."""
        self.fill_m = np.zeros(LEG_COUNT)
        self.direction = np.zeros(LEG_COUNT, dtype=np.int64)
        self.is_open = np.zeros(LEG_COUNT, dtype=bool)
        self._retract_config = RetractConfig(
            rod_forward=True, volume_scale=1.0, v_line_m3=params.line_volume_m3,
            beta_hose_Pa=params.hose_bulk_modulus_Pa, psi=params.pilot_ratio,
            p_crack_Pa=params.crack_pressure_Pa)
        self._need_cache: dict[tuple[int, float, float], tuple[float, float]] = {}

    def reset(self, leg: int) -> None:
        """Empty line, gate shut (a lock or a hold period)."""
        self.fill_m[leg] = 0.0
        self.direction[leg] = 0
        self.is_open[leg] = False
        self._last_need_array()[leg] = np.nan

    def advance_substep(self, leg: int, mean_valve_m_s: float, step_s: float,
                        head_ub_Pa: float, rod_ub_Pa: float, stroke_m: float,
                        direction: int) -> bool:
        """One sub-step of ``leg``; True once the gate is open.

        Args:
            leg: Leg index.
            mean_valve_m_s: Mean valve estimate of the sub-step.
            step_s: Sub-step length.
            head_ub_Pa: ``p_h_ub = max(p_h,k, p_h,k-1) + e_h`` (NaN: the gate stays shut).
            rod_ub_Pa: The tracker's ``p_hat`` (the larger, the later the rod check opens).
            stroke_m: Stroke reading (NaN: the retract need takes both stroke ends).
            direction: +1 extension, -1 retraction; a change empties the line (spec 2.1).
        """
        if direction != self.direction[leg]:
            self.fill_m[leg] = 0.0
            self.is_open[leg] = False
            self.direction[leg] = direction
        if self.is_open[leg]:
            return True
        if direction > 0:
            is_open = self._extend_substep(leg, mean_valve_m_s, step_s, head_ub_Pa, rod_ub_Pa)
        else:
            is_open = self._retract_substep(leg, mean_valve_m_s, step_s, head_ub_Pa, stroke_m)
        self.is_open[leg] = is_open
        return is_open

    def _gate_factor(self, mean_valve_m_s: float) -> float:
        closing_speed_m_s = self.params.vent_closing_opening * self.max_speed_m_s
        return max(1.0 - abs(mean_valve_m_s) / closing_speed_m_s, 0.0)

    def line_pressure_Pa(self, leg: int) -> float:
        """``p_A`` of the extension line state."""
        params = self.params
        return params.tank_pressure_Pa + (self.fill_m[leg] * self.head_area_m2[leg]
                                          * params.hose_bulk_modulus_Pa / params.line_volume_m3)

    def _extend_substep(self, leg, mean_valve_m_s, step_s, head_ub_Pa, rod_ub_Pa) -> bool:
        params = self.params
        drain_m_s = (self.neutral_coefficient[leg] * self._gate_factor(mean_valve_m_s)
                     * math.sqrt(max(self.line_pressure_Pa(leg) - params.tank_pressure_Pa, 0.0))
                     / self.head_area_m2[leg])
        fill_rate_m_s = params.fill_speed_factor * max(mean_valve_m_s, 0.0) - drain_m_s
        self.fill_m[leg] = max(self.fill_m[leg] + fill_rate_m_s * step_s, 0.0)
        if not (math.isfinite(head_ub_Pa) and math.isfinite(rod_ub_Pa)):
            return False
        head_check_Pa = head_ub_Pa + params.crack_pressure_Pa
        rod_check_Pa = params.tank_pressure_Pa + (
            rod_ub_Pa + params.crack_pressure_Pa - params.tank_pressure_Pa) / params.pilot_ratio
        return self.line_pressure_Pa(leg) >= max(head_check_Pa, rod_check_Pa)

    def _retract_substep(self, leg, mean_valve_m_s, step_s, head_ub_Pa, stroke_m) -> bool:
        if not math.isfinite(head_ub_Pa):
            return False
        need_m, open_pressure_Pa = self.retract_need_m(leg, head_ub_Pa, stroke_m)
        self._last_need_array()[leg] = need_m
        rise_Pa = max(open_pressure_Pa - self.params.tank_pressure_Pa, 0.0)
        level = min(self.fill_m[leg] / need_m, 1.0) if need_m > 0.0 else 0.0
        drain_m_s = (self.neutral_coefficient[leg] * self._gate_factor(mean_valve_m_s)
                     * math.sqrt(rise_Pa * level) / self.annulus_area_m2[leg])
        fill_rate_m_s = self.params.fill_speed_factor * max(-mean_valve_m_s, 0.0) - drain_m_s
        self.fill_m[leg] = max(self.fill_m[leg] + fill_rate_m_s * step_s, 0.0)
        return self.fill_m[leg] >= need_m

    def _last_need_array(self) -> NDArray[np.float64]:
        """``need_ub`` of the last retract sub-step per leg (a gate pickled before it gets
        NaN values)."""
        if "last_need_m" not in self.__dict__:
            self.last_need_m = np.full(LEG_COUNT, np.nan)
        return self.last_need_m

    def last_retract_need_m(self, leg: int) -> float | None:
        """``need_ub`` of the leg's last retract sub-step (``carry_log``); None = none yet."""
        value = float(self._last_need_array()[leg])
        return value if math.isfinite(value) else None

    def retract_need_m(self, leg: int, head_ub_Pa: float, stroke_m: float) -> tuple[float, float]:
        """``(need_ub, p_open)`` of a retraction: the M1c ``retract_dead`` need at the
        conservative inputs (spec 2.4 with user decision 147: ``p_h_ub``, ``p_r`` = floor,
        ``F_band`` 0, void 0, ``beta`` 0.69 GPa, ``L0r`` 0.10 m, ``L0h`` 0.08 m). The need is
        non-decreasing in ``p_h`` and non-increasing in ``p_r``, ``F_band`` and the stroke
        (review 3.3, T-JR-03 grid), so a NaN stroke reading takes stroke 0."""
        key = (leg, float(head_ub_Pa), float(stroke_m))
        cached = self._need_cache.get(key)
        if cached is not None:
            return cached
        best_need_m, best_open_Pa = retract_need_upper_bound(
            self.params, head_ub_Pa, stroke_m, float(self.head_area_m2[leg]),
            float(self.annulus_area_m2[leg]), self.stroke_max_m)
        if len(self._need_cache) > NEED_CACHE_SIZE:
            self._need_cache.clear()
        self._need_cache[key] = (best_need_m, best_open_Pa)
        return best_need_m, best_open_Pa

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_need_cache"] = {}
        return state


NEED_CACHE_SIZE = 64
"""Retract needs kept per gate (one per leg and period in practice)."""


class ExtendStartTracker:
    """State ``(p, u_v)`` per leg and the period update (module docstring).

    Args:
        bound: The conservative parameters.
        geometry: Cylinder data.
        start_Pa: Initial ``p`` per leg (``p_ret``: the history is unknown, spec 3).
    """

    def __init__(self, bound: ExtendStartBound, geometry: BoundGeometry,
                 start_Pa: ArrayLike) -> None:
        self.bound = bound
        self.geometry = geometry
        self.pressure_Pa = np.array(start_Pa, dtype=float).reshape(LEG_COUNT)
        self.valve_m_s = np.zeros(LEG_COUNT)
        self.saturated_substeps = 0
        self.saturation_stop_periods = np.zeros(LEG_COUNT, dtype=np.int64)
        """Periods per leg without counted relief for a relief stop (revision 3, spec 10)."""
        self.previous_head_Pa: NDArray[np.float64] | None = None
        self.lock_seed_raises = np.zeros(LEG_COUNT, dtype=np.int64)
        """Extensions after a lock that raised ``p`` to the lock's ④ (revision 4)."""
        self._law = RodPressureFlowLaw()
        self._last_substep_saturated = False
        if bound.is_hold_revision:
            self._init_hold_state()
        if bound.is_witness_revision:
            self._init_release_state()

    def _init_release_state(self) -> None:
        """Revision 6 state (spec 4.2, 4.3); absent on a revision 4 or 5 tracker. It runs on
        every leg whatever its rod sensor state (4.5)."""
        self.release_evidence = np.zeros(LEG_COUNT, dtype=bool)
        """R5-9: release evidence in the leg's current retract run (relief from the next
        sub-step on)."""
        self.release_relief_ran = np.zeros(LEG_COUNT, dtype=bool)
        """R5-10: R5-9 was on in the leg's last retract run (kept through the hold after it)."""
        self.release_evidence_runs = np.zeros(LEG_COUNT, dtype=np.int64)
        """Retract runs that got release evidence (witness or gate opening)."""
        self.release_relief_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        """Sub-steps that counted the R5-9 relief (``jp3_r59_substeps`` per run)."""
        self.release_end_guard_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        """Sub-steps under release evidence that the retract end guard did not count (stroke
        reading at or below ``s_lo``; ``r59_end_guard_substeps``)."""
        self.release_nan_stroke_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        """Sub-steps under release evidence with a NaN stroke reading (not counted, the guard's
        conservative side; ``r59_nan_stroke_substeps``, kept apart from the end guard)."""
        self.period_nan_stroke_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        self.release_uncounted_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        """Sub-steps under release evidence without counted relief (any guard)."""
        self.period_relief_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        """:attr:`release_relief_substeps` of the last period (the per-read trace)."""
        self.period_end_guard_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        self._run_sign = np.zeros(LEG_COUNT)
        self._was_locked_period = np.ones(LEG_COUNT, dtype=bool)

    def _init_hold_state(self) -> None:
        """Revision 5 state (spec 2.1, 6.3 records); absent on a revision 4 tracker."""
        geometry = self.geometry
        self.gate = LineFillGateBound(self.bound.line_fill_gate, geometry.head_area_m2,
                                      geometry.annulus_area_m2, geometry.stroke_max_m,
                                      geometry.max_speed_m_s)
        self.retract_seed_raises = np.zeros(LEG_COUNT, dtype=np.int64)
        self.carry_raises = np.zeros(LEG_COUNT, dtype=np.int64)
        self.hold_periods = np.zeros(LEG_COUNT, dtype=np.int64)
        self.carry_periods = np.zeros(LEG_COUNT, dtype=np.int64)
        self.gate_open_substeps: list[list[int]] = [[] for _ in range(LEG_COUNT)]
        """Per leg the sub-steps from the carry start to the gate opening (Dg-2 delay)."""
        self.gate_never_opened_carries = np.zeros(LEG_COUNT, dtype=np.int64)
        """Carry runs that ended with a lock or a hold before the gate opened."""
        self._carry_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        self._was_carry = np.zeros(LEG_COUNT, dtype=bool)

    def raise_to(self, leg: int, pressure_Pa: float) -> None:
        """Revision 4: ``p <- max(p, pressure_Pa)`` at the start of an extension that ends a
        lock (``pressure_Pa`` = the monitor's model bound ④ of the lock; NaN = none, no
        change). Counted in ``lock_seed_raises`` when it raises ``p``."""
        if math.isfinite(pressure_Pa) and pressure_Pa > self.pressure_Pa[leg]:
            self.pressure_Pa[leg] = pressure_Pa
            self.lock_seed_raises[leg] += 1

    def seed_raise_to(self, leg: int, pressure_Pa: float, direction: float) -> bool:
        """Revision 5 R5-3: ``p <- max(p, ④)`` at the first carry period after a lock, in both
        directions (``lock_seed_raises`` for an extension, ``retract_seed_raises`` for a
        retraction). Returns whether ``p`` rose."""
        if not (math.isfinite(pressure_Pa) and pressure_Pa > self.pressure_Pa[leg]):
            return False
        self.pressure_Pa[leg] = pressure_Pa
        if direction > 0.0:
            self.lock_seed_raises[leg] += 1
        else:
            self.retract_seed_raises[leg] += 1
        return True

    def carry_raise_to(self, leg: int, pressure_Pa: float) -> None:
        """Revision 5 R5-4: ``p <- max(p, ④c)`` in every carry period (the plant may still be
        locked: ``p_hat`` follows the locked bound of the carried candidates)."""
        if math.isfinite(pressure_Pa) and pressure_Pa > self.pressure_Pa[leg]:
            self.pressure_Pa[leg] = pressure_Pa
            self.carry_raises[leg] += 1

    def bound_Pa(self, leg: int) -> float:
        """``p + delta_m``: the bound the start value and the moving estimate take."""
        return float(self.pressure_Pa[leg]) + self.bound.margin_Pa

    def compliance_m3_Pa(self, leg: int, stroke_m: float) -> float:
        """``h C_r(s)``; an unknown stroke takes ``s = 0`` (largest ``C_r``: ``A_h > A_ann``)."""
        bound, geometry = self.bound, self.geometry
        stroke = stroke_m if math.isfinite(stroke_m) else 0.0
        stroke = min(max(stroke, 0.0), geometry.stroke_max_m)
        head_area, annulus = geometry.head_area_m2[leg], geometry.annulus_area_m2[leg]
        head_stiffness = bound.bulk_modulus_Pa * head_area / (bound.head_dead_length_m + stroke)
        rod_stiffness = bound.bulk_modulus_Pa * annulus / (
            bound.rod_dead_length_m + geometry.stroke_max_m - stroke)
        return bound.hose_factor * self._law.rod_compliance_m3_Pa(annulus, head_stiffness,
                                                                  rod_stiffness)

    def ensure_hold_state(self) -> None:
        """Create the revision 5 state when a revision 5 bound meets a tracker built without it
        (a monitor pickled with revision 4, then refreshed: empty state, 10.4 ⑧ precedent).
        Every call checks the test-only rule values again (edition 4a 13.7: a pickle skips
        ``__post_init__``)."""
        if not self.bound.is_hold_revision:
            return
        self.bound.check_allowed()
        if "gate" not in self.__dict__:
            self._init_hold_state()
        if self.bound.is_witness_revision and "release_evidence" not in self.__dict__:
            self._init_release_state()

    def advance(self, command_m_s: ArrayLike, stroke_m: ArrayLike,
                retract_floor_Pa: ArrayLike, period_s: float,
                head_Pa: ArrayLike | None = None,
                period_class: Sequence[PeriodClass] | None = None,
                carry_bound_Pa: ArrayLike | None = None,
                release_floor_Pa: ArrayLike | None = None) -> None:
        """One controller period with the acting command ``command_m_s``.

        Args:
            command_m_s: Acting command per leg (the output of the previous period).
            stroke_m: Stroke reading per leg (NaN = unknown).
            retract_floor_Pa: ``max(p_ret, retract moving model)`` per leg.
            period_s: Controller period ``T``.
            head_Pa: Head pressure reading per leg of this period (the relief-stop test with
                the previous one, revision 3); None = no reading given (no stop counted).
            period_class: Revision 5 class per leg (module docstring); None = the revision 4
                period, line for line.
            carry_bound_Pa: Revision 5 ④c per leg of the carry periods (NaN elsewhere).
            release_floor_Pa: Revision 6 R5-9 floor term ``max(p_ret, 13 bar + p_h^ub / 3)``
                per leg at :meth:`release_head_bounds_Pa` (NaN = unknown: no floor raise);
                None = no floor term.
        """
        if period_class is not None:
            self._advance_classified(command_m_s, stroke_m, retract_floor_Pa, period_s,
                                     head_Pa, list(period_class), carry_bound_Pa,
                                     release_floor_Pa)
            return
        command = np.asarray(command_m_s, dtype=float)
        stroke = np.asarray(stroke_m, dtype=float)
        is_retracting = command < 0.0
        self.pressure_Pa = np.where(
            is_retracting, np.maximum(self.pressure_Pa, np.asarray(retract_floor_Pa, float)),
            self.pressure_Pa)
        compliance = [self.compliance_m3_Pa(leg, float(stroke[leg])) for leg in range(LEG_COUNT)]
        is_stopped = self._relief_stop(head_Pa)
        self.saturation_stop_periods += is_stopped & ~is_retracting
        is_at_end = np.isfinite(stroke) & (stroke >= self.bound.stroke_end_m)
        for _ in range(round(period_s / self.bound.substep_s)):
            self._substep(command, is_retracting, is_at_end | is_stopped, compliance)

    def _relief_stop(self, head_Pa: ArrayLike | None) -> NDArray[np.bool_]:
        """Spec 10 #1, #3: head reading of this period or the previous one at or above
        ``p_sat``, or NaN (a stop that starts inside the period shows in one of the two)."""
        if head_Pa is None:
            return np.zeros(LEG_COUNT, dtype=bool)
        head = np.asarray(head_Pa, dtype=float).reshape(LEG_COUNT)
        previous = self.previous_head_Pa
        self.previous_head_Pa = head.copy()
        readings = [head] if previous is None else [head, previous]
        is_stopped = np.zeros(LEG_COUNT, dtype=bool)
        for reading in readings:
            with np.errstate(invalid="ignore"):
                is_stopped |= ~(reading < self.bound.saturation_stop_head_Pa)
        return is_stopped

    def _advance_classified(self, command_m_s, stroke_m, retract_floor_Pa, period_s, head_Pa,
                            classes: list[PeriodClass], carry_bound_Pa,
                            release_floor_Pa=None) -> None:
        """Revision 5 period (module docstring table); revision 6 adds the R5-9 sub-steps."""
        self.ensure_hold_state()
        command = np.asarray(command_m_s, dtype=float)
        stroke = np.asarray(stroke_m, dtype=float)
        carry_bound = (np.full(LEG_COUNT, np.nan) if carry_bound_Pa is None
                       else np.asarray(carry_bound_Pa, dtype=float))
        is_carry = np.array([period_class.is_carry for period_class in classes])
        is_retracting = np.array([period_class.is_retracting for period_class in classes])
        is_hold = np.array([period_class is PeriodClass.HOLD for period_class in classes])
        is_witness = self.bound.is_witness_revision
        if is_witness:
            self._start_release_period(command, classes, is_carry)
        self._finish_carry_runs(is_carry)
        for leg in np.flatnonzero(is_carry):
            self.carry_raise_to(int(leg), float(carry_bound[leg]))
        for leg, period_class in enumerate(classes):
            if period_class.is_locked:
                self.gate.reset(leg)
        self.pressure_Pa = np.where(
            is_retracting, np.maximum(self.pressure_Pa, np.asarray(retract_floor_Pa, float)),
            self.pressure_Pa)
        self.hold_periods += is_hold
        self.carry_periods += is_carry
        compliance = [self.compliance_m3_Pa(leg, float(stroke[leg])) for leg in range(LEG_COUNT)]
        head_ub_Pa = self._gate_head_bound_Pa(head_Pa)
        relief = (self._release_period_inputs(head_Pa, release_floor_Pa, stroke, command)
                  if is_witness else None)
        is_stopped = self._relief_stop(head_Pa)
        self.saturation_stop_periods += is_stopped & ~is_retracting
        is_at_end = np.isfinite(stroke) & (stroke >= self.bound.stroke_end_m)
        is_gate_shut = is_carry & ~self.gate.is_open
        direction = np.where(command > 0.0, 1, -1)
        for _ in range(round(period_s / self.bound.substep_s)):
            skips_relief = is_retracting | is_hold | is_gate_shut
            mean_valve_m_s = self._substep(command, skips_relief, is_at_end | is_stopped,
                                           compliance)
            if relief is not None:
                self._release_substep(mean_valve_m_s, is_retracting, is_stopped, compliance,
                                      relief)
            for leg in np.flatnonzero(is_gate_shut):
                is_open = self._advance_gate(
                    int(leg), float(mean_valve_m_s[leg]), float(head_ub_Pa[leg]),
                    float(stroke[leg]), int(direction[leg]))
                is_gate_shut[leg] = not is_open
                if is_open and is_witness and direction[leg] < 0:
                    # R5-9 evidence: the gate opening, counted from the next sub-step on
                    self.note_release_evidence(int(leg))
        self._was_carry = is_carry

    # --- revision 6: R5-9 retract relief after release evidence (spec v5 4.2) ---

    def note_release_evidence(self, leg: int) -> None:
        """Release evidence of the leg's retract run (a retract-direction R5-8 witness, or the
        gate opening in a retract carry): R5-9 counts from the next sub-step on. A second piece
        of evidence in the same run changes nothing (the earlier one counts)."""
        if not self.bound.is_witness_revision or self.release_evidence[leg]:
            return
        self.release_evidence[leg] = True
        self.release_evidence_runs[leg] += 1

    def _nan_stroke_total_array(self) -> NDArray[np.int64]:
        if "release_nan_stroke_substeps" not in self.__dict__:  # a tracker of 8a3c48c7
            self.release_nan_stroke_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        return self.release_nan_stroke_substeps

    def _nan_stroke_period_array(self) -> NDArray[np.int64]:
        if "period_nan_stroke_substeps" not in self.__dict__:
            self.period_nan_stroke_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        return self.period_nan_stroke_substeps

    def release_head_bounds_Pa(self, head_Pa: ArrayLike
                               ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """``(p_h^lb, p_h^ub)`` per leg: the smaller / larger of this head reading and the
        previous one, minus / plus ``e_h`` (the previous one is the one :meth:`advance` keeps;
        read only, call it before :meth:`advance`)."""
        head = np.asarray(head_Pa, dtype=float).reshape(LEG_COUNT)
        previous = self.previous_head_Pa
        lower = head if previous is None else np.minimum(head, previous)
        upper = head if previous is None else np.maximum(head, previous)
        margin_Pa = self.bound.release_relief.head_reading_margin_Pa
        return lower - margin_Pa, upper + margin_Pa

    def _start_release_period(self, command: NDArray[np.float64], classes: list[PeriodClass],
                              is_carry: NDArray[np.bool_]) -> None:
        """Stop and reset of R5-9 (spec v5 4.2): a period with ``|u| <= u_hold`` (lock, hold)
        stops it; a sign change or a new run (the first moving period after a lock or hold, a
        new carry) clears the evidence and the R5-10 mark of the run before."""
        self.period_relief_substeps[:] = 0
        self.period_end_guard_substeps[:] = 0
        self._nan_stroke_period_array()[:] = 0
        for leg, period_class in enumerate(classes):
            if period_class.is_locked:
                self.release_evidence[leg] = False
                self._was_locked_period[leg] = True
                continue
            sign = math.copysign(1.0, float(command[leg]))
            is_new_carry = bool(is_carry[leg]) and not bool(self._was_carry[leg])
            if self._was_locked_period[leg] or sign != self._run_sign[leg] or is_new_carry:
                self.release_evidence[leg] = False
                self.release_relief_ran[leg] = False
            self._run_sign[leg] = sign
            self._was_locked_period[leg] = False

    def _release_period_inputs(self, head_Pa, release_floor_Pa, stroke, command
                               ) -> dict[str, NDArray[np.float64]]:
        """The R5-9 terms that hold over the period: ``f_lb``, ``p*_ub``, the floor term and the
        sub-steps that never count (retract end guard, tail cut)."""
        params = self.bound.release_relief
        geometry = self.geometry
        floor = (np.full(LEG_COUNT, np.nan) if release_floor_Pa is None
                 else np.asarray(release_floor_Pa, dtype=float).reshape(LEG_COUNT))
        if head_Pa is None:
            lower = upper = np.full(LEG_COUNT, np.nan)
        else:
            lower, upper = self.release_head_bounds_Pa(head_Pa)
        flow_factor = np.array([relief_flow_factor(float(value), params) for value in lower])
        target_ub = np.full(LEG_COUNT, np.nan)
        for leg in range(LEG_COUNT):
            if math.isfinite(upper[leg]):
                force_ub_N = (upper[leg] * geometry.head_area_m2[leg]
                              - params.rod_floor_Pa * geometry.annulus_area_m2[leg])
                target_ub[leg] = retract_target_rod_pressure_Pa(
                    force_ub_N, geometry.head_area_m2[leg], geometry.annulus_area_m2[leg], params)
        is_end_guard = np.isfinite(stroke) & (stroke <= params.retract_end_stroke_m)
        # a NaN stroke reading may be at the end: not counted either (the conservative side),
        # recorded apart from the end guard
        is_nan_stroke = ~np.isfinite(stroke)
        is_tail_cut = np.abs(command) <= ZERO_COMMAND_M_S
        return {"flow_factor": flow_factor, "target_ub_Pa": target_ub, "floor_Pa": floor,
                "is_end_guard": is_end_guard, "is_nan_stroke": is_nan_stroke,
                "is_tail_cut": is_tail_cut}

    def _release_substep(self, mean_valve_m_s: NDArray[np.float64],
                         is_retracting: NDArray[np.bool_], is_stopped: NDArray[np.bool_],
                         compliance: list[float], relief: dict[str, NDArray[np.float64]]) -> None:
        """One R5-9 sub-step on the retracting legs with release evidence::

            p <- max(p - A_ann kappa_x |u_v| f_lb dt / (h C_r(s)),
                     p*_ub + (p - p*_ub) exp(-dt / tau), floor)

        A sub-step of pump saturation, of a head reading at the relief stop or NaN, of a zero
        acting command or at the retract end takes the floor term only."""
        bound, geometry = self.bound, self.geometry
        step_s = bound.substep_s
        keep = math.exp(-step_s / bound.lag_s) if bound.lag_s > 0.0 else 0.0
        for leg in np.flatnonzero(is_retracting & self.release_evidence):
            pressure_Pa = float(self.pressure_Pa[leg])
            floor_Pa = float(relief["floor_Pa"][leg])
            floor_Pa = floor_Pa if math.isfinite(floor_Pa) else -math.inf
            is_end_guard = bool(relief["is_end_guard"][leg])
            is_nan_stroke = bool(relief["is_nan_stroke"][leg])
            is_counted = not (self._last_substep_saturated or bool(is_stopped[leg])
                              or bool(relief["is_tail_cut"][leg]) or is_end_guard
                              or is_nan_stroke)
            self.release_relief_ran[leg] = True
            if not is_counted:
                self.pressure_Pa[leg] = max(pressure_Pa, floor_Pa)
                self.release_uncounted_substeps[leg] += 1
                if is_end_guard:
                    self.release_end_guard_substeps[leg] += 1
                    self.period_end_guard_substeps[leg] += 1
                if is_nan_stroke:
                    self._nan_stroke_total_array()[leg] += 1
                    self._nan_stroke_period_array()[leg] += 1
                continue
            drop_Pa = (geometry.annulus_area_m2[leg] * bound.speed_factor
                       * abs(float(mean_valve_m_s[leg])) * float(relief["flow_factor"][leg])
                       * step_s / compliance[leg])
            target_Pa = float(relief["target_ub_Pa"][leg])
            lag_Pa = target_Pa + (pressure_Pa - target_Pa) * keep
            self.pressure_Pa[leg] = max(pressure_Pa - drop_Pa, lag_Pa, floor_Pa)
            self.release_relief_substeps[leg] += 1
            self.period_relief_substeps[leg] += 1

    def _finish_carry_runs(self, is_carry: NDArray[np.bool_]) -> None:
        """A carry run that ends in a lock or hold period without the gate opened counts in
        ``gate_never_opened_carries``; a new carry run restarts its sub-step count."""
        for leg in range(LEG_COUNT):
            if is_carry[leg] and not self._was_carry[leg]:
                self._carry_substeps[leg] = 0
            ended = self._was_carry[leg] and not is_carry[leg]
            if ended and not self.gate.is_open[leg]:
                self.gate_never_opened_carries[leg] += 1

    def _gate_head_bound_Pa(self, head_Pa: ArrayLike | None) -> NDArray[np.float64]:
        """``p_h_ub = max(p_h,k, p_h,k-1) + e_h``; NaN when this reading (or a given previous
        one) is NaN or no head reading came (the gate stays shut)."""
        if head_Pa is None:
            return np.full(LEG_COUNT, np.nan)
        head = np.asarray(head_Pa, dtype=float).reshape(LEG_COUNT)
        previous = self.previous_head_Pa
        upper = head if previous is None else np.maximum(head, previous)
        return upper + self.bound.line_fill_gate.head_reading_margin_Pa

    def _advance_gate(self, leg: int, mean_valve_m_s: float, head_ub_Pa: float,
                      stroke_m: float, direction: int) -> bool:
        """One gate sub-step of a carry leg; records the delay when it opens."""
        self._carry_substeps[leg] += 1
        is_open = self.gate.advance_substep(leg, mean_valve_m_s, self.bound.substep_s,
                                            head_ub_Pa, float(self.pressure_Pa[leg]), stroke_m,
                                            direction)
        if is_open and len(self.gate_open_substeps[leg]) < MAX_RECORDED_GATE_OPENINGS:
            self.gate_open_substeps[leg].append(int(self._carry_substeps[leg]))
        return is_open

    def _substep(self, command, is_retracting, is_at_end, compliance) -> NDArray[np.float64]:
        """One relief sub-step; ``is_retracting`` marks the legs that count no relief (revision
        4: the retracting legs). Returns the mean valve estimate of the sub-step."""
        bound, geometry = self.bound, self.geometry
        step_s = bound.substep_s
        start_valve_m_s = self.valve_m_s
        mean_valve_m_s = self._advance_valve(command, step_s)
        demand_m3_s = self._pump_demand_m3_s(start_valve_m_s, self.valve_m_s)
        is_saturated = demand_m3_s > bound.volumetric_efficiency * bound.pump_flow_m3_s
        self.saturated_substeps += int(is_saturated)
        self._last_substep_saturated = is_saturated  # the R5-9 sub-step of revision 6 reads it
        cut_m_s = bound.overlap_cut_ratio * geometry.max_speed_m_s
        for leg in range(LEG_COUNT):
            if is_retracting[leg]:
                continue
            valve = float(self.valve_m_s[leg])
            # The plant closes the tail only with a zero acting command (spec L-6); a valve
            # still negative after a retract fills, so it never counts relief.
            is_tail_cut = abs(command[leg]) <= ZERO_COMMAND_M_S and valve < cut_m_s
            counts_relief = (valve > 0.0 and not is_tail_cut and not is_saturated
                             and not is_at_end[leg])
            mean_speed_m_s = max(float(mean_valve_m_s[leg]), 0.0)
            speed_m_s = bound.speed_factor * mean_speed_m_s if counts_relief else 0.0
            self.pressure_Pa[leg] = flow_limited_rod_pressure(
                float(self.pressure_Pa[leg]), bound.back_pressure_Pa, speed_m_s, step_s,
                bound.lag_s, compliance[leg], geometry.head_area_m2[leg],
                geometry.annulus_area_m2[leg], False)
        return mean_valve_m_s

    def _advance_valve(self, command: NDArray[np.float64], step_s: float
                       ) -> NDArray[np.float64]:
        """Move ``u_v`` to the end of the sub-step; return its exact mean over the sub-step."""
        tau_s = self.geometry.valve_tau_s
        start_m_s = self.valve_m_s
        if tau_s <= 0.0:
            self.valve_m_s = np.array(command, dtype=float)
            return self.valve_m_s.copy()
        keep = math.exp(-step_s / tau_s)
        self.valve_m_s = command + (start_m_s - command) * keep
        return command + (start_m_s - command) * (tau_s / step_s) * (1.0 - keep)

    def _pump_demand_m3_s(self, start_valve_m_s: NDArray[np.float64],
                          end_valve_m_s: NDArray[np.float64]) -> float:
        """``sum A |u_v|`` with per leg the larger demand of the sub-step start and end: on a
        falling valve the end value alone misses a saturation early in the sub-step (spec 3
        (ii), v2 review)."""
        return float(np.sum(np.maximum(self._leg_demand_m3_s(start_valve_m_s),
                                       self._leg_demand_m3_s(end_valve_m_s))))

    def _leg_demand_m3_s(self, valve_m_s: NDArray[np.float64]) -> NDArray[np.float64]:
        head = np.asarray(self.geometry.head_area_m2)
        annulus = np.asarray(self.geometry.annulus_area_m2)
        return np.where(valve_m_s > 0.0, head * valve_m_s, -annulus * valve_m_s)

    def record(self) -> dict[str, object]:
        """The state and counters (meta ``extend_start_record``); the revision 5 keys only on a
        revision 5 tracker."""
        record: dict[str, object] = {
            "extend_bound_Pa": self.pressure_Pa.tolist(),
            "valve_estimate_m_s": self.valve_m_s.tolist(),
            "saturated_substeps": self.saturated_substeps,
            "saturation_stop_periods": self.saturation_stop_periods.tolist(),
            "lock_seed_raises": self.lock_seed_raises.tolist()}
        if self.bound.is_hold_revision and "gate" in self.__dict__:
            record.update({
                "rule_revision": self.bound.revision,
                "retract_seed_raises": self.retract_seed_raises.tolist(),
                "carry_raises": self.carry_raises.tolist(),
                "hold_periods": self.hold_periods.tolist(),
                "carry_periods": self.carry_periods.tolist(),
                "gate_open_substeps": [list(values) for values in self.gate_open_substeps],
                "gate_never_opened_carries": self.gate_never_opened_carries.tolist()})
        if self.bound.is_witness_revision and "release_evidence" in self.__dict__:
            record.update({
                "release_evidence_runs": self.release_evidence_runs.tolist(),
                "r59_substeps": self.release_relief_substeps.tolist(),
                "r59_end_guard_substeps": self.release_end_guard_substeps.tolist(),
                "r59_nan_stroke_substeps": self._nan_stroke_total_array().tolist(),
                "r59_uncounted_substeps": self.release_uncounted_substeps.tolist()})
        return record


MAX_RECORDED_GATE_OPENINGS = 2000
"""Per leg cap of ``gate_open_substeps``."""


TENSION_READ_SIGMA_PA = 0.20e5
"""ASSUMPTION: white noise of one pressure reading, normal grade (``pressure_error`` table, spec
71); the static errors are removed by the zero offsets, not by this margin."""
TENSION_READ_K = 3.0
"""ASSUMPTION: the read margin is ``k sigma_F``, ``sigma_F = sigma sqrt(A_h^2 + A_ann^2)``
(hydraulics-expert ``tension_premise.md`` 4, S-1)."""
TENSION_RULE = "zero_corrected_3sigma"
"""``review_record.tension_rule``; a record without it is the raw-reading count of 83e8a36 and
earlier (judged invalid)."""


class PremiseRecord:
    """Review records of the bound's premises, kept with the ③ option on or off (criteria
    rev. 6 14.5, hydraulics-expert ③ review 2026-11-07; user decision 2026-11-07). Records only:
    nothing here feeds a command. The premise itself is judged on the plant truth
    (:class:`TensionTruthCounter`); these are the controller's readings, kept for the machine.

    * ``tension_substeps``: 1 ms sub-steps of an extending, zero-calibrated leg whose net force
      reading (zero offset removed) pulls beyond ``p_bB A_ann`` plus the read margin
      ``k sigma_F`` (front 828 N, rear 600 N); ``tension_substeps_uncalibrated`` the same for a
      leg without a zero offset (its static sensor error is still in the reading).
    * ``d2_violation_start_ratio``: stroke rate over the acting command at each D2 violation
      start (priority saturation shows as 1-2 % ``v_max`` delivered; ``None`` = no rate).

    Args:
        head_area_m2: ``A_h`` per leg.
        annulus_area_m2: ``A_ann`` per leg.
    """

    def __init__(self, head_area_m2: ArrayLike, annulus_area_m2: ArrayLike) -> None:
        head = np.asarray(head_area_m2, dtype=float).reshape(LEG_COUNT)
        annulus = np.asarray(annulus_area_m2, dtype=float).reshape(LEG_COUNT)
        self.tension_read_margin_N = (TENSION_READ_K * TENSION_READ_SIGMA_PA
                                      * np.sqrt(head**2 + annulus**2))
        self.tension_threshold_N = BOUND_BACK_PRESSURE_PA * annulus + self.tension_read_margin_N
        self.tension_substeps = np.zeros(LEG_COUNT, dtype=np.int64)
        self.tension_substeps_uncalibrated = np.zeros(LEG_COUNT, dtype=np.int64)
        self.d2_start_ratios: list[list[float | None]] = [[] for _ in range(LEG_COUNT)]

    def count_tension(self, command_m_s: ArrayLike, net_force_N: ArrayLike,
                      is_calibrated: ArrayLike, period_s: float) -> None:
        """One controller period: the net force reading holds over its 1 ms sub-steps.

        Args:
            command_m_s: Acting command per leg.
            net_force_N: ``p_h A_h - p_r A_ann - c_i`` per leg (``c_i`` 0 if not calibrated).
            is_calibrated: The leg has a zero offset.
            period_s: Controller period.
        """
        is_pulled = ((np.asarray(command_m_s, float) > 0.0)
                     & (np.asarray(net_force_N, float) < -self.tension_threshold_N))
        calibrated = np.asarray(is_calibrated, bool)
        substeps = round(period_s / BOUND_SUBSTEP_S)
        self.tension_substeps += substeps * (is_pulled & calibrated)
        self.tension_substeps_uncalibrated += substeps * (is_pulled & ~calibrated)

    def add_d2_start(self, leg: int, stroke_rate_m_s: float | None,
                     command_m_s: float) -> None:
        is_known = stroke_rate_m_s is not None and math.isfinite(stroke_rate_m_s)
        self.d2_start_ratios[leg].append(
            float(stroke_rate_m_s) / command_m_s if is_known else None)

    def to_meta(self) -> dict[str, object]:
        return {"tension_rule": TENSION_RULE,
                "tension_substeps": self.tension_substeps.tolist(),
                "tension_substeps_uncalibrated": self.tension_substeps_uncalibrated.tolist(),
                "tension_threshold_N": self.tension_threshold_N.tolist(),
                "tension_read_margin_N": self.tension_read_margin_N.tolist(),
                "d2_violation_start_ratio": [list(ratios) for ratios in self.d2_start_ratios]}


TENSION_TRUTH_RULE = ("plant p* > p_bB on an unlocked leg with valve > 0, per 1 ms; "
                      "diagnostic; judged by extend_bound_check")


class TensionTruthCounter:
    """Plant truth of premise ① (``tension_premise.md`` 4, S-2), a **diagnostic** record since
    5.4: the bound is judged by :class:`ExtendBoundCheck`. Time an extending leg spends with the
    plant's extend target ``p*`` above ``p_bB``, kept by the plant adapters (harness, L2b) and
    recorded as ``hydraulics_record.tension_truth``. ``active_substeps`` = the part where ``p*``
    is also above the plant rod pressure ``p_tr`` (the target holds the plant up: the case that
    can break the bound; a break-away after a retract lock relieves from above, 5.2). Records
    only.

    The adapters add every plant step (1 ms harness chunk, L2b step); the counts are the summed
    time in 1 ms sub-steps.
    """

    def __init__(self) -> None:
        self.seconds = np.zeros(LEG_COUNT)
        self.seconds_over_margin = np.zeros(LEG_COUNT)
        self.seconds_active = np.zeros(LEG_COUNT)
        self.max_excess_Pa = np.zeros(LEG_COUNT)
        self.min_plant_minus_target_Pa = np.full(LEG_COUNT, np.inf)
        self.first_t_s: list[float | None] = [None] * LEG_COUNT

    def add(self, is_extending: ArrayLike, target_Pa: ArrayLike, duration_s: float,
            t_s: float, plant_rod_Pa: ArrayLike | None = None) -> None:
        """One plant step.

        Args:
            is_extending: Unlocked leg with a valve speed > 0 in this step.
            target_Pa: Plant extend target ``p*`` per leg (gauge; NaN = not extending).
            duration_s: Step length.
            t_s: Plant time at the step end.
            plant_rod_Pa: Plant rod pressure ``p_tr`` per leg (None = not known: no
                ``active_substeps``).
        """
        extending = np.asarray(is_extending, bool)
        if not extending.any():
            return
        target = np.asarray(target_Pa, float)
        with np.errstate(invalid="ignore"):
            excess_Pa = np.where(extending, target - BOUND_BACK_PRESSURE_PA, -np.inf)
        over = excess_Pa > 0.0
        if not over.any():
            return
        self.seconds += duration_s * over
        self.seconds_over_margin += duration_s * (excess_Pa > BOUND_MARGIN_PA)
        self.max_excess_Pa = np.where(over, np.maximum(self.max_excess_Pa, excess_Pa),
                                      self.max_excess_Pa)
        if plant_rod_Pa is not None:
            plant_minus_target_Pa = np.asarray(plant_rod_Pa, float) - target
            with np.errstate(invalid="ignore"):
                self.seconds_active += duration_s * (over & (plant_minus_target_Pa < 0.0))
                self.min_plant_minus_target_Pa = np.where(
                    over, np.fmin(self.min_plant_minus_target_Pa, plant_minus_target_Pa),
                    self.min_plant_minus_target_Pa)
        for leg in np.flatnonzero(over):
            if self.first_t_s[leg] is None:
                self.first_t_s[leg] = round(float(t_s), 6)

    def record(self) -> dict[str, object]:
        known = np.isfinite(self.min_plant_minus_target_Pa)
        return {"rule": TENSION_TRUTH_RULE,
                "substeps": _substeps(self.seconds),
                "substeps_over_margin": _substeps(self.seconds_over_margin),
                "active_substeps": _substeps(self.seconds_active),
                "max_excess_bar": (self.max_excess_Pa / BAR_PA).tolist(),
                "min_p_tr_minus_p_star_bar": [
                    float(value) / BAR_PA if is_known else None
                    for value, is_known in zip(self.min_plant_minus_target_Pa, known,
                                               strict=True)],
                "first_t_s": list(self.first_t_s),
                "back_pressure_bar": BOUND_BACK_PRESSURE_PA / BAR_PA,
                "margin_bar": BOUND_MARGIN_PA / BAR_PA}


def _substeps(seconds: NDArray[np.float64]) -> list[int]:
    return [round(value / BOUND_SUBSTEP_S) for value in seconds.tolist()]


EXTEND_BOUND_CHECK_RULE = (
    "③-on rows (tension_premise.md 5.4, 6.3), plant rod pressure p_tr at every controller "
    "read. ext_moving (judged): breach_reads = p_tr > p_hat + delta_m, the sum must be 0; "
    "margin_used_reads = p_tr > p_hat is a FLAG. ext_locked: judged by the VB T4h replay "
    "(t4h_replay with the ③-on setting, over_0p6kN == 0); here a cross-check FLAG "
    "against the monitor's model bound ④ (before the reading bound ⑤): locked_breach_reads = "
    "p_tr > ④, locked_breach_over_tol_reads = p_tr > ④ + 0.6 kN / A_ann (the T4h tolerance; > 0 "
    "is a FLAG, a VB T4h disagreement is a replay mismatch); locked_vs_extend_bound_reads = "
    "p_tr > p_hat + delta_m on locked legs, diagnostic only. 1 Pa rounding allowance; "
    "retracting legs apart (premise ④); null record = option off or no rod reading")


BOUND_CHECK_TOLERANCE_PA = 1.0
"""Rounding allowance of :class:`ExtendBoundCheck`: in a steady extension the plant lag and the
bound's ``p_hat`` both converge to ``p_bB`` and differ by float rounding only (ASSUMPTION,
1 Pa = 1e-5 bar, far below any physical margin)."""


class ExtendBoundState(StrEnum):
    """Leg state of one bound comparison (``min_gap_state``)."""

    EXTEND_MOVING = "ext_moving"
    EXTEND_LOCKED = "ext_locked"
    RETRACT = "retract"


LOCKED_CHECK_TOLERANCE_N = 600.0
"""The T4h tolerance (criteria 9: lower bound <= truth + 0.6 kN), as a rod pressure
``0.6 kN / A_ann`` in ``locked_breach_over_tol_reads``."""


class ExtendBoundCheck:
    """The ③ bound against the plant at the controller reads (``tension_premise.md`` 5.5,
    6.4), kept by the plant adapters as ``hydraulics_record.extend_bound_check``. Records only;
    the judgement of the keys is :data:`EXTEND_BOUND_CHECK_RULE`.

    * ``ext_moving`` (moving while extending): ``p_tr`` against ``p_hat + delta_m``
      (``reads``, ``breach_reads``, ``margin_used_reads``, ``min_gap_*``,
      ``first_breach_t_s``).
    * ``ext_locked`` (locked after an extension): ``p_tr`` against the monitor's model bound ④
      (``locked_*``; its locked law follows the load after the lock, which ``p_hat`` does not),
      and against ``p_hat + delta_m`` as a diagnostic (``locked_vs_extend_bound_reads``).
    * ``retract``: apart (premise ④). A leg locked after a retraction is not compared.

    Args:
        annulus_area_m2: ``A_ann`` per leg (the 0.6 kN tolerance as a pressure).
    """

    def __init__(self, annulus_area_m2: ArrayLike) -> None:
        annulus = np.asarray(annulus_area_m2, dtype=float).reshape(LEG_COUNT)
        self.locked_tolerance_Pa = LOCKED_CHECK_TOLERANCE_N / annulus
        self.reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.breach_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.margin_used_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.min_gap_Pa = np.full(LEG_COUNT, np.inf)
        self.min_gap_t_s: list[float | None] = [None] * LEG_COUNT
        self.first_breach_t_s: list[float | None] = [None] * LEG_COUNT
        self.locked_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.locked_unpaired_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        """Locked plant leg without an open monitor lock stretch (no ④ to compare)."""
        self.locked_breach_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.locked_breach_over_tol_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.locked_vs_extend_bound_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.locked_min_gap_Pa = np.full(LEG_COUNT, np.inf)
        self.locked_min_gap_t_s: list[float | None] = [None] * LEG_COUNT
        self.locked_bound_source: list[str | None] = [None] * LEG_COUNT
        self.retract_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.retract_breach_reads = np.zeros(LEG_COUNT, dtype=np.int64)

    rev5: ExtendBoundCheckRev5 | None = None
    """Revision 5 J-P3 counters (436.9, spec 6.2 / 6.3); created by the first read that brings
    the monitor's period classes (class default: checks pickled before it have none)."""
    sensor_grade: str | None = None
    """Pressure sensor grade of the row (:data:`SENSOR_GRADES`; revision 5 record keys
    ``sensor_grade`` and ``jp3_judged_row``); the plant adapter sets it, None = not declared."""

    def add(self, t_s: float, bound_Pa: ArrayLike, plant_rod_Pa: ArrayLike,
            states: list[ExtendBoundState | None],
            locked_model_bound_Pa: ArrayLike | None = None,
            locked_sources: list[str | None] | None = None,
            period_classes: Sequence[PeriodClass | str | None] | None = None,
            used_bounds: ArrayLike | None = None,
            plant_states: Sequence[str] | None = None,
            trace_row: Mapping[str, Any] | None = None,
            p_star_ret_Pa: ArrayLike | None = None,
            true_force_N: ArrayLike | None = None) -> None:
        """One controller read.

        Args:
            t_s: Read time.
            bound_Pa: The controller's ``p_hat + delta_m`` per leg.
            plant_rod_Pa: Plant rod pressure ``p_tr`` per leg at the read.
            states: Leg state per leg; None = not compared (locked after a retraction).
            locked_model_bound_Pa: The monitor's ④ per leg (NaN = no open lock stretch);
                None = not given (locked legs then count as unpaired).
            locked_sources: The ``M_j`` source behind each ④.
            period_classes: Revision 5: the monitor's class per leg of this read; None = the
                revision 4 record only (no revision 5 key).
            used_bounds: Revision 5: the estimate the monitor used per leg (spec 6.2).
            plant_states: Revision 5: :data:`PLANT_STATES` value per leg.
            trace_row: Revision 5: the monitor's ``extend_bound_trace_row()`` (per-read trace).
            p_star_ret_Pa: Revision 5: the plant retract target ``p*_ret(F)`` per leg at the
                read (2nd edition 6.2: the trapped and the fill share of J-P3c and RET).
            true_force_N: Revision 5: the plant net force per leg (edition 4.1 false-drop
                count); None = unknown.
        """
        if period_classes is not None:
            if self.rev5 is None:
                self.rev5 = ExtendBoundCheckRev5(self.locked_tolerance_Pa, self.sensor_grade)
            self.rev5.add(t_s, period_classes, used_bounds, plant_rod_Pa, plant_states,
                          trace_row, p_star_ret_Pa, true_force_N)
        bound = np.asarray(bound_Pa, float)
        plant = np.asarray(plant_rod_Pa, float)
        model = (np.full(LEG_COUNT, np.nan) if locked_model_bound_Pa is None
                 else np.asarray(locked_model_bound_Pa, float))
        sources = locked_sources or [None] * LEG_COUNT
        for leg, state in enumerate(states):
            if state is None or not math.isfinite(plant[leg]):
                continue
            gap_Pa = float(bound[leg] - plant[leg])
            is_breach = gap_Pa < -BOUND_CHECK_TOLERANCE_PA
            if state is ExtendBoundState.RETRACT:
                self.retract_reads[leg] += 1
                self.retract_breach_reads[leg] += int(is_breach)
            elif state is ExtendBoundState.EXTEND_LOCKED:
                self.locked_vs_extend_bound_reads[leg] += int(is_breach)
                self._add_locked(leg, t_s, float(model[leg]) - float(plant[leg]), sources[leg])
            else:
                self._add_moving(leg, t_s, gap_Pa, is_breach)

    def _add_moving(self, leg: int, t_s: float, gap_Pa: float, is_breach: bool) -> None:
        self.reads[leg] += 1
        self.breach_reads[leg] += int(is_breach)
        self.margin_used_reads[leg] += int(gap_Pa < BOUND_MARGIN_PA - BOUND_CHECK_TOLERANCE_PA)
        if is_breach and self.first_breach_t_s[leg] is None:
            self.first_breach_t_s[leg] = round(float(t_s), 6)
        if gap_Pa < self.min_gap_Pa[leg]:
            self.min_gap_Pa[leg] = gap_Pa
            self.min_gap_t_s[leg] = round(float(t_s), 6)

    def _add_locked(self, leg: int, t_s: float, gap_Pa: float, source: str | None) -> None:
        if not math.isfinite(gap_Pa):
            self.locked_unpaired_reads[leg] += 1
            return
        self.locked_reads[leg] += 1
        self.locked_breach_reads[leg] += int(gap_Pa < -BOUND_CHECK_TOLERANCE_PA)
        self.locked_breach_over_tol_reads[leg] += int(gap_Pa < -self.locked_tolerance_Pa[leg])
        if gap_Pa < self.locked_min_gap_Pa[leg]:
            self.locked_min_gap_Pa[leg] = gap_Pa
            self.locked_min_gap_t_s[leg] = round(float(t_s), 6)
            self.locked_bound_source[leg] = source

    def record(self) -> dict[str, object]:
        record = self._revision_4_record()
        if self.rev5 is not None:
            record.update(self.rev5.record())
        return record

    def trace_arrays(self) -> dict[str, NDArray[Any]] | None:
        """Revision 5 per-read arrays for the T4h npz (spec 6.3); None on a revision 4 run."""
        return None if self.rev5 is None else self.rev5.trace.arrays()

    def _revision_4_record(self) -> dict[str, object]:
        return {"rule": EXTEND_BOUND_CHECK_RULE,
                "reads": self.reads.tolist(),
                "breach_reads": self.breach_reads.tolist(),
                "margin_used_reads": self.margin_used_reads.tolist(),
                "min_gap_bar": _bar_or_none(self.min_gap_Pa),
                "min_gap_t_s": list(self.min_gap_t_s),
                "first_breach_t_s": list(self.first_breach_t_s),
                "locked_reads": self.locked_reads.tolist(),
                "locked_unpaired_reads": self.locked_unpaired_reads.tolist(),
                "locked_breach_reads": self.locked_breach_reads.tolist(),
                "locked_breach_over_tol_reads": self.locked_breach_over_tol_reads.tolist(),
                "locked_min_gap_bar": _bar_or_none(self.locked_min_gap_Pa),
                "locked_min_gap_t_s": list(self.locked_min_gap_t_s),
                "locked_bound_source": list(self.locked_bound_source),
                "locked_tolerance_bar": (self.locked_tolerance_Pa / BAR_PA).tolist(),
                "locked_vs_extend_bound_reads": self.locked_vs_extend_bound_reads.tolist(),
                "retract_reads": self.retract_reads.tolist(),
                "retract_breach_reads": self.retract_breach_reads.tolist()}


PLANT_STATES = ("moving_ext", "moving_ret", "locked_ext", "locked_ret")
"""Plant leg states of the revision 5 record (a record column, not a judged set; spec 6.2)."""
PLANT_STATE_CODES = {state: code for code, state in enumerate(PLANT_STATES)}
JP3_SOURCE_NAMES = ("extend_bound", "pilot_model", "previous_moving", "retract_hold",
                    "retract_tracker")
"""Table of ``jp3_model_bound_source`` (the ``LockStartSource`` values of ``two_pressure`` in
their order; edition 4 J4a-4 appends ``retract_tracker`` at the end)."""
JP3_SOURCE_CODES = {name: code for code, name in enumerate(JP3_SOURCE_NAMES)}
RETRACT_TRACKER_SOURCE = "retract_tracker"
MAX_RETRACT_TRACKER_STRETCH_ROWS = 2000
TRACE_EXCERPT_GAP_PA = 2.0e5
"""Spec 6.3: an excerpt row is a read with a gap below 2 bar, a breach or a class change."""
TRACE_EXCERPT_CONTEXT_READS = 2
MAX_TRACE_EXCERPT_ROWS = 2000
EXTEND_BOUND_CHECK_REV5_RULE = (
    "436.9 J-P3 (jp3_remedy_spec.md 6.2): reads classified by the estimate the monitor used. "
    "jp3a (ext + carry_ext): p_tr > p_hat + delta_m, 1 Pa (judged); jp3b (hold): p_tr > ④ + "
    "0.6 kN / A_ann (judged; 1 Pa strict = FLAG); jp3c (carry_ret): p_tr > max(p_hat + delta_m, "
    "retract model), 1 Pa (judged); lock_ext (lock, plant locked after an extension): ④ cross-"
    "check FLAG; lock_ret, ret: records")


def plant_leg_states(is_locked: ArrayLike, last_direction: ArrayLike) -> list[str]:
    """:data:`PLANT_STATES` value per leg from the plant lock state and the sign of its last
    moving direction (> 0 extension)."""
    states = []
    for locked, direction in zip(np.asarray(is_locked, bool), np.asarray(last_direction, float),
                                 strict=True):
        kind = "ext" if direction > 0.0 else "ret"
        states.append(f"{'locked' if locked else 'moving'}_{kind}")
    return states


class _GapCounter:
    """Per-leg counts of one comparison ``gap = bound - p_tr`` (breach below -1 Pa)."""

    def __init__(self, tolerance_Pa: NDArray[np.float64] | None = None) -> None:
        self.tolerance_Pa = tolerance_Pa
        self.reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.unpaired_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.breach_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.over_tol_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.margin_used_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.min_gap_Pa = np.full(LEG_COUNT, np.inf)
        self.min_gap_t_s: list[float | None] = [None] * LEG_COUNT
        self.first_breach_t_s: list[float | None] = [None] * LEG_COUNT

    def add(self, leg: int, t_s: float, gap_Pa: float) -> bool:
        """Count one read; returns whether it breached (False for an unpaired read)."""
        if not math.isfinite(gap_Pa):
            self.unpaired_reads[leg] += 1
            return False
        self.reads[leg] += 1
        is_breach = gap_Pa < -BOUND_CHECK_TOLERANCE_PA
        self.breach_reads[leg] += int(is_breach)
        if self.tolerance_Pa is not None:
            self.over_tol_reads[leg] += int(gap_Pa < -self.tolerance_Pa[leg])
        self.margin_used_reads[leg] += int(gap_Pa < BOUND_MARGIN_PA - BOUND_CHECK_TOLERANCE_PA)
        if is_breach and self.first_breach_t_s[leg] is None:
            self.first_breach_t_s[leg] = round(float(t_s), 6)
        if gap_Pa < self.min_gap_Pa[leg]:
            self.min_gap_Pa[leg] = gap_Pa
            self.min_gap_t_s[leg] = round(float(t_s), 6)
        return is_breach

    def max_excess_bar(self) -> list[float | None]:
        """Largest ``p_tr - bound`` per leg (None without reads)."""
        return [None if not math.isfinite(gap) else max(-float(gap), 0.0) / BAR_PA
                for gap in self.min_gap_Pa]


class ExtendBoundTrace:
    """Revision 5 per-read trace (spec 6.3): the full arrays of the T4h npz and the excerpt of
    the ``extend_bound_check`` record."""

    EXCERPT_COLUMNS = ("t_s", "leg", "class", "plant_state", "u_m_s", "used_bound_Pa",
                       "ext_bound_Pa", "model_bound_Pa", "p_tr_Pa", "p_star_ret_Pa",
                       "head_read_Pa", "gap_Pa", "gate_open", "model_source", "model_age_s")
    PER_LEG_FIELDS = ("u_m_s", "ext_bound_Pa", "model_bound_Pa", "carry_bound_Pa",
                      "used_bound_Pa", "p_tr_Pa", "p_star_ret_Pa", "head_read_Pa",
                      "gate_fill_m", "model_bound_age_s", "model_bound_head_Pa",
                      "ret_after_gate_s")
    REVISION_6_FIELDS = {"r58_witness": bool, "r59_substeps": np.int32,
                         "r510_candidates": np.int32, "r59_end_guard_substeps": np.int32,
                         "r59_nan_stroke_substeps": np.int32}
    """Revision 6 per-read coverage columns (``jp3_<name>`` arrays; spec v5 6.3.9), kept only
    when the monitor's rows carry them (a revision 5 trace has none)."""

    rev6_values: dict[str, list[list[Any]]] | None = None
    """Revision 6 columns per read (class default None: a trace without them)."""

    def __init__(self) -> None:
        self.t_s: list[float] = []
        self.classes: list[list[int]] = []
        self.plant_states: list[list[int]] = []
        self.gate_open: list[list[bool]] = []
        self.sources: list[list[int]] = []
        """Edition 4 per-read ``jp3_model_bound_source`` (:data:`JP3_SOURCE_CODES`, -1 none)."""
        self.inherited: list[list[bool]] = []
        self.values: dict[str, list[list[float]]] = {name: [] for name in self.PER_LEG_FIELDS}

    def add(self, t_s: float, classes: Sequence[PeriodClass | None], plant_states: Sequence[str],
            used_bounds: NDArray[np.float64], plant_rod_Pa: NDArray[np.float64],
            row: Mapping[str, Any] | None,
            p_star_ret_Pa: NDArray[np.float64] | None = None) -> None:
        row = row or {}
        self.t_s.append(float(t_s))
        self.classes.append([-1 if value is None else PERIOD_CLASS_CODES[value]
                             for value in classes])
        self.plant_states.append([PLANT_STATE_CODES.get(state, -1) for state in plant_states])
        self.gate_open.append([bool(value) for value in row.get("gate_open", [False] * LEG_COUNT)])
        self.sources.append([JP3_SOURCE_CODES.get(value, -1) for value in
                             row.get("model_bound_source", [None] * LEG_COUNT)])
        self.inherited.append([bool(value) for value in
                               row.get("model_bound_inherited", [False] * LEG_COUNT)])
        given = {"used_bound_Pa": used_bounds, "p_tr_Pa": plant_rod_Pa,
                 "p_star_ret_Pa": p_star_ret_Pa}
        for name in self.PER_LEG_FIELDS:
            values = given.get(name, row.get(name))
            self.values[name].append(
                [math.nan] * LEG_COUNT if values is None
                else [math.nan if value is None else float(value) for value in values])
        self._add_revision_6_columns(row)

    def _add_revision_6_columns(self, row: Mapping[str, Any]) -> None:
        if not any(name in row for name in self.REVISION_6_FIELDS):
            if self.rev6_values is not None:  # a row without them after rows with them
                for name, kind in self.REVISION_6_FIELDS.items():
                    self.rev6_values[name].append([kind(0)] * LEG_COUNT)
            return
        if self.rev6_values is None:
            reads_before = len(self.t_s) - 1
            self.rev6_values = {name: [[kind(0)] * LEG_COUNT for _ in range(reads_before)]
                                for name, kind in self.REVISION_6_FIELDS.items()}
        for name, kind in self.REVISION_6_FIELDS.items():
            values = row.get(name) or [0] * LEG_COUNT
            self.rev6_values[name].append([kind(value) for value in values])

    def revision_6_totals(self) -> dict[str, list[int]] | None:
        """Per-leg sums of the revision 6 columns (None without them)."""
        if self.rev6_values is None:
            return None
        return {name: [int(sum(int(row[leg]) for row in rows)) for leg in range(LEG_COUNT)]
                for name, rows in self.rev6_values.items()}

    def arrays(self) -> dict[str, NDArray[Any]]:
        """``jp3_*`` arrays (n reads, n x 4) for the T4h npz."""
        count = len(self.t_s)
        arrays: dict[str, NDArray[Any]] = {
            "jp3_t_s": np.asarray(self.t_s, dtype=float),
            "jp3_class": np.asarray(self.classes, dtype=np.int8).reshape(count, LEG_COUNT),
            "jp3_plant_state": np.asarray(self.plant_states,
                                          dtype=np.int8).reshape(count, LEG_COUNT),
            "jp3_gate_open": np.asarray(self.gate_open, dtype=bool).reshape(count, LEG_COUNT),
            "jp3_class_names": np.asarray([value.value for value in PeriodClass]),
            "jp3_plant_state_names": np.asarray(PLANT_STATES),
            "jp3_model_bound_source": np.asarray(self.sources,
                                                 dtype=np.int8).reshape(count, LEG_COUNT),
            "jp3_source_names": np.asarray(JP3_SOURCE_NAMES),
            "jp3_model_bound_inherited": np.asarray(self.inherited,
                                                    dtype=bool).reshape(count, LEG_COUNT)}
        for name in self.PER_LEG_FIELDS:
            arrays[f"jp3_{name}"] = np.asarray(self.values[name],
                                               dtype=float).reshape(count, LEG_COUNT)
        for name, kind in self.REVISION_6_FIELDS.items():
            if self.rev6_values is not None:
                arrays[f"jp3_{name}"] = np.asarray(self.rev6_values[name],
                                                   dtype=kind).reshape(count, LEG_COUNT)
        return arrays

    def excerpt(self) -> tuple[list[list[Any]], bool]:
        """Rows of the interesting reads and their two neighbours each side (spec 6.3)."""
        used = np.asarray(self.values["used_bound_Pa"], dtype=float).reshape(-1, LEG_COUNT)
        plant = np.asarray(self.values["p_tr_Pa"], dtype=float).reshape(-1, LEG_COUNT)
        classes = np.asarray(self.classes, dtype=np.int64).reshape(-1, LEG_COUNT)
        with np.errstate(invalid="ignore"):
            gap = used - plant
            is_close = gap < TRACE_EXCERPT_GAP_PA
        is_change = np.zeros_like(is_close)
        is_change[1:] = classes[1:] != classes[:-1]
        picked = np.zeros_like(is_close)
        for offset in range(-TRACE_EXCERPT_CONTEXT_READS, TRACE_EXCERPT_CONTEXT_READS + 1):
            marked = is_close | is_change
            shifted = np.zeros_like(marked)
            if offset >= 0:
                shifted[offset:] = marked[:len(marked) - offset]
            else:
                shifted[:offset] = marked[-offset:]
            picked |= shifted
        rows = [self._excerpt_row(int(read), int(leg), gap)
                for read, leg in zip(*np.nonzero(picked), strict=True)]
        is_truncated = len(rows) > MAX_TRACE_EXCERPT_ROWS
        return rows[:MAX_TRACE_EXCERPT_ROWS], is_truncated

    def _excerpt_row(self, read: int, leg: int, gap: NDArray[np.float64]) -> list[Any]:
        class_code = self.classes[read][leg]
        state_code = self.plant_states[read][leg]
        return [round(self.t_s[read], 6), leg,
                None if class_code < 0 else list(PeriodClass)[class_code].value,
                None if state_code < 0 else PLANT_STATES[state_code],
                _plain_float(self.values["u_m_s"][read][leg]),
                _plain_float(self.values["used_bound_Pa"][read][leg]),
                _plain_float(self.values["ext_bound_Pa"][read][leg]),
                _plain_float(self.values["model_bound_Pa"][read][leg]),
                _plain_float(self.values["p_tr_Pa"][read][leg]),
                _plain_float(self.values["p_star_ret_Pa"][read][leg]),
                _plain_float(self.values["head_read_Pa"][read][leg]),
                _plain_float(gap[read, leg]), self.gate_open[read][leg],
                self.source_name(read, leg),
                _plain_float(self.values["model_bound_age_s"][read][leg])]

    def source_name(self, read: int, leg: int) -> str | None:
        """``jp3_model_bound_source`` of one read as its name (None = no ④ candidate)."""
        code = self.sources[read][leg]
        return None if code < 0 else JP3_SOURCE_NAMES[code]


def _plain_float(value: float) -> float | None:
    return float(value) if math.isfinite(value) else None


class _DominatedReads:
    """Edition 4.1 T-JR-12 records (spec 5.5, 6.3): lock and hold reads of a fallback leg whose
    ④ comes from an R5-7 ``retract_tracker`` candidate, per leg and per stretch.

    A read is over-conservative when ``④ - p_tr > 0.6 kN / A_ann`` (the jp3b tolerance) and a
    false drop when the true force is at or above ``F_min`` while the monitor's lower force is
    below it.
    """

    def __init__(self, tolerance_Pa: NDArray[np.float64]) -> None:
        self.tolerance_Pa = tolerance_Pa
        self.reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.over_tol_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.false_drop_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        self.stretches: dict[tuple[int, float], dict[str, Any]] = {}

    def add(self, classes: Sequence[PeriodClass | None], used_Pa: NDArray[np.float64],
            plant_Pa: NDArray[np.float64], row: Mapping[str, Any],
            true_force_N: ArrayLike | None) -> None:
        sources = row.get("model_bound_source") or [None] * LEG_COUNT
        fallback = row.get("is_fallback") or [False] * LEG_COUNT
        for leg, period_class in enumerate(classes):
            is_counted = (period_class is not None and period_class.is_locked
                          and bool(fallback[leg]) and sources[leg] == RETRACT_TRACKER_SOURCE)
            if is_counted:
                self._count(leg, float(used_Pa[leg] - plant_Pa[leg]), row, true_force_N)

    def _count(self, leg: int, gap_Pa: float, row: Mapping[str, Any],
               true_force_N: ArrayLike | None) -> None:
        self.reads[leg] += 1
        self.over_tol_reads[leg] += int(gap_Pa > self.tolerance_Pa[leg])
        self.false_drop_reads[leg] += int(self._is_false_drop(leg, row, true_force_N))
        stretch = self._stretch_row(leg, row)
        stretch["dominated_reads"] += 1
        if math.isfinite(gap_Pa):
            # 0.6 kN / tolerance = A_ann
            over_kN = gap_Pa * (600.0 / self.tolerance_Pa[leg]) / 1000.0
            previous = stretch["max_over_kN"]
            stretch["max_over_kN"] = over_kN if previous is None else max(previous, over_kN)

    @staticmethod
    def _is_false_drop(leg: int, row: Mapping[str, Any], true_force_N: ArrayLike | None) -> bool:
        lower = row.get("lower_force_N")
        f_min_N = row.get("f_min_N")
        if true_force_N is None or lower is None or f_min_N is None:
            return False
        truth_N = float(np.asarray(true_force_N, dtype=float)[leg])
        return truth_N >= f_min_N and float(lower[leg]) < f_min_N

    def _stretch_row(self, leg: int, row: Mapping[str, Any]) -> dict[str, Any]:
        opened = row.get("stretch_t_open_s") or [None] * LEG_COUNT
        key = (leg, opened[leg])
        stretch = self.stretches.get(key)
        if stretch is None:
            after = row.get("ret_after_gate_s") or [None] * LEG_COUNT
            speed = row.get("ret_mean_speed_m_s") or [None] * LEG_COUNT
            stretch = {"leg": LEG_ORDER[leg], "t_open_s": opened[leg],
                       "ret_after_gate_s": _finite_value(after[leg]),
                       "ret_mean_speed_m_s": _finite_value(speed[leg]),
                       "dominated_reads": 0, "max_over_kN": None}
            if len(self.stretches) < MAX_RETRACT_TRACKER_STRETCH_ROWS:
                self.stretches[key] = stretch
        return stretch

    def record(self) -> dict[str, object]:
        rows = list(self.stretches.values())
        after = [row["ret_after_gate_s"] for row in rows if row["ret_after_gate_s"] is not None]
        return {"retract_tracker_dominated_reads": self.reads.tolist(),
                "retract_tracker_over_tol_reads": self.over_tol_reads.tolist(),
                "retract_tracker_false_drop_reads": self.false_drop_reads.tolist(),
                "retract_tracker_ret_after_gate_s": _distribution(after),
                "retract_tracker_stretch_log": rows,
                "retract_tracker_stretch_log_columns": [
                    "leg", "t_open_s", "ret_after_gate_s", "ret_mean_speed_m_s",
                    "dominated_reads", "max_over_kN"]}


def _finite_value(value: float | None) -> float | None:
    return None if value is None or not math.isfinite(float(value)) else float(value)


def _distribution(values: list[float]) -> dict[str, float | None]:
    """p50 / p90 / max of a list (None values without data)."""
    if not values:
        return {"p50": None, "p90": None, "max": None, "count": 0}
    array = np.asarray(values, dtype=float)
    return {"p50": float(np.percentile(array, 50)), "p90": float(np.percentile(array, 90)),
            "max": float(array.max()), "count": len(values)}


class ExtendBoundCheckRev5:
    """Revision 5 J-P3 counters (spec 6.2, 6.3): each read is classified by the estimate the
    monitor used (its :class:`PeriodClass`), the plant state is a record column.

    The retracting classes are split at ``p*_ret`` of the read = the target the plant law used
    in its last step (2nd edition 6.2, user decision 148, ``hydraulics_remedy_review.md`` 10):
    above it the trapped share (``carry_ret`` judged as J-P3c, ``ret_trapped_*`` recorded), at
    or below it the fill share (``jp3c_fill_*``, ``ret_fill_*``: premise ④, recorded). A
    ``carry_ret`` read of a plant leg still locked is trapped whatever ``p*`` is. Without
    ``p*_ret`` every retracting read counts as trapped (the conservative side).

    Args:
        tolerance_Pa: ``0.6 kN / A_ann`` per leg (the jp3b and lock_ext tolerance).
        sensor_grade: Pressure sensor grade of the row (record keys ``sensor_grade`` and
            ``jp3_judged_row``); None = not declared.
    """

    def __init__(self, tolerance_Pa: NDArray[np.float64], sensor_grade: str | None = None) -> None:
        self.tolerance_Pa = np.asarray(tolerance_Pa, dtype=float)
        self.sensor_grade = sensor_grade
        self.jp3a = _GapCounter()
        self.jp3b = _GapCounter(self.tolerance_Pa)
        self.jp3c = _GapCounter()
        self.jp3c_fill = _GapCounter()
        self.lock_ext = _GapCounter(self.tolerance_Pa)
        self.lock_ret = _GapCounter()
        self.ret = _GapCounter()
        self.ret_trapped = _GapCounter()
        self.ret_fill = _GapCounter()
        self.lock_moving_reads = np.zeros(LEG_COUNT, dtype=np.int64)
        """Lock reads of a leg the plant still moves (valve tail): no comparison."""
        self.jp3a_by_plant_state = {state: [np.zeros(LEG_COUNT, dtype=np.int64),
                                            np.zeros(LEG_COUNT, dtype=np.int64)]
                                    for state in PLANT_STATES}
        self.class_reads = {value.value: np.zeros(LEG_COUNT, dtype=np.int64)
                            for value in PeriodClass}
        self.trace = ExtendBoundTrace()
        self.identity: dict[str, Any] | None = None
        """Edition 4a 13.6: ``spec_edition``, ``carry_end_rule``, ``retract_start_rule`` of the
        monitor (from its trace rows); None = no row carried one."""
        self.is_identity_consistent = True
        self.dominated = _DominatedReads(self.tolerance_Pa)

    def add(self, t_s: float, period_classes: Sequence[PeriodClass | str | None],
            used_bounds: ArrayLike | None, plant_rod_Pa: ArrayLike,
            plant_states: Sequence[str] | None, trace_row: Mapping[str, Any] | None,
            p_star_ret_Pa: ArrayLike | None = None,
            true_force_N: ArrayLike | None = None) -> None:
        """Count one read (see the class docstring); ``true_force_N`` = the plant's net force
        per leg (the false-drop count of ``retract_tracker_dominated_reads``; None = unknown)."""
        self._note_identity(trace_row)
        classes = [None if value is None else PeriodClass(value) for value in period_classes]
        used = (np.full(LEG_COUNT, np.nan) if used_bounds is None
                else np.asarray(used_bounds, dtype=float))
        plant = np.asarray(plant_rod_Pa, dtype=float)
        target = (np.full(LEG_COUNT, np.nan) if p_star_ret_Pa is None
                  else np.asarray(p_star_ret_Pa, dtype=float))
        states = list(plant_states) if plant_states is not None else [""] * LEG_COUNT
        for leg, period_class in enumerate(classes):
            if period_class is None:
                continue
            self.class_reads[period_class.value][leg] += 1
            if math.isfinite(plant[leg]):
                # hydraulics_remedy_review.md 10: the fill share needs p_tr <= p*_last (equal
                # = fill); a carry_ret read of a plant leg still locked is trapped whatever p*
                # is (P1 holds the release); a NaN target keeps the read trapped
                is_locked_plant = states[leg].startswith("locked")
                is_fill = bool(plant[leg] <= target[leg]) and not (
                    period_class is PeriodClass.CARRY_RET and is_locked_plant)
                self._compare(leg, t_s, period_class, states[leg], float(used[leg] - plant[leg]),
                              is_fill)
        if trace_row is not None:
            self.dominated.add(classes, used, plant, trace_row, true_force_N)
        self.trace.add(t_s, classes, states, used, plant, trace_row, target)

    def _note_identity(self, trace_row: Mapping[str, Any] | None) -> None:
        identity = None if trace_row is None else trace_row.get("identity")
        if identity is None:
            return
        if self.identity is None:
            self.identity = dict(identity)
        elif dict(identity) != self.identity:
            self.is_identity_consistent = False

    def _compare(self, leg: int, t_s: float, period_class: PeriodClass, plant_state: str,
                 gap_Pa: float, is_fill: bool = False) -> None:
        if period_class in (PeriodClass.EXT, PeriodClass.CARRY_EXT):
            is_breach = self.jp3a.add(leg, t_s, gap_Pa)
            by_state = self.jp3a_by_plant_state.get(plant_state)
            if by_state is not None and math.isfinite(gap_Pa):
                by_state[0][leg] += 1
                by_state[1][leg] += int(is_breach)
        elif period_class is PeriodClass.HOLD:
            self.jp3b.add(leg, t_s, gap_Pa)
        elif period_class is PeriodClass.CARRY_RET:
            (self.jp3c_fill if is_fill else self.jp3c).add(leg, t_s, gap_Pa)
        elif period_class is PeriodClass.RET:
            self.ret.add(leg, t_s, gap_Pa)
            (self.ret_fill if is_fill else self.ret_trapped).add(leg, t_s, gap_Pa)
        elif plant_state == "locked_ext":
            self.lock_ext.add(leg, t_s, gap_Pa)
        elif plant_state == "locked_ret":
            self.lock_ret.add(leg, t_s, gap_Pa)
        else:
            self.lock_moving_reads[leg] += 1

    def record(self) -> dict[str, object]:
        excerpt, is_truncated = self.trace.excerpt()
        jp3a, jp3b, jp3c = self.jp3a, self.jp3b, self.jp3c
        identity = self.identity or {}
        return {
            # a revision 6 monitor names its revision in the identity (spec v5 4.6)
            "rule_revision": identity.get("rule_revision", EXTEND_HOLD_REVISION),
            **self._revision_6_record(),
            "rule_rev5": EXTEND_BOUND_CHECK_REV5_RULE,
            "spec_edition": identity.get("spec_edition"),
            "carry_end_rule": identity.get("carry_end_rule"),
            "retract_start_rule": identity.get("retract_start_rule"),
            "identity_consistent": self.is_identity_consistent,
            **self.dominated.record(),
            "jp3a_reads": jp3a.reads.tolist(),
            "jp3a_breach_reads": jp3a.breach_reads.tolist(),
            "jp3a_margin_used_reads": jp3a.margin_used_reads.tolist(),
            "jp3a_min_gap_bar": _bar_or_none(jp3a.min_gap_Pa),
            "jp3a_min_gap_t_s": list(jp3a.min_gap_t_s),
            "jp3a_first_breach_t_s": list(jp3a.first_breach_t_s),
            "jp3a_by_plant_state": {state: {"reads": counts[0].tolist(),
                                            "breach_reads": counts[1].tolist()}
                                    for state, counts in self.jp3a_by_plant_state.items()},
            "jp3b_reads": jp3b.reads.tolist(),
            "jp3b_unpaired_reads": jp3b.unpaired_reads.tolist(),
            "jp3b_breach_reads": jp3b.breach_reads.tolist(),
            "jp3b_breach_over_tol_reads": jp3b.over_tol_reads.tolist(),
            "jp3b_min_gap_bar": _bar_or_none(jp3b.min_gap_Pa),
            "jp3b_min_gap_t_s": list(jp3b.min_gap_t_s),
            "jp3b_tolerance_bar": (self.tolerance_Pa / BAR_PA).tolist(),
            "jp3c_reads": jp3c.reads.tolist(),
            "jp3c_breach_reads": jp3c.breach_reads.tolist(),
            "jp3c_min_gap_bar": _bar_or_none(jp3c.min_gap_Pa),
            "jp3c_min_gap_t_s": list(jp3c.min_gap_t_s),
            "jp3c_fill_reads": self.jp3c_fill.reads.tolist(),
            "jp3c_fill_breach_reads": self.jp3c_fill.breach_reads.tolist(),
            "jp3c_fill_max_excess_bar": self.jp3c_fill.max_excess_bar(),
            "sensor_grade": self.sensor_grade,
            "jp3_judged_row": is_judged_sensor_grade(self.sensor_grade),
            "lock_ext_reads": self.lock_ext.reads.tolist(),
            "lock_ext_unpaired_reads": self.lock_ext.unpaired_reads.tolist(),
            "lock_ext_breach_reads": self.lock_ext.breach_reads.tolist(),
            "lock_ext_breach_over_tol_reads": self.lock_ext.over_tol_reads.tolist(),
            "lock_ext_min_gap_bar": _bar_or_none(self.lock_ext.min_gap_Pa),
            "lock_ext_min_gap_t_s": list(self.lock_ext.min_gap_t_s),
            "lock_ret_reads": self.lock_ret.reads.tolist(),
            "lock_ret_breach_reads": self.lock_ret.breach_reads.tolist(),
            "lock_moving_reads": self.lock_moving_reads.tolist(),
            "ret_reads": self.ret.reads.tolist(),
            "ret_breach_reads": self.ret.breach_reads.tolist(),
            "ret_max_excess_bar": self.ret.max_excess_bar(),
            "ret_trapped_reads": self.ret_trapped.reads.tolist(),
            "ret_trapped_breach_reads": self.ret_trapped.breach_reads.tolist(),
            "ret_trapped_max_excess_bar": self.ret_trapped.max_excess_bar(),
            "ret_fill_reads": self.ret_fill.reads.tolist(),
            "ret_fill_breach_reads": self.ret_fill.breach_reads.tolist(),
            "ret_fill_max_excess_bar": self.ret_fill.max_excess_bar(),
            "class_reads": {name: counts.tolist() for name, counts in self.class_reads.items()},
            "trace_excerpt": excerpt,
            "trace_excerpt_columns": list(ExtendBoundTrace.EXCERPT_COLUMNS),
            "trace_excerpt_truncated": is_truncated}

    def _revision_6_record(self) -> dict[str, list[int]]:
        """Spec v5 6.3.9 coverage keys, per leg over the whole run (the T4h ``jp3_*`` columns
        give them per read); empty for a revision 5 record."""
        totals = self.trace.revision_6_totals()
        if totals is None:
            return {}
        return {"jp3_r58_witness_carries": totals["r58_witness"],
                "jp3_r59_substeps": totals["r59_substeps"],
                "jp3_r510_candidates": totals["r510_candidates"],
                "r59_end_guard_substeps": totals["r59_end_guard_substeps"],
                "r59_nan_stroke_substeps": totals["r59_nan_stroke_substeps"]}


J_P3_NAME = "extend_bound_check.ext_moving.breach_reads == 0"
"""Judgement J-P3 of criteria revision 8 3.2."""


J_P3_JUDGED = "judged"
J_P3_NO_ROD_READING = "no_rod_reading"
J_P3_DEFECT_NO_RECORD = "defect_rod_reading_without_record"
J_P3_DEFECT_UNDECLARED = "defect_no_rod_reading_not_declared"
J_P3_DEFECT_RECORD_WITHOUT_READING = "defect_record_without_rod_reading"
J_P3_DEFECT_CASES = (J_P3_DEFECT_NO_RECORD, J_P3_DEFECT_UNDECLARED,
                     J_P3_DEFECT_RECORD_WITHOUT_READING)
J_P3_DEFECT_REVISION_5_RECORD = "defect_revision_5_record_in_revision_4_judgement"
"""Addendum 4a-2 R6: a revision 5 record (``rule_revision`` 5) handed to the revision 4
:func:`j_p3_judgement` is refused (a setting defect), never summed with the 436.8 key."""


def j_p3_run_case(record: dict[str, object] | None, has_rod_reading: bool,
                  head_only_declared: bool) -> str:
    """Row of the criteria revision 9 3.2 table of one ③-on run.

    Args:
        record: ``hydraulics_record.extend_bound_check`` (None or empty = no record).
        has_rod_reading: A rod-side pressure reached the controller at least once (3.1).
        head_only_declared: The run was set up without rod readings (3.1 "헤드 전용 구성";
            the harness steady path or readings ``head``).

    Returns:
        :data:`J_P3_JUDGED` (#1), :data:`J_P3_NO_ROD_READING` (#3) or one of
        :data:`J_P3_DEFECT_CASES` (#2, #4, #5).
    """
    has_record = bool(record)
    if has_rod_reading:
        return J_P3_JUDGED if has_record else J_P3_DEFECT_NO_RECORD
    if not head_only_declared:
        return J_P3_DEFECT_UNDECLARED
    return J_P3_DEFECT_RECORD_WITHOUT_READING if has_record else J_P3_NO_ROD_READING


def j_p3_judgement(records: list[dict[str, object] | None],
                   has_rod_reading: list[bool] | None = None,
                   head_only_declared: list[bool] | None = None) -> dict[str, object]:
    """J-P3 over the ③-on runs (criteria revision 8 3.2, applied by the revision 9 3.2 table):
    the ext_moving ``breach_reads`` of every run with a rod reading summed over its legs.

    The monitor runs the ③ tracker only on reads with a rod-side pressure, so a run without
    any rod reading has no record by construction. Revision 9: such a run is ``no_rod_reading``
    (not applicable, counted) only when it is DECLARED head-only; undeclared, or with a record
    after all, it is a setting defect (:func:`j_p3_run_case`).

    Args:
        records: ``hydraulics_record.extend_bound_check`` of each ③-on run (None = missing).
        has_rod_reading: Per run, whether it had a rod-side reading; None = all had one.
        head_only_declared: Per run, the head-only declaration; None = no run declared.

    Returns:
        ``status`` ``"pass"`` (all judged sums 0), ``"H-7"`` (a breach), ``"setting_defect"``
        (a #2 / #4 / #5 run: not judged, stop) or ``"no_p3_runs"``; ``runs_by_case`` (table
        rows), counts, ``margin_used_reads`` (FLAG) and ``locked_breach_over_tol_reads``
        (cross-check FLAG).
    """
    rod = [True] * len(records) if has_rod_reading is None else list(has_rod_reading)
    declared = [False] * len(records) if head_only_declared is None else list(head_only_declared)
    cases = [j_p3_run_case(record, has_rod, is_declared)
             for record, has_rod, is_declared in zip(records, rod, declared, strict=True)]
    # addendum 4a-2 R6: a revision 5 (or 6) record never goes into the revision 4 sum
    cases = [J_P3_DEFECT_REVISION_5_RECORD
             if case == J_P3_JUDGED and record.get("rule_revision") in HOLD_REVISIONS
             else case for record, case in zip(records, cases, strict=True)]
    judged = [record for record, case in zip(records, cases, strict=True)
              if case == J_P3_JUDGED]
    defects = sum(case in (*J_P3_DEFECT_CASES, J_P3_DEFECT_REVISION_5_RECORD) for case in cases)

    def total(key: str) -> int:
        return int(sum(sum(record.get(key) or []) for record in judged))

    breach_reads = total("breach_reads")
    if not records:
        status = "no_p3_runs"
    elif defects:
        status = "setting_defect"
    elif breach_reads:
        status = "H-7"
    else:
        status = "pass"
    return {"name": J_P3_NAME, "status": status, "runs": len(records),
            "runs_judged": len(judged),
            "runs_by_case": {name: cases.count(name) for name in
                             (J_P3_JUDGED, J_P3_NO_ROD_READING, *J_P3_DEFECT_CASES,
                              J_P3_DEFECT_REVISION_5_RECORD)},
            "missing_records": cases.count(J_P3_DEFECT_NO_RECORD),
            "no_rod_reading_runs": cases.count(J_P3_NO_ROD_READING),
            "breach_reads": breach_reads,
            "runs_with_breach": sum(bool(sum(record.get("breach_reads") or []))
                                    for record in judged),
            "margin_used_reads_flag": total("margin_used_reads"),
            "locked_breach_over_tol_reads_flag": total("locked_breach_over_tol_reads")}


J_P3_REV5_NAME = ("extend_bound_check rev5: jp3a_breach_reads + jp3b_breach_over_tol_reads "
                  "+ jp3c_breach_reads == 0")
"""436.9 J-P3 (``jp3_remedy_spec.md`` 6.2), the revision 5 rows only."""
J_P3_REV5_JUDGED_KEYS = ("jp3a_breach_reads", "jp3b_breach_over_tol_reads", "jp3c_breach_reads")
J_P3_REV5_FLAG_KEYS = ("jp3b_breach_reads", "jp3a_margin_used_reads",
                       "lock_ext_breach_over_tol_reads", "ret_breach_reads")
J_P3_DEFECT_NOT_REVISION_5 = "defect_record_not_revision_5"
"""A judged row whose record has no revision 5 keys (two definitions must not mix, 6.1)."""
J_P3_RECORD_ONLY_GRADE = "record_only_sensor_grade"
"""A row of a conservative or old_worst pressure sensor grade: recorded, not judged (user
decisions 147 / 148: J-P3 judges the ideal and normal-grade rows; the gate ``e_h`` 9 bar is a
normal-grade value)."""
J_P3_DEFECT_GRADE_MISSING = "defect_sensor_grade_missing"
"""A row without a declared sensor grade (2nd edition 6.1: a setting defect)."""
SENSOR_GRADES = ("ideal", "normal", "conservative", "old_worst")
"""Row grades of the revision 5 record (``sensor_grade``): ``ideal`` = the harness reading as
it is (r79 L0, L1), ``normal`` = r79 L2 / L2nocal / L2imuideal, then L3 and L4."""
JUDGED_SENSOR_GRADES = ("ideal", "normal")
J_P3_RECORD_ONLY_GRADES = ("conservative", "old_worst")


J_P3_JUDGED_KEY_MISSING = "judged_key_missing"
"""Addendum 4a-5 3.3: a judged row without the judged keys as per-leg lists (not judgeable;
a reason apart from ``no_judged_runs``, the name path 2 uses too)."""
J_P3_DEFECT_MIXED_REVISIONS = "defect_mixed_hold_revisions"
"""Edition 5 4.6: judged rows of revision 5 and revision 6 in one judgement (a setting
defect; each revision is judged on its own)."""
J_P3_DEFECT_IDENTITY = "defect_rule_identity_not_default"
"""Edition 4a 13.6: a revision 5 row of a test-only rule (``fresh_stretch``, ``model_only``) or
of another spec edition's code (``spec_edition`` missing or not :data:`JP3_SPEC_EDITION`)."""


def is_default_rule_identity(record: Mapping[str, Any] | None) -> bool:
    """The revision 5 or 6 record carries the sealed edition of its revision (revision 5:
    :data:`JP3_SPEC_EDITION`, revision 6: :data:`JP3_SPEC_EDITION_V5`) and the default rules
    (13.6, edition 5 4.6)."""
    record = record or {}
    edition = JP3_SPEC_EDITION_OF_REVISION.get(record.get("rule_revision", EXTEND_HOLD_REVISION))
    return (edition is not None and record.get("spec_edition") == edition
            and record.get("carry_end_rule") == CARRY_END_INHERIT
            and record.get("retract_start_rule") == RETRACT_START_WITH_TRACKER
            and record.get("identity_consistent", True) is True)


def is_judged_sensor_grade(grade: str | None) -> bool:
    """``jp3_judged_row`` of a row grade (2nd edition 6.1)."""
    return grade in JUDGED_SENSOR_GRADES


def j_p3_judgement_rev5(records: list[dict[str, object] | None],
                        has_rod_reading: list[bool] | None = None,
                        head_only_declared: list[bool] | None = None,
                        sensor_grades: list[str | None] | None = None,
                        expected_judged_runs: int | None = None) -> dict[str, object]:
    """J-P3 of 436.9 over the revision 5 rows (spec 6.1, 6.2): the judged keys summed over the
    legs of every judged row; FLAG keys are reported, they do not change the status.

    Edition 4a: a judged row whose rule identity is not the sealed default (``spec_edition``
    :data:`JP3_SPEC_EDITION`, ``carry_end_rule`` and ``retract_start_rule`` defaults) is
    :data:`J_P3_DEFECT_IDENTITY` (13.6); no judged row, or not ``expected_judged_runs`` of them
    (a batch with a fixed count, T-JR-12), is ``no_judged_runs`` (13.2). A judged row whose
    judged keys are not per-leg lists is :data:`J_P3_JUDGED_KEY_MISSING` (not judgeable,
    ``judged_key_missing_runs``; addendum 4a-5 3.3: setting defect > judged_key_missing >
    no_judged_runs > H-7 > pass).

    The run cases are those of :func:`j_p3_run_case` (criteria revision 9 3.2 table). A judged
    row whose record is not a revision 5 record is a setting defect (a revision 4 row is judged
    by :func:`j_p3_judgement`, never here). The row grade is ``sensor_grades`` (when given) or
    the record's ``sensor_grade``: ideal and normal rows are judged, conservative and old_worst
    rows are :data:`J_P3_RECORD_ONLY_GRADE` (their sums are reported apart), a row without a
    known grade is :data:`J_P3_DEFECT_GRADE_MISSING` (2nd edition 6.1, decision 148).

    Returns:
        ``status`` ``"pass"``, ``"H-7"``, ``"setting_defect"``, ``"judged_key_missing"``,
        ``"no_judged_runs"`` or ``"no_p3_runs"``; the judged sums per key,
        ``runs_with_breach``, the FLAG sums and
        ``record_only_grade_sums``.
    """
    rod = [True] * len(records) if has_rod_reading is None else list(has_rod_reading)
    declared = [False] * len(records) if head_only_declared is None else list(head_only_declared)
    if sensor_grades is None:
        grades = [(record or {}).get("sensor_grade") for record in records]
    else:
        grades = list(sensor_grades)
    cases = [j_p3_run_case(record, has_rod, is_declared)
             for record, has_rod, is_declared in zip(records, rod, declared, strict=True)]
    cases = [J_P3_DEFECT_NOT_REVISION_5
             if case == J_P3_JUDGED and record.get("rule_revision") not in HOLD_REVISIONS
             else case for record, case in zip(records, cases, strict=True)]
    cases = [J_P3_DEFECT_IDENTITY
             if case == J_P3_JUDGED and not is_default_rule_identity(record) else case
             for record, case in zip(records, cases, strict=True)]
    # edition 5 4.6: revision 5 and revision 6 rows are two definitions, never one sum
    revisions = sorted({record.get("rule_revision") for record, case in
                        zip(records, cases, strict=True) if case == J_P3_JUDGED})
    if len(revisions) > 1:
        cases = [J_P3_DEFECT_MIXED_REVISIONS if case == J_P3_JUDGED else case
                 for case in cases]
    cases = [_graded_case(case, grade) for case, grade in zip(cases, grades, strict=True)]
    judged = [record for record, case in zip(records, cases, strict=True)
              if case == J_P3_JUDGED]
    record_only = [record for record, case in zip(records, cases, strict=True)
                   if case == J_P3_RECORD_ONLY_GRADE]

    def total(record: Mapping[str, Any], key: str) -> int:
        return int(sum(record.get(key) or []))

    # prelaunch audit M-5 (4a-2 R2): a judged row without a judged key is never read as 0
    key_missing_runs = sum(not has_rev5_judged_keys(record) for record in judged)
    sums = {key: sum(total(record, key) for record in judged) for key in J_P3_REV5_JUDGED_KEYS}
    record_only_sums = {key: sum(total(record, key) for record in record_only)
                        for key in J_P3_REV5_JUDGED_KEYS}
    defects = sum(case in (*J_P3_DEFECT_CASES, J_P3_DEFECT_NOT_REVISION_5,
                           J_P3_DEFECT_GRADE_MISSING, J_P3_DEFECT_IDENTITY,
                           J_P3_DEFECT_MIXED_REVISIONS) for case in cases)
    is_count_wrong = expected_judged_runs is not None and len(judged) != expected_judged_runs
    if not records:
        status = "no_p3_runs"
    elif defects:
        status = "setting_defect"
    elif key_missing_runs:
        # addendum 4a-5 3.3: a judged row without its judged keys, a reason apart from 13.2
        status = J_P3_JUDGED_KEY_MISSING
    elif not judged or is_count_wrong:
        # edition 4a 13.2: no judged row (or not the fixed number) = not judgeable
        status = "no_judged_runs"
    elif any(sums.values()):
        status = "H-7"
    else:
        status = "pass"
    return {"name": J_P3_REV5_NAME, "status": status, "runs": len(records),
            "runs_judged": len(judged), "expected_judged_runs": expected_judged_runs,
            "judged_key_missing_runs": key_missing_runs,
            "runs_by_case": {name: cases.count(name) for name in
                             (J_P3_JUDGED, J_P3_NO_ROD_READING, *J_P3_DEFECT_CASES,
                              J_P3_DEFECT_NOT_REVISION_5, J_P3_DEFECT_GRADE_MISSING,
                              J_P3_DEFECT_IDENTITY, J_P3_RECORD_ONLY_GRADE)
                             + ((J_P3_DEFECT_MIXED_REVISIONS,) if len(revisions) > 1 else ())},
            "rule_revisions": revisions,
            **sums, "record_only_grade_sums": record_only_sums,
            "runs_with_breach": sum(any(total(record, key) for key in J_P3_REV5_JUDGED_KEYS)
                                    for record in judged),
            **{f"{key}_flag": sum(total(record, key) for record in judged)
               for key in J_P3_REV5_FLAG_KEYS}}


def has_rev5_judged_keys(record: Mapping[str, Any] | None) -> bool:
    """Every :data:`J_P3_REV5_JUDGED_KEYS` value is a per-leg list (prelaunch audit M-5)."""
    record = record or {}
    return all(isinstance(record.get(key), list) and len(record[key]) == LEG_COUNT
               for key in J_P3_REV5_JUDGED_KEYS)


def _graded_case(case: str, grade: str | None) -> str:
    """The run case after the row grade of 6.1 (only judged rows change)."""
    if case != J_P3_JUDGED or is_judged_sensor_grade(grade):
        return case
    if grade in J_P3_RECORD_ONLY_GRADES:
        return J_P3_RECORD_ONLY_GRADE
    return J_P3_DEFECT_GRADE_MISSING


def _bar_or_none(values_Pa: NDArray[np.float64]) -> list[float | None]:
    return [float(value) / BAR_PA if math.isfinite(value) else None for value in values_Pa]


def extend_bound_states(is_locked: ArrayLike, last_direction: ArrayLike
                        ) -> list[ExtendBoundState | None]:
    """Leg states of :class:`ExtendBoundCheck` from the plant lock state and the sign of its
    last moving direction (> 0 extension)."""
    states: list[ExtendBoundState | None] = []
    for locked, direction in zip(np.asarray(is_locked, bool), np.asarray(last_direction, float),
                                 strict=True):
        if direction > 0.0:
            states.append(ExtendBoundState.EXTEND_LOCKED if locked
                          else ExtendBoundState.EXTEND_MOVING)
        elif locked:
            states.append(None)
        else:
            states.append(ExtendBoundState.RETRACT)
    return states


def check_extend_start_meta(settings_meta: Mapping[str, Any]) -> int | None:
    """Refuse a stored two-pressure settings meta of an older ``tracked_bound`` rule.

    Args:
        settings_meta: ``TwoPressureSettings.to_meta()`` of a stored run.

    Returns:
        The bound revision (4, 5 or 6) of a ``tracked_bound`` meta, None for another rule.

    Raises:
        ValueError: The rule is ``tracked_bound`` and its bound has no ``revision`` (v1) or a
            revision outside :data:`SUPPORTED_REVISIONS`.
    """
    if settings_meta.get("extend_start_rule") != TRACKED_BOUND_RULE:
        return None
    revision = (settings_meta.get("extend_start_bound") or {}).get("revision")
    if revision not in SUPPORTED_REVISIONS:
        label = "v1 (no revision)" if revision is None else f"revision {revision!r}"
        raise ValueError(f"stored tracked_bound meta is {label}; this code runs revisions "
                         f"{SUPPORTED_REVISIONS}")
    return int(revision)


def initial_pressure_Pa(retract_floor_Pa: ArrayLike) -> NDArray[np.float64]:
    """Spec 3: the start ``p`` is ``p_ret`` per leg (history unknown, conservative)."""
    return np.array(retract_floor_Pa, dtype=float).reshape(LEG_COUNT)


__all__ = ["EXTEND_HOLD_REVISION", "EXTEND_SEED_FIX_REVISION", "EXTEND_START_REVISION",
           "EXTEND_WITNESS_REVISION", "HOLD_REVISIONS", "SUPPORTED_REVISIONS",
           "WITNESS_REVISIONS", "JP3_SPEC_EDITION_V7", "retract_need_upper_bound",
           "BoundGeometry", "ExtendBoundCheck", "ExtendBoundCheckRev5", "ExtendBoundState",
           "ExtendBoundTrace", "ExtendStartBound", "ExtendStartTracker", "LineFillGateBound",
           "LineFillGateParams", "PeriodClass", "PremiseRecord", "ReleaseReliefParams",
           "TensionTruthCounter", "check_extend_start_meta", "extend_bound_states",
           "initial_pressure_Pa", "j_p3_judgement_rev5", "period_class_of", "plant_leg_states",
           "relief_flow_factor", "release_witness_moved_m", "retract_target_rod_pressure_Pa",
           "ALLOW_FRESH_STRETCH_FOR_TEST", "ALLOW_MODEL_ONLY_RETRACT_START_FOR_TEST",
           "JP3_SPEC_EDITION", "JP3_SPEC_EDITION_OF_REVISION", "JP3_SPEC_EDITION_V5",
           "JP3_SOURCE_NAMES", "is_default_rule_identity"]
