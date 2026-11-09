"""Judge of the LAS-b revision A targets, addendum rev2 (P5r4 only: lower-floor criterion
G-2' and the out-of-sample quarter-step phase grid R-Q).

Rules: ``06_analysis/02_control/verif_matrix/las_revA_targeted_rules_rev2.md`` (control-expert,
sealed after the R-G / R-H results; LF sha256 :data:`RULES_REVA_REV2_SHA256`) on top of
rev1 (:data:`RULES_REVA_REV1_SHA256`), the revA rules (:data:`RULES_REVA_SHA256`) and the two
files they inherit (``las_rev_targeted_rules.md`` and its rev1); all five are checked (H-1,
:data:`SEALED_RULES`). The rules text wins where this code differs; rev2 wins over the
earlier files. Like ``las_rev_judge`` (whose pair checks it reuses) this module reads only
JSON lines, so ``las_revA_targeted.py`` uses its checks during a batch and a re-count script
can read the same files on its own.

Inputs: the ``revA_R*.jsonl`` files of ``las_revA_targeted.py`` in ``v5/las/revA2/``
(``rev`` block per line), the stored L lines of ``las_rev_judge.load_stored`` for R-T / R-S,
and three stored reference files that are not in git (pass their paths, H-10):
``v5/las/rev/rev_RG.jsonl`` (P5 R-G pairs, :data:`REFERENCE_RG_SHA256`, ``--ref-rg``),
``v5/las/revA/revA_RG.jsonl`` and ``revA_RH.jsonl`` (the stored P5r4 lines R-0A must
reproduce and the R-H P5 pairs, :data:`STORED_REVA_RG_SHA256` / :data:`STORED_REVA_RH_SHA256`,
``--ref-reva-rg`` / ``--ref-reva-rh``).

What it checks (rev2 / original rules section in brackets):
  R-0 [7.1]          six P0 hashes against the stored 64-character values (H-2).
  R-0P5 [7.2]        30 P5 lines (N_r 0): hash and ``F_RL_kN`` = the reference P5 line (H-2).
  R-0A [R2-5]        P5r4 on the 30 R-G + 24 R-H points: ``commands_sha256`` = the stored P5r4
                     line of the same point, 64 characters (H-2). Its lines are the R-G / R-H
                     part of (ga)'; integer ``j`` = R-G part, half step = R-H part.
  R-Q [R2-3]         P5r4 on the 48 quarter-step points (j 0.25 .. 3.75); no P5 pair.
  K-A [2.1, R2-3]    R-0A lines against their P5 pair (R-G part: ``rev_RG.jsonl``, R-H part:
                     the ``revA_RH.jsonl`` P5 line) K-A1 .. K-A8; R-Q lines K-A5 (lambda_0
                     from the line's own last acted period, the ramp acted, the step sequence),
                     K-A6, K-A8. A K-A5 / K-A6 / K-A8 mismatch is H-13 ``stop``.
  (ga)' [R2-4]       G-1 / G-1H / G-1Q F_RL and F_judged >= 10.400 kN, G-2' F_RL and F_judged
                     >= :data:`G2P_FLOOR_KN` over all 102 lines, G-3 per part (30 / 24 / 48),
                     G-4 = the K-A checks. Record only: the original G-2 R_c, G-2H R_c union
                     (8 points), the 16-point union, M-1 .. M-3, the trough clusters, Q-1 .. Q-5.
  Clusters [B.1]     gap = ``t_RL_min_s`` - (``las.end_t_s`` + 0.1); gap <= 0.05 s is the
                     lift-off first trough, else after the re-acceleration. Value cluster: low
                     [12.2, 13.5] kN, high [14.0, 16.0] kN, else between / outside (Q-2).
  (na) / (da) [5.2, 5.3] ``las_rev_judge.judge_t`` / ``judge_s`` with the rules 6 exception
                     that counts restarts after the end ramp (``las.ramp.end_t_s``).
  R-P0 [7.4]         ``las_rev_judge.judge_rp0``.
  Status [5.4]       stop > undecidable > fail > pass; no R-0A or R-Q lines is ``incomplete``.
Stops: H-2 (R-0 / R-0P5 / R-0A), H-4 (identity, a P5r6 or other foreign line), H-5, H-6' (P5r4
(ga)' ``fail``: ask), H-10, H-11' (M-1 or M-3 rejected on the 54 R-0A pairs: like H-2), H-13;
asks: H-6', H-9, H-12 (a Q prediction missed: ask before (na) / (da), even after a G-2' pass).
R_c, the force values and Delta F are written with all digits (``--json-out``, Markdown
``repr``).

Usage (python-dev or dynamics-dev, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/las_revA_judge.py [files ...]
      [--ref-rg <rev_RG.jsonl>] [--ref-reva-rg <revA_RG.jsonl>] [--ref-reva-rh <revA_RH.jsonl>]
      [--out <md>] [--json-out <json>]
      (no files: every ``revA_R*.jsonl`` in ``v5/las/revA2/``)
Exit codes: 0 judged, 1 a stop or ask (H-2 .. H-13), an undecidable / stop / ask candidate or
a candidate not run, 2 input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import las_rev_judge as rj  # noqa: E402

MissingField = rj.MissingField
need = rj.need
read_lines = rj.read_lines

ROOT = rj.ROOT
STORED_REVA_DIR = rj.V5_DIR / "las" / "revA"
"""The revA results of commit ``3e70f9c`` (R-0A pair source only, rev2 R2-4)."""
REVA2_DIR = rj.V5_DIR / "las" / "revA2"
"""Output folder of this addendum (rev2 R2-5); the earlier-bundle checks stay inside it."""
REVA_DIR = REVA2_DIR

RULES_REVA_PATH = rj.RULES_PATH.with_name("las_revA_targeted_rules.md")
RULES_REVA_SHA_PATH = RULES_REVA_PATH.with_suffix(".sha256")
RULES_REVA_SHA256 = "b09d004bb2f641db40cdd139a6fb2b1645651e4a3e45a9b16e81a5c938d5778f"
"""``las_revA_targeted_rules.sha256`` (LF digest, sealed 2026-11-09 00:45:52 +09:00)."""
RULES_REVA_REV1_PATH = RULES_REVA_PATH.with_name("las_revA_targeted_rules_rev1.md")
RULES_REVA_REV1_SHA_PATH = RULES_REVA_REV1_PATH.with_suffix(".sha256")
RULES_REVA_REV1_SHA256 = "c02518021c00b69a9d02ec6bceddbea18b9686ef6de96bafe5e55b716b023960"
"""rev1 (LF digest, sealed 2026-11-09 01:30:37 +09:00, pre-result typo fixes)."""
RULES_REVA_REV2_PATH = RULES_REVA_PATH.with_name("las_revA_targeted_rules_rev2.md")
RULES_REVA_REV2_SHA_PATH = RULES_REVA_REV2_PATH.with_suffix(".sha256")
RULES_REVA_REV2_SHA256 = "9f478b7fbc5aa0bd8859716b056bf2d531ac02057dc36d218bada7d7f13e4565"
"""rev2 (LF digest, sealed 2026-11-09 08:02:01 +09:00, after-result criteria change)."""
SEALED_RULES = (*rj.SEALED_RULES,
                (RULES_REVA_PATH, RULES_REVA_SHA_PATH, RULES_REVA_SHA256),
                (RULES_REVA_REV1_PATH, RULES_REVA_REV1_SHA_PATH, RULES_REVA_REV1_SHA256),
                (RULES_REVA_REV2_PATH, RULES_REVA_REV2_SHA_PATH, RULES_REVA_REV2_SHA256))
RULES_FIELDS = ("rules_sha256", "rules_rev1_sha256", "rules_revA_sha256",
                "rules_revA_rev1_sha256", "rules_revA_rev2_sha256")
"""The five rules digests every line records (rev2 B.1), in :data:`SEALED_RULES` order."""
RULES_VALUES = (rj.RULES_SHA256, rj.RULES_REV1_SHA256, RULES_REVA_SHA256,
                RULES_REVA_REV1_SHA256, RULES_REVA_REV2_SHA256)

REFERENCE_RG_SHA256 = "7e8c3b4173f1fc682e665ad173589dbbe335ba914a06d5ef2984c5807bb8cca6"
"""Raw sha256 of the stored P5 R-G lines of the original rules (rules 0 / 3.1, H-10)."""
STORED_REVA_RG_SHA256 = "ac3898095a50ea35e8a2141ba2909bb2f84237d4ad810c6c7360a0956014ede8"
"""Raw sha256 of the stored revA R-G lines (P5r4 / P5r6, rev2 R2-6 H-10)."""
STORED_REVA_RH_SHA256 = "f934cbd945353fe236e5313ed5b0b147c39a7e30f6b1b02cfc5557739422b0c9"
"""Raw sha256 of the stored revA R-H lines (P5 / P5r4 / P5r6, rev2 R2-6 H-10)."""
DEFAULT_REFERENCE_RG = rj.REV_DIR / "rev_RG.jsonl"
DEFAULT_STORED_REVA_RG = STORED_REVA_DIR / "revA_RG.jsonl"
DEFAULT_STORED_REVA_RH = STORED_REVA_DIR / "revA_RH.jsonl"
REFERENCE_CANDIDATE = "P5"

# Rules 1.2: (beta, n_min, N_r); P5r6 is dropped (rev2 R2-2).
CANDIDATE_VALUES = {"P0": (3.5, 0, 0), "P5": (4.5, 0, 0), "P5r4": (4.5, 0, 4)}
JUDGED_CANDIDATE = "P5r4"
JUDGED_CANDIDATES = (JUDGED_CANDIDATE,)
BUNDLES = ("R-0", "R-0P5", "R-0A", "R-Q", "R-T", "R-S", "R-P0", "R-X")
GRID_BUNDLES = ("R-0P5", "R-0A", "R-Q")
BUNDLE_CANDIDATE = {"R-0": "P0", "R-0P5": REFERENCE_CANDIDATE, "R-0A": JUDGED_CANDIDATE,
                    "R-Q": JUDGED_CANDIDATE, "R-T": JUDGED_CANDIDATE, "R-S": JUDGED_CANDIDATE,
                    "R-P0": "P0", "R-X": "P0"}
"""The only candidate a bundle's lines may carry; anything else is an identity problem."""

