"""H-7' of the LAS-b resume verification (sealed ``las_targeted_rules_rev4.md`` 2 and 3); the same
comparison is K-6 of T-3 (sealed ``las_targeted_rules_rev3.md`` 3, applied with the rev4 wording).

A line is an H-7' target when the new run has the LAS-b start event ``INFO_LIFTOFF_SLOW`` (not
``_END``), a stored baseline line of the same key (a run before the LAS-b switch) exists and its
batch has a declared format (:data:`BATCH_FORMATS`). First runs (:data:`FIRST_RUN_BATCHES`) are
never targets; their fired state is recorded only.

Criteria (rev4 2, a violation if any holds):
  C2     baseline pass / allowed_stop -> new fail; a baseline fail whose new fail items are not a
         subset of its own. A missing verdict on either side is a violation.
  C3     the ``FAULT*`` names of the new run are not a subset of the baseline's; a missing event
         record on either side is a violation.
  C4'    G6-2 true in the baseline and not true (false or None) in the new run.
  P3-2   P3-2 not failed in the baseline and failed or None in the new run (a FLAG is no failure).
  C5'-R  new READY - baseline READY > 5.0 s; baseline a number and new None is a violation, both
         None is not.
  C5'-S  new stroke max - baseline > 0.001 m; None on either side is a violation.
A quantity the batch format does not have ("형식 없음", extractor None) is not judged and is listed
as such. For G6-2 and P3-2 a baseline row without the item does not take the criterion (rev4a 2:
"기준 항목 없음", listed per line); an item that is there and not failed with a new None is a
violation. A line whose event list may be cut (``incomplete``: at the stored limit or flagged)
is undecidable and stops (rev4a 5, :class:`UndecidableLine`).

Field table (rev4a 1 / 5, rev4b): the G6-2 item is ``G6-2_loc`` everywhere (the rev3 key list's
``G6-2`` field is void). Declared: J-1, r72 (J-10 .. J-12), J-9 / J-13 main (``judged`` written
by the sealed judge, with ``judged.judge`` = name, version, sha256; without it C2 "verdict
missing"), J-3' (``d1s_judge.json`` ``cases.<id>``; events = the unfiltered names of Chrono
``result.json`` ``events``, whose count the caller adds as ``result_events_count`` and which
must match, rev4b 2), J-7 slope (``u3_slope_V0.json`` ``records[i]``; fired and FAULT from the
rerun's ``v5.las_events``, the baseline's FAULT from ``warnings``; a rerun without
``las_events`` is undecidable, rev4b 3), and by rev4c 1 - 3 J-5 / J-6 (:func:`jp_case_line`:
the case's ``rows`` + ``metrics``, fired and new FAULT from the rerun's ``las_events`` =
``run_S8C`` ``las_events.json``, baseline FAULT = ``metrics.events`` FAULT names plus failed
FAULT rows; no C4', P3-2), grid_vb (no C4', P3-2, C5'-S) and J-15 (``judged`` by revision 12,
events of ``result.json``; no C4'). Every batch result carries the silent-line hash check
(rev4c 4, :func:`silent_hash_check`); a difference stops the batch.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum

READY_INCREASE_LIMIT_S = 5.0
STROKE_INCREASE_LIMIT_M = 0.001
MM_PER_M = 1000.0
START_EVENT = "INFO_LIFTOFF_SLOW"
"""LAS-b start (``INFO_LIFTOFF_SLOW:<leg>``); ``INFO_LIFTOFF_SLOW_END:<reason>`` is its end."""
FAULT_PREFIX = "FAULT"
VERDICT_FAIL = "fail"
NOT_FAILED_VERDICTS = ("pass", "allowed_stop")
CRITERIA = ("C2", "C3", "C4'", "P3-2", "C5'-R", "C5'-S")


class FormatStatus(StrEnum):
    """Whether a batch's field table may be used for a verdict."""

    DECLARED = "declared"
    """Rev4 3 names every field; usable."""
    DRAFT = "draft: control-expert confirmation pending"
    """A "형식에 따름" cell or a batch whose table is still to be confirmed (rev4 3 note): the
    draft must not judge a run until control-expert confirms it."""


class P32State(StrEnum):
    OK = "ok"
    FAILED = "failed"


Extractor = Callable[[dict], object]


