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


def _p3a(t_lift=24.916, fpk=(123.7e3, 120.0e3, 77.5e3, 78.3e3), smax=0.58, within=True):
    return {"checks": {"P3a-1_within": within, "P3a-2_lifted": True, "P3a-3_within": True, "P3a-4_within": True,
                       "P3a-5_within": True},
            "P3a-2_liftoff": {"t_liftoff_s": t_lift}, "P3a-1_force_peak": {"F_peak_N": list(fpk)},
            "P3a-4_stroke": {"s_motor_max_m": [smax] * 4},
            "P3a-6_sinkage": {"geometric_at_liftoff_m": [0.0072] * 4, "geometric_end_m": [0.0076] * 4},
            "P3a-7_attitude": {"d_roll_range_deg": [-0.0099, 0.0], "d_pitch_range_deg": [-0.0439, 0.0001]}}


def test_p3a_agreement() -> None:
    nf = [450.0, 440.0, 490.0, 470.0]
    assert g.p3a_agreement(_p3a(), _p3a(), nf)["pass"]
    assert g.p3a_agreement(_p3a(t_lift=24.917), _p3a(), nf)["pass"]  # one 1 ms row
    assert not g.p3a_agreement(_p3a(t_lift=24.919), _p3a(), nf)["pass"]
    assert not g.p3a_agreement(_p3a(fpk=(124.3e3, 120.0e3, 77.5e3, 78.3e3)), _p3a(), nf)["pass"]
    assert not g.p3a_agreement(_p3a(smax=0.5802), _p3a(), nf)["pass"]
    assert not g.p3a_agreement(_p3a(within=False), _p3a(), nf)["pass"]
