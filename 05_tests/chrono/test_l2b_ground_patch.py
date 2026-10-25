"""S8 C-S8-3: L2b ground patch (chrono/l2b_ground_patch): the patch carries the pad like the
floor plate, a scheduled settlement unloads the leg, the snapshot carries the schedule."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("pychrono")

from outrigger_sim.chrono.l2b_ground_patch import attach_ground_patches  # noqa: E402
from outrigger_sim.chrono.l2b_model import L2bModel  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

pytestmark = pytest.mark.chrono


@pytest.fixture(scope="module")
def p2():
    return load_params(level="top", model="L2b_NSC")


def _mean_contact(m, steps):
    out = []
    for _ in range(steps):
        m.step()
        out.append([leg.GetContactForce().z for leg in m.legs])
    return np.mean(out, axis=0)


def test_patch_carries_the_pad_like_the_floor(p2) -> None:
    """0.1 s window means after 0.2 s: RR on its patch = RR on the plate within 1 % W/4."""
    ref = L2bModel(p2)
    pat = L2bModel(p2)
    attach_ground_patches(pat, ("RR",))
    n = round(0.2 / ref.dt_s)
    for _ in range(n):
        ref.step()
        pat.step()
    w = round(0.1 / ref.dt_s)
    a, b = _mean_contact(ref, w), _mean_contact(pat, w)
    w4 = p2.superstructure.mass_properties.mass_kg * p2.meta.gravity_m_s2 / 4.0
    assert np.abs(a - b).max() < 0.01 * w4


def test_settlement_unloads_the_leg_and_snapshot_keeps_it(p2) -> None:
    m = L2bModel(p2)
    patches = attach_ground_patches(m, ("RR",))
    for _ in range(round(0.2 / m.dt_s)):
        m.step()
    before = _mean_contact(m, round(0.05 / m.dt_s))
    t = float(m.system.GetChTime())
    patches.schedule(t + 0.01, depth_m=0.005, ramp_s=0.1, dt_s=m.dt_s)
    snap = m.snapshot()
    for _ in range(round(0.3 / m.dt_s)):
        m.step()
    after = _mean_contact(m, round(0.05 / m.dt_s))
    assert patches.displacement_m() == pytest.approx(0.005, abs=1e-12)
    assert after[3] < before[3] - 5000.0  # RR loses load (rigid legs, 5 mm)
    assert "ground_settlement.t_start_s" in snap.payload
    fresh = L2bModel(p2)
    attach_ground_patches(fresh, ("RR",))
    fresh.restore(snap)
    assert fresh.ground_patches.is_scheduled
