"""436.8 v5 resume: the Chrono rows (definitions, build checks, O-C5 R_c probe procedure; cad 2026-11-13).

Rules: ``06_analysis/02_control/verif_matrix/v5_resume_4368_rules.md`` (sealed, sha256 :data:`RULES_SHA256`), the
cad-expert share of 16: C-1 .. C-5 tags, C-4 off arm and its ``option_diff`` to P5r4 A1 / A3, C-6 / C-7, C-8a / C-8b,
the R_c probe runner / reader (5.4-1 .. 5.4-8), ``PROBE_DURATION``, the A-7 snapshot rows, per-row estimates, G-S.

Batches of ``s9_batch`` (``list`` / ``check-sources`` / ``run``; output ``07_results/S9/batch_<name>_<stamp>``, rules
4.3):

* ``V5-RESUME-K1-C1`` (10): D-1 fixed rigid rows of ``D1-CHRONO`` (L2b VB C2-01/02/04/05/06/08, L1-R V0 Kc x3
  C1-09 .. 12), tags only (rules 5.2 C-1).
* ``V5-RESUME-K1-C2`` (17 candidates): C2-03 / C2-07 roll-sign pairs (L2b, 4), S-01 / S-02 slope candidates (SCM,
  6) and the ``D1-PSC`` rows (7); the H-2 output (``resume_k1/h2_d1_select.json``) picks the launched rows
  (``c2-select`` -> ``--only-file``).
* ``V5-RESUME-K1-C3`` (2): S-03 / S-04 ``D1S_G1_B_{middle,bottom}_Fs4_spJ1FL``.
* ``V5-RESUME-K1-C4`` (4): ``V5-LAS-CHRONO`` form (mixed ground rigid + J1@FR, floor (2.3351, 1.5017) deg,
  ``record_only``, 160 s, VB) x Kc1 / Kc3 x LAS on (the preset, tag ``final_C4G2_P3_LAS_K1``) / off
  (``--las-off --k1-order-gate on``, tag ``final_C4G2_P3_K1``; no ``pre_las_preset_runner``).
* ``V5-RESUME-K1-C5`` (35): ``V5-STAGE3-LAS`` without P-2 / P-3 (rules 5.2 C-5), tags of rules 4.1.
* ``V5-RESUME-K1-C6C7`` (3): G1 open loop ``P3a_G1_B_VB_prop`` / ``P3a_G1_B_VB_FB`` / ``P3a_G1_B_V0_FB`` (5.3).
* ``V5-RESUME-K1-OC5PROBE``: the next R_c probe of each O-C5 row still probing (from the probe state file).
* ``V5-RESUME-K1-OC5``: the O-C5 main rows whose k is decided (5.4, names fixed by the rules).
* ``V5-RESUME-K1-JP`` (6 + 6): J_P re-run rows (only when the 7.3 reuse conditions fail).
* ``V5-RESUME-K1-GS``: the Chrono G-S dry run (11.2, ``--duration`` :data:`GS_DURATION_S`; never judged).

Retag rule (rules 4.1): the ③ decision is ``v5_options.is_extend_start_tag(<former row tag>)`` only; ③ rows get
``final_C4G2_P3_LAS_K1``, all others ``final_C4G2_LAS_K1``. run_S9 rows carry it in ``--expect-controller``; run_S8C
/ run_S6C rows cannot take ``--expect-controller`` outside the D8x / K-2 sets, so they carry the row field
``controller`` and :func:`argv_check` builds their controller config without Chrono (run_S8C ``d8x_preflight`` path /
``run_S6C.controller_config``) and checks its tag (``v5_options.with_switch_tags``).

Run identity (rules 6): SCM rows ``--threads 4`` (``run_S9.SCM_THREADS_FIXED``), row key ``start_env``
``{"OMP_WAIT_POLICY": "PASSIVE"}`` (no ``OUTRIGGER_HULL_HOOK``: unset = fast, 4.2), ``planned_pool`` ``pcore``
(G-S rows ``ecore``). Every row has ``r4368`` (criteria id, role, engine, A-7 snapshot, estimate range), copied to
batch.json.

CLI (Chrono-dev, project root, no simulation)::

    python -I -X utf8 04_scripts/02_chrono/v5_resume_4368_chrono_rows.py check [--out f.json]   # build checks
    python -I -X utf8 04_scripts/02_chrono/v5_resume_4368_chrono_rows.py manifest --out m.json    # rows, argv sha
    python -I -X utf8 04_scripts/02_chrono/v5_resume_4368_chrono_rows.py c2-select <h2.json> --out only.json
    python -I -X utf8 04_scripts/02_chrono/v5_resume_4368_chrono_rows.py oc5-status
    python -I -X utf8 04_scripts/02_chrono/v5_resume_4368_chrono_rows.py oc5-read <probe or OC5 batch folder>
    python -I -X utf8 04_scripts/02_chrono/v5_resume_4368_chrono_rows.py gs-check <G-S batch folder>

Every command ends with a plain ``errors N`` line (``tools/verif/log_errors.py``); exit 0 ok, 1 a check failed or a
stop, 2 an input is missing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

RULES = "06_analysis/02_control/verif_matrix/v5_resume_4368_rules.md"
RULES_SHA256 = "9019b405b7a196f28a756e7ca91f443f6241a58bd8e1eee0361483066cb19524"
SOURCE = f"{RULES} (sha256 {RULES_SHA256[:8]}) 5.2 / 5.3 / 5.4 / 6 / 11.2 / 16; cad 2026-11-13"
PREFIX = "V5-RESUME-K1-"
B_C1, B_C2, B_C3, B_C4, B_C5, B_C6C7 = (PREFIX + s for s in ("C1", "C2", "C3", "C4", "C5", "C6C7"))
B_PROBE, B_OC5, B_JP, B_GS = (PREFIX + s for s in ("OC5PROBE", "OC5", "JP", "GS"))
BATCHES = (B_C1, B_C2, B_C3, B_C4, B_C5, B_C6C7, B_PROBE, B_OC5, B_JP, B_GS)
VB_TAG, V0_TAG = "final_C4G2_P3_LAS_K1", "final_C4G2_LAS_K1"
OFF_VB_TAG = "final_C4G2_P3_K1"
"""Rules 4.1: VB / LS (③ on) and the other settings; C-4 off arm (VB) = ``--las-off --k1-order-gate on``."""
OFF_ARM_ARGS = ("--las-off", "--k1-order-gate", "on")
RUNNER_EXPECT_OPTION: dict[str, str | None] = {"L2b_NSC": "--expect-controller", "L1R": "--expect-controller"}
"""User decision Q-2 (2026-11-13): run_S8C / run_S6C get a controller-tag check option from python-expert. When its
name is set here (main session, after that change), :func:`finish` appends ``[<option>, <tag>]`` to every L2b / L1-R
row and :func:`argv_check` requires it; None = not yet available (the row carries the tag in ``controller`` only).
Set 2026-11-13 to ``--expect-controller`` (python-expert c17481d on its own branch: run_S8C ``run|check`` and run_S6C
``run`` refuse another tag before the closed loop, result.json ``controller_tag`` / ``expect_controller``). This
branch's runners do not have it yet: launch only after that change is merged."""
START_ENV_SCM = {"OMP_WAIT_POLICY": "PASSIVE"}
"""Rules 6 start env of the SCM rows (no ``OUTRIGGER_HULL_HOOK``: rules 4.2, unset = fast)."""
FORBIDDEN_TOKENS = ("--k1-order-gate", "--las-off", "--las-candidate", "--k1-forced-block", "--k2",
                    "--no-controller-check", "--allow-other-threads", "--allow-mixed-hull")
"""Rules 4.2 (all Chrono rows except the C-4 off arm, which may carry ``--las-off`` / ``--k1-order-gate on``)."""
FORBIDDEN_ENV = ("OUTRIGGER_HULL_HOOK", "OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED", "OUTRIGGER_LOC_SHADOW")
PRE_RUNNER_RE = re.compile(r"pre_[a-z0-9]+_preset_runner\.py$")

C1_IDS = ("C2-01", "C2-02", "C2-04", "C2-05", "C2-06", "C2-08", "C1-09", "C1-10", "C1-11", "C1-12")
C2_IDS = ("C2-03", "C2-07", "S-01", "S-02")
C3_IDS = ("S-03", "S-04")
C3_NAMES = ("D1S_G1_B_middle_Fs4_spJ1FL", "D1S_G1_B_bottom_Fs4_spJ1FL")
C5_DROP = ("S6P_P3b_J2_B_top_Fs4_m1p1_t180_flowoff", "S6P_P3b_J2_B_top_Fs4_m1p1_t180_flowon")
"""Rules 5.2 C-5: P-2 / P-3 equal the S6SEED ``..._seed20261026`` / ``..._seed20261026_flow`` rows (not run)."""
C5_EXPECTED = 35
C2_COUNT_RANGE = (4, 10)

P5K_STORED = "07_results/S9/batch_V5-LAS-P5R4-K1_20261111_232832"
"""P5r4 r2 batch (``las_p5r4_k1_judgement.md`` 1.1 / line 68): A1 / A3 / A5 argv and ``phases`` (times only)."""
P5K_A_CASES = {"A1": "P5K_A1_rigidJ1FR_Kc1_B_top_Fs4_VB_P0", "A3": "P5K_A3_rigidJ1FR_Kc3_B_top_Fs4_VB_P0",
               "A5": "P5K_A5_rigidJ1FR_Kc1_B_top_Fs4_V0_P0"}
OPENLOOP_VB_STORED = "batch_V5-OPENLOOP-VB_20261108_112044/P3a_G1_B_VB"
OPENLOOP_V0_STORED = "batch_V5-OPENLOOP-V0_20261108_123517/P3a_G1_B_V0"

