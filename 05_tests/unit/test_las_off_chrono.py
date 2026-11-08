"""LAS-b switch on the Chrono runners (spec 436.9, delegation W-4): ``--las-off`` of ``run_S9
level`` / ``run_S8C run``, the ``s9_batch run --las-off`` rows, the LAS tags of the V0v / S6SEED
and D-1 rows, and the ``chrono_t45_replay`` of a ``_LAS`` row (v5 criteria revision 11 #5).

No Chrono run: the ``level`` arguments are parsed and the run-time C2 config is built as
``run_S9 level`` builds it before the model; the replay test uses a stored stage 3 VB record
(``07_results``, git-ignored; skipped when absent) copied with a ``_LAS`` tag.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHRONO_SCRIPTS = PROJECT_ROOT / "04_scripts" / "02_chrono"
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
VB_STAGE3_RECORD = (PROJECT_ROOT / "07_results" / "S8" / "v5s3_VB_E_G4_Fs4_20261107_194230"
                    / "E_G4_Fs4")
"""Stage 3 VB event row (``final_C4G2_P3``), stored (as ``test_chrono_t45_replay``)."""
LAS_TAG_OF = {"final_C4G2": "final_C4G2_LAS", "final_C4G2_P3": "final_C4G2_P3_LAS"}


def _import(name: str, folder: Path):
    sys.path.insert(0, str(folder))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(folder))


@pytest.fixture(scope="module")
def run_s9():
    pytest.importorskip("pychrono")
    return _import("run_S9", CHRONO_SCRIPTS)


@pytest.fixture(scope="module")
def s9_batch():
    pytest.importorskip("pychrono")
    return _import("s9_batch", CHRONO_SCRIPTS)


def _level_args(run_s9, tokens: list[str]):
    return run_s9.build_parser().parse_args([*tokens, "--case", "x", "--out-root", "x"])


def _runtime_config(run_s9, args):
    """The C2 config ``run_S9 level`` checks with ``--expect-controller`` (before the model)."""
    from outrigger_sim.hydraulics.v5_options import apply_controller_options
    from outrigger_sim.params import load_params

    config, meta = run_s9.level_c2_config_of_args(args)
    options = run_s9.v5_hydraulic_options(args, load_params(model="L2b_NSC"))
    if options is not None:
        config = apply_controller_options(config, options, load_params().actuator.max_speed_m_s,
                                          options.valve_tau_s)
    return config, meta


def _with_tag(tokens: list[str], tag: str) -> list[str]:
    out = list(tokens)
    out[out.index("--expect-controller") + 1] = tag
    return out


# ------------------------------------------------------------------------------- run_S9 level
def test_without_las_off_the_preset_and_its_meta_stay(run_s9) -> None:
    args = _level_args(run_s9, ["level", "--soil", "J1"])
    assert not hasattr(args, "las_off")
    assert run_s9.las_off_config(args) is None
    config, meta = run_s9.level_c2_config_of_args(args)
    assert config.liftoff_approach_slow.enable
    assert meta["preset"] == "C2Config().with_10hz_d1()" and "las_off" not in meta


def test_las_off_builds_the_pre_switch_preset_and_records_it(run_s9) -> None:
    from outrigger_sim.control.c2 import C2Config

    args = _level_args(run_s9, ["level", "--soil", "J1", "--las-off"])
    config, meta = run_s9.level_c2_config_of_args(args)
    assert config == C2Config().with_10hz_d1(liftoff_approach_slow=False)
    assert meta["preset"] == run_s9.LAS_OFF_PRESET and meta["las_off"] is True
    assert run_s9.controller_expectation(config, run_s9.FINAL_CONTROLLER)["ok"]
    assert not run_s9.controller_expectation(config, run_s9.FINAL_LAS_CONTROLLER)["ok"]
    assert "las_off" in run_s9.SOURCE_ARGS_IGNORE


def _level_tokens(row: dict) -> list[str]:
    argv = row["argv"]
    return argv[argv.index("level"):]


@pytest.mark.parametrize("batch_name", ["V5_V0V_BATCH", "V5_S6_SEED_BATCH"])
def test_las_tags_pass_the_controller_check_of_the_v0v_and_s6seed_rows(
        run_s9, s9_batch, batch_name) -> None:
    """W-4: ``level --expect-controller final_C4G2_LAS`` / ``final_C4G2_P3_LAS`` is accepted
    on the run-time (switched) preset; the stored tag needs ``--las-off``."""
    rows = [row for row in s9_batch.batches()[getattr(s9_batch, batch_name)]
            if "--expect-controller" in row["argv"]]
    assert rows
    for row in rows:
        tokens = _level_tokens(row)
        stored_tag = tokens[tokens.index("--expect-controller") + 1]
        las_tag = LAS_TAG_OF[stored_tag]
        las_args = _level_args(run_s9, _with_tag(tokens, las_tag))
        assert las_args.expect_controller == las_tag
        config, _ = _runtime_config(run_s9, las_args)
        assert run_s9.controller_expectation(config, las_tag)["ok"], row["case"]
        assert not run_s9.controller_expectation(config, stored_tag)["ok"], row["case"]
        old_args = _level_args(run_s9, s9_batch.with_las_off(row, tokens))
        old_config, _ = _runtime_config(run_s9, old_args)
        assert run_s9.controller_expectation(old_config, stored_tag)["ok"], row["case"]


# ------------------------------------------------------------------------------- s9_batch
def test_batch_las_off_touches_only_pre_switch_rows(s9_batch) -> None:
    level = {"case": "a", "controller": "final_C4G2_P3", "argv": ["level"]}
    assert s9_batch.with_las_off(level, level["argv"]) == ["level", "--las-off"]
    assert s9_batch.with_las_off(level, ["level", "--las-off"]) == ["level", "--las-off"]
    las = {"case": "b", "controller": "final_C4G2_P3_LAS", "argv": ["level"]}
    assert s9_batch.with_las_off(las, las["argv"]) == ["level"]
    untagged = {"case": "c", "argv": ["level"]}
    assert s9_batch.with_las_off(untagged, untagged["argv"]) == ["level"]
    with pytest.raises(SystemExit, match="run_S6C"):
        s9_batch.with_las_off({"case": "d", "controller": "final_C4G2", "s6c": True}, ["run"])


def test_d1_rows_expect_the_las_tags(s9_batch) -> None:
    rows = s9_batch.batches()["D1-CHRONO"]
    soil = [row for row in rows if "--expect-controller" in row["argv"]]
    assert soil and all(row["controller"] == "final_C4G2_P3_LAS" for row in soil)
    assert all(row["argv"][row["argv"].index("--expect-controller") + 1] == "final_C4G2_P3_LAS"
               for row in soil)
    rigid = [row for row in rows if row.get("engine") == "L2b_NSC"]
    assert rigid and all(row["controller"] == "final_C4G2_P3_LAS" for row in rigid)


# ------------------------------------------------------------------------------- run_S8C
def test_run_s8c_las_off_gives_the_preset_keyword_block() -> None:
    pytest.importorskip("pychrono")
    from outrigger_sim.control.c2 import C2Config

    run_s8c = _import("run_S8C", CHRONO_SCRIPTS)
    switched = C2Config().with_10hz_d1()
    assert switched.liftoff_approach_slow.enable
    assert run_s8c.with_las_off(switched) == C2Config().with_10hz_d1(liftoff_approach_slow=False)


# ------------------------------------------------------------------------------- replay
@pytest.fixture(scope="module")
def t45():
    """``chrono_t45_replay`` with its folder on the path while the tests run (lazy imports)."""
    sys.path.insert(0, str(COUPLED_DIR))
    try:
        yield __import__("chrono_t45_replay")
    finally:
        sys.path.remove(str(COUPLED_DIR))


@pytest.mark.skipif(not VB_STAGE3_RECORD.is_dir(), reason="stored stage 3 VB record not present")
def test_t45_replay_of_a_las_row_rebuilds_las_on_and_gives_t4_t5(t45, tmp_path) -> None:
    """v5 criteria revision 11 #5: a ``_LAS`` row replays its monitor with LAS-b on and gives
    T4 / T5; J-P3 is expected (``EXTEND_START_TAGS``)."""
    case = tmp_path / VB_STAGE3_RECORD.name
    shutil.copytree(VB_STAGE3_RECORD, case)
    result_path = case / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["v5_hydraulics"]["controller_tag"] = "final_C4G2_P3_LAS"
    result_path.write_text(json.dumps(result), encoding="utf-8")
    record = t45.load_case(case)
    assert record.config.liftoff_approach_slow.enable
    row = t45.replay_case(case, with_t5=True)
    assert row["p3_expected"] is True
    assert row["settings_equal"] and row["t4_0"], row.get("setting_differences")
    assert "T4" in row and "T5" in row
    stored = t45.replay_case(VB_STAGE3_RECORD, with_t5=True)
    assert row["T4"] == stored["T4"] and row["T5"] == stored["T5"]  # the monitor has no LAS-b
