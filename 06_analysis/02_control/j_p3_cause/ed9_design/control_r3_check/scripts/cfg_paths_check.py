"""Edition 9 R3 pre-check (control-expert, 2026-11-28; not a judgement, no simulation run).

Builds, in one process with the edition 9 C-m switch installed (``verdict_runs.install_d1_median``
as the run_v5 pool initializer does), the C2 configs of every controller factory the v5 harness
uses, and of every setting named by the sealed edition 8 key files and the edition 9 batches,
through the real functions of the given worktree (``preset_config``, ``apply_controller_options``).
Prints which D1'' crawler rule each config takes in ``C2Controller._is_crawler_lifted_for_d1``:
``loc_rule`` (soil response on: LOC confirmed and no re-contact suspicion) or ``phase_rule``.

Reads job definitions only (``lines[*].job.setting`` of the key files); no result file is opened.

Usage (dynamics-dev, ``python -I -B``)::

    python cfg_paths_check.py --worktree <C9 worktree> --keys-dir <keys_seal_41e107e9>
        --numba-cache <new folder> --out <json>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

RUN_V5_RELATIVE = Path("04_scripts") / "04_hydraulic" / "coupled" / "run_v5.py"
KEY_FILES = ("census_keys_ed8.json", "heldout_g_ed8.json")


def _load_run_v5(worktree: Path):
    spec = importlib.util.spec_from_file_location("run_v5", worktree / RUN_V5_RELATIVE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_v5"] = module
    spec.loader.exec_module(module)
    return module


def _key_settings(keys_dir: Path) -> dict[str, list[str]]:
    out = {}
    for name in KEY_FILES:
        document = json.loads((keys_dir / name).read_text(encoding="utf-8"))
        out[name] = sorted({line["job"]["setting"] for line in document["lines"]})
    return out


def _rule_of(config) -> str:
    return "loc_rule" if config.soil.enable else "phase_rule"


def _describe(config, tag=None) -> dict:
    return {"soil.enable": bool(config.soil.enable),
            "imu_residual_median_check": bool(config.two_pressure.imu_residual_median_check),
            "d1_crawler_rule": _rule_of(config), "controller_tag": tag}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--keys-dir", type=Path, required=True)
    parser.add_argument("--numba-cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        print(json.dumps({"status": "input_error", "reason": f"{args.out} exists"}))
        return 2
    os.environ["NUMBA_CACHE_DIR"] = str(args.numba_cache)
    os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
    run_v5 = _load_run_v5(args.worktree)
    import verdict_runs  # noqa: I001 - after run_v5 put the worktree paths first

    verdict_runs.install_d1_median(True)
    import s9_soil_closed_loop as sl
    import s9_soil_slope as slope

    from outrigger_sim.control import c2 as c2_module
    from outrigger_sim.hydraulics import v5_options

    cl, c2, _ = sl._imports()
    v_max = verdict_runs.load_params().v_max  # the harness params module, as verdict_runs
    report: dict = {"worktree": str(args.worktree),
                    "c2_file": c2_module.__file__, "run_v5_file": run_v5.__file__,
                    "cl_file": cl.__file__}
    factories = {}
    for contact in ("COMBINED", "PRESSURE"):
        config = cl.preset_config(getattr(c2.ContactJudge, contact), with_imu_samples=True,
                                  with_reapproach=True)
        factories[f"c2py_r8d1_closed_loop.preset_config({contact})"] = _describe(config)
    factories["s9_soil_closed_loop.reference_config (unpatched factory)"] = _describe(
        sl.reference_config(cl, c2))
    slope._install_patches()
    report["s9_soil_slope_patch_replaces_make_controller"] = (
        sl.make_controller is slope._make_project_controller)
    report["factories"] = factories
    key_settings = _key_settings(args.keys_dir)
    report["key_file_settings"] = key_settings
    batch_settings = {}
    for batch in (*run_v5.D1_MEDIAN_BATCHES, *run_v5.ED9_OFF_TWIN_BATCHES):
        try:
            if batch in run_v5.ED9_JOBS_FILE_BATCHES:
                run_v5.ED8_KEYS_FILE[0] = args.keys_dir / "heldout_g_ed8.json"
            jobs = run_v5.batch_jobs(batch)
            batch_settings[batch] = sorted({job["setting"] for job in jobs})
        except Exception as exc:  # record only
            batch_settings[batch] = f"error {exc!r}"
    report["ed9_batch_settings"] = batch_settings
    report["d1_median_batches"] = list(run_v5.D1_MEDIAN_BATCHES)
    all_settings = sorted({s for names in key_settings.values() for s in names}
                          | {s for names in batch_settings.values() if isinstance(names, list)
                             for s in names})
    base = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True, with_reapproach=True)
    per_setting = {}
    for setting in all_settings:
        _, options = run_v5.options_of(setting)
        config = base if options is None else v5_options.apply_controller_options(
            base, options, v_max, 0.1)
        per_setting[setting] = _describe(config, v5_options.controller_tag(options, config))
    report["settings"] = per_setting
    report["any_phase_rule"] = sorted(name for name, row in
                                      {**factories, **per_setting}.items()
                                      if row["d1_crawler_rule"] == "phase_rule")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"status": "ok", "out": str(args.out),
                      "any_phase_rule": report["any_phase_rule"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
