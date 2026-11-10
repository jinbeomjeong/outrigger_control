"""LAS-b K1 S-Ch (cad 2026-11-09): ``run_S9 level --k1-order-gate {off,on}`` and the batch
``V5-LAS-K1-CHRONO`` (``04_scripts/02_chrono/las_k1_chrono_rows.py``).

No Chrono run: the ``level`` arguments are parsed and the run-time C2 config is built as
``run_S9 level`` builds it before the model; the controller is built from it without a plant.
"""

from __future__ import annotations

import pickle
import sys
from dataclasses import replace
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHRONO_SCRIPTS = PROJECT_ROOT / "04_scripts" / "02_chrono"
COUPLED_DIR = PROJECT_ROOT / "04_scripts" / "04_hydraulic" / "coupled"
BATCH = "V5-LAS-K1-CHRONO"
HARNESS_KEY = "D1|H-S-A-J2|G1+J2@FL|T|flat|K1|VB|e0"


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


@pytest.fixture(scope="module")
def rows(s9_batch):
    return s9_batch.batches()[BATCH]


def _level_args(run_s9, tokens: list[str]):
    return run_s9.build_parser().parse_args([*tokens, "--case", "x", "--out-root", "x"])


def _preset():
    from outrigger_sim.control.c2 import C2Config

    return C2Config().with_10hz_d1()


def _same_bits(a, b) -> bool:
    return a == b and pickle.dumps(a, protocol=4) == pickle.dumps(b, protocol=4) and repr(a) == repr(b)


# ------------------------------------------------------------------------------- run_S9 level
def test_without_the_option_no_attribute_and_the_preset_bits(run_s9) -> None:
    """K1 switch (``las_k1_rules_adopt.md`` 9.1): absent = ``preset`` (no attribute, the preset value, gate on);
    the request and the effective gate are recorded on every run."""
    args = _level_args(run_s9, ["level", "--soil", "G1"])
    assert not hasattr(args, "k1_order_gate")
    assert run_s9.k1_order_gate_of_args(args) is None
    config, meta = run_s9.level_c2_config_of_args(args)
    assert _same_bits(config, _preset())
    assert config.slope_clearance_margin.flat_soil_margin_order_gate is True
    assert meta["k1_order_gate"] == "preset" and meta["k1_order_gate_effective"] is True


def test_explicit_preset_is_the_absent_option(run_s9) -> None:
    args = _level_args(run_s9, ["level", "--soil", "G1", "--k1-order-gate", "preset"])
    assert run_s9.k1_order_gate_of_args(args) is None
    config, meta = run_s9.level_c2_config_of_args(args)
    assert _same_bits(config, _preset())
    assert meta["k1_order_gate"] == "preset" and meta["k1_order_gate_effective"] is True


def test_off_changes_only_the_order_gate_and_records_it(run_s9) -> None:
    args = _level_args(run_s9, ["level", "--soil", "G1", "--k1-order-gate", "off"])
    config, meta = run_s9.level_c2_config_of_args(args)
    preset = _preset()
    assert config != preset
    assert config.slope_clearance_margin.flat_soil_margin_order_gate is False
    assert _same_bits(replace(config, slope_clearance_margin=replace(
        config.slope_clearance_margin, flat_soil_margin_order_gate=True)), preset)
    assert meta["k1_order_gate"] == "off" and meta["k1_order_gate_effective"] is False


def test_on_keeps_the_preset_bits_and_records_it(run_s9) -> None:
    """The wrapper ``on`` over the switched preset is idempotent (applied twice = once)."""
    args = _level_args(run_s9, ["level", "--soil", "G1", "--k1-order-gate", "on"])
    config, meta = run_s9.level_c2_config_of_args(args)
    assert _same_bits(config, _preset())
    assert config.slope_clearance_margin.flat_soil_margin_order_gate is True
    assert meta["k1_order_gate"] == "on" and meta["k1_order_gate_effective"] is True


def test_bad_value_is_refused(run_s9) -> None:
    with pytest.raises(SystemExit):
        _level_args(run_s9, ["level", "--soil", "G1", "--k1-order-gate", "maybe"])


def test_las_off_and_gate_compose(run_s9) -> None:
    from outrigger_sim.control.c2 import C2Config

    args = _level_args(run_s9, ["level", "--soil", "G1", "--las-off", "--k1-order-gate", "on"])
    config, meta = run_s9.level_c2_config_of_args(args)
    base = C2Config().with_10hz_d1(liftoff_approach_slow=False, flat_soil_margin_order_gate=False)
    assert config == replace(base, slope_clearance_margin=replace(base.slope_clearance_margin,
                                                                   flat_soil_margin_order_gate=True))
    assert meta["las_off"] is True and meta["k1_order_gate"] == "on"
    assert meta["k1_order_gate_effective"] is True


