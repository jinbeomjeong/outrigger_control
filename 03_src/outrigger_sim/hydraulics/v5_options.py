"""Options of the v5 hydraulic coupling (``00_docs/02_hydraulic/v5_hydraulic_impl_spec.md`` 2.0).

Engine independent (no pychrono). **Every option is off by default**: a run without them keeps its
``vars(args)``, its meta and its result (D-5 is not switched). All numbers an option carries
are ASSUMPTIONS (spec 2.4, 2.5); U-R8-9 and the manufacturer answers replace them.

Combinations refused here:
  * rod-side lock window of the controller without the plant lock rule (spec 2.6, ``SystemExit``);
  * circuit BL with the lock closure (decision D-6, ``ValueError``);
  * the controller's ③ start bound with M1c (review 2026-11-07, ``ValueError``);
  * 436.9 (``jp3_remedy_spec.md`` 3, 4.1): ``extend_start_hold`` without ``extend_start_tracked``;
    P1 ``line_fill_gate`` with M1c, with BL + LC, or with the ③ bound of revision 4 (no line-fill
    gate in the tracker: counterexample ⑥); P2 / P3 / P4 without M2 (``ValueError``).
"""

from __future__ import annotations

import argparse
import math
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from typing import Any

from .flow_limit_run import FlowLimitSetting, flow_setting_from_args
from .rod_release import FLOW_LIMITED_LAW, FLOW_LIMITED_R6_LAW, STORED_LAWS

EXTEND_START_TRACKED_RULE = "tracked_bound"
"""``TwoPressureSettings.extend_start_rule`` of the ③ start bound."""
EXTEND_START_CONTROLLER_TAG = "final_C4G2_P3"
"""Controller tag of a run with ``extend_start_tracked`` (criteria revision 8 3.1: ``final_C4G2``
plus the ③ start bound, revision 4)."""
FINAL_CONTROLLER_TAG = "final_C4G2"
"""Tag of a run without the ③ start bound before the LAS-b switch (the runner's tag; the v5
records carry no key for it)."""
LIFTOFF_SLOW_TAG_SUFFIX = "_LAS"
"""LAS-b switch (2026-11-08): a controller with ``liftoff_approach_slow.enable`` adds this."""
LAS_CONTROLLER_TAG = FINAL_CONTROLLER_TAG + LIFTOFF_SLOW_TAG_SUFFIX
"""``final_C4G2_LAS``: the preset since the LAS-b switch (V0 and the other settings without ③)."""
EXTEND_START_LAS_CONTROLLER_TAG = EXTEND_START_CONTROLLER_TAG + LIFTOFF_SLOW_TAG_SUFFIX
"""``final_C4G2_P3_LAS``: the VB / LS controller since the LAS-b switch."""
ORDER_GATE_TAG_SUFFIX = "_K1"
"""LAS-b K1 switch (``las_k1_rules_adopt.md`` 9.2): a controller with
``slope_clearance_margin.flat_soil_margin_order_gate`` adds this after ``_LAS``. Not the touch-phase
K1 (rejected 2026-11-05) and not the harness key token ``K1`` (crawler stiffness x1)."""
LAS_K1_CONTROLLER_TAG = LAS_CONTROLLER_TAG + ORDER_GATE_TAG_SUFFIX
"""``final_C4G2_LAS_K1``: the preset since the K1 switch (V0 and the other settings without ③)."""
EXTEND_START_LAS_K1_CONTROLLER_TAG = EXTEND_START_LAS_CONTROLLER_TAG + ORDER_GATE_TAG_SUFFIX
"""``final_C4G2_P3_LAS_K1``: the VB / LS controller since the K1 switch."""
TOUCH_CREEP_TAG_SUFFIX = "_TCL"
"""K-2 TOUCH creep latch (``C2Config.touch_creep_latch.enable``, not adopted; user decision
2026-11-10, ``k2_touch_creep_rules.md`` 1.2 Q-3): Touch CreeP Latch, always last after ``_LAS`` /
``_K1`` (``final_C4G2_LAS_TCL``, ``final_C4G2_LAS_K1_TCL``). :data:`EXTEND_START_TAGS` keeps its
three entries; :func:`is_extend_start_tag` recognises the ``_TCL`` forms."""
LOCK_START_B_TAG_SUFFIX = "_LSB"
"""Edition 6 (``jp3_remedy_spec_v6.md`` 3.4, user decision Q6-1 2026-11-23): Lock-Start + B,
after ``_LAS`` and ``_K1`` and before a K-2 ``_TCL``: ``final_C4G2_P3W_LAS_K1_LSB``. The
components a run has on are its ``lsb_components`` meta (the suffix stays when fewer are on).
No other tag token is ``LSB`` (grep 2026-11-23: the word appears only as "least significant
bit" in an IMU study)."""
EXTEND_START_TAGS = (EXTEND_START_CONTROLLER_TAG, EXTEND_START_LAS_CONTROLLER_TAG,
                     EXTEND_START_LAS_K1_CONTROLLER_TAG)
"""Tags of a run with the ③ start bound (before LAS-b, LAS-b, LAS-b + K1). A list only: the ③
judgement uses :func:`is_extend_start_tag` (a set misses suffix combinations such as
``final_C4G2_P3_K1``, post-switch audit W-1)."""
EXTEND_HOLD_CONTROLLER_TAG = "final_C4G2_P3H"
"""436.9 (``jp3_remedy_spec.md`` 4.3): controller tag of a run with ``extend_start_hold`` (③
revision 5, micro-command lock hold). Its switch suffixes follow in the usual order
(``final_C4G2_P3H_LAS_K1``)."""
EXTEND_HOLD_TAGS = (EXTEND_HOLD_CONTROLLER_TAG,
                    EXTEND_HOLD_CONTROLLER_TAG + LIFTOFF_SLOW_TAG_SUFFIX,
                    EXTEND_HOLD_CONTROLLER_TAG + LIFTOFF_SLOW_TAG_SUFFIX
                    + ORDER_GATE_TAG_SUFFIX)
