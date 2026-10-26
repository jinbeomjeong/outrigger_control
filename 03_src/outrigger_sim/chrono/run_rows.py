"""Per-period (10 Hz) record helpers shared by the Chrono runners (control decision (가),
2026-10-26): the leg the C2 probe moves, recorded only (the command is not touched).

``probed_leg`` reads the controller's own P-R8-11 rule (``C2Controller._probed_leg``: the leg
of the running probe round or of its re-ground step; ``None`` outside PROBE or before the
round has started) after the control call, i.e. for the phase the row's ``phase`` column
shows. Wrappers with an ``inner`` controller (e.g. ``run_S8C.RodFaultInjection``) are
unwrapped. A controller without the method gives ``None`` (getattr rule).

Arrays (``r8_series.npz``) store the index 0..3 (FL, FR, RL, RR) as int8 with
:data:`PROBED_LEG_NONE` (-1) for ``None``; JSON rows (S9 ``s9_rows``) store the index or null.

No pychrono import.
"""

from __future__ import annotations

from typing import Any

PROBED_LEG_NONE = -1
"""Array value of ``probed_leg`` = None (not in PROBE / round not started)."""

PROBED_LEG_SOURCE = "C2Controller._probed_leg() after the control call (P-R8-11 rule)"


def probed_leg(controller: Any) -> int | None:
    """Leg index the probe moves now, or ``None`` (module docstring). Read only."""
    c2 = getattr(controller, "inner", controller)
    method = getattr(c2, "_probed_leg", None)
    if not callable(method):
        return None
    leg = method()
    return None if leg is None else int(leg)


def probed_leg_code(controller: Any) -> int:
    """:func:`probed_leg` as an array value (``None`` -> :data:`PROBED_LEG_NONE`)."""
    leg = probed_leg(controller)
    return PROBED_LEG_NONE if leg is None else leg


R8_SERIES_NAME = "r8_series.npz"


class MinimalR8Series:
    """``r8_series.npz`` for runners without ``run_S6C.R8Series`` (S9 ``level``): per control
    call ``t`` (absolute s), ``phase`` (after the call), ``issued_u`` (m/s), ``computed_u``
    (P-R8-6 ``computed_output_m_s`` before the output delay, NaN when absent) and
    ``probed_leg`` (int8, :data:`PROBED_LEG_NONE` = none) with the same names and meaning as
    ``R8Series``, so ``control/r5_fallback_replay.py`` reads both. Record only."""

    def __init__(self, controller: Any) -> None:
        self.controller = controller
        self.rows: dict[str, list[Any]] = {k: [] for k in
                                           ("t", "phase", "issued_u", "computed_u", "probed_leg")}

    def __call__(self, meas: Any, command: Any) -> None:
        import math
        from collections.abc import Mapping

        c2 = self.controller
        comp = getattr(c2, "computed_output_m_s", None)
        comp = comp() if callable(comp) else comp
        if isinstance(comp, Mapping):
            comp = comp.get("computed_u", comp.get("u"))
        r = self.rows
        r["t"].append(float(meas.t_s))
        phase = getattr(c2, "phase", None)
        r["phase"].append(str(getattr(phase, "value", phase)))
        r["issued_u"].append([float(v) for v in command.leg_speed_m_s])
        r["computed_u"].append([math.nan] * 4 if comp is None else [float(v) for v in comp])
        r["probed_leg"].append(probed_leg_code(c2))

    def save(self, path: Any) -> dict[str, Any]:
        import numpy as np

        arr = {"t": np.asarray(self.rows["t"], dtype=float),
               "phase": np.asarray(self.rows["phase"], dtype="U16"),
               "issued_u": np.asarray(self.rows["issued_u"], dtype=float).reshape(-1, 4),
               "computed_u": np.asarray(self.rows["computed_u"], dtype=float).reshape(-1, 4),
               "probed_leg": np.asarray(self.rows["probed_leg"], dtype=np.int8)}
        np.savez_compressed(path, **arr)
        return {"file": getattr(path, "name", str(path)), "samples": len(self.rows["t"]),
                "keys": sorted(arr), "kind": "MinimalR8Series (subset of run_S6C.R8Series)",
                "probed_leg": f"leg index 0..3 (FL, FR, RL, RR) after the call, {PROBED_LEG_NONE} = "
                              f"none; {PROBED_LEG_SOURCE}",
                "units": "t s (absolute), issued_u / computed_u m/s"}


__all__ = ["MinimalR8Series", "PROBED_LEG_NONE", "PROBED_LEG_SOURCE", "R8_SERIES_NAME",
           "probed_leg", "probed_leg_code"]
