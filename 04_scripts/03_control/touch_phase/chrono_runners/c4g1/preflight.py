"""No simulation. Checks that the pinned worktree is what gets imported and that the C4G1 config and the S7 args rebuild. Stops on any mix.

Usage: python -I -B -X utf8 preflight.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE / "wt"
MAIN = Path(r"C:\workspace\outrigger_control")
STORED = MAIN / "07_results/S9/batch_FINAL-REP_20261030_223359/S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0"
sys.path.insert(0, str(WT / "03_src"))
sys.path.insert(0, str(WT / "04_scripts" / "02_chrono"))
os.chdir(WT)


def main_tree_modules() -> list[str]:
    bad = []
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and Path(f).resolve().is_relative_to(MAIN.resolve()):
            bad.append(f"{name}: {f}")
    return bad


def main() -> None:
    import outrigger_sim
    import run_S8C
    import run_S9
    from outrigger_sim.control import c2
    from outrigger_sim.chrono import l2b_model, sim_shapes

    print("outrigger_sim", outrigger_sim.__file__)
    print("run_S8C", run_S8C.__file__, "ROOT", run_S8C.ROOT)
    print("run_S9", run_S9.__file__, "ROOT", run_S9.ROOT)
    print("c2", c2.__file__, hashlib.sha256(Path(c2.__file__).read_bytes()).hexdigest())
    print("l2b_model", l2b_model.__file__)
    print("sim_shapes dir", sim_shapes.SIM_SHAPES_DIR, sim_shapes.SIM_SHAPES_DIR.exists())
    print("main tree modules", main_tree_modules())
    cfg = c2.C2Config().with_10hz_d1(touch_twist_hold=True)
    print("hold", cfg.touch_twist_hold, "clip", cfg.clip_returned_command)
    exp = run_S9.controller_expectation(cfg, "final_SGS_R4")
    print("expect final_SGS_R4 ok", exp.get("ok"), [c for c in exp.get("checks", []) if not c["ok"]])
    stored = json.loads((STORED / "result.json").read_text(encoding="utf-8"))
    want = dict(stored["args"], out_root=str(MAIN / "07_results/S8/_x"))
    ap = run_S9.build_parser()
    sub = next(a for a in ap._actions if isinstance(a, argparse._SubParsersAction))
    lp = sub.choices["level"]
    argv = ["level"]
    for action in lp._actions:
        if action.dest in ("help", "action") or action.dest not in want or not action.option_strings:
            continue
        v = want[action.dest]
        if v is None or v is False:
            continue
        flag = action.option_strings[0]
        if v is True:
            argv.append(flag)
        elif isinstance(v, (list, tuple)):
            argv += [flag, *(repr(float(x)) if isinstance(x, float) else str(x) for x in v)]
        else:
            argv += [flag, repr(float(v)) if isinstance(v, float) else str(v)]
    parsed = {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(ap.parse_args(argv)).items()}
    print("S7 args diff", {k: (parsed.get(k), want.get(k)) for k in set(parsed) | set(want) if parsed.get(k) != want.get(k)})
    print("argv", argv)
    print("code_state dirty check", {k: stored["code_state"].get(k) for k in ("state",)})
    sc = run_S8C.case_table()
    print("rigid cases", sc["A_bottom_rpB_Fs0"].fs_kN, sc["A_bottom_rpB_Fs0"].scenario.level, sc["K24_top_roll5.5_Fs4"].fs_kN)
    print("main tree modules at end", main_tree_modules())


if __name__ == "__main__":
    main()
