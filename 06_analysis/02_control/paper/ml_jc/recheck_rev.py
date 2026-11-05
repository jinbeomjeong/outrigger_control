"""Independent recount of the paper-reviewer figures from the replay JSON and the stored ML records (read only)."""
import json
import os
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import beta, binomtest, fisher_exact

ROOT = r"C:\workspace\outrigger_control"
D = Path(ROOT) / r"06_analysis\02_control\paper\ml_jc"
ML = Path(ROOT) / r"07_results\S8\ml_main_20261025_090131"
h = json.load(open(D / "ml_jc_head.json", encoding="utf-8"))
det = json.load(open(D / "ml_jc_missed_detail.json", encoding="utf-8"))
SETS = ("train", "validation", "test", "OOD-1", "OOD-2", "MLJ")
FMIN = 9.41458911
runs = [(s, it) for s in SETS for it in h[s]]
print("F_min meta values", Counter(round(it["meta"]["F_min_N"], 3) for _, it in runs))
rows = [(s, it["meta"], r) for s, it in runs for r in it["rows"] if r["scope"] == "scored"]
print("n", len(rows))

# 1. Cross table, boundary sensitivity and decision source.
for fm in (FMIN, 9.4146, 9.0, 10.0):
    tab = Counter()
    for _, _, r in rows:
        k = "under" if r["true_at_samples_min_kN"] < fm else "between"
        tab[k, "n"] += 1
        tab[k, "jc"] += r["JC_first_decision_s"] is None
        tab[k, "jp"] += r["JP_first_decision_s"] is None
        tab[k, "both"] += r["JC_first_decision_s"] is None and r["JP_first_decision_s"] is None
        tab[k, "jp_only"] += r["JC_first_decision_s"] is not None and r["JP_first_decision_s"] is None
        tab[k, "jc_only"] += r["JC_first_decision_s"] is None and r["JP_first_decision_s"] is not None
    print("Fmin", fm, dict(sorted(tab.items())))
und_jp = [r for _, _, r in rows if r["true_at_samples_min_kN"] < FMIN and r["JP_first_decision_s"] is None]
print("under & JP miss: true at sample range", round(min(r["true_at_samples_min_kN"] for r in und_jp), 2), round(max(r["true_at_samples_min_kN"] for r in und_jp), 2),
      "lift flags", sum(r["is_lift"] for r in und_jp), "samples", sorted(Counter(r["samples"] for r in und_jp).items()), "band", round(st.median(r["band_on_kN"] for r in und_jp), 2))
jc_caught = [r for _, _, r in rows if r["JC_first_decision_s"] is not None]
print("caught where the estimate stays >= F_min (mark only)", sum((r["est_minus_Fmin_min_kN"] is not None and r["est_minus_Fmin_min_kN"] >= 0) for r in jc_caught), "of", len(jc_caught))
print("set split between", Counter(s for s, _, r in rows if r["true_at_samples_min_kN"] >= FMIN))

# 2. Force values of the 44.
miss = [(s, m, r) for s, m, r in rows if r["JC_first_decision_s"] is None]
tm = sorted(r["true_min_kN"] for _, _, r in miss)
print("true_min(record window min): min", round(tm[0], 2), "median", round(st.median(tm), 2), "<=0", sum(x <= 0 for x in tm), "max", round(tm[-1], 2))
key = {(o["set"], o["run"], o["leg"], o["t_on"]): o for o in det}
pad = []
for s, m, r in miss:
    o = key[(s, r["run"], r["leg"], round(r["t_on_s"], 1))]
    pad.append((r["true_min_kN"], o["min_window_kN"], r["is_lift"], o["air_ms"], o["N_le0_ms"], r["run"], r["leg"], o["under_ms"], r["samples"], s))
