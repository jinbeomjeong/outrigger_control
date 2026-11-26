"""Edition 8 S8-R step 0c: are the layer input keys present on the V0 pairs of the census rows?

Read only and value blind. For every census event row (C-J, C-S, C-D, C-G of spec 5.1) the
V0 pair line is located and the presence of the two layer input keys is counted:

- main.jsonl pairs (C-J, C-S): ``event_output.reapproach_starts`` and ``event_output.fast``
- stored grid runs (C-D, C-G): ``runs[int(run_id)].reapproach_starts`` and ``runs[...].fast``

Only presence, null, type (list / bool) and the number of empty start lists are counted.
No start time, start leg, ``fast`` value, pass flag or layer (E/N) is read into the output.
Key file sha256 digests are checked against the values quoted in the spec.

Usage: python -I -B layer_keys_0c.py <repo root> <out json>
Exit codes: 0 all event-row pairs found and all keys present, 1 a pair or key is missing or a
sha differs, 2 input error, 3 internal error.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import traceback
from collections import Counter
from pathlib import Path

MAIN_JSONL = "06_analysis/03_hydraulic/coupled/v5/main.jsonl"
MAIN_SHA_PREFIX = "9ad74990"
J9_MAIN = "06_analysis/02_control/j_p3_cause/j9_runs/8a2a52ce/j9main_a1/j9_main.jsonl"
SENS_KEYS = (
    "06_analysis/02_control/j_p3_cause/ed7_design/keys_seal_b46bdf8f/sens_keys_ed7.json",
    "be930b75a375877d07fc84fa98a9f8b0ee463f5b592319cfd6869fcc62a05b1b",
)
G1_KEYS = (
    "06_analysis/02_control/j_p3_cause/ed7_design/keys_seal_b46bdf8f/confirm_g1_grid171.json",
    "684054abb1ad05d8f82141f58eafdfa3c096edae1c05c9a4b9e8ae9ffe5b5dec",
)
GRID192_KEYS = "06_analysis/02_control/j_p3_cause/ed6_design/keys/confirm_b_grid192.json"
GRID192_SHA_PREFIX = "4e80e69b"
D_KEYS_REV = "3ecf61f1"
D_KEYS_PATH = "06_analysis/02_control/j_p3_cause/prelaunch_j9/run_records_ed6/d_grid_keys12.json"
D_KEYS_SHA = "a995abff9d73816f58a0e3d67a59f18b3e60fb006fe48d824012b79b57d87981"

EVENT_CASES = ("R12", "R14", "R15", "R16")
"""``verdict_cases`` cases with an ``EventTwin`` (R13 has none unless decided; not in census)."""
IGNORED_JOB_FIELDS = ("setting", "mask", "t4h_dir")
STARTS_KEY = "reapproach_starts"
FAST_KEY = "fast"
EXPECTED_ROWS = {"C-J": 388, "C-S": 460, "C-D": 12, "C-G": 171}


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plain_job_key(job: dict) -> str:
    """Job identity without the setting and the runtime-only fields."""
    return json.dumps({k: v for k, v in job.items() if k not in IGNORED_JOB_FIELDS},
                      sort_keys=True)


def is_event_job(job: dict) -> bool:
    return job.get("case") in EVENT_CASES


def count_key(container: dict, key: str, expected_type: type, counts: Counter, label: str) -> None:
    """Count presence, null and type of ``container[key]`` without reading the value out."""
    if key not in container:
        counts[f"{label}_absent"] += 1
        return
    value = container[key]
    if value is None:
        counts[f"{label}_null"] += 1
        return
    if not isinstance(value, expected_type):
        counts[f"{label}_wrong_type"] += 1
        return
    counts[f"{label}_present"] += 1
    if expected_type is list and not value:
        counts[f"{label}_empty_list"] += 1


def count_pair_keys(container: dict | None, counts: Counter) -> None:
    if not isinstance(container, dict):
        counts["pair_container_absent"] += 1
        return
    count_key(container, STARTS_KEY, list, counts, STARTS_KEY)
    count_key(container, FAST_KEY, bool, counts, FAST_KEY)


class MainV0:
    """V0 lines of the stored main.jsonl, indexed by plain job key."""

    def __init__(self, root: Path) -> None:
        data = (root / MAIN_JSONL).read_bytes()
        self.sha256 = sha256_of(data)
        self.lines_by_key: dict[str, list[dict]] = {}
        for raw in data.decode("utf-8").splitlines():
            if not raw.strip():
                continue
            line = json.loads(raw)
            job = line.get("job") or {}
            if job.get("setting") != "V0":
                continue
            self.lines_by_key.setdefault(plain_job_key(job), []).append(line)

    def find(self, job: dict) -> tuple[str, dict | None]:
        matches = self.lines_by_key.get(plain_job_key(job), [])
        if len(matches) != 1:
            return f"main_v0_matches_{len(matches)}", None
        if "error" in matches[0]:
            return "main_v0_error_line", None
        return "ok", matches[0]


class GridStore:
    """Stored V0 grid files (``results[*].runs[*]``), loaded once each."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: dict[str, dict] = {}
        self.file_sha256: dict[str, str] = {}

    def find(self, pair: dict, counts: Counter) -> tuple[str, dict | None]:
        name = pair.get("file")
        if not isinstance(name, str):
            return "pair_without_file", None
        if name not in self.files:
            path = self.root / name
            if not path.exists():
                return "grid_file_missing", None
            data = path.read_bytes()
            self.file_sha256[name] = sha256_of(data)
            self.files[name] = json.loads(data)
        stored_results = self.files[name].get("results", [])
        results = [r for r in stored_results if r.get("key") == pair.get("key")]
        if len(results) != 1:
            return f"grid_result_matches_{len(results)}", None
        run_id = pair.get("run_id")
        counts[f"run_id_type:{type(run_id).__name__}"] += 1
        try:
            run_index = int(run_id)  # spec 5.1: G1 stores run_id as text
        except (TypeError, ValueError):
            return "run_id_not_integer", None
        runs = results[0].get("runs", [])
        if not 0 <= run_index < len(runs):
            return "run_id_out_of_range", None
        run = runs[run_index]
        expected = pair.get("v0_commands_sha256")
        if expected is None:
            counts["pair_without_v0_commands_sha256"] += 1
        elif run.get("commands_sha256") != expected:
            return "grid_run_hash_differs", None
        return "ok", run