@dataclass(frozen=True)
class BatchFormat:
    """Where one batch's lines keep the quantities of rev4 2 (``None`` = "형식 없음").

    Attributes:
        name: Rev4 3 work number and batch.
        status: :class:`FormatStatus`.
        verdict: The line's verdict (``pass`` / ``allowed_stop`` / ``fail``).
        fail_items: The failed items of a ``fail`` verdict.
        event_names: The event names (heads before ``:``) of the run, None = no record.
        g62: The G6-2 item (True / False / None).
        p32: The P3-2 item as :class:`P32State` (None = no value).
        ready_s: The first READY time [s].
        stroke_m: The largest stroke [m].
    """

    name: str
    status: FormatStatus
    verdict: Extractor | None
    fail_items: Extractor | None
    event_names: Extractor | None
    g62: Extractor | None
    p32: Extractor | None
    ready_s: Extractor | None
    stroke_m: Extractor | None
    incomplete: Callable[[dict], str | None] | None = None
    """Why a line's event list may be cut (then the line is undecidable, rev4a 5), or None."""
    incomplete_new: Callable[[dict], str | None] | None = None
    """The same for the rerun line only (a field the stored baseline never had, rev4b 3)."""
    incomplete_base: Callable[[dict], str | None] | None = None
    """The same for the baseline line only (no FAULT source at all, rev4c 3)."""
    fired_events: Extractor | None = None
    """The events that mark the rerun line fired (None: ``event_names``)."""

    @property
    def absent(self) -> list[str]:
        """The rev4 2 criteria this format has no field for ("형식 없음")."""
        fields = {"C4'": self.g62, "P3-2": self.p32, "C5'-R": self.ready_s,
                  "C5'-S": self.stroke_m}
        return [name for name, field in fields.items() if field is None]


# ------------------------------------------------------------------------------- extractors
def _get(record: dict | None, *path):
    """``record[path[0]][path[1]]...``; None when a step is missing."""
    value = record
    for step in path:
        if not isinstance(value, dict):
            return None
        value = value.get(step)
    return value


def event_heads(names: Iterable | None) -> set[str] | None:
    """Event names cut at the first ``:``; ``names`` may be a count dict, names or
    ``(t, name)`` pairs. None stays None (no event record)."""
    if names is None:
        return None
    heads = set()
    for item in names:
        name = item[1] if isinstance(item, list | tuple) else item
        heads.add(str(name).split(":")[0])
    return heads


def is_fired(names: Iterable | None) -> bool:
    """The run has the LAS-b start event (``INFO_LIFTOFF_SLOW``, not ``_END``)."""
    return START_EVENT in (event_heads(names) or set())


LAS_EVENTS_KEY = "las_events"
"""Record-only field of a rerun (rev4b 3 / 4): ``liftoff_slow`` = every ``INFO_LIFTOFF_SLOW*``
event as ``[t_s, name]``, ``fault_names`` = the ``FAULT*`` names, ``event_count``."""


def las_events_record(events: Iterable) -> dict:
    """The ``las_events`` record of a run's controller events (``C2Event``-like objects with
    ``t_s`` / ``name`` or ``(t_s, name)`` pairs); reads them only (record, no command change)."""
    pairs = []
    for event in events:
        if hasattr(event, "t_s"):
            pairs.append((float(event.t_s), str(event.name)))
        else:
            pairs.append((float(event[0]), str(event[1])))
    return {"liftoff_slow": [[t_s, name] for t_s, name in pairs if name.startswith(START_EVENT)],
            "fault_names": sorted({name for _, name in pairs if name.startswith(FAULT_PREFIX)}),
            "event_count": len(pairs)}


def _las_events_names(record: dict | None) -> list[str] | None:
    """The names in a ``las_events`` record (LAS-b events and FAULT names), None without it."""
    if not isinstance(record, dict):
        return None
    return [*record.get("fault_names", []), *(name for _, name in record.get("liftoff_slow", []))]


def _d1_p32(line: dict) -> P32State | None:
    value = _get(line, "d1", "items", "P3-2")
    if value is None:
        return None
    return P32State.OK if value is True else P32State.FAILED


def _r72_verdict(line: dict) -> str | None:
    passed = _get(line, "base", "pass")
    if passed is None:
        return None
    return "pass" if passed else VERDICT_FAIL