# --- O-C5 (rules 5.4) -------------------------------------------------------------------------------------------
FLOOR_REF_DEG = (2.3351, 1.5017)
OC5_TARGET, OC5_TOL, OC5_MAX_PROBES = 0.95, 0.02, 3
CMP_EPS = 1e-9
"""Rules 7.6 comparison allowance (``|v - c| <= e`` true when ``|v - c| <= e + 1e-9``)."""
K_DECIMALS = 4
"""Rules 5.4-8: k written to 4 decimals; ASSUMPTION (확인 필요 Q-k): the rounded k is the k used (floors from it)."""
OC5_ROWS: dict[str, dict[str, Any]] = {
    "C-8a": {"name": "OC5_mixed_rigid_J1FR_Kc3_VB_top", "base": "A3", "crawler": "Kc3", "setting": "VB",
             "R_c_known": 1.035},
    "C-8b": {"name": "OC5_mixed_rigid_J1FR_Kc1_V0_top", "base": "A5", "crawler": "Kc1", "setting": "V0",
             "R_c_known": 1.076},
}
PROBE_CHECK_END_S = {"A3": 4.8, "A5": 4.8}
"""CHECK end of the stored A3 / A5 runs (closed-loop time, ``phases``: ``touch`` starts at 12.8 s absolute, loop start
8.0 s; read 2026-11-13 from :data:`P5K_STORED`, times only, ``read_phases``)."""
PROBE_DURATION_S = {k: float(math.ceil(v + 2.0 - CMP_EPS)) for k, v in PROBE_CHECK_END_S.items()}
"""Rules 5.4-1: CHECK end + 2 s, rounded up to an integer second (A3 / A5: 7 s)."""
OC5_STATE_DEFAULT = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "v5_resume_4368" / "oc5_state.json"
OC5_STATE_ENV = "R4368_OC5_STATE"
PROBE_READ_KEYS = ("p3b_ext.start_condition.crawler_attitude_deg", "p3b_ext.start_condition.R_c_operating",
                   "args.floor_roll", "args.floor_pitch", "args.duration", "phases")
"""Rules 5.4-2: the only result.json keys the probe reader reads."""

# --- G-S (rules 11.2) -------------------------------------------------------------------------------------------
GS_DURATION_S = 10.0
GS_OPENLOOP_LIFT_S = 10.0
"""ASSUMPTION (확인 필요 Q-gs-ol): the open-loop ``machine`` action has no ``--duration``; a G-S row would shorten
``--lift-s`` instead (not run)."""

# --- estimates (rules 12.1, ASSUMPTION / measured; [lo, hi] s per row on P, 4 parallel) ----------------------------
EST_RANGE_S = {"scm": (6649.0, 8898.0), "scm_c3": (6649.0, 12600.0), "mixed": (3885.0, 4413.0),
               "l2b": (862.0, 1869.0), "l1r": (600.0, 600.0), "probe": (900.0, 1800.0),
               "C-6": (1581.0, 1581.0), "C-7a": (1754.0, 1754.0), "C-7b": (1748.0, 1748.0),
               "gs": (450.0, 900.0)}
"""Rules 12.1 units (G-S: P5K G-S A4 alone on E 644 s, 2026-11-11; 2 rows in parallel on E, ASSUMPTION)."""


# =============================================================================================== helpers
def _import(name: str) -> ModuleType:
    sys.path.insert(0, str(HERE))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(HERE))


def _src_path() -> None:
    src = str(ROOT / "03_src")
    if src not in sys.path:
        sys.path.insert(0, src)


def results_root() -> Path:
    """Folder holding the stored results (``07_results/S9`` with :data:`P5K_STORED`): this checkout, else the main
    checkout above a worktree (a worktree may have its own partial ``07_results``, e.g. G-S output)."""
    for p in (ROOT, *ROOT.parents):
        if (p / P5K_STORED).is_dir():
            return p
    return _import("v5_stage3_las_rows").results_root()


def _v5opt() -> ModuleType:
    _src_path()
    from outrigger_sim.hydraulics import v5_options  # noqa: PLC0415

    return v5_options


def k1_tag_of(former: str | None) -> str:
    """Rules 4.1: ``final_C4G2_P3_LAS_K1`` when ``is_extend_start_tag(former)``, else ``final_C4G2_LAS_K1``."""
    return VB_TAG if _v5opt().is_extend_start_tag(former) else V0_TAG


def script_tail(argv: list[str]) -> list[str]:
    """Tokens after the runner script (interpreter, flags and the checkout path removed)."""
    for k, t in enumerate(argv):
        if t.endswith((".py",)) and Path(t).name in ("run_S9.py", "run_S8C.py", "run_S6C.py"):
            return list(argv[k + 1:])
    return list(argv)


def argv_sha256(argv: list[str]) -> str:
    """SHA-256 of the runner name + the tokens after it, NUL-joined (checkout-independent)."""
    runner = next((Path(t).name for t in argv if Path(t).name in ("run_S9.py", "run_S8C.py", "run_S6C.py")), "?")
    return hashlib.sha256("\x00".join([runner, *script_tail(argv)]).encode("utf-8")).hexdigest()


def option_diff(a: list[str], b: list[str]) -> list[str]:
    """Options whose values differ or that one argv lacks (tokens after the runner script)."""
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

    oa, ob = opts(script_tail(a)), opts(script_tail(b))
    return sorted(k for k in set(oa) | set(ob) if oa.get(k) != ob.get(k))


def _engine(row: dict[str, Any]) -> str:
    if row.get("s8c"):
        return "L2b_NSC"
    if row.get("s6c"):
        return "L1R"
    return "SCM"


def _set_value(argv: list[str], opt: str, value: str) -> list[str]:
    out = list(argv)
    out[out.index(opt) + 1] = value
    return out


def _drop_option(argv: list[str], opt: str, n_values: int = 1) -> list[str]:
    out = list(argv)
    if opt in out:
        k = out.index(opt)
        del out[k:k + 1 + n_values]
    return out


DROP_KEYS = ("las_family", "las_ready", "las", "las_crawler", "p5k_id", "p5k_stage", "p5k_gs", "p5k_family",
             "p5k_crawler", "p5k_mass_scale", "p5k_duration_s", "p5k_judge_duration_s", "p5k_rules", "las_candidate",
             "rem_key", "k1_candidate", "k2_arm", "source_expected_diffs", "rep_variable", "r4_x11_check")
"""Keys of the source definitions that would route ``s9_batch`` checks / launches to their own batch logic."""