@pytest.mark.parametrize("gate", ["off", "on"])
def test_built_controller_holds_the_gate(run_s9, gate) -> None:
    """``run_level`` compares the built controller with the request (C2Controller.from_params keeps it)."""
    from outrigger_sim.control.c2 import C2Controller
    from outrigger_sim.params import load_params

    args = _level_args(run_s9, ["level", "--soil", "G1", "--k1-order-gate", gate])
    config, _ = run_s9.level_c2_config_of_args(args)
    c2 = C2Controller.from_params(load_params(level="top"), config)
    assert c2.config.slope_clearance_margin.flat_soil_margin_order_gate is (gate == "on")
    assert run_s9.k1_order_gate_of_args(args) is (gate == "on")
    source = Path(run_s9.__file__).read_text(encoding="utf-8")
    i_from = source.index("c2 = controller_cls.from_params(params_ctrl, config)")  # K1 re-measure: class by option
    i_check = source.index("k1_gate = k1_order_gate_of_args(args)")
    i_expect = source.index('expect = getattr(args, "expect_controller", None)')
    i_cfg = source.index("config, c2_meta = level_c2_config_of_args(args)")
    assert i_cfg < i_expect < i_from < i_check


# ------------------------------------------------------------------------------- batch rows
def test_two_rows_and_fields(rows) -> None:
    assert [r["case"] for r in rows] == ["SCh_G1_J2FL_B_top_Fs4_VB_gateoff", "SCh_G1_J2FL_B_top_Fs4_VB_gateon"]
    for r, gate, cand in zip(rows, ("off", "on"), ("K1off", "K1on")):
        assert r["start_env"] == {"OMP_WAIT_POLICY": "PASSIVE", "OUTRIGGER_HULL_HOOK": "fast"}
        assert r["planned_pool"] == "pcore" and r["controller"] == "final_C4G2_P3_LAS"
        assert r["las_candidate"] == "P0" and r["k1_candidate"] == cand and r["v5_setting"] == "VB"
        assert r["est_s"] == 12600.0 and r["harness_case"] == HARNESS_KEY
        assert r["k1_order_gate"] == gate
        argv = r["argv"]
        assert argv[argv.index("--k1-order-gate") + 1] == gate
    assert rows[0]["pair_case"] == rows[1]["case"] and rows[1]["pair_case"] == rows[0]["case"]


def test_row_argv_is_the_defined_dry_argv(rows, s9_batch) -> None:
    head = ["level", "--soil", "G1", "--pad-variant", "dwg_rear250", "--level", "top", "--fs-kN", "4", "--grid",
            "0.02", "--crawler-grid", "0.04", "--settle-dashpot", "zrp", "--threads", "4", "--duration", "200",
            "--pressure-grade", "normal", "--imu-grade", "ideal", "--seed", "20261026", "--soil-patch", "FL:J2",
            "--soil-patch-grid", "0.01", "--expect-controller", "final_C4G2_P3_LAS", "--approved"]
    for r in rows:
        assert r["argv"][:len(s9_batch.RUN)] == s9_batch.RUN
        assert r["argv"][len(s9_batch.RUN):] == head + s9_batch.v5_vb_argv() + ["--k1-order-gate", r["k1_order_gate"]]


def test_pair_differs_only_in_the_gate_and_the_case(rows) -> None:
    """The launch argv (row argv + ``--case`` / ``--out-root`` of ``s9_batch.run_batch``) of the two rows."""
    launch = [r["argv"] + ["--case", r["case"], "--out-root", "X"] for r in rows]
    assert len(launch[0]) == len(launch[1])
    diff = [i for i, (a, b) in enumerate(zip(*launch)) if a != b]
    assert [launch[0][i - 1] for i in diff] == ["--k1-order-gate", "--case"]
    row_diff = [i for i, (a, b) in enumerate(zip(rows[0]["argv"], rows[1]["argv"])) if a != b]
    assert [rows[0]["argv"][i - 1] for i in row_diff] == ["--k1-order-gate"]


def test_argv_check_ok_and_check_sources(rows, s9_batch) -> None:
    """Since the K1 switch (``las_k1_rules_adopt.md`` 9.2) ``final_C4G2_P3_LAS`` checks the order gate off: the
    gate-off row still passes, the gate-on row (a result before the switch under the old tag) is refused loudly at
    that path only."""
    res = s9_batch.check_sources(BATCH, rows)
    assert not res["ok"], res
    assert [c["status"] for c in res["rows"]] == ["ok", "differs"]
    assert [c["order_gate"] for c in res["rows"]] == [False, True]
    (diff,) = res["rows"][1]["diffs"]
    assert diff["key"] == "controller_expectation"
    assert [c["path"] for c in diff["row"]] == ["slope_clearance_margin.flat_soil_margin_order_gate"]


def test_harness_key_matches_the_d1_row() -> None:
    """``d1_rows`` H-S-A-J2: G1 + J2@FL, top, flat, crawler x1; pad B and F_s 4 kN (module constants of the g6
    path, ``d1_runs._run_g6`` key ``d1|G1+J2@FL|top|Fs4`` = pad B in ``r72_g6_screen.pad_of_key``)."""
    d1 = _import("d1_rows", COUPLED_DIR)
    row = next(r for r in d1.all_rows() if r.group == "H-S-A-J2")
    assert row.key == "D1|H-S-A-J2|G1+J2@FL|T|flat|K1"
    assert HARNESS_KEY.startswith(row.key + "|")
    assert (row.base, row.patch_soil, row.patch_leg, row.level, row.crawler_k_scale) == ("G1", "J2", "FL", "top", 1.0)
    assert row.path == "g6" and (row.roll_deg, row.pitch_deg) == (0.0, 0.0)
    assert d1.PAD == "B" and d1.FS_KN == 4.0
