"""K-2b E1: influence matrix S of the reduced harness plant by 1 mm leg steps.

Diagnostic with the controller off. Purpose: check the linear 6-DoF influence matrix of
``k2_dyn_sensitivity.md`` (Q3, P3-P4, E1) against the nonlinear harness plant. Record-only
experiment, not a judgement run.

Plant: ``run_mast_flex_c2_check.FlexPlant`` with an empty CONFIG (rigid mast, flex 0: the original
``run_control_comparison`` kernel), top auger level, flat floor, Fs 0, pad friction mode 0,
dt 5e-4 s. This is the physics of the K-2 harness arm H0 (``KPlant`` with ``diss_preset none``
adds no physics; the valve lag of ``r8d1_td`` acts on controller commands only and is not used
here because the steps are stroke commands).

Procedure per (beta, crawler kn scale):
  1. start at the analytic settled pose on the crawler, legs just above their touch extension;
  2. preload: each leg extends at 2 mm/s until its pad carries 22 kN, then a trim loop keeps
     every pad in 15-30 kN; settle 20 s with all commands 0 -> state "on_crawler";
  3. all legs extend together at 0.5 v_max until the crawler is clear by 30 mm; settle 20 s
     -> state "pads_only" (``--diag-loaded``: FR, RL loaded instead -> state "diag_loaded");
  4. from each state snapshot: one baseline run (all commands 0) and one run per leg with a
     1 mm extension (ramp 0.5 s at 2 mm/s) then hold. S_ij = (F_i(step) - F_i(baseline)) / 1 mm,
     so the remaining settle motion of the snapshot cancels (same deterministic plant).

The pad force is the axial pad contact force of the kernel (``acc[11:15]``, 1 ms samples). S is
reported at two windows after the ramp: "hold2s" (mean of [1.6, 2.0] s of hold, the E1
specification) and "late" (mean of the last 2 s of an 8 s hold).

Linear references (same model as the dynamics-expert ``linmodel.py``): rigid 6-DoF, crawler
rollers diag(kt, kt, kn) with kt = kn, pads diag(kt_pad, kt_pad, k_leg), k_leg = k_oil series k_s,
contact points at the crawler bottom level, no geometric stiffness; plus the same model with the
crawler active set read from the snapshot, and the 3-DoF ``dyn_model.load_sensitivity`` for the
pads-only state.

Run (project root, dynamics-dev, E-cores):
  C:\\ProgramData\\miniforge3\\envs\\dynamics-dev\\python.exe -I -B
      04_scripts/03_control/k2/k2b_probe/e1_smatrix_probe.py --affinity 0x0FFF0000 --out <json>
"""

from __future__ import annotations

import argparse
import copy
import ctypes
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\agent-aeb1f64260f1bd2d7")
DYNAMICS_DIR = REPO_ROOT / "04_scripts" / "01_dynamics"
sys.path.insert(0, str(REPO_ROOT / "04_scripts" / "03_control"))
sys.path.insert(0, str(DYNAMICS_DIR))

import dyn_model as dm  # noqa: E402
import numpy as np  # noqa: E402
import run_control_comparison as rcc  # noqa: E402
import run_mast_flex_c2_check as rmf  # noqa: E402  (patches rcc.Plant = FlexPlant in this process)

LEGS = ("FL", "FR", "RL", "RR")
BETAS_PA = (0.69e9, 1.0e9, 1.6e9)
CRAWLER_KN_SCALES = (1.0, 3.0)
LEVEL = "top"
LOCK_RECORDS = []

CHUNK_STEPS = 2  # 1 ms at dt 5e-4 s
STEP_M = 1.0e-3
STEP_RAMP_S = 0.5
HOLD_S = 8.0
HOLD2S_WINDOW_S = (1.6, 2.0)  # after the ramp end
LATE_WINDOW_S = 2.0  # last part of the hold

APPROACH_SPEED_M_S = 2.0e-3
PRELOAD_START_GAP_M = 0.015  # legs placed this far above the nominal touch extension
PRELOAD_TARGET_N = 22.0e3
PRELOAD_BAND_N = (15.0e3, 30.0e3)
TRIM_SPEED_M_S = 1.0e-3
TRIM_PERIOD_S = 0.1
TRIM_IN_BAND_S = 1.0
PRELOAD_TIMEOUT_S = 120.0
SETTLE_S = 20.0

