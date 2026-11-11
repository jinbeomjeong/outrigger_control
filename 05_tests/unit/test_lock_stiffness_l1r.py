"""Harness option ``lock_stiffness="l1r"`` (``k2_dyn_sensitivity.md`` A.3-2).

The option puts the rod-side oil column of a locked leg in parallel with ``k_oil``. Checked here:
the kernel helpers of ``run_mast_flex_c2_check`` against the L1-R definitions of
``outrigger_sim.hydraulics.rod_chamber``, the derived values against the YAML, the off path (bit
for bit against the original ``run_control_comparison`` kernel) and the KPlant request / identity
handling. No closed-loop run: the 1 mm step matrix against E2 and the stored-hash comparison are
record runs. The reduced harness needs numba (dynamics-dev); the module skips without it.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
DYNAMICS = ROOT / "04_scripts" / "01_dynamics"
SRC = ROOT / "03_src"
for _folder in (DYNAMICS, SRC):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

pytest.importorskip("numba")

import run_mast_flex_c2_check as rmf  # noqa: E402
import run_s6_slope_boundary_check as rsb  # noqa: E402

from outrigger_sim.hydraulics.rod_chamber import RodChamberLegParams  # noqa: E402

BETA_PA = 1.0e9
K_LOCK_E2_N_M = {"front": 33.93e6, "rear": 26.40e6}
"""E2 L1-R locked pad stiffness (k2_dyn_sensitivity.md A.1)."""
DT_S = 5e-4


def _plant(mode: str | None = None, **kwargs) -> rmf.FlexPlant:
    rmf.CONFIG.clear()
    plant = rmf.FlexPlant("top", 0.0, 0.0, BETA_PA, 0.0)
    if mode is not None:
        plant.set_lock_stiffness(mode, **kwargs)
    return plant


def _yaml_rod_side() -> dict:
    return rmf.dm.load_params()["actuator"]["rod_side"]


def _per_leg(mapping: dict) -> list[float]:
    return [float(mapping[leg]) for leg in rmf.dm.LEG_NAMES]


# --- derived values ------------------------------------------------------------------------------
def test_rod_stiffness_is_the_yaml_l1r_value() -> None:
    plant = _plant("l1r")
    rod_side = _yaml_rod_side()
    assert plant.krs == pytest.approx(_per_leg(rod_side["k_rod_side_N_m"]), rel=1e-8)
    record = plant.lock_record
    assert record["column_length_m"] == pytest.approx(
        _per_leg(rod_side["column_length_m"]), abs=1e-12)
    assert record["k_lock_N_m"][0] == pytest.approx(K_LOCK_E2_N_M["front"], rel=1e-3)
    assert record["k_lock_N_m"][3] == pytest.approx(K_LOCK_E2_N_M["rear"], rel=1e-3)


def test_rod_dead_length_override_and_beta_scale_k_rs() -> None:
    nominal = _plant("l1r")
    short = _plant("l1r", rod_dead_length_m=0.02)
    column = np.asarray(nominal.lock_record["column_length_m"])
    expected = nominal.krs * column / (column - 0.05 + 0.02)
    assert short.krs == pytest.approx(expected, rel=1e-12)
    assert short.lock_record["rod_dead_length_source"] == "override"
    rmf.CONFIG.clear()
    stiff_oil = rmf.FlexPlant("top", 0.0, 0.0, 1.6e9, 0.0)
    stiff_oil.set_lock_stiffness("l1r")
    assert stiff_oil.krs == pytest.approx(1.6 * nominal.krs, rel=1e-12)


@pytest.mark.parametrize(("mode", "kwargs"), [
    ("on", {}),
    ("off", {"rod_dead_length_m": 0.05}),
    ("l1r", {"rod_dead_length_m": 0.0}),
])
def test_bad_requests_are_refused(mode, kwargs) -> None:
    with pytest.raises(ValueError):
        _plant(mode, **kwargs)


def test_option_is_set_once_before_the_first_step() -> None:
    plant = _plant("l1r")
    with pytest.raises(RuntimeError):
        plant.set_lock_stiffness("l1r")
    stepped = _plant()
    stepped.step(np.zeros(4), 2)
    with pytest.raises(RuntimeError):
        stepped.set_lock_stiffness("l1r")


# --- off path ------------------------------------------------------------------------------------
def _drive(plant, n_chunks: int = 300) -> None:
    rng = np.random.default_rng(7)
    for k in range(n_chunks):
        is_moving = k % 50 < 25
        speed = rng.uniform(-1.0, 1.0, 4) * 0.02 if is_moving else np.zeros(4)
        plant.step(speed, 4)


def test_off_path_is_the_original_kernel_bit_for_bit() -> None:
    rmf.CONFIG.clear()
    original = rmf.ORIG_PLANT("top", 1.0, 2.0, BETA_PA, 0.0)
    flex = rmf.FlexPlant("top", 1.0, 2.0, BETA_PA, 0.0)
    explicit_off = rmf.FlexPlant("top", 1.0, 2.0, BETA_PA, 0.0)
    explicit_off.set_lock_stiffness("off")
    for plant in (original, flex, explicit_off):
        _drive(plant)
    for name in ("r", "v", "q", "w", "x", "sref", "f"):
        assert np.array_equal(getattr(original, name), getattr(flex, name)), name
        assert np.array_equal(getattr(flex, name), getattr(explicit_off, name)), name
    assert np.array_equal(flex.pressure(), original.pressure())
    assert flex.lockm == 0 and not flex.frod.any()


# --- kernel helpers ------------------------------------------------------------------------------
def test_rod_position_without_rod_force_is_the_head_only_solve() -> None:
    ko, ks, sref, c0, gax = 2.9e7, 2.2e8, 0.40, 1047.0 + 300.0, 0.399
    free = (ko * sref + c0) / ko
    contact = (ko * sref + c0 + ks * gax) / (ks + ko)
    assert rmf._rod_position(ks, 0.0, gax, ko, sref, c0, False, 0.0, 0.0, 0.0) == contact
    assert rmf._rod_position(ks, 0.0, 1.0, ko, sref, c0, False, 0.0, 0.0, 0.0) == free


def _locked_pad_force(gax: float, x_lock: float, cap: float) -> float:
    """Pad force of a locked leg (rod weight 0) after the rod solve; checks the equilibrium."""
    ko, krs, ks, sref = 2.9e7, 1.08e7, 2.2e8, 0.40
    x = rmf._rod_position(ks, 0.0, gax, ko, sref, 0.0, True, krs, x_lock, cap)
    rod = rmf._rod_force(0, x, np.ones(1, np.int64), np.array([krs]), np.array([x_lock]),
                         np.array([cap]))
    pad = ks * max(x - gax, 0.0)
    assert pad == pytest.approx(ko * (sref - x) + rod, rel=1e-12, abs=1e-6)
    return pad


def test_locked_leg_is_stiffer_until_the_rod_side_floor() -> None:
    ko, krs, ks = 2.9e7, 1.08e7, 2.2e8
    x_lock, gax, step = 0.399, 0.398, 1.0e-5
    k_lock = 1.0 / (1.0 / (ko + krs) + 1.0 / ks)
    k_head = 1.0 / (1.0 / ko + 1.0 / ks)
    # gax is the floor along the leg axis: a larger gax unloads the pad (compression x - gax)
    high_cap = 1.0e9  # rod side far above its floor: the spring acts
    unloading = (_locked_pad_force(gax, x_lock, high_cap)
                 - _locked_pad_force(gax + step, x_lock, high_cap)) / step
    assert unloading == pytest.approx(k_lock, rel=1e-6)
    low_cap = 1.0e3  # x well below x_lock - cap / k_rs: rod side at its floor, force capped
    loading = (_locked_pad_force(gax - step, x_lock, low_cap)
               - _locked_pad_force(gax, x_lock, low_cap)) / step
    assert loading == pytest.approx(k_head, rel=1e-6)


def _lock_state() -> dict:
    return {"rlock": np.zeros(1, np.int64), "xlk": np.zeros(1), "fcap": np.zeros(1),
            "frod": np.zeros(1), "frel": np.zeros(1), "tdec": np.zeros(1),
            "rdir": np.ones(1, np.int64)}


def test_lock_release_and_relock_follow_the_l1r_rules() -> None:
    params = RodChamberLegParams(head_area_m2=1.327e-2, annulus_area_m2=3.770e-3,
                                 head_stiffness_N_m=2.9e7, rod_stiffness_N_m=1.08e7,
                                 outer_stiffness_N_m=2.2e8, rod_weight_N=1047.0)
    floor_gauge = params.floor_gauge_Pa
    tau_s = 0.05
    lkp = np.array([1e-6, tau_s, floor_gauge, params.poc_pilot_ratio, params.poc_cracking_Pa,
                    params.p_head_back_retract_Pa])
    area_p = np.array([params.head_area_m2])
    area_ann = np.array([params.annulus_area_m2])
    krs, p_r0_extend = np.array([1.08e7]), np.array([2.0e5])
    state = _lock_state()

    def update(u: float, x: float, head_force: float) -> None:
        rmf._update_rod_lock(0, u, DT_S, x, head_force, lkp, area_p, area_ann, p_r0_extend, krs,
                             state["rlock"], state["xlk"], state["fcap"], state["frod"],
                             state["frel"], state["tdec"], state["rdir"])

    update(0.0, 0.40, 2.0e4)  # fresh leg: locked after an extension
    assert state["rlock"][0] == 1 and state["xlk"][0] == 0.40
    assert state["fcap"][0] == pytest.approx((2.0e5 - floor_gauge) * area_ann[0])

    state["frod"][0] = 500.0
    update(-0.01, 0.40, 2.0e4)  # release: the residual decays from 500 N
    assert state["rlock"][0] == 0 and state["fcap"][0] == 500.0 and state["rdir"][0] == -1
    for _ in range(100):
        update(-0.01, 0.40, 2.0e4)
    assert state["fcap"][0] == pytest.approx(500.0 * math.exp(-100 * DT_S / tau_s), rel=1e-9)

    state["frod"][0] = state["fcap"][0]
    update(0.0, 0.39, 3.0e4)  # relock after a retraction: residual absorbed, pilot-threshold p_r0
    residual = state["frod"][0]
    p_r0 = params.retract_threshold_rod_pressure_Pa(3.0e4 + residual)
    assert state["xlk"][0] == pytest.approx(0.39 + residual / krs[0])
    expected_cap = residual + (p_r0 - floor_gauge) * area_ann[0]
    assert state["fcap"][0] == pytest.approx(expected_cap, rel=1e-12)


def test_plant_pressure_includes_the_rod_force_when_on() -> None:
    rmf.CONFIG.clear()
    plant = rmf.FlexPlant("top", 0.0, 0.0, BETA_PA, 0.0, init_ext=[0.40] * 4)  # on the pads
    plant.set_lock_stiffness("l1r")
    _drive(plant, 140)  # ends in a locked phase while the body still settles
    assert plant.lockm == 1 and plant.rlock.all()
    assert plant.frod.any()
    expected = plant.ko * (plant.sref - plant.x) + plant.frod
    assert np.array_equal(plant.pressure(), expected)


# --- KPlant request ------------------------------------------------------------------------------
@pytest.fixture
def set_rcfg(monkeypatch):
    def apply(values: dict) -> None:
        monkeypatch.setattr(rsb.rpt, "RCFG", dict(values))
    return apply


def test_kplant_without_the_key_keeps_the_option_off(set_rcfg) -> None:
    set_rcfg({"case_id": "a"})
    plant = rsb.KPlant("top", 0.0, 0.0, BETA_PA, 0.0)
    assert plant.lock_stiffness_requested is False and plant.lockm == 0
    rsb.check_kplant_lock_stiffness(plant, {"rcfg": {}})
    with pytest.raises(RuntimeError):
        rsb.check_kplant_lock_stiffness(plant, {"rcfg": {"lock_stiffness": "l1r"}})


def test_kplant_l1r_request_and_identity(set_rcfg) -> None:
    set_rcfg({"case_id": "a", "lock_stiffness": "l1r", "lock_rod_dead_length_m": 0.1})
    plant = rsb.KPlant("top", 0.0, 0.0, BETA_PA, 0.0)
    assert plant.lockm == 1 and plant.lock_record["rod_dead_length_m"] == 0.1
    rsb.check_kplant_lock_stiffness(plant, {"rcfg": {"lock_stiffness": "l1r"}})
    with pytest.raises(RuntimeError):
        rsb.check_kplant_lock_stiffness(plant, {"rcfg": {"lock_stiffness": "off"}})


def test_kplant_rod_dead_length_needs_the_mode(set_rcfg) -> None:
    set_rcfg({"case_id": "a", "lock_rod_dead_length_m": 0.1})
    with pytest.raises(ValueError):
        rsb.KPlant("top", 0.0, 0.0, BETA_PA, 0.0)
