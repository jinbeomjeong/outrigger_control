"""Tables of the asym runs, same definitions as dF_cause/decompose.py chrono(). Read only.

Usage: python -I analyze.py <out dir>   (run folders found under ./runs/batch_*/<id>)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1])
ROOT = Path(r"C:\workspace\outrigger_control")
S8 = ROOT / "07_results" / "S8"
STORED_OFF = S8 / "final_A_bottom_rpB_Fs0_20261031_011936" / "A_bottom_rpB_Fs0"
STORED_ON = S8 / "coupled_eta085_A_bottom_rpB_Fs0_20261104_144431" / "A_bottom_rpB_Fs0"
DF = ROOT / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/dF_cause"
LEGS = ("FL", "FR", "RL", "RR")
N = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
WIN = 0.4
T_END = 40.0
"""All rows are cut at this time after the settle (the runs end there)."""


def mov(x, n):
    return np.convolve(x, np.ones(n) / n, "valid")


def metrics(d: Path) -> dict:
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    p = np.load(d / "pads.npz", allow_pickle=False)
    rec = np.load(d / "record" / "record.npz", allow_pickle=False)
    s8 = np.load(d / "r8_series.npz", allow_pickle=False)
    off = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    t, F, Fm = p["t"] - off, p["F_cyl"] / 1e3, p["F_cyl_min_interval"] / 1e3
    s = p["s_motor"] * 1e3
    crt, crf = rec["t"] - off, np.linalg.norm(rec["F_crawler"], axis=1) / 1e3
    pt = s8["t"] - off
    te = float(pt[np.flatnonzero(~np.isin(s8["phase"], ("idle", "check", "touch")))[0]])
    W = float(np.median(F[(t > te - 8) & (t < te - 6)].sum(axis=1)) + np.median(crf[(crt > te - 8) & (crt < te - 6)]))
    sm = np.convolve(F.sum(axis=1), np.ones(20) / 20, "same")
    tl = float(t[np.flatnonzero((t > te) & (W - sm < 3.0))[0]])
    tz = float(crt[(crf == 0.0) & (crt > te)][0])
    ke, kl = int(np.searchsorted(t, te)), int(np.searchsorted(t, tl))
    k8 = int(np.searchsorted(t, tl + 8.0))
    kz = int(np.searchsorted(t, tz))
    kend = int(np.searchsorted(t, T_END))
    F0 = np.median(F[(t > te - 8) & (t < te - 6)], axis=0)
    first = [int(np.argmax(F[:, i] > F0[i] + 3.0)) for i in range(4)]
    after = Fm[kz:kend]
    i, j = np.unravel_index(int(np.argmin(after)), after.shape)
    touched = np.asarray(s8["touched"], bool)
    latch = [float(pt[np.argmax(touched[:, q])] - te) for q in range(4)]
    s_contact = [float(s[first[q], q]) for q in range(4)]
    tau_contact = float(N @ np.array(s_contact))
    return {
        "t_te_s": te, "t_lift_s": tl, "lift_after_te_s": tl - te, "t_zero10Hz_s": tz,
        "ready_s": res.get("ready_t_s"), "end_s": float(res["s8_end"]["end_t_s"]),
        "tau_te_mm": float(N @ s[ke]), "tau_lift_mm": float(N @ s[kl]),
        "tau_contact_mm": tau_contact, "tau_te_rel_contact_mm": float(N @ s[ke]) - tau_contact,
        "s_te_mm": [float(v) for v in s[ke]],
        "s_contact_mm": s_contact,
        "t_contact_rel_te_s": [float(t[q] - te) for q in first],
        "gap_LR_front_mm": s_contact[0] - s_contact[1], "gap_LR_rear_mm": s_contact[2] - s_contact[3],
        "latch_rel_te_s": latch,
        "D_te_kN": float(F[ke - 200:ke].mean(axis=0) @ N),
        "D_win_kN": float(F[kl:kl + int(WIN * 1000)].mean(axis=0) @ N),
        "F_win_kN": [float(v) for v in F[kl:kl + int(WIN * 1000)].mean(axis=0)],
        "F_RL_win_kN": float(F[kl:kl + int(WIN * 1000), 2].mean()),
        "F_RL_raw_8_kN": float(Fm[kl:k8, 2].min()),
        "F_RL_20ms_8_kN": float(mov(F[kl:k8, 2], 20).min()),
        "F_RL_1s_8_kN": float(mov(F[kl:k8, 2], 1000).min()),
        "F_min_after_lift_kN": float(after[i, j]), "F_min_leg": LEGS[j],
        "t_min_rel_lift_s": float(t[kz + i] - tl),
        "crawler_te_kN": float(W - F[ke - 20:ke].sum(axis=1).mean()),
        "D_after_lift_kN": {f"{o:g}": float(F[int(np.searchsorted(t, tl + o)) - 250:int(np.searchsorted(t, tl + o)) + 250].mean(axis=0) @ N)
                            for o in (1.0, 2.0, 3.5, 4.0, 6.0, 8.0, 12.0, 15.0)},
        "F_after_lift_3p5_kN": [float(v) for v in F[int(np.searchsorted(t, tl + 3.5)) - 250:int(np.searchsorted(t, tl + 3.5)) + 250].mean(axis=0)],
        "phase_end": str(s8["phase"][-1]),
        "W_kN": W,
        "us_per_step": (res.get("runner") or {}).get("us_per_step"),
        "offsets_mm": None if not (res.get("asym") or {}).get("pad_gap_offsets_m") else
        [1e3 * v for v in res["asym"]["pad_gap_offsets_m"]],
    }


def bit_compare(run: Path, stored: Path) -> dict:
    """Exact comparison up to the shorter record for every array of the three npz files."""
    out = {}
    for rel in ("pads.npz", "r8_series.npz", "s8_series.npz", "record/record.npz"):
        a, b = np.load(run / rel, allow_pickle=False), np.load(stored / rel, allow_pickle=False)
        bad, n_arr, n_val = [], 0, 0
        for k in a.keys():
            if k not in b or a[k].dtype.kind not in "fiub" or a[k].ndim == 0:
                continue
            n = min(len(a[k]), len(b[k]))
            x, y = a[k][:n], b[k][:n]
            n_arr += 1
            n_val += x.size
            if x.shape != y.shape or not np.array_equal(x, y, equal_nan=x.dtype.kind == "f"):
                bad.append(k)
        out[rel] = {"arrays": n_arr, "values": n_val, "different": bad, "samples_run": len(a["t"]) if "t" in a else None}
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = {"stored_off": metrics(STORED_OFF), "stored_on_eta085": metrics(STORED_ON)}
    runs = {}
    for b in sorted((HERE / "runs").glob("batch_*")):
        for d in b.iterdir():
            if d.is_dir() and (d / "result.json").exists():
                runs[d.name] = d
                rows[d.name] = metrics(d)
    report = {"rows": rows}
    if "ctrl_none" in runs:
        report["bit_ctrl_vs_stored_off"] = bit_compare(runs["ctrl_none"], STORED_OFF)
    h = json.loads((DF / "phase_off.json").read_text(encoding="utf-8"))
    h9 = sorted((x for x in h if x["job"]["case"] == "R9"), key=lambda x: x["job"]["eps"])
    report["harness_R9_off"] = [
        {k: x.get(k) for k in ("tau_te", "D_te", "D_lift", "F_RL_win", "F_min", "leg", "gap_front", "gap_rear", "t_ready", "s_contact", "t_contact_rel_te")}
        | {"eps": x["job"]["eps"]} for x in h9]
    for g in ("asym2", "mirror2", "asym06"):
        a = [r for k, r in rows.items() if k.startswith(g)]
        if a:
            report[f"spread_{g}"] = {
                q: {"min": min(r[q] for r in a), "max": max(r[q] for r in a)}
                for q in ("tau_te_mm", "D_te_kN", "D_win_kN", "F_RL_win_kN", "F_RL_raw_8_kN", "F_min_after_lift_kN")}
    fit = [r for k, r in rows.items() if k.split("_")[0] in ("asym2", "mirror2", "asym06")]
    if len(fit) >= 3:
        tau_geom = {"asym2": -0.187, "mirror2": 0.187, "asym06": -0.056}
        names = [k for k in rows if k.split("_")[0] in tau_geom]
        x = np.array([rows[k]["tau_te_mm"] - tau_geom[k.split("_")[0]] for k in names])
        y = np.array([rows[k]["D_te_kN"] for k in names])
        report["fit_D_te_vs_tau_minus_geom"] = {"slope_kN_mm": float(np.polyfit(x, y, 1)[0]), "intercept_kN": float(np.polyfit(x, y, 1)[1]),
                                                "residual_rms_kN": float(np.std(y - np.polyval(np.polyfit(x, y, 1), x)))}
        y2 = np.array([rows[k]["D_win_kN"] for k in names])
        y3 = np.array([rows[k]["F_RL_win_kN"] for k in names])
        report["fit_D_win_vs_tau_minus_geom"] = {"slope_kN_mm": float(np.polyfit(x, y2, 1)[0]), "intercept_kN": float(np.polyfit(x, y2, 1)[1]),
                                                 "residual_rms_kN": float(np.std(y2 - np.polyval(np.polyfit(x, y2, 1), x)))}
        report["fit_F_RL_win_vs_D_win"] = {"slope": float(np.polyfit(y2, y3, 1)[0]), "intercept_kN": float(np.polyfit(y2, y3, 1)[1])}
    report["spread_harness_R9"] = {
        q: {"min": min(r[q] for r in report["harness_R9_off"]), "max": max(r[q] for r in report["harness_R9_off"])}
        for q in ("tau_te", "D_te", "D_lift", "F_RL_win", "F_min")}
    (OUT / "asym_results.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    keys = ("t_te_s", "lift_after_te_s", "gap_LR_front_mm", "gap_LR_rear_mm", "tau_contact_mm", "tau_te_mm", "tau_te_rel_contact_mm",
            "tau_lift_mm", "D_te_kN", "D_win_kN", "F_RL_win_kN", "F_RL_raw_8_kN", "F_RL_1s_8_kN", "F_min_after_lift_kN", "F_min_leg", "ready_s", "end_s")
    with (OUT / "asym_table.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["run", *keys, "latch_rel_te_s", "s_te_mm", "offsets_mm"])
        for name, r in rows.items():
            w.writerow([name, *[round(r[k], 3) if isinstance(r[k], float) else r[k] for k in keys],
                        [round(v, 2) for v in r["latch_rel_te_s"]], [round(v, 3) for v in r["s_te_mm"]], r["offsets_mm"]])
    print(json.dumps({k: report[k] for k in report if k != "rows" and k != "harness_R9_off"}, indent=1))
    for name, r in rows.items():
        print(name, {k: (round(r[k], 3) if isinstance(r[k], float) else r[k]) for k in keys})
        print("   latch", np.round(r["latch_rel_te_s"], 2), "s_te", np.round(r["s_te_mm"], 3), "tc", np.round(r["t_contact_rel_te_s"], 3), "F_win", np.round(r["F_win_kN"], 1))


if __name__ == "__main__":
    main()
