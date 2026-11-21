"""436.9 edition 5 X-11 / X-13 (``jp3_12b_plan.py``, ``jp3_12b_judge.py``; spec v5 6.3, 7.2
"12b 판정 도구"): selection, plans and the two judge sub-commands on synthetic outputs in the
form the r79 runner writes (result rows with a T4h file name, the T4h npz in their folder).

Every ``main`` test runs with the working folder elsewhere than the inputs (tool rule (가)).
"""

from __future__ import annotations

import builtins
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
for _path in (COUPLED_DIR, S8_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import jp3_12b_judge as judge  # noqa: E402
import jp3_12b_plan as plan  # noqa: E402
import rod_fault_plan as rfp  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
ROWS = 40
PERIOD_S = 0.1
CHECK_ROWS = 10
CARRY_START = 20
"""Update 20 starts the fault leg's retract carry (tau_R trigger read; faulty from 21)."""
READY_S = 30.0


# ------------------------------------------------------------------------------- case source
def _cases() -> list[str]:
    families = [("g6", 100), ("g8", 50), ("ref", 17)]
    cases = []
    for family, count in families:
        cases += [f"{family}|{index}|x{index}|top|Fs0" for index in range(count)]
    return cases


def write_noise(path: Path) -> str:
    """A case source of the stored form: L1 and L2 lines, five seeds, 167 L2 cases."""
    results = []
    for seed in range(5):
        for level in ("L1", "L2"):
            if level == "L1" and seed:
                continue
            results += [{"key": f"cand=current#{level}|s{seed}|{case}", "level": level,
                         "seed_index": seed} for case in _cases()]
    path.write_text(json.dumps({"meta": {}, "results": results}), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture()
def selected(tmp_path):
    """X-11 run on the synthetic source with an empty scan root."""
    noise = tmp_path / "noise.json"
    sha = write_noise(noise)
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    out = tmp_path / "plans"
    document = plan.select(noise, scan_root, out, noise_sha256=sha)
    return {"noise": noise, "sha": sha, "scan": scan_root, "out": out, "doc": document}


# ------------------------------------------------------------------------------- X-11
def test_x11_blocks_seeds_cells_and_plans(selected) -> None:
    document, out = selected["doc"], selected["out"]
    assert [document["blocks"][f"b{j}"]["seed_index"] for j in range(1, 5)] == [30, 31, 32, 33]
    assert document["seed_repeats"] == 0 and document["cases"] == 167
    table = document["cell_table"]
    assert [row["cell"] for row in table[:9]] == [0, 1, 2, 3, 4, 5, 6, 7, 0]
    assert (table[0]["leg"], table[0]["phase"]) == ("FL", "tau_C")
    assert (table[3]["leg"], table[3]["phase"]) == ("FR", "tau_R")
    assert table[0]["case"] == "L2|g6|0|x0|top|Fs0"
    for block in ("b1", "b2", "b3", "b4"):
        loaded = rfp.load_plan(out / f"{block}_plan.json")  # a valid runner plan
        assert len(loaded.faults) == 167
        assert loaded.sha256 == document["outputs"][f"{block}_plan.json"]
        assert all(fault.delay_reads == 0 and fault.value_bar == -100.0
                   for fault in loaded.faults.values())
        keys = (out / f"{block}_keys.txt").read_text(encoding="utf-8").splitlines()
        assert keys == [rfp_key.split("#", 1)[1] for rfp_key in loaded.faults]
    b4 = rfp.load_plan(out / "b4_plan.json").faults
    assert {fault.anchor.text for fault in b4.values()} == {"retract_witness_after:LEVEL"}
    b1 = rfp.load_plan(out / "b1_plan.json").faults
    first = b1["cand=current#L2|s30|g6|0|x0|top|Fs0"]
    assert (first.leg, first.anchor.text) == ("FL", "phase_exit:CHECK")
    for name, sha in document["outputs"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == sha


def test_x11_dry_plan_seeds_90_91_twenty_per_cell(selected) -> None:
    out = selected["out"]
    dry = rfp.load_plan(out / "c90_91_plan.json").faults
    assert len(dry) == 160
    per_cell = {}
    for fault in dry.values():
        cell = (fault.leg, fault.anchor.text)
        per_cell[cell] = per_cell.get(cell, 0) + 1
    assert len(per_cell) == 8 and set(per_cell.values()) == {20}
    seeds = {key.split("|")[1] for key in dry}
    assert seeds == {"s90", "s91"}
    assert len((out / "c90_keys.txt").read_text(encoding="utf-8").splitlines()) == 80


def test_x11_scan_collision_raises_all_seeds_by_10(tmp_path) -> None:
    """6.3.1: a key of any block in the scan (``j9_runs`` included) raises all four by 10,
    repeated; the scan evidence is recorded; an L2nocal key is an r79 key too (X-3)."""
    noise = tmp_path / "noise.json"
    sha = write_noise(noise)
    scan = tmp_path / "scan"
    (scan / "02_control" / "j_p3_cause" / "j9_runs" / "x").mkdir(parents=True)
    (scan / "02_control" / "j_p3_cause" / "j9_runs" / "x" / "dg3.json").write_text(
        json.dumps({"results": [{"key": "cand=current#L2|s33|g8|5|x5|top|Fs0"}]}),
        encoding="utf-8")
    (scan / "other.jsonl").write_text(json.dumps({"key": "L2|s41|ref|2|x2|top|Fs0"}) + "\n"
                                      + json.dumps({"key": "L2nocal|s77|g6|0|x0"}) + "\n",
                                      encoding="utf-8")
    document = plan.select(noise, scan, tmp_path / "plans", noise_sha256=sha)
    assert [document["blocks"][f"b{j}"]["seed_index"] for j in range(1, 5)] == [50, 51, 52, 53]
    assert document["seed_repeats"] == 2
    assert document["scan"]["files_scanned"] == 2 and document["scan"]["seed_max"] == 77
    assert {row["path"] for row in document["scan"]["files"]} == {
        "02_control/j_p3_cause/j9_runs/x/dg3.json", "other.jsonl"}


def test_x11_refusals(tmp_path, selected, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert plan.main(["--noise", str(selected["noise"]), "--scan-root", str(selected["scan"]),
                      "--out-dir", str(tmp_path / "new")]) == 2  # not the fixed source
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "not_usable"
    with pytest.raises(plan.NotUsable, match="has files"):
        plan.select(selected["noise"], selected["scan"], selected["out"],
                    noise_sha256=selected["sha"])
    (selected["scan"] / "dry.json").write_text(json.dumps({"key": "L2|s90|g6|0|x0|top|Fs0"}),
                                                encoding="utf-8")
    with pytest.raises(plan.NotUsable, match="dry key"):
        plan.select(selected["noise"], selected["scan"], tmp_path / "plans2",
                    noise_sha256=selected["sha"])


def test_x11_main_end_to_end_in_another_folder(tmp_path, monkeypatch, capsys) -> None:
    noise = tmp_path / "in" / "noise.json"
    noise.parent.mkdir()
    sha = write_noise(noise)
    (tmp_path / "scan").mkdir()
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    monkeypatch.setattr(plan.fixed, "NOISE_VB_SHA256", sha)
    monkeypatch.setattr(plan.select, "__defaults__", (sha,))
    assert plan.main(["--noise", str(noise), "--scan-root", str(tmp_path / "scan"),
                      "--out-dir", str(tmp_path / "out")]) == 0
    last = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert last["status"] == "written" and last["seeds"] == [30, 31, 32, 33]
    assert (tmp_path / "out" / "selection.json").is_file()


# ------------------------------------------------------------------------------- synthetic runs
def _columns(leg: int, anchor: str, witness: bool) -> dict[str, np.ndarray]:
    """T4h columns of one run: CHECK reads 0 .. 9, LEVEL after; the fault leg retracts from
    update 20 to 25; with ``witness`` its reading drops 0.6 mm per read from read 21."""
    phase = np.array(["check"] * CHECK_ROWS + ["level"] * (ROWS - CHECK_ROWS))
    command = np.zeros((ROWS, 4))
    command[CARRY_START:CARRY_START + 6, leg] = -5e-3
    stroke = np.full((ROWS, 4), 0.40)
    if witness:
        for row in range(CARRY_START + 1, CARRY_START + 7):
            stroke[row:, leg] -= 0.6e-3
    first = CHECK_ROWS + 1 if anchor == "phase_exit:CHECK" else CARRY_START + 1
    applied = np.zeros((ROWS, 4), bool)
    applied[first:, leg] = True
    return {"t_s": np.arange(ROWS) * PERIOD_S, "phase": phase, "command_m_s": command,
            "motor_stroke_m": stroke, "rod_fault_applied": applied}


def _check_record() -> dict:
    return {"rule_revision": 6, "spec_edition": "fe6f5844",
            "carry_end_rule": "inherit_when_gate_shut", "retract_start_rule": "with_tracker",
            "identity_consistent": True, "sensor_grade": "normal",
            "jp3a_breach_reads": [0] * 4, "jp3b_breach_over_tol_reads": [0] * 4,
            "jp3c_breach_reads": [0] * 4}


class Arm:
    """Builder of one block and arm (rows plus T4h files) with per-key overrides."""

    def __init__(self, folder: Path, selection: dict, plans: Path, block: str, arm: str,
                 witness: bool = True) -> None:
        self.folder, self.selection, self.block, self.arm = folder, selection, block, arm
        self.plan_file = plans / f"{block}_plan.json"
        self.plan = json.loads(self.plan_file.read_text(encoding="utf-8"))["faults"]
        self.witness = witness
        self.rows: dict[str, dict] = {}
        self.events: dict[str, list] = {}
        self.columns: dict[str, dict] = {}
        for key, fault in self.plan.items():
            self._add(key, fault)

    def _add(self, key: str, fault: dict) -> None:
        leg = LEGS.index(fault["leg"])
        anchor = fault["anchor"]
        trigger = CHECK_ROWS + 1 if anchor == "phase_exit:CHECK" else CARRY_START
        if anchor == "retract_witness_after:LEVEL":
            trigger = CARRY_START + 2
        first = trigger if anchor == "phase_exit:CHECK" else trigger + 1
        record = {"plan_sha256": hashlib.sha256(self.plan_file.read_bytes()).hexdigest(),
                  "fault_id": fault["fault_id"], "leg": fault["leg"], "kind": "STUCK",
                  "value": -100.0, "anchor": anchor, "delay_reads": 0, "is_armed": True,
                  "trigger_read": trigger, "first_applied_read": first,
                  "first_applied_t_s": first * PERIOD_S,
                  "latched": {"is_latched": True, "reason": "D1", "t_s": first * PERIOD_S,
                              "reads_after_first": 0, "is_same_read_d1": True},
                  "pre_trigger_commands_sha256": "c" * 64, "pre_trigger_fallback": False}
        name = key.replace("|", "_").replace("#", "_").replace("=", "_") + ".npz"
        row = {"key": key, "v5_setting": judge.SETTING_OF_ARM[self.arm], "t4h_file": name,
               "rod_fault": record, "base": {"t_ready_s": READY_S}, "has_rod_reading": True,
               "head_only_declared": False, "events": []}
        if self.arm == "vbk":
            row.update(controller_tag="final_C4G2_P3W_LAS_K1", run_extend_start_revision=6,
                       hydraulics_record={"extend_bound_check": _check_record()})
        self.rows[key] = row
        self.events[key] = [[1.0, "INFO_PRESSURE_ZERO_CALIBRATED:FL"]]
        self.columns[key] = _columns(leg, anchor, self.witness)

    def key_at(self, rank: int) -> str:
        return list(self.rows)[rank]

    def write(self) -> tuple[Path, Path]:
        t4h = self.folder / f"{self.arm}_{self.block}_t4h"
        t4h.mkdir(parents=True)
        for key, row in self.rows.items():
            arrays = dict(self.columns[key])
            if self.arm == "vbk":
                leg = LEGS.index(row["rod_fault"]["leg"])
                witness = np.zeros((ROWS, 4), bool)
                substeps = np.zeros((ROWS, 4), np.int32)
                witness[CARRY_START + 2, leg] = self.witness
                substeps[CARRY_START + 3:CARRY_START + 6, leg] = 100 if self.witness else 0
                arrays.update(jp3_t_s=arrays["t_s"], jp3_r58_witness=witness,
                              jp3_r59_substeps=substeps,
                              jp3_r510_candidates=np.zeros((ROWS, 4), np.int32))
            meta = {"events": self.events[key], "controller_tag": row.get("controller_tag")}
            np.savez(t4h / row["t4h_file"], meta_json=np.array(json.dumps(meta)),
                                **arrays)
        result = self.folder / f"{self.arm}_{self.block}.json"
        result.write_text(json.dumps({"meta": {}, "results": list(self.rows.values())}),
                          encoding="utf-8")
        return result, t4h


@pytest.fixture()
def world(tmp_path, selected):
    """b1 / b2 of both arms, all opportunity pairs with a witness after the latch."""
    runs = tmp_path / "runs"
    runs.mkdir()
    selection_file = selected["out"] / "selection.json"
    return {"runs": runs, "plans": selected["out"], "selection": selection_file,
            "selection_sha": hashlib.sha256(selection_file.read_bytes()).hexdigest(),
            "doc": selected["doc"]}


def arms(world, block: str, **kwargs) -> tuple[Arm, Arm]:
    return (Arm(world["runs"], world["doc"], world["plans"], block, "vbk0", **kwargs),
            Arm(world["runs"], world["doc"], world["plans"], block, "vbk", **kwargs))


def decide_args(world, written: dict[str, tuple[Path, Path]], out: Path) -> list[str]:
    args = ["decide", "--selection", str(world["selection"]), "--selection-sha256",
            world["selection_sha"], "--out", str(out)]
    for block, (result, t4h) in written.items():
        args += ["--vbk0", f"{block}={result}", "--vbk0-t4h", f"{block}={t4h}"]
    return args


def judge_args(world, written0, written1, decision: Path, out: Path) -> list[str]:
    args = ["judge", "--selection", str(world["selection"]), "--selection-sha256",
            world["selection_sha"], "--decision", str(decision), "--decision-sha256",
            hashlib.sha256(decision.read_bytes()).hexdigest(), "--out", str(out)]
    for block, (result, t4h) in written0.items():
        args += ["--vbk0", f"{block}={result}", "--vbk0-t4h", f"{block}={t4h}"]
    for block, (result, t4h) in written1.items():
        args += ["--vbk", f"{block}={result}", "--vbk-t4h", f"{block}={t4h}"]
    return args


def run_main(args: list[str], capsys) -> tuple[int, dict, dict]:
    code = judge.main(args)
    last = json.loads(capsys.readouterr().out.splitlines()[-1])
    out = Path(args[args.index("--out") + 1])
    document = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    return code, last, document


@pytest.fixture()
def cwd_elsewhere(tmp_path, monkeypatch):
    other = tmp_path / "elsewhere"
    other.mkdir()
    monkeypatch.chdir(other)
    return other


def build(world, blocks=("b1", "b2"), witness=True, edit=None):
    """Write both arms of ``blocks``; ``edit(block, vbk0, vbk)`` changes them first."""
    written0, written1 = {}, {}
    for block in blocks:
        vbk0, vbk = arms(world, block, witness=witness)
        if edit is not None:
            edit(block, vbk0, vbk)
        written0[block], written1[block] = vbk0.write(), vbk.write()
    return written0, written1


# ---------------------------------------------------------------------- X-13 decide / judge
def test_12b_pass_end_to_end(world, capsys, cwd_elsewhere) -> None:
    written0, written1 = build(world)
    decision = world["runs"] / "decision.json"
    code, last, record = run_main(decide_args(world, written0, decision), capsys)
    assert code == 0 and last["status"] == "decided"
    assert record["blocks"] == ["b1", "b2"] and record["n_opp"] == 334 and record["k"] == 334
    assert record["aa"]["counted_pairs"] == 0 and not record["n_topup"]["needs_b3"]
    out = world["runs"] / "judge.json"
    code, last, report = run_main(judge_args(world, written0, written1, decision, out), capsys)
    assert code == 0 and last["status"] == "pass", report.get("problems")
    assert report["n_opp"] == 334 and report["jp3"]["status"] == "pass"
    assert report["coverage_totals"]["jp3_r59_substeps"] == 334 * 300
    assert report["coverage_totals"]["jp3_r58_witness_carries"] == 334
    assert sum(report["tau_r_trigger_phase"].values()) == sum(
        1 for row in world["doc"]["cell_table"] if row["phase"] == "tau_R") * 2
    assert report["pass_sentence"]["upper_bound_n_opp"] == pytest.approx(1 - 0.05 ** (1 / 334))
    assert set(last) >= {"status", "out", "setting_defects", "not_judgeable", "failures"}


def test_12b_decide_has_no_vbk_argument(world, cwd_elsewhere) -> None:
    written0, _ = build(world)
    args = decide_args(world, written0, world["runs"] / "d.json") + ["--vbk", "b1=x"]
    with pytest.raises(SystemExit) as stop:
        judge.main(args)
    assert stop.value.code == 2


class _FileWatch:
    """Every path opened through ``open`` / ``Path`` reads / ``np.load`` in a block."""

    def __init__(self, monkeypatch) -> None:
        self.paths: list[str] = []
        original_open, original_load = builtins.open, np.load
        original_read_text, original_read_bytes = Path.read_text, Path.read_bytes

        def watched_open(file, *args, **kwargs):
            self.paths.append(str(file))
            return original_open(file, *args, **kwargs)

        def watched_load(file, *args, **kwargs):
            self.paths.append(str(file))
            return original_load(file, *args, **kwargs)

        def watched_read_text(path, *args, **kwargs):
            self.paths.append(str(path))
            return original_read_text(path, *args, **kwargs)

        def watched_read_bytes(path):
            self.paths.append(str(path))
            return original_read_bytes(path)

        monkeypatch.setattr(builtins, "open", watched_open)
        monkeypatch.setattr(np, "load", watched_load)
        monkeypatch.setattr(Path, "read_text", watched_read_text)
        monkeypatch.setattr(Path, "read_bytes", watched_read_bytes)

    def touched(self, marker: str) -> list[str]:
        return [path for path in self.paths if marker in Path(path).name
                or marker in Path(path).parent.name]


def test_12b_aa_floor_stop_and_no_vbk_file_read(world, capsys, cwd_elsewhere,
                                                monkeypatch) -> None:
    """6.3.8: 3 A/A pairs stop with exit 2 ``aa_floor_stop``; the judge then refuses the
    decision before it opens any VBK file (file access watch)."""
    def edit(block, vbk0, vbk):
        if block == "b2":
            for rank in range(3):
                vbk0.rows[vbk0.key_at(rank)]["base"]["t_ready_s"] = READY_S + 30.000002
    written0, written1 = build(world, edit=edit)
    decision = world["runs"] / "decision.json"
    watch = _FileWatch(monkeypatch)
    code, last, record = run_main(decide_args(world, written0, decision), capsys)
    assert code == 2 and last["status"] == "aa_floor_stop"
    assert record["aa"]["counted_pairs"] == 3 and record["exit"] == 2
    assert watch.touched("vbk_") == []
    code, last, _ = run_main(judge_args(world, written0, written1, decision,
                                        world["runs"] / "judge.json"), capsys)
    assert code == 2 and last["status"] == "not_judgeable"
    assert watch.touched("vbk_") == []


def test_12b_aa_two_pairs_and_rounding_do_not_stop(world, capsys, cwd_elsewhere) -> None:
    def edit(block, vbk0, vbk):
        if block == "b2":
            vbk0.rows[vbk0.key_at(0)]["base"]["t_ready_s"] = None
            vbk0.rows[vbk0.key_at(1)]["base"]["t_ready_s"] = READY_S + 30.0000004  # rounds to 30
            vbk0.rows[vbk0.key_at(2)]["base"]["t_ready_s"] = READY_S + 31.0
    written0, _ = build(world, edit=edit)
    code, last, record = run_main(decide_args(world, written0, world["runs"] / "d.json"), capsys)
    assert record["aa"]["counted_pairs"] == 2 and not record["aa"]["is_stop"]
    assert record["categories"]["b2"]["vbk0_ready_unreached"] == 1


def test_12b_decision_sha_and_status_are_checked(world, capsys, cwd_elsewhere,
                                                 monkeypatch) -> None:
    written0, written1 = build(world)
    decision = world["runs"] / "decision.json"
    run_main(decide_args(world, written0, decision), capsys)
    args = judge_args(world, written0, written1, decision, world["runs"] / "judge.json")
    args[args.index("--decision-sha256") + 1] = "0" * 64
    watch = _FileWatch(monkeypatch)
    code, last, _ = run_main(args, capsys)
    assert code == 2 and last["status"] == "not_judgeable" and watch.touched("vbk_") == []


def test_12b_needs_b3_then_b3_below_301_is_not_judgeable(world, capsys, cwd_elsewhere) -> None:
    def edit(block, vbk0, vbk):
        for rank in range(70):  # no trigger on 70 pairs per block: 3 x 97 < 301
            for arm in (vbk0, vbk):
                arm.rows[arm.key_at(rank)]["rod_fault"].update(is_armed=False,
                                                               first_applied_read=None)
    written0, _ = build(world, blocks=("b1", "b2", "b3"), edit=edit)
    first = {block: written0[block] for block in ("b1", "b2")}
    code, last, record = run_main(decide_args(world, first, world["runs"] / "d1.json"), capsys)
    assert code == 0 and last["status"] == "needs_b3"
    code, last, record = run_main(decide_args(world, written0, world["runs"] / "d2.json"),
                                  capsys)
    assert code == 2 and last["status"] == "not_judgeable"
    assert record["reason"].startswith("N_opp")


def test_12b_needs_b4_and_b4_counts_its_opportunity_pairs(world, capsys, cwd_elsewhere) -> None:
    written0, written1 = build(world, blocks=("b1", "b2", "b4"), witness=False)
    first = {block: written0[block] for block in ("b1", "b2")}
    code, last, record = run_main(decide_args(world, first, world["runs"] / "d1.json"), capsys)
    assert last["status"] == "needs_b4" and record["witness_topup"]["k_without_b4"] == 0
    decision = world["runs"] / "d2.json"
    code, last, record = run_main(decide_args(world, written0, decision), capsys)
    assert code == 0 and record["blocks"] == ["b1", "b2", "b4"] and record["k"] == 167
    assert record["n_opp"] == 501


def test_12b_vbk0_not_latched_stops_the_decision(world, capsys, cwd_elsewhere) -> None:
    def edit(block, vbk0, vbk):
        if block == "b1":
            vbk0.rows[vbk0.key_at(5)]["rod_fault"]["latched"]["is_same_read_d1"] = False
    written0, _ = build(world, edit=edit)
    code, last, record = run_main(decide_args(world, written0, world["runs"] / "d.json"), capsys)
    assert code == 2 and last["status"] == "setting_defect"


def _decided(world, capsys, edit=None, blocks=("b1", "b2")):
    written0, written1 = build(world, blocks=blocks, edit=edit)
    decision = world["runs"] / "decision.json"
    code, _, record = run_main(decide_args(world, written0, decision), capsys)
    assert code == 0, record
    return written0, written1, decision


@pytest.mark.parametrize("change", ["vbk_fallback", "trigger_read", "commands", "plan",
                                    "vbk_unlatched", "revision_key", "tag", "delay"])
def test_12b_setting_defects(world, capsys, cwd_elsewhere, change) -> None:
    def edit(block, vbk0, vbk):
        if block != "b1":
            return
        key = vbk.key_at(7)
        record = vbk.rows[key]["rod_fault"]
        if change == "vbk_fallback":
            record["pre_trigger_fallback"] = True
        elif change == "trigger_read":
            record["trigger_read"] += 1
        elif change == "commands":
            record["pre_trigger_commands_sha256"] = "d" * 64
        elif change == "plan":
            record["fault_id"] = "other"
        elif change == "vbk_unlatched":
            record["latched"]["is_same_read_d1"] = False
        elif change == "revision_key":
            vbk.rows[key]["run_extend_start_revision"] = 5
        elif change == "tag":
            vbk.rows[key]["controller_tag"] = "final_C4G2_P3H_LAS_K1"
        elif change == "delay":
            record["delay_reads"] = 1
            vbk0.rows[key]["rod_fault"]["delay_reads"] = 1
    written0, written1, decision = _decided(world, capsys, edit) if change != "delay" else (
        None, None, None)
    if change == "delay":  # a VBK0 delay already stops the decision
        written0, _ = build(world, edit=edit)
        code, last, _ = run_main(decide_args(world, written0, world["runs"] / "d.json"), capsys)
        assert code == 2 and last["status"] == "setting_defect"
        return
    code, last, report = run_main(judge_args(world, written0, written1, decision,
                                             world["runs"] / "judge.json"), capsys)
    assert code == 2 and last["status"] == "setting_defect", report.get("problems")


def test_12b_fault_pairs_name_and_legs() -> None:
    """Audit B1: ':' then ',' split; the name is the first token."""
    assert judge.fault_pairs([[0.0, "FAULT_LIFT_STROKE_LIMIT:FL,RR"]]) == {
        ("FAULT_LIFT_STROKE_LIMIT", "FL"), ("FAULT_LIFT_STROKE_LIMIT", "RR")}
    assert judge.fault_pairs([[0.0, "FAULT_LIFT_STROKE_LIMIT:soil:FR"]]) == {
        ("FAULT_LIFT_STROKE_LIMIT", "FR")}
    assert judge.fault_pairs([[0.0, "FAULT_STOP"]]) == {("FAULT_STOP", "–")}
    assert judge.fault_pairs([[0.0, "WARN_FAULT_LIKE:FL"], [0.0, "INFO_X"]]) == set()
    new = judge.fault_pairs([[0, "FAULT_STROKE_END:FR,RL"]]) - judge.fault_pairs(
        [[0, "FAULT_STROKE_END:FL"]])
    assert new == {("FAULT_STROKE_END", "FR"), ("FAULT_STROKE_END", "RL")}


def test_12b_new_fault_after_a_truncated_row_event_list_fails(world, capsys,
                                                              cwd_elsewhere) -> None:
    """Re-audit C-2: the FAULT sits after 300 INFO events of the T4h meta (the result row's
    ``events`` is cut at 200 and has none); the judge reads the meta list and fails."""
    def edit(block, vbk0, vbk):
        if block == "b1":
            key = vbk.key_at(9)
            vbk.events[key] = [[0.1 * i, "INFO_PRESSURE_X:FL"] for i in range(300)] + [
                [40.0, "FAULT_STROKE_END:FR,RL"]]
            vbk.rows[key]["events"] = [[0.1 * i, "INFO_PRESSURE_X:FL"] for i in range(200)]
            vbk0.events[key] = [[40.0, "FAULT_STROKE_END:FL"]]
    written0, written1, decision = _decided(world, capsys, edit)
    code, last, report = run_main(judge_args(world, written0, written1, decision,
                                             world["runs"] / "judge.json"), capsys)
    assert code == 1 and last["status"] == "failed"
    assert any("new FAULT" in text for text in report["problems"]["failures"])


def test_12b_new_fault_judged_on_ready_missing_pairs_recorded_on_fallback(world, capsys,
                                                                          cwd_elsewhere) -> None:
    def edit(block, vbk0, vbk):
        if block != "b1":
            return
        unready = vbk.key_at(11)
        for arm in (vbk0, vbk):
            arm.rows[unready]["base"]["t_ready_s"] = None
        vbk.events[unready] = [[5.0, "FAULT_STOP"]]
        fallback = vbk.key_at(12)
        for arm in (vbk0, vbk):
            arm.rows[fallback]["rod_fault"]["pre_trigger_fallback"] = True
        vbk.events[fallback] = [[5.0, "FAULT_OTHER"]]
    written0, written1, decision = _decided(world, capsys, edit)
    code, last, report = run_main(judge_args(world, written0, written1, decision,
                                             world["runs"] / "judge.json"), capsys)
    assert code == 1
    assert [text for text in report["problems"]["failures"] if "new FAULT" in text] == [
        f"{plan.key_of(world['doc']['cell_table'][11]['case'], 30)}: new FAULT "
        "[('FAULT_STOP', '–')] (1)"]
    assert len(report["new_faults_recorded"]) == 1


@pytest.mark.parametrize(("delay_s", "is_failure"), [(30.0000004, False), (30.000001, True),
                                                     (None, True)])
def test_12b_ready_rules(world, capsys, cwd_elsewhere, delay_s, is_failure) -> None:
    def edit(block, vbk0, vbk):
        if block == "b2":
            key = vbk.key_at(3)
            vbk.rows[key]["base"]["t_ready_s"] = None if delay_s is None else READY_S + delay_s
    written0, written1, decision = _decided(world, capsys, edit)
    code, last, report = run_main(judge_args(world, written0, written1, decision,
                                             world["runs"] / "judge.json"), capsys)
    assert (code == 1) is is_failure, report["problems"]


def test_12b_jp3_breach_fails_and_missing_inputs_are_not_judgeable(world, capsys,
                                                                   cwd_elsewhere) -> None:
    def edit(block, vbk0, vbk):
        if block == "b1":
            vbk.rows[vbk.key_at(4)]["hydraulics_record"]["extend_bound_check"][
                "jp3a_breach_reads"] = [0, 1, 0, 0]
    written0, written1, decision = _decided(world, capsys, edit)
    code, _, report = run_main(judge_args(world, written0, written1, decision,
                                          world["runs"] / "judge.json"), capsys)
    assert code == 1 and report["jp3"]["status"] == "H-7"
    t4h = written1["b2"][1]
    victim = sorted(t4h.glob("*.npz"))[0]
    with np.load(victim, allow_pickle=False) as data:
        arrays = {name: data[name] for name in data.files if name != "jp3_r59_substeps"}
    np.savez_compressed(victim, **arrays)
    code, last, report = run_main(judge_args(world, written0, written1, decision,
                                             world["runs"] / "judge2.json"), capsys)
    assert code == 2 and last["status"] == "not_judgeable"
    assert any("jp3_r59_substeps missing" in text for text in report["problems"]["not_judgeable"])


def test_12b_zero_judged_rows_are_not_judgeable() -> None:
    problems = judge.Problems()
    judge._judge_jp3({"status": "no_judged_runs"}, 0, problems)
    assert problems.status() == "not_judgeable"


def test_12b_existing_out_and_tool_errors(world, capsys, cwd_elsewhere) -> None:
    written0, _ = build(world)
    out = world["runs"] / "exists.json"
    out.write_text("{}", encoding="utf-8")
    assert judge.main(decide_args(world, written0, out)) == 2
    written0["b1"][0].write_text("{broken", encoding="utf-8")
    code = judge.main(decide_args(world, written0, world["runs"] / "d.json"))
    assert code == 3
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "error"
