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
as such. Interpretation (to confirm by control-expert): for G6-2 and P3-2 a baseline value of None
means the row has no such item (a G6 row has no P3-2, a steady row no G6-2), so the criterion does
not apply to that line; it is listed per line as "baseline without the item".

Field note: rev4 3 J-1 names the G6-2 item ``d1.items["G6-2"]``; the stored D-1 lines name it
``G6-2_loc`` (``v5/d1.jsonl``, all 868 lines) and have no ``G6-2`` key, so the J-1 format reads
``G6-2_loc`` (reading ``G6-2`` would make C4' vacuous). The rev3 key list has the same ``G6-2``
field (None on all 76 T-3c entries although ``G6-2_loc`` is true there); the T-3 judge therefore
takes the baseline items from ``v5/d1.jsonl`` (rev3 K-6b: "d1.items").
"""
from __future__ import annotations

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


def _judged(field: str) -> Extractor:
    """A value the batch's own judge writes into ``line["judged"]`` before H-7' (the rev4 3
    "판정 원천" of the batches whose lines carry no verdict field)."""
    return lambda line: _get(line, "judged", field)


D1_FORMAT = BatchFormat(
    name="J-1 D-1 harness 868", status=FormatStatus.DECLARED,
    verdict=lambda line: _get(line, "d1", "verdict"),
    fail_items=lambda line: _get(line, "d1", "fail_items"),
    event_names=lambda line: line.get("event_names"),
    g62=lambda line: _get(line, "d1", "items", "G6-2_loc"),  # rev4 writes "G6-2" (docstring)
    p32=_d1_p32,
    ready_s=lambda line: _get(line, "d1", "t_ready_s"),
    stroke_m=lambda line: _get(line, "d1", "stroke_max_m"),
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
)
READY_ONLY_FORMAT = BatchFormat(
    name="J-9 U-9 V0 / J-13 main and pressure_only", status=FormatStatus.DECLARED,
    verdict=_judged("verdict"), fail_items=_judged("fail_items"),
    event_names=lambda line: line.get("event_names"),
    g62=None, p32=None,
    ready_s=lambda line: _get(line, "values", "times", "t_first_ready_s"),
    stroke_m=None,
)


def _draft(name: str) -> BatchFormat:
    """A format whose fields are not declared yet (every extractor reads ``judged``)."""
    return BatchFormat(name=name, status=FormatStatus.DRAFT, verdict=_judged("verdict"),
                       fail_items=_judged("fail_items"), event_names=_judged("event_names"),
                       g62=_judged("G6-2"), p32=_judged("P3-2"), ready_s=_judged("t_ready_s"),
                       stroke_m=_judged("stroke_max_m"))


BATCH_FORMATS: dict[str, BatchFormat] = {
    "J-1": D1_FORMAT,
    "J-3'": _draft("J-3' D-1 Chrono SCM S-03 / S-04 (d1s_judge row verdict)"),
    "J-5": _draft("J-5 / J-6 D-1 G1 Chrono and J_P fired reruns (original row verdict)"),
    "J-7-slope": _draft("J-7 U-3 slope V0 110 (u3_u6_rerun_rules_rev2: 형식에 따름)"),
    "J-9": READY_ONLY_FORMAT,
    "J-10": R72_FORMAT,
    "J-11": R72_FORMAT,
    "J-12": R72_FORMAT,
    "J-13-main": READY_ONLY_FORMAT,
    "J-13-grid_vb": _draft("J-13 stage-2 grid VB 768 (field table before any run)"),
    "J-15": _draft("J-15 stage-3 Chrono LAS reruns 37 (revision 12 row verdict)"),
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


def h7_violations(new: dict, base: dict, fmt: BatchFormat, *,
                  allow_draft: bool = False) -> dict[str, str]:
    """``criterion -> problem`` of one target line against its baseline (empty = no violation).

    Raises:
        ValueError: ``fmt`` is a draft and ``allow_draft`` is not set (rev4 3: confirm first).
    """
    if fmt.status is not FormatStatus.DECLARED and not allow_draft:
        raise ValueError(f"{fmt.name}: {fmt.status}")
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
    event_names: object


def judge_batch(batch: str, lines: list[TargetLine], *, allow_draft: bool = False) -> dict:
    """H-7' of one batch: fired, target and violation counts, per-key problems and the "형식
    없음" criteria of the batch.

    Raises:
        KeyError: ``batch`` is neither a format nor a first-run batch.
        ValueError: A draft format without ``allow_draft``.
    """
    fired = [line for line in lines if is_fired(line.event_names)]
    if batch in FIRST_RUN_BATCHES:
        return {"batch": batch, "h7_applies": False, "lines": len(lines),
                "fired": sorted(line.key for line in fired), "targets": 0, "violations": {}}
    fmt = BATCH_FORMATS[batch]
    targets = [line for line in fired if line.base is not None]
    violations = {}
    for line in targets:
        found = h7_violations(line.new, line.base, fmt, allow_draft=allow_draft)
        if found:
            violations[line.key] = found
    return {"batch": batch, "h7_applies": True, "format": fmt.name, "status": str(fmt.status),
            "format_absent": fmt.absent, "lines": len(lines),
            "fired": sorted(line.key for line in fired),
            "fired_without_baseline": sorted(line.key for line in fired if line.base is None),
            "targets": len(targets), "violations": violations,
            "not_applicable": {line.key: not_applicable(line.base, fmt) for line in targets
                               if not_applicable(line.base, fmt)},
            "stop": bool(violations)}