GRID_SETTINGS = rj.GRID_SETTINGS
GRID_CENTRES = rj.GRID_CENTRES
GRID_STEPS = rj.GRID_STEPS
RANGE_STEPS = rj.RANGE_STEPS
HALF_STEPS = (0.5, 1.5, 2.5, 3.5)
QUARTER_STEPS = (0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75)
UNION_STEPS = tuple(sorted((*RANGE_STEPS, *HALF_STEPS)))
UNION16_STEPS = tuple(sorted((*RANGE_STEPS, *HALF_STEPS, *QUARTER_STEPS)))
"""Rev2 R2-4 record: j 0 .. 3.75 in quarter steps (integer, half and quarter points)."""
POINTS_PER_STEP = len(GRID_SETTINGS) * len(GRID_CENTRES)
GRID_LINES = POINTS_PER_STEP * len(GRID_STEPS)
HALF_LINES = POINTS_PER_STEP * len(HALF_STEPS)
QUARTER_LINES = POINTS_PER_STEP * len(QUARTER_STEPS)
R0A_LINES = GRID_LINES + HALF_LINES
PART_RG, PART_RH, PART_RQ = "R-G", "R-H", "R-Q"
PART_STEPS = {PART_RG: GRID_STEPS, PART_RH: HALF_STEPS, PART_RQ: QUARTER_STEPS}

GRID_FORCE_FLOOR_KN = rj.GRID_FORCE_FLOOR_KN
GRID_RANGE_LIMIT_KN = rj.GRID_RANGE_LIMIT_KN
G2P_FLOOR_KN = 11.414589
"""Rev2 R2-1 G-2': F_min + 2 kN (R8 design target U-R8-18), compared with this value."""
G2P_KEY = "G-2'"
G2P_FAIL_KEY = "G-2'_fail"
TOLERANCE = rj.TIME_TOLERANCE_S
OUTPUT_DELAY_S = 0.1
"""Rules 0: d = 1, the command of period k reaches the plant at t_k + 0.1 s (K-A4, gap)."""
LAMBDA0_TOLERANCE = 1e-4
"""K-A5: the recorded ``start_factor`` against mean(out) / mean(in) of the last acted period
(the diag commands are rounded to 1e-4 mm/s)."""
RAMP_END_REASONS = ("done", "loc", "phase", "soil", "reapproach", "zone")
QUIET_ENDS = ("sum", "time")
KA1_FIELDS = ("start_t_s", "end_t_s", "end_reason", "active_periods", "scaled_periods",
              "start_leg")
KA5_KA6_KA8 = ("K-A5", "K-A6", "K-A8")
"""Rev2 R2-6 H-13: these mismatches in R-0A or R-Q stop everything."""
M2_P5_MAX_RANGE_KN = 1.1049128292761132
"""rev1 RA1-2: stored P5 max R_c (V0 c0.94, j <= 3), not the rounded 1.105."""
M3_BRANCH_A = (("V0", "0.94", 1), ("V0", "0.94", 3), ("V0", "1", 0), ("V0", "1", 2),
               ("V0", "1", 4), ("V0", "nom", 3))
"""Rules 2.2 M-3 (their P5 values: 10.771, 10.650, 10.740, 10.764, 10.728, 11.418 (V0 nom j3,
hash acfe58346d29; 11.314 was VB nom j3, rev1 RA1-1) kN)."""
M3_CONFIRM_COUNT = 4

# Rev2 R2-3.1 R-Q predictions and B.1 cluster classification.
CLUSTER_GAP_S = 0.05
TROUGH_FIRST = "liftoff_first"
TROUGH_AFTER = "after_reacceleration"
LOW_CLUSTER_KN = (12.2, 13.5)
HIGH_CLUSTER_KN = (14.0, 16.0)
CLUSTER_LOW, CLUSTER_HIGH, CLUSTER_BETWEEN, CLUSTER_OUTSIDE = "low", "high", "between", "outside"
Q1_RANGES_KN = {("VB", "1"): (14.13, 14.17), ("VB", "0.94"): (14.61, 14.64)}
Q2_CELLS = (("V0", "1"), ("V0", "0.94"), ("V0", "nom"), ("VB", "nom"))
Q3_LOW_COUNT = (6, 20)
Q4_FLOOR_KN = 14.0
Q5_MIN_RANGE_KN = (12.2, 12.7)
Q5_ALL_FLOOR_KN = 12.0

STATUS_STOP = "stop"
STATUS_UNDECIDABLE = "undecidable"
STATUS_FAIL = "fail"
STATUS_PASS = "pass"
STATUS_INCOMPLETE = "incomplete"
VERDICT_ASK = "ask"
IDENTITY_GROUPS = {JUDGED_CANDIDATE: ("R-0A", "R-Q", "R-T", "R-S"), "P0": ("R-P0", "R-X")}
"""Rules 4 / rev2 R2-5: the lines of one candidate come from one commit (R-0 / R-0P5 are
bit tests; every bundle of this addendum is checked for one commit by the run tool)."""


# ------------------------------------------------------------------------------- reading
def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed_rules_problems(sealed=SEALED_RULES) -> list[str]:
    """H-1 over the five sealed files (original, rev1, revA, revA rev1, revA rev2)."""
    return rj.sealed_rules_problems(sealed)


def reference_problems(path: Path, expected: str = REFERENCE_RG_SHA256) -> list[str]:
    """H-10: a stored reference file is there with its stored raw sha256."""
    if not path.exists():
        return [f"H-10 missing reference {path}"]
    digest = raw_sha256(path)
    if digest != expected:
        return [f"H-10 {path.name} sha256 {digest} != {expected}"]
    return []


def stored_reva_problems(rg_path: Path, rh_path: Path) -> list[str]:
    """H-10 (rev2 R2-6) of the two stored revA files R-0A is paired with."""
    return (reference_problems(rg_path, STORED_REVA_RG_SHA256)
            + reference_problems(rh_path, STORED_REVA_RH_SHA256))


def grid_point_of(line: dict) -> tuple[str, str, int | float] | None:
    """(setting, centre, j) of a grid line; ``j`` keeps its type (half / quarter steps are
    floats)."""
    point = rj.rev_of(line).get("grid_point")
    if point is None:
        return None
    return need(line, "job", "setting"), str(point[0]), point[1]


def part_of(line: dict) -> str | None:
    """The (ga)' part of a grid line: R-Q, or for R-0A the R-G (integer j) or R-H part."""
    bundle = rj.rev_of(line).get("bundle")
    if bundle == "R-Q":
        return PART_RQ
    if bundle != "R-0A":
        return None
    point = rj.rev_of(line).get("grid_point")
    if point is None:
        return None
    return PART_RG if float(point[1]).is_integer() else PART_RH


def _points_of(lines: list[dict], candidate: str, path: Path) -> dict[tuple, dict]:
    out = {}
    for line in lines:
        if rj.rev_of(line).get("candidate") != candidate or rj.is_error(line):
            continue
        point = grid_point_of(line)
        if point in out:
            raise ValueError(f"{path.name}: two {candidate} lines at {point}")
        out[point] = line
    return out


def load_reference(path: Path) -> dict[tuple, dict]:
    """``{(setting, centre, j): P5 line}`` of the reference ``rev_RG.jsonl`` (30 points).

    Raises:
        ValueError: Not 30 distinct P5 grid points.
    """
    out = _points_of(read_lines(path), REFERENCE_CANDIDATE, path)
    if len(out) != GRID_LINES:
        raise ValueError(f"{path.name}: {len(out)} P5 grid points, expected {GRID_LINES}")
    return out


@dataclass
class StoredRevA:
    """The stored revA lines R-0A is paired with (rev2 R2-5, B.1)."""

    p5r4: dict[tuple, dict]
    """P5r4 lines of ``revA_RG.jsonl`` + ``revA_RH.jsonl`` (54 points, the hash reference)."""
    half_p5: dict[tuple, dict]
    """P5 lines of ``revA_RH.jsonl`` (24 points, the K-A pairs of the R-H part)."""


def load_stored_reva(rg_path: Path, rh_path: Path) -> StoredRevA:
    """The P5r4 54 points and the R-H P5 24 points of the stored revA files.

    Raises:
        ValueError: Not 30 + 24 P5r4 points or not 24 R-H P5 points.
    """
    rg_lines, rh_lines = read_lines(rg_path), read_lines(rh_path)
    grid = _points_of(rg_lines, JUDGED_CANDIDATE, rg_path)
    half = _points_of(rh_lines, JUDGED_CANDIDATE, rh_path)
    half_p5 = _points_of(rh_lines, REFERENCE_CANDIDATE, rh_path)
    counts = (len(grid), len(half), len(half_p5))
    if counts != (GRID_LINES, HALF_LINES, HALF_LINES):
        raise ValueError(f"stored revA P5r4 R-G / P5r4 R-H / P5 R-H points {counts}, expected "
                         f"{(GRID_LINES, HALF_LINES, HALF_LINES)}")
    return StoredRevA({**grid, **half}, half_p5)


