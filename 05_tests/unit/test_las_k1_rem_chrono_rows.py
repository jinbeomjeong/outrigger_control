"""K1 re-measure (cad 2026-11-09): ``run_S9 level --k1-forced-block {off,first}`` and the batch ``V5-LAS-K1-REM``
(``04_scripts/02_chrono/las_k1_rem_chrono_rows.py``; rules ``las_k1_rules_adopt2.md`` 2.2 / 2.3 / 9.3).

No Chrono run. ``k1_forced_block.py`` (python-expert) is replaced by a stand-in module from ``tmp_path`` (a
``C2Controller`` subclass with ``module_sha256()``) placed in ``sys.modules``; a test against the real module runs only
when the file exists.
"""

from __future__ import annotations

import hashlib
import importlib.util
import pickle
import sys
from dataclasses import replace
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHRONO_SCRIPTS = PROJECT_ROOT / "04_scripts" / "02_chrono"
BATCH = "V5-LAS-K1-REM"
KEYS = ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "F1", "F2")
NAMES = {
    "R1": "REM_J2_B_top_Fs4_VB_gateoff", "R2": "REM_J2_B_middle_Fs4_VB_gateoff",
    "R3": "REM_J2_B_bottom_Fs4_VB_gateoff", "R4": "REM_J2_B_top_Fs4_m1p1_VB_gateoff",
    "R5": "REM_J2_B_top_Fs4_m1p1_V0_gateoff", "R6": "REM_J1_B_top_Fs4_m1p1_VB_gateoff",
    "R7": "REM_J2_B_top_Fs4_VB_gateon", "R8": "REM_J2_B_top_Fs4_m1p1_VB_gateon",
    "F1": "REM_J2_B_top_Fs4_VB_gateon_forced1", "F2": "REM_J2_B_top_Fs4_m1p1_VB_gateon_forced1",
}
"""Rules 2.2 / 2.3 case names."""

STAND_IN = '''"""Stand-in of 04_scripts/02_chrono/k1_forced_block.py for the unit tests."""
import hashlib
from pathlib import Path

from outrigger_sim.control.c2 import C2Controller


class K1ForcedBlockC2Controller(C2Controller):
    pass


def module_sha256():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
'''


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


