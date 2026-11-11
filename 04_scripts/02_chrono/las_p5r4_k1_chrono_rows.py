"""LAS-b P5r4 + K1 re-judgement: Chrono SCM rows (definitions + build / field checks only; cad 2026-11-11).

Batches of ``s9_batch`` (``list`` / ``check-sources`` / ``run``), rules
``06_analysis/02_control/verif_matrix/las_p5r4_k1_rules.md`` (sha256 ``5ee2bac0...f979``) 4.3 / 11.2 / 16.2 (b):

* ``V5-LAS-P5R4-K1``: the 12 judge rows of rules 4.3 (``role`` ``judge``);
* ``V5-LAS-P5R4-K1-GS``: the G-S dry run of rules 16.2 (b), the same 12 rows (same case names, same argv) with
  ``--duration`` :data:`GS_DURATION_S` only (``role`` ``gs``; never judged).

Arms (rules 2): ref = ``--las-candidate P0`` (the preset, no override), cand = ``--las-candidate P5r4``
(``run_S9.apply_las_candidate``: beta 4.5, N_r 4). Both arms run the run-time preset ``C2Config().with_10hz_d1()``
(LAS-b b0 + the K1 R4c30 order gate) under the K1 tags (``--expect-controller`` VB ``final_C4G2_P3_LAS_K1`` /
V0 ``final_C4G2_LAS_K1``); no ``--k1-order-gate``, ``--k1-forced-block``, ``--las-off`` or ``--k2`` (rules 2, K-3,
K-7). The argv of a pair differs in the ``--las-candidate`` value only (plus ``--case`` at launch).

Rows (rules 4.3 table), terrain helpers imported, their modules unchanged (rules 11.1):

* A1 .. A6: ``las_chrono_rows`` form (``base_case`` / ``level_argv``): mixed ground rigid + J1@FR
  (``--rigid-base FR --soil J1 --grid 0.01``), floor (2.3351, 1.5017) deg, ``--start-limit record_only``, 160 s;
  Kc1 (YAML crawler stiffness) or Kc3 (``--crawler-kn-scale 3``); VB (A1 .. A4) or V0 (A5 / A6, no v5 argument).
* B1 / B2: ``las_k1_chrono_rows`` form (``run_S9.g6_case``, G6 layout) with the patch set J1 instead of J2 (that
  module has no patch-set argument, rules 11.1): G1 base + J1 patch under FL (``--soil-patch FL:J1
  --soil-patch-grid 0.01``), flat, 200 s, VB. Harness key ``D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0`` (its ``K1`` = crawler
  stiffness x1, not the order gate).
* C1 .. C4: ``las_k1_rem_chrono_rows`` form (``base_case``: P3b J2 B top, uniform soil, flat), VB; C1 / C2 x1.0 120 s,
  C3 / C4 ``--mass-scale 1.1`` 180 s (rules 4.3 note: BT-C on the first 120 s).

Common: pad B (``dwg_rear250``), F_s 4 kN, auger top, pressure normal / IMU ideal / seed 20261026, ``--threads`` =
``run_S9.SCM_THREADS_FIXED`` (4), start env ``OMP_WAIT_POLICY=PASSIVE`` + ``OUTRIGGER_HULL_HOOK=fast`` (row key
``start_env``; rules 16.5), planned pool P (a pair on the same pool kind).

Estimates (ASSUMPTION, rules 12.2; not measured on these rows): P [s] A 5600, B 6800, C x1.0 6500, C x1.1 180 s 9700;
E = P x :data:`E_POOL_FACTOR` (1.5, the S9 E / P ratio of the project SCM rules 2026-11-08).

G-S field check (rules 16.2 (b), K-2 V-7: the batch must really write the files the judge tools read):
``python las_p5r4_k1_chrono_rows.py gs-check <batch folder>`` checks ``progress.log`` END ``rc=0``,
``<case>/result.json``, ``<case>/controller_commands.npz`` (``t_s``, ``issued_u_m_s``), the ``batch.json`` row and
every key path of :data:`RESULT_KEY_PATHS` / :data:`BATCH_ENTRY_KEYS` / :data:`BATCH_TOP_KEYS`; it prints presence only
(no force, stroke, time or hash value).
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

P5K_BATCH = "V5-LAS-P5R4-K1"
P5K_GS_BATCH = "V5-LAS-P5R4-K1-GS"
P5K_RULES = "06_analysis/02_control/verif_matrix/las_p5r4_k1_rules.md"
P5K_RULES_SHA256 = "5ee2bac0451f0ca00139a5a2d238c38d13a6b0f430efc5b44fe0e8b929c2f979"
P5K_SOURCE = f"{P5K_RULES} (sha256 {P5K_RULES_SHA256[:8]}) 4.3 / 11.2 / 16.2; cad row definition (2026-11-11)"
VB_CONTROLLER, V0_CONTROLLER = "final_C4G2_P3_LAS_K1", "final_C4G2_LAS_K1"
CONTROLLER_OF_SETTING = {"VB": VB_CONTROLLER, "V0": V0_CONTROLLER}
PAD, LEVEL, FS_KN, SEED = "B", "top", 4.0, 20261026
START_ENV = {"OMP_WAIT_POLICY": "PASSIVE", "OUTRIGGER_HULL_HOOK": "fast"}
PLANNED_POOL = "pcore"
E_POOL_FACTOR = 1.5
"""ASSUMPTION: E-pool wall / P-pool wall of an S9 row (project SCM rules 2026-11-08, about 1.5)."""
GS_DURATION_S = 10.0
"""G-S closed loop [s] (rules 16.2 (b) default 10 s). A 10 s smoke row of the GS batch (cad 2026-11-11, see the report)
ran the run_S9 post-analysis without an error, so the default stands."""
KC3_FACTOR = 3.0
B_BASE, B_PATCH_SET, B_PATCH_LEG, B_DURATION_S = "G1", "J1", "FL", 200.0
B_HARNESS_KEY = "D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0"
"""Harness key of the B pair (rules 4.3 #7); its ``K1`` = crawler stiffness x1 (``D1Row.crawler_k_scale``)."""
C_SOIL = "J2"
FORBIDDEN_OPTIONS = ("--k1-order-gate", "--k1-forced-block", "--las-off", "--k2", "--no-controller-check")
"""Rules 2 / K-3 / K-7: none of these in a row argv."""

# (p5k_id, family, crawler, mass_scale, setting, las_candidate, pair, duration_s, est_P_s)
ROWS: tuple[tuple[str, str, str, float, str, str, str, float, float], ...] = (
    ("A1", "A", "Kc1", 1.0, "VB", "P0", "A2", 160.0, 5600.0),
    ("A2", "A", "Kc1", 1.0, "VB", "P5r4", "A1", 160.0, 5600.0),
    ("A3", "A", "Kc3", 1.0, "VB", "P0", "A4", 160.0, 5600.0),
    ("A4", "A", "Kc3", 1.0, "VB", "P5r4", "A3", 160.0, 5600.0),
    ("A5", "A", "Kc1", 1.0, "V0", "P0", "A6", 160.0, 5600.0),
    ("A6", "A", "Kc1", 1.0, "V0", "P5r4", "A5", 160.0, 5600.0),
    ("B1", "B", "Kc1", 1.0, "VB", "P0", "B2", 200.0, 6800.0),
    ("B2", "B", "Kc1", 1.0, "VB", "P5r4", "B1", 200.0, 6800.0),
    ("C1", "C", "Kc1", 1.0, "VB", "P0", "C2", 120.0, 6500.0),
    ("C2", "C", "Kc1", 1.0, "VB", "P5r4", "C1", 120.0, 6500.0),
    ("C3", "C", "Kc1", 1.1, "VB", "P0", "C4", 180.0, 9700.0),
    ("C4", "C", "Kc1", 1.1, "VB", "P5r4", "C3", 180.0, 9700.0),
)
"""Rules 4.3 table (12 rows, 6 pairs); est_P_s = rules 12.2 (ASSUMPTION)."""
GS_US_PER_STEP_P = {"A": 2800.0, "B": 7000.0, "C": 9000.0}
"""ASSUMPTION (G-S estimate only): P per-step cost [us] (``las_chrono_rows.MIXED_US_PER_STEP``,
``run_S9.G6_US_PER_STEP_UPPER``, ``run_S9.P3B_US_PER_STEP_UPPER``)."""
VB_FACTOR = 1.2
"""ASSUMPTION (G-S estimate only): v5 VB cost factor (``s9_batch.V5_SOIL_VB_FACTOR``)."""


def _import(name: str) -> ModuleType:
    sys.path.insert(0, str(HERE))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(HERE))


