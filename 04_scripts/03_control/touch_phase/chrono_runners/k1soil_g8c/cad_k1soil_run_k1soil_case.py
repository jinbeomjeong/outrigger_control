"""One row of the K1 soil batch (next_soil_rows.md), pinned checkout 74032be, flow limit off. No source change.

Modes:
  --row B1|1a|1b|B2|2a|2b|B3|3a|3b [--t-ev-loop <s>]        one run into the batch folder
  --row 1a --check-short                                     2 s loop, far event time, scratch folder (start check)
  --event-time B1                                            read the base folder, write event_time_<row>.json, exit 3 if no DONE
  --judge-test <event run folder>                            import check of the event judge chain, prints values

A meta path finder sends any module that would load from the main tree to the same file in the checkout: r8d1_td.py line 24 puts the
main-tree 03_control on sys.path, and the event judge at the end of a run imports that chain. A module without a checkout twin raises.
Usage: python -I -B -X utf8 -u run_k1soil_case.py ...
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE.parent / "cad_c4g2" / "wt"
MAIN = Path(r"C:\workspace\outrigger_control")
COMMIT = "74032beae72c7e44858e41384bc54c263e724fd3"
C2_SHA = "28482b8d5678c3e1079c9dd89046013bd60cac718e0e8efa195101a36236df67"
BATCH = MAIN / "07_results/S9/batch_k1soil_G1_20261105"
OUT = MAIN / "06_analysis/02_control/touch_phase/chrono/k1soil"
EVENT = "RE1bF"
BASE_DURATION_S = 60.0
"""next_soil_rows.md section 3 (ASSUMPTION there: the first DONE falls inside; a base without DONE stops its row)."""
FLAGS_ON = {"touch_twist_hold": True, "reapproach_retrigger_two_samples": True}
ROWS = {"B1": ("S9EV_G1_FLFs0_base", 0.0, "FL", "base", "off", None), "1a": ("S9EV_G1_FLFs0_RE1bF_on", 0.0, "FL", "t", "on", "B1"), "1b": ("S9EV_G1_FLFs0_RE1bF_off", 0.0, "FL", "mid", "off", "B1"),
        "B2": ("S9EV_G1_FLFs8_base", 8.0, "FL", "base", "off", None), "2a": ("S9EV_G1_FLFs8_RE1bF_on", 8.0, "FL", "t", "on", "B2"), "2b": ("S9EV_G1_FLFs8_RE1bF_off", 8.0, "FL", "mid", "off", "B2"),
        "B3": ("S9EV_G1_RRFs0_base", 0.0, "RR", "base", "off", None), "3a": ("S9EV_G1_RRFs0_RE1bF_on", 0.0, "RR", "t", "on", "B3"), "3b": ("S9EV_G1_RRFs0_RE1bF_off", 0.0, "RR", "mid", "off", "B3")}
REDIRECTED: list[str] = []


class MainTreeRedirect:
    """Meta path finder: a module the path finder resolves under the main tree loads from the same relative file of the checkout."""

    @staticmethod
    def find_spec(name, path=None, target=None):
        spec = importlib.machinery.PathFinder.find_spec(name, path, target)
        origin = getattr(spec, "origin", None) if spec is not None else None
        if origin is None or not Path(origin).exists() or not Path(origin).resolve().is_relative_to(MAIN.resolve()):
            return spec
        twin = WT / Path(origin).resolve().relative_to(MAIN.resolve())
        if not twin.exists():
            raise ImportError(f"{name}: main-tree module {origin} has no twin in the checkout")
        REDIRECTED.append(f"{name}: {origin} -> {twin}")
        locations = [str(twin.parent)] if spec.submodule_search_locations is not None else None
        return importlib.util.spec_from_file_location(name, str(twin), submodule_search_locations=locations)


sys.meta_path.insert(0, MainTreeRedirect)
sys.path.insert(0, str(WT / "03_src"))
sys.path.insert(0, str(WT / "04_scripts" / "02_chrono"))


def main_tree_modules() -> list[str]:
    root = MAIN.resolve()
    return [f"{n}: {m.__file__}" for n, m in list(sys.modules.items()) if getattr(m, "__file__", None) and Path(m.__file__).resolve().is_relative_to(root)]


def checks() -> dict:
    import outrigger_sim
    import run_S9
    from outrigger_sim.control import c2

    sha = hashlib.sha256(Path(c2.__file__).read_bytes()).hexdigest()
    head = (WT / ".git").read_text(encoding="utf-8").strip()
    out = {"outrigger_sim": outrigger_sim.__file__, "run_S9": run_S9.__file__, "c2": c2.__file__, "c2_sha256": sha, "commit": COMMIT, "git_link": head}
    good = sha == C2_SHA and Path(outrigger_sim.__file__).resolve().is_relative_to(WT.resolve()) and Path(run_S9.__file__).resolve().is_relative_to(WT.resolve()) and not main_tree_modules()
    if not good:
        raise SystemExit(f"code mix, stopped: {out} {main_tree_modules()}")
    return out


def build_argv(run_s9, row: str, t_ev_loop: float | None, out_root: Path, duration: float | None) -> tuple[str, list[str]]:
    case, fs, leg, trig, _cfg, base = ROWS[row]
    c = run_s9.p3b_case(row, "G1", "B", "top", fs)
    c["case"] = case
    c["soil_patch"] = {"leg": leg, "set": "G1", "grid_m": run_s9.P3B_PAD_GRID_M["G1"]}
    if trig == "base":
        c["duration_s"] = BASE_DURATION_S
    elif trig == "mid":
        c["soil_event"] = f"{leg}:{EVENT}:mid@{ROWS[base][0]}"
    else:
        if t_ev_loop is None:
            raise SystemExit(f"row {row}: --t-ev-loop needed")
        c["soil_event"] = f"{leg}:{EVENT}:t{t_ev_loop!r}"
    if duration is not None:
        c["duration_s"] = duration
    return case, run_s9.p3b_level_argv(c) + ["--case", case, "--out-root", str(out_root)]


def run_row(row: str, t_ev_loop: float | None, short: bool) -> None:
    import run_S9
    from outrigger_sim.control import c2

    state = checks()
    _case, _fs, _leg, _trig, cfg_name, _base = ROWS[row]
    out_root = (HERE / "check_short") if short else BATCH
    case, argv = build_argv(run_S9, row, 1000.0 if short else t_ev_loop, out_root, 2.0 if short else None)
    if (out_root / case).exists():
        raise SystemExit(f"case folder exists: {out_root / case}")
    real = run_S9.level_c2_config
    seen: dict = {}

    def level_c2_config(allow_soil_off, config=None):
        cfg = c2.C2Config().with_10hz_d1(**FLAGS_ON) if cfg_name == "on" else c2.C2Config().with_10hz_d1()
        seen.update(hold=str(cfg.touch_twist_hold), clip=cfg.clip_returned_command, retrigger_samples=cfg.r8.lifted_reapproach.retrigger_samples)
        return real(allow_soil_off, config=cfg)

    run_S9.level_c2_config = level_c2_config
    out_root.mkdir(parents=True, exist_ok=True)
    print("argv", argv, flush=True)
    run_S9.main(argv)
    d = out_root / case
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    side = dict(state, row=row, config_name=cfg_name, argv=argv, config=seen, t_ev_loop_arg=t_ev_loop, flow_limit=res.get("args", {}).get("flow_eta_v"), main_tree_modules_at_end=main_tree_modules(), redirected=REDIRECTED,
                hold_meta=(res.get("controller_meta") or {}).get("touch_twist_hold"), soil_event_t_ev=(res.get("soil_event") or {}).get("t_ev_s") if isinstance(res.get("soil_event"), dict) else None,
                env={k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OUTRIGGER_PLACEMENT")})
    (d / "k1soil_job_side.json").write_text(json.dumps(side, indent=1, default=str), encoding="utf-8")
    print("side", json.dumps({k: side[k] for k in ("c2_sha256", "config", "main_tree_modules_at_end", "soil_event_t_ev")}, default=str), "redirected", len(REDIRECTED), flush=True)
    if side["main_tree_modules_at_end"]:
        raise SystemExit(f"main-tree modules at the end: {side['main_tree_modules_at_end']}")


def event_time(row: str) -> None:
    import run_S9

    case = ROWS[row][0]
    try:
        t = run_S9.base_event_time(BATCH / case)
    except ValueError as exc:
        print("stop", exc, flush=True)
        sys.exit(3)
    t["t_ev_loop_s"] = t["t_mid_s"] - t["t_loop_start_s"]
    OUT.mkdir(parents=True, exist_ok=True)
    for path in (BATCH / f"event_time_{row}.json", OUT / f"event_time_{row}.json"):
        path.write_text(json.dumps(t, indent=1), encoding="utf-8")
    print(json.dumps(t), flush=True)


def judge_test(d: Path) -> None:
    import run_S9

    state = checks()
    if not d.exists():
        h = str(WT / "04_scripts" / "03_control" / "s9")
        sys.path.insert(0, h)
        import s9_soil_event_screen as mod

        print("import only:", mod.__file__, "judge", hasattr(mod, "judge_soil_event"), "imports helper", mod.sl._imports()[0].__name__, "main tree modules", main_tree_modules(), "redirected", len(REDIRECTED), REDIRECTED[:6])
        print("modules from checkout 03_control", sum(1 for m in list(sys.modules.values()) if getattr(m, "__file__", None) and "03_control" in str(m.__file__)))
        return
    out = run_S9.judge_chrono_soil_event(d)
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    stored = (res.get("soil_event") or {}).get("judgement") or {}
    same = {k: out.get(k) == stored.get(k) for k in set(out) & set(stored)}
    print("state", state["c2_sha256"][:12], "main tree modules", main_tree_modules(), "redirected", len(REDIRECTED), REDIRECTED[:4])
    print("judge keys", list(out)[:14], "same as stored", sum(same.values()), "of", len(same), [k for k, v in same.items() if not v][:12])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", choices=tuple(ROWS))
    ap.add_argument("--t-ev-loop", type=float)
    ap.add_argument("--check-short", action="store_true")
    ap.add_argument("--event-time", choices=("B1", "B2", "B3"))
    ap.add_argument("--judge-test")
    me = ap.parse_args()
    os.chdir(WT)
    if me.judge_test:
        judge_test(Path(me.judge_test))
    elif me.event_time:
        event_time(me.event_time)
    else:
        run_row(me.row, me.t_ev_loop, me.check_short)


if __name__ == "__main__":
    main()
