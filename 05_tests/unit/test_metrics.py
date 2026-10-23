"""verify/metrics (V7 identification) and the S2a V7 diagnosis classes."""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.frames import quat_from_euler_zyx, quat_to_matrix
from outrigger_sim.scenarios.impulse import modal_reference
from outrigger_sim.verify.metrics import (
    fit_damped_sine,
    log_decrement,
    modal_coordinates,
    rigid_displacement,
    rotation_vector,
)
from outrigger_sim.verify.reference import (
    L1_BALL_CENTRE_REV13_V7_DIAGNOSTIC_ZETA_CASES,
    load_references,
)
from outrigger_sim.verify.s2a import V7Thresholds, v7_diagnosis, v7_thresholds, v7_yaw_verdict


@pytest.fixture(scope="module")
def v7_limits() -> V7Thresholds:
    return v7_thresholds(load_references(), "top")


def test_rotation_vector_small_and_large_angles() -> None:
    for angle in (1e-9, 1e-4, 0.3, 2.5):
        axis = np.array([0.3, -0.5, 0.8])
        axis /= np.linalg.norm(axis)
        q = np.concatenate(([math.cos(angle / 2)], math.sin(angle / 2) * axis))
        assert np.allclose(rotation_vector(quat_to_matrix(q)), angle * axis, rtol=1e-9, atol=1e-15)


def test_rigid_displacement_of_a_point() -> None:
    p = np.array([0.4, 0.0, 2.1])
    q0 = np.array([1.0, 0.0, 0.0, 0.0])
    q1 = quat_from_euler_zyx(0.0, 0.0, 1e-4)  # roll 1e-4 rad about the body origin
    d = rigid_displacement([[0.0, 0.0, 0.0]], [q1], (0.0, 0.0, 0.0), q0, p)[0]
    assert np.allclose(d[3:], [1e-4, 0.0, 0.0], atol=1e-15)
    assert np.allclose(d[:3], quat_to_matrix(q1) @ p - p, atol=1e-15)
    assert np.allclose(d[:3], np.cross([1e-4, 0.0, 0.0], p), atol=2e-8)  # first order


def test_modal_projection_recovers_modal_amplitudes() -> None:
    rng = np.random.default_rng(1)
    m = np.diag(rng.uniform(1.0, 5.0, 6))
    a = rng.normal(size=(6, 6))
    # mass-normalised eigenvectors of a random SPD stiffness
    k = a @ a.T + 6 * np.eye(6)
    w, v = np.linalg.eigh(np.linalg.inv(np.sqrt(m)) @ k @ np.linalg.inv(np.sqrt(m)))
    phi = np.linalg.inv(np.sqrt(m)) @ v
    eta_true = rng.normal(size=(10, 6))
    q = eta_true @ phi.T
    assert np.allclose(modal_coordinates(q, phi, m), eta_true, atol=1e-12)


@pytest.mark.parametrize(("f", "zeta"), [(1.7845, 0.00777), (5.8325, 0.0373)])
def test_damped_sine_fit_recovers_frequency_and_damping(f: float, zeta: float) -> None:
    t = np.arange(0.0, 20.0 if f < 3 else 2.0, 1e-3)
    wn = 2 * math.pi * f / math.sqrt(1 - zeta**2)
    wd = 2 * math.pi * f
    y = 0.2 * np.exp(-zeta * wn * t) * np.sin(wd * t + 0.3) + 1e-3
    y += np.random.default_rng(2).normal(scale=1e-5, size=t.size)
    fit = fit_damped_sine(t, y, f * 1.01)
    assert fit.f_damped_Hz == pytest.approx(f, rel=1e-5)
    assert fit.zeta == pytest.approx(zeta, rel=1e-3)
    assert fit.offset == pytest.approx(1e-3, abs=1e-5)
    assert fit.residual_rms_rel < 1e-3
    assert log_decrement(t, y, fit.f_damped_Hz) == pytest.approx(zeta, rel=0.05)


def test_modal_reference_numerical_damping_per_time_step() -> None:
    modal = modal_reference(load_references(), "top")
    nominal, nominal_source = modal.zeta_num_at(1.0e-4)
    double, double_source = modal.zeta_num_at(2.0e-4)
    half, half_source = modal.zeta_num_at(5.0e-5)
    assert "rev13" in modal.keys["zeta_num"] and "rev13" in modal.keys["phi"]
    assert nominal_source == "entry 0.0001 s" and double_source == "entry 0.0002 s"
    assert "x 0.5" in half_source
    assert np.allclose(half, 0.5 * nominal, rtol=1e-12)
    assert np.allclose(double, 2.0 * nominal, rtol=0.01)  # tabulated values are rounded


V7_PREDICTED_CASES = {
    # zeta_cases name of V7_ball_centre_bushing_rev13 / V7_diagnostic (top) -> expected class
    "nominal": "1",
    "c_n x0.0093 (floor body 1 kg)": "2",
    "c_n x2": "3",
    "c_t x2 (bushing input = c_t, R7 violation)": "4",
}


@pytest.fixture(scope="module")
def v7_zeta_cases() -> dict:
    return load_references().get(L1_BALL_CENTRE_REV13_V7_DIAGNOSTIC_ZETA_CASES, level="top")


@pytest.mark.parametrize(("case", "code"), V7_PREDICTED_CASES.items())
def test_v7_diagnosis_classes_of_the_reference_predictions(
    v7_limits: V7Thresholds, v7_zeta_cases: dict, case: str, code: str
) -> None:
    """The predicted zeta1 / zeta2 of each error case (reference, top) fall in its class."""
    z1, z2 = v7_zeta_cases[case][:2]
    d = v7_diagnosis(z1, z2, v7_limits)
    assert d.code == code
    assert d.needs_yaw == (code == "4")


def test_v7_diagnosis_between_the_classes_is_none(v7_limits: V7Thresholds) -> None:
    """zeta1 between the floor-mass limit and the normal band, zeta2 low: no class."""
    low, _ = v7_limits.normal_zeta1_band
    z1 = 0.5 * (v7_limits.gn_error_zeta1_max + low)
    d = v7_diagnosis(z1, 0.5 * v7_limits.normal_zeta2_band[0], v7_limits)
    assert d.code == "none"
    assert d.needs_yaw


def test_v7_thresholds_are_read_from_the_ball_centre_block(v7_limits: V7Thresholds) -> None:
    assert "V7_ball_centre_bushing_rev13 / V7_diagnostic / thresholds" in v7_limits.key
    low, high = v7_limits.normal_zeta1_band
    assert low < high
    assert v7_limits.gn_error_zeta1_max < low
    assert v7_limits.vertical_damping_excess_zeta1_min > high


def test_v7_yaw_verdict_thresholds(v7_limits: V7Thresholds) -> None:
    assert v7_yaw_verdict(0.07417, v7_limits).startswith("c_t doubled")  # c_t x2 prediction
    assert v7_yaw_verdict(0.0002323, v7_limits).startswith("bushing damping missing")
    assert v7_yaw_verdict(v7_limits.nominal_zeta3, v7_limits).startswith("c_t as intended")
