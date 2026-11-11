"""H-SH: the 456 D-1 soil-group keys (= S-C, ``s2d_SC.jsonl``) with the LOC anchor shadow.

Record only (``loc_anchor_review.md`` 5.2 H-SH). Each job is ``run_v5.run_one`` of the
``d1_rows`` job (the preset as it is: ``final_C4G2_LAS_K1``, no candidate wrapper) in its own
spawned worker (``maxtasksperchild=1``, ``chunksize=1``) with ``loc_anchor_shadow`` installed.
The line keeps the identifying and margin fields of the ``run_v5`` line and adds
``loc_shadow`` and ``margins``.

Reference command hash per key (``las_p5r4_k1_rules.md`` BT-CR): the Y-Pa K1on line of
``las/k1/k1_YP.jsonl`` (165 keys) or else the ``soil_defer/s2d_SC.jsonl`` line (291 keys).
A line whose hash differs, or an error line, stops the batch (exit 1): the shadow must not
reach the commands, and errors are reported before anything else.

Margins (record, mm): ``stroke_guard_margin_mm = 682.8 - d1.stroke_max_m``; the crawler
clearance values the row's harness judged against 25 mm (``rut_ready_mm`` / ``rut_end_mm``
of P3-5, ``rut_clear_*`` of G6-5, ``clear_end_mm`` of E-6) and
``clearance_margin_mm = min(values) - 25``.

Usage (dynamics-dev python.exe, cwd = the checkout, PowerShell, ``OUTRIGGER_LOC_SHADOW=1``)::

    python -I -B 04_scripts/03_control/k2/loc_shadow/hsh_run.py --out <jsonl>
        [--workers 8] [--mask 0x0FFF0000] [--keys K1,K2 | --limit N] [--v5-dir <v5>]

Finished keys of ``--out`` are skipped (resume). Identity sidecar ``<out>.identity.json``.
Exit: 0 done, 1 a hash mismatch or an error line, 2 input error.
"""

from __future__ import annotations

import os

THREAD_VARIABLES = ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                    "NUMBA_NUM_THREADS")
for _name in THREAD_VARIABLES:  # before numpy loads, here and in every spawned worker
    os.environ[_name] = "1"