def _r9() -> ModuleType:
    return _import("run_S9")


def stage_of(family: str, crawler: str, mass_scale: float, setting: str) -> str:
    """G-S stage of a row (rules 16.2 (b)): A-Kc1-VB, A-Kc3-VB, A-Kc1-V0, B, C-m1p0, C-m1p1."""
    if family == "A":
        return f"A-{crawler}-{setting}"
    if family == "B":
        return "B"
    return "C-m1p0" if mass_scale == 1.0 else "C-m" + f"{mass_scale:g}".replace(".", "p")


def case_name(pid: str, family: str, crawler: str, mass_scale: float, setting: str, cand: str) -> str:
    """Case names, e.g. ``P5K_A3_rigidJ1FR_Kc3_VB_P0``, ``P5K_C4_J2_m1p1_t180_VB_P5r4``."""
    if family == "A":
        body = f"rigidJ1FR_{crawler}"
    elif family == "B":
        body = f"{B_BASE}_{B_PATCH_SET}{B_PATCH_LEG}"
    else:
        body = f"{C_SOIL}" + ("" if mass_scale == 1.0 else "_m" + f"{mass_scale:g}".replace(".", "p")) \
               + ("" if mass_scale == 1.0 else "_t180")
    return f"P5K_{pid}_{body}_{PAD}_{LEVEL}_Fs{FS_KN:g}_{setting}_{cand}"


