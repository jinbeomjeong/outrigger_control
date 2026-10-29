"""S9 P3b judgement definitions of control spec rev. 60 (C-S9-60, U-S9P-13 / 14 / 15 (가)) in
``04_scripts/02_chrono/run_S9.py`` and the re-judgement path (``run_S9.rejudge_case``,
``s9_batch_summary.py P3b --rejudge``): P3-2 time clause T_lim, P3-5 minimum after the first READY,
P3-7 S-1 window reconstruction (gate, loaded window > 0.01 W_ref), ``_record`` keys, the per-case
re-judgement file and, when the batch is on disk, the 24 stored P3b cases against control's
``p3b_loc_detail.json`` / ``p3b_collect.json``. No Chrono."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "04_scripts" / "02_chrono"
V_MAX = 0.0209243016
W_REF = 376_583.56424339
SETTINGS = {"enable": True, "plateau_window_m": 0.01, "plateau_mean_speed_fraction": 0.15,
            "plateau_rise_max_N": 2000.0, "plausibility_fraction": 0.85, "push_speed_fraction": 0.25}
BATCH = ROOT / "07_results" / "S9" / "batch_P3b_20261026_122444"
CONTROL = ROOT / "06_analysis" / "02_control" / "s9" / "p3b"


def _import(name: str):
    sys.path.insert(0, str(SCRIPTS))
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(str(SCRIPTS))


r9 = _import("run_S9")


# --- P3-2 ----------------------------------------------------------------------------------------------


def test_p32_time_limit_from_soil_settings_and_v_max() -> None:
    lim = r9.p32_time_limit_s(SETTINGS, V_MAX)
    assert lim == pytest.approx(0.01 / (0.25 * V_MAX) + 1.0, rel=1e-15)
    assert lim == pytest.approx(2.91165, abs=1e-5)  # spec 314.1 "2.9114" is a rounding slip (1.9117 + 1.0)
    assert r9.P32_TAIL_ALLOWANCE_S == 1.0


def _p32(d: float, *, t_done: float | None = 60.0, loaded: bool = False, meta: dict | None = None,
         v_max: float | None = V_MAX):
    t = np.round(np.arange(30.001, 70.0, 1e-3), 6)
    t_dep, t_loc = 35.0, 35.0 + d
    cn = np.where(t < t_dep, 0.3 * 380e3, 0.0)
    if loaded:
        cn[np.abs(t - t_loc) < 0.01] = 0.02 * 380e3
    m = {"settings": SETTINGS, "t_P_s": t_dep + 0.9} if meta is None else meta
    return r9.p32_loc_block(t, cn, 380e3, t_loc=t_loc, t_dep=t_dep, t_done=t_done, t_soil_mode=33.0, soil_meta=m,
                            v_max_m_s=v_max)


def test_p32_within_new_clause_and_2s_record() -> None:
    p = _p32(2.5)
    assert p["within"] and not p["within_2s_record"] and p["limit_s"] == pytest.approx(2.91165, abs=1e-5)
    assert p["loc_minus_departure_s"] == pytest.approx(2.5) and p["tP_minus_departure_s"] == pytest.approx(0.9)
    assert p["window_s"] == pytest.approx(1.6) and p["soil_mode_used"] and "U-S9P-13" in p["criterion"]
    q = _p32(1.5)
    assert q["within"] and q["within_2s_record"]
    assert not _p32(2.95)["within"]  # beyond T_lim
    assert not _p32(1.0, loaded=True)["within"] and not _p32(1.0, loaded=True)["within_2s_record"]
    assert not _p32(1.0, t_done=35.5)["within"]  # LOC after the first DONE
    assert not _p32(-0.1)["within"]  # LOC before the departure
    none = _p32(1.0, meta={}, v_max=None)
    assert none["within"] is None and "T_lim" in none["reason"] and none["within_2s_record"]
    no_loc = r9.p32_loc_block(np.array([1.0]), np.array([0.0]), 1.0, t_loc=None, t_dep=1.0, t_done=None,
                              t_soil_mode=None, soil_meta={"settings": SETTINGS}, v_max_m_s=V_MAX)
    assert no_loc["within"] is False and no_loc["within_2s_record"] is False


# --- P3-5 ----------------------------------------------------------------------------------------------


def _rows(clear):
    return [{"t_s": round(30.0 + 0.1 * k, 6), "rut_clearance_m": c} for k, c in enumerate(clear)]


def test_p35_minimum_after_first_ready() -> None:
    # 30.0 .. 31.9 s; departure at 30.5 (clearance ~0), LOC at 30.8, READY at 31.2
    clear = [0.0] * 5 + [-0.002, 0.001, 0.004, 0.006, 0.02, 0.03, 0.04, 0.036, 0.05, 0.045, None, 0.05, 0.05, 0.05,
                         0.05]
    rows = _rows(clear)
    ph = [(12.0, "level"), (31.0, "done"), (31.05, "probe"), (31.2, "ready"), (31.5, "probe"), (31.6, "ready")]
    b = r9.p35_clearance_block(rows, ph, t_dep=30.5, t_loc=30.8, s_motor_max_m=[0.5, 0.4, 0.45, 0.3],
                               s_motor_limit_m=0.6848, probe_sinkage=[])
    assert b["rut_clearance_min_after_first_ready_m"] == pytest.approx(0.036) and b["t_at_min_s"] == pytest.approx(31.2)
    assert b["within"] and b["stroke_within"] and b["t_first_ready_s"] == 31.2
    assert b["rut_clearance_min_after_departure_m"] == pytest.approx(-0.002) and not b["within_after_departure_record"]
    assert b["rut_clearance_at_loc_m"] == pytest.approx(0.006) and b["rut_clearance_end_m"] == pytest.approx(0.05)
    low = r9.p35_clearance_block(rows, ph, t_dep=30.5, t_loc=30.8, s_motor_max_m=[0.69, 0.4, 0.45, 0.3],
                                 s_motor_limit_m=0.6848, probe_sinkage=[])
    assert not low["within"] and not low["stroke_within"]  # stroke clause kept
    shallow = r9.p35_clearance_block(_rows(clear[:12] + [0.02] + clear[13:]), ph, t_dep=30.5, t_loc=30.8,
                                     s_motor_max_m=[0.5] * 4, s_motor_limit_m=0.6848, probe_sinkage=[])
    assert not shallow["within"] and shallow["rut_clearance_min_after_first_ready_m"] == pytest.approx(0.02)
    nr = r9.p35_clearance_block(rows, ph[:2], t_dep=30.5, t_loc=30.8, s_motor_max_m=[0.5] * 4,
                                s_motor_limit_m=0.6848, probe_sinkage=[])
    assert nr["within"] is None and "no READY" in nr["reason"]


# --- P3-7 S-1 reconstruction ---------------------------------------------------------------------------

K = 30
"""Synthetic S-1 data: load sum rises 50 kN per mm of mean stroke until sample K, then flat at W_ref."""


def _s1(n: int = 60, slope_N_per_mm: float = 50e3, k: int = K):
    t = np.round(20.0 + 0.1 * np.arange(1, n + 1), 6)
    u = np.full((n, 4), 0.5 * V_MAX)
    e = np.cumsum(u[:, 0] * 0.1)  # mean stroke [m], 1.046 mm per sample
    load = W_REF - slope_N_per_mm * 1e3 * np.maximum(e[k] - e, 0.0)
    return t, u, np.repeat(e[:, None], 4, axis=1), np.repeat(load[:, None] / 4, 4, axis=1)


def test_s1_window_reconstruct_loc_clear_and_skip() -> None:
    t, u, e, f = _s1()
    lev = np.ones(len(t), bool)
    r = r9.s1_window_reconstruct(t, lev, u, e, f, SETTINGS, V_MAX, W_REF)
    assert r["t_P_s"] == t[K] and r["t_loc_s"] == t[K + 10]  # 10 samples x 1.046 mm >= 10 mm
    assert all(w["rise_N"] > 2000.0 for w in r["windows"][:-1]) and r["windows"][-1]["rise_N"] == pytest.approx(0.0, abs=1e-6)
    assert r["windows"][0]["t_end_s"] == t[10] and r["windows"][0]["n"] == 11
    # a retracting leg clears the window; a non-LEVEL sample is skipped without clearing
    u2 = u.copy()
    u2[K + 3, 0] = -1e-4
    r2 = r9.s1_window_reconstruct(t, lev, u2, e, f, SETTINGS, V_MAX, W_REF)
    assert r2["t_P_s"] == t[K + 4] and r2["t_loc_s"] == t[K + 14]
    slow = u.copy()
    slow[K + 3] = 0.1 * V_MAX  # mean below 0.15 v_max clears too
    assert r9.s1_window_reconstruct(t, lev, slow, e, f, SETTINGS, V_MAX, W_REF)["t_P_s"] == t[K + 4]
    lev2 = lev.copy()
    lev2[K + 5] = False
    r3 = r9.s1_window_reconstruct(t, lev2, u, e, f, SETTINGS, V_MAX, W_REF)
    assert r3["t_P_s"] == t[K] and r3["t_loc_s"] == t[K + 10]
    # plausibility: a flat load below 0.85 W_ref never confirms
    r4 = r9.s1_window_reconstruct(t, lev, u, e, f * 0.8, SETTINGS, V_MAX, W_REF)
    assert r4["t_loc_s"] is None and len(r4["windows"]) == len(t) - 10
    # two-sample tail: end-point difference
    step = np.full(len(t), 0.012)  # 12 mm per sample -> two-sample tails
    e2 = np.repeat(np.cumsum(step)[:, None], 4, axis=1)
    f2 = np.repeat(np.linspace(0.9 * W_REF, W_REF, len(t))[:, None] / 4, 4, axis=1)
    r5 = r9.s1_window_reconstruct(t, lev, u, e2, f2, SETTINGS, V_MAX, W_REF, stop_at_loc=False)
    w0 = r5["windows"][0]
    assert w0["n"] == 2 and w0["rise_N"] == pytest.approx((f2[1, 0] - f2[0, 0]) * 4 / 0.012 * 0.01)
    assert len(r5["windows"]) == len(t) - 1  # no stop at the LOC


def _rec(t, u, e, f, areas):
    a_p = np.asarray(areas["head_area_m2"])
    return {"t": t, "u_applied": u, "meas.head_pressure": f / a_p, "meas.rod_pressure": np.zeros_like(f),
            "meas.stroke": e, "F_cyl": f, "s_motor": e}


AREAS = {"head_area_m2": [0.013273229, 0.013273229, 0.0095, 0.0095], "annulus_area_m2": [0.0037699, 0.0037699, 0.003,
                                                                                           0.003]}


def _crawler(t, t_cut: float, level_N: float):
    ts = np.round(np.arange(t[0] - 1.0, t[-1] + 1.0, 1e-3), 6)
    return ts, np.where(ts <= t_cut + 1e-7, level_N, 0.0)


def test_p37_plateau_block_gate_loaded_windows_and_records() -> None:
    t, u, e, f = _s1()
    ph = [(10.0, "touch"), (20.05, "level")]
    rec = _rec(t, u, e, f, AREAS)
    meta = {"settings": SETTINGS, "loc": True, "t_P_s": float(t[K]), "t_loc_s": float(t[K + 10]), "W_ref_N": W_REF}
    ts, cn = _crawler(t, float(t[K - 3]), 0.02 * W_REF)  # loaded (> 0.01 W_ref) windows end at <= K - 3
    b = r9.p37_plateau_block(ts, cn, ph, rec, AREAS, meta, V_MAX)
    windows = r9.s1_window_reconstruct(t, np.ones(len(t), bool), u, e, f, SETTINGS, V_MAX, W_REF)["windows"]
    want = [w["rise_N"] for w in windows if w["t_end_s"] <= t[K - 3] + 1e-9]
    assert b["reconstruct_ok"] and b["t_P_rec_s"] == t[K] and b["t_loc_rec_s"] == t[K + 10]
    assert b["loaded_threshold_N"] == pytest.approx(0.01 * W_REF) and b["n_loaded_windows"] == len(want)
    assert b["rise_min_loaded_N"] == pytest.approx(min(want)) and b["within"] and min(want) >= 4000.0
    assert b["crawler_at_end_N"] == pytest.approx(0.02 * W_REF) and b["rise_min_gt1kN_N"] == pytest.approx(min(want))
    assert b["rise_min_gt0p05W_N"] is None and b["rise_min_loaded_true_N"] == pytest.approx(min(want))
    assert b["truth"]["t_loc_s"] == t[K + 10]
    # crawler between 1 kN and 0.01 W_ref: record only, no loaded window -> pass
    ts2, cn2 = _crawler(t, float(t[K - 3]), 2000.0)
    nb = r9.p37_plateau_block(ts2, cn2, ph, rec, AREAS, meta, V_MAX)
    assert nb["within"] and nb["no_loaded_window"] and nb["rise_min_loaded_N"] is None
    assert nb["rise_min_gt1kN_N"] == pytest.approx(min(want))
    # shallow load rise: loaded window below 4 kN fails
    t3, u3, e3, f3 = _s1(slope_N_per_mm=1500.0)
    r3 = r9.s1_window_reconstruct(t3, np.ones(len(t3), bool), u3, e3, f3, SETTINGS, V_MAX, W_REF)
    m3 = {**meta, "t_P_s": r3["t_P_s"], "t_loc_s": r3["t_loc_s"]}
    ts3, cn3 = _crawler(t3, float(r3["t_loc_s"]), 0.02 * W_REF)
    fb = r9.p37_plateau_block(ts3, cn3, ph, _rec(t3, u3, e3, f3, AREAS), AREAS, m3, V_MAX)
    assert fb["reconstruct_ok"] and fb["rise_min_loaded_N"] < 4000.0 and fb["within"] is False
    # gate: meta times differ -> not judgeable
    bad = r9.p37_plateau_block(ts, cn, ph, rec, AREAS, {**meta, "t_P_s": float(t[K]) + 0.1}, V_MAX)
    assert not bad["reconstruct_ok"] and bad["within"] is None and "gate failed" in bad["reason"]
    assert r9.p37_plateau_block(ts, cn, ph, rec, AREAS, {**meta, "loc": False}, V_MAX)["within"] is None
    assert "inputs missing" in r9.p37_plateau_block(ts, cn, ph, None, AREAS, meta, V_MAX)["reason"]
    # samples before the LEVEL entry are not in the window
    late = r9.p37_plateau_block(ts, cn, [(10.0, "touch"), (float(t[K + 2]), "level")], rec, AREAS, meta, V_MAX)
    assert late["t_P_rec_s"] == t[K + 2] and not late["reconstruct_ok"]


# --- re-judgement path ----------------------------------------------------------------------------------


def _case(d: Path) -> Path:
    """A finished synthetic ``level`` case folder (result.json, step_series.npz, record/)."""
    from outrigger_sim.params import load_params

    plant = r9.p37_plant_inputs(load_params())
    t, u, e, f = _s1(n=900, k=100)  # load rises until 18.1 s
    t = np.round(8.0 + 0.1 * np.arange(1, 901), 6)  # 8.1 .. 98.0 s, LEVEL from 12.0
    u[t < 12.0] = 0.0
    phases = [(8.1, "check"), (9.0, "touch"), (12.0, "level"), (60.0, "done"), (60.1, "probe"), (70.0, "ready")]
    rec = _rec(t, u, e, f, plant["cyl_areas"])
    lev = np.array([[p for tp, p in phases if tp <= x + 1e-9][-1] == "level" for x in t])
    s1 = r9.s1_window_reconstruct(t, lev, u, e, f, SETTINGS, V_MAX, W_REF)
    ts = np.round(np.arange(8.001, 98.0005, 1e-3), 6)
    n = ts.size
    t_dep = float(s1["t_P_s"]) - 0.2
    cn = np.where(ts < t_dep, 0.3 * W_REF, 0.0)
    s = {"t_s": ts, "scm_crawler_normal_N": cn, "scm_crawler_patches": (cn > 0).astype(float),
         "scm_track_normal_raw_N": np.repeat(cn[:, None] / 2, 2, axis=1), "track_utilisation": np.full((n, 2), 0.2),
         "scm_pad_normal_N": np.full((n, 4), 0.25 * W_REF), "F_cyl_N": np.full((n, 4), 90e3),
         "s_motor_m": np.full((n, 4), 0.4), "pad_sinkage_geometric_m": np.zeros((n, 4)),
         "roll_pitch_deg": np.zeros((n, 2)), "z_origin_m": np.zeros(n)}
    s["sinkage_rate_0p2s_m_s"] = r9.sinkage_rate(ts, s["pad_sinkage_geometric_m"])
    rows = [{"t_s": float(x), "rut_clearance_m": 0.0 if x < 70.0 else 0.04} for x in t]
    soil = {"settings": SETTINGS, "loc": True, "t_P_s": s1["t_P_s"], "t_loc_s": s1["t_loc_s"], "W_ref_N": W_REF}
    events = [(float(s1["t_loc_s"]), r9.SOIL_LOC_EVENT)]
    settle = {"track_normal_N": [0.15 * W_REF] * 2, "end_roll_pitch_deg": [0.0, 0.0]}
    ctx = {"weight_N": 380e3, "F_min_N": 9415.0, "P5_N": 16915.0, "s_motor_limit_m": 0.6848, "t_loop_start_s": 8.0,
           "settle": settle, "T_o_s": 0.8, "fallback_meta": None, "reapproach_history": None,
           "reapproach_settings": {"opposite_window_s": 0.8}, "soil_meta": soil, "record": rec, **plant}
    p3b = r9._plain(r9.p3b_records(s, rows, events, phases, ctx))
    # the stored p3b of a pre-rev. 60 run: former P3-2 / P3-5 values and no P3-7
    p3b["P3-2_loc"] = {"within": False, "note": "former"}
    p3b["P3-7_plateau"] = {"note": "not computed here"}
    p3b["checks"] = {"P3-2_within": False, "P3-5_within": False}
    d.mkdir(parents=True)
    res = {"action": "level", "args": {"soil": "J1", "pad_variant": "dwg_rear250", "level": "top", "fs_kN": 4.0,
                                       "grid": 0.01, "crawler_grid": 0.04},
           "phases": [{"t_s": a, "phase": b} for a, b in phases], "events": [{"t_s": a, "name": b} for a, b in events],
           "s9_rows": rows, "settle_reference": settle, "c2_soil": soil,
           "c2_lifted_reapproach": {"opposite_window_s": 0.8}, "c2_lifted_reapproach_history": None, "p3b": p3b}
    (d / "result.json").write_text(json.dumps(r9._plain(res)), "utf-8")
    np.savez(d / "step_series.npz", **s)
    (d / "record").mkdir()
    np.savez(d / "record" / "record.npz", **rec)
    (d / "record" / "meta.json").write_text(json.dumps({"run": {"params_file_sha256": "not-this-yaml"}}), "utf-8")
    return d


def test_rejudge_case_writes_overlay_and_keeps_result(tmp_path) -> None:
    d = _case(tmp_path / "batch" / "P3b_J1_B_top_Fs4")
    before = (d / "result.json").read_bytes()
    res = r9.rejudge_case(d)
    assert (d / "result.json").read_bytes() == before and (d / r9.REJUDGE_FILE).exists()
    assert res["unchanged_blocks_equal"] and res["unchanged_block_diffs"] == []
    assert not res["params_file_match"] and res["checks_before"] == {"P3-2_within": False, "P3-5_within": False}
    c = res["p3b"]["checks"]
    assert c["P3-2_within"] and c["P3-2_within_2s_record"] and c["P3-5_within"] is True
    assert c["P3-5_within_after_departure_record"] is False
    assert c["P3-7_reconstruct_ok"] and c["P3-7_within"] and c["P3-7_rise_min_loaded_N"] > 4000.0
    assert res["inputs_sha256"]["result.json"] == r9._file_sha256(d / "result.json")
    on_disk = json.loads((d / r9.REJUDGE_FILE).read_text("utf-8"))
    assert on_disk["p3b"]["checks"] == json.loads(json.dumps(r9._plain(c)))
    # a block outside the re-judged set that does not reproduce is reported
    r = json.loads((d / "result.json").read_text("utf-8"))
    # (P3-6_ready is re-judged since spec 421.1, P3-8 / W61 since spec 424.8.1; P3-9 stays outside the set)
    r["p3b"]["P3-9_deferred"]["flag"] = not r["p3b"]["P3-9_deferred"]["flag"]
    (d / "result.json").write_text(json.dumps(r), "utf-8")
    assert r9.rejudge_case(d, write=False)["unchanged_block_diffs"] == ["P3-9_deferred"]
    assert r9.rejudge_targets([str(tmp_path / "batch")]) == [d] and r9.rejudge_targets([str(d)]) == [d]


def test_summary_p3b_rejudge_uses_the_overlay(tmp_path) -> None:
    s = _import("s9_batch_summary")
    d = _case(tmp_path / "P3b_J1_B_top_Fs4")
    plain = s.summary_p3b(tmp_path)
    row = plain["rows"][d.name]
    assert row["p3b_source"] == "result.json" and row["checks"]["P3-2_within"] is False
    res = s.summary_p3b(tmp_path, rejudge=True)
    row = res["rows"][d.name]
    assert row["p3b_source"] == r9.REJUDGE_FILE and row["checks"]["P3-2_within"]
    assert row["checks"]["P3-7_within"] and row["checks_before_rev60"]["P3-2_within"] is False
    assert {"P3-2", "P3-5", "P3-7"} <= set(res["criteria"]) and "U-S9P-13" in res["criteria"]["P3-2"]
    assert "probe_sinkage" not in row["P3-5_clearance_stroke"] and row["P3-7_plateau"]["reconstruct_ok"]
    (d / "result.json").write_text((d / "result.json").read_text("utf-8") + " ", "utf-8")
    with pytest.raises(RuntimeError, match="another result.json"):
        s.summary_p3b(tmp_path)


# --- the 24 stored P3b cases (spec 314.1 test column) ------------------------------------------------------


@pytest.mark.skipif(not (BATCH.exists() and (CONTROL / "p3b_loc_detail.json").exists()),
                    reason="P3b batch 20261026_122444 or control p3b_loc_detail.json not on disk")
def test_rejudge_24_stored_cases_against_control() -> None:
    loc = json.loads((CONTROL / "p3b_loc_detail.json").read_text("utf-8"))
    col = json.loads((CONTROL / "p3b_collect.json").read_text("utf-8"))
    dirs = r9.rejudge_targets([str(BATCH)])
    assert len(dirs) == 24
    out = {d.name: r9.rejudge_case(d, write=False) for d in dirs}
    j1b = {k for k in out if "_J1_B_" in k}
    for k, res in out.items():
        p, c, ref = res["p3b"], res["p3b"]["checks"], loc[k]
        assert res["unchanged_blocks_equal"], k
        # P3-2
        assert c["P3-2_within"], k
        assert c["P3-2_within_2s_record"] is (k not in j1b), k
        assert p["P3-2_loc"]["tP_minus_departure_s"] == pytest.approx(ref["tP_minus_dep_s"], abs=1e-9)
        assert p["P3-2_loc"]["window_s"] == pytest.approx(ref["tail_s"], abs=1e-9)
        # P3-5
        p35 = p["P3-5_clearance_stroke"]
        assert c["P3-5_within"], k
        assert p35["rut_clearance_min_after_first_ready_m"] == pytest.approx(col[k]["P3-5"]["rut_min_after_first_ready"][0],
                                                                              abs=1e-12)
        # P3-7
        p37 = p["P3-7_plateau"]
        assert p37["reconstruct_ok"] and c["P3-7_within"], k
        for name, mine in p37["buckets_read"].items():
            r = ref["rise"]["read"]["buckets"][name]
            assert mine["n"] == r["n"], (k, name)
            if r["n"]:
                assert mine["rise_min_N"] == pytest.approx(r["rise_min_kN"] * 1e3, abs=0.01), (k, name)
    loc_minus = [out[k]["p3b"]["P3-2_loc"]["loc_minus_departure_s"] for k in j1b]
    assert min(loc_minus) == pytest.approx(2.43, abs=0.005) and max(loc_minus) == pytest.approx(2.61, abs=0.005)
    mins = {k: v["p3b"]["P3-5_clearance_stroke"]["rut_clearance_min_after_first_ready_m"] for k, v in out.items()}
    assert min(mins, key=mins.get) == "P3b_S1_B_top_Fs4" and mins["P3b_S1_B_top_Fs4"] == pytest.approx(0.0353, abs=5e-5)
    rise = {k: v["p3b"]["P3-7_plateau"]["rise_min_loaded_N"] for k, v in out.items()}
    assert all(rise[k] is None for k in rise if "_G1_" in k)
    j1b_rise = [rise[k] for k in j1b]
    assert min(j1b_rise) == pytest.approx(7310.0, abs=5.0) and max(j1b_rise) == pytest.approx(8940.0, abs=5.0)
    assert rise["P3b_J2_B_top_Fs4"] == pytest.approx(7500.0, abs=5.0)
