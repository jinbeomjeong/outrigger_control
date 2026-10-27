"""C-S8-76 (``s6_control_spec.md`` rev. 69 360 / 363): non-planar start G8 on L1-R.

* ``run_S6C.py``: sets ``g8c76`` (C1 / C2, run now) and ``g8c76_p28`` (C3 / C4, P-S8-28
  acceptance, refused without ``--allow-p28-cases``), field ``BundleCCase.pad_block``, floor
  ``edge``; every earlier S6C / stage-2 / S8C case and set definition keeps its hash
  (aggregates computed at master 7862ef6 + the rev. 69 working tree, before the change).
* ``verify.s6_control``: :func:`g8_metrics` / :func:`g8_rows` (360.2 gates, state-based FAULT
  including the unnamed stroke-end FAULT, crawler clearance of every sphere)."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

BEFORE = {
    # sha256 of json.dumps({case id: sha256(json.dumps(meta, sort_keys, default=str))},
    # sort_keys) before C-S8-76 (scratch def_hashes.py, 2026-10-27)
    "s6": (76, "30e3b66728edc160fe348ebd15bbebcd47f017791dcaa23eac6ee2e3621ae665"),
    "s6_repr": (76, "eeac83416de3bb4a44a1be1d6887ae7224f63e6f1e2f408f92b813ec5acaf3e0"),
    "s6_sets": (6, "bb18ae01dd655837f9df3bdd3238f3e667c81df9bd77eaefa66a7d4e08882f00"),
    "stage2": (68, "6031cc03b858f3404cb3b9d9856c3c8f3af37c6ce9a99ff14e97a751e1858216"),
    "s8": (134, "6b42e46d073954345766e76d559e8ed329f4c85f6bdd1e949cb9a8e7af3bcba5"),
    "s8_sets": (15, "36b54a1d44be81959bb33385c8e7936cf53f421562df695abe6aedc3e975162e"),
}
FLOORS_BEFORE = {
    "flat": (0.0, 0.0), "rp05": (2.7699, 1.7813), "rpB": (2.7355, 1.7592),
    "fdown3.2": (0.0, 3.2), "roll4.4": (4.4, 0.0),
}
NEW_SETS = ("g8c76", "g8c76_p28", "g8c76_p28acc")
RUN_IDS = ["G8C1_top_edge_FL_g200", "G8C1_top_edge_FL_g170", "G8C2_top_flat_FL_g55",
           "G8C2_top_flat_RR_g200"]
P28_IDS = ["G8C3_top_edge_RL_g230", "G8C3_top_edge_FL_g20", "G8C4_top_edge_RR_g230"]


@pytest.fixture(scope="module")
def s8c():
    import run_S8C

    return run_S8C


def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _agg(d: dict) -> tuple[int, str]:
    return len(d), hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


def test_earlier_definitions_unchanged(s8c) -> None:
    s6c, st = s8c.s6c, s8c.s6c.st
    doc = {k: {} for k in BEFORE}
    for name, fn in s6c.CASE_SETS.items():
        if name in NEW_SETS:
            continue
        cases = fn()
        doc["s6_sets"][name] = [c.case_id for c in cases]
        for c in cases:
            doc["s6"][c.case_id] = _h(c.to_meta())
            doc["s6_repr"][c.case_id] = _h(repr(c))
    doc["stage2"] = {c.case_id: _h(asdict(c)) for c in st.all_cases()}
    doc["s8"] = {c.case_id: _h(c.to_meta()) for c in s8c.s8_cases()}
    doc["s8_sets"] = {n: [c.case_id for c in s8c.case_set(n)] for n in s8c.SET_NAMES}
    for key, want in BEFORE.items():
        assert _agg(doc[key]) == want, key
    for name, rp in FLOORS_BEFORE.items():
        assert tuple(st.FLOORS[name]) == rp
    assert tuple(st.FLOORS["edge"]) == (2.2, 1.6)
    assert ("top", "edge") not in s6c.NEW_SNAPSHOTS and s6c.G8_SNAPSHOTS == (("top", "edge"),)


def test_g8c76_sets_match_spec_363(s8c) -> None:
    s6c = s8c.s6c
    run = s6c.CASE_SETS["g8c76"]()
    p28 = s6c.CASE_SETS["g8c76_p28"]()
    assert [c.case_id for c in run] == RUN_IDS
    assert [c.case_id for c in p28] == P28_IDS
    want = {  # (row, floor, leg, g_start m)
        "G8C1_top_edge_FL_g200": ("C1", "edge", "FL", 0.200),
        "G8C1_top_edge_FL_g170": ("C1", "edge", "FL", 0.170),
        "G8C2_top_flat_FL_g55": ("C2", "flat", "FL", 0.055),
        "G8C2_top_flat_RR_g200": ("C2", "flat", "RR", 0.200),
        "G8C3_top_edge_RL_g230": ("C3", "edge", "RL", 0.230),
        "G8C3_top_edge_FL_g20": ("C3", "edge", "FL", 0.020),
        "G8C4_top_edge_RR_g230": ("C4", "edge", "RR", 0.230),
    }
    table = s6c.case_table()
    for c in [*run, *p28]:
        row, floor, leg, g = want[c.case_id]
        assert table[c.case_id] == c
        assert c.config == f"G8-{row}" and c.pad_block == (leg, pytest.approx(g))
        assert c.scenario.floor == floor and c.scenario.level == "top"
        assert c.scenario.group == "G8" and c.scenario.event is None
        assert c.end_after_ready_s == 5.0 and not c.sensor_model and c.preground_leg is None
        assert c.conditional is (c in p28)
        assert c.snapshot == f"S6_crawler_top_{floor}"
        meta = c.to_meta()
        assert meta["pad_block"][0] == leg and "preground_leg" not in meta
        assert "pad_block" not in repr(c)
    # harness h of the C1 rows = spec 363 bump heights 139 / 169 mm
    h = {r[0]: r[5] for r in s6c.G8C76_CASES}
    assert round(h["G8C1_top_edge_FL_g200"]) == 139 and round(h["G8C1_top_edge_FL_g170"]) == 169
    assert round(h["G8C3_top_edge_RL_g230"]) == 119 and round(h["G8C3_top_edge_FL_g20"]) == 319
    assert round(h["G8C4_top_edge_RR_g230"]) == 118


def test_p28_acceptance_set_rev70(s8c) -> None:
    """Spec rev. 70 366: ``g8c76_p28acc`` = C3 / C4 + the C1 FL g170 re-run (same definition);
    the rev. 69 sets keep their case lists and definitions."""
    s6c = s8c.s6c
    acc = s6c.CASE_SETS["g8c76_p28acc"]()
    assert [c.case_id for c in acc] == [*P28_IDS, "G8C1_top_edge_FL_g170"]
    run = {c.case_id: c for c in s6c.CASE_SETS["g8c76"]()}
    assert acc[-1] == run["G8C1_top_edge_FL_g170"] and not acc[-1].conditional
    assert [c.case_id for c in s6c.CASE_SETS["g8c76_p28"]()] == P28_IDS
    s6c.case_table()  # one definition per id


@pytest.mark.parametrize("st_, stop", [
    ({}, False),
    ({"fault_t": 10.0, "last_t": 19.9}, False),
    ({"fault_t": 10.0, "last_t": 20.0}, True),                       # FAULT + 10 s, no re-ground
    ({"fault_t": 10.0, "rg_start_t": 11.0, "last_t": 20.0}, False),  # re-ground still running
    ({"fault_t": 10.0, "rg_start_t": 11.0, "rg_end_t": 18.0, "last_t": 22.9}, False),
    ({"fault_t": 10.0, "rg_start_t": 11.0, "rg_end_t": 18.0, "last_t": 23.0}, True),  # end + 5
    ({"fault_t": 10.0, "rg_start_t": 11.0, "rg_end_t": 13.0, "last_t": 20.0}, True),  # + 10 rules
    ({"fault_t": 10.0, "rg_start_t": 11.0, "last_t": 35.0}, True),   # cap FAULT + 25 s
])
def test_g8_fault_end_rule(s8c, st_, stop) -> None:
    assert s8c.s6c.g8_fault_stop(dict(st_)) is stop


def test_run_refuses_p28_cases_without_flag(s8c, monkeypatch) -> None:
    s6c = s8c.s6c
    monkeypatch.delenv("OUTRIGGER_L1_FALLBACK_RATIO_SOURCE", raising=False)
    called = []
    monkeypatch.setattr(s6c, "run_batch", lambda *a, **k: called.append((a, k)))
    with pytest.raises(SystemExit, match="allow-p28-cases"):
        s6c.main(["run", "--set", "g8c76_p28", "--approved"])
    with pytest.raises(SystemExit, match="allow-p28-cases"):
        s6c.main(["run", "--set", "g8c76", "--approved", "--only", "G8C4_top_edge_RR_g230"])
    with pytest.raises(SystemExit, match="approval"):
        s6c.main(["run", "--set", "g8c76"])
    assert not called
    s6c.main(["run", "--set", "g8c76", "--approved", "--jobs", "4", "--tag", "c76"])
    assert called[-1][0][0] == RUN_IDS
    s6c.main(["run", "--set", "g8c76_p28", "--approved", "--allow-p28-cases"])
    assert called[-1][0][0] == P28_IDS
    with pytest.raises(SystemExit, match="allow-p28-cases"):
        s6c.main(["run", "--set", "g8c76_p28acc", "--approved"])
    s6c.main(["run", "--set", "g8c76_p28acc", "--approved", "--allow-p28-cases"])
    assert called[-1][0][0] == [*P28_IDS, "G8C1_top_edge_FL_g170"]


# --- judge -----------------------------------------------------------------------------------


def _case(tmp_path: Path, *, phases, fault_events=(), stroke_end_mm=600.0, gap_end_m=0.15,
          lift_leg=None, end_att_deg=0.05, stroke_peak_mm=None, events=()):
    """Synthetic C-S8-76 case: 1 ms record of 20 s, crawler lift-off at 10 s."""
    from outrigger_sim.frames import quat_from_euler_zyx

    t0 = 100.0
    t = t0 + np.arange(0, 20.0, 1e-3)
    n = t.size
    fz = np.where(t - t0 < 10.0, 3.0e5, 0.0)
    q = np.array(quat_from_euler_zyx(0.0, np.radians(end_att_deg), 0.0))
    rec = {"t": t, "F_crawler": np.column_stack([np.zeros(n), np.zeros(n), fz]),
           "body_quat_wxyz": np.tile(q, (n, 1))}
    N = np.full((n, 4), 9.0e4)
    if lift_leg is not None:
        N[(t - t0 > 15.0) & (t - t0 < 15.2), lift_leg] = 0.0
    s = np.tile(np.linspace(0.0, stroke_end_mm * 1e-3, n)[:, None], (1, 4))
    if stroke_peak_mm is not None:  # transient peak of FR, back to the end value later
        s[n // 2, 1] = stroke_peak_mm * 1e-3
    pads = {"t": t, "N": N, "F_cyl": N + 2e4, "F_cyl_min_interval": N + 2e4, "s_motor": s}
    d = tmp_path / "case"
    d.mkdir()
    g8 = {"leg": "FL", "g_start_target_m": 0.2, "g_start_measured_m": 0.2, "g0_m": [0.34] * 4,
          "h_m": 0.14, "fault_event_names": list(fault_events),
          "crawler_gap_end_m": {"min": gap_end_m}, "clearance_target_m": 0.05,
          "controller_clearance_estimate_end_m": {"min": 0.05}, "fs_kN_plant": 0.0}
    res = {"case": "G8X", "settings": {"start_t_s": t0, "level": "top"}, "phases": phases,
           "g8": g8}
    ev = [f"C2Event(t_s={t0 + a!r}, name='{nm}')" for a, nm in events]
    return {"dir": d, "result": res, "rec": rec, "pads": pads, "events": ev, "probes": []}


class _P:
    class control:  # noqa: N801
        F_min_cylinder_N = 9414.59


def _rows_by(rows, word):
    return [r for r in rows if word in r["item"]]


def test_g8_rows_pass_case(tmp_path) -> None:
    from outrigger_sim.verify.s6_control import g8_metrics, g8_rows

    case = _case(tmp_path, phases=[[0.1, "check"], [5.0, "touch"], [9.0, "level"],
                                   [14.0, "ready"]])
    m = g8_metrics(case, _P())
    assert m["times_s"]["liftoff"] == pytest.approx(10.0)
    rows = g8_rows({"G8X": m})
    judged = [r for r in rows if r["kind"] == "judged"]
    assert len(judged) == 7 and all(r["passed"] is True for r in judged), judged
    assert m["fault"]["state_detected"] is False


def test_g8_rows_unnamed_stroke_end_fault(tmp_path) -> None:
    """``c2._update_stroke_end_fault`` leaves no event: the phase alone fails the row."""
    from outrigger_sim.verify.s6_control import g8_metrics, g8_rows

    case = _case(tmp_path, phases=[[0.1, "check"], [5.0, "touch"], [9.0, "level"],
                                   [16.0, "fault"]],
                 stroke_end_mm=693.9, gap_end_m=0.21, lift_leg=2, end_att_deg=0.5)
    m = g8_metrics(case, _P())
    assert m["fault"] == {"state_detected": True, "first_t_s": 16.0, "phases": ["fault"],
                          "event_names": [], "unnamed": True}
    rows = g8_rows({"G8X": m})
    assert _rows_by(rows, "FAULT 0")[0]["passed"] is False
    assert _rows_by(rows, "READY reached")[0]["passed"] is False
    assert _rows_by(rows, "maximum motor stroke")[0]["passed"] is False
    assert _rows_by(rows, "no pad lift")[0]["passed"] is False
    assert _rows_by(rows, "last 1 s")[0]["passed"] is False
    assert _rows_by(rows, "crawler clear")[0]["passed"] is True


def test_g8_stroke_gate_on_run_max_rev70(tmp_path) -> None:
    """Spec rev. 70 366: the gate reads the run maximum; the run-end value is a record."""
    from outrigger_sim.verify.s6_control import g8_metrics, g8_rows

    case = _case(tmp_path, phases=[[0.1, "check"], [14.0, "ready"]], stroke_peak_mm=687.98)
    m = g8_metrics(case, _P())
    assert max(m["stroke_end_mm"]) == pytest.approx(600.0)
    assert m["stroke_max_mm"][1] == pytest.approx(687.98)
    r = _rows_by(g8_rows({"G8X": m}), "maximum motor stroke")[0]
    assert r["passed"] is False and r["value"] == m["stroke_max_mm"]


def test_g8_p28_event_counts(tmp_path) -> None:
    from outrigger_sim.verify.s6_control import G8_P28_EVENTS, g8_metrics, g8_rows

    evs = [(30.0, "INFO_LOC_CLEARANCE_ANCHOR"), (40.0, "WARN_LIFT_STROKE_LIMITED:FR"),
           (41.0, "FAULT_STROKE_END:FR"), (41.1, "fault_reground_start:RL"),
           (45.0, "fault_reground_contact:RL"), (46.0, "fault_reground_end:RL"),
           (46.0, "fault_reground_end_extra"), (47.0, "INFO_PRESSURE_ZERO_CALIBRATED:FL")]
    case = _case(tmp_path, phases=[[0.1, "check"], [41.0, "fault_reground"], [46.0, "fault"]],
                 events=evs)
    m = g8_metrics(case, _P())
    assert m["p28_events"] == {**dict.fromkeys(G8_P28_EVENTS, 0),
                               "INFO_LOC_CLEARANCE_ANCHOR": 1, "WARN_LIFT_STROKE_LIMITED": 1,
                               "FAULT_STROKE_END": 1, "fault_reground_start": 1,
                               "fault_reground_contact": 1, "fault_reground_end": 1}
    rec = _rows_by(g8_rows({"G8X": m}), "event counts")[0]
    assert rec["kind"] == "record" and rec["passed"] is None
    assert _rows_by(g8_rows({"G8X": m}), "FAULT 0")[0]["passed"] is False


def test_g8_rows_crawler_not_clear(tmp_path) -> None:
    from outrigger_sim.verify.s6_control import g8_metrics, g8_rows

    case = _case(tmp_path, phases=[[0.1, "check"], [14.0, "ready"]], gap_end_m=-0.001)
    rows = g8_rows({"G8X": g8_metrics(case, _P())})
    assert _rows_by(rows, "crawler clear")[0]["passed"] is False
