"""Reference scenarios of the single-leg bench (spec 6.2). Shared by the Python spec implementation
(single_leg.py) and the Hopsan generator (hopsan_single_leg.py): same breakpoints, same parameters.

S1   locked (dual POC), +20 kN downward step on M (2 ms ramp)               -> oil spring, zeta, p rise
S1f  as S1 with seal friction F_s = 5 kN                                     -> friction lock
S2   moving: extend at v_max (ramp 0.1 s), hold 2 s, ramp down, lock         -> flow -> speed, stop
S2r  moving: retract at v_max with the rod line at the POC-A pilot pressure  -> retraction under load
S2b  stall: extend against a (practically) fixed superstructure -> 210 bar relief (V11b)
S3   locked, D2 downward step 125 kN (5 ms ramp) -> peak close to 350 bar (V17, pilot check)
S4   counterbalance option, D2 step 160 kN -> CB relieves at 350 bar, leg pushed in
S4p  same D2 step 160 kN with the pilot check (no CB) -> 350 bar exceeded
S5   locked, F_s = 5 kN, slow load cycle 0 -> +40 -> -40 -> 0 kN -> pressure reading vs true load
"""
from __future__ import annotations

from single_leg import Schedule

BIG = 1.0e3


def make(name: str, c: dict) -> tuple[Schedule, float, dict]:
    """Return (schedule, t_end, options) for scenario `name` with constants c (l2_params.build)."""
    q = c["q_max"]
    opts: dict = {"with_relief": False, "with_cb": False, "F_s": 0.0, "M": None, "F_preload": None,
                  "t_step": None}
    s = Schedule()
    if name in ("S1", "S1f"):
        dF = 20.0e3
        s.D2_N = [(0.0, 0.0), (0.1, 0.0), (0.102, dF), (BIG, dF)]
        t_end = 3.0
        opts["t_step"] = 0.1
        if name == "S1f":
            opts["F_s"] = 5.0e3
    elif name == "S2":
        s.rod_open = [(0.0, 0.0), (0.30, 0.0), (0.31, 1.0), (2.90, 1.0), (2.91, 0.0), (BIG, 0.0)]
        s.moving = [(0.0, 0.0), (0.30, 0.0), (0.300001, 1.0), (2.91, 1.0), (2.910001, 0.0), (BIG, 0.0)]
        s.q_head = [(0.0, 0.0), (0.5, 0.0), (0.6, q), (2.6, q), (2.7, 0.0), (BIG, 0.0)]
        t_end = 4.0
        opts["with_relief"] = True
        opts["t_step"] = 0.5
    elif name == "S2r":
        p_pilot = 36.0e5  # ~ p_A/3.5 + 3 bar for p_A 114 bar (POC-A pilot), ASSUMPTION
        s.rod_open = [(0.0, 0.0), (0.30, 0.0), (0.31, 1.0), (2.90, 1.0), (2.91, 0.0), (BIG, 0.0)]
        s.moving = [(0.0, 0.0), (0.30, 0.0), (0.300001, 1.0), (2.91, 1.0), (2.910001, 0.0), (BIG, 0.0)]
        s.p_rod_line_g = [(0.0, p_pilot), (BIG, p_pilot)]
        s.q_head = [(0.0, 0.0), (0.5, 0.0), (0.6, -q), (2.6, -q), (2.7, 0.0), (BIG, 0.0)]
        t_end = 4.0
        opts["with_relief"] = True
        opts["t_step"] = 0.5
    elif name == "S2b":
        s.rod_open = [(0.0, 0.0), (0.05, 0.0), (0.06, 1.0), (BIG, 1.0)]
        s.moving = [(0.0, 0.0), (0.05, 0.0), (0.050001, 1.0), (BIG, 1.0)]
        s.q_head = [(0.0, 0.0), (0.1, 0.0), (0.2, q), (BIG, q)]
        t_end = 1.0
        opts["with_relief"] = True
        opts["M"] = 1.0e9
        opts["F_preload"] = c["F0"]
        opts["t_step"] = 0.1
    elif name == "S5":
        # quasi-static load cycle on a locked leg with seal friction: pressure reading vs true load
        s.D2_N = [(0.0, 0.0), (0.5, 0.0), (2.5, 40.0e3), (4.5, -40.0e3), (6.5, 0.0), (BIG, 0.0)]
        t_end = 7.5
        opts["F_s"] = 5.0e3
        opts["t_step"] = 0.5
    elif name in ("S3", "S4", "S4p"):
        dF = 125.0e3 if name == "S3" else 160.0e3
        s.D2_N = [(0.0, 0.0), (0.1, 0.0), (0.105, dF), (BIG, dF)]
        t_end = 3.0
        opts["t_step"] = 0.1
        opts["with_cb"] = name == "S4"
    else:
        raise KeyError(name)
    return s, t_end, opts


ALL = ("S1", "S1f", "S2", "S2r", "S2b", "S3", "S4", "S4p", "S5")
