"""Detail behind the value table: pads minima definition check, re-READY, measurement differences, moving-pressure notes. Read only.

Output: v4_recheck/recheck_detail.json and a print.
Usage: python -I -B -X utf8 detail.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

MAIN = Path(r"C:\workspace\outrigger_control")
OUT = MAIN / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/v4_recheck"
S8 = MAIN / "07_results/S8"
NEW = S8 / "final_v4recheck_20261104_202815"
REST, P1R = "rest_20261024_233615", "p1r_20261024_222013"
SOURCE = {"N_G4_Fs0_pressure": REST, "N_G4_Fs4_pressure": REST, "N_G4_Fs8_pressure": REST, "N_SS_Fs0_pressure": REST, "N_SS_Fs4_pressure": REST,
          "N_SS_Fs8_pressure": REST, "K0V_top_fdown3.5_Fs0": P1R, "K24_top_fdown3.5_Fs2": REST, "K8_top_fdown3.5_Fs8": P1R, "E_SS_Fs0": P1R,
          "E_SS_Fs8": P1R, "E_RE1bF_Fs0": P1R, "E_RE1bP_Fs0": P1R, "E_RE1bP_Fs8": P1R}
LEGS = ("FL", "FR", "RL", "RR")


def reready(res: dict) -> dict:
    te = res.get("event_t_s")
    ph = res.get("phases")
    if te is None or not ph:
        return {"phases_type": type(ph).__name__}
    rows = [(float(p["t_s"]) if "t_s" in p else float(p["start_s"]), p.get("phase")) for p in ph] if isinstance(ph, list) and isinstance(ph[0], dict) else None
    if rows is None:
        return {"phases_sample": str(ph)[:200]}
    left = [t for t, q in rows if t > te and q != "ready"]
    after = [t for t, q in rows if q == "ready" and left and t > left[0]]
    return {"first_nonready_after_event_s": left[0] if left else None, "first_ready_again_rel_s": (after[0] - te) if after else None}


def main() -> None:
    out = {}
    for cid, src in SOURCE.items():
        n, o = NEW / cid, S8 / src / cid
        rn, ro = np.load(n / "record/record.npz", allow_pickle=False), np.load(o / "record/record.npz", allow_pickle=False)
        m = min(len(rn["t"]), len(ro["t"]))
        t = rn["t"][:m]
        row = {}
        for key in ("meas.head_pressure", "meas.rod_pressure", "F_cyl", "s_motor"):
            d = np.abs(rn[key][:m] - ro[key][:m]).reshape(m, -1).max(axis=1)
            w = np.flatnonzero(d > 0)
            row[key] = {"count": int(w.size), "first_t": float(t[w[0]]) if w.size else None, "last_t": float(t[w[-1]]) if w.size else None, "max_abs": float(d.max()), "t_at_max": float(t[int(np.argmax(d))])}
        pn, po = np.load(n / "pads.npz", allow_pickle=False), np.load(o / "pads.npz", allow_pickle=False)
        k = min(len(pn["t"]), len(po["t"]))
        pad = {}
        for key in sorted(set(pn.files) & set(po.files)):
            a, b = pn[key], po[key]
            if a.dtype.kind != "f" or a.ndim == 0 or b.ndim == 0 or a.shape[0] != len(pn["t"]) or b.shape[0] != len(po["t"]):
                continue
            x, y = a[:k], b[:k]
            same = np.logical_or(x == y, np.logical_and(np.isnan(x), np.isnan(y))).reshape(k, -1).all(axis=1)
            pad[key] = None if same.all() else float(pn["t"][int(np.argmin(same))])
        resn, reso = json.loads((n / "result.json").read_text(encoding="utf-8")), json.loads((o / "result.json").read_text(encoding="utf-8"))
        offn = float(rn["t"][-1]) - float(resn["s8_end"]["end_t_s"])
        fi_n, fi_o = pn["F_cyl_min_interval"][:k], po["F_cyl_min_interval"][:k]
        i, j = np.unravel_index(int(np.argmin(fi_n)), fi_n.shape)
        i2, j2 = np.unravel_index(int(np.argmin(fi_o)), fi_o.shape)
        ev = resn.get("event_t_s")
        rmin = {}
        if ev is not None:
            tp = pn["t"][:k] - offn
            leg = 3
            post = tp >= float(ev)
            q_n, q_o = np.argmin(fi_n[post, leg]), np.argmin(fi_o[post, leg])
            rmin = {"RR_new_min_N": float(fi_n[post, leg][q_n]), "RR_new_t_s": float(tp[post][q_n]), "RR_old_min_N": float(fi_o[post, leg][q_o]), "RR_old_t_s": float(tp[post][q_o]),
                    "new_at_old_time_N": float(fi_n[post, leg][q_o]), "old_at_new_time_N": float(fi_o[post, leg][q_n])}
        out[cid] = {"record": row, "pads_first_diff_rawtime": {kk: vv for kk, vv in pad.items() if vv is not None}, "pads_keys_same": [kk for kk, vv in pad.items() if vv is None],
                    "offset_new_s": offn, "RR_interval": rmin, "reready": reready(resn), "reready_old": reready(reso), "phases_head": str(resn.get("phases"))[:300],
                    "air_meta": {kk: resn.get("pad_record", {}).get(kk) for kk in ("samples",)}, "capped": resn.get("c2", {}).get("free_air_capped_legs") if isinstance(resn.get("c2"), dict) else None}
    (OUT / "recheck_detail.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for cid, v in out.items():
        r = v["record"]
        print(cid, "F_cyl", {a: (round(b, 3) if isinstance(b, float) else b) for a, b in r["F_cyl"].items()}, "| s_motor max", f"{r['s_motor']['max_abs']:.3g}", "| head", r["meas.head_pressure"]["count"], r["meas.head_pressure"]["first_t"], r["meas.head_pressure"]["last_t"], f"{r['meas.head_pressure']['max_abs']:.3g}", "| rod", r["meas.rod_pressure"]["count"], r["meas.rod_pressure"]["last_t"], f"{r['meas.rod_pressure']['max_abs']:.3g}")
        print("   pads first diff", {a: round(b, 2) for a, b in list(v["pads_first_diff_rawtime"].items())[:8]}, "offset", round(v["offset_new_s"], 3))
        print("   RR interval", {a: round(b, 2) for a, b in v["RR_interval"].items()}, "reready", v["reready"], v["reready_old"], "capped", v["capped"])
    print(out["E_SS_Fs0"]["phases_head"])
    for f in sorted((OUT.parent / "verify").glob("*E_RE1bF_Fs8*")):
        d = json.loads(f.read_text(encoding="utf-8"))
        print(f.name, {r["item"][:38]: r["value"] for r in d["rows"] if r.get("case") == "E_RE1bF_Fs8" and (r["item"].startswith(("item 9 M5", "4 max", "RE1b re-READY", "3 F_min (1 ms)")))})


if __name__ == "__main__":
    main()
