"""Reference values for the V checks, addressed by full-string key constants (R12).

``00_docs/03_chrono/chrono_build_plan.md`` R12: reference values are read at run time from
``reference.json`` and the other files the plan names, and every key is written as a
**full string constant** (brackets, spaces and punctuation included) guarded by a
key-existence test (``05_tests/unit/test_reference.py``). Nothing here abbreviates a key.

A key is a :class:`RefKey`: the file plus the JSON path. Its :meth:`RefKey.notation` is the
plan's spelling, ``reference.json / statics / total_weight_incl_rods_N``. Paths may contain
placeholders (:class:`Placeholder`, ``<level>``, ``<case>``, ``<beta>``, ``<leg>``) that are
filled in
with :meth:`RefKey.resolve` or the keyword arguments of :meth:`References.get`. A list item
picked by its ``name`` field (plan notation ``name = "Bushing 2deg"``) is a :class:`NamedItem`.

Values come back read-only (mappings as ``MappingProxyType``, lists as tuples). Each file is
fingerprinted with the SHA-256 of its bytes for the run meta (like ``Params.file_sha256``).

Engine independent: no pychrono import.
"""

from __future__ import annotations

import difflib
import hashlib
import itertools
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from outrigger_sim.params import LEG_ORDER, AugerLevel

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PATH_SEPARATOR = " / "


class ReferenceFile(StrEnum):
    """Reference files named by the plan; the value is the file name used in its notation."""

    REFERENCE = "reference.json"
    ACTUATOR_L2_FEASIBILITY = "actuator_L2_feasibility.json"
    STICK_FRICTION = "stick_friction.json"
    V7_DIAGNOSTIC = "v7_diagnostic.json"
    # Second baseline file next to reference.json (user decision 2026-10-20): lift loads.
    LEG_EXTENSION_LOADS = "leg_extension_loads.json"


DEFAULT_FILE_PATHS: Mapping[ReferenceFile, Path] = MappingProxyType(
    {
        ReferenceFile.REFERENCE: PROJECT_ROOT / "06_analysis/00_dynamics/reference.json",
        ReferenceFile.ACTUATOR_L2_FEASIBILITY: (
            PROJECT_ROOT / "06_analysis/00_dynamics/actuator_L2_feasibility.json"
        ),
        ReferenceFile.STICK_FRICTION: PROJECT_ROOT / "06_analysis/01_chrono/stick_friction.json",
        ReferenceFile.V7_DIAGNOSTIC: PROJECT_ROOT / "06_analysis/00_dynamics/v7_diagnostic.json",
        ReferenceFile.LEG_EXTENSION_LOADS: (
            PROJECT_ROOT / "06_analysis/00_dynamics/leg_extension_loads.json"
        ),
    }
)


class Placeholder(StrEnum):
    """Path parts the caller fills in; spelled as in the plan (``<level>``, ``<case>``)."""

    LEVEL = "<level>"
    SLOPE_CASE = "<case>"
    BETA = "<beta>"
    LEG = "<leg>"


# Plan S2a: the three V12 slope cases (keys of ``reference.json / slope_V12``).
SLOPE_V12_CASES: tuple[str, ...] = (
    "ground roll 0 deg, pitch 2 deg",
    "ground roll 2 deg, pitch 0 deg",
    "ground roll -2 deg, pitch 1.5 deg",
)

# Plan S4: the three oil bulk moduli of the beta sensitivity (keys of L1_beta_sensitivity_top).
L1_BETA_CASES: tuple[str, ...] = ("beta_6.9e+08", "beta_1.0e+09", "beta_1.6e+09")

PLACEHOLDER_VALUES: Mapping[Placeholder, tuple[str, ...]] = MappingProxyType(
    {
        Placeholder.LEVEL: tuple(level.value for level in AugerLevel),
        Placeholder.SLOPE_CASE: SLOPE_V12_CASES,
        Placeholder.BETA: L1_BETA_CASES,
        Placeholder.LEG: LEG_ORDER,
    }
)


class ValueKind(Enum):
    """Expected shape of a reference value; checked by :meth:`References.get`."""

    NUMBER = "number"
    NUMBER_ARRAY = "array of numbers (nested lists allowed)"
    TEXT = "text"
    TEXT_ARRAY = "array of text"
    MAPPING = "mapping"


@dataclass(frozen=True)
class NamedItem:
    """List element selected by its ``name`` field (plan notation ``name = "..."``)."""

    name: str

    def __str__(self) -> str:
        return f'name = "{self.name}"'


PathPart = str | NamedItem


class ReferenceKeyError(LookupError):
    """A reference key is missing, ambiguous, unresolved or its file is not loaded."""

    def __init__(self, notation: str, problem: str) -> None:
        super().__init__(f"{notation}: {problem}")
        self.notation = notation


class ReferenceValueError(ValueError):
    """A reference value does not have the :class:`ValueKind` its key declares."""

    def __init__(self, notation: str, problem: str) -> None:
        super().__init__(f"{notation}: {problem}")
        self.notation = notation