"""Tags of a run with ③ revision 5 (a list only: judge with :func:`is_extend_start_tag` and
:func:`extend_start_revision_of_tag`)."""
EXTEND_WITNESS_CONTROLLER_TAG = "final_C4G2_P3W"
"""436.9 edition 5 (``jp3_remedy_spec_v5.md`` 4.6): controller tag of a run with
``extend_start_witness`` (③ revision 6: release witness R5-8, retract relief R5-9, hold
candidate R5-10). Its switch suffixes follow in the usual order (``final_C4G2_P3W_LAS_K1``).
The revision 5 tag :data:`EXTEND_HOLD_CONTROLLER_TAG` stays for the stored records."""
EXTEND_WITNESS_TAGS = (EXTEND_WITNESS_CONTROLLER_TAG,
                       EXTEND_WITNESS_CONTROLLER_TAG + LIFTOFF_SLOW_TAG_SUFFIX,
                       EXTEND_WITNESS_CONTROLLER_TAG + ORDER_GATE_TAG_SUFFIX,
                       EXTEND_WITNESS_CONTROLLER_TAG + LIFTOFF_SLOW_TAG_SUFFIX
                       + ORDER_GATE_TAG_SUFFIX)
"""The four tag forms of ③ revision 6 (a list only, the tag audit list of 4.6: judge with
:func:`extend_start_revision_of_tag`)."""
EXTEND_START_REVISION_OF_BASE_TAG = {EXTEND_START_CONTROLLER_TAG: 4,
                                     EXTEND_HOLD_CONTROLLER_TAG: 5,
                                     EXTEND_WITNESS_CONTROLLER_TAG: 6}
"""③ bound revision per base tag (:func:`switch_base_tag`)."""
ALLOW_GATE_WITH_REV4_FOR_TEST = False
"""Test-only switch (``jp3_remedy_spec.md`` 4.2, case replay C): with True the P1 line-fill gate
may run with the ③ bound of revision 4. Never set by a runner."""
LOCK_SPEED_EPS_M_S = 1.0e-6
"""``|u_c| <=`` this = a zero command; same value as YAML ``actuator.rod_side.lock_eps_m_s``."""
DEFAULT_VOLUME_SCALE = 1.0
DEFAULT_VENT_CLOSING_OPENING = 0.02
"""``c_v`` of spec 2.4: spool opening where the neutral vent is shut, fraction of v_max."""


class CheckCircuit(StrEnum):
    """Neutral form of the valve in the check-opening model (user decision, spec 2.4)."""

    VENT_NO_REFILL = "VN"
    """A, B -> T in neutral, no refill of the rod chamber."""
    BLOCKED = "BL"
    """A, B blocked in neutral."""


@dataclass(frozen=True)
class CheckDelaySetting:
    """M1c check-opening delay (spec 2.4). Reference values: the units missed their criteria.

    Attributes:
        kind: ``"VN"`` or ``"BL"``. VR, E2 and E4 were left out of the port on purpose.
        volume_scale: Factor on the line, rod chamber, creep and head discharge volumes.
        c_v: Spool opening where the neutral vent is shut, fraction of v_max.
    """

    kind: str
    volume_scale: float = DEFAULT_VOLUME_SCALE
    c_v: float = DEFAULT_VENT_CLOSING_OPENING

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", CheckCircuit(self.kind).value)
        if not (self.volume_scale > 0.0 and math.isfinite(self.volume_scale)):
            raise ValueError(f"volume_scale must be > 0: {self.volume_scale!r}")
        if not (self.c_v > 0.0 and math.isfinite(self.c_v)):
            raise ValueError(f"c_v must be > 0: {self.c_v!r}")

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> CheckDelaySetting:
        """A setting from stored values.

        Raises:
            ValueError: Keys of the left-out variants (E2, E4, no_delay, ...) or kind VR.
        """
        unknown = sorted(set(values) - {"kind", "volume_scale", "c_v"})
        if unknown:
            raise ValueError(f"check delay setting has no {unknown}: VR, E2, E4 are not ported")
        return cls(**values)


@dataclass(frozen=True)
class LockClosureSetting:
    """LC: overlap tail cut and check closing delay (spec 2.5). Plant and controller share it.

    Attributes:
        overlap_ratio: ``delta_ol``, spool opening at the end of the overlap / v_max.
        closing_delay_s: ``t_c``, from the flow cut to the locked law.
    """

    overlap_ratio: float
    closing_delay_s: float

    def __post_init__(self) -> None:
        if not 0.0 < self.overlap_ratio < 1.0:
            raise ValueError(f"overlap_ratio must be in (0, 1): {self.overlap_ratio!r}")
        if not (self.closing_delay_s >= 0.0 and math.isfinite(self.closing_delay_s)):
            raise ValueError(f"closing_delay_s must be >= 0: {self.closing_delay_s!r}")

    def overlap_speed_m_s(self, max_speed_m_s: float) -> float:
        """``u_ol``: step mean spool speed below which a zero command stops the flow."""
        return self.overlap_ratio * max_speed_m_s


OPTIONAL_FIELDS = ("extend_start_tracked", "extend_start_hold", "extend_start_witness",
                   "line_fill_gate", "lock_anchor_continuous", "rod_flow_cap_all",
                   "rod_reading_truth", "lsb_components", "lsb_parameters")
"""Fields :meth:`HydraulicOptions.to_dict` leaves out while off (stored digests unchanged)."""
LSB_FIELDS = ("lsb_components", "lsb_parameters")
"""Edition 6 controller fields (``jp3_remedy_spec_v6.md`` 3.4): empty = off."""
M2_PLANT_FIELDS = ("lock_anchor_continuous", "rod_flow_cap_all", "rod_reading_truth")
"""P2, P3 and P4: defined on the M2 rod pressure only."""


