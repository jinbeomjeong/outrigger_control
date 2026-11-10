"""D8x judge, path 1 (``06_analysis/02_control/d8x/d8x_rules.md`` 8 and 9.2 item 4, with
``d8x_rules_rev1.md`` 9.2 item 4 and ``d8x_rules_rev2.md`` 7). Reads the raw results; never
runs a simulation.

Sub-commands:
  points        write ``d8x_points.json`` from the rules tables in force (rev1 1.2), or
                ``--check`` an existing file against them (I-3)
  manifest      run-path files F of a bundle and their git blob ids at a commit (2.2)
  prelaunch     run-start record ``d8x_prelaunch_<bundle>.json`` (I-1, I-3, I-5)
  expect-file   path 2's ``--expect`` file ``d8x_expect_k1.json`` from the rev3 1 tag table
  judge-g0      G0 gate: the 60 evaluations recomputed in ``d8x_g0_rev3.json`` (rev3 4, reuse 0;
                closure blobs vs ``--at-commit``), rev1 4.3 / 5.0, rev2 3 scope
  (G1, rev4 1.1: both K1 arms are judged rows; W and FLAG (i) / (ii) stay on the K1-off arm;
  V-2 counts LAS-b over both arms, user decision 2026-11-10)
  judge-ra      R-a rows (J1 .. J11, E-1 .. E-8), files ``ra_off.json`` + ``ra_on.json``
  judge-rc      R-c rows, files ``hrx_off.jsonl`` + ``hrx_on.jsonl``
  judge-chrono  Chrono rows from ``verify_*.json`` + ``r8_series.npz`` (4.4)
  invariance    V-1 (K1 hash pairs), V-2 (LAS-b activity), V-3 (VB - V0 J1)
  select-w      worst point W (5.1 with the rev1 eligibility) -> ``d8x_selection.json``
  select-v      F_s 8 floor V from the first-order Chrono judgement (5.2)
  report        gates G-S .. G3 and the grade (10) from the outputs above

Common contract: ``--out <file>`` (report), ``--format json|md``; exit 0 pass, 1 fail,
2 not judgeable / input error (a missing result key is 2), 3 internal error; the last stdout
line is JSON. Both rules files must match their sealed sha256 (exit 2 otherwise).
Run with the project interpreter (dynamics-dev for the harness files; python-dev is enough for
everything but ``manifest --python`` / ``prelaunch``, which call the run interpreter).
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import d8x_spec as spec  # noqa: E402

ROOT = spec.ROOT
EXIT_PASS, EXIT_FAIL, EXIT_NOT_JUDGEABLE, EXIT_INTERNAL = 0, 1, 2, 3
NAN_TOLERANCE = 1e-9
ANGLE_TOLERANCE_HARNESS_DEG = 1e-9
ANGLE_TOLERANCE_CHRONO_DEG = 1e-4
READY_CROSS_CHECK_S = 0.1 + 1e-6


class NotJudgeable(Exception):
    """Input error or a rules E-* / I-* condition that makes the judgement impossible."""


# ----------------------------------------------------------------------------------- helpers
def _load_json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise NotJudgeable(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise NotJudgeable(f"{path}: not JSON ({exc})") from exc


def _load_jsonl(path: Path) -> list[dict]:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise NotJudgeable(f"file not found: {path}") from exc
    return [json.loads(line) for line in lines if line.strip()]


def _git(*args: str) -> str:
    completed = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                               encoding="utf-8", timeout=120, check=False)
    if completed.returncode != 0:
        raise NotJudgeable(f"git {' '.join(args)}: {completed.stderr.strip()}")
    return completed.stdout


def f_d8_N() -> float:
    """F_D8 = YAML ``control.F_min_cylinder_N`` + 5 kN (rules header)."""
    import yaml

    params = yaml.safe_load(spec.PARAMS_PATH.read_text(encoding="utf-8"))
    return float(params["control"]["F_min_cylinder_N"]) + spec.GUARD_EXTRA_N


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _event_names(events) -> list[str]:
    """Names of ``[t, name]`` pairs or ``C2Event(t_s=.., name='..')`` strings."""
    names = []
    for event in events or []:
        if isinstance(event, (list, tuple)):
            names.append(str(event[1]))
        elif isinstance(event, str) and "name='" in event:
            names.append(event.split("name='", 1)[1].rsplit("'", 1)[0])
        else:
            names.append(str(event))
    return names


def _angles_match(values, reference, tolerance_deg: float) -> bool:
    """Two (roll, pitch) pairs equal within the tolerance; a missing or short pair is not."""
    if not isinstance(values, (list, tuple)) or len(values) != 2:
        return False
    return all(_is_number(value) and abs(value - expected) <= tolerance_deg
               for value, expected in zip(values, reference, strict=True))


def _prefix(name: str) -> str:
    return name.split(":")[0]


def event_counts(names: list[str]) -> dict:
    """Event families of rules 4.1 J7 .. J9, E-3, V-1 and V-2."""
    stroke = [n for n in names if n.startswith(spec.STROKE_EVENTS)]
    faults = [n for n in names if n.startswith("FAULT_") and n not in stroke]
    warns = [n for n in names if n.startswith("WARN_") and n not in stroke
             and _prefix(n) not in spec.WARN_ALLOWED]
    return {"J7_stroke_events": stroke, "J8_fault_events": faults, "J9_warn_events": warns,
            "E3_rejections": [n for n in names if n.startswith("REJ_")],
            "liftoff_slow_count": sum(_prefix(n) == spec.LIFTOFF_SLOW_EVENT for n in names),
            "soil_events": [n for n in names if _prefix(n) in spec.SOIL_EVENTS]}


# ------------------------------------------------------------------------------ row judgement
FIELD_MAP_HARNESS = {
    "J1": "d8x.J1_min_cyl_after_lift_N (1 ms chunk / sub-step min of true F_cyl from the earlier "
          "of the first crawler load zero and the LOC event) >= F_D8",
    "J2": "d8x.J2_min_cyl_reanchor_N (in reanchor_started .. end event) >= F_D8; only rows with "
          "an H4 interval",
    "J3": "d8x.J3_pad_lift_samples (F_cyl + rod weight <= 0 after the TOUCH end) == 0",
    "J4": "d8x.J4_att_max_after_ready_deg (true deck attitude from the first READY) <= 0.2",
    "J5": "d8x.t_ready_s <= 120",
    "J6": "d8x.J6_max_moving_bar <= 210 (R-a: the harness max_pressure_bar of every step)",
    "J7": "d8x.events FAULT_STROKE_END / WARN_LIFT_STROKE_LIMITED / FAULT_LIFT_STROKE_LIMIT*",
    "J8": "d8x.events other FAULT_*",
    "J9": "d8x.events WARN_* outside WARN_PROBE_STIFFNESS_OUT_OF_RANGE",
    "J11": "R-a: run.fails (rcc.metrics); R-c: d1.fail_items (d1_runs judgement)",
    "E-2": "d8x.t_touch_s, d8x.t_lift_s, d8x.t_ready_s present",
    "E-3": "d8x.events REJ_* == 0",
    "E-8": "d8x.J1_window_s >= 1 s (else not judgeable)",
}
REQUIRED_D8X_KEYS = ("t_touch_s", "t_lift_s", "t_ready_s", "J1_min_cyl_after_lift_N",
                     "J1_window_s", "reanchor_intervals_s", "J2_min_cyl_reanchor_N",
                     "J3_pad_lift_samples", "J4_att_max_after_ready_deg", "J6_max_moving_bar",
                     "events")


def _at_least(value, limit: float) -> bool:
    return _is_number(value) and value >= limit


def _at_most(value, limit: float) -> bool:
    return _is_number(value) and value <= limit


def judge_metrics(d8x: dict, fails: list | None, f_d8: float) -> dict:
    """J1 .. J9, J11, E-2, E-3, E-7, E-8 of one harness row (rules 4.1, 6).

    Raises:
        NotJudgeable: A required key is missing (exit 2 for the caller).
    """
    missing = [key for key in REQUIRED_D8X_KEYS if key not in d8x]
    if missing:
        raise NotJudgeable(f"d8x keys missing: {missing}")
    counts = event_counts(_event_names(d8x["events"]))
    has_h4 = bool(d8x["reanchor_intervals_s"])
    items = {
        "J1": _at_least(d8x["J1_min_cyl_after_lift_N"], f_d8),
        "J3": d8x["J3_pad_lift_samples"] == 0,
        "J4": _at_most(d8x["J4_att_max_after_ready_deg"], spec.ATTITUDE_LIMIT_DEG),
        "J5": _at_most(d8x["t_ready_s"], spec.READY_LIMIT_S),
        "J6": _at_most(d8x["J6_max_moving_bar"], spec.MOVING_LIMIT_BAR),
        "J7": not counts["J7_stroke_events"], "J8": not counts["J8_fault_events"],
        "J9": not counts["J9_warn_events"], "J11": fails is not None and not fails,
        "E-2": all(d8x[key] is not None for key in ("t_touch_s", "t_lift_s", "t_ready_s")),
        "E-3": not counts["E3_rejections"],
    }
    if has_h4:
        items["J2"] = _at_least(d8x["J2_min_cyl_reanchor_N"], f_d8)
    window = d8x["J1_window_s"]
    not_judgeable = [] if not _is_number(window) or window >= spec.LIFT_WINDOW_MIN_S else [
        f"E-8 lift-off window {window:.3f} s < 1 s"]
    return {"items": items, "fail_items": sorted(k for k, ok in items.items() if not ok),
            "not_judgeable": not_judgeable, "counts": counts,
            "values": {"J1_N": d8x["J1_min_cyl_after_lift_N"],
                       "J2_N": d8x["J2_min_cyl_reanchor_N"] if has_h4 else None,
                       "J4_deg": d8x["J4_att_max_after_ready_deg"], "t_ready_s": d8x["t_ready_s"],
                       "J6_bar": d8x["J6_max_moving_bar"], "stroke_max_m": d8x.get("stroke_max_m")}}


def _tag_problems(tag, expected_tag: str, is_las_on, is_k1_on: bool) -> list[str]:
    """Rev3 3.1 E-6a / b / c / e / f for one row (E-6d, the gate record, is the caller's).

    ``is_k1_on``: the row's K1 arm is on (Chrono rows: True, they run the preset).
    """
    problems = []
    if tag != expected_tag:
        problems.append(f"E-6a tag {tag} != {expected_tag}")
    is_las_tag = spec.is_liftoff_slow_tag(tag)
    if not is_las_tag:
        problems.append(f"E-6b tag {tag} is not a LAS-b tag")
    if spec.is_order_gate_tag(tag) is not is_k1_on:
        problems.append(f"E-6c tag {tag}: K1 suffix {spec.is_order_gate_tag(tag)} != arm "
                        f"{'on' if is_k1_on else 'off'}")
    if is_las_on is not True:
        problems.append(f"E-6e LAS-b record {is_las_on!r}, must be on")
    if tag in spec.LAS_OFF_TAGS:
        problems.append(f"E-6f tag {tag} is a LAS-b off tag")
    return problems


def _verdict(judged: dict) -> str:
    if judged["not_judgeable"]:
        return "not_judgeable"
    return "pass" if not judged["fail_items"] else "fail"


def _summarise(rows: list[dict], expected: int, label: str) -> dict:
    counts = {"pass": 0, "fail": 0, "not_judgeable": 0}
    for row in rows:
        counts[row["verdict"]] += 1
    return {"bundle": label, "expected": expected, "actual": len(rows), **counts}


def _status_of(summaries: list[dict], *, problems: list[str]) -> int:
    if problems or any(s["expected"] != s["actual"] or s["not_judgeable"] for s in summaries):
        return EXIT_NOT_JUDGEABLE
    return EXIT_FAIL if any(s["fail"] for s in summaries) else EXIT_PASS


# --------------------------------------------------------------------------------- points
def cmd_points(args) -> tuple[int, dict]:
    doc = spec.build_points()
    problems = spec.point_table_problems(doc)
    path = Path(args.points_file)
    if args.check:
        stored = _load_json(path)
        same = json.dumps(stored, sort_keys=True) == json.dumps(doc, sort_keys=True)
        if not same:
            problems.append(f"{path} differs from the rules tables in force (I-3)")
        return (EXIT_FAIL if problems else EXIT_PASS), {"points_file": str(path), "I-3": same,
                                                       "problems": problems}
    if problems:
        return EXIT_FAIL, {"problems": problems}
    path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    return EXIT_PASS, {"points_file": str(path), "rules_rev": doc["rules_rev"],
                       "ra_points": len(doc["ra_points"]), "rpx_points": len(doc["rpx_points"]),
                       "axis_vertices": len(doc["axis_vertices"]),
                       "table_sources": doc["table_sources"]}


def _points(args) -> dict:
    doc = _load_json(Path(args.points_file))
    if doc.get("rules_rev") != spec.CURRENT_RULES_REV:
        raise NotJudgeable(f"point file rules_rev {doc.get('rules_rev')!r}, expected "
                           f"{spec.CURRENT_RULES_REV!r}")
    fresh = spec.build_points()
    if json.dumps(doc, sort_keys=True) != json.dumps(fresh, sort_keys=True):
        raise NotJudgeable("point file differs from the rules tables in force (I-3)")
    return doc


# ------------------------------------------------------------------------------- manifest
BUNDLE_PATTERNS = {
    "common": ("03_src/outrigger_sim/**/*.py", "02_params/rexome33.yaml"),
    "ra": ("04_scripts/03_control/touch_phase/acceptance/acc_d8.py",
           "04_scripts/03_control/touch_phase/acceptance/acc_common.py",
           "04_scripts/03_control/r8d1/c2py_r8d1_closed_loop.py",
           "04_scripts/03_control/r8d1/r8d1_td.py", "04_scripts/03_control/r8d1/r8d1_td2.py",
           "04_scripts/01_dynamics/run_s6_slope_boundary_check.py",
           "04_scripts/01_dynamics/run_mast_flex_c2_check.py",
           "04_scripts/01_dynamics/run_pad_tangential_check.py",
           "04_scripts/01_dynamics/run_control_comparison.py",
           "04_scripts/03_control/run_c2_timedomain.py", "04_scripts/01_dynamics/dyn_model.py"),
    "rc": ("04_scripts/04_hydraulic/coupled/d1_rows.py",
           "04_scripts/04_hydraulic/coupled/d1_runs.py",
           "04_scripts/04_hydraulic/coupled/run_v5.py"),
    "C": ("04_scripts/02_chrono/run_S6C.py", "04_scripts/02_chrono/run_S8C.py",
          "04_scripts/02_chrono/s6_stage2.py", "04_scripts/02_chrono/s9_batch.py",
          "03_src/outrigger_sim/chrono/**/*.py"),
    "judge": ("04_scripts/03_control/d8x/*.py",),
}
"""Rules 2.2 table (patterns); the import closure and the recorded module lists close it."""


def _match(path: str, pattern: str) -> bool:
    from fnmatch import fnmatch

    if "**" in pattern:
        head, tail = pattern.split("**/", 1)
        return path.startswith(head) and fnmatch(path.rsplit("/", 1)[-1], tail)
    return fnmatch(path, pattern) and path.count("/") == pattern.count("/")


def tree_blobs(commit: str) -> dict[str, str]:
    """path -> blob id of every file at ``commit`` (``git ls-tree -r``)."""
    out = {}
    for line in _git("ls-tree", "-r", commit).splitlines():
        meta, path = line.split("\t", 1)
        _, kind, blob = meta.split()
        if kind == "blob":
            out[path] = blob
    return out


def _import_closure(python: str, bundle: str) -> dict:
    script = HERE / "d8x_record.py"
    completed = subprocess.run([python, "-I", "-B", str(script), "import-closure", "--bundle",
                                bundle], capture_output=True, text=True, encoding="utf-8",
                               cwd=str(ROOT), timeout=900, check=False)
    lines = [line for line in completed.stdout.splitlines() if line.startswith("{")]
    if completed.returncode != 0 or not lines:
        raise NotJudgeable(f"import closure {bundle} with {python} failed: "
                           f"{completed.stderr.strip()[-800:]}")
    return json.loads(lines[-1])


def _recorded_module_files(paths: list[Path]) -> set[str]:
    files: set[str] = set()
    for path in paths:
        if str(path).endswith(".jsonl"):
            for line in _load_jsonl(path):
                files.update(((line.get("d1") or {}).get("d8x") or {}).get("module_files") or [])
        else:
            for listed in ((_load_json(path).get("meta") or {}).get("d8x") or {}).get(
                    "module_files_by_sha256", {}).values():
                files.update(listed)
    return files


def build_manifest(bundles: list[str], commit: str, python: str | None,
                   results: list[Path]) -> dict:
    blobs = tree_blobs(commit)
    patterns = [p for b in ("common", *bundles) for p in BUNDLE_PATTERNS[b]]
    files = {path for path in blobs for pattern in patterns if _match(path, pattern)}
    closure = {}
    if python:
        for bundle in bundles:
            if bundle in ("ra", "rc", "C"):
                closure[bundle] = _import_closure(python, bundle)
                files.update(closure[bundle]["files"])
    recorded = _recorded_module_files(results)
    files.update(recorded)
    absent = sorted(path for path in files if path not in blobs)
    return {"commit": _git("rev-parse", commit).strip(), "bundles": bundles,
            "files": {path: blobs[path] for path in sorted(files) if path in blobs},
            "not_in_commit": absent,
            "closure_errors": {b: c.get("errors") for b, c in closure.items() if c.get("errors")},
            "recorded_module_files": len(recorded)}


def cmd_manifest(args) -> tuple[int, dict]:
    bundles = ["ra", "rc", "C", "judge"] if args.bundle == "all" else [args.bundle]
    manifest = build_manifest(bundles, args.commit, args.python, [Path(p) for p in args.results])
    if args.compare:
        other = _load_json(Path(args.compare))["files"]
        keys = sorted(set(other) | set(manifest["files"]))
        manifest["differences"] = {k: [other.get(k), manifest["files"].get(k)] for k in keys
                                   if other.get(k) != manifest["files"].get(k)}
    problems = manifest["not_in_commit"] or manifest["closure_errors"]
    status = EXIT_NOT_JUDGEABLE if problems else (
        EXIT_FAIL if manifest.get("differences") else EXIT_PASS)
    return status, manifest


# ------------------------------------------------------------------------------ prelaunch
def _interpreter(python: str) -> dict:
    completed = subprocess.run([python, "-I", "-c", "import platform, sys; "
                                "print(sys.executable, platform.python_version())"],
                               capture_output=True, text=True, timeout=120, check=False)
    executable, _, version = completed.stdout.strip().rpartition(" ")
    return {"python": executable or python, "python_version": version}


def cmd_prelaunch(args) -> tuple[int, dict]:
    points = _points(args)
    status_text = _git("status", "--porcelain", "--untracked-files=no").strip()
    head = _git("rev-parse", "HEAD").strip()
    bundles = {"ra": ["ra"], "rc": ["rc"], "C": ["C"]}[args.bundle]
    record = {
        "bundle": args.bundle, "head": head, "status_porcelain": status_text,
        "is_clean": status_text == "", "rules": spec.seal_report(),
        "points": {"file": str(args.points_file), "rules_rev": points["rules_rev"], "I-3": True},
        "manifest": build_manifest(bundles + ["judge"], "HEAD", args.python, []),
        "interpreter": _interpreter(args.python),
        "threads_expected": {"MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                             "NUMBA_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                             "MKL_THREADING_LAYER": "TBB"},
        "affinity_mask": args.mask, "k1": args.k1,
    }
    if args.bundle in ("ra", "rc") and args.k1 is None:
        raise NotJudgeable("prelaunch --bundle ra / rc needs --k1 off|on (rev3 2)")
    if args.bundle == "ra":
        preset_tag = args.expected_tag or spec.DEFAULT_TAGS["ra"]
        record.update(expected_tag=preset_tag,
                      expected_tags={"ra": dict(spec.EXPECTED_TAGS["ra"])},  # rev3 1
                      expected_arm_tag=spec.arm_tag(preset_tag, args.k1),
                      expected_count=spec.EXPECTED_COUNTS[f"ra_{args.k1}"])
    elif args.bundle == "rc":
        record.update(expected_tags={s: dict(spec.EXPECTED_TAGS[s]) for s in spec.RC_SETTINGS},
                      expected_arm_tags={s: spec.EXPECTED_TAGS[s][args.k1]
                                         for s in spec.RC_SETTINGS},
                      expected_count=spec.EXPECTED_COUNTS[f"rc_{args.k1}"])
    else:
        record.update(_chrono_prelaunch(args))
    out = Path(args.record_out or spec.D8X_DIR / f"d8x_prelaunch_{args.bundle}.json")
    out.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    problems = [] if record["is_clean"] else ["I-1: the checkout is not clean"]
    problems += record["manifest"]["not_in_commit"]
    return (EXIT_FAIL if problems else EXIT_PASS), {"record": str(out), "head": head,
                                                   "problems": problems}


def _chrono_prelaunch(args) -> dict:
    if not (args.expected_tag and args.start_states and args.threads):
        raise NotJudgeable("prelaunch --bundle C needs --expected-tag, --start-states, --threads")
    selection = _load_json(Path(args.selection)) if args.selection else {}
    rows = spec.chrono_rows(selection.get("W", {}).get("chrono_floor"),
                            selection.get("V", {}).get("floor"))
    return {"expected_tag": args.expected_tag, "rows": rows,
            "expected_count": spec.EXPECTED_COUNTS["C"],
            "start_states": _load_json(Path(args.start_states)), "threads": args.threads,
            "pool": "P", "selection": selection}


# ------------------------------------------------------------------------------ expect-file
def cmd_expect_file(args) -> tuple[int, dict]:
    """Rev3 3.3: write path 2's ``--expect`` file from the rev3 1 table (before any result)."""
    import hashlib

    doc = spec.path2_expect_doc()
    out = Path(args.expect_out)
    out.write_bytes((json.dumps(doc, indent=1) + "\n").encode("utf-8"))
    return EXIT_PASS, {"expect_file": str(out), "sha256": hashlib.sha256(
        out.read_bytes()).hexdigest(), "content": doc}


# --------------------------------------------------------------------------------- judge-g0
def _git_object(ref: str) -> tuple[dict, str]:
    """JSON content and blob id of ``<commit>:<path>`` or of a working file."""
    if ":" in ref and not Path(ref).exists():
        return json.loads(_git("show", ref)), _git("rev-parse", ref).strip()
    path = Path(ref)
    blob = _git("hash-object", str(path)).strip()
    return _load_json(path), blob


def _g0_rows(doc: dict) -> dict[tuple[str, str], dict]:
    return {(row["level"], row["tag"]): row for row in doc.get("rows", [])}


def _g0_source_problems(doc: dict, at_commit: str) -> tuple[list[str], dict]:
    """Rev3 4: a recompute of all 60 (reuse 0) from a clean checkout, and the closure blobs it
    recorded equal those at ``at_commit`` (H_impl or M; a difference = recompute at M)."""
    meta = doc.get("meta") or {}
    summary = doc.get("summary") or {}
    problems = []
    if meta.get("rules_rev") != spec.G0_REV3_RULES_REV:
        problems.append(f"G0 meta.rules_rev {meta.get('rules_rev')!r} != "
                        f"{spec.G0_REV3_RULES_REV!r} (rev3 4)")
    if meta.get("reuse") != 0 or summary.get("reused") != 0:
        problems.append(f"G0 reuse {meta.get('reuse')} / {summary.get('reused')} != 0 (rev3 4)")
    if meta.get("recompute") != spec.EXPECTED_COUNTS["G0"]:
        problems.append(f"G0 recompute {meta.get('recompute')} != 60 (rev3 4)")
    if not meta.get("run_commit"):
        problems.append("G0 meta.run_commit missing (rev3 4)")
    if meta.get("clean") is not True:
        problems.append("G0 run not from a clean checkout (I-1: status at start / end)")
    recorded = ((meta.get("closure") or {}).get("files")) or {}
    if not recorded:
        problems.append("G0 meta.closure.files missing (rev3 4)")
    reference = tree_blobs(at_commit) if recorded else {}
    differences = {name: [blob, reference.get(name)] for name, blob in recorded.items()
                   if reference.get(name) != blob}
    if differences:
        problems.append(f"G0 closure blobs differ at {at_commit} ({len(differences)} files): "
                        "recompute the 60 at that commit (rev3 4)")
    closure = {"at_commit": at_commit, "run_commit": meta.get("run_commit"),
               "compared": len(recorded), "differences": differences, "ok": not differences}
    return problems, closure


def _g0_4(row: dict, threshold: float) -> dict:
    g04 = (row.get("G0") or {}).get("G0-4") or {}
    floor_hat = g04.get("floor_hat_deg")
    errors = g04.get("err_deg")
    if floor_hat is None or errors is None:
        return {"pass": None, "reason": "G0-4 floor_hat_deg / err_deg missing"}
    rv_hat = spec.verification_usage(*floor_hat)
    max_error = max(abs(e) for e in errors)
    return {"Rv_hat_rev1": rv_hat, "max_err_deg": max_error, "threshold": threshold,
            "pass": rv_hat <= threshold and max_error <= spec.G0_4_ERROR_MAX_DEG}


def cmd_judge_g0(args) -> tuple[int, dict]:
    """Rev3 4 / 5: the 60 evaluations of one recompute file (``d8x_g0_rev3.json``, reuse 0)."""
    points = _points(args)
    doc, blob = _git_object(args.g0)
    problems, closure = _g0_source_problems(doc, args.at_commit)
    rows = _g0_rows(doc)
    angles = spec.points_by_name(points)
    evaluations = []
    for level in spec.LEVELS:
        for tag in points["g0_points"]:
            row = rows.get((level, tag))
            if row is None:
                problems.append(f"G0 row {level}|{tag} missing in {args.g0}")
                continue
            evaluations.append(_g0_evaluation(row, level, tag, angles[tag], problems))
    failed = [e["key"] for e in evaluations if not e["pass"]]
    if len(evaluations) != spec.EXPECTED_COUNTS["G0"]:
        problems.append(f"G0 evaluations {len(evaluations)} != 60")
    status = EXIT_NOT_JUDGEABLE if problems else (EXIT_FAIL if failed else EXIT_PASS)
    return status, {"gate_G0": {0: "pass", 1: "fail", 2: "not_judgeable"}[status],
                    "g0": {"ref": args.g0, "blob": blob}, "closure": closure,
                    "compare_rev1": (doc.get("meta") or {}).get("compare_rev1"),
                    "evaluations": evaluations, "failed": failed,
                    "w_eligibility": _w_eligibility(points, rows), "problems": problems,
                    "count": len(evaluations)}


def _g0_evaluation(row, level, tag, angles, problems) -> dict:
    floor = row.get("floor_deg")
    if not _angles_match(floor, angles, ANGLE_TOLERANCE_HARNESS_DEG):
        problems.append(f"G0 {level}|{tag}: floor {floor} != point {list(angles)}")
    g0 = row.get("G0") or {}
    items = {name: bool((g0.get(name) or {}).get("pass")) for name in ("G0-1", "G0-2", "G0-3")}
    judged_g04 = tag in spec.G0_4_JUDGED[level]
    g04 = _g0_4(row, spec.G0_4_RV_HAT_MAX)
    if judged_g04:
        items["G0-4"] = bool(g04["pass"])
    return {"key": f"{level}|{tag}", "source": row.get("source", "recomputed"),
            "items": items, "pass": all(items.values()), "G0-4": g04, "G0-4_judged": judged_g04,
            "G0-1_margin_mm": (g0.get("G0-1") or {}).get("margin_mm")}


def _w_eligibility(points: dict, rows: dict) -> dict:
    """Rev2 3: W eligibility by the true R_v (point file) <= 1.01; the rev1 for_level R_v hat
    (d45 1.01, others 1.005) of the top G0 row of the rev3 file is kept as a record."""
    true_usage = {entry["tag"]: entry["R_v"] for entry in points["ra_points"]}
    out = {}
    for candidate in points["w_candidates"]:
        tag = candidate["ra_point"]
        row = rows.get(("top", tag))
        threshold = spec.G0_4_RV_HAT_MAX_D45 if tag.startswith("d45") else spec.G0_4_RV_HAT_MAX
        record = None if row is None else _g0_4(row, threshold)
        out[tag] = {"pass": true_usage[tag] <= spec.W_TRUE_RV_MAX, "R_v_true": true_usage[tag],
                    "threshold": spec.W_TRUE_RV_MAX, "for_level_record": record}
    return out


# ------------------------------------------------------------------------------ judge-ra/rc
def _expected_tag(prelaunch: Path | None, fallback: str) -> str:
    return _load_json(prelaunch).get("expected_tag", fallback) if prelaunch else fallback


def judge_ra_file(path: Path, k1: str, points: dict, f_d8: float, expected_tag: str) -> dict:
    doc = _load_json(path)
    run_meta = (doc.get("meta") or {}).get("d8x") or {}
    stages = tuple(run_meta.get("stages") or ())
    wanted = ("main", "robust", "kt") if k1 == "off" else ("main",)
    problems = [] if stages == wanted else [f"{path.name}: stages {stages} != {wanted}"]
    if run_meta.get("k1") != k1:  # rev3 E-6d: the request recorded = the arm
        problems.append(f"{path.name}: meta.d8x.k1 {run_meta.get('k1')!r} != {k1!r} (E-6d)")
    arm_tag = spec.arm_tag(expected_tag, k1)
    problems += _tag_histogram_problems(path.name, [r.get("controller_tag")
                                                    for r in doc.get("runs", [])], {arm_tag})
    expected_ids = spec.expected_ra_ids(points, wanted)
    angles = spec.points_by_name(points)
    rows, seen = [], set()
    for run in doc.get("runs", []):
        rows.append(_judge_ra_run(run, k1, angles, f_d8, arm_tag, seen, problems))
    extra = sorted(seen - set(expected_ids))
    absent = sorted(set(expected_ids) - seen)
    if extra or absent:
        problems.append(f"{path.name}: ids outside the set {extra[:5]}, absent {absent[:5]} (E-5)")
    summary = _summarise(rows, spec.EXPECTED_COUNTS[f"ra_{k1}"], f"ra_{k1}")
    return {"summary": summary, "rows": rows, "problems": problems}


def _tag_histogram_problems(label: str, tags: list, allowed: set[str]) -> list[str]:
    """Rev3 3.2: a bundle file holds only the rev3 1 tags of its arm (errors carry no tag)."""
    histogram: dict[str, int] = {}
    for tag in tags:
        if tag is not None:
            histogram[str(tag)] = histogram.get(str(tag), 0) + 1
    other = {tag: n for tag, n in histogram.items() if tag not in allowed}
    if not other:
        return []
    return [f"{label}: tags outside rev3 1 {sorted(allowed)}: {other} (rev3 3.2)"]


def _judge_ra_run(run, k1, angles, f_d8, expected_tag, seen, problems) -> dict:
    """One R-a run; ``expected_tag`` is the arm's tag (rev3 1)."""
    run_id = run.get("id")
    if run_id in seen:
        problems.append(f"duplicate id {run_id} (E-5)")
    seen.add(run_id)
    if "error" in run:
        return {"id": run_id, "verdict": "not_judgeable", "reason": run["error"][:200]}
    reasons = []
    point = run.get("point")
    if point not in angles or not _angles_match(run.get("angles_deg"), angles[point],
                                                ANGLE_TOLERANCE_HARNESS_DEG):
        reasons.append("E-5 angles differ from the point file")
    reasons += _tag_problems(run.get("controller_tag"), expected_tag,
                             run.get("liftoff_slow_enabled"), k1 == "on")
    # E-6d effective gate: catches an off arm that ran the preset (gate on since the K1 switch)
    if run.get("k1_order_gate") is not (k1 == "on"):
        reasons.append(f"E-6d K1 gate record {run.get('k1_order_gate')} != {k1}")
    try:
        judged = judge_metrics(run.get("d8x") or {}, run.get("fails"), f_d8)
    except NotJudgeable as exc:
        return {"id": run_id, "verdict": "not_judgeable", "reason": str(exc)}
    judged["not_judgeable"] += reasons
    return {"id": run_id, "point": point, "level": run.get("level"), "mast": run.get("mast"),
            "stage": run.get("stage"), "variant": run.get("variant"), "k1": k1,
            "commands_sha256": run.get("commands_sha256"), "verdict": _verdict(judged),
            **{k: judged[k] for k in ("fail_items", "not_judgeable", "values")},
            "liftoff_slow_count": judged["counts"]["liftoff_slow_count"]}


def cmd_judge_ra(args) -> tuple[int, dict]:
    points = _points(args)
    f_d8 = f_d8_N()
    tag = _expected_tag(Path(args.prelaunch) if args.prelaunch else None, spec.DEFAULT_TAGS["ra"])
    parts = {k1: judge_ra_file(Path(path), k1, points, f_d8, tag)
             for k1, path in (("off", args.off), ("on", args.on))}
    return _bundle_result(parts, "ra")


def _bundle_result(parts: dict, label: str) -> tuple[int, dict]:
    """Rev4 1.1 (F-1): G1 judges both K1 arms (R-a 910 + 192, R-c 192 + 96); a ``fail`` in the
    K1-on arm fails the bundle like one in the off arm. ``k1_rows_failed`` stays a separate list
    so the judgement can set it against path 2 ``k1_rows_fail`` (rev4 1.4, manual check)."""
    summaries = [part["summary"] for part in parts.values()]
    problems = [p for part in parts.values() for p in part["problems"]]
    status = _status_of([parts["off"]["summary"], parts["on"]["summary"]], problems=problems)
    id_key = "id" if label == "ra" else "key"
    return status, {"bundle": label, "field_map": FIELD_MAP_HARNESS, "summaries": summaries,
                    "gate_rows_off": parts["off"]["summary"],
                    "gate_rows_on": parts["on"]["summary"],
                    "g1_scope": "rev4 1.1: both K1 arms",
                    "k1_rows_failed": [r[id_key] for r in parts["on"]["rows"]
                                       if r["verdict"] == "fail"],
                    "problems": problems,
                    "rows": [r for part in parts.values() for r in part["rows"]]}


def judge_rc_file(path: Path, k1: str, points: dict, f_d8: float) -> dict:
    lines = _load_jsonl(path)
    expected = spec.expected_rc_keys(points, k1)
    angles = spec.points_by_name(points)
    rows, seen = [], set()
    allowed = {spec.EXPECTED_TAGS[setting][k1] for setting in spec.RC_SETTINGS}
    problems = _tag_histogram_problems(path.name, [line.get("controller_tag") for line in lines
                                                   if "error" not in line], allowed)
    for line in lines:
        rows.append(_judge_rc_line(line, k1, angles, f_d8, seen, problems))
    extra = sorted(seen - set(expected))
    absent = sorted(set(expected) - seen)
    if extra or absent:
        problems.append(f"{path.name}: keys outside the set {extra[:5]}, absent {absent[:5]} (E-5)")
    return {"summary": _summarise(rows, spec.EXPECTED_COUNTS[f"rc_{k1}"], f"rc_{k1}"),
            "rows": rows, "problems": problems}


def _rc_key(line: dict) -> str:
    job = line.get("job") or {}
    row = job.get("d1") or {}
    return f"{row.get('key')}|{job.get('setting')}|e{float(job.get('eps', 0.0)):g}"


def _judge_rc_line(line, k1, angles, f_d8, seen, problems) -> dict:
    key = _rc_key(line)
    if key in seen:
        problems.append(f"duplicate key {key} (E-5)")
    seen.add(key)
    if "error" in line:
        return {"key": key, "verdict": "not_judgeable", "reason": str(line["error"])[:200]}
    job = line["job"]
    setting = job["setting"]
    d1 = line.get("d1") or {}
    d8x = d1.get("d8x") or {}
    reasons = []
    floor = job["d1"].get("slope_name")
    row_angles = [job["d1"].get("roll_deg"), job["d1"].get("pitch_deg")]
    if floor not in angles or not _angles_match(row_angles, angles[floor],
                                                ANGLE_TOLERANCE_HARNESS_DEG):
        reasons.append("E-5 angles differ from the point file")
    reasons += _tag_problems(line.get("controller_tag"), spec.EXPECTED_TAGS[setting][k1],
                             d8x.get("liftoff_slow_enabled"), k1 == "on")
    # E-6d request and effective gate: catches an off arm that ran the preset (gate on since
    # the K1 switch)
    if job.get("k1") != k1 or d8x.get("k1_order_gate") is not (k1 == "on"):
        reasons.append(f"E-6d K1 job {job.get('k1')} / gate {d8x.get('k1_order_gate')} != {k1}")
    try:
        judged = judge_metrics(d8x, d1.get("fail_items"), f_d8)
    except NotJudgeable as exc:
        return {"key": key, "verdict": "not_judgeable", "reason": str(exc)}
    judged["not_judgeable"] += reasons
    return {"key": key, "floor": floor, "level": job["d1"].get("level"),
            "crawler_k_scale": job["d1"].get("crawler_k_scale"), "setting": setting,
            "eps": job.get("eps"), "k1": k1, "commands_sha256": line.get("commands_sha256"),
            "verdict": _verdict(judged),
            **{k: judged[k] for k in ("fail_items", "not_judgeable", "values")},
            "liftoff_slow_count": judged["counts"]["liftoff_slow_count"]}


def cmd_judge_rc(args) -> tuple[int, dict]:
    points = _points(args)
    f_d8 = f_d8_N()
    parts = {k1: judge_rc_file(Path(path), k1, points, f_d8)
             for k1, path in (("off", args.off), ("on", args.on))}
    return _bundle_result(parts, "rc")


# ---------------------------------------------------------------------------- judge-chrono
CHRONO_FIELDS = {
    "J1_kN": ("min_cyl_after_liftoff_kN", "min_cyl_after_liftoff"),
    "J2_kN": ("min_cyl_reanchor_kN",),
    "J3_pad_min_kN": ("pad_N_min_after_liftoff_kN",),
    "J4_deg": ("att_err_after_ready_maxabs_deg",),
    "J6_moving_bar": ("max_moving_pressure_bar",),
    "J6_locked": ("max_pressure_by_variable",),
    "J10_recontacts": ("crawler_recontact_after_loc_count",),
    "events": ("events",),
    "times": ("times_s",),
    "slope_limit_mode": ("result.d8x.slope_limit_mode", "result.acceptance.slope_limit_mode"),
    "floor_true_deg": ("result.d8x.floor_true_deg", "floor_true_deg"),
    "half_spans_deg": ("result.d8x.half_spans_deg",),
    "row_number": ("result.d8x.row",),
    "controller_tag": ("result.d8x.controller_tag",),
    # rev3 2 / E-6d (cad-expert adds the d8x key; missing = not judgeable)
    "k1_order_gate": ("result.d8x.k1_order_gate",),
    "controller_meta_order_gate": (
        "result.controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate",
        "result.d8x.controller_meta_order_gate"),
    "liftoff_slow": ("result.d8x.liftoff_slow_enabled", "result.d8x.las_b",
                     "result.d8x.liftoff_approach_slow"),
    "settle_map": ("result.d8x.settle_map", "result.acceptance.controller_settle_map",
                   "result.settings.s7c.controller_settle_map"),
    "scenario_group": ("result.d8x.scenario_group", "result.d8x.scenario.group",
                       "result.settings.group"),
    "scenario_id": ("result.d8x.scenario_id", "result.d8x.scenario.id",
                    "result.settings.case_id"),
    "level": ("result.d8x.level", "level"),
    "beta_GPa": ("result.d8x.beta_GPa", "bundle_c.beta_GPa"),
    "fs_kN": ("result.d8x.fs_kN", "fs_kN_plant", "result.settings.s8.fs_kN",
              "result.settings.fs_kN"),
}
"""Rules 4.1 item -> key (first found) in the verify-json metrics of the case, ``result.*`` =
its ``result.json`` (the cad ``d8x`` block, I-4 / E-4 / E-6). J1 is read from the metrics
(choice (a): ``s6_bundle_c.D8_FLOORS`` is not extended, so no earlier row changes). J2 is needed
only for an H4 row, J6 locked only when present, F_s only for an L2b row; any other key
missing = not judgeable (exit 2)."""
OPTIONAL_CHRONO = ("J2_kN", "J6_locked", "fs_kN", "scenario_id")


def _lookup(entry: dict, dotted: str):
    value = entry
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return None, False
        value = value[part]
    return value, True


def chrono_fields(entry: dict) -> tuple[dict, list[str]]:
    values, missing = {}, []
    for field, candidates in CHRONO_FIELDS.items():
        for candidate in candidates:
            value, found = _lookup(entry, candidate)
            if found:
                values[field] = value
                break
        else:
            if field not in OPTIONAL_CHRONO:
                missing.append(f"{field} ({'/'.join(candidates)})")
    return values, missing


def _r8_series(case_dir: Path) -> dict:
    import numpy as np

    path = case_dir / "r8_series.npz"
    if not path.is_file():
        raise NotJudgeable(f"{path} missing")
    with np.load(path, allow_pickle=False) as data:
        phases = [str(p) for p in data["phase"]]
        times = [float(t) for t in data["t"]]
    ready = next((t for t, p in zip(times, phases, strict=True) if p == "ready"), None)
    return {"first_ready_s": ready, "has_reanchor_phase": "reanchor" in phases}


def _locked_bar(value) -> float | None:
    if _is_number(value):
        return float(value)
    if isinstance(value, dict):
        for key in ("locked_max_bar", "locked_bar", "locked"):
            if _is_number(value.get(key)):
                return float(value[key])
    return None


def judge_chrono_row(row: dict, entry: dict, case_dir: Path, f_d8: float,
                     angles: tuple[float, float], expected_tag: str) -> dict:
    result_path = case_dir / "result.json"
    if not result_path.is_file():
        raise NotJudgeable(f"{row['name']}: {result_path} missing")
    values, missing = chrono_fields({**entry, "result": _load_json(result_path)})
    if row["fs_kN"] is not None and "fs_kN" not in values:
        missing.append("fs_kN (an L2b row)")
    if missing:
        raise NotJudgeable(f"{row['name']}: verify keys missing {missing}")
    series = _r8_series(case_dir)
    times = values["times"]
    names = _event_names(values["events"])
    counts = event_counts(names)
    has_h4 = series["has_reanchor_phase"] or any(n.startswith("reanchor_started") for n in names)
    reasons = _chrono_identity(row, values, angles, expected_tag, series, times)
    items = {
        "J1": _at_least(values["J1_kN"] * 1e3 if _is_number(values["J1_kN"]) else None, f_d8),
        "J3": _is_number(values["J3_pad_min_kN"]) and values["J3_pad_min_kN"] > 0.0,
        "J4": _at_most(values["J4_deg"], spec.ATTITUDE_LIMIT_DEG),
        "J5": _at_most(times.get("ready"), spec.READY_LIMIT_S),
        "J6": _at_most(values["J6_moving_bar"], spec.MOVING_LIMIT_BAR),
        "J7": not counts["J7_stroke_events"], "J8": not counts["J8_fault_events"],
        "J9": not counts["J9_warn_events"], "J10": values["J10_recontacts"] == 0,
        "E-2": all(times.get(k) is not None for k in ("touch", "liftoff", "ready")),
        "E-3": not counts["E3_rejections"],
    }
    if has_h4:
        if "J2_kN" not in values:
            raise NotJudgeable(f"{row['name']}: H4 ran but min_cyl_reanchor_kN is missing")
        items["J2"] = _at_least(values["J2_kN"] * 1e3 if _is_number(values["J2_kN"]) else None,
                                f_d8)
    locked = _locked_bar(values.get("J6_locked"))
    if locked is not None:
        items["J6_locked"] = locked <= spec.LOCKED_LIMIT_BAR
    if _is_number(times.get("end")) and _is_number(times.get("liftoff")) and (
            times["end"] - times["liftoff"] < spec.LIFT_WINDOW_MIN_S):
        reasons.append("E-8 lift-off window < 1 s")
    judged = {"items": items, "fail_items": sorted(k for k, ok in items.items() if not ok),
              "not_judgeable": reasons}
    return {**row, "verdict": _verdict(judged), **judged,
            "values": {"J1_N": values["J1_kN"] * 1e3 if _is_number(values["J1_kN"]) else None,
                       "J2_N": (values["J2_kN"] * 1e3 if has_h4 and _is_number(values.get("J2_kN"))
                                else None), "J4_deg": values["J4_deg"]},
            "soil_events": counts["soil_events"],
            "liftoff_slow_count": counts["liftoff_slow_count"],
            "identity": {"settle_map_kind": (values["settle_map"].get("kind")
                                             if isinstance(values["settle_map"], dict) else None),
                         "scenario_group": values["scenario_group"],
                         "scenario_id": values.get("scenario_id"),
                         "controller_tag": values["controller_tag"]}}


def _chrono_identity(row, values, angles, expected_tag, series, times) -> list[str]:
    reasons = []
    if values["slope_limit_mode"] != "verification_ext":
        reasons.append(f"E-4 slope_limit_mode {values['slope_limit_mode']!r}")
    floor = values["floor_true_deg"]
    if not _angles_match(floor, angles, ANGLE_TOLERANCE_CHRONO_DEG):
        reasons.append(f"E-4 floor_true_deg {floor} != {list(angles)}")
    if values["row_number"] != row["number"]:
        reasons.append(f"I-4 row number {values['row_number']} != {row['number']}")
    spans = values["half_spans_deg"] or {}
    if any(not _is_number(spans.get(key)) or abs(spans[key] - expected) > 1e-9
           for key, expected in spec.VERIFICATION_EXT_HALF_SPANS_DEG.items()):
        reasons.append(f"E-4 half_spans_deg {spans} != {spec.VERIFICATION_EXT_HALF_SPANS_DEG}")
    if values["level"] != row["level"]:
        reasons.append(f"I-4 level {values['level']} != {row['level']}")
    if not _is_number(values["beta_GPa"]) or abs(values["beta_GPa"] - row["beta_GPa"]) > 1e-9:
        reasons.append(f"I-4 beta {values['beta_GPa']} != {row['beta_GPa']}")
    if row["fs_kN"] is not None and (not _is_number(values.get("fs_kN"))
                                     or abs(values["fs_kN"] - row["fs_kN"]) > 1e-9):
        reasons.append(f"I-4 F_s {values.get('fs_kN')} != {row['fs_kN']}")
    las = values["liftoff_slow"]
    las_on = las.get("enable") if isinstance(las, dict) else las
    reasons += _tag_problems(values["controller_tag"], expected_tag, las_on, True)
    # rev3 E-6d: Chrono runs the preset (K1 on): the d8x record and the controller meta agree
    if values["k1_order_gate"] is not True or values["controller_meta_order_gate"] is not True:
        reasons.append(f"E-6d K1 gate d8x {values['k1_order_gate']!r} / controller_meta "
                       f"{values['controller_meta_order_gate']!r}, both must be true")
    reasons += _settle_map_problems(row, values["settle_map"])
    reasons += _scenario_problems(row, values["scenario_group"])
    ready = series["first_ready_s"]
    if ready is None and times.get("ready") is None:
        end = times.get("end")
        if _is_number(end) and end < spec.READY_LIMIT_S:
            reasons.append(f"E-2 exception (rev2 5): no READY and the run ends at {end:.1f} s "
                           f"< 120 s; rerun this row with T_run >= 130 s")
    elif ready is None or not _is_number(times.get("ready")) or abs(
            ready - times["ready"]) > READY_CROSS_CHECK_S:
        reasons.append(f"r8_series first READY {ready} vs verify {times.get('ready')}")
    return reasons


def _settle_map_problems(row: dict, settle_map) -> list[str]:
    """Rev2 2 E-4b: identity on L2b, ``for_level(level)`` on L1-R, from the row meta."""
    from outrigger_sim.control.target import CrawlerSettleMap

    expected_kind = spec.SETTLE_MAP_BY_ENGINE[row["engine"]]
    if not isinstance(settle_map, dict) or settle_map.get("kind") != expected_kind:
        return [f"E-4b settle map {settle_map!r}, expected {expected_kind}"]
    expected_map = (CrawlerSettleMap.identity() if expected_kind == "identity"
                    else CrawlerSettleMap.for_level(row["level"]))
    coefficients = settle_map.get("coefficients") or {}
    expected = expected_map.to_meta()
    if any(not _is_number(coefficients.get(k)) or abs(coefficients[k] - v) > 1e-12
           for k, v in expected.items()):
        return [f"E-4b settle map coefficients {coefficients} != {expected_kind} "
                f"{row['level']} {expected}"]
    return []


def _scenario_problems(row: dict, group) -> list[str]:
    """Rev2 6 / E-5: the scenario group is recorded; the rows the rules name have their group."""
    if not group:
        return ["E-5 scenario group not recorded (rev2 6)"]
    expected = spec.SCENARIO_GROUPS.get(row["number"])
    if expected is not None and group != expected:
        return [f"E-5 scenario group {group} != {expected} (rev2 6)"]
    return []


def _verify_entries(paths: list[Path]) -> dict[str, tuple[dict, Path]]:
    entries = {}
    for path in paths:
        for entry in _load_json(path).get("metrics", []):
            entries[entry.get("case")] = (entry, path.parent / str(entry.get("case")))
    return entries


def cmd_judge_chrono(args) -> tuple[int, dict]:
    points = _points(args)
    prelaunch = _load_json(Path(args.prelaunch))
    expected_tag = prelaunch["expected_tag"]
    selection = _load_json(Path(args.selection)) if args.selection else {}
    rows = spec.chrono_rows(selection.get("W", {}).get("chrono_floor"),
                            selection.get("V", {}).get("floor"))
    wanted = [r for r in rows if r["order"] in ((1,) if args.order == "1" else (2,))]
    entries = _verify_entries([Path(p) for p in args.verify])
    names = {**spec.points_by_name(points), **_w_floor_angles(points)}
    f_d8 = f_d8_N()
    judged, problems = [], []
    for row in wanted:
        if row["name"] not in entries:
            problems.append(f"row {row['name']} not in the verify files (E-1)")
            continue
        entry, case_dir = entries[row["name"]]
        angles = names.get(row["floor"])
        if angles is None:
            problems.append(f"{row['name']}: floor {row['floor']} has no point")
            continue
        try:
            judged.append(judge_chrono_row(row, entry, case_dir, f_d8, angles, expected_tag))
        except NotJudgeable as exc:
            problems.append(str(exc))
    extra = sorted(set(entries) - {r["name"] for r in rows})
    summary = _summarise(judged, len(wanted), f"C_order{args.order}")
    status = _status_of([summary], problems=problems)
    return status, {"field_map": {k: list(v) for k, v in CHRONO_FIELDS.items()},
                    "summary": summary, "rows": judged, "problems": problems,
                    "unlisted_verify_cases": extra}


def _w_floor_angles(points: dict) -> dict:
    """The W Chrono floor name -> the R-a point's angles (rules 5.1: W keeps the R-a point)."""
    angles = spec.points_by_name(points)
    return {c["floor"]: angles[c["ra_point"]] for c in points["w_candidates"]}


# ------------------------------------------------------------------------------- invariance
def cmd_invariance(args) -> tuple[int, dict]:
    ra_off = _load_json(Path(args.ra_off))["runs"]
    ra_on = _load_json(Path(args.ra_on))["runs"]
    rc_off = _load_jsonl(Path(args.rc_off))
    rc_on = _load_jsonl(Path(args.rc_on))
    v1 = _k1_pairs(ra_off, ra_on, rc_off, rc_on)
    v2 = _las_activity(ra_off, rc_off, ra_on, rc_on)
    v3 = _vb_v0_differences(rc_off)
    problems = v1.pop("problems")
    status = EXIT_NOT_JUDGEABLE if problems else EXIT_PASS
    return status, {"V-1": v1, "V-2": v2, "V-3": v3, "problems": problems}


def _k1_pairs(ra_off, ra_on, rc_off, rc_on) -> dict:
    problems, dependent = [], set()
    off_ids = {run["id"]: run for run in ra_off if run.get("stage") == "main"}
    pairs = 0
    for run in ra_on:
        twin = off_ids.get(run["id"])
        if twin is None:
            problems.append(f"R-a K1 run {run['id']} has no K1-off twin")
            continue
        pairs += 1
        if run.get("commands_sha256") != twin.get("commands_sha256"):
            dependent.add(("ra", run.get("point"), run.get("level")))
    rc_off_keys = {_rc_key(line): line for line in rc_off if float(line["job"]["eps"]) == 0.0}
    for line in rc_on:
        twin = rc_off_keys.get(_rc_key(line))
        if twin is None:
            problems.append(f"R-c K1 line {_rc_key(line)} has no K1-off twin")
            continue
        pairs += 1
        if line.get("commands_sha256") != twin.get("commands_sha256"):
            row = line["job"]["d1"]
            dependent.add(("rc", row["slope_name"], row["level"]))
    expected = spec.EXPECTED_COUNTS["ra_on"] + spec.EXPECTED_COUNTS["rc_on"]
    if pairs != expected:
        problems.append(f"K1 pairs {pairs} != {expected}")
    return {"pairs": pairs, "class": "K1_INVARIANT" if not dependent else "K1_DEPENDENT",
            "K1_DEPENDENT": sorted([list(d) for d in dependent]), "problems": problems}


def _las_activity(ra_off, rc_off, ra_on=(), rc_on=()) -> dict:
    """V-2: ``INFO_LIFTOFF_SLOW`` count per (bundle, point, level) over both K1 arms (user
    decision 2026-11-10, rev4 check A-2 (b)): a point whose LAS-b acted only in K1-on rows is
    LAS_DEPENDENT too. ``counts_by_arm`` keeps the split."""
    by_arm: dict[str, dict[str, int]] = {"off": {}, "on": {}}
    for arm, runs, lines in (("off", ra_off, rc_off), ("on", ra_on, rc_on)):
        counts = by_arm[arm]
        for run in runs:
            key = f"ra|{run.get('point')}|{run.get('level')}"
            counts[key] = counts.get(key, 0) + _liftoff_slow(run.get("d8x"))
        for line in lines:
            row = line["job"]["d1"]
            key = f"rc|{row['slope_name']}|{row['level']}"
            counts[key] = counts.get(key, 0) + _liftoff_slow((line.get("d1") or {}).get("d8x"))
    total: dict[str, int] = {}
    for counts in by_arm.values():
        for key, count in counts.items():
            total[key] = total.get(key, 0) + count
    return {"counts": total, "counts_by_arm": by_arm, "scope": "both K1 arms (rev4 A-2 (b))",
            "LAS_DEPENDENT": sorted(k for k, v in total.items() if v),
            "LAS_INACTIVE": sorted(k for k, v in total.items() if not v)}


def _liftoff_slow(d8x: dict | None) -> int:
    return event_counts(_event_names((d8x or {}).get("events")))["liftoff_slow_count"]


def _vb_v0_differences(rc_off) -> list[dict]:
    by_key = {}
    for line in rc_off:
        job = line["job"]
        row = job["d1"]
        key = (row["slope_name"], row["level"], row["crawler_k_scale"], float(job["eps"]))
        j1 = ((line.get("d1") or {}).get("d8x") or {}).get("J1_min_cyl_after_lift_N")
        by_key.setdefault(key, {})[job["setting"]] = j1
    out = []
    for (floor, level, scale, eps), values in sorted(by_key.items()):
        vb, v0 = values.get("VB"), values.get("V0")
        out.append({"floor": floor, "level": level, "crawler_k_scale": scale, "eps": eps,
                    "J1_VB_N": vb, "J1_V0_N": v0,
                    "VB_minus_V0_N": vb - v0 if _is_number(vb) and _is_number(v0) else None})
    return out


# ------------------------------------------------------------------------------- select-w/v
def _ra_top_rigid_min(ra_off: list[dict]) -> dict[str, float]:
    minimum: dict[str, float] = {}
    for run in ra_off:
        if run.get("level") != "top" or run.get("mast") != "rigid" or "error" in run:
            continue
        value = (run.get("d8x") or {}).get("J1_min_cyl_after_lift_N")
        if _is_number(value):
            minimum[run["point"]] = min(minimum.get(run["point"], math.inf), value)
    return minimum


def _rc_top_min(rc_off: list[dict]) -> dict[str, float]:
    minimum: dict[str, float] = {}
    for line in rc_off:
        row = (line.get("job") or {}).get("d1") or {}
        value = ((line.get("d1") or {}).get("d8x") or {}).get("J1_min_cyl_after_lift_N")
        if row.get("level") == "top" and _is_number(value):
            floor = row["slope_name"]
            minimum[floor] = min(minimum.get(floor, math.inf), value)
    return minimum


def cmd_select_w(args) -> tuple[int, dict]:
    points = _points(args)
    g0 = _load_json(Path(args.g0_judgement)) if args.g0_judgement else {}
    eligibility = g0.get("w_eligibility") or {}
    ra_min = _ra_top_rigid_min(_load_json(Path(args.ra_off))["runs"])
    rc_min = _rc_top_min(_load_jsonl(Path(args.rc_off)))
    ranking = []
    for order, candidate in enumerate(points["w_candidates"]):
        tag = candidate["ra_point"]
        values = [ra_min.get(tag)]
        mirror = points["w_mirrors"].get(tag)
        if mirror is not None:
            values.append(rc_min.get(mirror))
        if any(v is None for v in values):
            raise NotJudgeable(f"W candidate {tag}: J1 missing (R-a {values[0]}, mirror "
                               f"{values[1:] or None})")
        true_usage = next(e["R_v"] for e in points["ra_points"] if e["tag"] == tag)
        ranking.append({"ra_point": tag, "chrono_floor": candidate["floor"], "order": order,
                        "m_N": min(values), "ra_min_N": values[0],
                        "mirror": mirror, "mirror_min_N": values[1] if mirror else None,
                        "R_v_true": true_usage,
                        "eligible": true_usage <= spec.W_TRUE_RV_MAX,
                        "for_level_record": (eligibility.get(tag) or {}).get("for_level_record")})
    ranking.sort(key=lambda item: (item["m_N"], item["order"]))
    chosen = next((item for item in ranking if item["eligible"]), None)
    skipped = [item["ra_point"] for item in ranking[: ranking.index(chosen)]] if chosen else [
        item["ra_point"] for item in ranking]
    angles = spec.points_by_name(points)
    result = {"W": None if chosen is None else {
        **chosen, "angles_deg": list(angles[chosen["ra_point"]])},
        "skipped_ineligible": skipped, "ranking": ranking,
        "rule": "d8x_rules.md 5.1 with d8x_rules_rev1.md 5.1 / 4.3 eligibility"}
    out = Path(args.selection_out or spec.D8X_DIR / "d8x_selection.json")
    stored = _load_json(out) if out.is_file() else {}
    out.write_text(json.dumps({**stored, **result}, indent=1) + "\n", encoding="utf-8")
    return (EXIT_PASS if chosen else EXIT_FAIL), {**result, "selection_file": str(out)}


def cmd_select_v(args) -> tuple[int, dict]:
    judgement = _load_json(Path(args.chrono_judgement))
    rows = [r for r in judgement.get("rows", []) if r.get("number") in range(1, 7)]
    if len(rows) != 6 or any(not _is_number((r.get("values") or {}).get("J1_N")) for r in rows):
        raise NotJudgeable("select-v needs rows #1 .. #6 with J1")
    chosen = min(rows, key=lambda r: (r["values"]["J1_N"], r["number"]))
    result = {"V": {"floor": chosen["floor"], "from_row": chosen["name"],
                    "J1_N": chosen["values"]["J1_N"]}, "rule": "d8x_rules.md 5.2"}
    out = Path(args.selection_out or spec.D8X_DIR / "d8x_selection.json")
    stored = _load_json(out) if out.is_file() else {}
    out.write_text(json.dumps({**stored, **result}, indent=1) + "\n", encoding="utf-8")
    return EXIT_PASS, {**result, "selection_file": str(out)}


# ----------------------------------------------------------------------------------- report
def cmd_report(args) -> tuple[int, dict]:
    g0 = _load_json(Path(args.g0_judgement))
    ra = _load_json(Path(args.ra_judgement))
    rc = _load_json(Path(args.rc_judgement))
    chrono = [_load_json(Path(p)) for p in args.chrono_judgement]
    invariance = _load_json(Path(args.invariance)) if args.invariance else None
    f_d8 = f_d8_N()
    gates = {
        "G-S": {"seals": spec.seals_ok(), "audit_pre_run_clear": args.audit_pre_clear},
        "G0": g0.get("gate_G0"),
        # rev4 1.1 (F-1): both K1 arms are judged rows
        "G1": _gate_of([ra.get("gate_rows_off"), ra.get("gate_rows_on"),
                        rc.get("gate_rows_off"), rc.get("gate_rows_on")],
                       [*ra.get("problems", []), *rc.get("problems", [])]),
        "G2": [_gate_of([c.get("summary")], c.get("problems", [])) for c in chrono],
        "G3": {"recount_agrees": args.recount_agrees, "audit_post_clear": args.audit_post_clear,
               "carry_over_confirmed": args.carry_over_confirmed},
    }
    flags = _flags(ra, rc, chrono, g0, invariance, f_d8)
    grade = _grade(gates, flags, len(chrono))
    return {"pass": EXIT_PASS, "conditional": EXIT_PASS, "fail": EXIT_FAIL}.get(
        grade, EXIT_NOT_JUDGEABLE), {
            "grade": grade, "gates": gates, "flags": flags,
            # rev4 1.3: K1-on arm (i) / (ii) hits are records, not grade flags
            "flag_records_k1_on": _value_flags(_k1_on_rows(ra, rc), f_d8),
            # rev4 1.4: set these against path 2 bundles[...].k1_rows_fail by hand
            "k1_rows_failed": {"R-a": ra.get("k1_rows_failed", []),
                               "R-c": rc.get("k1_rows_failed", [])}}


def _gate_of(summaries: list, problems: list) -> str:
    if problems or any(s is None or s["expected"] != s["actual"] or s["not_judgeable"]
                       for s in summaries):
        return "not_judgeable"
    return "fail" if any(s["fail"] for s in summaries) else "pass"


def _k1_on_rows(ra: dict, rc: dict) -> list[dict]:
    return [r for r in (*ra.get("rows", []), *rc.get("rows", [])) if r.get("k1") == "on"]


def _flags(ra, rc, chrono, g0, invariance, f_d8) -> list[dict]:
    """Original 10 FLAG. (i) / (ii) from the K1-off arm and the Chrono rows (rev4 1.3)."""
    harness_off = [r for r in (*ra.get("rows", []), *rc.get("rows", [])) if r.get("k1") != "on"]
    flags = _value_flags([*harness_off, *[r for c in chrono for r in c["rows"]]], f_d8)
    if invariance:
        for point in invariance["V-1"].get("K1_DEPENDENT", []):
            flags.append({"flag": "(iii)", "K1_DEPENDENT": point})
        for point in invariance["V-2"].get("LAS_DEPENDENT", []):
            flags.append({"flag": "(iii)", "LAS_DEPENDENT": point})
    for evaluation in g0.get("evaluations", []):
        error = (evaluation.get("G0-4") or {}).get("max_err_deg")
        if evaluation.get("G0-4_judged") and _is_number(error) and error > spec.G0_4_ERROR_FLAG_DEG:
            flags.append({"flag": "(iv)", "point": evaluation["key"], "err_deg": error})
    return flags


def _value_flags(rows: list[dict], f_d8: float) -> list[dict]:
    """FLAG (i) J1 / J2 < F_D8 + 2 kN and (ii) stroke margin < 5 mm of ``rows``."""
    flags = []
    for row in rows:
        values = row.get("values") or {}
        name = row.get("id") or row.get("key") or row.get("name")
        for item in ("J1_N", "J2_N"):
            if _is_number(values.get(item)) and values[item] < f_d8 + spec.FLAG_EXTRA_N:
                flags.append({"flag": "(i)", "row": name, "item": item, "value": values[item]})
        stroke = values.get("stroke_max_m")
        if _is_number(stroke) and (spec.STROKE_GUARD_M - stroke) * 1e3 < spec.STROKE_FLAG_MARGIN_MM:
            flags.append({"flag": "(ii)", "row": name, "margin_mm": (spec.STROKE_GUARD_M - stroke)
                          * 1e3})
    return flags


def _grade(gates: dict, flags: list, chrono_parts: int) -> str:
    states = [gates["G0"], gates["G1"], *gates["G2"]]
    if not gates["G-S"]["seals"] or "not_judgeable" in states or None in states:
        return "not_judgeable"
    if not all(gates["G3"].values()) or not gates["G-S"]["audit_pre_run_clear"]:
        return "not_judgeable"
    if "fail" in states:
        return "fail"
    if chrono_parts < 2:
        return "not_judgeable"
    return "conditional" if flags else "pass"


# -------------------------------------------------------------------------------------- CLI
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="D8x judge (path 1)")
    parser.add_argument("--out", type=Path, default=None, help="report file")
    parser.add_argument("--format", choices=("json", "md"), default="json")
    parser.add_argument("--points-file", default=str(spec.POINTS_PATH))
    sub = parser.add_subparsers(dest="command", required=True)
    points = sub.add_parser("points")
    points.add_argument("--check", action="store_true")
    manifest = sub.add_parser("manifest")
    manifest.add_argument("--bundle", required=True, choices=("ra", "rc", "C", "judge", "all"))
    manifest.add_argument("--commit", default="HEAD")
    manifest.add_argument("--python", default=None, help="interpreter for the import closure")
    manifest.add_argument("--results", nargs="*", default=[])
    manifest.add_argument("--compare", default=None, help="an earlier manifest JSON (I-2)")
    prelaunch = sub.add_parser("prelaunch")
    prelaunch.add_argument("--bundle", required=True, choices=("ra", "rc", "C"))
    prelaunch.add_argument("--python", required=True)
    prelaunch.add_argument("--mask", required=True, help="affinity mask of the run (0x0FFF0000)")
    prelaunch.add_argument("--k1", choices=("off", "on"), default=None,
                           help="ra / rc: the K1 arm of this run, required (rev3 2)")
    prelaunch.add_argument("--expected-tag", default=None)
    prelaunch.add_argument("--start-states", default=None)
    prelaunch.add_argument("--threads", type=int, default=None)
    prelaunch.add_argument("--selection", default=None)
    prelaunch.add_argument("--record-out", default=None)
    expect = sub.add_parser("expect-file")
    expect.add_argument("--expect-out", default=str(spec.D8X_DIR / "d8x_expect_k1.json"))
    g0 = sub.add_parser("judge-g0")
    g0.add_argument("--g0", default=str(spec.G0_REV3_PATH),
                    help="rev3 4 recompute file (d8x_g0_rev3.json, or <commit>:<path>)")
    g0.add_argument("--at-commit", default="HEAD",
                    help="commit whose closure blobs the G0 run must match (H_impl or M)")
    for name in ("judge-ra", "judge-rc"):
        bundle = sub.add_parser(name)
        bundle.add_argument("--off", required=True)
        bundle.add_argument("--on", required=True)
        bundle.add_argument("--prelaunch", default=None)
    chrono = sub.add_parser("judge-chrono")
    chrono.add_argument("--verify", nargs="+", required=True)
    chrono.add_argument("--prelaunch", required=True)
    chrono.add_argument("--selection", default=None)
    chrono.add_argument("--order", choices=("1", "2"), default="1")
    invariance = sub.add_parser("invariance")
    for name in ("--ra-off", "--ra-on", "--rc-off", "--rc-on"):
        invariance.add_argument(name, required=True)
    select_w = sub.add_parser("select-w")
    select_w.add_argument("--g0-judgement", default=None,
                          help="judge-g0 output (for_level R_v hat records only, rev2 3)")
    select_w.add_argument("--ra-off", required=True)
    select_w.add_argument("--rc-off", required=True)
    select_w.add_argument("--selection-out", default=None)
    select_v = sub.add_parser("select-v")
    select_v.add_argument("--chrono-judgement", required=True)
    select_v.add_argument("--selection-out", default=None)
    report = sub.add_parser("report")
    report.add_argument("--g0-judgement", required=True)
    report.add_argument("--ra-judgement", required=True)
    report.add_argument("--rc-judgement", required=True)
    report.add_argument("--chrono-judgement", nargs="*", default=[])
    report.add_argument("--invariance", default=None)
    for flag in ("--audit-pre-clear", "--recount-agrees", "--audit-post-clear",
                 "--carry-over-confirmed"):
        report.add_argument(flag, action="store_true")
    return parser


