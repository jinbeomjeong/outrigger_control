"""B1 = B2 command-hash identity of ``final_b1b2_identity.py`` (control spec 429.11 acceptance B).

Synthetic wrapper and event payloads cover equal hashes, a changed hash, ids present on one side
only, verdict changes, the study A prefix fallback (``base.commands_sha256``) and duplicate ids.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "04_scripts" / "03_control" / "s9"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import final_b1b2_identity as src  # noqa: E402


def wrapper_payload(rows: list[tuple[str, str, str]]) -> dict:
    return {
        "records": [
            {"id": case_id, "hash": hash_value, "verdict": verdict}
            for case_id, hash_value, verdict in rows
        ]
    }


def event_payload(
    prefix_field: str = "prefix_commands_sha256",
    run_hashes: tuple[str, ...] = ("r0", "r1"),
    passed: bool = True,
) -> dict:
    result = {
        "key": "screen|top|0.0|level|FL",
        "runs": [
            {"event": "G4", "offset_s": 0.0, "commands_sha256": value, "pass": passed}
            for value in run_hashes
        ],
    }
    if prefix_field == "prefix_commands_sha256":
        result["prefix_commands_sha256"] = "p0"
    else:
        result["base"] = {"commands_sha256": "p0"}
    return {"results": [result]}


def write_pair(folder: Path, name: str, b1: dict, b2: dict) -> None:
    (folder / f"finB1_{name}.json").write_text(json.dumps(b1), encoding="utf-8")
    (folder / f"finB2_{name}.json").write_text(json.dumps(b2), encoding="utf-8")


def test_wrapper_equal_hashes_count_as_equal():
    rows = [("a", "h1", "pass"), ("b", "h2", "fail")]
    before = src.load_wrapper_entries(wrapper_payload(rows))
    after = src.load_wrapper_entries(wrapper_payload(list(reversed(rows))))
    comparison = src.compare_entries(before, after)
    assert comparison["hash_equal"] == 2
    assert comparison["hash_different"] == 0
    assert comparison["unmatched"] == 0
    assert comparison["verdict_different"] == 0


def test_changed_hash_and_verdict_are_listed():
    before = src.load_wrapper_entries(wrapper_payload([("a", "h1", "pass")]))
    after = src.load_wrapper_entries(wrapper_payload([("a", "h9", "fail")]))
    comparison = src.compare_entries(before, after)
    assert comparison["hash_different"] == 1
    assert comparison["hash_different_ids"][0]["id"] == "a"
    assert comparison["verdict_different_ids"][0] == {
        "id": "a",
        "verdict_b1": "pass",
        "verdict_b2": "fail",
        "hash_equal": False,
    }


def test_one_sided_ids_are_unmatched():
    before = src.load_wrapper_entries(wrapper_payload([("a", "h1", "pass"), ("b", "h2", "pass")]))
    after = src.load_wrapper_entries(wrapper_payload([("a", "h1", "pass"), ("c", "h3", "pass")]))
    comparison = src.compare_entries(before, after)
    assert comparison["matched"] == 1
    assert comparison["only_b1"] == ["b"]
    assert comparison["only_b2"] == ["c"]
    assert comparison["unmatched"] == 2


def test_missing_hash_is_never_equal():
    before = src.load_wrapper_entries({"records": [{"id": "a", "verdict": "pass"}]})
    after = src.load_wrapper_entries({"records": [{"id": "a", "verdict": "pass"}]})
    assert src.compare_entries(before, after)["hash_different"] == 1


def test_duplicate_id_raises():
    with pytest.raises(ValueError, match="duplicate id"):
        src.load_wrapper_entries(wrapper_payload([("a", "h1", "pass"), ("a", "h1", "pass")]))


def test_event_run_ids_include_index_and_descriptor():
    runs, prefixes, sources = src.load_event_entries(event_payload())
    assert sorted(runs) == ["screen|top|0.0|level|FL#0:G4|0.0", "screen|top|0.0|level|FL#1:G4|0.0"]
    assert runs["screen|top|0.0|level|FL#0:G4|0.0"] == src.Entry("r0", "pass")
    assert prefixes["screen|top|0.0|level|FL"].hash == "p0"
    assert sources == {"prefix_commands_sha256"}


def test_study_a_prefix_falls_back_to_base_hash():
    _, prefixes, sources = src.load_event_entries(event_payload(prefix_field="base"))
    assert prefixes["screen|top|0.0|level|FL"].hash == "p0"
    assert sources == {"base.commands_sha256"}


def test_build_report_all_equal_and_mismatch(tmp_path):
    bundles = (src.Bundle("w", "wrapper", 2), src.Bundle("e", "event", 2))
    rows = [("a", "h1", "pass"), ("b", "h2", "pass")]
    write_pair(tmp_path, "w", wrapper_payload(rows), wrapper_payload(rows))
    write_pair(tmp_path, "e", event_payload(), event_payload())
    report = src.build_report(tmp_path, bundles, total_expected=4)
    assert report["totals"]["all_equal"] is True
    assert report["totals"]["hash_equal"] == 4

    write_pair(tmp_path, "e", event_payload(), event_payload(run_hashes=("r0", "rX")))
    report = src.build_report(tmp_path, bundles, total_expected=4)
    assert report["totals"]["all_equal"] is False
    assert report["bundles"]["e"]["hash_different"] == 1
    assert report["bundles"]["e"]["prefix"]["hash_equal"] == 1


def test_count_shortfall_is_not_all_equal(tmp_path):
    bundles = (src.Bundle("w", "wrapper", 3),)
    rows = [("a", "h1", "pass"), ("b", "h2", "pass")]
    write_pair(tmp_path, "w", wrapper_payload(rows), wrapper_payload(rows))
    report = src.build_report(tmp_path, bundles, total_expected=3)
    assert report["bundles"]["w"]["count_ok"] is False
    assert report["totals"]["all_equal"] is False
