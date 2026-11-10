"""T4h replay of harness records (v5 criteria 9, X-10; control-expert definition B).

Each ``t4h/<row>_<phase>_<setting>.npz`` (``run_v5`` VB / LS runs) holds the 10 Hz controller
inputs and outputs and the 1 ms truth at the samples. The two-pressure monitor of the run's
setting (harness preset + ``apply_lock_window`` of its options; the stored monitor settings
must be equal) is run offline with the rod-side fallback forced on all four legs from the first
row (``contact_replay.replay_fallback_monitor``). Judged samples (user decision 2026-11-06): a
zero acting command and the plant leg locked at t_k. Values: per leg the judged samples where
``lower - true_force_N > 0.6 kN`` (0 = provisional pass) and the largest ``lower - true_force_N``.
Zero-command samples whose leg is not locked yet (the valve tail; the Chrono T4 / T5 rule) are
recorded only (``unlocked_tail_*``), as is the ``lower - true_force_min_N`` value.

E-6 pressure-zero allowance (user decision 2026-11-08): the monitor deducts it from the lower
bound after the zero calibration, so the replay does too (:func:`offset_allowance_of`). A record
with ``pressure_offset_allowance_N`` / ``pressure_offset_allowance_from_s`` (written since
2026-11-08) uses them; an older one rebuilds them from its events: the setting's
``failure_allowance_N`` (front 5.5, rear 4.0 kN) on the legs the calibration skipped or found
implausible, from the time of the calibration events. Records without a failed leg replay as
before. ``--check-recorded`` also replays a record with the run's own events and reports the
largest difference to the run's own lower reading (``lower_reading_N``, r79 Dg-3 records).

Usage (dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/t4h_replay.py <out_json> <npz or folder> [...]
      [--extend-start tracked_bound|constant]   (③ start rule override)
``record`` (criteria revision 8 2 #3): ``T4h`` = the run's own monitor setting, rebuilt from its
meta (③ on for the revision 8 VB / LS records, the judged value) or the ``tracked_bound``
override; ``T4h-const`` = the ``constant`` override (③ off replay, a record).
      [--check-recorded]               (own-event replay against lower_reading_N)
``aggregate_v5`` reads ``<batch>/t4h/t4h_replay.json`` (write the output there for its table).
J-P3 (criteria revision 9, ``j_p3_inputs.j_p3_over_rows``): every VB / LS record (tag
``final_C4G2_P3`` or job setting VB / LS) is expected; one without the own rule ``tracked_bound``
is a setting defect; the output carries ``runs_expected`` and ``runs_judged``.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "04_scripts" / "03_control" / "s9", ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from j_p3_inputs import harness_head_only_declared, is_p3_expected, j_p3_over_rows  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
EXCESS_LIMIT_N = 600.0
"""Criteria 9 T4h: lower bound <= truth + 0.6 kN."""
FALLBACK_EVENT = "WARN_ROD_PRESSURE_FALLBACK"
HARNESS_VALVE_TAU_S = 0.1
EXTEND_START_KEYS = ("extend_start_rule", "extend_start_bound")
"""Two-pressure meta keys of the ③ start option (present only with the option on)."""
EXTEND_START_CHOICES = ("constant", "tracked_bound")
ZERO_CALIBRATED_EVENT = "INFO_PRESSURE_ZERO_CALIBRATED"
ZERO_FAILED_EVENTS = ("WARN_PRESSURE_ZERO_SKIPPED", "WARN_PRESSURE_ZERO_IMPLAUSIBLE")
"""Per-leg outcome events of the zero calibration (``zero_calibration.ZeroCalibration.events``);
``WARN_PRESSURE_ZERO_SKIPPED:all:<reason>`` covers every leg."""
ALL_LEGS_TOKEN = "all"
IDEAL_TAG_INFIX = "_IDEAL-"
"""Ideal-sensor diagnosis records (``ideal_stage1_plan.md`` 8.7): their tag names no real
controller, so the gate and LAS-b settings cannot be rebuilt from it; they are refused."""


class IdealRecordError(ValueError):
    """A record of an ideal-sensor run (exit 2, nothing replayed)."""


def reject_ideal_record(meta: dict, name: str) -> None:
    """Raise :class:`IdealRecordError` when the record's ``controller_tag`` has ``_IDEAL-``."""
    tag = meta.get("controller_tag")
    if tag is not None and IDEAL_TAG_INFIX in str(tag):
        raise IdealRecordError(f"{name}: ideal-sensor record (controller_tag {tag!r}) is not "
                               "replayed")


