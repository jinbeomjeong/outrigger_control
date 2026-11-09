"""LAS-b K1 S-Ch: Chrono SCM patch check of the R4 order gate, one harness key (definitions only; cad 2026-11-09).

Batch ``V5-LAS-K1-CHRONO`` of ``s9_batch`` (``list`` / ``check-sources`` / ``run``): one off / on pair of
``level --k1-order-gate`` (``run_S9.K1_ORDER_GATE_OPTION``; ``slope_clearance_margin.flat_soil_margin_order_gate``,
``06_analysis/02_control/verif_matrix/las_k1_rules.md``) on the harness key

    ``D1|H-S-A-J2|G1+J2@FL|T|flat|K1|VB|e0``

(``04_scripts/04_hydraulic/coupled/d1_rows.py`` ``_row("H-S-A-J2", "G1", "top", "flat", patch_soil="J2",
patch_leg="FL")`` with the module constants ``PAD = "B"``, ``FS_KN = 4.0``; ``run_v5`` setting VB, phase eps 0).
NOTE: the ``K1`` field of that harness key is the crawler contact stiffness x1 (``D1Row.crawler_k_scale``), NOT the
order gate (the rules' candidate token ``K1``); the gate is the row key ``k1_candidate`` (``K1off`` / ``K1on``).

Engine: the S9 G6 layout, G1 base (grid 0.02 m, crawler grid 0.04 m) + J2 SCM patch under FL (``--soil-patch FL:J2
--soil-patch-grid 0.01``), pad B (``dwg_rear250``), auger top, F_s 4 kN, flat floor, closed loop 200 s
(``run_S9.g6_case`` ... ``p3b_level_argv``), pressure normal / IMU ideal / seed 20261026, ``--threads`` fixed
(``run_S9.SCM_THREADS_FIXED``), VB plant arguments ``s9_batch.v5_vb_argv()``.

Controller: the run-time preset ``C2Config().with_10hz_d1()`` with ``--expect-controller final_C4G2_P3_LAS`` (the
LAS-b preset, ``las_candidate`` P0 = the adopted b0 preset); both rows give ``--k1-order-gate`` explicitly (``off`` =
the preset value, written so that the pair differs only in that value). ``run_S9.run_level`` applies the gate before the
``--expect-controller`` check and stops when the built controller does not hold it.

Start env: ``OMP_WAIT_POLICY=PASSIVE`` and ``OUTRIGGER_HULL_HOOK=fast`` (project SCM rules 2026-11-08 / 11-09) through
the row key ``start_env``; P pool planned.

Estimate (ASSUMPTION): ``est_s`` 12600 s per row (the G6P J2FL rate 9500 s x the v5 VB factor about 1.2, plus margin).
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

K1C_BATCH = "V5-LAS-K1-CHRONO"
K1C_SOURCE = "06_analysis/02_control/verif_matrix/las_k1_rules.md (rev1) S-Ch; cad row definition B (2026-11-09)"
K1C_HARNESS_KEY = "D1|H-S-A-J2|G1+J2@FL|T|flat|K1|VB|e0"
"""Harness key of the pair. Its ``K1`` field = crawler stiffness x1 (``D1Row.crawler_k_scale``), not the order gate."""
K1C_BASE, K1C_PATCH_SET, K1C_PATCH_LEG = "G1", "J2", "FL"
K1C_PAD, K1C_LEVEL, K1C_FS_KN = "B", "top", 4.0
K1C_DURATION_S = 200.0
"""Closed loop after the 8 s settle (the G6 FL patch length, ``run_S9.G6_DURATION_S['J1FL']``)."""
K1C_CONTROLLER = "final_C4G2_P3_LAS"
K1C_LAS_CANDIDATE = "P0"
K1C_SETTING = "VB"
K1C_EST_S = 12600.0
"""ASSUMPTION: wall estimate per row [s] on the P pool (G6P J2FL 9500 s x VB about 1.2 + margin)."""
START_ENV = {"OMP_WAIT_POLICY": "PASSIVE", "OUTRIGGER_HULL_HOOK": "fast"}
GATES: tuple[tuple[str, str], ...] = (("off", "K1off"), ("on", "K1on"))
"""(``--k1-order-gate`` value, ``k1_candidate``)."""


def _r9() -> ModuleType:
    sys.path.insert(0, str(HERE))
    try:
        import run_S9 as r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    return r9


def case_name(gate: str) -> str:
    return f"SCh_{K1C_BASE}_{K1C_PATCH_SET}{K1C_PATCH_LEG}_{K1C_PAD}_{K1C_LEVEL}_Fs{K1C_FS_KN:g}_{K1C_SETTING}_gate{gate}"


def base_case(r9: ModuleType) -> dict[str, Any]:
    """The run_S9 G6 case dict shared by both rows (G1 base + J2@FL, pad B, top, F_s 4 kN, 200 s) + controller."""
    c = r9.g6_case(K1C_BASE, K1C_PATCH_SET, K1C_PATCH_LEG, pad=K1C_PAD, level=K1C_LEVEL, fs=K1C_FS_KN,
                   group=K1C_BATCH, duration_s=K1C_DURATION_S)
    c["controller"] = K1C_CONTROLLER
    return c


def level_argv(r9: ModuleType, sb: ModuleType, gate: str) -> list[str]:
    """``run_S9.py level`` argv of a row: the G6 / P3b argv + VB plant arguments + ``--k1-order-gate <gate>``."""
    return r9.p3b_level_argv(base_case(r9)) + sb.v5_vb_argv() + [r9.K1_ORDER_GATE_OPTION, gate]


def k1_rows(sb: ModuleType) -> list[dict[str, Any]]:
    """2 rows: ``--k1-order-gate`` off / on (pair)."""
    r9 = _r9()
    rows = []
    for gate, cand in GATES:
        other = "on" if gate == "off" else "off"
        rows.append({
            "case": case_name(gate), "est_s": K1C_EST_S,
            "argv": list(sb.RUN) + level_argv(r9, sb, gate), "controller": K1C_CONTROLLER, "group": K1C_BATCH,
            "criteria_id": f"LAS-K1-SCh-{cand}", "v5_setting": K1C_SETTING, "planned_pool": "pcore",
            "start_env": dict(START_ENV), "las_candidate": K1C_LAS_CANDIDATE, "k1_candidate": cand,
            "k1_order_gate": gate, "pair_case": case_name(other),
            # harness key; its "K1" = crawler stiffness x1, not the order gate (k1_candidate)
            "harness_case": K1C_HARNESS_KEY,
            "note": (f"{K1C_BATCH} {cand}: G1 + J2@FL (G6 layout), pad B top, F_s 4 kN, flat, {K1C_DURATION_S:g} s, "
                     f"SCM VB, {K1C_CONTROLLER}, --k1-order-gate {gate}; harness {K1C_HARNESS_KEY} "
                     "(K1 there = crawler stiffness x1)")})
    return rows


def k1_batches(sb: ModuleType) -> dict[str, list[dict[str, Any]]]:
    rows = k1_rows(sb)
    names = [r["case"] for r in rows]
    if len(set(names)) != len(names):
        raise RuntimeError(f"{K1C_BATCH}: duplicate row names")
    return {K1C_BATCH: rows}


def run_level_config(r9: ModuleType, a: argparse.Namespace) -> Any:
    """The C2 config ``run_S9.run_level`` checks with ``--expect-controller`` (same steps, same order: preset with
    ``--las-off`` / ``--k1-order-gate``, twist relax, start limit, SCM fallback ratio, sensor setup, v5 controller
    options); no Chrono object is made."""
    from outrigger_sim.chrono.fallback_ratio import with_engine_fallback_ratio  # noqa: PLC0415

    config, _ = r9.level_c2_config_of_args(a)
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
    """Build check without Chrono: the level argv parses with the run_S9 parser, ``--threads`` = the fixed count,
    soil / patch / pad / level / F_s / duration are the row's, ``--k1-order-gate`` is the row's, and the run-time config
    (with the gate) passes ``--expect-controller`` and holds the requested gate."""
    out: dict[str, Any] = {"case": row["case"], "source": None, "k1_candidate": row["k1_candidate"]}
    r9 = _r9()
    argv = row["argv"]
    level = argv[argv.index("level"):]
    diffs = []
    try:
        a = r9.build_parser().parse_args(level)
    except SystemExit as e:
        return {**out, "status": "differs", "diffs": [{"key": "argparse", "former": "ok", "row": str(e)}]}
    want = {"threads": r9.SCM_THREADS_FIXED, "soil": K1C_BASE,
            "soil_patch": f"{K1C_PATCH_LEG}:{K1C_PATCH_SET}", "soil_patch_grid": r9.P3B_PAD_GRID_M[K1C_PATCH_SET],
            "pad_variant": r9.P3B_PAD[K1C_PAD], "level": K1C_LEVEL, "fs_kN": K1C_FS_KN, "duration": K1C_DURATION_S,
            "k1_order_gate": row["k1_order_gate"], "expect_controller": row["controller"]}
    for k, v in want.items():
        got = getattr(a, k, None)
        if isinstance(got, (list, tuple)) and len(got) == 1:
            got = got[0]
        if got != v and str(got) != str(v):
            diffs.append({"key": k, "former": v, "row": got})
    config = run_level_config(r9, a)
    chk = r9.controller_expectation(config, row["controller"])
    if not chk["ok"]:
        diffs.append({"key": "controller_expectation", "former": row["controller"],
                      "row": [c for c in chk["checks"] if not c["ok"]]})
    gate = config.slope_clearance_margin.flat_soil_margin_order_gate
    if gate is not (row["k1_order_gate"] == "on"):
        diffs.append({"key": "flat_soil_margin_order_gate", "former": row["k1_order_gate"] == "on", "row": gate})
    return {**out, "status": "differs" if diffs else "ok", "diffs": diffs, "order_gate": gate}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=f"{K1C_BATCH} build checks (no simulation)")
    ap.add_argument("--out", default=None, help="JSON result file")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(HERE))
    try:
        import s9_batch as sb  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    rows = sb.batches()[K1C_BATCH]
    doc: dict[str, Any] = {"checks": [argv_check(r, sb) for r in rows]}
    doc["ok"] = not any(c["status"] == "differs" for c in doc["checks"])
    text = json.dumps(doc, indent=1, default=str)
    if a.out:
        Path(a.out).write_text(text, "utf-8")
    print(text)
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
