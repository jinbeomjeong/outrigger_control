"""B1 creep basis (``V5-B1-CREEP``): the 32 harness runs of rules 2.2 with their run records.

Rules: ``06_analysis/02_control/b1/b1_creep_rules.md`` (sealed 2026-11-12,
:data:`RULES_SHA256`).

Bundles (rules 2.2), all on the v5 reduced harness through ``run_v5.run_one`` of the D-1 soil
row ``D1|H-S-0|J2|<T/M/B>|<slope>|K1`` (the preset as it is, no candidate wrapper):

  H-P    C1 .. C5 keys x {VB, V0} x eps {0, 2e-3}, LOC shadow on                         20
  H-W    C6 = the C1 key with the plant mass x 1.1 (spec 422.2), x {VB, V0} x eps {0, 2e-3}  4
  H-M0   C1, C5 keys x {VB, V0} x eps 0, research subclass ``B1MarginZeroC2Controller``
         (E3c10 ``enable`` kept, ``margin_m`` 0; rules 2.4, U-5 (a))                      4
  H-SH0  H-P VB eps 0 of C1, C2, C4, C5 with the LOC shadow off (command-hash pairs, U-7)  4

Every run gets its own spawned worker (``maxtasksperchild=1``, ``chunksize=1``): the shadow,
the period record and the H-M0 subclass are process-wide patches. The B1 period record
(``b1_record.install_period_record``) only reads controller state. The harness pad element is
the continuous Bekker law (``s9_soil_closed_loop.SoilPads``: ``coef = k_c / b_poly + k_phi`` on
the pad area), so its grid factor is ``f = 1`` (rules R-10); each line records that check.

Output (``--out-dir``, default ``06_analysis/03_hydraulic/coupled/v5/b1``):
  ``b1_H.jsonl``   one line per run (appended; finished run ids are skipped)
  ``npz/<run id>.npz``  run record ``b1-run-record/2``: the R-C1 names of rules 6 (``n``,
                   ``load_read_N`` (N, 4), ``att_raw_rad`` (N, 2), ``c_hat_m``,
                   ``c_hat_corner_m`` (N, 4), ``c_target_m``), plus ``t_s``, ``phase``,
                   ``stroke_read_m`` (N, 4), ``att_filt_rad`` (record), ``sink_m`` (N, 4, pad
                   element sinkage at the period instants), ``crawler_clear_true_m``
  ``b1_H.jsonl.identity.json``  checkout, code and environment at the start and the end

Usage (dynamics-dev python.exe, cwd = the checkout, PowerShell, ``OUTRIGGER_LOC_SHADOW=1``)::

    python -I -B 04_scripts/03_control/b1/b1_harness.py [--workers 8] [--mask 0x0FFF0000]
        [--groups H-P,H-W,H-M0,H-SH0] [--runs <id>,<id>] [--out-dir <dir>] [--list]

Exit: 0 done (no error line, no H-SH0 pair whose hash differs from its H-P twin; pairs not run
yet are printed as ``missing``), 1 an error line or a pair hash that differs, 2 input error.
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
import io  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from multiprocessing import get_context  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COUPLED_DIR = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
SHADOW_DIR = ROOT / "04_scripts" / "03_control" / "k2" / "loc_shadow"
for _folder in (HERE, SHADOW_DIR, COUPLED_DIR, ROOT / "03_src"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

RULES_FILE = "b1_creep_rules.md"
RULES_SHA256 = "6b99702ce26d6da28fbfe6473b622c7e51419241916cbc101f795828f498774e"
"""Sealed rules (``b1_creep_rules.sha256``, master ``1ad3e5d``, 2026-11-12)."""
SCHEMA = "b1-harness-line/1"
RECORD_SCHEMA = "b1-run-record/2"
DEFAULT_OUT_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "b1"
JSONL_NAME = "b1_H.jsonl"
NPZ_FOLDER = "npz"

SOIL = "J2"
D1_GROUP = "H-S-0"
CRAWLER_K = 1.0
ROWS: dict[str, tuple[str, str, tuple[float, float]]] = {
    "C1": ("bottom", "fdown-rec", (0.0, 2.8)),
    "C2": ("middle", "fdown-rec", (0.0, 2.8)),
    "C3": ("top", "fdown-rec", (0.0, 2.8)),
    "C4": ("bottom", "diag-rec", (1.925, 1.4)),
    "C5": ("top", "fup-rec", (0.0, -2.8)),
    "C6": ("bottom", "fdown-rec", (0.0, 2.8)),
}
"""Rules 2.1 row -> (auger level, D-1 slope name, Chrono (floor roll, floor pitch) [deg])."""
SLOPE_MATCH_TOL_DEG = 1e-4
"""The D-1 slope floats are rounded to 1e-4 deg (``s9_soil_slope._scaled_slope``)."""
C6_MASS_SCALE = 1.1
SETTINGS = ("VB", "V0")
EPS_TWO = (0.0, 2e-3)
GROUPS = ("H-P", "H-W", "H-M0", "H-SH0")
SHADOW_PAIR_ROWS = ("C1", "C2", "C4", "C5")
MARGIN_ZERO_ROWS = ("C1", "C5")
STORED_META_BLOCKS = ("slope_clearance_margin", "loc_revoke", "diff_sink", "lift_stroke_guard",
                      "pre_loc_lift_pause", "liftoff_window_reapproach", "liftoff_approach_slow")
"""``controller.meta()`` blocks kept on a line (rules M-8 rule activity, record only)."""
GRID_FACTOR_BASIS = ("harness SoilPads: sigma = (k_c / b_poly + k_phi) z^n on the pad area A "
                     "(continuous Bekker, s9_soil_closed_loop.SoilPads); f = 1 (rules R-10)")
EXIT_DONE, EXIT_STOP, EXIT_INPUT = 0, 1, 2
TOOL_FILES = {"b1_harness.py": HERE / "b1_harness.py", "b1_record.py": HERE / "b1_record.py"}

_CAPTURE: dict = {}


# ------------------------------------------------------------------------------------ jobs
def _d1_row_entry(level: str, slope_name: str) -> dict:
    """``D1Row.to_job()`` of the uniform J2 soil row of a level and slope (``d1_rows``).

    Raises:
        LookupError: No such D-1 row.
    """
    import d1_rows

    for row in d1_rows.soil_rows():
        if (row.group == D1_GROUP and row.base == SOIL and row.patch_soil is None
                and row.sink is None and row.level == level and row.slope_name == slope_name
                and row.crawler_k_scale == CRAWLER_K):
            return row.to_job()
    raise LookupError(f"no D-1 row {D1_GROUP} {SOIL} {level} {slope_name}")


def run_id(group: str, row_id: str, setting: str, eps: float) -> str:
    return f"{group}|{row_id}|{setting}|e{eps:g}"


def _job(group: str, row_id: str, setting: str, eps: float, *, mass_scale: float = 1.0,
         is_margin_zero: bool = False, is_shadow_on: bool = True) -> dict:
    level, slope_name, _ = ROWS[row_id]
    return {"b1": {"run_id": run_id(group, row_id, setting, eps), "group": group,
                   "row_id": row_id, "mass_scale": mass_scale, "margin_zero": is_margin_zero,
                   "shadow": is_shadow_on},
            "d1": _d1_row_entry(level, slope_name), "setting": setting, "eps": eps}


def b1_jobs() -> list[dict]:
    """The 32 jobs of rules 2.2 (H-P 20, H-W 4, H-M0 4, H-SH0 4)."""
    jobs = [_job("H-P", row_id, setting, eps) for row_id in ("C1", "C2", "C3", "C4", "C5")
            for setting in SETTINGS for eps in EPS_TWO]
    jobs += [_job("H-W", "C6", setting, eps, mass_scale=C6_MASS_SCALE)
             for setting in SETTINGS for eps in EPS_TWO]
    jobs += [_job("H-M0", row_id, setting, 0.0, is_margin_zero=True)
             for row_id in MARGIN_ZERO_ROWS for setting in SETTINGS]
    jobs += [_job("H-SH0", row_id, "VB", 0.0, is_shadow_on=False) for row_id in SHADOW_PAIR_ROWS]
    return jobs


def slope_mismatches(jobs: list[dict]) -> list[str]:
    """Jobs whose D-1 floor angles differ from the Chrono row floor of rules 2.1."""
    found = []
    for job in jobs:
        _, _, (roll_deg, pitch_deg) = ROWS[job["b1"]["row_id"]]
        d1 = job["d1"]
        if (abs(d1["roll_deg"] - roll_deg) > SLOPE_MATCH_TOL_DEG
                or abs(d1["pitch_deg"] - pitch_deg) > SLOPE_MATCH_TOL_DEG):
            found.append(f"{job['b1']['run_id']}: D-1 ({d1['roll_deg']}, {d1['pitch_deg']}) "
                         f"!= rules ({roll_deg}, {pitch_deg})")
    return found


def run_v5_job(job: dict) -> dict:
    """The ``run_v5.run_one`` job of a B1 job (``mass_scale`` only when it is not 1)."""
    out = {"d1": job["d1"], "eps": job["eps"], "setting": job["setting"]}
    if job["b1"]["mass_scale"] != 1.0:
        out["mass_scale"] = job["b1"]["mass_scale"]
    if job.get("mask") is not None:
        out["mask"] = job["mask"]
    return out


def npz_name(job_run_id: str) -> str:
    return job_run_id.replace("|", "_").replace(".", "p") + ".npz"


# ------------------------------------------------------------------------------------ worker
def _capture_d1_record() -> None:
    """Keep the plant, controller and harness record that ``d1_runs`` judges (worker only)."""
    import d1_runs

    original = d1_runs.d1_record

    def d1_record(row, setting_name, eps, result, plant, controller, harness):
        _CAPTURE.update(plant=plant, controller=controller, harness=harness)
        return original(row, setting_name, eps, result, plant, controller, harness)

    d1_runs.d1_record = d1_record


def _install_worker_patches(b1: dict) -> None:
    """Shadow (on-jobs), period record, then the H-M0 subclass (it must wrap the recorded
    class and be the base that ``verdict_runs.install_logged_controller`` extends)."""
    import b1_record

    from outrigger_sim.control import c2

    if b1["shadow"]:
        import loc_anchor_shadow as shadow

        shadow.install()
    b1_record.install_period_record(c2.C2Controller)
    if b1["margin_zero"]:
        c2.C2Controller = b1_record.make_margin_zero_class(c2.C2Controller)
    _capture_d1_record()


def _soil_log_arrays(period_s: float) -> dict[int, tuple[np.ndarray, float | None]]:
    """Period index -> (pad sinkage [m] (4,), rut clearance [m]) of ``s9_soil_slope``'s log."""
    import s9_soil_slope as slope

    log = slope._CAP.get("log") or {}
    sink_mm = log.get("sink_mm") or []
    rut_mm = log.get("rut_clear_mm") or []
    out: dict[int, tuple[np.ndarray, float | None]] = {}
    for index, t_s in enumerate(log.get("t_s") or []):
        sink = (np.asarray(sink_mm[index], dtype=float) / 1e3 if index < len(sink_mm)
                else np.full(4, np.nan))
        rut = rut_mm[index] / 1e3 if index < len(rut_mm) and rut_mm[index] is not None else None
        out[round(float(t_s) / period_s)] = (sink, rut)
    return out


