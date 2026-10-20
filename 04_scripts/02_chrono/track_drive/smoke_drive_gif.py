"""Smoke test GIF: a Chrono example tracked vehicle (M113 JSON template) driven in the project's
Chrono system. This is NOT the REXOME33 crawler model (see 00_docs/03_chrono/track_drive_plan.md).

What it checks (API smoke test, not a physics verdict):
  * ``pychrono.vehicle.TrackedVehicle(system, json)`` builds inside the project system from
    ``outrigger_sim.chrono.system.make_system`` (L2b_NSC: ChSystemNSC, gravity from the YAML
    stated explicitly (R1), Bullet collision (R2), PSOR iterations from the YAML),
  * an edited copy of the M113 single-pin JSON templates loads (shoe pitch 0.1732 m = REXOME
    CAD pitch, sprocket 11 teeth with the gear profile scaled to that pitch),
  * the sprockets driven by ``ChSprocket.ApplyAxleTorque`` move the vehicle forward and back.

Scenario (vehicle frame of Chrono Vehicle: x forward, y left, z up; ground plane z = 0):
  0.0-0.5 s settle (no torque), 0.5-1.5 s forward torque, 1.5-2.5 s reverse torque.
  The torque sign that drives +x is not assumed: a 0.3 s pre-run measures it (sign trap,
  track_drive_plan.md 1.1) and the frames show it.

Outputs:
  * 06_analysis/01_chrono/track_drive_smoke.gif   (git-ignored, regenerate with this script)
  * 06_analysis/01_chrono/track_drive_smoke.json  (summary, tracked)
  * 07_results/track_drive_smoke/                  (edited JSON copy, frames; git-ignored)

Usage (project root, Chrono-dev interpreter, about 2-4 min):
  C:\\ProgramData\\miniforge3\\envs\\Chrono-dev\\python.exe -I -u
      04_scripts/02_chrono/track_drive/smoke_drive_gif.py
"""

from __future__ import annotations

import json
import math
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, Polygon  # noqa: E402
from PIL import Image  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "03_src"
if str(SRC_DIR) not in sys.path:  # python -I: 03_src is not on sys.path
    sys.path.insert(0, str(SRC_DIR))

import pychrono as ch  # noqa: E402
import pychrono.vehicle as veh  # noqa: E402

from outrigger_sim.chrono.system import make_system  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

ANALYSIS_DIR = PROJECT_ROOT / "06_analysis" / "01_chrono"
GIF_PATH = ANALYSIS_DIR / "track_drive_smoke.gif"
SUMMARY_PATH = ANALYSIS_DIR / "track_drive_smoke.json"
WORK_DIR = PROJECT_ROOT / "07_results" / "track_drive_smoke"
VEHICLE_DATA_DIR = WORK_DIR / "vehicle_data"
"""Edited copy of the M113 JSON templates (the pychrono data folder is never modified)."""

CHRONO_VEHICLE_DATA = Path(ch.GetChronoDataPath()) / "vehicle"
M113_FILES = {
    "vehicle": "M113/vehicle/M113_Vehicle_SinglePin.json",
    "chassis": "M113/chassis/M113_Chassis.json",
    "driveline": "M113/driveline/M113_SimpleTrackDriveline.json",
    "brake": "M113/brake/M113_TrackBrakeSimple.json",
    "shoe": "M113/track_shoe/M113_TrackShoeSinglePin.json",
}
SIDES = ("Left", "Right")
SIDE_FILES = (
    "M113/track_assembly/M113_TrackAssemblySinglePin_{side}.json",
    "M113/sprocket/M113_SprocketSinglePin_{side}.json",
    "M113/idler/M113_DoubleIdler_{side}.json",
    "M113/idler_wheel/M113_DoubleIdlerWheel_{side}.json",
    "M113/suspension/M113_TranslationalDamperSuspension_{side}.json",
    "M113/road_wheel/M113_DoubleRoadWheel_{side}.json",
)

# --- template edit (M113 -> pitch 0.1732 m, 11 teeth) ------------------------------------
M113_PITCH_M = 0.154
NEW_PITCH_M = 0.1732  # REXOME CAD shoe pitch (crawler_summary.json shoe_pitch)
M113_TEETH = 10
NEW_TEETH = 11
NEW_SHOES = {"Left": 58, "Right": 59}
"""Smallest counts without a Chrono warning (57 / 58 printed "Insufficient number of track
shoes", missing 0.116 m); M113 uses 63 / 64 x 0.154 m."""

