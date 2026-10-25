"""Print the R51-1 closed-loop results (r51_reapp_closed_loop.py JSON) as compact rows; worst over start phases.
Usage: python -I r51_summary.py <json> [detail_event_id]
"""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
detail = sys.argv[2] if len(sys.argv) > 2 else None
print("meta", d["meta"]["wall_s"], "s")
rows = {}
for r in d["runs"]:
    if "error" in r:
        print(r["base"], r["variant"], "ERROR", r["error"])
        continue
    head = (f"{r['base']:14s} {r['variant']:6s} READY {r['t_ready_s']:.1f} D8min {r['D8_min_true_after_liftoff_kN']:.1f} "
            f"scale {r['twist_scale']} pre {len(r['pre_event_reapproach'])}")
    print(head)
    by = {}
    for e in r["events"]:
        by.setdefault(e["event"], []).append(e)
    for ev, es in by.items():
        if "error" in es[0]:
            print("   ", ev, es[0]["error"])
            continue
        g = lambda k: max(x[k] for x in es)  # noqa: E731
        mn = lambda k: min(x[k] for x in es)  # noqa: E731
        ok = all(all(x["gate_U832"].values()) for x in es)
        print(f"    {ev:9s} pairU {g('pair_union_s'):.3f} pairLast {g('pair_last_touch_s'):.3f} adjS {g('adj_sum_s'):.3f} "
              f"adjGap {g('adj_max_gap_mm'):.2f} starts {[x['n_starts'] for x in es]} late {[x['n_late_starts'] for x in es]} "
              f"sgn {[x['sign_changes'] for x in es]} W+ {g('W_after1.5_pos_J'):.0f} minF {mn('min_true_kN'):.1f} "
              f"att {g('max_att_change_deg'):.3f} READY {[x['t_back_ready_s'] for x in es]} {'OK' if ok else 'FAIL'}")
        if detail and ev == detail:
            for x in es:
                print("       off", x["offset_s"], "starts", x["starts"], "deferred", x["deferred"][:10])
                print("         lifts", {k: (v['sum_s'], v['last_touch_s'], v['max_gap_mm']) for k, v in x["lifts"].items()})
                print("         W", x["W_bins_J"], "Dptp", x["D_ptp_kN_bins_from1.5"])
