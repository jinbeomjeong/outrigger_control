"""Case GIF / MP4 of one or more finished closed-loop runs (record replay; no Chrono run).

User decisions 2026-10-30 (prototype review): start to first READY (+ tail) at ONE constant playback speed shown on
screen; 3D at true scale with an attitude inset (magnified roll / pitch level gauges + 4 stroke bars); SCM ground
schematic (pad pits coloured by sinkage) unless the case folder holds ``scm_nodes.npz`` (``run_S9.py level
--record-scm-nodes``), then the recorded SCM node surface is drawn.

One frame (1280 x 720):
  left   painter render of the C8 visual meshes (C11 colours) posed from the 10 Hz record (body pose, s_motor,
         auger level); rear pads scaled to the case's pad type (B: 250 / 330 in plan, about the pad centre); floor =
         rigid plane (+ per-pad floor tiles: G8 blocks, floor events) or the SCM plane (+ pits / node surface);
         attitude inset; HUD (time, phase, playback speed)
  right  phase strip with controller events, controller inputs (pressures, roll / pitch, strokes), output (u),
         plant truth (pad force, crawler force, pad sinkage or cylinder force, crawler gap), moving time cursor

Data per format (all absolute simulation time after the alignment below):
  S9 SCM (07_results/S9/batch_*/<case>): record/record.npz, step_series.npz (1 ms), r8_series.npz (phase,
      issued_u) or record u_cmd, completion_series.npz (controller clearance), result.json (events, phases, s9_rows
      rut_clearance_m / crawler_gap_min_m = in-run truth gap, settle_slope plane)
  S8 L2b / S6 L1-R rigid (07_results/S8|S6/<batch>/<case>): record/record.npz, pads.npz (1 ms), r8_series.npz or
      s8_series.npz (phase per 10 Hz sample, absolute t), controller_events.json (absolute), result.json
      floor_plane / g8; result.json ``phases`` are loop-relative and are only used shifted by
      (record t0 - first phase t) when no per-sample phase exists; crawler gap = crawler_gap.npz (truth) or the
      APPROXIMATION min over crawler-mesh bottom points of n . x - offset (rigid floor plane)

Outputs: 06_analysis/01_chrono/18_S8/gifs (rigid) or 19_S9/gifs (SCM): <batch>__<case>.gif (preview, every
--gif-every-th frame, --gif-scale) and .mp4 (all frames, libx264 yuv420p), meta <stage>_case_gifs.json (merged per
case). Frames are streamed to disk (<out>/_frames/<case>/) and deleted after encoding (--keep-frames keeps them).

Usage (PowerShell, Chrono-dev):
  python -I 04_scripts/02_chrono/render_case_gifs.py <case dir> [<case dir> ...] [--list cases.txt]
         [--fps-sim 2] [--speed 10] [--gif-every 2] [--gif-scale 0.75] [--tail-s 5] [--jobs 4]
         [--max-frames N] [--out-dir DIR] [--mesh-cache DIR] [--scm-nodes FILE] [--keep-frames] [--dry]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pickle
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "04_scripts" / "00_cad"))
sys.path.insert(0, str(ROOT / "03_src"))

import render_cad_tracks_summary as cadr  # noqa: E402
import render_layout_views as rlv  # noqa: E402

plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

LEGS = ("FL", "FR", "RL", "RR")
LEG_COLORS = {"FL": "#2a78d6", "FR": "#eb6834", "RL": "#1baf7a", "RR": "#eda100"}
PHASE_COLORS = {"check": "#b9b8b3", "touch": "#8fb8e8", "level": "#f2c26b", "loc": "#e87ba4", "probe": "#9bd3ae",
                "done": "#7fc97f", "ready": "#008300", "fault": "#e34948", "reanchor": "#c9a0dc", "hold": "#d0d0d0"}
VIEW = "case"
VIEW_TOWARD = (1.0, -1.0, 0.6)
W, H = 1280, 720
W3D, H3D = 540, 540
Y3D = 40
CELL_M = 0.04
ZCROP_M = 1.2
"""The 3D view is framed on the machine points below this body z [m] (undercarriage, pads, deck); the mast leaves
the frame."""
STROKE_MAX_M = 0.70
STROKE_MARK_M = 0.6848
"""Stroke bar marker: end-margin reference (CLAUDE.md 행정)."""
TARGET_BAND_DEG = 0.2
GAP_LIMIT_MM = 25.0
V_MAX_MM_S = 20.924
SOIL_COLOR = "#b8a27f"
TILE_COLOR = "#9c8e7a"
PIT_COLOR = "#5a3e22"
PAD_VARIANTS_JSON = ROOT / "02_params" / "pad_variants.json"
OUT_ROOT = ROOT / "06_analysis" / "01_chrono"
STAGE_DIRS = {"S9": OUT_ROOT / "19_S9" / "gifs", "S8": OUT_ROOT / "18_S8" / "gifs"}
FFMPEG = Path(sys.executable).parent / "Library" / "bin" / "ffmpeg.exe"


# =============================================================================================
# case data (one normalised structure for S9 / S8 / S6 folders)
# =============================================================================================


@dataclass
class Case:
    path: Path
    kind: str  # "S9" (SCM) or "S8" (rigid L2b / L1-R)
    label: str
    level: str
    pad_variant: str
    t_rec: np.ndarray
    pos: np.ndarray
    quat: np.ndarray
    s_motor: np.ndarray
    stroke_true: np.ndarray
    head_bar: np.ndarray
    rod_bar: np.ndarray
    stroke_meas_mm: np.ndarray
    imu_tilt_deg: np.ndarray
    t_u: np.ndarray
    u_mm_s: np.ndarray
    t_phase: np.ndarray
    phase: np.ndarray
    events: list[tuple[float, str]]
    t_fast: np.ndarray
    pad_N: np.ndarray
    roll_pitch_deg: np.ndarray
    crawler_N: np.ndarray  # total normal [N] on t_crawler
    t_crawler: np.ndarray
    track_N: np.ndarray | None  # (n, 2) on t_fast (S9)
    state3: np.ndarray  # pad sinkage [m] (S9) or cylinder force [N] (rigid), on t_fast
    state3_kind: str
    t_gap: np.ndarray
    gap_m: np.ndarray
    gap_label: str
    gap_is_approx: bool
    t_ctrl_gap: np.ndarray | None
    ctrl_gap_m: np.ndarray | None
    plane_normal: np.ndarray
    plane_point: np.ndarray
    pad_floor_delta: np.ndarray | None  # (n_fast, 4) local floor height under each pad vs the plane [m] (rigid)
    t_ready: float | None
    notes: list[str] = field(default_factory=list)
    scm_nodes: Path | None = None
    mass_scale: float = 1.0
    t_event: float | None = None
    """Floor / soil event time (S8 result event_t_s, S9 soil_event driver t_ev_s): the window then runs to the first
    READY after the event."""


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def _imu_tilt_deg(f: np.ndarray) -> np.ndarray:
    """Static tilt from the body-frame specific force: roll = atan2(f_y, f_z), pitch = atan2(-f_x, f_z) (pitch > 0
    nose down; checked against the truth on the D424R J1 case: median |diff| 0.003 deg)."""
    return np.degrees(np.stack([np.arctan2(f[:, 1], f[:, 2]), np.arctan2(-f[:, 0], f[:, 2])], axis=1))


def _roll_pitch_from_quats(q: np.ndarray) -> np.ndarray:
    from outrigger_sim.frames import roll_pitch_from_quat

    return np.degrees(np.array([roll_pitch_from_quat(np.asarray(v, float)) for v in q]))


def _first_key(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _first_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _first_key(v, key)
            if r is not None:
                return r
    return None


def _first_ready(t: np.ndarray, phase: np.ndarray) -> float | None:
    hit = [float(tt) for tt, p in zip(t, phase, strict=True) if "ready" in str(p).lower()]
    return hit[0] if hit else None


_EVENT_RE = re.compile(r"t_s=([-0-9.eE+]+), name='([^']*)'")


def load_case(path: Path) -> Case:
    path = Path(path)
    rec = _npz(path / "record" / "record.npz")
    res = _json(path / "result.json")
    t_rec = rec["t"]
    common = dict(
        path=path, label=f"{path.parent.name} / {path.name}", t_rec=t_rec, pos=rec["body_pos"],
        quat=rec["body_quat_wxyz"], s_motor=rec["s_motor"], stroke_true=rec["stroke_true"],
        head_bar=rec["meas.head_pressure"] / 1e5, rod_bar=rec["meas.rod_pressure"] / 1e5,
        stroke_meas_mm=rec["meas.stroke_corrected"] * 1e3, imu_tilt_deg=_imu_tilt_deg(rec["meas.specific_force"]))
    r8 = _npz(path / "r8_series.npz") if (path / "r8_series.npz").exists() else None
    if r8 is not None and "issued_u" in r8:
        t_u, u = r8["t"], r8["issued_u"]
    else:
        t_u, u = t_rec, rec["u_cmd"]
    notes: list[str] = []
    if (path / "step_series.npz").exists():  # ---------------- S9 SCM
        st = _npz(path / "step_series.npz")
        args = res.get("args", {})
        if r8 is not None and "phase" in r8:
            t_ph, ph = r8["t"], r8["phase"]
        else:
            rows = [p for p in res.get("phases", []) if isinstance(p, dict)]
            t_ph, ph = _expand_phases([(p["t_s"], p["phase"]) for p in rows], t_rec)
            notes.append("phase: result.json phases (absolute time)")
        events = [(float(e["t_s"]), str(e["name"])) for e in res.get("events", []) if isinstance(e, dict)]
        rows = res.get("s9_rows", [])
        t_gap = np.array([r["t_s"] for r in rows], float)
        if rows and "crawler_gap_min_m" in rows[0]:
            gap = np.array([np.nan if r.get("crawler_gap_min_m") is None else r["crawler_gap_min_m"] for r in rows],
                           float)
            gap_label = "크롤러 틈(참, 전 절점 최소)"
        else:
            gap = np.array([np.nan if r.get("rut_clearance_m") is None else r["rut_clearance_m"] for r in rows], float)
            gap_label = "크롤러 틈(참, 바퀴 자국 기준 최소)"
        comp = _npz(path / "completion_series.npz") if (path / "completion_series.npz").exists() else None
        normal = np.asarray((res.get("settle_slope") or {}).get("plane_normal_world") or [0.0, 0.0, 1.0], float)
        pp = _first_key(res.get("meta", {}), "plane_point_world_m")
        point = np.asarray(pp if pp is not None else [0.0, 0.0, float("nan")], float)
        scm_nodes = path / "scm_nodes.npz"
        return Case(**common, kind="S9", level=str(args.get("level", "top")),
                    pad_variant=str(args.get("pad_variant", "dwg_rear250")), t_u=t_u, u_mm_s=u * 1e3,
                    t_phase=t_ph, phase=ph, events=events, t_fast=st["t_s"], pad_N=st["scm_pad_normal_N"],
                    roll_pitch_deg=st["roll_pitch_deg"], crawler_N=st["scm_crawler_normal_N"],
                    t_crawler=st["t_s"], track_N=st.get("scm_track_normal_raw_N"),
                    state3=st["pad_sinkage_geometric_m"], state3_kind="sinkage", t_gap=t_gap, gap_m=gap,
                    gap_label=gap_label, gap_is_approx=False,
                    t_ctrl_gap=None if comp is None else comp["t_s"],
                    ctrl_gap_m=None if comp is None else comp["clearance_filtered_m"],
                    plane_normal=normal / np.linalg.norm(normal), plane_point=point, pad_floor_delta=None,
                    t_ready=_first_ready(t_ph, ph), notes=notes,
                    scm_nodes=scm_nodes if scm_nodes.exists() else None,
                    mass_scale=float(args.get("mass_scale", 1.0)),
                    t_event=((res.get("soil_event") or {}).get("driver") or {}).get("t_ev_s"))
    # ---------------------------------------------------------------- rigid (S8 L2b / S6 L1-R)
    settings = res.get("settings", {})
    s8s = _npz(path / "s8_series.npz") if (path / "s8_series.npz").exists() else None
    if r8 is not None and "phase" in r8:
        t_ph, ph = r8["t"], r8["phase"]
    elif s8s is not None and "phase" in s8s:
        t_ph, ph = s8s["t"], s8s["phase"]
    else:
        rows = res.get("phases", [])
        off = float(t_rec[0]) - float(rows[0][0])
        t_ph, ph = _expand_phases([(float(a) + off, b) for a, b in rows], t_rec)
        notes.append(f"phase: result.json phases are loop-relative, shifted by {off:+.3f} s (record t0 - first)")
    events = []
    ce = path / "controller_events.json"
    if ce.exists():
        for s in _json(ce):
            m = _EVENT_RE.search(str(s))
            if m:
                events.append((float(m.group(1)), m.group(2)))
    pads = np.load(path / "pads.npz", allow_pickle=False)
    t_fast = pads["t"]
    fp = res.get("floor_plane") or {}
    normal = np.asarray(fp.get("normal_world", [0.0, 0.0, 1.0]), float)
    normal = normal / np.linalg.norm(normal)
    offset = float(fp.get("offset_m", np.nan))
    point = normal * offset
    # local floor under each pad: contact point height over the plane while the pad carries > 1 kN (held otherwise;
    # contact_point_world is filled also without contact), rounded to 1 mm (contact compliance is not a floor change)
    cp = pads["contact_point_world"]
    loaded = pads["N"] > 1000.0
    raw = np.einsum("tkj,j->tk", cp, normal) - offset
    delta = np.zeros_like(raw)
    last = np.zeros(4)
    base = np.full(4, np.nan)  # contact height at the first loaded sample (contact compliance cancels)
    for i in range(len(raw)):
        ok = loaded[i] & np.isfinite(raw[i])
        base = np.where(ok & np.isnan(base), raw[i], base)
        last = np.where(ok, raw[i] - base, last)
        delta[i] = last
    delta[np.abs(delta) < 2e-3] = 0.0
    g8 = res.get("g8")
    if g8:  # G8 block (spec 360.1): constant from the start under the block leg
        h = float(g8.get("h_m", 0.0))
        delta[:, LEGS.index(str(g8.get("leg")))] = h
        notes.append(f"G8 block under {g8.get('leg')}: h = {h * 1e3:.1f} mm (result.json g8.h_m)")
    if (path / "crawler_gap.npz").exists():
        cg = _npz(path / "crawler_gap.npz")
        t_gap, gap, approx, gap_label = cg["t"], cg["min_gap_m"], False, "크롤러 틈(참, crawler_gap.npz)"
    else:
        t_gap, gap, approx, gap_label = t_rec, None, True, "크롤러 틈(근사: 메시 바닥점 - 바닥 평면)"
    F_cr = rec["F_crawler"]
    if "body_quat_wxyz" in pads.files:  # 1 ms body attitude (newer S8 folders), every 10th sample
        q = pads["body_quat_wxyz"]
        sel = np.arange(0, len(t_fast), 10)
        rp_s = _roll_pitch_from_quats(q[sel])
        rp_fast = np.stack([np.interp(t_fast, t_fast[sel], rp_s[:, j]) for j in range(2)], axis=1)
    else:
        rp_r = _roll_pitch_from_quats(rec["body_quat_wxyz"])
        rp_fast = np.stack([np.interp(t_fast, t_rec, rp_r[:, j]) for j in range(2)], axis=1)
        notes.append("roll / pitch truth: 10 Hz record quaternion interpolated (pads.npz has no body attitude)")
    case = Case(**common, kind="S8", level=str(settings.get("level", "top")),
                pad_variant=_default_pad_variant(), t_u=t_u, u_mm_s=u * 1e3, t_phase=t_ph, phase=ph,
                events=events, t_fast=t_fast, pad_N=pads["N"], roll_pitch_deg=rp_fast,
                crawler_N=F_cr @ normal, t_crawler=t_rec, track_N=None, state3=pads["F_cyl"],
                state3_kind="force", t_gap=t_gap, gap_m=gap if gap is not None else np.zeros(len(t_rec)),
                gap_label=gap_label, gap_is_approx=approx, t_ctrl_gap=None, ctrl_gap_m=None,
                plane_normal=normal, plane_point=point, pad_floor_delta=delta, t_ready=_first_ready(t_ph, ph),
                notes=notes, t_event=res.get("event_t_s"))
    pads.close()
    return case


def _expand_phases(rows: list[tuple[float, str]], t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    starts = np.array([a for a, _ in rows], float)
    names = [str(b) for _, b in rows]
    idx = np.clip(np.searchsorted(starts, t + 1e-9, side="right") - 1, 0, len(names) - 1)
    return t, np.array([names[i] for i in idx])


def _default_pad_variant() -> str:
    return str(_json(PAD_VARIANTS_JSON)["default"])


def pad_scales(variant: str) -> tuple[float, ...]:
    """Linear plan scale per leg of the C8 pad mesh (CAD 330 type) to draw ``variant``:
    sqrt(A_variant / A_cad330) from pad_variants.json."""
    pv = _json(PAD_VARIANTS_JSON)["variants"]
    a0 = pv["cad330"]["legs"]
    av = pv[variant]["legs"]
    return tuple(float(np.sqrt(av[leg]["bottom_area_m2"] / a0[leg]["bottom_area_m2"])) for leg in LEGS)


# =============================================================================================
# 3D (worker processes)
# =============================================================================================

_W: dict[str, Any] = {}


def _scaled_parts(scales: tuple[float, ...]):
    key = tuple(round(s, 6) for s in scales)
    cache = _W.setdefault("scaled", {})
    if key in cache:
        return cache[key]
    out = []
    for part in _W["parts"]:
        if part.kind == "pad" and part.leg in LEGS and abs(key[LEGS.index(part.leg)] - 1.0) > 1e-9:
            s = key[LEGS.index(part.leg)]
            v_all = np.vstack([pc.vertices for pc in part.pieces])
            zmin = v_all[:, 2].min()
            bottom = v_all[v_all[:, 2] < zmin + 0.005]
            c = 0.5 * (bottom[:, :2].min(axis=0) + bottom[:, :2].max(axis=0))
            pieces = []
            for pc in part.pieces:
                v = pc.vertices.copy()
                v[:, :2] = c + (v[:, :2] - c) * s
                pieces.append(cadr.Piece(v, pc.topology, pc.colour))
            part = cadr.Part(part.name, part.kind, part.leg, part.moves_with_auger, pieces, part.faces_source,
                             part.faces_drawn)
        out.append(part)
    cache[key] = out
    return out


def _worker_init(parts_pickle: str) -> None:
    with open(parts_pickle, "rb") as h:
        _W["parts"] = pickle.load(h)["parts"]
    cadr.register_view(VIEW, VIEW_TOWARD)


def _plane_z(n, p0, x, y):
    return p0[2] - (n[0] * (x - p0[0]) + n[1] * (y - p0[1])) / n[2]


def render_3d(task: dict) -> tuple[int, bytes]:
    parts = _scaled_parts(task["pad_scales"])
    items = cadr.posed_items(parts, auger_travel_m=task["auger"], s_motor=task["s_motor"],
                             direction=task["direction"], pos=task["pos"], rot=task["rot"])
    if task.get("terrain") is not None:
        for verts, faces in task["terrain"]:
            items.append(rlv.SceneItem(verts, rlv.part_topology(verts, faces), SOIL_COLOR, 0.0, True))
    w, h = task["size"]
    s = cadr.SUPERSAMPLE
    fig = plt.figure(figsize=(w * s / cadr.DPI, h * s / cadr.DPI), dpi=cadr.DPI, facecolor="none")
    ax = fig.add_axes((0, 0, 1, 1))
    lim = task["limits"]
    ax.set_xlim(*lim[0])
    ax.set_ylim(*lim[1])
    ax.set_axis_off()
    ax.patch.set_alpha(0.0)
    px_per_m = w * s / (lim[0][1] - lim[0][0])
    n, p0 = task["plane_normal"], task["plane_point"]
    cadr.floor_patch(ax, VIEW, p0, n, task["floor_rect"], ss=s)
    for k in range(4):  # per-pad floor tile (rigid floor change) or pit (SCM schematic)
        c = task["pad_xy"][k]
        hw = task["pad_half"][k] + 0.05
        if task["mode"] == "pit":
            sink = max(0.0, float(task["sink"][k]))
            if sink <= 0.0:
                continue
            col, a, dz = PIT_COLOR, min(0.9, 0.15 + sink / 0.08), 0.0
        else:
            dz = float(task["tile"][k])
            if dz == 0.0:
                continue
            col, a = (TILE_COLOR if dz > 0 else PIT_COLOR), 0.85
        sq = np.array([[c[0] - hw, c[1] - hw], [c[0] + hw, c[1] - hw], [c[0] + hw, c[1] + hw],
                       [c[0] - hw, c[1] + hw]])
        pts = np.array([[x, y, _plane_z(n, p0, x, y) + dz] for x, y in sq])
        ax.add_patch(Polygon(cadr.screen(pts, VIEW), closed=True, facecolor=col, alpha=a,
                             edgecolor="#3b2a17", lw=0.5 * s, zorder=0.55))
        if dz > 0:  # block sides (the two visible ones)
            for i0, i1 in ((0, 1), (1, 2)):
                side = np.array([pts[i0], pts[i1], pts[i1] - [0, 0, dz], pts[i0] - [0, 0, dz]])
                ax.add_patch(Polygon(cadr.screen(side, VIEW), closed=True, facecolor="#7d705e", alpha=0.9,
                                     edgecolor="#3b2a17", lw=0.4 * s, zorder=0.56))
    style = rlv.EdgeStyle(enabled=True, width_px=0.45 * s)
    scene = rlv.shade_scene(items, VIEW, px_per_m, style, cadr.DPI, depth_fade=True)
    ax.add_collection(rlv.scene_collection(scene, zorder=1.0), autolim=False)
    fig.canvas.draw()
    img = Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy(), "RGBA")
    plt.close(fig)
    img = img.convert("RGBa").resize((w, h), Image.Resampling.LANCZOS).convert("RGBA")
    b = io.BytesIO()
    img.save(b, format="PNG", compress_level=1)
    return task["i"], b.getvalue()


# =============================================================================================
# SCM node surface (scm_nodes.npz)
# =============================================================================================


class ScmSurface:
    """Replays scm_nodes.npz (run_S9.ScmNodeRecorder) and builds a decimated triangle mesh of the recorded nodes."""

    def __init__(self, path: Path, render_grid_m: float = 0.03) -> None:
        z = _npz(path)
        self.snap_t = z["snap_t_s"]
        self.frames = z["frames"]
        self.names = [str(n) for n in z["terrain_names"]]
        self.grid = z["grid_m"]
        self.rows = (z["snap"], z["terrain"], z["i"], z["j"], z["level_m"].astype(float))
        self.render_grid_m = render_grid_m
        self._state: list[dict[tuple[int, int], float]] = [{} for _ in self.names]
        self._applied = -1

    def advance(self, t: float) -> int:
        snap, ter, ii, jj, lv = self.rows
        n = int(np.searchsorted(self.snap_t, t + 1e-9, side="right") - 1)
        while self._applied < n:
            self._applied += 1
            m = snap == self._applied
            for k, i, j, v in zip(ter[m], ii[m], jj[m], lv[m], strict=True):
                self._state[int(k)][(int(i), int(j))] = float(v)
        return n

    def mesh(self, t: float) -> list[tuple[np.ndarray, np.ndarray]]:
        from scipy.spatial.transform import Rotation

        n = self.advance(t)
        out = []
        if n < 0:
            return out
        for k, st in enumerate(self._state):
            if not st:
                continue
            g = float(self.grid[k])
            step = max(1, int(round(self.render_grid_m / g)))
            keys = np.array(list(st.keys()), int)
            lv = np.array(list(st.values()), float)
            sel = (keys[:, 0] % step == 0) & (keys[:, 1] % step == 0)
            keys, lv = keys[sel] // step, lv[sel]
            if len(keys) < 4:
                continue
            i0, j0 = keys.min(axis=0)
            ni, nj = keys.max(axis=0) - (i0, j0) + 1
            idx = -np.ones((ni, nj), int)
            idx[keys[:, 0] - i0, keys[:, 1] - j0] = np.arange(len(keys))
            a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
            ok = (a >= 0) & (b >= 0) & (c >= 0) & (d >= 0)
            faces = np.concatenate([np.stack([a[ok], b[ok], c[ok]], 1), np.stack([a[ok], c[ok], d[ok]], 1)])
            fr = self.frames[n, k]
            rot = Rotation.from_quat([fr[4], fr[5], fr[6], fr[3]]).as_matrix()
            local = np.stack([keys[:, 0] * g * step, keys[:, 1] * g * step, lv], axis=1)
            out.append((local @ rot.T + fr[:3], faces))
        return out


# =============================================================================================
# plots (static background) and per-frame overlays
# =============================================================================================


def _style(ax, title, ylabel):
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#b9b8b3")
    ax.tick_params(labelsize=6.5, colors="#52514e", length=2, pad=1)
    ax.grid(True, color="#ebeae6", lw=0.5)
    ax.set_title(title, fontsize=7.5, loc="left", color="#0b0b0b", pad=2)
    ax.set_ylabel(ylabel, fontsize=6.5, color="#52514e", labelpad=1)


def _win(t, t0, t1):
    return (t >= t0 - 0.5) & (t <= t1 + 0.5)


def phase_segments(c: Case) -> list[tuple[float, float, str]]:
    out = []
    t, ph = c.t_phase, [str(p).lower() for p in c.phase]
    if not len(t):
        return out
    start = 0
    for i in range(1, len(t) + 1):
        if i == len(t) or ph[i] != ph[start]:
            end = float(t[i]) if i < len(t) else float(t[-1]) + 0.1
            out.append((float(t[start]), end, ph[start]))
            start = i
    return out


def build_plots(c: Case, t0: float, t1: float, speed: float):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor="#fcfcfb")
    X0 = W3D + 20
    colw, rowh, gapx, top = (W - X0 - 40 - 24) / 2, 124, 40, 70

    def box(col, row):
        x = X0 + col * (colw + gapx) + 18
        y = top + row * (rowh + 30)
        return fig.add_axes((x / W, 1 - (y + rowh) / H, (colw - 18) / W, rowh / H))

    tr, mr = c.t_rec, _win(c.t_rec, t0, t1)
    tf, mf = c.t_fast, _win(c.t_fast, t0, t1)
    axes = []
    ax = box(0, 0)
    axes.append(ax)
    for k, leg in enumerate(LEGS):
        ax.plot(tr[mr], c.head_bar[mr, k], color=LEG_COLORS[leg], lw=1.0, label=leg)
        ax.plot(tr[mr], c.rod_bar[mr, k], color=LEG_COLORS[leg], lw=0.6, ls="--")
    _style(ax, "입력: 압력 헤드(실선)·로드(점선), 10 Hz", "bar")
    ax.legend(fontsize=6, ncol=4, loc="upper left", frameon=False, handlelength=1.2, columnspacing=0.8)
    ax = box(0, 1)
    axes.append(ax)
    ax.plot(tf[mf], c.roll_pitch_deg[mf, 0], color="#2a78d6", lw=1.0, label="roll 참")
    ax.plot(tf[mf], c.roll_pitch_deg[mf, 1], color="#e34948", lw=1.0, label="pitch 참")
    ax.plot(tr[mr], c.imu_tilt_deg[mr, 0], ".", color="#2a78d6", ms=1.6, label="roll IMU")
    ax.plot(tr[mr], c.imu_tilt_deg[mr, 1], ".", color="#e34948", ms=1.6, label="pitch IMU")
    ax.axhspan(-TARGET_BAND_DEG, TARGET_BAND_DEG, color="#008300", alpha=0.07, lw=0)
    _style(ax, "입력: roll·pitch (선 참값, 점 IMU 비력 기울기 10 Hz, 가속 포함)", "deg")
    ax.legend(fontsize=6, ncol=4, loc="upper left", frameon=False, handlelength=1.2, columnspacing=0.8)
    rp = np.concatenate([c.roll_pitch_deg[mf].ravel(), [-TARGET_BAND_DEG, TARGET_BAND_DEG]])
    lo, hi = np.nanpercentile(rp, [0.2, 99.8])
    pad = 0.1 * (hi - lo) + 0.02
    ax.set_ylim(lo - pad, hi + pad)  # IMU acceleration spikes are clipped by the truth range
    ax = box(0, 2)
    axes.append(ax)
    for k, leg in enumerate(LEGS):
        ax.plot(tr[mr], c.stroke_meas_mm[mr, k], color=LEG_COLORS[leg], lw=1.0)
    _style(ax, "입력: 행정 센서(보정), 10 Hz", "mm")
    ax = box(0, 3)
    axes.append(ax)
    mu = _win(c.t_u, t0, t1)
    for k, leg in enumerate(LEGS):
        ax.step(c.t_u[mu], c.u_mm_s[mu, k], where="post", color=LEG_COLORS[leg], lw=1.0)
    ax.axhline(V_MAX_MM_S, color="#b9b8b3", lw=0.6, ls=":")
    _style(ax, "출력: 속도 명령 u (+ 신장), 10 Hz", "mm/s")
    ax.set_xlabel("시각 [s]", fontsize=6.5, color="#52514e", labelpad=1)
    ax = box(1, 0)
    axes.append(ax)
    for k, leg in enumerate(LEGS):
        ax.plot(tf[mf], c.pad_N[mf, k] / 1e3, color=LEG_COLORS[leg], lw=1.0)
    _style(ax, "상태: 패드 법선 반력" + (" (SCM)" if c.kind == "S9" else "") + ", 1 ms", "kN")
    ax = box(1, 1)
    axes.append(ax)
    mc = _win(c.t_crawler, t0, t1)
    ax.plot(c.t_crawler[mc], c.crawler_N[mc] / 1e3, color="#404040", lw=1.1, label="크롤러 합")
    if c.track_N is not None:
        ax.plot(tf[mf], c.track_N[mf, 0] / 1e3, color="#8a6a45", lw=0.7, ls="--", label="트랙 1")
        ax.plot(tf[mf], c.track_N[mf, 1] / 1e3, color="#e87ba4", lw=0.7, ls="--", label="트랙 2")
    _style(ax, "상태: 크롤러 법선 반력, " + ("1 ms" if c.kind == "S9" else "10 Hz"), "kN")
    ax.legend(fontsize=6, ncol=3, loc="upper right", frameon=False, handlelength=1.2)
    ax = box(1, 2)
    axes.append(ax)
    if c.state3_kind == "sinkage":
        for k, leg in enumerate(LEGS):
            ax.plot(tf[mf], c.state3[mf, k] * 1e3, color=LEG_COLORS[leg], lw=1.0)
        ax.axhline(0, color="#52514e", lw=0.6)
        _style(ax, "상태: 패드 침하(기하, 음수 = 흙 위), 1 ms", "mm")
    else:
        for k, leg in enumerate(LEGS):
            ax.plot(tf[mf], c.state3[mf, k] / 1e3, color=LEG_COLORS[leg], lw=1.0)
        _style(ax, "상태: 실린더 힘(실제), 1 ms", "kN")
    ax = box(1, 3)
    axes.append(ax)
    mg = _win(c.t_gap, t0, t1)
    ax.plot(c.t_gap[mg], c.gap_m[mg] * 1e3, color="#404040", lw=1.1, ls="--" if c.gap_is_approx else "-",
            label=c.gap_label)
    if c.ctrl_gap_m is not None:
        mcg = _win(c.t_ctrl_gap, t0, t1)
        ax.plot(c.t_ctrl_gap[mcg], c.ctrl_gap_m[mcg] * 1e3, color="#e87ba4", lw=1.0, label="제어기 추정 틈")
    ax.axhline(GAP_LIMIT_MM, color="#b9b8b3", lw=0.6, ls=":")
    _style(ax, "상태: 크롤러 틈", "mm")
    ax.legend(fontsize=6, ncol=1, loc="upper left", frameon=False, handlelength=1.2)
    ax.set_xlabel("시각 [s]", fontsize=6.5, color="#52514e", labelpad=1)
    for n, ax in enumerate(axes):
        if n % 4 != 3:
            ax.tick_params(labelbottom=False)
        ax.set_xlim(t0, t1)
        ax.margins(y=0.08)
        ax.ticklabel_format(axis="y", useOffset=False, style="plain")
    sx0, sx1 = (X0 + 18) / W, (W - 22) / W
    sax = fig.add_axes((sx0, 1 - 52 / H, sx1 - sx0, 14 / H))
    for a, b, name in phase_segments(c):
        a2, b2 = max(a, t0), min(b, t1)
        if b2 <= a2:
            continue
        sax.axvspan(a2, b2, color=PHASE_COLORS.get(name, "#d0d0d0"), lw=0)
        if b2 - a2 > (t1 - t0) * 0.05:
            sax.text((a2 + b2) / 2, 0.5, name.upper(), ha="center", va="center", fontsize=6.5, color="#0b0b0b")
    for t, _ in c.events:
        if t0 <= t <= t1:
            sax.plot([t, t], [0, 1], color="#0b0b0b", lw=0.5)
    sax.set_xlim(t0, t1)
    sax.set_ylim(0, 1)
    sax.set_axis_off()
    fig.text((X0 + 18) / W, 1 - 18 / H, "제어 단계(검은 눈금 = 제어기 사건)", fontsize=7, color="#52514e")
    fig.text(14 / W, 1 - 22 / H, c.label, fontsize=9.5, color="#0b0b0b", weight="bold")
    sub = f"패드 {c.pad_variant} · 오거 {c.level}" + (f" · 질량 x{c.mass_scale:g}" if c.mass_scale != 1.0 else "")
    sub += f" · 재생 x{speed:g}"
    fig.text(14 / W, 1 - 36 / H, sub, fontsize=7.5, color="#52514e")
    fig.canvas.draw()
    bg = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())
    spans = []
    for ax in [*axes, sax]:
        bb = ax.get_window_extent()
        spans.append((bb.x0, bb.x1, H - bb.y1, H - bb.y0))
    plt.close(fig)
    return bg, spans


def _font(size):
    try:
        return ImageFont.truetype("malgun.ttf", size)
    except OSError:
        return ImageFont.load_default()


def gauge_range_deg(c: Case, t0: float, t1: float) -> float:
    m = _win(c.t_fast, t0, t1)
    peak = float(np.nanmax(np.abs(c.roll_pitch_deg[m]))) if m.any() else 0.5
    for r in (0.5, 1.0, 2.0, 5.0, 10.0):
        if peak <= 0.95 * r:
            return r
    return 20.0


def draw_inset(dr: ImageDraw.ImageDraw, x0: int, y0: int, roll: float, pitch: float, strokes_m, rng: float,
               fonts) -> None:
    """Attitude inset: two magnified level gauges (+-rng deg, target band) and four stroke bars."""
    f, fs = fonts
    w, h = 250, 120
    dr.rectangle([x0, y0, x0 + w, y0 + h], fill=(252, 252, 251), outline=(185, 184, 179))
    dr.text((x0 + 6, y0 + 3), f"자세 계기 (확대, 범위 ±{rng:g}°)", fill=(82, 81, 78), font=fs)
    gx0, gx1 = x0 + 52, x0 + 150
    for row, (name, val, col) in enumerate((("roll", roll, (42, 120, 214)), ("pitch", pitch, (227, 73, 72)))):
        yc = y0 + 34 + row * 34
        dr.text((x0 + 6, yc - 8), name, fill=(11, 11, 11), font=fs)
        dr.rounded_rectangle([gx0, yc - 7, gx1, yc + 7], radius=7, fill=(240, 239, 235), outline=(150, 150, 150))
        bx = (gx0 + gx1) / 2
        half = (gx1 - gx0) / 2
        b = TARGET_BAND_DEG / rng * half
        dr.rectangle([bx - b, yc - 6, bx + b, yc + 6], fill=(206, 230, 206))
        dr.line([(bx, yc - 9), (bx, yc + 9)], fill=(82, 81, 78), width=1)
        xv = bx + float(np.clip(val / rng, -1, 1)) * (half - 6)
        dr.ellipse([xv - 6, yc - 6, xv + 6, yc + 6], fill=col, outline=(11, 11, 11))
        dr.text((x0 + 6, yc + 6), f"{val:+.3f}°", fill=(82, 81, 78), font=fs)
    sx = x0 + 160
    top, bot = y0 + 22, y0 + h - 18
    for k, leg in enumerate(LEGS):
        xx = sx + k * 22
        dr.rectangle([xx, top, xx + 12, bot], outline=(150, 150, 150), fill=(240, 239, 235))
        frac = float(np.clip(strokes_m[k] / STROKE_MAX_M, 0, 1))
        col = tuple(int(LEG_COLORS[leg][i:i + 2], 16) for i in (1, 3, 5))
        y_fill = bot - frac * (bot - top)
        if y_fill < bot - 1:
            dr.rectangle([xx + 1, y_fill, xx + 11, bot - 1], fill=col)
        ym = bot - STROKE_MARK_M / STROKE_MAX_M * (bot - top)
        dr.line([(xx - 2, ym), (xx + 14, ym)], fill=(227, 73, 72), width=1)
        dr.text((xx - 1, bot + 2), leg, fill=(82, 81, 78), font=fs)
    dr.text((sx - 2, y0 + 3), "행정 0-700 mm", fill=(82, 81, 78), font=fs)


# =============================================================================================
# GIF (streamed frames) / MP4
# =============================================================================================


def write_gif_stream(frame_paths: list[Path], duration_ms: float, path: Path, scale: float) -> dict:
    """Global 255-colour palette from 8 sample frames + leg / phase swatches, pixels equal to the previous frame
    written as the reserved transparent index 255, disposal 1 (render_S4_gifs.write_gif scheme), frames read one
    at a time from disk; identical frames merged into the previous frame's duration."""
    def load(p):
        im = Image.open(p).convert("RGB")
        if scale != 1.0:
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
        return im

    ids = sorted(set(np.linspace(0, len(frame_paths) - 1, 8).astype(int).tolist()))
    samples = [load(frame_paths[i]) for i in ids]
    w, h = samples[0].size
    sw_cols = [*LEG_COLORS.values(), *PHASE_COLORS.values(), "#e34948", "#404040", "#8a6a45", SOIL_COLOR, PIT_COLOR,
               cadr.GROUND_COLOR, "#ff4d06", "#696969", "#bfbfbf"]
    sw = []
    for col in sw_cols:
        base = np.array(matplotlib.colors.to_rgb(col))
        for shade in (0.55, 0.8, 1.0):
            sw.append(tuple(int(round(v * 255)) for v in np.clip(base * shade, 0, 1)))
    sheet = Image.new("RGB", (w * len(samples), h + 40))
    for k, im in enumerate(samples):
        sheet.paste(im, (k * w, 0))
    cw = max(1, sheet.width // len(sw))
    for k, col in enumerate(sw):
        sheet.paste(Image.new("RGB", (cw, 40), col), (k * cw, h))
    pal = sheet.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    colours = pal.getpalette()[: 3 * 255]
    colours += [0] * (3 * 255 - len(colours)) + [255, 0, 255]
    indexed, durs, prev = [], [], None
    for p in frame_paths:
        codes = np.asarray(load(p).quantize(palette=pal, dither=Image.Dither.NONE)).copy()
        if prev is not None and np.array_equal(codes, prev):
            durs[-1] += duration_ms
            continue
        coded = codes.copy()
        if prev is not None:
            coded[codes == prev] = 255
        prev = codes
        im = Image.fromarray(coded, "P")
        im.putpalette(colours)
        im.info["transparency"] = 255
        indexed.append(im)
        durs.append(duration_ms)
    durs = [max(20, int(round(d / 10.0)) * 10) for d in durs]
    cadr.save_atomic(path, lambda target: indexed[0].save(target, save_all=True, append_images=indexed[1:],
                                                          duration=durs, loop=0, optimize=False, disposal=1,
                                                          transparency=255))
    with Image.open(path) as g:
        n = g.n_frames
    return {"path": cadr.rel(path), "frames": n, "size_bytes": path.stat().st_size, "resolution_px": [w, h],
            "loop_s": round(sum(durs) / 1000, 2), "frame_ms": sorted(set(durs))[:3]}


def write_mp4(frame_dir: Path, fps: float, path: Path) -> dict:
    tmp = path.with_name(path.stem + ".tmp.mp4")
    subprocess.run([str(FFMPEG), "-y", "-loglevel", "error", "-framerate", f"{fps:g}", "-i",
                    str(frame_dir / "f%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
                    "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(path)
    return {"path": cadr.rel(path), "size_bytes": path.stat().st_size, "fps": fps, "codec": "libx264 yuv420p crf 23"}


# =============================================================================================
# one case
# =============================================================================================


def crawler_bottom_points(parts) -> np.ndarray:
    v = np.vstack([pc.vertices for p in parts if p.name == "crawler" for pc in p.pieces])
    return v[v[:, 2] < v[:, 2].min() + 0.01]


def approx_gap(c: Case, pts: np.ndarray) -> np.ndarray:
    from outrigger_sim.frames import quat_to_matrix

    off = float(c.plane_normal @ c.plane_point)
    out = np.empty(len(c.t_rec))
    for i in range(len(c.t_rec)):
        R = quat_to_matrix(c.quat[i])
        out[i] = float(np.min((pts @ R.T + c.pos[i]) @ c.plane_normal) - off)
    return out


def render_case(case_dir: Path, a: argparse.Namespace, parts, parts_pickle: Path, pool) -> dict:
    from outrigger_sim.frames import quat_to_matrix
    from outrigger_sim.geometry import extension_direction, pad_sphere_centre_body_m
    from outrigger_sim.params import load_params

    t_case = time.perf_counter()
    c = load_case(case_dir)
    if a.scm_nodes is not None:
        c.scm_nodes = a.scm_nodes
    params = load_params(level=c.level)
    direction = extension_direction(params)
    auger = float(params.superstructure.auger_travel_m)
    floor_z = float(params.ground.crawler_bottom_z_m)
    if not np.all(np.isfinite(c.plane_point)):
        c.plane_point = np.array([0.0, 0.0, floor_z])
    if c.gap_is_approx:
        c.gap_m = approx_gap(c, crawler_bottom_points(parts))
        c.notes.append("crawler gap APPROXIMATION: min over 40 mm-clustered crawler mesh bottom points of "
                       "n . x - offset (rigid floor plane), 10 Hz record pose")
    scales = pad_scales(c.pad_variant)
    pad_half = tuple(0.165 * s for s in scales)  # CAD 330 pad half side x scale
    t0 = float(c.t_rec[0]) if a.t_start is None else a.t_start
    ready_after_event = None
    if c.t_event is not None:
        # first READY sample after a non-READY sample that follows the event (READY re-entered)
        seq = [(float(tt), "ready" in str(p).lower()) for tt, p in zip(c.t_phase, c.phase, strict=True)
               if tt > float(c.t_event)]
        left = next((k for k, (_, r) in enumerate(seq) if not r), None)
        ready_after_event = next((tt for tt, r in seq[left:] if r), None) if left is not None else None
        c.notes.append(f"event at {float(c.t_event):.2f} s: window to the READY re-entry "
                       f"{ready_after_event if ready_after_event is not None else 'none (record end)'}")
    if a.t_end is not None:
        t1 = a.t_end
    elif c.t_event is not None:
        t1 = float(c.t_rec[-1]) if ready_after_event is None else min(float(c.t_rec[-1]),
                                                                       ready_after_event + a.tail_s)
    elif c.t_ready is not None:
        t1 = min(float(c.t_rec[-1]), c.t_ready + a.tail_s)
    else:
        t1 = float(c.t_rec[-1])
        c.notes.append("no READY in the record: rendered to the record end")
    times = np.arange(t0, t1 + 1e-9, 1.0 / a.fps_sim)
    if a.max_frames:
        times = times[: a.max_frames]
    stage = c.kind
    out_dir = a.out_dir or STAGE_DIRS[stage]
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{case_dir.parent.name}__{case_dir.name}"
    info = {"case": cadr.rel(case_dir), "kind": stage, "window_s": [t0, float(times[-1])], "t_ready_s": c.t_ready,
            "frames": int(len(times)), "fps_sim": a.fps_sim, "speed": a.speed, "pad_variant": c.pad_variant,
            "pad_plan_scale": scales, "auger_level": c.level, "mass_scale": c.mass_scale,
            "ground": ("SCM node surface (scm_nodes.npz)" if c.scm_nodes else "SCM schematic (pits by pad sinkage)")
            if stage == "S9" else "rigid plane + per-pad floor tiles", "crawler_gap": c.gap_label,
            "crawler_gap_approx": c.gap_is_approx, "notes": c.notes}
    if a.dry:
        return info
    surf = ScmSurface(c.scm_nodes) if (stage == "S9" and c.scm_nodes) else None
    # tasks
    tasks = []
    for i, t in enumerate(times):
        j = int(np.argmin(np.abs(c.t_rec - t)))
        pos, rot, s = c.pos[j].copy(), quat_to_matrix(c.quat[j]), c.s_motor[j].copy()
        jf = int(np.argmin(np.abs(c.t_fast - t)))
        pad_xy = np.array([rot @ np.asarray(pad_sphere_centre_body_m(params, k, s[k])) + pos for k in range(4)])
        task = dict(i=i, t=float(t), pos=pos, rot=rot, s_motor=s, auger=auger, direction=direction,
                    pad_scales=scales, pad_half=pad_half, pad_xy=pad_xy, plane_normal=c.plane_normal,
                    plane_point=c.plane_point, size=(W3D, H3D))
        if stage == "S9":
            task.update(mode="pit", sink=(c.state3[jf].copy() if surf is None else np.zeros(4)))
            task["terrain"] = surf.mesh(float(t)) if surf is not None else None
        else:
            task.update(mode="tile", tile=c.pad_floor_delta[jf].copy())
        tasks.append(task)
    # fixed view
    items0 = cadr.posed_items(parts, auger_travel_m=auger, s_motor=tasks[0]["s_motor"], direction=direction,
                              pos=tasks[0]["pos"], rot=tasks[0]["rot"])
    pts = cadr.items_points(items0, step=5)
    pts = pts[pts[:, 2] < ZCROP_M]
    rect = ((pts[:, 0].min() - 0.5, pts[:, 0].max() + 0.5), (pts[:, 1].min() - 0.5, pts[:, 1].max() + 0.5))
    fr = np.array([[x, y, _plane_z(c.plane_normal, c.plane_point, x, y)] for x in rect[0] for y in rect[1]])
    lim = cadr.fit_limits(cadr.screen(np.vstack([pts, fr]), VIEW), (W3D, H3D), margin=0.1)
    for tk in tasks:
        tk.update(limits=lim, floor_rect=rect)
    bg, spans = build_plots(c, t0, float(times[-1]) if len(times) > 1 else t1, a.speed)
    t_axis1 = float(times[-1]) if len(times) > 1 else t1
    rng = gauge_range_deg(c, t0, t_axis1)
    fdir = out_dir / "_frames" / stem
    if fdir.exists():
        shutil.rmtree(fdir)
    fdir.mkdir(parents=True)
    fonts = (_font(15), _font(11))
    segs = phase_segments(c)
    t_r = time.perf_counter()
    results = map(render_3d, tasks) if pool is None else pool.imap(render_3d, tasks, chunksize=2)
    paths = []
    for tk, (i, png) in zip(tasks, results, strict=True):
        t = tk["t"]
        frame = bg.copy()
        layer = Image.open(io.BytesIO(png)).convert("RGBA")
        frame.paste(layer, (0, Y3D), layer)
        dr = ImageDraw.Draw(frame)
        for x0, x1, y0, y1 in spans:
            x = x0 + (t - t0) / max(t_axis1 - t0, 1e-9) * (x1 - x0)
            dr.line([(round(x), y0), (round(x), y1)], fill=(227, 73, 72), width=1)
        jf = int(np.argmin(np.abs(c.t_fast - t)))
        jr = int(np.argmin(np.abs(c.t_rec - t)))
        r, p = c.roll_pitch_deg[jf]
        name = next((n for x, y, n in segs if x <= t < y), segs[-1][2] if segs else "").upper()
        dr.rectangle([12, 588, 12 + 250, 588 + 120], fill=(252, 252, 251))
        dr.text((16, 590), f"t = {t:6.1f} s   {name}", fill=(11, 11, 11), font=fonts[0])
        dr.text((16, 612), f"재생 x{a.speed:g} (일정 속도)", fill=(82, 81, 78), font=fonts[1])
        if stage == "S9":
            sk = c.state3[jf] * 1e3
            txt = "패드 침하 mm " + " ".join(f"{max(v, 0):.0f}" for v in sk)
            dr.text((16, 630), txt + "  (FL FR RL RR)", fill=(82, 81, 78), font=fonts[1])
            dr.text((16, 648), "지면: " + ("SCM 절점 기록면" if surf is not None else "도식(침하 깊이 = 색)"),
                    fill=(130, 130, 130), font=fonts[1])
        else:
            dz = c.pad_floor_delta[jf] * 1e3
            if np.any(dz != 0):
                dr.text((16, 630), "패드 아래 바닥 mm " + " ".join(f"{v:+.0f}" for v in dz), fill=(82, 81, 78),
                        font=fonts[1])
            dr.text((16, 648), "지면: 강체 평면", fill=(130, 130, 130), font=fonts[1])
        dr.text((16, 666), "3D 실제 크기 · 10 Hz 기록 재생", fill=(130, 130, 130), font=fonts[1])
        draw_inset(dr, 276, 588, float(r), float(p), c.stroke_true[jr], rng, fonts)
        fp = fdir / f"f{i:05d}.png"
        frame.save(fp, compress_level=1)
        paths.append(fp)
    t_r = time.perf_counter() - t_r
    gif_paths = paths[:: a.gif_every]
    info["gif"] = None if a.no_gif else write_gif_stream(
        gif_paths, 1000.0 * a.gif_every / (a.fps_sim * a.speed), out_dir / f"{stem}.gif", a.gif_scale)
    info["mp4"] = None if a.no_mp4 else write_mp4(fdir, a.fps_sim * a.speed, out_dir / f"{stem}.mp4")
    Image.open(paths[len(paths) // 2]).save(out_dir / f"{stem}_mid.png")
    info["layout_png"] = cadr.rel(out_dir / f"{stem}_mid.png")
    if not a.keep_frames:
        shutil.rmtree(fdir)
        try:
            (out_dir / "_frames").rmdir()
        except OSError:
            pass
    info["timing_s"] = {"render_and_compose": t_r, "total": time.perf_counter() - t_case,
                        "core_s_per_frame": t_r * max(1, a.jobs) / max(1, len(tasks))}
    try:
        import psutil

        info["rss_main_mb"] = psutil.Process().memory_info().rss / 1e6
    except Exception:  # noqa: BLE001
        pass
    return info


def merge_meta(path: Path, entries: list[dict], run: dict) -> None:
    meta = _json(path) if path.exists() else {"script": cadr.rel(Path(__file__)), "cases": {}}
    meta["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    meta.setdefault("runs", []).append(run)
    for e in entries:
        meta["cases"][e["case"]] = e
    cadr.save_atomic(path, lambda target: target.write_text(json.dumps(meta, ensure_ascii=False, indent=1,
                                                                       default=str), encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cases", nargs="*", type=Path)
    ap.add_argument("--list", type=Path, default=None, help="text file, one case folder per line (# = comment)")
    ap.add_argument("--fps-sim", type=float, default=2.0, help="frames per simulated second (MP4)")
    ap.add_argument("--speed", type=float, default=10.0, help="constant playback speed x real time")
    ap.add_argument("--gif-every", type=int, default=2, help="GIF uses every n-th frame")
    ap.add_argument("--gif-scale", type=float, default=0.75, help="GIF preview scale (0.75 = 960 x 540)")
    ap.add_argument("--tail-s", type=float, default=5.0, help="seconds after the first READY")
    ap.add_argument("--t-start", type=float, default=None)
    ap.add_argument("--t-end", type=float, default=None)
    ap.add_argument("--max-frames", type=int, default=0, help="smoke: first N frames only")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--out-dir", type=Path, default=None, help="override the stage gifs folder")
    ap.add_argument("--mesh-cache", type=Path, default=None)
    ap.add_argument("--scm-nodes", type=Path, default=None, help="override scm_nodes.npz (test)")
    ap.add_argument("--keep-frames", action="store_true")
    ap.add_argument("--no-gif", action="store_true")
    ap.add_argument("--no-mp4", action="store_true")
    ap.add_argument("--dry", action="store_true", help="load and plan only (no render)")
    a = ap.parse_args()
    cases = list(a.cases)
    if a.list:
        cases += [Path(s.strip()) for s in a.list.read_text(encoding="utf-8").splitlines()
                  if s.strip() and not s.strip().startswith("#")]
    if not cases:
        ap.error("no case folders")
    cache = a.mesh_cache or Path(tempfile.gettempdir()) / "outrigger_render_case_cache"
    cache.mkdir(parents=True, exist_ok=True)
    parts, stats = cadr.load_coloured_parts(cache, cell_m=CELL_M)
    key = hashlib.sha256(str(stats).encode()).hexdigest()[:10]
    parts_pickle = cache / f"case_parts_{key}.pkl"
    if not parts_pickle.exists():
        with open(parts_pickle, "wb") as h:
            pickle.dump({"parts": parts}, h, protocol=5)
    _worker_init(str(parts_pickle))
    entries = []
    t0 = time.perf_counter()
    pool = None
    try:
        if a.jobs > 1 and not a.dry:
            from multiprocessing import get_context

            pool = get_context("spawn").Pool(a.jobs, initializer=_worker_init, initargs=(str(parts_pickle),))
        for cd in cases:
            info = render_case(Path(cd), a, parts, parts_pickle, pool)
            entries.append(info)
            print(json.dumps({k: info.get(k) for k in ("case", "frames", "window_s", "gif", "mp4", "timing_s")},
                             ensure_ascii=False, default=str), flush=True)
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    if a.dry:
        print(json.dumps(entries, ensure_ascii=False, indent=1, default=str))
        return
    run = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "argv": sys.argv[1:], "jobs": a.jobs,
           "wall_s": time.perf_counter() - t0, "mesh": {"cell_m": CELL_M, "faces_drawn": stats.get("faces_drawn")}}
    by_dir: dict[Path, list[dict]] = {}
    for e in entries:
        d = a.out_dir or STAGE_DIRS[e["kind"]]
        by_dir.setdefault(d, []).append(e)
    for d, es in by_dir.items():
        merge_meta(d / f"{es[0]['kind'] if a.out_dir is None else 'custom'}_case_gifs.json", es, run)


if __name__ == "__main__":
    main()
