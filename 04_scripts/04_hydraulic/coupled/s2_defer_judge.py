"""S-2 soil-mode start deferral S2D: sealed values, bundle facts and the judge.

Rules: ``06_analysis/02_control/verif_matrix/s2_soil_defer_rules.md`` (control-expert, sealed;
LF sha256 :data:`RULES_S2D_SHA256`) with its addendum ``s2_soil_defer_rules_rev1.md``
(:data:`RULES_S2D_REV1_SHA256`, RS1-1 .. RS1-9; rev1 wins over the original) on top of the
LAS-b A-plan rules it inherits (six files, ``las_revA_diag.RULES_FIELDS``). The rules text
wins where this code differs.

Lines (``s2_defer_targeted.py``): the ``run_v5`` line with the ``las`` / ``rev`` blocks of
``las_revA_targeted`` (A-S lines are revA2 lines: bundle R-0A / R-Q / R-T / R-S, candidate
P5r4) and an ``s2d`` block: bundle (S-0 / S-C / S-D / A-S / A-P0), candidate (``N0`` = N_d 0
given explicitly, ``P0`` = the preset with the S2D values in shadow, ``S2D``, ``P5r4S``),
the controller's deferral settings, the rules digests, the run identity, ``soil`` (soil-mode
start, LOC, the meta ``defer`` record, R4c30), ``trace`` (latch release time ``t_rel_s``,
the first S2D entry evaluation and the sha256 of the commands before it, the deferral
periods with latch state and the smallest returned and computed command) and
``load_trace`` (smallest true leg force per control period from the first entry
evaluation - 0.2 s for 2.7 s).

Judged here (rules 4 / 5 / 6 / 7):
  S-0   9 hashes = the stored ones (K-S0, SH-2).
  S-C   census: soil-mode keys, shadow entries, latch release and LOC in one period or
        1 .. N_d periods apart (per group), Q-S2, shadow entries with |dR| < 1 N (RS1-3).
  SH-9  the S-C P0 hashes of the 19 keys with a stored FB L job dict = the stored L hashes.
  S     S-D pairs (S2D - P0 of S-C): SC-2, SC-F, SC-S, SC-R, SC-T (a) .. (d), K-S1 .. K-S5,
        Q-S3; SH-3 / SH-6 / SH-7 / SH-8 (with the pair-level SC-R, RS1-6). Undecidable:
        S-C not 456 keys in the group counts, S-D keys outside the selection, an unfinished
        or reset deferral (RS1-4), SC-T (a) without a P0 soil mode or (d) without a covered
        load window (RS1-2); SC-T (c) is n/a without G6 items (RS1-5, counts published).
  A     A-S: K-S1 (all 311 lines seen), Q-S1, Q-S4 and the A-plan rev2 judge
        (``las_revA_judge.judge``) over the stored revA2 R-0 / R-0P5 / R-P0 / R-X lines, the
        A-S lines and the A-P0 lines (the P0 identity is judged per source: stored revA2
        lines, new A-P0 lines).
  All   one ``git_head`` and one tool sha256 set over every S2D bundle (SH-4).
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
RULES_REV1_RELATIVE = RULES_RELATIVE.with_name("s2_soil_defer_rules_rev1.md")
RULES_S2D_REV1_SHA256 = "bc95453d7caf1d32408451e6d192cd3467407470202f9ae45999e372058807bd"
"""``s2_soil_defer_rules_rev1.sha256`` (LF digest, sealed 2026-11-09 11:23:03 +09:00): the
pre-result interpretations RS1-1 .. RS1-9."""
RULES_FIELDS = ("rules_s2d_sha256", "rules_s2d_rev1_sha256", *diag.RULES_FIELDS)
RULES_VALUES = (RULES_S2D_SHA256, RULES_S2D_REV1_SHA256, *diag.RULES_VALUES)
"""Every line records the S2D rules, its rev1 and the six A-plan rules digests (rules A.2)."""

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
K_S1_A_TARGETS = 311
"""Rules 5.2: K-S1 on A-S covers 311 lines (R-0A / R-Q / R-T 294 + R-S without soil mode 17)."""
SH9_SOURCES = ("F-3", "F-4")
SH9_KEYS = 19
SH9_SOIL_KEYS = 12
"""rev1 RS1-9: S-C keys whose job dict is a stored ``fb_F3`` / ``fb_F4`` L line's (12 of them
with a soil-mode start in the stored L line)."""

# ------------------------------------------------------------------------------- thresholds
PERIOD_S = 0.1
TIME_TOLERANCE_S = 1e-9
PERIOD_MATCH_S = 1e-6
"""Two control-period times within this are the same period (load-trace window cover)."""
READY_PAIR_LIMIT_S = rj.READY_MAX_LIMIT_S
"""rev1 RS1-6: a pair with READY dt above +5.0 s is an SC-R pair violation (SH-8)."""
FLAT_RISE_DELTA_N = 1.0
"""rev1 RS1-3 / RS1-7: entries with |R_k - R_{k-1}| below this are published (not judged)."""
NOT_APPLICABLE = "n/a"
"""rev1 RS1-5: SC-T (c) on a key without the G6-1 / G6-3 / G6-7 items."""
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
DEFER_EVENT = "INFO_SOIL_MODE_DEFER"
FLAT_SOIL_MARGIN_EVENT = diag.FLAT_SOIL_MARGIN_EVENT

STATUS_STOP, STATUS_UNDECIDABLE = "stop", "undecidable"
STATUS_FAIL, STATUS_PASS, STATUS_INCOMPLETE = "fail", "pass", "incomplete"
STATUS_ORDER = (STATUS_STOP, STATUS_UNDECIDABLE, STATUS_FAIL, STATUS_PASS)


# ------------------------------------------------------------------------------- seals
def rules_path(rules_root: Path = ROOT) -> Path:
    return rules_root / RULES_RELATIVE


def sealed_files(rules_root: Path = ROOT) -> tuple:
    """SH-1: the S2D rules and their rev1 (from ``rules_root``) and the six A-plan rules."""
    path = rules_path(rules_root)
    rev1 = rules_root / RULES_REV1_RELATIVE
    return ((path, path.with_suffix(".sha256"), RULES_S2D_SHA256),
            (rev1, rev1.with_suffix(".sha256"), RULES_S2D_REV1_SHA256), *ajudge.SEALED_RULES,
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


def deferral_entry_count(line: dict) -> int:
    return (line.get("event_names") or {}).get(DEFER_EVENT, 0)


def deferral_record_problems(line: dict) -> list[str]:
    """rev1 RS1-4 (undecidable, SH-4): a deferral that never ended, or deferral rows / entry
    events the meta ``deferral`` does not hold (the soil state was reset at a TOUCH re-entry,
    or a later deferral replaced an earlier one)."""
    deferral = deferral_of(line)
    rows = rj.need(line, "s2d", "trace", "defer_rows")
    entries = deferral_entry_count(line)
    key = key_of(line)
    problems = []
    if deferral is not None and deferral.get("end_reason") is None:
        problems.append(f"{key}: deferral from {deferral.get('start_s')} s never ended (RS1-4)")
    if deferral is None and (rows or entries):
        problems.append(f"{key}: {len(rows)} deferral rows, {entries} entry events and no meta "
                        "deferral (reset, RS1-4)")
    if entries > 1:
        problems.append(f"{key}: {entries} deferral entries, the meta holds the last (RS1-4)")
    return problems


def flat_entries(lines: list[dict]) -> dict:
    """rev1 RS1-3 / RS1-7 (published, not judged): entries (acting or shadow) whose recorded
    ``rise_delta_N`` is below 1 N in size; entries without the field are counted apart."""
    keys, unrecorded = [], []
    entries = 0
    for line in lines:
        for check in entry_checks(line):
            if not check.get("entered"):
                continue
            entries += 1
            delta_N = check.get("rise_delta_N")
            if delta_N is None:
                unrecorded.append(key_of(line))
            elif abs(delta_N) < FLAT_RISE_DELTA_N:
                keys.append(key_of(line))
    return {"entries": entries, "flat": len(keys), "flat_keys": sorted(keys),
            "unrecorded": len(unrecorded), "unrecorded_keys": sorted(unrecorded)[:20]}


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


def cross_bundle_identity_problems(lines: list[dict]) -> list[str]:
    """SH-4: every finished line of every S2D bundle (S-0, S-C, S-D, A-S, A-P0) has one
    ``git_head`` and one set of tool sha256."""
    identities: dict[tuple[str, str], set[str]] = {}
    for line in lines:
        bundle = s2d_of(line).get("bundle")
        if bundle not in BUNDLES or rj.is_error(line):
            continue
        identity = s2d_of(line).get("identity") or {}
        found = (str(identity.get("git_head")),
                 json.dumps(identity.get("sha256"), sort_keys=True))
        identities.setdefault(found, set()).add(bundle)
    if len(identities) <= 1:
        return []
    return [f"{len(identities)} run identities across bundles: "
            + "; ".join(f"{head[:12]} tools {hashlib.sha256(tools.encode()).hexdigest()[:12]}: "
                        f"{sorted(bundles)}" for (head, tools), bundles in identities.items())]


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
    return {"lines": len(sc_lines), "keys": len(by_key(sc_lines)),
            "errors": error_count(lines, "S-C"), "groups": groups,
            "group_counts_match": counts == SOIL_GROUP_COUNTS,
            "soil_mode_lines": sum(group["soil_mode"] for group in groups.values()),
            "Q-S2": q_s2, "Q-S2_holds": all(value["holds"] for value in q_s2.values()),
            "flat_entries": flat_entries(sc_lines)}


def sc_complete_problems(census: dict) -> list[str]:
    """SH-4 (S judgement): S-C holds 456 keys in the rules-3 group counts."""
    problems = []
    if census["keys"] != SC_LINES or census["lines"] != SC_LINES:
        problems.append(f"S-C: {census['lines']} lines / {census['keys']} keys, "
                        f"expected {SC_LINES}")
    if not census["group_counts_match"]:
        counts = {name: group["lines"] for name, group in census["groups"].items()}
        problems.append(f"S-C groups {counts} != {SOIL_GROUP_COUNTS}")
    return problems


def sh9_check(lines: list[dict], stored: dict | None) -> dict:
    """rev1 RS1-9 SH-9: the S-C P0 (shadow on) hash of every key whose job dict is a stored
    ``fb_F3`` / ``fb_F4`` L line's equals that line's hash (19 keys, 12 with soil mode).

    Status ``stop`` on a different hash, or with S-C finished and other key counts;
    ``incomplete`` before S-C finished; ``undecidable`` without the stored L lines."""
    import las_rev_targeted as rev

    sc_by_key = by_key(lines_of(lines, "S-C"))
    if not sc_by_key:
        return {"status": STATUS_INCOMPLETE, "reason": "no S-C line"}
    if stored is None:
        return {"status": STATUS_UNDECIDABLE, "reason": "stored fb_F3 / fb_F4 L lines not loaded"}
    rows = []
    for source in SH9_SOURCES:
        for key, l_line in sorted(stored[source].items()):
            line = sc_by_key.get(key)
            if line is None or rev._comparable_job(line["job"]) != rev._comparable_job(
                    l_line["job"]):
                continue
            rows.append({"source": source, "key": key, "S-C": line["commands_sha256"],
                         "L": l_line["commands_sha256"],
                         "equal": line["commands_sha256"] == l_line["commands_sha256"],
                         "L_soil_mode": has_soil_event(l_line)})
    different = [row["key"] for row in rows if not row["equal"]]
    soil = sum(row["L_soil_mode"] for row in rows)
    is_sc_finished = len(sc_by_key) == SC_LINES
    problems = [f"SH-9 {key}: S-C P0 hash != stored L hash" for key in different]
    if is_sc_finished and (len(rows) != SH9_KEYS or soil != SH9_SOIL_KEYS):
        problems.append(f"SH-9 {len(rows)} job-identical keys ({soil} soil mode), expected "
                        f"{SH9_KEYS} ({SH9_SOIL_KEYS})")
    if problems:
        status = STATUS_STOP
    elif not is_sc_finished:
        status = STATUS_INCOMPLETE
    else:
        status = STATUS_PASS
    return {"status": status, "keys": len(rows), "soil_mode_keys": soil,
            "equal": len(rows) - len(different), "different": different, "problems": problems,
            "rows": rows}


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
    """K-S4 (rev1 RS1-8): every deferral period, the last active one included, has the latch
    held, no retracting command computed in that period (before the output delay) and no
    retracting command returned (applied) in it; one row per deferral period."""
    rows = rj.need(line, "s2d", "trace", "defer_rows")
    key = key_of(line)
    problems = []
    active = [row for row in rows if row["active"]]
    for row in active:
        if not row["in_zone"]:
            problems.append(f"K-S4 {key} t {row['t_s']}: latch released")
        computed_m_s = rj.need(row, "min_computed_m_s")
        if computed_m_s < 0.0:
            problems.append(f"K-S4 {key} t {row['t_s']}: computed command {computed_m_s} < 0")
        if row["min_command_m_s"] < 0.0:
            problems.append(f"K-S4 {key} t {row['t_s']}: returned command "
                            f"{row['min_command_m_s']} < 0")
    deferral = deferral_of(line)
    is_ended = deferral is not None and deferral.get("end_reason") is not None
    if is_ended and not deferral_record_problems(line) and len(active) != deferral["periods"]:
        problems.append(f"K-S4 {key}: {len(active)} deferral rows for {deferral['periods']} "
                        "deferral periods")
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


def load_window_problem(line: dict, t0_s: float, t1_s: float) -> str | None:
    """rev1 RS1-2: the load trace has a row for every control period ending in [t0, t1]
    (``load_minimum_N`` reads those rows); None when it does."""
    trace = rj.need(line, "s2d", "load_trace")
    if trace is None:
        return "no load trace"
    ends = [t_s for t_s, _value in trace["rows"]]
    periods = round((t1_s - t0_s) / PERIOD_S)
    missing = []
    for index in range(periods + 1):
        wanted_s = t0_s + index * PERIOD_S
        if not any(abs(end_s - wanted_s) <= PERIOD_MATCH_S for end_s in ends):
            missing.append(round(wanted_s, 10))
    if not missing:
        return None
    return f"load trace misses {len(missing)} of {periods + 1} periods (first {missing[0]} s)"


def has_g6_items(cand: dict, base: dict) -> bool:
    """rev1 RS1-5: SC-T (c) applies to a key whose ``d1.items`` hold a G6-1 / -3 / -7 item."""
    items = {**rj.need(base, "d1", "items"), **rj.need(cand, "d1", "items")}
    return any(name in items for name in G6_ITEMS)


def new_g6_failures(cand: dict, base: dict) -> list[str]:
    cand_items, base_items = rj.need(cand, "d1", "items"), rj.need(base, "d1", "items")
    return [name for name in G6_ITEMS
            if base_items.get(name) is not False and cand_items.get(name) is False]


def _load_drop_check(cand: dict, base: dict, t0_s: float, t1_s: float) -> tuple:
    """SC-T (d): (check or None when a window is not covered, S2D min, P0 min, problems)."""
    problems = []
    for name, line in (("S2D", cand), ("P0", base)):
        problem = load_window_problem(line, t0_s, t1_s)
        if problem is not None:
            problems.append(f"{name}: {problem}")
    if problems:
        return None, None, None, problems
    cand_min = load_minimum_N(cand, t0_s, t1_s)
    base_min = load_minimum_N(base, t0_s, t1_s)
    is_within = cand_min >= base_min - LOAD_DROP_LIMIT_N - TIME_TOLERANCE_S
    return is_within, cand_min, base_min, []


def sc_t_record(cand: dict, base: dict) -> dict:
    """SC-T (a) .. (d) of one expired pair: True / False, None = undecidable (no P0 soil-mode
    start for (a), a load window not covered for (d); rev1 RS1-2), ``n/a`` for (c) on a key
    without G6 items (rev1 RS1-5)."""
    deferral = deferral_of(cand)
    delay_s = soil_start_s(cand) - soil_start_s(base) if has_soil_mode(base) else None
    new_items = new_g6_failures(cand, base)
    t0_s, t1_s = deferral["start_s"], deferral["end_s"] + LOAD_TAIL_S
    is_within, cand_min, base_min, window_problems = _load_drop_check(cand, base, t0_s, t1_s)
    checks = {
        "a": None if delay_s is None else delay_s <= DELAY_LIMIT_S + TIME_TOLERANCE_S,
        "b": not k_s4_problems(cand),
        "c": not new_items if has_g6_items(cand, base) else NOT_APPLICABLE,
        "d": is_within,
    }
    return {"key": key_of(cand), "reason": deferral["end_reason"], "delay_s": delay_s,
            "new_g6_failures": new_items, "min_load_S2D_N": cand_min, "min_load_P0_N": base_min,
            "window_s": [t0_s, t1_s], "window_problems": window_problems, "checks": checks}


def check_outcome(values) -> bool | None:
    """False when any value fails, None when any is undecidable, else True (``n/a`` skipped)."""
    present = [value for value in values if value != NOT_APPLICABLE]
    if any(value is False for value in present):
        return False
    if any(value is None for value in present):
        return None
    return True


def sc_t_undecidable(records: list[dict]) -> list[str]:
    """The SC-T parts no record could decide (SH-4 reasons, rev1 RS1-2)."""
    out = []
    for record in records:
        parts = [name for name, value in record["checks"].items() if value is None]
        if parts:
            out.append(f"{record['key']}: SC-T {parts} undecidable (delay {record['delay_s']}, "
                       f"{record['window_problems']})")
    return out


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
    dt_s = record["dt_s"]
    record["SC-R_fail"] = (record["changed"] and dt_s is not None
                           and dt_s > READY_PAIR_LIMIT_S + TIME_TOLERANCE_S)
    return record


def is_sh8_pair(pair: dict) -> bool:
    """SH-8: an SC-2, SC-F, SC-S or pair-level SC-R violation (READY dt > +5.0 s, rev1 RS1-6;
    a READY lost against P0 is an SC-2 (b) violation already)."""
    return bool(pair["violations"] or pair["SC-F_fail"] or pair["SC-S_fail"]
                or pair["SC-R_fail"])


def sc_violation_count(pairs: dict) -> int:
    """SH-8: pairs with an SC-2, SC-F, SC-S or SC-R pair violation."""
    return sum(1 for pair in pairs.values() if is_sh8_pair(pair))


def judge_s(lines: list[dict]) -> dict:
    """Rules 5.1 on the S-D pairs (S2D line, S-C P0 line of the key)."""
    sc_lines = lines_of(lines, "S-C")
    base_by_key = by_key(sc_lines)
    selection = sd_selection(lines)
    random_keys = set(selection["random_keys"])
    cand_by_key = by_key(lines_of(lines, "S-D"))
    selected = set(selection["keys"])
    out = {"selection": {name: len(value) for name, value in selection.items()},
           "errors": error_count(lines, "S-D"), "missing": sorted(selected - set(cand_by_key)),
           "extra": sorted(set(cand_by_key) - selected), "pairs": {},
           "undecidable": [], "k_problems": [], "sc_t": [], "loc_avoided": [],
           "flat_entries": flat_entries(list(cand_by_key.values()))}
    if not cand_by_key:
        return {**out, "status": STATUS_INCOMPLETE}
    out["undecidable"] += sc_complete_problems(sc_census(lines))
    if out["extra"]:
        out["undecidable"].append(f"{len(out['extra'])} S-D keys outside the selection: "
                                  f"{out['extra'][:5]}")
    for key in sorted(set(cand_by_key) & set(base_by_key) & selected):
        _judge_pair(out, cand_by_key[key], base_by_key[key], key in random_keys)
    out["sc_t_c_not_applicable"] = _not_applicable_counts(out)
    out["identity_problems"] = identity_problems(lines_of(lines, "S-D") + sc_lines)
    return _s_verdict(out)


def _judge_pair(out: dict, cand: dict, base: dict, is_random: bool) -> None:
    """One S-D pair into ``out``: K problems, SC record, SC-T (expired), RS1-4 reasons. An
    unfinished or reset deferral is undecidable and still judged on the other criteria."""
    key = key_of(cand)
    try:
        out["undecidable"] += deferral_record_problems(cand)
        out["k_problems"] += pair_k_problems(cand, base, is_random)
        record = sc_pair_record(cand, base)
        record["has_g6_items"] = has_g6_items(cand, base)
        out["pairs"][key] = record
        deferral = deferral_of(cand)
        if is_expired(deferral):
            out["sc_t"].append(sc_t_record(cand, base))
        elif deferral is not None and deferral.get("end_reason") == LOC_REASON:
            out["loc_avoided"].append(key)
    except rj.MissingField as exc:
        out["undecidable"].append(f"{key}: missing {exc}")


def _not_applicable_counts(out: dict) -> dict:
    """rev1 RS1-5: pairs without G6 items (SC-T (c) n/a) and the expired pairs among them."""
    keys = sorted(key for key, pair in out["pairs"].items() if not pair["has_g6_items"])
    expired = sorted(record["key"] for record in out["sc_t"]
                     if record["checks"]["c"] == NOT_APPLICABLE)
    return {"pairs": len(keys), "expired_pairs": len(expired), "expired_keys": expired}


def _s_verdict(out: dict) -> dict:
    pairs = out["pairs"]
    ready = rj.ready_population(pairs)
    c2 = {key: pair["violations"] for key, pair in pairs.items() if pair["violations"]}
    sc_t_values = [value for record in out["sc_t"] for value in record["checks"].values()]
    checks = {"SC-2": not c2,
              "SC-F": not [key for key, pair in pairs.items() if pair["SC-F_fail"]],
              "SC-S": not [key for key, pair in pairs.items() if pair["SC-S_fail"]],
              "SC-R": None if ready["R-1"] is None else bool(ready["R-1"] and ready["R-2"]),
              "SC-T": check_outcome(sc_t_values),
              "K": not out["k_problems"]}
    q_s3 = check_outcome(record["checks"]["a"] for record in out["sc_t"])
    out["undecidable"] += sc_t_undecidable(out["sc_t"])
    out.update(ready=ready, c2_violations=c2, checks=checks, **{"Q-S3": q_s3},
               sh8_pairs=sc_violation_count(pairs),
               sc_r_pair_violations=sorted(key for key, pair in pairs.items()
                                           if pair["SC-R_fail"]))
    stops, asks = [], []
    if out["k_problems"]:
        stops.append(f"SH-3 K-S1 .. K-S5: {out['k_problems'][:5]}")
    if out["identity_problems"]:
        stops.append(f"SH-4 identity: {out['identity_problems'][:5]}")
    if checks["SC-T"] is False:
        asks.append("SH-7 SC-T violation: S judgement short, do not go to A-S, ask")
    if out["sh8_pairs"] >= SH8_PAIRS:
        stops.append(f"SH-8 {out['sh8_pairs']} pairs with SC-2 / SC-F / SC-S / SC-R violations")
    if q_s3 is False:
        asks.append("SH-6 Q-S3 missed: ask before A-S")
    out.update(stops=stops, asks=asks)
    is_undecided = checks["SC-R"] is None or checks["SC-T"] is None
    if stops:
        status = STATUS_STOP
    elif out["undecidable"] or out["missing"] or out["errors"] or is_undecided:
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


def k_s1_coverage_problems(bits: dict) -> list[str]:
    """Rules 5.2 (SH-4 when short): K-S1 saw every one of its 311 A-S target lines."""
    if bits["targets"] == K_S1_A_TARGETS and bits["seen_targets"] == K_S1_A_TARGETS:
        return []
    return [f"K-S1 saw {bits['seen_targets']} of {bits['targets']} target lines, expected "
            f"{K_S1_A_TARGETS}"]


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
    k_problems, undecidable = list(bits["K-S1"]), k_s1_coverage_problems(bits)
    for line in as_lines:
        try:
            undecidable += deferral_record_problems(line)
            k_problems += k_s4_problems(line) + k_s5_problems(line)
        except rj.MissingField as exc:
            undecidable.append(f"{key_of(line)}: missing {exc}")
    asks = []
    if bits["Q-S1"] is None or not bits["Q-S1"]["holds"]:
        asks.append("SH-6 Q-S1 missed")
    if not bits["Q-S4"]["holds"]:
        asks.append("SH-6 Q-S4 missed")
    if k_problems or s2d_problems or result["stops"]:
        status = STATUS_STOP
    elif undecidable or verdict in (STATUS_UNDECIDABLE, STATUS_INCOMPLETE):
        status = STATUS_UNDECIDABLE
    elif verdict == "adopt_recommended":
        status = STATUS_PASS
    else:
        status = STATUS_FAIL
    return {"status": status, "bits": bits, "k_problems": k_problems,
            "undecidable": undecidable, "flat_entries": flat_entries(as_lines),
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
    """Every part (S-0, S-C census, SH-9, S, A) and the run identity across bundles.

    ``stored`` is ``las_rev_judge.load_stored()`` (the stored L lines: SH-9 and A), None when
    not loaded."""
    seals = seal_problems(rules_root)
    identity = cross_bundle_identity_problems(lines)
    out = {"seal_problems": seals, "identity_across_bundles": identity,
           "S-0": judge_s0(lines), "S-C": sc_census(lines), "SH-9": sh9_check(lines, stored),
           "S": judge_s(lines)}
    if reva2_lines is not None and stored is not None:
        out["A"] = judge_a(lines, reva2_lines, stored, reference, stored_reva)
    else:
        out["A"] = {"status": STATUS_INCOMPLETE, "reason": "revA2 inputs not loaded"}
    statuses = [out["S-0"]["status"], out["SH-9"]["status"], out["S"]["status"],
                out["A"]["status"]]
    if identity:
        statuses.append(STATUS_UNDECIDABLE)  # SH-4: one commit and one tool set for all
    status = STATUS_STOP if seals else worst_status(statuses)
    if status == STATUS_PASS and STATUS_INCOMPLETE in statuses:
        status = STATUS_INCOMPLETE  # a passed part does not stand for a part not yet run
    out["status"] = status
    out["asks"] = list(out["S"].get("asks") or []) + list(out["A"].get("asks") or [])
    if out["S-C"]["lines"] and not out["S-C"]["Q-S2_holds"]:
        out["asks"].append("SH-6 Q-S2 missed: ask before A-S")
    return out


def report_markdown(result: dict, source: Path) -> str:
    lines = [f"# S2D judge ({source})", "", f"- status: **{result['status']}**",
             f"- asks: {result['asks']}"]
    if result["seal_problems"]:
        lines.append(f"- SH-1 seals: {result['seal_problems']}")
    if result["identity_across_bundles"]:
        lines.append(f"- SH-4 identity across bundles: {result['identity_across_bundles']}")
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
    lines.append(f"  - shadow entries with |dR| < 1 N (RS1-3, no tolerance RS1-7): "
                 f"{json.dumps(census['flat_entries'])}")
    sh9 = result["SH-9"]
    lines.append(f"- SH-9 shadow harmlessness (RS1-9): {sh9['status']} "
                 f"{json.dumps({k: v for k, v in sh9.items() if k not in ('status', 'rows')})}")
    s_part = result["S"]
    lines.append(f"- S judgement: {s_part['status']}")
    for name in ("checks", "Q-S3", "stops", "asks", "missing", "extra", "undecidable",
                 "k_problems", "loc_avoided", "selection", "sh8_pairs", "sc_r_pair_violations",
                 "sc_t_c_not_applicable", "flat_entries"):
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


def _load_stored() -> dict | None:
    """The stored L lines (SH-9 and A); None when one of the files is not there."""
    if not all(path.exists() for path in rj.STORED_PATHS.values()):
        return None
    return rj.load_stored()


def _load_a_inputs(args) -> tuple:
    """revA2 lines, stored L lines and the A-plan references; None when not available."""
    stored = _load_stored()
    if not args.reva2_dir.exists():
        return None, stored, None, None
    reva2_lines = load_reva2(args.reva2_dir)
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
                      "SH-9": result["SH-9"]["status"], "S": result["S"]["status"],
                      "A": result["A"]["status"],
                      "asks": len(result["asks"])}))
    return 0 if result["status"] == STATUS_PASS and not result["asks"] else 1


if __name__ == "__main__":
    sys.exit(main())