def _r72_fail_items(line: dict) -> list[str] | None:
    gates = _get(line, "base", "gates")
    if gates is None:
        return None
    return sorted(name for name, ok in gates.items() if ok is False)


def _r72_p32(line: dict) -> P32State | None:
    value = _get(line, "base", "late_loc_reapproach", "verdict")
    if value is None:
        return None
    return P32State.FAILED if value == VERDICT_FAIL else P32State.OK  # "flag" is no failure


def _r79_stroke_m(line: dict) -> float | None:
    value = _get(line, "r79", "max_true_stroke_mm")
    return None if value is None else float(value) / MM_PER_M


JUDGE_IDENTITY_FIELDS = ("name", "version", "sha256")
"""rev4a 5: a ``judged`` block counts only with the sealed judge's name, version and sha256."""


def judged_by(line: dict) -> dict | None:
    """``line["judged"]["judge"]`` when it names the judge fully, else None."""
    judge = _get(line, "judged", "judge")
    if not isinstance(judge, dict) or any(not judge.get(k) for k in JUDGE_IDENTITY_FIELDS):
        return None
    return judge


def _judged(field: str) -> Extractor:
    """A value the batch's sealed judge writes into ``line["judged"]`` before H-7' (rev4 3 /
    rev4a 5); without the judge's identity the value is None (C2: "verdict missing")."""
    return lambda line: None if judged_by(line) is None else _get(line, "judged", field)


D1_EVENTS_LIMIT = 400
"""``verdict_runs._finish`` keeps the first 400 events; ``event_names`` counts those."""
R79_EVENTS_LIMIT = 200
"""``r79_sensor_screen`` keeps the first 200 events (``INFO_PRESSURE*`` / ``shadow*`` left out)."""
INCOMPLETE_KEYS = ("events_incomplete", "events_truncated", "incomplete")


def _flagged_incomplete(line: dict) -> str | None:
    flagged = [key for key in INCOMPLETE_KEYS if line.get(key)]
    return f"flagged {flagged}" if flagged else None


def _d1_incomplete(line: dict) -> str | None:
    names = line.get("event_names")
    if names is not None and sum(names.values()) >= D1_EVENTS_LIMIT:
        return f"event_names count {sum(names.values())} at the {D1_EVENTS_LIMIT} limit"
    return _flagged_incomplete(line)


def _r72_incomplete(line: dict) -> str | None:
    events = line.get("events")
    if events is not None and len(events) >= R79_EVENTS_LIMIT:
        return f"{len(events)} events at the {R79_EVENTS_LIMIT} limit"
    return _flagged_incomplete(line)


D1_FORMAT = BatchFormat(
    name="J-1 D-1 harness 868", status=FormatStatus.DECLARED,
    verdict=lambda line: _get(line, "d1", "verdict"),
    fail_items=lambda line: _get(line, "d1", "fail_items"),
    event_names=lambda line: line.get("event_names"),
    g62=lambda line: _get(line, "d1", "items", "G6-2_loc"),  # rev4 writes "G6-2" (docstring)
    p32=_d1_p32,
    ready_s=lambda line: _get(line, "d1", "t_ready_s"),
    stroke_m=lambda line: _get(line, "d1", "stroke_max_m"),
    incomplete=_d1_incomplete,
)
R72_FORMAT = BatchFormat(
    name="J-10 / J-11 / J-12 r72 (dg3 v4_on, dg3 off, stage-2 noise)",
    status=FormatStatus.DECLARED,
    verdict=_r72_verdict, fail_items=_r72_fail_items,
    event_names=lambda line: line.get("events"),
    g62=lambda line: _get(line, "base", "gates", "G6-2_loc"),
    p32=_r72_p32,
    ready_s=lambda line: _get(line, "base", "t_ready_s"),
    stroke_m=_r79_stroke_m,
    incomplete=_r72_incomplete,
)
READY_ONLY_FORMAT = BatchFormat(
    name="J-9 U-9 V0 / J-13 main and pressure_only", status=FormatStatus.DECLARED,
    verdict=_judged("verdict"), fail_items=_judged("fail_items"),
    event_names=lambda line: line.get("event_names"),
    g62=None, p32=None,
    ready_s=lambda line: _get(line, "values", "times", "t_first_ready_s"),
    stroke_m=None,
)