@dataclass(frozen=True)
class RefKey:
    """One reference value: file + JSON path, compared by file and path only."""

    file: ReferenceFile
    path: tuple[PathPart, ...]
    kind: ValueKind = field(compare=False)

    def notation(self) -> str:
        """Plan spelling, for example ``reference.json / statics / total_weight_incl_rods_N``."""
        return PATH_SEPARATOR.join([self.file.value, *(str(part) for part in self.path)])

    def placeholders(self) -> tuple[Placeholder, ...]:
        """Placeholders still in the path, in path order."""
        return tuple(Placeholder(part) for part in self.path if part in _PLACEHOLDER_TEXTS)

    def resolve(
        self,
        *,
        level: AugerLevel | str | None = None,
        case: str | None = None,
        beta: str | None = None,
        leg: str | None = None,
    ) -> RefKey:
        """Return the key with its placeholders filled in.

        Values for placeholders the path does not contain are ignored, so one set of
        arguments can resolve every key of a run. A placeholder left without a value stays
        in the path; :meth:`References.get` then raises :class:`ReferenceKeyError`.

        Raises:
            ReferenceKeyError: A value is not one of :data:`PLACEHOLDER_VALUES`.
        """
        given = {
            Placeholder.LEVEL: None if level is None else _level_text(level),
            Placeholder.SLOPE_CASE: case,
            Placeholder.BETA: beta,
            Placeholder.LEG: leg,
        }
        resolved_path: list[PathPart] = []
        for part in self.path:
            value = given.get(Placeholder(part)) if part in _PLACEHOLDER_TEXTS else None
            if value is None:
                resolved_path.append(part)
                continue
            if value not in PLACEHOLDER_VALUES[Placeholder(part)]:
                allowed = PLACEHOLDER_VALUES[Placeholder(part)]
                raise ReferenceKeyError(self.notation(), f"{part} = {value!r} not in {allowed}")
            resolved_path.append(value)
        return RefKey(self.file, tuple(resolved_path), self.kind)

    def expand(self) -> tuple[RefKey, ...]:
        """Every concrete key: the product of all values of the placeholders in the path."""
        choices = [
            PLACEHOLDER_VALUES[Placeholder(part)] if part in _PLACEHOLDER_TEXTS else (part,)
            for part in self.path
        ]
        return tuple(
            RefKey(self.file, tuple(path), self.kind) for path in itertools.product(*choices)
        )


_PLACEHOLDER_TEXTS = frozenset(member.value for member in Placeholder)


def _level_text(level: AugerLevel | str) -> str:
    return level.value if isinstance(level, AugerLevel) else level


# --- key builders --------------------------------------------------------------------------
# Common path heads, spelled once. Every constant below is still the full path.

_LEVEL = Placeholder.LEVEL.value
_CASE = Placeholder.SLOPE_CASE.value
_BETA = Placeholder.BETA.value
_L1_LEVEL_HEAD = ("chrono_test_references", "L1_rigid_motor_lumped_contact", "levels", _LEVEL)
_L2B_NSC_LEVEL_HEAD = (
    "chrono_test_references",
    "L2b_NSC_force_motor_axial_spring_lateral_bushing",
    "levels",
    _LEVEL,
)
_LIFT_V4 = ("lift_V4_compliant_crawler",)
_LIFT_V4_LAYOUT_D = (
    *_LIFT_V4,
    "layouts",
    "D rollers + gapped end shoes (YAML contact.crawler.sphere_layout)",
)
_LIFT_V4_LAYOUT_D_KN_X3 = (
    *_LIFT_V4,
    "layouts",
    "D kn_total x3 (sensitivity, YAML contact.crawler.kn_total_sensitivity_range_N_m)",
)
_LIFT_V4_LAYOUT_D_ROLLERS_ONLY = (
    *_LIFT_V4,
    "layouts",
    "sensitivity D without the end shoes (rollers only)",
)
_LIFT_V4_LAYOUT_D_RIGID_LIMIT = (
    *_LIFT_V4,
    "layouts",
    "D rigid crawler limit (kn_total x1e3, L2b-NSC V4)",
)
# V4 touch times (user decision 2026-10-20): the damped 3-DoF dynamic touch is the pass
# basis; the quasi-static touch is kept for reference only.
_TOUCH_DYN_S = ("dynamic_events_s", "touch_s (FL, FR, RL, RR)")
_TOUCH_QUASI_STATIC_S = ("quasi_static_events_s", "touch_s (FL, FR, RL, RR)")
_MODE_SHAPES = "mode_shapes_rev5"
_V14_REV5 = ("A_extension_dependence", "V14_rev5")
_V15_REV5 = ("C_seal_friction", "V15_rev5")


def _ref(kind: ValueKind, *path: PathPart) -> RefKey:
    return RefKey(ReferenceFile.REFERENCE, path, kind)


# leg_extension_loads.json heads; constants built from them start with LEG_EXTENSION_.
_LEG = Placeholder.LEG.value
_LEG_EXT_DAMPED_PER_LEG = (
    "validation",
    "quasi_static_check (damped 3-DoF)",
    "per_leg",
    _LEG,
)
_LEG_EXT_KEY_VALUES = ("key_values",)
_LEG_EXT_EVENTS = (*_LEG_EXT_KEY_VALUES, "events_s")
_LEG_EXT_KN_X3 = ("crawler_kn_total_x3_sensitivity",)
_LEG_EXT_KN_X3_EVENTS = (*_LEG_EXT_KN_X3, "events_full_stroke_s")
_LEG_EXT_KN_X3_DYNAMIC = (*_LEG_EXT_KN_X3, "dynamic (damped 3-DoF, 14.5-20 s)")


def _leg_extension(kind: ValueKind, *path: PathPart) -> RefKey:
    return RefKey(ReferenceFile.LEG_EXTENSION_LOADS, path, kind)


_NUMBER = ValueKind.NUMBER
_ARRAY = ValueKind.NUMBER_ARRAY
_TEXT = ValueKind.TEXT
_MAPPING = ValueKind.MAPPING

# --- S0: ground bushing regression (stick_friction.json) ------------------------------------