def finish(row: dict[str, Any], *, batch: str, criteria_id: str, role: str, tag: str | None, est_kind: str,
           note: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """The 436.8 form of a row: tag (``--expect-controller`` on run_S9 level rows, field ``controller``), group,
    ``planned_pool`` P, SCM ``start_env``, estimate range (rules 12.1) and the ``r4368`` record."""
    out = {k: v for k, v in row.items() if k not in DROP_KEYS}
    engine = _engine(out)
    former = row.get("controller")
    if tag is not None:
        if engine == "SCM" and "level" in out["argv"]:
            if "--expect-controller" not in out["argv"]:
                raise RuntimeError(f"{out['case']}: run_S9 level row without --expect-controller")
            out["argv"] = _set_value(out["argv"], "--expect-controller", tag)
        opt = RUNNER_EXPECT_OPTION.get(engine)
        if opt is not None:
            out["argv"] = (_set_value(out["argv"], opt, tag) if opt in out["argv"]
                           else list(out["argv"]) + [opt, tag])
        out["controller"] = tag
    lo, hi = EST_RANGE_S[est_kind]
    out.update(group=batch, rep_bundle=batch, criteria_id=criteria_id, est_s=hi,
               est_pool_s={"pcore": hi, "ecore": round(hi * 1.5, -1)}, planned_pool="pcore", note=note)
    if engine == "SCM":
        out["start_env"] = dict(START_ENV_SCM)
    else:
        out.pop("start_env", None)
    out.pop("run_env", None)
    out["r4368"] = {"rules": SOURCE, "criteria_id": criteria_id, "role": role, "engine": engine,
                    "former_controller": former, "tag": tag, "est_kind": est_kind, "est_range_s": [lo, hi],
                    **(extra or {})}
    return out


# =============================================================================================== row sets
def c1_c2_c3_rows(out: dict[str, list[dict]]) -> dict[str, list[dict[str, Any]]]:
    d1 = out["D1-CHRONO"]
    psc = out["D1-PSC"]
    res: dict[str, list[dict[str, Any]]] = {B_C1: [], B_C2: [], B_C3: []}
    for r in d1:
        rid = r.get("d1_id")
        engine = _engine(r)
        kind = {"L2b_NSC": "l2b", "L1R": "l1r"}.get(engine, "scm")
        tag = k1_tag_of(r.get("controller")) if engine != "L1R" else V0_TAG
        if rid in C1_IDS:
            res[B_C1].append(finish(r, batch=B_C1, criteria_id="C-1", role="judge" if engine != "L1R" else "record",
                                    tag=tag, est_kind=kind, extra={"d1_id": rid},
                                    note=f"{B_C1} {rid}: D1-CHRONO {r['case']} ({engine}), tag {tag}"))
        elif rid in C2_IDS:
            res[B_C2].append(finish(r, batch=B_C2, criteria_id="C-2", role="candidate", tag=tag, est_kind=kind,
                                    extra={"d1_id": rid, "select": r.get("d1_select")},
                                    note=f"{B_C2} {rid} candidate: D1-CHRONO {r['case']} ({engine}), tag {tag}; "
                                         "launched only when H-2 selects it"))
        elif rid in C3_IDS:
            res[B_C3].append(finish(r, batch=B_C3, criteria_id="C-3", role="judge", tag=tag, est_kind="scm_c3",
                                    extra={"d1_id": rid},
                                    note=f"{B_C3} {rid}: D1-CHRONO {r['case']} (SCM), tag {tag}; stored VB run = "
                                         "baseline record (spec 436.9.7)"))
    for r in psc:
        res[B_C2].append(finish(r, batch=B_C2, criteria_id="C-2", role="candidate",
                                tag=k1_tag_of(r.get("controller")), est_kind="scm",
                                extra={"d1_id": r.get("criteria_id"), "select": "psc"},
                                note=f"{B_C2} PS-c candidate: D1-PSC {r['case']} (SCM); launched only when H-2 S3 "
                                     "lists it"))
    if [r["case"] for r in res[B_C3]] != list(C3_NAMES):
        raise RuntimeError(f"{B_C3}: rows {[r['case'] for r in res[B_C3]]} != {C3_NAMES}")
    if len(res[B_C1]) != 10:
        raise RuntimeError(f"{B_C1}: {len(res[B_C1])} rows (10 expected)")
    return res


def c4_rows(sb: ModuleType) -> list[dict[str, Any]]:
    """C-4: ``las_chrono_rows`` mixed-ground form x Kc1 / Kc3 x LAS on / off (rules 5.2 C-4, 4.1, 4.2)."""
    r9 = _import("run_S9")
    lcr = _import("las_chrono_rows")
    rows = []
    for crawler, kn in (("Kc1", 1.0), ("Kc3", 3.0)):
        for arm in ("on", "off"):
            tag = VB_TAG if arm == "on" else OFF_VB_TAG
            c = lcr.base_case(r9)
            c["controller"] = tag
            argv = list(sb.RUN) + lcr.level_argv(r9, c, kn) + sb.v5_vb_argv()
            if arm == "off":
                argv = argv + list(OFF_ARM_ARGS)
            case = f"R4368C4_rigidJ1FR_B_top_Fs4_r2p3351_p1p5017_{crawler}_VB_las{arm}"
            a_id = "A1" if crawler == "Kc1" else "A3"
            row = {"case": case, "argv": argv, "controller": tag, "v5_setting": "VB",
                   "pair_case": case[:-len(arm)] + ("off" if arm == "on" else "on")}
            rows.append(finish(row, batch=B_C4, criteria_id="C-4", role="record", tag=tag, est_kind="mixed",
                               extra={"arm": arm, "crawler": crawler, "p5k_pair": a_id,
                                      "start_limit": "record_only", "duration_s": 160.0},
                               note=f"{B_C4} {crawler} LAS {arm}: V5-LAS-CHRONO form (rigid + J1@FR, floor (2.3351, "
                                    f"1.5017) deg, record_only, 160 s, VB), tag {tag}"
                                    + (" (--las-off --k1-order-gate on)" if arm == "off" else
                                       f"; = P5r4 {a_id} without --las-candidate P0")))
    return rows


def c5_rows(out: dict[str, list[dict]]) -> list[dict[str, Any]]:
    """C-5: V5-STAGE3-LAS (37) without P-2 / P-3 = 35 (L2b 24 + SCM 11), tags of rules 4.1."""
    rows = []
    for r in out["V5-STAGE3-LAS"]:
        if r["case"] in C5_DROP:
            continue
        engine = _engine(r)
        tag = k1_tag_of(r.get("controller"))
        row = finish(r, batch=B_C5, criteria_id="C-5", role="judge", tag=tag,
                     est_kind="l2b" if engine == "L2b_NSC" else "scm",
                     extra={"stage3_las_controller": r.get("controller"),
                            "hash_comparable_stored": r.get("hash_comparable")},
                     note=f"{B_C5}: V5-STAGE3-LAS {r['case']} ({engine}, {r.get('v5_setting')}), tag {tag}")
        wall = r.get("stored_wall_s")
        if engine == "L2b_NSC" and wall is not None and r.get("stored_pool") == "pcore":
            # rules 12.2 C-5 L2b: the stored stage 3 walls on P (batch_V5-STAGE3_20261107_184341)
            row["r4368"].update(est_kind="l2b_stored_wall", est_range_s=[round(float(wall)), round(float(wall))])
            row["est_s"] = round(float(wall))
            row["est_pool_s"] = {"pcore": row["est_s"], "ecore": round(row["est_s"] * 1.5, -1)}
        rows.append(row)
    n_l2b = sum(1 for r in rows if r["r4368"]["engine"] == "L2b_NSC")
    if len(rows) != C5_EXPECTED or n_l2b != 24:
        raise RuntimeError(f"{B_C5}: {len(rows)} rows ({C5_EXPECTED} expected), L2b {n_l2b} (24 expected)")
    return rows


def c6c7_rows(sb: ModuleType, out: dict[str, list[dict]]) -> list[dict[str, Any]]:
    """C-6 / C-7a / C-7b (rules 5.3): the G1 open-loop VB / V0 rows with ``--flow-law proportional`` or the budget
    speed (``s9_batch._fb_argv``: ``--lift-s 31.93 --lift-speed-fraction 0.87684``)."""
    vb = next(r for r in out[sb.V5_OPENLOOP_BATCH] if r["case"] == "P3a_G1_B_VB")
    v0 = next(r for r in out[sb.V5_OPENLOOP_V0_BATCH] if r["case"] == "P3a_G1_B_V0")
    k = vb["argv"].index("--flow-law")
    if vb["argv"][k + 1] != "priority":
        raise RuntimeError("P3a_G1_B_VB: flow law is not priority")
    prop = _set_value(vb["argv"], "--flow-law", "proportional")
    fb = {"lift_s": sb.V5_OPENLOOP_FB_LIFT_S, "lift_speed_fraction": sb.V5_OPENLOOP_FB_SPEED_FRACTION}
    spec = (("C-6", "P3a_G1_B_VB_prop", prop, vb, {**sb.V5_VB_ARGS, "flow_law": "proportional"},
             {"flow_law": "proportional"}, OPENLOOP_VB_STORED),
            ("C-7a", "P3a_G1_B_VB_FB", sb._fb_argv(vb["argv"]), vb, {**sb.V5_VB_ARGS, **fb}, fb, OPENLOOP_VB_STORED),
            ("C-7b", "P3a_G1_B_V0_FB", sb._fb_argv(v0["argv"]), v0, dict(fb), fb, OPENLOOP_V0_STORED))
    rows = []
    for cid, name, argv, base, exp_p3a, exp_v5, v5_stored in spec:
        row = {**base, "case": name, "argv": argv, "source_run": base["source_run"],
               "pair_case": base["case"], "v5_setting": base["v5_setting"]}
        rows.append(finish(row, batch=B_C6C7, criteria_id=cid, role="record", tag=None, est_kind=cid,
                           extra={"expected_diff_vs_p3a": exp_p3a, "expected_diff_vs_v5_openloop": exp_v5,
                                  "v5_openloop_stored": v5_stored, "controller_applied": False},
                           note=f"{B_C6C7} {cid}: {name} (open loop, no controller); base {v5_stored}"))
    return rows


def _a_row_argv(sb: ModuleType, base: str) -> list[str]:
    """The P5r4 A row argv of this checkout (``las_p5r4_k1_chrono_rows.level_argv``, ``--las-candidate P0``)."""
    p5k = _import("las_p5r4_k1_chrono_rows")
    r9 = _import("run_S9")
    crawler, setting = {"A1": ("Kc1", "VB"), "A3": ("Kc3", "VB"), "A5": ("Kc1", "V0")}[base]
    return list(sb.RUN) + p5k.level_argv(r9, sb, "A", crawler, 1.0, setting, "P0", 160.0)


def floor_of_k(k: float) -> tuple[float, float]:
    """Rules 5.4-8: (round(k 2.3351, 4), round(k 1.5017, 4)) deg."""
    return round(k * FLOOR_REF_DEG[0], 4), round(k * FLOOR_REF_DEG[1], 4)


def round_k(k: float) -> float:
    return round(float(k), K_DECIMALS)


def k_tag(k: float) -> str:
    return f"{k:.{K_DECIMALS}f}".replace(".", "p")


def oc5_argv(sb: ModuleType, rid: str, k: float, duration_s: float | None = None) -> list[str]:
    """C-8a / C-8b argv: the A3 / A5 argv without ``--las-candidate P0`` and with the floor of ``k`` (rules 5.4 table:
    these two the only differences); ``duration_s`` replaces ``--duration`` (probe / G-S)."""
    spec = OC5_ROWS[rid]
    argv = _drop_option(_a_row_argv(sb, spec["base"]), "--las-candidate")
    roll, pitch = floor_of_k(k)
    argv = _set_value(argv, "--floor-roll", f"{roll:g}")
    argv = _set_value(argv, "--floor-pitch", f"{pitch:g}")
    if duration_s is not None:
        argv = _set_value(argv, "--duration", f"{float(duration_s):g}")
    return argv


def oc5_first_k(rid: str) -> float:
    """Rules 5.4 first scale k_1 = 0.95 / R_c(A row), 4 decimals (0.9179 / 0.8829)."""
    return round_k(OC5_TARGET / OC5_ROWS[rid]["R_c_known"])


# --------------------------------------------------------------------------------------- probe procedure
def _within(rc: float) -> bool:
    return abs(rc - OC5_TARGET) <= OC5_TOL + CMP_EPS


def oc5_evaluate(rid: str, probes: list[dict[str, Any]]) -> dict[str, Any]:
    """Rules 5.4-3 .. 5.4-7 on the recorded probes of one row (in launch order). Returns ``status`` (``probing`` with
    ``next`` = {n, attempt, k, duration_s} | ``decided`` with ``k`` | ``stopped`` with ``reason``) and the counted
    probes (a doubled-duration retry is not counted, 5.4-3)."""
    pd = PROBE_DURATION_S[OC5_ROWS[rid]["base"]]
    k1 = oc5_first_k(rid)
    if not probes:
        return {"status": "probing", "next": {"n": 1, "attempt": 1, "k": k1, "duration_s": pd}, "n_probes": 0}
    last = probes[-1]
    counted = sorted({p["n"] for p in probes})
    if last.get("R_c") is None:
        if last["attempt"] == 1:
            return {"status": "probing", "n_probes": len(counted),
                    "next": {"n": last["n"], "attempt": 2, "k": last["k"], "duration_s": 2.0 * pd}}
        return {"status": "stopped", "n_probes": len(counted),
                "reason": "5.4-3: no R_c_operating after the doubled PROBE_DURATION (ask)"}
    by_n = {p["n"]: p for p in probes if p.get("R_c") is not None}
    n, r_now, k_now = last["n"], float(last["R_c"]), float(last["k"])
    if _within(r_now):
        return {"status": "decided", "k": k_now, "floor_deg": list(floor_of_k(k_now)), "R_c_probe": r_now,
                "decided_by_n": n, "n_probes": len(counted)}
    if n >= OC5_MAX_PROBES:
        return {"status": "stopped", "n_probes": len(counted), "reason": "5.4-7: third probe outside 0.95 +- 0.02"}
    r1, ka = float(by_n[1]["R_c"]), float(by_n[1]["k"])
    if n == 1:
        k_next = round_k(ka * OC5_TARGET / r1)
    else:
        r2, kb = float(by_n[2]["R_c"]), float(by_n[2]["k"])
        if r2 == r1:
            return {"status": "stopped", "n_probes": len(counted), "reason": "5.4-7: R_c(k2) = R_c(k1), no secant"}
        k_next = round_k(ka + (OC5_TARGET - r1) * (kb - ka) / (r2 - r1))
    if not (0.0 < k_next <= 1.0):
        return {"status": "stopped", "n_probes": len(counted), "reason": f"5.4-7: k {k_next} outside (0, 1]"}
    return {"status": "probing", "n_probes": len(counted),
            "next": {"n": n + 1, "attempt": 1, "k": k_next, "duration_s": pd}}


def oc5_state_path() -> Path:
    return Path(os.environ.get(OC5_STATE_ENV) or OC5_STATE_DEFAULT)


def oc5_state() -> dict[str, Any]:
    p = oc5_state_path()
    if p.is_file():
        return json.loads(p.read_text("utf-8"))
    return {"rules_sha256": RULES_SHA256, "probe_duration_s": dict(PROBE_DURATION_S),
            "rows": {rid: {"probes": [], "main": None} for rid in OC5_ROWS}}


def probe_case(rid: str, nxt: dict[str, Any]) -> str:
    spec = OC5_ROWS[rid]
    return (f"OC5P_{spec['crawler']}_{spec['setting']}_n{nxt['n']}" + ("_x2" if nxt["attempt"] == 2 else "")
            + f"_k{k_tag(nxt['k'])}")


def oc5_rows(sb: ModuleType, state: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(probe rows, main rows) from the probe state."""
    probes, mains = [], []
    for rid, spec in OC5_ROWS.items():
        ev = oc5_evaluate(rid, state["rows"][rid]["probes"])
        tag = VB_TAG if spec["setting"] == "VB" else V0_TAG
        common = {"oc5_row": rid, "oc5_base": spec["base"], "floor_ref_deg": list(FLOOR_REF_DEG),
                  "oc5_target": OC5_TARGET, "oc5_tol": OC5_TOL}
        if ev["status"] == "probing":
            nxt = ev["next"]
            roll, pitch = floor_of_k(nxt["k"])
            row = {"case": probe_case(rid, nxt), "argv": oc5_argv(sb, rid, nxt["k"], nxt["duration_s"]),
                   "controller": tag, "v5_setting": spec["setting"], "k": nxt["k"]}
            probes.append(finish(row, batch=B_PROBE, criteria_id=rid, role="probe", tag=tag, est_kind="probe",
                                 extra={**common, "probe": nxt, "floor_deg": [roll, pitch]},
                                 note=f"{B_PROBE} {rid} probe n{nxt['n']} attempt {nxt['attempt']}: k {nxt['k']:.4f}, "
                                      f"floor ({roll:g}, {pitch:g}) deg, --duration {nxt['duration_s']:g} "
                                      f"(PROBE_DURATION = {spec['base']} CHECK end "
                                      f"{PROBE_CHECK_END_S[spec['base']]:g} s + 2 s, ceil); start condition keys only"))
        elif ev["status"] == "decided":
            k = ev["k"]
            roll, pitch = floor_of_k(k)
            row = {"case": spec["name"], "argv": oc5_argv(sb, rid, k), "controller": tag,
                   "v5_setting": spec["setting"], "k": k}
            mains.append(finish(row, batch=B_OC5, criteria_id=rid, role="record", tag=tag, est_kind="mixed",
                                extra={**common, "k_decided": k, "floor_deg": [roll, pitch],
                                       "R_c_probe": ev["R_c_probe"], "n_probes": ev["n_probes"]},
                                note=f"{B_OC5} {rid}: {spec['base']} form, k {k:.4f}, floor ({roll:g}, {pitch:g}) deg, "
                                     f"no --las-candidate, tag {tag}; probe R_c {ev['R_c_probe']}"))
    return probes, mains


def jp_rows(out: dict[str, list[dict]], sb: ModuleType) -> list[dict[str, Any]]:
    """J_P re-run (rules 5.2 / 7.3, only when reuse fails): stored argv, tags of 4.1."""
    rows = []
    for name in (sb.V5_JP_BATCH, sb.V5_JP_V0_BATCH):
        for r in out[name]:
            rows.append(finish(r, batch=B_JP, criteria_id="JP", role="judge (7.3 reuse failed only)",
                               tag=k1_tag_of(r.get("controller")), est_kind="l2b",
                               note=f"{B_JP}: {name} {r['case']} re-run, tag {k1_tag_of(r.get('controller'))}"))
    return rows


GS_L2B_OF = ("C-1", "D1C2_middle_fdown3.2_Fs4")
GS_L1R_OF = ("C-1", "D1C1_top_flat_crx3")
GS_OL_OF = "P3a_G1_B_VB_prop"
"""User decision Q-3 (2026-11-13): engine representatives of the G-S (L2b, L1-R full length; open loop ``--lift-s``)."""


def gs_rows(sb: ModuleType, c1: list[dict], c2: list[dict], c3: list[dict], c4: list[dict], c5: list[dict],
            c6c7: list[dict]) -> list[dict[str, Any]]:
    """Rules 11.2: one row per Chrono option arm x stage of the run_S9 ``level`` batches, ``--duration`` 10 s, E pool
    (``planned_pool`` ``ecore``); plus (Q-3) one full-length L2b row and one L1-R row (P pool: their runners pin
    themselves) and the C-6 open-loop row with ``--lift-s`` :data:`GS_OPENLOOP_LIFT_S` (E pool)."""
    picks: list[tuple[str, dict[str, Any]]] = []
    s_cand = next(r for r in c2 if r["r4368"]["engine"] == "SCM" and r["r4368"].get("select") == "s_slope")
    picks.append(("C-2-SCM", s_cand))
    picks.append(("C-3", c3[0]))
    for r in c4:
        if r["r4368"]["crawler"] == "Kc3":
            picks.append((f"C-4-{r['r4368']['arm']}", r))
    seen = set()
    for r in c5:
        st = r.get("v5_setting")
        if r["r4368"]["engine"] == "SCM" and st not in seen:
            seen.add(st)
            picks.append((f"C-5-{st}", r))
    rows = []
    for stage, r in picks:
        argv = _set_value(r["argv"], "--duration", f"{GS_DURATION_S:g}")
        row = {**{k: v for k, v in r.items() if k != "r4368"}, "case": f"GS_{r['case']}", "argv": argv}
        keep = {k: r["r4368"][k] for k in ("arm", "crawler", "d1_id") if k in r["r4368"]}
        g = finish(row, batch=B_GS, criteria_id=r["criteria_id"], role="gs", tag=r.get("controller"),
                   est_kind="gs", extra={**keep, "gs_stage": stage, "gs_of": r["case"]},
                   note=f"{B_GS} {stage}: {r['case']} with --duration {GS_DURATION_S:g} (G-S, never judged)")
        g["planned_pool"] = "ecore"
        rows.append(g)
    for stage, src, kind in ((f"{GS_L2B_OF[0]}-L2b", next(r for r in c1 if r["case"] == GS_L2B_OF[1]), "l2b"),
                             (f"{GS_L1R_OF[0]}-L1R", next(r for r in c1 if r["case"] == GS_L1R_OF[1]), "l1r")):
        # user decision Q-3 (2026-11-13): one full-length row per engine; only the runner --tag differs
        argv = _set_value(src["argv"], "--tag", f"r4368gs_{src['case']}")
        row = {**{k: v for k, v in src.items() if k != "r4368"}, "case": f"GS_{src['case']}", "argv": argv}
        keep = {k: src["r4368"][k] for k in ("d1_id",) if k in src["r4368"]}
        rows.append(finish(row, batch=B_GS, criteria_id=src["criteria_id"], role="gs", tag=src.get("controller"),
                           est_kind=kind, extra={**keep, "gs_stage": stage, "gs_of": src["case"], "full_length": True},
                           note=f"{B_GS} {stage}: {src['case']} full length, --tag r4368gs_{src['case']} (G-S, Q-3)"))
    ol = next(r for r in c6c7 if r["case"] == GS_OL_OF)
    row = {**{k: v for k, v in ol.items() if k != "r4368"}, "case": f"GS_{ol['case']}_lift{GS_OPENLOOP_LIFT_S:g}",
           "argv": _set_value(ol["argv"], "--lift-s", f"{GS_OPENLOOP_LIFT_S:g}")}
    g = finish(row, batch=B_GS, criteria_id=ol["criteria_id"], role="gs", tag=None, est_kind="gs",
               extra={"gs_stage": "C-6-openloop", "gs_of": ol["case"]},
               note=f"{B_GS} C-6 open loop: {ol['case']} with --lift-s {GS_OPENLOOP_LIFT_S:g} (G-S, Q-3)")
    g["planned_pool"] = "ecore"
    rows.append(g)
    for rid in OC5_ROWS:
        spec = OC5_ROWS[rid]
        tag = VB_TAG if spec["setting"] == "VB" else V0_TAG
        row = {"case": f"GS_{spec['name']}_k1", "argv": oc5_argv(sb, rid, 1.0, GS_DURATION_S), "controller": tag,
               "v5_setting": spec["setting"], "k": 1.0}
        g = finish(row, batch=B_GS, criteria_id=rid, role="gs", tag=tag, est_kind="gs",
                   extra={"gs_stage": rid, "gs_of": spec["name"], "oc5_row": rid},
                   note=f"{B_GS} {rid}: k = 1 (A-row floor), --duration {GS_DURATION_S:g} (rules 11.2 C-8 G-S)")
        g["planned_pool"] = "ecore"
        rows.append(g)
    return rows


def resume_batches(sb: ModuleType, out: dict[str, list[dict]]) -> dict[str, list[dict[str, Any]]]:
    """All 436.8 Chrono batches for ``s9_batch.batches`` (needs D1-CHRONO, D1-PSC, V5-STAGE3-LAS, V5-OPENLOOP-*,
    V5-JP-* already in ``out``)."""
    res = c1_c2_c3_rows(out)
    res[B_C4] = c4_rows(sb)
    res[B_C5] = c5_rows(out)
    res[B_C6C7] = c6c7_rows(sb, out)
    res[B_PROBE], res[B_OC5] = oc5_rows(sb, oc5_state())
    res[B_JP] = jp_rows(out, sb)
    res[B_GS] = gs_rows(sb, res[B_C1], res[B_C2], res[B_C3], res[B_C4], res[B_C5], res[B_C6C7])
    for name, rows in res.items():
        names = [r["case"] for r in rows]
        dup = sorted({n for n in names if names.count(n) > 1})
        if dup:
            raise RuntimeError(f"{name}: duplicate row names {dup}")
    return res


# =============================================================================================== build checks
def _level_check(r: dict[str, Any], r9: ModuleType, diffs: list[dict[str, Any]]) -> dict[str, Any]:
    level = script_tail(r["argv"])
    out: dict[str, Any] = {}
    try:
        a = r9.build_parser().parse_args(level)
    except SystemExit as e:
        diffs.append({"key": "argparse", "want": "ok", "got": str(e)})
        return out
    if a.threads != r9.SCM_THREADS_FIXED:
        diffs.append({"key": "threads", "want": r9.SCM_THREADS_FIXED, "got": a.threads})
    if level[0] != "level":
        return out
    tag = r["controller"]
    if getattr(a, "expect_controller", None) != tag:
        diffs.append({"key": "expect_controller", "want": tag, "got": getattr(a, "expect_controller", None)})
    k1c = _import("las_k1_chrono_rows")
    try:
        config = k1c.run_level_config(r9, a)
    except SystemExit as e:
        diffs.append({"key": "level_config", "want": "ok", "got": f"SystemExit({e.code})"})
        return out
    chk = r9.controller_expectation(config, tag)
    if not chk["ok"]:
        diffs.append({"key": "controller_expectation", "want": tag, "got": [c for c in chk["checks"] if not c["ok"]]})
    v5o = _v5opt()
    off_arm = r["r4368"].get("arm") == "off"
    want_las, want_gate = (not off_arm), True
    if v5o.is_liftoff_slow_on(config) is not want_las:
        diffs.append({"key": "liftoff_approach_slow.enable", "want": want_las, "got": v5o.is_liftoff_slow_on(config)})
    if v5o.is_order_gate_on(config) is not want_gate:
        diffs.append({"key": "flat_soil_margin_order_gate", "want": want_gate, "got": v5o.is_order_gate_on(config)})
    if v5o.is_touch_creep_on(config):
        diffs.append({"key": "touch_creep_latch", "want": False, "got": True})
    out.update(expect_controller_ok=chk["ok"], las_on=v5o.is_liftoff_slow_on(config),
               order_gate=v5o.is_order_gate_on(config), k1_order_gate_request=r9.k1_order_gate_request(a),
               las_off=bool(getattr(a, "las_off", False)), start_limit=getattr(a, "start_limit", None),
               floor_deg=[getattr(a, "floor_roll", None), getattr(a, "floor_pitch", None)],
               duration_s=a.duration)
    return out


_S8C_TABLE: dict[str, Any] | None = None


def _s8c_check(r: dict[str, Any], sb: ModuleType, diffs: list[dict[str, Any]]) -> dict[str, Any]:
    global _S8C_TABLE
    _src_path()
    s8 = _import("run_S8C")
    s6 = _import("run_S6C")
    s7 = _import("run_S7C")
    from outrigger_sim.params import load_params  # noqa: PLC0415

    opt = RUNNER_EXPECT_OPTION.get("L2b_NSC")
    plain = {**r, "argv": _drop_option(r["argv"], opt) if opt else r["argv"]}  # the v5 parser has no tag option
    src = sb.v5_rigid_source_check(plain, root=results_root())
    if src["status"] == "differs":
        diffs.extend({"key": f"v5_args:{d['key']}", "want": d["former"], "got": d["row"]} for d in src["diffs"])
    if _S8C_TABLE is None:
        _S8C_TABLE = s8.case_table()
    cid = r.get("s8c_case_id", r["case"])
    c = _S8C_TABLE.get(cid)
    if c is None:
        diffs.append({"key": "s8c_case", "want": cid, "got": None})
        return {}
    if c.engine != "L2b_NSC":
        diffs.append({"key": "engine", "want": "L2b_NSC", "got": c.engine})
    cfg, _ = s7.apply_settle_map(s6.controller_config(load_params(level=c.scenario.level), c.base), "L2b_NSC",
                                 c.scenario.level)
    v5o = _v5opt()
    base = v5o.EXTEND_START_CONTROLLER_TAG if sb.v5_rigid_setting_args(r["v5_setting"]).get(
        "extend_start_tracked") else None
    tag = v5o.with_switch_tags(base, cfg) or v5o.FINAL_CONTROLLER_TAG
    if tag != r["controller"]:
        diffs.append({"key": "built_tag", "want": r["controller"], "got": tag})
    return {"built_tag": tag, "engine": c.engine, "v5_source_check": src["status"], "level": c.scenario.level}


def _s6c_check(r: dict[str, Any], diffs: list[dict[str, Any]]) -> dict[str, Any]:
    _src_path()
    s6 = _import("run_S6C")
    from outrigger_sim.params import load_params  # noqa: PLC0415

    argv = r["argv"]
    cid = argv[argv.index("--only") + 1]
    c = next((x for x in s6.d1c1_cases() if x.case_id == cid), None)
    if c is None:
        diffs.append({"key": "s6c_case", "want": cid, "got": None})
        return {}
    tag = s6.controller_tag_of(s6.controller_config(load_params(level=c.scenario.level), c))
    if tag != r["controller"]:
        diffs.append({"key": "built_tag", "want": r["controller"], "got": tag})
    snap = c.scenario.snapshot_override or c.scenario.snapshot
    return {"built_tag": tag, "start_snapshot": snap, "uses_fdown3p5_snapshot": "fdown3.5" in str(snap)}


def argv_check(r: dict[str, Any], sb: ModuleType) -> dict[str, Any]:
    """Build check of one 436.8 row without Chrono (rules 4.1 / 4.2 / 6 / 11.1 parts)."""
    diffs: list[dict[str, Any]] = []
    argv = r["argv"]
    tail = script_tail(argv)
    engine = r["r4368"]["engine"]
    head = argv[:len(argv) - len(tail)]
    want_head = {"SCM": sb.RUN, "L2b_NSC": sb.S8C, "L1R": sb.S6C}[engine]
    if [Path(t).name for t in head] != [Path(t).name for t in want_head]:
        diffs.append({"key": "runner_head", "want": [Path(t).name for t in want_head], "got": [Path(t).name
                                                                                            for t in head]})
    if any(PRE_RUNNER_RE.search(t) for t in argv):
        diffs.append({"key": "pre_preset_runner", "want": "absent", "got": "present"})
    off_arm = r["r4368"].get("arm") == "off"
    allowed = OFF_ARM_ARGS[:2] if off_arm else ()
    for tok in FORBIDDEN_TOKENS:
        if tok in tail and tok not in allowed:
            diffs.append({"key": tok, "want": "absent", "got": "present"})
    if off_arm:
        k = tail.index("--k1-order-gate") if "--k1-order-gate" in tail else -1
        if "--las-off" not in tail or k < 0 or tail[k + 1] != "on":
            diffs.append({"key": "off_arm_args", "want": list(OFF_ARM_ARGS), "got": tail[-3:]})
    env = {**(r.get("start_env") or {}), **(r.get("run_env") or {})}
    for key in FORBIDDEN_ENV:
        if key in env:
            diffs.append({"key": f"env:{key}", "want": "absent", "got": env[key]})
    if engine == "SCM" and env.get("OMP_WAIT_POLICY") != "PASSIVE":
        diffs.append({"key": "start_env.OMP_WAIT_POLICY", "want": "PASSIVE", "got": env.get("OMP_WAIT_POLICY")})
    want_pool = "ecore" if r["r4368"]["role"] == "gs" and engine == "SCM" else "pcore"
    if r.get("planned_pool") != want_pool:
        diffs.append({"key": "planned_pool", "want": want_pool, "got": r.get("planned_pool")})
    info: dict[str, Any] = {}
    if engine in RUNNER_EXPECT_OPTION:
        opt = RUNNER_EXPECT_OPTION[engine]
        if opt is None and "--expect-controller" in tail:
            diffs.append({"key": "--expect-controller", "want": "absent (runner option not yet available, Q-2)",
                          "got": "present"})
        elif opt is not None and r["r4368"]["tag"] is not None and (opt not in tail
                                                                    or tail[tail.index(opt) + 1] != r["controller"]):
            diffs.append({"key": opt, "want": r["controller"], "got": tail[tail.index(opt) + 1] if opt in tail
                          else "absent"})
    if engine == "SCM":
        info = _level_check(r, _import("run_S9"), diffs)
    elif engine == "L2b_NSC":
        info = _s8c_check(r, sb, diffs)
    else:
        info = _s6c_check(r, diffs)
    if r["r4368"]["tag"] is not None:
        want_tag = OFF_VB_TAG if off_arm else (VB_TAG if r.get("v5_setting") in ("VB", "LS1", "LS4") else None)
        if want_tag is not None and r["controller"] != want_tag:
            diffs.append({"key": "row_tag", "want": want_tag, "got": r["controller"]})
        if r["controller"] not in (VB_TAG, V0_TAG, OFF_VB_TAG):
            diffs.append({"key": "row_tag_set", "want": [VB_TAG, V0_TAG, OFF_VB_TAG], "got": r["controller"]})
        if not off_arm and r["controller"] != k1_tag_of(r["r4368"]["former_controller"]) \
                and r["r4368"]["former_controller"] is not None:
            diffs.append({"key": "retag", "want": k1_tag_of(r["r4368"]["former_controller"]), "got": r["controller"]})
    return {"case": r["case"], "batch": r["group"], "criteria_id": r["criteria_id"], "engine": engine,
            "status": "differs" if diffs else "ok", "diffs": diffs, "info": info, "argv_sha256": argv_sha256(argv)}


def _stored_entries(rel: str) -> dict[str, dict[str, Any]]:
    p = results_root() / rel / "batch.json"
    if not p.is_file():
        return {}
    return {c["case"]: c for c in json.loads(p.read_text("utf-8")).get("cases", [])}


def pair_checks(sb: ModuleType, b: dict[str, list[dict]]) -> list[dict[str, Any]]:
    """C-4 on arm vs P5r4 A1 / A3 (rules 5.2 C-4: only ``--las-candidate`` may differ), C-4 off vs on (``--las-off``
    / ``--k1-order-gate`` / ``--expect-controller``), C-8 rows vs A3 / A5 (5.4: floor + ``--las-candidate``),
    C-6 / C-7 against the stored results (5.3 ``check-sources``)."""
    out = []
    stored = _stored_entries(P5K_STORED)
    c4 = {(r["r4368"]["crawler"], r["r4368"]["arm"]): r for r in b[B_C4]}
    for crawler, a_id in (("Kc1", "A1"), ("Kc3", "A3")):
        on, off = c4[(crawler, "on")], c4[(crawler, "off")]
        live = _a_row_argv(sb, a_id)
        st = stored.get(P5K_A_CASES[a_id], {}).get("argv")
        d_live = option_diff(on["argv"], live)
        d_st = option_diff(on["argv"], st) if st else None
        d_off = option_diff(off["argv"], on["argv"])
        out.append({"check": f"C-4 {crawler} on vs P5r4 {a_id}", "option_diff_live": d_live,
                    "option_diff_stored": d_st, "stored": f"{P5K_STORED}/{P5K_A_CASES[a_id]}",
                    "ok": d_live == ["--las-candidate"] and d_st in (["--las-candidate"], None),
                    "stored_present": st is not None})
        out.append({"check": f"C-4 {crawler} off vs on", "option_diff": d_off,
                    "ok": d_off == ["--expect-controller", "--k1-order-gate", "--las-off"]})
    for rid, spec in OC5_ROWS.items():
        a = _a_row_argv(sb, spec["base"])
        st = stored.get(P5K_A_CASES[spec["base"]], {}).get("argv")
        row = oc5_argv(sb, rid, oc5_first_k(rid))
        d_live, d_st = option_diff(row, a), (option_diff(row, st) if st else None)
        want = ["--floor-pitch", "--floor-roll", "--las-candidate"]
        k1 = oc5_argv(sb, rid, 1.0)
        out.append({"check": f"{rid} (k1 {oc5_first_k(rid):.4f}) vs P5r4 {spec['base']}", "option_diff_live": d_live,
                    "option_diff_stored": d_st, "k1_floor_deg": list(floor_of_k(oc5_first_k(rid))),
                    "k_eq_1_option_diff_live": option_diff(k1, a),
                    "ok": d_live == want and d_st in (want, None) and option_diff(k1, a) == ["--las-candidate"]})
    a3 = oc5_argv(sb, "C-8a", 1.0)
    out.append({"check": "C-4 Kc3 on == C-8a at k = 1 (argv)", "same": script_tail(a3) == script_tail(c4[("Kc3", "on")]
                                                                                                  ["argv"]),
                "ok": True})
    r9 = _import("run_S9")
    for r in b[B_C6C7]:
        rec = r["r4368"]
        res = {"check": f"{rec['criteria_id']} {r['case']} check-sources"}
        for label, src, exp in (("vs_p3a", r["source_run"], rec["expected_diff_vs_p3a"]),
                                ("vs_v5_openloop", rec["v5_openloop_stored"], rec["expected_diff_vs_v5_openloop"])):
            folder = results_root() / "07_results" / "S9" / src
            chk = r9.source_args_check(script_tail(r["argv"]), folder)
            chk = sb.expected_diff_check(chk, exp)
            res[label] = {"source": f"07_results/S9/{src}", "status": chk["status"],
                          "diffs": chk.get("diffs")}
        res["ok"] = all(res[k]["status"] == "ok_expected_diff" for k in ("vs_p3a", "vs_v5_openloop"))
        out.append(res)
    return out


def count_checks(b: dict[str, list[dict]]) -> list[dict[str, Any]]:
    want = {B_C1: 10, B_C3: 2, B_C4: 4, B_C5: C5_EXPECTED, B_C6C7: 3, B_JP: 12}
    out = [{"check": f"rows {name}", "rows": len(b[name]), "want": n, "ok": len(b[name]) == n}
           for name, n in want.items()]
    eng = {}
    for name in (B_C1, B_C5):
        for r in b[name]:
            eng.setdefault(name, {}).setdefault(r["r4368"]["engine"], 0)
            eng[name][r["r4368"]["engine"]] += 1
    out.append({"check": "engines", "by_batch": eng,
                "ok": eng.get(B_C1) == {"L2b_NSC": 6, "L1R": 4} and eng.get(B_C5) == {"L2b_NSC": 24, "SCM": 11}})
    return out


def a7_rows(b: dict[str, list[dict]], checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Rules A-7: rows whose start state is a fdown3.5 L1-R snapshot (L1-R rows: their snapshot; L2b rows: engine
    L2b_NSC = own settle, no L1-R snapshot; SCM rows: own settle)."""
    l1r = [{"case": c["case"], "snapshot": c["info"].get("start_snapshot"),
            "uses_fdown3p5": c["info"].get("uses_fdown3p5_snapshot")} for c in checks if c["engine"] == "L1R"]
    l2b_not_l2b = [c["case"] for c in checks if c["engine"] == "L2b_NSC" and c["info"].get("engine") != "L2b_NSC"]
    return {"l1r_rows": l1r, "rows_using_fdown3p5": [x["case"] for x in l1r if x["uses_fdown3p5"]],
            "l2b_rows_not_L2b_NSC": l2b_not_l2b,
            "rule": "L1-R rows: start snapshot of run_S6C (snapshot_override); L2b-NSC / SCM rows settle on their own"}


# =============================================================================================== CLI pieces
def _batches() -> tuple[ModuleType, dict[str, list[dict]]]:
    sb = _import("s9_batch")
    allb = sb.batches()
    return sb, {k: allb[k] for k in BATCHES}


def cmd_check(out_path: str | None) -> int:
    sb, b = _batches()
    checks = [argv_check(r, sb) for name in BATCHES if name != B_JP for r in b[name]]
    checks += [argv_check(r, sb) for r in b[B_JP]]
    pairs = pair_checks(sb, b)
    counts = count_checks(b)
    doc = {"rules": SOURCE, "env_forbidden_set": [k for k in FORBIDDEN_ENV if os.environ.get(k)],
           "probe_duration_s": PROBE_DURATION_S, "rows": checks, "pairs": pairs, "counts": counts,
           "a7": a7_rows(b, checks)}
    n_err = sum(1 for c in checks if c["status"] != "ok") + sum(1 for p in pairs if not p["ok"]) \
        + sum(1 for c in counts if not c["ok"]) + len(doc["env_forbidden_set"])
    doc["n_errors"] = n_err
    text = json.dumps(doc, indent=1, default=str)
    if out_path:
        Path(out_path).write_text(text, "utf-8")
    print(json.dumps({"rows": len(checks), "rows_differ": [c["case"] for c in checks if c["status"] != "ok"],
                      "pairs_fail": [p["check"] for p in pairs if not p["ok"]],
                      "counts_fail": [c["check"] for c in counts if not c["ok"]], "a7": doc["a7"]["rows_using_fdown3p5"]},
                     indent=1))
    print(f"errors {n_err}")
    return 0 if n_err == 0 else 1


def cmd_manifest(out_path: str) -> int:
    sb, b = _batches()
    doc: dict[str, Any] = {"rules": SOURCE, "batches": {}}
    for name in BATCHES:
        rows = []
        for r in b[name]:
            rows.append({"case": r["case"], "criteria_id": r["criteria_id"], "role": r["r4368"]["role"],
                         "engine": r["r4368"]["engine"], "controller": r.get("controller"),
                         "v5_setting": r.get("v5_setting"), "planned_pool": r.get("planned_pool"),
                         "start_env": r.get("start_env"), "est_range_s": r["r4368"]["est_range_s"],
                         "argv_sha256": argv_sha256(r["argv"]), "argv_tail": script_tail(r["argv"]),
                         "depends_on": r.get("depends_on")})
        lo = sum(x["est_range_s"][0] for x in rows)
        hi = sum(x["est_range_s"][1] for x in rows)
        doc["batches"][name] = {"rows": rows, "n": len(rows), "est_sum_s": [lo, hi],
                                "list_sha256": hashlib.sha256("\n".join(f"{x['case']} {x['argv_sha256']}"
                                                                        for x in rows).encode()).hexdigest()}
    checks = [argv_check(r, sb) for name in BATCHES for r in b[name] if r["r4368"]["engine"] != "SCM"]
    a7 = a7_rows(b, checks)
    a7["decision"] = ("A-7 해당 없음: fdown3.5 L1-R 스냅숏을 시작 상태로 쓰는 436.8 행 0행 (사용자 결정 Q-5, 2026-11-13)"
                      if not a7["rows_using_fdown3p5"] else "A-7 적용: 위 행은 저장 행과 '조건 다름, 해시 비교 없음'")
    doc["a7"] = a7
    doc["probe_duration_s"] = {"value": PROBE_DURATION_S, "rule": "CHECK end = phase 'touch' start - loop start "
                               "(stored A3 / A5: 4.8 s) + 2 s, ceil (user decision Q-7, 2026-11-13)"}
    doc["k_rounding"] = "k rounded to 4 decimals, floors from the rounded k (user decision Q-1, 2026-11-13)"
    Path(out_path).write_text(json.dumps(doc, indent=1, default=str) + "\n", "utf-8")
    print(a7["decision"])
    for name, v in doc["batches"].items():
        print(f"{name} rows {v['n']} est_sum_s {v['est_sum_s']} list_sha256 {v['list_sha256']}")
    print("errors 0")
    return 0


def cmd_c2_select(h2: str, out_path: str | None) -> int:
    """Rules 5.2 C-2: the H-2 output (``d1_select.py`` report: S1 / S2 ``selected`` + S3 ``rows``) -> the
    ``--only-file`` list of ``V5-RESUME-K1-C2``; count 4 .. 10 (else stop, 8.2 S-15)."""
    p = Path(h2)
    if not p.is_file():
        print(f"c2-select: no file {h2}", file=sys.stderr)
        print("errors 1")
        return 2
    doc = json.loads(p.read_text("utf-8"))
    errors: list[str] = []
    if doc.get("exit_code") != 0:
        errors.append(f"H-2 exit_code {doc.get('exit_code')} (gates {doc.get('gates')})")
    names: list[str] = []
    for part in ("S1", "S2"):
        for cell, v in (doc.get(part) or {}).items():
            names += list(v.get("selected") or [])
    names += list((doc.get("S3") or {}).get("rows") or [])
    names = list(dict.fromkeys(names))
    _, b = _batches()
    known = {r["case"] for r in b[B_C2]}
    unknown = [n for n in names if n not in known]
    if unknown:
        errors.append(f"names outside {B_C2}: {unknown}")
    lo, hi = C2_COUNT_RANGE
    if not lo <= len(names) <= hi:
        errors.append(f"{len(names)} rows outside {lo} .. {hi} (rules 5.2 C-2, 8.2 S-15)")
    res = {"h2": p.as_posix(), "h2_sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "cases": names,
           "n": len(names), "errors": errors}
    if out_path:
        Path(out_path).write_text(json.dumps(res, indent=1) + "\n", "utf-8")
    print(json.dumps(res, indent=1))
    print(f"errors {len(errors)}")
    return 0 if not errors else 1


_MISSING = object()


def _get(doc: Any, path: str) -> Any:
    node = doc
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


def cmd_oc5_status() -> int:
    st = oc5_state()
    out = {"state": oc5_state_path().as_posix(), "probe_duration_s": PROBE_DURATION_S, "rows": {}}
    for rid in OC5_ROWS:
        out["rows"][rid] = {"first_k": oc5_first_k(rid), **oc5_evaluate(rid, st["rows"][rid]["probes"]),
                            "probes": st["rows"][rid]["probes"], "main": st["rows"][rid].get("main")}
    print(json.dumps(out, indent=1, default=str))
    stops = [rid for rid, v in out["rows"].items() if v["status"] == "stopped"]
    print(f"errors {len(stops)}")
    return 1 if stops else 0


def cmd_oc5_read(folder: str) -> int:
    """Read a ``V5-RESUME-K1-OC5PROBE`` / ``-OC5`` batch folder: only :data:`PROBE_READ_KEYS` of each row's
    result.json (rules 5.4-2), append probes to the state file, print the next step (5.4-3 .. 7) and, for main rows, the
    main-row R_c against the deciding probe (5.4-9, P-14)."""
    f = Path(folder)
    bpath = f / "batch.json"
    if not bpath.is_file():
        print(f"oc5-read: no batch.json in {folder}", file=sys.stderr)
        print("errors 1")
        return 2
    batch = json.loads(bpath.read_text("utf-8"))
    st = oc5_state()
    errors: list[str] = []
    read: list[dict[str, Any]] = []
    for e in batch.get("cases", []):
        rec = e.get("r4368") or {}
        if rec.get("role") not in ("probe", "record") or rec.get("oc5_row") not in OC5_ROWS:
            continue
        rid = rec["oc5_row"]
        res = f / e["case"] / "result.json"
        vals: dict[str, Any] = {k: None for k in PROBE_READ_KEYS}
        if e.get("rc") == 0 and res.is_file():
            doc = json.loads(res.read_text("utf-8"))
            for k in PROBE_READ_KEYS:
                v = _get(doc, k)
                vals[k] = None if v is _MISSING else v
            del doc
        elif e.get("rc") != 0:
            errors.append(f"{e['case']}: rc {e.get('rc')}")
        rc_val = vals["p3b_ext.start_condition.R_c_operating"]
        entry = {"case": e["case"], "folder": f.as_posix(), "k": rec.get("probe", {}).get("k", rec.get("k_decided")),
                 "R_c": rc_val, "crawler_attitude_deg": vals["p3b_ext.start_condition.crawler_attitude_deg"],
                 "floor_deg_args": [vals["args.floor_roll"], vals["args.floor_pitch"]],
                 "duration_s": vals["args.duration"], "phases": vals["phases"]}
        if rec["role"] == "probe":
            entry.update(n=rec["probe"]["n"], attempt=rec["probe"]["attempt"])
            if any(p["case"] == e["case"] and p["folder"] == entry["folder"] for p in st["rows"][rid]["probes"]):
                continue
            st["rows"][rid]["probes"].append(entry)
        else:
            entry["R_c_probe"] = rec.get("R_c_probe")
            entry["same_as_probe"] = (rc_val is not None and rec.get("R_c_probe") is not None
                                      and float(rc_val) == float(rec["R_c_probe"]))
            entry["R_c_le_1"] = None if rc_val is None else bool(float(rc_val) <= 1.0 + CMP_EPS)
            st["rows"][rid]["main"] = entry
        read.append({"row": rid, **entry})
    p = oc5_state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, indent=1, default=str) + "\n", "utf-8")
    status = {rid: oc5_evaluate(rid, st["rows"][rid]["probes"]) for rid in OC5_ROWS}
    for rid, v in status.items():
        if v["status"] == "stopped":
            errors.append(f"{rid}: {v['reason']}")
        m = st["rows"][rid].get("main")
        if m is not None and m.get("R_c_le_1") is False:
            errors.append(f"{rid}: main row R_c > 1 (5.4-9, S-10)")
    print(json.dumps({"state": p.as_posix(), "read": read, "status": status}, indent=1, default=str))
    print(f"errors {len(errors)}")
    return 0 if not errors else 1


