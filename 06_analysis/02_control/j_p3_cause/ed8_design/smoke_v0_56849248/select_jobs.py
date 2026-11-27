"""Pick two stored V0 R12 twin jobs of one (row, group) that differ only in offset_s.

Reads only the ``job`` of each line of the stored ``v5/main.jsonl`` (sha256 pinned) and the
condition V0 job form of the sealed held-out keys; writes ``jobs.json`` (the two jobs) and
prints the job key form only (no judged value).

Usage: python -I -B select_jobs.py <main checkout> <out jobs.json>
"""
import hashlib
import json
import sys
from pathlib import Path

MAIN_SHA256 = "9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e"
HELDOUT_SHA256 = "a18b5818734f1b10840c903fb9e4b5c140f619705048344f9ea48d16d3142ee5"
RUNTIME = ("mask", "t4h_dir")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    main_path = root / "06_analysis/03_hydraulic/coupled/v5/main.jsonl"
    keys_path = root / "06_analysis/02_control/j_p3_cause/ed8_design/keys_seal_41e107e9/heldout_g_ed8.json"
    if sha256(main_path) != MAIN_SHA256 or sha256(keys_path) != HELDOUT_SHA256:
        print(json.dumps({"status": "input_error", "reason": "sha256"}))
        return 2
    form = json.loads(keys_path.read_text(encoding="utf-8"))["lines"][0]["v0_pair"]["job"]
    form_keys = (sorted(form), sorted(form["twin"]))
    groups: dict[str, list[dict]] = {}
    with main_path.open(encoding="utf-8") as handle:
        for text in handle:
            job = json.loads(text).get("job") or {}
            twin = job.get("twin")
            if job.get("setting") != "V0" or job.get("case") != "R12" or not twin:
                continue
            job = {k: v for k, v in job.items() if k not in RUNTIME}
            key = json.dumps({k: v for k, v in job.items() if k != "offset_s"}, sort_keys=True)
            groups.setdefault(key, []).append(job)
    candidates = sorted((key, jobs) for key, jobs in groups.items() if len(jobs) >= 2)
    if not candidates:
        print(json.dumps({"status": "input_error", "reason": "no V0 R12 twin pair"}))
        return 2
    jobs = sorted(candidates[0][1], key=lambda job: job["offset_s"])[:2]
    out.write_text(json.dumps(jobs, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "written", "groups_with_pairs": len(candidates),
                      "job_keys": sorted(jobs[0]), "twin_keys": sorted(jobs[0]["twin"]),
                      "same_form_as_heldout_condition_v0": (sorted(jobs[0]), sorted(jobs[0]["twin"])) == form_keys,
                      "heldout_condition_job_keys": form_keys[0], "heldout_twin_keys": form_keys[1], "out": str(out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
