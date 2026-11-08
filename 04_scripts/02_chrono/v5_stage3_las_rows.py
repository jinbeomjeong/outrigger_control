"""V5-STAGE3-LAS: the v5 stage 3 Chrono rows re-run with the LAS-b tags (definitions only; cad 2026-11-08).

Basis: ``06_analysis/03_hydraulic/coupled/v5/v5_criteria_rev12.md`` 2.1 (sealed 2026-11-08; user decision Q2: every stored
stage 3 Chrono row - VB, LS, soil VB and their V0 pairs - is re-run on the LAS-b tags). 34 stage 3 rows
(``s9_batch.v5_stage3_rows``) + 3 pair rows outside stage 3 = 37 rows (else RuntimeError):

* P-1 ``E_G4_Fs4_V0``: the V0 pair of ``E_G4_Fs4`` (stored ``batch_FINAL-R-C4G2_20261105/final_E_G4_Fs4``): the stage 3
  rigid row form with setting V0 (``run_S8C run --set <family> --only E_G4_Fs4 ... --workers p7``, no v5 argument). The
  stored FINAL-R-C4G2 folder keeps no argv; the V0 form is the one the stage 3 V0 rows (``E_G4_Fs4_ph0.05_V0``) ran.
* P-2 ``S6P_P3b_J2_B_top_Fs4_m1p1_t180_flowoff`` / P-3 ``..._flowon``: the S6 argv of ``s9_batch.v5_s6_seed_rows`` before
  the seed change (stored seed 20261026): FINAL-REP-X (flow off) / COUPLED_eta085 (flow on). NOTE: with the stored seed
  these argv equal the S6SEED rows ``..._seed20261026`` / ``..._seed20261026_flow`` (only the case name differs), so
  P-2 / P-3 repeat those two runs (reported to the main session 2026-11-08).

Rules (main session C-1 .. C-5): plant / case / event / seed / ``--threads`` as the stored row; VB and LS = the current
``v5_vb_argv()`` / ``v5_rigid_argv()`` (the stored stage 3 VB / LS argv had no ``--extend-start-tracked``: the ③ start
bound of criteria rev. 8 is the only accepted argument difference, :data:`ACCEPTED_NEW_ARGS`); run_S9 rows get
``--expect-controller`` = ``V5_P3_LAS_CONTROLLER`` (VB / LS) or ``V5_LAS_CONTROLLER`` (V0, V0v, S6SEED, P-2, P-3);
run_S8C rows only the row field ``controller`` (the run uses the switched preset). Row fields: ``stored_result``,
``pair_case`` (inside this batch), ``hash_comparable`` (stored pool P and same ``--threads``), ``est_pool_s`` (stored
wall; an E-pool stored wall / 1.5 for P, ASSUMPTION), ``stored_argv_check`` (:func:`stored_argv_check`).
The former ``V5-STAGE3`` definition and its stored folders are not touched.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

LAS_STAGE3_BATCH = "V5-STAGE3-LAS"
STORED_SOIL = "07_results/S9/batch_V5-STAGE3_20261107_184239"
STORED_RIGID = "07_results/S9/batch_V5-STAGE3_20261107_184341"
STORED_P1 = "07_results/S9/batch_FINAL-R-C4G2_20261105"
STORED_P2 = "07_results/S9/batch_FINAL-REP-X_20261031_020716"
STORED_P3 = "07_results/S9/batch_COUPLED_eta085_20261104_142213"
S6_CASE = "P3b_J2_B_top_Fs4_m1p1_t180"
P1_NAME, P2_NAME, P3_NAME = "E_G4_Fs4_V0", f"S6P_{S6_CASE}_flowoff", f"S6P_{S6_CASE}_flowon"
E_TO_P = 1.5
"""ASSUMPTION (main session C-3): P wall = stored E wall / 1.5."""
VB_LS = ("VB", "LS1", "LS4")
ACCEPTED_NEW_ARGS = ("--extend-start-tracked",)
"""Arguments a VB / LS re-run row may add to the stored argv (③ start bound, criteria rev. 8 3.1)."""
EXPECTED_ROWS = 37


def results_root() -> Path:
    """Folder holding ``07_results`` (the worktree has none: then the main checkout two levels above)."""
    if (ROOT / "07_results").is_dir():
        return ROOT
    for p in ROOT.parents:
        if (p / "07_results").is_dir():
            return p
    return ROOT


def _batch_cases(rel: str) -> dict[str, dict]:
    p = results_root() / rel / "batch.json"
    if not p.is_file():
        return {}
    return {c["case"]: c for c in json.loads(p.read_text("utf-8")).get("cases", [])}


def _tail(argv: list[str]) -> list[str]:
    """argv after the script (``run_S9.py`` / ``run_S8C.py``), the interpreter and paths removed."""
    for k, t in enumerate(argv):
        if t.endswith(("run_S9.py", "run_S8C.py")):
            return list(argv[k + 1:])
    return list(argv)


def _without(argv: list[str], key: str) -> list[str]:
    out = list(argv)
    if key in out:
        k = out.index(key)
        del out[k:k + 2]
    return out


def stored_argv_check(row: dict, stored_argv: list[str] | None) -> dict[str, Any]:
    """Row argv vs the stored argv: equal after dropping ``--expect-controller`` (both), ``--case`` / ``--tag`` values
    are compared as they are (run_S8C ``--tag`` is the stored one), and the VB / LS accepted additions
    (:data:`ACCEPTED_NEW_ARGS`). ``status`` ok / differs / no_stored_argv."""
    if not stored_argv:
        return {"status": "no_stored_argv"}
    a = _without(_tail(row["argv"]), "--expect-controller")
    b = _without(_tail(stored_argv), "--expect-controller")
    added = [t for t in ACCEPTED_NEW_ARGS if t in a and t not in b] if row.get("v5_setting") in VB_LS else []
    a = [t for t in a if t not in added]
    if a == b:
        return {"status": "ok", "accepted_added": added}
    i = next((k for k, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return {"status": "differs", "accepted_added": added, "first_diff_index": i,
            "row": a[max(0, i - 2):i + 3], "stored": b[max(0, i - 2):i + 3]}


def _threads(argv: list[str] | None) -> str | None:
    if not argv or "--threads" not in argv:
        return None
    return argv[argv.index("--threads") + 1]


def _las_controller(sb: ModuleType, setting: str) -> str:
    return sb.V5_P3_LAS_CONTROLLER if setting in VB_LS else sb.V5_LAS_CONTROLLER


def _retag(sb: ModuleType, row: dict) -> dict:
    ctrl = _las_controller(sb, row.get("v5_setting") or "")
    out = dict(row)
    if not row.get("s8c"):
        out["argv"] = sb.with_expected_controller(row["argv"], ctrl)
    out["controller"] = ctrl
    out["stage3_controller"] = row.get("controller")
    return out


def _est(stored: dict | None) -> tuple[dict[str, float] | None, float | None, str | None]:
    if not stored or stored.get("wall_s") is None:
        return None, None, None
    w, pool = float(stored["wall_s"]), stored.get("pool")
    p = w / E_TO_P if pool == "ecore" else w
    e = w if pool == "ecore" else w * E_TO_P
    return {"pcore": round(p, -1), "ecore": round(e, -1)}, w, pool


def _stored_result(stored: dict | None, rel: str, case: str, s8c_id: str | None) -> str | None:
    if not stored:
        return None
    chk = stored.get("s8c_check") or {}
    if chk.get("batch_dir"):
        base = Path(chk["batch_dir"])
        try:
            base = base.relative_to(results_root())
        except ValueError:
            pass
        return (base / (s8c_id or case)).as_posix()
    return f"{rel}/{case}"


def _pair(case: str, setting: str) -> str | None:
    if setting == "V0v":
        return case[:-len("_v0v")]
    if case.endswith("_V0") and setting == "V0":
        return case[:-len("_V0")]
    for ls in ("_LS1", "_LS4"):
        if case.endswith(ls):
            return case[:-len(ls)]
    if setting == "S6SEED":
        return P3_NAME if case.endswith("_flow") else P2_NAME
    return None


def las_stage3_rows(sb: ModuleType, out: dict[str, list[dict]]) -> list[dict]:
    stage3 = out[sb.V5_STAGE3_BATCH]
    soil, rigid = _batch_cases(STORED_SOIL), _batch_cases(STORED_RIGID)
    names = {r["case"] for r in stage3}
    rows: list[dict] = []
    for r in stage3:
        setting = r.get("v5_setting") or ""
        rel = STORED_RIGID if r.get("s8c") else STORED_SOIL
        stored = (rigid if r.get("s8c") else soil).get(r["case"])
        row = _retag(sb, r)
        pair = _pair(r["case"], setting)
        if setting == "VB":
            pair = {"E_G4_Fs4": P1_NAME}.get(r["case"]) or (f"{r['case']}_V0" if f"{r['case']}_V0" in names
                                                            else f"{r['case']}_v0v" if f"{r['case']}_v0v" in names
                                                            else None)
        rows.append(_finish(row, stored, rel, pair))
    # P-1: V0 pair of E_G4_Fs4 (stage 3 rigid V0 form)
    vb = next(r for r in stage3 if r["case"] == "E_G4_Fs4")
    p1 = sb.v5_rigid_row("E_G4_Fs4", vb["family"], "V0", criteria_id="R12#19-pair", group=LAS_STAGE3_BATCH,
                         v0_wall_s=0.0, source_run=f"{STORED_P1}/final_E_G4_Fs4/E_G4_Fs4", pair_case="E_G4_Fs4",
                         name=P1_NAME, note="V5-STAGE3-LAS P-1: E_G4_Fs4 V0 pair (stored FINAL-R-C4G2)")
    p1_stored = _batch_cases(STORED_P1).get("E_G4_Fs4")
    rows.append(_finish(_retag(sb, p1), p1_stored, STORED_P1, "E_G4_Fs4",
                        stored_result=f"{STORED_P1}/final_E_G4_Fs4/E_G4_Fs4"))
    # P-2 / P-3: the S6 argv before the seed change (stored seed)
    base_off = next(r for r in out["FINAL-REP-X"] if r["case"] == S6_CASE)
    base_on = next(r for r in out[sb.COUPLED_BATCH] if r["case"] == S6_CASE and r.get("criteria_id") == "S6")
    for name, base, rel, flow in ((P2_NAME, base_off, STORED_P2, False), (P3_NAME, base_on, STORED_P3, True)):
        row = {**base, "case": name, "v5_setting": "S6SEED_pair", "group": LAS_STAGE3_BATCH,
               "criteria_id": "S6-pair", "source_run": f"{Path(rel).name}/{S6_CASE}",
               "note": f"V5-STAGE3-LAS P-{3 if flow else 2}: S6 stored seed, flow {'on' if flow else 'off'} "
                       f"(seed-row pair; argv = the S6SEED ..._seed20261026{'_flow' if flow else ''} row)"}
        row.pop("source_expected_diffs", None)
        stored = _batch_cases(rel).get(S6_CASE)
        rows.append(_finish(_retag(sb, row), stored, rel, None, stored_result=f"{rel}/{S6_CASE}"))
    for r in rows:
        r["group"] = r["rep_bundle"] = LAS_STAGE3_BATCH
    names_all = [r["case"] for r in rows]
    dup = sorted({n for n in names_all if names_all.count(n) > 1})
    if dup or len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"{LAS_STAGE3_BATCH}: {len(rows)} rows ({EXPECTED_ROWS} expected), duplicate names {dup}")
    return rows


def _finish(row: dict, stored: dict | None, rel: str, pair: str | None, *, stored_result: str | None = None) -> dict:
    est, wall, pool = _est(stored)
    stored_argv = (stored or {}).get("argv")
    out = {**row, "pair_case": pair,
           "stored_result": stored_result or _stored_result(stored, rel, row["case"], row.get("s8c_case_id")),
           "stored_wall_s": wall, "stored_pool": pool,
           "hash_comparable": bool(pool == "pcore" and _threads(stored_argv) == _threads(row["argv"])),
           "stored_argv_check": stored_argv_check(row, stored_argv)}
    if est is not None:
        out["est_pool_s"], out["est_s"], out["planned_pool"] = est, est["pcore"], "pcore"
    return out


def las_stage3_batches(sb: ModuleType, out: dict[str, list[dict]]) -> dict[str, list[dict]]:
    return {LAS_STAGE3_BATCH: las_stage3_rows(sb, out)}