# ------------------------------------------------------------------------------- line facts
def ramp_of(line: dict) -> dict:
    return need(line, "las", "ramp")


def ramp_end_s(line: dict) -> float | None:
    """Rules 6: restarts must follow the end ramp (``las.ramp.end_t_s``), or the LAS-b end
    when no ramp period was applied."""
    las = line.get("las") or {}
    ramp = las.get("ramp") or {}
    if ramp.get("periods_applied"):
        return ramp.get("end_t_s")
    return las.get("end_t_s")


def tag_problems(line: dict) -> list[str]:
    return rj.tag_problems(line)


def _acted_periods(line: dict) -> list[dict]:
    """The LAS-b ``las`` records of the diag periods that acted (active after the step)."""
    out = []
    for period in need(line, "diag", "periods"):
        las = period.get("las")
        if las and las.get("active_after"):
            out.append(las)
    return out


def lambda0_of(line: dict) -> tuple[bool, float | None]:
    """(lambda_0 < 1, mean(out) / mean(in)) of the line's last acted period (the periods before
    the end are the P5 pair's, K-A2).

    Raises:
        MissingField: The line started and ended but no acted period is recorded.
    """
    acted = _acted_periods(line)
    if not acted:
        raise MissingField("diag.periods[].las of the last acted period")
    last = acted[-1]
    if not last.get("is_scaled"):
        return False, 1.0
    inputs, outputs = last["input_mm_s"], last["output_mm_s"]
    return True, (sum(outputs) / len(outputs)) / (sum(inputs) / len(inputs))


def _forces(line: dict) -> tuple:
    summary = need(line, "diag", "summary")
    return need(summary, "F_RL_kN"), need(summary, "F_judged_min_kN")


def _f_rl(line: dict | None):
    if line is None:
        return None
    return ((line.get("diag") or {}).get("summary") or {}).get("F_RL_kN")


def trough_gap_s(line: dict) -> float | None:
    """B.1 gap = ``t_RL_min_s`` - (``las.end_t_s`` + 0.1 s); None when either is missing."""
    t_min = ((line.get("diag") or {}).get("summary") or {}).get("t_RL_min_s")
    t_end = (line.get("las") or {}).get("end_t_s")
    if t_min is None or t_end is None:
        return None
    return t_min - (t_end + OUTPUT_DELAY_S)


def trough_kind(gap_s: float | None) -> str | None:
    """B.1: gap <= 0.05 s is the lift-off first trough, else after the re-acceleration."""
    if gap_s is None:
        return None
    return TROUGH_FIRST if gap_s <= CLUSTER_GAP_S else TROUGH_AFTER


def _within(value: float, bounds: tuple[float, float]) -> bool:
    return bounds[0] <= value <= bounds[1]


def value_cluster(f_rl_kN: float | None) -> str | None:
    """Q-2 value cluster: low [12.2, 13.5], high [14.0, 16.0], between them, or outside."""
    if f_rl_kN is None:
        return None
    if _within(f_rl_kN, LOW_CLUSTER_KN):
        return CLUSTER_LOW
    if _within(f_rl_kN, HIGH_CLUSTER_KN):
        return CLUSTER_HIGH
    if LOW_CLUSTER_KN[1] < f_rl_kN < HIGH_CLUSTER_KN[0]:
        return CLUSTER_BETWEEN
    return CLUSTER_OUTSIDE


# ------------------------------------------------------------------------------- K-A checks
def settings_problems(line: dict) -> list[str]:
    """K-A8: the controller's own settings are the candidate's (beta, n_min, N_r)."""
    rev = rj.rev_of(line)
    candidate = need(rev, "candidate")
    if candidate not in CANDIDATE_VALUES:
        return [f"K-A8 candidate {candidate!r} is not one of rev2 {sorted(CANDIDATE_VALUES)}"]
    beta, n_min, n_r = CANDIDATE_VALUES[candidate]
    problems = []
    if need(rev, "settings_match") is not True:
        problems.append("K-A8 controller settings differ from the candidate's (other fields)")
    settings = need(rev, "settings")
    actual = (settings.get("light_leg_fraction_of_F_min"), settings.get("min_active_periods"),
              settings.get("end_ramp_periods"))
    if actual != (beta, n_min, n_r):
        problems.append(f"K-A8 settings beta/n_min/N_r {actual} != {(beta, n_min, n_r)}")
    params = need(line, "las", "params")
    from_params = (params.get("beta"), params.get("n_min"), params.get("n_r"))
    if from_params != (beta, n_min, n_r):
        problems.append(f"K-A8 las.params beta/n_min/n_r {from_params}")
    return problems


def _ka1(cand: dict, pair: dict) -> list[str]:
    las, pair_las = need(cand, "las"), need(pair, "las")
    return [f"K-A1 las.{name} {las.get(name)!r} != P5 {pair_las.get(name)!r}"
            for name in KA1_FIELDS if las.get(name) != pair_las.get(name)]


def _commands_before(line: dict, t_end_s: float) -> list[tuple]:
    return [(period["t_s"], period["cmd_mm_s"]) for period in need(line, "diag", "periods")
            if period["t_s"] < t_end_s - TOLERANCE]


def _ka2(cand: dict, pair: dict, t_end_s: float) -> list[str]:
    if _commands_before(cand, t_end_s) != _commands_before(pair, t_end_s):
        return [f"K-A2 period commands before t_e {t_end_s} differ from P5"]
    return []


def _ka4(cand: dict, pair: dict, t_end_s: float) -> list[str]:
    """Force-window rows at the same times inside both windows and before t_e + 0.1 s."""
    rows = need(cand, "diag", "force_window", "rows")
    pair_rows = need(pair, "diag", "force_window", "rows")
    if not rows or not pair_rows:
        return []
    t_from = max(rows[0][0], pair_rows[0][0])
    t_to = min(rows[-1][0], pair_rows[-1][0], t_end_s + OUTPUT_DELAY_S - TOLERANCE)

    def inside(table):
        return [row for row in table if t_from - TOLERANCE <= row[0] < t_to]

    if inside(rows) != inside(pair_rows):
        return [f"K-A4 force_window rows in [{t_from}, {t_to}) differ from P5"]
    return []


def _ramp_sequence_problems(line: dict, ramp: dict, applied: int) -> list[str]:
    """K-A5 sequence: the ramp periods carry m = 1 .. periods_applied and their
    ``ramp_scaled`` count is ``scaled_periods``."""
    ramp_periods = [period["las"] for period in need(line, "diag", "periods")
                    if (period.get("las") or {}).get("ramp_m") is not None]
    steps = [las["ramp_m"] for las in ramp_periods]
    problems = []
    if steps != list(range(1, applied + 1)):
        problems.append(f"K-A5 ramp steps {steps} != 1..{applied}")
    scaled = sum(1 for las in ramp_periods if las.get("ramp_scaled"))
    if scaled != ramp.get("scaled_periods"):
        problems.append(f"K-A5 {scaled} ramp_scaled periods != las.ramp.scaled_periods "
                        f"{ramp.get('scaled_periods')}")
    return problems


def _ka5_ka6(cand: dict, pair: dict | None, n_r: int) -> list[str]:
    """K-A5 / K-A6 (and the K-A8 ``ramp.n_r``); without a P5 pair (R-Q) lambda_0 comes from
    the line itself and "the ramp acted" is ``scaled_periods`` >= 1 (rev2 R2-3)."""
    las = need(cand, "las")
    ramp = ramp_of(cand)
    problems = []
    if ramp.get("n_r") != n_r:
        problems.append(f"K-A8 las.ramp.n_r {ramp.get('n_r')} != {n_r}")
    applied = need(ramp, "periods_applied")
    if las.get("end_reason") not in QUIET_ENDS:
        if applied != 0:
            problems.append(f"K-A6 end {las.get('end_reason')} with {applied} ramp periods")
        return problems
    is_scaled, lambda0 = lambda0_of(cand if pair is None else pair)
    if not is_scaled:
        if applied != 0:
            problems.append(f"K-A6 lambda_0 = 1 with {applied} ramp periods")
        return problems
    if pair is None:
        if not need(ramp, "scaled_periods"):
            problems.append("K-A5 the ramp never scaled a command (no P5 pair to compare)")
    elif cand["commands_sha256"] == pair["commands_sha256"]:
        problems.append("K-A5 commands hash equals P5 although the ramp acts")
    start = need(ramp, "start_factor")
    if start is None or abs(start - lambda0) > LAMBDA0_TOLERANCE:
        problems.append(f"K-A5 start_factor {start!r} != lambda_0 {lambda0!r}")
    if need(ramp, "end_reason") not in RAMP_END_REASONS:
        problems.append(f"K-A5 ramp end_reason {ramp.get('end_reason')!r}")
    limit_ok = applied == n_r if ramp.get("end_reason") == "done" else applied <= n_r
    if not limit_ok:
        problems.append(f"K-A5 {applied} ramp periods with end {ramp.get('end_reason')}")
    return problems + _ramp_sequence_problems(cand, ramp, applied)


def _n_r_of(line: dict) -> int:
    candidate = need(line, "rev", "candidate")
    return CANDIDATE_VALUES.get(candidate, (None, None, -1))[2]


