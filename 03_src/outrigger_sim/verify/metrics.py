"""Modal identification helpers (V7; shared with S4): modal projection and damped-sine fit.

``00_docs/03_chrono/chrono_build_plan.md`` S2a (``verify/metrics``); ``dynamics_model.md`` 5 V7:
the body motion is turned into the 6-DoF displacement ``q`` of the mode-shape reference
point (``reference.json / ... / mode_shapes_rev5``: translations of the point, small
rotations about it, body axes = world axes for the level body), and the modal coordinates are
``eta = Phi^T M q`` (``Phi`` mass-normalised, so ``Phi^T M Phi = I``). Each modal coordinate
is fitted with one exponentially decaying cosine plus an offset; the logarithmic decrement
of the peaks is a cross-check. Engine independent (numpy / scipy only).

S4 (plan S4 "6채널 ERA/SSI", risk #14): :func:`era_free_decay` is the multi-output
Eigensystem Realization Algorithm (Juang & Pappa 1985) applied to one free decay of all six
channels of ``q`` (the free response ``y_k = C A^k x_0`` takes the place of the Markov
parameters). It needs no mode shapes, so it also identifies runs whose stiffness differs from
the one ``Phi`` was computed with (beta sensitivity). :func:`select_era_mode` picks, for a
reference mode, the ERA mode that contributes most to its modal coordinate;
:func:`mass_mac` is the mass-weighted modal assurance criterion and
:func:`projection_leakage` measures how much of a modal coordinate comes from other modes
(the projection residual of risk #14).

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


@dataclass(frozen=True)
class DampedComponent:
    """One component of :func:`fit_damped_sum`."""

    f_damped_Hz: float
    zeta: float
    amplitude: float
    phase_rad: float
    sigma_1_s: float


@dataclass(frozen=True)
class DampedSumFit:
    """Result of :func:`fit_damped_sum` (components in the order of the guesses)."""

    components: tuple[DampedComponent, ...]
    offset: float
    residual_rms_rel: float
    n_samples: int
    window_s: tuple[float, float]
    success: bool


def fit_damped_sum(
    t: ArrayLike,
    y: ArrayLike,
    f_guess_Hz: Sequence[float],
    zeta_guess: Sequence[float],
) -> DampedSumFit:
    """Least-squares fit of a sum of decaying cosines + offset (S3 V8(a)).

    Used when a modal coordinate carries leakage from close modes that do not decay (zero
    physical damping): one component per guess, all frequencies and decay rates free. The
    amplitudes enter linearly and are solved for inside the residual (variable projection),
    so only ``2 n`` nonlinear parameters remain.
    """
    tt = np.asarray(t, dtype=float)
    yy = np.asarray(y, dtype=float)
    t_rel = tt - tt[0]
    n = len(f_guess_Hz)
    w0 = 2.0 * math.pi * np.asarray(f_guess_Hz, dtype=float)
    s0 = np.asarray(zeta_guess, dtype=float) * w0

    def basis(p: NDArray[np.float64]) -> NDArray[np.float64]:
        sig, wd = p[:n], p[n:]
        cols = [np.ones_like(t_rel)]
        for k in range(n):
            env = np.exp(-sig[k] * t_rel)
            cols.append(env * np.cos(wd[k] * t_rel))
            cols.append(env * np.sin(wd[k] * t_rel))
        return np.column_stack(cols)

    scale = float(np.std(yy)) or 1.0

    def solve(p: NDArray[np.float64]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        a = basis(p)
        coef, *_ = np.linalg.lstsq(a, yy, rcond=None)
        return coef, a @ coef - yy

    def residual(p: NDArray[np.float64]) -> NDArray[np.float64]:
        return solve(p)[1] / scale

    p0 = np.concatenate([s0, w0])
    sol = least_squares(residual, p0, method="lm", x_scale="jac", max_nfev=2000)
    coef, res = solve(sol.x)
    comps = []
    for k in range(n):
        sig, wd = float(sol.x[k]), abs(float(sol.x[n + k]))
        a_c, a_s = float(coef[1 + 2 * k]), float(coef[2 + 2 * k])
        wn = math.hypot(sig, wd)
        comps.append(
            DampedComponent(
                f_damped_Hz=wd / (2.0 * math.pi),
                zeta=sig / wn if wn > 0.0 else math.nan,
                amplitude=math.hypot(a_c, a_s),
                phase_rad=math.atan2(-a_s, a_c),
                sigma_1_s=sig,
            )
        )
    denom = float(np.sqrt(np.mean((yy - coef[0]) ** 2))) or 1.0
    return DampedSumFit(
        components=tuple(comps),
        offset=float(coef[0]),
        residual_rms_rel=float(np.sqrt(np.mean(res**2))) / denom,
        n_samples=len(tt),
        window_s=(float(tt[0]), float(tt[-1])),
        success=bool(sol.success),
    )


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


# --- S4: multi-output ERA ---------------------------------------------------------------------

ERA_DEFAULT_BLOCK_ROWS = 40
"""Block rows of the Hankel matrix (``r p`` rows for ``p`` channels)."""
ERA_MIN_OSCILLATORY_HZ = 0.05
"""Poles with a smaller damped frequency are treated as non-oscillatory (drift, offset)."""


@dataclass(frozen=True)
class EraMode:
    """One complex-conjugate pole pair of :func:`era_free_decay`.

    The contribution of the pair to channel ``j`` is ``2 Re(shape[j] exp(lambda t))`` with
    ``t`` from the first sample of the identification window.
    """

    f_undamped_Hz: float
    """``|lambda| / 2 pi``."""
    f_damped_Hz: float
    """``Im(lambda) / 2 pi``."""
    zeta: float
    """``-Re(lambda) / |lambda|``."""
    eigenvalue: complex
    """Continuous-time pole ``lambda`` [1/s] (positive imaginary part)."""
    shape: NDArray[np.complex128]
    """Complex output amplitude per channel at the window start (output units)."""
    rms_per_channel: NDArray[np.float64]
    """RMS of the pair contribution per channel over the window."""


@dataclass(frozen=True)
class EraResult:
    """Output of :func:`era_free_decay`."""

    modes: tuple[EraMode, ...]
    """Oscillatory pole pairs, sorted by :attr:`EraMode.f_undamped_Hz`."""
    real_poles: tuple[complex, ...]
    """Remaining poles (real or below :data:`ERA_MIN_OSCILLATORY_HZ`), continuous time."""
    order: int
    singular_values: NDArray[np.float64]
    """Leading singular values of the Hankel matrix (``2 order`` of them at most)."""
    dt_s: float
    """Sample period after decimation."""
    n_block_rows: int
    n_samples: int
    residual_rms_rel: float
    """RMS of (reconstruction - data) / RMS of the data, all channels together."""
    window_s: tuple[float, float]


def era_free_decay(
    t: ArrayLike,
    y: ArrayLike,
    *,
    order: int,
    n_block_rows: int = ERA_DEFAULT_BLOCK_ROWS,
    decimate: int = 1,
    channel_scale: ArrayLike | None = None,
) -> EraResult:
    """Multi-output ERA on one free decay ``y`` (n samples, p channels).

    Args:
        t: Sample times, equally spaced [s].
        y: Free response (n, p) about the equilibrium (no mean removal: a decaying response
            has a non-zero window mean).
        order: Model order (number of states, 2 per oscillatory mode); extra states take up
            drift and noise and are returned as weak or real poles.
        n_block_rows: Block rows ``r`` of the Hankel matrix; ``r p >= order`` is required.
        decimate: Keep every ``decimate``-th sample (the caller keeps the Nyquist frequency
            well above the modes of interest).
        channel_scale: Optional per-channel weight applied before the SVD and removed from
            the shapes afterwards (balances mixed units, e.g. m and rad).

    Raises:
        ValueError: Unequal sampling, too few samples or ``r p < order``.
    """
    tt = np.asarray(t, dtype=float)[::decimate]
    yy = np.asarray(y, dtype=float)
    if yy.ndim == 1:
        yy = yy[:, None]
    yy = yy[::decimate]
    n, p = yy.shape
    if len(tt) != n:
        raise ValueError(f"t has {len(tt)} samples, y has {n}")
    steps = np.diff(tt)
    dt = float(np.median(steps))
    if np.max(np.abs(steps - dt)) > 1e-6 * dt:
        raise ValueError("ERA needs equally spaced samples")
    r = int(n_block_rows)
    if r * p < order:
        raise ValueError(f"block rows x channels {r * p} < order {order}")
    s = n - r - 1
    if s < order:
        raise ValueError(f"{n} samples are too few for {r} block rows and order {order}")
    w = np.ones(p) if channel_scale is None else np.asarray(channel_scale, dtype=float)
    yw = yy * w
    h0 = np.vstack([yw[i : i + s].T for i in range(r)])
    h1 = np.vstack([yw[i + 1 : i + 1 + s].T for i in range(r)])
    u, sv, vt = np.linalg.svd(h0, full_matrices=False)
    sq = np.sqrt(sv[:order])
    a = (u[:, :order].T @ h1 @ vt[:order].T) / np.outer(sq, sq)
    c = u[:p, :order] * sq
    x0 = sq * vt[:order, 0]
    z, psi = np.linalg.eig(a)
    b = np.linalg.solve(psi, x0.astype(complex))
    lam = np.log(z.astype(complex)) / dt
    cm = (c @ psi) / w[:, None]  # back to the output units
    k_idx = np.arange(n)
    recon = np.zeros((n, p))
    modes: list[EraMode] = []
    real_poles: list[complex] = []
    for k in range(order):
        series = np.outer(z[k] ** k_idx, cm[:, k] * b[k])
        recon += series.real
        lk = complex(lam[k])
        f_d = lk.imag / (2.0 * math.pi)
        if f_d >= ERA_MIN_OSCILLATORY_HZ:
            wn = abs(lk)
            modes.append(
                EraMode(
                    f_undamped_Hz=wn / (2.0 * math.pi),
                    f_damped_Hz=f_d,
                    zeta=-lk.real / wn,
                    eigenvalue=lk,
                    shape=cm[:, k] * b[k],
                    rms_per_channel=np.sqrt(np.mean((2.0 * series.real) ** 2, axis=0)),
                )
            )
        elif f_d > -ERA_MIN_OSCILLATORY_HZ:
            real_poles.append(lk)
    modes.sort(key=lambda m: m.f_undamped_Hz)
    denom = float(np.sqrt(np.mean(yy**2))) or 1.0
    return EraResult(
        modes=tuple(modes),
        real_poles=tuple(real_poles),
        order=order,
        singular_values=sv[: min(len(sv), 2 * order)].copy(),
        dt_s=dt,
        n_block_rows=r,
        n_samples=n,
        residual_rms_rel=float(np.sqrt(np.mean((recon - yy) ** 2))) / denom,
        window_s=(float(tt[0]), float(tt[-1])),
    )


def mass_mac(shape: ArrayLike, phi_column: ArrayLike, mass_matrix: ArrayLike) -> float:
    """Mass-weighted MAC ``|phi^T M psi|^2 / ((phi^T M phi)(psi^H M psi))`` (0 ... 1)."""
    psi = np.asarray(shape, dtype=complex)
    phi = np.asarray(phi_column, dtype=float)
    m = np.asarray(mass_matrix, dtype=float)
    num = abs(phi @ m @ psi) ** 2
    den = float(phi @ m @ phi) * float(np.real(np.conj(psi) @ m @ psi))
    return float(num / den) if den > 0.0 else math.nan


def modal_amplitudes(era: EraResult, phi: ArrayLike, mass_matrix: ArrayLike) -> NDArray[np.float64]:
    """``|2 Phi^T M shape_k|`` per (reference mode i, ERA mode k): the start amplitude that ERA
    mode ``k`` puts into the modal coordinate ``eta_i`` (shape (n_ref_modes, n_era_modes))."""
    pm = np.asarray(phi, dtype=float).T @ np.asarray(mass_matrix, dtype=float)
    if not era.modes:
        return np.zeros((pm.shape[0], 0))
    shapes = np.column_stack([m.shape for m in era.modes])
    return 2.0 * np.abs(pm @ shapes)


def select_era_mode(
    era: EraResult,
    mode_index: int,
    phi: ArrayLike,
    mass_matrix: ArrayLike,
    f_ref_Hz: float,
    *,
    f_band_rel: float = 0.15,
    exclusive: bool = True,
) -> int | None:
    """Index into ``era.modes`` of the mode that contributes most to ``eta_{mode_index}``
    among the modes within ``f_ref_Hz (1 +- f_band_rel)``; None if there is none.

    With ``exclusive`` only ERA modes whose largest modal coordinate is ``eta_{mode_index}``
    qualify, so that a close, strongly excited neighbour leaking into ``eta_{mode_index}``
    (non-proportional damping) is not taken for it.
    """
    amps = modal_amplitudes(era, phi, mass_matrix)
    home = np.argmax(amps, axis=0) if amps.size else np.zeros(0, dtype=int)
    best, best_amp = None, -1.0
    for k, m in enumerate(era.modes):
        if abs(m.f_undamped_Hz - f_ref_Hz) > f_band_rel * f_ref_Hz:
            continue
        if exclusive and home[k] != mode_index:
            continue
        if amps[mode_index, k] > best_amp:
            best, best_amp = k, float(amps[mode_index, k])
    return best


def projection_leakage(
    era: EraResult, mode_index: int, era_index: int, phi: ArrayLike, mass_matrix: ArrayLike
) -> float:
    """RMS over the window of the other ERA modes' part of ``eta_{mode_index}`` divided by the
    RMS of the selected mode's part (0 = the modal coordinate holds one mode only)."""
    pm = (np.asarray(phi, dtype=float).T @ np.asarray(mass_matrix, dtype=float))[mode_index]
    j = np.arange(era.n_samples)
    own = np.zeros(era.n_samples)
    other = np.zeros(era.n_samples)
    for k, m in enumerate(era.modes):
        part = 2.0 * np.real((pm @ m.shape) * np.exp(m.eigenvalue * era.dt_s * j))
        if k == era_index:
            own += part
        else:
            other += part
    rms_own = float(np.sqrt(np.mean(own**2)))
    return float(np.sqrt(np.mean(other**2))) / rms_own if rms_own > 0.0 else math.inf
