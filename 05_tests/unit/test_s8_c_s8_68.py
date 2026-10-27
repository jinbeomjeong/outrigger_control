"""C-S8-68 (``s6_control_spec.md`` rev. 64 323 / 327.2, U-S8-68 G4 = (가)): head-sensor fault
cases and the G4 judge rows.

``run_S8C.py`` gets the head-fault injection (``head_fault`` event-spec key, the layout of
``rod_fault``; :class:`run_S8C.HeadFaultInjection`), the four ``G4H_*`` events, the six cases of
323.8 and the set ``mlj_c68``. The 99 + 2 existing cases must keep their definition hashes
(``06_analysis/02_control/s9/v5/cad_c67/hash_after.json``: SHA-256 of the canonical
``to_meta()`` JSON and of ``repr(case)``, the end rule) and every existing set its members and
order. ``verify.s8_control`` gets the FAULT entry rule (FAULT_REGROUND or FAULT), the
``head_sensor_reground`` cause and the rows G4-1 ... G4-8 (323.7), tested here on synthetic
records (P-S8-24 is not in the controller yet).

C-S8-70 (spec rev. 65 333 / 335.2): G4-3 / G4-7 zero output from + d T_s (d = 1), G4-4 record
columns, G4-7 on no-target runs only, F2 without the head-fault leg from the arm time, the
delivered head reading file, the abort / step-suspend counts in G4-8, the branch-restore soil
rule path, and the six C-S8-68 case hashes."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))
sys.path.insert(0, str(ROOT / "03_src"))

from outrigger_sim.verify import s8_control as s8  # noqa: E402

HASHES = ROOT / "06_analysis" / "02_control" / "s9" / "v5" / "cad_c67" / "hash_after.json"
C68 = ["MLJ_G4H_FS24_FR_Fs0", "MLJ_G4H_FS24_FR_Fs8", "MLJ_G4H_FS24_RL_Fs0",
       "MLJ_G4H_FS24_RL_Fs8", "MLJ_G4H_quiet_FR_Fs0", "MLJ_G4H_G4_RR_Fs4"]


@pytest.fixture(scope="module")
def run_s8c():
    import run_S8C

    return run_S8C


def _meta_sha(run_s8c, case) -> str:
    text = json.dumps(run_s8c.s6c._plain(case.to_meta()), sort_keys=True, default=repr)
    return hashlib.sha256(text.encode()).hexdigest()


# --- runner: case definitions ------------------------------------------------------------------


def test_existing_101_case_hashes_and_sets_unchanged(run_s8c) -> None:
    doc = json.loads(HASHES.read_text(encoding="utf-8"))
    assert len(doc["cases"]) == 101
    tab = run_s8c.case_table()
    for cid, ref in doc["cases"].items():
        c = tab[cid]
        assert _meta_sha(run_s8c, c) == ref["meta"], cid
        assert hashlib.sha256(repr(c).encode()).hexdigest() == ref["repr"], cid
        assert run_s8c.end_rule(c) == ref["end_rule"], cid
    for name, ids in doc["sets"].items():
        assert [c.case_id for c in run_s8c.case_set(name)] == ids, name
    # the new cases come after the existing ones (old order kept), before the smoke pair
    # C-S8-72 (spec rev. 67 345) appends group G1 after these (test_c_s8_72.py checks it)
    order = [c.case_id for c in run_s8c.s8_cases() if c.group != "G1"]
    assert [c for c in order if c not in C68] == \
        [c for c in order if c in doc["cases"]]
    assert set(order) == set(doc["cases"]) | set(C68)


def test_mlj_c68_set(run_s8c) -> None:
    assert "mlj_c68" in run_s8c.SET_NAMES
    c68 = run_s8c.case_set("mlj_c68")
    assert [c.case_id for c in c68] == C68
    assert len(run_s8c.case_set("mlj")) == 6
    assert not set(C68) & {c.case_id for c in run_s8c.case_set("mlj")}
    for c in c68:
        assert (c.group, c.priority, c.engine) == ("MLJ", 5, "L2b_NSC")
        assert c.event in run_s8c.G4H_EVENT_NAMES
    fs = {c.case_id: c.fs_kN for c in c68}
    assert fs == {"MLJ_G4H_FS24_FR_Fs0": 0.0, "MLJ_G4H_FS24_FR_Fs8": 8.0,
                  "MLJ_G4H_FS24_RL_Fs0": 0.0, "MLJ_G4H_FS24_RL_Fs8": 8.0,
                  "MLJ_G4H_quiet_FR_Fs0": 0.0, "MLJ_G4H_G4_RR_Fs4": 4.0}


def test_head_fault_specs(run_s8c) -> None:
    ev = run_s8c.EVENTS
    exp = {"G4H_FS24_FR": ("FR", 0.465, "reground", "FS24"),
           "G4H_FS24_RL": ("RL", 0.465, "reground", "FS24"),
           "G4H_G4_RR": ("RR", 2.05, "record", "G4")}
    for name, (leg, after, expect, base) in exp.items():
        e = ev[name]
        assert e["head_fault"] == {"leg": leg, "fault": "offset", "value_Pa": 150e5,
                                   "after_event_s": after, "expect": expect}
        # the floor event is exactly the base event's
        assert {k: v for k, v in e.items() if k not in ("head_fault", "end_after_s")} == ev[base]
        assert e["end_after_s"] == 20.0
    q = ev["G4H_quiet_FR"]
    assert q["kind"] == "fault" and q["at"] == "ready+5" and not q["fine"]
    assert q["head_fault"]["leg"] == "FR" and q["head_fault"]["expect"] == "negative"
    assert q["head_fault"]["after_event_s"] == 0.05
    assert "rod_fault" not in q
    # 323.8: the FS24 fault falls inside the first RL lift of the original MLJ records
    assert 0.205 < run_s8c.G4H_FS24_FAULT_AFTER_EVENT_S < 0.721
    # the injection is detected as a sensor-fault run by the judge (C-S8-26 ②)
    assert s8.sensor_fault_injected({"s8": {"event_spec": ev["G4H_G4_RR"]}})


def test_new_case_scenarios_and_end_rule(run_s8c) -> None:
    tab = run_s8c.case_table()

    def sc(cid):
        m = run_s8c.s6c._plain(tab[cid].to_meta())["base"]
        m.pop("case_id", None)
        m["scenario"].pop("case_id", None)
        return m

    assert sc("MLJ_G4H_FS24_FR_Fs0") == sc("MLJ_FS24_Fs0")
    assert sc("MLJ_G4H_FS24_RL_Fs8") == sc("MLJ_FS24_Fs8")
    assert sc("MLJ_G4H_G4_RR_Fs4") == sc("E_G4_Fs4")
    assert sc("MLJ_G4H_quiet_FR_Fs0") == sc("K0V_top_flat_Fs0")
    for cid in C68:
        r = run_s8c.end_rule(tab[cid])
        assert (r["anchor"], r["after_s"]) == ("event", 20.0)
        assert tab[cid].wall_estimate_s("p") > 0.0


# --- runner: injection wrapper -------------------------------------------------------------------


@dataclass(frozen=True)
class _Meas:
    t_s: float
    head_pressure_Pa: np.ndarray
    rod_pressure_Pa: np.ndarray | None = None


class _Inner:
    period_s = 0.1

    def __init__(self) -> None:
        self.seen: list[_Meas] = []

    def update(self, m):
        self.seen.append(m)
        return "cmd"

    def reset(self) -> None:
        pass


@pytest.mark.parametrize("fault,expect_fr", [("offset", 100e5 + 150e5), ("stuck", 150e5),
                                             ("dropout", math.nan)])
def test_head_fault_injection(run_s8c, fault, expect_fr) -> None:
    inner = _Inner()
    w = run_s8c.HeadFaultInjection(inner, leg=1, fault=fault, value_Pa=150e5)
    head = np.array([90e5, 100e5, 110e5, 120e5])
    assert w.update(_Meas(1.0, head)) == "cmd"  # not armed: unchanged
    w.arm(2.05)
    w.update(_Meas(2.0, head))
    w.update(_Meas(2.1, head))
    assert inner.seen[0].head_pressure_Pa is head and inner.seen[1].head_pressure_Pa is head
    got = inner.seen[2].head_pressure_Pa
    np.testing.assert_array_equal(got[[0, 2, 3]], head[[0, 2, 3]])
    assert (math.isnan(got[1]) if math.isnan(expect_fr) else got[1] == expect_fr)
    np.testing.assert_array_equal(head, [90e5, 100e5, 110e5, 120e5])  # input not mutated
    meta = w.meta()
    assert meta["leg"] == "FR" and meta["first_applied_t_s"] == 2.1
    assert meta["applied_periods"] == 1 and w.period_s == 0.1


def test_require_fault_reground(run_s8c, monkeypatch) -> None:
    cases = run_s8c.case_set("mlj_c68")
    monkeypatch.setattr(run_s8c, "fault_reground_available", lambda: False)
    with pytest.raises(SystemExit, match="P-S8-24"):
        run_s8c.require_fault_reground(cases)
    run_s8c.require_fault_reground(run_s8c.case_set("mlj"))  # no head fault: no check
    monkeypatch.setattr(run_s8c, "fault_reground_available", lambda: True)
    run_s8c.require_fault_reground(cases)


# --- judge -------------------------------------------------------------------------------------

F_MIN = 9415.0


def _synthetic(*, reground: bool, lifted_leg: str | None, fault_leg: str = "FR",
               rl_after_kN: float = 60.0):
    """10 Hz / 1 ms records of a run with the head fault at t_f = 10.0 s."""
    tc = np.round(np.arange(0.0, 20.0 + 1e-9, 0.1), 10)
    tp = np.round(np.arange(0.0, 20.0 + 1e-9, 0.001), 10)
    t_f = 10.0
    t_fault = 14.0 if reground else t_f
    phases = [[0.0, "level"], [5.0, "ready"]]
    phases += [[t_f, "fault_reground"], [t_fault, "fault"]] if reground else [[t_f, "fault"]]
    ph = np.where(tc < 5.0 - 1e-9, "level", "ready").astype("U16")
    ph[tc >= t_f - 1e-9] = "fault_reground" if reground else "fault"
    ph[tc >= t_fault - 1e-9] = "fault"
    u = np.zeros((tc.size, 4))
    u[tc < 5.0 - 1e-9] = 1e-3
    air = np.zeros((tp.size, 4), bool)
    f = np.full((tp.size, 4), 80e3)
    if lifted_leg is not None:
        k = s8.LEGS.index(lifted_leg)
        air[(tp >= 9.7) & (tp < 10.6), k] = True
        f[(tp >= 9.7) & (tp < 12.0), k] = 0.0
        f[tp >= 12.0, k] = rl_after_kN * 1e3
        if reground:
            u[(tc >= t_f - 1e-9) & (tc < 12.0 - 1e-9), k] = 0.25 * 0.020924
    names = [(t_f, f"FAULT_HEAD_PRESSURE:{fault_leg}"),
             (t_f, f"INFO_HEAD_PRESSURE_FAULT_REASON:{fault_leg}:D1_step")]
    if reground:
        names += [(t_f, f"fault_reground_start:{lifted_leg}"),
                  (12.0, f"fault_reground_contact:{lifted_leg}"),
                  (t_fault, "fault_reground_end:1/1")]
    s_motor = np.full((tp.size, 4), 0.30)
    if lifted_leg is not None and reground:
        k = s8.LEGS.index(lifted_leg)
        s_motor[:, k] += np.clip(tp - t_f, 0.0, 2.0) * 0.25 * 0.020924
    rp = np.zeros((tp.size, 2))
    return dict(t_f=t_f, fault_leg=fault_leg, phases=phases, names=names, tc=tc,
                phase_series=ph, issued_u=u, tp=tp, airborne=air, judged_force_N=f,
                f_cyl_N=f.copy(), head_true_Pa=np.full((tp.size, 4), 200e5), roll_pitch_rad=rp,
                s_motor_m=s_motor, f_min_N=F_MIN, extend_limit_N=EXTEND_LIMIT_N,
                t_event_s=5.0)


EXTEND_LIMIT_N = (278737.808, 278737.808, 199569.673, 199569.673)


def test_g4_positive_run_passes() -> None:
    g = s8.g4_metrics(expect="reground", **_synthetic(reground=True, lifted_leg="RL"))
    assert g["entry_s"] == 10.0 and g["fault_s"] == 14.0
    for k in ("g4_1", "g4_2", "g4_3", "g4_4", "g4_5", "g4_6"):
        assert g[k]["passed"] is True, (k, g[k])
    assert g["g4_2"]["targets"] == ["RL"] and g["g4_2"]["missed"] == []
    assert g["g4_7"]["passed"] is None and g["g4_7"]["same_as_direct_fault"] is False
    assert g["g4_5"]["healthy_legs"] == ["FL", "RR"]  # RL target, FR = fault leg
    assert g["g4_5"]["faulty_extend_limit_kN"] == pytest.approx(278.737808)
    assert g["g4_5"]["faulty_rise_vs_entry_kN"] == pytest.approx(0.0)
    assert g["g4_5"]["faulty_rise_vs_pre_event_median_kN"] == pytest.approx(0.0)
    assert g["g4_2"]["late_airborne"] == [] and g["g4_4"]["status"] == "judged"
    assert g["g4_8"]["within_limits"] is True
    assert g["g4_8"]["travel_mm"]["RL"] == pytest.approx(2.0 * 0.25 * 20.924, abs=0.1)
    rows = s8.g4_rows("X", g)
    assert [r["item"].split()[1] for r in rows] == [f"G4-{i}" for i in range(1, 9)] + ["G4-E"]
    assert [r["passed"] for r in rows] == [True] * 6 + [None, None, None]
    assert {r["kind"] for r in rows[6:]} == {"record"}


def test_g4_8_limits_from_the_controller_meta() -> None:
    """P-S8-24 meta layout (``controller_meta.fault_reground``: settings + run.targets)."""
    meta = {"settings": {"max_travel_m": 0.03, "max_leg_duration_s": 1.0,
                         "max_total_duration_s": 15.0},
            "run": {"targets": [{"leg": "RL", "sensor": "healthy", "cues": ["lower"],
                                 "gap_m": 0.0005, "max_travel_m": 0.0055, "travel_m": 0.010,
                                 "duration_s": 2.0, "outcome": "contact"}],
                    "end_reason": "done"}}
    g = s8.g4_metrics(expect="reground", reground_meta=meta,
                      **_synthetic(reground=True, lifted_leg="RL"))
    g8 = g["g4_8"]
    assert g8["max_travel_mm"]["RL"] == pytest.approx(5.5)
    assert g8["max_travel_source"] == {"FL": "settings", "FR": "settings",
                                       "RL": "run.targets", "RR": "settings"}
    assert g8["leg_time_limit_s"] == 1.0 and g8["within_limits"] is False  # 10.5 mm, 2 s
    assert g8["controller_targets"]["RL"]["outcome"] == "contact"
    assert g["controller_end_reason"] == "done"


def test_g4_missed_target_and_low_end_force_fail() -> None:
    d = _synthetic(reground=True, lifted_leg="RL", rl_after_kN=5.0)
    d["names"] = [n for n in d["names"] if not n[1].startswith("fault_reground_start")]
    d["names"].append((10.0, "fault_reground_start:FL"))
    g = s8.g4_metrics(expect="reground", **d)
    assert g["g4_2"]["passed"] is False and g["g4_2"]["missed"] == ["RL"]
    assert g["g4_2"]["false_targets"] == ["FL"]
    assert g["g4_4"]["passed"] is False
    assert g["g4_4"]["min_from_fault_plus_1s_kN"]["RL"] == pytest.approx(5.0)


def test_g4_negative_case() -> None:
    g = s8.g4_metrics(expect="negative", **_synthetic(reground=False, lifted_leg=None))
    assert g["g4_7"]["passed"] is True and g["g4_7"]["phase_at_t_f"] == "fault"
    assert g["g4_7"]["no_target_source"].startswith("no meta")
    assert g["g4_1"]["passed"] is True and g["g4_2"]["passed"] is True
    assert g["g4_2"]["truth_airborne"] == [] and g["g4_2"]["targets"] == []
    assert g["g4_3"]["passed"] is True and g["g4_4"]["passed"] is True
    assert g["g4_5"]["passed"] is None and g["g4_8"]["passed"] is None
    # C-S8-70 ③: a targeted run is a G4-7 record (rev. 64: judged on the "negative" expectation)
    g2 = s8.g4_metrics(expect="negative", **_synthetic(reground=True, lifted_leg="RL"))
    assert g2["g4_7"]["passed"] is None and g2["g4_7"]["same_as_direct_fault"] is False
    # ... and judged when the controller says no_target (here a contradicting record: fails)
    g3 = s8.g4_metrics(expect="negative", reground_meta={"run": {"end_reason": "no_target"}},
                       **_synthetic(reground=True, lifted_leg="RL"))
    assert g3["g4_7"]["passed"] is False and g3["g4_7"]["no_target"] is True


def test_g4_entry_late_and_output_after_fault_fail() -> None:
    d = _synthetic(reground=True, lifted_leg="RL")
    d["phases"] = [[0.0, "level"], [5.0, "ready"], [10.1, "fault_reground"], [14.0, "fault"]]
    d["issued_u"] = d["issued_u"].copy()
    d["issued_u"][-1, 0] = 1e-4
    g = s8.g4_metrics(expect="reground", **d)
    assert g["g4_1"]["passed"] is False and g["g4_1"]["entry_delay_s"] == pytest.approx(0.1)
    assert g["g4_3"]["passed"] is False


# --- 323.9 boundaries (rev. 64 supplement) -------------------------------------------------------


def test_g4_2_three_ms_tail_is_no_target_and_late_airborne() -> None:
    d = _synthetic(reground=True, lifted_leg="RL")
    air = d["airborne"].copy()
    tp = d["tp"]
    air[(tp >= 9.800 - 1e-9) & (tp < 9.803 - 1e-9), 1] = True  # FR tail 3 ms on t_f - 0.2
    air[(tp >= 10.10 - 1e-9) & (tp < 10.15 - 1e-9), 0] = True  # FL 50 ms after t_f
    air[(tp >= 10.20 - 1e-9) & (tp < 10.21 - 1e-9), 3] = True  # RR 10 ms: below 20 ms
    d["airborne"] = air
    g = s8.g4_metrics(expect="reground", **d)["g4_2"]
    assert g["airborne_at_samples"]["FR"] == [True, False, False]
    assert g["truth_airborne"] == ["RL"] and g["missed"] == [] and g["passed"] is True
    assert g["airborne_ms_in_window"]["FR"] == pytest.approx(3.0)
    assert g["late_airborne"] == ["FL"]
    assert g["late_airborne_ms"]["RR"] == pytest.approx(10.0)
    # two of the three samples airborne -> a true target, missed when not targeted
    air2 = d["airborne"].copy()
    air2[(tp >= 9.89) & (tp < 10.01), 1] = True
    d["airborne"] = air2
    g2 = s8.g4_metrics(expect="reground", **d)["g4_2"]
    assert g2["truth_airborne"] == ["FR", "RL"] and g2["missed"] == ["FR"]


@pytest.mark.parametrize("dip_s,ok", [(0.49, True), (0.51, False)])
def test_g4_5_healthy_dip_limit(dip_s, ok) -> None:
    d = _synthetic(reground=True, lifted_leg="RL")
    f = d["judged_force_N"].copy()
    tp = d["tp"]
    f[(tp >= 11.0 - 1e-9) & (tp < 11.0 + dip_s - 1e-9), 3] = 5e3  # RR (healthy) dip
    d["judged_force_N"] = f
    g = s8.g4_metrics(expect="reground", **d)["g4_5"]
    assert g["healthy_dips"]["RR"]["count"] == 1
    assert g["healthy_dips"]["RR"]["longest_s"] == pytest.approx(dip_s, abs=1.5e-3)
    assert g["passed"] is ok


def test_g4_5_faulty_leg_extend_limit() -> None:
    d = _synthetic(reground=True, lifted_leg="RL")
    fc = d["f_cyl_N"].copy()
    fc[(d["tp"] >= 12.0) & (d["tp"] < 12.1), 1] = 280e3  # FR (faulty) above 278.7 kN
    d["f_cyl_N"] = fc
    g = s8.g4_metrics(expect="reground", **d)["g4_5"]
    assert g["passed"] is False and g["faulty_F_cyl_max_kN"] == pytest.approx(280.0)
    assert g["faulty_rise_vs_entry_kN"] == pytest.approx(200.0)
    fc[(d["tp"] >= 12.0) & (d["tp"] < 12.1), 1] = 270e3  # +190 kN rise: limit only judges
    assert s8.g4_metrics(expect="reground", **d)["g4_5"]["passed"] is True


@pytest.mark.parametrize("freq_hz", [1.24, 1.5, 2.9])
def test_g4_6_rocking_sine_passes(freq_hz) -> None:
    d = _synthetic(reground=True, lifted_leg="RL")
    amp = math.radians(0.38)
    s = amp * np.sin(2 * math.pi * freq_hz * d["tp"])
    d["roll_pitch_rad"] = np.column_stack([s, s])
    g = s8.g4_metrics(expect="reground", **d)["g4_6"]
    assert g["passed"] is True and max(g["max_change_deg"]) < 0.5
    if freq_hz == 1.24:  # t_f falls off the zero crossing: the rev. 64 instant rule would fail
        assert max(g["instant_max_change_deg"]) > 0.5
    # an equilibrium change of 0.6 deg fails
    step = np.where(d["tp"] >= 11.0, math.radians(0.6), 0.0)
    d["roll_pitch_rad"] = np.column_stack([s + step, s])
    assert s8.g4_metrics(expect="reground", **d)["g4_6"]["passed"] is False


def test_g4_4_short_window_is_undecidable() -> None:
    d = _synthetic(reground=True, lifted_leg="RL")
    kc, kp = d["tc"] <= 17.5 + 1e-9, d["tp"] <= 17.5 + 1e-9
    for key in ("tc", "phase_series", "issued_u"):
        d[key] = d[key][kc]
    for key in ("tp", "airborne", "judged_force_N", "f_cyl_N", "head_true_Pa",
                "roll_pitch_rad", "s_motor_m"):
        d[key] = d[key][kp]
    g = s8.g4_metrics(expect="reground", **d)
    assert g["g4_4"]["status"] == "undecidable" and g["g4_4"]["passed"] is None
    assert g["g4_4"]["window_length_s"] == pytest.approx(2.5)
    row = [r for r in s8.g4_rows("X", g) if "G4-4" in r["item"]][0]
    assert row["kind"] == "hold" and row["passed"] is None


def test_extend_force_limits_from_yaml() -> None:
    from outrigger_sim.params import load_params

    lim = s8.extend_force_limits_N(load_params(level="top"))
    np.testing.assert_allclose(lim, EXTEND_LIMIT_N)


def test_fault_entry_and_classify_fault() -> None:
    ph = [[0.0, "level"], [10.0, "fault_reground"], [14.0, "fault"]]
    assert s8.fault_entry_s(ph) == 10.0
    assert s8.fault_entry_s([[0.0, "level"], [12.0, "fault"]]) == 12.0
    assert s8.fault_entry_s([[0.0, "level"]]) is None
    assert s8.legs_in("RL,FR") == ["FR", "RL"] and s8.legs_in("") == [] and s8.legs_in(None) == []
    names = [(10.0, "FAULT_HEAD_PRESSURE:FR"), (10.0, "fault_reground_start:RL")]
    c = s8.classify_fault(10.0, names, None, None, soft_max_m=0.6948, margin_m=1e-3)
    assert c["cause"] == "head_sensor_reground" and c["legs"] == ["FR"]
    assert c["reground_targets"] == ["RL"]
    # no target legs named: the plain sensor cause, as before
    c2 = s8.classify_fault(10.0, [(10.0, "FAULT_HEAD_PRESSURE:FR"),
                                  (10.0, "fault_reground_start:")], None, None,
                           soft_max_m=0.6948, margin_m=1e-3)
    assert c2["cause"] == "sensor"


def test_head_fault_of() -> None:
    res = {"settings": {"s8": {"event_spec": {"kind": "fault", "head_fault": {
        "leg": "FR", "fault": "offset", "value_Pa": 150e5, "after_event_s": 0.05,
        "expect": "negative"}}}}, "head_fault_t_s": 47.75, "head_fault_first_applied_t_s": 47.8}
    spec, t_arm, t_first = s8.head_fault_of(res)
    assert spec["leg"] == "FR" and t_arm == 47.75 and t_first == 47.8
    assert s8.head_fault_of({"settings": {"s8": {"event_spec": {"kind": "settle"}}}}) == \
        (None, None, None)


# --- C-S8-70 (spec rev. 65 333 / 335.2) -------------------------------------------------------

C68_HASHES = {  # meta / repr SHA-256 of the six C-S8-68 cases before C-S8-70 (unchanged)
    "MLJ_G4H_FS24_FR_Fs0": ("8303a31f0d5df4b3b3ecf4c318a899e24dcaaee20844a066f58e961de881aa27",
                            "1195a3203f80455d9341ffcd1cb35669092b7d55ccfcb3deb699c6a26ebbbd1a"),
    "MLJ_G4H_FS24_FR_Fs8": ("174aabe8e45cd21228beaacd8aa07bb6e9518e9ffec5b8c4a071a05043b53305",
                            "f545196dd213d91427a24d2a0e0d7a44c18f2ebb274324da0459f782bb65e18e"),
    "MLJ_G4H_FS24_RL_Fs0": ("def978a5f66ed4dc6b6e83a5f1ff3a2c3f4cc8213116f9a81344ce1694901618",
                            "36fe950ce091a17c6a644df6a057e19766c6192244b3966c329fb8fd872be514"),
    "MLJ_G4H_FS24_RL_Fs8": ("f383f3f6424957955f555a604939770a360d20eed21a3222a9d2c47d34d51a98",
                            "f239889da7c9901ead3bfa8fdb08975be2e88de5d48e088d624df1ce1e7dc890"),
    "MLJ_G4H_quiet_FR_Fs0": ("7eb070fe53588aa42d12a80dae970307d5d7a0d8d8f60211f8247cecba2f0b7f",
                             "dddb481b994010ab79d698de527c6615bf514d69f8d00cef138dc0f543b5144a"),
    "MLJ_G4H_G4_RR_Fs4": ("8286fc09bc3a082f76e8717d7eca74fcbc712e1dac99fb6533a3f13443b40f29",
                          "274c87e41a839b7a3ce6ae131c3d04ac64f52ec134de0755a529d1fc47f66b69"),
}


def test_c68_case_hashes_unchanged(run_s8c) -> None:
    tab = run_s8c.case_table()
    for cid, (meta_sha, repr_sha) in C68_HASHES.items():
        assert _meta_sha(run_s8c, tab[cid]) == meta_sha, cid
        assert hashlib.sha256(repr(tab[cid]).encode()).hexdigest() == repr_sha, cid


def test_g4_3_fault_sample_output_is_a_record() -> None:
    """① d = 1: the output issued on the FAULT sample is the previous command (record)."""
    d = _synthetic(reground=True, lifted_leg="RL")
    u = d["issued_u"].copy()
    k_fault = int(np.flatnonzero(np.isclose(d["tc"], 14.0))[0])
    u[k_fault, 2] = 5.74e-3
    d["issued_u"] = u
    g = s8.g4_metrics(expect="reground", **d)["g4_3"]
    assert g["passed"] is True and g["zero_check_from_s"] == pytest.approx(14.1)
    assert g["issued_u_at_fault_sample_mm_s"]["RL"] == pytest.approx(5.74)
    assert g["output_delay_periods"] == 1
    u[k_fault + 1, 2] = 1e-4  # one period later: a real output after FAULT
    assert s8.g4_metrics(expect="reground", **d)["g4_3"]["passed"] is False


def test_g4_7_t_f_sample_output_and_end_reason() -> None:
    """③ G4-7 judged on no_target only; the t_f-sample output (d = 1) is recorded."""
    d = _synthetic(reground=False, lifted_leg=None)
    u = d["issued_u"].copy()
    k_f = int(np.flatnonzero(np.isclose(d["tc"], 10.0))[0])
    u[k_f, 3] = 0.66e-3
    d["issued_u"] = u
    meta = {"run": {"end_reason": "no_target", "targets": []}}
    g = s8.g4_metrics(expect="record", reground_meta=meta, **d)
    assert g["g4_7"]["passed"] is True and g["g4_7"]["end_reason"] == "no_target"
    assert g["g4_7"]["issued_u_at_t_f_sample_mm_s"]["RR"] == pytest.approx(0.66)
    assert g["g4_3"]["passed"] is True
    u[k_f + 1, 3] = 0.66e-3
    assert s8.g4_metrics(expect="record", reground_meta=meta, **d)["g4_7"]["passed"] is False
    g2 = s8.g4_metrics(expect="negative", reground_meta={"run": {"end_reason": "attitude"}},
                       **_synthetic(reground=False, lifted_leg=None))
    assert g2["g4_7"]["passed"] is None and g2["g4_7"]["same_as_direct_fault"] is True


def test_g4_4_records_mean05_and_tail() -> None:
    """② teeter on RL after FAULT + 1 s: the rev. 64 strict rule fails (record), the C-S8-71
    rule (0.5 s mean >= F_min and, since U-S8-74 (a), no pad lift-off) passes."""
    d = _synthetic(reground=True, lifted_leg="RL", rl_after_kN=40.0)
    f = d["judged_force_N"].copy()
    tp = d["tp"]
    late = tp >= 12.0
    f[late, 2] = 40e3 + 35e3 * np.sin(2 * math.pi * 2.0 * tp[late])  # 2 Hz, min 5 kN
    d["judged_force_N"] = f
    g = s8.g4_metrics(expect="reground", **d)["g4_4"]
    assert g["passed"] is True and g["min_from_fault_plus_1s_kN"]["RL"] == pytest.approx(5.0,
                                                                                         abs=0.1)
    assert g["instant_min_ge_F_min"] is False and g["instant_min_positive"] is True
    assert g["below_F_min_s"]["RL"] > 0.0 and g["below_F_min_s"]["FL"] == 0.0
    assert g["mean05_passed"] is True
    assert g["mean05_min_kN"]["RL"] == pytest.approx(40.0, abs=0.2)
    assert g["last2s_mean_kN"]["RL"] == pytest.approx(40.0, abs=0.5)
    assert g["last2s_ptp_kN"]["RL"] == pytest.approx(70.0, abs=0.1)
    assert g["last2s_ptp_kN"]["FL"] == pytest.approx(0.0)
    # windows end at or after t_from: an FL dip over [14.0, 14.4) is outside every window that
    # ends at >= 15.0 s, inside one that ends at 14.4 s
    f2 = d["judged_force_N"].copy()
    f2[(tp >= 14.0 - 1e-9) & (tp < 14.4 - 1e-9), 0] = 0.0
    rec = s8.g4_4_records(tp, f2, 15.0, F_MIN, True)
    assert rec["mean05_min_kN"]["FL"] == pytest.approx(80.0)
    rec2 = s8.g4_4_records(tp, f2, 14.4, F_MIN, True)
    assert rec2["mean05_min_kN"]["FL"] == pytest.approx(80.0 * 0.2, abs=0.2)
    assert s8.g4_4_records(tp, f2, 14.4, F_MIN, False)["mean05_passed"] is None


def test_g4_4_records_short_record() -> None:
    rec = s8.g4_4_records(np.array([0.0]), np.zeros((1, 4)), 0.0, F_MIN, True)
    assert rec["mean05_min_kN"] is None and rec["last2s_mean_kN"] is None


def test_g4_8_abort_and_step_suspend_events() -> None:
    """⑦ WARN_FAULT_REGROUND_ABORT / INFO_D1_STEP_SUSPENDED counts, hold_count, attitude."""
    d = _synthetic(reground=True, lifted_leg="RL")
    d["names"] = d["names"] + [(10.1, "INFO_D1_STEP_SUSPENDED:FR"),
                               (13.9, "WARN_FAULT_REGROUND_ABORT:protected_leg_low"),
                               (13.9, "WARN_FAULT_REGROUND_LIMIT:RL:time")]
    meta = {"run": {"end_reason": "protected_leg_low", "max_filtered_attitude_change_rad": 0.004,
                    "targets": [{"leg": "RL", "hold_count": 2, "outcome": "aborted"}]}}
    g8 = s8.g4_metrics(expect="reground", reground_meta=meta, **d)["g4_8"]
    assert g8["abort_count"] == 1 and g8["abort_events"] == [[13.9, "protected_leg_low", None]]
    assert g8["step_suspended_count"] == 1 and g8["step_suspended_events"] == [[10.1, "FR"]]
    assert g8["hold_count"] == {"RL": 2} and g8["controller_targets"]["RL"]["hold_count"] == 2
    assert g8["max_filtered_attitude_change_rad"] == 0.004
    assert g8["end_reason"] == "protected_leg_low"
    # a direct FAULT (no re-ground window) still carries the counts
    g0 = s8.g4_metrics(expect="negative", **_synthetic(reground=False, lifted_leg=None))["g4_8"]
    assert g0["abort_count"] == 0 and g0["step_suspended_count"] == 0
    row = [r for r in s8.g4_rows("X", s8.g4_metrics(expect="reground", reground_meta=meta, **d))
           if "G4-8" in r["item"]][0]
    assert row["kind"] == "record" and row["value"]["abort_count"] == 1


def test_f2_head_fault_leg_cut() -> None:
    """④ F2 leaves out the head-fault leg from the arm time (relative ``head_fault_t_s``)."""
    tc = np.round(np.arange(40.0, 50.0 + 1e-9, 0.1), 10)
    res = {"settings": {"s8": {"event_spec": {"head_fault": {"leg": "RL"}}}},
           "head_fault_t_s": 48.165, "head_fault_first_applied_t_s": 48.2}
    cut, spec, t_arm = s8.head_fault_leg_cut(res, tc)
    assert spec["leg"] == "RL" and t_arm == 48.165
    assert cut.shape == (tc.size, 4) and not cut[:, [0, 1, 3]].any()
    assert np.array_equal(np.flatnonzero(cut[:, 2]), np.flatnonzero(tc >= 48.165))
    none, spec0, arm0 = s8.head_fault_leg_cut({"settings": {"s8": {}}}, tc)
    assert not none.any() and spec0 is None and arm0 is None


def test_head_fault_delivered_record(run_s8c, tmp_path) -> None:
    """⑥ the wrapper keeps the reading before / after the injection; the judge summary."""
    inner = _Inner()
    w = run_s8c.HeadFaultInjection(inner, leg=1, fault="offset", value_Pa=150e5)
    head = np.array([90e5, 100e5, 110e5, 120e5])
    w.arm(2.05)
    for t in (1.9, 2.0, 2.1, 2.2):
        w.update(_Meas(t, head))
    info = w.save_delivered(tmp_path / run_s8c.HEAD_DELIVERED_FILE)
    assert info["samples"] == 4 and info["applied_samples"] == 2
    assert run_s8c.HEAD_DELIVERED_FILE == s8.HEAD_DELIVERED_FILE
    z = s8.load_head_delivered(tmp_path)
    np.testing.assert_array_equal(z["t"], [1.9, 2.0, 2.1, 2.2])
    np.testing.assert_array_equal(z["meas.head_pressure"], np.tile(head, (4, 1)))
    assert z[s8.HEAD_DELIVERED_KEY][2, 1] == 250e5 and z[s8.HEAD_DELIVERED_KEY][1, 1] == 100e5
    s = s8.head_delivered_summary(tmp_path, "FR", t0=1.0)
    assert s["available"] and s["applied_samples"] == 2
    assert s["first_applied_t_s"] == pytest.approx(1.1)
    assert s["fault_leg_delta_bar"] == pytest.approx([150.0, 150.0])
    assert s["other_legs_max_abs_delta_bar"] == 0.0 and s["before_arm_max_abs_delta_bar"] == 0.0
    assert s8.head_delivered_summary(tmp_path / "none", "FR", 0.0)["available"] is False


def test_branch_restore_path_applies_the_soil_rule(run_s8c) -> None:
    """⑤ (spec rev. 65 334.3): the runner restores branches only in ``job_ml_episode``, and that
    path applies the soil rule (LOC restored on old pickles, else SoilStateRestoreError)."""
    import inspect

    src = inspect.getsource(run_s8c)
    callers = [ln for ln in src.splitlines()
               if "restore_branch(blob" in ln and not ln.lstrip().startswith("def ")]
    assert len(callers) == 2  # job_ml_episode + smoke_branch (fresh pickle of the same code)
    ep = inspect.getsource(run_s8c.job_ml_episode)
    assert "restore_branch(blob, engine)" in ep
    k_restore = ep.index("restore_branch(blob, engine)")
    k_ran = ep.index("ran_without_soil_response(c2)")
    k_rule = ep.index("apply_soil_rule(")
    k_run = ep.index("run_closed_loop(")
    assert k_restore < k_ran < k_rule < k_run
    smoke = inspect.getsource(run_s8c.smoke_branch)
    assert "save_branch(" in smoke and smoke.index("save_branch(") < smoke.index("restore_branch(")


# --- C-S8-71 (spec rev. 66 338, U-S8-72 (a)) ----------------------------------------------------


def test_g4_4_instant_floor_zero_fails_even_with_mean_ok() -> None:
    """① a short pad lift-off (20 ms at 0 N, airborne) fails G4-4 although the 0.5 s mean stays
    >= F_min (U-S8-74 (a): (b) = no pad lift-off, ``test_s8_u74.py``)."""
    d = _synthetic(reground=True, lifted_leg="RL", rl_after_kN=60.0)
    f = d["judged_force_N"].copy()
    tp = d["tp"]
    dip = (tp >= 16.0 - 1e-9) & (tp < 16.02 - 1e-9)
    f[dip, 2] = 0.0  # 20 ms at 0 N
    d["judged_force_N"] = f
    d["airborne"] = d["airborne"].copy()
    d["airborne"][dip, 2] = True
    g = s8.g4_metrics(expect="reground", **d)["g4_4"]
    assert g["mean05_min_kN"]["RL"] > F_MIN / 1e3
    assert g["instant_min_positive"] is False and g["no_lift"] is False
    assert g["passed"] is False
    assert g["rule"] == s8.G4_4_RULE
    # 1 kN instead of 0 N, pad on the ground: mean ok, no lift -> passes; the strict rule is
    # recorded as failed
    f[dip, 2] = 1e3
    d["airborne"][dip, 2] = False
    g2 = s8.g4_metrics(expect="reground", **d)["g4_4"]
    assert g2["passed"] is True and g2["instant_min_ge_F_min"] is False
    assert g2["last_below_F_min_t_s"]["RL"] == pytest.approx(16.019, abs=1.5e-3)
    row = [r for r in s8.g4_rows("X", s8.g4_metrics(expect="reground", **d))
           if "G4-4" in r["item"]][0]
    assert row["kind"] == "judged" and row["passed"] is True and "instantaneous" in row["note"]


def test_g4_4_mean_below_f_min_fails() -> None:
    """① a constant 5 kN after the re-ground (mean below F_min) fails."""
    g = s8.g4_metrics(expect="reground",
                      **_synthetic(reground=True, lifted_leg="RL", rl_after_kN=5.0))["g4_4"]
    assert g["instant_min_positive"] is True and g["mean05_passed"] is False
    assert g["passed"] is False


def test_g4_end_attitude_record() -> None:
    """③ G4-E: last 0.5 s mean minus the [FAULT - 0.5, FAULT] mean (record row)."""
    d = _synthetic(reground=True, lifted_leg="RL")
    tp = d["tp"]
    roll = np.where(tp >= 16.0, math.radians(0.3), 0.0)
    d["roll_pitch_rad"] = np.column_stack([roll, np.zeros_like(roll)])
    g = s8.g4_metrics(expect="reground", **d)
    e = g["g4_end"]
    assert e["change_deg"][0] == pytest.approx(0.3) and e["change_deg"][1] == pytest.approx(0.0)
    assert e["attitude_at_fault_deg"] == pytest.approx([0.0, 0.0])
    assert e["fault_mean_window_s"] == pytest.approx([13.5, 14.0])
    assert e["instant_max_abs_change_deg"][0] == pytest.approx(0.3)
    row = [r for r in s8.g4_rows("X", g) if "G4-E" in r["item"]][0]
    assert row["kind"] == "record" and row["passed"] is None
    d["roll_pitch_rad"] = None
    assert s8.g4_metrics(expect="reground", **d)["g4_end"]["passed"] is None


def test_general_rows_not_applicable_on_head_fault_runs() -> None:
    """③ run / 2 attitude / RE1b re-READY / 6 re-READY of a head-fault run are not applicable;
    other rows and runs without a head fault are untouched."""
    sms = {"H": {"s8": {"event_spec": {"head_fault": {"leg": "FR", "expect": "reground"}}}},
           "Q": {"s8": {"event_spec": {"head_fault": {"leg": "FR", "expect": "negative"}}}},
           "N": {"s8": {"event_spec": {"kind": "settle"}}}}
    rows = [s8._row(item, cid, 1.0, None, False, "n") for cid in ("H", "Q", "N")
            for item in s8.G4_NA_ITEMS]
    rows.append(s8._row("C-S8-68 G4-4 x", "H", 1.0, None, False, "n"))
    n = s8.apply_head_fault_na_rows(rows, sms)
    assert n == 8
    na = [r for r in rows if r["kind"] == s8.G4_NA_KIND]
    assert {r["case"] for r in na} == {"H", "Q"}
    assert all(r["passed"] is None and r["passed_raw"] is False and r["kind_raw"] == "judged"
               and r["note"].startswith("C-S8-71: not applicable") for r in na)
    assert [r["passed"] for r in rows if r["case"] == "N"] == [False] * 4
    assert rows[-1]["passed"] is False and rows[-1]["kind"] == "judged"
    assert s8.head_fault_expect(sms["H"]) == "reground" and s8.head_fault_expect(sms["N"]) is None
    # an unknown expectation keeps the rows
    sms["H"]["s8"]["event_spec"]["head_fault"]["expect"] = "other"
    rows2 = [s8._row(s8.RUN_ITEM, "H", 1.0, None, False, "n")]
    assert s8.apply_head_fault_na_rows(rows2, sms) == 0 and rows2[0]["passed"] is False


def test_head_delivered_alignment(run_s8c, tmp_path) -> None:
    """④ the side file is row-aligned with record/record.npz (t, head before the injection)."""
    inner = _Inner()
    w = run_s8c.HeadFaultInjection(inner, leg=1, fault="offset", value_Pa=150e5)
    head = np.array([90e5, 100e5, 110e5, 120e5])
    w.arm(2.05)
    for t in (1.9, 2.0, 2.1, 2.2):
        w.update(_Meas(t, head))
    w.save_delivered(tmp_path / run_s8c.HEAD_DELIVERED_FILE)
    (tmp_path / "record").mkdir()
    np.savez(tmp_path / "record" / "record.npz", t=np.array([1.9, 2.0, 2.1, 2.2]),
             **{"meas.head_pressure": np.tile(head, (4, 1))})
    s = s8.head_delivered_summary(tmp_path, "FR", t0=1.0)
    a = s["record_alignment"]
    assert a["aligned"] is True and a["record_rows"] == a["file_rows"] == 4
    assert a["record_has_delivered_key"] is False
    np.savez(tmp_path / "record" / "record.npz", t=np.array([1.9, 2.0, 2.1, 2.3]),
             **{"meas.head_pressure": np.tile(head, (4, 1))})
    assert s8.head_delivered_summary(tmp_path, "FR", t0=1.0)["record_alignment"]["aligned"] \
        is False
    (tmp_path / "record" / "record.npz").unlink()
    assert s8.head_delivered_summary(tmp_path, "FR", 1.0)["record_alignment"] == \
        {"record_npz": False}
