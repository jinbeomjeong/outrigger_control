"""C2 design verification in the time domain (00_docs/04_control/c2_design.md section 6).

Re-uses the reduced nonlinear 6-DoF plant, sensors, metrics and the C2 controller of
04_scripts/01_dynamics/run_control_comparison.py (imported read-only; that script is not modified) and adds what the
C2 design specification requires but the comparison model left out:
  * one extra control step of input delay (command computed at t_k is applied from t_{k+1}),
  * a valve ramp (acceleration limit): the applied leg speed moves towards the command at <= v_max / 0.1 s
    (ASSUMPTION, dynamics_model.md 5.2 item 4), integrated in 1 ms chunks (2 physics steps of 5e-4 s),
  * C2 gains / guard options from the design (class C2D), optional F_min guard priority (selector),
  * a flexible-mast surrogate (roll / pitch inertia scaled to the coupled rocking frequencies of
    dynamics_model.md 3.9.3, scale factors from c2_linear) and a leg damping scale (sensitivity).
The physics (numba kernel), crawler layout D, IMU C1 point, 2nd-order attitude filter, seeds (12345) are those of
run_control_comparison.py.

Run (project root):
  conda run -n dynamics-dev python -I 04_scripts/03_control/run_c2_timedomain.py [--quick] [--workers N]
Writes 06_analysis/02_control/c2_design_timedomain.json, c2_design_timedomain_*.png and merges a summary into
06_analysis/02_control/c2_design.json (key "timedomain") when that file exists.
Heavy work runs on the E-cores (logical CPUs 16-27) at below-normal priority (parallel Chrono S2b on the P-cores).
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "01_dynamics"))
sys.path.insert(0, str(HERE))
import run_control_comparison as rcc  # noqa: E402
import dyn_model as dm  # noqa: E402

OUT_DIR = dm.PROJECT_ROOT / "06_analysis" / "02_control"
E_CORES = list(range(16, 28))

# ---------------------------------------------------------------------------- design gain sets (tuning iterations)
# keys: run_control_comparison.CA overrides + C2D options
GAINSETS = {
    # it0: gains of the candidate comparison (control_candidates_comparison.md 2.2), with the delay + ramp of the spec
    "it0_current": {"Kp_att_1_s": 0.4, "Ki_att_1_s2": 0.02, "Kz_1_s": 0.5, "Ktw_1_s": 0.5, "guard_gain_1_s": 0.5,
                    "guard_priority": False, "delay_steps": 1, "ramp_s": 0.1},
    # it0 without delay / ramp = the comparison model as run before (regression anchor)
    "it0_nodelay": {"Kp_att_1_s": 0.4, "Ki_att_1_s2": 0.02, "Kz_1_s": 0.5, "Ktw_1_s": 0.5, "guard_gain_1_s": 0.5,
                    "guard_priority": False, "delay_steps": 0, "ramp_s": 0.0},
    "it1_Kp0.5": {"Kp_att_1_s": 0.5, "Ki_att_1_s2": 0.025, "Kz_1_s": 0.5, "Ktw_1_s": 0.5, "guard_gain_1_s": 0.5,
                  "guard_priority": False, "delay_steps": 1, "ramp_s": 0.1},
    "it2_Kp0.6": {"Kp_att_1_s": 0.6, "Ki_att_1_s2": 0.03, "Kz_1_s": 0.5, "Ktw_1_s": 0.5, "guard_gain_1_s": 0.5,
                  "guard_priority": False, "delay_steps": 1, "ramp_s": 0.1},
    # it3a: it0 gains + F_min guard gain 1.0 1/s with priority (selector)
    "it3a_guard": {"Kp_att_1_s": 0.4, "Ki_att_1_s2": 0.02, "Kz_1_s": 0.5, "Ktw_1_s": 0.5, "guard_gain_1_s": 1.0,
                   "guard_priority": True, "delay_steps": 1, "ramp_s": 0.1},
    # it3: proposal = it3a + faster twist loop Ktw 1.0 1/s
    "it3_proposal": {"Kp_att_1_s": 0.4, "Ki_att_1_s2": 0.02, "Kz_1_s": 0.5, "Ktw_1_s": 1.0, "guard_gain_1_s": 1.0,
                     "guard_priority": True, "delay_steps": 1, "ramp_s": 0.1, "clr_lpf_tau_s": 0.2},
    # it3 without the extra delay (robustness to the delay assumption)
    "it3_proposal_d0": {"Kp_att_1_s": 0.4, "Ki_att_1_s2": 0.02, "Kz_1_s": 0.5, "Ktw_1_s": 1.0, "guard_gain_1_s": 1.0,
                        "guard_priority": True, "delay_steps": 0, "ramp_s": 0.1, "clr_lpf_tau_s": 0.2},
    # it6: proposal + lift-off speed limit 0.3 v_max until the clearance estimate reaches 20 mm (negative test)
    "it6_liftoff0.3": {"Kp_att_1_s": 0.4, "Ki_att_1_s2": 0.02, "Kz_1_s": 0.5, "Ktw_1_s": 1.0, "guard_gain_1_s": 1.0,
                       "guard_priority": True, "delay_steps": 1, "ramp_s": 0.1, "clr_lpf_tau_s": 0.2,
                       "liftoff_speed_frac": 0.3},
}
PROPOSAL = "it3_proposal"
OPTION_DEFAULTS = {"guard_priority": False, "liftoff_speed_frac": 1.0, "liftoff_clr_m": 0.02, "clr_lpf_tau_s": 0.0,
                   "delay_steps": 0,
                   "ramp_s": 0.0}
BASE_SETS = ("it0_nodelay", "it0_current", "it1_Kp0.5", "it2_Kp0.6", "it3_proposal", "it3_proposal_d0")

SLOPES = [("flat", 0, 0), ("pitch+1", 0, 1), ("roll+1", 1, 0), ("diag1", 0.7071, 0.7071),
          ("pitch+3", 0, 3), ("pitch-3", 0, -3), ("roll+3", 3, 0), ("diag3", 2.1213, 2.1213),
          ("pitch+3.7", 0, 3.7), ("roll+5.7", 5.7, 0), ("diag3.2", 2.2627, 2.2627)]


def set_affinity():
    """E-cores, below-normal priority (inherited by the Pool workers)."""
    try:
        import psutil
        pr = psutil.Process()
        n = os.cpu_count() or 1
        cores = [c for c in E_CORES if c < n] or list(range(n))
        pr.cpu_affinity(cores)
        if hasattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS"):
            pr.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        return cores
    except Exception as e:  # noqa: BLE001
        return f"affinity not set: {e!r}"


# ---------------------------------------------------------------------------- controller


class C2D(rcc.C2):
    """C2 of the design: run_control_comparison.C2 + F_min guard with its own gain and (optional) priority:
    while the guard is active the twist-loop term that would lower the guarded leg is suppressed (selector)."""
    name = "C2D"

    def twist_rate(self, m):
        CA = rcc.CA
        c = self.c
        tw = float(c.n @ m["P"])
        db = CA["twist_deadband_N"]
        e = 0.0 if abs(tw) < db else (tw - math.copysign(db, tw))
        rate = -CA["Ktw_1_s"] * e / c.k_nom
        lo = c.F_min + 5e3
        L = self.load_est(m)
        i = int(np.argmin(L))
        if L[i] < lo:
            sgn = math.copysign(1.0, c.n[i])
            if CA.get("guard_priority", False) and rate * sgn < 0:
                rate = 0.0
            rate += sgn * CA.get("guard_gain_1_s", CA["Ktw_1_s"]) * (lo - L[i]) / c.k_nom
            self.guard_steps = getattr(self, "guard_steps", 0) + 1
        return rate


    def outer(self, m):
        """C1/C2 outer loops; optional first-order low-pass (clr_lpf_tau_s) on the stroke-based clearance used by the
        heave loop and the completion check (the stroke reading contains the oil compression P / k_oil, i.e. the
        rocking modes)."""
        zd, phid, thd, clr = super().outer(m)
        tz = rcc.CA.get("clr_lpf_tau_s", 0.0)
        if tz > 0:
            if getattr(self, "clr_f", None) is None:
                self.clr_f = clr
            else:
                self.clr_f += (rcc.T_CTRL / tz) * (clr - self.clr_f)
            clr = self.clr_f
            zd = float(np.clip(rcc.CA["Kz_1_s"] * (rcc.CA["clearance_target_m"] - clr), -self.c.vmax, self.c.vmax))
        return zd, phid, thd, clr

    def level(self, m):
        """Optional lift-off speed limit (tested, not part of the proposal): while the stroke-based crawler clearance
        estimate is below liftoff_clr_m, scale the leg-speed vector to <= liftoff_speed_frac v_max."""
        u = super().level(m)
        frac = rcc.CA.get("liftoff_speed_frac", 1.0)
        if frac < 1.0 and self.c.clearance_est(m["x"]) < rcc.CA.get("liftoff_clr_m", 0.02):
            mx = float(np.max(np.abs(u)))
            if mx > frac * self.c.vmax:
                u = u * (frac * self.c.vmax / mx)
        return u


rcc.CANDIDATES["C2D"] = C2D


# ---------------------------------------------------------------------------- one run (copy of rcc.run_case + delay, ramp, surrogates)


def run_case(level="top", roll=0.0, pitch=0.0, beta=1.0e9, Fs=0.0, imu="nominal", soft_FL=False, contact="pressure",
             settle=False, inertia_scale=(1.0, 1.0), damping_scale=1.0, keep_series=False, seed=None):
    CA = rcc.CA
    dt = rcc.DT
    plant = rcc.Plant(level, roll, pitch, beta=beta, Fs=Fs, soft_FL=soft_FL, dt=dt)
    if tuple(inertia_scale) != (1.0, 1.0):   # flexible-mast surrogate (ASSUMPTION, c2_linear._fit_inertia_scale)
        Dm = np.diag([math.sqrt(inertia_scale[0]), math.sqrt(inertia_scale[1]), 1.0])
        plant.Ib = Dm @ plant.Ib @ Dm
        plant.Ibinv = np.linalg.inv(plant.Ib)
    if damping_scale != 1.0:                  # leg damping sensitivity (pads only)
        plant.cn = plant.cn * damping_scale
        plant.ct = plant.ct * damping_scale
    nsub = int(round(rcc.T_CTRL / dt))
    plant.step(np.zeros(4), int(round(rcc.SETTLE_ON_CRAWLER_S / dt)))
    plant.t = 0.0
    rng = np.random.default_rng(CA["seed"] if seed is None else seed)
    sens = rcc.Sensors(CA["imu_" + imu], rng, plant.g)
    W_nom = dm.body_from_params(dm.load_params(), level).mass * plant.g
    k_nom = float(np.mean(rcc.Plant.k_nom_cache()))
    ctx = rcc.Ctx(plant.geo, W_nom, k_nom)
    ctrl = C2D(ctx, contact=contact)
    sc = CA["settle_scenario"]; sleg = dm.LEG_NAMES.index(sc["leg"])
    delay = int(CA.get("delay_steps", 0))
    ramp = float(CA.get("ramp_s", 0.0))
    vmax = plant.geo.v_max
    chunk = 2 if ramp > 0 else nsub                     # 1 ms chunks while ramping
    du_max = (vmax / ramp) * chunk * dt if ramp > 0 else np.inf
    queue = deque([np.zeros(4)] * delay)
    u_cmd = np.zeros(4); u_app = np.zeros(4)
    ser = {k: [] for k in ("t", "phi", "theta", "phi_m", "theta_m", "P", "Ftrue", "x", "u", "crawler_N", "clr",
                           "Pmax", "Pmin")}
    sat_steps = np.zeros(4); stroke_steps = np.zeros(4)
    t_lift = None; t_sink = None
    t_end = rcc.T_MAX
    acc_imu = np.zeros(3); acc_misc = np.zeros(24)
    while plant.t < t_end - 1e-9:
        if settle and ctrl.t_ready_first is not None:
            t_sink = ctrl.t_ready_first + sc["start_after_ready_s"]
            plant.goff[sleg] = sc["depth_m"] * min(1.0, max(0.0, (plant.t - t_sink) / sc["ramp_s"]))
        # input delay
        if delay > 0:
            queue.append(u_cmd.copy()); u_tgt = queue.popleft()
        else:
            u_tgt = u_cmd
        # integrate one control period in chunks (valve ramp)
        acc_imu[:] = 0.0
        pmax = np.full(4, -1e12); pmin = np.full(4, 1e12); sat = np.zeros(4); strk = np.zeros(4)
        done_steps = 0
        while done_steps < nsub:
            k = min(chunk, nsub - done_steps)
            if ramp > 0:
                u_app = u_app + np.clip(u_tgt - u_app, -du_max, du_max)
            else:
                u_app = u_tgt.copy()
            a = plant.step(u_app, k)
            acc_imu += a[0:3]
            pmax = np.maximum(pmax, a[16:20]); pmin = np.minimum(pmin, a[20:24])
            sat += a[3:7]; strk += a[7:11]
            done_steps += k
        acc_misc[:] = a
        acc_misc[0:3] = acc_imu
        acc_misc[3:7] = sat; acc_misc[7:11] = strk
        acc_misc[16:20] = pmax; acc_misc[20:24] = pmin
        sat_steps += sat; stroke_steps += strk
        m = sens.read(plant, acc_misc, nsub)
        phi, th = plant.attitude()
        if t_lift is None and a[15] == 0.0 and ctrl.phase == "level":
            t_lift = plant.t
        ser["t"].append(plant.t); ser["phi"].append(phi); ser["theta"].append(th)
        ser["phi_m"].append(ctrl.phi_f if ctrl.phi_f is not None else m["phi"])
        ser["theta_m"].append(ctrl.th_f if ctrl.th_f is not None else m["theta"])
        ser["P"].append(plant.pressure().copy()); ser["Ftrue"].append(plant.true_cyl_force().copy())
        ser["x"].append(plant.x.copy()); ser["u"].append(u_app.copy()); ser["crawler_N"].append(a[15])
        ser["clr"].append(plant.crawler_clearance())
        ser["Pmax"].append(pmax.copy()); ser["Pmin"].append(pmin.copy())
        u_cmd = np.asarray(ctrl.update(m, plant.t), float)
        if ctrl.t_ready_first is not None:
            t_end = min(rcc.T_MAX, ctrl.t_ready_first + (40.0 if settle else rcc.T_HOLD))
        if getattr(ctrl, "fault", False) and t_end == rcc.T_MAX:
            t_end = plant.t + rcc.T_HOLD
    S = {k: np.array(v) for k, v in ser.items()}
    res = rcc.metrics(S, ctrl, plant, t_lift, sat_steps, stroke_steps, t_sink)
    res["guard_active_s"] = round(getattr(ctrl, "guard_steps", 0) * rcc.T_CTRL, 2)
    # overshoot of the true attitude past zero after crawler lift-off (sign change relative to the start), deg
    att = np.degrees(np.column_stack([S["phi"], S["theta"]]))
    if t_lift is not None:
        post = S["t"] >= t_lift
        a0 = att[post][0]
        osh = [float(max(0.0, np.max(-np.sign(a0[j]) * att[post][:, j]))) if abs(a0[j]) > 0.2 else 0.0
               for j in range(2)]
        res["overshoot_true_deg"] = [round(v, 4) for v in osh]
    res["peak_leg_speed_mm_s"] = round(float(np.abs(S["u"]).max()) * 1e3, 2)
    res.update({"level": level, "roll_g": roll, "pitch_g": pitch, "beta_GPa": beta / 1e9, "Fs_kN": Fs / 1e3,
                "imu": imu, "soft_FL": soft_FL, "contact": contact, "settle": settle,
                "inertia_scale": list(inertia_scale), "damping_scale": damping_scale})
    if keep_series:
        res["_series"] = S
    return res


def _run(kw):
    kw = dict(kw)
    tag = kw.pop("tag"); grp = kw.pop("group", "base"); gs = kw.pop("gainset")
    rcc.CA.update(OPTION_DEFAULTS)          # workers are reused: reset the C2D options first
    rcc.CA.update(GAINSETS[gs])
    t0 = time.perf_counter()
    try:
        r = run_case(**kw)
    except Exception as e:  # noqa: BLE001
        r = {"error": repr(e)}
    r["slope"] = tag; r["group"] = grp; r["gainset"] = gs; r["wall_s"] = round(time.perf_counter() - t0, 1)
    r.pop("_series", None)
    return r


def case_list(quick=False):
    import c2_linear as cl
    cases = []
    sets = [PROPOSAL] if quick else list(BASE_SETS)
    levels = ("top",) if quick else ("top", "middle", "bottom")
    slopes = [s for s in SLOPES if s[0] in ("flat", "roll+3", "diag3", "pitch+3.7")] if quick else SLOPES
    for gs in sets:
        for lv in levels:
            for tag, ro, pi in slopes:
                cases.append(dict(gainset=gs, level=lv, roll=ro, pitch=pi, tag=tag, group="base"))
    if quick:
        return cases
    gp = PROPOSAL
    for tag, ro, pi in [("diag3", 2.1213, 2.1213), ("roll+3", 3, 0)]:
        for b in (0.69e9, 1.6e9):
            cases.append(dict(gainset=gp, level="top", roll=ro, pitch=pi, beta=b, tag=tag, group="beta"))
    for tag, ro, pi in [("flat", 0, 0), ("roll+3", 3, 0)]:
        for fs in (0.0, 2e3, 5e3, 12e3):
            for ctc in ("pressure", "combined"):
                if fs == 0.0 and ctc == "pressure":
                    continue
                cases.append(dict(gainset=gp, level="top", roll=ro, pitch=pi, Fs=fs, contact=ctc, tag=tag, group="seal"))
    for g in (gp, "it0_current", "it3a_guard"):
        for fs in (0.0, 12e3):
            for ctc in ("pressure", "combined"):
                cases.append(dict(gainset=g, level="top", Fs=fs, contact=ctc, settle=True, tag="flat", group="settle"))
        for tag, ro, pi in [("flat", 0, 0), ("diag3", 2.1213, 2.1213)]:
            cases.append(dict(gainset=g, level="top", roll=ro, pitch=pi, soft_FL=True, tag=tag, group="soft_FL"))
    for tag, ro, pi in [("flat", 0, 0), ("diag3", 2.1213, 2.1213)]:
        cases.append(dict(gainset=gp, level="top", roll=ro, pitch=pi, imu="worst", tag=tag, group="imu_worst"))
    # flexible-mast surrogate and low leg damping (zeta_leg 0.01 = x 1/3)
    for lv in ("top", "bottom"):
        for mast in ("sup_upper", "sup_lower"):
            sc = cl.build_plant(cl.PlantCase(level=lv, mast=mast)).inertia_scale
            for tag, ro, pi in [("flat", 0, 0), ("roll+3", 3, 0), ("diag3", 2.1213, 2.1213), ("pitch+3.7", 0, 3.7)]:
                for g in (gp, "it0_current"):
                    cases.append(dict(gainset=g, level=lv, roll=ro, pitch=pi, inertia_scale=sc, tag=tag,
                                      group=f"mast_{mast}"))
    sc_l = cl.build_plant(cl.PlantCase(level="top", mast="sup_lower")).inertia_scale
    for tag, ro, pi in [("diag3", 2.1213, 2.1213), ("pitch+3.7", 0, 3.7), ("roll+3", 3, 0)]:
        for isc, grp in (((1.0, 1.0), "liftoff_limit"), (sc_l, "liftoff_limit_mast_sup_lower")):
            cases.append(dict(gainset="it6_liftoff0.3", level="top", roll=ro, pitch=pi, inertia_scale=isc, tag=tag,
                              group=grp))
    for tag, ro, pi in [("flat", 0, 0), ("roll+3", 3, 0), ("diag3", 2.1213, 2.1213)]:
        cases.append(dict(gainset=gp, level="top", roll=ro, pitch=pi, damping_scale=1 / 3, tag=tag, group="damp_low"))
        sc = cl.build_plant(cl.PlantCase(level="top", mast="sup_lower")).inertia_scale
        cases.append(dict(gainset=gp, level="top", roll=ro, pitch=pi, damping_scale=1 / 3, inertia_scale=sc, tag=tag,
                          group="damp_low_mast_sup_lower"))
    return cases


KEEP = ("gainset", "group", "slope", "level", "beta_GPa", "Fs_kN", "imu", "soft_FL", "contact", "settle",
        "inertia_scale", "damping_scale", "t_touch_s", "t_crawler_liftoff_s", "t_done_s", "t_ready_s", "probe_time_s",
        "probe_rounds", "t_within_target_s", "ss_true_att_deg_mean", "ss_true_att_deg_maxabs", "min_true_cyl_force_kN",
        "min_true_leg", "min_pressure_reading_kN", "t_below_Fmin_true_s", "max_pressure_bar", "levelled_loads_true_kN",
        "levelled_twist_load_kN", "final_clearance_mm", "rocking_peak_deg", "overshoot_true_deg", "peak_leg_speed_mm_s",
        "guard_active_s", "force_sat_210bar_steps", "settle_result", "probe_window_max_true_att_deg", "fails", "events",
        "error", "wall_s")


def compact(r):
    out = {k: r[k] for k in KEEP if k in r and r[k] not in (None, [], {})}
    if "events" in out:
        out["events"] = out["events"][:6]
    if r.get("t_ready_s") is not None and r.get("t_touch_s") is not None:
        out["t_level_after_touch_s"] = round(r["t_ready_s"] - r["t_touch_s"], 2)
    return out


def summarise(runs):
    out = {}
    for gs in GAINSETS:
        for lv in ("top", "middle", "bottom", "all"):
            b = [r for r in runs if r.get("gainset") == gs and r.get("group") == "base" and (lv == "all" or r.get("level") == lv)]
            if not b:
                continue
            ok = [r for r in b if not r.get("fails") and "error" not in r]
            tl = [r["t_level_after_touch_s"] for r in ok if "t_level_after_touch_s" in r]
            out[f"{gs}:{lv}"] = {
                "runs": len(b), "pass": len(ok),
                "fail_cases": sorted(f"{r.get('level')}:{r.get('slope')}:{'/'.join(r.get('fails', []))}{r.get('error', '')}"
                                     for r in b if r.get("fails") or "error" in r),
                "t_level_median_s": round(float(np.median(tl)), 2) if tl else None,
                "t_level_max_s": round(float(np.max(tl)), 2) if tl else None,
                "t_level_sum_s": round(float(np.sum(tl)), 1) if tl else None,
                "min_true_cyl_force_kN": round(min(r["min_true_cyl_force_kN"] for r in ok), 2) if ok else None,
                "max_pressure_bar": max(r["max_pressure_bar"] for r in ok) if ok else None,
                "ss_true_att_deg_max": max(r["ss_true_att_deg_maxabs"] for r in ok) if ok else None,
                "rocking_peak_deg_max": max(r["rocking_peak_deg"] for r in ok) if ok else None,
                "overshoot_true_deg_max": max(max(r.get("overshoot_true_deg", [0, 0])) for r in ok) if ok else None,
            }
    return out


def figure(stem):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(3, 1, figsize=(9, 8.5), sharex=True)
    cols = {"it0_nodelay": "#9e9e9e", "it0_current": "#1f77b4", PROPOSAL: "#d62728"}
    for gs in ("it0_nodelay", "it0_current", PROPOSAL):
        rcc.CA.update(OPTION_DEFAULTS); rcc.CA.update(GAINSETS[gs])
        r = run_case("top", 3.0, 0.0, keep_series=True)
        S = r["_series"]; t = S["t"]
        ax[0].plot(t, np.degrees(S["phi"]), color=cols[gs], lw=1.0, label=f"{gs} (Kp {GAINSETS[gs]['Kp_att_1_s']})")
        ax[1].plot(t, S["Ftrue"].min(axis=1) / 1e3, color=cols[gs], lw=1.0)
        ax[2].plot(t, S["u"] * 1e3, color=cols[gs], lw=0.6)
    tg = rcc.CA["accuracy_target_deg"]
    ax[0].axhspan(-tg, tg, color="0.88", zorder=0)
    ax[0].set_ylabel("true roll [deg]"); ax[0].set_ylim(-0.4, 3.2); ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    ax[0].set_title("C2, top auger, ground roll +3 deg (reduced 6-DoF, crawler D, IMU C1, LPF 2 x 0.5 s), "
                    "grey = +/-0.2 deg", fontsize=9)
    ax[1].axhline(9.4525, color="k", ls="--", lw=0.8); ax[1].set_ylabel("min true cyl. force [kN]"); ax[1].grid(alpha=0.3)
    ax[1].set_ylim(0, 130)
    ax[2].set_ylabel("applied leg speed [mm/s]"); ax[2].set_xlabel("time from leg start [s]"); ax[2].grid(alpha=0.3)
    ax[2].set_xlim(10, 45)
    fig.tight_layout()
    p = OUT_DIR / f"{stem}_roll3.png"
    fig.savefig(p, dpi=90); plt.close(fig)
    return p


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--no-figure", action="store_true")
    args = ap.parse_args()
    cores = set_affinity()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = case_list(args.quick)
    t0 = time.perf_counter()
    _run(dict(cases[0]))   # compile the numba cache in the main process
    from multiprocessing import Pool
    with Pool(args.workers) as pool:
        runs = pool.map(_run, cases, chunksize=1)
    runs = [compact(r) for r in runs]
    stem = "c2_design_timedomain" + ("_quick" if args.quick else "")
    res = {"meta": {"script": "04_scripts/03_control/run_c2_timedomain.py", "argv": sys.argv[1:], "affinity": cores,
                    "dt_s": rcc.DT, "T_ctrl_s": rcc.T_CTRL, "gainsets": GAINSETS, "proposal": PROPOSAL,
                    "assumptions_base": {k: v for k, v in rcc.CA.items() if not isinstance(v, dict)},
                    "settle_on_crawler_s": rcc.SETTLE_ON_CRAWLER_S, "seed": rcc.CA["seed"],
                    "notes": "valve ramp = acceleration limit v_max/0.1 s in 1 ms chunks (ASSUMPTION); 1 extra control "
                             "step of input delay; mast = inertia-scaling surrogate; damping_scale scales pad c_n, c_t"},
           "summary": summarise(runs), "runs": runs}
    if not args.no_figure and not args.quick:
        res["meta"]["figure"] = str(figure(stem).relative_to(dm.PROJECT_ROOT)).replace("\\", "/")
    res["meta"]["wall_s"] = round(time.perf_counter() - t0, 1)
    p = OUT_DIR / f"{stem}.json"
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    main_json = OUT_DIR / "c2_design.json"
    if main_json.exists() and not args.quick:
        with open(main_json, encoding="utf-8") as fh:
            d = json.load(fh)
        d["timedomain"] = {"file": str(p.relative_to(dm.PROJECT_ROOT)).replace("\\", "/"), "summary": res["summary"],
                           "wall_s": res["meta"]["wall_s"]}
        with open(main_json, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=1, default=float)
    print("wrote", p, res["meta"]["wall_s"], "s,", len(runs), "runs")
    print(json.dumps(res["summary"], indent=1))


if __name__ == "__main__":
    main()
