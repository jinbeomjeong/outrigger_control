"""Structure-only inspection of design inputs (ed. 6 stats design, stats-design-expert 2026-11-23).

Prints nothing but a status line; writes key names / counts / identifier values (no metric values)
to the scratch folder given as argv[1]. Inputs: stored c4g2_only grid files (V0 base arm,
committed) and the D0 attribution json (ed. 5 public design input).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control")
GRID = ROOT / "touch_phase" / "acceptance" / "c4g2_only" / "grid"
D0 = ROOT / "j_p3_cause" / "ed5_d0_390f88a9" / "d0_attribution.json"


def main() -> int:
    out_dir = Path(sys.argv[1])
    res = {}
    for f in sorted(GRID.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        r = d["results"]
        first = r[0] if isinstance(r, list) else r[next(iter(r))]
        info = {"meta": d["meta"], "n_results": len(r), "result_type": type(r).__name__,
                "first_keys": list(first) if isinstance(first, dict) else str(type(first))}
        # identifier-like string fields only (no numbers)
        ids = {}
        if isinstance(first, dict):
            for k, v in first.items():
                if isinstance(v, str) and len(v) < 120:
                    vals = Counter(str(x.get(k)) for x in (r if isinstance(r, list) else r.values()))
                    ids[k] = {"n_unique": len(vals), "examples": list(vals)[:12]}
        info["string_fields"] = ids
        res[f.name] = info
    d0 = json.loads(D0.read_text(encoding="utf-8"))
    res["d0_variants_keys"] = list(d0["variants"])[:40] if isinstance(d0["variants"], dict) else \
        str(type(d0["variants"]))
    v = d0["variants"]
    if isinstance(v, dict):
        k0 = next(iter(v))
        res["d0_variant_first"] = {"name": k0, "keys": list(v[k0])[:40] if isinstance(v[k0], dict)
                                   else str(type(v[k0]))}
    ref = d0["reference"]["R12_o0.0"]["V0"]
    res["d0_ref_fields"] = list(ref)
    (out_dir / "s00_shape.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
