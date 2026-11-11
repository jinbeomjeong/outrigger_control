"""Harness 1 mm step S at the Chrono E2_b16 lock modes (front FLOOR, rear LOCK), lock_stiffness on/off.

Record only. Builds the E1 plant (``04_scripts/03_control/k2/k2b_probe/e1_smatrix_probe.py`` of
this checkout, beta 1.6, kn x1) and reaches the Chrono base loads in two stages so that the front
legs pass their knee while locked:

  A. extension-only preload to front = base - FRONT_GAIN_N, rear = base - REAR_GAIN_N;
  B. extend RL and RR together (front legs locked) until the front mean reaches the base front
     mean, settle; then extend the rear legs alone up to base - 0.5 kN (front legs stay locked).

With the option on, the front legs gain about 6.5 kN after their lock (> knee 4.1 kN) and turn
FLOOR (rod side at its floor, stiffness back to k_n); the rear legs relock at the end of B (LOCK).
The off arm runs the same procedure. Then the E1 matrix (baseline + four 1 mm steps) and an FR+RL
pair step.

Usage (repo root, dynamics-dev):
    python -I -B run_floor_state.py <e2_summary.json> <out.json> [--lock l1r]
"""

from __future__ import annotations

import argparse
import copy
import ctypes
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO_ROOT / "04_scripts" / "03_control" / "k2" / "k2b_probe"))
import e1_smatrix_probe as probe  # noqa: E402

BETA_PA = 1.6e9
FL, FR, RL, RR = range(4)
FRONT_GAIN_N = 6.5e3
"""Front load gained after the lock in stage B (front knee about 4.1 kN)."""
REAR_GAIN_N = 16.5e3
"""Rear load gained after the rear seat: front seating and stage B (tuned by trial runs: 5.6 /
13.0 kN ended the rears at about +7 / +3.5 kN above the base)."""
LIFT_REAR_SPEED_M_S = 2.0e-4
BAND_N = 500.0
TRIM_SPEED_M_S = 1.0e-4
TRIM_PERIOD_S = 0.1
TIMEOUT_S = 400.0
AFFINITY_E_CORES = 0x0FFF0000


def pin_to_e_cores() -> None:
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.SetProcessAffinityMask.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
    kernel32.SetProcessAffinityMask(kernel32.GetCurrentProcess(), AFFINITY_E_CORES)


def lock_modes(plant) -> list[str] | None:
    """LOCK / FLOOR / LIFT / MOVING of each leg from the rod-side state (None with the option off)."""
    if plant.lockm == 0:
        return None
    modes = []
    for i in range(4):
        spring_N = plant.krs[i] * (plant.xlk[i] - plant.x[i])
        if plant.rlock[i] != 1:
            modes.append("MOVING")
        elif plant.acc[11 + i] <= 0.0:
            modes.append("LIFT")
        else:
            modes.append("FLOOR" if spring_N >= plant.fcap[i] else "LOCK")
    return modes


def rod_state(plant) -> dict | None:
    if plant.lockm == 0:
        return None
    return {"rod_force_N": plant.frod.round(2).tolist(), "rod_force_cap_N": plant.fcap.round(2).tolist(),
            "knee_pad_load_N": (plant.fcap / (plant.krs / (plant.ko + plant.krs))).round(1).tolist()}


def preload_extend_only(plant, target_N: np.ndarray) -> dict:
    """Stage A without retraction: each leg extends until its pad reaches the target, then holds.

    The E1 trim retracts legs above the band; a lock after a retraction takes p_r0 at the POC
    pilot threshold (L1-R rule), so its knee is far higher (front about 18 kN at 22 kN). Chrono
    E2 locks after extensions, hence extensions only here.
    """
    plant.sref[:] = np.asarray(plant.geo.touch_extension, float) - probe.PRELOAD_START_GAP_M
    # The jump of s_ref (E1 start) leaves the rod at its old position; a leg that waits (u = 0) would
    # lock there and anchor far from its new equilibrium. Move the rod with it (hanging rod).
    plant.x[:] = plant.sref
    seated = np.zeros(4, bool)
    elapsed_s = 0.0
    for group in ((RL, RR), (FL, FR)):  # rear first: the front legs lock last, at their target
        in_group = np.zeros(4, bool)
        in_group[list(group)] = True
        while not seated[in_group].all():
            moving = in_group & ~seated
            probe.advance(plant, np.where(moving, probe.APPROACH_SPEED_M_S, 0.0))
            elapsed_s += 1e-3
            seated |= in_group & (probe.pad_forces(plant) >= target_N)
            if elapsed_s > TIMEOUT_S:
                raise RuntimeError("stage A approach timeout")
    probe.advance(plant, np.zeros(4), int(round(probe.SETTLE_S / 1e-3)))
    return {"preload_s": round(elapsed_s, 3), "settle_s": probe.SETTLE_S}


