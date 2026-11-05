"""v4.4 B-only recomputation (pad A rows removed). Read-only on 06_analysis."""
import json, collections
from pathlib import Path

R = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9")
OUT = Path(__file__).with_name("agg_b_out.txt")
L = []
def p(*a):
    L.append(" ".join(str(x) for x in a))
def att(r):
    a = r["att_end_deg"]
    return max(abs(v) for v in a) if isinstance(a, list) else a
def load(x):
    return json.loads((R / x).read_text(encoding="utf-8"))
def pad(i):
    t = [x for x in str(i).split("|") if x in ("A", "B")]
    return t[0] if t else "-"
def soil(i):
    for s in ("rigid", "G1", "J1", "J2", "S1"):
        if f"|{s}|" in f"|{i}|" or str(i).split("|")[1:2] == [s]:
            return s
    return "?"

# ---------- p3b ----------
p0 = [r for r in load("rev85/finB2_p0.json")["records"] if r["suite"] == "p3b"]
old = {r["id"]: r for r in load("rev83/R2DS_p3b.json")["records"]}
soilB = [r for r in p0 if pad(r["id"]) == "B"]
p("## p3b soil B n", len(soilB), collections.Counter(r["verdict"] for r in soilB))
p(" att max", max(att(r) for r in soilB), "minF min", min(r["min_force_kN"] for r in soilB),
  "READY", min(r["t_ready_s"] for r in soilB), max(r["t_ready_s"] for r in soilB),
  "rut min", min(r["rut_ready_mm"] for r in soilB))
ch = [r for r in soilB if r["id"] in old and old[r["id"]]["hash"] != r["hash"]]
p(" R9 changed B", len(ch), collections.Counter(soil(r["id"]) for r in ch))
if ch:
    d_rut = [r["rut_ready_mm"] - old[r["id"]]["rut_ready_mm"] for r in ch]
    d_rd = [r["t_ready_s"] - old[r["id"]]["t_ready_s"] for r in ch]
    d_att = [att(r) - att(old[r["id"]]) for r in ch]
    p(" d_rut", round(min(d_rut), 2), round(max(d_rut), 2), "d_ready", round(min(d_rd), 2), round(max(d_rd), 2),
      "d_att", round(min(d_att), 4), round(max(d_att), 4))
# level and Fs diffs per soil (B)
by = {r["id"]: r for r in soilB}
for s in ("G1", "S1", "J2", "J1"):
    lv = [by[f"base|{s}|B|{l}|Fs4"] for l in ("top", "middle", "bottom")]
    fs = [by[f"base|{s}|B|top|Fs{f}"] for f in (0, 4, 8)]
    p(f" {s}B level READY", [round(x['t_ready_s'], 1) for x in lv], "minF bottom-top", round(lv[2]['min_force_kN'] - lv[0]['min_force_kN'], 2),
      "Fs READY", [round(x['t_ready_s'], 1) for x in fs])
p(" rigid", len([r for r in p0 if pad(r["id"]) == "-"]))

# ---------- slope ----------
hr = load("rev85/finB2_harness_rejudged.json")["records"]
sl = [r for r in hr if r["suite"] == "slope"]
old_sl = {r["id"]: r for r in load("rev83/R2DS_slope_rejudged.json")["records"]}
B = [r for r in sl if pad(r["id"]) == "B"]
A = [r for r in sl if pad(r["id"]) == "A"]
p("## slope B", len(B), "A", len(A), "nopad", len([r for r in sl if pad(r["id"]) == "-"]))
p(" B verdict", collections.Counter(r["verdict"] for r in B))
for s in ("rigid", "G1", "J1", "J2", "S1"):
    rs = [r for r in B if soil(r["id"]) == s]
    p(f"  {s}", len(rs), collections.Counter(r["verdict"] for r in rs))
for s in ("rigid", "G1", "J1", "J2", "S1"):
    rs = [r for r in A if soil(r["id"]) == s]
    p(f"  A {s}", len(rs), collections.Counter(r["verdict"] for r in rs))
stops = [r for r in B if r["verdict"] == "stroke_limited_stop"]
p(" stops", len(stops), "minF_after_off min", round(min(r["soil_stop"]["min_true_Fcyl_after_off_kN"] for r in stops), 2),
  "max moving bar", max(r["soil_stop"]["moving_pressure"]["max_moving_bar"] for r in stops),
  "crawler loaded", sum(bool(r["soil_stop"].get("stop_with_crawler_loaded")) for r in stops))
passes = [r for r in B if r["verdict"] == "pass"]
p(" pass att max", round(max(att(r) for r in passes), 4), "minF min", round(min(r["min_force_kN"] for r in passes), 2),
  "READY max", round(max(r["t_ready_s"] for r in passes), 1))
softpass = [r for r in passes if soil(r["id"]) in ("J1", "J2", "S1")]
p(" soft pass", len(softpass))
fails = [r for r in B if r["verdict"] == "fail"]
p(" fails", len(fails))
for r in fails:
    ss = r.get("soil_stop") or {}
    p("   ", r["id"], r["failed_rows"], "stop_event", ss.get("stop_event"), "crawler_loaded", ss.get("stop_with_crawler_loaded"),
      "Fstop", ss.get("min_true_Fcyl_at_stop_kN"))
