"""D8 576 (td_main 144 + td_robust 432) with the project C2 on the revision-30 harness (r8d1_td2 plant and metrics).

The stored r8d1_td2 D8 runs use the harness controller, not C2Controller; this driver puts C2Controller in through
``c2py_r8d1_closed_loop.HarnessAdapter`` (controller queue and increment limit, harness queue off).
Resumes from <out>.partial.jsonl. Usage: python -I -B acc_d8.py <out.json> [--workers N] [--limit N] [--stage main|all]

D8x mode (``06_analysis/02_control/d8x/d8x_rules.md`` 3 R-a, 9.2 item 3), with ``--points``:
  python -I -B acc_d8.py --points 06_analysis/02_control/d8x/d8x_points.json
      [--stages main,robust,kt] [--k1 off|on] [--workers N] [out.json]
  Points = rules 1.2 (A) from the point file, the same floor at every auger level; variants as
  ``run_s6_slope_boundary_check.td_cases`` with the rules 3 point sets (:func:`d8x_cases`). The preset
  ``with_10hz_d1`` is used as it is (ACC_COMBO ``preset``; ACC_WT defaults to this checkout) except the R4c30 order
  gate, which every worker sets explicitly from ``--k1`` (off / on; the preset has it on since the K1
  switch, so off must be installed, not left to the preset). Output ``06_analysis/02_control/d8x/ra/ra_<k1>.json``
  unless ``out`` is given; every run adds ``point``, ``level``, ``mast``, ``stage``, ``variant``,
  ``angles_deg``, ``k1_order_gate``, ``controller_tag``, ``module_files_sha256`` and the ``d8x`` block
  (``d8x_record.run_metrics``); the meta adds the run identity at the start and the end (rules I-1).
  Without ``--points`` nothing of this applies (the run is as before).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
D8X_DIR = REPO_ROOT / "04_scripts" / "03_control" / "d8x"
D8X_ENV = "ACC_D8X"
D8X_K1_ENV = "ACC_D8X_K1"
IS_D8X = "--points" in sys.argv[1:] or os.environ.get(D8X_ENV) == "1"
if IS_D8X:  # before acc_common.install(): the preset as it is, this checkout by default
    os.environ[D8X_ENV] = "1"
    os.environ["ACC_COMBO"] = "preset"
    os.environ.setdefault("ACC_WT", str(REPO_ROOT))

sys.path.insert(0, str(HERE))
import acc_common  # noqa: E402

acc_common.install()
CONFIG_NAME = "C2_tv0.1"

D8X_STAGES = ("main", "robust", "kt")
D8X_ROBUST_LOWER_TAGS = ("pitch+", "pitch-", "roll+", "roll-", "r+p+0.5", "d45++")
"""Rules 3 R-a: td_robust middle / bottom points (beta 2 + d0 1 each)."""
D8X_KT_TAGS = ("pitch+", "pitch-", "roll+", "roll-", "r+p+0.5", "r+p+0.25", "d45++")
"""Rules 3 R-a: td_kt points."""
D8X_BETAS_PA = (0.69e9, 1.6e9)
D8X_RUN_KEYS = ("id", "cfg", "min_true_cyl_force_kN", "min_true_cyl_force_substep_kN", "t_ready_s",
                "t_touch_s", "t_crawler_liftoff_s", "ss_true_att_deg_maxabs", "max_pressure_bar", "fails",
                "guard_active_s", "s_motor_max_mm")
_SERIES: dict = {}


# ------------------------------------------------------------------------------------- D8x
def _d8x_default_out(k1: str) -> Path:
    return REPO_ROOT / "06_analysis" / "02_control" / "d8x" / "ra" / f"ra_{k1}.json"


def _record_module():
    if str(D8X_DIR) not in sys.path:
        sys.path.insert(0, str(D8X_DIR))
    import d8x_record

    return d8x_record


def d8x_cases(points: dict, stages: tuple[str, ...]) -> list[dict]:
    """R-a cases of rules 3: td_main / td_robust / td_kt on the (A) points at every level."""
    import c2py_r8d1_closed_loop as c2py

    rsb = c2py.td2.rsb
    rpt = c2py.rpt
    cases = []

    def add(stage, variant, cid, level, tag, angles, mast, *args, **kwargs):
        case = rsb.mkc(cid, level, angles, mast, *args, **kwargs)
        case["d8x"] = {"stage": stage, "variant": variant, "point": tag, "level": level, "mast": mast,
                       "angles_deg": [float(angles[0]), float(angles[1])]}
        cases.append(case)

    for level in _record_module().LEVELS:
        for tag, angles in points.items():
            if "main" in stages:
                for mast in rpt.MASTS:
                    add("main", "main", f"main|{level}|{mast}|{tag}", level, tag, angles, mast)
            if "robust" in stages:
                _add_robust(add, rpt, level, tag, angles)
            if "kt" in stages:
                _add_kt(add, rpt, rsb, level, tag, angles)
    return [_with_config(case, c2py) for case in cases]


def _add_robust(add, rpt, level, tag, angles) -> None:
    if level == "top":
        for mast in rpt.MASTS:
            for seed in (1, 2):
                add("robust", f"seed{seed}", f"seed|{level}|{mast}|{tag}|{seed}", level, tag, angles, mast,
                    seed=12345 + seed)
            for seed in range(3):
                add("robust", f"d0s{seed}", f"d0|{level}|{mast}|{tag}|{seed}", level, tag, angles, mast,
                    rpt.R1 + "_d0", seed=12345 + seed)
            for beta in D8X_BETAS_PA:
                add("robust", f"beta{beta:g}", f"beta|{level}|{mast}|{tag}|{beta:g}", level, tag, angles,
                    mast, beta=beta)
        return
    if tag not in D8X_ROBUST_LOWER_TAGS:
        return
    for mast in rpt.MASTS:
        for beta in D8X_BETAS_PA:
            add("robust", f"beta{beta:g}", f"beta|{level}|{mast}|{tag}|{beta:g}", level, tag, angles, mast,
                beta=beta)
        add("robust", "d0s0", f"d0|{level}|{mast}|{tag}|0", level, tag, angles, mast, rpt.R1 + "_d0")


def _add_kt(add, rpt, rsb, level, tag, angles) -> None:
    if tag not in D8X_KT_TAGS:
        return
    masts = ("rigid", "stiff") if level == "top" else ("rigid",)
    for mast in masts:
        for scale in (rsb.KT_REL_CHRONO, 0.3 * rsb.KT_REL_CHRONO, 3.0 * rsb.KT_REL_CHRONO):
            extra = {"rcfg_extra": {"ktcr_rel_kn": scale}}
            add("kt", f"kt{scale:.4f}", f"kt|{level}|{mast}|{tag}|{scale:.4f}", level, tag, angles, mast,
                **extra)
            if level == "top":
                add("kt", f"ktd0{scale:.4f}", f"ktd0|{level}|{mast}|{tag}|{scale:.4f}", level, tag, angles,
                    mast, rpt.R1 + "_d0", **extra)


def _with_config(case: dict, c2py) -> dict:
    d8x = case.pop("d8x")
    applied = c2py.td2.r8.apply(case, CONFIG_NAME)
    applied["d8x"] = d8x
    return applied


def _install_series_capture(c2py) -> None:
    """Keep the series of the last ``rpt.run_one`` (``td_one`` drops it before returning)."""
    rpt = c2py.rpt
    if getattr(rpt.run_one, "_d8x_capture", False):
        return
    original = rpt.run_one

    def run_one(case):
        out = original(case)
        _SERIES["S"] = (out.get("_series") or {}).get("S")
        return out

    run_one._d8x_capture = True
    rpt.run_one = run_one


def _d8x_fields(run: dict, adapter, c2py) -> dict:
    """The D8x record of one harness run (``d8x_record.run_metrics`` and the identity fields)."""
    record = _record_module()
    plant = c2py.rmf.LAST["plant"]
    series = _SERIES.get("S")
    if series is None or not plant.record or not plant.hist:
        raise RuntimeError("D8x record: no series / sub-step history of the run")
    import numpy as np

    hist = np.asarray(plant.hist, float)
    pad_normal = hist[:, 13:17]  # record layout of run_mast_flex_c2_check.extra_metrics
    rod_weight = np.asarray(plant.Wr, float)
    attitude = np.degrees(np.column_stack([series["phi"], series["theta"]]))
    stroke = np.asarray(series["x"], float)
    metrics = record.run_metrics(
        t_s=np.asarray(plant.hist_t, float), cyl_force_N=pad_normal - rod_weight,
        rod_weight_N=rod_weight, t_att_s=np.asarray(series["t"], float), att_deg=attitude,
        t_touch_s=adapter.t_touch, t_crawler_off_s=run.get("t_crawler_liftoff_s"),
        t_ready_s=adapter.t_ready_first, events=record.controller_events(adapter.controller),
        max_moving_bar=run.get("max_pressure_bar"), stroke_max_m=float(stroke.max()))
    files = record.repo_module_files(REPO_ROOT)
    return {"k1_order_gate": record.effective_k1(adapter.controller),
            "liftoff_slow_enabled": record.liftoff_slow_enabled(adapter.controller),
            "controller_tag": record.preset_controller_tag(adapter.controller),
            "module_files_sha256": record.files_digest(files), "module_files": files, "d8x": metrics}


# ------------------------------------------------------------------------------------- runs
def run_one(case: dict) -> dict:
    t0 = time.perf_counter()
    try:
        import c2py_r8d1_closed_loop as c2py

        if IS_D8X:
            # Both arms explicitly: the preset has the gate on since the K1 switch.
            record = _record_module()
            record.install_k1_order_gate(record.k1_arm_is_on(os.environ.get(D8X_K1_ENV)))
            _install_series_capture(c2py)
        c2py.rcr.SensorsS = c2py.traces.RecordingSensors
        c2py.rpt.C2RA = c2py.HarnessAdapter
        case["rcfg"]["ca_over"] = dict(case["rcfg"]["ca_over"], **c2py.HARNESS_LOOP_OFF)
        run = c2py.td2.run(case)
        if "error" in run:
            return {"id": case["id"], "error": run["error"], "tb": str(run.get("tb"))[-1500:]}
        adapter = c2py.rmf.LAST["ctrl"]
        names = [e.name for e in adapter.controller.events]
        keys = D8X_RUN_KEYS if IS_D8X else ("id", "cfg", "min_true_cyl_force_kN", "t_ready_s", "t_touch_s",
                                            "ss_true_att_deg_maxabs", "max_pressure_bar", "fails",
                                            "guard_active_s")
        out = {k: run.get(k) for k in keys}
        out.update(id=case["id"], phase=str(adapter.controller.phase), fault=adapter.fault,
                   hold_events=[n for n in names if "TOUCH_TWIST_HOLD" in n],
                   retrigger_deferred=sum("retrigger" in n for n in names),
                   reapproach_starts=sum(n.startswith("leg_reapproach_start") for n in names),
                   warnings=[n for n in names if n.startswith(("WARN", "FAULT"))][:12],
                   commands_sha256=c2py.reapproach_record(adapter.controller, adapter.commands)["commands_sha256"],
                   wall_s=round(time.perf_counter() - t0, 1))
        if IS_D8X:
            out.update(case["d8x"], **_d8x_fields(run, adapter, c2py))
        return out
    except Exception as exc:  # the batch goes on, the record says what failed
        import traceback

        return {"id": case["id"], "error": repr(exc), "tb": traceback.format_exc()[-1500:]}


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path, nargs="?" if IS_D8X else None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--stage", default="all", choices=("main", "all"))
    ap.add_argument("--points", type=Path, default=None, help="D8x point file (rules 1.2); D8x mode")
    ap.add_argument("--stages", default=None, help="D8x: comma list of main, robust, kt (default all three)")
    ap.add_argument("--k1", default=None, choices=("off", "on"), help="D8x: R4c30 order gate (default off)")
    args = ap.parse_args()
    if args.points is None and (args.stages is not None or args.k1 is not None):
        ap.error("--stages and --k1 belong to the D8x mode (--points)")
    if args.points is not None:
        args.stages = tuple(s for s in (args.stages or ",".join(D8X_STAGES)).split(",") if s)
        unknown = sorted(set(args.stages) - set(D8X_STAGES))
        if unknown or not args.stages:
            ap.error(f"--stages: unknown {unknown}, choose from {D8X_STAGES}")
        args.k1 = args.k1 or "off"
        args.out = args.out or _d8x_default_out(args.k1)
    return args


def _load_cases(args: argparse.Namespace) -> list[dict]:
    import c2py_r8d1_closed_loop as c2py

    if args.points is None:
        cases = c2py.td2.r8.cases_D8(CONFIG_NAME)
        if args.stage == "main":
            cases = [c for c in cases if str(c["id"]).startswith("main|")]
    else:
        record = _record_module()
        cases = d8x_cases(record.ra_point_angles(record.load_points(args.points)), args.stages)
    if args.limit:
        cases = cases[:: max(1, len(cases) // args.limit)][:args.limit]
    return cases


def _d8x_meta(args: argparse.Namespace, identity_start: dict) -> dict:
    record = _record_module()
    return {"d8x": {"rules": "06_analysis/02_control/d8x/d8x_rules.md 3 R-a",
                    "points_file": str(args.points), "points_sha256": record.text_sha256(args.points),
                    "stages": list(args.stages), "k1": args.k1, "limit": args.limit,
                    "identity_start": identity_start, "identity_end": record.run_identity(REPO_ROOT)}}


def _pop_module_lists(runs: list[dict]) -> dict[str, list[str]]:
    """Move each run's module file list to one table by digest (runs keep the digest)."""
    lists = {}
    for run in runs:
        files = run.pop("module_files", None)
        if files is not None:
            lists[run["module_files_sha256"]] = files
    return lists


