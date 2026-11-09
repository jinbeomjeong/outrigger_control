"""S-2 soil-mode start deferral S2D: sealed values, bundle facts and the judge.

Rules: ``06_analysis/02_control/verif_matrix/s2_soil_defer_rules.md`` (control-expert, sealed;
LF sha256 :data:`RULES_S2D_SHA256`) on top of the LAS-b A-plan rules it inherits (six files,
``las_revA_diag.RULES_FIELDS``). The rules text wins where this code differs.

Lines (``s2_defer_targeted.py``): the ``run_v5`` line with the ``las`` / ``rev`` blocks of
``las_revA_targeted`` (A-S lines are revA2 lines: bundle R-0A / R-Q / R-T / R-S, candidate
P5r4) and an ``s2d`` block: bundle (S-0 / S-C / S-D / A-S / A-P0), candidate (``N0`` = N_d 0
given explicitly, ``P0`` = the preset with the S2D values in shadow, ``S2D``, ``P5r4S``),
the controller's deferral settings, the rules digests, the run identity, ``soil`` (soil-mode
start, LOC, the meta ``defer`` record, R4c30), ``trace`` (latch release time ``t_rel_s``,
the first S2D entry evaluation and the sha256 of the commands before it, the deferral
periods with latch state and smallest command) and ``load_trace`` (smallest true leg force
per control period from the first entry evaluation - 0.2 s for 2.7 s).

Judged here (rules 4 / 5 / 6 / 7):
  S-0   9 hashes = the stored ones (K-S0, SH-2).
  S-C   census: soil-mode keys, shadow entries, latch release and LOC in one period or
        1 .. N_d periods apart (per group), Q-S2.
  S     S-D pairs (S2D - P0 of S-C): SC-2, SC-F, SC-S, SC-R, SC-T (a) .. (d), K-S1 .. K-S5,
        Q-S3; SH-3 / SH-6 / SH-7 / SH-8.
  A     A-S: K-S1 (311 lines), Q-S1, Q-S4 and the A-plan rev2 judge (``las_revA_judge.judge``)
        over the stored revA2 R-0 / R-0P5 / R-P0 / R-X lines, the A-S lines and the A-P0
        lines (the P0 identity is judged per source: stored revA2 lines, new A-P0 lines).
Status order ``stop`` > ``undecidable`` > ``fail`` > ``pass``; nothing to judge ``incomplete``.

Usage (dynamics-dev or python-dev python.exe, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/s2_defer_judge.py judge [--dir <soil_defer>]
      [--d1 <d1.jsonl>] [--reva2-dir <revA2>] [--ref-rg ..] [--ref-reva-rg ..]
      [--ref-reva-rh ..] [--rules-root <checkout>] [--out <md>] [--json-out <json>]
Exit codes: 0 every judged part passed, 1 a stop / fail / undecidable / ask, 2 input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fb_targeted as fb  # noqa: E402  (sets the thread variables before numpy loads)
import las_rev_judge as rj  # noqa: E402
import las_revA_diag as diag  # noqa: E402
import las_revA_judge as ajudge  # noqa: E402
import numpy as np  # noqa: E402

ROOT = fb.ROOT
SOIL_DEFER_DIR = fb.V5_DIR / "soil_defer"
RULES_RELATIVE = Path("06_analysis") / "02_control" / "verif_matrix" / "s2_soil_defer_rules.md"
RULES_S2D_SHA256 = "838bd27761b74fdbe6cd5148929d7af0489f63568c2efcebebd57869b4b2ab20"
"""``s2_soil_defer_rules.sha256`` (LF digest, sealed 2026-11-09 10:32:31 +09:00)."""
RULES_FIELDS = ("rules_s2d_sha256", *diag.RULES_FIELDS)
RULES_VALUES = (RULES_S2D_SHA256, *diag.RULES_VALUES)
"""Every line records the S2D rules and the six A-plan rules digests (rules A.2)."""

BUNDLES = ("S-0", "S-C", "S-D", "A-S", "A-P0")
S2D_VALUES = {"mode_defer_periods": 5, "mode_defer_stroke_m": 0.006,
              "mode_defer_rise_factor": 4.0}
"""Rules 1.3 / 2."""
ZERO_VALUES = {"mode_defer_periods": 0, "mode_defer_stroke_m": 0.0,
               "mode_defer_rise_factor": 4.0}
SOIL_CANDIDATES = {
    "N0": {**ZERO_VALUES, "mode_defer_shadow": False},
    "P0": {**S2D_VALUES, "mode_defer_shadow": True},
    "S2D": {**S2D_VALUES, "mode_defer_shadow": False},
    "P5r4S": {**S2D_VALUES, "mode_defer_shadow": False},
}
"""``s2d.candidate`` -> the four ``SoilResponseSettings`` fields set with ``replace``. ``P0``
of S-C is the preset whose S2D values are evaluated in shadow only (commands as P0)."""
BUNDLE_SOIL_CANDIDATE = {"S-0": "N0", "S-C": "P0", "S-D": "S2D", "A-S": "P5r4S", "A-P0": "N0"}

# ------------------------------------------------------------------------------- stored facts
DIAGA_PATH = fb.V5_DIR / "las" / "diagA" / "diagA.jsonl"
DIAGA_SHA256 = "1590e79baa361a2e7c83726169b7781e9e134e5e3b1b23f07a641f592a62ed5d"
S0_EXPECTED = {
    **{("R-0", key, label): sha for (key, label), sha in rj.R0_EXPECTED.items()},
    ("D-A", diag.KEY, "P0"): "fae9b3900c9dc13dbe6fa3e9a8a38510da058f268af09684f8e51313ab35fe06",
    ("D-A", diag.KEY, "P5"): "dfbb8dd823ba6527442683b3e8cf56208ca51f7d0579ad8495fcb3b56c1f7132",
    ("D-A", diag.KEY, "P5r4"):
        "eeacc7830847ecf2d597446d235277c990643f909dac06f8538038f29d5bbb9d",
}
"""Rules 3 S-0: (origin bundle, key, label) -> stored hash (A-plan R-0 table, diagA lines)."""
D1_PATH = fb.V5_DIR / "d1.jsonl"
D1_SHA256 = "9039b36a1a9c4ba5ed63528bb7384773018d4c7377dccbf76b18fbcfda86707f"
SOIL_GROUP_COUNTS = {"H-S-0": 216, "H-S-1": 12, "H-S-A": 72, "H-S-A-J2": 4, "H-S-C": 120,
                     "H-S-C-g": 24, "H-R-A-J2": 4, "H-R-A-S1": 4}
SC_LINES = sum(SOIL_GROUP_COUNTS.values())
D1_SOIL_MODE_LINES = 305
"""Rules 0 / 3: soil-mode lines of the soil groups in ``d1.jsonl`` (LAS-less controller)."""
SD_SEED = 20261109
SD_RANDOM_KEYS = 40
A_S_COUNTS = {"R-0A": 54, "R-Q": 48, "R-T": 192, "R-S": 30}
A_S_LINES = sum(A_S_COUNTS.values())
REVA2_FILES = {"R-0": "revA_R0.jsonl", "R-0P5": "revA_R0P5.jsonl", "R-0A": "revA_R0A.jsonl",
               "R-Q": "revA_RQ.jsonl", "R-T": "revA_RT.jsonl", "R-S": "revA_RS.jsonl",
               "R-P0": "revA_RP0.jsonl", "R-X": "revA_RX.jsonl"}
REVA2_SOIL_KEYS = 13
"""Rules 0 / Q-S4: revA2 R-S P5r4 lines with a soil-mode start."""

# ------------------------------------------------------------------------------- thresholds
PERIOD_S = 0.1
TIME_TOLERANCE_S = 1e-9
F_FLOOR_N = rj.C1_FORCE_FLOOR_N
STROKE_LIMIT_M = rj.STROKE_INCREASE_LIMIT_M
DELAY_LIMIT_S = 0.5
LOAD_DROP_LIMIT_N = 1000.0
LOAD_TAIL_S = 1.0
G6_ITEMS = ("G6-1_crawler", "G6-3_Fmin", "G6-7_preloc")
SH8_PAIRS = 5
Q_S2_FRACTION = 0.20
Q_S1_KEY = diag.KEY
Q_S1_LOC_S = 24.1
Q_S1_PERIODS = 3
Q_S1_STROKE_LIMIT_M = 0.438764 + 0.001
Q_S4_MAX_CHANGED = 4
EXPIRY_REASONS = ("periods", "stroke", "rise", "window")
LOC_REASON = "loc"
SOIL_MODE_EVENT = "soil_mode_start"
FLAT_SOIL_MARGIN_EVENT = diag.FLAT_SOIL_MARGIN_EVENT

STATUS_STOP, STATUS_UNDECIDABLE = "stop", "undecidable"
STATUS_FAIL, STATUS_PASS, STATUS_INCOMPLETE = "fail", "pass", "incomplete"
STATUS_ORDER = (STATUS_STOP, STATUS_UNDECIDABLE, STATUS_FAIL, STATUS_PASS)


# ------------------------------------------------------------------------------- seals
def rules_path(rules_root: Path = ROOT) -> Path:
    return rules_root / RULES_RELATIVE


def sealed_files(rules_root: Path = ROOT) -> tuple:
    """SH-1: the S2D rules (from ``rules_root``) and the six A-plan rules files."""
    path = rules_path(rules_root)
    return ((path, path.with_suffix(".sha256"), RULES_S2D_SHA256), *ajudge.SEALED_RULES,
            (diag.RULES_REVA_REV3_PATH, diag.RULES_REVA_REV3_SHA_PATH,
             diag.RULES_REVA_REV3_SHA256))


def seal_problems(rules_root: Path = ROOT) -> list[str]:
    return rj.sealed_rules_problems(sealed_files(rules_root))


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_problem(path: Path, expected: str) -> str | None:
    """A stored input file is there with its raw sha256."""
    if not path.exists():
        return f"missing {path}"
    digest = raw_sha256(path)
    return None if digest == expected else f"{path.name} sha256 {digest} != {expected}"


# ------------------------------------------------------------------------------- line facts
def s2d_of(line: dict) -> dict:
    """The ``s2d`` block; an error line from the pool keeps the entry inside ``rev``."""
    return line.get("s2d") or rj.rev_of(line).get("s2d") or {}


def key_of(line: dict) -> str | None:
    return rj.rev_of(line).get("key")


def lines_of(lines: list[dict], bundle: str) -> list[dict]:
    """Finished lines of an S2D bundle (error lines excluded)."""
    return [line for line in lines
            if s2d_of(line).get("bundle") == bundle and not rj.is_error(line)]


def error_count(lines: list[dict], bundle: str) -> int:
    return sum(1 for line in lines
               if rj.is_error(line) and s2d_of(line).get("bundle") == bundle)


def by_key(lines: list[dict]) -> dict[str, dict]:
    """The last line of each key (a re-run after an error line replaces nothing finished)."""
    return {key_of(line): line for line in lines}


def soil_block(line: dict) -> dict:
    return rj.need(line, "s2d", "soil")


def soil_start_s(line: dict) -> float | None:
    return soil_block(line)["t_S_s"]


def has_soil_mode(line: dict) -> bool:
    return soil_start_s(line) is not None


def deferral_of(line: dict) -> dict | None:
    return (soil_block(line).get("defer") or {}).get("deferral")


def shadow_of(line: dict) -> dict | None:
    return (soil_block(line).get("defer") or {}).get("shadow")


def entry_checks(line: dict) -> list[dict]:
    return (soil_block(line).get("defer") or {}).get("checks") or []


def is_expired(deferral: dict | None) -> bool:
    return deferral is not None and deferral.get("end_reason") in EXPIRY_REASONS


def settings_problems(line: dict) -> list[str]:
    """SH-4: the controller's deferral settings are the candidate's."""
    block = s2d_of(line)
    if block.get("settings_match") is not True:
        return [f"{key_of(line)}: deferral settings {block.get('settings')} != "
                f"{block.get('expected_settings')}"]
    return []


def rules_problems(line: dict) -> list[str]:
    block = s2d_of(line)
    recorded = tuple(block.get(name) for name in RULES_FIELDS)
    return [] if recorded == RULES_VALUES else [f"{key_of(line)}: rules digests {recorded}"]


def identity_problems(lines: list[dict]) -> list[str]:
    """SH-4: one commit, empty code diff, allowed dirty files only, the rules digests."""
    import las_rev_targeted as rev

    heads = {(s2d_of(line).get("identity") or {}).get("git_head") for line in lines}
    problems = [] if len(heads) <= 1 else [f"commits {sorted(map(str, heads))}"]
    for line in lines:
        identity = s2d_of(line).get("identity") or {}
        name = f"{s2d_of(line).get('bundle')} {key_of(line)}"
        if identity.get("code_diff_sha256") != fb.EMPTY_SHA256:
            problems.append(f"{name}: code diff not empty")
        dirty = [path for path in identity.get("dirty_files", []) if path not in rev.ALLOWED_DIRTY]
        if dirty:
            problems.append(f"{name}: dirty {dirty}")
        problems += rules_problems(line) + settings_problems(line)
    return problems


def worst_status(statuses) -> str:
    present = [status for status in statuses if status != STATUS_INCOMPLETE]
    if not present:
        return STATUS_INCOMPLETE
    return min(present, key=STATUS_ORDER.index)


# ------------------------------------------------------------------------------- S-0
def s0_expected_key(line: dict) -> tuple[str, str, str]:
    rev = rj.rev_of(line)
    return rev.get("bundle"), rev.get("key"), rev.get("label")


def judge_s0(lines: list[dict]) -> dict:
    """K-S0 / SH-2: the nine S-0 hashes are the stored ones."""
    found = {s0_expected_key(line): line["commands_sha256"] for line in lines_of(lines, "S-0")}
    rows = []
    for index, sha in S0_EXPECTED.items():
        got = found.get(index)
        bundle, key, label = index
        rows.append({"bundle": bundle, "key": key, "label": label, "expected": sha, "got": got,
                     "equal": got == sha})
    errors = error_count(lines, "S-0")
    ran = sum(1 for row in rows if row["got"] is not None)
    problems = identity_problems(lines_of(lines, "S-0"))
    problems += [text for line in lines_of(lines, "S-0") for text in ajudge.tag_problems(line)]
    is_pass = ran == len(S0_EXPECTED) and all(row["equal"] for row in rows) and not problems
    if not ran and not errors:
        status = STATUS_INCOMPLETE
    elif is_pass:
        status = STATUS_PASS
    else:
        status = STATUS_STOP
    return {"rows": rows, "ran": ran, "errors": errors, "problems": problems, "status": status}


# ------------------------------------------------------------------------------- S-C
def group_of(line: dict) -> str:
    return rj.need(line, "job", "d1", "group")


def release_loc_gap_periods(line: dict) -> int | None:
    """LOC time - latch release time in control periods (None without either)."""
    t_rel = rj.need(line, "s2d", "trace", "t_rel_s")
    t_loc = soil_block(line)["t_loc_s"]
    if t_rel is None or t_loc is None:
        return None
    return round((t_loc - t_rel) / PERIOD_S)


def sc_census(lines: list[dict]) -> dict:
    """Rules 7: per group the soil-mode keys, the shadow entries, the keys whose latch release
    and LOC fall in one period or 1 .. N_d periods apart; Q-S2 on the soil-mode keys."""
    sc_lines = lines_of(lines, "S-C")
    n_d = S2D_VALUES["mode_defer_periods"]
    groups: dict[str, dict] = {}
    for line in sc_lines:
        group = groups.setdefault(group_of(line), {
            "lines": 0, "soil_mode": 0, "shadow_entered": 0, "soil_mode_shadow_entered": 0,
            "same_period": 0, "within_n_d": 0})
        group["lines"] += 1
        entered = any(check.get("entered") for check in entry_checks(line))
        group["shadow_entered"] += entered
        if has_soil_mode(line):
            group["soil_mode"] += 1
            group["soil_mode_shadow_entered"] += entered
        gap = release_loc_gap_periods(line)
        group["same_period"] += gap == 0
        group["within_n_d"] += gap is not None and 1 <= gap <= n_d
    q_s2 = {}
    for name, group in groups.items():
        share = (group["soil_mode_shadow_entered"] / group["soil_mode"]
                 if group["soil_mode"] else None)
        q_s2[name] = {"share": share, "holds": share is None or share <= Q_S2_FRACTION + 1e-12}
    counts = {name: group["lines"] for name, group in groups.items()}
    return {"lines": len(sc_lines), "errors": error_count(lines, "S-C"), "groups": groups,
            "group_counts_match": counts == SOIL_GROUP_COUNTS,
            "soil_mode_lines": sum(group["soil_mode"] for group in groups.values()),
            "Q-S2": q_s2, "Q-S2_holds": all(value["holds"] for value in q_s2.values())}


def sd_selection(sc_lines: list[dict]) -> dict:
    """Rules 3 S-D: every S-C key with a soil-mode start, and 40 of the others drawn with
    ``default_rng(20261109).choice(n, 40, replace=False)`` over the sorted key names."""
    finished = by_key(lines_of(sc_lines, "S-C"))
    soil_keys = sorted(key for key, line in finished.items() if has_soil_mode(line))
    other_keys = sorted(key for key, line in finished.items() if not has_soil_mode(line))
    count = min(SD_RANDOM_KEYS, len(other_keys))
    picks = np.random.default_rng(SD_SEED).choice(len(other_keys), size=count, replace=False)
    random_keys = sorted(other_keys[int(index)] for index in picks)
    return {"soil_keys": soil_keys, "random_keys": random_keys,
            "keys": sorted(soil_keys + random_keys)}


# ------------------------------------------------------------------------------- K checks
def prefix_matches(cand: dict, base: dict) -> bool:
    """K-S3: the first entry evaluation is at the same time with the same command prefix."""
    cand_trace, base_trace = rj.need(cand, "s2d", "trace"), rj.need(base, "s2d", "trace")
    return (cand_trace.get("first_check_t_s") is not None
            and cand_trace.get("first_check_t_s") == base_trace.get("first_check_t_s")
            and cand_trace.get("prefix_sha256") == base_trace.get("prefix_sha256"))


def k_s4_problems(line: dict) -> list[str]:
    """K-S4: every deferral period has the latch held and no retracting command."""
    rows = rj.need(line, "s2d", "trace", "defer_rows")
    problems = []
    for row in rows:
        if not row["active"]:
            continue
        if not row["in_zone"]:
            problems.append(f"K-S4 {key_of(line)} t {row['t_s']}: latch released")
        if row["min_command_m_s"] < 0.0:
            problems.append(f"K-S4 {key_of(line)} t {row['t_s']}: command "
                            f"{row['min_command_m_s']} < 0")
    return problems


def k_s5_problems(line: dict) -> list[str]:
    """K-S5: an expired deferral's S-4 push base is the deferral-start mean stroke."""
    deferral = deferral_of(line)
    if not is_expired(deferral):
        return []
    base = soil_block(line).get("soil_mode_start_stroke_m")
    if base != deferral["start_stroke_m"]:
        return [f"K-S5 {key_of(line)}: push base {base} != deferral start "
                f"{deferral['start_stroke_m']}"]
    return []


