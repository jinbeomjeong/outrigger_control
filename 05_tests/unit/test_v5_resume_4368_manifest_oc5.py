"""436.8 rules rev15 R15-5 (f): the ``manifest`` rows of ``V5-RESUME-K1-OC5PROBE`` / ``-OC5``
(``v5_resume_4368_chrono_rows.manifest_oc5_rows``; cad 2026-11-14).

The launch definitions (``oc5_rows``, used by ``s9_batch``) stay as they were: a decided row launches no probe. The
manifest keeps every probe already run (state ``probes``) and adds the main row of each decided row. No Chrono run;
the argv builders need ``s9_batch`` (pychrono import), so the tests skip without it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHRONO_SCRIPTS = PROJECT_ROOT / "04_scripts" / "02_chrono"


def _import(name: str):
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(CHRONO_SCRIPTS))


@pytest.fixture(scope="module")
def mod():
    return _import("v5_resume_4368_chrono_rows")


@pytest.fixture(scope="module")
def sb():
    pytest.importorskip("pychrono")
    return _import("s9_batch")


def _state(probes_a, probes_b):
    return {"rows": {"C-8a": {"probes": probes_a, "main": None}, "C-8b": {"probes": probes_b, "main": None}}}


def _probe(n, k, rc, attempt=1):
    return {"n": n, "attempt": attempt, "k": k, "R_c": rc, "duration_s": 7.0, "case": f"c{n}{attempt}", "folder": "f"}


def test_empty_state_same_as_launch(mod, sb):
    st = _state([], [])
    assert mod.manifest_oc5_rows(sb, st) == mod.oc5_rows(sb, st)
    probes, mains = mod.manifest_oc5_rows(sb, st)
    assert [r["case"] for r in probes] == ["OC5P_Kc3_VB_n1_k0p9179", "OC5P_Kc1_V0_n1_k0p8829"] and mains == []


def test_decided_keeps_run_probes_and_adds_main(mod, sb):
    st = _state([_probe(1, 0.9179, 0.9523695802182304)], [_probe(1, 0.8829, 0.9568086623414596)])
    launch_probes, launch_mains = mod.oc5_rows(sb, st)
    assert launch_probes == []  # launch definition unchanged: no probe once decided
    probes, mains = mod.manifest_oc5_rows(sb, st)
    first = mod.oc5_rows(sb, _state([], []))[0]
    assert probes == first  # the run probes are the rows the empty state launched (same argv, same fields)
    assert mains == launch_mains
    assert [r["case"] for r in mains] == ["OC5_mixed_rigid_J1FR_Kc3_VB_top", "OC5_mixed_rigid_J1FR_Kc1_V0_top"]


def test_probing_lists_run_then_next(mod, sb):
    st = _state([_probe(1, 0.9179, 1.0)], [])  # C-8a probing (n2 next), C-8b first probe next
    probes, mains = mod.manifest_oc5_rows(sb, st)
    names = [r["case"] for r in probes]
    assert names[0] == "OC5P_Kc3_VB_n1_k0p9179"  # the run probe first
    assert set(names[1:]) == {r["case"] for r in mod.oc5_rows(sb, st)[0]}
    assert len(names) == len(set(names)) == 3 and mains == []
