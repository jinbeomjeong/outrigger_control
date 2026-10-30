"""P-S8-37 candidates (control spec 428.5.2, 427.11): R1' twist ledger and R4 flat-soil margin.

Harness-only subclass factory on any C2 class (03_src unchanged until adoption). The wrapper
``s9_slope_fix_candidates.py`` (tokens ``P37t``, ``R4c20``, ``R4c30``) and, through that
wrapper's ``_install_candidate``, the study A screen (``R426A_CANDIDATE``) and the r67 screen
(``R67_CANDIDATE``) put the same class on top of their controller.

R1' twist ledger (token ``P37t``)
  Reference: when a re-approach starts after the LOC, the rod-stroke twist
  ``tau = (x_FL - x_FR) - (x_RL - x_RR)`` of that period is kept for the leg.
  Offset: once that re-approach ended in contact and the completion-filter attitude deviation is
  below ``settle_attitude_rad`` (default ``done_attitude_rad``) with no re-approach active,
  ``d_leg += sign_leg * (tau - tau_ref)`` when ``|tau - tau_ref| >= min_twist_m``; the ledger of
  a leg is cut to ``+-max_offset_m`` (``INFO_FLOOR_DROP_OFFSET:<leg>:<mm>``).
  Use: the clearance paths read ``c_k(x - d)`` (crawler zone, heave loop, completion, lift
  guard; the S-3 bias / P-S8-28 anchor are applied on top, the two add).
  Hold (spec 428.5.3 item 3): while any re-approach is active (a lifted leg spoils tau) a
  contacted run is held, not skipped; it is booked in the first settled period after all
  re-approaches ended (``applied`` row ``deferred`` True when it waited on another re-approach).
  A run still held at the next LOC, at a LOC revocation or at the run end is recorded as
  ``skipped`` with reason ``pending_at_end`` (``at`` = ``new_loc`` / ``loc_revoked`` /
  ``run_end``); the run-end rows are added by ``floor_twist_record`` (state unchanged).
  ASSUMPTIONS (spec 428.5.3 items 1, 2 accepted): the ledger is cleared at every confirmed LOC
  (the S-3 bias of a new LOC already sees the floor); a LOC revocation drops the held runs but
  keeps the booked offsets until the next LOC; a run that ended without contact gives no
  offset; a later run of a leg still waiting keeps the older reference.
  Record (spec 428.5.3 item 1, record only): every LOC revocation that leaves a booked offset in
  the ledger (it then stays until the next LOC or the run end) adds one to
  ``p37_offset_across_revoke``.

R4 flat-soil clearance margin (tokens ``R4c20`` / ``R4c30``)
  At a confirmed LOC with the soil mode used in the lifting cycle, a known settle tilt at most
  the P-S8-31 ``tilt_min_rad`` (1 deg) and no run clearance target raised yet (P-S8-31 not
  applied), the run's clearance target becomes ``thresholds.clearance_target_m + margin_m``
  (``INFO_LOC_FLAT_SOIL_MARGIN:<target mm>``). It is judged again at the next LOC only when a
  revocation reset the run target (the P-S8-31 rule of ``keep_slope_margin_on_revoke``).

With ``enable`` False and ``flat_soil_margin_m`` 0 the factory returns ``base_class`` itself.
Units SI.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

TWIST_SIGNS = np.array([1.0, -1.0, -1.0, 1.0])
"""Twist coefficient sign per leg, order FL, FR, RL, RR."""
LEG_NAMES = ("FL", "FR", "RL", "RR")
OFFSET_EVENT = "INFO_FLOOR_DROP_OFFSET"
"""``INFO_FLOOR_DROP_OFFSET:<leg>:<ledger mm after the update>``."""
FLAT_MARGIN_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN"
"""``INFO_LOC_FLAT_SOIL_MARGIN:<effective target mm, integer>``."""
CONTACT_OUTCOME = "contact"
RECORD_ROWS_MAX = 20
SKIP_BELOW_MIN = "below_min"
SKIP_PENDING_AT_END = "pending_at_end"
"""A held run that never got its settled period before the ledger was dropped."""
PENDING_END_NEW_LOC = "new_loc"
PENDING_END_LOC_REVOKED = "loc_revoked"
PENDING_END_RUN_END = "run_end"


@dataclass(frozen=True)
class FloorTwistSettings:
    """R1' ledger and R4 margin settings (both off by default)."""

    enable: bool = False
    """R1' twist ledger (token P37t)."""
    min_twist_m: float = 0.005
    """|delta tau| below this gives no offset (ASSUMPTION, spec 428.5.2)."""
    max_offset_m: float = 0.06
    """Ledger limit per leg (ASSUMPTION, spec 428.5.2)."""
    settle_attitude_rad: float | None = None
    """Completion deviation that counts as settled; None = ``done_attitude_rad``."""
    flat_soil_margin_m: float = 0.0
    """R4 margin; 0 = R4 off (tokens R4c20 / R4c30: 0.02 / 0.03 m)."""

    def __post_init__(self) -> None:
        if self.min_twist_m <= 0.0 or self.max_offset_m <= 0.0:
            raise ValueError("min_twist_m and max_offset_m must be > 0")
        if self.flat_soil_margin_m < 0.0:
            raise ValueError(f"flat_soil_margin_m must be >= 0, got {self.flat_soil_margin_m}")

    @property
    def is_active(self) -> bool:
        return self.enable or self.flat_soil_margin_m > 0.0


