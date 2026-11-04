"""Run the project judge (verify.s8_control.judge_batch) on coupled / stored rigid batches.

Read only for the batches: the verify file goes to judgement_chrono/verify. Pins itself to the given
logical processors (short post-processing while the soil runs use the other cores).

Usage: conda run -n dynamics-dev python -I judge_batches.py <mask hex> <on|off|all>
"""
from __future__ import annotations

import ctypes
import json
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control")
HERE = ROOT / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono"
OUT = HERE / "verify"
sys.path.insert(0, str(ROOT / "03_src"))

CASES = {
    "R2": "K24_top_fdown3.5_Fs4", "R4": "K24_top_roll5.5_Fs4", "R16": "G1L_RE1bF_FL_top_o050_Fs4",
    "R12": "E_G4_Fs4", "R6": "K0V_top_rpB_Fs0", "R8": "A_middle_rpB_Fs0", "R9": "A_bottom_rpB_Fs0",
}


def pin(mask: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    kernel.SetProcessAffinityMask.restype = wintypes.BOOL
    if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), mask):
        raise OSError(ctypes.get_last_error(), "SetProcessAffinityMask")


def batches(which: str) -> list[Path]:
    found = []
    for case in CASES.values():
        if which in ("on", "all"):
            found += sorted((ROOT / "07_results/S8").glob(f"coupled_eta085_{case}_*"))[-1:]
        if which in ("off", "all"):
            found += sorted((ROOT / "07_results/S8").glob(f"final_{case}_2*"))[-1:]
    return found


def main() -> None:
    pin(int(sys.argv[1], 16))
    from outrigger_sim.verify.s8_control import judge_batch

    OUT.mkdir(exist_ok=True)
    for batch in batches(sys.argv[2]):
        out = OUT / f"verify_{batch.name}.json"
        if out.exists():
            continue
        start = time.perf_counter()
        path = judge_batch(batch, out, ref_batch=None, lookup_batches=[], deferred_ref=None)
        meta = json.loads(path.read_text(encoding="utf-8"))["meta"]
        print(batch.name, f"{time.perf_counter() - start:.1f} s", "rows", meta["rows"], "failed", meta["failed"],
              "hold", meta["hold"], flush=True)


if __name__ == "__main__":
    main()
