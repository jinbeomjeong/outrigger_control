"""T4h shadow judge of the adopted LAS-b variant (sealed ``las_targeted_rules.md`` 4 and its
sealed addendum ``las_targeted_rules_rev1.md`` 1, 2, 4, 5).

Per stored record: did the variant's start gate (S1 .. S8 of rules 1.2, S7 = S7' of rev1 2)
hold in any LEVEL step? ``fires`` = rerun needed, ``silent`` = the rule never starts, the
commands are bit for bit the stored ones (the rule acts only after its start),
``undecidable`` = rerun (a field is missing or the L-hat rebuild was rejected, rev1 R-5).

Inputs: T4h npz (``t_s``, ``phase``, ``meta_json`` with ``events`` and ``F_min_N``) and L-hat:
  stored   ``lower_estimate_N`` of the record (r79 Dg-3 and ``las_targeted.py --gate-npz-dir``
           records): mode ``stored``, delta 0.
  rebuilt  rev1 4 R-1 for a record without it, given the R-2 result (``--r2``): the run's own
           events are replayed through ``t4h_replay`` (``checked_run_config``,
           ``offset_allowance_of``, ``own_event_replay_lower_N`` = the ``--check-recorded`` path)
           and the lower reading goes through ``C2Controller._load_estimate_N`` itself. R-2
           (``r2``) measures the largest |L-hat rebuilt - L-hat stored| over the pre-LOC LEVEL
           steps of every record that has both; that delta sets the mode of every rebuilt
           record: ``exact`` (<= 1 N, R-3), ``band`` (1 N < delta <= 500 N, R-4: the gate is
           widened to the safe side with delta) or ``reject`` (> 500 N, R-5: undecidable).
           Without ``--r2`` a record without ``lower_estimate_N`` is undecidable. The replay
           reads the rod-side pressure on every row, so a head-only record (no finite
           ``rod_pressure_Pa``, e.g. a V0 run) is outside it: R-5 for a judged record, "not
           replayable" (left out of delta) in ``r2``. Of the stored v5 T4h records (all VB /
           LS) only the event runs carry rod-side readings; the steady runs are head-only
           (2026-11-08: 820 rebuildable, 822 head-only). ``r2`` also leaves out the records
           ``t4h_replay`` refuses (a ③ bound meta of revision 3, 135 Dg-3 records).
W_ref is ``meta.W_ref_N`` or, without it, the YAML superstructure mass x g
(``C2Controller._reference_weight_N``); S1 is ``meta.soil_enable`` or, without it, true
(assumption, listed per record; rev1 I-3).

The L-hat transform (rev1 R-1, checked in the code 2026-11-08). ``c2.C2Controller
._load_estimate_N(forces)`` returns ``forces`` unchanged only for ``ContactJudge.PRESSURE``; for
every other judge it returns ``forces - self._leg_seal_bands_N()``, i.e. it is NOT the identity
in the harness runs (contact COMBINED). The rebuild therefore calls that function with a view
whose ``config`` is the run's rebuilt config and whose ``_leg_seal_bands_N()`` is the record's
``seal_band_N`` row of that update: ``LoggedController._logged_readings`` stores
``self._leg_seal_bands_N()`` after each update, which in a LEVEL update equals the value at the
wrapper point (confirmation 1 below). ``r2`` also checks it on the records that carry the run's
own lower reading: ``transform_max_abs_N`` = max |L-hat stored - transform(lower_reading_N)|.

Gate evaluation per period k (``t_s[k]``; ``phase`` is the phase after the update):
  LEVEL step  the update ran ``_level_step``: phase entering it (``phase[k-1]``) LEVEL, or DONE /
              PROBE / READY with ``phase[k]`` LEVEL or FAULT* (the re-level of
              ``_hold_probe_or_relevel``: ``_start_relevel`` sets LEVEL first, and a DONE cannot
              follow in that period because ``complete_since_s`` was cleared). A head-sensor FAULT
              raised in ``_read`` of a LEVEL period is still counted (over-count, safe side).
  S2          a LEVEL step without ``WARN_CRAWLER_LIFTOFF_UNCONFIRMED`` at t_k (that S-4 FAULT is
              set in ``_update_crawler_zone``, before the wrapper point).
  S3          no ``crawler_liftoff_confirmed`` (or ``INFO_SOIL_STATE_RESTORED``) at or before t_k:
              the LOC is confirmed in ``_update_liftoff_window`` at the start of ``_level_step``,
              before the wrapper point, so an event at t_k already closes S3 in period k.
  S4          no ``soil_mode_start`` at or before t_k: it is raised in
              ``_hold_crawler_zone_until_liftoff`` inside ``_update_crawler_zone``, before the
              wrapper point.
  S5          true (proof below).
  S6          no active re-approach after the events at or before t_k: ``_update_lifted_reapproach``
              runs before ``_phase_command`` in ``update``; ``leg_reapproach_start`` adds the leg,
              ``leg_reapproach_contact`` / ``WARN_LEG_REAPPROACH_NO_CONTACT`` remove it, and a
              period entered in a phase outside ``REAPPROACH_PHASES`` ends all (no event). An
              unclear end is read as "no re-approach" (S6 true, rev1 I-2: over-counts fires).
  S7          S7' (rev1 2): sum L >= alpha W_ref, min L < beta F_min, rho_k >= rho_on and
              rho_k > rho_{k-1} on L-hat[k]; rho_{k-1} exists only when update k-1 was a LEVEL
              step (the controller clears it in a period without one), else S7' is false.
              Band mode (R-4): sum L >= alpha W_ref - 4 delta, min L < beta F_min + delta,
              rho_k >= rho_on - 8 delta / sum L, rho_k - rho_{k-1} > -16 delta / sum L.
  S8          true (rules 4: the stored command is not the P30fz-stage value; safe side).
Silent records list the blocked conditions: per condition the LEVEL steps where it was false,
the step with the fewest false conditions and the largest pre-LOC rho. Every record carries
``s7p_first_t_s``: the first LEVEL step where S7' alone held (V-1 compares it, H-8 reads it).

Confirmation 1 (rules 4): ``lower_estimate_N`` is L-hat of rules 1.1.
  ``verdict_runs.LoggedController._logged_lower_estimate_N`` logs
  ``self._load_estimate_N(self._state.last_forces.lower)`` after ``update``. In ``c2.py``
  ``_read`` sets ``state.last_forces = forces`` and builds the reading with
  ``cylinder_force_lower_N = forces.lower`` (the same array), so the logged input is
  ``reading.cylinder_force_lower_N``. ``_load_estimate_N`` subtracts ``_leg_seal_bands_N()`` =
  ``TwoPressureMonitor.leg_seal_bands_N(state.seal_band_N)``: ``state.seal_band_N`` is assigned
  only after a probe round (``c2.py`` ``_update_seal_band`` path, PROBE phase), and the
  fallback legs change only in ``TwoPressureMonitor.read`` (``_diagnose_sensors``,
  ``_check_moving``, ``_check_physical_lower_bound``) or ``probe_round_finished`` (PROBE). In a
  LEVEL update neither runs after ``_read``, so the value logged after the update equals the one
  the wrapper reads inside ``_level_step``. (``ContactJudge.PRESSURE`` returns the reading
  unchanged in both.) The ``--gate-npz-dir`` records use the same logger; V-1 checks it on runs.
Confirmation 2 (rules 4): in a soil-response run before the LOC every LEVEL step has
  ``in_crawler_zone`` true at the wrapper point. ``_level_step`` calls
  ``_update_crawler_zone`` (before ``_apply_pre_loc_lift_pause``); with ``config.soil.enable`` it
  ends with ``_hold_crawler_zone_until_liftoff``, which returns early only when
  ``soil.is_liftoff_confirmed``; otherwise a released latch is set back
  (``state.in_crawler_zone = True``, starting the soil mode). S3 (no LOC in the run) implies no
  LOC confirmed now, so S1 and S2 and S3 give S5. The instrumented runs count the steps where
  this failed (``las.gates.zone_false_with_s1_s3``, V-1 requires 0).
Same-time order: every event above is raised at ``reading.t_s`` = ``t_s[k]`` and, except the
  LOC revocation (after the command, not read here), before the wrapper point of that update.

Usage (dynamics-dev python, project root):
  python -I -B .../las_shadow.py r2 --t4h DIR_OR_NPZ ... --out <r2 json> [--workers 4]
  python -I -B .../las_shadow.py judge (--t4h DIR_OR_NPZ ... | --jsonl X --t4h-dir D)
      [--r2 <r2 json>] [--candidate b0 | custom --alpha ...] [--workers 4] --out <jsonl>
  python -I -B .../las_shadow.py v1 --instrumented <las_V1.jsonl> --npz-dir DIR [--r2 <json>]
  python -I -B .../las_shadow.py v2 --shadow <judge out jsonl> [--count 3] [--candidate b0]
      [--workers 3] [--affinity HEX] --out <jsonl>
The last stdout line is JSON. Exit codes: 0 done / check passed, 1 check failed (r2 rejected or
a validation record could not be rebuilt, judge over the R-5 undecidable limit, V-1, V-2) or
run errors, 2 input error.
"""
from __future__ import annotations

