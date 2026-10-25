"""Rule A envelope margins against the soft stroke end 0.6948 m (dynamics rev. 30 5.12.3).

Reuses s6_envelope_check (same folder) with S_END replaced; the envelope maps
(06_analysis/00_dynamics/target_envelope.json, rev. 21 geometry) are read only. The mount
geometry is on hold (Q-C2), so only the end limit and the REXOME35 static compression change
(+0.3 mm rear / -1.1 mm front, F/k_n with k_n 1.950 / 2.591e7 against 2.125 / 2.081e7) enter.
"""

import json
import sys
from pathlib import Path

# --- paths (migrated from the 2026-10-22 session scratchpad ctrl-run on 2026-10-25) ---
import sys as _sys
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[3]  # 04_scripts/03_control/s6_rev01_28/ -> repo root
OUT_DIR = REPO / "06_analysis" / "02_control" / "s6_rev01_28"  # results of these scripts
OUT_DIR.mkdir(parents=True, exist_ok=True)
_sys.path.append(str(REPO / "04_scripts" / "03_control"))  # siblings migrated earlier
# ---
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s6_envelope_check as env  # noqa: E402

MEASURABLE = 0.6948
SOFT_MARGIN = 0.010
COMPRESSION_BOUND_MM = 0.3  # worst-case extra stroke from the REXOME35 rear stiffness

env.S_END = MEASURABLE
env.OUT = OUT_DIR / "s6r12_envelope_raw.json"
env.main()
raw = json.loads(env.OUT.read_text())
worst = raw["worst_accepted"]["s_mm"] + COMPRESSION_BOUND_MM
slope = raw["heave_target_rule"]["ds_dclr_range"][1]
summary = {
    "worst_accepted_mm": worst,
    "worst_map": raw["worst_accepted"]["map"],
    "left_to_soft_end_mm(0.6848)": (MEASURABLE - SOFT_MARGIN) * 1e3 - worst,
    "left_to_fault_mm(0.6938)": (MEASURABLE - 0.001) * 1e3 - worst,
    "left_to_measurable_mm": MEASURABLE * 1e3 - worst,
    "A5_limit_mm": (MEASURABLE - SOFT_MARGIN - 0.003) * 1e3,
    "heave_target_max_mm_10mm_margin": 50 + ((MEASURABLE - SOFT_MARGIN) * 1e3 - worst) / slope,
    "verification_vertex_mm(668.7+0.3)": 669.0,
    "verification_vertex_left_to_soft_end_mm": (MEASURABLE - SOFT_MARGIN) * 1e3 - 669.0,
    "verification_vertex_left_to_fault_mm": (MEASURABLE - 0.001) * 1e3 - 669.0,
    "per_floor_worst_mm": {k: v.get("worst_s_max_mm") for k, v in raw["floors"].items()},
}
(OUT_DIR / "s6r12_envelope.json").write_text(json.dumps(summary, indent=1))
print(json.dumps(summary, indent=1))
