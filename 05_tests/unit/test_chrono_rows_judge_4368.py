"""436.8 Chrono path 1 aggregation new version (``04_scripts/02_chrono/chrono_rows_judge_4368.py``; rules rev5 R5-A1,
rev6 R6-A / R6-B / R6-C3).

Synthetic inputs only, plus an execution-path smoke on the stored G-S batch (no judgement, skipped when absent).
No Chrono run.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHRONO_SCRIPTS = PROJECT_ROOT / "04_scripts" / "02_chrono"
MAIN_CHECKOUT = Path(r"C:\workspace\outrigger_control")
PARAMS = PROJECT_ROOT / "02_params" / "rexome33.yaml"
GIT_AT_START = "4312b8e"
"""A judgement git_at_start for synthetic --row inputs (they have no batch.json entry: no_batch_entry, rev11 R11-4)."""


def _batch_head(batch: Path) -> str:
    """The first recorded code_at_launch head of a stored batch (its rows share one commit)."""
    doc = json.loads((batch / "batch.json").read_text(encoding="utf-8"))
    return next(c["code_at_launch"]["git"]["head"] for c in doc["cases"] if c.get("code_at_launch"))


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


RULES_REL = Path("06_analysis") / "02_control" / "verif_matrix"
RULES_DIRS = (PROJECT_ROOT / RULES_REL, MAIN_CHECKOUT / RULES_REL)
REV15_SEAL_COMMIT = "cc0d9b8"
"""rev15 seal commit S3: before the R3 merge the rev15 files are only in this commit's blobs."""
REV15_NAME = "v5_resume_4368_rules_rev15.md"
REV15_SHA256 = "0162561c3866412f06ef3be0b3a62434e4a9ba5a37c9003be4df2f373af545ef"
_BUILT_RULES: dict[str, Path] = {}


@pytest.fixture(scope="module", autouse=True)
def _rules_tmp(tmp_path_factory):
    _BUILT_RULES.clear()
    _BUILT_RULES["tmp"] = tmp_path_factory.mktemp("rules")


def _rules_files(mod) -> list[str]:
    return [f for n in mod.RULES_SEALS for f in (n, n.replace(".md", ".sha256"))]


def _blob(path: Path) -> bytes | None:
    """Bytes of ``path`` at the rev15 seal commit (None when the object is not in this repo)."""
    spec = f"{REV15_SEAL_COMMIT}:{path.as_posix()}"
    done = subprocess.run(["git", "-C", str(PROJECT_ROOT), "cat-file", "blob", spec],
                          capture_output=True, check=False)
    return done.stdout if done.returncode == 0 else None


def _rules_dir(mod) -> Path:
    """A folder with every sealed rules file: the checkout's own, else one built from the checkout
    files plus the seal commit blobs (rev15 before the R3 merge)."""
    for d in RULES_DIRS:
        if all((d / n).exists() for n in _rules_files(mod)):
            return d
    built = _BUILT_RULES["tmp"]
    if not all((built / n).exists() for n in _rules_files(mod)):
        for name in _rules_files(mod):
            data = next(((d / name).read_bytes() for d in RULES_DIRS if (d / name).exists()),
                        None) or _blob(RULES_REL / name)
            if data is None:
                pytest.skip(f"{name} not found (checkout or {REV15_SEAL_COMMIT})")
            (built / name).write_bytes(data)
    return built


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
           "controller_meta": {"two_pressure": {"fallback_lock_log": []}},
           # rev9 R9-1: a closed-loop row carries a true controller-tag check (V0 tag: no J-P3)
           "args": {"expect_controller": "final_C4G2_LAS_K1"},
           "c2_setup": {"expect_controller": {"name": "final_C4G2_LAS_K1", "ok": True}}}
    (d / "result.json").write_text(json.dumps(res), encoding="utf-8")
    return d


def _judge(mod, tmp_path, rows, extra=()):
    out = tmp_path / "out.json"
    argv = ["judge", "--git-at-start", GIT_AT_START, "--out", str(out), "--rules-dir", str(_rules_dir(mod)), "--params", str(PARAMS)]
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
    # z4372: the engine comes from the record
    res = {"settings": {"start_t_s": t0, "s8": {"engine": "L2b_NSC"}},
           "phases": [[3.1, "check"], [4.5, "level"]], "event_t_s": None}  # absolute
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


# ------------------------------------------------------------------------------------ engine (z4372)
def _write_pads_row(d: Path, *, engine: str | None, crawler_1ms: bool,
                    floor_normal: list[float] | None = None, record: bool = True) -> Path:
    """A run_S8C-like row; ``crawler_1ms`` False = a V0 L2b row (``law_locked``, no
    ``crawler_normal_N``). ``F_crawler`` z > 0 until 15.1 s, x > 0 until 16.1 s (so a tilted
    floor normal moves the 10 Hz t_lift); ``floor_normal`` None = no ``floor_plane`` record."""
    d.mkdir(parents=True)
    (d / "record").mkdir()
    t0 = 3.0
    t = t0 + np.arange(1, 20001) * 1e-3
    pads = {"t": t, "F_cyl_min_interval": np.full((t.size, 4), 6e4),
            "N": np.full((t.size, 4), 1e4), "law_locked": np.ones((t.size, 4), dtype=np.int8)}
    if crawler_1ms:
        pads["crawler_normal_N"] = np.where(t < t0 + 10.0005, 5000.0, 0.0)
    np.savez(d / "pads.npz", **pads)
    tr = t0 + np.arange(1, 200) * 0.1
    f_crawler = np.zeros((tr.size, 3))
    f_crawler[:, 0] = np.where(tr < t0 + 13.05, 5000.0, 0.0)
    f_crawler[:, 2] = np.where(tr < t0 + 12.05, 5000.0, 0.0)
    if record:
        np.savez(d / "record" / "record.npz", t=tr, F_crawler=f_crawler)
    np.savez(d / "r8_series.npz", t=tr)
    settings: dict = {"start_t_s": t0}
    if engine is not None:
        settings["s8"] = {"engine": engine}
    # rev9 R9-1: the row tag and its true check (V0 tag, so no J-P3)
    res = {"settings": settings, "phases": [[0.1, "check"], [5.0, "touch"], [8.0, "level"]],
           "event_t_s": None, "args": {"expect_controller": "final_C4G2_LAS_K1"},
           "expect_controller": {"name": "final_C4G2_LAS_K1", "ok": True}}
    if floor_normal is not None:
        res["floor_plane"] = {"normal_world": floor_normal}
    (d / "result.json").write_text(json.dumps(res), encoding="utf-8")
    return d


