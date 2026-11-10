"""Judge of the T-3 targeted check (sealed ``las_targeted_rules_rev3.md`` 3 K-0 .. K-7 and 4
H-T3-0 .. H-T3-6, ``las_targeted_rules_rev4.md`` 1 #1: T-3c fixed at 76); called by
``las_judge.py --stage T-3`` and by ``las_t3.py`` (R-0 gate and the final judge).

Baselines (rev4a 1): the composite-key line of ``v5/d1.jsonl`` (its sha256 must be the key
list's ``d1_baseline.sha256``) for the D-1 lines, the key list's stored T4h hash
(``shadow_commands_sha256_all_folders``, one value) for the Dg-3 lines. The key list is the
source of the key sets and counts; its ``G6-2`` field is void, its other baseline fields
(verdict, fail items, P3-2, READY, stroke, FAULT names, hash) must equal ``d1.jsonl``
(``key-list``, else H-T3-3).

  K-0  seals (the nine sealed files) and every line's ``t3.identity`` = its file header's
  K-1  key set per bundle = the key list (R-0 7, T-3a 228, T-3b 4, T-3c 76); no error left
       after the one retry (H-T3-2)
  K-2  R-0: hash = baseline, controller tag without ``_LAS`` (V0 none, VB ``final_C4G2_P3``;
       Dg-3: as its folder), LAS-b off and not fired
  K-3  T-3: tag = ``final_C4G2_LAS`` (V0, Dg-3 off) / ``final_C4G2_P3_LAS`` (VB, Dg-3 v4_on),
       ``_FB`` fails; a Dg-3 line (R-0 too) has the stored record's plant options, controller
       settings (LAS-b block and the full-config record left out) and ③ rule (rev4a 4)
  K-4  T-3a G1 uniform 72 + T-3b 4: not fired (a fired G1 line is H-T3-4, rev4a 3)
  K-5  every T-3 line that did not fire, G1 and Dg-3 included: hash = baseline (H-T3-5)
  K-6  every fired T-3 D-1 line: ``las_h7.h7_violations`` with the J-1 format (C2, C3, C4'
       G6-2, P3-2, C5'-R READY, C5'-S stroke; rev4a 2); a possibly cut event list is
       ``K-6-undecidable`` (H-T3-3)
  K-7  table of the fired lines (start, leg, end, active / scaled periods, LOC - t_off,
       Delta F_judged_min, start rho); a record, not a criterion
Stops: H-T3-0 (K-0), H-T3-3 (key-list, K-1 key set, K-3, K-6-undecidable), H-T3-2 (errors),
H-T3-1 (K-2), H-T3-4 (K-4), H-T3-5 (K-5), H-T3-6 (K-6). Exit codes: 0 passed, 1 a criterion
failed (K-2, K-4 .. K-6), 2 a stop without a verdict (H-T3-0, H-T3-2, H-T3-3) or an input error.

Rules mode ``rev5`` (sealed ``las_targeted_rules_rev5.md``, the default of ``main_t3``; the
criteria functions keep the rev3 / rev4c behaviour when no gate state is given):
  K-0   eleven seals; the R-0, R-0K and T-3 headers have one identity; the stored Dg-3 T4h
        events have no R4c30 (rev5 2.5)
  K-2   R-0 as above, and the line's K1 gate is off
  K-1K  the R-0K key list (45, list sha256, classes; its stored fields = ``d1.jsonl`` is the
        ``key-list`` check) and its key set
  K-2K  (i) tag ``final_C4G2_K1`` / ``final_C4G2_P3_K1``, LAS-b off, gate on, not fired, a
        ``would_block`` record (H-T3-3); (ii) ``would_block_any`` false -> stored hash, (iii)
        ``r0_no_r4`` keys: no block and the stored hash (H-T3-1K); (iv) ``uniform_r4`` keys: no
        block (H-T3-1Q: stop and ask)
  K-3   T-3K tag ``final_C4G2_LAS_K1`` / ``final_C4G2_P3_LAS_K1`` (``_LAS`` without ``_K1``
        fails), gate on; Dg-3 settings compared without the exact gate key, whose value is
        checked against the bundle (rev5 2.5)
  K-5   silent T-3K lines: hash = B(k); a silent D-1 line of a key outside R-0K must have no
        ``would_block`` (H-T3-5)
  K-6   fired T-3K D-1 lines against B(k): the R-0K line for an R-0K key, else ``d1.jsonl``
  K-7   + ``would_block_any``, ``applied``, first dP, the baseline source, whether the blocked
        LOC set differs from the baseline line's (a record)
Stops in rev5 order H-T3-0, H-T3-3, H-T3-2, H-T3-1, H-T3-1K, H-T3-1Q, H-T3-4, H-T3-5, H-T3-6;
H-T3-1K exits 1, H-T3-1Q exits 2.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import las_h7
import las_t3
import las_targeted as lt

TAG_V0_LAS = "final_C4G2_LAS"
TAG_P3 = "final_C4G2_P3"
TAG_P3_LAS = "final_C4G2_P3_LAS"
"""``v5_options`` tags (``LAS_CONTROLLER_TAG``, ``EXTEND_START_CONTROLLER_TAG``,
``EXTEND_START_LAS_CONTROLLER_TAG``); the ``rev4c`` mode."""
TAG_V0_K1 = "final_C4G2_K1"
TAG_P3_K1 = "final_C4G2_P3_K1"
TAG_V0_LAS_K1 = "final_C4G2_LAS_K1"
TAG_P3_LAS_K1 = "final_C4G2_P3_LAS_K1"
"""Rev5 2.2 tags (R-0K V0 / VB, T-3K V0 / VB): ``v5_options.with_order_gate_tag(None)``,
``with_order_gate_tag(EXTEND_START_CONTROLLER_TAG)``, ``LAS_K1_CONTROLLER_TAG``,
``EXTEND_START_LAS_K1_CONTROLLER_TAG``."""
LAS_TAG_TOKEN = "_LAS"
K1_TAG_SUFFIX = "_K1"
FB_TAG_TOKEN = "_FB"
IDENTITY_KEYS = ("git_head", "sha256", "c2_sha256", "threads", "workers", "affinity")
UNIFORM_G1 = "G1"
NO_VERDICT_STOPS = ("H-T3-0", "H-T3-2", "H-T3-3")
ASK_STOPS = ("H-T3-1Q",)
"""Rev5 4: a stop that asks the user (exit 2 as a stop without a verdict)."""
STOP_ORDER = ("H-T3-0", "H-T3-3", "H-T3-2", "H-T3-1", "H-T3-4", "H-T3-5", "H-T3-6")
STOP_ORDER_REV5 = ("H-T3-0", "H-T3-3", "H-T3-2", "H-T3-1", "H-T3-1K", "H-T3-1Q", "H-T3-4",
                   "H-T3-5", "H-T3-6")
CRITERION_STOP = {"K-0": "H-T3-0", "key-list": "H-T3-3", "K-1": "H-T3-3", "K-3": "H-T3-3",
                  "K-6-undecidable": "H-T3-3", "errors": "H-T3-2", "K-2": "H-T3-1",
                  "K-4": "H-T3-4", "K-5": "H-T3-5", "K-6": "H-T3-6",
                  "K-1K": "H-T3-3", "K-2K-i": "H-T3-3", "K-2K-ii": "H-T3-1K",
                  "K-2K-iii": "H-T3-1K", "K-2K-iv": "H-T3-1Q"}
"""The K-1K / K-2K rows are rev5 3.2 and 4 (they appear only in rev5 results)."""
K1_GATE_PREFIX = "K1 gate"
"""Rev5: problems of the line's recorded gate state start with this (R-0 K-2 keeps them)."""
"""rev3 4 with rev4a: a key-list field != ``d1.jsonl``, a Dg-3 run condition != the stored
record and a possibly cut event list are H-T3-3 (rev4a 1, 4 #2, 5); a fired G1 line is H-T3-4,
a silent line with another hash H-T3-5 wherever it is (rev4a 3)."""
DG3_IGNORED_SETTING_PREFIXES = ("liftoff_approach_slow", "full_config")
"""rev4a 4 #2: the LAS-b block and the full-config record are left out of the comparison."""
DG3_IGNORED_SETTING_KEYS = (las_t3.GATE_SETTING_KEY,)
"""Rev5 2.5: the exact gate key is left out too (never the whole ``slope_clearance_margin``
prefix); its value is checked against the bundle condition (:func:`gate_state_problems`). The
stored records have no such key; the ``rev4c`` mode leaves it out as well, because the Dg-3
runner records it since rev5 and the rev3 comparison never saw it."""
DG3_OPTION_REPRESENTATION = {"v4_on": {"extend_start_tracked": True}}
"""The one declared option difference of a folder (to confirm by control-expert): the stored
v4_on run switched ③ on through the preset (``with_10hz_d1(extend_start_tracked=True)``,
commit d74ab26, no option key), today's ``VB`` carries it as the option ``extend_start_tracked``.
The ③ state itself is compared through ``two_pressure.extend_start_rule`` (K-3)."""


