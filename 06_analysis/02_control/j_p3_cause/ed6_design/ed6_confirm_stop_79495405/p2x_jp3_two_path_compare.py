"""Two-path comparison of the edition 6 J-P3 (③ rev 6) results, no new judgement.

Path 1 side (own data):
  * judged-row counts and breach totals from the path 1 judge outputs (`rev6` block);
  * per line: the line record `hydraulics_record.extend_bound_check` (in-run path 1 computation:
    per-leg `jp3a/b/c` counts, `jp3a_first_breach_t_s`, `jp3a_min_gap_bar`, `jp3_judged_row`);
  * per breach read: path 1 T4h at the first-breach time (class, phase n-1/n, locked n-1, run
    position inside the carry_ext run, rod read vs used bound at n and n+1).
Path 2 side: `ed6_p2_79495405/jp3_p2_<bundle>.json` (`judged_rows`, `totals`, `lines[].role`,
`breach_rows[].reads`). Lines are matched by (setting, T4h file name).
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405")
P2 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed6_p2_79495405")
LEGS = ("FL", "FR", "RL", "RR")
BUNDLES = {
    "confirm_a": (RUN / "confirm_a1/confirm_a.jsonl", RUN / "confirm_a1/judge/confirm_a_judge.json"),
    "confirm_b": (RUN / "confirm_a1/confirm_b.jsonl", RUN / "records_after_stop/A_a1/grid_judge.json"),
    "sens": (RUN / "records_after_stop/B_a1/sens.jsonl", RUN / "records_after_stop/B_a1/sens_judge.json"),
    "j9_main": (RUN / "records_after_stop/B_a1/j9_main.jsonl",
                RUN / "records_after_stop/B_a1/j9main_judge.json"),
}
TOL_T = 1e-6
TOL_BAR = 1e-9


def find_rev6(obj):
    if isinstance(obj, dict):
        if "rev6" in obj and isinstance(obj["rev6"], dict) and "runs_judged" in obj["rev6"]:
            return obj["rev6"]
        for v in obj.values():
            r = find_rev6(v)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_rev6(v)
            if r is not None:
                return r
    return None


def p1_read_context(t4h: Path, t_breach: float, leg: int):
    with np.load(t4h, allow_pickle=False) as d:
        t = d["t_s"]
        names = [str(x) for x in d["jp3_class_names"]]
        cls = d["jp3_class"][:, leg]
        ph = d["phase"]
        locked = d["locked"][:, leg]
        rod = d["rod_pressure_Pa"][:, leg]
        bound = d["jp3_used_bound_Pa"][:, leg]
    i = int(np.argmin(np.abs(t - t_breach)))
    run_pos = 0
    j = i
    while j >= 0 and cls[j] == cls[i]:
        run_pos += 1
        j -= 1
    before = names[cls[j]] if j >= 0 else None
    over_n1 = bool(i + 1 < len(t) and rod[i + 1] > bound[i + 1])
    return {"dt": float(abs(t[i] - t_breach)), "class": names[cls[i]], "phase_prev": str(ph[i - 1]),
            "phase": str(ph[i]), "locked_prev": bool(locked[i - 1]), "locked_now": bool(locked[i]),
            "run_pos": run_pos, "class_before_run": before,
            "rod_bar": float(rod[i]) / 1e5, "bound_bar": float(bound[i]) / 1e5,
            "next_over": over_n1}


def main() -> int:
    bad = 0
    for bundle, (jsonl, judge) in BUNDLES.items():
        p2 = json.loads((P2 / f"jp3_p2_{bundle}.json").read_text(encoding="utf-8"))
        r6 = find_rev6(json.loads(judge.read_text(encoding="utf-8")))
        p1_judged = r6["runs_judged"]
        p1_tot = (r6["jp3a_breach_reads"], r6["jp3b_breach_over_tol_reads"], r6["jp3c_breach_reads"])
        p1_rows_breach = r6.get("runs_with_breach")
        p2_tot = tuple(p2["totals"][k] for k in ("jp3a_breach_reads", "jp3b_breach_over_tol_reads",
                                                    "jp3c_breach_reads"))
        print(f"== {bundle}: judged p1 {p1_judged} / p2 {p2['judged_rows']}; a/b/c p1 {p1_tot} / p2 {p2_tot};"
              f" breach rows p1 {p1_rows_breach} / p2 {len(p2['breach_rows'])}; status p1 {r6['status']}"
              f" / p2 {p2['status']}")
        # path 2 lines by (setting, t4h file)
        p2_lines = {}
        for ln in p2["lines"]:
            setting = ln["line"].split(" ", 2)[1]
            p2_lines[(setting, ln["t4h"]["file"])] = ln
        p2_breach = {}
        for br in p2["breach_rows"]:
            setting = br["line"].split(" ", 2)[1]
            fname = next(v["t4h"]["file"] for k, v in p2_lines.items()
                         if v["line"] == br["line"])
            p2_breach[(setting, fname)] = br
        t4h_dir = jsonl.parent / f"{jsonl.stem}_t4h"
        n_lines = n_judged_rec = judged_diff = leg_diff = read_diff = 0
        forms = Counter()
        matched_reads = 0
        unmatched_p2 = set(p2_breach)
        for text in jsonl.read_text(encoding="utf-8").splitlines():
            if not text.strip():
                continue
            row = json.loads(text)
            n_lines += 1
            setting = row["job"]["setting"]
            key = (setting, row.get("t4h_file"))
            ln = p2_lines.get(key)
            if ln is None:
                print("  path 1 line not in path 2:", key)
                bad += 1
                continue
            ebc = ((row.get("hydraulics_record") or {}).get("extend_bound_check") or {})
            j1 = bool(ebc.get("jp3_judged_row"))
            n_judged_rec += j1
            if j1 != (ln["role"] == "judged"):
                judged_diff += 1
                print("  judged-row difference", key, j1, ln["role"])
            if not j1:
                continue
            a = ebc.get("jp3a_breach_reads") or [0] * 4
            b = ebc.get("jp3b_breach_over_tol_reads") or [0] * 4
            c = ebc.get("jp3c_breach_reads") or [0] * 4
            pb = ln.get("breach") or {}
            if (list(a), list(b), list(c)) != (pb.get("jp3a_breach_reads"),
                                               pb.get("jp3b_breach_over_tol_reads"),
                                               pb.get("jp3c_breach_reads")):
                leg_diff += 1
                print("  per-leg difference", key, a, b, c, pb)
            if not sum(a):
                continue
            br = p2_breach.get(key)
            unmatched_p2.discard(key)
            if br is None:
                print("  path 1 breach line missing in path 2 breach_rows:", key)
                bad += 1
                continue
            p2_reads = {}
            for rd in br["reads"]:
                p2_reads.setdefault(rd["leg"], []).append(rd)
            firsts = ebc.get("jp3a_first_breach_t_s") or [None] * 4
            gaps = ebc.get("jp3a_min_gap_bar") or [None] * 4
            for li, leg in enumerate(LEGS):
                if not a[li]:
                    if leg in p2_reads:
                        read_diff += 1
                        print("  path 2 read on a leg path 1 has none", key, leg)
                    continue
                reads = p2_reads.get(leg, [])
                if len(reads) != a[li]:
                    read_diff += 1
                    print("  read count difference", key, leg, a[li], len(reads))
                    continue
                t_first = min(r["t_s"] for r in reads)
                max_excess = max(r["excess_bar"] for r in reads)
                ok_t = abs(t_first - firsts[li]) <= 1e-3
                ok_g = abs(-gaps[li] - max_excess) <= 1e-6
                ctx = p1_read_context(t4h_dir / row["t4h_file"], firsts[li], li)
                ok_rod = all(abs(ctx["rod_bar"] - r["rod_reading_bar"]) <= 1e-9 and
                             abs(ctx["bound_bar"] - r["used_bound_bar"]) <= 1e-9 for r in reads[:1])
                # path 2 `read_index_in_class_run` is 0-based (its summary text says 3rd/4th read);
                # path 1 run_pos counts reads in the run including this one (1-based).
                ok_pos = ctx["run_pos"] == reads[0]["read_index_in_class_run"] + 1
                if not (ok_t and ok_g and ok_rod and ok_pos):
                    read_diff += 1
                    print("  read value difference", key, leg, firsts[li], t_first, -gaps[li], max_excess,
                          ctx, reads[0]["read_index_in_class_run"])
                else:
                    matched_reads += len(reads)
                forms[(ctx["class"], f"{ctx['phase_prev']}/{ctx['phase']}",
                       f"locked_prev={ctx['locked_prev']}", f"locked_now={ctx['locked_now']}",
                       f"before={ctx['class_before_run']}", f"pos={ctx['run_pos']}",
                       f"next_over={ctx['next_over']}")] += a[li]
        for key in unmatched_p2:
            print("  path 2 breach line with no path 1 breach:", key)
            bad += 1
        print(f"  lines {n_lines}, path 1 record judged rows {n_judged_rec}, judged-row differences "
              f"{judged_diff}, per-leg count differences {leg_diff}, read differences {read_diff}, "
              f"reads matched (leg, first t, excess, rod read, bound, run position) {matched_reads}")
        for f, n in sorted(forms.items(), key=lambda x: -x[1]):
            print("  path 1 form", n, f)
        bad += judged_diff + leg_diff + read_diff
    print("differences total", bad)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