def grid_k_problems(cand: dict, pair: dict, part: str) -> list[str]:
    """K-A1 .. K-A8 of one R-0A line against its P5 pair (rules 2.1; K-A3 on the R-G part).

    Raises:
        MissingField: A field the checks read is not in either line.
    """
    problems = settings_problems(cand)
    las = need(cand, "las")
    if las.get("start_t_s") is None:
        if cand["commands_sha256"] != pair["commands_sha256"]:
            problems.append("K-A7 not started but the commands hash differs from P5")
        return problems
    problems += _ka1(cand, pair)
    t_end_s = las.get("end_t_s")
    if t_end_s is not None:
        problems += _ka2(cand, pair, t_end_s) + _ka4(cand, pair, t_end_s)
    lift, pair_lift = (need(cand, "diag", "summary", "t_lift_s"),
                       need(pair, "diag", "summary", "t_lift_s"))
    if part == PART_RG and lift != pair_lift:
        problems.append(f"K-A3 t_lift_s {lift} != P5 {pair_lift}")
    return problems + _ka5_ka6(cand, pair, _n_r_of(cand))


def quarter_k_problems(line: dict) -> list[str]:
    """K-A5, K-A6, K-A8 of one R-Q line (rev2 R2-3: no P5 pair, so no K-A1 .. K-A4).

    Raises:
        MissingField: A field the checks read is missing.
    """
    problems = settings_problems(line)
    if need(line, "las").get("start_t_s") is None:
        applied = need(ramp_of(line), "periods_applied")
        if applied != 0:
            problems.append(f"K-A6 not started with {applied} ramp periods")
        return problems
    return problems + _ka5_ka6(line, None, _n_r_of(line))


def is_h13(problem: str) -> bool:
    """A K-A5 / K-A6 / K-A8 problem text (rev2 H-13)."""
    return any(name in problem for name in KA5_KA6_KA8)


def pair_k_problems_of_line(line: dict, l_line: dict | None) -> list[str]:
    """K-A7 / K-A8 of one R-T / R-S line against its stored L line.

    Raises:
        MissingField: A field the checks read is missing.
    """
    problems = settings_problems(line)
    if l_line is not None and need(line, "las").get("start_t_s") is None and (
            line["commands_sha256"] != l_line["commands_sha256"]):
        problems.append("K-A7 not started but the commands hash differs from L")
    return problems


def pair_k_problems(lines: list[dict], stored: dict, candidate: str) -> list[str]:
    """K-A7 / K-A8 (H-3) of a candidate's R-T / R-S lines; a missing field is an ``H-4``
    entry (undecidable)."""
    out = []
    for bundle in ("R-T", "R-S"):
        for key, line in rj._pair_lines(lines, bundle, candidate)[0].items():
            try:
                out += [f"{key}: {text}" for text in
                        pair_k_problems_of_line(line, rj.stored_line(stored, key))]
            except MissingField as exc:
                out.append(f"{rj.MISSING_FIELD_MARK} {key}: missing {exc}")
    return out


# ------------------------------------------------------------------------------- bit tests
def judge_r0(lines: list[dict]) -> dict:
    """Rules 7.1: the six P0 hashes (``las_rev_judge.R0_EXPECTED``)."""
    found, problems, errors = {}, [], 0
    for line in lines:
        rev = rj.rev_of(line)
        if rev.get("bundle") != "R-0":
            continue
        if rj.is_error(line):
            errors += 1
            continue
        found[(rev["key"], rev["label"])] = line["commands_sha256"]
        problems += [f"{rev['key']}: {text}" for text in tag_problems(line)]
        try:
            problems += [f"{rev['key']}: {text}" for text in settings_problems(line)]
        except MissingField as exc:
            problems.append(f"{rev['key']}: missing {exc}")
    rows = [{"key": key, "label": label, "expected": sha, "got": found.get((key, label)),
             "equal": found.get((key, label)) == sha}
            for (key, label), sha in rj.R0_EXPECTED.items()]
    return {"rows": rows, "errors": errors, "ran": len(found), "problems": problems,
            "pass": errors == 0 and not problems and all(row["equal"] for row in rows)}


def _bundle_points(lines: list[dict], bundle: str) -> tuple[dict, list[str], int, list]:
    """(lines by point, tag / settings problems, errors, duplicate points) of a grid bundle."""
    found, problems, errors, duplicates = {}, [], 0, []
    for line in lines:
        rev = rj.rev_of(line)
        if rev.get("bundle") != bundle:
            continue
        if rj.is_error(line):
            errors += 1
            continue
        point = grid_point_of(line)
        if point in found:
            duplicates.append(point)
        found[point] = line
        problems += [f"{rev.get('label')}: {text}" for text in tag_problems(line)]
        try:
            problems += [f"{rev.get('label')}: {text}" for text in settings_problems(line)]
        except MissingField as exc:
            problems.append(f"{rev.get('label')}: missing {exc}")
    return found, problems, errors, duplicates


def judge_r0p5(lines: list[dict], reference: dict | None) -> dict:
    """Rules 7.2: 30 P5 lines (N_r 0) with the reference hash and ``F_RL_kN``, bit for bit."""
    found, problems, errors, duplicates = _bundle_points(lines, "R-0P5")
    rows = []
    for point in sorted((reference or {}), key=str):
        ref, line = reference[point], found.get(point)
        got_sha = None if line is None else line["commands_sha256"]
        got_f = _f_rl(line)
        ref_f = ref["diag"]["summary"]["F_RL_kN"]
        rows.append({"point": list(point), "expected": ref["commands_sha256"], "got": got_sha,
                     "F_RL_ref_kN": ref_f, "F_RL_kN": got_f,
                     "equal": got_sha == ref["commands_sha256"] and got_f == ref_f})
    is_pass = (reference is not None and errors == 0 and not problems and not duplicates
               and len(found) == GRID_LINES and all(row["equal"] for row in rows))
    return {"rows": rows, "errors": errors, "ran": len(found), "problems": problems,
            "duplicates": duplicates, "reference": reference is not None, "pass": is_pass}


def r0a_hash_problem(line: dict, stored: StoredRevA | None) -> str | None:
    """H-2 of one R-0A line: its 64-character hash against the stored P5r4 line."""
    point = grid_point_of(line)
    expected = None if stored is None else stored.p5r4.get(point)
    if expected is None:
        return f"H-2 R-0A {point} has no stored P5r4 line"
    if line["commands_sha256"] != expected["commands_sha256"]:
        return (f"H-2 R-0A {point} hash {line['commands_sha256']} != "
                f"{expected['commands_sha256']}")
    return None


def judge_r0a(lines: list[dict], stored: StoredRevA | None) -> dict:
    """Rev2 R2-5: 54 P5r4 lines whose ``commands_sha256`` equals the stored P5r4 line."""
    found, problems, errors, duplicates = _bundle_points(lines, "R-0A")
    rows = []
    for point in sorted((stored.p5r4 if stored else {}), key=str):
        line = found.get(point)
        expected = stored.p5r4[point]["commands_sha256"]
        got = None if line is None else line["commands_sha256"]
        rows.append({"point": list(point), "expected": expected, "got": got,
                     "equal": got == expected})
    extra = sorted(set(found) - set(stored.p5r4 if stored else {}), key=str)
    is_pass = (stored is not None and errors == 0 and not problems and not duplicates
               and not extra and len(found) == R0A_LINES and all(row["equal"] for row in rows))
    return {"rows": rows, "errors": errors, "ran": len(found), "problems": problems,
            "duplicates": duplicates, "extra_points": extra, "stored": stored is not None,
            "pass": is_pass}


# ------------------------------------------------------------------------------- (ga)'
@dataclass
class GridLines:
    """The judged candidate's lines of one (ga)' part (R-G / R-H of R-0A, or R-Q)."""

    part: str
    lines: dict[tuple, dict] = field(default_factory=dict)
    errors: int = 0
    duplicates: list = field(default_factory=list)

    @property
    def bundle(self) -> str:
        return self.part


def part_lines_of(lines: list[dict], part: str, candidate: str = JUDGED_CANDIDATE
                  ) -> GridLines:
    """A part's lines; error lines count by the step of their grid point."""
    out = GridLines(part)
    bundle = "R-Q" if part == PART_RQ else "R-0A"
    for line in lines:
        rev = rj.rev_of(line)
        if rev.get("bundle") != bundle or rev.get("candidate") != candidate:
            continue
        if part_of(line) != part:
            continue
        if rj.is_error(line):
            out.errors += 1
            continue
        point = grid_point_of(line)
        if point in out.lines:
            out.duplicates.append(point)
        out.lines[point] = line
    return out


def expected_points(steps) -> set[tuple]:
    return {(s, c, j) for s in GRID_SETTINGS for c in GRID_CENTRES for j in steps}


def exclusion_problems(grid: GridLines, steps) -> list[str]:
    """G-3 (original G-3): every line there, no error, level budget 0, gates consistent."""
    expected = expected_points(steps)
    problems = []
    if grid.errors or grid.duplicates or set(grid.lines) != expected:
        problems.append(f"{grid.part}: lines {len(grid.lines)}/{len(expected)}, errors "
                        f"{grid.errors}, duplicates {grid.duplicates}, missing "
                        f"{sorted(expected - set(grid.lines), key=str)}, extra "
                        f"{sorted(set(grid.lines) - expected, key=str)}")
    for point, line in grid.lines.items():
        try:
            budget = need(line, "diag", "touch_budget", "level_budget_periods")
            consistent = need(line, "diag", "summary", "gate_consistent")
        except MissingField as exc:
            problems.append(f"{grid.part} {point}: missing {exc}")
            continue
        if budget != 0 or consistent is not True:
            problems.append(f"{grid.part} {point}: level_budget_periods {budget}, "
                            f"gate_consistent {consistent}")
    return problems


