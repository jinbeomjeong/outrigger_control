"""Crawler stiffness rows: boundary slope points x auger levels x S (kn_total x S, damping x sqrt(S)) on the rigid floor.

Steady harness path of the hydraulic verdict (``s9_soil_slope.run_one``), flow limit off, F_s 4 kN (nominal, ASSUMPTION).
36 points x S 3, 100 = 72 rows. S 100 stands for the rigid crawler of L2b-NSC (crawler_hold_report.md).
Resumes from <out>.partial.jsonl. Usage: python -I -B acc_crawler.py <out.json> [--workers N] [--limit N] [--scales 3,100]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from multiprocessing import get_context
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acc_common  # noqa: E402

acc_common.install()
FS_KN = 4.0


def run_one(job: dict) -> dict:
    t0 = time.perf_counter()
    try:
        import verdict_cases
        import verdict_runs
        from harness_flow import FlowSetting

        import dyn_model as dm

        scale = float(job["S"])
        original_points = dm.crawler_points
        dm.crawler_points = lambda p, kn_scale=1.0: original_points(p, kn_scale * scale)
        inner = verdict_runs.make_flow_plant_class

        def make_class(plant_base, setting):
            flow = inner(plant_base, setting)

            class CrawlerPlant(flow):
                def __init__(self, *a, **kw):
                    super().__init__(*a, **kw)
                    self.ccr = self.ccr * math.sqrt(scale)
                    self.ctcr = self.ctcr * math.sqrt(scale)

            return CrawlerPlant

        verdict_runs.make_flow_plant_class = make_class
        twin = verdict_cases._rigid_row(job["level"], job["roll"], job["pitch"], FS_KN)
        case = verdict_cases.VerdictCase(job["id"], job["id"], twin)
        result, _ = verdict_runs.execute(case, FlowSetting(is_enabled=False), None)
        if "error" in result:
            return {"id": job["id"], "job": job, "error": result["error"], "tb": str(result.get("tb"))[-1500:]}
        return {"id": job["id"], "job": job, "final_phase": result["final_phase"], "harness_class": result.get("harness_class"),
                "failed_rows": result.get("failed_rows"), "values": result.get("values"), "warnings": result.get("warnings"),
                "events": [e for e in result["events"] if e[1].startswith(("INFO_TOUCH", "WARN", "FAULT", "INFO_LIFT", "leg_reapproach"))][:30],
                "commands_sha256": result["commands_sha256"], "max_stroke_reading_mm": result.get("max_motor_stroke_reading_mm"),
                "wall_s": round(time.perf_counter() - t0, 1)}
    except Exception as exc:
        import traceback

        return {"id": job["id"], "job": job, "error": repr(exc), "tb": traceback.format_exc()[-1500:]}


def jobs(scales) -> list[dict]:
    import run_s6_slope_boundary_check as rsb

    points = rsb.td_points(rsb.load())
    return [{"id": f"S{s:g}|{lv}|{tag}", "S": s, "level": lv, "tag": tag, "roll": round(float(ang[0]), 6), "pitch": round(float(ang[1]), 6)}
            for s in scales for (lv, tag), ang in points.items()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--scales", default="3,100")
    args = ap.parse_args()
    all_jobs = jobs([float(x) for x in args.scales.split(",")])
    if args.limit:
        all_jobs = all_jobs[:: max(1, len(all_jobs) // args.limit)][:args.limit]
    partial = args.out.with_name(args.out.name + ".partial.jsonl")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if partial.exists():
        for line in partial.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            done[rec["id"]] = rec
    todo = [j for j in all_jobs if j["id"] not in done]
    print(f"jobs {len(all_jobs)}, done {len(done)}, to run {len(todo)}", flush=True)
    t0 = time.perf_counter()
    if todo:
        with get_context("spawn").Pool(max(1, min(args.workers, len(todo))), maxtasksperchild=1) as pool, partial.open("a", encoding="utf-8") as sink:
            for n, rec in enumerate(pool.imap_unordered(run_one, todo, chunksize=1), 1):
                sink.write(json.dumps(rec, default=float) + "\n")
                sink.flush()
                done[rec["id"]] = rec
                print(f"[{n}/{len(todo)} {time.perf_counter() - t0:.0f} s] {rec['id']} {rec.get('final_phase')} {rec.get('harness_class')} {rec.get('error', '')[:200]}", flush=True)
    doc = {"meta": {**acc_common.provenance(), "n": len(all_jobs), "fs_kN": FS_KN, "wall_s_this_start": round(time.perf_counter() - t0, 1)},
           "runs": [done[j["id"]] for j in all_jobs]}
    args.out.write_text(json.dumps(doc, indent=1, default=float), encoding="utf-8")
    print("done", args.out, "errors", sum("error" in r for r in doc["runs"]), flush=True)


if __name__ == "__main__":
    main()
