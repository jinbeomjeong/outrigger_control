"""Step 9: the stats Q-3 shape record with each slot's own pair (record only). Writes
shape_record_unique.json."""
import json
import sys
from pathlib import Path

JUDGE = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4\04_scripts\04_hydraulic\coupled")
sys.path.insert(0, str(JUDGE))
import jp3_ed8_judge as J  # noqa: E402

OUT = Path(sys.argv[1])
KEYS = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\keys_seal_41e107e9\heldout_g_ed8.json")
lines = json.loads(KEYS.read_text(encoding="utf-8"))["lines"]
slots = json.loads((OUT / "slots_stage5.json").read_text(encoding="utf-8"))["slots"]
out = {k: {"pairs": 0, "failures": 0, "slots": []} for k in ("same", "harsher", "milder", "not_comparable")}
for rec, line in zip(slots, lines):
    pair = rec["pair_unique"]
    if pair["state"] != "pair" or not rec["base_pass"]:
        continue
    sev = J.shape_severity(J.effective_shape(line["aa_order"][pair["tries"] - 1]),
                           J.effective_shape(line["v0_pair"]["job"]))
    out[sev]["pairs"] += 1
    out[sev]["failures"] += bool(pair["aa_fail"])
    if sev != "same":
        out[sev]["slots"].append([rec["index"], rec["source"], rec["slot"], bool(pair["aa_fail"])])
out["default_re1bf_shape"] = list(J.DEFAULT_RE1BF_SHAPE)
(OUT / "shape_record_unique.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print({k: (v["pairs"], v["failures"]) if isinstance(v, dict) else v for k, v in out.items()})
