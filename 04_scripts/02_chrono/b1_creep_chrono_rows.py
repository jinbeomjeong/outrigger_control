"""B1 creep basis (``V5-B1-CREEP``): Chrono SCM row definitions + build / field checks (no simulation; cad 2026-11-12).

Rules ``06_analysis/02_control/b1/b1_creep_basis_rules_seal_candidate_draft.md`` (seal candidate, sha256
``fa142d52...``; not sealed when this module was written) 1.1 / 1.4 / 2.1 / 2.3 / 6. Batches of ``s9_batch``:

* ``V5-B1-CREEP``: the 6 rows of rules 2.1 (C1 .. C5 x1.0 160 s, C6 x1.1 180 s), grid record ``full`` (rules 6
  R-G1 "실행 전체 10 Hz");
* ``V5-B1-CREEP-WIN``: the same 6 rows with ``--b1-grid-record window`` (the rules 6 fallback clause; only when the
  pre-result cost measurement exceeds T-10; all six rows must take the same form);
* ``V5-B1-CREEP-GS``: the G-S dry run of rules 2.3, the C1 form and the C6 form with ``--duration``
  :data:`GS_DURATION_S` (``role`` ``gs``; never judged).

Row form (rules 2.1): ``run_S9.p3b_case`` (J2, pad B ``dwg_rear250``, F_s 4 kN, pad grid 0.01 m / crawler 0.04 m,
``--settle-dashpot zrp``, ``--threads 4``, pressure normal, IMU ideal, seed P3b) + floor roll / pitch + auger level +
``--start-limit record_only`` + ``--duration`` + (C6) ``--mass-scale 1.1`` + ``--b1-grid-record`` + the v5 VB
arguments of ``s9_batch.v5_vb_argv()`` + ``--expect-controller final_C4G2_P3_LAS_K1``. The rows are NOT built with
``s9_batch.v5_vb_rows()`` (that function replaces the expected tag by ``final_C4G2_P3``, rules 1.4). Start env
``OMP_WAIT_POLICY=PASSIVE`` only; ``OUTRIGGER_HULL_HOOK`` stays unset (default fast, rules 2.4 / I-7: the launching
shell removes it).

Estimates (ASSUMPTION, rules 12): P C1 .. C5 8500 s (REM J2 top 6500 s / 128 s x 168 s, rules 12 range
7000 .. 10000 s), C6 9700 s (``las_p5r4_k1_chrono_rows`` C x1.1 180 s); E = P x :data:`E_POOL_FACTOR`.

Field check: ``python b1_creep_chrono_rows.py gs-check <batch folder>`` prints presence only (file names, array /
key names, rc); no force, stroke, sinkage, time or hash value.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

B1_BATCH = "V5-B1-CREEP"
B1_WIN_BATCH = "V5-B1-CREEP-WIN"
B1_GS_BATCH = "V5-B1-CREEP-GS"
B1_RULES = "06_analysis/02_control/b1/b1_creep_basis_rules_seal_candidate_draft.md"
B1_RULES_SHA256 = "fa142d525c9c8d318212c245b552cea47b0394ed97680900653bcda737ab5cf9"
B1_SOURCE = f"{B1_RULES} (sha256 {B1_RULES_SHA256[:8]}, seal candidate) 2.1 / 2.3 / 6; cad row definition 2026-11-12"
CONTROLLER_VB = "final_C4G2_P3_LAS_K1"
SOIL, PAD, FS_KN = "J2", "B", 4.0
START_LIMIT = "record_only"
START_ENV = {"OMP_WAIT_POLICY": "PASSIVE"}
PLANNED_POOL = "pcore"
E_POOL_FACTOR = 1.5
GS_DURATION_S = 10.0
GS_IDS = ("C1", "C6")
FORBIDDEN_OPTIONS = ("--k1-order-gate", "--k1-forced-block", "--las-off", "--k2", "--las-candidate",
                     "--no-controller-check", "--soil-patch", "--rigid-base")

# (id, auger level, floor roll [deg], floor pitch [deg], mass scale, duration [s], budget leg, role, direction,
#  est P [s])
ROWS: tuple[tuple[str, str, float, float, float, float, str, str, str, float], ...] = (
    ("C1", "bottom", 0.0, 2.8, 1.0, 160.0, "FL", "core", "fdown", 8500.0),
    ("C2", "middle", 0.0, 2.8, 1.0, 160.0, "FL", "core", "fdown", 8500.0),
    ("C3", "top", 0.0, 2.8, 1.0, 160.0, "FL", "aux", "fdown", 8500.0),
    ("C4", "bottom", 1.925, 1.4, 1.0, 160.0, "FR", "core", "diag", 8500.0),
    ("C5", "top", 0.0, -2.8, 1.0, 160.0, "RL", "core", "fup", 8500.0),
    ("C6", "bottom", 0.0, 2.8, 1.1, 180.0, "FL", "sensitivity", "fdown", 9700.0),
)
"""Rules 2.1 table (est P = ASSUMPTION, rules 12)."""


def _import(name: str) -> ModuleType:
    sys.path.insert(0, str(HERE))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(HERE))


def _r9() -> ModuleType:
    return _import("run_S9")


def case_name(rid: str) -> str:
    """Rules 2.1 case names, e.g. ``B1_J2_B_bottom_Fs4_VB_fdown``, ``B1_J2_B_bottom_Fs4_m1p1_VB_fdown``."""
    _, level, _, _, m, _, _, _, direction, _ = next(r for r in ROWS if r[0] == rid)
    mass = "" if m == 1.0 else "_m" + f"{m:g}".replace(".", "p")
    return f"B1_{SOIL}_{PAD}_{level}_Fs{FS_KN:g}{mass}_VB_{direction}"


def level_argv(r9: ModuleType, sb: ModuleType, rid: str, *, duration_s: float | None = None,
               grid_mode: str = "full") -> list[str]:
    """``run_S9.py level`` argv of a row (without the interpreter)."""
    _, level, roll, pitch, m, dur, _, _, _, _ = next(r for r in ROWS if r[0] == rid)
    c = r9.p3b_case(B1_BATCH, SOIL, PAD, level, FS_KN)
    c.update(floor_deg=(float(roll), float(pitch)), start_limit=START_LIMIT,
             duration_s=float(dur if duration_s is None else duration_s), b1_grid_record=grid_mode)
    if m != 1.0:
        c["mass_scale"] = float(m)
    out = r9.p3b_level_argv(c)  # no "controller" key: the tag is appended after the VB arguments (rules 1.4)
    return out + list(sb.v5_vb_argv()) + ["--expect-controller", CONTROLLER_VB]


def b1_rows(sb: ModuleType, *, gs: bool = False, grid_mode: str = "full") -> list[dict[str, Any]]:
    r9 = _r9()
    batch = B1_GS_BATCH if gs else (B1_WIN_BATCH if grid_mode == "window" else B1_BATCH)
    rows = []
    for rid, level, roll, pitch, m, dur, leg, role, direction, est_p in ROWS:
        if gs and rid not in GS_IDS:
            continue
        run_dur = GS_DURATION_S if gs else dur
        if gs:
            sim = r9.CRAWLER_SETTLE_S + run_dur
            p = round(est_p * sim / (r9.CRAWLER_SETTLE_S + dur), -1)
        else:
            p = est_p
        pools = {"pcore": p, "ecore": round(p * E_POOL_FACTOR, -1)}
        rows.append({
            "case": case_name(rid), "est_s": pools["pcore"], "est_pool_s": pools,
            "argv": list(sb.RUN) + level_argv(r9, sb, rid, duration_s=run_dur, grid_mode=grid_mode),
            "controller": CONTROLLER_VB, "v5_setting": "VB", "group": batch, "criteria_id": f"B1-CREEP-{rid}",
            "b1_id": rid, "b1_role": "gs" if gs else role, "b1_budget_leg": leg, "b1_direction": direction,
            "b1_level": level, "b1_floor_deg": [roll, pitch], "b1_mass_scale": m, "b1_duration_s": run_dur,
            "b1_judge_duration_s": dur, "b1_grid_record": grid_mode, "planned_pool": PLANNED_POOL,
            "start_env": dict(START_ENV), "b1_rules": B1_SOURCE,
            "note": (f"{batch} {rid} ({'G-S dry run' if gs else role}): J2 B {level} floor ({roll:g}, {pitch:g}) deg, "
                     f"x{m:g}, {run_dur:g} s, VB {CONTROLLER_VB}, grid record {grid_mode}")})
    return rows


def rows(gs: bool = False, grid_mode: str = "full") -> list[dict[str, Any]]:
    """Row dicts built with this checkout's ``s9_batch`` (= ``s9_batch.batches()[name]``)."""
    return b1_rows(_import("s9_batch"), gs=gs, grid_mode=grid_mode)