import argparse
import functools
import json
import sys
from dataclasses import dataclass
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import las_targeted as lt  # noqa: E402  (first: sets the one-thread variables numpy reads)
import numpy as np  # noqa: E402

FIRES = "fires"
SILENT = "silent"
UNDECIDABLE = "undecidable"
MODE_STORED = "stored"
MODE_EXACT = "exact"
MODE_BAND = "band"
MODE_REJECT = "reject"
EXACT_LIMIT_N = 1.0
"""rev1 R-3: R-2 delta up to 1 N evaluates the rebuilt L-hat as it is."""
BAND_LIMIT_N = 500.0
"""rev1 R-4 / R-5: up to 500 N the gate is widened by delta; beyond, undecidable."""
UNDECIDABLE_LIMIT = 100
"""rev1 R-5: more undecidable records than this -> stop and ask (sealed H-5 extended)."""
SUM_BAND_FACTOR = 4.0
MIN_BAND_FACTOR = 1.0
RHO_BAND_FACTOR = 8.0
RISE_BAND_FACTOR = 16.0
"""rev1 R-4 widening: sum - 4 delta, min + delta, rho - 8 delta / sum, rise - 16 delta / sum."""
LOC_EVENTS = ("crawler_liftoff_confirmed", "INFO_SOIL_STATE_RESTORED")
SOIL_MODE_EVENT = "soil_mode_start"
S4_FAULT_EVENT = "WARN_CRAWLER_LIFTOFF_UNCONFIRMED"
REAPPROACH_START = "leg_reapproach_start"
REAPPROACH_ENDS = ("leg_reapproach_contact", "WARN_LEG_REAPPROACH_NO_CONTACT")
REAPPROACH_PHASES = ("level", "done", "probe", "ready")
RELEVEL_FROM = ("done", "probe", "ready")
RELEVEL_TO = ("level", "fault", "fault_reground")
BASE_ARRAYS = ("t_s", "phase", "meta_json")
REBUILD_ARRAYS = ("t_s", "phase", "command_m_s", "head_pressure_Pa", "rod_pressure_Pa",
                  "motor_stroke_m", "seal_band_N")
