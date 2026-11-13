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
    return (
        judge.sealed_rules_check(folder)["stop_S1"],
        common.seal_report(folder)["stop_S1"],
        not chrono_judge.seal_check(folder)["ok"],
    )


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
                    slope_clearance_margin=SimpleNamespace(flat_soil_margin_order_gate=k1),
                )
                options = HydraulicOptions(extend_start_tracked=extend_start)
                assert judge.recompute_tag(extend_start, las, k1) == controller_tag(options, config)


# --------------------------------------------------------------------- R8-1 recompute check
def _resume_block(las: object = True, k1: object = True, applicable: object = True) -> dict:
    return {
        "applicable": applicable,
        "liftoff_approach_slow": {"settings": {"enable": las}},
        "slope_clearance_margin": {"settings": {"flat_soil_margin_order_gate": k1}},
    }


def _r79(key: str, top_tag: str | None, *, extend_start: bool = True, **changes) -> dict:
    record: dict = {
        "key": key,
        "seed_index": 0,
        "harness": "g8",
        "inner": 0,
        "hydraulic_options": {"valve_tau_s": 0.1},
        "resume_k1": _resume_block(),
    }
    if extend_start:
        record["hydraulic_options"]["extend_start_tracked"] = True
    if top_tag is not None:
        record["controller_tag"] = top_tag
    record.update(changes)
    return record


def _grid_job(top_tag: str | None, runs: int = 2, **changes) -> dict:
    job = {
        "key": "g",
        "controller_tag": top_tag,
        "hydraulic_options": {"extend_start_tracked": True},
        "resume_k1": _resume_block(),
        "runs": [{"event": "FS24", "resume_k1": _resume_block()} for _ in range(runs)],
    }
    job.update(changes)
    return job


def _write(path: Path, results: list[dict]) -> Path:
    path.write_text(json.dumps({"meta": {}, "results": results}), encoding="utf-8")
    return path


def _check(tmp_path: Path, results: list[dict], name: str = "seedext.json") -> dict:
    return judge.r79_tag_check([_write(tmp_path / name, results)])


def test_b1ddeae_like_grid_and_seedext_records_are_s2(tmp_path: Path) -> None:
    """R8-1e: recorded final_C4G2_P3, recomputed final_C4G2_P3_LAS_K1."""
    check = judge.r79_tag_check(
        [
            _write(tmp_path / "grid.json", [_grid_job(TAG_BEFORE_FIX)]),
            _write(tmp_path / "seedext.json", [_r79("s", TAG_BEFORE_FIX)]),
        ]
    )
    assert (check["compared"], check["by_method"]["recompute"], check["mismatched"]) == (2, 2, 2)
    assert check["stop_S2"] is True and check["not_computable"] == 0
    assert {row["recomputed_tag"] for row in check["rows"]} == {TAG_P3}


