"""Summary table of an s9 result file (one line per run)."""
import json
import sys

d = json.loads(open(sys.argv[1], encoding="utf-8").read())
flt = sys.argv[2] if len(sys.argv) > 2 else ""
F_MIN = 9.415
hdr = ("id", "READY", "off", "rc", "crN@R", "SumF/W", "c_est", "c_rut", "minM", "attOff", "attEnd", "stroke", "reap",
       "prb", "rel", "warn", "loc_t", "c@P", "c@loc", "bias", "What")
print(" | ".join(hdr))
for r in d["runs"]:
    if flt and flt not in r["id"]:
        continue
    if "error" in r:
        print(r["id"], "ERROR", r["error"])
        continue
    m = r.get("soil_rule_meta") or {}

    def f(x, n=1):
        return "-" if x is None else f"{x:.{n}f}"
    print(" | ".join([
        r["id"], f(r["t_ready_s"]), f(r["t_crawler_off_first_s"]), str(r.get("n_crawler_recontact")),
        f(None if r["crawler_N_at_ready"] is None else r["crawler_N_at_ready"] / 1e3),
        f(r["sumF_over_Wcyl_at_ready"], 3), f(r["clear_est_ready_mm"]), f(r["clear_true_ready_mm"]),
        f(r["min_margin_after_off_kN"]), f(r["att_max_after_off_deg"], 2),
        f(max(abs(a) for a in r["att_end_deg"]), 3), f(r["max_motor_stroke_mm"]), str(r["n_reapproach"]),
        str(r["n_probe_rounds"]), str(r["n_relevel"]), str(r["n_warn"]), f(m.get("t_loc_s")),
        f(m.get("clear_est_at_P_mm")), f(m.get("clear_est_at_loc_mm")), f(m.get("bias_mm")),
        f(None if m.get("W_hat_N") is None else m["W_hat_N"] / 1e3)]))
