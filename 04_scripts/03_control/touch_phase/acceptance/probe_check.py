"""After the probes: did the candidates act, what code ran, and does the harness result match the first probe."""
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "probe_out"
for name in ("d8", "crawler"):
    p = OUT / name / "r.json"
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        print(name, json.dumps(d["meta"])[:520])
        for r in d["runs"]:
            print("  ", r["id"], r.get("error", "")[:160], {k: r.get(k) for k in ("min_true_cyl_force_kN", "t_ready_s", "fails", "hold_events", "retrigger_deferred", "final_phase", "harness_class", "failed_rows", "wall_s")}, [e for e in r.get("events", []) if "HOLD" in e[1]])
for name in ("L2", "L3"):
    d = json.loads((OUT / name / "r.json").read_text(encoding="utf-8"))
    for r in d["results"]:
        ev = [e for e in r.get("events", []) if "HOLD" in str(e)]
        print(name, r["key"], "wall", r["wall_s"], "peak_MB", r.get("worker_peak_wset_MB"), "hold", ev[:1], "base keys", list(r["base"].keys())[:6] if name == "L2" and r is d["results"][0] else "")
d = json.loads((OUT / "grid" / "r.json").read_text(encoding="utf-8"))
print("grid", d["meta"].get("n_jobs"), [(r["key"], r.get("wall_s"), len(r["runs"]), r["runs"][0].get("reapproach_starts")) for r in d["results"]])
d = json.loads((OUT / "soil" / "r.json").read_text(encoding="utf-8"))
print("soil", [(r["key"], r.get("wall_s"), len(r["runs"])) for r in d["results"]])
for f in glob.glob(str(OUT / "*" / "stdout.log")):
    txt = Path(f).read_text(encoding="utf-8", errors="replace")
    print(Path(f).parent.name, "guard lines", sorted({l for l in txt.splitlines() if "acc_guard" in l})[:4])
