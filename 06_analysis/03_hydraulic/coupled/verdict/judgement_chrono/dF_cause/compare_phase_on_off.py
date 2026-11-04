"""Compare on and off distributions under the same approach-phase perturbation (R4, R9).

Pairs are matched by eps. eps = 0 of the on side comes from the stored-hash run in zero-perturbation
form (sync2 stage 0, c = 1), because phase_on.json holds eps > 0 only. Same eps does not mean same
contact phase: the on run reaches contact 1.4-1.8 s later, so the pairing is only a labelling and the
unpaired comparison is the main one. Exact permutation test on the mean, Hodges-Lehmann shift.
Read only. Writes phase_on_off_compare.json.

Run: conda run -n dynamics-dev python -I compare_phase_on_off.py
"""
from __future__ import annotations

import ctypes
import itertools
import json
from ctypes import wintypes
from pathlib import Path

import numpy as np

kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.GetCurrentProcess.restype = wintypes.HANDLE
kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), 0x0C000000)

HERE = Path(__file__).resolve().parent
NRL = -0.5228340347436333
EPS = (0.0, 2.5e-4, 5e-4, 1e-3, 1.5e-3, 2e-3, 3e-3, 4e-3)
METRICS = ("F_min", "F_RL_min_first8", "mean1s_RL_min", "F_RL_win", "D_te", "D_lift", "tau_te", "base_RL", "t_ready")


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def base(rec):
    rec = dict(rec)
    rec["base_RL"] = rec["F_RL_win"] - NRL * rec["D_lift"]
    return rec


phase_on = [base(r) for r in load("phase_on.json")]
phase_off = [base(r) for r in load("phase_off.json")]
sync = [base(r) for r in load("sync2.json")]
report = {"n_phase_on_records": len(phase_on), "cases_on": sorted({r["job"]["case"] for r in phase_on}),
          "eps_on": sorted({r["job"].get("eps") for r in phase_on})}
for case in ("R4", "R9"):
    on = [r for r in phase_on if r["job"]["case"] == case]
    zero = [r for r in sync if r["job"]["case"] == case and r["job"]["eta"] == 0.85 and r["job"]["stage"] == 0]
    on_all = sorted(on + zero, key=lambda r: r["job"].get("eps", 0.0))
    off = sorted((r for r in phase_off if r["job"]["case"] == case), key=lambda r: r["job"]["eps"])
    block = {"n_on": len(on_all), "n_off": len(off), "rows_on": [], "rows_off": []}
    for label, rows in (("rows_on", on_all), ("rows_off", off)):
        for r in rows:
            block[label].append({"eps": r["job"].get("eps", 0.0), **{m: round(r[m], 3) for m in METRICS}, "leg": r["leg"],
                                 "lift_after_te": round(r["lift_after_te"], 3), "final_phase": r["final_phase"]})
    for m in METRICS:
        a = np.array([r[m] for r in on_all], float)
        b = np.array([r[m] for r in off], float)
        pooled = np.concatenate([a, b])
        observed = a.mean() - b.mean()
        stats = []
        for idx in itertools.combinations(range(len(pooled)), len(a)):
            mask = np.zeros(len(pooled), bool)
            mask[list(idx)] = True
            stats.append(pooled[mask].mean() - pooled[~mask].mean())
        stats = np.array(stats)
        p = float(np.mean(np.abs(stats) >= abs(observed) - 1e-12))
        walsh = (a[:, None] - b[None, :]).ravel()
        block[m] = {"on_mean": float(a.mean()), "on_min": float(a.min()), "on_max": float(a.max()), "on_std": float(a.std(ddof=1)),
                    "off_mean": float(b.mean()), "off_min": float(b.min()), "off_max": float(b.max()), "off_std": float(b.std(ddof=1)),
                    "on_unique": len(set(np.round(a, 1))), "off_unique": len(set(np.round(b, 1))),
                    "shift_mean": float(observed), "shift_median": float(np.median(a) - np.median(b)),
                    "hodges_lehmann": float(np.median(walsh)), "perm_p_two_sided": p, "perm_count": len(stats)}
    report[case] = block
    print(case, "n_on", len(on_all), "n_off", len(off))
    for side in ("rows_on", "rows_off"):
        print(" ", side)
        for row in block[side]:
            print("   ", row)
    for m in METRICS:
        print(" ", m, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in block[m].items()})
(HERE / "phase_on_off_compare.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