def _vb(sb: ModuleType, setting: str) -> list[str]:
    if setting == "VB":
        return sb.v5_vb_argv()
    if setting == "V0":
        return []
    raise ValueError(f"{P5K_BATCH}: v5 setting {setting!r} not VB / V0")


def level_argv(r9: ModuleType, sb: ModuleType, family: str, crawler: str, mass_scale: float, setting: str,
               cand: str, duration_s: float) -> list[str]:
    """``run_S9.py level`` argv of a row (without the interpreter): the terrain helper's argv + the v5 VB arguments
    (VB rows) + ``--las-candidate <cand>``; ``duration_s`` replaces the helper's ``--duration`` (G-S)."""
    tag = CONTROLLER_OF_SETTING[setting]
    if family == "A":
        lcr = _import("las_chrono_rows")
        c = lcr.base_case(r9)
        c["controller"] = tag
        out = lcr.level_argv(r9, c, 1.0 if crawler == "Kc1" else KC3_FACTOR)
    elif family == "B":
        c = r9.g6_case(B_BASE, B_PATCH_SET, B_PATCH_LEG, pad=PAD, level=LEVEL, fs=FS_KN, group=P5K_BATCH,
                       duration_s=B_DURATION_S)
        c["controller"] = tag
        out = r9.p3b_level_argv(c)
    elif family == "C":
        rem = _import("las_k1_rem_chrono_rows")
        c = rem.base_case(r9, C_SOIL, LEVEL, mass_scale, setting)
        c["controller"] = tag  # the REM helper sets the pre-switch tag; the rows run the K1 tag (rules 4.3)
        if mass_scale != 1.0:
            c["duration_s"] = 180.0
        out = r9.p3b_level_argv(c)
    else:
        raise ValueError(f"{P5K_BATCH}: family {family!r}")
    out = out + _vb(sb, setting) + [r9.LAS_CANDIDATE_OPTION, cand]
    k = out.index("--duration")
    out[k + 1] = f"{float(duration_s):g}"
    return out


def _est_gs(family: str, setting: str) -> dict[str, float]:
    r9 = _r9()
    sim_s = r9.CRAWLER_SETTLE_S + GS_DURATION_S
    p = sim_s / 1.0e-4 * GS_US_PER_STEP_P[family] * 1e-6 * (VB_FACTOR if setting == "VB" else 1.0)
    return {"pcore": round(p, -1), "ecore": round(p * E_POOL_FACTOR, -1)}


