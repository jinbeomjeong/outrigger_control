import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, time, argparse
from dataclasses import replace, asdict
import numpy as np
import r8d1_lin as R

G7 = dict(Kp=0.4, Ki=0.02, tau_f=0.5, Ktw=1.0)
A8 = dict(Kp=0.2, Ki=0.01, tau_f=0.8, Ktw=1.0)
LO = dict(Kp=0.15, Ki=0.0075, tau_f=1.0, Ktw=0.7)

def C(**k):
    return R.Cfg(**k)

GROUPS = {}
# 1. baseline d = 1 exact multirate, valve lag as first-order lag
GROUPS["base"] = {}
for gn, g in (("G7", G7), ("A8", A8), ("LO", LO)):
    for tv in (0.0, 0.03, 0.05, 0.1):
        GROUPS["base"][f"d1_{gn}_tv{tv:g}"] = C(d=1, tau_v=tv, **g)
    GROUPS["base"][f"d0_{gn}_tv0.1"] = C(d=0, tau_v=0.1, **g)
    GROUPS["base"][f"d2_{gn}_tv0"] = C(d=2, tau_v=0.0, **g)       # tau_v 0.1 as a pure delay
# 2. predictor / late IMU read (A8 gains, tau_v 0.1 and 0.05)
GROUPS["comp"] = {}
for tv in (0.05, 0.1):
    for gn, g in (("A8", A8), ("G7", G7)):
        GROUPS["comp"][f"d1_{gn}_tv{tv:g}_late9"] = C(d=1, tau_v=tv, m_att=9, **g)
        GROUPS["comp"][f"d1_{gn}_tv{tv:g}_smTW"] = C(d=1, tau_v=tv, smith=("tw",), **g)
        GROUPS["comp"][f"d1_{gn}_tv{tv:g}_smATT"] = C(d=1, tau_v=tv, smith=("phi", "theta"), **g)
        GROUPS["comp"][f"d1_{gn}_tv{tv:g}_smALL"] = C(d=1, tau_v=tv, smith=R.CH, **g)
        GROUPS["comp"][f"d1_{gn}_tv{tv:g}_smALL_late9"] = C(d=1, tau_v=tv, smith=R.CH, m_att=9, **g)

DES = {
    "A8": dict(A8),
    "A8k08": dict(A8, Ktw=0.8),
    "A8L": dict(A8, m_att=9),
    "A8S": dict(A8, smith=("tw",)),
    "A8LS": dict(A8, m_att=9, smith=("tw",)),
    "LO": dict(LO),
    "G7L": dict(G7, m_att=9),
    "M6L": dict(Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=1.0, m_att=9),
}
GROUPS["tv"] = {f"{dn}_tv{tv:g}": C(d=1, tau_v=tv, **dv) for dn, dv in DES.items()
                for tv in (0.0, 0.02, 0.05, 0.08, 0.1, 0.12, 0.15, 0.2)}
GROUPS["rate"] = {}
for T, N in ((0.05, 5), (0.04, 4), (0.025, 5), (0.02, 2)):
    for gn, g in (("G7", G7), ("A8", A8)):
        for tv in (0.0, 0.05, 0.1, 0.15):
            GROUPS["rate"][f"T{T:g}_{gn}_tv{tv:g}"] = C(T=T, N=N, d=1, tau_v=tv, **g)
GROUPS["robust"] = {}
for dn in ("A8", "A8k08", "A8L", "A8LS", "LO", "M6L", "G7L"):
    for tv in (0.05, 0.1, 0.15):
        dv = DES[dn]
        GROUPS["robust"][f"{dn}_tv{tv:g}_q2"] = C(d=1, tau_v=tv, q_out=2, **dv)
        GROUPS["robust"][f"{dn}_tv{tv:g}_p2"] = C(d=1, tau_v=tv, p_imu=2, **dv)
for sc in (0.5, 0.7, 1.5, 2.0):
    for tv in (0.1,):
        GROUPS["robust"][f"A8S_tv{tv:g}_sm{sc:g}"] = C(d=1, tau_v=tv, smith_scale=(1, 1, 1, sc), **DES["A8S"])
        GROUPS["robust"][f"A8S_tv{tv:g}_tvm0.05"] = C(d=1, tau_v=tv, tau_v_model=0.05, **DES["A8S"])
        GROUPS["robust"][f"A8S_tv{tv:g}_tvm0.15"] = C(d=1, tau_v=tv, tau_v_model=0.15, **DES["A8S"])