def pair_k_problems(cand: dict, base: dict, is_random: bool) -> list[str]:
    """K-S1 (random keys), K-S2, K-S3, K-S4, K-S5 of one S-D pair (S2D, S-C P0)."""
    problems = k_s4_problems(cand) + k_s5_problems(cand)
    same = cand["commands_sha256"] == base["commands_sha256"]
    shadow_entered = any(check.get("entered") for check in entry_checks(base))
    key = key_of(cand)
    if is_random and not has_soil_mode(base) and not same:
        problems.append(f"K-S1 {key}: no soil mode in P0 but the hash changed")
    if has_soil_mode(base) and not shadow_entered and not same:
        problems.append(f"K-S2 {key}: shadow 'not entered' but the hash changed")
    if not same:
        if not shadow_entered:
            problems.append(f"K-S3 {key}: hash changed without a shadow entry")
        elif not prefix_matches(cand, base):
            problems.append(f"K-S3 {key}: commands differ before the entry period")
    return problems


# ------------------------------------------------------------------------------- SC criteria
def load_minimum_N(line: dict, t0_s: float, t1_s: float) -> float | None:
    """Smallest true leg force of the ``load_trace`` periods in [t0, t1]."""
    trace = rj.need(line, "s2d", "load_trace")
    if trace is None:
        return None
    values = [value for t_s, value in trace["rows"]
              if t0_s - TIME_TOLERANCE_S <= t_s <= t1_s + TIME_TOLERANCE_S]
    return min(values) if values else None


