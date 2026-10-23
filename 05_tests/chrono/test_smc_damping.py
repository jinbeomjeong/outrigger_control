"""Chrono 10 SMC Hooke damping conventions (chrono_build_plan.md S0, R5; damping_survey.md).

Regression of the conventions measured by ``04_scripts/02_chrono/smc_damping_check.py``
(pychrono 10.0.0, 2026-10-20); the case builders and the identification live in that script and
are imported here so both use the same code:

(a) Hooke damping uses the effective mass: ``c = gn * m1 m2 / (m1 + m2)`` (floor mass 1e9, 1e3,
    1 kg; the fixed floor's mass counts).
(b) ``c`` is linear in the input ``gn`` (scale 1, 0.1, 0).
(c) Two SMC materials combine by the arithmetic mean of ``kn`` and of ``gn``.
(d) The YAML ``contact.rigid_floor.L1.gn_per_pad_1_s`` reproduces the YAML pad dashpot ``cn``,
    which since L1-R is on the LOCK stiffness (dynamics_model.md 5.12.8 Q-D3: ``derivation.
    damping_ratio`` 0.03 at ``damping_reference_mode_Hz`` 8.88 Hz, LOCK heave); the heave of the
    rigid 4-pad assembly on the SMC pads alone (no rod-side spring, FLOOR) then has zeta about
    0.035 (2026-10-24 update; before: head-only cn, zeta 0.03 at 7.39 Hz).
(e) The SMC contact force is integrated explicitly (semi-implicit Euler): no ``omega dt / 2``
    numerical damping; ``SetContactStiff(True)`` changes nothing.

Acceptance (chosen here; the measured margins are 5x or more): the identified ``k`` within
0.5 %, ``c`` within 1 % (single contact), damping ratio within 2 % and natural frequency within
0.5 % of the prediction of the exact discrete map. The rejected alternatives differ by more:
``m_eff = m_pad`` with a 1e3 kg floor +10.7 %, harmonic-mean composition -25 % in ``kn``,
backward-Euler contact numerical damping +7.7 % of the heave damping ratio at 1e-4 s.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytest.importorskip("pychrono")

import pychrono as ch  # noqa: E402

from outrigger_sim.params import Params, load_params  # noqa: E402

pytestmark = pytest.mark.chrono

SCRIPT = Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono" / "smc_damping_check.py"

K_REL_TOL = 5.0e-3
C_REL_TOL = 1.0e-2
ZETA_REL_TOL = 2.0e-2
F_REL_TOL = 5.0e-3
ZETA_NUMERICAL_MAX = 1.0e-4  # gn = 0: |zeta| (backward Euler would give omega dt / 2 = 0.022)
STATIC_REL_TOL = 1.0e-3
HEAVE_F_DESIGN_REL_TOL = 1.0e-3  # identified heave vs derivation.damping_reference_mode_Hz
WEIGHT_REL_TOL = 1.0e-2  # simulate-mode static equilibrium criterion
DTS = ("simulation.L1.dt_s", "simulation.dt_reference_s")
OMEGA_DT_MAX = 0.5
"""Identification resolution of the single-contact test (ASSUMPTION of this test: >= 12.6
steps per contact period; met by every case at dt 1e-4 s)."""


@pytest.fixture(scope="module")
def check() -> ModuleType:
    spec = importlib.util.spec_from_file_location("smc_damping_check", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def params(params_path: Path) -> Params:
    return load_params(params_path)


@pytest.fixture(scope="module", params=DTS)
def dt(request: pytest.FixtureRequest, params: Params) -> float:
    return float(params.get(request.param))


def _assert_matches_prediction(result) -> None:
    assert result.rel("k") == pytest.approx(0.0, abs=K_REL_TOL), result
    assert result.rel("c") == pytest.approx(0.0, abs=C_REL_TOL), result
    assert result.rel("zeta") == pytest.approx(0.0, abs=ZETA_REL_TOL), result
    assert result.rel("f") == pytest.approx(0.0, abs=F_REL_TOL), result


# --- helpers of the script ---------------------------------------------------------------


@pytest.mark.parametrize("scheme", ["symplectic_euler", "backward_euler"])
def test_discrete_map_inverse_round_trip(check: ModuleType, scheme: str) -> None:
    k, c, m, h = 2.08e7, 2.7e4, 106.78, 1.0e-4
    omega, zeta = check.discrete_modal(k, c, m, h, scheme)
    k_back, c_back = check.invert_discrete(omega, zeta, m, h, scheme)
    assert k_back == pytest.approx(k, rel=1e-9)
    assert c_back == pytest.approx(c, rel=1e-7)


def test_backward_euler_numerical_damping_is_omega_dt_over_2(check: ModuleType) -> None:
    """The textbook value the plan uses; holds for backward Euler, not for this contact."""
    k, m, h = 2.08e7, 106.78, 1.0e-5
    omega, zeta = check.discrete_modal(k, 0.0, m, h, "backward_euler")
    assert zeta == pytest.approx(math.sqrt(k / m) * h / 2, rel=1e-3)
    assert check.discrete_modal(k, 0.0, m, h, "symplectic_euler")[1] == pytest.approx(0, abs=1e-12)


# --- (c) composition rule ----------------------------------------------------------------


def test_composite_material_is_arithmetic_mean() -> None:
    a = ch.ChContactMaterialSMC()
    a.SetKn(1.0e6)
    a.SetGn(10.0)
    b = ch.ChContactMaterialSMC()
    b.SetKn(3.0e6)
    b.SetGn(50.0)
    composite = ch.ChContactMaterialCompositeSMC(ch.ChContactMaterialCompositionStrategy(), a, b)
    assert (composite.kn, composite.gn) == (2.0e6, 30.0)


def test_composite_contact_dynamics(check: ModuleType, params: Params, dt: float) -> None:
    """Sphere kn 3x and gn 0.25x the floor's: the contact behaves with the means."""
    l1 = params.contact.rigid_floor.L1
    kn_floor, gn_floor = l1.kn_per_pad_N_m[0], l1.gn_per_pad_1_s[0]
    result = check.single_contact(
        params, dt=dt, sphere_kn_N_m=3.0 * kn_floor, sphere_gn_1_s=0.25 * gn_floor
    )
    assert result.k_expected_N_m == pytest.approx(2.0 * kn_floor, rel=1e-7)
    assert result.c_expected_N_s_m == pytest.approx(
        0.625 * gn_floor * result.extra["m_eff_kg"], rel=1e-6
    )
    _assert_matches_prediction(result)
    harmonic_kn = 1.5 * kn_floor
    assert abs(result.k_identified_N_m / harmonic_kn - 1.0) > 0.2


