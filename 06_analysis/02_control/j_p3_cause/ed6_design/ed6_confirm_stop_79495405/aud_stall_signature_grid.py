"""LEVEL stall signature (ed5 erratum 8 8-3 conditions 2-4; condition 1 read as 'line ends
without READY': last phase is level/probe) on the grid (나) 192 lines, record only.
Also prints the phase vocabulary and the lines that meet the signature."""
import json
from collections import Counter
from pathlib import Path

import numpy as np

RUN = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\79495405")
JSONL = RUN / "confirm_a1/confirm_b.jsonl"
T4H = RUN / "confirm_a1/confirm_b_t4h"


def main() -> None:
    vocab = Counter()
    sig = []
    lasts = []
    noready = []
    n = 0
    for text in JSONL.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        row = json.loads(text)
        n += 1
        with np.load(T4H / row["t4h_file"], allow_pickle=False) as d:
            t = d["t_s"]
            ph = np.array([str(p).lower() for p in d["phase"]])
            s = d["motor_stroke_m"]
        vocab.update(set(ph.tolist()))
        lasts.append(round(float(t[-1]), 1))
        if "ready" not in ph:
            noready.append((row["t4h_file"], round(float(t[-1]), 1), ph[-1]))
        no_fault = not np.isin(ph, ["fault", "fault_reground"]).any()
        last_lp = ph[-1] in ("level", "probe")
        w = t >= t[-1] - 20.0 - 1e-6
        width = (s[w].max(axis=0) - s[w].min(axis=0)) * 1e3
        frozen = bool((width < 1.0).all())
        if no_fault and last_lp and frozen:
            sig.append((row["t4h_file"], round(float(t[-1]), 1), [round(float(x), 2) for x in width],
                        (row.get("event_output") or {}).get("pass")))
    keys = json.loads((Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause"
                            r"\ed6_design\keys\confirm_b_grid192.json")).read_text(encoding="utf-8"))
    rows = keys.get("rows") or keys.get("lines") or []
    v0 = {r.get("t4h_file"): (r.get("v0_pair") or {}).get("v0_pass", r.get("v0_pair"))
          for r in rows if isinstance(r, dict)}
    print("key rows", len(rows), "example keys", sorted(rows[0]) if rows else None)
    print("lines", n, "phase vocabulary", dict(vocab), "last t range", min(lasts), max(lasts),
          Counter(lasts).most_common(4))
    print("no-ready lines", noready)
    print("signature lines", len(sig))
    for x in sig:
        print("  ", x, "v0_pass", v0.get(x[0]))


if __name__ == "__main__":
    main()