STICK_BUSHING_2DEG = RefKey(
    ReferenceFile.STICK_FRICTION, ("cases", NamedItem("Bushing 2deg")), _MAPPING
)
STICK_BUSHING_FLAT_V0 = RefKey(
    ReferenceFile.STICK_FRICTION, ("cases", NamedItem("Bushing flat v0")), _MAPPING
)
STICK_BUSHING_30DEG_MUST_SLIDE = RefKey(
    ReferenceFile.STICK_FRICTION,
    ("cases", NamedItem("Bushing 30deg (tan>mu, must slide)")),
    _MAPPING,
)

# --- S1: statics on a level floor (V1-V3); V1 and V10 also in S5 -----------------------------

L1_CONTACT_FORCE_N = _ref(_ARRAY, *_L1_LEVEL_HEAD, "contact_force_N")  # V1, V10
L1_CYLINDER_FORCE_N = _ref(_ARRAY, *_L1_LEVEL_HEAD, "cylinder_force_N")  # V1
TOTAL_WEIGHT_INCL_RODS_N = _ref(_NUMBER, "statics", "total_weight_incl_rods_N")  # V1
L1_STATIC_PENETRATION_MM = _ref(  # V2 (plan table: top), initial-condition rule (<level>)
    _ARRAY, *_L1_LEVEL_HEAD, "static_penetration_or_compression_mm"
)
L1_STATIC_ATTITUDE_DEG = _ref(  # V3 (plan table: top), initial-condition rule (<level>)
    _ARRAY, *_L1_LEVEL_HEAD, "static_attitude_deg (roll, pitch)"
)

# --- S2a: bushing dynamics (V7 diagnostic) and slope statics (V12) ---------------------------

L1_F_DAMPED_HZ = _ref(_ARRAY, *_L1_LEVEL_HEAD, "f_damped_Hz")  # V7 diagnostic (first 2), V10
SLOPE_V12_EXTENSION_M = _ref(_ARRAY, "slope_V12", _CASE, "extension_m")  # V12 input
SLOPE_V12_L1 = _ref(_MAPPING, "slope_V12", _CASE, "L1")  # V12
# The plan cites v7_diagnostic.json as a whole for the V7 diagnosis; these are the blocks
# holding the predicted zeta per damping-input error and the numerical damping per mode.
V7_DIAGNOSTIC_L1_CASES = RefKey(ReferenceFile.V7_DIAGNOSTIC, ("L1", _LEVEL, "cases"), _MAPPING)
V7_DIAGNOSTIC_L1_ZETA_NUM = RefKey(
    ReferenceFile.V7_DIAGNOSTIC, ("L1", _LEVEL, "zeta_num_dt1e-4"), _ARRAY
)

# --- S2b: crawler settling ---------------------------------------------------------------------

LIFT_V4_LAYOUTS = _ref(_MAPPING, *_LIFT_V4, "layouts")
LIFT_V4_LAYOUT_D = _ref(_MAPPING, *_LIFT_V4_LAYOUT_D)  # settled_on_crawler initial state
LIFT_V4_LAYOUT_D_KN_X3 = _ref(_MAPPING, *_LIFT_V4_LAYOUT_D_KN_X3)
LIFT_V4_LAYOUT_D_ROLLERS_ONLY = _ref(_MAPPING, *_LIFT_V4_LAYOUT_D_ROLLERS_ONLY)
LIFT_V4_LAYOUT_D_RIGID_LIMIT = _ref(_MAPPING, *_LIFT_V4_LAYOUT_D_RIGID_LIMIT)
LIFT_V4_CRAWLER_ON_FLOOR_MODES = _ref(
    _MAPPING, *_LIFT_V4, "crawler_on_floor_modes (layout D, legs at 0)"
)
LIFT_V4_CRAWLER_ON_FLOOR_MODES_KN_X3 = _ref(
    _MAPPING, *_LIFT_V4, "crawler_on_floor_modes (layout D kn_total x3, legs at 0)"
)
LIFT_V4_CRAWLER_CONTACT_LAYOUT_D = _ref(
    _MAPPING, *_LIFT_V4, "crawler_contact_assumptions", "layout_D"
)

# --- S3: numerical damping (V8a), lift (V4), single-leg extension (V5, V6) -------------------