wm = sorted(x[1] for x in pad)
print("pads F_cyl sampled window min: min", wm[0], "median", st.median(wm), "<=0", sum(x <= 0 for x in wm))
print("diff record - pads: max abs", round(max(abs(a[0] - a[1]) for a in pad), 2), "record lower count", sum(a[0] < a[1] for a in pad))
print("lowest", sorted(pad)[:3])
print("<=0 not lift", [(round(a[0], 2), a[5], a[6]) for a in pad if a[0] <= 0 and not a[2]])
print("lift no air", [(round(a[0], 2), a[5], a[6], a[3]) for a in pad if a[2] and a[3] == 0], "air no lift", [(a[5], a[3]) for a in pad if not a[2] and a[3] > 0])
print("categories", Counter((a[0] <= 0, a[2], a[3] > 0) for a in pad))
rod = Counter()
for s, m, r in miss:
    pass
p0 = np.load(ML / "ml_dataset" / "ML38_ep1.npz", allow_pickle=False)
print("meta keys rod weight", json.loads(str(p0["meta_json"])).get("rod_weight_N") if "meta_json" in p0.files else p0.files[:6])

# 3. The two-window episodes.
for s, m, r in miss:
    if r["samples"] > 1:
        src = m["source"]
        folder = src if os.path.isabs(src) else os.path.join(ROOT, src)
        pads = np.load(os.path.join(folder, "pads.npz"), allow_pickle=False)
        ep = np.load(ML / "ml_dataset" / f"{r['run']}.npz", allow_pickle=False)
        i = ("FL", "FR", "RL", "RR").index(r["leg"])
        k = int(np.argmin(np.abs(ep["t_s"] - r["t_on_s"])))
        print(r["run"], r["leg"], "windows", [(round(float(ep["t_s"][j]), 1), round(float(ep["true_force_min_N"][j, i]) / 1e3, 2), round(float(ep["true_force_N"][j, i]) / 1e3, 2), round(float(ep["lower_reading_N"][j, i]) / 1e3, 2), round(float(ep["seal_band_N"][j, i]) / 1e3, 2)) for j in range(k - 1, k + r["samples"] + 1)])
        t = pads["t"]
        w = (t > r["t_on_s"] - 0.1) & (t <= r["t_on_s"] + (r["samples"] - 1) * 0.1 + 1e-9)
        f = pads["F_cyl"][w, i] / 1e3
        u = f < FMIN
        edges = np.flatnonzero(np.diff(u.astype(int)))
        print("   dips relative to t_on [ms]", [round(float((t[w][e + 1] - r["t_on_s"]) * 1e3)) for e in edges], "fixed sample F at samples", [round(float(np.interp(r["t_on_s"] + q * 0.1, t, pads["F_cyl"][:, i])) / 1e3, 2) for q in range(r["samples"])], "sample_every_ms", round(float(np.median(np.diff(t))) * 1e3, 2))

# 4. Later behaviour.
by_run = defaultdict(list)
for s, m, r in rows:
    by_run[r["run"]].append(r)
later = Counter()
later_rows = []
for s, m, r in miss:
    same = [x for x in by_run[r["run"]] if x["leg"] == r["leg"] and x["t_on_s"] > r["t_on_s"]]
    if not same:
        later["no later same-leg episode"] += 1
        continue
    nxt = min(same, key=lambda x: x["t_on_s"])
    caught = nxt["JC_first_decision_s"] is not None
    later["next same-leg caught" if caught else "next same-leg missed"] += 1
    later["all later caught" if all(x["JC_first_decision_s"] is not None for x in same) else "some later missed"] += 1
    later_rows.append((r["run"], r["leg"], round(nxt["t_on_s"] - r["t_on_s"], 1), caught, nxt["is_lift"], round(nxt["true_at_samples_min_kN"], 1)))
print(dict(later))
print("later rows", later_rows)
other = Counter()
for s, m, r in miss:
    oth = [x for x in by_run[r["run"]] if x is not r]
    other["other episodes in run" if oth else "no other"] += 1
    other["other caught"] += sum(x["JC_first_decision_s"] is not None for x in oth)
    other["other n"] += len(oth)
print(dict(other))


def end_of(s, run):
    folder = ML / ("ml_dataset_mlj" if s == "MLJ" else "ml_dataset")
    ep = np.load(folder / f"{run}.npz", allow_pickle=False)
    p = ep["phase"]
    return str(p[-1]), float(ep["t_s"][-1]), ep


