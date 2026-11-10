"""K-2 V-6 / V-7 Chrono runner definitions and the L1-R moving pad damping hook.

``04_scripts/02_chrono/k2_chrono_rows.py``, run_S6C / run_S8C ``--set k2_v6``, s9_batch
``k2_v7`` (``k2_touch_creep_rules.md`` 3.5 / 3.6 / 9.3); ``outrigger_sim.chrono.
moving_pad_damping``. No closed-loop Chrono run: parsers, configs, a built L1 model.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pytest

CHRONO_SCRIPTS = Path(__file__).resolve().parents[2] / "04_scripts" / "02_chrono"

V6_NAMES = (
    "K2_L1_top_fdown3.5_Fs0_off",
    "K2_L1_top_fdown3.5_Fs0_tcl",
    "K2_L1_top_k2pp025_Fs0_off",
    "K2_L1_top_k2pp025_Fs0_tcl",
    "K2_L2b_top_fdown3.5_Fs4_off",
    "K2_L2b_top_fdown3.5_Fs4_tcl",
    "K2_L2b_top_k2pp025_Fs4_off",
    "K2_L2b_top_k2pp025_Fs4_tcl",
)
"""``k2_judge.CHRONO_ROWS`` (rules 3.5 table)."""


def _import(name: str):
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(CHRONO_SCRIPTS))


@pytest.fixture(scope="module")
def s6c():
    pytest.importorskip("pychrono")
    return _import("run_S6C")


@pytest.fixture(scope="module")
def s8c():
    pytest.importorskip("pychrono")
    return _import("run_S8C")


@pytest.fixture(scope="module")
def k2c(s6c):
    return s6c.k2c


def _ns(**kw) -> argparse.Namespace:
    return argparse.Namespace(**kw)


# ------------------------------------------------------------------------------ row table
def test_rows_match_the_rules_table(k2c) -> None:
    assert tuple(r.name for r in k2c.V6_ROWS) == V6_NAMES
    assert [r.number for r in k2c.V6_ROWS] == list(range(1, 9))
    assert k2c.K2_FLOORS["k2pp025"] == (1.375, 2.625)
    for r in k2c.V6_ROWS:
        assert r.moving_damping is (r.engine == "L1R")
        assert r.fs_kN == (0.0 if r.engine == "L1R" else 4.0)
        assert r.expected_tag == ("final_C4G2_LAS_TCL" if r.arm == "on" else "final_C4G2_LAS")


def test_runner_sets(s6c, s8c) -> None:
    l1 = [c.case_id for c in s6c.CASE_SETS["k2_v6"]()]
    l2b = [c.case_id for c in s8c.case_set("k2_v6")]
    assert l1 == list(V6_NAMES[:4]) and l2b == list(V6_NAMES[4:])
    table = s6c.case_table()
    for cid in l1:
        c = table[cid]
        assert c.pad_zeta_moving == 0.1 and c.k1_order_gate is False and c.beta_GPa == 1.0
        assert c.k2_arm == ("on" if cid.endswith("_tcl") else "off")
    s8 = s8c.case_table()
    for cid in l2b:
        c = s8[cid]
        assert c.fs_kN == 4.0 and c.base.pad_zeta_moving is None and c.lock_valve == "pilot_check"
    assert s6c.st.FLOORS["k2pp025"] == (1.375, 2.625)
    assert table["K2_L1_top_fdown3.5_Fs0_off"].scenario.group == "G2-R"  # the C1_H4V scenario
    assert table["K2_L1_top_k2pp025_Fs0_off"].scenario.group == "D8"


def test_earlier_cases_keep_their_meta_and_repr(s6c, s8c) -> None:
    """New BundleCCase fields are repr=False / OPTIONAL_META: no earlier case gets a key."""
    new = ("k2_arm", "k1_order_gate", "pad_zeta_moving", "k2_row")
    for cid, c in s6c.case_table().items():
        if cid in V6_NAMES:
            continue
        meta = c.to_meta()
        assert not any(k in meta for k in new), cid
        assert not any(f"{k}=" in repr(c) for k in new), cid
    for cid, c in s8c.case_table().items():
        if cid not in V6_NAMES:
            assert c.base.k2_row is None


# ------------------------------------------------------------------------------ options
def _ok_args(arm: str, **kw):
    base = {
        "k2": arm,
        "k1_order_gate": "off",
        "expect_controller": {"off": "final_C4G2_LAS", "on": "final_C4G2_LAS_TCL"}[arm],
        "pad_zeta_moving": "0.1",
        "only": None,
    }
    base.update(kw)
    return _ns(**base)


@pytest.mark.parametrize("arm", ["off", "on"])
def test_select_rows_one_arm(k2c, arm) -> None:
    set_ids = list(V6_NAMES[:4])
    ids, rec = k2c.select_rows(_ok_args(arm), "L1R", set_ids)
    assert ids == [n for n in V6_NAMES[:4] if n.endswith("_tcl" if arm == "on" else "_off")]
    assert rec["k2"] == arm and rec["k1_order_gate"] is False and rec["pad_zeta_moving"] == 0.1
    ids2, _ = k2c.select_rows(_ok_args(arm, pad_zeta_moving="off"), "L2b", list(V6_NAMES[4:]))
    assert len(ids2) == 2


@pytest.mark.parametrize(
    "bad",
    [
        {"k2": "preset"},
        {"k1_order_gate": "on"},
        {"k1_order_gate": None},
        {"expect_controller": "final_C4G2_LAS_K1"},
        {"pad_zeta_moving": "off"},
        {"pad_zeta_moving": "0.2"},
        {"only": ["K2_L1_top_fdown3.5_Fs0_tcl"]},  # the other arm: mixing refused
        {"only": ["C1_H4V_top_fdown3.5"]},  # outside the set
    ],
)
def test_select_rows_refusals(k2c, bad) -> None:
    with pytest.raises(SystemExit):
        k2c.select_rows(_ok_args("off", **bad), "L1R", list(V6_NAMES[:4]))


def test_options_refused_outside_the_set(k2c) -> None:
    with pytest.raises(SystemExit):
        k2c.refuse_outside(_ns(k2="on"), "bundleC")
    with pytest.raises(SystemExit):
        k2c.refuse_outside(_ns(k1_order_gate="off"), "d8x_w1")
    with pytest.raises(SystemExit):
        k2c.refuse_outside(_ns(pad_zeta_moving="0.1"), "bundleC")
    k2c.refuse_outside(
        _ns(pad_zeta_moving="off", k1_order_gate="preset"), "bundleC"
    )  # defaults pass
    k2c.refuse_outside(_ns(), "bundleC")


def test_cli_parsers_accept_the_options(s6c, s8c) -> None:
    assert s8c.s6c.k2c is s6c.k2c
    for pad in (True, False):
        ap = argparse.ArgumentParser()
        s6c.k2c.add_arguments(ap, pad_zeta=pad)
        a = ap.parse_args([])
        assert not hasattr(a, "k2") and not hasattr(a, "k1_order_gate")
        a = ap.parse_args(["--k2", "on", "--k1-order-gate", "off"])
        assert a.k2 == "on" and a.k1_order_gate == "off"
        assert hasattr(a, "pad_zeta_moving") is pad


# ------------------------------------------------------------------------------ tags (I-10)
@pytest.mark.parametrize("arm", ["off", "on"])
def test_preflight_tags(s6c, s8c, arm) -> None:
    ids, rec = s6c.k2_preflight(_ok_args(arm), list(V6_NAMES[:4]))
    assert {v["controller_tag"] for v in rec["preflight"].values()} == {s6c.k2c.EXPECTED_TAG[arm]}
    ids, rec = s8c.k2_preflight(_ok_args(arm, pad_zeta_moving="off"), list(V6_NAMES[4:]))
    assert {v["controller_tag"] for v in rec["preflight"].values()} == {s6c.k2c.EXPECTED_TAG[arm]}
    assert all(v["k1_order_gate"] is False for v in rec["preflight"].values())


def test_preflight_refuses_a_wrong_config(k2c) -> None:
    from outrigger_sim.control.c2 import C2Config

    preset = C2Config().with_10hz_d1()  # K1 on, K-2 off: tag final_C4G2_LAS_K1
    with pytest.raises(SystemExit):
        k2c.preflight_record("K2_L1_top_fdown3.5_Fs0_off", preset, "final_C4G2_LAS_K1")
    cfg = k2c.apply_to_config(preset, k2_arm="on", k1_order_gate=False)
    with pytest.raises(SystemExit):  # an off row given the K-2 config
        k2c.preflight_record("K2_L1_top_fdown3.5_Fs0_off", cfg, "final_C4G2_LAS_TCL")
    assert k2c.preflight_record("K2_L1_top_fdown3.5_Fs0_tcl", cfg, "final_C4G2_LAS_TCL")[
        "touch_creep_latch"
    ]


def test_earlier_case_config_unchanged(s6c) -> None:
    """A case without K-2 fields builds the config of the preset path (no K-2 / K1 override)."""
    import pickle

    from outrigger_sim.params import load_params

    c = s6c.case_table()["C1_H4V_top_fdown3.5"]
    cfg = s6c.controller_config(load_params(level="top"), c)
    assert cfg.touch_creep_latch.enable is False
    assert (
        cfg.slope_clearance_margin.flat_soil_margin_order_gate is True
    )  # preset since the K1 switch
    k2 = s6c.case_table()["K2_L1_top_fdown3.5_Fs0_off"]
    cfg_off = s6c.controller_config(load_params(level="top"), k2)
    from dataclasses import replace

    assert pickle.dumps(
        replace(cfg_off, slope_clearance_margin=cfg.slope_clearance_margin)
    ) == pickle.dumps(cfg)


def test_mixed_batch_refused(s6c) -> None:
    with pytest.raises(SystemExit):
        s6c.run_batch(
            ["K2_L1_top_fdown3.5_Fs0_off", "K2_L1_top_fdown3.5_Fs0_tcl"],
            1,
            check=True,
            case_set="k2_v6",
            k2={"k2": "off", "expect_controller": "final_C4G2_LAS"},
        )
    with pytest.raises(SystemExit):  # K-2 rows without the record
        s6c.run_batch(["K2_L1_top_fdown3.5_Fs0_off"], 1, check=True, case_set="k2_v6")


# ------------------------------------------------------------------------------ damping hook
def test_open_fraction() -> None:
    from outrigger_sim.chrono.moving_pad_damping import open_fraction

    sw = [(1.0, 0, True), (2.0, 0, False), (3.0, 1, True)]
    assert open_fraction(sw, 0.0, 4.0, 2) == [0.25, 0.25]
    assert open_fraction(sw, 1.5, 3.5, 2) == [0.25, 0.25]
    assert open_fraction(sw, 2.0, 2.0, 2) is None


@pytest.fixture(scope="module")
def l1_model(s6c):
    from outrigger_sim.params import load_params

    params = load_params(level="top")
    model, _ = s6c.st.build_crawler_model(params, "fdown3.5", attach=False)
    return params, model


def test_hook_sets_cn_only_from_the_valve(l1_model) -> None:
    from outrigger_sim.chrono.moving_pad_damping import (
        MovingPadDamping,
        MovingPadDampingSettings,
        pad_materials,
    )

    params, model = l1_model
    mats = pad_materials(model)
    gn0 = [
        (float(s.GetGn()), float(p.GetGn()), float(s.GetKn()), float(s.GetKt()), float(s.GetGt()))
        for s, p in mats
    ]
    gn_yaml = [float(np.float32(v)) for v in params.contact.rigid_floor.L1.gn_per_pad_1_s]
    assert [g[0] for g in gn0] == gn_yaml and [g[1] for g in gn0] == gn_yaml
    s = MovingPadDampingSettings.from_params(params, 0.10)
    assert s.zeta_lock == 0.03 and s.lock_eps_m_s == 1e-6 and abs(s.factor - 0.10 / 0.03) < 1e-15
    hook = MovingPadDamping(model, s)
    c0 = np.array(model.rod_chamber._contact_damping, float)
    act = model.actuator
    act._valve_u[:] = [
        0.0,
        2e-6,
        1e-6,
        -5e-3,
    ]  # FR, RR open (|u| > 1e-6); RL at the threshold = LOCK
    hook(None)
    want_open = [False, True, False, True]
    for i, (sph, pat) in enumerate(mats):
        g = gn0[i][0] * (0.10 / 0.03) if want_open[i] else gn0[i][0]
        assert float(sph.GetGn()) == pytest.approx(g, rel=1e-6) and float(pat.GetGn()) == float(
            sph.GetGn()
        )
        assert (float(sph.GetKn()), float(sph.GetKt()), float(sph.GetGt())) == gn0[i][
            2:
        ]  # only g_n
        assert model.rod_chamber._contact_damping[i] == pytest.approx(
            c0[i] * (float(sph.GetGn()) / gn0[i][0]), rel=1e-12
        )
    act._valve_u[:] = 0.0
    hook(None)
    assert [float(m.GetGn()) for m, _ in mats] == gn_yaml
    assert np.array_equal(model.rod_chamber._contact_damping, c0)
    assert hook.meta()["n_switches"] == 4
    hook.restore_lock()


def test_v7_rows(s6c) -> None:
    sb = _import("s9_batch")
    rows = s6c.k2c.v7_rows(sb)
    assert [r["case"] for r in rows] == [
        "K2V7_P3b_J1_B_top_Fs4_off",
        "K2V7_P3b_J1_B_top_Fs4_tcl",
        "K2V7_P3b_J2_B_top_Fs4_off",
        "K2V7_P3b_J2_B_top_Fs4_tcl",
    ]
    for r in rows:
        argv = r["argv"]
        assert argv[argv.index("--expect-controller") + 1] == r["controller"]
        assert argv[-4:] == ["--k1-order-gate", "on", "--k2", r["k2_arm"]]  # V-7 K1 on (2026-11-10)
        assert r["controller"] == {"off": "final_C4G2_LAS_K1", "on": "final_C4G2_LAS_K1_TCL"}[r["k2_arm"]]
        assert r["k1_order_gate"] == "on"
        assert r["start_env"]["OMP_WAIT_POLICY"] == "PASSIVE"


def test_v7_configs_pass_their_tags(s6c) -> None:
    """V-7 build check (no Chrono): the level config with K1 on and the arm's K-2 passes the row tag."""
    sb = _import("s9_batch")
    for r in s6c.k2c.v7_rows(sb):
        chk = s6c.k2c.v7_argv_check(r)
        assert chk["status"] == "ok", chk
        assert chk["k1_order_gate"] is True and chk["touch_creep_latch"] is (r["k2_arm"] == "on")


