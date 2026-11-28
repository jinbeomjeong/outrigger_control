"""G-d record-only summary of an L2b case: phases, READY time, end rule, inclinometer error at its worst sample."""
import json
import sys
from pathlib import Path

import numpy as np

d = Path(sys.argv[1])
r = json.loads((d / "result.json").read_text(encoding="utf-8"))
with np.load(d / r["imua_record_file"], allow_pickle=False) as z:
    t, inc, tru = z["inclinometer_t_s"], z["inclinometer_rad"], z["attitude_true_at_inclinometer_rad"]
    pt, ph = z["t_s"], z["phase"]
err = np.degrees(inc - tru)
i = int(np.nanargmax(np.abs(err[:, 0])))
k = int(np.searchsorted(pt, t[i]))
t0 = r["settings"]["start_t_s"]
out = {"case": r["case"], "controller_tag": r["controller_tag"], "ready_t_s": r["ready_t_s"],
       "phases": r["phases"], "s8_end": {k_: r["s8_end"].get(k_) for k_ in ("end_t_s", "stopped_at_target",
                                                                            "timeout", "final_phase")},
       "events": json.loads((d / "controller_events.json").read_text(encoding="utf-8")),
       "worst_roll_error": {"t_rel_s": float(t[i] - t0), "err_deg": float(err[i, 0]),
                            "inclinometer_deg": float(np.degrees(inc[i, 0])), "true_deg": float(np.degrees(tru[i, 0])),
                            "phase": str(ph[min(k, len(ph) - 1)])},
       "runner_wall_s": r["runner"]["wall_s"]}
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(out, indent=1, ensure_ascii=False))
