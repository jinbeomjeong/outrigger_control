"""436.9 B2 dry check (addendum 4a-3 5.1, K-6): five runs outside every judged set, of which only
the two P4 evidence keys (``rod_reading_truth_calls``, ``two_pressure_reads``) and the error
flag are read. The outputs belong to an own folder (``dryrun_evidence/``) and no judgement uses
them.

Sub-commands:

``select``     The union of the judged job sets (run_v5 ``j9_main``, ``j9_cases``, ``j9_case_f``,
               ``j9_t8`` of ``--main-jsonl``; the jobs of the sealed baseline's rows; the Dg-3
               135 keys of ``--dg3``) and the jobs chosen outside it: the first event-path job
               of :data:`EVENT_CANDIDATES` whose normalised job (``job`` without ``setting``,
               ``mask``, ``t4h_dir``) is not in the union, and the first L2 key of ``--noise``
               that is not a Dg-3 key. The output shows the proof (``in_union`` false, the
               union sizes) and the five commands. No event candidate outside the union = stop
               (exit 2: 4a-3 5.1 "확인 필요", never a judged job instead).
``run-event``  One event-path run of the selected job under ``--setting`` (VBJ, VBH or VBJ0) in
               a spawned worker (``run_v5.run_one``), one JSON line to ``--out``. The main
               session launches it (a simulation).
``summarize``  The five outputs against the 4a-3 5.1 table: per run only the evidence keys and
               whether it ran without an error.

Exit codes: 0 done / all five as expected (``summarize``), 1 an expectation missed
(``summarize``), 2 not judgeable (no candidate outside the union, an output missing or without
the keys, an existing ``--out``), 3 error. The stdout's last line is JSON with ``status`` and the
output path only.

Usage (dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_dryrun_evidence.py select --out <sel.json>
      --main-jsonl <main checkout>/06_analysis/03_hydraulic/coupled/v5/main.jsonl
      --baseline <main checkout>/06_analysis/02_control/j_p3_cause/baseline_221456d
      --dg3 <main checkout>/06_analysis/03_hydraulic/coupled/v5/resume_k1/h6_dg3_v4on.json
      --noise <main checkout>/06_analysis/03_hydraulic/coupled/v5/resume_k1/h8_noise_VB.json
  python -I -B ... run-event --selection <sel.json> --setting VBJ
      --out <dryrun_evidence/event_VBJ.jsonl>
  python -I -B ... summarize --selection <sel.json> --out <summary.json>
      --event VBJ=<jsonl> VBH=<jsonl> VBJ0=<jsonl> --r79 VBJ=<json> VBH=<json>
"""
from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import jp3_baseline_compare as compare  # noqa: E402
from j_p3_inputs import ROD_READING_EVIDENCE_KEYS  # noqa: E402

JUDGED_BATCHES = ("j9_main", "j9_cases", "j9_case_f", "j9_t8")
RUNTIME_KEYS = ("setting", "mask", "t4h_dir")
EVENT_CANDIDATES = (
    {"case": "R14", "eps": 0.0, "offset_s": 0.025},
    {"case": "R16", "eps": 0.0, "offset_s": 0.0125},
    {"case": "R15", "eps": 0.0, "offset_s": 0.025},
)
"""Event-path rows with rod readings (R12 / R14 .. R16 family) at offsets no batch runs."""
EVENT_SETTINGS = ("VBJ", "VBH", "VBJ0")
R79_SETTINGS = ("VBJ", "VBH")
CANDIDATE_PREFIX = "cand=current#"
R79_LEVEL = "L2"
EXPECTED = {("event", "VBJ"): "equal", ("event", "VBH"): "truth_zero_monitor_positive",
            ("event", "VBJ0"): "equal", ("r79", "VBJ"): "equal", ("r79", "VBH"): "truth_zero"}
"""4a-3 5.1 table: equal = 1 = 2 > 0; truth_zero = 1 = 0 (with 2 > 0 for the event VBH run)."""
EXIT_DONE, EXIT_MISSED, EXIT_NOT_JUDGEABLE, EXIT_ERROR = 0, 1, 2, 3