# --------------------------------------------------------------------------------------------- G-S field check
def gs_key_paths() -> tuple[tuple[str, ...], dict[str, str]]:
    """Key paths the 436.8 judge tools read (4.2 record check, 7.2 K1 classes, 7.4 records, 6 identity) and the
    conditional ones (key -> condition)."""
    p5k = _import("las_p5r4_k1_chrono_rows")
    drop = ("c2_setup.las_candidate.", "args.las_candidate", "code_files_at_start.")
    keys = [k for k in p5k.RESULT_KEY_PATHS if not k.startswith(drop)]
    keys += ["p3b_ext.start_condition.R_c_operating", "p3b_ext.start_condition.crawler_attitude_deg",
             "p3b_ext.start_condition.operating_rule_rejects", "args.floor_roll", "args.floor_pitch",
             "args.start_limit", "args.expect_controller", "c2_setup.preset", "placement"]
    cond = dict(p5k.CONDITIONAL_KEY_PATHS)
    cond["c2_setup.las_off"] = "<off arm>"
    keys.append("c2_setup.las_off")
    for k in OFF_ARM_ABSENT_KEYS:
        cond[k] = "<on arm>"
    return tuple(dict.fromkeys(keys)), cond


OFF_ARM_ABSENT_KEYS = tuple(f"controller_meta.liftoff_approach_slow.{k}" for k in (
    "start_s", "end_s", "end_reason", "active_periods", "ramp", "ramp.periods_applied"))
