"""Chrono input adapter of the lock window alignment (v5 stage 3 R-4, criteria rev. 6 section 6).

The rule is :func:`lock_window_alignment.lock_window_alignment` unchanged; this module only builds
its inputs from a Chrono case folder (read only):

* commands: ``r8_series.npz`` ``t`` and ``issued_u`` (the acting command of a sample is the issued
  output of the sample before, ``d = 1``);
* monitor meta: ``result.json`` ``controller_meta.two_pressure`` (settings and the fallback
  stretch log) and ``controller_meta.period_s``;
* plant lock events: the 1 ms ``pads.npz`` ``law_locked`` transitions (1 locked, 0 moving,
  -1 = no armed law, read as locked like the harness "all legs locked at arm");
* controller events: ``controller_events.json``.

Times in s. Values only; the gates are the criteria's (H-7 for a fallback leg, L-e for LS rows).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from lock_window_alignment import lock_window_alignment  # noqa: E402

from outrigger_sim.contact_episode import read_controller_events  # noqa: E402

R8_SERIES_FILE = "r8_series.npz"
PADS_FILE = "pads.npz"
RESULT_FILE = "result.json"
EVENTS_FILE = "controller_events.json"
LAW_MOVING = 0
"""``law_locked`` value of a moving leg; 1 (locked) and -1 (no armed law) count as locked."""


def lock_events_from_law_state(t_s: np.ndarray, law_locked: np.ndarray) -> list[tuple]:
    """``(t, leg, locked)`` at every change of the 1 ms law state, in time order.

    The history starts locked (the harness convention); a leg that is moving at the first
    sample gets an unlock event at that time.
    """
    times = np.asarray(t_s, float)
    is_locked = np.asarray(law_locked) != LAW_MOVING
    events = []
    for leg in range(is_locked.shape[1]):
        with_start = np.concatenate(([True], is_locked[:, leg]))
        for j in np.flatnonzero(with_start[1:] != with_start[:-1]):
            events.append((float(times[j]), leg, bool(is_locked[j, leg])))
    events.sort(key=lambda event: (event[0], event[1]))
    return events


def chrono_lock_window_alignment(case_dir: Path) -> dict:
    """The ``lock_window_alignment`` record of one Chrono case folder (module docstring).

    Raises:
        FileNotFoundError: A required file is missing.
        KeyError: ``pads.npz`` without ``law_locked`` (a record before v5 X-11).
        lock_window_alignment.LockWindowMismatchError: The monitor's fallback stretches differ
            from the rebuilt ones (implementation defect).
    """
    case_dir = Path(case_dir)
    result = json.loads((case_dir / RESULT_FILE).read_text(encoding="utf-8"))
    controller = result.get("controller_meta") or {}
    with np.load(case_dir / R8_SERIES_FILE, allow_pickle=False) as series:
        t_s = np.asarray(series["t"], float)
        issued = np.asarray(series["issued_u"], float)
    with np.load(case_dir / PADS_FILE, allow_pickle=False) as pads:
        lock_events = lock_events_from_law_state(pads["t"], pads["law_locked"])
    events = [(float(t), str(name))
              for t, name in read_controller_events(case_dir / EVENTS_FILE)]
    record = lock_window_alignment(t_s, issued, lock_events, controller.get("two_pressure") or {},
                                   float(controller.get("period_s", 0.1)), events,
                                   float(t_s[-1]))
    record["lock_source"] = "pads.law_locked (1 ms, -1 read as locked)"
    return record


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: chrono_lock_window.py <out_json> <case_dir>")
        return 2
    record = chrono_lock_window_alignment(Path(sys.argv[2]))
    Path(sys.argv[1]).write_text(json.dumps(record, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"n_late_fallback": record.get("n_late_fallback")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
