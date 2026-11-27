"""V0 identity facts: the preset tag from the judge worktree code, run_v5.options_of('V0'), and
the identity-field presence of the stored main.jsonl V0 lines (key names / tag only)."""
import json
import sys
from collections import Counter
from pathlib import Path

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed8-judge")
sys.path.insert(0, str(WT / "04_scripts" / "04_hydraulic" / "coupled"))
sys.path.insert(0, str(WT / "03_src"))

from outrigger_sim.control.c2 import C2Config  # noqa: E402
from outrigger_sim.hydraulics import v5_options  # noqa: E402

out = {}
preset = C2Config().with_10hz_d1()
out["preset_tag"] = v5_options.controller_tag(None, preset)
out["preset_has_ed8_changes"] = bool(getattr(preset, "has_ed8_changes", False))
out["preset_lock_start_b_on"] = v5_options.is_lock_start_b_on(preset)
out["preset_lsb_components"] = v5_options.lsb_components_of(preset)
out["preset_probe_d6_enabled"] = bool(getattr(getattr(preset, "probe_d6", None), "is_enabled",
                                              False))
out["preset_liftoff_slow_on"] = v5_options.is_liftoff_slow_on(preset)
out["preset_order_gate_on"] = v5_options.is_order_gate_on(preset)
import run_v5  # noqa: E402

flow, options = run_v5.options_of("V0")
out["options_of_V0"] = None if options is None else options.to_dict()
out["V0_in_T4H_SETTINGS"] = "V0" in run_v5.T4H_SETTINGS
for tag in ("final_C4G2_LAS_K1", "final_C4G2_LAS_K1_LSB_ED8", "final_C4G2_P3X_LAS_K1_LSB_ED8"):
    out[f"rev_of[{tag}]"] = v5_options.extend_start_revision_of_tag(tag)

main = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\main.jsonl")
tags, keys_present, hopt, hrec = Counter(), Counter(), Counter(), Counter()
n = 0
for text in main.read_text(encoding="utf-8").splitlines():
    row = json.loads(text)
    if (row.get("job") or {}).get("setting") != "V0":
        continue
    n += 1
    tags[str(row.get("controller_tag", "<absent>"))] += 1
    for name in ("lsb_components", "lsb_settings", "probe_d6_settings", "probe_d6_record",
                 "probe_stiffness_record", "ib_block_record", "ed8_settings", "ed8_record",
                 "lsb_record", "t4h_file", "head_only_declared"):
        if name in row:
            keys_present[name] += 1
    hopt["null" if row.get("hydraulic_options") is None else "set"] += 1
    hrec["null" if row.get("hydraulics_record") is None else "set"] += 1
out["stored_main_V0"] = {"lines": n, "controller_tag": dict(tags),
                         "identity_keys_present": dict(keys_present),
                         "hydraulic_options": dict(hopt), "hydraulics_record": dict(hrec)}
print(json.dumps(out, indent=1, default=str))
