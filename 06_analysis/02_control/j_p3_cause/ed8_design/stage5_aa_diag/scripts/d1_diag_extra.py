"""Two more tables of the stage-5 A/A D1 diagnosis (record only; no judgement).

Usage (python-dev or dynamics-dev):
  python.exe -I -B d1_diag_extra.py <stage5_aa_diag folder>

Writes (refuses files that exist):
  gyro_availability.csv   per job: traced periods, lifted periods, periods without gyro
                          partial means, periods with the lever term applied / missing
  first_step_period.csv   per job and candidate leg: the first period after the lift with a
                          head step candidate (dp_h, |dp_h| A_p, threshold, sum F change,
                          M_eff df_z, residual change, outcome)
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

SAMPLE_PERIOD_S = 0.1


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _gyro_row(label: str, rows: list[dict]) -> dict:
    lifted = [row for row in rows if row["is_crawler_lifted"]]
    return {"label": label, "periods": len(rows), "lifted_periods": len(lifted),
            "periods_without_gyro": sum(row["gyro_partial_means"] is None for row in rows),
            "lifted_without_gyro": sum(row["gyro_partial_means"] is None for row in lifted),
            "lifted_lever_applied": sum(row["lever_z_m_s2"] is not None for row in lifted),
            "lifted_lever_missing": sum(row["is_lever_missing"] for row in lifted),
            "periods_without_f_z": sum(row["f_z_raw_m_s2"] is None for row in rows),
            "first_gyro_missing_event_t_s": next(
                (row["t_s"] for row in rows if "WARN_D1_IMU_GYRO_MISSING" in row["events"]),
                None)}


def _first_step_rows(summary: dict, rows: list[dict]) -> list[dict]:
    lift_s = summary["lift_s"]
    after = [row for row in rows if row["t_s"] > lift_s - 1e-9 and row.get("candidates")]
    if not after:
        return [{"label": summary["label"], "lift_s": lift_s, "t_s": None}]
    row = after[0]
    mass, f_z, f_z_before = row["mass_kg"], row["f_z_used_m_s2"], row["previous_f_z_used_m_s2"]
    common = {
        "label": summary["label"], "final_phase": summary["final_phase"],
        "t_event_s": summary["t_event_s"], "lift_s": round(lift_s, 4),
        "lift_phase_in_period_s": summary.get("lift_phase_in_period_s"),
        "t_s": round(row["t_s"], 4), "periods_after_lift": round(
            (row["t_s"] - lift_s) / SAMPLE_PERIOD_S, 3),
        "sum_change_kN": (row["net_sum_N"] - row["previous_net_sum_N"]) / 1e3,
        "f_z_before_m_s2": f_z_before, "f_z_now_m_s2": f_z,
        "M_eff_kg": mass, "M_df_z_kN": mass * (f_z - f_z_before) / 1e3,
        "residual_change_kN": row["residual_change_N"] / 1e3,
        "is_lever_missing": row["is_lever_missing"],
        "dp_head_bar": " ".join(f"{value / 1e5:.2f}" for value in row["dp_head_Pa"]),
    }
    out = []
    for leg, candidate in row["candidates"].items():
        out.append({**common, "leg": leg, "leg_dp_head_bar": candidate["dp_head_Pa"] / 1e5,
                    "step_force_kN": candidate["step_force_N"] / 1e3,
                    "threshold_kN": candidate["threshold_N"] / 1e3,
                    "residual_change_over_threshold": row["residual_change_N"]
                    / candidate["threshold_N"],
                    "is_unexplained": candidate["is_unexplained"]})
    return out


def main() -> int:
    folder = Path(sys.argv[1])
    targets = [folder / "gyro_availability.csv", folder / "first_step_period.csv"]
    if any(path.exists() for path in targets):
        print("refusing to overwrite")
        return 2
    summaries = json.loads((folder / "diag_summary.json").read_text(encoding="utf-8"))
    gyro_rows, step_rows = [], []
    for summary in summaries:
        trace = json.loads((folder / f"trace_{summary['label']}.json").read_text(
            encoding="utf-8"))
        rows = [row for row in trace["rows"] if row["monitor"] == summary["primary_monitor"]]
        gyro_rows.append(_gyro_row(summary["label"], rows))
        step_rows += _first_step_rows(summary, rows)
    _write_csv(targets[0], gyro_rows)
    _write_csv(targets[1], step_rows)
    for row in gyro_rows:
        print(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
