"""k04: report tables from k02 (per round medians by candidate; per leg mid state and K1).

Usage: conda run -n dynamics-dev python -I -B k04_tables.py
Output: k04_out.txt (this folder).
"""
import csv
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = ("k1_old", "kpad_old", "a0.05_k1", "a0.1_k1", "a0.2_k1", "b_k1", "c0.1_k1")


def f(v, nd=3):
    if v in (None, "", "None"):
        return "-"
    try:
        x = float(v)
    except ValueError:
        return str(v)
    return "-" if math.isnan(x) else f"{x:.{nd}f}"


def main() -> int:
    rounds = list(csv.DictReader((HERE / "k02_rounds.csv").open(encoding="utf-8")))
    legs = list(csv.DictReader((HERE / "k02_legs.csv").open(encoding="utf-8")))
    out = ["# per round: median ratio (count) [scale]; W = outside (0.8, 2.3)"]
    out.append("run | rnd | " + " | ".join(NAMES))
    for r in rounds:
        cells = []
        for n in NAMES:
            med = r.get(f"{n}_median")
            cnt = r.get(f"{n}_count")
            sc = r.get(f"{n}_scale")
            w = "W" if r.get(f"{n}_warn2.3") == "True" else ""
            cells.append(f"{f(med)}({cnt})[{f(sc, 2)}]{w}")
        out.append(f"{r['run']} | {r['round']} | " + " | ".join(cells))
    out.append("")
    out.append("# per leg: stuck_at_mid, moved_by_mid_mm, window_travel_mm, ratio old / Kpad / a0.1 / b / a0.1 mid shift, seal est old / a0.1 [kN], load est old / a0.1 [kN]")
    for g in legs:
        if g.get("reversed") == "True":
            out.append(f"{g['run']} r{g['round']} {g['leg']} reversed")
            continue
        out.append(
            f"{g['run']} r{g['round']} {g['leg']} stuck={g['stuck_at_mid']} f_mid={f(g['f_mid_kN'],2)} "
            f"Fs={f(g['Fs_kN'],2)} moved={f(g['moved_by_mid_mm'],4)} win={f(g['window_travel_mm'],3)} | "
            f"old={f(g['k1_old_ratio'])} kpad={f(g['kpad_old_ratio'])} a0.1={f(g['a0.1_k1_ratio'])} "
            f"(shift {g['a0.1_mid_shift']}, kpad {f(float(g['a0.1_kpad'])/float(g['s_nom_MN_m'])/1e6 if g['a0.1_kpad'] not in ('', 'nan') else 'nan')}) "
            f"b={f(g['b_k1_ratio'])} c0.1={f(g['c0.1_k1_ratio'])} | seal {f(g['k1_old_seal_kN'],2)}/{f(g['a0.1_k1_seal_kN'],2)} "
            f"load {f(g['k1_old_load_kN'],2)}/{f(g['a0.1_k1_load_kN'],2)}")
    (HERE / "k04_out.txt").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
