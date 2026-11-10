"""Second-round details: re-approach order, contact and strokes of the R16 phases; tau and prefix identity of R12; sampler."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "tables_r16"
S8 = Path(r"C:\workspace\outrigger_control\07_results\S8")
CASE = "G1L_RE1bF_FL_top_o050_Fs4"
TWIST = np.array([0.47607202408216903, -0.47607202408216903, -0.5228340347436333, 0.5228340347436333])
r = json.loads((OUT / "r16_results.json").read_text(encoding="utf-8"))["runs"]
base = r["stored_off"]["contact"]
for n in sorted(k for k in r if k.startswith("r16_")):
    doc = json.loads((OUT / f"verify_{n}.json").read_text(encoding="utf-8"))
    note = next(x.get("note") or x.get("detail") for x in doc["rows"] if x.get("case") == CASE and x["item"].startswith("C-S8-72 record: re-approach"))
    c = r[n]["contact"]
    p = np.load(HERE / "runs_r16" / n / CASE / "pads.npz", allow_pickle=False)
    rec = np.load(HERE / "runs_r16" / n / CASE / "record" / "record.npz", allow_pickle=False)
    res = json.loads((HERE / "runs_r16" / n / CASE / "result.json").read_text(encoding="utf-8"))
    off = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    k = int(np.searchsorted(p["t"] - off, r[n]["t_touch_end_s"]))
    print(n, str(note)[:150].split(";")[0])
    print("   s_contact", np.round(c["s_motor_mm"], 3), "pitch first", np.round(c["pitch_rise_at_first_deg"], 4), "pitch te", round(c["pitch_rise_at_touch_end_deg"], 4), "max", round(c["pitch_rise_max_before_lift_deg"], 4), "s_te", np.round(p["s_motor"][k] * 1e3, 3))

new = next((HERE / "runs_r12").glob("*/E_G4_Fs4_ph0.05"))
on = sorted(S8.glob("coupled_eta085_E_G4_Fs4_*"))[-1] / "E_G4_Fs4"
off_d = sorted(S8.glob("final_E_G4_Fs4_2*"))[-1] / "E_G4_Fs4"
for label, d in (("off", off_d), ("on", on), ("new", new)):
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    p = np.load(d / "pads.npz", allow_pickle=False)
    rec = np.load(d / "record" / "record.npz", allow_pickle=False)
    s8 = np.load(d / "r8_series.npz", allow_pickle=False)
    o = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    t = p["t"] - o
    pt = s8["t"] - o
    te = float(pt[np.flatnonzero(~np.isin(s8["phase"], ("idle", "check", "touch")))[0]])
    k = int(np.searchsorted(t, te))
    ev = float(res["event_t_s"])
    pre = (t >= ev - 1.0) & (t < ev)
    print(label, "t_te", round(te, 2), "tau_te", round(float(TWIST @ p["s_motor"][k] * 1e3), 4), "D_te", round(float((p["F_cyl"][k - 200:k].mean(axis=0) / 1e3) @ TWIST), 2), "D_pre", round(float((p["F_cyl"][pre].mean(axis=0) / 1e3) @ TWIST), 2))
a = np.load(new / "r8_series.npz", allow_pickle=False)
b = np.load(on / "r8_series.npz", allow_pickle=False)
n = min(len(a["t"]), len(b["t"]))
first = None
for key in a.files:
    if a[key].dtype.kind not in "fiub" or key not in b.files:
        continue
    x, y = a[key][:n], b[key][:n]
    same = (x == y) | (np.isnan(x) & np.isnan(y)) if x.dtype.kind == "f" else x == y
    same = same.reshape(n, -1).all(axis=1)
    if not same.all():
        i = int(np.argmin(same))
        if first is None or i < first[0]:
            first = (i, key)
print("R12 new vs on first difference in r8_series:", None if first is None else (first[1], float(a["t"][first[0]])), "event abs", float(json.loads((new / "result.json").read_text(encoding="utf-8"))["event_t_s"]) + 3.0)
s = json.loads((HERE / "r12_eta085_ph005.sample.json").read_text(encoding="utf-8"))
print("sample", {k: s[k] for k in list(s)[:14] if not isinstance(s[k], (list, dict))})