L1_NUMERICAL_DAMPING_BOUND_S = _ref(  # V8(a)
    _NUMBER, "time_step", "L1_numerical_damping_bound_s (omega1 dt/2 <= 0.1 zeta1, top)"
)
L1_ZETA = _ref(_ARRAY, *_L1_LEVEL_HEAD, "zeta")  # V8(a) first mode, V7
LIFT_V4 = _ref(_MAPPING, *_LIFT_V4)  # V4 whole block
LIFT_V4_PROCEDURE = _ref(_TEXT, *_LIFT_V4, "procedure")  # V4
LIFT_V4_TIME_ORIGIN = _ref(_TEXT, *_LIFT_V4, "time_origin")  # V4
LIFT_V4_RESIDUAL_AFTER_LAST_STOP = _ref(  # V4 residual rocking < 0.001 deg
    _MAPPING,
    *_LIFT_V4,
    "residual_after_last_stop_linear_L1 (deg, max |dev| over one 1st-rocking period)",
)
# V4 pass criterion: each leg's touch time within +-0.05 s of the damped 3-DoF dynamic
# reference with the same layout and stiffness. The touch order is not judged (it flips
# with crawler stiffness).
LIFT_V4_JUDGEMENT_BASIS = _ref(_TEXT, *_LIFT_V4, "V4_judgement_basis")
LIFT_V4_DYNAMIC_TOUCH_DAMPING_SENSITIVITY = _ref(
    _MAPPING, *_LIFT_V4, "dynamic_touch_damping_sensitivity"
)
LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D = _ref(_ARRAY, *_LIFT_V4_LAYOUT_D, *_TOUCH_DYN_S)
LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D_KN_X3 = _ref(_ARRAY, *_LIFT_V4_LAYOUT_D_KN_X3, *_TOUCH_DYN_S)
# Reference only (quasi-static touch), not the V4 pass basis.
LIFT_V4_QUASI_STATIC_TOUCH_S_LAYOUT_D = _ref(_ARRAY, *_LIFT_V4_LAYOUT_D, *_TOUCH_QUASI_STATIC_S)
LIFT_V4_QUASI_STATIC_TOUCH_S_LAYOUT_D_KN_X3 = _ref(
    _ARRAY, *_LIFT_V4_LAYOUT_D_KN_X3, *_TOUCH_QUASI_STATIC_S
)
L1_DF_PER_MM_FL_N = _ref(_ARRAY, *_L1_LEVEL_HEAD, "dF_per_mm_FL_N")  # V5
L1_DROLL_DPITCH_PER_MM_FL_DEG = _ref(  # V5
    _ARRAY, *_L1_LEVEL_HEAD, "droll_dpitch_per_mm_FL_deg"
)
L1_F_MIN_THRESHOLD_SINGLE_LEG = _ref(  # V6
    _MAPPING, *_L1_LEVEL_HEAD, "F_min_threshold_single_leg (cylinder force = F_min)"
)
L1_LIFTOFF_THRESHOLD_SINGLE_LEG = _ref(  # V6
    _MAPPING, *_L1_LEVEL_HEAD, "liftoff_threshold_single_leg (contact force 0)"
)

# --- S3: lift loads, second baseline file (leg_extension_loads.json) -------------------------
# Open-loop lift on all four legs, auger top, nominal crawler kn. Tolerances are not decided
# yet (user, 2026-10-20); these constants only fix the key paths and value kinds.

# Damped 3-DoF check: peak pad force per leg (<leg> = FL, FR, RL, RR).
LEG_EXTENSION_DAMPED_PEAK_PAD_FORCE_N = _leg_extension(
    _NUMBER, *_LEG_EXT_DAMPED_PER_LEG, "peak_pad_force_N"
)
# Quasi-static maximum pad reaction: over all legs, and per leg (FL, FR, RL, RR).
LEG_EXTENSION_MAX_PAD_REACTION_N = _leg_extension(
    _NUMBER, *_LEG_EXT_KEY_VALUES, "max_pad_reaction_N"
)
LEG_EXTENSION_MAX_PAD_REACTION_PER_LEG_N = _leg_extension(
    _ARRAY, *_LEG_EXT_KEY_VALUES, "max_over_time_per_leg_N"
)
# Quasi-static events: per-leg touch and the crawler leaving the floor (time origin: motor start).
LEG_EXTENSION_EVENTS_S = _leg_extension(_MAPPING, *_LEG_EXT_EVENTS)
LEG_EXTENSION_TOUCH_FL_S = _leg_extension(_NUMBER, *_LEG_EXT_EVENTS, "touch_FL")
LEG_EXTENSION_TOUCH_FR_S = _leg_extension(_NUMBER, *_LEG_EXT_EVENTS, "touch_FR")
LEG_EXTENSION_TOUCH_RL_S = _leg_extension(_NUMBER, *_LEG_EXT_EVENTS, "touch_RL")
LEG_EXTENSION_TOUCH_RR_S = _leg_extension(_NUMBER, *_LEG_EXT_EVENTS, "touch_RR")
LEG_EXTENSION_CRAWLER_OFF_S = _leg_extension(_NUMBER, *_LEG_EXT_EVENTS, "crawler_off")

# Crawler kn_total x3 sensitivity: the same quantities with the stiffer crawler.
LEG_EXTENSION_KN_X3 = _leg_extension(_MAPPING, *_LEG_EXT_KN_X3)
LEG_EXTENSION_KN_X3_EVENTS_S = _leg_extension(_MAPPING, *_LEG_EXT_KN_X3_EVENTS)
LEG_EXTENSION_KN_X3_TOUCH_FL_S = _leg_extension(_NUMBER, *_LEG_EXT_KN_X3_EVENTS, "touch_FL")
LEG_EXTENSION_KN_X3_TOUCH_FR_S = _leg_extension(_NUMBER, *_LEG_EXT_KN_X3_EVENTS, "touch_FR")
LEG_EXTENSION_KN_X3_TOUCH_RL_S = _leg_extension(_NUMBER, *_LEG_EXT_KN_X3_EVENTS, "touch_RL")
LEG_EXTENSION_KN_X3_TOUCH_RR_S = _leg_extension(_NUMBER, *_LEG_EXT_KN_X3_EVENTS, "touch_RR")
LEG_EXTENSION_KN_X3_CRAWLER_OFF_S = _leg_extension(_NUMBER, *_LEG_EXT_KN_X3_EVENTS, "crawler_off")
LEG_EXTENSION_KN_X3_MAX_PAD_REACTION_N = _leg_extension(
    _NUMBER, *_LEG_EXT_KN_X3, "quasi_static_max_pad_reaction_N"
)
LEG_EXTENSION_KN_X3_MAX_PAD_REACTION_PER_LEG_N = _leg_extension(
    _ARRAY, *_LEG_EXT_KN_X3, "quasi_static_max_over_time_per_leg_N"
)
LEG_EXTENSION_KN_X3_DAMPED_FIRST_TOUCH_S = _leg_extension(
    _ARRAY, *_LEG_EXT_KN_X3_DYNAMIC, "first_touch_dyn_s (FL, FR, RL, RR)"
)
LEG_EXTENSION_KN_X3_DAMPED_PEAK_PAD_FORCE_N = _leg_extension(
    _ARRAY, *_LEG_EXT_KN_X3_DYNAMIC, "peak_pad_force_N (FL, FR, RL, RR)"
)
LEG_EXTENSION_KN_X3_DAMPED_MAX_PEAK_PAD_FORCE_N = _leg_extension(
    _NUMBER, *_LEG_EXT_KN_X3_DYNAMIC, "max_peak_pad_force_N"
)

