import json
from pathlib import Path
R = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85")
rs = {r["id"]: r for r in json.loads((R / "finB2_harness_rejudged.json").read_text(encoding="utf-8"))["records"]}
def att(r):
    a = r["att_end_deg"]
    return max(abs(x) for x in a) if isinstance(a, list) else abs(a)
g = rs["H1|G1|B|top|flat"]
for s in ("J1", "J2", "S1"):
    r = rs[f"H1|{s}|B|top|flat"]
    print(s, "dREADY", round(r["t_ready_s"] - g["t_ready_s"], 2), "dminF", round(r["min_force_kN"] - g["min_force_kN"], 2),
          "datt", round(att(r) - att(g), 4), "dstroke(guard)", round(-(r["max_stroke_mm"] - g["max_stroke_mm"]), 1))
