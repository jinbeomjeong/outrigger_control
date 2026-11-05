"""Values of the d003 row against 1a (C4G2 + K1, t_ev 0.03 s earlier) and 1b (off), with the command prefix check. Read only; no judgement.

Prefix: controller_commands.npz issued_u_m_s and t_s, exact compare before the earlier event time of a pair; pre-event re-approach and K1 events listed.
Usage: python -I -B -X utf8 extract_d003.py preview   (1a against 1b, no d003 needed; print only)
       python -I -B -X utf8 extract_d003.py           (writes k1soil/d003_values.json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

BATCH = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_k1soil_G1_20261105")
OUT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono\k1soil")
D003, ON, OFF, BASE = "S9EV_G1_FLFs0_RE1bF_d003_C4G2", "S9EV_G1_FLFs0_RE1bF_on", "S9EV_G1_FLFs0_RE1bF_off", "S9EV_G1_FLFs0_base"
MARKS = ("leg_reapproach", "TOUCH_TWIST", "LIFT_PAUSED", "WARN", "FAULT", "liftoff", "LOC")


def row(case: str) -> dict:
    d = BATCH / case
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    se = res.get("soil_event") or {}
    t_ev = (se.get("driver") or {}).get("t_ev_s")
    return {"case": case, "t_ev_s": t_ev, "t_ev_loop_s": None if t_ev is None else t_ev - float(res["t_loop_start_s"]), "phases": res["phases"], "events": [e for e in res["events"] if any(m in e["name"] for m in MARKS)],
            "hold": (res.get("controller_meta") or {}).get("touch_twist_hold"), "judgement": se.get("judgement"), "prefix_check_stored": se.get("prefix_check"), "branch_sha256": se.get("branch_commands_sha256"), "wall_s": res.get("wall_s"), "us_per_step": res.get("us_per_step"), "flags": _side(d)}


def _side(d: Path) -> dict | None:
    p = d / "k1soil_job_side.json"
    if not p.exists():
        return None
    s = json.loads(p.read_text(encoding="utf-8"))
    return {k: s.get(k) for k in ("c2_sha256", "config", "main_tree_modules_at_end", "t_ev_loop_arg")}


def prefix(a: str, b: str, t_limit: float | None) -> dict:
    x, y = np.load(BATCH / a / "controller_commands.npz"), np.load(BATCH / b / "controller_commands.npz")
    n = min(len(x["t_s"]), len(y["t_s"]))
    same_t = np.array_equal(x["t_s"][:n], y["t_s"][:n])
    eq = (x["issued_u_m_s"][:n] == y["issued_u_m_s"][:n]).all(axis=1)
    first = None if eq.all() else float(x["t_s"][int(np.argmin(eq))])
    out = {"pair": [a, b], "t_limit_s": t_limit, "times_equal": bool(same_t), "commands": int(n), "first_difference_t_s": first}
    if t_limit is not None:
        m = x["t_s"][:n] < t_limit
        out.update(commands_before=int(m.sum()), identical_before=bool(eq[m].all()))
    return out


def main() -> None:
    preview = len(sys.argv) > 1 and sys.argv[1] == "preview"
    on, off = row(ON), row(OFF)
    doc = {"on_1a": on, "off_1b": off, "prefix_1a_vs_1b": prefix(ON, OFF, on["t_ev_s"]), "prefix_1a_vs_base": prefix(ON, BASE, on["t_ev_s"])}
    t_on = on["t_ev_s"]
    doc["1a_before_event_reapproach"] = [e for e in on["events"] if "leg_reapproach" in e["name"] and e["t_s"] < t_on]
    if not preview:
        d = row(D003)
        doc["d003"] = d
        doc["prefix_d003_vs_1a"] = prefix(D003, ON, t_on)
        doc["prefix_d003_vs_1b"] = prefix(D003, OFF, t_on)
        doc["d003_before_event_reapproach"] = [e for e in d["events"] if "leg_reapproach" in e["name"] and e["t_s"] < d["t_ev_s"]]
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "d003_values.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        print("written", OUT / "d003_values.json")
    for k in ("prefix_1a_vs_1b", "prefix_1a_vs_base", "prefix_d003_vs_1a", "prefix_d003_vs_1b", "1a_before_event_reapproach", "d003_before_event_reapproach"):
        if k in doc:
            print(k, doc[k])
    for name in ("on_1a", "off_1b", "d003"):
        if name not in doc:
            continue
        v = doc[name]
        j = v["judgement"] or {}
        print(name, "t_ev", v["t_ev_s"], v["t_ev_loop_s"], "wall", v["wall_s"], "flags", (v["flags"] or {}).get("config"), "hold", {q: x for q, x in (v["hold"] or {}).items() if q != "settings"})
        print("  judgement keys", list(j)[:30])
        print("  judgement", json.dumps({q: x for q, x in j.items() if not isinstance(x, (list, dict)) or len(str(x)) < 160}, ensure_ascii=False, default=str)[:1500])
        print("  events", [(round(e["t_s"], 1), e["name"]) for e in v["events"]][:14])


if __name__ == "__main__":
    main()
