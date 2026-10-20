"""Unit tests for the parameter loader (00_docs/03_chrono/chrono_build_plan.md S0, R16)."""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from outrigger_sim.params import (
    LEG_ORDER,
    AugerLevel,
    Params,
    ParamsError,
    find_numeric_strings,
    load_params,
    parameters_sha256,
)

GROUND_MASS_LINE = "ground_body_mass_kg: 1000000000.0"
# Integer counts in the YAML; every other number must load as float.
COUNT_KEY_NAMES = ("spheres_per_track", "solver_max_iterations")


@pytest.fixture(scope="module")
def yaml_tree(params_path: Path) -> dict[str, Any]:
    """The YAML read independently of the loader."""
    return yaml.safe_load(params_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def params(params_path: Path) -> Params:
    return load_params(params_path)


def _yaml_value(tree: dict[str, Any], dotted_path: str) -> Any:
    node: Any = tree
    for key in dotted_path.split("."):
        node = node[key]
    return node


def _leaves(node: Any, path: tuple = ()) -> list[tuple[tuple, Any]]:
    if isinstance(node, dict):
        return [leaf for key, value in node.items() for leaf in _leaves(value, (*path, key))]
    if isinstance(node, list | tuple):
        return [leaf for index, item in enumerate(node) for leaf in _leaves(item, (*path, index))]
    return [(path, node)]


def _raw_at(params: Params, path: tuple) -> Any:
    node: Any = params.raw
    for part in path:
        node = node[part]
    return node


def _write_variant(tmp_path: Path, params_path: Path, old: str, new: str) -> Path:
    text = params_path.read_text(encoding="utf-8")
    assert old in text, f"fixture text {old!r} not found in the YAML"
    variant = tmp_path / "variant.yaml"
    variant.write_text(text.replace(old, new, 1), encoding="utf-8")
    return variant


def _dump_tree(tmp_path: Path, tree: dict[str, Any], *, sort_keys: bool = False) -> Path:
    variant = tmp_path / "variant.yaml"
    text = yaml.safe_dump(tree, sort_keys=sort_keys, allow_unicode=True)
    variant.write_text(text, encoding="utf-8")
    return variant


# --- round trip --------------------------------------------------------------------------


def test_every_raw_leaf_equals_the_yaml_value(params: Params, yaml_tree: dict) -> None:
    leaves = _leaves(yaml_tree)
    assert len(leaves) > 600
    for path, yaml_value in leaves:
        loaded = _raw_at(params, path)
        if isinstance(yaml_value, str):
            assert loaded == yaml_value, path
        elif isinstance(yaml_value, int) and path[-1] in COUNT_KEY_NAMES:
            assert type(loaded) is int and loaded == yaml_value, path
        else:
            assert type(loaded) is float, path
            assert loaded == float(yaml_value), path


SCALAR_KEYS: list[tuple[str, Callable[[Params], Any]]] = [
    ("meta.gravity_m_s2", lambda p: p.meta.gravity_m_s2),
    ("contact.rigid_floor.friction", lambda p: p.contact.rigid_floor.friction),
    (
        "contact.rigid_floor.ground_body_mass_kg",
        lambda p: p.contact.rigid_floor.ground_body_mass_kg,
    ),
    (
        "contact.rigid_floor.damping_input_convention",
        lambda p: p.contact.rigid_floor.damping_input_convention,
    ),
    ("contact.rigid_floor.geometry", lambda p: p.contact.rigid_floor.geometry),
    (
        "contact.rigid_floor.L1.slip_damping_reenable_speed_m_s",
        lambda p: p.contact.rigid_floor.L1.slip_damping_reenable_speed_m_s,
    ),
    ("simulation.L1.dt_s", lambda p: p.simulation.L1.dt_s),
    ("simulation.crawler_clearance_m", lambda p: p.simulation.crawler_clearance_m),
    ("simulation.settle_on_crawler_min_s", lambda p: p.simulation.settle_on_crawler_min_s),
    ("simulation.settle_on_pads_min_s", lambda p: p.simulation.settle_on_pads_min_s),
    ("actuator.stroke_m", lambda p: p.actuator.stroke_m),
    ("actuator.full_stroke_time_s", lambda p: p.actuator.full_stroke_time_s),
    ("actuator.max_speed_m_s", lambda p: p.actuator.max_speed_m_s),
    ("control.F_min_cylinder_N", lambda p: p.control.F_min_cylinder_N),
    ("ground.crawler_bottom_z_m", lambda p: p.ground.crawler_bottom_z_m),
]


@pytest.mark.parametrize(("yaml_path", "typed"), SCALAR_KEYS, ids=[k for k, _ in SCALAR_KEYS])
def test_typed_scalar_equals_yaml(
    params: Params, yaml_tree: dict, yaml_path: str, typed: Callable[[Params], Any]
) -> None:
    assert typed(params) == _yaml_value(yaml_tree, yaml_path)


PER_LEG_L1_KEYS = [
    "kn_per_pad_N_m",
    "kt_per_pad_N_m",
    "cn_per_pad_N_s_m",
    "ct_per_pad_N_s_m",
    "gn_per_pad_1_s",
    "bushing_stiffness_per_pad_N_m",
    "bushing_damping_input_per_pad_N_s_m",
]


@pytest.mark.parametrize("key", PER_LEG_L1_KEYS)
def test_l1_per_leg_values_follow_leg_order(params: Params, yaml_tree: dict, key: str) -> None:
    yaml_block = yaml_tree["contact"]["rigid_floor"]["L1"][key]
    expected = tuple(float(yaml_block[name]) for name in LEG_ORDER)
    assert getattr(params.contact.rigid_floor.L1, key) == expected


def test_leg_geometry_equals_yaml(params: Params, yaml_tree: dict) -> None:
    assert params.meta.leg_order == LEG_ORDER
    for index, name in enumerate(LEG_ORDER):
        leg = params.leg(name)
        yaml_leg = yaml_tree["legs"][name]
        assert params.legs[index] is leg and leg.index == index
        assert list(leg.attachment_point_m) == yaml_leg["attachment_point_m"]
        assert list(leg.pad_bottom_center_retracted_m) == yaml_leg["pad_bottom_center_retracted_m"]
        assert [list(v) for v in leg.pad.polygon_xy_m] == yaml_leg["pad"]["polygon_xy_m"]
        assert leg.moving_part.mass_kg == yaml_leg["moving_part"]["mass_kg"]
        assert list(leg.moving_part.com_m) == yaml_leg["moving_part"]["com_retracted_m"]
        tilt_deg = yaml_leg["pad"]["swivel_tilt_range_deg"]
        assert leg.pad.swivel_tilt_range_rad == pytest.approx(math.radians(tilt_deg), rel=1e-15)


def test_no_numeric_strings_remain(params: Params) -> None:
    assert params.numeric_string_paths() == []


# --- numeric coercion --------------------------------------------------------------------


def test_unquoted_exponent_string_is_coerced_to_float(tmp_path: Path, params_path: Path) -> None:
    variant = _write_variant(tmp_path, params_path, GROUND_MASS_LINE, "ground_body_mass_kg: 1e9")
    raw_variant = yaml.safe_load(variant.read_text(encoding="utf-8"))
    # The PyYAML (YAML 1.1) trap this loader exists for: no dot, no exponent sign -> str.
    assert raw_variant["contact"]["rigid_floor"]["ground_body_mass_kg"] == "1e9"
    assert find_numeric_strings(raw_variant) == ["contact.rigid_floor.ground_body_mass_kg"]

    loaded = load_params(variant)
    assert loaded.contact.rigid_floor.ground_body_mass_kg == 1e9
    assert type(loaded.get("contact.rigid_floor.ground_body_mass_kg")) is float
    assert loaded.numeric_string_paths() == []


def test_float_spelling_does_not_change_the_parameter_hash(
    tmp_path: Path, params_path: Path, params: Params
) -> None:
    variant = _write_variant(tmp_path, params_path, GROUND_MASS_LINE, "ground_body_mass_kg: 1e9")
    loaded = load_params(variant)
    assert loaded.sha256 == params.sha256
    assert loaded.file_sha256 != params.file_sha256


def test_non_numeric_string_raises_with_key_path(tmp_path: Path, params_path: Path) -> None:
    variant = _write_variant(
        tmp_path, params_path, GROUND_MASS_LINE, 'ground_body_mass_kg: "heavy"'
    )
    with pytest.raises(ParamsError, match=r"contact\.rigid_floor\.ground_body_mass_kg"):
        load_params(variant)


def test_non_numeric_list_element_raises_with_index(tmp_path: Path, yaml_tree: dict) -> None:
    tree = yaml.safe_load(yaml.safe_dump(yaml_tree))
    tree["legs"]["RL"]["pad_bottom_center_retracted_m"][2] = "low"
    with pytest.raises(ParamsError, match=r"legs\.RL\.pad_bottom_center_retracted_m\[2\]"):
        load_params(_dump_tree(tmp_path, tree))


# --- required keys and leg order ---------------------------------------------------------


@pytest.mark.parametrize(
    "dotted_path",
    ["meta.gravity_m_s2", "contact.rigid_floor.L1.gn_per_pad_1_s", "simulation.L1.dt_s"],
)
def test_missing_key_raises_with_path(tmp_path: Path, yaml_tree: dict, dotted_path: str) -> None:
    tree = yaml.safe_load(yaml.safe_dump(yaml_tree))
    *parents, leaf = dotted_path.split(".")
    del _yaml_value(tree, ".".join(parents))[leaf]
    with pytest.raises(ParamsError, match=dotted_path.replace(".", r"\.")):
        load_params(_dump_tree(tmp_path, tree))


def test_missing_leg_in_per_leg_block_raises(tmp_path: Path, yaml_tree: dict) -> None:
    tree = yaml.safe_load(yaml.safe_dump(yaml_tree))
    del tree["contact"]["rigid_floor"]["L1"]["kn_per_pad_N_m"]["RR"]
    with pytest.raises(ParamsError, match=r"contact\.rigid_floor\.L1\.kn_per_pad_N_m"):
        load_params(_dump_tree(tmp_path, tree))


def test_leg_order_mismatch_raises(tmp_path: Path, params_path: Path) -> None:
    variant = _write_variant(
        tmp_path,
        params_path,
        'leg_order: ["FL", "FR", "RL", "RR"]',
        'leg_order: ["FL", "RL", "FR", "RR"]',
    )
    with pytest.raises(ParamsError, match=r"meta\.leg_order"):
        load_params(variant)


# --- auger level -------------------------------------------------------------------------


def test_default_level_is_the_yaml_default(params: Params, yaml_tree: dict) -> None:
    assert params.level == yaml_tree["superstructure"]["default_auger_level"] == AugerLevel.TOP


def test_three_levels_select_different_superstructures(params_path: Path, yaml_tree: dict) -> None:
    loaded = {level: load_params(params_path, level=level) for level in AugerLevel}
    for level, level_params in loaded.items():
        yaml_level = yaml_tree["superstructure"]["auger_levels"][level.value]
        mass_properties = level_params.superstructure.mass_properties
        assert level_params.superstructure.level is level
        assert level_params.superstructure.auger_travel_m == yaml_level["auger_travel_m"]
        assert list(mass_properties.com_m) == yaml_level["com_m"]
        assert [list(row) for row in mass_properties.inertia_kg_m2] == yaml_level["inertia_kg_m2"]
    com_heights = {lp.superstructure.mass_properties.com_m[2] for lp in loaded.values()}
    hashes = {lp.sha256 for lp in loaded.values()}
    assert len(com_heights) == 3
    assert len(hashes) == 3


def test_unknown_level_raises(params_path: Path) -> None:
    with pytest.raises(ParamsError, match="level"):
        load_params(params_path, level="ceiling")


# --- overrides ---------------------------------------------------------------------------


def test_override_changes_value_and_hash_but_not_the_file(
    params_path: Path, params: Params
) -> None:
    bytes_before = params_path.read_bytes()
    overridden = load_params(params_path, overrides={"actuator.oil_bulk_modulus_eff_Pa": 1.6e9})
    assert overridden.get("actuator.oil_bulk_modulus_eff_Pa") == 1.6e9
    assert params.get("actuator.oil_bulk_modulus_eff_Pa") == 1.0e9
    assert overridden.sha256 != params.sha256
    assert overridden.file_sha256 == params.file_sha256
    assert params_path.read_bytes() == bytes_before


def test_override_reaches_typed_fields_and_is_coerced(params_path: Path) -> None:
    overridden = load_params(params_path, overrides={"simulation.L1.dt_s": "1e-4"})
    assert overridden.simulation.L1.dt_s == 1e-4
    assert overridden.overrides == {"simulation.L1.dt_s": "1e-4"}


@pytest.mark.parametrize(
    "dotted_path", ["actuator.no_such_key", "hydraulic.beta_eff_Pa", "actuator.stroke_m.inner"]
)
def test_override_of_unknown_key_raises(params_path: Path, dotted_path: str) -> None:
    with pytest.raises(ParamsError, match="override"):
        load_params(params_path, overrides={dotted_path: 1.0})


# --- fingerprint -------------------------------------------------------------------------


def test_hash_is_deterministic(params_path: Path, params: Params) -> None:
    again = load_params(params_path)
    assert again.sha256 == params.sha256
    assert again.file_sha256 == params.file_sha256
    assert len(params.sha256) == 64


def test_hash_ignores_key_order(tmp_path: Path, yaml_tree: dict, params: Params) -> None:
    reordered = _dump_tree(tmp_path, yaml_tree, sort_keys=True)
    assert load_params(reordered).sha256 == params.sha256


def test_raw_mapping_is_read_only(params: Params) -> None:
    with pytest.raises(TypeError):
        params.raw["meta"]["gravity_m_s2"] = 0.0  # type: ignore[index]


# --- property checks (hypothesis) --------------------------------------------------------
# database=None: no .hypothesis/ example database is left in the project.

FINITE_FLOATS = st.floats(allow_nan=False, allow_infinity=False)
# A fixed alphabet (incl. Hangul for ensure_ascii=False) avoids building the full Unicode
# charmap, which alone takes about 1 s on the first run.
KEY_ALPHABET = "abcxyz_.FLRR가나"


@settings(max_examples=15, deadline=None, database=None)
@given(value=FINITE_FLOATS, spelling=st.sampled_from(["{!r}", "{:e}", "{:.17g}", "{:E}"]))
def test_numeric_string_override_loads_as_the_same_float(
    params_path: Path, value: float, spelling: str
) -> None:
    text = spelling.format(value)
    overridden = load_params(params_path, overrides={"simulation.L1.dt_s": text})
    assert overridden.simulation.L1.dt_s == float(text)
    assert type(overridden.get("simulation.L1.dt_s")) is float
    assert overridden.numeric_string_paths() == []


@settings(max_examples=25, deadline=None, database=None)
@given(
    tree=st.dictionaries(st.text(KEY_ALPHABET, min_size=1, max_size=8), FINITE_FLOATS, max_size=12)
)
def test_fingerprint_ignores_insertion_order(tree: dict[str, float]) -> None:
    reversed_tree = dict(reversed(list(tree.items())))
    for level in AugerLevel:
        assert parameters_sha256(tree, level) == parameters_sha256(reversed_tree, level)
    assert parameters_sha256(tree, AugerLevel.TOP) != parameters_sha256(tree, AugerLevel.BOTTOM)