# --- S4: six-mode identification by modal projection (V7) and beta sensitivity --------------

L1_F_UNDAMPED_HZ = _ref(_ARRAY, *_L1_LEVEL_HEAD, "f_undamped_Hz")  # V7
L1_MODE_SHAPES = _ref(_MAPPING, *_L1_LEVEL_HEAD, _MODE_SHAPES)  # V7 projection block
L1_MODE_PHI = _ref(
    _ARRAY,
    *_L1_LEVEL_HEAD,
    _MODE_SHAPES,
    "Phi (rows = coordinates, cols = modes in f_undamped_Hz order, first 6)",
)
L1_MODE_MASS_MATRIX = _ref(_ARRAY, *_L1_LEVEL_HEAD, _MODE_SHAPES, "mass_matrix (same coordinates)")
L1_MODE_REFERENCE_POINT_M = _ref(
    _ARRAY,
    *_L1_LEVEL_HEAD,
    _MODE_SHAPES,
    "reference_point_m (rotations about it, translations of it; body axes, level body = world)",
)
L1_MODE_COORDINATES = _ref(ValueKind.TEXT_ARRAY, *_L1_LEVEL_HEAD, _MODE_SHAPES, "coordinates")
L1_MODE_PROJECTION = _ref(_TEXT, *_L1_LEVEL_HEAD, _MODE_SHAPES, "projection")
BETA_K_L1_N_M = _ref(_ARRAY, "L1_beta_sensitivity_top", _BETA, "k_L1_N_m")  # override input
BETA_PENETRATION_MM = _ref(_ARRAY, "L1_beta_sensitivity_top", _BETA, "penetration_mm")
BETA_STATIC_PITCH_DEG = _ref(_NUMBER, "L1_beta_sensitivity_top", _BETA, "static_pitch_deg")
BETA_DF_PER_MM_FL_N = _ref(_ARRAY, "L1_beta_sensitivity_top", _BETA, "dF_per_mm_FL_N")
BETA_FL_PLUS_F_MIN_MM = _ref(_NUMBER, "L1_beta_sensitivity_top", _BETA, "FL+_F_min_mm")
BETA_FL_PLUS_LIFTOFF_MM = _ref(_NUMBER, "L1_beta_sensitivity_top", _BETA, "FL+_liftoff_mm")
BETA_F_HZ_TOP = _ref(_ARRAY, "L1_beta_sensitivity_top", _BETA, "f_Hz_top")

# --- S6: force saturation (V11b) and locked pressure (V17 path) ------------------------------

HYDRAULIC_MAX_HEAD_FORCE_N = _ref(_NUMBER, "hydraulic_circuit", "max_head_force_N")
HYDRAULIC_MAX_ROD_SIDE_FORCE_N = _ref(_NUMBER, "hydraulic_circuit", "max_rod_side_force_N")
HYDRAULIC_MAX_STATIC_HEAD_PRESSURE_PA = _ref(
    _NUMBER, "hydraulic_circuit", "max_static_head_pressure_Pa"
)

# --- S7: L2b-NSC (V0-V13 like L1, V4 NSC, V12, V14) ------------------------------------------
# f_undamped_Hz, f_damped_Hz, zeta and the mode-shape arrays have 10 entries here; the plan
# uses only the first 6 (superstructure modes).

