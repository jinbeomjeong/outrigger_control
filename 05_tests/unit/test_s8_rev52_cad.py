"""C-S8-36 / C-S8-37 (spec rev. 52 229-232): run_S8C re-approach variants and the refresh
meta, the corrected item-9 reading, the RT record and the twist-work bins."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s8_control as v

ROOT = Path(__file__).resolve().parents[2]


# --- C-S8-37 reading variants ------------------------------------------------------------------


def _pads(n_raw: list[float], *, seal_N: float = 8000.0, t_end: float = 1.0) -> dict:
    t = np.arange(0.0, t_end + 1e-12, 1e-3)
    return {"t": t, "N_raw": np.tile(np.asarray(n_raw, float), (t.size, 1)),
            "F_seal_limit": np.full((t.size, 4), seal_N)}


def test_corrected_reading_adds_half_kN_only_below_1p5_kN_pad_force() -> None:
    pads = _pads([1000.0, 2000.0, 0.0, 1499.0])
    t10 = np.arange(0.1, 1.0, 0.1)
    lower = np.full((t10.size, 4), 10_000.0)
    # rev. 54 249: the default correction needs L2b-NSC and F_s,i > 0 (8 kN -> 0.5 kN)
    out = v.reading_variants(t10, pads, lower, lower + 1.0, np.full(4, 700.0),
                             engine="L2b_NSC")
    add = out["corrected"]["lower_reading_N"] - lower
    np.testing.assert_allclose(add, np.tile([500.0, 0.0, 500.0, 500.0], (t10.size, 1)))
    np.testing.assert_allclose(out["corrected"]["net_force_N"] - (lower + 1.0), add)
    assert out["stats"]["corrected_per_leg"] == {"FL": 9, "FR": 0, "RL": 9, "RR": 9}
    assert out["stats"]["source"] == "N_raw"


def test_upper_sensitivity_lifts_only_lifted_legs_to_seal_limit_minus_rod_weight() -> None:
    pads = _pads([0.0, 2000.0, -1.0, 0.0], seal_N=8000.0)
    t10 = np.array([0.2, 0.5])
    lower = np.array([[1000.0, 1000.0, 9000.0, 7300.0]] * 2)
    out = v.reading_variants(t10, pads, lower, lower, np.full(4, 700.0))
    np.testing.assert_allclose(out["upper"]["lower_reading_N"],
                               [[7300.0, 1000.0, 9000.0, 7300.0]] * 2)


def test_reading_variants_without_pad_normal_are_none() -> None:
    out = v.reading_variants(np.array([0.1]), {"t": np.array([0.0, 1.0])},
                             np.zeros((1, 4)), np.zeros((1, 4)), np.zeros(4))
    assert out["corrected"] is None and out["upper"] is None


def test_pad_normal_is_interpolated_at_the_sample_time() -> None:
    t = np.array([0.0, 0.001, 0.002])
    pads = {"t": t, "N_raw": np.column_stack([np.array([0.0, 1000.0, 2000.0])] * 4)}
    n10, key = v.pad_normal_at(np.array([0.0015]), pads)
    assert key == "N_raw"
    np.testing.assert_allclose(n10, [[1500.0] * 4])


# --- C-S8-37 twist work and RT record ----------------------------------------------------------


def _work_inputs(d_step_N: float, u_tw_m_s: float, *, t_ev: float = 10.0, span: float = 4.0):
    t = np.round(np.arange(t_ev - 0.5, t_ev + span + 1e-9, 1e-3), 6)
    f = np.full((t.size, 4), 50_000.0)
    after = t >= t_ev
    f[after, 0] += d_step_N  # D = F_FL + F_RR - F_FR - F_RL
    rec_t = np.round(np.arange(t_ev - 0.5, t_ev + span + 1e-9, 0.1), 6)
    u = np.zeros((rec_t.size, 4))
    u[rec_t >= t_ev] = np.array([1.0, -1.0, -1.0, 1.0]) * u_tw_m_s  # n . u = 2 u_tw
    return {"t": t, "F_cyl": f}, {"t": rec_t, "u_applied": u}, t_ev


def test_twist_work_bins_follow_the_rev51_definition() -> None:
    pads, rec, t_ev = _work_inputs(10_000.0, 1e-3)
    w = v.twist_work_bins(pads, rec, t_ev, span_s=4.0)
    # P = D / 2 (n . u) = 5000 N x 2e-3 m/s = 10 W -> 5 J per 0.5 s bin
    np.testing.assert_allclose(w["bins_J"], [5.0] * 8, atol=0.02)
    assert w["max_bin_after_J"] == pytest.approx(5.0, abs=0.02)
    assert w["passed"] is True
    pads, rec, t_ev = _work_inputs(100_000.0, 1e-3)
    w = v.twist_work_bins(pads, rec, t_ev, span_s=4.0)
    # rev. 52 rule fails (50 J bins); rev. 54 248.3: one continuous cluster -> passes
    assert w["passed_rev52"] is False
    assert w["raw_max_bin_after_J"] == pytest.approx(50.0, abs=0.1)
    assert w["n_clusters"] == 1 and w["passed"] is True


def test_twist_work_bins_stop_at_the_record_end() -> None:
    pads, rec, t_ev = _work_inputs(10_000.0, 1e-3, span=2.2)
    w = v.twist_work_bins(pads, rec, t_ev, span_s=8.0)
    assert len(w["bins_J"]) == 5  # 0 .. 2.5 s; no empty bins after the end


def test_reapproach_rt_record_counts_retriggers_and_deferred_starts() -> None:
    t0 = 3.0
    cm = {"lifted_reapproach": [
        {"leg": "FL", "start_s": t0 + 9.0, "end_s": t0 + 9.4, "is_retrigger": False},
        {"leg": "FL", "start_s": t0 + 10.1, "end_s": t0 + 10.5, "is_retrigger": False,
         "outcome": "contact"},
        {"leg": "RR", "start_s": t0 + 10.5, "end_s": t0 + 10.9, "is_retrigger": True},
        {"leg": "RL", "start_s": t0 + 11.8, "end_s": t0 + 12.0, "is_retrigger": True}]}
    names = [(11.7, "leg_reapproach_deferred:RL"), (9.5, "leg_reapproach_deferred:FR")]
    out = v.reapproach_rt_record(names, 10.0, t0, cm, None, None)
    assert out["runs_after_event"] == 3
    assert out["retriggers"] == 2
    assert out["deferred"] == 1
    assert out["deferred_rel_s"] == [[1.7, "RL"]]
    assert out["starts_after_1.5_s"] == 1
    assert out["work"] is None


def test_rt_rows_judge_only_rt_variant_runs() -> None:
    w_bad = {"max_bin_after_J": 49.2, "raw_max_bin_after_J": 49.2, "passed": False,
             "clusters": [[1.5, 30.0], [2.5, 49.2]], "n_clusters": 2, "max_cluster_J": 49.2}
    w_ok = {"max_bin_after_J": 0.1, "raw_max_bin_after_J": 0.1, "passed": True,
            "clusters": [], "n_clusters": 0, "max_cluster_J": 0.0}

    def run(work, variant):
        return {"rt": {"runs_after_event": 2, "retriggers": 1, "deferred": 1,
                       "starts_after_1.5_s": 1, "deferred_rel_s": [], "runs": [],
                       "work": work}, "reapproach_variant": variant}

    rows = v.rt_rows({"A": run(w_bad, "rt"), "B": run(w_ok, "rt"), "C": run(w_bad, None)})
    work_rows = [r for r in rows if r["item"].startswith("C-S8-36")]
    judged = [r for r in work_rows if r["kind"] == "judged"]
    record = [r for r in work_rows if r["kind"] == "record"]
    assert len(judged) == 1 and judged[0]["passed"] is False
    assert judged[0]["value"]["failed"] == 1
    # rev. 54: per selection one judged-or-record recurrence row + two record rows
    assert len(record) == 2 + 3 and all(r["passed"] is None for r in record)


# --- C-S8-36 run_S8C ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def run_s8c():
    sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
    import run_S8C

    return run_S8C


def test_reapproach_variants(run_s8c) -> None:
    from outrigger_sim.control.c2 import C2Config, LiftedReapproachSettings

    cfg = C2Config().with_10hz_d1()
    assert run_s8c.with_reapproach_variant(cfg, "rt") is cfg
    assert run_s8c.with_reapproach_variant(cfg, None) is cfg
    off = run_s8c.with_reapproach_variant(cfg, "f1only").r8.lifted_reapproach
    for key in run_s8c.RT_KEYS:
        assert getattr(off, key) == getattr(LiftedReapproachSettings, key)
    assert off.retrigger_window_s is None and off.opposite_window_s is None
    # everything else of the preset stays
    lr = cfg.r8.lifted_reapproach
    assert off.load_fraction_of_F_min == lr.load_fraction_of_F_min == 1.4
    with pytest.raises(ValueError):
        run_s8c.with_reapproach_variant(cfg, "bogus")
    with pytest.raises(RuntimeError):
        run_s8c.with_reapproach_variant(C2Config(), "rt")


def test_refresh_records_the_nested_reapproach_fields(run_s8c) -> None:
    from outrigger_sim.control.c2 import C2Config, C2Controller
    from outrigger_sim.params import load_params

    params = load_params(level="top")
    cfg = C2Config().with_10hz_d1()
    old = C2Controller.from_params(params, run_s8c.with_reapproach_variant(cfg, "f1only"))
    fresh = C2Controller.from_params(params, cfg)
    meta = run_s8c.refresh_restored_controller(old, fresh)
    lr = meta["lifted_reapproach"]
    assert lr["pickled"]["retrigger_window_s"] is None
    assert lr["in_use"]["retrigger_window_s"] == 2.0 == lr["fresh"]["retrigger_window_s"]
    assert lr["in_use"]["opposite_window_s"] == 0.8
    changed = {f["path"] for r in meta["replaced"] for f in r["changed_fields"]}
    assert {"c2.config.r8.lifted_reapproach.retrigger_window_s",
            "c2.config.r8.lifted_reapproach.retrigger_speed_factor",
            "c2.config.r8.lifted_reapproach.opposite_window_s"} <= changed
    assert old.config.r8.lifted_reapproach.retrigger_window_s == 2.0


def test_dataclass_diff_reads_missing_fields_as_class_defaults(run_s8c) -> None:
    from outrigger_sim.control.c2 import LiftedReapproachSettings

    old = LiftedReapproachSettings(enable=True)
    object.__delattr__(old, "retrigger_window_s")  # an older pickle without the key
    new = LiftedReapproachSettings(enable=True, retrigger_window_s=2.0)
    diff = run_s8c.dataclass_diff(old, new, "lr")
    assert diff == [{"path": "lr.retrigger_window_s", "old": "None", "new": "2.0"}]