def _d1s_fail_items(case: dict) -> list[str] | None:
    """J-3' failed items: false gates plus false / ``fail`` P3 checks (rev4a 5)."""
    gates, checks = case.get("gates"), case.get("p3_checks")
    if gates is None or checks is None:
        return None
    failed = [name for name, ok in gates.items() if ok is False]
    failed += [name for name, value in checks.items() if value is False or value == VERDICT_FAIL]
    return sorted(failed)


def _d1s_p32(case: dict) -> P32State | None:
    value = _get(case, "p3_checks", "P3-2_verdict")
    if value is None:
        return None
    return P32State.FAILED if value == VERDICT_FAIL else P32State.OK


def _mm_to_m(path: tuple[str, ...]) -> Extractor:
    def extract(line: dict) -> float | None:
        value = _get(line, *path)
        return None if value is None else float(value) / MM_PER_M

    return extract


RESULT_EVENTS_COUNT_KEY = "result_events_count"
"""``len(result.json["events"])`` of the Chrono case, written beside the row by the caller
(:func:`with_result_events_count`) so the row's event list can be checked whole (rev4b 2)."""


def with_result_events_count(row: dict, result_json: dict) -> dict:
    """``row`` with :data:`RESULT_EVENTS_COUNT_KEY` from the case's ``result.json``."""
    return {**row, RESULT_EVENTS_COUNT_KEY: len(result_json.get("events") or [])}


def _events_count_mismatch(row: dict) -> str | None:
    """rev4b 2: the row's ``events`` must be the whole ``result.json`` list (count check)."""
    count = row.get(RESULT_EVENTS_COUNT_KEY)
    events = row.get("events")
    if count is None:
        return f"no {RESULT_EVENTS_COUNT_KEY} (result.json events not counted)"
    if events is None or len(events) != count:
        return f"{0 if events is None else len(events)} events != result.json {count}"
    return None


D1S_FORMAT = BatchFormat(
    name="J-3' D-1 Chrono SCM S-03 / S-04 (d1s_judge.json cases.<id>)",
    status=FormatStatus.DECLARED,  # rev4b 2: stroke_max_mm is in the stored and new rows
    verdict=lambda case: case.get("verdict"), fail_items=_d1s_fail_items,
    event_names=lambda case: case.get("events"),  # d1s_judge.py 152: names, unfiltered
    g62=lambda case: _get(case, "gates", "G6-2_loc"), p32=_d1s_p32,
    ready_s=lambda case: case.get("t_ready_rel_s"),
    stroke_m=_mm_to_m(("stroke_max_mm",)),
    incomplete=_events_count_mismatch,
)


def _u3_events(record: dict) -> list[str] | None:
    """J-7 FAULT names: the rerun's ``v5.las_events`` (rev4b 3), the stored baseline's
    ``warnings`` (it has no event list; ``FAULT*`` names are in it, rev4a 5)."""
    names = _las_events_names(_get(record, "v5", LAS_EVENTS_KEY))
    if names is not None:
        return names
    warnings = record.get("warnings")
    return None if warnings is None else list(warnings)


def _u3_no_las_events(record: dict) -> str | None:
    if _get(record, "v5", LAS_EVENTS_KEY) is None:
        return f"rerun record without v5.{LAS_EVENTS_KEY} (fired state unknown, rev4b 3)"
    return None


def _u3_p32(record: dict) -> P32State | None:
    value = _get(record, "late_loc_reapproach", "verdict")
    if value is None:
        return None
    return P32State.FAILED if value == VERDICT_FAIL else P32State.OK


U3_SLOPE_FORMAT = BatchFormat(
    name="J-7 U-3 slope V0 110 (u3_slope_V0.json records[i])",
    status=FormatStatus.DECLARED,  # rev4b 3: v5_rerun.run_record writes las_events
    verdict=lambda record: record.get("verdict"),
    fail_items=lambda record: record.get("failed_rows"),
    event_names=_u3_events,
    g62=None,  # no G6 gates in these records: 형식 없음 (rev4a 5)
    p32=_u3_p32,
    ready_s=lambda record: record.get("t_ready_s"),
    stroke_m=_mm_to_m(("max_stroke_mm",)),
    incomplete_new=_u3_no_las_events,
    fired_events=lambda record: _get(record, "v5", LAS_EVENTS_KEY, "liftoff_slow"),
)