def force_failures(grid: GridLines, floor_kN: float = GRID_FORCE_FLOOR_KN
                   ) -> tuple[list[str], list[str]]:
    """(failures below ``floor_kN``, values between 10.400 and 10.4146 kN)."""
    failures, between = [], []
    for point in sorted(grid.lines, key=str):
        line = grid.lines[point]
        try:
            f_rl, f_judged = _forces(line)
        except MissingField:
            continue  # counted by G-3
        if f_rl is None or f_judged is None or min(f_rl, f_judged) < floor_kN:
            failures.append(f"{grid.part} {rj.rev_of(line).get('key')} {point}: F_RL "
                            f"{f_rl!r} F_judged {f_judged!r}")
        for value in (f_rl, f_judged):
            if value is not None and GRID_FORCE_FLOOR_KN <= value < rj.C1_FORCE_FLOOR_N / 1e3:
                between.append(f"{grid.part} {point}: {value!r} kN")
    return failures, between


def range_cells(by_point: dict[tuple, dict], steps, all_steps=GRID_STEPS) -> list[dict]:
    """Per (setting, centre): R_c = max - min of F_RL over ``steps``, M_c their mean and
    P_c = |F(4) - F(0)| (when both are there); ``ok`` is the original 0.500 kN limit
    (record only in rev2)."""
    cells = []
    for setting in GRID_SETTINGS:
        for centre in GRID_CENTRES:
            values = {j: _f_rl(by_point.get((setting, centre, j))) for j in all_steps}
            phase = [values.get(j) for j in steps]
            cell = {"setting": setting, "centre": centre, "values": values}
            if any(value is None for value in phase):
                cells.append({**cell, "R_c": None, "M_c": None, "P_c": None, "ok": False})
                continue
            first, last = values.get(0), values.get(4)
            r_c = max(phase) - min(phase)
            cells.append({**cell, "R_c": r_c, "M_c": sum(phase) / len(phase),
                          "P_c": None if first is None or last is None else abs(last - first),
                          "ok": r_c <= GRID_RANGE_LIMIT_KN + TOLERANCE})
    return cells


def grid_status(has_k_problem: bool, has_undecidable: bool, has_failure: bool) -> str:
    """Rules 5.4: stop > undecidable > fail > pass."""
    if has_k_problem:
        return STATUS_STOP
    if has_undecidable:
        return STATUS_UNDECIDABLE
    return STATUS_FAIL if has_failure else STATUS_PASS


def _paired_k_problems(grid: GridLines, pairs: dict[tuple, dict] | None) -> tuple[list, list]:
    """(K-A problems, undecidable problems) of the R-0A part lines against their P5 pairs."""
    k_found, undecidable = [], []
    for point in sorted(grid.lines, key=str):
        pair = None if pairs is None else pairs.get(point)
        if pair is None:
            undecidable.append(f"{grid.part} {point}: no P5 pair line")
            continue
        try:
            k_found += [f"{grid.part} {point}: {text}"
                        for text in grid_k_problems(grid.lines[point], pair, grid.part)]
        except MissingField as exc:
            undecidable.append(f"{grid.part} {point}: missing {exc}")
    return k_found, undecidable


def _quarter_k(grid: GridLines) -> tuple[list, list]:
    k_found, undecidable = [], []
    for point in sorted(grid.lines, key=str):
        try:
            k_found += [f"{grid.part} {point}: {text}"
                        for text in quarter_k_problems(grid.lines[point])]
        except MissingField as exc:
            undecidable.append(f"{grid.part} {point}: missing {exc}")
    return k_found, undecidable


@dataclass
class PrimeParts:
    """The three (ga)' parts of the judged candidate and the P5 pairs of the R-0A parts."""

    grid: GridLines
    half: GridLines
    quarter: GridLines
    grid_pairs: dict | None
    half_pairs: dict | None

    def all_lines(self) -> dict[tuple, dict]:
        return {**self.grid.lines, **self.half.lines, **self.quarter.lines}


def prime_parts(lines: list[dict], reference: dict | None, stored: StoredRevA | None
                ) -> PrimeParts:
    return PrimeParts(part_lines_of(lines, PART_RG), part_lines_of(lines, PART_RH),
                      part_lines_of(lines, PART_RQ), reference,
                      None if stored is None else stored.half_p5)


def g2_prime_failures(parts: PrimeParts) -> list[dict]:
    """G-2' (rev2 R2-1): every line of the three parts has F_RL and F_judged >= 11.414589 kN;
    the failures with key, part, point and both values."""
    failures = []
    for grid in (parts.grid, parts.half, parts.quarter):
        for point in sorted(grid.lines, key=str):
            line = grid.lines[point]
            summary = (line.get("diag") or {}).get("summary") or {}
            f_rl, f_judged = summary.get("F_RL_kN"), summary.get("F_judged_min_kN")
            if f_rl is None or f_judged is None or min(f_rl, f_judged) < G2P_FLOOR_KN:
                failures.append({"part": grid.part, "key": rj.rev_of(line).get("key"),
                                 "point": list(point), "F_RL_kN": f_rl,
                                 "F_judged_min_kN": f_judged})
    return failures


def judge_prime(lines: list[dict], reference: dict | None, stored: StoredRevA | None) -> dict:
    """(ga)' of P5r4 (rev2 R2-4): G-1, G-1H, G-1Q, G-2', G-3, G-4, the records and the
    status."""
    parts = prime_parts(lines, reference, stored)
    r0a_ran = parts.grid.lines or parts.grid.errors or parts.half.lines or parts.half.errors
    rq_ran = parts.quarter.lines or parts.quarter.errors
    out = {"candidate": JUDGED_CANDIDATE, "R-G_lines": len(parts.grid.lines),
           "R-H_lines": len(parts.half.lines), "R-Q_lines": len(parts.quarter.lines)}
    if not r0a_ran or not rq_ran:
        missing = [name for name, ran in (("R-0A", r0a_ran), ("R-Q", rq_ran)) if not ran]
        return {**out, "status": STATUS_INCOMPLETE, "not_run": missing, "pass": False,
                "records": records(parts)}
    g3 = []
    for grid in (parts.grid, parts.half, parts.quarter):
        g3 += exclusion_problems(grid, PART_STEPS[grid.part])
    k_grid, undecided_grid = _paired_k_problems(parts.grid, parts.grid_pairs)
    k_half, undecided_half = _paired_k_problems(parts.half, parts.half_pairs)
    k_quarter, undecided_quarter = _quarter_k(parts.quarter)
    g1, between = force_failures(parts.grid)
    g1h, between_h = force_failures(parts.half)
    g1q, between_q = force_failures(parts.quarter)
    g2p = g2_prime_failures(parts)
    undecidable = g3 + undecided_grid + undecided_half + undecided_quarter
    if reference is None:
        undecidable.append("H-10 no reference P5 lines for the R-G part")
    if stored is None:
        undecidable.append("H-10 no stored revA lines for the R-H part pairs")
    k_all = k_grid + k_half + k_quarter
    status = grid_status(bool(k_all), bool(undecidable), bool(g1 or g1h or g1q or g2p))
    return {**out, "G-1": not g1, "G-1_fail": g1, "G-1H": not g1h, "G-1H_fail": g1h,
            "G-1Q": not g1q, "G-1Q_fail": g1q, G2P_KEY: not g2p, G2P_FAIL_KEY: g2p,
            "G-3": not g3, "G-3_problems": g3, "G-4": not k_all, "G-4_problems": k_all,
            "H-13": [text for text in k_all if is_h13(text)],
            "undecidable": undecidable, "between_thresholds": between + between_h + between_q,
            "min_F_RL_kN": _min_of(parts, "F_RL_kN"),
            "min_F_judged_kN": _min_of(parts, "F_judged_min_kN"),
            "records": records(parts), "status": status, "pass": status == STATUS_PASS}


def _min_of(parts: PrimeParts, name: str) -> float | None:
    values = [((line.get("diag") or {}).get("summary") or {}).get(name)
              for line in parts.all_lines().values()]
    values = [value for value in values if value is not None]
    return min(values) if values else None


def records(parts: PrimeParts) -> dict:
    """Rev2 R2-4 record items: the original G-2 / G-2H ranges, the 16-point union, the rows
    with their trough clusters and Q-1 .. Q-5."""
    union8 = {**parts.grid.lines, **parts.half.lines}
    return {"G-2_cells": range_cells(parts.grid.lines, RANGE_STEPS),
            "G-2H_union_cells": range_cells(union8, UNION_STEPS, UNION_STEPS),
            "union16_cells": range_cells(parts.all_lines(), UNION16_STEPS, UNION16_STEPS),
            "rows": (grid_rows(parts.grid, parts.grid_pairs)
                     + grid_rows(parts.half, parts.half_pairs) + grid_rows(parts.quarter, None)),
            "Q": q_predictions(parts.quarter)}