def p5k_rows(sb: ModuleType, gs: bool = False) -> list[dict[str, Any]]:
    """The 12 rows of rules 4.3 in table order (``gs``: the G-S rows of rules 16.2 (b), ``--duration``
    :data:`GS_DURATION_S`)."""
    r9 = _r9()
    names = {pid: case_name(pid, fam, cr, m, st, cand) for pid, fam, cr, m, st, cand, *_ in ROWS}
    batch = P5K_GS_BATCH if gs else P5K_BATCH
    rows = []
    for pid, fam, cr, m, st, cand, pair, dur, est_p in ROWS:
        run_dur = GS_DURATION_S if gs else dur
        pools = _est_gs(fam, st) if gs else {"pcore": est_p, "ecore": round(est_p * E_POOL_FACTOR, -1)}
        stage = stage_of(fam, cr, m, st)
        r = {
            "case": names[pid], "est_s": pools["pcore"], "est_pool_s": pools,
            "argv": list(sb.RUN) + level_argv(r9, sb, fam, cr, m, st, cand, run_dur),
            "controller": CONTROLLER_OF_SETTING[st], "group": batch, "criteria_id": f"LAS-P5R4-K1-{pid}",
            "p5k_id": pid, "p5k_stage": stage, "p5k_gs": bool(gs), "p5k_family": fam, "p5k_crawler": cr,
            "p5k_mass_scale": m, "p5k_duration_s": run_dur, "p5k_judge_duration_s": dur,
            "role": "gs" if gs else "judge", "v5_setting": st, "las_candidate": cand,
            "pair_case": names[pair], "planned_pool": PLANNED_POOL, "start_env": dict(START_ENV),
            "p5k_rules": P5K_SOURCE,
            "note": (f"{batch} {pid} ({'G-S dry run' if gs else 'judge'}): {stage}, pad B top, F_s 4 kN, "
                     f"{run_dur:g} s, {st} {CONTROLLER_OF_SETTING[st]}, --las-candidate {cand}; pair {pair}")}
        if fam == "B":
            r["harness_case"] = B_HARNESS_KEY
        rows.append(r)
    return rows


def p5k_batches(sb: ModuleType) -> dict[str, list[dict[str, Any]]]:
    out = {P5K_BATCH: p5k_rows(sb), P5K_GS_BATCH: p5k_rows(sb, gs=True)}
    for name, rows in out.items():
        names = [r["case"] for r in rows]
        if len(set(names)) != len(names) or len(rows) != len(ROWS):
            raise RuntimeError(f"{name}: {len(rows)} rows, {len(set(names))} unique names")
    return out


# --------------------------------------------------------------------------------------------- build checks
def run_level_config(r9: ModuleType, a: argparse.Namespace) -> tuple[Any, dict[str, Any], dict[str, Any] | None]:
    """The C2 config ``run_S9.run_level`` builds the controller from, without Chrono: the steps of
    ``las_k1_chrono_rows.run_level_config`` (preset ... v5 controller options), then the ``--expect-controller`` check
    and ``run_S9.apply_las_candidate`` in the run_level order. Returns (config, tag check, candidate record); a
    failing step raises SystemExit as run_level would."""
    k1c = _import("las_k1_chrono_rows")
    config = k1c.run_level_config(r9, a)
    chk = r9.controller_expectation(config, a.expect_controller)
    if not chk["ok"]:
        raise SystemExit(f"--expect-controller {a.expect_controller}: {[c for c in chk['checks'] if not c['ok']]}")
    config, record = r9.apply_las_candidate(config, a)
    return config, chk, record


def _scalar(v: Any) -> Any:
    return v[0] if isinstance(v, (list, tuple)) and len(v) == 1 else v


