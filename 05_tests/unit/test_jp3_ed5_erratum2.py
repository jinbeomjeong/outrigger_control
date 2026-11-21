"""436.9 edition 5 erratum 2 (``jp3_remedy_spec_v5_erratum2.md``): the 12b L1 key file (2-1),
the probe record form read by the 12b seed scan (2-3) and the extra fixed-list entries."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
if str(COUPLED_DIR) not in sys.path:
    sys.path.insert(0, str(COUPLED_DIR))

import jp3_12b_l1_keys as l1  # noqa: E402
import jp3_12b_plan as plan  # noqa: E402


def _noise(path: Path, *, drop_l1: str | None = None) -> str:
    """A case source: 167 L2 cases over two seeds, their L1 lines at s0; cases 0 and 1 share
    (harness, inner) with cases 100 and 101 (another index)."""
    cases = [f"g6|{index}|x{index % 100}|top|Fs0" for index in range(167)]
    results = []
    for seed in range(2):
        results += [{"key": f"cand=current#L2|s{seed}|{case}", "level": "L2"} for case in cases]
    results += [{"key": f"cand=current#L1|s0|{case}", "level": "L1"} for case in cases
                if case != drop_l1]
    path.write_text(json.dumps({"results": results}), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_l1_keys_one_per_harness_inner_in_first_order(tmp_path) -> None:
    noise = tmp_path / "noise.json"
    sha = _noise(noise)
    out = tmp_path / "l1_keys.txt"
    record = l1.write_l1_keys(noise, out, noise_sha256=sha)
    keys = out.read_bytes().decode("utf-8").split("\n")
    assert keys[-1] == "" and record["keys"] == len(keys) - 1 == 100  # x0 .. x99
    assert keys[:2] == ["L1|s0|g6|0|x0|top|Fs0", "L1|s0|g6|1|x1|top|Fs0"]
    assert "L1|s0|g6|100|x0|top|Fs0" not in keys  # the later case of the same inner
    assert record["sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    with pytest.raises(plan.NotUsable, match="exists"):
        l1.write_l1_keys(noise, out, noise_sha256=sha)


def test_l1_keys_refusals(tmp_path) -> None:
    noise = tmp_path / "noise.json"
    sha = _noise(noise, drop_l1="g6|5|x5|top|Fs0")
    with pytest.raises(plan.NotUsable, match="no L1 job"):
        l1.write_l1_keys(noise, tmp_path / "a.txt", noise_sha256=sha)
    with pytest.raises(plan.NotUsable, match="--noise"):
        l1.write_l1_keys(noise, tmp_path / "b.txt", noise_sha256="0" * 64)
    assert not (tmp_path / "a.txt").exists()


def test_l1_keys_main_in_another_folder(tmp_path, monkeypatch, capsys) -> None:
    noise = tmp_path / "in" / "noise.json"
    noise.parent.mkdir()
    sha = _noise(noise)
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")
    monkeypatch.setattr(l1.write_l1_keys, "__defaults__", (sha,))
    assert l1.main(["--noise", str(noise), "--out", str(tmp_path / "out" / "k.txt")]) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["keys"] == 100
    assert l1.main(["--noise", str(noise), "--out", str(tmp_path / "out" / "k.txt")]) == 2


def test_probe_record_form_is_read_by_the_12b_scan(tmp_path) -> None:
    """2-3: a probe line ``{"key": ..., "setting": ...}`` under 06_analysis is an r79 key of the
    12b base scan."""
    probes = tmp_path / "02_control" / "j_p3_cause" / "ed5_design" / "probes"
    probes.mkdir(parents=True)
    (probes / "probes_ed5.json").write_text(json.dumps({"results": [
        {"key": "L2|s30|ref|0|rigid|B|0,0", "setting": "VBJ", "commit": "8a3c48c7",
         "purpose": "unit tests", "output": "none"}]}, indent=1), encoding="utf-8")
    scan = plan.scan_r79_keys(tmp_path)
    assert scan.keys == {"L2|s30|ref|0|rigid|B|0,0"} and scan.seed_max == 30