def b1_batches(sb: ModuleType) -> dict[str, list[dict[str, Any]]]:
    out = {B1_BATCH: b1_rows(sb), B1_WIN_BATCH: b1_rows(sb, grid_mode="window"), B1_GS_BATCH: b1_rows(sb, gs=True)}
    for name, rs in out.items():
        names = [r["case"] for r in rs]
        if len(set(names)) != len(names):
            raise RuntimeError(f"{name}: duplicate case names")
    return out


# --------------------------------------------------------------------------------------------- build checks
def _scalar(v: Any) -> Any:
    return v[0] if isinstance(v, (list, tuple)) and len(v) == 1 else v


def argv_check(row: dict[str, Any], sb: ModuleType) -> dict[str, Any]:
    """Without Chrono: the argv parses with the run_S9 parser and holds the rules 2.1 values; no forbidden option;
    exactly the VB arguments; the run-time config (run_level order) passes ``--expect-controller`` with the tag;
    ``--start-limit record_only`` changes ``target.acceptance`` only; controller class C2Controller, K1 order gate
    on, TOUCH creep latch off."""
    out: dict[str, Any] = {"case": row["case"], "b1_id": row["b1_id"]}
    r9 = _r9()
    argv = row["argv"]
    level = argv[argv.index("level"):]
    diffs: list[dict[str, Any]] = []
    for opt in FORBIDDEN_OPTIONS:
        if opt in level:
            diffs.append({"key": opt, "want": "absent", "row": "present"})
    if level.count("--expect-controller") != 1:
        diffs.append({"key": "--expect-controller count", "want": 1, "row": level.count("--expect-controller")})
    try:
        a = r9.build_parser().parse_args(level)
    except SystemExit as e:
        return {**out, "status": "differs", "diffs": diffs + [{"key": "argparse", "want": "ok", "row": str(e)}]}
    want = {"soil": SOIL, "pad_variant": r9.P3B_PAD[PAD], "level": row["b1_level"], "fs_kN": FS_KN,
            "grid": r9.P3B_PAD_GRID_M[SOIL], "crawler_grid": r9.P3B_CRAWLER_GRID_M, "settle_dashpot": "zrp",
            "threads": r9.SCM_THREADS_FIXED, "duration": row["b1_duration_s"], "pressure_grade": "normal",
            "imu_grade": "ideal", "seed": r9.P3B_SEED, "floor_roll": row["b1_floor_deg"][0],
            "floor_pitch": row["b1_floor_deg"][1], "start_limit": START_LIMIT, "mass_scale": row["b1_mass_scale"],
            "expect_controller": CONTROLLER_VB, "b1_grid_record": row["b1_grid_record"], "approved": True,
            "soil_patch": None, "rigid_base": None}
    for k, v in want.items():
        got = _scalar(getattr(a, k, None))
        if got != v and not (v is not None and got is not None and str(got) == str(v)):
            diffs.append({"key": k, "want": v, "row": got})
    for attr in ("k1_order_gate", "las_off", "k2", "las_candidate"):
        if hasattr(a, attr):
            diffs.append({"key": attr, "want": "<no attribute>", "row": getattr(a, attr)})
    for k, v in sb.V5_VB_ARGS.items():
        got = _scalar(getattr(a, k, None))
        if got != v:
            diffs.append({"key": k, "want": v, "row": got})
    k1c = _import("las_k1_chrono_rows")
    try:
        config = k1c.run_level_config(r9, a)
    except SystemExit as e:
        return {**out, "status": "differs", "diffs": diffs + [{"key": "level_config", "want": "ok",
                                                               "row": f"SystemExit({e.code})"}]}
    chk = r9.controller_expectation(config, a.expect_controller)
    out["expect_controller"] = {"name": chk["name"], "ok": chk["ok"]}
    if not chk["ok"]:
        diffs.append({"key": "expect_controller", "want": True,
                      "row": [c["path"] for c in chk["checks"] if not c["ok"]]})
    _, sl = r9.apply_start_limit(r9.level_c2_config_of_args(a)[0], START_LIMIT, a.level)
    if list(sl["overrides"]) != ["target.acceptance"]:
        diffs.append({"key": "start_limit_overrides", "want": ["target.acceptance"], "row": list(sl["overrides"])})
    cls, meta = r9.level_controller_class(a)
    if cls.__name__ != "C2Controller" or meta.get("requested") != "off":
        diffs.append({"key": "controller_class", "want": "C2Controller", "row": [cls.__name__, meta]})
    if config.slope_clearance_margin.flat_soil_margin_order_gate is not True:
        diffs.append({"key": "flat_soil_margin_order_gate", "want": True,
                      "row": config.slope_clearance_margin.flat_soil_margin_order_gate})
    if bool(getattr(getattr(config, "touch_creep_latch", None), "enable", False)):
        diffs.append({"key": "touch_creep_latch", "want": False, "row": True})
    return {**out, "status": "differs" if diffs else "ok", "diffs": diffs}


