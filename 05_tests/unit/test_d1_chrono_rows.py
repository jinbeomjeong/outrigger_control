"""D-1 Chrono rows (cad 2026-11-08): definitions only (no Chrono run)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

pytest.importorskip("pychrono")

import d1_chrono_rows as d1  # noqa: E402
import run_S6C as s6  # noqa: E402
import run_S8C as s8  # noqa: E402
import s9_batch as sb  # noqa: E402


@pytest.fixture(scope="module")
def b():
    return sb.batches()


def test_sixteen_required_ids(b) -> None:
    rows = b[d1.D1_BATCH]
    assert d1.required_count(rows) == {"C2": 8, "C1": 4, "S": 4}
    ids = sorted({r["d1_id"] for r in rows})
    assert len(ids) == 16
    # roll sign and S slope are the only choices
    multi = {i for i in ids if sum(r["d1_id"] == i for r in rows) > 1}
    assert multi == {"C2-03", "C2-07", "S-01", "S-02"}


def test_c2_rows_use_live_vb_argv(b) -> None:
    rows = [r for r in b[d1.D1_BATCH] if r["d1_id"].startswith("C2-")]
    assert len(rows) == 10
    vb = sb.v5_rigid_argv("VB")
    for r in rows:
        assert r["s8c"] and r["v5_setting"] == "VB" and r["argv"][-len(vb):] == vb
        assert r["argv"][r["argv"].index("--set") + 1] == "d1c2"
        assert d1.D1_C2_TAG in r["d1_tag"]
        assert r["controller"] == "final_C4G2_P3_LAS" and "--extend-start-tracked" in r["argv"]
    floors = {c.case_id: (c.scenario.level, s8.st.FLOORS[c.floor], c.fs_kN) for c in s8.case_set("d1c2")}
    assert floors["D1C2_middle_rpBop_Fs4"] == ("middle", (2.3351, 1.5017), 4.0)
    assert floors["D1C2_bottom_rollm4.4_Fs4"] == ("bottom", (-4.4, 0.0), 4.0)
    assert floors["D1C2_bottom_fup3.2_Fs4"] == ("bottom", (0.0, -3.2), 4.0)


def test_soil_rows_vb_and_level_patch(b) -> None:
    vb = sb.v5_vb_argv()
    rows = [r for r in b[d1.D1_BATCH] if r["d1_id"].startswith("S-")]
    for r in rows:
        a = r["argv"]
        assert a[-len(vb):] == vb and "--expect-controller" in a
        # criteria revision 8 3.1 + the LAS-b switch: the VB rows run (and are checked as) final_C4G2_P3_LAS
        assert a[a.index("--expect-controller") + 1] == r["controller"] == "final_C4G2_P3_LAS"
        assert "--extend-start-tracked" in a
        assert a[a.index("--level") + 1] in ("middle", "bottom")
    patch = [r for r in rows if r["d1_id"] in ("S-03", "S-04")]
    assert all(r["argv"][r["argv"].index("--soil-patch") + 1] == "FL:J1" for r in patch)
    fup = [r for r in rows if r.get("d1_slope") == "fup-rec"]
    assert len(fup) == 2 and all(r["optional"] and r["d1_flag"] == "ASSUMED_BOUNDARY" for r in fup)


def test_c1_crawler_factor_plant_only() -> None:
    cases = s6.d1c1_cases()
    assert [c.case_id for c in cases] == list(s6.D1C1_IDS.values())
    c = cases[0]
    over = s6.param_overrides(c)
    from outrigger_sim.params import load_params

    base = load_params(level="top")
    assert over[s6.CRAWLER_KN_KEY] == pytest.approx(3.0 * float(base.get(s6.CRAWLER_KN_KEY)), rel=1e-15)
    assert over[s6.CRAWLER_GN_KEY] == pytest.approx(math.sqrt(3.0) * float(base.get(s6.CRAWLER_GN_KEY)), rel=1e-15)
    assert over[s6.CRAWLER_C_TOTAL_KEY] == pytest.approx(
        math.sqrt(3.0) * float(base.get(s6.CRAWLER_C_TOTAL_KEY)), rel=1e-15)
    assert s6.controller_param_overrides(c) == {}
    assert c.snapshot == "S6_crawler_top_flat_crx3"
    assert "crawler_k_factor" in c.to_meta()


def test_earlier_s6_cases_keep_meta() -> None:
    c = next(x for x in s6.bundle_c_cases() if x.case_id == "C1_G1_top_flat")
    assert "crawler_k_factor" not in c.to_meta() and "crawler_k_factor" not in repr(c)
    assert s6.param_overrides(c) == {}


def test_psc_rows_depend_on_base(b) -> None:
    rows = b[d1.D1_PSC_BATCH]
    names = {r["case"] for r in rows}
    for r in rows:
        assert r["optional"]
        if r.get("depends_on"):
            assert r["depends_on"] in names
            ev = r["argv"][r["argv"].index("--soil-event") + 1]
            leg = ev.split(":")[0]
            assert r["argv"][r["argv"].index("--soil-patch") + 1] == f"{leg}:J1"
