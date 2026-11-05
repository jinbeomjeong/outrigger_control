"""Sidecar of the C4G2-only runner: available memory 60, 120 and 300 s after the start, appended to a log. No effect on the run. Usage: python -I -B mem_watch.py <log>"""
import sys
import time
from pathlib import Path

import psutil

log = Path(sys.argv[1])
t0 = time.monotonic()
for mark in (60, 120, 300):
    time.sleep(max(0.0, mark - (time.monotonic() - t0)))
    vm = psutil.virtual_memory()
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"{time.strftime('%H:%M:%S')} +{mark}s available_GB {vm.available / 2**30:.2f} of {vm.total / 2**30:.2f}\n")
