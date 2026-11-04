"""Print array names of the stored S7 run and its end summary. Read only.

Usage: python -I -B -X utf8 peek_s7b.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

D = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_FINAL-REP_20261030_223359\S9SL_X6rb_J1_B_top_Fs4_rm2p86_p0")


def main() -> None:
    for f in ("record/record.npz", "step_series.npz", "r8_series.npz", "completion_series.npz", "controller_commands.npz"):
        z = np.load(D / f, allow_pickle=False)
        print(f, {k: z[k].shape for k in z.files})
    res = json.loads((D / "result.json").read_text(encoding="utf-8"))
    print("t_loop_start_s", res["t_loop_start_s"], "phases", res["phases"])
    print("events", str(res["events"])[:1500])
    print("step_series meta", str(res["step_series"])[:500])
    print("s9_rows", str(res["s9_rows"])[:600])
    p = res["p3_records"]
    print("p3 keys", list(p)[:60])
    print("p3b keys", list(res["p3b"])[:40] if isinstance(res["p3b"], dict) else str(res["p3b"])[:300])
    print("meta", list(res["controller_meta"])[:40])
    rj = json.loads((D / "result_rejudge_rev60.json").read_text(encoding="utf-8"))
    print("rejudge keys", list(rj)[:30])


if __name__ == "__main__":
    main()
