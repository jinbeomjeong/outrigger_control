"""H-S8-3: largest optimism / over-estimate rows of h_s8_3_window.json for one variant.

Usage: python -I h_s8_3_window_top.py <h_s8_3_window.json> <variant> [n]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    var = sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    rows = data["rows"]
    for key in ("opt_max_kN", "over_end_kN"):
        print("top", key)
        for r in sorted(rows, key=lambda r: -r[var][key])[:n]:
            print(f"  {r['case']:28s} {r['leg']} t0 {r['t0']:6.2f} u {r['u_last_mm_s']:7.3f} "
                  f"delay {r['lock_delay_s']:.3f} W {r[var]['W_s']:.3f} {key} {r[var][key]:.2f} "
                  f"eps: W {r['eps']['W_s']:.3f} {r['eps'][key]:.2f} late {r[var]['plant_lock_after_W']}")


if __name__ == "__main__":
    main()
