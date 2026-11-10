"""V-5 regression row keys: judged (acc_judge) vs record only, from the stored acceptance outputs (read only).

The K-2 V-5 regression steps (reg1 .. reg7) are the stored acceptance steps, so their outputs carry the same row
keys as the stored files under ``06_analysis/02_control/touch_phase/acceptance/regression``. Key format
``<output file>:<row key>`` (clip_A ``<key>#<run index>``, r79 ``<key>|<level>``).

judged   = acc_judge regression rows: clip_harness / clip_p0 ``records[].id``, clip_x426_C / _D ``results[]``,
           clip_A ``results[].runs[]``, ``clip_r79_L1L2_judgement.json runs[].key``
record   = every other entry of the step outputs: clip_r79_L1L2.json entries whose key is not a judgement row,
           all clip_r79_L3L4.json entries (acc_judge: "record only")

Usage: python -I -B regression_keys.py [--acc <acceptance folder>]  -> k2_v5_regression_keys.json next to this file
At the launch record the same function on the K-2 arm folders (runs/v5/<arm>) must give the same two lists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACC = HERE.parents[2] / "02_control" / "touch_phase" / "acceptance"


def keys(folder: Path) -> dict:
    def load(name):
        return json.loads((folder / name).read_text(encoding="utf-8"))

    judged = []
    for name in ("clip_harness.json", "clip_p0.json"):
        judged += [f"{name}:{r['id']}" for r in load(name)["records"]]
    for name in ("clip_x426_C.json", "clip_x426_D.json"):
        judged += [f"{name}:{r.get('key', r.get('id', r.get('case_id')))}" for r in load(name)["results"]]
    for res in load("clip_A.json")["results"]:
        judged += [f"clip_A.json:{res['key']}#{i}" for i in range(len(res["runs"]))]
    jk = {r["key"] for r in load("clip_r79_L1L2_judgement.json")["runs"]}
    judged += [f"clip_r79_L1L2_judgement.json:{k}" for k in jk]
    record = [f"clip_r79_L1L2.json:{r['key']}|{r.get('level')}" for r in load("clip_r79_L1L2.json")["results"]
              if r["key"] not in jk]
    record += [f"clip_r79_L3L4.json:{r['key']}|{r.get('level')}" for r in load("clip_r79_L3L4.json")["results"]]
    judged, record = sorted(set(judged)), sorted(set(record))

    def h(xs):
        return hashlib.sha256("\n".join(xs).encode("utf-8")).hexdigest()

    return {"source": str(folder), "judged_n": len(judged), "judged_sha256": h(judged),
            "record_n": len(record), "record_sha256": h(record), "judged": judged, "record": record}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--acc", type=Path, default=ACC / "regression")
    ap.add_argument("--out", type=Path, default=HERE / "k2_v5_regression_keys.json")
    args = ap.parse_args()
    doc = keys(args.acc)
    args.out.write_bytes(json.dumps(doc, indent=1).encode("utf-8"))
    print(json.dumps({k: doc[k] for k in ("judged_n", "judged_sha256", "record_n", "record_sha256")}))


if __name__ == "__main__":
    main()
