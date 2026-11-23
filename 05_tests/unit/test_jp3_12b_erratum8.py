"""436.9 edition 5 erratum 8 (``jp3_remedy_spec_v5_erratum8.md`` 8-8.3, sealed cd2de978).

The numbered tests 1 .. 14 of 8-8.3 for ``jp3_12b_judge.py`` (``decide`` / ``judge``) and the
run step gates of 8-9 (``run_steps_ed5/e8_gates_ed5.ps1``, run alone under pwsh with
``Set-StrictMode -Version 3`` as the steps do). The inputs are synthetic outputs in the r79
runner form, built with the builders of ``test_jp3_12b_tools.py`` under ``tmp_path``; no file
of ``j9_runs`` is read and the 8-7 blind files are never used (test 12). Every ``main`` test
runs with the working folder elsewhere than the inputs.
"""
# ruff: noqa: F811 (the fixtures world / selected / cwd_elsewhere come from test_jp3_12b_tools)

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from test_jp3_12b_tools import (  # noqa: F401 (selected, world, cwd_elsewhere: fixtures)
    READY_S,
    ROOT,
    ROWS,
    _FileWatch,
    build,
    cwd_elsewhere,
    decide_args,
    expect_args,
    expected_vbk0,
    judge,
    judge_args,
    run_main,
    selected,
    world,
)

STEPS = ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "prelaunch_j9" / "run_steps_ed5"
GATES_PS1 = STEPS / "e8_gates_ed5.ps1"
EMPTY_GRADES = {"vbk0": {"runs": []}, "vbk": {"runs": []}}
"""Grade-judge files that name no line: the test itself reads no VBK file (file watch)."""
CONSTANT_STROKE_M = 0.40
N23_FAILURE = "(2)+(3) n23 {n} > allow {k} (erratum 8 8-2)"


# ------------------------------------------------------------------------------- helpers
def chain(*edits):
    """One ``build`` edit from several."""
    def edit(block, vbk0, vbk):
        for one in edits:
            one(block, vbk0, vbk)
    return edit


def worse(block: str, losses: int, delays: int = 0, start: int = 0):
    """VBK READY lost on ``losses`` pairs of ``block`` and 31 s later on ``delays`` more."""
    def edit(name, vbk0, vbk):
        if name != block:
            return
        for rank in range(start, start + losses):
            vbk.rows[vbk.key_at(rank)]["base"]["t_ready_s"] = None
        for rank in range(start + losses, start + losses + delays):
            vbk.rows[vbk.key_at(rank)]["base"]["t_ready_s"] = READY_S + 31.0
    return edit


def decided(world, capsys, blocks=("b1", "b2"), witness=True, edit=None):
    """Both arms written and decided (b4: first b1 / b2 -> needs_b4, then with b4)."""
    written0, written1 = build(world, blocks=blocks, witness=witness, edit=edit)
    if "b4" in blocks:
        first = {block: written0[block] for block in ("b1", "b2")}
        code, last, _ = run_main(decide_args(world, first, world["runs"] / "d_b12.json"), capsys)
        assert (code, last["status"]) == (0, "needs_b4")
    decision = world["runs"] / "decision.json"
    code, last, record = run_main(decide_args(world, written0, decision), capsys)
    assert (code, last["status"]) == (0, "decided"), record
    return written0, written1, decision, record


def judged(world, capsys, written0, written1, decision, name="judge.json", grades=None):
    return run_main(judge_args(world, written0, written1, decision, world["runs"] / name,
                               grades), capsys)


def crafted_decision(world, record: dict, name: str, **changes) -> Path:
    """A decision record from ``record`` with ``changes`` (a value None drops the key)."""
    document = {**record}
    for key, value in changes.items():
        if value is None:
            document.pop(key, None)
        else:
            document[key] = value
    path = world["runs"] / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def plain(key: str) -> str:
    return judge.plain_key(key)


def rewrite_npz(path: Path, change) -> None:
    """Load a T4h npz, ``change(arrays)`` and write it back (uncompressed, as the builder)."""
    with np.load(path, allow_pickle=False) as data:
        arrays = {name: np.asarray(data[name]) for name in data.files}
    change(arrays)
    np.savez(path, **arrays)


def t4h_of(written: dict, block: str, key: str) -> Path:
    result, t4h = written[block]
    rows = json.loads(result.read_text(encoding="utf-8"))["results"]
    name = next(row["t4h_file"] for row in rows if plain(row["key"]) == plain(key))
    return t4h / name


def pairs_by_key(report: dict) -> dict[str, dict]:
    return {pair["key"]: pair for pair in report["pairs"]}


# ------------------------------------------------------------------------------- 1, 2
@pytest.mark.parametrize(("losses", "delays", "code", "verdict"), [(4, 3, 0, "pass"),
                                                                   (5, 3, 1, "failed")])
def test_e8_01_b1_b2_allowance_7(world, capsys, cwd_elsewhere, losses, delays, code,
                                 verdict) -> None:
    """8-8.3 1: b1 b2, n23 = 7 passes (exit 0), 8 fails (exit 1); loss and delay are one count."""
    written0, written1, decision, _ = decided(world, capsys, edit=worse("b1", losses, delays))
    got, last, report = judged(world, capsys, written0, written1, decision)
    n23 = losses + delays
    assert (got, last["status"]) == (code, verdict), report["problems"]
    rule = report["ready_rule"]
    assert (rule["n_ready_loss"], rule["n_ready_plus30"], rule["n_vbk_worse"]) == (
        losses, delays, n23)
    assert (rule["allow_k"], rule["blocks_used"], rule["verdict"]) == (7, ["b1", "b2"], verdict)
    expected = [N23_FAILURE.format(n=n23, k=7)] if verdict == "failed" else []
    assert report["problems"]["failures"] == expected
    assert report["problems"]["setting_defects"] == report["problems"]["not_judgeable"] == []
    assert rule["by_block"] == {
        "b1": {"n_opp": 167, "n_vbk_worse": n23, "n_ready_loss": losses,
               "n_ready_plus30": delays},
        "b2": {"n_opp": 167, "n_vbk_worse": 0, "n_ready_loss": 0, "n_ready_plus30": 0}}


