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
DRY_KEYS_FILE_SHA256 = "1a79e02fc33ae8844d0cd5672e9e5e745215c354e58e9a8095376939c4335e74"
"""4a-4 erratum 1: ``j4a_remedy_b06e409e/dryrun_selection_r79_key.txt`` (one line
``L2|s25|g6|0|g6|G1+J1@FL|top|Fs0``), the r79 dry key file of ``select`` / ``summarize``."""
STORED_H6_R79_JUDGE_SHA256 = (
    "d95627ac83a0bfc165df763e898956fbdcbf7c299fb2d9face8915ef478ed57b")
"""436.8 path 1 r79 judge of the stored H-6 (``verif_matrix/v5_resume_4368/judge_932f1fb/
harness_path1/h6_r79_judge.json``, named by that folder's ``h6_judge.json`` inputs): the
record comparison of ``jp3_tjr_judge.py base-judge-compare`` (4a-4 erratum 1, R-2)."""
STORED_H6_L1_REFERENCE_SHA256 = (
    "a591c3a8c5b3ad5822877e7f69ce2acf75e4cc96fff139a52fef7b6439d56ce7")
"""Its L1 reference extract (``h6_L1_reference.json`` of the same folder), compared as a
record with the new ``base-judge`` extract."""


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
