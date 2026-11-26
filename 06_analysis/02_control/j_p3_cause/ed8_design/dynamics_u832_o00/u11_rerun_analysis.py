"""Analysis of the u10 instrumented reruns.

Usage: python -I -B u11_rerun_analysis.py <rerun_dir> <out_folder> <stored_g1_jsonl> <stored_j9main_jsonl>

Writes (out_folder):
  u11_repro.csv           rerun vs stored commands_sha256 (VBM lines of G1 / j9main)
  u11_runs.csv            per run: pair union, lift intervals of the pair legs, re-approach
                          starts / ends of the pair legs relative to the event, sample phase
  u11_periods.csv         per run and control period (event - 0.2 s .. + 2.5 s): lower load
                          estimate, start / exit levels, low counts, active runs (exit samples)
  u11_lift_intervals.csv  1 ms lift intervals (pad contact force <= 0) of every leg after the event
  u11_s7_touch.json       S7 eps 0 / 0.001 first-touch times (oil force > 3 kN)
Column definitions: provenance (u12).
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")
DIAG = {0: 3, 3: 0, 1: 2, 2: 1}
rerun, out = Path(sys.argv[1]), Path(sys.argv[2])
STORED = {"g1": Path(sys.argv[3]), "j9main": Path(sys.argv[4])}


def jkey(job):
    j = {k: v for k, v in job.items() if k not in ("mask", "t4h_dir", "_scratch")}
    return json.dumps(j, sort_keys=True)


def stored_index():
    idx = {}
    for label, path in STORED.items():
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                if "error" in r:
                    continue
                if r["job"].get("setting") != "VBM":
                    continue
                idx[jkey(r["job"])] = (label, r.get("commands_sha256"),
                                       (r.get("event_output") or {}).get("pair_union_s"),
                                       ((r.get("values") or {}).get("times") or {}).get("t_first_ready_s"))
    return idx


def last_segment(rows):
    """Entries after the last time reset (prefix run + branch of the judged plant)."""
    t = np.array([r["t"] for r in rows])
    if len(t) < 2:
        return rows
    resets = np.flatnonzero(np.diff(t) < -1e-9)
    start = resets[-1] + 1 if len(resets) else 0
    # the timeline run is followed by the prefix run, which restarts at t = 0.1
    return rows[start:]


def intervals(mask, t):
    idx = np.flatnonzero(mask)
    if not idx.size:
        return []
    br = np.flatnonzero(np.diff(idx) > 1)
    st = np.r_[idx[0], idx[br + 1]]
    en = np.r_[idx[br], idx[-1]]
    return [(float(t[a]), float(t[b]) + 1e-3) for a, b in zip(st, en)]


records = [json.loads(x) for x in (rerun / "runs.jsonl").read_text(encoding="utf-8").splitlines()
           if x.strip()]
idx = stored_index()
repro, runs, periods, lifts = [], [], [], []
s7 = {}
for rec in records:
    job = rec["job"]
    stem = (rec.get("u8") or {}).get("stem")
    key = jkey(job)
    st = idx.get(key)
    repro.append({"setting": job["setting"], "case": job["case"], "eps": job.get("eps"),
                  "offset_s": job.get("offset_s"), "twin": json.dumps(job.get("twin")),
                  "error": rec.get("error"), "rerun_sha": rec.get("commands_sha256"),
                  "stored_src": st[0] if st else None, "stored_sha": st[1] if st else None,
                  "same_sha": (st[1] == rec.get("commands_sha256")) if st else None,
                  "rerun_pair_union_s": (rec.get("event_output") or {}).get("pair_union_s"),
                  "stored_pair_union_s": st[2] if st else None})
    if rec.get("error") or stem is None:
        continue
    log = json.loads((rerun / "logs" / f"{stem}_reapp.json").read_text(encoding="utf-8"))
    if job["case"] == "S7":
        s7[f"eps{job['eps']}"] = {"touch_first_t_s": log["touch"],
                                  "t_first_ready_s": rec["values"]["times"]["t_first_ready_s"],
                                  "t_touch_end_s": rec["values"]["times"]["t_touch_end_s"],
                                  "commands_sha256": rec["commands_sha256"]}
        continue
    npz = np.load(rerun / "logs" / f"{stem}_rows.npz")
    t_ev = float(npz["t_ev"])
    rows = npz["rows"]
    tr = rows[:, 0] - t_ev
    contact = rows[:, 1:5]
    seg = last_segment(log["reapp"])
    ev = rec["event_output"]
    tw = job["twin"]
    leg = LEGS.index(tw["leg"])
    pair = [leg, DIAG[leg]]
    run_id = f"{job['setting']}|{tw['level']}-{tw['leg']}-Fs{tw['fs_kN']:g}-{tw['event']}-o{job['offset_s']}"
    # lift intervals after the event
    after = tr >= 0.0
    for i in range(4):
        for a, b in intervals(after & (contact[:, i] <= 0.0), tr):
            lifts.append({"run": run_id, "leg": LEGS[i], "start_s": round(a, 3), "end_s": round(b, 3),
                          "dur_s": round(b - a, 3)})
    # control periods around the event
    starts, ends = {}, {}
    prev_active = set()
    first_sample = None
    for p in seg:
        trel = p["t"] - t_ev
        if trel < -0.25 or trel > 3.5:
            continue
        if trel > 1e-9 and first_sample is None:
            first_sample = round(trel, 4)
        active = set(int(k) for k in p["active"])
        for k in active - prev_active:
            starts.setdefault(LEGS[k], []).append(round(trel, 3))
        for k in prev_active - active:
            ends.setdefault(LEGS[k], []).append(round(trel, 3))
        prev_active = active
        if trel <= 2.5:
            periods.append({"run": run_id, "t_rel_s": round(trel, 3), "phase": p["phase"],
                            **{f"load_{LEGS[i]}_kN": round(p["load_lower_N"][i] / 1e3, 2) for i in range(4)},
                            "start_level_kN": round(p["start_level_N"] / 1e3, 2),
                            "exit_level_kN": round(p["exit_level_N"] / 1e3, 2),
                            **{f"low_{LEGS[i]}": p["low_after"][i] for i in range(4)},
                            "active": ";".join(f"{LEGS[int(k)]}:{v['exit_seen']}"
                                               + (":rt" if v["retrigger"] else "")
                                               for k, v in p["active"].items())})
    # event-leg reload: first 1 ms time after its first lift where contact force >= exit level
    exit_level = seg[-1]["exit_level_N"] if seg else np.nan
    true_F = rows[:, 5:9]
    lift_ev = intervals(after & (contact[:, leg] <= 0.0), tr)
    t_reload = None
    if lift_ev:
        m = (tr > lift_ev[0][1]) & (true_F[:, leg] >= exit_level)
        if m.any():
            t_reload = round(float(tr[np.flatnonzero(m)[0]]), 3)
    lift_dg = intervals(after & (contact[:, pair[1]] <= 0.0), tr)
    runs.append({"run": run_id, "setting": job["setting"], "level": tw["level"], "leg": tw["leg"],
                 "fs_kN": tw["fs_kN"], "event": tw["event"], "offset_s": job["offset_s"],
                 "t_ev_s": round(t_ev, 4), "first_sample_after_event_s": first_sample,
                 "pass": ev.get("pass"),
                 "failed": "|".join(k for k, v in ev["gates"].items() if not v),
                 "pair_union_s": ev["pair_union_s"], "pair_last_touch_s": ev["pair_last_touch_s"],
                 "event_leg_lifts": json.dumps([(round(a, 3), round(b, 3)) for a, b in lift_ev]),
                 "diag_leg_lifts": json.dumps([(round(a, 3), round(b, 3)) for a, b in lift_dg]),
                 "event_leg_reload_to_exit_level_s": t_reload,
                 "reapp_starts": json.dumps(starts), "reapp_ends": json.dumps(ends),
                 "commands_sha256": rec["commands_sha256"][:16]})


def write(name, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with (out / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


write("u11_repro.csv", repro)
write("u11_runs.csv", runs)
write("u11_periods.csv", periods)
write("u11_lift_intervals.csv", lifts)
(out / "u11_s7_touch.json").write_text(json.dumps(s7, indent=1), encoding="utf-8")
print("records", len(records), "runs", len(runs), "errors", sum(1 for r in records if r.get("error")))
for r in repro:
    print("REPRO", r["setting"], r["case"], r["offset_s"], r["twin"], "same", r["same_sha"],
          "pu", r["rerun_pair_union_s"], r["stored_pair_union_s"], (r["error"] or "")[:80])
for r in runs:
    print("RUN", r["run"], "fs1", r["first_sample_after_event_s"], "pu", r["pair_union_s"],
          "last", r["pair_last_touch_s"], "fail", r["failed"], "reload", r["event_leg_reload_to_exit_level_s"])
    print("    ev", r["event_leg_lifts"], "dg", r["diag_leg_lifts"])
    print("    starts", r["reapp_starts"], "ends", r["reapp_ends"])
print("S7", json.dumps(s7))
