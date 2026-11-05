"""R12 details for the M1b report: estimate tests with the event baseline removed, swallowed commands, LEVEL stuck after
the event, and the harness / Hopsan sink-law correction.

Usage (dynamics-dev): python -I analyze_m1b.py <hopsan t4 folder> <10 Hz series folder> > text
Output: m1b/analysis.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
PR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "pressure_review"
OUT = PR / "m1b"
D_MM, RAMP_S, TAU_V = 11.5, 2.0, 0.1
OFFSETS = (0.0, 0.025, 0.05, 0.075)
PLOT = ("OFF", "V1", "B1", "VR_c2_v1", "VN_c2_v1", "BL_v1", "VR_c2_v05", "VN_c2_v05", "BL_v05", "VR_c1_v1", "VR_rodonly")


def quintic(t):
    tau = np.clip(t / RAMP_S, 0.0, 1.0)
    return D_MM * tau**3 * (10.0 - 15.0 * tau + 6.0 * tau**2)


def linear(t):
    return D_MM * np.clip(t / RAMP_S, 0.0, 1.0)


def load(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def lagged(t10, c10, t):
    """Valve output on the 1 ms grid t for ZOH commands (one leg)."""
    u = np.zeros(len(t))
    idx = np.searchsorted(t10, t, side="right") - 1
    cmd = np.where(idx >= 0, c10[np.clip(idx, 0, len(c10) - 1)], 0.0)
    keep = np.exp(-np.diff(t, prepend=t[0]) / TAU_V)
    v = 0.0
    for k in range(len(t)):
        v = cmd[k] + (v - cmd[k]) * keep[k]
        u[k] = v
    return u


def main() -> None:
    hop_dir, ser_dir = Path(sys.argv[1]), Path(sys.argv[2])
    recs = {}
    for r in load(OUT / "r12.jsonl") + [x for x in load(OUT / "hash.jsonl") if not x["job"].get("twin")]:
        recs[(r["job"]["variant"], r["job"]["offset_s"])] = r
    result = {"estimates": {}, "stuck": {}, "sink": {}}
    for offset in OFFSETS:
        off = np.load(OUT / "series_r12" / f"R12_OFF_{offset}.npz")
        t = off["t"]
        k0 = int(np.searchsorted(t, 0.0))
        off_rr = (off["F"][:, 3] - off["F"][k0, 3]) / 1e3
        k_off = int(np.argmin(np.where((t >= 0) & (t <= 4), off["F"][:, 3], np.inf)))
        rec_off = recs[("OFF", offset)]
        t_ev = rec_off["t_event_s"]
        d10 = np.load(ser_dir / f"R12_OFF_{offset}.npz", allow_pickle=True)
        retract_cmd = np.flatnonzero((d10["t"] > t_ev) & ((d10["command"][:, 1] < -1e-6) | (d10["command"][:, 2] < -1e-6)))
        t_ret_off = float(d10["t"][retract_cmd[0]] - t_ev)
        row = {"t_FR_RL_retract_cmd_off_s": t_ret_off, "t_min_off_s": float(t[k_off]), "F_pre_off": np.round(off["F"][k0] / 1e3, 2).tolist(), "variants": {}}
        for name in PLOT:
            if name == "OFF":
                continue
            d = np.load(OUT / "series_r12" / f"R12_{name}_{offset}.npz")
            rec = recs[(name, offset)]
            n = min(len(t), len(d["t"]))
            k0v = int(np.searchsorted(d["t"], 0.0))
            rr = (d["F"][:, 3] - d["F"][k0v, 3]) / 1e3
            diff = rr[:n] - off_rr[:n]
            apart = np.flatnonzero((t[:n] > 0) & (np.abs(diff) > 0.5))
            k_min = int(np.argmin(np.where((d["t"] >= 0) & (d["t"] <= 4), d["F"][:, 3], np.inf)))
            t_ev_v = rec["t_event_s"]
            d10v = np.load(ser_dir / f"R12_{name}_{offset}.npz", allow_pickle=True)
            grid = np.arange(t_ev_v - 0.5, t_ev_v + float(t[k_off]), 1e-3)
            swallowed = {}
            delivered = d["v"]
            for i, leg in enumerate(("FL", "FR", "RL", "RR")):
                req = lagged(d10v["t"], d10v["command"][:, i], grid)
                keep = grid >= t_ev_v
                k1 = int(np.searchsorted(d["t"], t[k_off]))
                sel = (d["t"] >= 0) & (d["t"] <= t[k_off])
                swallowed[leg] = {"cmd_mm": round(float(np.sum(req[keep]) * 1e-3 * 1e3), 3), "delivered_mm": round(float(np.sum(delivered[sel, i]) * 1e-3 * 1e3), 3)}
            fills = [] if not rec["m1"] else [(round(f[0] - t_ev_v, 2), round(f[1] - t_ev_v, 2), ("FL", "FR", "RL", "RR")[f[2]], f[3], f[4], f[5], f[6]) for f in rec["m1"]["fills"] if f[1] > t_ev_v and f[0] < t_ev_v + 3.0]
            row["variants"][name] = {"t_apart_baseline_removed_s": float(t[apart[0]]) if apart.size else None, "RR_drop_pre_min_kN": round(float(rr[k_min]), 2), "RR_min": round(float(d["F"][k_min, 3] / 1e3), 2), "F_pre": np.round(d["F"][k0v] / 1e3, 2).tolist(), "t_min": round(float(d["t"][k_min]), 3), "swallowed_to_off_min": swallowed, "fills": fills[:10]}
        result["estimates"][str(offset)] = row
        print("offset", offset, "off min t", row["t_min_off_s"], "off F_pre", row["F_pre_off"], "first FR/RL retract cmd", t_ret_off)
        for name, v in row["variants"].items():
            print(" ", name, "RRmin", v["RR_min"], "t", v["t_min"], "pre", v["F_pre"][3], "drop", v["RR_drop_pre_min_kN"], "apart", v["t_apart_baseline_removed_s"], {k: (x["cmd_mm"], x["delivered_mm"]) for k, x in v["swallowed_to_off_min"].items()})
            if offset == 0.0:
                print("    fills", v["fills"])
    print("off RR drop", {o: round(float((np.load(OUT / 'series_r12' / f'R12_OFF_{o}.npz')['F'][:, 3].min() - np.load(OUT / 'series_r12' / f'R12_OFF_{o}.npz')['F'][int(np.searchsorted(np.load(OUT / 'series_r12' / f'R12_OFF_{o}.npz')['t'], 0.0)), 3]) / 1e3), 2) for o in OFFSETS})
    # stuck in LEVEL after the event
    for name in ("VR_c2_v05", "VR_c5_v1", "VN_c5_v05", "VN_c2_v1", "VR_c2_v1"):
        rec = recs[(name, 0.05)]
        ev = rec["t_event_s"]
        d = np.load(ser_dir / f"R12_{name}_0.05.npz", allow_pickle=True)
        tail = d["t"] > d["t"][-1] - 2.0
        mid = (d["t"] > ev + 10) & (d["t"] < ev + 12)
        info = {"final": rec["final_phase"], "back": rec["event_output"]["t_ready_back_s"], "run_after": rec["event_output"]["run_after_s"], "end": rec["state_at"]["end"], "cmd_tail_mm_s": np.round(d["command"][tail].mean(axis=0) * 1e3, 3).tolist(), "cmd_mid_mm_s": np.round(d["command"][mid].mean(axis=0) * 1e3, 3).tolist(), "filtered_tail_deg": np.round(d["filtered_deg"][tail].mean(axis=0), 4).tolist(), "hold": rec["m1"]["hold_s"], "phases": sorted(set(d["phase"][d["t"] > ev + 3].tolist())), "events": rec["events"][-6:]}
        result["stuck"][name] = info
        print("stuck", name, json.dumps(info)[:900])
    # sink law
    out = {}
    for offset, suffix in ((0.0, "0"), (0.025, "0.025"), (0.05, "0.05"), (0.075, "0.075")):
        h = np.load(OUT / "series_r12" / f"R12_OFF_{offset}.npz")
        t = h["t"]
        F = h["F"] / 1e3
        k0 = int(np.searchsorted(t, 0.0))
        first = float(t[(t > 0) & (np.abs(h["u"]).max(axis=1) > 1e-6)][0])
        free = (t >= 0) & (t <= first)
        row = {"first_cmd": first}
        for label, fn, hi in (("quintic_to_first_cmd", quintic, first), ("linear_to_first_cmd", linear, first), ("linear_to_min", linear, float(t[np.argmin(np.where(t >= 0, F[:, 3], np.inf))]))):
            sel = (t >= 0.1) & (t <= hi)
            row[label] = round(float(np.polyfit(fn(t[sel]), F[sel, 3], 1)[0]), 3)
        row["total_drop_over_linear_depth_at_min"] = round(float((F[k0, 3] - F[t >= 0, 3].min()) / linear(t[t >= 0][np.argmin(F[t >= 0, 3])])), 3)
        row["hopsan"] = {}
        for c in ("nocheck", "vent", "block"):
            d = np.load(hop_dir / f"{c}_OFF_{suffix}.npz")
            th, Fh = d["t"], d["F"] / 1e3
            j0 = int(np.searchsorted(th, 0.0))
            sel = (th >= 0.1) & (th <= first)
            kmin = int(np.argmin(np.where(th >= 0, Fh[:, 3], np.inf)))
            depth_gap = float(quintic(th[kmin]) - linear(th[kmin]))
            rate = float(-np.polyfit(linear(th[sel]), Fh[sel, 3], 1)[0])
            row["hopsan"][c] = {"rate_linear_kN_mm": round(rate, 3), "F_pre_RR": round(float(Fh[j0, 3]), 2), "RR_min": round(float(Fh[kmin, 3]), 2), "t_min": round(float(th[kmin]), 3),
                                "quintic_minus_linear_mm_at_tmin": round(depth_gap, 3), "corrected_RR_min": round(float(Fh[kmin, 3]) - rate * depth_gap, 2)}
        row["harness_RR_min"] = round(float(F[t >= 0, 3].min()), 2)
        row["harness_F_pre_RR"] = round(float(F[k0, 3]), 2)
        out[str(offset)] = row
        print("sink", offset, json.dumps(row))
    result["sink"] = out
    t4 = json.loads((PR / "m1_hopsan" / "t4_replay.json").read_text(encoding="utf-8"))
    table = []
    for r in t4:
        d = np.load(hop_dir / f"{r['name']}.npz")
        th, Fh = d["t"], d["F"] / 1e3
        kmin = int(np.argmin(np.where(th >= 0, Fh[:, 3], np.inf)))
        gap = float(quintic(th[kmin]) - linear(th[kmin]))
        table.append({"name": r["name"], "RR_min": round(float(Fh[kmin, 3]), 2), "t_min": round(float(th[kmin]), 3), "gap_mm": round(gap, 3), "corrected_6p9": round(float(Fh[kmin, 3]) - 6.9 * gap, 2), "RL": round(r["F_min_kN"]["RL"], 2), "FR": round(r["F_min_kN"]["FR"], 2)})
    result["t4_corrected"] = table
    for row in table:
        print(row)
    (OUT / "analysis.json").write_text(json.dumps(result, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