@pytest.fixture()
def stand_in(tmp_path, monkeypatch):
    """``k1_forced_block`` stand-in in ``sys.modules`` (``run_S9.k1_forced_block_class`` imports it from there)."""
    p = tmp_path / "k1_forced_block.py"
    p.write_bytes(STAND_IN.replace("\n", "\r\n").encode("utf-8"))
    spec = importlib.util.spec_from_file_location("k1_forced_block", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setitem(sys.modules, "k1_forced_block", mod)
    return mod, p


def _level_args(run_s9, tokens: list[str]):
    return run_s9.build_parser().parse_args([*tokens, "--case", "x", "--out-root", "x"])


def _preset():
    from outrigger_sim.control.c2 import C2Config

    return C2Config().with_10hz_d1()


def _same_bits(a, b) -> bool:
    return a == b and pickle.dumps(a, protocol=4) == pickle.dumps(b, protocol=4) and repr(a) == repr(b)


def _exit_code(fn) -> int | None:
    with pytest.raises(SystemExit) as e:
        fn()
    return e.value.code


# ------------------------------------------------------------------------------- run_S9 level
OFF_RECORD = {"requested": "off", "class": "outrigger_sim.control.c2.C2Controller", "module_sha256": None}


def test_without_the_options_default_off_preset_bits_and_off_record(run_s9) -> None:
    """Rules 9.3: default ``off`` (args value ``"off"``), the preset config and ``C2Controller`` as before the option;
    the off record is written on every run."""
    from outrigger_sim.control.c2 import C2Controller

    args = _level_args(run_s9, ["level", "--soil", "J2"])
    assert args.k1_forced_block == "off" and not hasattr(args, "k1_order_gate")
    assert run_s9.k1_forced_block_of_args(args) == "off"
    config, meta = run_s9.level_c2_config_of_args(args)
    assert _same_bits(config, _preset())
    assert "k1_forced_block" not in meta and "k1_order_gate" not in meta  # run_level adds the record
    cls, rec = run_s9.level_controller_class(args)
    assert cls is C2Controller and rec == OFF_RECORD
    explicit = _level_args(run_s9, ["level", "--soil", "J2", "--k1-forced-block", "off"])
    assert vars(explicit) == vars(args)  # off given = off by default (no gate needed)
    assert _same_bits(run_s9.level_c2_config_of_args(explicit)[0], config)


def test_namespace_without_the_attribute_is_off(run_s9) -> None:
    """A namespace without the key (e.g. args rebuilt from a stored result.json before the option) reads as off."""
    import argparse

    assert run_s9.k1_forced_block_of_args(argparse.Namespace()) == "off"


def test_source_args_check_accepts_the_new_default(run_s9, tmp_path) -> None:
    """check-sources / stored-args reproduction: a former result.json without ``k1_forced_block`` still matches
    (a key absent from the former args must keep its parser default)."""
    import json

    tokens = ["level", "--soil", "J2", "--k1-order-gate", "off"]
    full = vars(_level_args(run_s9, tokens))
    old = {k: v for k, v in full.items() if k != "k1_forced_block"}
    (tmp_path / "result.json").write_text(json.dumps({"args": old}), "utf-8")
    assert run_s9.source_args_check(tokens, tmp_path)["status"] == "ok"
    chk = run_s9.source_args_check([*tokens[:3], "--k1-order-gate", "on", "--k1-forced-block", "first"], tmp_path)
    assert {d["key"] for d in chk["diffs"]} == {"k1_order_gate", "k1_forced_block"}


@pytest.mark.parametrize("gate", ["off", "on"])
def test_gate_rows_record_off_and_c2controller(run_s9, gate) -> None:
    """Judge rows R1 .. R8 give ``--k1-order-gate`` and no ``--k1-forced-block``: record ``off`` / C2Controller (K-6);
    the config is the gate config of the S-Ch option (unchanged by this option)."""
    from outrigger_sim.control.c2 import C2Controller

    args = _level_args(run_s9, ["level", "--soil", "J2", "--k1-order-gate", gate])
    config, meta = run_s9.level_c2_config_of_args(args)
    preset = _preset()
    want = replace(preset, slope_clearance_margin=replace(preset.slope_clearance_margin,
                                                          flat_soil_margin_order_gate=(gate == "on")))
    assert _same_bits(config, want)
    cls, rec = run_s9.level_controller_class(args)
    assert cls is C2Controller
    assert rec == OFF_RECORD
    assert args.k1_forced_block == "off"  # judge rows: args.k1_forced_block "off" (K-5)


@pytest.mark.parametrize("tokens", [["--k1-forced-block", "off"], ["--k1-forced-block", "off", "--k1-order-gate", "off"],
                                    ["--k1-forced-block", "off", "--k1-order-gate", "on"]])
def test_off_is_allowed_without_the_gate(run_s9, tokens) -> None:
    from outrigger_sim.control.c2 import C2Controller

    args = _level_args(run_s9, ["level", "--soil", "J2", *tokens])
    assert run_s9.k1_forced_block_of_args(args) == "off"
    run_s9.level_c2_config_of_args(args)
    assert run_s9.level_controller_class(args) == (C2Controller, OFF_RECORD)


@pytest.mark.parametrize("tokens", [
    ["--k1-forced-block", "first"],
    ["--k1-forced-block", "first", "--k1-order-gate", "off"],
])
def test_forced_first_without_gate_on_exits_2(run_s9, tokens) -> None:
    args = _level_args(run_s9, ["level", "--soil", "J2", *tokens])
    assert _exit_code(lambda: run_s9.k1_forced_block_of_args(args)) == 2
    assert _exit_code(lambda: run_s9.level_c2_config_of_args(args)) == 2
    assert _exit_code(lambda: run_s9.level_controller_class(args)) == 2


def test_bad_value_is_refused_by_argparse(run_s9) -> None:
    assert _exit_code(lambda: _level_args(run_s9, ["level", "--soil", "J2", "--k1-forced-block", "all"])) == 2


def test_forced_first_uses_the_subclass_same_config(run_s9, stand_in) -> None:
    mod, path = stand_in
    args = _level_args(run_s9, ["level", "--soil", "J2", "--k1-order-gate", "on", "--k1-forced-block", "first"])
    on = _level_args(run_s9, ["level", "--soil", "J2", "--k1-order-gate", "on"])
    config, meta = run_s9.level_c2_config_of_args(args)
    assert _same_bits(config, run_s9.level_c2_config_of_args(on)[0])
    assert "k1_forced_block" not in meta  # recorded by run_level from level_controller_class
    cls, rec = run_s9.level_controller_class(args)
    assert cls is mod.K1ForcedBlockC2Controller
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert rec == {"requested": "first", "class": "k1_forced_block.K1ForcedBlockC2Controller", "module_sha256": sha}
    assert b"\r\n" in path.read_bytes()  # the digest is of the raw (CRLF) bytes
    from outrigger_sim.control.c2 import C2Controller
    from outrigger_sim.params import load_params

    c2 = cls.from_params(load_params(level="top"), config)
    assert isinstance(c2, C2Controller) and type(c2) is cls
    assert c2.config.slope_clearance_margin.flat_soil_margin_order_gate is True


def test_forced_first_refuses_a_wrong_module(run_s9, stand_in, monkeypatch) -> None:
    mod, _ = stand_in
    args = _level_args(run_s9, ["level", "--soil", "J2", "--k1-order-gate", "on", "--k1-forced-block", "first"])
    monkeypatch.setattr(mod, "module_sha256", lambda: "0" * 64)
    assert _exit_code(lambda: run_s9.level_controller_class(args)) == 2
    monkeypatch.delattr(mod, "K1ForcedBlockC2Controller")
    assert _exit_code(lambda: run_s9.level_controller_class(args)) == 2


def test_run_level_order_class_before_build_and_from_params(run_s9) -> None:
    src = Path(run_s9.__file__).read_text(encoding="utf-8")
    i_cfg = src.index("config, c2_meta = level_c2_config_of_args(args)")
    i_expect = src.index('expect = getattr(args, "expect_controller", None)')
    i_cls = src.index('controller_cls, c2_meta["k1_forced_block"] = level_controller_class(args)')
    i_build = src.index("model = build_machine(args, params, pv, soil)", i_expect)  # the run_level build
    i_from = src.index("c2 = controller_cls.from_params(params_ctrl, config)")
    i_gate = src.index("k1_gate = k1_order_gate_of_args(args)")
    i_setup = src.index('c2_setup = {**c2_meta, "lifted_reapproach"')
    assert i_cfg < i_expect < i_cls < i_build < i_from < i_gate < i_setup
    assert "C2Controller.from_params(params_ctrl" not in src


@pytest.mark.skipif(not (CHRONO_SCRIPTS / "k1_forced_block.py").is_file(), reason="k1_forced_block.py not merged yet")
def test_real_module_resolves(run_s9) -> None:
    sys.modules.pop("k1_forced_block", None)
    args = _level_args(run_s9, ["level", "--soil", "J2", "--k1-order-gate", "on", "--k1-forced-block", "first"])
    cls, rec = run_s9.level_controller_class(args)
    assert cls.__name__ == "K1ForcedBlockC2Controller"
    sha = hashlib.sha256((CHRONO_SCRIPTS / "k1_forced_block.py").read_bytes()).hexdigest()
    assert rec == {"requested": "first", "class": "k1_forced_block.K1ForcedBlockC2Controller", "module_sha256": sha}
    from outrigger_sim.params import load_params

    config, _ = run_s9.level_c2_config_of_args(args)
    meta = cls.from_params(load_params(level="top"), config).meta()["k1_forced_block"]
    # the judge (rules 5 F-only items): controller_meta class == c2_setup class, module sha == K-2 sha
    assert meta["class"] == rec["class"] and meta["module_sha256"] == sha and meta["mode"] == "first"


# ------------------------------------------------------------------------------- batch rows
def test_ten_rows_names_and_fields(rows) -> None:
    by = {r["rem_key"]: r for r in rows}
    assert [r["rem_key"] for r in rows] == list(KEYS)
    assert {k: by[k]["case"] for k in KEYS} == NAMES
    for r in rows:
        assert r["group"] == BATCH and r["planned_pool"] == "pcore" and r["las_candidate"] == "P0"
        assert r["start_env"] == {"OMP_WAIT_POLICY": "PASSIVE", "OUTRIGGER_HULL_HOOK": "fast"}
        assert r["role"] == ("diag" if r["rem_key"].startswith("F") else "judge")
        assert r["est_s"] == (5500.0 if r["rem_mass_scale"] == 1.1 else 4400.0)
        argv = r["argv"]
        assert argv[argv.index("--k1-order-gate") + 1] == r["k1_order_gate"]
        assert argv[argv.index("--expect-controller") + 1] == r["controller"]
        assert (argv[argv.index("--k1-forced-block") + 1] if "--k1-forced-block" in argv else "off") \
            == r["k1_forced_block"]
        assert ("--mass-scale" in argv) is (r["rem_mass_scale"] == 1.1)
        if "--mass-scale" in argv:
            assert argv[argv.index("--mass-scale") + 1] == "1.1"
        assert "--soil-patch" not in argv and "--floor-roll" not in argv
    assert [by[k]["k1_order_gate"] for k in KEYS] == ["off"] * 6 + ["on"] * 4
    assert [by[k]["k1_forced_block"] for k in KEYS] == ["off"] * 8 + ["first"] * 2
    assert [by[k]["v5_setting"] for k in KEYS] == ["VB"] * 4 + ["V0"] + ["VB"] * 5
    assert by["R5"]["controller"] == "final_C4G2_LAS"
    assert all(by[k]["controller"] == "final_C4G2_P3_LAS" for k in KEYS if k != "R5")
    assert [(by[k]["soil"], by[k]["level"], by[k]["rem_mass_scale"]) for k in KEYS] == [
        ("J2", "top", 1.0), ("J2", "middle", 1.0), ("J2", "bottom", 1.0), ("J2", "top", 1.1), ("J2", "top", 1.1),
        ("J1", "top", 1.1), ("J2", "top", 1.0), ("J2", "top", 1.1), ("J2", "top", 1.0), ("J2", "top", 1.1)]
    assert by["R1"]["pair_set"] == [NAMES["R1"], NAMES["R7"], NAMES["F1"]] == by["F1"]["pair_set"]
    assert by["R4"]["pair_set"] == [NAMES["R4"], NAMES["R8"], NAMES["F2"]] == by["R8"]["pair_set"]
    assert by["R2"]["pair_set"] is None and by["R5"]["pair_case"] is None
    assert (by["R7"]["pair_case"], by["R8"]["pair_case"]) == (NAMES["R1"], NAMES["R4"])
    assert (by["F1"]["pair_case"], by["F2"]["pair_case"]) == (NAMES["R1"], NAMES["R4"])


def test_row_argv_is_the_defined_argv(rows, s9_batch) -> None:
    def head(soil, level, m, ctrl):
        out = ["level", "--soil", soil, "--pad-variant", "dwg_rear250", "--level", level, "--fs-kN", "4", "--grid",
               "0.01", "--crawler-grid", "0.04", "--settle-dashpot", "zrp", "--threads", "4", "--duration", "120",
               "--pressure-grade", "normal", "--imu-grade", "ideal", "--seed", "20261026"]
        return out + (["--mass-scale", "1.1"] if m == 1.1 else []) + ["--expect-controller", ctrl, "--approved"]

    for r in rows:
        want = head(r["soil"], r["level"], r["rem_mass_scale"], r["controller"])
        want += s9_batch.v5_vb_argv() if r["v5_setting"] == "VB" else []
        want += ["--k1-order-gate", r["k1_order_gate"]]
        want += ["--k1-forced-block", "first"] if r["k1_forced_block"] == "first" else []
        assert r["argv"][:len(s9_batch.RUN)] == s9_batch.RUN
        assert r["argv"][len(s9_batch.RUN):] == want


def _launch(r):
    return r["argv"] + ["--case", r["case"], "--out-root", "X"]


def _option_diff(a: list[str], b: list[str]) -> list[str]:
    """Options whose value differs or that one argv has and the other not (``--case`` included)."""
    def opts(v):
        out, i = {}, 0
        while i < len(v):
            if v[i].startswith("--"):
                j = i + 1
                vals = []
                while j < len(v) and not v[j].startswith("--"):
                    vals.append(v[j])
                    j += 1
                out[v[i]] = tuple(vals)
                i = j
            else:
                i += 1
        return out

    oa, ob = opts(a), opts(b)
    return sorted(k for k in set(oa) | set(ob) if oa.get(k) != ob.get(k))


@pytest.mark.parametrize("base,other,option", [
    ("R1", "R7", "--k1-order-gate"), ("R4", "R8", "--k1-order-gate"),
    ("R7", "F1", "--k1-forced-block"), ("R8", "F2", "--k1-forced-block"),
])
def test_pair_argv_differs_only_in_the_expected_token(rows, base, other, option) -> None:
    """Rules K-5: R1 <-> R7 / R4 <-> R8 differ in the ``--k1-order-gate`` value, R7 <-> F1 / R8 <-> F2 in
    ``--k1-forced-block first`` (appended), besides ``--case``."""
    by = {r["rem_key"]: r for r in rows}
    a, b = by[base], by[other]
    assert _option_diff(_launch(a), _launch(b)) == sorted([option, "--case"])
    assert _option_diff(a["argv"], b["argv"]) == [option]
    assert b["argv_base_case"] == a["case"] and b["argv_diff_option"] == option
    if option == "--k1-order-gate":
        assert len(a["argv"]) == len(b["argv"])
        d = [i for i, (x, y) in enumerate(zip(a["argv"], b["argv"], strict=True)) if x != y]
        assert [a["argv"][i] for i in d] == ["off"]
        assert [b["argv"][i] for i in d] == ["on"]
    else:
        assert b["argv"] == a["argv"] + ["--k1-forced-block", "first"]


def test_r4_r5_are_not_a_pair_and_differ_in_plant_and_tag(rows, s9_batch) -> None:
    by = {r["rem_key"]: r for r in rows}
    diff = set(_option_diff(by["R4"]["argv"], by["R5"]["argv"]))
    vb = {t for t in s9_batch.v5_vb_argv() if t.startswith("--")}
    assert diff == vb | {"--expect-controller"}


def test_argv_check_and_check_sources_dry(rows, s9_batch, stand_in) -> None:
    res = s9_batch.check_sources(BATCH, rows)
    assert res["ok"], [c for c in res["rows"] if c["status"] != "ok"]
    by = {c["rem_key"]: c for c in res["rows"]}
    assert [by[k]["status"] for k in KEYS] == ["ok"] * 10
    assert by["R5"]["expect_controller"] == {"name": "final_C4G2_LAS", "ok": True}
    assert by["R5"]["v5_options"] is False and by["R4"]["v5_options"] is True
    assert [by[k]["order_gate"] for k in KEYS] == [False] * 6 + [True] * 4
    assert [by[k]["k1_forced_block"]["requested"] for k in KEYS] == ["off"] * 8 + ["first"] * 2


def test_argv_check_flags_a_wrong_tag_and_missing_module(rows, s9_batch, monkeypatch) -> None:
    rem = _import("las_k1_rem_chrono_rows", CHRONO_SCRIPTS)
    r5 = dict(next(r for r in rows if r["rem_key"] == "R5"))
    r5["argv"] = s9_batch.with_expected_controller(r5["argv"], "final_C4G2_P3_LAS")
    r5["controller"] = "final_C4G2_P3_LAS"
    chk = rem.argv_check(r5, s9_batch)
    assert chk["status"] == "differs" and "controller_expectation" in [d["key"] for d in chk["diffs"]]
    monkeypatch.setitem(sys.modules, "k1_forced_block", None)  # import fails
    f1 = next(r for r in rows if r["rem_key"] == "F1")
    chk = rem.argv_check(f1, s9_batch)
    assert chk["status"] == "differs" and [d["key"] for d in chk["diffs"]] == ["controller_class"]


def test_list_and_check_sources_cli(s9_batch, stand_in, capsys) -> None:
    s9_batch.main(["list", BATCH])
    out = capsys.readouterr().out
    assert f"{BATCH} 10 rows" in out and all(n in out for n in NAMES.values())
    s9_batch.main(["check-sources", BATCH])
    assert capsys.readouterr().out.strip().splitlines()[-1] == "ok"


def test_batch_meta_keys_carry_the_row_keys(s9_batch) -> None:
    for k in ("rem_key", "role", "k1_forced_block", "pair_set", "argv_base_case", "argv_diff_option", "source_rows",
              "rem_mass_scale", "k1_order_gate", "k1_candidate", "pair_case", "v5_setting", "start_env",
              "planned_pool"):
        assert k in s9_batch.ENTRY_META_KEYS
