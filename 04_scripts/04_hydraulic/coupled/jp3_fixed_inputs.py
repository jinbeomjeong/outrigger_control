"""436.9 fixed judgement inputs (addendum 4a-3 5.4, addendum 4a-4 5): the sha256 every tool
checks before it reads a stored input; a different file is not judgeable.

The unit test ``test_jp3_addendum_4a4.py`` checks these constants against the 4a-4 5 table.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

H10_SHA256 = "ce526b1f71e635e6b80d538f36841ece01710af46f02acb4b3fa1355a5a4dcb3"
"""``v5/resume_k1/h10_reuse_rerun.jsonl``: ``jp3_tjr_judge.py t8 --stored``."""
MAIN_JSONL_SHA256 = "9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e"
"""``v5/main.jsonl``: ``t8 --main-jsonl``, ``run_v5.py j9_t8 --p3-hash-source``, ``select``."""
H6_SHA256 = "ea0ab94c81e58eeb83ab2b6a63494a56c16bcd4165a62de47eba5efd03f23c89"
"""``v5/resume_k1/h6_dg3_v4on.json``: ``t12 --bundle VBH --base``, ``select --dg3``."""
NOISE_VB_SHA256 = "2219ab9782b22fbe07e6c1f90e8b49c6b3703b0575b5d7cfb7d72b4f067bec43"
"""``v5/resume_k1/h8_noise_VB.json`` (4a-4 1 table): ``select --noise``."""
BASELINE_SUMS_SHA256 = "197ac14e96822130ba4eee98486be6ba9646c207ed1a27936c275077b3a60361"
"""``baseline_221456d/SHA256SUMS``: ``select --baseline`` (and ``jp3_baseline_compare``)."""
GRID_SHA256 = "7160f9f19b497ea264e9dd90c58c2da25540ded51e8510197205cf91f00bd827"
"""``v5/resume_k1/h9_grid/grid_r67_top.json``: ``jp3_case_judge.py case-f`` / ``case-f-path``."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha_problem(path: Path, expected: str, label: str) -> str | None:
    """Why ``path`` is not the fixed input ``label`` (None: it is)."""
    path = Path(path)
    if not path.is_file():
        return f"{label}: {path} missing"
    actual = file_sha256(path)
    if actual != expected:
        return f"{label}: {path.name} sha256 {actual[:12]} is not the fixed {expected[:12]}"
    return None