@dataclass(frozen=True)
class HydraulicOptions:
    """All v5 plant options of one run; the defaults change nothing.

    Attributes:
        flow: Shared-pump flow limit (Chrono rows; the harness takes ``FlowSetting``).
        valve_tau_s: Valve lag of the soil Chrono rows.
        rod_release_force: M2, moving rod pressure shifts ``s_ref`` (spec 2.3).
        check_delay: M1c (spec 2.4).
        lock_closure: LC (spec 2.5).
        lock_window_follows_plant: The controller lock window takes the plant lock rule (spec 2.6).
        extend_start_tracked: The controller's ③ start bound after an extension
            (``TwoPressureSettings.extend_start_rule = "tracked_bound"``, revision 4); the v5
            VB and LS1 .. LS4 definition since criteria revision 8 (controller tag
            :data:`EXTEND_START_CONTROLLER_TAG`). Refused with M1c (:func:`check_extend_start`).
        extend_start_hold: ③ revision 5 (``ExtendStartBound(revision=5)``: micro-command lock
            hold, line-fill gate of the tracker; ``jp3_remedy_spec.md`` 2); needs
            ``extend_start_tracked``. Tag :data:`EXTEND_HOLD_CONTROLLER_TAG`.
        extend_start_witness: ③ revision 6 (``ExtendStartBound(revision=6)``: R5-8 .. R5-10,
            ``jp3_remedy_spec_v5.md`` 4); needs ``extend_start_hold``. Tag
            :data:`EXTEND_WITNESS_CONTROLLER_TAG`.
        line_fill_gate: P1, the M1c line state as the release gate of a locked leg
            (``check_open_delay.CheckOpenGate``; harness only).
        lock_anchor_continuous: P2, every lock anchor continues the M2 lag (no r5 step).
        rod_flow_cap_all: P3, M2 law ``flow_limited_r6`` (flow cap on all four branches).
        rod_reading_truth: P4, the controller's rod reading is the M2 plant truth.
        lsb_components: Edition 6 controller components (``A_i``, ``A_ii``, ``B``;
            ``control.lock_start_b``, ``jp3_remedy_spec_v6.md`` 3); empty = off. Tag suffix
            :data:`LOCK_START_B_TAG_SUFFIX`. Harness only.
        lsb_parameters: ``(name, value)`` pairs of the other ``LockStartBSettings`` fields of
            the run (the spec 3 placeholders); empty = the defaults. Needs ``lsb_components``.
    """

    flow: FlowLimitSetting | None = None
    valve_tau_s: float | None = None
    rod_release_force: bool = False
    check_delay: CheckDelaySetting | None = None
    lock_closure: LockClosureSetting | None = None
    lock_window_follows_plant: bool = False
    extend_start_tracked: bool = False
    extend_start_hold: bool = False
    line_fill_gate: CheckDelaySetting | None = None
    lock_anchor_continuous: bool = False
    rod_flow_cap_all: bool = False
    rod_reading_truth: bool = False
    extend_start_witness: bool = False
    lsb_components: tuple[str, ...] = ()
    lsb_parameters: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        components, parameters = _checked_lsb_fields(self.lsb_components, self.lsb_parameters)
        object.__setattr__(self, "lsb_components", components)
        object.__setattr__(self, "lsb_parameters", parameters)
        if self.lock_window_follows_plant and self.lock_closure is None:
            raise SystemExit("the controller lock window needs the plant lock rule "
                             "(spec 2.6: controller alone is refused)")
        if self.extend_start_hold and not self.extend_start_tracked:
            raise ValueError("extend_start_hold (③ revision 5) needs extend_start_tracked")
        if self.extend_start_witness and not self.extend_start_hold:
            raise ValueError("extend_start_witness (③ revision 6) needs extend_start_hold")
        _check_jp3_plant_options(self)
        if self.extend_start_tracked:
            check_extend_start(self, EXTEND_START_TRACKED_RULE, self.extend_start_revision)

    @property
    def is_any_on(self) -> bool:
        return self != HydraulicOptions()

    @property
    def extend_start_revision(self) -> int | None:
        """③ bound revision of these options (6 with ``extend_start_witness``, 5 with
        ``extend_start_hold``, 4 with the bound alone, None without it)."""
        if not self.extend_start_tracked:
            return None
        if self.extend_start_witness:
            return 6
        return 5 if self.extend_start_hold else 4

    @property
    def m2_law(self) -> str | None:
        """M2 law name of the run (None with M2 off)."""
        if not self.rod_release_force:
            return None
        return FLOW_LIMITED_R6_LAW if self.rod_flow_cap_all else FLOW_LIMITED_LAW

    def to_dict(self) -> dict[str, Any]:
        """The fields, plus ``m2_law`` with M2 on: the definition digests and metas of M2 runs
        change with the M2 law (revision 5, ``flow_limited_r5``; ``flow_limited_r6`` with
        ``rod_flow_cap_all``); the M2-off dict stays as it was. ``extend_start_tracked`` and the
        436.9 fields appear only when on, so the dicts (and digests) of the runs without them
        stay as they were (criteria revision 8, ``jp3_remedy_spec.md`` 4.4)."""
        values = asdict(self)
        values["lsb_components"] = list(self.lsb_components)  # JSON form (a stored line)
        values["lsb_parameters"] = dict(self.lsb_parameters)
        for name in OPTIONAL_FIELDS:
            if values[name] in (False, None) or (name in LSB_FIELDS and not values[name]):
                del values[name]
        if self.rod_release_force:
            values["m2_law"] = self.m2_law
        return values

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> HydraulicOptions:
        """The options of :meth:`to_dict` (a job description passed to a worker process).

        Raises:
            ValueError: An ``m2_law`` other than the one these options run (stored
                ``flow_limited_r3`` and ``flow_limited_r4`` runs are refused: this code cannot
                rerun them; ``flow_limited_r6`` goes with ``rod_flow_cap_all`` only).
        """
        options = cls._from_fields(values)
        expected = options.m2_law or FLOW_LIMITED_LAW
        if values.get("m2_law", expected) != expected:
            raise ValueError(f"M2 law {values['m2_law']!r} is not {expected!r}")
        return options

    @classmethod
    def from_stored(cls, values: dict[str, Any]) -> HydraulicOptions:
        """The options of a stored record, for reading it only (never to rerun it).

        Accepts the M2 laws of :data:`rod_release.STORED_LAWS`; the stored law is dropped, so
        ``to_dict`` of the result names the law of this code. Readers that need only the
        controller-side settings (``t4h_replay``: the lock window) use it.

        Raises:
            ValueError: An ``m2_law`` no revision of this project wrote, or ``flow_limited_r6``
                without ``rod_flow_cap_all`` (and the other way round).
        """
        stored_law = values.get("m2_law", FLOW_LIMITED_LAW)
        if stored_law not in STORED_LAWS:
            raise ValueError(f"M2 law {stored_law!r} is not one of {STORED_LAWS}")
        options = cls._from_fields(values)
        if (stored_law == FLOW_LIMITED_R6_LAW) != options.rod_flow_cap_all:
            raise ValueError(f"M2 law {stored_law!r} does not match rod_flow_cap_all "
                             f"{options.rod_flow_cap_all}")
        return options

    @classmethod
    def _from_fields(cls, values: dict[str, Any]) -> HydraulicOptions:
        flow = values.get("flow")
        check_delay = values.get("check_delay")
        lock_closure = values.get("lock_closure")
        line_fill_gate = values.get("line_fill_gate")
        return cls(
            flow=None if flow is None else FlowLimitSetting.from_dict(flow),
            valve_tau_s=values.get("valve_tau_s"),
            rod_release_force=bool(values.get("rod_release_force", False)),
            check_delay=None if check_delay is None else CheckDelaySetting.from_dict(check_delay),
            lock_closure=None if lock_closure is None else LockClosureSetting(**lock_closure),
            lock_window_follows_plant=bool(values.get("lock_window_follows_plant", False)),
            extend_start_tracked=bool(values.get("extend_start_tracked", False)),
            extend_start_hold=bool(values.get("extend_start_hold", False)),
            line_fill_gate=(None if line_fill_gate is None
                            else CheckDelaySetting.from_dict(line_fill_gate)),
            lock_anchor_continuous=bool(values.get("lock_anchor_continuous", False)),
            rod_flow_cap_all=bool(values.get("rod_flow_cap_all", False)),
            rod_reading_truth=bool(values.get("rod_reading_truth", False)),
            extend_start_witness=bool(values.get("extend_start_witness", False)),
            lsb_components=tuple(values.get("lsb_components", ())),
            lsb_parameters=tuple(dict(values.get("lsb_parameters", {})).items()))

    @property
    def lsb_parameter_dict(self) -> dict[str, Any]:
        return dict(self.lsb_parameters)

    def without_flow(self) -> HydraulicOptions:
        """The plant options alone (the runners keep the flow limit on their own path)."""
        return replace(self, flow=None)