# ------------------------------------------------------------------------------- input
def read_jsonl(path: Path) -> tuple[dict | None, list[dict]]:
    """(header, result lines) of a T-3 file."""
    header, lines = None, []
    for text in path.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        record = json.loads(text)
        if "header" in record:
            header = record["header"]
        else:
            lines.append(record)
    return header, lines


def line_key(line: dict) -> str:
    return line["t3"]["line_key"]


def good_lines(lines: list[dict]) -> tuple[dict[str, dict], list[str]]:
    """(line key -> last error-free line, keys whose every line is an error)."""
    good = {line_key(line): line for line in lines if "error" not in line}
    errors = sorted({line_key(line) for line in lines if "error" in line} - set(good))
    return good, errors


def load_baseline(path: Path) -> dict[str, dict]:
    return lt.load_baseline(path)


def baseline_hash(entry: dict, baseline: dict[str, dict]) -> str | None:
    if entry["kind"] == las_t3.KIND_D1:
        record = baseline.get(entry["line_key"])
        return None if record is None else record["commands_sha256"]
    hashes = entry.get("shadow_commands_sha256_all_folders") or []
    return hashes[0] if len(hashes) == 1 else None


REV5_TAGS = {(False, False): (None, TAG_P3), (False, True): (TAG_V0_K1, TAG_P3_K1),
             (True, True): (TAG_V0_LAS_K1, TAG_P3_LAS_K1)}
"""Rev5 2.2: (LAS-b on, gate on) -> (V0 / Dg-3 off tag, VB / Dg-3 v4_on tag) of R-0, R-0K,
T-3K."""


def expected_tag(entry: dict, line: dict, las_on: bool, gate_on: bool | None = None
                 ) -> str | None:
    """The controller tag a line must carry.

    Args:
        entry: The key-list entry (D-1 or Dg-3).
        line: The result line (a D-1 line's ``job.setting`` decides V0 / VB).
        las_on: LAS-b of the bundle (T-3 on; R-0 and R-0K off).
        gate_on: The K1 gate of the bundle (rev5 2.2 table); None is the rev3 2.2 table of the
            ``rev4c`` mode, which has no gate.

    Raises:
        ValueError: A condition rev5 has no tag for (LAS-b on with the gate off, a Dg-3 line
            in R-0K).
    """
    if entry["kind"] == las_t3.KIND_D1:
        is_p3 = line["job"]["setting"] == "VB"
    else:
        is_p3 = entry["folder"] == "v4_on"
    if gate_on is None:
        if las_on:
            return TAG_P3_LAS if is_p3 else TAG_V0_LAS
        return TAG_P3 if is_p3 else None
    condition = (bool(las_on), bool(gate_on))
    if condition not in REV5_TAGS:
        raise ValueError(f"rev5 has no bundle with LAS-b {las_on} and the gate {gate_on}")
    if entry["kind"] == las_t3.KIND_DG3 and condition == (False, True):
        raise ValueError("rev5 has no Dg-3 line in R-0K")
    v0_tag, p3_tag = REV5_TAGS[condition]
    return p3_tag if is_p3 else v0_tag


