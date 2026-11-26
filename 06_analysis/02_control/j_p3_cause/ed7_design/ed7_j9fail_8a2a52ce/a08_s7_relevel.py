"""a08: S7 (soil READY row, J3 limit 100 s) relevel after the first PROBE, VBM family vs
VBL / VBJ: probe attitude change, attitude values, relevel duration, LEVEL-start commands,
probe retract extra (i-b). Output a08_s7_relevel.csv."""
import csv
import json
import os

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
J9 = r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
SRC = {
    "ed7_j9main": (J9 + r"\8a2a52ce\j9main_a1\j9_main.jsonl", J9 + r"\8a2a52ce\j9main_a1\j9_main_t4h"),
    "ed7_sens": (J9 + r"\8a2a52ce\sens_a1\sens.jsonl", J9 + r"\8a2a52ce\sens_a1\sens_t4h"),
    "ed6rec_j9main": (J9 + r"\79495405\records_after_stop\B_a1\j9_main.jsonl",
                      J9 + r"\79495405\records_after_stop\B_a1\j9_main_t4h"),
    "ed6rec_sens": (J9 + r"\79495405\records_after_stop\B_a1\sens.jsonl",
                    J9 + r"\79495405\records_after_stop\B_a1\sens_t4h"),
    "ed5_j9main": (J9 + r"\606f8713\j9main_a1\j9_main.jsonl", J9 + r"\606f8713\j9main_a1\j9_main_t4h"),
}
rows = []
for src, (jl, td) in SRC.items():
    with open(jl, encoding="utf-8") as f:
        for ln in f:
            d = json.loads(ln)
            job = d["job"]
            if job.get("case") != "S7":
                continue
            name = d.get("t4h_file") or f"S7_e{job['eps']}_{job['setting']}.npz"
            path = os.path.join(td, name)
            v = d["values"]
            rec = {"source": src, "setting": job["setting"], "eps": job["eps"],
                   "t_first_ready_s": v["times"].get("t_first_ready_s"),
                   "probe_att_change_deg": v.get("probe_attitude_change_deg"),
                   "attitude": json.dumps(v.get("attitude"))}
            if os.path.exists(path):
                z = np.load(path, allow_pickle=False)
                t = z["t_s"]
                ph = z["phase"].astype(str)
                runs = []
                s = 0
                for i in range(1, len(ph) + 1):
                    if i == len(ph) or ph[i] != ph[s]:
                        runs.append((ph[s], s, i - 1))
                        s = i
                lv = [r for r in runs if r[0] == "level"]
                pr = [r for r in runs if r[0] == "probe"]
                if len(lv) >= 2:
                    a, b = lv[1][1], lv[1][2]
                    rec["relevel_s"] = round(float(t[b] - t[a]) + 0.1, 1)
                    cmd = z["command_m_s"]
                    rec["relevel_start_cmd_mm_s"] = json.dumps([round(float(x) * 1e3, 3) for x in cmd[a + 2]])
                    rec["relevel_max_abs_cmd_mm_s"] = round(float(np.max(np.abs(cmd[a:b + 1]))) * 1e3, 3)
                if pr:
                    rec["probe1_s"] = round(float(t[pr[0][2]] - t[pr[0][1]]) + 0.1, 1)
                    s_m = z["motor_stroke_m"]
                    a, b = pr[0][1], pr[0][2]
                    rec["probe1_net_stroke_mm"] = json.dumps(
                        [round(float(s_m[b, i] - s_m[a - 1, i]) * 1e3, 3) for i in range(4)])
                meta = json.loads(str(z["meta_json"]))
                rounds = (meta.get("probe_d6_record") or {}).get("rounds") or []
                ex = [r.get("retract_extra_m") for r in rounds[:4]]
                rec["probe1_extra_retract_mm"] = json.dumps(
                    [None if e is None else round(e * 1e3, 2) for e in ex]) if rounds else None
            rows.append(rec)
fields = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0].keys()).index(k) if k in rows[0] else 99)
with open(os.path.join(OUT, "a08_s7_relevel.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(r["source"], r["setting"], r["eps"], r["t_first_ready_s"], "relevel", r.get("relevel_s"),
          "probe1", r.get("probe1_s"), "net", r.get("probe1_net_stroke_mm"),
          "extra", r.get("probe1_extra_retract_mm"), "attchg", r["probe_att_change_deg"],
          "cmd0", r.get("relevel_start_cmd_mm_s"))
