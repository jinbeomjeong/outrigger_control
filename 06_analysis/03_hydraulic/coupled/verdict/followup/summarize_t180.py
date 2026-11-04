"""Values of the two 180 s S1 runs; also checks the 10 Hz commands against the stored shorter runs."""
import json
import sys
from pathlib import Path

import numpy as np

STORED = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict")
PAIRS = {"B_S1_eta0.90_t180s": "B_S1_eta0.90", "OFF_S1_t180s": "OFF_S1"}


def phase_segments(t: np.ndarray, phase: np.ndarray) -> list[list]:
    segments = []
    for i, name in enumerate(phase.tolist()):
        if not segments or segments[-1][0] != name:
            segments.append([name, round(float(t[i]), 1), round(float(t[i]), 1)])
        else:
            segments[-1][2] = round(float(t[i]), 1)
    return segments


def summarize(run_id: str, stored_id: str, folder: Path) -> dict:
    record = json.loads((folder / f"{run_id}.json").read_text(encoding="utf-8"))
    stored = json.loads((STORED / f"{stored_id}.json").read_text(encoding="utf-8"))
    with np.load(folder / f"{run_id}.npz") as data:
        t, phase, command = data["t"], data["phase"], data["command"]
        filtered, integral = data["filtered_deg"], data["integral"]
    with np.load(STORED / f"{stored_id}.npz") as data:
        stored_command = data["command"]
    common = len(stored_command)
    values = record["values"]
    t_ready = values["times"]["t_first_ready_s"]
    moving = np.flatnonzero(np.abs(command).max(axis=1) > 0.0)
    after_ready_events = [e for e in record["events"] if t_ready and e[0] >= t_ready]
    return {
        "run_id": run_id, "t_end_s": float(t[-1]), "periods": len(t),
        "command_prefix_equal_stored": command[:common].tobytes() == stored_command.tobytes(),
        "stored_periods": common, "stored_t_first_ready_s": stored["values"]["times"]["t_first_ready_s"],
        "final_phase": record["final_phase"], "harness_class": record["harness_class"],
        "failed_rows": record["failed_rows"], "times": values["times"],
        "last_nonzero_command_t_s": float(t[moving[-1]]) if moving.size else None,
        "phase_segments": phase_segments(t, phase),
        "events_after_first_ready": after_ready_events,
        "end_filtered_deg": np.round(filtered[-1], 5).tolist(),
        "end_integral_rad_s": np.round(integral[-1], 6).tolist(),
        "attitude": values["attitude"], "forces": values["forces"], "twist": values["twist"],
        "E1": values.get("E1"), "E2": values.get("E2"), "E3": values.get("E3"),
        "E4_saturated_s": (values.get("E4") or {}).get("saturated_s"),
        "E5": values.get("E5"),
        "V2_a": values.get("V2_a"),
        "rows": {key: record["rows"][key] for key in ("P3-1", "P3-3", "P3-4", "P3-5", "P3-6")
                 if key in record["rows"]},
        "rut_ready_mm": record["rut_ready_mm"], "rut_end_mm": record["rut_end_mm"],
        "max_stroke_mm": record["max_motor_stroke_reading_mm"],
        "commands_sha256": record["commands_sha256"],
    }


def main() -> None:
    folder, out = Path(sys.argv[1]), Path(sys.argv[2])
    report = {run: summarize(run, stored, folder) for run, stored in PAIRS.items()}
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    for row in report.values():
        print(row["run_id"], row["t_end_s"], row["command_prefix_equal_stored"], row["stored_periods"],
              row["final_phase"], row["harness_class"], row["failed_rows"], row["times"],
              "last_cmd", row["last_nonzero_command_t_s"])
        print(" segments", row["phase_segments"])
        print(" events", row["events_after_first_ready"])


if __name__ == "__main__":
    main()
