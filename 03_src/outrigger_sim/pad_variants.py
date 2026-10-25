"""Pad type as an experiment variable (YAML ``pad_shapes`` + ``02_params/pad_variants.json``).

User decisions U-PAD-1..6 (2026-10-25), ``00_docs/01_dynamics/dynamics_model.md`` rev. 44 5.30:

* ``dwg_rear250`` (type B, **default**): front 330 CAD pads, rear 250 x 250 drawing pads
  (chamfer 30 mm ASSUMPTION), 0.0607 m^2;
* ``cad330`` (type A): four 330 CAD pads, 0.1071 m^2.

Masses are the same for both types (U-PAD-3); only the pad bottom polygon and area change. The
rigid-floor models (L1, L2b; S1 ... S8) do not use the pad area (5.30.3).

Sources (YAML bundle 2026-10-25, decision D4):

* **Shape** (polygon, area, perimeter, Bekker width): the YAML block ``pad_shapes``, left out of
  the L1 / L2b fingerprint (``params.SCM_ONLY_HASH_PATHS``). A YAML from before the bundle has
  no such block; then the shapes come from the table and the YAML ``legs.<leg>.pad`` holds the
  type A polygons.
* **C8 shapes** (convex pad hull, simple visual OBJ): the table ``02_params/pad_variants.json``
  written by ``04_scripts/00_cad/export_pad_variants.py`` (do not edit by hand). Polygons that
  the table still records are checked against the YAML. Both the table format with polygons
  (schema 1) and a table that holds only the C8 mapping are read.

:func:`apply_pad_variant` selects the type of a run: with ``pad_shapes`` it overrides
``pad_shapes.default_type`` (the L1 / L2b fingerprint stays the same; an SCM run fingerprints the
type with ``params.scm_run_sha256``); without it, it overrides the polygons of
``legs.<leg>.pad`` (the fingerprint then contains the type).

Command line: :func:`add_pad_variant_argument` adds ``--pad-variant {cad330,dwg_rear250}``
(default ``dwg_rear250``) to a runner's parser; :func:`pad_variant_meta` returns the run meta
block (``pad_variant``, table SHA-256, per-leg area / Bekker width / polygon SHA-256).

Units SI (m, m^2), body frame (x forward, y left, z up); polygons relative to
``legs.<leg>.pad_bottom_center_retracted_m``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from outrigger_sim.params import (
    LEG_ORDER,
    PAD_SHAPES_KEY,
    PAD_TYPE_OVERRIDE_KEY,
    Params,
    load_params,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAD_VARIANTS_JSON = PROJECT_ROOT / "02_params" / "pad_variants.json"
PAD_VARIANT_NAMES: tuple[str, ...] = ("cad330", "dwg_rear250")
DEFAULT_PAD_VARIANT = "dwg_rear250"
"""U-PAD-1 (2026-10-25): drawing type B is the default."""
PAD_KEYS: tuple[str, ...] = ("polygon_xy_m", "bottom_area_m2")
"""Keys of ``legs.<leg>.pad`` a pad type replaces in a YAML without ``pad_shapes`` (U-PAD-3:
no mass key)."""
CAD_POLYGON_TOL_M = 1.0e-9
"""A table polygon / area must equal the YAML one within this (same B-rep)."""
SHAPE_REL_TOL = 1.0e-9
"""Relative tolerance of the table perimeter / Bekker width against the YAML."""

GEOMETRY_FROM_YAML = "yaml pad_shapes"
GEOMETRY_FROM_TABLE = "pad_variants.json (YAML without pad_shapes)"


class PadVariantError(ValueError):
    """Unknown pad type, a table that does not fit the YAML, or a bad table."""


@dataclass(frozen=True)
class PadShape:
    """One leg of one pad type."""

    leg: str
    polygon_xy_m: tuple[tuple[float, float], ...]
    bottom_area_m2: float
    perimeter_m: float
    bekker_b_m: float
    """Chrono SCM patch width ``2 A / perimeter`` [m]."""
    polygon_sha256: str
    source_kind: str
    """``cad_brep`` or ``drawing_synthesis_brep``."""
    assumptions: tuple[str, ...]
    hull_name: str
    hull_file: Path
    """C8 convex pad hull OBJ (body frame, retracted state)."""
    hull_in_c8_index: bool
    """True: the hull is the ``01_cad/09_sim_shapes/sim_shapes.json`` entry ``hull_name``."""
    visual_simple_name: str
    visual_simple_file: Path


@dataclass(frozen=True)
class PadVariant:
    """One pad type (four legs in LEG_ORDER)."""

    name: str
    label: str
    description: str
    legs: tuple[PadShape, ...]

    def leg(self, name: str) -> PadShape:
        return self.legs[LEG_ORDER.index(name)]

    def overrides(self) -> dict[str, Any]:
        """``legs.<leg>.pad`` overrides for a YAML **without** ``pad_shapes`` (before the
        bundle of 2026-10-25); a bundle YAML selects the type with ``pad_shapes.default_type``
        (:func:`apply_pad_variant`)."""
        out: dict[str, Any] = {}
        for shape in self.legs:
            out[f"legs.{shape.leg}.pad.polygon_xy_m"] = [list(p) for p in shape.polygon_xy_m]
            out[f"legs.{shape.leg}.pad.bottom_area_m2"] = shape.bottom_area_m2
        return out


@dataclass(frozen=True)
class PadVariantTable:
    """``02_params/pad_variants.json`` with the shapes resolved against the YAML."""

    path: Path
    sha256: str
    """SHA-256 of the table file bytes."""
    default: str
    variants: Mapping[str, PadVariant]
    params_file_sha256: str
    """YAML file hash the table was generated from (information; empty if not recorded)."""
    generator_sha256: str
    geometry_source: str = GEOMETRY_FROM_TABLE
    """:data:`GEOMETRY_FROM_YAML` or :data:`GEOMETRY_FROM_TABLE`."""

    def variant(self, name: str | None = None) -> PadVariant:
        resolved = resolve_pad_variant(name, self)
        return self.variants[resolved]


@dataclass(frozen=True)
class _ShapeGeometry:
    polygon_xy_m: tuple[tuple[float, float], ...]
    bottom_area_m2: float
    perimeter_m: float
    bekker_b_m: float
    source_kind: str


def polygon_sha256(polygon: Any) -> str:
    """SHA-256 of the canonical JSON of a polygon ``[[x, y], ...]`` (floats, no spaces)."""
    text = json.dumps([[float(x), float(y)] for x, y in polygon], separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def has_pad_shapes(params: Params) -> bool:
    """True when the YAML carries the ``pad_shapes`` block (bundle 2026-10-25)."""
    return PAD_SHAPES_KEY in params.raw


# --- shape geometry from the YAML or the table ---------------------------------------------


def _geometry(record: Mapping[str, Any]) -> _ShapeGeometry:
    return _ShapeGeometry(
        polygon_xy_m=tuple((float(x), float(y)) for x, y in record["polygon_xy_m"]),
        bottom_area_m2=float(record["bottom_area_m2"]),
        perimeter_m=float(record["perimeter_m"]),
        bekker_b_m=float(record["bekker_b_m"]),
        source_kind=str(record["source_kind"]),
    )


def _yaml_type_names(params: Params) -> tuple[str, ...]:
    return tuple(params.get(f"{PAD_SHAPES_KEY}.type_order"))


def _yaml_geometry(params: Params, type_name: str, leg: str) -> _ShapeGeometry:
    return _geometry(params.get(f"{PAD_SHAPES_KEY}.types.{type_name}.legs.{leg}"))


def _table_geometry(type_name: str, leg: str, record: Mapping[str, Any]) -> _ShapeGeometry | None:
    """Polygon recorded in the table (schema 1), hash-checked; None for a C8-only table."""
    if "polygon_xy_m" not in record:
        return None
    geometry = _geometry(record)
    if polygon_sha256(geometry.polygon_xy_m) != record["polygon_sha256"]:
        raise PadVariantError(f"{type_name}.{leg}: polygon_sha256 does not match the polygon")
    return geometry


def _is_close(first: float, second: float, rel_tol: float) -> bool:
    return math.isclose(first, second, rel_tol=rel_tol, abs_tol=0.0)


def _same_geometry(first: _ShapeGeometry, second: _ShapeGeometry) -> bool:
    if len(first.polygon_xy_m) != len(second.polygon_xy_m):
        return False
    for p, q in zip(first.polygon_xy_m, second.polygon_xy_m, strict=True):
        if any(abs(a - b) > CAD_POLYGON_TOL_M for a, b in zip(p, q, strict=True)):
            return False
    return (
        abs(first.bottom_area_m2 - second.bottom_area_m2) <= CAD_POLYGON_TOL_M
        and _is_close(first.perimeter_m, second.perimeter_m, SHAPE_REL_TOL)
        and _is_close(first.bekker_b_m, second.bekker_b_m, SHAPE_REL_TOL)
        and first.source_kind == second.source_kind
    )


def _shape(
    leg: str, geometry: _ShapeGeometry, record: Mapping[str, Any], root: Path
) -> PadShape:
    c8 = record["c8"]
    return PadShape(
        leg=leg,
        polygon_xy_m=geometry.polygon_xy_m,
        bottom_area_m2=geometry.bottom_area_m2,
        perimeter_m=geometry.perimeter_m,
        bekker_b_m=geometry.bekker_b_m,
        polygon_sha256=polygon_sha256(geometry.polygon_xy_m),
        source_kind=geometry.source_kind,
        assumptions=tuple(record.get("assumptions", ())),
        hull_name=c8["hull"]["name"],
        hull_file=root / c8["hull"]["file"],
        hull_in_c8_index=bool(c8["in_c8_index"]),
        visual_simple_name=c8["visual_simple"]["name"],
        visual_simple_file=root / c8["visual_simple"]["file"],
    )


def _resolved_geometry(
    params: Params, type_name: str, leg: str, record: Mapping[str, Any]
) -> _ShapeGeometry:
    """The YAML shape (checked against a polygon the table still records), else the table's."""
    table_geometry = _table_geometry(type_name, leg, record)
    if not has_pad_shapes(params):
        if table_geometry is None:
            raise PadVariantError(
                f"{type_name}.{leg}: the table has no polygon and the YAML has no pad_shapes"
            )
        return table_geometry
    yaml_geometry = _yaml_geometry(params, type_name, leg)
    if table_geometry is not None and not _same_geometry(table_geometry, yaml_geometry):
        raise PadVariantError(
            f"{type_name}.{leg}: table polygon differs from the YAML pad_shapes; rerun "
            "04_scripts/00_cad/export_pad_variants.py"
        )
    return yaml_geometry


