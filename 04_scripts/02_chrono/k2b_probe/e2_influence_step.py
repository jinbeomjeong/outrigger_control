"""K-2b E2: Chrono L1-R influence matrix S = dF_pad / ds_leg in a TOUCH-end-like static state.

Record / diagnosis only (no sealed judgement). Spec: ``06_analysis/02_control/k2/judgement/k2_dyn_sensitivity.md``
"메인 세션 권고" E2 (dynamics-expert 2026-11-11): top level, flat floor, crawler still carrying the machine, all four
pads touching (15-30 kN each), beta 1.0 (YAML), crawler kn x1; one leg +1 mm (ramp 0.5 s), hold 2 s.

Procedure (one process per case; the pre-load phase is deterministic, so every case starts from the same state and
the script records a hash of that state to prove it):

1. L1-R model (``OUTRIGGER_ROD_SIDE_MECHANICS=one_sided_parallel``) on the crawler, flat floor, restored from the
   settled snapshot ``07_results/states_L1R/S6_crawler_top_flat`` (legs unloaded; main checkout, read only).
2. Pre-load (open loop, per leg, ASSUMPTION of this probe): extend at v_max until the motor travel reaches
   gap - 5 mm, then at 1 mm/s until the pad normal force >= ``F_TARGET_N`` (22 kN), then stop (locks).
   Up to three top-up passes at 0.5 mm/s for any leg below ``F_TOPUP_N`` (15 kN) after a 1 s pause.
3. Settle ``SETTLE_S`` (3 s) with all commands 0; baseline = mean of the last 0.5 s.
4. Step: the case legs get the soft upper limit s_ref + 1 mm and the command 2 mm/s (1 mm in 0.5 s; the actuator
   brakes onto the soft limit), then 0; hold to 2.5 s after the step start; response = mean of the last 0.5 s.
   S[i, j] = (F_i(after) - F_i(base)) / (s_j(after) - s_j(base)) with s the motor position (leg extension).

Beta (``--beta`` 0.69 / 1.6 GPa, default 1.0 = YAML): the bundle-C plant path of ``run_S6C.py`` (pad ``kn`` from the
reference ``L1_beta_sensitivity_top/<beta>/k_L1_N_m``, ``actuator.oil_bulk_modulus_eff_Pa``; the L1-R machine
recomputes ``k_h`` / ``k_r``; crawler bushing kt held at the beta 1.0 ``(kt/kn)_pad`` ratio, C-R11; the snapshot is
re-tagged after the legs-unloaded check). beta 1.0 runs the unchanged E2 path.

Cases: ``FL``, ``FR``, ``RL``, ``RR`` (single legs = the four columns of S), ``diagFRRL`` (FR + RL together, P3
diagonal-pair check), ``common`` (all four, P3 common-mode check).

Outputs (``--out``/<case>/): ``result.json`` (identity, baseline, response, S column), ``series.npz`` (1 ms: t, pad
normal N (4), motor pos (4), s_ref (4), crawler normal sum and min, body roll / pitch, body rates, L1-R mode (4)).
Units SI (N, m, s, rad) unless the key says otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

os.environ["OUTRIGGER_ROD_SIDE_MECHANICS"] = "one_sided_parallel"
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MAIN = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))

import numpy as np  # noqa: E402

LEGS = ("FL", "FR", "RL", "RR")
CASES = {"FL": (0,), "FR": (1,), "RL": (2,), "RR": (3,), "diagFRRL": (1, 2), "common": (0, 1, 2, 3)}
SNAPSHOT = "S6_crawler_top_flat"
STATES = MAIN / "07_results" / "states_L1R"
F_TARGET_N = 22.0e3
F_TOPUP_N = 15.0e3
SLOW_M_S = 1.0e-3
TOPUP_M_S = 0.5e-3
NEAR_M = 5.0e-3
SETTLE_S = 3.0
STEP_M = 1.0e-3
STEP_RAMP_S = 0.5
STEP_TOTAL_S = 2.5
AVG_S = 0.5
PRELOAD_MAX_S = 60.0
BETA_KEYS = {0.69: "beta_6.9e+08", 1.0: "beta_1.0e+09", 1.6: "beta_1.6e+09"}
"""Keys of the reference block ``L1_beta_sensitivity_top`` (``run_S6C.BETA_KEYS``)."""
KN_KEY = "contact.rigid_floor.L1.kn_per_pad_N_m"


def kt_ratio(params) -> float:
    """Mean pad kt / kn (``run_S6C._crawler_kt_ratio``): the crawler bushing kt follows it, so a beta run scales the
    crawler kt back to the beta 1.0 value (C-R11, bundle C)."""
    kn = params.get(KN_KEY)
    kt = params.get("contact.rigid_floor.L1.kt_per_pad_N_m")
    return sum(float(kt[k]) / float(kn[k]) for k in kn) / len(kn)


def pin(mask: int) -> dict:
    import psutil

    cpus = [i for i in range(64) if mask >> i & 1]
    p = psutil.Process()
    p.cpu_affinity(cpus)
    return {"mask": hex(mask), "cpus": p.cpu_affinity()}


def git_head() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"unknown ({e})"


def body_rates(quat_wxyz, omega_world):
    w, x, y, z = quat_wxyz
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                  [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                  [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])
    return r.T @ np.asarray(omega_world, float)


class Recorder:
    def __init__(self, model):
        self.model = model
        self.rows = {k: [] for k in ("t", "N", "s", "s_ref", "cr_sum", "cr_min", "cr_n_pos", "rp", "rate", "mode")}
        self.mode = np.full(4, np.nan)
        model.rod_chamber.step_observers.append(self._obs)

    def _obs(self, step):
        self.mode = np.asarray(step.mode, dtype=float).copy()

    def sample(self, probe):
        from outrigger_sim.frames import roll_pitch_from_quat

        m = self.model
        cr = np.asarray(m.crawler_normals(), float)
        r = self.rows
        r["t"].append(probe.t_s)
        r["N"].append(np.asarray(m.bushing.normal_force_raw_N, float).copy())
        r["s"].append(np.asarray(probe.motor_pos_m, float).copy())
        r["s_ref"].append(np.asarray(m.actuator.acting_s_ref_m, float).copy())
        r["cr_sum"].append(float(cr.sum()))
        r["cr_min"].append(float(cr.min()))
        r["cr_n_pos"].append(int((cr > 0).sum()))
        r["rp"].append(np.asarray(roll_pitch_from_quat(probe.body_quat_wxyz), float))
        r["rate"].append(body_rates(probe.body_quat_wxyz, probe.body_omega_rad_s))
        r["mode"].append(self.mode.copy())

    def arrays(self):
        return {k: np.asarray(v) for k, v in self.rows.items()}


def run(case: str, out: Path, mask: int, beta_GPa: float = 1.0) -> dict:
    from outrigger_sim.params import load_params
    from outrigger_sim.record import load_snapshot

    import s6_stage2 as st

    placement = pin(mask)
    wall0 = time.perf_counter()
    base_params = load_params(level="top")
    beta_rec = {"beta_GPa": beta_GPa, "overrides": None, "crawler_bushing_kt_scale": None, "snapshot_retag": None}
    if beta_GPa == 1.0:  # the E2 (beta 1.0) path, unchanged
        params = base_params
        model, _ = st.build_crawler_model(params, "flat", attach=False)
        snap = load_snapshot(SNAPSHOT, params_sha256=params.sha256, directory=STATES)
    else:  # the bundle-C beta path of run_S6C (param_overrides / crawler_kt_scales, C-R11 crawler kt held)
        from outrigger_sim.verify.reference import BETA_K_L1_N_M, load_references
        from outrigger_sim.verify.s6_bundle_c import retag_snapshot

        key = BETA_KEYS[beta_GPa]
        kref = load_references().get(BETA_K_L1_N_M, beta=key)
        over = {f"{KN_KEY}.{leg}": float(v) for leg, v in zip(LEGS, kref, strict=True)}
        over["actuator.oil_bulk_modulus_eff_Pa"] = float(key.removeprefix("beta_"))
        params = load_params(level="top", overrides=over)
        kt_scale = kt_ratio(base_params) / kt_ratio(params)
        model, _ = st.build_crawler_model(params, "flat", attach=False, crawler_bushing_kt_scale=kt_scale)
        snap = load_snapshot(SNAPSHOT, params_sha256=base_params.sha256, directory=STATES)
        snap, retag = retag_snapshot(snap, params.sha256, name=SNAPSHOT)
        beta_rec.update(overrides=over, crawler_bushing_kt_scale=kt_scale, snapshot_retag=retag)
    from outrigger_sim.chrono.rod_chamber_link import leg_params_from_params

    lp, _ = leg_params_from_params(params)
    beta_rec["pad_stiffness_head_only_N_m"] = [float(x.pad_stiffness_head_only_N_m) for x in lp]
    beta_rec["pad_stiffness_locked_N_m"] = [float(x.pad_stiffness_locked_N_m) for x in lp]
    t0 = model.restore(snap)
    dt = model.dt_s
    every = max(1, round(1.0e-3 / dt))
    rec = Recorder(model)
    v_max = float(model.actuator.max_speed_m_s)
    gaps0 = np.asarray(st.pad_gaps_m(model), float)
    s_start = np.asarray(model.actuator.s_ref_m, float).copy()
    k = 0

    def step(u):
        nonlocal k
        model.set_command([float(x) for x in u])
        k += 1
        r = model.step(capture=(k % every == 0))
        if r.probe is not None:
            rec.sample(r.probe)

    def now():
        return float(model.system.GetChTime()) - t0

    # 2. pre-load
    phase = np.zeros(4, dtype=int)  # 0 approach, 1 slow, 2 done
    t_done = np.full(4, np.nan)
    while np.any(phase < 2):
        n = model.bushing.normal_force_raw_N
        s = model.actuator.s_ref_m
        u = np.zeros(4)
        for i in range(4):
            if phase[i] == 0 and s[i] - s_start[i] >= gaps0[i] - NEAR_M:
                phase[i] = 1
            if phase[i] == 1 and n[i] >= F_TARGET_N:
                phase[i] = 2
                t_done[i] = now()
            u[i] = v_max if phase[i] == 0 else SLOW_M_S if phase[i] == 1 else 0.0
        step(u)
        if now() > PRELOAD_MAX_S:
            raise RuntimeError(f"pre-load not finished in {PRELOAD_MAX_S} s: phase {phase}")
    topups = []
    for _p in range(3):
        for _ in range(round(1.0 / dt)):
            step(np.zeros(4))
        low = np.asarray(model.bushing.normal_force_raw_N) < F_TOPUP_N
        if not low.any():
            break
        topups.append({"t_s": now(), "legs": [LEGS[i] for i in np.flatnonzero(low)]})
        active = low.copy()
        while active.any():
            n = model.bushing.normal_force_raw_N
            active &= n < F_TARGET_N
            step(np.where(active, TOPUP_M_S, 0.0))
            if now() > PRELOAD_MAX_S + 20:
                raise RuntimeError("top-up not finished")
    # 3. settle
    for _ in range(round(SETTLE_S / dt)):
        step(np.zeros(4))
    a = rec.arrays()
    t_rel = a["t"] - t0
    t_step0 = now()
    base_win = t_rel >= t_step0 - AVG_S  # all samples so far are before the step
    base = {k2: a[k2][base_win].mean(axis=0) for k2 in ("N", "s", "cr_sum", "rp")}
    state_hash = hashlib.sha256(np.concatenate([a["N"][-1], a["s"][-1], a["rp"][-1]]).tobytes()).hexdigest()
    base_modes = a["mode"][-1].tolist()
    base_crawler_N = np.asarray(model.crawler_normals(), float).tolist()  # per sphere, end of the settle
    # 4. step
    legs = CASES[case]
    hi = np.asarray(model.actuator.stroke_range_m[:, 1], float).copy()
    s_ref = np.asarray(model.actuator.s_ref_m, float)
    for j in legs:
        hi[j] = s_ref[j] + STEP_M
    # other legs keep the full upper limit (they get command 0)
    model.actuator.set_soft_limits(hi_m=hi)
    u_step = np.zeros(4)
    for j in legs:
        u_step[j] = STEP_M / STEP_RAMP_S
    n_ramp = round((STEP_RAMP_S + 0.15) / dt)  # command ramp 0.1 s + brake margin; the soft limit ends the travel
    for i in range(round(STEP_TOTAL_S / dt)):
        step(u_step if i < n_ramp else np.zeros(4))
    a = rec.arrays()
    t_rel = a["t"] - t0
    t_end = now()
    resp_win = t_rel >= t_end - AVG_S
    base_win = (t_rel >= t_step0 - AVG_S) & (t_rel < t_step0)  # same samples as above, on the final arrays
    resp = {k2: a[k2][resp_win].mean(axis=0) for k2 in ("N", "s", "cr_sum", "rp")}
    dF = resp["N"] - base["N"]
    ds = resp["s"] - base["s"]
    step_win = t_rel >= t_step0
    col = None
    if len(legs) == 1:
        col = (dF / ds[legs[0]]).tolist()
    wall = time.perf_counter() - wall0
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "series.npz", t=t_rel, **{k2: v for k2, v in a.items() if k2 != "t"})
    res = {
        "experiment": "K-2b E2", "case": case, "legs_stepped": [LEGS[j] for j in legs],
        "record_only": True,
        "identity": {"git_head": git_head(), "script": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
                     "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     "python": sys.version.split()[0], "platform": platform.platform(),
                     "pychrono": __import__("pychrono").__version__ if hasattr(__import__("pychrono"), "__version__")
                     else "10.0.0", "params_sha256": params.sha256,
                     "rod_side_mechanics": os.environ["OUTRIGGER_ROD_SIDE_MECHANICS"],
                     "threads": {"OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
                                 "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"), "chrono": 1},
                     "placement": placement, "dt_s": dt,
                     "snapshot": f"07_results/states_L1R/{SNAPSHOT}",
                     "snapshot_npz_sha256": hashlib.sha256((STATES / f"{SNAPSHOT}.npz").read_bytes()).hexdigest()},
        "beta": beta_rec,
        "settings": {"F_target_N": F_TARGET_N, "F_topup_N": F_TOPUP_N, "slow_m_s": SLOW_M_S,
                     "approach_m_s": v_max, "near_m": NEAR_M, "settle_s": SETTLE_S, "step_m": STEP_M,
                     "step_ramp_s": STEP_RAMP_S, "step_total_s": STEP_TOTAL_S, "avg_window_s": AVG_S,
                     "beta_Pa": params.get("actuator.oil_bulk_modulus_eff_Pa"),
                     "kn_per_pad_N_m": dict(params.get("contact.rigid_floor.L1.kn_per_pad_N_m"))},
        "preload": {"gaps0_m": gaps0.tolist(), "t_latch_s": t_done.tolist(), "topups": topups,
                    "t_step_start_s": t_step0},
        "base": {k2: np.asarray(v).tolist() for k2, v in base.items()},
        "base_state_sha256": state_hash, "base_l1r_mode": base_modes, "base_crawler_normals_N": base_crawler_N,
        "end_crawler_normals_N": np.asarray(model.crawler_normals(), float).tolist(),
        "response": {k2: np.asarray(v).tolist() for k2, v in resp.items()},
        "dF_N": dF.tolist(), "ds_m": ds.tolist(),
        "S_column_kN_per_mm": None if col is None else [c * 1e-6 for c in col],
        "dF_per_mm_kN": (dF / (ds[list(legs)].mean()) * 1e-6).tolist(),
        "during_step": {"N_min_N": a["N"][step_win].min(axis=0).tolist(),
                        "N_max_N": a["N"][step_win].max(axis=0).tolist(),
                        "cr_n_pos_min": int(a["cr_n_pos"][step_win].min()),
                        "cr_n_pos_base": int(a["cr_n_pos"][base_win].min()),
                        "modes_seen": sorted({tuple(m) for m in a["mode"][step_win].tolist()})[:8]},
        "resp_window_N_ptp_N": np.ptp(a["N"][resp_win], axis=0).tolist(),
        "timing": {"wall_s": wall, "sim_s": now()},
    }
    (out / "result.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("case", choices=sorted(CASES))
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--mask", default="0x0FFF0000")
    ap.add_argument("--beta", type=float, default=1.0, choices=sorted(BETA_KEYS), help="GPa; 1.0 = YAML")
    a = ap.parse_args()
    res = run(a.case, a.out / a.case, int(a.mask, 16), a.beta)
    print(json.dumps({"case": res["case"], "dF_per_mm_kN": res["dF_per_mm_kN"], "wall_s": res["timing"]["wall_s"]}))


if __name__ == "__main__":
    main()
