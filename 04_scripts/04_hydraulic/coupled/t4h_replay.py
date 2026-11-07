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

Usage (dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/t4h_replay.py <out_json> <npz or folder> [...]
      [--extend-start tracked_bound]   (③ start rule override, record T4h-P3)
``aggregate_v5`` reads ``<batch>/t4h/t4h_replay.json`` (write the output there for its table).
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

LEGS = ("FL", "FR", "RL", "RR")
EXCESS_LIMIT_N = 600.0
"""Criteria 9 T4h: lower bound <= truth + 0.6 kN."""
FALLBACK_EVENT = "WARN_ROD_PRESSURE_FALLBACK"
HARNESS_VALVE_TAU_S = 0.1
EXTEND_START_KEYS = ("extend_start_rule", "extend_start_bound")
"""Two-pressure meta keys of the ③ start option (present only with the option on)."""
EXTEND_START_CHOICES = ("constant", "tracked_bound")


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
    """C2Config of the run: harness preset + the lock window of its options; ``extend_start``
    overrides the ③ start rule (``p3_extend_start_spec.md`` 4 #8, ``T4h-P3``).

    Raises:
        ValueError: ``tracked_bound`` on a run with M1c (review 2026-11-07, 2c).
    """
    import s9_soil_closed_loop as soil
    from params import load_params

    from outrigger_sim.control import c2
    from outrigger_sim.hydraulics.v5_options import (
        HydraulicOptions,
        apply_lock_window,
        check_extend_start,
    )

    closed_loop = soil._imports()[0]
    contact = (meta.get("job") or {}).get("contact") or "COMBINED"
    config = closed_loop.preset_config(c2.ContactJudge[contact], with_imu_samples=True,
                                       with_reapproach=True)
    # read only: records of earlier M2 laws keep their lock window (the replay reruns no plant)
    options = HydraulicOptions.from_stored(meta["hydraulic_options"])
    if options.lock_window_follows_plant:
        config = apply_lock_window(config, options, load_params().v_max, HARNESS_VALVE_TAU_S)
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


def replay_values(path: Path, extend_start: str | None = None) -> dict:
    """T4h values of one record (module docstring).

    Raises:
        RuntimeError: The rebuilt monitor settings differ from the stored ones (with
            ``extend_start``: apart from the ③ start keys).
    """
    from outrigger_sim.control.c2 import C2Geometry
    from outrigger_sim.control.contact_replay import replay_fallback_monitor
    from outrigger_sim.control.extend_start_bound import check_extend_start_meta

    arrays, meta = load_record(path)
    stored = meta["two_pressure_settings"]
    check_extend_start_meta(stored)
    closed_loop, config = run_config(meta, extend_start)
    rebuilt = _plain(config.two_pressure.to_meta())
    if (_settings_for_comparison(rebuilt, stored, extend_start)
            != _settings_for_comparison(stored, stored, extend_start)):
        raise RuntimeError(f"{path.name}: rebuilt two_pressure settings differ from the record")
    t_s = arrays["t_s"]
    forced = [(float(t_s[0]), f"{FALLBACK_EVENT}:{leg}") for leg in LEGS]
    geometry = C2Geometry.from_params(closed_loop.PARAMS)
    replay = replay_fallback_monitor(_Record(arrays, meta), forced, geometry, config)
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
    return {"file": path.name, "samples": int(len(t_s)),
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
            "extend_bound_check": meta.get("extend_bound_check")}


def _by_leg(counts) -> dict[str, int]:
    return dict(zip(LEGS, np.asarray(counts).tolist(), strict=True))


def _max_or_none(values: np.ndarray) -> float | None:
    return float(values.max()) if values.size else None


def record_files(paths: list[str]) -> list[Path]:
    files = []
    for path in map(Path, paths):
        files += sorted(path.glob("*.npz")) if path.is_dir() else [path]
    return files


def _override_revision(extend_start: str | None) -> int | None:
    """Bound revision of a ``tracked_bound`` override (None otherwise)."""
    from outrigger_sim.control.extend_start_bound import EXTEND_START_REVISION

    return EXTEND_START_REVISION if extend_start == "tracked_bound" else None


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_json")
    parser.add_argument("records", nargs="+", help="npz files or folders")
    parser.add_argument("--extend-start", choices=EXTEND_START_CHOICES, default=None,
                        help="override the ③ start rule (record T4h-P3; spec p3 4 #8)")
    return parser.parse_args()


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    args = _parse_arguments()
    rows = [replay_values(path, args.extend_start) for path in record_files(args.records)]
    report = {"rule": "criteria 9 T4h: zero acting command samples of a locked plant leg, "
                      "lower - true_force_N > 0.6 kN count (0 = provisional pass); fallback "
                      "forced on all legs; unlocked tail samples recorded only",
              "record": "T4h" if args.extend_start is None else "T4h-P3",
              "extend_start_rule": args.extend_start,
              "extend_start_revision": _override_revision(args.extend_start),
              "runs": len(rows), "runs_over": sum(not row["provisional_pass"] for row in rows),
              "rows": rows}
    Path(args.out_json).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("runs", "runs_over")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
