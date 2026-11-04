"""Engine-independent quasi-static flow sharing of the four legs on one fixed pump.

Candidate for the later 03_src module (criteria 9 step 1); it holds no engine or YAML
dependency, numpy only. Given the commanded leg speeds and the load pressures it returns
the leg speeds the shared pump can deliver.

Laws (hydraulic_coupling.md sec. 3):
  section    Q_i = K_i sqrt(y_i), K_i = A_i |u_i| / sqrt(dp_c), hence v_i = u_i sqrt(y_i / dp_c)
  priority   y_i = smin(dp_c, y_open(p_P - p_L,i)): pre-compensator of the drawing
  proportional  y_i = smin(dp_c, p_P - LS): common drop, flow sharing (Q-M5 contrast)
  y_open(D) = D X^2 / (X^2 + K_i^2): compensator fully open in series with the spool
  gallery    sum Q_i(p_P) + Q_byp(p_P) = Q_sup, Q_byp opens at p_P = LS + dp_ls

enabled=False returns the command unchanged. With Q_dem <= Q_sup (1 + 1e-6) and a
sufficient LS margin the result equals the command exactly (criteria V-1, V-2). All
pressures GAUGE [Pa], flows m3/s, speeds m/s, extension positive.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

SUPPLY_REL_TOL = 1.0e-6  # criteria V-1, V-2


@dataclass(frozen=True)
class FlowShareConfig:
    A_h: np.ndarray
    A_r: np.ndarray
    dp_c: float = 10e5
    dp_ls: float = 20e5
    width: float = 1e5  # smoothing width of the compensator transition [Pa]
    law: str = "priority"
    enabled: bool = True
    X_comp: float = 1.667e-3 / math.sqrt(7e6)
    Cs_unl: float = math.sqrt(7e6) / 2.6e-8
    Cf_unl: float = 1.0 / (1.9e-8 * math.sqrt(7e6))
    X_unl: float = 3.0e-3 / math.sqrt(7e6)
    p_T: float = 2e5
    p_relief: float = 210e5


@dataclass
class ShareResult:
    v: np.ndarray
    Q: np.ndarray  # flow from the gallery per leg
    p_P: float
    Q_byp: float
    ls: float
    y: np.ndarray
    limited: np.ndarray  # True where the leg gets less than commanded
    Q_dem: float


def smin(a: np.ndarray | float, b: np.ndarray | float, w: float):
    """C1 soft minimum, exactly min(a, b) when |a - b| >= w; w = 0 is the sharp minimum."""
    m = np.minimum(a, b)
    if w <= 0.0:
        return m
    gap = np.maximum(w - np.abs(a - b), 0.0)
    return m - gap**2 / (4.0 * w)


def load_pressure_ext(F: np.ndarray, p_r: np.ndarray, cfg: FlowShareConfig) -> np.ndarray:
    """Head pressure of an extending leg from the cylinder force and rod pressure."""
    return (F + cfg.A_r * p_r) / cfg.A_h


def _section_y(K: np.ndarray, D: np.ndarray, cfg: FlowShareConfig) -> np.ndarray:
    D_pos = np.maximum(D, 0.0)
    if cfg.law == "proportional":  # flow sharing: the same spool drop on every section
        return np.maximum(smin(cfg.dp_c, D_pos, cfg.width), 0.0)
    y_open = D_pos * cfg.X_comp**2 / (cfg.X_comp**2 + K**2)
    return np.maximum(smin(cfg.dp_c, y_open, cfg.width), 0.0)


def bypass(p_P: float, ls: float, cfg: FlowShareConfig) -> float:
    dp = max(p_P - cfg.p_T, 0.0)
    x_u = (p_P - cfg.dp_ls - ls) / (cfg.Cs_unl + cfg.Cf_unl * dp)
    return min(max(x_u, 0.0), cfg.X_unl) * math.sqrt(dp)


def share(u: np.ndarray, p_load: np.ndarray, Q_sup: float, cfg: FlowShareConfig) -> ShareResult:
    """Leg speeds for commands u [m/s] and load pressures p_load [Pa gauge] (see module doc)."""
    u = np.asarray(u, float)
    area = np.where(u < 0, cfg.A_r, cfg.A_h)
    active = u != 0
    Q_cmd = area * np.abs(u)
    Q_dem = float(Q_cmd.sum())
    ls = min(max(cfg.p_T, float(p_load[active].max()) if active.any() else cfg.p_T), cfg.p_relief)
    K = Q_cmd / math.sqrt(cfg.dp_c)

    if not cfg.enabled:
        return ShareResult(u.copy(), Q_cmd, ls + cfg.dp_ls, 0.0, ls, np.full(4, cfg.dp_c), np.zeros(4, bool), Q_dem)

    # inside the supply tolerance the demand counts as met (criteria V-1)
    supply = max(Q_sup, Q_dem) if Q_dem <= Q_sup * (1.0 + SUPPLY_REL_TOL) else Q_sup

    def flows(p_P: float) -> tuple[np.ndarray, np.ndarray]:
        D = np.full(4, p_P - ls) if cfg.law == "proportional" else p_P - p_load
        y = _section_y(K, D, cfg)
        return K * np.sqrt(y), y

    def excess(p_P: float) -> float:
        return float(flows(p_P)[0].sum()) + bypass(p_P, ls, cfg) - supply

    lo, hi = cfg.p_T, ls + cfg.dp_ls + 1e5
    while excess(hi) < 0.0 and hi < 1e9:
        hi = hi + 50e5
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if excess(mid) > 0.0:
            hi = mid
        else:
            lo = mid
    p_P = 0.5 * (lo + hi)
    Q, y = flows(p_P)
    exact = y >= cfg.dp_c * (1.0 - 1e-12)
    v = np.where(exact, u, u * np.sqrt(y / cfg.dp_c))
    Q = np.where(exact, Q_cmd, Q)
    limited = active & ~exact
    return ShareResult(v, Q, p_P, bypass(p_P, ls, cfg), ls, y, limited, Q_dem)
