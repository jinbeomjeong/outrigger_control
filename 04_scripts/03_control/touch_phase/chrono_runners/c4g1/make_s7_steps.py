"""Write the steps JSON of the S7 C4G1 runner. The result folder must not exist yet.

Usage: python -I -B -X utf8 make_s7_steps.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = r"C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe"
OUT = Path(r"C:\workspace\outrigger_control\07_results\S8\c4g1_S7_20261104")
if OUT.exists():
    raise SystemExit(f"result folder exists: {OUT}")
step = {"id": "c4g1_S7", "cwd": str(HERE), "cmd": f"{PY} -I -B -X utf8 -u {HERE / 'run_s7_c4g1.py'} --out-root {OUT}",
        "env": {"OMP_NUM_THREADS": "4", "OUTRIGGER_PLACEMENT": "pcore"}}
(HERE / "steps_S7.json").write_text(json.dumps([step], indent=1), encoding="utf-8")
print(step["cmd"])
