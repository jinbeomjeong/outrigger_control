"""436.9 edition 6 fixed before the seal (``jp3_remedy_spec_v6.md`` revision 9, spec 8 Y-8 /
Y-10 / Y-11): the key lists (``ed6_key_lists.py``), the edition 6 12b seed selection
(``jp3_12b_plan.py --edition 6``), the T4h name of a grid row (``run_v5.t4h_file_name``) and
the P-pred input statistics (``jp3_12b_ppred.py``).

Every ``main`` test runs with the working folder elsewhere than the inputs (tool rule (가)).
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import ed6_key_lists as key_lists  # noqa: E402
import jp3_12b_judge as judge  # noqa: E402
import jp3_12b_plan as plan  # noqa: E402
import jp3_12b_ppred as ppred  # noqa: E402
import run_v5  # noqa: E402
from test_jp3_12b_tools import write_noise  # noqa: E402

# ------------------------------------------------------------------------------- T4h names
GRID_JOB = {"case": "R12", "eps": 0.0, "offset_s": 0.05, "setting": "VBL",
            "twin": {"level": "bottom", "leg": "FL", "fs_kN": 0.0, "event": "FS24",
                     "timing": "level"}}


def test_t4h_name_of_a_grid_row_has_its_event_and_timing() -> None:
    assert run_v5.t4h_file_name(GRID_JOB) == "R12_bottom-FL-Fs0-o0.05-FS24-level_VBL.npz"


def test_t4h_name_of_a_g4_twin_is_unchanged() -> None:
    """A twin without grid fields keeps its former name (the P6-0 records)."""
    job = {"case": "R12", "eps": 0.0, "offset_s": 0.0, "setting": "VBJ",
           "twin": {"level": "top", "leg": "FL", "fs_kN": 8.0}}
    assert run_v5.t4h_file_name(job) == "R12_top-FL-Fs8-o0.0_VBJ.npz"


def test_grid_twin_fields_reach_the_case() -> None:
    case, _ = run_v5._case_of(GRID_JOB)
    twin = case.twin
    assert (twin.event, twin.timing, twin.level, twin.leg, twin.fs_kN, twin.offset_s) == (
        "FS24", "level", "bottom", "FL", 0.0, 0.05)
    assert case.path == "event"


# ------------------------------------------------------------------------------- key lists
def _write_grid(path: Path) -> str:
    """A 192-row grid sample of the stats s50 form (64 rows per event)."""
    rows = []
    for event, level, leg, timing, fs in itertools.product(
            ("FS24", "G4", "RE1bF"), ("top", "bottom"), ("FL", "FR", "RL", "RR"),
            ("level", "ready"), (0.0, 2.0, 4.0, 8.0)):
        rows.append({"level": level, "fs_kN": fs, "timing": timing, "leg": leg, "event": event,
                     "offset_s": 0.0, "n_offsets": 4, "n_v0_pass_offsets": 4, "v0_pass": True,
                     "file": "grid_r67_main.json", "key": f"{level}|{fs}|{timing}|{leg}|{event}",
                     "run_id": len(rows), "v0_commands_sha256": "a" * 64})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_key_lists_counts_probe_units_and_declarations(tmp_path, monkeypatch, capsys) -> None:
    grid = tmp_path / "in" / "s50.csv"
    grid.parent.mkdir()
    sha = _write_grid(grid)
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    out = tmp_path / "keys"
    argv = ["--out-dir", str(out), "--grid-sample", str(grid), "--grid-sample-sha256", sha]
    assert key_lists.main(argv) == key_lists.EXIT_WRITTEN
    status = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert status["lines"] == {"sens_keys_v2.json": 184, "confirm_a_keys_v2.json": 216,
                               "confirm_b_grid192.json": 192}
    documents = {name: json.loads((out / name).read_text(encoding="utf-8"))
                 for name in key_lists.OUTPUTS}
    for name, document in documents.items():
        data = (out / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == status["sha256"][name]
        assert document["code_identity"]["head"]
        assert len(document["lines"]) == document["expected_lines"]
        judged = sum(not line["head_only_declared"] for line in document["lines"])
        assert judged == document["expected_j_p3_judged_rows"] > 0
    sens = documents["sens_keys_v2.json"]
    assert sens["probe_seen_units"] == 32
    assert sens["subset"]["g4_twin_choice"] == key_lists.G4_CHOICE_RULE
    assert "without looking at any row result" in key_lists.G4_CHOICE_RULE
    assert {line["job"]["setting"] for line in sens["lines"]} == set(
        run_v5.ED6_SENSITIVITY_SETTINGS)
    assert all(line["v0_pair"]["job"]["setting"] == "V0" for line in sens["lines"])
    confirm_a = documents["confirm_a_keys_v2.json"]
    assert not any(line["probe_seen"] for line in confirm_a["lines"])
    assert confirm_a["expected_j_p3_judged_rows"] == 56  # the other G4 twins x 2 x 4
    regression = {line["key"] for line in confirm_a["lines"]
                  if line["job"]["case"] in ("R1", "R3", "S2")}
    assert regression == {"R1_e0.0", "R1_e0.002", *(f"{case}_e{eps}" for case in ("R3", "S2")
                                                     for eps in run_v5.EPS_ALL)}
    sens_keys = {(line["job"]["setting"], line["key"]) for line in sens["lines"]}
    confirm = {(line["job"]["setting"], line["key"])
               for line in confirm_a["lines"]}
    assert not sens_keys & confirm
    assert len(sens_keys | confirm) == 4 * len(key_lists.main_rows()) == 4 * (72 + 28)
    grid_doc = documents["confirm_b_grid192.json"]
    assert {line["job"]["setting"] for line in grid_doc["lines"]} == {"VBL"}
    assert len({line["t4h_file"] for line in grid_doc["lines"]}) == 192
    assert grid_doc["seed"] == 20261123 and grid_doc["v0_pass_lines"] == 192


def test_key_lists_refuse_an_existing_output_and_another_sample(tmp_path, capsys) -> None:
    grid = tmp_path / "s50.csv"
    sha = _write_grid(grid)
    out = tmp_path / "keys"
    out.mkdir()
    assert key_lists.main(["--out-dir", str(out), "--grid-sample", str(grid),
                           "--grid-sample-sha256", "0" * 64]) == key_lists.EXIT_INPUT
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["status"] == "input_error"
    assert not any(out.iterdir())
    (out / "sens_keys_v2.json").write_text("{}", encoding="utf-8")
    assert key_lists.main(["--out-dir", str(out), "--grid-sample", str(grid),
                           "--grid-sample-sha256", sha]) == key_lists.EXIT_INPUT
    assert (out / "sens_keys_v2.json").read_text(encoding="utf-8") == "{}"
    assert key_lists.main(["--out-dir", str(out), "--grid-sample", str(grid),
                           "--grid-sample-sha256", sha, "--only", "x.json"]) == key_lists.EXIT_INPUT


def test_key_lists_only_writes_the_named_files(tmp_path, capsys) -> None:
    """Change 14: the revision 2 files beside the existing grid file."""
    grid = tmp_path / "s50.csv"
    sha = _write_grid(grid)
    out = tmp_path / "keys"
    out.mkdir()
    (out / "confirm_b_grid192.json").write_text("{}", encoding="utf-8")
    only = "sens_keys_v2.json,confirm_a_keys_v2.json"
    assert key_lists.main(["--out-dir", str(out), "--grid-sample", str(grid),
                           "--grid-sample-sha256", sha, "--only", only]) == key_lists.EXIT_WRITTEN
    assert set(json.loads(capsys.readouterr().out.splitlines()[-1])["sha256"]) == set(
        only.split(","))
    assert (out / "confirm_b_grid192.json").read_text(encoding="utf-8") == "{}"
    document = json.loads((out / "sens_keys_v2.json").read_text(encoding="utf-8"))
    assert document["generation_command"].endswith(f"--only {only}")


def test_key_lists_stop_when_the_counts_differ(tmp_path, monkeypatch) -> None:
    grid = tmp_path / "s50.csv"
    sha = _write_grid(grid)
    monkeypatch.setitem(key_lists.EXPECTED, "sens_keys_v2.json", (183, 104))
    with pytest.raises(key_lists.InputError, match="sens_keys_v2.json: 184 lines"):
        key_lists.build(grid, sha, "cmd")


# ------------------------------------------------------------------------------- 12b seeds
@pytest.fixture()
def noise(tmp_path) -> tuple[Path, str]:
    path = tmp_path / "noise.json"
    return path, write_noise(path)


def _blocks(document: dict) -> list[int]:
    return [document["blocks"][f"b{j}"]["seed_index"] for j in range(1, 5)]


def test_edition_6_seeds_50_to_53_without_dry_plans(tmp_path, noise) -> None:
    scan = tmp_path / "scan"
    scan.mkdir()
    out = tmp_path / "plans"
    document = plan.select(noise[0], scan, out, noise_sha256=noise[1], edition=6)
    assert _blocks(document) == [50, 51, 52, 53] and document["seed_repeats"] == 0
    assert document["edition"] == 6 and document["reserved_seeds"] == list(
        plan.ED6_RESERVED_SEEDS)
    assert document["dry"] == {"seeds": [], "pairs": 0, "runs": {}, "union_check": None}
    assert sorted(path.name for path in out.iterdir()) == sorted(
        [*(f"b{j}_{kind}" for j in range(1, 5) for kind in ("plan.json", "keys.txt")),
         "selection.json"])
    assert document["run_commands"][0].startswith("R79_V5_SETTING=VBKL0 ")
    assert document["run_commands"][-1].startswith("R79_V5_SETTING=VBKL ")


def test_edition_6_reserved_seeds_raise_by_10() -> None:
    cases = ["L2|g6|0|x"]
    assert plan.block_seeds(cases, frozenset(), (22, 23, 24, 25), plan.ED6_RESERVED_SEEDS) == (
        (32, 33, 34, 35), 1)
    assert plan.block_seeds(cases, frozenset(), (80, 81, 82, 83), plan.ED6_RESERVED_SEEDS) == (
        (100, 101, 102, 103), 2)
    assert set(plan.ED6_RESERVED_SEEDS) >= {25, 80, 81, *range(90, 94), *range(95, 100)}


def test_edition_6_excluded_files_are_not_opened_and_key_lists_count(tmp_path, noise,
                                                                     monkeypatch) -> None:
    """A blinded file is left out by path (never read); a key list of its keys collides."""
    scan = tmp_path / "scan"
    blind = scan / "02_control" / "j9_runs" / "r" / "cdry_a1"
    blind.mkdir(parents=True)
    (blind / "VBK_c92.json").write_text(json.dumps({"key": "L2|s50|g6|0|x0|top|Fs0"}),
                                        encoding="utf-8")
    (blind / "VBK0_c92.json").write_text(json.dumps({"key": "L2|s92|g6|0|x0|top|Fs0"}),
                                         encoding="utf-8")
    original = Path.read_bytes

    def guarded(path: Path) -> bytes:
        assert path.name != "VBK_c92.json", "an excluded file was opened"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    excludes = ("02_control/j9_runs/r/cdry_a1/VBK_c92*",)
    document = plan.select(noise[0], scan, tmp_path / "p1", noise_sha256=noise[1], edition=6,
                           excludes=excludes)
    assert _blocks(document) == [50, 51, 52, 53]
    assert document["inputs"]["scan_excluded_files"] == [
        "02_control/j9_runs/r/cdry_a1/VBK_c92.json"]
    assert [row["path"] for row in document["scan"]["files"]] == [
        "02_control/j9_runs/r/cdry_a1/VBK0_c92.json"]
    listed = tmp_path / "c92_keys.txt"
    listed.write_text("L2|s92|g6|0|x0|top|Fs0\nL2|s50|g6|1|x1|top|Fs0\n", encoding="utf-8")
    document = plan.select(noise[0], scan, tmp_path / "p2", noise_sha256=noise[1], edition=6,
                           excludes=excludes, key_lists=(listed,))
    assert _blocks(document) == [60, 61, 62, 63] and document["seed_repeats"] == 1
    assert document["inputs"]["scan_keys_files"] == [str(listed)]


def test_edition_5_document_and_options_unchanged(tmp_path, noise) -> None:
    scan = tmp_path / "scan"
    scan.mkdir()
    document = plan.select(noise[0], scan, tmp_path / "p", noise_sha256=noise[1])
    assert "edition" not in document and "reserved_seeds" not in document
    assert set(document["inputs"]) == {"noise", "scan_root", "scan_extra"}
    assert _blocks(document) == [40, 41, 42, 43] and document["dry"]["seeds"] == [92, 93]
    with pytest.raises(plan.NotUsable, match="edition 6 options"):
        plan.select(noise[0], scan, tmp_path / "q", noise_sha256=noise[1],
                    excludes=("x*",))


def test_edition_6_main_from_another_folder(tmp_path, noise, monkeypatch, capsys) -> None:
    scan = tmp_path / "scan"
    scan.mkdir()
    tests = tmp_path / "05_tests"
    tests.mkdir()
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    monkeypatch.setattr(plan.fixed, "NOISE_VB_SHA256", noise[1])
    monkeypatch.setattr(plan.select, "__defaults__", (noise[1],))
    out = tmp_path / "x11"
    assert plan.main(["--noise", str(noise[0]), "--scan-root", str(scan), "--scan-extra",
                      str(tests), "--out-dir", str(out), "--edition", "6"]) == 0
    status = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert status["seeds"] == [50, 51, 52, 53] and (out / "selection.json").is_file()


# ------------------------------------------------------------------------------- P-pred
READY_S = 60.0
AA30_EXTRA_S = 35.0


def _cell_table(n_tau_c: int = 84, n_tau_r: int = 83) -> list[dict]:
    phases = ["tau_C"] * n_tau_c + ["tau_R"] * n_tau_r
    return [{"case": f"L2|g6|{i}|x{i}|top|Fs0", "phase": phase}
            for i, phase in enumerate(phases)]


def _line(case: str, block_seed: int, *, ready_s: float | None, injected: bool = True,
          fallback: bool = False, latched: bool = True) -> tuple[str, judge.Line]:
    level, rest = case.split("|", 1)
    key = f"cand=current#{level}|s{block_seed}|{rest}"
    record = {"is_armed": injected, "applied_periods": 5 if injected else 0,
              "first_applied_t_s": 1.0 if injected else None, "pre_trigger_fallback": fallback,
              "latched": {"is_same_read_d1": latched}}
    row = {"rod_fault": record, "base": {"t_ready_s": ready_s}}
    return key, judge.Line(key, row, Path("unused.npz"))


BLOCK_SEEDS = {"b1": 50, "b2": 51, "b4": 53}


def pattern_blocks(table: list[dict], pattern: dict) -> dict[str, dict[str, judge.Line]]:
    """VBKL0 lines of a per-case code string per block: ``0`` reached READY, ``1`` READY not
    reached, ``p`` no trigger (a stall before the trigger); ``aa30`` cases reach b2 35 s
    later than b1."""
    aa30 = set(pattern["aa30"])
    blocks = {}
    for block, seed in BLOCK_SEEDS.items():
        lines = {}
        for i, (row, code) in enumerate(zip(table, pattern[block], strict=True)):
            ready = None if code == "1" else READY_S
            if block == "b2" and i in aa30:
                ready += AA30_EXTRA_S
            key, line = _line(row["case"], seed, ready_s=ready, injected=code != "p")
            lines[key] = line
        blocks[block] = lines
    return blocks


S41_ROWS = ((1, 0.1029, 0.073145), (20261124, 0.10364, 0.073545))
"""Stats ``s41_keys_review.json`` part 2, n_par 20000 x n_rep 10: (seed, P(n23 > 9),
P(n23 > 10)) on the edition 5 pattern."""
ED5_STALLS = {0: (1, 1), 1: (1, 1), 2: (1, 0), 3: (0, 1), 84: (1, 0)}
"""Edition 5 VBK0 b1 / b2 stall pattern (erratum 8 8-1, stats s70 ``ed5_replay``)."""


def _ed5_pattern() -> dict:
    codes = {block: ["0"] * 167 for block in ("b1", "b2", "b4")}
    for i, stalls in ED5_STALLS.items():
        for block, stall in zip(("b1", "b2"), stalls, strict=True):
            codes[block][i] = str(stall)
    return {**{block: "".join(text) for block, text in codes.items()}, "aa30": [10]}


def _ed5_stats() -> ppred.InputStatistics:
    table = _cell_table()
    return ppred.input_statistics({"cell_table": table}, pattern_blocks(table, _ed5_pattern()))


def test_ppred_input_statistics_of_the_edition_5_pattern() -> None:
    stats = _ed5_stats()
    result = ppred.k_allow_pred(stats, n_par=10, n_rep=2)
    record = ppred.decision_record(stats, result)
    assert record["K_c"] == {"tau_C": 6, "tau_R": 1}
    assert record["N_c"] == {"tau_C": 168, "tau_R": 166}
    assert (record["a30"], record["n_both"]) == (1, 162)
    assert record["cases"]["L2|g6|0|x0|top|Fs0"] == {"k": 2, "n": 2}
    assert record["left_out_lines"] == {judge.NO_TRIGGER: 0, judge.PRE_FALLBACK: 0}
    assert record["blocks_used"] == ["b1", "b2"] and "b4" not in record
    assert record["p_pred_seed"] == ppred.P_PRED_SEED == 20261125
    assert record["replay_lines"] == 334 - 7
    assert record["p_n23_gt_k"] <= ppred.ALPHA < record["p_n23_gt_k_minus_1"]


def test_ppred_k_allow_of_the_edition_5_pattern_with_the_sealed_seed() -> None:
    """Spec 6.4 ("판 5 자료로 계산하면 10") with 20000 x 10 draws (change 14): P(n23 > 9) and
    P(n23 > 10) equal stats ``s41_keys_review`` (``s70 inner_pred``, same generator) exactly,
    so the draws are the same; k_allow is 10 for every seed s41 tried."""
    stats = _ed5_stats()
    result = ppred.k_allow_pred(stats)
    assert (result["seed"], result["n_par"], result["n_rep"]) == (20261125, 20000, 10)
    assert result["k_allow"] == 10
    assert (result["p_n23_gt_k_minus_1"], result["p_n23_gt_k"]) == (0.102945, 0.072775)
    assert ppred.k_allow_pred(stats) == result  # a new generator per call
    for seed, p_gt9, p_gt10 in S41_ROWS:
        other = ppred.k_allow_pred(stats, seed=seed)
        assert other["k_allow"] == 10, seed
        assert (other["p_n23_gt_k_minus_1"], other["p_n23_gt_k"]) == (p_gt9, p_gt10), seed


S71_INPUTS = {
    11: ({"b1": {"1": [], "p": [10, 34, 54, 65]},
          "b2": {"1": [34, 65, 108], "p": [10, 54, 109]},
          "b4": {"1": [4, 15, 16, 51, 53, 75, 149], "p": [21, 40, 61, 65, 73, 83, 127]}},
         [], 8, 18),
    12: ({"b1": {"1": [], "p": [29, 135]}, "b2": {"1": [], "p": []},
          "b4": {"1": [39, 42, 47, 101, 106, 117], "p": [12, 62, 85, 91, 104, 107, 141, 165]}},
         [98], 5, 15),
    13: ({"b1": {"1": [31, 56, 144], "p": [14]}, "b2": {"1": [11, 14, 144], "p": [31]},
          "b4": {"1": [10, 30, 44, 79, 141], "p": [40, 42, 53]}},
         [20, 145], 12, 19),
}
"""Stats ``s71_ppred_rev9.gen`` inputs (generator seeds 11 / 12 / 13; truth T0 with rho 0.6,
f_pre 0.5, p_TRw = 2 p_C, independent TRw case rates) as sparse codes per block (``1`` READY
not reached, ``p`` stall before the trigger = no trigger), the A/A > 30 s cases, and s71's
``pick(inner(default_rng(20261125), v, inputs(v, "spec"), b4mode, n_par, n_rep))`` for b4mode
None and "B", the same k at 1000 x 20 and at 20000 x 10 (computed 2026-11-24 with the stats
script; the draws were equal bit for bit at both)."""


def _s71_pattern(sparse: dict, aa30: list[int]) -> dict:
    pattern = {"aa30": aa30}
    for block, codes in sparse.items():
        text = ["0"] * 167
        for code, cases in codes.items():
            for i in cases:
                text[i] = code
        pattern[block] = "".join(text)
    return pattern


@pytest.mark.parametrize("gen_seed", sorted(S71_INPUTS))
def test_ppred_k_allow_equals_stats_s71_on_its_synthetic_inputs(gen_seed) -> None:
    """Change 13: the b1 / b2 decision and the b4 case B recalculation give s71's k with the
    sealed seed (each a new generator)."""
    sparse, aa30, k_b12, k_b124 = S71_INPUTS[gen_seed]
    table = _cell_table()
    blocks = pattern_blocks(table, _s71_pattern(sparse, aa30))
    stats = ppred.input_statistics({"cell_table": table}, blocks)
    b4 = ppred.b4_input(blocks["b4"])
    assert ppred.k_allow_pred(stats)["k_allow"] == k_b12
    with_b4 = ppred.k_allow_pred(stats, b4)
    assert with_b4["k_allow"] == k_b124
    record = ppred.decision_record(stats, with_b4, b4)
    stalled = len(sparse["b4"]["1"])
    assert record["b4"]["K_TRw"] == stalled
    assert record["b4"]["N_TRw"] == 167 - len(sparse["b4"]["p"])
    assert record["b4"]["opportunities"] == 167 - stalled - len(sparse["b4"]["p"])


def test_ppred_left_out_lines_and_partial_cases() -> None:
    """G-4: no trigger / pre-trigger fallback lines leave n_i < 2; such a case is out of the
    rho bootstrap and the A/A count, and its posterior uses n_i."""
    table = _cell_table(2, 2)
    blocks = {"b1": dict([_line(table[0]["case"], 50, ready_s=None),
                          _line(table[1]["case"], 50, ready_s=READY_S, injected=False),
                          _line(table[2]["case"], 50, ready_s=READY_S, fallback=True),
                          _line(table[3]["case"], 50, ready_s=READY_S)]),
              "b2": dict([_line(row["case"], 51, ready_s=READY_S + 1.0) for row in table])}
    stats = ppred.input_statistics({"cell_table": table}, blocks)
    assert stats.left_out == {judge.NO_TRIGGER: 1, judge.PRE_FALLBACK: 1}
    assert [(case.k, case.n) for case in stats.cases.values()] == [(1, 2), (0, 1), (0, 1),
                                                                    (0, 2)]
    assert (stats.K("tau_C"), stats.N("tau_C"), stats.K("tau_R"), stats.N("tau_R")) == (
        1, 3, 0, 3)
    assert (stats.a30, stats.n_both) == (0, 1)
    draws = ppred.n23_draws(np.random.default_rng(1), stats, None, 5, 4)
    assert draws.shape == (20,) and draws.max() <= 5


def test_ppred_b4_is_its_own_trw_cell() -> None:
    """G-2 case B: K_TRw / N_TRw from the kept b4 lines, every reached b4 line in the replay;
    the b1 / b2 cases and parameters are unchanged."""
    table = _cell_table(2, 2)
    blocks = {block: dict(_line(row["case"], seed, ready_s=READY_S) for row in table)
              for block, seed in (("b1", 50), ("b2", 51))}
    stats = ppred.input_statistics({"cell_table": table}, blocks)
    b4 = ppred.b4_input(dict([_line(table[0]["case"], 53, ready_s=READY_S),
                              _line(table[1]["case"], 53, ready_s=None),
                              _line(table[2]["case"], 53, ready_s=READY_S, injected=False),
                              _line(table[3]["case"], 53, ready_s=READY_S, fallback=True)]))
    assert (b4.stalled, b4.kept, b4.opportunities) == (1, 2, 1)
    assert b4.left_out == {judge.NO_TRIGGER: 1, judge.PRE_FALLBACK: 1}
    result = ppred.k_allow_pred(stats, b4, n_par=20, n_rep=5)
    assert result["replay_lines"] == 8 + 1
    record = ppred.decision_record(stats, result, b4)
    assert record["blocks_used"] == ["b1", "b2", "b4"]
    assert record["b4"] == {"K_TRw": 1, "N_TRw": 2, "opportunities": 1,
                            "left_out_lines": {judge.NO_TRIGGER: 1, judge.PRE_FALLBACK: 1}}
    assert record["K_c"] == {"tau_C": 0, "tau_R": 0}


def test_ppred_unlatched_line_and_missing_block_stop() -> None:
    table = _cell_table(1, 1)
    unlatched = dict([_line(table[0]["case"], 50, ready_s=READY_S, latched=False)])
    with pytest.raises(ppred.InputStop, match="not latched"):
        ppred.input_statistics({"cell_table": table}, {"b1": unlatched, "b2": {}})
    with pytest.raises(ppred.InputStop, match="missing"):
        ppred.input_statistics({"cell_table": table}, {"b1": {}})
    with pytest.raises(ppred.InputStop, match="b4 .* not latched"):
        ppred.b4_input(unlatched)
