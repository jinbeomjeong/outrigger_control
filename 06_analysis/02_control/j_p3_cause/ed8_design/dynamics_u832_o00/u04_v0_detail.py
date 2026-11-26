"""Detail of the stored V0 grid runs of the RE1bF clusters at the four offsets: per-leg lift
intervals, re-approach starts, event time (seen V0 records only).

Usage: python -I -B u04_v0_detail.py <out_folder>
"""
import json
import sys
from pathlib import Path

GRID = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance\c4g2_only\grid")
FILES = ["grid_r69_bottom.json", "grid_r69_top.json", "grid_r67_top.json"]
out = Path(sys.argv[1])
lines = []
for fn in FILES:
    d = json.loads((GRID / fn).read_text(encoding="utf-8"))
    for job in d["results"]:
        if job.get("timing") != "ready" or job.get("leg") not in ("FL", "FR", "RL"):
            continue
        lines.append(f"## {fn} {job['level']} {job['leg']} Fs{job['fs_kN']} {job['timing']} "
                     f"branch_t {job.get('branch_t_s')} phase {job.get('branch_phase')} "
                     f"t_ready {job.get('base', {}).get('t_ready')}")
        for r in job["runs"]:
            if r.get("event") != "RE1bF":
                continue
            lf = r.get("lifts") or {}
            lifts = {k: (v.get("first_s"), v.get("sum_s"), v.get("last_touch_s"), v.get("n"),
                         v.get("max_gap_mm")) for k, v in lf.items()}
            lines.append(f"  o{r['offset_s']:<6} t_ev {r.get('t_ev_s')} ph {r.get('phase_at_event')} "
                         f"pu {r.get('pair_union_s')} last {r.get('pair_last_touch_s')} "
                         f"lifts(first,sum,last,n,gap) {lifts}")
            lines.append(f"           reapp {r.get('reapproach_starts')} late {r.get('n_late_starts')} "
                         f"back {r.get('t_ready_back_s')} warn {r.get('warnings')}")
(out / "u04_v0_detail.txt").write_text("\n".join(lines), encoding="utf-8")
print("lines", len(lines))
