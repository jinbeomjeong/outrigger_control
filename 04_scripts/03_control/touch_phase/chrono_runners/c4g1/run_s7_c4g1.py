"""S7 soil row with C4G1, flow limit off, pinned worktree code. Stored flow-off args rebuilt and checked against the parser; only --out-root differs.

Config through ``run_S9.level_c2_config(allow, config=...)``: the preset with touch_twist_hold=True (the returned clip comes on with the preset).
Stops before the run on any main-tree module or another c2.py. Writes c4g1_job_side.json into the case folder at the end.
Usage: python -I -B -X utf8 -u run_s7_c4g1.py --out-root <dir>
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
COMMIT = "15176d153465b45c6bbd58aec5bed2732b9696e8"
C2_SHA = "02ca442c3be01ab3c91822b3101c0c1054f1b59c878555ced14c7393af58afd4"
sys.path.insert(0, str(WT / "03_src"))
sys.path.insert(0, str(WT / "04_scripts" / "02_chrono"))


def main_tree_modules() -> list[str]:
    root = MAIN.resolve()
    return [f"{n}: {m.__file__}" for n, m in list(sys.modules.items()) if getattr(m, "__file__", None) and Path(m.__file__).resolve().is_relative_to(root)]


def rebuild_argv(run_s9, stored_args: dict, out_root: str) -> list[str]:
    want = dict(stored_args, out_root=out_root)
    ap = run_s9.build_parser()
    lp = next(a for a in ap._actions if isinstance(a, argparse._SubParsersAction)).choices["level"]
    argv = ["level"]
    for action in lp._actions:
        if action.dest in ("help", "action") or action.dest not in want or not action.option_strings:
            continue
        value = want[action.dest]
        if value is None or value is False:
            continue
        flag = action.option_strings[0]
        if value is True:
            argv.append(flag)
        elif isinstance(value, (list, tuple)):
            argv += [flag, *(repr(float(v)) if isinstance(v, float) else str(v) for v in value)]
        else:
            argv += [flag, repr(float(value)) if isinstance(value, float) else str(value)]
    parsed = {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(ap.parse_args(argv)).items()}
    diff = {k: (parsed.get(k), want.get(k)) for k in set(parsed) | set(want) if parsed.get(k) != want.get(k)}
    if diff:
        raise SystemExit(f"rebuilt arguments differ from the stored run: {diff}")
    return argv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", required=True)
    me = ap.parse_args()
    if Path(me.out_root).exists():
        raise SystemExit(f"result folder exists: {me.out_root}")
    os.chdir(WT)
    import outrigger_sim
    import run_S9
    from outrigger_sim.control import c2

    sha = hashlib.sha256(Path(c2.__file__).read_bytes()).hexdigest()
    checks = {"outrigger_sim": outrigger_sim.__file__, "run_S9": run_S9.__file__, "c2": c2.__file__, "c2_sha256": sha, "commit": COMMIT}
    if sha != C2_SHA or not Path(outrigger_sim.__file__).resolve().is_relative_to(WT.resolve()) or not Path(run_S9.__file__).resolve().is_relative_to(WT.resolve()) or main_tree_modules():
        raise SystemExit(f"code mix, stopped: {checks} {main_tree_modules()}")
    stored = json.loads((STORED / "result.json").read_text(encoding="utf-8"))
    argv = rebuild_argv(run_S9, stored["args"], me.out_root)
    real = run_S9.level_c2_config
    seen = {}

    def level_c2_config(allow_soil_off, config=None):
        cfg = c2.C2Config().with_10hz_d1(touch_twist_hold=True)
        seen.update(hold=str(cfg.touch_twist_hold), clip=cfg.clip_returned_command)
        return real(allow_soil_off, config=cfg)

    run_S9.level_c2_config = level_c2_config
    run_S9.main(argv)
    d = Path(me.out_root) / stored["args"]["case"]
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    side = dict(checks, argv=argv, config=seen, main_tree_modules_at_end=main_tree_modules(), hold_meta=(res.get("controller_meta") or {}).get("touch_twist_hold"),
                env={k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OUTRIGGER_PLACEMENT")})
    (d / "c4g1_job_side.json").write_text(json.dumps(side, indent=1, default=str), encoding="utf-8")
    print("c4g1_s7_side", json.dumps(side, default=str)[:800], flush=True)


if __name__ == "__main__":
    main()
