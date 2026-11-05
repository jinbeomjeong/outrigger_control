"""K1 activity in the stored C4G2 + K1 bundles not rerun, no simulation. Classes per row:
A events recorded and complete (a start event would show): no retrigger -> same as C4G2 only.
B no re-approach start at all -> K1 cannot act -> same.
C command hash equals the stored same-code off row -> neither candidate acted -> same.
D otherwise unknown (starts present, no events) -> needs a C4G2-only run.
E core 27. Writes acceptance/c4g2_only/gap_check.json, prints a summary."""
import json
from pathlib import Path

import psutil

psutil.Process().cpu_affinity([27])
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
REV85 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85")
out = {}


def nm(e):
    return str(e.get("name")) if isinstance(e, dict) else str(e[-1]) if isinstance(e, (list, tuple)) else str(e)


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


# crawler
cr = load(ACC / "crawler/crawler_both.json")["runs"]
rows = []
for r in cr:
    names = [nm(e) for e in r.get("events", [])]
    rows.append({"key": r.get("key") or r.get("id") or r.get("case"), "n_events": len(names), "starts": sum(n.startswith("leg_reapproach_start") for n in names), "retrigger": sum(n.endswith(":retrigger") for n in names), "deferred": sum(n.startswith("leg_reapproach_deferred") for n in names), "values_events": r.get("values", {}).get("events") if isinstance(r.get("values", {}).get("events"), dict) else None, "wall_s": r.get("wall_s")})
print("crawler rows", len(rows), "with starts", sum(x["starts"] > 0 for x in rows), "retrigger", sum(x["retrigger"] > 0 for x in rows), "events max", max(x["n_events"] for x in rows), "sample names", [nm(e) for e in cr[0].get("events", [])][:8], "values.events", rows[0]["values_events"])
print("  cpu s", round(sum(x["wall_s"] or 0 for x in rows)))
out["crawler"] = rows

# soil_A + clip_A: runs without events
off = {r["key"]: r for r in load(REV85 / "finB2_A.json")["results"]}
for fname, label in (("soil/soil_A.json", "soil_A"), ("regression/clip_A.json", "clip_A")):
    doc = load(ACC / fname)
    rec = []
    for res in doc["results"]:
        o = off.get(res["key"])
        same_base = o is not None and o["base"].get("commands_sha256") == res["base"].get("commands_sha256")
        for i, run in enumerate(res["runs"]):
            orun = None
            if o is not None:
                orun = next((x for x in o["runs"] if x.get("timing") == run.get("timing") and x.get("event") == run.get("event")), None)
            same = orun is not None and orun.get("commands_sha256") == run.get("commands_sha256")
            cls = "C" if same else ("B" if not run["reapproach_starts"] else "D")
            rec.append({"key": res["key"], "timing": run.get("timing"), "event": run.get("event"), "starts": len(run["reapproach_starts"]), "same_as_off": same, "same_base": same_base, "class": cls, "pass": run.get("pass"), "job_wall_s": res.get("wall_s")})
    cnt = {c: sum(x["class"] == c for x in rec) for c in "BCD"}
    by = {}
    for x in rec:
        if x["class"] == "D":
            by.setdefault(x["key"], []).append(f"{x['timing']}/{x['event']}/{x['starts']}")
    print(label, "runs", len(rec), cnt, "base same as off", sorted({x["key"] for x in rec if x["same_base"]})[:3], "...")
    print("  D by job", json.dumps(by))
    print("  jobs wall", {r["key"]: r.get("wall_s") for r in doc["results"]}, "meta wall", doc["meta"].get("wall_s"), "workers", doc["meta"].get("workers"))
    out[label] = rec

# regression with events
for fname in ("clip_r79_L1L2", "clip_r79_L3L4"):
    d = load(ACC / f"regression/{fname}.json")["results"]
    r = [{"key": x["key"], "starts": sum(nm(e).startswith("leg_reapproach_start") for e in x["events"]), "retrigger": sum(nm(e).endswith(":retrigger") for e in x["events"])} for x in d]
    print(fname, "rows", len(r), "retrigger rows", sum(y["retrigger"] > 0 for y in r), "max starts", max(y["starts"] for y in r))
    out[fname] = r
d = load(ACC / "regression/clip_x426_D.json")["results"]
r = [{"id": x["id"], "starts": sum(nm(e).startswith("leg_reapproach_start") for e in x["events"]), "retrigger": sum(nm(e).endswith(":retrigger") for e in x["events"]), "n": len(x["events"]), "wall": x.get("wall_s_total")} for x in d]
print("clip_x426_D", r)
out["clip_x426_D"] = r
d = load(ACC / "regression/clip_x426_C.json")["results"]
print("clip_x426_C", [(x["key"], x.get("commands_sha256", "")[:8], x.get("warnings"), [k for k in x if "reapp" in k], x.get("wall_s")) for x in d])
for fname in ("clip_harness", "clip_p0"):
    doc = load(ACC / f"regression/{fname}.json")
    rec = doc["records"]
    r0 = rec[0]
    print(fname, "records", len(rec), "keys", list(r0)[:30])
    txt = json.dumps(rec)
    print("  text starts", txt.count("leg_reapproach_start"), "reapproach mentions", txt.count("reapproach"), "meta wall", doc["meta"].get("wall_s"), "comparison keys", list(doc["comparison"])[:6] if isinstance(doc["comparison"], dict) else type(doc["comparison"]).__name__)
    print("  rows", [{k: r.get(k) for k in ("id", "key", "case", "wall_s") if k in r} for r in rec[:2]], "reapproach fields", [k for k in r0 if "reapp" in k.lower() or "event" in k.lower() or "start" in k.lower()], )
(ACC / "c4g2_only/gap_check.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