@pytest.mark.parametrize(("b4_losses", "code", "verdict"), [(3, 0, "pass"), (4, 1, "failed")])
def test_e8_02_b1_b2_b4_allowance_9(world, capsys, cwd_elsewhere, b4_losses, code,
                                    verdict) -> None:
    """8-8.3 2: b1 b2 b4, n23 = 9 passes, 10 fails; the b4 pairs are the TRw layer."""
    edit = chain(worse("b1", 3), worse("b2", 3), worse("b4", b4_losses))
    written0, written1, decision, record = decided(world, capsys, blocks=("b1", "b2", "b4"),
                                                   witness=False, edit=edit)
    assert (record["blocks_used"], record["allow_k"]) == (["b1", "b2", "b4"], 9)
    got, last, report = judged(world, capsys, written0, written1, decision)
    n23 = 6 + b4_losses
    assert (got, last["status"]) == (code, verdict), report["problems"]
    rule = report["ready_rule"]
    assert (rule["n_vbk_worse"], rule["allow_k"], rule["verdict"]) == (n23, 9, verdict)
    expected = [N23_FAILURE.format(n=n23, k=9)] if verdict == "failed" else []
    assert report["problems"]["failures"] == expected
    assert rule["by_block"]["b4"]["n_ready_loss"] == b4_losses
    assert rule["by_cell"]["TRw"] == rule["by_block"]["b4"]
    assert sum(cell["n_opp"] for cell in rule["by_cell"].values()) == 501


# ------------------------------------------------------------------------------- 3
def test_e8_03_b3_is_not_judgeable(world, capsys, cwd_elsewhere, tmp_path) -> None:
    """8-8.3 3: a decision record with b3 is not judgeable (exit 2); decide that needs b3 stops
    with exit 2 (no needs_b3 status); the old b3 phase of the run steps starts nothing."""
    written0, written1, _, record = decided(world, capsys)
    for name, blocks in (("d_b3.json", ["b1", "b2", "b3"]), ("d_b13.json", ["b1", "b3"])):
        decision = crafted_decision(world, record, name, blocks=blocks, blocks_used=blocks)
        code, last, report = judged(world, capsys, written0, written1, decision,
                                    f"j_{name}", EMPTY_GRADES)
        assert (code, last["status"]) == (2, "not_judgeable")
        assert "no allowance" in report["reason"]

    def no_trigger(block, vbk0, vbk):
        for rank in range(70):  # 2 x 97 opportunity pairs < 0.9 x 334
            for arm in (vbk0, vbk):
                arm.rows[arm.key_at(rank)]["rod_fault"].update(is_armed=False,
                                                               first_applied_read=None)
    other = {**world, "runs": world["runs"] / "b3"}
    other["runs"].mkdir()
    written_b3, _ = build(other, edit=no_trigger)
    code, last, decided_b3 = run_main(decide_args(other, written_b3, other["runs"] / "d.json"),
                                      capsys)
    assert (code, last["status"], decided_b3["reason"]) == (2, "not_judgeable", judge.B3_REASON)
    assert "needs_b3" not in judge.EXIT_OF_STATUS and "aa_floor_stop" not in judge.EXIT_OF_STATUS
    pwsh = shutil.which("pwsh")
    assert pwsh is not None, "pwsh (PowerShell 7) is needed for the run step tests"
    empty_folder = tmp_path / "step6b_cwd"
    empty_folder.mkdir()
    done = subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-File",
                           str(STEPS / "step6b_vbk0.ps1"), "-Phase", "b3"], cwd=empty_folder,
                          capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 2 and "replaced by erratum 8" in done.stdout
    assert list(empty_folder.iterdir()) == []  # it starts and writes nothing


# ------------------------------------------------------------------------------- 4
def test_e8_04_ready_delay_boundary(world, capsys, cwd_elsewhere) -> None:
    """8-8.3 4: VBK0 100.0 s; VBK 130.000001 s counts (rounded 30.000001), 130.0 s and
    130.0000004 s do not (rounded 30.0); 30.0000005 s is never used. The mirror case (VBK0
    130.000001 s, VBK 100.0 s) is ``n_vbk0_worse_plus30``."""
    assert round(130.000001 - 100.0, 6) == 30.000001 > 30.0
    assert round(130.0 - 100.0, 6) == round(130.0000004 - 100.0, 6) == 30.0
    cases = {0: (100.0, 130.000001, "plus30"), 1: (100.0, 130.0, "ok"),
             2: (100.0, 130.0000004, "ok"), 3: (130.000001, 100.0, "ok")}

    def edit(block, vbk0, vbk):
        if block != "b1":
            return
        for rank, (ready0, ready, _) in cases.items():
            vbk0.rows[vbk0.key_at(rank)]["base"]["t_ready_s"] = ready0
            vbk.rows[vbk.key_at(rank)]["base"]["t_ready_s"] = ready
    written0, written1, decision, _ = decided(world, capsys, edit=edit)
    code, last, report = judged(world, capsys, written0, written1, decision)
    assert (code, last["status"]) == (0, "pass"), report["problems"]
    pairs = pairs_by_key(report)
    keys = list(json.loads(written0["b1"][0].read_text(encoding="utf-8"))["results"])
    for rank, (_, _, outcome) in cases.items():
        assert pairs[plain(keys[rank]["key"])]["ready_outcome"] == outcome, rank
    rule = report["ready_rule"]
    assert (rule["n_ready_plus30"], rule["n_ready_loss"], rule["n_vbk_worse"]) == (1, 0, 1)
    assert (rule["n_vbk0_worse_plus30"], rule["n_vbk0_worse_loss"], rule["n_vbk0_worse"]) == (
        1, 0, 1)


