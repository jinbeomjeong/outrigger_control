"""Creep-stop time under several definitions for the J1 B open-loop rows (V0, R sweep, v4).

Read-only: loads stored result.json + series.npz, writes JSON to argv[1].
Definitions (all: every pad, after crawler departure t_lo = stored P3a-2 t_liftoff_s):
  window W in {0.2, 1.0} s backward difference (time based, as run_S9.sinkage_rate),
  sign in {signed (+ = deeper) < 0.1 mm/s, two-sided |rate| < 0.1 mm/s},
  first = first time true, final = start of the last stretch that holds to the end (run_S9.creep_stop).
Also the rev52 rule (index based 200 rows, |rate|, time of last violating row) to reproduce 4.214 s.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

R = Path(r"C:\workspace\outrigger_control\07_results\S9")
ROWS = {
    "R300k": R / "batch_V5-OPENLOOP-R_20261108_231840/P3a_J1_B_V0_R300k",
    "R600k": R / "batch_V5-OPENLOOP-R_20261108_231840/P3a_J1_B_V0_R600k",
    "R888k": R / "batch_V5-OPENLOOP-R_20261108_231840/P3a_J1_B_V0_R888k",
    "V0_R992k": R / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0",
    "R1490k": R / "batch_V5-OPENLOOP-RFU_20261109_0100/P3a_J1_B_V0_R1490k",
    "v4_J1_B": R / "batch_P3a_20261026_092653/P3a_J1_B",
    "v4_J1_A": R / "batch_P3a_20261026_092653/P3a_J1_A",
    "v4_G1_B": R / "batch_P3a_20261026_092653/P3a_G1_B",
    "v4_G1_A": R / "batch_P3a_20261026_092653/P3a_G1_A",
}
LIMIT = 1.0e-4  # m/s
LEGS = ("FL", "FR", "RL", "RR")


def rate_time(t, s, w):
    """Backward difference over at least w seconds (copy of run_S9.sinkage_rate)."""
    j = np.searchsorted(t, t - w + 1e-9, side="right") - 1
    valid = j >= 0
    j = np.maximum(j, 0)
    r = np.full_like(s, np.nan)
    r[valid] = (s[valid] - s[j[valid]]) / (t[valid, None] - t[j[valid], None])
    return r


def first_final(t, ok, after):
    k = np.nonzero(ok)[0]
    if not k.size:
        return None, None
    if not ok[-1]:
        return float(t[k[0]]), None
    bad = np.nonzero(after & ~ok)[0]
    return float(t[k[0]]), (float(t[k[0]]) if not bad.size else float(t[bad[-1] + 1]))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


out = {}
for name, p in ROWS.items():
    res = json.loads((p / "result.json").read_text("utf-8"))
    z = np.load(p / "series.npz")
    t = z["t_s"]
    sk = z["pad_sinkage_geometric_m"]
    lo = float(res["p3a"]["P3a-2_liftoff"]["t_liftoff_s"])
    ilo = int(np.searchsorted(t, lo - 1e-9))
    row = {"npz_sha256": sha(p / "series.npz"), "t_liftoff_s": lo, "t_end_s": float(t[-1]),
           "dt_median_s": float(np.median(np.diff(t))), "stored_creep_stop": res["p3a"].get("creep_stop")}
    for w in (0.2, 1.0):
        r = rate_time(t, sk, w)
        valid = np.all(np.isfinite(r), axis=1)
        after = (t >= lo - 1e-12) & valid
        for tag, ok in (("signed", np.all(r < LIMIT, axis=1)), ("two_sided", np.all(np.abs(r) < LIMIT, axis=1))):
            f, fi = first_final(t, after & ok, after)
            key = f"W{w:g}_{tag}"
            d = {"first_after_lo_s": None if f is None else f - lo,
                 "final_after_lo_s": None if fi is None else fi - lo}
            # violation stretches between first and final (which pad, peak rate)
            if f is not None and fi is not None and fi > f + 1e-9:
                m = (t > f) & (t < fi) & after & ~(after & ok)
                rr = r[m]
                d["gap_rows"] = int(m.sum())
                d["gap_t_range_after_lo_s"] = [float(t[m][0] - lo), float(t[m][-1] - lo)]
                d["gap_peak_rate_mm_s"] = (np.nanmax(np.abs(rr), axis=0) * 1e3).tolist()
                d["gap_peak_signed_rate_mm_s"] = [float(rr[np.nanargmax(np.abs(rr[:, i])), i] * 1e3)
                                                  for i in range(4)]
                d["gap_violating_pads"] = [LEGS[i] for i in range(4)
                                           if np.any((rr[:, i] >= LIMIT) if tag == "signed" else
                                                     (np.abs(rr[:, i]) >= LIMIT))]
            # per-pad final (signed) for reference
            pp = []
            for i in range(4):
                oki = (r[:, i] < LIMIT) if tag == "signed" else (np.abs(r[:, i]) < LIMIT)
                _, fii = first_final(t, after & oki, after)
                pp.append(None if fii is None else fii - lo)
            d["per_pad_final_after_lo_s"] = dict(zip(LEGS, pp))
            row[key] = d
    # rev52 rule (index based, 200 rows, |rate|, last violating row time)
    kk = np.arange(ilo + 200, len(t))
    rates = np.abs(sk[kk] - sk[kk - 200]) / 0.2
    bad = np.nonzero(np.any(rates >= 1e-4, axis=1))[0]
    row["rev52_quiet_after_lo_s"] = float(t[kk[bad[-1]]] - lo) if bad.size else 0.0
    # creep amount and rate at +2/+4 s (1 s window, signed), RL
    r1 = rate_time(t, sk, 1.0)
    row["creep_after_lo_mm"] = ((sk[-1] - sk[ilo]) * 1e3).tolist()
    row["rate_1s_at_mm_s"] = {f"+{d:g}": (r1[int(np.searchsorted(t, lo + d - 1e-9))] * 1e3).tolist()
                              for d in (1.0, 2.0, 3.0, 4.0, 5.0)}
    # 2 Hz tail diagnostic: max |0.2 s rate| per pad in the last 10 s, and in [lo+4, lo+6]
    r02 = rate_time(t, sk, 0.2)
    m = t >= t[-1] - 10.0
    row["max_abs_rate_0p2s_last10s_mm_s"] = (np.nanmax(np.abs(r02[m]), axis=0) * 1e3).tolist()
    row["max_abs_rate_1s_last10s_mm_s"] = (np.nanmax(np.abs(r1[m]), axis=0) * 1e3).tolist()
    out[name] = row
    print(name, "lo", round(lo, 3),
          "W1 signed first/final", out[name]["W1_signed"]["first_after_lo_s"], out[name]["W1_signed"]["final_after_lo_s"],
          "W1 2s", out[name]["W1_two_sided"]["first_after_lo_s"], out[name]["W1_two_sided"]["final_after_lo_s"],
          "W0.2 2s", out[name]["W0.2_two_sided"]["first_after_lo_s"], out[name]["W0.2_two_sided"]["final_after_lo_s"],
          "rev52", round(out[name]["rev52_quiet_after_lo_s"], 3))
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=float), "utf-8")
print("ok")
