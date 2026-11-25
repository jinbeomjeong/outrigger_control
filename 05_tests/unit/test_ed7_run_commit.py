"""436.9 edition 7 run commit C (``jp3_remedy_spec_v7.md`` 5.1 (iii), P7-10): the two sealed
constants carry the values of the sealed spec, revision 6 (sha256 10902ffd...).

* ``JP3_SPEC_EDITION_V7`` = the first 8 hex digits of the sealed spec (the ``spec_edition`` of
  every revision 7 record);
* ``run_v5.ED7_KEY_FILE_SHA256`` = the two sealed key files of ``ed7_design/keys_seal_b46bdf8f/``
  (the ``ed7_keys`` batch refuses any other file).

The expected values are written out here (the sealed spec file is not part of the run commit),
so a later change of either constant fails this test.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from outrigger_sim.control import extend_start_bound as esb  # noqa: E402

SEALED_SPEC_SHA256 = "10902ffdb763aa092588b1be0dd13f55874826b489f9aa9f1351dd7f48c1da45"
"""sha256 of the sealed ``jp3_remedy_spec_v7.md`` revision 6 (its ``.sha256``, master e241638d)."""
SEALED_KEY_FILE_SHA256 = {
    "sens_keys_ed7.json": "be930b75a375877d07fc84fa98a9f8b0ee463f5b592319cfd6869fcc62a05b1b",
    "confirm_g1_grid171.json": "684054abb1ad05d8f82141f58eafdfa3c096edae1c05c9a4b9e8ae9ffe5b5dec",
}
"""Spec v7 5.1 table, ``ED7_KEY_FILE_SHA256`` "고정할 값" (revision 6)."""


def test_spec_edition_v7_is_the_sealed_spec_prefix() -> None:
    assert esb.JP3_SPEC_EDITION_V7 == SEALED_SPEC_SHA256[:8] == "10902ffd"
    assert esb.JP3_SPEC_EDITION_OF_REVISION[esb.EXTEND_SEED_FIX_REVISION] == "10902ffd"
    assert esb.ExtendStartBound(revision=7).identity()["spec_edition"] == "10902ffd"


def test_earlier_revisions_keep_their_sealed_editions() -> None:
    assert esb.ExtendStartBound(revision=5).identity()["spec_edition"] == "8be9de22"
    assert esb.ExtendStartBound(revision=6).identity()["spec_edition"] == "fe6f5844"


def test_ed7_key_file_sha256_is_the_sealed_table() -> None:
    import run_v5

    assert run_v5.ED7_KEY_FILE_SHA256 == SEALED_KEY_FILE_SHA256


def _write_key_file(folder: Path, name: str) -> Path:
    path = folder / name
    document = {
        "expected_lines": 1,
        "lines": [{"job": {"case": "R12", "eps": 0.0, "setting": "VBM"}}],
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


@pytest.mark.parametrize("name", [*SEALED_KEY_FILE_SHA256, "other_keys.json"])
def test_ed7_keys_refuses_a_file_other_than_the_sealed_bytes(tmp_path: Path, name: str) -> None:
    import run_v5

    path = _write_key_file(tmp_path, name)
    assert hashlib.sha256(path.read_bytes()).hexdigest() not in SEALED_KEY_FILE_SHA256.values()
    run_v5.ED7_KEYS_FILE[0] = path
    try:
        with pytest.raises(SystemExit, match="is not a sealed ed7_keys key file"):
            run_v5.batch_jobs(run_v5.ED7_KEYS_BATCH)
    finally:
        run_v5.ED7_KEYS_FILE[0] = None


def test_ed7_keys_accepts_a_file_whose_name_and_sha256_are_sealed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The acceptance path of ``sealed_key_jobs`` with a stand-in table entry (the sealed key
    files are not in a worktree)."""
    import run_v5

    path = _write_key_file(tmp_path, "sens_keys_ed7.json")
    stand_in = {"sens_keys_ed7.json": hashlib.sha256(path.read_bytes()).hexdigest()}
    monkeypatch.setattr(run_v5, "ED7_KEY_FILE_SHA256", stand_in)
    assert run_v5.sealed_key_jobs(path, run_v5.ED7_KEY_FILE_SHA256, run_v5.ED7_KEYS_BATCH) == [
        {"case": "R12", "eps": 0.0, "setting": "VBM"}
    ]