def argv_check(row: dict[str, Any], sb: ModuleType) -> dict[str, Any]:
    """Build check without Chrono (rules 11.2 #2): the level argv parses with the run_S9 parser; the fixed values
    (threads, terrain, pad, level, F_s, duration, grades, seed, mass scale, floor, start limit, crawler scale, tag,
    candidate) are the row's; no forbidden option (:data:`FORBIDDEN_OPTIONS`); VB rows carry exactly the VB
    arguments, V0 rows none; the run-time config passes the new-tag check, then the candidate preset / candidate
    checks; the controller class is C2Controller and the built controller holds the candidate settings and the
    order gate, with the TOUCH creep latch off."""
    out: dict[str, Any] = {"case": row["case"], "source": None, "p5k_id": row["p5k_id"],
                           "las_candidate": row["las_candidate"]}
    r9 = _r9()
    argv = row["argv"]
    level = argv[argv.index("level"):]
    diffs: list[dict[str, Any]] = []
    for opt in FORBIDDEN_OPTIONS:
        if opt in level:
            diffs.append({"key": opt, "former": "absent", "row": "present"})
    try:
        a = r9.build_parser().parse_args(level)
    except SystemExit as e:
        return {**out, "status": "differs", "diffs": diffs + [{"key": "argparse", "former": "ok", "row": str(e)}]}
    fam, m = row["p5k_family"], row["p5k_mass_scale"]
    want: dict[str, Any] = {
        "threads": r9.SCM_THREADS_FIXED, "pad_variant": r9.P3B_PAD[PAD], "level": LEVEL, "fs_kN": FS_KN,
        "duration": row["p5k_duration_s"], "pressure_grade": "normal", "imu_grade": "ideal", "seed": SEED,
        "mass_scale": m, "expect_controller": row["controller"], "las_candidate": row["las_candidate"],
        "k1_forced_block": r9.K1_FORCED_BLOCK_DEFAULT}
    if fam == "A":
        want.update(soil="J1", rigid_base="FR", soil_patch=None, crawler_grid=None, grid=0.01,
                    crawler_kn_scale=None if row["p5k_crawler"] == "Kc1" else KC3_FACTOR,
                    floor_roll=2.3351, floor_pitch=1.5017, start_limit=r9.S9SL_START_LIMIT)
    elif fam == "B":
        want.update(soil=B_BASE, soil_patch=f"{B_PATCH_LEG}:{B_PATCH_SET}",
                    soil_patch_grid=r9.P3B_PAD_GRID_M[B_PATCH_SET], grid=r9.P3B_PAD_GRID_M[B_BASE],
                    crawler_grid=r9.P3B_CRAWLER_GRID_M, rigid_base=None, crawler_kn_scale=None, floor_roll=0.0,
                    floor_pitch=0.0)
    else:
        want.update(soil=C_SOIL, soil_patch=None, grid=r9.P3B_PAD_GRID_M[C_SOIL], crawler_grid=r9.P3B_CRAWLER_GRID_M,
                    rigid_base=None, crawler_kn_scale=None, floor_roll=0.0, floor_pitch=0.0)
    for k, v in want.items():
        got = _scalar(getattr(a, k, None))
        if got != v and not (v is not None and got is not None and str(got) == str(v)):
            diffs.append({"key": k, "former": v, "row": got})
    for attr in ("k1_order_gate", "las_off", "k2"):
        if hasattr(a, attr):
            diffs.append({"key": attr, "former": "<no attribute>", "row": getattr(a, attr)})
    if row["v5_setting"] == "VB":
        for k, v in sb.V5_VB_ARGS.items():
            got = _scalar(getattr(a, k, None))
            if got != v:
                diffs.append({"key": k, "former": v, "row": got})
    else:
        present = [k for k in sb.V5_VB_ARGS if getattr(a, k, None) not in (None, False)]
        if present:
            diffs.append({"key": "v5_args", "former": [], "row": present})
    from outrigger_sim.hydraulics.flow_limit_run import flow_setting_from_args  # noqa: PLC0415

    if (flow_setting_from_args(a) is None) is (row["v5_setting"] == "VB"):
        diffs.append({"key": "flow_limit", "former": row["v5_setting"] == "VB",
                      "row": flow_setting_from_args(a) is not None})
    try:
        config, chk, record = run_level_config(r9, a)
    except SystemExit as e:
        return {**out, "status": "differs", "diffs": diffs + [{"key": "level_config", "former": "ok",
                                                               "row": f"SystemExit({e.code})"}]}
    out["expect_controller"] = {"name": chk["name"], "ok": chk["ok"]}
    want_las = {**r9.LAS_B0_SETTINGS, **r9.LAS_CANDIDATE_OVERRIDES[row["las_candidate"]]}
    las_diffs = r9.las_settings_diffs(config.liftoff_approach_slow, want_las)
    if las_diffs or record is None or record.get("requested") != row["las_candidate"]:
        diffs.append({"key": "las_candidate", "former": want_las, "row": las_diffs or record})
    gate = config.slope_clearance_margin.flat_soil_margin_order_gate
    if gate is not True:
        diffs.append({"key": "flat_soil_margin_order_gate", "former": True, "row": gate})
    cls, meta = r9.level_controller_class(a)
    if cls.__name__ != "C2Controller" or meta.get("requested") != "off":
        diffs.append({"key": "controller_class", "former": "C2Controller", "row": [cls.__name__, meta]})
    from outrigger_sim.params import load_params  # noqa: PLC0415

    built = cls.from_params(load_params(level=a.level), config)
    try:
        r9.check_built_las_candidate(built, None if record is None else dict(record))
    except SystemExit as e:
        diffs.append({"key": "built_las_candidate", "former": "ok", "row": f"SystemExit({e.code})"})
    if built.config.slope_clearance_margin.flat_soil_margin_order_gate is not True:
        diffs.append({"key": "built_order_gate", "former": True, "row": False})
    if bool(getattr(getattr(built.config, "touch_creep_latch", None), "enable", False)):
        diffs.append({"key": "touch_creep_latch", "former": False, "row": True})
    out["las_settings"] = None if record is None else record["settings"]
    return {**out, "status": "differs" if diffs else "ok", "diffs": diffs, "order_gate": gate}