def add_hydraulic_arguments(parser: argparse.ArgumentParser, *, with_valve_tau: bool) -> None:
    """CLI options of spec 2.0 (the flow options stay in ``add_flow_limit_arguments``).

    Absent stays absent (``argparse.SUPPRESS``): a run without them keeps ``vars(args)``.

    Args:
        parser: The parser to extend.
        with_valve_tau: Add ``--valve-tau-s`` (only ``run_S9``: ``run_S8C`` rows define the lag).
    """
    group = parser.add_argument_group("v5 hydraulic options (default off, all values ASSUMPTION)")
    if with_valve_tau:
        group.add_argument("--valve-tau-s", dest="valve_tau_s", type=float,
                           default=argparse.SUPPRESS,
                           help="turn the spool lag on, amp_ramp none (spec 2.2, value 0.1)")
    group.add_argument("--rod-release-force", dest="rod_release_force", action="store_true",
                       default=argparse.SUPPRESS,
                       help="M2: rod pressure of a moving leg shifts s_ref (spec 2.3)")
    group.add_argument("--check-delay", dest="check_delay",
                       choices=[kind.value for kind in CheckCircuit],
                       default=argparse.SUPPRESS,
                       help="M1c check opening delay, reference values only (spec 2.4)")
    group.add_argument("--check-delay-volume-scale", dest="check_delay_volume_scale", type=float,
                       default=argparse.SUPPRESS, help="M1c volume factor, nominal 1")
    group.add_argument("--check-delay-cv", dest="check_delay_cv", type=float,
                       default=argparse.SUPPRESS, help="M1c vent closing opening, nominal 0.02")
    group.add_argument("--lock-overlap-ratio", dest="lock_overlap_ratio", type=float,
                       default=argparse.SUPPRESS,
                       help="LC overlap end / v_max (spec 2.5, with --lock-closing-delay-s)")
    group.add_argument("--lock-closing-delay-s", dest="lock_closing_delay_s", type=float,
                       default=argparse.SUPPRESS,
                       help="LC check closing delay [s] (spec 2.5, with --lock-overlap-ratio)")
    group.add_argument("--lock-window-follows-plant", dest="lock_window_follows_plant",
                       action="store_true", default=argparse.SUPPRESS,
                       help="the controller lock window takes the LC rule (spec 2.6, needs LC)")
    group.add_argument("--extend-start-tracked", dest="extend_start_tracked",
                       action="store_true", default=argparse.SUPPRESS,
                       help="controller ③ start bound, revision 4 (v5 VB / LS definition, "
                            "criteria revision 8; refused with M1c)")
    _add_jp3_arguments(group)


def _add_jp3_arguments(group) -> None:
    """436.9 options (``jp3_remedy_spec.md`` 3, 4.1), all off and absent by default."""
    group.add_argument("--extend-start-hold", dest="extend_start_hold", action="store_true",
                       default=argparse.SUPPRESS,
                       help="③ revision 5: micro-command lock hold and line-fill gate "
                            "(needs --extend-start-tracked)")
    group.add_argument("--extend-start-witness", dest="extend_start_witness",
                       action="store_true", default=argparse.SUPPRESS,
                       help="③ revision 6: release witness, retract relief bound and hold "
                            "candidate (needs --extend-start-hold)")
    group.add_argument("--line-fill-gate", dest="line_fill_gate",
                       choices=[kind.value for kind in CheckCircuit], default=argparse.SUPPRESS,
                       help="P1: M1c line fill gates the release of a locked leg (harness)")
    group.add_argument("--line-fill-gate-volume-scale", dest="line_fill_gate_volume_scale",
                       type=float, default=argparse.SUPPRESS, help="P1 volume factor, nominal 1")
    group.add_argument("--line-fill-gate-cv", dest="line_fill_gate_cv", type=float,
                       default=argparse.SUPPRESS, help="P1 vent closing opening, nominal 0.02")
    group.add_argument("--lock-anchor-continuous", dest="lock_anchor_continuous",
                       action="store_true", default=argparse.SUPPRESS,
                       help="P2: every lock anchor continues the M2 lag (needs M2)")
    group.add_argument("--rod-flow-cap-all", dest="rod_flow_cap_all", action="store_true",
                       default=argparse.SUPPRESS,
                       help="P3: M2 law flow_limited_r6, flow cap on all branches (needs M2)")
    group.add_argument("--rod-reading-truth", dest="rod_reading_truth", action="store_true",
                       default=argparse.SUPPRESS,
                       help="P4: controller rod reading = M2 plant truth (needs M2)")


