"""M2: rod pressure of a moving leg shifts the oil reference (engine independent, no pychrono).

``00_docs/02_hydraulic/v5_hydraulic_impl_spec.md`` 2.3 (rule of ``pressure_review_report.md`` 12.4).
At the same net force a rod pressure ``p_r`` compresses the head oil column by another
``A_ann p_r / k_h``, so a moving leg's ``s_ref`` moves by that amount when ``p_r`` changes::

    d s_ref^k = A_ann (p_r^(k-1) - p_r^k) / k_h   moving legs, 0 on locked legs
    force change at a fixed body = (k_2 / k_h) A_ann d p_r

Both directions (decision D-4). **Off by default**: nothing here runs without the option. The rod
pressure is a model value of the plant law, not a measured one: ``p_bB`` 5 bar, ``tau`` 0.05 s and
``p_r0`` are ASSUMPTIONS (spec 2.3).

The shift is clipped to the travel range: a reference outside it would be clipped back by the next
speed reference step, which turns the difference into a large speed. Clipped steps are counted.

Units SI; gauge pressures; arrays per leg.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

PREVIOUS_PRESSURE_KEY = "m2_p_prev_Pa"
SHIFT_TOTAL_KEY = "m2_shift_total_m"
CLIPPED_STEPS_KEY = "m2_clipped_steps"
"""Optional snapshot keys (written only with the option on)."""


class RodReleaseShift:
    """Reference shift per step and its record (module docstring).

    Args:
        annulus_area_m2: ``A_ann`` per leg.
    """

    def __init__(self, annulus_area_m2: ArrayLike) -> None:
        self._annulus_area_m2 = np.array(annulus_area_m2, dtype=float).reshape(-1)
        leg_count = self._annulus_area_m2.size
        self._previous_pressure_Pa: NDArray[np.float64] | None = None
        self._shift_total_m = np.zeros(leg_count)
        self._clipped_steps = np.zeros(leg_count, dtype=np.int64)
        self._clip_times_s: list[list[float]] = [[] for _ in range(leg_count)]

    @property
    def shift_total_m(self) -> NDArray[np.float64]:
        """Accumulated shift per leg: it moves the stroke reading too (spec 2.3)."""
        return self._shift_total_m.copy()

    @property
    def clipped_steps(self) -> NDArray[np.int64]:
        return self._clipped_steps.copy()

    @property
    def clip_times_s(self) -> list[list[float]]:
        """Per leg the step times of the clipped steps that were given a ``t_s`` (v5 criteria
        rev. 2 2.1: split before / after the first lift-off). Not part of the snapshot."""
        return [list(times) for times in self._clip_times_s]

    def forget_pressure(self) -> None:
        """The next call starts from its own pressure (rod law disarmed: no pressure exists)."""
        self._previous_pressure_Pa = None

    def seed_pressure(self, leg: int, pressure_Pa: float) -> None:
        """Previous pressure of ``leg``: M1c has already moved the reference to this pressure."""
        if self._previous_pressure_Pa is not None:
            self._previous_pressure_Pa[leg] = pressure_Pa

    def shift_m(self, rod_pressure_Pa: ArrayLike, head_stiffness_N_m: ArrayLike,
                is_moving: ArrayLike, room_down_m: ArrayLike, room_up_m: ArrayLike,
                *, t_s: float | None = None) -> NDArray[np.float64]:
        """Advance one step; the amount to add to ``s_ref`` per leg [m].

        Args:
            rod_pressure_Pa: ``p_r`` of this step (before any pressure split floor).
            head_stiffness_N_m: ``k_h`` per leg.
            is_moving: False on locked legs.
            room_down_m: Allowed shift towards the lower limit, ``<= 0``.
            room_up_m: Allowed shift towards the upper limit, ``>= 0``.
            t_s: Step time; a clipped leg records it (:attr:`clip_times_s`). None = no time.
        """
        pressure_Pa = np.array(rod_pressure_Pa, dtype=float)
        previous_Pa = (pressure_Pa if self._previous_pressure_Pa is None
                       else self._previous_pressure_Pa)
        wanted_m = np.where(is_moving, self._annulus_area_m2 * (previous_Pa - pressure_Pa)
                            / np.asarray(head_stiffness_N_m, dtype=float), 0.0)
        shift_m = np.clip(wanted_m, room_down_m, room_up_m)
        is_clipped = shift_m != wanted_m
        self._clipped_steps += is_clipped
        if t_s is not None:
            for leg in np.flatnonzero(is_clipped):
                self._clip_times_s[leg].append(float(t_s))
        self._shift_total_m += shift_m
        self._previous_pressure_Pa = pressure_Pa
        return shift_m

    def state_arrays(self) -> dict[str, NDArray[Any]]:
        arrays: dict[str, NDArray[Any]] = {SHIFT_TOTAL_KEY: self._shift_total_m.copy(),
                                           CLIPPED_STEPS_KEY: self._clipped_steps.copy()}
        if self._previous_pressure_Pa is not None:
            arrays[PREVIOUS_PRESSURE_KEY] = self._previous_pressure_Pa.copy()
        return arrays

    def restore_state(self, arrays: Mapping[str, NDArray[Any]]) -> None:
        """A snapshot without the keys continues from the current pressure with a zero record.
        The clip times are not in the snapshot: they restart empty."""
        leg_count = self._annulus_area_m2.size
        self._clip_times_s = [[] for _ in range(leg_count)]
        self._previous_pressure_Pa = None
        if PREVIOUS_PRESSURE_KEY in arrays:
            self._previous_pressure_Pa = np.array(arrays[PREVIOUS_PRESSURE_KEY], dtype=float)
        self._shift_total_m = np.array(arrays.get(SHIFT_TOTAL_KEY, np.zeros(leg_count)),
                                       dtype=float)
        self._clipped_steps = np.array(arrays.get(CLIPPED_STEPS_KEY, np.zeros(leg_count)),
                                       dtype=np.int64)

    def record(self) -> dict[str, Any]:
        """Per-leg totals for the run summary."""
        return {"m2_shift_total_mm": (self._shift_total_m * 1e3).tolist(),
                "m2_clipped_steps": self._clipped_steps.tolist()}


__all__ = ["CLIPPED_STEPS_KEY", "PREVIOUS_PRESSURE_KEY", "SHIFT_TOTAL_KEY", "RodReleaseShift"]