# --- scenario -----------------------------------------------------------------------------
DT_S = 5.0e-4  # Chrono Vehicle tracked-vehicle demo practice; smoke test only
T_SETTLE_S = 0.5
T_FORWARD_END_S = 1.5
T_END_S = 2.5
TORQUE_N_M = 4000.0  # per sprocket, magnitude
PRE_RUN_S = 0.3  # sign probe: torque from t = 0.1 s
INIT_HEIGHT_M = 1.1  # chassis reference height at start (M113 demo value)
GROUND_FRICTION = 0.8  # M113 shoe material value (Chrono example), not a REXOME assumption
FRAME_EVERY_S = 0.02
GIF_FRAME_MS = 60
FIG_SIZE_IN = (11.0, 7.4)
FIG_DPI = 100


def strip_comments(text: str) -> str:
    """Remove full-line ``//`` comments (Chrono JSON files carry them)."""
    return re.sub(r"(?m)^\s*//.*$", "", text)


def read_json(path: Path) -> dict:
    return json.loads(strip_comments(path.read_text(encoding="utf-8")))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def ideal_assembly_radius(pitch: float, teeth: int) -> float:
    """Pin-circle radius of a single-pin chain: p / (2 sin(pi / N))."""
    return pitch / (2.0 * math.sin(math.pi / teeth))


def build_edited_templates() -> dict:
    """Copy the M113 single-pin templates and set pitch 0.1732 m and 11 sprocket teeth.

    Shoe: pitch, sprocket-contact cylinder offsets, guide pin and collision box lengths along
    the track are scaled by k = 0.1732 / 0.154; shoe mass and inertia are kept (M113 values).
    Sprocket: assembly, addendum and arc-centre radii are scaled by s so that the assembly
    radius keeps M113's ratio to the ideal pin circle; the gap arc radius is scaled by k.
    """
    if VEHICLE_DATA_DIR.exists():
        shutil.rmtree(VEHICLE_DATA_DIR)
    for rel in M113_FILES.values():
        write_json(VEHICLE_DATA_DIR / rel, read_json(CHRONO_VEHICLE_DATA / rel))
    for side in SIDES:
        for pattern in SIDE_FILES:
            rel = pattern.format(side=side)
            write_json(VEHICLE_DATA_DIR / rel, read_json(CHRONO_VEHICLE_DATA / rel))

    k = NEW_PITCH_M / M113_PITCH_M
    shoe_path = VEHICLE_DATA_DIR / M113_FILES["shoe"]
    shoe = read_json(shoe_path)
    shoe["Shoe"]["Pitch"] = NEW_PITCH_M
    cyl = shoe["Contact"]["Cylinder Shape"]
    cyl["Front Offset"] *= k
    cyl["Rear Offset"] *= k
    shoe["Guide Pin Center"][0] *= k
    for shape in shoe["Contact"]["Shoe Shapes"]:
        shape["Location"][0] *= k
        shape["Dimensions"][0] *= k
    shoe.pop("Visualization", None)
    write_json(shoe_path, shoe)

    m113_ideal = ideal_assembly_radius(M113_PITCH_M, M113_TEETH)
    new_ideal = ideal_assembly_radius(NEW_PITCH_M, NEW_TEETH)
    profiles = {}
    for side in SIDES:
        sp_path = VEHICLE_DATA_DIR / f"M113/sprocket/M113_SprocketSinglePin_{side}.json"
        sp = read_json(sp_path)
        prof = sp["Profile"]
        s = (prof["Assembly Radius"] / m113_ideal) * new_ideal / prof["Assembly Radius"]
        sp["Number Teeth"] = NEW_TEETH
        prof["Assembly Radius"] *= s
        prof["Addendum Radius"] *= s
        prof["Arc Centers Radius"] *= s
        prof["Arc Radius"] *= k
        sp.pop("Visualization", None)
        write_json(sp_path, sp)
        profiles[side] = dict(prof, scale=s)
        ta_path = VEHICLE_DATA_DIR / f"M113/track_assembly/M113_TrackAssemblySinglePin_{side}.json"
        ta = read_json(ta_path)
        ta["Track Shoes"]["Number Shoes"] = NEW_SHOES[side]
        write_json(ta_path, ta)
    for side in SIDES:  # visualization meshes are not used (off-screen frames)
        for rel in (
            f"M113/idler_wheel/M113_DoubleIdlerWheel_{side}.json",
            f"M113/road_wheel/M113_DoubleRoadWheel_{side}.json",
        ):
            data = read_json(VEHICLE_DATA_DIR / rel)
            data.pop("Visualization", None)
            write_json(VEHICLE_DATA_DIR / rel, data)
    chassis = read_json(VEHICLE_DATA_DIR / M113_FILES["chassis"])
    chassis.pop("Visualization", None)
    write_json(VEHICLE_DATA_DIR / M113_FILES["chassis"], chassis)
    return {"pitch_scale_k": k, "sprocket_profile_left": profiles["Left"]}


