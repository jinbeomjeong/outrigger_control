"""A1 / RV5 (study A on Chrono, user decision 2026-10-30): ``run_S9.py level --soil-event`` (the event leg's own SCM
terrain frame moved by -d P345), the E-1 .. E-7 adapter to the harness judge, the s9_batch ``depends_on`` rows. Small
SCM systems and synthetic run folders only (no machine model, no closed loop)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT / "04_scripts" / "02_chrono", ROOT / "04_scripts" / "03_control" / "s9"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import run_S9  # noqa: E402

Z_PLANE = -1.0509
GRID = 0.01
BASES = ["P3b_J2_B_top_Fs0_spFLJ2_base", "P3b_J2_B_top_Fs8_spRRJ2_base"]
EVENTS = ["P3b_J2_B_top_Fs0_spFLJ2_RE1bF", "P3b_J2_B_top_Fs8_spRRJ2_FS24"]
RV5_NAMES = [BASES[0], EVENTS[0], BASES[1], EVENTS[1]]


def _ch():
    return pytest.importorskip("pychrono")


def _system_terrain():
    ch = _ch()
    import pychrono.vehicle as veh

    s = ch.ChSystemSMC()
    s.SetCollisionSystemType(ch.ChCollisionSystem.Type_BULLET)
    s.SetGravitationalAcceleration(ch.ChVector3d(0.0, 0.0, -9.80665))
    s.SetNumThreads(1, 1, 1)
    t = veh.SCMTerrain(s, False)
    t.SetReferenceFrame(ch.ChCoordsysd(ch.ChVector3d(0.0, 0.0, Z_PLANE), ch.QUNIT))
    t.SetSoilParameters(2.0e6, 0.0, 1.1, 0.0, 30.0, 0.01, 2.0e8, 3.0e4)
    return s, t


def _box(s, t, z_above=0.06):
    ch = _ch()
    box = ch.ChBodyEasyBox(0.33, 0.33, 0.1, 2755.0, False, True, ch.ChContactMaterialSMC())
    box.SetPos(ch.ChVector3d(1.62, -0.93, Z_PLANE + z_above + 0.05))
    s.Add(box)
    t.AddActiveDomain(box, ch.ChVector3d(0, 0, -0.05), ch.ChVector3d(0.5, 0.5, 0.2))
    t.Initialize(8.0, 6.0, GRID)
    return box


# ------------------------------------------------------------------------------------------------ parsing
def test_parse_soil_event() -> None:
    a = run_S9.parse_soil_event("FL:RE1bF:mid@P3b_x_base")
    assert a["leg"] == "FL" and a["event_id"] == "RE1bF" and a["depth_m"] == pytest.approx(0.030)
    assert a["ramp_s"] == 0.05 and a["trigger"] == {"kind": "mid", "base_case": "P3b_x_base"}
    b = run_S9.parse_soil_event("RR:24:0.3:ready+5")
    assert b["event_id"] == "FS24" and b["trigger"] == {"kind": "ready", "delay_s": 5.0}
    assert run_S9.parse_soil_event("RR:11.5:20:t40")["trigger"] == {"kind": "t", "t_loop_s": 40.0}
    assert run_S9.parse_soil_event(None) is None
    for bad in ("XX:RE1bF:t1", "FL:RE1bF", "FL:0:1:t1", "FL:24:0.3:soon", "FL:BAD:t1", "FL:24:0.3:mid@"):
        with pytest.raises(ValueError):
            run_S9.parse_soil_event(bad)


def test_option_absent_leaves_no_attribute() -> None:
    base = ["level", "--soil", "J2", "--approved", "--case", "x", "--out-root", "x"]
    a = run_S9.build_parser().parse_args(base)
    assert not hasattr(a, "soil_event") and run_S9.parse_soil_event(getattr(a, "soil_event", None)) is None


def test_events_and_ramp_are_the_harness_copies() -> None:
    pytest.importorskip("numba")
    import s9_soil_event_screen as se

    assert run_S9.SOIL_EVENTS_MM_S == {k: (v["depth"] * 1e3, v["ramp"]) for k, v in se.EVENTS.items()}
    assert run_S9.SOIL_EVENT_ROW_COLUMNS == se.ROW_COLUMNS
    assert (run_S9.SOIL_EVENT_PRE_S, run_S9.SOIL_EVENT_MIN_AFTER_S, run_S9.SOIL_EVENT_MAX_AFTER_S,
            run_S9.SOIL_EVENT_READY_HOLD_S, run_S9.SOIL_EVENT_SLOW_TAIL_S) == (
        se.PRE_S, se.MIN_AFTER_S, se.MAX_AFTER_S, se.READY_HOLD_S, se.SLOW_WINDOW_TAIL_S)
    for tau in (-0.1, 0.0, 0.3, 0.77, 1.0, 1.4):
        assert run_S9.poly345(tau) == se.poly345(tau)


# ----------------------------------------------------------------------------------- A1 on a real SCMTerrain
def _node_state(t, points):
    ch = _ch()
    out = []
    for x, y in points:
        ni = t.GetNodeInfo(ch.ChVector3d(x, y, 0.0))
        out.append((ni.sinkage, ni.sinkage_plastic, ni.sigma_yield, ni.kshear))
    return out


def test_event_end_offset_is_minus_d_and_node_records_are_kept() -> None:
    """Spec 426.2 (가) on SCM: loaded nodes (box settled, then lifted clear) keep sinkage / plastic sinkage / yield
    stress / shear while the frame drops; at the ramp end the frame is z0 - d and the surface d lower."""
    ch = _ch()
    s, t = _system_terrain()
    box = _box(s, t, z_above=0.002)
    for _ in range(400):
        s.DoStepDynamics(5.0e-4)
    pts = [(1.62 + dx, -0.93 + dy) for dx in (-0.1, 0.0, 0.1) for dy in (-0.1, 0.0, 0.1)]
    assert all(st[0] > 1e-4 and st[2] > 0.0 for st in _node_state(t, pts))  # loaded, plastic history
    box.SetFixed(True)
    box.SetPos(ch.ChVector3d(1.62, -0.93, Z_PLANE + 0.5))
    for _ in range(4):
        s.DoStepDynamics(5.0e-4)
    before = _node_state(t, pts)
    h_before = [t.GetHeight(ch.ChVector3d(x, y, 0.0)) for x, y in pts]
    drv = run_S9.SoilEventDriver(t, (0.0, 0.0, Z_PLANE), np.eye(3), 0.030, 0.05)
    drv.set_event_time(s.GetChTime())
    for _ in range(200):
        drv.update(s.GetChTime())
        s.DoStepDynamics(5.0e-4)
    drv.update(s.GetChTime())
    assert drv.offset_m == 0.030 and drv.frame_z_m() == pytest.approx(Z_PLANE - 0.030, abs=1e-15)
    assert _node_state(t, pts) == before
    h_after = [t.GetHeight(ch.ChVector3d(x, y, 0.0)) for x, y in pts]
    assert np.allclose(np.subtract(h_before, h_after), 0.030, atol=1e-12)
    assert drv.meta()["n_frame_updates"] > 50


def _drop(driver_mode: str | None) -> np.ndarray:
    ch = _ch()
    s, t = _system_terrain()
    box = _box(s, t)
    drv = None
    if driver_mode is not None:
        drv = run_S9.SoilEventDriver(t, (0.0, 0.0, Z_PLANE), np.eye(3), 0.0 if driver_mode == "zero" else 0.03, 0.05)
        if driver_mode in ("late", "zero"):
            drv.set_event_time(1.0e3 if driver_mode == "late" else 0.05)
    out, f, m = [], ch.ChVector3d(), ch.ChVector3d()
    for _ in range(500):
        if drv is not None:
            drv.update(s.GetChTime())
        s.DoStepDynamics(5.0e-4)
        p = box.GetPos()
        t.GetContactForceBody(box, f, m)
        out.append([p.x, p.y, p.z, f.x, f.y, f.z, m.x, m.y, m.z])
    return np.array(out)


def test_no_event_is_bit_identical() -> None:
    """A driver without an event time, with one after the run, or with depth 0 makes no SCM call: the history is the
    run without the driver, bit for bit (the box lands within the run)."""
    ref = _drop(None)
    assert np.abs(ref[:, 5]).max() > 1000.0
    for mode in ("unset", "late", "zero"):
        assert np.array_equal(_drop(mode), ref), mode


# ------------------------------------------------------------------------------------------ timing / cut
def test_base_event_time(tmp_path) -> None:
    np.savez(tmp_path / run_S9.COMPLETION_SERIES_NAME, t_s=np.array([40.0, 40.1, 40.2, 40.3]),
             ok_loc=np.array([0.0, 1.0, 0.0, 1.0]))
    (tmp_path / "result.json").write_text(json.dumps({"t_loop_start_s": 8.0, "phases": [
        {"t_s": 30.0, "phase": "done"}, {"t_s": 41.0, "phase": "level"}, {"t_s": 52.1, "phase": "done"}]}), "utf-8")
    b = run_S9.base_event_time(tmp_path)
    assert (b["t_loc_s"], b["t_done_s"]) == (40.1, 52.1) and b["t_mid_s"] == pytest.approx(46.1)


def test_branch_cut_rule() -> None:
    ready = [(round(0.1 * k, 1), "level" if k < 50 else "ready") for k in range(-5, 700)]
    assert run_S9.soil_event_stop_s(ready, 0.3, 69.9) == (pytest.approx(12.0), "ready_held")
    late = [(round(0.1 * k, 1), "level" if k < 150 else "ready") for k in range(-5, 700)]
    assert run_S9.soil_event_stop_s(late, 0.3, 69.9) == (pytest.approx(18.0), "ready_held")
    assert run_S9.soil_event_stop_s(ready, 20.0, 69.9) == (pytest.approx(23.0), "ready_held")
    never = [(round(0.1 * k, 1), "level") for k in range(-5, 700)]
    assert run_S9.soil_event_stop_s(never, 0.3, 69.9) == (pytest.approx(60.0), "max_after")
    assert run_S9.soil_event_stop_s(never[:100], 0.3, 9.4) == (9.4, "run_end")


def _synthetic_case(d: Path, t_ev: float = 50.0) -> None:
    """A quiet Chrono-like run: every pad loaded 50 kN, READY from 45 s, crawler 60 mm clear, G4 event."""
    t = np.round(np.arange(t_ev - 0.5, t_ev + 20.0, 1e-3), 6)
    n = t.size
    rows = np.zeros((n, len(run_S9.SOIL_EVENT_ROW_COLUMNS)))
    rows[:, 0] = t
    rows[:, 1:5] = 50.6e3
    rows[:, 5:9] = 50.0e3
    rows[:, 17:19] = [0.01, -0.02]
    np.savez(d / run_S9.SOIL_EVENT_SERIES_NAME, rows=rows, columns=np.array(run_S9.SOIL_EVENT_ROW_COLUMNS), t_s=t,
             offset_m=np.zeros(n), sink_true_m=np.full((n, 4), 0.1), s_ref_m=np.full((n, 4), 0.5),
             s_ref_max_m=np.full(4, 0.52), s_ref_max_before_m=np.full(4, 0.52))
    s9_rows = [{"t_s": round(t_ev - 0.5 + 0.1 * k, 3), "c2_phase": "ready", "crawler_gap_min_m": 0.06}
               for k in range(int(20.5 / 0.1))]
    res = {"t_loop_start_s": 8.0, "args": {"fs_kN": 0.0}, "s9_rows": s9_rows, "events": [],
           "c2_soil": {"soil_mode_t_s": 30.0},
           "soil_event": {"spec": run_S9.parse_soil_event("RR:G4:t42"),
                          "driver": {"t_ev_s": t_ev}, "head_area_m2": [0.01327, 0.01327, 0.0095, 0.0095]}}
    (d / "result.json").write_text(json.dumps(res), "utf-8")


def test_judge_adapter_runs_the_harness_judge(tmp_path) -> None:
    """The adapter builds the harness BranchResult (cut at READY held 3 s, >= 12 s) and returns E-1 .. E-7; the
    quiet synthetic run passes every gate."""
    pytest.importorskip("numba")
    _synthetic_case(tmp_path)
    out = run_S9.judge_chrono_soil_event(tmp_path)
    assert out["stop_reason"] == "ready_held" and out["stop_rel_s"] == pytest.approx(12.0)
    assert out["fast"] is False and set(out["gates"]) >= {"E-1_no_lift", "E-3_Fmin_after_event", "E-4_window_350bar",
                                                           "E-5_end_ready_att", "E-6_crawler", "E-7_recurrence"}
    assert out["pass"] is True, {k: v for k, v in out["gates"].items() if not v}
    assert out["crawler"]["clear_end_mm"] == pytest.approx(60.0)


# ------------------------------------------------------------------------------------------------- RV5 rows
def _batches():
    import s9_batch

    return s9_batch, s9_batch.batches()


def test_rv5_rows() -> None:
    s9_batch, b = _batches()
    rows = b["RV5"]
    assert [r["case"] for r in rows] == RV5_NAMES
    by = {r["case"]: r for r in rows}
    for base, ev, leg, fs, eid in ((BASES[0], EVENTS[0], "FL", "0", "RE1bF"), (BASES[1], EVENTS[1], "RR", "8", "FS24")):
        a = by[base]["argv"]
        assert a[a.index("--soil-patch") + 1] == f"{leg}:J2" and a[a.index("--fs-kN") + 1] == fs
        assert "--soil-event" not in a and "depends_on" not in by[base]
        assert by[ev]["argv"] == a[:-1] + ["--soil-event", f"{leg}:{eid}:mid@{base}", a[-1]]
        assert by[ev]["depends_on"] == base
        p = run_S9.build_parser().parse_args(by[ev]["argv"][len(s9_batch.RUN):] + ["--case", ev, "--out-root", "x"])
        assert (p.soil, p.pad_variant, p.duration, p.soil_patch_grid) == ("J2", "dwg_rear250", 120.0, 0.01)
        assert run_S9.parse_soil_event(p.soil_event)["trigger"]["base_case"] == base
    assert all(r["est_s"] == 6900.0 for r in rows)
    assert not set(RV5_NAMES) & {r["case"] for r in run_S9.case_plan()}


def test_depends_on_scheduling() -> None:
    """--parallel 2: both bases first (the events wait); an event becomes runnable when its base ended rc 0; rows
    without dependencies keep the queue order; a dependency outside the run is refused."""
    s9_batch, b = _batches()
    q = s9_batch.schedule_cases(b["RV5"], parallel_e=0)["pcore"]
    q = list(q)
    started = [q.pop(s9_batch.next_runnable(q, set())), q.pop(s9_batch.next_runnable(q, set()))]
    assert [c["case"] for c in started] == BASES and s9_batch.next_runnable(q, set()) is None
    assert q[s9_batch.next_runnable(q, {BASES[1]})]["case"] == EVENTS[1]
    assert s9_batch.next_runnable([{"case": "a"}, {"case": "b"}], set()) == 0
    with pytest.raises(ValueError, match="depend"):
        s9_batch.schedule_cases([r for r in b["RV5"] if r["case"] == EVENTS[0]])
