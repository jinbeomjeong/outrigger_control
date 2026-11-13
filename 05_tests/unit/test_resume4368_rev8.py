"""436.8 rules rev8 (``v5_resume_4368_rules_rev8.md``, sealed 3ecafaaf) in the path 1 tools.

R8-4: the seal lists of ``resume4368_judge``, ``judge4368_common`` and ``chrono_rows_judge_4368``
carry rev8 (S-1 when the file or its ``.sha256`` is missing or differs). R8-1: runs without a T4h
record get their tag recomputed from the recorded switches and compared with the top-level
``controller_tag`` (different, one side only or not computable = S-2; G-S also S-11). R8-2: the
Chrono J-P3 applies to the ③ rows by the tag only. R8-3: the Chrono J11 reads the 1 ms
``law_locked`` (SCM ``step_series.npz``, L2b ``pads.npz``). Synthetic inputs only.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parents[2]
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
CHRONO_SCRIPTS = ROOT / "04_scripts" / "02_chrono"
SCRIPTS = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "scripts"
for _path in (COUPLED, CHRONO_SCRIPTS, SCRIPTS, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import chrono_rows_judge_4368 as chrono_judge  # noqa: E402
import judge4368_common as common  # noqa: E402
import resume4368_judge as judge  # noqa: E402
from lock_window_alignment import WindowSettings  # noqa: E402

REV8_NAME = "v5_resume_4368_rules_rev8.md"
REV8_SHA256 = "3ecafaaf33d84bb6f34a8cef5401771832a4999e4930f3644caff56eed640e56"
TAG_P3 = "final_C4G2_P3_LAS_K1"
TAG_V0 = "final_C4G2_LAS_K1"
TAG_BEFORE_FIX = "final_C4G2_P3"
"""The b1ddeae G-S top-level tag of the grid job and H-8 seedext (rev7 R7-1b record defect)."""


# ------------------------------------------------------------------------------- R8-4 seals
def test_every_path1_seal_list_has_rev8() -> None:
    assert (judge.RULES_REV8_NAME, judge.RULES_REV8_SHA256) == (REV8_NAME, REV8_SHA256)
    assert (REV8_NAME, REV8_SHA256) in judge.SEALED_REVISIONS
    assert (REV8_NAME, REV8_SHA256) in common.SEALED_RULES
    assert chrono_judge.RULES_SEALS[REV8_NAME] == REV8_SHA256


def test_stored_rev8_matches_its_seal() -> None:
    assert judge.sealed_rules_check()["problems"] == []
    assert common.seal_report()["problems"] == []
    assert chrono_judge.seal_check(common.RULES_DIR)["ok"] is True


def _copy_sealed_rules(target: Path) -> None:
    for name in [*chrono_judge.RULES_SEALS, *(n for n, _ in judge.SEALED_REVISIONS)]:
        source = common.RULES_DIR / name
        for path in (source, source.with_suffix(".sha256")):
            shutil.copy2(path, target / path.name)


def _seal_findings(folder: Path) -> tuple[bool, bool, bool]:
    return (judge.sealed_rules_check(folder)["stop_S1"], common.seal_report(folder)["stop_S1"],
            not chrono_judge.seal_check(folder)["ok"])


def test_rev8_seal_holds_on_a_copy(tmp_path: Path) -> None:
    _copy_sealed_rules(tmp_path)
    assert _seal_findings(tmp_path) == (False, False, False)


def test_a_changed_rev8_file_is_s1(tmp_path: Path) -> None:
    _copy_sealed_rules(tmp_path)
    rules = tmp_path / REV8_NAME
    rules.write_bytes(rules.read_bytes().replace(b"\n", b"\r\n"))  # sealed raw: CRLF differs
    assert _seal_findings(tmp_path) == (True, True, True)


def test_a_rev8_seal_file_with_another_value_is_s1(tmp_path: Path) -> None:
    _copy_sealed_rules(tmp_path)
    seal = tmp_path / "v5_resume_4368_rules_rev8.sha256"
    seal.write_text(f"{'0' * 64}  {REV8_NAME}\n", encoding="utf-8")
    assert _seal_findings(tmp_path) == (True, True, True)


@pytest.mark.parametrize("missing", [REV8_NAME, "v5_resume_4368_rules_rev8.sha256"])
def test_a_missing_rev8_file_is_s1(tmp_path: Path, missing: str) -> None:
    _copy_sealed_rules(tmp_path)
    (tmp_path / missing).unlink()
    assert _seal_findings(tmp_path) == (True, True, True)


# --------------------------------------------------------------------- R8-1c tag rules
@pytest.mark.parametrize(
    ("extend_start", "las", "k1", "tag"),
    [
        (True, True, True, "final_C4G2_P3_LAS_K1"),
        (True, True, False, "final_C4G2_P3_LAS"),
        (True, False, True, "final_C4G2_P3_K1"),
        (True, False, False, "final_C4G2_P3"),
        (False, True, True, "final_C4G2_LAS_K1"),
        (False, True, False, "final_C4G2_LAS"),
        (False, False, True, "final_C4G2_K1"),
        (False, False, False, None),
    ],
)
def test_recompute_tag_rules(extend_start, las, k1, tag) -> None:
    assert judge.recompute_tag(extend_start, las, k1) == tag


def test_recompute_tag_agrees_with_the_code_tag_function() -> None:
    """R8-1c last line: the sealed rule gives what ``v5_options.controller_tag`` gives."""
    from types import SimpleNamespace

    from outrigger_sim.hydraulics.v5_options import HydraulicOptions, controller_tag

    for extend_start in (False, True):
        for las in (False, True):
            for k1 in (False, True):
                config = SimpleNamespace(
                    liftoff_approach_slow=SimpleNamespace(enable=las),
                    slope_clearance_margin=SimpleNamespace(flat_soil_margin_order_gate=k1))
                options = HydraulicOptions(extend_start_tracked=extend_start)
                assert judge.recompute_tag(extend_start, las, k1) == \
                    controller_tag(options, config)


# --------------------------------------------------------------------- R8-1 recompute check
def _resume_block(las: object = True, k1: object = True, applicable: object = True) -> dict:
    return {"applicable": applicable,
            "liftoff_approach_slow": {"settings": {"enable": las}},
            "slope_clearance_margin": {"settings": {"flat_soil_margin_order_gate": k1}}}


def _r79(key: str, top_tag: str | None, *, extend_start: bool = True, **changes) -> dict:
    record: dict = {"key": key, "seed_index": 0, "harness": "g8", "inner": 0,
                    "hydraulic_options": {"valve_tau_s": 0.1}, "resume_k1": _resume_block()}
    if extend_start:
        record["hydraulic_options"]["extend_start_tracked"] = True
    if top_tag is not None:
        record["controller_tag"] = top_tag
    record.update(changes)
    return record


def _grid_job(top_tag: str | None, runs: int = 2, **changes) -> dict:
    job = {"key": "g", "controller_tag": top_tag,
           "hydraulic_options": {"extend_start_tracked": True},
           "resume_k1": _resume_block(),
           "runs": [{"event": "FS24", "resume_k1": _resume_block()} for _ in range(runs)]}
    job.update(changes)
    return job


def _write(path: Path, results: list[dict]) -> Path:
    path.write_text(json.dumps({"meta": {}, "results": results}), encoding="utf-8")
    return path


def _check(tmp_path: Path, results: list[dict], name: str = "seedext.json") -> dict:
    return judge.r79_tag_check([_write(tmp_path / name, results)])


def test_b1ddeae_like_grid_and_seedext_records_are_s2(tmp_path: Path) -> None:
    """R8-1e: recorded final_C4G2_P3, recomputed final_C4G2_P3_LAS_K1."""
    check = judge.r79_tag_check([_write(tmp_path / "grid.json", [_grid_job(TAG_BEFORE_FIX)]),
                                 _write(tmp_path / "seedext.json", [_r79("s", TAG_BEFORE_FIX)])])
    assert (check["compared"], check["by_method"]["recompute"], check["mismatched"]) == (2, 2, 2)
    assert check["stop_S2"] is True and check["not_computable"] == 0
    assert {row["recomputed_tag"] for row in check["rows"]} == {TAG_P3}


def test_c4e0ed9_like_records_match(tmp_path: Path) -> None:
    check = judge.r79_tag_check([
        _write(tmp_path / "grid.json", [_grid_job(TAG_P3)]),
        _write(tmp_path / "seedext.json", [_r79("s", TAG_P3)]),
        _write(tmp_path / "h7.json", [_r79("h7", TAG_V0, extend_start=False, controller_settings={
            "two_pressure.extend_start_rule": "constant"})]),
    ])
    assert (check["compared"], check["mismatched"], check["stop_S2"]) == (3, 0, False)


def test_no_tag_on_both_sides_matches_and_one_side_is_s2(tmp_path: Path) -> None:
    off = _resume_block(las=False, k1=False)
    no_tag = _r79("a", None, extend_start=False, resume_k1=off)
    assert _check(tmp_path, [no_tag])["stop_S2"] is False
    one_side = _check(tmp_path, [_r79("a", None)])
    assert one_side["stop_S2"] is True and "recomputed tag only" in one_side["rows"][0]["reason"]
    top_only = _check(tmp_path, [_r79("a", TAG_V0, extend_start=False, resume_k1=off)])
    assert "top level only" in top_only["rows"][0]["reason"]


def test_a_tcl_top_tag_differs(tmp_path: Path) -> None:
    assert _check(tmp_path, [_r79("a", TAG_P3 + "_TCL")])["stop_S2"] is True


@pytest.mark.parametrize(
    "changes",
    [
        {"hydraulic_options": None},
        {"resume_k1": None},
        {"resume_k1": _resume_block(applicable=False)},
        {"resume_k1": _resume_block(las=None)},
        {"resume_k1": _resume_block(k1="yes")},
    ],
)
def test_not_computable_is_s2_and_gs_s11(tmp_path: Path, changes: dict, monkeypatch) -> None:
    record = _r79("a", TAG_P3, **changes)
    if record.get("hydraulic_options") is None:
        del record["hydraulic_options"]
    check = _check(tmp_path, [record])
    assert check["stop_S2"] is True and check["not_computable"] == 1
    assert check["stop_S11_not_computable"] is True
    assert "not computable" in check["rows"][0]["reason"]
    monkeypatch.setattr(judge, "sealed_rules_check", lambda: {"problems": [], "stop_S1": False})
    out = tmp_path / "gs.json"
    code = judge.main(["gs", "--harness", str(tmp_path / "seedext.json"), "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == 1 and report["stop_S2"] is True and report["stop_S11"] is True
    assert "recomputed_tag" not in report["r79_tag_check"]["rows"][0]  # gs shows no tag values


def test_grid_run_switches_must_equal_the_job(tmp_path: Path) -> None:
    job = _grid_job(TAG_P3)
    job["runs"][1]["resume_k1"] = _resume_block(las=False)
    check = _check(tmp_path, [job], "grid.json")
    assert check["stop_S2"] is True and "runs[1]" in check["rows"][0]["reason"]
    job["runs"][1] = {"event": "FS24"}  # no block in a run: not computable
    assert _check(tmp_path, [job], "grid.json")["not_computable"] == 1


def test_dg3_extend_start_rule_must_match_the_switch(tmp_path: Path) -> None:
    record = _r79("a", TAG_P3, controller_settings={"two_pressure.extend_start_rule": "constant"})
    check = _check(tmp_path, [record])
    assert check["stop_S2"] is True and "extend_start_rule" in check["rows"][0]["reason"]


def test_a_run_with_t4h_file_is_never_recomputed(tmp_path: Path) -> None:
    """R8-1a: a listed T4h file that is not found is S-2 (R7-1a), not a recompute."""
    check = _check(tmp_path, [_r79("a", TAG_P3, t4h_file="missing.npz")], "h6.json")
    assert check["by_method"] == {"t4h_meta": 1, "recompute": 0} and check["stop_S2"] is True


# ----------------------------------------------------------------------- R8-2 Chrono J-P3
def _chrono_row(engine: str = "SCM", tag: str | None = TAG_P3, *,
                rule: str | None = "tracked_bound", options_flag: bool | None = True,
                breaches=(0, 0, 0, 0), check_ok: bool = True) -> dict:
    settings = {} if rule is None else {"extend_start_rule": rule}
    result: dict = {
        "controller_meta": {"period_s": 0.1,
                            "two_pressure": {"settings": settings, "has_rod_sensor": True}},
        "hydraulics_record": {"extend_bound_check": {"breach_reads": list(breaches)}},
    }
    if options_flag is not None:
        options = {"valve_tau_s": 0.1}
        if options_flag:
            options["extend_start_tracked"] = True
        result["v5_hydraulics"] = {"hydraulic_options": options}
    check = {"name": tag, "ok": check_ok}
    if engine == "SCM":
        result["args"] = {"expect_controller": tag}
        result["c2_setup"] = {"expect_controller": check}
    else:
        result["expect_controller"] = check
    return {"engine": engine, "name": "row", "result": result, "events": []}


def _meta(tag: str | None, extend_flag: bool, criteria: str = "C-5") -> dict:
    argv = ["python", "04_scripts/02_chrono/run_S9.py", "level"]
    if tag is not None:
        argv += ["--expect-controller", tag]
    if extend_flag:
        argv.append("--extend-start-tracked")
    return {"case": "row", "criteria_id": criteria, "argv": argv}


def test_j_p3_on_a_p3_row_passes_and_breach_is_h7() -> None:
    passed = chrono_judge.j_p3_block(_chrono_row(), _meta(TAG_P3, True))
    assert (passed["status"], passed["s2"], passed.get("stop")) == ("pass", [], None)
    breach = chrono_judge.j_p3_block(_chrono_row(breaches=(0, 2, 0, 0)), _meta(TAG_P3, True))
    assert breach["stop"] == "H-7" and breach["breach_reads"] == 2


def test_j_p3_is_not_applicable_on_a_v0_row_without_its_keys() -> None:
    row = _chrono_row(tag=TAG_V0, rule=None, options_flag=None)
    del row["result"]["hydraulics_record"]
    out = chrono_judge.j_p3_block(row, _meta(TAG_V0, False))
    assert (out["status"], out["s2"]) == ("not_applicable", [])


def test_j_p3_p3_row_without_rule_is_not_judgeable_other_rule_is_s2() -> None:
    missing = chrono_judge.j_p3_block(_chrono_row(rule=None), _meta(TAG_P3, True))
    assert missing["status"] == "not_judgeable" and missing["s2"] == []
    other = chrono_judge.j_p3_block(_chrono_row(rule="constant"), _meta(TAG_P3, True))
    assert other["status"] == "S-2" and other["s2"]


@pytest.mark.parametrize(
    ("tag", "extend_flag", "options_flag"),
    [(TAG_P3, False, True), (TAG_P3, True, False), (TAG_V0, True, None), (TAG_V0, False, True)],
)
def test_j_p3_request_records_against_the_tag_are_s2(tag, extend_flag, options_flag) -> None:
    out = chrono_judge.j_p3_block(_chrono_row(tag=tag, options_flag=options_flag),
                                  _meta(tag, extend_flag))
    assert out["s2"]
    stops = chrono_judge.rev8_stops("row", out, {"stop": False})
    assert stops and stops[0]["reason"].startswith("S-2")


def test_j_p3_expect_check_of_another_tag_is_s2() -> None:
    row = _chrono_row()
    row["result"]["c2_setup"]["expect_controller"]["name"] = TAG_V0
    assert chrono_judge.j_p3_block(row, _meta(TAG_P3, True))["s2"]


def test_j_p3_without_a_true_expect_check_is_not_judgeable() -> None:
    out = chrono_judge.j_p3_block(_chrono_row(check_ok=False), _meta(TAG_P3, True))
    assert out["status"] == "not_judgeable" and out["is_extend_start"] is None


def test_j_p3_l2b_row_reads_its_expect_check_and_argv() -> None:
    meta = _meta(TAG_P3, True)
    meta["argv"][1] = "04_scripts/02_chrono/run_S8C.py"
    out = chrono_judge.j_p3_block(_chrono_row("L2b"), meta)
    assert out["status"] == "pass" and out["tag"]["source"] == "batch argv"


# ------------------------------------------------------------------------ R8-3 Chrono J11
TAU_S, EPS_M_S, CLOSING_S, PERIOD_S = 0.1, 0.001, 0.05, 0.1
STOP_S = 0.4
"""FL command ends at the sample before 0.4 s: its stretch opens at 0.4 s."""


def _window_end() -> float:
    settings = WindowSettings(TAU_S, EPS_M_S, CLOSING_S, PERIOD_S)
    return settings.window_end_s(STOP_S, 0.01)


def _lock_row(engine: str = "SCM", *, fl_lock_s: float | None = None, unarmed: bool = False,
              current: bool = False, fallback_event: bool = True, law_dtype=np.int8) -> dict:
    """FL stretch from 0.4 s, window end ~0.78 s; FL locks at ``fl_lock_s`` (None = never)."""
    t_r8 = np.round(np.arange(10) * PERIOD_S, 10)
    issued = np.zeros((10, 4))
    issued[:3, 0] = 0.01  # acting command = issued of the sample before: FL moves 0.1 .. 0.3 s
    t_fine = np.round(np.arange(1, 901) * 1e-3, 10)
    law = np.ones((t_fine.size, 4), dtype=np.int8)
    law[:, 0] = 0
    if fl_lock_s is not None:
        law[t_fine >= fl_lock_s - 1e-9, 0] = 1
    if unarmed:
        law[:, 0] = -1
    monitor = {"has_rod_sensor": True, "load_estimate": "two_pressure",
               "settings": {"lock_window_valve_tau_s": TAU_S, "lock_window_eps_m_s": EPS_M_S,
                            "lock_window_closing_delay_s": CLOSING_S},
               "fallback_lock_log": [],
               "fallback_lock_current": (
                   [{"leg": "FL", "t_start_s": STOP_S, "window_end_s": _window_end()}]
                   if current else [])}
    events = [(0.35, "WARN_ROD_PRESSURE_FALLBACK:FL")] if fallback_event else []
    row = {"engine": engine, "name": "row", "events": events, "r8": {"t": t_r8, "issued_u": issued},
           "result": {"controller_meta": {"period_s": PERIOD_S, "two_pressure": monitor}}}
    arrays = {"law_locked": law.astype(law_dtype)}
    if engine == "SCM":
        row["series"] = {"t_s": t_fine, **arrays}
    else:
        row["pads"] = {"t": t_fine, **arrays}
    return row


def test_j11_late_fallback_leg_from_the_scm_law_locked_is_h7() -> None:
    out = chrono_judge.j11_block(_lock_row(current=True), {"criteria_id": "C-5", "case": "row"})
    assert out["lock_source"].startswith("step_series.npz law_locked")
    assert (out["n_late_fallback_R6_B7"], out["status"], out["stop"]) == (1, "H-7", True)


def test_j11_event_only_open_stretch_counts_rev6_b7() -> None:
    out = chrono_judge.j11_block(_lock_row(current=False), {"criteria_id": "C-5", "case": "row"})
    assert out["event_only_legs"] == ["FL"] and out["n_late_fallback_R6_B7"] == 1


def test_j11_locked_in_time_passes_and_unarmed_reads_as_locked() -> None:
    early = chrono_judge.j11_block(_lock_row(fl_lock_s=0.6, current=True), {"criteria_id": "C-5"})
    assert (early["n_late_fallback_R6_B7"], early["status"]) == (0, "pass")
    unarmed = chrono_judge.j11_block(_lock_row(unarmed=True, current=True), {"criteria_id": "C-5"})
    assert unarmed["n_late_fallback_R6_B7"] == 0 and unarmed["stop"] is False


def test_j11_ls_row_stop_is_l_e_and_l2b_reads_pads() -> None:
    out = chrono_judge.j11_block(_lock_row("L2b", current=True),
                                 {"criteria_id": "C-5", "case": "R12_o0.0_LS2"})
    assert out["lock_source"].startswith("pads.npz") and out["status"] == "L-e"


def test_j11_without_fallback_leg_records_n_late() -> None:
    out = chrono_judge.j11_block(_lock_row(fallback_event=False), {"criteria_id": "C-5"})
    assert out["status"] == "no_fallback_leg" and out["n_late_by_leg"]["FL"] == 1


@pytest.mark.parametrize("defect", ["missing", "dtype", "values", "shape"])
def test_j11_missing_or_malformed_record_stops_a_c5_row(defect: str) -> None:
    row = _lock_row(current=True)
    series = row["series"]
    if defect == "missing":
        del series["law_locked"]
    elif defect == "dtype":
        series["law_locked"] = series["law_locked"].astype(np.int16)
    elif defect == "values":
        series["law_locked"][5, 2] = 2
    else:
        series["law_locked"] = series["law_locked"][:-1]
    out = chrono_judge.j11_block(row, {"criteria_id": "C-5"})
    assert (out["status"], out["stop"]) == ("not_judgeable", True) and out["problems"]
    stops = chrono_judge.rev8_stops("row", {"s2": []}, out)
    assert stops and "J11 not judgeable" in stops[0]["reason"]
    other = chrono_judge.j11_block(row, {"criteria_id": "C-1"})
    assert (other["status"], other["stop"]) == ("not_applicable", False)


def test_rev8_counts_summary() -> None:
    rows = [{"items": {"J-P3_R8-2": {"status": "not_applicable", "s2": []},
                       "J11_R8-3": {"status": "not_judgeable", "j11_row": True}}},
            {"items": {"J-P3_R8-2": {"status": "pass", "s2": ["x"]},
                       "J11_R8-3": {"status": "pass", "j11_row": True}}}]
    counts = chrono_judge.rev8_counts(rows)
    assert counts["J-P3"] == {"not_applicable": 1, "pass": 1} and counts["S-2_rows"] == 1
    assert counts["J11_rows_not_judgeable"] == 1
