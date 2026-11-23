"""What the VBK0 lines do while stuck in LEVEL without READY (run 606f8713 12b A/A stop).

For every VBK0 line of b1/b2 whose READY is missing, and its other-seed partner: per 20 s
window from the first LEVEL, the number of updates with a non-zero command per leg, the
stroke change per leg (mm), the minimum true cylinder force (kN), and the T4h meta_json
event names after the first LEVEL (counts and the first 25). Writes ``aa_stall.json``.
Read-only; VBK0 files only.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
           r"\606f8713\12b_vbk0_base_a1")
LEGS = ("FL", "FR", "RL", "RR")


def plain(key: str) -> str:
    return key.split("#", 1)[1] if "#" in key else key


def case_of(key: str) -> str:
    t = plain(key).split("|")
    return "|".join([t[0], *t[2:]])


def ready(row: dict):
    b = row["base"]
    return b.get("t_ready_s", b.get("t_ready"))


def load(block: str) -> dict:
    doc = json.loads((RUN / f"VBK0_{block}.json").read_text(encoding="utf-8"))
    rows = doc["results"] if isinstance(doc, dict) else doc
    return {case_of(r["key"]): r for r in rows}


def summary(block: str, row: dict) -> dict:
    with np.load(RUN / f"VBK0_{block}_t4h" / row["t4h_file"], allow_pickle=False) as d:
        t = np.asarray(d["t_s"], float)
        phase = np.asarray(d["phase"]).astype(str)
        u = np.asarray(d["command_m_s"], float)
        s = np.asarray(d["motor_stroke_m"], float)
        fmin = np.asarray(d["true_force_min_N"], float) if "true_force_min_N" in d.files else None
        locked = np.asarray(d["locked"]) if "locked" in d.files else None
        meta = json.loads(str(d["meta_json"]))
    lev = np.flatnonzero(phase == "level")
    t0 = float(t[lev[0]]) if lev.size else float(t[0])
    windows = []
    edges = np.arange(t0, t[-1] + 20.0, 20.0)
    for a, b in zip(edges[:-1], edges[1:]):
        m = (t >= a) & (t < b)
        if not m.any():
            continue
        idx = np.flatnonzero(m)
        win = {"t": [round(float(a), 1), round(float(b), 1)],
               "phases": dict(Counter(phase[m])),
               "n_nonzero_u": [int((np.abs(u[m, j]) > 1e-9).sum()) for j in range(4)],
               "d_stroke_mm": [round(float((s[idx[-1], j] - s[idx[0], j]) * 1e3), 2)
                               for j in range(4)]}
        if fmin is not None:
            arr = fmin[m]
            win["true_force_min_kN"] = (np.round(arr.min(axis=0) / 1e3, 1).tolist()
                                        if arr.ndim > 1 else round(float(arr.min()) / 1e3, 1))
        if locked is not None:
            win["locked_frac"] = np.round(np.asarray(locked[m], float).mean(axis=0), 2).tolist() \
                if np.asarray(locked).ndim > 1 else None
        windows.append(win)
    events = meta.get("events") or []
    after = []
    for e in events:
        if isinstance(e, (list, tuple)) and len(e) >= 2:
            if float(e[0]) >= t0:
                after.append([round(float(e[0]), 1), str(e[1])])
        else:
            after.append([None, str(e)])
    names = Counter(x[1].split(":", 1)[0] for x in after)
    return {"t_first_level": round(t0, 1), "t_end": round(float(t[-1]), 1),
            "u_shape": list(u.shape), "windows": windows,
            "event_names_after_level": dict(names), "events_after_level_head": after[:25],
            "meta_keys": sorted(meta.keys())}


def main() -> None:
    b1, b2 = load("b1"), load("b2")
    focus = [c for c in b1 if ready(b1[c]) is None or ready(b2[c]) is None]
    focus.append("L2|g6|61|ref|S1|top|Fs4")
    out = {}
    for c in focus:
        out[c] = {"b1": summary("b1", b1[c]), "b2": summary("b2", b2[c]),
                  "ready": [ready(b1[c]), ready(b2[c])]}
    (HERE / "aa_stall.json").write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                        encoding="utf-8")
    print(json.dumps({"cases": focus}))


if __name__ == "__main__":
    main()