def stage_summary(rows: int, counts: Counter) -> dict:
    return {"rows": rows, "counts": dict(sorted(counts.items()))}


def check_c_j(root: Path, main_v0: MainV0) -> tuple[dict, str]:
    data = (root / J9_MAIN).read_bytes()
    counts: Counter = Counter()
    distinct_pairs: set[str] = set()
    rows = 0
    for raw in data.decode("utf-8").splitlines():
        if not raw.strip():
            continue
        rows += 1
        job = json.loads(raw)["job"]
        counts[f"setting:{job.get('setting')}"] += 1
        if not is_event_job(job):
            counts["steady_rows"] += 1
            continue
        counts["event_rows"] += 1
        status, line = main_v0.find(job)
        counts[f"pair:{status}"] += 1
        if line is None:
            continue
        distinct_pairs.add(plain_job_key(job))
        count_pair_keys(line.get("event_output"), counts)
    summary = stage_summary(rows, counts)
    summary["distinct_v0_pairs_of_event_rows"] = len(distinct_pairs)
    return summary, sha256_of(data)


def check_c_s(root: Path, main_v0: MainV0) -> tuple[dict, str]:
    rel, _ = SENS_KEYS
    data = (root / rel).read_bytes()
    counts: Counter = Counter()
    distinct_pairs: set[str] = set()
    lines = json.loads(data)["lines"]
    for line in lines:
        pair = line["v0_pair"]
        counts[f"pair_source:{pair.get('source')}"] += 1
        if not is_event_job(pair["job"]):
            counts["steady_rows"] += 1
            continue
        counts["event_rows"] += 1
        status, v0_line = main_v0.find(pair["job"])
        counts[f"pair:{status}"] += 1
        if v0_line is None:
            continue
        distinct_pairs.add(plain_job_key(pair["job"]))
        count_pair_keys(v0_line.get("event_output"), counts)
    summary = stage_summary(len(lines), counts)
    summary["distinct_v0_pairs_of_event_rows"] = len(distinct_pairs)
    return summary, sha256_of(data)


def check_grid_lines(lines: list[dict], store: GridStore, counts: Counter) -> set[str]:
    distinct_pairs: set[str] = set()
    for line in lines:
        job = line["job"]
        counts[f"case:{job.get('case')}"] += 1
        counts["event_rows" if is_event_job(job) else "steady_rows"] += 1
        status, run = store.find(line["v0_pair"], counts)
        counts[f"pair:{status}"] += 1
        if run is None:
            continue
        distinct_pairs.add(json.dumps(line["v0_pair"], sort_keys=True))
        counts[f"grid_run_has_event_output:{'event_output' in run}"] += 1
        count_pair_keys(run, counts)
    return distinct_pairs


def read_blob(root: Path, rev: str, rel: str) -> bytes:
    completed = subprocess.run(["git", "-C", str(root), "show", f"{rev}:{rel}"],
                               capture_output=True, check=True, timeout=60,
                               stdin=subprocess.DEVNULL)
    return completed.stdout


