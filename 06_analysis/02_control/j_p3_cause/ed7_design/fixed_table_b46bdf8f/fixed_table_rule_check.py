"""Synthetic inputs for the two fixed-table rule functions (each branch reached)."""
import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("fixed_table", SCRIPT)
module = importlib.util.module_from_spec(spec)
sys.modules["fixed_table"] = module
spec.loader.exec_module(module)


def unit(setting, row, phase, verdict, key="k"):
    return {"setting": setting, "row": row, "phase": phase, "verdict": verdict, "key": key}


def d_row(setting, verdict, breach=0, fault=(), key="k"):
    return {"setting": setting, "key": key, "is_counted_for_k": setting == "VBM",
            "v0_verdict": verdict, "v0_opportunity": True, "condition_breach_reads": breach,
            "fault_reasons": list(fault) if fault is not None else None,
            "line_jp3a_breach_reads": 0}


results = {}
results["two phases one row -> fail"] = module.cluster_rule_from_fixed(
    [unit("VBMslow", "R15", "o0", "fail"), unit("VBMslow", "R15", "o0.05", "fail")]
)["fixed_table_alone"] == "fail"
results["five singles over settings -> fail"] = module.cluster_rule_from_fixed(
    [unit(s, f"R{i}", "o0", "fail") for i, s in enumerate(
        ("VBMslow", "VBMfast", "VBMc005", "VBMc04", "VBMslow"))])["fixed_table_alone"] == "fail"
results["four singles -> not_failed"] = module.cluster_rule_from_fixed(
    [unit(s, "R1", "o0", "fail") for s in ("VBMslow", "VBMfast", "VBMc005", "VBMc04")]
)["fixed_table_alone"] == "not_failed"
results["missing that could fail -> undetermined"] = module.cluster_rule_from_fixed(
    [unit("VBMslow", "R15", "o0", "fail"), unit("VBMslow", "R15", "o0.05", "missing")]
)["fixed_table_alone"].startswith("undetermined")
results["D four VBM fails -> fail"] = module.confirmation_rule_from_fixed(
    [d_row("VBM", "fail", key=str(i)) for i in range(4)])["fixed_table_alone"] == "fail"
results["D three VBM fails -> not_failed"] = module.confirmation_rule_from_fixed(
    [d_row("VBM", "fail", key=str(i)) for i in range(3)])["fixed_table_alone"] == "not_failed"
results["D VBMslow fails not counted"] = module.confirmation_rule_from_fixed(
    [d_row("VBMslow", "fail", key=str(i)) for i in range(5)])["fixed_table_alone"] == "not_failed"
results["D breach -> fail"] = module.confirmation_rule_from_fixed(
    [d_row("VBMslow", "pass", breach=1)])["fixed_table_alone"] == "fail"
results["D fault -> fail"] = module.confirmation_rule_from_fixed(
    [d_row("VBMslow", "pass", fault=("gate fault0",))])["fixed_table_alone"] == "fail"
results["D breach missing -> undetermined"] = module.confirmation_rule_from_fixed(
    [d_row("VBM", "pass", breach=None)])["fixed_table_alone"].startswith("undetermined")
for name, ok in results.items():
    print(("ok  " if ok else "BAD ") + name)
sys.exit(0 if all(results.values()) else 1)
