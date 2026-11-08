"""Judge of the LAS-b revision A targets (P5r4 / P5r6: beta 4.5 + end ramp, sealed rules).

Rules: ``06_analysis/02_control/verif_matrix/las_revA_targeted_rules.md`` (control-expert,
sealed; LF sha256 :data:`RULES_REVA_SHA256`) on top of the original rules and rev1 of
``las_rev_targeted_rules`` (both checked, :data:`SEALED_RULES`). The rules text wins where this
code differs. Like ``las_rev_judge`` (whose pair checks it reuses) this module reads only JSON
lines, so ``las_revA_targeted.py`` uses its checks during a batch and a re-count script can read
the same files on its own.

Inputs: the ``revA_R*.jsonl`` files of ``las_revA_targeted.py`` (``rev`` block per line), the
stored L lines of ``las_rev_judge.load_stored`` for R-T / R-S, and the P5 reference
``v5/las/rev/rev_RG.jsonl`` (raw sha256 :data:`REFERENCE_RG_SHA256`, H-10; it is not in git:
pass its path with ``--ref-rg``).

What it checks (rules section in brackets):
  R-0 [7.1]        six P0 hashes against the stored 64-character values (H-2).
  R-0P5 [7.2]      30 P5 lines (N_r 0 given explicitly): hash and ``diag.summary.F_RL_kN``
                   equal to the reference P5 line of the grid point (H-2).
  K-A1 .. K-A8 [2.1] implementation predictions of every R-G / R-H candidate line against its
                   P5 pair (reference for R-G, the R-H P5 line for R-H); K-A7 / K-A8 also on R-T /
                   R-S lines against L. A mismatch is ``stop`` (H-3).
  (ga) [5.1]       G-1 / G-1H F_RL and F_judged >= 10.400 kN, G-2 R_c (j 0..3) and G-2H R_c over
                   the union j 0, 0.5, .., 3.5 <= 0.500 kN per cell, G-3 exclusion check (R-G 30
                   and R-H 24 lines), G-4 = K-A1 .. K-A6, K-A8.
  M-1 .. M-3 [2.2] mechanism checks (record only; H-11 when both candidates reject M-1 or M-3).
  (na) / (da) [5.2, 5.3] ``las_rev_judge.judge_t`` / ``judge_s`` with the rules 6 exception
                   that counts restarts after the end ramp (``las.ramp.end_t_s``).
  R-P0 [7.4]       ``las_rev_judge.judge_rp0``.
  Status [5.4]     stop > undecidable > fail > pass; a candidate without R-G or R-H lines is
                   ``incomplete`` (``not_run``, exit 1, not counted by H-6); H-6 counts only
                   (ga) ``fail``.
R_c, R_c union, M_c, P_c and Delta F are written with all digits (``--json-out`` and the
Markdown table use ``repr``).

Usage (python-dev, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/las_revA_judge.py [files ...]
      [--ref-rg <rev_RG.jsonl>] [--out <md>] [--json-out <json>]
      (no files: every ``revA_R*.jsonl`` in ``v5/las/revA/``)
Exit codes: 0 judged, 1 a stop condition (H-2 .. H-6, H-10, H-11), an undecidable / stop / ask
candidate or a candidate not run, 2 input error.
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
REVA_DIR = rj.V5_DIR / "las" / "revA"
RULES_REVA_PATH = rj.RULES_PATH.with_name("las_revA_targeted_rules.md")
RULES_REVA_SHA_PATH = RULES_REVA_PATH.with_suffix(".sha256")
RULES_REVA_SHA256 = "b09d004bb2f641db40cdd139a6fb2b1645651e4a3e45a9b16e81a5c938d5778f"
"""``las_revA_targeted_rules.sha256`` (LF digest, sealed 2026-11-09 00:45:52 +09:00)."""
SEALED_RULES = (*rj.SEALED_RULES, (RULES_REVA_PATH, RULES_REVA_SHA_PATH, RULES_REVA_SHA256))
REFERENCE_RG_SHA256 = "7e8c3b4173f1fc682e665ad173589dbbe335ba914a06d5ef2984c5807bb8cca6"
"""Raw sha256 of the stored R-G lines of the original rules (rules 0 / 3.1, H-10)."""
DEFAULT_REFERENCE_RG = rj.REV_DIR / "rev_RG.jsonl"
REFERENCE_CANDIDATE = "P5"

# Rules 1.2: (beta, n_min, N_r).
CANDIDATE_VALUES = {"P0": (3.5, 0, 0), "P5": (4.5, 0, 0), "P5r4": (4.5, 0, 4),
                    "P5r6": (4.5, 0, 6)}
JUDGED_CANDIDATES = ("P5r4", "P5r6")
"""Rules 1.2 / 9.4 order (P5r4 before P5r6)."""
HALF_CANDIDATES = (REFERENCE_CANDIDATE, *JUDGED_CANDIDATES)
BUNDLES = ("R-0", "R-0P5", "R-G", "R-H", "R-T", "R-S", "R-P0", "R-X")
GRID_BUNDLES = ("R-0P5", "R-G", "R-H")

GRID_SETTINGS = rj.GRID_SETTINGS
GRID_CENTRES = rj.GRID_CENTRES
GRID_STEPS = rj.GRID_STEPS
RANGE_STEPS = rj.RANGE_STEPS
HALF_STEPS = (0.5, 1.5, 2.5, 3.5)
UNION_STEPS = tuple(sorted((*RANGE_STEPS, *HALF_STEPS)))
GRID_LINES = len(GRID_SETTINGS) * len(GRID_CENTRES) * len(GRID_STEPS)
HALF_LINES = len(GRID_SETTINGS) * len(GRID_CENTRES) * len(HALF_STEPS)

GRID_FORCE_FLOOR_KN = rj.GRID_FORCE_FLOOR_KN
GRID_RANGE_LIMIT_KN = rj.GRID_RANGE_LIMIT_KN
TOLERANCE = rj.TIME_TOLERANCE_S
OUTPUT_DELAY_S = 0.1
"""Rules 0: d = 1, the command of period k reaches the plant at t_k + 0.1 s (K-A4)."""
LAMBDA0_TOLERANCE = 1e-4
"""K-A5: the recorded ``start_factor`` against mean(out) / mean(in) of the P5 pair's last acted
period (the diag commands are rounded to 1e-4 mm/s)."""
RAMP_END_REASONS = ("done", "loc", "phase", "soil", "reapproach", "zone")
QUIET_ENDS = ("sum", "time")
KA1_FIELDS = ("start_t_s", "end_t_s", "end_reason", "active_periods", "scaled_periods",
              "start_leg")
M2_P5_MAX_RANGE_KN = 1.105
M3_BRANCH_A = (("V0", "0.94", 1), ("V0", "0.94", 3), ("V0", "1", 0), ("V0", "1", 2),
               ("V0", "1", 4), ("V0", "nom", 3))
"""Rules 2.2 M-3 as written (their P5 values: 10.771, 10.650, 10.740, 10.764, 10.728, 11.314
kN; the stored V0 nom j3 P5 value is 11.418 kN, 11.314 is VB nom j3 -- reported, not changed)."""
M3_CONFIRM_COUNT = 4
RANK_FORCE_TIE_KN = rj.RANK_FORCE_TIE_KN

STATUS_STOP = "stop"
STATUS_UNDECIDABLE = "undecidable"
STATUS_FAIL = "fail"
STATUS_PASS = "pass"
STATUS_INCOMPLETE = "incomplete"
IDENTITY_GROUPS = {"P5r4": ("R-G", "R-H", "R-T", "R-S"), "P5r6": ("R-G", "R-H", "R-T", "R-S"),
                   "P5": ("R-H",), "P0": ("R-P0", "R-X")}
"""Rules 4: the lines of one candidate come from one commit (R-0 / R-0P5 are bit tests)."""


# ------------------------------------------------------------------------------- reading
def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed_rules_problems(sealed=SEALED_RULES) -> list[str]:
    """H-1 over the original rules, rev1 and the revA rules."""
    return rj.sealed_rules_problems(sealed)


def reference_problems(path: Path, expected: str = REFERENCE_RG_SHA256) -> list[str]:
    """H-10: the P5 reference file is there with its stored raw sha256."""
    if not path.exists():
        return [f"H-10 missing reference {path}"]
    digest = raw_sha256(path)
    if digest != expected:
        return [f"H-10 {path.name} sha256 {digest} != {expected}"]
    return []


def grid_point_of(line: dict) -> tuple[str, str, int | float] | None:
    """(setting, centre, j) of a grid line; ``j`` keeps its type (R-H half steps are floats)."""
    point = rj.rev_of(line).get("grid_point")
    if point is None:
        return None
    return need(line, "job", "setting"), str(point[0]), point[1]


def load_reference(path: Path) -> dict[tuple, dict]:
    """``{(setting, centre, j): P5 line}`` of the reference file (30 points).

    Raises:
        ValueError: Not 30 distinct P5 grid points.
    """
    out = {}
    for line in read_lines(path):
        rev = rj.rev_of(line)
        if rev.get("candidate") != REFERENCE_CANDIDATE or rj.is_error(line):
            continue
        out[grid_point_of(line)] = line
    if len(out) != GRID_LINES:
        raise ValueError(f"{path.name}: {len(out)} P5 grid points, expected {GRID_LINES}")
    return out


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


def lambda0_of(p5_line: dict) -> tuple[bool, float | None]:
    """(lambda_0 < 1, mean(out) / mean(in)) of the P5 pair's last acted period.

    Raises:
        MissingField: The pair started and ended but no acted period is recorded.
    """
    acted = _acted_periods(p5_line)
    if not acted:
        raise MissingField("diag.periods[].las of the last acted period")
    last = acted[-1]
    if not last.get("is_scaled"):
        return False, 1.0
    inputs, outputs = last["input_mm_s"], last["output_mm_s"]
    return True, (sum(outputs) / len(outputs)) / (sum(inputs) / len(inputs))


# ------------------------------------------------------------------------------- K-A checks
def settings_problems(line: dict) -> list[str]:
    """K-A8: the controller's own settings are the candidate's (beta, n_min, N_r)."""
    rev = rj.rev_of(line)
    candidate = need(rev, "candidate")
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


def _ka5_ka6(cand: dict, pair: dict, n_r: int) -> list[str]:
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
    is_scaled, lambda0 = lambda0_of(pair)
    if not is_scaled:
        if applied != 0:
            problems.append(f"K-A6 lambda_0 = 1 with {applied} ramp periods")
        return problems
    if cand["commands_sha256"] == pair["commands_sha256"]:
        problems.append("K-A5 commands hash equals P5 although the ramp acts")
    start = need(ramp, "start_factor")
    if start is None or abs(start - lambda0) > LAMBDA0_TOLERANCE:
        problems.append(f"K-A5 start_factor {start!r} != lambda_0 {lambda0!r}")
    if need(ramp, "end_reason") not in RAMP_END_REASONS:
        problems.append(f"K-A5 ramp end_reason {ramp.get('end_reason')!r}")
    limit_ok = applied == n_r if ramp.get("end_reason") == "done" else applied <= n_r
    if not limit_ok:
        problems.append(f"K-A5 {applied} ramp periods with end {ramp.get('end_reason')}")
    return problems


def grid_k_problems(cand: dict, pair: dict, bundle: str) -> list[str]:
    """K-A1 .. K-A8 of one R-G / R-H candidate line against its P5 pair (rules 2.1).

    Raises:
        MissingField: A field the checks read is not in either line.
    """
    n_r = CANDIDATE_VALUES[need(cand, "rev", "candidate")][2]
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
    if bundle == "R-G" and lift != pair_lift:
        problems.append(f"K-A3 t_lift_s {lift} != P5 {pair_lift}")
    return problems + _ka5_ka6(cand, pair, n_r)


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


def judge_r0p5(lines: list[dict], reference: dict | None) -> dict:
    """Rules 7.2: 30 P5 lines (N_r 0) with the reference hash and ``F_RL_kN``, bit for bit."""
    found, problems, errors = {}, [], 0
    for line in lines:
        rev = rj.rev_of(line)
        if rev.get("bundle") != "R-0P5":
            continue
        if rj.is_error(line):
            errors += 1
            continue
        found[grid_point_of(line)] = line
        problems += [f"{rev['key']}: {text}" for text in tag_problems(line)]
        try:
            problems += [f"{rev['label']}: {text}" for text in settings_problems(line)]
        except MissingField as exc:
            problems.append(f"{rev.get('label')}: missing {exc}")
    rows = []
    for point in sorted((reference or {}), key=str):
        ref, line = reference[point], found.get(point)
        got_sha = None if line is None else line["commands_sha256"]
        got_f = None if line is None else ((line.get("diag") or {}).get("summary") or {}).get(
            "F_RL_kN")
        ref_f = ref["diag"]["summary"]["F_RL_kN"]
        rows.append({"point": list(point), "expected": ref["commands_sha256"], "got": got_sha,
                     "F_RL_ref_kN": ref_f, "F_RL_kN": got_f,
                     "equal": got_sha == ref["commands_sha256"] and got_f == ref_f})
    is_pass = (reference is not None and errors == 0 and not problems and len(found) == GRID_LINES
               and all(row["equal"] for row in rows))
    return {"rows": rows, "errors": errors, "ran": len(found), "problems": problems,
            "reference": reference is not None, "pass": is_pass}


# ------------------------------------------------------------------------------- (ga)
@dataclass
class GridLines:
    """One candidate's lines of one grid bundle."""

    candidate: str
    bundle: str
    lines: dict[tuple, dict] = field(default_factory=dict)
    errors: int = 0
    duplicates: list = field(default_factory=list)