L2B_NSC_CONTACT_FORCE_N = _ref(_ARRAY, *_L2B_NSC_LEVEL_HEAD, "contact_force_N")
L2B_NSC_CYLINDER_FORCE_N = _ref(_ARRAY, *_L2B_NSC_LEVEL_HEAD, "cylinder_force_N")
L2B_NSC_STATIC_PENETRATION_MM = _ref(  # V2 = axial spring compression
    _ARRAY, *_L2B_NSC_LEVEL_HEAD, "static_penetration_or_compression_mm"
)
L2B_NSC_STATIC_ATTITUDE_DEG = _ref(
    _ARRAY, *_L2B_NSC_LEVEL_HEAD, "static_attitude_deg (roll, pitch)"
)
L2B_NSC_DF_PER_MM_FL_N = _ref(_ARRAY, *_L2B_NSC_LEVEL_HEAD, "dF_per_mm_FL_N")
L2B_NSC_DROLL_DPITCH_PER_MM_FL_DEG = _ref(
    _ARRAY, *_L2B_NSC_LEVEL_HEAD, "droll_dpitch_per_mm_FL_deg"
)
L2B_NSC_F_MIN_THRESHOLD_SINGLE_LEG = _ref(
    _MAPPING, *_L2B_NSC_LEVEL_HEAD, "F_min_threshold_single_leg (cylinder force = F_min)"
)
L2B_NSC_LIFTOFF_THRESHOLD_SINGLE_LEG = _ref(
    _MAPPING, *_L2B_NSC_LEVEL_HEAD, "liftoff_threshold_single_leg (contact force 0)"
)
L2B_NSC_F_UNDAMPED_HZ = _ref(_ARRAY, *_L2B_NSC_LEVEL_HEAD, "f_undamped_Hz")
L2B_NSC_F_DAMPED_HZ = _ref(_ARRAY, *_L2B_NSC_LEVEL_HEAD, "f_damped_Hz")
L2B_NSC_ZETA = _ref(_ARRAY, *_L2B_NSC_LEVEL_HEAD, "zeta")
L2B_NSC_MODE_SHAPES = _ref(_MAPPING, *_L2B_NSC_LEVEL_HEAD, _MODE_SHAPES)
L2B_NSC_MODE_PHI = _ref(
    _ARRAY,
    *_L2B_NSC_LEVEL_HEAD,
    _MODE_SHAPES,
    "Phi (rows = coordinates, cols = modes in f_undamped_Hz order, first 6)",
)
L2B_NSC_MODE_MASS_MATRIX = _ref(
    _ARRAY, *_L2B_NSC_LEVEL_HEAD, _MODE_SHAPES, "mass_matrix (same coordinates)"
)
L2B_NSC_MODE_REFERENCE_POINT_M = _ref(
    _ARRAY,
    *_L2B_NSC_LEVEL_HEAD,
    _MODE_SHAPES,
    "reference_point_m (rotations about it, translations of it; body axes, level body = world)",
)
L2B_NSC_MODE_COORDINATES = _ref(
    ValueKind.TEXT_ARRAY, *_L2B_NSC_LEVEL_HEAD, _MODE_SHAPES, "coordinates"
)
SLOPE_V12_L2B_NSC = _ref(_MAPPING, "slope_V12", _CASE, "L2b_NSC")  # V12
# V4(NSC): the NSC crawler does not sink, so its reference is the rigid crawler limit.
LIFT_V4_DYNAMIC_TOUCH_S_RIGID_LIMIT = _ref(_ARRAY, *_LIFT_V4_LAYOUT_D_RIGID_LIMIT, *_TOUCH_DYN_S)
# Reference only (quasi-static touch), not the V4(NSC) pass basis.
LIFT_V4_QUASI_STATIC_TOUCH_S_RIGID_LIMIT = _ref(
    _ARRAY, *_LIFT_V4_LAYOUT_D_RIGID_LIMIT, *_TOUCH_QUASI_STATIC_S
)
V14_REV5 = RefKey(ReferenceFile.ACTUATOR_L2_FEASIBILITY, _V14_REV5, _MAPPING)
V14_REV5_METHOD = RefKey(ReferenceFile.ACTUATOR_L2_FEASIBILITY, (*_V14_REV5, "method"), _TEXT)
V14_REV5_TEST_LEG = RefKey(
    ReferenceFile.ACTUATOR_L2_FEASIBILITY, (*_V14_REV5, "V14_test_leg"), _TEXT
)
V14_REV5_CASES = RefKey(ReferenceFile.ACTUATOR_L2_FEASIBILITY, (*_V14_REV5, "cases"), _MAPPING)

# --- S8: seal friction (V15) -------------------------------------------------------------------

V15_REV5_UPSWEEP_UNILATERAL = RefKey(
    ReferenceFile.ACTUATOR_L2_FEASIBILITY, (*_V15_REV5, "a_upsweep_unilateral"), _MAPPING
)
V15_REV5_ROUNDTRIP_10MM = RefKey(
    ReferenceFile.ACTUATOR_L2_FEASIBILITY, (*_V15_REV5, "b_roundtrip_10mm"), _MAPPING
)

# --- keys per stage (plan section 2 tables; a key is listed in every stage that uses it) ----