os.environ.setdefault("MKL_THREADING_LAYER", "TBB")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from multiprocessing import get_context  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
for _folder in (HERE, COUPLED_DIR, ROOT / "03_src"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import loc_anchor_shadow as shadow  # noqa: E402
import shadow_identity  # noqa: E402

MAIN_V5_DIR = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5")
SC_RELATIVE = Path("soil_defer") / "s2d_SC.jsonl"
YP_RELATIVE = Path("las") / "k1" / "k1_YP.jsonl"
SC_SHA256 = "70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa"
YP_SHA256 = "0d985d5624f0fbb0219ca50d1c839b7db639011d6c2ab14fa9d84cfd197fc2c3"
"""``las_p5r4_k1_rules.md`` appendix (Z-C reference files)."""
YP_REFERENCE_SUB_BUNDLE = "Y-Pa"
YP_REFERENCE_CANDIDATE = "K1on"
EXPECTED_KEYS = 456
EXPECTED_YP_KEYS = 165
STROKE_GUARD_MM = 682.8
CLEARANCE_MIN_MM = 25.0
CLEARANCE_FIELDS = ("rut_ready_mm", "rut_end_mm", "rut_clear_ready_mm", "rut_clear_end_mm",
                    "clear_end_mm")
"""Harness record fields of the 25 mm crawler clearance gates (P3-5, G6-5, E-6)."""
MAX_SEARCH_DEPTH = 6
KEPT_LINE_FIELDS = ("commands_sha256", "final_phase", "wall_s", "controller_tag",
                    "event_names", "harness_class", "t_event_s")
TOOL_FILES = {"hsh_run.py": HERE / "hsh_run.py",
              "loc_anchor_shadow.py": HERE / "loc_anchor_shadow.py"}
EXIT_DONE, EXIT_STOP, EXIT_INPUT = 0, 1, 2

_CAPTURE: dict = {}


# ------------------------------------------------------------------------------- reference
def _read_lines(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(text) for text in handle if text.strip()]


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference_hashes(v5_dir: Path) -> tuple[dict[str, str], dict[str, str]]:
    """(key -> reference hash, key -> source name) of the 456 keys.

    Raises:
        ValueError: A reference file is not the sealed one or the key counts differ.
    """
    sc_path, yp_path = v5_dir / SC_RELATIVE, v5_dir / YP_RELATIVE
    for path, expected in ((sc_path, SC_SHA256), (yp_path, YP_SHA256)):
        if _file_sha256(path) != expected:
            raise ValueError(f"{path}: sha256 is not {expected}")
    hashes = {row["d1"]["key"]: row["commands_sha256"] for row in _read_lines(sc_path)}
    sources = dict.fromkeys(hashes, "s2d_SC")
    yp_rows = [row for row in _read_lines(yp_path) if "k1" in row
               and row["k1"]["sub_bundle"] == YP_REFERENCE_SUB_BUNDLE
               and row["k1"]["k1_candidate"] == YP_REFERENCE_CANDIDATE]
    for row in yp_rows:
        hashes[row["k1"]["key"]] = row["commands_sha256"]
        sources[row["k1"]["key"]] = "k1_YP"
    if len(hashes) != EXPECTED_KEYS or len(yp_rows) != EXPECTED_YP_KEYS:
        raise ValueError(f"reference keys {len(hashes)} / Y-Pa {len(yp_rows)}, expected "
                         f"{EXPECTED_KEYS} / {EXPECTED_YP_KEYS}")
    return hashes, sources


def soil_group_jobs() -> list[dict]:
    """``d1_rows.jobs()`` of the S-C soil groups (``s2_defer_targeted.soil_group_jobs``)."""
    import d1_rows
    import s2_defer_judge

    return [job for job in d1_rows.jobs() if job["d1"]["group"] in s2_defer_judge.SOIL_GROUP_COUNTS]


def job_key(job: dict) -> str:
    """``las_targeted.composite_key`` of a D-1 job."""
    return f"{job['d1']['key']}|{job['setting']}|e{float(job['eps']):g}"


# ------------------------------------------------------------------------------- worker
def _capture_d1_record() -> None:
    """Keep the plant, controller and harness record ``d1_runs`` judges (worker only)."""
    import d1_runs

    original = d1_runs.d1_record

    def d1_record(row, setting_name, eps, result, plant, controller, harness):
        _CAPTURE.update(controller=controller, harness=harness)
        return original(row, setting_name, eps, result, plant, controller, harness)

    d1_runs.d1_record = d1_record


def clearance_values(record, depth: int = 0) -> dict[str, float]:
    """Every finite :data:`CLEARANCE_FIELDS` value in a nested harness record (path -> mm)."""
    found: dict[str, float] = {}
    if depth > MAX_SEARCH_DEPTH:
        return found
    items = record.items() if isinstance(record, dict) else []
    for name, value in items:
        if name in CLEARANCE_FIELDS and isinstance(value, int | float) and value == value:
            found[str(name)] = float(value)
        elif isinstance(value, dict):
            for inner, number in clearance_values(value, depth + 1).items():
                found[f"{name}.{inner}"] = number
    return found


def margins_of(d1: dict | None, harness: dict | None) -> dict:
    stroke_mm = None if not d1 or d1.get("stroke_max_m") is None else d1["stroke_max_m"] * 1e3
    values = clearance_values(harness or {})
    return {
        "stroke_max_mm": stroke_mm,
        "stroke_guard_margin_mm": None if stroke_mm is None else STROKE_GUARD_MM - stroke_mm,
        "clearance_values_mm": values,
        "clearance_margin_mm": min(values.values()) - CLEARANCE_MIN_MM if values else None,
    }


def _compact_d1(d1: dict | None) -> dict | None:
    if d1 is None:
        return None
    kept = ("key", "group", "path", "role", "setting", "eps", "verdict", "fail_items", "items",
            "stroke_max_m", "t_ready_s", "t_ready_limit_s", "harness_class")
    return {name: d1.get(name) for name in kept}


def run_shadow_job(job: dict) -> dict:
    """One job in a fresh worker: shadow installed, ``run_v5.run_one``, shadow and margins."""
    t_start = time.perf_counter()
    import run_v5

    shadow.install()
    _capture_d1_record()
    line = run_v5.run_one(job)
    out = {"key": job_key(job), "error": line.get("error"), "tb": line.get("tb"),
           **{name: line.get(name) for name in KEPT_LINE_FIELDS},
           "d1": _compact_d1(line.get("d1"))}
    controller = _CAPTURE.get("controller")
    out["loc_shadow"] = None if controller is None else shadow.record_of(controller)
    out["margins"] = margins_of(line.get("d1"), _CAPTURE.get("harness"))
    out["wall_total_s"] = round(time.perf_counter() - t_start, 1)
    if controller is None and out["error"] is None:
        out["error"] = "controller not captured"
    return out


# ------------------------------------------------------------------------------- batch
def _done_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {row["key"] for row in _read_lines(path) if not row.get("error")}


def _select(jobs: list[dict], keys: str | None, limit: int | None) -> list[dict]:
    if keys:
        wanted = set(keys.split(","))
        jobs = [job for job in jobs if job_key(job) in wanted]
    return jobs if limit is None else jobs[:limit]


def _print_line(count: int, total: int, row: dict, reference: str | None, elapsed_s: float) -> None:
    record = row.get("loc_shadow") or {}
    hash_text = "same" if row.get("commands_sha256") == reference else "DIFF"
    diff_text = f"[{record.get('diff_min_mm')}, {record.get('diff_max_mm')}]"
    print(f"[{count}/{total} {elapsed_s:.0f} s] {row['key']} {row.get('final_phase')} "
          f"hash {hash_text} paths {record.get('paths')} d {diff_text} err {row.get('error')}",
          flush=True)


def run_batch(todo: list[dict], out_path: Path, workers: int, hashes: dict[str, str]) -> int:
    """Run ``todo``; stop at the first error line or hash mismatch. Returns the exit code."""
    counts = {"lines": 0, "same": 0, "errors": 0, "mismatches": 0}
    t_start = time.perf_counter()
    context = get_context("spawn")
    pool = context.Pool(max(1, min(workers, len(todo))), maxtasksperchild=1)
    is_stopped = True  # until the loop ends normally (an exception also terminates the pool)
    try:
        with out_path.open("a", encoding="utf-8") as sink:
            for row in pool.imap_unordered(run_shadow_job, todo, chunksize=1):
                sink.write(json.dumps(row, default=float) + "\n")
                sink.flush()
                counts["lines"] += 1
                reference = hashes.get(row["key"])
                elapsed_s = time.perf_counter() - t_start
                _print_line(counts["lines"], len(todo), row, reference, elapsed_s)
                if row.get("error"):
                    counts["errors"] += 1
                elif row.get("commands_sha256") == reference:
                    counts["same"] += 1
                else:
                    counts["mismatches"] += 1
                if counts["errors"] or counts["mismatches"]:
                    print(f"STOP {json.dumps(counts)}", flush=True)
                    return EXIT_STOP
        is_stopped = False
    finally:
        if is_stopped:
            pool.terminate()
        else:
            pool.close()
        pool.join()
    print(f"done {json.dumps(counts)}", flush=True)
    return EXIT_DONE


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--mask", default=None, help="hex affinity of every worker (job mask)")
    parser.add_argument("--keys", default=None, help="comma-separated keys (trial)")
    parser.add_argument("--limit", type=int, default=None, help="first N keys (trial)")
    parser.add_argument("--v5-dir", type=Path, default=MAIN_V5_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not shadow.is_enabled():
        print(f"set {shadow.ENV_SWITCH}={shadow.ENV_ON}", file=sys.stderr)
        return EXIT_INPUT
    try:
        hashes, sources = reference_hashes(args.v5_dir)
    except (OSError, ValueError) as exc:
        print(f"reference: {exc}", file=sys.stderr)
        return EXIT_INPUT
    jobs = soil_group_jobs()
    if {job_key(job) for job in jobs} != set(hashes):
        print("the soil-group keys are not the reference keys", file=sys.stderr)
        return EXIT_INPUT
    mask = None if args.mask is None else int(args.mask, 16)
    jobs = [{**job, "mask": mask} if mask is not None else job for job in jobs]
    done = _done_keys(args.out)
    todo = [job for job in _select(jobs, args.keys, args.limit) if job_key(job) not in done]
    yp_count = sum(source == "k1_YP" for source in sources.values())
    print(f"keys {len(jobs)} (k1_YP {yp_count}), done {len(done)}, to run {len(todo)}, "
          f"workers {args.workers}", flush=True)
    sidecar = args.out.with_suffix(args.out.suffix + ".identity.json")
    start = shadow_identity.identity(ROOT, TOOL_FILES)
    shadow_identity.write_sidecar(sidecar, {"start": start, "end": None, "argv": sys.argv})
    code = run_batch(todo, args.out, args.workers, hashes) if todo else EXIT_DONE
    end = shadow_identity.identity(ROOT, TOOL_FILES)
    shadow_identity.write_sidecar(sidecar, {"start": start, "end": end, "argv": sys.argv,
                                            "exit": code})
    return code


if __name__ == "__main__":
    sys.exit(main())
