"""S9 C2 soil response: reduced closed loop of the project C2 on Bekker soil pads (spec rev. 57).

Harness (as 04_scripts/03_control/s8/r51_reapp_closed_loop.py, not imported because that file reads argv at import):
  reduced 6-DoF FlexPlant (rigid mast) + dynamics rev. 39 L1-R rod-side law (s8_g4_rodside_check.RodSidePlant,
  armed after the crawler settle), Coulomb seal friction per leg, valve first-order lag 0.1 s (exact chunk mean,
  1 ms chunks), leg damping switch locked / moving, IMU 10 ms samples, the project C2 (03_src, read only) with
  c2py_r8d1_closed_loop.preset_config(COMBINED) = with_10hz_d1 minus CHECK / zero calibration / REANCHOR / target
  check. Ideal sensors unless a sensor-error case is given (force error per leg, see SensorError).

Soil (new here): every pad sits on one Chrono-type SCM element (dynamics_model.md 5.31.2 / 5.32.3, the P0 law plus
  the damping R that P0 left out), solved implicitly once per 1 ms chunk:
      k_s (pen - z) = A (sigma_s(z) + R (z - z_prev) / h)
      sigma_s = 0 (z <= s_p), K (z - s_p) (z <= z_y = s_p + sigma_y / K), (k_c / b + k_phi) z^n (z > z_y)
      on the loading branch sigma_y = (k_c / b + k_phi) z^n, s_p = z - sigma_y / K  (plastic memory)
  k_s = series(k_rod, k_frame) (the concrete slab of the rigid-floor harness removed), pen = rod penetration of the
  original soil surface. The harness kernel sees the deformed surface through plant.goff.
  Crawler: the harness crawler (concrete compliance, YAML kn_total) on a floor tilted by the soil-minus-rigid settle
  pitch of P0 (pad_bekker_p0_soilsets.json, 'settle'), the pad surfaces offset so that body-to-surface heights at the
  pads match the P0 soil settle (h_i = (uz_rigid - uz_soil) + x_i tan(dtheta)). Crawler soil plasticity during the
  lift is not modelled (the crawler only unloads; its elastic rebound is the harness concrete spring).
Settle hook (make_plant ``settle_hook``, else environment S9_SETTLE_HOOK, default "p0"):
  "p0"      the flat P0 soil-minus-rigid settle above (every result up to rev. 79). Biased: the harness rigid crawler
            settles at pitch 0.179 deg, P0 rigid at 0.289 deg, so a soil case sits 0.11 deg less nose down and the
            front pad gaps are 8..9 mm off the P0 soil settle.
  "harness" dynamics row hook_harness["{soil}|{level}|{roll:g}|{pitch:g}"] of S9_SETTLE_TABLE (default
            06_analysis/00_dynamics/slope_crawler_settle.json), calibrated on the harness's own rigid crawler: the floor
            tilt add (floor_roll_add_deg, floor_pitch_add_deg) replaces the P0 pitch add, SoilPads.h = pad_h_m. A soil
            case without a row raises KeyError. Rigid floors are the table reference (no change).
Pads: 02_params/pad_variants.json type A (cad330) / B (dwg_rear250): area and Bekker b per leg; masses unchanged
  (U-PAD-3).
Non-planar start (spec 426.7 B, optional case key ``pad_start_gap``): after the crawler settle one
  pad's floor is moved to a target zero-stroke gap (``apply_pad_start_gap``); without the key
  ``run_case`` does nothing new (same commands bit for bit).
Units SI. Frames: body x fwd, y left, z up; pitch > 0 nose down.
Run (dynamics-dev, numba): python -I s9_soil_closed_loop.py <out_json> [workers] [case filter]
Deterministic except the optional seeded sensor noise (seed per case, recorded).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMBA_NUM_THREADS", "1")

import numba as nb  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _p in (ROOT / "03_src", ROOT / "04_scripts" / "03_control" / "r8d1", ROOT / "04_scripts" / "03_control",
           ROOT / "04_scripts" / "01_dynamics", HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

YAML_BETA = 1.0e9
LEGS = ("FL", "FR", "RL", "RR")
SOIL_SETS = json.loads((ROOT / "02_params" / "scm_soil_sets.json").read_text(encoding="utf-8"))["sets"]
PAD_VARIANTS = json.loads((ROOT / "02_params" / "pad_variants.json").read_text(encoding="utf-8"))["variants"]
P0_SETTLE = {k.split("|")[0]: v["settle"] for k, v in json.loads(
    (ROOT / "06_analysis" / "00_dynamics" / "pad_bekker_p0_soilsets.json").read_text(encoding="utf-8"))["paths"].items()
    if k.endswith("|B|closed")}
SETTLE_HOOK_ENV = "S9_SETTLE_HOOK"
SETTLE_TABLE_ENV = "S9_SETTLE_TABLE"
SETTLE_HOOK_P0 = "p0"
SETTLE_HOOK_HARNESS = "harness"
SETTLE_HOOKS = (SETTLE_HOOK_P0, SETTLE_HOOK_HARNESS)
DEFAULT_SETTLE_TABLE = ROOT / "06_analysis" / "00_dynamics" / "slope_crawler_settle.json"
SETTLE_TABLE_BLOCK = "hook_harness"
_SETTLE_TABLES: dict[Path, dict] = {}
"""hook_harness blocks read so far, per table path (one read per worker)."""
RUN_LIMIT_S = float(os.environ.get("S9_RUN_LIMIT_S", "240"))
HOLD_AFTER_READY_S = float(os.environ.get("S9_HOLD_S", "10"))
C_LOCK = np.array([34403.519, 34403.519, 30348.4527, 30348.4527])
C_MOVE = np.array([100206.065477022, 100206.065477022, 86949.0144383396, 86949.0144383396])
"""Leg damping [N s/m], locked zeta 0.03 / moving zeta 0.10 (as r51_reapp_closed_loop.py)."""


# ----------------------------------------------------------------------------------------------- soil element
@nb.njit(cache=True)
def _sigma_s(z, sp, sy, coef, n, K):
    if z <= sp:
        return 0.0
    zy = sp + sy / K
    if z <= zy:
        return K * (z - sp)
    return coef * max(z, 0.0) ** n


@nb.njit(cache=True)
def soil_tangent(z, sp, sy, coef, n, K):
    """d sigma_s / d z on the current branch (elastic K at and below the yield point)."""
    zy = sp + sy / K
    if z <= zy:
        return K
    return min(n * coef * max(z, 1e-9) ** (n - 1.0), K)


@nb.njit(cache=True)
def soil_chunk(pen, z, sp, sy, area, coef, n, K, R, ks, h, force):
    """Implicit Euler for the four pad elements (in place: z, sp, sy, force)."""
    for i in range(4):
        zp = z[i]
        lo = min(sp[i], zp) - 1e-6
        hi = max(pen[i], zp, sp[i]) + 1e-3
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            fp = ks[i] * max(pen[i] - mid, 0.0)
            g = fp - area[i] * (_sigma_s(mid, sp[i], sy[i], coef[i], n, K) + R * (mid - zp) / h)
            if g > 0.0:
                lo = mid
            else:
                hi = mid
        zn = 0.5 * (lo + hi)
        zy = sp[i] + sy[i] / K
        if zn > zy and zn > sp[i]:
            s_new = coef[i] * max(zn, 0.0) ** n
            sy[i] = s_new
            sp[i] = zn - s_new / K
        z[i] = zn
        force[i] = ks[i] * max(pen[i] - zn, 0.0)


class SoilPads:
    """Four SCM-type pad elements and the pad-surface offsets of one soil set.

    ``settle_row`` None: offsets from the flat P0 settle (settle hook "p0"); a hook_harness row: ``h = pad_h_m``."""

    def __init__(self, key: str, pad_type: str, pad_xy: np.ndarray, ks: np.ndarray, k_scale: float = 1.0,
                 settle_row: dict | None = None):
        s = SOIL_SETS[key]["chrono"]
        legs = next(v for v in PAD_VARIANTS.values() if v["label"] == pad_type)["legs"]
        self.area = np.array([legs[n]["bottom_area_m2"] for n in LEGS], float)
        b = np.array([legs[n]["bekker_b_m"] for n in LEGS], float)
        self.n = float(s["n"])
        self.coef = (s["Kc"] / b + s["Kphi"]) * k_scale
        self.K = float(max(s["elastic_K"], s["Kphi"] * k_scale))
        self.R = float(s["damping_R"])
        self.ks = np.asarray(ks, float)
        self.settle_row = settle_row
        if settle_row is None:
            st, rg = P0_SETTLE[key], P0_SETTLE["rigid"]
            self.dtheta = st["q"][2] - rg["q"][2]
            self.h = (rg["q"][0] - st["q"][0]) + pad_xy[:, 0] * math.tan(self.dtheta)
        else:
            self.dtheta = math.radians(float(settle_row["floor_pitch_add_deg"]))
            self.h = np.asarray(settle_row["pad_h_m"], float).copy()
        self.z = np.zeros(4); self.sp = np.zeros(4); self.sy = np.zeros(4); self.force = np.zeros(4)
        self.z_max_rate = np.zeros(4)


# ----------------------------------------------------------------------------------------------- settle hook
def resolve_settle_hook(settle_hook: str | None = None) -> str:
    """Settle hook of a run: the argument, else ``$S9_SETTLE_HOOK``, else "p0".

    Raises:
        ValueError: not one of ``SETTLE_HOOKS``.
    """
    hook = settle_hook or os.environ.get(SETTLE_HOOK_ENV) or SETTLE_HOOK_P0
    if hook not in SETTLE_HOOKS:
        raise ValueError(f"settle hook must be one of {SETTLE_HOOKS}, got {hook!r}")
    return hook


def settle_table_key(soil: str, level: str, slope) -> str:
    """hook_harness key of a soil, auger level and floor slope (roll, pitch) [deg]."""
    return f"{soil}|{level}|{float(slope[0]):g}|{float(slope[1]):g}"


def load_settle_row(soil: str, level: str, slope, table_path: str | Path | None = None) -> dict:
    """hook_harness row of the dynamics slope settle table.

    Args:
        soil, level, slope: soil set, auger level ("top", "middle", "bottom"), floor (roll, pitch) [deg].
        table_path: settle table; None = ``$S9_SETTLE_TABLE``, else ``DEFAULT_SETTLE_TABLE``.

    Raises:
        KeyError: the table has no row for this soil / level / slope (e.g. a level not tabled yet).
    """
    path = Path(table_path or os.environ.get(SETTLE_TABLE_ENV) or DEFAULT_SETTLE_TABLE)
    if path not in _SETTLE_TABLES:
        _SETTLE_TABLES[path] = json.loads(path.read_text(encoding="utf-8"))[SETTLE_TABLE_BLOCK]
    key = settle_table_key(soil, level, slope)
    rows = _SETTLE_TABLES[path]
    if key not in rows:
        raise KeyError(f"settle table {path} has no {SETTLE_TABLE_BLOCK} row {key!r}")
    return rows[key]


def _floor_rotation(roll_deg: float, pitch_deg: float) -> np.ndarray:
    """Floor R_f = Ry(pitch) Rx(roll) (the harness Plant convention)."""
    ph, th = math.radians(roll_deg), math.radians(pitch_deg)
    rot_x = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(ph), -math.sin(ph)], [0.0, math.sin(ph), math.cos(ph)]])
    rot_y = np.array([[math.cos(th), 0.0, math.sin(th)], [0.0, 1.0, 0.0], [-math.sin(th), 0.0, math.cos(th)]])
    return rot_y @ rot_x


def settle_snapshot(cl, plant) -> dict:
    """Settle state of a plant (read only): body attitude in the axes of the ORIGINAL floor (the case slope, without
    the hook's tilt add; ZYX of R_f^T R, deg) and the gap pad bottom to the original soil surface (soil_floor
    geometry, mm, None on a rigid floor); with a hook_harness row also the errors to its targets
    (target_q_floor phi / theta, gap_target_mm)."""
    info = getattr(plant, "settle_info", {})
    roll_deg, pitch_deg = info.get("floor_slope_deg", (0.0, 0.0))
    rotation = cl.rcc._R(plant.q)
    relative = _floor_rotation(roll_deg, pitch_deg).T @ rotation
    att_deg = [math.degrees(math.atan2(relative[2, 1], relative[2, 2])), math.degrees(-math.asin(relative[2, 0]))]
    snap = {"hook": info.get("hook"), "row_key": info.get("row_key"), "att_floor_deg": att_deg, "gap_mm": None}
    so = plant.soil
    if so is not None:
        a_n = float(plant.nrm @ rotation[:, 2])
        gaps = []
        for i in range(4):
            g0 = float(plant.nrm @ (plant.r + rotation @ plant.pad_rel[i])) / a_n
            gaps.append(-((plant.x[i] - g0) * a_n + so.h[i]) * 1e3)
        snap["gap_mm"] = gaps
    row = None if so is None else so.settle_row
    if row is not None:
        targets_deg = [math.degrees(t) for t in row["target_q_floor"][1:3]]
        snap["att_error_deg"] = [a - t for a, t in zip(att_deg, targets_deg, strict=True)]
        snap["gap_error_mm"] = [g - t for g, t in zip(snap["gap_mm"], row["gap_target_mm"], strict=True)]
    return snap


MASS_SCALE_NOTE = ("spec 422.2: plant superstructure mass and inertia x mass_scale (centre of mass kept); "
                   "controller YAML mass, W_ref and D1'' mass unchanged; crawler settle (pad gaps h_i, settle tilt) "
                   "and crawler damping keep the nominal-weight values (approximation)")


def scale_plant_mass(plant, mass_scale: float):
    """Spec 422.2 (decision Q-B): multiply the plant superstructure mass and inertia by ``mass_scale``.

    The centre of mass stays; only the plant changes (the controller keeps the YAML mass). 1.0 leaves the plant
    untouched (bit for bit). Rigid mast only (``flex`` 0: the rest-body mass / inertia are the body's).

    Raises:
        ValueError: ``mass_scale`` <= 0, or a flexible-mast plant with a scale other than 1.
    """
    mass_scale = float(mass_scale)
    if not mass_scale > 0.0:
        raise ValueError(f"mass_scale must be > 0, got {mass_scale!r}")
    if mass_scale == 1.0:
        return plant
    if getattr(plant, "flex", 0):
        raise ValueError("mass_scale is implemented for the rigid mast only")
    plant.m = plant.m * mass_scale
    plant.Ib = plant.Ib * mass_scale
    plant.Ibinv = np.linalg.inv(plant.Ib)
    plant.mr = plant.m
    plant.Ir = plant.Ib.copy()
    plant.mass_scale = mass_scale
    return plant


PAD_START_GAP_PASSES = 3
"""Rigid floor: the gap is linear in goff / a_n; a few passes absorb a_n (as r69_g8_screen)."""


def pad_floor_gaps_m(cl, plant) -> np.ndarray:
    """Pad bottom to floor gap per leg [m] at the current state (positive = in the air).

    Soil: gap to the original soil surface (``soil_floor`` geometry, minus the penetration).
    Rigid: the kernel floor gap of the r51 harness, (n.p + goff) / a_n - x."""
    rotation = cl.rcc._R(plant.q)
    a_n = float(plant.nrm @ rotation[:, 2])
    gaps = np.empty(4)
    for i in range(4):
        pad_height = float(plant.nrm @ (plant.r + rotation @ plant.pad_rel[i]))
        if plant.soil is None:
            gaps[i] = (pad_height + plant.goff[i]) / a_n - plant.x[i]
        else:
            gaps[i] = -((plant.x[i] - pad_height / a_n) * a_n + plant.soil.h[i])
    return gaps


def apply_pad_start_gap(cl, plant, spec: dict) -> dict:
    """Spec 426.7 B: move the floor under one pad so that its zero-stroke gap is a target.

    Called after the crawler settle (all pads in the air, the settle is unchanged) and before
    ``plant.t = 0``. Soil: the pad-surface height ``soil.h[i]`` (bump = the same soil heaped up,
    dip = the reference surface lowered, ASSUMPTION) and ``goff[i] = -h[i]``; rigid: ``goff[i]``.

    Args:
        spec: ``{"leg": "FL", "gap_m": 0.055}`` (target gap) or ``{"leg": ..., "delta_m": 0.060}``
            (settle gap + delta; > 0 = lowered floor).

    Returns:
        Record {leg, g0_mm, g_start_mm, delta_mm} (g0 = settle gap before the change).

    Raises:
        ValueError: unknown leg, or not exactly one of ``gap_m`` / ``delta_m``.
    """
    if spec.get("leg") not in LEGS or ("gap_m" in spec) == ("delta_m" in spec):
        raise ValueError(
            f"pad_start_gap needs a leg of {LEGS} and one of gap_m / delta_m: {spec!r}")
    leg = LEGS.index(spec["leg"])
    g0 = float(pad_floor_gaps_m(cl, plant)[leg])
    target = float(spec["gap_m"]) if "gap_m" in spec else g0 + float(spec["delta_m"])
    soil = plant.soil
    if soil is not None:
        soil.h[leg] += g0 - target  # the gap is minus (... + h): a higher surface, a smaller gap
        plant.goff[leg] = -soil.h[leg]
    else:
        for _ in range(PAD_START_GAP_PASSES):
            error = float(pad_floor_gaps_m(cl, plant)[leg]) - target
            a_n = float(plant.nrm @ cl.rcc._R(plant.q)[:, 2])
            plant.goff[leg] -= error * a_n
    g_start = float(pad_floor_gaps_m(cl, plant)[leg])
    return {"leg": spec["leg"], "g0_mm": g0 * 1e3, "g_start_mm": g_start * 1e3,
            "delta_mm": (g_start - g0) * 1e3}


def make_plant(cl, level: str, soil: str, pad_type: str, fs_kN: float, beta: float = 1.0e9, soil_kscale: float = 1.0,
               slope=(0.0, 0.0), settle_hook: str | None = None, settle_table: str | Path | None = None,
               settle_row: dict | None = None, mass_scale: float = 1.0):
    """Reduced plant of one case on a soil set (or "rigid") and a floor slope (roll, pitch) [deg].

    Args:
        settle_hook: "p0" | "harness" (None: ``$S9_SETTLE_HOOK``, default "p0"); see the module docstring.
        settle_table: settle table of the "harness" hook (None: ``$S9_SETTLE_TABLE`` or the default table).
        settle_row: a hook_harness row given directly (callers that already hold it); needs settle_hook "harness".
        mass_scale: spec 422.2 plant mass / inertia factor (:func:`scale_plant_mass`; 1.0 = unchanged).
            ``run_case`` applies a case's ``mass_scale`` itself after its (possibly wrapped) ``make_plant``.
    """
    import dyn_model as dm
    import s8_g4_rodside_check as rsc
    Plant = rsc.make_plant_class(cl)
    roll, pitch = float(slope[0]), float(slope[1])
    hook = resolve_settle_hook(settle_hook)
    if settle_row is not None and hook != SETTLE_HOOK_HARNESS:
        raise ValueError(f"settle_row needs settle_hook {SETTLE_HOOK_HARNESS!r}, got {hook!r}")
    row = None
    if soil != "rigid":
        if hook == SETTLE_HOOK_HARNESS:
            row = settle_row if settle_row is not None else load_settle_row(soil, level, slope, settle_table)
        p0_pitch_deg = math.degrees(P0_SETTLE[soil]["q"][2] - P0_SETTLE["rigid"]["q"][2])
        if row is not None:
            # the table add replaces the P0 add; written as (add - P0) before the common P0 add because the rows were
            # calibrated through this float path (run_slope_crawler_settle._hjob): bit for bit the tabled settle
            roll += float(row["floor_roll_add_deg"])
            pitch = pitch + float(row["floor_pitch_add_deg"]) - p0_pitch_deg
        pitch += p0_pitch_deg
    plant = Plant(level, roll, pitch, Fs=0.0)
    plant.settle_info = {"hook": hook, "row_key": None if row is None else settle_table_key(soil, level, slope),
                         "floor_slope_deg": (float(slope[0]), float(slope[1]))}
    k = beta / YAML_BETA
    plant.ko = np.asarray(plant.ko, float) * k
    plant.kh = plant.ko.copy()
    plant.kr = np.asarray(plant.kr, float) * k
    plant.Fs = np.array([fs_kN, fs_kN, 0.8333 * fs_kN, 0.8333 * fs_kN]) * 1e3
    plant.soil = None
    if soil != "rigid":
        ks = np.broadcast_to(np.asarray(dm.series(dm.k_rod(), dm.ASSUMPTIONS["frame_bracket_stiffness_N_m"]), float),
                             (4,)).copy()
        plant.ks = ks
        pad_xy = dm.geometry_from_params(dm.load_params()).pad_xy
        plant.soil = SoilPads(soil, pad_type, pad_xy, ks, soil_kscale, settle_row=row)
        plant.goff[:] = -plant.soil.h
    return scale_plant_mass(plant, mass_scale)


def soil_floor(cl, plant):
    """Called before every 1 ms chunk: update the four soil elements and the kernel floor.

    The soil state is committed at the current rod penetration (implicit Euler, rod spring k_s in series). For the
    next chunk the kernel pad spring is the series of k_s and the soil tangent A (dsigma/dz + R / h) about that state
    (plant.ks, plant.goff), so the kernel does not run one chunk ahead of a frozen soil surface (the frozen surface
    adds k_s v h, about 6 kN at 10 mm/s). Unloaded pads: tangent A (K + R / h) at the surface."""
    so = plant.soil
    if so is None:
        return
    R = cl.rcc._R(plant.q)
    ez = R[:, 2]
    a_n = float(plant.nrm @ ez)
    pen = np.empty(4)
    for i in range(4):
        p0 = plant.r + R @ plant.pad_rel[i]
        g0 = float(plant.nrm @ p0) / a_n
        pen[i] = (plant.x[i] - g0) * a_n + so.h[i]
    # consistency of the last chunk: kernel spring force at this penetration vs the committed soil force below
    f_kernel = plant.ks * np.maximum(pen - (plant.goff + so.h), 0.0)
    z_old = so.z.copy()
    soil_chunk(pen, so.z, so.sp, so.sy, so.area, so.coef, so.n, so.K, so.R, so.ks, 1e-3, so.force)
    so.max_force_mismatch = max(getattr(so, "max_force_mismatch", 0.0), float(np.max(np.abs(f_kernel - so.force))))
    so.z_max_rate = np.maximum(so.z_max_rate, (so.z - z_old) / 1e-3)
    ks_eff = np.empty(4)
    z0 = np.empty(4)
    for i in range(4):
        if so.force[i] > 0.0:
            kt = so.area[i] * (soil_tangent(so.z[i], so.sp[i], so.sy[i], so.coef[i], so.n, so.K) + so.R / 1e-3)
            ks_eff[i] = so.ks[i] * kt / (so.ks[i] + kt)
            z0[i] = pen[i] - so.force[i] / ks_eff[i]
        else:
            kt = so.area[i] * (so.K + so.R / 1e-3)
            ks_eff[i] = so.ks[i] * kt / (so.ks[i] + kt)
            z0[i] = so.z[i]
    plant.ks = ks_eff
    plant.goff[:] = z0 - so.h


# ----------------------------------------------------------------------------------------------- sensors
class SensorError:
    """Force reading error per leg: span (relative), residual offset [N] and white noise [N] (seeded)."""

    def __init__(self, span=(0, 0, 0, 0), offset_N=(0, 0, 0, 0), noise_N=0.0, seed=0):
        self.span = np.asarray(span, float); self.off = np.asarray(offset_N, float)
        self.noise = float(noise_N); self.rng = np.random.default_rng(seed)

    def apply(self, F):
        e = F * self.span + self.off
        if self.noise > 0:
            e = e + self.rng.normal(0.0, self.noise, 4)
        return F + e


def control_period(cl, Measurements, plant, cmd, valve, ha, period_s, rec, sens=None):
    lag_steps = round(cl.LAG_CHUNK_S / plant.dt)
    cps = round(cl.IMU_SAMPLE_S / cl.LAG_CHUNK_S)
    nsp = round(period_s / cl.IMU_SAMPLE_S)
    imu = []
    fmin = np.full(4, np.inf)
    crmax = 0.0
    for _ in range(nsp):
        fsum = np.zeros(3)
        for _ in range(cps):
            soil_floor(cl, plant)
            plant.cn = np.where(np.abs(valve) > 1e-6, C_MOVE, C_LOCK)
            acc = cl._lagged_step(plant, cmd, valve, lag_steps)
            fsum += acc[0:3]
            fmin = np.minimum(fmin, np.asarray(acc[11:15], float) - plant.Wr)
            crmax = max(crmax, float(acc[15]))
        imu.append(fsum / (lag_steps * cps))
    F_read = plant.pressure()
    if sens is not None:
        F_read = sens.apply(F_read)
    m = Measurements(
        t_s=plant.t, specific_force_m_s2=np.mean(imu, axis=0), angular_rate_rad_s=np.asarray(plant.w, float),
        head_pressure_Pa=F_read / ha, stroke_m=np.asarray(plant.sref, float),
        stroke_corrected_m=np.asarray(plant.x, float), imu_specific_force_samples_m_s2=np.array(imu))
    rec["fmin"] = fmin
    rec["crmax"] = crmax
    return m


# ----------------------------------------------------------------------------------------------- controller
def _imports():
    import c2py_r8d1_closed_loop as cl  # noqa: E402  (patches the harness modules)
    from outrigger_sim.control import c2
    from outrigger_sim.signals import Measurements
    return cl, c2, Measurements


def reference_config(cl, c2):
    """Harness preset with the project soil response explicitly off.

    Since 0400274 ``with_10hz_d1`` turns the project soil response on; the reference runs need
    the controller without it ("base" = project C2 before spec rev. 57, "loc" = SoilC2, whose
    own rules would otherwise run on top of the project ones: LOC twice, corner bias added)."""
    cfg = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True, with_reapproach=True)
    return replace(cfg, soil=c2.SoilResponseSettings())


def make_controller(cl, c2, variant: dict):
    cfg = reference_config(cl, c2)
    rule = variant.get("rule")
    if rule is None:
        ctrl = c2.C2Controller.from_params(cl.PARAMS, cfg)
    else:
        import s9_soil_rules as sr
        Cls = sr.make_class(c2)
        ctrl = Cls.from_params(cl.PARAMS, cfg)
        ctrl.soil_rule = dict(rule)
    ctrl.reset()
    return ctrl


# ----------------------------------------------------------------------------------------------- one run
def crawler_node_heights(cl, plant):
    R = cl.rcc._R(plant.q)
    return np.array([float(plant.nrm @ (plant.r + R @ c)) for c in plant.cr_rel])


def rut_clearance(cl, plant, node_d0, node_in):
    """Lowest rise of the crawler contact nodes (those in contact at the settle) above their settle position [m]
    (height above the rut, elastic rebound left out)."""
    d = crawler_node_heights(cl, plant)
    return float(np.min(d[node_in] - node_d0[node_in]))


def run_case(case: dict) -> dict:
    cl, c2, Measurements = _imports()
    C2Phase = c2.C2Phase
    t0 = time.perf_counter()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    # passed only when the case names them: wrappers replace make_plant with factories of the older signature
    settle_options = {k: case[k] for k in ("settle_hook", "settle_table") if case.get(k) is not None}
    plant = make_plant(cl, case["level"], case["soil"], case["pad"], case["fs_kN"], case.get("beta", 1.0e9),
                       case.get("soil_kscale", 1.0), case.get("slope", (0.0, 0.0)), **settle_options)
    # spec 422.2: applied here, not through make_plant, so wrapped factories of the older signature keep working
    mass_scale = float(case.get("mass_scale", 1.0))
    scale_plant_mass(plant, mass_scale)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    # spec 426.7 B: only cases with the key change the floor (no operation otherwise)
    start_gap = case.get("pad_start_gap")
    start_gap_record = None if start_gap is None else apply_pad_start_gap(cl, plant, start_gap)
    plant.t = 0.0
    plant.arm()
    settle = settle_snapshot(cl, plant)
    node_d0 = crawler_node_heights(cl, plant)
    node_in = node_d0 < 0.0
    hasher = hashlib.sha256()
    ctrl = make_controller(cl, c2, case.get("variant", {}))
    ha = ctrl.geometry.head_area_m2
    sens = None
    if case.get("sensor"):
        se = case["sensor"]
        sens = SensorError(se.get("span", (0, 0, 0, 0)), se.get("offset_N", (0, 0, 0, 0)), se.get("noise_N", 0.0),
                           se.get("seed", 0))
    W_cyl = plant.m * plant.g - float(np.sum(plant.Wr))
    F_min = ctrl.geometry.F_min_N
    cmd = np.zeros(4); valve = np.zeros(4)
    rec = {}
    ts = []
    t_level = t_done = t_ready = None
    t_off_first = None
    t_off_last_contact = None
    phase_prev = ctrl.phase
    min_after_off = math.inf
    att_max_after_off = 0.0
    cr_at_done = cr_at_ready = None
    sum_ratio_ready = None
    clear_est_ready = clear_true_ready = None
    max_stroke = 0.0
    after_ready_cr = 0.0
    after_ready_min = math.inf
    att_ready = []
    ph_path = []
    n_recontact = 0
    cr_series = []
    while plant.t < RUN_LIMIT_S:
        m = control_period(cl, Measurements, plant, cmd, valve, ha, ctrl.period_s, rec, sens)
        cmd = np.array(ctrl.update(m).leg_speed_m_s)
        hasher.update(cmd.tobytes())
        ph = ctrl.phase
        if ph is not phase_prev:
            ph_path.append((round(plant.t, 2), str(ph)))
        phase_prev = ph
        cr = rec["crmax"]
        if t_ready is None:
            cr_series.append((round(plant.t, 2), round(cr, 1)))
        Ftrue = plant.true_cyl_force()
        att = np.degrees(plant.attitude())
        max_stroke = max(max_stroke, float(np.max(plant.sref)))
        if t_level is None and ph is not C2Phase.TOUCH:
            t_level = plant.t
        if cr > 0.0:
            if t_off_first is not None and (t_off_last_contact is None or t_off_last_contact < t_off_first):
                n_recontact += 1
            t_off_last_contact = plant.t
        elif t_off_first is None and t_level is not None:
            t_off_first = plant.t
        elif t_off_first is not None and t_off_last_contact is not None and t_off_last_contact > t_off_first:
            t_off_first = t_off_first  # re-lifted after a re-contact (counted above)
        if t_off_first is not None and cr == 0.0:
            min_after_off = min(min_after_off, float(rec["fmin"].min()))
            att_max_after_off = max(att_max_after_off, float(np.abs(att).max()))
        if ph is C2Phase.DONE and t_done is None:
            t_done = plant.t
            cr_at_done = cr
        if ph is C2Phase.READY and t_ready is None:
            t_ready = plant.t
            cr_at_ready = cr
            sum_ratio_ready = float(np.sum(plant.pressure()) / W_cyl)
            clear_est_ready = float(ctrl.geometry.clearance_estimate_m(plant.x))
            clear_true_ready = rut_clearance(cl, plant, node_d0, node_in)
        if t_ready is not None:
            after_ready_cr = max(after_ready_cr, cr)
            after_ready_min = min(after_ready_min, float(rec["fmin"].min()))
            att_ready.append(att)
        if case.get("trace"):
            so = plant.soil
            ts.append([round(plant.t, 3), *np.round(cmd * 1e3, 3), *np.round(plant.x * 1e3, 2),
                       *np.round(np.asarray(m.head_pressure_Pa) * ha / 1e3, 2), *np.round(Ftrue / 1e3, 2),
                       *(np.round(so.z * 1e3, 2) if so is not None else [0.0] * 4), round(cr / 1e3, 2),
                       *np.round(att, 4), round(rut_clearance(cl, plant, node_d0, node_in) * 1e3, 2),
                       round(float(ctrl.geometry.clearance_estimate_m(plant.x)) * 1e3, 2), str(ph)])
        if ph is C2Phase.FAULT:
            break
        if t_ready is not None and plant.t >= t_ready + HOLD_AFTER_READY_S - 1e-9:
            break
    events = [f"{e.t_s:.1f} {e.name}" for e in ctrl.events]
    names = [e.name for e in ctrl.events]
    so = plant.soil
    att_end = np.degrees(plant.attitude())
    out = {
        "id": case["id"], "case": {k: v for k, v in case.items() if k not in ("trace",)},
        "t_level_s": t_level, "t_done_s": t_done, "t_ready_s": t_ready, "final_phase": str(ctrl.phase),
        "t_crawler_off_first_s": t_off_first, "t_crawler_last_contact_s": t_off_last_contact,
        "n_crawler_recontact": n_recontact, "commands_sha256": hasher.hexdigest(),
        "settle_hook": settle["hook"], "settle": settle,
        "crawler_N_at_done": cr_at_done, "crawler_N_at_ready": cr_at_ready, "crawler_N_max_after_ready": after_ready_cr,
        "crawler_burden_at_ready": None if cr_at_ready is None else cr_at_ready / (W_cyl + float(np.sum(plant.Wr))),
        "sumF_over_Wcyl_at_ready": sum_ratio_ready, "W_cyl_N": W_cyl,
        "clear_est_ready_mm": None if clear_est_ready is None else clear_est_ready * 1e3,
        "clear_true_ready_mm": None if clear_true_ready is None else clear_true_ready * 1e3,
        "min_true_Fcyl_after_off_kN": None if not np.isfinite(min_after_off) else min_after_off / 1e3,
        "min_margin_after_off_kN": None if not np.isfinite(min_after_off) else (min_after_off - F_min) / 1e3,
        "min_true_Fcyl_after_ready_kN": None if not np.isfinite(after_ready_min) else after_ready_min / 1e3,
        "att_max_after_off_deg": att_max_after_off,
        "att_end_deg": att_end.tolist(),
        "att_after_ready_max_deg": float(np.abs(att_ready).max()) if att_ready else None,
        "max_motor_stroke_mm": max_stroke * 1e3,
        "sink_final_mm": None if so is None else (so.z * 1e3).tolist(),
        "sink_rate_max_mm_s": None if so is None else (so.z_max_rate * 1e3).tolist(),
        "soil_force_mismatch_max_N": None if so is None else getattr(so, "max_force_mismatch", 0.0),
        "n_reapproach": sum(1 for n in names if n.startswith("leg_reapproach_start")),
        "n_reapproach_nocontact": sum(1 for n in names if n.startswith("WARN_LEG_REAPPROACH_NO_CONTACT")),
        "n_probe_rounds": len(ctrl.probe_history),
        "n_relevel": sum(1 for n in names if "relevel" in n),
        "n_warn": sum(1 for e in ctrl.events if e.name.startswith("WARN")),
        "phase_path": ph_path[:60],
        "events": events[:200],
        "wall_s": round(time.perf_counter() - t0, 1),
    }
    if start_gap_record is not None:  # spec 426.7 B (results without the key keep their keys)
        out["pad_start_gap"] = start_gap_record
    if mass_scale != 1.0:  # spec 422.2 (results of scale 1 keep their keys)
        out.update(mass_scale=mass_scale, mass_scale_note=MASS_SCALE_NOTE,
                   plant_weight_N=float(plant.m * plant.g),
                   controller_weight_ref_N=float(ctrl._reference_weight_N()))
    if hasattr(ctrl, "soil_meta"):
        out["soil_rule_meta"] = ctrl.soil_meta()
        # pinned-window margin: the smallest load-sum rise of a valid window that ended with the crawler loaded
        crd = dict(cr_series)
        pinned = [(t, rise) for t, rise, _ in out["soil_rule_meta"]["rise_log"] if crd.get(t, 0.0) > 1000.0]
        out["min_rise_pinned_N"] = min((r for _, r in pinned), default=None)
        out["n_windows_pinned"] = len(pinned)
    if case.get("trace"):
        out["trace_cols"] = ["t", "u_FL", "u_FR", "u_RL", "u_RR", "x_FL", "x_FR", "x_RL", "x_RR", "Fread_FL", "Fread_FR",
                             "Fread_RL", "Fread_RR", "Ftrue_FL", "Ftrue_FR", "Ftrue_RL", "Ftrue_RR", "z_FL", "z_FR",
                             "z_RL", "z_RR", "crawler_kN", "roll", "pitch", "clear_true_mm", "clear_est_mm", "phase"]
        out["trace"] = ts
    return out


def _safe(case):
    try:
        return run_case(case)
    except Exception as exc:  # keep the batch alive, record the failure
        import traceback
        return {"id": case["id"], "error": repr(exc), "tb": traceback.format_exc()}


def run_batch(cases, out_path: Path, workers: int, meta: dict | None = None):
    t0 = time.perf_counter()
    with Pool(min(workers, len(cases))) as pool:
        res = pool.map(_safe, cases, chunksize=1)
    out = {"meta": {"script": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
                    # LF line ends: a CRLF checkout (Windows worktree) gives the same digest
                    "script_sha256": hashlib.sha256(
                        Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                    "wall_s": round(time.perf_counter() - t0, 1), "workers": workers,
                    "settle_hook_env": resolve_settle_hook(),
                    "settle_table_env": os.environ.get(SETTLE_TABLE_ENV) or str(DEFAULT_SETTLE_TABLE), **(meta or {})},
           "runs": res}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    return out


def matrix(soils=("rigid", "G1", "J1", "J2", "S1"), pads=("A", "B"), levels=("top",), fs=(0.0,), variant=None,
           trace_top=True, tag="base"):
    cases = []
    for s in soils:
        for p in (pads if s != "rigid" else ("B",)):
            for lv in levels:
                for f in fs:
                    cases.append({"id": f"{tag}|{s}|{p}|{lv}|Fs{f:g}", "soil": s, "pad": p, "level": lv, "fs_kN": f,
                                  "variant": variant or {}, "trace": trace_top and lv == "top" and f == fs[0]})
    return cases


if __name__ == "__main__":
    out = Path(sys.argv[1])
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    flt = sys.argv[3] if len(sys.argv) > 3 else ""
    rule = json.loads(os.environ.get("S9_RULE", "null"))
    levels = tuple(os.environ.get("S9_LEVELS", "top").split(","))
    fs = tuple(float(x) for x in os.environ.get("S9_FS", "0").split(","))
    tag = os.environ.get("S9_TAG", "base" if rule is None else "loc")
    cs = [c for c in matrix(levels=levels, fs=fs, variant=None if rule is None else {"rule": rule}, tag=tag)
          if flt in c["id"]]
    r = run_batch(cs, out, workers)
    for x in r["runs"]:
        print(x["id"], x.get("error") or {k: x[k] for k in ("t_ready_s", "crawler_N_at_ready", "min_margin_after_off_kN",
                                                             "att_max_after_off_deg", "n_reapproach", "final_phase", "wall_s")})