ends = defaultdict(Counter)
for s, it in runs:
    run = str(it["meta"]["episode_id"])
    if "_ep" not in run:
        continue
    scored = [r for r in it["rows"] if r["scope"] == "scored"]
    cat = "no episode" if not scored else ("some J_C miss" if any(r["JC_first_decision_s"] is None for r in scored) else "episodes, none missed")
    ends[cat][end_of(s, run)[0]] += 1
for k, c in ends.items():
    print("end phase by run class", k, sum(c.values()), dict(c))
a, b = ends["some J_C miss"], ends["episodes, none missed"]
tbl = [[sum(a.values()) - a["ready"], a["ready"]], [sum(b.values()) - b["ready"], b["ready"]]]
print("non-READY end vs READY end, Fisher", tbl, fisher_exact(tbl))
print("miss-row end phases (per interval)", Counter(o["end_phase"] for o in det), "runs", len({o["run"] for o in det}))
for o in det:
    if o["end_phase"] != "ready":
        _, tend, ep = end_of(o["set"], o["run"])
        p, t = ep["phase"], ep["t_s"]
        ch = [(round(float(t[i]), 1), str(p[i])) for i in range(len(t)) if i == 0 or p[i] != p[i - 1]]
        print(o["set"], o["run"], o["leg"], "t_on", o["t_on"], "ev_leg", o["ev_leg"], "Fs", o["Fs_kN"], "grade", o["grade"], o["zc"], "end_t", round(tend, 1), "phases", ch)
        src = [it for s, it in runs if str(it["meta"]["episode_id"]) == o["run"]][0]["meta"]["source"]
        folder = src if os.path.isabs(src) else os.path.join(ROOT, src)
        ev = json.load(open(os.path.join(folder, "controller_events.json"), encoding="utf-8"))
        print("    n events", len(ev), "tail", [str(x)[:80] for x in ev[-6:]])
masks = json.load(open(ML / "verify_S8ML.json", encoding="utf-8")).get("ml_masks", {})
print("masks for fault run", masks.get("ML63_ep2"), "n masks", len(masks))
print("all runs ending in fault", [str(it["meta"]["episode_id"]) for s, it in runs if "_ep" in str(it["meta"]["episode_id"]) and end_of(s, str(it["meta"]["episode_id"]))[0] == "fault"])

# 5. Statistics.
print("sign 2 vs 0 one-sided", binomtest(2, 2, 0.5, alternative="greater").pvalue, "two-sided", binomtest(2, 2, 0.5).pvalue)
print("CP upper one-sided 44/604", beta.ppf(0.95, 45, 560), "two-sided 97.5", beta.ppf(0.975, 45, 560), "rate", 44 / 604, "J_P 106/604", beta.ppf(0.95, 107, 498), "0/522", 1 - 0.05 ** (1 / 522), "0/19", 1 - 0.05 ** (1 / 19))
disc = [(m.get("base_id") or r["run"], r["run"]) for s, m, r in rows if r["JC_first_decision_s"] is not None and r["JP_first_decision_s"] is None]
print("discordant", len(disc), "runs", len({d[1] for d in disc}), "bases", len({d[0] for d in disc}), "reverse", sum(r["JC_first_decision_s"] is None and r["JP_first_decision_s"] is not None for _, _, r in rows))
print("sign per episode p", binomtest(62, 62, 0.5, alternative="greater").pvalue, "per run", binomtest(len({d[1] for d in disc}), len({d[1] for d in disc}), 0.5, alternative="greater").pvalue, "per base", binomtest(len({d[0] for d in disc}), len({d[0] for d in disc}), 0.5, alternative="greater").pvalue)
mbase = Counter(m.get("base_id") or r["run"] for s, m, r in miss)
allbase = Counter(m.get("base_id") or r["run"] for s, m, r in rows)
print("miss bases", len(mbase), "of", len(allbase), "runs with miss", len({r["run"] for _, _, r in miss}), "of runs with episodes", len(by_run))
print("run-level CP any miss", len({r["run"] for _, _, r in miss}), len(by_run), beta.ppf(0.95, len({r["run"] for _, _, r in miss}) + 1, len(by_run) - len({r["run"] for _, _, r in miss})))