KEYS_BY_STAGE: Mapping[str, tuple[RefKey, ...]] = MappingProxyType(
    {
        "S0": (STICK_BUSHING_2DEG, STICK_BUSHING_FLAT_V0, STICK_BUSHING_30DEG_MUST_SLIDE),
        "S1": (
            L1_CONTACT_FORCE_N,
            L1_CYLINDER_FORCE_N,
            TOTAL_WEIGHT_INCL_RODS_N,
            L1_STATIC_PENETRATION_MM,
            L1_STATIC_ATTITUDE_DEG,
        ),
        "S2a": (
            L1_F_DAMPED_HZ,
            SLOPE_V12_EXTENSION_M,
            SLOPE_V12_L1,
            V7_DIAGNOSTIC_L1_CASES,
            V7_DIAGNOSTIC_L1_ZETA_NUM,
        ),
        "S2b": (
            LIFT_V4_LAYOUTS,
            LIFT_V4_LAYOUT_D,
            LIFT_V4_LAYOUT_D_KN_X3,
            LIFT_V4_LAYOUT_D_ROLLERS_ONLY,
            LIFT_V4_CRAWLER_ON_FLOOR_MODES,
            LIFT_V4_CRAWLER_ON_FLOOR_MODES_KN_X3,
            LIFT_V4_CRAWLER_CONTACT_LAYOUT_D,
        ),
        "S3": (
            L1_NUMERICAL_DAMPING_BOUND_S,
            L1_ZETA,
            LIFT_V4,
            LIFT_V4_PROCEDURE,
            LIFT_V4_TIME_ORIGIN,
            LIFT_V4_LAYOUTS,
            LIFT_V4_RESIDUAL_AFTER_LAST_STOP,
            LIFT_V4_LAYOUT_D,
            LIFT_V4_JUDGEMENT_BASIS,
            LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D,
            LIFT_V4_DYNAMIC_TOUCH_S_LAYOUT_D_KN_X3,
            LIFT_V4_DYNAMIC_TOUCH_DAMPING_SENSITIVITY,
            LIFT_V4_QUASI_STATIC_TOUCH_S_LAYOUT_D,
            LIFT_V4_QUASI_STATIC_TOUCH_S_LAYOUT_D_KN_X3,
            L1_CONTACT_FORCE_N,
            L1_STATIC_ATTITUDE_DEG,
            L1_DF_PER_MM_FL_N,
            L1_DROLL_DPITCH_PER_MM_FL_DEG,
            L1_F_MIN_THRESHOLD_SINGLE_LEG,
            L1_LIFTOFF_THRESHOLD_SINGLE_LEG,
            LEG_EXTENSION_DAMPED_PEAK_PAD_FORCE_N,
            LEG_EXTENSION_MAX_PAD_REACTION_N,
            LEG_EXTENSION_MAX_PAD_REACTION_PER_LEG_N,
            LEG_EXTENSION_EVENTS_S,
            LEG_EXTENSION_TOUCH_FL_S,
            LEG_EXTENSION_TOUCH_FR_S,
            LEG_EXTENSION_TOUCH_RL_S,
            LEG_EXTENSION_TOUCH_RR_S,
            LEG_EXTENSION_CRAWLER_OFF_S,
            LEG_EXTENSION_KN_X3,
            LEG_EXTENSION_KN_X3_EVENTS_S,
            LEG_EXTENSION_KN_X3_TOUCH_FL_S,
            LEG_EXTENSION_KN_X3_TOUCH_FR_S,
            LEG_EXTENSION_KN_X3_TOUCH_RL_S,
            LEG_EXTENSION_KN_X3_TOUCH_RR_S,
            LEG_EXTENSION_KN_X3_CRAWLER_OFF_S,
            LEG_EXTENSION_KN_X3_MAX_PAD_REACTION_N,
            LEG_EXTENSION_KN_X3_MAX_PAD_REACTION_PER_LEG_N,
            LEG_EXTENSION_KN_X3_DAMPED_FIRST_TOUCH_S,
            LEG_EXTENSION_KN_X3_DAMPED_PEAK_PAD_FORCE_N,
            LEG_EXTENSION_KN_X3_DAMPED_MAX_PEAK_PAD_FORCE_N,
        ),
        "S4": (
            L1_F_UNDAMPED_HZ,
            L1_F_DAMPED_HZ,
            L1_ZETA,
            L1_MODE_SHAPES,
            L1_MODE_PHI,
            L1_MODE_MASS_MATRIX,
            L1_MODE_REFERENCE_POINT_M,
            L1_MODE_COORDINATES,
            L1_MODE_PROJECTION,
            BETA_K_L1_N_M,
            BETA_PENETRATION_MM,
            BETA_STATIC_PITCH_DEG,
            BETA_DF_PER_MM_FL_N,
            BETA_FL_PLUS_F_MIN_MM,
            BETA_FL_PLUS_LIFTOFF_MM,
            BETA_F_HZ_TOP,
        ),
        "S5": (L1_CONTACT_FORCE_N, L1_F_DAMPED_HZ),
        "S6": (
            HYDRAULIC_MAX_HEAD_FORCE_N,
            HYDRAULIC_MAX_ROD_SIDE_FORCE_N,
            HYDRAULIC_MAX_STATIC_HEAD_PRESSURE_PA,
        ),
        "S7": (
            L2B_NSC_CONTACT_FORCE_N,
            L2B_NSC_CYLINDER_FORCE_N,
            L2B_NSC_STATIC_PENETRATION_MM,
            L2B_NSC_STATIC_ATTITUDE_DEG,
            L2B_NSC_DF_PER_MM_FL_N,
            L2B_NSC_DROLL_DPITCH_PER_MM_FL_DEG,
            L2B_NSC_F_MIN_THRESHOLD_SINGLE_LEG,
            L2B_NSC_LIFTOFF_THRESHOLD_SINGLE_LEG,
            L2B_NSC_F_UNDAMPED_HZ,
            L2B_NSC_F_DAMPED_HZ,
            L2B_NSC_ZETA,
            L2B_NSC_MODE_SHAPES,
            L2B_NSC_MODE_PHI,
            L2B_NSC_MODE_MASS_MATRIX,
            L2B_NSC_MODE_REFERENCE_POINT_M,
            L2B_NSC_MODE_COORDINATES,
            SLOPE_V12_L2B_NSC,
            LIFT_V4_LAYOUT_D_RIGID_LIMIT,
            LIFT_V4_DYNAMIC_TOUCH_S_RIGID_LIMIT,
            LIFT_V4_QUASI_STATIC_TOUCH_S_RIGID_LIMIT,
            TOTAL_WEIGHT_INCL_RODS_N,
            V14_REV5,
            V14_REV5_METHOD,
            V14_REV5_TEST_LEG,
            V14_REV5_CASES,
        ),
        "S8": (V15_REV5_UPSWEEP_UNILATERAL, V15_REV5_ROUNDTRIP_10MM),
    }
)


def _unique_keys(groups: Iterable[tuple[RefKey, ...]]) -> tuple[RefKey, ...]:
    return tuple(dict.fromkeys(key for group in groups for key in group))


ALL_KEYS: tuple[RefKey, ...] = _unique_keys(KEYS_BY_STAGE.values())
"""Every key constant once, in first-use stage order."""


# --- value access ----------------------------------------------------------------------------


def _freeze(node: Any) -> Any:
    if isinstance(node, dict):
        return MappingProxyType({key: _freeze(value) for key, value in node.items()})
    if isinstance(node, list):
        return tuple(_freeze(item) for item in node)
    return node