"""What ``contact_replay.replay_fallback_monitor`` and the L-hat transform read."""
REBUILD_META = ("events", "two_pressure_settings", "hydraulic_options")
TIME_TOLERANCE_S = 1e-9
RIGID_GROUP_TOKEN = "|H-R-0|"
"""Composite-key token of the uniform hard-ground rows (rev1 6 H-8)."""
V1_MIN_RECORDS = 10
V1_MIN_EACH = 3
V1_MIN_REBUILT = 3
"""rev1 R-6: V-1 holds at least 3 records judged on the rebuild path."""
V2_COUNT = 3


# ------------------------------------------------------------------------------- record
@dataclass(frozen=True)
class RebuildSetting:
    """The R-2 result a judge applies to every rebuilt record."""

    delta_N: float
    mode: str

    @classmethod
    def from_r2(cls, path: Path) -> RebuildSetting:
        report = json.loads(path.read_text(encoding="utf-8"))
        return cls(float(report["max_abs_N"]), str(report["mode"]))


def rebuild_mode(delta_N: float) -> str:
    """``exact`` / ``band`` / ``reject`` of an R-2 delta (rev1 R-3 .. R-5)."""
    if not np.isfinite(delta_N) or delta_N > BAND_LIMIT_N:
        return MODE_REJECT
    return MODE_EXACT if delta_N <= EXACT_LIMIT_N else MODE_BAND


@dataclass(frozen=True)
class ShadowRecord:
    """The fields of one T4h record the gate needs."""

    name: str
    t_s: np.ndarray
    phase: np.ndarray
    lower_estimate_N: np.ndarray
    events: list[tuple[float, str]]
    F_min_N: float
    weight_ref_N: float | None
    soil_enable: bool | None
    job: dict | None
    commands_sha256: str | None
    mode: str = MODE_STORED
    delta_N: float = 0.0
    """The widening of the gate (0 except in band mode)."""


class _LoadEstimateView:
    """What ``C2Controller._load_estimate_N`` reads of ``self`` in one update: the contact
    judge of the run's config and the per-leg seal bands stored for that update."""

    def __init__(self, config, seal_bands_N: np.ndarray) -> None:
        self.config = config
        self._seal_bands_N = seal_bands_N

    def _leg_seal_bands_N(self) -> np.ndarray:
        return self._seal_bands_N


def load_estimate_transform(config, lower_N: np.ndarray, seal_band_N: np.ndarray) -> np.ndarray:
    """L-hat per update through the controller's own ``_load_estimate_N`` (module docstring)."""
    from outrigger_sim.control import c2

    rows = [c2.C2Controller._load_estimate_N(_LoadEstimateView(config, band), lower)
            for lower, band in zip(np.asarray(lower_N, float),
                                   np.asarray(seal_band_N, float), strict=True)]
    return np.array(rows, float).reshape(-1, 4)


def transform_name(config) -> str:
    from outrigger_sim.control.c2 import ContactJudge

    if config.contact is ContactJudge.PRESSURE:
        return "identity (ContactJudge.PRESSURE)"
    return f"lower - seal_band_N ({config.contact.name}: _leg_seal_bands_N after the update)"


def replay_gap(arrays: dict, meta: dict | None) -> str | None:
    """Why the own-event replay cannot run on a record (None = it can)."""
    missing = [field for field in REBUILD_ARRAYS if field not in arrays]
    missing += [f"meta.{field}" for field in REBUILD_META if (meta or {}).get(field) is None]
    if missing:
        return f"missing {missing}"
    if not np.isfinite(np.asarray(arrays["rod_pressure_Pa"], float)).any():
        # a head-only run (V0, D-1 rows): the replay monitor reads the rod side on every row
        return "missing rod-side pressure readings (head-only run)"
    return None


def rebuilt_load_estimate_N(arrays: dict, meta: dict, name: str) -> tuple[np.ndarray, object]:
    """rev1 R-1: (L-hat per update, run config) from the own-event replay of a record.

    Raises:
        KeyError: A field the replay needs is missing.
        RuntimeError: The rebuilt monitor settings differ from the stored ones.
        ValueError: The replay cannot run on the record (``t4h_replay`` / ``contact_replay``).
    """
    import t4h_replay as tr

    why = replay_gap(arrays, meta)
    if why is not None:
        raise KeyError(why)
    closed_loop, config, _ = tr.checked_run_config(name, meta)
    allowance = tr.offset_allowance_of(meta, config)
    lower = tr.own_event_replay_lower_N(arrays, meta, closed_loop, config, allowance)
    return load_estimate_transform(config, lower, arrays["seal_band_N"]), config


def _load_npz(path: Path) -> tuple[dict, dict | None]:
    with np.load(path, allow_pickle=False) as data:
        arrays = {name: np.asarray(data[name]) for name in data.files if name != "meta_json"}
        meta = json.loads(str(data["meta_json"])) if "meta_json" in data.files else None
    return arrays, meta


def read_record(path: Path, rebuild: RebuildSetting | None = None
                ) -> tuple[ShadowRecord | None, str | None]:
    """(record, None) or (None, why it cannot be judged)."""
    arrays, meta = _load_npz(path)
    missing = [name for name in BASE_ARRAYS if name != "meta_json" and name not in arrays]
    if meta is None:
        missing.append("meta_json")
    if "lower_estimate_N" not in arrays and rebuild is None:
        missing.append("lower_estimate_N")
    if missing:
        return None, f"missing {missing}"
    if "events" not in meta:
        return None, "missing meta events"
    if meta.get("F_min_N") is None:
        return None, "missing meta F_min_N"
    if "lower_estimate_N" in arrays:
        estimate = np.asarray(arrays["lower_estimate_N"], float).reshape(-1, 4)
        return _shadow_record(path, arrays, meta, estimate, MODE_STORED, 0.0), None
    return rebuilt_record(path, arrays, meta, rebuild)


