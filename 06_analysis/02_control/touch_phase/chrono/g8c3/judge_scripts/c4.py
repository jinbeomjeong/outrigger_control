"""TOUCH latch of the raised leg: harness rows (F_s 4 traced, F_s 0 stored) against Chrono metrics."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono\g8c3\g8c3_values.json")
H0 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s8\rev70\r71_p28acc_harness_Fs0.json")
for line in (HERE / "out1.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    if r["key"].startswith("L1") and r["key"].split("|")[3] == "29":
        print("harness Fs4", r["tag"], json.dumps(r["base_keys"]["touch"])[:600])
doc = json.loads(V.read_text(encoding="utf-8"))
for cid, m in doc["metrics"].items():
    t = m["touch"]
    print("chrono", cid, {k: t.get(k) for k in ("first_contact_s", "latch_s", "T3_post_contact_stroke_mm", "T2_latch_after_contact_s", "crawler_min_kN")}, "t_touch", t["span_s"])
if H0.exists():
    d = json.loads(H0.read_text(encoding="utf-8"))
    rows = d if isinstance(d, list) else (d.get("results") or d.get("rows"))
    n = 0
    for r in rows:
        k = r.get("key", "") if isinstance(r, dict) else ""
        if "RL" in k and "230" in k:
            print("harness Fs0", k, json.dumps(r.get("touch"))[:500], r.get("stroke_max_run_mm"), r.get("t_loc"), [e for e in r.get("events", []) if "ANCHOR" in str(e)])
            n += 1
    print("Fs0 rows matched", n, "of", len(rows), "first keys", [r.get("key") for r in rows[:4]] if rows and isinstance(rows[0], dict) else type(rows))
else:
    print("no", H0)
