"""J_P (pressure-only contact judge) Chrono: extract VB / V0 values with the v4_recheck extract.py row definitions.

Usage: python -I jp_extract.py <verify dir> <out json>
Reuses case_values / first_diff of 04_scripts/03_control/touch_phase/chrono_runners/v4_recheck/extract.py (import only).
"""
import json
import sys
from pathlib import Path

MAIN = Path(r"C:\workspace\outrigger_control")
sys.path.insert(0, str(MAIN / "04_scripts/03_control/touch_phase/chrono_runners/v4_recheck"))
import extract as ex  # noqa: E402

S8 = MAIN / "07_results/S8"
V4 = S8 / "final_v4recheck_20261104_202815"
vdir, out_path = Path(sys.argv[1]), Path(sys.argv[2])
IDS = ("N_G4_Fs0_pressure", "N_G4_Fs4_pressure", "N_G4_Fs8_pressure",
       "N_SS_Fs0_pressure", "N_SS_Fs4_pressure", "N_SS_Fs8_pressure")
out = {"cases": {}, "all_items_example": None}
v4doc = json.loads((MAIN / "06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/v4_recheck/"
                    "verify_final_v4recheck_20261104_202815.json").read_text("utf-8"))
for setting in ("VB", "V0"):
    for cid in IDS:
        short = cid.replace("_pressure", "")
        folder = next(S8.glob(f"v5jp_{setting}_{cid}_*"))
        vf = vdir / f"verify_v5jp_{setting}_{short}.json"
        doc = json.loads(vf.read_text("utf-8"))
        v = ex.case_values(folder / cid, doc, cid)
        v["first_diff_vs_v4recheck_t_s"] = ex.first_diff(folder / cid, V4 / cid)
        v["failed_rows_all"] = [(r["item"], r.get("case")) for r in doc["rows"] if r.get("passed") is False]
        v["verify_summary"] = doc["meta"].get("summary")
        res = json.loads((folder / cid / "result.json").read_text("utf-8"))
        v["controller_tag"] = (res.get("settings") or {}).get("controller_tag") or res.get("controller_tag")
        v["settings_keys"] = sorted((res.get("settings") or {}).keys())
        v["v5_keys"] = {k: res[k] for k in res if k.startswith("v5") or k in ("hydraulic_options", "controller_options")}
        out["cases"][f"{setting}|{cid}"] = v
        if out["all_items_example"] is None:
            out["all_items_example"] = sorted({r["item"] for r in doc["rows"]})
# v4 recheck values with the same function
for cid in IDS:
    v = ex.case_values(V4 / cid, v4doc, cid)
    v["failed_rows_all"] = [(r["item"], r.get("case")) for r in v4doc["rows"] if r.get("passed") is False and r.get("case") == cid]
    out["cases"][f"v4|{cid}"] = v
out_path.write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False), "utf-8")
print("ok")
