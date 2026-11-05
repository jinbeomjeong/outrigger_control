"""Reuse counts for the C4G2-only acceptance. Noise: rows of the both run with no retrigger deferral event. Grid: jobs where every run has no re-approach start (no re-trigger window, K1 cannot act). Short output only."""
import json
from pathlib import Path

ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")


def partial(p):
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        out[r["key"]] = r
    return out


def ev_name(e):
    if isinstance(e, dict):
        return str(e.get("name"))
    if isinstance(e, (list, tuple)):
        return str(e[-1])
    return str(e)


for name in ("r79_L1L2", "r79_L3"):
    rows = partial(ACC / f"noise/{name}.json.partial.jsonl")
    n = len(rows)
    act = [k for k, r in rows.items() if any(ev_name(e).endswith(":retrigger") for e in r["events"])]
    anydef = sum(any("leg_reapproach_deferred" in ev_name(e) for e in r["events"]) for r in rows.values())
    lv = {}
    for k in rows:
        lv.setdefault(rows[k]["level"], [0, 0])[0] += 1
    for k in act:
        lv[rows[k]["level"]][1] += 1
    w = sum(rows[k]["wall_s"] for k in act)
    print(name, "rows", n, "K1 acted", len(act), "any deferred", anydef, "by level [n, acted]", lv, "CPU s acted", round(w), "CPU s all", round(sum(r["wall_s"] for r in rows.values())))
    print("  sample event", [ev_name(e) for e in next(iter(rows.values()))["events"]][:4], "n events first", len(next(iter(rows.values()))["events"]))
    print("  settings keys with retrig/hold", {k: v for k, v in next(iter(rows.values()))["controller_settings"].items() if "retrig" in k or "hold" in k})
    by = {}
    for k in act:
        by[rows[k]["harness"]] = by.get(rows[k]["harness"], 0) + 1
    print("  acted by harness", by)
    if name == "r79_L1L2":
        act12 = set(act)
        split = partial(ACC / "split/r79_c4g2.json.partial.jsonl")
        for k, r in split.items():
            b = rows[k]
            a_base = {x: r["base"][x] for x in r["base"] if r["base"].get(x) != b["base"].get(x)}
            print("  split", k[13:50], "in acted", k in act12, "r79 same", r["r79"] == b["r79"], "events same", r["events"] == b["events"], "base diff keys", list(a_base)[:6], "settings same", r["controller_settings"] == b["controller_settings"])
for f in ("grid_r67_main", "grid_r67_top", "grid_r69_top", "grid_r69_bottom"):
    g = json.loads((ACC / f"grid/{f}.json").read_text(encoding="utf-8"))
    res = g["results"]
    runs = sum(len(x["runs"]) for x in res)
    zero_jobs = [x["key"] for x in res if all(not u["reapproach_starts"] for u in x["runs"])]
    zero_runs = sum(not u["reapproach_starts"] for x in res for u in x["runs"])
    one_runs = sum(len(u["reapproach_starts"]) == 1 for x in res for u in x["runs"])
    print(f, "jobs", len(res), "runs", runs, "runs with 0 starts", zero_runs, "1 start", one_runs, "jobs all zero", len(zero_jobs), "wall", g["meta"]["wall_s"], "workers", g["meta"]["workers"], "cpu", round(sum(x.get("wall_s", 0) for x in res)), zero_jobs[:3], "offsets", g["meta"].get("offsets_s"))