# --- model ----------------------------------------------------------------------------------
@dataclass
class Model:
    system: ch.ChSystem
    vehicle: veh.TrackedVehicle
    terrain: veh.RigidTerrain
    dt_s: float
    meta: dict = field(default_factory=dict)


def build_model() -> Model:
    params = load_params()
    bundle = make_system(params, "L2b_NSC", dt=DT_S, floor_plate=False)
    system = bundle.system
    veh.SetVehicleDataPath(str(VEHICLE_DATA_DIR) + "/")
    vehicle = veh.TrackedVehicle(system, veh.GetVehicleDataFile(M113_FILES["vehicle"]))
    vehicle.Initialize(ch.ChCoordsysd(ch.ChVector3d(0, 0, INIT_HEIGHT_M), ch.QUNIT))
    vehicle.DisconnectDriveline()  # each sprocket gets its own axle torque (hydraulic motor)
    material = ch.ChContactMaterialNSC()
    material.SetFriction(GROUND_FRICTION)
    terrain = veh.RigidTerrain(system)
    terrain.AddPatch(material, ch.ChCoordsysd(ch.ChVector3d(0, 0, 0), ch.QUNIT), 60.0, 20.0)
    terrain.Initialize()
    gravity = system.GetGravitationalAcceleration()
    meta = {
        "system": type(system).__name__,
        "gravity_m_s2": [gravity.x, gravity.y, gravity.z],
        "collision_system": "BULLET",
        "solver": bundle.meta().get("solver"),
        "dt_s": bundle.dt_s,
    }
    return Model(system, vehicle, terrain, bundle.dt_s, meta)


def step(model: Model, torque_n_m: float) -> None:
    t = model.system.GetChTime()
    inputs = veh.DriverInputs()
    model.terrain.Synchronize(t)
    model.vehicle.Synchronize(t, inputs, model.terrain)
    for side in (veh.LEFT, veh.RIGHT):
        model.vehicle.GetTrackAssembly(side).GetSprocket().ApplyAxleTorque(torque_n_m)
    model.terrain.Advance(model.dt_s)
    model.vehicle.Advance(model.dt_s)
    model.system.DoStepDynamics(model.dt_s)


def vec(v) -> np.ndarray:
    """Copy a Chrono vector now (GetPos() returns a reference, R9)."""
    return np.array([v.x, v.y, v.z], dtype=float)


def rot_matrix(body) -> np.ndarray:
    q = body.GetRot()
    w, x, y, z = q.e0, q.e1, q.e2, q.e3
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ]
    )


