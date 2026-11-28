"""Step 10: independent coarse check (no judge code) of the a_phase E slots' own A/A pairs:
find the condition and candidate lines by job (json of the job dict), take the first candidate
whose own 6.3 layer equals the condition's (E: a diagonal start with 0 <= t, round(t,3) <= 0.45),
and compare the discrete fields that carry C-J items (final phase, fault events, event gates,
warning set, t_ready_back). Record only. Writes aphase_E_hand_check.csv."""
import csv
import json
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
RUNS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248")
KEYS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\keys_seal_41e107e9\heldout_g_ed8.json")
DIAG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
rows = {}
for p in (r"ho_v0_a1\ed8_heldout_v0.jsonl", r"ho_aa2_a1\ed8_heldout_aa2.jsonl", r"ho_aa3_a1\ed8_heldout_aa3.jsonl"):
    with (RUNS / p).open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            job = {k: v for k, v in row["job"].items() if k not in ("mask", "t4h_dir")}
            rows[json.dumps(job, sort_keys=True)] = row


def find(job):
    return rows.get(json.dumps({k: v for k, v in job.items() if k not in ("mask", "t4h_dir")}, sort_keys=True))


def layer(job, row):
    twin = job.get("twin") or {}
    if twin.get("event") != "RE1bF":
        return "N"
    d = DIAG[twin["leg"]]
    starts = (row.get("event_output") or {}).get("reapproach_starts") or []
    return "E" if any(leg == d and t >= 0 and round(t, 3) <= 0.450 for t, leg in starts) else "N"


def fields(row):
    eo = row.get("event_output") or {}
    return {"final": row.get("final_phase"), "faults": tuple(row["values"]["events"]["fault_events"]),
            "gates_all": all((eo.get("gates") or {}).values()), "warn": tuple(sorted(eo.get("warnings") or [])),
            "t_back": eo.get("t_ready_back_s")}


lines = json.loads(KEYS.read_text(encoding="utf-8"))["lines"]
out = []
for i, line in enumerate(lines):
    if line["source"] != "a_phase":
        continue
    cond = find(line["v0_pair"]["job"])
    L = layer(line["v0_pair"]["job"], cond)
    if L != "E":
        continue
    chosen = None
    for k, job in enumerate(line["aa_order"][:3], start=1):
        r = find(job)
        if r is not None and layer(job, r) == L:
            chosen = (k, job, r)
            break
    fc = fields(cond)
    rec = {"index": i, "slot": line["slot"], "o": line["v0_pair"]["job"]["offset_s"], "cond": fc}
    if chosen:
        fo = fields(chosen[2])
        rec.update({"try": chosen[0], "o2": chosen[1]["offset_s"], "cand": fo,
                    "same_discrete": (fc["final"], fc["faults"], fc["gates_all"], fc["warn"])
                    == (fo["final"], fo["faults"], fo["gates_all"], fo["warn"])})
    out.append(rec)
with open(OUT / "aphase_E_hand_check.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["index", "slot", "o", "try", "o2", "cond_final", "cand_final", "cond_gates_all",
                "cand_gates_all", "warn_equal", "t_back_cond", "t_back_cand", "same_discrete"])
    for r in out:
        c, d = r["cond"], r.get("cand", {})
        w.writerow([r["index"], r["slot"], r["o"], r.get("try"), r.get("o2"), c["final"], d.get("final"),
                    c["gates_all"], d.get("gates_all"), c["warn"] == d.get("warn"), c["t_back"],
                    d.get("t_back"), r.get("same_discrete")])
        print(r["index"], r["slot"], r["o"], "->", r.get("o2"), "try", r.get("try"), "same_discrete", r.get("same_discrete"),
              "t_back", c["t_back"], d.get("t_back"))
print("a_phase E slots", len(out), "with a same-layer pair", sum("cand" in r for r in out),
      "discrete differences", sum(r.get("same_discrete") is False for r in out))
