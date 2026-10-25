"""Second extraction: event-case summaries, b1 rows, item-8 F_band, probe rounds of event cases."""

import json
from pathlib import Path

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
ROOT = (REPO / r"06_analysis\01_chrono\16_S6")
cl = json.loads((ROOT / "verify_S6_L1_closed_loop_re3.json").read_text(encoding="utf-8"))
out = []
w = out.append
skip = {"fine_dt", "dt_segments", "probe_after_event", "ge1"}
for name, ev in cl["event_cases_RE1b_RE1c"].items():
    w(name + " " + json.dumps({k: v for k, v in ev.items() if k not in skip}, ensure_ascii=False))
w("--- b1 s12347 " + json.dumps(cl["b1_check"]["cases"].get("G3_top_fdown3.5_normal_zeroed_s12347"),
                                 ensure_ascii=False)[:1500])
for row in cl["b1_check"]["rows"]:
    w("b1row " + json.dumps(row, ensure_ascii=False)[:400])
w("--- probes_item7 event cases")
for name in ("RE1bF_top_flat_dropRR30", "RE1bP_top_flat_dropRR30_probe", "RE1b_top_flat_settleRR30"):
    p = cl["probes_item7"].get(name)
    w(name + " " + json.dumps(p, ensure_ascii=False)[:2500])
w("--- band_decomposition keys")
bd = cl["band_decomposition_U42"]
for name in ("G2_top_fdown3.5" if False else "", ):
    pass
for name, v in bd.items():
    if any(s in name for s in ("fdown3.5", "fup3.5")) and "G2-R" in name:
        w(name + " " + json.dumps(v, ensure_ascii=False)[:500])
# event logs for RE1bP
case = cl["cases"].get("RE1bP_top_flat_dropRR30_probe", {})
w("--- RE1bP case keys " + json.dumps(list(case.keys())))
for k in ("events", "phases", "probe", "item6", "phase_timeline"):
    if k in case:
        w(k + " " + json.dumps(case[k], ensure_ascii=False)[:3000])
(OUT_DIR / _Path(__file__).name).with_suffix(".txt").write_text("\n".join(out), encoding="utf-8")
print(len(out))
