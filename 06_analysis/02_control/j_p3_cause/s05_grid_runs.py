"""Step 5: the two grid breach runs (no T4h record kept): lock events, events, LAS / K1 records.

Prints for results[13].runs[3] of grid_r67_top.json (FR) and results[12].runs[0] of
grid_r69_bottom.json (RR) the run summary keys around the breach (46-51 s). Read-only.
"""
import json
from pathlib import Path

RK1 = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1")


def main():
    for fn, ri, rj, leg in (("grid_r67_top.json", 13, 3, 1), ("grid_r69_bottom.json", 12, 0, 3)):
        d = json.loads((RK1 / "h9_grid" / fn).read_text(encoding="utf-8"))
        res = d["results"][ri]
        run = res["runs"][rj]
        print("=" * 100)
        print(fn, res["key"], "branch_t_s", res.get("branch_t_s"), "run", rj)
        for k in ("event", "offset_s", "phase_at_event", "t_ev_s", "pass", "min_F_after_event_kN",
                  "min_F_after_W_kN", "adj_min_F_in_W_kN", "reapproach_starts", "n_late_starts",
                  "final_phase", "t_ready_back_s", "fault_events", "warnings", "lifts", "pair",
                  "las_events", "margins", "gates", "twist", "run_after_s"):
            print(f"  {k}: {json.dumps(run.get(k))[:700]}")
        hr = run["hydraulics_record"]
        ev = [e for e in hr.get("lock_events", []) if 46.0 <= e[0] <= 51.0]
        print("  lock events 46-51 s:", ev)
        print("  ext_lock_log 46-51 s:", [r for r in hr.get("ext_lock_log", []) if 46 <= r[0] <= 51])
        print("  tension_truth:", json.dumps(hr.get("tension_truth"))[:600])
        ebc = hr["extend_bound_check"]
        print("  ebc leg:", {k: ebc[k][leg] for k in ebc if isinstance(ebc[k], list)})
        print("  resume_k1:", json.dumps(run.get("resume_k1"))[:900])
        print("  runs in this result:", len(res["runs"]),
              [(r.get("offset_s"), r["hydraulics_record"]["extend_bound_check"]["breach_reads"])
               for r in res["runs"]])


if __name__ == "__main__":
    main()