def snapshot(model: Model, torque: float) -> dict:
    """State of the left track and the chassis (side view)."""
    v = model.vehicle
    ta = v.GetTrackAssembly(veh.LEFT)
    sp = ta.GetSprocket()
    gear = sp.GetGearBody()
    chassis = v.GetChassisBody()
    shoes = []
    for i in range(ta.GetNumTrackShoes()):
        body = ta.GetTrackShoe(i).GetShoeBody()
        shoes.append((vec(body.GetPos()), rot_matrix(body)))
    wheels = []
    idler = ta.GetIdler()
    wheels.append(
        (
            "idler",
            vec(idler.GetWheelBody().GetPos()),
            rot_matrix(idler.GetWheelBody()),
            idler.GetWheelRadius(),
        )
    )
    for i in range(ta.GetNumTrackSuspensions()):
        susp = ta.GetTrackSuspension(i)
        body = susp.GetWheelBody()
        wheels.append(("road", vec(body.GetPos()), rot_matrix(body), susp.GetWheelRadius()))
    omega_world = vec(gear.GetAngVelParent())
    return {
        "t": model.system.GetChTime(),
        "torque": torque,
        "axle_speed": sp.GetAxleSpeed(),
        "gear_omega_y": float(omega_world[1]),
        "gear_pos": vec(gear.GetPos()),
        "gear_R": rot_matrix(gear),
        "chassis_pos": vec(chassis.GetPos()),
        "ref_pos": vec(chassis.GetFrameRefToAbs().GetPos()),
        "chassis_R": rot_matrix(chassis),
        "chassis_vel": vec(chassis.GetPosDt()),
        "shoes": shoes,
        "wheels": wheels,
    }


def probe_forward_sign() -> dict:
    """0.3 s run with +T from t = 0.1 s: which torque sign moves the vehicle to +x?"""
    model = build_model()
    x0 = vec(model.vehicle.GetChassisBody().GetPos())[0]
    n = round(PRE_RUN_S / model.dt_s)
    for _ in range(n):
        torque = TORQUE_N_M if model.system.GetChTime() >= 0.1 else 0.0
        step(model, torque)
    snap = snapshot(model, TORQUE_N_M)
    dx = snap["chassis_pos"][0] - x0
    return {
        "applied_torque_n_m": TORQUE_N_M,
        "dx_m": dx,
        "vx_m_s": snap["chassis_vel"][0],
        "axle_speed_rad_s": snap["axle_speed"],
        "gear_omega_world_y_rad_s": snap["gear_omega_y"],
        "forward_torque_sign": 1.0 if snap["chassis_vel"][0] > 0 else -1.0,
    }


def run_scenario(forward_sign: float) -> tuple[list[dict], dict]:
    model = build_model()
    ta = model.vehicle.GetTrackAssembly(veh.LEFT)
    info = {
        "num_shoes_left": int(ta.GetNumTrackShoes()),
        "num_shoes_right": int(model.vehicle.GetTrackAssembly(veh.RIGHT).GetNumTrackShoes()),
        "pitch_m": ta.GetTrackShoe(0).GetPitch(),
        "teeth": int(ta.GetSprocket().GetNumTeeth()),
        "assembly_radius_m": ta.GetSprocket().GetAssemblyRadius(),
        "addendum_radius_m": ta.GetSprocket().GetAddendumRadius(),
        "num_road_wheels_left": int(ta.GetNumTrackSuspensions()),
        **model.meta,
    }
    n = round(T_END_S / model.dt_s)
    every = round(FRAME_EVERY_S / model.dt_s)
    frames = []
    wall0 = time.perf_counter()
    for i in range(n + 1):
        t = model.system.GetChTime()
        if t < T_SETTLE_S - 1e-9:
            torque = 0.0
        elif t < T_FORWARD_END_S - 1e-9:
            torque = forward_sign * TORQUE_N_M
        else:
            torque = -forward_sign * TORQUE_N_M
        if i % every == 0:
            frames.append(snapshot(model, torque))
        if i < n:
            step(model, torque)
    info["wall_s"] = time.perf_counter() - wall0
    info["ms_per_step"] = info["wall_s"] / n * 1e3
    info["steps"] = n
    return frames, info


# --- drawing --------------------------------------------------------------------------------
HULL_LOCAL = np.array(  # schematic M113-like hull outline in the chassis frame (x, z) [m]
    [(0.35, 0.15), (0.0, 0.85), (-4.55, 0.85), (-4.85, 0.35), (-4.55, 0.0), (0.05, 0.0)]
)
SHOE_HALF_HEIGHT_M = 0.03
COLORS = {
    "shoe": "#5b6573",
    "shoe_mark": "#e8590c",
    "sprocket": "#1c7ed6",
    "idler": "#2f9e44",
    "road": "#868e96",
    "hull": "#adb5bd",
    "ground": "#495057",
}


def xz(p: np.ndarray) -> tuple[float, float]:
    return float(p[0]), float(p[2])


def body_angle_y(R: np.ndarray) -> float:
    """Rotation angle about +y (side view, positive = x toward -z... right-hand about +y)."""
    return math.atan2(R[0, 2], R[0, 0])


