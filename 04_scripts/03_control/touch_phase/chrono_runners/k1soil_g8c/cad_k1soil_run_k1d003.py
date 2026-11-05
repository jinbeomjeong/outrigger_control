"""Row S9EV_G1_FLFs0_RE1bF_d003_C4G2: as row 1a of run_k1soil_case.py, event 0.03 s later than B1 mid, C4G2 alone (K1 off). No source change.

Modes: (none) the run into the batch folder; --check-short 2 s loop, far event time, scratch folder.
Usage: python -I -B -X utf8 -u run_k1d003.py [--check-short]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_k1soil_case as rk  # noqa: E402

ROW = "d003"
CASE = "S9EV_G1_FLFs0_RE1bF_d003_C4G2"
B1_T_EV_LOOP_S = 28.30000000008681
"""Stored in event_time_B1.json; the call below refuses another value."""
DELAY_S = 0.03


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-short", action="store_true")
    me = ap.parse_args()
    t = json.loads((rk.BATCH / "event_time_B1.json").read_text(encoding="utf-8"))
    if t["t_ev_loop_s"] != B1_T_EV_LOOP_S:
        raise SystemExit(f"B1 event time {t['t_ev_loop_s']!r}, want {B1_T_EV_LOOP_S!r}")
    t_ev = B1_T_EV_LOOP_S + DELAY_S
    rk.ROWS[ROW] = (CASE, 0.0, "FL", "t", "on", "B1")
    rk.FLAGS_ON = {"touch_twist_hold": True, "reapproach_retrigger_two_samples": False}
    print("row", ROW, "t_ev_loop", repr(t_ev), "flags", rk.FLAGS_ON, flush=True)
    os.chdir(rk.WT)
    mask = int(os.environ["K1D003_MASK"], 16) if os.environ.get("K1D003_MASK") else None
    if mask is not None:
        import psutil
        import run_S9

        real_place = run_S9.place
        wanted = [i for i in range(32) if mask >> i & 1]

        def place():
            """run_S9.place pins the whole P pool and switches EcoQoS off; the batch table's narrower mask goes on after it."""
            info = real_place()
            proc = psutil.Process()
            proc.cpu_affinity(wanted)
            got = proc.cpu_affinity()
            if got != wanted:
                raise SystemExit(f"affinity {got}, want {wanted}")
            info.update(affinity_override_mask=hex(mask), affinity_after_override=got)
            print("placement", info, flush=True)
            return info

        run_S9.place = place
    rk.run_row(ROW, t_ev, me.check_short)
    if mask is not None:
        print("affinity at the end", psutil.Process().cpu_affinity(), flush=True)


if __name__ == "__main__":
    main()
