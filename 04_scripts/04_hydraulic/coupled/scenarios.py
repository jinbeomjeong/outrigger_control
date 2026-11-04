"""Comparison scenarios of the coupled flow-saturation model (hydraulic_coupling.md sec. 5).

Suffix p = prescribed constant leg loads (circuit only, no mechanical coupling).
Suffix c = rigid-body coupling (heave, roll, pitch + leg stiffness).
Suffix 90 / 85 = eta_v 0.90 / 0.85. Command u is the signed leg speed / v_max, ramped
0 -> v_max in command_ramp_s. Load grid and eta_v grid: criteria 6 V-3, 8.2.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from params import LEGS, Params, static_loads


@dataclass(frozen=True)
class Scenario:
    name: str
    desc: str
    eta_v: float
    u: tuple[float, float, float, float]
    coupled: bool
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    head_override: tuple[tuple[str, float], ...] = ()  # (leg, head pressure GAUGE Pa)
    force_override: tuple[tuple[str, float], ...] = ()  # (leg, cylinder force N)
    t_end: float = 5.0
    window: float = 1.0  # steady window = last seconds
    t_start: float = 0.0
    hopsan: bool = True  # False: outside the Hopsan circuit (retract branch)

    def loads(self, p: Params) -> np.ndarray:
        F = static_loads(p, self.roll_deg, self.pitch_deg)
        for leg, ph in self.head_override:
            i = LEGS.index(leg)
            F[i] = ph * p.A_h[i] - p.p_T * p.A_r[i]
        for leg, force in self.force_override:
            F[LEGS.index(leg)] = force
        return F

    def s_start(self, p: Params) -> np.ndarray:
        return p.s0

    def load_fn(self, p: Params):
        F = self.loads(p)
        return lambda t: F

    def command_fn(self, p: Params):
        u_cmd = np.array(self.u)
        t_ramp = np.where(u_cmd != 0, p.ramp * np.maximum(np.abs(u_cmd), 1e-9), 1.0)
        return lambda t: u_cmd * np.minimum(t / t_ramp, 1.0)


ALL_UP = (1.0, 1.0, 1.0, 1.0)


def _pair(tag, desc, eta, u, **kw):
    return [Scenario(tag + "p", desc + ", prescribed loads", eta, u, False, **kw),
            Scenario(tag + "c", desc + ", rigid body", eta, u, True, **kw)]


def _grid(tag, desc, **kw):
    out = []
    for eta, suffix in ((0.90, "90"), (0.85, "85")):
        out += _pair(f"{tag}{suffix}", f"eta {eta:.2f}, {desc}", eta, ALL_UP, **kw)
    return out


# legs in the air during TOUCH: record F_cyl = -m_rod g; seal friction resists extension
_AIR0 = (("FL", -1047.2), ("FR", -1047.2), ("RL", -717.5), ("RR", -717.5))
_AIR4 = (("FL", 4000.0 - 1047.2), ("FR", 4000.0 - 1047.2), ("RL", 3333.2 - 717.5), ("RR", 3333.2 - 717.5))

SCENARIOS: list[Scenario] = [
    *_pair("A1", "eta 0.95, four legs at v_max (zero margin)", 0.95, ALL_UP),
    *_pair("A2", "eta 0.95, four legs at 0.95 v_max (no saturation)", 0.95, (0.95,) * 4),
    *_grid("B", "flat, four legs at v_max"),
    *_grid("C1", "roll +4.4 deg (right side loaded)", roll_deg=4.4),
    *_grid("C2", "pitch -3.2 deg (rear loaded)", pitch_deg=-3.2),
    *_grid("C3", "roll +2.2 deg, pitch +1.6 deg (diagonal)", roll_deg=2.2, pitch_deg=1.6),
    Scenario("D1p", "eta 0.95, FL locked, other three at v_max, prescribed loads", 0.95, (0.0, 1.0, 1.0, 1.0), False),
    # locked legs add little damping to the 8 Hz mode: longer run, window of several seconds
    *_pair("D2", "eta 0.95, front pair locked, rear pair at v_max", 0.95, (0.0, 0.0, 1.0, 1.0), t_end=15.0, window=3.0),
    *_pair("D3", "eta 0.95, rear pair locked, front pair at v_max", 0.95, (1.0, 1.0, 0.0, 0.0), t_end=15.0, window=3.0),
    Scenario("D485p", "eta 0.85, FR locked, other three at v_max, prescribed loads", 0.85, (1.0, 0.0, 1.0, 1.0), False),
    Scenario("E1p", "eta 0.95, 0.95 v_max, FL head 215 bar g: LS relief clamps", 0.95, (0.95,) * 4, False,
             head_override=(("FL", 215e5),)),
    Scenario("T090p", "eta 0.90, legs in the air (TOUCH), no seal friction, prescribed loads", 0.90, ALL_UP, False,
             force_override=_AIR0),
    Scenario("T085p", "eta 0.85, legs in the air (TOUCH), no seal friction, prescribed loads", 0.85, ALL_UP, False,
             force_override=_AIR0),
    Scenario("T190p", "eta 0.90, legs in the air (TOUCH), F_s 4 / 3.33 kN, prescribed loads", 0.90, ALL_UP, False,
             force_override=_AIR4),
    Scenario("T185p", "eta 0.85, legs in the air (TOUCH), F_s 4 / 3.33 kN, prescribed loads", 0.85, ALL_UP, False,
             force_override=_AIR4),
    Scenario("R1p", "eta 0.90, front pair retract at v_max, rear pair extend at v_max, prescribed loads",
             0.90, (-1.0, -1.0, 1.0, 1.0), False, hopsan=False),
]
BY_NAME = {s.name: s for s in SCENARIOS}