# ------------------------------------------------------------------------------- 5
def test_e8_05_vbk0_without_ready(world, capsys, cwd_elsewhere) -> None:
    """8-8.3 5: both without READY -> "VBK0 READY not reached", not in n23; VBK0 without and VBK
    with READY -> ``n_vbk0_worse_loss`` + 1, n23 unchanged; both are (1) judged pairs (N_1)."""
    def edit(block, vbk0, vbk):
        if block != "b2":
            return
        for arm in (vbk0, vbk):
            arm.rows[arm.key_at(0)]["base"]["t_ready_s"] = None
        vbk0.rows[vbk0.key_at(1)]["base"]["t_ready_s"] = None
    written0, written1, decision, _ = decided(world, capsys, edit=edit)
    code, last, report = judged(world, capsys, written0, written1, decision)
    assert (code, last["status"]) == (0, "pass"), report["problems"]
    keys = [plain(row["key"]) for row in
            json.loads(written0["b2"][0].read_text(encoding="utf-8"))["results"][:2]]
    pairs = pairs_by_key(report)
    assert [pairs[key]["category"] for key in keys] == [judge.VBK0_NOT_READY] * 2
    assert [pairs[key]["ready_s"] for key in keys] == [None, READY_S]
    assert "ready_outcome" not in pairs[keys[0]]
    rule = report["ready_rule"]
    assert (rule["n_vbk_worse"], rule["n_opp"], rule["n_fault_judged"]) == (0, 332, 334)
    assert (rule["n_vbk0_worse_loss"], rule["n_vbk0_worse_plus30"], rule["n_vbk0_worse"]) == (
        1, 0, 1)
    assert report["pass_sentence"]["n_fault_judged"] == 334


# ------------------------------------------------------------------------------- 6
def test_e8_06_stall_signature(world, capsys, cwd_elsewhere) -> None:
    """8-8.3 6: a VBK stall line (no READY, last phase level, no fault phase, every leg's
    stroke span < 1 mm over the last 20 s) is READY lost and listed; a lost pair without the
    signature (stroke span 3.6 mm, last phase done, a fault phase entry) counts the same; a
    VBK0 stall line is listed too. Without ``t_s`` in a T4h the signature is not computed and
    the status and exit code stay."""
    constant = np.full((ROWS, 4), CONSTANT_STROKE_M)

    def edit(block, vbk0, vbk):
        if block != "b1":
            return
        for rank in (0, 1, 3, 4):  # 3: last phase done; 4: a fault phase entry on both arms
            vbk.rows[vbk.key_at(rank)]["base"]["t_ready_s"] = None
        for rank in (0, 3, 4):
            vbk.columns[vbk.key_at(rank)]["motor_stroke_m"] = constant.copy()
        done = vbk.columns[vbk.key_at(3)]["phase"].copy()
        done[-5:] = "done"
        vbk.columns[vbk.key_at(3)]["phase"] = done
        for arm in (vbk0, vbk):  # the same entry on both arms: no new FAULT (1)
            faulted = arm.columns[arm.key_at(4)]["phase"].copy()
            faulted[30:33] = "fault"
            arm.columns[arm.key_at(4)]["phase"] = faulted
        for arm in (vbk0, vbk):
            arm.rows[arm.key_at(2)]["base"]["t_ready_s"] = None
        vbk0.columns[vbk0.key_at(2)]["motor_stroke_m"] = constant.copy()
    written0, written1, decision, _ = decided(world, capsys, edit=edit)
    code, last, report = judged(world, capsys, written0, written1, decision)
    assert (code, last["status"]) == (0, "pass"), report["problems"]
    rows = json.loads(written0["b1"][0].read_text(encoding="utf-8"))["results"]
    keys = [plain(row["key"]) for row in rows[:3]]
    rule = report["ready_rule"]
    assert (rule["n_ready_loss"], rule["n_vbk_worse"]) == (4, 4)
    assert rule["stall_signature_computed"] is True and rule["stall_signature_reasons"] == []
    last_t_s = float((ROWS - 1) * 0.1)
    assert rule["stall_signature_pairs"] == [
        {"block": "b1", "key": keys[0], "last_t_s": pytest.approx(last_t_s)}]
    assert rule["stall_signature_vbk0_lines"] == [
        {"block": "b1", "key": keys[2], "last_t_s": pytest.approx(last_t_s)}]
    rewrite_npz(t4h_of(written1, "b1", keys[1]), lambda arrays: arrays.pop("t_s"))
    code, last, again = judged(world, capsys, written0, written1, decision, "judge_no_t.json")
    assert (code, last["status"]) == (0, "pass"), again["problems"]
    rule = again["ready_rule"]
    assert rule["stall_signature_computed"] is False
    assert rule["stall_signature_pairs"] is None and rule["stall_signature_vbk0_lines"] is None
    assert any("t_s of" in text for text in rule["stall_signature_reasons"])
    assert rule["n_vbk_worse"] == 4 and again["problems"] == report["problems"]


