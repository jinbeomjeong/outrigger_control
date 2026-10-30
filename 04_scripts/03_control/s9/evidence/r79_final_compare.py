"""r79 sensor study on the final controller (fin_r79.json / fin_r79_judgement.json) against the former line
(r79_L1L2_all_R2DS.json runs = 05708b2 line; r79_L2_judgement_R2.json verdicts = R2 line): Q-E verdict (L2, S1 front
excluded, one-sided Clopper-Pearson 95 % upper bound <= 3 %), L1 reference, per-run command-hash changes, final-rule
activations (R8 = SGS soil stop: WARN_LIFT_STROKE_LIMITED / FAULT_LIFT_STROKE_LIMIT; R9 = R4 flat soil margin:
INFO_LOC_FLAT_SOIL_MARGIN) and the verdict changes on those runs.

Usage: python -I r79_final_compare.py <rev79 dir> <out json> [<final run json> <final judgement json>]
  (defaults fin_r79.json / fin_r79_judgement.json; 2026-10-31: fin_r79_merged.json /
  fin_r79_merged_judgement.json = fin + the fin2 per-leg re-run of the G1-base G6 cases)
"""
import json
import sys
from collections import Counter
from pathlib import Path

from scipy.stats import beta

D = Path(sys.argv[1])


def load(n):
    return json.loads((D / n).read_text(encoding="utf-8"))


def cp_upper(k, n, a=0.05):
    return 1.0 if k >= n else float(beta.ppf(1 - a, k + 1, n - k))


def find(d, key):
    if isinstance(d, dict):
        if key in d:
            return d[key]
        for v in d.values():
            r = find(v, key)
            if r is not None:
                return r
    elif isinstance(d, list):
        for v in d:
            r = find(v, key)
            if r is not None:
                return r
    return None


def ev_text(r):
    return json.dumps(r.get("events", []), default=str)


FIN_RUN = sys.argv[3] if len(sys.argv) > 3 else "fin_r79.json"
FIN_JUDGE = sys.argv[4] if len(sys.argv) > 4 else "fin_r79_judgement.json"
fin, old = load(FIN_RUN), load("r79_L1L2_all_R2DS.json")
def nk(k):
    return k.split("#", 1)[1] if k.startswith("cand=") else k


rf, ro = {nk(r["key"]): r for r in fin["results"]}, {nk(r["key"]): r for r in old["results"]}
HKEYS = ("commands_sha256", "cmd_sha256", "hash", "command_hash")


def hsh(r):
    v = (r.get("base") or {}).get("commands_sha256")
    if v:
        return v
    for k in HKEYS:
        v = find(r, k)
        if v:
            return v
    return None


changed = sorted(i for i in rf if i in ro and hsh(rf[i]) != hsh(ro[i]))
r4 = sorted(i for i in rf if "FLAT_SOIL_MARGIN" in ev_text(rf[i]))
guard = sorted(i for i in rf if "WARN_LIFT_STROKE_LIMITED" in ev_text(rf[i]) or "FAULT_LIFT_STROKE_LIMIT" in ev_text(rf[i]))
r4_old = sorted(i for i in ro if "FLAT_SOIL_MARGIN" in ev_text(ro[i]))

jf, jo = load(FIN_JUDGE), load("r79_L2_judgement_R2.json")


def run_verdicts(j):
    out = {}
    for r in j["runs"]:
        k = nk(r.get("key") or r.get("id"))
        fails = [s for s, row in (r.get("rows") or {}).items() if isinstance(row, dict) and row.get("ok") is False]
        if r.get("pass") is False and not fails:
            fails = ["pass=False"]
        out[k] = {"level": r.get("level"), "fails": fails, "s1front": any(t in k for t in ("S1@FL", "S1@FR"))}
    return out


vf, vo = run_verdicts(jf), run_verdicts(jo)
sample = jf["runs"][0]


