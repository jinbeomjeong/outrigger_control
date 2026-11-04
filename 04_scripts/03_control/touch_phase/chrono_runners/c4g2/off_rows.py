"""Judge rows of the event off pairs with the same judge, and where rows 7, 8 differ from the stored 40 s runs in pads. Writes c4g2_off_rows.json. No simulation.

Usage: python -I -B -X utf8 off_rows.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MAIN = Path(r"C:\workspace\outrigger_control")
OUT = MAIN / "06_analysis/02_control/touch_phase/chrono"
sys.path.insert(0, str(HERE / "wt" / "03_src"))
ASYM = HERE.parent / "cad_asym"
S8 = MAIN / "07_results/S8"
BATCH = {"r16_d000": (ASYM / "runs_r16/r16_mirror2_d000", "G1L_RE1bF_FL_top_o050_Fs4"), "r16_d070": (ASYM / "runs_r16/r16_mirror2_d070", "G1L_RE1bF_FL_top_o050_Fs4"),
         "R12": (S8 / "final_E_G4_Fs4_20261030_233941", "E_G4_Fs4"), "R15": (S8 / "final_G1L_RE1bF_FL_top_Fs0_20261031_003000", "G1L_RE1bF_FL_top_Fs0")}
KEEP = ("item 9 J_P", "item 9 J_C", "item 9 M5", "4 max", "3 F_min", "RE1b re-READY", "6 re-READY", "2 attitude")
STAMP = "20261104_222344"


def main() -> None:
    from outrigger_sim.verify.s8_control import judge_batch

    out = {}
    for k, (b, cid) in BATCH.items():
        vf = HERE / f"verify_off_{k}.json"
        judge_batch(b, vf, root=MAIN, ref_batch=None, lookup_batches=[], deferred_ref=None)
        doc = json.loads(vf.read_text(encoding="utf-8"))
        out[k] = {"failed": doc["meta"].get("failed"), "hold": doc["meta"].get("hold"), "rows": {r["item"]: r.get("value") for r in doc["rows"] if r.get("case") == cid and r["item"].startswith(KEEP) and "sensitiv" not in r["item"] and "raw reading" not in r["item"]}}
        print(k, out[k]["failed"], out[k]["hold"], json.dumps(out[k]["rows"], ensure_ascii=False)[:1100])
    bits = {}
    for row, name in (("R9_mirror2_d000_off", "mirror2_d000"), ("R9_mirror2_d035_off", "mirror2_d035")):
        a = np.load(S8 / f"c4g2_{row}_{STAMP}" / "A_bottom_rpB_Fs0" / "pads.npz", allow_pickle=False)
        b = np.load(ASYM / "runs/batch_164123" / name / "pads.npz", allow_pickle=False)
        n = min(len(a["t"]), len(b["t"]))
        info = {"samples_stored": int(len(b["t"])), "t_last_stored": float(b["t"][-1])}
        for k in ("R_world", "N", "T", "L", "utilisation", "F_cyl_mean_20ms", "F_cyl", "F_cyl_min_interval", "s_motor"):
            x, y = a[k][:n], b[k][:n]
            bad = ~(np.equal(x, y) | (np.isnan(x) & np.isnan(y))).reshape(n, -1).all(axis=1)
            info[k] = {"bad_samples": int(bad.sum()), "first_t": None if not bad.any() else float(a["t"][int(np.argmax(bad))]), "max_abs": float(np.nanmax(np.abs(x - y)))}
        bits[row] = info
        print(row, json.dumps(info))
    (OUT / "c4g2_off_rows.json").write_text(json.dumps({"off_rows": out, "pads_bit_detail": bits}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
