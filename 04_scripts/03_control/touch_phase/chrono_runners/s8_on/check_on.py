"""Check 1: eps 0 short run vs stored flow-on, raw signals, exact. Check 2: small eps short run, delivered speed and audit. Read only.

Usage: python -I -B -X utf8 check_on.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CASE = "S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0"
STORED = Path(r"C:\workspace\outrigger_control\07_results\S9\batch_COUPLED_eta085_20261104_142213") / CASE
LEGS = ("FL", "FR", "RL", "RR")
FILES = (("record/record.npz", "t"), ("r8_series.npz", "t"), ("step_series.npz", "t_s"), ("completion_series.npz", "t_s"), ("controller_commands.npz", "t_s"))


def compare(new: Path) -> dict:
    out, ok = {}, True
    for rel, tk in FILES:
        a, b = np.load(new / rel, allow_pickle=False), np.load(STORED / rel, allow_pickle=False)
        n = min(len(a[tk]), len(b[tk]))
        row = {"arrays": 0, "values": 0, "different": {}, "t_last": float(a[tk][n - 1]), "rows": n}
        for k in a.files:
            if k not in b.files or a[k].ndim == 0 or not len(a[k]) or len(a[k]) != len(a[tk]) or a[k].dtype.kind not in "fiubU":
                continue
            x, y = a[k][:n], b[k][:n]
            row["arrays"] += 1
            row["values"] += x.size
            same = ((x == y) | (np.isnan(x) & np.isnan(y))) if x.dtype.kind == "f" else (x == y)
            if not same.all():
                m = same.reshape(n, -1).all(axis=1)
                i = int(np.argmin(m))
                row["different"][k] = {"t": float(a[tk][i]), "n": int((~m).sum())}
        ok &= not row["different"]
        out[rel] = row
    a, b = np.load(new / "flow_series.npz", allow_pickle=True), np.load(STORED / "flow_series.npz", allow_pickle=True)
    ra, rb = a["rows"], b["rows"]
    n = min(len(ra), len(rb))
    same = (ra[:n] == rb[:n]) | (np.isnan(ra[:n]) & np.isnan(rb[:n]))
    cols = [str(c) for c in a["columns"]]
    bad = [cols[j] for j in range(same.shape[1]) if not same[:, j].all()]
    out["flow_series.npz"] = {"rows": n, "columns": len(cols), "different_columns": bad, "t_last": float(ra[n - 1, 0]),
                              "limited_rows": int((ra[:n, cols.index("limited_mask")] > 0).sum())}
    ok &= not bad
    res_a, res_b = (json.loads((d / "result.json").read_text(encoding="utf-8")) for d in (new, STORED))
    argd = {k: (res_a["args"].get(k), res_b["args"].get(k)) for k in set(res_a["args"]) | set(res_b["args"]) if res_a["args"].get(k) != res_b["args"].get(k)}
    m = min(len(res_a["s9_rows"]), len(res_b["s9_rows"]))
    s9bad = [k for k in res_a["s9_rows"][0] if any(res_a["s9_rows"][i].get(k) != res_b["s9_rows"][i].get(k) for i in range(m))]
    out["args_diff_keys"] = sorted(argd)
    out["s9_rows"] = {"compared": m, "keys_different": s9bad}
    out["settle_reference_same"] = res_a.get("settle_reference") == res_b.get("settle_reference")
    out["params_sha_same"] = res_a["meta"].get("params_sha256") == res_b["meta"].get("params_sha256")
    out["all_same"] = bool(ok and not s9bad and out["settle_reference_same"] and out["params_sha_same"])
    out["wall_s"] = res_a.get("wall_s")
    out["flow_summary_check"] = {k: res_a["flow_limit"]["summary"].get(k) for k in ("max_sum_Q_over_supply_minus_1", "steps", "short_s", "limited_s")}
    out["wrapper"] = json.loads((new / "eps_wrapper.json").read_text(encoding="utf-8"))["state"]
    return out


def eps_check(new: Path) -> dict:
    side = json.loads((new / "eps_wrapper.json").read_text(encoding="utf-8"))
    eps = side["eps"]
    z = np.load(new / "flow_series.npz", allow_pickle=True)
    rows, cols = z["rows"], [str(c) for c in z["columns"]]
    i = {c: k for k, c in enumerate(cols)}
    ft, v = rows[:, i["t"]], rows[:, [i[f"v_{l}"] for l in LEGS]]
    lim = rows[:, i["limited_mask"]] > 0
    s = np.load(new / "step_series.npz", allow_pickle=False)
    st, sm = s["t_s"], s["s_motor_m"]
    sel = (st[:-1] >= 13.4) & (st[1:] <= 14.95)
    slope = (sm[1:] - sm[:-1])[sel] / np.diff(st)[sel][:, None]
    vmid = np.column_stack([np.interp(st[:-1][sel], ft, v[:, j]) for j in range(4)])
    ratio = slope / vmid
    rec = np.load(new / "record/record.npz", allow_pickle=False)
    rt, ua = rec["t"], rec["u_applied"]
    rec_ratio = []
    for tq in (13.5, 14.0, 14.5, 14.9):
        k = int(np.searchsorted(rt, tq - 1e-6))
        j = int(np.searchsorted(ft, rt[k] - 1e-4 - 1e-9))
        rec_ratio.append({"t": float(rt[k]), "u_applied_mm_s": [float(x) * 1e3 for x in ua[k]], "flow_v_mm_s": [float(x) * 1e3 for x in v[j]], "ratio": [float(a / b) for a, b in zip(ua[k], v[j], strict=True)],
                          "limited_mask": int(rows[j, i["limited_mask"]])})
    base = np.load(STORED / "step_series.npz", allow_pickle=False)
    kb = int(np.searchsorted(base["t_s"], st[-1] - 1e-6))
    deficit = (base["s_motor_m"][kb] - sm[-1]) * 1e3
    q = rows[:, i["Q_sum"]]
    return {"eps": eps, "expected_ratio": 1.0 - eps, "slope_ratio_mean": ratio.mean(axis=0).tolist(), "slope_ratio_min": ratio.min(axis=0).tolist(), "slope_ratio_max": ratio.max(axis=0).tolist(),
            "steps_compared": int(sel.sum()), "limited_share_in_window": float(lim[(ft >= 13.4) & (ft <= 14.95)].mean()), "record_ratio": rec_ratio,
            "stroke_at_end_mm": (sm[-1] * 1e3).tolist(), "stroke_deficit_vs_stored_mm": deficit.tolist(), "expected_deficit_mm": ((sm[-1] * 1e3) * eps).tolist(),
            "flow_series_Q_sum_max_L_min": float(np.nanmax(q) * 6e4), "supply_L_min": float(z["supply_m3_s"]) * 6e4, "wrapper": side["state"]}


def main() -> None:
    c1 = compare(HERE / "bitcheck" / CASE)
    c2 = eps_check(HERE / "shortcheck" / CASE)
    (HERE / "check_on.json").write_text(json.dumps({"check1": c1, "check2": c2}, indent=1, default=str), encoding="utf-8")
    for k, v in c1.items():
        print("C1", k, v)
    for k, v in c2.items():
        print("C2", k, v)


if __name__ == "__main__":
    main()
