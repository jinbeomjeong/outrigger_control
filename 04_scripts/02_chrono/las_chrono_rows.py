"""LAS-b (lift-off approach slowdown, spec 436, ``las_judgement.md``) Chrono check rows (definitions only; cad 2026-11-08).

Batch ``V5-LAS-CHRONO`` of ``s9_batch`` (``list`` / ``check-sources`` / ``run``): LAS-b off / on pairs of the harness
problem family ``D1|H-R-A|rigid+J1@FR|T|diag-op`` (rigid base, J1 patch under FR, auger top, floor rpB-op
(2.3351, 1.5017) deg, K1 / K3).

Engine (cad 2026-11-08 rev. 2, user decision "강체 + SCM 혼합 지형, 구현 뒤 LAS 확인"): the S9 mixed ground
``S9Model(rigid_base=RigidBaseSpec(("FR",), k))`` (``03_src/outrigger_sim/chrono/rigid_base.py``; Chrono pattern
``demo_VEH_RigidSCMTerrain_MixedPatches.cpp:148``): rigid SMC base (L1 floor-patch path, concrete k 3.24e8 N/m on the
FL / RL / RR pad spheres, the 24 L1 crawler spheres) + J1 SCM under FR only (``--rigid-base FR --soil J1 --grid
0.01``), i.e. the harness family itself ``rigid+J1@FR``:

* pad B, auger top, F_s 4 kN (D-1 Chrono convention), floor (2.3351, 1.5017) deg, ``--start-limit record_only``
  (harness preset_config: target acceptance off), closed loop 160 s (S9SL length), VB plant arguments
  ``s9_batch.v5_vb_argv()``, ``--threads`` fixed (``run_S9.SCM_THREADS_FIXED``);
* crawler K1 = YAML ``contact.crawler.kn_total_N_m`` (1e8 N/m), K3 = ``--crawler-kn-scale 3`` (spheres x3, dashpot
  x sqrt 3, same heave zeta) = the harness K3 (crawler contact stiffness x3 on a rigid floor).

Rev. 1 (d4ceda6, superseded) used the G6 triple layout G1 base + J1@FR patch with a K3 analogue (G1 elastic_K x3).

LAS-b off / on: the rows do not pin the controller; the run-time preset ``C2Config().with_10hz_d1()`` runs and
``--expect-controller`` refuses a wrong preset.

* off: tag ``final_C4G2_P3``. Before the LAS-b 03_src merge the preset has no ``liftoff_approach_slow`` block, so the
  plain run_S9 argv is the off row. After the merge (``run_S9.FINAL_P3_LAS_CONTROLLER`` present) the off row runs
  through ``05_tests/unit/pre_las_preset_runner.py`` (preset keyword ``liftoff_approach_slow=False`` only).
* on: tag ``final_C4G2_P3_LAS`` (python-expert name). Before the merge the row is defined but ``las_ready`` is False
  and its build check reports ``blocked_pre_merge`` (run_S9 would refuse the unknown tag at argparse anyway).

Start env: ``OMP_WAIT_POLICY=PASSIVE`` (project SCM rule 2026-11-08, bit-identical) through the row key ``start_env``
(``s9_batch.run_batch``); P pool planned.

Compared quantities (off vs on, per K variant; run_S9 ``result.json`` p3b blocks):

1. ``P3-3_leg_force.F_min_after_N`` (true F_cyl, 1 ms, per leg, after the crawler departure) and
   ``F_min_transient_N`` (departure .. + lift-off transient window): event leg = the minimum leg (harness: RL, the
   diagonal of the FR patch).
2. ``P3-2_loc.loc_minus_departure_s`` (LOC - t_off) against ``limit_s``.
3. READY: ``P3-6_ready`` (first READY relative to the closed-loop start, limit 120 s on a slope).
4. Stroke: maximum stroke / ``P3-5_clearance_stroke`` (harness C5: increase <= 1 mm).
5. LAS record (on rows): controller events ``INFO_LIFTOFF_SLOW:<leg>`` / ``INFO_LIFTOFF_SLOW_END:<reason>``, start
   time and active periods (controller meta ``liftoff_approach_slow``); off rows must have none.

Harness reference (``las_judgement.md`` 3.1, K1 VB e0): base 9.103 kN -> b0 11.377 kN, LOC - t_off 1.0 s, READY +0.5 s.

Estimates (ASSUMPTION): :data:`MIXED_US_PER_STEP` (measured on the mixed ground, see there) x 168 s / dt x
``s9_batch.V5_SOIL_VB_FACTOR`` (1.2); E pool x :data:`E_POOL_FACTOR`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

LAS_BATCH = "V5-LAS-CHRONO"
LAS_SOURCE = "s6_control_spec.md 436 / 06_analysis/02_control/verif_matrix/las_judgement.md 7 L-8 (2026-11-08)"
LAS_FAMILY = "D1|H-R-A|rigid+J1@FR|T|diag-op"
LAS_FLOOR_DEG = (2.3351, 1.5017)
"""rpB-op floor (roll, pitch) [deg] of the harness family (``v5/d1.jsonl`` job.d1 roll_deg / pitch_deg)."""
LAS_BASE, LAS_PATCH_SET, LAS_PATCH_LEG = "rigid", "J1", "FR"
"""Rigid base, J1 SCM under FR (``--rigid-base FR --soil J1``)."""
LAS_GRID_M = 0.01
"""J1 pad grid (``run_S9.P3B_PAD_GRID_M``)."""
LAS_PAD, LAS_LEVEL, LAS_FS_KN = "B", "top", 4.0
LAS_DURATION_S = 160.0
"""Closed loop after the 8 s settle (S9SL length; harness READY of the family 68.7 s, P3-6 slope limit 120 s)."""
LAS_OFF_CONTROLLER = "final_C4G2_P3"
LAS_ON_CONTROLLER = "final_C4G2_P3_LAS"
"""python-expert tag (``s9_batch.V5_P3_LAS_CONTROLLER`` after the merge)."""
PRE_LAS_RUNNER = ROOT / "05_tests" / "unit" / "pre_las_preset_runner.py"
START_ENV = {"OMP_WAIT_POLICY": "PASSIVE"}
K3_FACTOR = 3.0
CRAWLER_VARIANTS: tuple[tuple[str, float], ...] = (("K1", 1.0), ("K3", K3_FACTOR))
"""(variant, ``--crawler-kn-scale``); all four rows required (user decision 2026-11-08: K1 / K3 x LAS off / on)."""
MIXED_US_PER_STEP = {"pcore": 2500.0, "ecore": 3300.0}
"""ASSUMPTION: per-step cost [us] of the mixed ground (rigid base + one 1 cm J1 pad terrain, 4 threads) under a
parallel P batch; set from the rigid+FR smoke (see the cad report 2026-11-08) with margin."""
E_POOL_FACTOR = 1.3


def _r9() -> ModuleType:
    sys.path.insert(0, str(HERE))
    try:
        import run_S9 as r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    return r9


def las_merged(r9: ModuleType | None = None) -> bool:
    """Whether the LAS-b switch is in this tree (run_S9 knows the LAS tag and the pre-LAS runner exists)."""
    r9 = r9 or _r9()
    return LAS_ON_CONTROLLER in getattr(r9, "CONTROLLER_EXPECTATIONS", {}) and PRE_LAS_RUNNER.is_file()


def _tag(v: float) -> str:
    return f"{v:g}".replace("-", "m").replace(".", "p")


def base_case(r9: ModuleType) -> dict[str, Any]:
    """The run_S9 case dict shared by all rows: the P3b case of J1 (pad B, top, F_s 4 kN, grid 0.01) with the S9SL
    floor / start-limit keys and the loop length; :func:`level_argv` turns it into the mixed-ground argv."""
    c = r9.p3b_case(LAS_BATCH, LAS_PATCH_SET, LAS_PAD, LAS_LEVEL, LAS_FS_KN)
    c.update(floor_deg=LAS_FLOOR_DEG, start_limit=r9.S9SL_START_LIMIT, duration_s=LAS_DURATION_S,
             grid_m=LAS_GRID_M)
    return c


def level_argv(r9: ModuleType, c: dict[str, Any], kn_scale: float) -> list[str]:
    """``run_S9.p3b_level_argv`` of the case without ``--crawler-grid`` and with ``--rigid-base FR`` (+
    ``--crawler-kn-scale`` for K3) inserted after the soil."""
    a = r9.p3b_level_argv(c)
    k = a.index("--crawler-grid")
    del a[k:k + 2]
    extra = ["--rigid-base", LAS_PATCH_LEG] + ([] if kn_scale == 1.0 else ["--crawler-kn-scale", f"{kn_scale:g}"])
    a[3:3] = extra
    return a


def est_pool_s() -> dict[str, float]:
    sim_s = 8.0 + LAS_DURATION_S
    p = sim_s / 1.0e-4 * MIXED_US_PER_STEP["pcore"] * 1e-6
    return {"pcore": round(p, -2), "ecore": round(sim_s / 1.0e-4 * MIXED_US_PER_STEP["ecore"] * 1e-6 * E_POOL_FACTOR,
                                                 -2)}


def las_rows(sb: ModuleType) -> list[dict[str, Any]]:
    """4 required rows: K1 / K3 x LAS-b off / on (mixed ground rigid + J1@FR)."""
    r9 = _r9()
    merged = las_merged(r9)
    roll, pitch = LAS_FLOOR_DEG
    rows = []
    for variant, kn_scale in CRAWLER_VARIANTS:
        for las in ("off", "on"):
            c = base_case(r9)
            ctrl = LAS_OFF_CONTROLLER if las == "off" else getattr(sb, "V5_P3_LAS_CONTROLLER", LAS_ON_CONTROLLER)
            c["controller"] = ctrl
            c["case"] = (f"LASC_{LAS_BASE}_{LAS_PATCH_SET}{LAS_PATCH_LEG}_{LAS_PAD}_{LAS_LEVEL}_Fs{LAS_FS_KN:g}"
                         f"_r{_tag(roll)}_p{_tag(pitch)}_{variant}_las{las}")
            argv_level = level_argv(r9, c, kn_scale)
            head = list(sb.RUN)
            if las == "off" and merged:
                head = head[:-1] + [str(PRE_LAS_RUNNER), head[-1]]
            pools = {k: round(v * sb.V5_SOIL_VB_FACTOR, -2) for k, v in est_pool_s().items()}
            ready = las == "off" or merged
            r = {"case": c["case"], "est_s": pools["pcore"], "est_pool_s": pools,
                 "argv": head + argv_level + sb.v5_vb_argv(), "controller": ctrl, "group": LAS_BATCH,
                 "criteria_id": f"LAS-C-{variant}", "v5_setting": "VB", "planned_pool": "pcore",
                 "las": las, "las_family": LAS_FAMILY, "las_crawler": variant, "las_ready": ready,
                 "pair_case": c["case"][:-len(las)] + ("on" if las == "off" else "off"),
                 "start_env": dict(START_ENV),
                 "note": (f"{LAS_BATCH} {variant} LAS-b {las}: mixed ground rigid + J1@FR (rigid_base.py), pad B top, "
                          f"F_s 4 kN, floor ({roll:g}, {pitch:g}) deg, record_only start, {LAS_DURATION_S:g} s, SCM VB, "
                          f"{ctrl}; crawler kn x{kn_scale:g}"
                          + ("" if las == "on" or not merged else "; pre_las_preset_runner"))}
            if not ready:
                r["requires"] = "LAS-b 03_src merge (run_S9 CONTROLLER_EXPECTATIONS['final_C4G2_P3_LAS'])"
            rows.append(r)
    return rows


def las_batches(sb: ModuleType) -> dict[str, list[dict[str, Any]]]:
    rows = las_rows(sb)
    names = [r["case"] for r in rows]
    if len(set(names)) != len(names):
        raise RuntimeError(f"{LAS_BATCH}: duplicate row names")
    return {LAS_BATCH: rows}


def run_level_config(r9: ModuleType, a: argparse.Namespace) -> Any:
    """The C2 config ``run_S9.run_level`` checks with ``--expect-controller`` (same steps, same order: preset, twist
    relax, start limit, SCM fallback ratio, sensor setup, v5 controller options); no Chrono object is made."""
    from outrigger_sim.chrono.fallback_ratio import with_engine_fallback_ratio  # noqa: PLC0415

    config, _ = r9.level_c2_config(a.allow_current_c2)
    config, _ = r9.apply_twist_relax(config, getattr(a, "twist_relax", r9.TWIST_RELAX_PRESET))
    config, _ = r9.apply_start_limit(config, getattr(a, "start_limit", r9.START_LIMIT_PRESET), a.level)
    config, _ = with_engine_fallback_ratio(config, "SCM")
    _, _, config, _ = r9.level_sensor_setup(a.pressure_grade, a.imu_grade, config)
    params, _, _ = r9.load_inputs(a)
    v5 = r9.v5_hydraulic_options(a, params)
    if v5 is not None:
        from outrigger_sim.hydraulics.v5_options import apply_controller_options  # noqa: PLC0415

        config = apply_controller_options(config, v5, params.actuator.max_speed_m_s, v5.valve_tau_s)
    return config


def argv_check(row: dict[str, Any], sb: ModuleType) -> dict[str, Any]:
    """Build check without Chrono: the level argv parses with the run_S9 parser, ``--threads`` = the fixed count, the
    patch / floor / start limit are the row's, and the installed preset passes ``--expect-controller`` (after the
    run_S9 start-limit step). ``blocked_pre_merge`` for an on row before the merge (not a failure)."""
    out: dict[str, Any] = {"case": row["case"], "source": None, "las": row["las"]}
    if not row["las_ready"]:
        return {**out, "status": "blocked_pre_merge", "diffs": []}
    r9 = _r9()
    argv = row["argv"]
    level = argv[argv.index("level"):]
    diffs = []
    try:
        a = r9.build_parser().parse_args(level)
    except SystemExit as e:
        return {**out, "status": "differs", "diffs": [{"key": "argparse", "former": "ok", "row": str(e)}]}
    kn = dict(CRAWLER_VARIANTS)[row["las_crawler"]]
    want = {"threads": r9.SCM_THREADS_FIXED, "soil": LAS_PATCH_SET, "rigid_base": LAS_PATCH_LEG, "soil_patch": None,
            "crawler_grid": None, "grid": LAS_GRID_M, "crawler_kn_scale": None if kn == 1.0 else kn,
            "floor_roll": LAS_FLOOR_DEG[0], "floor_pitch": LAS_FLOOR_DEG[1], "level": LAS_LEVEL,
            "start_limit": r9.S9SL_START_LIMIT, "expect_controller": row["controller"], "duration": LAS_DURATION_S}
    for k, v in want.items():
        if getattr(a, k, None) != v:
            diffs.append({"key": k, "former": v, "row": getattr(a, k, None)})
    if (str(PRE_LAS_RUNNER) in argv) != (row["las"] == "off" and las_merged(r9)):
        diffs.append({"key": "pre_las_runner", "former": row["las"] == "off" and las_merged(r9),
                      "row": str(PRE_LAS_RUNNER) in argv})
    if str(PRE_LAS_RUNNER) not in argv:  # the runner patches the preset at import; checked only on plain rows here
        chk = r9.controller_expectation(run_level_config(r9, a), row["controller"])
        if not chk["ok"]:
            diffs.append({"key": "controller_expectation", "former": row["controller"],
                          "row": [c for c in chk["checks"] if not c["ok"]]})
    return {**out, "status": "differs" if diffs else "ok", "diffs": diffs}


def build_model(row: dict[str, Any]) -> dict[str, Any]:
    """Short Chrono build (no step): the S9Model of the row's argv (terrains, patch, floor normal)."""
    import time  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415

    r9 = _r9()
    argv = row["argv"]
    a = r9.build_parser().parse_args(argv[argv.index("level"):])
    t0 = time.perf_counter()
    params, pv, soil = r9.load_inputs(a)
    model = r9.build_machine(a, params, pv, soil)
    n = np.asarray(model.floor_normal_world(), float) if callable(getattr(model, "floor_normal_world", None)) \
        else np.asarray(model.normal_world, float)
    rb = model.rigid_base
    return {"case": row["case"], "build_s": time.perf_counter() - t0, "soil_patch_leg": model.soil_patch_leg,
            "soil_patch_set": model.soil_patch_set.key, "soil_patch_grid_m": model.soil_patch_grid_m,
            "rigid_base": None if rb is None else {"scm_legs": list(rb.scm_legs),
                                                   "crawler_kn_scale": rb.crawler_kn_scale},
            "n_terrains": len(model.terrains),
            "floor_normal_world": n.tolist(), "soil_base": str(getattr(soil, "key", None)),
            "soil_base_meta": soil.meta() if callable(getattr(soil, "meta", None)) else None,
            "gravity": list(map(float, (lambda g: (g.x, g.y, g.z))(model.system.GetGravitationalAcceleration()))),
            "collision_system": type(model.system.GetCollisionSystem()).__name__,
            "system": type(model.system).__name__, "threads_arg": a.threads}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="V5-LAS-CHRONO build checks (no simulation)")
    ap.add_argument("--build", nargs="*", default=None, help="also build the S9Model of these cases (no step)")
    ap.add_argument("--out", default=None, help="JSON result file")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(HERE))
    try:
        import s9_batch as sb  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    rows = sb.batches()[LAS_BATCH]
    doc: dict[str, Any] = {"merged": las_merged(), "checks": [argv_check(r, sb) for r in rows], "builds": []}
    by = {r["case"]: r for r in rows}
    for name in a.build or ():
        doc["builds"].append(build_model(by[name]))
    doc["ok"] = not any(c["status"] == "differs" for c in doc["checks"])
    text = json.dumps(doc, indent=1, default=str)
    if a.out:
        Path(a.out).write_text(text, "utf-8")
    print(text)
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
