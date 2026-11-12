"""Unit tests of the 436.8 path 1 new judge versions (rules rev5 R5-A1, synthetic inputs)."""

from __future__ import annotations

import ast
import hashlib
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import d1_judge_4368 as d1j  # noqa: E402
import judge4368_common as common  # noqa: E402
import judge_stage1_4368 as s1  # noqa: E402
import las_t3_judge_4368 as t3j  # noqa: E402
import u3_judge_4368 as u3j  # noqa: E402
import u9_judge_4368 as u9j  # noqa: E402


# ------------------------------------------------------------------------------------ common
def test_seal_report_flags_a_changed_rule_file(tmp_path):
    for name, sha in common.SEALED_RULES:
        (tmp_path / name).write_bytes(b"x")
        (tmp_path / name).with_suffix(".sha256").write_text(f"{sha}  {name}\n", encoding="utf-8")
    report = common.seal_report(tmp_path)
    assert report["stop_S1"] and len(report["problems"]) == len(common.SEALED_RULES)


def test_definition_change_numbers_cover_d01_to_d25():
    assert sorted(common.DEFINITION_CHANGES) == [f"D-{n:02d}" for n in range(1, 26)]
    used = {
        *u3j.DEFINITION_CHANGES,
        *s1.DEFINITION_CHANGES,
        *u9j.DEFINITION_CHANGES,
        *t3j.DEFINITION_CHANGES,
        *d1j.DEFINITION_CHANGES,
    }
    assert used == set(common.DEFINITION_CHANGES) - {"D-19"}  # H-6 judge not yet written


def test_allowance_comparisons():
    assert common.is_at_least(common.F_MIN_N - 1e-10, common.F_MIN_N)
    assert not common.is_at_least(9414.5, common.F_MIN_N)
    assert not common.is_above(5.0 + 5e-10, 5.0) and common.is_above(5.0 + 2e-9, 5.0)


# ----------------------------------------------------------------------------- U-3 settle v2
def _settle_block(**changes):
    inputs = {
        "table": None,
        "table_sha256": None,
        "table_key": "k",
        "pad_xy_m": [[1.0, 2.0], [1.0, -2.0], [-1.0, 2.0], [-1.0, -2.0]],
        "pen_inst_mm": [-10.0, -10.0, -10.0, -10.0],
        "d_attitude_deg": [0.0, 0.0],
        "gap_target_mm": [10.0, 10.0, 10.0, 10.0],
        "gap_target_source": "table",
        "table_gap_target_mm": [10.0, 10.0, 10.0, 10.0],
        "residual_deg": [0.001, 0.0],
        "attitude_error_deg": [0.004, 0.001],
    }
    inputs.update(changes)
    result = u3j.recompute_settle_v2(inputs)
    return {
        "status": "checked",
        "inputs": inputs,
        "result": {**result, "gate": "judged"},
        "tolerances": dict(u3j.RECORDED_TOLERANCES),
    }


@pytest.fixture
def table_file(tmp_path):
    path = tmp_path / "table.json"
    path.write_text("{}", encoding="utf-8")
    return path


