"""H3' result: the 6 run lines against A (P8-9 condition (3) reading), the check line against H3,
the other 14 lines by the exact offline rule (diag/diag_scope_offline.csv), and the P8-9
eligibility table of H3' (case 1 = R12 bottom-FR-Fs4-RE1bF-ready o0.075 marked separately).

Usage: conda run -n dynamics-dev python -I -B h3p_analyze.py
Output: h3p_selection.json, h3p_metrics.csv, h3p_analyze_out.txt
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


p89 = _load("p89_rerun", PROBE / "p89_rerun.py")
an = _load("p89_analyze", PROBE / "p89_analyze.py")
CASE1 = "bottom-FR-Fs4-RE1bF-ready-o0.075"
CHECK = "bottom-FR-Fs0-RE1bF-ready-o0.0"


def row_of(r, raw):
    eo = r.get("event_output") or {}
    log = an.log_of(raw, r)
    te = r.get("t_event_s")
    t0 = te if te is not None else -1e9
    rel = (lambda t: round(t - te, 3)) if te is not None else (lambda t: round(t, 3))
    j7, capped = an.j7_set(r)
    twist = None
    return {"sha": r["commands_sha256"], "final_phase": r.get("final_phase"),
            "gates": eo.get("gates") or {}, "pass": eo.get("pass"),
            "pair_union_s": eo.get("pair_union_s"), "t_ready_back_s": eo.get("t_ready_back_s"),
            "ready_reached": an.ready_reached(r), "j7": sorted(j7), "capped": capped,
            "min_F_after_event_kN": min((eo.get("min_F_after_event_kN") or {"x": None}).values(),
                                        key=lambda v: 1e9 if v is None else v),
            "starts": [(rel(s["t"]), s["leg"], s["retrigger"]) for s in log["starts"]
                       if s["t"] >= t0 - 1e-9],
            "ends": [(rel(e["t"]), e["leg"], e["outcome"]) for e in log["ends"]
                     if e["t"] >= t0 - 1e-9],
            "h3": [(rel(h["t"]), h["leg"], h.get("retrigger")) for h in log["h3"]],
            "twist": twist}


main = {}
for x in (PROBE / "raw" / "runs.jsonl").read_text("utf-8").splitlines():
    r = json.loads(x)
    main[(an.jkey(r["job"]), r["job"]["setting"].split("-")[1])] = r
hp = {}
for x in (HERE / "raw" / "runs.jsonl").read_text("utf-8").splitlines():
    r = json.loads(x)
    hp[an.jkey(r["job"])] = r
offline = {}
with (PROBE / "diag" / "diag_scope_offline.csv").open(encoding="utf-8") as f:
    for row in csv.DictReader(f):
        offline[row["key"]] = row["variant_first_run_only"]


def off_label(key):
    return f"{key['case']} {key.get('twin')} o{key.get('offset_s')} e{key.get('eps')}"


table, out, csv_rows = {}, [], []
for group, label, key in p89.KEYS:
    k = an.jkey(p89.job_of(key, "A"))
    a = row_of(main[(k, "A")], PROBE / "raw")
    h3 = row_of(main[(k, "H3")], PROBE / "raw")
    if k in hp:
        r = hp[k]
        if "error" in r or r["p89"]["patched_arm"] != "H3p":
            raise SystemExit(f"bad line {label}: {r.get('error')} {r.get('p89')}")
        c = row_of(r, HERE / "raw")
        source = "run"
    else:
        kk = json.loads(k)
        verdict = offline[off_label({**key, **kk})]
        c = dict(h3) if verdict == "= H3" else dict(a)
        source = f"offline {verdict}"
    if label == CHECK:
        source += f"; check vs H3 sha equal {c['sha'] == h3['sha']}"
    new_gates = sorted(g for g, ok in c["gates"].items() if not ok and a["gates"].get(g, True))
    new_j7 = sorted(set(c["j7"]) - set(a["j7"]))
    ready_lost = a["ready_reached"] and not c["ready_reached"]
    rec = {"group": group, "key": label, "source": source, "sha_H3p": c["sha"][:8],
           "sha_A": a["sha"][:8], "sha_H3": h3["sha"][:8],
           "equal_A": c["sha"] == a["sha"], "equal_H3": c["sha"] == h3["sha"],
           "gates_failed_A": sorted(g for g, ok in a["gates"].items() if not ok),
           "gates_failed_H3": sorted(g for g, ok in h3["gates"].items() if not ok),
           "gates_failed_H3p": sorted(g for g, ok in c["gates"].items() if not ok),
           "new_failed_gates": new_gates, "new_j7": new_j7, "ready_lost": ready_lost,
           "pair_union_s": [a["pair_union_s"], h3["pair_union_s"], c["pair_union_s"]],
           "t_ready_back_s": [a["t_ready_back_s"], h3["t_ready_back_s"], c["t_ready_back_s"]],
           "final_phase_H3p": c["final_phase"], "pass_H3p": c["pass"],
           "starts_H3p": c["starts"], "ends_H3p": c["ends"], "h3_ext_H3p": c["h3"],
           "case1": label == CASE1}
    table[label] = rec
    csv_rows.append(rec)

cond1 = {label: not any(g.startswith("U832") for g in table[label]["gates_failed_H3p"])
         for group, label, _ in p89.KEYS if group == "U"}
cond2 = bool(table["bottom-FR-Fs8-FS24-ready-o0.0"]["pass_H3p"]
             if table["bottom-FR-Fs8-FS24-ready-o0.0"]["pass_H3p"] is not None else False)
c3_fail = {label: {k: table[label][k] for k in ("new_failed_gates", "new_j7", "ready_lost")}
           for group, label, _ in p89.KEYS if group in ("phase", "regression")
           and (table[label]["new_failed_gates"] or table[label]["new_j7"]
                or table[label]["ready_lost"])}
c3_fail_wo_case1 = {k: v for k, v in c3_fail.items() if k != CASE1}
n_diff = sum(1 for r in csv_rows if not r["equal_A"])
result = {"rule": "P8-9 (spec v8 draft rev 1, 12) conditions, applied to H3' after the "
                  "diagnosis (re-selection after seeing results, O8-4 extension)",
          "cond1_U832_by_key": cond1, "cond1": all(cond1.values()),
          "cond2_FS24_pass": cond2,
          "cond3_failures": c3_fail, "cond3": not c3_fail,
          "cond3_without_case1": not c3_fail_wo_case1,
          "eligible_as_written": all(cond1.values()) and cond2 and not c3_fail,
          "eligible_if_case1_set_aside": all(cond1.values()) and cond2 and not c3_fail_wo_case1,
          "n_keys_commands_differ_from_A": n_diff}
(HERE / "h3p_selection.json").write_text(json.dumps({"result": result, "lines": table},
                                                    indent=1, default=str), "utf-8")
cols = list(csv_rows[0])
with (HERE / "h3p_metrics.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for r in csv_rows:
        w.writerow([json.dumps(r[c], default=str) if isinstance(r[c], (list, dict)) else r[c]
                    for c in cols])
out.append(json.dumps(result, default=str))
for r in csv_rows:
    out.append(f"{r['group']:10s} {r['key']:34s} {r['source']:40s} H3p {r['sha_H3p']} A {r['sha_A']} "
               f"H3 {r['sha_H3']} =A {r['equal_A']} =H3 {r['equal_H3']} failA {r['gates_failed_A']} "
               f"failH3 {r['gates_failed_H3']} failH3p {r['gates_failed_H3p']} new {r['new_failed_gates']} "
               f"j7new {r['new_j7']} readylost {r['ready_lost']} PU {r['pair_union_s']} tRb {r['t_ready_back_s']}")
    if r["source"].startswith("run"):
        out.append(f"      starts {r['starts_H3p']}\n      ends {r['ends_H3p']}\n      h3 {r['h3_ext_H3p']}")
text = "\n".join(out)
(HERE / "h3p_analyze_out.txt").write_text(text, "utf-8")
print(text.encode("ascii", "replace").decode())
