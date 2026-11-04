"""Off-side judge rows and events, and the first difference of the new rigid rows from the off pairs. Read only. Adds c4g1_rigid_off_extra.json.

Usage: python -I -B -X utf8 show2.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

MAIN = Path(r"C:\workspace\outrigger_control")
OUT = MAIN / "06_analysis/02_control/touch_phase/chrono"
VD = MAIN / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/verify"
VERIFY = {"R9_sym": ("verify_final_A_bottom_rpB_Fs0_20261031_011936.json", "A_bottom_rpB_Fs0"), "R4": ("verify_final_K24_top_roll5.5_Fs4_20261030_230357.json", "K24_top_roll5.5_Fs4")}


def main() -> None:
    doc = json.loads((OUT / "c4g1_rigid_values.json").read_text(encoding="utf-8"))
    extra = {}
    for row, v in doc.items():
        don, doff = Path(v["on"]["dir"]), Path(v["off"]["dir"])
        ra, rb = np.load(don / "record/record.npz", allow_pickle=False), np.load(doff / "record/record.npz", allow_pickle=False)
        m = min(len(ra["t"]), len(rb["t"]))
        off = float(ra["t"][-1]) - float(v["on"]["end_t_s"])
        fd = {}
        for k in ("F_cyl", "s_motor", "u_cmd", "u_applied"):
            same = (ra[k][:m] == rb[k][:m]).reshape(m, -1).all(axis=1)
            fd[k] = None if same.all() else round(float(ra["t"][int(np.argmin(same))] - off), 2)
        ev = [str(e) for e in json.loads((doff / "controller_events.json").read_text(encoding="utf-8"))]
        e = {"first_diff_rel_s": fd, "rows_compared": m, "off_end_s": v["off"]["end_t_s"], "off_events_warn": [x for x in ev if any(q in x for q in ("WARN", "FAULT", "PAUSED", "reapproach"))]}
        if row in VERIFY:
            f, cid = VERIFY[row]
            vd = json.loads((VD / f).read_text(encoding="utf-8"))
            e["off_rows"] = {r["item"]: r["value"] for r in vd["rows"] if r.get("case") == cid and r["item"].startswith(("3 F_min", "2 attitude", "4 max"))}
            e["off_failed"] = vd["meta"].get("failed")
        extra[row] = e
        print(row, json.dumps(e, ensure_ascii=False)[:700])
    (OUT / "c4g1_rigid_off_extra.json").write_text(json.dumps(extra, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
