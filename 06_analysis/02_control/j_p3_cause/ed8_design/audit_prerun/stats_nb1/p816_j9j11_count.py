"""J9 / J11 opportunity and failure COUNTS ONLY on P8-16 pre-run L2_impl run_v5 lines (user permission 2026-11-27).

Selection (same as control_t8p_evidence/structural_inputs.py:52-54): job is a dict with "case",
ed8_probe.arm == "L2_impl"; lines carrying "error" are counted as not judgeable for both items.
J9  (judge_stage1_r5.py:136-137): hydraulics_record.m2_clipped_steps_post_lift present -> judged; any > 0 -> fail.
J11 (judge4368_common.py:578-615, stop setting): block not a dict -> not judgeable; fallback legs with
     n_late_fallback_by_leg missing/non-int -> not judgeable; any > 0 -> fail; no fallback leg -> pass.
No other arm, item or value is read out. Usage: p816_j9j11_count.py <p816.jsonl> <out.json>
"""
import hashlib
import json
import sys
from collections import Counter

LEGS = ("FL", "FR", "RL", "RR")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    raw = open(src, "rb").read()
    c = Counter()
    for text in raw.decode("utf-8").splitlines():
        if not text.strip():
            continue
        r = json.loads(text)
        job = r.get("job")
        if not (isinstance(job, dict) and "case" in job and (r.get("ed8_probe") or {}).get("arm") == "L2_impl"):
            continue
        c["l2_impl_run_v5_lines"] += 1
        if "error" in r:
            c["j9_not_judgeable"] += 1
            c["j11_not_judgeable"] += 1
            continue
        pc = (r.get("hydraulics_record") or {}).get("m2_clipped_steps_post_lift")
        if pc is None:
            c["j9_not_judgeable"] += 1
        else:
            c["j9_judged"] += 1
            vals = pc.values() if isinstance(pc, dict) else pc
            if any((v or 0) > 0 for v in vals):
                c["j9_fail"] += 1
        block = r.get("lock_window_alignment")
        if not isinstance(block, dict):
            c["j11_not_judgeable"] += 1
            continue
        fl = block.get("fallback_legs") or {}
        legs = [x for x in LEGS if isinstance(fl, (dict, list, tuple)) and x in fl]
        if not legs:
            c["j11_judged_no_fallback_leg"] += 1
            continue
        c["j11_opportunity_fallback_leg"] += 1
        by_leg = block.get("n_late_fallback_by_leg")
        vals = [by_leg.get(x) if isinstance(by_leg, dict) else None for x in legs]
        if any(isinstance(v, bool) or not isinstance(v, int) for v in vals):
            c["j11_not_judgeable"] += 1
        elif any(v > 0 for v in vals):
            c["j11_fail"] += 1
    keys = ["l2_impl_run_v5_lines", "j9_judged", "j9_fail", "j9_not_judgeable", "j11_judged_no_fallback_leg",
            "j11_opportunity_fallback_leg", "j11_fail", "j11_not_judgeable"]
    out = {"source": src, "source_sha256": hashlib.sha256(raw).hexdigest(), "counts": {k: c.get(k, 0) for k in keys}}
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=1)
    print(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    main()