class Stop(Exception):
    """A not-judgeable condition (exit 2)."""


def normalised_job(job: dict) -> str:
    """4a-3 5.1: ``job`` without the setting and the run keys, as sorted JSON."""
    return json.dumps({k: v for k, v in job.items() if k not in RUNTIME_KEYS}, sort_keys=True)


def plain_key(key: str) -> str:
    return key[len(CANDIDATE_PREFIX):] if key.startswith(CANDIDATE_PREFIX) else key


def judged_union(main_jsonl: Path, baseline_folder: Path, dg3: dict) -> dict:
    """The event-path job union (normalised) and the Dg-3 key union (plain keys)."""
    import run_v5

    run_v5.P3_HASH_SOURCE_OVERRIDE[0] = main_jsonl
    jobs = {name: {normalised_job(job) for job in run_v5.batch_jobs(name)}
            for name in JUDGED_BATCHES}
    baseline = compare.Baseline(baseline_folder)
    rows = [row for name in baseline.hashes if name.endswith(".jsonl")
            for row in baseline.rows(name)]
    jobs["baseline_221456d"] = {normalised_job(row["job"]) for row in rows}
    union = set().union(*jobs.values())
    dg3_keys = {plain_key(run["key"]) for run in dg3["results"]}
    return {"event_union": union, "dg3_keys": dg3_keys,
            "sizes": {name: len(found) for name, found in jobs.items()},
            "union_size": len(union), "dg3_key_count": len(dg3_keys)}


def select(main_jsonl: Path, baseline_folder: Path, dg3: dict, noise: dict) -> dict:
    """The ``select`` output (module docstring).

    Raises:
        Stop: No event candidate or no r79 key outside the union.
    """
    union = judged_union(main_jsonl, baseline_folder, dg3)
    proof = [{"job": job, "in_union": normalised_job(job) in union["event_union"]}
             for job in EVENT_CANDIDATES]
    event_job = next((row["job"] for row in proof if not row["in_union"]), None)
    if event_job is None:
        raise Stop("no event-path candidate outside the judged union (4a-3 5.1: 확인 필요)")
    r79_key = next((plain_key(run["key"]) for run in noise["results"]
                    if run.get("level") == R79_LEVEL
                    and plain_key(run["key"]) not in union["dg3_keys"]), None)
    if r79_key is None:
        raise Stop("no L2 noise key outside the Dg-3 135 keys")
    return {"event_job": event_job, "event_candidates": proof, "r79_key": r79_key,
            "r79_key_in_dg3": r79_key in union["dg3_keys"], "union_sizes": union["sizes"],
            "event_union_size": union["union_size"], "dg3_key_count": union["dg3_key_count"],
            "commands": _commands(event_job, r79_key)}


def _commands(event_job: dict, r79_key: str) -> dict:
    script = "04_scripts/04_hydraulic/coupled/jp3_dryrun_evidence.py"
    r79 = "04_scripts/03_control/s8/r79_L3L4_final.py"
    commands = {f"event_{setting}": f"python -I -B {script} run-event --selection <sel.json> "
                f"--setting {setting} --out dryrun_evidence/event_{setting}.jsonl"
                for setting in EVENT_SETTINGS}
    for setting in R79_SETTINGS:
        rod_model = " R79_ROD_MODEL=plant_truth" if setting == "VBJ" else ""
        commands[f"r79_{setting}"] = (
            f"env R79_V5_SETTING={setting}{rod_model} R72_PATH=per_leg python -I -B {r79} "
            f"<root> run dryrun_evidence/r79_{setting}.json --levels {R79_LEVEL} "
            f'--keys "{r79_key}" --workers 1')
    commands["event_job"] = event_job
    return commands


def run_event(selection: dict, setting: str, out: Path) -> None:
    """One event-path run of the selected job (a simulation: the main session runs it)."""
    import run_v5

    job = {**selection["event_job"], "setting": setting}
    with get_context("spawn").Pool(1, maxtasksperchild=1) as pool:
        record = pool.apply(run_v5.run_one, (job,))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, default=lambda v: v.item() if hasattr(v, "item")
                              else str(v)) + "\n", encoding="utf-8")


