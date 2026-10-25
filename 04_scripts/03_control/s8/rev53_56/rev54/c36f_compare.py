"""Compare C-S8-36 bundle A (RT + F1) episodes with the same 768 episodes (no rule).

Independent of the cad judge: reads pads.npz / r8_series.npz / record.npz / result.json
directly. Outputs a CSV (and a JSON summary) in OUT_DIR (06_analysis/02_control/s8/rev53_56/rev54).
"""
import json
import os
import csv
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # rev53_56/rejudge_paths.py
from rejudge_paths import rejudge_file  # noqa: E402  (re-judge archive, env S8_REJUDGE_ML768_DIR)
OUT_DIR = REPO / "06_analysis" / "02_control" / "s8" / "rev53_56" / "rev54"
OUT_DIR.mkdir(parents=True, exist_ok=True)
# ---

ROOT = str(REPO / r"07_results\S8")
A = ROOT + r"\c36_20261025_155317\A_rt\episodes"
B = ROOT + r"\c36_20261025_155317\B_f1only\episodes"
REF = ROOT + r"\ml_main_20261025_090131\episodes"
RJ = str(rejudge_file("rev54", "verify_S8ML_ml768_rev54.json"))
VA = ROOT + r"\c36_20261025_155317\A_rt\verify_S8ML.json"
OUT = str(OUT_DIR)
F_MIN_KN = 9.414589110


def rp_from_quat(q):
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
    return np.degrees(roll), np.degrees(pitch)


def episode(path):
    r = json.load(open(os.path.join(path, "result.json"), encoding="utf-8"))
    te = r["event_t_s"]
    p = np.load(os.path.join(path, "pads.npz"))
    t = p["t"]
    F = p["F_cyl"] / 1e3
    s = np.load(os.path.join(path, "r8_series.npz"))
    ts, ph = s["t"], s["phase"]
    rec = np.load(os.path.join(path, "record", "record.npz"))
    tr = rec["t"]
    roll, pitch = rp_from_quat(rec["body_quat_wxyz"])
    after = t >= te
    fmin_after = float(F[after].min())
    # re-READY: first 'ready' sample after the last non-ready sample following the event
    idx = np.where(ts >= te)[0]
    nonready = [i for i in idx if ph[i] != "ready"]
    if nonready:
        last_nr = nonready[-1]
        rr = ts[last_nr + 1] - te if last_nr + 1 < len(ts) else None
    else:
        rr = 0.0
    # did the phase go to ready before the last non-ready (multiple exits)?
    exits = int(np.sum((ph[idx][1:] != "ready") & (ph[idx][:-1] == "ready")))
    fault = bool(np.any(ph == "fault"))
    if rr is not None:
        m_post = t >= te + rr
        fmin_post = float(F[m_post].min()) if m_post.any() else None
    else:
        fmin_post = None
    # 1 s window after event + 1 s .. event + 3 s minimum per leg (transient)
    w = (t >= te) & (t <= te + 5.0)
    fmin_w = float(F[w].min())
    ra = tr >= te
    att_max = float(max(np.abs(roll[ra] - roll[ra][-1]).max(), np.abs(pitch[ra] - pitch[ra][-1]).max()))
    end_roll, end_pitch = float(roll[-1]), float(pitch[-1])
    phases = sorted(set(ph[idx].tolist()))
    return dict(te=te, fmin_after=fmin_after, fmin_5s=fmin_w, rr=rr, ready_exits=exits, fault=fault,
                fmin_post=fmin_post, att_dev_max=att_max, end_roll=end_roll, end_pitch=end_pitch,
                f_min_result=r.get("f_min_kN"), phases=phases, wall=r.get("wall_s"))


ids = json.load(open(ROOT + r"\c36_20261025_155317\c36_meta.json", encoding="utf-8"))["ids"]["A"]
rj = json.load(open(RJ, encoding="utf-8"))
va = json.load(open(VA, encoding="utf-8"))
rows = []
for e in ids:
    a = episode(os.path.join(A, e))
    b = episode(os.path.join(REF, e))
    ma, mb = va["ml_metrics"][e], rj["ml_metrics"].get(e, {})
    ua, ub = ma.get("u_s8_32") or {}, mb.get("u_s8_32") or {}

    def ev(u):
        if not u or not u.get("event"):
            return (None, None, None)
        cum = max(v["cum_s"] for v in u["event"].values())
        rc = [v["last_recontact_rel_s"] for v in u["event"].values() if v["last_recontact_rel_s"] is not None]
        gap = max(v["gap_max_m"] for v in u["event"].values())
        return (cum, max(rc) if rc else None, gap)

    def adj(u):
        if not u:
            return None
        return u.get("adjacent_sum_s")

    ca, cb = ev(ua), ev(ub)
    rows.append(dict(
        case=e,
        fmin_after_A=a["fmin_after"], fmin_after_R=b["fmin_after"],
        fmin_post_A=a["fmin_post"], fmin_post_R=b["fmin_post"],
        rr_A=a["rr"], rr_R=b["rr"], exits_A=a["ready_exits"], exits_R=b["ready_exits"],
        fault_A=a["fault"], fault_R=b["fault"],
        att_A=a["att_dev_max"], att_R=b["att_dev_max"],
        endroll_A=a["end_roll"], endroll_R=b["end_roll"], endpitch_A=a["end_pitch"], endpitch_R=b["end_pitch"],
        evcum_A=ca[0], evcum_R=cb[0], rc_A=ca[1], rc_R=cb[1],
        adj_A=adj(ua), adj_R=adj(ub),
        fallback_A=len((ma.get("rod_fallback") or {}).get("events", [])),
        fallback_R=len((mb.get("rod_fallback") or {}).get("events", [])),
        starts_A=len((ma.get("reapproach") or {}).get("starts_rel_s", [])),
        starts_R=len((mb.get("reapproach") or {}).get("starts_rel_s", [])),
        late_A=(ma.get("reapproach") or {}).get("late_starts"),
        late_R=(mb.get("reapproach") or {}).get("late_starts"),
        phases_A="|".join(a["phases"]), phases_R="|".join(b["phases"]),
    ))