# ------------------------------------------------------------------------------- 7
def test_e8_07_decide_records_aa_and_goes_on(world, capsys, cwd_elsewhere) -> None:
    """8-8.3 7: A/A 4 pairs (>= 3) -> decided (exit 0), ``aa_floor.is_stop`` False, the counted
    cases recorded."""
    def edit(block, vbk0, vbk):
        if block != "b2":
            return
        for rank, ready in ((0, None), (1, READY_S + 31.0), (2, None),
                            (3, READY_S + 30.000002)):
            vbk0.rows[vbk0.key_at(rank)]["base"]["t_ready_s"] = ready
    written0, _, _, record = decided(world, capsys, edit=edit)
    floor = record["aa_floor"]
    cases = [row["case"] for row in world["doc"]["cell_table"][:4]]
    assert (floor["pairs"], floor["counted_pairs"], floor["is_stop"]) == (167, 4, False)
    assert floor["counted"] == cases and floor["rule"] == "erratum 8 8-1: record"
    assert "stop_at" not in floor and record["exit"] == 0


# ------------------------------------------------------------------------------- 8
@pytest.mark.parametrize("case", ["new_fault", "h7", "n23_and_defect"])
def test_e8_08_failures_and_their_order(world, capsys, cwd_elsewhere, case) -> None:
    """8-8.3 8: (1) a new FAULT with n23 0 fails; (4) H-7 fails; n23 8 with a setting defect
    fails and keeps the defect (erratum 2 2-10)."""
    def edit(block, vbk0, vbk):
        if block != "b1":
            return
        if case == "new_fault":
            vbk.events[vbk.key_at(9)] = [[3.0, "FAULT_STROKE_END:FR"]]
        elif case == "h7":
            vbk.rows[vbk.key_at(4)]["hydraulics_record"]["extend_bound_check"][
                "jp3a_breach_reads"] = [0, 1, 0, 0]
        else:
            worse("b1", 8)(block, vbk0, vbk)
            vbk.rows[vbk.key_at(20)]["rod_fault"]["trigger_read"] += 1
    written0, written1, decision, _ = decided(world, capsys, edit=edit)
    code, last, report = judged(world, capsys, written0, written1, decision)
    assert (code, last["status"]) == (1, "failed"), report["problems"]
    failures = report["problems"]["failures"]
    if case == "new_fault":
        assert len(failures) == 1 and "new FAULT" in failures[0]
        assert report["ready_rule"]["n_vbk_worse"] == 0
    elif case == "h7":
        assert failures == ["J-P3 H-7 on the VBK lines (4)"]
    else:
        assert failures == [N23_FAILURE.format(n=8, k=7)]
        assert any("trigger reads differ" in text
                   for text in report["problems"]["setting_defects"])


# ------------------------------------------------------------------------------- 9
def test_e8_09_decision_blocks_and_allowance(world, capsys, cwd_elsewhere, monkeypatch) -> None:
    """8-8.3 9 (W-5): allow_k not the rule value, allow_k or blocks_used missing, blocks_used
    not the set of blocks, an allowance of another type: each not judgeable before any VBK
    file is opened."""
    written0, written1, _, record = decided(world, capsys)
    variants = {"allow_9": {"allow_k": 9}, "no_allow": {"allow_k": None},
                "no_used": {"blocks_used": None},
                "set_differs": {"blocks_used": ["b1", "b2", "b4"], "allow_k": 9},
                "allow_text": {"allow_k": "7"}, "repeated": {"blocks_used": ["b1", "b1", "b2"]},
                "used_text": {"blocks_used": "b1,b2"}}
    watch = _FileWatch(monkeypatch)
    for name, changes in variants.items():
        decision = crafted_decision(world, record, f"d_{name}.json", **changes)
        code, last, report = judged(world, capsys, written0, written1, decision,
                                    f"j_{name}.json", EMPTY_GRADES)
        assert (code, last["status"]) == (2, "not_judgeable"), name
        assert report["reason"], name
    assert watch.touched("vbk_") == []


# ------------------------------------------------------------------------------- 10
def test_e8_10_no_opportunity_pair_is_not_judgeable(world, capsys, cwd_elsewhere) -> None:
    """8-8.3 10: N_opp < 301 stops decide (exit 2); a decided record whose blocks hold no
    opportunity pair is not judgeable with n23 0 (never a pass on an empty set)."""
    def edit(block, vbk0, vbk):
        for rank in range(167):
            vbk0.rows[vbk0.key_at(rank)]["base"]["t_ready_s"] = None
    written0, written1 = build(world, edit=edit)
    code, last, record = run_main(decide_args(world, written0, world["runs"] / "d.json"), capsys)
    assert (code, last["status"]) == (2, "not_judgeable")
    assert record["n_topup"]["n_opp_b1_b2"] == 0
    decision = crafted_decision(world, record, "d_empty.json", status="decided",
                                blocks=["b1", "b2"], blocks_used=["b1", "b2"], allow_k=7,
                                n_opp=0, k=0, reason=None)
    code, last, report = judged(world, capsys, written0, written1, decision)
    assert (code, last["status"]) == (2, "not_judgeable"), report["problems"]
    assert "no opportunity pair" in report["problems"]["not_judgeable"]
    assert report["problems"]["failures"] == []
    rule = report["ready_rule"]
    assert (rule["n_opp"], rule["n_vbk_worse"], rule["verdict"]) == (0, 0, "not_judgeable")
    assert rule["n_fault_judged"] == 334


