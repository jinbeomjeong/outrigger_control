"""Modal identification helpers (V7; shared with S4): modal projection and damped-sine fit.

``00_docs/03_chrono/chrono_build_plan.md`` S2a (``verify/metrics``); ``dynamics_model.md`` 5 V7:
the body motion is turned into the 6-DoF displacement ``q`` of the mode-shape reference
point (``reference.json / ... / mode_shapes_rev5``: translations of the point, small
rotations about it, body axes = world axes for the level body), and the modal coordinates are
``eta = Phi^T M q`` (``Phi`` mass-normalised, so ``Phi^T M Phi = I``). Each modal coordinate
is fitted with one exponentially decaying cosine plus an offset; the logarithmic decrement
of the peaks is a cross-check. Engine independent (numpy / scipy only).

Units: SI; rotations in rad; frequencies in Hz.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import least_squares
from scipy.signal import find_peaks

from outrigger_sim.frames import quat_to_matrix


def rotation_vector(rotation: ArrayLike) -> NDArray[np.float64]:
    """Rotation vector (axis * angle, rad) of one or more 3x3 rotation matrices (log map)."""
    r = np.asarray(rotation, dtype=float)
    single = r.ndim == 2
    r = r.reshape(-1, 3, 3)
    trace = np.trace(r, axis1=1, axis2=2)
    cos_a = np.clip(0.5 * (trace - 1.0), -1.0, 1.0)
    angle = np.arccos(cos_a)
    skew = np.stack(
        (r[:, 2, 1] - r[:, 1, 2], r[:, 0, 2] - r[:, 2, 0], r[:, 1, 0] - r[:, 0, 1]), axis=1
    )
    sin_a = np.sin(angle)
    # angle / (2 sin angle) -> 1/2 for small angles (series to second order)
    factor = np.where(
        angle > 1e-6, angle / np.where(sin_a == 0.0, 1.0, 2.0 * sin_a), 0.5 + angle**2 / 12.0
    )
    out = skew * factor[:, None]
    return out[0] if single else out


def rigid_displacement(
    origin_m: ArrayLike,
    quat_wxyz: ArrayLike,
    origin0_m: Sequence[float],
    quat0_wxyz: Sequence[float],
    point_body_m: Sequence[float],
) -> NDArray[np.float64]:
    """6-DoF displacement ``q = [u (m), theta (rad)]`` of a body point from a reference pose.

    ``u`` = world displacement of the point, ``theta`` = rotation vector of ``R R0^T`` (world
    axes). Shapes: ``origin_m`` (n, 3), ``quat_wxyz`` (n, 4); returns (n, 6).
    """
    o = np.asarray(origin_m, dtype=float).reshape(-1, 3)
    q = np.asarray(quat_wxyz, dtype=float).reshape(-1, 4)
    p = np.asarray(point_body_m, dtype=float)
    r0 = quat_to_matrix(np.asarray(quat0_wxyz, dtype=float))
    rot = quat_to_matrix(q)
    point = o + np.einsum("nij,j->ni", rot, p)
    point0 = np.asarray(origin0_m, dtype=float) + r0 @ p
    theta = rotation_vector(np.einsum("nij,kj->nik", rot, r0))
    return np.hstack((point - point0, theta))


def modal_coordinates(q: ArrayLike, phi: ArrayLike, mass_matrix: ArrayLike) -> NDArray[np.float64]:
    """``eta = Phi^T M q`` for every row of ``q`` (n, 6) -> (n, n_modes)."""
    return np.asarray(q, dtype=float) @ (
        np.asarray(mass_matrix, dtype=float) @ np.asarray(phi, dtype=float)
    )


@dataclass(frozen=True)
class DampedFit:
    """One-mode fit ``y = A exp(-sigma t) cos(omega_d t + phase) + offset`` (t from 0)."""

    f_damped_Hz: float
    zeta: float
    f_undamped_Hz: float
    amplitude: float
    phase_rad: float
    offset: float
    sigma_1_s: float
    residual_rms_rel: float
    """RMS of the fit residual / RMS of the signal minus offset."""
    n_samples: int
    window_s: tuple[float, float]
    n_cycles: float
    success: bool


def _initial_guess(t: NDArray[np.float64], y: NDArray[np.float64], f_guess: float) -> list[float]:
    dt = float(np.median(np.diff(t)))
    yc = y - y.mean()
    spectrum = np.abs(np.fft.rfft(yc * np.hanning(len(yc)), n=8 * len(yc)))
    freqs = np.fft.rfftfreq(8 * len(yc), dt)
    band = (freqs > 0.5 * f_guess) & (freqs < 1.5 * f_guess)
    f0 = float(freqs[band][np.argmax(spectrum[band])]) if np.any(band) else f_guess
    decay = _log_decrement_sigma(t, yc)
    sigma0 = decay if decay is not None and decay > 0.0 else 2.0 * math.pi * f0 * 0.01
    amp0 = float(np.max(np.abs(yc[: max(3, int(1.0 / (f0 * dt)))])))
    return [amp0, sigma0, 2.0 * math.pi * f0, 0.0, float(y.mean())]


def _log_decrement_sigma(t: NDArray[np.float64], yc: NDArray[np.float64]) -> float | None:
    peaks, _ = find_peaks(np.abs(yc))
    if len(peaks) < 4:
        return None
    a = np.abs(yc[peaks])
    good = a > 0.0
    if good.sum() < 4:
        return None
    slope = np.polyfit(t[peaks][good], np.log(a[good]), 1)[0]
    return float(-slope)


def log_decrement(t: ArrayLike, y: ArrayLike, f_damped_Hz: float) -> float | None:
    """Cross-check zeta from the peak envelope (``|y - mean|`` peaks, log-linear fit)."""
    tt = np.asarray(t, dtype=float)
    yy = np.asarray(y, dtype=float)
    sigma = _log_decrement_sigma(tt, yy - yy.mean())
    if sigma is None:
        return None
    wd = 2.0 * math.pi * f_damped_Hz
    return float(sigma / math.hypot(sigma, wd))


def fit_damped_sine(t: ArrayLike, y: ArrayLike, f_guess_Hz: float) -> DampedFit:
    """Least-squares fit of one decaying cosine + offset to ``y(t)``.

    The phase is fitted through a cosine / sine pair, so the start phase does not matter.
    """
    tt = np.asarray(t, dtype=float)
    yy = np.asarray(y, dtype=float)
    t_rel = tt - tt[0]
    a0, s0, w0, _, c0 = _initial_guess(t_rel, yy, f_guess_Hz)
    scale = float(np.std(yy)) or 1.0

    def model(p: NDArray[np.float64]) -> NDArray[np.float64]:
        a_c, a_s, sigma, wd, c = p
        env = np.exp(-sigma * t_rel)
        return env * (a_c * np.cos(wd * t_rel) + a_s * np.sin(wd * t_rel)) + c

    def residual(p: NDArray[np.float64]) -> NDArray[np.float64]:
        return (model(p) - yy) / scale

    best = None
    for phase in (0.0, 0.5 * math.pi, math.pi, 1.5 * math.pi):
        p0 = np.array([a0 * math.cos(phase), -a0 * math.sin(phase), s0, w0, c0])
        sol = least_squares(residual, p0, method="lm", x_scale="jac", max_nfev=20000)
        if best is None or sol.cost < best.cost:
            best = sol
    assert best is not None
    a_c, a_s, sigma, wd, c = best.x
    wd = abs(wd)
    wn = math.hypot(sigma, wd)
    amp = math.hypot(a_c, a_s)
    res = model(best.x) - yy
    denom = float(np.sqrt(np.mean((yy - c) ** 2))) or 1.0
    return DampedFit(
        f_damped_Hz=wd / (2.0 * math.pi),
        zeta=sigma / wn if wn > 0.0 else math.nan,
        f_undamped_Hz=wn / (2.0 * math.pi),
        amplitude=amp,
        phase_rad=math.atan2(-a_s, a_c),
        offset=c,
        sigma_1_s=sigma,
        residual_rms_rel=float(np.sqrt(np.mean(res**2))) / denom,
        n_samples=len(tt),
        window_s=(float(tt[0]), float(tt[-1])),
        n_cycles=float((tt[-1] - tt[0]) * wd / (2.0 * math.pi)),
        success=bool(best.success),
    )
