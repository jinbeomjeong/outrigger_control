"""s9_batch ``code_at_launch`` on open-loop ``run_S9.py machine`` rows (436.8 rules rev11 R11-4, user decision
Q-R11-1 = B, 2026-11-13): record only, the same form as controller rows, argv unchanged."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import s9_batch as sb  # noqa: E402

CHILD = (
    "import json, pathlib, sys\n"
    "args = sys.argv\n"
    "folder = pathlib.Path(args[args.index('--out-root') + 1]) / args[args.index('--case') + 1]\n"
    "folder.mkdir(parents=True, exist_ok=True)\n"
    "(folder / 'result.json').write_text(json.dumps({}), encoding='utf-8')\n"
)


def test_is_open_loop_machine() -> None:
    run = [sys.executable, "-I", "-X", "utf8", "-u", str(Path("x") / "04_scripts" / "02_chrono" / "run_S9.py")]
    assert sb.is_open_loop_machine(run + ["machine", "--lift-s", "10"])
    assert not sb.is_open_loop_machine(run + ["level", "--approved"])
    assert not sb.is_open_loop_machine(run)
    assert not sb.is_open_loop_machine([sys.executable, "run_S8C.py", "machine"])
    assert sb.records_code_at_launch({"argv": run + ["machine"]})
    assert sb.records_code_at_launch({"argv": run + ["level"], "controller": "final_C4G2_LAS_K1"})
    assert sb.records_code_at_launch({"argv": [], "group": "FINAL-R"})
    assert not sb.records_code_at_launch({"argv": run + ["single-pad"]})


def test_stored_open_loop_rows_record(monkeypatch) -> None:
    """Every row of the stored batches whose argv runs run_S9 machine now records code_at_launch."""
    pytest.importorskip("pychrono")
    b = sb.batches()
    ol = [r for name in ("V5-RESUME-K1-GS", "V5-RESUME-K1-C6C7") for r in b[name]
          if sb.is_open_loop_machine(r["argv"])]
    assert ol and all(sb.records_code_at_launch(r) and not r.get("controller") for r in ol)


def test_run_batch_records_open_loop_code_at_launch(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("OUTRIGGER_HULL_HOOK", raising=False)
    monkeypatch.setattr(sb, "ROOT", tmp_path)
    script = tmp_path / "run_S9.py"
    script.write_text(CHILD, encoding="utf-8")
    rows = [{"case": "ol", "argv": [sys.executable, str(script), "machine"], "est_s": 1.0},
            {"case": "cl", "argv": [sys.executable, str(script), "level"], "est_s": 1.0, "controller": "tag"},
            {"case": "other", "argv": [sys.executable, str(script), "single-pad"], "est_s": 1.0}]
    monkeypatch.setattr(sb, "batches", lambda **_: {"TEST-CAL": rows})
    folder = sb.run_batch("TEST-CAL", parallel=3)
    doc = {c["case"]: c for c in json.loads((folder / "batch.json").read_text("utf-8"))["cases"]}
    for r in rows:
        assert doc[r["case"]]["argv"] == r["argv"]  # argv as built (no record option added)
    ol, cl = doc["ol"]["code_at_launch"], doc["cl"]["code_at_launch"]
    assert set(ol) == set(cl) == {"files", "git"}
    assert set(ol["files"]) == set(sb.CODE_HASH_FILES)
    assert set(ol["git"]) == set(cl["git"])
    if "error" not in ol["git"]:
        assert len(ol["git"]["head"]) == 40 and {"clean", "dirty", "paths", "taken_utc"} <= set(ol["git"])
    assert "controller_check" not in doc["ol"] and doc["cl"]["controller_check"] is True
    assert "code_at_launch" not in doc["other"] and "controller_check" not in doc["other"]
