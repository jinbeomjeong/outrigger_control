"""S9 C2 soil response verification table (spec rev. 57 284): per soil x pad, the worst over levels / F_s / seeds.

Criteria (spec 284, reduced model): crawler burden at READY 0 and no crawler re-contact after the first lift-off;
min true cylinder force after the lift-off >= F_min (margin >= 0, record the value); final true attitude
max(|roll|, |pitch|) <= 0.2 deg (target 0); READY reached (no FAULT); clearance above the rut at READY >= 25 mm
(ASSUMPTION, half the 50 mm target); motor stroke <= 0.6848 m; LOC window margin (min rise of windows ending with
the crawler loaded) > dF_thr.
python s9_judge.py <out_json> <file> [<file> ...]
"""
import json
import sys
from pathlib import Path

F_END = 684.8
rows = {}
fails = []
for f in sys.argv[2:]:
    base_only = f.endswith(":base")
    f = f.removesuffix(":base")
    for r in json.loads(Path(f).read_text(encoding="utf-8"))["runs"]:
        if base_only and not r["id"].startswith("base|"):
            continue
        if "error" in r:
            fails.append((r["id"], "error"))
            continue
        parts = r["id"].split("|")
        key = (parts[0].split("_")[0], parts[1], parts[2])
        att_end = max(abs(a) for a in r["att_end_deg"])
        ok_ready = r["t_ready_s"] is not None and r["final_phase"] != "fault"
        crawler = r["crawler_N_at_ready"] if r["crawler_N_at_ready"] is not None else float("nan")
        row = rows.setdefault(key, {"n": 0, "ready_fail": 0, "crawler_max_N": 0.0, "recontact": 0,
                                    "min_margin_kN": 1e9, "att_end_max": 0.0, "t_ready_max": 0.0, "t_ready_min": 1e9,
                                    "clear_min": 1e9, "clear_max": -1e9, "stroke_max": 0.0, "att_off_max": 0.0,
                                    "rise_pinned_min": 1e18, "reapproach": 0, "relevel": 0, "warn": 0})
        row["n"] += 1
        if not ok_ready:
            row["ready_fail"] += 1
            fails.append((r["id"], "no READY"))
            continue
        row["crawler_max_N"] = max(row["crawler_max_N"], crawler)
        row["recontact"] += r.get("n_crawler_recontact", 0)
        if r["min_margin_after_off_kN"] is not None:
            row["min_margin_kN"] = min(row["min_margin_kN"], r["min_margin_after_off_kN"])
        row["att_end_max"] = max(row["att_end_max"], att_end)
        row["att_off_max"] = max(row["att_off_max"], r["att_max_after_off_deg"])
        row["t_ready_max"] = max(row["t_ready_max"], r["t_ready_s"])
        row["t_ready_min"] = min(row["t_ready_min"], r["t_ready_s"])
        row["clear_min"] = min(row["clear_min"], r["clear_true_ready_mm"])
        row["clear_max"] = max(row["clear_max"], r["clear_true_ready_mm"])
        row["stroke_max"] = max(row["stroke_max"], r["max_motor_stroke_mm"])
        if r.get("min_rise_pinned_N") is not None:
            row["rise_pinned_min"] = min(row["rise_pinned_min"], r["min_rise_pinned_N"])
        row["reapproach"] += r["n_reapproach"]
        row["relevel"] += r["n_relevel"]
        row["warn"] += r["n_warn"]
        bad = []
        if crawler > 0:
            bad.append("crawler")
        if r.get("n_crawler_recontact", 0):
            bad.append("recontact")
        if r["min_margin_after_off_kN"] is not None and r["min_margin_after_off_kN"] < 0:
            bad.append("F_min")
        if att_end > 0.2:
            bad.append("att")
        if r["clear_true_ready_mm"] < 25:
            bad.append("clear<25")
        if r["max_motor_stroke_mm"] > F_END:
            bad.append("stroke")
        if bad:
            fails.append((r["id"], bad))
out = {"rows": {"|".join(k): v for k, v in sorted(rows.items())}, "fails": fails}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
print("variant|soil|pad | n | noREADY | crawler_max_kN | recontact | minMargin_kN | attEnd_max | attOff_max | "
      "READY min-max | clear min-max | stroke_max | rise_pinned_min_kN | reap | relev | warn")
for k, v in sorted(rows.items()):
    print("|".join(k), "|", v["n"], "|", v["ready_fail"], "|", round(v["crawler_max_N"] / 1e3, 2), "|", v["recontact"],
          "|", round(v["min_margin_kN"], 1), "|", round(v["att_end_max"], 3), "|", round(v["att_off_max"], 2), "|",
          f"{v['t_ready_min']:.1f}-{v['t_ready_max']:.1f}", "|", f"{v['clear_min']:.1f}-{v['clear_max']:.1f}", "|",
          round(v["stroke_max"], 1), "|", "-" if v["rise_pinned_min"] > 1e17 else round(v["rise_pinned_min"] / 1e3, 1),
          "|", v["reapproach"], "|", v["relevel"], "|", v["warn"])
print("fails:", len(fails))
for x in fails[:60]:
    print(" ", x)
