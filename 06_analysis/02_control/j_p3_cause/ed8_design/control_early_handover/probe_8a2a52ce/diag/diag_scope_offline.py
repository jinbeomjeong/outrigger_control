"""Offline (no run): which H-3 extensions of the P8-9 main lines fell on first runs and which on
re-trigger runs (RT2 window, ``_Reapproach.is_retrigger``), and what a "first-run-only" scope of
H-3 would leave exactly determined without a run:
  * = A    : the A trajectory has no contact end of a first run within T_r of its start (the
             variant never acts on the A path, so the variant line is the A line);
  * = H3   : every H-3 extension on the H3 trajectory is on a first run (the variant acts at the
             same points, so the variant line is the H3 line);
  * unknown: otherwise (a run is needed).
Record only; no new arm is run (user: re-selection only after a user decision).

Usage: conda run -n dynamics-dev python -I -B diag_scope_offline.py
Output: diag_scope_offline_out.txt, diag_scope_offline.csv
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = HERE.parent / "raw"
T_R = 0.5
recs = [json.loads(x) for x in (MAIN / "runs.jsonl").read_text("utf-8").splitlines()]
by = {}
for r in recs:
    arm = r["job"]["setting"].split("-")[1]
    key = json.dumps({k: v for k, v in r["job"].items() if k not in ("setting", "mask", "t4h_dir")},
                     sort_keys=True)
    by[(key, arm)] = r
rows, out = [], []
for (key, arm), r in sorted(by.items()):
    if arm != "H3":
        continue
    a = by[(key, "A")]
    la = json.loads((MAIN / "logs" / f"{a['p89']['stem']}_p89.json").read_text("utf-8"))
    lh = json.loads((MAIN / "logs" / f"{r['p89']['stem']}_p89.json").read_text("utf-8"))
    te = r.get("t_event_s") or 0.0
    a_first = {round(s["t"], 6): s["retrigger"] for s in la["starts"]}
    h_first = {round(s["t"], 6): s["retrigger"] for s in lh["starts"]}
    # A path: contact ends within T_r of start, by retrigger flag of the run
    a_short = [(round(e["t"] - te, 3), e["leg"], a_first.get(round(e["start_s"], 6)))
               for e in la["ends"] if e["outcome"] == "contact" and e["start_s"] is not None
               and e["t"] - e["start_s"] <= T_R + 1e-9 and e["exit_samples_seen"] >= 3]
    h_ext = [(round(h["t"] - te, 3), h["leg"], h_first.get(round(h["start_s"], 6)))
             for h in lh["h3"]]
    a_first_short = [x for x in a_short if x[2] is False]
    h_retrig_ext = [x for x in h_ext if x[2] is True]
    if r["commands_sha256"] == a["commands_sha256"]:
        verdict = "= A (H3 = A already)"
    elif not a_first_short:
        verdict = "= A"
    elif not h_retrig_ext:
        verdict = "= H3"
    else:
        verdict = "unknown"
    job = json.loads(key)
    label = f"{job['case']} {job.get('twin')} o{job.get('offset_s')} e{job.get('eps')}"
    rows.append({"key": label, "A_short_first_runs": a_first_short,
                 "A_short_retrig_runs": [x for x in a_short if x[2] is True],
                 "H3_ext_first": [x for x in h_ext if x[2] is False], "H3_ext_retrig": h_retrig_ext,
                 "variant_first_run_only": verdict})
    out.append(json.dumps(rows[-1]))
with (HERE / "diag_scope_offline.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    for row in rows:
        w.writerow({k: json.dumps(v) if isinstance(v, list) else v for k, v in row.items()})
text = "\n".join(out)
(HERE / "diag_scope_offline_out.txt").write_text(text, "utf-8")
print(text.encode("ascii", "replace").decode())