LIFT_SPEED_FRACTION = 0.5
LIFT_CLEARANCE_M = 0.030
LIFT_TIMEOUT_S = 60.0

# supplementary "diag_loaded" state (--diag-loaded): late diagonal pair loaded as in the K-2
# failure rows (35-90 kN)
DIAG_LOAD_TARGET_N = 60.0e3
DIAG_VICTIM_FLOOR_N = 6.0e3
DIAG_LOADED_BETAS_PA = (1.0e9, 1.6e9)


@dataclass
class Trace:
    """1 ms samples of one run from a snapshot."""

    t_s: np.ndarray  # (n,)
    pad_N: np.ndarray  # (n, 4) pad axial contact force
    crawler_N: np.ndarray  # (n,) total crawler normal force
    rollers_active: np.ndarray  # (n,) number of crawler spheres in contact


# ------------------------------------------------------------------------------ process / records
def set_affinity(mask: int) -> str:
    """Pin this process to ``mask`` (Windows) and return the mask read back."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.SetProcessAffinityMask.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
    kernel32.GetProcessAffinityMask.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.POINTER(ctypes.c_size_t),
    )
    handle = kernel32.GetCurrentProcess()
    if not kernel32.SetProcessAffinityMask(handle, ctypes.c_size_t(mask)):
        raise OSError(f"SetProcessAffinityMask({mask:#x}) failed")
    process_mask = ctypes.c_size_t()
    system_mask = ctypes.c_size_t()
    kernel32.GetProcessAffinityMask(handle, ctypes.byref(process_mask), ctypes.byref(system_mask))
    return hex(process_mask.value)


def git_state() -> dict:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        ).stdout.strip()

    return {
        "head": run("rev-parse", "HEAD"),
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "status_tracked": run("status", "--porcelain", "--untracked-files=no"),
    }


# ------------------------------------------------------------------------------ plant driving
def build_plant(beta_pa: float, crawler_kn_scale: float) -> rmf.FlexPlant:
    rmf.CONFIG.clear()
    rcc.CRAWLER_K_SCALE = crawler_kn_scale
    try:
        plant = rmf.FlexPlant(LEVEL, 0.0, 0.0, beta_pa, 0.0)
    finally:
        rcc.CRAWLER_K_SCALE = 1.0
    mode = os.environ.get('LK_MODE')
    if mode:
        l0r = os.environ.get('LK_L0R')
        LOCK_RECORDS.append(plant.set_lock_stiffness(mode, float(l0r) if l0r else None))
    if plant.flex != 0 or plant.fmode != 0:
        raise RuntimeError("plant is not the rigid-mast, friction-mode-0 kernel")
    return plant


def advance(plant, speed_m_s: np.ndarray, n_chunks: int = 1) -> np.ndarray:
    """Advance ``n_chunks`` 1 ms chunks at constant leg speeds; returns the last acc slots."""
    acc = None
    for _ in range(n_chunks):
        acc = plant.step(speed_m_s, CHUNK_STEPS)
    return acc


def pad_forces(plant) -> np.ndarray:
    return np.array(plant.acc[11:15], float)


def preload_on_crawler(plant) -> dict:
    """Bring all four pads to 15-30 kN while the crawler still carries the rest (controller off)."""
    plant.sref[:] = np.asarray(plant.geo.touch_extension, float) - PRELOAD_START_GAP_M
    seated = np.zeros(4, bool)
    elapsed_s = 0.0
    while not seated.all():
        advance(plant, np.where(seated, 0.0, APPROACH_SPEED_M_S))
        elapsed_s += 1e-3
        seated |= pad_forces(plant) >= PRELOAD_TARGET_N
        if elapsed_s > PRELOAD_TIMEOUT_S:
            raise RuntimeError(f"preload approach timeout, pad forces {pad_forces(plant)}")
    trim_chunks = int(round(TRIM_PERIOD_S / 1e-3))
    in_band_s = 0.0
    while in_band_s < TRIM_IN_BAND_S:
        forces = pad_forces(plant)
        speed = np.where(
            forces < PRELOAD_BAND_N[0],
            TRIM_SPEED_M_S,
            np.where(forces > PRELOAD_BAND_N[1], -TRIM_SPEED_M_S, 0.0),
        )
        advance(plant, speed, trim_chunks)
        elapsed_s += TRIM_PERIOD_S
        in_band_s = in_band_s + TRIM_PERIOD_S if not speed.any() else 0.0
        if elapsed_s > PRELOAD_TIMEOUT_S:
            raise RuntimeError(f"preload trim timeout, pad forces {pad_forces(plant)}")
    advance(plant, np.zeros(4), int(round(SETTLE_S / 1e-3)))
    return {"preload_s": round(elapsed_s, 3), "settle_s": SETTLE_S}


def load_late_diagonal(plant) -> dict:
    """Supplementary state: extend the late diagonal pair FR, RL until it carries
    DIAG_LOAD_TARGET_N or a first-diagonal pad (FL, RR) falls to DIAG_VICTIM_FLOOR_N, then settle
    (crawler still on the floor)."""
    late = np.array([False, True, True, False])
    elapsed_s = 0.0
    while True:
        forces = pad_forces(plant)
        loading = late & (forces < DIAG_LOAD_TARGET_N)
        if not loading.any() or forces[~late].min() <= DIAG_VICTIM_FLOOR_N:
            break
        advance(plant, np.where(loading, APPROACH_SPEED_M_S, 0.0), 10)
        elapsed_s += 10e-3
        if elapsed_s > PRELOAD_TIMEOUT_S:
            raise RuntimeError("late-diagonal loading timeout")
    advance(plant, np.zeros(4), int(round(SETTLE_S / 1e-3)))
    return {"diag_load_s": round(elapsed_s, 3), "settle_s": SETTLE_S}


def lift_off_crawler(plant) -> dict:
    """Extend all legs together until the crawler is clear by LIFT_CLEARANCE_M, then settle."""
    speed = np.full(4, LIFT_SPEED_FRACTION * float(plant.geo.v_max))
    elapsed_s = 0.0
    while plant.acc[15] > 0.0 or plant.crawler_clearance() < LIFT_CLEARANCE_M:
        advance(plant, speed, 10)
        elapsed_s += 10e-3
        if elapsed_s > LIFT_TIMEOUT_S:
            raise RuntimeError("crawler lift-off timeout")
    advance(plant, np.zeros(4), int(round(SETTLE_S / 1e-3)))
    return {"lift_s": round(elapsed_s, 3), "settle_s": SETTLE_S}


def state_record(plant) -> dict:
    roll, pitch = plant.attitude()
    active = np.asarray(plant.cflag, int)
    return {
        "pad_force_kN": (pad_forces(plant) / 1e3).round(3).tolist(),
        "crawler_force_kN": round(float(plant.acc[15]) / 1e3, 3),
        "crawler_spheres_active": int(active.sum()),
        "crawler_spheres_active_flags": active.tolist(),
        "crawler_clearance_mm": round(plant.crawler_clearance() * 1e3, 3),
        "motor_stroke_mm": (np.asarray(plant.sref) * 1e3).round(3).tolist(),
        "attitude_deg": [round(math.degrees(roll), 5), round(math.degrees(pitch), 5)],
        "t_plant_s": round(plant.t, 4),
    }


def run_from_snapshot(snapshot, leg: int | None) -> Trace:
    """Baseline (leg None) or a 1 mm step on ``leg`` from a deep copy of the snapshot."""
    plant = copy.deepcopy(snapshot)
    ramp_chunks = int(round(STEP_RAMP_S / 1e-3))
    hold_chunks = int(round(HOLD_S / 1e-3))
    ramp_speed = np.zeros(4)
    if leg is not None:
        ramp_speed[leg] = STEP_M / STEP_RAMP_S
    n = ramp_chunks + hold_chunks
    t_s = np.empty(n)
    pad_N = np.empty((n, 4))
    crawler_N = np.empty(n)
    rollers = np.empty(n, int)
    for k in range(n):
        acc = advance(plant, ramp_speed if k < ramp_chunks else np.zeros(4))
        t_s[k] = (k + 1) * 1e-3
        pad_N[k] = acc[11:15]
        crawler_N[k] = acc[15]
        rollers[k] = int(np.sum(plant.cflag))
    if leg is not None and abs(plant.sref[leg] - snapshot.sref[leg] - STEP_M) > 1e-9:
        raise RuntimeError(f"step on {LEGS[leg]} not applied (stroke limit or force saturation)")
    return Trace(t_s, pad_N, crawler_N, rollers)


def window_mean(
    trace_delta: np.ndarray, t_s: np.ndarray, start_s: float, end_s: float
) -> np.ndarray:
    mask = (t_s > start_s) & (t_s <= end_s + 1e-12)
    return trace_delta[mask].mean(axis=0)


def measure_matrix(snapshot) -> dict:
    """Influence matrix columns from one baseline and four step runs."""
    base = run_from_snapshot(snapshot, None)
    s_hold2 = np.zeros((4, 4))
    s_late = np.zeros((4, 4))
    swing = np.zeros((4, 4))
    rollers_min = []
    crawler_delta_kN = []
    pad_min_kN = []
    hold2 = (STEP_RAMP_S + HOLD2S_WINDOW_S[0], STEP_RAMP_S + HOLD2S_WINDOW_S[1])
    end_s = STEP_RAMP_S + HOLD_S
    for j in range(4):
        step = run_from_snapshot(snapshot, j)
        delta = step.pad_N - base.pad_N
        s_hold2[:, j] = window_mean(delta, step.t_s, *hold2) / (STEP_M * 1e3)
        s_late[:, j] = window_mean(delta, step.t_s, end_s - LATE_WINDOW_S, end_s) / (STEP_M * 1e3)
        late = step.t_s > end_s - LATE_WINDOW_S
        swing[:, j] = (delta[late].max(axis=0) - delta[late].min(axis=0)) / (STEP_M * 1e3)
        rollers_min.append(int(step.rollers_active.min()))
        # a pad reaching 0 N during a step means its column is clipped (lift-off), not a stiffness
        pad_min_kN.append((step.pad_N.min(axis=0) / 1e3).round(3).tolist())
        crawler_delta_kN.append(
            round(
                float(
                    window_mean(
                        (step.crawler_N - base.crawler_N)[:, None],
                        step.t_s,
                        end_s - LATE_WINDOW_S,
                        end_s,
                    )[0]
                )
                / 1e3,
                4,
            )
        )
    return {
        "S_hold2s_kN_per_mm": (s_hold2 / 1e3).round(4).tolist(),
        "S_late_kN_per_mm": (s_late / 1e3).round(4).tolist(),
        "late_window_peak_to_peak_kN_per_mm": (swing / 1e3).round(4).tolist(),
        "baseline_drift_kN": ((base.pad_N[-1] - base.pad_N[0]) / 1e3).round(4).tolist(),
        "crawler_spheres_active_min_per_step": rollers_min,
        "pad_force_min_kN_per_step": pad_min_kN,
        "crawler_force_change_kN_per_step": crawler_delta_kN,
    }


# ------------------------------------------------------------------------------ linear references
def _skew(r: np.ndarray) -> np.ndarray:
    return np.array([[0, -r[2], r[1]], [r[2], 0, -r[0]], [-r[1], r[0], 0]])


def _point_map(r: np.ndarray) -> np.ndarray:
    return np.hstack([np.eye(3), -_skew(r)])


def linear_influence(
    plant, roller_mask: np.ndarray | None, with_crawler: bool = True
) -> np.ndarray:
    """dF_i/ds_j [N/m] of the linear 6-DoF model (``linmodel.py`` of the dynamics report).

    ``roller_mask`` None = every roller station (crawler gap <= 0) as in the report; otherwise
    the given active set of crawler spheres.
    """
    gaps = dm.crawler_gaps(dm.load_params())
    stiffness = np.zeros((6, 6))
    if with_crawler:
        active = (gaps <= 0) if roller_mask is None else np.asarray(roller_mask, bool)
        for j in np.flatnonzero(active):
            k3 = np.diag([plant.ktcr[j], plant.ktcr[j], plant.kcr[j]])
            g = _point_map(plant.cr_rel[j])
            stiffness += g.T @ k3 @ g
    k_leg = 1.0 / (1.0 / np.asarray(plant.ko, float) + 1.0 / plant.ks)
    floor_z = plant.cr_rel[np.flatnonzero(gaps <= 0)[0], 2]
    pad_points = np.column_stack([plant.pad_rel[:, :2], np.full(4, floor_z)])
    normal_rows = []
    for i in range(4):
        g = _point_map(pad_points[i])
        stiffness += g.T @ np.diag([plant.kt[i], plant.kt[i], k_leg[i]]) @ g
        normal_rows.append(g[2])
    compliance = np.linalg.inv(stiffness)
    influence = np.zeros((4, 4))
    for j in range(4):
        q = compliance @ (k_leg[j] * normal_rows[j])
        for i in range(4):
            influence[i, j] = k_leg[i] * ((1.0 if i == j else 0.0) - normal_rows[i] @ q)
    return influence


def pads_only_3dof(plant) -> np.ndarray:
    k_leg = 1.0 / (1.0 / np.asarray(plant.ko, float) + 1.0 / plant.ks)
    return dm.load_sensitivity(k_leg, np.asarray(plant.geo.pad_xy, float))


# ------------------------------------------------------------------------------ coupling summary
def coupling_summary(s_kn_mm) -> dict:
    """Pair sums and stripping coefficients (rows = loaded pad, columns = extended leg)."""
    s = np.asarray(s_kn_mm, float)
    fl, fr, rl, rr = range(4)
    return {
        "diag_pair_FR_RL_on_FL_RR": [s[fl, fr] + s[fl, rl], s[rr, fr] + s[rr, rl]],
        "diag_pair_FL_RR_on_FR_RL": [s[fr, fl] + s[fr, rr], s[rl, fl] + s[rl, rr]],
        "rear_axle_pair_on_FL_FR": [s[fl, rl] + s[fl, rr], s[fr, rl] + s[fr, rr]],
        "front_axle_pair_on_RL_RR": [s[rl, fl] + s[rl, fr], s[rr, fl] + s[rr, fr]],
        "right_side_pair_on_FL_RL": [s[fl, fr] + s[fl, rr], s[rl, fr] + s[rl, rr]],
        "all_four_row_sum": s.sum(axis=1).tolist(),
        "alpha_adj_rear_RR_from_RL": -s[rr, rl] / s[rl, rl],
        "alpha_adj_rear_RL_from_RR": -s[rl, rr] / s[rr, rr],
        "alpha_adj_front_FL_from_FR": -s[fl, fr] / s[fr, fr],
        "alpha_side_RR_from_FR": -s[rr, fr] / s[fr, fr],
        "alpha_diag_RR_from_FL": -s[rr, fl] / s[fl, fl],
        "reciprocity_max_abs_S_minus_ST": float(np.abs(s - s.T).max()),
    }


def rounded(obj, digits: int = 4):
    if isinstance(obj, dict):
        return {key: rounded(value, digits) for key, value in obj.items()}
    if isinstance(obj, (list, tuple, np.ndarray)):
        return [rounded(value, digits) for value in obj]
    if isinstance(obj, (float, np.floating)):
        return round(float(obj), digits)
    return obj


# ------------------------------------------------------------------------------ one combination
MAIN_PROCEDURES = (("on_crawler", preload_on_crawler), ("pads_only", lift_off_crawler))
DIAG_LOADED_PROCEDURES = (("on_crawler", preload_on_crawler), ("diag_loaded", load_late_diagonal))


def run_combination(beta_pa: float, crawler_kn_scale: float, procedures=MAIN_PROCEDURES) -> dict:
    t0 = time.perf_counter()
    plant = build_plant(beta_pa, crawler_kn_scale)
    result = {
        "beta_Pa": beta_pa,
        "crawler_kn_scale": crawler_kn_scale,
        "k_oil_N_m": np.asarray(plant.ko, float).round(0).tolist(),
        "k_s_N_m": plant.ks.round(0).tolist(),
        "crawler_kn_per_sphere_N_m": float(plant.kcr[0]),
        "states": {},
    }
    for name, procedure in procedures:
        prep = procedure(plant)
        snapshot = copy.deepcopy(plant)
        measured = measure_matrix(snapshot)
        active = np.asarray(snapshot.cflag, bool)
        if name != "pads_only":
            linear = {
                "linear_report_all_rollers": linear_influence(snapshot, None),
                "linear_active_set": linear_influence(snapshot, active),
            }
        else:
            linear = {
                "linear_report_pads_only_6dof": linear_influence(
                    snapshot, None, with_crawler=False
                ),
                "linear_pads_only_3dof": pads_only_3dof(snapshot),
            }
        linear_kn_mm = {key: (value / 1e6) for key, value in linear.items()}
        result["states"][name] = {
            "preparation": prep,
            "state": state_record(snapshot),
            "measured": measured,
            "linear_kN_per_mm": {
                key: value.round(4).tolist() for key, value in linear_kn_mm.items()
            },
            "coupling": rounded(
                {
                    "measured_late": coupling_summary(measured["S_late_kN_per_mm"]),
                    "measured_hold2s": coupling_summary(measured["S_hold2s_kN_per_mm"]),
                    **{key: coupling_summary(value) for key, value in linear_kn_mm.items()},
                }
            ),
        }
    result["wall_s"] = round(time.perf_counter() - t0, 2)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--affinity",
        type=lambda text: int(text, 0),
        default=None,
        help="process mask, e.g. 0x0FFF0000",
    )
    parser.add_argument("--out", type=Path, required=True, help="output JSON path")
    parser.add_argument(
        "--diag-loaded",
        action="store_true",
        help="supplementary set: late diagonal FR, RL loaded to 60 kN (beta 1.0 / 1.6)",
    )
    args = parser.parse_args()
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    mask = set_affinity(args.affinity) if args.affinity is not None else None
    t0 = time.perf_counter()
    betas = DIAG_LOADED_BETAS_PA if args.diag_loaded else BETAS_PA
    procedures = DIAG_LOADED_PROCEDURES if args.diag_loaded else MAIN_PROCEDURES
    combos = []
    for beta_pa in betas:
        for scale in CRAWLER_KN_SCALES:
            combo = run_combination(beta_pa, scale, procedures)
            print(f"beta {beta_pa / 1e9:.2f} GPa  kn x{scale:g}  {combo['wall_s']} s", flush=True)
            combos.append(combo)
    record = {
        "experiment": "K-2b E1 harness influence matrix (record only, not a judgement run)",
        "started": started,
        "wall_s": round(time.perf_counter() - t0, 2),
        "git": git_state(),
        # the probe script is untracked: its digest identifies the version that wrote this record
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "argv": sys.argv,
        "python": sys.executable,
        "affinity_mask": mask,
        "env": {
            key: os.environ.get(key)
            for key in ("MKL_THREADING_LAYER", "NUMBA_CACHE_DIR", "CONDA_DEFAULT_ENV")
        },
        "numpy": np.__version__,
        "settings": {
            "level": LEVEL,
            "floor": "flat",
            "mast": "rigid (FlexPlant flex 0)",
            "Fs_N": 0.0,
            "pad_friction_mode": 0,
            "dt_s": rcc.DT,
            "sample_s": 1e-3,
            "step_m": STEP_M,
            "ramp_s": STEP_RAMP_S,
            "hold_s": HOLD_S,
            "hold2s_window_s_after_ramp": HOLD2S_WINDOW_S,
            "late_window_s": LATE_WINDOW_S,
            "preload_target_N": PRELOAD_TARGET_N,
            "preload_band_N": PRELOAD_BAND_N,
            "settle_s": SETTLE_S,
            "lift_clearance_m": LIFT_CLEARANCE_M,
            "diag_loaded": args.diag_loaded,
            "diag_load_target_N": DIAG_LOAD_TARGET_N,
            "diag_victim_floor_N": DIAG_VICTIM_FLOOR_N,
            "pad_force": "kernel acc[11:15] axial pad contact force (incl. dashpot)",
        },
        "combinations": combos,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(
        json.dumps({"out": str(args.out), "wall_s": record["wall_s"], "n_runs": 10 * len(combos)})
    )


if __name__ == "__main__":
    main()
