"""Rev. 56: E (c37, P-S8-21 + RT + F1) vs c36 A (RT + F1) vs 768 on the 17 fallback runs.

Independent of the judge for the force / attitude / FAULT / READY metrics: reads pads.npz,
r8_series.npz, controller_events.json and result.json directly. U-S8-32 values are taken
from the judge rows of each batch (same definition) for the side-by-side table.

Definitions (event-relative, engine time):
- judged force = pads F_cyl_min_interval, airborne samples -> F_cyl_mean_20ms (S8-A2), kN.
- min_post: min over all legs of the judged force on [0, end].
- min_after_ready: min over all legs on [re-READY, end] (None if not reached).
- min_tail: min over all legs on [3.0 s, re-READY or end] (U-S8-32 window end .. re-READY,
  same as the 257.2 record row; window end approximated by event + 3.0 s).
- attitude from pads body_quat_wxyz (ZYX): roll, pitch [deg]; max deviation from the value at the
  event over [0, end]; end |roll|, |pitch| = mean of the last 0.5 s.
- FAULT = controller events containing 'FAULT' after the event (count).
- fallback = WARN_ROD_PRESSURE_FALLBACK after the event; check_draining = INFO events with
  'check_draining' after the event.
"""
import json
import os
import re
import sys
import numpy as np

# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s8" / "rev53_56" / "rev56"
OUT_DIR.mkdir(parents=True, exist_ok=True)
# ---
ROOT = str(REPO / r"07_results\S8")
E = ROOT + r"\c37_20261025_180821\E_drain\episodes"
A = ROOT + r"\c36_20261025_155317\A_rt\episodes"
R = ROOT + r"\ml_main_20261025_090131\episodes"
VE = ROOT + r"\c37_20261025_180821\E_drain\verify_S8ML.json"
VA = ROOT + r"\c36_20261025_155317\A_rt\verify_S8ML.json"
IDS = sorted(os.listdir(E))
F_MIN = 9.41458911
PAT = re.compile(r"t_s=([-0-9.e]+), name='([^']+)'")


def euler(q):
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
    return np.degrees(roll), np.degrees(pitch)


