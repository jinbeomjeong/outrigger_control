"""Pad type table and run-time override (``outrigger_sim.pad_variants``, U-PAD 2026-10-25).

The rigid-floor fingerprints must not change: loading the YAML is untouched, only
:func:`apply_pad_variant` changes the pad polygons in memory. The tests pass on a YAML from
before the bundle of 2026-10-25 (shapes in the table) and on a bundle YAML (shapes in
``pad_shapes``).
"""

from __future__ import annotations

import argparse
import json
import math

import pytest

from outrigger_sim import pad_variants as pv
from outrigger_sim.params import (
    LEG_ORDER,
    PAD_TYPE_OVERRIDE_KEY,
    Params,
    load_params,
    scm_run_sha256,
)

if not pv.PAD_VARIANTS_JSON.exists():  # pragma: no cover - generated data
    pytest.skip("02_params/pad_variants.json missing", allow_module_level=True)


@pytest.fixture(scope="module")
def table() -> pv.PadVariantTable:
    return pv.load_pad_variants()


def _shoelace(poly) -> float:
    s = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1], strict=True):
        s += x0 * y1 - x1 * y0
    return 0.5 * s


def test_table_types_and_default(table: pv.PadVariantTable) -> None:
    assert table.default == "dwg_rear250" == pv.DEFAULT_PAD_VARIANT
    assert tuple(table.variants) == ("cad330", "dwg_rear250")
    a, b = table.variant("cad330"), table.variant(None)
    assert b.name == "dwg_rear250"
    assert [s.bottom_area_m2 for s in a.legs] == pytest.approx([0.1071] * 4, rel=1e-9)
    assert [s.bottom_area_m2 for s in b.legs] == pytest.approx([0.1071, 0.1071, 0.0607, 0.0607], rel=1e-9)
    # front pads are the same shape in both types (drawing = CAD)
    for leg in ("FL", "FR"):
        assert a.leg(leg).polygon_xy_m == b.leg(leg).polygon_xy_m
        assert a.leg(leg).hull_name == b.leg(leg).hull_name == f"pad_{leg}_hull"
    assert b.leg("RL").source_kind == "drawing_synthesis_brep"
    assert any("chamfer 30" in text for text in b.leg("RL").assumptions)
    assert not a.leg("RL").hull_in_c8_index and b.leg("RL").hull_in_c8_index


def test_polygon_area_perimeter_and_bekker_width(table: pv.PadVariantTable) -> None:
    for variant in table.variants.values():
        for shape in variant.legs:
            poly = list(shape.polygon_xy_m)
            assert _shoelace(poly) == pytest.approx(shape.bottom_area_m2, rel=1e-7)  # counter-clockwise
            perimeter = sum(math.dist(p, q) for p, q in zip(poly, poly[1:] + poly[:1], strict=True))
            assert perimeter == pytest.approx(shape.perimeter_m, rel=1e-8)
            assert shape.bekker_b_m == pytest.approx(2 * shape.bottom_area_m2 / perimeter, rel=1e-8)
            assert shape.polygon_sha256 == pv.polygon_sha256(poly)
            assert shape.hull_file.exists() and shape.visual_simple_file.exists()
    # dynamics_model.md 5.30.1: b 0.1714 (330) / 0.1306 (250)
    assert table.variant("dwg_rear250").leg("RR").bekker_b_m == pytest.approx(0.1306, abs=5e-5)
    assert table.variant("cad330").leg("RR").bekker_b_m == pytest.approx(0.1714, abs=5e-5)


def test_table_fits_the_yaml(table: pv.PadVariantTable) -> None:
    base = load_params()
    pv.check_table_against_params(table, base)
    if pv.has_pad_shapes(base):  # bundle 2026-10-25: the YAML is the shape source
        assert table.geometry_source == pv.GEOMETRY_FROM_YAML
        for variant in table.variants.values():
            for shape in variant.legs:
                yaml_shape = base.get(f"pad_shapes.types.{variant.name}.legs.{shape.leg}")
                assert [list(p) for p in shape.polygon_xy_m] == [
                    list(p) for p in yaml_shape["polygon_xy_m"]
                ]
                assert shape.bekker_b_m == yaml_shape["bekker_b_m"]
    else:  # before the bundle: type A = YAML polygons, the table is the shape source
        assert table.geometry_source == pv.GEOMETRY_FROM_TABLE
        assert table.params_file_sha256 == base.file_sha256


def _assert_pad_type_keeps_masses_and_joint(out: Params, base: Params) -> None:
    for i, leg in enumerate(LEG_ORDER):
        assert out.legs[i].moving_part == base.legs[i].moving_part  # U-PAD-3
        assert out.get(f"legs.{leg}.pad_body") == base.get(f"legs.{leg}.pad_body")
        assert out.legs[i].pad.thickness_m == base.legs[i].pad.thickness_m
        assert (out.legs[i].pad.swivel_center_above_pad_bottom_m
                == base.legs[i].pad.swivel_center_above_pad_bottom_m)


