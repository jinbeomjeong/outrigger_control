"""Independent recount of the D-b phase verdict (plan 0f24fcbe + rev1 91cd13e7)
and mechanism extraction for D-a / D-c. Does not import las_phase_judge."""
import itertools
import json
import statistics
from pathlib import Path

DIAG = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\las\diag")
V5 = Path(r"C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5")
OUT = Path(__file__).with_name("diag_recount_out.json")


def load(p):
    with open(p, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


db = load(DIAG / "diag_Db.jsonl")
res = {"n_lines": len(db)}

# ---------------- anchors
las_b0 = {r["d1"]["key"]: r["commands_sha256"] for r in load(V5 / "las" / "las_T1.jsonl")
          if r["las"]["candidate"] == "b0" and r["las"]["mode"] == "act"}
lf_f2 = {r["fb"]["key"]: r["commands_sha256"] for r in load(V5 / "fb" / "fb_F2.jsonl") if r["fb"]["candidate"] == "LF"}

NOM = 0.8768421006980677
rows = {}
excl = []
for r in db:
    d = r["diag"]
    tb, sm = d["touch_budget"], d["summary"]
    key = d["key"]
    kk = "VB" if "|VB|" in key else "V0"
    c = float(tb["s_c"])
    cname = "1" if abs(c - 1) < 1e-12 else ("0.94" if abs(c - 0.94) < 1e-12 else ("nom" if abs(c - NOM) < 1e-9 else str(c)))
    j = int(tb["j"])
    # independent s check: s = s_c T_c / (T_c + 0.025 j), T_c = T_1 / s_c, T_1 = 165*0.1*s_nom
    T1 = 165 * 0.1 * NOM
    Tc = T1 / c
    s_exp = c * Tc / (Tc + 0.025 * j)
    if abs(s_exp - tb["s"]) > 1e-9:
        excl.append((key, cname, j, f"s mismatch {tb['s']} vs {s_exp}"))
    if not sm.get("gate_consistent"):
        excl.append((key, cname, j, "gate_consistent False"))
    if sm.get("level_budget_periods", 0) != 0 or tb.get("level_budget_periods", 0) != 0:
        excl.append((key, cname, j, "LEVEL budget acted"))
    # gate consistency recheck on recorded periods: started <=> all gates true while armed
    for p in d["periods"]:
        la = p.get("las")
        if la and la["armed_before"] and not la["active_before"]:
            allg = all(la["gates"].values())
            if allg != la["started"]:
                excl.append((key, cname, j, f"start vs gates at {p['t_s']:.1f}"))
    rows[(kk, cname, j)] = dict(F=sm["F_RL_kN"], rho=sm["las_start_rho"], act=sm["las_active_periods"],
                                k=sm["las_start_period"], hash=r["commands_sha256"], key=key,
                                fb=sm["gates_false_before_start"], te=sm["t_touch_end_s"])
res["n_rows"] = len(rows)
anch = []
for kk in ("VB", "V0"):
    key = next(v["key"] for (a, _, _), v in rows.items() if a == kk)
    anch.append((f"A-1 {kk}", rows[(kk, "1", 0)]["hash"] == las_b0[key]))
    anch.append((f"A-2 {kk}", rows[(kk, "nom", 0)]["hash"] == lf_f2[key]))
res["anchors"] = anch
res["exclusions"] = excl
if len(rows) != 30 or excl or not all(a for _, a in anch):
    res["verdict"] = "undetermined(tool)"

# ---------------- measures
CENT = ["1", "0.94", "nom"]
meas = {}
for kk in ("VB", "V0"):
    for c in CENT:
        F = [rows[(kk, c, j)]["F"] for j in range(5)]
        R = max(F[:4]) - min(F[:4])
        M = statistics.mean(F[:4])
        P = abs(F[4] - F[0])
        cell = dict(R=R, M=M, P=P, P2=P <= max(0.3, 0.25 * R), evaluated=R >= 1.0)
        if cell["evaluated"]:
            st = [j for j in range(5) if rows[(kk, c, j)]["rho"] is not None and rows[(kk, c, j)]["act"] is not None]
            npred = ncon = 0
            for a, b in itertools.combinations(st, 2):
                ra, rb = rows[(kk, c, a)], rows[(kk, c, b)]
                for lo, hi in ((ra, rb), (rb, ra)):
                    dom = lo["act"] <= hi["act"] and lo["rho"] >= hi["rho"] and (lo["act"] < hi["act"] or lo["rho"] > hi["rho"])
                    if dom:
                        npred += 1
                        if lo["F"] > hi["F"] + 0.2:
                            ncon += 1
            cell.update(not_started=5 - len(st), pred=npred, contra=ncon,
                        P3=("undetermined" if (5 - len(st) > 1 or npred < 6) else ("pass" if ncon <= 1 else "fail")))
        meas[(kk, c)] = cell
res["measures"] = {f"{k[0]}|{k[1]}": v for k, v in meas.items()}

P1 = any(v["evaluated"] for v in meas.values())
P2 = all(v["P2"] for v in meas.values())
p3s = [v["P3"] for v in meas.values() if v["evaluated"]]
P3 = "undetermined" if (not p3s or "undetermined" in p3s) else ("pass" if all(x == "pass" for x in p3s) else "fail")
perkey = {}
for kk in ("VB", "V0"):
    Ms = [meas[(kk, c)]["M"] for c in CENT]
    Rs = [meas[(kk, c)]["R"] for c in CENT]
    mono = (Ms[0] >= Ms[1] >= Ms[2]) or (Ms[0] <= Ms[1] <= Ms[2])
    strict_mono = (Ms[0] > Ms[1] > Ms[2]) or (Ms[0] < Ms[1] < Ms[2])
    perkey[kk] = dict(spread=max(Ms) - min(Ms), maxR=max(Rs), P4=max(Ms) - min(Ms) <= max(Rs),
                      mono=strict_mono, change=abs(Ms[0] - Ms[2]), direction=(1 if Ms[0] < Ms[2] else -1),
                      speed=all(r < 0.5 for r in Rs) and strict_mono and abs(Ms[0] - Ms[2]) >= 1.0)
res["perkey"] = perkey
P4 = all(v["P4"] for v in perkey.values())
phase = P1 and P2 and P3 == "pass" and P4
mixed = P1 and P2 and P3 == "pass" and all(v["mono"] and v["change"] > v["maxR"] for v in perkey.values())
speed = all(v["speed"] for v in perkey.values()) and len({v["direction"] for v in perkey.values()}) == 1
res["conditions"] = dict(P1=P1, P2=P2, P3=P3, P4=P4, phase=phase, mixed=mixed, speed=speed)
if "verdict" not in res:
    res["verdict"] = "mixed" if mixed else ("phase" if phase else ("speed" if speed else "undetermined"))

# ---------------- mechanism: periods from TOUCH end to LAS start + 1
mech = []
for r in db:
    d = r["diag"]
    tb, sm = d["touch_budget"], d["summary"]
    kk = "VB" if "|VB|" in d["key"] else "V0"
    seq = []
    for p in d["periods"]:
        la = p.get("las")
        if la is None or p["t_s"] < sm["t_touch_end_s"] - 1e-6:
            continue
        if sm["t_las_start_s"] is not None and p["t_s"] > sm["t_las_start_s"] + 0.15:
            break
        seq.append(dict(t=round(p["t_s"], 1), sumW=round(la["sum_over_W"], 3), minF=round(la["min_over_F_min"], 2),
                        light=la["lightest_leg"], rho=round(la["rho"], 3), u=round(la["mean_u_over_v_max"], 2),
                        false=[g for g, v in la["gates"].items() if not v], started=la["started"],
                        loads=[round(x, 1) for x in p["loads_kN"]]))
    mech.append(dict(kk=kk, c=tb["s_c"], j=tb["j"], F=round(sm["F_RL_kN"], 3), k=sm["las_start_period"], seq=seq))
res["mech"] = mech
OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print("verdict", res["verdict"], res["conditions"])
print("anchors", anch, "excl", excl[:5], "n", len(rows))
for k, v in res["measures"].items():
    print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()})
for k, v in perkey.items():
    print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()})