def grid_rows(grid: GridLines, pairs: dict | None) -> list[dict]:
    """Record rows (rules 5.1 reference record + rev2 clusters), Delta F against the P5 pair
    (R-0A parts)."""
    rows = []
    for point in sorted(grid.lines, key=str):
        line = grid.lines[point]
        las = line.get("las") or {}
        summary = (line.get("diag") or {}).get("summary") or {}
        pair = None if pairs is None else pairs.get(point)
        f_rl, f_pair = summary.get("F_RL_kN"), _f_rl(pair)
        ramp = las.get("ramp") or {}
        gap = trough_gap_s(line)
        rows.append({"part": grid.part, "key": rj.rev_of(line).get("key"),
                     "point": list(point), "F_RL_kN": f_rl, "F_RL_P5_kN": f_pair,
                     "delta_F_kN": None if f_rl is None or f_pair is None else f_rl - f_pair,
                     "F_judged_min_kN": summary.get("F_judged_min_kN"),
                     "start_t_s": las.get("start_t_s"), "end_t_s": las.get("end_t_s"),
                     "active_periods": las.get("active_periods"),
                     "end_reason": las.get("end_reason"), "t_lift_s": summary.get("t_lift_s"),
                     "lambda_0": ramp.get("start_factor"),
                     "ramp_periods": ramp.get("periods_applied"),
                     "ramp_end_reason": ramp.get("end_reason"),
                     "ramp_end_t_s": ramp.get("end_t_s"),
                     "min_leg_after_lift": summary.get("min_leg_after_lift"),
                     "t_RL_min_s": summary.get("t_RL_min_s"), "gap_s": gap,
                     "trough": trough_kind(gap), "cluster": value_cluster(f_rl),
                     "commands_sha256": line["commands_sha256"]})
    return rows


# ------------------------------------------------------------------------------- Q-1 .. Q-5
def _quarter_facts(quarter: GridLines) -> list[dict]:
    facts = []
    for point in sorted(quarter.lines, key=str):
        line = quarter.lines[point]
        f_rl = _f_rl(line)
        gap = trough_gap_s(line)
        facts.append({"point": point, "cell": point[:2], "F_RL_kN": f_rl, "gap_s": gap,
                      "trough": trough_kind(gap), "cluster": value_cluster(f_rl)})
    return facts


def _q1(facts: list[dict]) -> dict:
    """Q-1: VB 1 and VB 0.94 eight lines each inside their narrow ranges."""
    detail = {}
    is_ok = True
    for cell, bounds in Q1_RANGES_KN.items():
        values = [fact["F_RL_kN"] for fact in facts if fact["cell"] == cell]
        cell_ok = len(values) == len(QUARTER_STEPS) and all(
            value is not None and _within(value, bounds) for value in values)
        detail[" ".join(cell)] = {"range_kN": bounds, "values": values, "ok": cell_ok}
        is_ok = is_ok and cell_ok
    return {"ok": is_ok, "detail": detail}


def _q2_q3(facts: list[dict]) -> tuple[dict, dict]:
    """Q-2: the 32 lines of the four cells are low or high, the low ones first troughs;
    Q-3: 6 .. 20 of them low."""
    lines = [fact for fact in facts if fact["cell"] in Q2_CELLS]
    is_complete = len(lines) == len(Q2_CELLS) * len(QUARTER_STEPS)
    off_cluster = [fact for fact in lines if fact["cluster"] not in (CLUSTER_LOW, CLUSTER_HIGH)]
    low = [fact for fact in lines if fact["cluster"] == CLUSTER_LOW]
    low_not_first = [fact for fact in low if fact["trough"] != TROUGH_FIRST]
    q2 = {"ok": is_complete and not off_cluster and not low_not_first, "lines": len(lines),
          "third_cluster": [_fact_text(fact) for fact in off_cluster],
          "low_not_first_trough": [_fact_text(fact) for fact in low_not_first]}
    q3 = {"ok": is_complete and Q3_LOW_COUNT[0] <= len(low) <= Q3_LOW_COUNT[1],
          "low_count": len(low), "of": len(lines), "range": Q3_LOW_COUNT}
    return q2, q3


def _q4(facts: list[dict]) -> dict:
    """Q-4: every line whose minimum came after the re-acceleration has F_RL >= 14.0 kN."""
    after = [fact for fact in facts if fact["trough"] == TROUGH_AFTER]
    low = [fact for fact in after if fact["F_RL_kN"] is None or fact["F_RL_kN"] < Q4_FLOOR_KN]
    unknown = [fact for fact in facts if fact["trough"] is None]
    return {"ok": not low and not unknown, "after_lines": len(after),
            "below_floor": [_fact_text(fact) for fact in low],
            "no_gap": [_fact_text(fact) for fact in unknown]}


def _q5(facts: list[dict]) -> dict:
    """Q-5: the 48-line minimum in [12.2, 12.7] kN, every line >= 12.0 kN."""
    values = [fact["F_RL_kN"] for fact in facts]
    if not values or None in values:
        return {"ok": False, "min_kN": None, "lines": len(values)}
    low = min(values)
    is_ok = (len(values) == QUARTER_LINES and _within(low, Q5_MIN_RANGE_KN)
             and low >= Q5_ALL_FLOOR_KN)
    return {"ok": is_ok, "min_kN": low, "lines": len(values)}


def _fact_text(fact: dict) -> str:
    return (f"{fact['point']}: F_RL {fact['F_RL_kN']!r} gap {fact['gap_s']!r} "
            f"{fact['trough']} {fact['cluster']}")


def q_predictions(quarter: GridLines) -> dict:
    """Rev2 R2-3.1 Q-1 .. Q-5 on the R-Q lines; ``None`` until all 48 lines are in (a missing
    line is G-3, not H-12). ``missed`` lists the predictions that are false (H-12)."""
    if (len(quarter.lines) != QUARTER_LINES or quarter.errors
            or set(quarter.lines) != expected_points(QUARTER_STEPS)):
        return {"complete": False, "Q-1": None, "Q-2": None, "Q-3": None, "Q-4": None,
                "Q-5": None, "missed": []}
    facts = _quarter_facts(quarter)
    q2, q3 = _q2_q3(facts)
    out = {"complete": True, "Q-1": _q1(facts), "Q-2": q2, "Q-3": q3, "Q-4": _q4(facts),
           "Q-5": _q5(facts)}
    out["missed"] = [name for name in ("Q-1", "Q-2", "Q-3", "Q-4", "Q-5")
                     if not out[name]["ok"]]
    return out


# ------------------------------------------------------------------------------- M-1 .. M-3
def mechanism(lines: list[dict], reference: dict | None, stored: StoredRevA | None) -> dict:
    """M-1 .. M-3 of P5r4 on the 54 R-0A pairs (rules 2.2, rev2 H-11')."""
    parts = prime_parts(lines, reference, stored)
    deltas = {}
    for grid, pairs in ((parts.grid, parts.grid_pairs), (parts.half, parts.half_pairs)):
        for point, line in grid.lines.items():
            f_rl, f_pair = _f_rl(line), _f_rl((pairs or {}).get(point))
            if f_rl is not None and f_pair is not None:
                deltas[point] = f_rl - f_pair
    is_complete = len(deltas) == R0A_LINES
    median = statistics.median(deltas.values()) if deltas else None
    ranges = [cell["R_c"] for cell in range_cells(parts.grid.lines, RANGE_STEPS)]
    max_range = None if None in ranges or not ranges else max(ranges)
    p5_ranges = [cell["R_c"] for cell in range_cells(reference or {}, RANGE_STEPS)]
    branch = {point: deltas.get(point) for point in M3_BRANCH_A}
    known = [value for value in branch.values() if value is not None]
    rises = sum(value > 0 for value in known)
    m3 = None
    if len(known) == len(M3_BRANCH_A):
        m3 = ("confirmed" if rises >= M3_CONFIRM_COUNT
              else "rejected" if all(value < 0 for value in known) else "neither")
    return {"candidate": JUDGED_CANDIDATE, "pairs": len(deltas), "complete": is_complete,
            "delta_F_kN": {str(point): value for point, value in sorted(deltas.items(),
                                                                       key=str)},
            "M-1_median_kN": median,
            "M-1": None if not is_complete else ("confirmed" if median > 0 else "rejected"),
            "M-2_max_R_c_kN": max_range,
            "M-2_P5_max_R_c_kN": None if None in p5_ranges or not p5_ranges else max(p5_ranges),
            "M-2": None if max_range is None else (
                "confirmed" if max_range < M2_P5_MAX_RANGE_KN else "rejected"),
            "M-3_branch_A": {str(point): value for point, value in branch.items()},
            "M-3_branch_A_P5_kN": {str(point): _f_rl((reference or {}).get(point))
                                   for point in M3_BRANCH_A},
            "M-3_rises": rises, "M-3": m3}


# ------------------------------------------------------------------------------- identity
def foreign_line_problems(lines: list[dict]) -> list[str]:
    """Lines of a bundle or candidate rev2 does not run (P5r6, the old R-G / R-H bundles,
    P5 in R-0A, ..): reported as identity problems, never ignored (rev2 B.3)."""
    problems = []
    for line in lines:
        rev = rj.rev_of(line)
        bundle, candidate = rev.get("bundle"), rev.get("candidate")
        if BUNDLE_CANDIDATE.get(bundle) != candidate:
            problems.append(f"{bundle} {candidate} {rev.get('label')} {rev.get('key')}: not a "
                            f"rev2 line (bundle candidate {BUNDLE_CANDIDATE.get(bundle)})")
    return problems


def rules_problems(rev: dict) -> list[str]:
    """The five rules digests a line records (rev2 B.1)."""
    recorded = tuple(rev.get(name) for name in RULES_FIELDS)
    if recorded != RULES_VALUES:
        return [f"rules sha256 {recorded}"]
    return []