C2_EVENT_REPR = re.compile(r"C2Event\(t_s=[-0-9.eE+]+, name='(.*)'\)")
"""``str(C2Event)`` as the jp ``metrics[i].events`` entries store it."""
FAULT_ROW_TOKEN = "fault"
"""A jp ``rows[]`` item about FAULTs (case-insensitive substring of ``item``, rev4c 3)."""


def jp_case_line(verify: dict, case: str, las_events: dict | None = None) -> dict:
    """One J-5 / J-6 line of a ``verify_v5jp_*.json``: the case's ``rows``, its ``metrics``
    entry and (rerun only) the run's ``las_events`` (``run_S8C`` ``las_events.json``).

    Raises:
        KeyError: The file has no metrics entry for ``case``.
    """
    metrics = next((m for m in verify.get("metrics") or [] if m.get("case") == case), None)
    if metrics is None:
        raise KeyError(f"no metrics for case {case!r}")
    rows = [row for row in verify.get("rows") or [] if row.get("case") in (case, None)]
    line = {"case": case, "rows": rows, "metrics": metrics}
    if las_events is not None:
        line[LAS_EVENTS_KEY] = las_events
    return line


def _jp_verdict(line: dict) -> str | None:
    rows = line.get("rows")
    if not rows:
        return None
    return "pass" if all(row.get("passed") is True for row in rows) else VERDICT_FAIL


def _jp_fail_items(line: dict) -> list[str] | None:
    rows = line.get("rows")
    return None if rows is None else sorted(str(row["item"]) for row in rows
                                            if row.get("passed") is False)


def _jp_metrics_event_names(line: dict) -> list[str] | None:
    events = _get(line, "metrics", "events")
    if events is None:
        return None
    names = []
    for entry in events:
        match = C2_EVENT_REPR.fullmatch(str(entry).strip())
        names.append(match.group(1) if match else str(entry))
    return names


def _jp_events(line: dict) -> list[str] | None:
    """C3 names: the rerun's ``las_events``; the baseline's FAULT names of ``metrics.events``
    together with its failed FAULT rows (rev4c 3: the union of what the record holds)."""
    if LAS_EVENTS_KEY in line:
        return _las_events_names(line[LAS_EVENTS_KEY])
    names = _jp_metrics_event_names(line)
    rows = line.get("rows")
    if names is None and rows is None:
        return None
    failed_fault_rows = [f"FAULT_ROW:{row['item']}" for row in rows or []
                         if FAULT_ROW_TOKEN in str(row.get("item", "")).lower()
                         and row.get("passed") is False]
    return [*(names or []), *failed_fault_rows]


def _jp_no_fault_source(line: dict) -> str | None:
    if _jp_metrics_event_names(line) is None and line.get("rows") is None:
        return "no FAULT source (metrics.events and rows both absent, rev4c 3)"
    return None


def _jp_stroke_m(line: dict) -> float | None:
    values = _get(line, "metrics", "stroke", "max_m")
    return None if not values else max(float(v) for v in values)


JP_FORMAT = BatchFormat(
    name="J-5 / J-6 verify_v5jp case line (rows + metrics, rigid L2b)",
    status=FormatStatus.DECLARED,  # rev4c 1
    verdict=_jp_verdict, fail_items=_jp_fail_items, event_names=_jp_events,
    g62=None, p32=None,  # rev4b 4: 형식 없음
    ready_s=lambda line: _get(line, "metrics", "ready_s"), stroke_m=_jp_stroke_m,
    incomplete_new=lambda line: None if line.get(LAS_EVENTS_KEY) is not None else (
        f"rerun line without {LAS_EVENTS_KEY} (rev4c 2)"),
    incomplete_base=_jp_no_fault_source,
    fired_events=lambda line: _get(line, LAS_EVENTS_KEY, "liftoff_slow"),
)
"""rev4c 1 - 3: the stored ``metrics[i].events`` (2 .. 3 entries) never mark a run fired; a
baseline FAULT row counts as ``FAULT_ROW:<item>`` (no event name, so a new FAULT name is never
covered by it: the safe side)."""


