"""Paper v5 rows of ``s9_batch`` (user decision 2026-11-08): 2.8 open-loop lift VB / V0 and 3.5.2 J_P VB / V0."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

CHRONO_SCRIPTS = Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"


def _import(name: str):
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(CHRONO_SCRIPTS))


@pytest.fixture(scope="module")
def sb():
    pytest.importorskip("pychrono")
    return _import("s9_batch")


@pytest.fixture(scope="module")
def all_batches(sb):
    return sb.batches()


def test_openloop_rows_are_the_stored_p3a_rows_plus_vb(sb, all_batches) -> None:
    p3a = {r["case"]: r for r in all_batches["P3a"]}
    vb = all_batches[sb.V5_OPENLOOP_BATCH]
    v0 = all_batches[sb.V5_OPENLOOP_V0_BATCH]
    assert [r["case"] for r in vb] == ["P3a_J1_B_VB", "P3a_G1_B_VB"]
    assert [r["case"] for r in v0] == ["P3a_J1_B_V0", "P3a_G1_B_V0"]
    for r in vb:
        base = p3a[r["case"].removesuffix("_VB")]
        assert r["argv"] == base["argv"] + sb.v5_vb_argv()
        assert r["source_expected_diffs"] == sb.V5_VB_ARGS
        assert "--expect-controller" not in r["argv"]
        assert r["source_run"].startswith(sb.V5_OPENLOOP_SOURCE + "/")
    for r in v0:
        assert r["argv"] == p3a[r["case"].removesuffix("_V0")]["argv"]
        assert r["source_expected_diffs"] is None


def test_openloop_prop_row_changes_only_the_flow_law(sb, all_batches) -> None:
    vb = {r["case"]: r for r in all_batches[sb.V5_OPENLOOP_BATCH]}
    prop = all_batches[sb.V5_OPENLOOP_PROP_BATCH]
    assert [r["case"] for r in prop] == ["P3a_J1_B_VB_prop"]
    r, base = prop[0], vb["P3a_J1_B_VB"]
    diff = [(a, b) for a, b in zip(r["argv"], base["argv"], strict=True) if a != b]
    assert diff == [("proportional", "priority")]
    assert r["argv"][r["argv"].index("--flow-law") + 1] == "proportional"
    assert r["source_expected_diffs"] == {**sb.V5_VB_ARGS, "flow_law": "proportional"}
    assert r["pair_case"] == "P3a_J1_B_VB" and r["source_run"] == base["source_run"]
    assert base["argv"][base["argv"].index("--flow-law") + 1] == "priority"  # VB row unchanged


def test_jp_rows_use_the_live_rigid_vb_arguments(sb, all_batches) -> None:
    vb = all_batches[sb.V5_JP_BATCH]
    v0 = all_batches[sb.V5_JP_V0_BATCH]
    assert [r["s8c_case_id"] for r in vb] == list(sb.V5_JP_IDS)
    assert [r["case"] for r in v0] == [f"{c}_V0" for c in sb.V5_JP_IDS]
    for r in vb:
        tail = r["argv"][r["argv"].index("--workers") + 2:]
        assert tail == sb.v5_rigid_argv("VB")
        assert r["controller"] == sb.V5_P3_CONTROLLER == "final_C4G2_P3"
        assert r["argv"][r["argv"].index("--set") + 1] == sb.V5_JP_SET
        assert r["source_run"] == f"{sb.V5_JP_SOURCE}/{r['s8c_case_id']}"
        assert r["est_s"] >= sb.V5_JP_EST_S["VB"]
    for r in v0:
        assert r["argv"][r["argv"].index("--workers") + 2:] == []
        assert r["controller"] == "final_C4G2"


def test_machine_parser_takes_the_vb_argv(sb) -> None:
    r9 = _import("run_S9")
    args = r9.build_parser().parse_args(["machine", "--soil", "G1", "--lift-s", "28", *sb.v5_vb_argv()])
    from outrigger_sim.hydraulics.v5_options import hydraulic_options_from_args

    opts = hydraulic_options_from_args(args)
    assert opts.valve_tau_s == 0.1 and opts.rod_release_force and opts.extend_start_tracked
    meta = r9.machine_controller_options_meta(opts)
    assert meta["applied"] is False and meta["extend_start_tracked"] is True
    plain = vars(r9.build_parser().parse_args(["machine", "--soil", "G1"]))
    assert "flow_eta_v" not in plain and "valve_tau_s" not in plain  # absent = no attribute (stored runs unchanged)
