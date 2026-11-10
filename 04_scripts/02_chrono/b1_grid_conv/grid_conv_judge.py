"""B1-GRIDCONV metrics (cad-side companion of the sealed plan ``06_analysis/02_control/b1/b1_gridconv_plan.md``).

Single-pad SCM grid convergence, J2 pad type B, grid 0.01 vs 0.005 m, rows GC-1..GC-4 (plan 3.2):
RL pair GC-1 (0.01) / GC-2 (0.005), FL pair GC-3 (0.01) / GC-4 (0.005). Reads the
``run_S9.py single-pad`` result folders ``<batch>/<case>/result.json`` and computes (plan 1, 3.3, 4):

* row validity V-1 (two load levels, end time >= 21 s), V-2 (threads 4, OMP PASSIVE, grid, J2 values,
  plane point 0, hull hook fast; argv checked key by key against plan 3.2), V-3 (N_h >= 3 and b_hull at both
  hold ends);
* per row and hold end k (levels[k].end): ``z_ref = (Fz_scm / (N_h d^2 (Kc/b_hull + Kphi)))^(1/n)``,
  ``f = [N_h d^2 (Kc/b_hull + Kphi) / (A (Kc/b_poly + Kphi))]^(-1/n)`` (A, b_poly from
  ``02_params/pad_variants.json``; A also checked against ``meta.pad_area_m2``);
* G-1 ``eps1 = n |z_node - z_ref| / z_node`` (z_node = ``sinkage_mean_contact_m``) <= 0.5 % (8 values, gate);
* G-2 ``|z/f (0.01) - z/f (0.005)|`` (z = ``sinkage_geometric_m``) <= 1 mm (4 values, gate);
* G-3 ``|dz/z2 (0.01) - dz/z2 (0.005)|`` <= 0.002 (2 values, gate);
* G-4 raw: z2, dz, z1 differences, f1, f2, N_h, b_hull per row; prediction check E-5..E-8 +-0.5 mm;
* G-5 ``max_t |r_0.01(t) - r_0.005(t)|``, ``r = (z(t) - z1) / (z2 - z1)``, t in [11.0, 21.0] s on the
  ``node_series`` 0.1 s samples (same times), <= 0.05 (flag only).

Verdict: UNDETERMINED (batch not COMPLETE) / REJECT (G-1 fail or G-2 > 1 mm) / HOLD (G-3 fail) / PASS.
Comparisons on unrounded doubles. Exit 0 PASS, 1 REJECT/HOLD, 3 UNDETERMINED, 2 input error.
Last stdout line = JSON summary; ``--out`` writes the full JSON.

Run (Chrono-dev or any Python with numpy; no Chrono import):
    python -I 04_scripts/02_chrono/b1_grid_conv/grid_conv_judge.py <batch_folder> [--out metrics.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
G1_LIMIT = 0.005
G2_LIMIT_M = 1.0e-3
G3_LIMIT = 0.002
G5_LIMIT = 0.05
PRED_TOL_M = 0.5e-3
T_HOLD_END_S = (11.0, 21.0)
J2 = {"Kphi": 1724690.0, "Kc": 16430.0, "n": 0.2, "cohesion": 0.0, "friction": 0.0, "Janosi": 0.01,
      "elastic_K": 2.0e8, "damping_R": 1103000.0}
"""SetSoilParameters of J2 in the bprime shear mode (c = phi = 0 in SCM; plan 1 table)."""
ROWS = {  # plan 3.2
    "GC-1": dict(case="GC1_J2_B_RL_1cm", leg="RL", grid=0.01, normal_load=74850.0, load_steps="0.97327989,1.0"),
    "GC-2": dict(case="GC2_J2_B_RL_0p5cm", leg="RL", grid=0.005, normal_load=74850.0, load_steps="0.97327989,1.0"),
    "GC-3": dict(case="GC3_J2_B_FL_1cm", leg="FL", grid=0.01, normal_load=122010.0, load_steps="0.98016556,1.0"),
    "GC-4": dict(case="GC4_J2_B_FL_0p5cm", leg="FL", grid=0.005, normal_load=122010.0, load_steps="0.98016556,1.0"),
}
COMMON_ARGS = dict(action="single-pad", soil="J2", pad_variant="dwg_rear250", level="top", joint="fixed", threads=4,
                   load_ramp=3.0, step_ramp=2.0, step_hold="8", scm_shear="bprime", stiffness_mode="series",
                   ray_shape="mesh", dt=1.0e-4, k_sw=1.5e4, terrain_size=[1.2, 1.2], force=0.0)
PAIRS = {"RL": ("GC-1", "GC-2"), "FL": ("GC-3", "GC-4")}
PRED = {"RL": {"z2_diff_m": 2.7e-3, "dz_diff_m": 0.35e-3}, "FL": {"z2_diff_m": -0.80e-3, "dz_diff_m": -0.08e-3}}
"""Plan 5 E-5..E-8 (fine-coarse sign: value(0.01) - value(0.005))."""


def k_of(b: float) -> float:
    return J2["Kc"] / b + J2["Kphi"]


def load_row(batch: Path, rid: str, spec: dict, pads: dict) -> dict:
    out: dict = {"id": rid, "case": spec["case"], "status": "VALID", "reasons": []}
    p = batch / spec["case"] / "result.json"
    if not p.is_file():
        out.update(status="MISSING", reasons=[f"no {p}"])
        return out
    r = json.loads(p.read_text(encoding="utf-8"))
    ls = r.get("load_steps") or {}
    levels = ls.get("levels") or []
    t_end = r["args"].get("t_end")
    if len(levels) != 2 or any(lv is None or "end" not in lv for lv in levels) or (t_end or 0.0) < 21.0 - 1e-6:
        out.update(status="MISSING", reasons=["V-1: two completed load levels to >= 21 s required"])
        return out
    a = r["args"]
    meta = r["meta"]
    want = dict(COMMON_ARGS, leg=spec["leg"], grid=spec["grid"], normal_load=spec["normal_load"],
                load_steps=spec["load_steps"], case=spec["case"])
    for key, val in want.items():
        if a.get(key) != val:
            out["reasons"].append(f"V-2 args.{key} = {a.get(key)!r}, plan {val!r}")
    if meta.get("num_threads_chrono") != 4:
        out["reasons"].append("V-2 num_threads_chrono != 4")
    if (r.get("placement") or {}).get("omp_wait_policy") != "PASSIVE":
        out["reasons"].append("V-2 OMP_WAIT_POLICY != PASSIVE")
    scm = meta["scm"]
    if abs(float(scm["grid_m"]) - spec["grid"]) > 1e-12:
        out["reasons"].append("V-2 grid_m")
    if any(abs(float(scm["SetSoilParameters"][k]) - v) > 1e-9 * max(1.0, abs(v)) for k, v in J2.items()):
        out["reasons"].append("V-2 SetSoilParameters != J2 (bprime)")
    if any(abs(float(v)) > 1e-12 for v in scm.get("plane_point_world_m", [1.0])):
        out["reasons"].append("V-2 plane_point_world_m != 0")
    hh = r.get("hull_hook") or {}
    if not (hh.get("requested") == "fast" and hh.get("mode") == "fast" and hh.get("fallback_reason") is None):
        out["reasons"].append(f"V-2 hull_hook requested {hh.get('requested')} effective {hh.get('mode')}")
    leg = spec["leg"]
    A, b_poly = pads[leg]["bottom_area_m2"], pads[leg]["bekker_b_m"]
    if abs(float(meta["pad_area_m2"]) - A) > 1e-9:
        out["reasons"].append(f"V-2 meta.pad_area_m2 {meta['pad_area_m2']} != table {A}")
    # V-2 pad xy offset 0: the level rows hold no pad xy; the 1 ms series of the share body (rotation and
    # translation of the pad locked to it by --joint fixed) starts at x = y = 0 -> checked from series.npz
    sp = batch / spec["case"] / "series.npz"
    xy0 = None
    if sp.is_file():
        import numpy as np  # noqa: PLC0415

        s = np.load(sp)
        xy0 = [float(s["x"][0]), float(s["y"][0])]
        if max(abs(xy0[0]), abs(xy0[1])) > 1e-9:
            out["reasons"].append(f"V-2 pad xy at first record {xy0}")
    else:
        out["reasons"].append("V-2 series.npz missing (pad xy offset not checkable)")
    out["pad_xy_first_record_m"] = xy0
    if out["reasons"]:
        out["status"] = "INVALID"
    d = spec["grid"]
    holds = []
    for k, lv in enumerate(levels):
        e = lv["end"]
        nd = e["nodes"]
        h = {"k": k + 1, "t_s": float(e["t_s"]), "load_N": float(e["load_N"]), "Fz_scm_N": float(e["Fz_scm_N"]),
             "z_geo_m": float(nd["sinkage_geometric_m"]), "z_node_m": nd.get("sinkage_mean_contact_m"),
             "N_h": int(nd["n_contact"]), "A_hull_m2": nd.get("contact_hull_area_m2"),
             "P_hull_m": nd.get("contact_hull_perimeter_m")}
        if abs(h["t_s"] - T_HOLD_END_S[k]) > 1e-6:
            out["reasons"].append(f"V-1 hold end {k + 1} at {h['t_s']} s, plan {T_HOLD_END_S[k]}")
            out["status"] = "INVALID"
        if h["N_h"] < 3 or not h["A_hull_m2"] or not h["P_hull_m"] or h["z_node_m"] is None:
            out["reasons"].append(f"V-3 hold end {k + 1}: N_h {h['N_h']}, hull {h['A_hull_m2']}")
            out["status"] = "INVALID"
            holds.append(h)
            continue
        b = 2.0 * h["A_hull_m2"] / h["P_hull_m"]
        z_ref = (h["Fz_scm_N"] / (h["N_h"] * d * d * k_of(b))) ** (1.0 / J2["n"])
        f = ((h["N_h"] * d * d * k_of(b)) / (A * k_of(b_poly))) ** (-1.0 / J2["n"])
        h.update(b_hull_m=b, z_ref_m=z_ref, f=f, z_over_f_m=h["z_geo_m"] / f,
                 eps1=J2["n"] * abs(h["z_node_m"] - z_ref) / h["z_node_m"])
        holds.append(h)
    out["holds"] = holds
    out["A_m2"], out["b_poly_m"] = A, b_poly
    ns = r.get("node_series") or []
    out["_series"] = [(round(float(row["t_s"]), 6), float(row["sinkage_geometric_m"])) for row in ns]
    out["us_per_step"], out["wall_s"] = r.get("us_per_step"), r.get("wall_s")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("batch", type=Path, help="batch folder 07_results/S9/batch_B1-GRIDCONV_<stamp>")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    if not a.batch.is_dir():
        print(json.dumps({"error": f"no folder {a.batch}"}))
        return 2
    pads = json.loads((ROOT / "02_params" / "pad_variants.json").read_text(encoding="utf-8"))["variants"]["dwg_rear250"]["legs"]
    rows = {rid: load_row(a.batch, rid, spec, pads) for rid, spec in ROWS.items()}
    complete = all(r["status"] == "VALID" for r in rows.values())
    g1 = {f"{rid}.k{h['k']}": h["eps1"] for rid, r in rows.items() for h in r.get("holds", []) if "eps1" in h}
    res: dict = {"plan": "06_analysis/02_control/b1/b1_gridconv_plan.md", "batch": str(a.batch),
                 "batch_status": "COMPLETE" if complete else "UNDETERMINED", "units": "m, N, s; ratios",
                 "rows": {rid: {k: v for k, v in r.items() if not k.startswith("_")} for rid, r in rows.items()},
                 "G1": {"values": g1, "max": max(g1.values()) if g1 else None, "limit": G1_LIMIT},
                 "pairs": {}}
    g1_ok = bool(g1) and len(g1) == 8 and all(v <= G1_LIMIT for v in g1.values())
    g2_vals, g3_vals, g5_flag = {}, {}, False
    for pname, (ci, fi) in PAIRS.items():
        c, f = rows[ci], rows[fi]  # c = 0.01 m, f = 0.005 m
        ok = c["status"] == "VALID" and f["status"] == "VALID"
        pr: dict = {"rows": [ci, fi], "status": "OK" if ok else "NA"}
        if ok:
            hc, hf = c["holds"], f["holds"]
            for k in range(2):
                g2_vals[f"{pname}.k{k + 1}"] = abs(hc[k]["z_over_f_m"] - hf[k]["z_over_f_m"])
            dzc, dzf = hc[1]["z_geo_m"] - hc[0]["z_geo_m"], hf[1]["z_geo_m"] - hf[0]["z_geo_m"]
            rc, rf = dzc / hc[1]["z_geo_m"], dzf / hf[1]["z_geo_m"]
            g3_vals[pname] = abs(rc - rf)
            sc, sf = dict(c["_series"]), dict(f["_series"])
            common = sorted(t for t in sc if t in sf and T_HOLD_END_S[0] - 1e-9 <= t <= T_HOLD_END_S[1] + 1e-9)

            def r_of(s, z1, z2):
                return {t: (s[t] - z1) / (z2 - z1) for t in common}

            r_c = r_of(sc, hc[0]["z_geo_m"], hc[1]["z_geo_m"])
            r_f = r_of(sf, hf[0]["z_geo_m"], hf[1]["z_geo_m"])
            g5 = max(abs(r_c[t] - r_f[t]) for t in common) if common else None
            g5_flag |= bool(g5 is not None and g5 > G5_LIMIT)
            raw = {"z2_diff_m": hc[1]["z_geo_m"] - hf[1]["z_geo_m"], "dz_diff_m": dzc - dzf,
                   "z1_diff_m": hc[0]["z_geo_m"] - hf[0]["z_geo_m"]}
            pred = {k: {"pred_m": v, "raw_m": raw[k], "confirmed": abs(raw[k] - v) <= PRED_TOL_M}
                    for k, v in PRED[pname].items()}
            pr.update(G2={f"k{k + 1}": g2_vals[f"{pname}.k{k + 1}"] for k in range(2)},
                      G3={"ratio_0p01": rc, "ratio_0p005": rf, "abs_diff": g3_vals[pname]},
                      G4=dict(raw, f=[[h["f"] for h in hc], [h["f"] for h in hf]],
                              N_h=[[h["N_h"] for h in hc], [h["N_h"] for h in hf]],
                              b_hull_m=[[h["b_hull_m"] for h in hc], [h["b_hull_m"] for h in hf]]),
                      G5={"max_abs_diff": g5, "n_samples": len(common), "flag": bool(g5 is not None and g5 > G5_LIMIT)},
                      prediction=pred)
        res["pairs"][pname] = pr
    g2_ok = len(g2_vals) == 4 and all(v <= G2_LIMIT_M for v in g2_vals.values())
    g3_ok = len(g3_vals) == 2 and all(v <= G3_LIMIT for v in g3_vals.values())
    if not complete:
        verdict = "UNDETERMINED"
    elif not g1_ok or not g2_ok:
        verdict = "REJECT"
    elif not g3_ok:
        verdict = "HOLD"
    else:
        verdict = "PASS"
    res.update(G2={"values": g2_vals, "limit_m": G2_LIMIT_M}, G3={"values": g3_vals, "limit": G3_LIMIT},
               G5_FLAG=g5_flag, verdict=verdict)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "batch_status": res["batch_status"],
                      "row_status": {rid: r["status"] for rid, r in rows.items()},
                      "G1_max": res["G1"]["max"], "G2_max_mm": None if not g2_vals else max(g2_vals.values()) * 1e3,
                      "G3_max": None if not g3_vals else max(g3_vals.values()), "G5_FLAG": g5_flag}))
    return {"PASS": 0, "REJECT": 1, "HOLD": 1, "UNDETERMINED": 3}[verdict]


if __name__ == "__main__":
    sys.exit(main())