def evidence_of(record: dict) -> dict:
    """Only the error flag and the two evidence keys of one output line / r79 result."""
    hydraulics = record.get("hydraulics_record") or {}
    return {"error": "error" in record,
            **{key: hydraulics.get(key) for key in ROD_READING_EVIDENCE_KEYS}}


def meets(expectation: str, evidence: dict) -> bool | None:
    """4a-3 5.1 expectation of one run (None: the keys are missing)."""
    truth, monitor = (evidence.get(key) for key in ROD_READING_EVIDENCE_KEYS)
    if evidence["error"] or truth is None or monitor is None:
        return None
    if expectation == "equal":
        return truth == monitor > 0
    if expectation == "truth_zero_monitor_positive":
        return truth == 0 and monitor > 0
    return truth == 0


def summarize(event_files: dict[str, Path], r79_files: dict[str, Path]) -> tuple[dict, int]:
    """The ``summarize`` output and its exit code."""
    rows, code = [], EXIT_DONE
    for (path_kind, setting), expectation in EXPECTED.items():
        files = event_files if path_kind == "event" else r79_files
        path = files.get(setting)
        if path is None or not path.is_file():
            rows.append({"run": f"{path_kind}_{setting}", "output": "missing"})
            code = EXIT_NOT_JUDGEABLE
            continue
        records = (_read_lines(path) if path_kind == "event"
                   else json.loads(path.read_text(encoding="utf-8"))["results"])
        evidence = [evidence_of(record) for record in records]
        results = [meets(expectation, item) for item in evidence]
        rows.append({"run": f"{path_kind}_{setting}", "expected": expectation,
                     "evidence": evidence, "meets": results})
        if len(records) != 1 or None in results:
            code = EXIT_NOT_JUDGEABLE
        elif not all(results) and code == EXIT_DONE:
            code = EXIT_MISSED
    return {"rows": rows}, code


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _pairs(values: list[str]) -> dict[str, Path]:
    """``SETTING=path`` arguments."""
    out = {}
    for value in values:
        setting, _, path = value.partition("=")
        out[setting] = Path(path)
    return out


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    chosen = commands.add_parser("select")
    chosen.add_argument("--out", type=Path, required=True)
    for name in ("main-jsonl", "baseline", "dg3", "noise"):
        chosen.add_argument(f"--{name}", type=Path, required=True)
    event = commands.add_parser("run-event")
    event.add_argument("--selection", type=Path, required=True)
    event.add_argument("--setting", choices=EVENT_SETTINGS, required=True)
    event.add_argument("--out", type=Path, required=True)
    summary = commands.add_parser("summarize")
    summary.add_argument("--selection", type=Path, required=True)
    summary.add_argument("--out", type=Path, required=True)
    summary.add_argument("--event", nargs="*", default=[])
    summary.add_argument("--r79", nargs="*", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"{args.out} exists (a new output never overwrites one)")
    try:
        if args.command == "select":
            report = select(args.main_jsonl, args.baseline,
                            json.loads(args.dg3.read_text(encoding="utf-8")),
                            json.loads(args.noise.read_text(encoding="utf-8")))
            code = EXIT_DONE
        elif args.command == "run-event":
            run_event(json.loads(args.selection.read_text(encoding="utf-8")), args.setting,
                      args.out)
            print(json.dumps({"status": "done", "out": str(args.out)}))
            return EXIT_DONE
        else:
            report, code = summarize(_pairs(args.event), _pairs(args.r79))
    except (Stop, compare.NotJudgeable) as exc:
        report, code = {"stop": str(exc)}, EXIT_NOT_JUDGEABLE
    except (OSError, KeyError, ValueError) as exc:
        report, code = {"error": f"{type(exc).__name__}: {exc}"}, EXIT_ERROR
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
    status = {EXIT_DONE: "done", EXIT_MISSED: "missed", EXIT_NOT_JUDGEABLE: "not_judgeable",
              EXIT_ERROR: "error"}[code]
    print(json.dumps({"status": status, "out": str(args.out)}))
    return code


if __name__ == "__main__":
    sys.exit(main())
