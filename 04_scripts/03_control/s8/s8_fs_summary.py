"""Tables of s8_fs_precheck.json (S8 pre-check, rev. 42 format). Run: python -I s8_fs_summary.py <json> [<json> ...]

Per base: READY time, D8 minimum, F_band, READY reading error, probe split of the seal estimate.
Per event (range over the start phases): min true force, time below F_min, lift time, re-approach, READY exit,
F10 periods, JP judge-level misses, JC judge-level misses (sampling_only count).
"""
import json
import sys

FMIN = 9.41459

for path in sys.argv[1:]:
    d = json.load(open(path, encoding="utf-8"))
    m = d["meta"]
    print(f"\n##### {path}: sink {m.get('sink')} rod {m.get('rod_side')} rear {m.get('rear_scale')} wall {m['wall_s']:.0f} s")
    runs = d["runs"]
    print("BASE floor judge Fs | t_ready D8min F_band | eps@READY | probe est / own / resid (kN, legs) | S_used/S_sec")
    for r in runs:
        pb = r.get("probe_breakdown_round1", [])
        est = "/".join(f"{p['seal_estimate_kN']:.1f}" for p in pb)
        own = "/".join(f"{p['own_friction_part_kN']:.1f}" for p in pb)
        res = "/".join(f"{p['residual_kN']:.1f}" for p in pb)
        ss = "/".join(f"{p['S_used_MN_m']:.1f}:{p['S_true_secant_MN_m']:.1f}" for p in pb)
        print(f"{r['floor']:7s} {r['judge']:8s} {r['Fs_kN']:3.0f} | {r['t_ready_s']:5.1f} {r['D8_min_true_after_liftoff_kN']:6.2f} "
              f"{r['F_band_kN']:5.2f} | " + " ".join(f"{x:+.2f}" for x in r["reading_minus_true_at_ready_kN"])
              + f" | {est} | {own} | {res} | {ss}")
    print("\nEVENT floor judge Fs event | min_true [lo, hi] leg | below_Fmin max | lift max | reap any/all | leaveREADY | F10 max"
          " | JP m0 miss eps | JC m0 miss eps (sampling_only)")
    for r in runs:
        by = {}
        for e in r["events"]:
            by.setdefault(e["event"], []).append(e)
        for ev, es in by.items():
            mt = [e["min_true_kN"] for e in es]
            legs = sorted({e["min_true_leg"] for e in es})
            reap = [e["reapproach"] for e in es]
            lv = [e["t_first_leave_ready_s"] for e in es]
            jp = sum(x["missed"] for e in es for x in e["JP_m0"]["episodes"])
            jpn = sum(len(e["JP_m0"]["episodes"]) for e in es)
            jc = sum(len(e["JC_m0_missed_episodes"]) for e in es)
            so = sum(x["sampling_only"] for e in es for x in e["JC_m0_missed_episodes"])
            print(f"{r['floor']:7s} {r['judge']:8s} {r['Fs_kN']:3.0f} {ev:16s} | [{min(mt):6.2f}, {max(mt):6.2f}] {legs} | "
                  f"{max(e['t_below_Fmin_s'] for e in es):4.1f} | {max(e['t_lift_s'] for e in es):4.1f} | "
                  f"{any(reap)}/{all(reap)} | {[None if v is None else round(v, 2) for v in lv]} | "
                  f"{max(e['F10_retract_on_low_load_periods'] for e in es)} | {jp}/{jpn} | {jc} ({so})")
