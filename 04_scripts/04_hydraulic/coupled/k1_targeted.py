"""LAS-b K1 (R4c30 order gate) on the reduced harness: bundles Y-0, Y-P, Y-S, Y-T.

Rules: ``06_analysis/02_control/verif_matrix/las_k1_rules.md`` (control-expert, sealed; LF
sha256 ``k1_judge.RULES_K1_SHA256``) and the six A-plan rules files it inherits (all checked
before anything runs). The rules text wins where this code differs. The run machinery (LAS-b
candidate wrapper, DONE record, pool, job dicts) is ``las_revA_targeted``'s; the S-C job dicts
come from ``s2_defer_targeted``; the key lists, sub-bundles and the judgement are
``k1_judge``'s. S2D is not installed (its settings stay the class defaults, recorded on every
line).

Candidates (two separate fields, rules 2): ``las_candidate`` P0 (the preset LAS-b b0) or P5r4
(``las_revA_targeted``), ``k1_candidate`` K1off / K1on (``dataclasses.replace`` of
``config.slope_clearance_margin.flat_soil_margin_order_gate`` in ``C2Controller.__init__``,
worker only; K1off sets False explicitly). The preset is not touched.

Sub-bundles (rules 3, ``k1_judge.SUB_BUNDLES``):
  Y-0a 5 / Y-0b 30 / Y-0c 30 / Y-0d 40 (K1off: hashes = the stored ones, shadow record),
  Y-Pa 165 / Y-Pb 40 (P0 + K1on), Y-Sa 30 (P0 + K1on) / Y-Sb 30 (P5r4 + K1on),
  Y-T 192 (P5r4 + K1on).
``run --bundle`` takes a bundle (all its sub-bundles) or one sub-bundle. Output
``<v5>/las/k1/k1_<name>.jsonl`` (opened with ``"x"``: new files only).

Gates before a run (exit 2): the seven rules seals; the stored base files (raw sha256) and the
recomputed key lists (= the appendix list sha256, rules 7); the LAS-b b0 preset; the run
identity (empty code diff, allowed dirty files, one thread, ``MKL_THREADING_LAYER=TBB``); job
dicts = the stored lines'; every earlier bundle judged ``pass`` (rules 3 order; after a
``stop`` only with ``--after-stop-decision``, recorded on every line); no line of the same
sub-bundles in another file. ``--keys`` / ``--limit`` exist only for a trial into
``--trial-out`` outside the K1 folder (rules 7: never in a judged run).
During a batch (rules 6): a run identity or ``controller_tag`` change stops the batch (SK-1);
an error line runs once more inside the batch, a second error stops it (SK-2); everything
else (a K, H or C finding) only prints: the bundle runs to its end and ``k1_judge`` grades it.
``--resume`` (SK-2, once): the keys of the bundle file with one error line and no finished
line, into ``k1_<name>_resume.jsonl`` (``k1.resume`` true on its lines).

Line = the ``run_v5`` line + ``las`` / ``rev`` / ``done_trace`` (``las_revA_targeted``) + ``k1``
{bundle, sub_bundle, las_candidate, k1_candidate, key, label, enabled, setting, decisions,
r4_applied, would_block_any, loc_calls (witness of ``_apply_slope_clearance_margin``),
identity, the seven rules sha256, controller_tag, base_file, base_file_sha256, s2d_settings,
resume, after_stop_decision, runner_mask}.

Usage (dynamics-dev python.exe, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/k1_targeted.py list [--bundle Y-0 ..]
      [--v5-dir <main checkout v5>]
  python -I -B 04_scripts/04_hydraulic/coupled/k1_targeted.py run --bundle Y-0
      [--v5-dir <v5>] [--workers 4] [--affinity HEX] [--resume]
      [--after-stop-decision TEXT] [--trial-out <jsonl> [--keys K1,K2] [--limit N]]
Exit codes: 0 done, 1 a batch stop or run errors (run) / a count or reference mismatch (list),
2 input error (seals, stored files, lists, gates, identity, job dicts, existing output).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import k1_judge as kj  # noqa: E402  (stdlib only: loads no numpy)
import las_revA_targeted as revA  # noqa: E402  (imports fb_targeted: thread variables first)
import s2_defer_targeted as s2t  # noqa: E402

rev = revA.rev
fb = revA.fb
rj = kj.rj
ROOT = fb.ROOT
IDENTITY_FILES = {**revA.DIAG_IDENTITY_FILES,
                  "s2_defer_targeted.py": HERE / "s2_defer_targeted.py",
                  "s2_defer_judge.py": HERE / "s2_defer_judge.py",
                  "k1_targeted.py": HERE / "k1_targeted.py",
                  "k1_judge.py": HERE / "k1_judge.py"}
"""Rules 2: c2.py, the nine inherited harness-path files (S2D judgement 0.2),
``s2_defer_targeted.py`` (and the ``s2_defer_judge.py`` it imports), the K1 tool and judge."""
RUN_CHOICES = (*kj.BUNDLES, *kj.SUB_BUNDLES)
LIST_SOURCE = {"A": "SC", "A5": "SC", "B": "SC", "C": "RS", "D": "RT"}
"""Where the job dicts of a key list come from (the file that made the stored hash)."""
WITNESS_ATTRIBUTE = "_k1_loc_calls"
RESUME_SUFFIX = "_resume"


# ------------------------------------------------------------------------------- installs
_INSTALLED: dict = {}


def install_order_gate(is_on: bool, controller_class=None) -> None:
    """Wrap ``C2Controller.__init__`` so every controller of this worker has
    ``slope_clearance_margin.flat_soil_margin_order_gate = is_on`` (nothing else changes).

    Raises:
        RuntimeError: Installed twice in one process.
    """
    if "gate" in _INSTALLED:
        raise RuntimeError("k1_targeted.install_order_gate: already installed")
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
    original_init = controller_class.__init__

    def __init__(self, geometry, config=None, *args, **kwargs):
        if config is not None:
            margin = replace(config.slope_clearance_margin, flat_soil_margin_order_gate=is_on)
            config = replace(config, slope_clearance_margin=margin)
        original_init(self, geometry, config, *args, **kwargs)

    controller_class.__init__ = __init__
    _INSTALLED["gate"] = (controller_class, "__init__", original_init)


def _witness_hook(original):
    def _apply_slope_clearance_margin(self, t_s):
        before_s = self._state.slope_margin_applied_s
        original(self, t_s)
        after_s = self._state.slope_margin_applied_s
        soil = self._soil_state()
        self.__dict__.setdefault(WITNESS_ATTRIBUTE, []).append({
            "t_s": float(t_s),
            "slope_margin_fired": after_s is not None and after_s != before_s,
            "r4_on": self.config.slope_clearance_margin.flat_soil_margin_m > 0.0,
            "t_S_s": soil.soil_mode_start_s, "t_P_s": soil.plateau_start_s})

    return _apply_slope_clearance_margin


def install_loc_witness(controller_class=None) -> None:
    """Record every call of ``_apply_slope_clearance_margin`` (one per confirmed LOC): the
    K-1 evidence of which LOCs evaluated R4 (read only, commands unchanged).

    Raises:
        RuntimeError: Installed twice in one process.
    """
    if "witness" in _INSTALLED:
        raise RuntimeError("k1_targeted.install_loc_witness: already installed")
    if controller_class is None:
        from outrigger_sim.control import c2

        controller_class = c2.C2Controller
    original = controller_class._apply_slope_clearance_margin
    controller_class._apply_slope_clearance_margin = _witness_hook(original)
    _INSTALLED["witness"] = (controller_class, "_apply_slope_clearance_margin", original)


def uninstall() -> None:
    """Undo both installs (tests only; workers never uninstall)."""
    for name in ("gate", "witness"):
        if name in _INSTALLED:
            cls, attribute, original = _INSTALLED.pop(name)
            setattr(cls, attribute, original)


# ------------------------------------------------------------------------------- jobs
def base_jobs(source: str) -> list[dict]:
    """``run_v5`` jobs of a stored file's keys, as the file's own tool built them."""
    if source == "SC":
        return s2t.soil_group_jobs()
    if source == "RS":
        return rev.s_base_jobs()
    if source == "RT":
        return rev.t_base_jobs()
    raise ValueError(f"unknown job source {source!r}")


def run_names(name: str) -> list[str]:
    """Sub-bundles of ``--bundle`` (a bundle or one sub-bundle)."""
    if name in kj.SUB_BUNDLES:
        return [name]
    return [sub.name for sub in kj.SUB_BUNDLES.values() if sub.bundle == name]


def _k1_entry(sub: kj.SubBundle, key: str, bases: kj.Bases, options: dict) -> dict:
    base_file, base_sha256 = kj.reference_file_of(sub, key, bases)
    return {"bundle": sub.bundle, "sub_bundle": sub.name, "las_candidate": sub.las_candidate,
            "k1_candidate": sub.k1_candidate, "base_file": base_file,
            "base_file_sha256": base_sha256, "resume": options.get("resume", False),
            "after_stop_decision": options.get("after_stop_decision"),
            "runner_mask": options.get("runner_mask"), "trial": options.get("trial", False)}


def sub_jobs(sub: kj.SubBundle, bases: kj.Bases, keys: list[str] | None = None,
             options: dict | None = None) -> list[dict]:
    """The jobs of one sub-bundle (VB first, the list order otherwise) with ``rev`` entries."""
    options = options or {}
    wanted = kj.sub_keys(sub, bases) if keys is None else list(keys)
    by_key = {fb.fb_key(job): job for job in base_jobs(LIST_SOURCE[sub.key_list])}
    missing = [key for key in wanted if key not in by_key]
    if missing:
        raise KeyError(f"{sub.name}: keys without a job: {missing[:5]}")
    ordered = sorted((by_key[key] for key in wanted), key=lambda job: job["setting"] != "VB")
    jobs = []
    for job in ordered:
        entry = rev._entry(sub.bundle, sub.las_candidate,
                           f"{sub.las_candidate}-{sub.k1_candidate}",
                           record_done=sub.record_done)
        entry["k1"] = _k1_entry(sub, fb.fb_key(job), bases, options)
        jobs.append(rev._with_entry(job, entry, options.get("mask")))
    return jobs


def bundle_jobs(name: str, bases: kj.Bases, keys_by_sub: dict | None = None,
                options: dict | None = None) -> list[dict]:
    """Jobs of a bundle or sub-bundle with ids over the whole run."""
    jobs = []
    for sub_name in run_names(name):
        keys = None if keys_by_sub is None else keys_by_sub.get(sub_name, [])
        if keys is not None and not keys:
            continue
        jobs += sub_jobs(kj.SUB_BUNDLES[sub_name], bases, keys, options)
    for index, job in enumerate(jobs):
        job["rev"]["id"] = index
    return jobs


def job_dict_problems(jobs: list[dict], bases: kj.Bases) -> list[str]:
    """Rules 3: every job dict = the job of the stored line that made its hash (and the
    stored L line's where there is one)."""
    problems = []
    for job in jobs:
        key = fb.fb_key(job)
        sub = kj.SUB_BUNDLES[job["rev"]["k1"]["sub_bundle"]]
        line = bases.by_file.get(LIST_SOURCE[sub.key_list], {}).get(key)
        if line is None:
            problems.append(f"{sub.name} {key}: no stored line")
        elif rev._comparable_job(job) != rev._comparable_job(line["job"]):
            problems.append(f"{sub.name} {key}: job dict differs from the stored line")
        stored_l = rj.stored_line(bases.stored_l, key) if bases.stored_l else None
        if stored_l is not None and rev._comparable_job(job) != rev._comparable_job(
                stored_l["job"]):
            problems.append(f"{sub.name} {key}: job dict differs from the stored L line")
    return problems


# ------------------------------------------------------------------------------- worker
def rules_block() -> dict:
    return dict(zip(kj.RULES_FIELDS, kj.RULES_VALUES, strict=True))


def run_identity() -> dict:
    return fb.run_identity(files=IDENTITY_FILES)


def _install_all(entry: dict) -> None:
    install_loc_witness()
    revA._install_all(entry)  # threads, preset LAS-b b0, run capture, P5r4, DONE record
    install_order_gate(entry["k1"]["k1_candidate"] == kj.K1_ON)


def k1_block(entry: dict, job: dict, controller, line: dict, identity: dict) -> dict:
    meta = controller.meta()["slope_clearance_margin"]
    decisions = meta["order_gate"]["decisions"]
    soil = controller.config.soil
    return {**entry["k1"], "key": fb.fb_key(job), "label": entry["label"],
            "enabled": meta["order_gate"]["enabled"],
            "setting": controller.config.slope_clearance_margin.flat_soil_margin_order_gate,
            "decisions": decisions, "r4_applied": bool(meta["flat_soil_margin_applied"]),
            "would_block_any": any(decision["would_block"] for decision in decisions),
            "loc_calls": list(controller.__dict__.get(WITNESS_ATTRIBUTE) or ()),
            "identity": identity, **rules_block(),
            "controller_tag": line.get("controller_tag"),
            "s2d_settings": {name: getattr(soil, name) for name in s2t.DEFER_FIELDS}}


def _add_blocks(line: dict, entry: dict, job: dict, identity: dict) -> None:
    revA._add_blocks(line, entry, job, identity)
    _, controller = fb._run_objects(job)
    line["rev"].update(rules_block())
    line["k1"] = k1_block(entry, job, controller, line, identity)


def run_k1_job(job: dict) -> dict:
    """Worker: install the witness, the LAS-b candidate and the K1 setting, run, add blocks."""
    t_start = time.perf_counter()
    entry = job.pop("rev")
    head = {"job": job, "rev": {**entry, "key": fb.fb_key(job)}}
    try:
        import run_v5  # sys.path and thread variables first

        identity = run_identity()
        _install_all(entry)
    except Exception as exc:  # recorded as an error line; the batch decides (SK-2)
        return {**head, "error": f"install: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    line = run_v5.run_one(job)
    if "error" in line:
        return {**line, "rev": head["rev"]}
    try:
        _add_blocks(line, entry, job, identity)
    except Exception as exc:
        return {**head, "error": f"metrics: {exc!r}", "tb": traceback.format_exc()[-3000:],
                "wall_s": round(time.perf_counter() - t_start, 1)}
    line["rev"]["id"] = entry["id"]
    return line


# ------------------------------------------------------------------------------- batch check
def make_checker():
    """``check(record, bundle, state, stored, k3_keys, identity)`` of ``rev.run_batch``:
    SK-1 stops (identity, controller tag); every other finding only prints (rules 6)."""

    def check(record, bundle, state, stored, k3_keys, current_identity) -> None:
        block = kj.k1_of(record)
        problems = fb.identity_mismatch(block.get("identity"), current_identity)
        if problems:
            state.stop = f"SK-1 run identity changed during the batch: {problems[:3]}"
            return
        tags = rj.tag_problems(record)
        if tags:
            state.stop = f"SK-1 {kj.key_of(record)}: {tags}"
            return
        decisions = block.get("decisions") or []
        found = kj.k1_problems(record) + kj.k23_problems(record)
        print(f"  k1 {block.get('sub_bundle')} {kj.key_of(record)}: decisions "
              f"{[(d.get('dP'), d.get('applied')) for d in decisions]}"
              f"{' PROBLEMS ' + str(found) if found else ''}", flush=True)

    return check


# ------------------------------------------------------------------------------- gates
def k1_dir_of(v5_dir: Path) -> Path:
    return v5_dir / kj.K1_DIR_RELATIVE


def out_name(name: str, is_resume: bool = False) -> str:
    return f"k1_{name.replace('-', '')}{RESUME_SUFFIX if is_resume else ''}.jsonl"


def identity_gate_problems(identity: dict) -> list[str]:
    return kj.identity_value_problems({"identity": identity, **rules_block()})


def order_gate_problems(name: str, lines: list[dict], bases: kj.Bases,
                        after_stop_decision: str | None) -> list[str]:
    """Rules 3 / 6: every bundle before this one judged ``pass`` (after a ``stop`` only with
    a recorded user decision)."""
    bundle = kj.SUB_BUNDLES[name].bundle if name in kj.SUB_BUNDLES else name
    earlier = kj.BUNDLES[: kj.BUNDLES.index(bundle)]
    if not earlier:
        return []
    result = kj.judge(lines, bases)
    problems = []
    for previous in earlier:
        status = result["bundles"][previous]["status"]
        if status == kj.STATUS_PASS:
            continue
        if status == kj.STATUS_STOP and after_stop_decision:
            print(f"{previous} stop: going on by the user decision {after_stop_decision!r}")
            continue
        problems.append(f"{previous} is {status}, not pass (rules 3 / 6)")
    return problems


def existing_line_problems(name: str, lines: list[dict]) -> list[str]:
    """No line of the same sub-bundles in another file (duplicates are a stop, rules 7)."""
    subs = set(run_names(name))
    found = sum(1 for line in lines if kj.k1_of(line).get("sub_bundle") in subs)
    return [f"{found} lines of {sorted(subs)} exist already (use --resume for error keys)"] \
        if found else []


def resume_plan(name: str, lines: list[dict]) -> dict[str, list[str]]:
    return {sub_name: kj.resume_keys(lines, sub_name) for sub_name in run_names(name)}


def _prepare(args) -> tuple[list[dict], Path, dict]:
    """Jobs, output path and identity of a run (raises ValueError / KeyError on input errors)."""
    is_trial = args.trial_out is not None
    if (args.keys or args.limit is not None) and not is_trial:
        raise ValueError("--keys / --limit only with --trial-out (rules 7)")
    k1_dir = k1_dir_of(args.v5_dir)
    if is_trial and args.trial_out.resolve().is_relative_to(k1_dir.resolve()):
        raise ValueError("--trial-out must lie outside the K1 folder")
    bases, problems = kj.load_bases(args.v5_dir)
    if problems:
        raise ValueError(f"stored files / key lists (rules 7): {problems[:5]}")
    import run_v5  # noqa: F401  (puts 03_src on sys.path before the preset check)

    fb.check_preset_las()
    identity = run_identity()
    problems = identity_gate_problems(identity)
    if problems:
        raise ValueError(f"run identity (rules 2): {problems}")
    lines = kj.read_run_lines(k1_dir) if k1_dir.exists() else []
    options = {"mask": None if args.affinity is None else int(args.affinity, 16),
               "runner_mask": args.affinity, "after_stop_decision": args.after_stop_decision,
               "resume": args.resume, "trial": is_trial}
    keys_by_sub = None
    if args.keys:
        wanted = set(args.keys.split(","))
        keys_by_sub = {name: [key for key in kj.sub_keys(kj.SUB_BUNDLES[name], bases)
                              if key in wanted] for name in run_names(args.bundle)}
    if not is_trial:
        problems = order_gate_problems(args.bundle, lines, bases, args.after_stop_decision)
        if not args.resume:
            problems += existing_line_problems(args.bundle, lines)
        if problems:
            raise ValueError(f"gates before {args.bundle}: {problems}")
    if args.resume:
        keys_by_sub = resume_plan(args.bundle, lines)
        print(f"resume keys (SK-2): {keys_by_sub}", flush=True)
    path = args.trial_out if is_trial else k1_dir / out_name(args.bundle, args.resume)
    problem = rev.out_path_problem(path, args.trial_out.parent if is_trial else k1_dir)
    if problem is not None:
        raise ValueError(problem)
    jobs = bundle_jobs(args.bundle, bases, keys_by_sub, options)
    problems = job_dict_problems(jobs, bases)
    if problems:
        raise ValueError(f"job dicts: {problems[:5]}")
    jobs = jobs if args.limit is None else jobs[: args.limit]
    if not jobs:
        raise ValueError("no runs selected")
    return jobs, path, identity


def _run_command(args) -> int:
    try:
        jobs, path, identity = _prepare(args)
    except (KeyError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"bundle": args.bundle, "stop": "input", "reason": str(exc)}))
        return 2
    print(f"run identity: {identity['git_head']} dirty {identity['git_dirty']} "
          f"code_diff {identity['code_diff_sha256'][:12]} rules K1 "
          f"{kj.RULES_K1_SHA256[:12]}", flush=True)
    print(f"{args.bundle}: {len(jobs)} runs -> {path}", flush=True)
    state = rev.run_batch(jobs, path, args.workers, args.bundle, {}, identity,
                          worker=run_k1_job, check=make_checker(), whole_bundle_rerun=())
    summary = {"bundle": args.bundle, "out": str(path), "runs": state.runs,
               "errors": state.errors, "skipped": state.skipped, "stop": state.stop}
    print(json.dumps(summary))
    return 1 if state.stop or state.skipped else 0