def qe(v):
    l2 = {k: x for k, x in v.items() if (x["level"] or k.split("|")[0]) == "L2"}
    rest = {k: x for k, x in l2.items() if not x["s1front"]}
    k = sum(bool(x["fails"]) for x in rest.values())
    s1 = {k2: x for k2, x in l2.items() if x["s1front"]}
    return {"L2_runs": len(l2), "rest_n": len(rest), "rest_fail": k, "rest_rate": k / max(len(rest), 1),
            "rest_cp95": cp_upper(k, len(rest)), "s1front_fail": sum(bool(x["fails"]) for x in s1.values()),
            "s1front_n": len(s1), "fail_rows": Counter(s for x in rest.values() for s in x["fails"])}


qf, qo = qe(vf), qe(vo)
flips = [(k, vo[k]["fails"], vf[k]["fails"]) for k in vf if k in vo and bool(vo[k]["fails"]) != bool(vf[k]["fails"])]
r4_fail = [(k, vf[k]["fails"]) for k in r4 if k in vf and vf[k]["fails"]]
by_level_r4 = Counter(rf[k]["level"] for k in r4)
by_group_r4 = Counter((rf[k]["level"], (rf[k].get("harness") or "?")) for k in r4)
out = {"n_fin": len(rf), "n_old": len(ro), "hash_key_found": hsh(next(iter(rf.values()))) is not None,
       "hash_changed_n": len(changed), "hash_changed": changed[:400],
       "hash_changed_not_r4": [i for i in changed if i not in r4][:50],
       "r4_runs_n": len(r4), "r4_runs_by_level": dict(by_level_r4), "r4_runs_by_level_harness": {
           f"{a}|{b}": n for (a, b), n in by_group_r4.items()}, "r4_runs_old_n": len(r4_old),
       "guard_or_sgs_runs": guard, "qe_final": qf, "qe_former_R2": qo, "verdict_flips_vs_R2": flips,
       "r4_runs_failing_final": r4_fail, "reference_final": jf.get("reference"),
       "reference_former": jo.get("reference"), "judge_run_sample_keys": list(sample)[:30]}
# 2026-10-31: the final run lost the soft patch on the G1-base G6 cases (weak-leg sinkage ~8 mm = uniform G1,
# g6_patch_check.py). Report the subset without those cases separately ("valid" = not '|G1+' in the key).
# A G1-base G6 run is valid when it carries the per-leg soil (re-run rows: soil_model SoilPadsPerLeg).
invalid = {k for k in rf if "|G1+" in k and rf[k].get("soil_model") != "SoilPadsPerLeg"}
out["final_files"] = [FIN_RUN, FIN_JUDGE]
out["g1_base_g6_runs"] = len([k for k in rf if "|G1+" in k])
out["g1_base_g6_per_leg_runs"] = len([k for k in rf if "|G1+" in k and k not in invalid])
g1_l2 = {k: v for k, v in vf.items() if "|G1+" in k and (v["level"] or k.split("|")[0]) == "L2"}
out["g1_base_g6_L2_verdicts"] = {"n": len(g1_l2), "fail": sum(bool(v["fails"]) for v in g1_l2.values()),
                                 "failing": [(k, v["fails"]) for k, v in g1_l2.items() if v["fails"]]}
pre_invalid = {k for k in rf if "|G1+" in k}
out["qe_final_without_g1_base"] = qe({k: v for k, v in vf.items() if k not in pre_invalid})
valid_f = {k: v for k, v in vf.items() if k not in invalid}
valid_o = {k: v for k, v in vo.items() if k not in invalid}
out["invalid_g1_base_g6_runs"] = len(invalid)
out["qe_final_valid_subset"] = qe(valid_f)
out["qe_former_valid_subset"] = qe(valid_o)
out["r4_runs_valid_subset"] = {"n": len([k for k in r4 if k not in invalid]),
                               "by_level": dict(Counter(rf[k]["level"] for k in r4 if k not in invalid)),
                               "failing": [(k, vf[k]["fails"]) for k in r4 if k not in invalid and vf.get(k, {}).get("fails")]}
out["hash_changed_valid_subset"] = len([k for k in changed if k not in invalid])
out["hash_changed_valid_not_r4"] = [k for k in changed if k not in invalid and k not in r4]
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k not in ("hash_changed", "hash_changed_not_r4")}, default=str)[:7000])