def grid_lines_of(lines: list[dict], bundle: str, candidate: str) -> GridLines:
    out = GridLines(candidate, bundle)
    for line in lines:
        rev = rj.rev_of(line)
        if rev.get("bundle") != bundle or rev.get("candidate") != candidate:
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
        problems.append(f"{grid.bundle}: lines {len(grid.lines)}/{len(expected)}, errors "
                        f"{grid.errors}, duplicates {grid.duplicates}, missing "
                        f"{sorted(expected - set(grid.lines), key=str)}")
    for point, line in grid.lines.items():
        try:
            budget = need(line, "diag", "touch_budget", "level_budget_periods")
            consistent = need(line, "diag", "summary", "gate_consistent")
        except MissingField as exc:
            problems.append(f"{grid.bundle} {point}: missing {exc}")
            continue
        if budget != 0 or consistent is not True:
            problems.append(f"{grid.bundle} {point}: level_budget_periods {budget}, "
                            f"gate_consistent {consistent}")
    return problems


def _forces(line: dict) -> tuple:
    summary = need(line, "diag", "summary")
    return need(summary, "F_RL_kN"), need(summary, "F_judged_min_kN")


def force_failures(grid: GridLines) -> tuple[list[str], list[str]]:
    """(G-1 / G-1H failures, values between 10.400 and 10.4146 kN)."""
    failures, between = [], []
    for point in sorted(grid.lines, key=str):
        try:
            f_rl, f_judged = _forces(grid.lines[point])
        except MissingField:
            continue  # counted by G-3
        if f_rl is None or f_judged is None or min(f_rl, f_judged) < GRID_FORCE_FLOOR_KN:
            failures.append(f"{point}: F_RL {f_rl!r} F_judged {f_judged!r}")
        for value in (f_rl, f_judged):
            if value is not None and GRID_FORCE_FLOOR_KN <= value < rj.C1_FORCE_FLOOR_N / 1e3:
                between.append(f"{point}: {value!r} kN")
    return failures, between