def sc_t_record(cand: dict, base: dict) -> dict:
    """SC-T (a) .. (d) of one expired pair."""
    deferral = deferral_of(cand)
    delay_s = soil_start_s(cand) - soil_start_s(base) if has_soil_mode(base) else None
    new_items = []
    cand_items, base_items = rj.need(cand, "d1", "items"), rj.need(base, "d1", "items")
    for name in G6_ITEMS:
        if base_items.get(name) is not False and cand_items.get(name) is False:
            new_items.append(name)
    t0_s, t1_s = deferral["start_s"], deferral["end_s"] + LOAD_TAIL_S
    cand_min = load_minimum_N(cand, t0_s, t1_s)
    base_min = load_minimum_N(base, t0_s, t1_s)
    checks = {
        "a": delay_s is not None and delay_s <= DELAY_LIMIT_S + TIME_TOLERANCE_S,
        "b": not k_s4_problems(cand),
        "c": not new_items,
        "d": None if cand_min is None or base_min is None
        else cand_min >= base_min - LOAD_DROP_LIMIT_N - TIME_TOLERANCE_S,
    }
    return {"key": key_of(cand), "reason": deferral["end_reason"], "delay_s": delay_s,
            "new_g6_failures": new_items, "min_load_S2D_N": cand_min, "min_load_P0_N": base_min,
            "window_s": [t0_s, t1_s], "checks": checks}


