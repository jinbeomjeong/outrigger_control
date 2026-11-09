"""K1 re-measure: Chrono SCM gate off / on rows on uniform soft soil (definitions only; cad 2026-11-09).

Batch ``V5-LAS-K1-REM`` of ``s9_batch`` (``list`` / ``check-sources`` / ``run``), rules
``06_analysis/02_control/verif_matrix/las_k1_rules_adopt2.md`` (sha256 ``fb3a5696...68e8``) 2.1-2.3 and 9.3: 8 judge
rows R1 .. R8 (``role`` ``judge``) + 2 diagnostic rows F1 / F2 (``role`` ``diag``, information only).

Row form (rules 2.1): ``run_S9.p3b_case("V5-LAS-K1-REM", soil, "B", level, 4.0)`` with ``mass_scale`` 1.1 on the x1.1
rows (``--mass-scale 1.1``, the MS1 / RV1 X5 / FINAL-REP x1.1 convention of ``run_S9.p3b_level_argv``) and
``controller`` (``--expect-controller``) -> ``run_S9.p3b_level_argv`` + plant arguments (VB = ``s9_batch.v5_vb_argv()``,
V0 = none) + ``--k1-order-gate <off|on>`` (every row, explicit) + ``--k1-forced-block first`` (F1 / F2 only).

Common: pad B (``dwg_rear250``), F_s 4 kN, flat floor, uniform soil (no patch), P3b pad grid, closed loop 120 s (P3b
fixed), ``--threads`` = ``run_S9.SCM_THREADS_FIXED`` (4), pressure normal / IMU ideal / seed 20261026 (P3b), start env
``OMP_WAIT_POLICY=PASSIVE`` + ``OUTRIGGER_HULL_HOOK=fast`` (row key ``start_env``), planned pool P. Pair sets
(R1, R7, F1) and (R4, R8, F2) run on the same pool kind.

Controller: the run-time preset ``C2Config().with_10hz_d1()`` (LAS-b b0, ``las_candidate`` P0); VB rows
``--expect-controller final_C4G2_P3_LAS``, R5 (V0, no v5 argument) ``final_C4G2_LAS``.

Estimate (ASSUMPTION, rules 11): ``est_s`` 4400 s per x1.0 row, 5500 s per x1.1 row (P, 4 threads, one row alone;
4 rows at once may be 1.2-1.5x slower; nominal 5650 s per row).
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

REM_BATCH = "V5-LAS-K1-REM"
REM_RULES = "06_analysis/02_control/verif_matrix/las_k1_rules_adopt2.md"
REM_RULES_SHA256 = "fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8"
REM_SOURCE = f"{REM_RULES} (sha256 {REM_RULES_SHA256[:8]}) 2.2 / 2.3; cad row definition (2026-11-09)"
REM_PAD, REM_FS_KN = "B", 4.0
REM_LAS_CANDIDATE = "P0"
REM_SEED = 20261026
VB_CONTROLLER, V0_CONTROLLER = "final_C4G2_P3_LAS", "final_C4G2_LAS"
CONTROLLER_OF_SETTING = {"VB": VB_CONTROLLER, "V0": V0_CONTROLLER}
REM_EST_S = {1.0: 4400.0, 1.1: 5500.0}
"""ASSUMPTION (rules 11): wall per row [s] on the P pool by plant mass scale."""
START_ENV = {"OMP_WAIT_POLICY": "PASSIVE", "OUTRIGGER_HULL_HOOK": "fast"}
PLANNED_POOL = "pcore"

# (rem_key, soil, level, mass_scale, v5_setting, gate, forced, role)
REM_ROWS: tuple[tuple[str, str, str, float, str, str, str, str], ...] = (
    ("R1", "J2", "top", 1.0, "VB", "off", "off", "judge"),
    ("R2", "J2", "middle", 1.0, "VB", "off", "off", "judge"),
    ("R3", "J2", "bottom", 1.0, "VB", "off", "off", "judge"),
    ("R4", "J2", "top", 1.1, "VB", "off", "off", "judge"),
    ("R5", "J2", "top", 1.1, "V0", "off", "off", "judge"),
    ("R6", "J1", "top", 1.1, "VB", "off", "off", "judge"),
    ("R7", "J2", "top", 1.0, "VB", "on", "off", "judge"),
    ("R8", "J2", "top", 1.1, "VB", "on", "off", "judge"),
    ("F1", "J2", "top", 1.0, "VB", "on", "first", "diag"),
    ("F2", "J2", "top", 1.1, "VB", "on", "first", "diag"),
)
"""Rules 2.2 (R1 .. R8) and 2.3 (F1, F2)."""
PAIR_SETS: tuple[tuple[str, ...], ...] = (("R1", "R7", "F1"), ("R4", "R8", "F2"))
"""Rules 2.1 / K-4: same pool kind inside a set."""
PAIR_CASE = {"R1": "R7", "R7": "R1", "R4": "R8", "R8": "R4", "F1": "R1", "F2": "R4"}
"""L1 pair (rules 3.4 K-7: R7 <-> R1, R8 <-> R4; 2.3 FORCED_PAIR_L1: F1 -> R1, F2 -> R4)."""
ARGV_BASE = {"R7": ("R1", "--k1-order-gate"), "R8": ("R4", "--k1-order-gate"),
             "F1": ("R7", "--k1-forced-block"), "F2": ("R8", "--k1-forced-block")}
"""Rules K-5: (base row, the only argv option that differs besides ``--case``)."""
SOURCE_ROWS = {
    ("J2", "top", 1.0): "P3b_J2_B_top_Fs4", ("J2", "middle", 1.0): "P3b_J2_B_middle_Fs4",
    ("J2", "bottom", 1.0): "P3b_J2_B_bottom_Fs4", ("J2", "top", 1.1): "P3b_J2_B_top_Fs4_m1p1",
    ("J1", "top", 1.1): "P3b_J1_B_top_Fs4_m1p1",
}
"""Record only (rules 1.1 / adopt 3.2): case names of the stored old-controller rows of the same condition."""


def _r9() -> ModuleType:
    sys.path.insert(0, str(HERE))
    try:
        import run_S9 as r9  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    return r9


def case_name(soil: str, level: str, mass_scale: float, setting: str, gate: str, forced: str) -> str:
    """Rules 2.2 / 2.3 case names, e.g. ``REM_J2_B_top_Fs4_m1p1_VB_gateon_forced1``."""
    m = "" if mass_scale == 1.0 else "_m" + f"{mass_scale:g}".replace(".", "p")
    f = "_forced1" if forced == "first" else ""
    return f"REM_{soil}_{REM_PAD}_{level}_Fs{REM_FS_KN:g}{m}_{setting}_gate{gate}{f}"


def base_case(r9: ModuleType, soil: str, level: str, mass_scale: float, setting: str) -> dict[str, Any]:
    """The run_S9 P3b case dict of a row (pad B, F_s 4 kN, P3b grid / 120 s) + mass scale + controller tag."""
    c = r9.p3b_case(REM_BATCH, soil, REM_PAD, level, REM_FS_KN)
    if mass_scale != 1.0:
        c["mass_scale"] = mass_scale
    c["controller"] = CONTROLLER_OF_SETTING[setting]
    return c


def level_argv(r9: ModuleType, sb: ModuleType, soil: str, level: str, mass_scale: float, setting: str, gate: str,
               forced: str) -> list[str]:
    """``run_S9.py level`` argv of a row (rules 2.1 row form)."""
    out = r9.p3b_level_argv(base_case(r9, soil, level, mass_scale, setting))
    if setting == "VB":
        out += sb.v5_vb_argv()
    elif setting != "V0":
        raise ValueError(f"{REM_BATCH}: v5 setting {setting!r} not VB / V0")
    out += [r9.K1_ORDER_GATE_OPTION, gate]
    if forced != "off":
        out += [r9.K1_FORCED_BLOCK_OPTION, forced]
    return out


def rem_rows(sb: ModuleType) -> list[dict[str, Any]]:
    """The 10 rows of rules 2.2 / 2.3 in table order."""
    r9 = _r9()
    names = {k: case_name(s, lv, m, st, g, f) for k, s, lv, m, st, g, f, _ in REM_ROWS}
    rows = []
    for key, soil, level, m, setting, gate, forced, role in REM_ROWS:
        pair_set = next((ps for ps in PAIR_SETS if key in ps), None)
        base = ARGV_BASE.get(key)
        rows.append({
            "case": names[key], "est_s": REM_EST_S[m],
            "argv": list(sb.RUN) + level_argv(r9, sb, soil, level, m, setting, gate, forced),
            "controller": CONTROLLER_OF_SETTING[setting], "group": REM_BATCH, "criteria_id": f"LAS-K1-REM-{key}",
            "rem_key": key, "role": role, "v5_setting": setting, "planned_pool": PLANNED_POOL,
            "start_env": dict(START_ENV), "las_candidate": REM_LAS_CANDIDATE,
            "k1_candidate": "K1on" if gate == "on" else "K1off", "k1_order_gate": gate, "k1_forced_block": forced,
            "soil": soil, "level": level, "rem_mass_scale": m,
            "pair_case": names[PAIR_CASE[key]] if key in PAIR_CASE else None,
            "pair_set": [names[k] for k in pair_set] if pair_set else None,
            "argv_base_case": names[base[0]] if base else None, "argv_diff_option": base[1] if base else None,
            "source_rows": SOURCE_ROWS[(soil, level, m)], "rules": REM_SOURCE,
            "note": (f"{REM_BATCH} {key} ({role}): {soil} B {level} x{m:g}, F_s {REM_FS_KN:g} kN, flat uniform, "
                     f"120 s, {setting} {CONTROLLER_OF_SETTING[setting]}, --k1-order-gate {gate}"
                     + (f", --k1-forced-block {forced}" if forced != "off" else "")
                     + f"; old-controller row {SOURCE_ROWS[(soil, level, m)]} (record)")})
    return rows


def rem_batches(sb: ModuleType) -> dict[str, list[dict[str, Any]]]:
    rows = rem_rows(sb)
    names = [r["case"] for r in rows]
    if len(set(names)) != len(names):
        raise RuntimeError(f"{REM_BATCH}: duplicate row names")
    return {REM_BATCH: rows}


def run_level_config(r9: ModuleType, a: argparse.Namespace) -> Any:
    """The C2 config ``run_S9.run_level`` checks with ``--expect-controller`` (same steps and order as
    ``las_k1_chrono_rows.run_level_config``); no Chrono object is made."""
    sys.path.insert(0, str(HERE))
    try:
        import las_k1_chrono_rows as k1c  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    return k1c.run_level_config(r9, a)


def _scalar(v: Any) -> Any:
    return v[0] if isinstance(v, (list, tuple)) and len(v) == 1 else v


def argv_check(row: dict[str, Any], sb: ModuleType) -> dict[str, Any]:
    """Build check without Chrono (rules 9.3): the level argv parses with the run_S9 parser; the fixed values (threads,
    soil, no patch, pad, level, F_s, duration, grades, seed, mass scale, gate, forced block, expect tag) are the row's;
    VB rows carry exactly the VB arguments and V0 rows none (no v5 option, no flow limit); the run-time config passes
    ``--expect-controller`` of the row (R5: ``final_C4G2_LAS``) and holds the gate; the controller class resolves
    (``run_S9.level_controller_class``: C2Controller, or K1ForcedBlockC2Controller on F1 / F2)."""
    out: dict[str, Any] = {"case": row["case"], "source": None, "rem_key": row["rem_key"],
                           "k1_candidate": row["k1_candidate"]}
    r9 = _r9()
    argv = row["argv"]
    level = argv[argv.index("level"):]
    diffs: list[dict[str, Any]] = []
    try:
        a = r9.build_parser().parse_args(level)
    except SystemExit as e:
        return {**out, "status": "differs", "diffs": [{"key": "argparse", "former": "ok", "row": str(e)}]}
    want = {"threads": r9.SCM_THREADS_FIXED, "soil": row["soil"], "soil_patch": None,
            "grid": r9.P3B_PAD_GRID_M[row["soil"]], "crawler_grid": r9.P3B_CRAWLER_GRID_M,
            "pad_variant": r9.P3B_PAD[REM_PAD], "level": row["level"], "fs_kN": REM_FS_KN,
            "duration": r9.P3B_DURATION_S, "pressure_grade": "normal", "imu_grade": "ideal", "seed": REM_SEED,
            "mass_scale": row["rem_mass_scale"],
            "floor_roll": 0.0, "floor_pitch": 0.0,
            "k1_order_gate": row["k1_order_gate"],
            "k1_forced_block": row["k1_forced_block"],  # judge rows: the parser default off (rules 9.3, K-5)
            "expect_controller": row["controller"]}
    for k, v in want.items():
        got = _scalar(getattr(a, k, None))
        if got != v and not (v is not None and got is not None and str(got) == str(v)):
            diffs.append({"key": k, "former": v, "row": got})
    if row["v5_setting"] == "VB":
        for k, v in sb.V5_VB_ARGS.items():
            got = _scalar(getattr(a, k, None))
            if got != v:
                diffs.append({"key": k, "former": v, "row": got})
    else:  # V0: no v5 / flow option at all (rules 2.2: v5_rigid_setting_args("V0") = {})
        present = [k for k in sb.V5_VB_ARGS if getattr(a, k, None) not in (None, False)]
        if present:
            diffs.append({"key": "v5_args", "former": [], "row": present})
    from outrigger_sim.hydraulics.flow_limit_run import flow_setting_from_args  # noqa: PLC0415

    if (flow_setting_from_args(a) is None) is (row["v5_setting"] == "VB"):
        diffs.append({"key": "flow_limit", "former": row["v5_setting"] == "VB",
                      "row": flow_setting_from_args(a) is not None})
    try:
        config = run_level_config(r9, a)
    except SystemExit as e:
        return {**out, "status": "differs", "diffs": diffs + [{"key": "level_config", "former": "ok",
                                                               "row": f"SystemExit({e.code})"}]}
    has_v5 = r9.v5_hydraulic_options(a, r9.load_inputs(a)[0]) is not None
    out["v5_options"] = has_v5
    if has_v5 is not (row["v5_setting"] == "VB"):
        diffs.append({"key": "v5_options", "former": row["v5_setting"] == "VB", "row": has_v5})
    chk = r9.controller_expectation(config, row["controller"])
    out["expect_controller"] = {"name": chk["name"], "ok": chk["ok"]}
    if not chk["ok"]:
        diffs.append({"key": "controller_expectation", "former": row["controller"],
                      "row": [c for c in chk["checks"] if not c["ok"]]})
    gate = config.slope_clearance_margin.flat_soil_margin_order_gate
    if gate is not (row["k1_order_gate"] == "on"):
        diffs.append({"key": "flat_soil_margin_order_gate", "former": row["k1_order_gate"] == "on", "row": gate})
    try:
        cls, meta = r9.level_controller_class(a)
    except SystemExit as e:
        diffs.append({"key": "controller_class", "former": row["k1_forced_block"], "row": f"SystemExit({e.code})"})
        cls, meta = None, None
    if cls is not None:
        want_cls = r9.K1_FORCED_BLOCK_CLASS if row["k1_forced_block"] == "first" else "C2Controller"
        if cls.__name__ != want_cls or (meta or {}).get("requested") != row["k1_forced_block"]:
            diffs.append({"key": "controller_class", "former": want_cls, "row": [cls.__name__, meta]})
        out["k1_forced_block"] = meta
    return {**out, "status": "differs" if diffs else "ok", "diffs": diffs, "order_gate": gate}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=f"{REM_BATCH} build checks (no simulation)")
    ap.add_argument("--out", default=None, help="JSON result file")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(HERE))
    try:
        import s9_batch as sb  # noqa: PLC0415
    finally:
        sys.path.remove(str(HERE))
    rows = sb.batches()[REM_BATCH]
    doc: dict[str, Any] = {"checks": [argv_check(r, sb) for r in rows]}
    doc["ok"] = not any(c["status"] == "differs" for c in doc["checks"])
    text = json.dumps(doc, indent=1, default=str)
    if a.out:
        Path(a.out).write_text(text, "utf-8")
    print(text)
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
