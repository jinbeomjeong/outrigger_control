"""B1-GRIDCONV path B (terramechanics-expert), independent of path A (numpy + json only, no project imports).

Plan: 06_analysis/02_control/b1/b1_gridconv_plan.md (sha 0e909bf1...) + rev1 (3f354eb7...).
Formulas (p1_levels.py form, SCMTerrain.cpp 584-588 / 1366-1377 / 1445 / 1475):
  k_eq(b) = Kc / b + Kphi
  z_ref   = (F / (N_h d^2 k_eq(b_hull)))^(1/n),  b_hull = 2 A_hull / P_hull of the contact nodes
  f       = [(N_h d^2 k_eq(b_hull)) / (A k_eq(b_poly))]^(-1/n)
  G-1: eps1 = n |z_node - z_ref| / z_node   (z_node = sinkage_mean_contact_m, F = Fz_scm_N), <= 0.005
  G-2: |z_k / f_k (0.01) - z_k / f_k (0.005)|, z = sinkage_geometric_m, <= 1e-3 m
  G-3: |dz/z2 (0.01) - dz/z2 (0.005)|, <= 0.002
  G-4: raw differences (record), G-5: max |r_0.01(t) - r_0.005(t)|, r = (z(t) - z1)/(z2 - z1), t in [11, 21] s
A from result.json meta.pad_area_m2; b_poly from 02_params/pad_variants.json dwg_rear250 legs.<leg>.bekker_b_m
(copy of YAML pad_shapes). Comparisons on unrounded doubles.
Usage: python -I -B gridconv_path_b.py <batch dir> <pad_variants.json> <out json>
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

BATCH = Path(sys.argv[1])
PADV = Path(sys.argv[2])
OUT = Path(sys.argv[3])

ROWS = {
    "GC-1": dict(case="GC1_J2_B_RL_1cm", leg="RL", grid="0.01", load="74850", steps="0.97327989,1.0"),
    "GC-2": dict(case="GC2_J2_B_RL_0p5cm", leg="RL", grid="0.005", load="74850", steps="0.97327989,1.0"),
    "GC-3": dict(case="GC3_J2_B_FL_1cm", leg="FL", grid="0.01", load="122010", steps="0.98016556,1.0"),
    "GC-4": dict(case="GC4_J2_B_FL_0p5cm", leg="FL", grid="0.005", load="122010", steps="0.98016556,1.0"),
}
PAIRS = {"RL": ("GC-1", "GC-2"), "FL": ("GC-3", "GC-4")}
J2 = {"Kphi": 1724690.0, "Kc": 16430.0, "n": 0.2, "cohesion": 0.0, "friction": 0.0, "Janosi": 0.01,
      "elastic_K": 2.0e8, "damping_R": 1103000.0}  # plan 1: J2 set; bprime -> c 0, phi 0 in SCM
DLL_SHA = "cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15"
T_HOLD_END = (11.0, 21.0)
TH = {"G1": 0.005, "G2": 1e-3, "G3": 0.002, "G5": 0.05}
PRED = {"E1": ("le", 0.001), "E2": ("le", 3e-4), "E3": ("le", 5e-4), "E4": ("le", 0.02),
        "E5": ("pm", 2.7e-3), "E6": ("pm", 0.35e-3), "E7": ("pm", -0.80e-3), "E8": ("pm", -0.08e-3)}
PM_TOL = 0.5e-3

padv = json.loads(PADV.read_text(encoding="utf-8"))["variants"]["dwg_rear250"]["legs"]
batch = json.loads((BATCH / "batch.json").read_text(encoding="utf-8"))
cases = {c["case"]: c for c in batch["cases"]}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def expected_argv(spec):
    return ["single-pad", "--soil", "J2", "--pad-variant", "dwg_rear250", "--level", "top", "--leg", spec["leg"],
            "--joint", "fixed", "--grid", spec["grid"], "--threads", "4", "--normal-load", spec["load"],
            "--load-steps", spec["steps"], "--load-ramp", "3", "--step-ramp", "2", "--step-hold", "8",
            "--case", spec["case"], "--out-root"]


def keq(b):
    return J2["Kc"] / b + J2["Kphi"]


rows = {}
for rid, spec in ROWS.items():
    rec = {"case": spec["case"], "checks": {}, "status": None}
    ck = rec["checks"]
    d = BATCH / spec["case"]
    c = cases.get(spec["case"])
    rj = d / "result.json"
    npz = d / "series.npz"
    r = json.loads(rj.read_text(encoding="utf-8")) if rj.exists() else None
    # V-1
    ck["V1_rc0"] = bool(c is not None and c.get("rc") == 0)
    ck["V1_result_json"] = r is not None
    levels = r["load_steps"]["levels"] if r else []
    ck["V1_two_levels"] = len(levels) == 2
    t_end = None
    if npz.exists():
        with np.load(npz, allow_pickle=False) as s:
            t_end = float(s["t"][-1])
            x0 = float(s["x"][0]) if "x" in s.files else None
            y0 = float(s["y"][0]) if "y" in s.files else None
    else:
        x0 = y0 = None
    rec["t_end_s"] = t_end
    ck["V1_t_end"] = bool(t_end is not None and t_end >= 21.0 - 1e-6)
    v1 = all(v for k, v in ck.items() if k.startswith("V1"))
    # V-2 (rev1 C-1, C-2)
    av = c["argv"] if c else []
    exp = expected_argv(spec)
    ck["V2_argv_tokens"] = bool(av[:len(exp)] == exp and len(av) == len(exp) + 1)
    ck["V2_out_root_is_batch"] = bool(len(av) == len(exp) + 1 and Path(av[-1]).resolve() == BATCH.resolve())
    if r:
        ck["V2_threads4"] = r["meta"]["num_threads_chrono"] == 4
        ck["V2_omp_passive"] = r["placement"].get("omp_wait_policy") == "PASSIVE"
        ck["V2_grid"] = float(r["meta"]["scm"]["grid_m"]) == float(spec["grid"])
        sp = r["meta"]["scm"]["SetSoilParameters"]
        ck["V2_soil_J2"] = all(float(sp[k]) == v for k, v in J2.items())
        ck["V2_plane_origin"] = [float(v) for v in r["meta"]["scm"]["plane_point_world_m"]] == [0.0, 0.0, 0.0]
        a = r["args"]
        ck["V2_no_pad_start_arg"] = not any(k.startswith("pad_start") and a[k] not in (None, False, "") for k in a)
        ck["V2_share_xy0"] = bool(x0 is not None and y0 is not None and abs(x0) <= 1e-9 and abs(y0) <= 1e-9)
        hh = r.get("hull_hook", {})
        ck["V2_hull_fast"] = hh.get("requested") == "fast" and hh.get("mode") == "fast"
        ck["V2_dll_sha"] = hh.get("dll_sha256") == DLL_SHA and hh.get("dll_sha_validated") is True
        rec["settle_end_xy_mm"] = [r["settle_end"]["x_mm"], r["settle_end"]["y_mm"]]
        rec["share_xy0_m"] = [x0, y0]
    v2 = all(v for k, v in ck.items() if k.startswith("V2")) and r is not None
    # V-3
    lv = []
    v3 = True
    for k, L in enumerate(levels[:2]):
        e = L["end"]
        nd = e["nodes"]
        ha, hp = nd.get("contact_hull_area_m2"), nd.get("contact_hull_perimeter_m")
        ok = nd.get("n_contact", 0) >= 3 and ha is not None and hp is not None
        v3 &= ok
        lv.append(dict(t_s=float(e["t_s"]), load_N=float(e["load_N"]), Fz_scm_N=float(e["Fz_scm_N"]),
                       N_h=int(nd["n_contact"]), hull_area_m2=ha, hull_perimeter_m=hp,
                       z_node_m=nd["sinkage_mean_contact_m"], z_geo_m=nd["sinkage_geometric_m"]))
    ck["V3_nodes_hull"] = bool(v3 and len(lv) == 2)
    ck["V3_hold_end_times"] = bool(len(lv) == 2 and all(abs(lv[k]["t_s"] - T_HOLD_END[k]) <= 1e-6 for k in range(2)))
    rec["status"] = ("MISSING" if not v1 else "INVALID" if not (v2 and ck["V3_nodes_hull"]) else "VALID")
    # metrics per level
    if lv and rec["status"] == "VALID":
        h = float(r["meta"]["scm"]["grid_m"])
        A = float(r["meta"]["pad_area_m2"])
        bp = float(padv[spec["leg"]]["bekker_b_m"])
        rec.update(grid_m=h, A_m2=A, b_poly_m=bp)
        for L in lv:
            bh = 2.0 * L["hull_area_m2"] / L["hull_perimeter_m"]
            Aeff = L["N_h"] * h * h
            zref = (L["Fz_scm_N"] / (Aeff * keq(bh))) ** (1.0 / J2["n"])
            f = ((Aeff * keq(bh)) / (A * keq(bp))) ** (-1.0 / J2["n"])
            L.update(b_hull_m=bh, A_eff_m2=Aeff, z_ref_m=zref, f=f,
                     eps1=J2["n"] * abs(L["z_node_m"] - zref) / L["z_node_m"],
                     z_corr_m=L["z_geo_m"] / f, z_node_over_ref_m1=L["z_node_m"] / zref - 1.0)
        z1, z2 = lv[0]["z_geo_m"], lv[1]["z_geo_m"]
        rec.update(dz_m=z2 - z1, dz_over_z2=(z2 - z1) / z2)
        ns = r["node_series"]
        rec["_series"] = [(round(float(p["t_s"]) * 10), float(p["sinkage_geometric_m"])) for p in ns
                          if p.get("sinkage_geometric_m") is not None]
    rec["levels"] = lv
    rows[rid] = rec

bundle = "COMPLETE" if all(r["status"] == "VALID" for r in rows.values()) else "UNDETERMINED"
pairs = {}
for p, (a, b) in PAIRS.items():
    ra, rb = rows[a], rows[b]
    if ra["status"] != "VALID" or rb["status"] != "VALID":
        pairs[p] = "NA"
        continue
    la, lb = ra["levels"], rb["levels"]
    g2 = [abs(la[k]["z_corr_m"] - lb[k]["z_corr_m"]) for k in range(2)]
    g3 = abs(ra["dz_over_z2"] - rb["dz_over_z2"])
    sa = dict(ra["_series"]); sb = dict(rb["_series"])
    ka = [k for k in sorted(set(sa) & set(sb)) if 110 <= k <= 210]
    ra_t = {k: (sa[k] - la[0]["z_geo_m"]) / ra["dz_m"] for k in ka}
    rb_t = {k: (sb[k] - lb[0]["z_geo_m"]) / rb["dz_m"] for k in ka}
    dif = [abs(ra_t[k] - rb_t[k]) for k in ka]
    i = int(np.argmax(dif))
    pairs[p] = dict(rows=[a, b],
                    G2_m=g2, G2_max_m=max(g2),
                    G3=g3, dz_over_z2=[ra["dz_over_z2"], rb["dz_over_z2"]],
                    G4=dict(z2_diff_m=la[1]["z_geo_m"] - lb[1]["z_geo_m"], dz_diff_m=ra["dz_m"] - rb["dz_m"],
                            z1_diff_m=la[0]["z_geo_m"] - lb[0]["z_geo_m"]),
                    G5_max=dif[i], G5_t_s=ka[i] / 10.0, G5_n_samples=len(ka))
for r in rows.values():
    r.pop("_series", None)

# G-1 over 8 values
g1_vals = [L["eps1"] for r in rows.values() if r["status"] == "VALID" for L in r["levels"]]
G = {}
if bundle == "COMPLETE":
    G["G1_max"] = max(g1_vals); G["G1_n"] = len(g1_vals); G["G1_pass"] = bool(len(g1_vals) == 8 and max(g1_vals) <= TH["G1"])
    g2v = [v for p in pairs.values() for v in p["G2_m"]]
    G["G2_max_m"] = max(g2v); G["G2_n"] = len(g2v); G["G2_pass"] = bool(len(g2v) == 4 and max(g2v) <= TH["G2"])
    g3v = [p["G3"] for p in pairs.values()]
    G["G3_max"] = max(g3v); G["G3_n"] = len(g3v); G["G3_pass"] = bool(len(g3v) == 2 and max(g3v) <= TH["G3"])
    g5v = [p["G5_max"] for p in pairs.values()]
    G["G5_max"] = max(g5v); G["G5_flag"] = bool(max(g5v) > TH["G5"])
    if not G["G1_pass"] or not G["G2_pass"]:
        verdict = "REJECT"
    elif not G["G3_pass"]:
        verdict = "HOLD"
    else:
        verdict = "PASS"
    vals = {"E1": G["G1_max"], "E2": G["G2_max_m"], "E3": G["G3_max"], "E4": G["G5_max"],
            "E5": pairs["RL"]["G4"]["z2_diff_m"], "E6": pairs["RL"]["G4"]["dz_diff_m"],
            "E7": pairs["FL"]["G4"]["z2_diff_m"], "E8": pairs["FL"]["G4"]["dz_diff_m"]}
    pred = {}
    for k, (kind, ref) in PRED.items():
        v = vals[k]
        ok = v <= ref if kind == "le" else abs(v - ref) <= PM_TOL
        pred[k] = dict(value=v, prediction=ref, rule="<=" if kind == "le" else "+-0.5 mm",
                       result="예측 확인" if ok else "예측 불일치")
else:
    verdict = "UNDETERMINED"
    pred = {}

out = dict(path="B", tool=dict(file=str(Path(__file__)), sha256=sha(__file__)),
           inputs=dict(batch_json_sha256=sha(BATCH / "batch.json"), pad_variants_sha256=sha(PADV),
                       results={r["case"]: sha(BATCH / r["case"] / "result.json") for r in rows.values()
                                if (BATCH / r["case"] / "result.json").exists()}),
           thresholds=TH, bundle=bundle, rows=rows, pairs=pairs, gates=G, predictions=pred, verdict=verdict)
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({"bundle": bundle, "verdict": verdict, **{k: v for k, v in G.items()}}))
