"""S8 seal friction (hydraulics/seal_friction) on the oil-only L2b law (k_out = inf).

Reference: ``00_docs/02_hydraulic/s8_seal_friction_counterbalance.md`` 2.9 (one front leg,
locked, rod-side law on, p_r0 2 bar g, locked at 118.1 kN, f = 0 at the start, s_ref fixed,
quasi-static link path c = s_ref - s: 0 -> +0.5 -> -0.5 -> 0 mm, F_s 4 kN) and C-9 (1)-(4).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from outrigger_sim.hydraulics.l2b_rod_side import L2bRodSide
from outrigger_sim.hydraulics.seal_friction import SealFriction, leg_limits_N
from outrigger_sim.params import load_params

DT = 1.0e-4
F_LOCK = 118.1e3
PATH_STEP = 0.25e-6


@pytest.fixture(scope="module")
def p2():
    return load_params(level="top", model="L2b_NSC")


def _k_out(p2, i):
    a = p2.l2b.actuator
    return 1.0 / (1.0 / a.k_rod_N_m[i] + 1.0 / a.frame_stiffness_N_m + 1.0 / a.k_concrete_N_m)


def _path(amp=0.5e-3, step=PATH_STEP):
    up = np.arange(0.0, amp + step / 2, step)
    down = np.arange(amp, -amp - step / 2, -step)
    back = np.arange(-amp, step / 2, step)
    return np.concatenate([up, down[1:], back[1:]])


class _Leg:
    """One leg: oil-only law + friction, quasi-static link path (spec 2.9)."""

    def __init__(self, p2, i, f_s, k_st=0.0, f_lock=F_LOCK):
        self.oil = L2bRodSide.from_params(p2, [i], mechanics="one_sided_parallel",
                                          oil_only=True)
        self.k_out = _k_out(p2, i)
        self.s_ref = p2.contact.rigid_floor.L1.operating_extension_m[i]
        k_h = self.oil.head_stiffness_N_m(0, self.s_ref)
        sp0 = self.s_ref - f_lock / k_h
        self.s0 = sp0 - f_lock / self.k_out
        self.fr = SealFriction([f_s], [self.k_out], stick_stiffness_N_m=k_st)
        self.fr.arm([sp0])
        self.sp0 = sp0
        self.t = 0.0
        self.fp = f_lock

    def hook(self, dc):
        s = np.array([self.s0 - dc])
        sr = np.array([self.s_ref])
        self.t += DT
        self.oil.spring_force_N(self.t, DT, [0.0], sr, sr - self.fr.s_p, [self.fp])
        spring = self.fr.step(s, sr, self.oil.oil_force_N, self.oil.oil_slope_N_m)
        self.oil.refresh_readings(sr - self.fr.s_p)
        self.fp = float(spring[0] - self.fr.f[0])
        return float(spring[0]), float(self.fr.f[0]), float(self.fr.s_p[0] - self.sp0)


def _run(leg, path, marks):
    out = {}
    first_slip = None
    for k, dc in enumerate(path):
        f_tot, f, sp = leg.hook(dc)
        if first_slip is None and not leg.fr.stuck[0]:
            first_slip = dc
        if k in marks:
            out[marks[k]] = (f_tot, f, sp)
    return out, first_slip


def test_level_definition_front_rear() -> None:
    lim = leg_limits_N(4000.0, 0.8333, ["FL", "FR", "RL", "RR"])
    np.testing.assert_allclose(lim, [4000.0, 4000.0, 3333.2, 3333.2])
    with pytest.raises(ValueError):
        leg_limits_N(1.0, 1.0, ["X1"])


def test_spec_2_9_front_cycle(p2) -> None:
    """Spec 2.9 table (allowance 1 N, 0.01 um except the first-slip path resolution)."""
    path = _path()
    n_up = round(0.5e-3 / PATH_STEP)
    marks = {n_up: "+0.5", 2 * n_up: "0 down", 3 * n_up: "-0.5", 4 * n_up: "0 end"}
    leg = _Leg(p2, 0, 4000.0)
    out, first = _run(leg, path, marks)
    expect = {"+0.5": (135.54e3, 4.0e3, -419.5e-6), "0 down": (114.77e3, -4.0e3, -16.6e-6),
              "-0.5": (97.76e3, -4.0e3, 406.1e-6), "0 end": (121.47e3, 4.0e3, 15.6e-6)}
    # The "0 down" row of the table is not at c = 0 exactly: its F (114.77) and s_p (-16.6 um)
    # satisfy F = k_out (s_p - s) only at c = +1.23 um (path sample of the reference script);
    # at c = 0 the same model gives F 114.73 / F_p 118.73 kN / s_p -15.57 um (slide slope
    # series(k_out, k_h + k_r) = 33.9 MN/m x 1.23 um = 42 N). Wider allowance on that row only.
    tol_f = {"0 down": 50.0}
    tol_s = {"0 down": 1.2e-6}
    for key, (f_tot, f, sp) in expect.items():
        got = out[key]
        assert got[0] == pytest.approx(f_tot, abs=tol_f.get(key, 6.0)), key  # printed to 10 N
        assert got[1] == pytest.approx(f, abs=1e-9), key
        assert got[0] - got[1] == pytest.approx(f_tot - f, abs=tol_f.get(key, 6.0)), key
        assert got[2] == pytest.approx(sp, abs=tol_s.get(key, 0.06e-6)), key  # 0.1 um print
    # internal consistency at every mark: F = k_out (s_p - s) = G + f
    for key in expect:
        f_tot, f, sp = out[key]
        dc = {"+0.5": 0.5e-3, "0 down": 0.0, "-0.5": -0.5e-3, "0 end": 0.0}[key]
        assert f_tot == pytest.approx(F_LOCK + leg.k_out * (sp + dc), abs=1e-3)
    assert first == pytest.approx(4000.0 / leg.k_out, abs=PATH_STEP)
    assert 4000.0 / leg.k_out == pytest.approx(18.46e-6, abs=0.005e-6)


def test_spec_2_9_rear_cycle(p2) -> None:
    path = _path()
    n_up = round(0.5e-3 / PATH_STEP)
    lim = leg_limits_N(4000.0, p2.l2b.seal_friction.rear_scale, ["RL"])[0]
    leg = _Leg(p2, 2, lim, f_lock=72.097e3)  # rear static load 72.097 kN (YAML 14.7)
    out, _ = _run(leg, path, {n_up: "+0.5", 4 * n_up: "0 end"})
    assert out["+0.5"][0] == pytest.approx(85.69e3, abs=6.0)
    assert out["+0.5"][0] - out["+0.5"][1] == pytest.approx(82.36e3, abs=6.0)
    assert out["0 end"][0] == pytest.approx(75.00e3, abs=6.0)
    assert out["0 end"][0] - out["0 end"][1] == pytest.approx(71.67e3, abs=6.0)


def test_zero_friction_equals_series_law(p2) -> None:
    """C-9 (1): F_s = 0 on the oil-only law = the series law (finite k_out) within 1e-12."""
    path = _path(amp=1.0e-3, step=5e-6)
    leg = _Leg(p2, 0, 0.0)
    series = L2bRodSide.from_params(p2, [0], mechanics="one_sided_parallel")
    c0 = F_LOCK / series.k2_N_m(0, leg.s_ref)
    worst = 0.0
    t = 0.0
    fs_prev = F_LOCK
    for dc in path:
        f_tot, f, _ = leg.hook(dc)
        t += DT
        fs = float(series.spring_force_N(t, DT, [0.0], [leg.s_ref], [c0 + dc], [fs_prev])[0])
        fs_prev = fs
        assert f == 0.0
        worst = max(worst, abs(f_tot - fs) / abs(fs))
    assert worst <= 1e-12


def test_stick_stiffness_first_slip(p2) -> None:
    """C-9 (4): k_st 1e8 N/m moves the first slip to about 68 um (path step 2.5 um)."""
    step = 2.5e-6
    path = np.arange(0.0, 0.2e-3, step)
    leg = _Leg(p2, 0, 4000.0, k_st=1.0e8)
    first = None
    for dc in path:
        leg.hook(dc)
        if not leg.fr.stuck[0]:
            first = dc
            break
    assert first == pytest.approx(67.8e-6, abs=step)


def test_dissipation_and_slip_counts(p2) -> None:
    leg = _Leg(p2, 0, 4000.0)
    _run(leg, _path(), {})
    # two reversals inside the cycle + the first slip: three stuck -> slide transitions
    assert leg.fr.slip_starts[0] == 3
    # dissipation = sum F_s |dsp| over sliding steps, positive
    assert leg.fr.dissipation_J[0] > 0.0
    travel = 2 * 0.4195e-3 + 2 * 0.4061e-3  # approx piston travel while sliding
    assert leg.fr.dissipation_J[0] == pytest.approx(4000.0 * travel, rel=0.05)


def test_static_ratio_holds_longer(p2) -> None:
    a, b = _Leg(p2, 0, 4000.0), _Leg(p2, 0, 4000.0)
    b.fr.static_ratio = 1.1
    path = np.arange(0.0, 60e-6, PATH_STEP)
    first = {}
    for name, leg in (("a", a), ("b", b)):
        for dc in path:
            leg.hook(dc)
            if not leg.fr.stuck[0]:
                first[name] = dc
                break
    assert first["b"] == pytest.approx(1.1 * first["a"], abs=2 * PATH_STEP)


def test_pressure_model_equals_level_at_reference(p2) -> None:
    sf = p2.l2b.seal_friction
    seal = {"kappa_N_per_m_Pa": sf.kappa_N_per_m_Pa, "F0_N": sf.F0_N,
            "F0_seal_diameter_sum_m": sf.F0_seal_diameter_sum_m,
            "p_ref_head_Pa": list(sf.p_ref_head_Pa), "p_ref_rod_Pa": sf.p_ref_rod_Pa,
            "bore_diameter_m": list(sf.bore_diameter_m), "rod_diameter_m": list(sf.rod_diameter_m)}
    lim = leg_limits_N(4000.0, sf.rear_scale, ["FL", "FR", "RL", "RR"])
    fr = SealFriction(lim, [2e8] * 4, pressure_model="seal_geometry", seal=seal)
    fr.update_limits(list(sf.p_ref_head_Pa), [sf.p_ref_rod_Pa] * 4)
    np.testing.assert_allclose(fr.F_s, lim, rtol=1e-12)
    # spec 2.3 kappa model at the operating pressures: front 2.11 kN for the 4 kN-scaled phi
    # ratio check: 200 bar locked -> 3.15 / 2.11 x level
    fr.update_limits([200e5, 200e5, 200e5, 200e5], [2e5] * 4)
    assert fr.F_s[0] / lim[0] == pytest.approx(3.15 / 2.11, rel=0.01)


def test_snapshot_roundtrip(p2) -> None:
    leg = _Leg(p2, 0, 4000.0)
    _run(leg, _path()[:2000], {})
    state = leg.fr.state_arrays()
    other = SealFriction([4000.0], [leg.k_out])
    other.restore_state(state)
    for k, v in other.state_arrays().items():
        assert np.array_equal(v, state[k], equal_nan=True), k
    assert math.isfinite(other.s_p[0])


def _linear_oil(k):
    return (lambda i, c: k * c), (lambda i, c: k)


def test_band_edge_chatter_count() -> None:
    """S8-A3: a slide stay of one step between stuck stays counts once; a stuck stay of 2.1 ms
    does not; without ``t_s`` nothing is counted (law unchanged)."""
    g, dg = _linear_oil(1.0e8)
    fr = SealFriction([1000.0], [1.0e8])
    fr.arm([0.0])
    sr = np.array([0.0])
    t = 0.0
    seq = [-2.0e-5, -5.0e-6] + [-5.0e-6] * 20 + [-3.0e-5]
    for s in seq:
        t += DT
        fr.step(np.array([s]), sr, g, dg, t_s=t)
    assert fr.slip_starts[0] == 2
    assert fr.chatter_count[0] == 1
    rec = fr.record()
    assert rec["band_edge_chatter"] == [1] and rec["band_edge_chatter_window_s"] == 1.0e-3
    st = fr.state_arrays()
    fr2 = SealFriction([1000.0], [1.0e8])
    fr2.restore_state({k: v for k, v in st.items() if k not in ("chatter_count",
                                                                "stay_start_t_s")})
    assert fr2.chatter_count[0] == 0  # old snapshots: count from 0
    fr3 = SealFriction([1000.0], [1.0e8])
    fr3.arm([0.0])
    for s in seq:
        fr3.step(np.array([s]), sr, g, dg)
    assert fr3.chatter_count[0] == 0 and fr3.f[0] == fr.f[0] and fr3.s_p[0] == fr.s_p[0]


def test_split_pressures_floor() -> None:
    """S8-A1: p_h floored, p_r re-solved, net force unchanged; legs above the floor keep the
    unfloored expression bit for bit."""
    pytest.importorskip("pychrono")
    from outrigger_sim.chrono.l2b_actuator import split_pressures

    a_p = np.array([0.0132732, 0.0132732, 0.0095033, 0.0095033])
    a_r = np.array([0.0037699, 0.0037699, 0.0031416, 0.0031416])
    f = np.array([-9.05e3, 50e3, -700.0, 30e3])
    p_r = np.array([2.0e5, 2.0e5, 2.0e5, 3.0e6])
    floor = np.array([-0.91325e5, 2.0e5, 2.0e5, -0.91325e5])
    p_h, p_r2, hit = split_pressures(f, p_r, a_p, a_r, floor)
    assert hit.tolist() == [True, False, True, False]
    assert np.all(p_h >= floor)
    np.testing.assert_allclose(p_h * a_p - p_r2 * a_r, f, rtol=0, atol=1e-6)
    raw = (f + p_r * a_r) / a_p
    assert p_h[1] == raw[1] and p_h[3] == raw[3] and p_r2[1] == p_r[1]
    assert p_h[0] == floor[0] and p_r2[0] > p_r[0]
