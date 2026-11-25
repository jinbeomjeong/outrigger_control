"""Print the parts of s04_result.json needed for the report."""
import collections
import json
import statistics
import sys

result = json.loads(open(sys.argv[1], encoding="utf-8").read())

print("== clear rows (plant, arm, part, key, count, log_rows, truncated, final_phase, class)")
for r in result["clear_rows"]:
    print(" ", r["plant"], r["arm"], r["part"], r["key"], r["count"], r["log_rows"], r["truncated"],
          r["final_phase"], r["harness_class"])

print("== clear counts by plant|arm|part: [rows, rows with clear, clears]")
per_plant = collections.defaultdict(lambda: [0, 0, 0])
for k, v in result["clear_counts_by"].items():
    print(" ", k, v)
    plant = k.split("|")[0]
    for i in range(3):
        per_plant[plant][i] += v[i]
print("== per plant", dict(per_plant))

print("== clear events")
cleared = []
for e in result["clear_events"]:
    cleared.append(e["cleared_bar"])
    keys = ("plant", "arm", "part", "key", "leg", "t_clear", "cleared_bar", "t_release", "window_s",
            "fill_release_row_at_release", "seed_row_at_release", "extend_open_at_release",
            "retract_fill_between", "release_kind", "valve_after_mm_s", "cmd_before_mm_s",
            "rod_read_before_bar", "rod_read_after_bar", "read_after_t", "read_after_locked",
            "lock_log", "status")
    print("  " + json.dumps({k: e.get(k) for k in keys}, ensure_ascii=False))
if cleared:
    cleared.sort()
    print("cleared bar: n", len(cleared), "min", cleared[0], "median", statistics.median(cleared),
          "max", cleared[-1])
    print("sorted:", cleared)
print("== status counts", collections.Counter(e["status"] for e in result["clear_events"]))
print("== release kinds of clear events", collections.Counter(e.get("release_kind") for e in result["clear_events"]))

print("== fill release kinds", result["fill_release_kinds"])
print("== seed count mismatches", result["seed_count_mismatch"][:5])
print("== caps", result["caps"])
ext_cap = collections.Counter((r["plant"], r["arm"]) for r in result["cap_rows"] if r["ext_starts_at_cap"])
print("== ext_starts at cap by plant/arm", dict(ext_cap))
print("== void episodes")
for e in result["void_episodes"]:
    print("  " + json.dumps({k: e.get(k) for k in ("plant", "arm", "part", "key", "leg", "t_start",
                                                   "t_end", "reads", "x_mm_min", "x_mm_max", "need_mm",
                                                   "drain_mm_s", "rod_read_bar_max", "t_lock",
                                                   "t_next_release", "rise_evidence")}))
print("== L stale summary")
tot = [0, 0]
for e in result["l_stale"]:
    s = e["stale"]
    tot[0] += s["releases_with_seed"]
    tot[1] += s["stale_releases"]
    if s["stale_releases"]:
        print("  ", e["arm"], e["key"], s, "seed_count", e["p1_retract_seed_count"],
              "seed-locked bar", e.get("stale_log_seed_minus_locked_bar"))
print("  totals releases_with_seed, stale:", tot)
dist = collections.Counter((e["stale"]["releases_with_seed"], e["stale"]["stale_releases"]) for e in result["l_stale"])
print("  (releases, stale) distribution:", sorted(dist.items()))
trunc = sum(1 for e in result["l_stale"] if e["stale"]["log_truncated"])
print("  log_truncated rows:", trunc, "anomalies:", len(result["l_anomalies"]))
