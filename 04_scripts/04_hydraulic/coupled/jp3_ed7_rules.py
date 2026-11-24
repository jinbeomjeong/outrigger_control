"""Edition 7 judgement rules (``jp3_remedy_spec_v7.md`` 6.1, 6.2, 6.3; spec 8 Y7-5).

Functions the edition 7 judge tools use (the judge CLI itself is a post-seal tool commit,
spec 4 step 4); the edition 6 / 436.8 functions stay as they are for the replays:

* :func:`j7_items_ed7` - J7 against V0 (user decision, spec 6.1): a new rod sensor fallback is
  the set difference of ``(name, leg, reason)``; the reason comes from the leg's
  ``INFO_ROD_PRESSURE_FAULT_REASON:<leg>:<reason>`` event, ``unknown`` without one (on both
  sides). The control period difference of a fallback present on both sides is a record item.
  The other J7 items (a WARN / FAULT name new against V0) are those of
  ``judge_stage1_4368.j7_items`` unchanged. ``judge_stage1_4368.j7_items`` (the period
  comparison) stays for the 436.8 / edition 5 / edition 6 replays.
* :func:`is_stall_signature_ed7` - the LEVEL deadlock signature of erratum 8 8-3 with condition
  1 fixed (spec 6.2): an event line "ends without READY after the event", a line without an
  event "never went through READY"; conditions 2 .. 4 unchanged (no fault phase, the last
  phase ``level`` / ``probe``, every leg's ``motor_stroke_m`` span below 1 mm over the last
  20 s). A record, never a judged status.
* :func:`split_sensitivity` - the judged four and the recorded six sensitivity settings.
* :func:`cluster_judgement` - the (setting, row) cluster rule of the sensitivity judgement
  (``k`` = 4): a (setting, row) fails with two or more failed unobserved phases; the clusters
  with a single failed phase fail together when they are more than ``k``.
* :func:`is_u832_cluster` - the three U832 grid clusters left out of the confirmation verdict
  (spec 6.3, user decision; run and recorded).
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence

import numpy as np

FALLBACK_EVENT = "WARN_ROD_PRESSURE_FALLBACK"
REASON_EVENT = "INFO_ROD_PRESSURE_FAULT_REASON"
UNKNOWN_REASON = "unknown"
CONTROL_PERIOD_S = 0.1
SENSITIVITY_JUDGED = ("VBMslow", "VBMfast", "VBMc005", "VBMc04")
SENSITIVITY_RECORD = ("VBMb069", "VBMb16", "VBMh05", "VBMh15", "VBMd05", "VBMd15")
SENSITIVITY_CLUSTER_K = 4
"""Spec 6.2 (stats S3): single-phase failures of the judged sensitivity settings allowed."""
CONFIRMATION_K = 3
"""Spec 6.3 G1: pass -> fail lines against V0 allowed on the opportunity lines."""
STALL_WINDOW_S = 20.0
STALL_WINDOW_TOLERANCE_S = 1e-6
STALL_SPAN_M = 1e-3
STALL_LAST_PHASES = ("level", "probe")
FAULT_PHASES = ("fault", "fault_reground")
READY_PHASE = "ready"
"""Erratum 8 8-3 values (``ed6_probe_share`` / ``jp3_12b_judge`` ``STALL_*``)."""
U832_CLUSTERS = (("bottom", "FL", 2.0), ("bottom", "FR", 2.0), ("bottom", "FR", 4.0))
U832_EVENT, U832_TIMING = "RE1bF", "ready"
"""Spec 6.3: the three U832 clusters ``bottom-FL/FR-Fs2/Fs4-RE1bF-ready`` = the three
``U832_pair_union`` failures of the edition 6 grid record (``j9_runs/79495405/
records_after_stop/A_a1/grid_judge.json``: FL-Fs2, FR-Fs2, FR-Fs4). The fourth combination of
the spec's short notation, ``bottom-FL-Fs4-RE1bF-ready``, did not fail there and stays judged
(reported as 확인 필요)."""


# ------------------------------------------------------------------------------ J7
def fallback_triples(events: Iterable[tuple[float, str]]) -> dict[tuple[str, str, str], float]:
    """``(name, leg, reason) -> time`` of every rod sensor fallback of a line. The reason is
    the leg's ``INFO_ROD_PRESSURE_FAULT_REASON:<leg>:<reason>`` (the monitor writes it with the
    fallback), ``unknown`` without one."""
    reasons: dict[str, str] = {}
    fallbacks: list[tuple[float, str, str]] = []
    for t_s, name in events:
        parts = str(name).split(":")
        if parts[0] == REASON_EVENT and len(parts) >= 3:
            reasons.setdefault(parts[1], ":".join(parts[2:]))
        elif parts[0] == FALLBACK_EVENT and len(parts) >= 2:
            fallbacks.append((float(t_s), parts[0], parts[1]))
    triples: dict[tuple[str, str, str], float] = {}
    for t_s, name, leg in fallbacks:
        triples.setdefault((name, leg, reasons.get(leg, UNKNOWN_REASON)), t_s)
    return triples


def _item(kind: str, detail: str, scatter: bool = False) -> dict:
    return {"item": "J7", "kind": kind, "detail": detail, "base_other_phase_has_it": scatter}


def j7_items_ed7(base: Mapping, on: Mapping, base_all: Sequence[Mapping]) -> list[dict]:
    """Spec 6.1 J7 of one (V0, setting) pair of metric rows (``events_full``,
    ``events_capped``, ``bad_436`` as ``judge_stage1_4368.metrics`` gives them)."""
    if base["events_capped"] or on["events_capped"]:
        return [_item("not_judgeable", "event list cut at 200")]
    items = [_item("fail", name, any(name in other["bad_436"] for other in base_all))
             for name in on["bad_436"]
             if name not in base["bad_436"] and not name.startswith(FALLBACK_EVENT)]
    base_triples = fallback_triples(base["events_full"])
    for triple, t_s in fallback_triples(on["events_full"]).items():
        name, leg, reason = triple
        label = f"{name}:{leg} reason {reason}"
        if triple not in base_triples:
            items.append(_item("fail", label))
            continue
        periods = round((t_s - base_triples[triple]) / CONTROL_PERIOD_S)
        if periods:
            items.append(_item("record", f"{label}: {periods:+d} periods against V0"))
    return items


# ------------------------------------------------------------------------------ deadlock
def is_stall_signature_ed7(phases: Sequence[str], t_s: Sequence[float],
                           motor_stroke_m: np.ndarray, t_event_s: float | None) -> bool:
    """Spec 6.2 LEVEL deadlock signature (module docstring); ``t_event_s`` None = a line
    without an event."""
    phases = [str(phase).lower() for phase in phases]
    times = np.asarray(t_s, float)
    strokes = np.asarray(motor_stroke_m, float)
    if not phases or any(phase in FAULT_PHASES for phase in phases):
        return False
    if t_event_s is None or not math.isfinite(t_event_s):
        if READY_PHASE in phases:
            return False
    else:
        after = [phase for phase, t in zip(phases, times, strict=True) if t >= t_event_s]
        if READY_PHASE in after:
            return False
    if phases[-1] not in STALL_LAST_PHASES:
        return False
    window = times >= times[-1] - STALL_WINDOW_S - STALL_WINDOW_TOLERANCE_S
    spans = strokes[window].max(axis=0) - strokes[window].min(axis=0)
    return bool((spans < STALL_SPAN_M).all())


# ------------------------------------------------------------------------------ sensitivity
def split_sensitivity(rows: Iterable[Mapping]) -> dict[str, list[Mapping]]:
    """``{"judged": [...], "record": [...], "other": [...]}`` by the row's ``setting``."""
    split: dict[str, list[Mapping]] = {"judged": [], "record": [], "other": []}
    for row in rows:
        setting = row.get("setting")
        if setting in SENSITIVITY_JUDGED:
            split["judged"].append(row)
        elif setting in SENSITIVITY_RECORD:
            split["record"].append(row)
        else:
            split["other"].append(row)
    return split


