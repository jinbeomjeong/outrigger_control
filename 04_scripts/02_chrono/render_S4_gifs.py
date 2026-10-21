"""Animated GIFs and the dashboard PNG of the S4 runs (L1, top level; stored results only,
nothing is simulated and no input is modified).

Reads:
    07_results/S4/A_modes/index.json -> modes_<run>/series.npz (t, q, eta; 1 ms samples, t = 0
        at the excitation) of the judged runs of verify_S4_L1_modes.json (v7.judged[].run)
    07_results/S4_energy/index.json -> v8b_pitch2_dt2e-04/{budget.npz, record/} (judged V8(b)
        case: 2 deg pitch floor, kick 0.5 m/s, 30 s), v8b_flat_dt2e-04/record (row 0 = the S1
        top snapshot pose and leg extensions used for the mode GIF)
    06_analysis/01_chrono/14_S4/verify_S4_L1_modes.json, verify_S4_L1_energy.json
    06_analysis/00_dynamics/s4_check.json            independent checks (dynamics-expert)
    06_analysis/00_dynamics/reference.json           Phi, M, reference point (modal_reference)
    02_params/rexome33.yaml                           levels, legs, ground height
    C8 visual meshes + C11 display colours via 04_scripts/00_cad/render_cad_tracks_summary.py

Writes (06_analysis/01_chrono/14_S4/):
    S4_modes.gif        V7 six modes, 2 x 3 panels. Each panel: the machine moved by
                        Phi_i eta_i(t) (eta_i = recorded Chrono projection of the judged run,
                        reference-point 6 DoF, exaggerated x A_i), grey ghost = equilibrium,
                        mast-top path of the lap; laps = cycles 0, 3, 6, 9 after the excitation
                        (16 phases per cycle), so the decay rate (zeta) shows; f, zeta
                        Chrono / reference / ERA; mini plot eta_i(t) with the lap window
    S4_energy_v8b.gif   V8(b) judged case: machine (body motion x20 about the kick pose,
                        pads red while lifted), pad anchor (bushing fixed point) slip paths
                        with create / remove events, energy terms as a stacked bar and as
                        lines, residual R(t) with the V8(b) limits, pad normal forces;
                        0-3 s in 20 ms steps, 3-30 s in 0.5 s steps
    S4_summary.png      one-page dashboard: V7 f / zeta utilisation, beta frequencies and
                        statics, leg-damping zeta ratio, V8(b) five checks, dt convergence
                        (Richardson), residual decomposition
    render_S4_gifs.json input sha256, script, settings, frame plans, value checks

Conventions: world / body x forward, y left, z up, SI; legs FL, FR, RL, RR. Mode coordinates
q = [u (m), theta (rad)] of the reference point (rigid_displacement), eta = Phi^T M q
[sqrt(kg) m]. 3D: orthographic, C8 meshes in the C11 display colours (render_cad_tracks_summary)
painted with hidden-line outlines; displacements are exaggerated (factor printed per panel).

CPU: P-cores (outrigger_sim.hostcpu.place_process("pcore")), up to --jobs render workers.

Usage (project root, Chrono-dev python):
    python -I -u 04_scripts/02_chrono/render_S4_gifs.py [--only modes energy summary]
        [--jobs 4] [--mesh-cache DIR] [--cpu pcore|os]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAD_SCRIPTS = ROOT / "04_scripts" / "00_cad"
sys.path.insert(0, str(CAD_SCRIPTS))
sys.path.insert(0, str(ROOT / "03_src"))

import render_cad_tracks_summary as cadr  # noqa: E402

OUT_DIR = ROOT / "06_analysis" / "01_chrono" / "14_S4"
MODES_VERIFY = OUT_DIR / "verify_S4_L1_modes.json"
ENERGY_VERIFY = OUT_DIR / "verify_S4_L1_energy.json"
S4_CHECK = ROOT / "06_analysis" / "00_dynamics" / "s4_check.json"
REFERENCE_JSON = ROOT / "06_analysis" / "00_dynamics" / "reference.json"
PARAMS_YAML = ROOT / "02_params" / "rexome33.yaml"
MODES_INDEX = ROOT / "07_results" / "S4" / "A_modes" / "index.json"
ENERGY_INDEX = ROOT / "07_results" / "S4_energy" / "index.json"
OUT = {
    "modes": OUT_DIR / "S4_modes.gif",
    "energy": OUT_DIR / "S4_energy_v8b.gif",
    "summary": OUT_DIR / "S4_summary.png",
    "json": OUT_DIR / "render_S4_gifs.json",
}
ENERGY_CASE = "v8b_pitch2_dt2e-04"
POSE_CASE = "v8b_flat_dt2e-04"
LEVEL = "top"
LEG_ORDER = ("FL", "FR", "RL", "RR")
LEG_COLORS = {"FL": "#2a78d6", "FR": "#eb6834", "RL": "#1baf7a", "RR": "#eda100"}
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300")
INK_PRIMARY, INK_SECONDARY, SURFACE = cadr.INK_PRIMARY, cadr.INK_SECONDARY, cadr.SURFACE
PASS_COLOR, FAIL_COLOR, LIMIT_COLOR = "#008300", "#e34948", "#e34948"
GHOST_COLOR = "#b9b8b3"
LIFT_COLOR = "#e34948"
MODE_NAMES = {1: "1차 roll-sway", 2: "2차 pitch-surge", 3: "3차 yaw-sway",
              4: "4차 pitch-surge-heave", 5: "5차 heave-pitch", 6: "6차 yaw-roll"}
MODE_CELL_M = 0.04
"""Vertex-clustering cell of the drawn meshes in the mode / energy GIFs [m] (small panels)."""
MODE_LAPS = (0, 3, 6, 9)
MODE_PHASES = 16
MODE_PEAK_M = 0.8
"""Exaggeration target: largest drawn displacement of a machine point in lap 0 [m]."""
ENERGY_K = 20.0
VIEW_TOWARD = (1.0, -1.0, 0.75)
FLOOR_RECT = ((-3.6, 4.4), (-2.6, 2.6))
MODE_FLOOR_RECT = ((-3.3, 4.0), (-2.0, 2.0))

plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


# =============================================================================================
# helpers
# =============================================================================================


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


rel = cadr.rel


def figure_to_image(fig) -> Image.Image:
    fig.canvas.draw()
    return Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())


def axes_box(fig, x, y, w, h, W, H):
    return fig.add_axes((x / W, 1 - (y + h) / H, w / W, h / H))


def style(ax, title=None, xlabel=None, ylabel=None, size=8.5):
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#b9b8b3")
    ax.tick_params(labelsize=7.5, colors=INK_SECONDARY, length=2)
    ax.grid(True, color="#ebeae6", lw=0.6)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, fontsize=size, loc="left", color=INK_PRIMARY, pad=4)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=7.8, color=INK_SECONDARY, labelpad=1)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=7.8, color=INK_SECONDARY, labelpad=1)


def rotvec_matrix(theta) -> np.ndarray:
    from scipy.spatial.transform import Rotation

    return Rotation.from_rotvec(np.asarray(theta, float)).as_matrix()


def quat_matrix(q) -> np.ndarray:
    from outrigger_sim.frames import quat_to_matrix

    return quat_to_matrix(np.asarray(q, float))


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=1)
    return buffer.getvalue()


def from_png(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGBA")


def swatches(colours) -> list[tuple[int, int, int]]:
    out = []
    bg = np.array(matplotlib.colors.to_rgb(SURFACE))
    for colour in colours:
        base = np.array(matplotlib.colors.to_rgb(colour))
        for shade in (0.4, 0.55, 0.7, 0.85, 1.0):
            rgb = np.clip(base * shade + 0.1 * (1 - shade), 0, 1)
            for fade in (0.0, 0.3):
                out.append(tuple(int(round(v * 255)) for v in rgb * (1 - fade) + bg * fade))
    return out


def write_gif(frames, durations, path: Path, extra_colours=()) -> dict:
    """One global palette (8 sample frames + colour swatches), pixels equal to the previous
    frame written as a reserved transparent index, disposal 1 (as render_S2_gifs.write_gif);
    identical frames merged first (Pillow would drop them)."""
    n_input = len(frames)
    merged, merged_d, previous = [], [], None
    for frame, duration in zip(frames, durations, strict=True):
        data = np.asarray(frame)
        if previous is not None and np.array_equal(data, previous):
            merged_d[-1] += duration
            continue
        merged.append(frame)
        merged_d.append(duration)
        previous = data
    frames, durations = merged, merged_d
    ids = sorted(set(np.linspace(0, len(frames) - 1, 8).astype(int).tolist()))
    w, h = frames[0].size
    sw_list = swatches(["#ff4d06", "#696969", "#bfbfbf", "#e0dfdb", "#3087e3", "#404040",
                        GHOST_COLOR, cadr.GROUND_COLOR, *LEG_COLORS.values(), *SERIES,
                        LIFT_COLOR, *extra_colours])
    sample = Image.new("RGB", (w * len(ids), h + 60))
    for k, i in enumerate(ids):
        sample.paste(frames[i], (k * w, 0))
    sw = max(1, sample.width // len(sw_list))
    for k, colour in enumerate(sw_list):
        sample.paste(Image.new("RGB", (sw, 60), colour), (k * sw, h))
    palette = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    colours = palette.getpalette()[: 3 * 255]
    colours += [0] * (3 * 255 - len(colours)) + [255, 0, 255]
    clear = 255
    lut = np.array(colours, dtype=np.uint8).reshape(-1, 3)
    check_ids = set(np.linspace(0, len(frames) - 1, 6).astype(int).tolist())
    expected, indexed, previous_codes = {}, [], None
    for n, frame in enumerate(frames):
        codes = np.asarray(frame.quantize(palette=palette, dither=Image.Dither.NONE)).copy()
        if n in check_ids:
            expected[n] = lut[codes]
        coded = codes.copy()
        if previous_codes is not None:
            coded[codes == previous_codes] = clear
        previous_codes = codes
        image = Image.fromarray(coded, "P")
        image.putpalette(colours)
        image.info["transparency"] = clear
        indexed.append(image)
    keep = [0] + [n for n in range(1, len(indexed)) if (np.asarray(indexed[n]) != clear).any()]
    if len(keep) != len(indexed):
        new_d = []
        for n in range(len(indexed)):
            if n in keep:
                new_d.append(durations[n])
            else:
                new_d[-1] += durations[n]
        expected = {keep.index(n): v for n, v in expected.items() if n in keep}
        indexed = [indexed[n] for n in keep]
        durations = new_d
    durations = [max(20, int(round(d / 10.0)) * 10) for d in durations]
    cadr.save_atomic(path, lambda target: indexed[0].save(
        target, save_all=True, append_images=indexed[1:], duration=durations, loop=0,
        optimize=False, disposal=1, transparency=clear))
    worst = 0
    with Image.open(path) as gif:
        n_frames = gif.n_frames
        for n in range(n_frames):
            gif.seek(n)
            if n in expected:
                decoded = np.asarray(gif.convert("RGB"), dtype=np.int16)
                worst = max(worst, int(np.abs(decoded - expected[n]).max()))
    return {"path": rel(path), "frames": n_frames,
            "roundtrip_max_abs_diff_rgb (decoded vs quantized, 6 frames)": worst,
            "size_bytes": path.stat().st_size, "loop_s": round(sum(durations) / 1000, 2),
            "resolution_px": [w, h], "merged_identical_frames": n_input - n_frames}


# =============================================================================================
# render workers (C8 + C11 meshes, painter)
# =============================================================================================

_WORKER: dict = {}


def _worker_init(parts_pickle: str, cpu: str):
    if cpu != "os":
        cadr.place_cpu("pcore")
    with open(parts_pickle, "rb") as handle:
        _WORKER["parts"] = pickle.load(handle)["parts"]
    cadr.register_view("s4", VIEW_TOWARD)


def _worker_render(task: dict) -> tuple:
    """task: key, pos, rot, s_motor, auger_travel_m, direction, pad_world, limits, size,
    floor (point, normal, rect) or None, colour (override for every part) or None,
    lifted (legs drawn red)."""
    override = None
    parts = _WORKER["parts"]
    items = []
    if task.get("colour"):
        override = {k: task["colour"] for k in ("body", "barrel", "rod", "pad")}
    lifted = set(task.get("lifted", ()))
    for part in parts:
        ov = override
        if part.kind == "pad" and part.leg in lifted:
            ov = {"pad": LIFT_COLOR}
        items += cadr.posed_items([part], auger_travel_m=task["auger_travel_m"],
                                  s_motor=task["s_motor"], direction=task["direction"],
                                  pos=task["pos"], rot=task["rot"],
                                  pad_world=task.get("pad_world"), colour_override=ov)
    image = cadr.render_items(items, "s4", task["limits"], task["size"], floor=task["floor"],
                              edges=task.get("edges", True), depth_fade=True)
    return task["key"], png_bytes(image)


def render_many(tasks, parts_pickle, jobs, cpu):
    out = {}
    if jobs <= 1:
        _worker_init(parts_pickle, cpu)
        for task in tasks:
            key, data = _worker_render(task)
            out[key] = data
        return out
    with ProcessPoolExecutor(jobs, initializer=_worker_init,
                             initargs=(parts_pickle, cpu)) as pool:
        for key, data in pool.map(_worker_render, tasks, chunksize=2):
            out[key] = data
    return out


# =============================================================================================
# shared model state
# =============================================================================================


class Context:
    def __init__(self, mesh_cache: Path, cpu: str):
        from outrigger_sim.geometry import extension_direction, pad_sphere_centre_body_m
        from outrigger_sim.params import load_params
        from outrigger_sim.scenarios.impulse import modal_reference
        from outrigger_sim.verify.reference import load_references

        self.params = load_params(level=LEVEL)
        self.direction = extension_direction(self.params)
        self.auger_travel = float(self.params.superstructure.auger_travel_m)
        self.modal = modal_reference(load_references(), LEVEL)
        self.floor_z = float(self.params.ground.crawler_bottom_z_m)
        self.cpu = cpu
        self.pad_centre_body = pad_sphere_centre_body_m
        parts, stats = cadr.load_coloured_parts(mesh_cache, cell_m=MODE_CELL_M)
        self.parts, self.mesh_stats = parts, stats
        key = hashlib.sha256(str(stats).encode()).hexdigest()[:10]
        self.parts_pickle = mesh_cache / f"s4_parts_{key}.pkl"
        if not self.parts_pickle.exists():
            with open(self.parts_pickle, "wb") as handle:
                pickle.dump({"parts": parts}, handle, protocol=5)
        cadr.register_view("s4", VIEW_TOWARD)

    def body_points(self, s_motor) -> np.ndarray:
        items = cadr.posed_items(self.parts, auger_travel_m=self.auger_travel, s_motor=s_motor,
                                 direction=self.direction)
        return cadr.items_points(items, step=5)

    def mast_top_body(self) -> np.ndarray:
        mast = [p for p in self.parts if p.name == "mast"][0]
        v = np.vstack([pc.vertices for pc in mast.pieces])
        return v[np.argmax(v[:, 2])]

    def sphere_centres_body(self, s_motor) -> np.ndarray:
        return np.array([self.pad_centre_body(self.params, k, s_motor[k]) for k in range(4)])


def load_record(case_dir: Path, params):
    from outrigger_sim.record import load_record as _load

    rec = _load(case_dir / "record", params_sha256=params.sha256)
    return {k: np.asarray(v) for k, v in rec.arrays.items()}, rec.bushing_events, rec.run_meta


# =============================================================================================
# GIF 1: six modes
# =============================================================================================


def render_modes(ctx: Context, jobs: int, summary: dict):
    t_start = time.perf_counter()
    verify = read_json(MODES_VERIFY)
    index = read_json(MODES_INDEX)
    energy_index = read_json(ENERGY_INDEX)
    pose_arrays, _, pose_meta = load_record(ROOT / energy_index[POSE_CASE]["dir"], ctx.params)
    pos0 = pose_arrays["body_pos"][0].copy()
    rot0 = quat_matrix(pose_arrays["body_quat_wxyz"][0])
    s_motor = pose_arrays["s_motor"][0].copy()
    phi, ref_body = ctx.modal.phi, ctx.modal.reference_point_body_m
    p_ref = pos0 + rot0 @ ref_body
    centres0 = ctx.sphere_centres_body(s_motor) @ rot0.T + pos0
    body_pts = ctx.body_points(s_motor) @ rot0.T + pos0
    mast_top = rot0 @ (ctx.mast_top_body() + np.array([0, 0, 0])) + pos0
    judged = {j["mode"]: j for j in verify["v7"]["judged"]}
    f_ref = np.asarray(ctx.modal.f_damped_Hz, float)
    zeta_ref = np.asarray(ctx.modal.zeta, float)
    cases = {}
    for i in range(1, 7):
        j = judged[i]
        case_dir = ROOT / index[f"modes_{j['run']}"]
        data = np.load(case_dir / "series.npz")
        t, eta = data["t"], data["eta"][:, i - 1]
        f_d = float(j["f_damped_proj_Hz"])
        period = 1.0 / f_d
        # first maximum of |eta| after the excitation = lap 0 start (cosine-like phase)
        first = t <= period
        t_peak = float(t[first][np.argmax(np.abs(eta[first]))])
        lap0 = (t >= t_peak) & (t <= t_peak + period)
        eta_peak = float(np.abs(eta[lap0]).max())
        u = phi[:3, i - 1] * eta_peak
        th = phi[3:, i - 1] * eta_peak
        disp = np.linalg.norm(u[None] + np.cross(th[None], body_pts - p_ref), axis=1)
        amp = MODE_PEAK_M / float(disp.max())
        if t_peak + (MODE_LAPS[-1] + 1) * period > t[-1]:
            raise SystemExit(f"mode {i}: record too short for lap {MODE_LAPS[-1]}")
        cases[i] = {"t": t, "eta": eta, "f_d": f_d, "period": period, "t_peak": t_peak,
                    "amp": amp, "judged": j, "run": j["run"], "dir": rel(case_dir),
                    "max_true_disp_mm": float(disp.max() * 1e3)}

    def pose(i, eta_value):
        c = cases[i]
        u = c["amp"] * phi[:3, i - 1] * eta_value
        th = c["amp"] * phi[3:, i - 1] * eta_value
        rd = rotvec_matrix(th)
        pos = p_ref + u + rd @ (pos0 - p_ref)
        centres = p_ref + u + (centres0 - p_ref) @ rd.T
        pads = {leg: (pos0 + centres[k] - centres0[k], rot0) for k, leg in enumerate(LEG_ORDER)}
        top = p_ref + u + rd @ (mast_top - p_ref)
        return pos, rd @ rot0, pads, top

    # panel geometry
    W, H = 1500, 980
    cols, rows = 3, 2
    pw, ph = 496, 430
    size3d = (pw - 6, 300)
    floor_pts = np.array([[x, y, ctx.floor_z] for x in MODE_FLOOR_RECT[0] for y in MODE_FLOOR_RECT[1]])
    all_pts = [body_pts, floor_pts]
    for i in cases:
        for sgn in (-1, 1):
            p, r, _, _ = pose(i, sgn * np.abs(cases[i]["eta"]).max())
            all_pts.append(((body_pts - pos0) @ rot0) @ r.T + p)
    limits = cadr.fit_limits(cadr.screen(np.vstack(all_pts), "s4"), size3d, 0.05)
    floor = ((0.0, 0.0, ctx.floor_z), (0.0, 0.0, 1.0), MODE_FLOOR_RECT)
    base = {"s_motor": s_motor, "auger_travel_m": ctx.auger_travel, "direction": ctx.direction,
            "limits": limits, "size": size3d}
    tasks = [dict(base, key=("ghost",), pos=pos0, rot=rot0, floor=floor, colour=GHOST_COLOR,
                  edges=False)]
    plan = []
    for lap in MODE_LAPS:
        for k in range(MODE_PHASES):
            plan.append((lap, k))
    for i in cases:
        c = cases[i]
        for lap, k in plan:
            t_f = c["t_peak"] + (lap + k / MODE_PHASES) * c["period"]
            e = float(np.interp(t_f, c["t"], c["eta"]))
            p, r, pads, _ = pose(i, e)
            tasks.append(dict(base, key=(i, lap, k), pos=p, rot=r, pad_world=pads, floor=None))
    print(f"  modes: {len(tasks)} renders", flush=True)
    images = render_many(tasks, str(ctx.parts_pickle), jobs, ctx.cpu)
    t_render = time.perf_counter() - t_start
    ghost = from_png(images[("ghost",)])
    gdata = np.asarray(ghost).copy()
    floor_img = cadr.render_items([], "s4", limits, size3d, floor=floor)
    fl = np.asarray(floor_img).astype(float) / 255
    gh = gdata.astype(float) / 255
    # ghost faded on the floor (ghost alpha x 0.55)
    a_g = gh[..., 3:4] * 0.55
    comp = gh[..., :3] * a_g + fl[..., :3] * fl[..., 3:4] * (1 - a_g)
    alpha = a_g + fl[..., 3:4] * (1 - a_g)
    back = Image.fromarray(np.uint8(np.clip(np.concatenate(
        [np.where(alpha > 0, comp / np.maximum(alpha, 1e-9), 0), alpha], axis=-1), 0, 1) * 255),
        "RGBA")

    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=SURFACE)
    fig.text(10 / W, 1 - 10 / H, "S4 V7 6개 모드 형상 (상단, L1, Chrono 기록에서 추출) — 판정: 통과 "
             "(dynamics_model.md 개정 19, 5.8절)", fontsize=14, fontweight="bold", va="top",
             color=INK_PRIMARY)
    fig.text(10 / W, 1 - 38 / H,
             "그림 = Φ_i η_i(t): η_i는 판정에 쓴 Chrono 실행의 모달 투영 기록(기준점 6자유도, 1 ms), Φ·M·기준점은 "
             "reference.json V7_ball_centre_bushing_rev13. 변위 과장 ×A_i(칸마다 표기), 회색 = 평형 자세, "
             "선 = 마스트 꼭대기 궤적.", fontsize=8.6, va="top", color=INK_SECONDARY)
    status = fig.text(10 / W, 1 - 58 / H, "", fontsize=9.2, va="top", color=INK_PRIMARY,
                      fontweight="bold")
    panels = {}
    for i in cases:
        c = cases[i]
        col, row = (i - 1) % cols, (i - 1) // cols
        x0, y0 = 8 + col * (pw + 4), 84 + row * (ph + 18)
        ax = axes_box(fig, x0, y0 + 60, *size3d, W, H)
        ax.set_xlim(*limits[0])
        ax.set_ylim(*limits[1])
        ax.set_axis_off()
        im = ax.imshow(np.asarray(back), extent=(*limits[0], *limits[1]), origin="upper",
                       interpolation="nearest", zorder=0, aspect="auto")
        im2 = ax.imshow(np.zeros((size3d[1], size3d[0], 4), np.uint8),
                        extent=(*limits[0], *limits[1]), origin="upper",
                        interpolation="nearest", zorder=1, aspect="auto")
        path_line, = ax.plot([], [], color=INK_PRIMARY, lw=1.0, zorder=3)
        dot, = ax.plot([], [], "o", color=LIFT_COLOR, ms=4, zorder=4)
        j = c["judged"]
        era = j["era"]
        fig.text((x0 + 4) / W, 1 - (y0 + 2) / H, f"모드 {i}: {MODE_NAMES[i]}", fontsize=10.5,
                 fontweight="bold", va="top", color=INK_PRIMARY)
        fig.text((x0 + 4) / W, 1 - (y0 + 21) / H,
                 f"f_n Chrono {j['judged_value']['f_Hz']:.4f} Hz · 기준 {f_ref[i - 1]:.4f} Hz "
                 f"({(j['judged_value']['f_Hz'] / f_ref[i - 1] - 1) * 100:+.3f} %)",
                 fontsize=8.4, va="top", color=INK_PRIMARY)
        fig.text((x0 + 4) / W, 1 - (y0 + 37) / H,
                 f"ζ Chrono {j['judged_value']['zeta']:.5f} · 기준 {zeta_ref[i - 1]:.5f} "
                 f"({(j['judged_value']['zeta'] / zeta_ref[i - 1] - 1) * 100:+.2f} %) · ERA "
                 f"{era['f_Hz']:.4f} Hz / {era['zeta']:.5f}", fontsize=8.0, va="top",
                 color=INK_SECONDARY)
        fig.text((x0 + pw - 8) / W, 1 - (y0 + 64) / H,
                 f"과장 ×{c['amp']:.0f}\n실제 최대 {c['max_true_disp_mm']:.2f} mm\n실행 modes_{c['run']}",
                 fontsize=7.6, va="top", ha="right", color=INK_SECONDARY)
        mini = axes_box(fig, x0 + 40, y0 + 370, pw - 60, 48, W, H)
        style(mini)
        n_end = c["t_peak"] + (MODE_LAPS[-1] + 1.3) * c["period"]
        m = c["t"] <= n_end
        mini.plot(c["t"][m], c["eta"][m] * 1e3, color=SERIES[0], lw=0.9)
        mini.set_xlim(0, n_end)
        mini.set_ylabel("η [1e-3]", fontsize=7, color=INK_SECONDARY, labelpad=1)
        mini.set_xlabel("가진 뒤 t [s]  (음영 = 지금 그리는 주기)", fontsize=7, color=INK_SECONDARY,
                        labelpad=0)
        span = mini.axvspan(0, 0, color="#cde2fb", alpha=0.9, lw=0, zorder=0)
        cur, = mini.plot([], [], "o", color=LIFT_COLOR, ms=3.5, zorder=5)
        lap_text = fig.text((x0 + 4) / W, 1 - (y0 + 64) / H, "", fontsize=8.2, va="top",
                            color=INK_PRIMARY)
        panels[i] = dict(im2=im2, path=path_line, dot=dot, span=span, cur=cur, lap=lap_text)
    frames, durations, frame_plan = [], [], []
    for lap, k in plan:
        for i in cases:
            c = cases[i]
            pn = panels[i]
            pn["im2"].set_data(np.asarray(from_png(images[(i, lap, k)])))
            ts = c["t_peak"] + (lap + np.linspace(0, 1, 65)) * c["period"]
            tops = np.array([pose(i, float(np.interp(tt, c["t"], c["eta"])))[3] for tt in ts])
            sp = cadr.screen(tops, "s4")
            pn["path"].set_data(sp[:, 0], sp[:, 1])
            t_f = c["t_peak"] + (lap + k / MODE_PHASES) * c["period"]
            e = float(np.interp(t_f, c["t"], c["eta"]))
            top = cadr.screen(pose(i, e)[3], "s4")[0]
            pn["dot"].set_data([top[0]], [top[1]])
            a0 = c["t_peak"] + lap * c["period"]
            pn["span"].set_x(a0)
            pn["span"].set_width(c["period"])
            pn["cur"].set_data([t_f], [e * 1e3])
            pn["lap"].set_text(f"가진 뒤 {lap}주기째\nt = {t_f:.3f} s")
        status.set_text(f"주기 {MODE_LAPS.index(lap) + 1}/{len(MODE_LAPS)}: 가진 뒤 {lap}번째 주기 "
                        f"(위상 {k}/{MODE_PHASES}) — 같은 주기 수에서 진폭이 덜 남은 모드일수록 ζ가 크다")
        frames.append(figure_to_image(fig))
        d = 75
        if k == 0:
            d = 500 if lap == 0 else 300
        durations.append(d)
        frame_plan.append([lap, k, d])
    plt.close(fig)
    summary["modes_gif"] = write_gif(frames, durations, OUT["modes"])
    summary["modes"] = {
        "pose_source": {"case": POSE_CASE, "row": 0, "params_sha256":
                        pose_meta.get("params_sha256", "")[:16],
                        "body_pos_m": pos0.tolist(), "s_motor_m": s_motor.tolist()},
        "laps_cycles_after_excitation": list(MODE_LAPS), "phases_per_cycle": MODE_PHASES,
        "exaggeration_target_m": MODE_PEAK_M, "mesh_cell_m": MODE_CELL_M,
        "per_mode": {i: {"run": c["run"], "dir": c["dir"], "f_damped_Hz": c["f_d"],
                         "t_lap0_start_s": c["t_peak"], "exaggeration": c["amp"],
                         "max_true_displacement_lap0_mm": c["max_true_disp_mm"],
                         "f_judged_Hz": c["judged"]["judged_value"]["f_Hz"],
                         "zeta_judged": c["judged"]["judged_value"]["zeta"],
                         "f_ref_Hz": float(f_ref[i - 1]), "zeta_ref": float(zeta_ref[i - 1])}
                     for i, c in cases.items()},
        "render_s": t_render, "total_s": time.perf_counter() - t_start,
        "frames_plan (lap, phase, ms)": frame_plan,
    }


# =============================================================================================
# GIF 2: V8(b) energy budget
# =============================================================================================


class Budget:
    TERMS = ("kinetic", "gravity", "spring", "D_visc", "D_slip", "residual")
    LABELS = {"kinetic": "운동 E_kin", "gravity": "중력 ΔV_g", "spring": "스프링 ΔV_s(패드+부싱)",
              "D_visc": "점성 소산 D_visc", "D_slip": "미끄럼 소산 D_slip",
              "residual": "수치 손실 -R"}

    def __init__(self, case_dir: Path):
        data = np.load(case_dir / "budget.npz")
        cols = [str(c) for c in data["columns"]]
        tab = data["table"]
        g = {c: tab[:, k] for k, c in enumerate(cols)}
        self.t_abs = g["t_s"]
        self.t = g["t_s"] - g["t_s"][0]
        spring = g["contact_spring"] + g["bushing_spring"]
        mech = g["kinetic"] + g["gravity"] + spring
        self.R = (mech - mech[0]) + g["dissipated_viscous"] + g["dissipated_slip"] - g["motor_work"]
        self.terms = {
            "kinetic": g["kinetic"],
            "gravity": g["gravity"] - g["gravity"][0],
            "spring": spring - spring[0],
            "D_visc": g["dissipated_viscous"],
            "D_slip": g["dissipated_slip"],
            "residual": -self.R,
        }
        self.W = g["motor_work"]
        self.E0 = float(g["kinetic"][0])
        self.D = g["dissipated_viscous"] + g["dissipated_slip"]
        self.raw = g


def render_energy(ctx: Context, jobs: int, summary: dict):
    t_start = time.perf_counter()
    eidx = read_json(ENERGY_INDEX)
    case_dir = ROOT / eidx[ENERGY_CASE]["dir"]
    verify = read_json(ENERGY_VERIFY)["cases"][ENERGY_CASE]
    bud = Budget(case_dir)
    a, ev, meta = load_record(case_dir, ctx.params)
    t_abs = a["t"]
    t = t_abs - t_abs[0]
    if abs(bud.t_abs[0] - t_abs[0]) > 1e-6 or len(bud.t) != len(t):
        raise SystemExit("budget.npz and record time bases differ")
    pos, rot = a["body_pos"], quat_matrix(a["body_quat_wxyz"])
    s_motor = a["s_motor"][0].copy()
    pos0, rot0 = pos[0].copy(), rot[0].copy()
    normal = np.asarray(verify["start"]["normal_world"], float)
    anchor = a["bushing_anchor"]
    plane_pt = np.nanmean(anchor[0], axis=0)
    contact = a["pad_in_contact"]
    N_kN = a["F_contact_n"] / 1e3
    events = list(zip(ev["t"] - t_abs[0], ev["leg"], ev["kind"], strict=True))
    centres_b = ctx.sphere_centres_body(s_motor)
    # frame plan
    times = list(np.round(np.arange(0.0, 3.0, 0.02), 4)) + list(np.arange(3.0, 30.0 + 1e-9, 0.5))
    durations = [1200] + [80] * (sum(1 for x in times if x < 3.0) - 1)
    durations += [110] * (len(times) - len(durations))
    durations[-1] = 2500
    idx = [int(np.clip(np.searchsorted(t, x - 1e-9), 0, len(t) - 1)) for x in times]
    K = ENERGY_K
    rect = FLOOR_RECT

    def draw_pose(i):
        rd = rot[i] @ rot0.T
        theta = rotvec_from_matrix(rd)
        rk = rotvec_matrix(K * theta)
        p = pos0 + K * (pos[i] - pos0)
        r = rk @ rot0
        return p, r

    def rotvec_from_matrix(m):
        from scipy.spatial.transform import Rotation

        return Rotation.from_matrix(m).as_rotvec()

    size3d = (700, 470)
    body_pts = ctx.body_points(s_motor)
    pts = [body_pts @ rot0.T + pos0]
    for i in idx[:: 5]:
        p, r = draw_pose(i)
        pts.append(body_pts[::4] @ r.T + p)
    z_of = lambda x, y: plane_pt[2] - (normal[0] * (x - plane_pt[0])  # noqa: E731
                                       + normal[1] * (y - plane_pt[1])) / normal[2]
    pts.append(np.array([[x, y, z_of(x, y)] for x in rect[0] for y in rect[1]]))
    limits = cadr.fit_limits(cadr.screen(np.vstack(pts), "s4"), size3d, 0.05)
    floor = (plane_pt, normal, rect)
    tasks = []
    for n, i in enumerate(idx):
        p, r = draw_pose(i)
        lifted = [LEG_ORDER[k] for k in range(4) if not contact[i, k]]
        tasks.append({"key": n, "pos": p, "rot": r, "s_motor": s_motor,
                      "auger_travel_m": ctx.auger_travel, "direction": ctx.direction,
                      "limits": limits, "size": size3d, "floor": floor, "lifted": lifted})
    print(f"  energy: {len(tasks)} renders", flush=True)
    images = render_many(tasks, str(ctx.parts_pickle), jobs, ctx.cpu)
    t_render = time.perf_counter() - t_start

    W, H = 1500, 930
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=SURFACE)
    fig.text(10 / W, 1 - 10 / H, "S4 V8(b) 에너지 수지 — 경사 2°(pitch) 바닥, 킥 0.5 m/s, 30 s, Δt 2e-4 s "
             "(판정 사례) — 판정: 통과 (dynamics_model.md 개정 19, 5.8절)", fontsize=13.5,
             fontweight="bold", va="top", color=INK_PRIMARY)
    fig.text(10 / W, 1 - 36 / H,
             "R(t) = ΔE_mech + D_visc + D_slip - W_motor (E_mech = 운동 + 중력 + 패드 접촉 ½k_nδ² + 부싱 ½k_t|x-a|²). "
             "킥 = 바닥면에 투영한 [0.8, 0.6, 0] 방향 강체 병진 0.5 m/s (가정). 0~3 s는 20 ms 간격(느리게), "
             "3~30 s는 0.5 s 간격.", fontsize=8.4, va="top", color=INK_SECONDARY)
    status = fig.text(10 / W, 1 - 56 / H, "", fontsize=10, va="top", color=INK_PRIMARY,
                      fontweight="bold")
    # 3D
    ax3 = axes_box(fig, 8, 80, *size3d, W, H)
    ax3.set_xlim(*limits[0])
    ax3.set_ylim(*limits[1])
    ax3.set_axis_off()
    im3 = ax3.imshow(np.zeros((size3d[1], size3d[0], 4), np.uint8), extent=(*limits[0],
                     *limits[1]), origin="upper", interpolation="nearest", aspect="auto")
    fig.text(14 / W, 1 - 88 / H, f"기계 (C8 메시 + C11 색). 상부체 운동 ×{K:.0f} 과장(킥 시점 자세 기준), "
             "패드 빨강 = 부상(접촉 없음)", fontsize=8.2, va="top", color=INK_SECONDARY)
    pad_labels = []
    for leg in LEG_ORDER:
        pad_labels.append(ax3.text(0, 0, "", fontsize=7.8, color=LEG_COLORS[leg], ha="center",
                                   va="top", fontweight="bold", zorder=6,
                                   bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none",
                                             alpha=0.85)))
    # pad slip panels (plan view, x forward = right, y left = up)
    slip_axes = {}
    order_xy = {"RL": (0, 0), "FL": (1, 0), "RR": (0, 1), "FR": (1, 1)}
    a0 = np.where(np.isnan(anchor[0]), 0, anchor[0])
    rel_anchor = (anchor - a0[None]) * 1e3
    centres_w = np.einsum("nij,kj->nki", rot, centres_b) + pos[:, None, :]
    rel_centre = (centres_w - centres_w[0][None]) * 1e3
    both = np.concatenate([rel_anchor[..., :2].reshape(-1, 2), rel_centre[..., :2].reshape(-1, 2)])
    lo, hi = np.nanmin(both, axis=0), np.nanmax(both, axis=0)
    mid = (lo + hi) / 2
    half_x = max((hi[0] - lo[0]) / 2, (hi[1] - lo[1]) / 2 * 270 / 130) * 1.12
    half_y = half_x * 130 / 270
    # slip of the bushing fixed point: steps with contact before and after (re-creation jumps
    # excluded); path length and net vector (= verify slip_window_m definition)
    step_ok = contact[1:] & contact[:-1]
    d_anchor = np.where(step_ok[..., None], np.diff(anchor[..., :2], axis=0), 0.0)
    d_anchor = np.nan_to_num(d_anchor)
    slip_path_mm = np.concatenate([np.zeros((1, 4)),
                                   np.cumsum(np.linalg.norm(d_anchor, axis=2), axis=0)]) * 1e3
    slip_net_mm = np.linalg.norm(np.concatenate([np.zeros((1, 4, 2)),
                                                 np.cumsum(d_anchor, axis=0)]), axis=2) * 1e3
    for leg, (cx, cy) in order_xy.items():
        k = LEG_ORDER.index(leg)
        ax = axes_box(fig, 50 + cx * 330, 588 + cy * 168, 270, 130, W, H)
        style(ax, title=f"{leg}: 부싱 고정점(굵은 선)·패드 구 중심(가는 선) 이동 [mm]", size=7.8)
        ax.set_xlim(mid[0] - half_x, mid[0] + half_x)
        ax.set_ylim(mid[1] - half_y, mid[1] + half_y)
        line_a, = ax.plot([], [], color=LEG_COLORS[leg], lw=2.0)
        line_c, = ax.plot([], [], color=LEG_COLORS[leg], lw=0.6, alpha=0.7)
        dot_a, = ax.plot([], [], "o", color=LEG_COLORS[leg], ms=5, mec="white", mew=0.8,
                         zorder=5)
        ev_create, = ax.plot([], [], "^", color=PASS_COLOR, ms=5, mfc="none", mew=1.2, zorder=6)
        ev_remove, = ax.plot([], [], "v", color=LIFT_COLOR, ms=5, mfc="none", mew=1.2, zorder=6)
        txt = ax.text(0.01, 0.04, "", transform=ax.transAxes, fontsize=7.2, color=INK_PRIMARY)
        slip_axes[leg] = dict(k=k, a=line_a, c=line_c, dot=dot_a, cr=ev_create, rm=ev_remove,
                              txt=txt)
    fig.text(50 / W, 1 - 910 / H, "평면도(가로 x 전방, 세로 y 좌측, 같은 축척 mm, 킥 시점 기준). △ 부싱 생성(재접지) "
             "▽ 부싱 소멸(부상). 고정점은 Coulomb 항복(미끄럼) 때만 움직인다", fontsize=7.4,
             va="top", color=INK_SECONDARY)
    # energy stacked bar
    x0 = 740
    axb = axes_box(fig, x0, 100, 730, 120, W, H)
    style(axb, title="(a) 에너지 배분 [J] (현재 시각): 합 = 킥 운동 에너지 E_kin0")
    axb.set_xlim(-300, bud.E0 * 1.08)
    axb.set_ylim(-1.0, 0.6)
    axb.set_yticks([])
    axb.axvline(bud.E0, color=INK_PRIMARY, lw=1.0, ls=(0, (4, 2)))
    axb.text(bud.E0, 0.5, f" E_kin0 {bud.E0:.1f} J", fontsize=7.5, va="center", ha="right",
             color=INK_PRIMARY)
    axb.axvline(0, color=INK_SECONDARY, lw=0.7)
    colours = dict(zip(Budget.TERMS[:5], SERIES[:5], strict=True))
    colours["residual"] = INK_SECONDARY
    bars = {name: axb.barh(0, 0, height=0.5, color=colours[name], edgecolor="white", lw=1.0)[0]
            for name in Budget.TERMS}
    bar_text = axb.text(-280, -0.72, "", fontsize=7.4, va="center",
                        color=INK_PRIMARY)
    handles = [matplotlib.patches.Patch(color=colours[n], label=Budget.LABELS[n])
               for n in Budget.TERMS]
    axb.legend(handles=handles, fontsize=7.2, ncol=6, loc="lower left",
               bbox_to_anchor=(0.0, 1.13), frameon=False, handlelength=1.2, columnspacing=1.0)
    # term lines
    axl = axes_box(fig, x0, 285, 730, 230, W, H)
    style(axl, title="(b) 에너지 항 누적 [J] 대 시간 (점 = 현재)", xlabel="킥 뒤 t [s]")
    dots = {}
    for name in Budget.TERMS:
        y = bud.terms[name]
        axl.plot(bud.t, y, color=colours[name], lw=1.4, label=Budget.LABELS[name])
        dots[name], = axl.plot([], [], "o", color=colours[name], ms=4, mec="white", mew=0.6)
    axl.set_xlim(0, 30)
    axl.axhline(0, color=INK_SECONDARY, lw=0.6)
    cursor_l = axl.axvline(0, color=INK_PRIMARY, lw=0.8, alpha=0.6)
    # residual
    axr = axes_box(fig, x0, 570, 350, 300, W, H)
    style(axr, title="(c) 잔차 R(t) [J]과 V8(b) 판정선", xlabel="킥 뒤 t [s]")
    axr.plot(bud.t, bud.R, color=INK_PRIMARY, lw=1.3, label="R(t)")
    lim1 = 1e-3 * bud.E0
    axr.axhline(lim1, color=LIMIT_COLOR, lw=1.0, ls=(0, (5, 3)),
                label=f"① 주입 상한 +{lim1:.2f} J (1e-3 E_ref)")
    axr.plot(bud.t, -0.1 * bud.D, color=LIMIT_COLOR, lw=1.0, ls=":",
             label="④ 끝 하한 -0.1(D_visc+D_slip)")
    axr.set_xlim(0, 30)
    axr.set_ylim(min(-0.1 * bud.D[-1] * 1.05, bud.R.min() * 1.3), 30)
    axr.legend(fontsize=7, loc="lower left", frameon=True, framealpha=0.9)
    r_dot, = axr.plot([], [], "o", color=LIFT_COLOR, ms=4)
    r_text = axr.text(0.02, 0.96, "", transform=axr.transAxes, fontsize=7.6, va="top",
                      color=INK_PRIMARY, bbox=dict(boxstyle="round,pad=0.2", fc="white",
                                                   ec="none", alpha=0.9))
    # normal forces
    axn = axes_box(fig, x0 + 395, 570, 335, 300, W, H)
    style(axn, title="(d) 패드 수직 반력 [kN] (0 = 부상)", xlabel="킥 뒤 t [s]")
    n_dots = []
    for k, leg in enumerate(LEG_ORDER):
        axn.plot(t, N_kN[:, k], color=LEG_COLORS[leg], lw=0.9, label=leg)
        d, = axn.plot([], [], "o", color=LEG_COLORS[leg], ms=4, mec="white", mew=0.6)
        n_dots.append(d)
    t_ev_end = float(max(e[0] for e in events)) if events else 3.0
    n_xmax = float(np.ceil(t_ev_end + 0.5))
    axn.set_xlim(0, n_xmax)
    axn.legend(fontsize=7, ncol=4, loc="upper right", frameon=True, framealpha=0.9)
    axn.set_title(f"(d) 패드 수직 반력 [kN] (0 = 부상) · 마지막 부싱 사건 "
                  f"{t_ev_end:.2f} s", fontsize=8.5, loc="left", color=INK_PRIMARY, pad=4)
    n_cursor = axn.axvline(0, color=INK_PRIMARY, lw=0.8, alpha=0.6)
    frames = []
    floor_n = normal
    for n, (tf, i) in enumerate(zip(times, idx, strict=True)):
        im3.set_data(np.asarray(from_png(images[n])))
        p, r = draw_pose(i)
        for k, leg in enumerate(LEG_ORDER):
            c = r @ centres_b[k] + p
            sp = cadr.screen(c - 0.35 * floor_n, "s4")[0]
            pad_labels[k].set_position((sp[0], sp[1]))
            state = "부상" if not contact[i, k] else f"{N_kN[i, k]:.0f} kN"
            pad_labels[k].set_text(f"{leg} {state}")
        for leg, sa in slip_axes.items():
            k = sa["k"]
            sa["a"].set_data(rel_anchor[: i + 1, k, 0], rel_anchor[: i + 1, k, 1])
            sa["c"].set_data(rel_centre[: i + 1, k, 0], rel_centre[: i + 1, k, 1])
            last = rel_anchor[i, k] if contact[i, k] else rel_centre[i, k]
            sa["dot"].set_data([last[0]], [last[1]])
            cr = [(e_t, e_k) for e_t, e_l, e_k in events if e_l == k and e_t <= tf + 1e-9]
            xs_c, ys_c, xs_r, ys_r = [], [], [], []
            for e_t, e_k in cr:
                j = int(np.clip(np.searchsorted(t, e_t - 1e-9), 0, len(t) - 1))
                pnt = rel_centre[j, k]
                (xs_c if e_k == 1 else xs_r).append(pnt[0])
                (ys_c if e_k == 1 else ys_r).append(pnt[1])
            sa["cr"].set_data(xs_c, ys_c)
            sa["rm"].set_data(xs_r, ys_r)
            sa["txt"].set_text(f"미끄럼 경로 {slip_path_mm[i, k]:.1f} mm · 순 {slip_net_mm[i, k]:.1f} mm"
                               f" · 사건 {len(cr)}")
        left_neg = 0.0
        left_pos = 0.0
        for name in Budget.TERMS:
            v = float(bud.terms[name][i])
            if v >= 0:
                bars[name].set_x(left_pos)
                bars[name].set_width(v)
                left_pos += v
            else:
                bars[name].set_x(left_neg + v)
                bars[name].set_width(-v)
                left_neg += v
        bar_text.set_text("  ".join(f"{Budget.LABELS[nm].split(' ')[-1]} {bud.terms[nm][i]:+.1f}"
                                    for nm in Budget.TERMS)
                          + f"   합 {sum(bud.terms[nm][i] for nm in Budget.TERMS):.1f} J")
        for name in Budget.TERMS:
            dots[name].set_data([bud.t[i]], [bud.terms[name][i]])
        cursor_l.set_xdata([bud.t[i]] * 2)
        r_dot.set_data([bud.t[i]], [bud.R[i]])
        r_text.set_text(f"R = {bud.R[i]:+.2f} J\nmax_t R = {bud.R[: i + 1].max():+.3f} J\n"
                        f"R / (D_visc+D_slip) = "
                        f"{bud.R[i] / bud.D[i] * 100 if bud.D[i] > 1 else 0:+.2f} %")
        for k in range(4):
            n_dots[k].set_data([t[i]], [N_kN[i, k]])
        n_cursor.set_xdata([min(t[i], n_xmax)] * 2)
        n_cursor.set_visible(t[i] <= n_xmax)
        lifted = [LEG_ORDER[k] for k in range(4) if not contact[i, k]]
        status.set_text(f"t = {t[i]:6.3f} s (킥 뒤)   E_kin {bud.terms['kinetic'][i]:7.1f} J   "
                        f"D_visc {bud.terms['D_visc'][i]:6.1f} J   D_slip {bud.terms['D_slip'][i]:6.1f} J   "
                        f"R {bud.R[i]:+7.2f} J   부상: {', '.join(lifted) if lifted else '없음'}")
        frames.append(figure_to_image(fig))
    plt.close(fig)
    summary["energy_gif"] = write_gif(frames, durations, OUT["energy"])
    jb = verify["budget"]
    summary["energy"] = {
        "case": ENERGY_CASE, "dir": rel(case_dir), "params_sha256":
            meta.get("params_sha256", "")[:16], "exaggeration_body_motion": K,
        "frames_plan (t_s, ms)": [[round(float(x), 3), d] for x, d in zip(times, durations,
                                                                          strict=True)],
        "value_checks": {
            "R_end_recomputed_J": float(bud.R[-1]), "R_end_verify_J": jb["residual_end_J"],
            "R_max_recomputed_J": float(bud.R.max()),
            "R_max_verify_J": jb["residual_max_signed_J"],
            "E_kin0_recomputed_J": bud.E0, "E_kin0_verify_J": jb["E_kin0_J"],
            "sum_terms_end_minus_E_kin0_J": float(sum(bud.terms[n][-1] for n in Budget.TERMS)
                                                  - bud.E0 + bud.W[-1]),
            "events_record": len(events),
            "events_verify": verify["bushing"]["events_window"],
            "anchor_slip_net_mm_record (contact steps, vector sum)": slip_net_mm[-1].tolist(),
            "anchor_slip_path_mm_record (contact steps)": slip_path_mm[-1].tolist(),
            "slip_window_mm_verify": [v * 1e3 for v in verify["bushing"]["slip_window_m"]],
        },
        "render_s": t_render, "total_s": time.perf_counter() - t_start,
    }


# =============================================================================================
# PNG 3: dashboard
# =============================================================================================


def _check_counts(node, acc):
    if isinstance(node, dict):
        if "passed" in node and "id" in node and "item" in node:
            acc[0] += 1
            acc[1] += bool(node["passed"])
            return
        for v in node.values():
            _check_counts(v, acc)
    elif isinstance(node, list):
        for v in node:
            _check_counts(v, acc)


def table(ax, cells, header, widths=None, size=7.6, pass_col=None):
    ax.set_axis_off()
    tb = ax.table(cellText=cells, colLabels=header, loc="upper left", cellLoc="center",
                  colLoc="center", colWidths=widths)
    tb.auto_set_font_size(False)
    tb.set_fontsize(size)
    tb.scale(1.0, 1.25)
    for (r, c), cell in tb.get_celld().items():
        cell.set_edgecolor("#d6d5d0")
        cell.set_linewidth(0.5)
        if r == 0:
            cell.set_facecolor("#f1efe9")
            cell.set_text_props(fontweight="bold", color=INK_PRIMARY)
        elif pass_col is not None and c == pass_col:
            txt = cell.get_text().get_text()
            cell.set_text_props(color=PASS_COLOR if txt.startswith("통과") else FAIL_COLOR,
                                fontweight="bold")
    return tb


def render_summary(summary: dict):
    mv = read_json(MODES_VERIFY)
    ev = read_json(ENERGY_VERIFY)
    chk = read_json(S4_CHECK)
    W, H = 1700, 1180
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=SURFACE)
    acc_m, acc_e = [0, 0], [0, 0]
    _check_counts({k: v for k, v in mv.items() if not k.startswith("info")}, acc_m)
    n_info_failed = len(mv.get("info_checks_failed", []))
    _check_counts(ev, acc_e)
    fig.text(10 / W, 1 - 10 / H, "S4 종합: V7 6개 모드 · β 감도 · 다리 감쇠 감도 · V8(b) 에너지 수지 — 상단, "
             "L1, Δt 2e-4 s", fontsize=15, fontweight="bold", va="top", color=INK_PRIMARY)
    fig.text(10 / W, 1 - 40 / H,
             f"최종 판정: 통과 (dyn, dynamics_model.md 개정 19 5.8절; 독립 확인 s4_check.json). 사전 판정 "
             f"A 갈래 {acc_m[1]}/{acc_m[0]} · B 갈래 {acc_e[1]}/{acc_e[0]} 통과\n"
             f"(정보 항목 미달 {n_info_failed}건은 기록만: ζ_leg 0.10 4차 맞춤 잔차 → ERA 값 사용; "
             f"verify_S4_L1_modes.json all_passed {mv['all_passed']}, verify_S4_L1_energy.json "
             f"all_passed {ev['all_passed']})", fontsize=9.6, va="top", color=PASS_COLOR,
             fontweight="bold", linespacing=1.3)
    # (A) V7 utilisation
    judged = {j["mode"]: j for j in mv["v7"]["judged"]}
    f_ref = np.array([judged[i]["f_ref_Hz"] for i in range(1, 7)])
    z_ref = np.array([judged[i]["zeta_ref"] for i in range(1, 7)])
    f_p = np.array([judged[i]["f_proj_Hz"] for i in range(1, 7)])
    z_p = np.array([judged[i]["zeta_proj"] for i in range(1, 7)])
    f_e = np.array([judged[i]["era"]["f_Hz"] for i in range(1, 7)])
    z_e = np.array([judged[i]["era"]["zeta"] for i in range(1, 7)])
    ax = axes_box(fig, 60, 95, 520, 300, W, H)
    style(ax, title="(A) V7 6개 모드: |Chrono - 기준| / 허용 [%] (100 % = 허용선)", xlabel="모드",
          size=9.5)
    xs = np.arange(1, 7)
    series = [("f 투영 (허용 ±3 %)", np.abs(f_p / f_ref - 1) / 0.03),
              ("f ERA", np.abs(f_e / f_ref - 1) / 0.03),
              ("ζ 투영 (허용 ±30 %)", np.abs(z_p / z_ref - 1) / 0.30),
              ("ζ ERA", np.abs(z_e / z_ref - 1) / 0.30)]
    for k, (lab, v) in enumerate(series):
        ax.bar(xs + (k - 1.5) * 0.2, np.maximum(v * 100, 1e-4), 0.18, color=SERIES[k], label=lab,
               edgecolor="white", lw=0.8)
    ax.set_yscale("log")
    ax.set_ylim(1e-3, 300)
    ax.axhline(100, color=LIMIT_COLOR, lw=1.2, ls=(0, (5, 3)))
    ax.text(6.45, 115, "허용선", color=LIMIT_COLOR, fontsize=7.5, ha="right", va="bottom")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_xticks(xs, [f"{i}\n{f_ref[i - 1]:.3f} Hz" for i in xs], fontsize=7.2)
    ax.legend(fontsize=7, ncol=2, loc="upper left", frameon=True, framealpha=0.9)
    ax.set_ylabel("허용 사용률 [%] (log)", fontsize=7.8, color=INK_SECONDARY)
    cells = [[str(i), f"{f_p[i - 1]:.4f}", f"{f_ref[i - 1]:.4f}",
              f"{(f_p[i - 1] / f_ref[i - 1] - 1) * 100:+.3f}", f"{z_p[i - 1]:.5f}",
              f"{z_ref[i - 1]:.5f}", f"{(z_p[i - 1] / z_ref[i - 1] - 1) * 100:+.2f}",
              f"{judged[i]['era']['mac_vs_phi']:.5f}"] for i in xs]
    table(axes_box(fig, 600, 95, 520, 190, W, H), cells,
          ["모드", "f Chrono [Hz]", "f 기준 [Hz]", "차 [%]", "ζ Chrono", "ζ 기준", "차 [%]", "ERA MAC"],
          widths=[0.07, 0.15, 0.14, 0.11, 0.14, 0.13, 0.11, 0.15], size=7.6)
    fig.text(600 / W, 1 - 290 / H, "ζ Chrono = 투영 맞춤 ζ - ζ_num(r ω Δt/2). 기준 = reference.json "
             "V7_ball_centre_bushing_rev13 (감쇠 진동수).\n투영·ERA 교차: f ≤ 0.03 %, ζ ≤ 0.7 %, 누설 최대 "
             f"{max(judged[i]['era']['leakage'] for i in xs):.3f}(4차).", fontsize=7.8, va="top",
             color=INK_SECONDARY)
    # (B) beta frequencies
    betas = [("beta_6.9e+08", 0.69), ("beta_1.0e+09", 1.0), ("beta_1.6e+09", 1.6)]
    ax = axes_box(fig, 1170, 95, 500, 300, W, H)
    style(ax, title="(B) β 감도: 고유진동수 [Hz] 대 β_eff [GPa]", xlabel="β_eff [GPa]", size=9.5)
    bx = np.array([b for _, b in betas])
    by_label = np.array([mv["beta"][k]["chrono"]["f_era_by_nominal_label_Hz"] for k, _ in betas])
    ref_sorted = np.array([mv["beta"][k]["reference"]["f_Hz_top_ball_centre_rev13"]
                           for k, _ in betas])
    for m in range(6):
        ax.plot(bx, by_label[:, m], "-o", color=SERIES[m], lw=1.4, ms=4,
                label=f"모드 {m + 1} (공칭 Φ 라벨)")
    for b, row in zip(bx, ref_sorted, strict=True):
        ax.plot([b] * 6, row, "_", color=INK_PRIMARY, ms=14, mew=1.4)
    ax.plot([], [], "_", color=INK_PRIMARY, ms=12, mew=1.4, label="기준(진동수 순)")
    ax.annotate("1.6 GPa: 5차(heave)가 6차 위로\n(5·6 순서 바뀜, 기준 모델도 같음)", xy=(1.58, 8.75),
                xytext=(1.0, 4.3), fontsize=7.4, color=INK_PRIMARY,
                arrowprops=dict(arrowstyle="->", color=INK_SECONDARY, lw=0.8))
    ax.legend(fontsize=6.6, ncol=2, loc="lower right", frameon=True, framealpha=0.9)
    ax.set_xticks(bx)
    ax.set_ylim(1.0, 10.2)
    # (B2) beta statics table (rows = quantity, cells = Chrono / linear reference)
    qty = [("FL 침투 [mm]", lambda c: c["penetration_mm"][0], lambda r: r["penetration_mm"][0],
            "{:.3f}"),
           ("정적 pitch [°]", lambda c: c["static_pitch_deg"], lambda r: r["static_pitch_deg"],
            "{:.5f}"),
           ("FL +1 mm ΔF_FL [kN]", lambda c: c["dF_FL_plus1mm_N"][0] / 1e3,
            lambda r: r["dF_per_mm_FL_N"][0] / 1e3, "{:.3f}"),
           ("FL+ F_min 이동 [mm]", lambda c: c["F_min_mm"], lambda r: r["FL+_F_min_mm"], "{:.2f}"),
           ("FL+ 부상 이동 [mm]", lambda c: c["liftoff_mm"], lambda r: r["FL+_liftoff_mm"],
            "{:.2f}")]
    rows = []
    for name, fc, fr, fmt in qty:
        row = [name]
        for k, _ in betas:
            r, c = mv["beta"][k]["reference"], mv["beta"][k]["chrono"]
            row.append(f"{fmt.format(fc(c))} / {fmt.format(fr(r))}")
        rows.append(row)
    rows.append(["판정(각 23항목)"] + ["통과" if all(ch["passed"] for ch in mv["beta"][k]["checks"])
                                    else "실패" for k, _ in betas])
    tb = table(axes_box(fig, 1170, 425, 500, 120, W, H), rows,
               ["항목 (Chrono / 기준)", "β 0.69 GPa", "β 1.0 GPa", "β 1.6 GPa"],
               widths=[0.31, 0.23, 0.23, 0.23], size=7.2)
    for col in (1, 2, 3):
        tb[len(rows), col].set_text_props(color=PASS_COLOR, fontweight="bold")
    fig.text(1170 / W, 1 - 575 / H, "칸 = Chrono / 선형 기준. V5·V6 차(-1.9~+1.6 %)는 P-δ 전부: 독립 정확 "
             "정역학과\nΔF ≤ 1.4 N, 문턱 ≤ 0.001 mm (s4_check.json C). 허용 V2 ±5 %, V3 ±0.002°, V5·V6 ±5 %.",
             fontsize=7.6, va="top", color=INK_SECONDARY)
    # (C) damping sensitivity
    ax = axes_box(fig, 60, 470, 520, 230, W, H)
    style(ax, title="(C) 다리 감쇠 감도: ζ Chrono / 1차 기대값(공칭 ζ × ζ_leg/0.03)", xlabel="모드",
          size=9.5)
    for k, z in enumerate(("0.01", "0.10")):
        ms = mv["damping"][z]["modes"]
        ratio = np.array([m["judged_value"]["zeta"] / m["zeta_first_order_expectation"]
                          for m in ms])
        ax.bar(xs + (k - 0.5) * 0.36, ratio, 0.34, color=SERIES[k], label=f"ζ_leg {z} (Δt "
               f"{mv['damping'][z]['dt_s']:g} s)", edgecolor="white", lw=0.8)
        for x, v, m in zip(xs + (k - 0.5) * 0.36, ratio, ms, strict=True):
            mark = "*" if m["judged_value"]["source"] == "ERA" else ""
            ax.text(x, v + 0.01, f"{v:.3f}{mark}", fontsize=6.4, ha="center", va="bottom",
                    color=INK_PRIMARY, rotation=90)
    ax.axhspan(0.7, 1.3, color="#e9f3e9", zorder=0)
    ax.axhline(1.3, color=LIMIT_COLOR, lw=1.0, ls=(0, (5, 3)))
    ax.axhline(0.7, color=LIMIT_COLOR, lw=1.0, ls=(0, (5, 3)))
    ax.set_ylim(0.6, 1.4)
    ax.set_xticks(xs)
    ax.legend(fontsize=7.2, loc="lower left", frameon=True, framealpha=0.9)
    ax.text(0.0, -0.17, "허용 ±30 % (녹색 띠, 빨간 점선). * = ERA 값(맞춤 잔차 > 0.05). 기대값은 선형 복소 "
            "모드와 ≤ 0.12 % (s4_check.json D)", transform=ax.transAxes, fontsize=7,
            color=INK_SECONDARY)
    # (D) V8(b) checks table
    case = ev["cases"][ENERGY_CASE]
    cks = {c["id"]: c for c in case["checks"]}
    dts = {c["item"].split("dt ")[-1]: c for c in ev["dt_sensitivity"]["checks"]}
    pairs = ev["dt_sensitivity"]["residual_end_J"]["pairs"]
    r4 = [c["budget"]["residual_end_over_dissipation"] for c in ev["cases"].values()
          if c["settings"]["dt_s"] == 2e-4]
    rows = [
        ["① 에너지 주입 없음", f"max_t R / E_ref = {cks['V8(b)-1']['value']:.2e}", "≤ 1e-3",
         "통과" if cks["V8(b)-1"]["passed"] else "실패"],
        ["② 잔차가 Δt에 1차", "R(2Δt)/R(Δt) = " + " / ".join(f"{p['ratio_2dt_over_dt']:.3f}"
                                                         for p in pairs), "1.6 ~ 2.4",
         "통과" if all(c["passed"] for c in ev["dt_sensitivity"]["checks"]
                     if c["id"] == "V8(b)-2") else "실패"],
        ["③ 장부 폐합(Richardson)", f"R(Δt→0) = {pairs[-1]['richardson_dt0']:+.2f} J "
         f"({abs(pairs[-1]['richardson_dt0']) / ev['dt_sensitivity']['E_ref_J_used_for_check_3'] * 100:.3f} % E_ref)",
         "≤ 1 % E_ref", "통과" if all(c["passed"] for c in ev["dt_sensitivity"]["checks"]
                                     if c["id"] == "V8(b)-3") else "실패"],
        ["④ 수치 소산 / 물리 소산", f"{cks['V8(b)-4']['value'] * 100:.2f} % (2e-4 s 5사례 "
         f"{min(abs(v) for v in r4) * 100:.2f}~{max(abs(v) for v in r4) * 100:.2f} %), R_end ≤ 0",
         "≤ 10 %", "통과" if cks["V8(b)-4"]["passed"] else "실패"],
        ["⑤ D_slip / Σ μN|Δa|", f"{cks['V8(b)-5']['value']:.4f}", "1.00 ~ 1.05",
         "통과" if cks["V8(b)-5"]["passed"] else "실패"],
    ]
    axd = axes_box(fig, 600, 360, 540, 150, W, H)
    axd.set_title(f"(D) V8(b) 5항 판정 — {ENERGY_CASE} (E_ref {case['budget']['E_ref_J']:.1f} J)",
                  fontsize=9.5, loc="left", color=INK_PRIMARY)
    table(axd, rows, ["항목", "측정", "허용", "판정"], widths=[0.27, 0.48, 0.13, 0.10], size=7.4,
          pass_col=3)
    fig.text(600 / W, 1 - 540 / H, "옛 문구 '잔차 ≤ 1 %'는 판정량이 아니라 Δt 2e-4 s 적분기의 수치 소산(2.3 %)을 "
             "잰다\n→ 개정 19에서 ①~⑤로 판정(옛 값 max|R|/E_kin0 2.29 %는 기록).", fontsize=7.6, va="top", color=INK_SECONDARY)
    # (E) dt convergence
    ax = axes_box(fig, 60, 770, 520, 340, W, H)
    style(ax, title="(E) Δt 1차 수렴: |R_end| 와 항별 |값| 대 Δt (log-log, 점선 = 기울기 1)",
          xlabel="Δt [s]", size=9.5)
    sh = ev["dt_sensitivity"]
    dt = np.array(sh["residual_end_J"]["dt_s"])
    names = [("residual_end_J", "R_end (합)"), ("bushing_lag", "부싱 1스텝 지연"),
             ("bushing_implicit", "부싱 암시 -½k_t|Δp|²"), ("kinetic_implicit", "운동 암시 -½ΔvᵀMΔv"),
             ("contact_explicit", "접촉 명시 +½k_nΔδ²")]
    for k, (key, lab) in enumerate(names):
        vals = np.array(sh[key]["values"] if key == "residual_end_J"
                        else sh["shares"][key]["values"])
        colour = INK_PRIMARY if k == 0 else SERIES[k - 1]
        ax.loglog(dt, np.abs(vals), "-o", color=colour, lw=2.0 if k == 0 else 1.2, ms=5,
                  label=lab)
    g = np.array([5e-5, 2e-4])
    ax.loglog(g, 111.58 * g / 2e-4, ":", color=INK_SECONDARY, lw=1.0)
    ax.set_xticks(dt)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_ylabel("|J|", fontsize=7.8, color=INK_SECONDARY)
    ax.legend(fontsize=7, loc="lower right", frameon=True, framealpha=0.9)
    txt = ["Richardson R(0) = 2R(Δt) - R(2Δt):"]
    for p in pairs:
        txt.append(f"  Δt {p['dt_s']:g}/{p['two_dt_s']:g} s: 비 {p['ratio_2dt_over_dt']:.3f}, "
                   f"R(0) {p['richardson_dt0']:+.3f} J")
    ax.text(0.02, 0.97, "\n".join(txt), transform=ax.transAxes, fontsize=7.2, va="top",
            color=INK_PRIMARY, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none",
                                         alpha=0.9))
    # (F) residual decomposition
    ax = axes_box(fig, 640, 620, 500, 490, W, H)
    style(ax, title="(F) 잔차 분해 R_end [J] (경사 2°, 3 Δt)", xlabel="Δt [s]", size=9.5)
    comp = [("bushing_lag", "부싱 1스텝 지연"), ("bushing_implicit", "부싱 암시"),
            ("kinetic_implicit", "운동 암시"), ("contact_explicit", "접촉 명시"),
            ("remainder_end_J", "나머지")]
    xpos = np.arange(len(dt))
    pos_b, neg_b = np.zeros(len(dt)), np.zeros(len(dt))
    for k, (key, lab) in enumerate(comp):
        vals = np.array(sh["shares"][key]["values"] if key != "remainder_end_J"
                        else sh[key]["values"])
        bottom = np.where(vals >= 0, pos_b, neg_b)
        ax.bar(xpos, vals, 0.55, bottom=bottom, color=SERIES[k] if k < 4 else "#b9b8b3",
               edgecolor="white", lw=1.0, label=lab)
        pos_b += np.where(vals >= 0, vals, 0)
        neg_b += np.where(vals < 0, vals, 0)
    rend = np.array(sh["residual_end_J"]["values"])
    ax.plot(xpos, rend, "D", color=INK_PRIMARY, ms=7, label="R_end (합)", zorder=5)
    for x, v in zip(xpos, rend, strict=True):
        ax.text(x + 0.3, v, f"{v:.1f}", fontsize=7.4, va="center", color=INK_PRIMARY)
    ax.axhline(0, color=INK_SECONDARY, lw=0.7)
    ax.set_ylim(neg_b.min() * 1.08, 175)
    ax.set_ylabel("J", fontsize=7.8, color=INK_SECONDARY)
    ax.set_xticks(xpos, [f"{d:g}" for d in dt])
    ax.legend(fontsize=7.2, loc="lower left", frameon=True, framealpha=0.9)
    blk = chk["A_block_lag_budget"]["k_e=2.103e+07"]["one_step_lag"]
    ax.text(0.98, 0.98, "이산 항등식: R = 지연 + 부싱 암시 - ½ΣΔvᵀMΔv + ½Σk_nΔδ²\n"
            "(1자유도 블록 모델 s4_check.json A에서 1e-9 J까지 성립;\n"
            f" 블록 Δt 2e-4 s R/D {blk[1]['R_over_dissipation'] * 100:.1f} %, 1e-4 s "
            f"{blk[2]['R_over_dissipation'] * 100:.1f} %)", transform=ax.transAxes, fontsize=7.0,
            ha="right", va="top", color=INK_SECONDARY)
    # (G) V8(b) all cases (record)
    rows = []
    for k, c in ev["cases"].items():
        rows.append([k.removeprefix("v8b_"), f"{c['settings']['dt_s']:g}",
                     f"{c['budget']['residual_creation_rel']:.1e}",
                     f"{c['budget']['residual_end_over_dissipation'] * 100:+.2f}",
                     f"{c['slip_ratio']:.4f}", str(c["bushing"]["events_window"]),
                     "통과" if c["all_passed"] else "실패"])
    axg = axes_box(fig, 1170, 640, 500, 170, W, H)
    axg.set_title("(G) V8(b) 사례별(①④⑤ + 사건 수)", fontsize=9.5, loc="left", color=INK_PRIMARY)
    table(axg, rows, ["사례", "Δt [s]", "① maxR/E_ref", "④ R/D [%]", "⑤ 비", "부싱 사건",
                      "판정"], widths=[0.30, 0.10, 0.15, 0.13, 0.11, 0.11, 0.10], size=7.0,
          pass_col=6)
    fig.text(1170 / W, 1 - 870 / H, "\n".join([
        "근거 파일: 06_analysis/01_chrono/14_S4/verify_S4_L1_modes.json · verify_S4_L1_beta.csv ·",
        "verify_S4_L1_energy.json · 06_analysis/00_dynamics/s4_check.json · 07_results/S4*/",
        "가정: 킥 0.5 m/s 방향 [0.8, 0.6, 0], 다리 ζ 감도 0.01/0.10, β 0.69~1.6 GPa(감도 범위),",
        "접촉·부싱 강성·μ는 YAML 가정치(ASSUMPTION). 다리 ζ 0.01은 Δt 5e-5 s(Δt 규칙 예외).",
    ]), fontsize=7.6, va="top", color=INK_SECONDARY, linespacing=1.45)
    cadr.save_atomic(OUT["summary"], lambda target: fig.savefig(target, dpi=100,
                                                                facecolor=SURFACE,
                                                                format="png"))
    plt.close(fig)
    summary["summary_png"] = {"path": rel(OUT["summary"]),
                              "size_bytes": OUT["summary"].stat().st_size,
                              "resolution_px": [W, H],
                              "checks_counted": {"A": acc_m, "B": acc_e}}


# =============================================================================================
# main
# =============================================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="*", default=["modes", "energy", "summary"])
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--mesh-cache", type=Path, default=None,
                        help="pickle cache of the coloured meshes (default: a temp dir)")
    parser.add_argument("--cpu", default="pcore", choices=["pcore", "os"])
    args = parser.parse_args()
    t0 = time.perf_counter()
    if args.mesh_cache is None:
        import tempfile

        args.mesh_cache = Path(tempfile.gettempdir()) / "outrigger_render_S4_cache"
    args.mesh_cache.mkdir(parents=True, exist_ok=True)
    summary = {"script": rel(Path(__file__)), "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "cpu": cadr.place_cpu(args.cpu), "jobs": args.jobs, "parts": args.only}
    ctx = None
    if {"modes", "energy"} & set(args.only):
        ctx = Context(args.mesh_cache, args.cpu)
        summary["meshes"] = ctx.mesh_stats
        print(f"context {time.perf_counter() - t0:.1f} s", flush=True)
    if "modes" in args.only:
        render_modes(ctx, args.jobs, summary)
        print(f"modes {time.perf_counter() - t0:.1f} s", flush=True)
    if "energy" in args.only:
        render_energy(ctx, args.jobs, summary)
        print(f"energy {time.perf_counter() - t0:.1f} s", flush=True)
    if "summary" in args.only:
        render_summary(summary)
        print(f"summary {time.perf_counter() - t0:.1f} s", flush=True)
    mi, ei = read_json(MODES_INDEX), read_json(ENERGY_INDEX)
    v = read_json(MODES_VERIFY)
    inputs = [MODES_VERIFY, ENERGY_VERIFY, OUT_DIR / "verify_S4_L1_beta.csv", S4_CHECK,
              REFERENCE_JSON, PARAMS_YAML, MODES_INDEX, ENERGY_INDEX, Path(cadr.__file__)]
    inputs += sorted({ROOT / mi[f"modes_{j['run']}"] / "series.npz" for j in v["v7"]["judged"]})
    for case in (ENERGY_CASE, POSE_CASE):
        d = ROOT / ei[case]["dir"]
        inputs += [d / "record" / "record.npz", d / "record" / "meta.json"]
    inputs.append(ROOT / ei[ENERGY_CASE]["dir"] / "budget.npz")
    summary["inputs"] = [cadr.source(p) for p in inputs]
    summary["wall_s"] = time.perf_counter() - t0
    if OUT["json"].exists() and set(args.only) != {"modes", "energy", "summary"}:
        old = read_json(OUT["json"])
        old.update(summary)
        summary = old
    OUT["json"].write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=float),
                           encoding="utf-8")
    print(f"done {summary['wall_s']:.1f} s", flush=True)


if __name__ == "__main__":
    main()
