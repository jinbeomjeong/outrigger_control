"""Three V0 event jobs with an explicit twin event and timing (RE1bF, FS24, G4), each a stored
grid condition at offset 0.0 (``confirm_b_grid192.json`` jobs, sha256 pinned) - never a G'
slot: the script first asserts that no job is one of the 1356 jobs of ``heldout_g_ed8.json``
(sha256 pinned). The RE1bF job carries the default shape explicitly (``depth_m`` 0.030,
``ramp_s`` 0.05). Writes ``jobs.json``; prints key forms only.

Usage: python -I -B make_jobs.py <main checkout> <out jobs.json>
"""
import hashlib
import json
import sys
from pathlib import Path

GRID_SHA256 = "4e80e69bd2233b994853ae3f60ed0749f2c39c7dbb6390bc012b016efa5cf85b"
HELDOUT_SHA256 = "a18b5818734f1b10840c903fb9e4b5c140f619705048344f9ea48d16d3142ee5"
EVENTS = ("RE1bF", "FS24", "G4")
RUNTIME = ("mask", "t4h_dir")
RE1BF_SHAPE = {"depth_m": 0.030, "ramp_s": 0.05}


def key_of(job: dict) -> str:
    return json.dumps({k: v for k, v in job.items() if k not in RUNTIME}, sort_keys=True)


def main() -> int:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    jp3 = root / "06_analysis/02_control/j_p3_cause"
    grid = jp3 / "ed6_design/keys/confirm_b_grid192.json"
    heldout = jp3 / "ed8_design/keys_seal_41e107e9/heldout_g_ed8.json"
    for path, sha in ((grid, GRID_SHA256), (heldout, HELDOUT_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            print(json.dumps({"status": "input_error", "reason": f"{path.name} sha256"}))
            return 2
    heldout_run, heldout_keys = set(), set()  # the 1356 stage 5 jobs; every key-file job
    for line in json.loads(heldout.read_text(encoding="utf-8"))["lines"]:
        heldout_run.update(key_of(job) for job in [line["v0_pair"]["job"], *line["aa_order"][:3]])
        heldout_keys.update(key_of(job) for job in [line["v0_pair"]["job"], *line["aa_order"]])
        heldout_keys.add(key_of(line["job"]))  # the VBN job too (another setting, never equal)
    assert len(heldout_run) == 1356, len(heldout_run)
    candidates = {event: [] for event in EVENTS}
    for line in json.loads(grid.read_text(encoding="utf-8"))["lines"]:
        job = {k: v for k, v in line["job"].items() if k not in RUNTIME}
        twin = job.get("twin") or {}
        if twin.get("event") in candidates and "timing" in twin and job.get("offset_s") == 0.0:
            candidates[twin["event"]].append({**job, "setting": "V0"})
    jobs = []
    for event in EVENTS:
        if not candidates[event]:
            print(json.dumps({"status": "input_error", "reason": f"no stored {event} o0.0"}))
            return 2
        job = sorted(candidates[event], key=key_of)[0]
        if event == "RE1bF":
            job = {**job, "twin": {**job["twin"], **RE1BF_SHAPE}}
        jobs.append(job)
    clash = [job["twin"]["event"] for job in jobs
             if key_of(job) in heldout_keys or key_of(job) in heldout_run]
    assert not clash, f"jobs in the held-out keys: {clash}"
    out.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "written", "jobs": len(jobs),
                      "events": [job["twin"]["event"] for job in jobs],
                      "twin_keys": [sorted(job["twin"]) for job in jobs],
                      "in_heldout_keys": 0, "heldout_stage5_jobs_checked": len(heldout_run),
                      "heldout_key_file_jobs_checked": len(heldout_keys),
                      "out": str(out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
