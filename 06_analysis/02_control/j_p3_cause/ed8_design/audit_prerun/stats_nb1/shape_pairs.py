"""Shape mix of b_shape A/A candidates in the sealed G' key file (keys only, no results).
Counts, per aa_order position 0..2, candidates whose (depth_m, ramp_s) differ from the condition V0,
split by direction (candidate harsher = deeper or faster). Usage: shape_pairs.py <heldout_g_ed8.json> <out.json>"""
import json
import sys
from collections import Counter


def shape(job):
    t = job.get("twin") or {}
    return (t.get("depth_m"), t.get("ramp_s"))


def main():
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    c = Counter()
    base_shapes = Counter()
    for ln in d["lines"]:
        if ln["source"] != "b_shape":
            continue
        b = shape(ln["v0_pair"]["job"])
        base_shapes[str(b)] += 1
        c["slots"] += 1
        c[f"aa_len_{len(ln['aa_order'])}"] += 1
        for pos, cand in enumerate(ln["aa_order"][:3]):
            s = shape(cand)
            if s == b:
                c[f"pos{pos}_same_shape"] += 1
            else:
                harsher = (s[0] or 0) > (b[0] or 0) or ((s[1] or 9) < (b[1] or 9))
                c[f"pos{pos}_diff_{'cand_harsher' if harsher else 'cand_milder'}"] += 1
    out = {"counts": dict(sorted(c.items())), "base_shapes": dict(base_shapes),
           "shapes_m_s": d["candidates"]["b_shape"]["shapes_m_s"]}
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
    print(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    main()
