"""Count J9 / J11 input presence and failure conditions on stored run_v5 lines (already-seen rows, O8-1).

J9 (judge_stage1_r5.py:136-137): hydraulics_record.m2_clipped_steps_post_lift has any entry > 0.
J11 (judge_stage1_r5.py:139-140; judge4368_common.py:578-615): lock_window_alignment.n_late is not None
and n_late_fallback > 0 (also checks sum of n_late_fallback_by_leg).

Output: counts only (per file x setting), no per-line values. Usage: j9j11_scan.py <out.json> <jsonl>...
"""
import hashlib
import json
import sys
from collections import Counter, defaultdict


def fam(setting):
    s = str(setting)
    if s.startswith("V0"):
        return "V0"
    if s.startswith("LS"):
        return "LS*"
    if s.startswith("VB"):
        return s
    return s


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    out_path, files = sys.argv[1], sys.argv[2:]
    report = {}
    for path in files:
        c = defaultdict(Counter)
        units_j9 = defaultdict(set)
        units_j11 = defaultdict(set)
        bad_lines = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    bad_lines += 1
                    continue
                job = rec.get("job") or {}
                s = fam(job.get("setting"))
                k = c[s]
                k["lines"] += 1
                if "error" in rec and rec.get("error"):
                    k["error_lines"] += 1
                hyd = rec.get("hydraulics_record")
                if hyd is None:
                    k["hyd_none"] += 1
                else:
                    pc = hyd.get("m2_clipped_steps_post_lift")
                    if pc is None:
                        k["hyd_postclip_none"] += 1
                    else:
                        k["j9_judged"] += 1
                        vals = pc.values() if isinstance(pc, dict) else pc
                        if any((v or 0) > 0 for v in vals):
                            k["j9_fail"] += 1
                            units_j9[s].add(json.dumps(job, sort_keys=True)[:200])
                lwa = rec.get("lock_window_alignment")
                if lwa is None:
                    k["lwa_none"] += 1
                elif not isinstance(lwa, dict):
                    k["lwa_not_dict"] += 1
                else:
                    # assess_j11 (judge4368_common.py:578-615): fallback legs, n_late_fallback_by_leg > 0
                    k["j11_block"] += 1
                    fl = lwa.get("fallback_legs") or {}
                    legs = [x for x in ("FL", "FR", "RL", "RR")
                            if isinstance(fl, (dict, list, tuple)) and x in fl]
                    if "reason" in lwa:
                        k["j11_block_reason_" + str(lwa.get("reason"))[:30]] += 1
                    if legs:
                        k["j11_fallback_line"] += 1
                        byleg = lwa.get("n_late_fallback_by_leg") or {}
                        vals = [byleg.get(x) if isinstance(byleg, dict) else None for x in legs]
                        if any(not isinstance(v, int) or isinstance(v, bool) for v in vals):
                            k["j11_missing_on_fallback_leg"] += 1
                        elif any(v > 0 for v in vals):
                            k["j11_fail"] += 1
                            units_j11[s].add(json.dumps(job, sort_keys=True)[:200])
                    late_all = lwa.get("n_late_by_leg") or {}
                    if isinstance(late_all, dict) and any((v or 0) > 0 for v in late_all.values()
                                                          if isinstance(v, (int, float))):
                        k["any_leg_n_late_pos"] += 1
        report[path] = {"sha256": sha(path), "bad_lines": bad_lines,
                        "by_setting": {s: dict(v) for s, v in sorted(c.items())}}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print(json.dumps({"status": "ok", "files": len(files)}))


if __name__ == "__main__":
    main()
