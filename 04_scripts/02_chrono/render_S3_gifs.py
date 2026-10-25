"""Animated GIF and PNGs of the S3 runs (L1; stored results only, no simulation).

Reads (nothing is simulated; the inputs are not modified):
    07_results/S3/index.json -> <case>/{result.json, record/, energy.npz}
        v4_D_wdefault (Record; YAML dt 2e-4 s + 1e-5 s transition window), v4_D_w1e-04,
        v4_D_w2e-04, v4_D_u*, v4touch_dt*, v5, v5_default, v6_FLp, v6_FLm, v6_FLp_fast,
        v8a_pads_dt*, v8a_crawler_dt*, v9_step_dt*, v9_free_dt*
    06_analysis/01_chrono/13_S3/verify_S3_L1.json   automatic pre-check summary (rev. 17 rules)
    06_analysis/00_dynamics/s3_lift_check.json    independent checks (dynamics-expert)
    06_analysis/00_dynamics/reference.json        via outrigger_sim.verify.reference
    02_params/rexome33.yaml, CAD drawing meshes (as render_S2_gifs.py)
    --before: the verify_S3_L1.json written before the 2026-10-21 YAML regeneration (pre-check
        counts before / after in the dashboard); default
        06_analysis/01_chrono/13_S3/history/before_yaml_dt2e-4/

Writes (06_analysis/01_chrono/13_S3/):
    S3_lift_v4.gif        V4 lift from the crawler: settled on the crawler -> motors start
                          (ramp) -> per-leg touch -> crawler off -> ramped stop at e_op ->
                          15 s residual; 3D (true scale) + pad / cylinder / crawler forces,
                          ground gaps, attitude, touch table
    S3_lift_v4_frame.png  representative frame (crawler off)
    S3_v5_v6.png          V5 FL +1 / +5 mm and V6 FL +/- single-leg extension to F_min and
                          lift-off, against the reference and the independent exact statics
    S3_v8a_energy.png     V8(a) with every physical damping off: pads and crawler energy,
                          numerical zeta per mode, crawler modal zeta and 1-s trend (rev. 17)
    S3_v9_convergence.png V9: differences to the dt 1e-5 s run, error ratios, touch-time
                          definitions (geometric judged, R15 recorded with its bound)
    S3_summary.png        one-page dashboard (verdict table + YAML change + regression)
    S3_gifs.json          frame plan, sizes, value checks, sources

Conventions: body / world frame x forward, y left, z up; SI; roll / pitch ZYX in deg (pitch + =
nose down); legs FL, FR, RL, RR. V4 times are measured from the equivalent origin (start command
+ ramp / 2 + dt / 2, measured: result.json equivalent_origin_s), as in run_S3.py. Cylinder force
= pad contact force - rod weight (Record F_cyl). 3D: oblique orthographic CAD meshes at true
scale (x1); the body is drawn at its recorded translation (attitude change <= 0.2 deg is not
drawn), rods moved along the leg axis by the recorded motor position (layer composition, whole
pixels, as render_S2_gifs.render_v11). Normal force arrows 1 m per 100 kN at the pad contact.

CPU: E-cores at below-normal priority (render_S2_gifs.place_cpu); --cpu os disables this.

Usage (Chrono-dev python):
    python -I -u 04_scripts/02_chrono/render_S3_gifs.py [--only NAME ...] [--mesh-cache DIR]
        [--before PATH]
    NAME: lift, v5v6, v8a, v9, summary (default: all)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "03_src"))

import render_S1_gifs as s1  # noqa: E402
import render_S2_gifs as s2  # noqa: E402  (meshes, layers, GIF writer, fonts)
from render_S2_gifs import (  # noqa: E402
    ACCENT,
    BAND_COLOR,
    EARTH_COLOR,
    INK_PRIMARY,
    INK_SECONDARY,
    LEG_COLORS,
    LEG_ORDER,
    LIN_COLOR,
    SURFACE,
    VIEWS,
    MeshBank,
    Scene,
    axes_box,
    banner_text,
    header_texts,
    load_drawing_meshes,
    new_figure,
    plane_split,
    read_json,
    rel,
    render_scene,
    scene_limits_for,
    scr,
    set_arrow,
    set_banner,
    text_block,
    write_gif,
)

from outrigger_sim.frames import roll_pitch_from_quat  # noqa: E402
from outrigger_sim.geometry import extension_direction, pad_sphere_centre_body_m  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402
from outrigger_sim.record import load_record  # noqa: E402
from outrigger_sim.scenarios.crawler_settle import crawler_layout  # noqa: E402

RES = ROOT / "07_results" / "S3"
INDEX = RES / "index.json"
OUT_DIR = ROOT / "06_analysis" / "01_chrono" / "13_S3"
VERIFY = OUT_DIR / "verify_S3_L1.json"
DEFAULT_BEFORE_VERIFY = OUT_DIR / "history" / "before_yaml_dt2e-4" / "verify_S3_L1.json"
LIFT_CHECK = ROOT / "06_analysis" / "00_dynamics" / "s3_lift_check.json"
OUT = {
    "lift": OUT_DIR / "S3_lift_v4.gif",
    "lift_frame": OUT_DIR / "S3_lift_v4_frame.png",
    "v5v6": OUT_DIR / "S3_v5_v6.png",
    "v8a": OUT_DIR / "S3_v8a_energy.png",
    "v9": OUT_DIR / "S3_v9_convergence.png",
    "summary": OUT_DIR / "S3_summary.png",
    "json": OUT_DIR / "S3_gifs.json",
}
ALL_PARTS = ("lift", "v5v6", "v8a", "v9", "summary")
LIFT_CASE = "v4_D_wdefault"
"""Lift Record drawn: the default-dt regression run (YAML simulation.L1.dt_s 2e-4 s + the
1e-5 s transition window); the earlier judged runs keep the old params_sha256 (Records of
another parameter file are refused by load_record)."""
SAMPLE_S = 1.0e-3
"""Record sample period of the S3 lift (run_S3.SAMPLE_S); the first sample is one period
after the run start."""
CRAWLER_COLOR = "#3b3b3b"
REF_COLOR = "#7d7c78"
INDEP_COLOR = "#5f7fb3"
DT_COLORS = {2.0e-4: "#c0392b", 1.0e-4: "#1f6fb2", 5.0e-5: "#2e8b57", 1.0e-5: "#3b3b3b"}
ARROW_N_M_PER_N = 1.0 / 100e3
LIFT_BOX = (8, 96, 560, 796)
# Placeholder 218.125 kN = the old common CAD cylinder value (removed from the YAML in the bundle
# 2026-10-25); main() overwrites both from legs.<leg>.cylinder.max_force_extend_N (REXOME35).
F_MAX_MOVING_KN = 218.125
F_MAX_MOVING_LEG_KN = [F_MAX_MOVING_KN] * 4
"""Per-leg moving saturation [kN] (LEG_ORDER); main() sets it (legs.<leg>.cylinder.*)."""


def draw_moving_limits(ax, x_text=None) -> None:
    """Moving saturation line(s): one line while every leg has the same limit (the figure of
    the common-limit YAML, unchanged), else one line per leg in the leg colour."""
    if all(v == F_MAX_MOVING_LEG_KN[0] for v in F_MAX_MOVING_LEG_KN):
        ax.axhline(F_MAX_MOVING_KN, color=ACCENT, lw=1.0)
        if x_text is not None:
            ax.text(x_text, F_MAX_MOVING_KN - 4,
                    f"이동 중 포화 {F_MAX_MOVING_KN:.1f} kN (210 bar)", color=ACCENT,
                    fontsize=7.5, va="top")
        return
    for leg, value in zip(LEG_ORDER, F_MAX_MOVING_LEG_KN, strict=True):
        ax.axhline(value, color=LEG_COLORS[leg], lw=1.0, ls="--")
    if x_text is not None:
        ax.text(x_text, min(F_MAX_MOVING_LEG_KN) - 4, "이동 중 포화 (210 bar, 다리별)",
                color=ACCENT, fontsize=7.5, va="top")

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# --- data ------------------------------------------------------------------------------------


def index() -> dict:
    return read_json(INDEX)


def result(case: str) -> dict:
    return read_json(ROOT / index()[case] / "result.json")


def case_dir(case: str) -> Path:
    return ROOT / index()[case]


def style(ax, title=None, xlabel=None, ylabel=None):
    s1.style_axes(ax, title=title, xlabel=xlabel, ylabel=ylabel)


def save_png(fig, path: Path):
    s1.save_atomic(path, lambda target: fig.savefig(target, dpi=fig.dpi, facecolor=SURFACE,
                                                    format="png"))
    plt.close(fig)
    with Image.open(path) as im:
        return {"path": rel(path), "resolution_px": list(im.size),
                "size_bytes": path.stat().st_size}


# =============================================================================================
# V4 lift GIF
# =============================================================================================


class Lift:
    """V4 Record on the equivalent-origin clock."""

    def __init__(self):
        self.params = load_params(level="top")
        self.res = result(LIFT_CASE)
        rec = load_record(case_dir(LIFT_CASE) / "record", params_sha256=self.params.sha256)
        self.meta = rec.run_meta
        a = {k: np.asarray(v) for k, v in rec.arrays.items()}
        self.a = a
        t_abs = np.asarray(a["t"], float)
        self.t_run0 = float(t_abs[0] - SAMPLE_S)
        self.t_eq0 = float(self.res["equivalent_origin_s"]["measured"])
        self.te = t_abs - self.t_run0 - self.t_eq0
        ev = rec.bushing_events
        self.events = [(float(t) - self.t_run0 - self.t_eq0, int(leg), int(kind))
                       for t, leg, kind in zip(ev["t"], ev["leg"], ev["kind"], strict=True)]
        self.pos = np.asarray(a["body_pos"], float)
        self.rot = s2.quat_to_matrix(a["body_quat_wxyz"])
        rp = np.array([roll_pitch_from_quat(q) for q in a["body_quat_wxyz"]])
        self.att_deg = np.degrees(rp)
        p = self.params
        self.floor_z = p.ground.crawler_bottom_z_m
        self.direction = extension_direction(p)
        base = np.array([pad_sphere_centre_body_m(p, k, 0.0) for k in range(4)])
        self.radius = np.array([leg.pad.swivel_center_above_pad_bottom_m for leg in p.legs])
        s = np.asarray(a["s_motor"], float)
        centres_body = base[None, :, :] + s[:, :, None] * self.direction[None, None, :]
        centres = np.einsum("nij,nkj->nki", self.rot, centres_body) + self.pos[:, None, :]
        self.pad_centres = centres
        self.pad_gap_mm = (centres[:, :, 2] - self.radius - self.floor_z) * 1e3
        layout = crawler_layout(p)
        cb = layout.centres_body_m(self.floor_z)
        cw = np.einsum("nij,kj->nki", self.rot, cb) + self.pos[:, None, :]
        self.crawler_gap_mm = (cw[:, :, 2].min(axis=1) - layout.sphere_radius_m
                               - self.floor_z) * 1e3
        self.N_kN = np.asarray(a["F_contact_n"], float) / 1e3
        self.Fcyl_kN = np.asarray(a["F_cyl"], float) / 1e3
        self.Fcr_kN = np.asarray(a["F_crawler"], float)[:, 2] / 1e3
        self.s_mm = s * 1e3
        self.u_mm = np.asarray(a["u_applied"], float) * 1e3
        plan = self.res["plan"]
        self.plan = plan
        self.stop_eq = [st - self.t_eq0 for st in plan["stop_s"]]
        self.last_stop_eq = plan["last_stop_s"] - self.t_eq0
        self.touch_eq = np.asarray(self.res["touch_eq_s"], float)
        self.touch_ref = np.asarray(self.res["touch_ref_dynamic_s"], float)
        self.off_eq = float(self.res["crawler_off_eq_s"])
        self.off_ref = float(self.res["crawler_off_ref_dynamic_s"])
        indep = read_json(LIFT_CHECK)["D_V4_6dof_dynamic"]["x1_bushing"]
        self.touch_indep = np.asarray(indep["touch_s"], float)
        self.off_indep = float(indep["crawler_off_force_zero_s"])

    def index(self, te):
        return int(np.clip(np.searchsorted(self.te, te - 1e-12), 0, len(self.te) - 1))

    def checks(self) -> dict:
        """Recomputed values against result.json (same Record, other path)."""
        created = sorted((t, leg) for t, leg, kind in self.events if kind == 1)
        touch_from_events = np.full(4, np.nan)
        for t, leg in created:
            touch_from_events[leg] = t
        first_n = np.array([self.te[np.flatnonzero(self.N_kN[:, k] > 0)[0]] for k in range(4)])
        mw = self.res["final"]["mean_window_s"]
        m = (self.te + self.t_eq0 >= mw[0]) & (self.te + self.t_eq0 <= mw[1])
        return {
            "touch_eq_events_minus_result_s": (touch_from_events - self.touch_eq).tolist(),
            "first_sample_N_gt_0_minus_touch_s (sample 1 ms)": (first_n - self.touch_eq).tolist(),
            "final_N_mean_minus_result_N": (self.N_kN[m].mean(axis=0) * 1e3
                                            - np.asarray(self.res["final"]["contact_force_N"]))
            .tolist(),
            "peak_pad_N_record_minus_result_N (1 ms samples)": (self.N_kN.max(axis=0) * 1e3
                                                                - np.asarray(
                                                                    self.res["peak_pad_force_N"]))
            .tolist(),
            "attitude_range_deg (roll, pitch)": np.ptp(self.att_deg, axis=0).tolist(),
            "body_rise_m": float(self.pos[-1, 2] - self.pos[0, 2]),
            "pad_gap_end_mm": self.pad_gap_mm[-1].tolist(),
            "crawler_min_gap_end_mm": float(self.crawler_gap_mm[-1]),
            "crawler_min_gap_end_result_mm": float(self.res["crawler_min_gap_end_mm"]),
        }


def lift_layers(bank, lift: Lift, limits, size):
    """Background + body + per-leg barrel / rod layers at the first recorded pose (legs 0)."""
    params = lift.params
    pos, rot = lift.pos[0], lift.rot[0]
    items = bank.items(params, np.zeros(4))
    background = render_scene([], [], limits, size, floor=((0, 0, lift.floor_z), (0, 0, 1.0)))
    body = [it for it in items if it[5] == "body"]
    layers = [("body", None, render_scene(*plane_split(body, pos, rot, (0, 0, lift.floor_z),
                                                       (0, 0, 1.0)), limits, size))]
    toward = VIEWS["oblique"][2]
    depth = {leg.name: float(np.array(leg.pad_bottom_center_retracted_m) @ toward)
             for leg in params.legs}
    for leg in sorted(LEG_ORDER, key=lambda n: depth[n]):
        for kind in ("rod", "barrel"):
            group = [it for it in items if it[5] == kind and it[6] == leg]
            layers.append((kind, leg, render_scene(*plane_split(group, pos, rot,
                                                                (0, 0, lift.floor_z),
                                                                (0, 0, 1.0)), limits, size)))
    return background, layers


def compose(background, layers, body_px, rod_px):
    frame = background.copy()
    for kind, leg, layer in layers:
        dx, dy = rod_px[leg] if kind == "rod" else body_px
        moved = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        moved.paste(layer, (dx, dy))
        frame = Image.alpha_composite(frame, moved)
    return frame


def lift_frame_times(lift: Lift):
    """(te, duration ms, banner) per frame."""
    touch = lift.touch_eq
    banners = {}
    for group, legs in (("전방", (0, 1)), ("후방", (2, 3))):
        tg = float(np.mean(touch[list(legs)]))
        names = "·".join(LEG_ORDER[k] for k in legs)
        diffs = ", ".join(f"{LEG_ORDER[k]} {(touch[k] - lift.touch_ref[k]) * 1e3:+.1f} ms"
                          for k in legs)
        banners[round(tg + 0.002, 3)] = f"{group} {names} 접지 (기준 대비 {diffs})"
    banners[round(lift.off_eq + 0.002, 3)] = (f"크롤러 이탈 {lift.off_eq:.3f} s "
                                              f"(기준 {lift.off_ref:.3f} s, 6자유도+부싱 "
                                              f"{lift.off_indep:.3f} s)")
    for legs, st in ((("RL", "RR"), lift.stop_eq[2]), (("FL", "FR"), lift.stop_eq[0])):
        banners[round(st + 0.02, 3)] = f"{'·'.join(legs)} 운용 신장 e_op 정지 (램프 0.1 s 제동)"
    banners[round(lift.last_stop_eq + 15.0, 3)] = "마지막 정지 + 15 s: 잔류 진동 판정 창"
    banners[0.05] = "모터 출발 명령 + 램프 0.1 s (등가 원점 = 출발 + 0.05 s)"
    times = [lift.te[0]]
    times += list(np.arange(1.0, 14.5, 1.0))
    times += list(np.arange(14.6, 14.95, 0.1))
    times += list(np.arange(14.95, 15.75, 0.02))
    times += list(np.arange(15.8, 18.0, 0.1))
    times += list(np.arange(18.5, lift.te[-1] - 0.05, 1.0))
    times += [lift.te[-1]]
    plan = {}
    for t in times:
        plan[round(float(t), 3)] = None
    for t, text in banners.items():
        plan[t] = text
    out = []
    keys = sorted(plan)
    for j, t in enumerate(keys):
        text = plan[t]
        if j == 0:
            d = 900
        elif j == len(keys) - 1:
            d = 2200
        elif text:
            d = 1500
        elif 14.9 <= t <= 15.8:
            d = 110
        else:
            d = 160
        out.append((t, d, text))
    return out


def render_lift(bank, summary):
    lift = Lift()
    params = lift.params
    t0 = time.perf_counter()
    size = (LIFT_BOX[2], LIFT_BOX[3])
    items0 = bank.items(params, np.zeros(4))
    items1 = bank.items(params, np.asarray(lift.plan["e_op_m"]))
    limits = scene_limits_for(items0 + items1, [(lift.pos[0], lift.rot[0])], size,
                              extra_world=[s1.ground_polygon(lift.floor_z)], margin=(0.2, 0.2))
    background, layers = lift_layers(bank, lift, limits, size)
    print(f"  lift layers {time.perf_counter() - t0:.1f} s", flush=True)
    scale = size[0] / (limits[0][1] - limits[0][0])
    dir_screen = scr(lift.rot[0] @ lift.direction)[0]
    origin_screen = scr(np.zeros(3))[0]
    fig = new_figure()
    scene = Scene(fig, LIFT_BOX, limits, background)
    header, status, note = header_texts(fig)
    banner = banner_text(fig, x=290, y=122)
    cursor = s1.Cursor()
    zoom_cursor = s1.Cursor()
    te = lift.te
    x0, w = 640, 745
    # (1) whole run: pad contact force + crawler reaction
    ax = axes_box(fig, x0, 108, w, 135)
    style(ax, title="(1) 패드 접촉력 다리별 · 크롤러 반력 합 [kN] (전체; 등가 원점 기준 t)",
          xlabel="t_eq [s]")
    for k, leg in enumerate(LEG_ORDER):
        ax.plot(te, lift.N_kN[:, k], color=LEG_COLORS[leg], lw=1.2, label=leg)
        cursor.add_dot(ax, te, lift.N_kN[:, k], LEG_COLORS[leg])
    ax.plot(te, lift.Fcr_kN, color=CRAWLER_COLOR, lw=1.3, ls=(0, (4, 2)), label="크롤러 F_z")
    cursor.add_dot(ax, te, lift.Fcr_kN, CRAWLER_COLOR)
    ax.set_xlim(te[0], te[-1])
    ax.set_ylim(-10, 400)
    ax.axvspan(lift.plan["transition_window_s"][0] - lift.t_eq0,
               lift.plan["transition_window_s"][1] - lift.t_eq0, color=BAND_COLOR, alpha=0.6,
               lw=0, label="Δt 1e-5 s 창")
    ax.legend(fontsize=7.2, ncol=6, loc="upper left", frameon=True, framealpha=0.9)
    cursor.add_axes(ax)
    # (2) transition zoom: cylinder force
    za, zb = 14.85, 18.05
    ax = axes_box(fig, x0, 300, w, 165)
    style(ax, title="(2) 실린더 힘 [kN] (접지~정지 확대) · 점선 = 기준 접지 시각 · 회색 = 3자유도 "
          "기준 피크 - 로드 무게 · 빨강 = 이동 중 상한", xlabel="t_eq [s]")

    for k, leg in enumerate(LEG_ORDER):
        ax.plot(te, lift.Fcyl_kN[:, k], color=LEG_COLORS[leg], lw=1.3)
        zoom_cursor.add_dot(ax, te, lift.Fcyl_kN[:, k], LEG_COLORS[leg])
        ax.axvline(lift.touch_ref[k], color=LEG_COLORS[leg], lw=0.8, ls=":")
    peak_ref = lift.res["peak_record"]["reference_peak_N"]
    for k in range(len(LEG_ORDER)):
        ax.axhline(peak_ref[k] / 1e3 - params.legs[k].moving_part.mass_kg * 9.80665 / 1e3,
                   color=REF_COLOR, lw=0.7, ls=(0, (6, 3)))
    draw_moving_limits(ax, za + 0.03)
    ax.set_xlim(za, zb)
    ax.set_ylim(-8, 232)
    zoom_cursor.add_axes(ax)
    # (3) ground gaps
    ax = axes_box(fig, x0, 522, w * 0.46, 120)
    style(ax, title="(3) 지면 틈 [mm] (구 바닥 - 바닥, 음수 = 접촉 변형)", xlabel="t_eq [s]")
    for k, leg in enumerate(LEG_ORDER):
        ax.plot(te, lift.pad_gap_mm[:, k], color=LEG_COLORS[leg], lw=1.2)
        zoom_cursor.add_dot(ax, te, lift.pad_gap_mm[:, k], LEG_COLORS[leg])
    ax.plot(te, lift.crawler_gap_mm, color=CRAWLER_COLOR, lw=1.3, ls=(0, (4, 2)),
            label="크롤러 최저 구")
    zoom_cursor.add_dot(ax, te, lift.crawler_gap_mm, CRAWLER_COLOR)
    ax.axhline(0, color=EARTH_COLOR, lw=0.9)
    ax.set_xlim(za, zb)
    ax.set_ylim(-12, 62)
    ax.legend(fontsize=7, loc="upper left", frameon=False)
    zoom_cursor.add_axes(ax)
    # (4) attitude
    ax = axes_box(fig, x0 + w * 0.54, 522, w * 0.46, 120)
    style(ax, title="(4) 자세 [deg] (ZYX, pitch + = 앞 숙임)", xlabel="t_eq [s]")
    ax.plot(te, lift.att_deg[:, 0], color="#1f6fb2", lw=1.2, label="roll")
    ax.plot(te, lift.att_deg[:, 1], color="#c0392b", lw=1.2, label="pitch")
    cursor.add_dot(ax, te, lift.att_deg[:, 0], "#1f6fb2")
    cursor.add_dot(ax, te, lift.att_deg[:, 1], "#c0392b")
    ax.set_xlim(te[0], te[-1])
    ax.legend(fontsize=7, loc="center right", frameon=False)
    cursor.add_axes(ax)
    # (5) touch table
    cells = [[leg, f"{lift.touch_eq[k]:.4f}", f"{lift.touch_ref[k]:.3f}",
              f"{(lift.touch_eq[k] - lift.touch_ref[k]) * 1e3:+.1f}",
              f"{(lift.touch_eq[k] - lift.touch_indep[k]) * 1e3:+.3f}",
              f"{lift.res['peak_cylinder_force_N'][k] / 1e3:.1f}"] for k, leg in enumerate(LEG_ORDER)]
    cells.append(["크롤러 이탈", f"{lift.off_eq:.4f}", f"{lift.off_ref:.3f}",
                  f"{(lift.off_eq - lift.off_ref) * 1e3:+.1f}",
                  f"{(lift.off_eq - lift.off_indep) * 1e3:+.3f}", "-"])
    s2.table_axes(axes_box(fig, x0, 690, w, 115),
                  cells, ["다리", "접지 Chrono [s]", "동적 기준 [s]", "차 [ms] (허용 ±50)",
                          "6자유도+부싱 대비 [ms]", "실린더 피크 [kN]"], size=7.6)
    fin = lift.res["final"]
    text_block(fig, x0, 828, [
        f"정지 뒤 V1 접촉력 {', '.join(f'{v / 1e3:.2f}' for v in fin['contact_force_N'])} kN · "
        f"V3 자세 {fin['attitude_deg'][0]:+.5f} / {fin['attitude_deg'][1]:+.5f} deg",
        f"잔류 반진폭 {fin['residual_half_p2p_deg'][0]:.2e} / {fin['residual_half_p2p_deg'][1]:.2e}"
        " deg (< 1e-3) · 포락선 ζ (ζ_num 차감) "
        + ", ".join(f"{e['zeta_corrected']:.5f} (기준 {e['zeta_ref']:.5f})"
                    for e in fin["envelope"]),
        f"사전 판정 {sum(c['passed'] for c in lift.res['checks'])}/{len(lift.res['checks'])} 통과 "
        f"· 피크 기록: 3자유도 기준 대비 "
        + ", ".join(f"{r * 100:+.1f} %" for r in lift.res["peak_record"]["relative_difference"]),
    ], size=8.0)
    labels = [scene.label(LEG_COLORS[leg], size=8.0, ha="center", va="top", fontweight="bold")
              for leg in LEG_ORDER]
    arrows = [scene.arrow(LEG_COLORS[leg]) for leg in LEG_ORDER]
    header.set_text("S3 V4 크롤러 위에서 들어 올림 · 상단 · L1 · 크롤러 D안 ×1 · "
                    f"Δt {lift.res['dt_s']:g} s (YAML 기본) + 전환 창 1e-5 s · 명령 램프 "
                    f"{params.actuator.command_ramp_s:g} s (YAML)")
    note.set_text("3D: CAD 메시 실제 크기(×1). 상부체는 기록된 위치만큼 이동(자세 변화 ≤ "
                  f"{max(np.ptp(lift.att_deg, axis=0)):.2f}°는 그리지 않음), 로드·패드는 모터 위치만큼 "
                  "다리 축 이동(층 합성). 화살표: 패드 수직 반력 1 m/100 kN.")
    frames, durations, plan_out = [], [], []
    rep_frame = None
    for t_frame, d, text in lift_frame_times(lift):
        i = lift.index(t_frame)
        body_d = scr(lift.pos[i] - lift.pos[0])[0] - origin_screen
        bx, by = int(round(body_d[0] * scale)), int(round(-body_d[1] * scale))
        rods = {}
        for k, leg in enumerate(LEG_ORDER):
            dd = body_d + (dir_screen - origin_screen) * lift.a["s_motor"][i, k]
            rods[leg] = (int(round(dd[0] * scale)), int(round(-dd[1] * scale)))
        scene.set_image(compose(background, layers, (bx, by), rods))
        for k, leg in enumerate(LEG_ORDER):
            c = lift.pad_centres[i, k]
            contact = c - np.array([0.0, 0.0, lift.radius[k]])
            n = max(lift.N_kN[i, k], 0.0) * 1e3
            set_arrow(arrows[k], contact, contact + np.array([0, 0, n * ARROW_N_M_PER_N]),
                      visible=n > 50.0)
            sp = scr(contact)[0]
            labels[k].set_position((sp[0], sp[1] - 0.15))
            labels[k].set_text(f"{leg} s {lift.s_mm[i, k]:5.1f} mm\nN {lift.N_kN[i, k]:6.1f} kN")
        cursor.update(te[i], i)
        if za <= te[i] <= zb:
            zoom_cursor.update(te[i], i)
        else:
            zoom_cursor.update(np.nan, i)
            for dot, *_ in zoom_cursor.dots:
                dot.set_data([np.nan], [np.nan])
        set_banner(banner, text)
        phase = ("크롤러 위 정착" if te[i] < 0.0 else
                 "접근 (등속 신장)" if te[i] < lift.touch_eq.min() else
                 "접지 → 하중 이전" if te[i] < lift.off_eq else
                 "크롤러 이탈 → 운용 신장" if te[i] < lift.last_stop_eq else "잔류 진동")
        status.set_text(f"t_eq = {te[i]:7.3f} s   단계: {phase}   크롤러 F_z {lift.Fcr_kN[i]:6.1f} kN"
                        f"   u = {', '.join(f'{v:+.1f}' for v in lift.u_mm[i])} mm/s")
        image = s1.figure_to_image(fig)
        frames.append(image)
        durations.append(d)
        plan_out.append([round(float(te[i]), 4), d, text])
        if text and text.startswith("크롤러 이탈"):
            rep_frame = image
    plt.close(fig)
    summary["lift_gif"] = write_gif(frames, durations, OUT["lift"])
    if rep_frame is not None:
        s1.save_atomic(OUT["lift_frame"], lambda target: rep_frame.convert("RGB").save(
            target, format="png"))
        summary["lift_frame"] = rel(OUT["lift_frame"])
    summary["lift"] = {"case": LIFT_CASE, "dir": index()[LIFT_CASE],
                       "params_sha256": lift.meta.get("params_sha256", "")[:16],
                       "frames_plan (t_eq, ms, banner)": plan_out,
                       "screen_scale_px_per_m": scale, "value_checks": lift.checks()}


# =============================================================================================
# V5 / V6 PNG
# =============================================================================================


def render_v5v6(summary):
    indep = read_json(LIFT_CHECK)["B_V5_V6_exact_statics"]["exact_pdelta"]
    fig = new_figure(1400, 820)
    fig.text(8 / 1400, 1 - 10 / 820, "S3 V5·V6 다리 단독 신장 (상단, L1, S1 정착 상태에서 출발)",
             fontsize=13, fontweight="bold", va="top", color=INK_PRIMARY)
    fig.text(8 / 1400, 1 - 38 / 820, "V5: FL +1 / +5 mm 뒤 다리별 접촉력 변화. 막대 = Chrono "
             "(Δt 2e-4 s YAML 기본 / 1e-4 s), 회색 테두리 = 선형 기준(소각, P-δ 없음), 점 = 독립 정확 "
             "정역학(P-δ). V6: FL ± 0.1 mm/s, 실린더 힘이 F_min에 닿는 다리와 부상(접촉력 0).",
             fontsize=8.6, va="top", color=INK_SECONDARY)
    old, new = result("v5"), result("v5_default")
    ref = new["reference"]
    xs = np.arange(4)
    for j, key in enumerate(("+1 mm", "+5 mm")):
        delta = float(key[1])
        ax = axes_box(fig, 60 + j * 330, 90, 290, 300, 1400, 820)
        style(ax, title=f"V5 FL {key}: ΔF 다리별 [kN]")
        lin = np.asarray(ref["dF_per_mm_FL_N"]) * delta / 1e3
        ax.bar(xs, lin, 0.8, facecolor="none", edgecolor=REF_COLOR, lw=1.4, label="선형 기준")
        for off, r, lab, alpha in ((-0.17, new, "Chrono 2e-4 s", 1.0),
                                   (0.17, old, "Chrono 1e-4 s", 0.55)):
            ax.bar(xs + off, np.asarray(r["results"][key]["dF_N"]) / 1e3, 0.32,
                   color=[LEG_COLORS[g] for g in LEG_ORDER], alpha=alpha, label=lab)
        ex = np.asarray(indep[f"V5_dF_{int(delta)}mm_N"]) / 1e3
        ax.plot(xs, ex, "o", color=INK_PRIMARY, ms=4, label="독립 정확(P-δ)")
        ax.axhline(0, color=INK_SECONDARY, lw=0.6)
        s2.leg_ticks(ax)
        tol = 0.05 * float(np.max(np.abs(lin)))
        dmax = float(np.max(np.abs(np.asarray(new["results"][key]["dF_N"]) / 1e3 - lin)))
        ax.text(0.0, -0.09, f"허용 ±{tol:.2f} kN (최대 성분 5 %)\nChrono 2e-4 s - 기준 최대 "
                f"{dmax * 1e3:.0f} N\nChrono - 독립 정확 최대 "
                f"{np.max(np.abs(np.asarray(new['results'][key]['dF_N']) / 1e3 - ex)) * 1e3:.1f} N",
                transform=ax.transAxes, fontsize=7.4, color=INK_PRIMARY, va="top")
        if j == 0:
            ax.legend(fontsize=7, loc="lower right", frameon=True, framealpha=0.9)
    ax = axes_box(fig, 60, 500, 620, 140, 1400, 820)
    style(ax, title="V5 자세 변화 [deg] (roll, pitch) — Chrono 2e-4 s / 1e-4 s / 선형 기준 / 독립 정확")
    rows = []
    for key in ("+1 mm", "+5 mm"):
        d = float(key[1])
        lin = np.asarray(ref["droll_dpitch_per_mm_FL_deg"]) * d
        ex = indep[f"V5_datt_{int(d)}mm_deg"]
        rows.append((key, new["results"][key]["dattitude_deg"], old["results"][key]["dattitude_deg"],
                     lin, ex))
    cells = []
    for key, a, b, lin, ex in rows:
        for j, name in enumerate(("roll", "pitch")):
            cells.append([f"FL {key} Δ{name}", f"{a[j]:+.6f}", f"{b[j]:+.6f}", f"{lin[j]:+.6f}",
                          f"{ex[j]:+.6f}", f"{(a[j] / lin[j] - 1) * 100:+.2f} %"])
    s2.table_axes(ax, cells, ["항목 [deg]", "Chrono 2e-4 s", "Chrono 1e-4 s", "선형 기준",
                              "독립 정확(P-δ)", "2e-4 s - 기준"], size=7.6)
    ax.text(0.0, -0.08, "Chrono - 선형 기준 -0.7 ~ -1.3 %는 P-δ(기하 강성)이며 독립 정확 정역학이 "
            "≤ 1.1 N로 재현한다 (dynamics_model.md 5.7). 허용 ±5 %.", fontsize=8.0,
            transform=ax.transAxes, color=INK_SECONDARY)
    v6 = {"FL+": result("v6_FLp"), "FL-": result("v6_FLm")}
    fast = result("v6_FLp_fast")
    f_min = v6["FL+"]["F_min_N"] / 1e3
    for j, (direction, r) in enumerate(v6.items()):
        ax = axes_box(fig, 760, 90 + j * 345, 600, 270, 1400, 820)
        s = r["series"]
        tr = np.asarray(s["travel_mm"])
        fc = np.asarray(s["cylinder_force_N"]) / 1e3
        style(ax, title=f"V6 {direction} 0.1 mm/s: 실린더 힘 [kN] 대 |FL 이동| [mm]",
              xlabel="|FL 이동| [mm]")
        for k, leg in enumerate(LEG_ORDER):
            ax.plot(tr, fc[:, k], color=LEG_COLORS[leg], lw=1.4, label=leg)
        if direction == "FL+":
            sf = fast["series"]
            ax.plot(sf["travel_mm"], np.asarray(sf["cylinder_force_N"])[:, 2] / 1e3,
                    color=INK_PRIMARY, lw=0.8, ls=(0, (2, 2)), label="RL, 0.5 mm/s (준정적 확인)")
        ax.axhline(f_min, color=ACCENT, lw=1.0, ls=(0, (5, 3)))
        ax.text(0.3, f_min + 3, f"F_min {f_min:.3f} kN (실린더 힘)", color=ACCENT, fontsize=7.5)
        leg_name = r["F_min_leg"]
        x_fmin = r["F_min_crossings_travel_mm"][leg_name]
        x_lift = r["liftoff_travel_mm"]
        key = "V6_FL+" if direction == "FL+" else "V6_FL-"
        for x, xr, xi, lab in ((x_fmin, r["reference"]["F_min"]["delta_mm"],
                                indep[key]["F_min_mm"], "F_min"),
                               (x_lift, r["reference"]["liftoff"]["delta_mm"],
                                indep[key]["liftoff_mm"], "부상")):
            ax.axvline(x, color=LEG_COLORS[leg_name], lw=1.0)
            ax.axvline(xr, color=REF_COLOR, lw=1.0, ls=(0, (4, 2)))
            ax.annotate(f"{lab}: Chrono {x:.3f} mm\n기준 {xr:.2f} mm ({(x / xr - 1) * 100:+.1f} %)"
                        f"\n독립 정확 {xi:.4f} mm", xy=(x, 20 if lab == "F_min" else 60),
                        xytext=(x - 6.8, 20 if lab == "F_min" else 60), fontsize=7.2,
                        color=INK_PRIMARY, bbox=dict(boxstyle="round,pad=0.2", fc="white",
                                                     ec="none", alpha=0.85))
        ax.set_xlim(0, max(tr.max(), x_lift + 0.8))
        ax.set_ylim(-5, 200)
        ax.legend(fontsize=7, loc="upper right", frameon=True, framealpha=0.9, ncol=2)
        ax.text(0.01, -0.15, f"첫 F_min 다리 {leg_name} (기준 {r['reference']['F_min']['leg_at_F_min']}), "
                f"부상 다리 {r['liftoff_leg']} (기준 {r['reference']['liftoff']['unloaded_leg']}) · "
                f"Δt {r['dt_s']:g} s + 전환 창 1e-5 s · 허용 ±5 %", transform=ax.transAxes,
                fontsize=7.4, va="top", color=INK_SECONDARY)
    fig.text(8 / 1400, 1 - 800 / 820, "V6는 1e-4 s(+1e-5 s 창)로 판정했다(옛 파라미터 지문, Δt·램프는 "
             "명시값이라 재실행 불필요 — dynamics_model.md 5.7 재실행 목록). V5는 YAML 기본 2e-4 s로 다시 "
             "돌린 v5_default와 1e-4 s 원본을 함께 그린다.", fontsize=8.0, color=INK_SECONDARY)
    summary["v5v6_png"] = save_png(fig, OUT["v5v6"])
    summary["v5v6"] = {
        "v5_default_minus_v5_dF_max_abs_N": max(float(np.max(np.abs(
            np.asarray(new["results"][k]["dF_N"]) - np.asarray(old["results"][k]["dF_N"]))))
            for k in ("+1 mm", "+5 mm")),
        "v6": {d: {"F_min_leg": r["F_min_leg"], "F_min_mm": r["F_min_crossings_travel_mm"],
                   "liftoff_mm": r["liftoff_travel_mm"]} for d, r in v6.items()},
    }


# =============================================================================================
# V8(a) energy PNG
# =============================================================================================


def energy_blocks(case: str, block_s=1.0):
    """1-s block means of (E - E0) / E_kin0 and their linear fit (as run_S3.job_v8a)."""
    data = np.load(case_dir(case) / "energy.npz")
    e, g = data["energy"], data["contact_geometric"]
    total = e[:, 1] + e[:, 2] + g[:, 0] + g[:, 1] + e[:, 5]
    kin0 = float(e[0, 1])
    t = e[:, 0] - e[0, 0]
    rel_e = (total - total[0]) / kin0
    n = int(round(60.0 / block_s))
    centres = (np.arange(n) + 0.5) * block_s
    means = np.array([rel_e[(t >= i * block_s) & (t < (i + 1) * block_s)].mean() for i in range(n)])
    slope, icpt = np.polyfit(centres, means, 1)
    return t, rel_e, centres, means, slope, icpt, kin0


def render_v8a(summary):
    fig = new_figure(1400, 860)
    fig.text(8 / 1400, 1 - 10 / 860, "S3 V8(a) 수치 감쇠 시험: 물리 감쇠를 모두 0으로 두고 60 s 자유 진동 "
             "(상단, L1, EULER_IMPLICIT_LINEARIZED)", fontsize=13, fontweight="bold", va="top",
             color=INK_PRIMARY)
    fig.text(8 / 1400, 1 - 38 / 860, "패드: 다리 고정(e_op), 6모드 각 5 J. 크롤러: 다리 0, heave·roll·"
             "pitch 작은 진폭(E_kin0 3.25 J). 개정 17 판정: 패드 = 에너지 상승 ≤ 1 % + 모드별 ζ_num ≤ "
             "0.1 ζ, 크롤러 = 모드 ζ ≥ -1 % 물리 ζ + 1 s 평균 60 s 추세 ≤ +1 %, max(E-E0)는 기록.",
             fontsize=8.6, va="top", color=INK_SECONDARY)
    # (a) pads energy
    ax = axes_box(fig, 60, 90, 610, 330, 1400, 860)
    style(ax, title="(a) 패드: (E - E0) / E_kin0 [%] — 단조 감소(에너지 주입 없음)", xlabel="t [s]")
    for dt in (1.0e-4, 2.0e-4):
        r = result(f"v8a_pads_dt{dt:.0e}")
        s = r["series"]
        ax.plot(s["t_s"], np.asarray(s["dE_geometric_J"]) / r["E_kin0_J"] * 100,
                color=DT_COLORS[dt], lw=1.2, label=f"Δt {dt:g} s (E_kin0 {r['E_kin0_J']:.1f} J)")
    ax.axhline(1.0, color=ACCENT, lw=0.9, ls=(0, (5, 3)), label="상승 허용 +1 %")
    ax.legend(fontsize=7.5, loc="lower left")
    # (b) pads numerical zeta
    ax = axes_box(fig, 760, 90, 600, 330, 1400, 860)
    style(ax, title="(b) 패드: 모드별 수치 감쇠 ζ_num (식별) 대 한계 0.1 ζ", xlabel="모드")
    xs = np.arange(1, 7)
    lim = None
    for j, dt in enumerate((1.0e-4, 2.0e-4)):
        r = result(f"v8a_pads_dt{dt:.0e}")
        z = np.array([m["zeta_num_fit"] for m in r["modes"]])
        pred = np.array([m["zeta_num_pred"] for m in r["modes"]])
        lim = np.array([m["limit_0p1_zeta"] for m in r["modes"]])
        ax.bar(xs + (j - 0.5) * 0.34, z * 1e3, 0.32, color=DT_COLORS[dt], label=f"식별 Δt {dt:g} s")
        ax.plot(xs + (j - 0.5) * 0.34, pred * 1e3, "_", color=INK_PRIMARY, ms=12, mew=1.6,
                label="예측 r ω Δt/2" if j == 0 else None)
        for x, zi, li in zip(xs, z, lim, strict=True):
            if dt == 2.0e-4:
                ax.text(x + 0.17, zi * 1e3 + 0.08, f"{zi / li * 100:.0f}%", fontsize=6.8,
                        ha="center", color=DT_COLORS[dt])
    ax.plot(xs, lim * 1e3, "s", color=ACCENT, ms=6, mfc="none", mew=1.4, label="한계 0.1 ζ")
    ax.set_ylabel("ζ × 1e3", fontsize=8, color=INK_SECONDARY)
    ax.set_xticks(xs)
    ax.legend(fontsize=7.3, loc="upper left")
    ax.set_ylim(0, 6.0)
    ax.text(0.40, 0.97, "막대 위 숫자: 2e-4 s의 한계 대비 %\n(3차 97 %, 6차 91 %: 여유가 가장 작은 모드)",
            transform=ax.transAxes, fontsize=7.3, ha="left", va="top", color=INK_SECONDARY)
    # (c) crawler energy with 1-s means and trend
    ax = axes_box(fig, 60, 490, 610, 320, 1400, 860)
    style(ax, title="(c) 크롤러: (E - E0) / E_kin0 [%] · 굵은 점 = 1 s 평균, 선 = 선형 추세",
          xlabel="t [s]")
    crawler_info = {}
    for dt in (1.0e-4, 2.0e-4):
        case = f"v8a_crawler_dt{dt:.0e}"
        r = result(case)
        t, rel_e, centres, means, slope, icpt, kin0 = energy_blocks(case)
        ax.plot(t[::20], rel_e[::20] * 100, color=DT_COLORS[dt], lw=0.4, alpha=0.45)
        ax.plot(centres, means * 100, "o", color=DT_COLORS[dt], ms=3)
        ax.plot(centres, (icpt + slope * centres) * 100, color=DT_COLORS[dt], lw=1.6,
                label=f"Δt {dt:g} s: 추세 {slope * 60 * 100:+.3f} %/60 s, max(E-E0) "
                f"{r['energy_rise_rel_geometric'] * 100:.2f} % (기록)")
        crawler_info[case] = {"trend_rel_over_60s_recomputed": slope * 60.0,
                              "trend_rel_over_60s_result": r["energy_trend_rel_over_window"],
                              "max_rise_rel": r["energy_rise_rel_geometric"], "E_kin0_J": kin0}
    ax.axhline(1.0, color=ACCENT, lw=0.9, ls=(0, (5, 3)), label="추세 허용 +1 % (60 s)")
    ax.set_ylim(-1.0, 1.6)
    ax.legend(fontsize=7.2, loc="lower right")
    # (d) crawler modal zeta
    ax = axes_box(fig, 760, 490, 600, 320, 1400, 860)
    style(ax, title="(d) 크롤러: 감쇠 0 모드 ζ / (0.01 ζ_phys) — 판정 ≥ -1 (symlog)",
          xlabel="모드")
    names = ("pitch", "roll", "heave")
    xs = np.arange(3)
    worst = 0.0
    for j, dt in enumerate((1.0e-4, 2.0e-4)):
        r = result(f"v8a_crawler_dt{dt:.0e}")
        z = {m["mode"]: m["zeta_fit"] for m in r["modes"]}
        phys = {m["mode"]: m["zeta_physical"] for m in r["modes"]}
        frac = [z[n] / (0.01 * phys[n]) for n in names]
        worst = min(worst, min(frac))
        ax.bar(xs + (j - 0.5) * 0.34, frac, 0.32, color=DT_COLORS[dt], label=f"Δt {dt:g} s")
        for x, f in zip(xs + (j - 0.5) * 0.34, frac, strict=True):
            ax.text(x, f * 1.6 if f < 0 else f * 1.6 + 1e-4, f"{f:+.4f}", ha="center",
                    va="top" if f < 0 else "bottom", fontsize=6.8, color=DT_COLORS[dt])
    ax.set_yscale("symlog", linthresh=1e-3)
    ax.axhline(-1.0, color=ACCENT, lw=1.4, label="문턱 -1 (= -0.01 ζ_phys)")
    ax.axhline(0, color=INK_SECONDARY, lw=0.6)
    ax.set_ylim(-3.0, 0.05)
    s2.plain_log_formatter(ax, "y")
    ax.set_xticks(xs, [f"{n}\nζ_phys {phys[n]:.4f}" for n in names])
    ax.legend(fontsize=7.4, loc="lower left")
    ax.text(0.99, 0.22, f"음의 ζ = 에너지 주입. 실측 최소 {worst:+.4f} = 문턱의 "
            f"1/{abs(1 / worst):.0f}\n(heave 추세는 Δt 무관 → 적분기 몫 아님, "
            "float32 접촉 기하 잔차로 봄)", transform=ax.transAxes, fontsize=7.3, ha="right",
            va="top", color=INK_SECONDARY)
    summary["v8a_png"] = save_png(fig, OUT["v8a"])
    summary["v8a"] = crawler_info


# =============================================================================================
# V9 convergence PNG
# =============================================================================================


def render_v9(summary):
    verify = read_json(VERIFY)
    det = verify["v9"]["detail"]
    dts = (2.0e-4, 1.0e-4, 5.0e-5)
    ref_dt = 1.0e-5
    fig = new_figure(1400, 860)
    fig.text(8 / 1400, 1 - 10 / 860, "S3 V9 시간 간격 수렴 (상단, L1): 2e-4 / 1e-4 / 5e-5 s를 기준해 "
             "1e-5 s와 비교", fontsize=13, fontweight="bold", va="top", color=INK_PRIMARY)
    fig.text(8 / 1400, 1 - 38 / 860, "개정 17: 접지 시각은 기하 정의(구 바닥이 바닥을 지나는 순간, 보간)로 "
             "≤ 1e-4 s 판정, R15 시각(첫 N > 0 스텝 끝)은 구조 상한 2Δt - Δt_ref + 기하 차와 함께 기록. "
             "오차비는 탄성 하중 k_n δ(차는 접촉력)로 판정.", fontsize=8.6, va="top",
             color=INK_SECONDARY)

    def keyed(d):
        return {float(k): v for k, v in d.items()}

    # (a) log-log differences
    ax = axes_box(fig, 60, 90, 610, 340, 1400, 860)
    style(ax, title="(a) 기준해(1e-5 s)와의 차 대 Δt (log-log, 점선 = 기울기 1)", xlabel="Δt [s]")
    step = keyed(det["step"]["peak_elastic_dF_RL_N"])
    free = keyed(det["free"]["amplitude_rel_to_ref"])
    series = {
        "V9-1 과도 탄성 하중 차 [N]": [abs(step[d] - step[ref_dt]) for d in dts],
        "V9-2 1차 모드 5 s 진폭 상대 차 × 1e4": [abs(free[d]) * 1e4 for d in dts],
    }
    v4u = {r["dt_s"]: r for r in (result(f"v4_D_u{d:.0e}") for d in (*dts, ref_dt))}
    pk = {d: np.asarray(r["peak_cylinder_force_N"]) for d, r in v4u.items()}
    series["V4 실린더 피크 상대 차 × 1e4 (최대 다리)"] = [
        float(np.max(np.abs(pk[d] / pk[ref_dt] - 1))) * 1e4 for d in dts]
    geo = keyed(det["v4_touch_geometric"])
    g_ref = np.asarray(geo[ref_dt]["touch_geometric_eq_s"])
    series["V4 기하 접지 시각 차 [ms] × 100"] = [
        float(np.max(np.abs(np.asarray(geo[d]["touch_geometric_eq_s"]) - g_ref))) * 1e5
        for d in dts]
    markers = ("o", "s", "^", "D")
    for (label, ys), mk in zip(series.items(), markers, strict=True):
        ax.loglog(dts, ys, mk + "-", lw=1.2, ms=5, label=label)
    guide = np.array([5e-5, 2e-4])
    ax.loglog(guide, 10 * guide / 1e-4, ":", color=INK_SECONDARY, lw=1.0)
    ax.set_xticks(dts)
    s2.plain_log_formatter(ax, "x")
    s2.plain_log_formatter(ax, "y")
    ax.legend(fontsize=7.2, loc="lower right")
    # (b) touch-time definitions
    ax = axes_box(fig, 760, 90, 600, 340, 1400, 860)
    style(ax, title="(b) V4 접지 시각 - 1e-5 s 실행 [ms] (4 다리), 판정 = 기하 정의",
          xlabel="Δt [s]")
    r15 = verify["v9"]["detail"]["v4_r15_touch_recorded"]
    for d in dts:
        g = (np.asarray(geo[d]["touch_geometric_eq_s"]) - g_ref) * 1e3
        ax.semilogx([d] * 4, g, "x", color=ACCENT, ms=7, mew=1.6,
                    label="기하 접지 (판정)" if d == dts[0] else None)
        rr = r15[f"uniform dt {d:g} s"]
        ax.semilogx([d] * 4, np.asarray(rr["touch_minus_ref_s"]) * 1e3, "o", color="#1f6fb2",
                    ms=5, mfc="none", label="R15 접지 (기록)" if d == dts[0] else None)
        ax.semilogx([d * 0.9, d * 1.1],
                    [rr["structural_bound_s (2 dt - dt_ref + geometric diff)"] * 1e3] * 2,
                    color="#1f6fb2", lw=1.2, label="R15 구조 상한" if d == dts[0] else None)
    ax.axhline(0.1, color=ACCENT, lw=1.0, ls=(0, (5, 3)), label="기하 허용 0.1 ms")
    ax.axhline(-0.1, color=ACCENT, lw=1.0, ls=(0, (5, 3)))
    ax.set_ylim(-0.15, 0.5)
    ax.set_xticks(dts)
    s2.plain_log_formatter(ax, "x")
    ax.legend(fontsize=7.3, loc="upper left")
    win = {k: v for k, v in r15.items() if "windowed" in k}
    ax.text(0.99, 0.03, "전환 창 실행(1e-5 s 창) R15 차: " + ", ".join(
        f"{k.split(' ')[0]} {v['max_abs_s'] * 1e3:.3f} ms" for k, v in win.items()),
        transform=ax.transAxes, fontsize=7.0, ha="right", color=INK_SECONDARY)
    # (c) order ratios
    ax = axes_box(fig, 60, 500, 380, 300, 1400, 860)
    style(ax, title="(c) 오차비 (Δt, Δt/2, Δt/4) — 1차 적분기 기대 2")
    o1 = det["step"]["order_elastic_judged"]["ratio"]
    o1raw = det["step"]["order_raw_contact_force_recorded"]["ratio"]
    o2 = det["free"]["order_amplitude"]["ratio"]
    o2ph = det["free"]["order_phase_recorded"]["ratio"]
    vals = [o1, o2, o1raw, o2ph]
    labs = ["V9-1 k_n δ\n(판정)", "V9-2 진폭\n(판정)", "V9-1 접촉력\n(기록)", "V9-2 위상\n(기록)"]
    cols = [ACCENT, ACCENT, LIN_COLOR, LIN_COLOR]
    ax.axhspan(1.6, 2.4, color=BAND_COLOR, alpha=0.7, lw=0, zorder=0)
    ax.bar(range(4), vals, color=cols, width=0.6, zorder=2)
    ax.axhline(2.0, color=INK_PRIMARY, lw=0.8, ls=":")
    for i, v in enumerate(vals):
        ax.text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=8, color=INK_PRIMARY)
    ax.set_xticks(range(4), labs, fontsize=7.4)
    ax.set_ylim(0, 3.0)
    # (d) judged table at 2e-4 s
    ax = axes_box(fig, 480, 505, 880, 345, 1400, 860)
    ax.set_axis_off()
    checks = [c for c in verify["v9"]["checks"]]
    cells = []
    for c in checks:
        if "0.0002" not in c["item"] and "2e-4" not in c["item"] and "dt 0.0002" not in c["item"]:
            continue
        v = c["value"]
        vtxt = (f"{max(abs(x) for x in v):.4g}" if isinstance(v, list) else f"{v:.4g}")
        rtxt = c["ref"]
        if "error ratio" in c["item"]:
            vtxt = f"비 {v:.3f}"
        elif isinstance(rtxt, list) and c["tol_kind"] == "rel":
            dev = max(abs(a / b - 1) for a, b in zip(v, rtxt, strict=True))
            vtxt = f"상대 {dev:.2e}"
        elif isinstance(rtxt, list):
            dev = max(abs(a - b) for a, b in zip(v, rtxt, strict=True))
            vtxt = f"차 {dev:.3g}"
        elif c["tol_kind"] == "rel" and isinstance(v, (int, float)) and rtxt:
            vtxt = f"상대 {abs(v / rtxt - 1):.2e}"
        cells.append([c["item"][:70], vtxt, f"{c['tol']:.3g} ({c['tol_kind']})",
                      "통과" if c["passed"] else "실패"])
    n_pass = sum(c["passed"] for c in checks)
    s2.table_axes(ax, cells, ["V9 판정 항목 (Δt 2e-4 s = 새 YAML 기본)", "값", "허용", "판정"],
                  col_widths=[0.64, 0.13, 0.14, 0.07], size=6.9, pass_col=3)
    fig.text(480 / 1400, 1 - 488 / 860, f"(d) Δt 2e-4 s 관련 판정 항목 — V9 전체 {n_pass}/{len(checks)} "
             "통과 (2e-4·1e-4·5e-5 s 균일 + 전환 창 실행 3건)", fontsize=9, color=INK_PRIMARY,
             va="bottom")
    summary["v9_png"] = save_png(fig, OUT["v9"])
    summary["v9"] = {"order_ratios": {"elastic": o1, "amplitude": o2, "raw_recorded": o1raw,
                                      "phase_recorded": o2ph},
                     "checks_passed": f"{n_pass}/{len(checks)}"}


# =============================================================================================
# dashboard
# =============================================================================================


def render_summary(summary, before_path: Path | None):
    verify = read_json(VERIFY)
    before = read_json(before_path) if before_path and before_path.exists() else None
    fig = new_figure(1400, 900)
    fig.text(8 / 1400, 1 - 10 / 900, "S3 종합: 수치 감쇠(V8a) · 들어 올림(V4) · 다리 단독 신장(V5·V6) · "
             "Δt 수렴(V9) — 상단, L1, 크롤러 D안", fontsize=14, fontweight="bold", va="top",
             color=INK_PRIMARY)
    n, nf = verify["n_checks"], verify["n_failed"]
    verdict = "사전 판정 전부 통과" if nf == 0 else f"사전 판정 실패 {nf}건"
    fig.text(8 / 1400, 1 - 40 / 900, f"{verdict}: {n - nf}/{n} (verify_S3_L1.json, 생성 "
             f"{verify['generated']}, 파라미터 지문 {verify['params_sha256'][:8]}…)"
             + (f" · YAML 재생성 전 {before['n_checks'] - before['n_failed']}/{before['n_checks']}"
                f" (실패 {before['n_failed']}건: 판정 정의 문제, 개정 17로 정리)" if before else ""),
             fontsize=10, va="top", color=ACCENT if nf else "#2e7d32", fontweight="bold")
    # verdict table by check id
    groups = {}
    for c in verify["checks"]:
        gid = c["id"]
        g = groups.setdefault(gid, [0, 0])
        g[0] += 1
        g[1] += bool(c["passed"])
    ax = axes_box(fig, 20, 80, 420, 300, 1400, 900)
    desc = {"V1": "정지 뒤 접촉력 (V4 끝)", "V3": "정지 뒤 자세", "V4": "들어 올림 접지·피크·잔류",
            "V5": "FL +1/+5 mm 하중 변화", "V6": "F_min·부상 이동량", "V8a": "수치 감쇠 (감쇠 0)",
            "V9": "Δt 수렴", "V13": "구속 위반·NaN"}
    cells = [[gid, desc.get(gid, ""), f"{ok}/{tot}", "통과" if ok == tot else "실패"]
             for gid, (tot, ok) in sorted(groups.items())]
    s2.table_axes(ax, cells, ["ID", "항목", "통과/전체", "판정"],
                  col_widths=[0.14, 0.52, 0.18, 0.14], size=8.4, pass_col=3)
    # YAML change box
    params = load_params(level="top")
    ax = axes_box(fig, 20, 310, 420, 200, 1400, 900)
    ax.set_axis_off()
    ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, fc="#f7f6f2", ec="#b9b8b3"))
    ax.text(0.03, 0.95, "YAML 재생성 (사용자 결정 2026-10-21)\n"
            f"· simulation.L1.dt_s: 1e-4 → {params.simulation.L1.dt_s:g} s\n"
            "   규칙: 모드별 r_i ω_i Δt/2 ≤ 0.1 ζ_i (경계 ~ 0.1 c_t/k_t = 0.203 ms)\n"
            f"· actuator.command_ramp_s: {params.actuator.command_ramp_s:g} s (가정, 2026-10-20)\n"
            f"· actuator.command_accel_limit_m_s2: {params.actuator.command_accel_limit_m_s2:.6g}\n"
            "· full_stroke_time_s 30 s = 등속 시간, 정지-정지 30.1 s\n"
            "· L2b-NSC 1e-4, L2 5e-5, 기준해·전환 1e-5 s 그대로\n"
            f"· 파라미터 지문 8d1cc183… → {params.sha256[:8]}…",
            transform=ax.transAxes, fontsize=8.4, va="top", color=INK_PRIMARY, linespacing=1.5)
    # regression table
    old, new, w1 = result("v4_D_w2e-04"), result("v4_D_wdefault"), result("v4_D_w1e-04")
    ax = axes_box(fig, 20, 540, 420, 240, 1400, 900)
    ax.set_axis_off()
    d_touch = (np.asarray(new["touch_eq_s"]) - np.asarray(old["touch_eq_s"])) * 1e3
    d_peak = (np.asarray(new["peak_cylinder_force_N"]) / np.asarray(old["peak_cylinder_force_N"])
              - 1) * 100
    v5o, v5n = result("v5"), result("v5_default")
    d_v5 = max(float(np.max(np.abs(np.asarray(v5n["results"][k]["dF_N"])
                                   - np.asarray(v5o["results"][k]["dF_N"])))) for k in ("+1 mm", "+5 mm"))
    lines = ["새 기본 Δt 회귀 (YAML 재생성 뒤 재실행)",
             "V4 v4_D_wdefault 대 v4_D_w2e-04 (옛 지문):",
             f"  접지 차 {', '.join(f'{x:+.3f}' for x in d_touch)} ms (≤ 0.02 ms)",
             f"  실린더 피크 차 {', '.join(f'{x:+.4f}' for x in d_peak)} % (≤ 0.01 %)",
             f"  대 v4_D_w1e-04: 접지 ≤ "
             f"{np.max(np.abs(np.asarray(new['touch_eq_s']) - np.asarray(w1['touch_eq_s']))) * 1e3:.3f} ms",
             f"V5 v5_default(2e-4 s) 대 v5(1e-4 s): ΔF 차 ≤ {d_v5:.2f} N",
             "S1 3단계·S2b 크롤러 정착 재저장, V11 30.099 s (YAML 램프에서 30.1 s 기대)"]
    ax.text(0, 1, "\n".join(lines), fontsize=8.3, va="top", transform=ax.transAxes,
            color=INK_PRIMARY, linespacing=1.45)
    # key plots
    lift = Lift()
    ax = axes_box(fig, 500, 90, 420, 250, 1400, 900)
    style(ax, title="V4 접지 시각: Chrono - 기준 [ms] (허용 ±50 ms)")
    xs = np.arange(4)
    ax.bar(xs - 0.2, (lift.touch_eq - lift.touch_ref) * 1e3, 0.38,
           color=[LEG_COLORS[g] for g in LEG_ORDER], label="동적 기준(3자유도) 대비")
    ax.bar(xs + 0.2, (lift.touch_eq - lift.touch_indep) * 1e3 * 100, 0.38, color="none",
           edgecolor=INK_PRIMARY, label="6자유도+부싱 대비 ×100")
    ax.axhline(0, color=INK_SECONDARY, lw=0.6)
    s2.leg_ticks(ax)
    ax.legend(fontsize=7, loc="upper left")
    ax.set_ylim(-12, 14)
    ax.text(0.99, 0.03, "전방 -7 ms = P-δ, 후방 +7.7 ms = 패드 부싱 수평 고정 (5.7절)",
            transform=ax.transAxes, fontsize=7, ha="right", color=INK_SECONDARY)
    ax = axes_box(fig, 960, 90, 420, 250, 1400, 900)
    style(ax, title="V4 피크 실린더 힘 [kN] · 이동 중 상한 218 kN")
    ax.bar(xs, np.asarray(new["peak_cylinder_force_N"]) / 1e3,
           color=[LEG_COLORS[g] for g in LEG_ORDER])
    draw_moving_limits(ax)
    for x, v in zip(xs, new["peak_cylinder_force_N"], strict=True):
        ax.text(x, v / 1e3 + 3, f"{v / 1e3:.1f}", ha="center", fontsize=7.5)
    s2.leg_ticks(ax)
    ax.set_ylim(0, 235)
    ax = axes_box(fig, 500, 390, 420, 230, 1400, 900)
    style(ax, title="V4 자세 [deg] (크롤러 위 → 패드 위)", xlabel="t_eq [s]")
    ax.plot(lift.te, lift.att_deg[:, 0], color="#1f6fb2", lw=1.1, label="roll")
    ax.plot(lift.te, lift.att_deg[:, 1], color="#c0392b", lw=1.1, label="pitch")
    ax.legend(fontsize=7)
    ax = axes_box(fig, 960, 390, 420, 230, 1400, 900)
    style(ax, title="V4 패드 접촉력·크롤러 반력 [kN] (접지 부근)", xlabel="t_eq [s]")
    for k, leg in enumerate(LEG_ORDER):
        ax.plot(lift.te, lift.N_kN[:, k], color=LEG_COLORS[leg], lw=1.1)
    ax.plot(lift.te, lift.Fcr_kN, color=CRAWLER_COLOR, lw=1.2, ls=(0, (4, 2)))
    ax.set_xlim(14.9, 16.2)
    ax = axes_box(fig, 500, 670, 880, 210, 1400, 900)
    ax.set_axis_off()
    v8 = {c["case"]: c for c in verify["checks"] if c["id"] == "V8a"}
    rej = verify.get("v8a_crawler_rejudged_rev17", {})
    lines = ["판정 정의 변경 (dynamics_model.md 5.7 개정 17, verify/s3.py)",
             "· V8(a) 크롤러: max(E-E0) ≤ 1 % → 기록. 판정 = 감쇠 0 모드 ζ ≥ -1 % 물리 ζ + 1 s 평균 60 s 추세 ≤ +1 % E_kin0. "
             + ", ".join(f"{k.split('_')[-1]}: max(E-E0) "
                         f"{v['recorded_only']['energy_rise_rel_geometric (max(E - E0) / E_kin0, recorded)'] * 100:.2f} %"
                         for k, v in rej.items()),
             "· V9 V4 접지 시각: R15 정의(양자화 max(1e-4, Δt)) → 기하 정의 ≤ 1e-4 s 판정, R15는 구조 상한 2Δt - Δt_ref + 기하 차와 기록",
             "· 남은 해석 차(판정 영향 없음): 크롤러 이탈 15.571 s 대 기준 15.607 s(-36 ms, 패드 부싱 수평 고정),"
             " ×3 감도 후방 패드 항복 약 10 ms(R8 크롤러 접선 모델 부재)",
             "· 다시 돌리지 않은 판정(V6, V8a, V9, ×3)은 Δt·램프를 명시해 돌려 옛 지문 그대로 유효(per_case.params_sha256에 표시)"]
    ax.text(0, 1, "\n".join(lines), fontsize=8.0, va="top", transform=ax.transAxes,
            color=INK_PRIMARY, linespacing=1.5, wrap=True)
    del v8
    summary["summary_png"] = save_png(fig, OUT["summary"])
    summary["summary"] = {"n_checks": n, "n_failed": nf,
                          "before": None if before is None else
                          {"n_checks": before["n_checks"], "n_failed": before["n_failed"],
                           "failed": [(c["case"], c["item"]) for c in before["failed"]]}}


# =============================================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="+", choices=ALL_PARTS, default=list(ALL_PARTS))
    parser.add_argument("--cluster-mm", type=float, default=12.0)
    parser.add_argument("--mesh-cache", type=Path, default=None)
    parser.add_argument("--before", type=Path, default=DEFAULT_BEFORE_VERIFY,
                        help="verify_S3_L1.json written before the YAML regeneration")
    parser.add_argument("--cpu", choices=("ecore", "os"), default="ecore")
    args = parser.parse_args()
    started = time.perf_counter()
    cpu = s2.place_cpu(args.cpu)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = read_json(OUT["json"]) if OUT["json"].exists() else {}
    params = load_params(level="top")
    global F_MAX_MOVING_KN, F_MAX_MOVING_LEG_KN
    from outrigger_sim.chrono.actuators import leg_force_limits_N

    # per leg (legs.<leg>.cylinder.max_force_extend_N, REXOME35); one line while equal
    F_MAX_MOVING_LEG_KN = [f / 1e3 for f in leg_force_limits_N(params)[0]]
    F_MAX_MOVING_KN = F_MAX_MOVING_LEG_KN[0]
    summary["meta"] = {"script": "04_scripts/02_chrono/render_S3_gifs.py", "cpu": cpu,
                       "params_sha256": params.sha256[:16],
                       "view_oblique_toward_viewer_body": VIEWS["oblique"][2].round(4).tolist(),
                       "arrow_normal_m_per_kN": ARROW_N_M_PER_N * 1e3,
                       "inputs": {"index": rel(INDEX), "verify": rel(VERIFY),
                                  "independent": rel(LIFT_CHECK)}}
    if "lift" in args.only:
        parts, render, stats, _ = load_drawing_meshes(args.mesh_cache, args.cluster_mm)
        bank = MeshBank.build(parts, render)
        summary["meta"]["meshes"] = stats
        print(f"meshes {stats} {time.perf_counter() - started:.0f} s", flush=True)
        render_lift(bank, summary)
        print(json.dumps(summary["lift_gif"]), flush=True)
    if "v5v6" in args.only:
        render_v5v6(summary)
    if "v8a" in args.only:
        render_v8a(summary)
    if "v9" in args.only:
        render_v9(summary)
    if "summary" in args.only:
        render_summary(summary, args.before)
    summary["last_run_s"] = round(time.perf_counter() - started, 1)
    OUT["json"].write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=float),
                           encoding="utf-8")
    print(f"done {summary['last_run_s']} s", flush=True)


if __name__ == "__main__":
    main()
