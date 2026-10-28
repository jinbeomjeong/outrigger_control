"""G6-0a: open-loop layout control of the G6 soil patch (dynamics / user decision 2026-10-28).

``run_S9.py machine`` with the P3a G1 B arguments and a G1 soil patch under RR (triple terrain, physics
unchanged) against the P3a G1 B run of the dual layout (``run_S9.G6_P3A_REFERENCE``). Criteria (patterned on
the dual-terrain equivalence E2-E4, ``dynamics_model.md`` 5.34.12 / 5.35.2):

  C-1 before the first pad contact (first 1 ms row with a pad SCM normal > 0 in either run): every float
      series of ``series.npz`` within 1e-12 relative (max |a - b| / max |a| over the rows before it; NaN at
      the same places)
  C-2 end (E3 type, last 0.1 s means): each pad normal rel <= 1e-6 or |diff| <= 0.01 sigma_bar h^2
      (sigma_bar h^2 = end pad normal / pad area x h^2, h = 0.02 m), normal sum rel <= 1e-6, crawler normal
      |diff| <= 0.01 x crawler node force (0.7 MPa x crawler grid^2, 5.35.2), body z |diff| <= 1 um, pitch
      |diff| <= 1e-5 deg
  C-3 instant (E4 type, dynamics_model.md 5.40.8): per pad max |diff| <= maximum node pressure x h^2; the
      machine series has no node-pressure record, so max <= 1.05 sigma_bar h^2 with the event width <= 2 rows
      (rows with |diff| > 0.5 sigma_bar h^2) and the pad position (geometric sinkage) difference <= 1 um on
      those rows; an event pad (max >= 0.01 sigma_bar h^2) ends with the 0.1 s mean end diff <= 0.01 sigma_bar
      h^2 or end / max <= 1/100 (the last instantaneous row is not used); small-force pads (max < 0.1
      sigma_bar h^2): 0.1 s mean end diff <= 0.01 sigma_bar h^2
  C-4 P3a-1 ... P3a-7: the P3a checks equal, lift-off within 2 ms, force peaks within sigma_bar h^2, stroke
      maxima within 0.1 mm, sinkage at lift-off / end within 0.1 mm, attitude ranges (d roll / d pitch
      min-max) within 2e-3 deg, end attitude (end roll / pitch) within 1e-3 deg

C-1 ... C-4 values: dynamics_model.md 5.40.5 (confirmed 2026-10-28).

Usage (Chrono-dev, project root)::

    python -I -X utf8 -u 04_scripts/02_chrono/s9_g6_patch_compare.py <G6-0a case folder> [<reference folder>] [--json out]

Units SI (kN / mm / deg where named).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REFERENCE = ROOT / "07_results/S9/batch_P3a_20261026_092653/P3a_G1_B"
PRE_REL = 1.0e-12
END_REL = 1.0e-6
NODE_FRACTION = 0.01
SMALL_FRACTION = 0.1
PAD_GRID_M = 0.02
CRAWLER_GRID_M = 0.04
CRAWLER_SIGMA_MAX_PA = 0.7e6
END_WINDOW_S = 0.1
MAX_FALLBACK_FACTOR = 1.05
SPIKE_WIDTH_MAX = 2
POSITION_DIFF_MAX_M = 1.0e-6
"""C-3 without a node-pressure record (dynamics_model.md 5.40.8)."""
SPIKE_FRACTION = 0.5
"""Rows counted in the event width: |diff| > 0.5 sigma_bar h^2 (counting threshold of this script; a one-node
flip is about one sigma_bar h^2)."""


def _max_run(flag: np.ndarray) -> int:
    best = run = 0
    for on in flag:
        run = run + 1 if on else 0
        best = max(best, run)
    return int(best)
TOL = {"liftoff_s": 2.0e-3, "stroke_m": 1.0e-4, "sinkage_m": 1.0e-4, "attitude_range_deg": 2.0e-3,
       "attitude_end_deg": 1.0e-3}
"""C-4 tolerances, dynamics_model.md 5.40.5 (2026-10-28); force peaks within sigma_bar h^2."""
LEGS = ("FL", "FR", "RL", "RR")


def load(case_dir: Path) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    z = np.load(Path(case_dir) / "series.npz")
    return {k: z[k] for k in z.files}, json.loads((Path(case_dir) / "result.json").read_text("utf-8"))


def first_contact_row(a: dict[str, np.ndarray], b: dict[str, np.ndarray]) -> int:
    n = min(len(a["t_s"]), len(b["t_s"]))
    hit = (np.asarray(a["scm_pad_normal_N"])[:n] > 0.0).any(axis=1) | (np.asarray(b["scm_pad_normal_N"])[:n] > 0.0).any(axis=1)
    return int(np.argmax(hit)) if hit.any() else n


def pre_contact(a, b, k_hit: int) -> dict[str, Any]:
    """C-1: per float series of the same row count, max relative difference before row ``k_hit``."""
    out: dict[str, Any] = {}
    worst = 0.0
    ok = True
    for key in sorted(set(a) & set(b)):
        x, y = np.asarray(a[key]), np.asarray(b[key])
        if x.shape[:1] != a["t_s"].shape or y.shape[:1] != b["t_s"].shape or not np.issubdtype(x.dtype, np.number):
            continue
        x, y = x[:k_hit].astype(float), y[:k_hit].astype(float)
        if x.size == 0:
            continue
        nan_same = bool(np.array_equal(np.isnan(x), np.isnan(y)))
        f = ~np.isnan(x) & ~np.isnan(y)
        scale = float(np.abs(x[f]).max()) if f.any() else 0.0
        d = float(np.abs(x[f] - y[f]).max()) if f.any() else 0.0
        r = 0.0 if d == 0.0 else d / max(scale, 1e-300)
        out[key] = {"max_rel": r, "nan_same": nan_same}
        worst = max(worst, r)
        ok = ok and nan_same and r <= PRE_REL
    return {"rows_before_contact": k_hit, "series": out, "max_rel": worst, "pass": bool(ok),
            "criterion": f"every float series rel <= {PRE_REL:g} before the first pad contact, NaN at the same rows"}


def node_forces_N(a, area_m2, h=PAD_GRID_M) -> list[float]:
    t = np.asarray(a["t_s"], float)
    w = t >= t[-1] - END_WINDOW_S - 1e-12
    n = np.asarray(a["scm_pad_normal_N"], float)
    return [float(abs(n[w, i].mean()) / float(area_m2[leg]) * h * h) for i, leg in enumerate(LEGS)]


def end_and_instant(a, b, area_m2) -> dict[str, Any]:
    """C-2 and C-3 (``a`` = G6-0a, ``b`` = reference)."""
    t = np.asarray(b["t_s"], float)
    n_rows = min(len(a["t_s"]), len(b["t_s"]))
    t = t[:n_rows]
    w = t >= t[-1] - END_WINDOW_S - 1e-12
    pa, pb = np.asarray(a["scm_pad_normal_N"], float)[:n_rows], np.asarray(b["scm_pad_normal_N"], float)[:n_rows]
    nf = node_forces_N({"t_s": t, "scm_pad_normal_N": pb}, area_m2)

    def rel(x, y):
        return float(abs(x - y) / max(abs(y), 1e-30))

    pads = []
    for i, leg in enumerate(LEGS):
        e_a, e_b = float(pa[w, i].mean()), float(pb[w, i].mean())
        df = np.abs(pa[:, i] - pb[:, i])
        mx, end = float(df.max()), float(df[-1])
        p = {"leg": leg, "end_rel": rel(e_a, e_b), "end_diff_N": abs(e_a - e_b), "node_force_N": nf[i],
             "max_diff_N": mx, "t_max_s": float(t[int(np.argmax(df))]), "last_diff_N": end}
        p["pass_end"] = bool(p["end_rel"] <= END_REL or p["end_diff_N"] <= NODE_FRACTION * nf[i])
        # C-3 (dynamics_model.md 5.40.8): max <= max node pressure x h^2; without a node-pressure record
        # max <= 1.05 sigma_bar h^2 with event width <= 2 rows and the pad position difference <= 1 um on those
        # rows; the end of an event pad is the 0.1 s mean end difference (not the last instantaneous row)
        p["small_force"] = bool(mx < SMALL_FRACTION * nf[i])
        p["event"] = bool(mx >= NODE_FRACTION * nf[i])
        spike = df > SPIKE_FRACTION * nf[i]
        p["spike_rows"] = int(spike.sum())
        p["spike_width_rows_max"] = _max_run(spike)
        za_p = np.asarray(a.get("pad_sinkage_geometric_m", np.zeros((len(a["t_s"]), 4))), float)[:n_rows, i]
        zb_p = np.asarray(b.get("pad_sinkage_geometric_m", np.zeros((len(b["t_s"]), 4))), float)[:n_rows, i]
        p["position_diff_at_spikes_m"] = float(np.abs(za_p[spike] - zb_p[spike]).max()) if spike.any() else 0.0
        p["max_basis"] = f"{MAX_FALLBACK_FACTOR:g} sigma_bar h^2 (no node-pressure record), width <= {SPIKE_WIDTH_MAX} rows"
        p["max_limit_N"] = MAX_FALLBACK_FACTOR * nf[i]
        p["pass_max"] = bool(mx <= p["max_limit_N"] and p["spike_width_rows_max"] <= SPIKE_WIDTH_MAX
                             and p["position_diff_at_spikes_m"] <= POSITION_DIFF_MAX_M)
        end_mean = p["end_diff_N"]
        if p["small_force"]:
            p["pass_end_c3"] = bool(end_mean <= NODE_FRACTION * nf[i])
        else:
            p["pass_end_c3"] = bool(not p["event"] or end_mean <= NODE_FRACTION * nf[i]
                                    or (mx > 0 and end_mean / mx <= 1e-2))
        p["end_over_max"] = end_mean / mx if mx > 0 else 0.0
        p["pass_instant"] = bool(p["pass_max"] and p["pass_end_c3"])
        pads.append(p)
    ca, cb = np.asarray(a["scm_crawler_normal_N"], float)[:n_rows], np.asarray(b["scm_crawler_normal_N"], float)[:n_rows]
    crawler_nf = CRAWLER_SIGMA_MAX_PA * CRAWLER_GRID_M ** 2
    sum_a, sum_b = ca + pa.sum(axis=1), cb + pb.sum(axis=1)
    za, zb = np.asarray(a["body_pos_m"], float)[:n_rows, 2], np.asarray(b["body_pos_m"], float)[:n_rows, 2]
    rpa, rpb = np.asarray(a["roll_pitch_deg"], float)[:n_rows], np.asarray(b["roll_pitch_deg"], float)[:n_rows]
    c2 = {"pads": pads, "normal_sum_rel": rel(float(sum_a[w].mean()), float(sum_b[w].mean())),
          "crawler_end_diff_N": float(abs(ca[w].mean() - cb[w].mean())), "crawler_node_force_N": crawler_nf,
          "z_end_diff_m": float(abs(za[w].mean() - zb[w].mean())),
          "pitch_end_diff_deg": float(abs(rpa[w, 1].mean() - rpb[w, 1].mean()))}
    c2["pass"] = bool(all(p["pass_end"] for p in pads) and c2["normal_sum_rel"] <= END_REL
                      and c2["crawler_end_diff_N"] <= NODE_FRACTION * crawler_nf and c2["z_end_diff_m"] <= 1e-6
                      and c2["pitch_end_diff_deg"] <= 1e-5)
    c3 = {"pads": [{k: p[k] for k in ("leg", "max_diff_N", "t_max_s", "last_diff_N", "end_diff_N", "end_over_max",
                                      "node_force_N", "max_limit_N", "max_basis", "event", "small_force",
                                      "spike_rows", "spike_width_rows_max", "position_diff_at_spikes_m",
                                      "pass_max", "pass_end_c3", "pass_instant")} for p in pads],
          "criterion": "dynamics_model.md 5.40.8: max <= max node pressure h^2 (fallback 1.05 sigma_bar h^2, event "
                       "width <= 2 rows, pad position diff <= 1 um on those rows); event pad end: 0.1 s mean end "
                       "diff <= 0.01 sigma_bar h^2 or end / max <= 1/100",
          "pass": bool(all(p["pass_instant"] for p in pads))}
    return {"C-2": c2, "C-3": c3, "rows_compared": int(n_rows)}


def p3a_agreement(pa: dict[str, Any], pb: dict[str, Any], node_force_N: list[float]) -> dict[str, Any]:
    """C-4 on the ``p3a`` blocks (``pa`` = G6-0a, ``pb`` = reference)."""
    out: dict[str, Any] = {}
    ca, cb = pa.get("checks") or {}, pb.get("checks") or {}
    keys = sorted(k for k in set(ca) | set(cb) if k.startswith("P3a-"))
    out["checks_equal"] = {k: ca.get(k) == cb.get(k) for k in keys}
    la, lb = (pa.get("P3a-2_liftoff") or {}).get("t_liftoff_s"), (pb.get("P3a-2_liftoff") or {}).get("t_liftoff_s")
    out["liftoff_diff_s"] = None if la is None or lb is None else abs(la - lb)
    fa = np.asarray((pa.get("P3a-1_force_peak") or {}).get("F_peak_N", [math.nan] * 4), float)
    fb = np.asarray((pb.get("P3a-1_force_peak") or {}).get("F_peak_N", [math.nan] * 4), float)
    out["force_peak_diff_N"] = np.abs(fa - fb).tolist()
    sa = np.asarray((pa.get("P3a-4_stroke") or {}).get("s_motor_max_m", [math.nan] * 4), float)
    sb = np.asarray((pb.get("P3a-4_stroke") or {}).get("s_motor_max_m", [math.nan] * 4), float)
    out["stroke_max_diff_m"] = np.abs(sa - sb).tolist()
    sink = {}
    for key in ("geometric_at_liftoff_m", "geometric_end_m"):
        xa = np.asarray((pa.get("P3a-6_sinkage") or {}).get(key, [math.nan] * 4), float)
        xb = np.asarray((pb.get("P3a-6_sinkage") or {}).get(key, [math.nan] * 4), float)
        sink[key] = np.abs(xa - xb).tolist()
    out["sinkage_diff_m"] = sink
    att = {}
    for key in ("d_roll_range_deg", "d_pitch_range_deg"):
        xa = np.asarray((pa.get("P3a-7_attitude") or {}).get(key, [math.nan] * 2), float)
        xb = np.asarray((pb.get("P3a-7_attitude") or {}).get(key, [math.nan] * 2), float)
        att[key] = np.abs(xa - xb).tolist()
    out["attitude_diff_deg"] = att
    ea = np.asarray((pa.get("P3a-7_attitude") or {}).get("end_roll_pitch_deg", [math.nan] * 2), float)
    eb = np.asarray((pb.get("P3a-7_attitude") or {}).get("end_roll_pitch_deg", [math.nan] * 2), float)
    out["end_attitude_diff_deg"] = np.abs(ea - eb).tolist()
    ok = (all(out["checks_equal"].values()) and out["liftoff_diff_s"] is not None
          and out["liftoff_diff_s"] <= TOL["liftoff_s"] + 1e-9
          and all(d <= f for d, f in zip(out["force_peak_diff_N"], node_force_N, strict=True))
          and max(out["stroke_max_diff_m"]) <= TOL["stroke_m"]
          and all(max(v) <= TOL["sinkage_m"] for v in sink.values())
          and all(max(v) <= TOL["attitude_range_deg"] for v in att.values())
          and max(out["end_attitude_diff_deg"]) <= TOL["attitude_end_deg"])
    out["pass"] = bool(ok)
    out["tolerances"] = dict(TOL)
    out["criterion"] = ("P3a checks equal, lift-off within 2 ms, force peaks within sigma_bar h^2, stroke max / "
                        "sinkage within 0.1 mm, attitude ranges within 2e-3 deg, end attitude within 1e-3 deg "
                        "(dynamics_model.md 5.40.5)")
    return out


def compare(case_dir: Path, ref_dir: Path = REFERENCE) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "03_src"))
    from outrigger_sim.pad_variants import pad_variant_meta

    a, ra = load(case_dir)
    b, rb = load(ref_dir)
    area = pad_variant_meta("dwg_rear250")["pad_bottom_area_m2"]
    k_hit = first_contact_row(a, b)
    res: dict[str, Any] = {"case": str(case_dir), "reference": str(ref_dir),
                           "layout": {"case": (ra.get("meta") or {}).get("terrain_layout"),
                                      "reference": (rb.get("meta") or {}).get("terrain_layout")},
                           "fingerprints_equal": {k: (ra.get("meta") or {}).get(k) == (rb.get("meta") or {}).get(k)
                                                  for k in ("params_sha256", "scm_run_sha256")},
                           "t_first_contact_s": float(np.asarray(b["t_s"])[min(k_hit, len(b["t_s"]) - 1)])}
    res["C-1"] = pre_contact(a, b, k_hit)
    res.update(end_and_instant(a, b, area))
    nf = node_forces_N(b, area)
    res["C-4"] = p3a_agreement(ra.get("p3a") or {}, rb.get("p3a") or {}, nf)
    res["pass_all"] = bool(all(res[k]["pass"] for k in ("C-1", "C-2", "C-3", "C-4"))
                           and all(res["fingerprints_equal"].values()))
    return res


def main(argv) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("case")
    ap.add_argument("reference", nargs="?", default=str(REFERENCE))
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    res = compare(Path(a.case), Path(a.reference))
    out = Path(a.json) if a.json else Path(a.case) / "g6_0a_compare.json"
    out.write_text(json.dumps(res, indent=1, default=float), "utf-8")
    print(json.dumps({k: res[k]["pass"] for k in ("C-1", "C-2", "C-3", "C-4")} | {"pass_all": res["pass_all"]}))
    print("->", out)


if __name__ == "__main__":
    main(sys.argv[1:])
