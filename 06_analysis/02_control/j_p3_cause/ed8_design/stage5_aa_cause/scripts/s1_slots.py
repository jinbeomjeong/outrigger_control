"""Stage 5 A/A cause analysis, step 1: rebuild the stage 5 slots with the T8'''' judge code
(read only, imported from the judge worktree) and record every slot with a unique index.

Writes slots_stage5.json / slots_stage5.csv into the evidence folder given as argv[1].
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

JUDGE = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4\04_scripts\04_hydraulic\coupled")
sys.path.insert(0, str(JUDGE))

import jp3_ed8_judge as J  # noqa: E402
import jp3_ed8_rules as rules  # noqa: E402
import jp3_ed7_judge as ed7  # noqa: E402
import ed8_key_lists as keys  # noqa: E402
import run_v5  # noqa: E402
import jp3_ed8_gate_judge as gate  # noqa: E402

MAIN = Path(r"C:\workspace\outrigger_control")
RUNS = MAIN / r"06_analysis\02_control\j_p3_cause\j9_runs\56849248"
KEYS = MAIN / r"06_analysis\02_control\j_p3_cause\ed8_design\keys_seal_41e107e9\heldout_g_ed8.json"
GRID_KEYS = MAIN / r"06_analysis\02_control\j_p3_cause\ed6_design\keys\confirm_b_grid192.json"
V0_ROWS = [RUNS / r"ho_v0_a1\ed8_heldout_v0.jsonl", RUNS / r"ho_aa2_a1\ed8_heldout_aa2.jsonl",
           RUNS / r"ho_aa3_a1\ed8_heldout_aa3.jsonl"]
OUT = Path(sys.argv[1])


def unit_detail(condition, found, folders):
    reference = ed7.metric_of(dict(condition), folders, J.V0_LABEL)
    treatment = ed7.metric_of(dict(found), folders, J.TREATMENT_LABEL)
    treatment["row"], treatment["phase"] = reference["row"], reference["phase"]
    verdicts = J.unit_item_verdicts([treatment], [reference],
                                    own_setting_items=J.AA_OWN_SETTING_ITEMS)
    unit = verdicts["units"][(reference["row"], str(reference["phase"]))]
    return unit, reference, treatment


def main():
    document = json.loads(KEYS.read_text(encoding="utf-8"))
    rows = [row for path in V0_ROWS for row in gate.read_rows(path)]
    rows_by = {run_v5.job_key(row["job"]): row for row in rows}
    folders = tuple(folder for path in V0_ROWS for folder in ed7.t4h_folders_of(path, gate.read_rows(path)))
    grid = J.GridStore(MAIN)
    hashes = J.stored_cluster_hashes(json.loads(GRID_KEYS.read_text("utf-8")), grid)
    out = []
    names = {}
    for index, line in enumerate(document["lines"]):
        slot = J.slot_inputs(line, rows_by, folders, hashes)
        names.setdefault(line["slot"], []).append(index)
        condition = rows_by[run_v5.job_key(line["v0_pair"]["job"])]
        cond_starts = keys.main_line_starts(condition)
        pair = rules.aa_pair_of(slot)
        rec = {"index": index, "source": line["source"], "slot": line["slot"],
               "condition_job": line["v0_pair"]["job"], "layer": slot["layer"],
               "base_pass": slot["base_pass"], "first_alias": slot["first_alias"],
               "condition_starts": cond_starts,
               "candidates": [], "pair_unique": pair}
        for job, cand in zip(line["aa_order"], slot["aa_candidates"]):
            found = rows_by.get(run_v5.job_key(job))
            rec["candidates"].append({"job": job, **cand,
                                      "starts": keys.main_line_starts(found)})
        if pair.get("state") == "pair" and pair.get("aa_fail"):
            found = rows_by[run_v5.job_key(line["aa_order"][pair["tries"] - 1])]
            unit, reference, treatment = unit_detail(condition, found, folders)
            rec["failed_items"] = unit["failed_items"]
        out.append(rec)
    dup = {k: v for k, v in names.items() if len(v) > 1}
    # counts the rules way (dict by name: last same-name slot's pair) vs unique index
    by_name = {}
    for rec in out:
        by_name[rec["slot"]] = rec["pair_unique"]
    def counts(use_unique):
        c = {"E": {"n": 0, "n_aa": 0, "x_aa": 0}, "N": {"n": 0, "n_aa": 0, "x_aa": 0}}
        for rec in out:
            if rec["first_alias"]:
                continue
            p = rec["pair_unique"] if use_unique else by_name[rec["slot"]]
            L = c[rec["layer"]]
            L["n"] += rec["base_pass"]
            if rec["base_pass"] and p["state"] == "pair":
                L["n_aa"] += 1
                L["x_aa"] += p["aa_fail"]
        return c
    summary = {"n_slots": len(out), "n_names": len(names), "duplicate_names": len(dup),
               "duplicate_sources": sorted({tuple(out[i]["source"] for i in v) for v in dup.values()}),
               "counts_by_name_as_tool": counts(False), "counts_unique_index": counts(True)}
    (OUT / "slots_stage5.json").write_text(json.dumps({"summary": summary, "slots": out}, indent=1,
                                                       ensure_ascii=False, default=str), encoding="utf-8")
    with open(OUT / "slots_stage5.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["index", "source", "slot", "offset_s", "depth_m", "ramp_s", "layer", "base_pass",
                    "first_alias", "pair_state", "tries", "crossed", "aa_fail", "cand_layers",
                    "cand_offsets", "failed_items"])
        for rec in out:
            j = rec["condition_job"]
            t = j.get("twin", {})
            w.writerow([rec["index"], rec["source"], rec["slot"], j.get("offset_s"), t.get("depth_m"),
                        t.get("ramp_s"), rec["layer"], rec["base_pass"], rec["first_alias"],
                        rec["pair_unique"]["state"], rec["pair_unique"]["tries"],
                        ";".join(map(str, rec["pair_unique"]["crossed"])),
                        rec["pair_unique"].get("aa_fail"),
                        ";".join(c["layer"] for c in rec["candidates"]),
                        ";".join(str(c["job"].get("offset_s")) for c in rec["candidates"]),
                        " | ".join(rec.get("failed_items", []))])
    print(json.dumps(summary, default=str))


if __name__ == "__main__":
    main()
