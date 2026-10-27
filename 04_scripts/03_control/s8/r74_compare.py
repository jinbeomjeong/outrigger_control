"""Spec rev. 73 383: P-S8-30 revised candidates on the (C) 8 + regression 20 + ref 20 runs (saved r74 JSON).

Per variant: r72_judge judgement (decision 2 + U-S9-G6c FLAG rules), pass counts per group, command hashes of the
ref runs against proj of the same batch, worst LOC delay, min F after the crawler lift-off, READY maximum.

Usage: python -I r74_compare.py <out_json> <r74 json> [...] --groups <r74_p30_judgement.json>
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r72_judge  # noqa: E402


def main():
    out = Path(sys.argv[1])
    files, groups_file = [], None
    it = iter(sys.argv[2:])
    for a in it:
        if a == "--groups":
            groups_file = next(it)
        else:
            files.append(a)
    g = json.loads(Path(groups_file).read_text(encoding="utf-8"))["g6"]
    reg = {c["key"] for c in g["changed"] if c["proj_pass"] and not c["af_pass"]}
    cset = {c["key"] for c in g["C_rows"]}
    rows = [r for f in files for r in json.loads(Path(f).read_text(encoding="utf-8"))["results"] if "error" not in r]
    by_var = defaultdict(dict)
    for r in rows:
        by_var[r["variant"]][r["inner_key"]] = r
    res = {"script": "04_scripts/03_control/s8/r74_compare.py", "inputs": files, "variants": {}}
    proj = by_var.get("proj", {})
    for var, rs in sorted(by_var.items()):
        tmp = out.parent / f"_cmp_{var}.json"
        tmp.write_text(json.dumps({"results": [dict(r, key=k) for k, r in rs.items()]}, default=float),
                       encoding="utf-8")
        jp = out.parent / f"_cmp_{var}_j.json"
        argv = sys.argv
        sys.argv = ["r72_judge.py", str(jp), str(tmp)]
        try:
            r72_judge.main()
        finally:
            sys.argv = argv
        j = json.loads(jp.read_text(encoding="utf-8"))
        tmp.unlink()
        jp.unlink()
        tab = {t["key"]: t for t in j["table"]}

        def cnt(keys):
            ks = [k for k in keys if k in tab]
            return f"{sum(1 for k in ks if not tab[k]['fails'])}/{len(ks)}"

        refs = [k for k in rs if k.startswith("ref|")]
        res["variants"][var] = {
            "C8_pass": cnt(cset), "reg20_pass": cnt(reg), "ref_pass": cnt(refs),
            "ref_hash_eq_proj": sum(1 for k in refs if k in proj and proj[k]["commands_sha256"] == rs[k]["commands_sha256"]),
            "gate_fail": j["gate_fail"],
            "C_fails": {k: tab[k]["fails"] for k in cset if k in tab and tab[k]["fails"]},
            "reg_fails": {k: tab[k]["fails"] for k in reg if k in tab and tab[k]["fails"]},
            "loc_delay_max_s": max((rs[k].get("loc_delay_s") or 0) for k in rs),
            "C_min_F_off_kN": min((tab[k]["min_F_kN"] for k in cset if k in tab and tab[k]["min_F_kN"] is not None),
                                  default=None),
            "all_min_F_off_kN": min(t["min_F_kN"] for t in j["table"] if t["min_F_kN"] is not None),
            "ready_max_s": max((t["t_ready_s"] or 0) for t in j["table"]),
            "flags": {"demoted": j["n_p38_demoted"], "preloc_loss": j["n_p38_preloc_loss"]}}
    out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    for var, v in res["variants"].items():
        print(var, {k: v[k] for k in ("C8_pass", "reg20_pass", "ref_pass", "ref_hash_eq_proj", "gate_fail",
                                      "loc_delay_max_s", "C_min_F_off_kN", "all_min_F_off_kN", "ready_max_s",
                                      "flags")})
        for k, f in list(v["C_fails"].items()) + list(v["reg_fails"].items()):
            print("   ", k, f)


if __name__ == "__main__":
    main()
