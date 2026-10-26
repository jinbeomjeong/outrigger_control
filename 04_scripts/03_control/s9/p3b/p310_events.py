"""S9 P3-10 path-2 check: soil response on vs off gives the same commands (spec rev. 60, 307).

For the two P3-10 cases (``flat``, ``rpB``) compares the soil-on and soil-off runs:
controller event multiset difference (``controller_events.json``) and max |diff| plus
SHA-256 of ``u_applied``, ``u_cmd``, ``F_cyl`` and ``body_quat_wxyz`` from
``record/record.npz`` (10 Hz).

Input: ``07_results/S9/batch_P3-10_20261026_122444/{flat,rpB}__{on,off}/``.
Output: standard output only.

Usage (dynamics-dev):
  conda run -n dynamics-dev python -I 04_scripts/03_control/s9/p3b/p310_events.py [<batch_dir>]
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_BATCH = ROOT / "07_results" / "S9" / "batch_P3-10_20261026_122444"
CASES = ("flat", "rpB")
SERIES = ("u_applied", "u_cmd", "F_cyl", "quat")


def _event_strings(events):
    if isinstance(events, dict):
        events = events.get("events", events)
    return [x if isinstance(x, str) else f"{x['t_s']:.6f} {x['name']}" for x in events]


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("batch_dir", nargs="?", type=Path, default=DEFAULT_BATCH)
    return parser.parse_args()


def main():
    b = _parse_args().batch_dir
    for case in CASES:
        ev, u = {}, {}
        for mode in ("on", "off"):
            d = b / f"{case}__{mode}"
            e = json.loads((d / "controller_events.json").read_text(encoding="utf-8"))
            ev[mode] = _event_strings(e)
            with np.load(d / "record" / "record.npz") as z:
                u[mode] = (z["u_applied"].copy(), z["u_cmd"].copy(), z["F_cyl"].copy(),
                           z["body_quat_wxyz"].copy())
        on, off = Counter(ev["on"]), Counter(ev["off"])
        print(case, "only_on:", sorted((on - off).elements()),
              "only_off:", sorted((off - on).elements()))
        for i, name in enumerate(SERIES):
            a, c = u["on"][i], u["off"][i]
            sha_on = hashlib.sha256(a.tobytes()).hexdigest()[:12]
            sha_off = hashlib.sha256(c.tobytes()).hexdigest()[:12]
            print(f"  {name}: shape {a.shape} max|diff| {np.max(np.abs(a - c)):.3e} "
                  f"sha_on {sha_on} sha_off {sha_off}")


if __name__ == "__main__":
    main()
