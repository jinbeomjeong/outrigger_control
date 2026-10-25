"""C-S8-34 (``s6_control_spec.md`` rev. 51 225, U-S8-44 / 47): FAULT cause split and the
U-S8-44 protective stop, no duplicate event-leg failure, ML-2 applied commands, ML tags
(``fault_tail``, ``plant_rod_collapse``, ``reapproach_pingpong``), and the main ML 768 rejudge
(rev. 51 expected values) when its verify file is present."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from outrigger_sim.verify import s8_control as s8

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "07_results" / "S8" / "ml_main_20261025_090131"
F_MIN = 9414.58911


def _quat_wxyz_roll(roll_rad: float, n: int) -> np.ndarray:
    q = np.zeros((n, 4))
    q[:, 0] = np.cos(roll_rad / 2)
    q[:, 1] = np.sin(roll_rad / 2)
    return q


def _pads(n: int = 2000, *, f_kN: float = 60.0, lift_leg: int | None = None,
          roll_deg: float = 0.0) -> dict[str, np.ndarray]:
    t = 3.0 + 1e-3 * np.arange(n)
    f = np.full((n, 4), f_kN * 1e3)
    air = np.zeros((n, 4), bool)
    if lift_leg is not None:
        air[n // 2:n // 2 + 20, lift_leg] = True
    return {"t": t, "F_cyl_min_interval": f, "F_cyl_mean_20ms": f, "airborne": air,
            "body_quat_wxyz": _quat_wxyz_roll(np.radians(roll_deg), n)}


# --- ① cause ---------------------------------------------------------------------------------


def test_operating_index() -> None:
    assert s8.operating_index([4.4, 0.0]) == pytest.approx(1.0)
    assert s8.operating_index([1.4636, -2.5523]) == pytest.approx(1.1302, abs=1e-4)
    assert s8.operating_index(None) is None


def test_classify_fault_sources() -> None:
    assert s8.classify_fault(None, [], None, None, soft_max_m=0.6948, margin_m=1e-3) is None
    ev = s8.classify_fault(10.0, [(9.9, "FAULT_STROKE_END:RR")], None, None,
                           soft_max_m=0.6948, margin_m=1e-3)
    assert ev["cause"] == "stroke_end" and ev["source"] == "event" and ev["legs"] == ["RR"]
    se = s8.classify_fault(10.0, [(5.0, "FAULT_HEAD_PRESSURE:FL")], None, None,
                           soft_max_m=0.6948, margin_m=1e-3)
    assert se["cause"] == "sensor" and se["legs"] == ["FL"]
    t = np.arange(0.0, 10.05, 0.1)
    s = np.full((t.size, 4), 0.5)
    s[t >= 7.9, 3] = 0.6950  # RR at the end for the last 2 s before the FAULT
    rec = s8.classify_fault(10.0, [], t, s, soft_max_m=0.6948, margin_m=1e-3)
    assert rec["cause"] == "stroke_end" and rec["source"] == "record" and rec["legs"] == ["RR"]
    s[t >= 9.0, 3] = 0.6950
    s[(t >= 7.9) & (t < 9.0), 3] = 0.69  # only 1 s at the end: not the controller's 2 s rule
    unk = s8.classify_fault(10.0, [], t, s, soft_max_m=0.6948, margin_m=1e-3)
    assert unk["cause"] == "unknown"


def test_stroke_end_protective_rule() -> None:
    p = _pads()
    tf = 0.5  # relative (t0 = 3.0)
    ok = s8.stroke_end_protective(p, 3.0, tf, [1.4636, -2.5523], F_MIN, [0.0, 0.0])
    assert ok["passed"] and ok["outside_operating"] and ok["lifted_legs"] == []
    inside = s8.stroke_end_protective(p, 3.0, tf, [0.5, 0.5], F_MIN, [0.0, 0.0])
    assert not inside["passed"]  # inside the operating diamond: fails
    low = s8.stroke_end_protective(_pads(f_kN=14.0), 3.0, tf, [1.46, -2.55], F_MIN, None)
    assert not low["passed"]  # 14 kN < F_min + 5 kN = 14.41 kN
    lift = s8.stroke_end_protective(_pads(lift_leg=2), 3.0, tf, [1.46, -2.55], F_MIN, None)
    assert not lift["passed"] and lift["lifted_legs"] == ["RL"]
    att = s8.stroke_end_protective(_pads(roll_deg=0.25), 3.0, tf, [1.46, -2.55], F_MIN, None)
    assert not att["passed"] and att["att_err_max_deg"][0] == pytest.approx(0.25, abs=1e-9)


# --- ② no duplicate failure --------------------------------------------------------------------


def test_event_leg_row_fault_gate() -> None:
    t = np.arange(0.0, 6.0, 1e-3)
    air = np.zeros((t.size, 4), bool)
    air[(t > 1.0) & (t < 1.5), 3] = True
    zb = np.zeros((t.size, 4))
    kw = {"t3_s": 0.82, "fault_t_s": 4.0}
    gated = s8.settle_lift_split(t, air, zb, 1.0, "RR", 0.02, 0.2, **kw)
    assert gated["event_pass"] is False  # the MLJ default: FAULT 0 in the event-leg row
    free = s8.settle_lift_split(t, air, zb, 1.0, "RR", 0.02, 0.2, fault_gate=False,
                                fault_cause="stroke_end", **kw)
    assert free["event_pass"] is True and free["fault_t_s"] == 4.0
    rows = s8.u_s8_32_rows("X", free)
    assert rows[1]["passed"] is True and "judged in the ML-0 FAULT rows" in rows[1]["note"]


# --- ③ applied commands ------------------------------------------------------------------------


def test_rod_fallback_command_context() -> None:
    tc = np.arange(0.0, 1.0, 0.1)
    issued = np.zeros((tc.size, 4))
    issued[5, 3] = -2.73e-5
    issued[6, 3] = 5.11e-3
    rec = {"t": tc + 3.0, "u_applied": np.zeros((tc.size, 4))}
    rec["u_applied"][6, 3] = -1.7e-5
    rec["u_applied"][5, 3] = 1.3e-22
    e = {"t_s": 0.6, "leg": "RR"}
    s8.rod_fallback_command_context(e, tc, issued, rec, None, 3.0)
    assert e["issued_this_sample_mm_s"] == pytest.approx(5.11)
    assert e["applied_this_period_issued_mm_s"] == pytest.approx(-0.0273)
    assert e["applied_past_period_issued_mm_s"] == 0.0
    assert e["plant_u_applied_now_mm_s"] == pytest.approx(-0.017)
    assert e["plant_locked_past_period"] is True
    assert "applied this period (issued t_k-1) -0.0273" in s8._rod_fallback_text(
        {**e, "reason": "D1"})


# --- ④ tags ------------------------------------------------------------------------------------


def test_reapproach_pingpong_window() -> None:
    names = [(10.0 + x, f"leg_reapproach_start:{leg}") for x, leg in
             ((0.5, "FL"), (1.7, "FR"), (2.1, "RR"), (2.9, "RL"))]
    names += [(13.3, "leg_reapproach_contact:RL")]
    pp = s8.reapproach_pingpong(names, 10.0, 30.0, 3.0)
    assert pp["late_starts"] == 3 and pp["leg_changes"] == 3
    w = pp["window"]
    assert w["start_s"] == pytest.approx(11.5) and w["end_s"] == pytest.approx(14.3)
    assert w["start_engine_s"] == pytest.approx(14.5)
    two = s8.reapproach_pingpong(names[:3], 10.0, 30.0, 3.0)
    assert two["window"] is None
    assert s8.reapproach_pingpong(names, None, 30.0, 3.0) is None


def test_plant_rod_collapse_locked_only() -> None:
    n = 400
    t = 3.0 + 1e-3 * np.arange(n)
    air = np.zeros((n, 4), bool)
    air[204:, 3] = True  # RR lift-off at 3.204 s
    air[150:, 0] = True  # FL lift-off at 3.150 s with an open valve
    rp = np.full((n, 4), 100e5)
    rp[205:, 3] = 3e5
    rp[151:, 0] = 3e5
    pads = {"t": t, "airborne": air, "rod_pressure": rp, "head_pressure": rp * 0.4}
    rec = {"t": np.array([3.0, 3.1, 3.2, 3.3]), "u_applied": np.zeros((4, 4))}
    rec["u_applied"][1, 0] = 1e-3  # FL valve open over 3.1 .. 3.2
    out = s8.plant_rod_collapse(pads, rec, 3.0)
    assert [x["leg"] for x in out] == ["RR"]
    x = out[0]
    assert x["liftoff_s"] == pytest.approx(0.204) and x["from_10hz_boundary_ms"] == pytest.approx(4.0)
    assert x["start_s"] == pytest.approx(-0.096) and x["end_s"] == pytest.approx(0.504)
    assert s8.plant_rod_collapse(pads, None, 3.0) == []


def test_valve_release_and_collapse_window_extension() -> None:
    # valve from ~0 towards -2.733e-5 m/s at the 63.2 s row: |u| crosses 1e-6 after 3.73 ms
    t10 = np.array([63.1, 63.2, 63.3])
    ev = s8.valve_release_events(t10, np.array([3.5e-22, 1.3e-22, -1.727e-5]),
                                 np.array([0.0, -2.733e-5, -2.733e-5]), 0.1, 1e-6, 63.4)
    assert [k for _, k, _, _ in ev] == ["release"]
    assert ev[0][0] - 63.2 == pytest.approx(-0.1 * np.log(1 - 1e-6 / 2.733e-5), rel=1e-6)
    n = 1000
    t = 63.0 + 1e-3 * np.arange(n)
    air = np.zeros((n, 4), bool)
    air[204:557, 3] = True  # lift-off 63.204 s, re-contact 63.557 s
    pads = {"t": t, "airborne": air}
    col = [{"leg": "RR", "liftoff_s": 0.204, "liftoff_engine_s": 63.204, "start_s": -0.096,
            "end_s": 0.504, "start_engine_s": 62.904, "end_engine_s": 63.504}]
    rel = [{"leg": "RR", "t_release_s": 0.2037, "t_boundary_s": 0.2, "t_x_ms": 3.7,
            "u_new_m_s": -2.733e-5, "rod_jump_bar": -106.3},
           {"leg": "FL", "t_release_s": 0.2, "t_boundary_s": 0.2, "t_x_ms": 0.0,
            "u_new_m_s": 5e-3, "rod_jump_bar": -80.0}]
    rest = s8.link_collapse_releases(col, rel, pads, 63.0, 0.020924)
    assert [r["leg"] for r in rest] == ["FL"]  # the matched release is the collapse itself
    assert col[0]["end_engine_s"] == pytest.approx(63.657)  # re-contact + 0.1 s (ML88_ep0)
    col[0].update(end_s=0.504, end_engine_s=63.504)
    rel[0]["u_new_m_s"] = -0.25 * 0.020924  # a real opening: window stays lift-off + 0.3 s
    s8.link_collapse_releases(col, rel, pads, 63.0, 0.020924)
    assert col[0]["end_engine_s"] == pytest.approx(63.504)


# --- main ML 768 rejudge (rev. 51 expected values) ---------------------------------------------


@pytest.mark.skipif(not (MAIN / "verify_S8ML.json").exists(), reason="main ML batch not present")
def test_main_ml_rejudge_expected() -> None:
    d = json.loads((MAIN / "verify_S8ML.json").read_text(encoding="utf-8"))
    if "C-S8-34" not in d["meta"].get("judge_revision", ""):
        pytest.skip("verify_S8ML.json not yet rejudged with C-S8-34")
    rows = d["rows"]
    ml0 = [r for r in rows if r["item"].startswith("ML-0") and r["kind"] == "judged"]
    assert all(r["passed"] is not False for r in ml0)
    se = [r for r in ml0 if "protective stop" in r["item"]]
    assert sorted(r["case"] for r in se) == ["ML28_ep5", "ML63_ep2", "ML87_ep6"]
    ev = [r["case"] for r in rows if "U-S8-32 event legs" in r["item"] and r["passed"] is False]
    adj = [r["case"] for r in rows if "U-S8-32 adjacent" in r["item"] and r["passed"] is False]
    assert ev == ["ML78_ep0"] and sorted(adj) == ["ML78_ep0", "ML78_ep3"]
    tags = d["ml_tags"]
    assert len(tags["reapproach_pingpong"]) == 6
    assert sum(len(v) for v in tags["plant_rod_collapse"].values()) == 7
    assert sorted(tags["fault_tail"]) == ["ML28_ep5", "ML63_ep2", "ML87_ep6"]
    n_rel = sum(len(v) for c, v in tags["plant_release_rod_step"].items() if "_ep" in c)
    assert n_rel == 871  # hydraulics 12.3: 878 releases with a > 20 bar step, 7 are collapses
    ends = {(c, x["leg"]): x["end_engine_s"] for c, v in tags["plant_rod_collapse"].items()
            for x in v}
    assert ends[("ML88_ep0", "RR")] == pytest.approx(63.657, abs=2e-3)
    assert ends[("ML28_ep6", "RL")] == pytest.approx(67.384, abs=2e-3)
    assert ends[("ML81_ep5", "RR")] == pytest.approx(69.902, abs=2e-3)