COMMANDS: dict[str, Callable] = {
    "points": cmd_points, "manifest": cmd_manifest, "prelaunch": cmd_prelaunch,
    "expect-file": cmd_expect_file, "judge-g0": cmd_judge_g0, "judge-ra": cmd_judge_ra,
    "judge-rc": cmd_judge_rc,
    "judge-chrono": cmd_judge_chrono, "invariance": cmd_invariance, "select-w": cmd_select_w,
    "select-v": cmd_select_v, "report": cmd_report,
}


def _markdown(command: str, status: int, result: dict) -> str:
    lines = [f"# d8x_judge {command}", "", f"- exit: {status}"]
    for key, value in result.items():
        if key == "rows":
            lines.append(f"- rows: {len(value)}")
            continue
        lines.append(f"- {key}: `{json.dumps(value, ensure_ascii=False)[:2000]}`")
    return "\n".join(lines) + "\n"


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        seals = spec.seal_report()
        if not spec.seals_ok(seals):
            raise NotJudgeable(f"rules seal mismatch: {seals}")
        status, result = COMMANDS[args.command](args)
        result = {"seals": {rev: entry["ok"] for rev, entry in seals.items()}, **result}
    except NotJudgeable as exc:
        status, result = EXIT_NOT_JUDGEABLE, {"error": str(exc)}
    except Exception as exc:  # contract: exit 3 with the trace in the report
        status, result = EXIT_INTERNAL, {"error": repr(exc), "trace": traceback.format_exc()}
    if args.out is not None:
        text = (json.dumps(result, indent=1, ensure_ascii=False) + "\n" if args.format == "json"
                else _markdown(args.command, status, result))
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    summary = {"command": args.command, "exit": status,
               **{k: result[k] for k in ("gate_G0", "grade", "error", "summary", "summaries",
                                         "problems") if k in result}}
    print(json.dumps(summary, ensure_ascii=False, default=str)[:4000])
    return status


if __name__ == "__main__":
    sys.exit(run())
