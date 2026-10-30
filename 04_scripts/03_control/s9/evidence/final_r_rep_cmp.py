"""FINAL-R-REP (spec 432.6.2): compare each final-controller rigid row (S8 L2b / S6 L1-R) with its source run.

Per row: controller settings recorded in result.json (SGS soil_stop / scope, R4 flat_soil_margin), final-feature
events (WARN_LIFT_STROKE_LIMITED, FAULT_LIFT_STROKE_LIMIT, INFO_LOC_FLAT_SOIL_MARGIN, INFO_LOC_CLEARANCE_MARGIN,
INFO_LOC_REVOKED, INFO_DIFF_SINK_*), event-list difference, and array-by-array equality of r8_series.npz (the
10 Hz controller series incl. valve commands) between the two runs.

Usage: python -I final_r_rep_cmp.py <repo root> <out json>
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1])
BATCH = ROOT / "07_results/S9/batch_FINAL-R-REP_20261030_223425"
FEAT = ("WARN_LIFT_STROKE_LIMITED", "FAULT_LIFT_STROKE_LIMIT", "FLAT_SOIL_MARGIN", "LOC_CLEARANCE_MARGIN",
        "LOC_REVOKED", "DIFF_SINK", "soil_stop", "LOC_WINDOW_RESTART", "LIFT_PAUSED")


def new_folders():
    out = {}
    for line in (BATCH / "progress.log").read_text(encoding="utf-8").splitlines():
        if line.startswith("END "):
            case = line.split()[1]
            m = re.search(r"(C:\\\S+)$", line)
            out[case] = Path(m.group(1)) / case if m else None
    for p in (ROOT / "07_results/S6").glob("bundleC_g8c76_p28acc_final_*"):
        for c in p.iterdir():
            if c.is_dir() and (c / "result.json").exists():
                out[c.name] = c
    return out


def events(folder):
    f = folder / "controller_events.json"
    if not f.exists():
        return []
    return [re.sub(r"^C2Event\(t_s=([0-9.e+-]+), name='(.*)'\)$", r"\1 \2", e) for e in
            json.loads(f.read_text(encoding="utf-8"))]


def find(d, key, path=""):
    """Yield (path, value) for every dict key == key."""
    if isinstance(d, dict):
        for k, v in d.items():
            p = f"{path}.{k}"
            if k == key:
                yield p, v
            yield from find(v, key, p)
    elif isinstance(d, list):
        for i, v in enumerate(d[:50]):
            yield from find(v, key, f"{path}[{i}]")


def npz_cmp(a, b):
    if not (a.exists() and b.exists()):
        return {"status": "missing", "new": a.exists(), "old": b.exists()}
    x, y = np.load(a, allow_pickle=False), np.load(b, allow_pickle=False)
    common = sorted(set(x.files) & set(y.files))
    diff = {}
    for k in common:
        u, v = x[k], y[k]
        if u.shape != v.shape:
            diff[k] = f"shape {u.shape} vs {v.shape}"
        elif u.dtype.kind in "fc" and not np.array_equal(u, v, equal_nan=True):
            diff[k] = float(np.nanmax(np.abs(u.astype(float) - v.astype(float))))
        elif u.dtype.kind not in "fc" and not np.array_equal(u, v):
            diff[k] = "differs"
    return {"status": "identical" if not diff and set(x.files) == set(y.files) else "differs",
            "n_common": len(common), "only_new": sorted(set(x.files) - set(y.files)),
            "only_old": sorted(set(y.files) - set(x.files)), "diff": dict(list(diff.items())[:12])}


rows = json.loads((BATCH / "batch.json").read_text(encoding="utf-8"))["cases"]
nf = new_folders()
out = []
for r in rows:
    case = r["case"]
    new = nf.get(case)
    old = ROOT / r["source_run"]
    res = json.loads((new / "result.json").read_text(encoding="utf-8")) if new and (new / "result.json").exists() \
        else {}
    settings = {}
    for key in ("soil_stop", "soil_stop_scope", "flat_soil_margin_m"):
        settings[key] = [v for _, v in find(res, key)][:2]
    en, eo = events(new) if new else [], events(old)
    names_n = [e.split(" ", 1)[1] for e in en]
    names_o = [e.split(" ", 1)[1] for e in eo]
    out.append({
        "case": case, "variable": r.get("rep_variable"), "new": str(new.relative_to(ROOT)) if new else None,
        "old": r["source_run"], "settings_new": settings,
        "final_feature_events_new": [e for e in en if any(t in e for t in FEAT)],
        "final_feature_events_old": [e for e in eo if any(t in e for t in FEAT)],
        "events_same_names": names_n == names_o, "events_same_full": en == eo,
        "events_only_new": [n for n in names_n if n not in names_o][:10],
        "events_only_old": [n for n in names_o if n not in names_n][:10],
        "r8_series": npz_cmp(new / "r8_series.npz", old / "r8_series.npz") if new else None,
        "result_keys": list(res)[:40],
    })
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
for o in out:
    s = o["r8_series"] or {}
    print(f"{o['case']:28s} {o['variable']} r8={s.get('status')} ndiff={len(s.get('diff', {}))} "
          f"ev_same={o['events_same_full']}/{o['events_same_names']} feat_new={o['final_feature_events_new'][:3]} "
          f"set={o['settings_new']} +{o['events_only_new'][:3]} -{o['events_only_old'][:3]}")
print("RESULT KEYS", out[0]["result_keys"])
print("DIFF SAMPLE", [(o["case"], o["r8_series"]["diff"]) for o in out if o["r8_series"] and o["r8_series"]["diff"]][:3])
