"""K-2 V-5 flattener: the existing acceptance-step verdicts as flat rows for ``v5_bundle``.

``k2_touch_creep_rules.md`` 3.4 judges V-5 with the stored criteria (``touch_phase/acceptance/criteria.md``,
"each script's existing verdict as it is"). Both judge paths (``k2_judge.py``, ``k2_recount.py``) read flat rows
(``key``, ``pass``; g8 also ``ready`` and ``faults``). This tool only moves the existing per-row verdicts of the
step outputs into that form; it decides nothing itself:

==============  ============================================  ==================================================
bundle          source files (one arm folder)                 row verdict taken from
==============  ============================================  ==================================================
grid            grid_r67_main, grid_r67_top, grid_r69_top,    ``results[].runs[].pass`` (``acc_judge.event_runs``;
                grid_r69_bottom (.json)                       an errored result is a row with ``pass`` false)
soil            soil_A.json                                   the same, ``|two`` keys only (acc_judge soil)
regression      clip_harness, clip_p0, clip_x426_C,           ``acc_judge.flat_verdicts`` + ``is_good``; clip_A by
                clip_x426_D, clip_A, clip_r79_L1L2_judgement  ``event_runs``; the r79 L1/L2 judgement ``runs[].pass``
                                                              (clip_r79_L3L4 is record only in acc_judge: not a row)
d8              d8_both.json                                  ``acc_judge.judge_d8`` row conditions (error, fails,
                                                              fault, below 14.41 kN, attitude > 0.2, READY > 100 s)
noise_L2        r79_L1L2_judgement.json                       ``runs[].pass`` of the L2 rows without S1@FL / S1@FR
                                                              (``acc_judge.noise_verdict``)
ps7             ps7.json or ps7_E.json (run_ps7 --out)        ``[].pass`` (``r68.run_job``); ``controller_tag`` /
                                                              ``touch_creep_latch`` carried along
g8_safe_stop    g8_jobs1, g8_jobs3, g8_jobs5 (.jsonl)         ``pass``; ``ready`` = ``final == "ready"``; ``faults``
                                                              = ``warn_fault`` names starting with FAULT
==============  ============================================  ==================================================

The r79 judgement files are the outputs of ``04_scripts/03_control/s8/r79_sensor_judge.py judge <out> <run>``
(as ``acc_judge.r79_judge``); without them the tool stops with that command, unless ``--run-r79-judge`` lets it
run the judge itself with this interpreter.

Usage (python-dev or dynamics-dev; scipy for acc_judge)::

    python -I -B k2_v5_flatten.py --arm-dir runs/v5/off --out-dir runs/v5/off/flat
        [--checkout <run checkout>] [--source <bundle>:<part>=<file> ...] [--run-r79-judge]

Writes ``<out-dir>/<bundle>.json`` (``{"meta", "runs"}``) per bundle and ``<out-dir>/flatten_summary.json``.
Exit 0 written, 2 input error (missing or unreadable source, existing output), 3 internal error. The last stdout
line is JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ACCEPTANCE_DIR = ROOT / "04_scripts" / "03_control" / "touch_phase" / "acceptance"
GUARD_KN = 14.41
"""acc_judge ``GUARD_KN`` (F_min + 5 kN)."""
D8_ATTITUDE_LIMIT_DEG = 0.2
D8_READY_LIMIT_S = 100.0
S1_FRONT = ("S1@FL", "S1@FR")
SOURCES: dict[str, dict[str, tuple[str, ...]]] = {
    "grid": {"grid_r67_main": ("grid_r67_main.json",), "grid_r67_top": ("grid_r67_top.json",),
             "grid_r69_top": ("grid_r69_top.json",), "grid_r69_bottom": ("grid_r69_bottom.json",)},
    "soil": {"soil_A": ("soil_A.json",)},
    "regression": {"clip_harness": ("clip_harness.json",), "clip_p0": ("clip_p0.json",),
                   "clip_x426_C": ("clip_x426_C.json",), "clip_x426_D": ("clip_x426_D.json",),
                   "clip_A": ("clip_A.json",), "clip_r79_L1L2": ("clip_r79_L1L2_judgement.json",)},
    "d8": {"d8": ("d8_both.json",)},
    "noise_L2": {"r79_L1L2": ("r79_L1L2_judgement.json",)},
    "ps7": {"ps7": ("ps7.json", "ps7_E.json")},
    "g8_safe_stop": {"g8_jobs1": ("g8_jobs1.jsonl",), "g8_jobs3": ("g8_jobs3.jsonl",),
                     "g8_jobs5": ("g8_jobs5.jsonl",)},
}
"""bundle -> part -> accepted file names, looked up in the arm folder and its sub-folder named after the
bundle family (``grid/``, ``regression/``, ``soil/``, ``d8/``, ``noise/``) as in the acceptance layout."""
SUBFOLDERS = {"grid": "grid", "soil": "soil", "regression": "regression", "d8": "d8", "noise_L2": "noise"}
R79_RUN_OF_JUDGEMENT = {"clip_r79_L1L2_judgement.json": "clip_r79_L1L2.json",
                        "r79_L1L2_judgement.json": "r79_L1L2.json"}
EXIT_WRITTEN, EXIT_INPUT, EXIT_INTERNAL = 0, 2, 3


class InputError(Exception):
    """A source is missing or unreadable (exit 2)."""


def _acc_judge():
    if str(ACCEPTANCE_DIR) not in sys.path:
        sys.path.insert(0, str(ACCEPTANCE_DIR))
    import acc_judge

    return acc_judge


# ------------------------------------------------------------------------------- reading
def _load(path: Path):
    try:
        if path.suffix == ".jsonl":
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"{path}: {exc}") from exc


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locate(arm_dir: Path, bundle: str, part: str, overrides: dict[str, Path]) -> Path | None:
    """The source file of one part: an override, the arm folder, or its bundle sub-folder."""
    override = overrides.get(f"{bundle}:{part}")
    if override is not None:
        return override
    folders = [arm_dir]
    if bundle in SUBFOLDERS:
        folders.append(arm_dir / SUBFOLDERS[bundle])
    for name in SOURCES[bundle][part]:
        for folder in folders:
            if (folder / name).is_file():
                return folder / name
    return None


# ------------------------------------------------------------------------------- per bundle
def _event_rows(doc: dict, prefix: str, keep=lambda key: True) -> list[dict]:
    """``acc_judge.event_runs``: one row per run (errored results: one row, ``pass`` false)."""
    rows = []
    for key, run in _acc_judge().event_runs(doc).items():
        if not keep(key):
            continue
        if len(key) == 2:
            rows.append({"key": f"{prefix}|{key[0]}|error", "pass": False, "error": True})
            continue
        rows.append({"key": f"{prefix}|" + "|".join(str(item) for item in key), "pass": bool(run.get("pass")),
                     "commands_sha256": run.get("commands_sha256")})
    return rows


def _flat_rows(doc: dict, prefix: str) -> list[dict]:
    """``acc_judge.flat_verdicts`` + ``is_good`` (wrapper, H8 and x426 formats)."""
    acc_judge = _acc_judge()
    return [{"key": f"{prefix}|{key}", "pass": bool(acc_judge.is_good(verdict)), "verdict": verdict}
            for key, verdict in acc_judge.flat_verdicts(doc).items()]


def _r79_rows(doc: dict, prefix: str, *, l2_without_s1_front: bool) -> list[dict]:
    """``runs[]`` of an r79 judgement (``acc_judge.noise_verdict`` filter for the noise bundle)."""
    rows = []
    for run in doc["runs"]:
        if l2_without_s1_front and (run["level"] != "L2" or any(m in run["inner"] for m in S1_FRONT)):
            continue
        rows.append({"key": f"{prefix}|{run['key']}", "pass": bool(run["pass"])})
    return rows


def d8_row_pass(run: dict) -> bool:
    """The row conditions of ``acc_judge.judge_d8`` (its ``bad`` lists): a row passes when it is in none."""
    if "error" in run:
        return False
    return not (run.get("fails") or run.get("fault") or run["min_true_cyl_force_kN"] < GUARD_KN
                or run["ss_true_att_deg_maxabs"] > D8_ATTITUDE_LIMIT_DEG
                or not run.get("t_ready_s") or run["t_ready_s"] > D8_READY_LIMIT_S)


def _d8_rows(doc: dict) -> list[dict]:
    return [{"key": f"d8|{run['id']}", "pass": d8_row_pass(run)} for run in doc["runs"]]


def _ps7_rows(doc: list) -> list[dict]:
    return [{"key": f"ps7|{row['key']}" if not str(row["key"]).startswith("ps7|") else row["key"],
             "pass": bool(row.get("pass")) and "error" not in row,
             "controller_tag": row.get("controller_tag"), "touch_creep_latch": row.get("touch_creep_latch")}
            for row in doc]


def _g8_rows(lines: list[dict]) -> list[dict]:
    rows = []
    for line in lines:
        faults = [str(name) for name in line.get("warn_fault") or [] if str(name).startswith("FAULT")]
        rows.append({"key": f"{line['tag']}|{line['key']}", "pass": bool(line.get("pass")) and not line.get("error"),
                     "ready": str(line.get("final")).lower() == "ready", "faults": faults,
                     "controller_tag": line.get("controller_tag"),
                     "touch_creep_latch": line.get("touch_creep_latch")})
    return rows


def rows_of(bundle: str, part: str, doc) -> list[dict]:
    """Flat rows of one source (module docstring table)."""
    if bundle == "grid":
        return _event_rows(doc, part)
    if bundle == "soil":
        return _event_rows(doc, part, keep=lambda key: key[0].endswith("|two"))
    if bundle == "regression":
        if part == "clip_A":
            return _event_rows(doc, part)
        if part == "clip_r79_L1L2":
            return _r79_rows(doc, part, l2_without_s1_front=False)
        return _flat_rows(doc, part)
    if bundle == "d8":
        return _d8_rows(doc)
    if bundle == "noise_L2":
        return _r79_rows(doc, part, l2_without_s1_front=True)
    if bundle == "ps7":
        return _ps7_rows(doc)
    if bundle == "g8_safe_stop":
        return _g8_rows(doc)
    raise InputError(f"unknown bundle {bundle!r}")


# ------------------------------------------------------------------------------- r79 judge
def run_r79_judge(judgement: Path, checkout: Path) -> None:
    """``acc_judge.r79_judge``: the checkout's ``r79_sensor_judge.py judge <out> <run>`` with this interpreter."""
    run_file = judgement.with_name(R79_RUN_OF_JUDGEMENT[judgement.name])
    if not run_file.is_file():
        raise InputError(f"no r79 run file {run_file} for {judgement.name}")
    script = checkout / "04_scripts" / "03_control" / "s8" / "r79_sensor_judge.py"
    done = subprocess.run([sys.executable, "-I", "-B", str(script), "judge", str(judgement), str(run_file)],
                          capture_output=True, text=True, timeout=1800, check=False)
    if done.returncode:
        raise InputError(f"r79 judge failed for {run_file}: {done.stderr[-800:]}")


