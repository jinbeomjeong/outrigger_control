"""Synthetic self-test of gridconv_judge.py (no Chrono result is read).

Usage: python -I gridconv_judge_selftest.py <gridconv_judge.py> <rexome33.yaml>
Cases: pass -> PASS, G-1 node sinkage +3 % -> REJECT, first-hold z1 -0.5 mm -> HOLD; missing row, wrong
--grid, share xy0 2e-9 m, no series.npz, unvalidated hull DLL (rev1) -> UNDETERMINED. Last line
{"status": "ok"} when every case gives the expected verdict.
"""
import copy
import json

import numpy as np
import math
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path

HERE = Path(tempfile.mkdtemp(prefix="gc_selftest_"))  # synthetic batches only, outside the repo
JUDGE = Path(sys.argv[1])
YAML = Path(sys.argv[2])
KC, KPHI, N = 16430.0, 1724690.0, 0.2
DLL_SHA = "cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15"
CENSUS = {"GC-1": (601, 0.1255), "GC-2": (2421, 0.1310), "GC-3": (1073, 0.1714), "GC-4": (4285, 0.1716)}
ROWS = {"GC-1": ("GC1_J2_B_RL_1cm", "RL", 0.01, 74850.0, "0.97327989,1.0", 0.97327989, 0.0607),
        "GC-2": ("GC2_J2_B_RL_0p5cm", "RL", 0.005, 74850.0, "0.97327989,1.0", 0.97327989, 0.0607),
        "GC-3": ("GC3_J2_B_FL_1cm", "FL", 0.01, 122010.0, "0.98016556,1.0", 0.98016556, 0.1071),
        "GC-4": ("GC4_J2_B_FL_0p5cm", "FL", 0.005, 122010.0, "0.98016556,1.0", 0.98016556, 0.1071)}


def zref(F, nh, d, b):
    return (F / (nh * d * d * (KC / b + KPHI))) ** (1 / N)


def make_row(rid):
    case, leg, d, load, steps, fac, area = ROWS[rid]
    nh, b = CENSUS[rid]
    levels, series = [], []
    zs = []
    for k, (f, t) in enumerate(((fac, 11.0), (1.0, 21.0))):
        F = f * load
        z = zref(F, nh, d, b)
        zs.append(z)
        nodes = {"n_contact": nh, "contact_hull_area_m2": b / 2, "contact_hull_perimeter_m": 1.0,
                 "sinkage_mean_contact_m": z, "sinkage_geometric_m": z}
        levels.append({"level": k, "end": {"t_s": t, "Fz_scm_N": F, "load_N": F, "nodes": nodes}})
    for i in range(1, 211):
        t = i * 0.1
        if t <= 11.0:
            z = zs[0]
        else:
            z = zs[1] - (zs[1] - zs[0]) * math.exp(-(t - 11.0) / 0.45)
            if abs(t - 21.0) < 1e-9:
                z = zs[1]
        series.append({"t_s": t, "sinkage_geometric_m": z})
    args = {"action": "single-pad", "soil": "J2", "pad_variant": "dwg_rear250", "level": "top", "joint": "fixed",
            "threads": 4, "load_ramp": 3.0, "step_ramp": 2.0, "step_hold": "8", "scm_shear": "bprime",
            "stiffness_mode": "series", "ray_shape": "mesh", "dt": 1e-4, "k_sw": 15000.0, "interface": False,
            "terrain_size": [1.2, 1.2], "force": 0.0, "soil_override": None, "crawler_grid": None,
            "force_limit_factor": None, "t_ramp": 0.5, "load_ramp_shape": "poly345", "case": case, "leg": leg,
            "grid": d, "normal_load": load, "load_steps": steps, "out_root": "x", "t_settle": 21.0, "t_end": 21.0}
    return case, {"action": "single-pad", "args": args, "placement": {"omp_wait_policy": "PASSIVE"},
                  "meta": {"num_threads_chrono": 4, "pad_area_m2": area,
                           "scm": {"grid_m": d, "SetSoilParameters": {"Kc": KC, "Kphi": KPHI, "n": N},
                                   "plane_point_world_m": [0.0, 0.0, 0.0]}},
                  "settle_end": {"x_mm": 0.0, "y_mm": 0.0},
                  "hull_hook": {"mode": "fast", "requested": None, "source": "default", "default_mode": "fast",
                                "dll_sha256": DLL_SHA, "dll_sha_validated": True},
                  "_xy0": [0.0, 0.0],
                  "load_steps": {"levels": levels}, "node_series": series}


