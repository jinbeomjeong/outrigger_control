"""Path 1 against path 2 for T-JR-12b and the T-JR-12a VBJ J-P3 (606f8713, read only).

Path 1: j9_runs/606f8713/12b_vbk_a1/judge/judge.json, dg3_a1/judge/t12_VBJ.json
Path 2: ed5_p2_606f8713/tjr12b_p2.json, jp3_rev6_VBJ_VBJ0_p2.json (dynamics-expert, tool dde4499d)
Output: p1p2_compare.json in this folder (control-expert, 2026-11-23, judgement section 7).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

J = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
P1_12B = J / "j9_runs/606f8713/12b_vbk_a1/judge/judge.json"
P1_T12 = J / "j9_runs/606f8713/dg3_a1/judge/t12_VBJ.json"
P2_12B = J / "ed5_p2_606f8713/tjr12b_p2.json"
P2_T12 = J / "ed5_p2_606f8713/jp3_rev6_VBJ_VBJ0_p2.json"
OUT = Path(__file__).resolve().parent / "p1p2_compare.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm(key: str) -> str:
    return key.split("#", 1)[-1]


def main() -> None:
    a = json.loads(P1_12B.read_text(encoding="utf-8"))
    b = json.loads(P2_12B.read_text(encoding="utf-8"))
    ta = json.loads(P1_T12.read_text(encoding="utf-8"))
    tb = json.loads(P2_T12.read_text(encoding="utf-8"))
    rr = a["ready_rule"]
    rows = []

    def add(item, v1, v2, kind="judged"):
        rows.append({"item": item, "kind": kind, "path1": v1, "path2": v2, "equal": v1 == v2})

    add("status", a["status"], b["status"])
    add("exit", a["exit"], b["exit_code"])
    add("N", a["decision"]["n"], b["N"])
    add("N_opp", a["n_opp"], b["N_opp"])
    add("k", a["decision"]["k"], b["supplement"]["k"])
    add("b3_needed", a["decision"]["n_topup"]["needs_b3"], b["supplement"]["b3_needed"])
    add("b4_needed", a["decision"]["witness_topup"]["needs_b4"], b["supplement"]["b4_needed"])
    add("(1) judged pairs N1", a["n_fault_judged"], b["new_fault"]["judged_pairs"])
    add("(1) new FAULT count", len(a["new_faults_recorded"]), len(b["new_fault"]["failing"]))
    add("(2)+(3) n23", rr["n_vbk_worse"], b["n23"]["value"])
    add("READY loss", rr["n_ready_loss"], b["n23"]["loss"])
    add("READY +30 s", rr["n_ready_plus30"], b["n23"]["delay"])
    add("k_allow", rr["allow_k"], b["n23"]["k_allow"])
    loss1 = sorted(p["key"] for p in a["pairs"] if p.get("ready_outcome") not in ("ok", None)
                   and p.get("category") == "opportunity")
    add("READY loss / delay keys", loss1, sorted(norm(k) for k in b["n23"]["loss_keys"] + b["n23"]["delay_keys"]))
    add("(4) J-P3 status", a["jp3"]["status"], b["jp3"]["status"])
    add("(4) J-P3 judged rows", a["jp3"]["runs_judged"], b["jp3"]["judged_runs"])
    add("(4) J-P3 breach a/b/c",
        [a["jp3"]["jp3a_breach_reads"], a["jp3"]["jp3b_breach_over_tol_reads"], a["jp3"]["jp3c_breach_reads"]],
        [b["jp3"]["totals"][k] for k in ("jp3a_breach_reads", "jp3b_breach_over_tol_reads", "jp3c_breach_reads")])
    add("(4) judged_key_missing", a["jp3"]["judged_key_missing_runs"], b["jp3"]["judged_key_missing_runs"])
    cats = {blk: a["categories_by_block"][blk] for blk in ("b1", "b2")}
    add("by_block opportunity / VBK0 READY unreached",
        {blk: [cats[blk]["opportunity"], cats[blk]["vbk0_ready_unreached"]] for blk in cats},
        {blk: [b["by_block"][blk]["opportunity"], b["by_block"][blk]["vbk0_ready_missing"]] for blk in cats},
        "record")
    add("by_block n23", {blk: rr["by_block"][blk]["n_vbk_worse"] for blk in ("b1", "b2")},
        {blk: b["by_block"][blk]["n23"] for blk in ("b1", "b2")}, "record")
    add("by_cell opportunity",
        {c: rr["by_cell"][c]["n_opp"] for c in sorted(rr["by_cell"])},
        {lab.split()[0]: v["opportunity"] for lab, v in b["by_cell"].items()}, "record")
    add("by_cell n23",
        {c: rr["by_cell"][c]["n_vbk_worse"] for c in sorted(rr["by_cell"])},
        {lab.split()[0]: v["n23"] for lab, v in b["by_cell"].items()}, "record")
    add("A/A counted pairs", sorted(rr["aa_floor"]["counted"]),
        sorted(x["case"] for x in b["aa_record"]["keys"]), "record")
    add("A/A pairs", rr["aa_floor"]["pairs"], b["aa_record"]["pairs"], "record")
    add("VBK0 stall signature lines", sorted(x["key"] for x in rr["stall_signature_vbk0_lines"]),
        sorted(norm(x["key"]) for x in b["deadlock_signature"]["vbk0_signature"]), "record")
    add("VBK stall signature pairs (READY loss)", sorted(rr["stall_signature_pairs"]),
        sorted(norm(x["key"]) for x in b["deadlock_signature"]["ready_loss_vbk_signature"]), "record")
    add("VBK0-only worse", rr["n_vbk0_worse"],
        len(b["vbk0_only_bad"]["vbk0_ready_missing_with_vbk_ready"]) + len(b["vbk0_only_bad"]["opp_vbk0_late_over_30s"]),
        "record")
    add("coverage totals (r58 / r59 / r510)",
        [a["coverage_totals"][k] for k in ("jp3_r58_witness_carries", "jp3_r59_substeps", "jp3_r510_candidates")],
        [b["coverage_opportunity_vbk"]["totals"][k] for k in ("jp3_r58_witness", "jp3_r59_substeps", "jp3_r510_candidates")],
        "record")
    # tau_R trigger phase: path 1 counts opportunity pairs, path 2 every tau_R pair; check the set sizes
    tr2 = [p for p in b["pairs"] if p.get("cell_phase") == "tau_R"]
    tr2_opp = [p for p in tr2 if norm(p["key"]) in {q["key"] for q in a["pairs"] if q["category"] == "opportunity"}]
    add("tau_R trigger phase (PROBE / LEVEL)",
        [a["tau_r_trigger_phase"].get("PROBE"), a["tau_r_trigger_phase"].get("LEVEL")],
        [b["tau_R_trigger_acting_phase"]["acting_phase_trigger_read=probe"],
         b["tau_R_trigger_acting_phase"]["acting_phase_trigger_read=level"]], "record")
    set_note = {"path1_tau_R_counted": sum(a["tau_r_trigger_phase"].values()),
                "path2_tau_R_pairs": len(tr2), "path2_tau_R_opportunity_pairs": len(tr2_opp)}
    # T-JR-12a VBJ J-P3
    add("T-JR-12a VBJ J-P3 status", ta["J-P3"]["status"], tb["status"])
    add("T-JR-12a VBJ J-P3 judged rows", ta["J-P3"]["runs_judged"], tb["judged_runs"])
    add("T-JR-12a VBJ J-P3 record rows", ta["J-P3"]["runs_by_case"]["record_only_sensor_grade"], tb["record_runs"])
    add("T-JR-12a VBJ J-P3 breach sum", 0 if ta["J-P3"]["outcome"] == "pass" else None, tb["breach_sum"])
    out = {"inputs": {str(p.relative_to(J)): sha(p) for p in (P1_12B, P1_T12, P2_12B, P2_T12)},
           "rows": rows, "judged_all_equal": all(r["equal"] for r in rows if r["kind"] == "judged"),
           "record_unequal": [r["item"] for r in rows if r["kind"] == "record" and not r["equal"]],
           "tau_R_set_note": set_note}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False)[:6000])


if __name__ == "__main__":
    main()
