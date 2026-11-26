"""Tables from the u01 scans: U832 failures, pair union by offset, and alias groups.

Usage: python -I -B u02_tables.py <folder>   (reads u01_scan_ed6.csv / u01_scan_ed7.csv there)
Writes u02_*.csv and prints ASCII summaries.
"""
import sys
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 400)

folder = Path(sys.argv[1])
d7 = pd.read_csv(folder / "u01_scan_ed7.csv")
d6 = pd.read_csv(folder / "u01_scan_ed6.csv")
d6["ed"], d7["ed"] = 6, 7
d = pd.concat([d6, d7], ignore_index=True)
d["fails_u832"] = d["failed_gates"].fillna("").str.contains("U832_pair_union")

ev = d[d["event"].notna()].copy()
print("== event rows per src/setting ==")
print(ev.groupby(["ed", "src", "setting"]).size())

print("\n== U832_pair_union failures ==")
cols = ["ed", "src", "setting", "level", "leg", "fs_kN", "event", "timing", "offset_s", "pair",
        "pair_union_s", "pair_last_touch_s", "failed_gates", "t_event_s"]
fails = ev[ev["fails_u832"]][cols]
print(fails.to_string())
fails.to_csv(folder / "u02_u832_failures.csv", index=False)

print("\n== all failures by offset (event rows) ==")
ev["fail"] = ev["pass"] == False  # noqa: E712
print(pd.crosstab([ev["ed"], ev["src"]], [ev["offset_s"], ev["fail"]]))
print("\n== U832_pair_union fails / lines by (ed, src, level, event, timing) x offset ==")
fast = ev[ev["event"].isin(["RE1bF", "FS24"])]
tab = fast.groupby(["ed", "src", "level", "event", "timing", "offset_s"]).agg(
    lines=("fails_u832", "size"), u832=("fails_u832", "sum"), pu_mean=("pair_union_s", "mean"),
    pu_max=("pair_union_s", "max"), pu_min=("pair_union_s", "min"))
print(tab.to_string())
tab.to_csv(folder / "u02_u832_by_offset.csv")

print("\n== failed gate names, offset 0.0 vs other ==")
ev["o0"] = ev["offset_s"] == 0.0
fg = ev[ev["fail"]].assign(g=ev["failed_gates"].str.split("|")).explode("g").reset_index(drop=True)
print(pd.crosstab([fg["ed"], fg["g"]], fg["o0"]))

# pair union by offset, RE1bF ready, per (ed, setting, level, leg, fs)
sub = ev[(ev["event"] == "RE1bF") & (ev["timing"] == "ready")]
piv = sub.pivot_table(index=["ed", "setting", "level", "leg", "fs_kN"], columns="offset_s",
                      values="pair_union_s", aggfunc="first")
print("\n== pair_union_s, RE1bF ready, by offset ==")
print(piv.to_string())
piv.to_csv(folder / "u02_pair_union_RE1bF_ready.csv")

sub2 = ev[(ev["event"] == "RE1bF")]
print("\n== pair_union_s summary by event/timing/level/offset (mean, max) ==")
print(ev.groupby(["ed", "event", "timing", "level", "offset_s"])["pair_union_s"].agg(["count", "mean", "max"]).to_string())

# alias: same commands_sha256 inside one (ed, src, setting, case, level, leg, fs, event, timing)
key = ["ed", "src", "setting", "case", "level", "leg", "fs_kN", "event", "timing"]
grp = ev.groupby(key, dropna=False)
al = grp.agg(n=("commands_sha256", "size"), n_sha=("commands_sha256", "nunique"),
             offsets=("offset_s", lambda s: ",".join(f"{x:g}" for x in sorted(s))))
print("\n== event clusters: lines vs unique command hashes ==")
print(al["n"].sum(), "lines", al["n_sha"].sum(), "unique within cluster;",
      int((al["n"] > al["n_sha"]).sum()), "clusters with a repeated hash")
al.to_csv(folder / "u02_event_alias.csv")

# bit aliases across distinct jobs: the same commands_sha256 on lines whose job identity differs
ok = d[d["error"].isna() & d["commands_sha256"].notna()].copy()
ok["job_id"] = ok[["setting", "case", "level", "leg", "fs_kN", "event", "timing", "offset_s", "eps"]] \
    .astype("object").astype(str).apply(lambda r: "|".join(map(str, r)), axis=1)
dup = ok.groupby("commands_sha256").filter(lambda g: g["job_id"].nunique() > 1)
same_job = ok.groupby("commands_sha256").filter(lambda g: len(g) > 1 and g["job_id"].nunique() == 1)
print("\n== identical commands_sha256 on different job identities (bit alias) ==")
print(dup.sort_values("commands_sha256")[["ed", "src", "setting", "case", "level", "leg", "fs_kN",
                                          "event", "offset_s", "eps", "commands_sha256"]].to_string())
print("repeated identical jobs (same identity, same hash):", len(same_job), "lines in",
      same_job["commands_sha256"].nunique(), "groups;", "sources",
      same_job.groupby("src").size().to_dict())
dup.to_csv(folder / "u02_bit_alias_distinct_jobs.csv", index=False)

