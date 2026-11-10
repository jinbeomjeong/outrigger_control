"""Options of the v5 hydraulic coupling (``00_docs/02_hydraulic/v5_hydraulic_impl_spec.md`` 2.0).

Engine independent (no pychrono). **Every option is off by default**: a run without them keeps its
``vars(args)``, its meta and its result (D-5 is not switched). All numbers an option carries
are ASSUMPTIONS (spec 2.4, 2.5); U-R8-9 and the manufacturer answers replace them.

Combinations refused here:
  * rod-side lock window of the controller without the plant lock rule (spec 2.6, ``SystemExit``);
  * circuit BL with the lock closure (decision D-6, ``ValueError``);
  * the controller's ③ start bound with M1c (review 2026-11-07, ``ValueError``).
"""

from __future__ import annotations

import argparse
import math
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from typing import Any

from .flow_limit_run import FlowLimitSetting, flow_setting_from_args
from .rod_release import FLOW_LIMITED_LAW, STORED_LAWS

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
EXTEND_START_TAGS = (EXTEND_START_CONTROLLER_TAG, EXTEND_START_LAS_CONTROLLER_TAG,
                     EXTEND_START_LAS_K1_CONTROLLER_TAG)
"""Tags of a run with the ③ start bound (before LAS-b, LAS-b, LAS-b + K1). A list only: the ③
judgement uses :func:`is_extend_start_tag` (a set misses suffix combinations such as
``final_C4G2_P3_K1``, post-switch audit W-1)."""
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
    """

    flow: FlowLimitSetting | None = None
    valve_tau_s: float | None = None
    rod_release_force: bool = False
    check_delay: CheckDelaySetting | None = None
    lock_closure: LockClosureSetting | None = None
    lock_window_follows_plant: bool = False
    extend_start_tracked: bool = False

    def __post_init__(self) -> None:
        if self.lock_window_follows_plant and self.lock_closure is None:
            raise SystemExit("the controller lock window needs the plant lock rule "
                             "(spec 2.6: controller alone is refused)")
        if self.extend_start_tracked:
            check_extend_start(self, EXTEND_START_TRACKED_RULE)

    @property
    def is_any_on(self) -> bool:
        return self != HydraulicOptions()

    def to_dict(self) -> dict[str, Any]:
        """The fields, plus ``m2_law`` with M2 on: the definition digests and metas of M2 runs
        change with the M2 law (revision 5, ``flow_limited_r5``); the M2-off dict stays as it
        was. ``extend_start_tracked`` appears only when on, so the dicts (and digests) of the
        runs without the ③ bound stay as they were (criteria revision 8)."""
        values = asdict(self)
        if not self.extend_start_tracked:
            del values["extend_start_tracked"]
        if self.rod_release_force:
            values["m2_law"] = FLOW_LIMITED_LAW
        return values

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> HydraulicOptions:
        """The options of :meth:`to_dict` (a job description passed to a worker process).

        Raises:
            ValueError: An ``m2_law`` other than the one this code runs (stored
                ``flow_limited_r3`` and ``flow_limited_r4`` runs are refused: this code cannot
                rerun them).
        """
        if values.get("m2_law", FLOW_LIMITED_LAW) != FLOW_LIMITED_LAW:
            raise ValueError(f"M2 law {values['m2_law']!r} is not {FLOW_LIMITED_LAW!r}")
        return cls._from_fields(values)

    @classmethod
    def from_stored(cls, values: dict[str, Any]) -> HydraulicOptions:
        """The options of a stored record, for reading it only (never to rerun it).

        Accepts the M2 laws of :data:`rod_release.STORED_LAWS`; the stored law is dropped, so
        ``to_dict`` of the result names the law of this code. Readers that need only the
        controller-side settings (``t4h_replay``: the lock window) use it.

        Raises:
            ValueError: An ``m2_law`` no revision of this project wrote.
        """
        stored_law = values.get("m2_law", FLOW_LIMITED_LAW)
        if stored_law not in STORED_LAWS:
            raise ValueError(f"M2 law {stored_law!r} is not one of {STORED_LAWS}")
        return cls._from_fields(values)

    @classmethod
    def _from_fields(cls, values: dict[str, Any]) -> HydraulicOptions:
        flow = values.get("flow")
        check_delay = values.get("check_delay")
        lock_closure = values.get("lock_closure")
        return cls(
            flow=None if flow is None else FlowLimitSetting.from_dict(flow),
            valve_tau_s=values.get("valve_tau_s"),
            rod_release_force=bool(values.get("rod_release_force", False)),
            check_delay=None if check_delay is None else CheckDelaySetting.from_dict(check_delay),
            lock_closure=None if lock_closure is None else LockClosureSetting(**lock_closure),
            lock_window_follows_plant=bool(values.get("lock_window_follows_plant", False)),
            extend_start_tracked=bool(values.get("extend_start_tracked", False)))

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


def _check_delay_from_args(args: argparse.Namespace) -> CheckDelaySetting | None:
    given = {key: getattr(args, key)
             for key in ("check_delay_volume_scale", "check_delay_cv") if hasattr(args, key)}
    if not hasattr(args, "check_delay"):
        if given:
            raise SystemExit(f"{sorted(given)} need --check-delay")
        return None
    return CheckDelaySetting(
        kind=args.check_delay,
        volume_scale=given.get("check_delay_volume_scale", DEFAULT_VOLUME_SCALE),
        c_v=given.get("check_delay_cv", DEFAULT_VENT_CLOSING_OPENING))


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
        extend_start_tracked=hasattr(args, "extend_start_tracked"))


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
    plant_options = (options.rod_release_force, options.check_delay, options.lock_closure)
    if engine == "L1" and any(option not in (None, False) for option in plant_options):
        raise SystemExit("M2, M1c and LC are L2b / harness options, not L1 (spec 2.0)")
    closure = options.lock_closure
    if closure is not None and not options.lock_window_follows_plant \
            and closure.closing_delay_s > period_s:
        raise ValueError(f"plant rule alone with t_c {closure.closing_delay_s} s > T {period_s} s: "
                         "the old window would close before the lock (spec 2.6)")
    if closure is not None and options.check_delay is not None \
            and options.check_delay.kind == CheckCircuit.BLOCKED.value:
        raise ValueError("BL with LC is refused (decision D-6: t_c assumes A, B -> T)")
    if lock_valve == "counterbalance" and (closure is not None or options.rod_release_force):
        raise ValueError("LC and M2 are not defined with the counterbalance (spec 2.3, 2.5)")


def check_extend_start(options: HydraulicOptions | None, extend_start_rule: str) -> None:
    """Refuse the ③ start bound with M1c (hydraulics-expert review 2026-11-07, 2c): M1c holds
    the extending leg back, which the bound's speed lower bound does not cover.

    Raises:
        ValueError: ``extend_start_rule`` is ``"tracked_bound"`` and M1c is on.
    """
    if extend_start_rule == "tracked_bound" and options is not None \
            and options.check_delay is not None:
        raise ValueError("extend_start_rule tracked_bound with M1c is refused "
                         "(review 2026-11-07: the speed lower bound does not hold)")


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
    (:func:`apply_lock_window`) and the ③ start bound (``extend_start_tracked``).

    Returns:
        ``config`` itself when both are off (bit-identical path), else a copy.
    """
    config = apply_lock_window(config, options, v_max_m_s, valve_tau_s)
    if not options.extend_start_tracked:
        return config
    two_pressure = replace(config.two_pressure, extend_start_rule=EXTEND_START_TRACKED_RULE)
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