def sprocket_outline(prof: dict, teeth: int, phase: float) -> np.ndarray:
    """Gear profile in the gear plane: addendum circle cut by the gap arcs (polar ray test)."""
    ra, rc, rg = prof["Addendum Radius"], prof["Arc Centers Radius"], prof["Arc Radius"]
    th = np.linspace(0, 2 * math.pi, 720, endpoint=False)
    r = np.full_like(th, ra)
    for k in range(teeth):
        alpha = th - (phase + 2 * math.pi * k / teeth)
        alpha = (alpha + math.pi) % (2 * math.pi) - math.pi
        disc = rg * rg - (rc * np.sin(alpha)) ** 2
        hit = (disc > 0) & (np.cos(alpha) > 0)
        near = rc * np.cos(alpha) - np.sqrt(np.where(disc > 0, disc, 0))
        r = np.where(hit & (near < r), near, r)
    return np.c_[r * np.cos(th), r * np.sin(th)]


def gap_phase(frame: dict, prof: dict, teeth: int) -> float:
    """Phase of the gap centres in the gear frame from the shoes wrapped on the sprocket."""
    c = frame["gear_pos"]
    beta = body_angle_y(frame["gear_R"])
    angles = []
    for pos, _ in frame["shoes"]:
        d = np.array([pos[0] - c[0], pos[2] - c[2]])
        if abs(np.hypot(*d) - prof["Assembly Radius"]) < 0.08:
            angles.append(math.atan2(d[1], d[0]) + beta)
    if not angles:
        return 0.0
    pitch_angle = 2 * math.pi / teeth
    z = np.mean(np.exp(1j * np.array(angles) * teeth))
    return float(np.angle(z) / teeth) % pitch_angle


