"""Controller protocol: the controller side of the engine / controller boundary.

``00_docs/03_chrono/chrono_build_plan.md`` 3.3 and S6. Contract every controller follows:

* **Input is** :class:`Measurements` **only.** The runner calls :meth:`Controller.update` once
  per control period with the delivered sensor values; a controller never sees
  ``TruthState`` (plan S6 risk 1).
* **Output is a** :class:`Command` issued at the measurement time
  (``command.t_s == measurements.t_s``). The engine holds it until the next command
  (zero-order hold) and applies speed limits, stroke ends and the 210 bar cut-off itself.
* **Period.** :attr:`Controller.period_s` is the control period the controller was designed
  for (default 20 ms, :data:`outrigger_sim.signals.DEFAULT_CONTROL_PERIOD_S`); the runner
  calls ``update`` at that period and the controller may rely on it (filters, integrators).
* **Reset.** :meth:`Controller.reset` clears every internal state (filters, integrators,
  phase, probe bookkeeping) so the next ``update`` starts a fresh run.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from outrigger_sim.signals import Command, Measurements


@runtime_checkable
class Controller(Protocol):
    """A leveling controller seen by the runner.

    ``isinstance(obj, Controller)`` only checks that the members exist; the behaviour is
    the module docstring's contract.
    """

    @property
    def period_s(self) -> float:
        """Control period the controller expects between two updates (s)."""
        ...

    def reset(self) -> None:
        """Clear all internal state before a new run."""
        ...

    def update(self, measurements: Measurements) -> Command:
        """Command for the next period from the measurements of this sample."""
        ...

    def meta(self) -> dict[str, Any]:
        """JSON-serialisable name and settings for the run meta (a new dict per call)."""
        ...
