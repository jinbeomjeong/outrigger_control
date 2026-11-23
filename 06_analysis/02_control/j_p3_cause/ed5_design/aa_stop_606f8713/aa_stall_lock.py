"""Lock state and command size in the stalled VBK0 LEVEL windows (run 606f8713, read-only).

For the stalled lines (final LEVEL, no READY): over the last 20 s, the share of updates each
leg is ``locked``, the max |command| (mm/s), and the share of updates with
|command| <= u_hold (0.209 mm/s, the 12b hold speed of the rod_fault record).
Writes ``aa_stall_lock.json``.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
           r"\606f8713\12b_vbk0_base_a1")


def plain(key: str) -> str:
    return key.split("#", 1)[1] if "#" in key else key


def case_of(key: str) -> str:
    t = plain(key).split("|")
    return "|".join([t[0], *t[2:]])


def main() -> None:
    out = {}
    for blk in ("b1", "b2"):
        doc = json.loads((RUN / f"VBK0_{blk}.json").read_text(encoding="utf-8"))
        rows = doc["results"] if isinstance(doc, dict) else doc
        for r in rows:
            b = r["base"]
            if b.get("t_ready_s", b.get("t_ready")) is not None or b.get("final_phase") != "level":
                continue
            u_hold = r["rod_fault"]["hold_speed_m_s"]
            with np.load(RUN / f"VBK0_{blk}_t4h" / r["t4h_file"], allow_pickle=False) as d:
                t = np.asarray(d["t_s"], float)
                u = np.asarray(d["command_m_s"], float)
                locked = np.asarray(d["locked"], float)
                s = np.asarray(d["motor_stroke_m"], float)
            m = t >= t[-1] - 20.0
            out[f"{blk}:{case_of(r['key'])}"] = {
                "locked_share": np.round(locked[m].mean(axis=0), 3).tolist(),
                "u_abs_max_mm_s": np.round(np.abs(u[m]).max(axis=0) * 1e3, 3).tolist(),
                "share_u_le_hold": np.round((np.abs(u[m]) <= u_hold).mean(axis=0), 3).tolist(),
                "stroke_span_mm": np.round((s[m].max(axis=0) - s[m].min(axis=0)) * 1e3, 3).tolist(),
                "u_hold_mm_s": round(u_hold * 1e3, 4)}
    (HERE / "aa_stall_lock.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