def _with_table(block, path):
    block["inputs"]["table"] = str(path)
    block["inputs"]["table_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return block


def test_settle_v2_units_rad_and_mm():
    inputs = _settle_block(d_attitude_deg=[0.01, 0.0])["inputs"]
    pen = u3j.recompute_settle_v2(inputs)["pen_mean_mm"]
    assert pen[0] == pytest.approx(-10.0 + 2000.0 * math.radians(0.01))


def test_settle_v2_states(table_file):
    sha = {}
    assert u3j.assess_settle_v2(_with_table(_settle_block(), table_file), sha)["state"] == "ok"
    failing = _with_table(_settle_block(pen_inst_mm=[-12.0, -10.0, -10.0, -10.0]), table_file)
    assert u3j.assess_settle_v2(failing, sha)["state"] == "fail"
    tampered = _with_table(_settle_block(), table_file)
    tampered["result"]["ok"] = False
    assert u3j.assess_settle_v2(tampered, sha)["state"] == "not_judgeable"
    assert u3j.assess_settle_v2(None, sha)["state"] == "not_judgeable"
    assert u3j.assess_settle_v2({"status": "error"}, sha)["state"] == "not_judgeable"
    assert u3j.assess_settle_v2({"status": "no_table_check"}, sha)["state"] == "not_applicable"
    record_only = _with_table(_settle_block(), table_file)
    record_only["result"]["gate"] = "record_only"
    assert u3j.assess_settle_v2(record_only, sha)["state"] == "record_only"


def test_settle_v2_source_and_tolerance_checks(table_file):
    sha = {}
    wrong_sha = _with_table(_settle_block(), table_file)
    wrong_sha["inputs"]["table_sha256"] = "0" * 64
    assert u3j.assess_settle_v2(wrong_sha, sha)["state"] == "not_judgeable"
    wrong_target = _with_table(
        _settle_block(table_gap_target_mm=[9.0, 10.0, 10.0, 10.0]), table_file
    )
    assert u3j.assess_settle_v2(wrong_target, sha)["state"] == "not_judgeable"
    tolerance = _with_table(_settle_block(), table_file)
    tolerance["tolerances"]["gap_mm"] = 1.5
    assert u3j.assess_settle_v2(tolerance, sha)["tolerance_problems"]


def test_start_gap_records_the_table_target_outcome(table_file):
    block = _with_table(
        _settle_block(
            gap_target_mm=[12.0, 10.0, 10.0, 10.0],
            pen_inst_mm=[-12.0, -10.0, -10.0, -10.0],
            gap_target_source="start_gap",
        ),
        table_file,
    )
    found = u3j.assess_settle_v2(block, {})
    assert found["state"] == "ok" and found["start_gap_table_ok"] is False


def test_study_d_grade_uses_rows_verdict(table_file):
    bundle = next(b for b in u3j.BUNDLES if b.name == "D")
    entry = {
        "verdict": "settle_check_fail",
        "verdict_rows": "pass",
        "rows": {},
        "settle_v2": _with_table(_settle_block(), table_file),
    }
    assert u3j.grade(entry, bundle, {})["grade"] == "pass"


def test_reuse_check_counts_and_uniqueness():
    payload = {"meta": {"v5": {"reuse_d1": {"slope": {"reused": ["a", "b"]}}}}}
    items = [{"id": "a", "reuse": "d1", "d1_key": "k1"}, {"id": "b", "reuse": "d1", "d1_key": "k2"}]
    assert u3j.reuse_check(payload, items, "slope", {"k1": 1, "k2": 1})["pass"]
    assert not u3j.reuse_check(payload, items, "slope", {"k1": 1, "k2": 2})["pass"]
    with pytest.raises(common.InputError):
        u3j.reuse_check(payload, items, "slope", None)


# ---------------------------------------------------------------------------------- stage 1
def _row(**changes):
    row = {
        "row": "R3",
        "phase": "eps 0",
        "group": "R3",
        "setting": "VB",
        "is_event": False,
        "class": "pass",
        "F_after": 20.0,
        "F_after_event": None,
        "F_after_W_min_kN": None,
        "t_ready": 50.0,
        "case_floor": [0.0, 0.0],
        "events_capped": False,
        "bad_436": [],
        "fallback_436": [],
        "lwa": None,
        "events_full": [],
        "sa4": None,
        "pressure": {},
        "p_move": 100.0,
        "gates": [],
    }
    row.update(changes)
    return row


def test_event_name_drops_numeric_segments_only():
    assert s1.event_name_436("FAULT_LIFT_STROKE_LIMIT:soil") == "FAULT_LIFT_STROKE_LIMIT:soil"
    assert s1.event_name_436("WARN_X:FL:12.5") == "WARN_X:FL"


def test_j1_safe_stop_move_is_a_record_and_s8_leaving_fails():
    base, on = _row(), _row(**{"class": "stroke_limited_stop"})
    assert [i["kind"] for i in s1.j1_items(base, on, [base])] == ["record"]
    assert s1.j1_items(base, _row(**{"class": "fail"}), [base])[0]["kind"] == "fail"
    s8 = _row(row="S8", **{"class": "pass"})
    assert s1.j1_items(_row(row="S8"), s8, [])[0]["kind"] == "fail"


def test_j2_uses_the_unrounded_f_min():
    base = _row(F_after=10.0)
    assert not s1.j2_items(base, _row(F_after=9.4146), [base])  # 9,414.6 N >= 9,414.589 N
    assert s1.j2_items(base, _row(F_after=9.4145), [base])


def test_j2_rigid_event_rows_use_e3():
    base = _row(row="R12", group="R12", is_event=True, F_after_W_min_kN=10.0, F_after_event=1.0)
    on = _row(row="R12", group="R12", is_event=True, F_after_W_min_kN=9.0, F_after_event=20.0)
    assert s1.j2_items(base, on, [base])


def test_j3_rigid_flag_limit_follows_the_floor():
    assert s1.j3_items(_row(), _row(t_ready=100.0))[0]["kind"] == "flag"
    assert not s1.j3_items(_row(), _row(t_ready=100.0, case_floor=[2.0, 0.0]))
    assert s1.j3_items(_row(), _row(case_floor=None))[0]["detail"].endswith("미정")


def test_j11_none_with_fallback_legs_is_not_judgeable():
    assert (
        s1.j11_items(_row(lwa={"n_late": None, "fallback_legs": ["FL"]}))[0]["kind"]
        == "not_judgeable"
    )
    assert s1.j11_items(_row(lwa={"n_late": None}))[0]["kind"] == "record"
    late = _row(setting="LS1", lwa={"n_late": 2, "n_late_fallback": 1, "fallback_legs": ["FL"]})
    assert "L-e" in s1.j11_items(late)[0]["detail"]


def test_order_131_reverse_fails_only_when_v0_keeps_order():
    def rows(setting, medians):
        return [
            _row(row=name, setting=setting, F_after=m + d)
            for name, m in zip(s1.ITEM8_ORDER, medians, strict=True)
            for d in (-0.1, 0.0, 0.1)
        ]

    found = s1.order_131(rows("V0", [1, 2, 3]) + rows("VB", [3, 2, 1]), [])
    assert found["V0"]["state"] == "순서 유지" and found["VB"]["state"] == "반대" and found["fail"]
    found = s1.order_131(rows("V0", [1, 2, 3]) + rows("VB", [2, 1, 3]), [])
    assert not found["fail"] and found["flag"]


def test_phase_scatter_and_p7():
    assert s1.phase_scatter([1.0, 1.1], [2.0, 2.1])["state"] == "구분됨"
    assert s1.phase_scatter([1.0, 2.0], [1.5, 1.4])["state"] == "위상 산포 안"
    rows = {
        "V0": [{"row": "R1", "phase": "p", "sha": "a"}],
        "L1": [{"row": "R1", "phase": "p", "sha": "a"}],
    }
    assert s1.p7(rows)["violation"]


def test_sa4_needs_every_record():
    row = _row(
        row="S8",
        t_ready=None,
        F_after=20.0,
        events_full=[
            (10.0, "WARN_LIFT_STROKE_LIMITED:FL"),
            (10.02, "FAULT_LIFT_STROKE_LIMIT:soil"),
        ],
        sa4={"lift_after_stop_ms": [0, 0, 0, 0]},
        pressure={"saturation_leg_chunks": 0},
    )
    assert s1.sa4_items(row)["state"] == "pass"
    assert s1.sa4_items({**row, "sa4": {}})["state"] == "판정 불가"


# ---------------------------------------------------------------------------------- U-9 H0
def test_h0_uses_the_h10_main_vb_line():
    u9 = [
        {
            "job": {"case": c, "eps": e, "setting": "VB", "eta_v": 0.85, "u9_metrics": True},
            "commands_sha256": "h",
        }
        for c, e in u9j.H0_KEYS
    ]
    main = [
        {"job": {"case": c, "eps": e, "setting": "VB"}, "commands_sha256": "h"}
        for c, e in u9j.H0_KEYS
    ]
    assert not u9j.h0(u9, main, None)["stop"]
    main[0]["commands_sha256"] = "other"
    assert u9j.h0(u9, main, None)["stop"]


# ------------------------------------------------------------------------------------- D-1
def _d1_line(items, preloc=None, path="g6"):
    d1 = {
        "key": "k|VB|e0",
        "row_key": "k",
        "eps": 0.0,
        "setting": "VB",
        "path": path,
        "verdict": "fail",
        "items": items,
        "t_ready_s": 40.0,
    }
    if preloc is not None:
        d1["g6_preloc"] = {"preloc_flag_ok": preloc}
    return {
        "job": {"d1": {"tags": []}},
        "d1": d1,
        "values": {"times": {"t_first_ready_s": 40.0, "t_check_start_s": 0.1}},
    }


def test_377_demotion_and_missing_f8():
    line = _d1_line({"G6-7_preloc": False, "READY": True}, preloc=True)
    grade = d1j.regrade(line)
    assert grade["verdict"] == "pass" and grade["demoted_items"][0]["flag"] == "P3-8_demoted"
    assert d1j.regrade(_d1_line({"G6-7_preloc": False}, preloc=False))["verdict"] == "fail"
    assert d1j.regrade(_d1_line({"G6-7_preloc": False}))["problems"]


def test_ready_origin_checks():
    line = _d1_line({"READY": True})
    line["values"]["times"]["t_check_start_s"] = 0.2
    assert d1j.ready_origin_problems(line)
    line = _d1_line({"READY": True})
    line["d1"]["t_ready_s"] = 41.0
    assert d1j.ready_origin_problems(line)


# --------------------------------------------------------------------------------------- T-3K
def test_dg3_folder_comes_from_the_record():
    assert t3j.recorded_folder({"extend_start_rule": "tracked_bound"}) == "v4_on"
    assert t3j.recorded_folder({"extend_start_rule": "constant"}) == "off"


def test_k6_allowance_installed():
    limits = t3j.install_allowance()
    assert limits["READY_INCREASE_LIMIT_S"] == pytest.approx(5.0 + 1e-9, abs=0)


def test_identity_rows_on_a_d8x_style_sidecar():
    record = {
        "git": {"head": "abc123", "is_clean": True, "status_porcelain": ""},
        "threads": {
            "MKL_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "NUMBA_NUM_THREADS": "1",
            "MKL_THREADING_LAYER": "TBB",
        },
    }
    found = t3j.identity_rows({"start": [record], "end": [record]}, "abc123", None)
    assert found["rows"]["head"]["state"] == "pass"
    assert found["rows"]["c2_sha256"]["state"] == "판정 불가"
    assert found["state"] == "판정 불가"


# --------------------------------------------------------------------- record-only runner code
def test_sa4_record_rejects_nan_after_the_stop():
    import verdict_runs as vr
    from harness_flow import COLUMN, COLUMNS, TRUE_FORCE

    rows = np.zeros((100, len(COLUMNS)))
    rows[:, COLUMN["t"]] = np.arange(100) * 1e-3
    rows[:, TRUE_FORCE] = 1000.0
    found = vr.sa4_record(rows, 500.0, [(0.05, "FAULT_LIFT_STROKE_LIMIT:soil")])
    assert found["rule"] == vr.SA4_RULE and found["lift_after_stop_ms"] == [0.0] * 4
    rows[10, TRUE_FORCE.start] = np.nan  # before the stop: not checked
    vr.sa4_record(rows, 500.0, [(0.05, "FAULT_LIFT_STROKE_LIMIT:soil")])
    rows[80, TRUE_FORCE.start] = np.nan
    with pytest.raises(ValueError):
        vr.sa4_record(rows, 500.0, [(0.05, "FAULT_LIFT_STROKE_LIMIT:soil")])


def _function(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


def test_command_hash_does_not_depend_on_the_record_fields():
    """The commands hash is taken from the period commands only; F-4 / F-8 are written into
    the finished result (record only), so they cannot change it."""
    finish = ast.unparse(_function(COUPLED / "verdict_runs.py", "_finish"))
    assert '_command_digest(period["command"])' in finish.replace("'", '"')
    execute = ast.unparse(_function(COUPLED / "d1_runs.py", "execute"))
    assert execute.index("PATH_RUNNERS[") < execute.index("d1_record(")


def test_g6_preloc_record_copies_the_r72_fields():
    import d1_runs

    harness = {
        "preloc_flag_ok": True,
        "preloc_starts": [{"leg": "FL", "t_s": 3.0, "true_min_kN": 12.0}],
    }
    found = d1_runs.g6_preloc_record(harness)
    assert found["preloc_flag_ok"] is True and found["preloc_starts"] == harness["preloc_starts"]
    found["preloc_starts"][0]["leg"] = "FR"
    assert harness["preloc_starts"][0]["leg"] == "FL"