# --- public API ----------------------------------------------------------------------------


def load_pad_variants(
    path: str | Path | None = None, *, params: Params | None = None
) -> PadVariantTable:
    """Read the pad-type table and resolve every shape against the YAML.

    Args:
        path: Table file; defaults to :data:`PAD_VARIANTS_JSON`.
        params: Parameters whose YAML gives the shapes; None loads the default YAML.

    Raises:
        PadVariantError: Missing type, legs not in LEG_ORDER, polygon hash mismatch, a table
            polygon that differs from the YAML ``pad_shapes``, or no shape source at all.
        OSError: The file cannot be read.
    """
    path = PAD_VARIANTS_JSON if path is None else Path(path)
    params = load_params() if params is None else params
    data = path.read_bytes()
    doc = json.loads(data.decode("utf-8"))
    root = path.resolve().parents[1]  # <root>/02_params/pad_variants.json
    if tuple(doc["names"]) != PAD_VARIANT_NAMES or set(doc["variants"]) != set(PAD_VARIANT_NAMES):
        raise PadVariantError(f"{path}: expected types {PAD_VARIANT_NAMES}, got {doc['names']}")
    if has_pad_shapes(params) and _yaml_type_names(params) != PAD_VARIANT_NAMES:
        raise PadVariantError(
            f"YAML pad_shapes.type_order {_yaml_type_names(params)} differs from "
            f"{PAD_VARIANT_NAMES}"
        )
    variants = {}
    for name in PAD_VARIANT_NAMES:
        item = doc["variants"][name]
        if tuple(item["legs"]) != LEG_ORDER:
            raise PadVariantError(f"{name}: expected legs {LEG_ORDER}, got {tuple(item['legs'])}")
        shapes = []
        for leg in LEG_ORDER:
            record = item["legs"][leg]
            geometry = _resolved_geometry(params, name, leg, record)
            shapes.append(_shape(leg, geometry, record, root))
        variants[name] = PadVariant(
            name=name,
            label=item["label"],
            description=item.get("description", ""),
            legs=tuple(shapes),
        )
    default = doc.get("default", DEFAULT_PAD_VARIANT)
    if default != DEFAULT_PAD_VARIANT:
        raise PadVariantError(f"{path}: default {default!r}, expected {DEFAULT_PAD_VARIANT!r}")
    return PadVariantTable(
        path=path,
        sha256=hashlib.sha256(data).hexdigest(),
        default=default,
        variants=variants,
        params_file_sha256=doc.get("params_yaml", {}).get("file_sha256", ""),
        generator_sha256=doc.get("generator", {}).get("sha256", ""),
        geometry_source=GEOMETRY_FROM_YAML if has_pad_shapes(params) else GEOMETRY_FROM_TABLE,
    )


