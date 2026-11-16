"""Scope census of the 436.8 harness bundles for the 436.9 J-P3 remedy rerun estimate.

Reads identity sidecars (start / end time, affinity mask) and result lines (setting / tag counts).
Read only. Prints JSON.
"""
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1")


def parse_time(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S %z")


def identity_summary(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    starts = data.get("start") or []
    ends = data.get("end") or []
    out = {"n_start": len(starts), "n_end": len(ends)}
    if starts and ends:
        t0 = parse_time(starts[0]["time"])
        t1 = parse_time(ends[-1]["time"])
        out["wall_s"] = (t1 - t0).total_seconds()
        mask = int(starts[0].get("affinity_mask", "0x0"), 16)
        out["cores"] = bin(mask).count("1")
        out["mask"] = starts[0].get("affinity_mask")
    return out


def line_records(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def setting_of(record):
    job = record.get("job") or {}
    return job.get("setting") or record.get("setting") or record.get("v5_setting")


def tag_of(record):
    return record.get("controller_tag") or (record.get("job") or {}).get("controller_tag")


def main():
    result = {}
    for ident in sorted(ROOT.glob("*.identity.json")):
        result[ident.name] = identity_summary(ident)
    for ident in sorted((ROOT / "h9_grid").glob("*.identity.json")):
        result["h9_grid/" + ident.name] = identity_summary(ident)
    counts = {}
    for jl in sorted(ROOT.glob("*.jsonl")):
        rows = line_records(jl)
        counts[jl.name] = {"lines": len(rows),
                           "settings": dict(Counter(str(setting_of(r)) for r in rows)),
                           "tags": dict(Counter(str(tag_of(r)) for r in rows))}
    for grid in sorted((ROOT / "h9_grid").glob("grid_*.json")):
        if grid.name.endswith(".identity.json"):
            continue
        data = json.loads(grid.read_text(encoding="utf-8"))
        res = data.get("results") or []
        runs = sum(len(r.get("runs") or []) for r in res)
        tags = Counter()
        for r in res:
            for run in r.get("runs") or []:
                tags[str(run.get("controller_tag") or r.get("controller_tag"))] += 1
        counts["h9_grid/" + grid.name] = {"results": len(res), "runs": runs, "tags": dict(tags)}
    for name in ("h6_dg3_v4on.json", "h7_dg3_off.json", "h8_noise_VB.json", "h8_seedext_VB.json",
                 "h9_family_F_VB.json"):
        path = ROOT / name
        data = json.loads(path.read_text(encoding="utf-8"))
        keys = list(data)[:12] if isinstance(data, dict) else type(data).__name__
        counts[name] = {"top_keys": keys}
    json.dump({"identity": result, "counts": counts}, sys.stdout, indent=1, default=str)


if __name__ == "__main__":
    main()