def main() -> None:
    args = _parse_args()
    if args.points is not None:
        os.environ[D8X_K1_ENV] = args.k1  # inherited by the spawned workers
    identity_start = _record_module().run_identity(REPO_ROOT) if IS_D8X else None
    cases = _load_cases(args)
    partial = args.out.with_name(args.out.name + ".partial.jsonl")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if partial.exists():
        for line in partial.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            done[rec["id"]] = rec
    todo = [c for c in cases if c["id"] not in done]
    print(f"cases {len(cases)}, done {len(done)}, to run {len(todo)}, workers {args.workers}", flush=True)
    t0 = time.perf_counter()
    if todo:
        with Pool(max(1, min(args.workers, len(todo)))) as pool, partial.open("a", encoding="utf-8") as sink:
            for n, rec in enumerate(pool.imap_unordered(run_one, todo, chunksize=1), 1):
                sink.write(json.dumps(rec, default=float) + "\n")
                sink.flush()
                done[rec["id"]] = rec
                print(f"[{n}/{len(todo)} {time.perf_counter() - t0:.0f} s] {rec['id']} {rec.get('error', '')[:200]} min {rec.get('min_true_cyl_force_kN')} ready {rec.get('t_ready_s')}", flush=True)
    bad = acc_common.main_tree_modules()
    if bad:
        raise SystemExit(f"main-tree modules imported: {bad[:5]}")
    meta = {**acc_common.provenance(), "n": len(cases), "wall_s_this_start": round(time.perf_counter() - t0, 1),
            "config": CONFIG_NAME}
    runs = [done[c["id"]] for c in cases]
    if IS_D8X:
        meta.update(_d8x_meta(args, identity_start))
        meta["d8x"]["module_files_by_sha256"] = _pop_module_lists(runs)
    doc = {"meta": meta, "runs": runs}
    args.out.write_text(json.dumps(doc, indent=1, default=float), encoding="utf-8")
    print("done", args.out, "errors", sum("error" in r for r in doc["runs"]), flush=True)


if __name__ == "__main__":
    main()
