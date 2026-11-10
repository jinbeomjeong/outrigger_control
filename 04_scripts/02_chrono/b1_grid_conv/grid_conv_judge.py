"""B1 pre-seal check: single-pad SCM grid convergence (J2, pad type B), coarse vs fine grid.

Reads two ``run_S9.py single-pad --load-steps <f1>,1.0`` result folders (same leg / soil / load
schedule, grids 0.02 m and 0.01 m) and computes, per grid (all lengths positive = deeper):

* ``z1`` / ``z2``: pad geometric sinkage (``-z_bottom_m``, YAML pad bottom; type B OBJ offset 0)
  at the end of the hold of load level 0 (N1) and level 1 (N2), from ``load_steps.levels[*].end``;
* ``dz = z2 - z1`` (the post-LOC sinkage increment N1 -> N2);
* steady check per hold: sinkage change over the last 1 s of the hold (``node_series``, 0.1 s)
  and SCM normal force / applied load at the hold end;
* node diagnostics at each hold end: contact nodes n, effective area ``A_eff = n d^2``, patch
  ``b = 2 A_hull / P_hull`` and the static Bekker reference ``z_B = (N / (A_eff (Kc/b + Kphi)))^(1/n)``
  (J2 set of the run's result.json), with the residual ``z - z_B``.

Prediction (user value 2026-11-10, recorded before the main run): rear pad
``|z2(fine) - z2(coarse)| <= 4 mm`` and ``|dz(fine) - dz(coarse)| <= 2 mm``. The absolute
difference is also given at N1. Exit 0 = both within, 1 = at least one outside, 2 = input error.
Last stdout line = JSON summary. ``--out`` writes the full JSON.

Run (Chrono-dev, no Chrono import):
    python -I 04_scripts/02_chrono/b1_grid_conv/grid_conv_judge.py <coarse_dir> <fine_dir> [--out x.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ABS_LIMIT_M = 4.0e-3
DZ_LIMIT_M = 2.0e-3
STEADY_RATE_LIMIT_M_S = 1.0e-4
"""Hold-end steadiness flag: |sinkage change over the last 1 s| < 0.1 mm."""


def _fail(msg: str) -> None:
    print(json.dumps({"error": msg}))
    raise SystemExit(2)


def grid_row(folder: Path) -> dict:
    p = folder / "result.json"
    if not p.is_file():
        _fail(f"missing {p}")
    r = json.loads(p.read_text(encoding="utf-8"))
    ls = r.get("load_steps")
    if not ls or len(ls.get("levels") or []) < 2 or any(v is None for v in ls["levels"][:2]):
        _fail(f"{folder}: no two completed load levels (run with --load-steps f1,1.0)")
    meta = r["meta"]
    soil = meta["scm"]["SetSoilParameters"]
    d = float(meta["scm"]["grid_m"])
    nodes = r.get("node_series") or []
    out = {"folder": str(folder), "grid_m": d, "leg": meta["leg"], "soil_key": meta["scm"]["soil"]["key"],
           "pad_variant": r["args"]["pad_variant"], "normal_load_N": meta["normal_load_N"],
           "num_threads_chrono": meta["num_threads_chrono"], "dt_s": r["args"]["dt"],
           "hull_hook": {k: (r.get("hull_hook") or {}).get(k) for k in ("mode", "fallback_reason", "dll_sha_validated")},
           "placement": {k: r["placement"].get(k) for k in ("mode", "affinity_logical_processors", "omp_wait_policy")},
           "wall_s": r["wall_s"], "us_per_step": r["us_per_step"], "levels": []}
    for lv, sched in zip(ls["levels"][:2], ls["schedule"][:2], strict=True):
        e = lv["end"]
        n_ = e["nodes"]
        z = -float(e["z_bottom_m"])
        N = float(e["load_N"])
        t_end = float(e["t_s"])
        last = [row for row in nodes if t_end - 1.0 - 1e-9 <= row["t_s"] <= t_end + 1e-9]
        dz_last = (last[-1]["sinkage_geometric_m"] - last[0]["sinkage_geometric_m"]) if len(last) >= 2 else None
        a_eff = n_["n_contact"] * d * d
        b = (2.0 * n_["contact_hull_area_m2"] / n_["contact_hull_perimeter_m"]
             if n_.get("contact_hull_area_m2") and n_.get("contact_hull_perimeter_m") else None)
        z_b = (N / (a_eff * (soil["Kc"] / b + soil["Kphi"]))) ** (1.0 / soil["n"]) if (b and a_eff > 0) else None
        out["levels"].append({
            "level": lv["level"], "factor": sched["factor"], "load_N": N, "t_hold_end_s": t_end,
            "hold_s": sched["hold_s"], "z_m": z, "Fz_scm_over_load": float(e["Fz_scm_N"]) / N,
            "sinkage_change_last_1s_m": dz_last,
            "steady": None if dz_last is None else abs(dz_last) < STEADY_RATE_LIMIT_M_S,
            "n_contact": n_["n_contact"], "A_eff_m2": a_eff, "b_patch_m": b, "z_bekker_ref_m": z_b,
            "z_minus_bekker_ref_m": None if z_b is None else z - z_b,
            "node_minus_geometric_m": n_.get("node_minus_geometric_m")})
    out["z1_m"], out["z2_m"] = out["levels"][0]["z_m"], out["levels"][1]["z_m"]
    out["dz_m"] = out["z2_m"] - out["z1_m"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("coarse", type=Path, help="result folder, grid 0.02 m")
    ap.add_argument("fine", type=Path, help="result folder, grid 0.01 m")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    c, f = grid_row(a.coarse), grid_row(a.fine)
    same = ("leg", "soil_key", "pad_variant", "normal_load_N", "num_threads_chrono", "dt_s")
    diff_keys = [k for k in same if c[k] != f[k]]
    if diff_keys:
        _fail(f"runs differ in {diff_keys}")
    if not f["grid_m"] < c["grid_m"]:
        _fail(f"fine grid {f['grid_m']} must be smaller than coarse {c['grid_m']}")
    if [lv["factor"] for lv in c["levels"]] != [lv["factor"] for lv in f["levels"]]:
        _fail("load schedules differ")
    d_abs2 = f["z2_m"] - c["z2_m"]
    d_abs1 = f["z1_m"] - c["z1_m"]
    d_dz = f["dz_m"] - c["dz_m"]
    ok_abs, ok_dz = abs(d_abs2) <= ABS_LIMIT_M, abs(d_dz) <= DZ_LIMIT_M
    res = {"rule": "B1 pre-seal single-pad grid convergence (prediction: |dz_abs| <= 4 mm, |d(dz)| <= 2 mm)",
           "units": "m (sinkage positive deeper), N, s",
           "coarse": c, "fine": f,
           "abs_diff_N2_m": d_abs2, "abs_diff_N1_m": d_abs1, "dz_diff_m": d_dz,
           "abs_within": ok_abs, "dz_within": ok_dz,
           "all_steady": all(lv["steady"] for g in (c, f) for lv in g["levels"]),
           "Richardson_p1_z2_m": f["z2_m"] + (f["z2_m"] - c["z2_m"]) * (f["grid_m"] / (c["grid_m"] - f["grid_m"])),
           "Richardson_note": "first-order extrapolation from two grids only; quantisation is not smooth in d, "
                              "read as an indication"}
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    short = {"abs_diff_N2_mm": round(d_abs2 * 1e3, 3), "abs_diff_N1_mm": round(d_abs1 * 1e3, 3),
             "dz_diff_mm": round(d_dz * 1e3, 3), "z2_mm": [round(c["z2_m"] * 1e3, 2), round(f["z2_m"] * 1e3, 2)],
             "dz_mm": [round(c["dz_m"] * 1e3, 2), round(f["dz_m"] * 1e3, 2)], "abs_within": ok_abs,
             "dz_within": ok_dz, "all_steady": res["all_steady"]}
    print(json.dumps(short))
    return 0 if (ok_abs and ok_dz) else 1


if __name__ == "__main__":
    sys.exit(main())
