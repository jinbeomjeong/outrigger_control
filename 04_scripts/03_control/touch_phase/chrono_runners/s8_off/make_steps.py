"""Write the steps JSON of the two flow-off eps runs. Result folders must not exist yet."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = r"C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe"
DRIVER = HERE / "run_s8_eps.py"
RESULTS = Path(r"C:\workspace\outrigger_control\07_results\S9")
RUNS = {"A": ("s8off_eps1e-3", 1.0e-3, "batch_s8off_eps1e-3_20261104"),
        "B": ("s8off_eps2e-3", 2.0e-3, "batch_s8off_eps2e-3_20261104")}
GATE_S = 12.85
for key, (sid, eps, folder) in RUNS.items():
    out = RESULTS / folder
    if out.exists():
        raise SystemExit(f"result folder exists: {out}")
    step = {"id": sid, "cwd": r"C:\workspace\outrigger_control",
            "cmd": f"{PY} -I -X utf8 -u {DRIVER} --eps {eps:g} --gate-s {GATE_S:g} --out-root {out}",
            "env": {"OMP_NUM_THREADS": "4", "OUTRIGGER_PLACEMENT": "pcore"}}
    (HERE / f"steps_{key}.json").write_text(json.dumps([step], indent=1), encoding="utf-8")
    print(key, step["cmd"])
