"""Recount the final r79 sensor study (merged files) with and without the pad A reference cases (read-only).

Pad A cases: ref harness inner '<soil>|A|0,0' (soil G1/J1/J2/S1).  Q-E rule (spec 429.11.2): L2 runs except the
S1 front patch (g6 / g6r '+S1@FL' / '+S1@FR'); failure = run 'pass' False; upper bound = one-sided 95 %
Clopper-Pearson (checked against the recorded 11/855 -> 0.021206).  R9 (R4 code) activation = an event name
containing 'CLEARANCE_MARGIN' in the run record; the total is checked against the recorded 480 (L1 81, L2 399).
"""
import json
import re
from collections import Counter
from pathlib import Path

from scipy.stats import beta

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s8\rev79")
judge = json.loads((D / "fin_r79_merged_judgement.json").read_text(encoding="utf-8"))
res = json.loads((D / "fin_r79_merged.json").read_text(encoding="utf-8"))["results"]


def cp_up(k, n):
    return 1.0 if k >= n else float(beta.ppf(0.95, k + 1, n - k))


def is_pad_a(inner):
    return re.fullmatch(r"(G1|J1|J2|S1)\|A\|.*", inner) is not None


def is_s1_front(inner):
    return re.search(r"\+S1@F[LR]", inner) is not None


def stats(runs, drop_a):
    rest = [r for r in runs if not is_s1_front(r["inner"]) and not (drop_a and is_pad_a(r["inner"]))]
    s1f = [r for r in runs if is_s1_front(r["inner"])]
    k = sum(1 for r in rest if not r["pass"])
    rows = Counter(row for r in rest if not r["pass"] for row, v in r["rows"].items() if not v.get("ok", True))
    return len(rest), k, cp_up(k, len(rest)), sum(1 for r in s1f if not r["pass"]), len(s1f), dict(rows)


L2 = [r for r in judge["runs"] if r["level"] == "L2"]
print("L2 runs", len(L2), "pad A L2 runs", sum(is_pad_a(r["inner"]) for r in L2),
      "pad A L2 failures", sum(1 for r in L2 if is_pad_a(r["inner"]) and not r["pass"]))
for drop in (False, True):
    n, k, up, s1k, s1n, rows = stats(L2, drop)
    print(f"Q-E drop_padA={drop}: rest {k}/{n} = {k/n*100:.2f} %, CP95 {up*100:.2f} %, S1 front {s1k}/{s1n}, rows {rows}")

# L1 reference pass (harness_pass of the stored L1 runs)
L1 = [r for r in res if r["level"] == "L1"]
def l1_pass(r):
    b = r.get("base", {})
    return bool(b.get("pass", b.get("passed")))
for drop in (False, True):
    sel = [r for r in L1 if not (drop and is_pad_a(r["inner"]))]
    print(f"L1 drop_padA={drop}: harness pass {sum(l1_pass(r) for r in sel)}/{len(sel)}")
print("pad A L1 runs:", [(r["inner"], l1_pass(r)) for r in L1 if is_pad_a(r["inner"])])


# R9 (R4 code) activation
def r4_fired(r):
    blob = json.dumps(r.get("base", {}).get("events", "")) + json.dumps(r.get("r79", {}))
    return "CLEARANCE_MARGIN" in blob


fired = [r for r in res if r4_fired(r)]
c = Counter((r["level"], is_pad_a(r["inner"])) for r in fired)
print("R4 fired total", len(fired), dict(c))
pass_by_key = {r["key"]: r["pass"] for r in judge["runs"]}
fail_fired = [r["key"] for r in fired if r["level"] == "L2" and pass_by_key.get(r["key"].replace("cand=current#", "")) is False]
print("R4-fired L2 failures (key match):", len(fail_fired))
print("judge key example:", judge["runs"][0]["key"], "| result key example:", res[0]["key"])
