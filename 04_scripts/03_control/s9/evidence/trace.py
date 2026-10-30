"""Trace one wrapper case per candidate: per control period phase, filtered attitude, completion deviation and PI
integrals (record only; wraps C2Controller._phase_command). Usage (project root):
python -I trace.py <suite> <case_id> <out_json> <cand1,cand2,...>

Moved 2026-10-30 from session scratchpad ctrl-zic/trace.py; the project root (was C:\\workspace\\outrigger_control)
is now found from this file's location."""
import json, sys, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s9"))
sys.path.insert(0, str(ROOT / "03_src"))
import s9_slope_fix_candidates as w  # noqa: E402
from outrigger_sim.control import c2  # noqa: E402

LOG: list = []
_orig = c2.C2Controller._phase_command


def _traced(self, reading):
    out = _orig(self, reading)
    s = self._state
    try:
        dev = self._completion_deviation_rad()
    except Exception:
        dev = float("nan")
    LOG.append({"t": round(float(reading.t_s), 2), "ph": str(s.phase.name).lower(),
                "roll": round(math.degrees(s.roll_rad), 4), "pitch": round(math.degrees(s.pitch_rad), 4),
                "dev": round(math.degrees(dev), 4), "Ir": round(s.roll_integral, 5), "Ip": round(s.pitch_integral, 5),
                "u_mm_s": [round(float(x) * 1e3, 3) for x in out]})
    return out


c2.C2Controller._phase_command = _traced


def main():
    suite, cid, out_path, cands = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4].split(",")
    payload = dict(w.suite_cases(suite))[cid]
    res = {}
    for cand in cands:
        LOG.clear()
        rec = w.run_job({"suite": suite, "id": cid, "candidate": cand, "payload": payload, "params": {}})
        ctrl = w._RUNNING.get("controller")
        ev = [(round(float(e.t_s), 2), e.name) for e in ctrl.events] if ctrl is not None else []
        res[cand] = {"verdict": rec.get("verdict"), "t_ready_s": rec.get("t_ready_s"), "final_phase": rec.get("final_phase"),
                     "hash": rec.get("hash"), "att_end_deg": rec.get("att_end_deg"), "events": ev,
                     "p38": (rec.get("metrics") or {}).get("p38"), "log": list(LOG)}
        print(cand, rec.get("verdict"), rec.get("t_ready_s"), rec.get("final_phase"), (rec.get("hash") or "")[:12], flush=True)
    out_path.write_text(json.dumps(res), "utf-8")


if __name__ == "__main__":
    main()
