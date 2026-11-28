"""Step 7: the sealed rules' stage5_selection (T8'''' jp3_ed8_rules, read only) on the same 339
slots, (a) with the tool's slot names (reproduces ho_k_selection) and (b) with unique slot
names "<source>|<slot>". Record only (not a judgement). Writes rerule_unique_names.json."""
import json
import sys
from pathlib import Path

JUDGE = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4\04_scripts\04_hydraulic\coupled")
sys.path.insert(0, str(JUDGE))
import jp3_ed8_rules as rules  # noqa: E402

OUT = Path(sys.argv[1])
KEYS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\keys_seal_41e107e9\heldout_g_ed8.json")
lines = json.loads(KEYS.read_text(encoding="utf-8"))["lines"]
slots = json.loads((OUT / "slots_stage5.json").read_text(encoding="utf-8"))["slots"]


def slot_dicts(unique):
    out = []
    for rec, line in zip(slots, lines):
        assert rec["slot"] == line["slot"]
        name = f"{rec['source']}|{rec['slot']}" if unique else rec["slot"]
        out.append({"slot": name, "first_alias": rec["first_alias"], "layer": rec["layer"],
                    "base_pass": rec["base_pass"],
                    "aa_candidates": [{"layer": c["layer"], "hash_equal": c["hash_equal"],
                                       "aa_fail": c["aa_fail"]} for c in rec["candidates"]],
                    "aa_order_length": len(line["aa_order"])})
    return out


res = {}
for unique in (False, True):
    sel = rules.stage5_selection(slot_dicts(unique))
    res["unique_names" if unique else "tool_names"] = {
        k: sel[k] for k in ("status", "reasons", "merged", "merged_why", "layers", "n_before_merge",
                            "aa_summary")}
res["note"] = ("record only: the sealed rules code run on the 339 rebuilt slots; tool_names must "
               "equal ho_k_selection.json; unique_names gives each slot its own A/A pair")
(OUT / "rerule_unique_names.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