# ------------------------------------------------------------------------------- 11
def test_e8_11_record_item_exceptions_keep_the_status(world, capsys, cwd_elsewhere,
                                                      monkeypatch) -> None:
    """8-8.3 11 (W-4): a record item that raises (t_s and motor_stroke_m of other lengths, a
    failing helper) is ``computed`` False with its reason; status and exit code are those
    without the exception. An upper case ``LEVEL`` phase meets signature condition 3."""
    constant = np.full((ROWS, 4), CONSTANT_STROKE_M)

    def edit(block, vbk0, vbk):
        if block != "b1":
            return
        for rank in (0, 1):
            key = vbk.key_at(rank)
            vbk.rows[key]["base"]["t_ready_s"] = None
            vbk.columns[key]["motor_stroke_m"] = constant.copy()
        key = vbk.key_at(1)
        vbk.columns[key]["phase"] = np.char.upper(vbk.columns[key]["phase"])
    written0, written1, decision, _ = decided(world, capsys, edit=edit)
    code, last, control = judged(world, capsys, written0, written1, decision)
    assert (code, last["status"]) == (0, "pass"), control["problems"]
    keys = [plain(row["key"]) for row in
            json.loads(written1["b1"][0].read_text(encoding="utf-8"))["results"][:2]]
    assert [item["key"] for item in control["ready_rule"]["stall_signature_pairs"]] == keys
    rewrite_npz(t4h_of(written1, "b1", keys[0]),
                lambda arrays: arrays.update(t_s=arrays["t_s"][:-1]))
    code, last, report = judged(world, capsys, written0, written1, decision, "judge_len.json")
    assert (code, last["status"]) == (0, "pass") and report["problems"] == control["problems"]
    rule = report["ready_rule"]
    assert rule["stall_signature_computed"] is False
    assert "ValueError" in rule["stall_signature_reasons"][0]
    assert rule["n_vbk_worse"] == 2 and rule["by_cell_computed"] is True

    def fail(*_args, **_kwargs):
        raise TypeError("a record helper failed")
    for name in ("vbk0_worse_record", "_cell_of", "by_block_record"):
        monkeypatch.setattr(judge, name, fail)
    code, last, report = judged(world, capsys, written0, written1, decision, "judge_raise.json")
    assert (code, last["status"]) == (0, "pass") and report["problems"] == control["problems"]
    rule = report["ready_rule"]
    for item, keys_of_item in judge.RECORD_ITEM_KEYS.items():
        if item == "stall_signature":
            continue
        assert rule[f"{item}_computed"] is False, item
        assert rule[f"{item}_reasons"] == ["exception TypeError: a record helper failed"]
        assert all(rule[key] is None for key in keys_of_item)
    assert (rule["n_vbk_worse"], rule["verdict"]) == (2, "pass")


# ------------------------------------------------------------------------------- 12
def test_e8_12_no_blind_file_in_tests_or_fixtures(world) -> None:
    """8-8.3 12 / 8-7: the judge tests and their fixtures never name or use the blind files
    (the c dry VBK runs of seeds 92 / 93 and the c dry logs of the run commit, the 12b VBK
    outputs); no output folder of the run commit is named at all. (A synthetic ``cdry_a1``
    folder of the older commit ae9d0b2d under ``tmp_path`` is no blind file.)"""
    blind = ["VBK" + "_c92", "VBK" + "_c93", "606f" + "8713", "12b_vbk" + "_a"]
    sources = [Path(__file__), Path(__file__).with_name("test_jp3_12b_tools.py")]
    for source in sources:
        text = source.read_text(encoding="utf-8")
        assert [name for name in blind if name in text] == [], source.name
    assert Path(world["runs"]).resolve().is_relative_to(Path(world["selection"]).parents[1])


# ------------------------------------------------------------------------------- 13
def test_e8_13_expected_vbk0_inputs(world, capsys, cwd_elsewhere, monkeypatch) -> None:
    """8-8.3 13 / 8-9 (d): a run file sha256 or a T4h digest other than expected, no
    expectation, one block without, or an expectation for a block without a fixed value:
    decide exit 2 ``not_judgeable`` with status, reason and input sha256 only."""
    written0, _ = build(world)
    expected = expected_vbk0(written0)
    base = decide_args(world, written0, world["runs"] / "unused.json", expect=False)
    other = "0" * 64
    variants = {
        "run_sha": {**expected, "b1": (other, expected["b1"][1])},
        "digest": {**expected, "b2": (expected["b2"][0], other)},
        "none": {}, "b1_only": {"b1": expected["b1"]},
        "b4_extra": {**expected, "b4": (other, other)}}
    watch = _FileWatch(monkeypatch)
    malformed = ["--expect-vbk0-sha256", "b1=xyz"]  # not 64 hex
    without_b1 = decide_args(world, {"b2": written0["b2"]}, world["runs"] / "unused.json",
                             expect=False)
    runs = {**{name: [*base, *expect_args(given)] for name, given in variants.items()},
            "malformed": [*base, *expect_args({"b2": expected["b2"]}), *malformed,
                          "--expect-vbk0-t4h-digest", f"b1={expected['b1'][1]}"],
            "b1_not_given": [*without_b1, *expect_args(expected)]}
    for name, args in runs.items():
        args[args.index("--out") + 1] = str(world["runs"] / f"d_{name}.json")
        code, last, record = run_main(args, capsys)
        assert (code, last["status"]) == (2, "not_judgeable"), name
        assert set(record) == {"rule", "inputs", "status", "reason", "exit"}, name
        assert record["reason"].startswith("erratum 8 8-9 (d)"), name
        assert record["inputs"]["vbk0"]["b2"]["run_sha256"] == expected["b2"][0], name
    assert "one b<j>=<64 hex sha256> per block" in json.loads(
        (world["runs"] / "d_malformed.json").read_text(encoding="utf-8"))["reason"]
    assert "VBK0 b1 not given" in json.loads(
        (world["runs"] / "d_b1_not_given.json").read_text(encoding="utf-8"))["reason"]
    assert watch.touched("vbk_") == []
    code, last, record = run_main(decide_args(world, written0, world["runs"] / "d_ok.json"),
                                  capsys)
    assert (code, last["status"]) == (0, "decided")
    assert record["inputs"]["vbk0_expected"] == {
        "b1": {"run_sha256": expected["b1"][0], "t4h_sha256_digest": expected["b1"][1]},
        "b2": {"run_sha256": expected["b2"][0], "t4h_sha256_digest": expected["b2"][1]},
        "matched": True}


