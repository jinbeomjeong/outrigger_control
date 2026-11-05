"""Prepare the C4G2-only acceptance bundle without running a simulation (criteria_c4g2_only.md).

Seeds acceptance/c4g2_only/noise/*.partial.jsonl: rows of the C4G2 + K1 run with no retrigger deferral (K1 cannot have acted, so the C4G2-only run is the same) and the
stored C4G2-only split rows. r79 resumes on the seeded keys and runs the rest: rows where K1 acted, and a check sample of inactive rows held out of the seed.
Copies the same-code off grid files. Writes steps_c4g2only.json for make_runner.py and manifest.json. Refuses to overwrite an existing partial file.
Usage: python -I -B prepare.py [--workers 15]
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "c4g2k1"))
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
OUT = ACC / "c4g2_only"
WT = HERE.parent / "cad_c4g2" / "wt"
ENV_DIR = Path(r"C:\ProgramData\miniforge3\envs\dynamics-dev")
PY = str(ENV_DIR / "python.exe")
LAUNCH = HERE.parent / "c4g2k1" / "acc_launch.py"
JUDGE = HERE.parent / "c4g2k1" / "acc_judge.py"
VERIFY = HERE / "verify_reuse.py"
S8 = WT / "04_scripts/03_control/s8"
SEED = 20261105
SAMPLE = {"r79_L1L2": (10, 10), "r79_L3": (5, 5)}
"""(most re-approach starts, random) inactive rows rerun as the check of the reuse rule."""


def partial(path: Path) -> dict:
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        rows[rec["key"]] = rec
    return rows


def name_of(event) -> str:
    return str(event.get("name")) if isinstance(event, dict) else str(event[-1]) if isinstance(event, (list, tuple)) else str(event)


def acted(row: dict) -> bool:
    return any(name_of(e).endswith(":retrigger") for e in row["events"])


def starts(row: dict) -> int:
    return sum(name_of(e).startswith("leg_reapproach_start") for e in row["events"])


def base_env() -> dict:
    path = ";".join([str(ENV_DIR), str(ENV_DIR / "Library/mingw-w64/bin"), str(ENV_DIR / "Library/usr/bin"), str(ENV_DIR / "Library/bin"), str(ENV_DIR / "Scripts"), str(ENV_DIR / "bin"), r"C:\Windows\System32", r"C:\Windows", r"C:\Program Files\Git\cmd"])
    return {"ACC_WT": str(WT), "ACC_COMBO": "c4g2", "CONDA_PREFIX": str(ENV_DIR), "CONDA_DEFAULT_ENV": "dynamics-dev", "PATH": path, "MKL_THREADING_LAYER": "TBB", "MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "NUMBA_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1", "OUTRIGGER_ACC": "c4g2only"}


def step(sid: str, script: Path, args: str, **env) -> dict:
    return {"id": sid, "cmd": f"{PY} -I -B {LAUNCH} {script} {args}", "cwd": str(WT), "env": {**base_env(), "ACC_PROVENANCE": str(OUT / "provenance" / f"{sid}.json"), **env}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=15)
    me = ap.parse_args()
    for sub in ("noise", "grid", "provenance"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    split = partial(ACC / "split/r79_c4g2.json.partial.jsonl")
    rng = random.Random(SEED)
    manifest = {"seed": SEED, "rule": "criteria_c4g2_only.md", "files": {}}
    for name, (n_near, n_rand) in SAMPLE.items():
        rows = partial(ACC / f"noise/{name}.json.partial.jsonl")
        act = sorted(k for k, r in rows.items() if acted(r))
        from_split = sorted(k for k in rows if k in split)
        inactive = sorted(k for k in rows if k not in act and k not in split)
        near = sorted(inactive, key=lambda k: (-starts(rows[k]), k))[:n_near]
        rest = [k for k in inactive if k not in near]
        sample = near + rng.sample(rest, n_rand)
        seeded = [k for k in inactive if k not in sample]
        path = OUT / "noise" / f"{name}.json.partial.jsonl"
        if path.exists():
            raise SystemExit(f"exists, not overwritten: {path}")
        with path.open("w", encoding="utf-8") as sink:
            for k in seeded:
                sink.write(json.dumps({**rows[k], "reuse": "C4G2+K1 row without retrigger deferral"}) + "\n")
            for k in from_split:
                sink.write(json.dumps({**split[k], "reuse": "stored C4G2-only split row"}) + "\n")
        todo = [k for k in act if k not in split] + sample
        manifest["files"][name] = {"rows": len(rows), "acted": len(act), "from_split": from_split, "seeded_inactive": len(seeded), "to_run": len(todo), "acted_to_run": [k for k in act if k not in split], "sample_near": near, "sample_random": sample[n_near:],
                                   "near_starts": [starts(rows[k]) for k in near], "cpu_s_to_run": round(sum(rows[k]["wall_s"] for k in todo)), "peak_wset_MB_max": max(r.get("worker_peak_wset_MB", 0) for r in rows.values())}
    for off in ("grid_r69_top_off.json", "grid_r69_bottom_off.json"):
        shutil.copy2(ACC / "grid" / off, OUT / "grid" / off)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    r79 = S8 / "r79_L3L4_final.py"
    r67, r69 = S8 / "r67_g1_screen.py", S8 / "r69_g5_screen.py"
    verify = lambda sid, name: {"id": sid, "cmd": f"{PY} -I -B {VERIFY} {name}", "cwd": str(HERE), "env": base_env()}
    steps = [step("noise_L1L2", r79, f"{WT} run {OUT / 'noise' / 'r79_L1L2.json'} --workers {me.workers} --levels L1,L2", R72_PATH="per_leg", ACC_R79_INCLUDE_PAD_A="1"),
             verify("verify_L1L2", "r79_L1L2"),
             step("grid_r67_main", r67, f"{WT} {OUT / 'grid' / 'grid_r67_main.json'} {me.workers}", R67_MODE="screen", R67_OFFSETS="0,0.05"),
             step("grid_r67_top", r67, f"{WT} {OUT / 'grid' / 'grid_r67_top.json'} {me.workers}", R67_MODE="screen", R67_OFFSETS="0,0.025,0.05,0.075", R67_FILTER="screen|top"),
             step("grid_r69_top", r69, f"{WT} {OUT / 'grid' / 'grid_r69_top.json'} {me.workers}", R67_FILTER="|top|"),
             step("grid_r69_bottom", r69, f"{WT} {OUT / 'grid' / 'grid_r69_bottom.json'} {me.workers}", R67_FILTER="|bottom|"),
             step("noise_L3", r79, f"{WT} run {OUT / 'noise' / 'r79_L3.json'} --workers {me.workers} --levels L3", R72_PATH="per_leg"),
             verify("verify_L3", "r79_L3"),
             {"id": "judge", "cmd": f"{PY} -I -B {JUDGE} --acc {OUT}", "cwd": str(HERE.parent / "c4g2k1"), "env": base_env()}]
    (HERE / "steps_c4g2only.json").write_text(json.dumps(steps, indent=1), encoding="utf-8")
    print(json.dumps({k: {x: v[x] for x in ("rows", "acted", "seeded_inactive", "to_run", "cpu_s_to_run", "peak_wset_MB_max", "near_starts")} | {"from_split": len(v["from_split"])} for k, v in manifest["files"].items()}, indent=0))


if __name__ == "__main__":
    main()