def test_engine_from_records_not_from_pads_keys(mod, tmp_path):
    """z4372: a V0 L2b row (no crawler_normal_N) is L2b by its records; batch.json r4368.engine
    counts too."""
    v0 = _write_pads_row(tmp_path / "v0", engine="L2b_NSC", crawler_1ms=False)
    row = mod.load_row(v0)
    assert row["engine"] == "L2b"
    assert row["engine_record"]["sources"] == {"result.json settings.s8.engine": "L2b_NSC"}
    l1r = _write_pads_row(tmp_path / "l1r", engine=None, crawler_1ms=False)
    row = mod.load_row(l1r, {"case": "X", "r4368": {"engine": "L1R"}})
    assert row["engine"] == "L1R"
    assert row["engine_record"]["sources"] == {"batch.json r4368.engine": "L1R"}
    # a 1 ms crawler array does not make a recorded L1-R row L2b
    assert mod.load_row(_write_pads_row(tmp_path / "l1r1ms", engine=None, crawler_1ms=True),
                        {"r4368": {"engine": "L1R"}})["engine"] == "L1R"


def test_engine_record_missing_unknown_or_conflicting_is_input_error(mod, tmp_path):
    bare = _write_pads_row(tmp_path / "bare", engine=None, crawler_1ms=True)
    with pytest.raises(mod.InputError, match="engine record"):
        mod.load_row(bare)
    with pytest.raises(mod.InputError, match="unknown engine"):
        mod.load_row(bare, {"r4368": {"engine": "L2b_SMC"}})
    v0 = _write_pads_row(tmp_path / "v0", engine="L2b_NSC", crawler_1ms=False)
    with pytest.raises(mod.InputError, match="disagree"):
        mod.load_row(v0, {"r4368": {"engine": "L1R"}})
    with pytest.raises(mod.InputError, match="does not fit"):
        mod.load_row(bare, {"r4368": {"engine": "SCM"}})
    scm = _write_scm_row(tmp_path / "scm", sgs=False)
    assert mod.load_row(scm, {"r4368": {"engine": "SCM"}})["engine"] == "SCM"
    with pytest.raises(mod.InputError, match="does not fit"):
        mod.load_row(scm, {"r4368": {"engine": "L2b_NSC"}})


def test_v0_l2b_row_d29_by_10hz_bracket_r15_3(mod, tmp_path):
    """Rev15 R15-3: a V0 L2b row (no 1 ms crawler normal) takes the R6-B1 10 Hz bracket t_b; C1 and
    Q-14 are computed from it; a 1 ms row keeps the 1 ms t_lift."""
    v0 = _write_pads_row(tmp_path / "E_G4_Fs4_V0", engine="L2b_NSC", crawler_1ms=False,
                         floor_normal=[0.0, 0.0, 2.0])  # not unit length: normalised
    vb = _write_pads_row(tmp_path / "E_G4_Fs4", engine="L2b_NSC", crawler_1ms=True,
                         floor_normal=[0.0, 0.0, 1.0])
    code, doc = _judge(mod, tmp_path, [v0, vb])
    assert code == 0, doc["stops"]
    rows = {r["case"]: r for r in doc["rows"]}
    items = rows["E_G4_Fs4_V0"]["items"]
    basis = items["D8_t_lift_basis"]
    assert items["D8_t_lift_s_D-29_D-30"] == pytest.approx(15.1)
    assert basis["basis"] == "bracket_10Hz" and basis["rule"] == mod.R15_3_RULE
    assert basis["t_a_s"] == pytest.approx(15.0) and basis["t_b_s"] == pytest.approx(15.1)
    assert basis["normal"] == "result.json floor_plane.normal_world"
    assert items["C1_R40"]["status"] == "judged" and items["C1_R40"]["verdict"] == "pass"
    assert items["C1_R40"]["t_lift_s"] == pytest.approx(15.1)
    q14 = items["D8_no_pad_lift_Q-14"]
    assert q14["t_from_s"] == pytest.approx(15.1) and q14["lifted"] is False
    sus = items["D8_t_lift_sus_R21_1"]  # rev21 R21-1 record of the V0 row
    assert sus["t_lift_sus_10Hz_s"] == pytest.approx(15.1) and sus["differs_from_t_b"] is False
    ok = rows["E_G4_Fs4"]["items"]
    assert ok["D8_t_lift_basis"] == "1ms_sus"  # rev21 R21-1
    assert ok["D8_t_lift_s_D-29_D-30"] == pytest.approx(13.001)
    assert ok["D8_t_lift_sus_R21_1"]["t_lift_first_le0_rev6_record_s"] == pytest.approx(13.001)
    assert doc["l2b_bracket_rows_R15_3"] == ["E_G4_Fs4_V0"]