def sc_pair_record(cand: dict, base: dict) -> dict:
    """SC-2 / SC-F / SC-S facts and the READY delta of one S-D pair."""
    record = {"violations": rj.pair_violations(cand, base),
              "changed": cand["commands_sha256"] != base["commands_sha256"],
              "is_case": False, "ready_cand_s": rj.ready_time(cand),
              "ready_L_s": rj.ready_time(base),
              "F_cand_N": rj.need(cand, "d1", "F_judged_min_N"),
              "F_L_N": rj.need(base, "d1", "F_judged_min_N"),
              "stroke_increase_m": rj.stroke_increase_m(cand, base)}
    both = record["ready_cand_s"] is not None and record["ready_L_s"] is not None
    record["dt_s"] = record["ready_cand_s"] - record["ready_L_s"] if both else None
    f_base, f_cand = record["F_L_N"], record["F_cand_N"]
    record["SC-F_fail"] = (f_base is not None and f_base >= F_FLOOR_N
                           and (f_cand is None or f_cand < F_FLOOR_N))
    increase = record["stroke_increase_m"]
    record["SC-S_fail"] = increase is None or increase > STROKE_LIMIT_M + TIME_TOLERANCE_S
    return record


def sc_violation_count(pairs: dict) -> int:
    """SH-8: pairs with an SC-2, SC-F or SC-S violation."""
    return sum(1 for pair in pairs.values()
               if pair["violations"] or pair["SC-F_fail"] or pair["SC-S_fail"])