def resolve_pad_variant(name: str | None, table: PadVariantTable | None = None) -> str:
    """``None`` -> the default type; unknown names raise :class:`PadVariantError`."""
    resolved = (table.default if table is not None else DEFAULT_PAD_VARIANT) if name is None else name
    if resolved not in PAD_VARIANT_NAMES:
        raise PadVariantError(f"unknown pad type {resolved!r}, expected one of {PAD_VARIANT_NAMES}")
    return resolved


def check_table_against_params(table: PadVariantTable, params: Params) -> None:
    """The table shapes must be the shapes of ``params``' YAML.

    With ``pad_shapes``: every type and leg equals the YAML type. Without it (before the bundle):
    the table's ``cad_brep`` legs equal the YAML ``legs.<leg>.pad`` polygons (type A = YAML).

    Raises:
        PadVariantError: A shape differs (regenerate the table with
            ``04_scripts/00_cad/export_pad_variants.py``).
    """
    if has_pad_shapes(params):
        _check_table_against_pad_shapes(table, params)
        return
    base = _base_params(params)
    for variant in table.variants.values():
        for shape, leg in zip(variant.legs, base.legs, strict=True):
            if shape.source_kind != "cad_brep":
                continue
            yaml_poly = leg.pad.polygon_xy_m
            if len(yaml_poly) != len(shape.polygon_xy_m) or any(
                abs(a - b) > CAD_POLYGON_TOL_M
                for p, q in zip(yaml_poly, shape.polygon_xy_m, strict=True)
                for a, b in zip(p, q, strict=True)
            ) or abs(leg.pad.bottom_area_m2 - shape.bottom_area_m2) > CAD_POLYGON_TOL_M:
                raise PadVariantError(
                    f"{variant.name}.{shape.leg}: CAD pad differs from the YAML; rerun "
                    "04_scripts/00_cad/export_pad_variants.py"
                )