# ------------------------------------------------------------------------------------ rev21 R21-1 t_lift,sus
SUS_PHASES = [(0.0, "idle"), (1.0, "check"), (2.0, "touch"), (3.0, "level")]
SUS_THRESHOLD = 0.01 * 376.7e3


def _sus(mod, cn):
    t = np.round(np.arange(0.0, 10.0, 0.001), 6)
    return mod.sustained_lift_time(t, np.asarray(cn(t), float), SUS_PHASES, SUS_THRESHOLD)


def test_t_lift_sus_held_to_the_end(mod):
    assert _sus(mod, lambda t: np.where(t < 5.0, 1e5, 3000.0)) == pytest.approx(5.0)
    assert mod.SUSTAINED_LIFT_FRACTION * mod.SUSTAINED_LIFT_WEIGHT_N == pytest.approx(3767.0)


def test_t_lift_sus_after_a_recontact(mod):
    """A dip to 0 at 4 s that recontacts above 0.01 W at 6 s does not count; the last stretch from
    7 s does (the rev6 first-sample rule would give 4 s)."""
    def cn(t):
        return np.where(t < 4.0, 1e5, np.where(t < 6.0, 0.0, np.where(t < 7.0, 2e4, 0.0)))
    assert _sus(mod, cn) == pytest.approx(7.0)


def test_t_lift_sus_none_when_not_held(mod):
    assert _sus(mod, lambda t: np.where(t < 9.999, 0.0, 1e4)) is None
    assert _sus(mod, lambda t: np.full(t.size, 1e5)) is None


def test_t_lift_sus_skips_pre_lift_phases(mod):
    """Below 0.01 W from 1.5 s (in CHECK / TOUCH) to the end: t_lift,sus = first LEVEL sample."""
    assert _sus(mod, lambda t: np.where(t < 1.5, 1e5, 0.0)) == pytest.approx(3.0)


def test_v0_counterpart_differs_from_t_b(mod, tmp_path):
    """R21-1 V0 record: z normal 2 kN (> 0, < 0.01 W) from 13.05 s, 0 from 15.05 s: t_b = 15.1 s,
    the 10 Hz t_lift,sus counterpart = 13.1 s, flagged as differing."""
    d = _write_pads_row(tmp_path / "E_G4_Fs4_V0", engine="L2b_NSC", crawler_1ms=False,
                        floor_normal=[0.0, 0.0, 1.0])
    rec = dict(np.load(d / "record" / "record.npz"))
    tr = rec["t"]
    rec["F_crawler"][:, 0] = 0.0
    rec["F_crawler"][:, 2] = np.where(tr < 13.05, 5e4, np.where(tr < 15.05, 2000.0, 0.0))
    np.savez(d / "record" / "record.npz", **rec)
    code, doc = _judge(mod, tmp_path, [d])
    items = doc["rows"][0]["items"]
    assert items["D8_t_lift_s_D-29_D-30"] == pytest.approx(15.1)
    sus = items["D8_t_lift_sus_R21_1"]
    assert sus["t_lift_sus_10Hz_s"] == pytest.approx(13.1) and sus["differs_from_t_b"] is True


def test_l2b_row_without_t_lift_sus_is_not_judgeable(mod, tmp_path):
    d = _write_pads_row(tmp_path / "E_G4_Fs4", engine="L2b_NSC", crawler_1ms=True,
                        floor_normal=[0.0, 0.0, 1.0])
    pads = dict(np.load(d / "pads.npz"))
    pads["crawler_normal_N"][-5:] = 1e4  # recontact at the record end
    np.savez(d / "pads.npz", **pads)
    _, doc = _judge(mod, tmp_path, [d])
    items = doc["rows"][0]["items"]
    assert items["D8_t_lift_s_D-29_D-30"] is None
    assert items["D8_t_lift_sus_R21_1"]["status"] == "not_judgeable"
    assert items["C1_R40"]["status"] == "not_judgeable"


def test_v0_l2b_bracket_uses_the_floor_normal(mod, tmp_path):
    """R15-3 projects F_crawler on the floor normal: x > 0 lasts 1 s longer than z, so a 45-degree
    normal moves t_b from 15.1 s to 16.1 s."""
    d = _write_pads_row(tmp_path / "tilt", engine="L2b_NSC", crawler_1ms=False,
                        floor_normal=[1.0, 0.0, 1.0])
    t_lift, basis = mod.v0_l2b_bracket_lift(mod.load_row(d))
    assert t_lift == pytest.approx(16.1) and basis["t_a_s"] == pytest.approx(16.0)


def test_v0_l2b_bracket_without_inputs_is_not_judgeable(mod, tmp_path):
    """R15-3 inputs missing (floor normal; record.npz): t_lift not judgeable, inputs named."""
    no_floor = mod.load_row(_write_pads_row(tmp_path / "nf", engine="L2b_NSC", crawler_1ms=False))
    t_lift, basis = mod.v0_l2b_bracket_lift(no_floor)
    assert t_lift is None and basis["status"] == "not_judgeable"
    assert basis["missing_inputs"] == ["result.json floor_plane.normal_world"]
    no_rec = mod.load_row(_write_pads_row(tmp_path / "nr", engine="L2b_NSC", crawler_1ms=False,
                                          floor_normal=[0.0, 0.0, 1.0], record=False))
    t_lift, basis = mod.v0_l2b_bracket_lift(no_rec)
    assert t_lift is None
    assert basis["missing_inputs"] == ["record/record.npz F_crawler", "record/record.npz t"]
    code, doc = _judge(mod, tmp_path, [tmp_path / "nf"])
    items = doc["rows"][0]["items"]
    assert code == 0 and items["C1_R40"]["status"] == "not_judgeable"
    assert items["D8_no_pad_lift_Q-14"]["status"] == "not_judgeable"
    assert doc["l2b_bracket_rows_R15_3"] == ["nf"]