# --- (a) effective mass ------------------------------------------------------------------


@pytest.mark.parametrize("floor_mass", [1.0e9, 1.0e3, 1.0])
def test_damping_uses_effective_mass(
    check: ModuleType, params: Params, dt: float, floor_mass: float
) -> None:
    m_pad = params.leg("FL").moving_part.mass_kg
    m_eff = m_pad * floor_mass / (m_pad + floor_mass)
    # a 1 kg floor makes the contact mode fast (omega ~ 4.6e3 rad/s): keep >= 12.6 steps per
    # period so that the identification resolves it (YAML L1 dt 2e-4 s gives omega dt 0.92)
    omega_eff = math.sqrt(params.contact.rigid_floor.L1.kn_per_pad_N_m[0] / m_eff)
    dt = min(dt, OMEGA_DT_MAX / omega_eff)
    result = check.single_contact(params, dt=dt, floor_mass_kg=floor_mass)
    assert result.extra["m_eff_kg"] == pytest.approx(m_eff, rel=1e-12)
    gn = result.extra["floor_gn_1_s"]
    assert result.c_identified_N_s_m == pytest.approx(gn * m_eff, rel=C_REL_TOL)
    _assert_matches_prediction(result)
    if floor_mass < 1.0e6:  # the moving mass alone would be clearly rejected
        assert abs(result.c_identified_N_s_m / (gn * m_pad) - 1.0) > 0.05


# --- (b) linearity in gn and (e) numerical damping -----------------------------------------


@pytest.mark.parametrize("gn_scale", [1.0, 0.1])
def test_damping_linear_in_gn(
    check: ModuleType, params: Params, dt: float, gn_scale: float
) -> None:
    result = check.single_contact(params, dt=dt, gn_scale=gn_scale)
    assert result.c_expected_N_s_m == pytest.approx(
        gn_scale * params.contact.rigid_floor.L1.gn_per_pad_1_s[0] * result.extra["m_eff_kg"],
        rel=1e-6,
    )
    _assert_matches_prediction(result)


def test_no_numerical_damping_of_contact(check: ModuleType, params: Params, dt: float) -> None:
    result = check.single_contact(params, dt=dt, gn_scale=0.0)
    assert abs(result.zeta_measured) < ZETA_NUMERICAL_MAX
    assert result.rel("k") == pytest.approx(0.0, abs=K_REL_TOL)