def row_key(job: Mapping) -> str:
    """The case-table row of a job (spec 6.2 "행"): the case (``R2ra`` for the re-anchor
    decision) and, for a G4 / grid twin, its level, leg and F_s (a twin key is one row);
    the offset / eps is the phase inside it."""
    case = "R2ra" if job.get("decision") == "reanchor_on" else str(job["case"])
    twin = job.get("twin")
    if not twin:
        return case
    key = f"{case} {twin['level']}-{twin['leg']}-Fs{float(twin['fs_kN']):g}"
    for field in ("event", "timing"):
        if field in twin:
            key += f"-{twin[field]}"
    return key


def cluster_judgement(units: Iterable[Mapping], k: int = SENSITIVITY_CLUSTER_K,
                      observed: frozenset[tuple[str, str]] = frozenset()) -> dict:
    """Spec 6.2 (setting, row) rule over unit results ``{"setting", "row", "phase",
    "failed"}``; ``observed`` = (setting, row key + phase) units seen before (stop condition
    only, never counted). Fails when a cluster has two or more failed unobserved phases or
    the single-phase clusters are more than ``k``."""
    failed_phases: dict[tuple[str, str], list[str]] = defaultdict(list)
    counted = 0
    for unit in units:
        if (unit["setting"], f"{unit['row']} {unit['phase']}") in observed:
            continue
        counted += 1
        if unit["failed"]:
            failed_phases[(unit["setting"], unit["row"])].append(str(unit["phase"]))
    multi = sorted(f"{setting} {row}" for (setting, row), phases in failed_phases.items()
                   if len(phases) >= 2)
    single = sorted(f"{setting} {row}" for (setting, row), phases in failed_phases.items()
                    if len(phases) == 1)
    is_failed = bool(multi) or len(single) > k
    return {"status": "fail" if is_failed else ("pass" if counted else "not_judgeable"),
            "units": counted, "multi_phase_clusters": multi,
            "single_phase_clusters": single, "k": k}


# ------------------------------------------------------------------------------ grid
def is_u832_cluster(level: str, leg: str, fs_kN: float, event: str, timing: str) -> bool:
    return ((level, leg, float(fs_kN)) in U832_CLUSTERS and event == U832_EVENT
            and timing == U832_TIMING)
