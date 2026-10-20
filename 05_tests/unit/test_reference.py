"""Unit tests for the reference-value keys (00_docs/03_chrono/chrono_build_plan.md R12)."""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

import pytest

from outrigger_sim.params import LEG_ORDER, AugerLevel
from outrigger_sim.verify import reference
from outrigger_sim.verify.reference import (
    ALL_KEYS,
    DEFAULT_FILE_PATHS,
    KEYS_BY_STAGE,
    L1_CONTACT_FORCE_N,
    LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D,
    LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D_KN_X3,
    LIFT_V4_DYNAMIC_TOUCH_S_RIGID_LIMIT,
    LIFT_V4_JUDGEMENT_BASIS,
    LIFT_V4_QUASI_STATIC_TOUCH_S_LAYOUT_D,
    LIFT_V4_QUASI_STATIC_TOUCH_S_LAYOUT_D_KN_X3,
    LIFT_V4_QUASI_STATIC_TOUCH_S_RIGID_LIMIT,
    LIFT_V4_RESIDUAL_AFTER_LAST_STOP,
    SLOPE_V12_L1,
    STICK_BUSHING_30DEG_MUST_SLIDE,
    TOTAL_WEIGHT_INCL_RODS_N,
    NamedItem,
    ReferenceFile,
    ReferenceKeyError,
    References,
    ReferenceValueError,
    RefKey,
    ValueKind,
    load_reference_file,
    load_references,
)

PLAN_RELATIVE_PATH = Path("00_docs/03_chrono/chrono_build_plan.md")

# Plan notation in backticks: `<file>.json / key / key ...`.
PLAN_NOTATION_PATTERN = re.compile(r"`([A-Za-z0-9_]+\.json / [^`]+)`")
# Plan S3 table: "L1 머리 + `key`" means the L1 per-level head with level top.
PLAN_L1_HEAD_ITEM_PATTERN = re.compile(r"L1 머리 \+ `([^`]+)`")
PLAN_L1_HEAD = (
    "reference.json / chrono_test_references / L1_rigid_motor_lumped_contact / levels / top"
)
PLAN_NAMED_ITEM_PATTERN = re.compile(r'name = "(.*)"')
# Notations that are not one key: a path head ending in " /" and a generic "<항목>" slot.
PLAN_GENERIC_SLOT = "<항목>"
# Run summaries the plan cites with the same notation (e.g. `verify_S2a_L1.json / ...`) are
# results, not reference values, so R12 does not ask for a constant.
PLAN_RUN_SUMMARY_FILE_PATTERN = re.compile(r"verify_[A-Za-z0-9_]+\.json")


def _concrete_keys() -> list[RefKey]:
    return [concrete for key in ALL_KEYS for concrete in key.expand()]


def _parse_plan_notation(notation: str) -> RefKey:
    file_name, *parts = notation.split(" / ")
    path: list[str | NamedItem] = []
    for part in parts:
        named = PLAN_NAMED_ITEM_PATTERN.fullmatch(part)
        path.append(NamedItem(named.group(1)) if named else part)
    return RefKey(ReferenceFile(file_name), tuple(path), ValueKind.MAPPING)


def _plan_notations(plan_text: str) -> set[str]:
    """Full-string key notations written in the plan, markdown table escapes removed."""
    found = set()
    for raw in PLAN_NOTATION_PATTERN.findall(plan_text):
        notation = raw.replace("\\|", "|").strip()
        if notation.endswith("/") or PLAN_GENERIC_SLOT in notation:
            continue
        file_name = notation.split(" / ", 1)[0]
        if PLAN_RUN_SUMMARY_FILE_PATTERN.fullmatch(file_name):
            continue
        found.add(notation)
    for item in PLAN_L1_HEAD_ITEM_PATTERN.findall(plan_text):
        found.add(f"{PLAN_L1_HEAD} / {item}")
    return found


@pytest.fixture(scope="module")
def refs() -> References:
    return load_references()


@pytest.fixture(scope="module")
def plan_keys(project_root: Path) -> list[RefKey]:
    plan_text = (project_root / PLAN_RELATIVE_PATH).read_text(encoding="utf-8")
    keys = [_parse_plan_notation(notation) for notation in sorted(_plan_notations(plan_text))]
    return [concrete for key in keys for concrete in key.expand()]