@pytest.mark.parametrize(("change", "problem"), [
    ("F_crawler_2col", "F_crawler shape"),
    ("t_short", "record/record.npz t shape"),
    ("zero_normal", "floor_plane.normal_world"),
])
def test_v0_l2b_bracket_wrong_input_form_is_not_judgeable(mod, tmp_path, change, problem):
    """Rev15 R15-3: F_crawler not [N, 3], t of another length or a zero normal = not judgeable."""
    normal = [0.0, 0.0, 0.0] if change == "zero_normal" else [0.0, 0.0, 1.0]
    d = _write_pads_row(tmp_path / change, engine="L2b_NSC", crawler_1ms=False,
                        floor_normal=normal)
    rec = dict(np.load(d / "record" / "record.npz"))
    if change == "F_crawler_2col":
        rec["F_crawler"] = rec["F_crawler"][:, :2]
    elif change == "t_short":
        rec["t"] = rec["t"][:-1]
    np.savez(d / "record" / "record.npz", **rec)
    t_lift, basis = mod.v0_l2b_bracket_lift(mod.load_row(d))
    assert t_lift is None and basis["status"] == "not_judgeable"
    assert len(basis["form_problems"]) == 1 and problem in basis["form_problems"][0]


def test_v0_l2b_bracket_basis_names_its_inputs(mod, tmp_path):
    d = _write_pads_row(tmp_path / "v0", engine="L2b_NSC", crawler_1ms=False,
                        floor_normal=[0.0, 0.0, 1.0])
    _, basis = mod.v0_l2b_bracket_lift(mod.load_row(d))
    assert basis["inputs"] == list(mod.R15_3_SOURCES)


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


def test_rev15_in_the_seal_list(mod):
    """Rev15 R15-7: the path 1 Chrono judge checks rev15 (rev13 / rev14 stay outside, R14-7)."""
    assert mod.RULES_SEALS[REV15_NAME] == REV15_SHA256
    assert "v5_resume_4368_rules_rev13.md" not in mod.RULES_SEALS
    assert "v5_resume_4368_rules_rev14.md" not in mod.RULES_SEALS
    assert "rev15" in mod.RULES_DESCRIPTION and "R15-3" in mod.RULES_DESCRIPTION


REV16_18_SHA256 = {
    "v5_resume_4368_rules_rev16.md": "b38991943a565a020488d1046dd6e0b5c71276cf925715fa5ba844d8819d0683",
    "v5_resume_4368_rules_rev17.md": "9400660e2f228c3bdfaf26b1eb36cf08a753e7ebc49fbcdedc4a8ab4e0b92422",
    "v5_resume_4368_rules_rev18.md": "3693a69c3f04eb6c5b26556ec5997d081e38f8f6fa6a581aee66ba512d122a9e",
    "v5_resume_4368_rules_rev19.md": "7f87b8bb091d23c1bdcd2bf356b732a77bea12c4cfc4853d0ea58f7d239c92b2",
    "v5_resume_4368_rules_rev20.md": "615a8fbd82f4ef93f1ca76b3fb4d5c24a2e602e63a997c7c56119fcc73fb5531",
    "v5_resume_4368_rules_rev21.md": "ecd709495f203eae1769ae42e67b5ae5bf2fb457146b558c12e46d636ed03f9a",
    "v5_resume_4368_rules_rev22.md": "a48a81f9a71091aab40f643d48ae65ba559a5c0c629e02ef3145745a095f9328",
    "v5_resume_4368_rules_rev23.md": "fa72e1726f87f686093e36f2f3f489d5b135df6392de6aae7fe91b8739b56f97",
    "v5_resume_4368_rules_rev24.md": "f475cf77bc610802aa36026394cbe8dbae74745c8889ac203b53a6430e1e1e15",
}
"""Rev18 R18-1 2 .. rev24 R24-3: rev16 .. rev24 in the Chrono judge seal list (sha of each
``.sha256``)."""


def test_rev16_to_rev18_in_the_seal_list(mod):
    """Rev24 R24-3: the path 1 Chrono judge checks rev16 .. rev24; rev13 / rev14 stay out."""
    for name, sha in REV16_18_SHA256.items():
        assert mod.RULES_SEALS[name] == sha
    assert "rev15 .. rev24" in mod.RULES_DESCRIPTION and "R24-3" in mod.RULES_DESCRIPTION


def test_seals_command_checks_rev16_to_rev18(mod, capsys):
    """``seals`` on the checkout's rules folder: rev16 .. rev18 match their ``.sha256``."""
    rules_dir = PROJECT_ROOT / RULES_REL
    if not all((rules_dir / n).exists() for n in _rules_files(mod)):
        pytest.skip("rev16 .. rev18 not in this checkout")
    capsys.readouterr()
    assert mod.main(["seals", "--rules-dir", str(rules_dir)]) == 0
    files = json.loads(capsys.readouterr().out.strip().splitlines()[-1])["files"]
    for name, sha in REV16_18_SHA256.items():
        assert files[name] == {"sha256": sha, "sealed": sha, "tool": sha, "ok": True}


