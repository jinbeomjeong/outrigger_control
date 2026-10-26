"""M-3 batch: every case key of ``m3_run.CASES`` with the soil response on and off, two Chrono
processes at a time (the on / off pair of one case together).

Usage: ``python -I -X utf8 -u 04_scripts/02_chrono/s9_merge/m3_batch.py <out_root> [keys...]``
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = ("flat", "rpB", "roll55", "re1bf_l1", "s8_re1bf")
TIMEOUT_S = 3600.0


def main(argv: list[str]) -> int:
    out_root = Path(argv[0]).resolve()
    keys = argv[1:] or list(ORDER)
    out_root.mkdir(parents=True, exist_ok=True)
    log = out_root / "progress.log"
    rows = []

    def note(text: str) -> None:
        line = f"{dt.datetime.now().isoformat(timespec='seconds')} {text}"
        print(line, flush=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    for key in keys:
        procs = {}
        for variant in ("on", "off"):
            d = out_root / f"{key}__{variant}"
            d.mkdir(parents=True, exist_ok=True)
            fh = (d / "case.log").open("w", encoding="utf-8")
            p = subprocess.Popen([sys.executable, "-I", "-X", "utf8", "-u",
                                  str(HERE / "m3_run.py"), key, variant, str(out_root)],
                                 stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            procs[variant] = (p, fh, time.perf_counter())
            note(f"START {key} {variant} pid={p.pid}")
        for variant, (p, fh, t0) in procs.items():
            try:
                rc = p.wait(timeout=TIMEOUT_S)
            except subprocess.TimeoutExpired:
                p.kill()
                rc = "timeout"
            fh.close()
            wall = time.perf_counter() - t0
            rows.append({"key": key, "variant": variant, "rc": rc, "wall_s": wall})
            note(f"END {key} {variant} rc={rc} wall={wall:.0f}s")
    (out_root / "batch.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    note("BATCH DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