# --- R12: every constant exists in its file ------------------------------------------------


@pytest.mark.parametrize("key", _concrete_keys(), ids=lambda key: key.notation())
def test_every_constant_key_exists_with_its_kind(refs: References, key: RefKey) -> None:
    refs.get(key)  # raises on a missing key or a value of the wrong kind


def test_all_keys_lists_every_module_constant() -> None:
    module_constants = [value for value in vars(reference).values() if isinstance(value, RefKey)]
    assert set(module_constants) == set(ALL_KEYS)
    assert len(module_constants) == len(ALL_KEYS), "two constants share one path"


def test_every_stage_group_holds_only_known_keys() -> None:
    for stage, keys in KEYS_BY_STAGE.items():
        assert keys, stage
        assert set(keys) <= set(ALL_KEYS), stage


def test_plan_paths_are_covered_by_constants(plan_keys: list[RefKey]) -> None:
    # Guards the parser: the plan cites far more than this; zero would hide everything.
    assert len(plan_keys) > 30
    missing = sorted(key.notation() for key in set(plan_keys) - set(_concrete_keys()))
    assert missing == []


def test_constant_notation_matches_plan_spelling() -> None:
    assert STICK_BUSHING_30DEG_MUST_SLIDE.notation() == (
        'stick_friction.json / cases / name = "Bushing 30deg (tan>mu, must slide)"'
    )
    assert TOTAL_WEIGHT_INCL_RODS_N.notation() == (
        "reference.json / statics / total_weight_incl_rods_N"
    )
    assert "max |dev| over one 1st-rocking period" in LIFT_V4_RESIDUAL_AFTER_LAST_STOP.notation()


# --- values ----------------------------------------------------------------------------------


LIFT_V4_DYNAMIC_TOUCH_KEYS = (
    LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D,
    LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D_KN_X3,
    LIFT_V4_DYNAMIC_TOUCH_S_RIGID_LIMIT,
)
LIFT_V4_QUASI_STATIC_TOUCH_KEYS = (
    LIFT_V4_QUASI_STATIC_TOUCH_S_LAYOUT_D,
    LIFT_V4_QUASI_STATIC_TOUCH_S_LAYOUT_D_KN_X3,
    LIFT_V4_QUASI_STATIC_TOUCH_S_RIGID_LIMIT,
)


@pytest.mark.parametrize(
    "touch_key",
    [*LIFT_V4_DYNAMIC_TOUCH_KEYS, *LIFT_V4_QUASI_STATIC_TOUCH_KEYS],
    ids=lambda key: f"{key.path[2]} / {key.path[3]}",
)
def test_lift_v4_touch_times_are_one_float_per_leg(refs: References, touch_key: RefKey) -> None:
    touch_s = refs.get(touch_key)
    assert len(touch_s) == len(LEG_ORDER)
    assert all(isinstance(value, float) for value in touch_s)


def test_v4_judgement_basis_names_the_dynamic_touch_path(refs: References) -> None:
    basis = refs.get(LIFT_V4_JUDGEMENT_BASIS)
    dynamic_touch_path = "/".join(str(part) for part in LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D.path[-2:])
    assert dynamic_touch_path in basis


def test_v4_judgement_uses_dynamic_touch_in_s3_and_s7() -> None:
    assert {LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D, LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D_KN_X3} <= set(
        KEYS_BY_STAGE["S3"]
    )
    assert LIFT_V4_DYNAMIC_TOUCH_S_RIGID_LIMIT in KEYS_BY_STAGE["S7"]


