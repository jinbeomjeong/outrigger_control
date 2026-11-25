"""Checks of the sealed-candidate G1 key file (keys only, no result indicator).

Usage: python -I -B verify_g1.py <confirm_g1_grid171.json> <report.json>
"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(r"C:\workspace\outrigger_control")
CAUSE = REPO / "06_analysis/02_control/j_p3_cause"
D_BLOB = ("3ecf61f1:06_analysis/02_control/j_p3_cause/prelaunch_j9/run_records_ed6/"
          "d_grid_keys12.json")
U832 = {("bottom", "FL", 2.0), ("bottom", "FR", 2.0), ("bottom", "FR", 4.0)}
FL_FS4 = ("bottom", "FL", 4.0, "RE1bF", "ready")


def job_text(job):
    return json.dumps({k: v for k, v in job.items() if k != "setting"}, sort_keys=True)


def cluster(job):
    twin = job["twin"]
    return (twin["level"], twin["leg"], float(twin["fs_kN"]), twin["event"], twin["timing"])


def stored_run(pair, cache):
    path = REPO / pair["file"]
    if path not in cache:
        cache[path] = json.loads(path.read_text(encoding="utf-8"))
    result = next((r for r in cache[path]["results"] if r["key"] == pair["key"]), None)
    if result is None:
        return None
    runs = result["runs"]
    if isinstance(runs, dict):
        return runs.get(str(pair["run_id"]))
    index = int(pair["run_id"])
    return runs[index] if 0 <= index < len(runs) else None


def main():
    document = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    lines = document["lines"]
    d_doc = json.loads(subprocess.run(["git", "-C", str(REPO), "show", D_BLOB],
                                      capture_output=True, check=True).stdout)
    d_jobs = {job_text(entry["job"]) for entry in d_doc["jobs"]}
    ed6_grid = json.loads((CAUSE / "ed6_design/keys/confirm_b_grid192.json").read_text(
        encoding="utf-8"))
    ed6_jobs = {job_text(line["job"]) for line in ed6_grid["lines"]}
    probe = json.loads((CAUSE / "ed7_design/tool_6bfb2560/keys/probe_keys_ed7.json").read_text(
        encoding="utf-8"))
    probe_jobs = {job_text(line["job"]) for line in probe["lines"]}
    cache = {}
    hash_problems, pass_problems = [], []
    for line in lines:
        run = stored_run(line["v0_pair"], cache)
        name = line["t4h_file"]
        if run is None:
            hash_problems.append(f"{name}: no stored run")
            continue
        if run.get("commands_sha256") != line["v0_pair"]["v0_commands_sha256"]:
            hash_problems.append(f"{name}: hash differs")
        if run.get("pass") is not True:
            pass_problems.append(f"{name}: stored pass {run.get('pass')!r}")
    clusters = [cluster(line["job"]) for line in lines]
    not_counted = sorted(f"{c[0]}-{c[1]}-Fs{c[2]:g}-{c[3]}-{c[4]} o{line['job']['offset_s']:g}"
                         for c, line in zip(clusters, lines) if not line["counted_for_k"])
    fl_fs4 = [line for c, line in zip(clusters, lines) if c == FL_FS4]
    report = {
        "file": sys.argv[1], "seed": document["seed"], "lines": len(lines),
        "expected_lines": document["expected_lines"],
        "k_counted_lines": document["k_counted_lines"],
        "fault_jp3_judged_lines": document["fault_jp3_judged_lines"],
        "expected_j_p3_judged_rows": document["expected_j_p3_judged_rows"],
        "counted_for_k_true": sum(line["counted_for_k"] for line in lines),
        "judged_fault_jp3_true": sum(line["judged_fault_jp3"] for line in lines),
        "head_only_declared_true": sum(line["head_only_declared"] for line in lines),
        "not_counted_lines": not_counted,
        "not_counted_are_u832": all((c[0], c[1], c[2]) in U832 and c[3:] == ("RE1bF", "ready")
                                    for c, line in zip(clusters, lines)
                                    if not line["counted_for_k"]),
        "distinct_clusters": len(set(clusters)),
        "settings": dict(Counter(line["job"]["setting"] for line in lines)),
        "unique_t4h_files": len({line["t4h_file"] for line in lines}),
        "overlap_with_d12_keys": sum(job_text(line["job"]) in d_jobs for line in lines),
        "overlap_with_ed6_grid192": sum(job_text(line["job"]) in ed6_jobs for line in lines),
        "overlap_with_probe_keys": sum(job_text(line["job"]) in probe_jobs for line in lines),
        "d12_keys_in_ed6_grid192": sum(job in ed6_jobs for job in d_jobs),
        "v0_pair_hash_problems": hash_problems, "v0_pair_stored_pass_problems": pass_problems,
        "v0_pass_flags_true": sum(line["v0_pair"]["v0_pass"] is True for line in lines),
        "run_id_types": dict(Counter(type(line["v0_pair"]["run_id"]).__name__ for line in lines)),
        "fl_fs4_ready_lines": [{"t4h_file": line["t4h_file"], "offset_s": line["job"]["offset_s"],
                                "counted_for_k": line["counted_for_k"]} for line in fl_fs4],
        "code_identity": document["code_identity"],
        "generation_command": document["generation_command"],
    }
    Path(sys.argv[2]).write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
    problems = hash_problems or pass_problems or len(lines) != 171
    print(json.dumps({"status": "problems" if problems else "ok", "out": sys.argv[2]}))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