def option_diff(a: list[str], b: list[str]) -> list[str]:
    """Options whose values differ or that only one argv has (tokens from ``level`` on)."""
    def opts(v: list[str]) -> dict[str, tuple[str, ...]]:
        out: dict[str, tuple[str, ...]] = {}
        i = 0
        while i < len(v):
            if v[i].startswith("--"):
                j = i + 1
                while j < len(v) and not v[j].startswith("--"):
                    j += 1
                out[v[i]] = tuple(v[i + 1:j])
                i = j
            else:
                i += 1
        return out

    oa, ob = opts(a[a.index("level"):]), opts(b[b.index("level"):])
    return sorted(k for k in set(oa) | set(ob) if oa.get(k) != ob.get(k))


def batch_check(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Batch-level check (rules 4.3 / K-7 / K-9): 12 rows, unique names, every pair on the same planned pool, the
    pair argv differs in ``--las-candidate`` only (ref P0, cand P5r4), the pair keys point at each other."""
    diffs: list[dict[str, Any]] = []
    by = {r["case"]: r for r in rows}
    if len(rows) != len(ROWS) or len(by) != len(rows):
        diffs.append({"key": "rows", "former": len(ROWS), "row": [len(rows), len(by)]})
    for r in rows:
        other = by.get(r["pair_case"])
        if other is None or other["pair_case"] != r["case"]:
            diffs.append({"key": "pair_case", "case": r["case"], "row": r["pair_case"]})
            continue
        if other["planned_pool"] != r["planned_pool"]:
            diffs.append({"key": "planned_pool", "case": r["case"], "row": [r["planned_pool"], other["planned_pool"]]})
        d = option_diff(r["argv"], other["argv"])
        if d != ["--las-candidate"]:
            diffs.append({"key": "pair_argv_diff", "case": r["case"], "row": d})
        if {r["las_candidate"], other["las_candidate"]} != {"P0", "P5r4"}:
            diffs.append({"key": "pair_candidates", "case": r["case"],
                          "row": [r["las_candidate"], other["las_candidate"]]})
    return {"case": "<batch>", "source": None, "status": "differs" if diffs else "ok", "diffs": diffs}


# --------------------------------------------------------------------------------------------- G-S field check
I_KEYS = ("P3-1_recontact_pass", "P3-1_crawler_zero_after_ready", "P3-2_within", "P3-3_within", "P3-4_within_0p2",
          "P3-5_within", "P3-6_within", "P3-7_within", "P3-8_within")
"""Rules 6.3: the judged item set I of ``p3b.checks``."""
RESULT_KEY_PATHS: tuple[str, ...] = (
    *(f"p3b.checks.{k}" for k in I_KEYS),
    "p3b.checks.P3-2_late_loc_reapproach", "p3b.checks.P3-2_late_loc_revoked", "p3b.checks.P3-4_window_short",
    "p3b.P3-3_leg_force.F_min_after_N", "p3b.P3-3_leg_force.F_min_transient_N",
    "p3b.P3-5_clearance_stroke.s_motor_max_m", "p3b.P3-6_ready.t_ready_after_loop_start_s",
    "controller_meta.liftoff_approach_slow.settings", "controller_meta.liftoff_approach_slow.start_s",
    "controller_meta.liftoff_approach_slow.end_s", "controller_meta.liftoff_approach_slow.end_reason",
    "controller_meta.liftoff_approach_slow.active_periods", "controller_meta.liftoff_approach_slow.ramp",
    "controller_meta.liftoff_approach_slow.ramp.periods_applied",
    "controller_meta.slope_clearance_margin.settings",
    "controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate",
    "controller_meta.slope_clearance_margin.order_gate.enabled",
    "controller_meta.slope_clearance_margin.order_gate.decisions",
    "controller_meta.loc_revoke", "controller_meta.soil.mode_starts", "controller_meta.soil.t_P_s",
    "controller_meta.soil.t_loc_s", "controller_meta.touch_creep_latch",
    "c2_setup.las_candidate.requested", "c2_setup.las_candidate.settings", "c2_setup.las_candidate.built_check",
    "c2_setup.k1_order_gate", "c2_setup.k1_order_gate_effective", "c2_setup.k1_forced_block",
    "c2_setup.expect_controller.ok", "c2_setup.touch_creep", "c2_setup.touch_creep_effective",
    "args.threads", "args.las_candidate", "args.duration", "num_threads_chrono",
    "placement.affinity_ok", "placement.power_throttling_off_ok", "placement.omp_wait_policy", "placement.mode",
    "hull_hook.mode", "hull_hook.requested", "hull_hook.fallback_reason", "hull_hook.dll_sha256",
    "code_state.git_at_start.head", "code_state.git_at_start.dirty", "code_state.files_at_start",
    "code_files_at_start.files", "code_files_at_start.head",
    "loc_corrections.locs", "loc_corrections.settings",
    "events", "phases", "t_loop_start_s", "mass_scale")
"""Key paths the judge tools read (rules 5.2 / 6.3 / 9 and the 16.2 (b) list) + the LOC-correction record; a key must
exist (its value may be None, e.g. no LOC in a 10 s G-S loop)."""
BATCH_TOP_KEYS = ("batch", "cases", "mixed_hull_mode", "failed")
BATCH_ENTRY_KEYS = ("case", "argv", "rc", "pool", "planned_pool", "omp_wait_policy", "hull_hook_requested",
                    "hull_hook_effective", "p5k_id", "las_candidate", "pair_case", "start_env", "code_at_launch",
                    "controller", "v5_setting")
NPZ_ARRAYS = ("t_s", "issued_u_m_s")
_MISSING = object()


def _get(doc: Any, path: str) -> Any:
    node = doc
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


def field_check(folder: Path, batch_name: str | None = None) -> dict[str, Any]:
    """Rules 16.2 (b) field check of a finished batch folder: presence only (files, arrays, key paths), no values.
    ``batch_name`` defaults to ``batch.json`` ``batch``; it must be :data:`P5K_BATCH` or :data:`P5K_GS_BATCH`."""
    import numpy as np  # noqa: PLC0415

    folder = Path(folder)
    out: dict[str, Any] = {"folder": folder.as_posix(), "errors": [], "cases": []}
    bpath, ppath = folder / "batch.json", folder / "progress.log"
    batch = json.loads(bpath.read_text("utf-8")) if bpath.is_file() else None
    out["batch_json"] = batch is not None
    out["progress_log"] = ppath.is_file()
    name = batch_name or (batch or {}).get("batch")
    if name not in (P5K_BATCH, P5K_GS_BATCH):
        out["errors"].append(f"batch name {name!r} is not {P5K_BATCH} / {P5K_GS_BATCH}")
        out["ok"] = False
        return out
    out["batch"] = name
    sb = _import("s9_batch")
    rows = sb.batches()[name]
    if batch is not None:
        out["batch_top_missing"] = [k for k in BATCH_TOP_KEYS if k not in batch]
    entries = {e.get("case"): e for e in (batch or {}).get("cases", [])}
    progress = ppath.read_text("utf-8", errors="replace") if ppath.is_file() else ""
    end_rc = {}
    for line in progress.splitlines():
        mt = re.match(r"END (\S+) \S+ rc=(-?\d+|None)", line)
        if mt:
            end_rc[mt.group(1)] = mt.group(2)
    for r in rows:
        case = r["case"]
        c: dict[str, Any] = {"case": case, "p5k_id": r["p5k_id"]}
        c["progress_end"] = case in end_rc
        c["progress_end_rc0"] = end_rc.get(case) == "0"
        e = entries.get(case)
        c["batch_entry"] = e is not None
        c["batch_entry_missing"] = [] if e is None else [k for k in BATCH_ENTRY_KEYS if k not in e]
        c["batch_entry_rc0"] = e is not None and e.get("rc") == 0
        res = folder / case / "result.json"
        c["result_json"] = res.is_file()
        c["result_missing"] = list(RESULT_KEY_PATHS)
        if res.is_file():
            try:
                doc = json.loads(res.read_text("utf-8"))
                c["result_missing"] = [p for p in RESULT_KEY_PATHS if _get(doc, p) is _MISSING]
            except (OSError, json.JSONDecodeError) as ex:
                c["result_error"] = type(ex).__name__
        npz = folder / case / "controller_commands.npz"
        c["controller_commands_npz"] = npz.is_file()
        c["npz_arrays_missing"] = list(NPZ_ARRAYS)
        c["npz_arrays_nonempty"] = False
        if npz.is_file():
            with np.load(npz, allow_pickle=False) as z:
                c["npz_arrays_missing"] = [k for k in NPZ_ARRAYS if k not in z.files]
                c["npz_arrays_nonempty"] = not c["npz_arrays_missing"] and all(z[k].size > 0 for k in NPZ_ARRAYS)
        c["ok"] = (c["progress_end_rc0"] and c["batch_entry"] and not c["batch_entry_missing"] and c["batch_entry_rc0"]
                   and c["result_json"] and not c["result_missing"] and "result_error" not in c
                   and c["controller_commands_npz"] and c["npz_arrays_nonempty"])
        out["cases"].append(c)
    out["n_rows"] = len(rows)
    out["n_ok"] = sum(1 for c in out["cases"] if c["ok"])
    out["ok"] = (not out["errors"] and out["batch_json"] and out["progress_log"]
                 and not out.get("batch_top_missing") and out["n_ok"] == len(rows))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=f"{P5K_BATCH} / {P5K_GS_BATCH} build checks and G-S field check "
                                             "(no simulation)")
    sub = ap.add_subparsers(dest="cmd")
    bc = sub.add_parser("check", help="build checks of the rows (default)")
    bc.add_argument("--gs", action="store_true", help=f"check {P5K_GS_BATCH} instead of {P5K_BATCH}")
    bc.add_argument("--out", default=None)
    fc = sub.add_parser("gs-check", help="rules 16.2 (b) field check of a batch folder (presence only)")
    fc.add_argument("folder")
    fc.add_argument("--batch", default=None, choices=(P5K_BATCH, P5K_GS_BATCH))
    fc.add_argument("--out", default=None)
    a = ap.parse_args(argv if argv is not None else sys.argv[1:] or ["check"])
    if a.cmd == "gs-check":
        if not Path(a.folder).is_dir():
            print(f"gs-check: no folder {a.folder}", file=sys.stderr)
            return 2
        doc = field_check(Path(a.folder), a.batch)
    else:
        sb = _import("s9_batch")
        name = P5K_GS_BATCH if a.gs else P5K_BATCH
        rows = sb.batches()[name]
        doc = {"batch": name, "checks": [argv_check(r, sb) for r in rows] + [batch_check(rows)]}
        doc["ok"] = not any(c["status"] == "differs" for c in doc["checks"])
    if a.cmd == "gs-check":
        n_err = len(doc["errors"]) + sum(1 for c in doc["cases"] if not c["ok"]) \
            + (0 if doc.get("batch_json") else 1) + (0 if doc.get("progress_log") else 1) \
            + len(doc.get("batch_top_missing") or ())
    else:
        n_err = sum(1 for c in doc["checks"] if c["status"] == "differs")
    doc["n_errors"] = n_err
    text = json.dumps(doc, indent=1, default=str)
    if a.out:
        Path(a.out).write_text(text, "utf-8")
    print(text)
    print(f"errors {n_err}")  # plain line for log_errors.py (rules 16.3)
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