def _f_rl(line: dict | None):
    if line is None:
        return None
    return ((line.get("diag") or {}).get("summary") or {}).get("F_RL_kN")


def range_cells(by_point: dict[tuple, dict], steps, all_steps=GRID_STEPS) -> list[dict]:
    """Per (setting, centre): R_c = max - min of F_RL over ``steps``, M_c their mean and
    P_c = |F(4) - F(0)| (when both are there)."""
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


def _k_problems_of(grid: GridLines, pairs: dict[tuple, dict] | None) -> tuple[list, list]:
    """(K-A problems, undecidable problems) of every line of a grid bundle."""
    k_found, undecidable = [], []
    for point in sorted(grid.lines, key=str):
        pair = None if pairs is None else pairs.get(point)
        if pair is None:
            undecidable.append(f"{grid.bundle} {point}: no P5 pair line")
            continue
        try:
            k_found += [f"{grid.bundle} {point}: {text}"
                        for text in grid_k_problems(grid.lines[point], pair, grid.bundle)]
        except MissingField as exc:
            undecidable.append(f"{grid.bundle} {point}: missing {exc}")
    return k_found, undecidable


def judge_grid(candidate: str, lines: list[dict], reference: dict | None) -> dict:
    """(ga) of one candidate: G-1, G-2, G-1H, G-2H, G-3, G-4 and the status (rules 5.1)."""
    grid = grid_lines_of(lines, "R-G", candidate)
    half = grid_lines_of(lines, "R-H", candidate)
    half_p5 = grid_lines_of(lines, "R-H", REFERENCE_CANDIDATE)
    out = {"candidate": candidate, "R-G_lines": len(grid.lines), "R-H_lines": len(half.lines)}
    if not (grid.lines or grid.errors) or not (half.lines or half.errors):
        missing = [name for name, item in (("R-G", grid), ("R-H", half))
                   if not (item.lines or item.errors)]
        return {**out, "status": STATUS_INCOMPLETE, "not_run": missing, "pass": False}
    g3 = exclusion_problems(grid, GRID_STEPS) + exclusion_problems(half, HALF_STEPS)
    g3 += [f"P5 reference {text}" for text in exclusion_problems(half_p5, HALF_STEPS)]
    k_grid, undecided_grid = _k_problems_of(grid, reference)
    k_half, undecided_half = _k_problems_of(half, half_p5.lines)
    g1, between = force_failures(grid)
    g1h, between_h = force_failures(half)
    cells = range_cells(grid.lines, RANGE_STEPS)
    union = range_cells({**grid.lines, **half.lines}, UNION_STEPS, UNION_STEPS)
    g2 = [cell for cell in cells if not cell["ok"]]
    g2h = [cell for cell in union if not cell["ok"]]
    undecidable = g3 + undecided_grid + undecided_half
    if reference is None:
        undecidable.append("H-10 no reference P5 lines for R-G")
    status = grid_status(bool(k_grid or k_half), bool(undecidable),
                         bool(g1 or g1h or g2 or g2h))
    forces = []
    for item in (grid, half):
        for line in item.lines.values():
            value = ((line.get("diag") or {}).get("summary") or {}).get("F_judged_min_kN")
            if value is not None:
                forces.append(value)
    return {**out, "G-1": not g1, "G-1_fail": g1, "G-1H": not g1h, "G-1H_fail": g1h,
            "G-2": not g2, "G-2H": not g2h, "cells": cells, "union_cells": union,
            "G-3": not g3, "G-3_problems": g3, "G-4": not (k_grid or k_half),
            "G-4_problems": k_grid + k_half, "undecidable": undecidable,
            "between_thresholds": between + between_h,
            "min_F_judged_kN": min(forces) if forces else None,
            "rows": grid_rows(grid, reference) + grid_rows(half, half_p5.lines),
            "status": status, "pass": status == STATUS_PASS}


