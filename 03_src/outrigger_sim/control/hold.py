"""The empty controller: every leg stopped (plan S6 smoke test of the closed loop)."""

from __future__ import annotations

from typing import Any

from outrigger_sim.signals import DEFAULT_CONTROL_PERIOD_S, Command, Measurements

HOLD_CONTROLLER_NAME = "hold"


class HoldController:
    """Commands zero speed on every leg; has no state.

    Args:
        period_s: Control period (s).
    """

    def __init__(self, period_s: float = DEFAULT_CONTROL_PERIOD_S) -> None:
        if not period_s > 0.0:
            raise ValueError(f"period_s must be > 0, got {period_s!r}")
        self._period_s = float(period_s)

    @property
    def period_s(self) -> float:
        """Control period (s)."""
        return self._period_s

    def reset(self) -> None:
        """Nothing to clear."""

    def update(self, measurements: Measurements) -> Command:
        """Zero speed on every leg, issued at the measurement time."""
        return Command.stopped(measurements.t_s)

    def meta(self) -> dict[str, Any]:
        """Name and period."""
        return {"controller": HOLD_CONTROLLER_NAME, "period_s": self._period_s}
