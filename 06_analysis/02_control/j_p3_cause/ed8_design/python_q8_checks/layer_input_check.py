"""Q8-11: is ``reapproach_starts`` present on the V0 pair lines of the edition 8 layer rule?

Read only. Prints and writes key presence, types and counts; never a value of a start list
(no times, no legs, no pass flags).

Usage: python -I -B layer_input_check.py <main checkout root> <out json>
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

MAIN_JSONL = "06_analysis/03_hydraulic/coupled/v5/main.jsonl"
MAIN_SHA_PREFIX = "9ad74990"
KEY_FILES = {
    "confirm_b_grid192": ("06_analysis/02_control/j_p3_cause/ed6_design/keys/confirm_b_grid192.json",
                          "4e80e69bd2233b994853ae3f60ed0749f2c39c7dbb6390bc012b016efa5cf85b"),
    "confirm_g1_grid171": ("06_analysis/02_control/j_p3_cause/ed7_design/keys_seal_b46bdf8f/"
                           "confirm_g1_grid171.json",
                           "684054abb1ad05d8f82141f58eafdfa3c096edae1c05c9a4b9e8ae9ffe5b5dec"),
    "sens_keys_ed7": ("06_analysis/02_control/j_p3_cause/ed7_design/keys_seal_b46bdf8f/"
                      "sens_keys_ed7.json",
                      "be930b75a375877d07fc84fa98a9f8b0ee463f5b592319cfd6869fcc62a05b1b"),
}
D_KEYS_BLOB = ("3ecf61f1", "06_analysis/02_control/j_p3_cause/prelaunch_j9/run_records_ed6/"
                           "d_grid_keys12.json",
               "a995abff9d73816f58a0e3d67a59f18b3e60fb006fe48d824012b79b57d87981")
RUNTIME_JOB_KEYS = ("mask", "t4h_dir")
EVENT_CASES = ("R12", "R14", "R15", "R16")
"""``verdict_cases`` cases with an ``EventTwin`` (R13 has no twin)."""
START_KEY = "reapproach_starts"


def job_key(job: dict) -> str:
    """``run_v5.job_key`` (same form, copied to stay read only)."""
    return json.dumps({k: job[k] for k in sorted(job) if k not in RUNTIME_JOB_KEYS},
                      sort_keys=True)


def starts_shape(value) -> str:
    """Structure class of a start list, without its values."""
    if not isinstance(value, list):
        return f"not_list:{type(value).__name__}"
    for item in value:
        if not (isinstance(item, list) and len(item) == 2
                and isinstance(item[0], (int, float)) and isinstance(item[1], str)):
            return "list_with_other_items"
    return "list_of_[number,str]"


def is_event_job(job: dict) -> bool:
    return job.get("case") in EVENT_CASES


def check_main(root: Path) -> tuple[dict, dict[str, dict]]:
    path = root / MAIN_JSONL
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    v0_by_key: dict[str, dict] = {}
    counts: Counter = Counter()
    for raw in data.decode("utf-8").splitlines():
        line = json.loads(raw)
        counts["lines"] += 1
        job = line.get("job") or {}
        if job.get("setting") != "V0":
            continue
        counts["v0_lines"] += 1
        if "error" in line:
            counts["v0_error_lines"] += 1
            continue
        key = job_key(job)
        if key in v0_by_key:
            counts["v0_duplicate_keys"] += 1
        v0_by_key[key] = line
        kind = "event" if is_event_job(job) else "steady"
        output = line.get("event_output")
        counts[f"v0_{kind}_lines"] += 1
        if not isinstance(output, dict) or not output:
            counts[f"v0_{kind}_event_output_empty_or_absent"] += 1
            continue
        if START_KEY not in output:
            counts[f"v0_{kind}_event_output_without_{START_KEY}"] += 1
            continue
        counts[f"v0_{kind}_with_{START_KEY}"] += 1
        counts[f"v0_{kind}_{START_KEY}_shape:{starts_shape(output[START_KEY])}"] += 1
    by_case = Counter(json.loads(k).get("case") for k in v0_by_key)
    summary = {"path": MAIN_JSONL, "sha256": digest,
               "sha256_prefix_ok": digest.startswith(MAIN_SHA_PREFIX),
               "counts": dict(sorted(counts.items())),
               "v0_keys_by_case": dict(sorted(by_case.items()))}
    return summary, v0_by_key


class GridStore:
    """Stored V0 grid files (r67 screen form ``results[*].runs[*]``), loaded once each."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: dict[str, dict] = {}

    def run(self, pair: dict) -> tuple[str, dict | None]:
        name = pair["file"]
        if name not in self.files:
            path = self.root / name
            if not path.exists():
                return "file_missing", None
            self.files[name] = json.loads(path.read_text(encoding="utf-8"))
        stored = self.files[name]
        result = next((r for r in stored.get("results", []) if r.get("key") == pair["key"]),
                      None)
        run_id = pair.get("run_id")
        if isinstance(run_id, str) and run_id.isdigit():  # some key files store it as text
            run_id = int(run_id)
        if result is None or not isinstance(run_id, int) or run_id >= len(result.get("runs", [])):
            return "run_missing", None
        run = result["runs"][run_id]
        expected = pair.get("v0_commands_sha256")
        if expected is not None and run.get("commands_sha256") != expected:
            return "hash_differs", run
        return "ok", run


