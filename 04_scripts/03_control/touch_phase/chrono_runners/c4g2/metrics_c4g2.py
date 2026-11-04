"""C4G2 values against the flow-off pairs; definitions as dF_cause/decompose.py chrono() and cad_c4g1/metrics.py. No judgement.

Usage:
  python -I -B -X utf8 metrics_c4g2.py expected        -> touch_phase/chrono/expected_c4g2_before_run.json
  python -I -B -X utf8 metrics_c4g2.py new <stamp>     -> verify_c4g2_*.json, c4g2_values.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WT = HERE / "wt"
MAIN = Path(r"C:\workspace\outrigger_control")
S8 = MAIN / "07_results/S8"
OUT = MAIN / "06_analysis/02_control/touch_phase/chrono"
ASYM = HERE.parent / "cad_asym"
VD = MAIN / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/verify"
LEGS = ("FL", "FR", "RL", "RR")
N = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
V_MAX = 20.924e-3
F_MIN_KN = 9.41458911
R16, R12, R15, R9, R9F = "G1L_RE1bF_FL_top_o050_Fs4", "E_G4_Fs4", "G1L_RE1bF_FL_top_Fs0", "A_bottom_rpB_Fs0", "A_bottom_rpB_Fs4"
PAIR = {"R16_mirror2_d000_C4G2K1": (R16, ASYM / "runs_r16/r16_mirror2_d000" / R16), "R16_mirror2_d070_C4G2K1": (R16, ASYM / "runs_r16/r16_mirror2_d070" / R16),
        "R12_C4G2K1": (R12, S8 / "final_E_G4_Fs4_20261030_233941" / R12), "R16_mirror2_d000_C4G2": (R16, ASYM / "runs_r16/r16_mirror2_d000" / R16),
        "R15_C4G2K1": (R15, S8 / "final_G1L_RE1bF_FL_top_Fs0_20261031_003000" / R15), "R9_mirror2_d035_Fs4_C4G2K1": (R9F, None),
        "R9_mirror2_d000_off": (R9, ASYM / "runs/batch_164123/mirror2_d000"), "R9_mirror2_d035_off": (R9, ASYM / "runs/batch_164123/mirror2_d035"), "R9_mirror2_d035_Fs4_off": (R9F, None)}
C4G1_ON = {"R9_mirror2_d000_off": S8 / "c4g1_R9_mirror2_d000_20261104_211444" / R9, "R9_mirror2_d035_off": S8 / "c4g1_R9_mirror2_d035_20261104_211444" / R9}
ROW_RE = re.compile(r"^(3 F_min|6 min after settlement|.*re-READY|4 max|item 9 (J_P|J_C|M5)|.*REANCHOR min|G4 item 6|run$|2 attitude|C1 D8|3 lift-off|.*F_min)")


def metrics(d: Path) -> dict:
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    p = np.load(d / "pads.npz", allow_pickle=False)
    rec = np.load(d / "record/record.npz", allow_pickle=False)
    r8 = np.load(d / "r8_series.npz", allow_pickle=False)
    off = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    t, F, Fm, s = p["t"] - off, p["F_cyl"] / 1e3, p["F_cyl_min_interval"] / 1e3, p["s_motor"] * 1e3
    air = p["airborne"].astype(bool)
    dt = np.diff(t, prepend=t[0] - 1e-3)
    crt, crf = rec["t"] - off, np.linalg.norm(rec["F_crawler"], axis=1) / 1e3
    pt = r8["t"] - off
    te = float(pt[np.flatnonzero(~np.isin(r8["phase"], ("idle", "check", "touch")))[0]])
    W = float(np.median(F[(t > te - 8) & (t < te - 6)].sum(axis=1)) + np.median(crf[(crt > te - 8) & (crt < te - 6)]))
    sm = np.convolve(F.sum(axis=1), np.ones(20) / 20, "same")
    tl = float(t[np.flatnonzero((t > te) & (W - sm < 3.0))[0]])
    tz = float(crt[(crf == 0.0) & (crt > te)][0])
    ke, kl, kz = int(np.searchsorted(t, te)), int(np.searchsorted(t, tl)), int(np.searchsorted(t, tz))
    k8 = int(np.searchsorted(t, tl + 8.0))
    ev = res.get("event_t_s")
    kev = None if ev is None else int(np.searchsorted(t, float(ev)))
    kz_end = kev if kev is not None and kev > kz else len(t)

    def leg_min(a, b) -> dict:
        return {g: float(Fm[a:b, i].min()) for i, g in enumerate(LEGS)} if b > a else None

    events = [str(e) for e in json.loads((d / "controller_events.json").read_text(encoding="utf-8"))]
    ename = []
    for e in events:
        m = re.match(r"C2Event\(t_s=([0-9.]+), name='(.*)'\)", e)
        ename.append((float(m[1]) - off, m[2]) if m else (None, e))
    ph = res["phases"]
    out = {"dir": str(d), "t_te_s": te, "t_lift_s": tl, "lift_after_te_s": tl - te, "t_crawler_zero_s": tz, "W_kN": W, "tau_te_mm": float(N @ s[ke]), "tau_lift_mm": float(N @ s[kl]),
           "D_te_kN": float(F[ke - 200:ke].mean(axis=0) @ N), "D_lift_kN": float(F[kl:kl + 400].mean(axis=0) @ N), "F_win_kN": [float(v) for v in F[kl:kl + 400].mean(axis=0)],
           "F_min_lift8_kN": leg_min(kl, k8), "F_min_zero_kN": leg_min(kz, kz_end), "F_min_zero_to40_kN": leg_min(kz, int(np.searchsorted(t, 40.0))), "ready_t_s": res.get("ready_t_s"),
           "end_t_s": float(res["s8_end"]["end_t_s"]), "final_phase": res["s8_end"].get("final_phase"), "stroke_max_mm": [float(v) for v in s.max(axis=0)], "stroke_end_mm": [float(v) for v in s[-1]],
           "end_attitude_deg": [float(v) for v in _attitude(p["body_quat_wxyz"][-1])], "head_pressure_max_bar": float(p["head_pressure"].max() / 1e5) if "head_pressure" in p.files else None,
           "u_cmd_max_over_vmax": float(np.abs(rec["u_cmd"]).max() / V_MAX), "u_applied_max_over_vmax": float(np.abs(rec["u_applied"]).max() / V_MAX), "wall_s": (res.get("runner") or {}).get("wall_s"),
           "phase_at_event": (res.get("event_state") or {}).get("phase_at_event"), "event_t_s": ev, "phases": ph, "events_rel": ename,
           "hold_events": [x for x in ename if "TOUCH_TWIST" in x[1]], "retrigger_deferred": [x for x in ename if "leg_reapproach_deferred" in x[1] and "retrigger" in x[1]],
           "reapproach_starts": [x for x in ename if "leg_reapproach_start" in x[1]], "lift_paused": [x for x in ename if "LIFT_PAUSED" in x[1]], "warn_fault": [x for x in ename if "WARN" in x[1] or "FAULT" in x[1]],
           "hold_meta": {k: v for k, v in ((res.get("controller_meta") or {}).get("touch_twist_hold") or {}).items() if k != "settings"}}
    if kev is not None:
        post = slice(kev, len(t))
        out["after_event"] = {g: {"min_interval_kN": float(Fm[post, i].min()), "t_rel_s": float(t[kev + int(np.argmin(Fm[post, i]))] - float(ev)), "under_F_min_s": float(dt[post][(Fm[post, i] < F_MIN_KN) & ~air[post, i]].sum()),
                                  "airborne_s": float(dt[post][air[post, i]].sum())} for i, g in enumerate(LEGS)}
        later = [q[0] for q in ph if q[1] == "ready" and q[0] > float(ev)]
        out["re_ready_after_event_s"] = (later[0] - float(ev)) if later else None
    # twist estimate parts at the last three 10 Hz TOUCH samples, truth from pads
    parts = []
    for ts in (te - 0.2, te - 0.1, te):
        k = int(np.searchsorted(t, ts))
        row = {"t_s": ts, "nT_F_cyl_kN": float(N @ F[k])}
        if "F_pressure" in p.files:
            row["nT_F_pressure_kN"] = float(N @ p["F_pressure"][k] / 1e3)
            row["nT_F_pressure_minus_F_cyl_kN"] = row["nT_F_pressure_kN"] - row["nT_F_cyl_kN"]
        if "f_seal" in p.files:
            row["nT_f_seal_kN"] = float(N @ p["f_seal"][k] / 1e3)
        if "seal_stuck" in p.files:
            row["seal_stuck"] = [int(v) for v in p["seal_stuck"][k]]
        parts.append(row)
    out["touch_last3"] = parts
    h = out["hold_meta"]
    if h.get("end_t_s") is not None:
        k2 = int(np.searchsorted(t, float(h["end_t_s"]) - off))
        k1 = int(np.searchsorted(t, float(h["start_t_s"]) - off))
        out["achieved_tau_hold_mm"] = float(N @ (s[k2] - s[k1]))
    seal = [k for k in p.files if "seal" in k.lower() or "stick" in k.lower()]
    out["seal_keys"] = seal
    for key in seal:
        if p[key].ndim == 2 and p[key].shape[0] == len(t):
            k = int(np.searchsorted(t, te))
            out[f"at_te.{key}"] = [float(v) for v in p[key][k]]
    return out


def _attitude(q):
    w, x, y, z = q
    return np.degrees(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))), np.degrees(np.arcsin(2 * (w * y - z * x)))


def first_diff(a: Path, b: Path) -> dict:
    ra, rb = np.load(a / "record/record.npz", allow_pickle=False), np.load(b / "record/record.npz", allow_pickle=False)
    m = min(len(ra["t"]), len(rb["t"]))
    res = json.loads((a / "result.json").read_text(encoding="utf-8"))
    off = float(ra["t"][-1]) - float(res["s8_end"]["end_t_s"])
    out = {}
    for k in ("F_cyl", "s_motor", "u_cmd", "u_applied", "meas.head_pressure"):
        same = (ra[k][:m] == rb[k][:m]).reshape(m, -1).all(axis=1)
        out[k] = None if same.all() else round(float(ra["t"][int(np.argmin(same))] - off), 3)
    return out


def bit_compare(run: Path, stored: Path) -> dict:
    out = {}
    for rel in ("pads.npz", "r8_series.npz", "s8_series.npz", "record/record.npz"):
        a, b = np.load(run / rel, allow_pickle=False), np.load(stored / rel, allow_pickle=False)
        bad, narr, nval = [], 0, 0
        for k in a.keys():
            if k not in b or a[k].dtype.kind not in "fiub" or a[k].ndim == 0:
                continue
            n = min(len(a[k]), len(b[k]))
            x, y = a[k][:n], b[k][:n]
            narr += 1
            nval += x.size
            if x.shape != y.shape or not np.array_equal(x, y, equal_nan=x.dtype.kind == "f"):
                bad.append(k)
        out[rel] = {"arrays": narr, "values": nval, "different": bad, "samples_new": int(len(a["t"])) if "t" in a else None, "samples_stored": int(len(b["t"])) if "t" in b else None}
    return out


def expected() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pairs = {}
    for row, (_cid, d) in PAIR.items():
        if d is not None:
            m = metrics(d)
            m.pop("events_rel")
            pairs[row] = m
    table = (OUT / "next_batch_rows.md").read_text(encoding="utf-8")
    doc = {"written_before_run": True, "note": "Off values and the table expectations; no acceptance rule here, control-expert judges.", "code": {"commit": "74032beae72c7e44858e41384bc54c263e724fd3", "c2_sha256": "28482b8d5678c3e1079c9dd89046013bd60cac718e0e8efa195101a36236df67"},
           "pairs": {k: None if v[1] is None else str(v[1]) for k, v in PAIR.items()}, "table_expectations_source": "touch_phase/chrono/next_batch_rows.md 'see' table", "table_expectations_text": table[table.find("## 보는 양"):table.find("## 참고")],
           "added_row_9": "R9_mirror2_d035_Fs4_off: same clone and same commit as row 6, hold and K1 off, the same-code pair of row 6.",
           "expected_extra": {"rows_7_8": "Off path. Stored 02efc57 runs have no returned clip; preset here has it on. Bit-equal to 40 s expected if the clip never acts before 40 s; a difference is reported with the first array.",
                              "pair_note": "Rows 7, 8 use commit 74032be off; the on rows c4g1_R9_mirror2_* are 15176d1 (G1). Same preset clip, different hold / ramp code.",
                              "row_6": "D_hat error bound about +-7.3 kN (0.32 mm) from the table; true-force twist from pads against D_hat in touch_last3."},
           "pair_values": pairs}
    (OUT / "expected_c4g2_before_run.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    for row, m in pairs.items():
        ae = m.get("after_event")
        print(row, {q: (round(m[q], 3) if isinstance(m[q], float) else m[q]) for q in ("t_te_s", "tau_te_mm", "D_te_kN", "t_lift_s", "D_lift_kN", "ready_t_s", "end_t_s")}, None if ae is None else {g: round(ae[g]["min_interval_kN"], 2) for g in LEGS}, m["seal_keys"])


def new(stamp: str) -> None:
    sys.path.insert(0, str(WT / "03_src"))
    from outrigger_sim.verify.s8_control import judge_batch

    rows = {}
    for row, (cid, pair) in PAIR.items():
        b = S8 / f"c4g2_{row}_{stamp}"
        vf = OUT / f"verify_{b.name}.json"
        judge_batch(b, vf, root=MAIN, ref_batch=None, lookup_batches=[], deferred_ref=None)
        doc = json.loads(vf.read_text(encoding="utf-8"))
        d = b / cid
        m = metrics(d)
        items = {r["item"]: r for r in doc["rows"] if r.get("case") == cid}
        r_all = {k: {"value": r.get("value"), "passed": r.get("passed"), "note": (r.get("note") or "")[:160]} for k, r in items.items() if ROW_RE.match(k)}
        sampling = {r["item"]: {"sampling_only": r.get("sampling_only"), "count": r.get("sampling_only_count")} for r in doc["rows"] if "sampling_only" in r or "sampling_only_count" in r}
        rec = {"on": m, "rows": r_all, "meta_failed": doc["meta"].get("failed"), "meta_hold": doc["meta"].get("hold"), "failed_rows": [k for k, r in items.items() if r.get("passed") is False], "sampling_only_rows": sampling,
               "side": json.loads((d / "c4g2_job_side.json").read_text(encoding="utf-8"))}
        if pair is not None:
            rec["off"] = metrics(pair)
            rec["first_diff_vs_off"] = first_diff(d, pair)
        rows[row] = rec
    a, b = S8 / f"c4g2_R9_mirror2_d035_Fs4_C4G2K1_{stamp}" / R9F, S8 / f"c4g2_R9_mirror2_d035_Fs4_off_{stamp}" / R9F
    rows["R9_mirror2_d035_Fs4_C4G2K1"]["off"] = rows["R9_mirror2_d035_Fs4_off"]["on"]
    rows["R9_mirror2_d035_Fs4_C4G2K1"]["first_diff_vs_off"] = first_diff(a, b)
    for row, on in C4G1_ON.items():
        d = S8 / f"c4g2_{row}_{stamp}" / R9
        rows[row]["bit_vs_stored_40s"] = bit_compare(d, PAIR[row][1])
        rows[row]["first_diff_vs_c4g1_on"] = first_diff(d, on)
        rows[row]["c4g1_on"] = metrics(on)
    (OUT / "c4g2_values.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("written", OUT / "c4g2_values.json")
    for row, v in rows.items():
        print(row, "failed", v["meta_failed"], "hold", v["meta_hold"], v["failed_rows"])


if __name__ == "__main__":
    if sys.argv[1] == "expected":
        expected()
    else:
        new(sys.argv[2])