DES2 = {
    "M6": dict(Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=1.0),
    "M6k08": dict(Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8),
    "M6Lk08": dict(Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8, m_att=9),
    "M5L": dict(Kp=0.3, Ki=0.015, tau_f=0.5, Ktw=1.0, m_att=9),
    "G7f6L": dict(Kp=0.4, Ki=0.02, tau_f=0.6, Ktw=1.0, m_att=9),
    "G7f7L": dict(Kp=0.4, Ki=0.02, tau_f=0.7, Ktw=1.0, m_att=9),
    "M6L": dict(Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=1.0, m_att=9),
    "A8": dict(A8), "A8k08": dict(A8, Ktw=0.8),
}
GROUPS["des2"] = {f"{dn}_tv{tv:g}": C(d=1, tau_v=tv, **dv) for dn, dv in DES2.items() if dn not in ("M6L", "A8", "A8k08")
                  for tv in (0.05, 0.1, 0.15)}
GROUPS["des2"]["R7_50Hz"] = C(T=0.02, N=2, d=1, tau_v=0.0, **G7)
GROUPS["des2"]["R7_50Hz_N1"] = C(T=0.02, N=1, d=1, tau_v=0.0, **G7)
GROUPS["rob2"] = {}
DES2["M5L"] = dict(Kp=0.3, Ki=0.015, tau_f=0.5, Ktw=1.0, m_att=9)
DES2["G7L"] = dict(G7, m_att=9)
for dn in ("M5L", "M6L", "M6Lk08", "A8", "A8k08", "G7L"):
    for tv in (0.05, 0.1, 0.15):
        dv = DES2[dn]
        GROUPS["rob2"][f"{dn}_tv{tv:g}_q2"] = C(d=1, tau_v=tv, q_out=2, **dv)
        GROUPS["rob2"][f"{dn}_tv{tv:g}_p2"] = C(d=1, tau_v=tv, p_imu=2, **dv)
        GROUPS["rob2"][f"{dn}_tv{tv:g}_q2p2"] = C(d=1, tau_v=tv, q_out=2, p_imu=2, **dv)

GROUPS["rate2"] = {}
for T, N in ((0.1, 10), (0.08, 8), (0.06, 6), (0.05, 5), (0.04, 4), (0.03, 3), (0.02, 2)):
    for tv in (0.0, 0.05, 0.1, 0.15):
        GROUPS["rate2"][f"T{T:g}_G7_tv{tv:g}"] = C(T=T, N=N, d=1, tau_v=tv, **G7)
        GROUPS["rate2"][f"T{T:g}_G7L_tv{tv:g}"] = C(T=T, N=N, d=1, tau_v=tv, m_att=N - 1, **G7)
        GROUPS["rate2"][f"T{T:g}_A8_tv{tv:g}"] = C(T=T, N=N, d=1, tau_v=tv, **A8)

GROUPS["harn"] = {}
for dn, dv in (("R12AR", A8), ("A8k08", dict(A8, Ktw=0.8)), ("M5", dict(Kp=0.3, Ki=0.015, tau_f=0.5, Ktw=1.0)),
               ("M6", dict(Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=1.0)), ("G7", G7)):
    for tv in (0.0, 0.1):
        GROUPS["harn"][f"H_{dn}_d1_tv{tv:g}"] = C(N=1, d=1, tau_v=tv, **dv)            # harness: IMU 100 ms mean, d = 1
        GROUPS["harn"][f"H_{dn}_late_tv{tv:g}"] = C(N=1, d=0, pd=1, tau_v=tv, **dv)    # harness 'late' scheme
for tv in (0.0, 0.1):
    GROUPS["harn"][f"H_R7_50Hz_tv{tv:g}"] = C(T=0.02, N=1, d=1, tau_v=tv, **G7)

def worker(args):
    item, cfgs = args
    lp = R.make_plant(item)
    out = {}
    for name, cfg in cfgs.items():
        try:
            r, _ = R.analyse(lp, cfg)
            out[name] = {"Ms_max": r["Ms_max"], "Ms_ch": r["Ms_ch"], "rho": r["rho"],
                         "Ms": {c: r[c]["Ms"] for c in R.CH}, "wMs": {c: r[c]["w_Ms"] for c in R.CH},
                         "PM": {c: r[c]["PM"] for c in R.CH}, "wgc": {c: r[c]["wgc"] for c in R.CH}, "Ms_leg": r["Ms_leg_sv"]}
        except Exception as e:
            out[name] = {"error": repr(e)}
    return R.tag(lp), out