def test_apply_type_a_and_type_b_change_only_rear_pads(table: pv.PadVariantTable) -> None:
    base = load_params()
    a = pv.apply_pad_variant(base, "cad330", table=table)
    b = pv.apply_pad_variant(base, None, table=table)
    assert a.file_sha256 == b.file_sha256 == base.file_sha256
    _assert_pad_type_keeps_masses_and_joint(a, base)
    _assert_pad_type_keeps_masses_and_joint(b, base)
    assert a.legs[2].pad.bottom_area_m2 == pytest.approx(0.1071, rel=1e-9)
    assert b.legs[2].pad.bottom_area_m2 == pytest.approx(0.0607, rel=1e-9)
    assert a.legs[0].pad.polygon_xy_m == b.legs[0].pad.polygon_xy_m
    if pv.has_pad_shapes(base):
        # the type is not part of the rigid-floor fingerprint, only of the SCM one (D5)
        assert a.sha256 == b.sha256 == base.sha256
        assert scm_run_sha256(a) != scm_run_sha256(b)
        assert scm_run_sha256(b) == scm_run_sha256(base)  # YAML default = type B
        assert a.legs[2].pad.pad_type == "cad330" and b.legs[2].pad.pad_type == "dwg_rear250"
        assert set(b.overrides) == {PAD_TYPE_OVERRIDE_KEY}
    else:
        assert a.sha256 == base.sha256  # type A polygons are the YAML polygons
        assert b.sha256 != base.sha256  # the run fingerprint contains the type
        assert b.legs[0].pad == base.legs[0].pad
        assert set(b.overrides) == {f"legs.{leg}.pad.{k}" for leg in LEG_ORDER for k in pv.PAD_KEYS}
        assert base.legs[2].pad.bottom_area_m2 == pytest.approx(0.1071, rel=1e-9)  # untouched
    # re-applying another type replaces the pad overrides, other overrides stay
    other = load_params(overrides={"actuator.oil_bulk_modulus_eff_Pa": 1.6e9})
    b2 = pv.apply_pad_variant(other, "dwg_rear250", table=table)
    a2 = pv.apply_pad_variant(b2, "cad330", table=table)
    assert a2.overrides["actuator.oil_bulk_modulus_eff_Pa"] == 1.6e9
    assert a2.legs[2].pad.bottom_area_m2 == pytest.approx(0.1071, rel=1e-9)
    assert a2.sha256 == pv.apply_pad_variant(other, "cad330", table=table).sha256


GEOMETRY_RECORD_KEYS = ("polygon_xy_m", "polygon_sha256", "bottom_area_m2", "perimeter_m",
                        "bekker_b_m")


def test_table_with_only_the_c8_mapping(tmp_path, table: pv.PadVariantTable) -> None:
    """The reduced table format (C8 hull / visual mapping, no polygons; cad C-2) is read when
    the YAML has ``pad_shapes`` and refused otherwise (no shape source left)."""
    doc = json.loads(pv.PAD_VARIANTS_JSON.read_text(encoding="utf-8"))
    for item in doc["variants"].values():
        for record in item["legs"].values():
            for key in GEOMETRY_RECORD_KEYS:
                record.pop(key)
    reduced_path = tmp_path / "02_params" / "pad_variants.json"
    reduced_path.parent.mkdir()
    reduced_path.write_text(json.dumps(doc), encoding="utf-8")
    base = load_params()
    if not pv.has_pad_shapes(base):
        with pytest.raises(pv.PadVariantError, match="no pad_shapes"):
            pv.load_pad_variants(reduced_path, params=base)
        return
    reduced = pv.load_pad_variants(reduced_path, params=base)
    for name, variant in reduced.variants.items():
        for shape, full in zip(variant.legs, table.variant(name).legs, strict=True):
            assert shape.polygon_xy_m == full.polygon_xy_m
            assert shape.polygon_sha256 == full.polygon_sha256
            assert shape.hull_name == full.hull_name
            assert shape.hull_file.relative_to(tmp_path.resolve()) == full.hull_file.relative_to(
                pv.PROJECT_ROOT)


def test_apply_keeps_model_and_level(table: pv.PadVariantTable) -> None:
    base = load_params(level="bottom", model="L2b_NSC")
    out = pv.apply_pad_variant(base, "dwg_rear250", table=table)
    assert out.level == base.level and out.model == base.model and out.l2b is not None


def test_unknown_type_raises(table: pv.PadVariantTable) -> None:
    with pytest.raises(pv.PadVariantError):
        pv.apply_pad_variant(load_params(), "cad250", table=table)


def test_argument_and_meta(table: pv.PadVariantTable) -> None:
    parser = argparse.ArgumentParser()
    pv.add_pad_variant_argument(parser)
    assert parser.parse_args([]).pad_variant == "dwg_rear250"
    assert parser.parse_args(["--pad-variant", "cad330"]).pad_variant == "cad330"
    with pytest.raises(SystemExit):
        parser.parse_args(["--pad-variant", "x"])
    meta = pv.pad_variant_meta("cad330", table=table)
    assert meta["pad_variant"] == "cad330"
    assert meta["pad_variants_sha256"] == table.sha256
    assert meta["pad_hull"]["RL"] == "pad_RL_hull_cad330"
    assert set(meta["pad_bottom_area_m2"]) == set(LEG_ORDER)
    json.dumps(meta)  # JSON-ready
