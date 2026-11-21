"""436.9 J-P3 narrow prelaunch re-audit (``prelaunch_j9/audit_prelaunch2.md``, 2026-11-21) and
the user decision appended to it (N-1 option 1, code):

* N-1: the r79 path keeps a ``LockWindowMismatchError`` as the run's error line
  (``r79_sensor_screen.v5_record_or_mismatch``); ``records`` reads it as the T-JR-14 failure
  (exit 1) and ``t12`` stops with exit 1 on it, not as not judgeable.
* N-3: an unexpected exception of any type is exit 3 in the four judge tools.
* N-4: a VB line of ``j9_t8`` with P4 evidence other than 1 = 0 makes T-JR-10 not judgeable
  with the "저장값 노후 확인 전" reason.
* R-b: the dry ``summarize`` records whether the r79 lines carry the T-JR-14 / 15 keys.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import jp3_baseline_compare as compare  # noqa: E402
import jp3_case_judge as case_judge  # noqa: E402
import jp3_dryrun_evidence as dryrun  # noqa: E402
import jp3_tjr_judge as tjr  # noqa: E402
from test_jp3_addendum_4a2 import (  # noqa: E402
    REPLAY_REPORTS,
    T4H_NAMES,
    _dg3_document,
    h6_keys,
    records_inputs,
    valid_lock_rows,
)
from test_jp3_addendum_4a3 import _t8_inputs  # noqa: E402

MISMATCH = "LockWindowMismatchError: stretch_mismatch [('FL', 1.0)], window max |diff| 0.1 s"
TIMEOUT_S = 600


# --- N-1: the r79 path ------------------------------------------------------------------------

SEAM_SCRIPT = """
import json
import sys
from types import SimpleNamespace

sys.path[:0] = [{s8!r}, {coupled!r}, {src!r}]
import os
os.environ["R79_V5_SETTING"] = "VB"
import harness_hydraulics
import lock_window_alignment
import r67_g1_screen as r67
import r79_sensor_screen as r79
import run_v5
import verdict_runs
from outrigger_sim.control.c2 import C2Config
from outrigger_sim.hydraulics.v5_options import HydraulicOptions

# the record wiring only (as test_r79_controller_tag.py): no plant is built
harness_hydraulics.check_last_lock_window = lambda *args, **kwargs: None
harness_hydraulics.check_last_extend_start = lambda *args, **kwargs: None
harness_hydraulics.last_armed_record = lambda *args, **kwargs: {{}}
r67.first_lift_time_s = lambda plant, period: None
r67._lift_and_lock_window = lambda plant, ctrl: (None, {{}})
r67.resume_k1_block = lambda ctrl: {{}}
verdict_runs.review_record_of = lambda ctrl: None
r79.j_p3_run_record = lambda record, periods: {{}}

options = HydraulicOptions.from_dict(run_v5.SETTINGS["VB"][1])
ctrl = SimpleNamespace(config=C2Config().with_10hz_d1(), events=[])
run = SimpleNamespace(ctrl=ctrl, adapter=None, controller_period_arrays=lambda: {{}})
plant = SimpleNamespace(lock_events=[])
r67.V5_JOB_RUN.update(plant=plant, ctrl=ctrl)
out = {{}}

verdict_runs.lock_window_record = lambda plant, ctrl, period: {{"n_late_fallback": 0}}
plain = r79._v5_record(options, run, plant)
seam = r79.v5_record_or_mismatch(options, run, plant)
out["same_without_error"] = plain == seam and "error" not in seam


def mismatch(plant, ctrl, period):
    raise lock_window_alignment.LockWindowMismatchError("stretch_mismatch [('FL', 1.0)]")


verdict_runs.lock_window_record = mismatch
out["mismatch"] = r79.v5_record_or_mismatch(options, run, plant)


def other(plant, ctrl, period):
    raise RuntimeError("another runtime error")


verdict_runs.lock_window_record = other
try:
    r79.v5_record_or_mismatch(options, run, plant)
    out["other"] = "not raised"
except RuntimeError as exc:
    out["other"] = str(exc)
