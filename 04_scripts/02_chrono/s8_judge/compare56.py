"""Compare judge rev. 56 (new56) with the rev. 55 judge (pre55) on the same records.

Moved from the cad scratchpad (``cad-run55/compare56.py``, 2026-10-25); the folders are
arguments now. Rows keyed by (item, case); the C-S8-41 deferred row (item text changed in
rev. 56) is matched by its prefix. Every other common row must be byte-identical (json dump);
new rows are listed. The pre55 outputs were byte-identical to the rev55 outputs (file names
``*_rev55.json``): pass ``--pre-tag rev55`` to read those. Copies (local only, ``07_results`` is
gitignored): rev55 in ``07_results/S8/archive/18_S8_extra/rejudge/rev55/``, new56 in
``.../rejudge/rev56/``; the ml768 files are kept apart in
``07_results/S8/archive/rejudge_ml768/{rev55,rev56}/`` (``*_pre55``, ``*_rev55``, ``*_new56``),
so ``--pre`` / ``--new`` see them only if they are placed in the same folder.

usage::

    python -I -X utf8 compare56.py --pre <dir> --new <dir> [--pre-tag pre55] [--new-tag new56]
"""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--pre", type=Path, required=True, help="folder with the rev. 55 judge outputs")
ap.add_argument("--new", type=Path, required=True, help="folder with the rev. 56 judge outputs")
ap.add_argument("--pre-tag", default="pre55")
ap.add_argument("--new-tag", default="new56")
a = ap.parse_args()
NAMES = {"A": "S8ML", "B": "S8ML", "C": "S8C", "D": "S8C", "ml768": "S8ML", "mlj": "S8C",
         "p1r": "S8C", "rest": "S8C"}
DEF = "C-S8-41 RT deferral"
WKEYS = ("leg", "deferred_s", "next_start_s", "window_s", "min_kN", "min_t_s", "raw_min_kN",
         "lift", "below_F_min")


def key(r):
    item = r["item"]
    return (DEF if item.startswith(DEF) else item, str(r["case"]))


def dump(x):
    return json.dumps(x, sort_keys=True, default=str)


total_bad = 0
for w, kind in NAMES.items():
    pa = a.pre / f"verify_{kind}_{w}_{a.pre_tag}.json"
    pb = a.new / f"verify_{kind}_{w}_{a.new_tag}.json"
    if not (pa.exists() and pb.exists()):
        print(f"===== {w}: missing {pa if not pa.exists() else pb} (summary only?)")
        continue
    x0 = json.loads(pa.read_text("utf-8"))
    y0 = json.loads(pb.read_text("utf-8"))
    ra = {key(r): r for r in x0["rows"]}
    rb = {key(r): r for r in y0["rows"]}
    new = [k for k in rb if k not in ra]
    gone = [k for k in ra if k not in rb]
    diff = [k for k in ra if k in rb and k[0] != DEF and dump(ra[k]) != dump(rb[k])]
    fa = sum(1 for r in x0["rows"] if r["passed"] is False)
    fb = sum(1 for r in y0["rows"] if r["passed"] is False)
    print(f"===== {w}: rows {len(ra)} -> {len(rb)}, failed {fa} -> {fb}, other rows changed "
          f"{len(diff)}, gone {len(gone)}")
    total_bad += len(diff) + len(gone)
    for k in diff:
        print("  CHANGED", k)
    for k in gone:
        print("  GONE", k)
    for k in new:
        r = rb[k]
        print(f"  NEW [{r['kind']}] passed={r['passed']} crit={r.get('criterion_met')} | "
              f"{k[0][:100]} | value={dump(r['value'])[:400]}")
        print(f"      note={str(r.get('note'))[:600]}")
    k = (DEF, "*")
    if k in ra or k in rb:
        x, y = ra.get(k), rb.get(k)
        same = {f: dump(x[f]) == dump(y[f]) for f in ("value", "passed", "limit", "flagged",
                                                       "kind")}
        print("  C-S8-41 row: same", same, "| flag", x.get("flag"), "->", y.get("flag"),
              "| note same", x["note"] == y["note"])
        if x["note"] != y["note"]:
            print("    note new:", y["note"][:800])
        wa = {c: [{f: q[f] for f in WKEYS} for q in v] for c, v in x["per_run"].items()}
        wb = {c: [{f: q[f] for f in WKEYS} for q in v] for c, v in y["per_run"].items()}
        print("    windows (rev. 55 fields) identical:", dump(wa) == dump(wb),
              "| ref_flagged", y.get("ref_flagged"), "| compared", y.get("ref_compared_windows"),
              "| no ref", y.get("runs_without_reference"))
        if dump(wa) != dump(wb):
            total_bad += 1
            for c in wa:
                if dump(wa[c]) != dump(wb.get(c)):
                    print("     ", c, wa[c], "->", wb.get(c))
        for c, v in y["per_run"].items():
            for q in v:
                print(f"    {c} {q['leg']} win {q['window_s']} min {q['min_kN']} | run "
                      f"{q.get('leg_0_4s')} | ref {q.get('ref_0_4s')} | {q.get('ref_flag')}")
    print("  summary new:", dump(y0["meta"].get("summary"))[:700])
    print("  judge_revision head:", y0["meta"]["judge_revision"][:60])
print("TOTAL changed/gone existing rows (+ window changes):", total_bad)
