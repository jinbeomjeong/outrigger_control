"""Print judge rows of the stored source batches for the 14 v4 recheck cases (read only).

Usage: python -I -B -X utf8 peek_old.py
"""
from __future__ import annotations

import json
from pathlib import Path

S8 = Path(r"C:\workspace\outrigger_control\07_results\S8")
SRC = {"rest": S8 / "rest_20261024_233615", "p1r": S8 / "p1r_20261024_222013"}
CASES = {"N_G4_Fs0_pressure": "rest", "N_G4_Fs4_pressure": "rest", "N_G4_Fs8_pressure": "rest", "N_SS_Fs0_pressure": "rest",
         "N_SS_Fs4_pressure": "rest", "N_SS_Fs8_pressure": "rest", "K0V_top_fdown3.5_Fs0": "p1r", "K24_top_fdown3.5_Fs2": "rest",
         "K8_top_fdown3.5_Fs8": "p1r", "E_SS_Fs0": "p1r", "E_SS_Fs8": "p1r", "E_RE1bF_Fs0": "p1r", "E_RE1bP_Fs0": "p1r", "E_RE1bP_Fs8": "p1r"}


def main() -> None:
    for name, d in SRC.items():
        for f in sorted(d.glob("verify_S8C*.json")):
            doc = json.loads(f.read_text(encoding="utf-8"))
            print("==", name, f.name, "rows", len(doc["rows"]), "meta keys", list(doc["meta"])[:30], "failed", doc["meta"].get("failed"))
    doc = json.loads((SRC["rest"] / "verify_S8C_rev45judge.json").read_text(encoding="utf-8"))
    for r in doc["rows"]:
        if r.get("case") == "N_G4_Fs8_pressure":
            print(json.dumps({k: r.get(k) for k in ("item", "value", "passed", "kind", "note")}, ensure_ascii=False)[:420])
    for c in ("K8_top_fdown3.5_Fs8", "E_RE1bP_Fs8"):
        doc = json.loads((SRC["p1r"] / "verify_S8C_rev45judge.json").read_text(encoding="utf-8"))
        for r in doc["rows"]:
            if r.get("case") == c and ("F_min" in r["item"] or "item 9" in r["item"] or "READY" in r["item"] or "pressure" in r["item"]):
                print(c, json.dumps({k: r.get(k) for k in ("item", "value", "passed")}, ensure_ascii=False)[:300])
    d = SRC["rest"] / "N_G4_Fs8_pressure"
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    print("result keys", list(res))
    print("settings keys", list(res["settings"]))
    print("s8", json.dumps(res["settings"].get("s8"), ensure_ascii=False)[:800])
    print("events", (d / "controller_events.json").read_text(encoding="utf-8")[:1000])
    print("log", (d / "case.log").read_text(encoding="utf-8")[:600])
    batch = json.loads((SRC["rest"] / "batch.json").read_text(encoding="utf-8"))
    print("batch keys", list(batch))
    for name, cases_src in SRC.items():
        b = json.loads((cases_src / "batch.json").read_text(encoding="utf-8"))
        cs = b.get("cases") or b.get("outcomes")
        for o in cs:
            cid = o.get("case_id")
            if CASES.get(cid) == name:
                print(cid, name, o.get("status"), o.get("wall_s"))


if __name__ == "__main__":
    main()