# ------------------------------------------------------------------------------- 14
def test_e8_14_b4_chain(world, capsys, cwd_elsewhere, tmp_path) -> None:
    """8-8.3 14: decide on b1 b2 says needs_b4 (exit 0), decide on b1 b2 b4 is decided with
    blocks_used b1 b2 b4 and allow_k 9; the run steps stop on a second needs_b4 (8-9 3) and
    step6c takes the b4 decision when 12b_decide_e8_b4.done exists (8-9 4)."""
    written0, _ = build(world, blocks=("b1", "b2", "b4"), witness=False)
    first_path = world["runs"] / "d_b12.json"
    code, last, first = run_main(decide_args(world, {block: written0[block] for block in
                                                     ("b1", "b2")}, first_path), capsys)
    assert (code, last["status"]) == (0, "needs_b4")
    second_path = world["runs"] / "d_b124.json"
    code, last, second = run_main(decide_args(world, written0, second_path), capsys)
    assert (code, last["status"]) == (0, "decided")
    assert (second["blocks_used"], second["allow_k"], second["blocks"]) == (
        ["b1", "b2", "b4"], 9, ["b1", "b2", "b4"])
    again = crafted_decision(world, second, "d_again.json", status="needs_b4",
                             blocks_used=None, allow_k=None)
    runs = tmp_path / "runs_root"
    for step, decision in (("12b_decide_e8", first_path), ("12b_decide_e8_b4", second_path)):
        folder = runs / f"{step}_a1"
        folder.mkdir(parents=True)
        shutil.copyfile(decision, folder / "decision.json")
        (runs / f"{step}.done").write_text(json.dumps({"folder": str(folder)}),
                                           encoding="utf-8")
    out = _gate(tmp_path, [
        f"Get-E8DecisionStop '{first_path}' @('needs_b4')",
        f"Get-E8DecisionStop '{first_path}' @('decided')",
        f"Get-E8DecisionStop '{second_path}' @('decided')",
        f"Get-E8DecisionStop '{again}' @('decided')",
        f"Get-E8DecisionChoice '{runs}'"])
    assert out[0] == "go" and out[1].startswith("2|") and out[2] == "go"
    assert out[3].startswith("2|") and "needs_b4 again: a setting defect" in out[3]
    chosen = runs / "12b_decide_e8_b4_a1" / "decision.json"
    assert out[4] == f"ok|path={chosen};step=12b_decide_e8_b4"


def test_e8_14_b4_below_45_is_not_judgeable(world, capsys, cwd_elsewhere) -> None:
    """8-9 3 / 6.3.6: k < 45 after b4 (here 37 b4 opportunity pairs) is not judgeable (exit
    2) without the decision keys; the run step then stops (not decided)."""
    def unready_b4(block, vbk0, vbk):
        if block == "b4":
            for rank in range(130):
                vbk0.rows[vbk0.key_at(rank)]["base"]["t_ready_s"] = None
    written0, _ = build(world, blocks=("b1", "b2", "b4"), witness=False, edit=unready_b4)
    code, last, record = run_main(decide_args(world, written0, world["runs"] / "d.json"), capsys)
    assert (code, last["status"]) == (2, "not_judgeable")
    assert record["reason"] == f"k 37 < {judge.K_MIN} after b4"
    assert not {"blocks", "blocks_used", "allow_k"} & set(record)


# ------------------------------------------------------------------------------- run step gates
SHOW = r"""
function Show($Result) {
    if ($null -eq $Result) { return 'go' }
    if ($Result.ContainsKey('code')) { return "$($Result.code)|$($Result.reason)" }
    $Pairs = @($Result.Keys) | Sort-Object | ForEach-Object { "$_=$($Result[$_])" }
    return 'ok|' + ($Pairs -join ';')
}
"""


def _gate(tmp_path: Path, calls: list[str]) -> list[str]:
    """Run each PowerShell call after dot-sourcing ``e8_gates_ed5.ps1`` alone (strict mode 3,
    errors stop, as the run steps); one output line per call (``Show``)."""
    pwsh = shutil.which("pwsh")
    assert pwsh is not None, "pwsh (PowerShell 7) is needed for the run step gate tests"
    index = len(list(tmp_path.glob("e8_gate_*.ps1")))
    script = tmp_path / f"e8_gate_{index}.ps1"
    body = "\n".join(f"Write-Output (Show ({call}))" for call in calls)
    script.write_text("[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)\n"
                      "Set-StrictMode -Version 3\n$ErrorActionPreference = 'Stop'\n"
                      f". '{GATES_PS1}'\n{SHOW}\n{body}\n", encoding="utf-8-sig")
    done = subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-File", str(script)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=120, check=False)
    assert done.returncode == 0, done.stderr
    lines = done.stdout.strip().splitlines()
    assert len(lines) == len(calls), done.stdout
    return lines


def _ps_lines(lines: list[str]) -> str:
    """A PowerShell array literal of strings (tabs written as `t)."""
    quoted = ", ".join('"' + line.replace("\t", "`t") + '"' for line in lines)
    return f"@({quoted})"