def draw_frame(ax_scene, ax_text, ax_plot, frame, series, ctx) -> None:
    ax_scene.clear()
    ax_text.clear()
    ax_text.axis("off")
    x_centre = ctx["x_view_centre"]
    ax_scene.set_xlim(x_centre - 3.9, x_centre + 3.9)
    ax_scene.set_ylim(-0.25, 2.05)
    ax_scene.set_aspect("equal")
    ax_scene.set_xlabel("x [m] (Chrono Vehicle frame, forward +x)")
    ax_scene.set_ylabel("z [m]")
    # ground with tick marks (motion reference)
    ax_scene.fill_between([-20, 20], -0.25, 0, color="#e9ecef", zorder=0)
    ax_scene.axhline(0, color=COLORS["ground"], lw=1.2, zorder=1)
    for gx in np.arange(-10, 10.01, 0.5):
        ax_scene.plot([gx, gx - 0.08], [0, -0.08], color=COLORS["ground"], lw=0.8, zorder=1)
    # hull (schematic)
    Rc, pc = frame["chassis_R"], frame["ref_pos"]
    hull = [xz(pc + Rc @ np.array([hx, 0.0, hz])) for hx, hz in HULL_LOCAL]
    ax_scene.add_patch(
        Polygon(hull, closed=True, fc=COLORS["hull"], ec="#495057", lw=1.0, alpha=0.55, zorder=2)
    )
    ax_scene.plot(*xz(frame["chassis_pos"]), marker="+", color="k", ms=8, zorder=6)
    ax_scene.text(*xz(frame["chassis_pos"]), "  COM", fontsize=8, va="center", zorder=6)
    # wheels
    for kind, pos, R, radius in frame["wheels"]:
        color = COLORS["idler"] if kind == "idler" else COLORS["road"]
        ax_scene.add_patch(Circle(xz(pos), radius, fc="white", ec=color, lw=1.6, zorder=3))
        beta = body_angle_y(R)
        x0, z0 = xz(pos)
        ax_scene.plot(
            [x0, x0 + 0.85 * radius * math.cos(beta)],
            [z0, z0 - 0.85 * radius * math.sin(beta)],
            color=color,
            lw=1.4,
            zorder=3,
        )
    # sprocket (gear profile rotated with the gear body)
    beta = body_angle_y(frame["gear_R"])
    prof = ctx["profile"]
    outline = ctx["sprocket_local"]
    cb, sb = math.cos(beta), math.sin(beta)
    gx, gz = xz(frame["gear_pos"])
    pts = np.c_[
        gx + outline[:, 0] * cb - outline[:, 1] * sb, gz - (outline[:, 0] * sb + outline[:, 1] * cb)
    ]
    ax_scene.add_patch(
        Polygon(pts, closed=True, fc="#d0ebff", ec=COLORS["sprocket"], lw=1.4, zorder=4)
    )
    ax_scene.plot(
        [gx, gx + 0.8 * prof["Addendum Radius"] * cb],
        [gz, gz - 0.8 * prof["Addendum Radius"] * sb],
        color=COLORS["sprocket"],
        lw=2.0,
        zorder=4,
    )
    # shoes (left track)
    half_p = ctx["pitch"] / 2
    corners = np.array(
        [
            [-half_p, 0, -SHOE_HALF_HEIGHT_M],
            [half_p, 0, -SHOE_HALF_HEIGHT_M],
            [half_p, 0, SHOE_HALF_HEIGHT_M],
            [-half_p, 0, SHOE_HALF_HEIGHT_M],
        ]
    )
    for i, (pos, R) in enumerate(frame["shoes"]):
        poly = [xz(pos + R @ c) for c in corners]
        marked = i == 0
        ax_scene.add_patch(
            Polygon(
                poly,
                closed=True,
                fc=COLORS["shoe_mark"] if marked else COLORS["shoe"],
                ec="white",
                lw=0.4,
                zorder=5,
            )
        )
    ax_scene.text(
        0.01,
        0.98,
        "left track, side view (seen from +y); orange = shoe #0",
        transform=ax_scene.transAxes,
        va="top",
        fontsize=8.5,
        color="#343a40",
    )
    ax_scene.text(
        0.99,
        0.98,
        "hull outline schematic",
        transform=ax_scene.transAxes,
        va="top",
        ha="right",
        fontsize=8,
        color="#868e96",
    )

    # text panel
    vx = frame["chassis_vel"][0]
    chain = frame["gear_omega_y"] * ctx["r_eff"]
    slip = slip_ratio(chain, vx)
    phase = (
        "settle (T = 0)"
        if frame["t"] < T_SETTLE_S - 1e-9
        else ("forward torque" if frame["t"] < T_FORWARD_END_S - 1e-9 else "reverse torque")
    )
    lines = [
        f"t = {frame['t']:5.2f} s   phase: {phase}",
        f"ApplyAxleTorque(T), each sprocket: T = {frame['torque']:+6.0f} N m",
        f"sprocket GetAxleSpeed() = {frame['axle_speed']:+6.2f} rad/s",
        f"sprocket omega about world +y = {frame['gear_omega_y']:+6.2f} rad/s",
        f"chassis x = {frame['chassis_pos'][0] - ctx['x0']:+6.3f} m   vx = {vx:+6.3f} m/s",
        f"omega_y r_eff = {chain:+6.3f} m/s (r_eff = Np/2pi = {ctx['r_eff']:.4f} m)",
        f"slip s = (omega_y r_eff - vx) / max = {slip:+6.3f}",
        "",
        f"SIGN TRAP (measured): ApplyAxleTorque({ctx['fwd_sign']:+.0f}) -> +x travel,",
        f"  GetAxleSpeed {ctx['axle_sign_fwd']:+.0f}, world omega_y {ctx['omega_sign_fwd']:+.0f}"
        " while moving +x",
    ]
    ax_text.text(0.0, 1.0, "\n".join(lines), va="top", family="monospace", fontsize=8.6)

    # time series
    ax_plot.clear()
    ts, vxs, chains = series["t"], series["vx"], series["chain"]
    ax_plot.plot(ts, vxs, color="#1c7ed6", lw=1.6, label="chassis vx [m/s]")
    ax_plot.plot(ts, chains, color="#e8590c", lw=1.2, ls="--", label="omega_y r_eff [m/s]")
    ax_plot.axvspan(T_SETTLE_S, T_FORWARD_END_S, color="#d3f9d8", alpha=0.6, lw=0)
    ax_plot.axvspan(T_FORWARD_END_S, T_END_S, color="#ffe3e3", alpha=0.6, lw=0)
    ax_plot.axvline(frame["t"], color="k", lw=1.0)
    ax_plot.axhline(0, color="#adb5bd", lw=0.8)
    ax_plot.set_xlim(0, T_END_S)
    lim = 1.1 * max(1e-3, np.max(np.abs(np.r_[vxs, chains])))
    ax_plot.set_ylim(-lim, lim)
    ax_plot.set_xlabel("t [s]  (green: forward torque, red: reverse torque)")
    ax_plot.set_ylabel("speed [m/s]")
    ax_plot.legend(loc="upper left", fontsize=8, frameon=False)
    ax_plot.grid(alpha=0.3)