def is_fired(line: dict) -> bool:
    return bool((line.get("las_t3") or {}).get("fired"))


# ------------------------------------------------------------------------------- checks
def identity_problems(label: str, header: dict | None, lines: list[dict]) -> list[str]:
    """K-0: every line's identity equals the header's."""
    if header is None:
        return [f"{label}: no header line"]
    reference = header.get("identity") or {}
    problems = []
    for line in lines:
        identity = (line.get("t3") or {}).get("identity") or {}
        differing = [key for key in IDENTITY_KEYS if identity.get(key) != reference.get(key)]
        if differing:
            problems.append(f"{label} {line_key(line)}: {differing} differ from the header")
    return problems


def key_list_problems(keys: dict, entries: dict[str, list[dict]], baseline: dict[str, dict],
                      baseline_path: Path) -> tuple[list[str], list[str]]:
    """(problems, notes) of the key list against ``d1.jsonl``."""
    problems, notes = [], []
    digest = hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    if digest != keys["d1_baseline"]["sha256"]:
        problems.append(f"d1.jsonl sha256 {digest} != key list {keys['d1_baseline']['sha256']}")
    for bundle in ("T-3a", "T-3c"):
        for entry in entries[bundle]:
            record = baseline.get(entry["line_key"])
            if record is None:
                problems.append(f"{entry['line_key']}: no d1.jsonl line")
                continue
            problems += _entry_differences(entry, record)
    for entry in entries[las_t3.R0] + entries["T-3b"]:
        if entry["kind"] == las_t3.KIND_DG3 and baseline_hash(entry, baseline) is None:
            problems.append(f"{entry['line_key']}: not one stored T4h hash")
    notes.append("key list G6-2 field void (rev4a 1); K-6 reads d1.items G6-2_loc of d1.jsonl")
    return problems, notes


def _entry_differences(entry: dict, record: dict) -> list[str]:
    d1 = record["d1"]
    faults = sorted(name for name in (record.get("event_names") or {})
                    if name.startswith(las_h7.FAULT_PREFIX))
    pairs = {"commands_sha256": (entry["commands_sha256"], record["commands_sha256"]),
             "verdict": (entry["verdict"], d1["verdict"]),
             "fail_items": (sorted(entry["fail_items"]), sorted(d1["fail_items"])),
             "P3-2": (entry["P3-2"], d1["items"].get("P3-2")),
             "t_ready_s": (entry["t_ready_s"], d1["t_ready_s"]),
             "stroke_max_m": (entry["stroke_max_m"], d1["stroke_max_m"]),
             "fault_names": (sorted(entry["fault_names"]), faults)}
    return [f"{entry['line_key']}: key list {name} {a!r} != d1.jsonl {b!r}"
            for name, (a, b) in pairs.items() if a != b]


def key_set_problems(bundle: str, entries: list[dict], good: dict[str, dict],
                     all_lines: list[dict]) -> list[str]:
    """K-1 of a bundle (an empty expected set is never a pass)."""
    expected = {entry["line_key"] for entry in entries}
    have = {key for key, line in good.items() if line["t3"]["bundle"] == bundle}
    seen = {line_key(line) for line in all_lines if line["t3"]["bundle"] == bundle}
    problems = []
    if not expected:
        problems.append(f"{bundle}: empty key set")
    missing, extra = sorted(expected - have), sorted(seen - expected)
    if missing:
        problems.append(f"{bundle}: {len(missing)} keys without a good line {missing[:3]}")
    if extra:
        problems.append(f"{bundle}: {len(extra)} keys not in the key list {extra[:3]}")
    return problems


def recorded_gate(entry: dict, line: dict) -> bool | None:
    """The K1 gate state a line recorded: ``las_t3.k1.enabled`` (D-1), the controller setting
    of the gate key (Dg-3); None when not recorded."""
    if entry["kind"] == las_t3.KIND_DG3:
        value = (line.get("controller_settings") or {}).get(las_t3.GATE_SETTING_KEY)
    else:
        value = ((line.get("las_t3") or {}).get("k1") or {}).get("enabled")
    return None if value is None else bool(value)


def gate_state_problems(entry: dict, line: dict, gate_on: bool) -> list[str]:
    """Rev5 2.2 / 2.5: the line recorded the bundle's gate state."""
    recorded = recorded_gate(entry, line)
    if recorded is None:
        return [f"{K1_GATE_PREFIX} state not recorded"]
    if recorded != gate_on:
        return [f"{K1_GATE_PREFIX} {recorded} != bundle {gate_on}"]
    return []


def _rev5_tag_problems(tag: str | None) -> list[str]:
    if tag is not None and LAS_TAG_TOKEN in tag and not tag.endswith(K1_TAG_SUFFIX):
        return [f"tag {tag} has {LAS_TAG_TOKEN} without {K1_TAG_SUFFIX}"]
    return []


def tag_problems(entry: dict, line: dict, is_las_on: bool, gate_on: bool | None = None
                 ) -> list[str]:
    """K-3 (T-3) / the tag part of K-2 (R-0) / K-2K (i) (R-0K) for one line; ``gate_on`` None
    is the ``rev4c`` mode (no gate check)."""
    tag = line.get("controller_tag")
    problems = []
    if tag is not None and FB_TAG_TOKEN in tag:
        problems.append(f"tag {tag} has {FB_TAG_TOKEN}")
    if gate_on is not None:
        problems += _rev5_tag_problems(tag)
    try:
        wanted = expected_tag(entry, line, is_las_on, gate_on)
    except ValueError as exc:
        problems.append(f"tag {tag}: {exc}")
    else:
        if tag != wanted:
            problems.append(f"tag {tag} != {wanted}")
    las_enable = (line.get("las_t3") or {}).get("enable")
    if bool(las_enable) != is_las_on:
        problems.append(f"LAS-b enable {las_enable}")
    if gate_on is not None:
        problems += gate_state_problems(entry, line, gate_on)
    if entry["kind"] == las_t3.KIND_DG3:
        rule = line.get("extend_start_rule")
        if rule != las_t3.DG3_RULE_OF_FOLDER[entry["folder"]]:
            problems.append(f"③ start rule {rule} != folder {entry['folder']}")
    return problems