def _delay_setting_from_args(args: argparse.Namespace, option: str) -> CheckDelaySetting | None:
    """``CheckDelaySetting`` of ``--<option>`` with its ``-volume-scale`` / ``-cv`` companions
    (``option`` is the attribute name: ``check_delay`` or ``line_fill_gate``)."""
    scale_key, cv_key = f"{option}_volume_scale", f"{option}_cv"
    given = {key: getattr(args, key) for key in (scale_key, cv_key) if hasattr(args, key)}
    if not hasattr(args, option):
        if given:
            raise SystemExit(f"{sorted(given)} need --{option.replace('_', '-')}")
        return None
    return CheckDelaySetting(
        kind=getattr(args, option),
        volume_scale=given.get(scale_key, DEFAULT_VOLUME_SCALE),
        c_v=given.get(cv_key, DEFAULT_VENT_CLOSING_OPENING))


def _check_delay_from_args(args: argparse.Namespace) -> CheckDelaySetting | None:
    return _delay_setting_from_args(args, "check_delay")


def _lock_closure_from_args(args: argparse.Namespace) -> LockClosureSetting | None:
    has_ratio = hasattr(args, "lock_overlap_ratio")
    if has_ratio != hasattr(args, "lock_closing_delay_s"):
        raise SystemExit("--lock-overlap-ratio and --lock-closing-delay-s go together")
    if not has_ratio:
        return None
    return LockClosureSetting(args.lock_overlap_ratio, args.lock_closing_delay_s)


def hydraulic_options_from_args(args: argparse.Namespace) -> HydraulicOptions:
    """The options of :func:`add_hydraulic_arguments` and ``add_flow_limit_arguments``.

    Raises:
        SystemExit: An option that needs another one, or the controller window alone.
    """
    return HydraulicOptions(
        flow=flow_setting_from_args(args),
        valve_tau_s=getattr(args, "valve_tau_s", None),
        rod_release_force=hasattr(args, "rod_release_force"),
        check_delay=_check_delay_from_args(args),
        lock_closure=_lock_closure_from_args(args),
        lock_window_follows_plant=hasattr(args, "lock_window_follows_plant"),
        extend_start_tracked=hasattr(args, "extend_start_tracked"),
        extend_start_hold=hasattr(args, "extend_start_hold"),
        line_fill_gate=_delay_setting_from_args(args, "line_fill_gate"),
        lock_anchor_continuous=hasattr(args, "lock_anchor_continuous"),
        rod_flow_cap_all=hasattr(args, "rod_flow_cap_all"),
        rod_reading_truth=hasattr(args, "rod_reading_truth"),
        extend_start_witness=hasattr(args, "extend_start_witness"))


def validate(options: HydraulicOptions, *, period_s: float, engine: str = "harness",
             lock_valve: str = "pilot_check") -> None:
    """Refuse the combinations of spec 2.0, 2.4, 2.6 and decision D-6 before a run starts.

    Args:
        options: The run's options.
        period_s: Controller period ``T``.
        engine: ``"harness"``, ``"L2b"`` or ``"L1"``.
        lock_valve: YAML ``actuator.lock_valve`` of the plant.

    Raises:
        SystemExit: Controller window without the plant rule; a plant option on an L1 row.
        ValueError: Plant rule alone with ``t_c > T``; BL with LC; LC or M2 with the
            counterbalance.
    """
    if options.lock_window_follows_plant and options.lock_closure is None:
        raise SystemExit("the controller lock window alone is refused (spec 2.6)")
    jp3_plant_options = (options.line_fill_gate, options.lock_anchor_continuous,
                         options.rod_flow_cap_all, options.rod_reading_truth)
    plant_options = (options.rod_release_force, options.check_delay, options.lock_closure,
                     *jp3_plant_options)
    if engine == "L1" and any(option not in (None, False) for option in plant_options):
        raise SystemExit("M2, M1c and LC are L2b / harness options, not L1 (spec 2.0)")
    if engine != "harness" and any(option not in (None, False) for option in jp3_plant_options):
        raise SystemExit("P1 .. P4 (436.9) are harness options; the L2b plant has none "
                         "(jp3_remedy_spec.md 3, user decision 146)")
    if engine != "harness" and options.lsb_components:
        raise SystemExit("the edition 6 components are harness only (jp3_remedy_spec_v6.md 9)")
    closure = options.lock_closure
    if closure is not None and not options.lock_window_follows_plant \
            and closure.closing_delay_s > period_s:
        raise ValueError(f"plant rule alone with t_c {closure.closing_delay_s} s > T {period_s} s: "
                         "the old window would close before the lock (spec 2.6)")
    if closure is not None and options.check_delay is not None \
            and options.check_delay.kind == CheckCircuit.BLOCKED.value:
        raise ValueError("BL with LC is refused (decision D-6: t_c assumes A, B -> T)")
    if lock_valve == "counterbalance" and (closure is not None or options.rod_release_force
                                           or options.line_fill_gate is not None):
        raise ValueError("LC, M2 and P1 are not defined with the counterbalance "
                         "(spec 2.3, 2.5; jp3_remedy_spec.md 3)")


def check_extend_start(options: HydraulicOptions | None, extend_start_rule: str,
                       revision: int | None = None) -> None:
    """Refuse the ③ start bound with M1c (hydraulics-expert review 2026-11-07, 2c): M1c holds
    the extending leg back, which the bound's speed lower bound does not cover. Refuse the
    bound of revision 4 with the P1 line-fill gate (``jp3_remedy_spec.md`` 3, counterexample ⑥:
    only revision 5 has the tracker gate), unless :data:`ALLOW_GATE_WITH_REV4_FOR_TEST`.

    Args:
        options: The run's options (None = none).
        extend_start_rule: ``"tracked_bound"`` or ``"constant"``.
        revision: Bound revision of the run; None = 4 (the revision before 436.9).

    Raises:
        ValueError: ``extend_start_rule`` is ``"tracked_bound"`` and M1c is on, or P1 is on
            with a revision 4 bound.
    """
    if extend_start_rule != "tracked_bound" or options is None:
        return
    if options.check_delay is not None:
        raise ValueError("extend_start_rule tracked_bound with M1c is refused "
                         "(review 2026-11-07: the speed lower bound does not hold)")
    is_revision_4 = revision is None or revision == 4
    if options.line_fill_gate is not None and is_revision_4 and not ALLOW_GATE_WITH_REV4_FOR_TEST:
        raise ValueError("the P1 line-fill gate with the ③ bound of revision 4 is refused "
                         "(jp3_remedy_spec.md 3: counterexample ⑥, revision 5 needed)")


