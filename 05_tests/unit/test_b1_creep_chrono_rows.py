"""B1 creep basis (cad 2026-11-12): ``run_S9 level --b1-grid-record {full,window}``
(``03_src/outrigger_sim/chrono/b1_grid_record.py``) and the batches ``V5-B1-CREEP`` / ``V5-B1-CREEP-WIN`` /
``V5-B1-CREEP-GS`` (``04_scripts/02_chrono/b1_creep_chrono_rows.py``; rules
``b1_creep_rules.md`` (sealed) sha256 ``6b99702c`` 1.4 / 2.1 / 2.3 / 6).

No Chrono run: argv / config checks, the window rule and the recorder on stand-in model / controller objects.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHRONO_SCRIPTS = PROJECT_ROOT / "04_scripts" / "02_chrono"
BATCH, WIN, GS = "V5-B1-CREEP", "V5-B1-CREEP-WIN", "V5-B1-CREEP-GS"
NAMES = {  # rules 2.1 table, written out here
    "C1": "B1_J2_B_bottom_Fs4_VB_fdown", "C2": "B1_J2_B_middle_Fs4_VB_fdown", "C3": "B1_J2_B_top_Fs4_VB_fdown",
    "C4": "B1_J2_B_bottom_Fs4_VB_diag", "C5": "B1_J2_B_top_Fs4_VB_fup", "C6": "B1_J2_B_bottom_Fs4_m1p1_VB_fdown"}
FLOOR = {"C1": ("0", "2.8"), "C2": ("0", "2.8"), "C3": ("0", "2.8"), "C4": ("1.925", "1.4"), "C5": ("0", "-2.8"),
         "C6": ("0", "2.8")}
LEVEL = {"C1": "bottom", "C2": "middle", "C3": "top", "C4": "bottom", "C5": "top", "C6": "bottom"}


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
def b1(s9_batch):
    return _import("b1_creep_chrono_rows", CHRONO_SCRIPTS)


@pytest.fixture(scope="module")
def all_batches(s9_batch):
    return s9_batch.batches()


def _opt(argv, name):
    i = argv.index(name)
    return argv[i + 1]


def _level(argv):
    return argv[argv.index("level"):]


# ------------------------------------------------------------------------------------------------ rows
def test_rows_names_values(all_batches):
    rows = all_batches[BATCH]
    assert [r["b1_id"] for r in rows] == list(NAMES)
    for r in rows:
        lv = _level(r["argv"])
        rid = r["b1_id"]
        assert r["case"] == NAMES[rid]
        assert _opt(lv, "--soil") == "J2" and _opt(lv, "--pad-variant") == "dwg_rear250"
        assert _opt(lv, "--level") == LEVEL[rid]
        assert (_opt(lv, "--floor-roll"), _opt(lv, "--floor-pitch")) == FLOOR[rid]
        assert _opt(lv, "--grid") == "0.01" and _opt(lv, "--crawler-grid") == "0.04"
        assert _opt(lv, "--threads") == "4" and _opt(lv, "--settle-dashpot") == "zrp"
        assert _opt(lv, "--start-limit") == "record_only"
        assert _opt(lv, "--pressure-grade") == "normal" and _opt(lv, "--imu-grade") == "ideal"
        assert _opt(lv, "--fs-kN") == "4"
        assert _opt(lv, "--duration") == ("180" if rid == "C6" else "160")
        assert ("--mass-scale" in lv) is (rid == "C6")
        if rid == "C6":
            assert _opt(lv, "--mass-scale") == "1.1"
        assert lv.count("--expect-controller") == 1
        assert _opt(lv, "--expect-controller") == "final_C4G2_P3_LAS_K1"  # not v5_vb_rows' final_C4G2_P3
        assert _opt(lv, "--b1-grid-record") == "full"
        assert r["start_env"] == {"OMP_WAIT_POLICY": "PASSIVE"}
        for bad in ("--k1-order-gate", "--las-off", "--k2", "--las-candidate", "--soil-patch", "--rigid-base"):
            assert bad not in lv


def test_vb_tail_is_v5_vb_argv(all_batches, s9_batch):
    vb = s9_batch.v5_vb_argv()
    for r in all_batches[BATCH]:
        lv = _level(r["argv"])
        assert lv[-(len(vb) + 2):-2] == vb
        assert lv[-2:] == ["--expect-controller", "final_C4G2_P3_LAS_K1"]


def test_gs_and_window_forms(all_batches):
    judge = {r["b1_id"]: r for r in all_batches[BATCH]}
    gs = all_batches[GS]
    assert [r["b1_id"] for r in gs] == ["C1", "C6"]
    for r in gs:
        a, b = _level(r["argv"]), _level(judge[r["b1_id"]]["argv"])
        assert _opt(a, "--duration") == "10"
        a2 = list(a)
        a2[a2.index("--duration") + 1] = _opt(b, "--duration")
        assert a2 == b
    for r in all_batches[WIN]:
        a, b = _level(r["argv"]), _level(judge[r["b1_id"]]["argv"])
        assert _opt(a, "--b1-grid-record") == "window"
        a2 = list(a)
        a2[a2.index("--b1-grid-record") + 1] = "full"
        assert a2 == b


def test_argv_check_ok_and_negative(all_batches, s9_batch, b1):
    for r in all_batches[BATCH] + all_batches[GS]:
        c = b1.argv_check(r, s9_batch)
        assert c["status"] == "ok", c
        assert c["expect_controller"] == {"name": "final_C4G2_P3_LAS_K1", "ok": True}
    r = dict(all_batches[BATCH][0])
    r["argv"] = s9_batch.with_expected_controller(r["argv"], "final_C4G2_P3")
    assert b1.argv_check(r, s9_batch)["status"] == "differs"
    assert b1.batch_check(all_batches[BATCH], BATCH)["status"] == "ok"
    assert b1.batch_check(all_batches[GS], GS)["status"] == "ok"


def test_option_absent_no_attribute(run_s9, all_batches):
    lv = _level(all_batches[BATCH][0]["argv"])
    i = lv.index("--b1-grid-record")
    a = run_s9.build_parser().parse_args(lv[:i] + lv[i + 2:])
    assert not hasattr(a, "b1_grid_record")
    with pytest.raises(SystemExit):
        run_s9.build_parser().parse_args(lv[:i] + ["--b1-grid-record", "every"] + lv[i + 2:])


def test_start_limit_record_only_overrides(run_s9, all_batches):
    a = run_s9.build_parser().parse_args(_level(all_batches[BATCH][0]["argv"]))
    _, rec = run_s9.apply_start_limit(run_s9.level_c2_config_of_args(a)[0], "record_only", a.level)
    assert list(rec["overrides"]) == ["target.acceptance"]


# ------------------------------------------------------------------------------------------------ window rule
@pytest.fixture(scope="module")
def gr():
    sys.path.insert(0, str(PROJECT_ROOT / "03_src"))
    try:
        from outrigger_sim.chrono import b1_grid_record
    finally:
        sys.path.remove(str(PROJECT_ROOT / "03_src"))
    return b1_grid_record


def test_window_set(gr):
    # LOC at n 200, last rise n 300, READY n 500
    w = [n for n in range(0, 800) if gr.in_rule_window(n, 200, 300, 500)]
    assert set(range(190, 321)) <= set(w) and set(range(490, 511)) <= set(w)
    assert 321 not in w and 489 not in w and 330 in w and 511 not in w and 520 in w
    assert gr.in_rule_window(195, None, None, None) is False
    assert gr.in_rule_window(195, 200, None, None) is True  # no rise yet: [n_L1 - 10, n_L1 + 20]


def test_may_skip(gr):
    assert not gr.may_skip(400, None, None, None)
    assert not gr.may_skip(400, 200, 300, None)  # READY not seen yet
    assert not gr.may_skip(505, 200, 300, 500)  # READY + 1 s
    assert not gr.may_skip(315, 200, 300, 290)  # rise + 2 s
    assert not gr.may_skip(520, 200, 300, 500)  # 1 s grid
    assert gr.may_skip(521, 200, 300, 500)
    for n in range(0, 800):  # a skippable cycle is never in the window of the same event cycles
        if gr.may_skip(n, 200, 300, 500):
            assert not gr.in_rule_window(n, 200, 300, 500)


# ------------------------------------------------------------------------------------------------ recorder
class _V:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = float(x), float(y), float(z)


class _Pad:
    def __init__(self, i):
        self.p = np.array([1.0 + i, 2.0 * i, 0.5])

    def TransformPointLocalToParent(self, v):  # noqa: N802
        return _V(self.p[0] + v.x, self.p[1] + v.y, self.p[2] + v.z)

    def GetPos(self):  # noqa: N802
        return _V(*self.p)

    def TransformDirectionLocalToParent(self, v):  # noqa: N802 - 90 deg yaw
        return _V(-v.y, v.x, v.z)


class _Model:
    def __init__(self):
        self.pads = tuple(_Pad(i) for i in range(4))
        self.plane_point_world_m = np.zeros(3)
        self.plane_rot = np.eye(3)
        self.pad_bottom_local_pad_m = [np.array([0.0, 0.0, -0.1])] * 4
        sq = np.array([[0, 0, -0.1], [0.3, 0, -0.1], [0.3, 0.3, -0.1], [0, 0.3, -0.1]], float)
        self.pad_outline_local_m = [sq] * 4
        self.pad_grid_by_leg_m = (0.01,) * 4
        self.pad_terrain_by_leg = (object(),) * 4
        self.calls = 0

    def pad_node_stats(self):
        self.calls += 1
        st = {"n_inside": 900, "n_contact": 880, "n_sigma_negative": 0, "contact_hull_area_m2": 0.088,
              "contact_hull_perimeter_m": 1.18, "sinkage_geometric_m": 0.09, "sigma_sum_area_N": 7.0e4,
              "sinkage_mean_contact_m": 0.091}
        return [dict(st) for _ in range(4)]


class _Geom:
    def clearance_corners_m(self, rod):  # corner k = 0.01 k + mean rod stroke
        return np.array([0.01 * k + float(np.mean(rod)) for k in range(4)])


class _Ctl:
    """Stand-in with the controller members R-C1 reads (state after the update, pure methods)."""

    def __init__(self, bias=None, soil_enable=True):
        self.events, self.phase = [], "C2Phase.LEVEL"
        soil = None if bias is None else SimpleNamespace(corner_bias_m=np.asarray(bias, float),
                                                         has_corner_bias=bool(np.any(np.asarray(bias) != 0.0)))
        self._state = SimpleNamespace(period_raw_tilts=[], last_forces=None, last_reading=None, soil=soil)
        self.geometry = _Geom()
        self.config = SimpleNamespace(soil=SimpleNamespace(enable=soil_enable))
        self.soil_state_calls = 0

    def _clearance_target_m(self):  # noqa: PLR6301
        return 0.08

    def _period_raw_attitude_rad(self):
        tl = self._state.period_raw_tilts
        return (float(np.mean([t.roll_rad for t in tl])), float(np.mean([t.pitch_rad for t in tl])))

    def _soil_state(self):  # must not be called (it would create the soil state)
        self.soil_state_calls += 1
        raise AssertionError("_soil_state called")


def _drive(gr, mode, n_end=800, ctl=None):
    m, c = _Model(), (_Ctl() if ctl is None else ctl)
    rec = gr.B1GridRecorder(m, c, mode)
    stroke = np.zeros(4)
    outs = {}
    for n in range(1, n_end):
        t = n * 0.1
        if n == 200:
            c.events.append(SimpleNamespace(t_s=t, name="crawler_liftoff_confirmed"))
        if 200 <= n <= 300:
            stroke = stroke + 1e-4
        if n == 500:
            c.phase = "C2Phase.READY"
        c._state.period_raw_tilts = [SimpleNamespace(t_s=t - (9 - k) * 0.01, roll_rad=1e-3, pitch_rad=-2e-3)
                                     for k in range(10)]
        if n == 400:  # an update without new IMU samples: kept list, no duplicate rows
            c._state.period_raw_tilts = list(c._state.period_raw_tilts)
        if n >= 2:  # the first instant has no reading yet (R-C1 NaN)
            c._state.last_forces = SimpleNamespace(nominal=np.array([1.0e5, 1.1e5, 0.9e5, 0.8e5]) + n)
            c._state.last_reading = SimpleNamespace(rod_stroke_m=stroke + 0.3)
        meas = SimpleNamespace(t_s=t, stroke_m=stroke.copy(),
                               imu_specific_force_samples_m_s2=np.tile([0.0, 0.0, 9.81], (10, 1)))
        outs[n] = rec.pad_nodes(meas)
    return m, rec, outs


def test_recorder_full(gr, tmp_path):
    m, rec, outs = _drive(gr, "full")
    assert m.calls == 799 and all(v is not None for v in outs.values())
    meta = rec.save(tmp_path / gr.B1_GRID_RECORD_NAME)
    assert meta["window_cycles"] == {"n_loc1": 200, "n_up": 300, "n_ready": 500}
    with np.load(tmp_path / gr.B1_GRID_RECORD_NAME) as z:
        assert z["n_cycle"].tolist() == list(range(1, 800))
        assert z["n_contact"].shape == (799, 4) and z["computed"].all()
        assert z["pad_bottom_centre_plane_xy_m"].shape == (799, 4, 2)
        assert np.allclose(z["pad_yaw_plane_rad"], math.pi / 2)
        assert np.allclose(z["pad_bottom_centre_world_m"][0, 1], [2.0, 2.0, 0.4])
        assert z["imu_t_s"].size == 7990 and np.all(np.diff(z["imu_t_s"]) > 0)
        assert z["imu_specific_force_m_s2"].shape == (7990, 3)
    assert meta["static"]["pads"][0]["b_poly_m"] == pytest.approx(2 * 0.09 / 1.2)
    json.dumps(meta)


def test_recorder_window(gr, tmp_path):
    m, rec, outs = _drive(gr, "window")
    skipped = [n for n, v in outs.items() if v is None]
    assert skipped and min(skipped) == 511 and all(n % 10 for n in skipped)
    assert m.calls + len(skipped) == 799
    rec.save(tmp_path / "w.npz")
    with np.load(tmp_path / "w.npz") as z:
        stored = z["n_cycle"].tolist()
        assert stored == [n for n in range(1, 800) if gr.in_rule_window(n, 200, 300, 500)]
        assert z["computed"].all()  # no late stroke rise: every stored cycle computed
        assert (z["n_contact"] >= 0).all()


def test_recorder_bad_mode(gr):
    with pytest.raises(ValueError):
        gr.B1GridRecorder(_Model(), _Ctl(), "every")


def test_field_check_missing_folder(b1, tmp_path):
    out = b1.field_check(tmp_path, GS)
    assert out["ok"] is False and out["n_ok"] == 0


# ------------------------------------------------------------------------------------------------ R-C1 (sealed 6)
R_C1 = {"n": (799,), "load_read_N": (799, 4), "att_raw_rad": (799, 2), "c_hat_m": (799,),
        "c_hat_corner_m": (799, 4), "c_target_m": (799,)}
"""Sealed rules 6 R-C1 names and shapes, written out here."""


@pytest.mark.parametrize("bias", [None, [0.0, 0.0, 0.0, 0.0], [0.001, -0.002, 0.0, 0.003]])
def test_r_c1_keys_values(gr, b1, tmp_path, bias):
    ctl = _Ctl(bias=bias)
    _, rec, _ = _drive(gr, "full", ctl=ctl)
    meta = rec.save(tmp_path / "record" / gr.B1_GRID_RECORD_NAME)
    assert meta["file"] == "record/b1_grid_record.npz" == gr.B1_GRID_RECORD_REL
    assert ctl.soil_state_calls == 0
    with np.load(tmp_path / "record" / gr.B1_GRID_RECORD_NAME) as z:
        for k, shape in R_C1.items():
            assert z[k].shape == shape, k
            assert meta["key_shapes"][k] == list(shape)
        assert z["n"].dtype == np.int64 and z["n"].tolist() == z["n_cycle"].tolist()
        assert b1.r_c1_shape_errors(z) == []
        # first instant: no reading -> NaN; target always the controller's
        assert np.isnan(z["load_read_N"][0]).all() and np.isnan(z["c_hat_corner_m"][0]).all()
        assert np.all(z["c_target_m"] == 0.08)
        k = 299  # cycle n = 300
        assert z["n"][k] == 300
        assert np.array_equal(z["load_read_N"][k], np.array([1.0e5, 1.1e5, 0.9e5, 0.8e5]) + 300)
        rod = np.full(4, 0.3 + 101 * 1e-4)  # 101 rises of 1e-4 by n = 300
        corners = np.array([0.01 * j + float(np.mean(rod)) for j in range(4)])
        if bias is not None:
            corners = corners - np.asarray(bias)
        assert np.allclose(z["c_hat_corner_m"][k], corners, atol=1e-12)
        assert z["c_hat_m"][k] == pytest.approx(float(np.min(corners)))
        assert np.allclose(z["att_raw_rad"][k], [1e-3, -2e-3])


def test_r_c1_bias_ignored_when_soil_off(gr, tmp_path):
    ctl = _Ctl(bias=[0.01, 0.01, 0.01, 0.01], soil_enable=False)
    _, rec, _ = _drive(gr, "full", n_end=50, ctl=ctl)
    rec.save(tmp_path / "x.npz")
    with np.load(tmp_path / "x.npz") as z:
        rod = 0.3
        assert np.allclose(z["c_hat_corner_m"][10], [0.01 * j + rod for j in range(4)])


def _fake_result(z_path, stats_fn):
    with np.load(z_path) as z:
        rows = [{"t_s": float(t), "pad_nodes": stats_fn()} for t in z["t_s"]]
    return {"s9_rows": rows}


def test_pad_nodes_consistency(gr, tmp_path):
    m, rec, _ = _drive(gr, "full", n_end=60)
    p = tmp_path / "g.npz"
    rec.save(p)
    res = _fake_result(p, m.pad_node_stats)
    ok = gr.pad_nodes_consistency(p, res)
    assert ok["ok"] and ok["cycles"] == 59 and ok["values"] == 59 * 4 * 6 and ok["differ"] == 0
    res["s9_rows"][5]["pad_nodes"][2]["sigma_sum_area_N"] += 1e-9
    bad = gr.pad_nodes_consistency(p, res)
    assert not bad["ok"] and bad["differ"] == 1 and bad["first_differ"] == {"cycle": 6, "leg": 2,
                                                                            "field": "sigma_sum_area_N"}
    res["s9_rows"] = res["s9_rows"][:-1]
    assert gr.pad_nodes_consistency(p, res)["cycles_missing_in_result"] == 1
    # None in result.json (no hull) <-> NaN in the npz
    m2 = _Model()
    base = m2.pad_node_stats

    def no_hull():
        s = base()
        for d in s:
            d["contact_hull_area_m2"] = d["contact_hull_perimeter_m"] = None
        return s
    m2.pad_node_stats = no_hull
    rec2 = gr.B1GridRecorder(m2, _Ctl(), "full")
    for n in range(1, 5):
        rec2.pad_nodes(SimpleNamespace(t_s=n * 0.1, stroke_m=np.zeros(4), imu_specific_force_samples_m_s2=None))
    rec2.save(tmp_path / "h.npz")
    assert gr.pad_nodes_consistency(tmp_path / "h.npz", _fake_result(tmp_path / "h.npz", no_hull))["ok"]