LEG_EXTENSION_PER_LEG_ARRAY_KEYS = (
    reference.LEG_EXTENSION_MAX_PAD_REACTION_PER_LEG_N,
    reference.LEG_EXTENSION_KN_X3_MAX_PAD_REACTION_PER_LEG_N,
    reference.LEG_EXTENSION_KN_X3_DAMPED_FIRST_TOUCH_S,
    reference.LEG_EXTENSION_KN_X3_DAMPED_PEAK_PAD_FORCE_N,
)
LEG_EXTENSION_TOUCH_KEYS_BY_LEG = {
    "nominal": (
        reference.LEG_EXTENSION_TOUCH_FL_S,
        reference.LEG_EXTENSION_TOUCH_FR_S,
        reference.LEG_EXTENSION_TOUCH_RL_S,
        reference.LEG_EXTENSION_TOUCH_RR_S,
    ),
    "kn_x3": (
        reference.LEG_EXTENSION_KN_X3_TOUCH_FL_S,
        reference.LEG_EXTENSION_KN_X3_TOUCH_FR_S,
        reference.LEG_EXTENSION_KN_X3_TOUCH_RL_S,
        reference.LEG_EXTENSION_KN_X3_TOUCH_RR_S,
    ),
}


def _leg_extension_constants() -> list[RefKey]:
    return [
        value
        for name, value in vars(reference).items()
        if name.startswith("LEG_EXTENSION_") and isinstance(value, RefKey)
    ]


def test_leg_extension_constants_point_to_their_file_and_stage_s3() -> None:
    constants = _leg_extension_constants()
    assert constants
    assert all(key.file is ReferenceFile.LEG_EXTENSION_LOADS for key in constants)
    assert set(constants) <= set(KEYS_BY_STAGE["S3"])
    other_constants = set(ALL_KEYS) - set(constants)
    assert all(key.file is not ReferenceFile.LEG_EXTENSION_LOADS for key in other_constants)


@pytest.mark.parametrize(
    "per_leg_key", LEG_EXTENSION_PER_LEG_ARRAY_KEYS, ids=lambda key: str(key.path[-1])
)
def test_leg_extension_per_leg_arrays_are_one_float_per_leg(
    refs: References, per_leg_key: RefKey
) -> None:
    values = refs.get(per_leg_key)
    assert len(values) == len(LEG_ORDER)
    assert all(isinstance(value, float) for value in values)


@pytest.mark.parametrize("leg", LEG_ORDER)
def test_leg_extension_damped_peak_pad_force_resolves_per_leg(refs: References, leg: str) -> None:
    peak_pad_force_N = refs.get(reference.LEG_EXTENSION_DAMPED_PEAK_PAD_FORCE_N, leg=leg)
    assert isinstance(peak_pad_force_N, float)


def test_leg_placeholder_expands_to_the_leg_order() -> None:
    expanded = reference.LEG_EXTENSION_DAMPED_PEAK_PAD_FORCE_N.expand()
    assert [key.path[3] for key in expanded] == list(LEG_ORDER)


def test_unknown_leg_raises() -> None:
    with pytest.raises(ReferenceKeyError, match="<leg>"):
        reference.LEG_EXTENSION_DAMPED_PEAK_PAD_FORCE_N.resolve(leg="FX")


@pytest.mark.parametrize("variant", LEG_EXTENSION_TOUCH_KEYS_BY_LEG)
def test_leg_extension_touch_keys_follow_leg_order(refs: References, variant: str) -> None:
    touch_keys = LEG_EXTENSION_TOUCH_KEYS_BY_LEG[variant]
    assert [key.path[-1] for key in touch_keys] == [f"touch_{leg}" for leg in LEG_ORDER]
    assert all(isinstance(refs.get(key), float) for key in touch_keys)


def test_number_and_array_values(refs: References) -> None:
    total_weight_N = refs.get(TOTAL_WEIGHT_INCL_RODS_N)
    contact_force_N = refs.get(L1_CONTACT_FORCE_N, level="top")
    assert isinstance(total_weight_N, float)
    assert isinstance(contact_force_N, tuple)
    assert len(contact_force_N) == 4
    assert all(isinstance(value, float) for value in contact_force_N)


def test_values_are_read_only(refs: References) -> None:
    slope = refs.get(SLOPE_V12_L1, case="ground roll 0 deg, pitch 2 deg")
    with pytest.raises(TypeError):
        slope["cylinder_force_N"] = None  # type: ignore[index]
    assert isinstance(slope["contact_horizontal_xy_N"][0], tuple)


def test_level_enum_and_text_resolve_alike() -> None:
    assert L1_CONTACT_FORCE_N.resolve(level=AugerLevel.MIDDLE) == L1_CONTACT_FORCE_N.resolve(
        level="middle"
    )
    assert len(L1_CONTACT_FORCE_N.expand()) == len(AugerLevel)


