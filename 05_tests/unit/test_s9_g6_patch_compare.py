"""G6-0a comparator (``04_scripts/02_chrono/s9_g6_patch_compare.py``, dynamics / user decision 2026-10-28):
C-1 pre-contact 1e-12, C-2 / C-3 E3 / E4-type end and instant differences against sigma_bar h^2, C-4 P3a
agreement, on synthetic series."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import s9_g6_patch_compare as g  # noqa: E402

AREA = {"FL": 0.1071, "FR": 0.1071, "RL": 0.0607, "RR": 0.0607}


def _series(n=3000):
    t = 8.0 + np.arange(n) * 1e-3
    pad = np.zeros((n, 4))
    k = t >= 9.0
    pad[k] = np.array([120e3, 117e3, 75e3, 70e3]) * np.minimum(1.0, (t[k, None] - 9.0) / 0.5)
    crawler = np.where(t < 9.5, 3.8e5 - pad.sum(axis=1), 0.0)
    return {"t_s": t, "scm_pad_normal_N": pad, "scm_crawler_normal_N": crawler,
            "body_pos_m": np.column_stack([np.zeros(n), np.zeros(n), np.linspace(0, 0.01, n)]),
            "roll_pitch_deg": np.zeros((n, 2)), "rut_clearance_m": np.full(n, np.nan),
            "node_t_s": np.arange(30) * 0.1}


def test_identical_runs_pass() -> None:
    a, b = _series(), _series()
    k = g.first_contact_row(a, b)
    assert k == 1001  # first row with a pad normal > 0 (t = 9.001 s)
    assert g.pre_contact(a, b, k)["pass"]
    r = g.end_and_instant(a, b, AREA)
    assert r["C-2"]["pass"] and r["C-3"]["pass"]


def test_pre_contact_tolerance() -> None:
    a, b = _series(), _series()
    k = g.first_contact_row(a, b)
    a["body_pos_m"] = a["body_pos_m"].copy()
    a["body_pos_m"][500, 2] *= 1 + 5e-13
    assert g.pre_contact(a, b, k)["pass"]
    a["body_pos_m"][500, 2] *= 1 + 1e-9
    res = g.pre_contact(a, b, k)
    assert not res["pass"] and res["series"]["body_pos_m"]["max_rel"] > 1e-12
    c = _series()
    c["rut_clearance_m"] = c["rut_clearance_m"].copy()
    c["rut_clearance_m"][10] = 0.0  # NaN pattern differs
    assert not g.pre_contact(c, b, k)["pass"]


def test_end_and_instant_node_force_rule() -> None:
    a, b = _series(), _series()
    nf = g.node_forces_N(b, AREA)
    assert nf[0] == pytest.approx(120e3 / 0.1071 * 0.02 ** 2)
    a["scm_pad_normal_N"] = a["scm_pad_normal_N"].copy()
    a["scm_pad_normal_N"][-200:, 3] += 0.005 * nf[3]  # end tail below 0.01 sigma_bar h^2
    r = g.end_and_instant(a, b, AREA)
    assert r["C-2"]["pads"][3]["pass_end"] and r["C-3"]["pads"][3]["pass_instant"]
    a["scm_pad_normal_N"][-200:, 3] += 0.05 * nf[3]  # end diff 5.5 % of a node force: fails
    r = g.end_and_instant(a, b, AREA)
    assert not r["C-2"]["pads"][3]["pass_end"] and not r["C-2"]["pass"]
    c = _series()
    c["scm_pad_normal_N"] = c["scm_pad_normal_N"].copy()
    c["scm_pad_normal_N"][1500, 0] += 0.5 * nf[0]  # one node event that decays: max <= node force, end 0
    r = g.end_and_instant(c, b, AREA)
    assert r["C-3"]["pads"][0]["pass_instant"] and not r["C-3"]["pads"][0]["small_force"]
    c["scm_pad_normal_N"][1500, 0] += 1.0 * nf[0]  # 1.5 node forces: fails C-3
    assert not g.end_and_instant(c, b, AREA)["C-3"]["pass"]


def test_c3_dynamics_5_40_8() -> None:
    """dynamics_model.md 5.40.8 (G6-0a): one-row node flips up to 1.05 sigma_bar h^2 pass (FL 1.0095 in the
    run), width <= 2 rows, pad position diff <= 1 um on those rows; the end of an event pad is the 0.1 s
    mean (an instantaneous last-row tail of 1.7 % of the max passes when the mean is small)."""
    b = _series()
    nf = g.node_forces_N(b, AREA)
    n = len(b["t_s"])
    b["pad_sinkage_geometric_m"] = np.zeros((n, 4))

    def run(mod):
        a = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in b.items()}
        mod(a)
        return g.end_and_instant(a, b, AREA)["C-3"]["pads"]

    p = run(lambda a: a["scm_pad_normal_N"].__setitem__((1500, 0), a["scm_pad_normal_N"][1500, 0] + 1.0095 * nf[0]))
    assert p[0]["pass_instant"] and p[0]["spike_width_rows_max"] == 1 and p[0]["max_limit_N"] == pytest.approx(1.05 * nf[0])
    p = run(lambda a: a["scm_pad_normal_N"].__setitem__((1500, 0), a["scm_pad_normal_N"][1500, 0] + 1.06 * nf[0]))
    assert not p[0]["pass_instant"]

    def wide(a):
        a["scm_pad_normal_N"][1500:1503, 0] += 0.8 * nf[0]
    assert run(wide)[0]["spike_width_rows_max"] == 3 and not run(wide)[0]["pass_instant"]

    def moved(a):
        a["scm_pad_normal_N"][1500, 0] += 0.8 * nf[0]
        a["pad_sinkage_geometric_m"][1500, 0] += 2e-6
    assert not run(moved)[0]["pass_max"]

    def tail(a):  # FR-type: one node flip, last instantaneous row 1.7 % of the max, 0.1 s mean tiny
        a["scm_pad_normal_N"][1500, 1] += 0.9 * nf[1]
        a["scm_pad_normal_N"][-1, 1] += 0.017 * 0.9 * nf[1]
    p = run(tail)
    assert p[1]["last_diff_N"] / p[1]["max_diff_N"] == pytest.approx(0.017, rel=1e-6)
    assert p[1]["pass_end_c3"] and p[1]["pass_instant"]


def _p3a(t_lift=24.916, fpk=(123.7e3, 120.0e3, 77.5e3, 78.3e3), smax=0.58, within=True, d_pitch_min=-0.0439,
         end_pitch=0.10):
    return {"checks": {"P3a-1_within": within, "P3a-2_lifted": True, "P3a-3_within": True, "P3a-4_within": True,
                       "P3a-5_within": True},
            "P3a-2_liftoff": {"t_liftoff_s": t_lift}, "P3a-1_force_peak": {"F_peak_N": list(fpk)},
            "P3a-4_stroke": {"s_motor_max_m": [smax] * 4},
            "P3a-6_sinkage": {"geometric_at_liftoff_m": [0.0072] * 4, "geometric_end_m": [0.0076] * 4},
            "P3a-7_attitude": {"d_roll_range_deg": [-0.0099, 0.0], "d_pitch_range_deg": [d_pitch_min, 0.0001],
                               "end_roll_pitch_deg": [0.0001, end_pitch]}}


def test_p3a_agreement() -> None:
    """dynamics_model.md 5.40.5: lift-off <= 2 ms, ranges <= 2e-3 deg, end attitude <= 1e-3 deg."""
    nf = [450.0, 440.0, 490.0, 470.0]
    res = g.p3a_agreement(_p3a(), _p3a(), nf)
    assert res["pass"] and res["tolerances"]["liftoff_s"] == 2.0e-3
    assert g.p3a_agreement(_p3a(t_lift=24.918), _p3a(), nf)["pass"]  # 2 ms
    assert not g.p3a_agreement(_p3a(t_lift=24.919), _p3a(), nf)["pass"]  # 3 ms
    assert g.p3a_agreement(_p3a(d_pitch_min=-0.0454), _p3a(), nf)["pass"]  # range diff 1.5e-3 deg
    assert not g.p3a_agreement(_p3a(d_pitch_min=-0.0464), _p3a(), nf)["pass"]  # 2.5e-3 deg
    assert g.p3a_agreement(_p3a(end_pitch=0.1008), _p3a(), nf)["pass"]  # end 0.8e-3 deg
    assert not g.p3a_agreement(_p3a(end_pitch=0.1015), _p3a(), nf)["pass"]  # end 1.5e-3 deg
    assert not g.p3a_agreement(_p3a(fpk=(124.3e3, 120.0e3, 77.5e3, 78.3e3)), _p3a(), nf)["pass"]
    assert not g.p3a_agreement(_p3a(smax=0.5802), _p3a(), nf)["pass"]
    assert not g.p3a_agreement(_p3a(within=False), _p3a(), nf)["pass"]
