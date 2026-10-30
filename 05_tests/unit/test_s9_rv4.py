"""D2 / RV4 (study D on Chrono, user decision 2026-10-30): ``run_S9.py level --pad-start-gap`` (SCM node levels under
one pad after the settle), the spec 426.6 TOUCH record and the ``s9_batch.py run RV4`` rows. Small SCM systems only
(no machine model, no closed loop)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "04_scripts" / "02_chrono", ROOT / "04_scripts" / "03_control" / "s9"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import run_S9  # noqa: E402

RV4_NAMES = ["P3b_J2_B_top_Fs4_sgRRd150", "P3b_J2_B_top_Fs4_sgFLg20"]
Z_PLANE = -1.0509  # crawler bottom z of the machine model [m] (frame height of the SCM plane)
GRID = 0.01


def _ch():
    return pytest.importorskip("pychrono")


def _terrain(system):
    ch = _ch()
    import pychrono.vehicle as veh

    t = veh.SCMTerrain(system, False)
    t.SetReferenceFrame(ch.ChCoordsysd(ch.ChVector3d(0.0, 0.0, Z_PLANE), ch.QUNIT))
    t.SetSoilParameters(2.0e6, 0.0, 1.1, 0.0, 30.0, 0.01, 2.0e8, 3.0e4)
    return t


def _system():
    ch = _ch()
    s = ch.ChSystemSMC()
    s.SetCollisionSystemType(ch.ChCollisionSystem.Type_BULLET)
    s.SetGravitationalAcceleration(ch.ChVector3d(0.0, 0.0, -9.80665))
    s.SetNumThreads(1, 1, 1)
    return s


def _square(cx, cy, z, half=0.165):
    return np.array([[cx - half, cy - half, z], [cx + half, cy - half, z], [cx + half, cy + half, z],
                     [cx - half, cy + half, z]])


# ------------------------------------------------------------------------------------------- parsing / CLI
def test_parse_pad_start_gap() -> None:
    assert run_S9.parse_pad_start_gap(None) is None and run_S9.parse_pad_start_gap("") is None
    assert run_S9.parse_pad_start_gap("FL:g20") == {"leg": "FL", "kind": "gap", "value_mm": 20.0, "text": "FL:g20"}
    assert run_S9.parse_pad_start_gap("RR:d150")["kind"] == "delta"
    for bad in ("XX:g20", "FL:x20", "FL:g", "FL20", "FL:g2"):
        with pytest.raises(ValueError):
            run_S9.parse_pad_start_gap(bad)


def test_option_absent_leaves_no_attribute() -> None:
    """Without --pad-start-gap the namespace has no key (result.json args unchanged), run_level makes no call."""
    base = ["level", "--soil", "J2", "--approved", "--case", "x", "--out-root", "x"]
    a = run_S9.build_parser().parse_args(base)
    assert not hasattr(a, "pad_start_gap") and "pad_start_gap" not in vars(a)
    assert run_S9.parse_pad_start_gap(getattr(a, "pad_start_gap", None)) is None
    b = run_S9.build_parser().parse_args(base[:-4] + ["--pad-start-gap", "RR:d150"] + base[-4:])
    assert b.pad_start_gap == "RR:d150"


def test_touch_limits_are_the_harness_copy() -> None:
    import s9_soil_slope as ss

    assert run_S9.TOUCH_FLAG_LIMITS == ss.TOUCH_FLAG_LIMITS


# ------------------------------------------------------------------------------------ D2 on a real SCMTerrain
@pytest.mark.parametrize("text, tilt_deg", [("FL:g20", 0.0), ("FL:g110", 1.5), ("RR:d150", 0.0), ("RR:d60", 2.0)])
def test_start_gap_within_tolerance(text, tilt_deg) -> None:
    """Applied start gap = target +- 0.1 mm (spec 426.7 T-5 on SCM), also with a tilted leg axis; levels persist."""
    ch = _ch()
    s = _system()
    t = _terrain(s)
    t.Initialize(8.0, 6.0, GRID)
    g0_vertical = 0.3396
    outline = _square(1.62, -0.93, Z_PLANE + g0_vertical)
    outline[0, 2] -= 0.002  # pad hanging slightly tilted: the lowest vertex sets the gap
    a = math.radians(tilt_deg)
    axis = np.array([math.sin(a), 0.0, -math.cos(a)])
    spec = run_S9.parse_pad_start_gap(text)
    rec = run_S9.apply_scm_pad_start_gap(t, (0.0, 0.0, Z_PLANE), np.eye(3), GRID, outline, axis, spec)
    g0 = (g0_vertical - 0.002) / math.cos(a)
    target = spec["value_mm"] * 1e-3 if spec["kind"] == "gap" else g0 + spec["value_mm"] * 1e-3
    assert rec["check_ok"] and abs(rec["g_start_mm"] - target * 1e3) <= 0.1
    assert rec["g0_mm"] == pytest.approx(g0 * 1e3, abs=1e-9)
    assert rec["surface_shift_m"] == pytest.approx((g0 - target) * math.cos(a), abs=1e-12)
    # every node of the box got the level; neighbours outside stay at the plane
    h_in = t.GetHeight(ch.ChVector3d(1.62 + 0.165 + 0.14, -0.93, 0.0))
    h_out = t.GetHeight(ch.ChVector3d(1.62 + 0.165 + 0.20, -0.93, 0.0))
    assert h_in == pytest.approx(rec["surface_height_after_m"], abs=1e-12) and h_out == pytest.approx(Z_PLANE)
    s.DoStepDynamics(1.0e-3)  # nothing touches: the node levels stay
    assert run_S9._surface_gap_m(t, outline, math.cos(a))[0] == pytest.approx(rec["g_start_mm"] * 1e-3, abs=1e-12)


def test_start_gap_refuses_a_loaded_pad_and_slopes() -> None:
    s = _system()
    t = _terrain(s)
    t.Initialize(8.0, 6.0, GRID)
    spec = run_S9.parse_pad_start_gap("FL:g20")
    with pytest.raises(ValueError, match="above the SCM surface"):
        run_S9.apply_scm_pad_start_gap(t, (0, 0, Z_PLANE), np.eye(3), GRID, _square(0, 0, Z_PLANE + 0.01),
                                       (0, 0, -1), spec)
    rot = np.array([[1, 0, 0], [0, math.cos(0.05), -math.sin(0.05)], [0, math.sin(0.05), math.cos(0.05)]])
    with pytest.raises(ValueError, match="flat floor"):
        run_S9.apply_scm_pad_start_gap(t, (0, 0, Z_PLANE), rot, GRID, _square(0, 0, Z_PLANE + 0.3), (0, 0, -1), spec)


def _drop_box(delta_zero_call: bool) -> np.ndarray:
    """A 300 kg box dropped from 60 mm onto SCM (own active domain), optionally with the D2 call at Δ = 0 before the
    first step; returns the position / SCM force history."""
    ch = _ch()
    s = _system()
    t = _terrain(s)
    box = ch.ChBodyEasyBox(0.33, 0.33, 0.1, 2755.0, False, True, ch.ChContactMaterialSMC())
    box.SetPos(ch.ChVector3d(1.62, -0.93, Z_PLANE + 0.06 + 0.05))
    s.Add(box)
    t.AddActiveDomain(box, ch.ChVector3d(0, 0, -0.05), ch.ChVector3d(0.5, 0.5, 0.2))
    t.Initialize(8.0, 6.0, GRID)
    if delta_zero_call:
        rec = run_S9.apply_scm_pad_start_gap(t, (0.0, 0.0, Z_PLANE), np.eye(3), GRID,
                                             _square(1.62, -0.93, Z_PLANE + 0.06), (0, 0, -1),
                                             run_S9.parse_pad_start_gap("FL:d0"))
        assert rec["surface_shift_m"] == 0.0 and rec["n_nodes"] > 3000
    out = []
    f, m = ch.ChVector3d(), ch.ChVector3d()
    for _ in range(500):
        s.DoStepDynamics(5.0e-4)
        p = box.GetPos()
        t.GetContactForceBody(box, f, m)
        out.append([p.x, p.y, p.z, f.x, f.y, f.z, m.x, m.y, m.z])
    return np.array(out)


def test_delta_zero_is_bit_identical_on_scm() -> None:
    """Δ = 0 (fresh node records at the initial level) leaves the SCM contact history bit for bit; the box lands
    (non-zero force) within the run."""
    a, b = _drop_box(False), _drop_box(True)
    assert np.abs(a[:, 5]).max() > 1000.0
    assert np.array_equal(a, b)


# -------------------------------------------------------------------------------------------------- TOUCH
def _rows(n, contact_from, latch_from, att_step=0.01):
    rows, ts, pn = [], [], []
    for k in range(n):
        t = 100.0 + 0.1 * (k + 1)
        ph = "check" if k < 2 else ("touch" if k < n - 2 else "level")
        rows.append({"t_s": t, "c2_phase": ph, "c2_touched": [k >= latch_from] * 4,
                     "s_ref_m": [0.002 * (k + 1)] * 4, "roll_pitch_deg": [0.0, att_step * k]})
        for m in range(100):
            ts.append(t - 0.1 + 0.001 * (m + 1))
            pn.append([0.0 if k < contact_from else 50.0] * 4)
    return rows, {"t_s": np.array(ts), "scm_pad_normal_N": np.array(pn)}


def test_touch_record_flags_match_the_harness_definition() -> None:
    """Same synthetic case as the harness test (test_426_start_gap_and_sets.test_touch_record_flags): contact from
    period 10, latch at 40 -> post-contact stroke 62 mm (T-3'), latch 3.1 s after the contact (T-2'), no T-4."""
    rows, series = _rows(42, 10, 40)
    rec = run_S9.touch_record_s9(rows, series, "FL", 100.0)
    leg = rec["legs"]["FL"]
    assert leg["first_contact_s"] == pytest.approx(1.0) and leg["latch_s"] == pytest.approx(4.1)
    assert leg["post_contact_stroke_mm"] == pytest.approx(82.0 - 20.0)
    assert leg["latch_after_contact_s"] == pytest.approx(3.1)
    assert rec["flags"] == ["T-3'", "T-2'"]
    rows, series = _rows(42, 10, 12, att_step=0.05)
    rec = run_S9.touch_record_s9(rows, series, "FL", 100.0)
    assert rec["flags"] == ["T-4"]  # 0.05 x 37 = 1.85 deg
    assert run_S9.touch_record_s9([{"t_s": 1.0}], series, None, 0.0)["has_touch"] is False


# --------------------------------------------------------------------------------------------- RV4 rows
def _batches():
    import s9_batch

    return s9_batch, s9_batch.batches()


def test_rv4_rows_are_p3b_j2_plus_the_start_gap() -> None:
    s9_batch, b = _batches()
    rows = b["RV4"]
    assert [r["case"] for r in rows] == RV4_NAMES
    pair = {r["case"]: r for r in b["P3b"]}["P3b_J2_B_top_Fs4"]["argv"]
    for r, gap in zip(rows, ("RR:d150", "FL:g20")):
        assert r["argv"] == pair[:-1] + ["--pad-start-gap", gap, pair[-1]]
        a = run_S9.build_parser().parse_args(r["argv"][len(s9_batch.RUN):] + ["--case", r["case"], "--out-root", "x"])
        assert a.pad_start_gap == gap and (a.soil, a.pad_variant, a.duration, a.fs_kN) == ("J2", "dwg_rear250",
                                                                                          120.0, 4.0)
        assert run_S9.p36_ready_limit(vars(a))["limit_s"] == 100.0
        assert r["est_s"] == r["est_pool_s"][r["planned_pool"]] and r["note"].startswith("RV4 ")
    assert [r["est_pool_s"] for r in rows] == [{"pcore": 7200.0, "ecore": 10800.0},
                                               {"pcore": 6900.0, "ecore": 10300.0}]
    assert not set(RV4_NAMES) & {r["case"] for r in run_S9.case_plan()}


def test_rv4_harness_ids_exist() -> None:
    import s9_soil_slope as ss

    h = {c.case_id: c for c in ss.build_cases(("H8",))}
    for c in run_S9.rv4_cases():
        hc = h[c["harness_case"]]
        spec = run_S9.parse_pad_start_gap(c["pad_start_gap"])
        assert tuple(hc.start_gap) == (spec["leg"], spec["kind"], spec["value_mm"])
        assert (hc.soil, run_S9.P3B_PAD[hc.pad], hc.level, hc.fs_kN) == (c["soil"], c["pad_variant"], "top", 4.0)


@pytest.mark.parametrize("argv", [["run", "RV4", "--parallel", "1", "--parallel-e", "1", "--e-cases",
                                   "P3b_J2_B_top_Fs4_sgFLg20"], ["run", "RV4", "--parallel", "2"]])
def test_rv4_schedule(argv) -> None:
    s9_batch, b = _batches()
    kw = s9_batch.schedule_args(s9_batch.build_parser().parse_args(argv), argv)
    q = s9_batch.schedule_cases(b["RV4"], e_cases=kw["e_cases"], parallel_e=kw["parallel_e"])
    if kw["parallel_e"]:
        assert [c["case"] for c in q["pcore"]] == RV4_NAMES[:1] and [c["case"] for c in q["ecore"]] == RV4_NAMES[1:]
    else:
        assert [c["case"] for c in q["pcore"]] == RV4_NAMES