def test_named_item_selects_by_name(refs: References) -> None:
    case = refs.get(STICK_BUSHING_30DEG_MUST_SLIDE)
    assert case["name"] == "Bushing 30deg (tan>mu, must slide)"


# --- errors ----------------------------------------------------------------------------------


def test_missing_key_names_the_path_and_close_matches(refs: References) -> None:
    typo = RefKey(ReferenceFile.REFERENCE, ("statics", "total_weight_incl_rods"), ValueKind.NUMBER)
    with pytest.raises(ReferenceKeyError) as caught:
        refs.get(typo)
    assert caught.value.notation == "reference.json / statics / total_weight_incl_rods"
    assert "total_weight_incl_rods_N" in str(caught.value)


def test_missing_named_item_raises(refs: References) -> None:
    absent = RefKey(
        ReferenceFile.STICK_FRICTION, ("cases", NamedItem("Bushing 3deg")), ValueKind.MAPPING
    )
    with pytest.raises(ReferenceKeyError, match="matches 0 items"):
        refs.get(absent)


def test_ambiguous_named_item_raises(tmp_path: Path) -> None:
    duplicated = tmp_path / "stick_friction.json"
    duplicated.write_text('{"cases": [{"name": "a"}, {"name": "a"}]}', encoding="utf-8")
    refs = load_references(
        {ReferenceFile.STICK_FRICTION: duplicated}, files=[ReferenceFile.STICK_FRICTION]
    )
    key = RefKey(ReferenceFile.STICK_FRICTION, ("cases", NamedItem("a")), ValueKind.MAPPING)
    with pytest.raises(ReferenceKeyError, match="matches 2 items"):
        refs.get(key)


def test_unresolved_placeholder_raises(refs: References) -> None:
    with pytest.raises(ReferenceKeyError, match="unresolved placeholder"):
        refs.get(L1_CONTACT_FORCE_N)


def test_unknown_placeholder_value_raises() -> None:
    with pytest.raises(ReferenceKeyError, match="<level>"):
        L1_CONTACT_FORCE_N.resolve(level="highest")


def test_wrong_kind_raises(refs: References) -> None:
    mapping_as_number = RefKey(ReferenceFile.REFERENCE, ("statics",), ValueKind.NUMBER)
    with pytest.raises(ReferenceValueError, match="reference.json / statics"):
        refs.get(mapping_as_number)


def test_key_of_unloaded_file_raises() -> None:
    refs = load_references(files=[ReferenceFile.REFERENCE])
    with pytest.raises(ReferenceKeyError, match="not loaded"):
        refs.get(STICK_BUSHING_30DEG_MUST_SLIDE)


def test_non_object_file_raises(tmp_path: Path) -> None:
    not_object = tmp_path / "reference.json"
    not_object.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ReferenceValueError, match="JSON object"):
        load_reference_file(ReferenceFile.REFERENCE, not_object)


# --- fingerprint -----------------------------------------------------------------------------


def test_sha256_is_the_file_bytes_hash_and_deterministic() -> None:
    path = DEFAULT_FILE_PATHS[ReferenceFile.REFERENCE]
    first = load_reference_file(ReferenceFile.REFERENCE)
    second = load_reference_file(ReferenceFile.REFERENCE)
    assert first.sha256 == second.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_sha256_changes_with_file_content(tmp_path: Path) -> None:
    original = DEFAULT_FILE_PATHS[ReferenceFile.STICK_FRICTION]
    copy = tmp_path / original.name
    shutil.copyfile(original, copy)
    same = load_reference_file(ReferenceFile.STICK_FRICTION, copy)
    copy.write_bytes(original.read_bytes() + b"\n")
    changed = load_reference_file(ReferenceFile.STICK_FRICTION, copy)
    assert same.sha256 == load_reference_file(ReferenceFile.STICK_FRICTION).sha256
    assert changed.sha256 != same.sha256


def test_sha256_by_file_covers_loaded_files(refs: References) -> None:
    fingerprints = refs.sha256_by_file()
    assert set(fingerprints) == {file.value for file in ReferenceFile}
    assert all(len(digest) == 64 for digest in fingerprints.values())