def test_seals_command_checks_rev15(mod, tmp_path, capsys):
    """``seals`` on the sealed files (rev15 from the seal commit blob before R3): exit 0 with rev15
    matching; a changed rev15 is exit 1, a rev15 without its .sha256 is exit 2 (original 8.2
    S-1)."""
    src = _rules_dir(mod)
    for name in _rules_files(mod):
        shutil.copy2(src / name, tmp_path / name)
    capsys.readouterr()
    assert mod.main(["seals", "--rules-dir", str(tmp_path)]) == 0
    entry = json.loads(capsys.readouterr().out.strip().splitlines()[-1])["files"][REV15_NAME]
    assert entry == {"sha256": REV15_SHA256, "sealed": REV15_SHA256, "tool": REV15_SHA256,
                     "ok": True}
    rev15 = tmp_path / REV15_NAME
    rev15.write_bytes(rev15.read_bytes() + b"\n")
    assert mod.main(["seals", "--rules-dir", str(tmp_path)]) == 1
    assert mod.seal_check(tmp_path)["files"][REV15_NAME]["ok"] is False
    (tmp_path / REV15_NAME.replace(".md", ".sha256")).unlink()
    assert mod.main(["seals", "--rules-dir", str(tmp_path)]) == 2
    assert mod.seal_check(tmp_path)["missing"] == [REV15_NAME]


def test_missing_input_exit_2(mod, tmp_path, capsys):
    code = mod.main(["judge", "--git-at-start", GIT_AT_START, "--out", str(tmp_path / "o.json"), "--rules-dir", str(_rules_dir(mod)),
                     "--params", str(PARAMS), "--row", str(tmp_path / "nope")])
    assert code == 2
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["exit"] == 2


def test_assume_override_marks_deviation(mod, tmp_path):
    d = _write_scm_row(tmp_path, sgs=False)
    code, doc = _judge(mod, tmp_path, [d], ["--assume", "C-3=final"])
    assert doc["deviates_from_rev6"] == {"C-3": "final"}
    assert mod.main(["judge", "--git-at-start", GIT_AT_START, "--out", str(tmp_path / "x.json"), "--row", str(d), "--assume", "C-3=bogus"]) == 2


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
    code = mod.main(["judge", "--git-at-start", _batch_head(GS_BATCH), "--out", str(out), "--batch", str(GS_BATCH),
                     "--results-root", str(MAIN_CHECKOUT / "07_results"), "--rules-dir", str(_rules_dir(mod)),
                     "--params", str(PARAMS)])
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert code in (0, 1)
    assert {r["engine"] for r in doc["rows"]} == {"L2b", "L1R"}
    for r in doc["rows"]:
        assert r["origin_check_R5_B1"]["ok"] is True
    l1r = next(r for r in doc["rows"] if r["engine"] == "L1R")
    assert l1r["items"]["D8_t_lift_basis"]["basis"] == "bracket_10Hz"


# ------------------------------------------------------------------------------------------------- row folders (v2)
def _rigid_batch(tmp_path: Path, *, log_line: bool, folder_stamps: list[str], script="run_S6C.py"):
    """A batch with one run_S6C (or run_S8C) row whose runner folder(s) live under ``<results>/S6`` (``S8``)."""
    results = tmp_path / "07_results"
    batch = results / "S9" / "batch_X_20261113_082117"
    batch.mkdir(parents=True)
    tag, only, case = "r4368gs_D1C1_top_flat_crx3", "D1C1_top_flat_crx3", "GS_D1C1_top_flat_crx3"
    dirs = []
    for st in folder_stamps:
        sub = (results / "S6" / f"bundleC_d1c1_{tag}_L1R_{st}") if script == "run_S6C.py" else \
            (results / "S8" / f"{tag}_{st}")
        (sub / only).mkdir(parents=True)
        (sub / only / "result.json").write_text("{}", encoding="utf-8")
        dirs.append(sub)
    argv = ["python.exe", f"C:/x/04_scripts/02_chrono/{script}", "run", "--only", only, "--tag", tag]
    (batch / "batch.json").write_text(json.dumps({"cases": [{"case": case, "argv": argv, "wall_s": 228.6,
                                                             "criteria_id": "C-1"}]}), encoding="utf-8")
    (batch / "progress.log").write_text(f"START {case} 2026-11-13T08:21:17 pid=1\n"
                                        f"END {case} 2026-11-13T08:25:06 rc=0 wall_s=229\n", encoding="utf-8")
    log = f"{only}: ok 226.6s\n"
    if log_line:
        log += f"batch wall 226.8 s, jobs 1 -> {dirs[0]}\n"
    (batch / f"{case}.log").write_text(log, encoding="utf-8")
    return batch, results, dirs, only


def test_row_dir_from_case_log_one_second_late(mod, tmp_path):
    batch, results, dirs, only = _rigid_batch(tmp_path, log_line=True, folder_stamps=["20261113_082118"])
    rows = mod.batch_rows(batch, results)
    assert rows[0][0] == dirs[0] / only
    assert rows[0][1]["_row_dir"]["source"] == "case_log"


def test_row_dir_log_rule_matches_s8c_case_check():
    s9b = _import("s9_batch")
    mod = _import("chrono_rows_judge_4368")
    for text in ("a\nbatch wall 520.2 s -> C:\\r\\S8\\t_20261113_082117\n",
                 "x: ok 1s\nbatch wall 226.8 s, jobs 1 -> C:\\r\\S6\\b_20261113_082118\nbatch wall 1 s -> D:\\z\n",
                 "no line\n"):
        assert mod.runner_log_dir(text) == s9b.s8c_case_check(text, "x")["batch_dir"]