def _r79_judge_command(arm_dir: Path, bundle: str, checkout: Path) -> str:
    name = SOURCES[bundle]["clip_r79_L1L2" if bundle == "regression" else "r79_L1L2"][0]
    run_name = R79_RUN_OF_JUDGEMENT[name]
    return (f"<python> -I -B {checkout / '04_scripts/03_control/s8/r79_sensor_judge.py'} judge "
            f"{arm_dir / name} {arm_dir / run_name}")


# ------------------------------------------------------------------------------- CLI
def flatten(arm_dir: Path, out_dir: Path, overrides: dict[str, Path], *, checkout: Path,
            bundles: list[str], run_judge: bool) -> dict:
    summary = {"arm_dir": str(arm_dir), "bundles": {}}
    for bundle in bundles:
        rows, sources = [], {}
        for part in SOURCES[bundle]:
            path = locate(arm_dir, bundle, part, overrides)
            if path is None and run_judge and part in ("clip_r79_L1L2", "r79_L1L2"):
                path = arm_dir / SOURCES[bundle][part][0]
                run_r79_judge(path, checkout)
            if path is None:
                hint = (f" (run {_r79_judge_command(arm_dir, bundle, checkout)})"
                        if part in ("clip_r79_L1L2", "r79_L1L2") else "")
                raise InputError(f"{bundle}:{part}: no {SOURCES[bundle][part]} in {arm_dir}{hint}")
            part_rows = rows_of(bundle, part, _load(path))
            sources[part] = {"path": str(path), "sha256": _sha256(path), "rows": len(part_rows)}
            rows += [{**row, "part": part} for row in part_rows]
        keys = [row["key"] for row in rows]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise InputError(f"{bundle}: duplicate keys {duplicates[:5]}")
        target = out_dir / f"{bundle}.json"
        meta = {"tool": "k2_v5_flatten", "bundle": bundle, "sources": sources, "rows": len(rows),
                "failed": sum(not row["pass"] for row in rows)}
        target.write_text(json.dumps({"meta": meta, "runs": rows}, indent=1), encoding="utf-8")
        summary["bundles"][bundle] = {"file": str(target), "rows": len(rows), "failed": meta["failed"]}
    (out_dir / "flatten_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def _overrides(items: list[str]) -> dict[str, Path]:
    out = {}
    for item in items:
        name, _, path = item.partition("=")
        bundle, _, part = name.partition(":")
        if not path or bundle not in SOURCES or part not in SOURCES[bundle]:
            raise InputError(f"--source {item!r}: expected <bundle>:<part>=<file>")
        out[name] = Path(path)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--checkout", type=Path, default=ROOT, help="checkout of r79_sensor_judge.py")
    parser.add_argument("--source", action="append", default=[], help="<bundle>:<part>=<file> override")
    parser.add_argument("--bundles", default=",".join(SOURCES), help="comma list (default all)")
    parser.add_argument("--run-r79-judge", action="store_true",
                        help="run r79_sensor_judge for a missing r79 judgement (acc_judge.r79_judge)")
    args = parser.parse_args(argv)
    try:
        bundles = [name for name in args.bundles.split(",") if name]
        unknown = sorted(set(bundles) - set(SOURCES))
        if unknown:
            raise InputError(f"--bundles: unknown {unknown}")
        targets = [args.out_dir / f"{bundle}.json" for bundle in bundles]
        existing = [str(path) for path in targets if path.exists()]
        if existing:
            raise InputError(f"outputs exist (new files only): {existing}")
        args.out_dir.mkdir(parents=True, exist_ok=True)
        summary = flatten(args.arm_dir, args.out_dir, _overrides(args.source), checkout=args.checkout,
                          bundles=bundles, run_judge=args.run_r79_judge)
    except InputError as exc:
        print(json.dumps({"exit": EXIT_INPUT, "error": str(exc)}))
        return EXIT_INPUT
    except Exception as exc:  # contract: internal error = exit 3 with the traceback
        print(traceback.format_exc()[-3000:], file=sys.stderr)
        print(json.dumps({"exit": EXIT_INTERNAL, "error": repr(exc)}))
        return EXIT_INTERNAL
    print(json.dumps({"exit": EXIT_WRITTEN, "bundles": {k: v["rows"] for k, v in summary["bundles"].items()}}))
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main())
