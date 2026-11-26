"""Provenance of the U832 / o0.0 analysis: inputs (sha256), code identity, column definitions.

Usage: python -I -B u14_provenance.py <folder>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

folder = Path(sys.argv[1])
R = Path(r"C:\workspace\outrigger_control\06_analysis\02_control")
J = R / "j_p3_cause" / "j9_runs"
G = R / "touch_phase" / "acceptance" / "c4g2_only" / "grid"
WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed7-impl")
inputs = {
    "ed7_confirm_g1": J / "8a2a52ce" / "confirm_a1" / "confirm_g1.jsonl",
    "ed7_probe_d": J / "8a2a52ce" / "confirm_a1" / "ed7_probe_d.jsonl",
    "ed7_j9_main": J / "8a2a52ce" / "j9main_a1" / "j9_main.jsonl",
    "ed7_sens": J / "8a2a52ce" / "sens_a1" / "sens.jsonl",
    "ed6_confirm_b_grid192": J / "79495405" / "confirm_a1" / "confirm_b.jsonl",
    "ed6_confirm_a": J / "79495405" / "confirm_a1" / "confirm_a.jsonl",
    **{f"v0_grid_{p.stem}": G / f"{p.stem}.json" for p in
       (Path("grid_r67_main"), Path("grid_r67_top"), Path("grid_r69_bottom"), Path("grid_r69_top"))},
    "rerun_runs_jsonl": folder / "rerun_raw" / "runs.jsonl",
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


head = subprocess.run(["git", "-C", str(WT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
status = subprocess.run(["git", "-C", str(WT), "status", "--porcelain"], capture_output=True, text=True).stdout
code = {
    "U832 gate": "04_scripts/03_control/s8/r67_g1_screen.py:323-328 (pair, union, last touch), :367-370 (gates), :376 (margins); ed7-impl C 8a2a52ce = ed7-judge T' (same file content used by the judge via verdict_runs)",
    "event time": "04_scripts/04_hydraulic/coupled/verdict_runs.py:564-566 (stop_t = target - PRE_S, t_event = plant.t + PRE_S + offset_s); r67_g1_screen.py:214-216 (run_base stops on the 0.1 s control grid)",
    "floor event": "r67_g1_screen.py:249-254 (Poly345 floor offset per 1 ms chunk, tau from the chunk start time)",
    "control period": "04_scripts/03_control/s8/r51_reapp_closed_loop.py:328-349 (1 ms chunks, 10 ms IMU samples, 0.1 s period; floor_fn before every chunk)",
    "re-approach start/end": "03_src/outrigger_sim/control/c2.py:6255-6351 (_update_lifted_reapproach, _end_finished_reapproaches: exit after exit_samples at >= F_min + exit_margin_N; _start_reapproaches: single_leg)",
    "re-approach settings": "c2.py:1213-1301 (LiftedReapproachSettings: samples 1, single_leg True, exit_margin_N 5000, exit_samples 3, mode twist), R8 preset c2.py:1654-1663",
    "eps": "04_scripts/04_hydraulic/coupled/run_v5.py:708-721 (_install_approach_scale: delivered x (1 - eps) until any leg oil force > 3 kN)",
    "T4h name / offset key": "run_v5.py:668-687 (t4h_file_name), :724-737 (_case_of: twin offset_s)",
}
columns = {
    "u01_scan_ed6/ed7.csv": {
        "pair_union_s": {"def": "sum of the 1 ms intervals after the event start in which either leg of the event pair (event leg + its diagonal) has pad contact force <= 0", "code": "r67_g1_screen.py:323-326", "unit": "s", "window": "event start .. run end (12..60 s after the event)", "sign": "-", "relation": "gate U832_pair_union = pair_union_s <= 1.8"},
        "pair_last_touch_s": {"def": "end of the last such union interval, relative to the event start", "code": "r67_g1_screen.py:327", "unit": "s", "window": "same", "sign": "-", "relation": "gate U832_last_touch = <= 3.0"},
        "<leg>_first_s/_sum_s/_last_touch_s/_n/_max_gap_mm": {"def": "per-leg 1 ms lift intervals after the event (first start, total, last end, count, max pad gap)", "code": "r67_g1_screen.py:316-321", "unit": "s / - / mm", "window": "after the event", "sign": "-", "relation": "pair_union_s <= sum of the two pair legs' sum_s"},
        "reapproach_starts": {"def": "(t - t_ev, leg) of the controller events leg_reapproach_start", "code": "r67_g1_screen.py:357", "unit": "s", "window": "branch", "sign": "-", "relation": "-"},
        "offset_s": {"def": "event start = branch time (on the 0.1 s grid) + PRE_S 0.5 s + offset_s", "code": "verdict_runs.py:566", "unit": "s", "window": "-", "sign": "-", "relation": "phase phi = offset_s mod 0.1 s relative to the controller samples"},
    },
    "u11_periods.csv": {
        "load_<leg>_kN": {"def": "controller lower load estimate = cylinder_force_lower_N - seal band (C2Controller._load_estimate_N) at the period read", "code": "c2.py:5584-5588, logged by u10 patch of _update_lifted_reapproach", "unit": "kN", "window": "event - 0.25 .. + 2.5 s", "sign": "+ = compressive leg load", "relation": "start level = load_fraction_of_F_min x F_min; exit level = F_min + exit_margin_N = 14.415 kN"},
        "active": {"def": "active re-approach runs after the period: <leg>:<exit_samples_seen>[:rt = re-trigger]", "code": "c2.py:6286-6301, 6384-6397", "unit": "-", "window": "same", "sign": "-", "relation": "run ends when exit_samples_seen reaches 3"},
        "low_<leg>": {"def": "reapproach_low_counts after the period", "code": "c2.py:6331-6350", "unit": "count", "window": "same", "sign": "-", "relation": "reset while another leg is active (single_leg)"},
    },
    "u12_exit_window.csv": {
        "t_reload_s": {"def": "first 1 ms time after the event leg's first lift with r67 F column (pad contact - rod weight) >= exit level", "code": "u11_rerun_analysis.py (event_leg_reload_to_exit_level_s)", "unit": "s after t_ev", "window": "-", "sign": "-", "relation": "-"},
        "t_hold_end_s": {"def": "last 1 ms time before the event leg's second lift with F >= exit level", "code": "u12_exit_window.py", "unit": "s after t_ev", "window": "-", "sign": "-", "relation": "loaded window = [t_reload_s, t_hold_end_s]"},
        "samples_in_window": {"def": "controller sample times (t - t_ev) inside the loaded window", "code": "u12_exit_window.py", "unit": "s", "window": "-", "sign": "-", "relation": "3 samples needed for the event leg exit (exit_samples)"},
        "event_leg_exit_s / diag_start_s": {"def": "end of the event leg's run / start of the diagonal leg's run (u11 from the period log)", "code": "u11_rerun_analysis.py", "unit": "s after t_ev", "window": "-", "sign": "-", "relation": "equal in every run (single_leg hand-over on the same period)"},
        "diag_first_lift_end_s": {"def": "end of the diagonal leg's first 1 ms lift interval", "code": "u11_rerun_analysis.py", "unit": "s after t_ev", "window": "-", "sign": "-", "relation": "early hand-over = diag_start_s < diag_first_lift_end_s"},
    },
    "u05_eps_pairs.csv": {
        "same_sha": {"def": "commands_sha256 equal (bit alias)", "code": "u05_eps_alias.py", "unit": "-", "window": "-", "sign": "-", "relation": "-"},
        "same_times": {"def": "values.times t_check_start/t_touch_end/t_first_done/t_first_ready equal (10 Hz phase times)", "code": "u05_eps_alias.py", "unit": "-", "window": "-", "sign": "-", "relation": "discrete_alias = same_times and same event counts and same command_stats"},
    },
}
prov = {"created": "2026-11-26", "agent": "dynamics-expert",
        "code_worktree": {"path": str(WT), "head": head, "clean": status.strip() == ""},
        "inputs": {k: {"path": str(p), "sha256": sha(p)} for k, p in inputs.items()},
        "code_lines": code, "columns": columns,
        "rerun": {"script": "u10_instrumented_rerun.py", "env": "dynamics-dev via conda run, -I -B",
                  "workers": 8, "mask": "0xFFFF", "jobs": 25, "wall": "about 5 min",
                  "deterministic": "no seeded noise in these settings; VBM lines reproduce the stored commands_sha256"}}
(folder / "provenance.json").write_text(json.dumps(prov, indent=1), encoding="utf-8")
print("ok", head, "clean", status.strip() == "")