class _Record:
    """The ``Episode`` view ``replay_fallback_monitor`` reads (arrays and meta)."""

    def __init__(self, arrays: dict, meta: dict) -> None:
        self._arrays, self.meta = arrays, meta

    def has(self, name: str) -> bool:
        return name in self._arrays

    def __getitem__(self, name: str) -> np.ndarray:
        return self._arrays[name]


def load_record(path: Path) -> tuple[dict, dict]:
    with np.load(path, allow_pickle=False) as data:
        arrays = {name: np.asarray(data[name]) for name in data.files if name != "meta_json"}
        meta = json.loads(str(data["meta_json"]))
    return arrays, meta


def run_config(meta: dict, extend_start: str | None = None):
    """C2Config of the run: harness preset + the controller options of its options (lock
    window, ③ start bound) or, for a ③-on record without the option key, the stored monitor
    rule; ``extend_start`` overrides the ③ start rule (``p3_extend_start_spec.md`` 4 #8).

    Raises:
        ValueError: ``tracked_bound`` on a run with M1c (review 2026-11-07, 2c).
    """
    import s9_soil_closed_loop as soil
    from params import load_params

    from outrigger_sim.control import c2
    from outrigger_sim.hydraulics.v5_options import (
        EXTEND_START_TRACKED_RULE,
        HydraulicOptions,
        apply_controller_options,
        check_extend_start,
        is_liftoff_slow_tag,
        is_order_gate_tag,
    )

    reject_ideal_record(meta, "run_config")
    closed_loop = soil._imports()[0]
    contact = (meta.get("job") or {}).get("contact") or "COMBINED"
    config = closed_loop.preset_config(c2.ContactJudge[contact], with_imu_samples=True,
                                       with_reapproach=True)
    # LAS-b switch (2026-11-08): replay the controller the record ran; records before the switch
    # carry no ``_LAS`` tag and replay with LAS-b off
    config = replace(config, liftoff_approach_slow=replace(
        config.liftoff_approach_slow,
        enable=is_liftoff_slow_tag(meta.get("controller_tag"))))
    # K1 switch (las_k1_rules_adopt.md 9.2): likewise the order gate only with a ``_K1`` tag
    config = replace(config, slope_clearance_margin=replace(
        config.slope_clearance_margin,
        flat_soil_margin_order_gate=is_order_gate_tag(meta.get("controller_tag"))))
    # read only: records of earlier M2 laws keep their lock window (the replay reruns no plant);
    # a record of the revision 8 VB / LS definition brings its ③ start bound
    options = HydraulicOptions.from_stored(meta["hydraulic_options"])
    config = apply_controller_options(config, options, load_params().v_max, HARNESS_VALVE_TAU_S)
    stored_rule = (meta.get("two_pressure_settings") or {}).get("extend_start_rule")
    if extend_start is None and stored_rule == EXTEND_START_TRACKED_RULE:
        # a ③-on run whose options predate the option key (Dg-3 v4): the stored monitor rule
        extend_start = stored_rule
    if extend_start is not None:
        check_extend_start(options, extend_start)
        config = replace(config, two_pressure=replace(config.two_pressure,
                                                      extend_start_rule=extend_start))
    return closed_loop, config


def _settings_for_comparison(settings: dict, stored: dict, extend_start: str | None) -> dict:
    """An override of another rule than the stored one changes only the ③ start keys: leave
    them out. The same rule compares them all (the bound ``revision`` included)."""
    stored_rule = stored.get("extend_start_rule", "constant")
    if extend_start is None or extend_start == stored_rule:
        return settings
    return {key: value for key, value in settings.items() if key not in EXTEND_START_KEYS}


