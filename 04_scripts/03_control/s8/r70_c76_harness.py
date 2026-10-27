"""C-S8-76 same-condition harness values: the four Chrono L1-R cases at F_s 0 (L1-R has no seal friction), project
controller (proj) and the P-S8-28 candidate (AG2), on the r69 / r70 harness.

  G8C1_top_edge_FL_g200 / g170  -> slope|edge|top|0.0|FL|raised|200.0 / 170.0
  G8C2_top_flat_FL_g55 / RR_g200 -> main|flat|top|0.0|FL|raised|55.0 / main|flat|top|0.0|RR|raised|200.0
plus the two refs (edge, flat) at F_s 0.

Usage (dynamics-dev): python -I r70_c76_harness.py <project_root> <out_json> [workers]
Env: R70_AFFINITY (hex mask on the parent).
"""
from __future__ import annotations

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s8"))

import r70_p28_screen as r70  # noqa: E402

CASES = {
    "G8C1_top_edge_FL_g200": "slope|edge|top|0.0|FL|raised|200.0",
    "G8C1_top_edge_FL_g170": "slope|edge|top|0.0|FL|raised|170.0",
    "G8C2_top_flat_FL_g55": "main|flat|top|0.0|FL|raised|55.0",
    "G8C2_top_flat_RR_g200": "main|flat|top|0.0|RR|raised|200.0",
    "ref_edge": "slope|edge|top|0.0|ref|none|0",
    "ref_flat": "main|flat|top|0.0|ref|none|0",
}


def main():
    r70.set_parent_placement()
    keys = [f"{k}|{v}" for k in CASES.values() for v in ("proj", "AG2")]
    t0 = time.perf_counter()
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    with Pool(min(workers, len(keys))) as pool:
        res = pool.map(r70.job, keys, chunksize=1)
    name = {v: k for k, v in CASES.items()}
    for r in res:
        r["case"] = name.get(r.get("r69_key"))
    Path(sys.argv[2]).write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r70_c76_harness.py",
                                                      "wall_s": round(time.perf_counter() - t0, 1)},
                                             "results": res}, indent=1, default=float), encoding="utf-8")
    for r in res:
        if "error" in r:
            print(r["key"], r["error"])
            continue
        tch = r.get("touch") or {}
        print(r["case"], r["variant"], r.get("final_phase"), "pass", r["pass"],
              {k: v for k, v in r["gates"].items() if not v}, "h", r["info"].get("g0_mm"),
              "stroke", r["stroke_end_mm"], "D8", min(r["min_F_after_liftoff_kN"].values()),
              "att", r.get("att_end_deg"), "clear", r["crawler_clearance_end_mm"],
              "T3", tch.get("post_contact_stroke_mm"), "latch", tch.get("latch_after_contact_s"),
              "T4", max(tch.get("max_abs_att_change_deg") or [0]), "touch_s", tch.get("duration_s"),
              "t_ready", r.get("t_ready"), "cmd", r["cmd_sha256"])


if __name__ == "__main__":
    main()
