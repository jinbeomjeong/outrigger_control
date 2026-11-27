"""NB-1: per C-J (i) item, which kinds the real A/A reading path gives on stored V0 pairs.

No judged value is printed: per item only "judged" (computed: pass or fail merged),
"not_judgeable" and "record: 입력 없음" counts, the not-judgeable reasons, and whether two
treatment labels give the same failed-item set (a yes/no count, not the set).
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed8-judge2")
for sub in ("04_scripts/04_hydraulic/coupled", "03_src"):
    sys.path.insert(0, str(WT / sub))

import jp3_ed6_judge as ed6  # noqa: E402
import jp3_ed7_judge as ed7  # noqa: E402
import jp3_ed8_judge as ed8  # noqa: E402
import jp3_j9main_judge as base  # noqa: E402
import judge_stage1_4368 as path1  # noqa: E402

MAIN = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\main.jsonl")
ITEMS = ("J1", "J2", "J3", "J4", "J5", "J6", "J7", "J8", "J9", "J10", "J11", "SA-4", "R15")


def item_table(treatment, reference, label):
    rows_by = path1._by_setting([treatment, reference])
    table = base._full_items(rows_by, (label,), ed8.V0_LABEL)
    ed7.replace_j7(table, rows_by, ed8.V0_LABEL)
    ed6.apply_reading_1(table, rows_by, ed8.V0_LABEL)
    s8 = ed6.s8_items(rows_by, (label,))
    entries = list(table[label]["items"]) + s8["failures"] + s8["stops"] + s8["not_judgeable"]
    r15 = base.r15_worsening(rows_by) if treatment["row"] == "R15" else None
    return entries, table[label]["no_reference"], r15


rows = [json.loads(t) for t in MAIN.read_text(encoding="utf-8").splitlines()]
v0 = [r for r in rows if (r.get("job") or {}).get("setting") == "V0"]
metrics = [ed7.metric_of(dict(r), (), ed8.V0_LABEL) for r in v0]
by_row = defaultdict(list)
for r, m in zip(v0, metrics):
    by_row[(m["row"], m["group"])].append((r, m))

kinds = {kind: Counter() for kind in ("event", "steady")}
reasons = Counter()
same_label = Counter()
n_pairs = Counter()
capped = Counter()
for row_name, members in sorted(by_row.items()):
    for (ra, ma), (rb, mb) in zip(members, members[1:]):
        kind = "event" if ma["is_event"] else "steady"
        n_pairs[kind] += 1
        capped[kind] += int(bool(ma["events_capped"] or mb["events_capped"]))
        reference = ed7.metric_of(dict(ra), (), ed8.V0_LABEL)
        per_label = {}
        for label in ("VB", "V0AA"):
            treatment = ed7.metric_of(dict(rb), (), label)
            treatment["row"], treatment["phase"] = reference["row"], reference["phase"]
            entries, missing, r15 = item_table(treatment, reference, label)
            per_label[label] = sorted((e["item"], e["kind"]) for e in entries
                                      if e["kind"] in ("fail", "stop"))
            if label != "VB":
                continue
            seen_nj = {e["item"] for e in entries if e["kind"] == "not_judgeable"}
            seen_noinput = {e["item"] for e in entries
                            if e["kind"] == "record" and e.get("detail") == "입력 없음"}
            for e in entries:
                if e["kind"] == "not_judgeable":
                    reasons[f"{kind} {e['item']}: {str(e.get('detail'))[:70]}"] += 1
            if r15 is not None and r15["state"] in base.R15_UNJUDGEABLE_STATES:
                seen_nj.add("R15")
                reasons[f"{kind} R15: {r15['state']}"] += 1
            for item in ITEMS:
                state = ("not_judgeable" if item in seen_nj else
                         "record 입력 없음" if item in seen_noinput else "judged_or_absent")
                kinds[kind][f"{item}|{state}"] += 1
            if missing:
                reasons[f"{kind} no_reference"] += 1
        # VB label without the J11 item vs the V0AA label: same failed-item set?
        vb = [x for x in per_label["VB"] if x[0] != "J11"]
        aa = [x for x in per_label["V0AA"] if x[0] != "J11"]
        same_label[f"{kind} same_without_J11={vb == aa}"] += 1

print(json.dumps({"stored_V0_lines": len(v0), "pairs": dict(n_pairs),
                  "pairs_with_events_capped": dict(capped),
                  "item_kinds": {k: dict(sorted(v.items())) for k, v in kinds.items()},
                  "not_judgeable_reasons": dict(reasons),
                  "VB_vs_V0AA_label": dict(same_label),
                  "J11_STOP_SETTINGS": list(path1.common.J11_STOP_SETTINGS),
                  "JUDGED_SETTING": path1.JUDGED_SETTING,
                  "S8_ROW": path1.S8_ROW}, ensure_ascii=False, indent=1))
