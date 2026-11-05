"""Judge the K1 soil sweep by sweep_criteria.md: metrics, separation, Chrono-anchored estimate, T1..T7, B1, forced-hold reading.
Reads k1soil\\sweep\\{A,B,Af,Bf}.jsonl and .npz and k1soil_values.json. Writes sweep\\sweep_values.json and sweep\\xval_rows.bin for Julia; prints a text view."""
import json
from pathlib import Path

import numpy as np

K = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono\k1soil")
S = K / "sweep"
LEGS = ("FL", "FR", "RL", "RR")
ROWS = ("FLFs0", "FLFs8", "RRFs0")
FMIN = 9.4146
DENSE = [round(0.01 * k, 2) for k in range(11)]
ALL = DENSE + [0.2, 0.35, 0.5, 0.7]
ANCHOR = {"FLFs0": 0.0, "FLFs8": 0.05, "RRFs0": 0.0}
ACC = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance")
REV85 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\s9\rev85")
HKEY = {"FLFs0": "A|G1|FL|Fs0|two", "FLFs8": "A|G1|FL|Fs8|two", "RRFs0": "A|G1|RR|Fs0|two"}


def load(arm):
    rows = {}
    for line in (S / f"{arm}.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        rows[(r["row"], r["delta"])] = r
    z = np.load(S / f"{arm}.npz")
    prov = json.loads((S / f"{arm}.prov.json").read_text(encoding="utf-8"))
    return rows, z, prov


def leg_min(z, row, d, wc):
    key = f"{row}_{d:.2f}"
    t, suf = z[key + "_t"], z[key + "_sufmin"]
    k = int(np.searchsorted(t, wc, side="right"))
    return {leg: float(suf[k, i]) / 1e3 for i, leg in enumerate(LEGS)}


def pair_metrics(aR, aZ, bR, bZ, row, d):
    a, b = aR[(row, d)], bR[(row, d)]
    wc = max(a["W_end_s"], b["W_end_s"])
    ma, mb = leg_min(aZ, row, d, wc), leg_min(bZ, row, d, wc)
    return {"wc": wc, "A": ma, "B": mb, "MA": min(ma.values()) - FMIN, "MB": min(mb.values()) - FMIN, "readyA": a["t_ready_back_s"], "readyB": b["t_ready_back_s"], "unionA": a["pair_union_s"], "unionB": b["pair_union_s"],
            "startsA": len(a["reapproach_starts"]), "startsB": len(b["reapproach_starts"]), "deferred": b["n_deferred_retrigger"], "passA": a["pass"], "passB": b["pass"], "failB": [k for k, v in b["gates"].items() if not v], "failA": [k for k, v in a["gates"].items() if not v],
            "faultB": b["fault_periods"], "faultA": a["fault_periods"], "finalB": b["final_phase"], "same_cmd": a["commands_sha256"] == b["commands_sha256"], "crawlerB": b["crawler"]["contact_in_window_ms"] + b["crawler"]["contact_outside_window_ms"], "crawlerA": a["crawler"]["contact_in_window_ms"] + a["crawler"]["contact_outside_window_ms"], "t_ev_same": abs(a["t_ev"] - b["t_ev"]) < 1e-9,
            "firstEvDeltaKn": None}


def sep(delta, base):
    d, b = np.array(delta, float), np.array(base, float)
    med = float(np.median(d))
    S_ = float(b.max() - b.min())
    n_same = int(max((d > 0).sum(), (d < 0).sum()))
    return {"median": round(med, 3), "min": round(float(d.min()), 3), "max": round(float(d.max()), 3), "S_A": round(S_, 3), "n_same_sign": n_same, "separated": bool(n_same >= 9 and abs(med) > S_ / 2)}


def main():
    A, AZ, Pa = load("A")
    B, BZ, Pb = load("B")
    Af, AfZ, Pf = load("Af")
    Bf, BfZ, Pg = load("Bf")
    chrono = json.loads((K / "k1soil_values.json").read_text(encoding="utf-8"))["rows"]
    oldoff = {r["key"]: r for r in json.loads((REV85 / "finB2_A.json").read_text(encoding="utf-8"))["results"]}
    soilA = {r["key"]: r for r in json.loads((ACC / "soil/soil_A.json").read_text(encoding="utf-8"))["results"]}
    out = {"valid": {}, "rows": {}, "tests": {}}
    errs = [(arm, k, v["error"]) for arm, R in (("A", A), ("B", B), ("Af", Af), ("Bf", Bf)) for k, v in R.items() if "error" in v]
    out["valid"] = {"errors": errs, "n": {"A": len(A), "B": len(B), "Af": len(Af), "Bf": len(Bf)}, "main_tree": [Pa["main_tree_modules"], Pb["main_tree_modules"], Pf["main_tree_modules"], Pg["main_tree_modules"]], "c2": sorted({p["c2_sha256"] for p in (Pa, Pb, Pf, Pg)}), "head": sorted({p["git_head"] for p in (Pa, Pb, Pf, Pg)}), "wall_s": [Pa["wall_s"], Pb["wall_s"], Pf["wall_s"], Pg["wall_s"]]}
    for row in ROWS:
        st = [x for x in soilA[HKEY[row]]["runs"] if x["event"] == "RE1bF" and x["timing"] == "level"][0]
        so = [x for x in oldoff[HKEY[row]]["runs"] if x["event"] == "RE1bF" and x["timing"] == "level"][0]
        out["valid"][row] = {"B0_hash_vs_soil_A": B[(row, 0.0)]["commands_sha256"] == st["commands_sha256"], "A0_hash_vs_stored_off": A[(row, 0.0)]["commands_sha256"] == so["commands_sha256"], "hold_in_A": A[(row, 0.0)]["base"]["hold"], "A_base_vs_off": A[(row, 0.0)]["base"]["commands_sha256"] == oldoff[HKEY[row]]["base"]["commands_sha256"], "hold_in_Af": Af.get((row, 0.0), {}).get("base", {}).get("hold")}
    tests = {}
    for row in ROWS:
        P = {d: pair_metrics(A, AZ, B, BZ, row, d) for d in ALL}
        dense = [P[d] for d in DENSE]
        rec = {"phases": {f"{d:.2f}": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in P[d].items() if k not in ("A", "B")} | {"A": {k: round(v, 2) for k, v in P[d]["A"].items()}, "B": {k: round(v, 2) for k, v in P[d]["B"].items()}} for d in ALL}}
        rec["same_cmd_phases"] = sum(1 for d in ALL if P[d]["same_cmd"])
        rec["deferred_range"] = [min(p["deferred"] for p in P.values()), max(p["deferred"] for p in P.values())]
        rec["t_ev_same_all"] = all(p["t_ev_same"] for p in P.values())
        seps = {}
        for leg in LEGS:
            seps[leg] = sep([p["B"][leg] - p["A"][leg] for p in dense], [p["A"][leg] for p in dense])
        seps["M"] = sep([p["MB"] - p["MA"] for p in dense], [p["MA"] for p in dense])
        seps["ready"] = sep([p["readyB"] - p["readyA"] for p in dense], [p["readyA"] for p in dense])
        seps["union"] = sep([p["unionB"] - p["unionA"] for p in dense], [p["unionA"] for p in dense])
        rec["sep"] = seps
        rec["worst"] = {"MA": round(min(p["MA"] for p in P.values()), 3), "MB": round(min(p["MB"] for p in P.values()), 3), "MA_d": min(P, key=lambda d: P[d]["MA"]), "MB_d": min(P, key=lambda d: P[d]["MB"]), "RR_below_Fmin": {"A": sum(p["A"]["RR"] < FMIN for p in P.values()), "B": sum(p["B"]["RR"] < FMIN for p in P.values())}, "RR_below_Fmin5": {"A": sum(p["A"]["RR"] < FMIN + 5 for p in P.values()), "B": sum(p["B"]["RR"] < FMIN + 5 for p in P.values())},
                        "RR_range": {"A": [round(min(p["A"]["RR"] for p in P.values()), 2), round(max(p["A"]["RR"] for p in P.values()), 2)], "B": [round(min(p["B"]["RR"] for p in P.values()), 2), round(max(p["B"]["RR"] for p in P.values()), 2)]}, "RL_range": {"A": [round(min(p["A"]["RL"] for p in P.values()), 2), round(max(p["A"]["RL"] for p in P.values()), 2)], "B": [round(min(p["B"]["RL"] for p in P.values()), 2), round(max(p["B"]["RL"] for p in P.values()), 2)]},
                        "ready_range": {"A": [min(p["readyA"] for p in P.values()), max(p["readyA"] for p in P.values())], "B": [min(p["readyB"] for p in P.values()), max(p["readyB"] for p in P.values())]}, "union_max": {"A": max(p["unionA"] for p in P.values()), "B": max(p["unionB"] for p in P.values())},
                        "fail_A": sum(not p["passA"] for p in P.values()), "fail_B": sum(not p["passB"] for p in P.values()), "pass_to_fail": [[d, P[d]["failB"]] for d in P if P[d]["passA"] and not P[d]["passB"]], "fail_to_pass": [[d, P[d]["failA"]] for d in P if P[d]["passB"] and not P[d]["passA"]], "fault_B": sum(p["faultB"] > 0 for p in P.values()), "fault_A": sum(p["faultA"] > 0 for p in P.values()), "crawler_B": sum(p["crawlerB"] > 0 for p in P.values()), "crawler_A": sum(p["crawlerA"] > 0 for p in P.values()),
                        "starts": {"A": [min(p["startsA"] for p in P.values()), max(p["startsA"] for p in P.values())], "B": [min(p["startsB"] for p in P.values()), max(p["startsB"] for p in P.values())]}}
        # Chrono-anchored estimate
        ch = chrono[row]
        common = ch["common_window"]
        CA, CB = common["RE1bF_off"], common["RE1bF_on"]
        da = ANCHOR[row]
        est = {}
        g = {}
        for leg in LEGS:
            dC = CB[leg] - CA[leg]
            dh = P[da]["B"][leg] - P[da]["A"][leg]
            g[leg] = max(1.0, abs(dC) / max(abs(dh), 0.5))
        for d in ALL:
            Ah = {leg: CA[leg] + P[d]["A"][leg] - P[da]["A"][leg] for leg in LEGS}
            Bh = {}
            for leg in LEGS:
                dh = P[d]["B"][leg] - P[d]["A"][leg]
                Bh[leg] = Ah[leg] + (g[leg] * dh if dh < 0 else dh)
            est[d] = {"A": Ah, "B": Bh, "MA": min(Ah.values()) - FMIN, "MB": min(Bh.values()) - FMIN}
        off_ready = ch["RE1bF_off"]["judgement"]["t_ready_back_s"]
        on_ready = ch["RE1bF_on"]["judgement"]["t_ready_back_s"]
        t_loop = ch["RE1bF_on"]["judgement"]["t_ev_loop_s"]
        dh_t = P[da]["readyB"] - P[da]["readyA"]
        g_t = max(1.0, (on_ready - off_ready) / max(dh_t, 0.5))
        ready_est = {}
        for d in ALL:
            At = off_ready + P[d]["readyA"] - P[da]["readyA"]
            dt = P[d]["readyB"] - P[d]["readyA"]
            ready_est[d] = {"A": At, "B": At + (g_t * dt if dt > 0 else dt)}
        rec["estimate"] = {"g": {k: round(v, 3) for k, v in g.items()}, "g_t": round(g_t, 3), "anchor_delta": da, "chrono_common_A": CA, "chrono_common_B": CB, "MA_min": round(min(e["MA"] for e in est.values()), 3), "MB_min": round(min(e["MB"] for e in est.values()), 3), "MB_d": min(est, key=lambda d: est[d]["MB"]), "n_below_B": sum(e["MB"] < 0 for e in est.values()), "n_below_A": sum(e["MA"] < 0 for e in est.values()),
                           "below_rows": [{"delta": d, "MB": round(e["MB"], 2), "MA": round(e["MA"], 2), "A_min_ok": bool(e["MA"] >= 0)} for d, e in est.items() if e["MB"] < 0], "RR_B_min": round(min(e["B"]["RR"] for e in est.values()), 2), "RR_A_min": round(min(e["A"]["RR"] for e in est.values()), 2), "n_RR_below_B": sum(e["B"]["RR"] < FMIN for e in est.values()), "n_RR_below_A": sum(e["A"]["RR"] < FMIN for e in est.values()),
                           "ready_B_max_s": round(max(e["B"] for e in ready_est.values()), 2), "ready_loop_B_max_s": round(t_loop + max(e["B"] for e in ready_est.values()), 2), "phases": {f"{d:.2f}": {"MA": round(e["MA"], 2), "MB": round(e["MB"], 2), "RR_A": round(e["A"]["RR"], 2), "RR_B": round(e["B"]["RR"], 2), "ready_B": round(ready_est[d]["B"], 2)} for d, e in est.items()}}
        # forced hold
        if row in ("FLFs0", "RRFs0"):
            Pf2 = {d: pair_metrics(Af, AfZ, Bf, BfZ, row, d) for d in ALL}
            df = [Pf2[d] for d in DENSE]
            q = {}
            for name, fn in (("M", lambda p: (p["MA"], p["MB"])), ("RL", lambda p: (p["A"]["RL"], p["B"]["RL"])), ("RR", lambda p: (p["A"]["RR"], p["B"]["RR"])), ("FL", lambda p: (p["A"]["FL"], p["B"]["FL"])), ("ready", lambda p: (p["readyA"], p["readyB"]))):
                hold_share = [fn(pf)[0] - fn(p)[0] for pf, p in zip(df, dense)]
                k_forced = [fn(pf)[1] - fn(pf)[0] for pf in df]
                k_plain = [fn(p)[1] - fn(p)[0] for p in dense]
                S_ = max(fn(p)[0] for p in dense) - min(fn(p)[0] for p in dense)
                dif = float(np.median(k_forced) - np.median(k_plain))
                q[name] = {"hold_share_median": round(float(np.median(hold_share)), 3), "hold_share_range": [round(min(hold_share), 3), round(max(hold_share), 3)], "K1_forced_median": round(float(np.median(k_forced)), 3), "K1_plain_median": round(float(np.median(k_plain)), 3), "K1_diff": round(dif, 3), "S_half": round(S_ / 2, 3), "unchanged": bool(abs(dif) < S_ / 2)}
            rec["forced"] = {"hold": Af[(row, 0.0)]["base"]["hold"], "D_pre_A_Af": [A[(row, 0.0)]["D_pre_kN"], Af[(row, 0.0)]["D_pre_kN"]], "F_pre_A_Af": [A[(row, 0.0)]["F_ev_pre_kN"], Af[(row, 0.0)]["F_ev_pre_kN"]], "compare": q,
                             "worst": {"MA": round(min(p["MA"] for p in Pf2.values()), 3), "MB": round(min(p["MB"] for p in Pf2.values()), 3), "RR_below_A": sum(p["A"]["RR"] < FMIN for p in Pf2.values()), "RR_below_B": sum(p["B"]["RR"] < FMIN for p in Pf2.values())}, "pass_to_fail": [[d, Pf2[d]["failB"]] for d in Pf2 if Pf2[d]["passA"] and not Pf2[d]["passB"]], "fault_B": sum(p["faultB"] > 0 for p in Pf2.values()), "union_max_B": max(p["unionB"] for p in Pf2.values()), "same_cmd": sum(p["same_cmd"] for p in Pf2.values())}
        out["rows"][row] = rec
    R = out["rows"]
    T = {}
    T["T1"] = {"pass": all(R[r]["worst"]["fault_B"] == 0 and not R[r]["worst"]["pass_to_fail"] for r in ROWS), "detail": {r: {"fault_B": R[r]["worst"]["fault_B"], "pass_to_fail": R[r]["worst"]["pass_to_fail"], "fail_A": R[r]["worst"]["fail_A"], "fail_B": R[r]["worst"]["fail_B"]} for r in ROWS}}
    T["T2"] = {"pass": all(R[r]["worst"]["MB"] >= 0 for r in ROWS), "detail": {r: R[r]["worst"]["MB"] for r in ROWS}}
    T["T3"] = {"pass": all(R[r]["estimate"]["n_below_B"] == 0 for r in ROWS), "detail": {r: {"MB_min": R[r]["estimate"]["MB_min"], "MA_min": R[r]["estimate"]["MA_min"], "n_below_B": R[r]["estimate"]["n_below_B"], "n_below_A": R[r]["estimate"]["n_below_A"], "below": R[r]["estimate"]["below_rows"]} for r in ROWS}}
    T["T3_A_ok_at_failing_phase"] = any(b["A_min_ok"] for r in ROWS for b in R[r]["estimate"]["below_rows"])
    n4 = sum(R[r]["worst"]["MB"] >= R[r]["worst"]["MA"] for r in ROWS)
    T["T4"] = {"pass": n4 >= 2, "rows_B_ge_A": n4, "detail": {r: [R[r]["worst"]["MA"], R[r]["worst"]["MB"]] for r in ROWS}}
    T["T5"] = {"pass": all(R[r]["worst"]["RR_below_Fmin"]["B"] <= R[r]["worst"]["RR_below_Fmin"]["A"] for r in ROWS), "detail": {r: R[r]["worst"]["RR_below_Fmin"] for r in ROWS}}
    T["T6"] = {"pass": all(R[r]["worst"]["union_max"]["B"] <= 1.8 for r in ROWS), "detail": {r: R[r]["worst"]["union_max"] for r in ROWS}}
    T["T7"] = {"pass": all(R[r]["estimate"]["ready_loop_B_max_s"] <= 90.0 for r in ROWS), "detail": {r: R[r]["estimate"]["ready_loop_B_max_s"] for r in ROWS}}
    nrl = sum(R[r]["sep"]["RL"]["median"] > 0 and R[r]["sep"]["RL"]["separated"] for r in ROWS)
    nm = sum(R[r]["sep"]["M"]["median"] > 0 and R[r]["sep"]["M"]["separated"] for r in ROWS)
    T["B1"] = {"pass": nrl >= 2 and nm >= 1, "RL_rows": nrl, "M_rows": nm}
    drop = (not T["T1"]["pass"]) or (not T["T2"]["pass"]) or (not T["T6"]["pass"]) or T["T3_A_ok_at_failing_phase"]
    full = all(T[k]["pass"] for k in ("T1", "T2", "T3", "T4", "T5", "T6", "T7", "B1"))
    T["verdict"] = "탈락 권고" if drop else ("예외 근거 있음" if full else "근거 불충분")
    out["tests"] = T
    (S / "sweep_values.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(out["valid"], ensure_ascii=False, default=str)[:1800])
    print("TESTS", json.dumps(T, ensure_ascii=False, default=str))
    for r in ROWS:
        v = R[r]
        print("=====", r, "same_cmd", v["same_cmd_phases"], "deferred", v["deferred_range"], "t_ev same", v["t_ev_same_all"])
        print(" worst", json.dumps(v["worst"], default=str))
        print(" sep", json.dumps(v["sep"]))
        e = dict(v["estimate"])
        ph = e.pop("phases")
        print(" est", json.dumps(e, default=str))
        print(" est phases", json.dumps(ph))
        print(" phases d: MA MB | RL A B | RR A B | FL A B | FR A B | ready A B | union A B | starts A B def")
        for d, p in v["phases"].items():
            print("  ", d, p["MA"], p["MB"], "|", p["A"]["RL"], p["B"]["RL"], "|", p["A"]["RR"], p["B"]["RR"], "|", p["A"]["FL"], p["B"]["FL"], "|", p["A"]["FR"], p["B"]["FR"], "|", p["readyA"], p["readyB"], "|", p["unionA"], p["unionB"], "|", p["startsA"], p["startsB"], p["deferred"], "passAB", p["passA"], p["passB"], p["failA"], p["failB"], p["same_cmd"])
        if "forced" in v:
            print(" forced", json.dumps(v["forced"], default=str))


if __name__ == "__main__":
    main()