def _plain(value):
    return json.loads(json.dumps(value, default=str))


def _failed_legs(name: str) -> list[int]:
    """Legs a zero-calibration outcome event marks as failed (empty for other events)."""
    if not name.startswith(ZERO_FAILED_EVENTS):
        return []
    leg_name = name.split(":")[1]
    return list(range(len(LEGS))) if leg_name == ALL_LEGS_TOKEN else [LEGS.index(leg_name)]


def rebuilt_offset_allowance(events: list, failure_allowance_N, setting_allowance_N):
    """E-6 allowance of a record written before the allowance was recorded.

    The controller sets ``max(setting allowance, failure_allowance_N on the failed legs)`` at
    the update that ends the calibration, where it also raises the outcome events; the
    deduction acts on the reads after it. A run with outcome events at more than one time
    (a restarted CHECK) is rebuilt from the first one (noted).

    Args:
        events: ``(t_s, name)`` controller events of the run (T4h meta ``events``).
        failure_allowance_N: ``ZeroCalibrationSettings.failure_allowance_N`` of the run.
        setting_allowance_N: ``C2Config.pressure_offset_allowance_N`` of the run.

    Returns:
        ``r5_fallback_replay.OffsetAllowance``.

    Raises:
        ValueError: A nonzero setting allowance (it acts from the start, which a single start
            time cannot express; harness presets carry 0).
    """
    from outrigger_sim.control.r5_fallback_replay import OffsetAllowance

    if np.any(np.asarray(setting_allowance_N, float) != 0.0):
        raise ValueError("nonzero pressure_offset_allowance_N setting: not rebuildable")
    outcomes = [(float(t), str(name)) for t, name in events
                if str(name).startswith((ZERO_CALIBRATED_EVENT, *ZERO_FAILED_EVENTS))]
    if not outcomes:
        return OffsetAllowance(np.zeros(len(LEGS)), None, "rebuilt: no zero calibration, 0")
    from_s = min(t for t, _ in outcomes)
    is_failed = np.zeros(len(LEGS), bool)
    for t_s, name in outcomes:
        if t_s == from_s:
            is_failed[_failed_legs(name)] = True
    deduction = np.where(is_failed, np.asarray(failure_allowance_N, float), 0.0)
    note = "rebuilt: failure_allowance_N on the skipped / implausible legs"
    if len({t for t, _ in outcomes}) > 1:
        note += " (outcome events at several times: the first calibration)"
    return OffsetAllowance(deduction, from_s, note)


def offset_allowance_of(meta: dict, config):
    """E-6 allowance of a record: the recorded fields, else :func:`rebuilt_offset_allowance`
    with the run's controller setting ``config``."""
    from outrigger_sim.control.r5_fallback_replay import OffsetAllowance

    recorded = meta.get("pressure_offset_allowance_N")
    if recorded is not None:
        return OffsetAllowance(np.asarray(recorded, float),
                               meta.get("pressure_offset_allowance_from_s"), "recorded")
    return rebuilt_offset_allowance(meta.get("events") or [],
                                    config.zero_calibration.failure_allowance_N,
                                    config.pressure_offset_allowance_N)


def own_event_replay_lower_N(arrays: dict, meta: dict, closed_loop, config,
                             allowance) -> np.ndarray:
    """Per-period lower reading of the replay with the run's own events (the
    ``--check-recorded`` path; ``las_shadow`` rebuilds L-hat from it)."""
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.control.contact_replay import replay_fallback_monitor

    events = [(float(t), str(name)) for t, name in meta.get("events") or []]
    replay = replay_fallback_monitor(_Record(arrays, meta), events,
                                     C2Geometry.from_params(closed_loop.PARAMS), config,
                                     offset_allowance_N=allowance.deduction_N,
                                     offset_allowance_from_s=allowance.from_s)
    return np.asarray(replay.lower_reading_N, float)


