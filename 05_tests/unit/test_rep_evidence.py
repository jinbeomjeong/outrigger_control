"""Representative-set evidence (``04_scripts/03_control/s9/rep_evidence.py``, spec 432.4 E1 /
E5): pair construction, the monotonicity rule and missing input files. Synthetic inputs only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))

import rep_evidence as rep  # noqa: E402


def _record(verdict: str, ready_s: float, min_force_kN: float,
            max_stroke_reading_mm: float = 600.0, gap_mm: float = 40.0) -> dict:
    return {"verdict": verdict, "ready_s": ready_s, "min_force_kN": min_force_kN,
            "max_stroke_reading_mm": max_stroke_reading_mm, "gap_ready_mm": gap_mm}


def _write_stroke_record(case_dir: Path, reading_m: list[list[float]]) -> None:
    """A run ``record/record.npz`` with only the controller stroke reading (samples x legs)."""
    path = case_dir / rep.RECORD_NPZ_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, **{rep.STROKE_READING_KEY: np.asarray(reading_m)})


def _p3b_summary_row(is_pass: bool, ready_s: float | None, min_force_N: list[float],
                     gap_m: float | None = 0.04) -> dict:
    checks = {check: True for check in rep.P3B_PASS_CHECKS}
    checks["P3-6_within"] = is_pass
    return {"checks": checks,
            "P3-6_ready": {"t_ready_after_loop_start_s": ready_s},
            "P3-3_leg_force": {"F_min_after_N": min_force_N},
            "P3-5_clearance_stroke": {"s_motor_max_m": [0.5, 0.6],
                                      "rut_clearance_min_after_first_ready_m": gap_m},
            "P3-4_attitude": {"p34_absmax_deg": 0.02}}


def _write_rejudge(repo: Path, batch: str, case: str, p3b_block: dict) -> None:
    path = rep._rejudge_path(repo, batch, case)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"p3b": p3b_block}), encoding="utf-8")


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
    assert normalized["max_stroke_reading_mm"] == 610.0  # max(plant.sref) = the reading
    assert normalized["max_stroke_true_mm"] is None  # not stored by the harness
    assert normalized["att_end_absmax_deg"] == pytest.approx(0.03)


def test_p3b_block_stroke_is_the_true_rod_stroke_per_leg():
    values = rep.chrono_values_from_p3b_block(_p3b_summary_row(True, 55.0, [60e3]))
    assert values["max_stroke_true_mm"] == pytest.approx([500.0, 600.0])
    assert "max_stroke_reading_mm" not in values
    assert "max_stroke_mm" not in values


def test_read_stroke_reading_max_per_leg(tmp_path: Path):
    _write_stroke_record(tmp_path, [[0.40, 0.50, 0.30, 0.20], [0.45, 0.48, 0.35, 0.10]])
    reading = rep.read_stroke_reading_max_mm(tmp_path / rep.RECORD_NPZ_REL)
    assert reading == pytest.approx([450.0, 500.0, 350.0, 200.0])
    assert rep.read_stroke_reading_max_mm(tmp_path / "absent.npz") is None


def test_stroke_pairs_compare_reading_with_reading_only():
    """The Chrono true stroke must not be differenced with the harness reading."""
    harness = dict(_record("pass", 60.0, 60.0, max_stroke_reading_mm=516.3),
                   max_stroke_true_mm=None)
    chrono = dict(_record("pass", 60.0, 60.0), max_stroke_true_mm=[495.0, 500.4],
                  max_stroke_reading_mm=[500.0, 505.1])
    _, deltas = rep.classify_pair(harness, chrono)
    assert deltas["d_max_stroke_reading_mm"] == pytest.approx(-11.2)
    assert "d_max_stroke_true_mm" not in deltas
    assert "d_max_stroke_mm" not in deltas


def test_curated_readings_are_added_by_harness_id(tmp_path: Path):
    harness_id = "H6|J2|B|top|flat|m1.1"
    batch, case = rep.CURATED_RECORD_DIRS[harness_id]
    _write_stroke_record(tmp_path / rep.CHRONO_RESULTS_REL / batch / case,
                         [[0.5691, 0.5345, 0.5927, 0.5683]])
    readings = rep.curated_stroke_readings(tmp_path)
    curated = (("B4 weight", case, harness_id,
                {"verdict": "fail", "max_stroke_true_mm": 586.9}, "v", "spec"),)
    harness = {harness_id: _record("fail", 90.0, 70.0, max_stroke_reading_mm=571.6)}
    (pair,) = rep.build_pairs({}, harness, curated=curated, curated_readings=readings)
    assert pair["chrono"]["max_stroke_true_mm"] == 586.9
    assert pair["chrono"]["stroke_record"] == f"07_results/S9/{batch}/{case}/record/record.npz"
    assert pair["delta"]["d_max_stroke_reading_mm"] == pytest.approx(21.1)
    others = [entry for key, entry in readings.items() if key != harness_id]
    assert all(entry["max_stroke_reading_mm"] is None for entry in others)
    assert rep.missing_stroke_records([pair]) == []


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
    assert summary["d_max_stroke_reading_mm_chrono_minus_harness"] == {
        "n": 2, "min": 0.0, "max": 0.0, "mean": 0.0}


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
    summary = {"source_batch": "07_results/S9/batch_P3b_test",
               "rows": {"P3b_J1_B_top_Fs4": _p3b_summary_row(True, 55.0, [60e3, 62e3])}}
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
    assert "pending" not in pairs
    assert "-13 mm" in pairs["meta"]["h6_margin"]
    assert "+23 mm" in pairs["meta"]["h6_margin"]
    # no RV2 / RV3 run folders: 4 + 1 + 1 pairs dropped and listed
    assert len(pairs["meta"]["missing_chrono_inputs"]) == 6
    # no final run folders: every final pair is dropped and listed apart
    assert pairs["final_pairs"] == []
    assert len(pairs["meta"]["missing_final_inputs"]) == len(rep.FINAL_RUNS)
    assert len(pairs["meta"]["final_pending_runs"]) == len(rep.FINAL_PENDING_RUNS)
    assert pairs["combined_counts"]["n_pairs"] == pairs["summary"]["n_pairs"]
    assert pairs["meta"]["schema_version"] == 3
    assert p3b_pair["censored_at_guard"] is None  # no result.json for the Chrono run
    # no record.npz anywhere: the P3b case and the four curated record folders are listed
    assert len(pairs["meta"]["missing_stroke_records"]) == 1 + len(rep.CURATED_RECORD_DIRS)
    assert "d_max_stroke_reading_mm" not in p3b_pair["delta"]
    by_name = {study["variable"]: study for study in studies["studies"]}
    assert by_name["B2 F_s 4 -> 0 on slope (x426 B2)"]["n_groups"] == 0


# ---------------------------------------------------------------------------- RV2 / RV3 pairs
def test_rv2_pair_is_tagged_with_its_batch_and_same_version(tmp_path: Path):
    batch, case = rep.RV2_RUNS[0]
    _write_rejudge(tmp_path, batch, case, _p3b_summary_row(True, 70.7, [67.81e3, 70e3]))
    harness = {"base|J1|B|top|Fs0": _record("pass", 62.7, 69.06, gap_mm=47.2)}
    pairs, missing = rep.build_same_version_pairs(tmp_path, harness)
    rv2 = [pair for pair in pairs if pair["chrono_case"].startswith(case)]
    assert len(rv2) == 1
    (pair,) = rv2
    assert pair["chrono_case"] == f"{case} @ {batch}"
    assert pair["harness_id"] == "base|J1|B|top|Fs0"
    assert pair["variable"] == "B2 F_s"
    assert pair["chrono"]["version"] == rep.SAME_VERSION
    assert pair["chrono"]["src"].endswith(f"{batch}/{case}/result_rejudge_rev60.json")
    assert pair["delta"]["verdict_same"] is True
    assert pair["delta"]["d_ready_s"] == pytest.approx(8.0)
    assert pair["delta"]["d_gap_ready_mm"] == pytest.approx(-7.2)
    assert len(missing) == 5  # the other three RV2 runs and both RV3 runs


def test_rv3_slope_pair_without_ready_compares_stroke_and_force(tmp_path: Path):
    run = rep.RV3_SLOPE_RUN
    block = _p3b_summary_row(True, None, [68.09e3, 107e3], gap_m=None)
    block["checks"]["P3-1_crawler_zero_after_ready"] = None  # no READY window
    block["P3-5_clearance_stroke"]["s_motor_max_m"] = [0.4749, 0.6763]
    _write_rejudge(tmp_path, run["batch"], run["case"], block)
    case_dir = rep._rejudge_path(tmp_path, run["batch"], run["case"]).parent
    _write_stroke_record(case_dir, [[0.4802, 0.6829]])
    harness = {run["harness_id"]: _record("fail", None, 69.66, max_stroke_reading_mm=683.7,
                                          gap_mm=None)}
    pairs, _ = rep.build_same_version_pairs(tmp_path, harness)
    (pair,) = [pair for pair in pairs if pair["harness_id"] == run["harness_id"]]
    assert pair["chrono"]["verdict"] == "fail"
    assert pair["chrono"]["gap_ready_mm"] is None
    assert pair["chrono"]["max_stroke_true_mm"] == pytest.approx([474.9, 676.3])
    # reading vs reading (682.9 - 683.7); the mixed true-vs-reading -7.4 mm is gone
    assert pair["delta"] == {"verdict_same": True, "d_min_force_kN": pytest.approx(-1.57),
                             "d_max_stroke_reading_mm": pytest.approx(-0.8),
                             "minF_ratio_h_over_c": pytest.approx(1.023)}
    assert pair["side"] == "representative"


def test_rv3_g6_pair_reads_the_judge_case(tmp_path: Path):
    run = rep.RV3_G6_RUN
    judge = {"cases": [{"case": "other"},
                       {"case": run["case"], "pass": False, "t_ready_rel_s": 67.6,
                        "F_min_after_departure_kN": [76.67, 116.89, 65.7, 11.8],
                        "s_motor_max_mm": [557.13, 447.88], "rut_min_after_ready_mm": 87.95,
                        "attitude_p34_absmax_deg": 0.0152}]}
    judge_path = tmp_path / run["judge_rel"]
    judge_path.parent.mkdir(parents=True)
    judge_path.write_text(json.dumps(judge), encoding="utf-8")
    harness = {run["harness_id"]: _record("fail", 64.1, 18.33, max_stroke_reading_mm=541.47,
                                          gap_mm=69.63)}
    pairs, missing = rep.build_same_version_pairs(tmp_path, harness)
    (pair,) = pairs
    assert pair["chrono"]["min_force_kN"] == 11.8
    assert pair["chrono"]["src"] == run["judge_rel"]
    assert pair["delta"]["verdict_same"] is True
    assert pair["delta"]["d_ready_s"] == pytest.approx(3.5)
    assert pair["side"] == "optimistic"  # harness min force 18.3 vs Chrono 11.8 kN
    assert not any(run["judge_rel"] in path for path in missing)


def test_g6_judge_without_the_case_is_listed_missing(tmp_path: Path):
    judge_path = tmp_path / rep.RV3_G6_RUN["judge_rel"]
    judge_path.parent.mkdir(parents=True)
    judge_path.write_text(json.dumps({"cases": []}), encoding="utf-8")
    pairs, missing = rep.build_same_version_pairs(tmp_path, {})
    assert pairs == []
    assert any(rep.RV3_G6_RUN["case"] in path for path in missing)


def test_missing_p3b_summary_raises(minimal_repo: Path, tmp_path: Path):
    (minimal_repo / rep.P3B_SUMMARY_REL).unlink()
    with pytest.raises(FileNotFoundError):
        rep.main(["rep_evidence.py", str(minimal_repo), str(tmp_path / "out")])


def test_missing_required_table_raises_key_error(minimal_repo: Path):
    rep.harness_files(minimal_repo)["h6"].unlink()
    harness = rep.load_harness(rep.harness_files(minimal_repo))
    with pytest.raises(KeyError, match="h6"):
        rep.build_studies(harness)


# ---------------------------------------------------------------------------- H-6 note
def test_h6_margin_note_is_the_spec_432_4_5_text():
    assert rep.H6_MARGIN_NOTE == (
        "H-6 optimistic margin (ASSUMPTION, spec 432.4 / 432.4.5 / 432.4.7, 2026-10-31): flat "
        "READY +17 s, gap -13 mm (RV2 J2 -12.7 mm, 432.4.4); soft slope rows gap -15 mm "
        "(X6-rb2 -14.5 mm, 432.4.7); stroke reading one-sided +23 mm "
        "(Chrono meas.stroke max - harness max(plant.sref); observed X6-rb vs H9 "
        "roll_neg@k0.65 >= +22.7 mm censored at the guard, RV3 C-C1 +21.5 mm uncensored; "
        "stroke sensor share <= 0.4 mm) for soft J1/J2/S1 incl. one-pad patches, not G1 or "
        "rigid; slope / x1.1 READY +31 s")
    assert rep.H6_MARGIN_NOTE.isascii()


# ---------------------------------------------------------------------------- guard censoring
def _write_run_events(case_dir: Path, names: list[str]) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    events = [{"t_s": float(i), "name": name} for i, name in enumerate(names)]
    (case_dir / rep.RUN_RESULT_FILE_NAME).write_text(json.dumps({"events": events}),
                                                     encoding="utf-8")


def test_stroke_guard_events_keep_guard_names_only():
    names = ["INFO_LOC_CLEARANCE_MARGIN:80", "WARN_LIFT_STROKE_LIMITED:FL",
             "FAULT_LIFT_STROKE_LIMIT:soil:FL", "WARN_LIFT_STROKE_LIMITED:FL",
             "FAULT_STROKE_END:FL"]
    assert rep.stroke_guard_events(names) == ["FAULT_LIFT_STROKE_LIMIT:soil:FL",
                                              "WARN_LIFT_STROKE_LIMITED:FL"]


def test_normalize_record_reads_guard_events_from_warnings():
    guarded = rep.normalize_record({"id": "a", "verdict": "stroke_limited_stop",
                                    "warnings": ["WARN_LIFT_STROKE_LIMITED:FR"]})
    assert guarded["stroke_guard_events"] == ["WARN_LIFT_STROKE_LIMITED:FR"]
    assert rep.normalize_record({"id": "b", "warnings": []})["stroke_guard_events"] == []
    assert rep.normalize_record({"id": "c"})["stroke_guard_events"] is None


def test_chrono_guard_events_come_from_result_json(tmp_path: Path):
    _write_run_events(tmp_path, ["TOUCH", "FAULT_LIFT_STROKE_LIMIT:FR"])
    fields = rep.stroke_reading_fields(tmp_path, tmp_path)
    assert fields["stroke_guard_events"] == ["FAULT_LIFT_STROKE_LIMIT:FR"]
    assert rep.read_chrono_guard_events(tmp_path / "absent.json") is None


@pytest.mark.parametrize(("chrono_events", "harness_events", "expected"), [
    (["WARN_LIFT_STROKE_LIMITED:FL"], [], (True, "chrono")),
    ([], ["FAULT_LIFT_STROKE_LIMIT:FR"], (True, "harness")),
    (["WARN_LIFT_STROKE_LIMITED:FR"], ["WARN_LIFT_STROKE_LIMITED:FR"], (True, "both")),
    ([], [], (False, None)),
    (None, [], (None, None)),
    (["WARN_LIFT_STROKE_LIMITED:FL"], None, (True, "chrono")),
])
def test_stroke_censoring_sides(chrono_events, harness_events, expected):
    harness = {"stroke_guard_events": harness_events}
    chrono = {"stroke_guard_events": chrono_events}
    censoring = rep.stroke_censoring(harness, chrono)
    assert (censoring["censored_at_guard"], censoring["censored_side"]) == expected


def test_classify_pair_ignores_event_name_lists():
    harness = dict(_record("pass", 60.0, 60.0, max_stroke_reading_mm=660.3),
                   stroke_guard_events=[])
    chrono = dict(_record("stroke_limited_stop", None, 60.0),
                  max_stroke_reading_mm=[683.0, 433.9], stroke_guard_events=[
                      "FAULT_LIFT_STROKE_LIMIT:soil:FL", "WARN_LIFT_STROKE_LIMITED:FL"])
    side, deltas = rep.classify_pair(harness, chrono)
    assert deltas["d_max_stroke_reading_mm"] == pytest.approx(22.7)
    assert side == "optimistic"  # harness pass vs Chrono safe stop


def test_summary_keeps_censored_pairs_out_of_the_uncensored_stats():
    pairs = [{"variable": "A2 roll", "chrono_case": "cut", "harness": {}, "side": "optimistic",
              "delta": {"d_max_stroke_reading_mm": 22.7}, "censored_at_guard": True,
              "censored_side": "chrono"},
             {"variable": "A1 soil", "chrono_case": "free", "harness": {},
              "side": "representative", "delta": {"d_max_stroke_reading_mm": -2.0},
              "censored_at_guard": False, "censored_side": None}]
    summary = rep.summarize_pairs(pairs)
    assert summary["d_max_stroke_reading_mm_chrono_minus_harness"]["max"] == 22.7
    assert summary["d_max_stroke_reading_mm_uncensored"] == {"n": 1, "min": -2.0,
                                                             "max": -2.0, "mean": -2.0}
    assert summary["censored_stroke_reading"] == [
        {"chrono_case": "cut", "censored_side": "chrono", "d_max_stroke_reading_mm": 22.7}]


# ---------------------------------------------------------------------------- final pairs
def _final_run(**overrides) -> dict:
    run = {"variable": "A2 roll test [X]", "batch": "batch_FINAL_test", "case": "S9SL_X",
           "harness_key": "finB2_h9", "harness_id": "H9|J1|B|top|roll_neg@k0.65",
           "spec": "spec 1"}
    run.update(overrides)
    return run


def test_final_pair_uses_the_spec_verdict_and_the_final_harness(tmp_path: Path):
    run = _final_run(verdict="stroke_limited_stop", note="safe stop")
    block = _p3b_summary_row(True, None, [62.9e3, 70e3], gap_m=None)
    block["checks"]["P3-6_within"] = False  # no READY: the automatic verdict is fail
    _write_rejudge(tmp_path, run["batch"], run["case"], block)
    case_dir = rep._rejudge_path(tmp_path, run["batch"], run["case"]).parent
    _write_stroke_record(case_dir, [[0.68302, 0.43394]])
    _write_run_events(case_dir, ["WARN_LIFT_STROKE_LIMITED:FL",
                                 "FAULT_LIFT_STROKE_LIMIT:soil:FL"])
    final_harness = {"finB2_h9": {run["harness_id"]: dict(
        _record("pass", 76.4, 63.39, max_stroke_reading_mm=660.28), stroke_guard_events=[])}}
    pairs, missing = rep.build_final_pairs(tmp_path, final_harness, runs=(run,))
    assert missing == []
    (pair,) = pairs
    assert pair["chrono"]["verdict"] == "stroke_limited_stop"
    assert pair["chrono"]["verdict_auto"] == "fail"
    assert pair["chrono"]["note"] == "safe stop"
    assert pair["chrono"]["version"] == rep.FINAL_VERSION
    assert pair["harness"]["source"] == "finB2_h9"
    assert pair["chrono_case"] == f"{run['case']} @ {run['batch']}"
    assert pair["delta"]["d_max_stroke_reading_mm"] == pytest.approx(22.74)
    payload = rep.build_pairs_payload([], {}, tmp_path, [], pairs, missing)
    (final,) = payload["final_pairs"]
    assert (final["censored_at_guard"], final["censored_side"]) == (True, "chrono")
    assert payload["final_summary"]["d_max_stroke_reading_mm_uncensored"] == {}
    assert payload["combined_counts"] == {"n_pairs": 1, "n_with_harness": 1,
                                          "verdict_same": 0}


def test_final_pair_without_spec_verdict_keeps_the_automatic_one(tmp_path: Path):
    run = _final_run(harness_key="finB2_p0", harness_id="base|J1|B|top|Fs4")
    _write_rejudge(tmp_path, run["batch"], run["case"], _p3b_summary_row(True, 74.2, [68.1e3]))
    pairs, missing = rep.build_final_pairs(tmp_path, {}, runs=(run,))
    (pair,) = pairs
    assert pair["chrono"]["verdict"] == "pass"
    assert "verdict_auto" not in pair["chrono"]
    assert pair["harness"] is None
    assert pair["side"] is None
    assert missing == ["harness finB2_p0: base|J1|B|top|Fs4"]


def test_final_runs_name_loaded_harness_keys_and_pending_runs_are_apart():
    keys = set(rep.FINAL_HARNESS_FILES_REL)
    assert all(run["harness_key"] in keys for run in rep.FINAL_RUNS + rep.FINAL_PENDING_RUNS)
    final_cases = {(run["batch"], run["case"]) for run in rep.FINAL_RUNS}
    assert not final_cases & {(run["batch"], run["case"]) for run in rep.FINAL_PENDING_RUNS}
    assert len(rep.FINAL_RUNS) == 10
    superseding_cases = {run["superseded_by"] for run in rep.FINAL_RUNS
                         if "superseded_by" in run}
    assert superseding_cases <= {f"{run['case']} @ {run['batch']}" for run in rep.FINAL_RUNS}


# ---------------------------------------------------------------------------- P3-2 FLAG
def _p3_2_flag_block(reason_check: str) -> dict:
    block = _p3b_summary_row(True, 98.9, [68e3])
    block["checks"].update({"P3-2_within": False, "P3-2_verdict": "flag",
                            "P3-2_late_loc_revoked": False,
                            "P3-2_late_loc_reapproach": False, reason_check: True})
    return block


@pytest.mark.parametrize("reason_check", ["P3-2_late_loc_revoked",
                                          "P3-2_late_loc_reapproach"])
def test_p3_2_flag_counts_as_pass_and_names_the_reason(reason_check):
    values = rep.chrono_values_from_p3b_block(_p3_2_flag_block(reason_check))
    assert values["verdict"] == "pass"
    assert values["flags"] == [reason_check]


def test_p3_2_failure_without_flag_stays_fail_and_has_no_flags():
    block = _p3b_summary_row(True, 55.0, [60e3])
    block["checks"].update({"P3-2_within": False, "P3-2_verdict": "fail"})
    values = rep.chrono_values_from_p3b_block(block)
    assert values["verdict"] == "fail"
    assert "flags" not in values


def test_p3_2_flag_does_not_hide_another_failed_check():
    block = _p3_2_flag_block("P3-2_late_loc_revoked")
    block["checks"]["P3-4_within_0p2"] = False  # e.g. P3-4 not judged (window short)
    values = rep.chrono_values_from_p3b_block(block)
    assert values["verdict"] == "fail"
    assert values["flags"] == ["P3-2_late_loc_revoked"]


def test_final_pair_with_flag_keeps_spec_verdict_and_pass_as_automatic(tmp_path: Path):
    run = _final_run(verdict="pass", harness_key="finB2_p0", harness_id="base|J2|B|top|Fs4")
    _write_rejudge(tmp_path, run["batch"], run["case"],
                   _p3_2_flag_block("P3-2_late_loc_revoked"))
    (pair,), _ = rep.build_final_pairs(tmp_path, {}, runs=(run,))
    assert pair["chrono"]["verdict"] == "pass"
    assert pair["chrono"]["verdict_auto"] == "pass"
    assert pair["chrono"]["flags"] == ["P3-2_late_loc_revoked"]


def test_superseded_final_pair_is_listed_but_not_counted(tmp_path: Path):
    old = _final_run(case="P3b_old", superseded_by="P3b_new @ batch_FINAL_test")
    new = _final_run(case="P3b_new")
    for run in (old, new):
        _write_rejudge(tmp_path, run["batch"], run["case"], _p3b_summary_row(True, 90.0, [68e3]))
    final_harness = {"finB2_h9": {old["harness_id"]: _record("pass", 85.0, 68.0)}}
    pairs, _ = rep.build_final_pairs(tmp_path, final_harness, runs=(old, new))
    payload = rep.build_pairs_payload([], {}, tmp_path, [], pairs, [])
    assert len(payload["final_pairs"]) == 2
    assert payload["final_pairs"][0]["superseded_by"] == "P3b_new @ batch_FINAL_test"
    assert payload["final_summary"]["n_pairs"] == 1
    assert payload["final_summary"]["verdict_same"] == 1
    assert payload["final_summary"]["superseded"] == [
        {"chrono_case": "P3b_old @ batch_FINAL_test",
         "superseded_by": "P3b_new @ batch_FINAL_test"}]
    assert payload["combined_counts"]["n_pairs"] == 1