"""G-S 2026-11-13 (C-4 off arm, ``--las-off``): run_S9 writes ``controller_meta.liftoff_approach_slow`` = only
``settings`` (``enable`` False) with LAS-b off; these keys exist on the on-arm rows only."""
SERIES_FILES = ("step_series.npz", "r8_series.npz")
"""run_S9 ``level`` series files (rules 9.1 path 2 names ``series.npz`` / ``r8_series``; a level run writes
``step_series.npz``, G-S 2026-11-13)."""


RIGID_KEY_PATHS = (
    "controller_meta.liftoff_approach_slow.settings", "controller_meta.liftoff_approach_slow.start_s",
    "controller_meta.liftoff_approach_slow.end_s", "controller_meta.liftoff_approach_slow.end_reason",
    "controller_meta.liftoff_approach_slow.active_periods",
    "controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate",
    "controller_meta.slope_clearance_margin.order_gate", "controller_meta.slope_clearance_margin.order_gate.decisions",
    "controller_meta.soil", "controller_meta.loc_revoke", "phases", "ready_t_s", "events_count", "monitor",
    "stroke.max_m", "runner.placement", "runner.sensor_seed", "runner.wall_s", "settings.controller_config",
    "acceptance.crawler_attitude_deg")
"""L2b / L1-R result.json keys the judge tools read (Q-3 G-S, 2026-11-13: 7.2 classes, 4.2 record, 6 identity)."""
RIGID_EXPECT_KEYS = ("controller_tag", "expect_controller.ok", "expect_controller.name")
"""python-expert c17481d record (top level): required when the row argv carries the tag option."""
RIGID_FILES = {"L2b_NSC": ("controller_events.json", "r8_series.npz", "s8_series.npz", "case.json"),
               "L1R": ("controller_events.json", "r8_series.npz", "case.json")}
