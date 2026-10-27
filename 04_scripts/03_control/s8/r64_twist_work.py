"""Rev. 64 (b)-7: twist-mode actuator work after a floor event split by command component.

Work definition of spec 248.3: P = 1/2 (D - D0) (n . u), D = (F_FL + F_RR) - (F_FR + F_RL) of
``pads.F_cyl`` (1 ms), D0 = median over [t_ev - 0.5, t_ev), n = (+, -, -, +) / 2,
u = ``record.u_applied`` held between the 10 Hz samples; bins of 0.5 s from the event to 8 s.
Split: each 10 Hz period's applied twist speed n . u_applied is divided among the components
(``cmp_attitude_u``, ``cmp_heave_u``, ``cmp_twist_u``, ``cmp_guard_u``, ``cmp_reapproach_u``) in
proportion to their twist projection n . cmp in the r8 sample ``j`` periods earlier; ``j`` (0..3)
is the shift that best fits n . issued_u to n . u_applied (least squares, reported). A period
whose component twist sum is below 1e-7 m/s goes to ``unassigned``.
Bins > +20 J at >= 1.5 s (spec 248.3 bundle rule) are listed with their component shares.
Only settle / drop events (no forced window, so no masking is needed).
Usage: python -I r64_twist_work.py <out_json> <workers> <root> [<root> ...]
Read only; no random numbers.
"""
from __future__ import annotations

import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r64_common import case_dirs, load_json  # noqa: E402

COMPONENTS = ("attitude", "heave", "twist", "guard", "reapproach")
N_VEC = np.array([0.5, -0.5, -0.5, 0.5])
SPAN_S = 8.0
BIN_S = 0.5
JUDGED_START_S = 1.5
BUNDLE_J = 20.0


def analyse(case: Path) -> dict | None:
    result = load_json(case / "result.json")
    if not isinstance(result, dict) or not (case / "pads.npz").exists() \
            or not (case / "r8_series.npz").exists():
        return None
    t_ev = result.get("event_t_s")
    if not isinstance(t_ev, (int, float)):
        return None
    ep = result.get("episode") or {}
    if ep.get("kind") not in (None, "settle", "drop"):
        return None
    pads = np.load(case / "pads.npz", allow_pickle=True)
    rec = np.load(case / "record" / "record.npz", allow_pickle=True)
    r8 = np.load(case / "r8_series.npz", allow_pickle=True)
    if not all(f"cmp_{c}_u" in r8.files for c in COMPONENTS):
        return None
    tp = np.asarray(pads["t"], float)
    m = (tp >= t_ev - 0.5) & (tp < t_ev + SPAN_S)
    t = tp[m] - t_ev
    F = np.asarray(pads["F_cyl"], float)[m]
    D = (F[:, 0] + F[:, 3]) - (F[:, 1] + F[:, 2])
    D0 = float(np.median(D[t < 0]))
    dD = D - D0
    tr = np.asarray(rec["t"], float) - t_ev
    ua = np.asarray(rec["u_applied"], float) @ N_VEC
    t8 = np.asarray(r8["t"], float) - t_ev
    if len(t8) != len(tr) or np.max(np.abs(t8 - tr)) > 1e-6:
        return {"case": str(case), "error": "record / r8 time mismatch"}
    issued = np.asarray(r8["issued_u"], float) @ N_VEC
    comps = np.stack([np.asarray(r8[f"cmp_{c}_u"], float) @ N_VEC for c in COMPONENTS], axis=1)
    post = tr >= -0.5
    fits = {}
    for j in range(4):
        a = ua[j:][post[j:]]
        b = issued[: len(issued) - j][post[j:]]
        fits[j] = float(np.sum((a - b) ** 2) / max(np.sum(a**2), 1e-30))
    j_best = min(fits, key=fits.get)
    shifted = np.vstack([np.zeros((j_best, len(COMPONENTS))), comps[: len(comps) - j_best]])
    total = shifted.sum(axis=1)
    share = np.zeros_like(shifted)
    ok = np.abs(total) > 1e-7
    share[ok] = shifted[ok] / total[ok, None]
    k = np.clip(np.searchsorted(tr, t, side="right") - 1, 0, len(tr) - 1)
    u1 = ua[k]
    dt = float(np.median(np.diff(t)))
    P = 0.5 * dD * u1
    Pc = P[:, None] * share[k]
    P_un = P * (~ok[k])
    bins = []
    for b0 in np.arange(0.0, SPAN_S, BIN_S):
        mb = (t >= b0) & (t < b0 + BIN_S)
        if not mb.any():
            continue
        row = {"t0": float(b0), "W_J": float(P[mb].sum() * dt),
               **{c: float(Pc[mb, i].sum() * dt) for i, c in enumerate(COMPONENTS)},
               "unassigned": float(P_un[mb].sum() * dt)}
        bins.append(row)
    judged = [b for b in bins if b["t0"] >= JUDGED_START_S - 1e-9]
    over = [b for b in judged if b["W_J"] > BUNDLE_J]
    # bundles = maximal runs of consecutive over bins
    bundles, cur = [], []
    for b in judged:
        if b["W_J"] > BUNDLE_J:
            cur.append(b)
        elif cur:
            bundles.append(cur)
            cur = []
    if cur:
        bundles.append(cur)
    pos = {c: float(sum(max(b[c], 0.0) for b in judged)) for c in COMPONENTS + ("unassigned",)}
    return {"case": str(case), "name": case.name, "batch": case.parent.parent.name
            if case.parent.name == "episodes" else case.parent.name,
            "kind": ep.get("kind"), "leg": ep.get("leg"), "depth_m": ep.get("depth_m"),
            "ramp_s": ep.get("ramp_s"), "delay_periods": j_best,
            "fit_rel_sq_err": round(fits[j_best], 4), "bins": bins,
            "bundles": [{"t0": bb[0]["t0"], "t1": bb[-1]["t0"] + BIN_S,
                         "W_J": float(sum(x["W_J"] for x in bb)),
                         **{c: float(sum(x[c] for x in bb)) for c in COMPONENTS + ("unassigned",)}}
                        for bb in bundles],
            "judged_positive_by_component_J": pos,
            "judged_net_by_component_J": {c: float(sum(b[c] for b in judged))
                                          for c in COMPONENTS + ("unassigned",)},
            "n_over_bins": len(over)}


