"""S9 P3b RE1c positive tests: independent R-1 .. R-4 check from raw events (spec rev. 60, 307).

Parses controller events directly (spec 284.1 re-approach time limit): re-approach starts,
``WARN_LEG_REAPPROACH_NO_CONTACT`` warnings, FAULT-like events, the distinct event names,
and the time from the first re-approach start to the first no-contact warning (expected
10 s). Any JSON event representation is accepted (dict with ``t_s`` / ``name``, or the
``C2Event(...)`` repr string). The events are in ``controller_events.json``; ``result.json``
of these runs carries none.

Inputs (default): ``07_results/S8/p3b_N_RE1c_Fs{0,8}_combined_*/N_RE1c_Fs{0,8}_combined/
controller_events.json``.
Output: standard output only.

Usage (dynamics-dev):
  conda run -n dynamics-dev python -I 04_scripts/03_control/s9/p3b/re1c_check.py [<events.json> ...]
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_EVENT_FILES = [
    ROOT / "07_results" / "S8" / "p3b_N_RE1c_Fs0_combined_20261026_191935"
    / "N_RE1c_Fs0_combined" / "controller_events.json",
    ROOT / "07_results" / "S8" / "p3b_N_RE1c_Fs8_combined_20261026_190815"
    / "N_RE1c_Fs8_combined" / "controller_events.json",
]
C2_EVENT_REPR = re.compile(r"C2Event\(t_s=([0-9.eE+-]+), name='([^']+)'")


def walk_events(obj):
    """Yield (t, name) from any event list representation found in the JSON object."""
    if isinstance(obj, dict):
        if "t_s" in obj and "name" in obj and isinstance(obj["name"], str):
            yield float(obj["t_s"]), obj["name"]
        for v in obj.values():
            yield from walk_events(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_events(v)
    elif isinstance(obj, str):
        m = C2_EVENT_REPR.match(obj)
        if m:
            yield float(m.group(1)), m.group(2)


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("event_files", nargs="*", type=Path, default=DEFAULT_EVENT_FILES)
    return parser.parse_args()


def main():
    for p in _parse_args().event_files:
        r = json.loads(Path(p).read_text(encoding="utf-8"))
        print("==", p)
        print(" top type:", type(r).__name__, len(r))
        ev = sorted(set(walk_events(r)))
        starts = [t for t, n in ev if n.startswith("leg_reapproach_start")]
        warns = [(t, n) for t, n in ev if n.startswith("WARN_LEG_REAPPROACH_NO_CONTACT")]
        faults = [(t, n) for t, n in ev if "FAULT" in n]
        start_events = [(t, n) for t, n in ev if n.startswith("leg_reapproach_start")]
        print(" reapproach starts:", start_events)
        print(" no-contact warnings:", warns)
        print(" fault-like events:", faults)
        print(" all distinct names:", sorted({n.split(':')[0] for _, n in ev}))
        if starts and warns:
            print(f" warn - first start: {warns[0][0] - starts[0]:.4f} s")


if __name__ == "__main__":
    main()