def rebuilt_record(path: Path, arrays: dict, meta: dict, rebuild: RebuildSetting
                   ) -> tuple[ShadowRecord | None, str | None]:
    """The record judged on the rebuild path (rev1 R-1, R-3 .. R-5), or why it cannot be."""
    if rebuild.mode == MODE_REJECT:
        return None, f"R-5: R-2 delta {rebuild.delta_N:.3f} N > {BAND_LIMIT_N:g} N"
    try:
        estimate, _ = rebuilt_load_estimate_N(arrays, meta, path.name)
    except (KeyError, RuntimeError, ValueError) as exc:
        return None, f"R-5: rebuild failed: {exc}"
    delta_N = rebuild.delta_N if rebuild.mode == MODE_BAND else 0.0
    return _shadow_record(path, arrays, meta, estimate, rebuild.mode, delta_N), None


def _shadow_record(path: Path, arrays: dict, meta: dict, estimate: np.ndarray, mode: str,
                   delta_N: float) -> ShadowRecord:
    return ShadowRecord(
        name=path.name, t_s=np.asarray(arrays["t_s"], float),
        phase=np.asarray(arrays["phase"]).astype(str), lower_estimate_N=estimate,
        events=[(float(t), str(name)) for t, name in meta.get("events") or []],
        F_min_N=meta.get("F_min_N"), weight_ref_N=meta.get("W_ref_N"),
        soil_enable=meta.get("soil_enable"), job=meta.get("job"),
        commands_sha256=meta.get("commands_sha256"), mode=mode, delta_N=delta_N)


_YAML_WEIGHT: dict = {}


def yaml_weight_ref_N() -> float:
    """``C2Controller._reference_weight_N`` from the YAML (superstructure mass x g)."""
    if "W" not in _YAML_WEIGHT:
        from outrigger_sim.params import load_params
        from outrigger_sim.sensors.imu import STANDARD_GRAVITY_M_S2

        mass_kg = load_params().superstructure.mass_properties.mass_kg
        _YAML_WEIGHT["W"] = float(mass_kg) * STANDARD_GRAVITY_M_S2
    return _YAML_WEIGHT["W"]


# ------------------------------------------------------------------------------- gates
def _events_at(events: list[tuple[float, str]], t_s: float) -> list[str]:
    return [name for t, name in events if abs(t - t_s) <= TIME_TOLERANCE_S]


def level_step_flags(phase: np.ndarray) -> np.ndarray:
    """Whether update k ran ``_level_step`` (module docstring)."""
    flags = np.zeros(len(phase), bool)
    for k in range(1, len(phase)):
        entering, after = phase[k - 1], phase[k]
        flags[k] = entering == "level" or (entering in RELEVEL_FROM and after in RELEVEL_TO)
    return flags


def reapproach_active(record: ShadowRecord) -> np.ndarray:
    """Whether a re-approach is active at the wrapper point of update k (S6 false)."""
    active: set[str] = set()
    out = np.zeros(len(record.t_s), bool)
    by_time: dict[int, list[str]] = {}
    for t, name in record.events:
        k = int(np.searchsorted(record.t_s, t - TIME_TOLERANCE_S))
        if k < len(record.t_s) and abs(record.t_s[k] - t) <= TIME_TOLERANCE_S:
            by_time.setdefault(k, []).append(name)
    for k in range(len(record.t_s)):
        entering = record.phase[k - 1] if k else ""
        if entering not in REAPPROACH_PHASES:
            active.clear()
        for name in by_time.get(k, []):
            head, _, leg = name.partition(":")
            if head == REAPPROACH_START:
                active.add(leg)
            elif head in REAPPROACH_ENDS:
                active.discard(leg)
        out[k] = bool(active)
    return out


def _first_time(events: list[tuple[float, str]], heads: tuple[str, ...]) -> float | None:
    times = [t for t, name in events if name.split(":")[0] in heads]
    return min(times) if times else None


def twist_ratios(loads_N: np.ndarray) -> np.ndarray:
    """rho_k per update with the wrapper's own function (``lt.diagonal_deficit_ratio``)."""
    return np.array([lt.diagonal_deficit_ratio(row)[0] for row in loads_N], float)


def s7_prime(loads_N: np.ndarray, level: np.ndarray, params: lt.LasParams, weight_N: float,
             F_min_N: float, delta_N: float = 0.0) -> np.ndarray:
    """S7' per update (rev1 2), widened by ``delta_N`` as rev1 R-4 (0 = exact)."""
    sums = loads_N.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        is_sum = sums >= params.alpha * weight_N - SUM_BAND_FACTOR * delta_N
        is_min = loads_N.min(axis=1) < params.beta * F_min_N + MIN_BAND_FACTOR * delta_N
        if params.rho_on is None:
            return is_sum & is_min & np.isfinite(loads_N).all(axis=1)
        rho = twist_ratios(loads_N)
        previous_rho = np.r_[np.nan, rho[:-1]]
        has_previous = np.r_[False, level[:-1]]
        is_high = rho >= params.rho_on - RHO_BAND_FACTOR * delta_N / sums
        is_rising = rho - previous_rho > -RISE_BAND_FACTOR * delta_N / sums
    return is_sum & is_min & has_previous & is_high & is_rising & np.isfinite(loads_N).all(axis=1)


