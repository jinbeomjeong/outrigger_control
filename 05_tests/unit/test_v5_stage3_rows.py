"""v5 stage 3 bundles of ``s9_batch`` (``stage3_impl_spec.md`` 3 / 4, criteria rev. 6 3)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

CHRONO_SCRIPTS = Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"


@pytest.fixture(scope="module")
def sb():
    pytest.importorskip("pychrono")
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    try:
        import s9_batch
    finally:
        sys.path.remove(str(CHRONO_SCRIPTS))
    return s9_batch


@pytest.fixture(scope="module")
def all_batches(sb):
    return sb.batches()


def test_bundle_sizes_and_unique_names(sb, all_batches) -> None:
    sizes = {name: len(all_batches[name]) for name in (
        sb.V5_T45_BATCH, sb.V5_T45LS_BATCH, sb.V5_R12_BATCH, sb.V5_REC_BATCH, sb.V5_V0V_BATCH,
        sb.V5_VB_BATCH, sb.V5_S6_SEED_BATCH, sb.V5_STAGE3_BATCH)}
    assert sizes == {"V5-T45": 12, "V5-T45LS": 6, "V5-R12": 3, "V5-REC": 2, "V5-V0V": 3, "V5-VB": 3,
                     "V5-S6SEED": 5, "V5-STAGE3": 34}
    names = [r["case"] for r in all_batches[sb.V5_STAGE3_BATCH]]
    assert len(set(names)) == 34


def test_rigid_rows_carry_their_setting_arguments(sb, all_batches) -> None:
    for name in (sb.V5_T45_BATCH, sb.V5_T45LS_BATCH, sb.V5_R12_BATCH, sb.V5_REC_BATCH):
        for row in all_batches[name]:
            argv = row["argv"]
            # criteria revision 8 3.1: VB and LS run final_C4G2_P3, V0 final_C4G2
            expected = "final_C4G2" if row["v5_setting"] == "V0" else "final_C4G2_P3"
            assert row["s8c"] and row["controller"] == expected
            assert ("--extend-start-tracked" in argv) == (row["v5_setting"] != "V0")
            assert argv[argv.index("--only") + 1] == row["s8c_case_id"]
            assert argv[argv.index("--tag") + 1] == f"v5s3_{row['v5_setting']}_{row['s8c_case_id']}"
            tail = argv[argv.index("--workers") + 2:]
            assert tail == sb.v5_rigid_argv(row["v5_setting"])
            assert "--valve-tau-s" not in argv
            if row["v5_setting"] == "V0":
                assert tail == []


def test_ls_values(sb, all_batches) -> None:
    for row in all_batches[sb.V5_T45LS_BATCH]:
        setting = row["v5_setting"]
        assert row["case"].endswith(f"_{setting}")
        ratio, delay = sb.V5_LS_ARGS[setting]
        argv = row["argv"]
        assert float(argv[argv.index("--lock-overlap-ratio") + 1]) == ratio
        assert float(argv[argv.index("--lock-closing-delay-s") + 1]) == delay


def test_v0v_rows_add_only_the_valve(sb, all_batches) -> None:
    vb = {r["case"]: r for r in all_batches[sb.V5_VB_BATCH]}
    for row in all_batches[sb.V5_V0V_BATCH]:
        base = vb[row["case"][: -len("_v0v")]]
        stored = base["argv"][: len(base["argv"]) - len(sb.v5_vb_argv())]
        # the VB row runs final_C4G2_P3; V0v keeps the stored controller (no ③ bound)
        stored = sb.with_expected_controller(stored, base["p3_base_controller"])
        assert row["argv"] == stored + ["--valve-tau-s", "0.1"]
        assert row["source_expected_diffs"] == {"valve_tau_s": 0.1}
        assert row["controller"] == base["p3_base_controller"] != "final_C4G2_P3"
        assert "--extend-start-tracked" not in row["argv"]
        assert base["argv"][base["argv"].index("--expect-controller") + 1] == "final_C4G2_P3"


def test_rigid_source_check_finds_a_wrong_argument(sb, all_batches) -> None:
    row = dict(all_batches[sb.V5_T45LS_BATCH][0])
    assert sb.v5_rigid_source_check(row)["status"] in ("ok", "no_source")
    argv = list(row["argv"])
    argv[argv.index("--lock-overlap-ratio") + 1] = "0.03"
    bad = sb.v5_rigid_source_check({**row, "argv": argv})
    assert bad["status"] == "differs"
    assert [d["key"] for d in bad["diffs"]] == ["lock_overlap_ratio"]
    v0 = next(r for r in all_batches[sb.V5_REC_BATCH] if r["v5_setting"] == "V0")
    extra = sb.v5_rigid_source_check({**v0, "argv": v0["argv"] + ["--rod-release-force"]})
    assert extra["status"] == "differs"


def test_new_rec_case_is_the_c72_case_with_the_phase_only(sb) -> None:
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    try:
        import run_S8C
    finally:
        sys.path.remove(str(CHRONO_SCRIPTS))
    table = run_S8C.case_table()
    new, old = table["G1R_FS24_FL_top_o050_Fs0"], table["G1R_FS24_FL_top_Fs0"]
    assert [c.case_id for c in run_S8C.case_set("v5rec")] == ["G1R_FS24_FL_top_o050_Fs0"]
    assert new.phase_offset_s == 0.050 and old.phase_offset_s == 0.025
    paths: list[str] = []

    def walk(x, y, path: str) -> None:
        if isinstance(x, dict) and isinstance(y, dict):
            for key in set(x) | set(y):
                walk(x.get(key), y.get(key), f"{path}.{key}")
        elif x != y:
            paths.append(path)

    walk(new.to_meta(), old.to_meta(), "")
    assert sorted(paths) == [".base.case_id", ".base.scenario.case_id", ".case_id", ".notes",
                             ".phase_offset_s"]
