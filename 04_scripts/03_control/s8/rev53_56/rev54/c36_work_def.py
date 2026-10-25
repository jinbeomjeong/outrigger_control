"""Compare twist-work judge definitions on recorded runs (read only).

Usage: python -I c36_work_def.py <out_json> <case_dir> [<case_dir> ...]
Per case: original rev. 52 bin work (twist_work_bins definition), detrended (oscillatory) work
with a centred moving average of length T_MA, late start counts, settle ramp end.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter1d

N_TW = np.array([0.5, -0.5, -0.5, 0.5])
BIN = 0.5
AFTER = 1.5
SPAN = 8.0
T_MAS = (1.0, 1.5, 2.0)


def ma(x, n):
    return uniform_filter1d(x, size=n, mode="nearest")


def analyse(case: Path):
    res = json.loads((case / "result.json").read_text(encoding="utf-8"))
    t_ev = res.get("event_t_s")
    if t_ev is None:
        return None
    t_ev = float(t_ev)
    ep = res.get("episode") or {}
    pads = np.load(case / "pads.npz", allow_pickle=True)
    rec = np.load(case / "record" / "record.npz", allow_pickle=True)
    tp = np.asarray(pads["t"], float)
    m = (tp >= t_ev - 0.5 - 1.5) & (tp <= t_ev + SPAN + 1.5)
    t = tp[m] - t_ev
    f = np.asarray(pads["F_cyl"], float)[m]
    d = (f[:, 0] + f[:, 3]) - (f[:, 1] + f[:, 2])
    pre = (t < 0) & (t >= -0.5)
    d0 = float(np.median(d[pre])) if pre.any() else 0.0
    tr = np.asarray(rec["t"], float) - t_ev
    utw = np.asarray(rec["u_applied"], float) @ N_TW
    j = np.clip(np.searchsorted(tr, t, side="right") - 1, 0, tr.size - 1)
    u = utw[j]
    dt = 1e-3
    out = {"case": case.name, "kind": ep.get("kind"), "leg": ep.get("leg"),
           "depth_mm": None if ep.get("depth_m") is None else 1e3 * ep["depth_m"],
           "ramp_s": ep.get("ramp_s"), "t_end_rel": float(t[-1])}
    sel = (t >= 0) & (t <= SPAN)
    edges = np.arange(0.0, min(SPAN, float(t[-1])) - 1e-9, BIN)

    def bins(p):
        return [float(np.sum(p[(t >= a) & (t < a + BIN) & sel]) * dt) for a in edges]

    p0 = 0.5 * (d - d0) * u
    b0 = bins(p0)
    out["orig_bins"] = [round(x, 1) for x in b0]
    late = [w for a, w in zip(edges, b0) if a >= AFTER - 1e-9]
    out["orig_max_after"] = max(late) if late else None
    for T in T_MAS:
        n = int(round(T / dt))
        dd = (d - d0) - ma(d - d0, n)
        uu = u - ma(u, n)
        p = 0.5 * dd * uu
        b = bins(p)
        lt = [w for a, w in zip(edges, b) if a >= AFTER - 1e-9]
        out[f"osc{T:g}_bins"] = [round(x, 1) for x in b]
        out[f"osc{T:g}_max_after"] = max(lt) if lt else None
        # net oscillatory work over [1.5, 8] s
        wsel = (t >= AFTER) & (t <= SPAN)
        out[f"osc{T:g}_net_after"] = float(np.sum(p[wsel]) * dt)
        # 2 s sliding net (step 0.5 s)
        w2 = []
        for a in np.arange(AFTER, min(SPAN, float(t[-1])) - 2.0 + 1e-9, 0.5):
            w2.append(float(np.sum(p[(t >= a) & (t < a + 2.0)]) * dt))
        out[f"osc{T:g}_net2s_max"] = max(w2) if w2 else None
    # quasi-static share in the worst original bin
    ev = json.loads((case / "controller_events.json").read_text(encoding="utf-8"))
    starts, ends = [], []
    for e in ev:
        s = str(e)
        ts = float(s.split("t_s=")[1].split(",")[0]) - t_ev
        name = s.split("name='")[1].rstrip("')")
        if name.startswith("leg_reapproach_start:") and ts >= -1e-6:
            starts.append([round(ts, 2), name.split(":")[1]])
        elif name.startswith(("leg_reapproach_contact:", "leg_reapproach_no_contact:",
                              "leg_reapproach_end:", "leg_reapproach_phase:")) and ts >= -1e-6:
            ends.append([round(ts, 2), name.split(":")[1]])
    out["reapp_starts"] = starts
    out["reapp_ends"] = ends
    out["starts_after_1.5"] = sum(1 for s in starts if s[0] > AFTER + 1e-9)
    # twist excursion: rocking amplitude of detrended D after 1.5 s
    dd15 = (d - d0) - ma(d - d0, 1500)
    w = (t >= AFTER) & (t <= SPAN)
    out["osc_D_pp_kN_after"] = float((dd15[w].max() - dd15[w].min()) / 1e3) if w.any() else None
    return out


def main():
    outp = Path(sys.argv[1])
    rows = []
    cases = []
    for a in sys.argv[2:]:
        pa = Path(a)
        if (pa / "result.json").exists():
            cases.append(pa)
        else:
            cases.extend(sorted(q for q in pa.iterdir() if (q / "result.json").exists()))
    for c in cases:
        try:
            r = analyse(Path(c))
        except Exception as exc:  # noqa: BLE001
            r = {"case": Path(c).name, "error": repr(exc)}
        if r is not None:
            rows.append(r)
    outp.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    keys = ["orig_max_after", "osc1_max_after", "osc1.5_max_after", "osc2_max_after",
            "osc1.5_net_after", "osc1.5_net2s_max", "starts_after_1.5", "osc_D_pp_kN_after"]
    print("case kind leg depth ramp | " + " ".join(keys))
    for r in rows:
        if "error" in r:
            print(r["case"], r["error"])
            continue
        vals = " ".join(f"{r[k]:7.1f}" if isinstance(r[k], float) else f"{r[k]!s:>7}" for k in keys)
        print(f"{r['case']:<12} {r['kind']:<8} {r['leg']!s:<3} {r['depth_mm'] or 0:5.1f} "
              f"{r['ramp_s'] or 0:5.2f} | {vals}")


if __name__ == "__main__":
    main()