def summarise(rows, names):
    S = {}
    for n in names:
        good = [(t, r[n]) for t, r in rows if "error" not in r[n]]
        if not good:
            S[n] = {"errors": len(rows)}; continue
        w = max(good, key=lambda x: x[1]["Ms_max"])
        chw = {c: max(good, key=lambda x: x[1]["Ms"][c]) for c in R.CH}
        S[n] = {"n": len(good), "errors": len(rows) - len(good), "Ms_worst": round(w[1]["Ms_max"], 4), "plant": w[0],
                "ch": w[1]["Ms_ch"], "w_Ms": round(w[1]["wMs"][w[1]["Ms_ch"]], 3),
                "over1.5": sum(r["Ms_max"] > 1.5 for _, r in good), "over1.6": sum(r["Ms_max"] > 1.6 for _, r in good),
                "unstable": sum(r["rho"] >= 1 for _, r in good),
                "Ms_leg_max": round(max(r["Ms_leg"] for _, r in good), 4),
                "ch_worst": {c: (round(chw[c][1]["Ms"][c], 4), chw[c][0], round(chw[c][1]["wMs"][c], 3)) for c in R.CH}}
    return S

GROUPS["rob2"]["A8S_tv0.1_sm0.5"] = C(d=1, tau_v=0.1, smith_scale=(1, 1, 1, 0.5), **DES["A8S"])
GROUPS["rob2"]["A8S_tv0.1_sm2"] = C(d=1, tau_v=0.1, smith_scale=(1, 1, 1, 2.0), **DES["A8S"])
GROUPS["rob2"]["A8S_tv0.1_tvm0.05"] = C(d=1, tau_v=0.1, tau_v_model=0.05, **DES["A8S"])
GROUPS["rob2"]["A8S_tv0.1_tvm0.15"] = C(d=1, tau_v=0.1, tau_v_model=0.15, **DES["A8S"])
for dn in ("M5L", "A8k08"):
    GROUPS["rob2"][f"{dn}_tv0.1_p5"] = C(d=1, tau_v=0.1, p_imu=5, **DES2[dn])
    GROUPS["rob2"][f"{dn}_tv0.1_q5"] = C(d=1, tau_v=0.1, q_out=5, **DES2[dn])

FIN = {
    "A8T3": dict(A8, tau_tw=0.3),
    "A8T2": dict(A8, tau_tw=0.2),
    "M6LT3": dict(Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=1.0, m_att=9, tau_tw=0.3),
    "M6LT2": dict(Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=1.0, m_att=9, tau_tw=0.2),
    "M6Lk08": dict(Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8, m_att=9),
    "M5LT3": dict(Kp=0.3, Ki=0.015, tau_f=0.5, Ktw=1.0, m_att=9, tau_tw=0.3),
    "G7LT3": dict(G7, m_att=9, tau_tw=0.3),
}
GROUPS["fin"] = {}
for dn, dv in FIN.items():
    for tv in (0.05, 0.1, 0.15):
        GROUPS["fin"][f"{dn}_tv{tv:g}"] = C(d=1, tau_v=tv, **dv)
    GROUPS["fin"][f"{dn}_tv0.1_q2"] = C(d=1, tau_v=0.1, q_out=2, **dv)
    GROUPS["fin"][f"{dn}_tv0.1_p2"] = C(d=1, tau_v=0.1, p_imu=2, **dv)
    for gl in range(4):
        GROUPS["fin"][f"{dn}_tv0.1_g{gl}"] = C(d=1, tau_v=0.1, guard_leg=gl, **dv)
GROUPS["guardref"] = {}
for gl in range(4):
    GROUPS["guardref"][f"R7_50Hz_tv0.1_g{gl}"] = C(T=0.02, N=2, d=1, tau_v=0.1, guard_leg=gl, **G7)
    GROUPS["guardref"][f"A8_tv0.1_g{gl}"] = C(d=1, tau_v=0.1, guard_leg=gl, **A8)
    GROUPS["guardref"][f"A8_d0_tv0.1_g{gl}"] = C(d=0, tau_v=0.1, guard_leg=gl, **A8)

GROUPS["guardkg"] = {}
for dn, dv in (("M6Lk08", FIN["M6Lk08"]), ("A8k08", dict(A8, Ktw=0.8)), ("M6LT2", FIN["M6LT2"]), ("A8", dict(A8))):
    for kg in (0.25, 0.4, 0.6):
        for gl in range(4):
            GROUPS["guardkg"][f"{dn}_tv0.1_Kg{kg:g}_g{gl}"] = C(d=1, tau_v=0.1, guard_leg=gl, Kg=kg, **dv)
