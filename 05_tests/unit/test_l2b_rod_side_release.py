"""C-S8-35 / H-S8-4 F1 (``02_hydraulic/s8_seal_friction_counterbalance.md`` 12.3, 12.7): on the
release step of a locked leg the moving rod pressure starts from the locked-law rod pressure of
the last call, not from the lock-instant ``p_r0`` held by the skipped state machine.

(a) lock after an extension (p_r0 2 bar g), unload while locked (rod pressure rises), release:
    first rod pressure = p_prev + (target - p_prev)(1 - exp(-dt / tau)), both directions;
(b) the force output is bit-identical to the pre-fix behaviour (only the reading changes);
(c) lock after a retraction (YAML p_r0) and a release from the floor keep the same continuity.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide
from outrigger_sim.hydraulics.rod_chamber import RodChamberMode
from outrigger_sim.params import load_params

DT = 1.0e-4
LEG = 3  # RR


@pytest.fixture(scope="module")
def p2():
    return load_params(level="middle", model="L2b_NSC")


def _law(p2) -> L2bRodSide:
    return L2bRodSide.from_params(p2, [0, 1, 2, 3], armed=True, mechanics="one_sided_parallel",
                                  oil_only=True)


def _step(law, k, u, s, c, f):
    return law.spring_force_N(k * DT, DT, np.full(4, u), s, np.full(4, c), np.full(4, f))


def _locked_unloaded(p2, *, emulate_old: bool = False):
    """Lock at ~70 kN after an extension, unload to ~0 while locked (lift-off), then the
    release step with ``u`` = -2e-6 m/s (just above eps, the ML88_ep0 case)."""
    law = _law(p2)
    s = np.full(4, 0.5666)
    k2 = law.k2_N_m(LEG, s[LEG])
    c0 = 70e3 / k2
    _step(law, 1, 0.0, s, c0, 70e3)  # lock (fresh machine: after an extension)
    forces, p_r = [], []
    for k, c in enumerate(np.linspace(c0, -1.2e-3, 200), start=2):
        forces.append(_step(law, k, 0.0, s, c, 0.0))
        p_r.append(law.rod_pressure_Pa[LEG])
    assert law.locked[LEG]
    p_prev = float(law.rod_pressure_Pa[LEG])
    leg = law._legs[LEG]
    if emulate_old:  # pre-fix: the release started from the machine's stale tracked value
        law._last_p_r[LEG] = leg.tracked_rod_pressure_Pa
    f_cyl = -800.0
    forces.append(_step(law, 300, -2e-6, s, -1.2e-3, f_cyl))
    return law, p_prev, np.array(forces), np.array(p_r), f_cyl


def test_release_after_unloading_is_continuous(p2) -> None:
    law, p_prev, _, p_r, f_cyl = _locked_unloaded(p2)
    leg = law._legs[LEG]
    assert p_r[0] < 5e5 < 100e5 < p_prev  # extension lock 2 bar g, unloading raised it
    assert not law.locked[LEG]
    target = leg.params.moving_target_rod_pressure_Pa(RodChamberMode.RET, f_cyl)
    keep = math.exp(-DT / law._tau)
    expect = target + (p_prev - target) * keep
    assert law.rod_pressure_Pa[LEG] == pytest.approx(expect, rel=1e-9)
    assert law.rod_pressure_Pa[LEG] > 0.9 * p_prev  # not the lock-instant 2 bar g


def test_release_extend_direction_is_continuous(p2) -> None:
    law = _law(p2)
    s = np.full(4, 0.5)
    c0 = 50e3 / law.k2_N_m(LEG, s[LEG])
    _step(law, 1, 0.0, s, c0, 50e3)
    _step(law, 2, 0.0, s, -5e-4, 0.0)
    p_prev = float(law.rod_pressure_Pa[LEG])
    _step(law, 3, +3e-6, s, -5e-4, -500.0)
    leg = law._legs[LEG]
    target = leg.params.moving_target_rod_pressure_Pa(RodChamberMode.EXT, -500.0)
    expect = target + (p_prev - target) * math.exp(-DT / law._tau)
    assert law.rod_pressure_Pa[LEG] == pytest.approx(expect, rel=1e-9)


def test_force_output_bit_identical_to_the_pre_fix_path(p2) -> None:
    new = _locked_unloaded(p2)
    old = _locked_unloaded(p2, emulate_old=True)
    assert np.array_equal(new[2], old[2])  # every force output, incl. the release step
    assert abs(new[0].rod_pressure_Pa[LEG] - old[0].rod_pressure_Pa[LEG]) > 50e5  # reading only


def test_lock_after_retract_and_floor_release_are_continuous(p2) -> None:
    law = _law(p2)
    s = np.full(4, 0.45)
    c = 30e3 / law.k2_N_m(LEG, s[LEG])
    for k in range(1, 4):  # moving in retraction
        _step(law, k, -1e-3, s, c, 30e3)
    _step(law, 4, 0.0, s, c, 30e3)  # lock after a retraction: p_r0 from the YAML
    assert law.locked[LEG]
    p_r0 = float(law.rod_pressure_Pa[LEG])
    assert p_r0 == pytest.approx(p2.l2b.rod_side.p_r0_after_retract_Pa[LEG], rel=1e-12)
    knee_c = law.knee_force_N(LEG) / law.k1_lock(LEG)
    _step(law, 5, 0.0, s, c + 3.0 * knee_c, 60e3)  # load beyond the knee: rod side at the floor
    p_floor = float(law.rod_pressure_Pa[LEG])
    assert p_floor == pytest.approx(law.p_floor_gauge_Pa, abs=1e-6)
    _step(law, 6, +2e-6, s, c + 3.0 * knee_c, 60e3)  # release (extend)
    leg = law._legs[LEG]
    target = leg.params.moving_target_rod_pressure_Pa(RodChamberMode.EXT, 60e3)
    expect = target + (p_floor - target) * math.exp(-DT / law._tau)
    assert law.rod_pressure_Pa[LEG] == pytest.approx(expect, rel=1e-9, abs=1e-6)