def _grid_fault_names(run: dict) -> list[str] | None:
    faults, warnings = run.get("fault_events"), run.get("warnings")
    if faults is None or warnings is None:
        return None
    return [*faults, *(name for name in warnings if str(name).startswith(FAULT_PREFIX))]


GRID_VB_FORMAT = BatchFormat(
    name="J-13 grid_vb results[i].runs[j]", status=FormatStatus.DECLARED,  # rev4c 1
    verdict=lambda run: None if run.get("pass") is None else (
        "pass" if run["pass"] else VERDICT_FAIL),
    fail_items=lambda run: None if run.get("gates") is None else sorted(
        name for name, ok in run["gates"].items() if ok is False),
    event_names=_grid_fault_names,
    g62=None, p32=None, stroke_m=None,  # rev4b 4: 형식 없음
    ready_s=lambda run: run.get("t_ready_back_s"),
    incomplete_new=lambda run: None if run.get(LAS_EVENTS_KEY) is not None else (
        f"rerun run without {LAS_EVENTS_KEY}"),
    fired_events=lambda run: _get(run, LAS_EVENTS_KEY, "liftoff_slow"),
)
"""rev4c 1: verdict ``pass``, failed items the false ``gates``, READY ``t_ready_back_s`` (after
the event; the row's ``base.t_ready`` is the prefix run's and is not used), fired from the
``las_events`` that ``r67_g1_screen.screen_job`` writes per run."""


def _p3b_stroke_m(result: dict) -> float | None:
    values = _get(result, "p3b", "P3-5_clearance_stroke", "s_motor_max_m")
    return None if not values else max(float(v) for v in values)


def _p3b_p32(result: dict) -> P32State | None:
    value = _get(result, "p3b", "checks", "P3-2_verdict")
    if value is None:
        return None
    return P32State.FAILED if value == VERDICT_FAIL else P32State.OK


def _result_events_names(result: dict) -> list[str] | None:
    events = result.get("events")
    return None if events is None else [event["name"] for event in events]


STAGE3_FORMAT = BatchFormat(
    name="J-15 stage-3 Chrono result.json (p3b)", status=FormatStatus.DECLARED,  # rev4c 1
    verdict=_judged("verdict"), fail_items=_judged("fail_items"),
    event_names=_result_events_names,
    g62=None,  # rev4b 4: 형식 없음
    p32=_p3b_p32,
    ready_s=lambda result: _get(result, "p3b", "P3-6_ready", "t_ready_after_loop_start_s"),
    stroke_m=_p3b_stroke_m,
    incomplete=lambda result: None if result.get("events") is not None else "no events",
    fired_events=_result_events_names,
)
"""rev4c 1: ``run_S9`` writes ``events`` from every ``c2.events`` entry (no cap, ``run_S9.py``
5850 / 5910), so the list is whole; the row verdict is revision 12's judge (``judged``)."""


BATCH_FORMATS: dict[str, BatchFormat] = {
    "J-1": D1_FORMAT,
    "J-3'": D1S_FORMAT,
    "J-5": JP_FORMAT,
    "J-7-slope": U3_SLOPE_FORMAT,
    "J-9": READY_ONLY_FORMAT,
    "J-10": R72_FORMAT,
    "J-11": R72_FORMAT,
    "J-12": R72_FORMAT,
    "J-13-main": READY_ONLY_FORMAT,
    "J-13-grid_vb": GRID_VB_FORMAT,
    "J-15": STAGE3_FORMAT,
}
"""Rev4 3: the batches H-7' applies to. ``J-9`` / ``J-13-main`` take the verdict from their own
judge (``line["judged"]``); the drafts wait for control-expert (``FormatStatus.DRAFT``)."""
FIRST_RUN_BATCHES = ("J-3", "J-4", "J-7-new", "J-8", "J-14")
"""Rev4 2 / 3: first runs without a baseline (D-1 Chrono fixed rigid and selected rows, U-3 new
2,118, U-6 726, LAS Chrono pairs): not H-7' targets, the fired state is recorded only."""


