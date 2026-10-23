"""Integration of the L1-R rod chamber with quasi-static four-leg rigid-body statics.

Dynamics references (``00_docs/01_dynamics/dynamics_model.md`` 5.12.5 V5, 5.12.8 probe S_ii):
the probed / moved leg is moving (head-only ``k_n``), the other three are locked after an
extension (``p_r0`` 2 bar) and follow the one-sided law, knee included. The plant inputs below
(pad positions, static pad loads at the top auger level, ``k_n``, rod weight) are those of the
dynamics reference scripts ``l1r_v5v6.py`` / ``l1r_sii.py`` (rev. 30, drawing dimensions,
stroke 0.70, rear 71.5 kg), dumped 2026-10-22; the oil columns are the hydraulics geometry, with
which ``k_n'`` reproduces the dynamics value exactly.
"""

from __future__ import annotations

import numpy as np
import pytest

from outrigger_sim.hydraulics.rod_chamber import (
    CylinderOilColumns,
    RodChamberLegParams,
    RodChamberOptions,
    RodChamberStateMachine,
)

PAD_XY_M = np.array([[2.2938, 1.3238], [2.2938, -1.3238], [-2.556, 1.1679], [-2.556, -1.2429]])
STATIC_PAD_LOAD_N = np.array(
    [119427.52466906616, 117182.98789421299, 73263.44998373804, 71724.66888361068]
)
PAD_STIFFNESS_N_M = np.array(
    [25905744.167678546, 25905744.167678546, 19504614.904850326, 19504614.904850326]
)
LOCKED_STIFFNESS_N_M = np.array(
    [33929017.01378223, 33929017.01378223, 26402110.9664324, 26402110.9664324]
)
ROD_WEIGHT_N = np.array([1047.1900381788998, 1047.1900381788998, 701.175475, 701.175475])
KNEE_N = np.array([4089.0357108266853, 4089.0357108266853, 3170.129809504481, 3170.129809504481])

# dynamics script results (full precision) and the rounded values of the document
V5_FL_1MM_N = np.array(
    [5960.551418550018, -5960.551418550013, -6546.024529514276, 6546.024529514276]
)
V5_DOC_KN = np.array([5.96, -5.96, -6.55, 6.55])
PROBE_SECANT_N_M = {
    (0, +2e-3): 5827767.305904885,
    (0, -2e-3): 5640814.426981462,
    (2, +2e-3): 6985428.0127220275,
    (2, -2e-3): 6530450.037251096,
}
PROBE_DOC_KN_MM = {(0, +2e-3): 5.828, (0, -2e-3): 5.641, (2, +2e-3): 6.985, (2, -2e-3): 6.531}
SMALL_SIGNAL_DOC_KN_MM = {0: 6.272, 2: 7.245}

GEOMETRY = (
    (0.130, 0.110, 0.4011),
    (0.130, 0.110, 0.4011),
    (0.110, 0.090, 0.3909),
    (0.110, 0.090, 0.3909),
)
MOVING_SPEED_M_S = 1.0e-3


def support_matrix(pad_xy_m: np.ndarray) -> np.ndarray:
    """Pad vertical displacement = A @ [heave, roll, pitch] (dyn_model.support_matrix)."""
    return np.column_stack([np.ones(len(pad_xy_m)), pad_xy_m[:, 1], -pad_xy_m[:, 0]])


def make_machine() -> RodChamberStateMachine:
    legs = []
    for (bore, rod, extension), pad_N_m, weight_N in zip(
        GEOMETRY, PAD_STIFFNESS_N_M, ROD_WEIGHT_N, strict=True
    ):
        columns = CylinderOilColumns(bore, rod, extension, 0.70, 0.05, 0.05, 1.0e9)
        legs.append(RodChamberLegParams.from_pad_stiffness(columns, pad_N_m, weight_N))
    return RodChamberStateMachine(legs, RodChamberOptions())


