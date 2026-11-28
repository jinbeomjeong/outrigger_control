"""Phase-based E-2 target status (rules draft r11 4.2.1 'target' row: READY -> LEVEL right after the
last READY entry) on the public check-run T4h records of both arms (A-v5, A2) and their R0 arms,
next to the jsonl final phase and the corrected G5b event lists of the two public reviews
(imua_check_review.md 50-53, imua_check_a2_review.md 1). Only phase / t_s arrays are read.

Also records, per file, the time from the last READY entry to the record end (harness stop rule) and,
for targets, t_L - t_R and t_end - t_L.

Usage: python -I -B e2_targets_check.py <v5 folder> <inputs.json> <out.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ARMS = {"A-v5": ("imua_check", "imua_check_A-v5_t4h"), "A2": ("imua_check_a2", "imua_check_A2_t4h"),
        "R0(A-v5 run)": ("imua_check", "imua_check_R0_t4h"), "R0(A2 run)": ("imua_check_a2", "imua_check_R0_t4h")}
CORRECTED = {"A-v5": {"S5_e0.002_VB-eta0.8", "S5_e0.003_VB-eta0.8"},
             "A2": {"S3_e0.0_VB-eta0.85", "S3_e0.002_VB-eta0.85", "S5_e0.001_VB-eta0.8",
                    "S5_e0.002_VB-eta0.8", "S4_e0.0_VB"}}


def entries(ph, name):
    return [k for k in range(len(ph)) if ph[k] == name and (k == 0 or ph[k - 1] != name)]


def status(f: Path) -> dict:
    z = np.load(f, allow_pickle=False)
    ph = np.asarray(z["phase"]).astype(str)
    t = np.asarray(z["t_s"], float)
    r = entries(ph, "ready")
    if not r:
        return {"target": False, "why": "no READY", "last_phase": ph[-1]}
    k_r = r[-1]
    k_l = next((k for k in range(k_r + 1, len(ph)) if ph[k - 1] == "ready" and ph[k] == "level"), None)
    rec = {"n_ready_entries": len(r), "end_minus_last_ready_s": float(t[-1] - t[k_r]), "last_phase": ph[-1],
           "phases_after_last_ready": sorted(set(ph[k_r:].tolist()))}
    if k_l is None:
        return rec | {"target": False}
    return rec | {"target": True, "tL_minus_tR_s": float(t[k_l] - t[k_r]), "end_minus_tL_s": float(t[-1] - t[k_l])}


def main(v5: str, inputs: str, out: str) -> int:
    base = Path(v5)
    inp = json.loads(Path(inputs).read_text(encoding="utf-8"))
    res = {}
    for arm, (run, sub) in ARMS.items():
        folder = base / run / sub
        per = {f.stem: status(f) for f in sorted(folder.glob("*.npz"))}
        targets = sorted(k for k, v in per.items() if v["target"])
        ends = [v["end_minus_last_ready_s"] for v in per.values() if "end_minus_last_ready_s" in v]
        res[arm] = {"files": len(per), "targets": targets,
                    "corrected_list": sorted(CORRECTED.get(arm, [])),
                    "targets_equal_corrected": (sorted(CORRECTED[arm]) == targets) if arm in CORRECTED else None,
                    "end_minus_last_ready_s_range": [min(ends), max(ends)] if ends else None,
                    "per_file": per}
    # jsonl final phase of rows flagged ready_lost_A in inputs.json (READY reached, final != READY)
    for arm in ("A-v5", "A2"):
        rows = inp["check"][arm]["rows"]
        res[arm]["inputs_ready_lost_rows"] = [
            {"case": r["case"], "setting": r["setting"], "eta": r["eta"], "eps": r["eps"],
             "final_phase_A": r["final_phase_A"]} for r in rows if r["ready_lost_A"]]
        res[arm]["final_phase_values"] = sorted({str(r["final_phase_A"]) for r in rows})
    Path(out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"status": "ok", **{a: {"targets": len(v["targets"]),
                                             "equal_corrected": v["targets_equal_corrected"]}
                                         for a, v in res.items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
