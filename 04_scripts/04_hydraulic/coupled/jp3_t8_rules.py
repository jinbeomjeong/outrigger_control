"""436.9 T-JR-10 meta clause on the harness (addendum 4a-3 section 3): the conditions A / B, the
record equality with the fixed allowed paths of 3.2, and the record C.

Pure functions of two result lines (a stored VB line of ``resume_k1/h10_reuse_rerun.jsonl`` and
a new VBH line of the run_v5 batch ``j9_t8``); ``jp3_tjr_judge.py t8`` calls them.

The allowed paths of 3.2 are fixed by the addendum (a change needs a new addendum); the unit
test ``test_jp3_addendum_4a3.py`` checks them against its table and against the record keys the
code writes (``harness_hydraulics._LockLog.record``, ``ROD_READING_EVIDENCE_KEYS``).
"""
from __future__ import annotations

P3_RECORD_KEYS = ("extend_bound_check", "tension_truth")
"""3.2 ③ keys (``p3_hash_check.py`` ``P3_RECORD_KEYS``): always left out of the comparison."""
TEXT_ONLY_PATHS = ("m2_law.rule",)
"""3.2 text-only path (``p3_hash_check.py`` ``TEXT_ONLY_PATHS``): always left out."""
LOCK_LOG_KEYS = ("lock_log", "lock_log_columns", "relock_count", "relock_step_over_1bar_count",
                 "max_abs_dp_tr_step_bar", "p1_retract_seed_count",
                 "p1_retract_seed_step_max_bar", "p1_retract_seed_log",
                 "p1_retract_seed_log_columns")
"""3.2 436.9 per-lock records (``_LockLog.record``): left out only when the stored line lacks
them and the new line has them."""
EVIDENCE_KEYS = ("rod_reading_truth_calls", "two_pressure_reads")
"""3.2 436.9 B2 evidence keys: the same rule as :data:`LOCK_LOG_KEYS`."""
NEW_ONLY_KEYS = (*LOCK_LOG_KEYS, *EVIDENCE_KEYS)
FALLBACK_EVENT = "WARN_ROD_PRESSURE_FALLBACK"
"""3.1 condition A: no event of this name in either line."""
STORED_TAG = "final_C4G2_P3_LAS_K1"
"""3.1: the controller tag of every stored h10 line (else not judgeable)."""
STORED_REVISION = 4
"""3.1: the ③ revision of the stored line's T4h meta (else not judgeable)."""
HASH_LENGTH = 64
FALLBACK_ESTIMATE_KEY = "fallback_rod_estimate_Pa"
"""3.1 condition C (a record): per-leg values in the T4h meta, when both sides have them."""
FALLBACK_ESTIMATE_TOLERANCE_PA = 1.0


def differing_paths(before, after, path: str = "") -> list[str]:
    """Dotted paths where two JSON values differ (``p3_hash_check.differing_paths``)."""
    if isinstance(before, dict) and isinstance(after, dict):
        paths = []
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}" if path else str(key)
            paths += differing_paths(before.get(key), after.get(key), child)
        return paths
    return [] if before == after else [path]


def record_differences(stored: dict, new: dict) -> list[str]:
    """3.1 record equality: the differing ``hydraulics_record`` paths outside 3.2's list."""
    excluded = set(P3_RECORD_KEYS)
    excluded |= {key for key in NEW_ONLY_KEYS if key not in stored and key in new}
    stored_kept = {key: value for key, value in stored.items() if key not in excluded}
    new_kept = {key: value for key, value in new.items() if key not in excluded}
    return [path for path in differing_paths(stored_kept, new_kept)
            if path not in TEXT_ONLY_PATHS]


def has_fallback_event(line: dict) -> bool | None:
    """3.1 A: a ``WARN_ROD_PRESSURE_FALLBACK`` in ``event_names`` or ``events`` (None: a key
    missing)."""
    if "event_names" not in line or "events" not in line:
        return None
    names = [str(name) for name in line["event_names"] or []]
    names += [str(event[1]) for event in line["events"] or [] if len(event) > 1]
    return any(name.startswith(FALLBACK_EVENT) for name in names)


def condition_b_problems(stored: dict, new: dict) -> list[str]:
    """3.1 B: ``commands_sha256`` (64 characters), ``event_names`` and ``events`` equal."""
    problems = []
    stored_hash, new_hash = stored.get("commands_sha256"), new.get("commands_sha256")
    if not (isinstance(new_hash, str) and len(new_hash) == HASH_LENGTH
            and stored_hash == new_hash):
        problems.append("commands_sha256 differs")
    for key in ("event_names", "events"):
        if stored.get(key) != new.get(key):
            problems.append(f"{key} differ")
    return problems


def fallback_estimate_record(stored_meta: dict | None, new_meta: dict | None) -> dict:
    """3.1 C (a record): new - stored ``fallback_rod_estimate_Pa`` per leg and whether each is
    >= -1 Pa; "no record" when either side lacks it (never not judgeable)."""
    stored_values = (stored_meta or {}).get(FALLBACK_ESTIMATE_KEY)
    new_values = (new_meta or {}).get(FALLBACK_ESTIMATE_KEY)
    if stored_values is None or new_values is None:
        return {"record": "no record"}
    differences = [None if a is None or b is None else float(b) - float(a)
                   for a, b in zip(stored_values, new_values, strict=True)]
    return {"new_minus_stored_Pa": differences,
            "at_least_minus_1_Pa": [None if value is None
                                    else value >= -FALLBACK_ESTIMATE_TOLERANCE_PA
                                    for value in differences]}