def recorded_lower_difference_N(arrays: dict, meta: dict, closed_loop, config,
                                allowance) -> float | None:
    """Largest ``|replay - lower_reading_N|`` of the replay with the run's own events (None
    without the run's lower reading); NaN in both counts as equal."""
    if "lower_reading_N" not in arrays:
        return None
    replayed = own_event_replay_lower_N(arrays, meta, closed_loop, config, allowance)
    recorded = arrays["lower_reading_N"]
    both_nan = np.isnan(replayed) & np.isnan(recorded)
    difference = np.where(both_nan, 0.0, np.abs(replayed - recorded))
    return float(np.max(difference)) if difference.size else 0.0


def checked_run_config(path_name: str, meta: dict, extend_start: str | None = None):
    """:func:`run_config` of a record after the stored-settings checks of :func:`replay_values`.

    Raises:
        RuntimeError: The rebuilt monitor settings differ from the stored ones (with
            ``extend_start``: apart from the ③ start keys).
    """
    from outrigger_sim.control.extend_start_bound import check_extend_start_meta

    stored = meta["two_pressure_settings"]
    check_extend_start_meta(stored)
    closed_loop, config = run_config(meta, extend_start)
    rebuilt = _plain(config.two_pressure.to_meta())
    if (_settings_for_comparison(rebuilt, stored, extend_start)
            != _settings_for_comparison(stored, stored, extend_start)):
        raise RuntimeError(f"{path_name}: rebuilt two_pressure settings differ from the record")
    return closed_loop, config, rebuilt


def replay_values(path: Path, extend_start: str | None = None,
                  check_recorded: bool = False) -> dict:
    """T4h values of one record (module docstring); ``check_recorded`` adds the own-event
    replay difference ``recorded_lower_max_abs_N``.

    Raises:
        RuntimeError: The rebuilt monitor settings differ from the stored ones (with
            ``extend_start``: apart from the ③ start keys).
    """
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.control.contact_replay import replay_fallback_monitor

    arrays, meta = load_record(path)
    reject_ideal_record(meta, path.name)
    stored = meta["two_pressure_settings"]
    closed_loop, config, rebuilt = checked_run_config(path.name, meta, extend_start)
    t_s = arrays["t_s"]
    forced = [(float(t_s[0]), f"{FALLBACK_EVENT}:{leg}") for leg in LEGS]
    geometry = C2Geometry.from_params(closed_loop.PARAMS)
    allowance = offset_allowance_of(meta, config)
    replay = replay_fallback_monitor(_Record(arrays, meta), forced, geometry, config,
                                     offset_allowance_N=allowance.deduction_N,
                                     offset_allowance_from_s=allowance.from_s)
    acting = np.zeros_like(arrays["command_m_s"])
    acting[1:] = arrays["command_m_s"][:-1]
    is_zero = acting == 0.0
    is_locked = np.asarray(arrays["locked"], bool)
    excess = replay.lower_reading_N - arrays["true_force_N"]
    zero_with_truth = is_zero & np.isfinite(excess)
    judged = zero_with_truth & is_locked
    unlocked_tail = zero_with_truth & ~is_locked
    over = judged & (excess > EXCESS_LIMIT_N)
    excess_min_basis = replay.lower_reading_N - arrays["true_force_min_N"]
    recorded = judged & np.isfinite(excess_min_basis)
    own_events = {} if not check_recorded else {
        "recorded_lower_max_abs_N": recorded_lower_difference_N(arrays, meta, closed_loop,
                                                                config, allowance)}
    return {"file": path.name, "samples": int(len(t_s)),
            "offset_allowance_N": allowance.deduction_N.tolist(),
            "offset_allowance_from_s": allowance.from_s,
            "offset_allowance_source": allowance.note, **own_events,
            "judged_samples_by_leg": _by_leg(judged.sum(axis=0)),
            "over_0p6kN_by_leg": _by_leg(over.sum(axis=0)),
            "over_0p6kN": int(over.sum()),
            "max_excess_N": _max_or_none(excess[judged]),
            "max_excess_vs_window_min_N": _max_or_none(excess_min_basis[recorded]),
            "unlocked_tail_samples_by_leg": _by_leg(unlocked_tail.sum(axis=0)),
            "unlocked_tail_over_0p6kN_by_leg": _by_leg(
                (unlocked_tail & (excess > EXCESS_LIMIT_N)).sum(axis=0)),
            "unlocked_tail_max_excess_N": _max_or_none(excess[unlocked_tail]),
            "provisional_pass": bool(over.sum() == 0),
            "settings_equal": True, "commands_sha256": meta.get("commands_sha256"),
            "extend_start_revision": (rebuilt.get("extend_start_bound") or {}).get("revision"),
            "tension_truth": meta.get("tension_truth"),
            "extend_bound_check": meta.get("extend_bound_check"),
            # criteria revision 9 (j_p3_inputs): which runs J-P3 must cover and their declaration
            "p3_expected": is_p3_expected(meta.get("controller_tag"),
                                          (meta.get("job") or {}).get("setting")),
            "has_rod_reading": bool(np.isfinite(arrays["rod_pressure_Pa"]).any()),
            "head_only_declared": harness_head_only_declared(meta),
            **({} if "extend_start_rule" not in stored
               else {"run_extend_start_rule": stored["extend_start_rule"]})}