L2B_VB_KEYS = ("v5_hydraulics.controller_tag", "v5_hydraulics.hydraulic_options", "flow_limit.setting")
OPENLOOP_KEY_PATHS = ("p3a.checks", "p3a.P3a-1_force_peak", "p3a.P3a-2_liftoff", "p3a.P3a-9_min_cylinder_force",
                      "p3a.t_lift_start_s", "num_threads_chrono", "placement.mode", "placement.omp_wait_policy",
                      "placement.power_throttling_off_ok", "placement.affinity_ok", "hull_hook.mode",
                      "hull_hook.fallback_reason", "hull_hook.dll_sha256", "args.lift_s", "args.lift_speed_fraction",
                      "args.flow_law", "v5_hydraulics.controller_options", "flow_limit.summary", "wall_s")
OPENLOOP_FILES = ("series.npz", "flow_series.npz")


def gs_kind(entry: dict[str, Any]) -> str:
    rec = entry.get("r4368") or {}
    if rec.get("engine") in ("L2b_NSC", "L1R"):
        return rec["engine"]
    tail = script_tail(entry.get("argv") or [])
    return "openloop" if tail[:1] == ["machine"] else "level"


def _gs_other(f: Path, e: dict[str, Any], kind: str) -> dict[str, Any]:
    """Presence check of an L2b / L1-R (result in the runner's own folder, from the case log) or open-loop row."""
    not_expected = {"openloop": ("controller", "code_at_launch"),
                    "L1R": ("start_env", "v5_setting")}.get(kind, ("start_env",))  # L1-R: no v5 option (None)
    c: dict[str, Any] = {"case": e["case"], "kind": kind, "batch_entry_missing": [k for k in GS_ENTRY_KEYS
                                                                                   if k not in e
                                                                                   and k not in not_expected]}
    progress = (f / "progress.log").read_text("utf-8", errors="replace") if (f / "progress.log").is_file() else ""
    c["progress_end_rc0"] = re.search(rf"^END {re.escape(e['case'])} \S+ rc=0\b", progress, re.M) is not None
    if kind == "openloop":
        case_dir, keys, files = f / e["case"], list(OPENLOOP_KEY_PATHS), OPENLOOP_FILES
    else:
        tail = script_tail(e.get("argv") or [])
        cid = tail[tail.index("--only") + 1]
        log = f / f"{e['case']}.log"
        chk = _import("s9_batch").s8c_case_check(log.read_text("utf-8", errors="replace"), cid) if log.is_file() \
            else {"ok": False, "result_json": None}
        c["runner_outcome_ok"] = bool(chk.get("ok"))
        c["runner_batch_dir"] = chk.get("batch_dir")
        case_dir = Path(chk["result_json"]).parent if chk.get("result_json") else f / "<missing>"
        keys, files = list(RIGID_KEY_PATHS), RIGID_FILES[kind]
        if kind == "L2b_NSC" and e.get("v5_setting") in ("VB", "LS1", "LS4"):
            keys += list(L2B_VB_KEYS)
        opt = RUNNER_EXPECT_OPTION.get(kind)
        c["argv_has_tag_option"] = bool(opt and opt in tail)
        if c["argv_has_tag_option"]:
            keys += list(RIGID_EXPECT_KEYS)
        else:
            c["tag_keys_not_required"] = "argv without the tag option (run before python-expert c17481d)"
    res = case_dir / "result.json"
    c["result_json"] = res.is_file()
    c["result_missing"] = list(keys)
    if res.is_file():
        doc = json.loads(res.read_text("utf-8"))
        c["result_missing"] = [k for k in keys if _get(doc, k) is _MISSING]
    c["files_missing"] = [n for n in files if not (case_dir / n).is_file()]
    c["n_key_paths"] = len(keys)
    c["ok"] = (c["progress_end_rc0"] and not c["batch_entry_missing"] and c["result_json"] and not c["result_missing"]
               and not c["files_missing"] and c.get("runner_outcome_ok", True))
    return c