def _checked_lsb_fields(
    components: Any, parameters: Any
) -> tuple[tuple[str, ...], tuple[tuple[str, Any], ...]]:
    """The edition 6 fields in canonical form: components in ``A_i``, ``A_ii``, ``B`` order,
    parameters sorted by name; checked by building the controller settings.

    Raises:
        ValueError: An unknown component or parameter, parameters without a component, or a
            value ``LockStartBSettings`` refuses.
    """
    components = tuple(str(name) for name in components)
    parameters = tuple(sorted((str(name), value) for name, value in parameters))
    if not components:
        if parameters:
            raise ValueError("lsb_parameters need lsb_components (edition 6)")
        return (), ()
    # Imported here: control.lock_start_b imports check_open_delay, which imports this module.
    from outrigger_sim.control.lock_start_b import LockStartBSettings, parameter_names

    unknown = sorted(name for name, _ in parameters if name not in parameter_names())
    if unknown:
        raise ValueError(f"unknown lsb_parameters {unknown}")
    settings = LockStartBSettings(components=components, **dict(parameters))
    return settings.components, parameters


def _check_jp3_plant_options(options: HydraulicOptions) -> None:
    """436.9 plant options P1 .. P4 (``jp3_remedy_spec.md`` 3 refusal column).

    Raises:
        ValueError: P1 with M1c or with BL + LC (D-6); P2 / P3 / P4 without M2.
    """
    gate = options.line_fill_gate
    if gate is not None:
        if options.check_delay is not None:
            raise ValueError("line_fill_gate (P1) and check_delay (M1c) are refused together: "
                             "P1 is the M1c gate alone")
        if gate.kind == CheckCircuit.BLOCKED.value and options.lock_closure is not None:
            raise ValueError("line_fill_gate BL with LC is refused (decision D-6)")
    if not options.rod_release_force:
        on = [name for name in M2_PLANT_FIELDS if getattr(options, name)]
        if on:
            raise ValueError(f"{on} need M2 (rod_release_force)")


def apply_lock_window(config: Any, options: HydraulicOptions, v_max_m_s: float,
                      valve_tau_s: float) -> Any:
    """The C2 configuration with the controller lock window of the plant rule (spec 2.6, R-2).

    Args:
        config: ``control.c2.C2Config``.
        options: The run's options; the window and the plant come from one ``LockClosureSetting``.
        v_max_m_s: ``v_max`` of the plant.
        valve_tau_s: ``tau_v`` of the plant valve.

    Returns:
        ``config`` itself when the window option is off (bit-identical path), else a copy.
    """
    if not options.lock_window_follows_plant:
        return config
    closure = options.lock_closure
    return config.with_lock_closure(closure.overlap_speed_m_s(v_max_m_s),
                                    closure.closing_delay_s, valve_tau_s)


def apply_controller_options(config: Any, options: HydraulicOptions, v_max_m_s: float,
                             valve_tau_s: float) -> Any:
    """The C2 configuration with every controller-side v5 option: the lock window
    (:func:`apply_lock_window`), the ③ start bound (``extend_start_tracked``) and the edition 6
    components (``lsb_components``, ``C2Config.with_lock_start_b``).

    Returns:
        ``config`` itself when all are off (bit-identical path), else a copy.
    """
    config = apply_lock_window(config, options, v_max_m_s, valve_tau_s)
    if options.extend_start_tracked:
        config = _with_extend_start_bound(config, options)
    if options.lsb_components:
        config = config.with_lock_start_b(options.lsb_components, options.lsb_parameter_dict)
    return config


def _with_extend_start_bound(config: Any, options: HydraulicOptions) -> Any:
    changes: dict[str, Any] = {"extend_start_rule": EXTEND_START_TRACKED_RULE}
    if options.extend_start_hold:  # ③ revision 5 / 6 (436.9); revision 4 keeps the default
        from outrigger_sim.control.extend_start_bound import ExtendStartBound

        changes["extend_start_bound"] = ExtendStartBound(revision=options.extend_start_revision)
    two_pressure = replace(config.two_pressure, **changes)
    return replace(config, two_pressure=two_pressure)


def is_liftoff_slow_on(config: Any | None) -> bool:
    """The C2 configuration has LAS-b on (``liftoff_approach_slow.enable``; False for ``None``,
    a config from code before LAS-b and a controller config without the block)."""
    settings = getattr(config, "liftoff_approach_slow", None)
    return bool(getattr(settings, "enable", False))


def is_order_gate_on(config: Any | None) -> bool:
    """The C2 configuration has the LAS-b K1 R4c30 order gate on
    (``slope_clearance_margin.flat_soil_margin_order_gate``; False for ``None``, a config from
    code before K1 and a controller config without the block)."""
    margin = getattr(config, "slope_clearance_margin", None)
    return bool(getattr(margin, "flat_soil_margin_order_gate", False))


def is_touch_creep_on(config: Any | None) -> bool:
    """The C2 configuration has the K-2 TOUCH creep latch on (``touch_creep_latch.enable``;
    False for ``None``, a config from code before K-2 and a controller config without the
    block)."""
    settings = getattr(config, "touch_creep_latch", None)
    return bool(getattr(settings, "enable", False))


def is_lock_start_b_on(config: Any | None) -> bool:
    """The C2 configuration has an edition 6 component on (``lock_start_b.is_enabled``; False
    for ``None`` and a config from code before edition 6)."""
    settings = getattr(config, "lock_start_b", None)
    return bool(getattr(settings, "is_enabled", False))


def lsb_components_of(config: Any | None) -> list[str]:
    """The edition 6 components a C2 configuration has on (the ``lsb_components`` meta)."""
    settings = getattr(config, "lock_start_b", None)
    return list(getattr(settings, "components", ()))


def _split_suffix(tag: str, suffix: str) -> tuple[str, bool]:
    """``(tag without a trailing suffix, whether it had one)``."""
    if tag.endswith(suffix):
        return tag[: -len(suffix)], True
    return tag, False


def _split_order_gate_suffix(tag: str) -> tuple[str, bool]:
    """``(tag without a trailing _K1, whether it had one)``."""
    return _split_suffix(tag, ORDER_GATE_TAG_SUFFIX)


def _split_touch_creep_suffix(tag: str) -> tuple[str, bool]:
    """``(tag without a trailing _TCL, whether it had one)``."""
    return _split_suffix(tag, TOUCH_CREEP_TAG_SUFFIX)


