"""Exposure of the F1-revealed D1 rod fallback in the 768 population.

In the 768 records (F1 defect) a plant release shows as a 1 ms rod-pressure drop > 20 bar
(reading snaps back to p_r0). The physical (F1-fixed) rod pressure then drains with
tau ~ 50 ms instead, so the next 10 Hz sample still sees ~ 0.15 p_pre. Predictor: the
pre-release rod pressure p_pre; a fallback needs a one-period step > max_step (100 bar).
Calibrated on bundle A (55 episodes, 17 actual fallbacks), then counted on all 768.
"""
import json
import os
import numpy as np
from concurrent.futures import ProcessPoolExecutor

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s8" / "rev53_56" / "rev54"
OUT_DIR.mkdir(parents=True, exist_ok=True)
# ---
ROOT = str(REPO / r"07_results\S8")
REF = ROOT + r"\ml_main_20261025_090131\episodes"
VA = ROOT + r"\c36_20261025_155317\A_rt\verify_S8ML.json"
OUT = str(OUT_DIR / r"c36f_exposure.json")


def scan(case):
    path = os.path.join(REF, case)
    try:
        r = json.load(open(os.path.join(path, "result.json"), encoding="utf-8"))
        z = np.load(os.path.join(path, "pads.npz"))
        t = z["t"]
        rod = z["rod_pressure"] / 1e5
        air = z["airborne"]
    except Exception as exc:  # noqa: BLE001
        return case, None, str(exc)
    d = np.diff(rod, axis=0)
    out = []
    for i, leg in zip(*np.where(d < -20.0)):
        out.append(dict(t_rel=float(t[i + 1] - r["event_t_s"]), leg=int(leg), pre=float(rod[i, leg]),
                        post=float(rod[i + 1, leg]), air=bool(air[i, leg])))
    return case, out, None


if __name__ == "__main__":
    cases = sorted(os.listdir(REF))
    with ProcessPoolExecutor(max_workers=12) as ex:
        res = list(ex.map(scan, cases, chunksize=8))
    data = {c: o for c, o, e in res if o is not None}
    errs = {c: e for c, o, e in res if e}
    json.dump(dict(data=data, errors=errs), open(OUT, "w"))
    va = json.load(open(VA, encoding="utf-8"))
    actual = {c for c, m in va["ml_metrics"].items() if (m.get("rod_fallback") or {}).get("events")}
    a_ids = list(va["ml_metrics"])
    print("runs scanned", len(data), "errors", len(errs))
    for thr in (80, 100, 110, 115, 120, 125):
        pred = {c for c in a_ids if any(s["pre"] > thr and s["t_rel"] > 0 for s in data.get(c, []))}
        tp = len(pred & actual)
        print(f"thr {thr} bar: A predicted {len(pred)}, true pos {tp}/{len(actual)}, false pos {len(pred - actual)} "
              f"{sorted(pred - actual)[:8]} missed {sorted(actual - pred)}")
        allp = [c for c, o in data.items() if any(s["pre"] > thr and s["t_rel"] > 0 for s in o)]
        print(f"      768 runs with a release from > {thr} bar after the event: {len(allp)}")
    pre_actual = []
    for c in actual:
        pre_actual.append(max(s["pre"] for s in data[c] if s["t_rel"] > 0))
    print("A actual fallback cases: max pre after event", sorted(np.round(pre_actual, 1)))
    non = [max([s["pre"] for s in data[c] if s["t_rel"] > 0] or [0]) for c in a_ids if c not in actual]
    print("A non-fallback cases: max pre after event", sorted(np.round(non, 1)))
