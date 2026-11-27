"""G' window shift, part 1: stored V0 grid (seen, public) -> per-cluster E flags and bounds on the
controller-effective load window [t_r*, t_h*] of the event leg (front legs, RE1bF and FS24).

E rule (spec 6.3 reading, stats): the diagonal leg's first re-approach start after the event,
round(t, 3) <= 0.450 s. Stored times are rounded to 0.01 s (0.425 -> 0.42), so the start is mapped
back to the 0.1 s control grid of the run's phase phi = offset mod 0.1: t = 0.1 k - phi.

Interval model (dynamics_u832_o00 4.2): the event leg's exit is the 3rd consecutive control sample
inside [t_r*, t_h*]; first sample s1 = min{0.1 k - phi >= t_r*}; E <=> s1 + 0.2 <= min(t_h*, 0.4505).
Per offset this gives:
  phi 0     : E <=> t_r* <= 0.200            (s1 0.2, exit 0.40)
  phi 0.025 : E <=> t_r* <= 0.175            (else s1 0.275 -> exit 0.475 > 0.45)
  phi 0.05  : E <=> t_r* <= 0.25 and t_h* >= 0.45   (exit 0.45)
  phi 0.075 : E <=> t_r* <= 0.225 and t_h* >= 0.425 (exit 0.425)
Usage: python -I -B g01_grid_E.py <out_folder>
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

GRID = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance\c4g2_only\grid")
FILES = ["grid_r67_main.json", "grid_r67_top.json", "grid_r69_bottom.json", "grid_r69_top.json"]
LEGS = ("FL", "FR", "RL", "RR")
DIAG = {"FL": "RR", "RR": "FL", "FR": "RL", "RL": "FR"}
OUT = Path(sys.argv[1])


def snap(t_stored, phi):
    """Map a 0.01 s rounded start back to the 0.1 s grid 0.1 k - phi of the run."""
    k = round((t_stored + phi) / 0.1)
    return round(0.1 * k - phi, 4)


rows = []
seen = set()
for fn in FILES:
    d = json.loads((GRID / fn).read_text(encoding="utf-8"))
    for job in d["results"]:
        leg = job.get("leg")
        if leg not in ("FL", "FR"):
            continue
        for r in job["runs"]:
            ev = r.get("event")
            if ev not in ("RE1bF", "FS24"):
                continue
            off = float(r["offset_s"])
            phi = round(off % 0.1, 4)
            key = (job["level"], leg, float(job["fs_kN"]), job["timing"], ev, off)
            dup = key in seen
            seen.add(key)
            starts = r.get("reapproach_starts") or []
            dstarts = [float(s[0]) for s in starts if s[1] == DIAG[leg]]
            estarts = [float(s[0]) for s in starts if s[1] == leg]
            d0 = min(dstarts) if dstarts else None
            d0s = snap(d0, phi) if d0 is not None else None
            lf = (r.get("lifts") or {}).get(leg) or {}
            rows.append({"file": fn, "dup": dup, "level": job["level"], "leg": leg, "fs_kN": float(job["fs_kN"]),
                         "timing": job["timing"], "event": ev, "offset_s": off, "phi_s": phi,
                         "diag_start_stored_s": d0, "diag_start_grid_s": d0s,
                         "E": (d0s is not None and round(d0s, 3) <= 0.450),
                         "event_start_s": min(estarts) if estarts else None,
                         "ev_first_lift_s": lf.get("first_s"), "ev_n_lifts": lf.get("n"),
                         "pass": r.get("pass"), "fast": r.get("fast")})

uniq = [r for r in rows if not r["dup"]]
with (OUT / "g01_grid_E_rows.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

# per-cluster table and bounds (bottom front RE1bF / FS24)
clusters = defaultdict(dict)
for r in uniq:
    clusters[(r["level"], r["event"], r["timing"], r["leg"], r["fs_kN"])][r["offset_s"]] = r
lines = ["cluster(level,event,timing,leg,Fs) | diag start (grid) at o0/0.025/0.05/0.075 | E flags | t_r* bound | t_h* bound"]
summary = defaultdict(lambda: defaultdict(list))
for key in sorted(clusters):
    c = clusters[key]
    offs = [0.0, 0.025, 0.05, 0.075]
    ds = [c[o]["diag_start_grid_s"] if o in c else None for o in offs]
    es = [c[o]["E"] if o in c else None for o in offs]
    tr = "t_r*<=0.200" if es[0] else ("t_r*>0.200" if es[0] is False else "?")
    th = "t_h*>=0.450" if es[2] else ("t_h*<0.450 or t_r*>0.25" if es[2] is False else "?")
    lines.append(f"{key} | {ds} | {['E' if e else ('N' if e is False else '-') for e in es]} | {tr} | {th}")
    for o, e in zip(offs, es):
        if e is not None:
            summary[(key[0], key[1])][(o, key[4])].append(int(e))
lines.append("")
lines.append("E rate by (level, event) x offset x Fs  [E/n]")
for lk in sorted(summary):
    lines.append(f"## {lk}")
    fss = sorted({k[1] for k in summary[lk]})
    for o in [0.0, 0.025, 0.05, 0.075]:
        cells = []
        for fs in fss:
            v = summary[lk].get((o, fs), [])
            cells.append(f"Fs{fs:g} {sum(v)}/{len(v)}")
        lines.append(f"  o{o:<6} " + "  ".join(cells))
(OUT / "g01_grid_E.txt").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({"status": "ok", "rows": len(rows), "unique": len(uniq)}))
