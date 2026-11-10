"""Second read of the R16 gap runs: miss details, event-leg rows, stroke at TOUCH end, pitch lever check."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "tables_r16"
CASE = "G1L_RE1bF_FL_top_o050_Fs4"
NAMES = ("stored_worktree_code", "r16_mirror2_d000", "r16_mirror2_d035", "r16_mirror2_d070")
INPUT = {"r16_mirror2_d000": (-2.0, 2.0, -2.0, 2.0), "r16_mirror2_d035": (-1.65, 2.35, -1.65, 2.35), "r16_mirror2_d070": (-1.3, 2.7, -1.3, 2.7)}
res = json.loads((OUT / "r16_results.json").read_text(encoding="utf-8"))
report = {}
for n in NAMES:
    doc = json.loads((OUT / f"verify_{n}.json").read_text(encoding="utf-8"))
    sm = doc["s8_metrics"][CASE]
    print("==", n, "item9 keys", list(sm["item9"])[:30])
    report[n] = {"item9": sm["item9"], "g1": sm.get("g1")}
    for r in doc["rows"]:
        if r.get("case") == CASE and any(s in r["item"] for s in ("event legs (settled", "record: re-approach", "1 ms instantaneous", "item 9 J_C M1", "item 9 J_P M1")):
            print(r["item"][:90], "=>", json.dumps(r.get("value"))[:700])
            print("   note", str(r.get("note") or r.get("detail") or "")[:500])
(OUT / "r16_item9_g1.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")

runs = res["runs"]
base = runs["stored_off"]["contact"]
print("lever check: stroke late = stroke change - input; pitch drop against gap 0 at that leg's first contact")
fit_f, fit_r = [], []
for n, inp in INPUT.items():
    c = runs[n]["contact"]
    ds = np.array(c["s_motor_mm"]) - np.array(base["s_motor_mm"])
    late = ds - np.array(inp)
    dp = np.radians(np.array(c["pitch_rise_at_first_deg"]) - np.array(base["pitch_rise_at_first_deg"]))
    print(n, "ds", np.round(ds, 3), "late", np.round(late, 3), "dpitch mrad", np.round(dp * 1e3, 4), "late/dpitch m", np.round(late[[0, 1, 3]] * 1e-3 / dp[[0, 1, 3]], 3))
    fit_f += [late[0] * 1e-3 / dp[0], late[1] * 1e-3 / dp[1]]
    fit_r += [late[3] * 1e-3 / dp[3]]
print("arm front mean, std", np.mean(fit_f), np.std(fit_f), "arm rear mean, std", np.mean(fit_r), np.std(fit_r))
for n in ("stored_off", *INPUT):
    d = HERE / "runs_r16" / n / CASE if n in INPUT else Path(r"C:\workspace\outrigger_control\07_results\S8\final_G1L_RE1bF_FL_top_o050_Fs4_20261031_004637") / CASE
    p = np.load(d / "pads.npz", allow_pickle=False)
    rec = np.load(d / "record" / "record.npz", allow_pickle=False)
    r = json.loads((d / "result.json").read_text(encoding="utf-8"))
    off = float(rec["t"][-1]) - float(r["s8_end"]["end_t_s"])
    k = int(np.searchsorted(p["t"] - off, runs[n]["t_touch_end_s"]))
    print(n, "s_te", np.round(p["s_motor"][k] * 1e3, 3), "F_te", np.round(p["F_cyl"][k - 200:k].mean(axis=0) / 1e3, 1))