def _by_leg(counts) -> dict[str, int]:
    return dict(zip(LEGS, np.asarray(counts).tolist(), strict=True))


def _max_or_none(values: np.ndarray) -> float | None:
    return float(values.max()) if values.size else None


def record_files(paths: list[str]) -> list[Path]:
    files = []
    for path in map(Path, paths):
        files += sorted(path.glob("*.npz")) if path.is_dir() else [path]
    return files


def record_name(extend_start: str | None) -> str:
    """Criteria revision 8 2 #3: ``T4h-const`` for the ③-off override, else ``T4h``."""
    return "T4h-const" if extend_start == "constant" else "T4h"


def _override_revision(extend_start: str | None) -> int | None:
    """Bound revision of a ``tracked_bound`` override (None otherwise)."""
    from outrigger_sim.control.extend_start_bound import EXTEND_START_REVISION

    return EXTEND_START_REVISION if extend_start == "tracked_bound" else None


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_json")
    parser.add_argument("records", nargs="+", help="npz files or folders")
    parser.add_argument("--extend-start", choices=EXTEND_START_CHOICES, default=None,
                        help="override the ③ start rule (constant: record T4h-const)")
    parser.add_argument("--check-recorded", action="store_true",
                        help="also replay with the run's own events against lower_reading_N")
    return parser.parse_args()


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    args = _parse_arguments()
    try:
        rows = [replay_values(path, args.extend_start, args.check_recorded)
                for path in record_files(args.records)]
    except IdealRecordError as exc:
        print(f"input error: {exc}")
        print(json.dumps({"stop": "ideal_record", "reason": str(exc)}))
        return 2
    report = {"rule": "criteria 9 T4h: zero acting command samples of a locked plant leg, "
                      "lower - true_force_N > 0.6 kN count (0 = provisional pass); fallback "
                      "forced on all legs; unlocked tail samples recorded only",
              "record": record_name(args.extend_start),
              "extend_start_rule": args.extend_start,
              "extend_start_revision": _override_revision(args.extend_start),
              "runs": len(rows), "runs_over": sum(not row["provisional_pass"] for row in rows),
              "offset_allowance_runs": sum(any(value != 0.0 for value in
                                               row["offset_allowance_N"]) for row in rows),
              "J-P3": j_p3_over_rows(rows),
              "rows": rows}
    if args.check_recorded:
        differences = [row["recorded_lower_max_abs_N"] for row in rows
                       if row["recorded_lower_max_abs_N"] is not None]
        report["recorded_lower_max_abs_N"] = max(differences) if differences else None
    Path(args.out_json).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"runs": report["runs"], "runs_over": report["runs_over"],
                      "J-P3": report["J-P3"]["status"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
