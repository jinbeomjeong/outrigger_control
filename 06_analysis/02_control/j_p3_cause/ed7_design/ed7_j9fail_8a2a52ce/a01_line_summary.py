"""a01: per-line summary across plants (V0, ed5 VBJ, ed6 VBL record, ed7 VBM) for the
ed7 j9main / sens failure analysis (path 1 cause analysis, after the judgement).

Inputs (read only): stored jsonl run outputs. Output: a01_line_summary.csv / .json in this
folder. Fields: setting, family (plant generation), job key, final phase, times, stiffness
warning ratios, warning names, probe round count, A_ib shot count.
"""
import csv
import json
import os
import re

OUT = os.path.dirname(os.path.abspath(__file__))
J9 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
SOURCES = {
    "V0": r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\main.jsonl",
    "ed5_j9main": J9 + r"\606f8713\j9main_a1\j9_main.jsonl",
    "ed6rec_j9main": J9 + r"\79495405\records_after_stop\B_a1\j9_main.jsonl",
    "ed6rec_sens": J9 + r"\79495405\records_after_stop\B_a1\sens.jsonl",
    "ed7_j9main": J9 + r"\8a2a52ce\j9main_a1\j9_main.jsonl",
    "ed7_sens": J9 + r"\8a2a52ce\sens_a1\sens.jsonl",
}
STIFF = "WARN_PROBE_STIFFNESS_OUT_OF_RANGE"


def job_key(job):
    tw = job.get("twin") or {}
    return "|".join(str(x) for x in (job.get("case"), job.get("eps", 0.0),
                                     job.get("offset_s", 0.0), tw.get("level", ""),
                                     tw.get("leg", ""), tw.get("fs_kN", "")))


def summarize(src, d):
    job = d.get("job", {})
    times = (d.get("values") or {}).get("times") or {}
    eo = d.get("event_output") or {}
    events = d.get("events") or []
    names = sorted({str(n).split(":")[0] for _, n in events})
    stiff = [float(n.split(":")[1]) for _, n in events if str(n).startswith(STIFF)]
    stiff_t = [round(float(t), 2) for t, n in events if str(n).startswith(STIFF)]
    en = d.get("event_names") or {}
    blind = ((d.get("lsb_record") or {}).get("blind") or {})
    d6 = d.get("probe_d6_record") or {}
    return {
        "source": src, "setting": job.get("setting"), "key": job_key(job),
        "case": job.get("case"), "final_phase": d.get("final_phase"),
        "t_first_done_s": times.get("t_first_done_s"),
        "t_first_ready_s": times.get("t_first_ready_s"),
        "t_event_s": d.get("t_event_s"), "t_ready_back_s": eo.get("t_ready_back_s"),
        "warn_names": ";".join(n for n in names if n.startswith(("WARN", "FAULT"))),
        "stiff_n": len(stiff), "stiff_ratios": ";".join(f"{v:.3f}" for v in stiff),
        "stiff_t_s": ";".join(str(v) for v in stiff_t),
        "probe_rounds_d6": len(d6.get("rounds") or []),
        "ib_shots": len(blind.get("shots") or []),
        "relevel_predicted": en.get("relevel_predicted", 0),
        "soil_mode_start": en.get("soil_mode_start", 0),
        "loc_revoked": en.get("INFO_LOC_REVOKED", 0),
        "level_done_n": len(blind.get("level_done") or []),
        "commands_sha256": d.get("commands_sha256"),
    }


rows = []
for src, path in SOURCES.items():
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            rows.append(summarize(src, json.loads(ln)))
fields = list(rows[0].keys())
with open(os.path.join(OUT, "a01_line_summary.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
counts = {}
for r in rows:
    c = counts.setdefault(r["source"] + ":" + str(r["setting"]), {"lines": 0, "stiff_lines": 0})
    c["lines"] += 1
    c["stiff_lines"] += r["stiff_n"] > 0
with open(os.path.join(OUT, "a01_line_summary.json"), "w", encoding="utf-8") as f:
    json.dump({"sources": SOURCES, "counts": counts}, f, indent=1)
print(json.dumps(counts, indent=1))
