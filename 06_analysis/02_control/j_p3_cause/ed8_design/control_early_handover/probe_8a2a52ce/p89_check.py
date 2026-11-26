"""P8-9 patch check on bottom-FR-Fs0-RE1bF-ready o0.0 (raw_check/runs.jsonl).

1. A arm commands_sha256 == stored U8-A line (dynamics_u832_o00/rerun_raw/runs.jsonl).
2. H3n3 (H-3 copy with N_S 3) and H1off (H-1 path with W_D < 0) == A (patch identity).
3. H3: the event leg's first contact exit after the event needs 4 samples and ends later than
   the normal rule would have; H1: the diagonal start after the contact end waits.

Usage: conda run -n dynamics-dev python -I -B p89_check.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
U10 = HERE.parents[1] / "dynamics_u832_o00" / "rerun_raw" / "runs.jsonl"


def load(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


rows = {r["job"]["setting"].split("-")[1]: r for r in load(HERE / "raw_check" / "runs.jsonl")}
stored = [r for r in load(U10) if r["job"]["setting"] == "U8-A"
          and r["job"]["twin"]["leg"] == "FR" and r["job"]["twin"]["fs_kN"] == 0.0]
out = {"stored_U8A_sha": stored[0]["commands_sha256"],
       "A_sha": rows["A"]["commands_sha256"]}
out["A_equals_stored_U8A"] = out["A_sha"] == out["stored_U8A_sha"]
for arm in ("H3n3", "H1off", "H3", "H1"):
    out[f"{arm}_equals_A"] = rows[arm]["commands_sha256"] == out["A_sha"]
for arm, r in rows.items():
    out[f"{arm}_p89"] = r["p89"]
t_ev = rows["A"]["t_event_s"]
out["t_event_s"] = t_ev
for arm in ("A", "H3", "H1"):
    log = json.loads((HERE / "raw_check" / "logs" / f"{rows[arm]['p89']['stem']}_p89.json")
                     .read_text(encoding="utf-8"))
    rel = lambda t: round(t - t_ev, 3)  # noqa: E731
    out[f"{arm}_starts_rel"] = [(rel(s["t"]), s["leg"], s["retrigger"]) for s in log["starts"]
                                if s["t"] >= t_ev - 1e-9]
    out[f"{arm}_ends_rel"] = [(rel(e["t"]), e["leg"], e["outcome"], e["exit_samples_seen"],
                               e["required"], None if e["start_s"] is None else rel(e["start_s"]))
                              for e in log["ends"] if e["t"] >= t_ev - 1e-9]
    out[f"{arm}_h3_rel"] = [(rel(h["t"]), h["leg"], h["seen"], h["required"]) for h in log["h3"]]
    out[f"{arm}_h1_defer_rel"] = [(rel(h["t"]), h["leg"]) for h in log["h1_defer"]]
    out[f"{arm}_h1_land_rel"] = [(rel(h["t"]), h["leg"]) for h in log["h1_land"]]
    out[f"{arm}_h1_b3_block_rel"] = [(rel(h["t"]), h["leg"]) for h in log["h1_b3_block"]]
    eo = rows[arm]["event_output"]
    out[f"{arm}_gates"] = eo.get("gates")
    out[f"{arm}_pair_union_s"] = eo.get("pair_union_s")
    out[f"{arm}_deferred_events"] = {k: v for k, v in rows[arm]["event_names"].items()
                                     if "deferred" in k}
text = json.dumps(out, indent=1, default=str)
(HERE / "check_out.json").write_text(text, encoding="utf-8")
print(text)
