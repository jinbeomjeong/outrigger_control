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
DRY_KEYS_FILE_SHA256_G8 = "b7c7470a800ce1146d30caefa8050fbb1a73c18058af2b23af7dedf399619bd4"
"""Edition 5 erratum 1 9.1: the g8 dry key file (one line
``L2|s25|g8|0|slope|edge|top|4.0|ref|none|0`` + CRLF)."""
DRY_KEYS_FILE_SHA256_REF = "95ce6f27b44bb13b76fe8fb02d056f6dc5ae1de9be28b29d1529b8fbbd965299"
"""Edition 5 erratum 1 9.1: the ref dry key file (one line ``L2|s25|ref|0|rigid|B|0,0`` +
CRLF)."""
DRY_KEYS_FILE_SHA256_BY_FAMILY = {"g6": DRY_KEYS_FILE_SHA256, "g8": DRY_KEYS_FILE_SHA256_G8,
                                  "ref": DRY_KEYS_FILE_SHA256_REF}
"""The fixed key file sha of each r79 dry family (erratum 1 9.1 table)."""
STORED_H6_R79_JUDGE_SHA256 = (
    "d95627ac83a0bfc165df763e898956fbdcbf7c299fb2d9face8915ef478ed57b")
"""436.8 path 1 r79 judge of the stored H-6 (``verif_matrix/v5_resume_4368/judge_932f1fb/
harness_path1/h6_r79_judge.json``, named by that folder's ``h6_judge.json`` inputs): the
record comparison of ``jp3_tjr_judge.py base-judge-compare`` (4a-4 erratum 1, R-2)."""
H10_T4H_SUMS_SHA256 = "3d0ed49a5044c7dd223940e782b6d280a833ffaeb9916347f8cc0622000cc3ac"
"""``prelaunch_j9/h10_reuse_rerun_t4h.SHA256SUMS`` (FIXED_INPUTS): the 426 T4h names of the
stored h10 folder (``records --t4h-sums``, T-JR-13 report and input folder, 4a-5 1)."""
H6_T4H_SUMS_SHA256 = "c426f5185adc04102dca229b9a4257db71e2cc8c5933f392a083086e186ce655"
"""``prelaunch_j9/h6_dg3_v4on_t4h.SHA256SUMS`` (FIXED_INPUTS): the 135 stored H-6 T4h names."""
STORED_H6_JUDGE_SHA256 = (
    "f8352c5d12d31aebcffe2a4bc5bdfa7919e605a3f3261da8455640df3bad0d0b")
"""That folder's ``h6_judge.json`` (FIXED_INPUTS row 24): ``base-judge-compare
--stored-h6-judge`` (prelaunch audit R-8, optional item of the remedy round)."""
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