# ------------------------------------------------------------------------------- criteria
def _c2(new: dict, base: dict, fmt: BatchFormat) -> str | None:
    verdict, stored = fmt.verdict(new), fmt.verdict(base)
    if verdict is None or stored is None:
        return f"verdict missing (baseline {stored}, new {verdict})"
    if stored in NOT_FAILED_VERDICTS and verdict == VERDICT_FAIL:
        return f"{stored} -> fail {fmt.fail_items(new)}"
    if stored == VERDICT_FAIL and verdict == VERDICT_FAIL:
        new_items, stored_items = fmt.fail_items(new), fmt.fail_items(base)
        if new_items is None or stored_items is None:
            return "fail items missing"
        extra = set(new_items) - set(stored_items)
        if extra:
            return f"new fail items {sorted(extra)}"
    return None


def _faults(heads: set[str] | None) -> set[str] | None:
    return None if heads is None else {name for name in heads if name.startswith(FAULT_PREFIX)}


def _c3(new: dict, base: dict, fmt: BatchFormat) -> str | None:
    new_faults = _faults(event_heads(fmt.event_names(new)))
    stored_faults = _faults(event_heads(fmt.event_names(base)))
    if new_faults is None or stored_faults is None:
        return "event names missing"
    extra = new_faults - stored_faults
    return f"new FAULT {sorted(extra)}" if extra else None


def _c4(new: dict, base: dict, fmt: BatchFormat) -> str | None:
    if fmt.g62(base) is not True:
        return None
    value = fmt.g62(new)
    return None if value is True else f"G6-2 true -> {value}"


def _p32(new: dict, base: dict, fmt: BatchFormat) -> str | None:
    if fmt.p32(base) is not P32State.OK:
        return None
    value = fmt.p32(new)
    return None if value is P32State.OK else f"P3-2 ok -> {value}"


def _increase(new_value, base_value) -> float | None:
    if new_value is None or base_value is None:
        return None
    return float(new_value) - float(base_value)


def _c5_ready(new: dict, base: dict, fmt: BatchFormat) -> str | None:
    ready_new, ready_base = fmt.ready_s(new), fmt.ready_s(base)
    if ready_new is None:
        return None if ready_base is None else f"READY lost (baseline {ready_base} s)"
    up = _increase(ready_new, ready_base)
    if up is not None and up > READY_INCREASE_LIMIT_S:
        return f"READY +{up:.2f} s"
    return None


def _c5_stroke(new: dict, base: dict, fmt: BatchFormat) -> str | None:
    stroke_new, stroke_base = fmt.stroke_m(new), fmt.stroke_m(base)
    if stroke_new is None or stroke_base is None:
        return f"stroke missing (baseline {stroke_base}, new {stroke_new})"
    up = float(stroke_new) - float(stroke_base)
    return f"stroke +{up * MM_PER_M:.2f} mm" if up > STROKE_INCREASE_LIMIT_M else None


_CHECKS = {"C2": _c2, "C3": _c3, "C4'": _c4, "P3-2": _p32, "C5'-R": _c5_ready,
           "C5'-S": _c5_stroke}


class UndecidableLine(ValueError):
    """A line H-7' cannot judge (an event list that may be cut, rev4a 5): stop, not a pass."""


def incomplete_reason(new: dict, base: dict, fmt: BatchFormat) -> str | None:
    """Why the new or the baseline line has a possibly cut event list (None = both whole)."""
    if fmt.incomplete_new is not None:
        reason = fmt.incomplete_new(new)
        if reason is not None:
            return f"new: {reason}"
    if fmt.incomplete_base is not None:
        reason = fmt.incomplete_base(base)
        if reason is not None:
            return f"baseline: {reason}"
    if fmt.incomplete is None:
        return None
    for side, line in (("new", new), ("baseline", base)):
        reason = fmt.incomplete(line)
        if reason is not None:
            return f"{side}: {reason}"
    return None


def new_line_incomplete(new: dict, fmt: BatchFormat) -> str | None:
    """Why a rerun line's own event record cannot show its fired state (None = it can)."""
    for check in (fmt.incomplete_new, fmt.incomplete):
        reason = None if check is None else check(new)
        if reason is not None:
            return reason
    return None