GS_ENTRY_KEYS = ("case", "argv", "rc", "pool", "planned_pool", "omp_wait_policy", "hull_hook_requested",
                 "hull_hook_effective", "hull_hook_env", "start_env", "code_at_launch", "controller", "v5_setting",
                 "criteria_id", "r4368")


def cmd_gs_check(folder: str) -> int:
    """Presence-only field check of a ``V5-RESUME-K1-GS`` folder (no values printed)."""
    import numpy as np  # noqa: PLC0415

    f = Path(folder)
    bpath, ppath = f / "batch.json", f / "progress.log"
    if not bpath.is_file():
        print(f"gs-check: no batch.json in {folder}", file=sys.stderr)
        print("errors 1")
        return 2
    batch = json.loads(bpath.read_text("utf-8"))
    progress = ppath.read_text("utf-8", errors="replace") if ppath.is_file() else ""
    end_rc = {m.group(1): m.group(2) for m in re.finditer(r"^END (\S+) \S+ rc=(-?\d+|None)", progress, re.M)}
    keys, cond = gs_key_paths()
    cases = []
    for e in batch.get("cases", []):
        kind = gs_kind(e)
        if kind != "level":
            cases.append(_gs_other(f, e, kind))
            continue
        c: dict[str, Any] = {"case": e["case"], "progress_end_rc0": end_rc.get(e["case"]) == "0",
                             "batch_entry_missing": [k for k in GS_ENTRY_KEYS if k not in e],
                             "mixed_hull_mode_key": "mixed_hull_mode" in batch}
        res = f / e["case"] / "result.json"
        c["result_json"] = res.is_file()
        missing, conditional = list(keys), []
        if res.is_file():
            doc = json.loads(res.read_text("utf-8"))
            absent = [k for k in keys if _get(doc, k) is _MISSING]
            off_arm = (e.get("r4368") or {}).get("arm") == "off"
            missing = []
            for k in absent:
                if (k == "c2_setup.las_off" and not off_arm) or (k in OFF_ARM_ABSENT_KEYS and off_arm):
                    conditional.append(k)
                elif k in cond and not cond[k].startswith("<") and _get(doc, cond[k]) is False:
                    conditional.append(k)
                else:
                    missing.append(k)
        c["result_missing"], c["conditional_absent"] = missing, conditional
        npz = f / e["case"] / "controller_commands.npz"
        c["controller_commands_npz"] = npz.is_file()
        if npz.is_file():
            with np.load(npz, allow_pickle=False) as z:
                c["npz_arrays_ok"] = all(k in z.files and z[k].size > 0 for k in ("t_s", "issued_u_m_s"))
        c["series_files_missing"] = [n for n in SERIES_FILES if not (f / e["case"] / n).is_file()]
        c["ok"] = (c["progress_end_rc0"] and not c["batch_entry_missing"] and c["result_json"] and not missing
                   and c.get("npz_arrays_ok", False) and not c["series_files_missing"])
        cases.append(c)
    n_err = sum(1 for c in cases if not c["ok"]) + (0 if cases else 1)
    print(json.dumps({"folder": f.as_posix(), "batch": batch.get("batch"), "n_cases": len(cases),
                      "n_key_paths": len(keys), "cases": cases}, indent=1))
    print(f"errors {n_err}")
    return 0 if n_err == 0 else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="436.8 v5 resume Chrono rows (no simulation)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--out", default=None)
    m = sub.add_parser("manifest")
    m.add_argument("--out", required=True)
    s = sub.add_parser("c2-select")
    s.add_argument("h2")
    s.add_argument("--out", default=None)
    sub.add_parser("oc5-status")
    r = sub.add_parser("oc5-read")
    r.add_argument("folder")
    g = sub.add_parser("gs-check")
    g.add_argument("folder")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        return cmd_check(a.out)
    if a.cmd == "manifest":
        return cmd_manifest(a.out)
    if a.cmd == "c2-select":
        return cmd_c2_select(a.h2, a.out)
    if a.cmd == "oc5-status":
        return cmd_oc5_status()
    if a.cmd == "oc5-read":
        return cmd_oc5_read(a.folder)
    return cmd_gs_check(a.folder)


if __name__ == "__main__":
    raise SystemExit(main())