tr = collections.Counter((old_sl[r["id"]]["verdict"], r["verdict"]) for r in B if r["id"] in old_sl)
p(" transitions old->new", dict(tr))
crawl_old = [(r["id"], old_sl[r["id"]].get("crawler_N_max_after_ready")) for r in B
             if r["id"] in old_sl and (old_sl[r["id"]].get("crawler_N_max_after_ready") or 0) > 1000]
p(" old crawler after ready >1kN (B)", crawl_old)
p(" new crawler after ready max", max((r.get("crawler_N_max_after_ready") or 0) for r in B))
dirs = collections.Counter()
for r in B:
    d = r["id"].split("|")[4].split("@")[0]
    dirs[(d, r["verdict"])] += 1
p(" by dir", sorted(dirs.items()))
# J1 H3 rows
j1 = [r for r in B if r["id"].startswith("H3|J1|B|top|") and r["id"].split("|")[4].split("@")[0] in ("nose_down", "roll_pos", "edge_nd")]
p(" H3 J1 B top 3dir", len(j1), collections.Counter(r["verdict"] for r in j1), [r["id"] for r in j1 if r["verdict"] != "pass"])

# ---------- h9 ----------
h9 = load("rev85/finB2_h9.json")["records"]
for pd in ("A", "B"):
    rs = [r for r in h9 if pad(r["id"]) == pd]
    p(f"## h9 {pd}", len(rs), collections.Counter(r["verdict"] for r in rs))
    bnd = [r["id"] for r in rs if r["verdict"] == "pass" and soil(r["id"]) in ("J1", "J2")
           and ((682.8 - r["max_stroke_mm"]) < 23 or (r["rut_ready_mm"] - 25) < 15)]
    p("   boundary(stroke<23 or gap<15)", len(bnd), bnd)
for r in h9:
    if pad(r["id"]) == "B":
        p("   ", r["id"], r["verdict"], round(r["max_stroke_mm"], 1), round(r["rut_ready_mm"] or -1, 1))

# ---------- h6 ----------
h6 = [r for r in hr if r["suite"] == "h6"]
for pd in ("A", "B"):
    rs = [r for r in h6 if pad(r["id"]) == pd]
    c = collections.Counter()
    for r in rs:
        m = "m1.2" if "m1.2" in r["id"] else ("m1.1" if "m1.1" in r["id"] else "m1.0")
        c[(m, soil(r["id"]), r["verdict"])] += 1
    p(f"## h6 {pd}", len(rs), sorted(c.items()))

# ---------- B5 wide ----------
def b5(path, tag):
    recs = load(path)["records"]
    keep = [r for r in recs if pad(r["src"]) != "A"]
    p(f"## B5 {tag} all {len(recs)} keep {len(keep)} cases {len({r['src'] for r in keep})}")
    for ctl in ("C2", "ABL", "IND"):
        rs = [r for r in keep if r["controller"] == ctl]
        stop = sum(1 for r in rs if r.get("official_verdict") == "stroke_limited_stop")
        p(f"  {ctl} n {len(rs)} lite_pass {sum(bool(r['lite_pass']) for r in rs)} official_stop {stop} crawler_fail {sum(bool(r.get('crawler_liftoff_fail')) for r in rs)}",
          "official", dict(collections.Counter(r.get("official_verdict") for r in rs)))
    return {(r["src"], r["controller"]): r for r in keep}
new = b5("rev84/fin2_b5_wide_official.json", "final")
oldb = b5("rev84/b5_wide_official.json", "R7")
# C2 transitions old lite -> new (lite pass / official stop / fail)
def cls(r):
    if r.get("official_verdict") == "stroke_limited_stop":
        return "stop"
    return "pass" if r["lite_pass"] else "fail"
t = collections.Counter()
for (src, ctl), r in new.items():
    if ctl == "C2" and (src, "C2") in oldb:
        t[(("pass" if oldb[(src, 'C2')]["lite_pass"] else "fail"), cls(r))] += 1
p(" C2 old lite -> new", dict(t))
x = sum(1 for (src, ctl), r in new.items() if ctl == "C2" and cls(r) == "stop" and new[(src, "IND")]["lite_pass"])
p(" C2 stop & IND pass", x)
oldfail = [src for (src, ctl), r in oldb.items() if ctl == "C2" and not r["lite_pass"]]
p(" old C2 lite fail", len(oldfail), "slope", sum(1 for s in oldfail if not s.startswith("g6")), "g6", sum(1 for s in oldfail if s.startswith("g6")))
newfail = [src for (src, ctl), r in new.items() if ctl == "C2" and cls(r) == "fail"]
p(" new C2 fail", len(newfail), newfail)
oldslp = [src for (src, ctl), r in oldb.items() if ctl == "C2" and r["lite_pass"] and new[(src, "C2")].get("official_verdict") == "stroke_limited_stop"]
p(" old lite pass -> stop", len(oldslp))
OUT.write_text("\n".join(L), encoding="utf-8")
print("ok")