def _split_order_gate_suffix(tag: str) -> tuple[str, bool]:
    """``(tag without a trailing _K1, whether it had one)``."""
    if tag.endswith(ORDER_GATE_TAG_SUFFIX):
        return tag[: -len(ORDER_GATE_TAG_SUFFIX)], True
    return tag, False


def with_liftoff_slow_tag(tag: str | None) -> str:
    """The LAS-b tag of a run tag: ``None`` (the runner's ``final_C4G2``) -> ``final_C4G2_LAS``,
    any other tag gets :data:`LIFTOFF_SLOW_TAG_SUFFIX` once (``ABL`` -> ``ABL_LAS``). A tag
    with the K1 suffix keeps it last (``final_C4G2_K1`` -> ``final_C4G2_LAS_K1``;
    ``final_C4G2_LAS_K1`` is returned as it is)."""
    if tag is None:
        return LAS_CONTROLLER_TAG
    base, has_order_gate = _split_order_gate_suffix(tag)
    if not base.endswith(LIFTOFF_SLOW_TAG_SUFFIX):
        base += LIFTOFF_SLOW_TAG_SUFFIX
    return base + ORDER_GATE_TAG_SUFFIX if has_order_gate else base


def with_order_gate_tag(tag: str | None) -> str:
    """The K1 tag of a run tag: ``None`` (the runner's ``final_C4G2``) -> ``final_C4G2_K1``,
    any other tag gets :data:`ORDER_GATE_TAG_SUFFIX` once (``ABL_LAS`` -> ``ABL_LAS_K1``)."""
    base = FINAL_CONTROLLER_TAG if tag is None else tag
    return base if base.endswith(ORDER_GATE_TAG_SUFFIX) else base + ORDER_GATE_TAG_SUFFIX