def run(path):
    r = json.load(open(os.path.join(path, "result.json"), encoding="utf-8"))
    te = float(r["event_t_s"])
    p = np.load(os.path.join(path, "pads.npz"))
    t = p["t"] - te
    J = p["F_cyl_min_interval"].astype(float).copy()
    air = p["airborne"].astype(bool)
    J[air] = p["F_cyl_mean_20ms"][air]
    J /= 1e3
    s = np.load(os.path.join(path, "r8_series.npz"), allow_pickle=True)
    ts, ph = s["t"] - te, [str(x) for x in s["phase"]]
    rr, seen = None, False
    for i in range(len(ts)):
        if ts[i] < 0:
            continue
        if ph[i] == "done":
            seen = True
        if rr is None and seen and ph[i] == "ready":
            rr = float(ts[i])
    end_phase = ph[-1]
    ev = []
    for e in json.load(open(os.path.join(path, "controller_events.json"), encoding="utf-8")):
        m = PAT.search(e)
        if m and float(m.group(1)) >= te - 1e-6:
            ev.append((float(m.group(1)) - te, m.group(2)))
    post = t >= 0
    i = int(np.argmin(np.where(post[:, None], J, np.inf)) // 4)
    k = int(np.argmin(np.where(post[:, None], J, np.inf)) % 4)
    out = dict(min_post=round(float(J[i, k]), 3), min_post_leg="FL FR RL RR".split()[k],
               min_post_t=round(float(t[i]), 3))
    if rr is not None:
        w = t >= rr
        out["min_after_ready"] = round(float(J[w].min()), 3)
    else:
        out["min_after_ready"] = None
    b = rr if rr is not None else float(t[-1])
    w = (t >= 3.0) & (t <= b)
    out["min_tail"] = round(float(J[w].min()), 3) if w.any() else None
    ro, pi = euler(p["body_quat_wxyz"])
    i0 = int(np.argmin(abs(t)))
    out["dev_max_deg"] = round(float(max(abs(ro[post] - ro[i0]).max(), abs(pi[post] - pi[i0]).max())), 3)
    last = t >= t[-1] - 0.5
    out["end_roll_deg"] = round(float(abs(ro[last].mean())), 3)
    out["end_pitch_deg"] = round(float(abs(pi[last].mean())), 3)
    out["fault"] = sum(1 for _, n in ev if "FAULT" in n and not n.startswith("INFO"))
    out["fault_names"] = sorted({n for _, n in ev if "FAULT" in n})
    out["fallback"] = [(round(x, 2), n) for x, n in ev if n.startswith("WARN_ROD_PRESSURE_FALLBACK")]
    out["check_draining"] = [(round(x, 2), n) for x, n in ev if "check_draining" in n]
    out["defer"] = [(round(x, 2), n) for x, n in ev if n.startswith("leg_reapproach_deferred")]
    out["re_ready"] = None if rr is None else round(rr, 1)
    out["end_phase"] = end_phase
    out["t_end"] = round(float(t[-1]), 2)
    return out


def u32(vfile):
    d = json.load(open(vfile, encoding="utf-8"))
    o = {}
    for r in d["rows"]:
        if r["item"].startswith("U-S8-32 adjacent"):
            o.setdefault(r["case"], {})["adj"] = (r["value"], r["passed"])
        if r["item"].startswith("U-S8-32 event legs"):
            o.setdefault(r["case"], {})["evt"] = (r["value"], r["passed"])
    return o


UE, UA = u32(VE), u32(VA)
res = {}
for c in IDS:
    res[c] = dict(E=run(os.path.join(E, c)), A=run(os.path.join(A, c)), R=run(os.path.join(R, c)),
                  u32_E=UE.get(c), u32_A=UA.get(c))
dst = os.path.join(str(OUT_DIR), "s56_compare.json")
json.dump(res, open(dst, "w", encoding="utf-8"), indent=1, default=str)

keys = ["min_post", "min_after_ready", "min_tail", "dev_max_deg", "end_roll_deg", "end_pitch_deg",
        "fault", "re_ready", "end_phase"]
for c in IDS:
    print("==", c)
    for b in "EAR":
        x = res[c][b]
        print("  ", b, {k: x[k] for k in keys}, "fb", len(x["fallback"]), "cd", len(x["check_draining"]),
              "def", x["defer"])
    print("   U32 E", res[c]["u32_E"])
    print("   U32 A", res[c]["u32_A"])


def agg(b, k):
    v = [res[c][b][k] for c in IDS if res[c][b][k] is not None]
    return (round(min(v), 3), round(max(v), 3), len(v)) if v else None


print("\nSUMMARY")
for k in ("min_post", "min_after_ready", "min_tail", "dev_max_deg", "end_roll_deg", "end_pitch_deg"):
    print(k, "E", agg("E", k), "A", agg("A", k), "768", agg("R", k))
for k in ("min_post", "min_after_ready", "min_tail"):
    d = [(c, round(res[c]["E"][k] - res[c]["A"][k], 3)) for c in IDS
         if res[c]["E"][k] is not None and res[c]["A"][k] is not None]
    lower = [x for x in d if x[1] < -1e-3]
    print(k, "E-A: n", len(d), "lower", len(lower), "worst", min(d, key=lambda z: z[1]) if d else None,
          "median", round(float(np.median([x[1] for x in d])), 3) if d else None)
    d = [(c, round(res[c]["E"][k] - res[c]["R"][k], 3)) for c in IDS
         if res[c]["E"][k] is not None and res[c]["R"][k] is not None]
    lower = [x for x in d if x[1] < -1e-3]
    print(k, "E-768: n", len(d), "lower", len(lower), "worst", min(d, key=lambda z: z[1]) if d else None)
d = [(c, round(res[c]["E"]["dev_max_deg"] - res[c]["A"]["dev_max_deg"], 3)) for c in IDS]
print("dev E-A worst", max(d, key=lambda z: z[1]), "median", float(np.median([x[1] for x in d])))
print("fault E/A/R", [sum(res[c][b]["fault"] for c in IDS) for b in "EAR"])
print("fallback runs E/A/R", [sum(1 for c in IDS if res[c][b]["fallback"]) for b in "EAR"])
print("check_draining runs E/A/R", [sum(1 for c in IDS if res[c][b]["check_draining"]) for b in "EAR"],
      "events E", sum(len(res[c]["E"]["check_draining"]) for c in IDS))
for b in "EAR":
    print("re-READY", b, {c: res[c][b]["re_ready"] for c in IDS})