def check_pair(pair, store: GridStore, v0_by_key: dict[str, dict], counts: Counter) -> None:
    if not isinstance(pair, dict):
        counts["v0_pair_absent"] += 1
        return
    if "file" in pair:
        counts["v0_pair_grid_file"] += 1
        counts[f"v0_pair_run_id_type:{type(pair.get('run_id')).__name__}"] += 1
        status, run = store.run(pair)
        counts[f"grid_run_{status}"] += 1
        if run is None:
            return
        counts[f"grid_run_top_level_{START_KEY}:{START_KEY in run}"] += 1
        counts[f"grid_run_has_event_output:{'event_output' in run}"] += 1
        if START_KEY in run:
            counts[f"grid_run_{START_KEY}_shape:{starts_shape(run[START_KEY])}"] += 1
        return
    if "job" in pair:
        counts["v0_pair_main_job"] += 1
        line = v0_by_key.get(job_key(pair["job"]))
        if line is None:
            counts["main_v0_line_missing"] += 1
            return
        output = line.get("event_output") or {}
        kind = "event" if is_event_job(pair["job"]) else "steady"
        counts[f"main_{kind}_pair_has_{START_KEY}:{START_KEY in output}"] += 1
        return
    counts[f"v0_pair_other_fields:{','.join(sorted(pair))}"] += 1


def key_lines(document) -> list[dict]:
    if isinstance(document, dict) and isinstance(document.get("lines"), list):
        return document["lines"]
    if isinstance(document, list):
        return document
    return []


def check_key_file(name: str, data: bytes, expected_sha: str, store: GridStore,
                   v0_by_key: dict[str, dict]) -> dict:
    digest = hashlib.sha256(data).hexdigest()
    document = json.loads(data)
    lines = key_lines(document)
    counts: Counter = Counter()
    field_sets: Counter = Counter()
    for line in lines:
        counts["lines"] += 1
        field_sets[",".join(sorted(line))] += 1
        pair = line.get("v0_pair")
        if isinstance(pair, dict):
            field_sets["v0_pair:" + ",".join(sorted(pair))] += 1
        check_pair(pair, store, v0_by_key, counts)
    return {"name": name, "sha256_ok": digest == expected_sha,
            "top_level_keys": sorted(document) if isinstance(document, dict) else "list",
            "line_field_sets": dict(field_sets), "counts": dict(sorted(counts.items()))}


def read_blob(root: Path, rev: str, rel: str) -> bytes:
    completed = subprocess.run(["git", "-C", str(root), "show", f"{rev}:{rel}"],
                               capture_output=True, check=True, timeout=60)
    return completed.stdout


def main() -> int:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    main_summary, v0_by_key = check_main(root)
    store = GridStore(root)
    files = {}
    for name, (rel, sha) in KEY_FILES.items():
        files[name] = check_key_file(name, (root / rel).read_bytes(), sha, store, v0_by_key)
    rev, rel, sha = D_KEYS_BLOB
    files["d_grid_keys12"] = check_key_file("d_grid_keys12", read_blob(root, rev, rel), sha,
                                            store, v0_by_key)
    result = {"main_jsonl": main_summary, "key_files": files,
              "grid_files_loaded": sorted(store.files)}
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({"main_counts": main_summary["counts"],
                      "key_file_counts": {k: v["counts"] for k, v in files.items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
