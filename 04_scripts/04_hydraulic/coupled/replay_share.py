"""Quasi-static flow sharing over the 24 final-controller records (criteria 7.3 E-1, E-2, E-4 format).

Open loop on the records: commands u_applied and forces F_cyl as recorded, sample by sample
through flow_share.share. The speed loss does not feed back on the mechanics or the
controller, so the twist self stress that equalises diagonal legs (rigid-body scenarios) is
absent here. The reduced-model pairs of criteria 8.4 close that loop later. Rod pressure:
back pressure of the B->T land when extending, pilot threshold when retracting.

E-4 (criteria rev. 3): the residual legs are the limited legs whose spool drop lies within
E4_BAND_PA of the lowest one; a swap counts only when the group changes to one with no leg in
common. Label changes without the overlap rule and the original count (band 0.01 bar) stay in
the output for comparison.

Output per case, eta_v and law: time and largest deficit by phase, min r_i and longest
r_i < 0.93 by leg and phase, residual legs, swaps, gallery pressure, sample period.
Also the criteria V-1 and V-2 checks on the records. Writes record_share.json, e4_table.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from cross_check import moving_ratio  # noqa: E402
from flow_exposure import case_dirs  # noqa: E402
from flow_share import share  # noqa: E402
from params import LEGS, OUT_DIR, load_params  # noqa: E402

ETAS = (0.95, 0.90, 0.85)
R_LIM = 0.93
E4_BAND_PA = 0.5e5  # criteria 7.3 rev. 3
E4_BAND_ORIG_PA = 1e3  # 0.01 bar, the rule before rev. 3
E4_FLAG_HZ = 1.0  # criteria 7.3, ASSUMPTION of the criteria


def load(case: Path) -> dict:
    with np.load(case / "record" / "record.npz", allow_pickle=True) as d:
        out = {k: np.asarray(d[k], float) for k in ("t", "u_applied", "F_cyl")}
    n = len(out["t"])
    out["phase"] = np.array(["all"] * n)
    series = case / "r8_series.npz"
    if series.exists():
        with np.load(series, allow_pickle=True) as d:
            if "phase" in d and len(d["phase"]) == n:
                out["phase"] = np.asarray(d["phase"]).astype(str)
    return out


def residual_groups(y: np.ndarray, limited: np.ndarray, band: float) -> np.ndarray:
    """Bit mask per sample of the limited legs within band of the lowest spool drop, -1 if none is limited."""
    ratio = np.where(limited, y, np.inf)
    low = ratio.min(axis=1, keepdims=True)
    masks = ((ratio <= low + band) & limited) @ (1 << np.arange(4))
    return np.where(limited.any(axis=1), masks, -1)


def label_changes(g: np.ndarray) -> np.ndarray:
    """Indices k where the group label differs from sample k - 1, both samples saturated."""
    return np.nonzero((g[1:] != g[:-1]) & (g[1:] >= 0) & (g[:-1] >= 0))[0] + 1


def disjoint_changes(g: np.ndarray) -> np.ndarray:
    """Indices k where the group shares no leg with sample k - 1, both samples saturated (E-4)."""
    return np.nonzero(((g[1:] & g[:-1]) == 0) & (g[1:] >= 0) & (g[:-1] >= 0))[0] + 1


def chained_changes(g: np.ndarray) -> np.ndarray:
    """Stricter check on E-4: a slide A -> A+B -> B also counts, and an unsaturated gap does not reset.

    Keeps the running intersection of the groups; a swap is the sample that empties it.
    """
    out = []
    common = -1
    for k, mask in enumerate(g.tolist()):
        if mask < 0:
            continue
        if common < 0:
            common = mask
        elif common & mask:
            common &= mask
        else:
            out.append(k)
            common = mask
    return np.array(out, int)


def max_in_window(t: np.ndarray, idx: np.ndarray, width: float = 1.0) -> int:
    """Largest number of events in any window of the given width [s]."""
    if len(idx) == 0:
        return 0
    te = t[idx]
    return int((np.searchsorted(te, te + width, side="left") - np.arange(len(te))).max())


def run_case(d: dict, p, eta: float, t_check: float | None = 30.0) -> dict:
    cfg = p.share_config()
    t, U, F = d["t"], d["u_applied"], d["F_cyl"]
    Q_sup = p.Q_pump(eta)
    n = len(t)
    V, Qsum, dem, pP = np.zeros((n, 4)), np.zeros(n), np.zeros(n), np.zeros(n)
    Y, lim = np.zeros((n, 4)), np.zeros((n, 4), bool)
    K_bt = p.K_spool / p.v_max * p.bt_ratio
    for k in range(n):
        u = U[k]
        ext, ret = u > 0, u < 0
        p_r = np.where(ext, p.p_T + (p.A_r * np.abs(u) / np.maximum(K_bt * np.abs(u), 1e-30)) ** 2,
                       np.where(ret, p.p_pilot, p.p_T))
        p_h = (F[k] + p.A_r * p_r) / p.A_h
        r = share(u, np.where(ret, p_r, p_h), Q_sup, cfg)
        V[k], Qsum[k], dem[k], pP[k] = r.v, r.Q.sum(), r.Q_dem, r.p_P
        Y[k], lim[k] = r.y, r.limited
    dt = np.gradient(t)
    out: dict = {"Q_sup_L_min": Q_sup * 6e4, "phases": {}, "legs": {}}
    deficit = np.cumsum((U - V) * dt[:, None], axis=0)
    out["tracking_integral_max_mm"] = dict(zip(LEGS, (np.abs(deficit).max(axis=0) * 1e3).round(2).tolist()))
    out["tracking_between_legs_max_mm"] = float((deficit.max(axis=1) - deficit.min(axis=1)).max() * 1e3)
    if t_check is not None:
        k = int(np.searchsorted(t, t_check))
        out["tracking_at_t_check_mm"] = dict(zip(LEGS, (deficit[min(k, n - 1)] * 1e3).round(2).tolist()))
    # V-1 and V-2
    off = np.abs(V - U).max()
    out["max_abs_v_minus_u_m_s"] = float(off)
    out["max_flow_excess_rel"] = float((Qsum / Q_sup - 1.0).max())
    met = dem <= Q_sup * (1 + 1e-6)
    out["max_abs_v_minus_u_when_met_m_s"] = float(np.abs(V - U)[met].max()) if met.any() else None
    # E-1 by phase
    short = dem > Q_sup * (1 + 1e-6)
    for ph in sorted(set(d["phase"].tolist())):
        m = d["phase"] == ph
        out["phases"][ph] = {"duration_s": float(dt[m].sum()), "short_s": float(dt[m & short].sum()),
                             "max_deficit_L_min": float(max(0.0, (dem[m] - Q_sup).max()) * 6e4),
                             "gallery_bar_g": [float(pP[m].min() / 1e5), float(pP[m].max() / 1e5)]}
    # E-2 by leg and phase
    for i, leg in enumerate(LEGS):
        r = moving_ratio(t, V[:, i], U[:, i], p.v_max)
        row = {}
        for ph in sorted(set(d["phase"].tolist())):
            m = (d["phase"] == ph) & np.isfinite(r)
            if not m.any():
                continue
            low = m & (r < R_LIM)
            longest, run = 0.0, 0.0
            for flag, h in zip(low, dt):
                run = run + h if flag else 0.0
                longest = max(longest, run)
            row[ph] = {"min_r": float(r[m].min()), "longest_below_0p93_s": float(longest)}
        out["legs"][leg] = row
    # E-4
    group = residual_groups(Y, lim, E4_BAND_PA)
    orig = residual_groups(Y, lim, E4_BAND_ORIG_PA)
    sat = group >= 0

    def by_leg(g: np.ndarray) -> dict:
        times = defaultdict(float)
        for mask, h in zip(g[sat], dt[sat]):
            times["+".join(leg for i, leg in enumerate(LEGS) if mask >> i & 1)] += float(h)
        return dict(times)

    swaps = disjoint_changes(group)
    chain = chained_changes(group)
    sat_s = float(dt[sat].sum())
    out["sample_period_s"] = {"median": float(np.median(np.diff(t))), "min": float(np.diff(t).min()), "max": float(np.diff(t).max())}
    out["residual_leg_time_s"] = by_leg(group)
    out["residual_leg_time_s_band_0p01bar"] = by_leg(orig)
    out["swaps"] = int(len(swaps))  # criteria 7.3 rev. 3
    out["swap_rate_hz"] = float(len(swaps) / sat_s) if sat_s > 0 else 0.0
    out["swaps_max_in_1s"] = max_in_window(t, swaps)
    out["swaps_chained"] = int(len(chain))
    out["swaps_chained_max_in_1s"] = max_in_window(t, chain)
    out["label_changes_band_0p5bar"] = int(len(label_changes(group)))
    out["swaps_orig_band_0p01bar"] = int(len(label_changes(orig)))  # the count before rev. 3
    out["swap_rate_orig_hz"] = float(out["swaps_orig_band_0p01bar"] / sat_s) if sat_s > 0 else 0.0
    out["saturated_s"] = sat_s
    out["gallery_when_saturated_bar_g"] = [float(pP[sat].min() / 1e5), float(pP[sat].max() / 1e5)] if sat.any() else None
    return out


def run_one(case: Path) -> tuple[str, dict]:
    p = load_params()
    d = load(case)
    return case.name, {f"{eta:.2f}": run_case(d, p, eta) for eta in ETAS}


def write_e4_table(table: dict) -> None:
    with open(OUT_DIR / "e4_table.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["case", "eta_v", "sample_period_s", "saturated_s", "swaps_orig_0p01bar", "rate_orig_hz", "flag_orig", "label_changes_0p5bar",
                    "swaps_rev3", "rate_rev3_hz", "flag_rev3", "swaps_rev3_max_in_1s", "swaps_chained", "swaps_chained_max_in_1s", "gallery_min_bar_g", "gallery_max_bar_g"])
        for case, row in table.items():
            for eta in ("0.90", "0.85"):
                e = row[eta]
                gal = e["gallery_when_saturated_bar_g"] or [None, None]
                w.writerow([case, eta, e["sample_period_s"]["median"], e["saturated_s"], e["swaps_orig_band_0p01bar"], e["swap_rate_orig_hz"],
                            e["swap_rate_orig_hz"] > E4_FLAG_HZ, e["label_changes_band_0p5bar"], e["swaps"], e["swap_rate_hz"], e["swap_rate_hz"] > E4_FLAG_HZ,
                            e["swaps_max_in_1s"], e["swaps_chained"], e["swaps_chained_max_in_1s"], *gal])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        table = dict(ex.map(run_one, case_dirs()))
    for name, row in table.items():
        e90, e85 = row["0.90"], row["0.85"]
        print(f"{name[:34]:34s} on-off95 {row['0.95']['max_abs_v_minus_u_m_s']:.1e} sat90 {e90['saturated_s']:5.1f} sw {e90['swaps']:3d} "
              f"sat85 {e85['saturated_s']:5.1f} orig {e85['swaps_orig_band_0p01bar']:3d} label {e85['label_changes_band_0p5bar']:3d} sw {e85['swaps']:3d} "
              f"chain {e85['swaps_chained']:3d} dt {e85['sample_period_s']['median']:.4f} res85 {json.dumps({k: round(v, 1) for k, v in e85['residual_leg_time_s'].items()})}")
    (OUT_DIR / "record_share.json").write_text(json.dumps(table, indent=1), encoding="utf-8")
    write_e4_table(table)

    # compact tables
    def col(eta, fn):
        return [fn(table[c][eta]) for c in table]

    for eta in ("0.90", "0.85"):
        ph_short = defaultdict(list)
        for c in table:
            for ph, v in table[c][eta]["phases"].items():
                ph_short[ph].append((v["short_s"], v["max_deficit_L_min"]))
        print(eta, {ph: {"median_short_s": round(float(np.median([a for a, _ in x])), 2), "max_short_s": round(max(a for a, _ in x), 2),
                         "max_deficit": round(max(b for _, b in x), 2), "n": len(x)} for ph, x in ph_short.items()})
        print(" V-2 excess max", max(col(eta, lambda r: r["max_flow_excess_rel"])),
              " min r by leg", {leg: round(min(v["min_r"] for c in table for v in table[c][eta]["legs"][leg].values()), 3) for leg in LEGS},
              " longest<0.93", round(max(v["longest_below_0p93_s"] for c in table for leg in LEGS for v in table[c][eta]["legs"][leg].values()), 2))
        print(" E-4 flag rev3", sum(table[c][eta]["swap_rate_hz"] > E4_FLAG_HZ for c in table), "orig", sum(table[c][eta]["swap_rate_orig_hz"] > E4_FLAG_HZ for c in table),
              "max swaps", max(col(eta, lambda r: r["swaps"])), "max chained", max(col(eta, lambda r: r["swaps_chained"])))
    print("V-1 eta 0.95 max |v-u|", max(table[c]["0.95"]["max_abs_v_minus_u_m_s"] for c in table))


if __name__ == "__main__":
    main()