def run_record_arrays(controller) -> dict[str, np.ndarray]:
    """``b1-run-record/2`` arrays of the finished run of this worker."""
    import b1_record

    arrays = b1_record.period_record_arrays(controller)
    soil = _soil_log_arrays(float(controller.config.period_s))
    sink = np.full((len(arrays["n"]), 4), np.nan)
    rut = np.full(len(arrays["n"]), np.nan)
    for index, n in enumerate(arrays["n"]):
        if int(n) in soil:
            sink[index] = soil[int(n)][0]
            rut_value = soil[int(n)][1]
            rut[index] = np.nan if rut_value is None else rut_value
    return {**arrays, "sink_m": sink, "crawler_clear_true_m": rut}


def soil_model_check(plant, soil_key: str = SOIL) -> dict:
    """Rules R-10: the harness pad element law is the continuous Bekker law (f = 1) of the
    soil set ``soil_key`` on the pad B areas."""
    soil = getattr(plant, "soil", None)
    if soil is None:
        return {"is_continuous_bekker": False, "reason": "rigid floor"}
    import s9_soil_closed_loop as sl

    soil_set = sl.SOIL_SETS[soil_key]["chrono"]
    legs = next(v for v in sl.PAD_VARIANTS.values() if v["label"] == "B")["legs"]
    b_poly = np.array([legs[name]["bekker_b_m"] for name in sl.LEGS], dtype=float)
    area = np.array([legs[name]["bottom_area_m2"] for name in sl.LEGS], dtype=float)
    expected = soil_set["Kc"] / b_poly + soil_set["Kphi"]
    is_same = bool(np.array_equal(np.asarray(soil.coef, float), expected)
                   and np.array_equal(np.asarray(soil.area, float), area)
                   and float(soil.n) == float(soil_set["n"]))
    return {"is_continuous_bekker": is_same, "grid_factor": 1.0 if is_same else None,
            "basis": GRID_FACTOR_BASIS}


