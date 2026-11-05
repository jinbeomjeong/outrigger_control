"""Options of the v5 hydraulic coupling (``00_docs/02_hydraulic/v5_hydraulic_impl_spec.md`` 2.0).

Engine independent (no pychrono). **Every option is off by default**: a run without them keeps its
``vars(args)``, its meta and its result (D-5 is not switched). All numbers an option carries
are ASSUMPTIONS (spec 2.4, 2.5); U-R8-9 and the manufacturer answers replace them.

Combinations refused here:
  * rod-side lock window of the controller without the plant lock rule (spec 2.6, ``SystemExit``);
  * circuit BL with the lock closure (decision D-6, ``ValueError``).
"""

from __future__ import annotations

import argparse
import math
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from .flow_limit_run import FlowLimitSetting, flow_setting_from_args

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
    """

    flow: FlowLimitSetting | None = None
    valve_tau_s: float | None = None
    rod_release_force: bool = False
    check_delay: CheckDelaySetting | None = None
    lock_closure: LockClosureSetting | None = None
    lock_window_follows_plant: bool = False

    def __post_init__(self) -> None:
        if self.lock_window_follows_plant and self.lock_closure is None:
            raise SystemExit("the controller lock window needs the plant lock rule "
                             "(spec 2.6: controller alone is refused)")

    @property
    def is_any_on(self) -> bool:
        return self != HydraulicOptions()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
        lock_window_follows_plant=hasattr(args, "lock_window_follows_plant"))


__all__ = [
    "LOCK_SPEED_EPS_M_S",
    "CheckCircuit",
    "CheckDelaySetting",
    "HydraulicOptions",
    "LockClosureSetting",
    "add_hydraulic_arguments",
    "hydraulic_options_from_args",
]