def test_e8_gate_diff_rule(tmp_path) -> None:
    """8-9 (a): the allowed diff lines go on; D, an existing 06_analysis file changed, the shared
    run steps, pre_las_preset_runner.py, another code or test path stop 3."""
    judge_tool = "04_scripts/04_hydraulic/coupled/jp3_12b_judge.py"
    allowed = [f"M\t{judge_tool}", "A\t05_tests/unit/test_jp3_12b_erratum8.py",
               "M\t05_tests/unit/test_jp3_12b_tools.py",
               "M\t06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps_ed5/common_ed5.ps1",
               "A\t06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps_ed5/x.ps1",
               "A\t06_analysis/02_control/j_p3_cause/prelaunch_j9/FIXED_INPUTS_abcdef12.SHA256SUMS",
               "M\t00_docs/decision_log.md", "M\tCLAUDE.md", "A\t00_docs/new.md"]
    refused = ["D\t06_analysis/02_control/j_p3_cause/x.md",
               "M\t06_analysis/02_control/j_p3_cause/jp3_remedy_spec_v5.md",
               "M\t06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps/common.ps1",
               "M\t05_tests/unit/pre_las_preset_runner.py",
               "M\t04_scripts/04_hydraulic/coupled/las_t3_dg3.py",
               "M\t04_scripts/04_hydraulic/coupled/jp3_fixed_inputs.py",
               "A\t05_tests/unit/test_other.py", "M\t03_src/outrigger_sim/x.py",
               "D\t" + judge_tool, "R100\ta\tb", "M\t.claude/agents/paper-reviewer.md"]
    calls = [f"Get-E8DiffStop {_ps_lines(allowed)}", "Get-E8DiffStop @()"]
    calls += [f"Get-E8DiffStop {_ps_lines([line])}" for line in refused]
    out = _gate(tmp_path, calls)
    assert out[:2] == ["go", "go"]
    assert all(line.startswith("3|erratum 8 8-9 (a)") for line in out[2:]), out


def test_e8_gate_ready_rule_of_step8(tmp_path) -> None:
    """Erratum 2 2-9.6 with 8-10 (W-5): ready_rule verdict pass and allow_k of blocks_used go
    on; a missing block or key, another verdict or allowance, an allowance as text stop 2."""
    good = {"verdict": "pass", "allow_k": 7, "blocks_used": ["b1", "b2"]}
    cases = {"good": {"ready_rule": good},
             "good_b4": {"ready_rule": {**good, "allow_k": 9, "blocks_used": ["b1", "b2", "b4"]}},
             "none": {"status": "pass"},
             "failed": {"ready_rule": {**good, "verdict": "failed"}},
             "empty": {"ready_rule": {**good, "verdict": "not_judgeable"}},
             "allow": {"ready_rule": {**good, "allow_k": 9}},
             "text": {"ready_rule": {**good, "allow_k": "7"}},
             "b3": {"ready_rule": {**good, "blocks_used": ["b1", "b2", "b3"]}},
             "no_used": {"ready_rule": {"verdict": "pass", "allow_k": 7}}}
    paths = {}
    for name, document in cases.items():
        paths[name] = tmp_path / f"judge_{name}.json"
        paths[name].write_text(json.dumps(document), encoding="utf-8")
    lines = _gate(tmp_path, [f"Get-E8ReadyRuleStop '{paths[name]}'" for name in cases])
    out = dict(zip(cases, lines, strict=True))
    assert out.pop("good") == "go" and out.pop("good_b4") == "go"
    assert all(line.startswith("2|") for line in out.values()), out