def is_liftoff_slow_tag(tag: str | None) -> bool:
    """A recorded tag of a run with LAS-b on (records without a tag ran before the switch);
    true with or without the K1 suffix after ``_LAS`` (``final_C4G2_P3_LAS_K1``)."""
    if tag is None:
        return False
    base, _ = _split_order_gate_suffix(tag)
    return base.endswith(LIFTOFF_SLOW_TAG_SUFFIX)


def is_order_gate_tag(tag: str | None) -> bool:
    """A recorded tag of a run with the LAS-b K1 order gate on (suffix ``_K1``)."""
    return tag is not None and tag.endswith(ORDER_GATE_TAG_SUFFIX)


def switch_base_tag(tag: str) -> str:
    """``tag`` without the switch suffixes :func:`with_switch_tags` adds (a trailing ``_K1``,
    then a trailing ``_LAS``): ``final_C4G2_P3_LAS_K1`` / ``final_C4G2_P3_K1`` ->
    ``final_C4G2_P3``, ``ABL_LAS`` -> ``ABL``."""
    base, _ = _split_order_gate_suffix(tag)
    if base.endswith(LIFTOFF_SLOW_TAG_SUFFIX):
        base = base[: -len(LIFTOFF_SLOW_TAG_SUFFIX)]
    return base


def is_extend_start_tag(tag: str | None) -> bool:
    """A recorded tag of a run with the ③ start bound: its base tag (:func:`switch_base_tag`)
    is :data:`EXTEND_START_CONTROLLER_TAG`, whatever the LAS-b and K1 switches were
    (post-switch audit W-1, user decision (a) 2026-11-10). False for ``None``."""
    return tag is not None and switch_base_tag(tag) == EXTEND_START_CONTROLLER_TAG


def with_switch_tags(tag: str | None, config: Any | None) -> str | None:
    """``tag`` with the suffixes of the switches ``config`` has on: ``_LAS`` (LAS-b), then
    ``_K1`` (order gate). Unchanged (possibly None) when both are off."""
    if is_liftoff_slow_on(config):
        tag = with_liftoff_slow_tag(tag)
    if is_order_gate_on(config):
        tag = with_order_gate_tag(tag)
    return tag


def controller_tag(options: HydraulicOptions | None, config: Any | None = None) -> str | None:
    """Tag of a v5 run: :data:`EXTEND_START_CONTROLLER_TAG` with the ③ start bound, else None
    (the run keeps the tag of its runner, ``final_C4G2``); with ``config`` the suffixes of its
    switches (:func:`with_switch_tags`): ``final_C4G2_P3_LAS_K1`` / ``final_C4G2_LAS_K1`` for the
    preset since the K1 switch, ``_LAS`` alone for LAS-b without the order gate. Without
    ``config`` the tag is the one before the LAS-b switch (callers that know the controller
    pass it)."""
    tag = None
    if options is not None and options.extend_start_tracked:
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


__all__ = [
    "EXTEND_START_LAS_CONTROLLER_TAG",
    "EXTEND_START_LAS_K1_CONTROLLER_TAG",
    "EXTEND_START_TAGS",
    "LAS_CONTROLLER_TAG",
    "LAS_K1_CONTROLLER_TAG",
    "LIFTOFF_SLOW_TAG_SUFFIX",
    "ORDER_GATE_TAG_SUFFIX",
    "is_extend_start_tag",
    "is_liftoff_slow_on",
    "is_liftoff_slow_tag",
    "is_order_gate_on",
    "is_order_gate_tag",
    "with_liftoff_slow_tag",
    "with_order_gate_tag",
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