def _compared_settings(settings: dict | None) -> dict:
    return {key: value for key, value in (settings or {}).items()
            if not key.startswith(DG3_IGNORED_SETTING_PREFIXES)
            and key not in DG3_IGNORED_SETTING_KEYS}


def dg3_condition_problems(entry: dict, line: dict, stored_dir: Path) -> list[str]:
    """rev4a 4 #2, #3: the Dg-3 run used the stored record's plant options and controller
    settings (LAS-b block and identity left out) and the stored folder's ③ rule."""
    meta, record = las_t3.stored_dg3_record(entry, stored_dir)
    problems = []
    if line.get("v5_setting") != record.get("v5_setting"):
        problems.append(f"v5_setting {line.get('v5_setting')} != {record.get('v5_setting')}")
    options = dict(line.get("hydraulic_options") or {})
    for key, value in DG3_OPTION_REPRESENTATION.get(entry["folder"], {}).items():
        if options.get(key) == value:
            del options[key]
    if options != (record.get("hydraulic_options") or {}):
        problems.append(f"hydraulic_options {options} != stored {record.get('hydraulic_options')}")
    new, stored = (_compared_settings(line.get("controller_settings")),
                   _compared_settings(record.get("controller_settings")))
    differing = sorted(key for key in set(new) | set(stored) if new.get(key) != stored.get(key))
    if differing:
        problems.append(f"controller_settings differ: "
                        f"{ {key: (new.get(key), stored.get(key)) for key in differing} }")
    stored_rule = (meta.get("preset_settings") or {}).get("two_pressure.extend_start_rule")
    if line.get("extend_start_rule") != stored_rule:
        problems.append(f"③ rule {line.get('extend_start_rule')} != stored preset {stored_rule}")
    return problems


def condition_problems(entry: dict, line: dict, is_las_on: bool, stored_dir: Path,
                       gate_on: bool | None = None) -> list[str]:
    """K-3 (T-3) / the R-0 run condition: tag, LAS-b state (rev5: gate state), and a Dg-3
    line's condition."""
    problems = tag_problems(entry, line, is_las_on, gate_on)
    if entry["kind"] == las_t3.KIND_DG3:
        problems += dg3_condition_problems(entry, line, stored_dir)
    return problems


def hash_problem(entry: dict, line: dict, baseline: dict[str, dict]) -> str | None:
    stored = baseline_hash(entry, baseline)
    new = line.get("commands_sha256")
    if stored is not None and new == stored:
        return None
    return f"hash {str(new)[:12]} != baseline {str(stored)[:12]}"


def k1_of(line: dict | None) -> dict:
    """The ``las_t3.k1`` block of a line (empty: none, e.g. a stored ``d1.jsonl`` line)."""
    return ((line or {}).get("las_t3") or {}).get("k1") or {}


def k7_k1_columns(entry: dict, line: dict, baseline: dict[str, dict],
                  r0k_keys: frozenset[str]) -> dict:
    """Rev5 3.4 record columns of a fired line: the gate's decisions against the baseline."""
    k1 = k1_of(line)
    key = entry["line_key"]
    base_k1 = k1_of(baseline.get(key)) if key in r0k_keys else {}
    blocked, base_blocked = k1.get("blocked_t_loc_s"), base_k1.get("blocked_t_loc_s")
    return {"would_block_any": k1.get("would_block_any"), "applied": k1.get("applied_count"),
            "first_dP": k1.get("first_dP"),
            "baseline_source": las_t3.R0K if key in r0k_keys else "stored",
            "decisions_differ": (None if blocked is None or base_blocked is None
                                 else sorted(blocked) != sorted(base_blocked))}


def k7_row(entry: dict, line: dict, baseline: dict[str, dict]) -> dict:
    las = line.get("las_t3") or {}
    row = {"key": entry["line_key"], "start_s": las.get("start_s"),
           "start_leg": las.get("start_leg"), "end_reason": las.get("end_reason"),
           "active_periods": las.get("active_periods"),
           "scaled_periods": las.get("scaled_periods"),
           "loc_minus_t_off_s": las.get("loc_minus_t_off_s"),
           "start_rho": las.get("start_rho"), "events": las.get("events")}
    record = baseline.get(entry["line_key"]) if entry["kind"] == las_t3.KIND_D1 else None
    if record is not None and "d1" in line:
        new_f, base_f = line["d1"].get("F_judged_min_N"), record["d1"].get("F_judged_min_N")
        row["dF_judged_min_N"] = None if None in (new_f, base_f) else new_f - base_f
    return row


# ------------------------------------------------------------------------------- R-0
def r0_criteria(lines: list[dict], entries: list[dict], baseline: dict[str, dict],
                stored_dir: Path = las_t3.V5_DIR, gate_on: bool | None = None) -> dict:
    """K-1 (R-0), errors, K-2 and the run condition (K-3 form) of the R-0 lines; ``gate_on``
    False (rev5) adds the gate-off check to K-2."""
    good, errors = good_lines(lines)
    kept_prefixes = ("tag", "LAS-b") if gate_on is None else ("tag", "LAS-b", K1_GATE_PREFIX)
    k2, k3 = {}, {}
    for entry in entries:
        line = good.get(entry["line_key"])
        if line is None:
            continue
        found = [problem for problem in tag_problems(entry, line, False, gate_on)
                 if problem.startswith(kept_prefixes)]
        problem = hash_problem(entry, line, baseline)
        if problem:
            found.append(problem)
        if is_fired(line):
            found.append("fired")
        if found:
            k2[entry["line_key"]] = found
        if entry["kind"] == las_t3.KIND_DG3:
            condition = dg3_condition_problems(entry, line, stored_dir)
            if condition:
                k3[entry["line_key"]] = condition
    return {"K-1": key_set_problems(las_t3.R0, entries, good, lines),
            "errors": errors, "K-2": k2, "K-3": k3}


