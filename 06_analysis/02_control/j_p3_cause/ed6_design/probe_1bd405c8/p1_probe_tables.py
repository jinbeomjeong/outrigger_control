"""Edition 6 probe (run 1bd405c8, 320 lines): failure units per arm and plant, the sealed-arm
(a1a2b) prediction table, and the remaining a1a2b failure (read only).

Inputs: j9_runs/1bd405c8/ed6_probe_a1/ed6_probe_share.json (python-expert share tool; groups carry
the V0-relative failure items of the 436.8 path-1 definitions D-07..D-17) and ed6_probe.jsonl.
Conventions: negative feedback, T_s 0.1 s, d = 1; forces kN (E-3 min_F_after_W), READY s.
Outputs (this folder): p1_units.csv (plant x arm x key), p1_pred_a1a2b.csv, p1_summary.json.
control-expert 2026-11-24 (analysis after the probe, design input; disclosed).
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

P = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\1bd405c8\ed6_probe_a1")
OUT = Path(__file__).resolve().parent
ARMS = ["a2", "b", "a2b", "a1b", "a1a2", "a1a2b", "a1a2bh", "a1a2b1"]
PLANTS = ["J", "c005", "c04", "v05", "v15"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    d = json.loads((P / "ed6_probe_share.json").read_text(encoding="utf-8"))
    rows = {(r["plant"], r["arm"], r["key"]): r for r in d["rows"]}
    keys = sorted({r["key"] for r in d["rows"]})
    plants = sorted({r["plant"] for r in d["rows"]}, key=lambda x: PLANTS.index(x) if x in PLANTS else 99)
    fail = {}
    items = defaultdict(list)
    for gk, g in d["groups"].items():
        plant, arm = gk.split(" ", 1)
        fail[(plant, arm)] = set(g["failed_keys"])
        for it in g["fail_items"]:
            items[(plant, arm)].append(it)
    units = []
    for (plant, arm, key), r in sorted(rows.items()):
        units.append({"plant": plant, "arm": arm, "key": key, "fail_vs_V0": key in fail.get((plant, arm), set()),
                      "final_phase": r["final_phase"], "t_first_ready_s": r["t_first_ready_s"],
                      "min_force_kN": r["min_force_kN"], "min_force_leg": r["min_force_leg"],
                      "Fmin_10hz_kN": r.get("Fmin_10hz_kN"),
                      "diag_release_delay_s": r.get("other_leg_retract_delay_max_s"),
                      "held_fraction": r.get("held_fraction"), "stall_signature": r.get("stall_signature"),
                      "a1_triggers": r.get("lsb_a1_triggers"), "a1_cap": r.get("lsb_a1_cap_reached"),
                      "a2_floors": r.get("lsb_a2_floors"), "a2_hold": r.get("lsb_a2_hold_periods"),
                      "b1_blocked": r.get("lsb_b1_blocked_periods"), "b3_periods": r.get("lsb_b3_periods"),
                      "sha10": r["commands_sha256"][:10]})
    with open(OUT / "p1_units.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(units[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(units)
    pred = [u for u in units if u["arm"] == "a1a2b"]
    pred.sort(key=lambda u: (keys.index(u["key"]), plants.index(u["plant"])))
    with open(OUT / "p1_pred_a1a2b.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pred[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(pred)
    table = {arm: {pl: sorted(fail.get((pl, arm), set())) for pl in plants} for arm in ARMS}
    counts = {arm: sum(len(v) for v in table[arm].values()) for arm in ARMS}
    full_items = {f"{pl}": items[(pl, "a1a2b")] for pl in plants if items[(pl, "a1a2b")]}
    hold_items = {f"{pl}": [i for i in items[(pl, "a1a2bh")]] for pl in plants if items[(pl, "a1a2bh")]}
    summ = {"probe_jsonl_sha256": sha(P / "ed6_probe.jsonl"), "share_sha256": sha(P / "ed6_probe_share.json"),
            "units": len(units), "failed_units_by_arm": counts, "failed_keys_by_arm_plant": table,
            "a1a2b_fail_items": full_items, "a1a2bh_fail_items": hold_items,
            "share_components": d["share"]["components"], "kept": d["share"]["kept"]}
    (OUT / "p1_summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: summ[k] for k in ("probe_jsonl_sha256", "units", "failed_units_by_arm",
                                           "failed_keys_by_arm_plant", "a1a2b_fail_items", "a1a2bh_fail_items")},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
