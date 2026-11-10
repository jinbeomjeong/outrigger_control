"""Item-by-item comparison of path A and path B metrics (read-only). Tolerance: abs <= 1e-9 (m or ratio) or rel <= 1e-9."""
import json
import sys

A = json.load(open(sys.argv[1], encoding="utf-8"))
B = json.load(open(sys.argv[2], encoding="utf-8"))
items = []


def num(name, a, b):
    d = abs(a - b)
    rel = d / max(abs(a), abs(b), 1e-300)
    ok = d <= 1e-9 or rel <= 1e-9
    items.append((name, a, b, d, ok))


def disc(name, a, b):
    items.append((name, a, b, None, a == b))


disc("bundle", A["bundle"], B["bundle"])
disc("verdict", A["verdict"], B["verdict"])
for rid in ("GC-1", "GC-2", "GC-3", "GC-4"):
    ra, rb = A["rows"][rid], B["rows"][rid]
    disc(f"{rid} status", ra["status"], rb["status"])
    disc(f"{rid} xy0", ra["xy0_m"], rb["share_xy0_m"])
    for k in range(2):
        ha, lb = ra["holds"][k], rb["levels"][k]
        disc(f"{rid} h{k+1} N_h", ha["n_contact"], lb["N_h"])
        for fa, fb in (("Fz_scm_N", "Fz_scm_N"), ("z_node_m", "z_node_m"), ("z_geo_m", "z_geo_m"),
                       ("b_hull_m", "b_hull_m"), ("z_ref_m", "z_ref_m"), ("g1_eps", "eps1"), ("f", "f"),
                       ("z_over_f_m", "z_corr_m")):
            num(f"{rid} h{k+1} {fa}", ha[fa], lb[fb])
    num(f"{rid} dz_m", ra["dz_m"], rb["dz_m"])
    num(f"{rid} dz_over_z2", ra["dz_over_z2"], rb["dz_over_z2"])
for p in ("RL", "FL"):
    pa, pb = A["pairs"][p], B["pairs"][p]
    for k in range(2):
        num(f"{p} G2 h{k+1}", pa["g2_m"][k], pb["G2_m"][k])
    num(f"{p} G3", pa["g3"], pb["G3"])
    num(f"{p} G4 z1", pa["z1_diff_m"], pb["G4"]["z1_diff_m"])
    num(f"{p} G4 z2", pa["z2_diff_m"], pb["G4"]["z2_diff_m"])
    num(f"{p} G4 dz", pa["dz_diff_m"], pb["G4"]["dz_diff_m"])
    num(f"{p} G5", pa["g5"], pb["G5_max"])
    disc(f"{p} G5 samples", pa["g5_samples"], pb["G5_n_samples"])
g = A["gates"]
disc("G-1 pass", g["G-1"]["pass"], B["gates"]["G1_pass"])
disc("G-1 count", g["G-1"]["count"], B["gates"]["G1_n"])
disc("G-2 pass", g["G-2"]["pass"], B["gates"]["G2_pass"])
disc("G-3 pass", g["G-3"]["pass"], B["gates"]["G3_pass"])
disc("G-5 flag", g["G-5"]["flag"], B["gates"]["G5_flag"])
for e in range(1, 9):
    pa = A["predictions"][f"E-{e}"]
    pb = B["predictions"][f"E{e}"]
    disc(f"E-{e} confirmed", pa.get("confirmed", pa.get("within")), pb["result"] == "예측 확인")
    num(f"E-{e} value", pa.get("observed_m", pa.get("observed")), pb["value"])
bad = [i for i in items if not i[4]]
mx = max((i[3] for i in items if i[3] is not None), default=0.0)
for i in items:
    print(("OK " if i[4] else "BAD"), i[0], i[1], i[2], "" if i[3] is None else f"{i[3]:.3e}")
print(json.dumps({"n_items": len(items), "n_bad": len(bad), "max_abs_diff": mx}))