def stage_b_load_rear(plant, front_target_N: float) -> dict:
    """Extend RL, RR together until the front mean pad load reaches the target, then settle."""
    speed = np.array([0.0, 0.0, LIFT_REAR_SPEED_M_S, LIFT_REAR_SPEED_M_S])
    elapsed_s = 0.0
    while probe.pad_forces(plant)[[FL, FR]].mean() < front_target_N:
        probe.advance(plant, speed, 10)
        elapsed_s += 10e-3
        if elapsed_s > TIMEOUT_S:
            raise RuntimeError("stage B timeout")
    probe.advance(plant, np.zeros(4), int(round(probe.SETTLE_S / 1e-3)))
    return {"stage_b_s": round(elapsed_s, 3), "modes_after_b": lock_modes(plant)}


def trim_rear(plant, rear_target_N: np.ndarray) -> dict:
    """Rear legs alone up to target - BAND_N by extension only (front commands 0), then settle."""
    chunks = int(round(TRIM_PERIOD_S / 1e-3))
    elapsed_s = in_band_s = 0.0
    while in_band_s < 1.0:
        error_N = probe.pad_forces(plant)[[RL, RR]] - rear_target_N
        speed = np.zeros(4)
        speed[[RL, RR]] = np.where(error_N < -BAND_N, TRIM_SPEED_M_S, 0.0)
        probe.advance(plant, speed, chunks)
        elapsed_s += TRIM_PERIOD_S
        in_band_s = in_band_s + TRIM_PERIOD_S if not speed.any() else 0.0
        if elapsed_s > TIMEOUT_S:
            raise RuntimeError("rear trim timeout")
    probe.advance(plant, np.zeros(4), int(round(probe.SETTLE_S / 1e-3)))
    return {"rear_trim_s": round(elapsed_s, 3)}


def pair_step(snapshot, legs: tuple[int, ...]) -> list[float]:
    """Load change [kN] at the hold2s window for a 1 mm step of several legs together."""
    base = probe.run_from_snapshot(snapshot, None)
    plant = copy.deepcopy(snapshot)
    ramp = int(round(probe.STEP_RAMP_S / 1e-3))
    hold = int(round(probe.HOLD_S / 1e-3))
    speed = np.zeros(4)
    speed[list(legs)] = probe.STEP_M / probe.STEP_RAMP_S
    pads = np.empty((ramp + hold, 4))
    for k in range(ramp + hold):
        pads[k] = probe.advance(plant, speed if k < ramp else np.zeros(4))[11:15]
    start = probe.STEP_RAMP_S + probe.HOLD2S_WINDOW_S[0]
    end = probe.STEP_RAMP_S + probe.HOLD2S_WINDOW_S[1]
    return (probe.window_mean(pads - base.pad_N, base.t_s, start, end) / 1e3).round(4).tolist()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("e2_summary", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--lock", default=None, choices=("l1r",))
    args = parser.parse_args()
    pin_to_e_cores()
    e2 = json.loads(args.e2_summary.read_text(encoding="utf-8"))
    base_N = np.asarray(e2["base_N_kN"]["FL"], float) * 1e3
    plant = probe.build_plant(BETA_PA, 1.0)
    lock_record = plant.set_lock_stiffness(args.lock) if args.lock else None
    stage_a = base_N - np.array([FRONT_GAIN_N, FRONT_GAIN_N, REAR_GAIN_N, REAR_GAIN_N])
    preparation = {"stage_a": preload_extend_only(plant, stage_a),
                   "state_after_a": probe.state_record(plant), "modes_after_a": lock_modes(plant)}
    preparation.update(stage_b_load_rear(plant, base_N[[FL, FR]].mean()))
    preparation.update(trim_rear(plant, base_N[[RL, RR]]))
    snapshot = copy.deepcopy(plant)
    record = {"lock": args.lock, "beta_Pa": BETA_PA, "lock_record": lock_record,
              "probe_file": probe.__file__, "rmf_file": probe.rmf.__file__,
              "chrono_base_kN": (base_N / 1e3).round(3).tolist(), "preparation": preparation,
              "state": probe.state_record(snapshot), "modes": lock_modes(snapshot),
              "rod_state": rod_state(snapshot), "measured": probe.measure_matrix(snapshot),
              "diag_pair_FR_RL_dF_kN": pair_step(snapshot, (FR, RL))}
    args.out.write_text(json.dumps(record, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"lock": args.lock, "state": record["state"]["pad_force_kN"],
                      "spheres": record["state"]["crawler_spheres_active"], "modes": record["modes"],
                      "modes_after_a": preparation["modes_after_a"]}))


if __name__ == "__main__":
    main()
