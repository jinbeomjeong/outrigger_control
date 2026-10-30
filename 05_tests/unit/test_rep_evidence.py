"""Representative-set evidence (``04_scripts/03_control/s9/rep_evidence.py``, spec 432.4 E1 /
E5): pair construction, the monotonicity rule and missing input files. Synthetic inputs only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))

import rep_evidence as rep  # noqa: E402


def _record(verdict: str, ready_s: float, min_force_kN: float, max_stroke_mm: float = 600.0,
            gap_mm: float = 40.0) -> dict:
    return {"verdict": verdict, "ready_s": ready_s, "min_force_kN": min_force_kN,
            "max_stroke_mm": max_stroke_mm, "gap_ready_mm": gap_mm}


def _p3b_summary_row(is_pass: bool, ready_s: float, min_force_N: list[float]) -> dict:
    checks = {check: True for check in rep.P3B_PASS_CHECKS}
    checks["P3-6_within"] = is_pass
    return {"checks": checks,
            "P3-6_ready": {"t_ready_after_loop_start_s": ready_s},
            "P3-3_leg_force": {"F_min_after_N": min_force_N},
            "P3-5_clearance_stroke": {"s_motor_max_m": [0.5, 0.6],
                                      "rut_clearance_min_after_first_ready_m": 0.04},
            "P3-4_attitude": {"p34_absmax_deg": 0.02}}


# ---------------------------------------------------------------------------- records
def test_normalize_record_reads_nested_run_and_bool_pass():
    record = {"key": "ref|G1|top|Fs4|PA", "pass": False,
              "run": {"t_ready_s": 50.0, "min_true_Fcyl_after_off_kN": 60.0,
                      "max_motor_stroke_mm": 610.0, "att_end_deg": [0.01, -0.03]}}
    normalized = rep.normalize_record(record)
    assert normalized["id"] == "ref|G1|top|Fs4|PA"
    assert normalized["verdict"] == "fail"
    assert normalized["ready_s"] == 50.0
    assert normalized["min_force_kN"] == 60.0
    assert normalized["max_stroke_mm"] == 610.0
    assert normalized["att_end_absmax_deg"] == pytest.approx(0.03)


def test_merge_by_id_keeps_first_source():
    harness = {"p3b": {"a": {"id": "a", "verdict": "pass"}},
               "slope": {"a": {"id": "a", "verdict": "fail"}, "b": {"id": "b"}}}
    merged = rep.merge_by_id(harness)
    assert merged["a"]["source"] == "p3b"
    assert merged["a"]["verdict"] == "pass"
    assert merged["b"]["source"] == "slope"


# ---------------------------------------------------------------------------- E1 pairs
def test_p3b_pairs_map_case_name_to_harness_id_and_variable():
    chrono = {"P3b_J2_B_top_Fs4": _record("pass", 60.0, 60.0),
              "P3b_G1_A_middle_Fs4": _record("pass", 50.0, 60.0),
              "P3b_S1_B_top_Fs0": _record("pass", 50.0, 60.0)}
    harness = {"base|J2|B|top|Fs4": _record("pass", 58.0, 61.0)}
    pairs = rep.build_pairs(chrono, harness, curated=())
    by_case = {pair["chrono_case"]: pair for pair in pairs}
    assert [pair["chrono_case"] for pair in pairs] == sorted(chrono)
    assert by_case["P3b_J2_B_top_Fs4"]["harness_id"] == "base|J2|B|top|Fs4"
    assert by_case["P3b_J2_B_top_Fs4"]["variable"] == "A1 soil / B3 pad"
    assert by_case["P3b_G1_A_middle_Fs4"]["variable"] == "B1 auger"
    assert by_case["P3b_S1_B_top_Fs0"]["variable"] == "B2 F_s"
    assert by_case["P3b_G1_A_middle_Fs4"]["chrono_version_note"].startswith("equivalent")
    assert by_case["P3b_J2_B_top_Fs4"]["chrono_version_note"].startswith("not equivalent")
    assert by_case["P3b_S1_B_top_Fs0"]["harness"] is None
    assert by_case["P3b_S1_B_top_Fs0"]["side"] is None


def test_curated_pair_carries_version_and_src():
    curated = (("A2 roll test", "case_x", "H1|J1|A|top|roll_pos", {"verdict": "pass"},
                "v1", "spec 1"),)
    harness = {"H1|J1|A|top|roll_pos": _record("fail", 50.0, 60.0)}
    (pair,) = rep.build_pairs({}, harness, curated=curated)
    assert pair["chrono"] == {"verdict": "pass", "version": "v1", "src": "spec 1"}
    assert pair["delta"] == {"verdict_same": False}
    assert pair["side"] == "conservative"  # harness verdict worse than Chrono


def test_summary_counts_verdict_matches_and_no_twin():
    chrono = {"P3b_G1_B_top_Fs4": _record("pass", 50.0, 60.0),
              "P3b_J1_B_top_Fs4": _record("fail", 80.0, 60.0),
              "P3b_J2_B_top_Fs4": _record("pass", 50.0, 60.0)}
    harness = {"base|G1|B|top|Fs4": _record("pass", 49.0, 60.0),
               "base|J1|B|top|Fs4": _record("pass", 70.0, 60.0)}
    summary = rep.summarize_pairs(rep.build_pairs(chrono, harness, curated=()))
    assert summary["n_pairs"] == 3
    assert summary["n_with_harness"] == 2
    assert summary["verdict_same"] == 1
    assert summary["by_variable_side"] == {
        "A1 soil": {"representative": 1, "optimistic": 1, "no_twin": 1}}
    assert summary["d_ready_s_chrono_minus_harness"] == {"n": 2, "min": 1.0, "max": 10.0,
                                                         "mean": 5.5}


@pytest.mark.parametrize(("harness", "chrono", "side"), [
    (_record("pass", 60.0, 60.0), _record("pass", 62.0, 61.0), "representative"),
    (_record("pass", 60.0, 60.0), _record("pass", 66.0, 60.0), "optimistic"),
    (_record("pass", 60.0, 67.0), _record("pass", 60.0, 60.0), "optimistic"),
    (_record("pass", 60.0, 60.0, gap_mm=60.0), _record("pass", 60.0, 60.0, gap_mm=45.0),
     "optimistic"),
    (_record("pass", 60.0, 60.0), _record("pass", 54.0, 60.0), "conservative"),
    (_record("pass", 60.0, 50.0), _record("pass", 60.0, 60.0), "conservative"),
    (_record("pass", 60.0, 60.0), _record("pass", 54.0, 50.0), "mixed"),
])
def test_classify_pair_sides(harness, chrono, side):
    assert rep.classify_pair(harness, chrono)[0] == side


def test_classify_pair_uses_largest_magnitude_of_chrono_lists():
    harness = _record("pass", 60.0, 60.0)
    chrono = dict(_record("pass", 60.0, 60.0), att_end_absmax_deg=[0.01, -0.05])
    harness["att_end_absmax_deg"] = 0.02
    _, deltas = rep.classify_pair(harness, chrono)
    assert deltas["d_att_end_absmax_deg"] == pytest.approx(0.03)


def test_classify_pair_without_verdict_has_no_side():
    assert rep.classify_pair(None, {"verdict": "pass"}) == (None, {})
    assert rep.classify_pair({"verdict": None}, {"verdict": "pass"}) == (None, {})


# ---------------------------------------------------------------------------- E5 monotonicity
def _levels(*rows: tuple[str, float, float]) -> dict:
    return {level: _record("pass", ready, force) for level, ready, force in rows}


def test_study_counts_direction_and_monotone_with_tolerance():
    groups = {
        "rising": _levels(("a", 50.0, 60.0), ("b", 55.0, 60.1), ("c", 60.0, 60.0)),
        "dip": _levels(("a", 50.0, 60.0), ("b", 45.0, 60.0), ("c", 52.0, 60.0)),
        "flat_jitter": _levels(("a", 50.0, 60.0), ("b", 50.4, 60.0), ("c", 50.1, 60.0)),
    }
    study = rep.monotonicity_study("t", groups, ["a", "b", "c"])
    ready = study["metrics"]["ready_s"]
    assert study["n_groups"] == 3
    assert ready == {"up": 2, "down": 0, "flat": 1, "monotone": 2, "n": 3}
    assert study["metrics"]["min_force_kN"]["flat"] == 3
    assert study["non_monotone"] == [{"group": "dip", "metric": "ready_s",
                                      "seq": [50.0, 45.0, 52.0]}]


def test_study_ranks_verdicts_and_lists_verdict_changes():
    groups = {"g": {"a": _record("pass", 50.0, 60.0),
                    "b": _record("stroke_limited_fail", 50.0, 60.0)}}
    study = rep.monotonicity_study("t", groups, ["a", "b"])
    assert study["metrics"]["rank"]["up"] == 1
    assert study["verdict_changes"] == [{"group": "g",
                                         "verdicts": ["pass", "stroke_limited_fail"]}]


def test_study_skips_incomplete_groups_and_missing_metrics():
    groups = {"short": _levels(("a", 50.0, 60.0)),
              "no_ready": {"a": _record("pass", 50.0, 60.0), "b": _record("pass", 50.0, 60.0)}}
    groups["no_ready"]["b"]["ready_s"] = None
    study = rep.monotonicity_study("t", groups, ["a", "b"])
    assert study["n_groups"] == 1
    assert study["metrics"]["ready_s"]["n"] == 0
    assert study["metrics"]["min_force_kN"]["n"] == 1


def test_group_p3b_by_part_moves_one_part_to_the_level():
    p3b = {"base|J1|B|top|Fs0": {"x": 0}, "base|J1|B|top|Fs8": {"x": 8},
           "base|J1|B|middle|Fs0": {"x": 1}, "other|J1|B|top|Fs0": {"x": 9}}
    assert rep.group_p3b_by_part(p3b, 4) == {"J1|B|top": {"Fs0": {"x": 0}, "Fs8": {"x": 8}},
                                             "J1|B|middle": {"Fs0": {"x": 1}}}
    assert rep.group_p3b_by_part(p3b, 3)["J1|B|Fs0"] == {"top": {"x": 0}, "middle": {"x": 1}}


def test_group_slope_by_ratio_joins_flat_h3_and_h1_rows():
    slope = {"H1|J1|B|top|flat": "flat", "H3|J1|B|top|roll_pos@k0.5": "k05",
             "H1|J1|B|top|roll_pos": "k1"}
    assert rep.group_slope_by_ratio(slope) == {
        "J1|B|top|roll_pos": {"k0.5": "k05", "k1.0": "k1", "k0": "flat"}}


# ---------------------------------------------------------------------------- missing inputs
def _write_records(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"records": records}), encoding="utf-8")


def _harness_row(record_id: str, verdict: str = "pass") -> dict:
    return {"id": record_id, "verdict": verdict, "t_ready_s": 50.0, "min_force_kN": 60.0,
            "max_stroke_mm": 600.0, "rut_ready_mm": 40.0}


@pytest.fixture
def minimal_repo(tmp_path: Path) -> Path:
    """A repo with the P3b summary and the required R2DS / x426 tables, no x426 B files."""
    summary = {"rows": {"P3b_J1_B_top_Fs4": _p3b_summary_row(True, 55.0, [60e3, 62e3])}}
    summary_path = tmp_path / rep.P3B_SUMMARY_REL
    summary_path.parent.mkdir(parents=True)
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    files = rep.harness_files(tmp_path)
    _write_records(files["p3b"], [_harness_row("base|J1|B|top|Fs4")])
    _write_records(files["slope"], [_harness_row("H1|J1|B|top|flat")])
    for key in ("g6", "h6", "C", "D"):
        _write_records(files[key], [])
    return tmp_path


def test_load_harness_skips_missing_files(minimal_repo: Path):
    harness = rep.load_harness(rep.harness_files(minimal_repo))
    assert set(harness) == {"p3b", "slope", "g6", "h6", "C", "D"}


def test_main_runs_without_optional_x426_b_files(minimal_repo: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    rep.main(["rep_evidence.py", str(minimal_repo), str(out_dir)])
    pairs = json.loads((out_dir / rep.PAIRS_FILE_NAME).read_text(encoding="utf-8"))
    studies = json.loads((out_dir / rep.MONOTONICITY_FILE_NAME).read_text(encoding="utf-8"))
    assert pairs["meta"]["script"] == rep.SCRIPT_REL
    assert len(pairs["meta"]["script_sha256"]) == 64
    p3b_pair = pairs["pairs"][0]
    assert p3b_pair["harness"]["source"] == "p3b"
    assert p3b_pair["delta"]["verdict_same"] is True
    assert pairs["summary"]["n_with_harness"] == 1  # curated ids have no twin here
    by_name = {study["variable"]: study for study in studies["studies"]}
    assert by_name["B2 F_s 4 -> 0 on slope (x426 B2)"]["n_groups"] == 0


def test_missing_p3b_summary_raises(minimal_repo: Path, tmp_path: Path):
    (minimal_repo / rep.P3B_SUMMARY_REL).unlink()
    with pytest.raises(FileNotFoundError):
        rep.main(["rep_evidence.py", str(minimal_repo), str(tmp_path / "out")])


def test_missing_required_table_raises_key_error(minimal_repo: Path):
    rep.harness_files(minimal_repo)["h6"].unlink()
    harness = rep.load_harness(rep.harness_files(minimal_repo))
    with pytest.raises(KeyError, match="h6"):
        rep.build_studies(harness)
