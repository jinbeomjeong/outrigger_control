"""Judge the M1b R12 and G4 runs (m1_criteria.md, M1b section) and test the two estimates on the 1 ms R12 record.

Usage (dynamics-dev): python -I aggregate_m1b.py
Output: m1b/m1b_judgement.json, text on stdout. F_min = 9.415 kN. Effect = median(on) - median(off), scatter = ptp(off).
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
PR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review"
OUT = PR / "m1b"
F_MIN = 9.415
LEGS = ("FL", "FR", "RL", "RR")


def load(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def main_values(rec):
    e = rec["event_output"]
    if not e:
        return {"no_event": True, "times": rec["values"]["times"], "names": rec["event_names"], "phase": rec["final_phase"]}
    fev = e["min_F_after_event_kN"]
    leg = min(fev, key=fev.get)
    return {"pass": e["pass"], "gates": [k for k, v in e["gates"].items() if not v], "F": fev[leg], "leg": leg, "Fall": fev,
            "FW": min(e["min_F_after_W_kN"].values()), "back": e["t_ready_back_s"], "rev": rec["command_stats"]["n_rev"],
            "ready": rec["values"]["times"]["t_first_ready_s"], "final": e["final_phase"], "att": max(abs(v) for v in e["att_end_deg"]),
            "lifts": list(e["lifts"]), "start": e["reapproach_starts"][:1], "bad": sorted(k for k in rec["event_names"] if k.startswith(("FAULT", "WARN"))), "aborts": rec["values"]["events"]["probe_aborts"]}


def test_estimates(table) -> dict:
    """The two estimates of the criteria on the 1 ms record of R12."""
    out = {}
    for offset in (0.0, 0.025, 0.05, 0.075):
        off = np.load(OUT / "series_r12" / f"R12_OFF_{offset}.npz")
        t = off["t"]
        retract = (off["u"][:, 1] < -1e-6) | (off["u"][:, 2] < -1e-6)
        t_ret = float(t[(t > 0) & retract][0]) if ((t > 0) & retract).any() else None
        first_cmd = float(t[(t > 0) & (np.abs(off["u"]).max(axis=1) > 1e-6)][0])
        row = {"t_first_cmd": first_cmd, "t_FR_RL_first_retract_off": t_ret, "variants": {}}
        for path in sorted((OUT / "series_r12").glob(f"R12_*_{offset}.npz")):
            name = path.stem[4:].rsplit("_", 1)[0]
            d = np.load(path)
            n = min(len(t), len(d["t"]))
            after = (d["t"] >= 0.0) & (d["t"] <= 4.0)
            rr = d["F"][:, 3] / 1e3
            k = int(np.argmin(np.where(after, rr, np.inf)))
            k_off = int(np.argmin(np.where((t >= 0) & (t <= 4), off["F"][:, 3], np.inf)))
            diff = (d["F"][:n, 3] - off["F"][:n, 3]) / 1e3
            apart = np.flatnonzero((t[:n] > 0) & (np.abs(diff) > 0.5))
            t_apart = float(t[apart[0]]) if apart.size else None
            # the commands the fill swallowed before the off run's minimum
            pre = (t[:n] >= 0) & (t[:n] <= float(t[k_off]))
            lost = np.trapezoid(np.abs(d["u"][:n][pre] - d["v"][:n][pre]), t[:n][pre], axis=0) * 1e3
            lost_ret = [float(np.trapezoid(np.abs(np.where(d["u"][:n][pre, i] < 0, d["u"][:n][pre, i] - d["v"][:n][pre, i], 0.0)), t[:n][pre]) * 1e3) for i in range(4)]
            row["variants"][name] = {"RR_min": round(float(rr[k]), 2), "t_min": round(float(d["t"][k]), 3), "t_apart_0p5kN": t_apart,
                                     "dRR_at_off_min": round(float(diff[k_off]), 2), "lost_to_off_min_mm": np.round(lost, 3).tolist(),
                                     "lost_retract_to_off_min_mm": np.round(lost_ret, 3).tolist(),
                                     "reapp_cmd_t": float(d["t"][(d["t"] > 0) & (np.abs(d["u"][:, 3]) > 2e-3)][0]) if ((d["t"] > 0) & (np.abs(d["u"][:, 3]) > 2e-3)).any() else None}
        out[str(offset)] = row
    return out


def main() -> None:
    r12 = load(OUT / "r12.jsonl") + [r for r in load(OUT / "hash.jsonl") if not r["job"].get("twin")]
    table = defaultdict(dict)
    errors = [r["job"] for r in r12 if "error" in r]
    for r in r12:
        if "error" not in r:
            table[r["job"]["variant"]][r["job"]["offset_s"]] = main_values(r)
    print("r12 runs", len(r12), "errors", errors)
    off = table["OFF"]
    off_f = [v["F"] for v in off.values()]
    summary = {}
    for name, rows in table.items():
        phases = sorted(rows)
        if any("no_event" in rows[p] for p in phases):
            summary[name] = {"no_event_phases": [p for p in phases if "no_event" in rows[p]], "detail": rows}
            print(name, "NO EVENT", summary[name]["no_event_phases"], {p: (rows[p].get("names"), rows[p].get("times")) for p in phases if "no_event" in rows[p]})
            continue
        f = [rows[p]["F"] for p in phases]
        d = [rows[p]["F"] - off[p]["F"] for p in phases]
        effect = statistics.median(f) - statistics.median(off_f)
        s = max(off_f) - min(off_f)
        summary[name] = {"F": [round(x, 2) for x in f], "legs": sorted({rows[p]["leg"] for p in phases}), "pass": sum(rows[p]["pass"] for p in phases),
                         "effect": round(effect, 2), "scatter": round(s, 2), "separated": bool(abs(effect) > s and (all(x > 0 for x in d) or all(x < 0 for x in d))),
                         "gates": sorted({g for p in phases for g in rows[p]["gates"]}), "rev": [rows[p]["rev"] for p in phases], "back": [rows[p]["back"] for p in phases],
                         "ready": [rows[p]["ready"] for p in phases], "bad": sorted({b for p in phases for b in rows[p]["bad"]}), "final": sorted({rows[p]["final"] for p in phases}),
                         "aborts": [rows[p]["aborts"] for p in phases], "lifts": sorted({x for p in phases for x in rows[p]["lifts"]}), "start": [rows[p]["start"] for p in phases],
                         "FW": [round(rows[p]["FW"], 2) for p in phases], "att": max(rows[p]["att"] for p in phases),
                         "rr_all": [round(rows[p]["Fall"]["RR"], 2) for p in phases], "other_all": {leg: round(min(rows[p]["Fall"][leg] for p in phases), 2) for leg in ("FL", "FR", "RL")}}
        print(name, json.dumps(summary[name]))
    print()
    # hash
    stored = {r["job"]["offset_s"]: r for r in load(PR / "m1" / "main.jsonl") if r["job"]["case"] == "R12" and r["job"]["variant"] == "OFF"}
    hash_rows = load(OUT / "hash.jsonl")
    print("hash", [(r["job"]["offset_s"], r["job"].get("twin"), r["commands_sha256"][:8], (stored.get(r["job"]["offset_s"]) or {}).get("commands_sha256", "")[:8]) for r in hash_rows if not r["job"].get("twin")])
    old_g4 = load(PR / "m1" / "g4.jsonl")
    old_off = {json.dumps([r["job"]["twin"], r["job"]["offset_s"]]): r for r in old_g4 if r["job"]["variant"] == "OFF"}
    print("hash g4", [(r["commands_sha256"][:8], old_off[json.dumps([r["job"]["twin"], r["job"]["offset_s"]])]["commands_sha256"][:8]) for r in hash_rows if r["job"].get("twin")])
    # g4
    g4 = load(OUT / "g4.jsonl")
    g4_errors = [r["job"] for r in g4 if "error" in r]
    print("g4 runs", len(g4), "errors", g4_errors)
    per = defaultdict(list)
    for r in old_g4:
        per[r["job"]["variant"] + "(M1)" if r["job"]["variant"] != "OFF" else "OFF"].append(r)
    for r in g4:
        per[r["job"]["variant"]].append(r)
    g4_summary = {}
    off_rows = {json.dumps([r["job"]["twin"], r["job"]["offset_s"]]): r for r in per["OFF"]}
    for name, rows in per.items():
        c = Counter()
        fs = defaultdict(list)
        no_event = 0
        rev_flag = 0
        for r in rows:
            e = r["event_output"]
            if not e:
                no_event += 1
                continue
            for g, ok in e["gates"].items():
                if not ok:
                    c[g] += 1
            fs[r["job"]["twin"]["fs_kN"]].append(min(e["min_F_after_event_kN"].values()))
            o = off_rows[json.dumps([r["job"]["twin"], r["job"]["offset_s"]])]
            if r["command_stats"]["n_rev"] >= 2 * o["command_stats"]["n_rev"] and r["command_stats"]["n_rev"] >= o["command_stats"]["n_rev"] + 6:
                rev_flag += 1
        allf = [x for v in fs.values() for x in v]
        g4_summary[name] = {"n": len(rows), "pass": sum(bool(r["event_output"] and r["event_output"]["pass"]) for r in rows), "gates": dict(c), "no_event": no_event, "F_range": [round(min(allf), 2), round(max(allf), 2)], "by_Fs": {str(k): [round(min(v), 2), round(max(v), 2)] for k, v in fs.items()}, "rev_flag": rev_flag, "rev_max": max(r["command_stats"]["n_rev"] for r in rows), "back_max": max((r["event_output"]["t_ready_back_s"] or 0) for r in rows if r["event_output"]), "fault": sum(any(k.startswith("FAULT") for k in r["event_names"]) for r in rows)}
        print(name, json.dumps(g4_summary[name]))
    estimates = test_estimates(table)
    print()
    for off_key, row in estimates.items():
        print(off_key, "first cmd", row["t_first_cmd"], "first FR/RL retract", row["t_FR_RL_first_retract_off"])
        for name in ("OFF", "V1", "B1", "VR_c2_v1", "VN_c2_v1", "BL_v1", "VR_rodonly", "VR_c2_v05", "VN_c2_v05", "BL_v05"):
            print("  ", name, row["variants"].get(name))
    (OUT / "m1b_judgement.json").write_text(json.dumps({"r12": summary, "g4": g4_summary, "estimates": estimates}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
