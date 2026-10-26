"""Summarise ``m4_offline.py`` output by batch group and reason.

Usage: ``python -I -X utf8 04_scripts/02_chrono/s9_merge/m4_table.py <m4.json> [<summary.json>]``
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path


def group_of(run: str) -> str:
    p = Path(run).as_posix()
    i = p.find("07_results/")
    parts = p[i + len("07_results/"):].split("/")
    # S8/<batch>/<sub>/... ; S7/<batch>/<case>
    if len(parts) >= 4 and parts[2] in ("bases", "episodes", "judged", "A_rt", "B_f1only",
                                         "C_gate", "D_fs24", "E_drain"):
        return "/".join(parts[:3])
    return "/".join(parts[:2])


def main(argv: list[str]) -> int:
    rows = json.loads(Path(argv[0]).read_text("utf-8"))
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        groups[group_of(r["run"])].append(r)
    table = []
    for g, rs in sorted(groups.items()):
        reasons = collections.Counter(r.get("reason") or "OK" for r in rs)
        first = collections.Counter(r.get("first_phase") for r in rs)
        locs = [r["loc"] for r in rs if r.get("loc")]
        rises = [r["best_rise_N"] for r in rs if r.get("loc")]
        clear_p = [r["loc"]["clearance_at_P_m"] for r in rs if r.get("loc")]
        clear_l = [r["loc"]["clearance_at_loc_m"] for r in rs if r.get("loc")]
        ratio = [r["loc"]["W_ratio"] for r in rs if r.get("loc")]
        lead = [r["release_t_s"] - r["loc"]["t_loc_s"] for r in rs
                if r.get("loc") and r.get("release_t_s") is not None]
        row = {"group": g, "n": len(rs), "first_phase": dict(first),
               "n_with_level": sum(1 for r in rs if r.get("n_level_calls")),
               "n_loc": len(locs), "n_unchanged": sum(1 for r in rs if r.get("unchanged")),
               "reasons": dict(reasons)}
        if locs:
            row.update(rise_max_N=max(rises), c_P_max_mm=1e3 * max(clear_p),
                       c_loc_max_mm=1e3 * max(clear_l), W_ratio=[min(ratio), max(ratio)],
                       release_minus_loc_s_min=min(lead) if lead else None)
        table.append(row)
        print(json.dumps(row, ensure_ascii=False))
    if len(argv) > 1:
        Path(argv[1]).write_text(json.dumps(table, indent=1, ensure_ascii=False), "utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
