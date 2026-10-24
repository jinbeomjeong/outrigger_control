"""verify/s7_control (control ③ pair rows, READY hold, NSC read-out) and the L2b pad record's
centred moving mean (no Chrono run)."""

from __future__ import annotations

import numpy as np
import pytest

from outrigger_sim.verify.s7_control import (
    PAIR_FLAG_N,
    nsc_readout_row,
    pair_rows,
    ready_hold_metrics,
    ready_hold_rows,
)


SLOW_ITEM = ("pair L2b - L1: D8 min true cylinder force after crawler lift-off, 1 s centred "
             "mean [kN]")
RAW_ITEM = "pair L2b - L1: D8 min true cylinder force after crawler lift-off, raw 1 ms [kN]"


def test_pair_rows_difference_and_flag() -> None:
    """C-R18: the flag is on the slow-component row only; the raw row is a record."""
    l2b = {"case": "L2b_x", "min_cyl_slow_after_liftoff_kN": 40.0,
           "min_cyl_after_liftoff_kN": 30.0, "t_ready_minus_touch_s": 30.0,
           "final_twist_kN": 1.0, "att_err_last5_maxabs_deg": 0.01,
           "osc_half_amp_kN": [1.0, 2.0, 10.0, 4.0]}
    l1 = {"min_cyl_slow_after_liftoff_kN": 42.5, "min_cyl_after_liftoff_kN": 40.0,
          "t_ready_minus_touch_s": 29.0, "final_twist_kN": 0.5,
          "att_err_last5_maxabs_deg": 0.02, "min_cyl_reanchor_kN": 20.0,
          "osc_half_amp_kN": [1.0, 2.0, 5.0, 4.0]}
    rows = {r["item"]: r for r in pair_rows(l2b, l1, l1_source="test")}
    d8 = rows[SLOW_ITEM]
    assert d8["value"] == pytest.approx(-2.5)
    assert d8["pair_flag"] is True and d8["passed"] is None and d8["kind"] == "pair"
    raw = rows[RAW_ITEM]
    assert raw["value"] == pytest.approx(-10.0) and "pair_flag" not in raw
    assert rows["pair L2b - L1: READY - TOUCH end [s]"]["value"] == pytest.approx(1.0)
    missing = rows["pair L2b - L1: min true cylinder force inside REANCHOR [kN]"]
    assert missing["value"] is None
    osc = [r for item, r in rows.items() if "half-amplitude" in item]
    assert [r["value"] for r in osc] == pytest.approx([0.0, 0.0, 5.0, 0.0])
    assert "ratio 2.00" in osc[2]["note"] and all(r["passed"] is None for r in osc)
    l1["min_cyl_slow_after_liftoff_kN"] = 40.0 + PAIR_FLAG_N / 1e3 - 1e-6
    d8 = pair_rows(l2b, l1, l1_source="t")[0]
    assert d8["item"] == SLOW_ITEM and d8["pair_flag"] is False


def test_pair_rows_without_l1() -> None:
    rows = pair_rows({"case": "c", "min_cyl_after_liftoff_kN": 1.0}, None, l1_source="none")
    assert all(r["value"] is None and r["passed"] is None for r in rows)


def test_ready_hold() -> None:
    ph = [(0.0, "check"), (2.0, "touch"), (20.0, "level"), (40.0, "probe"), (50.0, "ready")]
    rh = ready_hold_metrics(ph, 115.0)
    assert rh["first_ready_s"] == 50.0 and rh["held_s"] == 65.0 and rh["left_ready"] is False
    rows = ready_hold_rows({"case": "s", "phases": ph, "times_s": {"end": 115.0},
                            "att_err_last5_maxabs_deg": 0.05})
    assert [r["passed"] for r in rows] == [True, True]
    ph2 = [*ph, (70.0, "level"), (80.0, "ready")]
    rh2 = ready_hold_metrics(ph2, 115.0)
    assert rh2["held_s"] == 20.0 and rh2["left_ready"] is True
    assert ready_hold_rows({"case": "s", "phases": ph2, "times_s": {"end": 115.0}})[0][
        "passed"] is False
    assert ready_hold_metrics([(0.0, "check")], 10.0)["first_ready_s"] is None


def test_nsc_readout_row() -> None:
    ok = nsc_readout_row("c", {"format": "l2b_pad_record_v1", "contact_window_s": 0.02})
    assert ok["passed"] is True
    assert nsc_readout_row("c", {"format": "l2b_pad_record_v1",
                                 "contact_window_s": 0.01})["passed"] is False
    assert nsc_readout_row("c", None)["passed"] is False


def test_centred_moving_mean() -> None:
    pytest.importorskip("pychrono")  # chrono package path (module itself is numpy only)
    from outrigger_sim.chrono.l2b_pad_record import centred_moving_mean

    x = np.arange(10.0)[:, None, None] * np.ones((1, 2, 3))
    y = centred_moving_mean(x, 4)
    # window [k-2, k+2): interior mean = k - 0.5
    assert y[5, 0, 0] == pytest.approx(4.5)
    assert y[0, 1, 2] == pytest.approx(0.5)  # truncated [0, 2)
    assert y.shape == x.shape
    assert np.array_equal(centred_moving_mean(x, 1), x)
