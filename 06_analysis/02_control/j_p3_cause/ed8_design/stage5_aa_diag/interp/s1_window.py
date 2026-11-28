"""Interp step 1: per label, the periods from t_event - 0.1 s to t_event + 0.5 s of the primary
monitor (the monitor of the first-step row in first_step_period.csv): head bar, sum F, f_z,
M f_z, residual r and its change. Writes interp/window_rows.csv and prints them."""
import csv
import sys
from pathlib import Path

D = Path(sys.argv[1])
first = list(csv.DictReader(open(D / "first_step_period.csv", encoding="utf-8")))
tev = {r["label"]: float(r["t_event_s"]) for r in first}
lift = {r["label"]: float(r["lift_s"]) for r in first}
rows = list(csv.DictReader(open(D / "event_window.csv", encoding="utf-8")))
# primary monitor: the one that has a row at the first-step period with residual_change
step_t = {r["label"]: float(r["t_s"]) for r in first}
mon = {}
for r in rows:
    if abs(float(r["t_s"]) - step_t[r["label"]]) < 1e-6 and r["residual_change_kN"]:
        mon.setdefault(r["label"], r["monitor"])
cols = ["label", "t_s", "t_rel_lift_s", "head_bar_FL", "head_bar_FR", "head_bar_RL", "head_bar_RR",
        "rod_bar_FL", "rod_bar_FR", "rod_bar_RL", "rod_bar_RR",
        "net_sum_kN", "f_z_used_m_s2", "M_f_z_kN", "residual_kN", "residual_change_kN",
        "head_step_candidates", "head_fault_reasons"]
out = []
for r in rows:
    lab = r["label"]
    t = float(r["t_s"])
    if r["monitor"] != mon.get(lab) or not (tev[lab] - 0.15 <= t <= tev[lab] + 0.45):
        continue
    rec = {c: r.get(c, "") for c in cols}
    rec["t_rel_lift_s"] = round(t - lift[lab], 4)
    out.append(rec)
with open(D / "interp" / "window_rows.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(out)


def f(x, n=1):
    try:
        return f"{float(x):.{n}f}"
    except ValueError:
        return "-"


for r in out:
    print(r["label"][:3], f(r["t_s"], 2), f(r["t_rel_lift_s"], 3), "h", f(r["head_bar_FL"]), f(r["head_bar_FR"]),
          f(r["head_bar_RL"]), f(r["head_bar_RR"]), "S", f(r["net_sum_kN"]), "fz", f(r["f_z_used_m_s2"], 3),
          "Mfz", f(r["M_f_z_kN"]), "r", f(r["residual_kN"]), "dr", f(r["residual_change_kN"]),
          r["head_step_candidates"], r["head_fault_reasons"])
