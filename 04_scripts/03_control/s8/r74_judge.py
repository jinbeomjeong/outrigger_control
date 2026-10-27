"""Spec rev. 73: P-S8-30 (Af3B4) acceptance from the saved rev74 runs (no simulation).

G6: per variant (proj, Af3B4) the r72_judge judgement (decision 2 and U-S9-G6c FLAG rules), the changed command list
Af3B4 vs proj of the same batch, and the (C) rows (rigid + S1 front). G8: Af3B4 rows against a baseline (rev70
AG2c5 / p28 flat proj rows; unchanged by P-S8-29 and the tail margin, checked by python). Writes the expected-hash
file for the python acceptance of P-S8-30 (implemented controller "proj" = the Af3B4 rows).

Usage: python -I r74_judge.py <out_dir> --g6 <r74 json> [...] --g8 <r74 json> [...] --base8 <json> [...]
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r72_judge  # noqa: E402


def load(paths):
    out = []
    for p in paths:
        out += json.loads(Path(p).read_text(encoding="utf-8"))["results"]
    return out


def main():
    out_dir = Path(sys.argv[1])
    args = {"--g6": [], "--g8": [], "--base8": []}
    cur = None
    for a in sys.argv[2:]:
        if a in args:
            cur = a
        else:
            args[cur].append(a)
    out_dir.mkdir(parents=True, exist_ok=True)
    res = {"script": "04_scripts/03_control/s8/r74_judge.py", "inputs": args}
    # ---------------------------------------------------------------- G6
    g6 = [r for r in load(args["--g6"]) if r.get("harness") == "g6"]
    errors = [r["key"] for r in g6 if "error" in r]
    by_var = defaultdict(dict)
    for r in g6:
        if "error" not in r:
            by_var[r["variant"]][r["inner_key"]] = r
    judg = {}
    for var, rows in by_var.items():
        tmp = out_dir / f"_r74_{var}.json"
        tmp.write_text(json.dumps({"results": [dict(r, key=k) for k, r in rows.items()]}, default=float),
                       encoding="utf-8")
        jp = out_dir / f"r74_g6_{var}_judgement.json"
        argv = sys.argv
        sys.argv = ["r72_judge.py", str(jp), str(tmp)]
        try:
            r72_judge.main()
        finally:
            sys.argv = argv
        tmp.unlink()
        judg[var] = json.loads(jp.read_text(encoding="utf-8"))
    cand = os.environ.get("R74_CAND", "Af3B4")
    p, a = by_var.get("proj", {}), by_var.get(cand, {})
    changed = sorted(k for k in a if k in p and a[k]["commands_sha256"] != p[k]["commands_sha256"])
    tab = {v: {t["key"]: t for t in j["table"]} for v, j in judg.items()}
    c_keys = sorted(k for k in a if k.startswith("g6r|rigid+S1@F"))
    res["g6"] = {
        "errors": errors,
        "summary": {v: {"n": j["n"], "pass": j["n_pass"], "gate_fail": j["gate_fail"],
                        "p38_demoted": j["n_p38_demoted"], "p38_preloc_loss": j["n_p38_preloc_loss"]}
                    for v, j in judg.items()},
        "n_changed": len(changed),
        "changed": [{"key": k, "proj_pass": not tab["proj"][k]["fails"], "af_pass": not tab[cand][k]["fails"],
                     "ready": [tab["proj"][k]["t_ready_s"], tab[cand][k]["t_ready_s"]],
                     "min_F_kN": [tab["proj"][k]["min_F_kN"], tab[cand][k]["min_F_kN"]],
                     "flags": tab[cand][k]["flags_p38"], "fails": tab[cand][k]["fails"],
                     "pauses": (a[k].get("p30") or {}).get("pauses")} for k in changed],
        "C_rows": [{"key": k, "fails": tab[cand][k]["fails"], "flags": tab[cand][k]["flags_p38"],
                    "min_F_after_off_kN": tab[cand][k]["min_F_kN"], "t_ready_s": tab[cand][k]["t_ready_s"],
                    "preloc": tab[cand][k]["preloc_starts"]} for k in c_keys],
    }
    # ---------------------------------------------------------------- G8
    base = {}
    for r in load(args["--base8"]):
        if "error" not in r:
            base[r.get("r69_key") or r["key"].rsplit("|", 1)[0]] = r["cmd_sha256"]
    g8 = [r for r in load(args["--g8"]) if r.get("harness") == "g8"]
    g8_err = [r["key"] for r in g8 if "error" in r]
    g8 = [r for r in g8 if "error" not in r]
    g8_changed = [r for r in g8 if base.get(r["inner_key"]) != r["cmd_sha256"]]
    res["g8"] = {"n": len(g8), "errors": g8_err, "missing_base": sum(1 for r in g8 if r["inner_key"] not in base),
                 "n_changed": len(g8_changed),
                 "changed": [{"key": r["inner_key"], "pass": r["pass"], "gates": r["gates"],
                              "pauses": (r.get("p30") or {}).get("pauses"),
                              "D8_min_kN": min(r["min_F_after_liftoff_kN"].values()) if r.get(
                                  "min_F_after_liftoff_kN") else None} for r in g8_changed],
                 "n_pass": sum(1 for r in g8 if r["pass"])}
    # ---------------------------------------------------------------- expected hashes for python
    exp = {"note": "P-S8-30 acceptance: implemented controller (variant proj) command SHA-256 per harness key; "
                   "G6 / G8 = the r74 candidate rows (P-S8-29 tree)", "candidate": cand,
           "g6": {k: r["commands_sha256"] for k, r in sorted(a.items())},
           "g8": {r["inner_key"]: r["cmd_sha256"] for r in sorted(g8, key=lambda x: x["inner_key"])}}
    (out_dir / f"r74_p30_expected_hashes_{cand}.json").write_text(json.dumps(exp, indent=1), encoding="utf-8")
    (out_dir / ("r74_p30_judgement.json" if cand == "Af3B4" else f"r74_p30_judgement_{cand}.json")).write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("G6", json.dumps(res["g6"]["summary"]), "changed", res["g6"]["n_changed"], "errors", errors)
    for c in res["g6"]["changed"]:
        print("  chg", c["key"], "pass", c["proj_pass"], "->", c["af_pass"], "ready", c["ready"], "minF",
              [None if x is None else round(x, 2) for x in c["min_F_kN"]], c["flags"], c["fails"], "pauses",
              c["pauses"])
    print("G8 n", res["g8"]["n"], "pass", res["g8"]["n_pass"], "changed", res["g8"]["n_changed"], "missing",
          res["g8"]["missing_base"], "errors", g8_err)
    for c in res["g8"]["changed"][:40]:
        print("  g8chg", c["key"], c["pass"], c["pauses"], c["D8_min_kN"])


if __name__ == "__main__":
    main()
