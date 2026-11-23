"""Compact tables from s10_ai_witness.json -> s10_ai_tables.txt (stats-design-expert, 2026-11-23)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    d = json.loads((HERE / "s10_ai_witness.json").read_text(encoding="utf-8"))
    L = [f"seed {d['seed']}, sigma {d['sigma_mm']} mm, streak {d['L_streak']} cycles; "
         f"self_checks {d['self_checks']}", "",
         "== A(i) false trigger per moving streak (max over u 0.25-0.6, f 1.0/0.85/0.7) and "
         "worst f=0.7 u=0.25 ; stall detection median/p95 [s] at u 0.22 / 0.4 / 0.75 =="]
    delay = {(r["est"], r["N_trig"], r["D_trig"], r["eta"]): r["delay"] for r in d["stall_delay"]}
    for r in d["false_trigger_moving"]:
        key = (r["est"], r["N_trig"], r["D_trig"], r["eta"])
        dl = delay[key]
        cells = []
        for u in ("u0.22", "u0.4", "u0.75"):
            x = dl[u]
            cells.append(f"{x['median_s']}/{x['p95_s']}(p{x['p_detect_10s']:.3f})")
        L.append(f"{r['est']} N{r['N_trig']:>2} D{r['D_trig']:.1f} eta{r['eta']:.2f} | "
                 f"maxFT {100*r['max_p']:6.2f}%  f1.0u0.25 {100*r['p']['u0.25_f1.0']:6.2f}% "
                 f"f0.85u0.25 {100*r['p']['u0.25_f0.85']:6.2f}% | " + "  ".join(cells))
    L += ["", "== A(i) episode (u_ctrl 0.3): per r_th: p_witness / end p95 s / pulse median,p95 mm /"
          " p_false_end =="]
    for r in d["episodes"]:
        if r["N_cap"] != 20 and not (r["est"] == "E1" and r["du_step"] == 0.05):
            continue
        cells = []
        for rth, x in r["by_rth"].items():
            cells.append(f"r{rth}:{x['p_witness']:.3f}/{x['end_s_p95']:.1f}/"
                         f"{x['pulse_mm_median']:.2f},{x['pulse_mm_p95']:.2f}/{x['p_false_end']:.3f}")
        L.append(f"{r['est']} du{r['du_step']} cap{r['u_cap']} sw{r['s_w']} Ncap{r['N_cap']} "
                 f"{r['speed']:>4} | " + " ".join(cells))
    (HERE / "s10_ai_tables.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