def gate_matrix(record: ShadowRecord, params: lt.LasParams) -> dict[str, np.ndarray]:
    """S1 .. S8 per update (booleans) and the LEVEL-step flag."""
    t_s = record.t_s
    count = len(t_s)
    weight_N = record.weight_ref_N if record.weight_ref_N is not None else yaml_weight_ref_N()
    soil = True if record.soil_enable is None else bool(record.soil_enable)
    level = level_step_flags(record.phase)
    s4_fault = np.array([S4_FAULT_EVENT in [n.split(":")[0] for n in _events_at(record.events, t)]
                         for t in t_s], bool)
    t_loc = _first_time(record.events, LOC_EVENTS)
    t_soil = _first_time(record.events, (SOIL_MODE_EVENT,))
    return {
        "level": level,
        "S1": np.full(count, soil),
        "S2": level & ~s4_fault,
        "S3": np.array([t_loc is None or t < t_loc - TIME_TOLERANCE_S for t in t_s], bool),
        "S4": np.array([t_soil is None or t < t_soil - TIME_TOLERANCE_S for t in t_s], bool),
        "S5": np.ones(count, bool),
        "S6": ~reapproach_active(record),
        "S7": s7_prime(record.lower_estimate_N, level, params, weight_N, record.F_min_N,
                       record.delta_N),
        "S8": np.ones(count, bool),
    }


def _max_pre_loc_rho(record: ShadowRecord, gates: dict[str, np.ndarray]) -> float | None:
    rows = np.flatnonzero(gates["S2"] & gates["S3"])
    if not rows.size:
        return None
    rho = twist_ratios(record.lower_estimate_N[rows])
    return float(np.nanmax(rho)) if np.isfinite(rho).any() else None


def shadow_judge(record: ShadowRecord, params: lt.LasParams) -> dict:
    """``fires`` / ``silent`` / ``undecidable`` of one record and why."""
    gates = gate_matrix(record, params)
    names = lt.GATE_NAMES
    stacked = np.stack([gates[name] for name in names], axis=1)
    before_s7 = stacked[:, :6].all(axis=1)
    has_nan_where_needed = bool((before_s7 & ~np.isfinite(record.lower_estimate_N).all(axis=1))
                                .any())
    fired = np.flatnonzero(stacked.all(axis=1))
    s7_alone = np.flatnonzero(gates["S2"] & gates["S7"])
    assumptions = []
    if record.weight_ref_N is None:
        assumptions.append("W_ref from YAML")
    if record.soil_enable is None:
        assumptions.append("S1 assumed true")
    out = {"file": record.name, "job": record.job, "commands_sha256": record.commands_sha256,
           "assumptions": assumptions, "mode": record.mode, "delta_N": record.delta_N,
           "s7p_first_t_s": float(record.t_s[s7_alone[0]]) if s7_alone.size else None}
    if fired.size:
        k = int(fired[0])
        return {**out, "status": FIRES, "first_fire_t_s": float(record.t_s[k])}
    if has_nan_where_needed:
        return {**out, "status": UNDECIDABLE, "reason": "lower_estimate_N NaN where S1 .. S6 hold"}
    level_rows = np.flatnonzero(gates["S2"])
    false_counts = {name: int((~gates[name][level_rows]).sum()) for name in names}
    closest = None
    if level_rows.size:
        misses = (~stacked[level_rows]).sum(axis=1)
        best = int(level_rows[int(np.argmin(misses))])
        closest = {"t_s": float(record.t_s[best]),
                   "false": [name for name in names if not gates[name][best]]}
    return {**out, "status": SILENT, "first_fire_t_s": None,
            "blocked": {"level_steps": int(level_rows.size), "false_counts": false_counts,
                        "closest": closest, "max_pre_loc_rho": _max_pre_loc_rho(record, gates)}}


def judge_file(path: Path, params: lt.LasParams, rebuild: RebuildSetting | None = None) -> dict:
    record, why = read_record(path, rebuild)
    if record is None:
        return {"file": path.name, "status": UNDECIDABLE, "reason": why}
    return shadow_judge(record, params)


# ------------------------------------------------------------------------------- inputs
def npz_files(paths: list[Path]) -> list[Path]:
    out = []
    for path in paths:
        out += sorted(path.rglob("*.npz")) if path.is_dir() else [path]
    return out


def files_of_jsonl(jsonl: Path, t4h_dir: Path) -> list[tuple[dict, Path | None]]:
    """(line, npz or None) per line: ``t4h_file`` (run_v5) or ``las.gate_npz``."""
    out = []
    for text in jsonl.read_text(encoding="utf-8").splitlines():
        line = json.loads(text)
        name = line.get("t4h_file") or (line.get("las") or {}).get("gate_npz")
        out.append((line, None if name is None else t4h_dir / name))
    return out


def params_from_args(args) -> lt.LasParams:
    (_, params), = lt.resolve_candidates([args.candidate], args)
    if params.kind != lt.KIND_LASB:
        raise ValueError("the shadow judge is defined for LAS-b variants only")
    return params


def _map(function, items: list, workers: int) -> list:
    """``function`` over ``items`` in order, in ``workers`` spawned processes (1 = here)."""
    if workers <= 1 or len(items) <= 1:
        return [function(item) for item in items]
    with get_context("spawn").Pool(workers) as pool:
        return pool.map(function, items, chunksize=1)


def _status_counts(results: list[dict]) -> dict[str, int]:
    return {status: sum(r["status"] == status for r in results)
            for status in (FIRES, SILENT, UNDECIDABLE)}


