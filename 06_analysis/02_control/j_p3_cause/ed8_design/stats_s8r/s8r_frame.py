"""S8-R design, part 1: frame of the held-out source G' and of the census strata (no ed8 results).

Inputs (all pre-ed8, public design inputs or stored V0 baseline):
  - stored V0 grid (11-05) touch_phase/acceptance/c4g2_only/grid/grid_r6*.json  (V0 only)
  - ed7 pool frame ed7_design/stats_v7/s30_pool_runs.csv (V0 pass per cluster x offset, key list)
  - ed7 G1 key file ed7_design/keys_seal_b46bdf8f/confirm_g1_grid171.json (keys + V0 pair flags)
  - dynamics ed6 scan ed8_design/dynamics_u832_o00/u01_scan_ed6.csv (ed6 VBL treatment rows,
    used only for the handover-time pattern by family; ed6 results were published before ed7)

Stratum rule (spec v8 rules 6.3): E = event row whose V0 pair has a re-approach start of the event
leg's diagonal at <= 0.45 s after the event. Evaluated here with a tolerance argument to expose ties.

Usage: python -I -B s8r_frame.py <out_folder>
Outputs: s8r_frame.json, s8r_frame.txt
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control")
GRID = ROOT / "touch_phase" / "acceptance" / "c4g2_only" / "grid"
GRID_FILES = ["grid_r67_main.json", "grid_r67_top.json", "grid_r69_bottom.json", "grid_r69_top.json"]
POOL = ROOT / "j_p3_cause" / "ed7_design" / "stats_v7" / "s30_pool_runs.csv"
G1 = ROOT / "j_p3_cause" / "ed7_design" / "keys_seal_b46bdf8f" / "confirm_g1_grid171.json"
SCAN6 = ROOT / "j_p3_cause" / "ed8_design" / "dynamics_u832_o00" / "u01_scan_ed6.csv"
DIAG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
E_LIMIT = 0.45
NEW_PHASES = [0.0125, 0.0375, 0.0625, 0.0875]
OLD_PHASES = [0.0, 0.025, 0.05, 0.075]

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
res = {}
txt = []


def ckey(level, fs, timing, leg, event):
    return (str(level), float(fs), str(timing), str(leg), str(event))


def diag_first(starts, leg):
    d = DIAG[leg]
    ts = [float(t) for t, lg in (starts or []) if lg == d]
    return min(ts) if ts else None


# ---------------------------------------------------------------- stored V0 grid runs
v0 = {}
raw_starts = Counter()
for fn in GRID_FILES:
    d = json.loads((GRID / fn).read_text(encoding="utf-8"))
    for job in d["results"]:
        runs = job.get("runs") or []
        items = runs.values() if isinstance(runs, dict) else runs
        for r in items:
            k = ckey(job["level"], job["fs_kN"], job["timing"], job["leg"], r.get("event"))
            key = k + (round(float(r["offset_s"]), 4),)
            if key in v0:
                continue
            st = r.get("reapproach_starts")
            if st:
                for t, _ in st:
                    raw_starts[repr(t)] += 1
            v0[key] = {"pass": bool(r.get("pass")), "pu": r.get("pair_union_s"),
                       "diag_first": diag_first(st, job["leg"]) if st is not None else "MISSING",
                       "starts_present": st is not None}

# precision of stored start times: are they on a 0.005 / 0.01 grid?
res["v0_grid_runs"] = len(v0)
dec = Counter()
for s in raw_starts:
    t = float(s)
    dec["0.01-grid" if abs(t * 100 - round(t * 100)) < 1e-9 else
        ("0.005-grid" if abs(t * 200 - round(t * 200)) < 1e-9 else "finer")] += raw_starts[s]
res["start_time_precision"] = dict(dec)
txt.append(f"stored V0 grid runs {len(v0)}; reapproach start precision {dict(dec)}")
missing = [k for k, v in v0.items() if v["diag_first"] == "MISSING"]
res["v0_runs_missing_reapproach_key"] = len(missing)

# ---------------------------------------------------------------- frame (pool csv)
pool = list(csv.DictReader(POOL.open(encoding="utf-8")))
clusters = defaultdict(list)
for r in pool:
    k = ckey(r["level"], r["fs_kN"], r["timing"], r["leg"], r["event"])
    clusters[k].append(r)
res["pool_rows"] = len(pool)
res["clusters"] = len(clusters)


def fam(k):  # family without F_s
    return (k[0], k[2], k[3], k[4])


fam_ct = Counter(fam(k) for k in clusters)
res["families_wo_fs"] = len(fam_ct)
mixed, allfail, allpass = [], [], []
for k, rs in clusters.items():
    p = [r["v0_pass"] == "True" for r in rs]
    (allpass if all(p) else allfail if not any(p) else mixed).append(k)
res["v0_cluster_status"] = {"all_pass": len(allpass), "mixed": len(mixed), "all_fail": len(allfail)}
txt.append(f"pool rows {len(pool)}, clusters {len(clusters)}, families(no Fs) {len(fam_ct)}; "
           f"V0 cluster status {res['v0_cluster_status']}")
by_ev = Counter((k[0], k[2], k[4]) for k in clusters)
txt.append("clusters by (level, timing, event): " + str(dict(sorted(by_ev.items()))))
mix_tab = Counter((k[0], k[2], k[3], k[4]) for k in mixed + allfail)
txt.append("V0 mixed/all-fail clusters by (level,timing,leg,event): " + str(dict(sorted(mix_tab.items()))))
res["v0_mixed_or_fail_by_family"] = {"|".join(map(str, k)): v for k, v in sorted(mix_tab.items())}

# ---------------------------------------------------------------- E stratum at stored offsets
tab = defaultdict(lambda: Counter())
tie = []
for key, v in v0.items():
    k, off = key[:5], key[5]
    if k not in clusters:
        continue
    df = v["diag_first"]
    if df == "MISSING":
        s = "missing"
    elif df is None:
        s = "N(no diag start)"
    elif df <= E_LIMIT + 1e-9:
        s = "E"
        if abs(df - E_LIMIT) < 0.0051:
            tie.append("|".join(map(str, key)) + f" diag {df}")
    else:
        s = "N(diag>0.45)"
    tab[(k[0], k[2], "front" if k[3] in ("FL", "FR") else "rear", k[4])][(off, s)] += 1
rows = []
for f, c in sorted(tab.items()):
    for (off, s), n in sorted(c.items()):
        rows.append({"family": "|".join(f), "offset": off, "stratum": s, "n": n})
res["v0_stratum_by_family_offset"] = rows
res["v0_E_units_at_stored_offsets"] = sum(r["n"] for r in rows if r["stratum"] == "E")
res["E_ties_within_5ms"] = tie
txt.append("\n== V0 stored grid: stratum by family x offset (E = diag start <= 0.45 s) ==")
for r in rows:
    if r["stratum"] == "E" or r["family"].startswith("bottom"):
        txt.append(f"  {r['family']:<26} o{r['offset']:<6} {r['stratum']:<18} {r['n']}")
txt.append(f"E units at stored offsets: {res['v0_E_units_at_stored_offsets']}; ties within 5 ms: {tie}")

# E-candidate clusters = clusters with >= 1 E unit at stored offsets
e_clusters = sorted({key[:5] for key, v in v0.items()
                     if key[:5] in clusters and isinstance(v["diag_first"], float)
                     and v["diag_first"] <= E_LIMIT + 1e-9})
res["E_candidate_clusters"] = ["|".join(map(str, k)) for k in e_clusters]
res["E_candidate_families_wo_fs"] = sorted({"|".join(map(str, fam(k))) for k in e_clusters})
e_frac = Counter()
for k in e_clusters:
    offs = [key[5] for key in v0 if key[:5] == k]
    ne = sum(1 for key in v0 if key[:5] == k and isinstance(v0[key]["diag_first"], float)
             and v0[key]["diag_first"] <= E_LIMIT + 1e-9)
    e_frac[(ne, len(offs))] += 1
res["E_candidate_offsets_E_of_n"] = {f"{a}/{b}": c for (a, b), c in e_frac.items()}
txt.append(f"E-candidate clusters {len(e_clusters)} in {len(res['E_candidate_families_wo_fs'])} families: "
           f"{res['E_candidate_families_wo_fs']}; E offsets per cluster {res['E_candidate_offsets_E_of_n']}")

# ---------------------------------------------------------------- dynamics 4.3 interval model at new phases
# early iff s1 + 0.2 <= t_hold, s1 = first sample 0.1k - phi >= t_reload; t_reload 0.177-0.197, t_hold 0.442-0.451
def early(phi, tr, th):
    k = 0
    while 0.1 * k - phi < tr - 1e-12:
        k += 1
    s1 = 0.1 * k - phi
    return s1 + 0.2 <= th + 1e-12, round(s1 + 0.2, 4)


grid_pred = {}
for phi in NEW_PHASES + OLD_PHASES:
    outs = set()
    for tr in [0.177, 0.182, 0.1875, 0.19, 0.197]:
        for th in [0.442, 0.446, 0.451]:
            outs.add(early(phi, tr, th))
    grid_pred[phi] = sorted(outs)
res["interval_model_new_phases"] = {str(k): [list(x) for x in v] for k, v in grid_pred.items()}
txt.append("\n== dynamics 4.3 interval model (front bottom RE1bF ready): phase -> {(early?, exit)} ==")
for k, v in grid_pred.items():
    txt.append(f"  phi {k}: {v}")

# ---------------------------------------------------------------- ed6 VBL scan (handover pattern by family)
sc = list(csv.DictReader(SCAN6.open(encoding="utf-8")))
pat = defaultdict(Counter)
for r in sc:
    if r["src"] != "ed6_grid" or not r["event"]:
        continue
    st = json.loads(r["reapproach_starts"]) if r["reapproach_starts"] else []
    dfirst = diag_first(st, r["leg"])
    s = "E" if (dfirst is not None and dfirst <= E_LIMIT + 1e-9) else "N"
    side = "front" if r["leg"] in ("FL", "FR") else "rear"
    pat[(r["level"], r["timing"], side, r["event"])][(float(r["offset_s"]), s)] += 1
res["ed6_VBL_handover_by_family"] = {"|".join(f): {f"o{a}|{b}": n for (a, b), n in sorted(c.items())}
                                     for f, c in sorted(pat.items())}
txt.append("\n== ed6 VBL grid (treatment, published): E-pattern by family (front only shown) ==")
for f, c in sorted(pat.items()):
    if f[2] == "front":
        txt.append(f"  {'|'.join(f):<26} " + ", ".join(f"o{a}:{b}={n}" for (a, b), n in sorted(c.items())))

# ---------------------------------------------------------------- G' source sizes (unique conditions)
# (a) phase source: every cluster x 4 new phases
n_clusters = len(clusters)
e_fams = {fam(k) for k in e_clusters}
re1_clusters = [k for k in clusters if k[4] == "RE1bF"]
re1_e_fam_clusters = [k for k in re1_clusters if fam(k) in e_fams]
# (c) F_s source: new Fs replaces cluster Fs -> unique condition = family x new Fs (clusters differing
#     only in Fs collapse onto the same condition)
fs_conditions = {(fam(k), fs) for k in clusters for fs in (1.0, 3.0, 6.0)}
fs_cond_e = {c for c in fs_conditions if c[0] in e_fams}
res["G_sources"] = {
    "a_phase_candidates": n_clusters * 4,
    "a_phase_slots_one_per_cluster": n_clusters,
    "a_E_candidate_cluster_units_all_phases": len(e_clusters) * 4,
    "b_depth_RE1bF_clusters": len(re1_clusters),
    "b_depth_conditions_2_shapes": len(re1_clusters) * 2,
    "b_depth_E_family_conditions": len(re1_e_fam_clusters) * 2,
    "c_fs_naive_cluster_x_3": n_clusters * 3,
    "c_fs_unique_conditions": len(fs_conditions),
    "c_fs_unique_conditions_E_families": len(fs_cond_e),
    "E_families_wo_fs": len(e_fams),
}
txt.append("\n== G' source sizes ==")
for k, v in res["G_sources"].items():
    txt.append(f"  {k}: {v}")

# ---------------------------------------------------------------- census E (G1 lines; D keys are in G1 clusters)
g1 = json.loads(G1.read_text(encoding="utf-8"))
g1E, g1N, g1miss = [], 0, 0
for ln in g1["lines"]:
    j = ln["job"]
    tw = j["twin"]
    key = ckey(tw["level"], tw["fs_kN"], tw["timing"], tw["leg"], tw["event"]) + (round(float(j["offset_s"]), 4),)
    v = v0.get(key)
    if v is None:
        g1miss += 1
        continue
    if not ln["v0_pair"]["v0_pass"]:
        continue
    if isinstance(v["diag_first"], float) and v["diag_first"] <= E_LIMIT + 1e-9:
        g1E.append("|".join(map(str, key)) + f" diag {v['diag_first']}")
    else:
        g1N += 1
res["census_G1"] = {"lines": len(g1["lines"]), "v0_pass_E": len(g1E), "v0_pass_N": g1N,
                    "no_v0_match": g1miss, "E_lines": g1E}
txt.append(f"\n== census C-G (G1 171): V0-pass E {len(g1E)}, N {g1N}, unmatched {g1miss} ==")
for s in g1E:
    txt.append("  " + s)

(out / "s8r_frame.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
(out / "s8r_frame.txt").write_text("\n".join(txt), encoding="utf-8")
print("status ok")