def test_contact_stiff_flag_has_no_effect(check: ModuleType, params: Params) -> None:
    dt = float(params.get("simulation.L1.dt_s"))
    plain = check.single_contact(params, dt=dt)
    stiff = check.single_contact(params, dt=dt, contact_stiff=True)
    assert stiff.extra["contact_stiff"] is True
    assert (stiff.f_measured_Hz, stiff.zeta_measured) == (plain.f_measured_Hz, plain.zeta_measured)


def test_static_penetration(check: ModuleType, params: Params) -> None:
    result = check.static_penetration(params, dt=float(params.get("simulation.L1.dt_s")))
    assert result["rel_error"] == pytest.approx(0.0, abs=STATIC_REL_TOL)
    assert result["contact_force_z_N"] == pytest.approx(result["weight_N"], rel=1e-3)


# --- (d) heave of the rigid 4-pad assembly -------------------------------------------------


def _yaml_per_leg(params: Params, key: str) -> list[float]:
    block = params.get(key)
    return [float(block[name]) for name in ("FL", "FR", "RL", "RR")]


HEAVE_FLOOR_ZETA_DOC = 0.035
"""dynamics_model.md 5.12.8 Q-D3: with the LOCK-basis dashpot the heave of the pads alone
(no rod-side spring, state FLOOR) has zeta about 0.035."""


def _check_heave(check: ModuleType, params: Params, dt: float) -> None:
    """Heave of the rigid 4-pad assembly on the SMC pads alone.

    Since L1-R (dynamics_model.md 5.12.8 Q-D3, YAML ``derivation.damping_basis: "LOCK"``) the pad
    dashpot is ``cn_i = 2 zeta sqrt(k_lock_i m / 4)`` on the LOCK stiffness (head + rod-side
    oil); ``damping_ratio`` 0.03 and ``damping_reference_mode_Hz`` refer to that LOCK heave. This
    test has no rod-side spring (the SMC ``kn`` = head side only), so it sees the FLOOR heave:
    ``zeta = sum(cn) / (2 sqrt(sum(kn) m))`` (about 0.035, Q-D3) and ``f = sqrt(sum(kn) / m) / 2 pi``.
    """
    result = check.heave(params, dt=dt)
    design = result.extra["design"]
    _assert_matches_prediction(result)
    # the YAML gn reproduces the YAML cn on each pad (gn per moving-part mass, floor 1e9 kg)
    c_per_pad = result.extra["c_per_pad_N_s_m"]
    assert c_per_pad == pytest.approx(result.extra["cn_per_pad_yaml_N_s_m"], rel=1e-6)
    m = design["damping_mass_kg"]
    assert result.mass_kg == pytest.approx(m, rel=1e-9)
    # YAML cn on the LOCK basis with the design zeta (Q-D3)
    assert params.get("contact.rigid_floor.L1.derivation.damping_basis") == "LOCK"
    zeta_d = design["damping_ratio"]
    k_lock = _yaml_per_leg(params, "contact.rigid_floor.L1.derivation.k_lock_N_m")
    kn = _yaml_per_leg(params, "contact.rigid_floor.L1.kn_per_pad_N_m")
    cn = _yaml_per_leg(params, "contact.rigid_floor.L1.cn_per_pad_N_s_m")
    for c_i, k_i in zip(cn, k_lock, strict=True):
        assert c_i == pytest.approx(2.0 * zeta_d * math.sqrt(k_i * m / 4.0), rel=1e-6)
    assert design["damping_reference_mode_Hz"] == pytest.approx(
        math.sqrt(sum(k_lock) / m) / (2.0 * math.pi), rel=1e-6
    )
    # FLOOR heave seen by this test
    zeta_floor = sum(cn) / (2.0 * math.sqrt(sum(kn) * m))
    f_floor = math.sqrt(sum(kn) / m) / (2.0 * math.pi)
    assert zeta_floor == pytest.approx(HEAVE_FLOOR_ZETA_DOC, abs=1.0e-3)
    assert result.zeta_expected == pytest.approx(zeta_floor, rel=1e-4)
    assert result.zeta_measured_minus_numerical == pytest.approx(zeta_floor, rel=ZETA_REL_TOL)
    assert result.f_measured_Hz == pytest.approx(f_floor, rel=HEAVE_F_DESIGN_REL_TOL)
    # placed at static equilibrium: first-step contact force = weight - c v0
    weight = result.extra["weight_N"]
    assert result.extra["contact_force_sum_first_step_N"] == pytest.approx(
        weight, rel=WEIGHT_REL_TOL
    )


def test_heave_general_dt(check: ModuleType, params: Params) -> None:
    _check_heave(check, params, float(params.get("simulation.L1.dt_s")))


@pytest.mark.sim
def test_heave_reference_dt(check: ModuleType, params: Params) -> None:
    _check_heave(check, params, float(params.get("simulation.dt_reference_s")))
