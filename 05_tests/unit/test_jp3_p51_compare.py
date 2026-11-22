"""436.9 edition 5 P5-1 compare tool (``jp3_p51_compare.py``) on short sample rows of both row
forms (r79 lines in a run file, run_v5 rows as JSON lines, T4h event lists), with the working
folder elsewhere than the inputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import jp3_p51_compare as p51  # noqa: E402

A, B = "a" * 64, "b" * 64


def r79_row(key: str, setting: str, sha: str, fallback=False) -> dict:
    return {"key": f"cand=current#{key}", "v5_setting": setting, "commands_sha256": sha,
            "r79": {"rod_fallback": [[12.3, "FR"]] if fallback else []},
            "rod_fallback_reasons": []}


def v5_row(case: str, setting: str, sha: str, events=(), t4h_file=None) -> dict:
    row = {"job": {"case": case, "eps": 0.0, "setting": setting, "mask": 3},
           "commands_sha256": sha, "events": [list(event) for event in events]}
    if t4h_file:
        row["t4h_file"] = t4h_file
    return row


@pytest.fixture()
def elsewhere(tmp_path, monkeypatch):
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    return tmp_path


def _files(folder: Path, old: list[dict], new: list[dict]) -> tuple[Path, Path]:
    old_file, new_file = folder / "old.json", folder / "new.jsonl"
    old_file.write_text(json.dumps({"meta": {}, "results": old}, indent=1), encoding="utf-8")
    new_file.write_text("".join(json.dumps(row) + "\n" for row in new), encoding="utf-8")
    return old_file, new_file


def _run(folder, old, new, capsys, extra=()):
    old_file, new_file = _files(folder, old, new)
    out = folder / "report.json"
    code = p51.main(["--old", str(old_file), "--new", str(new_file), "--out", str(out),
                     *extra])
    return code, json.loads(capsys.readouterr().out.splitlines()[-1]), json.loads(
        out.read_text(encoding="utf-8"))


def test_p51_equal_rows_pass_and_fallback_rows_are_recorded(elsewhere, capsys) -> None:
    old = [r79_row("L2|s0|g6|0|x", "VBJ", A), r79_row("L2|s0|g6|1|x", "VBJ", A, fallback=True),
           r79_row("L2|s0|g6|2|x", "VBJ0", B, fallback=True)]
    new = [r79_row("L2|s0|g6|0|x", "VBJ", A), r79_row("L2|s0|g6|1|x", "VBJ", B),
           r79_row("L2|s0|g6|2|x", "VBJ0", B, fallback=True)]
    code, last, report = _run(elsewhere, old, new, capsys)
    assert code == 0 and last["status"] == "pass"
    assert report["judged_pairs"] == 2 and report["fallback_pairs_recorded"] == 1


def test_p51_a_differing_judged_pair_stops(elsewhere, capsys) -> None:
    code, last, report = _run(elsewhere, [v5_row("R12", "VBJ", A)], [v5_row("R12", "VBJ", B)],
                              capsys)
    assert code == 1 and report["differing_pairs"] == 1
    # an always-equal setting differs even with a fallback
    events = [(3.0, "WARN_ROD_PRESSURE_FALLBACK:FL")]
    code, _, _ = _run(elsewhere / "cwd", [v5_row("R12", "VB", A, events)],
                      [v5_row("R12", "VB", B, events)], capsys)
    assert code == 1


def test_p51_not_judgeable_cases(elsewhere, capsys) -> None:
    code, _, report = _run(elsewhere, [v5_row("R12", "VBJ", A)], [v5_row("R14", "VBJ", A)],
                           capsys)
    assert code == 2 and any("one side only" in text for text in report["problems"])
    capped = [(0.1 * i, "INFO_X") for i in range(p51.ROW_EVENT_CAP)]
    folder = elsewhere / "cap"
    folder.mkdir()
    code, _, report = _run(folder, [v5_row("R12", "VBJ", A, capped)],
                           [v5_row("R12", "VBJ", A)], capsys)
    assert code == 2 and any("at the cap" in text for text in report["problems"])


def test_p51_reads_the_t4h_event_list(elsewhere, capsys) -> None:
    """A fallback after the row's 400-event cap is found in the T4h meta (recorded, not
    judged), the row is then judgeable."""
    t4h = elsewhere / "t4h"
    t4h.mkdir()
    events = [[0.1 * i, "INFO_X"] for i in range(500)] + [[60.0, "WARN_ROD_PRESSURE_FALLBACK:RR"]]
    np.savez_compressed(t4h / "r.npz", meta_json=np.array(json.dumps({"events": events})))
    capped = [(0.1 * i, "INFO_X") for i in range(p51.ROW_EVENT_CAP)]
    old = [v5_row("R12", "VBJ", A, capped, t4h_file="r.npz")]
    new = [v5_row("R12", "VBJ", B, capped, t4h_file="r.npz"), ]
    code, last, report = _run(elsewhere, old, new + [v5_row("R14", "VBJ0", A)], capsys,
                              ["--old-t4h", str(t4h), "--new-t4h", str(t4h)])
    assert report["fallback_pairs_recorded"] == 1
    assert code == 2  # R14 is on one side only
    folder = elsewhere / "two"
    folder.mkdir()
    code, _, report = _run(folder, old + [v5_row("R14", "VBJ0", A)],
                           new + [v5_row("R14", "VBJ0", A)], capsys,
                           ["--old-t4h", str(t4h), "--new-t4h", str(t4h)])
    assert code == 0 and report["judged_pairs"] == 1 and report["fallback_pairs_recorded"] == 1
