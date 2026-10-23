"""Direct Chrono check of the nose-down 3.2 deg operating limit (dynamics_model.md 5.18.6, rev. 32 suppl. 4).

S6 L1-R (``OUTRIGGER_ROD_SIDE_MECHANICS=one_sided_parallel``), combined contact judge (G2-R
configuration), the installed C2 default (R7, H4 ``nose_down_only``, R6 stair), floor nose down
3.2 deg, rigid mast, seed 12345. Cases (5.18.6):

* ``C1_bottom_fdown3.2_sec``: bottom, pad tangential k_t = secant value of
  ``04_scripts/00_cad/leg_rod_lateral_check.py`` at the levelled extension of 3.2 deg (per leg),
  c_t proportional to sqrt(k_t), Chrono bushing damping input = c_t / 2 (rule kept);
* ``C2_top_fdown3.2_sec``: top, secant;
* ``C3_bottom_fdown3.2_yaml``: bottom, YAML k_t (link between the legs);
* ``C4_bottom_fdown3.2_sec_cr03``: bottom, secant, crawler tangential k_t x 0.3 (path sensitivity);
* ``C5_bottom_fdown3.5_yaml``: bottom, YAML, 3.5 deg = the bundle-B case G2-R_bottom_fdown3.5 with
  the current code (link to 5.18.3 / M1 effect; not part of the judgement).
* ``C6_bottom_fdown3.2_sec_cr3`` (5.19.6, rev. 32 suppl. 5): as C1 with crawler tangential k_t x 3
  (upper end of the declared range); ``C7_..._sec_cr15`` (x 1.5, monotonicity, optional) and
  ``C8_..._sec_cr22`` (x 2.2 = elastic-contact bound, the 5.19.2 fallback when C6 misses SF 1.5).
  Each variant settles its own crawler start snapshot (the K6 crawler-settlement map used by the
  start check is built for x 1 and is not re-derived here).

Overrides live only in this batch: ``load_params(overrides=...)`` of the pad bushing keys
``contact.rigid_floor.L1.bushing_stiffness_per_pad_N_m`` and ``bushing_damping_input_per_pad_N_s_m``
(the only pad keys the Chrono model reads, ``ground_bushing.GroundBushingCoulomb.for_legs``).
``kt_per_pad_N_m`` / ``ct_per_pad_N_s_m`` are left at the YAML values, so the crawler anchor
bushing (``crawler_bushing.crawler_bushing_values``: kt from the YAML pad kt/kn ratio) keeps its
YAML-derived value unless the case sets ``crawler_kt_scale``. The YAML file, 03_src and the
reference files are not changed. Every case writes ``override_identity`` into its result.json:
the requested overrides, ``Params.overrides`` and ``sha256`` as loaded, and the stiffness /
damping actually held by the pad and crawler bushing objects of the run model.

Snapshots: settled crawler start states are built per (level, floor, variant) into the batch's
own ``states`` folder (``s6_stage2.job_snapshot``, same procedure as the project snapshots);
the project ``07_results/states_L1R`` folder is only read (regression of the C5 snapshot).

Usage (Chrono-dev python, project root)::

    python -I -X utf8 -u 04_scripts/02_chrono/s6_fdown32_direct.py run [--jobs 5] [--only C1 ...]

Output: ``07_results/S6/fdown32_L1R_<stamp>/`` with ``batch_meta.json``, ``states/``,
``snapshots/`` (batch of the start states) and ``runs/`` (batch of the cases, same files as a
stage-2 case). Units SI.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import sys
from pathlib import Path

os.environ["OUTRIGGER_ROD_SIDE_MECHANICS"] = "one_sided_parallel"  # 5.18.6: L1-R on (children inherit)
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(HERE))

import s6_stage2  # noqa: E402
from outrigger_sim import params as _params_mod  # noqa: E402

RESULTS = ROOT / "07_results" / "S6"
PROJECT_STATES = ROOT / "07_results" / "states_L1R"
FLOOR_NAME = "fdown3.2"
s6_stage2.FLOORS[FLOOR_NAME] = (0.0, 3.2)  # floor nose down 3.2 deg (theta > 0 = nose down)
KT_KEY = "contact.rigid_floor.L1.bushing_stiffness_per_pad_N_m"
CT_KEY = "contact.rigid_floor.L1.bushing_damping_input_per_pad_N_s_m"
LEGS = ("FL", "FR", "RL", "RR")
SNAP_TIMEOUT_S = 1200.0
CASE_TIMEOUT_S = 2400.0

# --- per-process variant state (set by the job before any s6_stage2 call) -------------------
_VARIANT: dict = {"overrides": {}, "crawler_kt_scale": 1.0, "tag": "yaml"}
_LAST_MODEL: list = []
_orig_load_params = _params_mod.load_params
_orig_build = s6_stage2.build_crawler_model
_orig_snapshot_name = s6_stage2.snapshot_name


def _load_params(path=None, *, level=None, overrides=None):
    merged = {**_VARIANT["overrides"], **dict(overrides or {})}
    return _orig_load_params(path, level=level, overrides=merged or None)


def _build(params, floor, *, attach, settlement_legs=(), tangential=False, **kw):
    kw.setdefault("crawler_bushing_kt_scale", float(_VARIANT["crawler_kt_scale"]))
    model, pose = _orig_build(params, floor, attach=attach, settlement_legs=settlement_legs,
                              tangential=tangential, **kw)
    _LAST_MODEL[:] = [model]
    return model, pose


def _snapshot_name(level, floor, *, off=False):
    return _orig_snapshot_name(level, floor, off=off) + f"__{_VARIANT['tag']}"


_params_mod.load_params = _load_params
s6_stage2.build_crawler_model = _build
s6_stage2.snapshot_name = _snapshot_name


# --- case definitions --------------------------------------------------------------------------
def secant_kt_3p2() -> dict:
    """Secant pad k_t at the levelled extension of floor pitch +3.2 deg (leg_rod_lateral_check
    'ext' model: series(swivel leg bending at e, concrete)), N/m per leg."""
    sys.path.insert(0, str(ROOT / "04_scripts" / "00_cad"))
    import numpy as np

    import leg_rod_lateral_check as lr

    p = lr.load_params()
    geo = lr.leg_geometry(p)
    L1 = p["contact"]["rigid_floor"]["L1"]
    kt_yaml = np.array([float(L1["kt_per_pad_N_m"][n]) for n in LEGS])
    k_lat_yaml = np.array([float(L1["derivation"]["k_lateral_leg_swivel_N_m"][n]) for n in LEGS])
    k_conc = 1.0 / (1.0 / kt_yaml - 1.0 / k_lat_yaml)
    e = lr.levelling_extension(p, 0.0, 3.2)
    kb = np.array([lr.leg_case(geo[leg], p, float(e[i]), 1.0, 0.0, "swivel", 305e6)["k_lat_bending_N_m"]
                   for i, leg in enumerate(LEGS)])
    kt = 1.0 / (1.0 / kb + 1.0 / k_conc)
    ct_in_yaml = np.array([float(L1["bushing_damping_input_per_pad_N_s_m"][n]) for n in LEGS])
    ct_in = ct_in_yaml * np.sqrt(kt / kt_yaml)
    return {"levelled_extension_m": e.tolist(), "k_bending_N_m": kb.tolist(), "k_concrete_N_m": k_conc.tolist(),
            "kt_yaml_N_m": kt_yaml.tolist(), "kt_secant_N_m": kt.tolist(),
            "ct_input_yaml_N_s_m": ct_in_yaml.tolist(), "ct_input_secant_N_s_m": ct_in.tolist(),
            "rule": "kt = series(k_bending(e_3.2), k_concrete); ct = ct_yaml sqrt(kt/kt_yaml); Chrono "
                    "input = ct/2 (YAML bushing_damping_input = ct_per_pad/2, scaled by sqrt(kt/kt_yaml))"}


def variants(sec: dict) -> dict:
    kt = {n: float(v) for n, v in zip(LEGS, sec["kt_secant_N_m"], strict=True)}
    ct = {n: float(v) for n, v in zip(LEGS, sec["ct_input_secant_N_s_m"], strict=True)}
    sec_ov = {KT_KEY: kt, CT_KEY: ct}
    return {"sec": {"overrides": sec_ov, "crawler_kt_scale": 1.0},
            "yaml": {"overrides": {}, "crawler_kt_scale": 1.0},
            "sec_cr03": {"overrides": sec_ov, "crawler_kt_scale": 0.3},
            # 5.19.2 / 5.19.6 (rev. 32 suppl. 5): crawler tangential k_t upper bound (x3 declared range),
            # x1.5 for monotonicity, x2.2 = elastic-contact (Mindlin, nu 0.2) bound, fallback of 5.19.2
            "sec_cr15": {"overrides": sec_ov, "crawler_kt_scale": 1.5},
            "sec_cr22": {"overrides": sec_ov, "crawler_kt_scale": 2.2},
            "sec_cr3": {"overrides": sec_ov, "crawler_kt_scale": 3.0}}


CASES = {
    "C1": ("C1_bottom_fdown3.2_sec", "bottom", "fdown3.2", "sec"),
    "C2": ("C2_top_fdown3.2_sec", "top", "fdown3.2", "sec"),
    "C3": ("C3_bottom_fdown3.2_yaml", "bottom", "fdown3.2", "yaml"),
    "C4": ("C4_bottom_fdown3.2_sec_cr03", "bottom", "fdown3.2", "sec_cr03"),
    "C5": ("C5_bottom_fdown3.5_yaml", "bottom", "fdown3.5", "yaml"),
    # 5.19.6: crawler k_t upper bound (judgement condition of the 3.2 deg nose-down limit)
    "C6": ("C6_bottom_fdown3.2_sec_cr3", "bottom", "fdown3.2", "sec_cr3"),
    "C7": ("C7_bottom_fdown3.2_sec_cr15", "bottom", "fdown3.2", "sec_cr15"),   # optional, monotonicity
    "C8": ("C8_bottom_fdown3.2_sec_cr22", "bottom", "fdown3.2", "sec_cr22"),   # 5.19.2 fallback (x2.2)
}


def stage2_case(cid, level, floor):
    from dataclasses import replace

    c = s6_stage2.Stage2Case(cid, "D32", level, floor,
                             duration_s=s6_stage2._length(floor, h4=True, check_s=s6_stage2.CHECK_S),
                             items=("R",), notes=("dynamics_model.md 5.18.6 direct nose-down check",))
    return replace(c, duration_s=c.duration_s + s6_stage2.check_extra_s(c))


def _set_variant(settings: dict) -> None:
    _VARIANT.update(overrides=settings["overrides"], crawler_kt_scale=settings["crawler_kt_scale"],
                    tag=settings["tag"])


def _plain(o):
    import numpy as np

    if isinstance(o, dict):
        return {str(k): _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_plain(v) for v in o]
    if isinstance(o, np.ndarray):
        return _plain(o.tolist())
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    return str(o)


def identity(params, model, settings) -> dict:
    """Overrides requested vs loaded vs held by the bushing objects (rel. error)."""
    pads = model.bushing._pads
    held_kt = [float(p.stiffness_N_m) for p in pads]
    held_ct = [float(p.damping_input_N_s_m) for p in pads]
    want = settings["overrides"]
    exp_kt = [float(want[KT_KEY][n]) for n in LEGS] if KT_KEY in want else \
        [float(v) for v in params.get(KT_KEY).values()]
    exp_ct = [float(want[CT_KEY][n]) for n in LEGS] if CT_KEY in want else \
        [float(v) for v in params.get(CT_KEY).values()]
    cbv = model.crawler_bushing_values
    yaml_params = _orig_load_params(level=params.level)
    from outrigger_sim.chrono.crawler_bushing import crawler_bushing_values

    cr_ref = crawler_bushing_values(yaml_params, settings["crawler_kt_scale"])
    rel = lambda a, b: max(abs(x / y - 1.0) for x, y in zip(a, b, strict=True))  # noqa: E731
    out = {"variant": settings["tag"], "requested_overrides": want,
           "params_overrides_loaded": dict(params.overrides), "params_sha256": params.sha256,
           "yaml_params_sha256": yaml_params.sha256, "yaml_file_sha256": params.file_sha256,
           "pad_bushing_held": {"stiffness_N_m": held_kt, "damping_input_N_s_m": held_ct},
           "pad_bushing_expected": {"stiffness_N_m": exp_kt, "damping_input_N_s_m": exp_ct},
           "pad_rel_err_max": max(rel(held_kt, exp_kt), rel(held_ct, exp_ct)),
           "crawler_bushing_held": cbv.meta() if cbv is not None else None,
           "crawler_expected_kt_N_m": cr_ref.kt_N_m, "crawler_expected_ct_N_s_m": cr_ref.ct_N_s_m,
           "crawler_rel_err": None if cbv is None else max(abs(cbv.kt_N_m / cr_ref.kt_N_m - 1.0),
                                                           abs(cbv.ct_N_s_m / cr_ref.ct_N_s_m - 1.0)),
           "rod_side_mechanics": str(getattr(model.rod_chamber, "mechanics", None))}
    out["ok"] = bool(out["pad_rel_err_max"] <= 1e-12 and (out["crawler_rel_err"] or 0.0) <= 1e-12
                     and out["rod_side_mechanics"].endswith("one_sided_parallel"))
    return out


# --- jobs (module level for spawn) ----------------------------------------------------------
def job_snap(case, case_dir):
    from outrigger_sim.batch import CaseResult

    s = case.settings
    _set_variant(s)
    states = Path(s["states_dir"])
    summary = s6_stage2.job_snapshot(s["level"], s["floor"], Path(case_dir), states)
    model = _LAST_MODEL[0]
    params = _load_params(level=s["level"])
    summary["override_identity"] = identity(params, model, s)
    (Path(case_dir) / "result.json").write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False),
                                                encoding="utf-8")
    if not summary["override_identity"]["ok"]:
        raise RuntimeError(f"override identity failed: {summary['override_identity']}")
    return CaseResult(summary=_plain(summary), run_meta=None)


def job_case(case, case_dir):
    from outrigger_sim.batch import CaseResult

    s = case.settings
    _set_variant(s)
    c = stage2_case(case.case_id, s["level"], s["floor"])
    s6_stage2.all_cases = lambda: [c]  # job_stage2 looks the case up here
    summary, run_meta = s6_stage2.job_stage2(case.case_id, Path(case_dir), Path(s["states_dir"]))
    model = _LAST_MODEL[0]
    params = _load_params(level=s["level"])
    summary["override_identity"] = identity(params, model, s)
    (Path(case_dir) / "result.json").write_text(json.dumps(_plain(summary), indent=1, ensure_ascii=False),
                                                encoding="utf-8")
    if not summary["override_identity"]["ok"]:
        raise RuntimeError(f"override identity failed: {summary['override_identity']}")
    return CaseResult(summary=_plain(summary), run_meta=run_meta)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run", "plan"))
    ap.add_argument("--jobs", type=int, default=5)
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args(argv)
    from outrigger_sim.batch import Case, run_cases

    import l1r_variant

    sec = secant_kt_3p2()
    var = variants(sec)
    keys = a.only or list(CASES)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch = RESULTS / f"fdown32{l1r_variant.suffix()}_{stamp}"
    states = batch / "states"
    c2_meta = s6_stage2.default_c2_meta()
    snaps, runs = {}, []
    for k in keys:
        cid, level, floor, vname = CASES[k]
        settings = {**var[vname], "tag": vname, "level": level, "floor": floor, "states_dir": str(states)}
        sname = _orig_snapshot_name(level, floor) + f"__{vname}"
        snaps.setdefault(sname, settings)
        runs.append(Case(cid, settings))
    meta = {"spec": "dynamics_model.md 5.18.6 (rev. 32 suppl. 4); C6-C8: 5.19.2 / 5.19.6 (suppl. 5)", "c2": c2_meta, "l1r": l1r_variant.meta(),
            "secant_kt_3p2": sec, "variants": var, "cases": {r.case_id: r.settings for r in runs},
            "snapshots": list(snaps), "floor_slope_deg": {"fdown3.2": [0.0, 3.2], "fdown3.5": [0.0, 3.5]},
            "notes": ["kt_per_pad_N_m / ct_per_pad_N_s_m not overridden: crawler bushing keeps its YAML "
                      "derivation (kt/kn pad ratio of the YAML) unless crawler_kt_scale != 1",
                      "YAML, 03_src and reference files unchanged; overrides only in this batch"]}
    print(json.dumps({"batch": str(batch), "cases": [r.case_id for r in runs], "snapshots": list(snaps),
                      "kt_secant": sec["kt_secant_N_m"], "ct_in_secant": sec["ct_input_secant_N_s_m"],
                      "c2": c2_meta}, indent=1), flush=True)
    if a.cmd == "plan":
        return
    if c2_meta.get("reanchor_direction") != "nose_down_only":
        raise SystemExit(f"C2 REANCHOR direction {c2_meta.get('reanchor_direction')!r} != nose_down_only")
    batch.mkdir(parents=True, exist_ok=False)
    states.mkdir()
    (batch / "batch_meta.json").write_text(json.dumps(_plain(meta), indent=1), encoding="utf-8")
    t0 = _dt.datetime.now()
    rep = run_cases([Case(n, s) for n, s in snaps.items()], job_snap, batch / "snapshots",
                    max_workers=a.jobs, placement="pcore", timeout_s=SNAP_TIMEOUT_S)
    for o in rep.outcomes:
        print(f"snapshot {o.case_id}: {o.status} {o.wall_s:.1f}s {(o.error or '')[-1500:]}", flush=True)
    if any(o.status != "ok" for o in rep.outcomes):
        raise SystemExit("snapshot failed")
    rep = run_cases(runs, job_case, batch / "runs", max_workers=a.jobs, placement="pcore",
                    timeout_s=CASE_TIMEOUT_S)
    for o in rep.outcomes:
        print(f"case {o.case_id}: {o.status} {o.wall_s:.1f}s {(o.error or '')[-1500:]}", flush=True)
    print(f"done in {(_dt.datetime.now() - t0).total_seconds():.0f} s -> {batch}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
