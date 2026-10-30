"""Stable-READY comparison of candidate runs against "current" (spec 429.8, ZIC criteria Z-1..Z-4).

Spec 429.8 corrects the READY comparison of 429.4: READY times are compared at the *stable READY*,
the last READY entry that lasts until the end of the run. A run that ends without a stable READY
(re-level, probe or FAULT at the end) makes its row ``incomparable``; such rows keep their first
DONE time and end phase but are left out of Z-3 / Z-4. The end attitude is the mean roll / pitch
over the stable READY interval.

Criteria per candidate (spec 429.4 with the 429.8 correction):
  Z-1  every idle run (no candidate part acted) keeps the "current" command hash
  Z-2  no pass -> fail and no new FAULT; a spec 427.9 safe stop (``stroke_limited_stop``) and
       a FAULT end of a P36s guard stop are listed apart and not counted
  Z-3  focus-part runs: stable-READY end attitude increase (max |roll|, |pitch|) <= 0.02 deg
  Z-4  focus-part runs: stable-READY delay > +5 s in no row, median delay <= 0
  kept the 1.1 / 1.2 x h6 fail -> pass rows of stage 1 stay fail -> pass (``--keep-fixed``)
"Focus-part runs" are the runs where ``--focus-part`` acted, alone or with other parts; the
summary also records Z-3 / Z-4 on the runs where it acted alone (``focus_only``, attribution
inside a combination candidate, not part of the verdict).

Where the stable READY comes from (``ready_basis`` of a row):
  phase_events             the record has ``phase_events`` ([[t_s, phase], ...], transitions);
                           the stable READY is the last transition when it is into READY
  first_ready_final_ready  fallback for records without phase events: a run that ends in READY
                           is taken to have stayed there since its first READY (``t_ready_s``).
                           Exact unless the run left READY and came back inside the hold window
  no_stable_ready          the run does not end in READY (exact for both kinds of record)
The end attitude (``attitude_basis``) is ``stable_ready_att_mean_deg`` when the record has it,
otherwise the end-of-run value ``att_end_deg`` (``end_instant``).

Inputs:
  wrapper result files of ``s9_slope_fix_candidates.py`` (``records``): candidate records are the
  non-"current" records of the positional files, baseline records the "current" records of the
  ``--baseline`` files (a ``*_cmp.json`` holds both; one file may be given on both sides).
  event screens (study A, r67; ``results``) are paired file by file with
  ``--screen-pair <current.json> <candidate.json>``; their READY is the READY return after the
  event (``t_ready_back_s``).

Usage (python-dev, standard library only):
  python -I stable_ready_compare.py <candidate.json> ... --baseline <current.json> ...
      [--screen-pair <current.json> <candidate.json>] [--focus-part P38z] --out <compare.json>
Writes ``<compare>.json`` (meta, summary per candidate, rows) and ``<compare>_rows.csv``.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:  # python -I drops the script directory from sys.path
    sys.path.insert(0, str(HERE))

import screen_candidate_compare as screen  # noqa: E402

BASELINE_CANDIDATE = "current"
READY_PHASE = "ready"
FAULT_PHASES = ("fault", "fault_reground")  # = s9_slope_fix_candidates.FAULT_PHASES
SAFE_STOP_VERDICT = "stroke_limited_stop"  # spec 427.9, neither pass nor fail
GUARD_STOP_PART = "P36s"  # acted part of the spec 427.9 soil-guard stop

END_ATTITUDE_INCREASE_MAX_DEG = 0.02  # Z-3
READY_DELAY_MAX_S = 5.0  # Z-4, per row
READY_DELAY_MEDIAN_MAX_S = 0.0  # Z-4, median over the focus-part rows
DEFAULT_FOCUS_PART = "P38z"
KEPT_FAIL_TO_PASS_IDS = (  # spec 429.7: stage 1 h6 fail -> pass rows that must stay fixed
    "H6|J2|B|top|flat|m1.1",
    "H6|J1|A|top|flat|m1.2",
    "H6|J1|A|bottom|flat|m1.2",
)

# Mirror of s9_slope_fix_candidates.has_candidate_acted (not imported: that module pulls the
# controller stack, this script stays standard-library only).
FIX_EVENT_PREFIX = "FIX_"
S4_STROKE_EVENT = "WARN_CRAWLER_LIFTOFF_UNCONFIRMED:stroke"
RECORD_ONLY_FIX_EVENTS = ("FIX_LOC_REVOKE_SKIPPED",)

BASIS_PHASE_EVENTS = "phase_events"
BASIS_FIRST_READY = "first_ready_final_ready"
BASIS_NO_STABLE_READY = "no_stable_ready"
ATTITUDE_BASIS_MEAN = "stable_ready_mean"
ATTITUDE_BASIS_END = "end_instant"

STATUS_IDLE = "idle"
STATUS_FOCUS = "focus_acted"
STATUS_OTHER = "other_acted"


@dataclass(frozen=True)
class RunOutcome:
    """What the comparison needs from one run, whatever result format it came from."""

    suite: str
    case_id: str
    candidate: str
    verdict: str | None
    is_passed: bool
    command_hash: str | None
    final_phase: str | None
    t_first_ready_s: float | None
    t_first_done_s: float | None
    t_stable_ready_s: float | None
    ready_basis: str
    end_attitude_deg: tuple[float, float] | None
    attitude_basis: str
    acted_parts: tuple[str, ...]
    is_acted: bool

    @property
    def key(self) -> tuple[str, str]:
        return (self.suite, self.case_id)

    @property
    def has_stable_ready(self) -> bool:
        return self.t_stable_ready_s is not None

    @property
    def is_fault(self) -> bool:
        return self.final_phase in FAULT_PHASES

    @property
    def is_safe_stop(self) -> bool:
        return self.verdict == SAFE_STOP_VERDICT

    @property
    def is_guard_stop(self) -> bool:
        """The spec 427.9 soil-guard stop acted; it ends in a FAULT phase by design."""
        return GUARD_STOP_PART in self.acted_parts


# ------------------------------------------------------------------ stable READY of one run
def stable_ready_from_phase_events(phase_events: list) -> float | None:
    """Time of the last phase transition when it goes into READY, else None."""
    if not phase_events:
        return None
    t_s, phase = phase_events[-1]
    return float(t_s) if str(phase).lower() == READY_PHASE else None


def stable_ready(
    final_phase: str | None, t_first_ready_s: float | None, phase_events: list | None
) -> tuple[float | None, str]:
    """Stable READY time and its basis (see the module docstring)."""
    if phase_events:
        t_stable_s = stable_ready_from_phase_events(phase_events)
        return t_stable_s, BASIS_PHASE_EVENTS if t_stable_s is not None else BASIS_NO_STABLE_READY
    if final_phase == READY_PHASE and t_first_ready_s is not None:
        return float(t_first_ready_s), BASIS_FIRST_READY
    return None, BASIS_NO_STABLE_READY


def stable_attitude(source: dict, has_stable_ready: bool) -> tuple[tuple[float, float] | None, str]:
    """End attitude [deg] of a run with a stable READY: the READY-interval mean when recorded."""
    if not has_stable_ready:
        return None, ATTITUDE_BASIS_END
    mean_deg = source.get("stable_ready_att_mean_deg")
    if mean_deg is not None:
        return (float(mean_deg[0]), float(mean_deg[1])), ATTITUDE_BASIS_MEAN
    end_deg = source.get("att_end_deg")
    if end_deg is None:
        return None, ATTITUDE_BASIS_END
    return (float(end_deg[0]), float(end_deg[1])), ATTITUDE_BASIS_END


def _lookup(record: dict, name: str):
    """Field of a record at the top level or under ``metrics``."""
    if name in record:
        return record[name]
    return (record.get("metrics") or {}).get(name)


# ----------------------------------------------------------------------- wrapper records
def wrapper_acted_parts(record: dict) -> tuple[str, ...]:
    """Combination parts that acted (= s9_slope_fix_candidates.acted_parts)."""
    metrics = record.get("metrics") or {}
    floor_twist = metrics.get("p37") or {}
    parts = []
    if (metrics.get("p36s") or {}).get("stop"):
        parts.append("P36s")
    if floor_twist.get("applied"):
        parts.append("P37t")
    if floor_twist.get("flat_margins"):
        parts.append("R4c")
    if (metrics.get("p38") or {}).get("clamp_count"):
        parts.append("P38z")
    return tuple(parts)


def _has_fix_event(metrics: dict) -> bool:
    for _, name in metrics.get("fix_events") or []:
        is_fix = name.startswith((FIX_EVENT_PREFIX, S4_STROKE_EVENT))
        if is_fix and name.split(":", 1)[0] not in RECORD_ONLY_FIX_EVENTS:
            return True
    return False


def has_wrapper_candidate_acted(record: dict) -> bool:
    """Any candidate fix changed the run (= s9_slope_fix_candidates.has_candidate_acted)."""
    metrics = record.get("metrics") or {}
    if metrics.get("e3_applied") or (metrics.get("p36") or {}).get("actions"):
        return True
    if wrapper_acted_parts(record):
        return True
    return _has_fix_event(metrics)


def wrapper_outcome(record: dict) -> RunOutcome:
    """Outcome of one ``s9_slope_fix_candidates.py`` record."""
    final_phase = record.get("final_phase")
    t_stable_s, ready_basis = stable_ready(
        final_phase, record.get("t_ready_s"), _lookup(record, "phase_events")
    )
    attitude_source = {
        "stable_ready_att_mean_deg": _lookup(record, "stable_ready_att_mean_deg"),
        "att_end_deg": record.get("att_end_deg"),
    }
    end_attitude, attitude_basis = stable_attitude(attitude_source, t_stable_s is not None)
    return RunOutcome(
        suite=record["suite"],
        case_id=record["id"],
        candidate=record["candidate"],
        verdict=record.get("verdict"),
        is_passed=bool(record.get("passed")),
        command_hash=record.get("hash"),
        final_phase=final_phase,
        t_first_ready_s=record.get("t_ready_s"),
        t_first_done_s=_lookup(record, "t_first_done_s"),
        t_stable_ready_s=t_stable_s,
        ready_basis=ready_basis,
        end_attitude_deg=end_attitude,
        attitude_basis=attitude_basis,
        acted_parts=wrapper_acted_parts(record),
        is_acted=has_wrapper_candidate_acted(record),
    )


def load_wrapper_outcomes(paths: list[Path], want_baseline: bool) -> tuple[list[RunOutcome], list]:
    """Baseline ("current") or candidate outcomes of wrapper files; error records are skipped."""
    outcomes, skipped = [], []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload.get("records") or []:
            is_baseline = record.get("candidate") == BASELINE_CANDIDATE
            if is_baseline != want_baseline:
                continue
            if "error" in record:
                skipped.append(f"{path.name}:{record.get('suite')}|{record.get('id')}: error")
                continue
            outcomes.append(wrapper_outcome(record))
    return outcomes, skipped


# --------------------------------------------------------------------------- event screens
def screen_suite_label(candidate_path: Path) -> str:
    """Suite label of a screen pair: the candidate file stem (keeps r67 main / top apart)."""
    return f"screen:{candidate_path.stem}"


def screen_outcome(suite: str, branch_key: str, entry: dict, candidate: str) -> RunOutcome:
    """Outcome of one study A / r67 branch run (``screen_candidate_compare.index_runs`` entry)."""
    run = entry["run"]
    record = run.get("candidate_record") or {}
    final_phase = run.get("final_phase")
    t_stable_s, ready_basis = stable_ready(
        final_phase, run.get("t_ready_back_s"), run.get("phase_events")
    )
    end_attitude, attitude_basis = stable_attitude(run, t_stable_s is not None)
    return RunOutcome(
        suite=suite,
        case_id=branch_key,
        candidate=candidate,
        verdict="pass" if run.get("pass") else "fail",
        is_passed=bool(run.get("pass")),
        command_hash=entry["hash"],
        final_phase=final_phase,
        t_first_ready_s=run.get("t_ready_back_s"),
        t_first_done_s=None,
        t_stable_ready_s=t_stable_s,
        ready_basis=ready_basis,
        end_attitude_deg=end_attitude,
        attitude_basis=attitude_basis,
        acted_parts=tuple(record.get("acted_parts") or ()),
        is_acted=bool(record.get("acted")),
    )


def _screen_candidate_name(payload: dict) -> str:
    names = sorted(
        {job["candidate"] for job in payload.get("results") or [] if job.get("candidate")}
    )
    if not names:
        return "unknown"
    return "|".join(names)


def _screen_side(path: Path, suite: str) -> tuple[list[RunOutcome], list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    candidate = _screen_candidate_name(payload)
    outcomes, skipped = [], []
    for branch_key, entry in screen.index_runs(payload).items():
        if "run" not in entry:
            skipped.append(f"{path.name}:{branch_key}: error")
            continue
        outcomes.append(screen_outcome(suite, branch_key, entry, candidate))
    return outcomes, skipped


def load_screen_pair(current_path: Path, candidate_path: Path):
    """Baseline and candidate outcomes of one screen pair, under one suite label."""
    suite = screen_suite_label(candidate_path)
    baseline, skipped_before = _screen_side(current_path, suite)
    candidates, skipped_after = _screen_side(candidate_path, suite)
    return baseline, candidates, skipped_before + skipped_after


# ------------------------------------------------------------------------------ comparison
def _max_abs(attitude_deg: tuple[float, float] | None) -> float | None:
    return None if attitude_deg is None else max(abs(value) for value in attitude_deg)


def _difference(after: float | None, before: float | None, digits: int) -> float | None:
    return None if after is None or before is None else round(after - before, digits)


def _acted_status(after: RunOutcome, focus_part: str) -> str:
    if not after.is_acted:
        return STATUS_IDLE
    return STATUS_FOCUS if focus_part in after.acted_parts else STATUS_OTHER


def _round_attitude(attitude_deg: tuple[float, float] | None) -> list[float] | None:
    return None if attitude_deg is None else [round(value, 4) for value in attitude_deg]


def compare_outcomes(before: RunOutcome, after: RunOutcome, focus_part: str) -> dict:
    """One row: candidate ``after`` against its "current" ``before``."""
    is_comparable = before.has_stable_ready and after.has_stable_ready
    is_hash_same = before.command_hash is not None and before.command_hash == after.command_hash
    is_new_fault = after.is_fault and not before.is_fault
    attitude_increase = _difference(
        _max_abs(after.end_attitude_deg), _max_abs(before.end_attitude_deg), 4
    )
    return {
        "suite": after.suite,
        "id": after.case_id,
        "candidate": after.candidate,
        "status": _acted_status(after, focus_part),
        "acted_parts": "+".join(after.acted_parts),
        "focus_only": after.acted_parts == (focus_part,),  # attribution inside a combination
        "comparable": is_comparable,
        "hash_same": is_hash_same,
        "verdict_before": before.verdict,
        "verdict_after": after.verdict,
        "pass_to_fail": before.is_passed and not after.is_passed and not after.is_safe_stop,
        "pass_to_safe_stop": before.is_passed and after.is_safe_stop,
        "fail_to_pass": not before.is_passed and after.is_passed,
        # a spec 427.9 guard stop ends in a FAULT phase by design; it is counted apart
        "new_fault": is_new_fault and not after.is_guard_stop,
        "new_fault_guard_stop": is_new_fault and after.is_guard_stop,
        "final_phase_before": before.final_phase,
        "final_phase_after": after.final_phase,
        "t_first_done_before_s": before.t_first_done_s,
        "t_first_done_after_s": after.t_first_done_s,
        "d_first_ready_s": _difference(after.t_first_ready_s, before.t_first_ready_s, 3),
        "t_stable_ready_before_s": before.t_stable_ready_s,
        "t_stable_ready_after_s": after.t_stable_ready_s,
        "d_stable_ready_s": _difference(after.t_stable_ready_s, before.t_stable_ready_s, 3)
        if is_comparable
        else None,
        "att_before_deg": _round_attitude(before.end_attitude_deg),
        "att_after_deg": _round_attitude(after.end_attitude_deg),
        "d_att_abs_deg": attitude_increase if is_comparable else None,
        "ready_basis": f"{before.ready_basis}/{after.ready_basis}",
        "attitude_basis": f"{before.attitude_basis}/{after.attitude_basis}",
    }


def pair_rows(
    baseline: list[RunOutcome], candidates: list[RunOutcome], focus_part: str
) -> tuple[list[dict], list[str], list[str]]:
    """Rows of every candidate outcome with a baseline; missing baselines and duplicates."""
    baseline_by_key: dict[tuple[str, str], RunOutcome] = {}
    duplicates = []
    for outcome in baseline:
        known = baseline_by_key.get(outcome.key)
        if known is not None and known.command_hash != outcome.command_hash:
            duplicates.append(f"baseline {outcome.suite}|{outcome.case_id}: hashes differ")
            continue
        baseline_by_key.setdefault(outcome.key, outcome)
    rows, missing = [], []
    for outcome in candidates:
        before = baseline_by_key.get(outcome.key)
        if before is None:
            missing.append(f"{outcome.candidate}:{outcome.suite}|{outcome.case_id}")
            continue
        rows.append(compare_outcomes(before, outcome, focus_part))
    return rows, missing, duplicates


# --------------------------------------------------------------------------------- summary
def _z1(rows: list[dict]) -> dict:
    idle = [row for row in rows if row["status"] == STATUS_IDLE]
    differing = [f"{row['suite']}|{row['id']}" for row in idle if not row["hash_same"]]
    return {"pass": not differing, "idle": len(idle), "idle_hash_differs": differing}


def _z2(rows: list[dict]) -> dict:
    pass_to_fail = [f"{row['suite']}|{row['id']}" for row in rows if row["pass_to_fail"]]
    new_fault = [f"{row['suite']}|{row['id']}" for row in rows if row["new_fault"]]
    guard_faults = [f"{row['suite']}|{row['id']}" for row in rows if row["new_fault_guard_stop"]]
    safe_stops = [f"{row['suite']}|{row['id']}" for row in rows if row["pass_to_safe_stop"]]
    return {
        "pass": not pass_to_fail and not new_fault,
        "pass_to_fail": pass_to_fail,
        "new_fault": new_fault,
        "new_fault_guard_stop": guard_faults,
        "pass_to_safe_stop": safe_stops,
        "fail_to_pass": sum(row["fail_to_pass"] for row in rows),
    }


def _row_label(row: dict, value_key: str) -> str:
    return f"{row['suite']}|{row['id']} ({row['acted_parts']}): {row[value_key]:+}"


def _z3(focus_rows: list[dict]) -> dict:
    over = [
        _row_label(row, "d_att_abs_deg")
        for row in focus_rows
        if row["d_att_abs_deg"] is not None
        and row["d_att_abs_deg"] > END_ATTITUDE_INCREASE_MAX_DEG + 1e-12
    ]
    increases = [row["d_att_abs_deg"] for row in focus_rows if row["d_att_abs_deg"] is not None]
    return {
        "pass": not over,
        "limit_deg": END_ATTITUDE_INCREASE_MAX_DEG,
        "n": len(increases),
        "max_increase_deg": max(increases) if increases else None,
        "over_limit": over,
    }


def _z4(focus_rows: list[dict]) -> dict:
    delays = [row["d_stable_ready_s"] for row in focus_rows if row["d_stable_ready_s"] is not None]
    over = [
        _row_label(row, "d_stable_ready_s")
        for row in focus_rows
        if row["d_stable_ready_s"] is not None
        and row["d_stable_ready_s"] > READY_DELAY_MAX_S + 1e-9
    ]
    median_s = statistics.median(delays) if delays else None
    is_median_ok = median_s is None or median_s <= READY_DELAY_MEDIAN_MAX_S + 1e-9
    return {
        "pass": not over and is_median_ok,
        "limit_s": READY_DELAY_MAX_S,
        "n": len(delays),
        "median_s": median_s,
        "max_s": max(delays) if delays else None,
        "over_limit": over,
    }


def _kept_fail_to_pass(rows: list[dict], kept_ids: tuple[str, ...]) -> dict:
    by_id = {row["id"]: row for row in rows}
    status = {}
    for case_id in kept_ids:
        row = by_id.get(case_id)
        if row is None:
            status[case_id] = "missing"
        else:
            status[case_id] = "kept" if row["fail_to_pass"] else "lost"
    if "lost" in status.values():
        verdict = False
    elif "missing" in status.values():
        verdict = None
    else:
        verdict = True
    return {"pass": verdict, "rows": status}


def _basis_counts(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["ready_basis"]] = counts.get(row["ready_basis"], 0) + 1
    return counts


def _overall(criteria: dict) -> str:
    verdicts = [block["pass"] for block in criteria.values()]
    if False in verdicts:
        return "fail"
    return "incomplete" if None in verdicts else "pass"


def summarize_candidate(rows: list[dict], kept_ids: tuple[str, ...]) -> dict:
    """Z-1 .. Z-4, the kept fail -> pass rows and the row counts of one candidate."""
    focus_rows = [row for row in rows if row["status"] == STATUS_FOCUS]
    focus_comparable = [row for row in focus_rows if row["comparable"]]
    focus_only_comparable = [row for row in focus_comparable if row["focus_only"]]
    criteria = {
        "Z-1": _z1(rows),
        "Z-2": _z2(rows),
        "Z-3": _z3(focus_comparable),
        "Z-4": _z4(focus_comparable),
        "kept_fail_to_pass": _kept_fail_to_pass(rows, kept_ids),
    }
    return {
        "verdict": _overall(criteria),
        "n": len(rows),
        "focus_acted": len(focus_rows),
        "focus_comparable": len(focus_comparable),
        "focus_incomparable": [
            f"{row['suite']}|{row['id']} ({row['final_phase_before']}/{row['final_phase_after']})"
            for row in focus_rows
            if not row["comparable"]
        ],
        "other_acted": sum(row["status"] == STATUS_OTHER for row in rows),
        "ready_basis_counts": _basis_counts(rows),
        "criteria": criteria,
        # record only: Z-3 / Z-4 on the rows where the focus part acted alone
        "focus_only": {"Z-3": _z3(focus_only_comparable), "Z-4": _z4(focus_only_comparable)},
    }


def summarize(rows: list[dict], kept_ids: tuple[str, ...]) -> dict:
    by_candidate: dict[str, list[dict]] = {}
    for row in rows:
        by_candidate.setdefault(row["candidate"], []).append(row)
    return {name: summarize_candidate(group, kept_ids) for name, group in by_candidate.items()}


# ------------------------------------------------------------------------------------ main
def build_comparison(
    candidate_paths: list[Path],
    baseline_paths: list[Path],
    screen_pairs: list[tuple[Path, Path]],
    focus_part: str = DEFAULT_FOCUS_PART,
    kept_ids: tuple[str, ...] = KEPT_FAIL_TO_PASS_IDS,
) -> dict:
    """Rows and per-candidate summary of all inputs."""
    baseline, skipped_baseline = load_wrapper_outcomes(baseline_paths, want_baseline=True)
    candidates, skipped_candidates = load_wrapper_outcomes(candidate_paths, want_baseline=False)
    skipped = skipped_baseline + skipped_candidates
    for current_path, candidate_path in screen_pairs:
        screen_baseline, screen_candidates, screen_skipped = load_screen_pair(
            current_path, candidate_path
        )
        baseline += screen_baseline
        candidates += screen_candidates
        skipped += screen_skipped
    rows, missing, duplicates = pair_rows(baseline, candidates, focus_part)
    meta = {
        "rule": "spec 429.8 stable READY (Z-1..Z-4 of 429.4)",
        "script": "04_scripts/03_control/s9/stable_ready_compare.py",
        "candidate_files": [str(path) for path in candidate_paths],
        "baseline_files": [str(path) for path in baseline_paths],
        "screen_pairs": [[str(a), str(b)] for a, b in screen_pairs],
        "focus_part": focus_part,
        "kept_fail_to_pass_ids": list(kept_ids),
        "no_baseline": missing,
        "skipped": skipped,
        "baseline_conflicts": duplicates,
    }
    return {"meta": meta, "summary": summarize(rows, kept_ids), "rows": rows}


def write_outputs(out_path: Path, result: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=1), encoding="utf-8")
    rows = result["rows"]
    if not rows:
        return
    csv_path = out_path.with_name(out_path.stem + "_rows.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("candidates", nargs="*", type=Path, help="wrapper candidate result files")
    parser.add_argument(
        "--baseline",
        nargs="+",
        type=Path,
        default=[],
        help='wrapper files holding the "current" records',
    )
    parser.add_argument(
        "--screen-pair",
        nargs=2,
        type=Path,
        action="append",
        default=[],
        metavar=("CURRENT", "CANDIDATE"),
        help="study A / r67 screen files",
    )
    parser.add_argument(
        "--focus-part",
        default=DEFAULT_FOCUS_PART,
        help="acted part whose rows Z-3 / Z-4 judge (default P38z)",
    )
    parser.add_argument(
        "--keep-fixed",
        default=";".join(KEPT_FAIL_TO_PASS_IDS),
        help="semicolon list of case ids that must stay fail -> pass",
    )
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    kept_ids = tuple(case_id for case_id in args.keep_fixed.split(";") if case_id)
    result = build_comparison(
        args.candidates,
        args.baseline,
        [tuple(pair) for pair in args.screen_pair],
        args.focus_part,
        kept_ids,
    )
    write_outputs(args.out, result)
    for name, block in result["summary"].items():
        criteria = {key: value["pass"] for key, value in block["criteria"].items()}
        print(name, block["verdict"], json.dumps(criteria))


if __name__ == "__main__":
    main()