def first_stop(criteria: dict, order: tuple[str, ...] = STOP_ORDER) -> str | None:
    stops = {CRITERION_STOP[name] for name, found in criteria.items() if found}
    return next((stop for stop in order if stop in stops), None)


def r0_gate(lines: list[dict], entries: list[dict], baseline_path: Path,
            rules: str = las_t3.RULES_REV4C) -> dict:
    """The run's R-0 gate: the next bundle starts only without a stop (H-T3-1 / H-T3-2 /
    H-T3-3); the Dg-3 records are read from the folder of ``baseline_path`` (the v5 folder).
    ``rev5`` also checks that every R-0 line had the gate off."""
    gate_on = False if rules == las_t3.RULES_REV5 else None
    criteria = r0_criteria(lines, entries, load_baseline(baseline_path), baseline_path.parent,
                           gate_on)
    return {"criteria": criteria, "stop": first_stop(criteria)}


# ------------------------------------------------------------------------------- R-0K
def r0k_key_list_problems(entries: list[dict], baseline: dict[str, dict]) -> list[str]:
    """``key-list`` (rev5 2.3, H-T3-3): the stored fields of the R-0K list equal
    ``d1.jsonl`` (hash, tag, verdict, R4c30 count)."""
    problems = []
    for entry in entries:
        key = entry["line_key"]
        record = baseline.get(key)
        if record is None:
            problems.append(f"{key}: no d1.jsonl line")
            continue
        count = int((record.get("event_names") or {}).get(las_t3.R4C30_EVENT, 0))
        pairs = {"stored_commands_sha256": (entry.get("stored_commands_sha256"),
                                            record.get("commands_sha256")),
                 "stored_controller_tag": (entry.get("stored_controller_tag"),
                                           record.get("controller_tag")),
                 "stored_verdict": (entry.get("stored_verdict"),
                                    (record.get("d1") or {}).get("verdict")),
                 "stored_r4c30_count": (entry.get("stored_r4c30_count"), count)}
        problems += [f"{key}: R-0K list {name} {a!r} != d1.jsonl {b!r}"
                     for name, (a, b) in pairs.items() if a != b]
    return problems


def _stored_hash(baseline: dict[str, dict], key: str) -> str | None:
    record = baseline.get(key)
    return None if record is None else record.get("commands_sha256")


def _blocked_detail(line: dict, record: dict | None) -> dict:
    """What H-T3-1Q attaches: the blocking decisions and the difference to the stored line."""
    k1 = k1_of(line)
    decisions = [d for d in k1.get("decisions") or [] if d.get("would_block")]
    stored_d1 = (record or {}).get("d1") or {}
    new_d1 = line.get("d1") or {}
    return {"blocked": [{"t_loc_s": d.get("t_loc_s"), "dP": d.get("dP"), "n_P": d.get("n_P"),
                         "n_S": d.get("n_S")} for d in decisions],
            "hash": [line.get("commands_sha256"), (record or {}).get("commands_sha256")],
            "verdict": [new_d1.get("verdict"), stored_d1.get("verdict")],
            "t_ready_s": [new_d1.get("t_ready_s"), stored_d1.get("t_ready_s")],
            "stroke_max_m": [new_d1.get("stroke_max_m"), stored_d1.get("stroke_max_m")]}


def _r0k_line_problems(entry: dict, line: dict, baseline: dict[str, dict],
                       criteria: dict) -> None:
    key = entry["line_key"]
    found = tag_problems(entry, line, False, True)
    if is_fired(line):
        found.append("fired")
    blocked = k1_of(line).get("would_block_any")
    if blocked is None:
        found.append("no would_block record")
    if found:
        criteria["K-2K-i"][key] = found
    stored = _stored_hash(baseline, key)
    is_stored_hash = stored is not None and line.get("commands_sha256") == stored
    hash_text = f"hash {str(line.get('commands_sha256'))[:12]} vs stored {str(stored)[:12]}"
    if blocked is False and not is_stored_hash:
        criteria["K-2K-ii"][key] = f"would_block_any false, {hash_text}"
    if entry.get("class") == las_t3.CLASS_R0_NO_R4 and (blocked or not is_stored_hash):
        criteria["K-2K-iii"][key] = f"r0_no_r4: would_block_any {blocked}, {hash_text}"
    if entry.get("class") == las_t3.CLASS_UNIFORM_R4 and blocked:
        criteria["K-2K-iv"][key] = _blocked_detail(line, baseline.get(key))


def r0k_record(entry: dict, line: dict, baseline: dict[str, dict]) -> dict:
    """One row of the R-0K record (every key; a record, not a criterion)."""
    k1 = k1_of(line)
    return {"key": entry["line_key"], "class": entry.get("class"),
            "would_block_any": k1.get("would_block_any"), "applied": k1.get("applied_count"),
            "first_dP": k1.get("first_dP"),
            "stored_hash": line.get("commands_sha256") == _stored_hash(baseline,
                                                                        entry["line_key"]),
            "predicted_would_block": entry.get("predicted_would_block")}


def r0k_criteria(lines: list[dict], entries: list[dict], baseline: dict[str, dict],
                 r0k_list_problems: list[str] | None = None) -> tuple[dict, list[dict]]:
    """K-1K, errors, the R-0K key-list check and K-2K (i) .. (iv) of the R-0K lines (rev5
    3.2), and the R-0K record rows."""
    good, errors = good_lines(lines)
    criteria = {"K-1K": [*(r0k_list_problems or []),
                         *key_set_problems(las_t3.R0K, entries, good, lines)],
                "key-list": r0k_key_list_problems(entries, baseline), "errors": errors,
                "K-2K-i": {}, "K-2K-ii": {}, "K-2K-iii": {}, "K-2K-iv": {}}
    records = []
    for entry in entries:
        line = good.get(entry["line_key"])
        if line is None:
            continue
        _r0k_line_problems(entry, line, baseline, criteria)
        records.append(r0k_record(entry, line, baseline))
    return criteria, records