def lock_all_then_move(moving_leg: int) -> tuple[RodChamberStateMachine, np.ndarray]:
    """All legs locked after an extension at the static loads, then one leg moves."""
    machine = make_machine()
    deflection = STATIC_PAD_LOAD_N / PAD_STIFFNESS_N_M
    common = {
        "step_s": 2e-4,
        "pad_deflection_m": deflection,
        "pad_deflection_rate_m_s": 0.0,
        "motor_position_m": 0.4,
        "cylinder_force_N": STATIC_PAD_LOAD_N - ROD_WEIGHT_N,
    }
    machine.step(time_s=0.0, applied_speed_m_s=0.0, **common)
    speed = np.zeros(4)
    speed[moving_leg] = MOVING_SPEED_M_S
    machine.step(time_s=0.01, applied_speed_m_s=speed, **common)
    return machine, deflection


def solve_load_change(
    machine: RodChamberStateMachine, deflection_lock: np.ndarray, extension_m: np.ndarray
) -> np.ndarray:
    """Rigid-body statics A^T dN = 0 with the module's pad law (Newton, piecewise linear)."""
    support = support_matrix(PAD_XY_M)
    body = np.zeros(3)
    for _ in range(50):
        deflection = deflection_lock + extension_m - support @ body
        normal = np.array(
            [leg.normal_force_at(d) for leg, d in zip(machine.legs, deflection, strict=True)]
        )
        change = normal - STATIC_PAD_LOAD_N
        residual = support.T @ change
        if np.max(np.abs(residual)) < 1e-6:
            return change
        stiffness = np.array(
            [leg.pad_stiffness_at(d) for leg, d in zip(machine.legs, deflection, strict=True)]
        )
        body = body + np.linalg.solve(support.T @ np.diag(stiffness) @ support, residual)
    raise AssertionError("statics did not converge")


def test_parameters_match_the_dynamics_values() -> None:
    machine = make_machine()
    for leg, locked, knee in zip(machine.legs, LOCKED_STIFFNESS_N_M, KNEE_N, strict=True):
        assert leg.params.pad_stiffness_locked_N_m == pytest.approx(locked, rel=1e-12)
        assert leg.params.knee_force_increment_N(2e5) == pytest.approx(knee, rel=1e-12)


def test_v5_front_left_plus_1mm_load_exchange() -> None:
    machine, deflection = lock_all_then_move(moving_leg=0)
    change = solve_load_change(machine, deflection, np.array([1e-3, 0.0, 0.0, 0.0]))
    assert change == pytest.approx(V5_FL_1MM_N, rel=1e-9)
    assert change / 1e3 == pytest.approx(V5_DOC_KN, abs=0.006)
    head_only_kN = np.array([4.98, -4.98, -5.47, 5.47])
    assert change[0] / 1e3 / head_only_kN[0] == pytest.approx(1.20, abs=0.01)  # +20 %


@pytest.mark.parametrize("key", sorted(PROBE_SECANT_N_M))
def test_probe_secant(key: tuple[int, float]) -> None:
    leg, stroke_m = key
    machine, deflection = lock_all_then_move(moving_leg=leg)
    extension = np.zeros(4)
    extension[leg] = stroke_m
    secant = solve_load_change(machine, deflection, extension)[leg] / stroke_m
    assert secant == pytest.approx(PROBE_SECANT_N_M[key], rel=1e-9)
    assert secant / 1e6 == pytest.approx(PROBE_DOC_KN_MM[key], abs=6e-4)


@pytest.mark.parametrize("leg", sorted(SMALL_SIGNAL_DOC_KN_MM))
def test_probe_small_signal(leg: int) -> None:
    machine, deflection = lock_all_then_move(moving_leg=leg)
    stiffness = np.diag(
        [chamber.pad_stiffness_at(d) for chamber, d in zip(machine.legs, deflection, strict=True)]
    )
    support = support_matrix(PAD_XY_M)
    reduced = (
        stiffness
        @ support
        @ np.linalg.solve(support.T @ stiffness @ support, support.T @ stiffness)
    )
    sensitivity = stiffness - reduced
    assert sensitivity[leg, leg] / 1e6 == pytest.approx(SMALL_SIGNAL_DOC_KN_MM[leg], abs=6e-4)
