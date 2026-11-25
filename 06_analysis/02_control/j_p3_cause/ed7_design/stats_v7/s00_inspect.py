"""Structure probe (identifiers only) for the ed. 7 stats design (stats-design-expert, 2026-11-24).

Reads: the stored V0 grid (touch_phase/acceptance/c4g2_only/grid, public, committed 2026-11-05) and
the ed. 6 grid key file ed6_design/keys/confirm_b_grid192.json (key list, sealed with ed. 6).
Writes the key/field vocabulary of one grid run and of one key-file row to argv[1] (json).
No ed. 7 results exist; no blind path is touched. stdout: status only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control")
GRID = ROOT / "touch_phase" / "acceptance" / "c4g2_only" / "grid"
KEYS = ROOT / "j_p3_cause" / "ed6_design" / "keys" / "confirm_b_grid192.json"


def shape(v, depth=0):
    if depth > 3:
        return type(v).__name__
    if isinstance(v, dict):
        return {k: shape(x, depth + 1) for k, x in list(v.items())[:40]}
    if isinstance(v, list):
        return [shape(v[0], depth + 1)] if v else []
    return type(v).__name__ if not isinstance(v, (int, float, str, bool)) or depth > 2 else v


def main() -> int:
    out = {}
    d = json.loads((GRID / "grid_r67_main.json").read_text(encoding="utf-8"))
    out["grid_top_keys"] = list(d)
    job = d["results"][0]
    out["grid_job_keys"] = list(job)
    runs = job["runs"]
    run = next(iter(runs.values())) if isinstance(runs, dict) else runs[0]
    out["grid_run_shape"] = shape(run)
    k = json.loads(KEYS.read_text(encoding="utf-8"))
    out["keyfile_top"] = list(k) if isinstance(k, dict) else "list"
    rows = k["rows"] if isinstance(k, dict) and "rows" in k else k
    if isinstance(rows, dict):
        out["keyfile_rows_is_dict_first_keys"] = list(rows)[:5]
        rows = list(rows.values())
    out["keyfile_row0"] = shape(rows[0])
    out["keyfile_meta"] = {kk: (vv if not isinstance(vv, (list, dict)) else type(vv).__name__)
                           for kk, vv in (k.items() if isinstance(k, dict) else [])}
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
