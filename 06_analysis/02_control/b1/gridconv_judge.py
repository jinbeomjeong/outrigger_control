"""B1-GRIDCONV path A judge (b1_gridconv_plan.md, sealed 0e909bf1...).

Reads the four single-pad rows GC-1..GC-4 of one batch folder and writes the metrics, row / bundle
states, the gates G-1..G-5, the verdict (PASS / REJECT / HOLD / UNDETERMINED) and the prediction
check E-1..E-8. numpy + json + stdlib only; no project import (path B is written separately).

Definitions (plan section 1):
    z_ref = (F / (N_h d^2 (kc / b_hull + kphi)))**(1/n)          F = Fz_scm_N at the hold end
    f     = [N_h d^2 (kc / b_hull + kphi) / (A (kc / b_poly + kphi))]**(-1/n)
    b_hull = 2 A_hull / P_hull of the contact nodes (result.json nodes record)
    A, b_poly from YAML pad_shapes.dwg_rear250.legs.<leg> (bottom_area_m2, bekker_b_m)

Usage:
    python -I gridconv_judge.py <batch folder> --out <metrics_A.json>
        [--yaml 02_params/rexome33.yaml] [--rc CASE=RC ...]
Exit: 0 verdict PASS, 1 verdict REJECT / HOLD / UNDETERMINED, 2 input error.
The last stdout line is a one-line JSON summary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

PLAN_SHA256 = "0e909bf1186a4cc90e40353d25244ee4a76a04cdabe48235e7051f9a111e9b24"
J2 = {"Kc": 16430.0, "Kphi": 1724690.0, "n": 0.2}
T_HOLD_END = (11.0, 21.0)  # [s] ends of the two holds (3 s ramp + 8 s, 2 s ramp + 8 s)
T_END_MIN = 21.0 - 1e-6
ROWS = {  # ID: case, leg, grid [m], normal load [N], load steps string
    "GC-1": ("GC1_J2_B_RL_1cm", "RL", 0.01, 74850.0, "0.97327989,1.0"),
    "GC-2": ("GC2_J2_B_RL_0p5cm", "RL", 0.005, 74850.0, "0.97327989,1.0"),
    "GC-3": ("GC3_J2_B_FL_1cm", "FL", 0.01, 122010.0, "0.98016556,1.0"),
    "GC-4": ("GC4_J2_B_FL_0p5cm", "FL", 0.005, 122010.0, "0.98016556,1.0"),
}
PAIRS = {"RL": ("GC-1", "GC-2"), "FL": ("GC-3", "GC-4")}  # (0.01 m, 0.005 m)
EXPECTED_ARGS = {  # parsed args (result.json "args" = vars(args)); per-row keys filled in expected_args()
    "action": "single-pad", "soil": "J2", "pad_variant": "dwg_rear250", "level": "top", "joint": "fixed",
    "threads": 4, "load_ramp": 3.0, "step_ramp": 2.0, "step_hold": "8", "scm_shear": "bprime",
    "stiffness_mode": "series", "ray_shape": "mesh", "dt": 1.0e-4, "k_sw": 1.5e4, "interface": False,
    "terrain_size": [1.2, 1.2], "force": 0.0, "soil_override": None, "crawler_grid": None,
    "force_limit_factor": None, "t_ramp": 0.5, "load_ramp_shape": "poly345",
}
G1_MAX = 0.005      # n |z - z_ref| / z
G2_MAX_M = 1.0e-3   # |z/f (0.01) - z/f (0.005)|
G3_MAX = 0.002      # |dz/z2 (0.01) - dz/z2 (0.005)|
G5_MAX = 0.05       # max |r_0.01 - r_0.005|
PRED = {  # plan section 5: E-5..E-8 raw values [m], tolerance 0.5 mm
    "E-5": ("RL", "z2_diff_m", 2.7e-3), "E-6": ("RL", "dz_diff_m", 0.35e-3),
    "E-7": ("FL", "z2_diff_m", -0.80e-3), "E-8": ("FL", "dz_diff_m", -0.08e-3),
}
PRED_TOL_M = 0.5e-3
PRED_BOUND = {"E-1": ("G-1", 0.001), "E-2": ("G-2", 0.3e-3), "E-3": ("G-3", 0.0005), "E-4": ("G-5", 0.02)}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def yaml_pad_b(yaml_path: Path) -> dict[str, tuple[float, float]]:
    """(A, b_poly) per leg from pad_shapes.dwg_rear250.legs (plain line scan, no YAML library)."""
    lines = yaml_path.read_text(encoding="utf-8").splitlines()
    out: dict[str, tuple[float, float]] = {}
    i = next(k for k, s in enumerate(lines) if s.rstrip() == "pad_shapes:")
    i = next(k for k in range(i, len(lines)) if lines[k].strip() == "dwg_rear250:")
    leg, area = None, None
    for s in lines[i + 1:]:
        if s and not s.startswith("    "):
            break  # left the pad_shapes block
        m = re.match(r"^        (FL|FR|RL|RR):\s*$", s)
        if m:
            leg, area = m.group(1), None
            continue
        m = re.match(r"^\s+bottom_area_m2:\s*([0-9.eE+-]+)", s)
        if m and leg:
            area = float(m.group(1))
        m = re.match(r"^\s+bekker_b_m:\s*([0-9.eE+-]+)", s)
        if m and leg and area is not None:
            out[leg] = (area, float(m.group(1)))
        if re.match(r"^    \S", s) and s.strip() != "dwg_rear250:":
            break  # next pad type
    if set(out) != {"FL", "FR", "RL", "RR"}:
        raise ValueError(f"pad_shapes.dwg_rear250 legs incomplete in {yaml_path}: {sorted(out)}")
    return out


def k_eq(b: float, soil: dict) -> float:
    return soil["Kc"] / b + soil["Kphi"]


def grid_factor(nh: int, d: float, b_hull: float, area: float, b_poly: float, soil: dict) -> float:
    return (nh * d * d * k_eq(b_hull, soil) / (area * k_eq(b_poly, soil))) ** (-1.0 / soil["n"])


def z_ref(force: float, nh: int, d: float, b_hull: float, soil: dict) -> float:
    return (force / (nh * d * d * k_eq(b_hull, soil))) ** (1.0 / soil["n"])


def expected_args(rid: str) -> dict:
    case, leg, grid, load, steps = ROWS[rid]
    e = dict(EXPECTED_ARGS)
    e.update(case=case, leg=leg, grid=grid, normal_load=load, load_steps=steps)
    return e


def same(a, b) -> bool:
    if isinstance(b, float) and isinstance(a, (int, float)) and not isinstance(a, bool):
        return math.isclose(float(a), b, rel_tol=0.0, abs_tol=1e-12 * max(1.0, abs(b)))
    if isinstance(b, list) and isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def find_rc(batch: Path, case: str, rc_cli: dict[str, int]) -> tuple[int | None, str]:
    if case in rc_cli:
        return rc_cli[case], "cli"
    bj = batch / "batch.json"
    if bj.is_file():
        try:
            data = json.loads(bj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None, "batch.json unreadable"
        for c in data.get("cases", []) if isinstance(data, dict) else []:
            if isinstance(c, dict) and case in (c.get("case"), c.get("name")):
                for key in ("rc", "returncode", "exit_code"):
                    if isinstance(c.get(key), int):
                        return c[key], f"batch.json {key}"
    return None, "none"


def batch_argv(batch: Path, case: str) -> list[str] | None:
    bj = batch / "batch.json"
    if not bj.is_file():
        return None
    try:
        data = json.loads(bj.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for c in data.get("cases", []) if isinstance(data, dict) else []:
        if isinstance(c, dict) and case in (c.get("case"), c.get("name")) and isinstance(c.get("argv"), list):
            return [str(x) for x in c["argv"]]
    return None


def expected_argv_tail(rid: str) -> list[str]:
    case, leg, grid, load, steps = ROWS[rid]
    return ["single-pad", "--soil", "J2", "--pad-variant", "dwg_rear250", "--level", "top", "--leg", leg,
            "--joint", "fixed", "--grid", f"{grid:g}", "--threads", "4", "--normal-load", f"{load:.0f}",
            "--load-steps", steps, "--load-ramp", "3", "--step-ramp", "2", "--step-hold", "8", "--case", case]


def hold_end_record(res: dict, k: int) -> dict:
    lv = res["load_steps"]["levels"][k]["end"]
    nd = lv["nodes"]
    return {"t_s": float(lv["t_s"]), "Fz_scm_N": float(lv["Fz_scm_N"]), "load_N": float(lv["load_N"]),
            "n_contact": int(nd["n_contact"]), "hull_area_m2": nd.get("contact_hull_area_m2"),
            "hull_perimeter_m": nd.get("contact_hull_perimeter_m"),
            "z_node_m": nd.get("sinkage_mean_contact_m"), "z_geo_m": float(nd["sinkage_geometric_m"])}


def judge_row(rid: str, batch: Path, pads: dict, rc_cli: dict[str, int]) -> dict:
    case, leg, grid, _, _ = ROWS[rid]
    row: dict = {"id": rid, "case": case, "leg": leg, "grid_m": grid, "status": None, "reasons": []}
    rp = batch / case / "result.json"
    rc, rc_src = find_rc(batch, case, rc_cli)
    row.update(rc=rc, rc_source=rc_src)
    # V-1
    if not rp.is_file():
        row["status"] = "MISSING"
        row["reasons"].append("V-1 result.json absent")
        return row
    row["result_sha256"] = sha256_file(rp)
    res = json.loads(rp.read_text(encoding="utf-8"))
    levels = (res.get("load_steps") or {}).get("levels") or []
    v1 = []
    if rc != 0:
        v1.append(f"V-1 rc {rc} (source {rc_src})")
    if len(levels) != 2:
        v1.append(f"V-1 load_steps.levels {len(levels)} != 2")
    elif float(levels[1]["end"]["t_s"]) < T_END_MIN:
        v1.append(f"V-1 end time {levels[1]['end']['t_s']} < 21 s")
    if v1:
        row["status"] = "MISSING"
        row["reasons"] += v1
        return row
    # V-2
    v2 = []
    args = res.get("args") or {}
    for key, val in expected_args(rid).items():
        if key not in args or not same(args[key], val):
            v2.append(f"V-2 args.{key} = {args.get(key, '<absent>')!r}, expected {val!r}")
    argv = batch_argv(batch, case)
    row["argv_checked"] = argv is not None
    if argv is not None:
        tail = expected_argv_tail(rid)
        i = next((k for k, s in enumerate(argv) if s == "single-pad"), None)
        got = argv[i:i + len(tail)] if i is not None else []
        if got != tail:
            v2.append(f"V-2 batch.json argv {got} != {tail}")
        rest = argv[i + len(tail):] if i is not None else []
        if rest[:1] != ["--out-root"] or len(rest) != 2:
            v2.append(f"V-2 batch.json argv after --case: {rest} (expected --out-root <batch>)")
    meta = res.get("meta") or {}
    scm = meta.get("scm") or {}
    if meta.get("num_threads_chrono") != 4:
        v2.append(f"V-2 num_threads_chrono {meta.get('num_threads_chrono')}")
    if (res.get("placement") or {}).get("omp_wait_policy") != "PASSIVE":
        v2.append(f"V-2 placement.omp_wait_policy {(res.get('placement') or {}).get('omp_wait_policy')!r}")
    if not same(scm.get("grid_m"), grid):
        v2.append(f"V-2 meta.scm.grid_m {scm.get('grid_m')}")
    ssp = scm.get("SetSoilParameters") or {}
    for key, val in J2.items():
        if not same(ssp.get(key), val):
            v2.append(f"V-2 SetSoilParameters.{key} {ssp.get(key)}")
    if not same(scm.get("plane_point_world_m"), [0.0, 0.0, 0.0]):
        v2.append(f"V-2 plane_point_world_m {scm.get('plane_point_world_m')}")
    se = res.get("settle_end") or {}
    for key in ("x_mm", "y_mm"):
        if not isinstance(se.get(key), (int, float)) or abs(se[key]) > 1e-3:
            v2.append(f"V-2 settle_end.{key} {se.get(key)}")
    hh = res.get("hull_hook") or {}
    requested = hh.get("requested")
    if requested is None and hh.get("source") == "default":
        requested = hh.get("default_mode")  # unset env: requested = resolved default (plan 3.1)
    if hh.get("mode") != "fast" or requested != "fast":
        v2.append(f"V-2 hull_hook mode {hh.get('mode')!r} requested {hh.get('requested')!r}")
    area, b_poly = pads[leg]
    if not same(meta.get("pad_area_m2"), area):
        v2.append(f"V-2 meta.pad_area_m2 {meta.get('pad_area_m2')} != YAML {area}")
    if v2:
        row["status"] = "INVALID"
        row["reasons"] += v2
        return row
    # V-3 and per-hold metrics
    holds = [hold_end_record(res, k) for k in range(2)]
    v3 = [f"V-3 hold {k + 1}: N_h {h['n_contact']} / hull {h['hull_area_m2']}" for k, h in enumerate(holds)
          if h["n_contact"] < 3 or not h["hull_area_m2"] or not h["hull_perimeter_m"] or h["z_node_m"] is None]
    if v3:
        row["status"] = "INVALID"
        row["reasons"] += v3
        return row
    soil = {k: float(ssp[k]) for k in J2}
    for h in holds:
        h["b_hull_m"] = 2.0 * h["hull_area_m2"] / h["hull_perimeter_m"]
        h["z_ref_m"] = z_ref(h["Fz_scm_N"], h["n_contact"], grid, h["b_hull_m"], soil)
        h["g1_eps"] = soil["n"] * abs(h["z_node_m"] - h["z_ref_m"]) / h["z_node_m"]
        h["f"] = grid_factor(h["n_contact"], grid, h["b_hull_m"], area, b_poly, soil)
        h["z_over_f_m"] = h["z_geo_m"] / h["f"]
        h["node_minus_geo_m"] = h["z_node_m"] - h["z_geo_m"]
    row["holds"] = holds
    row["dz_m"] = holds[1]["z_geo_m"] - holds[0]["z_geo_m"]
    row["dz_over_z2"] = row["dz_m"] / holds[1]["z_geo_m"]
    ns = res.get("node_series") or []
    row["series"] = {round(float(e["t_s"]) * 10.0): float(e["sinkage_geometric_m"]) for e in ns
                     if T_HOLD_END[0] - 1e-9 <= float(e["t_s"]) <= T_HOLD_END[1] + 1e-9}
    row["pad_area_m2"], row["b_poly_m"] = area, b_poly
    row["status"] = "VALID"
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("batch")
    ap.add_argument("--out", required=True)
    ap.add_argument("--yaml", default=None, help="default: <repo>/02_params/rexome33.yaml (repo = 4 levels up)")
    ap.add_argument("--rc", nargs="*", default=[], metavar="CASE=RC")
    a = ap.parse_args(argv)
    batch = Path(a.batch)
    yaml_path = Path(a.yaml) if a.yaml else Path(__file__).resolve().parents[3] / "02_params" / "rexome33.yaml"
    try:
        rc_cli = {k: int(v) for k, v in (s.split("=", 1) for s in a.rc)}
        pads = yaml_pad_b(yaml_path)
    except (ValueError, OSError, StopIteration) as exc:
        print(json.dumps({"status": "input_error", "error": str(exc)}))
        return 2
    if not batch.is_dir():
        print(json.dumps({"status": "input_error", "error": f"batch folder {batch} absent"}))
        return 2
    rows = {rid: judge_row(rid, batch, pads, rc_cli) for rid in ROWS}
    bundle = "COMPLETE" if all(r["status"] == "VALID" for r in rows.values()) else "UNDETERMINED"
    gates: dict = {"G-1": {"values": {}}, "G-2": {"values": {}}, "G-3": {"values": {}},
                   "G-4": {"values": {}}, "G-5": {"values": {}}}
    for rid, r in rows.items():
        if r["status"] == "VALID":
            for k, h in enumerate(r["holds"]):
                gates["G-1"]["values"][f"{rid}/hold{k + 1}"] = h["g1_eps"]
    pairs: dict = {}
    for leg, (c, f_) in PAIRS.items():
        rc_, rf = rows[c], rows[f_]
        if rc_["status"] != "VALID" or rf["status"] != "VALID":
            pairs[leg] = None
            continue
        p = {"z1_diff_m": rc_["holds"][0]["z_geo_m"] - rf["holds"][0]["z_geo_m"],
             "z2_diff_m": rc_["holds"][1]["z_geo_m"] - rf["holds"][1]["z_geo_m"],
             "dz_diff_m": rc_["dz_m"] - rf["dz_m"],
             "g2_m": [abs(rc_["holds"][k]["z_over_f_m"] - rf["holds"][k]["z_over_f_m"]) for k in range(2)],
             "g3": abs(rc_["dz_over_z2"] - rf["dz_over_z2"])}
        common = sorted(set(rc_["series"]) & set(rf["series"]))
        if len(common) >= 2:
            def r_of(row):
                z = np.array([row["series"][t] for t in common])
                return (z - row["holds"][0]["z_geo_m"]) / (row["holds"][1]["z_geo_m"] - row["holds"][0]["z_geo_m"])
            p["g5"] = float(np.max(np.abs(r_of(rc_) - r_of(rf))))
            p["g5_samples"] = len(common)
        else:
            p["g5"], p["g5_samples"] = None, len(common)
        pairs[leg] = p
        for k in range(2):
            gates["G-2"]["values"][f"{leg}/hold{k + 1}"] = p["g2_m"][k]
        gates["G-3"]["values"][leg] = p["g3"]
        gates["G-4"]["values"][leg] = {"z1_diff_m": p["z1_diff_m"], "z2_diff_m": p["z2_diff_m"],
                                       "dz_diff_m": p["dz_diff_m"]}
        gates["G-5"]["values"][leg] = p["g5"]
    n1 = len(gates["G-1"]["values"])
    gates["G-1"].update(count=n1, max=max(gates["G-1"]["values"].values()) if n1 else None)
    gates["G-1"]["pass"] = (n1 == 8 and gates["G-1"]["max"] <= G1_MAX) if n1 else None
    n2 = len(gates["G-2"]["values"])
    gates["G-2"].update(count=n2, max=max(gates["G-2"]["values"].values()) if n2 else None)
    gates["G-2"]["pass"] = (n2 == 4 and gates["G-2"]["max"] <= G2_MAX_M) if n2 else None
    n3 = len(gates["G-3"]["values"])
    gates["G-3"].update(count=n3, max=max(gates["G-3"]["values"].values()) if n3 else None)
    gates["G-3"]["pass"] = (n3 == 2 and gates["G-3"]["max"] <= G3_MAX) if n3 else None
    g5v = [v for v in gates["G-5"]["values"].values() if v is not None]
    gates["G-5"].update(count=len(g5v), max=max(g5v) if g5v else None)
    gates["G-5"]["flag"] = bool(g5v) and max(g5v) > G5_MAX
    # verdict (plan section 4): G-1 first (stop), then G-2, then G-3
    if bundle != "COMPLETE":
        verdict, why = "UNDETERMINED", "bundle UNDETERMINED"
    elif not gates["G-1"]["pass"]:
        verdict, why = "REJECT", "G-1 failed (stop; G-2..G-5 computed but not used)"
    elif not gates["G-2"]["pass"]:
        verdict, why = "REJECT", "G-2 > 1 mm"
    elif not gates["G-3"]["pass"]:
        verdict, why = "HOLD", "G-3 > 0.002"
    else:
        verdict, why = "PASS", "G-1, G-2, G-3 within thresholds"
    preds: dict = {}
    for eid, (leg, key, val) in PRED.items():
        p = pairs.get(leg)
        got = None if p is None else p[key]
        preds[eid] = {"predicted_m": val, "observed_m": got,
                      "confirmed": None if got is None else abs(got - val) <= PRED_TOL_M}
    for eid, (gid, bound) in PRED_BOUND.items():
        mx = gates[gid]["max"]
        preds[eid] = {"bound": bound, "observed": mx, "within": None if mx is None else mx <= bound}
    raw = [preds[e]["confirmed"] for e in PRED]
    pred_state = ("예측 확인" if all(raw) else "예측 불일치") if all(x is not None for x in raw) else "NA"
    for r in rows.values():
        if "series" in r:
            r["series_samples"] = len(r.pop("series"))
    out = {"schema": "b1-gridconv-metrics/1", "path": "A", "plan_sha256": PLAN_SHA256,
           "tool_sha256": sha256_file(Path(__file__)), "batch": str(batch.resolve()),
           "yaml": str(yaml_path), "yaml_sha256": sha256_file(yaml_path), "bundle": bundle,
           "rows": rows, "pairs": pairs, "gates": gates, "verdict": verdict, "verdict_reason": why,
           "predictions": preds, "prediction_state": pred_state}
    text = json.dumps(out, indent=1, ensure_ascii=False) + "\n"
    Path(a.out).write_bytes(text.encode("utf-8"))
    print(json.dumps({"status": "ok", "verdict": verdict, "bundle": bundle, "out": str(a.out),
                      "out_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