def h7_violations(new: dict, base: dict, fmt: BatchFormat, *,
                  allow_draft: bool = False) -> dict[str, str]:
    """``criterion -> problem`` of one target line against its baseline (empty = no violation).

    Raises:
        ValueError: ``fmt`` is a draft and ``allow_draft`` is not set (rev4 3: confirm first).
        UndecidableLine: An event list that may be cut (rev4a 5: undecidable, stop).
    """
    if fmt.status is not FormatStatus.DECLARED and not allow_draft:
        raise ValueError(f"{fmt.name}: {fmt.status}")
    reason = incomplete_reason(new, base, fmt)
    if reason is not None:
        raise UndecidableLine(f"{fmt.name}: {reason}")
    absent = set(fmt.absent)
    out = {}
    for name, check in _CHECKS.items():
        if name in absent:
            continue
        problem = check(new, base, fmt)
        if problem is not None:
            out[name] = problem
    return out


def not_applicable(base: dict, fmt: BatchFormat) -> list[str]:
    """Criteria whose item the baseline row does not have (G6-2 / P3-2 None, docstring)."""
    out = []
    if fmt.g62 is not None and fmt.g62(base) is None:
        out.append("C4'")
    if fmt.p32 is not None and fmt.p32(base) is None:
        out.append("P3-2")
    return out


@dataclass(frozen=True)
class TargetLine:
    """One rerun line, its baseline (None = a first run) and the events that mark it fired."""

    key: str
    new: dict
    base: dict | None
    event_names: object = None
    new_hash: str | None = None
    """The rerun's command hash (the batch's own hash field)."""
    base_hash: str | None = None
    """The stored baseline's command hash of the same key."""


def silent_hash_check(lines: list[TargetLine], fired_ids: set[int]) -> dict:
    """rev4c 4: every silent line with a baseline keeps the stored command hash (a missing hash
    counts as different); 0 silent lines is recorded as such."""
    silent = [line for line in lines if id(line) not in fired_ids and line.base is not None]
    differing = {line.key: f"hash {str(line.new_hash)[:12]} != stored {str(line.base_hash)[:12]}"
                 for line in silent
                 if line.new_hash is None or line.new_hash != line.base_hash}
    return {"silent_lines": len(silent), "silent_equal": len(silent) - len(differing),
            "silent_hash_differs": differing,
            "note": "no silent line with a baseline" if not silent else None}


def judge_batch(batch: str, lines: list[TargetLine], *, allow_draft: bool = False) -> dict:
    """H-7' of one batch: fired, target and violation counts, per-key problems, the "형식
    없음" criteria and the silent-line hash check (rev4c 4: a silent line with another hash
    than the stored one is an implementation defect and stops the batch).

    Raises:
        KeyError: ``batch`` is neither a format nor a first-run batch.
        ValueError: A draft format without ``allow_draft``.
    """
    if batch in FIRST_RUN_BATCHES:
        fired = [line for line in lines if is_fired(line.event_names)]
        return {"batch": batch, "h7_applies": False, "lines": len(lines),
                "fired": sorted(line.key for line in fired), "targets": 0, "violations": {}}
    fmt = BATCH_FORMATS[batch]
    fired = [line for line in lines if is_fired(
        line.event_names if fmt.fired_events is None else fmt.fired_events(line.new))]
    targets = [line for line in fired if line.base is not None]
    violations, undecidable = {}, {}
    for line in targets:
        try:
            found = h7_violations(line.new, line.base, fmt, allow_draft=allow_draft)
        except UndecidableLine as exc:
            undecidable[line.key] = str(exc)
            continue
        if found:
            violations[line.key] = found
    fired_ids = {id(line) for line in fired}
    for line in lines:  # "not fired" needs a whole event record too
        reason = None if id(line) in fired_ids else new_line_incomplete(line.new, fmt)
        if reason is not None:
            undecidable[line.key] = f"new: {reason} (fired state unknown)"
    hashes = silent_hash_check([line for line in lines if line.key not in undecidable],
                               fired_ids)
    return {"batch": batch, "h7_applies": True, "format": fmt.name, "status": str(fmt.status),
            "format_absent": fmt.absent, "lines": len(lines),
            "fired": sorted(line.key for line in fired),
            "fired_without_baseline": sorted(line.key for line in fired if line.base is None),
            "targets": len(targets), "violations": violations, "undecidable": undecidable,
            "not_applicable": {line.key: not_applicable(line.base, fmt) for line in targets
                               if not_applicable(line.base, fmt)},
            "silent_hash": hashes,
            "stop": bool(violations or undecidable or hashes["silent_hash_differs"])}
