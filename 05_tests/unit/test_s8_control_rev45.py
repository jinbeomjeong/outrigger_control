"""S8 judge rev. 45 (C-S8-21, U-S8-18 / 19; ``s6_control_spec.md`` 215, ``dynamics_model.md``
5.27.2): F1 reading law ``r = F_hat - (F - f + E_s)``, R45-2 / R45-3 split of the calibrated
residual, R45-4 low-load probe record; p1r record checks (WIKA noise sigma, ideal |r| <= 0.1 kN,
re-judgement gate)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.sensors.pressure_error import PressureErrorTerms
from outrigger_sim.verify import s8_control as s8

ROOT = Path(__file__).resolve().parents[2]
P1R = ROOT / "07_results" / "S8" / "p1r_20261024_222013"
WIKA_CASES = ("S_top_rpB_wika_Fs8", "S_top_fdown3.5_wika_Fs8")
A_P = np.array([0.013273229, 0.013273229, 0.00950331778, 0.00950331778])
A_ANN = np.array([0.00376991118, 0.00376991118, 0.00314159265, 0.00314159265])
SIGMA_P = 0.20e5
SIGMA_F_MODEL = SIGMA_P * np.hypot(A_P, A_ANN)  # 276 / 200 N (spec 215.2)


def _terms_meta(rng: np.random.Generator) -> dict[str, dict[str, float]]:
    meta = {}
    for side in ("head", "rod"):
        for leg in s8.LEGS:
            meta[f"{side}:{leg}"] = {"offset_Pa": rng.uniform(-2e5, 2e5),
                                     "gain": rng.uniform(-0.005, 0.005),
                                     "nonlinearity_Pa": rng.uniform(-2e5, 2e5),
                                     "temperature_offset_Pa": 0.0, "temperature_gain": 0.0}
    return meta


def test_limits_match_the_spec_values() -> None:
    """215.2: 6 sigma_F + 0.1 kN = 1.76 / 1.30 kN at sigma_p 0.20 bar; ideal 0.1 kN."""
    np.testing.assert_allclose(SIGMA_F_MODEL, [276.0, 276.0, 200.2, 200.2], atol=0.3)
    np.testing.assert_allclose(s8.f1_law_limit_N(SIGMA_F_MODEL) / 1e3,
                               [1.756, 1.756, 1.301, 1.301], atol=1e-3)
    assert s8.f1_law_limit_N(np.zeros(4)).tolist() == [100.0] * 4
    assert s8.AIR_RESIDUAL_FLAG_N == 1700.0 and s8.F1_FALLBACK_CONST_N == 1300.0
    # R46-1 (U-S8-25) replaced max(0.1 kN, 0.065 F_s,leg): 0.1 kN at F_s 0, 0.75 kN at F_s > 0
    np.testing.assert_allclose(s8.friction_flag_limit_N([0.0, 2e3, 8e3, 6666.4]),
                               [100.0, 750.0, 750.0, 750.0])


def test_sensor_static_error_matches_the_sensor_model() -> None:
    """E_s = e_h(p_h) A_p - e_r(p_r) A_ann with the +-4 bar clip, per sensor; extra offsets."""
    rng = np.random.default_rng(7)
    meta = _terms_meta(rng)
    meta["head:FL"].update(offset_Pa=3.9e5, gain=0.005)  # clipped at high pressure
    p_h = rng.uniform(0.0, 300e5, (50, 4))
    p_r = rng.uniform(0.0, 40e5, (50, 4))
    es = s8.sensor_static_error_N(meta, "normal", p_h, p_r, A_P, A_ANN)
    for j, leg in enumerate(s8.LEGS):
        def err(side, p, j=j, leg=leg):
            m = meta[f"{side}:{leg}"]
            return PressureErrorTerms(np.float64(m["offset_Pa"]), np.float64(m["gain"]),
                                      np.float64(m["nonlinearity_Pa"]), np.float64(0.0),
                                      np.float64(0.0), 4.0e5).error_Pa(p)
        np.testing.assert_allclose(es[:, j], err("head", p_h[:, j]) * A_P[j]
                                   - err("rod", p_r[:, j]) * A_ANN[j], rtol=1e-12)
    assert np.abs(es[:, 0]).max() <= 4.0e5 * (A_P[0] + A_ANN[0]) + 1e-6
    # no terms (ideal / legacy): only the configured extra offsets
    cfg = {"head_offset_Pa": [1e5, 0.0, 0.0, 0.0], "rod_offset_Pa": [0.0, 0.0, 0.0, 1e5]}
    e0 = s8.sensor_static_error_N(None, None, p_h, p_r, A_P, A_ANN, cfg)
    np.testing.assert_allclose(e0[:, 0], 1e5 * A_P[0])
    np.testing.assert_allclose(e0[:, 3], -1e5 * A_ANN[3])
    assert not e0[:, 1:3].any()


def test_f1_law_metrics_max_and_statistics_rows() -> None:
    """① max |r| vs 6 sigma + 0.1 kN; ② mean <= 0.1 kN and std / sigma in [0.85, 1.15]."""
    rng = np.random.default_rng(20261025)
    n = 800
    r = rng.normal(0.0, 1.0, (n, 4)) * SIGMA_F_MODEL
    use = np.ones(n, bool)
    m = s8.f1_law_metrics(r, SIGMA_F_MODEL, use)
    assert m["violations"] == 0 and m["stats_passed"] is True
    assert all(0.9 < x < 1.1 for x in m["std_ratio"])
    spike = r.copy()
    spike[10, 2] = 1.35e3  # rear limit 1.30 kN
    assert s8.f1_law_metrics(spike, SIGMA_F_MODEL, use)["violations_per_leg"] == [0, 0, 1, 0]
    biased = r + np.array([150.0, 0.0, 0.0, 0.0])  # 1 % area error at ~15 kN
    mb = s8.f1_law_metrics(biased, SIGMA_F_MODEL, use)
    assert mb["violations"] == 0 and mb["stats_ok"] == [False, True, True, True]
    wide = s8.f1_law_metrics(r * 1.25, SIGMA_F_MODEL, use)  # wrong noise model
    assert wide["stats_passed"] is False
    use[:5] = False  # CHECK rows left out
    spike[:5] = 9e3
    assert s8.f1_law_metrics(spike, SIGMA_F_MODEL, use)["violations_per_leg"] == [0, 0, 1, 0]
    # ideal sensor: sigma 0 -> |r| <= 0.1 kN, no statistics row
    ideal = s8.f1_law_metrics(np.full((5, 4), 90.0), np.zeros(4), np.ones(5, bool))
    assert ideal["violations"] == 0 and ideal["stats_passed"] is None
    assert s8.f1_law_metrics(np.full((5, 4), 110.0), np.zeros(4),
                             np.ones(5, bool))["violations"] == 20


def test_check_hold_rows_follow_the_controller_stage_rule() -> None:
    """Common hold start = the period where the last moving leg reaches; 10 rows after it."""
    n = 50
    t = 3.0 + 0.1 * np.arange(n)
    phases = np.array(["check"] * 46 + ["touch"] * 4)
    u = np.zeros((n, 4))
    u[1:9, :] = 1e-3   # extend: legs 0, 1, 3 reach at row 9, leg 2 at row 10
    u[9, 2] = 1e-3
    u[21:31, :] = -1e-3
    u[31, 2] = -1e-3   # retract: leg 2 reaches at row 32
    holds = s8.check_hold_rows(phases, u, t)
    for j in range(4):
        assert holds[j][0].tolist() == list(range(11, 21))
        assert holds[j][1].tolist() == list(range(33, 43))
    u[:, 3] = 0.0  # a skipped leg (no move): no hold, the others unchanged
    holds = s8.check_hold_rows(phases, u, t)
    assert holds[3] == [] and holds[0][0].tolist() == list(range(11, 21))


def test_calibration_split_and_error_split_identity() -> None:
    """r_cal = (E_s - c_sens) - c_fric + (r - c_noise) with c_i = c_sens + c_noise + c_fric."""
    rng = np.random.default_rng(3)
    n = 60
    law = rng.uniform(5e3, 30e3, (n, 4))
    es = rng.uniform(-600.0, 600.0, (n, 4))
    noise = rng.normal(0.0, 1.0, (n, 4)) * SIGMA_F_MODEL
    f_hat = law + es + noise
    w = np.array([1047.0, 1047.0, 718.0, 718.0])
    holds = [[np.arange(10, 20), np.arange(30, 40)]] * 4
    c_i = [0.5 * (f_hat[10:20, j].mean() + f_hat[30:40, j].mean()) + w[j] for j in range(4)]
    sp = s8.calibration_split(f_hat, law, es, w, c_i, holds)
    for j in range(4):
        assert sp[j]["c_rebuild_error_N"] == pytest.approx(0.0, abs=1e-6)
        assert sp[j]["c_sens_N"] + sp[j]["c_noise_N"] + sp[j]["c_fric_N"] \
            == pytest.approx(c_i[j])
    r = f_hat - law - es
    r_cal = f_hat - np.array(c_i)[None, :] - law
    for j in range(4):
        parts = (es[:, j] - sp[j]["c_sens_N"]) - sp[j]["c_fric_N"] + (r[:, j] - sp[j]["c_noise_N"])
        np.testing.assert_allclose(parts, r_cal[:, j], atol=1e-6)
    fs = [8e3, 8e3, 6.666e3, 6.666e3]
    mask = np.zeros((n, 4), bool)
    mask[45:55, 1] = True
    es_big = es.copy()
    es_big[50, 1] = sp[1]["c_sens_N"] + 700.0  # static part 0.70 kN -> flag
    out = s8.error_split(mask, r, es_big, r_cal, sp, SIGMA_F_MODEL, fs)
    assert out["static_flag"] is True and out["legs"][1]["n"] == 10
    assert out["legs"][0]["static_max_kN"] is None  # no FL sample in the mask
    assert out["legs"][0]["c_fric_kN"] == pytest.approx(sp[0]["c_fric_N"] / 1e3)
    flagged = [abs(sp[j]["c_fric_N"]) > (750.0 if fs[j] > 0 else 100.0) for j in range(4)]
    assert [x["fric_flag"] for x in out["legs"]] == flagged
    assert out["total_flag"] is (out["total_max_kN"] > 1.6)


def test_air_residual_flag_is_1_7_kN_with_parts() -> None:
    """R45-3: flag above 1.7 kN; the split is attached."""
    sens = np.array([[1.65e3, 0.0, 0.0, 0.0], [1.8e3, 0.0, 0.0, 0.0]])
    f_true = np.zeros((2, 4))
    n_pad = np.zeros((2, 4))
    a = s8.air_residual(sens[:1], f_true[:1], n_pad[:1], np.array([True]), ["touch"],
                        split={"static_max_kN": 0.1})
    assert a["flag"] is False and a["split"] == {"static_max_kN": 0.1}
    assert s8.air_residual(sens, f_true, n_pad, np.array([True, True]),
                           ["touch", "touch"])["flag"] is True


def _probe(leg, est, grounded=True, t0=10.0, skipped=False):
    return {"leg_index": leg, "load_estimate_N": est, "is_grounded": grounded,
            "is_skipped": skipped, "t_move_start_s": t0 + 3.0 * leg,
            "t_first_hold_end_s": t0 + 3.0 * leg + 1.4, "t_second_hold_end_s": t0 + 3.0 * leg + 2.9}


def test_reconstruct_reground_leg_load_first() -> None:
    f_min = 9414.59
    rows = [_probe(0, 80e3), _probe(1, 12e3), _probe(2, 13e3), _probe(3, 60e3)]
    d = s8.reconstruct_reground_leg(rows, np.full(4, 50e3), f_min, 5e3, 0, 3)
    assert d["leg"] == "FR" and d["acted"] and d["rule"].startswith("light")
    d3 = s8.reconstruct_reground_leg(rows, np.full(4, 50e3), f_min, 5e3, 2, 3)
    assert d3["leg"] == "FR" and not d3["acted"]  # max rounds reached
    rows2 = [_probe(0, 80e3), _probe(1, 40e3, grounded=False), _probe(2, 50e3, grounded=False),
             _probe(3, 60e3)]
    d2 = s8.reconstruct_reground_leg(rows2, np.array([80e3, 45e3, 30e3, 60e3]), f_min, 5e3, 0, 3)
    assert d2["leg"] == "RL" and d2["rule"].startswith("combined")
    assert s8.reconstruct_reground_leg([_probe(0, 80e3)], np.zeros(4), f_min, 5e3, 0, 3)[
        "leg"] is None


def test_low_load_probe_records() -> None:
    """R45-4: only legs whose lower bound at the round start is below F_min + 15 kN."""
    f_min = 9414.59
    t0 = 3.0
    tc = np.round(np.arange(0.0, 40.0, 0.1), 10)
    lower = np.full((tc.size, 4), 60e3)
    lower[:, 2] = 20e3  # RL below F_min + 15 kN = 24.4 kN
    k = np.searchsorted(tc, 10.0 + 6.0 + 2.9 - t0 + 0.5)
    lower[k, 2] = 16e3  # dip inside the 2 s window after RL's second hold end
    t_pad = np.round(np.arange(0.0, 40.0, 0.001), 10)
    f_true = np.full((t_pad.size, 4), 70e3)
    f_true[:, 2] = 25e3
    rnd = [_probe(0, 80e3), _probe(1, 75e3), _probe(2, 21e3), _probe(3, 60e3)]
    pr_legs = [{"round": 0, "leg": "RL", "load_estimate_kN": 21.0, "truth_cyl_kN": 19.0,
                "truth_end_kN": 18.5}]
    recs = s8.low_load_probe_records([rnd], pr_legs, tc, lower, np.full((tc.size, 4), 50e3),
                                     t_pad, f_true, f_min, t0)
    assert len(recs) == 1 and recs[0]["leg"] == "RL"
    r = recs[0]
    assert r["lower_at_round_start_kN"] == pytest.approx(20.0)
    assert r["F2_margin_min_kN"] == pytest.approx((16e3 - f_min) / 1e3)
    assert r["true_margin_min_kN"] == pytest.approx((25e3 - f_min) / 1e3)
    assert r["E_minus_T2_kN"] == pytest.approx(2.5) and r["T2_minus_T0_kN"] == pytest.approx(-0.5)
    assert r["reground"]["leg"] is None and r["reground_this_leg"] is False  # 21 kN > 14.4 kN
    assert s8.low_load_probe_records([rnd], pr_legs, tc, lower + 10e3, lower, t_pad, f_true,
                                     f_min, t0) == []


# --- p1r records (C-S8-21 tests) ------------------------------------------------------------------


def _law_of(case_id: str):
    from outrigger_sim.params import load_params
    from outrigger_sim.verify import s6_control as s6

    d = P1R / case_id
    case = s6.load_case(d)
    params = load_params(level=case["result"]["settings"]["level"])
    pads = case["pads"]
    series = s8.load_series(d)
    t_abs = np.asarray(series["t"], float)
    law = s8._reading_law(case, pads, t_abs, params, wika=s8._is_wika(case))
    f = s8._pad_at(pads, t_abs, "F_cyl") - s8._pad_at(pads, t_abs, "f_seal")
    r = np.asarray(series["F_hat_N"], float) - (f + law["E_s"])
    post = np.asarray(series["phase"]).astype(str) != "check"
    return case, law, r, post


@pytest.mark.skipif(not (P1R / WIKA_CASES[0] / "pads.npz").exists(), reason="p1r not present")
@pytest.mark.parametrize("case_id", WIKA_CASES)
def test_p1r_wika_reading_law_reproduces_5_27_2(case_id: str) -> None:
    """C-S8-21: per run and leg the residual std is inside the R45-1 ② band [0.85, 1.15]
    sigma_F (control rev. 46 216.6 (1): +-3 % is checked per side pooled over the two runs,
    :func:`test_p1r_wika_std_pooled_per_side_within_3_percent`); mean <= 0.1 kN; max row
    passes."""
    _case, law, r, post = _law_of(case_id)
    assert law["available"] and law["has_terms"] and law["grade"] == "normal"
    np.testing.assert_allclose(law["sigma_F_N"], SIGMA_F_MODEL, rtol=1e-6)
    assert law["check_F_minus_f_vs_F_pressure_N"] < 1e-6
    m = s8.f1_law_metrics(r, np.asarray(law["sigma_F_N"]), post)
    assert m["violations"] == 0 and m["stats_passed"] is True
    assert all(0.85 <= x <= 1.15 for x in m["std_ratio"])
    assert max(abs(v) for v in m["mean_N"]) <= 100.0


@pytest.mark.skipif(not (P1R / WIKA_CASES[0] / "pads.npz").exists(), reason="p1r not present")
def test_p1r_wika_std_pooled_per_side_within_3_percent() -> None:
    """Control rev. 46 216.6 (1): the two WIKA runs pooled per side (front FL + FR, rear RL +
    RR, n ~ 2,760, rel. s.e. 1.35 %): std within +-3 % of 276 / 200 N; the pooling of
    :func:`s8.pooled_side_std` equals the direct pooled sample std."""
    laws, xs = [], {"front": [], "rear": []}
    for cid in WIKA_CASES:
        _case, law, r, post = _law_of(cid)
        law["metrics"] = s8.f1_law_metrics(r, np.asarray(law["sigma_F_N"]), post)
        laws.append(law)
        xs["front"].append(r[post][:, :2].ravel())
        xs["rear"].append(r[post][:, 2:].ravel())
    pooled = s8.pooled_side_std(laws)
    for side, model in (("front", 276.0), ("rear", 200.0)):
        direct = float(np.concatenate(xs[side]).std(ddof=1))
        assert pooled[side]["std_N"] == pytest.approx(direct, rel=1e-9)
        assert abs(direct / model - 1.0) <= 0.03, (side, direct)
        assert pooled[side]["flag"] is False


@pytest.mark.skipif(not (P1R / WIKA_CASES[0] / "pads.npz").exists(), reason="p1r not present")
def test_p1r_calibration_split_reproduces_the_controller_offsets() -> None:
    """The CHECK-hold windows reproduce the controller zero-calibration offsets c_i."""
    from outrigger_sim.params import load_params

    case, law, r, post = _law_of(WIKA_CASES[0])
    d = P1R / WIKA_CASES[0]
    series = s8.load_series(d)
    t_abs = np.asarray(series["t"], float)
    tc = t_abs - float(case["result"]["settings"]["start_t_s"])
    phases = np.asarray(series["phase"]).astype(str)
    f = s8._pad_at(case["pads"], t_abs, "F_cyl") - s8._pad_at(case["pads"], t_abs, "f_seal")
    f_hat = np.asarray(series["F_hat_N"], float)
    params = load_params(level="top")
    sp = s8._calibration_split_of_case(case, series, phases, tc, f_hat, f, law["E_s"], params,
                                       np.zeros_like(f_hat), post)
    assert all(abs(x["c_rebuild_error_N"]) < 1.0 for x in sp)
    assert all(0.0 < x["c_fric_N"] < 600.0 for x in sp)  # F_s 8: + (reads low), 5.27.2 range


@pytest.mark.skipif(not (P1R / "verify_S8C.json").exists(), reason="p1r verdict not present")
def test_p1r_ideal_sensor_cases_reading_law_within_0_1_kN() -> None:
    """C-S8-21: every ideal-sensor p1r case: |F_hat - (F - f)| <= 0.1 kN outside CHECK."""
    n = 0
    for d in sorted(p for p in P1R.iterdir() if (p / "s8_series.npz").exists()):
        res = json.loads((d / "result.json").read_text(encoding="utf-8"))
        if (res["settings"].get("bundle_c") or {}).get("sensor_model"):
            continue
        with np.load(d / "pads.npz") as pads, np.load(d / "s8_series.npz") as s:
            t = np.asarray(s["t"], float)
            f = s8._pad_at(pads, t, "F_cyl") - s8._pad_at(pads, t, "f_seal")
            r = np.asarray(s["F_hat_N"], float) - f
            post = np.asarray(s["phase"]).astype(str) != "check"
        assert np.abs(r[post]).max() <= 100.0, d.name
        n += 1
    assert n == 35


@pytest.mark.skipif(not (P1R / "verify_S8C.json").exists(), reason="p1r verdict not present")
def test_p1r_rev45_rejudgement_keeps_zero_gate_failures() -> None:
    """C-S8-21: the rev. 45 re-judgement of p1r (ref batch p1) has no failed row; every F1 law
    row passes; ideal-sensor max |r| <= 0.1 kN; the rev. 44 verdict file is kept."""
    doc = json.loads((P1R / "verify_S8C.json").read_text(encoding="utf-8"))
    if not str(doc["meta"].get("judge_revision", "")).startswith(("spec rev. 45", "spec rev. 46")):
        pytest.skip("p1r verify_S8C.json not yet re-judged with rev. 45 or later")
    assert doc["meta"]["failed"] == 0
    assert (P1R / "verify_S8C_rev44judge.json").exists()
    law = [r for r in doc["rows"] if r["item"] == s8.F1_LAW_ITEM]
    assert len(law) == 37 and all(r["passed"] is True for r in law)
    ideal = [r for r in law if max(r["sigma_F_N"]) == 0.0]
    assert len(ideal) == 35
    assert max(max(x for x in r["max_abs_kN"] if x is not None) for r in ideal) <= 0.1
    stats = [r for r in doc["rows"] if r["item"] == s8.F1_STATS_ITEM]
    assert {r["case"] for r in stats} == set(WIKA_CASES) and all(r["passed"] for r in stats)
    assert not [r for r in doc["rows"] if r["item"] == s8.F1_FALLBACK_ITEM]