def _check_table_against_pad_shapes(table: PadVariantTable, params: Params) -> None:
    if _yaml_type_names(params) != PAD_VARIANT_NAMES:
        raise PadVariantError(
            f"YAML pad_shapes.type_order {_yaml_type_names(params)} differs from "
            f"{PAD_VARIANT_NAMES}"
        )
    for variant in table.variants.values():
        for shape in variant.legs:
            table_geometry = _ShapeGeometry(
                polygon_xy_m=shape.polygon_xy_m,
                bottom_area_m2=shape.bottom_area_m2,
                perimeter_m=shape.perimeter_m,
                bekker_b_m=shape.bekker_b_m,
                source_kind=shape.source_kind,
            )
            if not _same_geometry(table_geometry, _yaml_geometry(params, variant.name, shape.leg)):
                raise PadVariantError(
                    f"{variant.name}.{shape.leg}: table shape differs from the YAML pad_shapes"
                )


def _base_params(params: Params) -> Params:
    """``params`` without any pad override (other overrides kept)."""
    pad_paths = {f"legs.{leg}.pad.{key}" for leg in LEG_ORDER for key in PAD_KEYS}
    pad_paths.add(PAD_TYPE_OVERRIDE_KEY)
    if not pad_paths & set(params.overrides):
        return params
    rest = {k: v for k, v in params.overrides.items() if k not in pad_paths}
    return load_params(params.source_path, level=params.level, overrides=rest, model=params.model)