def check_c_d(root: Path, store: GridStore) -> tuple[dict, str, str]:
    d_data = read_blob(root, D_KEYS_REV, D_KEYS_PATH)
    grid_data = (root / GRID192_KEYS).read_bytes()
    grid_lines = json.loads(grid_data)["lines"]
    grid_by_job: dict[str, list[dict]] = {}
    for line in grid_lines:
        grid_by_job.setdefault(plain_job_key(line["job"]), []).append(line)
    counts: Counter = Counter()
    matched: list[dict] = []
    d_jobs = json.loads(d_data)["jobs"]
    for entry in d_jobs:
        found = grid_by_job.get(plain_job_key(entry["job"]), [])
        counts[f"grid192_line_matches:{len(found)}"] += 1
        if len(found) == 1:
            matched.append(found[0])
    distinct = check_grid_lines(matched, store, counts)
    summary = stage_summary(len(d_jobs), counts)
    summary["census_rows"] = 2 * len(d_jobs)
    summary["census_rows_note"] = "12 D keys x {VBN, VBNslow}; both settings share one V0 pair"
    summary["distinct_v0_pairs"] = len(distinct)
    return summary, sha256_of(d_data), sha256_of(grid_data)


def check_c_g(root: Path, store: GridStore) -> tuple[dict, str]:
    rel, _ = G1_KEYS
    data = (root / rel).read_bytes()
    lines = json.loads(data)["lines"]
    counts: Counter = Counter()
    distinct = check_grid_lines(lines, store, counts)
    summary = stage_summary(len(lines), counts)
    summary["distinct_v0_pairs"] = len(distinct)
    return summary, sha256_of(data)


def sha_table(main_v0: MainV0, digests: dict[str, str]) -> dict:
    return {
        "main.jsonl": {"sha256": main_v0.sha256, "spec": f"{MAIN_SHA_PREFIX}... (prefix)",
                       "match": main_v0.sha256.startswith(MAIN_SHA_PREFIX)},
        "j9_main.jsonl": {"sha256": digests["j9_main"], "spec": None, "match": None},
        "sens_keys_ed7.json": {"sha256": digests["sens"], "spec": SENS_KEYS[1],
                               "match": digests["sens"] == SENS_KEYS[1]},
        "d_grid_keys12.json (git blob)": {"sha256": digests["d"], "spec": D_KEYS_SHA,
                                          "match": digests["d"] == D_KEYS_SHA},
        "confirm_g1_grid171.json": {"sha256": digests["g1"], "spec": G1_KEYS[1],
                                    "match": digests["g1"] == G1_KEYS[1]},
        "confirm_b_grid192.json": {"sha256": digests["grid192"],
                                   "spec": f"{GRID192_SHA_PREFIX}... (prefix)",
                                   "match": digests["grid192"].startswith(GRID192_SHA_PREFIX)},
    }


def is_complete(stage: dict) -> bool:
    counts = stage["counts"]
    event_rows = counts.get("event_rows", 0)
    if event_rows == 0:
        return False  # an empty selection is not a pass
    return (counts.get("pair:ok", 0) == event_rows
            and counts.get(f"{STARTS_KEY}_present", 0) == event_rows
            and counts.get(f"{FAST_KEY}_present", 0) == event_rows)


def run(root: Path, out: Path) -> int:
    main_v0 = MainV0(root)
    store = GridStore(root)
    stage_j, sha_j9 = check_c_j(root, main_v0)
    stage_s, sha_sens = check_c_s(root, main_v0)
    stage_d, sha_d, sha_grid192 = check_c_d(root, store)
    stage_g, sha_g1 = check_c_g(root, store)
    stages = {"C-J": stage_j, "C-S": stage_s, "C-D": stage_d, "C-G": stage_g}
    for name, stage in stages.items():
        stage["rows_expected"] = EXPECTED_ROWS[name]
        stage["rows_match_expected"] = stage["rows"] == EXPECTED_ROWS[name]
        stage["all_event_pairs_have_both_keys"] = is_complete(stage)
    shas = sha_table(main_v0, {"j9_main": sha_j9, "sens": sha_sens, "d": sha_d,
                               "g1": sha_g1, "grid192": sha_grid192})
    result = {"inputs_sha256": shas, "grid_files_sha256": dict(sorted(store.file_sha256.items())),
              "stages": stages}
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    shas_ok = all(entry["match"] is not False for entry in shas.values())
    complete = all(stage["all_event_pairs_have_both_keys"] for stage in stages.values())
    rows_ok = all(stage["rows_match_expected"] for stage in stages.values())
    status = "ok" if shas_ok and complete and rows_ok else "findings"
    print(json.dumps({"status": status, "shas_ok": shas_ok, "rows_ok": rows_ok,
                      "keys_complete": complete, "out": str(out)}))
    return 0 if status == "ok" else 1


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"status": "input_error", "error": "usage: <repo root> <out json>"}))
        return 2
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    if out.exists():
        print(json.dumps({"status": "input_error", "error": f"refusing to overwrite {out}"}))
        return 2
    try:
        return run(root, out)
    except (OSError, subprocess.CalledProcessError) as error:
        print(json.dumps({"status": "input_error", "error": str(error)}))
        return 2
    except Exception:  # noqa: BLE001 - any other failure is a tool defect (exit 3)
        traceback.print_exc()
        print(json.dumps({"status": "internal_error"}))
        return 3


if __name__ == "__main__":
    sys.exit(main())
