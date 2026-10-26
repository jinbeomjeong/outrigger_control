"""S9 dual-terrain equivalence test E1 ... E4 (dynamics_model.md 5.34.12, rev. 49).

Single SCM terrain (pads + tracks, grid h) against the dual layout (pad terrain h + crawler terrain
h, U-S9G-1 mechanism) on a loaded-pad case: machine G1, pads start 3 mm above the SCM plane
(start extensions), gravity Poly345 over 0.5 s, all four legs extend at v_max from t = 0, so the
pads load while the crawler settles (pad + crawler loaded, 1.5 s).

Criteria (5.34.12):
  E1 determinism   each layout run twice (separate processes): all series bit-identical
  E2 no-event part series bit-identical between layouts up to the first step with a pad SCM force
  E3 end / integral last 0.1 s means of the normal sum, pad normals, z0: rel diff <= 1e-6 (pitch
                   abs <= 1e-5 deg); normal-sum impulse int sum F_n dt rel diff <= 1e-6
  E4 instant       per body max |F(t) diff| <= one node force sigma_bar h^2 of that body (pads:
                   end pad normal / pad area x h^2); end diff <= 1/100 of the max diff (decay)

Revised by dynamics 5.35.2 (user decision U-S9P-3, 2026-10-26):
  E2 bit identity only when the pads start outside the SCM ray window (bottom > plane + 0.1 m);
     inside it, every series before the first pad force within 1e-12 relative
  E3 pad normals: rel <= 1e-6 OR end diff <= 0.01 sigma_bar h^2
  E4 small-force bodies (max < 0.1 sigma_bar h^2, no own node event): end diff <= 0.01 sigma_bar h^2;
     crawler: basis = maximum node pressure x h^2 (``--crawler-sigma-max-Pa``), spike width
     <= 2 steps (steps over the mean-pressure node force) and z0 diff <= 1 um at the spikes

Usage (Chrono-dev, worktree root)::

    python -I -X utf8 -u 04_scripts/02_chrono/s9_dual_terrain_equivalence.py run --layout single --rep 1 --out <dir>
    python -I -X utf8 -u 04_scripts/02_chrono/s9_dual_terrain_equivalence.py judge --out <dir> [--json <file>]

Units SI; world = body axes at the start (x forward, z up); gravity (0, 0, -9.80665) m/s^2.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

G = 9.80665
T_END_S = 1.5
GRAVITY_RAMP_S = 0.5
START_CLEARANCE_M = 0.003
GRID_M = 0.02
SOIL = "G1"
PAD_VARIANT = "dwg_rear250"
KEYS = ("t", "crawler_n", "pad_n", "pad_f", "sup_f", "pitch_deg", "roll_deg", "z0")
# criteria revised by dynamics 5.35.2 (user decision U-S9P-3, 2026-10-26)
RAY_TEST_HEIGHT_M = 0.1
"""SCM ray test window above the plane (``SCMTerrain::SetTestHeight``, default 0.1 m; 5.35.2 E2)."""
E2_REL_IN_WINDOW = 1.0e-12
E3_REL = 1.0e-6
E3_NODE_FRACTION = 0.01
E4_SMALL_FRACTION = 0.1
CRAWLER_SIGMA_MAX_PA = 0.7e6
CRAWLER_SIGMA_BASIS = ("dynamics 5.35.2 E4: G1 crawler end node, sinkage about 4.7 mm, sigma about 0.7 MPa "
                       "(node force about 280 N at 2 cm); ASSUMPTION when not measured in the run")


def build(layout: str, threads: int, ext=None):
    from outrigger_sim.chrono.scm_model import S9Model, load_soil_set
    from outrigger_sim.pad_variants import apply_pad_variant, pad_variant_meta
    from outrigger_sim.params import load_params

    params = apply_pad_variant(load_params(level="top", model="L2b_NSC"), PAD_VARIANT)
    pv = pad_variant_meta(PAD_VARIANT, params=params)
    return S9Model(params, load_soil_set(SOIL), pv, grid_m=GRID_M, extensions_m=ext, num_threads=threads,
                   crawler_grid_m=GRID_M if layout == "dual" else None), params


def run(args) -> None:
    import run_S9  # noqa: PLC0415
    from outrigger_sim.chrono.scm_model import gravity_ramp_factor
    from outrigger_sim.frames import roll_pitch_from_quat

    placement = run_S9.place()
    probe_model, _ = build(args.layout, args.threads)
    clearance = -probe_model.pad_sinkage_m()  # pad bottom above the plane, legs hanging [m]
    del probe_model
    ext = [float(c - START_CLEARANCE_M) for c in clearance]
    model, params = build(args.layout, args.threads, ext)
    start_clear = (-model.pad_sinkage_m()).tolist()
    v = float(params.actuator.max_speed_m_s)
    n = model.normal_world
    rec = {k: [] for k in KEYS}
    dt = model.dt_s
    steps = round(T_END_S / dt)
    t0 = time.perf_counter()
    model.set_command([v] * 4)
    for k in range(steps):
        model.set_gravity_factor(gravity_ramp_factor(k * dt, GRAVITY_RAMP_S, "poly345"))
        p = model.step(capture=True)
        f = model.forces
        rec["t"].append((k + 1) * dt)
        rec["crawler_n"].append(float(f.sup_force_N @ n))
        rec["pad_n"].append((f.pad_force_N @ n).tolist())
        rec["pad_f"].append(f.pad_force_N.tolist())
        rec["sup_f"].append(f.sup_force_N.tolist())
        roll, pitch = roll_pitch_from_quat(p.body_quat_wxyz)[:2]
        rec["pitch_deg"].append(math.degrees(pitch))
        rec["roll_deg"].append(math.degrees(roll))
        rec["z0"].append(float(p.body_pos_m[2]))
    wall = time.perf_counter() - t0
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{args.layout}_rep{args.rep}"
    np.savez(out / f"{stem}.npz", **{k: np.asarray(v_, dtype=float) for k, v_ in rec.items()})
    meta = {"layout": args.layout, "rep": args.rep, "threads": model.num_threads, "grid_m": GRID_M,
            "soil": SOIL, "pad_variant": PAD_VARIANT, "dt_s": dt, "steps": steps, "wall_s": wall,
            "us_per_step": wall / steps * 1e6, "placement": placement, "start_extensions_m": ext,
            "start_clearance_m": start_clear, "terrain_layout": model.meta()["terrain_layout"],
            "lift_speed_m_s": v, "gravity_ramp_s": GRAVITY_RAMP_S}
    (out / f"{stem}.json").write_text(json.dumps(meta, indent=1), "utf-8")
    print(json.dumps({k: meta[k] for k in ("layout", "rep", "us_per_step", "start_clearance_m")}), flush=True)


def _load(out: Path, stem: str):
    z = np.load(out / f"{stem}.npz")
    return {k: z[k] for k in z.files}, json.loads((out / f"{stem}.json").read_text("utf-8"))


def _bitsame(a, b) -> bool:
    return all(np.array_equal(a[k], b[k]) for k in KEYS)


def judge(args) -> dict:
    out = Path(args.out)
    s1, ms1 = _load(out, "single_rep1")
    s2, _ = _load(out, "single_rep2")
    d1, md1 = _load(out, "dual_rep1")
    d2, _ = _load(out, "dual_rep2")
    t = s1["t"]
    dt = float(t[1] - t[0])
    res: dict = {"basis": "dynamics_model.md 5.34.12 E1-E4; case in the module docstring",
                 "case": {k: ms1[k] for k in ("soil", "pad_variant", "grid_m", "dt_s", "steps", "threads",
                                               "start_clearance_m", "lift_speed_m_s", "gravity_ramp_s")},
                 "cost_us_per_step": {"single": ms1["us_per_step"], "dual": md1["us_per_step"]}}
    res["E1"] = {"single_rep_bit_identical": _bitsame(s1, s2), "dual_rep_bit_identical": _bitsame(d1, d2)}
    res["E1"]["pass"] = res["E1"]["single_rep_bit_identical"] and res["E1"]["dual_rep_bit_identical"]
    loaded = np.any(np.abs(s1["pad_f"]).sum(axis=2) > 0.0, axis=1) | np.any(np.abs(d1["pad_f"]).sum(axis=2) > 0.0, axis=1)
    k_hit = int(np.argmax(loaded)) if loaded.any() else len(t)
    diff_any = np.zeros(len(t), dtype=bool)
    for k in KEYS:
        a, b = s1[k], d1[k]
        dd = (a != b)
        diff_any |= dd.reshape(len(t), -1).any(axis=1) if dd.ndim > 1 else dd
    k_diff = int(np.argmax(diff_any)) if diff_any.any() else None
    res["E2"] = {"t_first_pad_force_s": float(t[k_hit]) if k_hit < len(t) else None,
                 "bit_identical_before_first_pad_force": bool(k_diff is None or k_diff >= k_hit),
                 "t_first_difference_s": None if k_diff is None else float(t[k_diff]),
                 "t_first_crawler_force_s": float(t[int(np.argmax(np.abs(s1["crawler_n"]) > 0.0))]),
                 "crawler_force_max_rel_diff_before_first_pad_force": float(
                     np.abs(s1["sup_f"][:k_hit] - d1["sup_f"][:k_hit]).max() / max(np.abs(s1["sup_f"][:k_hit]).max(), 1e-30))
                 if k_hit > 0 else None,
                 "pitch_max_abs_diff_before_first_pad_force_deg": float(
                     np.abs(s1["pitch_deg"][:k_hit] - d1["pitch_deg"][:k_hit]).max()) if k_hit > 0 else None}
    # E2 applicability (5.35.2, U-S9P-3): bit identity only when the pads start outside the SCM ray
    # test window (pad bottom > plane + test height); inside it the pad nodes enter the hit map from
    # the start, the hit maps differ between layouts, and the criterion is a relative difference
    # <= 1e-12 of every series before the first pad force
    clear = float(min(ms1["start_clearance_m"]))
    in_window = clear <= RAY_TEST_HEIGHT_M
    pre = slice(0, k_hit)
    rel_pre = 0.0
    for k in ("crawler_n", "pad_n", "pad_f", "sup_f"):  # force series, relative to their maximum
        if k_hit == 0:
            break
        a, b = s1[k][pre], d1[k][pre]
        scale = max(float(np.abs(a).max()), 1e-30)
        rel_pre = max(rel_pre, float(np.abs(a - b).max()) / scale)
    kin_pre = ({k: float(np.abs(s1[k][pre] - d1[k][pre]).max()) for k in ("pitch_deg", "roll_deg", "z0")}
               if k_hit > 0 else {})
    res["E2"].update(pad_start_clearance_min_m=clear, ray_test_height_m=RAY_TEST_HEIGHT_M,
                     pads_in_ray_window=in_window, max_rel_diff_before_first_pad_force=rel_pre,
                     kinematic_abs_diff_before_first_pad_force=kin_pre,
                     criterion=("force series relative diff <= 1e-12 before the first pad force (pads in the ray "
                                "window, 5.35.2); kinematic abs diffs recorded (deg, m)"
                                if in_window else "bit-identical before the first pad force (pads outside the window)"))
    res["E2"]["pass"] = (bool(rel_pre <= E2_REL_IN_WINDOW) if in_window
                         else res["E2"]["bit_identical_before_first_pad_force"])
    win = t >= t[-1] - 0.1 - 1e-12

    def rel(a, b):
        return float(abs(a - b) / max(abs(b), 1e-30))

    ns_s = s1["crawler_n"] + s1["pad_n"].sum(axis=1)
    ns_d = d1["crawler_n"] + d1["pad_n"].sum(axis=1)
    h = float(ms1["grid_m"])
    from outrigger_sim.pad_variants import pad_variant_meta
    from outrigger_sim.params import LEG_ORDER

    area = pad_variant_meta(PAD_VARIANT)["pad_bottom_area_m2"]
    # mean node force sigma_bar h^2 per pad (end pad normal / pad area x h^2)
    pad_node_f = [float(abs(s1["pad_n"][win, i].mean()) / float(area[leg]) * h * h) for i, leg in enumerate(LEG_ORDER)]
    pad_end_diff = [float(abs(d1["pad_n"][win, i].mean() - s1["pad_n"][win, i].mean())) for i in range(4)]
    e3 = {"normal_sum_rel": rel(ns_d[win].mean(), ns_s[win].mean()),
          "pad_normal_rel": [rel(d1["pad_n"][win, i].mean(), s1["pad_n"][win, i].mean()) for i in range(4)],
          "pad_normal_end_diff_N": pad_end_diff,
          "pad_normal_end_diff_over_node_force": [d / f if f > 0 else None for d, f in zip(pad_end_diff, pad_node_f, strict=True)],
          "z0_rel": rel(d1["z0"][win].mean(), s1["z0"][win].mean()),
          "pitch_abs_deg": float(abs(d1["pitch_deg"][win].mean() - s1["pitch_deg"][win].mean())),
          "impulse_single_N_s": float(ns_s.sum() * dt), "impulse_dual_N_s": float(ns_d.sum() * dt)}
    e3["impulse_rel"] = rel(e3["impulse_dual_N_s"], e3["impulse_single_N_s"])
    # 5.35.2 (U-S9P-3): a pad passes with rel <= 1e-6 OR end diff <= 0.01 sigma_bar h^2 (node-event tail)
    e3["pad_pass"] = [bool(r <= E3_REL or d <= E3_NODE_FRACTION * f)
                      for r, d, f in zip(e3["pad_normal_rel"], pad_end_diff, pad_node_f, strict=True)]
    e3["criterion"] = ("normal sum, z0, impulse rel <= 1e-6, pitch <= 1e-5 deg; pads rel <= 1e-6 or end diff <= "
                       "0.01 sigma_bar h^2 (5.35.2)")
    e3["pass"] = bool(e3["normal_sum_rel"] <= E3_REL and all(e3["pad_pass"]) and e3["z0_rel"] <= E3_REL
                      and e3["pitch_abs_deg"] <= 1e-5 and e3["impulse_rel"] <= E3_REL)
    res["E3"] = e3
    bodies = []
    for i, leg in enumerate(LEG_ORDER):
        df = np.linalg.norm(d1["pad_f"][:, i] - s1["pad_f"][:, i], axis=1)
        bodies.append({"body": f"pad_{leg}", "max_diff_N": float(df.max()), "t_max_s": float(t[int(np.argmax(df))]),
                       "end_diff_N": float(df[-1]), "node_force_N": pad_node_f[i],
                       "node_force_basis": "end pad normal / pad area x h^2 (mean node force)"})
    df = np.linalg.norm(d1["sup_f"] - s1["sup_f"], axis=1)
    # crawler (5.35.2 E4): basis = maximum node pressure x h^2 (the crawler pressure is uneven under pitch);
    # the former mean-pressure basis (max crawler normal / 2.592 m^2 x h^2) is kept as the spike threshold
    sup_mean_f = float(np.abs(s1["crawler_n"]).max()) / 2.592 * h * h
    sigma_max = float(args.crawler_sigma_max_Pa)
    spike = df > sup_mean_f
    runs, run = [], 0
    for on in spike:
        run = run + 1 if on else 0
        if on:
            runs.append(run)
    spike_width = max(runs) if runs else 0
    dz_spike = float(np.abs(d1["z0"][spike] - s1["z0"][spike]).max()) if spike.any() else 0.0
    bodies.append({"body": "superstructure (crawler)", "max_diff_N": float(df.max()), "t_max_s": float(t[int(np.argmax(df))]),
                   "end_diff_N": float(df[-1]), "node_force_N": sigma_max * h * h,
                   "node_force_basis": f"max node pressure {sigma_max:g} Pa x h^2 ({args.crawler_sigma_basis})",
                   "mean_pressure_node_force_N": sup_mean_f,
                   "spike_steps_over_mean_node_force": int(spike.sum()), "spike_width_steps_max": spike_width,
                   "z0_abs_diff_at_spikes_m": dz_spike,
                   "crawler_normal_max_N": float(np.abs(s1["crawler_n"]).max()),
                   "crawler_normal_end_N": float(s1["crawler_n"][-1])})
    for b in bodies:
        nf = b["node_force_N"]
        b["max_over_node_force"] = b["max_diff_N"] / nf if nf > 0 else None
        b["end_over_max"] = b["end_diff_N"] / b["max_diff_N"] if b["max_diff_N"] > 0 else 0.0
        b["pass_max"] = bool(b["max_diff_N"] <= nf)
        if b["body"].startswith("superstructure"):
            b["small_force_body"] = False
            b["event_body"] = bool(b["max_diff_N"] >= 0.01 * nf)
            b["pass_decay"] = bool(b["end_over_max"] <= 1e-2) if b["event_body"] else None
            b["pass_spike"] = bool(b["spike_width_steps_max"] <= 2 and b["z0_abs_diff_at_spikes_m"] <= 1e-6)
            b["criterion"] = "max <= max node pressure h^2, spike width <= 2 steps, z0 diff <= 1 um at spikes (5.35.2)"
            b["pass"] = bool(b["pass_max"] and b["pass_spike"] and (b["pass_decay"] is not False))
            continue
        # 5.35.2: a body without its own node event (max < 0.1 sigma_bar h^2) is judged on the end diff
        b["small_force_body"] = bool(b["max_diff_N"] < E4_SMALL_FRACTION * nf)
        if b["small_force_body"]:
            b["event_body"] = False
            b["pass_decay"] = None
            b["pass_end"] = bool(b["end_diff_N"] <= E3_NODE_FRACTION * nf)
            b["criterion"] = "small-force body: end diff <= 0.01 sigma_bar h^2 (5.35.2)"
            b["pass"] = bool(b["pass_max"] and b["pass_end"])
        else:
            b["event_body"] = bool(b["max_diff_N"] >= 0.01 * nf)
            b["pass_decay"] = bool(b["end_over_max"] <= 1e-2) if b["event_body"] else None
            b["criterion"] = "max <= sigma_bar h^2, end / max <= 1/100"
            b["pass"] = bool(b["pass_max"] and (b["pass_decay"] is not False))
    res["E4"] = {"bodies": bodies, "pass": all(b["pass"] for b in bodies)}
    res["pass_all"] = all(res[k]["pass"] for k in ("E1", "E2", "E3", "E4"))
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1), "utf-8")
    print(json.dumps(res, indent=1))
    return res


def main(argv) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="action", required=True)
    r = sub.add_parser("run")
    r.add_argument("--layout", choices=("single", "dual"), required=True)
    r.add_argument("--rep", type=int, default=1)
    r.add_argument("--threads", type=int, default=4)
    r.add_argument("--out", required=True)
    j = sub.add_parser("judge")
    j.add_argument("--out", required=True)
    j.add_argument("--json", default=None)
    j.add_argument("--crawler-sigma-max-Pa", type=float, default=CRAWLER_SIGMA_MAX_PA,
                   help="maximum crawler node pressure for the E4 crawler basis [Pa]")
    j.add_argument("--crawler-sigma-basis", default=CRAWLER_SIGMA_BASIS)
    a = ap.parse_args(argv)
    run(a) if a.action == "run" else judge(a)


if __name__ == "__main__":
    main(sys.argv[1:])
