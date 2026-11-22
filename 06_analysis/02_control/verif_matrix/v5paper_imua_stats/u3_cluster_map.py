"""U-3 key -> case cluster map for the v5 paper A-type rules (control-expert, 2026-11-22, draft for sealing).

Input: the 436.8 U-3 stored files (identifiers only: ``records[].id`` / ``results[].key`` / ``results[].id``),
``06_analysis/02_control/v5_rerun/las_k1/u3_<study>_<V0|VB>.json``. No grade field is read.

Rule (a cluster = one physical scenario; scalar knob variants of the same scenario are one cluster):
  token removed                         studies       meaning
  ``Fs<x>`` field                       h6, g6, p3b, x426b, C   seal friction F_s variant
  ``m<x>`` field (m1.1, m1.2)           h6, x426b     mass scale variant
  ``@k<x>`` suffix of the slope token   h9, x426b     slope magnitude fraction R_c of the boundary
  ``b<x>`` field                        p3b           bulk modulus variant (rigid rows)
  height field (``|<h>|proj`` -> ``|proj``) and ``ref|none|0`` kept   g8   start-height variant
  ``<LEG>:g<h>`` / ``<LEG>:d<h>`` field D            non-planar start gap / drop variant
  nothing                               slope         each key is its own scenario
The cluster id is ``<study>::<key with the tokens removed>``. The same map serves V0 and VB (equal key sets,
checked). Output CSV columns: study, key, cluster. Exit 0 = written, 1 = V0/VB key sets differ or a key matches
no rule, 2 = input missing.

Usage: python -I -B u3_cluster_map.py <out.csv> <out_summary.json>
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\v5_rerun\las_k1")
STUDIES = ("slope", "h6", "h9", "g6", "g8", "p3b", "x426b", "C", "D")
EXPECTED = {"slope": 110, "h6": 26, "h9": 24, "g6": 116, "g8": 516, "p3b": 171, "x426b": 84, "C": 34, "D": 33}
FS = re.compile(r"^Fs\d+(\.\d+)?$")
MASS = re.compile(r"^m\d+(\.\d+)?$")
BETA = re.compile(r"^b\d+(\.\d+)?$")
PATCH = re.compile(r"^(FL|FR|RL|RR):[gd]\d+(\.\d+)?$")
KFRAC = re.compile(r"@k\d+(\.\d+)?$")
G8 = re.compile(r"^(?P<head>.+\|(?:FL|FR|RL|RR)\|(?:raised|lowered))\|\d+(\.\d+)?\|(?P<tail>proj.*)$")


def keys_of(path: Path) -> list[str]:
    d = json.load(open(path, encoding="utf-8"))
    out = [str(r["id"]) for r in d.get("records", []) or [] if isinstance(r, dict) and "id" in r]
    for r in d.get("results", []) or []:
        if isinstance(r, dict):
            if "key" in r:
                out.append(str(r["key"]))
            elif "id" in r:
                out.append(str(r["id"]))
    return out


def cluster(study: str, key: str) -> str:
    if study == "g8":
        m = G8.match(key)
        body = key if m is None else f'{m["head"]}|{m["tail"]}'
        return f"{study}::{body}"
    fields = key.split("|")
    kept = []
    for f in fields:
        if study in ("h6", "g6", "p3b", "x426b", "C") and FS.match(f):
            continue
        if study in ("h6", "x426b") and MASS.match(f):
            continue
        if study == "p3b" and BETA.match(f):
            continue
        if study == "D" and PATCH.match(f):
            continue
        if study in ("h9", "x426b"):
            f = KFRAC.sub("", f)
        kept.append(f)
    return f"{study}::{'|'.join(kept)}"


def main(out_csv: str, out_json: str) -> int:
    rows, summary, bad = [], {}, []
    for st in STUDIES:
        try:
            k0 = keys_of(BASE / f"u3_{st}_V0.json")
            k1 = keys_of(BASE / f"u3_{st}_VB.json")
        except FileNotFoundError as exc:
            print(json.dumps({"status": "input_missing", "detail": str(exc)}))
            return 2
        if sorted(k0) != sorted(k1) or len(k0) != EXPECTED[st] or len(set(k0)) != len(k0):
            bad.append({"study": st, "n_V0": len(k0), "n_VB": len(k1), "expected": EXPECTED[st]})
        cl = {k: cluster(st, k) for k in k0}
        sizes = Counter(cl.values())
        summary[st] = {"keys": len(k0), "clusters": len(sizes), "max_size": max(sizes.values()),
                       "singletons": sum(1 for v in sizes.values() if v == 1)}
        rows += [(st, k, cl[k]) for k in k0]
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(("study", "key", "cluster"))
        w.writerows(rows)
    total = {"keys": len(rows), "clusters": len({r[2] for r in rows})}
    json.dump({"per_study": summary, "total": total, "defects": bad}, open(out_json, "w", encoding="utf-8"),
              indent=1)
    print(json.dumps({"status": "ok" if not bad else "defect", "total": total, "per_study": summary,
                      "defects": bad}))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
