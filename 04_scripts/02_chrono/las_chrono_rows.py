"""LAS-b (lift-off approach slowdown, spec 436, ``las_judgement.md``) Chrono check rows (definitions only; cad 2026-11-08).

Batch ``V5-LAS-CHRONO`` of ``s9_batch`` (``list`` / ``check-sources`` / ``run``): LAS-b off / on pairs of the harness
problem family ``D1|H-R-A|rigid+J1@FR|T|diag-op`` (rigid base, J1 patch under FR, auger top, floor rpB-op
(2.3351, 1.5017) deg, K1 / K3).

Engine choice (cad 2026-11-08): the S9 SCM model has no rigid contact at all (``scm_model.S9Model``: SMC system, pads /
crawler only on SCM rays; run_S9 ``d424_cases`` note "the S9 model has no rigid base"). Chrono itself can mix a rigid
patch with an SCM patch (``demo_VEH_RigidSCMTerrain_MixedPatches.cpp``, chrono-rag 10.0.0), but that would be a new
S9Model contact path in 03_src, not a row definition. The nearest existing model is used instead:

* base G1 (compacted gravel K30, ``scm_soil_sets.json``) under FL / RL / RR and the crawler, J1 patch under FR (G6
  triple layout ``--soil-patch FR:J1``, patch grid 0.01 m), pad B, auger top, F_s 4 kN (D-1 Chrono convention), floor
  (2.3351, 1.5017) deg, ``--start-limit record_only`` (harness preset_config: target acceptance off), closed loop
  160 s (S9SL length), VB plant arguments ``s9_batch.v5_vb_argv()``, ``--threads`` fixed (``run_S9.SCM_THREADS_FIXED``).
* crawler K1 = G1 as it is; K3 analogue (optional) = ``--soil-override elastic_K=<3 x G1 elastic_K>`` on the base
  set (the patch set takes no override): the SCM unloading branch of the crawler (and the elastic reload of the three
  G1 pads) x3. It is not the harness K3 (crawler contact stiffness x3 on a rigid floor); recorded as an analogue.

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

Estimates (ASSUMPTION): ``run_S9.final_est_pool_s`` of the G6 form (G1 base + patch, 168 s basis P 8,500 / E 11,100 s;
the floor slope is not in the G6 basis) x ``s9_batch.V5_SOIL_VB_FACTOR`` (1.2). Cross-check: the running D-1 G1 + J1@FL
VB rows (200 s loop) were estimated 12,600 s, x 168 / 208 = 10,200 s.
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
LAS_BASE, LAS_PATCH_SET, LAS_PATCH_LEG = "G1", "J1", "FR"
LAS_PAD, LAS_LEVEL, LAS_FS_KN = "B", "top", 4.0
LAS_DURATION_S = 160.0
"""Closed loop after the 8 s settle (S9SL length; harness READY of the family 68.7 s, P3-6 slope limit 120 s)."""
LAS_OFF_CONTROLLER = "final_C4G2_P3"
LAS_ON_CONTROLLER = "final_C4G2_P3_LAS"
"""python-expert tag (``s9_batch.V5_P3_LAS_CONTROLLER`` after the merge)."""
PRE_LAS_RUNNER = ROOT / "05_tests" / "unit" / "pre_las_preset_runner.py"
START_ENV = {"OMP_WAIT_POLICY": "PASSIVE"}
K3_FACTOR = 3.0
CRAWLER_VARIANTS: tuple[tuple[str, bool], ...] = (("K1", False), ("K3", True))
"""(variant, optional). K3 = elastic_K x :data:`K3_FACTOR` on the base set (analogue, see module doc)."""


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


def base_elastic_k(soil: str = LAS_BASE) -> float:
    doc = json.loads((ROOT / "02_params" / "scm_soil_sets.json").read_text("utf-8"))
    return float(doc["sets"][soil]["chrono"]["elastic_K"])


def _tag(v: float) -> str:
    return f"{v:g}".replace("-", "m").replace(".", "p")


def base_case(r9: ModuleType) -> dict[str, Any]:
    """The run_S9 case dict shared by all rows (G6 triple layout + S9SL floor / start-limit keys)."""
    c = r9.g6_case(LAS_BASE, LAS_PATCH_SET, LAS_PATCH_LEG, pad=LAS_PAD, level=LAS_LEVEL, fs=LAS_FS_KN,
                   group=LAS_BATCH, duration_s=LAS_DURATION_S)
    c.update(floor_deg=LAS_FLOOR_DEG, start_limit=r9.S9SL_START_LIMIT)
    return c


def las_rows(sb: ModuleType) -> list[dict[str, Any]]:
    """2 required (K1 off / on) + 2 optional (K3 analogue off / on) rows."""
    r9 = _r9()
    merged = las_merged(r9)
    k_el = base_elastic_k()
    roll, pitch = LAS_FLOOR_DEG
    rows = []
    for variant, optional in CRAWLER_VARIANTS:
        for las in ("off", "on"):
            c = base_case(r9)
            ctrl = LAS_OFF_CONTROLLER if las == "off" else getattr(sb, "V5_P3_LAS_CONTROLLER", LAS_ON_CONTROLLER)
            c["controller"] = ctrl
            c["case"] = (f"LASC_{LAS_BASE}_{LAS_PAD}_{LAS_LEVEL}_Fs{LAS_FS_KN:g}_sp{LAS_PATCH_SET}{LAS_PATCH_LEG}"
                         f"_r{_tag(roll)}_p{_tag(pitch)}_{variant}_las{las}")
            level_argv = r9.p3b_level_argv(c)
            if variant == "K3":
                level_argv[3:3] = ["--soil-override", f"elastic_K={K3_FACTOR * k_el:g}"]
            head = list(sb.RUN)
            if las == "off" and merged:
                head = head[:-1] + [str(PRE_LAS_RUNNER), head[-1]]
            est = r9.final_est_pool_s({k: v for k, v in c.items() if k != "floor_deg"})
            pools = {k: round(v * sb.V5_SOIL_VB_FACTOR, -2) for k, v in est.items()}
            ready = las == "off" or merged
            r = {"case": c["case"], "est_s": pools["pcore"], "est_pool_s": pools,
                 "argv": head + level_argv + sb.v5_vb_argv(), "controller": ctrl, "group": LAS_BATCH,
                 "criteria_id": f"LAS-C-{variant}", "v5_setting": "VB", "planned_pool": "pcore",
                 "las": las, "las_family": LAS_FAMILY, "las_crawler": variant, "las_ready": ready,
                 "pair_case": c["case"][:-len(las)] + ("on" if las == "off" else "off"),
                 "start_env": dict(START_ENV),
                 "note": (f"{LAS_BATCH} {variant} LAS-b {las}: G1 base + J1@FR (triple layout), pad B top, F_s 4 kN, "
                          f"floor ({roll:g}, {pitch:g}) deg, record_only start, {LAS_DURATION_S:g} s, SCM VB, "
                          f"{ctrl}; Chrono stand-in of {LAS_FAMILY} {variant} (no rigid base in S9)"
                          + ("; K3 analogue = base elastic_K x3" if variant == "K3" else "")
                          + ("" if las == "on" or not merged else "; pre_las_preset_runner"))}
            if optional:
                r["optional"] = True
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
    want = {"threads": r9.SCM_THREADS_FIXED, "soil": LAS_BASE, "soil_patch": f"{LAS_PATCH_LEG}:{LAS_PATCH_SET}",
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
    return {"case": row["case"], "build_s": time.perf_counter() - t0, "soil_patch_leg": model.soil_patch_leg,
            "soil_patch_set": model.soil_patch_set.key, "soil_patch_grid_m": model.soil_patch_grid_m,
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
