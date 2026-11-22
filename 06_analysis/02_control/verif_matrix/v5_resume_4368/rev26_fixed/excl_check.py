"""Check an exclusion list (excl_fields_r1/r2 form) against the verif audit findings (paths and categories only).

Excluded = categories I, S, F. N = compared after checkout-root normalisation (r2). A probe path matches an entry
when one is a prefix of the other; ``*`` in a probe matches any single token (used for row-id levels).
"""
import json
import sys
from collections import Counter

d = json.load(open(sys.argv[1], encoding="utf-8"))


def match(probe, entry):
    n = min(len(probe), len(entry))
    return all(a == "*" or a == b for a, b in zip(probe[:n], entry[:n]))


probe = {
    "harness_path1/grid_h10.json": [["v0_pair_source", "source"]],
    "harness_path1/family_f_trigger.json": [["v0_pair_source", "source"]],
    "harness_path2/p2v5c_grid.json": [["v0_pair", "source"], ["v0_pair", "sample", "detail"], ["imports"]],
    "harness_path1_retry1/r4_inputs.json": [["files"]],
    "harness_path1_retry1/stage1_judge.json": [["R4", "H-9_grid_R16_7", "files"], ["diff_vs_existing"]],
    "harness_path2/harness.json": [["bundles", "H-4", "files"], ["argv"]],
    "harness_path2/p2v5c_noise.json": [["reaggregated", "seedext", "V0", "detail"]],
    "harness_path2/c16.json": [["rows", "*", "items", "G6_source"]],
    "harness_path1/sidecars.json": [["rows", "[]", "start", "seals_ok"], ["rows", "[]", "start", "times"]],
    "harness_path1/family_table.json": [["rows", "[]", "source"]],
    "harness_path1/overlap_steps.json": [["rows", "[]", "output"]],
    "harness_path1/log_errors_run_harness.json": [["steps", "[]", "done_line"]],
    "harness_path1/u3_judge.json": [["G-3", "rules_seal"], ["diff_vs_existing"]],
    "harness_path2/v5j_u9.json": [["v5_options", "path"], ["r4_rev13_25_sha256"]],
}
for f, paths in probe.items():
    rows = d["d"].get(f, [])
    for p in paths:
        hit = [(tuple(e), c) for e, c in rows if match(p, e)]
        cats = sorted({c for _, c in hit})
        print(f, "/".join(p), "->", cats or "compared", hit[:3])
cnt = Counter(c for rows in d["d"].values() for _, c in rows)
print("d counts", dict(cnt), "c counts", dict(Counter(c for rows in d["c"].values() for _, c in rows)))
whole_args = [(f, e) for f, rows in d["d"].items() for e, c in rows
              if e and e[-1] in ("argv", "args", "cmd", "command", "commands_run") and c != "N"]
print("whole argument nodes excluded:", len(whole_args), whole_args[:6])
