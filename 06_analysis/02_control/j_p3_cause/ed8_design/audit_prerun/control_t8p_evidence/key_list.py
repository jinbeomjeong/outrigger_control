"""List the selection-used key candidates (job identity only, no judged values)."""
import json
from collections import defaultdict
from pathlib import Path

D = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design")
RAW = {
    "P8-9": D / "control_early_handover/probe_8a2a52ce/raw/runs.jsonl",
    "P8-9p": D / "control_early_handover/probe_8a2a52ce/h3p/raw/runs.jsonl",
    "P8-14": D / "control_level_deadlock/probe_8a2a52ce/raw/runs.jsonl",
}
CENSUS = D / "keys_seal_41e107e9/census_keys_ed8.json"
IGNORED = ("setting", "mask", "t4h_dir")


def plain(job):
    return json.dumps({k: v for k, v in job.items() if k not in IGNORED}, sort_keys=True)


def plant(name):
    name = name.split("-")[-1]
    for old, new in (("VBM", "VBN"), ("LSM", "LSN")):
        if name.startswith(old):
            return new + name[len(old):]
    return name


def short(job):
    twin = job.get("twin") or {}
    tw = "|".join(str(twin.get(k)) for k in ("level", "leg", "fs_kN", "event", "timing")
                  if k in twin)
    return f"{job.get('case')} eps{job.get('eps')} o{job.get('offset_s')} {tw}"


sources = defaultdict(set)
arms = defaultdict(set)
jobs = {}
for name, path in RAW.items():
    for text in path.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        row = json.loads(text)
        job = row.get("job")
        if not isinstance(job, dict):
            continue
        key = (plant(job["setting"]), plain(job))
        sources[key].add(name)
        arms[key].add(job["setting"].rsplit("-", 1)[0])
        jobs[key] = job

census = json.loads(CENSUS.read_text(encoding="utf-8"))
where = defaultdict(list)
for line in census["lines"]:
    where[(line["job"]["setting"], plain(line["job"]))].append(
        f"{line['stage']}:{line.get('role')}")
for key in sorted(jobs, key=lambda k: (k[0], short(jobs[k]))):
    print(f"{key[0]:8s} {short(jobs[key]):60s} src={sorted(sources[key])} "
          f"arms={sorted(arms[key])} census={where.get(key, ['-'])}")
