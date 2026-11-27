"""Tabulate the shape of lock_window_alignment blocks (key sets, 'reason' strings) and of the J9 input
(length of m2_clipped_steps_post_lift, whether lock_events exist) on stored already-seen lines.
Counts only. Usage: lwa_kinds.py <out.json> <jsonl>...
"""
import json
import sys
from collections import Counter


def main():
    out_path, files = sys.argv[1], sys.argv[2:]
    rep = {}
    for path in files:
        kinds = Counter()
        hyd = Counter()
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                lwa = rec.get("lock_window_alignment")
                if isinstance(lwa, dict):
                    kinds[(tuple(sorted(lwa)), str(lwa.get("reason"))[:80])] += 1
                h = rec.get("hydraulics_record")
                if isinstance(h, dict):
                    le = h.get("lock_events")
                    hyd[("lock_events_len_gt0" if le else "lock_events_empty_or_none",
                         "post_clip_type_" + type(h.get("m2_clipped_steps_post_lift")).__name__)] += 1
        rep[path] = {"lwa_kinds": [[list(k[0]), k[1], v] for k, v in kinds.most_common()],
                     "hyd_kinds": [[list(k), v] for k, v in hyd.most_common()]}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    main()
