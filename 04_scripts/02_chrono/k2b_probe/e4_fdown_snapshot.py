"""K-2b E4: rebuild the L1-R ``fdown3.5`` settled crawler start state with less residual crawler pitch-x sway.

Record / diagnosis only. Spec: ``06_analysis/02_control/k2/judgement/k2_dyn_sensitivity.md`` E4 / 4.2. The existing
``07_results/states_L1R/S6_crawler_top_fdown3.5`` (``s6_stage2.job_snapshot``: half-cosine in-plane gravity ramp
3.0 s + settle 65.5 s) keeps a 0.625 Hz, zeta ~0.004 sway, so the CHECK gyro window sees 0.020 deg/s RMS (limit
0.01 deg/s) and the C2 controller warns ``WARN_GYRO_BIAS_SKIPPED``.

Note on the ramp: the stage-2 ramp is the half-cosine ``(1 - cos(pi t / T)) / 2`` (``scenarios.slope.gravity_ramp``),
not a linear ramp. Its residual factor for an undamped mode f is ``|cos(pi f T)| / |1 - (2 f T)^2|``, zero at
``f T = 1.5, 2.5, ...`` (T = 2.4 / 4.0 / 5.6 s at 0.625 Hz), not at integer ``f T`` (the linear-ramp sinc zeros).

``build``: the ``job_snapshot`` procedure (analytic ``crawler_slope_pose``, crawler anchor bushings Q12 at zero
deformation, in-plane gravity ramp, settle) with the ramp shape / length and the settle length as arguments; the
snapshot is written under a NEW name into ``--states`` (refuses to overwrite). ``check``: restore a snapshot into a
fresh model, hold all commands 0 for ``--hold`` s (no controller), and report the deck body-axis roll / pitch rate
RMS about the mean over 2 s windows (the CHECK ``T_b`` window statistic without sensor noise) and the dominant
frequency / decay. Units SI; ``*_deg_s`` = deg/s.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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

LIMIT_RAD_S = math.radians(0.01)
WINDOW_S = 2.0


def ramp(shape: str, t: float, T: float) -> float:
    if t <= 0.0:
        return 0.0
    if t >= T:
        return 1.0
    x = t / T
    if shape == "halfcos":
        return 0.5 * (1.0 - math.cos(math.pi * x))
    if shape == "poly345":
        return x**3 * (10.0 - 15.0 * x + 6.0 * x * x)
    if shape == "linear":
        return x
    raise ValueError(shape)


def pin(mask: int) -> dict:
    import psutil

    p = psutil.Process()
    p.cpu_affinity([i for i in range(64) if mask >> i & 1])
    return {"mask": hex(mask), "cpus": p.cpu_affinity()}


def identity(params, placement, dt) -> dict:
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except Exception as e:  # noqa: BLE001
        head = f"unknown ({e})"
    return {"git_head": head, "script": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "python": sys.version.split()[0], "platform": platform.platform(), "pychrono": "10.0.0",
            "params_sha256": params.sha256, "rod_side_mechanics": os.environ["OUTRIGGER_ROD_SIDE_MECHANICS"],
            "threads": {"OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
                        "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
                        "OMP_WAIT_POLICY": os.environ.get("OMP_WAIT_POLICY"), "chrono": 1},
            "placement": placement, "dt_s": dt}


def body_rates(q, w_world):
    w, x, y, z = q
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                  [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                  [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])
    return r.T @ np.asarray(w_world, float)


def rate_stats(t, rates) -> dict:
    """2 s window RMS about the window mean (roll, pitch), windows starting every 0.1 s; FFT peak of pitch."""
    starts = np.arange(0.0, t[-1] - WINDOW_S + 1e-9, 0.1)
    rms = []
    for s in starts:
        m = (t >= s) & (t < s + WINDOW_S)
        w = rates[m]
        rms.append(np.sqrt(np.mean((w - w.mean(axis=0)) ** 2, axis=0)))
    rms = np.asarray(rms)
    first = rms[0]
    p = rates[:, 1] - rates[:, 1].mean()
    dtt = float(np.median(np.diff(t)))
    spec = np.abs(np.fft.rfft(p * np.hanning(p.size)))
    f = np.fft.rfftfreq(p.size, dtt)
    band = (f > 0.2) & (f < 6.0)
    fpk = float(f[band][np.argmax(spec[band])])
    half = t[-1] / 2
    a1 = np.ptp(p[t < half]) / 2
    a2 = np.ptp(p[t >= half]) / 2
    return {"first_window_rms_deg_s": np.degrees(first).tolist(),
            "first_window_pass": bool(first.max() <= LIMIT_RAD_S),
            "max_window_rms_deg_s": np.degrees(rms.max(axis=0)).tolist(),
            "min_window_rms_deg_s": np.degrees(rms.min(axis=0)).tolist(),
            "first_quiet_window_start_s": (float(starts[np.argmax(rms.max(axis=1) <= LIMIT_RAD_S)])
                                           if np.any(rms.max(axis=1) <= LIMIT_RAD_S) else None),
            "pitch_peak_hz": fpk, "pitch_amp_first_half_deg_s": math.degrees(a1),
            "pitch_amp_second_half_deg_s": math.degrees(a2),
            "mean_rate_deg_s": np.degrees(rates.mean(axis=0)).tolist(),
            "limit_deg_s": 0.01, "window_s": WINDOW_S}


def build(args) -> dict:
    from outrigger_sim.chrono.system import set_gravity
    from outrigger_sim.frames import roll_pitch_from_quat
    from outrigger_sim.params import load_params
    from outrigger_sim.record import save_snapshot
    from outrigger_sim.scenarios.crawler_slope import crawler_slope_pose
    from outrigger_sim.scenarios.slope import floor_normal, floor_rotation

    import s6_stage2 as st

    placement = pin(int(args.mask, 16))
    states = Path(args.states)
    if (states / f"{args.name}.npz").exists() or (states / f"{args.name}.meta.json").exists():
        raise SystemExit(f"{args.name} exists in {states}: refusing to overwrite")
    level, floor = "top", args.floor
    params = load_params(level=level)
    model, start = st.build_crawler_model(params, floor, attach=True)
    pose = crawler_slope_pose(params, *st.FLOORS[floor], tangential=True)
    rf = floor_rotation(floor_normal(*st.FLOORS[floor]))
    g_floor = rf.T @ np.array([0.0, 0.0, -params.meta.gravity_m_s2])

    def gvec(t):
        k = ramp(args.ramp_shape, t, args.ramp_s)
        return rf @ np.array([k * g_floor[0], k * g_floor[1], g_floor[2]])

    cb = model.crawler_bushing
    dt = model.dt_s
    n_ramp = round(args.ramp_s / dt)
    n_total = n_ramp + round(args.settle_s / dt)
    rows = {"t": [], "rp": [], "rate": []}
    wall0 = time.perf_counter()
    set_gravity(model.system, tuple(gvec(0.0)))
    for k in range(n_total):
        if k <= n_ramp:
            set_gravity(model.system, tuple(gvec(float(model.system.GetChTime()))))
        r = model.step(capture=(k % 5 == 4))
        if r.probe is not None:
            rows["t"].append(r.probe.t_s)
            rows["rp"].append(np.asarray(roll_pitch_from_quat(r.probe.body_quat_wxyz), float))
            rows["rate"].append(body_rates(r.probe.body_quat_wxyz, r.probe.body_omega_rad_s))
    wall = time.perf_counter() - wall0
    cb.assert_hold_released(f"snapshot {level}/{floor}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    arr = {k: np.asarray(v) for k, v in rows.items()}
    np.savez_compressed(out / "build_series.npz", **arr)
    procedure = (f"analytic crawler_slope_pose, crawler anchor bushings (Q12) at zero deformation, in-plane gravity "
                 f"ramp {args.ramp_shape} {args.ramp_s} s, settle {args.settle_s} s")
    path = save_snapshot(model.snapshot(), args.name, directory=states, overwrite=False,
                         note={"stage": "S6 stage 2 start (K-2b E4 rebuild)", "level": level, "floor": floor,
                               "floor_slope_deg": st.FLOORS[floor], "procedure": procedure,
                               "ramp_shape": args.ramp_shape, "ramp_s": args.ramp_s, "settle_s": args.settle_s,
                               "replaces_for_new_bundles": f"S6_crawler_{level}_{floor}",
                               "generator": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
                               "crawler_bushing": model.crawler_bushing_values.meta()})
    t = arr["t"] - arr["t"][0]
    last = t >= t[-1] - 10.0
    tail = rate_stats(t[last] - t[last][0], arr["rate"][last][:, :2])
    normals = np.asarray(model.crawler_normals())
    res = {"experiment": "K-2b E4 build", "name": args.name, "snapshot_path": str(path),
           "npz_sha256": hashlib.sha256((states / f"{args.name}.npz").read_bytes()).hexdigest(),
           "meta_sha256": hashlib.sha256((states / f"{args.name}.meta.json").read_bytes()).hexdigest(),
           "identity": identity(params, placement, dt), "procedure": procedure,
           "end_roll_pitch_deg": np.degrees(arr["rp"][-1]).tolist(),
           "analytic_roll_pitch_deg": [pose.body_roll_deg, pose.body_pitch_deg],
           "start_roll_pitch_deg": [start.body_roll_deg, start.body_pitch_deg],
           "crawler_normal_sum_N": float(normals.sum()),
           "last10s_build_rates": tail,
           "yield_steps_total": int(np.asarray(cb.yield_steps).sum()),
           "timing": {"wall_s": wall, "steps": n_total, "sim_s": n_total * dt}}
    (out / "build.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return res


def check(args) -> dict:
    from outrigger_sim.params import load_params
    from outrigger_sim.record import load_snapshot

    import k2_chrono_rows as k2c
    import s6_stage2 as st

    k2c.register_floors(st.FLOORS)
    placement = pin(int(args.mask, 16))
    states = Path(args.states)
    params = load_params(level="top")
    model, _ = st.build_crawler_model(params, args.floor, attach=False)
    snap = load_snapshot(args.name, params_sha256=params.sha256, directory=states)
    t0 = model.restore(snap)
    dt = model.dt_s
    rows = {"t": [], "rate": [], "s": []}
    wall0 = time.perf_counter()
    n = round(args.hold / dt)
    for k in range(n):
        model.set_command([0.0, 0.0, 0.0, 0.0])
        r = model.step(capture=(k % 5 == 4))
        if r.probe is not None:
            rows["t"].append(r.probe.t_s - t0)
            rows["rate"].append(body_rates(r.probe.body_quat_wxyz, r.probe.body_omega_rad_s))
    wall = time.perf_counter() - wall0
    t = np.asarray(rows["t"])
    rates = np.asarray(rows["rate"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / f"check_{args.name}.npz", t=t, rate=rates)
    res = {"experiment": "K-2b E4 check", "snapshot": args.name, "states": str(states),
           "npz_sha256": hashlib.sha256((states / f"{args.name}.npz").read_bytes()).hexdigest(),
           "snapshot_time_s": t0, "hold_s": args.hold, "identity": identity(params, placement, dt),
           "rates": rate_stats(t, rates[:, :2]), "timing": {"wall_s": wall}}
    (out / f"check_{args.name}.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--name", required=True)
    b.add_argument("--floor", default="fdown3.5")
    b.add_argument("--ramp-shape", choices=("halfcos", "poly345", "linear"), required=True)
    b.add_argument("--ramp-s", type=float, required=True)
    b.add_argument("--settle-s", type=float, required=True)
    c = sub.add_parser("check")
    c.add_argument("--name", required=True)
    c.add_argument("--floor", default="fdown3.5")
    c.add_argument("--hold", type=float, default=10.0)
    for p in (b, c):
        p.add_argument("--states", required=True)
        p.add_argument("--out", required=True)
        p.add_argument("--mask", default="0x0FFF0000")
    a = ap.parse_args()
    res = build(a) if a.cmd == "build" else check(a)
    keep = ("name", "snapshot", "npz_sha256", "rates", "last10s_build_rates", "timing")
    print(json.dumps({k: res[k] for k in keep if k in res}, default=float))


if __name__ == "__main__":
    main()
