"""H4lb end lateral loads with the R5 test stair (band 2.50 kN, floor margin 10 kN -> 45 / 30 / 21.91 / 21.91 kN),
independent path (dynamics harness C2RA, pressure-stop) for spec rev. 21. Read-only import of the project driver.
Run (project root, dynamics-dev): conda run -n dynamics-dev python -I <this file>"""
import json
import math
import sys
from pathlib import Path

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
sys.path.insert(0, str(REPO / r"04_scripts\03_control"))
import run_h4_fs_order_check as hk  # noqa: E402

OUT = OUT_DIR / "s6r21_h4lb.json"
FLOOR = hk.F_MIN + 2.50e3 + 10e3
SLOPES = {"V:pitch+3.5": (0.0, 3.5), "V:pitch-3.5": (0.0, -3.5), "P:pitch+3.2": (0.0, 3.2), "P:pitch-3.2": (0.0, -3.2)}
hk.SLOPES.update(SLOPES)


def cases():
    C = []
    for tag in SLOPES:
        for km in ("yaml", "ext"):
            for s in (12345, 12346, 12347):
                C.append(hk.mk(f"H|R5lb|{tag}|rigid|{km}|Fs0|{s}", tag, "rigid", km, 0.0,
                               hk.spec(hk.stair(45e3, FLOOR)), seed=s))
    return C


def main():
    import psutil
    psutil.Process().cpu_affinity(hk.P_CORES)
    C = cases()
    r0 = hk.one(C[0])
    from multiprocessing import Pool
    with Pool(8) as p:
        runs = [r0] + p.map(hk.one, C[1:], chunksize=1)
    OUT.write_text(json.dumps({"floor_N": FLOOR, "runs": runs}, indent=1, default=float), encoding="utf-8")
    for r in sorted(runs, key=lambda r: r["id"]):
        if "error" in r:
            print(r["id"], r["error"]); continue
        x = r["x"]
        tag = r["id"].split("|")[2]
        th = math.radians(abs(float(tag.split("pitch")[1])))
        sgn = 1.0 if "pitch+" in tag else -1.0
        n0 = x["Fl_start_kN"]
        pred = [round(min(x["Ft_start_kN"][i] - sgn * n0[i] * math.sin(th), 0.5 * FLOOR / 1e3) + sgn * n0[i] * math.sin(th), 2)
                for i in (2, 3)]
        print(r["id"], "min", r["min_true_cyl_force_kN"], "Ft start", x["Ft_start_kN"], "Ft end", x["Ft_final_kN"],
              "max end", max(x["Ft_final_kN"]), "pred rear", pred, "stops", [s["P_stop_reading_kN"] for s in x["steps"]])


if __name__ == "__main__":
    main()