def _is_number(value: Any) -> bool:
    # bool is a subclass of int; a JSON true/false is not a reference number.
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_number_array(value: Any) -> bool:
    if not isinstance(value, tuple) or not value:
        return False
    return all(_is_number(item) or _is_number_array(item) for item in value)


def _matches_kind(value: Any, kind: ValueKind) -> bool:
    if kind is ValueKind.NUMBER:
        return _is_number(value)
    if kind is ValueKind.NUMBER_ARRAY:
        return _is_number_array(value)
    if kind is ValueKind.TEXT:
        return isinstance(value, str)
    if kind is ValueKind.TEXT_ARRAY:
        return isinstance(value, tuple) and all(isinstance(item, str) for item in value)
    return isinstance(value, Mapping)


def _missing_key_problem(key: str, mapping: Mapping[str, Any]) -> str:
    close = difflib.get_close_matches(key, list(mapping), n=3, cutoff=0.6)
    hint = f"; close matches: {close}" if close else ""
    return f"missing key {key!r}{hint}"


def _select_named_item(items: Any, part: NamedItem, walked: str) -> Any:
    if not isinstance(items, tuple):
        raise ReferenceKeyError(walked, f"expected a list to select {part}")
    matches = [
        item for item in items if isinstance(item, Mapping) and item.get("name") == part.name
    ]
    if len(matches) != 1:
        raise ReferenceKeyError(walked, f"{part} matches {len(matches)} items, expected 1")
    return matches[0]


def _walk(tree: Any, key: RefKey) -> Any:
    node = tree
    walked = key.file.value
    for part in key.path:
        if isinstance(part, NamedItem):
            node = _select_named_item(node, part, walked)
        elif isinstance(node, Mapping) and part in node:
            node = node[part]
        elif isinstance(node, Mapping):
            raise ReferenceKeyError(key.notation(), _missing_key_problem(part, node))
        else:
            raise ReferenceKeyError(key.notation(), f"{walked} is not a mapping")
        walked += PATH_SEPARATOR + str(part)
    return node


@dataclass(frozen=True, eq=False)
class ReferenceData:
    """One reference file, parsed and frozen."""

    file: ReferenceFile
    source_path: Path
    tree: Mapping[str, Any]
    sha256: str
    """SHA-256 of the file bytes as read."""


def load_reference_file(file: ReferenceFile, path: str | Path | None = None) -> ReferenceData:
    """Read one reference file.

    Args:
        file: Which reference file.
        path: Location; defaults to :data:`DEFAULT_FILE_PATHS` ``[file]``.

    Raises:
        OSError: The file cannot be read.
        ReferenceValueError: The file is not a JSON object.
    """
    source_path = Path(path) if path is not None else DEFAULT_FILE_PATHS[file]
    file_bytes = source_path.read_bytes()
    try:
        tree = json.loads(file_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReferenceValueError(file.value, f"{source_path} is not UTF-8 JSON: {error}") from None
    if not isinstance(tree, dict):
        raise ReferenceValueError(file.value, f"{source_path} does not contain a JSON object")
    return ReferenceData(
        file=file,
        source_path=source_path,
        tree=_freeze(tree),
        sha256=hashlib.sha256(file_bytes).hexdigest(),
    )


@dataclass(frozen=True, eq=False)
class References:
    """Loaded reference files; read values with :meth:`get`."""

    files: Mapping[ReferenceFile, ReferenceData]

    def get(
        self,
        key: RefKey,
        *,
        level: AugerLevel | str | None = None,
        case: str | None = None,
        beta: str | None = None,
        leg: str | None = None,
    ) -> Any:
        """Return the read-only value at ``key`` after filling in its placeholders.

        Example: ``refs.get(L1_CONTACT_FORCE_N, level="top")`` or
        ``refs.get(LEG_EXTENSION_DAMPED_PEAK_PAD_FORCE_N, leg="FL")``.

        Raises:
            ReferenceKeyError: A placeholder has no value, the file is not loaded, a key is
                missing, or a named list item is missing or ambiguous. The message holds
                the full notation.
            ReferenceValueError: The value is not of ``key.kind``.
        """
        concrete = key.resolve(level=level, case=case, beta=beta, leg=leg)
        unresolved = concrete.placeholders()
        if unresolved:
            names = ", ".join(placeholder.value for placeholder in unresolved)
            raise ReferenceKeyError(concrete.notation(), f"unresolved placeholder(s) {names}")
        if concrete.file not in self.files:
            raise ReferenceKeyError(concrete.notation(), "reference file not loaded")
        value = _walk(self.files[concrete.file].tree, concrete)
        if not _matches_kind(value, concrete.kind):
            raise ReferenceValueError(
                concrete.notation(), f"expected {concrete.kind.value}, got {value!r:.80}"
            )
        return value

    def sha256_by_file(self) -> dict[str, str]:
        """File name -> SHA-256 of its bytes, for the run meta (R16, plan S3 meta)."""
        return {file.value: data.sha256 for file, data in self.files.items()}


def load_references(
    paths: Mapping[ReferenceFile, str | Path] | None = None,
    *,
    files: Iterable[ReferenceFile] = tuple(ReferenceFile),
) -> References:
    """Load the reference files.

    Args:
        paths: Per-file location overrides; files not listed use :data:`DEFAULT_FILE_PATHS`.
        files: Which files to load (default: all of :class:`ReferenceFile`).

    Raises:
        OSError: A file cannot be read.
        ReferenceValueError: A file is not a JSON object.
    """
    locations = paths or {}
    loaded = {file: load_reference_file(file, locations.get(file)) for file in files}
    return References(files=MappingProxyType(loaded))
