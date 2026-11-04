"""Compact old vs new table for the report, plus the first-difference detail. Read only.

Usage: python -I -B -X utf8 compact.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

MAIN = Path(r"C:\workspace\outrigger_control")
OUT = MAIN / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/v4_recheck"
S8 = MAIN / "07_results/S8"
JC, JP = "item 9 J_C M1 missed / M1' late / M3 median / M2 / M4 max (record)", "item 9 J_P M1 missed / M1' late / M3 median / M2 / M4 max (record)"
M5 = "item 9 M5 closed loop: min true / under F_min [s] / lifted [s]"


def s(v, n=3):
    if isinstance(v, float):
        return round(v, n)
    if isinstance(v, list):
        return [s(x, n) for x in v]
    return v


def main() -> None:
    exp = json.loads((OUT / "expected_before_run.json").read_text(encoding="utf-8"))
    old = exp["stored_batch_values"]
    doc = json.loads((OUT / "recheck_values.json").read_text(encoding="utf-8"))
    for cid, n in doc["cases"].items():
        o = old[cid]
        ro, rn = o["rows"], n["rows"]
        g = lambda r, k: s(r.get(k, {}).get("value"))
        print(f"== {cid} wall {n['wall_s']:.0f} end {n['s8_end']['end_t_s']:.1f}/{n['s8_end']['final_phase']} timeout {n['s8_end']['timeout']} phase {n['phase_at_event']} READY {s(o['ready_t_s'])}->{s(n['ready_t_s'])} ev {s(n['event_t_s'])}")
        print("  F3", g(ro, "3 F_min (1 ms)"), "->", g(rn, "3 F_min (1 ms)"), "|", (rn.get("3 F_min (1 ms)") or {}).get("note", "")[:70], "| passed", rn.get("3 F_min (1 ms)", {}).get("passed"))
        print("  M5", g(ro, M5), "->", g(rn, M5), " JC", g(ro, JC), "->", g(rn, JC), " JP", g(ro, JP), "->", g(rn, JP))
        for k in sorted(set(ro) | set(rn)):
            if ("re-READY" in k and "<=" in k) or k.startswith(("4 max", "C2 REANCHOR", "RE1b re-READY")) or "REANCHOR min" in k:
                print("  ", k[:50], g(ro, k), "->", g(rn, k), "passed", rn.get(k, {}).get("passed"))
        fd = n["first_diff_vs_stored_t_s"]
        print("  first diff", {k: s(v, 2) for k, v in fd.items()}, " dip", n["touch_dip_held"], " warn", n["warn_fault"], " failed", n["failed_rows"])
        oe, ne = set(o["events"]), set(n["events"])
        print("  events +", sorted(ne - oe)[:14])
        print("  events -", sorted(oe - ne)[:14])
        if n["legs_after_event"]:
            for leg in ("FL", "FR", "RL", "RR"):
                a, b = o["legs_after_event"][leg], n["legs_after_event"][leg]
                print(f"   {leg} min {a['min_interval_kN']:.3f}->{b['min_interval_kN']:.3f} at +{b['t_rel_s']:.2f}s 1ms {a['min_sample_1ms_kN']:.3f}->{b['min_sample_1ms_kN']:.3f} under {a['under_F_min_interval_s']:.3f}->{b['under_F_min_interval_s']:.3f} air {a['airborne_s']:.3f}->{b['airborne_s']:.3f}")
    print("sums JP", sum(c["rows"][JP]["value"][0] for c in doc["cases"].values()), "JC", sum(c["rows"][JC]["value"][0] for c in doc["cases"].values()))
    # what differs at the first head-pressure difference
    b = Path(doc["batch"])
    for cid, src in (("N_G4_Fs0_pressure", "rest_20261024_233615"), ("K8_top_fdown3.5_Fs8", "p1r_20261024_222013")):
        ra, rb = np.load(b / cid / "record/record.npz", allow_pickle=False), np.load(S8 / src / cid / "record/record.npz", allow_pickle=False)
        common = sorted(set(ra.files) & set(rb.files))
        print(cid, "keys new only", sorted(set(ra.files) - set(rb.files))[:10], "old only", sorted(set(rb.files) - set(ra.files))[:10])
        m = min(len(ra["t"]), len(rb["t"]))
        out = {}
        for k in common:
            if ra[k].dtype.kind not in "fiub" or ra[k].shape[0] != len(ra["t"]) or rb[k].shape[0] != len(rb["t"]):
                continue
            x, y = ra[k][:m], rb[k][:m]
            same = np.logical_or(x == y, np.logical_and(x != x, y != y)).reshape(m, -1).all(axis=1)
            if not same.all():
                i = int(np.argmin(same))
                out[k] = [float(ra["t"][i]), float(np.nanmax(np.abs((x - y).astype(float))))]
        print("  differing keys [first t, max abs diff]", {k: [round(v[0], 2), float(f"{v[1]:.3g}")] for k, v in sorted(out.items(), key=lambda kv: kv[1][0])[:14]})
    # the fourth RE1b row of the manuscript range, stored final run (not rerun here)
    p = OUT.parent / "verify" / "verify_final_E_RE1bF_Fs8_20261031_000914.json"
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        print("final E_RE1bF_Fs8", {r["item"][:40]: s(r["value"]) for r in d["rows"] if r.get("case") == "E_RE1bF_Fs8" and r["item"] in (M5, "4 max pressure in the event transient", "4 max moving pressure outside the event transient", "RE1b re-READY <= 60 s")})


if __name__ == "__main__":
    main()
