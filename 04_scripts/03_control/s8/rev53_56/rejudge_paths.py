"""Locations of the S8 re-judge verify files (judge rev. 52..56) read by the rev53_56 scripts.

The verify files are in ``07_results`` (gitignored), so they exist only on the machine that
ran the re-judge. Git keeps summaries only: ``06_analysis/01_chrono/18_S8/rejudge/`` (list
and SHA256 in ``06_analysis/01_chrono/18_S8/README.md`` and ``_manifest.json``).

Layout (one sub-folder per judge revision, ``rev52`` .. ``rev56``)::

    <S8_REJUDGE_DIR>/rev5x/verify_S8C_*.json, verify_S8ML_{A,B}_*.json
    <S8_REJUDGE_ML768_DIR>/rev5x/verify_S8ML_ml768_*.json

Defaults (environment variable unset or empty):

* ``S8_REJUDGE_DIR`` = ``07_results/S8/archive/18_S8_extra/rejudge``
* ``S8_REJUDGE_ML768_DIR`` = ``07_results/S8/archive/rejudge_ml768``
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]  # 04_scripts/03_control/s8/rev53_56/
VERIFY_DIR_ENV = "S8_REJUDGE_DIR"
ML768_DIR_ENV = "S8_REJUDGE_ML768_DIR"
DEFAULT_VERIFY_DIR = REPO_ROOT / "07_results" / "S8" / "archive" / "18_S8_extra" / "rejudge"
DEFAULT_ML768_DIR = REPO_ROOT / "07_results" / "S8" / "archive" / "rejudge_ml768"
ML768_MARKER = "_ml768_"  # file names of the 768-episode batch hold this tag


def _root_from_env(env_name: str, default: Path) -> Path:
    value = os.environ.get(env_name)
    return Path(value) if value else default


def verify_root() -> Path:
    """Return the parent folder of the ``rev5x`` verify folders (A, B, C, D, mlj, p1r, rest)."""
    return _root_from_env(VERIFY_DIR_ENV, DEFAULT_VERIFY_DIR)


def ml768_root() -> Path:
    """Return the parent folder of the ``rev5x`` ml768 verify folders."""
    return _root_from_env(ML768_DIR_ENV, DEFAULT_ML768_DIR)


def _root_for(file_name: str) -> tuple[Path, str]:
    if ML768_MARKER in file_name:
        return ml768_root(), ML768_DIR_ENV
    return verify_root(), VERIFY_DIR_ENV


def _missing_message(missing: Path, root: Path, env_name: str) -> str:
    return (
        f"S8 re-judge input not found: {missing}\n"
        f"  searched under {root} (override with the environment variable {env_name})\n"
        "  07_results is gitignored: the re-judge verify archive exists only locally on the\n"
        "  machine that ran it. Git holds summaries only, in\n"
        "  06_analysis/01_chrono/18_S8/rejudge/ (see README.md and _manifest.json there)."
    )


def find_rejudge_file(revision: str, file_name: str) -> Path | None:
    """Return ``<root>/<revision>/<file_name>`` if it exists, else ``None``.

    Args:
        revision: Judge revision folder, e.g. ``"rev54"``.
        file_name: Verify file name; names containing ``_ml768_`` are looked up under
            the ml768 root, all others under the verify root.
    """
    root, _ = _root_for(file_name)
    path = root / revision / file_name
    return path if path.is_file() else None


def rejudge_file(revision: str, file_name: str) -> Path:
    """Return ``<root>/<revision>/<file_name>``; same lookup as :func:`find_rejudge_file`.

    Raises:
        FileNotFoundError: The file does not exist (message names the folder searched).
    """
    root, env_name = _root_for(file_name)
    path = root / revision / file_name
    if not path.is_file():
        raise FileNotFoundError(_missing_message(path, root, env_name))
    return path


def verify_dir(revision: str) -> Path:
    """Return the verify folder of one judge revision (without the ml768 files).

    Raises:
        FileNotFoundError: The folder does not exist.
    """
    root = verify_root()
    folder = root / revision
    if not folder.is_dir():
        raise FileNotFoundError(_missing_message(folder, root, VERIFY_DIR_ENV))
    return folder