for kg in (0.25, 0.4, 0.6):
    for gl in range(4):
        GROUPS["guardkg"][f"M6Lk08_tv0.15_Kg{kg:g}_g{gl}"] = C(d=1, tau_v=0.15, guard_leg=gl, Kg=kg, **FIN["M6Lk08"])
        GROUPS["guardkg"][f"M6Lk08_tv0.05_Kg{kg:g}_g{gl}"] = C(d=1, tau_v=0.05, guard_leg=gl, Kg=kg, **FIN["M6Lk08"])

NL = {
    "A8k05": dict(A8, Ktw=0.5),
    "A8k05T2": dict(A8, Ktw=0.5, tau_tw=0.2),
    "LOk05": dict(LO, Ktw=0.5),
    "LO": dict(LO),
    "A8f1k05": dict(Kp=0.2, Ki=0.01, tau_f=1.0, Ktw=0.5),
}
GROUPS["nolate"] = {}
for dn, dv in NL.items():
    GROUPS["nolate"][f"{dn}_tv0.1"] = C(d=1, tau_v=0.1, **dv)
    for kg in (0.1, 0.15, 0.25):
        for gl in range(4):
            GROUPS["nolate"][f"{dn}_tv0.1_Kg{kg:g}_g{gl}"] = C(d=1, tau_v=0.1, guard_leg=gl, Kg=kg, **dv)

FINAL = {
    "C1": (dict(Kp=0.3, Ki=0.015, tau_f=0.6, Ktw=0.8, m_att=9), 0.25),
    "C2": (dict(A8, Ktw=0.5, tau_tw=0.2), 0.15),
    "C2b": (dict(A8, Ktw=0.5), 0.15),
}
GROUPS["final"] = {}
for dn, (dv, kg) in FINAL.items():
    for tv in (0.0, 0.05, 0.1, 0.15, 0.2):
        GROUPS["final"][f"{dn}_tv{tv:g}"] = C(d=1, tau_v=tv, **dv)
        for gl in range(4):
            GROUPS["final"][f"{dn}_tv{tv:g}_G_g{gl}"] = C(d=1, tau_v=tv, guard_leg=gl, Kg=kg, **dv)
    for ext in ("q2", "p2", "q2p2"):
        kw = dict(q_out=2 if "q2" in ext else 0, p_imu=2 if "p2" in ext else 0)
        GROUPS["final"][f"{dn}_tv0.1_{ext}"] = C(d=1, tau_v=0.1, **kw, **dv)
        for gl in range(4):
            GROUPS["final"][f"{dn}_tv0.1_{ext}_G_g{gl}"] = C(d=1, tau_v=0.1, guard_leg=gl, Kg=kg, **kw, **dv)

GROUPS["rateg"] = {}
for T, N in ((0.05, 5), (0.04, 4), (0.03, 3), (0.02, 2)):
    for kg in (1.0, 0.5):
        for gl in range(4):
            GROUPS["rateg"][f"T{T:g}_G7_tv0.1_Kg{kg:g}_g{gl}"] = C(T=T, N=N, d=1, tau_v=0.1, guard_leg=gl, Kg=kg, **G7)
            GROUPS["rateg"][f"T{T:g}_G7L_tv0.1_Kg{kg:g}_g{gl}"] = C(T=T, N=N, d=1, tau_v=0.1, m_att=N - 1, guard_leg=gl, Kg=kg, **G7)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--groups", default="base"); ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cfgs = {}
    for g in a.groups.split(","):
        cfgs.update(GROUPS[g])
    items = R.catalogue_ext()
    t0 = time.perf_counter()
    from multiprocessing import Pool
    with Pool(a.workers) as p:
        rows = p.map(worker, [(it, cfgs) for it in items], chunksize=1)
    S = summarise(rows, list(cfgs))
    out = a.out or f"r8d1_{a.groups.replace(',', '_')}.json"
    json.dump({"cfgs": {k: asdict(v) for k, v in cfgs.items()}, "summary": S, "rows": rows}, open(out, "w"), indent=1, default=float)
    for k, v in S.items():
        print(k, {kk: vv for kk, vv in v.items() if kk != "ch_worst"})
        print("     ", v.get("ch_worst"))
    print("wall", round(time.perf_counter() - t0, 1))