def _split_tail(tag: str) -> tuple[str, bool, bool]:
    """``(tag without a trailing _TCL and then _LSB, had _LSB, had _TCL)``: the suffixes that
    follow ``_LAS`` / ``_K1`` (:data:`LOCK_START_B_TAG_SUFFIX` before the K-2 one)."""
    tag, has_touch_creep = _split_touch_creep_suffix(tag)
    tag, has_lock_start_b = _split_suffix(tag, LOCK_START_B_TAG_SUFFIX)
    return tag, has_lock_start_b, has_touch_creep


def _with_tail(tag: str, has_lock_start_b: bool, has_touch_creep: bool) -> str:
    if has_lock_start_b:
        tag += LOCK_START_B_TAG_SUFFIX
    return tag + TOUCH_CREEP_TAG_SUFFIX if has_touch_creep else tag


def with_liftoff_slow_tag(tag: str | None) -> str:
    """The LAS-b tag of a run tag: ``None`` (the runner's ``final_C4G2``) -> ``final_C4G2_LAS``,
    any other tag gets :data:`LIFTOFF_SLOW_TAG_SUFFIX` once (``ABL`` -> ``ABL_LAS``). A tag
    with the K1 suffix keeps it last (``final_C4G2_K1`` -> ``final_C4G2_LAS_K1``;
    ``final_C4G2_LAS_K1`` is returned as it is); an edition 6 ``_LSB`` and a K-2 suffix stay
    after both."""
    if tag is None:
        return LAS_CONTROLLER_TAG
    tag, has_lock_start_b, has_touch_creep = _split_tail(tag)
    base, has_order_gate = _split_order_gate_suffix(tag)
    if not base.endswith(LIFTOFF_SLOW_TAG_SUFFIX):
        base += LIFTOFF_SLOW_TAG_SUFFIX
    tag = base + ORDER_GATE_TAG_SUFFIX if has_order_gate else base
    return _with_tail(tag, has_lock_start_b, has_touch_creep)


def with_order_gate_tag(tag: str | None) -> str:
    """The K1 tag of a run tag: ``None`` (the runner's ``final_C4G2``) -> ``final_C4G2_K1``,
    any other tag gets :data:`ORDER_GATE_TAG_SUFFIX` once (``ABL_LAS`` -> ``ABL_LAS_K1``); an
    edition 6 ``_LSB`` and a K-2 suffix stay last."""
    base = FINAL_CONTROLLER_TAG if tag is None else tag
    base, has_lock_start_b, has_touch_creep = _split_tail(base)
    tag = base if base.endswith(ORDER_GATE_TAG_SUFFIX) else base + ORDER_GATE_TAG_SUFFIX
    return _with_tail(tag, has_lock_start_b, has_touch_creep)


def with_lock_start_b_tag(tag: str | None) -> str:
    """The edition 6 tag of a run tag: ``None`` -> ``final_C4G2_LSB``, any other tag gets
    :data:`LOCK_START_B_TAG_SUFFIX` once, after ``_LAS`` / ``_K1`` and before a K-2 suffix
    (``final_C4G2_P3W_LAS_K1`` -> ``final_C4G2_P3W_LAS_K1_LSB``)."""
    base = FINAL_CONTROLLER_TAG if tag is None else tag
    base, _, has_touch_creep = _split_tail(base)
    return _with_tail(base, True, has_touch_creep)


def with_touch_creep_tag(tag: str | None) -> str:
    """The K-2 tag of a run tag: ``None`` (the runner's ``final_C4G2``) -> ``final_C4G2_TCL``,
    any other tag gets :data:`TOUCH_CREEP_TAG_SUFFIX` once (``final_C4G2_LAS_K1`` ->
    ``final_C4G2_LAS_K1_TCL``)."""
    base = FINAL_CONTROLLER_TAG if tag is None else tag
    return base if base.endswith(TOUCH_CREEP_TAG_SUFFIX) else base + TOUCH_CREEP_TAG_SUFFIX


def is_liftoff_slow_tag(tag: str | None) -> bool:
    """A recorded tag of a run with LAS-b on (records without a tag ran before the switch);
    true with or without the K1 suffix after ``_LAS`` (``final_C4G2_P3_LAS_K1``) and an
    edition 6 / K-2 suffix after that."""
    if tag is None:
        return False
    tag, _, _ = _split_tail(tag)
    base, _ = _split_order_gate_suffix(tag)
    return base.endswith(LIFTOFF_SLOW_TAG_SUFFIX)


def is_order_gate_tag(tag: str | None) -> bool:
    """A recorded tag of a run with the LAS-b K1 order gate on (suffix ``_K1``, before an
    edition 6 or K-2 suffix when there is one)."""
    if tag is None:
        return False
    tag, _, _ = _split_tail(tag)
    return tag.endswith(ORDER_GATE_TAG_SUFFIX)


def is_lock_start_b_tag(tag: str | None) -> bool:
    """A recorded tag of a run with an edition 6 component on (suffix ``_LSB``, before a K-2
    suffix when there is one). Which components: the run's ``lsb_components``."""
    if tag is None:
        return False
    _, has_lock_start_b, _ = _split_tail(tag)
    return has_lock_start_b


def is_touch_creep_tag(tag: str | None) -> bool:
    """A recorded tag of a run with the K-2 TOUCH creep latch on (suffix ``_TCL``)."""
    return tag is not None and tag.endswith(TOUCH_CREEP_TAG_SUFFIX)


def switch_base_tag(tag: str) -> str:
    """``tag`` without the switch suffixes :func:`with_switch_tags` adds (a trailing ``_TCL``,
    then ``_LSB``, then ``_K1``, then ``_LAS``): ``final_C4G2_P3_LAS_K1`` /
    ``final_C4G2_P3_K1`` -> ``final_C4G2_P3``, ``final_C4G2_P3W_LAS_K1_LSB`` ->
    ``final_C4G2_P3W``, ``ABL_LAS`` -> ``ABL``."""
    tag, _, _ = _split_tail(tag)
    base, _ = _split_order_gate_suffix(tag)
    if base.endswith(LIFTOFF_SLOW_TAG_SUFFIX):
        base = base[: -len(LIFTOFF_SLOW_TAG_SUFFIX)]
    return base


def is_extend_start_tag(tag: str | None) -> bool:
    """A recorded tag of a run with the ③ start bound: its base tag (:func:`switch_base_tag`)
    is :data:`EXTEND_START_CONTROLLER_TAG` (revision 4) or :data:`EXTEND_HOLD_CONTROLLER_TAG`
    (revision 5, 436.9), whatever the LAS-b and K1 switches were (post-switch audit W-1, user
    decision (a) 2026-11-10). False for ``None``."""
    return extend_start_revision_of_tag(tag) is not None


