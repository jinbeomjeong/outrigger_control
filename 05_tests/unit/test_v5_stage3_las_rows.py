"""V5-STAGE3-LAS (criteria rev. 12 2.1): 34 stage 3 rows + 3 pair rows on the LAS-b tags, definitions only."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

pytest.importorskip("pychrono")

import s9_batch as sb  # noqa: E402
import v5_stage3_las_rows as las3  # noqa: E402


@pytest.fixture(scope="module")
def all_batches():
    return sb.batches()


@pytest.fixture(scope="module")
def rows(all_batches):
    return all_batches[las3.LAS_STAGE3_BATCH]


def _arg(argv, key):
    return argv[argv.index(key) + 1] if key in argv else None


def test_count_names(rows, all_batches) -> None:
    assert len(rows) == 37
    stage3 = {r["case"] for r in all_batches[sb.V5_STAGE3_BATCH]}
    names = [r["case"] for r in rows]
    assert len(set(names)) == 37 and stage3 <= set(names)
    assert set(names) - stage3 == {las3.P1_NAME, las3.P2_NAME, las3.P3_NAME}


def test_controllers(rows) -> None:
    for r in rows:
        want = sb.V5_P3_LAS_K1_CONTROLLER if r["v5_setting"] in las3.VB_LS else sb.V5_LAS_K1_CONTROLLER
        assert r["controller"] == want
        if not r.get("s8c"):
            assert _arg(r["argv"], "--expect-controller") == want
            assert _arg(r["argv"], "--threads") == "4"
        else:
            assert "--expect-controller" not in r["argv"]


def test_same_case_args_as_stage3(rows, all_batches) -> None:
    """Plant / case / event / seed / threads: the stage 3 argv apart from the controller tag."""
    by = {r["case"]: r for r in all_batches[sb.V5_STAGE3_BATCH]}
    for r in rows:
        if r["case"] in by:
            assert las3._without(r["argv"], "--expect-controller") == las3._without(by[r["case"]]["argv"],
                                                                                   "--expect-controller")


def test_pairs_inside_batch(rows) -> None:
    names = {r["case"] for r in rows}
    for r in rows:
        if r.get("pair_case") is not None:
            assert r["pair_case"] in names, r["case"]


def test_p2_p3_are_stored_seed_s6(rows, all_batches) -> None:
    by = {r["case"]: r for r in rows}
    off, on = by[las3.P2_NAME], by[las3.P3_NAME]
    assert _arg(off["argv"], "--seed") == str(sb.P3B_SEED_STORED) and "--flow-eta-v" not in off["argv"]
    assert _arg(on["argv"], "--seed") == str(sb.P3B_SEED_STORED) and "--flow-eta-v" in on["argv"]
    # with the stored seed they repeat the S6SEED stored-seed rows (case name aside)
    assert off["argv"] == by[f"{las3.S6_CASE}_seed{sb.P3B_SEED_STORED}"]["argv"]
    assert on["argv"] == by[f"{las3.S6_CASE}_seed{sb.P3B_SEED_STORED}_flow"]["argv"]


def test_stored_argv_check(rows) -> None:
    if not (las3.results_root() / las3.STORED_SOIL / "batch.json").is_file():
        pytest.skip("stored batches not reachable")
    st = {r["case"]: r["stored_argv_check"]["status"] for r in rows}
    assert st.pop(las3.P1_NAME) == "no_stored_argv"
    assert set(st.values()) == {"ok"}
    for r in rows:
        assert r["stored_result"] and r["est_pool_s"]["pcore"] > 0


def test_other_batches_unchanged(all_batches) -> None:
    orig = sb._stage3_las_module
    try:
        sb._stage3_las_module = lambda: type("M", (), {"las_stage3_batches": staticmethod(lambda s, o: {})})
        without = sb.batches()
    finally:
        sb._stage3_las_module = orig

    def h(x):
        return hashlib.sha256(json.dumps(x, sort_keys=True, default=str).encode()).hexdigest()

    assert set(all_batches) - set(without) == {las3.LAS_STAGE3_BATCH}
    assert [k for k in without if h(without[k]) != h(all_batches[k])] == []
