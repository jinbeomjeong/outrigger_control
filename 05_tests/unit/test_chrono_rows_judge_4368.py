"""436.8 Chrono path 1 aggregation new version (``04_scripts/02_chrono/chrono_rows_judge_4368.py``; rules rev5 R5-A1,
rev6 R6-A / R6-B / R6-C3).

Synthetic inputs only, plus an execution-path smoke on the stored G-S batch (no judgement, skipped when absent).
No Chrono run.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHRONO_SCRIPTS = PROJECT_ROOT / "04_scripts" / "02_chrono"
MAIN_CHECKOUT = Path(r"C:\workspace\outrigger_control")
PARAMS = PROJECT_ROOT / "02_params" / "rexome33.yaml"
F_MIN = 9414.58911
W = 380_000.0


def _import(name: str):
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(CHRONO_SCRIPTS))


@pytest.fixture(scope="module")
def mod():
    return _import("chrono_rows_judge_4368")


def _rules_dir(mod) -> Path:
    for d in (PROJECT_ROOT / "06_analysis" / "02_control" / "verif_matrix",
              MAIN_CHECKOUT / "06_analysis" / "02_control" / "verif_matrix"):
        if all((d / n).exists() for n in mod.RULES_SEALS):
            return d
    pytest.skip("rules original .. rev6 not found")


# ------------------------------------------------------------------------------------------------- departure / t_D
def test_departure_100_samples(mod):
    t = np.arange(0, 1.0, 1e-3)
    cn = np.full(t.size, 10_000.0)
    cn[200:300] = 0.0  # exactly 100 samples below 0.01 W
    d = mod.departure(t, cn, W, "count")
    assert d["departed"] and d["t_departure_s"] == pytest.approx(0.2)
    assert d["t_confirmed_s"] == pytest.approx(0.299)
    assert not mod.departure(t, cn, W, "span")["departed"]  # the runner rule needs 101 samples
    cn[200:301] = 0.0
    assert mod.departure(t, cn, W, "span")["departed"]


def test_recontact_duration_to_run_end(mod):
    t = np.arange(0, 2.0, 1e-3)
    cn = np.zeros(t.size)
    dep = mod.departure(t, cn, W, "count")
    cn[1500:] = 0.02 * W  # loaded to the run end: 500 samples
    rc = mod.recontact_events(t, cn, W, dep, None, None)
    assert rc["events"][0]["samples"] == 500
    assert rc["events"][0]["duration_s"] == pytest.approx(0.5)
    assert rc["events"][0]["class"] == "strict_fail" and rc["pass"] is False


# ------------------------------------------------------------------------------------------------- P3-2 / P3-8
def _tl(mod, events):
    return mod.loc_timeline(events)


def test_p32_strict_order_and_loaded(mod):
    t = np.arange(0, 20.0, 1e-3)
    cn = np.zeros(t.size)
    ev = [(10.0, "crawler_liftoff_confirmed")]
    p = mod.p32_block(t, cn, W, _tl(mod, ev), 9.0, 10.0, 2.9117)
    assert p["order"] is False and p["within"] is False  # LOC == first DONE -> false (strict <)
    p = mod.p32_block(t, cn, W, _tl(mod, ev), 9.0, 10.1, 2.9117)
    assert p["order"] and p["within"]
    cn[:] = 0.01 * W  # exactly 0.01 W is not loaded (> 0.01 W)
    assert mod.p32_block(t, cn, W, _tl(mod, ev), 9.0, None, 2.9117)["loaded"] is False


def test_loc_timeline_revoke_and_revoked_normal(mod):
    t = np.arange(0, 20.0, 1e-3)
    cn = np.zeros(t.size)
    cn[(t > 4.9) & (t < 5.1)] = 0.05 * W
    ev = [(5.0, "crawler_liftoff_confirmed"), (6.0, "INFO_LOC_REVOKED"), (8.0, "crawler_liftoff_confirmed")]
    tl = _tl(mod, ev)
    assert tl["t_loc_first_s"] == 5.0 and tl["t_loc_final_s"] == 8.0 and tl["revoked_loc_s"] == [5.0]
    p = mod.p32_block(t, cn, W, tl, 4.0, None, 5.0)
    assert p["revoked"][0]["loaded"] is True


def _p38(mod, events, f, g63=True, fault=False, loc="first"):
    t = np.arange(0, 30.0, 1e-3)
    return mod.p38_block(t, f(t), events, _tl(mod, events), F_MIN, fault, loc, g63)


def test_p38_window_soil_mode_and_first_loc(mod):
    ev = [(4.0, "soil_mode_start"), (5.0, "leg_reapproach_start:FL"), (10.0, "crawler_liftoff_confirmed")]
    p = _p38(mod, ev, lambda t: np.full((t.size, 4), 50_000.0))
    assert p["window_end_s"] == 4.0 and p["events"] == [] and p["verdict"] == "pass"
    ev = [(5.0, "leg_reapproach_start:FL"), (10.0, "crawler_liftoff_confirmed"), (11.0, "INFO_LOC_REVOKED"),
          (15.0, "crawler_liftoff_confirmed")]
    p = _p38(mod, ev, lambda t: np.full((t.size, 4), 50_000.0))
    assert p["window_end_s"] == 10.0 and len(p["events"]) == 1


def test_p38_377_demoted(mod):
    ev = [(5.0, "leg_reapproach_start:FL"), (10.0, "crawler_liftoff_confirmed")]
    p = _p38(mod, ev, lambda t: np.full((t.size, 4), 20_000.0))
    assert p["verdict"] == "flag" and p["flags"] == ["P3-8_demoted"]
    assert p["demoted_items"] == [{"item": "G6-7_preloc", "rule": "377", "flag": "P3-8_demoted"}]
    assert p["preloc_rows"][0]["window_s"] == [5.0, 11.0]  # first LOC + 1 s (rev6 R6-B3)


def test_p38_preloc_loss_branch_and_fail(mod):
    ev = [(5.0, "leg_reapproach_start:FL"), (10.0, "crawler_liftoff_confirmed")]

    def low(t):
        f = np.full((t.size, 4), 20_000.0)
        f[(t > 6.0) & (t < 6.5), 0] = 5_000.0  # below F_min inside 5 .. 11 s
        return f

    p = _p38(mod, ev, low, g63=True)
    assert p["verdict"] == "flag" and p["flags"] == ["P3-8_preloc_loss"]
    assert p["demoted_items"][0]["rule"] == "U-S9-G6c"
    assert _p38(mod, ev, low, g63=False)["verdict"] == "fail"
    assert _p38(mod, ev, low, g63=True, fault=True)["verdict"] == "fail"


def test_p38_other_kind_not_377(mod):
    ev = [(5.0, "relevel_predicted:FL"), (10.0, "crawler_liftoff_confirmed")]
    p = _p38(mod, ev, lambda t: np.full((t.size, 4), 50_000.0), g63=True)
    assert p["preloc_flag_ok"] is False and p["flags"] == ["P3-8_preloc_loss"]


def test_p38_final_loc_recorded(mod):
    ev = [(5.0, "leg_reapproach_start:FL"), (10.0, "crawler_liftoff_confirmed"), (10.5, "INFO_LOC_REVOKED"),
          (20.0, "crawler_liftoff_confirmed")]

    def f(t):
        x = np.full((t.size, 4), 20_000.0)
        x[(t > 15.0) & (t < 15.5), 0] = 5_000.0  # only inside the final-LOC window
        return x

    p = _p38(mod, ev, f)
    assert p["preloc_flag_ok"] is True
    assert p["record_377_other_loc"]["preloc_flag_ok"] is False and p["record_377_other_loc"]["differs"]


# ------------------------------------------------------------------------------------------------- pressure / lift
def test_moving_pressure_threshold(mod):
    u = np.zeros((5, 4))
    u[2, 0] = 5e-7  # above 1e-9 (the runner judge's 1e-6 would call it locked)
    a = [0.0132732, 0.0132732, 0.0095033, 0.0095033]
    f = np.full((5, 4), 1000.0)
    f[2, 0] = 190e5 * a[0]
    mp = mod.moving_pressure({"u_applied": u, "F_cyl": f}, a, event_row=False)
    assert mp["moving_samples"] == 1 and mp["max_moving_bar"] == pytest.approx(190.0)
    assert mp["within"] is False
    assert mod.moving_pressure({"u_applied": u, "F_cyl": f}, a, event_row=True)["status"] == "not_judgeable"


def test_d8_lift_time_phase_condition(mod):
    t = np.arange(0, 10.0, 1e-3)
    cn = np.full(t.size, 1000.0)
    cn[(t >= 1.0) & (t < 2.0)] = 0.0  # zero during touch: not t_lift
    cn[t >= 6.0] = 0.0
    phases = [(0.5, "check"), (0.9, "touch"), (5.0, "level")]
    assert mod.d8_lift_time(t, cn, phases) == pytest.approx(6.0)


def test_lift_samples_q14(mod):
    t = np.arange(0, 1.0, 1e-3)
    pn = np.full((t.size, 4), 100.0)
    pn[500, 2] = 0.0
    out = mod.lift_samples(t, pn, 0.2)
    assert out["lifted"] and out["per_leg"]["RL"]["samples"] == 1
    assert mod.lift_samples(t, pn, 0.6)["lifted"] is False


# ------------------------------------------------------------------------------------------------- rigid C1
def _rigid_row(mod, tmp: Path, f_dip: float, dip_t: float, *, rigid=True) -> dict:
    t0 = 3.0
    t = t0 + np.arange(1, 40001) * 1e-3
    cn = np.where(t < t0 + 10.0, 5000.0, 0.0)
    f = np.full((t.size, 4), 60_000.0)
    f[np.abs(t - (t0 + dip_t)) < 0.003, 1] = f_dip
    pads = {"t": t, "crawler_normal_N": cn, "F_cyl_min_interval": f, "F_cyl_mean_20ms": f.copy(),
            "airborne": np.zeros((t.size, 4), bool), "N": np.full((t.size, 4), 1e4)}
    res = {"settings": {"start_t_s": t0, "s8": {"crawler_contact": "nsc_rigid" if rigid else "l1r_flexible",
                                                "crawler_check_passed": not rigid}},
           "phases": [[0.1, "check"], [5.0, "touch"], [8.0, "level"]], "event_t_s": None}
    return {"pads": pads, "result": res, "t0": t0, "phases": [(t0 + 0.1, "check"), (t0 + 5.0, "touch"),
                                                              (t0 + 8.0, "level")]}


def test_c1_hold_is_not_judgeable_and_stop(mod, tmp_path):
    row = _rigid_row(mod, tmp_path, 10_000.0, 12.0)  # dip 2 s after t_lift, slow mean stays above the limit
    t_lift = mod.d8_lift_time(row["pads"]["t"], row["pads"]["crawler_normal_N"], row["phases"])
    assert t_lift == pytest.approx(13.0)
    c1 = mod.c1_block(row, t_lift, F_MIN, "s8a2")
    assert c1["hold"] and c1["status"] == "not_judgeable" and c1["stop"]
    assert c1["limit_N"] == pytest.approx(F_MIN + 5000.0)
    assert c1["s8a2_airborne_samples_in_window"] == 0
    row = _rigid_row(mod, tmp_path, 10_000.0, 12.0, rigid=False)
    c1 = mod.c1_block(row, t_lift, F_MIN, "s8a2")
    assert c1["verdict"] == "fail" and not c1["hold"]


# ------------------------------------------------------------------------------------------------- SCM row end to end
def _write_scm_row(d: Path, *, sgs: bool, name="D1S_G1_B_middle_Fs4_spJ1FL") -> Path:
    d = d / name
    (d / "record").mkdir(parents=True)
    t0, dt = 5.0, 1e-3
    t = t0 + np.arange(0, 60_000) * dt
    cn = np.where(t < t0 + 20.0, 0.5 * W, 0.0)
    f = np.full((t.size, 4), 50_000.0)
    pn = np.full((t.size, 4), 1e5)
    np.savez(d / "step_series.npz", t_s=t, scm_crawler_normal_N=cn, scm_pad_normal_N=pn, F_cyl_N=f)
    tr = t0 + np.arange(1, 600) * 0.1
    u = np.zeros((tr.size, 4))
    u[50:60] = 0.01
    np.savez(d / "record" / "record.npz", t=tr, u_applied=u, F_cyl=np.full((tr.size, 4), 50_000.0))
    np.savez(d / "r8_series.npz", t=tr)
    phases = [(t0 + 0.1, "check"), (t0 + 5.0, "touch"), (t0 + 10.0, "level")]
    events = [(t0 + 21.0, "crawler_liftoff_confirmed")]
    if sgs:
        events.append((t0 + 30.0, "FAULT_LIFT_STROKE_LIMIT:soil:FL"))
        phases.append((t0 + 30.0, "fault"))
    else:
        phases += [(t0 + 40.0, "done"), (t0 + 41.0, "ready")]
    p3b = {"weight_N": W, "F_min_N": F_MIN, "t_loop_start_s": t0, "departure": {"t_departure_s": t0 + 20.0},
           "P3-2_loc": {"limit_s": 2.9117}, "P3-6_ready": {"limit_s": 90.0},
           "P3-5_clearance_stroke": {"rut_clearance_min_after_first_ready_m": 0.05, "stroke_within": True},
           "checks": {"P3-4_verdict": "pass"}}
    res = {"p3b": p3b, "phases": [{"t_s": a, "phase": b} for a, b in phases],
           "events": [{"t_s": a, "name": b} for a, b in events],
           "controller_meta": {"two_pressure": {"fallback_lock_log": []}}}
    (d / "result.json").write_text(json.dumps(res), encoding="utf-8")
    return d


def _judge(mod, tmp_path, rows, extra=()):
    out = tmp_path / "out.json"
    argv = ["judge", "--out", str(out), "--rules-dir", str(_rules_dir(mod)), "--params", str(PARAMS)]
    for r in rows:
        argv += ["--row", str(r)]
    code = mod.main(argv + list(extra))
    return code, json.loads(out.read_text(encoding="utf-8")) if out.exists() else None


def test_scm_row_g6_pass_and_td_record(mod, tmp_path, capsys):
    d = _write_scm_row(tmp_path, sgs=False)
    code, doc = _judge(mod, tmp_path, [d])
    assert code == 0
    r = doc["rows"][0]
    assert r["row_id"] == "S-03" and r["grade"] == "pass", r.get("gates")
    dep = r["items"]["departure_t_D"]
    assert dep["t_departure_s"] == pytest.approx(25.0) and not dep["differs_from_runner"]
    assert doc["t_D_vs_runner_R6_B4"]["rows_differing"] == 0
    last = capsys.readouterr().out.strip().splitlines()
    assert last[-2] == "errors 0" and json.loads(last[-1])["exit"] == 0


def test_scm_row_sgs_stroke_limited_stop(mod, tmp_path):
    d = _write_scm_row(tmp_path, sgs=True)
    code, doc = _judge(mod, tmp_path, [d])
    r = doc["rows"][0]
    sgs = r["items"]["SGS_427_9_D-26"]
    assert sgs["applies"] and sgs["class"] == "stroke_limited_stop", sgs
    assert r["grade"] == "stroke_limited_stop"


def test_phase_time_base_mix_is_s11(mod, tmp_path):
    d = tmp_path / "L2b_row"
    d.mkdir()
    t0 = 3.0
    t = t0 + np.arange(1, 2001) * 1e-3
    np.savez(d / "pads.npz", t=t, crawler_normal_N=np.zeros(t.size), F_cyl_min_interval=np.full((t.size, 4), 6e4),
             N=np.full((t.size, 4), 1e4))
    np.savez(d / "r8_series.npz", t=t0 + np.arange(1, 21) * 0.1)
    res = {"settings": {"start_t_s": t0}, "phases": [[3.1, "check"], [4.5, "level"]], "event_t_s": None}  # absolute
    (d / "result.json").write_text(json.dumps(res), encoding="utf-8")
    code, doc = _judge(mod, tmp_path, [d])
    assert code == 1 and doc["origin_failed"] == ["L2b_row"]
    assert any("S-11" in p for p in doc["rows"][0]["origin_check_R5_B1"]["problems"])


def test_fallback_log_leg_without_event_is_s11(mod, tmp_path):
    d = _write_scm_row(tmp_path, sgs=False)
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    res["controller_meta"]["two_pressure"]["fallback_lock_log"] = [{"leg": "RR", "t_start_s": 5.0 + 1.0,
                                                                    "window_end_s": 6.5}]
    (d / "result.json").write_text(json.dumps(res), encoding="utf-8")
    code, doc = _judge(mod, tmp_path, [d])
    oc = doc["rows"][0]["origin_check_R5_B1"]
    assert code == 1 and any("S-11" in p for p in oc["problems"])
    assert oc["fallback"]["fallback_legs_R6_B7"] == ["RR"]


# ------------------------------------------------------------------------------------------------- seals / CLI
def test_seals(mod, tmp_path):
    src = _rules_dir(mod)
    for n in mod.RULES_SEALS:
        for f in (n, n.replace(".md", ".sha256")):
            shutil.copy2(src / f, tmp_path / f)
    assert mod.seal_check(tmp_path)["ok"]
    p = tmp_path / "v5_resume_4368_rules_rev6.md"
    p.write_bytes(p.read_bytes() + b"\n")
    s = mod.seal_check(tmp_path)
    assert not s["ok"] and not s["files"]["v5_resume_4368_rules_rev6.md"]["ok"]
    (tmp_path / "v5_resume_4368_rules_rev3.sha256").unlink()
    assert mod.main(["seals", "--rules-dir", str(tmp_path)]) == 2


def test_missing_input_exit_2(mod, tmp_path, capsys):
    code = mod.main(["judge", "--out", str(tmp_path / "o.json"), "--rules-dir", str(_rules_dir(mod)),
                     "--params", str(PARAMS), "--row", str(tmp_path / "nope")])
    assert code == 2
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["exit"] == 2


def test_assume_override_marks_deviation(mod, tmp_path):
    d = _write_scm_row(tmp_path, sgs=False)
    code, doc = _judge(mod, tmp_path, [d], ["--assume", "C-3=final"])
    assert doc["deviates_from_rev6"] == {"C-3": "final"}
    assert mod.main(["judge", "--out", str(tmp_path / "x.json"), "--row", str(d), "--assume", "C-3=bogus"]) == 2


def test_disclose_counts(mod):
    d = mod.disclose()
    assert len(d["pairs"]) == 3 and all("added" in p for p in d["pairs"]), d


def test_definitions_are_rev6(mod):
    assert mod.ASSUMPTIONS == {"C-1": "bracket_10hz", "C-2": "s8a2", "C-3": "first", "C-4": "count", "C-5": "10hz",
                               "C-6": "round", "C-7": "union", "C-8": "S-01,S-02,S-03,S-04", "C-9": "q14"}
    assert mod.D_NUMBERS["N-1"] == "D-26" and mod.D_NUMBERS["N-14"] == "D-39"


# ------------------------------------------------------------------------------------------------- G-S smoke (path)
GS_BATCH = MAIN_CHECKOUT / "07_results" / "S9" / "batch_V5-RESUME-K1-GS_20261113_020211"


@pytest.mark.skipif(not (GS_BATCH / "batch.json").exists(), reason="G-S batch not present")
def test_gs_batch_execution_path(mod, tmp_path):
    """Execution path only (no judgement): both rows load, the origin check runs on stored data."""
    out = tmp_path / "gs.json"
    code = mod.main(["judge", "--out", str(out), "--batch", str(GS_BATCH),
                     "--results-root", str(MAIN_CHECKOUT / "07_results"), "--rules-dir", str(_rules_dir(mod)),
                     "--params", str(PARAMS)])
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert code in (0, 1)
    assert {r["engine"] for r in doc["rows"]} == {"L2b", "L1R"}
    for r in doc["rows"]:
        assert r["origin_check_R5_B1"]["ok"] is True
    l1r = next(r for r in doc["rows"] if r["engine"] == "L1R")
    assert l1r["items"]["D8_t_lift_basis"]["basis"] == "bracket_10Hz"