def _identity(head: str = "a" * 40, threads: str = "1", affinity: str = "0xf") -> dict:
    entry = {"time": "t", "python": "C:/dyn/python.exe", "python_version": "3.12.15",
             "threads": {"MKL_NUM_THREADS": threads, "OMP_NUM_THREADS": "1",
                         "NUMBA_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                         "MKL_THREADING_LAYER": "TBB"},
             "affinity_mask": affinity, "git": {"head": head, "status_porcelain": "",
                                               "is_clean": True},
             "rules_seals": {"rev6": {"sha256": "c" * 64, "ok": True}}}
    return {"start": [entry], "end": [{**entry, "time": "u"}]}


def test_e8_gate_identity_environment_and_workers(tmp_path) -> None:
    """8-9 (c): another mask, time, plan, T4h folder or setting name go on; another thread
    value, head or an undeclared variable stop 2; --workers 4 on both."""
    head = "a" * 40
    files = {"base": _identity(head), "same": _identity(head, affinity="0xf0"),
             "threads": _identity(head, threads="2"), "head": _identity("b" * 40)}
    paths = {}
    for name, document in files.items():
        paths[name] = tmp_path / f"{name}.identity.json"
        paths[name].write_text(json.dumps(document), encoding="utf-8")
    base_env = ("@{ R72_PATH = 'per_leg'; LAS_T3_DG3_LAS = 'on'; R79_V5_SETTING = 'VBK0'; "
                "R79_ROD_MODEL = 'plant_truth'; R79_T4H_DIR = 'a'; R79_ROD_FAULT_PLAN = 'p1' }")
    vbk_env = ("@{ R72_PATH = 'per_leg'; LAS_T3_DG3_LAS = 'on'; R79_V5_SETTING = 'VBK'; "
               "R79_ROD_MODEL = 'plant_truth'; R79_T4H_DIR = 'b'; R79_ROD_FAULT_PLAN = 'p4' }")
    extra_env = vbk_env[:-2] + "; R79_EXTRA = 'x' }"
    model_env = vbk_env.replace("plant_truth", "dyn_map")
    calls = [f"Get-E8IdentityStop '{paths['base']}' '{paths[name]}' '{head}'"
             for name in ("same", "threads", "head")]
    calls += [f"Get-E8EnvironmentStop {base_env} {vbk_env} 'VBK' @{{}}",
              f"Get-E8EnvironmentStop {base_env} {extra_env} 'VBK' @{{}}",
              f"Get-E8EnvironmentStop {base_env} {extra_env} 'VBK' @{{ R79_EXTRA = 'x' }}",
              f"Get-E8EnvironmentStop {base_env} {model_env} 'VBK' @{{}}",
              f"Get-E8EnvironmentStop {base_env} {vbk_env} 'VBK0' @{{}}",
              "Get-E8WorkersStop 'x.py run o --workers 4 --affinity 0x000F' 4",
              "Get-E8WorkersStop 'x.py run o --workers 3' 4",
              "Get-E8WorkersStop 'x.py run o --workers 4' 3"]
    out = _gate(tmp_path, calls)
    assert out[0] == "go" and out[1].startswith("2|") and out[2].startswith("2|")
    assert out[3] == "go" and out[4].startswith("2|") and out[5] == "go"
    assert out[6].startswith("2|") and "R79_ROD_MODEL" in out[6]
    assert out[7].startswith("2|") and out[8] == "go"
    assert out[9].startswith("2|") and out[10].startswith("2|")


def _base_root(root: Path, stops: int = 1, exit_code: int = 2, done: bool = False) -> Path:
    folder = root / "12b_vbk0_base_a1"
    folder.mkdir(parents=True)
    for block in ("b1", "b2"):
        (folder / f"VBK0_{block}.json").write_text("{}", encoding="utf-8")
        (folder / f"VBK0_{block}.identity.json").write_text("{}", encoding="utf-8")
        (folder / f"VBK0_{block}_t4h").mkdir()
    record = json.dumps({"folder": str(folder), "exit_code": exit_code})
    for index in range(stops):
        name = "12b_vbk0_base.stop" + ("" if index == 0 else f".2026112{index}")
        (root / name).write_text(record, encoding="utf-8")
    if done:
        (root / "12b_vbk0_base.done").write_text(record, encoding="utf-8")
    return folder


def test_e8_gate_stopped_base_attempt(tmp_path) -> None:
    """8-9 (e): the one stopped attempt a1 (exit 2, no done marker) with its b1 / b2 files is
    taken; a done marker, a second stop marker or another exit code stop 2."""
    roots = {name: tmp_path / name for name in ("good", "done", "two", "exit1")}
    folder = _base_root(roots["good"])
    _base_root(roots["done"], done=True)
    _base_root(roots["two"], stops=2)
    _base_root(roots["exit1"], exit_code=1)
    out = _gate(tmp_path, [f"Get-E8BaseStop '{root}'" for root in roots.values()])
    assert out[0] == f"ok|folder={folder}"
    assert all(line.startswith("2|") for line in out[1:]), out


def test_e8_gate_two_fixed_lists(tmp_path) -> None:
    """8-9 (a''): the old list holds but its run step lines, which the tool list must hold;
    the tool list names the old list with its sha256; any other change stops 2."""
    prefix = "06_analysis/x/run_steps_ed5/"
    files = {"06_analysis/data.json": "data", f"{prefix}common_ed5.ps1": "old",
             "06_analysis/rule.md": "rule"}
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")

    def sha(name: str) -> str:
        return hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()

    def write_list(name: str, entries: list[str]) -> str:
        (tmp_path / name).write_text("".join(f"{sha(entry)} *{entry}\n" for entry in entries),
                                     encoding="utf-8", newline="\n")
        return name

    old = write_list("06_analysis/FIXED_INPUTS_old.SHA256SUMS", list(files))
    (tmp_path / f"{prefix}common_ed5.ps1").write_text("new", encoding="utf-8")
    tool = write_list("06_analysis/FIXED_INPUTS_tool.SHA256SUMS",
                      [old, f"{prefix}common_ed5.ps1", "06_analysis/rule.md"])
    unlinked = write_list("06_analysis/FIXED_INPUTS_unlinked.SHA256SUMS",
                          [f"{prefix}common_ed5.ps1"])
    no_step = write_list("06_analysis/FIXED_INPUTS_nostep.SHA256SUMS", [old])

    def call(tool_list: str) -> str:
        return (f"Get-E8FixedListStop '{tmp_path / old}' '{tmp_path / tool_list}' "
                f"'{tmp_path}' '{prefix}'")
    out = _gate(tmp_path, [call(tool), call(unlinked), call(no_step)])
    assert out[0] == "go" and out[1].startswith("2|") and out[2].startswith("2|")
    (tmp_path / "06_analysis/data.json").write_text("changed", encoding="utf-8")
    out = _gate(tmp_path, [call(tool)])
    assert out[0].startswith("2|fixed input 06_analysis/data.json")


def test_e8_gate_decision_record_w5(tmp_path) -> None:
    """8-9 (d) on the script side: a decided record must hold blocks, blocks_used (the same set)
    and allow_k of 8-2; a needs_b4 record goes where it is allowed."""
    good = {"status": "decided", "blocks": ["b1", "b2"], "blocks_used": ["b1", "b2"],
            "allow_k": 7}
    cases = {"good": good, "needs": {"status": "needs_b4", "blocks": ["b1", "b2"]},
             "allow": {**good, "allow_k": 9}, "set": {**good, "blocks_used": ["b1", "b2", "b4"]},
             "missing": {"status": "decided", "blocks": ["b1", "b2"]},
             "judgeable": {"status": "not_judgeable"}}
    paths = {}
    for name, document in cases.items():
        paths[name] = tmp_path / f"decision_{name}.json"
        paths[name].write_text(json.dumps(document), encoding="utf-8")
    calls = [f"Get-E8DecisionStop '{paths[name]}' @('decided', 'needs_b4')" for name in cases]
    calls.append(f"Get-E8DecisionStop '{tmp_path / 'missing.json'}' @('decided')")
    out = dict(zip([*cases, "absent"], _gate(tmp_path, calls), strict=True))
    assert out.pop("good") == "go" and out.pop("needs") == "go"
    assert out.pop("absent").startswith("3|")
    assert all(line.startswith("2|") for line in out.values()), out
