"""Steps and line counts of the 436.8 harness bundles (rules ``v5_resume_4368_rules.md`` 4.3, 5.1).

Writes one steps file per bundle (the ``make_runner.py`` form ``{"steps": [{id, cwd, cmd, env}]}``,
every step
with a ``resume_k1`` block: bundle, settings, expected tags of 4.1, output of 4.3, counted lines)
and
``steps_h2.json`` (H-1 .. H-10 in one file, the name the rules give), plus ``counts.json``: per
bundle the line
count of 5.1, the count this module derives from the job definitions, and the stop flag S-15. Writes
files
only; it never starts a run.

Commands are the stored ones (``sched_v5all`` / ``v5_r5rerun`` / ``las_t3`` usage) with the 436.8
output names:
the runner scripts of the repository only, no wrapper, no preset keyword, no candidate token (4.2).
Bundles
whose original command needs a session-scratchpad wrapper or whose runner cannot write the 4.3 name
are listed
under ``blocked`` with the reason (``확인 필요``), not as steps.

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/resume_k1_steps.py <out_dir> [--root <checkout>]
      [--workers 24] [--mask 0x0FFFFFFF] [--data-root <folder with 06_analysis results>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v5  # noqa: E402
import u3_judge  # noqa: E402

DYNAMICS_PYTHON = r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B"
PYTHON_DEV = r"C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B"
V5 = "06_analysis/03_hydraulic/coupled/v5"
RESUME = f"{V5}/resume_k1"
LAS_K1 = "06_analysis/02_control/v5_rerun/las_k1"
RV85 = "06_analysis/02_control/s9/rev85"
RV84 = "06_analysis/02_control/s9/rev84"
FIX = "04_scripts/03_control/s9/s9_slope_fix_candidates.py"
B5 = "04_scripts/03_control/s9/b5_baseline_compare.py"
RUN_V5 = "04_scripts/04_hydraulic/coupled/run_v5.py"

TABLE_LINES = {
    "H-0": 360,
    "H-1": 868,
    "H-2": 1,
    "H-3": 2228,
    "H-4": 726 + 242,
    "H-5": 14,
    "H-6": 135,
    "H-7": 135,
    "H-8": 3106,
    "H-9": 812 + 96 + 768,
    "H-10": 462,
}
"""Rules 5.1 line counts (H-4 = U-6 726 + IND_LAS record 242, H-9 = main 812 + pressure_only 96 + grid 768)."""
TAGS_V0_VB = {"V0": "final_C4G2_LAS_K1", "VB": "final_C4G2_P3_LAS_K1"}
U6_TAGS = {"C2": "final_C4G2_P3_LAS_K1", "ABL": "ABL_LAS_K1", "IND": "IND"}
FIX_SUITES = (
    ("slope", "harness", "finB2_harness", True),
    ("h9", "harness", "finB2_h9", True),
    ("h6", "harness", "finB2_harness", False),
    ("g6", "p0", "finB2_p0", False),
    ("g8", "p0", "finB2_p0", False),
    ("p3b", "p0", "finB2_p0", False),
    ("x426b", "harness", "finB2_x426b", False),
)
"""``sched_v5all/gen_steps.py`` suites: (suite, settle hook, ids file, ``--reuse-d1``)."""
MAIN_STAGE1_SETTINGS = ("V0", "V1", "V2", "V3", "L1", "L2", "V4", "V5", "V6", "V7", "V8")
"""H-9: the main batch without VB / LS1 .. LS4 (V0 .. V8, L1, L2)."""
MAIN_REUSE_SETTINGS = ("VB", "LS1", "LS2", "LS3", "LS4")
"""H-10: the main batch VB / LS1 .. LS4."""

BLOCKED = {
    "H-6": "dg3 v4_on: the stored command is the scratchpad wrapper ctrl_v5s3/dg3_run_on.py (patches the "
    "with_10hz_d1 default, 4.2 forbids wrappers; VB now carries ③ itself). The plain runner "
    "r79_L3L4_final.py run --keys <135 dg3 keys> with R79_V5_SETTING=VB is the candidate; it writes "
    "a .json + .partial.jsonl, not h6_dg3_v4on.jsonl (4.3).",
    "H-7": "dg3 off (③ off): VB of run_v5.SETTINGS has ③ on; the stored off arm ran before that "
    "(ctrl_v5s3/dg3_run_off.py). No repository command gives the VB plant with ③ off without a "
    "wrapper or a new setting.",
    "H-8": "noise VB / V0: r79_L3L4_final.py writes r79_*.json (+ .partial.jsonl), not h8_noise.jsonl; "
    "seedext needs the scratchpad wrapper sched_s3/seedext_run.py (job list of seeds 0..24).",
    "H-9 grid": "grid VB (r67_g1_screen.py / r69_g5_screen.py, env R67_*): JSON outputs with results[i].runs[j], "
    "not lines of h9_stage1.jsonl.",
}
"""Bundles without a step here (``확인 필요``): see the report."""


def _step(step_id: str, cmd: str, root: str, meta: dict, env: dict | None = None) -> dict:
    step = {"id": step_id, "cwd": root, "cmd": cmd, "resume_k1": meta}
    if env:
        step["env"] = env
    return step


def _meta(bundle: str, output: str, settings, tags, lines: int | None) -> dict:
    return {
        "bundle": bundle,
        "output": output,
        "settings": list(settings),
        "expected_tags": tags,
        "lines": lines,
    }


def h0_steps(root: str, workers: int, mask: str) -> list[dict]:
    """H-0 T-3K: ``las_t3.py run`` (rules rev5 default, output ``v5/las/t3_k1/``, ``las_targeted_rules_rev5`` 2.6)."""
    cmd = (
        f"{DYNAMICS_PYTHON} 04_scripts/04_hydraulic/coupled/las_t3.py run --workers {workers} "
        f"--affinity {mask}"
    )
    meta = _meta(
        "H-0",
        f"{V5}/las/t3_k1/",
        ("V0", "VB"),
        "las_targeted_rules_rev5 (T-3K)",
        TABLE_LINES["H-0"],
    )
    return [
        _step(
            "h0_t3k", cmd, root, {**meta, "lines_source": "rules 5.1 (las_t3.py list counts them)"}
        )
    ]


def run_v5_step(
    step_id: str,
    batch: str,
    out: str,
    settings,
    root: str,
    workers: int,
    mask: str,
    bundle: str,
    lines: int,
) -> dict:
    settings_arg = "" if settings is None else f" --settings {','.join(settings)}"
    cmd = f"{DYNAMICS_PYTHON} {RUN_V5} {batch} --workers {workers} --mask {mask} --out {out}{settings_arg}"
    shown = _settings_of(batch, settings)
    tags = {s: run_v5_tag(s) for s in shown}
    return _step(step_id, cmd, root, _meta(bundle, out, shown, tags, lines))


def _settings_of(batch: str, settings) -> tuple[str, ...]:
    """The settings a run_v5 step runs (d1: V0 / VB; p3_hash: VB, read from the stored main.jsonl at run time)."""
    if settings is not None:
        return tuple(settings)
    if batch == run_v5.D1_BATCH:
        return ("V0", "VB")
    if batch == run_v5.P3_HASH_BATCH:
        return ("VB",)
    return tuple(sorted({job["setting"] for job in run_v5.batch_jobs(batch)}))


def run_v5_tag(setting: str) -> str:
    """Rules 4.1: ③ settings (VB, LS1 .. LS4) ``final_C4G2_P3_LAS_K1``, the others ``final_C4G2_LAS_K1``."""
    return (
        TAGS_V0_VB["VB"]
        if run_v5.SETTINGS[setting][1].get("extend_start_tracked")
        else TAGS_V0_VB["V0"]
    )


def u3_steps(root: str, workers: int, mask: str) -> list[dict]:
    """H-3: the ``sched_v5all`` U-3 commands with the outputs in ``v5_rerun/las_k1/`` and the D-1 reuse input
    ``resume_k1/h1_d1.jsonl`` (rules 7.1 rev3 part)."""
    expected = {bundle.name: bundle.expected for bundle in u3_judge.BUNDLES}
    steps = []
    for setting in ("V0", "VB"):
        tags = {setting: TAGS_V0_VB[setting]}
        for suite, hook, ids, reuse in FIX_SUITES:
            out = f"{LAS_K1}/u3_{suite}_{setting}.json"
            cmd = (
                f"{DYNAMICS_PYTHON} {FIX} run --suite {suite} --settle-hook {hook} --v5-setting {setting} "
                f"--ids-from {RV85}/{ids}.json --pad B "
                + (f"--reuse-d1 {RESUME}/h1_d1.jsonl " if reuse else "")
                + f"--workers {workers} --affinity {mask} --out {out}"
            )
            steps.append(
                _step(
                    f"u3_{suite}_{setting}",
                    cmd,
                    root,
                    _meta("H-3", out, (setting,), tags, expected[suite]),
                )
            )
        out = f"{LAS_K1}/u3_C_{setting}.json"
        cmd = (
            f"{DYNAMICS_PYTHON} 04_scripts/03_control/s8/r72_g6_screen.py {root} {out} {workers} "
            f"--v5-setting {setting} --ids-from {RV85}/fin_x426_C.json --pad B"
        )
        env = {
            "R72_SET": "x426",
            "R72_PATH": "per_leg",
            "S9_SETTLE_HOOK": "p0",
            "R72_AFFINITY": mask,
        }
        steps.append(
            _step(
                f"u3_C_{setting}",
                cmd,
                root,
                _meta("H-3", out, (setting,), tags, expected["C"]),
                env,
            )
        )
        out = f"{LAS_K1}/u3_D_{setting}.json"
        cmd = (
            f"{DYNAMICS_PYTHON} 04_scripts/03_control/s9/s9_soil_slope.py --groups H8 --v5-setting {setting} "
            f"--ids-from {RV85}/fin_x426_D.json --pad B --workers {workers} --affinity {mask} --out {out}"
        )
        steps.append(
            _step(f"u3_D_{setting}", cmd, root, _meta("H-3", out, (setting,), tags, expected["D"]))
        )
    return steps


def u6_steps(root: str, workers: int, mask: str) -> list[dict]:
    """H-4: U-6 VB (C2, ABL, IND) and the IND_LAS record column (rules rev2 3), outputs in ``las_k1/``."""
    steps = []
    for label, cases_arg, ids, cases, pad, env in (
        ("wide", "wide --official", f"{RV84}/fin2_b5_wide_official.json", 226, "B", None),
        ("main", "all", f"{RV84}/fin_b5_main.json", 16, None, {"R72_PATH": "per_leg"}),
    ):
        pad_arg = f" --pad {pad}" if pad else ""
        for controllers, runs, tags in (
            ("C2,ABL,IND", 3 * cases, U6_TAGS),
            ("IND_LAS", cases, {"IND_LAS": "IND_LAS"}),
        ):
            suffix = "" if controllers != "IND_LAS" else "_IND_LAS"
            out = f"{LAS_K1}/u6_b5_{label}_VB{suffix}.json"
            cmd = (
                f"{DYNAMICS_PYTHON} {B5} run --cases {cases_arg} --controllers {controllers} --v5-setting VB "
                f"--ids-from {ids}{pad_arg} --workers {workers} --affinity {mask} --out {out}"
            )
            steps.append(
                _step(
                    f"u6_{label}_VB{suffix}", cmd, root, _meta("H-4", out, ("VB",), tags, runs), env
                )
            )
    return steps


def stored_main_path(data_root: Path) -> Path:
    return data_root / V5 / "main.jsonl"


def h10_counts(data_root: Path) -> dict:
    """H-10 jobs per part and the distinct job keys of the combined file (run_v5 skips a key already done)."""
    parts = {
        "main": run_v5.select_settings(run_v5.batch_jobs("main"), MAIN_REUSE_SETTINGS),
        "u9_targeted": run_v5.select_settings(run_v5.u9_targeted_jobs(), ("VB",)),
        "item8": run_v5.batch_jobs("item8"),
        "overlap": run_v5.batch_jobs("overlap"),
    }
    main_path = stored_main_path(data_root)
    if main_path.is_file():
        parts["p3_hash"] = [job for _, job in run_v5.p3_hash_jobs(main_path)]
    keys = {run_v5.job_key(job) for jobs in parts.values() for job in jobs}
    return {
        "jobs": {name: len(jobs) for name, jobs in parts.items()},
        "jobs_total": sum(len(jobs) for jobs in parts.values()),
        "distinct_keys": len(keys),
        "p3_hash_source": str(main_path) if main_path.is_file() else "missing (not counted)",
    }


def build(args: argparse.Namespace) -> dict:
    root, w, m = args.root, args.workers, args.mask
    d1_lines = _d1_count()
    h1 = [run_v5_step("h1_d1", "d1", f"{RESUME}/h1_d1.jsonl", None, root, w, m, "H-1", d1_lines)]
    h2 = [
        _step(
            "h2_d1_select",
            f"{PYTHON_DEV} 04_scripts/04_hydraulic/coupled/d1_select.py "
            f"{RESUME}/h2_d1_select.json {RESUME}/h1_d1.jsonl",
            root,
            _meta("H-2", f"{RESUME}/h2_d1_select.json", (), None, 1),
        )
    ]
    u9_v0 = len(run_v5.select_settings(run_v5.u9_targeted_jobs(), ("V0",)))
    h5 = [
        run_v5_step(
            "h5_u9_v0", "u9_targeted", f"{RESUME}/h5_u9_v0.jsonl", ("V0",), root, w, m, "H-5", u9_v0
        )
    ]
    main9 = len(run_v5.select_settings(run_v5.batch_jobs("main"), MAIN_STAGE1_SETTINGS))
    h9 = [
        run_v5_step(
            "h9_main",
            "main",
            f"{RESUME}/h9_stage1.jsonl",
            MAIN_STAGE1_SETTINGS,
            root,
            w,
            m,
            "H-9",
            main9,
        ),
        run_v5_step(
            "h9_pressure_only",
            "pressure_only",
            f"{RESUME}/h9_stage1.jsonl",
            None,
            root,
            w,
            m,
            "H-9",
            len(run_v5.batch_jobs("pressure_only")),
        ),
    ]
    h10_out = f"{RESUME}/h10_reuse_rerun.jsonl"
    h10 = [
        run_v5_step("h10_main", "main", h10_out, MAIN_REUSE_SETTINGS, root, w, m, "H-10", None),
        run_v5_step("h10_u9_vb", "u9_targeted", h10_out, ("VB",), root, w, m, "H-10", None),
        run_v5_step("h10_p3_hash", "p3_hash", h10_out, None, root, w, m, "H-10", None),
        run_v5_step("h10_item8", "item8", h10_out, None, root, w, m, "H-10", None),
        run_v5_step("h10_overlap", "overlap", h10_out, None, root, w, m, "H-10", None),
    ]
    bundles = {
        "H-0": h0_steps(root, w, m),
        "H-1": h1,
        "H-2": h2,
        "H-3": u3_steps(root, w, m),
        "H-4": u6_steps(root, w, m),
        "H-5": h5,
        "H-9": h9,
        "H-10": h10,
    }
    return {
        "bundles": bundles,
        "counts": counts_report(bundles, d1_lines, main9, Path(args.data_root)),
    }


def _d1_count() -> int | None:
    """H-1 jobs from ``d1_rows.jobs()`` (None when the module does not import in this interpreter)."""
    try:
        import d1_rows  # noqa: PLC0415
    except ImportError:
        return None
    return len(d1_rows.jobs())


def counts_report(bundles: dict, d1_lines: int | None, main9: int, data_root: Path) -> dict:
    """Rules 5.1 / S-15: the table count, the derived count and whether they differ, per bundle."""
    derived: dict[str, int | None] = {}
    for name, steps in bundles.items():
        lines = [step["resume_k1"]["lines"] for step in steps]
        derived[name] = None if any(v is None for v in lines) else sum(lines)
    h10 = h10_counts(data_root)
    derived["H-10"] = h10["distinct_keys"]
    derived["H-9"] = None  # grid part blocked (BLOCKED["H-9 grid"])
    out = {}
    for name, table in TABLE_LINES.items():
        value = derived.get(name)
        out[name] = {
            "table": table,
            "derived": value,
            "differs_S15": None if value is None else value != table,
        }
    out["H-9"]["parts"] = {
        "main V0..V8 L1 L2": main9,
        "pressure_only": len(run_v5.batch_jobs("pressure_only")),
        "grid": "blocked",
    }
    out["H-10"]["parts"] = h10
    out["H-1"]["source"] = (
        "d1_rows.jobs()" if d1_lines is not None else "d1_rows not importable here"
    )
    return out


def write(out_dir: Path, built: dict) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    harness = [step for name, steps in built["bundles"].items() if name != "H-0" for step in steps]
    for name, steps in built["bundles"].items():
        path = (
            out_dir / f"steps_bundle_{name.replace('-', '').lower()}.json"
        )  # not steps_h2.json (all of H-1..)
        path.write_text(json.dumps({"steps": steps}, indent=1), encoding="utf-8")
        files[name] = str(path)
    (out_dir / "steps_h2.json").write_text(
        json.dumps({"steps": harness}, indent=1), encoding="utf-8"
    )
    report = {
        "counts": built["counts"],
        "blocked": BLOCKED,
        "files": files,
        "steps_h2": str(out_dir / "steps_h2.json"),
    }
    (out_dir / "counts.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_dir", type=Path)
    parser.add_argument(
        "--root", default=r"C:\workspace\outrigger_control", help="checkout the steps run in"
    )
    parser.add_argument(
        "--data-root", default=str(ROOT), help="folder holding the stored v5/main.jsonl"
    )
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--mask", default="0x0FFFFFFF")
    args = parser.parse_args(argv)
    report = write(args.out_dir, build(args))
    differs = [n for n, c in report["counts"].items() if c["differs_S15"]]
    print(
        json.dumps(
            {"differs_S15": differs, "blocked": sorted(BLOCKED), "steps_h2": report["steps_h2"]}
        )
    )
    return 1 if differs or BLOCKED else 0


if __name__ == "__main__":
    sys.exit(main())