def r0k_gate(lines: list[dict], entries: list[dict], baseline_path: Path) -> dict:
    """The run's R-0K gate (rev5 3.2): T-3K starts only without a stop."""
    criteria, records = r0k_criteria(lines, entries, load_baseline(baseline_path))
    return {"criteria": criteria, "stop": first_stop(criteria, STOP_ORDER_REV5),
            "r0k": records}


def stop_exit_code(stop: str | None) -> int:
    """Exit code of one stop: 0 none, 2 without a verdict or asking (H-T3-1Q), else 1."""
    if stop is None:
        return 0
    return 2 if stop in (*NO_VERDICT_STOPS, *ASK_STOPS) else 1


def baseline_lines(r0k_lines: list[dict], r0k_entries_: list[dict],
                   baseline: dict[str, dict]) -> dict[str, dict]:
    """Rev5 3.1 B(k): the R-0K line for an R-0K key (left out when that key has no good line,
    so its T-3K line has no baseline), the stored ``d1.jsonl`` line for any other key."""
    good, _ = good_lines(r0k_lines)
    out = dict(baseline)
    for entry in r0k_entries_:
        key = entry["line_key"]
        if key in good:
            out[key] = good[key]
        else:
            out.pop(key, None)
    return out


# ------------------------------------------------------------------------------- T-3
def t3_criteria(lines: list[dict], entries: dict[str, list[dict]], baseline: dict[str, dict],
                stored_dir: Path = las_t3.V5_DIR, gate_on: bool | None = None,
                r0k_keys: frozenset[str] = frozenset()) -> tuple[dict, list[dict]]:
    """K-1 (T-3 bundles), errors, K-3 .. K-6 (and undecidable K-6 lines), the K-7 rows.

    Args:
        lines: The T-3 result lines.
        entries: Bundle entries of the key list.
        baseline: The baselines (rev5: B(k) of :func:`baseline_lines`).
        stored_dir: The v5 folder of the stored Dg-3 records.
        gate_on: None (``rev4c``) or True (rev5 T-3K: gate checks, K-5 addition, K-7 columns).
        r0k_keys: The R-0K keys (rev5: their silent lines need no would_block check).
    """
    good, errors = good_lines(lines)
    criteria = {"K-1": [], "errors": errors, "K-3": {}, "K-4": {}, "K-5": {}, "K-6": {},
                "K-6-undecidable": {}}
    k7 = []
    for bundle in las_t3.T3_BUNDLES:
        criteria["K-1"] += key_set_problems(bundle, entries[bundle], good, lines)
        for entry in entries[bundle]:
            line = good.get(entry["line_key"])
            if line is None:
                continue
            _judge_t3_line(bundle, entry, line, baseline, criteria, stored_dir, gate_on,
                           r0k_keys)
            if is_fired(line):
                row = k7_row(entry, line, baseline)
                if gate_on is not None:
                    row.update(k7_k1_columns(entry, line, baseline, r0k_keys))
                k7.append(row)
    return criteria, k7


def _is_k4_line(bundle: str, entry: dict) -> bool:
    return bundle == "T-3b" or (bundle == "T-3a" and entry.get("base") == UNIFORM_G1)


def _silent_block_problem(entry: dict, line: dict, r0k_keys: frozenset[str]) -> str | None:
    """Rev5 3.3 K-5 addition ((G-c)): a silent D-1 line of a key outside R-0K blocked R4c30."""
    if entry["kind"] != las_t3.KIND_D1 or entry["line_key"] in r0k_keys:
        return None
    if k1_of(line).get("would_block_any"):
        return "silent line outside R-0K has would_block (premise G-c)"
    return None


def _judge_t3_line(bundle: str, entry: dict, line: dict, baseline: dict[str, dict],
                   criteria: dict, stored_dir: Path, gate_on: bool | None = None,
                   r0k_keys: frozenset[str] = frozenset()) -> None:
    key = entry["line_key"]
    found = condition_problems(entry, line, True, stored_dir, gate_on)
    if found:
        criteria["K-3"][key] = found
    fired = is_fired(line)
    hash_issue = hash_problem(entry, line, baseline)
    if _is_k4_line(bundle, entry) and fired:  # rev4a 3: a fired G1 line
        criteria["K-4"][key] = "fired"
    if not fired and gate_on is not None:
        block_issue = _silent_block_problem(entry, line, r0k_keys)
        hash_issue = "; ".join(issue for issue in (hash_issue, block_issue) if issue) or None
    if not fired and hash_issue:  # rev4a 3: any silent line, G1 and Dg-3 included
        criteria["K-5"][key] = hash_issue
    if fired and entry["kind"] == las_t3.KIND_D1:
        if key not in baseline:
            criteria["K-6-undecidable"][key] = "no baseline line (R-0K line missing)"
            return
        try:
            violations = las_h7.h7_violations(line, baseline[key], las_h7.D1_FORMAT)
        except las_h7.UndecidableLine as exc:
            criteria["K-6-undecidable"][key] = str(exc)
            return
        if violations:
            criteria["K-6"][key] = violations


def _header_problems(headers: dict[str, dict | None], lines: dict[str, list[dict]]) -> list[str]:
    """K-0 identity of the result files: each line = its header, every header the same, no
    ``--keys`` subset."""
    problems = []
    for label, header in headers.items():
        problems += identity_problems(label, header, lines[label])
        if header and header.get("keys_subset"):
            problems.append(f"{label}: a --keys subset run is not a T-3 verdict")
    identities = [header.get("identity") for header in headers.values() if header]
    if any(identity != identities[0] for identity in identities[1:]):
        problems.append(f"{' / '.join(headers)} headers have other identities")
    return problems


