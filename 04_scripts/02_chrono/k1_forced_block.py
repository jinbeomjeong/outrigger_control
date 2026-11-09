"""LAS-b K1 forced-block diagnostic controller (research variant, not a design change).

Rules: ``06_analysis/02_control/verif_matrix/las_k1_rules_adopt2.md`` 2.3 (variant ``first``)
and 9.3 (implementation). The rules text wins where this code differs.

:class:`K1ForcedBlockC2Controller` is :class:`C2Controller` with one change: the first
``_is_flat_soil_order_blocked`` call of a run returns True (blocked). That method is only called
when the R4 conditions hold (``c2.py`` ``_apply_slope_clearance_margin`` short-circuits), so the
first call is the run's first R4-evaluated LOC ($L_1$). Every later call returns the original rule
(blocked unless ``n_P > n_S``). Settings, gains, event names and the command path are unchanged;
the decision record is still written by ``c2.py``, so the forced LOC records ``would_block`` true
and ``applied`` false. ``c2.py`` is not modified.

The forced call keeps the original value (``natural_blocked``, ``n_P``, ``n_S``, ``dP``) and every
call is listed; both are added to ``meta()["k1_forced_block"]``.

Used by ``run_S9.py level --k1-forced-block first`` (cad-expert) instead of
:meth:`C2Controller.from_params`; the class name and this module path are fixed by the rules.
"""

from __future__ import annotations

import dataclasses
import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MODULE_PATH = Path(__file__).resolve()
SOURCE_DIR = MODULE_PATH.parents[2] / "03_src"
if str(SOURCE_DIR) not in sys.path:  # same convention as run_S9.py (the package is not installed)
    sys.path.insert(0, str(SOURCE_DIR))

from outrigger_sim.control.c2 import C2Config, C2Controller, C2Geometry, _SoilState  # noqa: E402

FORCED_MODE = "first"
"""Rules 2.3: only the first ``_is_flat_soil_order_blocked`` call of a run is forced."""
META_KEY = "k1_forced_block"
REQUIRED_CONTROLLER_METHODS = (
    "_is_flat_soil_order_blocked",
    "_flat_soil_order_periods",
    "_soil_state",
    "meta",
    "reset",
)
"""Private ``C2Controller`` methods this variant overrides or calls (rules 9.3)."""
REQUIRED_SOIL_STATE_FIELDS = ("liftoff_s",)
"""``_SoilState.liftoff_s`` holds the LOC time while ``_apply_slope_clearance_margin`` runs."""


def _check_controller_interface() -> None:
    """Stop at import when ``c2.py`` no longer has the private names this variant relies on."""
    missing = [
        name
        for name in REQUIRED_CONTROLLER_METHODS
        if not callable(getattr(C2Controller, name, None))
    ]
    soil_fields = {item.name for item in dataclasses.fields(_SoilState)}
    missing += [
        f"_SoilState.{name}" for name in REQUIRED_SOIL_STATE_FIELDS if name not in soil_fields
    ]
    if missing:
        raise ImportError(
            f"k1_forced_block: C2Controller has no {', '.join(missing)}; the forced-block variant "
            "(las_k1_rules_adopt2.md 9.3) must be revised before it is used"
        )


_check_controller_interface()


def module_sha256() -> str:
    """sha256 of this file's raw bytes (the work-tree file, CRLF in a Windows checkout)."""
    return hashlib.sha256(MODULE_PATH.read_bytes()).hexdigest()


MODULE_SHA256_AT_IMPORT = module_sha256()
"""The digest of the code that was imported (recorded in the meta)."""


@dataclass
class _ForcedBlockRecord:
    """Per-run bookkeeping of the forced call and of every ``_is_flat_soil_order_blocked`` call."""

    has_forced: bool = False
    forced_t_loc_s: float | None = None
    forced_n_loc: int | None = None
    natural_blocked: bool | None = None
    n_P: int | None = None
    n_S: int | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def note_forced(
        self,
        t_loc_s: float | None,
        period_s: float,
        natural_blocked: bool,
        n_P: int | None,
        n_S: int | None,
    ) -> None:
        self.has_forced = True
        self.forced_t_loc_s = t_loc_s
        # rules 0: whole periods with Python round (the c2.py _flat_soil_order_periods rule)
        self.forced_n_loc = None if t_loc_s is None else round(t_loc_s / period_s)
        self.natural_blocked = natural_blocked
        self.n_P = n_P
        self.n_S = n_S

    def to_meta(self) -> dict[str, Any]:
        has_both = self.n_P is not None and self.n_S is not None
        return {
            "forced_t_loc_s": self.forced_t_loc_s,
            "forced_n_loc": self.forced_n_loc,
            "natural_blocked": self.natural_blocked,
            "n_P": self.n_P,
            "n_S": self.n_S,
            "dP": self.n_P - self.n_S if has_both else None,
            "calls": [dict(call) for call in self.calls],
        }


class K1ForcedBlockC2Controller(C2Controller):
    """:class:`C2Controller` whose first K1 order decision of a run is forced to "blocked".

    Args:
        geometry: Machine quantities, usually :meth:`C2Geometry.from_params`.
        config: The run's C2 config; ``None`` = the class defaults of :class:`C2Config`.

    Raises:
        ValueError: The config has the K1 order gate off
            (``slope_clearance_margin.flat_soil_margin_order_gate`` false). A forced block has
            no effect without the gate (rules 2.3).
    """

    def __init__(self, geometry: C2Geometry, config: C2Config | None = None) -> None:
        super().__init__(geometry, config)
        if not self.config.slope_clearance_margin.flat_soil_margin_order_gate:
            raise ValueError(
                "K1ForcedBlockC2Controller needs the K1 order gate on "
                "(slope_clearance_margin.flat_soil_margin_order_gate, run_S9 --k1-order-gate on)"
            )
        self._forced_block = _ForcedBlockRecord()

    def reset(self) -> None:
        """:meth:`C2Controller.reset`; a new run forces its own first call again."""
        super().reset()
        self._forced_block = _ForcedBlockRecord()

    def _is_flat_soil_order_blocked(self) -> bool:
        natural_blocked = super()._is_flat_soil_order_blocked()
        n_P, n_S = self._flat_soil_order_periods()
        record = self._forced_block
        is_forced = not record.has_forced
        # _confirm_liftoff stores the LOC time in liftoff_s just before this call
        t_loc_s = self._soil_state().liftoff_s
        if is_forced:
            record.note_forced(t_loc_s, self.config.period_s, natural_blocked, n_P, n_S)
        is_blocked = True if is_forced else natural_blocked
        record.calls.append(
            {"t_s": t_loc_s, "forced": is_forced, "result": is_blocked, "n_P": n_P, "n_S": n_S}
        )
        return is_blocked

    def meta(self) -> dict[str, Any]:
        """:meth:`C2Controller.meta` plus ``k1_forced_block`` (rules 2.3 record fields)."""
        meta = super().meta()
        cls = type(self)
        meta[META_KEY] = {
            "mode": FORCED_MODE,
            "class": f"{cls.__module__}.{cls.__qualname__}",
            "module_sha256": MODULE_SHA256_AT_IMPORT,
            **self._forced_block.to_meta(),
        }
        return meta
