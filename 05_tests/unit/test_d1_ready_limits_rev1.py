"""D-1 READY limits by ``d1_selection_rules_rev1.md`` (sealed 2026-11-08): the H-S rows take the
spec 421.1 limit (``s9_soil_slope.ready_limit_s``), the H-R rows keep flat 90 / slope 120 s.
Row definitions only, no harness run."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import d1_rows  # noqa: E402
import d1_select as sel  # noqa: E402

ROWS = {row.key: row for row in d1_rows.all_rows()}


@pytest.mark.parametrize(("key", "limit_s"), [
    ("D1|H-S-0|G1|T|flat|K1", 90.0), ("D1|H-S-0|G1|M|flat|K1", 90.0),
    ("D1|H-S-0|G1|B|flat|K1", 90.0),
    ("D1|H-S-A|G1+J1@FL|T|flat|K1", 90.0), ("D1|H-S-A|G1+J1@RL|B|flat|K1", 90.0),
    ("D1|H-S-A-J2|G1+J2@FL|T|flat|K1", 90.0),
    ("D1|H-S-0|J1|T|flat|K1", 100.0), ("D1|H-S-0|J2|B|flat|K1", 100.0),
    ("D1|H-S-1|S1|T|flat|K1", 100.0), ("D1|H-S-1|S1|B|flat|K1", 100.0),
    ("D1|H-S-C|J1|T|flat|K1|c-mid@FL", 100.0),
    ("D1|H-S-0|G1|T|fdown-rec|K1", 120.0), ("D1|H-S-0|J1|M|roll-rec|K1", 120.0),
    ("D1|H-S-A|G1+J1@FR|T|diag-psa-soil|K1", 120.0),
    ("D1|H-S-C-g|J1|T|diag-rec|K1|c-mid@FR|dsb_gated_off", 120.0),
])
def test_soil_rows_take_the_spec_421_limit(key, limit_s) -> None:
    assert ROWS[key].ready_limit_s == limit_s


def test_rigid_rows_are_unchanged() -> None:
    for row in ROWS.values():
        if row.group.startswith("H-R"):
            assert row.ready_limit_s == (90.0 if row.slope_name == "flat" else 120.0), row.key


def test_every_soil_row_matches_ready_limit_s() -> None:
    slope = d1_rows._slope_module()
    for row in ROWS.values():
        if row.group.startswith("H-S"):
            case = {"soil": row.soil, "pad": "B", "roll_deg": row.roll_deg,
                    "pitch_deg": row.pitch_deg}
            assert row.ready_limit_s == slope.ready_limit_s(case), row.key


def test_list_report_prints_the_limit_of_every_row() -> None:
    lines = d1_rows.ready_limit_lines(list(ROWS.values()))
    assert lines[0].startswith("READY limit (d1_selection_rules_rev1.md 1")
    assert len(lines) == 1 + len(ROWS)
    by_key = {line.split()[0]: line.split()[-2] for line in lines[1:]}
    assert by_key["D1|H-S-0|G1|T|flat|K1"] == "90"
    assert by_key["D1|H-S-1|S1|M|flat|K1"] == "100"


def test_ready_rule_record_reads_the_file(tmp_path) -> None:
    text = tmp_path / "d1_selection_rules_rev1.md"
    text.write_bytes(b"line\r\n")
    record = d1_rows.ready_rule_record(text)
    assert record["rules"] == "d1_selection_rules_rev1.md"
    assert record["sha256"] == d1_rows.text_sha256(text) == sel.file_sha256(text)
    assert d1_rows.ready_rule_record(tmp_path / "absent.md")["sha256"] is None


def test_selection_report_records_the_revision(tmp_path, monkeypatch) -> None:
    rules = tmp_path / "d1_selection_rules.md"
    revision = tmp_path / "d1_selection_rules_rev1.md"
    rules.write_text("rules\n", encoding="utf-8")
    revision.write_text("rev1\n", encoding="utf-8")
    seal = tmp_path / "d1_selection_rules_rev1.sha256"
    seal.write_text(f"{sel.file_sha256(revision)}  d1_selection_rules_rev1.md\n",
                    encoding="utf-8")
    results = tmp_path / "d1.jsonl"
    results.write_text("", encoding="utf-8")
    out = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", ["d1_select", str(out), str(results), "--rules", str(rules),
                                      "--revisions", str(revision)])
    sel.main()
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["rules_revisions"] == [{
        "rules": "d1_selection_rules_rev1.md", "sha256": sel.file_sha256(revision),
        "sealed_sha256": sel.file_sha256(revision), "match_seal": True}]


def test_selection_stops_without_the_revision(tmp_path, monkeypatch) -> None:
    rules = tmp_path / "d1_selection_rules.md"
    rules.write_text("rules\n", encoding="utf-8")
    results = tmp_path / "d1.jsonl"
    results.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["d1_select", str(tmp_path / "o.json"), str(results),
                                      "--rules", str(rules), "--revisions",
                                      str(tmp_path / "absent_rev1.md")])
    assert sel.main() == 2
