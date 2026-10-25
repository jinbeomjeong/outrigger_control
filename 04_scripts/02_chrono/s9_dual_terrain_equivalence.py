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
    res["E2"]["pass"] = res["E2"]["bit_identical_before_first_pad_force"]
    win = t >= t[-1] - 0.1 - 1e-12

    def rel(a, b):
        return float(abs(a - b) / max(abs(b), 1e-30))

    ns_s = s1["crawler_n"] + s1["pad_n"].sum(axis=1)
    ns_d = d1["crawler_n"] + d1["pad_n"].sum(axis=1)
    e3 = {"normal_sum_rel": rel(ns_d[win].mean(), ns_s[win].mean()),
          "pad_normal_rel": [rel(d1["pad_n"][win, i].mean(), s1["pad_n"][win, i].mean()) for i in range(4)],
          "z0_rel": rel(d1["z0"][win].mean(), s1["z0"][win].mean()),
          "pitch_abs_deg": float(abs(d1["pitch_deg"][win].mean() - s1["pitch_deg"][win].mean())),
          "impulse_single_N_s": float(ns_s.sum() * dt), "impulse_dual_N_s": float(ns_d.sum() * dt)}
    e3["impulse_rel"] = rel(e3["impulse_dual_N_s"], e3["impulse_single_N_s"])
    e3["pass"] = bool(e3["normal_sum_rel"] <= 1e-6 and max(e3["pad_normal_rel"]) <= 1e-6 and e3["z0_rel"] <= 1e-6
                      and e3["pitch_abs_deg"] <= 1e-5 and e3["impulse_rel"] <= 1e-6)
    res["E3"] = e3
    h = float(ms1["grid_m"])
    from outrigger_sim.pad_variants import pad_variant_meta
    from outrigger_sim.params import LEG_ORDER

    area = pad_variant_meta(PAD_VARIANT)["pad_bottom_area_m2"]
    bodies = []
    for i, leg in enumerate(LEG_ORDER):
        df = np.linalg.norm(d1["pad_f"][:, i] - s1["pad_f"][:, i], axis=1)
        node_f = float(abs(s1["pad_n"][win, i].mean()) / float(area[leg]) * h * h)
        bodies.append({"body": f"pad_{leg}", "max_diff_N": float(df.max()), "t_max_s": float(t[int(np.argmax(df))]),
                       "end_diff_N": float(df[-1]), "node_force_N": node_f})
    df = np.linalg.norm(d1["sup_f"] - s1["sup_f"], axis=1)
    # the crawler unloads in this case (pads take the machine): node force from the crawler maximum
    sup_sigma = float(np.abs(s1["crawler_n"]).max()) / 2.592  # crawler contact area of the Chrono phase (5.34.11)
    bodies.append({"body": "superstructure (crawler)", "max_diff_N": float(df.max()), "t_max_s": float(t[int(np.argmax(df))]),
                   "end_diff_N": float(df[-1]), "node_force_N": sup_sigma * h * h,
                   "node_force_basis": "max crawler normal / 2.592 m^2 (2 cm Chrono-phase contact area, 5.34.11) x h^2",
                   "crawler_normal_max_N": float(np.abs(s1["crawler_n"]).max()),
                   "crawler_normal_end_N": float(s1["crawler_n"][-1])})
    for b in bodies:
        b["max_over_node_force"] = b["max_diff_N"] / b["node_force_N"] if b["node_force_N"] > 0 else None
        b["end_over_max"] = b["end_diff_N"] / b["max_diff_N"] if b["max_diff_N"] > 0 else 0.0
        # decay test only meaningful for a body with a node event (max diff >= 1 % of a node force)
        b["event_body"] = bool(b["max_diff_N"] >= 0.01 * b["node_force_N"])
        b["pass_max"] = bool(b["max_diff_N"] <= b["node_force_N"])
        b["pass_decay"] = bool(b["end_over_max"] <= 1e-2) if b["event_body"] else None
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
    a = ap.parse_args(argv)
    run(a) if a.action == "run" else judge(a)


if __name__ == "__main__":
    main(sys.argv[1:])