def identity_problems(lines: list[dict]) -> dict[str, list[str]]:
    """H-4 (rules 4) per candidate: one commit, no code diff, allowed dirty files only, the
    five rules sha256 and the controller tag of the setting; ``foreign`` = lines rev2 does
    not run."""
    out = {}
    for candidate, bundles in IDENTITY_GROUPS.items():
        heads, problems = set(), []
        for line in lines:
            rev = rj.rev_of(line)
            if rev.get("candidate") != candidate or rev.get("bundle") not in bundles or (
                    rj.is_error(line)):
                continue
            identity = rev.get("identity") or {}
            heads.add(identity.get("git_head"))
            key = f"{rev.get('bundle')} {rev.get('label')} {rev.get('key')}"
            if identity.get("code_diff_sha256") != rj.EMPTY_SHA256:
                problems.append(f"{key}: code diff")
            extra = set(identity.get("dirty_files") or ()) - set(rj.ALLOWED_DIRTY)
            if extra:
                problems.append(f"{key}: dirty {sorted(extra)}")
            problems += [f"{key}: {text}" for text in rules_problems(rev)]
            problems += [f"{key}: {text}" for text in tag_problems(line)]
        if len(heads) > 1:
            problems.append(f"{len(heads)} commits: {sorted(map(str, heads))}")
        if problems:
            out[candidate] = problems
    foreign = foreign_line_problems(lines)
    if foreign:
        out["foreign"] = foreign
    return out


# ------------------------------------------------------------------------------- verdict
def _pair_verdict(t_result: dict | None, s_result: dict | None, rp0: dict) -> dict:
    """(na) / (da) part of a candidate that passed (ga)'.

    Rules 5.4 order: incomplete (not run) > undecidable (missing pair, empty population with
    changed hashes = R-1 / R-2 None) > fail (a check False) > H-9 ask > R-P0 > adopt. A
    missing pair is undecidable even when another pair already failed a check (post-judgement
    audit 2026-11-09; ``las_rev_judge`` let a definite failure win under its own rules).
    """
    if t_result is None or s_result is None:
        return {"verdict": STATUS_INCOMPLETE, "at": "(na)/(da) not run"}
    if not (t_result["complete"] and s_result["complete"]) or None in (
            t_result["checks"]["R-1"], t_result["checks"]["R-2"]):
        return {"verdict": STATUS_UNDECIDABLE, "at": "missing / empty population"}
    failed = [f"{label} {check}" for label, result in (("(na)", t_result), ("(da)", s_result))
              for check, value in result["checks"].items() if value is False]
    if failed:
        return {"verdict": STATUS_FAIL, "at": failed}
    if t_result["exception_excess"]:
        return {"verdict": VERDICT_ASK, "at": "H-9 exception excess"}
    if not rp0["pass"]:
        return {"verdict": STATUS_INCOMPLETE, "at": "R-P0"}
    return {"verdict": "adopt_recommended", "at": None}


def candidate_verdict(out: dict) -> dict:
    """Rules 5.4 order for P5r4: stop > undecidable > fail > (H-12 ask) > (na) / (da)."""
    name = JUDGED_CANDIDATE
    grid = out["grid"]
    if grid["status"] == STATUS_INCOMPLETE:
        return {"verdict": STATUS_INCOMPLETE, "at": f"not_run: {grid['not_run']}",
                "not_run": True}
    stop_problems, missing = rj.split_k_problems(out["pair_k_problems"])
    if grid["status"] == STATUS_STOP or stop_problems:
        return {"verdict": STATUS_STOP, "at": "K-A mismatch (implementation defect candidate)"}
    undecidable = [f"H-4 run identity {owner}" for owner in (name, "foreign")
                   if owner in out["identity"]]
    if missing:
        undecidable.append("H-4 missing field")
    if grid["status"] == STATUS_UNDECIDABLE:
        undecidable.append("G-3 / pair / H-10")
    if undecidable:
        return {"verdict": STATUS_UNDECIDABLE, "at": undecidable}
    if grid["status"] == STATUS_FAIL:
        return {"verdict": STATUS_FAIL, "at": "(ga)' G-1 / G-1H / G-1Q / G-2'"}
    missed = grid["records"]["Q"]["missed"]
    pair = _pair_verdict(out["R-T"], out["R-S"], out["R-P0"])
    if missed and pair["verdict"] in (STATUS_INCOMPLETE, "adopt_recommended"):
        return {"verdict": VERDICT_ASK, "at": f"H-12 R-Q predictions missed {missed}"}
    return pair


def judge(lines: list[dict], stored: dict, reference: dict | None,
          stored_reva: StoredRevA | None = None,
          reference_issues: list[str] | None = None) -> dict:
    """Every criterion of the rev2 rules over the given lines."""
    out = {"R-0": judge_r0(lines), "R-0P5": judge_r0p5(lines, reference),
           "R-0A": judge_r0a(lines, stored_reva),
           "grid": judge_prime(lines, reference, stored_reva),
           "mechanism": mechanism(lines, reference, stored_reva), "R-T": None, "R-S": None,
           "stops": list(reference_issues or []), "asks": []}
    if rj._pair_lines(lines, "R-T", JUDGED_CANDIDATE)[0]:
        out["R-T"] = rj.judge_t(lines, stored, JUDGED_CANDIDATE, ramp_end_s)
    if rj._pair_lines(lines, "R-S", JUDGED_CANDIDATE)[0]:
        out["R-S"] = rj.judge_s(lines, stored, JUDGED_CANDIDATE, ramp_end_s)
    out["pair_k_problems"] = pair_k_problems(lines, stored, JUDGED_CANDIDATE)
    out["R-P0"] = rj.judge_rp0(lines, stored)
    out["identity"] = identity_problems(lines)
    _add_stops(out, lines)
    out["candidates"] = {JUDGED_CANDIDATE: candidate_verdict(out)}
    return out


def _has_later_lines(lines: list[dict]) -> bool:
    return any(rj.rev_of(line).get("bundle") not in ("R-0", "R-0P5") for line in lines)


def _add_stops(out: dict, lines: list[dict]) -> None:
    """H-2, H-4, H-5, H-6', H-11', H-12 (ask) and H-13."""
    stops, asks = out["stops"], out["asks"]
    bit_ok = out["R-0"]["pass"] and out["R-0P5"]["pass"]
    if (out["R-0"]["ran"] or out["R-0P5"]["ran"] or _has_later_lines(lines)) and not bit_ok:
        stops.append("H-2 R-0 / R-0P5 bit test not passed")
    later = [line for line in lines if rj.rev_of(line).get("bundle") not in
             ("R-0", "R-0P5", "R-0A")]
    if (out["R-0A"]["ran"] or out["R-0A"]["errors"] or later) and not out["R-0A"]["pass"]:
        stops.append("H-2 R-0A bit test not passed")
    for owner, problems in out["identity"].items():
        stops.append(f"H-4 identity {owner}: {problems[:3]}")
    if out["R-P0"]["H-5"]:
        stops.append(f"H-5 reproduction failed: {out['R-P0']['H-5'][:3]}")
    grid = out["grid"]
    if grid.get("H-13"):
        stops.append(f"H-13 K-A5 / K-A6 / K-A8 mismatch: {grid['H-13'][:3]}")
    if grid["status"] == STATUS_FAIL:
        stops.append("H-6' P5r4 (ga)' fail: stop and ask (no other candidate or m chosen)")
    mech = out["mechanism"]
    if "rejected" in (mech["M-1"], mech["M-3"]):
        stops.append(f"H-11' M-1 {mech['M-1']} / M-3 {mech['M-3']} on the R-0A pairs "
                     f"(handled like H-2)")
    missed = grid["records"]["Q"]["missed"]
    if missed:
        asks.append(f"H-12 R-Q predictions missed {missed}: ask before (na) / (da)")


def is_stop_result(result: dict) -> bool:
    """Exit 1: a stop, an ask, or an undecidable / stop / ask / not-run candidate."""
    return bool(result["stops"] or result["asks"]) or any(
        verdict["verdict"] in (STATUS_UNDECIDABLE, STATUS_STOP, VERDICT_ASK)
        or verdict.get("not_run") for verdict in result["candidates"].values())


def r0a_gate_problems(lines: list[dict], reference: dict | None,
                      stored: StoredRevA | None) -> list[str]:
    """H-2 / H-3 / H-11' / H-13 before R-Q: the 54 R-0A hashes reproduced, no K-A mismatch
    or missing field on them and neither M-1 nor M-3 rejected."""
    result = judge_r0a(lines, stored)
    problems = []
    if not result["pass"]:
        bad = [row["point"] for row in result["rows"] if not row["equal"]]
        problems.append(f"H-2 R-0A not passed: ran {result['ran']}, errors {result['errors']}, "
                        f"unequal {bad[:5]}, problems {result['problems'][:3]}")
    parts = prime_parts(lines, reference, stored)
    for grid, pairs in ((parts.grid, parts.grid_pairs), (parts.half, parts.half_pairs)):
        k_found, undecided = _paired_k_problems(grid, pairs)
        problems += [f"K-A {text}" for text in k_found] + undecided
    mech = mechanism(lines, reference, stored)
    if "rejected" in (mech["M-1"], mech["M-3"]):
        problems.append(f"H-11' M-1 {mech['M-1']} / M-3 {mech['M-3']}")
    return problems


def na_da_gate_problems(result: dict) -> list[str]:
    """Rev2 R2-4 / R2-6 gate before R-T / R-S: (ga)' ``pass``, no H-2 / H-4 / H-11' /
    H-13 stop and no H-12 ask (R-T / R-S lines themselves do not block)."""
    problems = []
    grid = result["grid"]
    if grid["status"] != STATUS_PASS:
        problems.append(f"(ga)' status {grid['status']}, not pass")
    problems += [text for text in result["stops"] if not text.startswith("H-5")]
    problems += result["asks"]
    return problems


# ------------------------------------------------------------------------------- report
def _full(value) -> str:
    return "None" if value is None else repr(value)


