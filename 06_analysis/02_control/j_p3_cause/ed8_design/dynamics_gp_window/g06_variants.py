"""G' window shift, part 6: reduced-model DIFFERENCES held-out shape - stored shape (g00 model, own code).

For each stored V0 rerun (8 runs: bottom FL-Fs2 / FR-Fs4, ready, 4 offsets), its own valve history and each
calibrated ensemble member (g04_calibration.json), simulate 30 mm / 0.05 s (stored shape), 25 mm / 0.05 s and
30 mm / 0.04 s and report the shifts of the event-leg window edges:
  t_contact, t_r* (controller-effective rising edge), t_h* (falling edge), t_relift, diagonal land.
Sensitivities (best member, o0.0 runs only): valve history off, pad mu 0.3 / 1.0, dt / 2.
Usage: python -I -B g06_variants.py <rerun_dir> <out_folder>
"""
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g00_rock_model as rm  # noqa: E402

rerun, out = Path(sys.argv[1]), Path(sys.argv[2])
ENS = json.loads((out / "g04_calibration.json").read_text(encoding="utf-8"))["ensemble"]
SHAPES = {"30/0.05": (0.030, 0.05), "25/0.05": (0.025, 0.05), "30/0.04": (0.030, 0.04)}
STEMS = [(f"R12_bottom-{lg}-Fs{fs}-o{o}-RE1bF-ready_V0", 0 if lg == "FL" else 1, float(fs))
         for lg, fs in (("FL", 2), ("FR", 4)) for o in ("0.0", "0.025", "0.05", "0.075")]
KEYS = ("t_contact", "t_r_star", "t_h_star", "t_relift", "d_land", "v_imp", "F_peak_kN")

t0 = time.time()
rows = []
for stem, leg, fs in STEMS:
    valve, _, _ = rm.load_valve(rerun, stem)
    cases = [(f"ens{i}", p, valve, 0.5, 5e-5) for i, p in enumerate(ENS)]
    if "-o0.0-" in stem:
        p = ENS[0]
        cases += [("valve_off", p, None, 0.5, 5e-5), ("mu0.3", p, valve, 0.3, 5e-5), ("mu1.0", p, valve, 1.0, 5e-5),
                  ("dt_half", p, valve, 0.5, 2.5e-5)]
    for name, p, vlv, mu, dt in cases:
        feats = {}
        for sh, (d, T) in SHAPES.items():
            tt, F, g = rm.simulate(leg, d, T, p["kf"], p["cf"], vlv, h=p["h"], ktf=p["ktf"], mu=mu, dt=dt, t_end=1.2)
            feats[sh] = rm.window_features(tt, F, g, leg, fs)
        base = feats["30/0.05"]
        for sh, f in feats.items():
            row = {"stem": stem, "case": name, "shape": sh, **{k: round(f[k], 4) for k in KEYS},
                   "relift_found": f["relift_found"]}
            for k in KEYS[:5]:
                row[f"d_{k}"] = round(f[k] - base[k], 4) if np.isfinite(f[k]) and np.isfinite(base[k]) else None
            rows.append(row)
with (out / "g06_variants.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
lines = []
for sh in ("25/0.05", "30/0.04"):
    for grp, sel in (("ensemble x 8 runs", lambda r: r["case"].startswith("ens")),
                     ("valve_off (o0.0, best)", lambda r: r["case"] == "valve_off"),
                     ("mu0.3", lambda r: r["case"] == "mu0.3"), ("mu1.0", lambda r: r["case"] == "mu1.0"),
                     ("dt_half", lambda r: r["case"] == "dt_half"),
                     ("best member ens0 x 8 runs", lambda r: r["case"] == "ens0")):
        sub = [r for r in rows if r["shape"] == sh and sel(r)]
        if not sub:
            continue
        parts = []
        for k in ("t_contact", "t_r_star", "t_h_star", "t_relift", "d_land"):
            v = np.array([r[f"d_{k}"] for r in sub if r[f"d_{k}"] is not None], float)
            parts.append(f"d_{k} {1e3 * v.mean():+6.1f} [{1e3 * v.min():+6.1f}, {1e3 * v.max():+6.1f}] ms")
        lines.append(f"{sh:8s} {grp:28s} n {len(sub):2d} | " + " | ".join(parts))
base_rows = [r for r in rows if r["shape"] == "30/0.05" and r["case"] == "ens0"]
lines.append("")
lines.append("ens0 stored-shape absolute (model) per run: stem, t_contact, t_r*, t_h*, t_relift, d_land")
for r in base_rows:
    lines.append(f"  {r['stem']}: {r['t_contact']} {r['t_r_star']} {r['t_h_star']} {r['t_relift']} {r['d_land']}")
(out / "g06_variants.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
print(json.dumps({"status": "ok", "rows": len(rows), "elapsed_s": round(time.time() - t0, 1)}))
