"""Digest of Chrono P3b-form re-judge files (result_rejudge_rev60.json, block 'p3b') + controller events of
result.json for a list of case folders: P3 rows, key values, final-feature events (SGS / R4 / L1gs / DSb75 /
E3c10 / LWa / P30fz), crawler recontacts, probe rounds.

Usage: python -I p3b_digest.py <out json> <case dir> [<case dir> ...]
"""
import json
import sys
from pathlib import Path

FEAT = ("WARN_LIFT_STROKE", "FAULT", "FLAT_SOIL_MARGIN", "LOC_CLEARANCE", "LOC_REVOKED", "DIFF_SINK",
        "TWIST_UNSETTLED", "LIFT_PAUSED", "LOC_WINDOW", "crawler_liftoff", "relevel", "probe_start", "ready",
        "done")
out = {}
for c in sys.argv[2:]:
    p = Path(c)
    rj = json.loads((p / "result_rejudge_rev60.json").read_text(encoding="utf-8"))
    res = json.loads((p / "result.json").read_text(encoding="utf-8"))
    b = rj.get("p3b") or rj
    o = {"unchanged_blocks_equal": rj.get("unchanged_blocks_equal"), "params_file_match": rj.get("params_file_match"),
         "checks": b.get("checks"), "t_loop_start_s": res.get("t_loop_start_s"), "mass_scale": res.get("mass_scale")}
    for k in ("P3-1_recontact", "P3-2_loc", "P3-3_leg_force", "P3-4_attitude", "P3-5_clearance_stroke", "P3-6_ready",
              "P3-7_plateau", "departure", "P3-8_counts", "reapproach_limit_FLAG", "pre_liftoff_min_F_cyl",
              "P3-1_crawler", "P3-1"):
        v = b.get(k)
        if v is not None:
            o[k] = v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if not (
                isinstance(vv, list) and len(vv) > 12)}
    ev = res.get("events") or []
    o["events_sel"] = [json.dumps(e, ensure_ascii=False)[:150] for e in ev
                       if any(t in json.dumps(e) for t in FEAT)][:80]
    o["phases"] = res.get("phases")
    out[p.name] = o
Path(sys.argv[1]).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
for n, o in out.items():
    c = o["checks"] or {}
    print("==", n, "blocks_equal", o["unchanged_blocks_equal"], "params", o["params_file_match"])
    print("  checks", json.dumps({k: v for k, v in c.items() if not isinstance(v, (dict, list)) or k in (
        "P3-4_absmax_deg",)}, default=str)[:1400])
    print("  ready", json.dumps(o.get("P3-6_ready"), default=str)[:300])
    print("  F", json.dumps((o.get("P3-3_leg_force") or {}).get("F_min_after_N"), default=str))
    print("  P3-5", json.dumps({k: v for k, v in (o.get("P3-5_clearance_stroke") or {}).items()
                                if k in ("rut_clearance_min_after_first_ready_m", "s_motor_max_m", "t_first_ready_s",
                                         "within")}, default=str))
    print("  LOC", json.dumps({k: v for k, v in (o.get("P3-2_loc") or {}).items() if not isinstance(v, (dict,))},
                              default=str)[:900])
    print("  dep", json.dumps(o.get("departure"), default=str)[:500])
    for e in o["events_sel"]:
        print("   ", e)