def test_row_dir_logged_folder_without_result_is_input_error(mod, tmp_path):
    batch, results, dirs, only = _rigid_batch(tmp_path, log_line=True, folder_stamps=["20261113_082118"])
    (dirs[0] / only / "result.json").unlink()
    with pytest.raises(mod.InputError, match="case log names"):
        mod.batch_rows(batch, results)


def test_row_dir_logged_in_removed_worktree_is_relocated(mod, tmp_path):
    batch, results, dirs, only = _rigid_batch(tmp_path, log_line=False, folder_stamps=["20261113_082118"])
    gone = Path("C:/gone/worktree/07_results/S6") / dirs[0].name
    log = batch / "GS_D1C1_top_flat_crx3.log"
    log.write_text(log.read_text(encoding="utf-8") + f"batch wall 1 s -> {gone}\n", encoding="utf-8")
    rows = mod.batch_rows(batch, results)
    assert rows[0][0] == dirs[0] / only and rows[0][1]["_row_dir"]["source"] == "case_log_relocated"


@pytest.mark.parametrize("script", ["run_S6C.py", "run_S8C.py"])
def test_row_dir_time_window_fallback(mod, tmp_path, script):
    batch, results, dirs, only = _rigid_batch(tmp_path, log_line=False, folder_stamps=["20261113_082118"],
                                              script=script)
    rows = mod.batch_rows(batch, results)
    assert rows[0][0] == dirs[0] / only and rows[0][1]["_row_dir"]["source"] == "time_window"


def test_row_dir_time_window_none_or_two_is_input_error(mod, tmp_path, capsys):
    batch, results, _, _ = _rigid_batch(tmp_path / "a", log_line=False, folder_stamps=["20261113_090000"])
    with pytest.raises(mod.InputError, match="0 runner folder"):
        mod.batch_rows(batch, results)
    batch, results, _, _ = _rigid_batch(tmp_path / "b", log_line=False,
                                        folder_stamps=["20261113_082118", "20261113_082300"])
    with pytest.raises(mod.InputError, match="2 runner folder"):
        mod.batch_rows(batch, results)
    code = mod.main(["judge", "--git-at-start", GIT_AT_START, "--out", str(tmp_path / "o.json"), "--rules-dir", str(_rules_dir(mod)),
                     "--params", str(PARAMS), "--batch", str(batch), "--results-root", str(results)])
    assert code == 2 and json.loads(capsys.readouterr().out.strip().splitlines()[-1])["exit"] == 2


# ------------------------------------------------------------------------------------------------- open-loop skip (v2)
def _openloop_row(tmp_path: Path) -> Path:
    d = tmp_path / "P3a_G1_B_VB_prop"
    d.mkdir()
    np.savez(d / "series.npz", t=np.arange(3.0))
    np.savez(d / "flow_series.npz", t=np.arange(3.0))
    (d / "result.json").write_text(json.dumps({"action": "machine", "p3a": {"checks": {}}}), encoding="utf-8")
    return d


def test_openloop_row_is_skipped_and_listed(mod, tmp_path, capsys):
    d = _openloop_row(tmp_path)
    scm = _write_scm_row(tmp_path, sgs=False)
    code, doc = _judge(mod, tmp_path, [d, scm])
    assert code == 0 and len(doc["rows"]) == 1
    sk = doc["skipped_rows"]
    assert [s["case"] for s in sk] == ["P3a_G1_B_VB_prop"] and sk[0]["skipped"] == "openloop_not_judged_here"
    assert set(sk[0]["inputs"]) == {"series.npz", "flow_series.npz"} and "9.1" in sk[0]["rule"]
    last = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert last["skipped"] == {"P3a_G1_B_VB_prop": "openloop_not_judged_here"}


GS_BATCH_2 = MAIN_CHECKOUT / "07_results" / "S9" / "batch_V5-RESUME-K1-GS_20261113_082117"


@pytest.mark.skipif(not (GS_BATCH_2 / "batch.json").exists(), reason="G-S batch 082117 not present")
def test_gs_batch_082117_execution_path(mod, tmp_path):
    """Execution path only (G-S values are not judged): the L1-R folder 1 s after the batch stamp comes from
    the case log, the open-loop row is listed as skipped. Rev8 R8-3 / R8-4: this batch predates the SCM
    ``law_locked`` record, so its three C-5 SCM rows stop on J11 (rc 1). Rev11 R11-4: it also predates the
    open-loop ``code_at_launch`` record, so the C-6 row is S-12; every other row has the batch commit."""
    out = tmp_path / "gs2.json"
    code = mod.main(["judge", "--git-at-start", _batch_head(GS_BATCH_2), "--out", str(out), "--batch", str(GS_BATCH_2),
                     "--results-root", str(MAIN_CHECKOUT / "07_results"), "--rules-dir", str(_rules_dir(mod)),
                     "--params", str(PARAMS)])
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert code == 1
    c5_scm = sorted(r["case"] for r in doc["rows"] if r["criteria_id"] == "C-5" and r["engine"] == "SCM")
    j11 = [s for s in doc["stops"] if s["reason"].startswith("J11 not judgeable")]
    s12 = [s for s in doc["stops"] if s["reason"].startswith("S-12")]
    assert len(c5_scm) == 3 and sorted(s["case"] for s in j11) == c5_scm
    assert [s["case"] for s in s12] == ["GS_P3a_G1_B_VB_prop_lift10"] and len(doc["stops"]) == 4
    assert doc["commit_identity_R11_4"]["s12_rows"] == ["GS_P3a_G1_B_VB_prop_lift10"]
    assert doc["rev8_counts"]["S-2_rows"] == 0
    assert [s["criteria_id"] for s in doc["skipped_rows"]] == ["C-6"]
    l1r = next(r for r in doc["rows"] if r["engine"] == "L1R")
    assert l1r["row_dir"]["source"] == "case_log" and l1r["dir"].endswith("_082118\\D1C1_top_flat_crx3")