def _mode_counts(results: list[dict]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for result in results:
        if result["status"] == UNDECIDABLE:
            continue
        by_status = out.setdefault(result["mode"], {FIRES: 0, SILENT: 0})
        by_status[result["status"]] += 1
    return out


def run_judge(args) -> int:
    params = params_from_args(args)
    rebuild = None if args.r2 is None else RebuildSetting.from_r2(args.r2)
    judge = functools.partial(judge_file, params=params, rebuild=rebuild)
    if args.jsonl is not None:
        pairs = files_of_jsonl(args.jsonl, args.t4h_dir)
        present = [path for _, path in pairs if path is not None and path.exists()]
        judged = dict(zip(present, _map(judge, present, args.workers), strict=True))
        results = [judged[path] if path in judged else
                   {"file": None if path is None else path.name, "job": line["job"],
                    "status": UNDECIDABLE, "reason": "no T4h record"} for line, path in pairs]
    else:
        results = _map(judge, npz_files(args.t4h), args.workers)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, default=str) + "\n")
    counts = _status_counts(results)
    reasons: dict[str, int] = {}
    for result in results:
        if result["status"] == UNDECIDABLE:
            reason = result["reason"].split(":")[0] if result["reason"].startswith("R-5") \
                else result["reason"]
            reasons[reason] = reasons.get(reason, 0) + 1
    is_over_limit = counts[UNDECIDABLE] > UNDECIDABLE_LIMIT
    print(f"{len(results)} records: {counts}; by mode {_mode_counts(results)}; "
          f"undecidable reasons {reasons}")
    print(json.dumps({"command": "judge", "params": params.to_dict(), "records": len(results),
                      **counts, "by_mode": _mode_counts(results),
                      "rebuild": None if rebuild is None else vars(rebuild),
                      "undecidable_reasons": reasons, "stop_R5": is_over_limit,
                      "out": str(args.out)}))
    return 1 if is_over_limit else 0


# ------------------------------------------------------------------------------- R-2
def _pre_loc_level_rows(phase: np.ndarray, t_s: np.ndarray, events) -> np.ndarray:
    t_loc = _first_time(events, LOC_EVENTS)
    before_loc = t_s < np.inf if t_loc is None else t_s < t_loc - TIME_TOLERANCE_S
    return level_step_flags(phase) & before_loc


def _abs_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """|a - b|; NaN in both counts as equal, NaN in one as an infinite difference."""
    both_nan = np.isnan(a) & np.isnan(b)
    difference = np.abs(a - b)
    return np.where(both_nan, 0.0, np.where(np.isnan(difference), np.inf, difference))


def r2_record(path: Path) -> dict:
    """R-2 of one record with a stored L-hat: max |rebuilt - stored| over its pre-LOC LEVEL
    steps, and the transform check on its own lower reading."""
    arrays, meta = _load_npz(path)
    if "lower_estimate_N" not in arrays or meta is None:
        return {"file": path.name, "status": "no stored L-hat"}
    try:
        rebuilt, config = rebuilt_load_estimate_N(arrays, meta, path.name)
    except (KeyError, ValueError) as exc:
        # outside the replay domain (R-5 for a judged record): a missing field, a head-only
        # run, or a record this code refuses to replay (e.g. a ③ bound meta of revision 3)
        return {"file": path.name, "status": "not replayable", "reason": repr(exc)}
    except RuntimeError as exc:  # rebuilt settings differ from the stored ones
        return {"file": path.name, "status": "failed", "reason": repr(exc)}
    stored = np.asarray(arrays["lower_estimate_N"], float).reshape(-1, 4)
    events = [(float(t), str(name)) for t, name in meta.get("events") or []]
    rows = _pre_loc_level_rows(np.asarray(arrays["phase"]).astype(str),
                               np.asarray(arrays["t_s"], float), events)
    difference = _abs_difference(rebuilt, stored)[rows]
    out = {"file": path.name, "status": "compared", "rows": int(rows.sum()),
           "max_abs_N": float(difference.max()) if difference.size else 0.0,
           "transform": transform_name(config)}
    if "lower_reading_N" in arrays:
        own = load_estimate_transform(config, arrays["lower_reading_N"], arrays["seal_band_N"])
        out["transform_max_abs_N"] = float(_abs_difference(own, stored).max())
    return out


def r2_verdict(rows: list[dict]) -> dict:
    compared = [row for row in rows if row["status"] == "compared"]
    failed = [row for row in rows if row["status"] == "failed"]
    delta_N = max((row["max_abs_N"] for row in compared), default=float("nan"))
    transform_values = [row["transform_max_abs_N"] for row in compared
                        if "transform_max_abs_N" in row]
    worst = max(compared, key=lambda row: row["max_abs_N"], default=None)
    not_replayable = sum(row["status"] == "not replayable" for row in rows)
    return {"command": "r2", "records": len(compared), "failed": len(failed),
            "not_replayable": not_replayable,
            "without_stored": len(rows) - len(compared) - len(failed) - not_replayable,
            "compared_rows": sum(row["rows"] for row in compared), "max_abs_N": delta_N,
            "mode": rebuild_mode(delta_N) if compared else MODE_REJECT,
            "worst_file": None if worst is None else worst["file"],
            "transform_max_abs_N": max(transform_values) if transform_values else None,
            "transforms": sorted({row["transform"] for row in compared})}


def run_r2(args) -> int:
    rows = _map(r2_record, npz_files(args.t4h), args.workers)
    verdict = r2_verdict(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({**verdict, "rows": rows}, indent=1), encoding="utf-8")
    for row in rows:
        if row["status"] != "compared" or row["max_abs_N"] > EXACT_LIMIT_N:
            print(f"{row['file']}: {row['status']} {row.get('max_abs_N', row.get('reason'))}")
    print(json.dumps({**verdict, "out": str(args.out)}))
    return 0 if verdict["mode"] != MODE_REJECT and not verdict["failed"] else 1


# ------------------------------------------------------------------------------- V-1
def _same_time(a: float | None, b: float | None) -> bool:
    return (a is None and b is None) or (
        a is not None and b is not None and abs(a - b) <= TIME_TOLERANCE_S)


def _rebuilt_match(online: float | None, offline: dict,
                   online_s7p: float | None = None) -> tuple[bool, bool]:
    """(match, band extra fire) of a rebuild-path judge against the online first times.

    Exact mode must give the same start-gate time and the same first S7'-alone time. Band
    mode is widened to the safe side: an online start must be found at or before its time; a
    band fire without an online start is an extra fire (counted, not a mismatch)."""
    off_t = offline.get("first_fire_t_s")
    if offline["status"] == UNDECIDABLE:
        return False, False
    if offline["mode"] != MODE_BAND:
        is_same = (_same_time(online, off_t)
                   and _same_time(online_s7p, offline.get("s7p_first_t_s")))
        return is_same, False
    if online is None:
        return True, off_t is not None
    return off_t is not None and off_t <= online + TIME_TOLERANCE_S, False


