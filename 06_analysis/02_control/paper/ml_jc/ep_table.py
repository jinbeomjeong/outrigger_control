"""Compact episode table (leg, t_on, duration, is_lift, flags) from the replay of stored batches and final reruns."""
import glob
import json
import os

R = r"C:\workspace\outrigger_control\07_results\S8"
A = r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\verdict\judgement_chrono\v4_recheck\verify_final_v4recheck_20261104_202815.json"
F = r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85\evidence\final_r_rep\verify_final_E_RE1bF_Fs8_20261031_000914.json"
RUNS = [("p1r_20261024_222013", ["E_RE1bF_Fs0", "E_RE1bF_Fs8", "E_RE1bP_Fs0", "E_RE1bP_Fs8"]),
        ("rest_20261024_233615", ["N_G4_Fs8_pressure", "N_SS_Fs8_pressure", "N_RE1bF_Fs0_pressure", "N_RE1bF_Fs8_pressure",
                                  "N_RE1c_Fs0_combined", "N_RE1c_Fs8_combined"])]


def show(v, c, tag):
    it = v["s8_metrics"][c]["item9"]["replay"]
    t0 = None
    for j in ("J_C", "J_P"):
        eps = it[j]["episodes"]
        miss = it[j]["score"]["M1_missed"]
        print(f"{tag} {c} {j} n={len(eps)} M1={miss} M1p={it[j]['score']['M1p_late']}")
        if j == "J_C":
            for e in eps:
                print(f"   {e['leg']} t_on={e['t_on_s']:.1f} dur={e['t_off_s']-e['t_on_s']:.1f} lift={e['is_lift']} first_decision={e['first_decision_s']} transient={e['crawler_transient']} sampling_only={e['sampling_only']}")
        else:
            print("   J_P first_decision None:", [(e['leg'], round(e['t_on_s'], 1)) for e in eps if e['first_decision_s'] is None])


lift = nolift = 0
for b, cases in RUNS:
    v = json.load(open(os.path.join(R, b, "verify_S8C.json"), encoding="utf-8"))
    for c in cases:
        show(v, c, b[:4])
        for e in v["s8_metrics"][c]["item9"]["replay"]["J_C"]["episodes"]:
            if e["is_lift"]:
                lift += 1
            else:
                nolift += 1
print("lift", lift, "nolift", nolift)
v = json.load(open(A, encoding="utf-8"))
for c in ("E_RE1bF_Fs0", "E_RE1bP_Fs0", "E_RE1bP_Fs8", "N_G4_Fs8_pressure", "N_SS_Fs8_pressure"):
    show(v, c, "RECHECK")
v = json.load(open(F, encoding="utf-8"))
show(v, "E_RE1bF_Fs8", "FINALREP")
print("CP 0/12", 1 - 0.05 ** (1 / 12), "CP 0/6", 1 - 0.05 ** (1 / 6))