# ------------------------------------------------------------------------------- list
def list_bundles(names: list[str], v5_dir: Path) -> tuple[list[str], list[str]]:
    """(report lines, problems): base files, recomputed lists and runs per (sub-)bundle."""
    bases, problems = kj.load_bases(v5_dir)
    report = [f"base {name}: {bases.paths.get(name)} sha256 {bases.sha256.get(name)}"
              for name in (*kj.BASE_FILES, *kj.STORED_L_FILES)]
    for name, keys in bases.lists.items():
        report.append(f"list {name}: {len(keys)} keys sha256 {kj.key_list_sha256(keys)} "
                      f"(appendix {kj.LIST_SHA256[name][:12]})")
    if problems:
        return report, problems
    for name in names:
        jobs = bundle_jobs(name, bases)
        counts: dict[str, int] = {}
        for job in jobs:
            sub_name = job["rev"]["k1"]["sub_bundle"]
            counts[sub_name] = counts.get(sub_name, 0) + 1
        report.append(f"{name}: {len(jobs)} runs {counts}")
        expected = kj.BUNDLE_COUNTS.get(name)
        if expected is not None and len(jobs) != expected:
            problems.append(f"{name}: {len(jobs)} runs, expected {expected}")
        problems += job_dict_problems(jobs, bases)
    return report, problems


