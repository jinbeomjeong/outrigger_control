"""Rod pressure sensor fault plan of the r79 noise runs (X-10, edition 5 6.2a, record and gate).

One fault per job: the rod reading of one leg is replaced after the sensor error model and the
signal range saturation (``SensorAdapter.deliver``), just before the controller reads it; the
head reading stays as it is. ``r79_sensor_screen`` imports this module only when
``R79_ROD_FAULT_PLAN`` names a plan file.

Plan file (JSON, schema :data:`PLAN_SCHEMA`; a repeated JSON key is an error)::

    {"schema": "r79_rod_fault_plan/1",
     "faults": {"<r79 job key as run_job gets it>": {
         "fault_id": "<text>", "leg": "FL" | "FR" | "RL" | "RR",
         "kind": "STUCK" | "DROPOUT", "value_bar": <finite number> | null,
         "anchor": "<anchor>", "delay_reads": <int >= 0>}}}

``STUCK`` holds the reading at ``value_bar`` (the gate fault: -100 bar, a broken wire, 0 mA);
``DROPOUT`` gives NaN (record only, ``value_bar`` null).

Reads and anchors. Read n is the n-th measurement delivered to the controller (0-based);
controller update n reads it, so read n is T4h row n. The phase *in effect* at read n is the
controller phase after update n - 1 (the one the truth log records); the commands ``u_k`` are
the 10 Hz output commands of update k (T4h ``command_m_s``). The trigger uses only these two
quantities, which both arms of a pair share before the fault.

Anchors (trigger read, first faulty read):

``phase_enter:CHECK``
    T-CK record: the first read in effect in CHECK; faulty from it.
``phase_exit:CHECK``
    tau_C (T0'): the first read in effect outside CHECK after a CHECK read (the read right
    after the update that left CHECK); faulty from it.
``retract_start_after:LEVEL``
    tau_R (TR'): from the first update whose phase is LEVEL, the first update k >= 1 with
    ``|u_{k-1}| <= u_hold`` and ``u_k < -u_hold`` on the fault leg; trigger read k, faulty
    from read k + 1 (the trigger never depends on the fault).
``t:<s>``
    tests: the first read with ``t >= s``; faulty from it.

``delay_reads`` adds that many reads before the first faulty read. ``u_hold`` =
``extend_start_bound.HOLD_SPEED_RATIO`` (0.01, decision 146) x YAML
``actuator.max_speed_m_s`` (0.20924 mm/s).

Pair identity (6.2a.4): ``pre_trigger_commands_sha256`` is the sha256 of the output commands
of every update before the first faulty read (``verdict_runs._command_digest`` bytes, float64
rows in order), ``pre_trigger_fallback`` whether a ``WARN_ROD_PRESSURE_FALLBACK`` event of any
leg came before it.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path

import numpy as np

PLAN_SCHEMA = "r79_rod_fault_plan/1"
PLAN_KEYS = frozenset({"schema", "faults"})
FAULT_KEYS = frozenset({"fault_id", "leg", "kind", "value_bar", "anchor", "delay_reads"})
LEGS = ("FL", "FR", "RL", "RR")
PA_PER_BAR = 1e5
TIME_TOLERANCE_S = 1e-9
PHASE_CHECK = "check"
PHASE_LEVEL = "level"
FALLBACK_EVENT = "WARN_ROD_PRESSURE_FALLBACK"
FAULT_REASON_EVENT = "INFO_ROD_PRESSURE_FAULT_REASON"
TIME_ANCHOR = re.compile(r"t:(?P<time_s>[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)")
SUM_OFFSET_RULE = ("change of the four-leg net-force sum (two_pressure._net_sum_N) on the "
                   "fault leg: -A_ann (p_fault - p_rod before the fault), per faulty read")
HOLD_SPEED_SOURCE = ("outrigger_sim.control.extend_start_bound.HOLD_SPEED_RATIO x YAML "
                     "actuator.max_speed_m_s (outrigger_sim.params.load_params)")


class RodFaultPlanError(ValueError):
    """A plan file that cannot be used (schema, keys, values, or no fault for a job)."""


class FaultKind(StrEnum):
    STUCK = "STUCK"
    """The reading held at ``value_bar`` (finite)."""
    DROPOUT = "DROPOUT"
    """The reading NaN (record only; it switches D1' / D1'' off on every leg)."""


class AnchorKind(StrEnum):
    PHASE_ENTER_CHECK = "phase_enter:CHECK"
    PHASE_EXIT_CHECK = "phase_exit:CHECK"
    RETRACT_START_AFTER_LEVEL = "retract_start_after:LEVEL"
    TIME = "t"


@dataclass(frozen=True)
class Anchor:
    """A parsed plan anchor; ``time_s`` only for :attr:`AnchorKind.TIME`."""

    kind: AnchorKind
    text: str
    time_s: float | None = None


@dataclass(frozen=True)
class RodFault:
    """One planned fault of one job."""

    job_key: str
    fault_id: str
    leg: str
    kind: FaultKind
    value_bar: float | None
    anchor: Anchor
    delay_reads: int

    @property
    def leg_index(self) -> int:
        return LEGS.index(self.leg)

    @property
    def value_Pa(self) -> float:
        """The faulty reading (NaN for a dropout)."""
        if self.kind is FaultKind.DROPOUT:
            return math.nan
        return float(self.value_bar) * PA_PER_BAR


@dataclass(frozen=True)
class RodFaultPlan:
    """A validated plan file: its identity and one fault per job key."""

    path: str
    sha256: str
    schema: str
    faults: dict[str, RodFault]

    def meta(self) -> dict:
        """The run meta block ``rod_fault_plan``."""
        return {"path": self.path, "sha256": self.sha256, "n_faults": len(self.faults),
                "schema": self.schema}

    def key_problems(self, job_keys: list[str]) -> list[str]:
        """Why the plan keys are not exactly the run's job keys (empty = they are)."""
        planned, jobs = set(self.faults), set(job_keys)
        problems = []
        if jobs - planned:
            problems.append(f"{len(jobs - planned)} job keys without a fault "
                            f"(e.g. {sorted(jobs - planned)[0]!r})")
        if planned - jobs:
            problems.append(f"{len(planned - jobs)} plan keys that are no job of the run "
                            f"(e.g. {sorted(planned - jobs)[0]!r})")
        return problems

    def fault_for(self, job_key: str) -> RodFault:
        """The fault of ``job_key``.

        Raises:
            RodFaultPlanError: The plan has no fault for the key.
        """
        if job_key not in self.faults:
            raise RodFaultPlanError(f"plan {self.path} has no fault for job {job_key!r}")
        return self.faults[job_key]


# ------------------------------------------------------------------------------- plan loading
def _reject_repeated_keys(pairs: list[tuple[str, object]]) -> dict:
    keys = [key for key, _ in pairs]
    repeated = sorted({key for key in keys if keys.count(key) > 1})
    if repeated:
        raise RodFaultPlanError(f"repeated JSON keys {repeated[:3]}")
    return dict(pairs)


def parse_anchor(text: object) -> Anchor:
    """The anchor of a plan entry.

    Raises:
        RodFaultPlanError: Not one of the module docstring's anchors.
    """
    if not isinstance(text, str):
        raise RodFaultPlanError(f"anchor must be a string, got {text!r}")
    time_match = TIME_ANCHOR.fullmatch(text)
    if time_match is not None:
        return Anchor(AnchorKind.TIME, text, float(time_match["time_s"]))
    named = {kind.value: kind for kind in AnchorKind if kind is not AnchorKind.TIME}
    if text not in named:
        raise RodFaultPlanError(f"unknown anchor {text!r} (one of {sorted(named)} or t:<s>)")
    return Anchor(named[text], text)


def _fault_value_bar(kind: FaultKind, value: object, where: str) -> float | None:
    if kind is FaultKind.DROPOUT:
        if value is not None:
            raise RodFaultPlanError(f"{where}: a DROPOUT has value_bar null, got {value!r}")
        return None
    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if not is_number or not math.isfinite(float(value)):
        raise RodFaultPlanError(f"{where}: a STUCK value_bar must be a finite number, "
                                f"got {value!r}")
    return float(value)


def _parse_fault(job_key: str, entry: object) -> RodFault:
    where = f"fault of {job_key!r}"
    if not isinstance(entry, dict):
        raise RodFaultPlanError(f"{where} must be an object")
    if set(entry) != FAULT_KEYS:
        raise RodFaultPlanError(f"{where}: keys missing {sorted(FAULT_KEYS - set(entry))}, "
                                f"extra {sorted(set(entry) - FAULT_KEYS)}")
    fault_id, leg, delay = entry["fault_id"], entry["leg"], entry["delay_reads"]
    if not isinstance(fault_id, str) or not fault_id:
        raise RodFaultPlanError(f"{where}: fault_id must be a non-empty string")
    if leg not in LEGS:
        raise RodFaultPlanError(f"{where}: leg must be one of {LEGS}, got {leg!r}")
    if entry["kind"] not in {kind.value for kind in FaultKind}:
        raise RodFaultPlanError(f"{where}: kind must be STUCK or DROPOUT, got "
                                f"{entry['kind']!r}")
    if not isinstance(delay, int) or isinstance(delay, bool) or delay < 0:
        raise RodFaultPlanError(f"{where}: delay_reads must be an integer >= 0, got {delay!r}")
    kind = FaultKind(entry["kind"])
    return RodFault(job_key, fault_id, leg, kind, _fault_value_bar(kind, entry["value_bar"],
                                                                     where),
                    parse_anchor(entry["anchor"]), delay)


def load_plan(path: str | Path) -> RodFaultPlan:
    """Read and validate a plan file.

    Raises:
        RodFaultPlanError: Unreadable file, wrong schema or keys, an empty plan, a bad entry
            or a repeated ``fault_id``.
    """
    try:
        raw = Path(path).read_bytes()
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_repeated_keys)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RodFaultPlanError(f"plan {path} cannot be read: {exc}") from exc
    if not isinstance(document, dict) or set(document) != PLAN_KEYS:
        found = sorted(document) if isinstance(document, dict) else type(document).__name__
        raise RodFaultPlanError(f"plan {path}: top-level keys must be {sorted(PLAN_KEYS)}, "
                                f"got {found}")
    if document["schema"] != PLAN_SCHEMA:
        raise RodFaultPlanError(f"plan {path}: schema {document['schema']!r} is not "
                                f"{PLAN_SCHEMA!r}")
    entries = document["faults"]
    if not isinstance(entries, dict) or not entries:
        raise RodFaultPlanError(f"plan {path}: faults must be a non-empty object "
                                "(an empty plan is refused)")
    faults = {key: _parse_fault(key, entry) for key, entry in entries.items()}
    ids = [fault.fault_id for fault in faults.values()]
    repeated = sorted({fault_id for fault_id in ids if ids.count(fault_id) > 1})
    if repeated:
        raise RodFaultPlanError(f"plan {path}: repeated fault_id {repeated[:3]}")
    return RodFaultPlan(str(path), hashlib.sha256(raw).hexdigest(), PLAN_SCHEMA, faults)