@dataclass
class FloorTwistState:
    """Per-run bookkeeping of the R1' ledger and the R4 margin."""

    offsets_m: np.ndarray = field(default_factory=lambda: np.zeros(len(LEG_NAMES)))
    pending: dict = field(default_factory=dict)
    """leg -> {t_start_s, tau_ref_m, contacted, deferred}: re-approaches waiting for their
    offset; ``deferred`` = a contacted run was held because another re-approach was active."""
    applied: list = field(default_factory=list)
    """{t_s, leg, d_tau_mm, offset_mm, capped, deferred} of every ledger update."""
    skipped: list = field(default_factory=list)
    """{t_s, leg, d_tau_mm, reason} of settled re-approaches that gave no offset (``below_min``)
    and {t_s, leg, reason, at, t_start_s, contacted, deferred} of held runs dropped before
    their settled period (``pending_at_end``)."""
    ledger_clears: int = 0
    pending_dropped: int = 0
    """Held runs dropped at a new LOC or a LOC revocation (all, also beyond the row limit)."""
    flat_margins: list = field(default_factory=list)
    """{t_s, target_mm} of every R4 application."""
    offset_across_revoke: int = 0
    """LOC revocations passed with a booked (nonzero) offset in the ledger (spec 428.5.3)."""
    offset_across_revoke_rows: list = field(default_factory=list)
    """{t_s, offsets_mm} of those revocations (first ``RECORD_ROWS_MAX``)."""


def rod_twist_m(rod_stroke_m) -> float:
    """``tau = (x_FL - x_FR) - (x_RL - x_RR)`` [m]."""
    return float(TWIST_SIGNS @ np.asarray(rod_stroke_m, dtype=float))


def twist_offset_increment_m(leg: int, tau_ref_m: float, tau_now_m: float,
                             min_twist_m: float) -> float | None:
    """Ledger increment of ``leg`` for a twist change, ``sign_leg * delta tau``; None below
    ``min_twist_m``."""
    delta_m = tau_now_m - tau_ref_m
    if abs(delta_m) < min_twist_m:
        return None
    return float(TWIST_SIGNS[leg] * delta_m)


def is_flat_soil_margin_due(soil_mode_used: bool, settle_rad: tuple[float, float] | None,
                            tilt_max_rad: float, has_run_target: bool) -> bool:
    """R4 conditions at a LOC (see the module docstring)."""
    if not soil_mode_used or has_run_target or settle_rad is None:
        return False
    return max(abs(settle_rad[0]), abs(settle_rad[1])) <= tilt_max_rad


def pending_at_end_row(t_s: float, leg: int, run: dict, at: str) -> dict:
    """``skipped`` row of a held run dropped before its settled period."""
    return {"t_s": round(float(t_s), 2), "leg": LEG_NAMES[leg], "reason": SKIP_PENDING_AT_END,
            "at": at, "t_start_s": round(float(run["t_start_s"]), 2),
            "contacted": bool(run["contacted"]), "deferred": bool(run.get("deferred", False))}


def _run_end_time_s(controller) -> float | None:
    reading = getattr(getattr(controller, "_state", None), "last_reading", None)
    return None if reading is None else float(reading.t_s)