# ------------------------------------------------------------- rules rev24 CD-3 / CD-5
HEAD_AREA_M2 = [0.01] * 4
"""Head area of the synthetic CD-3 rows: p [bar] = F_cyl [N] / 1000."""
T0_S = 2.0
EVENT_T_S = 10.0
"""``event_t_s`` (relative to ``settings.start_t_s`` = :data:`T0_S`)."""


def floor_result(**over) -> dict:
    return {"settings": {"event": "drop_RR_30", "level": "top", "start_t_s": T0_S},
            "event_t_s": EVENT_T_S, **over}


def fast_result(*, depth: float = 0.05, ramp: float | None = 0.5, event_t_s=EVENT_T_S) -> dict:
    return {"settings": {"event": None, "level": "top", "start_t_s": T0_S}, "event_t_s": event_t_s,
            "event": {"spec": {"kind": "settle", "leg": "FL", "depth_m": depth, "ramp_s": ramp}}}


def cd3_row(result: dict, *, rr_lift: tuple[float, float] | None = None, airborne: bool = True,
            record_p_bar: float = 100.0) -> dict:
    """A synthetic L2b row: 1 ms pads (RR pad normal <= 0 inside ``rr_lift``, relative times),
    10 Hz record rows extending at ``record_p_bar`` on every leg."""
    t = np.round(np.arange(0.0, 30.0, 0.001), 6) + T0_S
    n = np.full((t.size, 4), 1e4)
    if rr_lift is not None:
        lifted = (t - T0_S >= rr_lift[0]) & (t - T0_S < rr_lift[1])
        n[lifted, 3] = 0.0
    pads = {"t": t, "N": n}
    if airborne:
        pads.update(airborne=np.zeros((t.size, 4), bool), ball_centre_world=np.zeros((t.size, 4, 3)))
    tr = np.round(np.arange(0.0, 30.0, 0.1), 6) + T0_S
    rec = {"t": tr, "u_applied": np.full((tr.size, 4), 1e-3),
           "F_cyl": np.full((tr.size, 4), record_p_bar * 1e3)}
    return {"result": result, "pads": pads, "record": rec, "t0": T0_S, "name": "inner_case",
            "phases": [(T0_S + 1.0, "level"), (T0_S + 5.0, "ready")], "engine": "L2b"}


@pytest.mark.parametrize(("result", "kind"), [
    (floor_result(), "floor"),
    (fast_result(), "fast"),                                   # 100 mm/s > v_max
    (fast_result(ramp=0.0), "fast"),                           # zero ramp: infinitely fast
    (fast_result(ramp=None), "fast"),
    (fast_result(depth=0.0115, ramp=2.0), None),               # E_G4: 5.75 mm/s, event-free
    (fast_result(event_t_s=None), None),                       # null event_t_s: not fast
    ({"settings": {"event": "settle_RR"}, "event_t_s": EVENT_T_S}, None),  # event_t_s alone
])
def test_cd3_event_row_test(mod, result, kind):
    """Rules rev24 CD-3: the closed test; a non-null event_t_s never makes an event row alone."""
    assert mod.event_row_kind(result)["kind"] == kind


@pytest.mark.parametrize(("rr_lift", "end_rel"), [
    ((10.5, 11.0), 11.0 + 0.82),        # last re-contact 11.0 s + T_3
    (None, EVENT_T_S + 0.82),           # no lift: t_event + T_3
    ((10.5, 40.0), EVENT_T_S + 5.0),    # lifted to the record end: t_event + 5 s
    ((10.5, 14.9), EVENT_T_S + 5.0),    # re-contact + T_3 past the cap
])
def test_cd3_floor_window(mod, rr_lift, end_rel):
    row = cd3_row(floor_result(), rr_lift=rr_lift)
    window = mod.event_window(row, mod.event_row_kind(row["result"]))
    assert window["end_rel_s"] == pytest.approx(end_rel)
    assert window["start_abs_s"] == pytest.approx(EVENT_T_S + T0_S)


def test_cd3_floor_window_without_event_t_s(mod):
    """A floor event without event_t_s starts at the first READY + 5 s."""
    row = cd3_row(floor_result(event_t_s=None))
    window = mod.event_window(row, mod.event_row_kind(row["result"]))
    assert window["t_event_rel_s"] == pytest.approx(5.0 + 5.0)
    assert window["t_event_source"].startswith("first READY")


def test_cd3_fast_window(mod):
    """Fast settlement: the U-S8-32 split (no event leg lifted: t_event + T_3); without the
    airborne record W ends at t_event + 5 s."""
    row = cd3_row(fast_result())
    window = mod.event_window(row, mod.event_row_kind(row["result"]))
    assert window["end_rel_s"] == pytest.approx(EVENT_T_S + 0.82)
    row = cd3_row(fast_result(), airborne=False)
    window = mod.event_window(row, mod.event_row_kind(row["result"]))
    assert window["end_rel_s"] == pytest.approx(EVENT_T_S + 5.0)
    assert "no_airborne_record" in window["notes"]