with open(os.path.join(OUT, "c36f_compare.csv"), "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0]))
    wr.writeheader()
    wr.writerows(rows)


def nz(x):
    return np.array([np.nan if v is None else float(v) for v in x])


def summ(name, a, r, worse_if="lower"):
    a, r = nz(a), nz(r)
    d = a - r
    ok = ~np.isnan(d)
    if worse_if == "lower":
        worse = d < 0
    else:
        worse = d > 0
    i = int(np.nanargmin(d) if worse_if == "lower" else np.nanargmax(d))
    print(f"{name}: A min/max {np.nanmin(a):.3f}/{np.nanmax(a):.3f}, ref min/max {np.nanmin(r):.3f}/{np.nanmax(r):.3f}; "
          f"worse count {int(np.sum(worse & ok))}/{int(ok.sum())}; worst delta {d[i]:+.3f} at {rows[i]['case']}; "
          f"median delta {np.nanmedian(d):+.3f}")


summ("min true force after event [kN]", [r["fmin_after_A"] for r in rows], [r["fmin_after_R"] for r in rows])
summ("min true force after re-READY [kN]", [r["fmin_post_A"] for r in rows], [r["fmin_post_R"] for r in rows])
summ("re-READY rel event [s]", [r["rr_A"] for r in rows], [r["rr_R"] for r in rows], "higher")
summ("attitude dev max after event [deg]", [r["att_A"] for r in rows], [r["att_R"] for r in rows], "higher")
summ("event-leg cum lift [s]", [r["evcum_A"] for r in rows], [r["evcum_R"] for r in rows], "higher")
summ("event-leg last recontact [s]", [r["rc_A"] for r in rows], [r["rc_R"] for r in rows], "higher")
print("FAULT A/R:", sum(r["fault_A"] for r in rows), sum(r["fault_R"] for r in rows))
print("READY exits A/R total:", sum(r["exits_A"] for r in rows), sum(r["exits_R"] for r in rows))
print("rod fallback runs A/R:", sum(r["fallback_A"] > 0 for r in rows), sum(r["fallback_R"] > 0 for r in rows))
print("rod fallback in A only:", [r["case"] for r in rows if r["fallback_A"] > 0 and r["fallback_R"] == 0])
print("rod fallback in R:", [r["case"] for r in rows if r["fallback_R"] > 0])
print("end |roll|,|pitch| max A:", max(abs(r["endroll_A"]) for r in rows), max(abs(r["endpitch_A"]) for r in rows))
print("end |roll|,|pitch| max R:", max(abs(r["endroll_R"]) for r in rows), max(abs(r["endpitch_R"]) for r in rows))
print("starts total A/R:", sum(r["starts_A"] for r in rows), sum(r["starts_R"] for r in rows))
print("late starts total A/R:", sum(r["late_A"] or 0 for r in rows), sum(r["late_R"] or 0 for r in rows))
print("rr None A/R:", [r["case"] for r in rows if r["rr_A"] is None], [r["case"] for r in rows if r["rr_R"] is None])
for c in ("ML78_ep0", "ML78_ep1", "ML78_ep3", "ML00_ep5", "ML21_ep1", "ML90_ep1", "ML42_ep6", "ML33_ep4", "ML88_ep0"):
    r = next(x for x in rows if x["case"] == c)
    print(c, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k != "case"})
# worst 5 fmin_after deltas
d = sorted(rows, key=lambda r: r["fmin_after_A"] - r["fmin_after_R"])[:6]
print("worst fmin_after deltas:", [(r["case"], round(r["fmin_after_A"], 2), round(r["fmin_after_R"], 2)) for r in d])
d = sorted(rows, key=lambda r: -((r["rr_A"] or 0) - (r["rr_R"] or 0)))[:6]
print("worst re-READY deltas:", [(r["case"], round(r["rr_A"], 2), round(r["rr_R"], 2)) for r in d])
d = sorted(rows, key=lambda r: (r["fmin_post_A"] or 0) - (r["fmin_post_R"] or 0))[:6]
print("worst fmin_post deltas:", [(r["case"], round(r["fmin_post_A"], 2), round(r["fmin_post_R"], 2)) for r in d])
print("min fmin_post A:", min(r["fmin_post_A"] for r in rows), "F_min", F_MIN_KN)
