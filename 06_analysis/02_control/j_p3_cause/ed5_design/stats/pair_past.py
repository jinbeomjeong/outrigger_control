"""Past same-seed setting pairs (pre-edition-4a stored results) as empirical
models of how a controller change perturbs READY / FAULT per pair.

Pairs: H-7 (Dg-3 off) vs H-6 (v4 on) on the 135 Dg-3 keys; h8_noise V0 vs VB;
h8_seedext V0 vs VB. Reads only these stored files.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\resume_k1")
S = Path(sys.argv[1])


def strip_key(k):
    return k.split("#", 1)[1] if "#" in k else k


def load(name):
    data = json.loads((ROOT / name).read_text(encoding="utf-8"))
    rows = {}
    for r in data["results"]:
        b = r.get("base") or {}
        t = b.get("t_ready_s")
        if t is None:
            t = b.get("t_ready")
        rows[strip_key(r["key"])] = {
            "t": t,
            "phase": b.get("final_phase"),
            "cmd": r.get("commands_sha256"),
            "pass": b.get("pass"),
            "err": r.get("error"),
            "level": r.get("level"),
        }
    meta = {k: v for k, v in data["meta"].items() if isinstance(v, (str, int, float, bool))}
    return rows, meta


def compare(a_name, b_name, label):
    a, ma = load(a_name)
    b, mb = load(b_name)
    keys = sorted(set(a) & set(b))
    rec = []
    for k in keys:
        x, y = a[k], b[k]
        same = x["cmd"] is not None and x["cmd"] == y["cmd"]
        case = "|".join([k.split("|")[0]] + k.split("|")[2:])
        rec.append(
            {
                "key": k,
                "case": case,
                "level": x["level"],
                "same_cmd": same,
                "ta": x["t"],
                "tb": y["t"],
                "pa": x["phase"],
                "pb": y["phase"],
            }
        )
    d = pd.DataFrame(rec)
    res = {"label": label, "a": a_name, "b": b_name, "n_pairs": len(d)}
    res["meta_a"] = {k: ma[k] for k in ("purpose", "set", "seeds", "excluded", "levels") if k in ma}
    res["meta_b"] = {k: mb[k] for k in ("purpose", "set", "seeds", "excluded", "levels") if k in mb}
    res["same_cmd"] = int(d.same_cmd.sum())
    for direction, (base, new) in {"a_base": ("ta", "tb"), "b_base": ("tb", "ta")}.items():
        base_ready = d[base].notna()
        new_missing = d[new].isna()
        late = (d[new] - d[base]) > 30.0
        fail = base_ready & (new_missing | late)
        dd = {
            "base_ready": int(base_ready.sum()),
            "fail_missing": int((base_ready & new_missing).sum()),
            "fail_late30": int((base_ready & ~new_missing & late).sum()),
            "fail_total": int(fail.sum()),
            "fail_among_changed_cmd": int((fail & ~d.same_cmd).sum()),
            "changed_cmd": int((~d.same_cmd).sum()),
            "fail_cases": int(d[fail].case.nunique()),
        }
        diff = (d[new] - d[base])[base_ready & ~new_missing & ~d.same_cmd]
        if len(diff):
            dd["ready_diff_changed_q"] = {
                q: float(np.quantile(diff, q)) for q in (0.01, 0.05, 0.5, 0.95, 0.99)
            }
            dd["ready_diff_changed_sd"] = float(np.std(diff, ddof=1))
        res[direction] = dd
    by_level = d.groupby("level").agg(n=("key", "size"), same=("same_cmd", "sum")).to_dict("index")
    res["by_level_same_cmd"] = {k: {kk: int(vv) for kk, vv in v.items()} for k, v in by_level.items()}
    d.to_csv(S / f"pairs_{label}.csv", index=False)
    return res


out = [
    compare("h7_dg3_off.json", "h6_dg3_v4on.json", "dg3_off_vs_on"),
    compare("h8_noise_V0.json", "h8_noise_VB.json", "noise_V0_vs_VB"),
    compare("h8_seedext_V0.json", "h8_seedext_VB.json", "seedext_V0_vs_VB"),
]
(S / "pair_past.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print("ok")