def judge_s(lines: list[dict]) -> dict:
    """Rules 5.1 on the S-D pairs (S2D line, S-C P0 line of the key)."""
    base_by_key = by_key(lines_of(lines, "S-C"))
    selection = sd_selection(lines)
    random_keys = set(selection["random_keys"])
    cand_by_key = by_key(lines_of(lines, "S-D"))
    out = {"selection": {name: len(value) for name, value in selection.items()},
           "errors": error_count(lines, "S-D"), "missing": sorted(set(selection["keys"])
                                                                    - set(cand_by_key)),
           "extra": sorted(set(cand_by_key) - set(selection["keys"])), "pairs": {},
           "undecidable": [], "k_problems": [], "sc_t": [], "loc_avoided": []}
    if not cand_by_key:
        return {**out, "status": STATUS_INCOMPLETE}
    for key in sorted(set(cand_by_key) & set(base_by_key)):
        cand, base = cand_by_key[key], base_by_key[key]
        try:
            out["k_problems"] += pair_k_problems(cand, base, key in random_keys)
            out["pairs"][key] = sc_pair_record(cand, base)
            deferral = deferral_of(cand)
            if is_expired(deferral):
                out["sc_t"].append(sc_t_record(cand, base))
            elif deferral is not None and deferral.get("end_reason") == LOC_REASON:
                out["loc_avoided"].append(key)
        except rj.MissingField as exc:
            out["undecidable"].append(f"{key}: missing {exc}")
    out["identity_problems"] = identity_problems(lines_of(lines, "S-D") + lines_of(lines, "S-C"))
    return _s_verdict(out)


