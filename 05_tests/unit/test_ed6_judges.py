"""436.9 edition 6 tool commit (``jp3_remedy_spec_v6.md`` 4 step 4a; 8 Y-5 / Y-6 / Y-10):
``jp3_ed6_judge.py`` (j9_main readings, sensitivity / confirmation, grid), the J-P3 setting
tables, the ``run_v5`` edition 6 batches and ``jp3_12b_judge_ed6.py`` (P-pred decide / judge).

The edition 5 reproduction (judgement 5 2: 75 items / 72 pair items, L-b relative 5 /
absolute 10, S8 not applicable 20) and the stored-file checks read the main checkout
(``MAIN_CHECKOUT``); every ``main`` runs with the working folder elsewhere (tool rule (가)).
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED_DIR, ROOT / "03_src", Path(__file__).resolve().parent):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import j_p3_inputs  # noqa: E402
import jp3_12b_judge as judge12b  # noqa: E402
import jp3_12b_judge_ed6 as judge12b6  # noqa: E402
import jp3_12b_ppred as ppred  # noqa: E402
import jp3_ed6_judge as ed6  # noqa: E402
import run_v5  # noqa: E402
import test_jp3_12b_tools as tools12b  # noqa: E402

MAIN_CHECKOUT = Path(r"C:\workspace\outrigger_control")
J5_ROWS = (MAIN_CHECKOUT / "06_analysis" / "02_control" / "j_p3_cause" / "j9_runs" / "606f8713"
           / "j9main_a1" / "j9_main.jsonl")
V0_MAIN = MAIN_CHECKOUT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "main.jsonl"
V0_SHA256 = "9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e"
KEYS = MAIN_CHECKOUT / "06_analysis" / "02_control" / "j_p3_cause" / "ed6_design" / "keys"
PRELOCK_T4H = (MAIN_CHECKOUT / "06_analysis" / "02_control" / "j_p3_cause" / "ed6_design"
               / "prelock_12a_755a15d8" / "L1_VBL_t4h")
SEALED = ["A_i", "A_ii", "B3"]


# ------------------------------------------------------------------------------- edition 5
@pytest.fixture(scope="module")
def ed5_report(tmp_path_factory) -> dict:
    """The edition 5 j9_main judged by the new tool with the readings (``main``, cwd elsewhere)."""
    folder = tmp_path_factory.mktemp("ed5")
    out = folder / "report.json"
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(folder)
        code = ed6.main(["j9main", "--edition", "5", "--rows", str(J5_ROWS), "--v0",
                         str(V0_MAIN), "--v0-sha256", V0_SHA256, "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))
    report["exit"] = code
    return report


def test_edition_5_reproduction_readings_1_to_3(ed5_report) -> None:
    """Judgement 5 2 and 3: 75 items / 72 pair items, L-b relative 5 / absolute 10, S8 F-5
    not applicable 20; the status stays failed (exit 1) and J-P3 passes on 200 judged rows."""
    report = ed5_report
    assert (report["vb_fail_items"], report["vb_fail_pair_items"]) == (75, 72)
    assert report["vb_fail_by_item"] == {"J1": 35, "J2": 31, "J4": 4, "J5": 4, "J3": 1}
    assert {(m["row"], m["gate"]) for m in report["reading_1_moved"]
            if m["setting"] == "VB"} == {("R15", "end_att")}
    assert (len(report["L-b"]), len(report["L-b_absolute"])) == (5, 10)
    assert len(report["S8"]["not_applicable_harness"]) == 20
    assert report["S8"]["not_judgeable"] == [] and report["not_judgeable_items"] == []
    baseline = report["baseline_failures"]
    assert baseline["counted"] == 0 and baseline["record_count"] == 30
    assert baseline["failure_item_units"] == 14  # + R15 J2 2 of the worsening rule = 16
    assert report["J-P3"]["status"] == "pass" and report["J-P3_judged_rows"] == 200
    assert report["status"] == "failed" and report["exit"] == ed6.EXIT_FAILED
    basis = report["status_basis"]
    assert basis["failures"] == ["VB J1 .. J11 (pair items): 72", "L-b (relative): 5"]
    assert basis["setting_defects"] == [] and basis["not_judgeable"] == []


# ------------------------------------------------------------------------------- reading (1)
def _event_rows(base_gates: list[str], on_gates: list[str]) -> tuple[dict, dict]:
    base = {"row": "R12", "phase": "offset 0.0", "gates": base_gates}
    table = {"VB": {"items": [{"row": "R12", "phase": "offset 0.0", "item": "J1", "kind": "fail",
                               "detail": f"gate {gate}", "base_other_phase_has_it": False}
                              for gate in on_gates if gate not in base_gates],
                    "no_reference": []}}
    return {"V0": [base]}, table


@pytest.mark.parametrize(("base_gates", "on_gates", "expected"), [
    (["Fmin_after_W"], ["Fmin_after_W", "end_att"], {"end_att": "record"}),
    (["U832_pair_union"], ["U832_pair_union", "fault0"], {"fault0": "record"}),
    (["U832_pair_union"], ["U832_pair_union", "Fmin_after_event"],
     {"Fmin_after_event": "record"}),
    (["Fmin_after_W"], ["Fmin_after_W", "no_lift"], {"no_lift": "fail"}),
    (["Fmin_after_W"], ["Fmin_after_W", "U57_outside"], {"U57_outside": "fail"}),
    ([], ["end_att"], {"end_att": "fail"}),  # V0 passes J1: the new gate is a J1 failure
])
def test_reading_1_maps_new_gates_on_a_v0_j1_failure(base_gates, on_gates, expected) -> None:
    rows_by, table = _event_rows(base_gates, on_gates)
    moved = ed6.apply_reading_1(table, rows_by, "V0")
    kinds = {item["detail"][5:]: item["kind"] for item in table["VB"]["items"]}
    assert kinds == expected
    assert len(moved) == sum(kind == "record" for kind in expected.values())
    for entry in moved:
        assert entry["judged_by"] == list(ed6.GATE_ITEMS[entry["gate"]])


def test_pair_items_count_j1_once_per_pair() -> None:
    items = [{"row": "R12", "phase": "a", "item": "J1", "kind": "fail"},
             {"row": "R12", "phase": "a", "item": "J1", "kind": "fail"},
             {"row": "R12", "phase": "a", "item": "J2", "kind": "fail"},
             {"row": "R12", "phase": "b", "item": "J1", "kind": "record"}]
    assert ed6.pair_items(items) == [("R12", "a", "J1"), ("R12", "a", "J2")]


# ------------------------------------------------------------------------------- reading (3)
def _s8_rows(setting_chunks: int, v0_chunks: int, margin=None) -> dict:
    def row(setting, chunks, value):
        return {"setting": setting, "row": "S8", "phase": "eps 0.0", "sa4": None,
                "soil_stop_crawler": {"after_stop_chunks": chunks, "margin_at_stop_kN": value,
                                      "max_after_stop_kN": value}}

    return {"V0": [row("V0", v0_chunks, None)], "VB": [row("VB", setting_chunks, margin)]}


@pytest.mark.parametrize(("chunks", "v0_chunks", "margin", "groups"), [
    (0, 0, None, {"not_applicable_harness"}),
    (0, 3, None, {"not_judgeable"}),
    (2, 0, None, {"not_judgeable"}),
    (2, 2, -7.5, {"stops", "f5_records"}),
    (2, 2, -1.0, {"f5_records"}),
])
def test_reading_3_s8_without_post_stop_samples(monkeypatch, chunks, v0_chunks, margin,
                                                groups) -> None:
    import judge_stage1_4368 as path1

    monkeypatch.setattr(path1, "sa4_items", lambda row: {"state": "pass", "items": {}})
    found = ed6.s8_items(_s8_rows(chunks, v0_chunks, margin), ("VB",))
    assert {name: len(values) for name, values in found.items() if values} == dict.fromkeys(
        groups, 1)


# ------------------------------------------------------------------------------- identity
@pytest.fixture(scope="module")
def sealed_settings() -> dict:
    return ed6.sealed_lsb_settings()


def test_sealed_lsb_settings_equal_a_vbl_run_record(sealed_settings) -> None:
    """6.1 (M-6): the expected ``lsb_settings`` are those a VBL run of ac3c25a7 wrote (the
    755a15d8 12a check run, controller blobs of ac3c25a7)."""
    path = next(PRELOCK_T4H.glob("*.npz"))
    with np.load(path, allow_pickle=False) as data:
        meta = json.loads(str(data["meta_json"]))
    assert meta["lsb_settings"] == sealed_settings
    assert sealed_settings["components"] == SEALED


def _ed6_row(settings: dict, **changes) -> dict:
    row = {"controller_tag": ed6.ED6_TAG, "run_extend_start_revision": 6,
           "hydraulic_options": dict.fromkeys(("extend_start_tracked", "extend_start_hold",
                                               "extend_start_witness"), True),
           "hydraulics_record": {"extend_bound_check": {"rule_revision": 6,
                                                        "spec_edition": "fe6f5844"}},
           "lsb_components": list(SEALED), "lsb_settings": copy.deepcopy(settings)}
    row.update(changes)
    return row


def test_ed6_identity(sealed_settings) -> None:
    assert ed6.ed6_identity_problems(_ed6_row(sealed_settings), sealed_settings) == []
    reordered = _ed6_row(sealed_settings, lsb_components=["B3", "A_i", "A_ii"])
    assert ed6.ed6_identity_problems(reordered, sealed_settings) == []
    for components in (["A_i", "A_ii"], ["A_i", "A_ii", "B3", "B3"], ["A_i", "A_ii", "B1"]):
        row = _ed6_row(sealed_settings, lsb_components=components)
        assert ed6.ed6_identity_problems(row, sealed_settings), components
    changed = copy.deepcopy(sealed_settings)
    changed["b3_travel_cap_fraction"] = 0.07
    assert ed6.ed6_identity_problems(_ed6_row(sealed_settings, lsb_settings=changed),
                                     sealed_settings)
    wrong_tag = _ed6_row(sealed_settings, controller_tag="final_C4G2_P3W_LAS_K1")
    assert any("is not final_C4G2_P3W_LAS_K1_LSB" in p for p in ed6.ed6_identity_problems(
        wrong_tag, sealed_settings))
    head_only = _ed6_row(sealed_settings, hydraulics_record={"extend_bound_check": None})
    assert ed6.ed6_identity_problems(head_only, sealed_settings) == []
    off = _ed6_row(sealed_settings, controller_tag=ed6.ED6_P3_OFF_TAG)
    assert ed6.ed6_identity_problems(off, sealed_settings, p3_on=False) == []
    assert ed6.ed6_identity_problems(_ed6_row(sealed_settings), sealed_settings, p3_on=False)


def test_jp3_settings_of_edition_6() -> None:
    for setting in ("VBL", "LSL1", "LSL4", "VBKL", *ed6.SENSITIVITY_SETTINGS):
        assert setting in j_p3_inputs.REV5_JUDGED_SETTINGS, setting
        assert j_p3_inputs.is_p3_expected(None, setting), setting
    for setting in ("VBL0", "VBKL0"):
        assert not j_p3_inputs.is_p3_expected(ed6.ED6_P3_OFF_TAG, setting), setting


@pytest.mark.parametrize(("judged", "expected", "defects", "unjudged"), [
    (200, 200, [], []), (199, 200, ["J-P3 judged rows 199 != 200"], []),
    (0, 200, [], ["J-P3 0 judged rows"]), (5, None, [], [])])
def test_jp3_basis_counts_the_judged_rows(judged, expected, defects, unjudged) -> None:
    jp3 = {"status": "pass", "status_by_revision": {"4": "no_p3_runs", "6": "pass"},
           "rev6": {"status": "pass", "runs_judged": judged, "runs_with_breach": 0}}
    assert ed6.jp3_basis(jp3, expected) == ([], defects, unjudged)


# ------------------------------------------------------------------------------- J7 exception
def _j7_table(setting: str, names: list[str]) -> dict:
    return {setting: {"items": [{"row": "R12", "phase": "top|FL|8|0.0", "item": "J7",
                                 "kind": "fail", "detail": name,
                                 "base_other_phase_has_it": False} for name in names],
                      "no_reference": []}}


@pytest.mark.parametrize(("setting", "names", "is_exempt"), [
    ("VBLv15", ["WARN_PROBE_STIFFNESS_OUT_OF_RANGE"], True),
    ("VBLc005", ["WARN_PROBE_STIFFNESS_OUT_OF_RANGE:2.468"], True),
    ("VBLv15", ["WARN_PROBE_STIFFNESS_OUT_OF_RANGE", "WARN_LIFT_STROKE_LIMITED"], False),
    ("VBLv15", ["WARN_PROBE_STIFFNESS_OUT_OF_RANGE", "FAULT_STROKE_END"], False),
    ("VBLv15", ["WARN_PROBE_STIFFNESS_OUT_OF_RANGE",
                "WARN_ROD_PRESSURE_FALLBACK at period 12"], False),
    ("VBL", ["WARN_PROBE_STIFFNESS_OUT_OF_RANGE"], False),
    ("LSL1", ["WARN_PROBE_STIFFNESS_OUT_OF_RANGE"], False),
    ("VBKL", ["WARN_PROBE_STIFFNESS_OUT_OF_RANGE"], False),
])
def test_j7_stiffness_exception_single_condition(setting, names, is_exempt) -> None:
    table = _j7_table(setting, names)
    events = [(42.5, "WARN_PROBE_STIFFNESS_OUT_OF_RANGE:2.468")]
    rows_by = {setting: [{"row": "R12", "phase": "top|FL|8|0.0", "events_full": events}]}
    records = ed6.apply_j7_exception(table, rows_by, ())
    kinds = {item["kind"] for item in table[setting]["items"]}
    assert kinds == ({"record"} if is_exempt else {"fail"})  # never one name left out
    if is_exempt:
        (record,) = records
        assert record["exempt_applied"] and record["count"] == 1
        assert record["events"] == [{"t_s": 42.5, "phase": None, "raw_ratio": 2.468}]
    else:
        assert records == []


def test_cluster_rule_k_2() -> None:
    units = [("VBLc04", "R12", p) for p in "abcd"] + [("VBLc04", "R16", p) for p in "ab"] + [
        ("VBLv05", "S1", p) for p in "ab"] + [("VBLv15", "S4", "a")]
    two_in_a_row = {("VBLc04", "R12", "a"): ["x"], ("VBLc04", "R12", "b"): ["x"]}
    assert ed6.cluster_rule(two_in_a_row, units)["is_failed"]
    singles = {("VBLc04", "R12", "a"): ["x"], ("VBLc04", "R16", "a"): ["x"]}
    assert not ed6.cluster_rule(singles, units)["is_failed"]
    three = {**singles, ("VBLv05", "S1", "b"): ["x"]}
    result = ed6.cluster_rule(three, units)
    assert result["single_failures"] == 3 and result["is_failed"]
    assert not ed6.cluster_rule({}, units)["is_failed"]


# ------------------------------------------------------------------------------- key files
@pytest.mark.parametrize("name", sorted(ed6.SEALED_KEY_FILES))
def test_sealed_key_files_load(name) -> None:
    document, sealed = ed6.load_key_file(KEYS / name)
    assert len(document["lines"]) == sealed[1]
    assert run_v5.ED6_KEY_FILE_SHA256[name] == sealed[0]
    jobs = run_v5.ed6_key_jobs(KEYS / name)
    assert len(jobs) == sealed[1]


def test_key_file_refusals(tmp_path) -> None:
    copy_path = tmp_path / "sens_keys_v2.json"
    copy_path.write_bytes((KEYS / "sens_keys_v2.json").read_bytes() + b" ")
    with pytest.raises(ed6.NotJudgeable, match="not a sealed key file"):
        ed6.load_key_file(copy_path)
    with pytest.raises(ed6.NotJudgeable):
        ed6.load_key_file(KEYS / "sens_keys.json")  # v1: never used (6.2)
    with pytest.raises(SystemExit):
        run_v5.ed6_key_jobs(copy_path)


def test_missing_and_extra_lines_are_not_judgeable() -> None:
    document = json.loads((KEYS / "sens_keys_v2.json").read_text(encoding="utf-8"))
    rows = [{"job": line["job"]} for line in document["lines"]]
    assert len(ed6.matched_lines(document, rows)) == 184
    with pytest.raises(ed6.NotJudgeable, match="line problems"):
        ed6.matched_lines(document, rows[1:])
    with pytest.raises(ed6.NotJudgeable, match="line problems"):
        ed6.matched_lines(document, [*rows, {"job": {**rows[0]["job"], "eps": 9.0}}])
    with pytest.raises(ed6.NotJudgeable, match="line problems"):
        ed6.matched_lines(document, [{**rows[0], "error": "x"}, *rows[1:]])


def test_edition_6_j9_main_batch() -> None:
    jobs = run_v5.ed6_j9_main_jobs()
    assert len(jobs) == 388
    counts = {s: sum(job["setting"] == s for job in jobs) for s in ed6.SETTING_MAPS[6]}
    assert counts == {"VBL": 100, "LSL1": 72, "LSL2": 72, "LSL3": 72, "LSL4": 72}
    assert run_v5.batch_jobs(run_v5.ED6_J9_MAIN_BATCH) == jobs


def test_j9main_missing_line_is_not_judgeable(tmp_path, monkeypatch, capsys) -> None:
    rows = tmp_path / "rows.jsonl"
    rows.write_text("".join(json.dumps({"job": job}) + "\n"
                            for job in run_v5.ed6_j9_main_jobs()[1:]), encoding="utf-8")
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    out = tmp_path / "r.json"
    code = ed6.main(["j9main", "--edition", "6", "--rows", str(rows), "--v0", str(V0_MAIN),
                     "--v0-sha256", V0_SHA256, "--out", str(out)])
    assert code == ed6.EXIT_STOP
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["status"] == "not_judgeable" and "1 missing" in report["reason"]
    assert ed6.main(["j9main", "--edition", "6", "--rows", str(rows), "--v0", str(V0_MAIN),
                     "--v0-sha256", V0_SHA256, "--out", str(out)]) == ed6.EXIT_STOP


# ------------------------------------------------------------------------------- grid (나)
def _grid_rows(document: dict, edit=None) -> list[dict]:
    rows = []
    for line in document["lines"]:
        event = {"pass": True, "gates": {"fault0": True}, "fault_periods": 0,
                 "fault_events": [], "warnings": []}
        row = {"job": dict(line["job"]), "event_output": event, "events": []}
        if edit is not None:
            edit(line, row)
        rows.append(row)
    return rows


@pytest.fixture()
def grid_judge(monkeypatch, tmp_path):
    """``judge_grid`` on synthetic VBL grid lines against the stored V0 grid (J-P3 and the
    identity mocked; their rules are tested above)."""
    monkeypatch.setattr(ed6, "jp3_basis", lambda jp3, expected: ([], [], []))
    monkeypatch.setattr(ed6, "ed6_identity_problems", lambda row, expected, **_: [])
    monkeypatch.setattr(ed6, "jp3_judged_rows", lambda jp3: 192)
    monkeypatch.setattr(ed6, "sealed_lsb_settings", lambda: {})
    monkeypatch.setattr(ed6.base, "j_p3_rows", lambda rows, folders: [])
    document = json.loads((KEYS / "confirm_b_grid192.json").read_text(encoding="utf-8"))

    def run(edit=None) -> dict:
        rows = tmp_path / f"grid_{len(list(tmp_path.iterdir()))}.jsonl"
        rows.write_text("".join(json.dumps(row) + "\n" for row in _grid_rows(document, edit)),
                        encoding="utf-8")
        return ed6.judge_grid(KEYS / "confirm_b_grid192.json", rows, MAIN_CHECKOUT)

    return document, run


def _fail_lines(document: dict, count: int, *, opportunity: bool):
    chosen = [line["t4h_file"] for line in document["lines"]
              if bool(line["v0_pair"]["v0_pass"]) is opportunity][:count]

    def edit(line, row):
        if line["t4h_file"] in chosen:
            row["event_output"]["pass"] = False
            row["event_output"]["gates"]["U832_pair_union"] = False

    return edit


def test_grid_opportunity_allowance_fault_and_warn(grid_judge) -> None:
    document, run = grid_judge
    report = run()
    assert (report["status"], report["opportunities"], report["lines"]) == ("pass", 174, 192)
    assert run(_fail_lines(document, 1, opportunity=True))["status"] == "pass"
    assert run(_fail_lines(document, 2, opportunity=True))["status"] == "failed"
    assert run(_fail_lines(document, 18, opportunity=False))["status"] == "pass"

    def warn(line, row):
        row["event_output"]["warnings"] = ["WARN_PROBE_STIFFNESS_OUT_OF_RANGE:2.4"]

    warned = run(warn)
    assert warned["status"] == "pass" and len(warned["warn_records"]) == 192  # never judged
    first_v0_fail = next(line["t4h_file"] for line in document["lines"]
                         if not line["v0_pair"]["v0_pass"])

    def fault(line, row):
        if line["t4h_file"] == first_v0_fail:
            row["event_output"]["fault_periods"] = 3

    faulted = run(fault)
    assert faulted["status"] == "failed" and faulted["fault_lines"][0]["line"] == first_v0_fail


def test_fault_reasons() -> None:
    row = {"event_output": {"fault_periods": 0, "fault_events": [], "gates": {"fault0": True}},
           "events": [[1.0, "WARN_X"], [2.0, "INFO_ROD_PRESSURE_FAULT_REASON"]]}
    assert ed6.fault_reasons(row) == []
    row["events"].append([3.0, "FAULT_STROKE_END:FL"])
    row["event_output"]["gates"]["fault0"] = False
    assert ed6.fault_reasons(row) == ["gate fault0", "event FAULT_STROKE_END"]


# ------------------------------------------------------------------------------- 12b (Y-10)
@pytest.fixture()
def world6(tmp_path):
    noise = tmp_path / "noise.json"
    sha = tools12b.write_noise(noise)
    scan = tmp_path / "scan"
    scan.mkdir()
    import jp3_12b_plan as plan

    out = tmp_path / "plans"
    document = plan.select(noise, scan, out, noise_sha256=sha, edition=6)
    runs = tmp_path / "runs"
    runs.mkdir()
    selection = out / "selection.json"
    return {"runs": runs, "plans": out, "selection": selection,
            "selection_sha": hashlib.sha256(selection.read_bytes()).hexdigest(),
            "doc": document}


def _ed6_arm_edit(settings: dict, edit=None):
    def apply(block, vbk0, vbk):
        for row in vbk0.rows.values():
            row.update(controller_tag=ed6.ED6_P3_OFF_TAG, lsb_components=list(SEALED),
                       lsb_settings=copy.deepcopy(settings))
        for row in vbk.rows.values():
            row.update(controller_tag=ed6.ED6_TAG, lsb_components=list(SEALED),
                       lsb_settings=copy.deepcopy(settings))
        if edit is not None:
            edit(block, vbk0, vbk)

    return apply


def _run12b(args: list[str], capsys) -> tuple[int, dict]:
    code = judge12b6.main(args)
    capsys.readouterr()
    out = Path(args[args.index("--out") + 1])
    return code, json.loads(out.read_text(encoding="utf-8"))


def _stall(rank: int):
    def edit(block, vbk0, vbk):
        if block == "b1":
            vbk0.rows[vbk0.key_at(rank)]["base"]["t_ready_s"] = None
            vbk.rows[vbk.key_at(rank)]["base"]["t_ready_s"] = None

    return edit


def test_12b_ed6_decide_uses_p_pred_and_judge_rechecks_it(world6, capsys, tmp_path,
                                                          monkeypatch, sealed_settings) -> None:
    monkeypatch.chdir(tmp_path)
    with judge12b6.edition_6():
        written0, written1 = tools12b.build(world6, edit=_ed6_arm_edit(sealed_settings,
                                                                         _stall(0)))
    decision = world6["runs"] / "decision.json"
    code, record = _run12b(tools12b.decide_args(world6, written0, decision, expect=False),
                           capsys)
    assert code == 0 and record["status"] == "decided", record.get("reason")
    p_pred = record["p_pred"]
    assert record["allow_k"] == p_pred["k_allow"] and record["allow_k"] not in (None,)
    assert p_pred["p_pred_seed"] == 20261125 and (p_pred["n_par"], p_pred["n_rep"]) == (20000,
                                                                                         10)
    assert p_pred["K_c"]["tau_C"] + p_pred["K_c"]["tau_R"] == 1
    assert p_pred["blocks_used"] == ["b1", "b2"]
    assert p_pred["p_n23_gt_k"] <= ppred.ALPHA < p_pred["p_n23_gt_k_minus_1"]
    assert judge12b.SETTING_OF_ARM == {"vbk0": "VBK0", "vbk": "VBK"}  # restored
    out = world6["runs"] / "judge.json"
    code, report = _run12b(tools12b.judge_args(world6, written0, written1, decision, out),
                           capsys)
    assert code == 0 and report["status"] == "pass", report.get("problems")
    assert report["ready_rule"]["allow_k"] == record["allow_k"]
    assert report["p_pred_recomputed"] == p_pred
    tau_r = sum(1 for row in world6["doc"]["cell_table"] if row["phase"] == "tau_R")
    assert sum(report["tau_r_trigger_phase_all"].values()) == tau_r * 2
    edited = json.loads(decision.read_text(encoding="utf-8"))
    edited["allow_k"] = edited["p_pred"]["k_allow"] = 7  # the edition 5 fixed value
    other = world6["runs"] / "decision_7.json"
    other.write_text(json.dumps(edited), encoding="utf-8")
    code, report = _run12b(tools12b.judge_args(world6, written0, written1, other,
                                               world6["runs"] / "judge7.json"), capsys)
    assert code == judge12b.EXIT_NOT_JUDGEABLE
    assert any("P-pred" in text for text in report["problems"]["not_judgeable"])


def test_12b_ed6_identity_defects(world6, capsys, tmp_path, monkeypatch,
                                  sealed_settings) -> None:
    monkeypatch.chdir(tmp_path)

    def wrong(block, vbk0, vbk):
        vbk0.rows[vbk0.key_at(3)]["lsb_components"] = ["A_i", "A_ii"]

    with judge12b6.edition_6():
        written0, _ = tools12b.build(world6, edit=_ed6_arm_edit(sealed_settings, wrong))
    code, record = _run12b(tools12b.decide_args(world6, written0, world6["runs"] / "d.json",
                                                expect=False), capsys)
    assert code == judge12b.EXIT_NOT_JUDGEABLE and record["status"] == "setting_defect"

    def old_tag(block, vbk0, vbk):
        vbk.rows[vbk.key_at(5)]["controller_tag"] = "final_C4G2_P3W_LAS_K1"

    world6["runs"] = world6["runs"] / "second"
    world6["runs"].mkdir()
    with judge12b6.edition_6():
        written0, written1 = tools12b.build(world6, edit=_ed6_arm_edit(sealed_settings,
                                                                         old_tag))
    decision = world6["runs"] / "d2.json"
    _run12b(tools12b.decide_args(world6, written0, decision, expect=False), capsys)
    code, report = _run12b(tools12b.judge_args(world6, written0, written1, decision,
                                               world6["runs"] / "j2.json"), capsys)
    assert report["status"] == "setting_defect"
    assert any("final_C4G2_P3W_LAS_K1_LSB" in text
               for text in report["problems"]["setting_defects"])


# ------------------------------------------------------------------------------- sens units
@pytest.fixture()
def sens_judge(monkeypatch, tmp_path):
    """``judge_sens`` over the sealed ``sens_keys_v2.json`` with the per-unit tables mocked:
    ``failing`` (setting, key) units get one J2 failure; the rest of the pipeline is real."""
    document = json.loads((KEYS / "sens_keys_v2.json").read_text(encoding="utf-8"))
    rows_path = tmp_path / "rows.jsonl"
    rows_path.write_text("".join(json.dumps({"job": line["job"]}) + "\n"
                                 for line in document["lines"]), encoding="utf-8")
    unit_of = {run_v5.job_key(line["job"]): (line["job"]["setting"], line["key"])
               for line in document["lines"]}
    monkeypatch.setattr(ed6.base, "stored_v0_rows", lambda path, sha: [])
    monkeypatch.setattr(ed6, "metric_rows", lambda rows, folders, mapping: [
        {"setting": unit_of[run_v5.job_key(row["job"])][0], "row": "row",
         "phase": unit_of[run_v5.job_key(row["job"])][1]} for row in rows])
    monkeypatch.setattr(ed6, "s8_items", lambda rows_by, settings: {
        "failures": [], "stops": [], "not_judgeable": []})
    monkeypatch.setattr(ed6, "jp3_basis", lambda jp3, expected: ([], [], []))
    monkeypatch.setattr(ed6, "jp3_judged_rows", lambda jp3: 104)
    monkeypatch.setattr(ed6, "ed6_identity_problems", lambda row, expected, **_: [])
    monkeypatch.setattr(ed6, "sealed_lsb_settings", lambda: {})
    monkeypatch.setattr(ed6.base, "j_p3_rows", lambda rows, folders: [])

    def run(failing: set[tuple[str, str]]) -> dict:
        def full_items(rows_by, settings, reference):
            return {setting: {"runs": 1, "no_reference": [], "items": [
                {"row": "row", "phase": key, "item": "J2", "kind": "fail", "detail": "F",
                 "base_other_phase_has_it": False}
                for s, key in sorted(failing) if s == setting]} for setting in settings}

        monkeypatch.setattr(ed6.base, "_full_items", full_items)
        return ed6.judge_sens(KEYS / "sens_keys_v2.json", rows_path, V0_MAIN, V0_SHA256)

    probe = sorted((line["job"]["setting"], line["key"]) for line in document["lines"]
                   if line["probe_seen"])
    judged = sorted((line["job"]["setting"], line["key"]) for line in document["lines"]
                    if not line["probe_seen"])
    return run, probe, judged


def test_sens_probe_units_stop_and_cluster_rule(sens_judge) -> None:
    run, probe, judged = sens_judge
    assert (len(probe), len(judged)) == (32, 152)
    report = run(set())
    assert report["status"] == "pass" and report["probe_units"] == 32
    stopped = run({probe[0]})
    assert stopped["status"] == "failed" and stopped["probe_unit_stops"]
    assert run({judged[0]})["status"] == "pass"
    singles = [unit for unit in judged if unit[1].startswith(("S4_", "S7_", "R16_"))]
    rows = {}
    for unit in singles:
        rows.setdefault((unit[0], unit[1].split("_", 1)[0]), unit)
    three = set(list(rows.values())[:3])
    assert run(three)["status"] == "failed"