def _report_cells(prime: dict) -> list[str]:
    rec = prime["records"]
    lines = ["", "| setting | centre | R_c G-2 (j 0..3) | R_c G-2H (8 points) | "
             "R_c 16 points | M_c (j 0..3) | P_c |", "|---|---|---|---|---|---|---|"]
    for cell, union, union16 in zip(rec["G-2_cells"], rec["G-2H_union_cells"],
                                    rec["union16_cells"], strict=True):
        lines.append(f"| {cell['setting']} | {cell['centre']} | {_full(cell['R_c'])} | "
                     f"{_full(union['R_c'])} | {_full(union16['R_c'])} | "
                     f"{_full(cell['M_c'])} | {_full(cell['P_c'])} |")
    return lines


def _report_q(q: dict) -> list[str]:
    lines = ["", "### R-Q predictions (rev2 R2-3.1)", ""]
    if not q["complete"]:
        return lines + ["- not judged: R-Q incomplete"]
    for name in ("Q-1", "Q-2", "Q-3", "Q-4", "Q-5"):
        item = q[name]
        lines.append(f"- {name} {item['ok']}: "
                     f"{ {k: v for k, v in item.items() if k != 'ok'} }")
    return lines + [f"- missed {q['missed']}"]


def _report_grid(prime: dict, mech: dict) -> list[str]:
    lines = ["", f"## (ga)' {JUDGED_CANDIDATE}", "", f"- status {prime['status']}"]
    if prime["status"] == STATUS_INCOMPLETE:
        return lines + [f"- not run: {prime['not_run']}"]
    lines += [f"- G-1 {prime['G-1']}, G-1H {prime['G-1H']}, G-1Q {prime['G-1Q']}, G-2' "
              f"{prime[G2P_KEY]}, G-3 {prime['G-3']}, G-4 {prime['G-4']}",
              f"- min F_RL {_full(prime['min_F_RL_kN'])} kN, min F_judged "
              f"{_full(prime['min_F_judged_kN'])} kN (G-2' floor {G2P_FLOOR_KN!r} kN)",
              f"- G-2' failures {prime[G2P_FAIL_KEY]}",
              f"- G-1 / G-1H / G-1Q failures {prime['G-1_fail']} {prime['G-1H_fail']} "
              f"{prime['G-1Q_fail']}",
              f"- G-3 {prime['G-3_problems'][:10]}", f"- G-4 {prime['G-4_problems'][:10]}",
              f"- undecidable {prime['undecidable'][:10]}",
              f"- between 10.400 and 10.414589 kN: {prime['between_thresholds']}"]
    lines += _report_cells(prime)
    lines += ["", f"- M-1 {mech['M-1']} (median Delta F {_full(mech['M-1_median_kN'])} kN over "
                  f"{mech['pairs']} pairs), M-2 {mech['M-2']} (max R_c "
                  f"{_full(mech['M-2_max_R_c_kN'])} kN, P5 {_full(mech['M-2_P5_max_R_c_kN'])}), "
                  f"M-3 {mech['M-3']} ({mech['M-3_rises']}/6 rise)"]
    lines += _report_q(prime["records"]["Q"])
    lines += ["", "| part | point | F_RL | F_RL P5 | Delta F | F_judged | gap | trough | "
                  "cluster | lambda_0 | ramp | ramp end |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {row['part']} | {row['point']} | "
              f"{_full(row['F_RL_kN'])} | {_full(row['F_RL_P5_kN'])} | "
              f"{_full(row['delta_F_kN'])} | {_full(row['F_judged_min_kN'])} | "
              f"{_full(row['gap_s'])} | {row['trough']} | {row['cluster']} | "
              f"{_full(row['lambda_0'])} | {row['ramp_periods']} | {row['ramp_end_reason']} |"
              for row in prime["records"]["rows"]]
    return lines


def _report_bits(result: dict) -> list[str]:
    lines = ["## R-0", "", "| key | label | expected | got | equal |", "|---|---|---|---|---|"]
    r0 = result["R-0"]
    lines += [f"| {row['key']} | {row['label']} | {row['expected']} | {row['got']} | "
              f"{row['equal']} |" for row in r0["rows"]]
    lines += [f"- ran {r0['ran']}, errors {r0['errors']}, problems {r0['problems']}, "
              f"pass {r0['pass']}"]
    for name in ("R-0P5", "R-0A"):
        block = result[name]
        lines += ["", f"## {name}", "", "| point | expected | got | equal |", "|---|---|---|---|"]
        lines += [f"| {row['point']} | {row['expected']} | {row['got']} | {row['equal']} |"
                  for row in block["rows"]]
        lines += [f"- ran {block['ran']}, errors {block['errors']}, duplicates "
                  f"{block['duplicates']}, problems {block['problems'][:5]}, pass {block['pass']}"]
    return lines


def report_markdown(result: dict, sources: list[Path], reference_paths: list[Path]) -> str:
    lines = ["# LAS-b revision A addendum rev2: judgement (las_revA_judge.py)", "",
             f"- rules sha256: {dict(zip(RULES_FIELDS, RULES_VALUES, strict=True))}",
             f"- references {[str(path) for path in reference_paths]} (expected raw sha256 "
             f"{REFERENCE_RG_SHA256}, {STORED_REVA_RG_SHA256}, {STORED_REVA_RH_SHA256})",
             f"- inputs: {', '.join(str(path) for path in sources)}", ""]
    lines += _report_bits(result)
    lines += _report_grid(result["grid"], result["mechanism"])
    for label, item in (("(na) R-T", result["R-T"]), ("(da) R-S", result["R-S"])):
        if item is None:
            continue
        lines += ["", f"## {label} {JUDGED_CANDIDATE}", "", f"- checks {item['checks']}",
                  f"- complete {item['complete']}, missing {len(item['missing'])}, "
                  f"undecidable {item['undecidable'][:5]}, errors {item['errors']}",
                  f"- C-2 violating pairs {len(item['C-2_violations'])}: "
                  f"{dict(list(item['C-2_violations'].items())[:5])}"]
    rp0 = result["R-P0"]
    lines += ["", "## R-P0", "", f"- needed {rp0['needed']}, reproduced {rp0['reproduced']}, "
              f"missing {rp0['missing'][:10]}, H-5 {rp0['H-5'][:5]}", "", "## Verdict", "",
              f"- candidates {result['candidates']}",
              f"- K-A on R-T / R-S {result['pair_k_problems'][:10]}",
              f"- identity {result['identity']}", f"- stops {result['stops']}",
              f"- asks {result['asks']}", ""]
    return "\n".join(lines)


def default_inputs(directory: Path = REVA2_DIR) -> list[Path]:
    return sorted(directory.glob("revA_R*.jsonl"))


def _json_key(value):
    return value.item() if hasattr(value, "item") else str(value)


@dataclass
class References:
    """The three stored reference files and their H-10 problems."""

    reference: dict | None
    stored_reva: StoredRevA | None
    issues: list[str]


def load_references(rg_path: Path, reva_rg_path: Path, reva_rh_path: Path) -> References:
    """H-10 checks and the loaded references (None where a check failed).

    Raises:
        OSError, ValueError: A file that passed its sha256 check cannot be read as expected.
    """
    rg_issues = reference_problems(rg_path)
    reva_issues = stored_reva_problems(reva_rg_path, reva_rh_path)
    reference = None if rg_issues else load_reference(rg_path)
    stored_reva = None if reva_issues else load_stored_reva(reva_rg_path, reva_rh_path)
    return References(reference, stored_reva, rg_issues + reva_issues)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--ref-rg", type=Path, default=DEFAULT_REFERENCE_RG,
                        help="stored rev_RG.jsonl (main checkout; not in git)")
    parser.add_argument("--ref-reva-rg", type=Path, default=DEFAULT_STORED_REVA_RG,
                        help="stored revA_RG.jsonl (main checkout; not in git)")
    parser.add_argument("--ref-reva-rh", type=Path, default=DEFAULT_STORED_REVA_RH,
                        help="stored revA_RH.jsonl (main checkout; not in git)")
    parser.add_argument("--out", type=Path, default=None, help="new Markdown file")
    parser.add_argument("--json-out", type=Path, default=None, help="new JSON file, all digits")
    args = parser.parse_args(argv)
    problems = sealed_rules_problems()
    if problems:
        print(f"input error (H-1): {problems}")
        print(json.dumps({"stop": "H-1", "reasons": problems}))
        return 2
    for path in (args.out, args.json_out):
        if path is not None and path.exists():
            print(f"input error: {path} exists (new files only)")
            return 2
    sources = args.files or default_inputs()
    try:
        lines = [line for path in sources for line in read_lines(path)]
        stored = rj.load_stored()
        refs = load_references(args.ref_rg, args.ref_reva_rg, args.ref_reva_rh)
    except (OSError, ValueError) as exc:
        print(f"input error: {exc!r}")
        return 2
    result = judge(lines, stored, refs.reference, refs.stored_reva, refs.issues)
    report = report_markdown(result, sources, [args.ref_rg, args.ref_reva_rg, args.ref_reva_rh])
    print(report)
    if args.out is not None:
        with args.out.open("x", encoding="utf-8") as handle:
            handle.write(report)
    if args.json_out is not None:
        with args.json_out.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, default=_json_key, indent=1)
    print(json.dumps({"candidates": result["candidates"], "R-0": result["R-0"]["pass"],
                      "R-0P5": result["R-0P5"]["pass"], "R-0A": result["R-0A"]["pass"],
                      "stops": result["stops"], "asks": result["asks"]}))
    return 1 if is_stop_result(result) else 0


if __name__ == "__main__":
    sys.exit(main())