def _s_verdict(out: dict) -> dict:
    pairs = out["pairs"]
    ready = rj.ready_population(pairs)
    c2 = {key: pair["violations"] for key, pair in pairs.items() if pair["violations"]}
    checks = {"SC-2": not c2,
              "SC-F": not [key for key, pair in pairs.items() if pair["SC-F_fail"]],
              "SC-S": not [key for key, pair in pairs.items() if pair["SC-S_fail"]],
              "SC-R": None if ready["R-1"] is None else bool(ready["R-1"] and ready["R-2"]),
              "SC-T": all(all(value is True for value in record["checks"].values())
                          for record in out["sc_t"]),
              "K": not out["k_problems"]}
    q_s3 = all(record["checks"]["a"] for record in out["sc_t"])
    out.update(ready=ready, c2_violations=c2, checks=checks, **{"Q-S3": q_s3},
               sh8_pairs=sc_violation_count(pairs))
    stops, asks = [], []
    if out["k_problems"]:
        stops.append(f"SH-3 K-S1 .. K-S5: {out['k_problems'][:5]}")
    if out["identity_problems"]:
        stops.append(f"SH-4 identity: {out['identity_problems'][:5]}")
    if not checks["SC-T"]:
        asks.append("SH-7 SC-T violation: S judgement short, do not go to A-S, ask")
    if out["sh8_pairs"] >= SH8_PAIRS:
        stops.append(f"SH-8 {out['sh8_pairs']} pairs with SC-2 / SC-F / SC-S violations")
    if not q_s3:
        asks.append("SH-6 Q-S3 missed: ask before A-S")
    out.update(stops=stops, asks=asks)
    if stops:
        status = STATUS_STOP
    elif out["undecidable"] or out["missing"] or out["errors"] or checks["SC-R"] is None:
        status = STATUS_UNDECIDABLE
    elif not all(value is True for value in checks.values()):
        status = STATUS_FAIL
    else:
        status = STATUS_PASS
    return {**out, "status": status}


# ------------------------------------------------------------------------------- A
def load_reva2(directory: Path) -> list[dict]:
    """Every line of the stored revA2 files (raises OSError / ValueError)."""
    lines = []
    for name in REVA2_FILES.values():
        lines += rj.read_lines(directory / name)
    return lines


def reva2_p5r4(reva2_lines: list[dict]) -> dict[tuple[str, str, str], dict]:
    """(bundle, label, key) -> stored revA2 P5r4 line."""
    return {(rj.rev_of(line)["bundle"], rj.rev_of(line)["label"], key_of(line)): line
            for line in reva2_lines
            if rj.rev_of(line).get("candidate") == ajudge.JUDGED_CANDIDATE
            and not rj.is_error(line)}


def has_soil_event(line: dict) -> bool:
    return bool((line.get("event_names") or {}).get(SOIL_MODE_EVENT))


def k_s1_targets(stored: dict) -> set[tuple[str, str, str]]:
    """K-S1 on A-S: every R-0A / R-Q / R-T line and the R-S keys without a revA2 soil mode."""
    return {index for index, line in stored.items()
            if index[0] in ("R-0A", "R-Q", "R-T") or (index[0] == "R-S"
                                                      and not has_soil_event(line))}


def judge_a_bits(as_lines: list[dict], stored: dict) -> dict:
    """K-S1 (311 lines), Q-S1 (boundary key), Q-S4 (changed among the 13 revA2 soil keys)."""
    targets = k_s1_targets(stored)
    seen, k_s1, changed_soil = set(), [], []
    q_s1 = None
    for line in as_lines:
        rev = rj.rev_of(line)
        index = (rev["bundle"], rev["label"], rev["key"])
        stored_line = stored.get(index)
        if stored_line is None:
            continue
        seen.add(index)
        same = line["commands_sha256"] == stored_line["commands_sha256"]
        if index in targets and not same:
            k_s1.append(f"K-S1 {index}: hash changed")
        if index[0] == "R-S" and has_soil_event(stored_line) and not same:
            changed_soil.append(index[2])
        if index[0] == "R-S" and index[2] == Q_S1_KEY:
            q_s1 = q_s1_record(line)
    return {"targets": len(targets), "seen_targets": len(targets & seen), "K-S1": k_s1,
            "Q-S1": q_s1, "Q-S4": {"changed_soil_keys": sorted(changed_soil),
                                   "holds": len(changed_soil) <= Q_S4_MAX_CHANGED}}


