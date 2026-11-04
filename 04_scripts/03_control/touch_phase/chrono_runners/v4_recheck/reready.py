"""Re-READY after the event from result.json phases, old and new, and the stored final RE1bF F_s 8 lift by both definitions. Read only.

Output: v4_recheck/recheck_reready.json and a print.
Usage: python -I -B -X utf8 reready.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

MAIN = Path(r"C:\workspace\outrigger_control")
OUT = MAIN / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/v4_recheck"
S8 = MAIN / "07_results/S8"
NEW = S8 / "final_v4recheck_20261104_202815"
REST, P1R = "rest_20261024_233615", "p1r_20261024_222013"
SOURCE = {"N_G4_Fs0_pressure": REST, "N_G4_Fs4_pressure": REST, "N_G4_Fs8_pressure": REST, "N_SS_Fs0_pressure": REST, "N_SS_Fs4_pressure": REST,
          "N_SS_Fs8_pressure": REST, "E_SS_Fs0": P1R, "E_SS_Fs8": P1R, "E_RE1bF_Fs0": P1R, "E_RE1bP_Fs0": P1R, "E_RE1bP_Fs8": P1R}


def rr(d: Path) -> dict:
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    te, ph = float(res["event_t_s"]), res["phases"]
    idx = next((i for i, (t, q) in enumerate(ph) if t > te - 1e-9 and q in ("level", "touch", "probe")), None)
    ready = next((t for t, q in ph[(idx or 0) + 1:] if q == "ready"), None) if idx is not None else None
    return {"event_s": te, "first_active_s": None if idx is None else ph[idx][0], "re_ready_after_event_s": None if ready is None else ready - te, "phases": ph}


def main() -> None:
    out = {c: {"old": rr(S8 / b / c), "new": rr(NEW / c)} for c, b in SOURCE.items()}
    (OUT / "recheck_reready.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for c, v in out.items():
        print(c, "old", round(v["old"]["re_ready_after_event_s"] or -1, 2), "new", round(v["new"]["re_ready_after_event_s"] or -1, 2), "active new", v["new"]["first_active_s"], "phases new", [(round(t, 1), q) for t, q in v["new"]["phases"]][4:])
    d = S8 / "final_E_RE1bF_Fs8_20261031_000914/E_RE1bF_Fs8"
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    rec = np.load(d / "record/record.npz", allow_pickle=False)
    p = np.load(d / "pads.npz", allow_pickle=False)
    off = float(rec["t"][-1]) - float(res["s8_end"]["end_t_s"])
    t = p["t"] - off
    post = t >= float(res["event_t_s"])
    dt = np.diff(t, prepend=t[0] - 1e-3)
    print("final E_RE1bF_Fs8 pads airborne RR s", float(dt[post][p["airborne"][post, 3].astype(bool)].sum()), "re-READY", rr(d)["re_ready_after_event_s"])
    for f in (OUT.parent).rglob("verify_final_E_RE1bF_Fs8*.json"):
        doc = json.loads(f.read_text(encoding="utf-8"))
        print(f, [(r["item"][:30], r["value"]) for r in doc["rows"] if r.get("case") == "E_RE1bF_Fs8" and r["item"].startswith(("item 9 M5", "4 max pressure in"))])


if __name__ == "__main__":
    main()
