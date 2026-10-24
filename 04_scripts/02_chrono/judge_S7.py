"""S7 judgement: read a ``run_S7.py run`` batch and apply ``outrigger_sim.verify.s7``.

``00_docs/03_chrono/chrono_build_plan.md`` S7; ``dynamics_model.md`` rev. 33 5.20. Usage (any env
with numpy / scipy / pyyaml / matplotlib; dynamics-dev or Chrono-dev; no pychrono needed)::

    python -I -X utf8 judge_S7.py [--run 07_results/S7/run_<stamp>] [--extra-run <batch> ...]
                                   [--out <json>] [--no-figures]

Default run = the newest ``07_results/S7/run_*``. Output ``06_analysis/01_chrono/17_S7/
verify_S7_L2b.json`` (checks, per-V summary, extracted numbers) and figures
``verify_S7_L2b_V14.png``, ``verify_S7_L2b_modes.png``, ``verify_S7_L2b_V11b_V4.png``.
Missing cases are reported as ``missing`` (their V is not judged). Units SI; angles in deg where
named.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))

from outrigger_sim.verify import s7  # noqa: E402
from outrigger_sim.verify.checks import CheckResult, check_max  # noqa: E402

RESULTS = ROOT / "07_results" / "S7"
OUT_DIR = ROOT / "06_analysis" / "01_chrono" / "17_S7"
REFS_FILE = ROOT / "06_analysis" / "00_dynamics" / "reference.json"
LEVELS = ("top", "middle", "bottom")
V14_TAGS = {"flat": "level", "pitchp": "max pitch+", "rollp": "max roll+", "diag": "max diag 45"}
WINDOW_S = 0.1
ERA_ORDER = 24
ERA_ORDER_CHECK = 32
ERA_BLOCK_ROWS = 40
ERA_DECIMATE = 5
SHORT_WINDOW_S = 2.0
LONG_MODES = (0, 1)
BASELINE_S = 0.05
"""Pre-move baseline: mean of the first 50 ms (the move ramp has travelled < 1e-8 m; a single
sample carries the PSOR noise of the law output, std 18 / 37 / 77 / 159 N at 1e-4 / 5e-5 /
2.5e-5 / 1e-5 s, S7 batch 2026-10-24)."""
TRANSIENT_WINDOW = 20
"""V9 transient extreme on 20-sample (20 ms) centred means: the same linear filter for every dt
(2 Hz attenuation 0.03 %), removes the dt-dependent PSOR noise from the extreme."""
LIFT_COMMAND_START_S = 1.0
"""``run_S7._job_lift``: 1 s on the crawler, then the lift command (plan times = command time)."""
SATURATION_STOP_S = 2.0e-3
"""``actuation.SATURATION_STOP_S`` (law C, 2 ms); repeated here so the judge needs no pychrono."""
V9_ID = re.compile(r"^V9(?:s_([A-Za-z0-9]+))?_FLp1_dt([0-9.eE+-]+)$")
"""V9 case ids: base batch ``V9_FLp1_dt<dt>``, V9 (b) sensitivity ``V9s_<setting>_FLp1_dt<dt>``
(``run_S7.py`` ``V9S_VARIANTS``: psor100, rec005; dynamics_model.md 5.22.3)."""
V9_BASE = "base"
V9_DTS = (1.0e-4, 5.0e-5, 2.5e-5, 1.0e-5)
V9_STILL_S = 5.0
"""Still window (last 5 s of the 10 s settle) for the PSOR noise record of V9 (b)."""
V9_RECORD_SHARE = 0.3
"""V9 (a) record rule: every coarse dt within 30 % of the 1 % transient tolerance of the reference
dt (5.22.3, user decision 2026-10-24)."""
REPLICA_FILE = ROOT / "06_analysis" / "00_dynamics" / "v9_semi_implicit_replica.json"


class Case:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.id = path.name
        self.case = json.loads((path / "case.json").read_text(encoding="utf-8"))
        self.result = json.loads((path / "result.json").read_text(encoding="utf-8"))

    def npz(self, name: str = "series.npz") -> dict[str, np.ndarray]:
        z = np.load(self.path / name)
        return {k: z[k] for k in z.files}

    @property
    def settings(self) -> dict[str, Any]:
        return self.case["settings"]


def _load(run: Path) -> tuple[dict[str, Case], list[str]]:
    cases, missing = {}, []
    for d in sorted(p for p in run.iterdir() if p.is_dir()):
        if (d / "result.json").exists() and (d / "case.json").exists():
            c = Case(d)
            if c.case.get("runner", {}).get("status") == "ok":
                cases[c.id] = c
                continue
        missing.append(d.name)
    return cases, missing


def _rows(checks: list[CheckResult]) -> list[dict[str, Any]]:
    return [c.as_dict() for c in checks]


def _window(dt_sample: float) -> int:
    return max(1, round(WINDOW_S / dt_sample))


def _dt_sample(t: np.ndarray) -> float:
    return float(np.median(np.diff(t)))


# --- pre-checks ---------------------------------------------------------------------------------


def pre_checks(c: Case, lp: s7.LegParameters, ref_ext: list[float] | None,
               series: dict[str, np.ndarray] | None, extra_bound_m=None) -> list[CheckResult]:
    out: list[CheckResult] = []
    r = c.result
    if "piston_monitor" in r:
        out += s7.piston_checks(c.id, r["piston_monitor"])
    table = r.get("rod_side_lock_table")
    if table is None or series is None:
        return out
    u_last = np.abs(series["u_applied_m_s"][-1])
    locked = [i for i in range(4) if u_last[i] <= 1e-6 and table["locked"][i]]
    if not locked:
        return out
    s_ref_last = series["s_ref_m"][-1]
    out += s7.lock_table_checks(c.id, table, s_ref_at_lock_m=s_ref_last, ref_extensions_m=ref_ext,
                                leg_params=lp, locked_legs=locked,
                                key=f"{s7.REF} / V14 or k_of_s_table e_op",
                                extra_bound_m=extra_bound_m)
    return out


# --- modal identification ------------------------------------------------------------------------


def identify(t: np.ndarray, q: np.ndarray, *, phi: np.ndarray | None, mm: np.ndarray,
             f_ref: list[float], window_s: float, all_long: bool = False
             ) -> tuple[list[s7.ModeId], list[dict[str, Any]], np.ndarray | None]:
    """Projection fit (when ``phi``) + ERA (24 / 32) per mode; judged value by the S4 rule."""
    from outrigger_sim.verify.metrics import (
        era_free_decay,
        fit_damped_sine,
        modal_coordinates,
        select_era_mode,
    )
    from outrigger_sim.verify.s4 import ModeRow, judged_value

    scale = np.sqrt(np.diag(mm))
    t = t - t[0]
    eras: dict[str, Any] = {}
    for label, win in (("long", window_s), ("short", min(window_s, SHORT_WINDOW_S))):
        m = t <= win + 1e-9
        eras[label] = era_free_decay(t[m], q[m], order=ERA_ORDER, n_block_rows=ERA_BLOCK_ROWS,
                                     decimate=ERA_DECIMATE, channel_scale=scale)
    eta = None if phi is None else modal_coordinates(q, phi, mm)
    rows, details = [], []
    for i in range(6):
        long_ = all_long or i in LONG_MODES
        win = window_s if long_ else min(window_s, SHORT_WINDOW_S)
        era = eras["long" if long_ else "short"]
        mask = t <= win + 1e-9
        f_era = z_era = None
        if phi is not None:
            k = select_era_mode(era, i, phi, mm, float(f_ref[i]), f_band_rel=0.15)
        else:
            cands = [(abs(md.f_undamped_Hz / f_ref[i] - 1.0), j) for j, md in enumerate(era.modes)
                     if abs(md.f_undamped_Hz / f_ref[i] - 1.0) <= 0.15]
            k = min(cands)[1] if cands else None
        if k is not None:
            f_era, z_era = float(era.modes[k].f_undamped_Hz), float(era.modes[k].zeta)
        det: dict[str, Any] = {"mode": i + 1, "window_s": win, "f_ref_Hz": float(f_ref[i]),
                               "era_f_Hz": f_era, "era_zeta": z_era}
        if phi is not None:
            fit = fit_damped_sine(t[mask], eta[mask, i], float(f_ref[i]))
            det.update(f_proj_Hz=fit.f_undamped_Hz, zeta_proj=fit.zeta,
                       fit_residual=fit.residual_rms_rel, amplitude=fit.amplitude)
            row = ModeRow(mode=i + 1, run="", f_proj_Hz=fit.f_undamped_Hz, zeta_proj=fit.zeta,
                          fit_residual_rms_rel=fit.residual_rms_rel, f_era_Hz=f_era,
                          zeta_era=z_era, leakage=None, zeta_num=0.0, f_ref_Hz=float(f_ref[i]),
                          zeta_ref=math.nan)
            j = judged_value(row)
            rows.append(s7.ModeId(i + 1, j.f_Hz, j.zeta, j.source, j.reason))
        else:
            rows.append(s7.ModeId(i + 1, math.nan if f_era is None else f_era,
                                  math.nan if z_era is None else z_era, "ERA",
                                  "nearest ERA pole within 15 % (no mode shapes for this case)"))
        details.append(det)
    return rows, details, eta


def _modal_series(c: Case, name: str, point: list[float]) -> tuple[np.ndarray, np.ndarray]:
    z = c.npz(name)
    kick = c.result.get("kick", {}).get("t_s")
    q = s7.modal_q(z["t_s"], z["body_pos_m"], z["body_vel_m_s"], z["body_omega_rad_s"], point,
                   z["pad_centre_world_m"][:, :, 2], t_kick=kick)
    # integrated roll / pitch vs the recorded attitude (consistency, rad)
    rp = np.radians(z["roll_pitch_deg"] - z["roll_pitch_deg"][0])
    q_check = float(np.abs(q[:, 3:5] - q[0, 3:5] - rp).max())
    return z["t_s"], np.hstack([q, np.full((len(q), 1), q_check)])


# --- V9 -------------------------------------------------------------------------------------------


def _v9_setting(case_id: str) -> tuple[str, float] | None:
    """``(setting, dt)`` of a V9 case id: ``V9_FLp1_dt<dt>`` -> base, ``V9s_<tag>_FLp1_dt<dt>``."""
    m = V9_ID.match(case_id)
    if m is None:
        return None
    return (m.group(1) or V9_BASE), float(m.group(2))


def _v9_numbers(c: Case, tail: float) -> dict[str, Any]:
    z = c.npz()
    t = z["t_s"]
    last = t >= t[-1] - tail
    base = t <= t[0] + BASELINE_S
    _, f_rl = s7.centred_moving_mean(t, z["cylinder_force_N"][:, 2], TRANSIENT_WINDOW)
    still = t >= t[-1] - V9_STILL_S
    out: dict[str, Any] = {
        "final_F": z["cylinder_force_N"][last].mean(axis=0),
        "final_att": z["roll_pitch_deg"][last].mean(axis=0),
        "transient": float((f_rl - z["cylinder_force_N"][base, 2].mean()).min()),
    }
    # PSOR noise record (5.22.3 (b)): high-pass std = y - 20-sample centred mean, still window
    for key, name in (("cylinder_force_N", "law_F_hp20_std_N"),
                      ("pad_normal_N", "contact_hp20_std_N")):
        if key not in z:
            continue
        y = z[key][still]
        _, ym = s7.centred_moving_mean(t[still], y, TRANSIENT_WINDOW)
        h = TRANSIENT_WINDOW // 2
        n = len(ym)
        out[name] = (y[h:h + n] - ym).std(axis=0).tolist() if n > 0 else None
    override = c.result.get("solver_override") or c.settings.get("solver_override")
    out["solver_override"] = override
    return out


def _v9_record_rule(cs: list[CheckResult], transient: dict[float, float], ref_dt: float
                    ) -> list[CheckResult]:
    """V9 (a) record rule (dynamics_model.md 5.22.3, user decision 2026-10-24 after V9 (b)).

    When the error-ratio row fails but every coarse dt is within V9_RECORD_SHARE x the V9 transient
    tolerance of the reference dt (the differences are PSOR noise, not dt error), the ratio row is
    kept as ``info`` (recorded) and replaced by two V9 rows: the noise-level bound itself and the
    first-order ratio of the semi-implicit Euler replica of the same laws
    (``v9_semi_implicit_replica.json``)."""
    ratio = [c for c in cs if c.item.startswith("error ratio")]
    if not ratio or ratio[0].passed:
        return cs
    ref_val = transient[ref_dt]
    devs = np.array([transient[d] - ref_val for d in transient if d != ref_dt])
    bound = V9_RECORD_SHARE * s7.V9_TRANSIENT_REL * abs(ref_val)
    if not np.all(np.abs(devs) <= bound):
        return cs
    out = [c for c in cs if c is not ratio[0]]
    r0 = ratio[0]
    out.append(CheckResult("info", r0.item + " (recorded, V9 (a) record rule)", r0.value, r0.ref,
                           r0.tol, r0.tol_kind, r0.unit, r0.passed, note=r0.note))
    out.append(check_max("V9", f"(a) record rule: |transient(dt) - transient({ref_dt:g})| <= "
                         f"{V9_RECORD_SHARE:g} x {s7.V9_TRANSIENT_REL:g} x |ref| (noise level)",
                         np.abs(devs), bound, "N", note=f"deviations {devs.tolist()}"))
    rep = REPLICA_FILE
    if rep.exists():
        rj = json.loads(rep.read_text(encoding="utf-8"))
        rr = float(rj["error_ratio (1e-4/5e-5/2.5e-5)"])
        out.append(CheckResult(
            "V9", "(a) first-order dt convergence of the replica (semi-implicit Euler, same laws, "
            "1-step input lag), ratio 1e-4/5e-5/2.5e-5", rr, s7.V9_RATIO, s7.V9_RATIO_REL, "rel",
            "1", bool(abs(rr - s7.V9_RATIO) <= s7.V9_RATIO_REL * s7.V9_RATIO),
            ref_key=str(rep.relative_to(ROOT)),
            note=f"replica dt error at 1e-4 s {rj['error_vs_richardson_N']['0.0001']:.3e} N"))
    else:
        out.append(CheckResult("V9", "(a) replica file present", False, True, None, "equal", "-",
                               False, ref_key=str(rep.relative_to(ROOT))))
    return out


def _v9(cases: dict[str, Case], tail: float, w_total: float
        ) -> tuple[list[CheckResult], dict[str, Any]]:
    """V9 per solver setting. Base only: ids ``V9`` as before. With ``V9s_*`` cases (5.22.3 (b)):
    each setting is judged on its own 1e-5 s run under id ``V9[<setting>]`` and ``V9`` passes when
    at least one setting passes every one of its V9 checks."""
    by_setting: dict[str, dict[float, dict[str, Any]]] = {}
    for cid, c in cases.items():
        key = _v9_setting(cid)
        if key is None:
            continue
        by_setting.setdefault(key[0], {})[key[1]] = _v9_numbers(c, tail)
    checks: list[CheckResult] = []
    numbers: dict[str, Any] = {}
    variants = sorted(k for k in by_setting if k != V9_BASE)
    passed_settings, judged = [], []
    for setting in [V9_BASE, *variants]:
        rows = by_setting.get(setting, {})
        ref_dt = min(V9_DTS)
        if not any(abs(d - ref_dt) <= 1e-12 for d in rows) or len(rows) < 2:
            continue
        rows = {min(V9_DTS, key=lambda x, d=d: abs(x - d)): v for d, v in rows.items()}
        cs = s7.v9_checks(final_force_N={d: v["final_F"] for d, v in rows.items()},
                          final_att_deg={d: v["final_att"] for d, v in rows.items()},
                          transient_N={d: v["transient"] for d, v in rows.items()},
                          ref_dt_s=ref_dt, w_total_N=w_total)
        cs = _v9_record_rule(cs, {d: v["transient"] for d, v in rows.items()}, ref_dt)
        if variants:
            cs = [CheckResult(x.id if x.id == "info" else f"V9[{setting}]",
                              *[getattr(x, f) for f in (
                "item", "value", "ref", "tol", "tol_kind", "unit", "passed", "ref_key",
                "deviation", "note")]) for x in cs]
        checks += cs
        judged.append(setting)
        complete = len(rows) == len(V9_DTS)
        if complete and all(x.passed for x in cs if x.id != "info"):
            passed_settings.append(setting)
        numbers["V9" if setting == V9_BASE else f"V9[{setting}]"] = {
            f"{k:g}": {"final_F_N": v["final_F"].tolist(), "final_att_deg": v["final_att"].tolist(),
                       "transient_RL_dF_min_N": v["transient"],
                       "law_F_hp20_std_N (still window)": v.get("law_F_hp20_std_N"),
                       "contact_hp20_std_N (still window)": v.get("contact_hp20_std_N"),
                       "solver_override": v["solver_override"]}
            for k, v in sorted(rows.items(), reverse=True)}
    if variants:
        checks.append(CheckResult(
            "V9", "at least one solver setting passes every V9 check, all 4 dt "
            "(dynamics_model.md 5.22.3 (a) record rule, (b) settings)", passed_settings, judged,
            None, "any", "-", bool(passed_settings),
            note=f"settings judged {judged}; incomplete settings (missing dt) cannot pass"))
    return checks, numbers


# --- main judgement -------------------------------------------------------------------------------


def judge(run: Path, extra_runs: list[Path] | None = None) -> dict[str, Any]:
    from outrigger_sim.params import load_params

    refs_all = json.loads(REFS_FILE.read_text(encoding="utf-8"))
    ref = refs_all[s7.REF_BLOCK]
    lp = s7.LegParameters.from_block(ref)
    cases, missing = _load(run)
    for extra in extra_runs or []:
        # extra batches add cases (V9 (b) sensitivity, 5.22.3); an id already present is an error
        ex, ex_missing = _load(extra)
        clash = sorted(set(ex) & set(cases))
        if clash:
            raise SystemExit(f"--extra-run {extra}: case ids already loaded {clash}")
        cases.update(ex)
        missing += [f"{extra.name}/{m}" for m in ex_missing]
    checks: list[CheckResult] = []
    numbers: dict[str, Any] = {"missing_or_failed_cases": missing}
    params = load_params(level="top", model="L2b_NSC")
    g = params.meta.gravity_m_s2
    rod_m = np.array([leg.moving_part.mass_kg for leg in params.legs])
    radius = np.array([leg.pad.swivel_center_above_pad_bottom_m for leg in params.legs])
    v_max = params.actuator.max_speed_m_s
    w_total = float(ref["levels"]["top"]["W_total_N"])
    f_min = float(ref["levels"]["top"]["F_min_cylinder_N"])
    e_op = ref["leg_parameters"]["k_of_s_table"]["e_op"]["s_m"]
    pad_xy = np.array([leg.attachment_point_m[:2] for leg in params.legs], float)

    # pre-checks and V13 health on every case
    nonfinite = {}
    for cid, c in cases.items():
        series_name = next((n for n in ("series_creep.npz", "series_modes.npz", "series.npz",
                                        "series_still.npz", "series_v11.npz")
                            if (c.path / n).exists()), None)
        z = c.npz(series_name) if series_name else None
        ref_ext = extra = None
        if cid.startswith("V14_"):
            rc = ref["V14"]["cases"][V14_TAGS[cid.split("_")[1]]]
            ref_ext = rc["extension_m"]
            extra = s7.slope_rounding_bound_m(rc["ground_roll_pitch_deg"], pad_xy)
        elif c.settings.get("kind") in ("settle", "impulse", "lift"):
            ref_ext = e_op  # legs locked at the operating extension (moving legs: own s_ref only)
        armed = (c.settings.get("kind") != "slope"
                 or bool(c.settings.get("arm_rod_side_after_settle")))
        checks += pre_checks(c, lp, ref_ext, z if armed else None, extra)
        nf = 0
        for f in c.path.glob("series*.npz"):  # snapshot payloads hold NaN sentinels
            zz = np.load(f)
            nf += sum(int(np.count_nonzero(~np.isfinite(zz[k]))) for k in zz.files
                      if zz[k].dtype.kind == "f")
        nonfinite[cid] = nf
    checks.append(check_max("V13", "non-finite values in every stored series (all cases)",
                            float(sum(nonfinite.values())), 0.0, "-",
                            note=f"{len(cases)} cases"))

    # V0 + V1/V2/V3/V13 + V10 loads
    settle_contact = {}
    for lv in LEVELS:
        c = cases.get(f"settle_{lv}")
        if c is None:
            continue
        p = load_params(level=lv, model="L2b_NSC")
        mp = p.superstructure.mass_properties
        checks += s7.v0_checks(c.result["inventory_V0"], gravity_m_s2=(0.0, 0.0, -g),
                               sup_mass_kg=mp.mass_kg, sup_com_m=mp.com_m,
                               sup_inertia=mp.inertia_kg_m2, rod_masses_kg=rod_m, level=lv)
        still = c.result["still"]
        key = f"{s7.REF} / levels / {lv}"
        checks += s7.settle_checks(lv, still, ref["levels"][lv], key=key)
        settle_contact[lv] = still["pad_normal_mean_N"]
        cross = c.result.get("crosscheck", [])
        if cross:
            body = np.array([x["get_contact_force_N"] for x in cross])
            bal = np.array([x["axial_balance_N"] for x in cross])
            rep = max(x["max_abs_body_minus_report_N"] for x in cross)
            checks.append(check_max("info", f"{lv}: risk 5 GetContactForce vs ReportAllContacts "
                                    "(max over 0.1 s samples)", rep, 1e-9, "N"))
            checks.append(check_max("info", f"{lv}: risk 5 mean(body - rod axial balance) per leg "
                                    "(0.1 s samples)", np.abs((body - bal).mean(axis=0)),
                                    s7.V13_W4 * w_total / 4, "N"))
        numbers[f"settle_{lv}"] = {k: still[k] for k in (
            "pad_normal_mean_N", "cylinder_force_mean_N", "axial_spring_compression_mm",
            "roll_pitch_mean_deg", "pad_normal_window_span_N", "pad_normal_step_std_N",
            "cylinder_force_step_std_N", "cylinder_force_window_span_N", "roll_pitch_span_deg")}
    if settle_contact:
        checks += s7.v10_load_checks(settle_contact, {lv: ref["levels"][lv]["contact_force_N (V1)"]
                                                       for lv in settle_contact}, w_total)

    # V0 sign (air)
    c = cases.get("V11_air")
    if c is not None:
        z = c.npz("series_sign.npz")
        k_end = int(np.searchsorted(z["t_s"], z["t_s"][0] + 1.2 - 1e-6))
        dz = z["pad_centre_world_m"][-1, :, 2] - z["pad_centre_world_m"][0, :, 2]
        ds = z["motor_pos_m"][-1] - z["motor_pos_m"][0]
        # hanging force at rest: mean of the last 0.05 s of the 0.2 s hold (the first sample is
        # already inside the command ramp, F = -m g + m a)
        rest = z["t_s"] >= z["t_s"][-1] - 0.05
        hang = z["cylinder_force_N"][rest].mean(axis=0)
        checks += s7.v0_sign_checks(dz, ds, hang, rod_m * g)
        numbers["V0_sign"] = {"pad_dz_m": dz.tolist(), "motor_ds_m": ds.tolist(),
                              "hanging_force_rest_N": hang.tolist(),
                              "first_sample_force_N": z["cylinder_force_N"][0].tolist(),
                              "k_end": k_end}
        checks += _v11(c, params, v_max, numbers)

    # V5
    l1r = refs_all["L1R_rod_side_reference_rev32"]["V5_V6_quasi_static"]["top"][
        "L1R (FL moving, others LOCK)"]
    f1_top = ref["levels"]["top"]["modes"]["LOCK"]["f_damped_Hz (first 6)"][0]
    tail = 3.0 / f1_top
    for mm in (1, 5):
        c = cases.get(f"V5_FL_p{mm}mm")
        if c is None:
            continue
        z = c.npz()
        last = z["t_s"] >= z["t_s"][-1] - tail
        base = z["t_s"] <= z["t_s"][0] + BASELINE_S
        st = cases.get("settle_top")
        if st is not None:
            # settled equilibrium of the same model and start (the V5 run moves 1 s after the
            # analytic start, whose rocking transient decays with tau_1 ~ 9 s)
            f_base = np.asarray(st.result["still"]["cylinder_force_mean_N"], float)
            a_base = np.asarray(st.result["still"]["roll_pitch_mean_deg"], float)
        else:
            f_base = z["cylinder_force_N"][base].mean(axis=0)
            a_base = z["roll_pitch_deg"][base].mean(axis=0)
        dF = z["cylinder_force_N"][last].mean(axis=0) - f_base
        datt = z["roll_pitch_deg"][last].mean(axis=0) - a_base
        dF_first = (z["cylinder_force_N"][last].mean(axis=0)
                    - z["cylinder_force_N"][base].mean(axis=0))
        r5 = l1r[f"FL +{mm} mm"]
        checks += s7.v5_checks(mm, dF_N=dF, dF_ref_N=r5["dF_N"], datt_deg=datt,
                               datt_ref_deg=[r5["droll_deg"], r5["dpitch_deg"]],
                               key="reference.json / L1R_rod_side_reference_rev32 / "
                                   f"V5_V6_quasi_static / top / L1R (FL moving, others LOCK) / "
                                   f"FL +{mm} mm")
        numbers[f"V5_FL_p{mm}mm"] = {"dF_N": dF.tolist(), "datt_deg": datt.tolist(),
                                     "dF_vs_first_50ms_N (record)": dF_first.tolist(),
                                     "ref_dF_N": r5["dF_N"]}

    # V6
    thr = ref["levels"]["top"]["single_leg_thresholds_mm (V5 / V6 / V14 level)"]
    for tag, test, leg, sign in (("FLp", "FL+", 0, 1), ("RLp", "RL+", 2, 1),
                                 ("RLm", "RL-", 2, -1)):
        c = cases.get(f"V6_{tag}")
        if c is None:
            continue
        z = c.npz()
        trav = sign * (z["s_ref_m"][:, leg] - z["s_ref_m"][0, leg])
        res = s7.creep_thresholds(z["t_s"], trav, z["cylinder_force_N"], z["pad_normal_N"],
                                  f_min, window=_window(_dt_sample(z["t_s"])),
                                  exclude_leg=leg if sign > 0 else None)
        rr = thr[test]["L1R_after_extend"]
        checks += s7.threshold_checks("V6", test, res, f_min_ref=rr["F_min_mm"],
                                      liftoff_ref=rr["liftoff_mm"],
                                      key=f"{s7.REF} / levels / top / single_leg_thresholds_mm / "
                                          f"{test} / L1R_after_extend")
        numbers[f"V6_{tag}"] = res.__dict__

    # V7 + V10 modes
    f_by_level: dict[str, list[float]] = {}
    modal_numbers: dict[str, Any] = {}
    etas: dict[str, Any] = {}
    for lv in LEVELS:
        c = cases.get(f"V7_{lv}")
        if c is None:
            continue
        lock = ref["levels"][lv]["modes"]["LOCK"]
        shapes = lock["mode_shapes"]
        phi = np.asarray(shapes["Phi (rows = coordinates, cols = first 6 modes)"], float)
        mm_ = np.asarray(shapes["mass_matrix"], float)
        t, qx = _modal_series(c, "series.npz", shapes["reference_point_m (superstructure CoM)"])
        q, qchk = qx[:, :10], float(qx[0, 10])
        win = float(t[-1] - t[0])
        rows, det, eta = identify(t, q, phi=phi, mm=mm_, f_ref=lock["f_damped_Hz (first 6)"],
                                  window_s=win)
        key = f"{s7.REF} / levels / {lv} / modes / LOCK"
        checks += s7.mode_checks("V7", f"V7 {lv}", rows, f_ref_Hz=lock["f_damped_Hz (first 6)"],
                                 zeta_ref=lock["zeta (first 6)"], key_f=key + " / f_damped_Hz",
                                 key_zeta=key + " / zeta")
        checks.append(check_max("info", f"V7 {lv}: integrated roll/pitch vs recorded attitude",
                                qchk, 1e-7, "rad"))
        f_by_level[lv] = [r.f_Hz for r in rows]
        modal_numbers[f"V7_{lv}"] = {"judged": [r.__dict__ for r in rows], "detail": det}
        etas[f"V7_{lv}"] = (t - t[0], eta)
        if lv in ("top", "middle", "bottom"):
            checks += s7.mode_checks("V10", f"V10 {lv}", rows[:2],
                                     f_ref_Hz=lock["f_damped_Hz (first 6)"], zeta_ref=None,
                                     key_f=key + " / f_damped_Hz")
    if len(f_by_level) == 3:
        checks += s7.v10_order_checks(f_by_level)

    # V8(a)
    lock = ref["levels"]["top"]["modes"]["LOCK"]
    shapes = lock["mode_shapes"]
    phi = np.asarray(shapes["Phi (rows = coordinates, cols = first 6 modes)"], float)
    mm_ = np.asarray(shapes["mass_matrix"], float)
    for dt in (1.0e-4, 2.0e-4):
        c = cases.get(f"V8a_top_dt{dt:.0e}")
        if c is None:
            continue
        meta_act = c.case["run_meta"].get("engine", {}).get("actuator", {})
        lat = c.case["run_meta"].get("engine", {}).get("lateral_bushing", {})
        t, qx = _modal_series(c, "series.npz", shapes["reference_point_m (superstructure CoM)"])
        q = qx[:, :10]
        rows, det, eta = identify(t, q, phi=phi, mm=mm_, f_ref=lock["f_damped_Hz (first 6)"],
                                  window_s=float(t[-1] - t[0]), all_long=True)
        growth = [s7.envelope_ratio(t, eta[:, i]) for i in range(6)]
        checks += s7.v8a_checks(dt, rows, growth, lock["zeta (first 6)"],
                                key=f"{s7.REF} / levels / top / modes / LOCK / zeta")
        damp = {"axial_locked": meta_act.get("damping_locked_N_s_m"),
                "axial_moving": meta_act.get("damping_moving_N_s_m"),
                "lateral": lat.get("damping_actual_N_s_m")}
        flat = [v for vals in damp.values() if vals is not None for v in vals]
        checks.append(check_max("V8a", f"dt {dt:g} s: every dashpot 0 (axial locked / moving, "
                                "lateral; cad assumption)", float(np.max(np.abs(flat)))
                                if flat else math.nan, 0.0, "N s/m", note=json.dumps(damp)))
        modal_numbers[f"V8a_{dt:g}"] = {"judged": [r.__dict__ for r in rows], "growth": growth,
                                        "detail": det, "damping": damp}
        etas[f"V8a_{dt:g}"] = (t - t[0], eta)

    # V9 (+ V9 (b) solver settings from --extra-run, 5.22.3)
    v9_checks_all, v9_numbers = _v9(cases, tail, w_total)
    checks += v9_checks_all
    numbers.update(v9_numbers)

    # V11b
    sat = ref["leg_parameters"]["saturation_moving_210bar"]
    c_mov = ref["leg_parameters"]["c_oil_moving_N_s_m (zeta 0.10 on k2(e_op), concrete in series)"]
    k2e = ref["leg_parameters"]["k_of_s_table"]["e_op"]["k2_axial_head_only_N_m (moving)"]
    v11b_series = {}
    for leg in ("FL", "RL"):
        c = cases.get(f"V11b_{leg}")
        if c is None:
            continue
        i = s7.LEGS.index(leg)
        z = c.npz()
        bounds = np.cumsum([0.0] + [p[0] for p in c.result["phases_s_cmd"]])
        exp = s7.v11b_expected_dF(c_mov[i], k2e[i], v_max, SATURATION_STOP_S)
        for ph, direction, lim in ((0, 1, sat["extend_N (A_p)"][i]),
                                   (2, -1, sat["retract_N (A_ann)"][i])):
            phase = s7.v11b_phase(z["t_s"], z["force_N"], z["s_ref_m"], z["saturated"],
                                  z["motor_pos_m"], t0=bounds[ph], t1=bounds[ph + 1],
                                  direction=direction, k2_N_m=k2e[i])
            dt_run = float(np.median(np.diff(z["t_s"])))
            bound = s7.v11b_creep_bound_m(c_mov[i], k2e[i], v_max, dt_run)
            checks += s7.v11b_checks(leg, phase, limit_N=lim, expected_dF_N=exp,
                                     key=f"{s7.REF} / leg_parameters / saturation_moving_210bar",
                                     creep_bound_m=bound)
            sat_starts = int(np.count_nonzero(np.diff(np.asarray(z["saturated"], int)) == 1))
            checks.append(check_max("info", f"{leg}: law C saturation re-arm count (whole run, "
                                    "record)", float(sat_starts), math.inf, "-"))
            numbers[f"V11b_{leg}_{'ext' if direction > 0 else 'ret'}"] = phase.__dict__
        v11b_series[leg] = z

    # V12
    for cid in sorted(k for k in cases if k.startswith("V12_")):
        c = cases[cid]
        name = c.result["case_name"]
        n = np.asarray(c.result["floor_normal"], float)
        z = c.npz()
        slip = _slip(z, n, radius, 0, -1)
        checks += s7.v12_checks(cid + f" ({name})",
                                contact_world_N=c.result["mean_last_s"]["pad_contact_world_N"],
                                ref=refs_all["slope_V12"][name]["L2b_NSC"], slip_in_plane_m=slip,
                                w_total_N=w_total, key=f"reference.json / slope_V12 / {name} / "
                                                       "L2b_NSC")
        topo = ROOT / "06_analysis" / "00_dynamics" / "v12_l2b_topology_check.json"
        if topo.exists():
            rep = json.loads(topo.read_text(encoding="utf-8")).get(name)
            if rep is not None:
                hor = np.asarray(c.result["mean_last_s"]["pad_contact_world_N"], float)[:, :2]
                checks.append(s7.check_abs(
                    "info", f"{cid} ({name}): horizontal vs Chrono-topology linear replica "
                    "(kt barrel-rod horizontal, rigid stick; v12_l2b_topology_check.py)", hor,
                    rep["chrono_topology_horizontal_N"], s7.V12_HOR_ABS_N, "N",
                    ref_key="06_analysis/00_dynamics/v12_l2b_topology_check.json"))
        numbers[cid] = {"mean_last_s": c.result["mean_last_s"], "slip_in_plane_m": slip.tolist(),
                        "raw_centre_slip_m": c.result["pad_slip_m"]}

    # V4
    c = cases.get("V4_lift_top")
    lift_series = None
    if c is not None:
        z = c.npz()
        lift_series = z
        plan = c.result["plan"]
        t_cmd = z["t_s"] - LIFT_COMMAND_START_S  # run_S7 _job_lift: 1 s settle, then command
        r0, r1 = plan["residual_window_s"]
        res_mask = (t_cmd >= r0 - 1e-9) & (t_cmd <= r1 + 1e-9)
        amp = ((0.5 * np.ptp(z["roll_pitch_deg"][res_mask], axis=0)).tolist()
               if res_mask.any() else [math.nan, math.nan])
        checks += s7.v4_checks(c.result["touch_eq_s"],
                               ref["V4_NSC"]["L2b_dynamic"]["touch_s (FL, FR, RL, RR)"],
                               residual_amp_deg=amp,
                               key=f"{s7.REF} / V4_NSC / L2b_dynamic / touch_s (FL, FR, RL, RR)")
        m0, m1 = plan["mean_window_s"]
        mean_mask = (t_cmd >= m0 - 1e-9) & (t_cmd <= m1 + 1e-9)
        fin = z["pad_normal_N"][mean_mask].mean(axis=0)
        stops = plan["stop_s"]
        checks.append(s7.check_abs("info", "V4: final contact vs V1 (rod-side lock path "
                                   "dependence, record)", fin,
                                   ref["levels"]["top"]["contact_force_N (V1)"],
                                   s7.V1_LEG_W4 * w_total / 4, "N"))
        numbers["V4"] = {"touch_eq_s": c.result["touch_eq_s"], "plan_stops_s": stops,
                         "residual_amp_deg": amp, "final_contact_N": fin.tolist()}

    # V14
    v14_series = {}
    for tag, name in V14_TAGS.items():
        rc = ref["V14"]["cases"][name]
        c = cases.get(f"V14_{tag}_RL")
        if c is not None:
            z = c.npz("series_creep.npz")
            zs = c.npz("series.npz")
            trav = z["s_ref_m"][:, 2] - z["s_ref_m"][0, 2]
            w = _window(_dt_sample(z["t_s"]))
            res = s7.creep_thresholds(z["t_s"], trav, z["cylinder_force_N"], z["pad_normal_N"],
                                      f_min, window=w, exclude_leg=2)
            sec = s7.secant_at(trav, z["cylinder_force_N"], 1.0e-3, z["t_s"], w)
            n = np.asarray(c.result["floor_normal"], float)
            slip_settle = np.linalg.norm(_slip(zs, n, radius, 0, -1), axis=1)
            # judged slip: settle + creep up to the F_min crossing; near lift-off the unloading
            # pad slides at T = mu N (friction cap, N -> 0): recorded up to lift-off
            k_fmin = (int(np.searchsorted(trav, 1e-3 * res.f_min_mm)) if res.f_min_mm
                      else len(trav) - 1)
            k_lift = int(np.searchsorted(trav, 1e-3 * res.liftoff_mm)) if res.liftoff_mm \
                else len(trav) - 1
            slip_creep = np.linalg.norm(_slip(z, n, radius, 0, min(k_fmin, len(trav) - 1)),
                                        axis=1)
            slip_lift = np.linalg.norm(_slip(z, n, radius, 0, min(k_lift, len(trav) - 1)), axis=1)
            slip = np.maximum(slip_settle, slip_creep)
            key = f"{s7.REF} / V14 / cases / {name} / RL+ / L1R_after_extend"
            checks += s7.v14_checks(f"V14 {tag}", secant_N=sec, thresholds=res,
                                    ref=rc["RL+"]["L1R_after_extend"], slip_m=slip, key=key)
            checks.append(check_max("info", f"V14 {tag}: in-plane slip up to lift-off (friction "
                                    "cap of the unloading pad, record)", slip_lift,
                                    s7.V14_SLIP_M, "m"))
            numbers[f"V14_{tag}_RL"] = {"thresholds": res.__dict__, "secant_N": sec.tolist(),
                                        "slip_settle_m": slip_settle.tolist(),
                                        "slip_creep_to_F_min_m": slip_creep.tolist(),
                                        "slip_creep_to_liftoff_m": slip_lift.tolist(),
                                        "V12_like_mean_last_s": c.result["mean_last_s"]}
            v14_series[tag] = (trav, z, res, rc)
        c = cases.get(f"V14_{tag}_modes")
        if c is not None:
            shapes_top = ref["levels"]["top"]["modes"]["LOCK"]["mode_shapes"]
            t, qx = _modal_series(c, "series_modes.npz",
                                  shapes_top["reference_point_m (superstructure CoM)"])
            q = qx[:, :10]
            f_ref = rc["f_Hz_LOCK (first 6, rocking judged +-3 %)"]
            rows, det, _ = identify(t, q, phi=None, mm=np.asarray(shapes_top["mass_matrix"]),
                                    f_ref=f_ref, window_s=float(t[-1] - t[0]))
            checks += s7.mode_checks("V14", f"V14 {tag} modes", rows, f_ref_Hz=f_ref,
                                     zeta_ref=None, key_f=f"{s7.REF} / V14 / cases / {name} / "
                                     "f_Hz_LOCK", f_tol=s7.V14_F_REL)
            modal_numbers[f"V14_{tag}_modes"] = {"judged": [r.__dict__ for r in rows],
                                                 "detail": det}

    summary = s7.summarize_ids([c.as_dict() for c in checks])
    return {"run": str(run), "cases": sorted(cases), "summary": summary,
            "checks": _rows(checks), "numbers": numbers, "modal": modal_numbers,
            "_plots": {"etas": etas, "v14": v14_series, "v11b": v11b_series,
                       "lift": lift_series}}


def _slip(z: dict[str, np.ndarray], n: np.ndarray, radius: np.ndarray, k0: int, k1: int
          ) -> np.ndarray:
    """In-plane slip of the contact point between samples ``k0`` and ``k1``: centre motion minus
    the rolling lever ``dtheta x (r n)`` (the rod turns with the body, sphere radius r)."""
    dc = z["pad_centre_world_m"][k1] - z["pad_centre_world_m"][k0]
    theta = s7.integrate_rotation(z["t_s"][k0:(None if k1 == -1 else k1 + 1)],
                                  z["body_omega_rad_s"][k0:(None if k1 == -1 else k1 + 1)])[-1]
    lever = np.array([np.cross(theta, r * n) for r in radius])
    return s7.in_plane(dc - lever, n)


def _v11(c: Case, params, v_max: float, numbers: dict[str, Any]) -> list[CheckResult]:
    z = c.npz("series_v11.npz")
    sched = c.result["v11"]["schedule"]
    t = z["t_s"] - z["t_s"][0] + _dt_sample(z["t_s"])
    u = z["u_applied_m_s"]
    sr = z["s_ref_m"]
    half = float(sched.get("end_s", 69.0)) / 2.0
    stroke = params.actuator.stroke_m
    times = {}
    second = t >= half
    for i, leg in enumerate(s7.LEGS):
        moving = second & (np.abs(u[:, i]) > 0)
        if not moving.any():
            continue
        k_stop = np.flatnonzero(moving)[-1]
        times[f"{leg} {'0->0.70' if sr[-1, i] > 0.35 else '0.70->0'}"] = float(t[k_stop] - half)
    expected = stroke / v_max + params.actuator.command_ramp_s
    track = np.abs(z["motor_pos_m"] - sr).max(axis=0)
    numbers["V11"] = {"stroke_times_s": times, "expected_s": expected,
                      "max_abs_u": np.abs(u).max(axis=0).tolist(),
                      "tracking_max_m": track.tolist()}
    return s7.v11_checks(v_max=v_max, max_abs_u=np.abs(u).max(axis=0), reach_legs=[True] * 4,
                         s_ref_min=float(sr.min()), s_ref_max=float(sr.max()), stroke_m=stroke,
                         stroke_times_s=times, expected_time_s=expected, tracking_max_m=track)


# --- figures --------------------------------------------------------------------------------------


def _repo_rel(p: Path) -> str:
    """Repository-relative path string (absolute only if outside the repository)."""
    p = Path(p).resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def figures(res: dict[str, Any], out_dir: Path) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    files = []
    plots = res["_plots"]
    if plots["v14"]:
        fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
        for ax, (tag, (trav, z, _thr, rc)) in zip(axes.ravel(), plots["v14"].items(), strict=False):
            tc, f = s7.centred_moving_mean(z["t_s"], z["cylinder_force_N"], 100)
            _, n = s7.centred_moving_mean(z["t_s"], z["pad_normal_N"], 100)
            tr = 1e3 * np.interp(tc, z["t_s"], trav)
            for i, leg in enumerate(s7.LEGS):
                ax.plot(tr, f[:, i] / 1e3, label=f"{leg} cylinder F")
            ax.plot(tr, n[:, 3] / 1e3, "k--", lw=0.8, label="RR contact N")
            r = rc["RL+"]["L1R_after_extend"]
            ax.axvline(r["F_min_threshold_mm"]["value"], color="0.5", ls=":")
            ax.axvline(r["liftoff_threshold_mm"]["value"], color="0.5", ls="-.")
            ax.axhline(9.41459, color="r", lw=0.6)
            ax.set_title(f"V14 {tag}: RL+ creep (ref F_min / lift-off dotted)")
            ax.set_xlabel("RL s_ref travel [mm]")
            ax.set_ylabel("force [kN] (0.1 s window mean)")
            ax.grid(alpha=0.3)
        axes[0, 0].legend(fontsize=7)
        p = out_dir / "verify_S7_L2b_V14.png"
        fig.savefig(p, dpi=110)
        plt.close(fig)
        files.append(_repo_rel(p))
    if plots["etas"]:
        keys = list(plots["etas"])
        fig, axes = plt.subplots(len(keys), 1, figsize=(11, 2.2 * len(keys)),
                                 constrained_layout=True, squeeze=False)
        for ax, k in zip(axes[:, 0], keys, strict=True):
            t, eta = plots["etas"][k]
            for i in range(eta.shape[1]):
                ax.plot(t, eta[:, i] / (np.abs(eta[:, i]).max() or 1) + 2.2 * i, lw=0.5)
            ax.set_title(f"{k}: modal coordinates 1-6 (normalised, offset)")
            ax.set_xlabel("t [s]")
            ax.set_yticks([])
        p = out_dir / "verify_S7_L2b_modes.png"
        fig.savefig(p, dpi=100)
        plt.close(fig)
        files.append(_repo_rel(p))
    if plots["v11b"] or plots["lift"] is not None:
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
        for leg, z in plots["v11b"].items():
            axes[0].plot(z["t_s"], np.asarray(z["force_N"]) / 1e3, label=f"V11b {leg} force")
        axes[0].set_xlabel("t [s]")
        axes[0].set_ylabel("cylinder force [kN]")
        axes[0].legend()
        axes[0].grid(alpha=0.3)
        z = plots["lift"]
        if z is not None:
            for i, leg in enumerate(s7.LEGS):
                axes[1].plot(z["t_s"], z["pad_normal_N"][:, i] / 1e3, lw=0.6, label=leg)
            axes[1].plot(z["t_s"], z["crawler_normal_N"] / 1e3, "k", lw=0.6, label="crawler")
            axes[1].set_xlabel("t [s] (absolute)")
            axes[1].set_ylabel("contact normal [kN]")
            axes[1].legend(fontsize=7)
            axes[1].grid(alpha=0.3)
            axes[1].set_title("V4 lift (top)")
        p = out_dir / "verify_S7_L2b_V11b_V4.png"
        fig.savefig(p, dpi=110)
        plt.close(fig)
        files.append(_repo_rel(p))
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=OUT_DIR / "verify_S7_L2b.json")
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--extra-run", type=Path, action="append", default=[],
                    help="additional batch folder whose cases are added (repeatable; V9 (b) "
                         "V9s_<setting>_FLp1_dt* cases, dynamics_model.md 5.22.3)")
    args = ap.parse_args(argv)
    run = args.run or max((p for p in RESULTS.glob("run_*") if p.is_dir()),
                          key=lambda p: p.name)
    res = judge(run, args.extra_run)
    res["extra_runs"] = [str(p) for p in args.extra_run]
    plots = res.pop("_plots")
    if not args.no_figures:
        res["figures"] = figures({"_plots": plots}, args.out.parent)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for k, v in res["summary"].items():
        print(f"{k:6s} {'pass' if v else 'FAIL'}")
    for row in res["checks"]:
        if not row["passed"] and row["id"] != "info":
            print("FAIL", row["id"], row["item"], "value", json.dumps(row["value"])[:160],
                  "ref", json.dumps(row["ref"])[:120])
    print("missing:", res["numbers"]["missing_or_failed_cases"])
    print("out:", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
