"""Reference tables of the M1c R12 and G4 runs (the units missed their criteria: not a verdict).

Usage (dynamics-dev): python -I aggregate_m1c.py
Output: m1c/m1c_reference.json, text on stdout. F_min 9.415 kN; effect = median(on) - median(off), scatter = ptp(off).
Zone rule, written before reading the runs' start states: an extend start is in a missed zone when p_r and p_h are both within
25 % of one of (p_r, p_h) = (20, 60), (30, 80), (8, 30) bar g, the states where the boundary unit missed.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
PR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review"
OUT = PR / "m1c"
ZONES = ((20.0, 60.0), (30.0, 80.0), (8.0, 30.0))
LEGS = ("FL", "FR", "RL", "RR")
REGARD_WINDOW_S = (-0.2, 3.0)


def load(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def zone_of(p_r, p_h):
    for zr, zh in ZONES:
        if abs(p_r - zr) <= 0.25 * zr and abs(p_h - zh) <= 0.25 * zh:
            return f"pr{zr:g}_ph{zh:g}"
    return None


def starts_of(rec):
    """Extend starts of a run: all, and in the sink window; each with its zone."""
    m1 = rec.get("m1")
    if not m1:
        return [], []
    ev = rec.get("t_event_s")
    all_s = [(s[0], LEGS[s[1]], s[2], s[3], s[4], zone_of(s[3], s[2])) for s in m1["ext_starts"]]
    win = [] if ev is None else [s for s in all_s if ev + REGARD_WINDOW_S[0] <= s[0] <= ev + REGARD_WINDOW_S[1]]
    return all_s, win


def row_values(rec):
    e = rec["event_output"]
    if not e:
        return {"no_event": True, "names": rec["event_names"], "times": rec["values"]["times"], "final": rec["final_phase"]}
    fev = e["min_F_after_event_kN"]
    leg = min(fev, key=fev.get)
    all_s, win = starts_of(rec)
    return {"F": fev[leg], "leg": leg, "pass": e["pass"], "gates": [k for k, v in e["gates"].items() if not v], "back": e["t_ready_back_s"], "final": e["final_phase"],
            "rev": rec["command_stats"]["n_rev"], "bad": sorted(k for k in rec["event_names"] if k.startswith(("FAULT", "WARN"))), "n_all": len(all_s), "z_all": sum(s[5] is not None for s in all_s), "n_win": len(win), "z_win": sum(s[5] is not None for s in win), "win": win, "att": max(abs(v) for v in e["att_end_deg"])}


def main() -> None:
    r12 = load(OUT / "r12.jsonl") + [r for r in load(OUT / "hash.jsonl") if not r["job"].get("twin")]
    m1b = {}
    for r in load(PR / "m1b" / "r12.jsonl") + [x for x in load(PR / "m1b" / "hash.jsonl") if not x["job"].get("twin")]:
        if "error" not in r and r["event_output"]:
            m1b.setdefault(r["job"]["variant"], {})[r["job"]["offset_s"]] = min(r["event_output"]["min_F_after_event_kN"].values())
    print("r12 runs", len(r12), "errors", [r["job"] for r in r12 if "error" in r], "walls", round(float(np.mean([r["wall_s"] for r in r12 if "wall_s" in r])), 1))
    table = defaultdict(dict)
    for r in r12:
        table[r["job"]["variant"]][r["job"]["offset_s"]] = row_values(r)
    off = [table["OFF"][p]["F"] for p in sorted(table["OFF"])]
    report = {"r12": {}, "g4": {}}
    for name, rows in table.items():
        phases = sorted(rows)
        if any("no_event" in rows[p] for p in phases):
            print(name, "NO EVENT phases", [p for p in phases if "no_event" in rows[p]], {p: rows[p].get("times") for p in phases if "no_event" in rows[p]})
        vals = [rows[p] for p in phases if "no_event" not in rows[p]]
        if not vals:
            report["r12"][name] = {"no_event": True}
            continue
        f = [v["F"] for v in vals]
        phases_ok = [p for p in phases if "no_event" not in rows[p]]
        d = [rows[p]["F"] - table["OFF"][p]["F"] for p in phases_ok]
        effect = statistics.median(f) - statistics.median(off)
        s = max(off) - min(off)
        old = m1b.get(name)
        diff_b = None if not old else [round(rows[p]["F"] - old[p], 2) for p in phases_ok if p in old]
        entry = {"F": [round(x, 2) for x in f], "legs": sorted({v["leg"] for v in vals}), "pass": sum(v["pass"] for v in vals), "effect": round(effect, 2), "scatter": round(s, 2), "separated": bool(abs(effect) > s and (all(x > 0 for x in d) or all(x < 0 for x in d))),
                 "above_Fmin": sum(x >= 9.415 for x in f), "gates": sorted({g for v in vals for g in v["gates"]}), "back": [v["back"] for v in vals], "final": [v["final"] for v in vals], "stuck": sum(v["back"] is None for v in vals), "rev": [v["rev"] for v in vals], "bad": sorted({b for v in vals for b in v["bad"]}),
                 "minus_m1b": diff_b, "m1b_F": None if not old else [round(old[p], 2) for p in phases_ok if p in old], "zone_window": (sum(v["z_win"] for v in vals), sum(v["n_win"] for v in vals)), "zone_all": (sum(v["z_all"] for v in vals), sum(v["n_all"] for v in vals)), "att": round(max(v["att"] for v in vals), 3)}
        report["r12"][name] = entry
        print(name, json.dumps(entry))
    # hash
    stored = {r["job"]["offset_s"]: r for r in load(PR / "m1" / "main.jsonl") if r["job"]["case"] == "R12" and r["job"]["variant"] == "OFF"}
    print("hash", [(r["job"]["offset_s"], r["commands_sha256"][:8] == stored[r["job"]["offset_s"]]["commands_sha256"][:8]) for r in load(OUT / "hash.jsonl") if not r["job"].get("twin")])
    # start states of R12 in the sink window, phase 0
    for name in ("VN_c2_v1", "BL_v1", "VR_c2_v1"):
        v = table[name][0.0]
        print("starts", name, [(round(s[0] - r12_event(r12, name, 0.0), 2), s[1], s[2], s[3], s[4], s[5]) for s in v.get("win", [])])
    # G4
    g4 = load(OUT / "g4.jsonl")
    print("g4 runs", len(g4), "errors", [r["job"] for r in g4 if "error" in r])
    old_rows = load(PR / "m1b" / "g4.jsonl")
    old_off = {json.dumps([r["job"]["twin"], r["job"]["offset_s"]]): r for r in load(PR / "m1" / "g4.jsonl") if r["job"]["variant"] == "OFF"}
    groups = defaultdict(list)
    for r in g4:
        groups[r["job"]["variant"]].append(r)
    old_groups = defaultdict(list)
    for r in old_rows:
        old_groups[r["job"]["variant"]].append(r)
    for name, rs in groups.items():
        c = Counter()
        fs = defaultdict(list)
        zone_marks = []
        n_win = z_win = no_event = rev_flag = 0
        for r in rs:
            e = r["event_output"]
            if not e:
                no_event += 1
                continue
            for g, ok in e["gates"].items():
                if not ok:
                    c[g] += 1
            fs[r["job"]["twin"]["fs_kN"]].append(min(e["min_F_after_event_kN"].values()))
            _all, win = starts_of(r)
            n_win += len(win)
            z = [s for s in win if s[5]]
            z_win += len(z)
            if z:
                zone_marks.append((r["job"]["twin"]["leg"], r["job"]["twin"]["level"], r["job"]["twin"]["fs_kN"], r["job"]["offset_s"], [(s[1], s[2], s[3], s[5]) for s in z], round(min(e["min_F_after_event_kN"].values()), 2), e["pass"]))
            o = old_off[json.dumps([r["job"]["twin"], r["job"]["offset_s"]])]
            if r["command_stats"]["n_rev"] >= 2 * o["command_stats"]["n_rev"] and r["command_stats"]["n_rev"] >= o["command_stats"]["n_rev"] + 6:
                rev_flag += 1
        allf = [x for v in fs.values() for x in v]
        old = old_groups.get(name, [])
        entry = {"n": len(rs), "pass": sum(bool(r["event_output"] and r["event_output"]["pass"]) for r in rs), "gates": dict(c), "no_event": no_event, "F": [round(min(allf), 2), round(max(allf), 2)], "by_Fs": {str(k): [round(min(v), 2), round(max(v), 2)] for k, v in fs.items()},
                 "stuck": sum(bool(r["event_output"]) and r["event_output"]["t_ready_back_s"] is None for r in rs), "rev_flag": rev_flag, "fault": sum(any(k.startswith("FAULT") for k in r["event_names"]) for r in rs), "zone_window": (z_win, n_win), "m1b_pass": sum(bool(r["event_output"] and r["event_output"]["pass"]) for r in old), "m1b_stuck": sum(bool(r["event_output"]) and r["event_output"]["t_ready_back_s"] is None for r in old), "zone_rows": zone_marks}
        report["g4"][name] = entry
        print(name, json.dumps({k: v for k, v in entry.items() if k != "zone_rows"}))
        print("   zone rows", zone_marks[:12])
    # RR records
    marks = {}
    for path in sorted((OUT / "series_r12").glob("R12_*.npz")):
        d = np.load(path, allow_pickle=True)
        t, F, pr = d["t"], d["F"][:, 3] / 1e3, d["p_r"][:, 3] / 1e5
        at = lambda x: int(np.searchsorted(t, x))  # noqa: E731
        k = int(np.argmin(np.where((t >= 0) & (t <= 4), F, np.inf)))
        marks[path.stem[4:]] = {"F_pre": round(float(F[at(0.0)]), 2), "F": {str(v): round(float(F[at(v)]), 2) for v in (0.85, 1.0, 1.2, 1.4)}, "t_min": round(float(t[k]), 3), "F_min": round(float(F[k]), 2), "p_r": {str(v): round(float(pr[at(v)]), 1) for v in (0.5, 0.85, 1.0, 1.2, 1.4)}}
    report["rr_marks"] = marks
    for name in ("OFF", "OFF_E2", "VN_c2_v1", "VN_c2_v1_E2", "VN_c2_v1_E4", "BL_v1", "BL_v1_E2", "BL_v1_E4", "VR_c2_v1", "VR_c2_v1_E2", "VR_c2_v1_E4"):
        print("marks", name, json.dumps(marks.get(f"{name}_0.025")))
    (OUT / "m1c_reference.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


def r12_event(rows, name, offset):
    for r in rows:
        if r["job"]["variant"] == name and r["job"]["offset_s"] == offset:
            return r["t_event_s"] or 0.0
    return 0.0


if __name__ == "__main__":
    main()