def test_v6_tags_stay_k1_off(k2c) -> None:
    assert k2c.EXPECTED_TAG == {"off": "final_C4G2_LAS", "on": "final_C4G2_LAS_TCL"}
    assert k2c.K1_ORDER_GATE is False


def test_dhat_window_rule(k2c) -> None:
    """The k2_record.dhat_window_record rule on 1 ms chunks: window (t_touch - 0.3, t_touch], open = |u| > 1e-6,
    stroke gained from the last chunk at or before the window start."""
    t = np.round(np.arange(0.0, 1.0001, 0.001), 9)
    valves = np.zeros((t.size, 4))
    strokes = np.zeros((t.size, 4))
    valves[(t > 0.65) & (t <= 0.80), 1] = 2e-3  # FR open inside the window
    valves[(t > 0.10) & (t <= 0.69), 2] = 2e-3  # RL open before the window only
    valves[t > 0.70, 3] = 1e-6  # RR at the threshold = closed
    strokes[:, 1] = t * 2e-3  # FR 2 mm/s
    legs, mm = k2c.dhat_window_record(t, valves, strokes, 1.0)
    assert legs == ["FR"]
    assert mm[0] is None and mm[2] is None and mm[3] is None
    assert mm[1] == pytest.approx(0.6, abs=1e-9)  # 0.3 s x 2 mm/s
    assert k2c.dhat_window_record(t, valves, strokes, None) == (None, None)