def hold_speed_m_s() -> float:
    """``u_hold`` of the tau_R trigger (see :data:`HOLD_SPEED_SOURCE`)."""
    from outrigger_sim.control.extend_start_bound import HOLD_SPEED_RATIO
    from outrigger_sim.params import load_params

    return HOLD_SPEED_RATIO * float(load_params().actuator.max_speed_m_s)


def commands_sha256(period_log: list, rows: int) -> str:
    """sha256 of the output commands of the first ``rows`` updates of a ``LoggedController``
    log (the bytes of ``verdict_runs._command_digest``)."""
    commands = np.array([row[2] for row in period_log[:rows]], float).reshape(-1, len(LEGS))
    return hashlib.sha256(commands.tobytes()).hexdigest()


# ------------------------------------------------------------------------------- injection
class RodFaultInjector:
    """Applies one :class:`RodFault` to the delivered measurements of a run and records it.

    Args:
        fault: The job's fault.
        plan_sha256: Identity of the plan file.
        hold_speed: ``u_hold`` [m/s] of the tau_R trigger.
    """

    def __init__(self, fault: RodFault, plan_sha256: str, hold_speed: float) -> None:
        self.fault = fault
        self.plan_sha256 = plan_sha256
        self.hold_speed_m_s = hold_speed
        self.trigger_read: int | None = None
        self.armed_t_s: float | None = None
        self.first_applied_read: int | None = None
        self.first_applied_t_s: float | None = None
        self.pre_trigger_commands_sha256: str | None = None
        self.pre_trigger_fallback_events: list[tuple[float, str]] | None = None
        self.read_t_s: list[float] = []
        self.pre_fault_rod_Pa: list[np.ndarray] = []
        self.is_applied: list[bool] = []
        self.sum_offsets_N: list[float] = []
        self._has_seen_check = False
        self._level_row: int | None = None
        self._scanned_rows = 0

    # --- per read
    def apply(self, ctrl, delivered):
        """The measurements the controller reads at this period (faulty from the first
        faulty read on).

        Raises:
            RuntimeError: No rod channel, or no command log for the tau_R trigger.
        """
        read = len(self.read_t_s)
        if delivered.rod_pressure_Pa is None:
            raise RuntimeError("rod fault plan: the level delivers no rod reading")
        rod_Pa = np.array(delivered.rod_pressure_Pa, float)
        t_s = float(delivered.t_s)
        if self.trigger_read is None:
            self._find_trigger(ctrl, read, t_s)
        is_faulty = self.first_applied_read is not None and read >= self.first_applied_read
        if is_faulty and read == self.first_applied_read:
            self._note_first_faulty_read(ctrl, read, t_s)
        self.read_t_s.append(t_s)
        self.pre_fault_rod_Pa.append(rod_Pa.copy())
        self.is_applied.append(is_faulty)
        if not is_faulty:
            return delivered
        leg = self.fault.leg_index
        annulus = np.asarray(ctrl.geometry.annulus_area_m2, float)
        self.sum_offsets_N.append(-float(annulus[leg]) * (self.fault.value_Pa - rod_Pa[leg]))
        rod_Pa[leg] = self.fault.value_Pa
        return replace(delivered, rod_pressure_Pa=rod_Pa)

    def _arm(self, trigger_read: int, armed_t_s: float, first_read: int) -> None:
        self.trigger_read = trigger_read
        self.armed_t_s = armed_t_s
        self.first_applied_read = first_read + self.fault.delay_reads

    def _find_trigger(self, ctrl, read: int, t_s: float) -> None:
        kind = self.fault.anchor.kind
        phase = str(ctrl.phase)
        if kind is AnchorKind.TIME:
            if t_s >= self.fault.anchor.time_s - TIME_TOLERANCE_S:
                self._arm(read, t_s, read)
        elif kind is AnchorKind.PHASE_ENTER_CHECK:
            if phase == PHASE_CHECK:
                self._arm(read, t_s, read)
        elif kind is AnchorKind.PHASE_EXIT_CHECK:
            if phase == PHASE_CHECK:
                self._has_seen_check = True
            elif self._has_seen_check:
                self._arm(read, t_s, read)
        else:
            self._scan_retract_start(self._period_log(ctrl, read))

    @staticmethod
    def _period_log(ctrl, read: int) -> list:
        log = ctrl.__dict__.get("period_log")
        if log is None and read > 0:
            raise RuntimeError("rod fault plan: the tau_R trigger needs the 10 Hz command log "
                               "(verdict_runs.install_logged_controller)")
        return log or []

    def _scan_retract_start(self, log: list) -> None:
        """tau_R on the updates not scanned yet (normally the one just done)."""
        leg = self.fault.leg_index
        for row in range(self._scanned_rows, len(log)):
            self._scanned_rows = row + 1
            if self._level_row is None and log[row][1] == PHASE_LEVEL:
                self._level_row = row
            if self._level_row is None or row < max(self._level_row, 1):
                continue
            previous_u, current_u = float(log[row - 1][2][leg]), float(log[row][2][leg])
            if abs(previous_u) <= self.hold_speed_m_s and current_u < -self.hold_speed_m_s:
                self._arm(row, float(log[row][0]), row + 1)
                return

    def _note_first_faulty_read(self, ctrl, read: int, t_s: float) -> None:
        self.first_applied_t_s = t_s
        log = ctrl.__dict__.get("period_log") or []
        self.pre_trigger_commands_sha256 = commands_sha256(log, read)
        self.pre_trigger_fallback_events = [
            (round(float(event.t_s), 6), event.name) for event in ctrl.events
            if event.name.startswith(FALLBACK_EVENT)]

    # --- after the run
    def latch_record(self, ctrl) -> dict:
        """The fault leg's rod fallback at or after the first faulty read."""
        empty = {"is_latched": False, "reason": None, "t_s": None, "reads_after_first": None}
        if self.first_applied_t_s is None:
            return empty
        prefix = f"{FAULT_REASON_EVENT}:{self.fault.leg}:"
        for event in ctrl.events:
            if event.name.startswith(prefix) and (
                    float(event.t_s) >= self.first_applied_t_s - TIME_TOLERANCE_S):
                t_latch = float(event.t_s)
                reads = [i for i, t in enumerate(self.read_t_s)
                         if abs(t - t_latch) <= TIME_TOLERANCE_S]
                return {"is_latched": True, "reason": event.name[len(prefix):],
                        "t_s": round(t_latch, 6),
                        "reads_after_first": (reads[0] - self.first_applied_read) if reads
                        else None}
        return empty

    def sum_offset_record(self) -> dict | None:
        """``rod_fault_sum_offset_N`` (None without a faulty read; NaN values are counted
        apart, a dropout has none finite)."""
        if not self.sum_offsets_N:
            return None
        finite = [value for value in self.sum_offsets_N if math.isfinite(value)]
        first = self.sum_offsets_N[0]
        return {"rule": SUM_OFFSET_RULE, "n_reads": len(self.sum_offsets_N),
                "n_finite": len(finite),
                "first_N": first if math.isfinite(first) else None,
                "min_N": min(finite) if finite else None,
                "max_N": max(finite) if finite else None}

    def record(self, ctrl) -> dict:
        """The result row block ``rod_fault``."""
        fault = self.fault
        log = ctrl.__dict__.get("period_log") or []
        fallback = self.pre_trigger_fallback_events
        return {
            "plan_sha256": self.plan_sha256, "fault_id": fault.fault_id, "leg": fault.leg,
            "kind": fault.kind.value, "value": fault.value_bar,
            "value_unit": "bar", "anchor": fault.anchor.text,
            "delay_reads": fault.delay_reads,
            "hold_speed_m_s": self.hold_speed_m_s, "hold_speed_source": HOLD_SPEED_SOURCE,
            "is_armed": self.trigger_read is not None,
            "trigger_read": self.trigger_read, "armed_t_s": self.armed_t_s,
            "first_applied_read": self.first_applied_read,
            "first_applied_t_s": self.first_applied_t_s,
            "applied_periods": int(sum(self.is_applied)),
            "latched": self.latch_record(ctrl),
            "pre_trigger_commands_sha256": self.pre_trigger_commands_sha256,
            "pre_trigger_fallback": None if fallback is None else bool(fallback),
            "pre_trigger_fallback_events": fallback,
            "rod_fault_sum_offset_N": self.sum_offset_record(),
            "reads": len(self.read_t_s), "updates": len(log),
        }

    def t4h_arrays(self, period_t: np.ndarray) -> dict[str, np.ndarray]:
        """Per T4h row (matched by time): the rod reading before the fault and where the fault
        was applied (NaN / False for a row without a delivered read)."""
        by_time = {round(t, 9): i for i, t in enumerate(self.read_t_s)}
        rows = len(period_t)
        pre_fault = np.full((rows, len(LEGS)), np.nan)
        applied = np.zeros((rows, len(LEGS)), bool)
        for row, t_s in enumerate(np.asarray(period_t, float)):
            read = by_time.get(round(float(t_s), 9))
            if read is None:
                continue
            pre_fault[row] = self.pre_fault_rod_Pa[read]
            applied[row, self.fault.leg_index] = self.is_applied[read]
        return {"rod_pressure_pre_fault_Pa": pre_fault, "rod_fault_applied": applied}
