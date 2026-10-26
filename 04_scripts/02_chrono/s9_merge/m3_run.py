"""M-3 (control spec rev. 59 295): one Chrono case with the C2 soil response on / off.

Usage (Chrono-dev python, any cwd)::

    python -I -X utf8 -u 04_scripts/02_chrono/s9_merge/m3_run.py <case_key> <on|off> <out_root>

``on``  = the R8 preset as installed (``C2Config.with_10hz_d1()``: soil response on, re-approach
          time limit 10 s, spec rev. 57 285 / 0400274).
``off`` = the same preset with ``soil.enable`` False **and**
          ``r8.lifted_reapproach.max_duration_s`` None, i.e. the revision-56 controller that is on
          master (the merge question is whether the branch preset changes any command).

Case keys (:data:`CASES`): L1-R rigid floor bundle-C definitions (``run_S6C.py``) and one S8
L2b-NSC rigid-floor re-approach gate case (``run_S8C.py`` ``E_RE1bF_Fs0``, c37 C_gate).

Outputs ``<out_root>/<case_key>__<variant>/``: the runner files (record/, r8_series.npz,
controller_events.json, result.json) + ``m3.json`` (command SHA-256, soil meta, config check).
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import traceback
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHRONO = HERE.parent
ROOT = CHRONO.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(CHRONO))

import run_S6C as s6c  # noqa: E402  (sets the L1-R env, inserts ROOT/03_src)

CASES = {
    "flat": ("L1", "M3_D8_top_flat_b1.0"),
    "rpB": ("L1", "M3_D8_top_rpB_b1.0"),
    "roll55": ("L1", "C1_D8_top_roll5.5_b1.6"),
    "re1bf_l1": ("L1", "C1_RE1bF_top_flat_dropRR30"),
    "s8_re1bf": ("L2b", "E_RE1bF_Fs0"),
}


def l1_case(case_id: str):
    """Bundle-C case; the two ``M3_`` ids are the D8 definition on flat / rpB at beta 1.0."""
    if case_id.startswith("M3_D8_top_"):
        floor = case_id.removeprefix("M3_D8_top_").removesuffix("_b1.0")
        sc = replace(s6c._d8("top", floor), case_id=case_id)
        return s6c.BundleCCase(case_id, "C-1", sc, beta_GPa=1.0,
                               notes=("M-3 (spec rev. 59 295) D8 top beta 1.0",))
    return s6c.case_table()[case_id]


def patch_controller(variant: str) -> dict:
    """Wrap ``run_S6C.controller_config`` (also used by ``run_S8C._controller``)."""
    original = s6c.controller_config
    seen: dict = {}

    def wrapped(params, case):
        config = original(params, case)
        if variant == "off":
            lr = replace(config.r8.lifted_reapproach, max_duration_s=None)
            config = replace(config, soil=replace(config.soil, enable=False),
                             r8=replace(config.r8, lifted_reapproach=lr))
        elif variant != "on":
            raise ValueError(variant)
        seen["soil_enable"] = bool(config.soil.enable)
        seen["reapproach_max_duration_s"] = config.r8.lifted_reapproach.max_duration_s
        seen["soil_settings"] = config.soil.to_meta()
        return config

    s6c.controller_config = wrapped
    return seen


def array_sha(a) -> str:
    import numpy as np

    return hashlib.sha256(np.ascontiguousarray(np.asarray(a, dtype=np.float64)).tobytes()).hexdigest()


def main(argv: list[str]) -> int:
    key, variant, out_root = argv[0], argv[1], Path(argv[2])
    duration = float(argv[3]) if len(argv) > 3 else None  # smoke only
    engine, case_id = CASES[key]
    case_dir = out_root / f"{key}__{variant}"
    case_dir.mkdir(parents=True, exist_ok=True)
    from outrigger_sim import hostcpu

    placement = hostcpu.place_process("pcore")
    import outrigger_sim

    src = Path(outrigger_sim.__file__).resolve()
    if not src.is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"outrigger_sim imported from {src}, not from the worktree {ROOT}")
    seen = patch_controller(variant)
    wall0 = time.perf_counter()
    if engine == "L1":
        case = l1_case(case_id)
        summary, run_meta = s6c.job_bundle_c(case, case_dir, duration_s=duration)
    else:
        import run_S8C as s8c

        if s8c.s6c is not s6c:
            raise RuntimeError("run_S8C imported a second run_S6C module: patch would not apply")
        case = s8c.case_table()[case_id]
        summary, run_meta = s8c.job_l2b_s8(case, case_dir, duration_s=duration)
    wall = time.perf_counter() - wall0
    (case_dir / "result.json").write_text(
        json.dumps(s6c._plain(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    import numpy as np

    r8 = np.load(case_dir / s6c.R8_SERIES_NAME, allow_pickle=False)
    events = json.loads((case_dir / "controller_events.json").read_text("utf-8"))
    modules = sorted({str(Path(m.__file__).resolve()) for m in list(sys.modules.values())
                      if getattr(m, "__file__", None) and "outrigger" in str(m.__file__)})
    foreign = [m for m in modules if not Path(m).is_relative_to(ROOT.resolve())]
    meta = summary.get("controller_meta", {})
    out = {
        "case_key": key, "case_id": case_id, "engine": engine, "variant": variant,
        "config_seen": seen, "placement": placement, "wall_s": wall,
        "outrigger_sim_file": str(src), "foreign_project_modules": foreign,
        "n_periods": int(len(r8["t"])),
        "sha256_issued_u": array_sha(r8["issued_u"]),
        "sha256_computed_u": array_sha(r8["computed_u"]),
        "sha256_events": hashlib.sha256(json.dumps(events).encode("utf-8")).hexdigest(),
        "ready_t_s": summary.get("ready_t_s"),
        "phases": summary.get("phases"),
        "soil": meta.get("soil"),
        "events_soil": [e for e in events if any(k in e for k in (
            "soil_mode_start", "crawler_liftoff_confirmed", "INFO_CLEARANCE_BIAS",
            "WARN_CRAWLER_LIFTOFF_UNCONFIRMED", "WARN_WEIGHT_MISMATCH",
            "WARN_LEG_REAPPROACH_NO_CONTACT"))],
        "events_reapproach": [e for e in events if "reapproach" in e],
    }
    (case_dir / "m3.json").write_text(json.dumps(s6c._plain(out), indent=1), encoding="utf-8")
    print(f"M3 {key} {variant} done wall={wall:.0f}s n={out['n_periods']} "
          f"sha={out['sha256_issued_u'][:16]}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:
        traceback.print_exc()
        sys.exit(1)
