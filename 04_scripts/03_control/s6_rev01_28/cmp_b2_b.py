"""Compare settlement/drop cases: B2 (L1-R on, M1) vs bundle B (L1-R off substitute)."""
import json

# migrated 2026-10-25 from session scratchpad a06eea4a ctrl-run; repository-relative
ROOT = (__import__("pathlib").Path(__file__).resolve().parents[3] / "06_analysis" / "01_chrono" / "16_S6").as_posix() + "/"
b2 = json.load(open(ROOT + "verify_S6_L1_closed_loop_L1R_B2.json", encoding="utf-8"))
bb = json.load(open(ROOT + "verify_S6_L1_closed_loop_L1R.json", encoding="utf-8"))

ITEMS = [
    ("3 F_min (1 ms)", "Fmin"),
    ("3 F_min before the event", "Fpre"),
    ("3 F_min after the re-READY", "Fpost"),
    ("RE1b re-READY <= 60 s", "reR"),
    ("6 re-READY <= 40 s", "reR6"),
    ("6 min after settlement", "F6"),
    ("4 max pressure in the event transient", "pEv"),
    ("4 max moving pressure outside the event trans", "pMov"),
    ("2 attitude +-0.2 (+mount)", "att"),
    ("7c load estimate error", "7c"),
    ("5a rocking amplitude in the event transient", "rockEv"),
    ("3 lift-off RR time / ratio", "RRlift"),
]


def table(d):
    out = {}
    for r in d["rows"]:
        for key, short in ITEMS:
            if r["item"].startswith(key):
                v = r["value"]
                out.setdefault(r["case"], {})[short] = (v, r["passed"])
    return out


t2, tb = table(b2), table(bb)


def f(x):
    if x is None:
        return "-"
    v, p = x
    if isinstance(v, list):
        s = "/".join(f"{y:.2f}" for y in v)
    elif isinstance(v, float):
        s = f"{v:.2f}"
    else:
        s = str(v)
    return s + ("" if p in (True, None) else "!")


shorts = [s for _, s in ITEMS]
print("case".ljust(36), " | ".join(s.rjust(10) for s in shorts))
for case in b2["cases"]:
    if case.startswith("PS7"):
        continue
    for tag, t in (("B2", t2), ("B ", tb)):
        row = t.get(case, {})
        print(f"{tag} {case[:33]:33s}", " | ".join(f(row.get(s)).rjust(10) for s in shorts))
# per case min_cyl excluding and h4 etc
print()
for case in b2["cases"]:
    if case in bb["cases"]:
        c2, cb = b2["cases"][case], bb["cases"][case]
        print(f"{case[:36]:36s} readyB2={c2['times_s']['ready']:.2f} readyB={cb['times_s']['ready']:.2f} "
              f"final_cyl B2={[round(x,1) for x in c2['final_cyl_kN']]} B={[round(x,1) for x in cb['final_cyl_kN']]}")
