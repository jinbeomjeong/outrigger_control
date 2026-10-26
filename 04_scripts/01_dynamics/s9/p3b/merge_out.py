"""Merge the S9 P3b dynamics intermediates into one JSON (dynamics_model.md rev. 53, 5.37.10/5.38).

Reads ``p3b_judge.json``, ``p3b_judge2.json`` and ``p3b_roll_ratio.json`` from a work folder
(outputs of the scripts of the same names) and writes
``06_analysis/01_chrono/19_S9/s9_P3b_dyn_judgement_rev53.json`` (default): per case the
``p3b_judge`` values plus ``extra`` (``p3b_judge2``) and ``roll`` (``p3b_roll_ratio``), the dt
checks D1 / D2, the D2 end-point values printed by ``d2_check.py`` (copied by hand below) and
the P3a-7 attitude recomputation. ``scripts_sha256_12`` holds the first 12 hex digits of the
SHA-256 of the four computing scripts in this folder (line endings normalised to LF).

Usage (dynamics-dev, from the repository root, one command line):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/s9/p3b/merge_out.py
      <work_dir> [<out_json>]
"""

import argparse
import hashlib
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUT = ROOT / "06_analysis" / "01_chrono" / "19_S9" / "s9_P3b_dyn_judgement_rev53.json"
SCRIPTS = ["p3b_judge.py", "p3b_judge2.py", "p3b_roll_ratio.py", "d2_check.py"]
ABOUT = (
    "S9 P3b dynamics judgement support values (dynamics_model.md rev. 53, 5.37.10 / 5.38). "
    "Frame: body x fwd, y left, z up; roll > 0 left up, pitch > 0 nose down; "
    "g = (0, 0, -9.80665) m/s^2. "
    "Sinkage + = pad bottom below SCM plane (crawler bottom + 4 mm). "
    "SI unless key says mm / kN / deg.")
SOURCES = {
    "P3b": "07_results/S9/batch_P3b_20261026_122444 (step_series.npz 1 ms, result.json)",
    "summary": "06_analysis/01_chrono/19_S9/s9_P3b_summary.json",
    "D1": "07_results/S9/batch_DT_20261026_122444/DT_G1_B_top_M14s_dashpot8s_dt5e-5 "
          "vs s9_P2prime_summary.json",
    "D2": "07_results/S9/batch_DT_20261026_122444/DT_P3a_G1_B_dt5e-5 "
          "vs 07_results/S9/batch_P3a_20261026_092653/P3a_G1_B",
    "P3a": "s9_P3a_summary.json + batch_P3a series.npz (5.37.1 P3a-7 correction)",
}
SCRIPTS_LOCATION = (
    "04_scripts/01_dynamics/s9/p3b (moved 2026-10-26 from the dynamics-expert scratchpad; "
    "SHA over LF-normalised text)")
# Printed by d2_check.py (1 ms grid of the dt 1e-4 run), copied by hand.
D2_END_POINT = {
    "end_sink_rel_pct": [0.00325, 0.00238, -0.00102, -0.00493],
    "end_rp_abs_diff_deg": [-3.41e-06, 6.46e-06],
    "d_end_vs_own_settle_diff_deg": [-3.42e-06, 7.08e-06],
    "traj_max_abs_d_sink_mm": 0.00304, "traj_max_abs_d_rp_deg": [9.46e-06, 1.81e-05],
    "traj_max_abs_dF_over_Fmax_pct": [0.129, 0.167, 0.245, 0.211],
    "t_liftoff_s": [24.916, 24.916], "note": "d2_check.py, 1 ms grid of the dt 1e-4 run",
}


def script_sha256_12(path: Path) -> str:
    """First 12 hex digits of the SHA-256 of a text file with LF line endings."""
    text = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(text).hexdigest()[:12]


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("work_dir", type=Path,
                        help="folder with p3b_judge.json, p3b_judge2.json, p3b_roll_ratio.json")
    parser.add_argument("out_json", nargs="?", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main():
    args = _parse_args()
    a = json.loads((args.work_dir / "p3b_judge.json").read_text("utf-8"))
    b = json.loads((args.work_dir / "p3b_judge2.json").read_text("utf-8"))
    c = json.loads((args.work_dir / "p3b_roll_ratio.json").read_text("utf-8"))
    out = {
        "about": ABOUT,
        "sources": SOURCES,
        "scripts_sha256_12": {n: script_sha256_12(SCRIPT_DIR / n) for n in SCRIPTS},
        "scripts_location": SCRIPTS_LOCATION,
        "cases": {k: {**a["cases"][k], **{"extra": b[k]}, **{"roll": c[k]}} for k in a["cases"]},
        "dt": a["dt"],
        "D2_end_point": D2_END_POINT,
        "p3a_attitude": a["p3a_attitude"],
    }
    out_json = args.out_json
    out_json.write_text(json.dumps(out, indent=1, default=float), "utf-8")
    print(out_json, out_json.stat().st_size, hashlib.sha256(out_json.read_bytes()).hexdigest()[:12])
    print(out["scripts_sha256_12"])


if __name__ == "__main__":
    main()
