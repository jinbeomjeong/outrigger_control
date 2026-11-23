"""j9_main 606f8713 failure analysis, step A1: pair tables V0 / stored VB / VBJ / LSJ.

Read-only analysis (control-expert, 2026-11-23). Inputs are stored result files only;
no simulation is run and no project file is modified.

Inputs
- V0 and stored VB (old VB plant, ③ rev 4): 06_analysis/03_hydraulic/coupled/v5/main.jsonl
- VBJ, LSJ1..4 (P1..P4 plant + ③ rev 6): j9_runs/606f8713/j9main_a1/j9_main.jsonl
- T8 rows of the same commit (VB, VBH, VBJ, VBJ0): j9_runs/<commit>/t8_a1/j9_t8.jsonl

Outputs (this folder)
- a1_pairs.csv        one line per (row key, setting) for R12 / R15 / S5 / S1 rows
- a1_t8_identity.csv  commands_sha256 of the T8 rows per setting and commit
- a1_summary.json     counts used in the report
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control")
V5 = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5" / "main.jsonl"
RUNS = ROOT / "06_analysis" / "02_control" / "j_p3_cause" / "j9_runs"
J9 = RUNS / "606f8713" / "j9main_a1" / "j9_main.jsonl"
T8 = {c: RUNS / c / "t8_a1" / "j9_t8.jsonl" for c in ("606f8713", "78fd5d2d", "fa997f4c")}
OUT = Path(__file__).resolve().parent
F_MIN_KN = 9.41458911
CASES = ("R12", "R15", "S5", "S1")


def key_of(job: dict) -> str:
    """Pair key: same row and same phase (v5_criteria 1)."""
    tw = job.get("twin")
    tws = f"{tw['level']}|{tw['leg']}|{tw['fs_kN']:g}" if tw else "-"
    return "|".join([str(job.get("case")), str(job.get("decision") or "-"), tws,
                     f"o{job.get('offset_s')}", f"e{job.get('eps')}"])


def summ(d: dict) -> dict:
    j = d["job"]
    eo = d.get("event_output") or {}
    v = d.get("values") or {}
    t = v.get("times") or {}
    mfw = eo.get("min_F_after_W_kN") or {}
    leg_min = min(mfw, key=mfw.get) if mfw else None
    gates = eo.get("gates") or {}
    lfg = ((d.get("hydraulics_record") or {}).get("line_fill_gate") or {})
    hold = lfg.get("hold_s")
    return {
        "key": key_of(j),
        "setting": j.get("setting"),
        "sha10": (d.get("commands_sha256") or "")[:10],
        "final_phase": d.get("final_phase"),
        "t_first_ready_s": t.get("t_first_ready_s"),
        "t_event_s": d.get("t_event_s"),
        "t_ready_back_s": eo.get("t_ready_back_s"),
        "minF_after_W_kN": mfw.get(leg_min) if leg_min else None,
        "minF_leg": leg_min,
        "event_pass": eo.get("pass"),
        "failed_gates": ";".join(k for k, x in gates.items() if x is False),
        "n_rev": (d.get("command_stats") or {}).get("n_rev"),
        "line_fill_hold_s_sum": (round(sum(sum(x) for x in hold), 3) if hold else None),
        "E1": json.dumps({k: x.get("duration_s") for k, x in (v.get("E1") or {}).items()}),
        "tag": d.get("controller_tag"),
    }


def load(path: Path, settings: set[str] | None = None) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            j = d.get("job") or {}
            if settings and j.get("setting") not in settings:
                continue
            if str(j.get("case")) not in CASES:
                continue
            out.append(summ(d))
    return out


def main() -> None:
    rows = load(V5, {"V0", "VB"}) + load(J9)
    by = defaultdict(dict)
    for r in rows:
        by[r["key"]][r["setting"]] = r
    fields = list(rows[0].keys())
    with open(OUT / "a1_pairs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for k in sorted(by):
            for s in ("V0", "VB", "VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4"):
                if s in by[k]:
                    w.writerow(by[k][s])

    # R12 32 keys: V0 / VB / VBJ min force and pass
    r12 = [k for k in by if k.startswith("R12|")]
    stat = {"R12_keys": len(r12)}
    for s in ("V0", "VB", "VBJ", "LSJ1", "LSJ2", "LSJ3", "LSJ4"):
        vals = [by[k][s]["minF_after_W_kN"] for k in r12 if s in by[k]]
        stat[f"R12_{s}_n"] = len(vals)
        stat[f"R12_{s}_below_Fmin"] = sum(1 for x in vals if x is not None and x < F_MIN_KN)
        stat[f"R12_{s}_min_kN"] = min(vals) if vals else None
        stat[f"R12_{s}_max_kN"] = max(vals) if vals else None
        stat[f"R12_{s}_pass"] = sum(1 for k in r12 if s in by[k] and by[k][s]["event_pass"])
    drops = [by[k]["VB"]["minF_after_W_kN"] - by[k]["VBJ"]["minF_after_W_kN"] for k in r12
             if "VB" in by[k] and "VBJ" in by[k]]
    stat["R12_VB_minus_VBJ_kN"] = {"min": min(drops), "max": max(drops),
                                   "mean": sum(drops) / len(drops), "n": len(drops)}
    stat["R12_same_min_leg_VB_VBJ"] = sum(
        1 for k in r12 if by[k]["VB"]["minF_leg"] == by[k]["VBJ"]["minF_leg"])
    stat["R12_VBJ_not_ready"] = sorted(
        (k, by[k]["VBJ"]["final_phase"]) for k in r12 if by[k]["VBJ"]["final_phase"] != "ready")
    for c in ("R15", "S5", "S1"):
        for k in sorted(x for x in by if x.startswith(c + "|")):
            stat[k] = {s: {f: by[k][s][f] for f in ("final_phase", "t_first_ready_s", "t_ready_back_s",
                                                    "minF_after_W_kN", "failed_gates", "n_rev",
                                                    "line_fill_hold_s_sum", "E1")}
                       for s in by[k]}
    # T8 identity: ③ on / off per plant and commit
    t8rows = []
    for c, p in T8.items():
        for r in load(p):
            r["commit"] = c
            t8rows.append(r)
    with open(OUT / "a1_t8_identity.csv", "w", newline="", encoding="utf-8") as f:
        fl = ["commit", "key", "setting", "tag", "sha10", "minF_after_W_kN", "minF_leg", "event_pass",
              "final_phase", "t_first_ready_s", "t_ready_back_s"]
        w = csv.DictWriter(f, fieldnames=fl, extrasaction="ignore")
        w.writeheader()
        for r in sorted(t8rows, key=lambda x: (x["key"], x["commit"], x["setting"])):
            w.writerow(r)
    ident = defaultdict(set)
    for r in t8rows:
        plant = "old" if r["setting"] in ("VB", "VBH") else "new"
        ident[(r["key"], plant)].add(r["sha10"])
    stat["t8_sha_sets_by_plant"] = {f"{k[0]} {k[1]}": sorted(v) for k, v in sorted(ident.items())}
    # stored VB vs current VB (same old plant) on the T8 key
    stat["stored_VB_vs_t8_VB_606f8713"] = {
        r["key"]: [r["sha10"], by.get(r["key"], {}).get("VB", {}).get("sha10")]
        for r in t8rows if r["commit"] == "606f8713" and r["setting"] == "VB"}
    with open(OUT / "a1_summary.json", "w", encoding="utf-8") as f:
        json.dump(stat, f, indent=1, ensure_ascii=False)
    print(json.dumps(stat, indent=1, ensure_ascii=False)[:9000])


if __name__ == "__main__":
    main()