print(json.dumps(out))
"""


def test_n1_r79_keeps_the_mismatch_as_the_error_line(tmp_path) -> None:
    pytest.importorskip("numba", reason="r67 / r79 import the harness (dynamics-dev)")
    script = tmp_path / "seam_check.py"
    script.write_text(SEAM_SCRIPT.format(s8=str(S8_DIR), coupled=str(COUPLED_DIR),
                                         src=str(ROOT / "03_src")), encoding="utf-8")
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "MKL_THREADING_LAYER": "TBB"}
    done = subprocess.run([sys.executable, "-I", "-B", str(script), str(ROOT)], cwd=ROOT,
                          env=environment, capture_output=True, text=True, timeout=TIMEOUT_S)
    assert done.returncode == 0, done.stderr[-2000:]
    out = json.loads(done.stdout.strip().splitlines()[-1])
    assert out["same_without_error"] is True  # no exception: the record as before
    assert out["mismatch"] == {"error": "LockWindowMismatchError: stretch_mismatch "
                                        "[('FL', 1.0)]"}
    assert out["other"] == "another runtime error"  # any other error still ends the run
    assert tjr.is_lock_window_mismatch(out["mismatch"])


# --- N-1: the judges --------------------------------------------------------------------------

def _mismatch_documents() -> list[dict]:
    files = [_dg3_document(setting="VBH"), _dg3_document(setting="VBJ")]
    line = files[1]["results"][7]
    line["error"] = MISMATCH
    line.pop("lock_window_alignment")
    return files


def test_n1_records_reads_the_mismatch_line_as_a_t_jr_14_failure() -> None:
    files = _mismatch_documents()
    lock_rows = valid_lock_rows()
    lock_rows[5 + 7] = json.loads(json.dumps(files[1]["results"][7]))  # its Dg-3 VBJ line
    report, problems = tjr.judge_records(records_inputs(lock_rows, dg3=files))
    assert problems.status() == compare.STATUS_FAILED, problems.as_dict()
    assert report["T-JR-14"]["VBJ"]["mismatch_error_lines"] == 1
    assert problems.not_judgeable == []


def test_n1_records_command_exit_1(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(tjr, "t4h_names_of", lambda paths: (T4H_NAMES, []))
    monkeypatch.setattr(tjr, "h6_keys_of", lambda path: (h6_keys(), []))
    files = _mismatch_documents()
    lock_rows = valid_lock_rows()
    lock_rows[5 + 7] = json.loads(json.dumps(files[1]["results"][7]))
    paths = []
    for name, document in (("r0", REPLAY_REPORTS[0]), ("r1", REPLAY_REPORTS[1]),
                           ("dg3_VBH", files[0]), ("dg3_VBJ", files[1])):
        paths.append(tmp_path / f"{name}.json")
        paths[-1].write_text(json.dumps(document), encoding="utf-8")
    rows = tmp_path / "rows.jsonl"
    rows.write_text("".join(json.dumps(row) + "\n" for row in lock_rows), encoding="utf-8")
    code = tjr.main(["records", "--out", str(tmp_path / "out.json"), "--replay", str(paths[0]),
                     str(paths[1]), "--dg3", str(paths[2]), str(paths[3]), "--lock-rows",
                     str(rows), "--t4h-sums", "unused", "--h6", "unused"])
    assert code == 1


@pytest.fixture
def pass_grades(monkeypatch):
    import h8_noise_judge_4368 as h8

    monkeypatch.setattr(h8, "grade_lines", lambda results, judge: {
        h8.plain_key(run["key"]): {"grade": h8.GRADE_PASS, "level": run["level"]}
        for run in results})


def test_n1_t12_mismatch_line_is_a_failure_not_not_judgeable(pass_grades) -> None:
    new = _dg3_document()
    new["results"][9]["error"] = MISMATCH
    report, problems = tjr.judge_t12("VBH", _dg3_document(setting="VB"), {}, new, {})
    assert problems.status() == compare.STATUS_FAILED, problems.as_dict()
    assert report["lock_window_mismatch_keys"] == ["L3|s0|h|9|inner"]
    assert any("T-JR-14 failure" in text for text in problems.failures)


@pytest.mark.parametrize("side", ["other_error_new", "mismatch_base"])
def test_n1_t12_other_error_lines_stay_not_judgeable(pass_grades, monkeypatch, side) -> None:
    monkeypatch.setattr(tjr, "_dg3_j_p3", lambda lines, problems: {"status": "pass"})
    base, new = _dg3_document(setting="VBJ0"), _dg3_document(setting="VBJ")
    if side == "other_error_new":
        new["results"][3]["error"] = "ValueError: x"
    else:
        base["results"][3]["error"] = MISMATCH
    _, problems = tjr.judge_t12("VBJ", base, {}, new, {})
    assert problems.status() == compare.STATUS_NOT_JUDGEABLE


def test_n1_t12_command_exit_1(tmp_path, pass_grades) -> None:
    new = _dg3_document()
    new["results"][9]["error"] = MISMATCH
    files = {"base": tmp_path / "base.json", "new": tmp_path / "new.json",
             "judge": tmp_path / "judge.json"}
    files["base"].write_text(json.dumps(_dg3_document(setting="VBJ0")), encoding="utf-8")
    for line in new["results"]:
        line["v5_setting"] = "VBJ"
    files["new"].write_text(json.dumps(new), encoding="utf-8")
    files["judge"].write_text("{}", encoding="utf-8")
    sha = compare.file_sha256(files["judge"])
    code = tjr.main(["t12", "--out", str(tmp_path / "out.json"), "--bundle", "VBJ", "--base",
                     str(files["base"]), "--base-judge", str(files["judge"]), "--new",
                     str(files["new"]), "--new-judge", str(files["judge"]),
                     "--base-judge-sha256", sha, "--new-judge-sha256", sha])
    assert code == 1


# --- N-3 --------------------------------------------------------------------------------------

def _raise(error):
    def raiser(*args, **kwargs):
        raise error
    return raiser


@pytest.mark.parametrize("error", [RuntimeError("x"), ZeroDivisionError(), StopIteration()])
def test_n3_any_exception_is_exit_3(tmp_path, monkeypatch, error) -> None:
    selection = tmp_path / "selection.json"
    selection.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(tjr, "judge_records", _raise(error))
    monkeypatch.setattr(compare, "Baseline", _raise(error))
    monkeypatch.setattr(case_judge, "_run", _raise(error))
    monkeypatch.setattr(dryrun, "summarize", _raise(error))
    cases = [(tjr.main, ["records"]), (compare.main, ["baseline", "--new", "x.jsonl"]),
             (case_judge.main, ["case-f", "--rows", "r", "--grid", "g"]),
             (dryrun.main, ["summarize", "--selection", str(selection)])]
    for index, (main, argv) in enumerate(cases):
        out = tmp_path / f"out_{index}.json"
        assert main([*argv, "--out", str(out)]) == 3, index
        assert "error" in json.loads(out.read_text(encoding="utf-8"))


def test_n3_keyboard_interrupt_is_not_caught(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(tjr, "judge_records", _raise(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        tjr.main(["records", "--out", str(tmp_path / "out.json")])


# --- N-4 --------------------------------------------------------------------------------------

def test_n4_vb_line_with_p4_readings_makes_t_jr_10_not_judgeable() -> None:
    def vb_truth_reads(inputs, key):
        inputs.rerun["VB"][key]["hydraulics_record"]["rod_reading_truth_calls"] = 3

    problems = compare.Problems()
    report = tjr.judge_t8(_t8_inputs(vb_truth_reads), problems)
    assert report["T-JR-10"]["status"] == compare.STATUS_NOT_JUDGEABLE
    assert any(tjr.VB_STALE_REASON in text and "P4 evidence 1" in text
               for text in problems.not_judgeable)
    assert report["T-JR-11"]["status"] == compare.STATUS_PASS
    assert report["VB_rerun_record"]["evidence_problems"]


def test_n4_vb_lines_without_p4_readings_pass() -> None:
    problems = compare.Problems()
    report = tjr.judge_t8(_t8_inputs(), problems)
    assert report["VB_rerun_record"]["evidence_problems"] == []
    assert problems.status() == compare.STATUS_PASS


# --- R-b --------------------------------------------------------------------------------------

def test_rb_record_keys_present() -> None:
    line = _dg3_document(setting="VBJ", count=1)["results"][0]
    assert dryrun.record_keys_present(line) == {
        "hydraulics_record.relock_step_over_1bar_count": False,
        "hydraulics_record.p1_retract_seed_log_columns": False,
        "lock_window_alignment.n_late_fallback": True}
    line["hydraulics_record"].update(relock_step_over_1bar_count=0,
                                     p1_retract_seed_log_columns=[])
    assert all(dryrun.record_keys_present(line).values())
