"""D8 576 (td_main 144 + td_robust 432) with the project C2 on the revision-30 harness (r8d1_td2 plant and metrics).

The stored r8d1_td2 D8 runs use the harness controller, not C2Controller; this driver puts C2Controller in through
``c2py_r8d1_closed_loop.HarnessAdapter`` (controller queue and increment limit, harness queue off).
Resumes from <out>.partial.jsonl. Usage: python -I -B acc_d8.py <out.json> [--workers N] [--limit N] [--stage main|all]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acc_common  # noqa: E402

acc_common.install()
CONFIG_NAME = "C2_tv0.1"


def run_one(case: dict) -> dict:
    t0 = time.perf_counter()
    try:
        import c2py_r8d1_closed_loop as c2py

        c2py.rcr.SensorsS = c2py.traces.RecordingSensors
        c2py.rpt.C2RA = c2py.HarnessAdapter
        case["rcfg"]["ca_over"] = dict(case["rcfg"]["ca_over"], **c2py.HARNESS_LOOP_OFF)
        run = c2py.td2.run(case)
        if "error" in run:
            return {"id": case["id"], "error": run["error"], "tb": str(run.get("tb"))[-1500:]}
        adapter = c2py.rmf.LAST["ctrl"]
        names = [e.name for e in adapter.controller.events]
        out = {k: run.get(k) for k in ("id", "cfg", "min_true_cyl_force_kN", "t_ready_s", "t_touch_s", "ss_true_att_deg_maxabs",
                                       "max_pressure_bar", "fails", "guard_active_s")}
        out.update(id=case["id"], phase=str(adapter.controller.phase), fault=adapter.fault,
                   hold_events=[n for n in names if "TOUCH_TWIST_HOLD" in n],
                   retrigger_deferred=sum("retrigger" in n for n in names),
                   reapproach_starts=sum(n.startswith("leg_reapproach_start") for n in names),
                   warnings=[n for n in names if n.startswith(("WARN", "FAULT"))][:12],
                   commands_sha256=c2py.reapproach_record(adapter.controller, adapter.commands)["commands_sha256"],
                   wall_s=round(time.perf_counter() - t0, 1))
        return out
    except Exception as exc:  # the batch goes on, the record says what failed
        import traceback

        return {"id": case["id"], "error": repr(exc), "tb": traceback.format_exc()[-1500:]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--stage", default="all", choices=("main", "all"))
    args = ap.parse_args()
    import c2py_r8d1_closed_loop as c2py

    cases = c2py.td2.r8.cases_D8(CONFIG_NAME)
    if args.stage == "main":
        cases = [c for c in cases if str(c["id"]).startswith("main|")]
    if args.limit:
        cases = cases[:: max(1, len(cases) // args.limit)][:args.limit]
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
    doc = {"meta": {**acc_common.provenance(), "n": len(cases), "wall_s_this_start": round(time.perf_counter() - t0, 1), "config": CONFIG_NAME},
           "runs": [done[c["id"]] for c in cases]}
    args.out.write_text(json.dumps(doc, indent=1, default=float), encoding="utf-8")
    print("done", args.out, "errors", sum("error" in r for r in doc["runs"]), flush=True)


if __name__ == "__main__":
    main()
