"""Flow demand of the 24 final-controller records against the pump supply (read only).

Corrected from the main-session flow_demand.py: demand uses the speed the plant applies
(clip of the command to +-v_max, actuation.py:226 = record u_applied), not issued_u.
Demand = sum per leg: extending A_h v, retracting A_r |v|. No shared-circuit response is
computed here; it is an exposure count. Writes flow_exposure.json.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from params import LEGS, OUT_DIR, ROOT, load_params  # noqa: E402

ETAS = (0.95, 0.90, 0.85)


def case_dirs() -> list[Path]:
    s9 = sorted({q.parent.parent for q in (ROOT / "07_results" / "S9").glob("batch_FINAL-REP*/*/record/record.npz")})
    s8 = sorted({q.parent.parent for q in (ROOT / "07_results" / "S8").glob("final_*/*/record/record.npz")})
    return s9 + s8


def load_case(case: Path) -> dict:
    with np.load(case / "record" / "record.npz", allow_pickle=True) as d:
        out = {k: np.asarray(d[k]) for k in ("t", "u_cmd", "u_applied", "F_cyl", "stroke_true")}
    series = case / "r8_series.npz"
    out["phase"] = None
    if series.exists():
        with np.load(series, allow_pickle=True) as d:
            if "phase" in d and len(d["phase"]) == len(out["t"]):
                out["phase"] = np.asarray(d["phase"]).astype(str)
    return out


def demand(v: np.ndarray, p) -> np.ndarray:
    return (np.maximum(v, 0.0) * p.A_h + np.maximum(-v, 0.0) * p.A_r).sum(axis=1)


def analyse(case: Path, p) -> dict:
    d = load_case(case)
    t = d["t"]
    dt = np.gradient(t)
    q_applied = demand(d["u_applied"], p)
    q_clip = demand(np.clip(d["u_cmd"], -p.v_max, p.v_max), p)
    row = {"case": case.parent.name + "/" + case.name, "duration_s": float(t[-1] - t[0]),
           "max_demand_applied_L_min": float(q_applied.max() * 6e4),
           "max_demand_clipped_cmd_L_min": float(q_clip.max() * 6e4),
           "max_abs_u_cmd_mm_s": float(np.abs(d["u_cmd"]).max() * 1e3),
           "max_abs_u_applied_mm_s": float(np.abs(d["u_applied"]).max() * 1e3),
           "rms_clip_vs_applied_mm_s": float(np.sqrt(np.mean((np.clip(d["u_cmd"], -p.v_max, p.v_max) - d["u_applied"]) ** 2)) * 1e3),
           "phase_available": d["phase"] is not None, "eta": {}}
    for eta in ETAS:
        supply = p.Q_pump(eta)
        short = q_applied > supply * (1 + 1e-6)
        entry = {"supply_L_min": supply * 6e4, "short_s": float(dt[short].sum()),
                 "max_shortfall_pct": float(max(0.0, q_applied.max() / supply - 1.0) * 100)}
        if d["phase"] is not None and short.any():
            by = defaultdict(float)
            for ph, h in zip(d["phase"][short], dt[short]):
                by[ph] += float(h)
            entry["short_s_by_phase"] = {k: round(v, 2) for k, v in sorted(by.items())}
        row["eta"][f"{eta:.2f}"] = entry
    return row


def air_loads(case: Path, p) -> dict:
    """Cylinder force statistics while all four legs are commanded at v_max (TOUCH descent)."""
    d = load_case(case)
    mask = (np.abs(d["u_applied"]) > 0.99 * p.v_max).all(axis=1)
    if not mask.any():
        return {}
    return {"samples": int(mask.sum()), "F_cyl_median_N": dict(zip(LEGS, np.median(d["F_cyl"][mask], axis=0).round(1).tolist())),
            "F_cyl_min_N": dict(zip(LEGS, d["F_cyl"][mask].min(axis=0).round(1).tolist())),
            "F_cyl_max_N": dict(zip(LEGS, d["F_cyl"][mask].max(axis=0).round(1).tolist()))}


def main() -> None:
    p = load_params()
    rows, failed = [], []
    for case in case_dirs():
        try:
            rows.append(analyse(case, p) | {"all_legs_at_vmax": air_loads(case, p)})
        except (OSError, KeyError, ValueError) as err:
            failed.append({"case": str(case), "error": repr(err)})
    out = {"n": len(rows), "failed": failed, "rows": rows}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "flow_exposure.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("cases", len(rows), "failed", len(failed))
    for f in failed:
        print(f)
    for r in rows:
        e = r["eta"]
        print(f"{r['case'][-46:]:46s} {r['duration_s']:6.0f} s  max {r['max_demand_applied_L_min']:6.2f} L/min  cmd {r['max_abs_u_cmd_mm_s']:6.2f} applied {r['max_abs_u_applied_mm_s']:6.2f} mm/s "
              + " ".join(f"{k}:{e[k]['short_s']:5.1f}s" for k in e)
              + "  " + json.dumps(e["0.90"].get("short_s_by_phase", {})))
    a = next((r["all_legs_at_vmax"] for r in rows if r["all_legs_at_vmax"]), None)
    print("example all-legs-at-vmax load:", a)


if __name__ == "__main__":
    main()
