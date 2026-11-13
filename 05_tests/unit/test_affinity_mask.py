"""Pool affinity masks (``s9_batch run --p-mask / --e-mask``, ``hostcpu.MASK_ENV``; cad-expert 2026-11-13).

Record-only option: the masks go into the child env, never into argv. The one process test pins a short child
python to E-cores 16-23 (skipped off Windows or without an E pool covering them). No Chrono run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "03_src"
CHRONO_SCRIPTS = PROJECT_ROOT / "04_scripts" / "02_chrono"
sys.path.insert(0, str(SRC))

from outrigger_sim import hostcpu  # noqa: E402


def _s9b():
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    try:
        import s9_batch  # noqa: PLC0415

        return s9_batch
    finally:
        sys.path.remove(str(CHRONO_SCRIPTS))


FAKE_SETS = [{"id": i, "group": 0, "logical": i, "core": i, "efficiency_class": 1 if i < 16 else 0} for i in range(28)]


def test_parse_and_pool_override():
    assert hostcpu.parse_mask("0x00FF0000") == 0x00FF0000 and hostcpu.parse_mask(" 255 ") == 255
    for bad in ("0", "-1", "zz"):
        with pytest.raises(ValueError):
            hostcpu.parse_mask(bad)
    e = hostcpu.pool_logical("ecore", FAKE_SETS)
    p = hostcpu.pool_logical("pcore", FAKE_SETS)
    assert e == list(range(16, 28)) and p == list(range(16))
    assert hostcpu.pool_mask_override("ecore", e, {}) == (None, None)
    assert hostcpu.pool_mask_override("ecore", e, {"OUTRIGGER_ECORE_MASK": ""}) == (None, None)
    assert hostcpu.pool_mask_override("ecore", e, {"OUTRIGGER_ECORE_MASK": "0x00FF0000"}) == (0x00FF0000, "0x00FF0000")
    assert hostcpu.pool_mask_override("pcore", p, {"OUTRIGGER_ECORE_MASK": "0x00FF0000"}) == (None, None)
    with pytest.raises(ValueError, match="outside the ecore pool"):
        hostcpu.pool_mask_override("ecore", e, {"OUTRIGGER_ECORE_MASK": "0x000000FF"})
    assert hostcpu.mask_hex(0xFF0000) == "0x00FF0000"
    assert _s9b().MASK_ENV == hostcpu.MASK_ENV


def test_case_env_and_record_without_masks_unchanged(monkeypatch):
    s9b = _s9b()
    for k in hostcpu.MASK_ENV.values():
        monkeypatch.delenv(k, raising=False)
    env = s9b._case_env("ecore")
    assert not any(k in env for k in hostcpu.MASK_ENV.values())
    assert s9b.mask_env_record(env, "ecore") == {}
    assert s9b.pool_masks(None, None) is None


def test_case_env_with_masks(monkeypatch):
    s9b = _s9b()
    monkeypatch.setattr(hostcpu, "cpu_sets", lambda: FAKE_SETS)
    masks = s9b.pool_masks(None, "0xFF0000")
    assert masks == {"ecore": "0x00FF0000"}
    env = s9b._case_env("pcore", masks=masks)
    assert env["OUTRIGGER_ECORE_MASK"] == "0x00FF0000" and "OUTRIGGER_PCORE_MASK" not in env
    rec = s9b.mask_env_record(env, "pcore")
    assert rec == {"affinity_mask_requested": None, "affinity_mask_env": {"OUTRIGGER_ECORE_MASK": "0x00FF0000"}}
    assert s9b.mask_env_record(env, "ecore")["affinity_mask_requested"] == "0x00FF0000"
    with pytest.raises(SystemExit, match="outside the pcore pool"):
        s9b.pool_masks("0x00FF0000", None)


def test_resume_mask_changes_record_only():
    s9b = _s9b()
    kept = [{"case": "a"}, {"case": "b"}, {"case": "c"}]
    former = {"a": {"pool": "ecore", "affinity_mask_requested": "0x00FF0000"}, "b": {"pool": "ecore"},
              "c": {"pool": "earlier_launch"}}
    assert s9b.resume_mask_changes(kept, former, {"ecore": "0x00FF0000"}) == [
        {"case": "b", "pool": "ecore", "before": None, "now": "0x00FF0000"}]
    assert s9b.resume_mask_changes(kept, former, None) == [
        {"case": "a", "pool": "ecore", "before": "0x00FF0000", "now": None}]


def test_placement_applied_reads_result(tmp_path):
    s9b = _s9b()
    (tmp_path / "r1").mkdir()
    pl = {"mode": "ecore", "affinity_mask_requested": "0x00FF0000", "affinity_mask_process": "0x00FF0000",
          "affinity_mask_ok": True, "affinity_logical_processors": list(range(16, 24))}
    (tmp_path / "r1" / "result.json").write_text(json.dumps({"placement": pl}), encoding="utf-8")
    got = s9b.placement_applied(tmp_path, {"case": "r1", "argv": []})
    assert got["affinity_mask_process"] == "0x00FF0000" and got["affinity_mask_ok"] is True
    # run_S8C-style row: result in the runner folder named by the case log, placement under runner
    rdir = tmp_path / "S8" / "t_20261113_082117"
    (rdir / "X").mkdir(parents=True)
    (rdir / "X" / "result.json").write_text(json.dumps({"runner": {"placement": pl}}), encoding="utf-8")
    (tmp_path / "r2.log").write_text(f"X: ok 1s\nbatch wall 1 s -> {rdir}\n", encoding="utf-8")
    got = s9b.placement_applied(tmp_path, {"case": "r2", "argv": ["run_S8C.py", "run", "--only", "X"]})
    assert got["mode"] == "ecore" and got["result_json"].endswith("X/result.json")
    assert s9b.placement_applied(tmp_path, {"case": "none", "argv": []}) is None


def _e_pool_has_16_23() -> bool:
    try:
        e = hostcpu.pool_logical("ecore")
    except OSError:
        return False
    return set(range(16, 24)) <= set(e) and len({s["efficiency_class"] for s in hostcpu.cpu_sets()}) > 1


@pytest.mark.skipif(sys.platform != "win32" or not _e_pool_has_16_23(), reason="needs an E pool with CPUs 16-23")
def test_place_process_mask_read_back_child():
    """A child python pinned with OUTRIGGER_ECORE_MASK=0x00FF0000: the record carries the mask read back from the
    process (GetProcessAffinityMask) and psutil sees the same CPU set."""
    code = ("import json, sys; sys.path.insert(0, sys.argv[1]); from outrigger_sim.hostcpu import place_process; "
            "info = place_process('ecore'); import psutil; info['psutil'] = psutil.Process().cpu_affinity(); "
            "print(json.dumps(info))")
    env = dict(os.environ, OUTRIGGER_ECORE_MASK="0x00FF0000")
    out = subprocess.run([sys.executable, "-I", "-c", code, str(SRC)], capture_output=True, text=True, env=env,
                         timeout=60, stdin=subprocess.DEVNULL, check=True)
    info = json.loads(out.stdout.strip().splitlines()[-1])
    assert info["affinity_ok"] and info["affinity_mask_ok"] is True
    assert info["affinity_mask_requested"] == info["affinity_mask_process"] == "0x00FF0000"
    assert info["affinity_logical_processors"] == list(range(16, 24)) == sorted(info["psutil"])
    bad = subprocess.run([sys.executable, "-I", "-c", code, str(SRC)], capture_output=True, text=True, timeout=60,
                         env=dict(os.environ, OUTRIGGER_ECORE_MASK="0x000000FF"), stdin=subprocess.DEVNULL)
    assert bad.returncode != 0 and "outside the ecore pool" in bad.stderr
