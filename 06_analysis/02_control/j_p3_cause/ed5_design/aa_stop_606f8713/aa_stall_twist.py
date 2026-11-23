"""Which completion quantity holds the stalled VBK0 LEVEL lines (run 606f8713, read-only).

For every VBK0 b1/b2 line ending in LEVEL without READY, and for the other seed of the same
case: over the last 20 s of LEVEL (stalled lines) or the 5 s before the first DONE (READY
lines), the mean command per leg (mm/s), the command pattern projected on heave / roll /
pitch / twist (+ - - + over FL FR RL RR), the diagonal twist of ``true_force_N`` and of
``lower_estimate_N`` (kN, FL+RR-FR-RL), and the fault-leg reading. Writes
``aa_stall_twist.json``.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
           r"\606f8713\12b_vbk0_base_a1")
LEGS = ("FL", "FR", "RL", "RR")
TWIST = np.array([1.0, -1.0, -1.0, 1.0])
BASIS = {"heave": np.array([1, 1, 1, 1.0]) / 2, "roll": np.array([1, -1, 1, -1.0]) / 2,
         "pitch": np.array([1, 1, -1, -1.0]) / 2, "twist": TWIST / 2}


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


def window_stats(block: str, row: dict) -> dict:
    with np.load(RUN / f"VBK0_{block}_t4h" / row["t4h_file"], allow_pickle=False) as d:
        t = np.asarray(d["t_s"], float)
        phase = np.asarray(d["phase"]).astype(str)
        u = np.asarray(d["command_m_s"], float)
        ft = np.asarray(d["true_force_N"], float)
        fe = np.asarray(d["lower_estimate_N"], float) if "lower_estimate_N" in d.files else None
        fr = np.asarray(d["lower_reading_N"], float) if "lower_reading_N" in d.files else None
    done = np.flatnonzero(phase == "done")
    if ready(row) is None:
        m = (phase == "level") & (t >= t[-1] - 20.0)
        kind = "stall_last_20s"
    else:
        m = (t >= t[done[0]] - 5.0) & (t < t[done[0]])
        kind = "5s_before_first_DONE"
    um = u[m].mean(axis=0) * 1e3
    out = {"window": kind, "t": [round(float(t[m][0]), 1), round(float(t[m][-1]), 1)],
           "u_mean_mm_s": np.round(um, 4).tolist(),
           "u_rms_mm_s": np.round(np.sqrt((u[m] ** 2).mean(axis=0)) * 1e3, 4).tolist(),
           "u_modes_mm_s": {k: round(float(um @ v), 4) for k, v in BASIS.items()},
           "twist_true_kN": round(float((ft[m] @ TWIST).mean()) / 1e3, 2)}
    if fe is not None:
        out["twist_lower_estimate_kN"] = round(float((fe[m] @ TWIST).mean()) / 1e3, 2)
        out["lower_estimate_kN"] = np.round(fe[m].mean(axis=0) / 1e3, 1).tolist()
    if fr is not None:
        out["lower_reading_kN"] = np.round(fr[m].mean(axis=0) / 1e3, 1).tolist()
    out["true_force_kN"] = np.round(ft[m].mean(axis=0) / 1e3, 1).tolist()
    out["fault_leg"] = row["rod_fault"]["leg"]
    return out


def main() -> None:
    b1, b2 = load("b1"), load("b2")
    focus = [c for c in b1 if ready(b1[c]) is None or ready(b2[c]) is None]
    out = {c: {"b1": window_stats("b1", b1[c]), "b2": window_stats("b2", b2[c])}
           for c in focus if (b1[c]["base"].get("final_phase") == "level"
                              or b2[c]["base"].get("final_phase") == "level")}
    (HERE / "aa_stall_twist.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for c, v in out.items():
        for blk in ("b1", "b2"):
            w = v[blk]
            print(c, blk, w["window"], "leg", w["fault_leg"], "modes", w["u_modes_mm_s"],
                  "tw_true", w["twist_true_kN"], "tw_est", w.get("twist_lower_estimate_kN"),
                  "est", w.get("lower_estimate_kN"), "true", w["true_force_kN"])


if __name__ == "__main__":
    main()