def safe(case: Path):
    try:
        return analyse(case)
    except Exception as exc:  # report, continue
        return {"case": str(case), "error": repr(exc)}


def main() -> None:
    out_path, workers, roots = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    cases = list(case_dirs(roots))
    with Pool(workers) as pool:
        rows = [r for r in pool.map(safe, cases, chunksize=4) if r]
    good = [r for r in rows if "error" not in r]
    by_batch = {}
    for r in good:
        by_batch.setdefault(r["batch"], []).append(r)
    summary = {"cases": len(good), "errors": [r for r in rows if "error" in r][:10]}
    for batch, rs in sorted(by_batch.items()):
        bundles = [dict(case=r["name"], **b) for r in rs for b in r["bundles"]]
        comp_pos = {c: float(sum(r["judged_positive_by_component_J"][c] for r in rs))
                    for c in COMPONENTS + ("unassigned",)}
        dominant = {}
        for b in bundles:
            c = max(COMPONENTS, key=lambda x: b[x])
            dominant[c] = dominant.get(c, 0) + 1
        summary[batch] = {
            "cases": len(rs),
            "delay_periods_hist": {str(j): sum(r["delay_periods"] == j for r in rs) for j in range(4)},
            "fit_rel_sq_err_max": max(r["fit_rel_sq_err"] for r in rs),
            "runs_with_bundles": sum(bool(r["bundles"]) for r in rs),
            "runs_with_2plus_bundles": sum(len(r["bundles"]) >= 2 for r in rs),
            "bundles": len(bundles),
            "bundle_dominant_component": dominant,
            "judged_positive_work_by_component_J": comp_pos,
            "top_bundles": sorted(bundles, key=lambda b: -b["W_J"])[:12],
        }
    Path(out_path).write_text(json.dumps({"summary": summary, "cases": good}, indent=1,
                                         ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False)[:9000])


if __name__ == "__main__":
    main()
