"""Initial-velocity excitation of the settled machine (V7 diagnosis, S2a; later S4).

``00_docs/03_chrono/chrono_build_plan.md`` S2a (``scenarios/impulse``: the name of the plan
skeleton, the content is an **initial velocity**); ``dynamics_model.md`` 5 V7 (rev. 5:
excite from the settled state with an initial velocity, no bushing yield; project on the
modes with ``eta = Phi^T M q``). Engine independent: this module picks the rigid velocity
field and the windows; the engine adds it to every body (``chrono/runs.set_rigid_velocity``).

Reference values (plan rev. 10, option A, user decision 2026-10-20): the ground bushing acts
at the pad ball centre, so the mode shapes, frequencies, zeta and numerical damping come from
``V7_ball_centre_bushing_rev13`` (``dynamics_model.md`` rev. 13, 5.4); the contact-point keys
(``mode_shapes_rev5`` etc.) are history.

Excitation (all three about the mode-shape reference point, the centre of mass of the
superstructure + 4 rods at ``e_op``):

* ``roll``: angular velocity about world x, window 20 s (modes 1 / 2 diagnosis, mode 1);
* ``pitch``: angular velocity about world y, window 20 s (mode 2);
* ``yaw``: angular velocity about world z, window 2 s (diagnosis 5: mode 3, yaw-sway).

The angular speed is ``amplitude * 2 pi f`` with ``f`` the reference damped frequency of the
mode the direction is judged on, i.e. a rotation amplitude of about ``amplitude`` if all the
energy went into that mode. ASSUMPTION (plan: "no bushing yield"): 0.02 deg for roll and
pitch, 0.01 deg for yaw. At 0.02 deg the pad load changes by about 7-14 kN (no lift-off, the
smallest static pad load is 72 kN) and the bushing deformation stays below 1 mm, against a
yield deformation ``mu N / kt`` of about 4 mm; the run checks that no step yields.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.verify.reference import (
    L1_BALL_CENTRE_REV13_F_DAMPED_HZ,
    L1_BALL_CENTRE_REV13_MODE_COORDINATES,
    L1_BALL_CENTRE_REV13_MODE_MASS_MATRIX,
    L1_BALL_CENTRE_REV13_MODE_PHI,
    L1_BALL_CENTRE_REV13_MODE_REFERENCE_POINT_M,
    L1_BALL_CENTRE_REV13_ZETA,
    L1_BALL_CENTRE_REV13_ZETA_NUM_R_OMEGA_DT_HALF,
    References,
    RefKey,
)

EXPECTED_COORDINATES = ("surge x", "sway y", "heave z", "roll", "pitch", "yaw")
ZETA_NUM_BASE_DT_S = 1.0e-4
"""Time step whose ``r omega dt / 2`` entry other time steps are scaled from (linear in dt)."""
DT_MATCH_REL_TOL = 1.0e-9


@dataclass(frozen=True)
class Excitation:
    """One initial-velocity case."""

    name: str
    axis_world: tuple[float, float, float]
    mode_index: int
    """0-based mode the case is judged on (roll -> 0, pitch -> 1, yaw -> 2)."""
    amplitude_deg: float
    window_s: float


EXCITATIONS: dict[str, Excitation] = {
    "roll": Excitation("roll", (1.0, 0.0, 0.0), 0, 0.02, 20.0),
    "pitch": Excitation("pitch", (0.0, 1.0, 0.0), 1, 0.02, 20.0),
    "yaw": Excitation("yaw", (0.0, 0.0, 1.0), 2, 0.01, 2.0),
}


@dataclass(frozen=True)
class ModalReference:
    """Mode shapes and reference modal values of one level (L1, first 6 modes)."""

    phi: NDArray[np.float64]
    """(6 coordinates, 6 modes), mass-normalised (per sqrt(kg))."""
    mass_matrix: NDArray[np.float64]
    reference_point_body_m: NDArray[np.float64]
    f_damped_Hz: NDArray[np.float64]
    zeta: NDArray[np.float64]
    zeta_num_by_dt_s: dict[float, NDArray[np.float64]]
    """``r_i omega_i dt / 2`` per tabulated time step [s] (``zeta_num_r_omega_dt_half``)."""
    keys: dict[str, str]

    def zeta_num_at(self, dt_s: float) -> tuple[NDArray[np.float64], str]:
        """Numerical damping per mode at ``dt_s`` and where it came from.

        The tabulated entry is used when ``dt_s`` is one of its time steps; otherwise the
        :data:`ZETA_NUM_BASE_DT_S` entry is scaled by ``dt_s / ZETA_NUM_BASE_DT_S``
        (``r omega dt / 2`` is linear in dt).

        Returns:
            ``(zeta_num, source)`` with ``source`` naming the entry and any scaling.
        """
        for tabulated_dt_s, zeta_num in self.zeta_num_by_dt_s.items():
            if math.isclose(dt_s, tabulated_dt_s, rel_tol=DT_MATCH_REL_TOL):
                return zeta_num, f"entry {tabulated_dt_s:g} s"
        base = self.zeta_num_by_dt_s[ZETA_NUM_BASE_DT_S]
        scale = dt_s / ZETA_NUM_BASE_DT_S
        return base * scale, f"entry {ZETA_NUM_BASE_DT_S:g} s x {scale:g} (linear in dt)"


def _zeta_num_by_dt_s(table: Mapping[str, Any]) -> dict[float, NDArray[np.float64]]:
    # The keys are decimal texts ("0.0001"); float() of them equals the literal 1.0e-4.
    by_dt_s = {float(dt_text): np.asarray(values, dtype=float) for dt_text, values in table.items()}
    if ZETA_NUM_BASE_DT_S not in by_dt_s:
        raise ValueError(f"zeta_num table has no {ZETA_NUM_BASE_DT_S:g} s entry: {list(table)}")
    return by_dt_s


def modal_reference(refs: References, level: str) -> ModalReference:
    """Read the ball-centre bushing (rev. 13) mode shapes and reference values of ``level``.

    Raises:
        ValueError: The coordinate order is not :data:`EXPECTED_COORDINATES`, or the
            numerical-damping table has no :data:`ZETA_NUM_BASE_DT_S` entry.
    """
    coords = tuple(refs.get(L1_BALL_CENTRE_REV13_MODE_COORDINATES, level=level))
    if coords != EXPECTED_COORDINATES:
        raise ValueError(f"mode-shape coordinates {coords} != {EXPECTED_COORDINATES}")
    keys = {
        name: key.resolve(level=level).notation()
        for name, key in (
            ("phi", L1_BALL_CENTRE_REV13_MODE_PHI),
            ("mass_matrix", L1_BALL_CENTRE_REV13_MODE_MASS_MATRIX),
            ("reference_point", L1_BALL_CENTRE_REV13_MODE_REFERENCE_POINT_M),
            ("f_damped_Hz", L1_BALL_CENTRE_REV13_F_DAMPED_HZ),
            ("zeta", L1_BALL_CENTRE_REV13_ZETA),
            ("zeta_num", L1_BALL_CENTRE_REV13_ZETA_NUM_R_OMEGA_DT_HALF),
        )
    }

    def array(key: RefKey) -> NDArray[np.float64]:
        return np.asarray(refs.get(key, level=level), dtype=float)

    return ModalReference(
        phi=array(L1_BALL_CENTRE_REV13_MODE_PHI),
        mass_matrix=array(L1_BALL_CENTRE_REV13_MODE_MASS_MATRIX),
        reference_point_body_m=array(L1_BALL_CENTRE_REV13_MODE_REFERENCE_POINT_M),
        f_damped_Hz=array(L1_BALL_CENTRE_REV13_F_DAMPED_HZ),
        zeta=array(L1_BALL_CENTRE_REV13_ZETA),
        zeta_num_by_dt_s=_zeta_num_by_dt_s(
            refs.get(L1_BALL_CENTRE_REV13_ZETA_NUM_R_OMEGA_DT_HALF, level=level)
        ),
        keys=keys,
    )


def angular_velocity_world(excitation: Excitation, modal: ModalReference) -> NDArray[np.float64]:
    """``axis * amplitude * 2 pi f_mode`` [rad/s]."""
    f = float(modal.f_damped_Hz[excitation.mode_index])
    speed = math.radians(excitation.amplitude_deg) * 2.0 * math.pi * f
    return np.asarray(excitation.axis_world, dtype=float) * speed
