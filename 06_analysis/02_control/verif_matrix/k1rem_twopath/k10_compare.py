"""K-10 exact comparison of path 1 (judge_REM.json) and path 2 (path2_REM.json).

No tolerance. Floats are compared with ==. Label vocabulary mapping is declared
up front (GATEON outcome names) and reported.
"""
import hashlib
import json
import sys
from pathlib import Path

P1 = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\las\k1\judge_REM.json")
P2 = Path(r"C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control"
          r"\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\k1rem_path2\path2_REM.json")
EXPECT_P2_SHA = "5ecde300426afbb7b30a33931ae315a305a0fb7962024ea79a1cf9e83de1785f"
OUT = Path(__file__).with_name("k10_result.json")

# Declared before comparison: equivalent outcome labels for an L1-applied gate-on row.
GATEON_LABEL_MAP = {"L1_APPLIED": "APPLIED_AT_L1"}

KEYS = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "F1", "F2"]
JUDGE = KEYS[:8]
DEC_FIELDS = ["t_loc_s", "n_loc", "t_P_s", "t_S_s", "n_P", "n_S", "dP", "would_block", "applied",
              "post_revoke", "last_revoke_n", "restart_n", "struct_zero"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    s2 = sha(P2)
    p1 = json.loads(P1.read_text(encoding="utf-8"))
    p2 = json.loads(P2.read_text(encoding="utf-8"))
    res = []

    def cmp(group, item, a, b, info=False):
        ok = (a == b) and (type(a) is type(b) or {type(a), type(b)} <= {int, float})
        res.append(dict(group=group, item=item, p1=a, p2=b, equal=ok, info_only=info))

    cmp("meta", "path2_output_sha_fixed", s2, EXPECT_P2_SHA)
    cmp("meta", "rules_sha", p1["rules_sha256"], p2["rules_sha256"])
    # files read in common: compare sha for overlapping paths
    f1 = {k.replace("/", "\\").lower(): v for k, v in p1["files_read_sha256"].items()}
    f2 = {k.replace("/", "\\").lower(): v for k, v in p2["files_read_sha256"].items()}
    common = sorted(set(f1) & set(f2))
    for k in common:
        cmp("files_read", k.split("\\")[-2] + "/" + k.split("\\")[-1], f1[k], f2[k])

    for k in KEYS:
        r1, r2 = p1["rows"][k], p2["rows"][k]
        info = k in ("F1", "F2")
        cmp("state", k, r1["state"], r2["status"], info)
        L1a = r1["L1"]
        L1b = r2["L1"]
        for f in ["n_loc", "n_P", "n_S", "dP", "t_P_s", "t_S_s"]:
            cmp("L1", f"{k}.{f}", L1a.get(f) if L1a else None, L1b.get(f) if L1b else None, info)
        cmp("L1", f"{k}.post_revoke", L1a["post_revoke"], r2["L1_post_revoke"], info)
        cmp("L1", f"{k}.n_loc_minus_n_P", L1a["n_loc_minus_n_P"], r2["L1_loc_minus_P"], info)
        cmp("decisions", f"{k}.count", len(r1["decisions"]), len(r2["decisions"]), info)
        for i, (d1, d2) in enumerate(zip(r1["decisions"], r2["decisions"])):
            for f in DEC_FIELDS:
                cmp("decisions", f"{k}.d{i}.{f}", d1[f], d2[f], info)
            cmp("decisions", f"{k}.d{i}.r4", d1["r4_due_without_gate"], d2["r4"], info)
            cmp("decisions", f"{k}.d{i}.rec_match", d1["recorded_periods_match"], d2["rec_match"], info)
        cmp("record", f"{k}.revokes", r1["revoke_periods"], r2["revokes_n"], info)
        cmp("record", f"{k}.mode_starts",
            [(m["n"], m["t_s"], m["source"]) for m in r1["mode_starts"]],
            [(m["n"], m["t_s"], m["source"]) for m in r2["mode_starts"]], info)
        cmp("record", f"{k}.loc_periods", r1["loc_periods"], r2["loc_event_periods"], info)
        cmp("record", f"{k}.e3c10", r1["e3c10_locs"], r2["n_e3c10_loc"], info)
        e1 = r1["end"]
        cmp("record", f"{k}.s_motor_max_m", e1["s_motor_max_m"], r2["s_motor_max_m"], info)
        cmp("record", f"{k}.crawler_gap_end", e1["crawler_gap_grid_end_m"], r2["crawler_gap_end_grid_m"], info)
        cmp("record", f"{k}.first_done", e1["first_done_s"], r2["first_done_t_s"], info)
        cmp("record", f"{k}.first_ready", e1["first_ready_s"], r2["first_ready_t_s"], info)
        cmp("record", f"{k}.last_phase", e1["last_phase"], r2["final_phase"], info)
        cmp("record", f"{k}.fault_warn", sorted(e1["fault_warn_events"]),
            sorted(r2["faults"] + r2["warn_names"]), info)
        cmp("record", f"{k}.missing_reasons", r1["missing_reasons"], r2["missing_reasons"], info)
        rr1 = None if r1["rerun_of"] in (None, "<missing>") else r1["rerun_of"]
        cmp("record", f"{k}.rerun_of(normalized)", rr1, r2["rerun_of"], info)

    # pairs
    k7 = {p: v["ok"] for p, v in p1["pairs"]["K-7"]["pairs"].items()}
    c3 = {p: v["ok"] for p, v in p1["pairs"]["condition_3"]["pairs"].items()}
    for p in ("R7", "R8"):
        cmp("pairs", f"{p}.K-7", k7[p], p2["pairs"][p]["k7"])
        cmp("pairs", f"{p}.cond3", c3[p], p2["pairs"][p]["cond3"])
        g1 = p1["flags"]["GATEON_PATH"][p]["outcome"]
        cmp("pairs", f"{p}.gateon_path(mapped)", GATEON_LABEL_MAP.get(g1, g1), p2["pairs"][p]["gateon_path"])
        cmp("pairs", f"{p}.gateon_r4_sequence",
            [(d["n_loc"], d["dP"], d["applied"], d["struct_zero"]) for d in p1["flags"]["GATEON_PATH"][p]["r4_decisions"]],
            [(d["n_loc"], d["dP"], d["applied"], d["struct_zero"]) for d in p2["pairs"][p]["gateon_r4_sequence"]])
    pc = {tuple(x["rows"]): x["same"] for x in p1["flags"]["pair_commands"]}
    cmp("pairs", "R1/R7.cmd_same", pc[("R1", "R7")], p2["pairs"]["R7"]["cmd"]["sha_equal"])
    cmp("pairs", "R4/R8.cmd_same", pc[("R4", "R8")], p2["pairs"]["R8"]["cmd"]["sha_equal"])

    # flags
    f1f, fc2 = p1["flags"], p2["flag_counts"]
    g_count1 = sum(1 for v in f1f["GATEON_PATH"].values() if v["outcome"] in ("R4_APPLIED_LATE", "R4_NEVER"))
    cmp("flags", "THIN_MARGIN", len(f1f["THIN_MARGIN"]), fc2["THIN_MARGIN"])
    cmp("flags", "LATE_R4", len(f1f["LATE_R4"]), fc2["LATE_R4"])
    cmp("flags", "SHADOW_RELOC", f1f["SHADOW_RELOC"]["count"], fc2["SHADOW_RELOC"])
    cmp("flags", "SHADOW_RELOC_struct_zero", f1f["SHADOW_RELOC"]["struct_zero"], fc2["SHADOW_RELOC_struct_zero"])
    cmp("flags", "SHADOW_RELOC_items",
        [(x["row"], x["n_loc"], x["dP"], x["struct_zero"]) for x in f1f["SHADOW_RELOC"]["items"]],
        [(x["row"], x["n_loc"], x["dP"], x["struct_zero"]) for x in p2["flags"]["SHADOW_RELOC"]["items"]])
    cmp("flags", "PAIR_DIVERGE", len(f1f["PAIR_DIVERGE"]), fc2["PAIR_DIVERGE"])
    cmp("flags", "GATEON_PATH(late/never count)", g_count1, fc2["GATEON_PATH"])
    cmp("flags", "OLD_CTRL_SHIFT_count", len(f1f["OLD_CTRL_SHIFT"]), fc2["OLD_CTRL_SHIFT"])
    for k, v in f1f["OLD_CTRL_SHIFT"].items():
        w = p2["flags"]["OLD_CTRL_SHIFT"][k]
        cmp("flags", f"OLD_CTRL_SHIFT.{k}", (v["n_loc_minus_old_n_R"], v["n_S_minus_old_n_S"]),
            (w["d_n_loc"], w["d_n_S"]))
    for k, v in f1f["harness_comparison"].items():
        cmp("flags", f"harness.{k}", (tuple(v["harness_dP"]), v["chrono_dP"]),
            (tuple(p2["harness_compare"][k]["harness_range"]), p2["harness_compare"][k]["chrono_dP"]), True)

    # conditions and grade
    cmp("conditions", "1_MUST", p1["conditions"]["①"], p2["conditions"]["1_MUST"])
    cmp("conditions", "3_PAIR", p1["conditions"]["③"],
        all(v["cond3"] for v in p2["conditions"]["3_PAIR"].values()))
    k_ok1 = all(c["ok"] for c in p1["k_checks"])
    cmp("conditions", "K0-K9 all ok / no stop", k_ok1, len(p2["stop_keys"]) == 0)
    cmp("grade", "grade_provisional", p1["grade_provisional"], p2["grade_provisional"])

    # F diag (info only, user decision 3)
    for k in ("F1", "F2"):
        d1, d2 = p1["diag"][k], p2["diag"][k]
        cmp("F_diag", f"{k}.path", d1["path"], d2["path_class"], True)
        cmp("F_diag", f"{k}.valid", d1["valid"], d2["valid"], True)
        cmp("F_diag", f"{k}.FORCED_AT_L1", d1["FORCED_AT_L1"], d2["FORCED_AT_L1"], True)
        cmp("F_diag", f"{k}.FORCED_PAIR_L1", d1["FORCED_PAIR_L1"], d2["FORCED_PAIR_L1"], True)
        cmp("F_diag", f"{k}.revokes_after_L1", d1["revokes_after_L1"], d2["revokes_after_L1"], True)
        cmp("F_diag", f"{k}.reeval",
            [(x["n_loc"], x["dP"], x["applied"], x["struct_zero"]) for x in d1["reevaluations"]],
            [(x["n_loc"], x["dP"], x["applied"], x["struct_zero"]) for x in d2["reeval"]], True)
        cmp("F_diag", f"{k}.late_applied", d1["late_applied"], d2["late_applied"], True)

    # predictions inside/outside
    pr1 = {p["id"]: p["inside"] for p in p1["predictions"]}
    for pid in sorted(pr1, key=lambda s: int(s.split("-")[1])):
        cmp("predictions", pid, pr1[pid], p2["predictions"][pid]["inside"])

    mism = [r for r in res if not r["equal"]]
    summary = dict(n_items=len(res), n_equal=sum(r["equal"] for r in res),
                   mismatches=mism,
                   by_group={g: [sum(1 for r in res if r["group"] == g and r["equal"]),
                                 sum(1 for r in res if r["group"] == g)]
                             for g in dict.fromkeys(r["group"] for r in res)},
                   gateon_label_map=GATEON_LABEL_MAP, p2_sha=s2)
    OUT.write_text(json.dumps(dict(summary=summary, items=res), ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if not mism else 1


if __name__ == "__main__":
    sys.exit(main())
