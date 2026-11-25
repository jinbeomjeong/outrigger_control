"""Did the review 1-4 / 1-1 paths fire on a VBM preview line? Prints the P1 supplement record
counts of one ``run_v5`` job (record values only). Scratch helper.

Usage: python -I -B path_counts.py <worktree> <job json> <out json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


R12 = {"case": "R12", "eps": 0.0, "offset_s": 0.0}
S5 = {"case": "S5", "eps": 0.0}
JOBS = {"VBM_R12": {**R12, "setting": "VBM"}, "VBMslow_R12": {**R12, "setting": "VBMslow"},
        "VBMslow_S5": {**S5, "setting": "VBMslow"}}


def main() -> None:
    worktree, job, out_path = Path(sys.argv[1]), JOBS[sys.argv[2]], Path(sys.argv[3])
    sys.path[:0] = [str(worktree / "04_scripts" / "04_hydraulic" / "coupled"),
                    str(worktree / "03_src")]
    import run_v5

    record = run_v5.run_one({**job, "mask": None, "t4h_dir": str(out_path.parent / "t4h")})
    gate = (record.get("hydraulics_record") or {}).get("line_fill_gate") or {}
    hydraulics = record.get("hydraulics_record") or {}
    summary = {"job": job, "hash": record.get("commands_sha256"),
               "rod_check_clear_count": gate.get("rod_check_clear_count"),
               "rod_check_clear_rows": len(gate.get("rod_check_clear_log") or []),
               "fill_rise_peak_bar": gate.get("fill_rise_peak_bar"),
               "fill_releases": len(hydraulics.get("p1_fill_release_log") or []),
               "n_fills": gate.get("n_fills")}
    out_path.write_text(json.dumps(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
