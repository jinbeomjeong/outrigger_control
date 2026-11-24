"""Unit tests of the edition-6 J-P3 path-2 judge (identity, declaration, evidence)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "path2"))

import jp3_ed6_judge_p2 as j6  # noqa: E402

OPTS = {"extend_start_tracked": True, "extend_start_hold": True, "extend_start_witness": True}


def line(**kw):
    raw = {"job": {"case": "S1", "eps": 0.0, "setting": "VBL"}, "head_only_declared": True,
           "controller_tag": j6.ED6_TAG, "lsb_components": ["A_i", "A_ii", "B3"],
           "hydraulic_options": dict(OPTS),
           "hydraulics_record": {"rod_reading_truth_calls": 0, "two_pressure_reads": 0,
                                 "extend_bound_check": None}}
    raw.update(kw)
    return raw


def kinds(raw, tmp_path):
    return [k for k, _ in j6.judge_line(1, raw, tmp_path).issues]


def test_tag_base():
    assert j6.tag_base("final_C4G2_P3W_LAS_K1_LSB") == "final_C4G2_P3W"
    assert j6.tag_base("final_C4G2_P3W_LAS_K1") == "final_C4G2_P3W"
    assert j6.tag_base("final_C4G2_P3W_K1_LAS_LSB") == "final_C4G2_P3W_K1"  # order matters
    assert j6.tag_base(None) is None


def test_declared_line_clean(tmp_path):
    o = j6.judge_line(1, line(), tmp_path)
    assert o.role == "no_rod_reading" and o.issues == []


def test_identity_defects(tmp_path):
    assert "setting_defect" in kinds(line(controller_tag="final_C4G2_P3W_LAS_K1"), tmp_path)
    assert "setting_defect" in kinds(line(lsb_components=["A_i", "A_ii", "B3", "B3"]), tmp_path)
    assert "setting_defect" in kinds(line(lsb_components=["A_i", "A_ii", "B1"]), tmp_path)
    assert "setting_defect" in kinds(line(lsb_components=["A_i", "A_ii"]), tmp_path)
    assert kinds(line(lsb_components=["B3", "A_ii", "A_i"]), tmp_path) == []
    o = dict(OPTS, extend_start_witness=False)
    assert "setting_defect" in kinds(line(hydraulic_options=o), tmp_path)
    assert kinds(line(run_extend_start_revision=6), tmp_path) == []
    assert "setting_defect" in kinds(line(run_extend_start_revision=5), tmp_path)
    assert "setting_defect" in kinds(line(run_extend_start_revision=6, hydraulic_options=o),
                                     tmp_path)


def test_evidence(tmp_path):
    raw = line()
    raw["hydraulics_record"]["two_pressure_reads"] = 3
    assert "setting_defect" in kinds(raw, tmp_path)
    raw = line()
    del raw["hydraulics_record"]["rod_reading_truth_calls"]
    assert "setting_defect" in kinds(raw, tmp_path)


def test_declared_with_record_and_event_without_record(tmp_path):
    raw = line()
    raw["hydraulics_record"]["extend_bound_check"] = {"rule_revision": 6,
                                                      "spec_edition": "fe6f5844"}
    assert "setting_defect" in kinds(raw, tmp_path)
    raw = line(head_only_declared=False)
    raw["hydraulics_record"].update(rod_reading_truth_calls=5, two_pressure_reads=5)
    assert "setting_defect" in kinds(raw, tmp_path)  # event path without a ③ record


def test_off_and_unknown_settings(tmp_path):
    raw = line(job={"case": "S1", "setting": "VBL0"})
    o = j6.judge_line(1, raw, tmp_path)
    assert o.role == "reference_off" and o.issues == []
    raw = line(job={"case": "S1", "setting": "VBJ"})
    assert "setting_defect" in kinds(raw, tmp_path)
