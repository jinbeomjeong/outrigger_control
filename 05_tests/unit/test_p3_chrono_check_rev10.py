"""``p3_chrono_check.compare`` check 3 with criteria revision 10: a differing
``two_pressure.fallback_rod_estimate_Pa`` passes only under A (no fallback event), B (checks 1
and 2) and C (per leg rerun >= stored - 1 Pa). Synthetic case folders."""

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

import p3_chrono_check as check  # noqa: E402

CASE = "SYNTHETIC"
STORED_ESTIMATE_PA = [1.5e6, 1.4e6, 1.3e6, 1.2e6]
EVENTS = [{"t_s": 1.0, "name": "touch:FL"}, {"t_s": 9.0, "name": "ready"}]


def _meta(estimate_Pa: list[float], *, p3: bool) -> dict:
    settings = {"extend_start_rule": "tracked_bound",
                "extend_start_bound": {"revision": 4}} if p3 else {}
    return {"two_pressure": {"settings": settings, "fallback_rod_estimate_Pa": estimate_Pa}}


def _case(folder: Path, estimate_Pa: list[float], events: list[dict], *, p3: bool) -> Path:
    (folder / "record").mkdir(parents=True)
    arrays = {name: np.arange(12.0).reshape(3, 4) for name in check.COMPARED_ARRAYS}
    np.savez(folder / "record" / "record.npz", **arrays)
    result = {"controller_meta": _meta(estimate_Pa, p3=p3),
              "hydraulics_record": {"extend_bound_check": {"breach_reads": [0] * 4,
                                                           "margin_used_reads": [0] * 4}},
              "v5_hydraulics": {"controller_tag": "final_C4G2_P3"}}
    (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")
    (folder / "controller_events.json").write_text(json.dumps(events), encoding="utf-8")
    return folder


@pytest.fixture()
def stored(tmp_path: Path, monkeypatch) -> Path:
    folder = _case(tmp_path / "stored", STORED_ESTIMATE_PA, EVENTS, p3=False)
    monkeypatch.setitem(check.SEALED_SHA256, CASE, check.array_digests(folder))
    return folder


def test_raised_estimate_without_fallback_passes(stored: Path, tmp_path: Path) -> None:
    raised = [value + 2e5 for value in STORED_ESTIMATE_PA]
    rerun = _case(tmp_path / "rerun", raised, EVENTS, p3=True)
    report = check.compare(CASE, stored, rerun)
    assert report["fallback_rod_estimate_differs"]
    assert report["revision10_fallback_estimate"]["all"]
    assert report["checks"]["3_controller_meta_only_p3"] and report["pass"]


def test_lowered_estimate_fails_condition_c(stored: Path, tmp_path: Path) -> None:
    lowered = [*STORED_ESTIMATE_PA[:3], STORED_ESTIMATE_PA[3] - 2.0]
    rerun = _case(tmp_path / "rerun", lowered, EVENTS, p3=True)
    report = check.compare(CASE, stored, rerun)
    conditions = report["revision10_fallback_estimate"]["conditions"]
    assert not conditions["C_rerun_not_below_stored"]
    assert conditions["A_no_fallback_event"] and conditions["B_arrays_and_events_equal"]
    assert not report["revision10_fallback_estimate"]["per_leg"][3]["ok"]
    assert not report["checks"]["3_controller_meta_only_p3"] and not report["pass"]


def test_one_fallback_event_fails_conditions_a_and_b(tmp_path: Path, monkeypatch) -> None:
    events = [*EVENTS, {"t_s": 5.0, "name": "WARN_ROD_PRESSURE_FALLBACK:RR"}]
    stored_dir = _case(tmp_path / "stored", STORED_ESTIMATE_PA, events, p3=False)
    monkeypatch.setitem(check.SEALED_SHA256, CASE, check.array_digests(stored_dir))
    raised = [value + 1e5 for value in STORED_ESTIMATE_PA]
    rerun = _case(tmp_path / "rerun", raised, events, p3=True)
    report = check.compare(CASE, stored_dir, rerun)
    conditions = report["revision10_fallback_estimate"]["conditions"]
    assert not conditions["A_no_fallback_event"]
    assert conditions["B_arrays_and_events_equal"] and conditions["C_rerun_not_below_stored"]
    assert report["revision10_fallback_estimate"]["fallback_events"] == [
        "WARN_ROD_PRESSURE_FALLBACK:RR"]
    assert not report["checks"]["3_controller_meta_only_p3"]


def test_revision10_digest_reads_the_seal_file(tmp_path: Path) -> None:
    seal = tmp_path / "v5_criteria_rev10.sha256"
    seal.write_text("ab" * 32 + "  v5_criteria_rev10.md  sealed ...", encoding="utf-8")
    assert check.revision10_digest(seal) == "ab" * 32
    assert check.revision10_digest(tmp_path / "missing.sha256").startswith("unknown")
