"""Per-item wall of the warm probes and the time estimate per step (8 workers E1, 4 workers E2, margin 1.25, ASSUMPTION)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "probe_out"
units = {}
for name in ("L2", "L3"):
    rows = json.loads((OUT / name / "r.json").read_text(encoding="utf-8"))["results"]
    print(name, [(r["level"], r["wall_s"]) for r in rows])
    units[name] = {lv: sum(r["wall_s"] for r in rows if r["level"] == lv) / max(1, sum(r["level"] == lv for r in rows)) for lv in {r["level"] for r in rows}}
for name in ("d8", "crawler"):
    rows = json.loads((OUT / name / "r.json").read_text(encoding="utf-8"))["runs"]
    w = [r["wall_s"] for r in rows]
    print(name, w)
    units[name] = sum(w) / len(w)
for name in ("grid", "soil"):
    rows = json.loads((OUT / name / "r.json").read_text(encoding="utf-8"))["results"]
    w = [r["wall_s"] for r in rows]
    print(name, w, [len(r["runs"]) for r in rows])
    units[name] = sum(w) / sum(len(r["runs"]) for r in rows)
print(json.dumps(units))
L2, L1, L3 = units["L2"]["L2"], units["L2"]["L1"], units["L3"]["L3"]
d8, cr, ev, soil = units["d8"], units["crawler"], units["grid"], units["soil"]
M = 1.25
rows = [("reg (118: 30 wrapper at 60 s, 4x5 A at soil, 79 r79 at L3, 5 at 60 s)", (35 * 60 + 20 * soil + 79 * L3), 8),
        ("grid both 768", 768 * ev, 8), ("grid off 384", 384 * ev, 8), ("soil 80", 80 * soil, 8), ("d8 576", 576 * d8, 8), ("d8 main off 144", 144 * d8, 8),
        ("crawler 72", 72 * cr, 8), ("L3 501", 501 * L3, 8), ("L4 501", 501 * L3, 8), ("E2 L1 171 + L2 855", 171 * L1 + 855 * L2, 4)]
tot = 0
for name, ws, w in rows:
    h = ws / w / 3600 * M
    if w == 8:
        tot += h
    print(f"{name}: {ws:.0f} worker-s, {h:.2f} h")
print("E1 total h", round(tot, 2))
