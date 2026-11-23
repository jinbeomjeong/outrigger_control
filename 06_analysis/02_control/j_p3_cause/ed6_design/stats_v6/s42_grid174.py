"""Ed. 6 confirmation (na): grid 192 rows with the pass->fail rule on the 174 V0-pass opportunity
rows only (V0-fail 18 rows judged for FAULT 0 / J-P3, recorded otherwise). Recomputes the s40
'Da_192x1' grid figures on 174 units (stats-design-expert, 2026-11-24, design only).
Writes s42_grid174.json / .txt next to this file. stdout: status only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# isort: split
import s40_sens_confirm as s40  # noqa: E402

SEED = 20261124


def main() -> int:
    rng = np.random.default_rng(SEED)
    out = {"seed": SEED, "null": {}, "power": {}}
    for n in (192, 174):
        fr = [(1, 0)] * n
        for c in (3.0, 3.5):
            r = s40.simulate(fr, c, 0.5, 20000, rng, k_list=(0, 1))
            out["null"][f"n{n}|c{c}"] = {"zero": r["zero"], "allow1": r["count1"]}
        for frac in (0.01, 0.02, 0.05):
            nh = max(1, int(round(frac * n)))
            for mb in (0.0, -1.0):
                idx = rng.choice(n, nh, replace=False)
                r = s40.simulate(fr, 3.5, 0.5, 10000, rng, harm=idx, m_bad=mb, k_list=(0, 1))
                out["power"][f"n{n}|frac{frac}(nh{nh})|mbad{mb}"] = {"zero": r["zero"],
                                                                      "allow1": r["count1"]}
    (HERE / "s42_grid174.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item()),
                                           encoding="utf-8")
    L = [f"{k:<34} zero {100*v['zero']:.1f}% allow1 {100*v['allow1']:.1f}%"
         for blk in ("null", "power") for k, v in out[blk].items()]
    (HERE / "s42_grid174.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
