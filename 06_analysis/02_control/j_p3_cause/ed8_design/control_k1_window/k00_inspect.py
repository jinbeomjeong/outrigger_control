"""k00: list the keys / shapes of the dynamics d00 re-run raw files (no values judged).

Usage: conda run -n dynamics-dev python -I -B k00_inspect.py
Output: k00_out.txt (this folder).
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "dynamics_d1_d3" / "rerun_raw"
RUN = "R12_top-FR-Fs8-o0.0_D8-M-a2"


def main() -> int:
    lines = []
    t4h = np.load(RAW / "t4h" / f"{RUN}.npz", allow_pickle=False)
    lines.append("t4h keys:")
    for k in t4h.files:
        lines.append(f"  {k} {t4h[k].shape} {t4h[k].dtype}")
    for kind in ("plant", "ctrl"):
        z = np.load(RAW / "logs" / f"{RUN}_{kind}.npz", allow_pickle=False)
        lines.append(f"{kind} keys ({len(z.files)}):")
        for k in z.files[:80]:
            lines.append(f"  {k} {z[k].shape} {z[k].dtype}")
    cue = json.loads((RAW / "logs" / f"{RUN}_cue.json").read_text(encoding="utf-8"))
    lines.append(f"cue top keys: {list(cue.keys())}")
    for key, val in cue.items():
        if isinstance(val, list) and val:
            lines.append(f"  {key}: list[{len(val)}] first keys {list(val[0].keys()) if isinstance(val[0], dict) else type(val[0])}")
        else:
            lines.append(f"  {key}: {type(val).__name__}")
    runs = (RAW / "runs.jsonl").read_text(encoding="utf-8").splitlines()
    first = json.loads(runs[0])
    lines.append(f"runs.jsonl lines {len(runs)}, first keys {sorted(first.keys())[:60]}")
    (HERE / "k00_out.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