def extend_start_revision_of_tag(tag: str | None) -> int | None:
    """③ bound revision of a recorded tag: ``final_C4G2_P3*`` -> 4, ``final_C4G2_P3H*`` -> 5,
    ``final_C4G2_P3W*`` -> 6 (the base tag after the switch suffixes, never a prefix test),
    any other tag (or None) -> None. Every tool that rebuilds a setting from a tag uses this
    (``jp3_remedy_spec.md`` 4.3): a revision 5 row must never be re-tagged as revision 4."""
    if tag is None:
        return None
    return EXTEND_START_REVISION_OF_BASE_TAG.get(switch_base_tag(tag))


def with_switch_tags(tag: str | None, config: Any | None) -> str | None:
    """``tag`` with the suffixes of the switches ``config`` has on: ``_LAS`` (LAS-b), then
    ``_K1`` (order gate), then the edition 6 ``_LSB``, then the K-2 ``_TCL`` (TOUCH creep
    latch). Unchanged (possibly None) when all are off."""
    if is_liftoff_slow_on(config):
        tag = with_liftoff_slow_tag(tag)
    if is_order_gate_on(config):
        tag = with_order_gate_tag(tag)
    if is_lock_start_b_on(config):
        tag = with_lock_start_b_tag(tag)
    if is_touch_creep_on(config):
        tag = with_touch_creep_tag(tag)
    return tag


def controller_tag(options: HydraulicOptions | None, config: Any | None = None) -> str | None:
    """Tag of a v5 run: :data:`EXTEND_START_CONTROLLER_TAG` with the ③ start bound, else None
    (the run keeps the tag of its runner, ``final_C4G2``); with ``config`` the suffixes of its
    switches (:func:`with_switch_tags`): ``final_C4G2_P3_LAS_K1`` / ``final_C4G2_LAS_K1`` for the
    preset since the K1 switch, ``_LAS`` alone for LAS-b without the order gate. Without
    ``config`` the tag is the one before the LAS-b switch (callers that know the controller
    pass it)."""
    tag = None
    if options is not None and options.extend_start_witness:
        tag = EXTEND_WITNESS_CONTROLLER_TAG
    elif options is not None and options.extend_start_hold:
        tag = EXTEND_HOLD_CONTROLLER_TAG
    elif options is not None and options.extend_start_tracked:
        tag = EXTEND_START_CONTROLLER_TAG
    return with_switch_tags(tag, config)


def check_lock_window_meta(two_pressure_meta: dict[str, Any], options: HydraulicOptions,
                           v_max_m_s: float, valve_tau_s: float) -> None:
    """After a run: the controller meta holds the window of the options (criteria P-4).

    Raises:
        RuntimeError: The meta differs from the options.
    """
    expected: dict[str, Any] = {"lock_window_eps_m_s": LOCK_SPEED_EPS_M_S}
    if options.lock_window_follows_plant:
        closure = options.lock_closure
        expected = {"lock_window_eps_m_s": closure.overlap_speed_m_s(v_max_m_s),
                    "lock_window_closing_delay_s": closure.closing_delay_s,
                    "lock_window_valve_tau_s": valve_tau_s}
    elif "lock_window_closing_delay_s" in two_pressure_meta:
        raise RuntimeError("the controller window has t_c but the option is off")
    differing = {key: (two_pressure_meta.get(key), value) for key, value in expected.items()
                 if two_pressure_meta.get(key) != value}
    if differing:
        raise RuntimeError(f"controller lock window meta differs from the options: {differing}")


def check_lock_start_b_config(config: Any | None, options: HydraulicOptions) -> None:
    """Edition 6 identity guard (spec 3.4): the C2 configuration a run built has exactly the
    components and thresholds of its options (none with the options off).

    Raises:
        RuntimeError: No configuration with components on, or other components / values.
    """
    if not options.lsb_components:
        if is_lock_start_b_on(config):
            raise RuntimeError(f"edition 6 components {lsb_components_of(config)} are on, the "
                               "options have none")
        return
    if config is None:
        raise RuntimeError("no C2 configuration was built for the edition 6 options")
    settings = config.lock_start_b
    expected = type(settings)(components=options.lsb_components, **options.lsb_parameter_dict)
    if settings != expected:
        raise RuntimeError(f"edition 6 settings {settings.to_meta()} differ from the options "
                           f"{expected.to_meta()}")


__all__ = [
    "ALLOW_GATE_WITH_REV4_FOR_TEST",
    "LOCK_START_B_TAG_SUFFIX",
    "check_lock_start_b_config",
    "is_lock_start_b_on",
    "is_lock_start_b_tag",
    "lsb_components_of",
    "with_lock_start_b_tag",
    "EXTEND_HOLD_CONTROLLER_TAG",
    "EXTEND_HOLD_TAGS",
    "EXTEND_START_LAS_CONTROLLER_TAG",
    "EXTEND_START_LAS_K1_CONTROLLER_TAG",
    "EXTEND_START_TAGS",
    "EXTEND_WITNESS_CONTROLLER_TAG",
    "EXTEND_WITNESS_TAGS",
    "extend_start_revision_of_tag",
    "LAS_CONTROLLER_TAG",
    "LAS_K1_CONTROLLER_TAG",
    "LIFTOFF_SLOW_TAG_SUFFIX",
    "ORDER_GATE_TAG_SUFFIX",
    "TOUCH_CREEP_TAG_SUFFIX",
    "is_extend_start_tag",
    "is_liftoff_slow_on",
    "is_liftoff_slow_tag",
    "is_order_gate_on",
    "is_order_gate_tag",
    "is_touch_creep_on",
    "is_touch_creep_tag",
    "with_liftoff_slow_tag",
    "with_order_gate_tag",
    "with_touch_creep_tag",
    "switch_base_tag",
    "with_switch_tags",
    "LOCK_SPEED_EPS_M_S",
    "apply_lock_window",
    "check_extend_start",
    "check_lock_window_meta",
    "validate",
    "CheckCircuit",
    "CheckDelaySetting",
    "HydraulicOptions",
    "LockClosureSetting",
    "add_hydraulic_arguments",
    "hydraulic_options_from_args",
]
