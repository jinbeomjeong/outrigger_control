"""Third extraction: pressure / saturation / rocking per event case, item-8 per stage values."""

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
keys = ("max_moving_pressure_bar", "max_pressure_any_step_bar", "saturation_steps",
        "rocking_amp_deg", "min_cyl_excl_reanchor_kN", "min_cyl_after_liftoff_kN", "event3")
out = []
for name, case in cl["cases"].items():
    if name.startswith(("RE1b", "G2-R_", "G4", "G6")):
        out.append(name + " " + json.dumps({k: case.get(k) for k in keys}, ensure_ascii=False)[:700])
for row in cl["rows"]:
    if row["item"].startswith("4 ") and row["case"].startswith(("RE1b", "G4")):
        out.append("row4 " + json.dumps(row, ensure_ascii=False))
    if row["item"].startswith("5a") and row["case"].startswith(("RE1b", "G4")):
        out.append("row5a " + json.dumps(row, ensure_ascii=False))
(OUT_DIR / _Path(__file__).name).with_suffix(".txt").write_text("\n".join(out), encoding="utf-8")
print(len(out))