def v1_compare(line: dict, npz_dir: Path, rebuild: RebuildSetting | None) -> dict:
    """In-run first S1 .. S7' time against the offline judge of the run's own record (stored
    L-hat, and the rebuilt one when ``rebuild`` is given); S7' alone likewise."""
    las = line.get("las") or {}
    params = lt.LasParams.from_dict(las["params"])
    gates = las.get("gates") or {}
    online = gates.get("first_s1_s7_t_s")
    online_s7p = (las.get("s7p_first") or {}).get("t_s")
    path = npz_dir / las["gate_npz"]
    offline = judge_file(path, params)
    is_same = (_same_time(online, offline.get("first_fire_t_s"))
               and _same_time(online_s7p, offline.get("s7p_first_t_s")))
    row = {"key": las.get("key"), "file": las["gate_npz"], "setting": line["job"].get("setting"),
           "online_first_s": online, "offline_first_s": offline.get("first_fire_t_s"),
           "online_s7p_s": online_s7p, "offline_s7p_s": offline.get("s7p_first_t_s"),
           "s7p_first": las.get("s7p_first"), "offline_status": offline["status"],
           "zone_false_with_s1_s3": gates.get("zone_false_with_s1_s3"),
           "match": bool(is_same and offline["status"] != UNDECIDABLE
                         and gates.get("zone_false_with_s1_s3") == 0)}
    if rebuild is None:
        return row
    arrays, meta = _load_npz(path)
    gap = replay_gap(arrays, meta)
    row["rebuilt_applicable"] = gap is None
    if gap is None:  # the same run on the rebuild path (its stored L-hat unused)
        record, why = rebuilt_record(path, arrays, meta, rebuild)
        rebuilt = ({"status": UNDECIDABLE, "reason": why, "mode": None} if record is None
                   else shadow_judge(record, params))
        is_match, is_extra = _rebuilt_match(online, rebuilt, online_s7p)
        row.update(rebuilt_mode=rebuilt.get("mode"), rebuilt_status=rebuilt["status"],
                   rebuilt_first_s=rebuilt.get("first_fire_t_s"),
                   rebuilt_s7p_s=rebuilt.get("s7p_first_t_s"),
                   rebuilt_reason=rebuilt.get("reason"), rebuilt_match=is_match,
                   rebuilt_band_extra_fire=is_extra)
    return row


def h8_record(rows: list[dict]) -> dict:
    """rev1 6 H-8: uniform hard-ground (H-R-0) records where S7' held. ``start_gate`` = S1 ..
    S7' in a LEVEL step (the start context, as rev1 3), ``s7p_alone`` = S7' alone; any
    ``start_gate`` entry stops before T-1."""
    rigid = [row for row in rows if RIGID_GROUP_TOKEN in (row["key"] or "")]
    start_gate = [row["key"] for row in rigid if row["online_first_s"] is not None]
    alone = [row["key"] for row in rigid if row["online_s7p_s"] is not None]
    return {"rigid_records": len(rigid), "start_gate": start_gate, "s7p_alone": alone,
            "stop": bool(start_gate)}


def v1_verdict(rows: list[dict]) -> dict:
    fires = sum(row["online_first_s"] is not None for row in rows)
    silent = sum(row["online_first_s"] is None for row in rows)
    settings = sorted({row["setting"] for row in rows})
    problems = []
    if len(rows) < V1_MIN_RECORDS:
        problems.append(f"{len(rows)} records < {V1_MIN_RECORDS}")
    if fires < V1_MIN_EACH or silent < V1_MIN_EACH:
        problems.append(f"fires {fires}, silent {silent} (>= {V1_MIN_EACH} each)")
    if not {"V0", "VB"} <= set(settings):
        problems.append(f"settings {settings} (VB and V0 needed)")
    mismatched = [row["key"] for row in rows if not row["match"]]
    if mismatched:
        problems.append(f"mismatch {mismatched}")
    rebuilt = [row for row in rows if row.get("rebuilt_applicable")]
    rebuilt_ok = [row for row in rebuilt if row["rebuilt_status"] != UNDECIDABLE]
    if len(rebuilt_ok) < V1_MIN_REBUILT:
        problems.append(f"{len(rebuilt_ok)} rebuild-path records < {V1_MIN_REBUILT} (R-6)")
    rebuilt_mismatched = [row["key"] for row in rebuilt if not row["rebuilt_match"]]
    if rebuilt_mismatched:
        problems.append(f"rebuild-path mismatch {rebuilt_mismatched}")
    return {"command": "v1", "records": len(rows), "fires": fires, "silent": silent,
            "settings": settings, "rebuilt_records": len(rebuilt_ok),
            "rebuilt_modes": sorted({str(row["rebuilt_mode"]) for row in rebuilt}),
            "rebuilt_band_extra_fires": sum(bool(row.get("rebuilt_band_extra_fire"))
                                            for row in rebuilt),
            "H-8": h8_record(rows), "passed": not problems, "problems": problems}