def test_c4e0ed9_like_records_match(tmp_path: Path) -> None:
    check = judge.r79_tag_check(
        [
            _write(tmp_path / "grid.json", [_grid_job(TAG_P3)]),
            _write(tmp_path / "seedext.json", [_r79("s", TAG_P3)]),
            _write(
                tmp_path / "h7.json",
                [
                    _r79(
                        "h7",
                        TAG_V0,
                        extend_start=False,
                        controller_settings={"two_pressure.extend_start_rule": "constant"},
                    )
                ],
            ),
        ]
    )
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
def _chrono_row(
    engine: str = "SCM",
    tag: str | None = TAG_P3,
    *,
    rule: str | None = "tracked_bound",
    options_flag: bool | None = True,
    breaches=(0, 0, 0, 0),
    check_ok: bool = True,
) -> dict:
    settings = {} if rule is None else {"extend_start_rule": rule}
    result: dict = {
        "controller_meta": {
            "period_s": 0.1,
            "two_pressure": {"settings": settings, "has_rod_sensor": True},
        },
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
    out = chrono_judge.j_p3_block(
        _chrono_row(tag=tag, options_flag=options_flag), _meta(tag, extend_flag)
    )
    assert out["s2"]
    stops = chrono_judge.rev8_stops("row", out, {"stop": False})
    assert stops and stops[0]["reason"].startswith("S-2")


def test_j_p3_expect_check_of_another_tag_is_s2() -> None:
    row = _chrono_row()
    row["result"]["c2_setup"]["expect_controller"]["name"] = TAG_V0
    assert chrono_judge.j_p3_block(row, _meta(TAG_P3, True))["s2"]


def test_j_p3_without_a_true_expect_check_is_s2_rev9() -> None:
    """Rev9 R9-1: expect_controller.ok false or missing = S-2 (not only J-P3 not judgeable)."""
    out = chrono_judge.j_p3_block(_chrono_row(check_ok=False), _meta(TAG_P3, True))
    assert out["status"] == "S-2" and out["is_extend_start"] is None and out["expect_check_failed"]
    assert chrono_judge.rev8_stops("row", out, {"stop": False})[0]["reason"].startswith("S-2")
    missing = _chrono_row()
    del missing["result"]["c2_setup"]["expect_controller"]
    assert chrono_judge.j_p3_block(missing, _meta(TAG_P3, True))["status"] == "S-2"


def test_j_p3_l2b_row_reads_its_expect_check_and_argv() -> None:
    meta = _meta(TAG_P3, True)
    meta["argv"][1] = "04_scripts/02_chrono/run_S8C.py"
    out = chrono_judge.j_p3_block(_chrono_row("L2b"), meta)
    assert out["status"] == "pass" and out["tag"]["source"] == "batch argv"


# ------------------------------------------------------------------------ R8-3 Chrono J11
TAU_S, EPS_M_S, CLOSING_S, PERIOD_S = 0.1, 0.001, 0.05, 0.1
STOP_S = 0.4
"""FL command ends at the sample before 0.4 s: its stretch opens at 0.4 s."""
PRE_ARM_SAMPLES = 100


def _window_end() -> float:
    settings = WindowSettings(TAU_S, EPS_M_S, CLOSING_S, PERIOD_S)
    return settings.window_end_s(STOP_S, 0.01)


def _lock_row(
    engine: str = "SCM",
    *,
    fl_lock_s: float | None = None,
    pre_arm: bool = False,
    current: bool = False,
    fallback_event: bool = True,
    law_dtype=np.int8,
) -> dict:
    """FL stretch from 0.4 s, window end ~0.78 s; FL locks at ``fl_lock_s`` (None = never).
    ``pre_arm``: all
    four legs -1 for the first 100 ms (the allowed rev9 R9-3 pattern)."""
    t_r8 = np.round(np.arange(10) * PERIOD_S, 10)
    issued = np.zeros((10, 4))
    issued[:3, 0] = 0.01  # acting command = issued of the sample before: FL moves 0.1 .. 0.3 s
    t_fine = np.round(np.arange(1, 901) * 1e-3, 10)
    law = np.ones((t_fine.size, 4), dtype=np.int8)
    law[:, 0] = 0
    if fl_lock_s is not None:
        law[t_fine >= fl_lock_s - 1e-9, 0] = 1
    if pre_arm:
        law[:PRE_ARM_SAMPLES, :] = -1
    monitor = {
        "has_rod_sensor": True,
        "load_estimate": "two_pressure",
        "settings": {
            "lock_window_valve_tau_s": TAU_S,
            "lock_window_eps_m_s": EPS_M_S,
            "lock_window_closing_delay_s": CLOSING_S,
        },
        "fallback_lock_log": [],
        "fallback_lock_current": (
            [{"leg": "FL", "t_start_s": STOP_S, "window_end_s": _window_end()}] if current else []
        ),
    }
    events = [(0.35, "WARN_ROD_PRESSURE_FALLBACK:FL")] if fallback_event else []
    row = {
        "engine": engine,
        "name": "row",
        "events": events,
        "r8": {"t": t_r8, "issued_u": issued},
        "result": {"controller_meta": {"period_s": PERIOD_S, "two_pressure": monitor}},
    }
    arrays = {"law_locked": law.astype(law_dtype)}
    if engine == "SCM":
        row["series"] = {"t_s": t_fine, **arrays}
    else:
        row["pads"] = {"t": t_fine, **arrays}
    return row


def _law(row: dict) -> np.ndarray:
    return (row.get("series") or row.get("pads"))["law_locked"]


MANIFEST = chrono_judge.load_manifest(chrono_judge.MANIFEST_DEFAULT)
C5_BUNDLE = "V5-RESUME-K1-C5"


def _manifest_meta(
    case: str,
    bundle: str = C5_BUNDLE,
    runner: str = "run_S8C.py",
    batch_setting: object = "<manifest>",
) -> dict:
    """Batch meta of a stored manifest row: argv from ``argv_tail``, ``batch.json``
    ``v5_setting`` = the
    manifest value unless given (``None`` key removed when ``batch_setting`` is ``"<absent>"``)."""
    entry = next(r for r in MANIFEST["batches"][bundle]["rows"] if r["case"] == case)
    argv = ["python.exe", f"04_scripts/02_chrono/{runner}", *entry["argv_tail"]]
    meta = {
        "case": case,
        "criteria_id": entry["criteria_id"],
        "argv": argv,
        "_batch": f"07_results/S9/batch_{bundle}_20261113_120000",
        "v5_setting": entry["v5_setting"] if batch_setting == "<manifest>" else batch_setting,
    }
    if batch_setting == "<absent>":
        del meta["v5_setting"]
    return meta


# ------------------------------------------------------------------ rev9 R9-4 LS rows
def test_ls_setting_ls_rows_from_manifest_and_batch_json() -> None:
    ls_row = chrono_judge.ls_setting(_manifest_meta("K0V_top_fup3.5_Fs0_LS1"), MANIFEST)
    assert (ls_row["is_ls"], ls_row["v5_setting"], ls_row["bundle"]) == (True, "LS1", C5_BUNDLE)
    assert chrono_judge.ls_setting(_manifest_meta("E_G4_Fs8_LS4"), MANIFEST)["is_ls"] is True


def test_ls_setting_non_ls_rows() -> None:
    vb_row = chrono_judge.ls_setting(_manifest_meta("E_G4_Fs8"), MANIFEST)
    assert (vb_row["is_ls"], vb_row["v5_setting"]) == (False, "VB")
    for case in ("E_G4_Fs4_V0", "P3b_J1_B_top_Fs4_v0v", "P3b_J2_B_top_Fs4_m1p1_t180_seed20261026"):
        assert (
            chrono_judge.ls_setting(_manifest_meta(case, runner="run_S9.py"), MANIFEST)["is_ls"]
            is False
        )


def test_ls_setting_undecided_cases() -> None:
    meta = _manifest_meta("K0V_top_fup3.5_Fs0_LS1")
    assert chrono_judge.ls_setting(meta, None)["is_ls"] is None  # no manifest
    absent = chrono_judge.ls_setting(
        _manifest_meta("K0V_top_fup3.5_Fs0_LS1", batch_setting="<absent>"), MANIFEST
    )
    assert absent["is_ls"] is None and "one side only" in absent["reason"]
    none_batch = chrono_judge.ls_setting(
        _manifest_meta("K0V_top_fup3.5_Fs0_LS1", batch_setting=None), MANIFEST
    )
    assert none_batch["is_ls"] is None
    differs = chrono_judge.ls_setting(
        _manifest_meta("K0V_top_fup3.5_Fs0_LS1", batch_setting="LS4"), MANIFEST
    )
    assert differs["is_ls"] is None and "!=" in differs["reason"]
    unknown = {**meta, "case": "K0V_top_fup3.5_Fs0_LS9"}  # no manifest row: the name is not read
    assert chrono_judge.ls_setting(unknown, MANIFEST)["is_ls"] is None
    entry = {"case": meta["case"]}  # manifest without the key, batch.json LS1: one side only
    no_key = chrono_judge.ls_setting(meta, {"batches": {C5_BUNDLE: {"rows": [entry]}}})
    assert no_key["is_ls"] is None and "manifest row without v5_setting" in no_key["reason"]


def test_ls_setting_absent_on_both_sides_is_not_ls() -> None:
    """Rev9 R9-4: manifest and batch.json both without (or None) v5_setting = not LS (L1-R)."""
    l1r = chrono_judge.ls_setting(
        _manifest_meta("D1C1_top_flat_crx3", bundle="V5-RESUME-K1-C1", runner="run_S6C.py"),
        MANIFEST,
    )
    assert (l1r["is_ls"], l1r["v5_setting"], l1r["batch_v5_setting"]) == (False, None, None)
    meta = _manifest_meta("D1C1_top_flat_crx3", bundle="V5-RESUME-K1-C1", batch_setting="<absent>")
    assert chrono_judge.ls_setting(meta, MANIFEST)["is_ls"] is False


def test_ls_row_with_a_tag_that_is_not_p3_is_s2() -> None:
    meta = {
        **_meta(TAG_V0, False),
        **{
            k: v
            for k, v in _manifest_meta("E_G4_Fs8_LS1").items()
            if k in ("case", "_batch", "v5_setting")
        },
    }
    out = chrono_judge.j_p3_block(_chrono_row(tag=TAG_V0, options_flag=None), meta, MANIFEST)
    assert any("R9-4" in text for text in out["s2"])


# ------------------------------------------------------------------ J11 (rev8 R8-3, rev9)
def test_j11_late_fallback_leg_on_a_vb_row_is_h7() -> None:
    out = chrono_judge.j11_block(_lock_row(current=True), _manifest_meta("E_G4_Fs8"), MANIFEST)
    assert out["lock_source"].startswith("step_series.npz law_locked")
    assert (out["n_late_fallback_R6_B7"], out["status"], out["stop"]) == (1, "H-7", True)
    assert out["ls_setting"]["is_ls"] is False


def test_j11_ls_row_stop_is_l_e_and_l2b_reads_pads() -> None:
    meta = _manifest_meta("K0V_top_fup3.5_Fs0_LS1")
    out = chrono_judge.j11_block(_lock_row("L2b", current=True), meta, MANIFEST)
    assert out["lock_source"].startswith("pads.npz") and out["status"] == "L-e" and out["stop"]


def test_j11_undecided_ls_row_is_not_judgeable_and_stops() -> None:
    """A late fallback leg on a C-5 row whose LS setting cannot be fixed (no name guess)."""
    out = chrono_judge.j11_block(
        _lock_row(current=True), {"criteria_id": "C-5", "case": "R12_o0.0_LS2"}, MANIFEST
    )
    assert (out["status"], out["stop"]) == ("not_judgeable", True)
    assert "undecided" in out["problems"][0] and out["ls_setting"]["is_ls"] is None
    stops = chrono_judge.rev8_stops("row", {"s2": []}, out)
    assert stops and "J11 not judgeable" in stops[0]["reason"]


def test_j11_event_only_open_stretch_counts_rev6_b7() -> None:
    out = chrono_judge.j11_block(_lock_row(current=False), {"criteria_id": "C-5", "case": "row"})
    assert out["event_only_legs"] == ["FL"] and out["n_late_fallback_R6_B7"] == 1


def test_j11_locked_in_time_passes_and_pre_arm_minus_one_reads_as_locked() -> None:
    early = chrono_judge.j11_block(_lock_row(fl_lock_s=0.6, current=True), {"criteria_id": "C-5"})
    assert (early["n_late_fallback_R6_B7"], early["status"]) == (0, "pass")
    pre_arm = chrono_judge.j11_block(
        _lock_row(fl_lock_s=0.6, pre_arm=True, current=True), {"criteria_id": "C-5"}
    )
    assert (
        pre_arm["law_locked_form"]["minus_one"] == "pre_arm_prefix" and pre_arm["status"] == "pass"
    )


def test_j11_late_on_a_row_of_another_criterion_is_recorded_only() -> None:
    """Rev9 R9-6: J11 stops on C-5 rows only."""
    out = chrono_judge.j11_block(_lock_row(current=True), {"criteria_id": "C-1", "case": "row"})
    assert (out["n_late_fallback_R6_B7"], out["status"], out["stop"]) == (1, "late_recorded", False)
    assert chrono_judge.rev8_stops("row", {"s2": []}, out) == []


def test_j11_without_fallback_leg_records_n_late() -> None:
    out = chrono_judge.j11_block(_lock_row(fallback_event=False), {"criteria_id": "C-5"})
    assert out["status"] == "no_fallback_leg" and out["n_late_by_leg"]["FL"] == 1


def _defect(row: dict, defect: str) -> None:
    arrays = row.get("series") or row.get("pads")
    law = arrays["law_locked"]
    time_key = "t_s" if "t_s" in arrays else "t"
    if defect == "missing":
        del arrays["law_locked"]
    elif defect == "time_column":
        del arrays[time_key]
    elif defect == "dtype":
        arrays["law_locked"] = law.astype(np.int16)
    elif defect == "values":
        law[5, 2] = 2
    elif defect == "shape":
        arrays["law_locked"] = law[:-1]
    elif defect == "spacing":
        arrays[time_key] = arrays[time_key].copy()
        arrays[time_key][300:] += 2e-6
    elif defect == "after_arm":
        law[500, :] = -1
    elif defect == "whole_run":
        law[:, :] = -1
    elif defect == "leg_mismatch":
        law[:50, :] = -1
        law[50:80, 1] = -1


DEFECTS = [
    "missing",
    "time_column",
    "dtype",
    "values",
    "shape",
    "spacing",
    "after_arm",
    "whole_run",
    "leg_mismatch",
]


@pytest.mark.parametrize("engine", ["SCM", "L2b"])
@pytest.mark.parametrize("defect", DEFECTS)
def test_j11_missing_or_malformed_record_stops_a_c5_row_of_both_engines(
    engine: str, defect: str
) -> None:
    """Rev9 R9-2 / R9-3 form, R9-5 both engines the same, R9-6 other rows "no input"."""
    row = _lock_row(engine, current=True)
    _defect(row, defect)
    out = chrono_judge.j11_block(row, {"criteria_id": "C-5"})
    assert (out["status"], out["stop"]) == ("not_judgeable", True) and out["problems"]
    stops = chrono_judge.rev8_stops("row", {"s2": []}, out)
    assert stops and "J11 not judgeable" in stops[0]["reason"]
    other = chrono_judge.j11_block(row, {"criteria_id": "C-1"})
    assert (other["status"], other["stop"]) == ("no_input", False)


@pytest.mark.parametrize(
    ("defect", "item"),
    [
        ("time_column", "time_column"),
        ("shape", "shape"),
        ("dtype", "dtype"),
        ("values", "values"),
        ("spacing", "spacing"),
        ("after_arm", "minus_one"),
        ("whole_run", "minus_one"),
        ("leg_mismatch", "minus_one"),
    ],
)
def test_law_locked_form_items(defect: str, item: str) -> None:
    row = _lock_row(current=True)
    _defect(row, defect)
    form = chrono_judge.law_locked_form(row["series"], "t_s")
    assert item in form["problems"] and not form["key_missing"]
    if item == "minus_one":
        assert form["minus_one"] == defect


def test_minus_one_patterns() -> None:
    law = np.ones((10, 4), dtype=np.int8)
    assert chrono_judge.minus_one_pattern(law) == "none"
    law[:3] = -1
    assert chrono_judge.minus_one_pattern(law) == "pre_arm_prefix"
    law[6, 0] = -1
    assert chrono_judge.minus_one_pattern(law) == "after_arm"


def test_rev8_counts_summary() -> None:
    rows = [
        {
            "items": {
                "J-P3_R8-2": {"status": "not_applicable", "s2": [], "ls_setting": {"is_ls": None}},
                "J11_R8-3": {
                    "status": "not_judgeable",
                    "j11_row": True,
                    "law_locked_form": {
                        "key_missing": False,
                        "problems": {"spacing": "x"},
                        "minus_one": "none",
                    },
                },
            }
        },
        {
            "items": {
                "J-P3_R8-2": {
                    "status": "S-2",
                    "s2": ["x"],
                    "expect_check_failed": True,
                    "ls_setting": {"is_ls": True},
                },
                "J11_R8-3": {
                    "status": "no_input",
                    "j11_row": False,
                    "law_locked_form": {"key_missing": True, "problems": {}, "minus_one": None},
                },
            }
        },
    ]
    counts = chrono_judge.rev8_counts(rows)
    assert counts["J-P3"] == {"not_applicable": 1, "S-2": 1} and counts["S-2_rows"] == 1
    assert counts["J11_rows_not_judgeable"] == 1 and counts["R9-1_expect_failed"] == 1
    assert counts["R9-2_form_problems_by_item"]["spacing"] == 1 and counts["R9-2_key_missing"] == 1
    assert counts["R9-3_minus_one"] == {"none": 1}
    assert (counts["R9-4_ls_rows"], counts["R9-4_undecided"], counts["R9-6_no_input"]) == (1, 1, 1)
