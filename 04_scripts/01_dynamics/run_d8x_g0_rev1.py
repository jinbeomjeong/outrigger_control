"""D8x G0 under rules rev1 (06_analysis/02_control/d8x/d8x_rules_rev1.md, sha ad16f452...).

rev1 3: reuse 33 evaluations (11 unchanged points x 3 levels) from commit 3da8daa d8x_g0.json (blob 26e90fd0...)
if the G0 execution-path files (run_target_envelope.py, run_s6_slope_boundary_check.py, dyn_model.py, YAML and their
import closure) have the same git blob ids as in 3da8daa; recompute the 27 changed evaluations (9 points x 3 levels)
with the same code. rev1 4.3: G0-4 judged only on the Chrono-fixed points (top fdown3.7 / fup3.6 / roll5.7 /
rollm5.7 / rpX, middle / bottom rpX), threshold 1.005; W candidates (top) get a selection eligibility (d45 1.01,
others 1.005); error <= 0.037 deg for all. R_v uses the rev1 asymmetric diamond (5.7, nose down 3.7, nose up 3.6).

This wrapper only imports run_s6_slope_boundary_check (stage d8x_g0 functions) and does not change any execution-path
file. As a cross-check it also recomputes the 33 reused evaluations and records the difference (not used for judging).

Run (worktree root, dynamics-dev, E-cores):
  conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_d8x_g0_rev1.py
Output: 06_analysis/00_dynamics/d8x_g0_rev1.json (3da8daa d8x_g0.json is not touched).
Conventions as run_s6_slope_boundary_check (body x fwd, y left, z up; roll + left up; pitch + nose down).
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import argparse  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_s6_slope_boundary_check as sb  # noqa: E402

ROOT = sb.ROOT
OUT = ROOT / "06_analysis" / "00_dynamics" / "d8x_g0_rev1.json"
RULES_REV1 = "06_analysis/02_control/d8x/d8x_rules_rev1.md"
RULES_REV1_SHA = "ad16f452fb4dce7395a059c73d7caf213f1a9a69f18af8d230bf03f4518e80d4"
BASE_COMMIT = "3da8daa"
BASE_JSON = "06_analysis/00_dynamics/d8x_g0.json"
BASE_JSON_BLOB = "26e90fd07ea0c29b8b77d589139b5ef89369a92b"

SPAN_ROLL, SPAN_DN, SPAN_UP = 5.7, 3.7, 3.6          # rev1 1.1
REV1_POINTS = [                                       # rev1 1.2 (A) + (B), literal [deg] (phi_g, theta_g)
    ("pitch+", 0.0, 3.7), ("pitch-", 0.0, -3.6), ("roll+", 5.7, 0.0), ("roll-", -5.7, 0.0),
    ("r+p+0.25", 1.425, 2.775), ("r+p+0.5", 2.85, 1.85), ("r+p+0.75", 4.275, 0.925),
    ("r+p-0.25", 1.425, -2.7), ("r+p-0.5", 2.85, -1.8), ("r+p-0.75", 4.275, -0.9),
    ("r-p+0.5", -2.85, 1.85), ("r-p-0.5", -2.85, -1.8),
    ("d45++", 2.2627, 2.2627), ("d45-+", -2.2627, 2.2627), ("d45+-", 2.2064, -2.2064), ("d45--", -2.2064, -2.2064),
    ("rpX", 2.8632, 1.8413), ("rpX-+", -2.8632, 1.8413), ("rpX+-", 2.8242, -1.8162), ("rpX--", -2.8242, -1.8162),
]
UNCHANGED = ("pitch+", "roll+", "roll-", "r+p+0.25", "r+p+0.5", "r+p+0.75", "r-p+0.5", "d45++", "d45-+", "rpX",
             "rpX-+")
CHANGED = ("pitch-", "r+p-0.25", "r+p-0.5", "r+p-0.75", "r-p-0.5", "d45+-", "d45--", "rpX+-", "rpX--")
CHRONO_NAME = {"pitch+": "fdown3.7", "pitch-": "fup3.6", "roll+": "roll5.7", "roll-": "rollm5.7", "rpX": "rpX"}
W_CAND = sb.D8X_W_CANDIDATES
RV_HAT_MAX = 1.005
RV_HAT_MAX_D45_W = 1.01
ERR_MAX = 0.037


def rv(ph, th):
    return abs(ph) / SPAN_ROLL + abs(th) / (SPAN_DN if th >= 0 else SPAN_UP)


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def blob_check():
    """Import closure of the G0 path (modules loaded in this process, inside the repo) + YAML: blob at 3da8daa vs HEAD,
    and a clean tracked tree."""
    files = set()
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f:
            continue
        p = Path(f).resolve()
        try:
            rel = p.relative_to(ROOT)
        except ValueError:
            continue
        if rel.parts[0] == "04_scripts" and p.name == Path(__file__).name:
            continue                                   # this wrapper is new (not an execution-path file of 3da8daa)
        files.add(rel.as_posix())
    files.add("02_params/rexome33.yaml")
    rows = {}
    for f in sorted(files):
        b0 = git("rev-parse", f"{BASE_COMMIT}:{f}"); b1 = git("rev-parse", f"HEAD:{f}")
        rows[f] = {"base": b0, "head": b1, "same": bool(b0) and b0 == b1}
    status = git("status", "--porcelain", "--untracked-files=no")
    return {"files": rows, "all_same": all(v["same"] for v in rows.values()), "status_porcelain": status,
            "clean": status == "", "n_files": len(rows)}


def rejudge(row):
    """rev1 R_v, G0-4 scope and thresholds on a d8x_eval row (G0-1..3 unchanged)."""
    lv, tag = row["level"], row["tag"]
    ph, th = row["floor_deg"]
    r = dict(row)
    r["Rv_rev1"] = rv(ph, th)
    if lv == "top":
        r["chrono_floor"] = CHRONO_NAME.get(tag)
    else:
        r["chrono_floor"] = "rpX" if tag == "rpX" else None
    r["w_candidate_top"] = lv == "top" and tag in W_CAND
    r["g04_role"] = "chrono" if r["chrono_floor"] else ("w_candidate" if r["w_candidate_top"] else None)
    J = {k: dict(v) for k, v in row["G0"].items()}
    g4 = J["G0-4"]
    if g4.get("floor_hat_deg") is not None:
        hp, ht = g4["floor_hat_deg"]
        rvh = rv(hp, ht)
        emax = max(abs(g4["err_deg"][0]), abs(g4["err_deg"][1]))
        lim = RV_HAT_MAX_D45_W if (r["g04_role"] == "w_candidate" and tag.startswith("d45")) else RV_HAT_MAX
        g4.update({"Rv_hat_orig_rule": g4.get("Rv_hat"), "Rv_hat": rvh, "Rv_hat_limit": lim,
                   "margin_Rv": lim - rvh, "margin_err_deg": ERR_MAX - emax,
                   "pass": rvh <= lim and emax <= ERR_MAX,
                   "use": {"chrono": "gate", "w_candidate": "W eligibility (rev1 5.1)"}.get(r["g04_role"], "record")})
        g4.pop("applies", None)
    J["G0-4"] = g4
    r["G0"] = J
    req = ["G0-1", "G0-2", "G0-3"] + (["G0-4"] if r["g04_role"] == "chrono" else [])
    vals = [J[k].get("pass") for k in req]
    r["judged_items"] = req
    r["verdict"] = "not_judgeable" if any(v is None for v in vals) else ("pass" if all(vals) else "fail")
    return r


def compute(points, levels, workers):
    jobs = [(lv, t, a, b) for lv in levels for t, a, b in points]
    first = sb._d8x_job(jobs[0])
    from multiprocessing import Pool
    with Pool(workers) as pool:
        rest = pool.map(sb._d8x_job, jobs[1:], chunksize=1)
    res = dict([first] + rest)
    return [sb.d8x_eval(lv, t, a, b, res[(lv, t, a, b)]) for (lv, t, a, b) in jobs]


def _num_diff(a, b, path=""):
    """Max abs difference over numeric leaves of two JSON-like trees (None if structure differs)."""
    if isinstance(a, dict) and isinstance(b, dict):
        ds = [_num_diff(a[k], b[k]) for k in a if k in b]
        return max([d for d in ds if d is not None], default=0.0)
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        ds = [_num_diff(x, y) for x, y in zip(a, b, strict=True)]
        return max([d for d in ds if d is not None], default=0.0)
    if isinstance(a, bool) or isinstance(b, bool):
        return 0.0 if a == b else float("inf")
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=sb.WORKERS)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    t0 = time.perf_counter()
    pts = {t: (p, q) for t, p, q in REV1_POINTS}
    # base JSON (3da8daa) and its identity
    base_blob = git("rev-parse", f"{BASE_COMMIT}:{BASE_JSON}")
    if base_blob != BASE_JSON_BLOB:
        raise SystemExit(f"base JSON blob {base_blob} != {BASE_JSON_BLOB}")
    base = json.loads(git("show", f"{BASE_COMMIT}:{BASE_JSON}"))
    base_rows = {(r["level"], r["tag"]): r for r in base["rows"]}
    # recompute changed 27 (+ the 33 unchanged as a cross-check, not judged)
    changed = [(t, *pts[t]) for t in CHANGED]
    unchanged = [(t, *pts[t]) for t in UNCHANGED]
    new_rows = compute(changed + unchanged, sb.dm.LEVELS, a.workers)
    new_by = {(r["level"], r["tag"]): r for r in new_rows}
    bc = blob_check()                                     # after the imports done by compute (workers import the same)
    reuse_ok = bc["all_same"] and bc["clean"]
    rows = []
    cross = {}
    for lv in sb.dm.LEVELS:
        for t, p, q in REV1_POINTS:
            if t in UNCHANGED and reuse_ok:
                br = base_rows[(lv, t)]
                if br["floor_deg"] != [p, q]:
                    raise SystemExit(f"reused point {lv}|{t} coordinates {br['floor_deg']} != rev1 {[p, q]}")
                r = rejudge(br); r["source"] = f"reused {BASE_COMMIT} {BASE_JSON} blob {BASE_JSON_BLOB[:8]}"
                d = _num_diff(br["G0"], new_by[(lv, t)]["G0"])
                cross[f"{lv}|{t}"] = d
            else:
                r = rejudge(new_by[(lv, t)]); r["source"] = "recomputed (rev1)"
            rows.append(r)
    n = len(rows)
    cnt = {v: sum(r["verdict"] == v for r in rows) for v in ("pass", "fail", "not_judgeable")}
    fails = {k: [f"{r['level']}|{r['tag']}" for r in rows if r["G0"][k].get("pass") is False
                 and (k != "G0-4" or r["g04_role"] == "chrono")] for k in ("G0-1", "G0-2", "G0-3", "G0-4")}

    def worst(k, key, role=None):
        c = [r for r in rows if r["G0"][k].get(key) is not None and (role is None or r["g04_role"] == role)]
        r = min(c, key=lambda r: r["G0"][k][key])
        return {"point": f"{r['level']}|{r['tag']}", key: r["G0"][k][key]}
    gate = "not_judgeable" if (n != 60 or cnt["not_judgeable"]) else ("pass" if cnt["pass"] == 60 else "fail")
    w = {r["tag"]: {"eligible": r["G0"]["G0-4"]["pass"], "Rv_rev1": r["Rv_rev1"],
                    "Rv_hat": r["G0"]["G0-4"]["Rv_hat"], "limit": r["G0"]["G0-4"]["Rv_hat_limit"],
                    "err_deg": r["G0"]["G0-4"]["err_deg"]} for r in rows if r["g04_role"] == "w_candidate"}
    import platform
    out = {
        "meta": {"rules": "06_analysis/02_control/d8x/d8x_rules.md + " + RULES_REV1, "rules_rev": "rev1",
                 "rules_rev1_sha256": RULES_REV1_SHA, "rules_rev1_blob": git("rev-parse", f"HEAD:{RULES_REV1}"),
                 "sections": "rev1 3 (reuse 33 + recompute 27 = 60), 4.3 (G0-4 scope), 5.0, 5.1 eligibility",
                 "base": {"commit": git("rev-parse", BASE_COMMIT), "json": BASE_JSON, "blob": base_blob},
                 "reuse_condition": {"satisfied": reuse_ok, **bc},
                 "reused_vs_recomputed_max_abs_diff": {"max": max([v for v in cross.values() if v is not None],
                                                                  default=None), "per_point": cross,
                                                       "note": "cross-check only; judging uses the reused values"},
                 "thresholds": {**sb.D8X_G0, "Rv_hat_max": RV_HAT_MAX, "Rv_hat_max_d45_W": RV_HAT_MAX_D45_W,
                                "inv_err_max_deg": ERR_MAX},
                 "diamond_deg": {"roll": SPAN_ROLL, "nose_down": SPAN_DN, "nose_up": SPAN_UP},
                 "G0-4_scope": "gate: top fdown3.7/fup3.6/roll5.7/rollm5.7/rpX, middle/bottom rpX (<= 1.005); "
                               "W candidates top: eligibility (d45 <= 1.01, others <= 1.005); err <= 0.037 deg; "
                               "others record",
                 "models": base["meta"]["models"], "conventions": base["meta"]["conventions"],
                 "identity": {**sb._d8x_identity(), "python": sys.executable,
                              "python_version": platform.python_version(),
                              "wrapper_blob_HEAD": git("rev-parse", "HEAD:04_scripts/01_dynamics/run_d8x_g0_rev1.py")},
                 "wall_s": round(time.perf_counter() - t0, 1),
                 "script": "04_scripts/01_dynamics/run_d8x_g0_rev1.py"},
        "summary": {"expected": 60, "actual": n, "reused": sum(r["source"].startswith("reused") for r in rows),
                    "recomputed": sum(r["source"].startswith("recomputed") for r in rows), **cnt, "gate_G0": gate,
                    "fails_by_item": fails,
                    "min_margin": {"G0-1_mm": worst("G0-1", "margin_mm"), "G0-2_kN": worst("G0-2", "margin_kN"),
                                   "G0-3_deg": worst("G0-3", "margin_deg"),
                                   "G0-4_err_deg_gate": worst("G0-4", "margin_err_deg", "chrono"),
                                   "G0-4_Rv_gate": worst("G0-4", "margin_Rv", "chrono")},
                    "w_candidates_eligibility": w},
        "rows": rows,
    }
    p = Path(a.out) if a.out else OUT
    p.write_text(json.dumps(out, indent=1, default=lambda v: v.tolist() if hasattr(v, "tolist") else
                            (bool(v) if type(v).__name__ == "bool_" else float(v))), encoding="utf-8")
    for r in rows:
        J = r["G0"]
        print(f"{r['level']:6s} {r['tag']:9s} ({r['floor_deg'][0]:+7.4f},{r['floor_deg'][1]:+7.4f}) "
              f"s {J['G0-1']['s_max_m']*1e3:7.2f} m1 {J['G0-1']['margin_mm']:+6.2f} F {J['G0-2']['F_static_min_N']/1e3:6.2f}"
              f" sw {J['G0-3']['swivel_deg']:.2f} Rvh {J['G0-4']['Rv_hat']:.5f}/{J['G0-4']['Rv_hat_limit']} "
              f"e {max(map(abs, J['G0-4']['err_deg'])):.4f} {J['G0-4']['pass']} [{r['g04_role']}] {r['verdict']} "
              f"{r['source'][:10]}")
    print(json.dumps(out["summary"]["min_margin"]))
    print(json.dumps({"reuse_ok": reuse_ok, "xcheck_max": out["meta"]["reused_vs_recomputed_max_abs_diff"]["max"]}))
    print(json.dumps({"gate_G0": gate, "pass": cnt["pass"], "fail": cnt["fail"], "nj": cnt["not_judgeable"],
                      "out": str(p)}))


if __name__ == "__main__":
    main()