def judge_t3(r0_path: Path, t3_path: Path, keys_path: Path, baseline_path: Path,
             rules_dir: Path, rules: str = las_t3.RULES_REV5, r0k_path: Path | None = None,
             r0k_keys_path: Path = las_t3.R0K_KEYS_PATH) -> dict:
    """The T-3 verdict (module docstring) of a rules mode.

    Raises:
        OSError, KeyError, ValueError: An input file is missing or not of this form.
    """
    if rules == las_t3.RULES_REV5:
        if r0k_path is None:
            r0k_path = t3_path.parent / las_t3.R0K_FILE
        return _judge_t3_rev5(r0_path, r0k_path, t3_path, keys_path, r0k_keys_path,
                              baseline_path, rules_dir)
    keys = las_t3.load_key_list(keys_path)
    entries = las_t3.bundle_entries(keys)
    baseline = load_baseline(baseline_path)
    r0_header, r0_lines = read_jsonl(r0_path)
    t3_header, t3_lines = read_jsonl(t3_path)
    stored_dir = baseline_path.parent
    seals = lt.seal_problems(rules_dir, las_t3.REV4C_REQUIRED_SEALS)
    list_problems, notes = key_list_problems(keys, entries, baseline, baseline_path)
    k0 = seals + las_t3.count_problems(entries)
    k0 += identity_problems("R-0", r0_header, r0_lines)
    k0 += identity_problems("T-3", t3_header, t3_lines)
    if r0_header and t3_header and r0_header.get("identity") != t3_header.get("identity"):
        k0.append("R-0 and T-3 headers have other identities")
    for label, header in (("R-0", r0_header), ("T-3", t3_header)):
        if header and header.get("keys_subset"):
            k0.append(f"{label}: a --keys subset run is not a T-3 verdict")
    r0 = r0_criteria(r0_lines, entries[las_t3.R0], baseline, stored_dir)
    t3, k7 = t3_criteria(t3_lines, entries, baseline, stored_dir)
    criteria = {"K-0": k0, "key-list": list_problems, "K-1": r0["K-1"] + t3["K-1"],
                "errors": r0["errors"] + t3["errors"], "K-2": r0["K-2"],
                "K-3": {**r0["K-3"], **t3["K-3"]}, "K-4": t3["K-4"], "K-5": t3["K-5"],
                "K-6": t3["K-6"], "K-6-undecidable": t3["K-6-undecidable"]}
    stops = [CRITERION_STOP[name] for name, found in criteria.items() if found]
    counts = {"R-0": len(good_lines(r0_lines)[0]),
              **{bundle: sum(line["t3"]["bundle"] == bundle
                             for line in good_lines(t3_lines)[0].values())
                 for bundle in las_t3.T3_BUNDLES}}
    fired = sorted(row["key"] for row in k7)
    return {"stage": "T-3", "criteria": criteria,
            "passed": {name: not found for name, found in criteria.items()},
            "stops": sorted(set(stops), key=STOP_ORDER.index), "counts": counts,
            "fired": fired, "fired_count": len(fired),
            "silent_count": sum(counts.values()) - counts["R-0"] - len(fired),
            "k7": k7, "notes": notes, "format_absent_k6": las_h7.D1_FORMAT.absent,
            "seals": {name: lt.SEALS[name].sha256 for name in las_t3.REV4C_REQUIRED_SEALS},
            "identity": (t3_header or r0_header or {}).get("identity")}


def _rev5_k0(entries: dict[str, list[dict]], rules_dir: Path, stored_dir: Path,
             headers: dict[str, dict | None], lines: dict[str, list[dict]]) -> list[str]:
    k0 = lt.seal_problems(rules_dir, las_t3.T3_REQUIRED_SEALS) + las_t3.count_problems(entries)
    k0 += las_t3.dg3_r4c30_problems(entries, stored_dir)
    return k0 + _header_problems(headers, lines)


def _judge_t3_rev5(r0_path: Path, r0k_path: Path, t3_path: Path, keys_path: Path,
                   r0k_keys_path: Path, baseline_path: Path, rules_dir: Path) -> dict:
    """Rev5 3 / 4: R-0 (rev3 K-2 with the gate off), R-0K (K-1K, K-2K), T-3K against B(k)."""
    keys = las_t3.load_key_list(keys_path)
    entries = las_t3.bundle_entries(keys)
    entries[las_t3.R0K] = las_t3.r0k_entries(las_t3.load_r0k_key_list(r0k_keys_path))
    baseline = load_baseline(baseline_path)
    stored_dir = baseline_path.parent
    files = {"R-0": read_jsonl(r0_path), "R-0K": read_jsonl(r0k_path), "T-3": read_jsonl(t3_path)}
    headers = {label: header for label, (header, _) in files.items()}
    lines = {label: body for label, (_, body) in files.items()}
    list_problems, notes = key_list_problems(keys, entries, baseline, baseline_path)
    r0 = r0_criteria(lines["R-0"], entries[las_t3.R0], baseline, stored_dir, gate_on=False)
    r0k, r0k_rows = r0k_criteria(lines["R-0K"], entries[las_t3.R0K], baseline,
                                 las_t3.r0k_key_problems(entries[las_t3.R0K], entries))
    r0k_keys = frozenset(entry["line_key"] for entry in entries[las_t3.R0K])
    b_of_k = baseline_lines(lines["R-0K"], entries[las_t3.R0K], baseline)
    t3, k7 = t3_criteria(lines["T-3"], entries, b_of_k, stored_dir, True, r0k_keys)
    criteria = {"K-0": _rev5_k0(entries, rules_dir, stored_dir, headers, lines),
                "key-list": list_problems + r0k["key-list"], "K-1": r0["K-1"] + t3["K-1"],
                "K-1K": r0k["K-1K"], "errors": r0["errors"] + r0k["errors"] + t3["errors"],
                "K-2": r0["K-2"], "K-2K-i": r0k["K-2K-i"], "K-2K-ii": r0k["K-2K-ii"],
                "K-2K-iii": r0k["K-2K-iii"], "K-2K-iv": r0k["K-2K-iv"],
                "K-3": {**r0["K-3"], **t3["K-3"]}, "K-4": t3["K-4"], "K-5": t3["K-5"],
                "K-6": t3["K-6"], "K-6-undecidable": t3["K-6-undecidable"]}
    stops = {CRITERION_STOP[name] for name, found in criteria.items() if found}
    t3_good = good_lines(lines["T-3"])[0].values()
    counts = {"R-0": len(good_lines(lines["R-0"])[0]),
              "R-0K": len(good_lines(lines["R-0K"])[0]),
              **{bundle: sum(line["t3"]["bundle"] == bundle for line in t3_good)
                 for bundle in las_t3.T3_BUNDLES}}
    fired = sorted(row["key"] for row in k7)
    notes.append("B(k): the R-0K line for the 45 R-0K keys, d1.jsonl / stored T4h hash else")
    return {"stage": "T-3", "rules": las_t3.RULES_REV5, "criteria": criteria,
            "passed": {name: not found for name, found in criteria.items()},
            "stops": sorted(stops, key=STOP_ORDER_REV5.index), "counts": counts,
            "fired": fired, "fired_count": len(fired),
            "silent_count": sum(counts.values()) - counts["R-0"] - counts["R-0K"] - len(fired),
            "k7": k7, "r0k": r0k_rows, "notes": notes,
            "format_absent_k6": las_h7.D1_FORMAT.absent,
            "seals": {name: lt.SEALS[name].sha256 for name in las_t3.T3_REQUIRED_SEALS},
            "identity": (headers["T-3"] or headers["R-0K"] or headers["R-0"] or {}).get(
                "identity")}


