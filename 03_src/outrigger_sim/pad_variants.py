"""Pad type as an experiment variable (``02_params/pad_variants.json``, engine independent).

User decisions U-PAD-1..6 (2026-10-25), ``00_docs/01_dynamics/dynamics_model.md`` rev. 44 5.30
(implementation (1) of 5.30.5: run-time override from a generated side table):

* ``dwg_rear250`` (type B, **default**): front 330 CAD pads, rear 250 x 250 drawing pads
  (chamfer 30 mm ASSUMPTION), 0.0607 m^2;
* ``cad330`` (type A): four 330 CAD pads, 0.1071 m^2 (the polygons the YAML holds today).

Masses are the same for both types (U-PAD-3); only ``legs.<leg>.pad.polygon_xy_m`` and
``legs.<leg>.pad.bottom_area_m2`` change. The rigid-floor models (L1, L2b; S1 ... S8) do not use
the pad area (5.30.3), so they keep loading the YAML unchanged and their ``Params.sha256`` /
``file_sha256`` do not change. Consumers that use the pad shape (S9 SCM pad hull, C8 shape
selection) call :func:`apply_pad_variant`, which reloads the parameters with the type's
polygons as overrides: the fingerprint of such a run then contains the type (a snapshot of the
other type never matches).

The table is written by ``04_scripts/00_cad/export_pad_variants.py`` (do not edit by hand). At
the next YAML regeneration bundle the values move into a YAML block ``pad_shapes`` that is left
out of the L1 / L2b fingerprint (5.30.5 (3)); this module is then replaced by that block.

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
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from outrigger_sim.params import LEG_ORDER, Params, load_params

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAD_VARIANTS_JSON = PROJECT_ROOT / "02_params" / "pad_variants.json"
PAD_VARIANT_NAMES: tuple[str, ...] = ("cad330", "dwg_rear250")
DEFAULT_PAD_VARIANT = "dwg_rear250"
"""U-PAD-1 (2026-10-25): drawing type B is the default."""
PAD_KEYS: tuple[str, ...] = ("polygon_xy_m", "bottom_area_m2")
"""Keys of ``legs.<leg>.pad`` a pad type replaces (U-PAD-3: no mass key)."""
CAD_POLYGON_TOL_M = 1.0e-9
"""A ``cad_brep`` leg of the table must equal the YAML polygon within this (same B-rep)."""


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
        """Dotted-path overrides for :func:`outrigger_sim.params.load_params`."""
        out: dict[str, Any] = {}
        for shape in self.legs:
            out[f"legs.{shape.leg}.pad.polygon_xy_m"] = [list(p) for p in shape.polygon_xy_m]
            out[f"legs.{shape.leg}.pad.bottom_area_m2"] = shape.bottom_area_m2
        return out


@dataclass(frozen=True)
class PadVariantTable:
    """``02_params/pad_variants.json``."""

    path: Path
    sha256: str
    """SHA-256 of the table file bytes."""
    default: str
    variants: Mapping[str, PadVariant]
    params_file_sha256: str
    """YAML file hash the table was generated from (information; see :func:`apply_pad_variant`)."""
    generator_sha256: str

    def variant(self, name: str | None = None) -> PadVariant:
        resolved = resolve_pad_variant(name, self)
        return self.variants[resolved]


def polygon_sha256(polygon: Any) -> str:
    """SHA-256 of the canonical JSON of a polygon ``[[x, y], ...]`` (floats, no spaces)."""
    text = json.dumps([[float(x), float(y)] for x, y in polygon], separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _shape(leg: str, rec: Mapping[str, Any], root: Path) -> PadShape:
    polygon = tuple((float(x), float(y)) for x, y in rec["polygon_xy_m"])
    if polygon_sha256(polygon) != rec["polygon_sha256"]:
        raise PadVariantError(f"{leg}: polygon_sha256 does not match the polygon")
    c8 = rec["c8"]
    return PadShape(
        leg=leg,
        polygon_xy_m=polygon,
        bottom_area_m2=float(rec["bottom_area_m2"]),
        perimeter_m=float(rec["perimeter_m"]),
        bekker_b_m=float(rec["bekker_b_m"]),
        polygon_sha256=rec["polygon_sha256"],
        source_kind=rec["source_kind"],
        assumptions=tuple(rec.get("assumptions", ())),
        hull_name=c8["hull"]["name"],
        hull_file=root / c8["hull"]["file"],
        hull_in_c8_index=bool(c8["in_c8_index"]),
        visual_simple_name=c8["visual_simple"]["name"],
        visual_simple_file=root / c8["visual_simple"]["file"],
    )


def load_pad_variants(path: str | Path | None = None) -> PadVariantTable:
    """Read and check the pad-type table.

    Raises:
        PadVariantError: Missing type, legs not in LEG_ORDER, polygon hash mismatch.
        OSError: The file cannot be read.
    """
    path = PAD_VARIANTS_JSON if path is None else Path(path)
    data = path.read_bytes()
    doc = json.loads(data.decode("utf-8"))
    root = path.resolve().parents[1]  # <root>/02_params/pad_variants.json
    if tuple(doc["names"]) != PAD_VARIANT_NAMES or set(doc["variants"]) != set(PAD_VARIANT_NAMES):
        raise PadVariantError(f"{path}: expected types {PAD_VARIANT_NAMES}, got {doc['names']}")
    variants = {}
    for name in PAD_VARIANT_NAMES:
        item = doc["variants"][name]
        if tuple(item["legs"]) != LEG_ORDER:
            raise PadVariantError(f"{name}: expected legs {LEG_ORDER}, got {tuple(item['legs'])}")
        variants[name] = PadVariant(
            name=name,
            label=item["label"],
            description=item["description"],
            legs=tuple(_shape(leg, item["legs"][leg], root) for leg in LEG_ORDER),
        )
    if doc["default"] != DEFAULT_PAD_VARIANT:
        raise PadVariantError(f"{path}: default {doc['default']!r}, expected {DEFAULT_PAD_VARIANT!r}")
    return PadVariantTable(
        path=path,
        sha256=hashlib.sha256(data).hexdigest(),
        default=doc["default"],
        variants=variants,
        params_file_sha256=doc["params_yaml"]["file_sha256"],
        generator_sha256=doc["generator"]["sha256"],
    )


def resolve_pad_variant(name: str | None, table: PadVariantTable | None = None) -> str:
    """``None`` -> the default type; unknown names raise :class:`PadVariantError`."""
    resolved = (table.default if table is not None else DEFAULT_PAD_VARIANT) if name is None else name
    if resolved not in PAD_VARIANT_NAMES:
        raise PadVariantError(f"unknown pad type {resolved!r}, expected one of {PAD_VARIANT_NAMES}")
    return resolved


def check_table_against_params(table: PadVariantTable, params: Params) -> None:
    """The table's CAD legs must be the YAML polygons (type A = YAML today).

    Raises:
        PadVariantError: A ``cad_brep`` leg differs from the YAML (regenerate the table with
            ``04_scripts/00_cad/export_pad_variants.py``).
    """
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


def _base_params(params: Params) -> Params:
    """``params`` without any pad override (other overrides kept)."""
    pad_paths = {f"legs.{leg}.pad.{key}" for leg in LEG_ORDER for key in PAD_KEYS}
    if not pad_paths & set(params.overrides):
        return params
    rest = {k: v for k, v in params.overrides.items() if k not in pad_paths}
    return load_params(params.source_path, level=params.level, overrides=rest, model=params.model)


def apply_pad_variant(
    params: Params, name: str | None = None, *, table: PadVariantTable | None = None
) -> Params:
    """Parameters with the pad polygons / areas of type ``name`` (default type B).

    The YAML file is not touched (``file_sha256`` unchanged). The returned :class:`Params`
    is reloaded with the type's overrides on top of ``params.overrides`` (same file, level and
    model), so ``sha256`` contains the type. Use it only where the pad shape matters (S9 SCM,
    shape consumers); the rigid-floor runs keep ``params``. Type A (``cad330``) equals the YAML
    polygons today, so its fingerprint equals the plain YAML one.

    Raises:
        PadVariantError: Unknown type or a table that does not fit the YAML.
    """
    table = load_pad_variants() if table is None else table
    variant = table.variant(name)
    check_table_against_params(table, params)
    overrides = {**dict(params.overrides), **variant.overrides()}
    out = load_params(params.source_path, level=params.level, overrides=overrides, model=params.model)
    for before, after in zip(params.legs, out.legs, strict=True):  # U-PAD-3: no mass change
        if before.moving_part != after.moving_part:
            raise PadVariantError(f"{before.name}: pad type changed the moving-part mass properties")
    return out


def pad_variant_meta(name: str | None = None, *, table: PadVariantTable | None = None) -> dict[str, Any]:
    """Run meta block of the pad type (JSON-ready; 5.30.5: type, polygon SHA, A, b)."""
    table = load_pad_variants() if table is None else table
    variant = table.variant(name)
    try:
        path_text = table.path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        path_text = table.path.resolve().as_posix()
    return {
        "pad_variant": variant.name,
        "pad_variant_label": variant.label,
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
        help="pad type (02_params/pad_variants.json): cad330 = four 330 CAD pads, dwg_rear250 = "
             "front 330 / rear 250 drawing pads (default; U-PAD-1)",
    )


__all__ = [
    "DEFAULT_PAD_VARIANT",
    "PAD_VARIANTS_JSON",
    "PAD_VARIANT_NAMES",
    "PadShape",
    "PadVariant",
    "PadVariantError",
    "PadVariantTable",
    "add_pad_variant_argument",
    "apply_pad_variant",
    "check_table_against_params",
    "load_pad_variants",
    "pad_variant_meta",
    "polygon_sha256",
    "resolve_pad_variant",
]
