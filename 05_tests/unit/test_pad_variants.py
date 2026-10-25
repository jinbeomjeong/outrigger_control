"""Pad type table and run-time override (``outrigger_sim.pad_variants``, U-PAD 2026-10-25).

The rigid-floor fingerprints must not change: loading the YAML is untouched, only
:func:`apply_pad_variant` changes the pad polygons in memory.
"""

from __future__ import annotations

import argparse
import json
import math

import pytest

from outrigger_sim import pad_variants as pv
from outrigger_sim.params import LEG_ORDER, load_params

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


def test_yaml_fingerprint_untouched_by_the_table(table: pv.PadVariantTable) -> None:
    base = load_params()
    assert table.params_file_sha256 == base.file_sha256
    pv.check_table_against_params(table, base)  # type A = YAML polygons today


def test_apply_type_a_equals_yaml_and_type_b_changes_only_rear_pads(table: pv.PadVariantTable) -> None:
    base = load_params()
    a = pv.apply_pad_variant(base, "cad330", table=table)
    b = pv.apply_pad_variant(base, None, table=table)
    assert a.sha256 == base.sha256  # type A polygons are the YAML polygons
    assert a.file_sha256 == b.file_sha256 == base.file_sha256
    assert b.sha256 != base.sha256  # the run fingerprint contains the type
    for i, leg in enumerate(LEG_ORDER):
        assert b.legs[i].moving_part == base.legs[i].moving_part  # U-PAD-3
        assert b.get(f"legs.{leg}.pad_body") == base.get(f"legs.{leg}.pad_body")
        assert b.legs[i].pad.thickness_m == base.legs[i].pad.thickness_m
        assert b.legs[i].pad.swivel_center_above_pad_bottom_m == base.legs[i].pad.swivel_center_above_pad_bottom_m
    assert b.legs[2].pad.bottom_area_m2 == pytest.approx(0.0607, rel=1e-9)
    assert b.legs[0].pad == base.legs[0].pad
    assert set(b.overrides) == {f"legs.{leg}.pad.{k}" for leg in LEG_ORDER for k in pv.PAD_KEYS}
    # base object untouched
    assert base.legs[2].pad.bottom_area_m2 == pytest.approx(0.1071, rel=1e-9)
    # re-applying another type replaces the pad overrides, other overrides stay
    other = load_params(overrides={"actuator.oil_bulk_modulus_eff_Pa": 1.6e9})
    b2 = pv.apply_pad_variant(other, "dwg_rear250", table=table)
    a2 = pv.apply_pad_variant(b2, "cad330", table=table)
    assert a2.overrides["actuator.oil_bulk_modulus_eff_Pa"] == 1.6e9
    assert a2.sha256 == other.sha256


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
