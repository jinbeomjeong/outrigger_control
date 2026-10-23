"""Leg reaction time history while all four outriggers extend 0 -> full stroke on a rigid level floor.

Model (same family as reference.json ``lift_V4_compliant_crawler``, dyn_model.static_unilateral):
  * rigid superstructure (auger level top, mass case C) + 4 rod/pad moving parts, vertical 3-DoF
    q = [uz, roll, pitch] about the body-frame origin (small angles, x/y/yaw fixed),
  * rigid level floor at ground.crawler_bottom_z_m,
  * 4 unilateral pad springs, k = contact.rigid_floor.L1.kn_per_pad_N_m (oil column + rod + frame +
    concrete in series, L1 lumped), placed at the pad bottom centres,
  * crawler layout D (dyn_model.crawler_points / crawler_gaps, YAML contact.crawler.*): 2 x 6 roller
    stations on the floor + 2 x 6 raised end shoes as unilateral springs with an initial gap; kn_total x3
    sensitivity block (contact.crawler.kn_total_sensitivity_range_N_m, dashpot x sqrt(3), same heave zeta),
  * all legs e(t) = min(v t, stroke), v = actuator.max_speed_m_s, t = 0 at motor start,
  * quasi-static (rate effects neglected; checked by a damped 3-DoF time integration through the
    transition, section "quasi_static_check").

Outputs (leg order FL, FR, RL, RR):
  * pad floor reaction F_pad (floor -> pad, + up) [N],
  * cylinder force F_cyl = F_pad - m_rod g [N] (net axial force the oil column transmits; + = compression).
    Before touch the rod hangs from the cylinder: F_cyl = -m_rod g. The head-side pressure sensor reads
    p = max(F_cyl, 0) / A_head (rod-side chamber carries the hanging rod; seal friction neglected).
  * crawler total floor reaction [N], attitude, crawler clearance.

Run (dynamics-dev, activated):
    C:\\ProgramData\\miniforge3\\Scripts\\conda.exe run -n dynamics-dev python -I \\
        04_scripts/01_dynamics/run_leg_extension_loads.py [--speedup 3] [--fps 12.5] [--no-gif]

Writes 06_analysis/00_dynamics/leg_extension_loads.json and leg_extension_loads.gif.
Deterministic (no random numbers).
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dyn_model as dm  # noqa: E402
from run_reference import V4_LAYOUT_D, V4_LAYOUT_D_K3  # noqa: E402  (reference.json layout keys)

OUT_DIR = dm.PROJECT_ROOT / "06_analysis" / "00_dynamics"
OUT_JSON = OUT_DIR / "leg_extension_loads.json"
OUT_GIF = OUT_DIR / "leg_extension_loads.gif"
REF_JSON = OUT_DIR / "reference.json"
KIN_JSON = dm.PROJECT_ROOT / "01_cad" / "02_legs" / "leg_extension_kinematics.json"
LEVEL = "top"

# Colours: identical to 04_scripts/00_cad/analyze_parts.py (LEG_COLORS, OTHER_PART_COLOR, INK_*, SURFACE),
# used by leg_extension.gif and the 3-view drawings. Copied (not imported) because analyze_parts imports
# Chrono-dev-only CAD modules.
LEG_COLORS = {"FL": "#2a78d6", "FR": "#eb6834", "RL": "#1baf7a", "RR": "#eda100"}
CRAWLER_COLOR = "#8d8c86"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
SURFACE = "#fcfcfb"
ALERT = "#c0392b"

EVENT_TOL_S = 1e-7
EVENT_MERGE_S = 0.01   # events closer than this share one held frame


def r(x, n=6):
    if isinstance(x, dict):
        return {k: r(v, n) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [r(v, n) for v in x]
    if isinstance(x, np.ndarray):
        return r(x.tolist(), n)
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (float, np.floating)):
        return float(f"{float(x):.{n}g}")
    if isinstance(x, np.integer):
        return int(x)
    return x


# ---------------------------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------------------------
class LiftModel:
    """Quasi-static unilateral spring statics (pads + crawler spheres), all inputs from the YAML."""

    def __init__(self, p: dict, k_pad: np.ndarray | None = None, kn_scale: float = 1.0):
        self.p = p
        self.geo = geo = dm.geometry_from_params(p)
        self.g = geo.g
        self.v = geo.v_max
        self.stroke = geo.stroke
        self.touch = geo.touch_extension                          # pad touch extension on the floor [m]
        L1 = p["contact"]["rigid_floor"]["L1"]
        self.k_pad = (np.array([float(L1["kn_per_pad_N_m"][n]) for n in dm.LEG_NAMES])
                      if k_pad is None else np.asarray(k_pad, float))
        self.c_pad = np.array([float(L1["cn_per_pad_N_s_m"][n]) for n in dm.LEG_NAMES])
        self.zeta_leg = float(L1["derivation"]["damping_ratio"])            # leg axial zeta behind cn (heave basis)
        self.zeta_crawler = float(p["contact"]["crawler"]["damping_ratio_heave"])
        self.kn_scale = float(kn_scale)
        self.cr_xy, self.cr_k, self.cr_c = dm.crawler_points(p, kn_scale)   # YAML contact.crawler, layout D
        self.cr_gap = dm.crawler_gaps(p)                                      # initial gap per sphere [m]
        self.body = dm.body_from_params(p, LEVEL)                 # superstructure only
        self.bw = dm.body_with_rods(p, geo, LEVEL, np.zeros(4))   # + 4 moving parts (rod x,y fixed)
        self.W_super = self.body.mass * self.g
        self.W_tot = self.bw.mass * self.g
        self.cg = self.bw.com[:2]
        self.W_rod = geo.rod_mass * self.g
        self.xy_all = np.vstack([geo.pad_xy, self.cr_xy])
        self.k_all = np.concatenate([self.k_pad, self.cr_k])
        self.A_pad = dm.support_matrix(geo.pad_xy)
        self.A_cr = dm.support_matrix(self.cr_xy)
        act = p["actuator"]
        # per leg (rev. 30): scalar while all legs share the cylinder (pre-REXOME35 YAML), else (4,)
        self.A_head = dm.scalar_if_equal(math.pi / 4 * dm.leg_cylinder_array(p, "bore_diameter_m") ** 2)
        self.F_ext_max = dm.scalar_if_equal(dm.leg_cylinder_array(p, "max_force_extend_N"))
        self.F_min_cyl = float(p["control"]["F_min_cylinder_N"])

    def solve(self, e: np.ndarray) -> dict:
        e = np.broadcast_to(np.asarray(e, float), (4,))
        delta = np.concatenate([e - self.touch, -self.cr_gap])
        F, q, act = dm.static_unilateral(self.xy_all, self.k_all, delta, self.W_tot, self.cg)
        gap_all = -(delta - dm.support_matrix(self.xy_all) @ q)    # + = open gap
        F_pad = F[:4]
        return {
            "e": e.copy(), "q": q, "F_pad": F_pad, "F_cyl": F_pad - self.W_rod,
            "F_cr": F[4:], "F_cr_tot": float(F[4:].sum()),
            "pad_contact": act[:4].copy(), "crawler_contact": bool(act[4:].any()),
            "gap_all": gap_all, "active_all": act.copy(), "F_all": F,
            "crawler_clearance": float((self.A_cr @ q + self.cr_gap).min()),
        }


def first_change(model, schedule, grid, pred):
    """Times where the boolean pred(state) changes (precomputed grid states + bisection).

    grid = (t array, list of states). Returns list of (t, new_value)."""
    tg, states = grid
    vals = [pred(s) for s in states]
    out = []
    for i in range(len(tg) - 1):
        if vals[i] != vals[i + 1]:
            lo, hi, v_lo = tg[i], tg[i + 1], vals[i]
            while hi - lo > EVENT_TOL_S:
                mid = 0.5 * (lo + hi)
                if pred(model.solve(schedule(mid))) == v_lo:
                    lo = mid
                else:
                    hi = mid
            out.append((0.5 * (lo + hi), vals[i + 1]))
    return out


def events(model, schedule, t_scan, step=1e-3):
    tg = np.arange(0.0, t_scan + 1e-12, step)
    grid = (tg, [model.solve(schedule(t)) for t in tg])
    ev = {}
    for i, n in enumerate(dm.LEG_NAMES):
        ch = first_change(model, schedule, grid, lambda s, i=i: bool(s["pad_contact"][i]))
        ev[f"touch_{n}"] = ch[0][0] if ch else float("nan")
        ch = first_change(model, schedule, grid, lambda s, i=i: bool(s["F_cyl"][i] >= model.F_min_cyl))
        ev[f"F_min_reached_{n}"] = ch[0][0] if ch else float("nan")
    ch = first_change(model, schedule, grid, lambda s: s["crawler_contact"])
    ev["crawler_off"] = ch[0][0] if ch else float("nan")
    ch = first_change(model, schedule, grid, lambda s: bool((s["F_cyl"] >= model.F_min_cyl).all()))
    ev["all_cyl_ge_F_min"] = ch[0][0] if ch else float("nan")
    return ev


# ---------------------------------------------------------------------------------------------
# Independent checks
# ---------------------------------------------------------------------------------------------
def energy_min_check(model: LiftModel, e: np.ndarray) -> np.ndarray:
    """Independent path: minimise the total potential (gravity + unilateral springs) with BFGS."""
    from scipy.optimize import minimize

    delta = np.concatenate([np.broadcast_to(e, (4,)) - model.touch, -model.cr_gap])
    A = dm.support_matrix(model.xy_all)
    w = np.array([model.W_tot, model.W_tot * model.cg[1], -model.W_tot * model.cg[0]])
    scale = np.array([1e-3, 1e-3, 1e-3])  # mm / mrad variables

    def f(z):
        q = z * scale
        c = np.maximum(delta - A @ q, 0.0)
        V = w @ q + 0.5 * np.sum(model.k_all * c * c)
        grad = (w - A.T @ (model.k_all * c)) * scale
        return V, grad

    q0 = np.zeros(3)
    res = minimize(f, q0, jac=True, method="BFGS", options={"gtol": 1e-6, "maxiter": 10000})
    res = minimize(f, res.x, jac=True, method="BFGS", options={"gtol": 1e-8, "maxiter": 10000})
    q = res.x * scale
    c = np.maximum(delta - A @ q, 0.0)
    return model.k_all * c


def dynamic_check(model: LiftModel, t0: float, t1: float, schedule):
    """Damped vertical 3-DoF (uz, roll, pitch about the origin) through the touch transition.

    M = m a a^T + blockdiag(0, I_xy) with a = [1, cg_y, -cg_x] (CoM vertical velocity), I_xy = roll/pitch block of
    the inertia about the CoM (horizontal CoM motion from rotation neglected). Unilateral spring-dampers:
    F = max(0, k c + c_d c_dot) for c > 0 (YAML cn_per_pad, crawler damping_total / n_roller). Gravity on the
    combined CoM. Integrator DOP853 (non-stiff: highest mode ~10 Hz), max_step 1 ms (contact switching).
    """
    from scipy.integrate import solve_ivp

    bw = model.bw
    a = np.array([1.0, bw.com[1], -bw.com[0]])
    M = bw.mass * np.outer(a, a)
    M[1:, 1:] += bw.inertia[:2, :2]
    A = dm.support_matrix(model.xy_all)
    k = model.k_all
    cd = np.concatenate([model.c_pad, model.cr_c])
    w = np.array([model.W_tot, model.W_tot * model.cg[1], -model.W_tot * model.cg[0]])
    v = model.v

    def forces(t, q, qd):
        e = schedule(t)
        ed = np.full(4, v if model.v * t < model.stroke else 0.0)
        delta = np.concatenate([e - model.touch, -model.cr_gap])
        deltad = np.concatenate([ed, np.zeros(len(model.cr_xy))])
        c = delta - A @ q
        cdot = deltad - A @ qd
        F = np.where(c > 0, np.maximum(k * c + cd * cdot, 0.0), 0.0)
        return F

    def rhs(t, y):
        q, qd = y[:3], y[3:]
        F = forces(t, q, qd)
        return np.concatenate([qd, np.linalg.solve(M, A.T @ F - w)])

    s0 = model.solve(schedule(t0))
    y0 = np.concatenate([s0["q"], np.zeros(3)])  # rods move, body at rest on the crawler
    tt = np.round(np.arange(t0, t1 + 1e-12, 1e-3), 6)

    def run(max_step):
        t_wall = time.perf_counter()
        sol = solve_ivp(rhs, (t0, t1), y0, method="DOP853", rtol=1e-9, atol=1e-12, max_step=max_step, t_eval=tt)
        t_wall = time.perf_counter() - t_wall
        F_dyn = np.array([forces(t, sol.y[:3, j], sol.y[3:, j]) for j, t in enumerate(sol.t)])
        return sol, F_dyn, t_wall

    sol, F_dyn, t_wall = run(1e-3)
    sol2, F_dyn2, _ = run(5e-4)
    conv = float(np.abs(F_dyn - F_dyn2).max())
    F_qs = np.array([model.solve(schedule(t))["F_all"] for t in sol.t])
    diff = F_dyn[:, :4] - F_qs[:, :4]
    dpad = np.abs(diff)
    dcr = np.abs(F_dyn[:, 4:].sum(1) - F_qs[:, 4:].sum(1))
    j = int(np.argmax(dpad.max(1)))
    mean_end = F_qs[-1, :4].mean()
    big = np.where(dpad.max(1) > 0.01 * mean_end)[0]
    t_settle = float(sol.t[big[-1]]) if len(big) else float("nan")
    # dynamic contact loss after first touch (pad force back to 0 while the quasi-static pad is loaded)
    lift = {}
    for i, n in enumerate(dm.LEG_NAMES):
        touched = np.where(F_dyn[:, i] > 0)[0]
        if not len(touched):
            lift[n] = None
            continue
        k0 = touched[0]
        loss = (F_dyn[k0:, i] <= 0) & (F_qs[k0:, i] > 0)
        reach = np.where(F_dyn[k0:, i] - model.W_rod[i] >= model.F_min_cyl)[0]
        after_reach = F_dyn[k0 + reach[0]:, i] - model.W_rod[i] if len(reach) else np.array([np.nan])
        lift[n] = {"first_touch_dyn_s": r(float(sol.t[k0]), 6),
                   "contact_lost_samples_after_touch": int(loss.sum()),
                   "cyl_force_min_after_first_reaching_F_min_N": r(float(after_reach.min()), 6),
                   "peak_pad_force_N": r(float(F_dyn[:, i].max()), 6),
                   "peak_at_s": r(float(sol.t[int(np.argmax(F_dyn[:, i]))]), 6),
                   "max_over_quasi_static_N": r(float(diff[:, i].max()), 5),
                   "max_under_quasi_static_N": r(float(diff[:, i].min()), 5)}
    dec = slice(None, None, 2)
    return {
        "model": dynamic_check.__doc__.split("\n\n")[1].strip().replace("\n    ", " "),
        "initial_condition": f"quasi-static pose on the crawler at t = {t0} s, body velocity 0 (pads still in the air)",
        "window_s": [t0, t1],
        "solver": {"method": "DOP853", "rtol": 1e-9, "atol": 1e-12, "max_step_s": 1e-3,
                   "nfev": int(sol.nfev), "status": int(sol.status), "wall_s": round(t_wall, 2),
                   "max_abs_force_diff_vs_max_step_5e-4_N": r(conv, 3)},
        "max_abs_diff_pad_N (FL, FR, RL, RR)": r(dpad.max(0), 4),
        "max_abs_diff_pad_N_at_s": r(float(sol.t[j]), 6),
        "max_abs_diff_crawler_total_N": r(float(dcr.max()), 4),
        "max_diff_rel_to_end_mean_pad_load": r(float(dpad.max() / mean_end), 4),
        "last_time_diff_above_1pct_of_mean_s": r(t_settle, 6),
        "end_diff_pad_N": r(dpad[-1], 4),
        "per_leg": lift,
        "series_2ms": {"t_s": r(sol.t[dec], 7), "F_pad_N": r(F_dyn[dec, :4], 6),
                       "F_crawler_total_N": r(F_dyn[dec, 4:].sum(1), 6)},
        "_arrays": (sol.t, F_dyn[:, :4], F_dyn[:, 4:].sum(1)),
    }


# ---------------------------------------------------------------------------------------------
# GIF
# ---------------------------------------------------------------------------------------------
def timeline(t_end, speedup, fps, hold_start, hold_end, hold_event, event_times):
    """(real time, duration ms, banner) per frame; same rule as render_leg_extension.timeline."""
    step = speedup / fps
    times = list(np.arange(0.0, t_end, step)) + [t_end] + list(event_times)
    times = sorted(set(round(t, 6) for t in times))
    frames = []
    for t in times:
        banner = next((txt for te, txt in event_times.items() if abs(te - t) < 1e-6), None)
        if t == 0.0:
            d = hold_start * 1000
        elif t == round(t_end, 6):
            d = hold_end * 1000
        elif banner:
            d = hold_event * 1000
        else:
            d = 1000.0 / fps
        frames.append((t, d, banner))
    return frames


def render_gif(model, series, ev, rigid_ev, args, ref_lines, dyn_arrays=None):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.patches import FancyBboxPatch, Patch
    from matplotlib.lines import Line2D
    from PIL import Image

    fp = font_manager.FontProperties(family="Malgun Gothic")
    matplotlib.rcParams["font.family"] = fp.get_name()
    matplotlib.rcParams["axes.unicode_minus"] = False

    T = series["t"]
    Fp = series["F_pad"] / 1e3
    Fc = series["F_cyl"] / 1e3
    Fcr = series["F_cr_tot"] / 1e3
    kN = 1e-3
    t_end = model.stroke / model.v

    # held event frames: clusters of touch / crawler-off events
    raw = sorted([(ev[f"touch_{n}"], n) for n in dm.LEG_NAMES] + [(ev["crawler_off"], None)])
    clusters = []
    for t, lab in raw:
        if clusters and t - clusters[-1][-1][0] < EVENT_MERGE_S:
            clusters[-1].append((t, lab))
        else:
            clusters.append([(t, lab)])
    event_times = {}
    for cl in clusters:
        legs = [lab for _, lab in cl if lab]
        txt = []
        if legs:
            txt.append(f"{'·'.join(legs)} 패드 접지")
        if any(lab is None for _, lab in cl):
            txt.append("크롤러 하중 0 (지면에서 떨어짐)")
        times = " / ".join(f"{t:.3f}" for t, _ in cl)
        event_times[round(cl[-1][0] + 1e-4, 6)] = f"▶ {' · '.join(txt)}  (t = {times} s, 유연 모델)"
    plan = timeline(t_end, args.speedup, args.fps, args.hold_start_s, args.hold_end_s, args.hold_event_s,
                    event_times)

    W, H, dpi = args.width_px, int(args.width_px * 0.74), 100
    fig = plt.figure(figsize=(W / dpi, H / dpi), dpi=dpi, facecolor=SURFACE)
    # layout [left, bottom, width, height] in figure fractions
    ax_full = fig.add_axes([0.065, 0.43, 0.50, 0.36])
    ax_zoom = fig.add_axes([0.625, 0.43, 0.355, 0.36])
    ax_bar = fig.add_axes([0.065, 0.065, 0.70, 0.29])
    ax_txt = fig.add_axes([0.785, 0.065, 0.20, 0.29]); ax_txt.axis("off")

    Fmin = model.F_min_cyl * kN
    Fmax = float(np.min(model.F_ext_max)) * kN   # per leg (rev. 30): lowest limit (rear) drawn
    mean_cyl = ref_lines["mean_cyl_N"] * kN
    mean_pad = ref_lines["mean_pad_N"] * kN
    ymax = 1.06 * max(Fcr.max(), Fmax, Fp.max())
    z0, z1 = args.zoom
    rigid_touch_rear, rigid_touch_front = rigid_ev["touch_rear_s"], rigid_ev["touch_front_s"]

    def ref_hlines(ax, labels=True, xr=None):
        ax.axhline(Fmax, color=ALERT, lw=1.1, ls="-.", zorder=1)
        ax.axhline(Fmin, color=ALERT, lw=1.1, ls="--", zorder=1)
        ax.axhline(mean_cyl, color=INK_SECONDARY, lw=0.9, ls=":", zorder=1)
        if labels and xr is not None:
            x = xr[0] + 0.01 * (xr[1] - xr[0])
            ax.text(x, Fmax + 4, f"이동 중 신장 힘 한계 {Fmax:.1f} kN (210 bar × 헤드 면적"
                    + (")" if np.ndim(model.F_ext_max) == 0 else ", 후방)"), fontsize=7.5,
                    color=ALERT, va="bottom")
            ax.text(x, Fmin + 4, f"F_min {Fmin:.2f} kN (실린더 힘 기준)", fontsize=7.5, color=ALERT, va="bottom")
            ax.text(x, mean_cyl + 4, f"정적 평균 {mean_cyl:.1f} kN (실린더) / {mean_pad:.1f} kN (패드)",
                    fontsize=7.5, color=INK_SECONDARY, va="bottom")

    for ax, (xa, xb) in ((ax_full, (0.0, t_end)), (ax_zoom, (z0, z1))):
        ax.set_facecolor(SURFACE)
        ax.grid(True, color="#e4e3df", lw=0.6)
        for n in dm.LEG_NAMES:
            ax.plot(T, Fp[:, dm.LEG_NAMES.index(n)], color=LEG_COLORS[n], lw=1.8, label=f"{n} 패드 반력")
        ax.plot(T, Fcr, color=CRAWLER_COLOR, lw=1.8, label="크롤러 총 반력")
        ax.set_xlim(xa, xb)
        ax.set_ylim(-8, ymax)
        ax.tick_params(labelsize=8, colors=INK_SECONDARY)
        ax.set_xlabel("실제 시간 t [s] (모터 기동 = 0)", fontsize=8.5, color=INK_SECONDARY)
        ref_hlines(ax, labels=(ax is ax_full), xr=(xa, xb))
    ax_full.set_ylabel("지면 반력 [kN]", fontsize=9, color=INK_SECONDARY)
    ax_full.set_title("다리별 패드 지면 반력과 크롤러 총 반력 (0 → 30 s)", fontsize=10, loc="left",
                      color=INK_PRIMARY)
    ax_zoom.set_title(f"확대: {z0:.1f} → {z1:.1f} s (접지 전환)", fontsize=10, loc="left", color=INK_PRIMARY)
    ax_full.axvspan(z0, z1, color="#d9d7d0", alpha=0.35, lw=0)
    # rigid kinematic GIF events (for side-by-side reading)
    for tr in (rigid_touch_rear, rigid_touch_front):
        ax_zoom.axvline(tr, color=INK_SECONDARY, lw=0.8, ls=(0, (1, 2)))
    ax_zoom.text(rigid_touch_rear, 300, f"강체 GIF\n후방 접지\n{rigid_touch_rear:.3f} s ",
                 fontsize=7, color=INK_SECONDARY, va="top", ha="right")
    ax_zoom.text(rigid_touch_front, 300, f" 강체 GIF\n 전방 접지·\n 크롤러 이탈\n {rigid_touch_front:.3f} s",
                 fontsize=7, color=INK_SECONDARY, va="top", ha="left")
    for key in ("touch_RR", "touch_FL", "crawler_off"):
        ax_zoom.axvline(ev[key], color=INK_PRIMARY, lw=0.6, alpha=0.5)
    if dyn_arrays is not None:
        td, Fd, Fcrd = dyn_arrays
        for i, n in enumerate(dm.LEG_NAMES):
            ax_zoom.plot(td, Fd[:, i] / 1e3, color=LEG_COLORS[n], lw=0.8, alpha=0.75, ls=(0, (3, 1.5)), zorder=2)
        ax_zoom.plot(td, Fcrd / 1e3, color=CRAWLER_COLOR, lw=0.8, alpha=0.75, ls=(0, (3, 1.5)), zorder=2)
        ax_zoom.legend(handles=[Line2D([], [], color="#555", lw=1.8, label="준정적 (이 GIF의 기준)"),
                                Line2D([], [], color="#555", lw=0.8, ls=(0, (3, 1.5)),
                                       label=f"감쇠 3자유도 동적 (참고, 감쇠 가정 ζ 다리 {model.zeta_leg:g}·크롤러 {model.zeta_crawler:g})")],
                       loc="center right", fontsize=7, frameon=False, bbox_to_anchor=(1.0, 0.62))
    handles = [Line2D([], [], color=LEG_COLORS[n], lw=2, label=f"{n} 패드") for n in dm.LEG_NAMES]
    handles.append(Line2D([], [], color=CRAWLER_COLOR, lw=2, label="크롤러 합"))
    ax_full.legend(handles=handles, loc="upper right", fontsize=7.5, ncol=1, frameon=False,
                   bbox_to_anchor=(1.0, 0.98))
    cur_full = ax_full.axvline(0, color=INK_PRIMARY, lw=1.3)
    cur_zoom = ax_zoom.axvline(0, color=INK_PRIMARY, lw=1.3)
    dots_full = [ax_full.plot([], [], "o", ms=5, color=LEG_COLORS[n], mec="white", mew=0.8, zorder=5)[0]
                 for n in dm.LEG_NAMES] + [ax_full.plot([], [], "o", ms=5, color=CRAWLER_COLOR, mec="white",
                                                         mew=0.8, zorder=5)[0]]
    dots_zoom = [ax_zoom.plot([], [], "o", ms=5, color=LEG_COLORS[n], mec="white", mew=0.8, zorder=5)[0]
                 for n in dm.LEG_NAMES] + [ax_zoom.plot([], [], "o", ms=5, color=CRAWLER_COLOR, mec="white",
                                                         mew=0.8, zorder=5)[0]]

    # bar panel
    ax_bar.set_facecolor(SURFACE)
    ax_bar.grid(True, axis="y", color="#e4e3df", lw=0.6)
    xs = np.arange(4)
    bw_ = 0.36
    bars_pad = ax_bar.bar(xs - bw_ / 2, np.zeros(4), bw_, color=[LEG_COLORS[n] for n in dm.LEG_NAMES])
    bars_cyl = ax_bar.bar(xs + bw_ / 2, np.zeros(4), bw_, color="white",
                          edgecolor=[LEG_COLORS[n] for n in dm.LEG_NAMES], hatch="///", lw=1.4)
    bar_cr = ax_bar.bar([4.6], [0.0], 0.6, color=CRAWLER_COLOR)
    ax_bar.set_xticks(list(xs) + [4.6])
    ax_bar.set_xticklabels([f"{n}" for n in dm.LEG_NAMES] + ["크롤러 합"], fontsize=9.5)
    ax_bar.set_xlim(-0.6, 5.3)
    ax_bar.set_ylim(-12, ymax)
    ax_bar.tick_params(labelsize=8, colors=INK_SECONDARY)
    ax_bar.set_ylabel("현재 시각 힘 [kN]", fontsize=9, color=INK_SECONDARY)
    ax_bar.axhline(0, color=INK_PRIMARY, lw=0.8)
    ref_hlines(ax_bar, labels=False)
    lab_pad = [ax_bar.text(x - bw_ / 2, 0, "", ha="center", va="bottom", fontsize=8, color=INK_PRIMARY)
               for x in xs]
    lab_cyl = [ax_bar.text(x + bw_ / 2, 0, "", ha="center", va="bottom", fontsize=8, color=INK_SECONDARY)
               for x in xs]
    lab_cr = ax_bar.text(4.6, 0, "", ha="center", va="bottom", fontsize=8.5, color=INK_PRIMARY)
    ax_bar.legend(handles=[Patch(facecolor="#777", label="패드 지면 반력 (바닥 → 패드)"),
                           Patch(facecolor="white", edgecolor="#777", hatch="///",
                                 label="실린더 힘 = 패드 반력 - 로드 무게 (압력 센서 값)"),
                           Line2D([], [], color=ALERT, lw=1.1, ls="-.",
                                  label=f"이동 중 신장 힘 한계 {Fmax:.1f} kN (210 bar × 헤드 면적)"),
                           Line2D([], [], color=INK_SECONDARY, lw=0.9, ls=":",
                                  label=f"정적 평균 {mean_cyl:.1f} kN (실린더) / {mean_pad:.1f} kN (패드)"),
                           Line2D([], [], color=ALERT, lw=1.1, ls="--", label=f"F_min {Fmin:.2f} kN (실린더 힘 기준)")],
                  loc="upper left", fontsize=7.8, frameon=False, ncol=1, bbox_to_anchor=(0.0, 1.0))
    ax_bar.set_title("현재 시각의 다리별 힘과 크롤러 총 반력", fontsize=10, loc="left", color=INK_PRIMARY)
    txt_box = ax_txt.text(0.0, 1.0, "", va="top", ha="left", fontsize=8.3, color=INK_PRIMARY,
                          family=fp.get_name(), linespacing=1.45, transform=ax_txt.transAxes)

    # header
    fig.text(0.012, 0.975, "아우트리거 4개 동시 신장 0 → 680 mm (22.67 mm/s) · 강체 평지 · 다리·크롤러 유연(L1) 준정적 · "
             "오거 상단(경우 C)", fontsize=12.5, weight="bold", color=INK_PRIMARY, va="top")
    fig.text(0.988, 0.975, f"{args.speedup:g}배속", fontsize=12.5, weight="bold", color=ALERT, va="top", ha="right")
    h_line1 = fig.text(0.012, 0.935, "", fontsize=10.5, color=INK_PRIMARY, va="top")
    h_line3 = fig.text(0.012, 0.865, "", fontsize=10.5, color=INK_PRIMARY, va="top")
    h_banner = fig.text(0.012, 0.832, "", fontsize=10.5, weight="bold", color=ALERT, va="top")
    fig.text(0.988, 0.832, f"사건 시각은 이 유연 모델 기준. 강체 기구학 GIF(leg_extension.gif): 후방 접지 "
             f"{rigid_touch_rear:.3f} s, 전방 접지·크롤러 이탈 {rigid_touch_front:.3f} s",
             fontsize=7.8, color=INK_SECONDARY, va="top", ha="right")
    status_boxes = []
    x0 = 0.052
    fig.text(0.012, 0.9, "접지:", fontsize=10.5, color=INK_PRIMARY, va="center")
    for n in dm.LEG_NAMES:
        box = FancyBboxPatch((x0, 0.886), 0.07, 0.028, boxstyle="round,pad=0.002,rounding_size=0.006",
                             transform=fig.transFigure, fc=LEG_COLORS[n], ec=LEG_COLORS[n], lw=1.6)
        fig.patches.append(box)
        tx = fig.text(x0 + 0.035, 0.9, "", fontsize=9, ha="center", va="center", weight="bold")
        status_boxes.append((n, box, tx))
        x0 += 0.078
    cr_txt = fig.text(x0 + 0.01, 0.9, "", fontsize=10.5, color=INK_PRIMARY, va="center")

    frames, durations, idx_frames = [], [], []
    for t, dur, banner in plan:
        s = model.solve(np.full(4, min(model.v * t, model.stroke)))
        e = s["e"][0]
        fp_ = s["F_pad"] * kN; fc_ = s["F_cyl"] * kN; fcr = s["F_cr_tot"] * kN
        cur_full.set_xdata([t, t]); cur_zoom.set_xdata([t, t])
        vals = list(fp_) + [fcr]
        for d1, d2, y in zip(dots_full, dots_zoom, vals):
            d1.set_data([t], [y]); d2.set_data([t], [y])
        for i in range(4):
            bars_pad[i].set_height(fp_[i]); bars_cyl[i].set_height(fc_[i])
            lab_pad[i].set_position((xs[i] - bw_ / 2, max(fp_[i], 0) + 2)); lab_pad[i].set_text(f"{fp_[i]:.1f}")
            lab_cyl[i].set_position((xs[i] + bw_ / 2, max(fc_[i], 0) + 2)); lab_cyl[i].set_text(f"{fc_[i]:.1f}")
        bar_cr[0].set_height(fcr)
        lab_cr.set_position((4.6, fcr + 2)); lab_cr.set_text(f"{fcr:.1f}")
        q = s["q"]
        h_line1.set_text(f"경과 시간 t = {t:6.2f} s (실제)      신장량 e = {e * 1e3:6.1f} mm (4다리 동일)      "
                         f"상부체 원점 높이 변화 uz = {q[0] * 1e3:+7.1f} mm")
        for i, (n, box, tx) in enumerate(status_boxes):
            if s["pad_contact"][i]:
                box.set_facecolor(LEG_COLORS[n]); tx.set_color("white"); tx.set_text(f"{n} 접지")
            else:
                box.set_facecolor(SURFACE); tx.set_color(LEG_COLORS[n]); tx.set_text(f"{n} 공중")
        cr_txt.set_text(("크롤러 접지" if s["crawler_contact"] else "크롤러 들림") +
                        f"  (최저점 높이 {max(s['crawler_clearance'], 0.0) * 1e3:5.1f} mm)")
        h_line3.set_text(f"roll = {math.degrees(q[1]) + 0.0:+.3f}°    pitch = {math.degrees(q[2]) + 0.0:+.3f}° "
                         f"(+ = 앞 내림)    ΣF(패드+크롤러) = {(s['F_pad'].sum() + s['F_cr_tot']) * kN:.1f} kN "
                         f"(총 중량 {model.W_tot * kN:.1f} kN)")
        h_banner.set_text(banner or "")
        p_bar = np.maximum(s["F_cyl"], 0.0) / model.A_head / 1e5
        lines = ["헤드 압력 환산 [bar]", "  p = max(F_cyl,0) / A_head"]
        for i, n in enumerate(dm.LEG_NAMES):
            lines.append(f"  {n}: {p_bar[i]:6.1f}")
        lines += ["", f"로드·패드 무게 {model.W_rod[0] * kN:.3f} kN/다리",
                  "공중 다리: 실린더 힘 = -로드 무게", "(로드측이 매단 무게를 받음)",
                  "", "가정: 다리 축 강성 kn(L1),", "크롤러 D안(롤러 2×6 + 끝 슈 틈), 준정적,",
                  "실 마찰·관성 무시"]
        txt_box.set_text("\n".join(lines))
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, facecolor=SURFACE)
        buf.seek(0)
        frames.append(Image.open(buf).convert("RGB"))
        durations.append(int(round(dur / 10.0)) * 10)
        idx_frames.append({"t_s": round(t, 4), "duration_ms": durations[-1], "banner": banner})
    plt.close(fig)

    sample_ids = [0, len(frames) // 2, len(frames) - 1]
    sample = Image.new("RGB", (frames[0].width * len(sample_ids), frames[0].height + 40))
    for k, i in enumerate(sample_ids):
        sample.paste(frames[i], (k * frames[0].width, 0))
    sw = [LEG_COLORS[n] for n in dm.LEG_NAMES] + [CRAWLER_COLOR, ALERT, INK_PRIMARY, INK_SECONDARY, "white", SURFACE]
    w_ = sample.width // len(sw)
    for k, c in enumerate(sw):
        sample.paste(Image.new("RGB", (w_, 40), c), (k * w_, frames[0].height))
    palette = sample.quantize(colors=args.colors, method=Image.Quantize.MEDIANCUT)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    OUT_GIF.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(OUT_GIF, save_all=True, append_images=indexed[1:], duration=durations, loop=0,
                    optimize=False, disposal=1)
    if args.preview_dir:
        pdir = Path(args.preview_dir); pdir.mkdir(parents=True, exist_ok=True)
        picks = {"start": 0, "end": len(frames) - 1}
        for j, f in enumerate(idx_frames):
            if f["banner"]:
                picks[f"event_{j}"] = j
        for name, j in picks.items():
            frames[j].save(pdir / f"frame_{name}_t{idx_frames[j]['t_s']:.3f}.png")
    return {"frames": len(indexed), "resolution_px": list(indexed[0].size), "loop_s": sum(durations) / 1000,
            "event_frames": event_times, "frame_list": idx_frames, "palette_colors": args.colors}


# ---------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--speedup", type=float, default=3.0)
    ap.add_argument("--fps", type=float, default=12.5)
    ap.add_argument("--hold-start-s", type=float, default=1.0)
    ap.add_argument("--hold-end-s", type=float, default=1.5)
    ap.add_argument("--hold-event-s", type=float, default=0.6)
    ap.add_argument("--width-px", type=int, default=1400)
    ap.add_argument("--colors", type=int, default=256)
    ap.add_argument("--zoom", type=float, nargs=2, default=[14.8, 17.2])
    ap.add_argument("--preview-dir", type=str, default="")
    ap.add_argument("--no-gif", action="store_true")
    args = ap.parse_args()
    t_start = time.perf_counter()

    p = dm.load_params()
    model = LiftModel(p)
    v, stroke = model.v, model.stroke
    t_end = stroke / v

    def sched_full(t):
        return np.full(4, min(v * t, stroke))

    # ---------------- (1) V4 reproduction: legs stop at the operating extension
    e_op = np.array([float(p["contact"]["rigid_floor"]["L1"]["derivation"]["operating_extension_m"][n])
                     for n in dm.LEG_NAMES])

    def sched_v4(t):
        return np.minimum(v * t, e_op)

    ref = json.loads(REF_JSON.read_text(encoding="utf-8"))
    v4 = ref["lift_V4_compliant_crawler"]["layouts"][V4_LAYOUT_D]
    t_v4_end = float((e_op / v).max())
    ev_v4 = events(model, sched_v4, t_v4_end)
    s_v4 = model.solve(e_op)
    ref_touch = v4["quasi_static_events_s"]["touch_s (FL, FR, RL, RR)"]
    our_touch = [ev_v4[f"touch_{n}"] for n in dm.LEG_NAMES]
    ref_F = np.array(v4["end_state (after the last stop)"]["pad_contact_force_N"])
    yaml_static = np.array([float(p["superstructure"]["auger_levels"][LEVEL]["static_leg_loads_N"][n])
                            for n in dm.LEG_NAMES])
    check_v4 = {
        "schedule": "e_i(t) = min(v t, operating_extension_m_i) (YAML contact.rigid_floor.L1.derivation)",
        "touch_s (FL, FR, RL, RR) this / reference": [r(our_touch, 6), ref_touch],
        "touch_max_abs_diff_s": r(float(np.max(np.abs(np.array(our_touch) - ref_touch))), 3),
        "crawler_off_s this / reference": [r(ev_v4["crawler_off"], 6), v4["quasi_static_events_s"]["crawler_fully_off_s"]],
        "end_pad_force_N this / reference": [r(s_v4["F_pad"], 7), ref_F.tolist()],
        "end_pad_force_max_rel_diff": r(float(np.max(np.abs(s_v4["F_pad"] - ref_F) / ref_F)), 3),
        "end_cyl_force_N this / YAML static_leg_loads_N (equal-k superstructure)": [r(s_v4["F_cyl"], 7), yaml_static.tolist()],
        "end_cyl_vs_yaml_max_rel_diff": r(float(np.max(np.abs(s_v4["F_cyl"] - yaml_static) / yaml_static)), 3),
        "end_attitude_deg this / reference": [r(np.degrees(s_v4["q"][1:]), 5), v4["end_state (after the last stop)"]["attitude_deg (roll, pitch)"]],
        "end_crawler_min_clearance_mm this / reference": [r(s_v4["crawler_clearance"] * 1e3, 6),
                                                         v4["end_state (after the last stop)"]["crawler_min_clearance_mm"]],
        "note": "reference rounds to 5 significant digits; end_cyl vs YAML differs because YAML uses equal leg stiffness (front/rear kn differ by 2 %)",
    }

    # ---------------- full stroke time series
    ev = events(model, sched_full, 17.0)   # nothing switches after the crawler is off (checked below)
    tt = np.round(np.arange(0.0, t_end + 1e-9, 0.01), 6)
    tt = np.unique(np.concatenate([tt, np.round(np.arange(14.8, 16.2, 0.001), 6)]))
    st = [model.solve(sched_full(t)) for t in tt]
    F_pad = np.array([s["F_pad"] for s in st]); F_cyl = np.array([s["F_cyl"] for s in st])
    F_cr = np.array([s["F_cr_tot"] for s in st]); Q = np.array([s["q"] for s in st])
    act = np.array([s["active_all"] for s in st]); gaps = np.array([s["gap_all"] for s in st])
    F_all = np.array([s["F_all"] for s in st])
    clr = np.array([s["crawler_clearance"] for s in st])
    switch_after_17 = bool((act[tt >= 17.0] != act[tt >= 17.0][0]).any())

    # ---------------- (2) end-state equilibrium
    s_end = st[-1]
    xy = model.geo.pad_xy
    Fz = s_end["F_pad"].sum() + s_end["F_cr_tot"]
    Mx = s_end["F_all"] @ model.xy_all[:, 1]; My = -(s_end["F_all"] @ model.xy_all[:, 0])
    eq = {
        "sum_F_pad_N": r(Fz, 9), "total_weight_N (superstructure + 4 moving parts)": r(model.W_tot, 9),
        "rel_err_force": r(abs(Fz - model.W_tot) / model.W_tot, 3),
        "moment_about_x_rel_err (sum F y vs W cg_y)": r(abs(Mx - model.W_tot * model.cg[1]) / (model.W_tot * 1.0), 3),
        "moment_about_y_rel_err (sum -F x vs -W cg_x)": r(abs(My + model.W_tot * model.cg[0]) / (model.W_tot * 1.0), 3),
        "moment_reference_length_m": 1.0,
        "cylinder_basis: sum F_cyl vs superstructure weight": [r(s_end["F_cyl"].sum(), 9), r(model.W_super, 9)],
        "cylinder_basis_moment_about_x_rel_err": r(abs(s_end["F_cyl"] @ xy[:, 1] - model.W_super * model.body.com[1]) / model.W_super, 3),
        "cylinder_basis_moment_about_y_rel_err": r(abs(s_end["F_cyl"] @ xy[:, 0] - model.W_super * model.body.com[0]) / model.W_super, 3),
    }
    # all frames: force balance
    bal = np.abs(F_all.sum(1) - model.W_tot).max() / model.W_tot

    # ---------------- (3) unilateral contact
    uni = {
        "min_pad_force_N": r(float(F_pad.min()), 6),
        "min_crawler_sphere_force_N": r(float(F_all[:, 4:].min()), 6),
        "max_gap_violation_active_m (active spring with open gap)": r(float(np.max(np.where(act, gaps, -np.inf))), 3),
        "min_gap_inactive_m (inactive spring penetrating if < 0)": r(float(np.min(np.where(~act, gaps, np.inf))), 3),
        "max_force_balance_rel_err_all_samples": r(float(bal), 3),
    }

    # ---------------- independent energy minimisation at several times
    t_chk = [10.0, ev["touch_RR"] + 0.05, ev["touch_FL"] + 0.05, 0.5 * (ev["touch_FL"] + ev["crawler_off"]),
             ev["crawler_off"] + 0.1, 25.0, t_end]
    emin = []
    for t in t_chk:
        F_ind = energy_min_check(model, sched_full(t))
        F_as = model.solve(sched_full(t))["F_all"]
        emin.append({"t_s": r(t, 6), "max_abs_diff_N": r(float(np.abs(F_ind - F_as).max()), 3),
                     "rel_to_W": r(float(np.abs(F_ind - F_as).max() / model.W_tot), 3)})

    # ---------------- (5) quasi-static check (damped dynamics through the transition)
    dyn = dynamic_check(model, 14.5, 20.0, sched_full)
    dyn_arrays = dyn.pop("_arrays")

    # ---------------- leg damping sensitivity of the dynamic check (c_pad scales with zeta: c = 2 zeta sqrt(k m/4))
    zeta_sens = {"description": ("dynamic check repeated with the pad dashpots scaled to leg zeta (heave basis); crawler "
                                 "damping kept at the YAML value; F_min margin = min over legs of the cylinder force after "
                                 "it first reaches F_min, minus F_min"),
                 "crawler_zeta": model.zeta_crawler, "cases": {}}
    c_yaml = model.c_pad.copy()
    for z in (0.01, model.zeta_leg, 0.10):
        model.c_pad = c_yaml * (z / model.zeta_leg)
        dz = dyn if z == model.zeta_leg else dynamic_check(model, 14.5, 20.0, sched_full)
        dz.pop("_arrays", None)
        pl = dz["per_leg"]
        fmin_after = [pl[n]["cyl_force_min_after_first_reaching_F_min_N"] for n in dm.LEG_NAMES]
        peak = [pl[n]["peak_pad_force_N"] for n in dm.LEG_NAMES]
        zeta_sens["cases"][f"zeta_leg_{z:g}"] = {
            "c_pad_N_s_m": r(model.c_pad, 6),
            "peak_pad_force_N (FL, FR, RL, RR)": r(peak, 6),
            "max_peak_pad_force_N": r(max(peak), 6),
            "max_peak_cylinder_force_N": r(max(peak[i] - model.W_rod[i] for i in range(4)), 6),
            "max_over_quasi_static_N": r(max(pl[n]["max_over_quasi_static_N"] for n in dm.LEG_NAMES), 5),
            "max_abs_diff_vs_quasi_static_N": r(float(max(dz["max_abs_diff_pad_N (FL, FR, RL, RR)"])), 5),
            "cyl_force_min_after_first_reaching_F_min_N (FL, FR, RL, RR)": r(fmin_after, 6),
            "F_min_margin_N": r(min(fmin_after) - model.F_min_cyl, 4),
            "contact_lost_samples_after_touch": sum(pl[n]["contact_lost_samples_after_touch"] for n in dm.LEG_NAMES),
            "last_time_diff_above_1pct_of_mean_s": dz["last_time_diff_above_1pct_of_mean_s"],
            "max_step_convergence_N": dz["solver"]["max_abs_force_diff_vs_max_step_5e-4_N"],
        }
    model.c_pad = c_yaml

    # ---------------- crawler kn_total x3 sensitivity (user decision 2026-10-20: kn_total kept, x3 as sensitivity;
    # crawler dashpot x sqrt(3) so the crawler heave zeta stays; pads unchanged)
    def dyn_summary(dz, mdl):
        pl = dz["per_leg"]
        fmin_after = [pl[n]["cyl_force_min_after_first_reaching_F_min_N"] for n in dm.LEG_NAMES]
        peak = [pl[n]["peak_pad_force_N"] for n in dm.LEG_NAMES]
        return {"first_touch_dyn_s (FL, FR, RL, RR)": [pl[n]["first_touch_dyn_s"] for n in dm.LEG_NAMES],
                "peak_pad_force_N (FL, FR, RL, RR)": r(peak, 6),
                "peak_at_s (FL, FR, RL, RR)": [pl[n]["peak_at_s"] for n in dm.LEG_NAMES],
                "max_peak_pad_force_N": r(max(peak), 6),
                "max_peak_cylinder_force_N": r(max(peak[i] - mdl.W_rod[i] for i in range(4)), 6),
                "cyl_force_min_after_first_reaching_F_min_N (FL, FR, RL, RR)": r(fmin_after, 6),
                "F_min_margin_N": r(min(fmin_after) - mdl.F_min_cyl, 4),
                "contact_lost_samples_after_touch": sum(pl[n]["contact_lost_samples_after_touch"] for n in dm.LEG_NAMES),
                "max_step_convergence_N": dz["solver"]["max_abs_force_diff_vs_max_step_5e-4_N"]}

    s3 = dm.crawler_kn_scales(p)[-1]
    m3 = LiftModel(p, kn_scale=s3)
    ev3_v4 = events(m3, sched_v4, t_v4_end)
    ev3 = events(m3, sched_full, 17.0)
    st3 = [m3.solve(sched_full(t)) for t in tt]
    F_pad3 = np.array([s["F_pad"] for s in st3]); F_cyl3 = np.array([s["F_cyl"] for s in st3])
    d3 = dynamic_check(m3, 14.5, 20.0, sched_full)
    d3.pop("_arrays")
    v4_k3 = ref["lift_V4_compliant_crawler"]["layouts"][V4_LAYOUT_D_K3]
    touch3 = [ev3_v4[f"touch_{n}"] for n in dm.LEG_NAMES]
    s3_0 = m3.solve(np.zeros(4))
    crawler_k3 = {
        "description": ("crawler kn_total x %g (contact.crawler.kn_total_sensitivity_range_N_m), crawler dashpot x sqrt(%g) "
                        "(same heave zeta), layout D, pads and everything else unchanged" % (s3, s3)),
        "kn_total_N_m": r(float(p["contact"]["crawler"]["kn_total_N_m"]) * s3, 9),
        "kn_per_sphere_N_m": r(float(m3.cr_k[0]), 9), "c_per_sphere_N_s_m": r(float(m3.cr_c[0]), 7),
        "settled_q_about_origin (uz_mm, roll_deg, pitch_deg)": r([s3_0["q"][0] * 1e3, math.degrees(s3_0["q"][1]),
                                                                   math.degrees(s3_0["q"][2])], 5),
        "V4_reproduction: touch_s (FL, FR, RL, RR) this / reference.json": [r(touch3, 6),
                                                                           v4_k3["quasi_static_events_s"]["touch_s (FL, FR, RL, RR)"]],
        "V4_touch_max_abs_diff_s": r(float(np.max(np.abs(np.array(touch3) - v4_k3["quasi_static_events_s"]["touch_s (FL, FR, RL, RR)"]))), 3),
        "V4_touch_minus_nominal_s (FL, FR, RL, RR)": r([touch3[i] - our_touch[i] for i in range(4)], 4),
        "events_full_stroke_s": r(ev3, 7),
        "quasi_static_max_pad_reaction_N": r(float(F_pad3.max()), 7),
        "quasi_static_max_over_time_per_leg_N": r(F_pad3.max(0), 7),
        "quasi_static_F_min_check": {n: {"after_touch_below_F_min_until_s": r(ev3[f"F_min_reached_{n}"], 6),
                                         "duration_after_touch_s": r(ev3[f"F_min_reached_{n}"] - ev3[f"touch_{n}"], 4)}
                                     for n in dm.LEG_NAMES},
        "max_cylinder_force_over_extend_limit (per leg, 210 bar x A_p)": r(float(np.max(F_cyl3 / m3.F_ext_max)), 4),  # rev. 30: was max_cylinder_force_vs_218kN
        "dynamic (damped 3-DoF, 14.5-20 s)": dyn_summary(d3, m3),
        "dynamic_nominal_kn_for_comparison": dyn_summary(dyn, model),
    }

    # ---------------- stiffness sensitivity: oil column stiffness varying with the extension
    act_p = p["actuator"]
    beta, dead = float(act_p["oil_bulk_modulus_eff_Pa"]), float(act_p["oil_dead_length_m"])
    k_oil = lambda e: beta * model.A_head / (dead + e)  # noqa: E731

    def k_var(e):
        return 1.0 / (1.0 / model.k_pad + 1.0 / k_oil(e) - 1.0 / k_oil(e_op))

    m_var = LiftModel(p, k_pad=k_var(np.full(4, stroke)))
    s_var = m_var.solve(np.full(4, stroke))
    sens = {
        "description": "kn(e) = 1/(1/kn_yaml + 1/k_oil(e) - 1/k_oil(e_op)), k_oil = beta A_head/(dead + e) (YAML actuator), evaluated at e = stroke",
        "kn_at_stroke_N_m": r(k_var(np.full(4, stroke)), 6),
        "end_pad_force_N": r(s_var["F_pad"], 7),
        "diff_vs_constant_kn_N": r(s_var["F_pad"] - s_end["F_pad"], 4),
        "end_pitch_deg": r(math.degrees(s_var["q"][2]), 5),
    }

    # ---------------- rigid kinematic GIF comparison
    kin = json.loads(KIN_JSON.read_text(encoding="utf-8"))["gif_schedule"]
    kt = kin["touch_s (FL, FR, RL, RR)"]
    rigid_ev = {"touch_rear_s": float(kt[2]), "touch_front_s": float(kt[0]), "crawler_off_s": float(kin["crawler_off_s"])}
    s0 = model.solve(np.zeros(4))
    gap0 = model.touch + model.A_pad @ s0["q"]
    cmp_rigid = {
        "rows (quantity, this compliant model, rigid kinematic GIF, diff s)": [
            [f"touch {n} [s]", r(ev[f"touch_{n}"], 6), kt[i], r(ev[f"touch_{n}"] - kt[i], 4)]
            for i, n in enumerate(dm.LEG_NAMES)] + [
            ["crawler off [s]", r(ev["crawler_off"], 6), rigid_ev["crawler_off_s"], r(ev["crawler_off"] - rigid_ev["crawler_off_s"], 4)],
            ["end uz [mm]", r(s_end["q"][0] * 1e3, 6), kin["end_state"]["uz_mm"], r(s_end["q"][0] * 1e3 - kin["end_state"]["uz_mm"], 4)],
            ["end pitch [deg]", r(math.degrees(s_end["q"][2]), 5), kin["end_state"]["pitch_deg"], r(math.degrees(s_end["q"][2]) - kin["end_state"]["pitch_deg"], 4)],
            ["end crawler min clearance [mm]", r(s_end["crawler_clearance"] * 1e3, 6), kin["end_state"]["crawler_min_clearance_mm"],
             r(s_end["crawler_clearance"] * 1e3 - kin["end_state"]["crawler_min_clearance_mm"], 4)],
        ],
        "initial_settled_on_crawler": {
            "uz_mm": r(s0["q"][0] * 1e3, 5), "roll_deg": r(math.degrees(s0["q"][1]), 4), "pitch_deg": r(math.degrees(s0["q"][2]), 4),
            "pad_gap_mm (FL, FR, RL, RR)": r(gap0 * 1e3, 5),
        },
        "pad_compression_at_end_mm": r(s_end["F_pad"] / model.k_pad * 1e3, 5),
    }

    # ---------------- key values
    i_max = np.unravel_index(np.argmax(F_pad), F_pad.shape)
    after = tt >= ev["crawler_off"] + 1e-6
    below = {}
    for i, n in enumerate(dm.LEG_NAMES):
        m_ = (F_cyl[:, i] < model.F_min_cyl) & (tt > ev[f"touch_{n}"])
        below[n] = {"after_touch_below_F_min_until_s": r(ev[f"F_min_reached_{n}"], 6),
                    "duration_after_touch_s": r(ev[f"F_min_reached_{n}"] - ev[f"touch_{n}"], 4),
                    "below_after_crawler_off": bool(((F_cyl[:, i] < model.F_min_cyl) & after).any()),
                    "samples_below_after_touch": int(m_.sum())}
    key = {
        "end_state (e = stroke, t = stroke / v_max)": {  # rev. 30: was "t = 30 s"
            "pad_reaction_N": r(s_end["F_pad"], 7), "cylinder_force_N": r(s_end["F_cyl"], 7),
            "head_pressure_bar": r(s_end["F_cyl"] / model.A_head / 1e5, 5),
            "crawler_total_N": r(s_end["F_cr_tot"], 4),
            "roll_deg": r(math.degrees(s_end["q"][1]), 5), "pitch_deg": r(math.degrees(s_end["q"][2]), 5),
            "uz_mm": r(s_end["q"][0] * 1e3, 6), "crawler_min_clearance_mm": r(s_end["crawler_clearance"] * 1e3, 6),
        },
        "max_pad_reaction_N": r(float(F_pad[i_max]), 7), "max_pad_reaction_leg": dm.LEG_NAMES[i_max[1]],
        "max_pad_reaction_first_reached_s": r(float(tt[np.argmax(F_pad[:, i_max[1]] >= F_pad[i_max] * (1 - 1e-9))]), 6),
        "max_over_time_per_leg_N": r(F_pad.max(0), 7),
        "pad_reaction_constant_after_crawler_off": r(float(np.abs(F_pad[after] - F_pad[after][-1]).max()), 3),
        "events_s": r(ev, 7),
        "F_min_cylinder_N": model.F_min_cyl, "F_min_pad_basis_N (F_min + rod weight)": r(model.F_min_cyl + model.W_rod, 7),
        "F_min_check": below,
        "max_cylinder_force_over_extend_limit (per leg, 210 bar x A_p)": r(float(np.max(F_cyl / model.F_ext_max)), 4),  # rev. 30: was max_cylinder_force_vs_218kN
        "mean_static_leg_load_N": {"cylinder (superstructure / 4)": r(model.W_super / 4, 7), "pad (incl. rod)": r(model.W_tot / 4, 7)},
        "active_set_switch_after_17s": switch_after_17,
    }

    out = {
        "meta": {
            "script": "04_scripts/01_dynamics/run_leg_extension_loads.py",
            "params": "02_params/rexome33.yaml",
            "auger_level": LEVEL, "mass_case": p["meta"]["mass_basis"]["case"] if "mass_basis" in p.get("meta", {}) else "C",
            "frame": "body: x forward, y left, z up; level body = world; origin = CAD origin; q = [uz, roll, pitch] about the origin",
            "gravity_m_s2": [0.0, 0.0, -model.g],
            "sign": "forces + = compression / floor pushes up; pitch + = nose down (rotation about +y); roll + = left side (+y) up (rotation about +x)",
            "time_origin": "t = 0 at motor start; e(t) = min(v t, stroke) on all four legs",
            "model": __doc__.split("Model (")[1].split("Outputs")[0].strip(),
            "inputs_from_yaml": {
                "kn_per_pad_N_m (contact.rigid_floor.L1)": r(model.k_pad, 9),
                "crawler kn_total_N_m / n spheres / n floor-contact (roller) spheres": [p["contact"]["crawler"]["kn_total_N_m"], len(model.cr_xy), int((model.cr_gap <= 0).sum())],
                "superstructure_mass_kg": r(model.body.mass, 9), "moving_part_mass_kg": r(model.geo.rod_mass, 9),
                "combined_cg_xy_m": r(model.cg, 7), "touch_extension_m": r(model.touch, 7),
                "head_area_m2": r(model.A_head, 7),
                "max_force_extend_N": model.F_ext_max if np.ndim(model.F_ext_max) == 0 else r(model.F_ext_max, 9),
            },
            "cylinder_force_definition": "F_cyl = F_pad - m_rod g (oil column force, + compression). Leg in the air: F_cyl = -m_rod g; head pressure sensor p = max(F_cyl,0)/A_head (rod side carries the hanging rod; seal friction neglected)",
        },
        "validation": {
            "V4_reproduction": check_v4,
            "end_equilibrium": eq,
            "unilateral_contact": uni,
            "energy_minimisation_independent (BFGS)": emin,
            "quasi_static_check (damped 3-DoF)": dyn,
            "quasi_static_check_leg_zeta_sensitivity": zeta_sens,
        },
        "stiffness_sensitivity_k_oil_of_extension": sens,
        "crawler_kn_total_x3_sensitivity": crawler_k3,
        "rigid_kinematic_gif_comparison": cmp_rigid,
        "key_values": key,
        "series": {
            "t_s": r(tt, 7),
            "F_pad_N": r(F_pad, 7), "F_cyl_N": r(F_cyl, 7), "F_crawler_total_N": r(F_cr, 7),
            "uz_mm": r(Q[:, 0] * 1e3, 6), "roll_deg": r(np.degrees(Q[:, 1]), 5), "pitch_deg": r(np.degrees(Q[:, 2]), 5),
            "crawler_min_clearance_mm": r(clr * 1e3, 6),
            "pad_contact": act[:, :4].astype(int).tolist(),
            "columns": "rows = time samples (0.01 s, plus 1 ms in 14.8-16.2 s); per-leg columns FL, FR, RL, RR",
        },
    }

    if not args.no_gif:
        series = {"t": tt, "F_pad": F_pad, "F_cyl": F_cyl, "F_cr_tot": F_cr}
        ref_lines = {"mean_cyl_N": model.W_super / 4, "mean_pad_N": model.W_tot / 4}
        t0 = time.perf_counter()
        gif = render_gif(model, series, ev, rigid_ev, args, ref_lines, dyn_arrays)
        gif["render_s"] = round(time.perf_counter() - t0, 1)
        gif["path"] = str(OUT_GIF.relative_to(dm.PROJECT_ROOT))
        gif["size_bytes"] = OUT_GIF.stat().st_size
        gif["playback"] = {"speedup": args.speedup, "fps_moving": args.fps, "hold_start_s": args.hold_start_s,
                           "hold_end_s": args.hold_end_s, "hold_event_s": args.hold_event_s}
        out["gif"] = gif
    out["meta"]["wall_s"] = round(time.perf_counter() - t_start, 1)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    summary = {k: ({kk: vv for kk, vv in val.items() if kk != "series_2ms"} if isinstance(val, dict) else val)
               for k, val in out["validation"].items()}
    print(json.dumps({"validation": summary, "sensitivity": sens, "crawler_x3": crawler_k3, "rigid": cmp_rigid, "key": key,
                      "gif": {k: v for k, v in out.get("gif", {}).items() if k != "frame_list"}},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