def write_batch(name, mutate=None, drop=None):
    root = HERE / "gc_selftest" / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    cases = []
    for rid in ROWS:
        case, res = make_row(rid)
        if mutate:
            mutate(rid, res)
        cases.append({"case": case, "rc": 0})
        if rid == drop:
            continue
        (root / case).mkdir()
        xy0 = res.pop("_xy0")
        if xy0 is not None:  # rev1 C-1: share-body x, y series (1 ms rows in the real run)
            np.savez(root / case / "series.npz", t=np.array([1e-3, 2e-3]), x=np.array([xy0[0], xy0[0]]),
                     y=np.array([xy0[1], xy0[1]]))
        (root / case / "result.json").write_text(json.dumps(res), encoding="utf-8")
    (root / "batch.json").write_text(json.dumps({"cases": cases}), encoding="utf-8")
    return root


def run(root):
    out = root / "metrics_A.json"
    p = subprocess.run([sys.executable, "-I", str(JUDGE), str(root), "--out", str(out), "--yaml", str(YAML)],
                       capture_output=True, text=True)
    m = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
    return p.returncode, p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr, m


def g1_bad(rid, res):
    if rid == "GC-2":
        res["load_steps"]["levels"][1]["end"]["nodes"]["sinkage_mean_contact_m"] *= 1.03


def g3_bad(rid, res):
    if rid == "GC-4":  # change z1 only via load: shift first-hold sinkage (law kept: change Fz accordingly)
        lv = res["load_steps"]["levels"][0]["end"]
        lv["Fz_scm_N"] *= 0.99914  # z1 about -0.5 mm: G-2 ~0.5 mm passes, G-3 ~0.004 fails
        z = zref(lv["Fz_scm_N"], CENSUS[rid][0], 0.005, CENSUS[rid][1])
        lv["nodes"]["sinkage_mean_contact_m"] = lv["nodes"]["sinkage_geometric_m"] = z


def bad_arg(rid, res):
    if rid == "GC-3":
        res["args"]["grid"] = 0.02


def xy_off(rid, res):
    if rid == "GC-1":
        res["_xy0"] = [2e-9, 0.0]  # beyond 1e-9 m (rev1 C-1)


def no_series(rid, res):
    if rid == "GC-3":
        res["_xy0"] = None  # series.npz absent


def dll_bad(rid, res):
    if rid == "GC-2":
        res["hull_hook"]["dll_sha256"] = "0" * 64
        res["hull_hook"]["dll_sha_validated"] = False


results = {}
for name, mut, drop, expect in (("pass", None, None, (0, "PASS")), ("g1", g1_bad, None, (1, "REJECT")),
                                ("g3", g3_bad, None, (1, "HOLD")), ("missing", None, "GC-4", (1, "UNDETERMINED")),
                                ("badarg", bad_arg, None, (1, "UNDETERMINED")),
                                ("xy_off", xy_off, None, (1, "UNDETERMINED")),
                                ("no_series", no_series, None, (1, "UNDETERMINED")),
                                ("dll_bad", dll_bad, None, (1, "UNDETERMINED"))):
    rc, last, m = run(write_batch(name, mut, drop))
    ok = (rc, m["verdict"] if m else None) == expect
    results[name] = {"rc": rc, "verdict": m["verdict"] if m else None, "ok": ok, "last": last}
    if name == "pass":
        results[name].update(pairs={k: {kk: v[kk] for kk in ("z2_diff_m", "dz_diff_m", "g3", "g5")}
                                    for k, v in m["pairs"].items()},
                             g1=m["gates"]["G-1"]["max"], g2=m["gates"]["G-2"]["max"],
                             pred=m["prediction_state"])
    if name in ("badarg", "xy_off", "no_series", "dll_bad"):
        results[name]["reasons"] = [r for row in m["rows"].values() for r in row["reasons"]]
print(json.dumps(results, indent=1, ensure_ascii=False))
print(json.dumps({"status": "ok" if all(r["ok"] for r in results.values()) else "fail"}))
