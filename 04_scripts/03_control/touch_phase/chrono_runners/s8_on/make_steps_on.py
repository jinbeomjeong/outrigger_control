"""Steps of the two flow-on eps runs; stored baseline of the slope ratio; window-crossing margin on the stored flow-on run."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MAIN = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(MAIN / "03_src"))
from outrigger_sim.control.c2 import C2Config, C2Controller  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402

D = MAIN / "07_results/S9/batch_COUPLED_eta085_20261104_142213/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0"
LEGS = ("FL", "FR", "RL", "RR")
z = np.load(D / "flow_series.npz", allow_pickle=True)
rows, cols = z["rows"], [str(c) for c in z["columns"]]
i = {c: k for k, c in enumerate(cols)}
ft, v = rows[:, i["t"]], rows[:, [i[f"v_{l}"] for l in LEGS]]
s = np.load(D / "step_series.npz", allow_pickle=False)
st, sm = s["t_s"], s["s_motor_m"]
sel = (st[:-1] >= 13.4) & (st[1:] <= 14.95)
slope = (sm[1:] - sm[:-1])[sel] / np.diff(st)[sel][:, None]
vm = np.column_stack([np.interp(st[:-1][sel], ft, v[:, j]) for j in range(4)])
print("stored slope / v in the same window", np.round((slope / vm).mean(axis=0), 6))
rec = np.load(D / "record/record.npz", allow_pickle=False)
c2 = C2Controller.from_params(load_params(level="top"), C2Config().with_10hz_d1())
w = (c2._touch_extension_m - c2.config.r8.touch_window_m) * 1e3  # noqa: SLF001
tr, sm10, u = rec["t"], rec["s_motor"] * 1e3, rec["u_cmd"] * 1e3
for j, leg in enumerate(LEGS):
    above = np.flatnonzero((tr > 13.5) & (sm10[:, j] >= w[j]))[0]
    print(leg, "first 10 Hz sample at or above window start: t", round(float(tr[above]), 1), "margin mm", round(float(sm10[above, j] - w[j]), 3), "previous margin", round(float(sm10[above - 1, j] - w[j]), 3), "eps 2e-3 deficit there", round(0.002 * float(sm10[above, j]), 3))

PY = r"C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe"
DRIVER = HERE / "run_s8_on_eps.py"
RESULTS = MAIN / "07_results" / "S9"
RUNS = {"A": ("s8on_eps1e-3", 1.0e-3, "batch_s8on_eps1e-3_20261104"), "B": ("s8on_eps2e-3", 2.0e-3, "batch_s8on_eps2e-3_20261104")}
for key, (sid, eps, folder) in RUNS.items():
    out = RESULTS / folder
    if out.exists():
        raise SystemExit(f"result folder exists: {out}")
    step = {"id": sid, "cwd": str(MAIN),
            "cmd": f"{PY} -I -B -X utf8 -u {DRIVER} --eps {eps:g} --gate-s 12.85 --out-root {out} --step-id {sid}",
            "env": {"OMP_NUM_THREADS": "4", "OUTRIGGER_PLACEMENT": "pcore"}}
    (HERE / f"steps_{key}.json").write_text(json.dumps([step], indent=1), encoding="utf-8")
    print(key, step["cmd"])
print(json.dumps(json.loads((HERE / "bitcheck" / "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0" / "eps_wrapper.json").read_text(encoding="utf-8"))["main_head"]))