def run_v1(args) -> int:
    rebuild = None if args.r2 is None else RebuildSetting.from_r2(args.r2)
    lines = [json.loads(t) for t in args.instrumented.read_text(encoding="utf-8").splitlines()]
    good = [line for line in lines if "error" not in line and (line.get("las") or {})
            .get("mode") == lt.MODE_GATE and (line.get("las") or {}).get("gate_npz")]
    rows = [v1_compare(line, args.npz_dir, rebuild) for line in good]
    for row in rows:
        rebuilt = ("" if "rebuilt_match" not in row else
                   f" rebuilt {row['rebuilt_first_s']} S7' {row['rebuilt_s7p_s']} "
                   f"({row['rebuilt_mode']}, "
                   f"{'ok' if row['rebuilt_match'] else 'MISMATCH'})")
        print(f"{row['file']:<52} online {row['online_first_s']} offline {row['offline_first_s']} "
              f"S7' {row['online_s7p_s']}/{row['offline_s7p_s']} ({row['offline_status']}) "
              f"zone_false {row['zone_false_with_s1_s3']} "
              f"{'ok' if row['match'] else 'MISMATCH'}{rebuilt}")
    verdict = v1_verdict(rows)
    verdict["error_lines"] = len(lines) - len(good)
    verdict["rows"] = rows
    print(json.dumps(verdict, default=str))
    return 0 if verdict["passed"] else 1


# ------------------------------------------------------------------------------- V-2
def _is_rerunnable(job: dict | None) -> bool:
    """A ``run_v5`` job (``case``) or a D-1 job (``d1``); other stored jobs cannot rerun."""
    return bool(job) and ("case" in job or "d1" in job)


def pick_silent(shadow_lines: list[dict], count: int) -> list[dict]:
    """``count`` silent rerunnable records with a command hash, rebuild-path records first
    (rev1 R-6: the new path is the one to check), each group in file order."""
    picked = [line for line in shadow_lines if line["status"] == SILENT
              and _is_rerunnable(line.get("job")) and line.get("commands_sha256")]
    picked.sort(key=lambda line: line.get("mode", MODE_STORED) == MODE_STORED)
    return picked[:count]


def run_v2(args) -> int:
    params = params_from_args(args)
    shadow_lines = [json.loads(t) for t in args.shadow.read_text(encoding="utf-8").splitlines()]
    picked = pick_silent(shadow_lines, args.count)
    if len(picked) < args.count:
        print(json.dumps({"command": "v2", "error": f"{len(picked)} silent records with a job"}))
        return 2
    mask = None if args.affinity is None else int(args.affinity, 16)
    jobs = lt.with_las([dict(line["job"]) for line in picked], args.candidate, params,
                       lt.MODE_ACT, mask)
    import run_v5  # noqa: F401  (sys.path of the harness, as las_targeted.run_batch)
    import verdict_runs

    verdict_runs.warm_numba_cache()
    with get_context("spawn").Pool(args.workers, maxtasksperchild=1) as pool:
        reruns = pool.map(lt.run_las_job, jobs, chunksize=1)
    rows = []
    for line, rerun in zip(picked, reruns, strict=True):
        new_hash = rerun.get("commands_sha256")
        rows.append({"file": line["file"], "mode": line.get("mode"),
                     "stored": line["commands_sha256"], "rerun": new_hash,
                     "error": rerun.get("error"), "started": (rerun.get("las") or {})
                     .get("start_t_s"), "equal": new_hash == line["commands_sha256"]})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for rerun in reruns:
            rerun["job"].pop("mask", None)
            handle.write(json.dumps(rerun, default=str) + "\n")
    for row in rows:
        print(f"{row['file']} ({row['mode']}): stored {row['stored'][:12]} rerun "
              f"{str(row['rerun'])[:12]} {'equal' if row['equal'] else 'DIFFERENT'}")
    passed = all(row["equal"] for row in rows)
    print(json.dumps({"command": "v2", "passed": passed, "rows": rows}))
    return 0 if passed else 1


# ------------------------------------------------------------------------------- CLI
def _add_candidate_args(parser) -> None:
    parser.add_argument("--candidate", default="b0")
    for name in ("--alpha", "--beta", "--gamma", "--alpha-end", "--t-max", "--rho-on"):
        parser.add_argument(name, type=float)
    parser.add_argument("--n-end", type=int)


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    r2 = sub.add_parser("r2", help="R-2: rebuilt against stored L-hat (sets the judge mode)")
    r2.add_argument("--t4h", type=Path, nargs="+", required=True)
    r2.add_argument("--out", type=Path, required=True)
    r2.add_argument("--workers", type=int, default=1)
    judge = sub.add_parser("judge", help="fires / silent / undecidable per record")
    judge.add_argument("--t4h", type=Path, nargs="*", default=[])
    judge.add_argument("--jsonl", type=Path, default=None)
    judge.add_argument("--t4h-dir", type=Path, default=None)
    judge.add_argument("--r2", type=Path, default=None, help="r2 output: rebuild L-hat")
    judge.add_argument("--workers", type=int, default=1)
    judge.add_argument("--out", type=Path, required=True)
    _add_candidate_args(judge)
    v1 = sub.add_parser("v1", help="instrumented runs against the offline judge")
    v1.add_argument("--instrumented", type=Path, required=True)
    v1.add_argument("--npz-dir", type=Path, required=True)
    v1.add_argument("--r2", type=Path, default=None, help="r2 output: also the rebuild path")
    v2 = sub.add_parser("v2", help="rerun silent records with the variant, compare hashes")
    v2.add_argument("--shadow", type=Path, required=True)
    v2.add_argument("--count", type=int, default=V2_COUNT)
    v2.add_argument("--workers", type=int, default=V2_COUNT)
    v2.add_argument("--affinity", default=None)
    v2.add_argument("--out", type=Path, required=True)
    _add_candidate_args(v2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.command == "r2":
            return run_r2(args)
        if args.command == "judge":
            if (args.jsonl is None) == (not args.t4h):
                raise ValueError("give --t4h or --jsonl with --t4h-dir")
            if args.jsonl is not None and args.t4h_dir is None:
                raise ValueError("--jsonl needs --t4h-dir")
            return run_judge(args)
        if args.command == "v1":
            return run_v1(args)
        return run_v2(args)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"command": args.command, "error": repr(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