def _npz_bytes(arrays: dict[str, np.ndarray]) -> bytes:
    buffer = io.BytesIO()
    np.savez(buffer, schema=np.array(RECORD_SCHEMA), **arrays)
    return buffer.getvalue()


def _json_safe(value):
    from verdict_runs import meta_for_json

    return meta_for_json(value)


def _line_of(job: dict, line: dict, out_dir: Path) -> dict:
    """The jsonl line of a finished run; writes its run record npz."""
    import b1_record
    import loc_anchor_shadow as shadow

    b1 = job["b1"]
    controller, plant = _CAPTURE.get("controller"), _CAPTURE.get("plant")
    d1 = line.get("d1") or {}
    values = (line.get("values") or {})
    out = {"schema": SCHEMA, "rules_file": RULES_FILE, "rules_sha256": RULES_SHA256,
           **{key: b1[key] for key in ("run_id", "group", "row_id", "mass_scale",
                                       "margin_zero", "shadow")},
           "d1_key": d1.get("key"), "setting": job["setting"], "eps": job["eps"],
           "level": ROWS[b1["row_id"]][0], "slope_name": ROWS[b1["row_id"]][1],
           "error": line.get("error"), "tb": line.get("tb"),
           "commands_sha256": line.get("commands_sha256"),
           "final_phase": line.get("final_phase"), "controller_tag": line.get("controller_tag"),
           "harness_class": line.get("harness_class"), "wall_s": line.get("wall_s"),
           "t_first_ready_s": (values.get("times") or {}).get("t_first_ready_s"),
           "t_departure_s": (values.get("forces") or {}).get("t_lift_s"),
           "stroke_max_m": d1.get("stroke_max_m")}
    if controller is None:
        out["error"] = out["error"] or "controller not captured"
        return out
    out["events"] = [[float(event.t_s), event.name] for event in controller.events]
    out["controller"] = b1_record.controller_record(controller)
    meta = controller.meta()
    out["controller_meta"] = _json_safe({name: meta.get(name) for name in STORED_META_BLOCKS})
    out["loc_shadow"] = shadow.record_of(controller)
    out["soil_model"] = soil_model_check(plant, job["d1"]["base"])
    out["plant_mass_scale"] = float(getattr(plant, "mass_scale", 1.0))
    arrays = run_record_arrays(controller)
    data = _npz_bytes(arrays)
    path = out_dir / NPZ_FOLDER / npz_name(b1["run_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    out["npz"] = f"{NPZ_FOLDER}/{path.name}"
    out["npz_sha256"] = hashlib.sha256(data).hexdigest()
    out["periods"] = int(len(arrays["n"]))
    return out


def run_b1_job(job: dict) -> dict:
    """One job in a fresh worker (module docstring)."""
    t_start = time.perf_counter()
    try:
        _install_worker_patches(job["b1"])
        import run_v5

        line = run_v5.run_one(run_v5_job(job))
        out = _line_of(job, line, Path(job["out_dir"]))
    except Exception as exc:  # the batch goes on; the line records the failure
        import traceback

        out = {"schema": SCHEMA, **{key: job["b1"][key] for key in ("run_id", "group", "row_id")},
               "error": repr(exc), "tb": traceback.format_exc()[-3000:]}
    out["wall_total_s"] = round(time.perf_counter() - t_start, 1)
    return out


# ------------------------------------------------------------------------------------ batch
def _read_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(text) for text in handle if text.strip()]


def shadow_pair_check(lines: list[dict]) -> dict:
    """Rules 2.2: every H-SH0 run has the command hash of its H-P VB eps 0 twin."""
    by_id = {line["run_id"]: line for line in lines if not line.get("error")}
    pairs = {}
    for row_id in SHADOW_PAIR_ROWS:
        off = by_id.get(run_id("H-SH0", row_id, "VB", 0.0))
        on = by_id.get(run_id("H-P", row_id, "VB", 0.0))
        if off is None or on is None:
            pairs[row_id] = "missing"
        else:
            pairs[row_id] = "same" if off["commands_sha256"] == on["commands_sha256"] else "DIFF"
    return {"pairs": pairs, "all_same": all(state == "same" for state in pairs.values())}


def _select(jobs: list[dict], groups: str | None, runs: str | None) -> list[dict]:
    if groups:
        wanted = set(groups.split(","))
        jobs = [job for job in jobs if job["b1"]["group"] in wanted]
    if runs:
        wanted = set(runs.split(","))
        jobs = [job for job in jobs if job["b1"]["run_id"] in wanted]
    return jobs


def run_batch(todo: list[dict], out_path: Path, workers: int) -> int:
    """Run ``todo`` (one spawned worker per job); the number of error lines."""
    errors = 0
    pool = get_context("spawn").Pool(max(1, min(workers, len(todo))), maxtasksperchild=1)
    is_finished = False
    try:
        with out_path.open("a", encoding="utf-8") as sink:
            for count, line in enumerate(pool.imap_unordered(run_b1_job, todo, chunksize=1), 1):
                sink.write(json.dumps(line, default=float) + "\n")
                sink.flush()
                errors += bool(line.get("error"))
                state = (line.get("error") or "")[:200] or (
                    f"{line.get('final_phase')} {str(line.get('commands_sha256'))[:8]}")
                print(f"{count}/{len(todo)} {line['run_id']}: {state} "
                      f"{line.get('wall_total_s')} s", flush=True)
        is_finished = True
    finally:
        if is_finished:
            pool.close()
        else:
            pool.terminate()
        pool.join()
    return errors


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--mask", default=None, help="hex affinity of every worker (job mask)")
    parser.add_argument("--groups", default=None, help=f"comma-separated of {', '.join(GROUPS)}")
    parser.add_argument("--runs", default=None, help="comma-separated run ids (trial)")
    parser.add_argument("--list", action="store_true", help="print the jobs and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import loc_anchor_shadow as shadow
    import shadow_identity

    args = _parse_args(argv)
    jobs = _select(b1_jobs(), args.groups, args.runs)
    mismatches = slope_mismatches(jobs)
    if mismatches:
        print("\n".join(mismatches), file=sys.stderr)
        return EXIT_INPUT
    if args.list:
        for job in jobs:
            print(job["b1"]["run_id"], job["d1"]["key"], f"mass {job['b1']['mass_scale']:g}",
                  f"margin_zero {job['b1']['margin_zero']}", f"shadow {job['b1']['shadow']}")
        return EXIT_DONE
    if any(job["b1"]["shadow"] for job in jobs) and not shadow.is_enabled():
        print(f"set {shadow.ENV_SWITCH}={shadow.ENV_ON}", file=sys.stderr)
        return EXIT_INPUT
    out_path = args.out_dir / JSONL_NAME
    done = {line["run_id"] for line in _read_lines(out_path) if not line.get("error")}
    mask = None if args.mask is None else int(args.mask, 16)
    todo = [{**job, "mask": mask, "out_dir": str(args.out_dir)} for job in jobs
            if job["b1"]["run_id"] not in done]
    print(f"B1 harness: {len(jobs)} jobs, done {len(done)}, to run {len(todo)}, "
          f"workers {args.workers}", flush=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    sidecar = out_path.with_suffix(out_path.suffix + ".identity.json")
    start = shadow_identity.identity(ROOT, TOOL_FILES)
    shadow_identity.write_sidecar(sidecar, {"start": start, "end": None, "argv": sys.argv})
    errors = run_batch(todo, out_path, args.workers) if todo else 0
    pairs = shadow_pair_check(_read_lines(out_path))
    print(f"shadow pairs {json.dumps(pairs)}", flush=True)
    end = shadow_identity.identity(ROOT, TOOL_FILES)
    has_diff_pair = any(state == "DIFF" for state in pairs["pairs"].values())
    code = EXIT_STOP if errors or has_diff_pair else EXIT_DONE
    shadow_identity.write_sidecar(sidecar, {"start": start, "end": end, "argv": sys.argv,
                                            "errors": errors, "shadow_pairs": pairs,
                                            "exit": code})
    return code


if __name__ == "__main__":
    sys.exit(main())