def slip_ratio(chain: float, vx: float) -> float:
    den = max(abs(chain), abs(vx))
    return 0.0 if den < 0.05 else (chain - vx) / den


def render_gif(frames: list[dict], info: dict, sign_probe: dict, profile: dict) -> int:
    frames_dir = WORK_DIR / "frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)
    teeth = info["teeth"]
    r_eff = teeth * info["pitch_m"] / (2 * math.pi)
    fwd_frames = [f for f in frames if T_SETTLE_S + 0.3 < f["t"] < T_FORWARD_END_S]
    ref = fwd_frames[-1]
    ctx = {
        "profile": profile,
        "pitch": info["pitch_m"],
        "r_eff": r_eff,
        "x0": frames[0]["chassis_pos"][0],
        "fwd_sign": sign_probe["forward_torque_sign"],
        "axle_sign_fwd": math.copysign(1, ref["axle_speed"]),
        "omega_sign_fwd": math.copysign(1, ref["gear_omega_y"]),
    }
    ctx["sprocket_local"] = sprocket_outline(profile, teeth, gap_phase(frames[0], profile, teeth))
    xs = [f["ref_pos"][0] for f in frames]
    ctx["x_view_centre"] = 0.5 * (min(xs) + max(xs)) - 2.15
    series = {
        "t": np.array([f["t"] for f in frames]),
        "vx": np.array([f["chassis_vel"][0] for f in frames]),
        "chain": np.array([f["gear_omega_y"] * r_eff for f in frames]),
    }
    fig = plt.figure(figsize=FIG_SIZE_IN, dpi=FIG_DPI)
    grid = fig.add_gridspec(
        2,
        2,
        height_ratios=[2.2, 1.0],
        width_ratios=[1.3, 1.0],
        hspace=0.32,
        wspace=0.12,
        left=0.06,
        right=0.98,
        top=0.88,
        bottom=0.08,
    )
    ax_scene = fig.add_subplot(grid[0, :])
    ax_plot = fig.add_subplot(grid[1, 0])
    ax_text = fig.add_subplot(grid[1, 1])
    fig.suptitle(
        "SMOKE TEST - Chrono example tracked vehicle (M113 single-pin JSON, edited copy: "
        f"pitch {info['pitch_m']:.4f} m, {teeth} teeth)\n"
        "NOT the REXOME33 crawler model | project ChSystem: "
        f"{info['system']}, g = {info['gravity_m_s2'][2]:.5f} m/s^2, Bullet, "
        f"PSOR, dt {info['dt_s']:.0e} s",
        fontsize=10.5,
        fontweight="bold",
    )
    images = []
    for k, frame in enumerate(frames):
        mask = series["t"] <= frame["t"] + 1e-9
        sub = {key: val[mask] for key, val in series.items()}
        draw_frame(ax_scene, ax_text, ax_plot, frame, sub, ctx)
        out = frames_dir / f"frame_{k:04d}.png"
        fig.savefig(out)
        images.append(Image.open(out).convert("RGB"))
    plt.close(fig)
    palette_src = images[len(images) // 2].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    quantized = [im.quantize(palette=palette_src, dither=Image.Dither.NONE) for im in images]
    durations = [GIF_FRAME_MS] * len(quantized)
    durations[-1] = 1500
    GIF_PATH.parent.mkdir(parents=True, exist_ok=True)
    quantized[0].save(
        GIF_PATH,
        save_all=True,
        append_images=quantized[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    return len(quantized)


def main() -> None:
    t0 = time.perf_counter()
    edit = build_edited_templates()
    print(f"templates written to {VEHICLE_DATA_DIR}", flush=True)
    sign_probe = probe_forward_sign()
    print(f"sign probe: {sign_probe}", flush=True)
    frames, info = run_scenario(sign_probe["forward_torque_sign"])
    print(f"scenario: {info['steps']} steps, {info['ms_per_step']:.2f} ms/step", flush=True)
    profile = edit["sprocket_profile_left"]
    n_frames = render_gif(frames, info, sign_probe, profile)
    r_eff = info["teeth"] * info["pitch_m"] / (2 * math.pi)

    def at(t_query: float) -> dict:
        return min(frames, key=lambda f: abs(f["t"] - t_query))

    checkpoints = {}
    for label, tq in (
        ("end_settle", T_SETTLE_S),
        ("end_forward", T_FORWARD_END_S),
        ("end", T_END_S),
    ):
        f = at(tq)
        chain = f["gear_omega_y"] * r_eff
        checkpoints[label] = {
            "t_s": f["t"],
            "chassis_dx_m": f["chassis_pos"][0] - frames[0]["chassis_pos"][0],
            "chassis_vx_m_s": f["chassis_vel"][0],
            "chassis_z_m": f["chassis_pos"][2],
            "sprocket_axle_speed_rad_s": f["axle_speed"],
            "sprocket_omega_world_y_rad_s": f["gear_omega_y"],
            "chain_speed_omega_y_r_eff_m_s": chain,
            "slip_ratio": slip_ratio(chain, f["chassis_vel"][0]),
        }
    window = [f for f in frames if 1.0 <= f["t"] < T_FORWARD_END_S - 1e-9]
    chain_w = np.array([f["gear_omega_y"] * r_eff for f in window])
    vx_w = np.array([f["chassis_vel"][0] for f in window])
    checkpoints["forward_window_1.0_1.5_s_mean"] = {
        "chassis_vx_m_s": float(vx_w.mean()),
        "chain_speed_omega_y_r_eff_m_s": float(chain_w.mean()),
        "slip_ratio_of_means": slip_ratio(float(chain_w.mean()), float(vx_w.mean())),
        "frames": len(window),
    }
    summary = {
        "what": "Smoke test: Chrono example tracked vehicle (M113 single-pin JSON templates, "
        "edited copy) in the project Chrono system; NOT the REXOME33 crawler model",
        "plan": "00_docs/03_chrono/track_drive_plan.md (section 10)",
        "script": "04_scripts/02_chrono/track_drive/smoke_drive_gif.py",
        "gif": str(GIF_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "gif_frames": n_frames,
        "pychrono_version": getattr(ch, "__version__", "10.0.0"),
        "vehicle_data": {
            "source": "Chrono data vehicle/M113 (pychrono 10.0.0 install), copied and edited "
            "to 07_results/track_drive_smoke/vehicle_data (source not modified)",
            "edits": f"shoe pitch 0.154 -> {NEW_PITCH_M} m (cylinder offsets, guide pin, box "
            "lengths x k), sprocket teeth 10 -> 11 (assembly/addendum/arc-centre "
            "radius x s, arc radius x k), shoes 63/64 -> "
            f"{NEW_SHOES['Left']}/{NEW_SHOES['Right']}; shoe mass/inertia unchanged",
            "pitch_scale_k": edit["pitch_scale_k"],
            "sprocket_profile_left": profile,
        },
        "scenario": {
            "settle_s": [0.0, T_SETTLE_S],
            "forward_torque_s": [T_SETTLE_S, T_FORWARD_END_S],
            "reverse_torque_s": [T_FORWARD_END_S, T_END_S],
            "torque_per_sprocket_n_m": TORQUE_N_M,
            "drive": "ChSprocket.ApplyAxleTorque each step, driveline disconnected",
            "ground": "RigidTerrain plane z = 0, NSC friction "
            f"{GROUND_FRICTION} (M113 example value)",
        },
        "model": info,
        "r_eff_m": r_eff,
        "sign_probe": sign_probe,
        "checkpoints": checkpoints,
        "wall_total_s": time.perf_counter() - t0,
        "note": "API smoke test only; no physics verdict (no static-equilibrium, slip or "
        "energy judgement).",
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print(json.dumps(checkpoints, indent=1), flush=True)
    print(f"gif {GIF_PATH} ({n_frames} frames), summary {SUMMARY_PATH}", flush=True)


if __name__ == "__main__":
    main()