def test_dhat_recorder_reads_only(l1_model, k2c) -> None:
    params, model = l1_model
    rec = k2c.DhatWindowRecorder(model)
    assert rec.every == 5  # 1 ms at dt 2e-4 s
    gn = [float(m.GetGn()) for m, _ in __import__(
        "outrigger_sim.chrono.moving_pad_damping", fromlist=["pad_materials"]).pad_materials(model)]
    model.actuator._valve_u[:] = [0.0, 3e-3, 0.0, -1e-3]
    for _ in range(5):
        rec(None)
    assert len(rec.t) == 1 and rec.valve[0].tolist() == [0.0, 3e-3, 0.0, 1e-3]
    model.actuator._valve_u[:] = 0.0
    assert [float(m.GetGn()) for m, _ in __import__(
        "outrigger_sim.chrono.moving_pad_damping", fromlist=["pad_materials"]).pad_materials(model)] == gn


def test_batch_identity_records(k2c, tmp_path) -> None:
    """batch_meta.json identity_start / identity_end: raw argv, cwd, git HEAD / status, env subset, affinity, the
    pychrono package and (end) every row's rc."""
    from types import SimpleNamespace

    start = k2c.batch_identity("start")
    for key in ("argv", "cwd", "pid", "git", "env", "affinity_mask", "pychrono", "utc"):
        assert key in start, key
    assert start["git"]["head"] and "status_porcelain" in start["git"]
    assert all(k.startswith(k2c.IDENTITY_ENV_PREFIXES) for k in start["env"])
    assert start["pychrono"] and start["pychrono"].startswith("pychrono-")
    outs = [SimpleNamespace(case_id="A", status="ok", exit_code=0, wall_s=1.0, case_dir=tmp_path / "A"),
            SimpleNamespace(case_id="B", status="failed", exit_code=3, wall_s=2.0, case_dir=tmp_path / "B")]
    end = k2c.batch_identity("end", outs)
    assert end["rows"]["B"]["exit_code"] == 3 and end["all_rc_zero"] is False


def test_batch_dir_option(k2c, tmp_path) -> None:
    assert k2c.batch_dir_of_args(_ns()) is None
    assert k2c.batch_dir_of_args(_ns(batch_dir=str(tmp_path / "new"))) == tmp_path / "new"
    with pytest.raises(SystemExit):  # an existing folder is refused
        k2c.batch_dir_of_args(_ns(batch_dir=str(tmp_path)))
    with pytest.raises(SystemExit):  # only with --set k2_v6
        k2c.refuse_outside(_ns(batch_dir=str(tmp_path / "x")), "bundleC")


def test_cost_rows(k2c) -> None:
    from types import SimpleNamespace

    rows = k2c.cost_rows("L1R", [SimpleNamespace(case_id="x")], lambda c: 93.0, lambda c: 177.0)
    assert rows == [{"case": "x", "sim_s": 93.0, "wall_p_s": 177.0, "wall_e_s": 20.0 + 6.5 * 93.0}]
