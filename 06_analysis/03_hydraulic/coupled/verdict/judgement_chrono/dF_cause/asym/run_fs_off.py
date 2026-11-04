"""G4 flow-off rows at event phase 0.05 s, F_s 0 and 8 kN: table cases, main-tree code, output in this scratch folder.

Same job as run_r12_off.py; two case processes at once, placement pcore. Run with -B so nothing is written next to the code.
Usage: python -I -B -X utf8 -u run_fs_off.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

MAIN = Path(r"C:\workspace\outrigger_control")
HERE = Path(__file__).resolve().parent
CASES = ("E_G4_Fs0_ph0.05", "E_G4_Fs8_ph0.05")
HASHED = ("04_scripts/02_chrono/run_S8C.py", "04_scripts/02_chrono/run_S7C.py", "04_scripts/02_chrono/run_S6C.py",
          "03_src/outrigger_sim/chrono/l2b_model.py", "03_src/outrigger_sim/chrono/l2b_actuator.py", "03_src/outrigger_sim/actuation.py",
          "03_src/outrigger_sim/runner.py", "03_src/outrigger_sim/control/c2.py", "03_src/outrigger_sim/verify/s8_control.py", "02_params/rexome33.yaml")
sys.path.insert(0, str(MAIN / "03_src"))
sys.path.insert(0, str(MAIN / "04_scripts" / "02_chrono"))


def job(case, case_dir):
    import run_S8C as s8

    if not Path(s8.__file__).resolve().is_relative_to(MAIN):
        raise SystemExit(f"wrong run_S8C: {s8.__file__}")
    return s8.job_case(case, case_dir)


def main() -> None:
    from outrigger_sim.batch import Case, run_cases

    d = HERE / time.strftime("final_E_G4_Fs0Fs8_ph0.05_off_%Y%m%d_%H%M%S")
    d.mkdir(parents=False, exist_ok=False)
    code = {f: hashlib.sha256((MAIN / f).read_bytes()).hexdigest() for f in HASHED}
    head = (MAIN / ".git/refs/heads/master").read_text(encoding="utf-8").strip()
    (d / "code_state.json").write_text(json.dumps({"main_head": head, "code_sha256": code}, indent=1), encoding="utf-8")
    t0 = time.perf_counter()
    run_cases([Case(c, {"duration_s": None}) for c in CASES], job, d, max_workers=2, placement="pcore", timeout_s=1800.0)
    print("dir", d, "wall_s", round(time.perf_counter() - t0, 1), flush=True)


if __name__ == "__main__":
    main()