def floor_twist_record(controller) -> dict | None:
    """Run record of the P-S8-37 layer (None on a controller without it).

    Runs still held at the run end are added to ``skipped`` as ``pending_at_end`` / ``run_end``
    rows (the controller state is not changed); ``pending_legs`` keeps naming them.
    """
    state = getattr(controller, "p37_state", None)
    if state is None:
        return None
    skipped = list(state.skipped)
    end_s = _run_end_time_s(controller)
    for leg, run in sorted(state.pending.items()):
        row_s = run["t_start_s"] if end_s is None else end_s
        skipped.append(pending_at_end_row(row_s, leg, run, PENDING_END_RUN_END))
    return {"offsets_mm": [round(float(v) * 1e3, 2) for v in state.offsets_m],
            "applied": list(state.applied[:RECORD_ROWS_MAX]),
            "skipped": skipped[:RECORD_ROWS_MAX],
            "pending_legs": [LEG_NAMES[leg] for leg in sorted(state.pending)],
            "pending_at_end_n": state.pending_dropped + len(state.pending),
            "ledger_clears": state.ledger_clears,
            "flat_margins": list(state.flat_margins),
            "p37_offset_across_revoke": state.offset_across_revoke,
            "offset_across_revoke_rows": list(state.offset_across_revoke_rows)}


def has_floor_twist_acted(record: dict | None) -> bool:
    """A ledger offset or an R4 margin changed the run (the wrapper "acted" rule)."""
    if not record:
        return False
    return bool(record.get("applied") or record.get("flat_margins"))


