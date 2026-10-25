"""CB (counterbalance) vs pilot-check twin regression (spec 206: D8 min diff <= 0.1 kN).

Pairs CB_<x> (cb batch) with the pilot-check twin in the p1r batch and prints the D8 min
outside REANCHOR, REANCHOR min, min after lift-off, READY time, event min (row
"6 min after settlement" or "3 F_min (1 ms)"), max CB vent (cb_delta) and max rod pressure.
Usage: python -I s8cb_regress.py <cb_batch_dir> <p1r_batch_dir> <out_json>
"""
import json
import sys
from pathlib import Path

import numpy as np

PAIRS = {"CB_H4V_fdown3.5_Fs0": "K0V_top_fdown3.5_Fs0", "CB_H4V_fdown3.5_Fs8": "K8_top_fdown3.5_Fs8",
         "CB_G4_Fs0": "E_G4_Fs0", "CB_G4_Fs8": "E_G4_Fs8",
         "CB_RE1bF_Fs0": "E_RE1bF_Fs0", "CB_RE1bF_Fs8": "E_RE1bF_Fs8"}


def load(batch: Path):
    v = json.load(open(batch / "verify_S8C.json", encoding="utf-8"))
    met = {m["case"]: m for m in v["metrics"]}
    rows = {}
    for r in v["rows"]:
        rows.setdefault(r["case"], {})[r["item"]] = r
    return met, rows


def summary(batch: Path, case: str, met, rows):
    m = met[case]
    r = rows.get(case, {})
    ev = r.get("6 min after settlement") or r.get("3 F_min (1 ms)")
    pads = np.load(batch / case / "pads.npz", allow_pickle=True)
    cbd = pads["cb_delta"]
    return {"D8_min_excl_reanchor_kN": m.get("min_cyl_excl_reanchor_kN"),
            "reanchor_min_kN": m.get("min_cyl_reanchor_kN"),
            "min_after_liftoff_kN": m.get("min_cyl_after_liftoff_kN"),
            "ready_s": m["times_s"].get("ready"),
            "final_phase": m.get("final_phase"),
            "event_min_kN": None if ev is None else ev["value"],
            "cb_delta_max_mm": None if np.all(np.isnan(cbd)) else float(1e3 * np.nanmax(np.abs(cbd))),
            "rod_p_max_bar": float(np.nanmax(pads["rod_pressure"]) / 1e5),
            "head_p_max_bar": float(np.nanmax(pads["head_pressure"]) / 1e5)}


cb_dir, ref_dir = Path(sys.argv[1]), Path(sys.argv[2])
cb_met, cb_rows = load(cb_dir)
ref_met, ref_rows = load(ref_dir)
out = {}
for cb, ref in PAIRS.items():
    a = summary(cb_dir, cb, cb_met, cb_rows)
    b = summary(ref_dir, ref, ref_met, ref_rows)
    diff = {k: (a[k] - b[k]) if isinstance(a[k], (int, float)) and isinstance(b[k], (int, float)) else None
            for k in a}
    out[cb] = {"cb": a, "pilot_check": b, "twin": ref, "diff": diff}
    print(f"{cb:22s} vs {ref:22s}")
    for k in a:
        print(f"   {k:26s} CB {a[k]!s:>22.22s}  POC {b[k]!s:>22.22s}  diff {diff[k]!s:>12.12s}")
json.dump(out, open(sys.argv[3], "w", encoding="utf-8"), indent=1)