def grid_rows(grid: GridLines, pairs: dict | None) -> list[dict]:
    """Record rows (rules 5.1 reference record) with Delta F against the P5 pair."""
    rows = []
    for point in sorted(grid.lines, key=str):
        line = grid.lines[point]
        las = line.get("las") or {}
        summary = (line.get("diag") or {}).get("summary") or {}
        pair = None if pairs is None else pairs.get(point)
        f_rl, f_pair = summary.get("F_RL_kN"), _f_rl(pair)
        ramp = las.get("ramp") or {}
        rows.append({"bundle": grid.bundle, "point": list(point), "F_RL_kN": f_rl,
                     "F_RL_P5_kN": f_pair,
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
                     "t_RL_min_s": summary.get("t_RL_min_s"),
                     "commands_sha256": line["commands_sha256"]})
    return rows


# ------------------------------------------------------------------------------- M-1 .. M-3
def mechanism(candidate: str, lines: list[dict], reference: dict | None) -> dict:
    """M-1 .. M-3 of one candidate (rules 2.2, hypotheses: record only)."""
    grid = grid_lines_of(lines, "R-G", candidate).lines
    half = grid_lines_of(lines, "R-H", candidate).lines
    half_p5 = grid_lines_of(lines, "R-H", REFERENCE_CANDIDATE).lines
    deltas = {}
    for points, pairs in ((grid, reference or {}), (half, half_p5)):
        for point, line in points.items():
            f_rl, f_pair = _f_rl(line), _f_rl(pairs.get(point))
            if f_rl is not None and f_pair is not None:
                deltas[point] = f_rl - f_pair
    is_complete = len(deltas) == GRID_LINES + HALF_LINES
    median = statistics.median(deltas.values()) if deltas else None
    cells = range_cells(grid, RANGE_STEPS)
    ranges = [cell["R_c"] for cell in cells]
    max_range = None if None in ranges or not ranges else max(ranges)
    p5_ranges = [cell["R_c"] for cell in range_cells(reference or {}, RANGE_STEPS)]
    branch = {point: deltas.get(point) for point in M3_BRANCH_A}
    known = [value for value in branch.values() if value is not None]
    rises = sum(value > 0 for value in known)
    m3 = None
    if len(known) == len(M3_BRANCH_A):
        m3 = ("confirmed" if rises >= M3_CONFIRM_COUNT
              else "rejected" if all(value < 0 for value in known) else "neither")
    return {"candidate": candidate, "pairs": len(deltas), "complete": is_complete,
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
def identity_problems(lines: list[dict]) -> dict[str, list[str]]:
    """H-4 (rules 4) per candidate: one commit, no code diff, allowed dirty files only, the
    three rules sha256 and the controller tag of the setting."""
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
            recorded = (rev.get("rules_sha256"), rev.get("rules_rev1_sha256"),
                        rev.get("rules_revA_sha256"))
            if recorded != (rj.RULES_SHA256, rj.RULES_REV1_SHA256, RULES_REVA_SHA256):
                problems.append(f"{key}: rules sha256 {recorded}")
            problems += [f"{key}: {text}" for text in tag_problems(line)]
        if len(heads) > 1:
            problems.append(f"{len(heads)} commits: {sorted(map(str, heads))}")
        if problems:
            out[candidate] = problems
    return out


# ------------------------------------------------------------------------------- verdict
def _pair_verdict(name: str, t_result: dict | None, s_result: dict | None, rp0: dict) -> dict:
    """(na) / (da) part of a candidate that passed (ga) (as ``las_rev_judge``)."""
    if t_result is None or s_result is None:
        return {"verdict": STATUS_INCOMPLETE, "at": "(na)/(da) not run"}
    failed = [f"{label} {check}" for label, result in (("(na)", t_result), ("(da)", s_result))
              for check, value in result["checks"].items() if value is False]
    if failed:
        return {"verdict": STATUS_FAIL, "at": failed}
    if not (t_result["complete"] and s_result["complete"]) or None in (
            t_result["checks"]["R-1"], t_result["checks"]["R-2"]):
        return {"verdict": STATUS_UNDECIDABLE, "at": "missing / empty population"}
    if t_result["exception_excess"]:
        return {"verdict": "ask", "at": "H-9 exception excess"}
    if not rp0["pass"]:
        return {"verdict": STATUS_INCOMPLETE, "at": "R-P0"}
    return {"verdict": "adopt_recommended", "at": None}


def candidate_verdict(name: str, out: dict) -> dict:
    """Rules 5.4 order: stop > undecidable > fail > pass; ``incomplete`` when not run."""
    grid = out["grid"][name]
    if grid["status"] == STATUS_INCOMPLETE:
        return {"verdict": STATUS_INCOMPLETE, "at": f"not_run: {grid['not_run']}",
                "not_run": True}
    stop_problems, missing = rj.split_k_problems(out["pair_k_problems"].get(name, []))
    if grid["status"] == STATUS_STOP or stop_problems:
        return {"verdict": STATUS_STOP, "at": "K-A mismatch (implementation defect candidate)"}
    undecidable = []
    for owner in (name, REFERENCE_CANDIDATE):
        if owner in out["identity"]:
            undecidable.append(f"H-4 run identity {owner}")
    if missing:
        undecidable.append("H-4 missing field")
    if grid["status"] == STATUS_UNDECIDABLE:
        undecidable.append("G-3 / pair / H-10")
    if undecidable:
        return {"verdict": STATUS_UNDECIDABLE, "at": undecidable}
    if grid["status"] == STATUS_FAIL:
        return {"verdict": STATUS_FAIL, "at": "(ga) G-1 / G-2 / G-1H / G-2H"}
    return _pair_verdict(name, out["R-T"].get(name), out["R-S"].get(name), out["R-P0"])


def rank(passing: list[str], out: dict) -> list[str]:
    """Rules 9: min F_judged of (ga) (0.3 kN tie), fewer changed pairs, smaller R-1 median,
    P5r4 before P5r6."""
    def changed(name):
        return (out["R-T"][name]["ready"]["changed"]
                + sum(pair["changed"] for pair in out["R-S"][name]["pairs"].values()))

    def median(name):
        value = out["R-T"][name]["ready"]["median_s"]
        return float("inf") if value is None else value

    remaining = sorted(passing, key=JUDGED_CANDIDATES.index)
    ordered = []
    while remaining:
        best = max(out["grid"][name]["min_F_judged_kN"] for name in remaining)
        tied = [name for name in remaining
                if best - out["grid"][name]["min_F_judged_kN"] <= RANK_FORCE_TIE_KN]
        tied.sort(key=lambda name: (changed(name), median(name), JUDGED_CANDIDATES.index(name)))
        ordered.append(tied[0])
        remaining.remove(tied[0])
    return ordered


def _has_candidate_lines(lines: list[dict]) -> bool:
    return any(rj.rev_of(line).get("bundle") not in ("R-0", "R-0P5") for line in lines)


def judge(lines: list[dict], stored: dict, reference: dict | None,
          reference_issues: list[str] | None = None) -> dict:
    """Every criterion of the revA rules over the given lines."""
    out = {"R-0": judge_r0(lines), "R-0P5": judge_r0p5(lines, reference), "grid": {},
           "mechanism": {}, "R-T": {}, "R-S": {}, "pair_k_problems": {},
           "stops": list(reference_issues or []), "asks": []}
    for name in JUDGED_CANDIDATES:
        out["grid"][name] = judge_grid(name, lines, reference)
        out["mechanism"][name] = mechanism(name, lines, reference)
        if rj._pair_lines(lines, "R-T", name)[0]:
            out["R-T"][name] = rj.judge_t(lines, stored, name, ramp_end_s)
        if rj._pair_lines(lines, "R-S", name)[0]:
            out["R-S"][name] = rj.judge_s(lines, stored, name, ramp_end_s)
        problems = pair_k_problems(lines, stored, name)
        if problems:
            out["pair_k_problems"][name] = problems
    out["R-P0"] = rj.judge_rp0(lines, stored)
    out["identity"] = identity_problems(lines)
    _add_stops(out, lines)
    out["candidates"] = {name: candidate_verdict(name, out) for name in JUDGED_CANDIDATES}
    passing = [name for name, verdict in out["candidates"].items()
               if verdict["verdict"] == "adopt_recommended"]
    out["ranking"] = rank(passing, out) if passing else []
    return out


def _add_stops(out: dict, lines: list[dict]) -> None:
    """H-2, H-4, H-5, H-6 and H-11 (an ask)."""
    stops = out["stops"]
    is_bit_ok = out["R-0"]["pass"] and out["R-0P5"]["pass"]
    if (out["R-0"]["ran"] or out["R-0P5"]["ran"] or _has_candidate_lines(lines)) and not (
            is_bit_ok):
        stops.append("H-2 R-0 / R-0P5 bit test not passed")
    for candidate, problems in out["identity"].items():
        stops.append(f"H-4 identity {candidate}: {problems[:3]}")
    if out["R-P0"]["H-5"]:
        stops.append(f"H-5 reproduction failed: {out['R-P0']['H-5'][:3]}")
    statuses = [out["grid"][name]["status"] for name in JUDGED_CANDIDATES]
    if all(status == STATUS_FAIL for status in statuses):
        stops.append("H-6 both candidates failed (ga)")
    rejected = [name for name in JUDGED_CANDIDATES
                if "rejected" in (out["mechanism"][name]["M-1"], out["mechanism"][name]["M-3"])]
    if len(rejected) == len(JUDGED_CANDIDATES):
        out["asks"].append("H-11 both candidates reject M-1 or M-3: no longer ramp without asking")


def is_stop_result(result: dict) -> bool:
    """Exit 1: a stop, an ask, or an undecidable / stop / ask / not-run candidate."""
    return bool(result["stops"] or result["asks"]) or any(
        verdict["verdict"] in (STATUS_UNDECIDABLE, STATUS_STOP, "ask") or verdict.get("not_run")
        for verdict in result["candidates"].values())


# ------------------------------------------------------------------------------- report
def _full(value) -> str:
    return "None" if value is None else repr(value)


def _report_grid(name: str, grid: dict, mech: dict) -> list[str]:
    lines = ["", f"## (ga) {name}", "", f"- status {grid['status']}"]
    if grid["status"] == STATUS_INCOMPLETE:
        return lines + [f"- not run: {grid['not_run']}"]
    lines += [f"- G-1 {grid['G-1']}, G-1H {grid['G-1H']}, G-2 {grid['G-2']}, G-2H "
              f"{grid['G-2H']}, G-3 {grid['G-3']}, G-4 {grid['G-4']}, min F_judged "
              f"{_full(grid['min_F_judged_kN'])} kN",
              f"- G-1 failures {grid['G-1_fail']}", f"- G-1H failures {grid['G-1H_fail']}",
              f"- G-3 {grid['G-3_problems'][:10]}", f"- G-4 {grid['G-4_problems'][:10]}",
              f"- undecidable {grid['undecidable'][:10]}",
              f"- between 10.400 and 10.414589 kN: {grid['between_thresholds']}", "",
              "| setting | centre | R_c (j 0..3) | R_c union (8 points) | M_c | P_c |",
              "|---|---|---|---|---|---|"]
    for cell, union in zip(grid["cells"], grid["union_cells"], strict=True):
        lines.append(f"| {cell['setting']} | {cell['centre']} | {_full(cell['R_c'])} | "
                     f"{_full(union['R_c'])} | {_full(cell['M_c'])} | {_full(cell['P_c'])} |")
    lines += ["", f"- M-1 {mech['M-1']} (median Delta F {_full(mech['M-1_median_kN'])} kN over "
                  f"{mech['pairs']} pairs), M-2 {mech['M-2']} (max R_c "
                  f"{_full(mech['M-2_max_R_c_kN'])} kN, P5 {_full(mech['M-2_P5_max_R_c_kN'])}), "
                  f"M-3 {mech['M-3']} ({mech['M-3_rises']}/6 rise)", "",
              "| bundle | point | F_RL | F_RL P5 | Delta F | F_judged | end | lambda_0 | ramp | "
              "ramp end |", "|---|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {row['bundle']} | {row['point']} | {_full(row['F_RL_kN'])} | "
              f"{_full(row['F_RL_P5_kN'])} | {_full(row['delta_F_kN'])} | "
              f"{_full(row['F_judged_min_kN'])} | {row['end_reason']} | "
              f"{_full(row['lambda_0'])} | {row['ramp_periods']} | {row['ramp_end_reason']} |"
              for row in grid["rows"]]
    return lines


def report_markdown(result: dict, sources: list[Path], reference_path: Path | None) -> str:
    lines = ["# LAS-b revision A targets: judgement (las_revA_judge.py)", "",
             f"- rules sha256 original {rj.RULES_SHA256}, rev1 {rj.RULES_REV1_SHA256}, "
             f"revA {RULES_REVA_SHA256}",
             f"- reference {reference_path} (expected raw sha256 {REFERENCE_RG_SHA256})",
             f"- inputs: {', '.join(str(path) for path in sources)}", "",
             "## R-0", "", "| key | label | expected | got | equal |", "|---|---|---|---|---|"]
    r0 = result["R-0"]
    lines += [f"| {row['key']} | {row['label']} | {row['expected']} | {row['got']} | "
              f"{row['equal']} |" for row in r0["rows"]]
    lines += [f"- ran {r0['ran']}, errors {r0['errors']}, problems {r0['problems']}, "
              f"pass {r0['pass']}", "", "## R-0P5", "",
              "| point | expected | got | F_RL ref | F_RL | equal |", "|---|---|---|---|---|---|"]
    r0p5 = result["R-0P5"]
    lines += [f"| {row['point']} | {row['expected'][:16]} | {(row['got'] or 'None')[:16]} | "
              f"{_full(row['F_RL_ref_kN'])} | {_full(row['F_RL_kN'])} | {row['equal']} |"
              for row in r0p5["rows"]]
    lines += [f"- ran {r0p5['ran']}, errors {r0p5['errors']}, problems {r0p5['problems']}, "
              f"pass {r0p5['pass']}"]
    for name in JUDGED_CANDIDATES:
        lines += _report_grid(name, result["grid"][name], result["mechanism"][name])
    for label, block in (("(na) R-T", result["R-T"]), ("(da) R-S", result["R-S"])):
        for name, item in block.items():
            lines += ["", f"## {label} {name}", "", f"- checks {item['checks']}",
                      f"- complete {item['complete']}, missing {len(item['missing'])}, "
                      f"undecidable {item['undecidable'][:5]}, errors {item['errors']}",
                      f"- C-2 violating pairs {len(item['C-2_violations'])}: "
                      f"{dict(list(item['C-2_violations'].items())[:5])}"]
    rp0 = result["R-P0"]
    lines += ["", "## R-P0", "", f"- needed {rp0['needed']}, reproduced {rp0['reproduced']}, "
              f"missing {rp0['missing'][:10]}, H-5 {rp0['H-5'][:5]}", "", "## Verdict", "",
              f"- candidates {result['candidates']}", f"- ranking {result['ranking']}",
              f"- K-A on R-T / R-S {result['pair_k_problems']}",
              f"- identity {result['identity']}", f"- stops {result['stops']}",
              f"- asks {result['asks']}", ""]
    return "\n".join(lines)


def default_inputs(directory: Path = REVA_DIR) -> list[Path]:
    return sorted(directory.glob("revA_R*.jsonl"))


def _json_key(value):
    return value.item() if hasattr(value, "item") else str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--ref-rg", type=Path, default=DEFAULT_REFERENCE_RG,
                        help="stored rev_RG.jsonl (main checkout; not in git)")
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
    reference_issues = reference_problems(args.ref_rg)
    try:
        lines = [line for path in sources for line in read_lines(path)]
        stored = rj.load_stored()
        reference = None if reference_issues else load_reference(args.ref_rg)
    except (OSError, ValueError) as exc:
        print(f"input error: {exc!r}")
        return 2
    result = judge(lines, stored, reference, reference_issues)
    report = report_markdown(result, sources, args.ref_rg)
    print(report)
    if args.out is not None:
        with args.out.open("x", encoding="utf-8") as handle:
            handle.write(report)
    if args.json_out is not None:
        with args.json_out.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, default=_json_key, indent=1)
    print(json.dumps({"candidates": result["candidates"], "ranking": result["ranking"],
                      "R-0": result["R-0"]["pass"], "R-0P5": result["R-0P5"]["pass"],
                      "stops": result["stops"], "asks": result["asks"]}))
    return 1 if is_stop_result(result) else 0


if __name__ == "__main__":
    sys.exit(main())