def q_s1_record(line: dict) -> dict:
    deferral = deferral_of(line) or {}
    soil = soil_block(line)
    r4c30 = bool(soil.get("r4c30"))
    stroke_m = rj.need(line, "d1", "stroke_max_m")
    parts = {"deferral_periods": deferral.get("periods") == Q_S1_PERIODS,
             "end_loc": deferral.get("end_reason") == LOC_REASON,
             "loc_time": soil.get("t_loc_s") is not None
             and abs(soil["t_loc_s"] - Q_S1_LOC_S) <= 1e-6,
             "no_soil_mode": soil.get("t_S_s") is None, "no_r4c30": not r4c30,
             "stroke": stroke_m is not None and stroke_m <= Q_S1_STROKE_LIMIT_M + TIME_TOLERANCE_S}
    return {"parts": parts, "holds": all(parts.values()), "deferral": deferral,
            "t_loc_s": soil.get("t_loc_s"), "stroke_max_m": stroke_m}


def _p0_identity_by_source(stored_p0: list[dict], new_p0: list[dict]) -> list[str]:
    """The P0 identity per source (rules 5.2: new A-P0 lines join the stored revA2 R-P0)."""
    problems = []
    for name, group in (("stored revA2", stored_p0), ("A-P0", new_p0)):
        result = ajudge.identity_problems(group).get("P0")
        if result:
            problems += [f"{name}: {text}" for text in result]
    return problems


def judge_a(lines: list[dict], reva2_lines: list[dict], stored: dict, reference: dict | None,
            stored_reva) -> dict:
    """Rules 5.2: K-S1, Q-S1, Q-S4 and the A-plan rev2 judge over P5r4S."""
    as_lines = lines_of(lines, "A-S")
    if not as_lines:
        return {"status": STATUS_INCOMPLETE}
    ap0_lines = lines_of(lines, "A-P0")
    stored_p5r4 = reva2_p5r4(reva2_lines)
    bits = judge_a_bits(as_lines, stored_p5r4)
    kept = [line for line in reva2_lines if rj.rev_of(line).get("bundle") in
            ("R-0", "R-0P5", "R-P0", "R-X")]
    result = ajudge.judge(kept + as_lines + ap0_lines, stored, reference, stored_reva)
    p0_lines = [line for line in kept if rj.rev_of(line).get("bundle") in ("R-P0", "R-X")]
    p0_problems = _p0_identity_by_source(p0_lines, ap0_lines)
    if not p0_problems and "P0" in result["identity"]:
        result["identity"].pop("P0")
        result["stops"] = [text for text in result["stops"]
                           if not text.startswith("H-4 identity P0")]
        result["candidates"] = {ajudge.JUDGED_CANDIDATE: ajudge.candidate_verdict(result)}
    verdict = result["candidates"][ajudge.JUDGED_CANDIDATE]["verdict"]
    s2d_problems = identity_problems(as_lines + ap0_lines)
    k_problems = bits["K-S1"] + [text for line in as_lines
                                 for text in k_s4_problems(line) + k_s5_problems(line)]
    asks = []
    if bits["Q-S1"] is None or not bits["Q-S1"]["holds"]:
        asks.append("SH-6 Q-S1 missed")
    if not bits["Q-S4"]["holds"]:
        asks.append("SH-6 Q-S4 missed")
    if k_problems or s2d_problems or result["stops"]:
        status = STATUS_STOP
    elif verdict in (STATUS_UNDECIDABLE, STATUS_INCOMPLETE):
        status = STATUS_UNDECIDABLE
    elif verdict == "adopt_recommended":
        status = STATUS_PASS
    else:
        status = STATUS_FAIL
    return {"status": status, "bits": bits, "k_problems": k_problems,
            "identity_problems": s2d_problems, "p0_identity_by_source": p0_problems,
            "revA_verdict": result["candidates"], "revA_stops": result["stops"],
            "revA_asks": result["asks"], "R-T": _short(result.get("R-T")),
            "R-S": _short(result.get("R-S")), "R-P0": result.get("R-P0"),
            "grid_status": result["grid"]["status"], "asks": asks}


def _short(part: dict | None) -> dict | None:
    if part is None:
        return None
    return {"complete": part["complete"], "checks": part["checks"], "pass": part["pass"],
            "missing": part["missing"][:10], "C-2_violations": part["C-2_violations"]}


# ------------------------------------------------------------------------------- whole
def judge_all(lines: list[dict], reva2_lines: list[dict] | None, stored: dict | None,
              reference: dict | None, stored_reva, rules_root: Path = ROOT) -> dict:
    seals = seal_problems(rules_root)
    out = {"seal_problems": seals, "S-0": judge_s0(lines), "S-C": sc_census(lines),
           "S": judge_s(lines)}
    if reva2_lines is not None and stored is not None:
        out["A"] = judge_a(lines, reva2_lines, stored, reference, stored_reva)
    else:
        out["A"] = {"status": STATUS_INCOMPLETE, "reason": "revA2 inputs not loaded"}
    statuses = [out["S-0"]["status"], out["S"]["status"], out["A"]["status"]]
    out["status"] = STATUS_STOP if seals else worst_status(statuses)
    out["asks"] = list(out["S"].get("asks") or []) + list(out["A"].get("asks") or [])
    if out["S-C"]["lines"] and not out["S-C"]["Q-S2_holds"]:
        out["asks"].append("SH-6 Q-S2 missed: ask before A-S")
    return out


