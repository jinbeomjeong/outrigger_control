"""436.9 edition 5 P5-2 record of ``jp3_p5_fixed_values.py`` on sample case replay rows (the
P5-4 replay is smoke-run on harness T4h records outside the unit tests)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import jp3_p5_fixed_values as p5  # noqa: E402


def _row(setting: str, revision: int, witness=(0, 1, 0, 0), with_coverage=True) -> dict:
    check = {"rule_revision": revision, "jp3a_breach_reads": [0] * 4,
             "jp3b_breach_over_tol_reads": [0] * 4, "jp3c_breach_reads": [0] * 4}
    if with_coverage:
        check.update(jp3_r58_witness_carries=list(witness), jp3_r59_substeps=[0, 300, 0, 0],
                     jp3_r510_candidates=[0, 2, 0, 0])
    return {"job": {"case": "R12", "setting": setting},
            "hydraulics_record": {"extend_bound_check": check}}


def test_p52_rows_and_problems(tmp_path, monkeypatch, capsys) -> None:
    rows = tmp_path / "in" / "cases.jsonl"
    rows.parent.mkdir()
    lines = [_row("VBJ", 6), _row("LSJ1", 6, with_coverage=False), {"job": {"case": "R14"}}]
    rows.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    out = tmp_path / "p52.json"
    assert p5.main(["p52", "--rows", str(rows), "--out", str(out)]) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["problems"] == 4
    report = json.loads(out.read_text(encoding="utf-8"))
    first = report["rows"][0]
    assert first["jp3_r59_substeps_sum"] == 300 and first["jp3_r58_witness_carries_sum"] == 1
    assert report["judged_key_total"] == 0
    assert any("no extend_bound_check" in text for text in report["problems"])
    assert sum("missing" in text for text in report["problems"]) == 3  # rev 6 coverage keys
    assert p5.main(["p52", "--rows", str(rows), "--out", str(out)]) == 2  # existing --out