def exit_code(result: dict) -> int:
    if any(stop in (*NO_VERDICT_STOPS, *ASK_STOPS) for stop in result["stops"]):
        return 2
    return 1 if result["stops"] else 0


# ------------------------------------------------------------------------------- report
def _cell(text) -> str:
    return str(text).replace("|", "\\|")


REPORT_TITLES = {las_t3.RULES_REV4C: "# LAS T-3 judge (rules rev3 3 / 4, rev4 1 #1)",
                 las_t3.RULES_REV5: "# LAS T-3K judge (rules rev5 3 / 4; rev3, rev4, rev4a)"}


def _k7_lines(result: dict) -> list[str]:
    is_rev5 = result.get("rules") == las_t3.RULES_REV5
    header = "| key | start s | leg | end | active | scaled | LOC-t_off s | dF kN | rho |"
    rule = "|---|---|---|---|---|---|---|---|---|"
    if is_rev5:
        header += " would_block | applied | first dP | baseline | decisions differ |"
        rule += "---|---|---|---|---|"
    lines = ["", "## K-7 fired lines", "", header, rule]
    for row in result["k7"]:
        d_f = row.get("dF_judged_min_N")
        text = (f"| `{_cell(row['key'])}` | {row['start_s']} | {row['start_leg']} | "
                f"{row['end_reason']} | {row['active_periods']} | {row['scaled_periods']} | "
                f"{row['loc_minus_t_off_s']} | {'-' if d_f is None else f'{d_f / 1e3:.3f}'} | "
                f"{row['start_rho']} |")
        if is_rev5:
            text += (f" {row.get('would_block_any')} | {row.get('applied')} | "
                     f"{row.get('first_dP')} | {row.get('baseline_source')} | "
                     f"{row.get('decisions_differ')} |")
        lines.append(text)
    return lines


def _r0k_lines(result: dict) -> list[str]:
    lines = ["", "## R-0K record", "",
             "| key | class | would_block | applied | first dP | stored hash | predicted |",
             "|---|---|---|---|---|---|---|"]
    for row in result.get("r0k") or []:
        lines.append(f"| `{_cell(row['key'])}` | {row['class']} | {row['would_block_any']} | "
                     f"{row['applied']} | {row['first_dP']} | {row['stored_hash']} | "
                     f"{row['predicted_would_block']} |")
    return lines


def report_lines(result: dict) -> list[str]:
    title = REPORT_TITLES[result.get("rules", las_t3.RULES_REV4C)]
    lines = [title, "",
             f"lines per bundle: {result['counts']}; fired {result['fired_count']}, "
             f"silent {result['silent_count']}", "",
             "| criterion | result | problems |", "|---|---|---|"]
    for name, found in result["criteria"].items():
        count = len(found)
        lines.append(f"| {name} | {'ok' if not found else 'NG'} | {count} |")
    lines.append("")
    for name, found in result["criteria"].items():
        items = found.items() if isinstance(found, dict) else ((None, f) for f in found)
        for key, problem in items:
            prefix = f"`{_cell(key)}`: " if key is not None else ""
            lines.append(f"- {name} {prefix}{_cell(problem)}")
    if result["k7"]:
        lines += _k7_lines(result)
    if result.get("r0k"):
        lines += _r0k_lines(result)
    for note in result["notes"]:
        lines.append(f"- note: {note}")
    lines.append(f"- K-6 criteria without a field in the J-1 format: "
                 f"{result['format_absent_k6'] or 'none'}")
    lines.append(f"result: stops {result['stops'] or 'none'}")
    return lines


def main_t3(args) -> int:
    """``las_judge.py --stage T-3 <las_T3.jsonl> --r0 <las_T3_R0.jsonl> ...`` (``--t3-rules``
    rev5 by default: ``--r0k`` defaults to the R-0K file next to the T-3 lines)."""
    out_dir = args.jsonl.parent
    r0_path = args.r0 or out_dir / las_t3.R0_FILE
    keys_path = args.keys or las_t3.KEYS_PATH
    rules_dir = (args.rules.parent if args.rules is not None else las_t3.RULES_DIR)
    rules = getattr(args, "t3_rules", None) or las_t3.RULES_REV5
    r0k_path = getattr(args, "r0k", None) or out_dir / las_t3.R0K_FILE
    r0k_keys_path = getattr(args, "r0k_keys", None) or las_t3.R0K_KEYS_PATH
    try:
        result = judge_t3(r0_path, args.jsonl, keys_path, args.baseline, rules_dir, rules,
                          r0k_path, r0k_keys_path)
        text = "\n".join(report_lines(result)) + "\n"
        if args.out is not None:
            with args.out.open("x", encoding="utf-8") as handle:
                handle.write(text)
        if args.json_out is not None:
            with args.json_out.open("x", encoding="utf-8") as handle:
                handle.write(json.dumps(result, indent=1, default=str))
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"stage": "T-3", "error": repr(exc)}))
        return 2
    print(text, end="")
    print(json.dumps({key: result[key] for key in ("stage", "stops", "counts", "fired_count",
                                                   "passed")}))
    return exit_code(result)