def report_markdown(result: dict, source: Path) -> str:
    lines = [f"# S2D judge ({source})", "", f"- status: **{result['status']}**",
             f"- asks: {result['asks']}"]
    if result["seal_problems"]:
        lines.append(f"- SH-1 seals: {result['seal_problems']}")
    s0 = result["S-0"]
    lines.append(f"- S-0: {s0['status']} ({s0['ran']}/{len(S0_EXPECTED)} ran, errors "
                 f"{s0['errors']})")
    lines += [f"  - {row['bundle']} {row['label']} {row['key']}: "
              f"{'equal' if row['equal'] else 'DIFFERENT'} {str(row['got'])[:16]}"
              for row in s0["rows"]]
    census = result["S-C"]
    lines.append(f"- S-C census: {census['lines']} lines, soil mode "
                 f"{census['soil_mode_lines']}, groups match {census['group_counts_match']}, "
                 f"Q-S2 holds {census['Q-S2_holds']}")
    for name, group in sorted(census["groups"].items()):
        lines.append(f"  - {name}: {json.dumps(group)} Q-S2 {census['Q-S2'][name]}")
    s_part = result["S"]
    lines.append(f"- S judgement: {s_part['status']}")
    for name in ("checks", "Q-S3", "stops", "asks", "missing", "undecidable", "k_problems",
                 "loc_avoided", "selection", "sh8_pairs"):
        if name in s_part:
            lines.append(f"  - {name}: {json.dumps(s_part[name], default=str)[:2000]}")
    for record in s_part.get("sc_t", []):
        lines.append(f"  - SC-T {json.dumps(record, default=str)}")
    a_part = result["A"]
    lines.append(f"- A judgement: {a_part['status']}")
    for name, value in a_part.items():
        if name != "status":
            lines.append(f"  - {name}: {json.dumps(value, default=str)[:2000]}")
    return "\n".join(lines) + "\n"


def _json_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value.item() if hasattr(value, "item") else str(value)


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("judge", help="rules 4 .. 6 on the soil_defer files")
    run.add_argument("--dir", type=Path, default=SOIL_DEFER_DIR)
    run.add_argument("--reva2-dir", type=Path, default=ajudge.REVA2_DIR)
    run.add_argument("--ref-rg", type=Path, default=ajudge.DEFAULT_REFERENCE_RG)
    run.add_argument("--ref-reva-rg", type=Path, default=ajudge.DEFAULT_STORED_REVA_RG)
    run.add_argument("--ref-reva-rh", type=Path, default=ajudge.DEFAULT_STORED_REVA_RH)
    run.add_argument("--rules-root", type=Path, default=ROOT,
                     help="checkout whose verif_matrix holds the sealed S2D rules")
    run.add_argument("--out", type=Path, default=None, help="new Markdown file")
    run.add_argument("--json-out", type=Path, default=None, help="new JSON file")
    return parser.parse_args(argv)


def _load_a_inputs(args) -> tuple:
    """revA2 lines, stored L lines and the A-plan references; None when not available."""
    if not args.reva2_dir.exists():
        return None, None, None, None
    reva2_lines = load_reva2(args.reva2_dir)
    stored = rj.load_stored()
    reference = ajudge.load_reference(args.ref_rg) if args.ref_rg.exists() else None
    stored_reva = (ajudge.load_stored_reva(args.ref_reva_rg, args.ref_reva_rh)
                   if args.ref_reva_rg.exists() and args.ref_reva_rh.exists() else None)
    return reva2_lines, stored, reference, stored_reva


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    for path in (args.out, args.json_out):
        if path is not None and path.exists():
            print(f"input error: {path} exists (new files only)")
            return 2
    try:
        lines = [line for path in sorted(args.dir.glob("s2d_*.jsonl"))
                 for line in rj.read_lines(path)]
        reva2_lines, stored, reference, stored_reva = _load_a_inputs(args)
    except (OSError, ValueError) as exc:
        print(f"input error: {exc!r}")
        return 2
    result = judge_all(lines, reva2_lines, stored, reference, stored_reva, args.rules_root)
    report = report_markdown(result, args.dir)
    print(report)
    if args.out is not None:
        with args.out.open("x", encoding="utf-8") as handle:
            handle.write(report)
    if args.json_out is not None:
        with args.json_out.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=1, default=_json_value)
    print(json.dumps({"status": result["status"], "S-0": result["S-0"]["status"],
                      "S": result["S"]["status"], "A": result["A"]["status"],
                      "asks": len(result["asks"])}))
    return 0 if result["status"] == STATUS_PASS and not result["asks"] else 1


if __name__ == "__main__":
    sys.exit(main())