def apply_pad_variant(
    params: Params, name: str | None = None, *, table: PadVariantTable | None = None
) -> Params:
    """Parameters with the pad shapes of type ``name`` (default type B).

    The YAML file is not touched (``file_sha256`` unchanged). The returned :class:`Params` is
    reloaded from the same file, level and model with ``params.overrides`` plus the type:

    * YAML with ``pad_shapes``: override ``pad_shapes.default_type``. ``sha256`` stays the
      L1 / L2b fingerprint (the block is not part of it); ``params.scm_run_sha256`` holds the
      type. ``table`` is only checked when given.
    * YAML without it: the type's polygons as ``legs.<leg>.pad`` overrides, so ``sha256``
      contains the type (type A = the YAML polygons, same fingerprint).

    Use it only where the pad shape matters (S9 SCM, shape consumers).

    Raises:
        PadVariantError: Unknown type or a table that does not fit the YAML.
    """
    if has_pad_shapes(params):
        resolved = resolve_pad_variant(name, table)
        if table is not None:
            check_table_against_params(table, params)
        type_override = {PAD_TYPE_OVERRIDE_KEY: resolved}
    else:
        table = load_pad_variants(params=params) if table is None else table
        check_table_against_params(table, params)
        type_override = table.variant(name).overrides()
    overrides = {**dict(params.overrides), **type_override}
    out = load_params(params.source_path, level=params.level, overrides=overrides, model=params.model)
    for before, after in zip(params.legs, out.legs, strict=True):  # U-PAD-3: no mass change
        if before.moving_part != after.moving_part:
            raise PadVariantError(f"{before.name}: pad type changed the moving-part mass properties")
    return out


def pad_variant_meta(
    name: str | None = None,
    *,
    table: PadVariantTable | None = None,
    params: Params | None = None,
) -> dict[str, Any]:
    """Run meta block of the pad type (JSON-ready; 5.30.5: type, polygon SHA, A, b).

    ``params`` gives the YAML of the shapes when ``table`` is None (default YAML otherwise).
    """
    table = load_pad_variants(params=params) if table is None else table
    variant = table.variant(name)
    try:
        path_text = table.path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        path_text = table.path.resolve().as_posix()
    return {
        "pad_variant": variant.name,
        "pad_variant_label": variant.label,
        "pad_shapes_source": table.geometry_source,
        "pad_variants_path": path_text,
        "pad_variants_sha256": table.sha256,
        "pad_variants_params_file_sha256": table.params_file_sha256,
        "pad_bottom_area_m2": {s.leg: s.bottom_area_m2 for s in variant.legs},
        "pad_bekker_b_m": {s.leg: s.bekker_b_m for s in variant.legs},
        "pad_polygon_sha256": {s.leg: s.polygon_sha256 for s in variant.legs},
        "pad_hull": {s.leg: s.hull_name for s in variant.legs},
    }


def add_pad_variant_argument(parser: argparse.ArgumentParser) -> argparse.Action:
    """Add the common ``--pad-variant {cad330,dwg_rear250}`` option (default type B)."""
    return parser.add_argument(
        "--pad-variant",
        choices=PAD_VARIANT_NAMES,
        default=DEFAULT_PAD_VARIANT,
        help="pad type (YAML pad_shapes; C8 shapes 02_params/pad_variants.json): cad330 = four "
             "330 CAD pads, dwg_rear250 = front 330 / rear 250 drawing pads (default; U-PAD-1)",
    )


__all__ = [
    "DEFAULT_PAD_VARIANT",
    "GEOMETRY_FROM_TABLE",
    "GEOMETRY_FROM_YAML",
    "PAD_VARIANTS_JSON",
    "PAD_VARIANT_NAMES",
    "PadShape",
    "PadVariant",
    "PadVariantError",
    "PadVariantTable",
    "add_pad_variant_argument",
    "apply_pad_variant",
    "check_table_against_params",
    "has_pad_shapes",
    "load_pad_variants",
    "pad_variant_meta",
    "polygon_sha256",
    "resolve_pad_variant",
]
