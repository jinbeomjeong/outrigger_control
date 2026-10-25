"""C-S8-40 (spec rev. 54 248.3 / 249 / 251 #8): twist-work recurrence ban with the forced
window masked, cluster counting, the narrowed reading correction delta_i = min(0.5 kN, 2 F_s,i)
on L2b-NSC only, the reference FLAG row, and (data test) the 768 recurrence list of 248.2."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s8_control as v

ROOT = Path(__file__).resolve().parents[2]
ML768 = ROOT / "07_results" / "S8" / "ml_main_20261025_090131"
AFFECTED = ROOT / "06_analysis" / "02_control" / "s8" / "s8_rev52_r51_affected.json"
RECURRENCE_768 = {"ML78_ep0", "ML78_ep1", "ML78_ep3", "ML00_ep5", "ML21_ep1", "ML42_ep6",
                  "ML33_ep4"}
"""Spec rev. 54 248.2: the seven 768 episodes with >= 2 clusters (all inside the affected 55)."""

U_TW = 1e-3  # m/s per leg along n -> n . u = 2e-3 m/s, P = 1e-3 (D - D0) W


def _bins_inputs(bin_work_J, *, t_ev: float = 10.0, span: float = 4.0):
    """Pad force / command whose 0.5 s twist-work bins are ``bin_work_J`` (bin k from the
    event); W_k = 0.5 s x 1e-3 x (D - D0) -> D - D0 = 2000 W_k."""
    t = np.round(np.arange(t_ev - 0.5, t_ev + span + 1e-9, 1e-3), 6)
    f = np.full((t.size, 4), 50_000.0)
    for k, w in enumerate(bin_work_J):
        m = (t >= t_ev + 0.5 * k - 1e-9) & (t < t_ev + 0.5 * (k + 1) - 1e-9)
        f[m, 0] += 2000.0 * w
    rec_t = np.round(np.arange(t_ev - 0.5, t_ev + span + 1e-9, 0.1), 6)
    u = np.zeros((rec_t.size, 4))
    u[rec_t >= t_ev - 1e-9] = np.array([1.0, -1.0, -1.0, 1.0]) * U_TW
    return {"t": t, "F_cyl": f}, {"t": rec_t, "u_applied": u}, t_ev


@pytest.mark.parametrize(("late", "n", "passed"), [
    ([30.0, -5.0, 40.0], 2, False),   # 251 #8 (ii): two clusters -> recurrence -> fail
    ([30.0, 40.0, -5.0], 1, True),    # one cluster (consecutive bins) -> pass
    ([10.0, 15.0, 5.0], 0, True),     # nothing over +20 J
])
def test_clusters_of_bins_over_20_J_after_1p5_s(late, n, passed) -> None:
    pads, rec, t_ev = _bins_inputs([0.0, 0.0, 0.0, *late, 0.0])
    w = v.twist_work_bins(pads, rec, t_ev, span_s=3.5)
    np.testing.assert_allclose(w["bins_J"][3:6], late, atol=0.05)
    assert w["n_clusters"] == n and w["passed"] is passed
    if n == 2:
        assert [a for a, _w in w["clusters"]] == [1.5, 2.5]
        assert w["max_cluster_J"] == pytest.approx(40.0, abs=0.1)
    if n == 1:
        assert w["clusters"][0][1] == pytest.approx(70.0, abs=0.1)


def test_bins_before_1p5_s_do_not_make_clusters() -> None:
    pads, rec, t_ev = _bins_inputs([100.0, -5.0, 100.0, 0.0, 30.0, 0.0])
    w = v.twist_work_bins(pads, rec, t_ev, span_s=3.0)
    assert w["n_clusters"] == 1 and w["passed"] is True


def test_forced_window_is_masked_to_done_plus_tail() -> None:
    # 251 #8 (i): large positive work inside the forced window [0, done 1.8 s + 0.1 s]
    pads, rec, t_ev = _bins_inputs([0.0, 0.0, 0.0, 200.0, 0.0, 30.0, 0.0])
    raw = v.twist_work_bins(pads, rec, t_ev, span_s=3.5)
    assert raw["n_clusters"] == 2 and raw["passed"] is False
    fw = {"start_s": 4.0, "done_s": 5.8, "end_s": 30.0, "others": "controller"}  # run-relative
    w = v.twist_work_bins(pads, rec, t_ev, span_s=3.5, forced=v.forced_rel_to_event(fw, 4.0))
    assert w["masked_s"] == [0.0, pytest.approx(1.9)]
    # only 1.901 .. 1.999 s left (the 1.900 s sample is inside the closed mask): 99 / 500
    assert w["bins_J"][3] == pytest.approx(200.0 * 99 / 500, abs=0.05)
    assert w["raw_bins_J"][3] == pytest.approx(200.0, abs=0.2)
    assert w["raw_max_bin_after_J"] == pytest.approx(200.0, abs=0.2)
    assert w["n_clusters"] == 2  # 40 J tail + 30 J later: still two separate clusters
    fw_long = {**fw, "done_s": 6.4}  # mask to 2.5 s covers the 200 J bin entirely
    w = v.twist_work_bins(pads, rec, t_ev, span_s=3.5,
                          forced=v.forced_rel_to_event(fw_long, 4.0))
    assert w["bins_J"][3] == 0.0 and w["n_clusters"] == 1 and w["passed"] is True


def test_forced_window_without_done_masks_to_the_end_not_judgeable() -> None:
    pads, rec, t_ev = _bins_inputs([0.0, 0.0, 0.0, 200.0, 0.0, 30.0, 0.0])
    fw = {"start_s": 0.0, "done_s": None, "end_s": 30.0}
    w = v.twist_work_bins(pads, rec, t_ev, span_s=3.5, forced=v.forced_rel_to_event(fw, 0.0))
    assert w["judged_bins"] == 0 and w["passed"] is None and w["max_cluster_J"] is None
    assert w["status"].startswith("not judgeable")
    assert w["masked_s"] == [0.0, None]


def test_work_clusters_end_at_unjudged_bins() -> None:
    edges = [1.5, 2.0, 2.5, 3.0]
    assert v.work_clusters(edges, [30.0, 30.0, 30.0, 30.0], [True, False, True, True]) == \
        [[1.5, 30.0], [2.5, 60.0]]


@pytest.mark.parametrize(("fs_N", "delta_N"), [(100.0, 200.0), (0.0, 0.0), (4000.0, 500.0),
                                                (250.0, 500.0)])
def test_reading_delta_is_min_half_kN_twice_seal(fs_N, delta_N) -> None:
    # 251 #8 (iii)
    pads = {"F_seal_limit": np.full((50, 4), fs_N)}
    np.testing.assert_allclose(v.reading_bias_delta_N(pads, "L2b_NSC"), [delta_N] * 4)


def test_reading_delta_zero_off_l2b_nsc_and_per_leg_median() -> None:
    # 251 #8 (iv): L1 engine (or no engine / no seal record) -> 0
    pads = {"F_seal_limit": np.full((50, 4), 4000.0)}
    for eng in ("L1R", "L1", None):
        np.testing.assert_allclose(v.reading_bias_delta_N(pads, eng), 0.0)
    np.testing.assert_allclose(v.reading_bias_delta_N({}, "L2b_NSC"), 0.0)
    fs = np.column_stack([np.full(9, 4000.0), np.full(9, 3330.0), np.zeros(9),
                          np.r_[np.zeros(4), np.full(5, 100.0)]])
    np.testing.assert_allclose(v.reading_bias_delta_N({"F_seal_limit": fs}, "L2b_NSC"),
                               [500.0, 500.0, 0.0, 200.0])


def test_reading_variants_default_vs_all_apply() -> None:
    t = np.arange(0.0, 1.0 + 1e-12, 1e-3)
    pads = {"t": t, "N_raw": np.tile([1000.0, 1000.0, 3000.0, 1000.0], (t.size, 1)),
            "F_seal_limit": np.tile([4000.0, 100.0, 4000.0, 0.0], (t.size, 1))}
    t10 = np.arange(0.1, 1.0, 0.1)
    lower = np.full((t10.size, 4), 10_000.0)
    out = v.reading_variants(t10, pads, lower, lower, np.full(4, 700.0), engine="L2b_NSC")
    np.testing.assert_allclose(out["corrected"]["lower_reading_N"][0] - 10_000.0,
                               [500.0, 200.0, 0.0, 0.0])
    np.testing.assert_allclose(out["all_apply"]["lower_reading_N"][0] - 10_000.0,
                               [500.0, 500.0, 0.0, 500.0])
    assert out["stats"]["delta_N"] == {"FL": 500.0, "FR": 200.0, "RL": 500.0, "RR": 0.0}
    assert out["stats"]["engine"] == "L2b_NSC"
    l1 = v.reading_variants(t10, pads, lower, lower, np.full(4, 700.0), engine="L1R")
    np.testing.assert_allclose(l1["corrected"]["lower_reading_N"], lower)


def _rt_run(work, variant="rt"):
    return {"rt": {"runs_after_event": 1, "retriggers": 0, "deferred": 0,
                   "starts_after_1.5_s": 0, "deferred_rel_s": [], "runs": [], "work": work},
            "reapproach_variant": variant}


def _w(clusters):
    return {"max_bin_after_J": max((w for _a, w in clusters), default=0.0),
            "raw_max_bin_after_J": 60.0, "clusters": clusters, "n_clusters": len(clusters),
            "max_cluster_J": max((w for _a, w in clusters), default=0.0),
            "passed": len(clusters) <= 1, "masked_s": None}


def test_rt_rows_flag_against_reference() -> None:
    cms = {"A": _rt_run(_w([[1.5, 75.0]])), "B": _rt_run(_w([[1.5, 30.0]])),
           "C": _rt_run(_w([[1.5, 30.0], [3.0, 25.0]]))}
    ref = {"A": {"max_cluster_J": 50.0}, "B": {"max_cluster_J": 29.0}, "C": None}
    rows = v.rt_rows(cms, ref, "768")
    judged = [r for r in rows if r["kind"] == "judged"]
    assert len(judged) == 1 and judged[0]["passed"] is False
    assert set(judged[0]["over"]) == {"C"}
    flag = [r for r in rows if "FLAG" in r["item"]][0]
    assert flag["passed"] is None and flag["kind"] == "record"
    assert set(flag["flagged"]) == {"A"}  # 75 - 50 = 25 > 20 J; B +1 J
    assert flag["value"]["missing_in_reference"] == ["C"]


@pytest.mark.skipif(not (ML768 / "episodes").is_dir(), reason="768 batch records not present")
def test_768_recurrence_list_equals_spec_248_2() -> None:
    # 251 #8 (v): the rev. 54 rule over all 768 episodes (forced window masked) fails exactly
    # the seven of 248.2, all inside the affected 55
    eps = sorted(p for p in (ML768 / "episodes").iterdir()
                 if p.is_dir() and not p.name.startswith("_"))
    fails = set()
    for d in eps:
        w = v.ml_twist_work_of_dir(d)
        if w is not None and w["passed"] is False:
            fails.add(d.name)
    assert fails == RECURRENCE_768
    affected = set(json.loads(AFFECTED.read_text(encoding="utf-8"))["affected"])
    assert fails <= affected
