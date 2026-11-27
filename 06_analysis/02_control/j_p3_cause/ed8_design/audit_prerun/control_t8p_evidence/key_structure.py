"""Key-structure probe for the edition 8 T8' decisions (no judged values printed).

Prints: field names, setting / arm labels and counts of the three probe raw files, the census
unit key overlap (setting-aware and setting-blind), and the held-out V0 job uniqueness.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design")
RAW = {
    "P8-9": D / "control_early_handover/probe_8a2a52ce/raw/runs.jsonl",
    "P8-9p": D / "control_early_handover/probe_8a2a52ce/h3p/raw/runs.jsonl",
    "P8-14": D / "control_level_deadlock/probe_8a2a52ce/raw/runs.jsonl",
}
CENSUS = D / "keys_seal_41e107e9/census_keys_ed8.json"
HELDOUT = D / "keys_seal_41e107e9/heldout_g_ed8.json"
IGNORED = ("setting", "mask", "t4h_dir")
JOB_FIELDS_SEEN = Counter()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plain(job):
    return json.dumps({k: v for k, v in job.items() if k not in IGNORED}, sort_keys=True)


def map_setting(name):
    if name is None:
        return None
    name = name.split("-")[-1]  # probe arm prefix (P89-H3-, P814-L2-, ...)
    if name.startswith("VBM"):
        return "VBN" + name[3:]
    if name.startswith("LSM"):
        return "LSN" + name[3:]
    return name


out = {"sha256": {}, "raw": {}, "census": {}, "overlap": {}, "heldout": {}}
for name, path in RAW.items():
    out["sha256"][name] = sha(path)
    tops, jobs_fields, settings, arms, n = Counter(), Counter(), Counter(), Counter(), 0
    keyed = []
    for text in path.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        n += 1
        row = json.loads(text)
        tops.update(row.keys())
        job = row.get("job")
        if isinstance(job, dict):
            jobs_fields.update(job.keys())
            settings[str(job.get("setting"))] += 1
            keyed.append(job)
        for label in ("arm", "cand", "candidate", "variant"):
            if label in row and isinstance(row[label], (str, int)):
                arms[f"{label}={row[label]}"] += 1
    distinct_plain = {plain(j) for j in keyed if "r79_key" not in j}
    distinct_full = {(map_setting(j.get("setting")), plain(j)) for j in keyed
                     if "r79_key" not in j}
    out["raw"][name] = {"lines": n, "top_fields": sorted(tops), "job_fields": dict(jobs_fields),
                        "settings": dict(settings), "arm_labels": dict(arms),
                        "distinct_run_v5_jobs_plain": len(distinct_plain),
                        "distinct_run_v5_jobs_mapped_setting": len(distinct_full),
                        "r79_jobs": sum("r79_key" in j for j in keyed)}
    out["raw"][name]["_sets"] = (distinct_plain, distinct_full)

census = json.loads(CENSUS.read_text(encoding="utf-8"))
out["sha256"]["census"] = sha(CENSUS)
units = []
stage_roles = Counter()
for line in census["lines"]:
    job, stage = line["job"], line["stage"]
    stage_roles[(stage, job.get("setting"), line.get("role"))] += 1
    is_unit = ((stage == "C-J" and job["setting"] == "VBN")
               or (stage == "C-S" and line.get("role") == "judged_vs_V0")
               or (stage == "C-D" and job["setting"] == "VBN")
               or stage == "C-G")
    if is_unit:
        units.append((stage, job["setting"], plain(job)))
out["census"]["line_fields"] = sorted({k for line in census["lines"] for k in line})
out["census"]["stage_setting_role"] = {f"{a}|{b}|{c}": v for (a, b, c), v in
                                       sorted(stage_roles.items(), key=str)}
out["census"]["units"] = len(units)
out["census"]["units_by_stage"] = dict(Counter(s for s, _, _ in units))
census_all = [(line["stage"], line["job"]["setting"], plain(line["job"]))
              for line in census["lines"]]
SETS = {name: out["raw"][name].pop("_sets") for name in RAW}
for name in RAW:
    plain_set, full_set = SETS[name]
    blind = Counter(s for s, _, p in units if p in plain_set)
    aware = Counter(s for s, st, p in units if (st, p) in full_set)
    lines_aware = Counter(f"{s}|{st}" for s, st, p in census_all if (st, p) in full_set)
    unmatched = sum(1 for st, p in full_set
                    if not any(st == cst and p == cp for _, cst, cp in census_all))
    out["overlap"][name] = {"units_setting_blind": dict(blind), "units_setting_aware": dict(aware),
                            "census_lines_setting_aware": dict(lines_aware),
                            "raw_jobs_not_in_census_lines": unmatched}
union_full = set().union(*(SETS[n][1] for n in RAW))
out["overlap"]["union"] = {
    "distinct_mapped_jobs": len(union_full),
    "units_setting_aware": dict(Counter(s for s, st, p in units if (st, p) in union_full)),
    "units_setting_blind": dict(Counter(s for s, _, p in units
                                        if p in {q for _, q in union_full}))}

held = json.loads(HELDOUT.read_text(encoding="utf-8"))
out["sha256"]["heldout"] = sha(HELDOUT)
lens = Counter(len(line["aa_order"]) for line in held["lines"])
v0_batch = [line["v0_pair"]["job"] for line in held["lines"]] + \
           [line["aa_order"][0] for line in held["lines"]]
aa2 = [line["aa_order"][1] for line in held["lines"]]
aa3 = [line["aa_order"][2] for line in held["lines"]]
key = lambda j: json.dumps({k: v for k, v in j.items() if k not in ("mask", "t4h_dir")},  # noqa: E731
                           sort_keys=True)
all_jobs = v0_batch + aa2 + aa3
out["heldout"] = {"lines": len(held["lines"]), "aa_order_lengths": dict(lens),
                  "v0_pair_settings": dict(Counter(line["v0_pair"]["job"].get("setting")
                                                   for line in held["lines"])),
                  "aa_settings": dict(Counter(j.get("setting") for j in all_jobs)),
                  "slot_job_settings": dict(Counter(line["job"].get("setting")
                                                    for line in held["lines"])),
                  "v0_batch_jobs": len(v0_batch), "v0_batch_unique": len({key(j) for j in v0_batch}),
                  "aa2_unique": len({key(j) for j in aa2}), "aa3_unique": len({key(j) for j in aa3}),
                  "all_1356_unique": len({key(j) for j in all_jobs}),
                  "line_fields": sorted({k for line in held["lines"] for k in line}),
                  "v0_pair_fields": sorted({k for line in held["lines"] for k in line["v0_pair"]})}
json.dump(out, sys.stdout, indent=1, default=str)
print()
