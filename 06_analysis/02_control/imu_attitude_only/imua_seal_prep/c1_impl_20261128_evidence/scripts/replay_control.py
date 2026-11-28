"""Negative control of the P-8 acceptance on an A-type Chrono record: the same replay with the A-type rebuild
switched off (``chrono_t45_replay._with_a_type`` -> identity) must lose ``settings_equal``.

Usage (dynamics-dev, worktree root): python replay_control.py <worktree> <case dir> <out json>
"""
import json
import sys
from pathlib import Path

wt = Path(sys.argv[1])
sys.path.insert(0, str(wt / "04_scripts" / "04_hydraulic" / "coupled"))
sys.path.insert(0, str(wt / "03_src"))
import chrono_t45_replay as r  # noqa: E402

case = Path(sys.argv[2])
row_on = r.replay_case(case)
orig = r._with_a_type
r._with_a_type = lambda config, result: config
try:
    row_off = r.replay_case(case)
finally:
    r._with_a_type = orig
out = {"with_a_type": {k: row_on.get(k) for k in ("settings_equal", "t4_0", "max_relative_difference",
                                                  "setting_differences")},
       "without_a_type_rebuild": {k: row_off.get(k) for k in ("settings_equal", "t4_0", "setting_differences")}}
Path(sys.argv[3]).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print(json.dumps(out, indent=1, default=str))