def batch_check(rs: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """Batch-level: row set and unique names; every row on the same planned pool and start env."""
    want_ids = list(GS_IDS) if name == B1_GS_BATCH else [r[0] for r in ROWS]
    diffs = []
    if [r["b1_id"] for r in rs] != want_ids or len({r["case"] for r in rs}) != len(rs):
        diffs.append({"key": "rows", "want": want_ids, "row": [r["b1_id"] for r in rs]})
    if len({r["planned_pool"] for r in rs}) != 1 or any(r["start_env"] != START_ENV for r in rs):
        diffs.append({"key": "pool / start_env", "row": [[r["planned_pool"], r["start_env"]] for r in rs]})
    if len({r["b1_grid_record"] for r in rs}) != 1:
        diffs.append({"key": "b1_grid_record mixed", "row": [r["b1_grid_record"] for r in rs]})
    return {"case": "<batch>", "status": "differs" if diffs else "ok", "diffs": diffs}


# --------------------------------------------------------------------------------------------- G-S field check
RESULT_KEY_PATHS: tuple[str, ...] = (
    "c2_setup.expect_controller.ok", "c2_setup.expect_controller.name", "c2_setup.start_limit.mode",
    "c2_setup.start_limit.overrides", "num_threads_chrono", "args.threads", "args.b1_grid_record",
    "placement.omp_wait_policy", "placement.mode", "hull_hook.mode", "hull_hook.requested",
    "hull_hook.fallback_reason", "hull_hook.dll_sha256", "code_state.git_at_start.head", "code_state.git_at_start.dirty",
    "controller_meta", "events", "phases", "t_loop_start_s", "mass_scale", "s9_rows", "step_series.keys",
    "loc_corrections.locs", "p3b", "b1_grid_record.file", "b1_grid_record.mode", "b1_grid_record.keys",
    "b1_grid_record.static.pads", "b1_grid_record.pad_node_stats_wall_s", "b1_grid_record.loop_wall_s",
    "meta.params_sha256")
"""result.json key paths the B1 tools read (5 / 6 / 4.1); presence only."""
GRID_ARRAYS = ("n_cycle", "t_s", "computed", "n_inside", "n_contact", "n_sigma_negative", "contact_hull_area_m2",
               "contact_hull_perimeter_m", "sinkage_geometric_m", "sigma_sum_area_N", "sinkage_mean_contact_m",
               "pad_bottom_centre_world_m", "pad_bottom_centre_plane_xy_m", "pad_body_pos_world_m",
               "pad_yaw_plane_rad", "imu_n_cycle", "imu_t_s", "imu_raw_roll_rad", "imu_raw_pitch_rad",
               "imu_specific_force_m_s2")
STEP_ARRAYS = ("t_s", "pad_sinkage_geometric_m")
RECORD_FILES = ("result.json", "step_series.npz", "record/record.npz", "b1_grid_record.npz", "controller_commands.npz")
BATCH_TOP_KEYS = ("batch", "cases", "mixed_hull_mode", "failed")
BATCH_ENTRY_KEYS = ("case", "argv", "rc", "pool", "planned_pool", "omp_wait_policy", "hull_hook_requested",
                    "hull_hook_effective", "start_env", "controller", "v5_setting", "criteria_id")
_MISSING = object()


def _get(doc: Any, path: str) -> Any:
    node = doc
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


def field_check(folder: Path, batch_name: str | None = None) -> dict[str, Any]:
    """Presence-only check of a finished batch folder (rules 2.3 outputs: rc, expect_controller.ok, tag, hull_hook,
    num_threads_chrono, field key names); no simulation value is read into the output."""
    import numpy as np  # noqa: PLC0415

    folder = Path(folder)
    out: dict[str, Any] = {"folder": folder.as_posix(), "errors": [], "cases": []}
    bpath, ppath = folder / "batch.json", folder / "progress.log"
    batch = json.loads(bpath.read_text("utf-8")) if bpath.is_file() else None
    out["batch_json"], out["progress_log"] = batch is not None, ppath.is_file()
    name = batch_name or (batch or {}).get("batch")
    if name not in (B1_BATCH, B1_WIN_BATCH, B1_GS_BATCH):
        out["errors"].append(f"batch name {name!r} is not a B1 batch")
        out["ok"] = False
        return out
    rs = _import("s9_batch").batches()[name]
    out["batch_top_missing"] = [] if batch is None else [k for k in BATCH_TOP_KEYS if k not in batch]
    entries = {e.get("case"): e for e in (batch or {}).get("cases", [])}
    progress = ppath.read_text("utf-8", errors="replace") if ppath.is_file() else ""
    end_rc = {m.group(1): m.group(2) for m in re.finditer(r"^END (\S+) \S+ rc=(-?\d+|None)", progress, re.M)}
    for r in rs:
        case = r["case"]
        c: dict[str, Any] = {"case": case, "b1_id": r["b1_id"], "progress_end_rc0": end_rc.get(case) == "0"}
        e = entries.get(case)
        c["batch_entry"] = e is not None
        c["batch_entry_missing"] = list(BATCH_ENTRY_KEYS) if e is None else [k for k in BATCH_ENTRY_KEYS if k not in e]
        c["batch_entry_rc0"] = e is not None and e.get("rc") == 0
        e_argv = list((e or {}).get("argv") or [])
        c["batch_argv_equal_row"] = ("level" in e_argv
                                     and e_argv[e_argv.index("level"):] == r["argv"][r["argv"].index("level"):])
        d = folder / case
        c["files_missing"] = [f for f in RECORD_FILES if not (d / f).is_file()]
        c["result_missing"] = list(RESULT_KEY_PATHS)
        if (d / "result.json").is_file():
            doc = json.loads((d / "result.json").read_text("utf-8"))
            c["result_missing"] = [p for p in RESULT_KEY_PATHS if _get(doc, p) is _MISSING]
            c["expect_controller_ok"] = _get(doc, "c2_setup.expect_controller.ok") is True
            c["tag_equal"] = _get(doc, "c2_setup.expect_controller.name") == CONTROLLER_VB
            c["hull_hook_mode"] = _get(doc, "hull_hook.mode") if _get(doc, "hull_hook.mode") is not _MISSING else None
            c["num_threads_chrono_4"] = _get(doc, "num_threads_chrono") == 4
            c["b1_grid_record_error"] = "error" in (doc.get("b1_grid_record") or {})
        c["grid_arrays_missing"] = list(GRID_ARRAYS)
        if (d / "b1_grid_record.npz").is_file():
            with np.load(d / "b1_grid_record.npz", allow_pickle=False) as z:
                c["grid_arrays_missing"] = [k for k in GRID_ARRAYS if k not in z.files]
                c["grid_rows_nonempty"] = bool(z["n_cycle"].size > 0) if "n_cycle" in z.files else False
                c["imu_rows_nonempty"] = bool(z["imu_t_s"].size > 0) if "imu_t_s" in z.files else False
        c["step_arrays_missing"] = list(STEP_ARRAYS)
        if (d / "step_series.npz").is_file():
            with np.load(d / "step_series.npz", allow_pickle=False) as z:
                c["step_arrays_missing"] = [k for k in STEP_ARRAYS if k not in z.files]
        c["ok"] = bool(c["progress_end_rc0"] and c["batch_entry"] and not c["batch_entry_missing"]
                       and c["batch_entry_rc0"] and c["batch_argv_equal_row"] and not c["files_missing"]
                       and not c["result_missing"] and c.get("expect_controller_ok") and c.get("tag_equal")
                       and c.get("hull_hook_mode") == "fast" and c.get("num_threads_chrono_4")
                       and not c.get("b1_grid_record_error") and not c["grid_arrays_missing"]
                       and c.get("grid_rows_nonempty") and c.get("imu_rows_nonempty") and not c["step_arrays_missing"])
        out["cases"].append(c)
    out["n_rows"], out["n_ok"] = len(rs), sum(1 for c in out["cases"] if c["ok"])
    out["ok"] = (not out["errors"] and out["batch_json"] and out["progress_log"] and not out["batch_top_missing"]
                 and out["n_ok"] == len(rs))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="V5-B1-CREEP build checks and G-S field check (no simulation)")
    sub = ap.add_subparsers(dest="cmd")
    bc = sub.add_parser("check")
    bc.add_argument("--batch", default=B1_BATCH, choices=(B1_BATCH, B1_WIN_BATCH, B1_GS_BATCH))
    bc.add_argument("--out", default=None)
    fc = sub.add_parser("gs-check")
    fc.add_argument("folder")
    fc.add_argument("--batch", default=None, choices=(B1_BATCH, B1_WIN_BATCH, B1_GS_BATCH))
    fc.add_argument("--out", default=None)
    pa = sub.add_parser("argv", help="expanded argv (from 'level') and its sha256 per row (prelaunch I-2)")
    pa.add_argument("--batch", default=B1_BATCH, choices=(B1_BATCH, B1_WIN_BATCH, B1_GS_BATCH))
    pa.add_argument("--out", default=None)
    a = ap.parse_args(argv if argv is not None else sys.argv[1:] or ["check"])
    if a.cmd == "gs-check":
        if not Path(a.folder).is_dir():
            print(f"gs-check: no folder {a.folder}", file=sys.stderr)
            return 2
        doc = field_check(Path(a.folder), a.batch)
        n_err = len(doc["errors"]) + sum(1 for c in doc["cases"] if not c["ok"])
    elif a.cmd == "argv":
        import hashlib  # noqa: PLC0415

        rs = _import("s9_batch").batches()[a.batch]
        doc = {"batch": a.batch, "rows": []}
        for r in rs:
            lv = r["argv"][r["argv"].index("level"):]
            doc["rows"].append({"id": r["b1_id"], "case": r["case"], "argv_level": lv,
                                "argv_level_sha256": hashlib.sha256(json.dumps(lv).encode("utf-8")).hexdigest(),
                                "est_pool_s": r["est_pool_s"]})
        doc["sha_basis"] = "sha256 of json.dumps(argv from 'level') (UTF-8, default separators)"
        doc["ok"], n_err = True, 0
    else:
        sb = _import("s9_batch")
        rs = sb.batches()[a.batch]
        doc = {"batch": a.batch, "checks": [argv_check(r, sb) for r in rs] + [batch_check(rs, a.batch)]}
        n_err = sum(1 for c in doc["checks"] if c["status"] == "differs")
        doc["ok"] = n_err == 0
    doc["n_errors"] = n_err
    text = json.dumps(doc, indent=1, default=str, ensure_ascii=False)
    if a.out:
        Path(a.out).write_text(text, "utf-8")
    print(text)
    print(f"errors {n_err}")
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
