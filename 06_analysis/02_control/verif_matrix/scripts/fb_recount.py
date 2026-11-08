"""Independent recount of FB acceptance criteria C-1..C-10.

Reads only the jsonl result files and implements the criteria from the
sealed rule text (fb_targeted_rules.md section 4 + rev1..rev3). It does not
import fb_judge / fb_targeted.
"""
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5")
OUT = Path(__file__).with_name("recount_out.json")


def load(p):
    with open(p, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def setting(r):
    return r["job"]["setting"]


def eta(r):
    return r["job"].get("eta_v")


def is_vb085(r):
    return setting(r) == "VB" and (eta(r) is None or abs(eta(r) - 0.85) < 1e-12)


def names(r):
    return {k.split(":")[0] for k in (r.get("event_names") or {})}


def has_d1(r):
    d = r.get("d1")
    return isinstance(d, dict) and "verdict" in d


def t_ready(r):
    t = (r.get("values") or {}).get("times", {}).get("t_first_ready_s")
    return t


# ---- load
B = {}
for n in range(6):
    B[n] = load(ROOT / "fb" / f"fb_F{n}.jsonl")
las_rows = load(ROOT / "las" / "las_T1.jsonl") + load(ROOT / "las" / "las_T2.jsonl")
las_b0 = {r["d1"]["key"]: r for r in las_rows if r["las"]["candidate"] == "b0" and r["las"]["mode"] == "act"}
t1_keys = sorted({r["d1"]["key"] for r in load(ROOT / "las" / "las_T1.jsonl")})

# ---- pairs per bundle (F-1..F-4)
pairs = {}  # bundle -> list of (key, L, LF)
for n in (1, 2, 3, 4):
    lf = {r["fb"]["key"]: r for r in B[n] if r["fb"]["candidate"] == "LF"}
    if n == 2:
        L = {k: las_b0[k] for k in lf}
    else:
        L = {r["fb"]["key"]: r for r in B[n] if r["fb"]["candidate"] == "L"}
    assert set(L) == set(lf), (n, set(L) ^ set(lf))
    pairs[n] = [(k, L[k], lf[k]) for k in sorted(lf)]

res = {}

# ---- C-1
c1 = []
for n in (1, 2, 3, 4):
    for k, L, F in pairs[n]:
        if is_vb085(F):
            c1.append((n, k, F["fb"]["saturation_s"]["all"]["any_s"]))
res["C-1"] = dict(n=len(c1), max_s=max(v for *_, v in c1), over=[x for x in c1 if x[2] > 0.01])

# ---- C-2
c2 = []
c2_ref = []
trunc = 0
h4 = defaultdict(set)
for n in (1, 2, 3, 4):
    for k, L, F in pairs[n]:
        if F["fb"].get("events_truncated") or (L.get("fb") or {}).get("events_truncated"):
            trunc += 1
        msgs = []
        if has_d1(F):
            vl, vf = L["d1"]["verdict"], F["d1"]["verdict"]
            if vl == "pass" and vf == "fail":
                msgs.append(f"(a) pass->fail {F['d1']['fail_items']}")
            if vl != vf:
                c2_ref.append((n, k, vl, vf))
            fl = set(L["d1"].get("fail_items") or [])
            new = [x for x in (F["d1"].get("fail_items") or []) if x not in fl and (x.startswith("P3-2") or x.startswith("G6-2"))]
            if new:
                msgs.append(f"(a) new {new}")
        else:
            if L["final_phase"] == "ready" and F["final_phase"] != "ready":
                msgs.append(f"(b) ready->{F['final_phase']}")
        newfw = sorted(x for x in names(F) - names(L) if x.startswith("FAULT") or x.startswith("WARN"))
        if newfw:
            msgs.append(f"(c) new {newfw}")
        if msgs:
            c2.append((n, k, msgs))
            h4[n].add(k)
res["C-2"] = dict(pairs=sum(len(v) for v in pairs.values()), violations=c2, verdict_changes=c2_ref,
                  truncated_pairs=trunc, h4={f"F-{n}": len(v) for n, v in h4.items()})

# ---- C-3
lf2 = {k: F for k, L, F in pairs[2]}
c3 = [(k, lf2[k]["d1"]["F_judged_min_N"] / 1e3, las_b0[k]["d1"]["F_judged_min_N"] / 1e3) for k in t1_keys]
res["C-3"] = dict(n=len(c3), rows=c3, min_kN=min(x[1] for x in c3), under=[x for x in c3 if x[1] < 10.4])

# ---- C-4
same, diff = [], []
d1_vs_values = 0
for n in (1, 2, 3, 4):
    for k, L, F in pairs[n]:
        tl, tf = t_ready(L), t_ready(F)
        for r in (L, F):
            if has_d1(r) and r["d1"].get("t_ready_s") is not None and t_ready(r) is not None:
                if abs(r["d1"]["t_ready_s"] - t_ready(r)) > 1e-6:
                    d1_vs_values += 1
        if tl is None or tf is None:
            continue
        dt = tf - tl
        if names(L) == names(F):
            same.append((n, k, round(dt, 6)))
        else:
            diff.append((n, k, round(dt, 6), sorted(names(F) - names(L)), sorted(names(L) - names(F))))
dts = [x[2] for x in same]
res["C-4"] = dict(n_same=len(same), median=statistics.median(dts), max=max(dts),
                  over5=[x for x in same if x[2] > 5.0 + 1e-9],
                  top=sorted(same, key=lambda x: -x[2])[:12],
                  n_diff=len(diff), diff_by_bundle={f"F-{n}": sum(1 for x in diff if x[0] == n) for n in (1, 2, 3, 4)},
                  d1_t_ready_mismatch=d1_vs_values)
# per-setting medians
by = defaultdict(list)
for n, k, dt in same:
    s = "V0" if "|V0|" in k else ("VB" if "|VB|" in k else "?")
    by[(n, s)].append(dt)
res["C-4"]["median_by_bundle_setting"] = {f"F-{n}|{s}": (len(v), statistics.median(v), max(v)) for (n, s), v in sorted(by.items())}

# ---- C-5 / C-6
c5, c6 = [], []
for k, L, F in pairs[1]:
    e = eta(F)
    if setting(F) == "VB" and e is not None and abs(e - 0.80) < 1e-9:
        c5.append((k, F["fb"]["u9_values"]["longest_ge3_s"], F["fb"]["saturation_s"]["touch"]["any_s"]))
    if setting(F) == "VB" and e is not None and abs(e - 0.70) < 1e-9:
        b = F["fb"]["budget"]
        cuts = b["cuts"]
        delay = (min(c["t_s"] for c in cuts) - b["t_first_touch_s"]) if cuts else None
        c6.append((k, delay, F["fb"]["u9_values"]["longest_ge3_s"]))
res["C-5"] = dict(n=len(c5), viol=[x for x in c5 if x[1] > 0.01 or x[2] > 1.0], rows=c5)
res["C-6"] = dict(n=len(c6), viol=[x for x in c6 if x[1] is None or not (-1e-9 <= x[1] <= 1.0 + 1e-9) or x[2] > 0.01], rows=c6)

# ---- C-7
f0 = B[0]
h = {(r["fb"]["key"], r["fb"]["candidate"]): r["commands_sha256"] for r in f0}
c7 = []
for key in sorted({k for k, _ in h}):
    c7.append((key, h[(key, "L")] == h[(key, "LF-off")], h[(key, "L")] == las_b0[key]["commands_sha256"]))
res["C-7"] = c7

# ---- C-8
c8 = []
for n in (2, 3, 4):
    for k, L, F in pairs[n]:
        if has_d1(F):
            c8.append((n, k, (F["d1"]["stroke_max_m"] - L["d1"]["stroke_max_m"]) * 1e3))
res["C-8"] = dict(n=len(c8), max_mm=max(x[2] for x in c8), over=[x for x in c8 if x[2] > 1.0])

# ---- C-9
c9 = []
for n in (1, 2, 3, 4):
    for k, L, F in pairs[n]:
        if is_vb085(F) or setting(F) == "V0":
            c9.append((n, k, len(F["fb"]["budget"]["cuts"]), "INFO_FLOW_BUDGET_CUT" in names(F)))
res["C-9"] = dict(n=len(c9), viol=[x for x in c9 if x[2] or x[3]])

# ---- C-10
ol = {(r["fb"]["key"], r["fb"]["candidate"]): r["fb"]["open_loop"] for r in B[5]}
c10 = []
for (k, c), o in ol.items():
    if c == "OL-LF" and "|VB|" in k:
        kv = k.replace("|VB|", "|V0|")
        ref = ol[(kv, "OL-L")]
        mag = math.hypot(o["roll_change_deg"], o["pitch_change_deg"])
        mref = math.hypot(ref["roll_change_deg"], ref["pitch_change_deg"])
        c10.append((k, o["stroke_spread_mm"], mag, mref, o["stroke_spread_mm"] <= 1.0 and mag <= mref + 0.05))
res["C-10"] = c10

OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
for k, v in res.items():
    s = json.dumps(v, default=str)
    print(k, s[:1800])
