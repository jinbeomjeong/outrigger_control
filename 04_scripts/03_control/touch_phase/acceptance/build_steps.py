"""Steps of the acceptance runners E1 and E2. Prints the counts; writes steps_E1.json, steps_E2.json, env.json."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = HERE.parent
WT = SCRATCH / "cad_c4g2" / "wt"
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
PY = r"C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe"
ENV_DIR = Path(PY).parent
LAUNCH = HERE / "acc_launch.py"
MASK_E1, MASK_E2 = "0x00FF0000", "0x0F000000"
WORKERS_E1, WORKERS_E2 = 8, 4
S8 = WT / "04_scripts/03_control/s8"
S9 = WT / "04_scripts/03_control/s9"
PATH_VALUE = ";".join([str(ENV_DIR), str(ENV_DIR / "Library/mingw-w64/bin"), str(ENV_DIR / "Library/usr/bin"), str(ENV_DIR / "Library/bin"),
                       str(ENV_DIR / "Scripts"), str(ENV_DIR / "bin"), os.environ.get("SystemRoot", r"C:\Windows") + r"\System32", os.environ.get("SystemRoot", r"C:\Windows"), r"C:\Program Files\Git\cmd"])
BASE_ENV = {"ACC_WT": str(WT), "ACC_COMBO": "both", "CONDA_PREFIX": str(ENV_DIR), "CONDA_DEFAULT_ENV": "dynamics-dev", "PATH": PATH_VALUE,
            "MKL_THREADING_LAYER": "TBB", "MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "NUMBA_NUM_THREADS": "1",
            "PYTHONDONTWRITEBYTECODE": "1", "OUTRIGGER_ACC": "c4g2k1"}


def step(sid: str, script: Path, args: str, **env) -> dict:
    return {"id": sid, "cmd": f'{PY} -I -B {LAUNCH} {script} {args}', "cwd": str(WT),
            "env": {**BASE_ENV, "ACC_PROVENANCE": str(ACC / "provenance" / f"{sid}.json"), **env}}


def regression_steps(mask: str, workers: int) -> list[dict]:
    """The 118 rows of the stored clip rerun list (py_c2clip/rerun_commands.ps1), same selections, new output folder."""
    text = (SCRATCH / "py_c2clip" / "rerun_commands.ps1").read_text(encoding="utf-8")
    steps, env, index = [], {}, 0
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("$env:") and "MKL_THREADING" not in line:
            for name, value in re.findall(r"\$env:(\w+) = (?:'([^']*)'|\$mask)", line):
                env[name] = value or mask
            continue
        if line.startswith("Remove-Item Env:"):
            for name in re.findall(r"Env:(\w+)", line):
                env.pop(name, None)
            continue
        if not line.startswith("& $py"):
            continue
        index += 1
        body = line.split("-I ", 1)[1]
        script_rel, args = body.split(" ", 1)
        args = args.replace("(Get-Location).Path", str(WT)).replace("$workers", str(workers)).replace("$mask", mask)
        args = re.sub(r"06_analysis/02_control/s[89]/rev91/(\w+\.json)", lambda m: str(ACC / "regression" / m.group(1)), args)
        args = args.replace("'", '"')
        steps.append(step(f"reg{index}", WT / script_rel, args, **env))
    return steps


def grid_steps(workers: int) -> list[dict]:
    steps = []
    grid = (("grid_r67_main", S8 / "r67_g1_screen.py", {"R67_MODE": "screen", "R67_OFFSETS": "0,0.05"}, "both"),
            ("grid_r67_top", S8 / "r67_g1_screen.py", {"R67_MODE": "screen", "R67_OFFSETS": "0,0.025,0.05,0.075", "R67_FILTER": "screen|top"}, "both"),
            ("grid_r69_top", S8 / "r69_g5_screen.py", {"R67_FILTER": "|top|"}, "both"),
            ("grid_r69_bottom", S8 / "r69_g5_screen.py", {"R67_FILTER": "|bottom|"}, "both"),
            ("grid_r69_top_off", S8 / "r69_g5_screen.py", {"R67_FILTER": "|top|"}, "off"),
            ("grid_r69_bottom_off", S8 / "r69_g5_screen.py", {"R67_FILTER": "|bottom|"}, "off"))
    for sid, script, env, combo in grid:
        steps.append(step(sid, script, f"{WT} {ACC / 'grid' / (sid + '.json')} {workers}", ACC_COMBO=combo, **env))
    return steps


def main() -> None:
    (ACC / "provenance").mkdir(parents=True, exist_ok=True)
    e1 = regression_steps(MASK_E1, WORKERS_E1) + grid_steps(WORKERS_E1)
    e1.append(step("soil_A", S9 / "s9_soil_event_screen.py", f"{WT} {ACC / 'soil' / 'soil_A.json'} {WORKERS_E1}", R426A_SET="all"))
    d8_env = {**BASE_ENV, "ACC_PROVENANCE": str(ACC / "provenance" / "d8.json")}
    e1.append({"id": "d8", "cmd": f"{PY} -I -B {HERE / 'acc_d8.py'} {ACC / 'd8' / 'd8_both.json'} --workers {WORKERS_E1}", "cwd": str(WT), "env": d8_env})
    e1.append({"id": "d8_main_off", "cmd": f"{PY} -I -B {HERE / 'acc_d8.py'} {ACC / 'd8' / 'd8_main_off.json'} --workers {WORKERS_E1} --stage main", "cwd": str(WT),
               "env": {**d8_env, "ACC_COMBO": "off"}})
    e1.append({"id": "crawler", "cmd": f"{PY} -I -B {HERE / 'acc_crawler.py'} {ACC / 'crawler' / 'crawler_both.json'} --workers {WORKERS_E1}", "cwd": str(WT), "env": d8_env})
    r79 = S8 / "r79_L3L4_final.py"
    for level in ("L3", "L4"):
        e1.append(step(f"noise_{level}", r79, f"{WT} run {ACC / 'noise' / f'r79_{level}.json'} --workers {WORKERS_E1} --levels {level}", R72_PATH="per_leg"))
    e2 = [step("noise_L1L2", r79, f"{WT} run {ACC / 'noise' / 'r79_L1L2.json'} --workers {WORKERS_E2} --levels L1,L2", R72_PATH="per_leg", ACC_R79_INCLUDE_PAD_A="1")]
    (HERE / "steps_E1.json").write_text(json.dumps(e1, indent=1), encoding="utf-8")
    (HERE / "steps_E2.json").write_text(json.dumps(e2, indent=1), encoding="utf-8")
    print("E1", [s["id"] for s in e1])
    print("E2", [s["id"] for s in e2])
    for s in e1[:6]:
        print(s["id"], s["cmd"][:220], {k: v[:60] for k, v in s["env"].items() if k.startswith(("R79", "R72", "R426", "S9"))})
    json.dump({k: v for k, v in BASE_ENV.items()}, sys.stdout, indent=0)


if __name__ == "__main__":
    main()