# ------------------------------------------------------------------------------- CLI
def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="runs of the bundles and the stored-input checks")
    listing.add_argument("--bundle", nargs="+", choices=RUN_CHOICES, default=list(kj.BUNDLES))
    listing.add_argument("--v5-dir", type=Path, default=kj.V5_DIR,
                         help="v5 folder with the stored files (the main checkout's)")
    run = sub.add_parser("run", help="run a bundle into a new file")
    run.add_argument("--bundle", required=True, choices=RUN_CHOICES)
    run.add_argument("--v5-dir", type=Path, default=kj.V5_DIR)
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--affinity", default=None, help="hex mask, set in every worker")
    run.add_argument("--resume", action="store_true",
                     help="SK-2: re-run the keys with one error line once")
    run.add_argument("--after-stop-decision", default=None,
                     help="user decision text that allows going on after an earlier stop")
    run.add_argument("--trial-out", type=Path, default=None,
                     help="trial run file outside the K1 folder (never judged)")
    run.add_argument("--keys", default=None, help="trial only: comma-separated keys")
    run.add_argument("--limit", type=int, default=None, help="trial only: first N runs")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    problems = kj.seal_problems()
    if problems:
        print(f"input error (rules seals): {problems}")
        print(json.dumps({"stop": "seals", "reasons": problems}))
        return 2
    if args.command == "run":
        return _run_command(args)
    try:
        lines, problems = list_bundles(args.bundle, args.v5_dir)
    except (KeyError, OSError, ValueError) as exc:
        print(f"input error: {exc!r}")
        print(json.dumps({"bundles": args.bundle, "input_error": str(exc)}))
        return 2
    print("\n".join(lines))
    for problem in problems:
        print(f"MISMATCH {problem}")
    print(json.dumps({"bundles": args.bundle, "problems": len(problems)}))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
