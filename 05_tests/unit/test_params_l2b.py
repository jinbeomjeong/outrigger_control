"""S7: ``load_params(model=...)`` and the typed L2b-NSC blocks (chrono_build_plan.md S7)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from outrigger_sim.params import (
    LEG_ORDER,
    ModelKind,
    ParamsError,
    axial_stiffness_N_m,
    load_params,
)

# L1 fingerprints before S7 (2026-10-24, YAML file sha256 84a46dc1...): the model selection
# must not change them (R16 snapshots).
L1_SHA256_BEFORE_S7 = {
    "top": "de068f3b6548a33d6d15b83c7604124fbae965a6fcda448eff7d66409147d7f5",
    "middle": "55686abc569501e11ce9c29e05978f6115cb84315c8436bf84118a960554b599",
    "bottom": "06f3ae97b9d372ca5ed99bff2f3e842c2d97a60722896244fad5e68c9b094550",
}
YAML_FILE_SHA256 = "84a46dc172b9442f80b921a788bbfc5c01cd1e85194ad671b1627b54e1a771b9"


@pytest.fixture(scope="module")
def yaml_tree(params_path: Path) -> dict:
    return yaml.safe_load(params_path.read_text(encoding="utf-8"))


def test_l1_default_is_unchanged(params_path: Path) -> None:
    for level, sha in L1_SHA256_BEFORE_S7.items():
        p = load_params(params_path, level=level)
        if p.file_sha256 != YAML_FILE_SHA256:
            pytest.skip("YAML regenerated since S7; L1 fingerprint baseline no longer applies")
        assert p.model is ModelKind.L1
        assert p.l2b is None
        assert p.sha256 == sha
        assert load_params(params_path, level=level, model="L1").sha256 == sha


def test_l2b_fingerprint_differs_and_is_deterministic(params_path: Path) -> None:
    l1 = load_params(params_path)
    a = load_params(params_path, model="L2b_NSC")
    b = load_params(params_path, model=ModelKind.L2B_NSC)
    assert a.model is ModelKind.L2B_NSC
    assert a.sha256 == b.sha256 != l1.sha256
    assert a.file_sha256 == l1.file_sha256


def test_unknown_model_raises(params_path: Path) -> None:
    with pytest.raises(ParamsError, match="model"):
        load_params(params_path, model="L2")


def test_l2b_typed_values_equal_yaml(params_path: Path, yaml_tree: dict) -> None:
    p = load_params(params_path, model="L2b_NSC")
    assert p.l2b is not None
    blk = yaml_tree["actuator"]["L2b_NSC"]
    act = p.l2b.actuator
    for i, leg in enumerate(LEG_ORDER):
        assert act.axial_operating_point_N_m[i] == float(
            blk["axial_stiffness"]["operating_point_N_m"][leg]
        )
        assert act.oil_damping_N_s_m[i] == float(blk["oil_damping_N_s_m"][leg])
        assert act.oil_damping_moving_N_s_m[i] == float(blk["oil_damping_moving_N_s_m"][leg])
        assert act.lateral_bushing_N_m[i] == float(blk["lateral_bushing_N_m"][leg])
        assert act.lateral_bushing_damping_input_N_s_m[i] == float(
            blk["lateral_bushing_damping_input_N_s_m"][leg]
        )
        assert act.head_area_m2[i] == float(yaml_tree["legs"][leg]["cylinder"]["head_area_m2"])
        assert act.k_rod_N_m[i] == float(
            yaml_tree["contact"]["rigid_floor"]["L1"]["derivation"]["k_rod_N_m"][leg]
        )
    assert act.k_concrete_N_m == float(yaml_tree["contact"]["rigid_floor"]["concrete"]["k_N_m"])
    floor = yaml_tree["contact"]["rigid_floor"]["L2b_NSC"]
    assert p.l2b.rigid_floor.solver == floor["solver"]
    assert p.l2b.rigid_floor.solver_max_iterations == int(floor["solver_max_iterations"])
    assert isinstance(p.l2b.rigid_floor.solver_max_iterations, int)
    assert p.l2b.rigid_floor.friction == float(floor["friction"])
    assert p.l2b.rigid_floor.crawler_friction == float(yaml_tree["contact"]["crawler"]["friction"])
    assert p.l2b.dt_s == float(yaml_tree["simulation"]["L2b_NSC"]["dt_s"])


def test_axial_stiffness_reproduces_operating_point(params_path: Path) -> None:
    p = load_params(params_path, model="L2b_NSC")
    act = p.l2b.actuator
    e_op = p.contact.rigid_floor.L1.operating_extension_m
    k_oil = p.get("contact.rigid_floor.L1.derivation.k_oil_N_m")
    for i, leg in enumerate(LEG_ORDER):
        kw = dict(
            bulk_modulus_Pa=act.oil_bulk_modulus_eff_Pa,
            head_area_m2=act.head_area_m2[i],
            dead_length_m=act.oil_dead_length_m,
            k_rod_N_m=act.k_rod_N_m[i],
            k_frame_N_m=act.frame_stiffness_N_m,
        )
        k = axial_stiffness_N_m(e_op[i], k_concrete_N_m=act.k_concrete_N_m, **kw)
        assert k == pytest.approx(act.axial_operating_point_N_m[i], rel=1e-8)
        # = L1 pad stiffness (head side only, dynamics_model.md 2.3)
        assert k == pytest.approx(p.contact.rigid_floor.L1.kn_per_pad_N_m[i], rel=1e-8)
        # oil column alone = the YAML k_oil at e_op
        k_oil_only = act.oil_bulk_modulus_eff_Pa * act.head_area_m2[i] / (
            act.oil_dead_length_m + e_op[i]
        )
        assert k_oil_only == pytest.approx(float(k_oil[leg]), rel=1e-8)
        # SCM option drops the concrete -> stiffer path
        assert axial_stiffness_N_m(e_op[i], k_concrete_N_m=None, **kw) > k
        # monotonically softer with extension (longer oil column)
        assert axial_stiffness_N_m(0.6, k_concrete_N_m=act.k_concrete_N_m, **kw) < k


def test_stale_operating_point_raises(params_path: Path) -> None:
    with pytest.raises(ParamsError, match="operating_point_N_m"):
        load_params(
            params_path, model="L2b_NSC", overrides={"actuator.oil_bulk_modulus_eff_Pa": 1.6e9}
        )
    # the same override is fine for L1 (derived values are not recomputed, as before)
    assert load_params(params_path, overrides={"actuator.oil_bulk_modulus_eff_Pa": 1.6e9})


def test_lateral_damping_input_is_half_the_l1_ct(params_path: Path) -> None:
    p = load_params(params_path, model="L2b_NSC")
    for i in range(len(LEG_ORDER)):
        assert 2.0 * p.l2b.actuator.lateral_bushing_damping_input_N_s_m[i] == pytest.approx(
            p.contact.rigid_floor.L1.ct_per_pad_N_s_m[i], rel=1e-8
        )
        assert p.l2b.actuator.lateral_bushing_N_m[i] == pytest.approx(
            p.contact.rigid_floor.L1.kt_per_pad_N_m[i], rel=1e-12
        )


def test_axial_stiffness_rejects_nonpositive_column() -> None:
    with pytest.raises(ValueError, match="column"):
        axial_stiffness_N_m(
            -0.1, bulk_modulus_Pa=1e9, head_area_m2=0.01, dead_length_m=0.05,
            k_rod_N_m=1e9, k_frame_N_m=1e9, k_concrete_N_m=None,
        )
