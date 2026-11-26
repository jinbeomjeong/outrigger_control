"""436.9 edition 8 run commit C8 (``jp3_remedy_spec_v8_rules.md`` 11.1, P8-10).

C8 fills ``run_v5.ED8_KEY_FILE_SHA256`` with the two sealed key files made by
``ed8_key_lists.py`` at the implementation commit 41e107e9 (``ed8_design/keys_seal_41e107e9/``).
These tests pin the values, regenerate both files from the sources of the records checkout
(``OUTRIGGER_RECORDS_ROOT``) and check that the edition 8 key batches take the sealed files and
refuse an altered copy.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _path in (COUPLED_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

RECORDS_ROOT = Path(os.environ.get("OUTRIGGER_RECORDS_ROOT", str(ROOT)))
"""The checkout with the analysis records (the main checkout when the tests run in a
worktree)."""
SEAL_DIR = (RECORDS_ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "ed8_design"
            / "keys_seal_41e107e9")
SEALED_SHA256 = {
    "census_keys_ed8.json": "278b332f694405d5f9be432467e294b64492d5ffd638a76986e819460c88c535",
    "heldout_g_ed8.json": "a18b5818734f1b10840c903fb9e4b5c140f619705048344f9ea48d16d3142ee5",
}
"""Spec v8 11.1 / P8-10: the key files C8 seals (census 1043 lines, held-out G' 339 lines)."""
EXPECTED_LINES = {"census_keys_ed8.json": 1043, "heldout_g_ed8.json": 339}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sources_present() -> bool:
    import ed8_key_lists as keys

    return all((RECORDS_ROOT / path).exists() for path, _ in (
        keys.J9_MAIN, keys.SENS_KEYS, keys.G1_KEYS, keys.GRID192_KEYS))


@pytest.fixture(scope="module")
def regenerated() -> dict[str, bytes]:
    """Both key files made again from the sources (P8-10)."""
    import ed8_key_lists as keys

    if not _sources_present():
        pytest.skip(f"the key-file sources are not under {RECORDS_ROOT} (OUTRIGGER_RECORDS_ROOT)")
    sources = keys.read_census_sources(RECORDS_ROOT)
    return {
        "census_keys_ed8.json": keys.document_bytes(keys.census_document(sources)),
        "heldout_g_ed8.json": keys.document_bytes(keys.heldout_document(RECORDS_ROOT, sources)),
    }


@pytest.fixture()
def sealed_files(tmp_path: Path, regenerated: dict[str, bytes]) -> dict[str, Path]:
    """The regenerated files written under their sealed names (a folder of the test)."""
    paths = {}
    for name, data in regenerated.items():
        paths[name] = tmp_path / name
        paths[name].write_bytes(data)
    return paths


def test_c8_key_table_is_the_sealed_one() -> None:
    import run_v5

    assert run_v5.ED8_KEY_FILE_SHA256 == SEALED_SHA256


def test_p8_10_regenerated_files_have_the_sealed_sha256(regenerated: dict[str, bytes]) -> None:
    for name, data in regenerated.items():
        assert _sha256(data) == SEALED_SHA256[name], name
        assert len(json.loads(data)["lines"]) == EXPECTED_LINES[name], name


def test_p8_10_regenerated_files_equal_the_sealed_folder(regenerated: dict[str, bytes]) -> None:
    if not SEAL_DIR.is_dir():
        pytest.skip(f"no sealed key folder {SEAL_DIR} (OUTRIGGER_RECORDS_ROOT)")
    for name, data in regenerated.items():
        stored = (SEAL_DIR / name).read_bytes()
        assert stored == data, name
        assert stored.splitlines() == data.splitlines(), name


def test_edition_8_key_batches_take_the_sealed_files(sealed_files: dict[str, Path],
                                                      monkeypatch) -> None:
    import run_v5

    monkeypatch.setattr(run_v5, "ED8_KEYS_FILE", [sealed_files["census_keys_ed8.json"]])
    assert len(run_v5.batch_jobs(run_v5.ED8_KEYS_BATCH)) == 1043
    monkeypatch.setattr(run_v5, "ED8_KEYS_FILE", [sealed_files["heldout_g_ed8.json"]])
    assert len(run_v5.batch_jobs(run_v5.ED8_KEYS_BATCH)) == 339
    assert len(run_v5.batch_jobs(run_v5.ED8_HELDOUT_V0_BATCH)) == 678


@pytest.mark.parametrize("name", sorted(SEALED_SHA256))
def test_edition_8_key_batches_refuse_an_altered_copy(sealed_files: dict[str, Path], name: str,
                                                       monkeypatch) -> None:
    import run_v5

    path = sealed_files[name]
    document = json.loads(path.read_bytes())
    document["lines"] = document["lines"][:-1]  # one line less, same file name
    path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(run_v5, "ED8_KEYS_FILE", [path])
    with pytest.raises(SystemExit):
        run_v5.batch_jobs(run_v5.ED8_KEYS_BATCH)


def test_edition_8_key_batches_refuse_another_name(sealed_files: dict[str, Path],
                                                    tmp_path: Path, monkeypatch) -> None:
    import run_v5

    renamed = tmp_path / "census_keys_ed8_copy.json"
    renamed.write_bytes(sealed_files["census_keys_ed8.json"].read_bytes())
    monkeypatch.setattr(run_v5, "ED8_KEYS_FILE", [renamed])
    with pytest.raises(SystemExit):
        run_v5.batch_jobs(run_v5.ED8_KEYS_BATCH)