def test_cd3_items_inside_and_outside(mod):
    """Outside W: extension samples only (<= 180 bar), retraction recorded; inside W: any state
    <= 350 bar; saturation counts outside-W extension samples >= 210 bar."""
    row = cd3_row(floor_result())
    rec = row["record"]
    t = rec["t"]
    start, end = EVENT_T_S + T0_S, EVENT_T_S + T0_S + 1.0
    inside = (t >= start - 1e-9) & (t <= end + 1e-9)
    rec["F_cyl"][inside, 2] = 300e3                     # 300 bar inside W: within 350
    rec["u_applied"][inside, 2] = 0.0                   # locked
    late = t > 25.0 + T0_S
    rec["u_applied"][late, 0] = -1e-3                   # retraction outside W at 250 bar: report
    rec["F_cyl"][late, 0] = 250e3
    items = mod.event_pressure_items(rec, HEAD_AREA_M2, start, end)
    assert items["outside_extension"]["within"] is True
    assert items["outside_extension"]["max_bar"] == pytest.approx(100.0)
    assert items["outside_retraction_record"]["max_bar"] == pytest.approx(250.0)
    assert items["inside"]["max_bar"] == pytest.approx(300.0) and items["inside"]["state"] == "locked"
    assert items["inside"]["within"] is True and items["saturated_samples"] == 0
    rec["F_cyl"][inside, 2] = 360e3
    rec["F_cyl"][~inside & ~late, 1] = 215e3            # extension outside W >= 210 bar
    items = mod.event_pressure_items(rec, HEAD_AREA_M2, start, end)
    assert items["inside"]["within"] is False and items["outside_extension"]["within"] is False
    assert items["saturated_samples"] > 0 and items["saturation_within"] is False


def write_runner_window(tmp_path: Path, end_rel: float, *, case: str = "E_X") -> Path:
    folder = tmp_path / "runner_judge"
    folder.mkdir(exist_ok=True)
    (folder / f"C5_{case}.verify_S8C.json").write_text(json.dumps({"metrics": [
        {"case": "inner_case", "event_window": {"start_s": EVENT_T_S, "pressure_end_s": end_rel}}]}),
        encoding="utf-8")
    return folder


@pytest.mark.parametrize(("runner_end", "stop"), [
    (EVENT_T_S + 0.82, False),          # same end
    (EVENT_T_S + 0.82 + 0.15, True),    # > 0.1 s
])
def test_cd3_window_end_difference(mod, tmp_path, runner_end, stop):
    row = cd3_row(floor_result())
    params = {"head_area_m2": HEAD_AREA_M2}
    block = mod.l2b_moving_pressure(row, params, write_runner_window(tmp_path, runner_end), "C-5", "E_X")
    check = block["runner_window_CD_3"]
    assert block["status"] == "judged" and check["status"] == "found" and check["stop"] is stop


def test_cd3_window_difference_that_changes_a_verdict(mod, tmp_path):
    """A difference <= 0.1 s that moves a 200 bar extension sample out of W: the outside-W
    verdict changes, so the bundle stops."""
    row = cd3_row(floor_result())
    t = row["record"]["t"]
    k = int(np.flatnonzero(np.isclose(t, EVENT_T_S + 0.8 + T0_S))[0])
    row["record"]["F_cyl"][k, 1] = 200e3
    block = mod.l2b_moving_pressure(row, {"head_area_m2": HEAD_AREA_M2},
                                    write_runner_window(tmp_path, EVENT_T_S + 0.75), "C-5", "E_X")
    check = block["runner_window_CD_3"]
    assert check["difference_s"] < 0.1 and check["verdicts_changed"] and check["stop"] is True


def test_cd3_window_undecided_and_runner_missing(mod, tmp_path):
    row = cd3_row(floor_result())
    del row["pads"]["N"]
    block = mod.l2b_moving_pressure(row, {"head_area_m2": HEAD_AREA_M2}, None, "C-5", "E_X")
    assert block["status"] == "not_judgeable" and block["reason"].startswith("사건 창 결정 불가")
    row = cd3_row(floor_result())
    block = mod.l2b_moving_pressure(row, {"head_area_m2": HEAD_AREA_M2}, tmp_path, "C-5", "E_X")
    assert block["runner_window_CD_3"]["status"] == "runner judge file missing"
    assert block["runner_window_CD_3"]["stop"] is False


def test_cd3_event_free_row_keeps_the_d32_rule(mod):
    row = cd3_row(fast_result(depth=0.0115, ramp=2.0))
    block = mod.l2b_moving_pressure(row, {"head_area_m2": HEAD_AREA_M2}, None, "C-5", "E_G4_X")
    assert block["status"] == "judged" and "row_kind" not in block
    assert block["max_moving_bar"] == pytest.approx(100.0) and block["event_test_CD_3"]["kind"] is None


def test_cd5_ready_items_without_ready(mod):
    out = mod.ready_items([(1.0, "level")], 0.0, {"P3-6_ready": {"limit_s": 60.0}})
    assert out["P3-6"] == "fail" and out["READY_le_120s"] is False
    assert out["reason"].startswith("READY 없음")


def test_cd5_g6_gates_without_ready(mod):
    """No READY: G6-1 on the recontact condition, G6-4 / G6-5 not applicable (out of the grade),
    G6-6 and READY <= 120 s fail."""
    ready = {"t_ready_rel_s": None, "P3-6": "fail", "READY_le_120s": False}
    rc = {"pass": True, "flags": []}
    out = mod.g6_grade({"checks": {"P3-4_verdict": "pass"}}, np.zeros(3), np.zeros(3), 50e3, rc,
                       {"within": True}, {"verdict": "pass"}, ready, {"class": None}, False, F_MIN)
    gates = out["gates"]
    assert gates["G6-1_crawler"] == "pass" and gates["G6-4_att"] == "not_applicable"
    assert gates["G6-5_rut_stroke"] == "not_applicable" and gates["G6-6_fault_ready"] == "fail"
    assert out["grade"] == "fail" and "G6-4_att" in out["gate_reasons_CD_5"]