def make_floor_twist_class(c2, base_class, settings: FloorTwistSettings):
    """Subclass of ``base_class`` with the R1' ledger and / or the R4 margin of ``settings``;
    ``base_class`` itself when both are off (commands bit for bit)."""
    if not settings.is_active:
        return base_class

    class FloorTwistC2(base_class):
        floor_twist = settings

        def reset(self) -> None:
            super().reset()
            self.p37_state = FloorTwistState()

        def _p37(self) -> FloorTwistState:
            state = getattr(self, "p37_state", None)
            if state is None:  # a controller used before its first reset
                state = self.p37_state = FloorTwistState()
            return state

        # ------------------------------------------------------------ R1' ledger
        def update(self, measurements):
            command = super().update(measurements)
            if settings.enable:
                self._p37_settle_pending(float(measurements.t_s))
            return command

        def _begin_reapproach(self, leg, reading, lifted_settings) -> None:
            super()._begin_reapproach(leg, reading, lifted_settings)
            if not settings.enable or not self._is_liftoff_confirmed():
                return
            self._p37().pending.setdefault(int(leg), {
                "t_start_s": float(reading.t_s), "tau_ref_m": rod_twist_m(reading.rod_stroke_m),
                "contacted": False, "deferred": False})

        def _end_reapproach(self, leg, reading, outcome) -> None:
            super()._end_reapproach(leg, reading, outcome)
            pending = self._p37().pending
            if int(leg) not in pending:
                return
            if outcome == CONTACT_OUTCOME:
                pending[int(leg)]["contacted"] = True
            else:
                del pending[int(leg)]

        def _p37_settle_attitude_rad(self) -> float:
            if settings.settle_attitude_rad is not None:
                return settings.settle_attitude_rad
            return self.config.thresholds.done_attitude_rad

        def _p37_settle_pending(self, t_s: float) -> None:
            ledger = self._p37()
            if not ledger.pending:
                return
            if not self._is_liftoff_confirmed():  # LOC revoked: the stroke reference is gone
                self._p37_drop_pending(t_s, PENDING_END_LOC_REVOKED)
                return
            if self._state.active_reapproaches:
                self._p37_mark_deferred()
                return
            if self._completion_deviation_rad() >= self._p37_settle_attitude_rad():
                return
            reading = self._state.last_reading
            tau_now_m = rod_twist_m(reading.rod_stroke_m)
            for leg, run in sorted(ledger.pending.items()):
                if run["contacted"]:
                    self._p37_book(t_s, leg, run, tau_now_m)
            ledger.pending = {leg: run for leg, run in ledger.pending.items()
                              if not run["contacted"]}

        def _revoke_loc(self, t_s: float, rise_N: float) -> None:
            super()._revoke_loc(t_s, rise_N)
            ledger = self._p37()
            if not settings.enable or not ledger.offsets_m.any():
                return
            # record only: the booked offsets stay until the next LOC (spec 428.5.3 item 1)
            ledger.offset_across_revoke += 1
            if len(ledger.offset_across_revoke_rows) < RECORD_ROWS_MAX:
                ledger.offset_across_revoke_rows.append(
                    {"t_s": round(float(t_s), 2),
                     "offsets_mm": [round(float(v) * 1e3, 2) for v in ledger.offsets_m]})

        def _p37_mark_deferred(self) -> None:
            """Held runs that already made contact wait on another re-approach (record only)."""
            for run in self._p37().pending.values():
                if run["contacted"]:
                    run["deferred"] = True

        def _p37_drop_pending(self, t_s: float, at: str) -> None:
            """Record every held run as ``pending_at_end`` and empty the pending list."""
            ledger = self._p37()
            for leg, run in sorted(ledger.pending.items()):
                ledger.pending_dropped += 1
                if len(ledger.skipped) < RECORD_ROWS_MAX:
                    ledger.skipped.append(pending_at_end_row(t_s, leg, run, at))
            ledger.pending = {}

        def _p37_book(self, t_s: float, leg: int, run: dict, tau_now_m: float) -> None:
            ledger = self._p37()
            tau_ref_m = run["tau_ref_m"]
            d_tau_mm = round((tau_now_m - tau_ref_m) * 1e3, 2)
            increment_m = twist_offset_increment_m(leg, tau_ref_m, tau_now_m,
                                                   settings.min_twist_m)
            if increment_m is None:
                if len(ledger.skipped) < RECORD_ROWS_MAX:
                    ledger.skipped.append({"t_s": round(t_s, 2), "leg": LEG_NAMES[leg],
                                           "d_tau_mm": d_tau_mm, "reason": SKIP_BELOW_MIN})
                return
            unclipped_m = float(ledger.offsets_m[leg]) + increment_m
            limit_m = settings.max_offset_m
            ledger.offsets_m[leg] = min(limit_m, max(-limit_m, unclipped_m))
            offset_mm = round(float(ledger.offsets_m[leg]) * 1e3, 2)
            ledger.applied.append({"t_s": round(t_s, 2), "leg": LEG_NAMES[leg],
                                   "d_tau_mm": d_tau_mm, "offset_mm": offset_mm,
                                   "capped": abs(unclipped_m) > limit_m,
                                   "deferred": bool(run.get("deferred", False))})
            self._add_event(t_s, f"{OFFSET_EVENT}:{LEG_NAMES[leg]}:{offset_mm:.1f}")

        def _clearance_corners_m(self, rod_stroke_m):
            offsets_m = self._p37().offsets_m
            if not offsets_m.any():
                return super()._clearance_corners_m(rod_stroke_m)
            return super()._clearance_corners_m(np.asarray(rod_stroke_m, dtype=float)
                                                - offsets_m)

        # ------------------------------------------------------------ LOC hook (both)
        def _apply_slope_clearance_margin(self, t_s: float) -> None:
            """Called by ``_confirm_liftoff`` at every confirmed LOC, after the S-3 bias."""
            super()._apply_slope_clearance_margin(t_s)
            ledger = self._p37()
            if settings.enable and (ledger.offsets_m.any() or ledger.pending):
                ledger.offsets_m = np.zeros(len(LEG_NAMES))
                self._p37_drop_pending(t_s, PENDING_END_NEW_LOC)
                ledger.ledger_clears += 1
            if settings.flat_soil_margin_m > 0.0:
                self._p37_apply_flat_soil_margin(t_s)

        def _p37_apply_flat_soil_margin(self, t_s: float) -> None:
            soil = self._soil_state()
            state = self._state
            tilt_max_rad = self.config.slope_clearance_margin.tilt_min_rad
            if not is_flat_soil_margin_due(soil.soil_mode_start_s is not None,
                                           self._settle_attitude_rad(), tilt_max_rad,
                                           state.clearance_target_m is not None):
                return
            target_m = self.config.thresholds.clearance_target_m + settings.flat_soil_margin_m
            state.clearance_target_m = target_m
            self._p37().flat_margins.append({"t_s": round(float(t_s), 2),
                                             "target_mm": round(target_m * 1e3, 1)})
            self._add_event(t_s, f"{FLAT_MARGIN_EVENT}:{target_m * 1e3:.0f}")

    FloorTwistC2.__name__ = FloorTwistC2.__qualname__ = f"FloorTwist{base_class.__name__}"
    return FloorTwistC2
