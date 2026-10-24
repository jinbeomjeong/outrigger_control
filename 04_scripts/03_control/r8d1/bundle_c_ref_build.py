"""Build 06_analysis/02_control/r8_10hz/d1/bundle_c_consistency_ref.json from bundle_c_ref.py raw output.
Usage: python -I bundle_c_ref_build.py <raw.json> <s6c_list.txt> <out.json>"""
import hashlib
import json
import statistics as st
import sys
from pathlib import Path

raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ids = [ln.split()[0] for ln in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines() if ln.strip()]
out_path = Path(sys.argv[3])
c2 = Path(__file__).resolve().parents[3] / "03_src" / "outrigger_sim" / "control" / "c2.py"


def minf(m):
    v = [m["min_true_cyl_force_kN"]]
    if m.get("min_true_after_sink_kN") is not None:
        v.append(m["min_true_after_sink_kN"])
    return min(x for x in v if x is not None)


rows = raw["rows"]
assert not [r for r in rows if "error" in r]
ref = {"_meta": {
    "spec": "s6_control_spec.md rev. 31 146 (consistency flag only) / 142 C harness with c2.py",
    "generator": "control-expert 2026-10-24, 04_scripts/03_control/r8d1/bundle_c_ref.py (harness r8d1_td2 + "
                 "project C2Controller, C2Config().with_10hz_d1() with the Chrono case settings)",
    "c2_py_sha256": hashlib.sha256(c2.read_bytes()).hexdigest(),
    "c2_revision_meta": rows[0]["revision"],
    "value": "min_force_kN = median over noise seeds 12345-12347 of the minimum true cylinder force "
             "after the crawler lift-off, sampled every control period (10 Hz; Chrono uses the 1 ms "
             "interval minimum, so Chrono may read lower by short dips); G4 / C-9 / C-10 include the "
             "settlement (min of pre- and post-settlement). ready_s = harness first READY measured "
             "from the TOUCH start (no CHECK / zero calibration in the harness; Chrono ready_s is "
             "later by the CHECK length). ready_minus_touch_s is the comparable READY quantity.",
    "departures": "no CHECK / zero calibration, target check off, IMU period mean (no 10 ms samples), "
                  "head pressure only (no L1-R rod side), harness sensor noise (not WIKA), rigid mast, "
                  "floor angles = Chrono floors, G4 settlement 11.5 mm in 2 s at READY + 5 s",
}}
for cid in ids:
    if cid in raw["null"]:
        ref[cid] = {"min_force_kN": None, "ready_s": None, "reason": raw["null"][cid]}
        continue
    rs = [r for r in rows if r["case"] == cid and not r["h142"]]
    if len(rs) != 3:
        raise RuntimeError(f"{cid}: {len(rs)} rows")
    f = [minf(r["metrics"]) for r in rs]
    tr = [r["metrics"]["t_ready_s"] for r in rs]
    tt = [r["metrics"]["t_touch_s"] for r in rs]
    e = {"min_force_kN": round(st.median(f), 2),
         "ready_s": round(st.median(tr), 2) if None not in tr else None,
         "seeds_min_force_kN": f,
         "seeds_ready_s": tr,
         "ready_minus_touch_s": round(st.median([a - b for a, b in zip(tr, tt)]), 2)
         if None not in tr and None not in tt else None,
         "fails": sorted({x for r in rs for x in (r["fails"] or [])}),
         "fault": any(r["fault"] for r in rs)}
    if rs[0]["metrics"].get("min_true_after_sink_kN") is not None:
        e["min_before_settlement_kN"] = round(st.median(r["metrics"]["min_true_cyl_force_kN"] for r in rs), 2)
        e["min_after_settlement_kN"] = round(st.median(r["metrics"]["min_true_after_sink_kN"] for r in rs), 2)
    sc = raw["cases"][cid]
    e["harness_settings"] = sc
    h = [r for r in rows if r["case"] == cid and r["h142"]]
    if h:
        e["h142_min_force_kN"] = round(st.median(minf(r["metrics"]) for r in h), 2)
        e["h142_ready_s"] = round(st.median(r["metrics"]["t_ready_s"] for r in h), 2)
    notes = []
    if cid.startswith("C1_G3"):
        notes.append("sensor errors (normal grade + calibration) not reproduced; harness noise only")
    if sc["floor"] in ("fdown3.5", "fdown3.2") and sc["h4"]:
        notes.append("H4 REANCHOR runs; the minimum is inside REANCHOR (P_stop region)")
    if notes:
        e["note"] = "; ".join(notes)
    ref[cid] = e
extra = set(raw["cases"]) - set(ids)
assert not extra, extra
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(ref, indent=1), encoding="utf-8")
for cid in ids:
    e = ref[cid]
    print(f"{cid:40s} {e['min_force_kN']!s:>7} {e['ready_s']!s:>6} "
          f"{e.get('h142_min_force_kN', '')!s:>7} {e.get('seeds_min_force_kN', '')} {e.get('fails', '')}")
