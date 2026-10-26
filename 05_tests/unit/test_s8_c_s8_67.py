"""C-S8-67 (``s6_control_spec.md`` rev. 62 317.1, U-S8-67 (나)): V-5 ③′ positive test cases.

``run_S8C.py`` gets the event ``G4RRF`` (= ``G4RF`` with the rod-sensor dropout on RR, the G4
leg) and the set ``mlj_c67``. The existing ``mlj`` / ``mlj_c29`` cases must keep their case
definition hash (SHA-256 of the canonical ``S8Case.to_meta()`` JSON) and the ``mlj`` set its
six members, so the main ML batch and the C-S8-29 runs are unchanged."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

MLJ_META_SHA256 = {
    # computed at master 7b4de6f (before C-S8-67) with :func:`_meta_sha`
    "MLJ_FS24_Fs0": "14b33934972dcb32484cbbfac1fb9c3e964e819c6b6068274f84797d09b58f5e",
    "MLJ_SS9P_Fs0": "e290f04fef74e9002409b94e2ff48fd1adee49aeee6b6fde3f3be6d1411de727",
    "MLJ_K0V_fdown3.5_G4RF_Fs0":
        "923e9d7776e8063ec4fc04153297a96b813d65f38d599096d5bfe003290d8cc9",
    "MLJ_FS24_Fs8": "2b200e078999ca54d0d66a9e27b302d84a90d28f9a9383fa8398583623fd0632",
    "MLJ_SS9P_Fs8": "e7e9004dad7d50eeec66c43e585147576566c013a533655dd1bf675d0a2329ea",
    "MLJ_K0V_fdown3.5_G4RF_Fs8":
        "999ef44185bf772e218b32d804c41db90319a53464e35f23ff449b2c95621240",
}
"""Order = the ``mlj`` set order at 7b4de6f."""
C67 = ["MLJ_K0V_fdown3.5_G4RRF_Fs0", "MLJ_K0V_fdown3.5_G4RRF_Fs8"]


@pytest.fixture(scope="module")
def run_s8c():
    import run_S8C

    return run_S8C


def _meta_sha(run_s8c, case) -> str:
    text = json.dumps(run_s8c.s6c._plain(case.to_meta()), sort_keys=True, default=repr)
    return hashlib.sha256(text.encode()).hexdigest()


def _flat(x, p: str = "") -> dict:
    if isinstance(x, dict):
        return {k2: v2 for k, v in x.items() for k2, v2 in _flat(v, f"{p}.{k}").items()}
    if isinstance(x, (list, tuple)):
        return {k2: v2 for i, v in enumerate(x) for k2, v2 in _flat(v, f"{p}[{i}]").items()}
    return {p: x}


def test_existing_mlj_sets_and_hashes_unchanged(run_s8c) -> None:
    mlj = run_s8c.case_set("mlj")
    assert [c.case_id for c in mlj] == list(MLJ_META_SHA256)
    assert {c.case_id: _meta_sha(run_s8c, c) for c in mlj} == MLJ_META_SHA256
    c29 = run_s8c.case_set("mlj_c29")
    assert [c.case_id for c in c29] == ["MLJ_K0V_fdown3.5_G4RF_Fs0", "MLJ_K0V_fdown3.5_G4RF_Fs8"]
    assert all(_meta_sha(run_s8c, c) == MLJ_META_SHA256[c.case_id] for c in c29)


def test_mlj_c67_cases(run_s8c) -> None:
    assert "mlj_c67" in run_s8c.SET_NAMES
    c67 = run_s8c.case_set("mlj_c67")
    assert [c.case_id for c in c67] == C67
    assert not set(C67) & {c.case_id for c in run_s8c.case_set("mlj")}
    for c in c67:
        assert (c.group, c.priority, c.engine, c.event) == ("MLJ", 5, "L2b_NSC", "G4RRF")
    ev = run_s8c.EVENTS["G4RRF"]
    ref = run_s8c.EVENTS["G4RF"]
    assert ev["rod_fault"] == {"leg": "RR", "fault": "dropout",
                               "after_ready_s": run_s8c.G4RF_FAULT_AFTER_S}
    assert {k: v for k, v in ev.items() if k != "rod_fault"} == \
        {k: v for k, v in ref.items() if k != "rod_fault"}
    assert {k: v for k, v in ev["rod_fault"].items() if k != "leg"} == \
        {k: v for k, v in ref["rod_fault"].items() if k != "leg"}


@pytest.mark.parametrize("fs", ["Fs0", "Fs8"])
def test_g4rrf_differs_from_g4rf_only_in_the_fault_leg(run_s8c, fs) -> None:
    tab = run_s8c.case_table()
    old = tab[f"MLJ_K0V_fdown3.5_G4RF_{fs}"]
    new = tab[f"MLJ_K0V_fdown3.5_G4RRF_{fs}"]
    m_old = _flat(run_s8c.s6c._plain(old.to_meta()))
    m_new = _flat(run_s8c.s6c._plain(new.to_meta()))
    diff = {k for k in set(m_old) | set(m_new) if m_old.get(k) != m_new.get(k)}
    assert diff == {".case_id", ".base.case_id", ".base.scenario.case_id", ".event",
                    ".event_spec.rod_fault.leg", ".notes[0]"}
    assert m_new[".event_spec.rod_fault.leg"] == "RR"
    assert new.scenario.seed == old.scenario.seed
    assert new.duration_s == old.duration_s and new.fs_kN == old.fs_kN
    assert run_s8c.end_rule(new) == run_s8c.end_rule(old)
    assert new.extra_overrides == old.extra_overrides
