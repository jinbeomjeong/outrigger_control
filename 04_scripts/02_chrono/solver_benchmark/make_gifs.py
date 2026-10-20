"""Off-screen GIFs of the three benchmark cases (matplotlib Agg, no Irrlicht window).

Usage: python -I -u make_gifs.py <l1|scm|scale|all>
No benchmark re-run: each case re-simulates its short scene (L1 3 s ~30 s, SCM 3 s ~2.5 min,
scale 1 s ~1 min) and reads the measured costs from 07_results/solver_benchmark/.
Uses the same builders as bench_case.py (same models, SPARSE_QR + lock, dt 1e-4 s) and writes
06_analysis/01_chrono/solver_benchmark_<L1|SCM|scale>.gif. Frames go to
07_results/solver_benchmark/gif_frames/<case>/.
Solver costs printed on the frames come from results/ (this benchmark's measurements).

Displacements are tiny (mm) compared with the 11 m machine, so body poses are drawn with an
exaggeration factor s about their initial pose (position p0 + s (p - p0), rotation angle x s);
s is printed on every frame. Machine geometry is a schematic (boxes from the CAD bbox extents),
not the CAD mesh; leg, pad, crawler-sphere positions are the model's.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # python -I: the script folder is not on sys.path
import bench_case as bc  # noqa: E402
import bench_common as bcm  # noqa: E402  (puts 03_src and 04_scripts/00_cad on sys.path)
import pychrono as ch  # noqa: E402

RES = bcm.RESULTS_DIR
FRAMES_DIR = RES / "gif_frames"
SOLVER_LABEL = {"QR": "SPARSE_QR", "LU": "SPARSE_LU", "PARDISO": "PARDISO_MKL"}


def cost_text(phase: str, prefix: str) -> str:
    """Median wall us/step per solver (best measured variant) for one case."""
    lines = []
    for short in ("QR", "LU", "PARDISO"):
        best = None
        for f in (RES / phase).glob(f"{prefix}{short}_*.json"):
            if f.name.endswith(".cfg.json"):
                continue
            r = json.loads(f.read_text())
            v = r["wall_us_per_step_median"]
            ls = (
                r["chrono_timers_us_per_step"]["LSsetup"]
                + r["chrono_timers_us_per_step"]["LSsolve"]
            )
            if best is None or v < best[0]:
                best = (v, ls, f.stem.replace(prefix, ""))
        if best:
            lines.append(
                f"{SOLVER_LABEL[short]:<12s} {best[0]:9.1f} us/step  (LS {best[1]:7.1f})  "
                f"[{best[2]}]"
            )
    return "\n".join(lines)


# --- geometry helpers --------------------------------------------------------------------


def quat_to_R(q) -> np.ndarray:
    w, x, y, z = q
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ]
    )


def body_pose(body) -> tuple[np.ndarray, np.ndarray]:
    p = body.GetPos()
    q = body.GetRot()
    return np.array([p.x, p.y, p.z]), np.array([q.e0, q.e1, q.e2, q.e3])


def exaggerate(p0, q0, p, q, s):
    """Pose with displacement and rotation scaled by s (rotation about the body origin)."""
    R0, R = quat_to_R(q0), quat_to_R(q)
    dR = R @ R0.T
    ang = math.acos(max(-1.0, min(1.0, (np.trace(dR) - 1) / 2)))
    if ang < 1e-15:
        Rs = np.eye(3)
    else:
        ax = np.array([dR[2, 1] - dR[1, 2], dR[0, 2] - dR[2, 0], dR[1, 0] - dR[0, 1]]) / (
            2 * math.sin(ang)
        )
        a = ang * s
        K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
        Rs = np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K
    return p0 + s * (p - p0), Rs @ R0


def box_faces(lo, hi):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    v = np.array(
        [
            [x0, y0, z0],
            [x1, y0, z0],
            [x1, y1, z0],
            [x0, y1, z0],
            [x0, y0, z1],
            [x1, y0, z1],
            [x1, y1, z1],
            [x0, y1, z1],
        ]
    )
    idx = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 3, 7, 4]]
    return [v[i] for i in idx]


def transform(faces, p_ref0, p_disp, R):
    """Move faces (world coords at the initial pose) rigidly: x -> p_disp + R (x - p_ref0)."""
    return [(R @ (f - p_ref0).T).T + p_disp for f in faces]


def save_gif(frames: list[Path], out: Path, ms: int) -> None:
    imgs = [Image.open(f).convert("RGB") for f in frames]
    pal = imgs[len(imgs) // 2].quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in imgs]
    q[0].save(out, save_all=True, append_images=q[1:], duration=ms, loop=0, optimize=False)


# --- case 1: full-scale L1 ---------------------------------------------------------------


def machine_geometry(P, lift):
    """Schematic boxes in world coordinates at the initial (levelled) pose."""
    zf = P.ground.crawler_bottom_z_m
    boxes = {
        "track_L": ((-2.1, 0.766, zf + lift), (2.1, 1.366, zf + lift + 0.70), "#555555"),
        "track_R": ((-2.1, -1.366, zf + lift), (2.1, -0.766, zf + lift + 0.70), "#555555"),
        "frame": ((-2.4, -1.25, zf + lift + 0.70), (2.6, 1.25, zf + lift + 1.35), "#d9a441"),
        "cab": ((-0.6, 0.25, zf + lift + 1.35), (0.9, 1.25, zf + lift + 3.2), "#8fb3d9"),
        "engine": ((-2.4, -1.25, zf + lift + 1.35), (-0.9, 0.2, zf + lift + 2.6), "#c98b3a"),
        "mast": ((3.2, -0.25, zf + lift + 0.4), (3.7, 0.25, 10.44 + lift), "#b04a3a"),
        "drive": ((2.9, -0.5, 8.6 + lift), (4.0, 0.5, 9.8 + lift), "#7a3a8a"),
    }
    return boxes


def run_l1(t_end=3.0, frame_dt=0.04, s=50.0):
    cfg = {"model": "l1", "solver": "SPARSE_QR", "lock": True, "dt": 1e-4}
    b, state, hook, extra, _, _ = bc.build_machine(cfg, scm=False)
    sysm = b.system
    P = bc.P
    lift = P.simulation.crawler_clearance_m
    bodies = {bd.GetName(): bd for bd in sysm.GetBodies()}
    sup = bodies["superstructure"]
    legs = [bodies[f"leg_{n}"] for n in ("FL", "FR", "RL", "RR")]
    sup0 = body_pose(sup)
    legs0 = [body_pose(bd) for bd in legs]
    boxes = machine_geometry(P, lift)
    # crawler spheres in world coords at init
    yc = float(P.get("contact.crawler.sphere_layout.track_centre_y_m"))
    x0, x1 = (float(v) for v in P.get("contact.crawler.sphere_layout.x_range_m"))
    rs = float(P.get("contact.crawler.sphere_layout.sphere_radius_m"))
    zf = P.ground.crawler_bottom_z_m
    spheres0 = np.array([[x, y, zf + lift + rs] for y in (yc, -yc) for x in np.linspace(x0, x1, 9)])
    l1 = P.contact.rigid_floor.L1
    pads0, rods0 = [], []
    for i, leg in enumerate(P.legs):
        e = l1.operating_extension_m[i]
        pb = np.array(leg.pad_bottom_center_retracted_m) + [0, 0, lift - e]
        poly = np.array([[pb[0] + u, pb[1] + v, pb[2]] for u, v in leg.pad.polygon_xy_m])
        top = poly + [0, 0, leg.pad.thickness_m]
        pads0.append((poly, top))
        att = np.array(leg.attachment_point_m) + [0, 0, lift]
        rods0.append((att, pb + [0, 0, leg.pad.thickness_m]))
    texts = cost_text("l1", "dt1e-04_")
    frames_dir = FRAMES_DIR / "l1"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for f in frames_dir.glob("*.png"):
        f.unlink()
    hist_t, hist_z, hist_f, hist_p = [], [], [], []
    n_per = round(frame_dt / cfg["dt"])
    n_frames = round(t_end / frame_dt) + 1
    frames = []

    def record():
        p_, q_ = body_pose(sup)
        hist_t.append(sysm.GetChTime())
        hist_z.append((p_[2] - sup0[0][2]) * 1e3)
        # pitch (about y) and roll (about x) from the rotation matrix, small angles, degrees
        R_ = quat_to_R(q_)
        hist_p.append(
            [
                math.degrees(math.atan2(-R_[2, 0], R_[2, 2])),
                math.degrees(math.atan2(R_[2, 1], R_[2, 2])),
            ]
        )
        hist_f.append([bd.GetContactForce().z / 1e3 for bd in legs])

    record()
    for k in range(n_frames):
        if k > 0:
            for j in range(n_per):
                sysm.DoStepDynamics(cfg["dt"])
                hook()
                if (j + 1) % 10 == 0:
                    record()
        t = sysm.GetChTime()
        p, q = body_pose(sup)
        ps, Rs = exaggerate(sup0[0], sup0[1], p, q, s)
        R_rel = Rs @ quat_to_R(sup0[1]).T
        fig = plt.figure(figsize=(17, 9), dpi=110)
        ax = fig.add_axes([0.0, 0.03, 0.33, 0.86], projection="3d")
        av = fig.add_axes([0.35, 0.36, 0.34, 0.54])
        faces, colors = [], []
        for lo, hi, c in boxes.values():
            fs = transform(box_faces(np.array(lo), np.array(hi)), sup0[0], ps, R_rel)
            faces += fs
            colors += [c] * len(fs)
            for f_ in fs:
                av.fill(f_[:, 0], f_[:, 2], color=c, alpha=0.18, lw=0)
        ax.add_collection3d(
            Poly3DCollection(faces, facecolors=colors, edgecolors="k", linewidths=0.3, alpha=0.30)
        )
        sph = (R_rel @ (spheres0 - sup0[0]).T).T + ps
        ax.scatter(
            sph[:, 0],
            sph[:, 1],
            sph[:, 2],
            s=22,
            c="#1f77b4",
            depthshade=False,
            label="crawler spheres (2x9)",
        )
        for c_ in sph[sph[:, 1] > 0]:
            av.add_patch(plt.Circle((c_[0], c_[2]), rs, fc="#1f77b4", ec="k", lw=0.5, zorder=4))
        segs = []
        for i, bd in enumerate(legs):
            pl, ql = body_pose(bd)
            pl_s, Rl = exaggerate(legs0[i][0], legs0[i][1], pl, ql, s)
            Rl_rel = Rl @ quat_to_R(legs0[i][1]).T
            poly, top = pads0[i]
            pb_s = (Rl_rel @ (poly - legs0[i][0]).T).T + pl_s
            pt_s = (Rl_rel @ (top - legs0[i][0]).T).T + pl_s
            pad_faces = [pb_s, pt_s] + [
                np.array([pb_s[j], pb_s[(j + 1) % 8], pt_s[(j + 1) % 8], pt_s[j]]) for j in range(8)
            ]
            fz = bd.GetContactForce().z
            col = plt.cm.viridis(min(1.0, max(0.0, fz / 2.0e5)))
            ax.add_collection3d(
                Poly3DCollection(pad_faces, facecolors=[col], edgecolors="k", linewidths=0.4)
            )
            att, rod_bot = rods0[i]
            att_s = (R_rel @ (att - sup0[0])) + ps
            rb_s = (Rl_rel @ (rod_bot - legs0[i][0])) + pl_s
            segs.append([att_s, rb_s])
            if P.legs[i].name in ("FL", "RL"):  # side view from the left (+y side)
                av.plot([att_s[0], rb_s[0]], [att_s[2], rb_s[2]], color="#222222", lw=5, zorder=5)
                av.fill(
                    np.r_[pb_s[:, 0].min(), pb_s[:, 0].max(), pt_s[:, 0].max(), pt_s[:, 0].min()],
                    np.r_[pb_s[:, 2].min(), pb_s[:, 2].min(), pt_s[:, 2].max(), pt_s[:, 2].max()],
                    color=col,
                    ec="k",
                    lw=0.8,
                    zorder=6,
                )
                av.annotate(
                    f"{P.legs[i].name}\n{fz / 1e3:5.1f} kN",
                    (rb_s[0], pb_s[:, 2].min() - 0.08),
                    ha="center",
                    va="top",
                    fontsize=9,
                    zorder=7,
                )
        ax.add_collection3d(Line3DCollection(segs, colors="#222222", linewidths=4))
        gx, gy = np.meshgrid(np.linspace(-4, 5, 10), np.linspace(-3, 3, 7))
        ax.plot_wireframe(gx, gy, np.full_like(gx, zf), color="#999999", linewidth=0.5)
        ax.set_xlim(-4, 5)
        ax.set_ylim(-4.5, 4.5)
        ax.set_zlim(-1.5, 11)
        ax.set_box_aspect((9, 9, 12.5))
        ax.view_init(elev=18, azim=-58)
        ax.set_xlabel("x [m] (forward)")
        ax.set_ylabel("y [m] (left)")
        ax.set_zlabel("z [m]")
        ax.legend(loc="upper left", fontsize=8)
        ax.set_title("3D overview", fontsize=10)
        av.axhspan(zf - 1.0, zf, color="#c8c8c8", zorder=1)
        av.axhline(zf, color="k", lw=1, zorder=2)
        av.set_xlim(-3.0, 4.3)
        av.set_ylim(zf - 0.55, 1.4)
        av.set_aspect("equal")
        av.set_xlabel("x [m] (forward)")
        av.set_ylabel("z [m]")
        av.grid(alpha=0.3)
        av.set_title(
            f"side view from the left (FL, RL legs; lower part), motion x{s:g}", fontsize=10
        )
        fig.text(
            0.35,
            0.335,
            f"grey = rigid floor. With x{s:g} the pad-spring compression (actual about 5 mm) "
            "shows as pads entering the floor.",
            fontsize=9,
        )
        fig.text(
            0.01,
            0.965,
            "Case 1: full-scale L1 (top auger) - superstructure + 4 legs on locked position "
            "motors, "
            "SMC pad spheres, 2x9 crawler spheres (50 mm above floor), ground bushings + Coulomb "
            "hook",
            fontsize=11.5,
            weight="bold",
        )
        fig.text(
            0.01,
            0.935,
            f"t = {t:6.3f} s    dt 1e-4 s, SPARSE_QR (+lock), same model and start as the "
            "benchmark "
            "(pads touching, unloaded -> drops onto the pad springs).  Displacement and rotation "
            f"drawn x{s:g}; "
            "machine = schematic boxes.",
            fontsize=10,
        )
        fig.text(
            0.35,
            0.28,
            "Measured cost, this model (dt 1e-4 s, median of 3 windows;\n"
            "wall = incl. Python bushing hook; LS = Chrono LSsetup + LSsolve timers):\n" + texts,
            fontsize=9.5,
            family="monospace",
            va="top",
        )
        a1 = fig.add_axes([0.73, 0.70, 0.25, 0.20])
        a1.plot(hist_t, hist_z, color="#1f77b4", lw=1)
        a1.set_xlim(0, t_end)
        a1.set_ylabel("superstructure dz [mm]")
        a1.grid(alpha=0.3)
        a3 = fig.add_axes([0.73, 0.40, 0.25, 0.22])
        hp = np.array(hist_p)
        a3.plot(hist_t, hp[:, 0], label="pitch", lw=1)
        a3.plot(hist_t, hp[:, 1], label="roll", lw=1)
        a3.set_xlim(0, t_end)
        a3.set_ylabel("angle [deg] (true scale)")
        a3.legend(fontsize=8)
        a3.grid(alpha=0.3)
        a2 = fig.add_axes([0.73, 0.07, 0.25, 0.26])
        hf = np.array(hist_f)
        for j, n in enumerate(("FL", "FR", "RL", "RR")):
            a2.plot(hist_t, hf[:, j], label=n, lw=1)
        a2.set_xlim(0, t_end)
        a2.set_xlabel("t [s]")
        a2.set_ylabel("pad contact force z [kN]")
        a2.legend(fontsize=8, ncol=4)
        a2.grid(alpha=0.3)
        fpath = frames_dir / f"f{k:04d}.png"
        fig.savefig(fpath)
        plt.close(fig)
        frames.append(fpath)
    out = bcm.GIF_PATHS["l1"]
    save_gif(frames, out, int(frame_dt * 1000 * 2))
    return out, len(frames), {"final_sum_fz_over_weight": state()["sum_fz_over_weight"]}


# --- case 2: SCM -------------------------------------------------------------------------


def run_scm(t_end=3.0, frame_dt=0.05, delta=0.02, s=5.0):
    cfg = {
        "model": "scm",
        "solver": "SPARSE_QR",
        "lock": True,
        "dt": 1e-4,
        "scm_params": bcm.SCM_PARAMS,
        "scm_size": [8.0, 6.0],
        "scm_delta": delta,
        "scm_domains": True,
    }
    b, state, hook, extra, scm_timers, terrain = bc.build_machine(cfg, scm=True)
    sysm = b.system
    P = bc.P
    lift = P.simulation.crawler_clearance_m
    zf = P.ground.crawler_bottom_z_m
    bodies = {bd.GetName(): bd for bd in sysm.GetBodies()}
    sup = bodies["superstructure"]
    sup0 = body_pose(sup)
    boxes = machine_geometry(P, lift)
    pads_xy = [np.array(leg.pad_bottom_center_retracted_m[:2]) for leg in P.legs]
    half, nq = 0.36, 73  # query window per pad (0.72 m, 1 cm sampling for display)
    us = np.linspace(-half, half, nq)
    texts = cost_text("scm", f"d{delta:g}_")
    frames_dir = FRAMES_DIR / "scm"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for f in frames_dir.glob("*.png"):
        f.unlink()

    def height_map(c):
        h = np.empty((nq, nq))
        for a, yy in enumerate(us):
            for bb, xx in enumerate(us):
                h[a, bb] = terrain.GetHeight(ch.ChVector3d(c[0] + xx, c[1] + yy, 0.0))
        return h

    h_init = height_map(pads_xy[0])
    yc = float(P.get("contact.crawler.sphere_layout.track_centre_y_m"))
    cx = np.arange(-2.2, 2.0001, 0.02)  # x < 2.0 m keeps the FL pad pit out of the strip
    cy = np.arange(yc - 0.30, yc + 0.3001, 0.02)
    xs0, xs1 = (float(v) for v in P.get("contact.crawler.sphere_layout.x_range_m"))
    rs = float(P.get("contact.crawler.sphere_layout.sphere_radius_m"))
    spheres0 = np.array(
        [[x, y, zf + lift + rs] for y in (yc, -yc) for x in np.linspace(xs0, xs1, 9)]
    )

    def strip_map():
        h = np.empty((len(cy), len(cx)))
        for a_, yy in enumerate(cy):
            for b_, xx in enumerate(cx):
                h[a_, b_] = terrain.GetHeight(ch.ChVector3d(xx, yy, 0.0))
        return (zf - h) * 1e3

    hist_t, hist_sink, hist_cr = [], [], []
    n_per = round(frame_dt / cfg["dt"])
    n_frames = round(t_end / frame_dt) + 1
    frames = []
    vmax = 90.0
    pad_r = [math.sqrt(leg.pad.bottom_area_m2 / math.pi) for leg in P.legs]
    cmap = plt.cm.magma_r
    names = ("FL", "FR", "RL", "RR")
    for k in range(n_frames):
        if k > 0:
            for _ in range(n_per):
                sysm.DoStepDynamics(cfg["dt"])
        t = sysm.GetChTime()
        st = state()
        hist_t.append(t)
        hist_sink.append([v * 1e3 for v in st["pad_sinkage_m"]])
        hist_cr.append(st["crawler_fz_N"] / 1e3)
        maps = [(zf - height_map(c)) * 1e3 for c in pads_xy]  # sinkage [mm], + down
        smap = strip_map()
        fig = plt.figure(figsize=(17, 9.6), dpi=110)
        fig.text(
            0.01,
            0.968,
            "Case 2: SCM soft ground (Bekker-Wong SCMTerrain) - same machine, pads = cylinders of "
            "the pad "
            f"area, crawler 50 mm up at start; grid delta {delta * 100:g} cm (middle of 5 / 2 / 1 "
            "cm)",
            fontsize=11.5,
            weight="bold",
        )
        fig.text(
            0.01,
            0.940,
            f"t = {t:6.3f} s    dt 1e-4 s, SPARSE_QR (+lock). Soil = TEST ASSUMPTION (heavy clay, "
            "Wong table: "
            "n 0.13, kc 12.7 kN/m^1.13, kphi 1556 kN/m^2.13, c 69 kPa, phi 34 deg; Chrono K 2e8 "
            "Pa/m, R 3e4 Pa s/m)",
            fontsize=10,
        )
        ax = fig.add_axes([0.0, 0.04, 0.30, 0.85], projection="3d")
        p, q = body_pose(sup)
        ps, Rs = exaggerate(sup0[0], sup0[1], p, q, s)
        R_rel = Rs @ quat_to_R(sup0[1]).T
        faces, colors = [], []
        for lo, hi, c in boxes.values():
            fs = transform(box_faces(np.array(lo), np.array(hi)), sup0[0], ps, R_rel)
            faces += fs
            colors += [c] * len(fs)
        ax.add_collection3d(
            Poly3DCollection(faces, facecolors=colors, edgecolors="k", linewidths=0.3, alpha=0.35)
        )
        sph = (R_rel @ (spheres0 - sup0[0]).T).T + ps
        ax.scatter(sph[:, 0], sph[:, 1], sph[:, 2], s=14, c="#1f77b4", depthshade=False)
        for i, c in enumerate(pads_xy):
            X, Y = np.meshgrid(c[0] + us, c[1] + us)
            Z = zf - s * maps[i] * 1e-3
            ax.plot_surface(
                X,
                Y,
                Z,
                facecolors=cmap(np.clip(maps[i] / vmax, 0, 1)),
                shade=False,
                rstride=2,
                cstride=2,
                linewidth=0,
            )
        X, Y = np.meshgrid(cx, cy)
        ax.plot_surface(
            X,
            Y,
            zf - s * smap * 1e-3,
            facecolors=cmap(np.clip(smap / vmax, 0, 1)),
            shade=False,
            rstride=2,
            cstride=2,
            linewidth=0,
        )
        gx, gy = np.meshgrid(np.linspace(-4, 5, 10), np.linspace(-3, 3, 7))
        ax.plot_wireframe(gx, gy, np.full_like(gx, zf), color="#aaaaaa", linewidth=0.4)
        ax.set_xlim(-4, 5)
        ax.set_ylim(-4.5, 4.5)
        ax.set_zlim(-2.0, 11)
        ax.set_box_aspect((9, 9, 13))
        ax.view_init(elev=18, azim=-58)
        ax.set_xlabel("x [m] (forward)")
        ax.set_ylabel("y [m] (left)")
        ax.set_zlabel("z [m]")
        ax.set_title(f"overview: body motion and soil pits drawn x{s:g}", fontsize=10)
        # pad maps laid out as a top view (x right = forward, y up = left)
        pos = {"RL": (0.33, 0.52), "FL": (0.50, 0.52), "RR": (0.33, 0.10), "FR": (0.50, 0.10)}
        im = None
        for i, n in enumerate(names):
            x_, y_ = pos[n]
            a = fig.add_axes([x_, y_, 0.15, 0.33])
            im = a.imshow(
                maps[i],
                origin="lower",
                extent=[-half, half, -half, half],
                cmap=cmap,
                vmin=0,
                vmax=vmax,
            )
            th = np.linspace(0, 2 * np.pi, 100)
            a.plot(pad_r[i] * np.cos(th), pad_r[i] * np.sin(th), "--", color="#2ca02c", lw=0.9)
            a.set_title(f"{n} pad: max sinkage {maps[i].max():5.1f} mm", fontsize=9.5)
            a.set_xlabel("x - x_pad [m]", fontsize=8)
            a.set_ylabel("y - y_pad [m]", fontsize=8)
            a.tick_params(labelsize=7)
        fig.text(
            0.33,
            0.905,
            "soil surface under the pads (top view; green dashed = pad outline, equal-area circle)",
            fontsize=9.5,
        )
        cax = fig.add_axes([0.665, 0.10, 0.009, 0.75])
        fig.colorbar(im, cax=cax).set_label("sinkage below the initial surface [mm]", fontsize=9)
        a3 = fig.add_axes([0.745, 0.73, 0.245, 0.13])
        a3.imshow(
            smap,
            origin="lower",
            extent=[cx[0], cx[-1], cy[0], cy[-1]],
            cmap=cmap,
            vmin=0,
            vmax=vmax,
            aspect="auto",
        )
        a3.set_title(
            f"left track strip: max {smap.max():4.1f} mm, crawler Fz "
            f"{st['crawler_fz_N'] / 1e3:5.1f} kN",
            fontsize=9,
        )
        a3.set_xlabel("x [m]", fontsize=8)
        a3.set_ylabel("y [m]", fontsize=8)
        a3.tick_params(labelsize=7)
        a2 = fig.add_axes([0.745, 0.40, 0.245, 0.24])
        hs = np.array(hist_sink)
        for j, n in enumerate(names):
            a2.plot(hist_t, hs[:, j], label=n)
        a2.set_xlim(0, t_end)
        a2.set_ylim(0, vmax)
        a2.set_xlabel("t [s]", fontsize=8)
        a2.set_ylabel("pad sinkage [mm]", fontsize=9)
        a2.legend(fontsize=8, ncol=4, loc="upper left")
        a2.grid(alpha=0.3)
        a2.tick_params(labelsize=8)
        fig.text(
            0.715,
            0.31,
            f"Measured cost, delta {delta * 100:g} cm (dt 1e-4 s, median of 3):\n"
            + texts.replace("  [", "\n     ["),
            fontsize=8.6,
            family="monospace",
            va="top",
        )
        fig.text(
            0.715,
            0.10,
            f"sum of vertical soil forces / weight = {st['sum_fz_over_weight']:.3f}\n"
            "front pads (about 118 kN each) sink most;\nbeyond 50 mm the crawler front spheres "
            "touch the soil.",
            fontsize=9,
            va="top",
        )
        fpath = frames_dir / f"f{k:04d}.png"
        fig.savefig(fpath)
        plt.close(fig)
        frames.append(fpath)
    out = bcm.GIF_PATHS["scm"]
    save_gif(frames, out, int(frame_dt * 1000 * 2))
    return (
        out,
        len(frames),
        {
            "final": {k: st[k] for k in ("pad_sinkage_m", "sum_fz_over_weight", "crawler_fz_N")},
            "h_init_range_m": [float(h_init.min()), float(h_init.max())],
        },
    )


# --- case 3: scaling grid ----------------------------------------------------------------


def run_scale(N=100, t_end=1.0, frame_dt=0.02, s=300.0):
    cfg = {"model": "grid", "N": N, "solver": "SPARSE_LU", "lock": True, "dt": 1e-4}
    b, state, _, extra, _, _ = bc.build_grid(cfg)
    sysm = b.system
    bodies = [bd for bd in sysm.GetBodies() if not bd.IsFixed()]
    p0 = [body_pose(bd) for bd in bodies]
    nx = extra["nx"]
    pairs = []
    for k in range(N):
        ix = k % nx
        for j in (k + 1 if ix + 1 < nx else None, k + nx):
            if j is not None and j < N:
                pairs.append((k, j))
    texts = cost_text("scale", f"grid_N{N}_")
    frames_dir = FRAMES_DIR / "scale"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for f in frames_dir.glob("*.png"):
        f.unlink()
    a = 0.25
    cube = box_faces(np.array([-a, -a, -a]), np.array([a, a, a]))
    n_per = round(frame_dt / cfg["dt"])
    n_frames = round(t_end / frame_dt) + 1
    frames = []
    rc = json.loads((RES / "scale" / f"grid_N{N}_LU_lock1_thrdef.json").read_text())["counts"]
    counts = (rc["coords_vel"], rc["constraints"])
    for k in range(n_frames):
        if k > 0:
            for _ in range(n_per):
                sysm.DoStepDynamics(cfg["dt"])
        t = sysm.GetChTime()
        fig = plt.figure(figsize=(13, 8), dpi=110)
        ax = fig.add_axes([0.0, 0.0, 0.68, 0.92], projection="3d")
        faces, cols, centres = [], [], []
        for i, bd in enumerate(bodies):
            p, q = body_pose(bd)
            ps, Rs = exaggerate(p0[i][0], p0[i][1], p, q, s)
            centres.append(ps)
            dz = (p[2] - p0[i][0][2]) * 1e3
            c = plt.cm.coolwarm(0.5 + dz / 2.4)
            for f in cube:
                faces.append((Rs @ f.T).T + ps)
                cols.append(c)
        ax.add_collection3d(
            Poly3DCollection(faces, facecolors=cols, edgecolors="k", linewidths=0.2)
        )
        segs = [[centres[i], centres[j]] for i, j in pairs]
        ax.add_collection3d(Line3DCollection(segs, colors="#2ca02c", linewidths=1.2))
        ax.set_xlim(-0.5, nx - 0.5)
        ax.set_ylim(-0.5, nx - 0.5)
        ax.set_zlim(0.4, 1.6)
        ax.set_box_aspect((nx, nx, 1.2))
        ax.view_init(elev=28, azim=-60)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_zlabel("z [m]")
        fig.text(
            0.01,
            0.965,
            f"Case 3: synthetic scaling grid, N = {N} bodies (KKT unknowns "
            f"{counts[0]} vel + {counts[1]} constraints = {counts[0] + counts[1]})",
            fontsize=11,
            weight="bold",
        )
        fig.text(
            0.01,
            0.905,
            f"t = {t:6.3f} s   dt 1e-4 s, SPARSE_LU (+lock; QR at this size is 48 ms/step). Each "
            "body: "
            "ChLinkMotorLinearPosition to the floor (spherical guide),\n"
            "z = 1 mm sine 2 Hz with phase 0.37 k rad; green lines = neighbour bushings (k 1e6 "
            "N/m, c 1e3 N s/m). "
            f"Motion and rotation drawn x{s:g}.",
            fontsize=9.5,
        )
        fig.text(
            0.66,
            0.80,
            f"Measured cost (grid N = {N}, dt 1e-4 s):\n" + texts.replace("  [", "\n   ["),
            fontsize=8.5,
            family="monospace",
            va="top",
        )
        fig.text(0.66, 0.40, "colour = body dz (blue -1.2 mm ... red +1.2 mm)", fontsize=9)
        fpath = frames_dir / f"f{k:04d}.png"
        fig.savefig(fpath)
        plt.close(fig)
        frames.append(fpath)
    out = bcm.GIF_PATHS["scale"]
    save_gif(frames, out, int(frame_dt * 1000 * 4))
    return out, len(frames), {"kkt": counts}


def main() -> None:
    case = sys.argv[1] if len(sys.argv) > 1 else "all"
    runners = {"l1": run_l1, "scm": run_scm, "scale": run_scale}
    for name in runners if case == "all" else [case]:
        t0 = time.perf_counter()
        out, n, info = runners[name]()
        w, h = Image.open(out).size
        rec = {
            "case": name,
            "gif": str(out),
            "bytes": out.stat().st_size,
            "frames": n,
            "size_px": [w, h],
            "wall_s": time.perf_counter() - t0,
            "info": info,
        }
        (RES / f"gif_{name}.json").write_text(json.dumps(rec, indent=1, default=float))
        print(json.dumps(rec, default=float), flush=True)


if __name__ == "__main__":
    main()
